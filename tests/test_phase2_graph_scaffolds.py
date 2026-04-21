from __future__ import annotations

import json
from pathlib import Path

from lia_graph.graph import GraphClient, GraphClientConfig, GraphQueryResult, GraphWriteStatement
from lia_graph.graph.schema import NodeKind
from lia_graph.corpus_ops import build_corpus_status
from lia_graph.ingest import (
    audit_corpus_documents,
    materialize_graph_artifacts,
    scaffold_graph_build,
)
from lia_graph.ingestion import classify_edge_candidates
from lia_graph.ingestion.linker import RawEdgeCandidate
from lia_graph.topic_guardrails import get_topic_scope, normalize_topic_key
from lia_graph.topic_taxonomy import load_topic_taxonomy, topic_taxonomy_version


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


def test_scaffold_graph_build_skips_unresolved_article_edges() -> None:
    markdown_documents = [
        (
            "knowledge_base/normativa/sample.md",
            """
## Artículo 1. Regla especial
Conforme a la Ley 1607 de 2012, Art. 22-1, el contribuyente debe conservar soporte.
""",
        )
    ]

    result = scaffold_graph_build(markdown_documents)

    assert not any(edge["target_key"] == "22-1" for edge in result["typed_edges"])
    assert any(edge["target_kind"] == "ReformNode" for edge in result["typed_edges"])
    assert result["graph_load_plan"]["validation"]["ok"] is True
    assert any(
        warning.startswith("Skipped 1 unresolved ArticleNode edge")
        for warning in result["graph_load_plan"]["warnings"]
    )


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
    assert "artifacts/corpus_reconnaissance_report.json" in status["audit_artifacts"]
    assert "artifacts/canonical_corpus_manifest.json" in status["audit_artifacts"]
    assert status["graph_target_families"] == ["normativa"]
    assert status["graph_scaffold"]["graph_name"] == "LIA_REGULATORY_GRAPH"
    assert "MODIFIES" in status["graph_scaffold"]["edge_types"]


def test_topic_guardrails_normalize_taxonomy_aliases_and_scopes() -> None:
    assert normalize_topic_key("rst") == "regimen_simple"

    scope = get_topic_scope("costos_deducciones_renta")

    assert scope is not None
    assert scope.key == "costos_deducciones_renta"
    assert "declaracion_renta" in scope.allowed_topics


