# Parallelism, rate limits, and deterministic ingest

**Source:** `docs/done/next/ingestion_tunningv2.md` §16 Appendix D; commit `34f658b` (phase 2a).

## Throughput bottleneck: LLM latency, not rate ceiling

The sequential PASO-4 classifier caps at **~40 RPM** even when `--rate-limit-rpm` is set to 300. Each Gemini 2.5 Flash call is ~1.5 s of network wait; one sequential worker can only make ~40 calls/min regardless of the ceiling. For the ~3,900-doc v6 corpus, that's 94 minutes of idle-looking-but-actually-throttled work.

**Lesson:** for I/O-bound LLM pipelines, `--rate-limit-rpm` is a *ceiling*, not a *target*. Actual throughput = `min(RPM_ceiling, workers × 60 / latency_seconds)`.

## Parallelism, done right

Phase 2a added `src/lia_graph/ingest_classifier_pool.py` (`ThreadPoolExecutor`, 8 workers by default, shared `TokenBucket`) and made it the **persistent default** for every ingest entry point — CLI, delta runtime, delta worker, UI controller. Measured: 40 RPM → 309 RPM steady-state (7.5×), 94 min → 6.5 min.

### Non-negotiables derived from the collusion-avoidance research

Tests pinning each guarantee live in `tests/test_ingest_classifier_pool.py`:

1. **Output order = input order.** Pre-allocated `results[i]`, workers write only to their own slot. Never use `as_completed` for canonical output. Test: `test_output_order_matches_input_regardless_of_completion_order`.
2. **Cross-run determinism.** `workers=1` and `workers=8` produce identical outputs on pure inputs. Test: `test_same_inputs_yield_same_outputs_across_runs`.
3. **Shared rate-limiter is one object.** Per-worker limiters interleave wrong. One `TokenBucket`, `threading.Lock`-guarded. Test: `test_token_bucket_caps_global_rpm_under_parallelism`.
4. **Retry with decorrelated jitter** (Brooker, AWS 2015: `random.uniform(base, min(cap, prev*3))`). Fixed backoff makes all N workers 429-lockstep.
5. **Per-slot failure isolation.** Exception in one worker populates `_ClassifierError(exc)` in that slot; siblings continue. Test: `test_per_doc_exception_isolates_to_that_slot`.
6. **No shared HTTP client state.** `urllib.request.urlopen` creates a fresh connection per call — safe. `requests.Session` reuse across threads is **not** safe without per-thread clients.
7. **Event log is append-only, order-unstable.** POSIX `O_APPEND` atomicity holds for writes < 4 KB (`PIPE_BUF`). Keep events compact; no raw prompts, no full doc bodies. Consumers sort on `ts_utc`.

## Rate-limit quotas are orthogonal

Gemini meters **three independent ceilings**. Throttling only one is not throttling at all.

| Ceiling | Model | Limit | How we throttled |
|---|---|---|---|
| **RPM** (requests/min) | Flash 2.5 | 1,000 | `TokenBucket(300)` — 70 % headroom ✅ |
| **TPM** (tokens/min) | Flash 2.5 | 1,000,000 | *unthrottled in v6* ❌ |
| **RPD** (requests/day) | Flash 2.5 | 10,000 | bounded by run duration ✅ |
| **RPM** | Embedding-1 | 3,000 | `--batch-size 25` for the embedding backfill ✅ |

**The gap that bit us.** During the cloud-sink classifier re-pass on 2026-04-24, EXPERTOS/PRACTICA docs (10 K+ tokens each) × 8 workers briefly pushed TPM past 1 M. Gemini returned **92 429s** ("RESOURCE_EXHAUSTED"). The classifier's inner try/except caught each 429 and returned a degraded N1-only verdict with `requires_subtopic_review=True`. Pool saw success (no exception). Result: ~7 % of docs landed without N2 subtopic refinement, honestly flagged but quietly degraded.

**Follow-up (prioritized):** add a `TokenBudget` sibling to `TokenBucket` that debits input-token estimates pre-call and refunds on 429. Until that lands, run with `--classifier-workers 4` on any corpus with >500 docs exceeding 5 K tokens, or accept the ~7 % N1-only degradation.

### Update — 2026-04-24 §J full rebuild measurement (next_v2.md §J)

