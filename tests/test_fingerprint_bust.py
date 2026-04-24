"""Tests for ``scripts/fingerprint_bust.py``.

The bust tool mutates ``documents.doc_fingerprint`` on production Supabase.
Its safety rails (``--dry-run`` default, mandatory ``--confirm``,
``--force-multi`` for multi-topic runs, 200-row soft threshold) are the
only thing stopping a typo from nullifying 6,730 fingerprints. These
tests fence every rail AND lock the manifest-before-execute invariant so
a mid-UPDATE crash always leaves an audit trail.

Mirrors the ``_FakeClient`` pattern from ``test_dangling_store.py`` and
extends it with ``.is_()`` (needed for ``retired_at IS NULL``) and
``.update()`` (needed for the NULL-fingerprint write).
"""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

# ``scripts/fingerprint_bust.py`` is a flat CLI file, not an installed
# package. Load it via importlib so tests can exercise the pure functions
# without touching a real Supabase client.
_SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "scripts"
    / "monitoring"
    / "monitor_ingest_topic_batches"
    / "fingerprint_bust.py"
)
_spec = importlib.util.spec_from_file_location("fingerprint_bust", _SCRIPT)
assert _spec is not None and _spec.loader is not None
fingerprint_bust = importlib.util.module_from_spec(_spec)
sys.modules["fingerprint_bust"] = fingerprint_bust
_spec.loader.exec_module(fingerprint_bust)  # type: ignore[union-attr]


# ── Minimal supabase fake ────────────────────────────────────────────


@dataclass
class _Execute:
    data: list[dict[str, Any]]


class _Query:
    def __init__(
        self,
        parent: "_Table",
        op: str,
        payload: Any = None,
    ) -> None:
        self._parent = parent
        self._op = op
        self._payload = payload
        self._filters: list[tuple[str, str, Any]] = []
        self._columns: str | None = None

    def select(self, columns: str) -> "_Query":
        self._columns = columns
        return self

    def in_(self, column: str, values: list[Any]) -> "_Query":
        self._filters.append(("in_", column, list(values)))
        return self

    def is_(self, column: str, value: Any) -> "_Query":
        # PostgREST `is_("retired_at", "null")` — value is the literal
        # string "null". The fake honors the same contract.
        self._filters.append(("is_", column, value))
        return self

    def _matches(self, row: dict[str, Any]) -> bool:
        for op, column, value in self._filters:
            if op == "in_":
                if row.get(column) not in value:
                    return False
            elif op == "is_":
                cell = row.get(column)
                if str(value).lower() == "null":
                    if cell is not None:
                        return False
                else:
                    if cell != value:
                        return False
        return True

    def execute(self) -> _Execute:
        rows = self._parent.rows
        if self._op == "select":
            picked: list[dict[str, Any]] = []
            for r in rows:
                if self._matches(r):
                    picked.append({k: r.get(k) for k in self._cols_list()})
            return _Execute(picked)
        if self._op == "update":
            touched: list[dict[str, Any]] = []
            for r in rows:
                if self._matches(r):
                    r.update(self._payload or {})
                    touched.append(dict(r))
            return _Execute(touched)
        return _Execute([])

    def _cols_list(self) -> list[str]:
        if not self._columns:
            return []
        return [c.strip() for c in self._columns.split(",") if c.strip()]


class _Table:
    def __init__(
        self,
        name: str,
        rows: list[dict[str, Any]],
        client: "_FakeClient",
    ) -> None:
        self.name = name
        self.rows = rows
        self._client = client

    def select(self, columns: str) -> _Query:
        self._client.calls.append(("select", self.name, 0))
        q = _Query(self, "select")
        q.select(columns)
        return q

    def update(self, payload: dict[str, Any]) -> _Query:
        self._client.calls.append(("update", self.name, len(payload)))
        return _Query(self, "update", payload=payload)


class _FakeClient:
    def __init__(self, seed: dict[str, list[dict[str, Any]]] | None = None) -> None:
        self._rows: dict[str, list[dict[str, Any]]] = {}
        for name, rows in (seed or {}).items():
            self._rows[name] = [dict(r) for r in rows]
        self.calls: list[tuple[str, str, int]] = []

    def table(self, name: str) -> _Table:
        if name not in self._rows:
            self._rows[name] = []
        return _Table(name, self._rows[name], self)

    def rows(self, name: str) -> list[dict[str, Any]]:
        return self._rows.get(name, [])

    def count_calls(self, op: str, table: str | None = None) -> int:
        return sum(
            1 for (o, t, _n) in self.calls
            if o == op and (table is None or t == table)
        )


