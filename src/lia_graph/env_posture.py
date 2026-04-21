"""Local-vs-cloud env posture guard.

Phase A3 of ingestfix-v2-maximalist. Prevents the silent-risk mode
where a misconfigured ``.env.local`` pointing at cloud Supabase lets a
"local WIP backfill" write LLM classifier output into cloud production
under the wrong key.

Any script that asserts "this is a local-only run" should call
``assert_local_posture()`` near the top of ``main()`` — it raises
``EnvPostureError`` the moment it detects a non-local hostname on
``SUPABASE_URL`` or ``FALKORDB_URL``. An explicit escape hatch,
``--allow-non-local-env``, lets cloud runs opt out.
"""
from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlparse

from .instrumentation import emit_event

_LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost", "::1", "0.0.0.0"})

# Non-local markers that identify cloud providers even if the hostname is
# unfamiliar: covers supabase.co, .supabase.net, AWS, Railway.app, *.cloud,
# etc. We only check the first match — if the parsed host already resolves
# as `_LOCAL_HOSTS`, we never look at this list.
_CLOUD_HOST_MARKERS: tuple[str, ...] = (
    "supabase.co",
    "supabase.net",
    ".aws",
    ".cloud",
    "railway.app",
    "amazonaws.com",
)


class EnvPostureError(RuntimeError):
    """Raised when env URLs resolve to a non-local host during a local-only run."""


def _host_from_url(raw: str | None) -> str:
    if not raw:
        return ""
    value = raw.strip()
    if not value:
        return ""
    try:
        parsed = urlparse(value if "://" in value else f"//{value}", scheme="http")
    except ValueError:
        return ""
    host = (parsed.hostname or "").lower()
    if not host and "://" not in value:
        # redis://localhost:6389 style already handled by urlparse, but bare
        # "localhost:5432" falls through — extract the prefix.
        host = value.split(":", 1)[0].lower()
    return host


def _classify_host(host: str) -> str:
    if not host:
        return "unset"
    if host in _LOCAL_HOSTS:
        return "local"
    for marker in _CLOUD_HOST_MARKERS:
        if marker in host:
            return "cloud"
    # Docker-compose-internal names (no dots) count as local; public FQDNs
    # (with dots) that we can't identify are treated as cloud for safety.
    if "." not in host:
        return "local"
    return "cloud"


def describe_posture() -> dict[str, str]:
    """Return the parsed Supabase + Falkor hosts and the aggregate posture."""
    supabase_host = _host_from_url(os.environ.get("SUPABASE_URL"))
    falkor_host = _host_from_url(os.environ.get("FALKORDB_URL"))
    supabase_class = _classify_host(supabase_host)
    falkor_class = _classify_host(falkor_host)
    if "cloud" in {supabase_class, falkor_class}:
        posture = "cloud"
    elif supabase_class == "unset" and falkor_class == "unset":
        posture = "unset"
    else:
        posture = "local"
    return {
        "supabase_host": supabase_host,
        "falkor_host": falkor_host,
        "supabase_class": supabase_class,
        "falkor_class": falkor_class,
        "posture": posture,
    }


def assert_local_posture(
    *,
    require_supabase: bool = True,
    require_falkor: bool = True,
    emit: bool = True,
) -> dict[str, str]:
    """Raise ``EnvPostureError`` when env URLs resolve to non-local hosts.

    Args:
        require_supabase: when True, an ``unset`` SUPABASE_URL also raises.
        require_falkor: when True, an ``unset`` FALKORDB_URL also raises.
        emit: when True, emits ``env.posture.asserted`` trace event.
    """
    snapshot = describe_posture()
    problems: list[str] = []
    if snapshot["supabase_class"] == "cloud":
        problems.append(
            f"SUPABASE_URL points at cloud host {snapshot['supabase_host']!r}"
        )
    elif snapshot["supabase_class"] == "unset" and require_supabase:
        problems.append("SUPABASE_URL is not set")

    if snapshot["falkor_class"] == "cloud":
        problems.append(
            f"FALKORDB_URL points at cloud host {snapshot['falkor_host']!r}"
        )
    elif snapshot["falkor_class"] == "unset" and require_falkor:
        problems.append("FALKORDB_URL is not set")

    if emit:
        emit_event(
            "env.posture.asserted",
            {
                "supabase_host": snapshot["supabase_host"],
                "falkor_host": snapshot["falkor_host"],
                "posture": snapshot["posture"],
            },
        )

    if problems:
        raise EnvPostureError(
            "Local-env posture guard failed: "
            + "; ".join(problems)
            + ". Fix the .env file, or pass --allow-non-local-env to bypass."
        )
    return snapshot


__all__ = [
    "EnvPostureError",
    "assert_local_posture",
    "describe_posture",
]
