"""Tests for v5 Phase 1 / F11 — sink preserves specific tema against
classifier regression.

Locks the contract: when the classifier outputs `otros_sectoriales` but the
existing Supabase row already has a SPECIFIC tema (sector_* or any
non-catchall key), the sink preserves the existing value instead of
overwriting. Prevents additive re-ingest from silently undoing manual
curation / Task E migrations.

See docs/next/ingestionfix_v5.md §5 Phase 1.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from lia_graph.ingestion.supabase_sink import SupabaseCorpusSink, _sanitize_doc_id


# ── Richer fake client (supports .select().in_().execute() for tema reads) ──


@dataclass
class _Exec:
    data: list[dict[str, Any]]


class _Query:
    def __init__(self, parent: "_Table", op: str, payload: Any = None) -> None:
        self._parent = parent
        self._op = op
        self._payload = payload
        self._columns: list[str] = []
        self._in_filter: tuple[str, list[Any]] | None = None
        self._on_conflict: str | None = None

    def select(self, columns: str) -> "_Query":
        self._columns = [c.strip() for c in columns.split(",") if c.strip()]
        return self

    def in_(self, column: str, values: list[Any]) -> "_Query":
        self._in_filter = (column, list(values))
        return self

    def eq(self, column: str, value: Any) -> "_Query":
        return self

    def execute(self) -> _Exec:
        rows = self._parent.rows
        if self._op == "select":
            filt_col, filt_vals = self._in_filter or ("", [])
            picked: list[dict[str, Any]] = []
            for r in rows:
                if filt_col and r.get(filt_col) not in filt_vals:
                    continue
                picked.append({c: r.get(c) for c in self._columns} if self._columns else dict(r))
            return _Exec(picked)
        if self._op == "upsert":
            # record the upserted rows on the table for later assertion
            for row in self._payload or []:
                did = row.get("doc_id")
                if did is None:
                    continue
                replaced = False
                for i, existing in enumerate(rows):
                    if existing.get("doc_id") == did:
                        rows[i] = {**existing, **row}
                        replaced = True
                        break
                if not replaced:
                    rows.append(dict(row))
            return _Exec(list(self._payload or []))
        return _Exec([])


class _Table:
    def __init__(self, name: str, rows: list[dict[str, Any]]) -> None:
        self.name = name
        self.rows = rows

    def select(self, columns: str) -> _Query:
        q = _Query(self, "select")
        return q.select(columns)

    def upsert(self, rows: Any, on_conflict: str | None = None) -> _Query:
        payload = list(rows) if isinstance(rows, list) else [rows]
        q = _Query(self, "upsert", payload)
        q._on_conflict = on_conflict
        return q

    def update(self, payload: dict[str, Any]) -> _Query:
        return _Query(self, "update", payload)

    def delete(self) -> _Query:
        return _Query(self, "delete")


class _FakeClient:
    def __init__(self, seed: dict[str, list[dict[str, Any]]] | None = None) -> None:
        self._tables: dict[str, list[dict[str, Any]]] = {}
        for name, rows in (seed or {}).items():
            self._tables[name] = [dict(r) for r in rows]

    def table(self, name: str) -> _Table:
        if name not in self._tables:
            self._tables[name] = []
        return _Table(name, self._tables[name])

    def rows(self, name: str) -> list[dict[str, Any]]:
        return self._tables.get(name, [])


# ── Fixtures ──────────────────────────────────────────────────────────────


def _doc(rel: str, *, topic_key: str = "otros_sectoriales") -> dict[str, Any]:
    return {
        "relative_path": rel,
        "source_path": rel,
        "title_hint": rel,
        "markdown": "# stub\nprose body",
        "family": "normativa",
        "knowledge_class": "normative_base",
        "source_type": "article_collection",
        "source_tier": "official_compilation",
        "authority_level": "dian",
        "topic_key": topic_key,   # what the classifier decided
        "subtopic_key": None,
        "document_archetype": "article_collection",
        "pais": "colombia",
    }


# ── Tests ─────────────────────────────────────────────────────────────────


def test_specific_sector_tema_preserved_when_classifier_says_otros_sectoriales() -> None:
    """The Task E regression case: doc has `tema=sector_salud` in Supabase;
    classifier says `otros_sectoriales`; sink should KEEP sector_salud.
    """
    rel = "CORE/LEYES/OTROS_SECTORIALES/Ley-1122-salud.md"
    # Seed: existing row in documents with tema=sector_salud
    seed = {
        "documents": [
            {"doc_id": _sanitize_doc_id(rel), "tema": "sector_salud"},
        ]
    }
    client = _FakeClient(seed=seed)
    sink = SupabaseCorpusSink(
        target="production", generation_id="gen_test_f11", client=client,
    )
    sink.write_generation(documents=1, chunks=0, files=[rel])
    sink.write_documents([_doc(rel, topic_key="otros_sectoriales")])

    # Inspect the documents table state
    written = {r["doc_id"]: r for r in client.rows("documents")}
    doc = next(iter(written.values()))
    assert doc["tema"] == "sector_salud", f"tema should preserve sector_salud, got {doc['tema']}"


def test_classifier_specific_tema_overrides_existing_otros_sectoriales() -> None:
    """Inverse case: existing=otros_sectoriales, classifier=sector_vivienda.
    The classifier's specific answer should WIN (no preservation needed)."""
    rel = "CORE/LEYES/OTROS_SECTORIALES/Ley-1537-vivienda.md"
    seed = {
        "documents": [
            {"doc_id": _sanitize_doc_id(rel), "tema": "otros_sectoriales"},
        ]
    }
    client = _FakeClient(seed=seed)
    sink = SupabaseCorpusSink(
        target="production", generation_id="gen_test_f11", client=client,
    )
    sink.write_generation(documents=1, chunks=0, files=[rel])
    sink.write_documents([_doc(rel, topic_key="sector_vivienda")])

    written = {r["doc_id"]: r for r in client.rows("documents")}
    doc = next(iter(written.values()))
    assert doc["tema"] == "sector_vivienda"


