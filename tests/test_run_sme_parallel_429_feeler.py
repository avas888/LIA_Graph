"""fix_v10_may session-mint 429 hardening — runner-level rate-limit feeler.

Verifies that scripts/eval/run_sme_parallel._RateLimit429Feeler:
  * Stays silent for non-429 responses
  * Logs a warning on the first 429
  * Trips the cancel event on the threshold-th 429
  * Is thread-safe under concurrent record() calls
"""

from __future__ import annotations

import logging
import sys
import threading

# scripts/ isn't a normal package; import the module directly.
sys.path.insert(0, "scripts/eval")

from run_sme_parallel import _RateLimit429Feeler  # type: ignore  # noqa: E402


def _silent_logger() -> logging.Logger:
    log = logging.getLogger("test_429_feeler")
    log.handlers.clear()
    log.addHandler(logging.NullHandler())
    log.propagate = False
    return log


def test_feeler_silent_on_non_429() -> None:
    feeler = _RateLimit429Feeler(threshold=2, logger=_silent_logger())
    for status in (200, 200, 500, 503, -1, 200):
        feeler.record("qid_x", status)
    assert feeler.count == 0
    assert feeler.cancelled is False


def test_feeler_first_429_warns_does_not_trip() -> None:
    feeler = _RateLimit429Feeler(threshold=2, logger=_silent_logger())
    feeler.record("q1", 429)
    assert feeler.count == 1
    assert feeler.cancelled is False
    assert feeler.sample_qids == ["q1"]


def test_feeler_threshold_429_trips_cancel() -> None:
    feeler = _RateLimit429Feeler(threshold=2, logger=_silent_logger())
    feeler.record("q1", 429)
    feeler.record("q2", 429)
    assert feeler.count == 2
    assert feeler.cancelled is True
    assert feeler.sample_qids == ["q1", "q2"]


def test_feeler_excess_429_after_trip_still_records_but_stays_cancelled() -> None:
    feeler = _RateLimit429Feeler(threshold=2, logger=_silent_logger())
    for i in range(5):
        feeler.record(f"q{i}", 429)
    assert feeler.count == 5
    assert feeler.cancelled is True


def test_feeler_threshold_zero_disables_feeler() -> None:
    """--max-429 0 must NEVER cancel (escape hatch for special debugging)."""
    feeler = _RateLimit429Feeler(threshold=0, logger=_silent_logger())
    for _ in range(20):
        feeler.record("q", 429)
    assert feeler.count == 20
    assert feeler.cancelled is False


def test_feeler_sample_qids_capped_at_10() -> None:
    feeler = _RateLimit429Feeler(threshold=999, logger=_silent_logger())
    for i in range(25):
        feeler.record(f"q{i}", 429)
    assert feeler.count == 25
    assert len(feeler.sample_qids) == 10
    assert feeler.sample_qids[0] == "q0"
    assert feeler.sample_qids[-1] == "q9"


def test_feeler_thread_safe_concurrent_record() -> None:
    """Burst 100 simultaneous 429 records from 10 threads; the count
    must be exact and the cancel event must trip exactly once at the
    threshold (i.e., no double-trip race that would log twice)."""
    feeler = _RateLimit429Feeler(threshold=10, logger=_silent_logger())
    barrier = threading.Barrier(parties=10)

    def _hammer(worker_id: int) -> None:
        barrier.wait()
        for i in range(10):
            feeler.record(f"w{worker_id}_q{i}", 429)

    threads = [threading.Thread(target=_hammer, args=(w,)) for w in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert feeler.count == 100
    assert feeler.cancelled is True
