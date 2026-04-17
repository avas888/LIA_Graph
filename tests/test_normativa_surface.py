from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlparse

from lia_graph.normativa.assembly import build_normativa_modal_payload
from lia_graph.citation_resolution import document_reference_semantics
from lia_graph.normativa.shared import NormativaSection, NormativaSynthesis
from lia_graph.normativa.synthesis import synthesize_normativa_surface
from lia_graph.normative_references import extract_normative_reference_mentions
from lia_graph.ui_citation_controllers import handle_citation_get
import lia_graph.normative_analysis as normative_analysis
import lia_graph.ui_citation_profile_builders as citation_builders


def test_normativa_surface_does_not_import_main_chat_answer_layers() -> None:
    package_dir = Path(__file__).resolve().parents[1] / "src" / "lia_graph" / "normativa"
    python_files = sorted(package_dir.glob("*.py"))
    assert python_files
    for path in python_files:
        text = path.read_text(encoding="utf-8")
        assert "pipeline_d.answer_" not in text
        assert "answer_first_bubble" not in text
        assert "answer_assembly" not in text
        assert "answer_synthesis" not in text


def test_llm_citation_profile_payload_uses_normativa_surface(monkeypatch) -> None:
    fake_ui = type(
        "FakeUI",
        (),
        {
            "_normalize_citation_profile_text": staticmethod(
                lambda value, max_chars=320: str(value or "").strip()[:max_chars]
            ),
        },
    )
    monkeypatch.setattr(citation_builders, "_ui", lambda: fake_ui)
    monkeypatch.setattr(
        "lia_graph.normativa.orchestrator.run_normativa_surface",
        lambda context: (
            {"query_mode": "article_lookup"},
            {
                "synthesis": NormativaSynthesis(
                    lead="Lead graph-native.",
                    professional_impact="- Revisa soporte.\n- Contrasta vigencia.",
                    sections=(
                        NormativaSection(
                            id="scope",
                            title="Qué mirar en esta norma",
                            body="- Línea uno.\n- Línea dos.",
                        ),
                    ),
                )
            },
        ),
    )

    payload = citation_builders._llm_citation_profile_payload({"title": "Ley 2277 de 2022"})

    assert payload["lead"] == "Lead graph-native."
    assert payload["professional_impact"] == "- Revisa soporte.\n- Contrasta vigencia."
    assert payload["sections_payload"] == [
        {
            "id": "scope",
            "title": "Qué mirar en esta norma",
            "body": "- Línea uno.\n- Línea dos.",
        }
    ]


def test_build_normative_analysis_payload_uses_normativa_surface(monkeypatch) -> None:
    monkeypatch.setattr(
        normative_analysis,
        "run_normativa_surface",
        lambda context: (
            {"query_mode": "reform_chain"},
            {
                "synthesis": NormativaSynthesis(
                    lead="Reforma tributaria con impacto operativo.",
                    sections=(
                        NormativaSection(
                            id="impacto",
                            title="Impacto para contadores",
                            body="Prioriza vigencia material y trazabilidad.",
                        ),
                    ),
                )
            },
        ),
    )

    payload = normative_analysis.build_normative_analysis_payload(
        {
            "title": "Ley 2277 de 2022",
            "document_family": "ley",
            "document_profile": {
                "document_family": "ley",
                "family_subtype": "ley_ordinaria",
                "hierarchy_tier": "legal_primario",
                "binding_force": "Ley o estatuto",
                "binding_force_rank": 900,
                "analysis_template_id": "primary_law_analysis",
                "ui_surface": "deep_analysis",
                "allowed_secondary_overlays": ["jurisprudencia", "concepto_dian"],
                "caution_banner": {
                    "title": "Revisa vigencia material",
                    "body": "Contrasta si el artículo fue modificado por norma posterior.",
                    "tone": "warning",
                },
            },
            "requested_row": {},
            "citation": {},
            "related_rows": [],
            "rows_by_doc_id": {},
        },
        preview_facts=[{"label": "Qué regula", "value": "Ajusta reglas de renta."}],
        source_action={"label": "Ir a documento original", "url": "/source-view?doc_id=doc_law_2277"},
        companion_action=None,
        runtime_config_path="unused",
    )

    assert payload["lead"] == "Reforma tributaria con impacto operativo."
    assert payload["binding_force"] == "Ley o estatuto"
    assert payload["sections"] == [
        {
            "id": "impacto",
            "title": "Impacto para contadores",
            "body": "Prioriza vigencia material y trazabilidad.",
        }
    ]
    assert payload["recommended_actions"][0]["url"] == "/source-view?doc_id=doc_law_2277"


