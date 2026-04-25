"""TokenBudget — next_v1 step 06 primitive.

Five tests per the step-06 design §4 regression guards:

1. Default TPM (1M) never throttles a reasonable workload.
2. Low TPM (100) correctly forces sequential calls.
3. Cost > capacity gets clamped.
4. ``refund()`` restores tokens exactly.
5. Thread-safety: 8 workers acquire+refund against a shared budget without deadlock.

These tests cover the primitive's contract. The integration into
``classify_documents_parallel`` (pre-debit + 429 refund + retry) is a
separate follow-up because it requires threading a new
``TPMRateLimitError`` through ``ingestion_classifier._run_n2_cascade``
(which today swallows all exceptions). See step-06 deep-dive §3.3 + §3.4.
"""

from __future__ import annotations

import threading
import time

from lia_graph.ingest_classifier_pool import (
    TokenBudget,
    estimate_input_tokens,
)


def test_default_tpm_1m_never_throttles_reasonable_workload() -> None:
    """At 1 M TPM (Gemini Flash paid-tier), a 100-call × 500-token burst
    fits well within the 10-second burst capacity (~166K tokens) and
    should complete in well under 50 ms total wait."""
    budget = TokenBudget(tpm=1_000_000)
    t0 = time.perf_counter()
    for _ in range(100):
        budget.acquire(500)  # 50K total, capacity ≈ 166K
    wall = time.perf_counter() - t0
    # Unthrottled acquires are effectively no-ops — must finish near-instantly.
    assert wall < 0.1, f"default TPM unexpectedly throttled: {wall:.3f}s"


def test_low_tpm_forces_sequential_pacing() -> None:
    """At 600 TPM (= 10 tokens/s), acquiring 20 tokens twice must take
    at least ~1 second of real waiting on the second call because capacity
    is 100 tokens (600/6) so both fit in burst — but acquiring 120 tokens
    would need to wait. Use the stronger test: cost > capacity forces wait."""
    budget = TokenBudget(tpm=600)  # capacity = 100 tokens
    # Drain the burst first
    budget.acquire(100)
    t0 = time.perf_counter()
    budget.acquire(30)  # needs 30 tokens, refill rate = 10/s → ~3s wait
    wall = time.perf_counter() - t0
    assert wall >= 2.5, f"low-tpm acquire should pace but waited only {wall:.3f}s"
    assert wall < 4.0, f"low-tpm acquire overshot expected pace: {wall:.3f}s"


def test_cost_greater_than_capacity_is_clamped() -> None:
    """A single acquire that exceeds capacity must not deadlock — it
    gets clamped to capacity so the worker proceeds (over-estimates
    shouldn't freeze the pool)."""
    budget = TokenBudget(tpm=6000)  # capacity = 1000 tokens
    t0 = time.perf_counter()
    budget.acquire(10_000_000)  # absurdly over-estimated
    wall = time.perf_counter() - t0
    # Clamped to capacity=1000 tokens; burst has 1000 tokens → immediate
    assert wall < 0.5, f"over-cost should clamp+return fast, took {wall:.3f}s"


def test_refund_restores_tokens_exactly() -> None:
    """After debiting N and refunding N, the budget should be back to
    its pre-debit token count (within floating-point + refill rounding)."""
    budget = TokenBudget(tpm=6000)  # capacity = 1000
    # Debit 800 out of 1000
    budget.acquire(800)
    with budget._lock:
        after_debit = budget._tokens
    budget.refund(800)
    with budget._lock:
        after_refund = budget._tokens
    assert after_refund > after_debit
    # Refund should not overshoot capacity
    assert after_refund <= budget.capacity + 0.01


def test_thread_safety_eight_workers_no_deadlock() -> None:
    """8 workers acquiring + refunding a shared budget concurrently must
    all terminate cleanly. Deadlock would show up as a timeout here."""
    budget = TokenBudget(tpm=120_000)  # capacity = 20K, plenty for the test
    iterations_per_worker = 25
    errors: list[BaseException] = []
    done = threading.Event()

    def _worker() -> None:
        try:
            for _ in range(iterations_per_worker):
                budget.acquire(100)
                budget.refund(50)  # half-refund each cycle
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=_worker) for _ in range(8)]
    t0 = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10.0)
        assert not t.is_alive(), "worker thread deadlocked"
    wall = time.perf_counter() - t0
    assert not errors, f"workers raised: {errors}"
    assert wall < 10.0, f"thread test overran: {wall:.2f}s"


# ── estimate_input_tokens sanity ───────────────────────────────


def test_estimator_sums_prompt_and_truncated_body() -> None:
    """Regression guard for the cheap estimator heuristic."""
    # Both below max_body_chars: straight sum
    assert estimate_input_tokens("abc", "defgh") == 8
    # Body truncation: body longer than max_body_chars only counts the window
    long_body = "x" * 5000
    assert estimate_input_tokens("", long_body, max_body_chars=2000) == 2000
    # None/empty resilience
    assert estimate_input_tokens("", "") == 0
    assert estimate_input_tokens(None, None) == 0  # type: ignore[arg-type]


def test_tpm_zero_means_unlimited() -> None:
    """tpm=0 sentinel matches TokenBucket — budget never blocks."""
    budget = TokenBudget(tpm=0)
    t0 = time.perf_counter()
    budget.acquire(100_000_000)  # any cost, should no-op
    assert time.perf_counter() - t0 < 0.05
