from __future__ import annotations

from http import HTTPStatus
from pathlib import Path
from types import SimpleNamespace

import lia_graph.interpretacion.orchestrator as interpretacion_orchestrator
import lia_graph.ui_analysis_controllers as analysis_controllers
from lia_graph.contracts.document import DocumentRecord
from lia_graph.interpretacion.orchestrator import (
    run_citation_interpretations_request,
    run_expert_panel_enhance_request,
    run_expert_panel_explore_request,
    run_expert_panel_request,
    run_interpretation_summary_request,
)
from lia_graph.ui_expert_extractors import (
    _expand_expert_panel_requested_refs,
    _expert_card_summary,
    _expert_extended_excerpt,
    _prioritize_expert_panel_docs,
    _resolve_doc_expert_providers,
)
from lia_graph.ui_source_view_processors import (
    _classify_provider,
    _dedupe_interpretation_docs,
    _filter_provider_links,
    _summarize_snippet,
)


def _doc(
    *,
    doc_id: str,
    authority: str,
    provider_label: str,
    score: float,
    normative_refs: tuple[str, ...] = ("et_art_147",),
) -> DocumentRecord:
    return DocumentRecord(
        doc_id=doc_id,
        relative_path=f"interpretacion/{doc_id}.md",
        absolute_path=f"/tmp/{doc_id}.md",
        category="interpretative_guidance",
        source_type="markdown",
        topic="renta",
        authority=authority,
        trust_tier="high",
        provider_labels=(provider_label,),
        normative_refs=normative_refs,
        retrieval_score=score,
        knowledge_class="interpretative_guidance",
    )


def _row_for(doc: DocumentRecord) -> dict[str, object]:
    return {
        "doc_id": doc.doc_id,
        "source_label": doc.authority,
        "legal_reference": doc.authority,
        "authority": doc.authority,
        "provider_labels": list(doc.provider_labels),
        "normative_refs": list(doc.normative_refs),
        "reference_identity_keys": list(doc.reference_identity_keys),
        "mentioned_reference_keys": list(doc.mentioned_reference_keys),
        "knowledge_class": "interpretative_guidance",
        "source_type": "markdown",
        "official_url": f"https://{doc.authority.lower().replace(' ', '')}.example.com/{doc.doc_id}",
    }


def _corpus_for(doc: DocumentRecord) -> str:
    return (
        f"# {doc.authority}\n\n"
        "El artículo 147 ET permite compensar pérdidas fiscales contra la renta líquida ordinaria cuando se documentan los saldos por vigencia. "
        "Como aplicar: verificar soportes, conservar trazabilidad del saldo y documentar el monto compensado.\n\n"
        f"[{doc.authority}](https://{doc.authority.lower().replace(' ', '')}.example.com/{doc.doc_id})"
    )


def _analysis_deps(docs: tuple[DocumentRecord, ...] = ()) -> dict[str, object]:
    rows = {doc.doc_id: _row_for(doc) for doc in docs}
    corpora = {doc.doc_id: _corpus_for(doc) for doc in docs}

    def _load_doc_corpus_text(doc_id: str, *, prefer_original: bool = False):
        del prefer_original
        return corpora.get(doc_id, ""), rows.get(doc_id, {})

    def _build_public_citation_from_row(row: dict[str, object]) -> dict[str, object]:
        doc_id = str(row.get("doc_id") or "").strip()
        source_label = str(row.get("source_label") or row.get("authority") or doc_id).strip()
        official_url = str(row.get("official_url") or "").strip()
        return {
            "doc_id": doc_id,
            "source_label": source_label,
            "legal_reference": str(row.get("legal_reference") or source_label).strip(),
            "authority": str(row.get("authority") or source_label).strip(),
            "knowledge_class": str(row.get("knowledge_class") or "interpretative_guidance").strip(),
            "source_type": str(row.get("source_type") or "markdown").strip(),
            "official_url": official_url or None,
            "open_url": official_url or None,
        }

    return {
        "build_extractive_interpretation_summary": lambda **kwargs: "## Lectura profesional\nFallback extractivo.",
        "build_interpretation_query_seed": lambda **kwargs: "artículo 147 ET pérdidas fiscales",
        "build_public_citation_from_row": _build_public_citation_from_row,
        "citation_cls": SimpleNamespace(from_document=lambda doc: SimpleNamespace(to_public_dict=lambda: {"doc_id": doc.doc_id})),
        "classify_provider": _classify_provider,
        "clip_session_content": lambda text, max_chars=18000: str(text or "")[:max_chars],
        "dedupe_interpretation_docs": _dedupe_interpretation_docs,
        "expand_expert_panel_requested_refs": _expand_expert_panel_requested_refs,
        "expert_card_summary": _expert_card_summary,
        "filter_provider_links": _filter_provider_links,
        "find_document_index_row": lambda doc_id: rows.get(doc_id),
        "generate_llm_strict": lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("llm unavailable")),
        "index_file_path": Path("unused.jsonl"),
        "llm_runtime_config_path": Path("unused-runtime.json"),
        "load_doc_corpus_text": _load_doc_corpus_text,
        "logical_doc_id": lambda doc_id: doc_id,
        "normalize_pais": lambda value: str(value or "colombia").strip().lower() or "colombia",
        "normalize_topic_key": lambda value: str(value or "").strip().lower() or None,
        "prioritize_expert_panel_docs": _prioritize_expert_panel_docs,
        "resolve_doc_expert_providers": _resolve_doc_expert_providers,
        "summarize_snippet": _summarize_snippet,
        "supported_topics": {"renta"},
        "warn_missing_active_index_generation": lambda: None,
    }


