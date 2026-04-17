from __future__ import annotations

from pathlib import Path

from lia_graph.pipeline_c.contracts import PipelineCRequest
from lia_graph.pipeline_d import answer_support
from lia_graph.pipeline_d.answer_support import (
    extract_article_insights,
    extract_support_doc_insights,
)
from lia_graph.pipeline_d.contracts import GraphEvidenceItem, GraphSupportDocument


def _write_support_doc(tmp_path: Path, name: str, text: str) -> str:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path.name


def _support_doc(*, source_path: str, title_hint: str = "Doc practica") -> GraphSupportDocument:
    return GraphSupportDocument(
        relative_path=source_path,
        source_path=source_path,
        title_hint=title_hint,
        family="practica",
        knowledge_class="guia",
        topic_key="declaracion_renta",
        subtopic_key=None,
        canonical_blessing_status="ready",
        graph_target=True,
        reason="topic_support_doc",
    )


def test_extract_support_doc_insights_projects_planning_candidates_into_bucket_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source_path = _write_support_doc(
        tmp_path,
        "planeacion.md",
        """
- Antes del cierre compare RST y ordinario si hay perdidas fiscales acumuladas y documente el proposito comercial de la estructura.
- Documente papeles de trabajo y certificaciones del revisor fiscal antes de presentar la declaracion.
- Existe riesgo de rechazo si el beneficio fiscal no tiene proposito economico verificable.
""".strip(),
    )
    monkeypatch.setattr(answer_support, "_WORKSPACE_ROOT", tmp_path)

    insights = extract_support_doc_insights(
        request=PipelineCRequest(
            message=(
                "En una planeacion tributaria legitima, con proposito comercial y riesgo de abuso, "
                "que estrategia y checklist debo revisar antes del cierre?"
            )
        ),
        support_documents=(_support_doc(source_path=source_path, title_hint="Planeacion tributaria"),),
    )

    assert insights["strategy"]
    assert any("rst" in line.lower() for line in insights["strategy"])
    assert insights["jurisprudence"]
    assert any("proposito economico" in line.lower() for line in insights["jurisprudence"])
    assert insights["checklist"]
    assert any("papeles de trabajo" in line.lower() for line in insights["checklist"])


def test_extract_support_doc_insights_skips_planning_only_docs_for_non_planning_queries(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source_path = _write_support_doc(
        tmp_path,
        "planeacion.md",
        """
- Antes del cierre compare RST y ordinario si hay perdidas fiscales acumuladas y documente el proposito comercial de la estructura.
""".strip(),
    )
    monkeypatch.setattr(answer_support, "_WORKSPACE_ROOT", tmp_path)

    insights = extract_support_doc_insights(
        request=PipelineCRequest(message="Como presento la declaracion de renta de una sociedad?"),
        support_documents=(_support_doc(source_path=source_path, title_hint="Planeacion tributaria"),),
    )

    assert insights == {
        "procedure": (),
        "paperwork": (),
        "context": (),
        "precaution": (),
        "strategy": (),
        "jurisprudence": (),
        "checklist": (),
    }


def test_extract_support_doc_insights_keeps_loss_compensation_lines_focused_on_that_workflow(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source_path = _write_support_doc(
        tmp_path,
        "perdidas.md",
        """
- La compensacion de perdidas fiscales se imputa contra la renta liquida ordinaria y extiende el termino de firmeza de la declaracion.
- Documente la politica de cierre comercial para otra estrategia distinta.
""".strip(),
    )
    monkeypatch.setattr(answer_support, "_WORKSPACE_ROOT", tmp_path)

    insights = extract_support_doc_insights(
        request=PipelineCRequest(
            message=(
                "Mi cliente tiene perdidas fiscales de anos anteriores y en AG 2025 tiene renta liquida positiva. "
                "Como opera la compensacion y la firmeza?"
            )
        ),
        support_documents=(_support_doc(source_path=source_path, title_hint="Perdidas fiscales"),),
    )

    surfaced = {
        line
        for bucket_lines in insights.values()
        for line in bucket_lines
    }

    assert surfaced
    assert all("perdidas fiscales" in line.lower() or "renta liquida" in line.lower() for line in surfaced)


def test_extract_article_insights_projects_ranked_buckets_from_article_candidates() -> None:
    insights = extract_article_insights(
        request=PipelineCRequest(
            message=(
                "En una planeacion tributaria legitima con proposito comercial, "
                "que soportes y riesgos debo revisar antes del cierre?"
            )
        ),
        temporal_context={},
        primary_articles=(
            GraphEvidenceItem(
                node_kind="ArticleNode",
                node_key="869",
                title="Abuso en materia tributaria",
                excerpt=(
                    "El contribuyente debe verificar soportes y certificados antes del cierre. "
                    "Existe riesgo de rechazo si no demuestra proposito comercial y beneficio fiscal."
                ),
                source_path=None,
                score=5.0,
                hop_distance=0,
            ),
        ),
        connected_articles=(),
    )

    assert insights["procedure"]
    assert any("verificar soportes" in line.lower() for line in insights["procedure"])
    assert insights["paperwork"]
    assert any("certificados" in line.lower() for line in insights["paperwork"])
    assert insights["precaution"]
    assert any("riesgo de rechazo" in line.lower() for line in insights["precaution"])
    assert insights["jurisprudence"]
    assert any("proposito comercial" in line.lower() for line in insights["jurisprudence"])
