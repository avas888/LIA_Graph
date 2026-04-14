from __future__ import annotations

import json
from pathlib import Path

from lia_graph.corpus_ops import build_corpus_status
from lia_graph.ingest import (
    audit_corpus_documents,
    materialize_graph_artifacts,
    scaffold_graph_build,
)


def test_scaffold_graph_build_creates_nodes_edges_and_validation() -> None:
    markdown_documents = [
        (
            "knowledge_base/normativa/sample.md",
            """
## Artículo 1. Renta liquida cedular
Modificado por la Ley 2277 de 2022.
Para efectos del calculo, conforme al artículo 2 del E.T., debe conservar soporte.

Parágrafo 1. Debe conservar soporte idoneo.

## Artículo 2. Definiciones especiales
Se entiende por ingreso gravado el valor sometido al impuesto.
""",
        )
    ]

    result = scaffold_graph_build(markdown_documents)

    assert len(result["articles"]) == 2
    assert len(result["raw_edges"]) >= 2
    assert any(edge["kind"] == "MODIFIES" for edge in result["typed_edges"])
    assert any(
        edge["kind"] == "COMPUTATION_DEPENDS_ON" and edge["target_key"] == "2"
        for edge in result["typed_edges"]
    )

    load_plan = result["graph_load_plan"]
    assert load_plan["validation"]["ok"] is True
    assert load_plan["validation"]["node_count"] == 3
    assert load_plan["warnings"] == ["FALKORDB_URL is not configured; load plan is staged only."]


def test_build_corpus_status_exposes_phase_2_graph_scaffold() -> None:
    status = build_corpus_status()

    assert status["status"] == "phase_2_scaffold"
    assert status["corpus_families"] == ["normativa", "interpretacion", "practica"]
    assert status["audit_decisions"] == [
        "include_corpus",
        "revision_candidate",
        "exclude_internal",
    ]
    assert "artifacts/corpus_audit_report.json" in status["audit_artifacts"]
    assert "artifacts/canonical_corpus_manifest.json" in status["audit_artifacts"]
    assert status["graph_target_families"] == ["normativa"]
    assert status["graph_scaffold"]["graph_name"] == "LIA_REGULATORY_GRAPH"
    assert "MODIFIES" in status["graph_scaffold"]["edge_types"]