def test_expert_extended_excerpt_drops_trailing_orphan_heading_from_empty_section() -> None:
    # The source markdown carries a final section heading with no body under it
    # (the corpus section is genuinely empty). The extractor must omit the
    # heading entirely rather than rendering it stranded in the modal.
    markdown = (
        "# Mapa Completo\n\n"
        "## 2. Convergencias\n\n"
        "La firmeza general es de 3 años.\n\n"
        "## 3. Divergencias y Zonas Grises\n"
    )
    assert "Divergencias" not in _expert_extended_excerpt(markdown, max_chars=2500)


def test_expert_extended_excerpt_drops_trailing_orphan_heading_when_budget_overflows() -> None:
    # Heading fits but the paragraph under it does not fit in the remaining
    # budget — the heading would otherwise be emitted without any content.
    markdown = (
        "## 2. Convergencias\n\n"
        "Convergencia uno.\n\n"
        "## 3. Divergencias y Zonas Grises\n\n"
        + ("Contenido extenso bajo divergencias. " * 80)
    )
    excerpt = _expert_extended_excerpt(markdown, max_chars=120)
    assert "Convergencia uno" in excerpt
    assert "Divergencias" not in excerpt


def test_expert_extended_excerpt_keeps_heading_when_section_has_content() -> None:
    markdown = (
        "## 2. Convergencias\n\n"
        "Convergencia uno.\n\n"
        "## 3. Divergencias y Zonas Grises\n\n"
        "Existe una divergencia entre Actualicese y CR Consultores.\n"
    )
    excerpt = _expert_extended_excerpt(markdown, max_chars=2500)
    assert "Divergencias" in excerpt
    assert "Actualicese" in excerpt


def test_interpretacion_surface_does_not_import_main_chat_or_normativa_layers() -> None:
    package_dir = Path(__file__).resolve().parents[1] / "src" / "lia_graph" / "interpretacion"
    python_files = sorted(package_dir.glob("*.py"))
    assert python_files
    for path in python_files:
        text = path.read_text(encoding="utf-8")
        assert "pipeline_d.answer_" not in text
        assert "answer_first_bubble" not in text
        assert "answer_assembly" not in text
        assert "answer_synthesis" not in text
        assert "src/lia_graph/normativa" not in text
        assert "from ..normativa" not in text


def test_handle_analysis_post_dispatches_expert_routes(monkeypatch) -> None:
    seen: dict[str, object] = {}

    def _fake_runner(payload, *, deps):
        seen["payload"] = payload
        seen["deps"] = deps
        return HTTPStatus.OK, {"ok": True, "route": "expert-panel"}, None

    monkeypatch.setitem(analysis_controllers._ANALYSIS_POST_RUNNERS, "/api/expert-panel", _fake_runner)

    class _Handler:
        def __init__(self) -> None:
            self.sent: tuple[int, dict[str, object]] | None = None

        def _read_json_payload(self, *, object_error: str | None = None):
            del object_error
            return {"trace_id": "trace_test", "message": "Consulta de prueba"}

        def _send_json(self, status: int, payload: dict[str, object]) -> None:
            self.sent = (status, payload)

    handler = _Handler()
    handled = analysis_controllers.handle_analysis_post(handler, "/api/expert-panel", deps={"token": "ok"})

    assert handled is True
    assert seen["payload"] == {"trace_id": "trace_test", "message": "Consulta de prueba"}
    assert seen["deps"] == {"token": "ok"}
    assert handler.sent == (HTTPStatus.OK, {"ok": True, "route": "expert-panel"})


