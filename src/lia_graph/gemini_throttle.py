"""Cross-process Gemini API throttle (token bucket on a file lock).

Why this exists
---------------
The canonicalizer's parallel runner spawns N concurrent extract processes.
Each process's `VigenciaSkillHarness` makes its own Gemini calls. Without
coordination, 3 concurrent harnesses each firing a Gemini call every
~25 sec produces bursts of ~3 simultaneous in-flight calls — enough to
trigger HTTP 503 ("model overloaded") on `gemini-2.5-pro` even within
project quota. The retry path in `gemini_runtime.py` recovers from
transients but doesn't prevent them.

This module provides a SHARED, FILE-BASED rate limiter that ALL
canonicalizer Gemini calls — across ALL processes — pass through. The
result: the project-wide Gemini RPS stays under a configurable cap
regardless of how many batches run in parallel.

How it works
------------
Token bucket with a sliding time window:

  * The bucket state lives in `var/gemini_throttle_state.json` — a list
    of recent call timestamps (UTC ISO).
  * `acquire_token()` advisory-locks the state file, evicts timestamps
    older than the window, checks how many calls happened in the window,
    and either:
    - If count < cap: append a new timestamp and return immediately.
    - If count >= cap: sleep until the oldest in-window timestamp
      "expires", then retry the check.

Concurrent processes serialize through `fcntl.flock(LOCK_EX)` so the
window is consistent.

Tuning
------
Two env vars:

  * `LIA_GEMINI_GLOBAL_RPM` — calls allowed per 60-second window.
    Default 60 (= 1 RPS sustained). Set higher (e.g. 180) if you have
    headroom and want faster batch wall time.
  * `LIA_GEMINI_GLOBAL_DISABLED=1` — disable the throttle (single-batch
    runs don't need it).

Robustness
----------
  * State file race conditions: file lock is exclusive per the OS.
  * Partial-write corruption: state file is rewritten via temp + rename
    (atomic on POSIX).
  * Crash during sleep: if a process dies holding the lock, the OS
    releases it; the next process re-reads the (clean) state.
  * Logical regression: timestamps in the future / way in the past are
    filtered defensively.
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

LOGGER = logging.getLogger(__name__)

DEFAULT_STATE_PATH = Path("var/gemini_throttle_state.json")
DEFAULT_WINDOW_SECONDS = 60

# `gemini-2.5-pro` Tier 1 (paid) hard limits:
#   * 150 RPM (requests per minute)
#   * 1,000 RPD (requests per day)
#   * 1,000,000 TPM (tokens per minute)
# (source: https://ai.google.dev/gemini-api/docs/rate-limits)
#
# A canonicalizer Gemini call has ~16K chars × 2 sources + ~3K rules =
# ~10-15K tokens per call. So under TPM cap: 1M / ~12K = ~80 RPM is the
# practical ceiling; under RPM cap: 150. The TPM ceiling is the binding
# one. Default 80 RPM leaves headroom for adapter retries and other
# Gemini callers in the project (eval scripts, dependency smokes).
# Override via LIA_GEMINI_GLOBAL_RPM. The daily 1000 RPD cap is not
# enforced by this throttle — operators running 7+ batches × 150 norms
# in a day should track it separately.
DEFAULT_RPM = 80


def _read_env_int(key: str, default: int) -> int:
    raw = os.environ.get(key)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        LOGGER.warning("Invalid int for %s=%r; using default %d", key, raw, default)
        return default


def _is_disabled() -> bool:
    return os.environ.get("LIA_GEMINI_GLOBAL_DISABLED", "") == "1"


def acquire_token(
    *,
    state_path: Path | None = None,
    rpm: int | None = None,
    window_seconds: int = DEFAULT_WINDOW_SECONDS,
    max_wait_seconds: float = 120.0,
) -> None:
    """Block until a Gemini-call token is available.

    Sleeps as long as needed to stay under the configured RPM. The
    exclusive file lock ensures cross-process consistency. If the
    throttle is disabled (`LIA_GEMINI_GLOBAL_DISABLED=1`), returns
    immediately.

    Raises `TimeoutError` if `max_wait_seconds` elapses without a token.
    """

    if _is_disabled():
        return

    state_path = state_path or DEFAULT_STATE_PATH
    rpm = rpm or _read_env_int("LIA_GEMINI_GLOBAL_RPM", DEFAULT_RPM)
    state_path.parent.mkdir(parents=True, exist_ok=True)

    deadline = time.monotonic() + max_wait_seconds

    # fcntl is POSIX-only (mac/linux). On other platforms, fall back to no-op.
    try:
        import fcntl
    except ImportError:
        LOGGER.debug("fcntl unavailable — throttle disabled on this platform")
        return

    # Open or create the state file (read+write).
    flags = os.O_RDWR | os.O_CREAT
    fd = os.open(str(state_path), flags, 0o644)
    try:
        while True:
            fcntl.flock(fd, fcntl.LOCK_EX)
            try:
                # Read state (may be empty / corrupt).
                os.lseek(fd, 0, os.SEEK_SET)
                raw = os.read(fd, 65536).decode("utf-8", errors="replace").strip()
                timestamps: list[str] = []
                if raw:
                    try:
                        loaded = json.loads(raw)
                        if isinstance(loaded, list):
                            timestamps = [str(t) for t in loaded if isinstance(t, str)]
                    except json.JSONDecodeError:
                        LOGGER.warning("Throttle state corrupt; resetting")
                        timestamps = []

                now = datetime.now(timezone.utc)
                cutoff = now - timedelta(seconds=window_seconds)
                # Evict expired entries.
                kept: list[str] = []
                for ts_raw in timestamps:
                    try:
                        ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
                    except ValueError:
                        continue
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)
                    if ts > now:
                        # Future timestamp — clock skew or corruption; drop.
                        continue
                    if ts >= cutoff:
                        kept.append(ts_raw)
                timestamps = kept

                if len(timestamps) < rpm:
                    # Token available — append now, write, return.
                    timestamps.append(now.isoformat())
                    _atomic_write(state_path, fd, timestamps)
                    return

                # No token. Compute the sleep needed for the oldest entry
                # to fall outside the window.
                oldest = datetime.fromisoformat(timestamps[0].replace("Z", "+00:00"))
                if oldest.tzinfo is None:
                    oldest = oldest.replace(tzinfo=timezone.utc)
                wait = (oldest + timedelta(seconds=window_seconds) - now).total_seconds()
                wait = max(0.5, min(wait, 30.0))  # clamp to [0.5, 30]
            finally:
                fcntl.flock(fd, fcntl.LOCK_UN)

            if time.monotonic() + wait > deadline:
                raise TimeoutError(
                    f"Gemini throttle: waited too long for a token "
                    f"(window={window_seconds}s rpm={rpm} max_wait={max_wait_seconds}s)"
                )
            LOGGER.info(
                "Gemini throttle: at-cap (%d/%d in last %ds), sleeping %.1fs",
                len(timestamps), rpm, window_seconds, wait,
            )
            time.sleep(wait)
    finally:
        os.close(fd)


def _atomic_write(path: Path, fd: int, timestamps: list[str]) -> None:
    """Persist via temp + rename so a kill mid-write can't corrupt state.

    The caller still holds the exclusive flock on `fd`; readers won't
    see a partial state.
    """

    tmp = path.with_suffix(path.suffix + ".tmp")
    body = json.dumps(timestamps, ensure_ascii=False)
    tmp.write_text(body, encoding="utf-8")
    os.replace(tmp, path)


__all__ = ["acquire_token", "DEFAULT_RPM", "DEFAULT_WINDOW_SECONDS"]