def test_audit_corpus_documents_classifies_include_revision_and_exclude(
    tmp_path: Path,
) -> None:
    corpus_dir = tmp_path / "knowledge_base"
    (corpus_dir / "CORE ya Arriba" / "normativa").mkdir(parents=True)
    (corpus_dir / "to upload").mkdir(parents=True)
    (corpus_dir / "CORE ya Arriba" / "normativa" / "renta.md").write_text(
        """
## Artículo 1. Renta liquida cedular
Modificado por la Ley 2277 de 2022.
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (corpus_dir / "to upload" / "PATCH_renta.md").write_text(
        "Insertar en: CORE ya Arriba/normativa/renta.md\n\nAgregar paragrafo final.\n",
        encoding="utf-8",
    )
    (corpus_dir / "CORE ya Arriba" / "normativa" / "state.md").write_text(
        "# Estado\n\nPendiente validar corpus.\n",
        encoding="utf-8",
    )

    audit_rows = audit_corpus_documents(corpus_dir=corpus_dir)
    rows_by_path = {row.relative_path: row for row in audit_rows}

    included = rows_by_path["CORE ya Arriba/normativa/renta.md"]
    revision = rows_by_path["to upload/PATCH_renta.md"]
    excluded = rows_by_path["CORE ya Arriba/normativa/state.md"]

    assert included.ingestion_decision == "include_corpus"
    assert included.source_origin == "core_ya_arriba"
    assert included.family == "normativa"
    assert included.knowledge_class == "normative_base"
    assert included.source_type == "ley"
    assert included.graph_target is True
    assert included.graph_parse_ready is True
    assert included.parse_strategy == "markdown_graph_parse"
    assert included.document_archetype == "base_doc"
    assert included.topic_key == "declaracion_renta"
    assert included.vocabulary_status == "ratified_v1_2"

    assert revision.ingestion_decision == "revision_candidate"
    assert revision.parse_strategy == "revision_merge_candidate"
    assert revision.document_archetype == "revision_patch"
    assert revision.base_doc_target == "CORE ya Arriba/normativa/renta.md"

    assert excluded.ingestion_decision == "exclude_internal"
    assert excluded.parse_strategy == "excluded_internal"
    assert excluded.document_archetype == "working_note"
    assert excluded.decision_reason == "Excluded working state file."


def test_audit_gate_excludes_working_readme_and_keeps_custom_pending_topic(
    tmp_path: Path,
) -> None:
    corpus_dir = tmp_path / "knowledge_base"
    (corpus_dir / "CORE ya Arriba" / "normativa").mkdir(parents=True)
    (corpus_dir / "CORE ya Arriba" / "README.md").write_text(
        "# README\n\nNext action: revisar corpus. Checkpoint log pendiente.\n",
        encoding="utf-8",
    )
    (corpus_dir / "CORE ya Arriba" / "normativa" / "informacion_exogena_2026.md").write_text(
        """
# Informacion exogena 2026

Resolucion DIAN para medios magneticos y formatos de reporte.
""".strip()
        + "\n",
        encoding="utf-8",
    )

    audit_rows = audit_corpus_documents(corpus_dir=corpus_dir)
    rows_by_path = {row.relative_path: row for row in audit_rows}

    readme_row = rows_by_path["CORE ya Arriba/README.md"]
    exogena_row = rows_by_path["CORE ya Arriba/normativa/informacion_exogena_2026.md"]

    assert readme_row.ingestion_decision == "exclude_internal"
    assert readme_row.decision_reason == "Excluded working README or implementation note."

    assert exogena_row.ingestion_decision == "include_corpus"
    assert exogena_row.family == "normativa"
    assert exogena_row.topic_key == "informacion_exogena"
    assert exogena_row.vocabulary_status == "custom_topic_pending_vocab"


def test_audit_gate_includes_non_markdown_corpus_asset_without_graph_parsing(
    tmp_path: Path,
) -> None:
    corpus_dir = tmp_path / "knowledge_base"
    (corpus_dir / "CORE ya Arriba" / "normativa").mkdir(parents=True)
    pdf_path = corpus_dir / "CORE ya Arriba" / "normativa" / "concepto_001.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\x00fake-binary-payload")

    audit_rows = audit_corpus_documents(corpus_dir=corpus_dir)
    row = {row.relative_path: row for row in audit_rows}["CORE ya Arriba/normativa/concepto_001.pdf"]

    assert row.ingestion_decision == "include_corpus"
    assert row.family == "normativa"
    assert row.text_extractable is False
    assert row.parse_strategy == "binary_inventory_only"
    assert row.document_archetype == "base_doc"
    assert row.graph_target is True
    assert row.graph_parse_ready is False


def test_materialize_graph_artifacts_writes_expected_files(tmp_path: Path) -> None:
    corpus_dir = tmp_path / "knowledge_base"
    (corpus_dir / "CORE ya Arriba" / "normativa").mkdir(parents=True)
    (corpus_dir / "CORE ya Arriba" / "industry_guidance").mkdir(parents=True)
    (corpus_dir / "CORE ya Arriba" / "practica").mkdir(parents=True)
    (corpus_dir / "to upload").mkdir(parents=True)
    (corpus_dir / "CORE ya Arriba" / "normativa" / "renta.md").write_text(
        """
## Artículo 1. Renta liquida cedular
Modificado por la Ley 2277 de 2022.
Para efectos del calculo, conforme al artículo 2 del E.T., debe conservar soporte.

## Artículo 2. Definiciones especiales
Se entiende por ingreso gravado el valor sometido al impuesto.
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (corpus_dir / "CORE ya Arriba" / "industry_guidance" / "iva_expertos.md").write_text(
        "# IVA\n\nAnalisis profesional sobre soporte tributario.\n",
        encoding="utf-8",
    )
    (corpus_dir / "CORE ya Arriba" / "practica" / "checklist_iva.md").write_text(
        "# Practica\n\nChecklist operativo para cierres contables.\n",
        encoding="utf-8",
    )
    (corpus_dir / "to upload" / "UPSERT_renta.md").write_text(
        "Insertar en: CORE ya Arriba/normativa/renta.md\n\nAgregar nota operativa.\n",
        encoding="utf-8",
    )
    (corpus_dir / "CORE ya Arriba" / "normativa" / "state.md").write_text(
        "# Estado\n\nPendiente validar corpus.\n",
        encoding="utf-8",
    )
    (corpus_dir / "CORE ya Arriba" / "normativa" / "concepto_001.pdf").write_bytes(
        b"%PDF-1.4\x00fake-binary-payload"
    )
    artifacts_dir = tmp_path / "artifacts"

    result = materialize_graph_artifacts(
        corpus_dir=corpus_dir,
        artifacts_dir=artifacts_dir,
    )

    assert result["document_count"] == 4
    assert result["scanned_file_count"] == 6
    assert result["decision_counts"] == {
        "exclude_internal": 1,
        "include_corpus": 4,
        "revision_candidate": 1,
    }
    assert result["document_family_counts"] == {
        "interpretacion": 1,
        "normativa": 2,
        "practica": 1,
    }
    assert result["extension_counts"] == {
        ".md": 5,
        ".pdf": 1,
    }
    assert result["graph_target_families"] == ["normativa"]
    assert result["graph_target_document_count"] == 2
    assert result["graph_parse_ready_document_count"] == 1
    assert result["article_count"] == 2

    audit_report_path = artifacts_dir / "corpus_audit_report.json"
    revision_candidates_path = artifacts_dir / "revision_candidates.json"
    excluded_files_path = artifacts_dir / "excluded_files.json"
    canonical_manifest_path = artifacts_dir / "canonical_corpus_manifest.json"
    corpus_inventory_path = artifacts_dir / "corpus_inventory.json"
    parsed_articles_path = artifacts_dir / "parsed_articles.jsonl"
    raw_edges_path = artifacts_dir / "raw_edges.jsonl"
    typed_edges_path = artifacts_dir / "typed_edges.jsonl"
    load_report_path = artifacts_dir / "graph_load_report.json"
    validation_report_path = artifacts_dir / "graph_validation_report.json"

    assert audit_report_path.exists()
    assert revision_candidates_path.exists()
    assert excluded_files_path.exists()
    assert canonical_manifest_path.exists()
    assert corpus_inventory_path.exists()
    assert parsed_articles_path.exists()
    assert raw_edges_path.exists()
    assert typed_edges_path.exists()
    assert load_report_path.exists()
    assert validation_report_path.exists()

    audit_report = json.loads(audit_report_path.read_text(encoding="utf-8"))
    revision_candidates = json.loads(revision_candidates_path.read_text(encoding="utf-8"))
    excluded_files = json.loads(excluded_files_path.read_text(encoding="utf-8"))
    canonical_manifest = json.loads(canonical_manifest_path.read_text(encoding="utf-8"))
    corpus_inventory = json.loads(corpus_inventory_path.read_text(encoding="utf-8"))
    parsed_lines = parsed_articles_path.read_text(encoding="utf-8").strip().splitlines()
    typed_lines = typed_edges_path.read_text(encoding="utf-8").strip().splitlines()
    load_report = json.loads(load_report_path.read_text(encoding="utf-8"))
    validation_report = json.loads(validation_report_path.read_text(encoding="utf-8"))

    assert audit_report["decision_counts"] == {
        "exclude_internal": 1,
        "include_corpus": 4,
        "revision_candidate": 1,
    }
    assert audit_report["parse_strategy_counts"]["binary_inventory_only"] == 1
    assert revision_candidates["count"] == 1
    assert excluded_files["count"] == 1
    assert canonical_manifest["document_count"] == 4
    assert canonical_manifest["documents_with_pending_revisions"] == 1
    assert canonical_manifest["unresolved_revision_candidate_count"] == 0
    assert corpus_inventory["family_counts"] == {
        "interpretacion": 1,
        "normativa": 2,
        "practica": 1,
    }
    assert corpus_inventory["decision_counts"] == {
        "exclude_internal": 1,
        "include_corpus": 4,
        "revision_candidate": 1,
    }
    assert corpus_inventory["knowledge_class_counts"] == {
        "interpretative_guidance": 1,
        "normative_base": 2,
        "practica_erp": 1,
    }
    assert corpus_inventory["graph_target_document_count"] == 2
    assert corpus_inventory["graph_parse_ready_document_count"] == 1
    assert any(row["parse_strategy"] == "binary_inventory_only" for row in corpus_inventory["documents"])
    assert any(row["vocabulary_status"] == "ratified_v1_2" for row in corpus_inventory["documents"])
    assert any(row["family"] == "interpretacion" for row in corpus_inventory["documents"])
    assert any(row["family"] == "practica" for row in corpus_inventory["documents"])
    assert len(parsed_lines) == 2
    assert any(json.loads(line)["kind"] == "COMPUTATION_DEPENDS_ON" for line in typed_lines)
    assert load_report["executed"] is False
    assert validation_report["ok"] is True
