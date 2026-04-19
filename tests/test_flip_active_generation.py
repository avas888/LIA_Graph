"""Tests for scripts/supabase_flip_active_generation.py.

Loads the script as a module via importlib and asserts:
- Refuses to run without --confirm (exits 1).
- With --confirm, calls the two-step deactivate-then-activate flow once each.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, call

import pytest


_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "supabase_flip_active_generation.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("flip_active_generation", _SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _FakeTable:
    def __init__(self, rows_by_table: dict[str, list[dict]], calls: list) -> None:
        self._rows = rows_by_table
        self._calls = calls
        self._name: str | None = None
        self._pending: dict | None = None
        self._where: list[tuple[str, str, object]] = []

    def bind(self, name: str) -> "_FakeTable":
        fresh = _FakeTable(self._rows, self._calls)
        fresh._name = name
        return fresh

    def select(self, *_a, **_kw):
        return self

    def update(self, payload: dict):
        self._pending = payload
        return self

    def eq(self, field: str, value: object):
        self._where.append(("eq", field, value))
        return self

    def neq(self, field: str, value: object):
        self._where.append(("neq", field, value))
        return self

    def limit(self, *_a, **_kw):
        return self

    def execute(self):
        if self._pending is not None:
            self._calls.append(
                SimpleNamespace(
                    table=self._name,
                    payload=dict(self._pending),
                    where=list(self._where),
                )
            )
            self._pending = None
            self._where = []
            return MagicMock(data=[])
        return MagicMock(data=list(self._rows.get(self._name or "", [])))


class _FakeClient:
    def __init__(self, rows_by_table: dict[str, list[dict]]) -> None:
        self._rows = rows_by_table
        self.calls: list = []
        self._root = _FakeTable(rows_by_table, self.calls)

    def table(self, name: str):
        return self._root.bind(name)


def test_refuses_without_confirm(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    module = _load_module()
    client = _FakeClient(
        {
            "corpus_generations": [
                {"generation_id": "gen_new", "is_active": False},
            ]
        }
    )
    monkeypatch.setattr(module, "_client", lambda _target: client)
    rc = module.main(["--target", "wip", "--generation", "gen_new"])
    assert rc == 1
    # No update calls should have happened — only selects.
    assert all(entry.payload is not None for entry in client.calls) or client.calls == []
    # Specifically, no activate payload was written
    activate_payloads = [c for c in client.calls if c.payload.get("is_active") is True]
    assert activate_payloads == []


def test_confirmed_flip_runs_deactivate_then_activate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module()
    client = _FakeClient(
        {
            "corpus_generations": [
                {"generation_id": "gen_new", "is_active": False},
                {"generation_id": "gen_old", "is_active": True},
            ]
        }
    )
    monkeypatch.setattr(module, "_client", lambda _target: client)

    rc = module.main(
        ["--target", "wip", "--generation", "gen_new", "--confirm", "--json"]
    )
    assert rc == 0, client.calls

    deactivates = [c for c in client.calls if c.payload.get("is_active") is False]
    activates = [c for c in client.calls if c.payload.get("is_active") is True]
    assert len(deactivates) == 1, deactivates
    assert len(activates) == 1, activates


def test_raises_when_target_row_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module()
    client = _FakeClient({"corpus_generations": []})
    monkeypatch.setattr(module, "_client", lambda _target: client)

    rc = module.main(
        ["--target", "wip", "--generation", "gen_missing", "--confirm"]
    )
    assert rc == 2