def test_no_existing_row_classifier_otros_sectoriales_lands_as_otros() -> None:
    """First-ingest case: no existing row; classifier picks otros_sectoriales;
    preservation logic is a no-op (nothing to preserve)."""
    rel = "CORE/LEYES/OTROS_SECTORIALES/Ley-NEW.md"
    client = _FakeClient()
    sink = SupabaseCorpusSink(
        target="production", generation_id="gen_test_f11", client=client,
    )
    sink.write_generation(documents=1, chunks=0, files=[rel])
    sink.write_documents([_doc(rel, topic_key="otros_sectoriales")])

    written = {r["doc_id"]: r for r in client.rows("documents")}
    doc = next(iter(written.values()))
    assert doc["tema"] == "otros_sectoriales"


def test_both_sides_otros_sectoriales_no_change() -> None:
    """Idempotent case: existing=otros_sectoriales, classifier=otros_sectoriales.
    Result stays otros_sectoriales — no accidental preservation loop."""
    rel = "CORE/LEYES/OTROS_SECTORIALES/Ley-true-orphan.md"
    seed = {
        "documents": [
            {"doc_id": _sanitize_doc_id(rel), "tema": "otros_sectoriales"},
        ]
    }
    client = _FakeClient(seed=seed)
    sink = SupabaseCorpusSink(
        target="production", generation_id="gen_test_f11", client=client,
    )
    sink.write_generation(documents=1, chunks=0, files=[rel])
    sink.write_documents([_doc(rel, topic_key="otros_sectoriales")])

    written = {r["doc_id"]: r for r in client.rows("documents")}
    doc = next(iter(written.values()))
    assert doc["tema"] == "otros_sectoriales"


def test_specific_existing_tema_non_sector_also_preserved() -> None:
    """Task E also migrated docs into existing non-sector topics (laboral,
    presupuesto_hacienda, etc.). Those should also be preserved against
    otros_sectoriales regression."""
    rel = "CORE/LEYES/OTROS_SECTORIALES/Ley-1527-libranzas.md"
    seed = {
        "documents": [
            {"doc_id": _sanitize_doc_id(rel), "tema": "laboral"},
        ]
    }
    client = _FakeClient(seed=seed)
    sink = SupabaseCorpusSink(
        target="production", generation_id="gen_test_f11", client=client,
    )
    sink.write_generation(documents=1, chunks=0, files=[rel])
    sink.write_documents([_doc(rel, topic_key="otros_sectoriales")])

    written = {r["doc_id"]: r for r in client.rows("documents")}
    doc = next(iter(written.values()))
    assert doc["tema"] == "laboral"
