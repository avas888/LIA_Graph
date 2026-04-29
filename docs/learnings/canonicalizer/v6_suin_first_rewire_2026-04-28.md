# v6 SUIN-first scraper rewire — engineering learnings (2026-04-28 Bogotá)

**Context.** fixplan_v6 wired SUIN-Juriscol as the preferred primary
source for the vigencia harness, replacing DIAN normograma's "knowingly
unstable" 3-MB master-page path. Engineering steps 1-5 closed in five
commits (`cfe64bb` → `f6525e1`); see `fixplan_v6.md` §3 for the recipes.
The first cascade attempt under the new code surfaced four lessons that
were **not** in the plan and that future cascades must internalize.

---

## Lesson 1 — Memory pressure is silent until catastrophic

**Symptom.** Cascade launched 7 batches × 24 thread workers (168 total).
Within 90 s, all workers were alive but **producing zero events**. The
throttle bucket had 2 timestamps from 2.5 min ago, then nothing. 0
active TCP connections from any worker. `sample` on a worker pid
showed every thread parked on `take_gil` / `_pthread_cond_wait`.

**Diagnosis.** `vm_stat` + `sysctl vm.swapusage` revealed the truth:
- Swap used: **14.8 GB / 16 GB total**.
- Pages free: ~73 MB.
- Per-worker RSS: 514 MB.

The system was thrashing into swap. Workers weren't deadlocked at the
Python level — they were stuck because the OS couldn't service their
memory requests fast enough.

**Root cause.** The SUIN scraper's `_slice_article_from_suin_html` ran
`parse_document()` on the **17 MB DUR-1625 HTML** for every norm in
the batch. BeautifulSoup-parsing a 17 MB doc allocates ~500 MB of
working memory and takes ~3-5 s. With 168 workers parsing
simultaneously, peak demand ≈ 84 GB. On a 16 GB machine, the OS swaps
hard, and the swap-page traffic blocks every CPU cycle.

**Fix** (commit `3845ee7`). Cache the parsed `SuinDocument` per URL on
the scraper instance. One parse per parent doc; all subsequent fetches
in the batch are dict lookups + a linear `SuinArticle` walk to find
the target article. Lock guards the dict; the parse itself runs
outside the lock (worst case two workers race on first parse — no
correctness issue, one wins the dict slot).

**Benchmark.** 60 fetches against the real DUR-1625 cached HTML:
- Before: 60 × ~30 s = ~30 min wall.
- After: 37 s wall (single parse + 60 slices).
- **~48× speedup; memory pressure linear in number of distinct parent docs, not norms.**

**Generalization.** Any scraper that does work-per-norm against a
shared parent doc must cache the parent. The cost of "naively parse on
every call" scales by `num_norms`; the cost of caching scales by
`num_parent_docs`. For DUR cascades that's 100× difference. The same
pattern applies to the Senado segment scraper if a future cascade
fans out across many articles in one segment file.

**How to detect this earlier next time.**
1. Watch `vm_stat` + `sysctl vm.swapusage` during the first 60 s of any
   high-fan-out batch. If `Pages free` drops below 10 000 (≈160 MB),
   you have ~30 s before the system seizes.
2. Watch worker TCP connection count via `lsof -p <pid> | grep TCP`.
   Zero TCP after 60 s in a network-bound workload = something is
   wrong before the network even gets queried.
3. The throttle state file (`var/gemini_throttle_state.json`) is the
   cheapest progress signal: if its timestamp count hasn't changed in
   60 s while workers are alive, the workers aren't reaching the
   `acquire_token()` call — i.e., they're stuck before the LLM step.

---

## Lesson 2 — The DEFAULT_RPM=80 was Gemini-derived, not DeepSeek-imposed

**What the comment said.** `gemini_throttle.py` documented the 80 cap
as "1 M TPM ÷ ~12 K tokens per call ≈ 80 RPM, the practical Gemini
Tier 1 ceiling." This number was carried over verbatim when the
canonicalizer migrated to DeepSeek-v4-pro, **without** anyone checking
DeepSeek's actual rate limits.

**What's actually true.** DeepSeek doesn't publish a per-account
RPM/TPM ceiling at our scale. The account limit is concurrency-based,
not per-minute. The 80 cap on DeepSeek runs is purely a "don't burn a
million calls in a runaway loop" safety net.