The 7 % degradation rate cited above was the cloud-sink re-pass measurement. A second data point landed during the §J cloud verification rebuild (same corpus, same 8 workers, no TokenBudget primitive yet wired): **702 / 1275 = 55 % `requires_subtopic_review=true`, 144 HTTP 429s in the log, 96 tracebacks**. Eight times the prior data point and 11× the 5 % warning threshold.

**What changed.** Almost certainly the upstream prompt-template change between runs — heavier prompts inflate input tokens per call, so the same 8 workers blow past the 1 M TPM ceiling much earlier. The doc's mitigation (`--classifier-workers 4`) is now a **mandatory** floor for any full-corpus rebuild against production until the TokenBudget primitive is wired into the pool.

**The §J cloud verification trap.** The structural cleanup (delete-stale-TEMA-before-MERGE) ran correctly — but its inputs were ~55 % N1-only verdicts. So the new TEMA edges that replaced the wiped ones are partly based on degraded classifier output. The wrong-classification of `06_Libro1_T1_Cap5_Deducciones.md` (RENTA/Deductions chapter labeled `iva`) post-rebuild may itself be a degradation artifact, not a stable N2-refined verdict. **§K (classifier hardening) cannot be measured fairly until the rebuild is re-run with `--classifier-workers 4`.**

**Updated rule.** Any full-rebuild against the v6+ corpus on production: `--classifier-workers 4` is the default, not the fallback. Going to 8 workers requires either: (a) the TokenBudget primitive being live, or (b) acceptance that ~half the corpus will land N1-only and the rebuild's TEMA edges encode degraded verdicts.

### Update — 2026-04-25 taxonomy v2 landing (next_v3.md §7)

The next_v3 §7 classifier prompt redesign (taxonomy-aware + 6 mutex rules + PATH VETO clause + default-to-parent) is **heavier than the v1 prompt**: it enumerates all 88 active topics with one-line definitions, numbers 6 hard mutex-rule blocks, and adds a path-veto paragraph. Input tokens per call grow materially — rough estimate +40-60 % vs the v1 prompt on the same body preview.

**Implication for workers.** Enabling `LIA_INGEST_CLASSIFIER_TAXONOMY_AWARE={shadow,enforce}` on a full corpus rebuild re-enters the TPM-pressure regime that caused the §J 55 % degradation. The **`--classifier-workers 4` floor still holds** — and becomes more binding, not less. Running the v2 prompt at workers=8 against production without TokenBudget would push past 1 M TPM even faster than the v1 prompt did.

**Nothing-to-see-here detail that bit us.** `nohup bash -c "..."` on macOS inherits the parent shell's exported env vars — but `ps eww -p <pid>` on macOS does **not** show subprocess env the way Linux does (it shows cmdline only). That makes it easy to launch a detached rebuild believing the flag propagated when it silently didn't, or to doubt that it did when it actually did. **Fix pattern** (landed in `scripts/ingestion/launch_phase2_full_rebuild.sh` 2026-04-25): the launch script `export`s both `LIA_INGEST_CLASSIFIER_WORKERS` and `LIA_INGEST_CLASSIFIER_TAXONOMY_AWARE` explicitly inside the `nohup bash -c "..."` body, and emits a `phase2.rebuild.launch` event to `logs/events.jsonl` on startup whose payload echoes the active flag values. That gives the operator a definitive side-channel to confirm mode without relying on `ps eww`.

**Rule (addendum).** Every new long-running background launcher must (a) explicitly re-export every environment variable it depends on inside the `nohup` body and (b) emit a startup marker event whose payload echoes the relevant flag values. Never rely on ambient env-inheritance for a flag whose correctness matters — cheap emit, definitive verification.

## Config surface (make sure you inherit the defaults)

| Entry point | Default workers | Default RPM | Env override |
|---|---|---|---|
| `lia_graph.ingest` CLI | 8 | 300 | `LIA_INGEST_CLASSIFIER_WORKERS`, `LIA_INGEST_CLASSIFIER_RPM` |
| `ingestion.delta_runtime.materialize_delta` | 8 (via caller) | 300 | same |
| `ingestion.delta_worker` | 8 (via deps) | 300 | same |
| `ui_ingest_delta_controllers` | 8 (via deps) | 300 | same |

To force sequential for debugging: `--classifier-workers 1`. Never do this in production.

## See also

- `docs/done/next/ingestion_tunningv2.md` §16 Appendix D sections 2–3.
- `src/lia_graph/ingest_classifier_pool.py` — the primitives.
- `tests/test_ingest_classifier_pool.py` — the pinned invariants.