def test_synthesize_normativa_surface_builds_policy_driven_parts_and_sections() -> None:
    evidence = SimpleNamespace(
        primary_articles=(
            SimpleNamespace(
                excerpt="La disposición fija el alcance inmediato de la obligación consultada.",
            ),
        ),
        connected_articles=(),
        related_reforms=(
            SimpleNamespace(
                title="Ley 2277 de 2022",
                why="Introduce una reforma que debe contrastarse con la lectura vigente.",
            ),
        ),
        support_documents=(
            SimpleNamespace(
                title_hint="Guía operativa de renta",
                reason="topic_support_doc",
            ),
        ),
    )

    synthesis = synthesize_normativa_surface(
        context={
            "title": "Artículo 147 ET",
            "document_profile": {"binding_force": "Ley o estatuto"},
        },
        evidence=evidence,
        query_mode="article_lookup",
    )

    assert synthesis.lead == "La disposición fija el alcance inmediato de la obligación consultada."
    assert "ley o estatuto" in synthesis.hierarchy_summary.lower()
    assert "Guía operativa de renta" in synthesis.professional_impact
    assert "Ley 2277 de 2022" in synthesis.relations_summary
    assert [section.id for section in synthesis.sections] == [
        "normativa_scope",
        "normativa_practical",
        "normativa_relations",
    ]
    payload = build_normativa_modal_payload(synthesis)
    assert payload["sections_payload"][2]["title"] == "Relaciones útiles detectadas"


def test_synthesize_normativa_surface_falls_back_to_default_section_when_evidence_is_thin() -> None:
    evidence = SimpleNamespace(
        primary_articles=(),
        connected_articles=(),
        related_reforms=(),
        support_documents=(),
    )

    synthesis = synthesize_normativa_surface(
        context={
            "title": "Resolución 000001 de 2024",
            "document_profile": {"binding_force": "Resolución administrativa"},
        },
        evidence=evidence,
        query_mode="reform_chain",
    )

    assert synthesis.sections == (
        NormativaSection(
            id="normativa_default",
            title="Lectura inicial",
            body=(
                "Resolución 000001 de 2024 requiere contraste con el documento original y con sus desarrollos o modificaciones "
                "antes de convertirlo en instrucción cerrada."
            ),
        ),
    )
    assert synthesis.caution_text.startswith("El grafo no encontró un anclaje primario")


def test_citation_controller_llm_phase_preserves_contract() -> None:
    class _Handler:
        sent: tuple[int, dict[str, object]] | None = None

        def _send_json(self, status: int, payload: dict[str, object]) -> None:
            self.sent = (status, payload)

    handler = _Handler()
    parsed = urlparse("/api/citation-profile?doc_id=doc_law_2277&phase=llm")
    ok = handle_citation_get(
        handler,
        parsed.path,
        parsed,
        deps={
            "collect_citation_profile_context": lambda *args, **kwargs: {"citation": {}},
            "collect_citation_profile_context_by_reference_key": lambda *args, **kwargs: None,
            "apply_citation_profile_request_context": lambda context, **kwargs: context,
            "should_skip_citation_profile_llm": lambda context: False,
            "llm_citation_profile_payload": lambda context: {
                "lead": "Lead enriquecido.",
                "sections_payload": [
                    {
                        "id": "impacto",
                        "title": "Impacto para contadores",
                        "body": "Contenido enriquecido.",
                    }
                ],
            },
            "build_citation_profile_lead": lambda context, llm_payload=None: str((llm_payload or {}).get("lead") or ""),
            "build_citation_profile_facts": lambda context, llm_payload=None: [{"label": "Tipo", "value": "Ley"}],
            "build_citation_profile_sections": lambda context, llm_payload=None: list((llm_payload or {}).get("sections_payload") or []),
            "render_citation_profile_payload": lambda *args, **kwargs: {},
            "render_normative_analysis_payload": lambda *args, **kwargs: {},
            "build_structured_vigencia_detail": lambda *args, **kwargs: {},
            "summarize_vigencia_llm": lambda *args, **kwargs: "",
            "citation_targets_et_article": lambda citation: False,
            "index_file_path": Path("unused.jsonl"),
        },
    )

    assert ok is True
    assert handler.sent is not None
    status, payload = handler.sent
    assert status == 200
    assert payload == {
        "ok": True,
        "phase": "llm",
        "lead": "Lead enriquecido.",
        "facts": [{"label": "Tipo", "value": "Ley"}],
        "sections": [
            {
                "id": "impacto",
                "title": "Impacto para contadores",
                "body": "Contenido enriquecido.",
            }
        ],
    }