**Fix** (commit `a3ee6cd`). Env var resolution priority:
1. `LLM_DEEPSEEK_RPM` — preferred when on DeepSeek (current default).
2. `LIA_LLM_GLOBAL_RPM` — provider-agnostic alias.
3. `LIA_GEMINI_GLOBAL_RPM` — legacy, still honored.

Disable knob got a modern alias too (`LLM_GLOBAL_DISABLED`) alongside
the legacy `LIA_GEMINI_GLOBAL_DISABLED`. Module name + state file
keep the legacy `gemini_throttle` to avoid a sprawling rename;
docstring + log lines updated to read "LLM throttle".

**Generalization.** When migrating providers, audit the throttle
constants — they're easy to leave behind because the file name and
env var name still match the old provider. A grep for the old
provider name (`gemini`, `LIA_GEMINI`) will surface stale references
that the new provider doesn't bind.

**Tactical recommendation for DeepSeek runs.** `LLM_DEEPSEEK_RPM=240`
is a comfortable default — leaves headroom to triple worker count
without hitting the cap.

---

## Lesson 3 — F2 is NOT a SUIN-first beneficiary; canary picking matters

**Hypothesis the plan made.** `fixplan_v6.md` §4 expected F2 (94 v5
refusals, `res.dian.13.2021.art.*`) to jump from 17/111 to ~92/111
under the SUIN-first chain.

**What actually happened.** F2 closed in 3.2 min: **30/111 successes
(27 %), all `dian_normograma`-sourced**, 81 refusals all
`INSUFFICIENT_PRIMARY_SOURCES`.

**Diagnosis.** `res.dian.*` is **not in the SUIN registry** —
SUIN-Juriscol doesn't host DIAN administrative resolutions on factura
electrónica. F2's chain routes:
1. SUIN scraper → `_resolve_url(res.dian.13.2021.art.*)` → registry
   miss → returns None.
2. Senado → no res.dian.
3. DIAN normograma → returns content (the 3-MB master page) → same
   slicing problem v5 had.
4. CC, CE → no.

The 13 new successes came from DIAN retry alone (DIAN normograma is
"knowingly unstable", so retrying transient failures helps). SUIN
contributed nothing to F2's verdicts.

**Generalization.** When picking a canary for "did the new path
help?", verify the canary actually exercises the new path. F2's
parent doc isn't in our registry, so SUIN can't help — running F2
first told us nothing about whether SUIN-first works on DUR
articles. The proper canary for SUIN-first is **E1a**
(`decreto.1625.2016.art.*`) where the parent doc IS in the registry
and the slicer is the bottleneck.

**Process tweak for the next cascade.** Before running a batch as a
"canary", check: is the batch's parent norm_id in the relevant
scraper's registry? If not, the scraper can't help — use a different
canary or expect the result to reflect only the fallback chain.

---

## Lesson 4 — DUR multi-segment article numbers were silently truncated

**Bug.** `src/lia_graph/ingestion/suin/parser.py`'s
`_ARTICLE_HEADING_RE` used `\d+(?:[-.]\d+)?` — only ONE optional
`[-.]\d+` group. For "Artículo 1.1.1" the regex captured "1.1", which
`normalize_article_key` collapsed to "1-1". DUR articles like
`1.6.1.1.10` came out as "1-6". Every DUR-style canonical key would
have missed.

**Why nobody noticed.** The harvester's `articles.jsonl` was for
jurisprudencia (sentencias), where article numbers are typically
single-segment ("1", "2", etc.). The truncation didn't surface until
the SUIN scraper tried to slice DUR articles by full dotted key and
got zero matches.

**Fix** (commit `9940faf`, embedded in step 2). One-line regex
change: `\d+(?:[-.]\d+)*(?:\s*[Bb][Ii][Ss])?`. Verified against the
cached 17-MB DUR-1625: 4 557 articles now have proper multi-segment
numbers. `1-1-1` and `1-6-1-1-10` resolve correctly.

**Generalization.** When a regex captures a "number" in a domain
where multi-segment numbers are common (DUR, ETN, statutory
sub-articles), default to `+` or `*` repetition unless you have a
specific reason to limit it. The single-segment default came from a
pattern that was "correct for the document we tested against" but
silently wrong for the real production corpus.

**Test guardrail.** `test_real_dur_article_slice` in
`tests/test_suin_juriscol_scraper.py` runs against the real cached
DUR-1625 page; if anyone reverts the regex, the test fails loudly.

---

## Lesson 5 — Sequential is NOT always slower than parallel

