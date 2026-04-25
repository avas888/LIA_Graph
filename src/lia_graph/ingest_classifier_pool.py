"""Phase 2a (v6) — parallel classifier pool with deterministic output.

The sequential PASO-4 classifier caps at ~40 RPM because each Gemini call
is ~1.5 s of network wait. Throughput-wise the workload is I/O-bound,
not CPU-bound, so a ``ThreadPoolExecutor`` closes the gap without
cascading async changes through ``llm_runtime``, ``ingestion_classifier``,
or the CLI.

This module owns the three primitives needed to parallelize that pass
without collusion:

1. ``TokenBucket`` — thread-safe, in-process RPM admission. One shared
   bucket per pipeline run so the *aggregate* RPM across workers stays
   under the Gemini ceiling, regardless of worker count. Bucket capacity
   is ``max(1, rpm // 6)`` (10-second burst budget — matches the
   Guava / Envoy local-rate-limit defaults and avoids the long-smooth
   starvation that leaky-bucket variants show on bursty inputs).

2. ``classify_documents_parallel`` — the pool loop. Pre-allocated
   ``results[i]`` list, futures submitted with their input index,
   output assembly by index. **Output order is byte-identical to the
   input regardless of completion order** (determinism criterion), and
   any per-doc failure is captured per-future, never aborts siblings
   (idempotency / isolation criterion).

3. ``_sleep_with_jitter`` — decorrelated-jitter backoff on per-call
   failure. Prevents thundering-herd retry lockstep on rate-limit 429s
   (Marc Brooker, "Exponential Backoff And Jitter", AWS 2015).

Not in scope (defer):
  * Persistent verdict cache keyed on (content_hash, template_version,
    model_id). Would make *replays* bit-identical across runs; not
    required for a single run to be deterministic.
  * Per-worker HTTP session. ``GeminiChatAdapter`` uses
    ``urllib.request.urlopen`` per call with no shared opener, so
    worker sessions would buy nothing here.
  * Queue-serialized event writer. POSIX ``O_APPEND`` writes <4 KB
    are atomic, and our event payloads are well under that; the
    existing ``instrumentation._append_jsonl`` is safe for our workers.

This module is intentionally ~130 LOC. Extract further only if we grow
it beyond ~250. Keep ``ingest_subtopic_pass.py`` thin — its job is to
glue the taxonomy/audit/event bookkeeping around whatever
classification strategy is selected.
"""

from __future__ import annotations

import random
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable


