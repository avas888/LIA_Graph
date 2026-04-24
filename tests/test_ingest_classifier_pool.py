"""Phase 2a (v6) — parallel classifier pool.

Pins the determinism + idempotency + rate-cap guarantees so any future
regression (a well-meaning refactor that swaps to ``as_completed``, for
example) breaks loudly. We test the pool primitives in isolation — no
real LLM, no real corpus — to keep this fast.
"""

from __future__ import annotations

import threading
import time

import pytest

from lia_graph.ingest_classifier_pool import (
    TokenBucket,
    classifier_error,
    classify_documents_parallel,
    is_classifier_error,
)


# ── 1. Output order is input order, always ────────────────────────────


def test_output_order_matches_input_regardless_of_completion_order() -> None:
    # Slower-when-earlier-index work: index 0 sleeps longest, index N-1
    # sleeps briefest. In a wrong implementation (as_completed, append),
    # the result order would be [N-1, N-2, ..., 0]; we must always get
    # [0, 1, ..., N-1].
    docs = tuple(f"doc-{i}" for i in range(20))
    def _work(idx: int, doc: str) -> str:
        time.sleep(0.02 * (len(docs) - idx))  # earliest idx is slowest
        return f"OUT-{doc}"

    results = classify_documents_parallel(
        docs,
        classify_fn=_work,
        worker_count=8,
        rate_limit_rpm=1000,
    )
    assert results == [f"OUT-doc-{i}" for i in range(len(docs))]


# ── 2. Determinism across repeated runs ──────────────────────────────


def test_same_inputs_yield_same_outputs_across_runs() -> None:
    docs = tuple(f"doc-{i}" for i in range(30))
    def _work(idx: int, doc: str) -> str:
        time.sleep(0.001)  # trivial variance
        return f"v-{idx}-{doc}"

    run1 = classify_documents_parallel(
        docs, classify_fn=_work, worker_count=8, rate_limit_rpm=1000
    )
    run2 = classify_documents_parallel(
        docs, classify_fn=_work, worker_count=8, rate_limit_rpm=1000
    )
    run3 = classify_documents_parallel(
        docs, classify_fn=_work, worker_count=1, rate_limit_rpm=1000
    )
    assert run1 == run2 == run3


# ── 3. Token bucket enforces the global RPM even under N workers ──────


def test_token_bucket_caps_global_rpm_under_parallelism() -> None:
    docs = tuple(range(60))  # 60 items
    rpm = 120
    worker_count = 8
    calls: list[float] = []
    calls_lock = threading.Lock()

    def _work(idx: int, doc: int) -> int:
        with calls_lock:
            calls.append(time.monotonic())
        return doc * 2

    t0 = time.monotonic()
    classify_documents_parallel(
        docs,
        classify_fn=_work,
        worker_count=worker_count,
        rate_limit_rpm=rpm,
    )
    elapsed = time.monotonic() - t0
    # 60 items at 120 RPM (= 2/s) ideal floor is 30 s, but the 10-second
    # burst (capacity=20) lets the first 20 happen ~instantly, so the
    # remaining 40 need at least 40 / 2 = 20 s. Leave a safety margin
    # for test-host jitter; assert the cap, not an exact number.
    min_expected = 40 / (rpm / 60.0) * 0.85  # ≥ 17s
    assert elapsed >= min_expected, f"elapsed {elapsed:.2f}s too fast — RPM not enforced"


# ── 4. Failure in one worker does not abort siblings ──────────────────


def test_per_doc_exception_isolates_to_that_slot() -> None:
    docs = tuple(range(10))
    def _work(idx: int, doc: int) -> int:
        if doc == 5:
            raise RuntimeError("simulated classifier failure")
        return doc * 10

    results = classify_documents_parallel(
        docs,
        classify_fn=_work,
        worker_count=4,
        rate_limit_rpm=1000,
        max_retries=0,  # fail fast in the test
    )
    assert len(results) == 10
    for i, v in enumerate(results):
        if i == 5:
            assert is_classifier_error(v)
            err = classifier_error(v)
            assert isinstance(err, RuntimeError)
        else:
            assert v == i * 10


# ── 5. Retries back off with decorrelated jitter (not lockstep) ───────


def test_retries_succeed_on_second_attempt() -> None:
    attempts: dict[int, int] = {}
    attempts_lock = threading.Lock()

    def _work(idx: int, doc: int) -> int:
        with attempts_lock:
            attempts[idx] = attempts.get(idx, 0) + 1
            current = attempts[idx]
        if current < 2:
            raise ConnectionError("transient")
        return doc

    docs = tuple(range(6))
    results = classify_documents_parallel(
        docs,
        classify_fn=_work,
        worker_count=3,
        rate_limit_rpm=1000,
        max_retries=2,
    )
    assert results == list(docs)
    # Each doc should have been tried exactly twice.
    assert all(attempts[i] == 2 for i in range(6))


# ── 6. Empty input is a no-op ─────────────────────────────────────────


def test_empty_input_returns_empty_list() -> None:
    results = classify_documents_parallel(
        (),
        classify_fn=lambda i, d: d,
        worker_count=8,
        rate_limit_rpm=1000,
    )
    assert results == []


# ── 7. TokenBucket in isolation — single-thread guarantee ─────────────


def test_token_bucket_single_thread_rate() -> None:
    bucket = TokenBucket(rpm=60, capacity=2)  # 1/sec, 2-burst
    # First 2 acquires should be near-instant (burst capacity).
    t0 = time.monotonic()
    bucket.acquire()
    bucket.acquire()
    burst_elapsed = time.monotonic() - t0
    assert burst_elapsed < 0.5, f"burst took {burst_elapsed:.3f}s, should be ~0"
    # Third acquire must wait ~1 second (1/sec steady rate).
    bucket.acquire()
    steady_elapsed = time.monotonic() - t0
    assert steady_elapsed >= 0.8, f"steady acquire didn't wait ({steady_elapsed:.3f}s)"
