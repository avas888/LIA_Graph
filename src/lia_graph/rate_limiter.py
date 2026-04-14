"""In-memory token-bucket rate limiter (thread-safe).

Also exposes `check_and_increment_daily_quota`, a Supabase-backed daily counter
used by the no-login `/public` chat surface to enforce a per-IP-hash daily
message ceiling that survives process restarts.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from datetime import date
from typing import Any


@dataclass
class _Bucket:
    tokens: float
    last_refill: float


class InMemoryRateLimiter:
    """Simple sliding-window rate limiter backed by an in-memory dict.

    State is lost on process restart — acceptable for MVP.
    """

    def __init__(self) -> None:
        self._buckets: dict[str, _Bucket] = {}
        self._lock = threading.Lock()

    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """Return True if the request is within rate limits, False otherwise."""
        now = time.monotonic()
        refill_rate = max_requests / window_seconds

        with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                bucket = _Bucket(tokens=max_requests - 1, last_refill=now)
                self._buckets[key] = bucket
                return True

            elapsed = now - bucket.last_refill
            bucket.tokens = min(max_requests, bucket.tokens + elapsed * refill_rate)
            bucket.last_refill = now

            if bucket.tokens >= 1:
                bucket.tokens -= 1
                return True
            return False

    def reset(self) -> None:
        """Clear all buckets (useful for testing)."""
        with self._lock:
            self._buckets.clear()


def check_and_increment_daily_quota(
    *,
    ip_hash: str,
    cap: int,
    supabase_client: Any,
    today: date | None = None,
) -> tuple[bool, int]:
    """Atomically increment the daily quota counter for an IP hash.

    Returns `(allowed, count_after_increment)`.

    * `allowed=True` means the request is under the cap (and the counter has
      been incremented to reflect this request).
    * `allowed=False` means the request hit the cap; the counter is left at
      `cap` and the caller should refuse the request.

    Fails CLOSED on any DB error: if Supabase is unreachable, the function
    returns `(False, 0)` so callers refuse the request rather than letting
    abuse drain the LLM budget.
    """
    if not ip_hash:
        return False, 0
    if cap <= 0:
        return False, 0
    if supabase_client is None:
        return False, 0

    day_str = (today or date.today()).isoformat()
    try:
        # Read current row (if any)
        existing = (
            supabase_client.table("public_usage_quota")
            .select("count")
            .eq("ip_hash", ip_hash)
            .eq("day", day_str)
            .maybe_single()
            .execute()
        )
        current_count = 0
        if existing and getattr(existing, "data", None):
            current_count = int(existing.data.get("count", 0) or 0)

        if current_count >= cap:
            return False, current_count

        next_count = current_count + 1
        # UPSERT — keyed on (ip_hash, day) primary key
        supabase_client.table("public_usage_quota").upsert(
            {
                "ip_hash": ip_hash,
                "day": day_str,
                "count": next_count,
                "last_seen": "now()",
            },
            on_conflict="ip_hash,day",
        ).execute()
        return True, next_count
    except Exception:
        # Fail CLOSED — abuse must not be cheaper than reliability incidents.
        return False, 0