class TokenBucket:
    """Thread-safe token-bucket admission control for N workers.

    ``rpm <= 0`` means unlimited (the bucket never blocks) — matches the
    prior ``_apply_rate_limit`` sentinel used by tests that don't care
    about throttling.
    """

    def __init__(self, rpm: int, capacity: int | None = None) -> None:
        self.rpm = int(rpm)
        # 10-second burst window; Guava/Envoy convention. For rpm=300 this
        # caps initial burst at 50 requests, smoothing the ramp after a
        # pause (e.g., a retry backoff) without long-tail starvation.
        effective_rpm = max(1, self.rpm)
        self.capacity = float(
            capacity if capacity is not None else max(1, effective_rpm // 6)
        )
        self._tokens = self.capacity
        self._last = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        if self.rpm <= 0:
            return  # unlimited — no throttling
        while True:
            with self._lock:
                now = time.monotonic()
                elapsed = now - self._last
                self._tokens = min(
                    self.capacity, self._tokens + elapsed * (self.rpm / 60.0)
                )
                self._last = now
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
                deficit = 1.0 - self._tokens
                wait = deficit * (60.0 / self.rpm)
            # Sleep outside the lock so siblings can refill the bucket
            # between our wake-ups.
            time.sleep(wait)


class TokenBudget:
    """Thread-safe TPM admission control for N workers.

    Sibling to :class:`TokenBucket` but with per-acquire variable cost.
    Workers acquire ``cost`` tokens where ``cost`` = estimated prompt+body
    token count for the call. Prevents silent TPM-429s on Gemini Flash
    (1 M TPM paid-tier quota) which today are absorbed by
    ``ingestion_classifier._run_n2_cascade`` as degraded N1-only verdicts
    (``requires_subtopic_review=True``), costing ~7% of v6-corpus docs.

    ``tpm <= 0`` means unlimited (budget no-ops). That is the current
    default — operators opt into the limiter by setting
    ``LIA_INGEST_CLASSIFIER_TPM`` or passing ``token_budget_tpm`` to
    :func:`classify_documents_parallel`. See next_v1 step 06 for the
    full design rationale and the remaining 429-detection follow-up.
    """

    def __init__(self, tpm: int, capacity: int | None = None) -> None:
        self.tpm = int(tpm)
        # 10-second burst window — matches ``TokenBucket`` shape.
        effective_tpm = max(1, self.tpm)
        self.capacity = float(
            capacity if capacity is not None else max(1, effective_tpm // 6)
        )
        self._tokens = self.capacity
        self._last = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self, cost: int) -> None:
        if self.tpm <= 0 or cost <= 0:
            return  # unlimited or zero-cost — no throttling
        # Clamp to capacity so an over-estimate can't deadlock the worker.
        cost = min(int(cost), int(self.capacity))
        while True:
            with self._lock:
                now = time.monotonic()
                elapsed = now - self._last
                self._tokens = min(
                    self.capacity, self._tokens + elapsed * (self.tpm / 60.0)
                )
                self._last = now
                if self._tokens >= cost:
                    self._tokens -= cost
                    return
                deficit = cost - self._tokens
                wait = deficit * (60.0 / self.tpm)
            # Sleep outside the lock so siblings can refill between wake-ups.
            time.sleep(wait)

    def refund(self, cost: int) -> None:
        """Return tokens to the budget — called on a TPM-429 retry path.

        Does not overshoot ``capacity`` (a refund that would exceed capacity
        is silently capped). Future follow-up in next_v1 step 06 wires this
        into the classifier's 429 retry loop once the Gemini adapter's
        exception shape is confirmed.
        """
        if self.tpm <= 0 or cost <= 0:
            return
        with self._lock:
            self._tokens = min(self.capacity, self._tokens + int(cost))


def estimate_input_tokens(prompt: str, body: str, *, max_body_chars: int = 2000) -> int:
    """Rough Gemini tokenizer estimate for TPM admission control.

    Spanish legal text is ~1.25 chars per token on average (heavier than
    English's ~4:1 because of diacritics + legal-specific vocabulary).
    We over-estimate to 1 char = 1 token — cheaper to over-debit than to
    hit a 429. The classifier truncates body at ~2 KB, so we don't count
    past ``max_body_chars``.

    Not using Gemini's ``countTokens`` API here: it would double LLM
    volume for what is fundamentally a rate-limiting decision, not a
    billing decision.
    """
    truncated = body[:max_body_chars] if body else ""
    return len(prompt or "") + len(truncated)


def _sleep_with_jitter(attempt: int, base: float = 0.5, cap: float = 30.0) -> float:
    """Decorrelated-jitter backoff per Brooker (AWS 2015).

    Returns the slept duration so the caller can log it.
    """
    delay = random.uniform(base, min(cap, base * (3 ** attempt)))
    time.sleep(delay)
    return delay


def classify_documents_parallel(
    documents: tuple,
    *,
    classify_fn: Callable[[int, Any], Any],
    worker_count: int,
    rate_limit_rpm: int,
    max_retries: int = 2,
    on_progress: Callable[[int], None] | None = None,
) -> list:
    """Run ``classify_fn(index, doc)`` over ``documents`` with ``worker_count``
    threads, sharing a single ``TokenBucket`` rated at ``rate_limit_rpm``.

    Returns a list the same length as ``documents``, populated in input
    order. Each slot holds whatever ``classify_fn`` returned, or ``_Error``
    (exposed as its ``.exc`` attribute) when the call kept failing through
    all retries.

    Determinism guarantees:
      * Output index matches input index, regardless of completion order.
      * No shared counter is mutated in worker threads.
      * ``classify_fn`` is expected to be pure-enough (the LLM call is the
        non-pure part; the caller — ``ingest_subtopic_pass`` — owns the
        taxonomy bookkeeping and event emission around it).
    """
    n = len(documents)
    results: list[Any] = [None] * n
    bucket = TokenBucket(rate_limit_rpm)

    def _worker(index: int, doc: Any) -> tuple[int, Any]:
        last_exc: BaseException | None = None
        for attempt in range(max_retries + 1):
            bucket.acquire()
            try:
                return index, classify_fn(index, doc)
            except Exception as exc:  # noqa: BLE001 — per-doc tolerance
                last_exc = exc
                if attempt >= max_retries:
                    break
                _sleep_with_jitter(attempt)
        return index, _ClassifierError(last_exc)

    with ThreadPoolExecutor(
        max_workers=max(1, worker_count),
        thread_name_prefix="classpool",
    ) as executor:
        futures: list[Future] = [
            executor.submit(_worker, i, doc) for i, doc in enumerate(documents)
        ]
        for fut in futures:
            index, value = fut.result()
            results[index] = value
            if on_progress is not None:
                on_progress(index)

    return results


class _ClassifierError:
    """Opaque sentinel carrying the original exception.

    Callers branch on ``isinstance(value, _ClassifierError)`` instead of
    the ``None`` sentinel used by the sequential path — this distinguishes
    "classifier failed for this doc" from "worker hasn't filled this slot
    yet" during partial shutdowns.
    """

    __slots__ = ("exc",)

    def __init__(self, exc: BaseException | None) -> None:
        self.exc = exc

    def __repr__(self) -> str:
        return f"_ClassifierError({self.exc!r})"


def is_classifier_error(value: Any) -> bool:
    return isinstance(value, _ClassifierError)


def classifier_error(value: Any) -> BaseException | None:
    return value.exc if isinstance(value, _ClassifierError) else None


__all__ = [
    "TokenBucket",
    "TokenBudget",
    "classifier_error",
    "classify_documents_parallel",
    "estimate_input_tokens",
    "is_classifier_error",
]
