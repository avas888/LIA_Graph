"""LLM prompt, payload, and facts builders for the citation-profile modal.

Extracted from `ui_citation_profile_builders.py` during granularize-v2
round 12c. Functions:

  * ``_build_citation_profile_prompt(context)`` — produces the JSON-
    constrained prompt for the normativa surface LLM. Keyed by
    ``document_family`` (ley / decreto / formulario / concepto / …).
  * ``_llm_citation_profile_payload(context)`` — runs the prompt via
    the normativa surface orchestrator and normalizes the response.
  * ``_should_skip_citation_profile_llm(context)`` — returns True for
    document families that should use deterministic builders only
    (currently formulario — the form-guide path renders the whole card
    deterministically).
  * ``_append_citation_profile_fact`` / ``_build_citation_profile_facts``
    — produce the `[{label, value}, …]` list rendered in the modal's
    facts strip (publish_date, vigencia, latest_identified, etc.).

All collaborators flow through the lazy ``_ui()`` accessor so existing
monkeypatch-based tests keep working when they patch either this
module or the host.
"""

from __future__ import annotations

import re
from typing import Any


def _ui() -> Any:
    """Lazy accessor for `lia_graph.ui_server` (avoids circular import)."""
    from . import ui_server as _mod
    return _mod



def _build_citation_profile_prompt(context: dict[str, Any]) -> str:
    family = str(context.get("document_family") or "generic").strip()
    title = str(context.get("title") or "Documento").strip()
    citation = dict(context.get("citation") or {})
    requested_row = dict(context.get("requested_row") or {})
    material = dict(context.get("material") or {})
    texts = _ui()._collect_citation_profile_texts(context)
    snippets = []
    for text in texts[:5]:
        for sentence in _ui()._split_sentences(text)[:2]:
            snippets.append(f"- {sentence}")
            if len(snippets) >= 6:
                break
        if len(snippets) >= 6:
            break
    snippets_block = "\n".join(snippets) or "- Sin extractos utilizables."

    focus = {
        "formulario": (
            "explica para qué sirve el formulario, "
            "indica desde qué año gravable o periodo fiscal empezó a ser obligatorio (fecha concreta o resolución que lo prescribió), "
            "y cómo impacta el trabajo del contador"
        ),
        "constitucion": "explica qué principio o marco constitucional aporta y por qué importa para la lectura tributaria",
        "ley": "explica qué regula la ley, su propósito regulatorio y el impacto para la profesión contable",
        "decreto": "explica qué regula el decreto, su propósito regulatorio y el impacto para la profesión contable",
        "resolucion": "explica qué fija la resolución, su propósito regulatorio y el impacto para la profesión contable",
        "et_dur": "explica qué regula la norma compilada o estatutaria y el impacto para la profesión contable",
        "concepto": "explica qué criterio fija el documento y qué implica para contadores",
        "circular": "explica qué lineamiento fija la circular y qué implica para contadores",
        "jurisprudencia": "explica qué problema jurídico resolvió, cuál fue la decisión central y su relevancia vigente",
        "generic": "explica qué es el documento y por qué le sirve a un contador",
    }.get(family, "explica el documento seleccionado de forma útil para un contador")

    metadata_lines = [
        f"titulo={title}",
        f"familia={family}",
        f"source_label={citation.get('source_label') or ''}",
        f"legal_reference={citation.get('legal_reference') or ''}",
        f"authority={citation.get('authority') or requested_row.get('authority') or ''}",
        f"publish_date={requested_row.get('publish_date') or ''}",
        f"effective_date={requested_row.get('effective_date') or ''}",
        f"vigencia={requested_row.get('vigencia') or ''}",
        f"notes={requested_row.get('notes') or ''}",
    ]
    source_text = _ui()._clip_session_content(
        str(material.get("usable_text") or material.get("public_text") or "\n\n".join(texts)).strip(),
        max_chars=7000,
    )
    return (
        "Eres editor legal y tributario para contadores.\n"
        "Tu tarea es construir una ficha breve y creíble del documento seleccionado.\n"
        f"Enfócate en: {focus}.\n"
        "Usa únicamente metadata explícita y extractos del documento seleccionado o de sus variantes lógicas.\n"
        "No menciones corpus, pipeline, metadata interna, checksums, part_XX, doc_id, provider ni source_tier.\n"
        "Si un dato no está soportado, omítelo.\n"
        "Responde SOLO JSON válido con llaves opcionales entre estas:\n"
        '{"lead":"","purpose_text":"","mandatory_when":"","regulatory_purpose":"","criterion_text":"","problem_resolved":"","decision_core":"","relevance_text":"","professional_impact":""}\n'
        "mandatory_when: para formularios debe indicar DESDE CUÁNDO es obligatorio (año gravable, periodo, o resolución que lo prescribió), NO para quién.\n"
        "Cada valor debe ser breve, directo y anclado al documento seleccionado.\n\n"
        "metadata:\n"
        f"{chr(10).join(metadata_lines)}\n\n"
        "extractos:\n"
        f"{snippets_block}\n\n"
        "texto_fuente:\n"
        f"{source_text}\n"
    )