def _seed_documents(
    *,
    live_by_topic: dict[str, int],
    retired_by_topic: dict[str, int] | None = None,
) -> list[dict[str, Any]]:
    """Produce a fixture of ``documents`` rows with predictable doc_ids.

    Live rows get an arbitrary non-null fingerprint so the test can verify
    the bust nulls it; retired rows get a fingerprint too but should never
    be touched (their ``retired_at`` filters them out of the SELECT).
    """
    rows: list[dict[str, Any]] = []
    for tema, n in live_by_topic.items():
        for i in range(n):
            rows.append(
                {
                    "doc_id": f"doc_{tema}_{i:03d}",
                    "tema": tema,
                    "doc_fingerprint": f"fp_{tema}_{i:03d}",
                    "retired_at": None,
                }
            )
    for tema, n in (retired_by_topic or {}).items():
        for i in range(n):
            rows.append(
                {
                    "doc_id": f"doc_{tema}_retired_{i:03d}",
                    "tema": tema,
                    "doc_fingerprint": f"fp_ret_{tema}_{i:03d}",
                    "retired_at": "2026-04-01T00:00:00Z",
                }
            )
    return rows


# ── Tests ────────────────────────────────────────────────────────────


def test_dry_run_reports_count_does_not_mutate(tmp_path: Path) -> None:
    client = _FakeClient(
        seed={"documents": _seed_documents(live_by_topic={"laboral": 7})}
    )
    outcome = fingerprint_bust.run_bust(
        client,
        topics=["laboral"],
        target="production",
        dry_run=True,
        confirm=False,  # explicitly NOT confirmed — dry-run bypasses confirm rule
        force_multi=False,
        manifest_dir=tmp_path,
        tag="laboral",
    )
    assert outcome.dry_run is True
    assert outcome.rows_updated == 0
    assert outcome.plan.row_count == 7
    # Verify no UPDATE call was issued.
    assert client.count_calls("update") == 0
    # Verify the doc_fingerprint values are unchanged.
    for r in client.rows("documents"):
        assert r["doc_fingerprint"] is not None
    # Manifest was still written.
    assert outcome.manifest_path.exists()


def test_single_topic_bust_sets_fingerprint_null(tmp_path: Path) -> None:
    client = _FakeClient(
        seed={
            "documents": _seed_documents(
                live_by_topic={"laboral": 5, "iva": 3},
                retired_by_topic={"laboral": 2},  # must NOT be touched
            )
        }
    )
    outcome = fingerprint_bust.run_bust(
        client,
        topics=["laboral"],
        target="production",
        dry_run=False,
        confirm=True,
        force_multi=False,
        manifest_dir=tmp_path,
        tag="laboral",
    )
    assert outcome.dry_run is False
    assert outcome.plan.row_count == 5
    assert outcome.rows_updated == 5

    # Live-laboral rows: fingerprint now NULL.
    for r in client.rows("documents"):
        if r["tema"] == "laboral" and r["retired_at"] is None:
            assert r["doc_fingerprint"] is None
        elif r["tema"] == "laboral" and r["retired_at"] is not None:
            # Retired rows untouched.
            assert r["doc_fingerprint"] is not None
        else:
            # iva rows untouched.
            assert r["tema"] == "iva"
            assert r["doc_fingerprint"] is not None


def test_multi_topic_requires_force_multi_flag(tmp_path: Path) -> None:
    client = _FakeClient(
        seed={"documents": _seed_documents(live_by_topic={"laboral": 1, "iva": 1})}
    )
    with pytest.raises(fingerprint_bust.UnsafeBustError) as excinfo:
        fingerprint_bust.run_bust(
            client,
            topics=["laboral", "iva"],
            target="production",
            dry_run=False,
            confirm=True,
            force_multi=False,  # offense: two topics, no --force-multi
            manifest_dir=tmp_path,
            tag="mixed",
        )
    assert "force-multi" in str(excinfo.value).lower()
    # No I/O happened — SELECT never ran.
    assert client.count_calls("select") == 0
    assert client.count_calls("update") == 0


def test_non_dry_run_requires_confirm(tmp_path: Path) -> None:
    client = _FakeClient(
        seed={"documents": _seed_documents(live_by_topic={"laboral": 3})}
    )
    with pytest.raises(fingerprint_bust.UnsafeBustError) as excinfo:
        fingerprint_bust.run_bust(
            client,
            topics=["laboral"],
            target="production",
            dry_run=False,
            confirm=False,  # offense: non-dry without --confirm
            force_multi=False,
            manifest_dir=tmp_path,
            tag="laboral",
        )
    assert "--confirm" in str(excinfo.value)


