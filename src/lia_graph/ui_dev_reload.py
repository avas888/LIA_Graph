"""Dev-time reload watcher + server-info payload for `ui_server.py`.

Extracted during granularize-v2 round 16. Four pure utilities that the
main `ui_server` module orchestrates around the HTTP server lifecycle:

  * ``_best_effort_git_commit()`` — short SHA of HEAD, or ``"unknown"``.
  * ``_build_info_payload()`` — payload for the ``/__info`` endpoint;
    computes the most recent UI asset mtime across `ui/` + `frontend/`
    and surfaces the git commit + dev-boot env hints.
  * ``_build_reload_snapshot(roots)`` — filesystem snapshot of every
    `.py` / `.html` / `.js` / `.css` file under the watch roots
    (used to detect changes).
  * ``_start_reload_watcher(...)`` — background thread that polls the
    snapshot on an interval and calls `server.shutdown()` when a change
    is detected, driving the outer auto-restart loop.

No side effects at import time. Host re-imports these names for
back-compat with existing call sites.
"""

from __future__ import annotations

import os
import subprocess
import threading
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any


_RELOAD_WATCH_SUFFIXES = {".py", ".html", ".js", ".css"}


def _best_effort_git_commit(workspace_root: Path) -> str:
    try:
        output = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=workspace_root,
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except Exception:  # noqa: BLE001
        return "unknown"
    return str(output or "").strip() or "unknown"


def _build_info_payload(
    *,
    server_started_at: str,
    workspace_root: Path,
    ui_dir: Path,
    frontend_dir: Path,
) -> dict[str, Any]:
    ui_asset_mtime = ""
    latest_mtime = 0.0
    candidate_roots = (ui_dir, frontend_dir)
    for root in candidate_roots:
        if not root.exists() or not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in {".html", ".css", ".js", ".ts", ".json"}:
                continue
            try:
                stat = path.stat()
            except OSError:
                continue
            latest_mtime = max(latest_mtime, stat.st_mtime)
    if latest_mtime > 0:
        ui_asset_mtime = datetime.fromtimestamp(latest_mtime, tz=timezone.utc).isoformat()
    reset_chat_on_dev_boot = str(os.environ.get("LIA_RESET_CHAT_ON_DEV_BOOT") or "").strip() == "1"
    dev_boot_nonce = str(os.environ.get("LIA_DEV_BOOT_NONCE") or "").strip()
    return {
        "server_started_at": server_started_at,
        "git_commit": _best_effort_git_commit(workspace_root),
        "app_version": "lia-ui-1",
        "ui_asset_mtime": ui_asset_mtime,
        "reset_chat_on_dev_boot": reset_chat_on_dev_boot,
        "dev_boot_nonce": dev_boot_nonce,
    }


def _build_reload_snapshot(roots: tuple[Path, ...]) -> tuple[tuple[str, int, int], ...]:
    rows: list[tuple[str, int, int]] = []
    for root in roots:
        if not root.exists() or not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in _RELOAD_WATCH_SUFFIXES:
                continue
            try:
                stat = path.stat()
            except OSError:
                continue
            rows.append((str(path), int(stat.st_mtime_ns), int(stat.st_size)))
    rows.sort()
    return tuple(rows)


def _start_reload_watcher(
    *,
    server: ThreadingHTTPServer,
    watch_roots: tuple[Path, ...],
    interval_seconds: float,
    emit_audit_event: Any,
) -> tuple[threading.Event, threading.Event, threading.Thread]:
    stop_event = threading.Event()
    reload_event = threading.Event()
    baseline = _build_reload_snapshot(watch_roots)

    def _watch_loop() -> None:
        nonlocal baseline
        while not stop_event.wait(interval_seconds):
            current = _build_reload_snapshot(watch_roots)
            if current == baseline:
                continue
            reload_event.set()
            emit_audit_event(
                "ui_server.reload_requested",
                {
                    "watch_roots": [str(root) for root in watch_roots],
                    "interval_seconds": interval_seconds,
                },
            )
            try:
                server.shutdown()
            except OSError:
                pass
            return

    watcher = threading.Thread(target=_watch_loop, name="lia-ui-reloader", daemon=True)
    watcher.start()
    return stop_event, reload_event, watcher