def _llm_citation_profile_payload(context: dict[str, Any]) -> dict[str, Any]:
    try:
        from .normativa.assembly import build_normativa_modal_payload
        from .normativa.orchestrator import run_normativa_surface

        _diagnostics, runtime_payload = run_normativa_surface(context)
        synthesis = runtime_payload.get("synthesis")
    except Exception:  # noqa: BLE001
        return {}
    if synthesis is None:
        return {}
    payload = build_normativa_modal_payload(synthesis)
    normalized: dict[str, Any] = {}
    for key, value in payload.items():
        if key == "sections_payload" and isinstance(value, list):
            sections: list[dict[str, str]] = []
            for item in value:
                if not isinstance(item, dict):
                    continue
                title = _ui()._normalize_citation_profile_text(item.get("title"), max_chars=120)
                body = str(item.get("body") or "").strip()
                body = re.sub(r"\n{3,}", "\n\n", body)
                if not title or not body:
                    continue
                sections.append(
                    {
                        "id": str(item.get("id") or "").strip() or "normativa_section",
                        "title": title,
                        "body": body,
                    }
                )
            if sections:
                normalized["sections_payload"] = sections
            continue
        clean = _ui()._normalize_citation_profile_text(value, max_chars=320)
        if clean:
            normalized[str(key)] = clean
    return normalized


def _should_skip_citation_profile_llm(context: dict[str, Any]) -> bool:
    family = str(context.get("document_family") or "").strip().lower()
    if not family:
        profile = dict(context.get("document_profile") or {})
        family = str(profile.get("document_family") or "").strip().lower()
    if not family:
        family = _ui()._classify_document_family(
            dict(context.get("citation") or {}),
            dict(context.get("requested_row") or {}),
        ).strip().lower()
    return family == "formulario"


def _append_citation_profile_fact(facts: list[dict[str, str]], label: str, value: str) -> None:
    clean_value = _ui()._normalize_citation_profile_text(value, max_chars=180)
    if not clean_value:
        return
    if any(item.get("label") == label for item in facts):
        return
    facts.append({"label": label, "value": clean_value})


