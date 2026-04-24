# Step 06 — TPM-aware token-budget limiter

**Priority:** P1 · **Estimated effort:** 3 days (2 dev + 1 validation) · **Prerequisite:** none (independent of retrieval-quality steps)

## §1 What

Add a `TokenBudget` sibling to the existing `TokenBucket` in `src/lia_graph/ingest_classifier_pool.py`. The bucket today tracks **requests per minute (RPM)** — perfect for Gemini's per-model RPM cap (1,000 for Flash). The budget will track **tokens per minute (TPM)** — which is an independent, orthogonal quota (1,000,000 for Flash).

Classifier workers will acquire from BOTH: one RPM token, and N TPM tokens sized to the prompt's estimated input-token count. If either ceiling is hit, the worker sleeps until both are available.

On a 429 `RESOURCE_EXHAUSTED` with `metric=...input_token_count`, the worker refunds the TPM tokens (we over-estimated or were burst-bounded) and retries after the server-provided `retryDelay`.

## §2 Why

Every v6 classifier run emitted 92–114 `Traceback` lines in stderr, all from Gemini TPM 429s. The classifier's `_run_n2_cascade` catches them and returns degraded N1-only verdicts with `requires_subtopic_review=True`. Effects:

1. **~7 % of docs land with degraded subtopic classification.** They get N1 (rule-based) stamps instead of N2 (LLM-refined). Measurable via `grep -c '"requires_subtopic_review": true' logs/events.jsonl`.
2. **Each 429 costs ~53 s of retry wait per worker.** With 8 workers × ~15 collisions each × 53 s = 6+ min of lost throughput. A TPM-aware limiter prevents the collision entirely, so we claim that time back.
3. **Root cause is well-understood.** RPM says "how often can we call?"; TPM says "how much text can we send?". Our single-field throttle answers question 1 and silently violates question 2.

Evidence: `docs/learnings/ingestion/parallelism-and-rate-limits.md` §"Rate-limit quotas are orthogonal" and the 2026-04-24 post-mortem in `docs/learnings/process/cloud-sink-execution-notes.md`.

## §3 Design

### §3.1 The `TokenBudget` class

Mirror `TokenBucket` but with configurable acquire-size:

```python
class TokenBudget:
    """Thread-safe token-count budget for N concurrent LLM workers.

    Parallel to TokenBucket but with per-acquire variable cost. Workers
    acquire the estimated input tokens for their call; refund on 429
    for subsequent retry.
    """
    def __init__(self, tpm: int, capacity: int | None = None) -> None:
        self.tpm = max(1, int(tpm))
        # Burst window — 10 s worth, same shape as TokenBucket
        self.capacity = float(capacity if capacity is not None else self.tpm / 6)
        self._tokens = self.capacity
        self._last = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self, cost: int) -> None:
        if self.tpm <= 0 or cost <= 0:
            return
        cost = min(cost, int(self.capacity))  # clamp to capacity
        while True:
            with self._lock:
                now = time.monotonic()
                elapsed = now - self._last
                self._tokens = min(
                    self.capacity,
                    self._tokens + elapsed * (self.tpm / 60.0),
                )
                self._last = now
                if self._tokens >= cost:
                    self._tokens -= cost
                    return
                deficit = cost - self._tokens
                wait = deficit / (self.tpm / 60.0)
            time.sleep(wait)

    def refund(self, cost: int) -> None:
        with self._lock:
            self._tokens = min(self.capacity, self._tokens + cost)
```

### §3.2 Token-count estimator

Cheap heuristic — don't call Gemini's `countTokens` per doc, that doubles API volume. Use whitespace+punctuation:

```python
def estimate_input_tokens(prompt: str, body: str, max_body_chars: int = 2000) -> int:
    """Rough Gemini tokenizer estimate.

    Spanish legal text is ~1.25 chars per token on average (heavier than
    English's ~4:1 because of diacritics + legal-specific vocabulary).
    We over-estimate to 1 char = 1 token for safety — it's cheaper to
    over-debit than to hit a 429.
    """
    # Classifier truncates body at 2 KB so don't count past that.
    truncated = body[:max_body_chars]
    return len(prompt) + len(truncated)
```

Trade-off: over-estimate by ~20 %. That slightly reduces worker concurrency at TPM boundary. Acceptable — the alternative (exact token count) costs one extra API call per classifier call, doubling LLM volume.

### §3.3 Worker integration

Extend `classify_documents_parallel` signature:

```python
def classify_documents_parallel(
    documents,
    *,
    classify_fn,
    worker_count: int,
    rate_limit_rpm: int,
    token_budget_tpm: int = 1_000_000,   # NEW — Gemini Flash paid-tier default
    max_retries: int = 2,
    on_progress=None,
) -> list[Any]:
```

Inside `_worker`:

