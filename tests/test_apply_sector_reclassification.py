"""Tests for ``scripts/monitoring/monitor_sector_reclassification/apply_sector_reclassification.py``.

Locks the four safety rails Phase 2.5 Task E relies on:

1. Non-``.approved.json`` inputs are refused before any I/O.
2. Checksum mismatch on the decisions body is refused before any I/O.
3. ``--dry-run`` (or missing ``--confirm`` on a non-dry run) issues zero UPDATE calls.
4. The pre-execute manifest survives a mid-UPDATE crash.

Mirrors the ``_FakeClient`` pattern from ``test_fingerprint_bust.py``.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

_SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "scripts"
    / "monitoring"
    / "monitor_sector_reclassification"
    / "apply_sector_reclassification.py"
)
_spec = importlib.util.spec_from_file_location("apply_sector_reclassification", _SCRIPT)
assert _spec is not None and _spec.loader is not None
apply_mod = importlib.util.module_from_spec(_spec)
sys.modules["apply_sector_reclassification"] = apply_mod
_spec.loader.exec_module(apply_mod)  # type: ignore[union-attr]


# ── Minimal supabase fake (update-only; mirrors test_fingerprint_bust) ─


@dataclass
class _Execute:
    data: list[dict[str, Any]]


class _Query:
    def __init__(self, parent: "_Table", op: str, payload: Any = None) -> None:
        self._parent = parent
        self._op = op
        self._payload = payload
        self._in_filter: tuple[str, list[Any]] | None = None

    def in_(self, column: str, values: list[Any]) -> "_Query":
        self._in_filter = (column, list(values))
        return self

    def execute(self) -> _Execute:
        if self._op != "update":
            return _Execute([])
        column, values = self._in_filter or ("doc_id", [])
        touched: list[dict[str, Any]] = []
        for r in self._parent.rows:
            if r.get(column) in values:
                r.update(self._payload or {})
                touched.append(dict(r))
        return _Execute(touched)


class _Table:
    def __init__(self, name: str, rows: list[dict[str, Any]], client: "_FakeClient") -> None:
        self.name = name
        self.rows = rows
        self._client = client

    def update(self, payload: dict[str, Any]) -> _Query:
        self._client.calls.append(("update", self.name, dict(payload)))
        return _Query(self, "update", payload=payload)


class _FakeClient:
    def __init__(self, rows: list[dict[str, Any]] | None = None) -> None:
        self._rows: dict[str, list[dict[str, Any]]] = {
            "documents": [dict(r) for r in (rows or [])]
        }
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    def table(self, name: str) -> _Table:
        return _Table(name, self._rows.setdefault(name, []), self)

    def rows_for(self, name: str) -> list[dict[str, Any]]:
        return self._rows.get(name, [])

    def count_calls(self, op: str) -> int:
        return sum(1 for (o, _t, _p) in self.calls if o == op)


# ── Fixture helpers ──────────────────────────────────────────────────


def _make_approved_body(decisions: list[dict[str, Any]], plan_version: str = "v3.1-test") -> dict[str, Any]:
    # Deep-copy decisions so callers that tamper (e.g. checksum-mismatch test)
    # don't pollute the module-level _SAMPLE_DECISIONS fixture.
    body = {
        "plan_version": plan_version,
        "approved_by": "test@lia.dev",
        "approved_at_bogota": "2026-04-23 03:00 PM",
        "decisions": [dict(d) for d in decisions],
    }
    canonical = json.dumps(
        {"plan_version": body["plan_version"], "decisions": body["decisions"]},
        sort_keys=True,
        ensure_ascii=False,
    ).encode("utf-8")
    body["decisions_sha256"] = hashlib.sha256(canonical).hexdigest()
    return body


def _write_approved(tmp_path: Path, decisions: list[dict[str, Any]], name: str = "x.approved.json") -> Path:
    body = _make_approved_body(decisions)
    p = tmp_path / name
    p.write_text(json.dumps(body, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return p


_SAMPLE_DECISIONS = [
    {
        "doc_id": "doc_a",
        "current_tema": "otros_sectoriales",
        "new_tema": "sector_salud",
        "action": "new_sector",
        "reason_tag": "merge_map_canonical",
    },
    {
        "doc_id": "doc_b",
        "current_tema": "otros_sectoriales",
        "new_tema": "sector_salud",
        "action": "new_sector",
        "reason_tag": "merge_map_canonical",
    },
    {
        "doc_id": "doc_c",
        "current_tema": "otros_sectoriales",
        "new_tema": "laboral",
        "action": "migrate_existing",
        "reason_tag": "existing_taxonomy_key",
    },
    {
        "doc_id": "doc_d",
        "current_tema": "otros_sectoriales",
        "new_tema": "otros_sectoriales",
        "action": "stay_orphan",
        "reason_tag": "true_orphan",
    },
]


def _seed_docs() -> list[dict[str, Any]]:
    return [
        {"doc_id": "doc_a", "tema": "otros_sectoriales", "doc_fingerprint": "fp_a"},
        {"doc_id": "doc_b", "tema": "otros_sectoriales", "doc_fingerprint": "fp_b"},
        {"doc_id": "doc_c", "tema": "otros_sectoriales", "doc_fingerprint": "fp_c"},
        {"doc_id": "doc_d", "tema": "otros_sectoriales", "doc_fingerprint": "fp_d"},
        {"doc_id": "doc_untouched", "tema": "iva", "doc_fingerprint": "fp_iva"},
    ]


# ── Tests ────────────────────────────────────────────────────────────


def test_refuses_non_approved_suffix(tmp_path: Path) -> None:
    p = _write_approved(tmp_path, _SAMPLE_DECISIONS, name="raw_proposal.json")
    with pytest.raises(apply_mod.UnsafeApplyError) as excinfo:
        apply_mod.load_approved_plan(p)
    assert ".approved.json" in str(excinfo.value)


def test_refuses_checksum_mismatch(tmp_path: Path) -> None:
    body = _make_approved_body(_SAMPLE_DECISIONS)
    # Tamper with a decision AFTER signing.
    body["decisions"][0]["new_tema"] = "tampered_topic"
    p = tmp_path / "tampered.approved.json"
    p.write_text(json.dumps(body, indent=2, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(apply_mod.UnsafeApplyError) as excinfo:
        apply_mod.load_approved_plan(p)
    assert "checksum mismatch" in str(excinfo.value).lower()


def test_refuses_missing_required_field(tmp_path: Path) -> None:
    body = _make_approved_body(_SAMPLE_DECISIONS)
    body.pop("decisions_sha256")
    p = tmp_path / "nosig.approved.json"
    p.write_text(json.dumps(body, indent=2, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(apply_mod.UnsafeApplyError):
        apply_mod.load_approved_plan(p)


def test_dry_run_writes_manifest_but_no_updates(tmp_path: Path) -> None:
    approved = _write_approved(tmp_path, _SAMPLE_DECISIONS)
    client = _FakeClient(rows=_seed_docs())

    outcome = apply_mod.run_apply(
        client,
        approved_path=approved,
        manifest_dir=tmp_path / "manifests",
        dry_run=True,
        confirm=False,
    )
    assert outcome.dry_run is True
    assert outcome.rows_written == 0
    assert client.count_calls("update") == 0
    assert outcome.manifest_path.exists()

    # Manifest body covers the 3 write_decisions (doc_a, doc_b, doc_c)
    payload = json.loads(outcome.manifest_path.read_text())
    assert payload["write_row_count"] == 3
    assert payload["action_counts"] == {
        "new_sector": 2,
        "migrate_existing": 1,
        "stay_orphan": 1,
    }
    assert payload["new_tema_counts"] == {"sector_salud": 2, "laboral": 1}

    # Fingerprints untouched in dry-run.
    for r in client.rows_for("documents"):
        assert r["doc_fingerprint"] is not None


def test_non_dry_run_requires_confirm(tmp_path: Path) -> None:
    approved = _write_approved(tmp_path, _SAMPLE_DECISIONS)
    client = _FakeClient(rows=_seed_docs())
    with pytest.raises(apply_mod.UnsafeApplyError) as excinfo:
        apply_mod.run_apply(
            client,
            approved_path=approved,
            manifest_dir=tmp_path / "manifests",
            dry_run=False,
            confirm=False,
        )
    assert "--confirm" in str(excinfo.value)
    assert client.count_calls("update") == 0


def test_confirmed_run_writes_tema_and_nulls_fingerprint(tmp_path: Path) -> None:
    approved = _write_approved(tmp_path, _SAMPLE_DECISIONS)
    client = _FakeClient(rows=_seed_docs())

    outcome = apply_mod.run_apply(
        client,
        approved_path=approved,
        manifest_dir=tmp_path / "manifests",
        dry_run=False,
        confirm=True,
    )
    assert outcome.dry_run is False
    assert outcome.rows_written == 3  # doc_a, doc_b, doc_c

    rows = {r["doc_id"]: r for r in client.rows_for("documents")}
    assert rows["doc_a"]["tema"] == "sector_salud"
    assert rows["doc_a"]["doc_fingerprint"] is None
    assert rows["doc_b"]["tema"] == "sector_salud"
    assert rows["doc_b"]["doc_fingerprint"] is None
    assert rows["doc_c"]["tema"] == "laboral"
    assert rows["doc_c"]["doc_fingerprint"] is None
    # stay_orphan untouched.
    assert rows["doc_d"]["tema"] == "otros_sectoriales"
    assert rows["doc_d"]["doc_fingerprint"] == "fp_d"
    # Unrelated iva doc untouched.
    assert rows["doc_untouched"]["tema"] == "iva"
    assert rows["doc_untouched"]["doc_fingerprint"] == "fp_iva"

    # 2 UPDATE calls — one per distinct new_tema (sector_salud, laboral).
    assert client.count_calls("update") == 2


def test_manifest_written_before_execute(tmp_path: Path) -> None:
    """If apply_migration explodes mid-batch, the manifest must already exist."""
    approved = _write_approved(tmp_path, _SAMPLE_DECISIONS)
    client = _FakeClient(rows=_seed_docs())

    original = apply_mod.apply_migration

    def _exploding(client: Any, *, decisions: Any, batch_size: int = 200) -> int:
        raise RuntimeError("simulated PostgREST outage mid-UPDATE")

    apply_mod.apply_migration = _exploding  # type: ignore[assignment]
    try:
        with pytest.raises(RuntimeError):
            apply_mod.run_apply(
                client,
                approved_path=approved,
                manifest_dir=tmp_path / "manifests",
                dry_run=False,
                confirm=True,
            )
    finally:
        apply_mod.apply_migration = original  # type: ignore[assignment]

    manifests = list((tmp_path / "manifests").glob("*_apply.json"))
    assert len(manifests) == 1
    payload = json.loads(manifests[0].read_text())
    assert payload["dry_run"] is False
    assert payload["write_row_count"] == 3


def test_groups_by_new_tema_preserves_stay_orphan_skip() -> None:
    plan_decisions = [
        apply_mod.Decision(
            doc_id="a", current_tema="otros_sectoriales",
            new_tema="sector_x", action="new_sector", reason_tag="",
        ),
        apply_mod.Decision(
            doc_id="b", current_tema="otros_sectoriales",
            new_tema="otros_sectoriales", action="stay_orphan", reason_tag="",
        ),
        apply_mod.Decision(
            doc_id="c", current_tema="otros_sectoriales",
            new_tema="sector_x", action="new_sector", reason_tag="",
        ),
    ]
    groups = apply_mod._group_by_new_tema(plan_decisions)
    assert groups == {"sector_x": ["a", "c"]}


def test_batching_chunks_large_groups(tmp_path: Path) -> None:
    """A group with >UPDATE_BATCH_SIZE docs issues multiple UPDATE calls."""
    decisions = [
        {
            "doc_id": f"doc_{i:04d}",
            "current_tema": "otros_sectoriales",
            "new_tema": "sector_salud",
            "action": "new_sector",
            "reason_tag": "merge_map_canonical",
        }
        for i in range(250)
    ]
    approved = _write_approved(tmp_path, decisions)
    rows = [{"doc_id": d["doc_id"], "tema": "otros_sectoriales", "doc_fingerprint": f"fp_{d['doc_id']}"} for d in decisions]
    client = _FakeClient(rows=rows)

    outcome = apply_mod.run_apply(
        client,
        approved_path=approved,
        manifest_dir=tmp_path / "manifests",
        dry_run=False,
        confirm=True,
    )
    assert outcome.rows_written == 250
    # 250 rows, UPDATE_BATCH_SIZE=200 -> 2 update calls.
    assert client.count_calls("update") == 2


def test_cli_help_advertises_required_flags() -> None:
    parser = apply_mod.build_argparser()
    text = parser.format_help()
    for flag in ("--approved", "--dry-run", "--confirm"):
        assert flag in text