def test_build_fallback_citation_profile_payload_for_et_article(monkeypatch) -> None:
    fake_ui = type(
        "FakeUI",
        (),
        {
            "_clean_markdown_inline": staticmethod(lambda value: str(value or "").strip()),
            "_clip_session_content": staticmethod(lambda value, max_chars=320: str(value or "")[:max_chars]),
            "_prefer_normograma_mintic_mirror": staticmethod(lambda url: str(url)),
        },
    )
    monkeypatch.setattr(citation_builders, "_ui", lambda: fake_ui)
    monkeypatch.setattr(
        citation_builders,
        "_lookup_parsed_et_article",
        lambda locator_start: {
            "heading": "Firmeza de las declaraciones tributarias",
            "full_text": (
                "ARTICULO 714. La declaración tributaria quedará en firme si dentro de los tres años "
                "siguientes no se ha notificado requerimiento especial."
            ),
        }
        if locator_start == "714"
        else None,
    )

    payload = citation_builders._build_fallback_citation_profile_payload(
        reference_key="et",
        locator_start="714",
    )

    assert payload["title"] == "Estatuto Tributario, Artículo 714"
    assert payload["document_family"] == "et_dur"
    assert payload["lead"] == (
        "El Artículo 714 del Estatuto Tributario regula firmeza de las declaraciones tributarias."
    )
    assert payload["facts"] == [
        {
            "label": "Artículo consultado",
            "value": "ET Artículo 714. Firmeza de las declaraciones tributarias.",
        }
    ]
    assert payload["original_text"] == {
        "title": "Texto normativo disponible en artifacts",
        "quote": (
            "ARTICULO 714. La declaración tributaria quedará en firme si dentro de los tres años "
            "siguientes no se ha notificado requerimiento especial."
        ),
        "source_url": "https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario.htm#714",
        "evidence_status": "verified",
    }
    assert payload["analysis_action"]["state"] == "not_applicable"
    assert payload["companion_action"]["state"] == "not_applicable"
    assert payload["source_action"]["url"] == (
        "https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario.htm#714"
    )


