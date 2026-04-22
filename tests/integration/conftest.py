"""Shared fixtures + gating for integration tests.

Gate: ``LIA_INTEGRATION=1`` env var OR ``--integration`` flag is required
to run these. The tests also require a live local FalkorDB at the
``FALKORDB_URL`` endpoint.

Without both, every integration test is skipped (so CI and the default
``pytest`` run stay green).
"""
from __future__ import annotations

import os
import socket
from urllib.parse import urlparse

import pytest


def _integration_enabled() -> bool:
    flag = os.environ.get("LIA_INTEGRATION", "").strip().lower()
    return flag in {"1", "true", "yes", "on"}


def _falkor_reachable() -> bool:
    raw = os.environ.get("FALKORDB_URL", "").strip()
    if not raw:
        raw = "redis://localhost:6389"
    parsed = urlparse(raw if "://" in raw else f"redis://{raw}")
    host = parsed.hostname or "localhost"
    port = parsed.port or 6379
    try:
        with socket.create_connection((host, port), timeout=1.5):
            return True
    except OSError:
        return False


@pytest.fixture(autouse=True, scope="session")
def _skip_when_integration_disabled() -> None:
    if not _integration_enabled():
        pytest.skip(
            "integration tests disabled — set LIA_INTEGRATION=1 to run",
            allow_module_level=True,
        )
    if not _falkor_reachable():
        pytest.skip(
            "FalkorDB docker not reachable at FALKORDB_URL — "
            "skipping integration tests",
            allow_module_level=True,
        )


@pytest.fixture(autouse=True, scope="session")
def _isolate_falkor_test_graph() -> None:
    """Point Falkor writes at a dedicated test graph for the duration of the
    session.

    The integration fixtures run destructive operations (wipe SubTopicNodes,
    re-MERGE) that MUST NOT touch the production graph the single-pass
    ingest wrote into. Before this fixture existed, every
    ``make phase2-graph-artifacts-smoke`` run wiped the freshly-ingested
    SubTopicNodes from ``LIA_REGULATORY_GRAPH`` — the exact opposite of
    what a preflight canary should do.

    We override ``FALKORDB_GRAPH`` to ``LIA_REGULATORY_GRAPH_TEST`` for the
    session and restore it on teardown. ``GraphClient.from_env()`` then
    connects to the isolated graph automatically.
    """
    prev = os.environ.get("FALKORDB_GRAPH")
    os.environ["FALKORDB_GRAPH"] = "LIA_REGULATORY_GRAPH_TEST"
    try:
        yield
    finally:
        if prev is None:
            os.environ.pop("FALKORDB_GRAPH", None)
        else:
            os.environ["FALKORDB_GRAPH"] = prev