**The cascade design** (`run_cascade_v5.sh`) is sequential: F2 →
E1a → E1b → ... → D5. We assumed parallel-batches would always be
faster.

**Reality check.** The 168-worker meltdown showed that parallelism
multiplied a per-process scaling problem (memory thrashing) into a
system-wide one. Sequential batches at 24 workers each would have
exposed the memory-per-norm cost in one batch (E1a) and let us
diagnose+fix it before launching others.

**Generalization.** Parallelize across batches only when each batch
is independently healthy at the chosen worker count. If you haven't
yet seen a single batch close cleanly at the target worker count, do
NOT parallelize. The cascade driver is sequential for a reason.

**Tactical rule for v6.1+.** Run E1a alone first at the target
worker count. If it closes cleanly, parallelize the remaining 6
batches. If it stalls or thrashes, fix the root cause before
launching anything else.

---

## Lesson 6 — Función Pública gestor normativo is the cleanest 6th-scraper candidate

**Background.** F2's INSUFFICIENT_PRIMARY_SOURCES refusals (and any
similar `res.dian.*` / `concepto.dian.*` failures) won't be fixed by
SUIN-first — those norms aren't in SUIN's harvest. We need a 6th
authoritative source.

**Research finding** (alt-DB research fork). Función Pública's gestor
normativo:
- Base: `https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=<N>`
- Verified DUR-1625: HTTP 200, 4.2 MB.
- HTML uses `<a name="1.1.1">` — DUR keys 1:1, **even cleaner** than
  SUIN's `ver_NNN`. Existing slicer pattern reuses with one regex
  tweak.
- Modification chains inline (`Modificado por…`).
- Government public domain, no auth wall.

**Coverage caveat.** DUR + ET + leyes confirmed; DIAN-specific
resolutions not yet probed. Run a 5-10-doc verification scrape before
committing.

**Discarded alternates.** `dian.gov.co` main site (PDF blobs, no
per-article anchors), Imprenta Diario Oficial (503 + paywalled),
Cancillería mirror (UA-sensitive, partial coverage).

**Recommendation.** Wire Función Pública as the 6th scraper using
the exact shape of the SUIN scraper (commit `9940faf`):
1. Build `var/funcionpublica_doc_id_registry.json` mapping canonical
   → `i=<N>`.
2. Implement `FuncionPublicaScraper` with three-tier cache + per-URL
   parsed-doc cache (the latter is now mandatory — see Lesson 1).
3. Add to chain after DIAN: `[Suin, Senado, Dian, FuncionPublica, CC, CE]`.

**Effort.** ~3 hr engineering. Tracked as v6.1 candidate.

---

## File index — what changed in v6 + the perf fix

| Concern | Commit |
|---|---|
| SUIN registry build script + 10 entries | `cfe64bb` |
| SUIN scraper rewrite + parser regex fix | `9940faf` |
| Scraper chain reorder (SUIN first) + trusted set expansion | `d00da64` |
| `--rerun-only-refusals` flag + launcher passthrough | `f91401b` |
| State ledger close (engineering done) | `f6525e1` |
| **Per-URL parsed-doc cache (cascade-stall fix)** | `3845ee7` |
| **`LLM_DEEPSEEK_RPM` env var (Gemini→DeepSeek transition)** | `a3ee6cd` |
| This learnings doc | _pending commit_ |

---

*Authored 2026-04-28 PM Bogotá by claude-opus-4-7 immediately after the
first v6 cascade meltdown + recovery. Cascade outcome appended below
(authored same evening after closure).*

---

## Cascade outcome (appended 2026-04-28 ~9:25 PM Bogotá)

After the meltdown + 4 corrective commits (perf cache, persisted slice
cache, throttle env-var rename, parser regex fix), the cascade ran end-
to-end across all three waves:

* **Postgres `norm_vigencia_history`: 783 → 2019 (+1236 net rows).**
* **2340 successes / 220 refusals / 0 errors** across 14 batches × 3
  hours of runtime.
