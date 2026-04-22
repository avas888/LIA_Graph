"""C5 audit-admission tightener tests.

Covers the fail-fast filter added at the top of
``lia_graph.ingest_classifiers._classify_ingestion_decision``:

  * image-style binary assets (``.svg``, ``.png``, etc.) are rejected
    with ``decision_reason="binary_asset"``
  * structural manifest JSONs sitting alongside form-guide prose
    (``guide_manifest.json``, ``structured_guide.json``,
    ``sources.json``, ``interactive_map.json``,
    ``citation_profile.json``) are rejected with
    ``decision_reason="structural_manifest"``
  * the ``LEYES/DEROGADAS/`` corpus subtree is rejected with
    ``decision_reason="derogated_law"``
  * normal markdown under ``normativa/`` keeps flowing to
    ``INGESTION_DECISION_INCLUDE``
  * exactly one ``audit.admission.rejected`` trace event fires per
    excluded file

All cases go through the public ``audit_corpus_documents`` entry-point
so they also exercise ``_audit_single_file``'s downstream record
shape (strategy, tier, priority) for excluded rows.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from lia_graph import ingest_classifiers as classifier_module
from lia_graph.ingest import audit_corpus_documents


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _write(corpus_dir: Path, relative: str, *, content: bytes | str = b"") -> Path:
    path = corpus_dir / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, str):
        path.write_text(content, encoding="utf-8")
    else:
        path.write_bytes(content)
    return path


def _row_by_relative(rows, relative_path: str):
    matches = [row for row in rows if row.relative_path == relative_path]
    assert matches, (
        f"audit row missing for {relative_path!r}; "
        f"have: {[row.relative_path for row in rows]}"
    )
    assert len(matches) == 1
    return matches[0]


# ---------------------------------------------------------------------------
# binary_asset — .svg / image files live alongside prose and have no
# accountant-facing content. They must never enter graph-parse.
# ---------------------------------------------------------------------------


def test_svg_excluded(tmp_path: Path) -> None:
    corpus_dir = tmp_path / "knowledge_base"
    relative = "form_guides/formulario_210/pn_residente/assets/page_02.svg"
    _write(corpus_dir, relative, content=b"<svg xmlns='http://www.w3.org/2000/svg'/>")

    rows = audit_corpus_documents(corpus_dir=corpus_dir)
    row = _row_by_relative(rows, relative)

    assert row.ingestion_decision == "exclude_internal"
    assert row.decision_reason == "binary_asset"
    assert row.document_archetype == "binary_asset"
    assert row.graph_target is False
    assert row.graph_parse_ready is False


# ---------------------------------------------------------------------------
# structural_manifest — manifest JSONs regenerated from prose; they
# carry no accountant-facing text on their own.
# ---------------------------------------------------------------------------


def test_guide_manifest_json_excluded(tmp_path: Path) -> None:
    corpus_dir = tmp_path / "knowledge_base"
    relative = "form_guides/formulario_2516/pj_obligados_contabilidad/guide_manifest.json"
    _write(corpus_dir, relative, content='{"sections": []}')

    rows = audit_corpus_documents(corpus_dir=corpus_dir)
    row = _row_by_relative(rows, relative)

    assert row.ingestion_decision == "exclude_internal"
    assert row.decision_reason == "structural_manifest"
    assert row.document_archetype == "structural_manifest"
    assert row.graph_target is False


def test_structured_guide_json_excluded(tmp_path: Path) -> None:
    corpus_dir = tmp_path / "knowledge_base"
    relative = "form_guides/formulario_210/pn_residente/structured_guide.json"
    _write(corpus_dir, relative, content='{"anchors": []}')

    rows = audit_corpus_documents(corpus_dir=corpus_dir)
    row = _row_by_relative(rows, relative)

    assert row.ingestion_decision == "exclude_internal"
    assert row.decision_reason == "structural_manifest"
    assert row.document_archetype == "structural_manifest"


# ---------------------------------------------------------------------------
# derogated_law — whole subtree held out of ingestion regardless of
# file extension / content signal.
# ---------------------------------------------------------------------------


def test_derogated_laws_path_excluded(tmp_path: Path) -> None:
    corpus_dir = tmp_path / "knowledge_base"
    relative = "CORE ya Arriba/LEYES/DEROGADAS/LOGGRO_Ley-52-1975.md"
    _write(
        corpus_dir,
        relative,
        content=(
            "# Ley 52 de 1975 (DEROGADA)\n\n"
            "Texto historico, reemplazado por normativa posterior.\n"
        ),
    )

    rows = audit_corpus_documents(corpus_dir=corpus_dir)
    row = _row_by_relative(rows, relative)

    assert row.ingestion_decision == "exclude_internal"
    assert row.decision_reason == "derogated_law"
    assert row.document_archetype == "derogated_law"
    assert row.graph_target is False


# ---------------------------------------------------------------------------
# non-excluded markdown under ``normativa/`` still flows through to
# ``INGESTION_DECISION_INCLUDE`` — we must not over-filter.
# ---------------------------------------------------------------------------


def test_non_excluded_markdown_still_included(tmp_path: Path) -> None:
    corpus_dir = tmp_path / "knowledge_base"
    relative = "CORE ya Arriba/normativa/ley-1819-2016.md"
    _write(
        corpus_dir,
        relative,
        content=(
            "## Artículo 1. Regla general\n\n"
            "Conforme al Estatuto Tributario, las expensas necesarias son deducibles.\n"
        ),
    )

    rows = audit_corpus_documents(corpus_dir=corpus_dir)
    row = _row_by_relative(rows, relative)

    assert row.ingestion_decision == "include_corpus"
    assert row.decision_reason != "binary_asset"
    assert row.decision_reason != "structural_manifest"
    assert row.decision_reason != "derogated_law"
    assert row.graph_target is True


# ---------------------------------------------------------------------------
# emit_event fires exactly once per excluded file, with the expected
# {relative_path, reason} payload.
# ---------------------------------------------------------------------------


def test_emit_event_fires_on_exclusion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    events: list[tuple[str, dict]] = []

    def _capture(event_type: str, payload: dict) -> None:
        events.append((event_type, dict(payload)))

    monkeypatch.setattr(classifier_module, "emit_event", _capture)

    corpus_dir = tmp_path / "knowledge_base"
    # Three distinct rejection reasons + one normal admission.
    svg_rel = "form_guides/formulario_115/pes_general/assets/page_02.svg"
    manifest_rel = "form_guides/formulario_115/pes_general/guide_manifest.json"
    derogated_rel = "CORE ya Arriba/LEYES/DEROGADAS/NORMATIVA_Ley-1-1976.md"
    normal_rel = "CORE ya Arriba/normativa/ley-1819-2016.md"

    _write(corpus_dir, svg_rel, content=b"<svg/>")
    _write(corpus_dir, manifest_rel, content="{}")
    _write(
        corpus_dir,
        derogated_rel,
        content="# Ley 1 de 1976 (DEROGADA)\nTexto historico.\n",
    )
    _write(
        corpus_dir,
        normal_rel,
        content="## Artículo 1.\nRegla general.\n",
    )

    audit_corpus_documents(corpus_dir=corpus_dir)

    rejection_events = [
        payload for event_type, payload in events
        if event_type == "audit.admission.rejected"
    ]
    # Exactly one event per excluded file; the normal-md admission
    # emits nothing.
    assert len(rejection_events) == 3

    by_path = {event["relative_path"]: event for event in rejection_events}
    assert by_path[svg_rel]["reason"] == "binary_asset"
    assert by_path[manifest_rel]["reason"] == "structural_manifest"
    assert by_path[derogated_rel]["reason"] == "derogated_law"

    # No event for the admitted document.
    assert normal_rel not in by_path