```python
def _worker(index: int, doc: Any) -> tuple[int, Any]:
    estimated_tokens = estimate_input_tokens(PROMPT_TEMPLATE, doc.body)
    last_exc = None
    for attempt in range(max_retries + 1):
        bucket.acquire()           # RPM
        budget.acquire(estimated_tokens)  # TPM
        try:
            return index, classify_fn(index, doc)
        except TPMRateLimitError as exc:
            # Classifier wrapping teaches us to detect this specific 429
            budget.refund(estimated_tokens)
            if attempt >= max_retries:
                last_exc = exc
                break
            _sleep_with_jitter(attempt, base=exc.retry_after_seconds or 1.0)
        except Exception as exc:
            last_exc = exc
            if attempt >= max_retries:
                break
            _sleep_with_jitter(attempt)
    return index, _ClassifierError(last_exc)
```

### §3.4 Surfacing the 429 up from the classifier

Today the classifier swallows the 429 inside `_run_n2_cascade` and returns a degraded verdict. We need a way for the pool to see it. Options:

| Option | Pro | Con |
|---|---|---|
| A: Thread an `on_rate_limit` callback from pool into classifier | Minimal API change | Threading a callback through 3 layers is ugly |
| B: Have the classifier re-raise TPM 429s instead of swallowing | Clean separation | Changes classifier contract; other callers might break |
| C: Inspect the returned verdict for `requires_subtopic_review=True` AND empty N2 verdict fields as a post-hoc signal | Works without changing classifier internals | Noisy signal — other failure modes also set these flags |

**Pick B.** Classifier raises a specific `TPMRateLimitError` (new exception class in `ingestion_classifier.py`); callers that want the old "silently degrade" behavior opt in via a flag. Pool opts out (lets the pool handle retries).

### §3.5 Configuration surface

New env var: `LIA_INGEST_CLASSIFIER_TPM` default 1000000. CLI flag `--classifier-tpm` pass-through same as `--classifier-workers`.

## §4 Success criteria

**Hard gates (must all pass before merge):**

1. **Zero `Traceback` lines in stderr** during a full classifier pass on the v6 corpus (1,275 docs, 8 workers). Verify: `grep -c Traceback logs/phase2_full_rebuild_*.log` returns 0.
2. **Zero rows with `requires_subtopic_review=True`** in the post-run events.jsonl. Verify: `grep -c '"requires_subtopic_review": true' logs/events.jsonl` returns 0 for the run's events.
3. **Wall-time within ±10 % of baseline** (6m32s measured). Acceptance band: 5m54s to 7m11s. The TPM limiter slows individual bursts but eliminates retries; net should be close.
4. **All existing tests still pass:** `make test-batched` count unchanged.

**New tests (regression guards):**

5. `tests/test_token_budget.py` — 5 tests:
   - Default TPM (1M) never throttles a reasonable workload.
   - Low TPM (100) correctly forces sequential calls.
   - Cost > capacity gets clamped.
   - `refund()` restores tokens exactly.
   - Thread-safety: 8 workers acquire+refund against a shared budget without deadlock.

6. `tests/test_ingest_classifier_pool.py::test_token_budget_integration` — 1 test: pool run with a fake classifier that simulates TPM 429 on 1 of 10 docs; verify retry + successful completion with total_tokens_used within the budget.

**Soft gates (lift but not block):**

7. Next full-corpus run logs zero `Quota exceeded for metric: ...generate_content_paid_tier_input_token_count` lines.
8. On a smaller corpus (100 docs), run with `LIA_INGEST_CLASSIFIER_TPM=50000` (deliberately tight) — verify the run completes without failures, just slower.

## §5 Out of scope

- **Token-counting via the Gemini tokenizer API.** Too expensive per call. Heuristic + clamp is good enough.
- **Per-model TPM differentiation.** We currently only call Flash for classification. If we add Pro for high-confidence docs later, add per-model budgets then.
- **RPM/TPM split between classifier and embedding calls.** Embeddings use a different model (Gemini Embedding 1) with its own 3K RPM cap (enforced by batch-size on the embedding script, not by this TokenBudget).

## §6 What could go wrong

- **Heuristic over-estimates enough that effective TPM usage drops below 50 %.** Workers wait on budget longer than they need to. Symptom: wall time regresses > 20 %. Mitigation: tune the `max_body_chars` and/or the 1:1 chars-to-tokens assumption. Fall-back: switch to actual `countTokens` API with a small cache.
- **Classifier's internal try/except still swallows some 429s** even after option-B refactor. Symptom: tracebacks in log but zero in pool-boundary failure count. Mitigation: grep both signals in the success criterion.
- **TPM budget becomes stale** if Gemini changes its quota tier. Every `LIA_INGEST_CLASSIFIER_TPM` default bump is a followup.

## §7 Rollback

- Env var set to 0 or unlimited → budget no-ops → classifier behaves as pre-step-06 (swallow 429s, degrade). Full rollback via env.
- Code rollback: `git revert <sha>` — no cloud writes, no migrations. Safe.

## §8 Dependency on step 05

Step 05 exposes worker-count knob via UI. This step adds a new env var. UI should surface this one too after step 05 ships. Not a blocker — the env var is usable without UI exposure.