* **91.4% overall pass rate** (97.0% if K3's CCo gap is excluded).

Per-wave breakdown:

| Wave | Batches | Pass rate | Notes |
|---|---|---|---|
| 1 (DUR-1625) | 6 batches, 1452 norms | **96.8%** | E3b 100%, E2c 96%, E1b 95%, E1d 89%, E2a 86%, E1a partial |
| 2 (CST/CCo) | 5 batches, 354 norms | 55.6% | **CST 100%** (J1-J4); **K3 CCo 30%** — gap detailed below |
| 3 (DUR-1072) | 3 batches, 754 norms | **97.7%** | All three above 97%; SUIN's DUR-1072 harvest is well-shaped |

### Lesson 7 — K3 CCo gap is a Senado-side problem, not SUIN

K3 (Wave 2 CCo articles) closed with 66 successes and 157 refusals. The
diagnostic surprised me — **all 157 refusals had
`single_source_accepted='secretaria_senado'`**. Meaning:
- SUIN returned None for the CCo articles (registry has CCo but harvest
  may be incomplete OR slicer misses CCo numbering).
- Senado returned content (single-source acceptance triggered).
- LLM was invoked and refused with `INSUFFICIENT_PRIMARY_SOURCES`.

So Senado IS finding content, but the slice is too thin. The root
cause is likely that we don't ship a `var/senado_cco_pr_index.json`
(equivalent to the ET index) — high-numbered CCo articles fall back
to the master `codigo_comercio.html` page where anchor-slicing pulls
a too-small fragment.

**Fix candidates (v7):**
1. Build the CCo pr-segment index (mirror `build_senado_et_index.py`).
2. Improve the master-page slicer to include full body between anchors.
3. Wire **Función Pública gestor normativo** as a 6th scraper.

Per the alt-DB research fork, Función Pública has CCo with
`<a name="N">` anchors — cleaner than Senado's `[[ART:N]]` markers
and cleaner than SUIN's `ver_NNN`. This is the cheapest path because
it reuses the SUIN scraper architecture.

### Lesson 8 — Memory pressure isn't always swap pressure

Mid-cascade I diagnosed multiple stalls as "memory thrashing" because
free RAM was 60-80 MB and swap was 13+ GB used. But the operator's
Activity Monitor screenshot showed the system was actually fine
(24 GB total RAM, GREEN memory pressure indicator, ~3.5 GB free).

The 60-80 MB "Free RAM" reading on macOS doesn't mean starved — macOS
uses available RAM for caching aggressively, and the real signal is
the memory-pressure indicator (green/yellow/red). I'd been
over-interpreting `vm_stat` output.

**Lesson:** trust the OS-level memory pressure signal (Activity Monitor
or `memory_pressure -Q`), not just `vm_stat | awk` for free pages.
For server/headless environments, parse `sysctl vm.swapusage` plus
`memory_pressure` for the proper signal.

### Lesson 9 — Sequential primer + parallel consumers IS the pattern

After the meltdown, the recovery pattern that scaled cleanly:

1. Launch ONE batch alone (the "primer") — pays the parse cost,
   populates the SQLite slice cache.
2. Wait ~90 seconds for the parse to complete + slices to land in
   `parsed_meta["articles"]`.
3. Launch the rest as "consumers" — they read SQLite slices, never
   re-parse. Per-process memory ~50 MB.

Wave 2 used this with J1+K3 as primers (different parents — CST + CCo)
and J2/J3/J4 as CST consumers. All J* batches landed at 100% pass
rate. The pattern is now codified in
`docs/re-engineer/fixplan_v6.md` §8b lessons-learned.

### Final state

Engineering deliverables (all committed):
* `cfe64bb` SUIN registry build script + 10 entries
* `9940faf` SUIN scraper + parser regex fix (multi-segment DUR numbers)
* `d00da64` Chain reorder + trusted set
* `f91401b` `--rerun-only-refusals` + launcher passthrough
* `f6525e1` Engineering ledger close
* `a3ee6cd` `LLM_DEEPSEEK_RPM` env var
* `3845ee7` Per-URL parsed-doc cache (48× speedup)
* `19fd5a1` This learnings doc (initial 6 lessons)
* `92c5661` Persisted slice cache via SQLite (38× speedup, parallel-safe)
* `d65ee62` Cascade closure ledger entry
* `b821162` Cascade outputs (2340 veredicto JSONs)

Outstanding follow-ons (queued):
* Función Pública 6th scraper (~3 hr) — closes F2/G1/CCo gaps
* SUIN harvest extension (v7) — decreto 417/2020 + concepto 0001/2003
* CCo pr-segment index (v7) — fixes K3 if Función Pública isn't built
* E1a long tail finishes async (workers=2 conservative — ~325 norms left)
* Cloud promotion (operator gate, post SME signoff)