def test_materialize_graph_artifacts_refuses_live_load_until_gate_is_ready(
    tmp_path: Path,
) -> None:
    corpus_dir = tmp_path / "knowledge_base"
    (corpus_dir / "CORE ya Arriba" / "normativa").mkdir(parents=True)
    (corpus_dir / "to upload").mkdir(parents=True)
    (corpus_dir / "CORE ya Arriba" / "normativa" / "renta.md").write_text(
        """
## Artículo 1. Renta liquida cedular
Modificado por la Ley 2277 de 2022.
Conforme al artículo 2 del E.T., debe conservar soporte.

## Artículo 2. Definiciones especiales
Se entiende por ingreso gravado el valor sometido al impuesto.
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (corpus_dir / "to upload" / "PATCH_renta.md").write_text(
        "Insertar en: CORE ya Arriba/normativa/renta.md\n\nAgregar paragrafo final.\n",
        encoding="utf-8",
    )

    artifacts_dir = tmp_path / "artifacts"
    result = materialize_graph_artifacts(
        corpus_dir=corpus_dir,
        artifacts_dir=artifacts_dir,
        execute_load=True,
    )

    load_report = result["graph_load_report"]
    assert result["reconnaissance_quality_gate"]["status"] == "review_required"
    assert load_report["requested_execution"] is True
    assert load_report["executed"] is False
    assert load_report["success_count"] == 0
    assert load_report["failure_count"] == 0
    assert load_report["skipped_count"] == load_report["statement_count"]
    assert load_report["connection"]["is_configured"] is False
    assert all(
        row["diagnostics"]["reason"] == "reconnaissance_gate_not_ready"
        for row in load_report["results"]
    )


def test_materialize_graph_artifacts_executes_live_load_with_override_and_client(
    tmp_path: Path,
) -> None:
    corpus_dir = tmp_path / "knowledge_base"
    (corpus_dir / "CORE ya Arriba" / "normativa").mkdir(parents=True)
    (corpus_dir / "to upload").mkdir(parents=True)
    (corpus_dir / "CORE ya Arriba" / "normativa" / "renta.md").write_text(
        """
## Artículo 1. Renta liquida cedular
Modificado por la Ley 2277 de 2022.
Conforme al artículo 2 del E.T., debe conservar soporte.

## Artículo 2. Definiciones especiales
Se entiende por ingreso gravado el valor sometido al impuesto.
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (corpus_dir / "to upload" / "PATCH_renta.md").write_text(
        "Insertar en: CORE ya Arriba/normativa/renta.md\n\nAgregar paragrafo final.\n",
        encoding="utf-8",
    )

    def fake_executor(statement, config):
        return GraphQueryResult(
            description=statement.description,
            query=statement.query,
            parameters=statement.parameters,
            stats={"nodes_created": 1, "relationships_created": 0},
            diagnostics={"configured_url": config.redacted_url},
        )

    graph_client = GraphClient(
        config=GraphClientConfig(url="redis://lia:secret@example.com:6379/0"),
        executor=fake_executor,
    )
    artifacts_dir = tmp_path / "artifacts"
    result = materialize_graph_artifacts(
        corpus_dir=corpus_dir,
        artifacts_dir=artifacts_dir,
        execute_load=True,
        allow_unblessed_load=True,
        graph_client=graph_client,
    )

    load_report = result["graph_load_report"]
    assert result["reconnaissance_quality_gate"]["status"] == "review_required"
    assert load_report["requested_execution"] is True
    assert load_report["executed"] is True
    assert load_report["success_count"] == load_report["statement_count"]
    assert load_report["failure_count"] == 0
    assert load_report["skipped_count"] == 0
    assert load_report["connection"]["is_configured"] is True
    assert load_report["connection"]["url"] == "redis://lia:***@example.com:6379"
    assert all(row["ok"] is True for row in load_report["results"])


def test_graph_client_execute_many_reuses_single_live_connection(monkeypatch) -> None:
    class FakeSocket:
        def __init__(self) -> None:
            self._buffer = b""
            self.closed = False

        def settimeout(self, timeout: float) -> None:
            self.timeout = timeout

        def sendall(self, data: bytes) -> None:
            assert b"GRAPH.QUERY" in data
            self._buffer += _resp_value([["Nodes created: 1"]])

        def recv(self, size: int) -> bytes:
            if not self._buffer:
                return b""
            chunk = self._buffer[:size]
            self._buffer = self._buffer[size:]
            return chunk

        def close(self) -> None:
            self.closed = True

        def __enter__(self) -> "FakeSocket":
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            self.close()

    connection_attempts: list[tuple[tuple[str, int], float]] = []
    sockets: list[FakeSocket] = []

    def fake_create_connection(address: tuple[str, int], timeout: float) -> FakeSocket:
        connection_attempts.append((address, timeout))
        sock = FakeSocket()
        sockets.append(sock)
        return sock

    monkeypatch.setattr("lia_graph.graph.client.socket.create_connection", fake_create_connection)

    client = GraphClient(config=GraphClientConfig(url="redis://127.0.0.1:6379"))
    statements = (
        GraphWriteStatement(description="one", query="RETURN 1"),
        GraphWriteStatement(description="two", query="RETURN 2"),
    )

    results = client.execute_many(statements, strict=True)

    assert len(connection_attempts) == 1
    assert [result.description for result in results] == ["one", "two"]
    assert all(result.ok is True for result in results)
    assert all(result.stats["nodes_created"] == 1 for result in results)
    assert sockets[0].closed is True


def _resp_value(value: object) -> bytes:
    if isinstance(value, list):
        payload = [f"*{len(value)}\r\n".encode("utf-8")]
        payload.extend(_resp_value(item) for item in value)
        return b"".join(payload)
    encoded = str(value).encode("utf-8")
    return b"".join(
        [
            f"${len(encoded)}\r\n".encode("utf-8"),
            encoded,
            b"\r\n",
        ]
    )


def test_classifier_falls_back_when_edge_kind_is_invalid_for_target() -> None:
    candidate = RawEdgeCandidate(
        source_kind=NodeKind.ARTICLE,
        source_key="10",
        target_kind=NodeKind.REFORM,
        target_key="DECRETO-0173-s_f",
        raw_reference="Decreto 0173",
        context="No requiere solicitud. Decreto 0173 Art. 2-3.",
        relation_hint="REQUIRES",
    )

    classified = classify_edge_candidates([candidate])

    assert len(classified) == 1
    assert classified[0].record.kind.value == "REFERENCES"
    assert classified[0].rule == "fallback_reference"


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
    taxonomy_version = topic_taxonomy_version()

    assert included.ingestion_decision == "include_corpus"
    assert included.source_origin == "core_ya_arriba"
    assert included.family == "normativa"
    assert included.knowledge_class == "normative_base"
    assert included.source_type == "ley"
    assert included.source_tier == "normativo"
    assert included.authority_level == "primary_legal_authority"
    assert included.graph_target is True
    assert included.graph_parse_ready is True
    assert included.parse_strategy == "markdown_graph_parse"
    assert included.document_archetype == "base_doc"
    assert included.topic_key == "declaracion_renta"
    assert included.subtopic_key is None
    assert included.vocabulary_status == "ratified_v1_2"
    assert included.taxonomy_version == taxonomy_version
    assert included.to_dict()["taxonomy_version"] == taxonomy_version
    assert included.review_priority == "none"
    assert included.ambiguity_flags == ()

    assert revision.ingestion_decision == "revision_candidate"
    assert revision.parse_strategy == "revision_merge_candidate"
    assert revision.document_archetype == "revision_patch"
    assert revision.base_doc_target == "CORE ya Arriba/normativa/renta.md"
    assert revision.authority_level == "revision_instruction"
    assert revision.review_priority == "high"
    assert "revision_candidate_requires_merge_review" in revision.ambiguity_flags

    assert excluded.ingestion_decision == "exclude_internal"
    assert excluded.parse_strategy == "excluded_internal"
    assert excluded.document_archetype == "working_note"
    assert excluded.decision_reason == "Excluded working state file."


def test_audit_corpus_documents_handles_branch_drafts_and_raw_root_working_files(
    tmp_path: Path,
) -> None:
    corpus_dir = tmp_path / "Corpus"
    (
        corpus_dir
        / "CORE ya Arriba"
        / "Documents to branch and improve"
        / "Devoluciones_Saldos_Favor"
        / "Normativa_Base"
    ).mkdir(parents=True)
    (
        corpus_dir
        / "CORE ya Arriba"
        / "Documents to branch and improve"
        / "Devoluciones_Saldos_Favor"
        / "Interpretacion_Expertos"
    ).mkdir(parents=True)
    (
        corpus_dir
        / "CORE ya Arriba"
        / "Documents to branch and improve"
        / "Devoluciones_Saldos_Favor"
        / "Practica_LOGGRO"
    ).mkdir(parents=True)
    (
        corpus_dir
        / "CORE ya Arriba"
        / "Documents to branch and improve"
        / "to_upload"
    ).mkdir(parents=True)
    (corpus_dir / "SELF-IMPROVEMENT").mkdir(parents=True)
    (corpus_dir / "Improvement_Corpus").mkdir(parents=True)

    (
        corpus_dir
        / "CORE ya Arriba"
        / "Documents to branch and improve"
        / "Devoluciones_Saldos_Favor"
        / "Normativa_Base"
        / "dev_normativa_devoluciones.md"
    ).write_text(
        """
## Artículo 815. Compensación de saldos a favor
La compensación procede conforme al Estatuto Tributario.
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (
        corpus_dir
        / "CORE ya Arriba"
        / "Documents to branch and improve"
        / "Devoluciones_Saldos_Favor"
        / "Interpretacion_Expertos"
        / "dev_expertos_devoluciones.md"
    ).write_text(
        "# Interpretación profesional\n\nAnálisis experto sobre devoluciones y compensaciones.\n",
        encoding="utf-8",
    )
    (
        corpus_dir
        / "CORE ya Arriba"
        / "Documents to branch and improve"
        / "Devoluciones_Saldos_Favor"
        / "Practica_LOGGRO"
        / "dev_practica_devoluciones.md"
    ).write_text(
        "# Guía práctica\n\nPaso a paso y checklist operativo para devolución.\n",
        encoding="utf-8",
    )
    (
        corpus_dir
        / "CORE ya Arriba"
        / "Documents to branch and improve"
        / "to_upload"
        / "dev_fragmento.md"
    ).write_text(
        "# Fragmento\n\nParte 01 para branch interno.\n",
        encoding="utf-8",
    )
    (corpus_dir / "SELF-IMPROVEMENT" / "fixes-run5.md").write_text(
        "# Fixes Recomendados\n\nPost eval run 5.\n",
        encoding="utf-8",
    )
    (corpus_dir / "Improvement_Corpus" / "100-preguntas.md").write_text(
        "# 100 preguntas\n\nDataset interno para evaluación del corpus.\n",
        encoding="utf-8",
    )
    (corpus_dir / "CLAUDE.md").write_text(
        "# Instrucciones\n\nOperador interno.\n",
        encoding="utf-8",
    )
    (corpus_dir / "DECRETOS-state.md").write_text(
        "# Estado\n\nTracker de decretos.\n",
        encoding="utf-8",
    )

    audit_rows = audit_corpus_documents(corpus_dir=corpus_dir)
    rows_by_path = {row.relative_path: row for row in audit_rows}

    normativa = rows_by_path[
        "CORE ya Arriba/Documents to branch and improve/Devoluciones_Saldos_Favor/Normativa_Base/dev_normativa_devoluciones.md"
    ]
    interpretacion = rows_by_path[
        "CORE ya Arriba/Documents to branch and improve/Devoluciones_Saldos_Favor/Interpretacion_Expertos/dev_expertos_devoluciones.md"
    ]
    practica = rows_by_path[
        "CORE ya Arriba/Documents to branch and improve/Devoluciones_Saldos_Favor/Practica_LOGGRO/dev_practica_devoluciones.md"
    ]
    fragment = rows_by_path[
        "CORE ya Arriba/Documents to branch and improve/to_upload/dev_fragmento.md"
    ]
    self_improvement = rows_by_path["SELF-IMPROVEMENT/fixes-run5.md"]
    improvement_corpus = rows_by_path["Improvement_Corpus/100-preguntas.md"]
    claude = rows_by_path["CLAUDE.md"]
    decretos_state = rows_by_path["DECRETOS-state.md"]

    assert normativa.ingestion_decision == "include_corpus"
    assert normativa.family == "normativa"
    assert normativa.graph_target is True
    assert normativa.graph_parse_ready is True

    assert interpretacion.ingestion_decision == "include_corpus"
    assert interpretacion.family == "interpretacion"
    assert interpretacion.graph_target is False
    assert interpretacion.parse_strategy == "markdown_inventory_only"

    assert practica.ingestion_decision == "include_corpus"
    assert practica.family == "practica"
    assert practica.graph_target is False
    assert practica.parse_strategy == "markdown_inventory_only"

    assert fragment.ingestion_decision == "exclude_internal"
    assert fragment.decision_reason == (
        "Excluded branch-staging fragment pending consolidation into accountant-facing documents."
    )

    assert self_improvement.ingestion_decision == "exclude_internal"
    assert improvement_corpus.ingestion_decision == "exclude_internal"
    assert claude.ingestion_decision == "exclude_internal"
    assert decretos_state.ingestion_decision == "exclude_internal"


def test_audit_corpus_documents_maps_imported_folders_to_expected_topics(
    tmp_path: Path,
) -> None:
    corpus_dir = tmp_path / "knowledge_base"
    fixtures = {
        "CORE ya Arriba/Documents to branch and improve/Devoluciones_Saldos_Favor/Interpretacion_Expertos/dev_expertos_devoluciones.md": (
            "# Devoluciones\n\nAnálisis experto sobre saldos a favor.\n",
            "procedimiento_tributario",
        ),
        "CORE ya Arriba/to update/FE-ROADMAP-NUEVOS-DOCS-2026/FASE-1-CONTENIDO/LOGGRO/FE-06-roadmap-ecosistema-electronico-DIAN-2026-2027.md": (
            "# Roadmap FE\n\nGuía práctica del ecosistema de documentos electrónicos.\n",
            "facturacion_electronica",
        ),
        "to upload/URLS-PIPELINE-DIAN/EXPERTOS/EXPERTOS_Pipeline-regulatorio-DIAN-monitoreo-proyectos-normatividad.md": (
            "# Pipeline regulatorio\n\nComentario experto sobre monitoreo normativo DIAN.\n",
            "procedimiento_tributario",
        ),
        "CORE ya Arriba/REGIMEN_CAMBIARIO_PYME/LOGGRO/L01-guia-practica-regimen-cambiario-pyme.md": (
            "# Régimen cambiario\n\nPaso a paso para operaciones de cambio.\n",
            "cambiario",
        ),
        "CORE ya Arriba/PRECIOS_TRANSFERENCIA_SIMPLIFICADO/EXPERTOS/PRT-E01-interpretaciones-precios-transferencia-simplificado-PYME.md": (
            "# Precios de transferencia\n\nAnálisis experto para PYME.\n",
            "precios_de_transferencia",
        ),
        "CORE ya Arriba/Documents to branch and improve/Revisoria_Fiscal/Practica_LOGGRO/rev_practica_revisoria_fiscal.md": (
            "# Revisoría fiscal\n\nChecklist práctico para la sociedad.\n",
            "comercial_societario",
        ),
        "CORE ya Arriba/Documents to branch and improve/Tributacion_Dividendos/Practica_LOGGRO/div_practica_dividendos.md": (
            "# Dividendos\n\nGuía práctica de distribución de utilidades.\n",
            "dividendos_utilidades",
        ),
        "CORE ya Arriba/NUEVOS-DATOS-BRECHAS-MARZO-2026/02-MAPA-EMERGENCIA-CONSOLIDADO/INTERPRETACION/T-EME-CONSOLIDADO-emergencia-interpretaciones-expertos.md": (
            "# Emergencia tributaria\n\nAnálisis experto consolidado del Decreto 0240.\n",
            "emergencia_tributaria",
        ),
    }

    for relative_path, (content, _) in fixtures.items():
        path = corpus_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    audit_rows = audit_corpus_documents(corpus_dir=corpus_dir)
    rows_by_path = {row.relative_path: row for row in audit_rows}

    for relative_path, (_, expected_topic_key) in fixtures.items():
        row = rows_by_path[relative_path]
        assert row.ingestion_decision == "include_corpus"
        assert row.topic_key == expected_topic_key
        assert row.vocabulary_status == "ratified_v1_2"


def test_audit_corpus_documents_uses_allowed_path_prefixes_for_topic_assignment(
    tmp_path: Path,
    monkeypatch,
) -> None:
    taxonomy_path = tmp_path / "topic_taxonomy.json"
    taxonomy_path.write_text(
        json.dumps(
            {
                "version": "test_v1",
                "topics": [
                    {
                        "key": "comercial_societario",
                        "label": "Comercial y societario",
                        "aliases": ["comercial_societario"],
                        "ingestion_aliases": ["societario"],
                        "legacy_document_topics": ["comercial_societario"],
                        "allowed_path_prefixes": [
                            "CORE ya Arriba/LEYES/COMERCIAL_SOCIETARIO/"
                        ],
                        "vocabulary_status": "ratified_v1_2",
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("LIA_TOPIC_TAXONOMY_PATH", str(taxonomy_path))
    load_topic_taxonomy.cache_clear()

    try:
        corpus_dir = tmp_path / "knowledge_base"
        doc_dir = corpus_dir / "CORE ya Arriba" / "LEYES" / "COMERCIAL_SOCIETARIO"
        doc_dir.mkdir(parents=True)
        (doc_dir / "Ley-1258-2008.md").write_text(
            "# Ley 1258 de 2008\n\nSociedades por acciones simplificadas.\n",
            encoding="utf-8",
        )

        audit_rows = audit_corpus_documents(corpus_dir=corpus_dir)
        row = {row.relative_path: row for row in audit_rows}[
            "CORE ya Arriba/LEYES/COMERCIAL_SOCIETARIO/Ley-1258-2008.md"
        ]

        assert row.topic_key == "comercial_societario"
        assert row.subtopic_key is None
        assert row.vocabulary_status == "ratified_v1_2"
        assert row.taxonomy_version == "test_v1"
    finally:
        load_topic_taxonomy.cache_clear()


def test_audit_corpus_documents_does_not_flag_base_document_phrases_as_revision(
    tmp_path: Path,
) -> None:
    corpus_dir = tmp_path / "knowledge_base"
    (corpus_dir / "CORE ya Arriba" / "RENTA" / "EXPERTOS").mkdir(parents=True)
    doc_path = (
        corpus_dir
        / "CORE ya Arriba"
        / "RENTA"
        / "EXPERTOS"
        / "T12-facturacion-electronica-soportes-interpretaciones.md"
    )
    doc_path.write_text(
        """
# T12 — Facturación Electrónica y Soportes: Interpretaciones de Expertos

La base documental de la conciliación fiscal debe ser consistente.
La DIAN exige aplicar sobretasa solo en los eventos previstos en la ley.
""".strip()
        + "\n",
        encoding="utf-8",
    )

    audit_rows = audit_corpus_documents(corpus_dir=corpus_dir)
    row = {row.relative_path: row for row in audit_rows}[
        "CORE ya Arriba/RENTA/EXPERTOS/T12-facturacion-electronica-soportes-interpretaciones.md"
    ]

    assert row.ingestion_decision == "include_corpus"
    assert row.document_archetype == "base_doc"
    assert row.base_doc_target is None


def test_audit_corpus_documents_infers_revision_target_from_filename_hint(
    tmp_path: Path,
) -> None:
    corpus_dir = tmp_path / "knowledge_base"
    (corpus_dir / "CORE ya Arriba" / "RENTA" / "EXPERTOS").mkdir(parents=True)
    (corpus_dir / "to upload").mkdir(parents=True)
    (
        corpus_dir
        / "CORE ya Arriba"
        / "RENTA"
        / "EXPERTOS"
        / "T-B-costos-deducciones-fuentes-secundarias.md"
    ).write_text(
        "# T-B\n\nDocumento base interpretativo.\n",
        encoding="utf-8",
    )
    (
        corpus_dir
        / "to upload"
        / "A-2_PATCH-T-B-art-105-interpretaciones.md"
    ).write_text(
        "# A-2: PATCH-T-B — Art. 105 ET: Interpretaciones\n\nParche interpretativo.\n",
        encoding="utf-8",
    )

    audit_rows = audit_corpus_documents(corpus_dir=corpus_dir)
    revision = {row.relative_path: row for row in audit_rows}[
        "to upload/A-2_PATCH-T-B-art-105-interpretaciones.md"
    ]

    assert revision.ingestion_decision == "revision_candidate"
    assert (
        revision.base_doc_target
        == "CORE ya Arriba/RENTA/EXPERTOS/T-B-costos-deducciones-fuentes-secundarias.md"
    )


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
    assert exogena_row.subtopic_key is None
    assert exogena_row.vocabulary_status == "ratified_v1_2"
    assert exogena_row.review_priority == "none"
    assert exogena_row.ambiguity_flags == ()


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
    assert row.review_priority == "high"
    assert "graph_target_not_parse_ready" in row.ambiguity_flags


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
    assert result["reconnaissance_quality_gate"]["status"] == "review_required"
    assert result["graph_target_families"] == ["normativa"]
    assert result["graph_target_document_count"] == 2
    assert result["graph_parse_ready_document_count"] == 1
    assert result["article_count"] == 2

    audit_report_path = artifacts_dir / "corpus_audit_report.json"
    reconnaissance_report_path = artifacts_dir / "corpus_reconnaissance_report.json"
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
    assert reconnaissance_report_path.exists()
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
    reconnaissance_report = json.loads(reconnaissance_report_path.read_text(encoding="utf-8"))
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
    assert reconnaissance_report["quality_gate"]["status"] == "review_required"
    assert reconnaissance_report["quality_gate"]["canonical_blessing_allowed"] is False
    assert reconnaissance_report["manual_review_queue_count"] == 3
    assert reconnaissance_report["revision_linkage_status_counts"] == {
        "attached_to_base_doc": 1,
        "not_applicable": 5,
    }
    assert reconnaissance_report["authority_level_counts"]["primary_legal_authority"] == 2
    assert reconnaissance_report["authority_level_counts"]["revision_instruction"] == 1
    assert reconnaissance_report["canonical_blessing_status_counts"] == {
        "excluded": 1,
        "pending_merge_review": 1,
        "ready": 2,
        "review_required": 2,
    }
    assert revision_candidates["count"] == 1
    assert excluded_files["count"] == 1
    assert canonical_manifest["document_count"] == 4
    assert canonical_manifest["canonical_ready_count"] == 2
    assert canonical_manifest["review_required_count"] == 2
    assert canonical_manifest["blocked_count"] == 0
    assert canonical_manifest["documents_with_pending_revisions"] == 1
    assert canonical_manifest["unresolved_revision_candidate_count"] == 0
    renta_manifest = next(
        row
        for row in canonical_manifest["documents"]
        if row["relative_path"] == "CORE ya Arriba/normativa/renta.md"
    )
    pdf_manifest = next(
        row
        for row in canonical_manifest["documents"]
        if row["relative_path"] == "CORE ya Arriba/normativa/concepto_001.pdf"
    )
    assert renta_manifest["canonical_ready"] is False
    assert renta_manifest["canonical_blessing_status"] == "review_required"
    assert renta_manifest["pending_revision_count"] == 1
    assert pdf_manifest["canonical_ready"] is False
    assert pdf_manifest["canonical_blessing_status"] == "review_required"
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
    assert corpus_inventory["taxonomy_version"] == topic_taxonomy_version()
    assert corpus_inventory["topic_key_counts"]["declaracion_renta"] == 1
    assert corpus_inventory["subtopic_key_counts"]["[none]"] == 4
    assert corpus_inventory["graph_target_document_count"] == 2
    assert corpus_inventory["graph_parse_ready_document_count"] == 1
    assert any(row["parse_strategy"] == "binary_inventory_only" for row in corpus_inventory["documents"])
    assert any(row["vocabulary_status"] == "ratified_v1_2" for row in corpus_inventory["documents"])
    assert all(
        row["taxonomy_version"] == topic_taxonomy_version()
        for row in corpus_inventory["documents"]
    )
    assert any(row["family"] == "interpretacion" for row in corpus_inventory["documents"])
    assert any(row["family"] == "practica" for row in corpus_inventory["documents"])
    assert len(parsed_lines) == 2
    assert any(json.loads(line)["kind"] == "COMPUTATION_DEPENDS_ON" for line in typed_lines)
    assert load_report["executed"] is False
    assert validation_report["ok"] is True


def test_reconnaissance_gate_blocks_unknown_corpus_shape_and_unresolved_revision(
    tmp_path: Path,
) -> None:
    corpus_dir = tmp_path / "knowledge_base"
    (corpus_dir / "CORE ya Arriba" / "normativa").mkdir(parents=True)
    (corpus_dir / "CORE ya Arriba" / "misc").mkdir(parents=True)
    (corpus_dir / "to upload").mkdir(parents=True)
    (corpus_dir / "CORE ya Arriba" / "normativa" / "renta.md").write_text(
        """
## Artículo 1. Renta liquida cedular
Modificado por la Ley 2277 de 2022.
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (corpus_dir / "CORE ya Arriba" / "misc" / "nota_ambigua.md").write_text(
        "# Nota operativa\n\nDocumento mixto sin familia clara ni autoridad verificable.\n",
        encoding="utf-8",
    )
    (corpus_dir / "to upload" / "PATCH_sin_target.md").write_text(
        "Agregar nota final sin target declarado.\n",
        encoding="utf-8",
    )

    artifacts_dir = tmp_path / "artifacts"
    result = materialize_graph_artifacts(
        corpus_dir=corpus_dir,
        artifacts_dir=artifacts_dir,
    )

    assert result["reconnaissance_quality_gate"]["status"] == "blocked"
    reconnaissance_report = json.loads(
        (artifacts_dir / "corpus_reconnaissance_report.json").read_text(encoding="utf-8")
    )
    canonical_manifest = json.loads(
        (artifacts_dir / "canonical_corpus_manifest.json").read_text(encoding="utf-8")
    )

    assert reconnaissance_report["quality_gate"]["blocker_count"] == 2
    assert reconnaissance_report["revision_linkage_status_counts"] == {
        "missing_base_doc_target": 1,
        "not_applicable": 2,
    }
    assert reconnaissance_report["canonical_blessing_status_counts"] == {
        "blocked": 2,
        "ready": 1,
    }
    assert any(
        row["relative_path"] == "CORE ya Arriba/misc/nota_ambigua.md"
        and row["canonical_blessing_status"] == "blocked"
        for row in reconnaissance_report["rows"]
    )
    assert any(
        row["relative_path"] == "to upload/PATCH_sin_target.md"
        and row["canonical_blessing_status"] == "blocked"
        for row in reconnaissance_report["rows"]
    )
    assert canonical_manifest["blocked_count"] == 1
    assert canonical_manifest["canonical_ready_count"] == 1


def test_audit_and_inventory_materialize_parent_and_child_taxonomy(
    tmp_path: Path,
) -> None:
    corpus_dir = tmp_path / "knowledge_base"
    (corpus_dir / "CORE ya Arriba" / "RENTA" / "NORMATIVA").mkdir(parents=True)
    (
        corpus_dir
        / "CORE ya Arriba"
        / "RENTA"
        / "NORMATIVA"
        / "renta.md"
    ).write_text(
        """
## Artículo 1. Renta liquida cedular
Modificado por la Ley 2277 de 2022.
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (
        corpus_dir
        / "CORE ya Arriba"
        / "RENTA"
        / "NORMATIVA"
        / "costos_y_deducciones_art_107.md"
    ).write_text(
        """
# Costos y deducciones - Art. 107

Expensas necesarias y medios de pago para deduccion.
""".strip()
        + "\n",
        encoding="utf-8",
    )

    audit_rows = audit_corpus_documents(corpus_dir=corpus_dir)
    rows_by_path = {row.relative_path: row for row in audit_rows}
    taxonomy_version = topic_taxonomy_version()

    renta_row = rows_by_path["CORE ya Arriba/RENTA/NORMATIVA/renta.md"]
    child_row = rows_by_path["CORE ya Arriba/RENTA/NORMATIVA/costos_y_deducciones_art_107.md"]

    assert renta_row.topic_key == "declaracion_renta"
    assert renta_row.subtopic_key is None
    assert renta_row.taxonomy_version == taxonomy_version

    assert child_row.topic_key == "declaracion_renta"
    assert child_row.subtopic_key == "costos_deducciones_renta"
    assert child_row.vocabulary_status == "ratified_v1_2"
    assert child_row.taxonomy_version == taxonomy_version

    artifacts_dir = tmp_path / "artifacts"
    materialize_graph_artifacts(
        corpus_dir=corpus_dir,
        artifacts_dir=artifacts_dir,
    )
    corpus_inventory = json.loads(
        (artifacts_dir / "corpus_inventory.json").read_text(encoding="utf-8")
    )

    assert corpus_inventory["taxonomy_version"] == taxonomy_version
    assert corpus_inventory["topic_key_counts"] == {
        "declaracion_renta": 2,
    }
    # Phase A4+A5: the classifier pass validates subtopic_keys against the
    # curated taxonomy. ``costos_deducciones_renta`` is produced by the
    # legacy regex vocabulary but is NOT in the curated taxonomy, so it
    # is dropped from the classified CorpusDocument (and thus the
    # inventory view, which is the post-classifier snapshot).
    assert corpus_inventory["subtopic_key_counts"] == {"[none]": 2}
    assert corpus_inventory["topic_subtopic_coverage"] == {
        "declaracion_renta": {
            "direct_document_count": 2,
            "subtopic_document_count": 0,
            "subtopic_counts": {},
        }
    }
    serialized_child = next(
        row
        for row in corpus_inventory["documents"]
        if row["relative_path"] == "CORE ya Arriba/RENTA/NORMATIVA/costos_y_deducciones_art_107.md"
    )
    assert serialized_child["taxonomy_version"] == taxonomy_version
    assert serialized_child["topic_key"] == "declaracion_renta"
    # subtopic_key is dropped by A4 validation because it's not in taxonomy.
    assert serialized_child["subtopic_key"] is None
