"""Tests for the env_posture guard (Phase A3)."""
from __future__ import annotations

import pytest

from lia_graph import env_posture
from lia_graph.env_posture import (
    EnvPostureError,
    assert_local_posture,
    describe_posture,
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("FALKORDB_URL", raising=False)


def test_local_urls_pass(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("SUPABASE_URL", "http://127.0.0.1:54321")
    monkeypatch.setenv("FALKORDB_URL", "redis://localhost:6389")
    # Redirect the event log path to a temp dir to keep tests hermetic.
    monkeypatch.setattr(
        "lia_graph.env_posture.emit_event",
        lambda *a, **k: None,
    )
    snapshot = assert_local_posture()
    assert snapshot["posture"] == "local"
    assert snapshot["supabase_host"] == "127.0.0.1"
    assert snapshot["falkor_host"] == "localhost"


def test_cloud_supabase_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "https://abcd1234.supabase.co")
    monkeypatch.setenv("FALKORDB_URL", "redis://localhost:6389")
    monkeypatch.setattr("lia_graph.env_posture.emit_event", lambda *a, **k: None)
    with pytest.raises(EnvPostureError) as exc_info:
        assert_local_posture()
    assert "cloud host" in str(exc_info.value)
    assert "supabase.co" in str(exc_info.value)


def test_cloud_falkor_marker_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "http://127.0.0.1:54321")
    monkeypatch.setenv("FALKORDB_URL", "redis://falkor.railway.app:6389")
    monkeypatch.setattr("lia_graph.env_posture.emit_event", lambda *a, **k: None)
    with pytest.raises(EnvPostureError) as exc_info:
        assert_local_posture()
    assert "FALKORDB_URL" in str(exc_info.value)


def test_describe_posture_parses_hosts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "http://127.0.0.1:54321/rest/v1")
    monkeypatch.setenv("FALKORDB_URL", "redis://localhost:6389")
    snapshot = describe_posture()
    assert snapshot == {
        "supabase_host": "127.0.0.1",
        "falkor_host": "localhost",
        "supabase_class": "local",
        "falkor_class": "local",
        "posture": "local",
    }


def test_unset_supabase_raises_when_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FALKORDB_URL", "redis://localhost:6389")
    monkeypatch.setattr("lia_graph.env_posture.emit_event", lambda *a, **k: None)
    with pytest.raises(EnvPostureError):
        assert_local_posture(require_supabase=True, require_falkor=False)


def test_emit_event_called_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "http://127.0.0.1:54321")
    monkeypatch.setenv("FALKORDB_URL", "redis://localhost:6389")
    calls: list[tuple[str, dict]] = []
    monkeypatch.setattr(
        "lia_graph.env_posture.emit_event",
        lambda name, payload, *a, **k: calls.append((name, payload)),
    )
    assert_local_posture()
    assert len(calls) == 1
    assert calls[0][0] == "env.posture.asserted"
    assert calls[0][1]["posture"] == "local"