def test_run_expert_panel_request_uses_turn_kernel_without_waiting_on_normativa(monkeypatch) -> None:
    docs = (
        _doc(doc_id="interp_actualicese_147", authority="Actualícese", provider_label="Actualícese", score=0.96),
        _doc(doc_id="interp_deloitte_147", authority="Deloitte", provider_label="Deloitte", score=0.91),
    )
    deps = _analysis_deps(docs)
    monkeypatch.setattr(
        interpretacion_orchestrator,
        "_retrieve_interpretation_docs",
        lambda **kwargs: SimpleNamespace(
            docs_selected=list(docs),
            retrieval_diagnostics={"query": kwargs["query"], "knowledge_layer_filter": "interpretative_guidance"},
        ),
    )

    search_seed = "Consulta: pérdidas fiscales art. 147 ET\nTesis: aplica contra renta líquida ordinaria."
    status, payload, _ = run_expert_panel_request(
        {
            "trace_id": "trace_exp_1",
            "message": "¿Cómo aplico el artículo 147 ET a pérdidas fiscales?",
            "assistant_answer": "El artículo 147 ET permite compensar pérdidas fiscales con soporte por vigencia.",
            "normative_article_refs": ["art. 147 ET"],
            "search_seed": search_seed,
            "search_seed_origin": "deterministic",
            "topic": "renta",
            "pais": "colombia",
        },
        deps=deps,
    )

    assert status == HTTPStatus.OK
    assert payload["ok"] is True
    assert payload["groups"]
    assert payload["groups"][0]["article_ref"] == "et_art_147"
    assert payload["groups"][0]["requested_match"] is True
    assert payload["retrieval_diagnostics"]["expert_query_seed"] == search_seed
    assert payload["retrieval_diagnostics"]["expert_query_seed_origin"] == "deterministic"


def test_run_expert_panel_request_skips_malformed_provider_urls(monkeypatch) -> None:
    doc = _doc(doc_id="interp_actualicese_bad_url", authority="Actualícese", provider_label="Actualícese", score=0.96)
    deps = _analysis_deps((doc,))

    def _load_doc_corpus_text(doc_id: str, *, prefer_original: bool = False):
        del prefer_original
        if doc_id != doc.doc_id:
            return "", {}
        return (
            "# Actualícese\n\n"
            "Comentario profesional sobre el artículo 147 ET.\n\n"
            "[Fuente rota](https://[broken)\n"
            "[Fuente válida](https://actualicese.com/tributaria/perdidas-fiscales)",
            _row_for(doc),
        )

    deps["load_doc_corpus_text"] = _load_doc_corpus_text
    monkeypatch.setattr(
        interpretacion_orchestrator,
        "_retrieve_interpretation_docs",
        lambda **kwargs: SimpleNamespace(
            docs_selected=[doc],
            retrieval_diagnostics={"query": kwargs["query"], "knowledge_layer_filter": "interpretative_guidance"},
        ),
    )

    status, payload, _ = run_expert_panel_request(
        {
            "trace_id": "trace_exp_bad_url",
            "message": "¿Cómo aplico el artículo 147 ET a pérdidas fiscales?",
            "assistant_answer": "El artículo 147 ET permite compensar pérdidas fiscales con soporte por vigencia.",
            "normative_article_refs": ["art. 147 ET"],
            "search_seed": "Consulta: artículo 147 ET pérdidas fiscales",
            "search_seed_origin": "deterministic",
            "topic": "renta",
            "pais": "colombia",
        },
        deps=deps,
    )

    assert status == HTTPStatus.OK
    assert payload["ok"] is True
    snippets = payload["groups"][0]["snippets"] if payload["groups"] else payload["ungrouped"]
    assert snippets
    provider_links = snippets[0]["provider_links"]
    assert provider_links == [
        {
            "url": "https://actualicese.com/tributaria/perdidas-fiscales",
            "label": "Fuente válida",
            "provider": "Actualícese",
            "domain": "actualicese.com",
        }
    ]