def test_citation_controller_instant_phase_uses_et_fallback_payload() -> None:
    class _Handler:
        sent: tuple[int, dict[str, object]] | None = None

        def _send_json(self, status: int, payload: dict[str, object]) -> None:
            self.sent = (status, payload)

    handler = _Handler()
    parsed = urlparse(
        "/api/citation-profile?reference_key=et&locator_start=714&locator_text=Art%C3%ADculo%20714&phase=instant"
    )
    ok = handle_citation_get(
        handler,
        parsed.path,
        parsed,
        deps={
            "collect_citation_profile_context": lambda *args, **kwargs: None,
            "collect_citation_profile_context_by_reference_key": lambda *args, **kwargs: None,
            "build_fallback_citation_profile_payload": lambda **kwargs: {
                "title": "Estatuto Tributario, Artículo 714",
                "document_family": "et_dur",
                "lead": "Fallback local.",
                "facts": [{"label": "Artículo consultado", "value": "ET Artículo 714"}],
                "sections": [],
                "original_text": {
                    "title": "Texto normativo disponible en artifacts",
                    "quote": "ARTICULO 714.",
                    "source_url": "https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario.htm#714",
                    "evidence_status": "verified",
                },
                "analysis_action": {
                    "label": "Abrir análisis normativo",
                    "state": "not_applicable",
                    "url": None,
                    "helper_text": None,
                },
                "companion_action": {
                    "label": "¿Quieres una guía sobre cómo llenarlo?",
                    "state": "not_applicable",
                    "url": None,
                    "helper_text": None,
                },
                "source_action": {
                    "label": "Ir a documento original",
                    "state": "available",
                    "url": "https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario.htm#714",
                    "helper_text": None,
                },
            },
            "apply_citation_profile_request_context": lambda context, **kwargs: context,
            "should_skip_citation_profile_llm": lambda context: False,
            "llm_citation_profile_payload": lambda context: {},
            "build_citation_profile_lead": lambda context, llm_payload=None: "",
            "build_citation_profile_facts": lambda context, llm_payload=None: [],
            "build_citation_profile_sections": lambda context, llm_payload=None: [],
            "render_citation_profile_payload": lambda *args, **kwargs: {},
            "render_normative_analysis_payload": lambda *args, **kwargs: {},
            "build_structured_vigencia_detail": lambda *args, **kwargs: {},
            "summarize_vigencia_llm": lambda *args, **kwargs: "",
            "citation_targets_et_article": lambda citation: False,
            "index_file_path": Path("unused.jsonl"),
        },
    )

    assert ok is True
    assert handler.sent is not None
    status, payload = handler.sent
    assert status == 200
    assert payload["ok"] is True
    assert payload["needs_llm"] is False
    assert payload["title"] == "Estatuto Tributario, Artículo 714"
    assert payload["lead"] == "Fallback local."


def test_format_form_reference_title_strips_redundant_manifest_prefix(monkeypatch) -> None:
    fake_ui = type(
        "FakeUI",
        (),
        {
            "_spanish_title_case": staticmethod(citation_builders._spanish_title_case),
        },
    )
    monkeypatch.setattr(citation_builders, "_ui", lambda: fake_ui)

    title = citation_builders._format_form_reference_title(
        "Formulario 2516",
        "Formato 2516 - Conciliación fiscal para obligados a llevar contabilidad",
    )

    assert title == "Formato 2516: Conciliación Fiscal para Obligados a Llevar Contabilidad"


def test_extract_normative_reference_mentions_keeps_formato_label_but_canonicalizes_key() -> None:
    references = extract_normative_reference_mentions("Formato 2517 y Formulario 110.")

    assert references[0]["reference_key"] == "formulario:2517"
    assert references[0]["reference_type"] == "formulario"
    assert references[0]["reference_text"] == "Formato 2517"
    assert references[1]["reference_key"] == "formulario:110"
    assert references[1]["reference_text"] == "Formulario 110"


def test_document_reference_semantics_treats_formato_official_doc_as_canonical_form() -> None:
    semantics = document_reference_semantics(
        {
            "title": "Formato 2517 oficial",
            "relative_path": (
                "knowledge_base/normativa/renta/corpus_legal/C_DIAN_Formularios_y_Operacion/"
                "articulos/dian_formato_2517_oficial.md"
            ),
            "tipo_de_documento": "formulario",
            "knowledge_class": "normative_base",
            "source_type": "official_primary",
        }
    )

    assert semantics["entity_id"] == "formulario:2517"
    assert semantics["entity_type"] == "formulario"
    assert semantics["relation_type"] == "canonical_for"