def _build_citation_profile_facts(context: dict[str, Any], llm_payload: dict[str, str] | None = None) -> list[dict[str, str]]:
    payload = dict(llm_payload or {})
    row = dict(context.get("requested_row") or {})
    rows = list(context.get("related_rows") or [row])
    rows_by_doc_id = dict(context.get("rows_by_doc_id") or {})
    family = str(context.get("document_family") or "generic").strip()
    texts = _ui()._collect_citation_profile_texts(context)
    citation = dict(context.get("citation") or {})

    latest_identified = _ui()._latest_identified_citation_profile_date(rows)
    publish_date = _ui()._format_citation_profile_date(row.get("publish_date")) or _ui()._format_citation_profile_date(row.get("effective_date"))
    normative_year = _ui()._extract_normative_year(context)
    official_date = _ui()._official_publish_date_or_year(
        row.get("publish_date") or row.get("effective_date") or "", normative_year,
    )
    vigencia = str(row.get("vigencia", "")).strip().lower()
    vigencia_text = ""
    if vigencia and vigencia != "desconocida":
        if vigencia == "vigente":
            vigencia_text = "Vigente"
        elif vigencia == "derogada":
            replacement = _ui()._resolve_superseded_label(row, rows_by_doc_id)
            vigencia_text = f"No vigente. {replacement}".strip() if replacement else "No vigente"
        else:
            vigencia_text = vigencia.capitalize()
    elif str(row.get("superseded_by", "")).strip():
        replacement = _ui()._resolve_superseded_label(row, rows_by_doc_id)
        vigencia_text = f"Tiene reemplazo registrado. {replacement}".strip() if replacement else "Tiene reemplazo registrado."

    facts: list[dict[str, str]] = []
    if _ui()._citation_targets_et_article(citation):
        et_row = _ui()._resolve_et_locator_row(context)
        et_meta: dict[str, str] = {}
        if et_row is not None:
            et_analysis = _ui()._build_source_view_candidate_analysis(et_row, view="normalized")
            et_meta = _ui()._extract_et_article_metadata(str(et_analysis.get("raw_text") or ""))
        article_display = (
            str(et_meta.get("article_number_display") or "").strip()
            or _ui()._citation_et_locator_label(citation)
        )
        article_title = str(et_meta.get("article_title") or "").strip()
        vigencia_detail = _ui()._build_et_article_vigencia_detail(context)
        if article_display:
            label = f"Artículo consultado"
            value = f"ET Artículo {article_display}"
            if article_title:
                value = f"{value}. {article_title}."
            _ui()._append_citation_profile_fact(facts, label, value)
        _ui()._append_citation_profile_fact(
            facts,
            "Vigencia específica",
            "\n".join(
                item
                for item in (
                    vigencia_detail.get("label"),
                    vigencia_detail.get("basis"),
                    vigencia_detail.get("notes"),
                    f"Última verificación del corpus: {vigencia_detail.get('last_verified_date')}"
                    if str(vigencia_detail.get("last_verified_date") or "").strip()
                    else "",
                )
                if str(item or "").strip()
            ),
        )
        return facts

    if family == "formulario":
        purpose_text = payload.get("purpose_text") or _ui()._find_grounded_profile_sentence(
            texts,
            keywords=(
                "sirve",
                "report",
                "liquid",
                "impuesto",
                "declaración",
                "declaracion",
                "presentar",
            ),
        )
        mandatory_when = payload.get("mandatory_when") or _ui()._find_grounded_profile_sentence(
            texts,
            keywords=(
                "prescrit",
                "resoluci",
                "año gravable",
                "ano gravable",
                "obligad",
                "debe",
                "deberá",
                "debera",
                "aplica",
                "utilizar",
            ),
        )
        if mandatory_when and vigencia_text == "Vigente" and "vigente" not in mandatory_when.lower():
            mandatory_when = f"{mandatory_when} Sigue vigente."
        _ui()._append_citation_profile_fact(facts, "Para qué sirve", purpose_text)
        _ui()._append_citation_profile_fact(facts, "Desde cuándo es obligatorio", mandatory_when)
        _ui()._append_citation_profile_fact(facts, "Última actualización identificada", latest_identified)
        return facts

    if family == "constitucion":
        constitutional_anchor = payload.get("regulatory_purpose") or _ui()._find_grounded_profile_sentence(
            texts,
            keywords=("constitución", "constitucion", "principio", "garantiza", "reserva", "debido proceso"),
        )
        _ui()._append_citation_profile_fact(facts, "Marco constitucional", constitutional_anchor)
        _ui()._append_citation_profile_fact(facts, "Fecha de referencia", publish_date)
        _ui()._append_citation_profile_fact(facts, "Vigencia", vigencia_text or "Vigente")
        return facts

    if family in {"ley", "decreto", "resolucion", "et_dur"}:
        regulatory_purpose = payload.get("regulatory_purpose") or _ui()._find_grounded_profile_sentence(
            texts,
            keywords=("objeto", "finalidad", "propósito", "proposito", "regula", "establece", "define", "compila"),
        )
        _ui()._append_citation_profile_fact(facts, "Fecha de expedición", official_date)
        _ui()._append_citation_profile_fact(facts, "Propósito regulatorio", regulatory_purpose)
        if vigencia_text:
            _ui()._append_citation_profile_fact(facts, "Vigencia", vigencia_text)
        return facts

    if family in {"concepto", "circular"}:
        _ui()._append_citation_profile_fact(facts, "Emisión", official_date)
        _ui()._append_citation_profile_fact(facts, "Estado de vigencia/reemplazo", vigencia_text)
        _ui()._append_citation_profile_fact(facts, "Última actualización identificada", latest_identified)
        return facts

    if family == "jurisprudencia":
        decision_core = payload.get("decision_core") or _ui()._find_grounded_profile_sentence(
            texts,
            keywords=("decid", "resolv", "declaró", "declaro", "determin", "conclu"),
        )
        relevance = payload.get("relevance_text") or vigencia_text
        _ui()._append_citation_profile_fact(facts, "Fecha", official_date)
        _ui()._append_citation_profile_fact(facts, "Decisión central", decision_core)
        _ui()._append_citation_profile_fact(facts, "Relevancia vigente", relevance)
        return facts

    # Expert/interpretative documents: extract structured metadata from body text
    expert_meta = _extract_expert_body_metadata(context)
    if expert_meta:
        normas = expert_meta.get("normas_base", "").strip()
        if normas:
            _ui()._append_citation_profile_fact(facts, "Normas base", normas)
        ambito = expert_meta.get("ambito_aplicacion", "").strip()
        if ambito:
            _ui()._append_citation_profile_fact(facts, "Ámbito de aplicación", ambito)
        fecha_verif = expert_meta.get("fecha_verificacion", "").strip()
        if fecha_verif:
            _ui()._append_citation_profile_fact(facts, "Fecha de última verificación", fecha_verif)
        if not normas and not ambito:
            _ui()._append_citation_profile_fact(facts, "Fecha identificada", official_date or latest_identified)
            _ui()._append_citation_profile_fact(facts, "Vigencia", vigencia_text)
        return facts

    _ui()._append_citation_profile_fact(facts, "Fecha identificada", official_date or latest_identified)
    _ui()._append_citation_profile_fact(facts, "Vigencia", vigencia_text)
    return facts
