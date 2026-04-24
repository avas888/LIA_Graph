"""Tests for ``scripts/monitoring/monitor_sector_reclassification/sector_classify.py``.

Focused on the pieces that matter if Gemini returns something weird:

* JSON-array extraction tolerates fenced blocks + leading prose.
* Batching is deterministic + respects batch_size.
* A mock adapter that omits doc_ids produces ``kind=error`` entries so
  no doc silently vanishes from the proposal.
* Atomic checkpoint writes don't leave partial files behind on failure.

Skips the Gemini network call itself — that's covered by the live
rehearsal run documented in ingestionfix_v3 §5 Phase 2.5 Task A.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "scripts"
    / "monitoring"
    / "monitor_sector_reclassification"
    / "sector_classify.py"
)
_spec = importlib.util.spec_from_file_location("sector_classify", _SCRIPT)
assert _spec is not None and _spec.loader is not None
mod = importlib.util.module_from_spec(_spec)
sys.modules["sector_classify"] = mod
_spec.loader.exec_module(mod)  # type: ignore[union-attr]


# ── JSON array extraction ────────────────────────────────────────────


def test_extract_plain_json_array() -> None:
    raw = '[{"doc_id":"d1","proposed_topic":"sector_salud","kind":"new_sector","confidence":"high","reasoning":"test"}]'
    out = mod._extract_json_array(raw)
    assert len(out) == 1
    assert out[0]["doc_id"] == "d1"


def test_extract_fenced_json_array() -> None:
    raw = '```json\n[{"doc_id":"d1","kind":"orphan"}]\n```'
    out = mod._extract_json_array(raw)
    assert len(out) == 1
    assert out[0]["kind"] == "orphan"


def test_extract_json_with_leading_prose() -> None:
    raw = 'Aquí está la clasificación:\n\n[{"doc_id":"d1","kind":"migrate"}]\n\nEspero que ayude.'
    out = mod._extract_json_array(raw)
    assert len(out) == 1


def test_extract_malformed_raises() -> None:
    import pytest
    with pytest.raises(ValueError):
        mod._extract_json_array("not json at all")


# ── Batching ────────────────────────────────────────────────────────


def test_build_batches_respects_size() -> None:
    ids = [f"d{i}" for i in range(50)]
    batches = mod._build_batches(ids, batch_size=20)
    assert len(batches) == 3
    assert len(batches[0].doc_ids) == 20
    assert len(batches[1].doc_ids) == 20
    assert len(batches[2].doc_ids) == 10
    # Batch numbers are 1-indexed.
    assert [b.batch_num for b in batches] == [1, 2, 3]


def test_hash_ids_is_order_invariant() -> None:
    a = mod._hash_ids(["d1", "d2", "d3"])
    b = mod._hash_ids(["d3", "d1", "d2"])
    assert a == b


def test_hash_ids_distinguishes_different_sets() -> None:
    a = mod._hash_ids(["d1", "d2"])
    b = mod._hash_ids(["d1", "d3"])
    assert a != b


# ── classify_batch graceful failure ─────────────────────────────────


class _StubAdapter:
    def __init__(self, response: str) -> None:
        self.response = response

    def generate(self, prompt: str) -> str:
        return self.response


def test_classify_batch_marks_omitted_docs_as_error() -> None:
    # Adapter returns only d1; d2 should show up as kind=error.
    stub = _StubAdapter(
        '[{"doc_id":"d1","proposed_topic":"sector_salud","kind":"new_sector","confidence":"high","reasoning":"x"}]'
    )
    docs = [("d1", "T1", "body1"), ("d2", "T2", "body2")]
    results = mod.classify_batch(stub, docs=docs, existing_topics=["laboral"])
    by_id = {r.doc_id: r for r in results}
    assert by_id["d1"].kind == "new_sector"
    assert by_id["d2"].kind == "error"
    assert "omitted" in by_id["d2"].reasoning.lower()


def test_classify_batch_handles_malformed_response() -> None:
    stub = _StubAdapter("not json; also fenced ```but not properly```")
    docs = [("d1", "T1", "body")]
    results = mod.classify_batch(stub, docs=docs, existing_topics=["laboral"])
    assert len(results) == 1
    assert results[0].kind == "error"
    assert "parse_failed" in results[0].reasoning


# ── Atomic checkpointing ────────────────────────────────────────────


def test_atomic_write_replaces_file(tmp_path: Path) -> None:
    target = tmp_path / "x.json"
    mod._atomic_write_json(target, {"v": 1})
    assert json.loads(target.read_text())["v"] == 1
    mod._atomic_write_json(target, {"v": 2})
    assert json.loads(target.read_text())["v"] == 2
    # No leftover temp file.
    assert not (tmp_path / "x.json.tmp").exists()


def test_index_load_returns_empty_when_missing(tmp_path: Path) -> None:
    got = mod.load_index(tmp_path / "no_such.json")
    assert got == {"batches": {}, "created_at_utc": None}


def test_index_load_tolerates_corrupt_json(tmp_path: Path) -> None:
    p = tmp_path / "idx.json"
    p.write_text("{not valid", encoding="utf-8")
    got = mod.load_index(p)
    assert got["batches"] == {}


# ── Heartbeat output shape ──────────────────────────────────────────


def test_render_heartbeat_shows_required_fields() -> None:
    text = mod.render_heartbeat(
        batch_num=3,
        total_batches=26,
        per_batch_seconds=[10.0, 12.0, 14.0],
        sector_histogram={"sector_salud": 5, "sector_educacion": 3},
        migration_histogram={"laboral": 2},
        errors=0,
        total_docs_done=60,
        total_docs=510,
        cost_usd=0.05,
    )
    assert "batch 3/26" in text
    assert "60/510" in text
    assert "sector_salud=5" in text
    assert "laboral=2" in text
    assert "$0.050" in text