def test_run_citation_interpretations_request_returns_cards(monkeypatch) -> None:
    docs = (
        _doc(doc_id="interp_actualicese_147", authority="Actualícese", provider_label="Actualícese", score=0.96),
        _doc(doc_id="interp_deloitte_147", authority="Deloitte", provider_label="Deloitte", score=0.91),
    )
    deps = _analysis_deps(docs)
    citation_row = {
        "doc_id": "renta_corpus_a_et_art_147",
        "source_label": "Artículo 147 ET",
        "legal_reference": "Artículo 147 ET",
        "authority": "ET",
        "normative_refs": ["et_art_147"],
        "reference_identity_keys": ["et:147"],
        "mentioned_reference_keys": [],
        "topic": "renta",
        "pais": "colombia",
    }
    deps["find_document_index_row"] = lambda doc_id: citation_row if doc_id == "renta_corpus_a_et_art_147" else _row_for(docs[0] if doc_id == docs[0].doc_id else docs[1])
    monkeypatch.setattr(
        interpretacion_orchestrator,
        "_retrieve_interpretation_docs",
        lambda **kwargs: SimpleNamespace(
            docs_selected=list(docs),
            retrieval_diagnostics={"query": kwargs["query"], "knowledge_layer_filter": "interpretative_guidance"},
        ),
    )

    status, payload, _ = run_citation_interpretations_request(
        {
            "trace_id": "trace_interp_1",
            "citation": {"doc_id": "renta_corpus_a_et_art_147", "source_label": "Artículo 147 ET"},
            "message_context": "Necesito ver interpretación profesional sobre pérdidas fiscales.",
            "assistant_answer": "El artículo 147 ET permite la compensación bajo ciertas verificaciones.",
            "top_k": 4,
            "process_limit": 3,
        },
        deps=deps,
    )

    assert status == HTTPStatus.OK
    assert payload["ok"] is True
    assert payload["citation_doc_id"] == "renta_corpus_a_et_art_147"
    assert payload["query_seed"] == "artículo 147 ET pérdidas fiscales"
    assert len(payload["interpretations"]) >= 1


def test_run_interpretation_summary_request_falls_back_to_extractive_mode() -> None:
    docs = (_doc(doc_id="interp_actualicese_147", authority="Actualícese", provider_label="Actualícese", score=0.96),)
    deps = _analysis_deps(docs)
    citation_row = {
        "doc_id": "renta_corpus_a_et_art_147",
        "source_label": "Artículo 147 ET",
        "legal_reference": "Artículo 147 ET",
        "authority": "ET",
        "normative_refs": ["et_art_147"],
    }
    deps["find_document_index_row"] = lambda doc_id: citation_row if doc_id == "renta_corpus_a_et_art_147" else _row_for(docs[0])

    status, payload, _ = run_interpretation_summary_request(
        {
            "trace_id": "trace_summary_1",
            "citation": {"doc_id": "renta_corpus_a_et_art_147", "source_label": "Artículo 147 ET"},
            "interpretation": {"doc_id": docs[0].doc_id, "title": "Actualícese"},
            "message_context": "¿Qué cambia en pérdidas fiscales pre-2017?",
        },
        deps=deps,
    )

    assert status == HTTPStatus.OK
    assert payload["ok"] is True
    assert payload["mode"] == "extractive_fallback"
    assert payload["summary_markdown"].startswith("## Lectura profesional")
    assert payload["grounding"]["citation"]["doc_id"] == "renta_corpus_a_et_art_147"
    assert payload["grounding"]["interpretation"]["doc_id"] == docs[0].doc_id


def test_run_expert_panel_enhance_request_falls_back_deterministically() -> None:
    status, payload, _ = run_expert_panel_enhance_request(
        {
            "trace_id": "trace_enhance_1",
            "message": "¿Cómo aplico el artículo 147 ET?",
            "assistant_answer": "Se puede compensar con soporte.",
            "cards": [
                {
                    "card_id": "card_1",
                    "classification": "concordancia",
                    "article_ref": "et_art_147",
                    "summary_signal": "Las fuentes convergen en la misma regla operativa.",
                    "dominant_signal": "permite",
                    "snippets": [
                        {"card_summary": "Explica la compensación y los soportes por vigencia."},
                    ],
                }
            ],
        },
        deps=_analysis_deps(),
    )

    assert status == HTTPStatus.OK
    assert payload["ok"] is True
    assert payload["llm_runtime"]["mode"] == "deterministic_fallback"
    assert payload["enhancements"][0]["card_id"] == "card_1"
    assert payload["enhancements"][0]["es_relevante"] is True


def test_run_expert_panel_explore_request_falls_back_deterministically() -> None:
    status, payload, _ = run_expert_panel_explore_request(
        {
            "trace_id": "trace_explore_1",
            "mode": "deep",
            "message": "¿Cómo aplico el artículo 147 ET?",
            "assistant_answer": "Se puede compensar con soporte.",
            "classification": "concordancia",
            "article_ref": "et_art_147",
            "summary_signal": "Las fuentes convergen en la misma regla operativa.",
            "snippets": [
                {
                    "authority": "Actualícese",
                    "card_summary": "Explica la compensación y los soportes por vigencia.",
                    "position_signal": "permite",
                }
            ],
        },
        deps=_analysis_deps(),
    )

    assert status == HTTPStatus.OK
    assert payload["ok"] is True
    assert payload["llm_runtime"]["mode"] == "deterministic_fallback"
    assert "Checklist operativo para el contador" in payload["content"]