def test_collect_citation_profile_context_by_reference_key_uses_local_form_guide_package(
    monkeypatch,
    tmp_path: Path,
) -> None:
    guide_dir = tmp_path / "formulario_2516" / "pj_obligados_contabilidad"
    guide_dir.mkdir(parents=True)
    (guide_dir / "guide_manifest.json").write_text(
        json.dumps(
            {
                "reference_key": "formulario:2516",
                "title": "Formato 2516 - Conciliación fiscal para obligados a llevar contabilidad",
                "form_version": "Versión 9",
                "profile_id": "pj_obligados_contabilidad",
                "profile_label": "Persona Jurídica - Obligados a Llevar Contabilidad",
                "supported_views": ["structured", "interactive"],
            }
        ),
        encoding="utf-8",
    )
    (guide_dir / "sources.json").write_text(
        json.dumps(
            [
                {
                    "source_id": "src_dian_f2516",
                    "title": "Guía oficial DIAN",
                    "url": "https://www.dian.gov.co/formulario-2516.pdf",
                    "source_type": "formulario_oficial_pdf",
                    "authority": "DIAN",
                    "is_primary": True,
                }
            ]
        ),
        encoding="utf-8",
    )

    fake_ui = type(
        "FakeUI",
        (),
        {
            "FORM_GUIDES_ROOT": tmp_path,
            "_find_reference_doc_id": staticmethod(lambda *args, **kwargs: ""),
            "_normalize_citation_profile_text": staticmethod(lambda value, max_chars=320: str(value or "").strip()[:max_chars]),
            "_format_form_reference_title": staticmethod(citation_builders._format_form_reference_title),
            "_reference_label_from_key": staticmethod(lambda key: f"Formulario {str(key).split(':', 1)[1].upper()}"),
            "_guide_primary_source_payload": staticmethod(
                lambda package: {
                    "official_url": getattr((package.sources or [None])[0], "url", "") if package is not None else "",
                    "authority": getattr((package.sources or [None])[0], "authority", "DIAN") if package is not None else "DIAN",
                    "source_provider": getattr((package.sources or [None])[0], "authority", "DIAN") if package is not None else "DIAN",
                }
            ),
            "_load_index_rows_by_doc_id": staticmethod(lambda index_file=None: {}),
            "_spanish_title_case": staticmethod(citation_builders._spanish_title_case),
        },
    )
    monkeypatch.setattr(citation_builders, "_ui", lambda: fake_ui)

    context = citation_builders._collect_citation_profile_context_by_reference_key(
        "Formulario:2516",
        index_file=tmp_path / "unused.jsonl",
    )

    assert context is not None
    assert context["document_family"] == "formulario"
    assert context["title"] == "Formato 2516: Conciliación Fiscal para Obligados a Llevar Contabilidad"
    assert context["citation"]["reference_key"] == "formulario:2516"
    assert context["citation"]["official_url"] == "https://www.dian.gov.co/formulario-2516.pdf"
    assert context["requested_row"]["relative_path"] == (
        "form_guides/formulario_2516/pj_obligados_contabilidad/guide_manifest.json"
    )


def test_collect_citation_profile_context_by_reference_key_returns_generic_form_context_without_guide(
    monkeypatch,
    tmp_path: Path,
) -> None:
    fake_ui = type(
        "FakeUI",
        (),
        {
            "FORM_GUIDES_ROOT": tmp_path,
            "_find_reference_doc_id": staticmethod(lambda *args, **kwargs: ""),
            "_normalize_citation_profile_text": staticmethod(lambda value, max_chars=320: str(value or "").strip()[:max_chars]),
            "_format_form_reference_title": staticmethod(citation_builders._format_form_reference_title),
            "_reference_label_from_key": staticmethod(lambda key: f"Formulario {str(key).split(':', 1)[1].upper()}"),
            "_guide_primary_source_payload": staticmethod(
                lambda package: {"official_url": "", "authority": "DIAN", "source_provider": "DIAN"}
            ),
            "_load_index_rows_by_doc_id": staticmethod(lambda index_file=None: {}),
            "_spanish_title_case": staticmethod(citation_builders._spanish_title_case),
        },
    )
    monkeypatch.setattr(citation_builders, "_ui", lambda: fake_ui)

    context = citation_builders._collect_citation_profile_context_by_reference_key(
        "Formulario:195",
        index_file=tmp_path / "unused.jsonl",
    )

    assert context is not None
    assert context["document_family"] == "formulario"
    assert context["title"] == "Formulario 195"
    assert context["citation"]["reference_key"] == "formulario:195"
    assert context["citation"]["official_url"] == ""
    assert context["requested_row"]["relative_path"] == "form_guides/formulario_195/default/guide_manifest.json"
