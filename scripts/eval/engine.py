"""Shared runner engine for chat-based evaluation harnesses.

Lifts the byte-for-byte duplicated plumbing that lived in
`scripts/run_100qs_eval.py` and
`scripts/evaluations/run_multiturn_dialogue_harness.py` into one home so
new harnesses (e.g. `scripts/eval/run_sme_validation.py`) don't grow a
third copy.

What's in here:
    * `ChatClient`        — HTTP POST to `/api/chat` with optional public
                            session token (Bearer auth).
    * `post_json`         — generic JSON POST helper that returns
                            `(status, payload)`; tolerates HTTPError
                            bodies, JSON or otherwise.
    * `load_jsonl` / `append_jsonl` — JSONL IO with fsync on append.
    * `completed_ids`    — resume support for runs whose rows carry an
                            `id` field and `ok=True` flag.
    * `utc_iso`, `utc_iso_compact`, `bogota_now_human` — timestamp
                            helpers, Bogotá AM/PM per repo convention.
    * `git_sha`           — captures `HEAD` for manifests.
    * `write_manifest`    — atomic JSON write with newline tail.

What's NOT in here (intentionally):
    * Per-harness fixture parsing and per-harness diagnostic extraction.
      Each harness owns its own row shape; the engine only moves bytes.

Stdlib only — drop-in for any script that needs to hit `/api/chat` and
write resumable JSONL output.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


_BOGOTA = _dt.timezone(_dt.timedelta(hours=-5), name="America/Bogota")

DEFAULT_TIMEOUT_SECONDS = 90.0


# ── Time helpers ─────────────────────────────────────────────────────────


def utc_iso() -> str:
    """ISO 8601 UTC timestamp with timezone suffix (machine-readable)."""
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def utc_iso_compact() -> str:
    """Filename-safe UTC stamp: `YYYYMMDDTHHMMSSZ`."""
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def bogota_now_human() -> str:
    """Human-facing timestamp: `2026-04-26 7:14:50 PM Bogotá`."""
    return (
        _dt.datetime.now(_BOGOTA)
        .strftime("%Y-%m-%d %I:%M:%S %p Bogotá")
    )


# ── HTTP ─────────────────────────────────────────────────────────────────


def post_json(
    url: str,
    body: dict[str, Any],
    *,
    headers: dict[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> tuple[int, dict[str, Any]]:
    """POST JSON, return `(http_status, parsed_json)`.

    Tolerates non-200 responses (returns the parsed error payload when
    available, or `{"_raw_body": "..."}` when the body wasn't JSON).
    Network/transport errors are NOT caught here — callers decide
    whether to log-and-continue or abort.
    """
    data = json.dumps(body).encode("utf-8")
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
    req = Request(url, data=data, headers=req_headers, method="POST")
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            payload = _safe_json(raw)
            return int(resp.status), payload
    except HTTPError as exc:
        try:
            body_text = exc.read().decode("utf-8")
        except Exception:  # noqa: BLE001
            body_text = ""
        return int(exc.code), _safe_json(body_text)


def _safe_json(raw: str) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {"_raw_body": raw}
    if isinstance(parsed, dict):
        return parsed
    return {"_raw_body": raw}


@dataclass
class ChatClient:
    """Minimal client for `/api/chat`.

    Optional Bearer auth via `/api/public/session` for harnesses hitting
    the Vite-proxied port (5173); set `auth=False` for direct calls to
    the `lia-ui` server (8787 by default), which doesn't gate `/api/chat`.
    """

    base_url: str
    auth: bool = True
    timeout: float = DEFAULT_TIMEOUT_SECONDS
    pais: str = "colombia"

    def __post_init__(self) -> None:
        self.base_url = self.base_url.rstrip("/")
        self._auth_headers: dict[str, str] = {}

    # -- session ---------------------------------------------------------

    def ensure_session(self) -> None:
        """Mint a public session token if `auth=True` and we don't have one yet.

        Safe to call repeatedly; subsequent calls are no-ops.
        """
        if not self.auth or self._auth_headers:
            return
        status, payload = post_json(
            f"{self.base_url}/api/public/session",
            {},
            timeout=self.timeout,
        )
        if status != 200 or not payload.get("ok"):
            raise RuntimeError(
                f"/api/public/session failed: status={status} payload={payload}"
            )
        token = str(payload.get("token") or "").strip()
        if not token:
            raise RuntimeError("/api/public/session returned no token")
        self._auth_headers = {"Authorization": f"Bearer {token}"}

    # -- request ---------------------------------------------------------

    def chat(
        self,
        message: str,
        *,
        session_id: str | None = None,
        topic: str | None = None,
        extra_body: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> tuple[int, dict[str, Any]]:
        """POST to `/api/chat`. Returns `(http_status, parsed_payload)`."""
        self.ensure_session()
        body: dict[str, Any] = {"message": message, "pais": self.pais}
        if session_id:
            body["session_id"] = session_id
        if topic:
            body["topic"] = topic
        if extra_body:
            body.update(extra_body)
        return post_json(
            f"{self.base_url}/api/chat",
            body,
            headers=self._auth_headers or None,
            timeout=timeout if timeout is not None else self.timeout,
        )


# ── JSONL IO ─────────────────────────────────────────────────────────────


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read a JSONL file, skipping blank lines and `#` comment lines."""
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, start=1):
            stripped = raw.strip()
            if not stripped or stripped.startswith("#"):
                continue
            try:
                rows.append(json.loads(stripped))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path} line {lineno} invalid JSON: {exc}") from exc
    return rows


def iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    """Stream JSONL rows without loading the whole file into memory."""
    with path.open("r", encoding="utf-8") as fh:
        for raw in fh:
            stripped = raw.strip()
            if not stripped or stripped.startswith("#"):
                continue
            try:
                yield json.loads(stripped)
            except json.JSONDecodeError:
                continue


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    """Atomically append one JSON object to a JSONL file (fsync best-effort)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(row, ensure_ascii=False) + "\n"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line)
        fh.flush()
        try:
            os.fsync(fh.fileno())
        except OSError:
            pass


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    """Truncate-and-write JSONL; returns count written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += 1
    return n


def completed_ids(output_jsonl: Path, *, id_field: str = "id") -> set[str]:
    """Return the set of `id_field` values already captured with `ok=True`.

    Used by resumable runners — re-running with the same output path skips
    rows that already succeeded.
    """
    if not output_jsonl.exists():
        return set()
    ids: set[str] = set()
    for row in iter_jsonl(output_jsonl):
        if not row.get("ok"):
            continue
        ident = str(row.get(id_field) or "").strip()
        if ident:
            ids.add(ident)
    return ids


# ── Manifest ─────────────────────────────────────────────────────────────


def git_sha(repo_root: Path | None = None) -> str | None:
    """Return current `HEAD` SHA, or `None` if `git` isn't available."""
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            cwd=str(repo_root) if repo_root else None,
        )
        return out.decode("ascii").strip()
    except Exception:  # noqa: BLE001
        return None


def write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    """Write a manifest JSON with trailing newline."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