def test_safety_threshold_rejects_huge_count(tmp_path: Path) -> None:
    """``--confirm`` is mandatory regardless of count, but the explicit
    threshold-exceeded message is what operators see when they try to bust
    a megatopic without thinking. Exercises the distinct error path that
    Phase 3.0 G-check G9 relies on.
    """
    # 250 live laboral docs — above the 200-row threshold.
    client = _FakeClient(
        seed={"documents": _seed_documents(live_by_topic={"laboral": 250})}
    )
    # Bypass flag-rules check by explicitly invoking the row-count rule
    # with a pre-resolved plan: this test exercises enforce_row_count_rule
    # directly to lock the "huge count" branch wording.
    plan = fingerprint_bust.resolve_affected_docs(
        client, topics=["laboral"], target="production"
    )
    assert plan.row_count == 250
    with pytest.raises(fingerprint_bust.UnsafeBustError) as excinfo:
        fingerprint_bust.enforce_row_count_rule(
            plan, confirm=False, dry_run=False
        )
    msg = str(excinfo.value)
    assert "250" in msg
    assert "200" in msg  # threshold mentioned explicitly
    assert "refus" in msg.lower()


def test_manifest_written_before_execute(tmp_path: Path) -> None:
    """If the UPDATE crashes mid-flight, the manifest must already exist."""
    client = _FakeClient(
        seed={"documents": _seed_documents(live_by_topic={"laboral": 3})}
    )

    # Monkey-patch null_fingerprints to simulate a mid-flight crash.
    original = fingerprint_bust.null_fingerprints

    def _exploding(client: Any, *, doc_ids: Any) -> int:
        raise RuntimeError("simulated httpx.InvalidURL mid-UPDATE")

    fingerprint_bust.null_fingerprints = _exploding  # type: ignore[assignment]
    try:
        with pytest.raises(RuntimeError):
            fingerprint_bust.run_bust(
                client,
                topics=["laboral"],
                target="production",
                dry_run=False,
                confirm=True,
                force_multi=False,
                manifest_dir=tmp_path,
                tag="laboral",
            )
    finally:
        fingerprint_bust.null_fingerprints = original  # type: ignore[assignment]

    # Manifest exists even though the UPDATE exploded.
    manifests = list(tmp_path.glob("*_laboral.json"))
    assert len(manifests) == 1
    import json as _json
    payload = _json.loads(manifests[0].read_text(encoding="utf-8"))
    assert payload["row_count"] == 3
    assert len(payload["doc_ids"]) == 3
    assert payload["dry_run"] is False


def test_cli_rejects_both_topic_and_topics() -> None:
    # argparse's mutually_exclusive_group handles this at parse time.
    parser = fingerprint_bust.build_argparser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--topic", "laboral", "--topics", "iva,renta"])


def test_cli_help_advertises_all_required_flags() -> None:
    parser = fingerprint_bust.build_argparser()
    text = parser.format_help()
    for flag in ("--topic", "--topics", "--dry-run", "--confirm", "--force-multi"):
        assert flag in text


def test_idempotency_second_bust_is_noop_on_fingerprint(tmp_path: Path) -> None:
    """Running the tool twice on the same topic leaves the same rows
    NULL'd (idempotent). This is the contract Quality Gate G6 relies on.
    """
    client = _FakeClient(
        seed={"documents": _seed_documents(live_by_topic={"cambiario": 4})}
    )
    first = fingerprint_bust.run_bust(
        client,
        topics=["cambiario"],
        target="production",
        dry_run=False,
        confirm=True,
        force_multi=False,
        manifest_dir=tmp_path,
        tag="cambiario",
    )
    assert first.rows_updated == 4

    second = fingerprint_bust.run_bust(
        client,
        topics=["cambiario"],
        target="production",
        dry_run=False,
        confirm=True,
        force_multi=False,
        manifest_dir=tmp_path,
        tag="cambiario",
    )
    # Second pass still "updates" the same rows (they're just written as
    # NULL → NULL). Row count stays stable; final state is still NULL.
    assert second.plan.row_count == 4
    for r in client.rows("documents"):
        if r["tema"] == "cambiario":
            assert r["doc_fingerprint"] is None
