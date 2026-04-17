from __future__ import annotations

import html as html_mod
import json
import re
from dataclasses import replace
from datetime import datetime
from typing import Any
from urllib.parse import quote

from .normativa.assembly import build_normativa_analysis_payload as _assemble_normativa_analysis_payload
from .normativa.orchestrator import run_normativa_surface
from .normativa.shared import NormativaSection, NormativaSynthesis
from .normative_taxonomy import NormativeDocumentProfile, classify_normative_document
from .pipeline_c.orchestrator import generate_llm_strict

_MONTHS_ES = (
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
)
_INTERNAL_METADATA_RE = re.compile(r"\b(?:doc_id|part_[0-9]+|source_tier|checksum|pipeline)\b", re.IGNORECASE)
_NON_CONTENT_DOC_RE = re.compile(
    r"catalogo|catalog[_\-\s]|readme|\bindice\b|\bíndice\b|bloque[_\s]+\d"
    r"|rag[_\s]?ready|_ingest_|ingestion_rag",
    re.IGNORECASE,
)


def _clean_text(value: Any, *, max_chars: int = 320) -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip())
    if not text:
        return ""
    if _INTERNAL_METADATA_RE.search(text):
        return ""
    return text[:max_chars].strip()


def _split_sentences(text: str) -> list[str]:
    clean = re.sub(r"\s+", " ", str(text or "").strip())
    if not clean:
        return []
    return [item.strip() for item in re.split(r"(?<=[\.\?!:;])\s+", clean) if item.strip()]


def _safe_json_obj(raw: str) -> dict[str, Any]:
    if not raw:
        return {}
    candidate = str(raw).strip()
    if candidate.startswith("```"):
        candidate = candidate.strip("`").strip()
        if candidate.lower().startswith("json"):
            candidate = candidate[4:].strip()
    try:
        parsed = json.loads(candidate)
    except Exception:
        return {}
    return dict(parsed) if isinstance(parsed, dict) else {}


def _format_date_es(value: Any) -> str:
    clean = str(value or "").strip()
    if not clean:
        return ""
    try:
        parsed = datetime.fromisoformat(clean)
    except ValueError:
        return clean
    d = parsed.date()
    return f"{_MONTHS_ES[d.month - 1]} {d.day}, {d.year}"


def _find_best_sentence(texts: list[str], keywords: tuple[str, ...], *, max_chars: int = 300) -> str:
    best_sentence = ""
    best_score = 0
    for text in texts:
        for sentence in _split_sentences(text):
            lowered = sentence.lower()
            score = sum(1 for keyword in keywords if keyword in lowered)
            if score > best_score:
                best_sentence = sentence
                best_score = score
    return _clean_text(best_sentence, max_chars=max_chars) if best_score > 0 else ""


def _collect_texts(context: dict[str, Any]) -> list[str]:
    texts: list[str] = []
    material = dict(context.get("material") or {})
    for key in ("usable_text", "public_text", "raw_text"):
        clean = _clean_text(material.get(key), max_chars=7000)
        if clean:
            texts.append(clean)
    # Supplement with structured sections from RAG-ready markdown when
    # the above sources yielded thin text (common for decreto/resolucion
    # documents whose usable_text is just a short summary paragraph).
    if all(len(t) < 200 for t in texts):
        # Prefer requested_raw_text (the actual document) over material
        # raw_text which may be from a different document due to
        # provenance_uri collisions.
        raw_text = str(context.get("requested_raw_text") or "") or str(material.get("raw_text") or "")
        if raw_text:
            from .ui_text_utilities import _markdown_section_map
            section_map = _markdown_section_map(raw_text)
            for section_key in (
                "texto base referenciado (resumen tecnico)",
                "texto base referenciado (resumen técnico)",
                "condiciones de aplicacion",
                "condiciones de aplicación",
                "riesgos de interpretacion",
                "riesgos de interpretación",
                "regla operativa para lia",
            ):
                section_text = section_map.get(section_key, "")
                # Skip scaffold placeholder text
                if "scaffold debe evolucionar" in section_text.lower():
                    continue
                clean = _clean_text(section_text, max_chars=2000)
                if clean:
                    texts.append(clean)
    for item in list(context.get("related_analyses") or []):
        clean = _clean_text((item or {}).get("usable_text") or (item or {}).get("public_text"), max_chars=7000)
        if clean:
            texts.append(clean)
    return texts


def _profile_from_context(context: dict[str, Any]) -> NormativeDocumentProfile:
    profile_payload = context.get("document_profile")
    if isinstance(profile_payload, dict) and profile_payload.get("document_family"):
        return NormativeDocumentProfile(
            document_family=str(profile_payload.get("document_family") or "generic"),
            family_subtype=str(profile_payload.get("family_subtype") or "documento_general"),
            hierarchy_tier=str(profile_payload.get("hierarchy_tier") or "documental"),
            binding_force=str(profile_payload.get("binding_force") or "Documento de soporte"),
            binding_force_rank=int(profile_payload.get("binding_force_rank") or 100),
            analysis_template_id=str(profile_payload.get("analysis_template_id") or "generic_document_analysis"),
            ui_surface=str(profile_payload.get("ui_surface") or "deep_analysis"),
            relation_types=tuple(str(item) for item in (profile_payload.get("relation_types") or [])),
            allowed_secondary_overlays=tuple(str(item) for item in (profile_payload.get("allowed_secondary_overlays") or [])),
            caution_banner=dict(profile_payload.get("caution_banner") or {}) or None,
        )
    return classify_normative_document(
        context.get("citation") if isinstance(context.get("citation"), dict) else {},
        context.get("requested_row") if isinstance(context.get("requested_row"), dict) else {},
    )


def _extract_purpose_clause(texts: list[str], *, max_chars: int = 300) -> str:
    """Extract the purpose clause from a decree/resolution preamble.

    Tries in order:
    1. The "para establecer/fijar/..." purpose fragment (most actionable)
    2. The full "Por el cual..." clause (truncated if needed)
    """
    _PARA_PURPOSE_RE = re.compile(
        r"[,;]\s*(para\s+(?:establecer|fijar|regular|definir|reglamentar"
        r"|modificar|ajustar|adoptar|prescribir|determinar|señalar)[^.]{10,}\.)",
        re.IGNORECASE,
    )
    _POR_RE = re.compile(
        r"(Por\s+(?:el|la|medio\s+de\s+(?:el|la))\s+cual\b.{10,?}\.)",
        re.IGNORECASE,
    )
    for text in texts:
        decoded = _clean_html_entities(text) if "&" in text else text
        # First: try the "para [verb]..." purpose fragment directly
        para_match = _PARA_PURPOSE_RE.search(decoded)
        if para_match:
            purpose = para_match.group(1).strip()
            purpose = purpose[0].upper() + purpose[1:]
            if len(purpose) > max_chars:
                purpose = purpose[:max_chars].rsplit(" ", 1)[0] + "..."
            return purpose
        # Second: try the full "Por el cual..." clause
        por_match = _POR_RE.search(decoded)
        if por_match:
            clause = por_match.group(1).strip()
            if len(clause) > max_chars:
                clause = clause[:max_chars].rsplit(" ", 1)[0] + "..."
            return clause
    return ""


def _fallback_lead(*, title: str, profile: NormativeDocumentProfile, texts: list[str]) -> str:
    # First try the purpose clause from the preamble — the most
    # informative single sentence in any decree/resolution/ley.
    por_clause = _extract_purpose_clause(texts)
    if por_clause:
        return por_clause

    grounded_by_family = {
        "constitucion": ("principio", "constitucional", "garantiza", "reserva"),
        "ley": ("regula", "establece", "define", "modifica"),
        "et_dur": ("compila", "estatuto", "reglamenta", "establece"),
        "decreto": ("reglamenta", "desarrolla", "establece", "define", "plazos", "calendario"),
        "resolucion": ("prescribe", "establece", "fija", "adopta", "ajustar", "valores"),
        "formulario": ("formulario", "diligenciar", "presentar", "declaración", "declaracion"),
        "concepto": ("criterio", "aclara", "interpreta", "precisa"),
        "circular": ("lineamiento", "instruye", "orienta", "indica"),
        "jurisprudencia": ("decisión", "decide", "resuelve", "problema jurídico"),
    }
    # Decode HTML entities before sentence grounding
    decoded_texts = [_clean_html_entities(t) if "&" in t else t for t in texts]
    grounded = _find_best_sentence(decoded_texts, grounded_by_family.get(profile.document_family, ("regula", "establece")))
    if grounded:
        return grounded
    fallback = {
        "constitucion": f"{title} fija el marco constitucional que sirve de base para interpretar la regulación tributaria aplicable.",
        "ley": f"{title} es una norma legal relevante para el subcapítulo tributario analizado.",
        "et_dur": f"{title} compila reglas tributarias que deben leerse con atención a su vigencia y modificaciones.",
        "decreto": f"{title} desarrolla o reglamenta una obligación tributaria aplicable al caso.",
        "resolucion": f"{title} fija una regla administrativa prescriptiva relevante para la operación tributaria.",
        "formulario": f"{title} es el instrumento prescrito para materializar una obligación formal ante la DIAN.",
        "concepto": f"{title} resume una tesis doctrinal de la DIAN sobre la lectura de una norma superior.",
        "circular": f"{title} comunica lineamientos administrativos que deben leerse subordinados a la norma matriz.",
        "jurisprudencia": f"{title} contiene una interpretación judicial relevante para la aplicación tributaria actual.",
    }
    return fallback.get(profile.document_family, f"{title} es el documento seleccionado para análisis normativo.")


def _build_prompt(context: dict[str, Any], *, profile: NormativeDocumentProfile, preview_facts: list[dict[str, str]]) -> str:
    title = _clean_text(context.get("title"), max_chars=180) or "Documento"
    row = dict(context.get("requested_row") or {})
    facts_block = "\n".join(
        f"- {item.get('label')}: {item.get('value')}"
        for item in preview_facts
        if str(item.get("label") or "").strip() and str(item.get("value") or "").strip()
    ) or "- Sin hechos previos."
    raw_sentences = _split_sentences(_clean_html_entities("\n".join(_collect_texts(context))))
    text_block = "\n".join(f"- {sentence}" for sentence in raw_sentences[:8]) or "- Sin extractos utilizables."
    caution = ""
    if profile.caution_banner:
        caution = f"Precaución editorial existente: {profile.caution_banner.get('title')}: {profile.caution_banner.get('body')}\n"
    return (
        "Eres editor legal y tributario para contadores colombianos.\n"
        "Construye una lectura profunda pero breve del documento seleccionado.\n"
        "Usa solo metadata y extractos del documento. Si un dato no está soportado, omítelo.\n"
        "No menciones doc_id, chunks, pipeline, checksums, part_XX ni metadatos internos.\n"
        f"Familia documental: {profile.document_family}\n"
        f"Subtipo: {profile.family_subtype}\n"
        f"Jerarquía: {profile.hierarchy_tier}\n"
        f"Fuerza vinculante: {profile.binding_force}\n"
        f"{caution}"
        "Responde SOLO JSON válido con estas llaves opcionales:\n"
        '{"lead":"","hierarchy_summary":"","applicability_summary":"","professional_impact":"","caution_text":"","next_step_1":"","next_step_2":""}\n'
        f"Título: {title}\n"
        f"Facts previos:\n{facts_block}\n"
        f"Extractos:\n{text_block}\n"
    )


def _llm_payload(
    context: dict[str, Any],
    *,
    profile: NormativeDocumentProfile,
    preview_facts: list[dict[str, str]],
    runtime_config_path: str,
) -> dict[str, str]:
    prompt = _build_prompt(context, profile=profile, preview_facts=preview_facts)
    if not prompt.strip():
        return {}
    try:
        text, _diag = generate_llm_strict(prompt, runtime_config_path=runtime_config_path, trace_id=None)
    except Exception:
        return {}
    parsed = _safe_json_obj(text)
    normalized: dict[str, str] = {}
    for key in ("lead", "hierarchy_summary", "applicability_summary", "professional_impact", "caution_text", "next_step_1", "next_step_2"):
        clean = _clean_text(parsed.get(key), max_chars=340)
        if clean:
            normalized[key] = clean
    return normalized


def _build_timeline_events(context: dict[str, Any]) -> list[dict[str, str]]:
    row = dict(context.get("requested_row") or {})
    rows = list(context.get("related_rows") or [])
    events: list[dict[str, str]] = []
    publish = _format_date_es(row.get("publish_date"))
    effective = _format_date_es(row.get("effective_date"))
    if publish:
        events.append({"id": "publish_date", "label": "Expedición identificada", "date": publish, "detail": ""})
    if effective and effective != publish:
        events.append({"id": "effective_date", "label": "Entrada en vigencia identificada", "date": effective, "detail": ""})
    latest = ""
    date_candidates: list[str] = []
    for candidate in rows:
        for field in ("publish_date", "effective_date"):
            raw = str(candidate.get(field) or "").strip()
            if raw:
                date_candidates.append(raw)
    if date_candidates:
        try:
            latest = _format_date_es(max(datetime.fromisoformat(item).date().isoformat() for item in date_candidates))
        except Exception:
            latest = ""
    if latest and latest not in {publish, effective}:
        events.append({"id": "latest_identified", "label": "Última actualización identificada", "date": latest, "detail": ""})
    superseded_by = str(row.get("superseded_by") or "").strip()
    rows_by_doc_id = dict(context.get("rows_by_doc_id") or {})
    replacement = dict(rows_by_doc_id.get(superseded_by) or {}) if superseded_by else {}
    replacement_title = _clean_text(replacement.get("notes") or replacement.get("title") or replacement.get("relative_path"), max_chars=180)
    if superseded_by and replacement_title:
        events.append({
            "id": "replacement",
            "label": "Reemplazo registrado",
            "date": _format_date_es(replacement.get("publish_date") or replacement.get("effective_date")),
            "detail": replacement_title,
        })
    return events


def _relation_label(relation_type: str) -> str:
    return {
        "superseded_by": "Documento de reemplazo",
        "summarized_by": "Variante relacionada",
        "regulated_by": "Norma relacionada",
    }.get(relation_type, relation_type.replace("_", " ").strip())


def _build_related_documents(context: dict[str, Any], *, profile: NormativeDocumentProfile) -> list[dict[str, Any]]:
    row = dict(context.get("requested_row") or {})
    rows_by_doc_id = dict(context.get("rows_by_doc_id") or {})
    related_rows = [dict(item) for item in list(context.get("related_rows") or []) if isinstance(item, dict)]
    requested_doc_id = str(row.get("doc_id") or "").strip()
    related: list[dict[str, Any]] = []
    seen: set[str] = set()

    superseded_by = str(row.get("superseded_by") or "").strip()
    if superseded_by and superseded_by in rows_by_doc_id:
        replacement = dict(rows_by_doc_id[superseded_by])
        replacement_profile = classify_normative_document({}, replacement)
        related.append(
            {
                "doc_id": superseded_by,
                "title": _clean_text(replacement.get("notes") or replacement.get("title") or replacement.get("relative_path"), max_chars=180),
                "document_family": replacement_profile.document_family,
                "relation_type": "superseded_by",
                "relation_label": _relation_label("superseded_by"),
                "helper_text": "Existe reemplazo o sucesión normativa registrada en el índice activo.",
                "url": f"/normative-analysis?doc_id={quote(superseded_by, safe='')}",
            }
        )
        seen.add(superseded_by)

    for candidate in related_rows:
        candidate_doc_id = str(candidate.get("doc_id") or "").strip()
        if not candidate_doc_id or candidate_doc_id == requested_doc_id or candidate_doc_id in seen:
            continue
        # Skip structural/index/readme documents
        _cand_text = " ".join(filter(None, [
            str(candidate.get("title") or ""),
            str(candidate.get("relative_path") or ""),
        ]))
        if _NON_CONTENT_DOC_RE.search(candidate_doc_id) or _NON_CONTENT_DOC_RE.search(_cand_text):
            continue
        candidate_profile = classify_normative_document({}, candidate)
        related.append(
            {
                "doc_id": candidate_doc_id,
                "title": _clean_text(candidate.get("notes") or candidate.get("title") or candidate.get("relative_path"), max_chars=180),
                "document_family": candidate_profile.document_family,
                "relation_type": "summarized_by",
                "relation_label": _relation_label("summarized_by"),
                "helper_text": "Corresponde a una variante lógica o material relacionada con el mismo documento base.",
                "url": f"/normative-analysis?doc_id={quote(candidate_doc_id, safe='')}",
            }
        )
        seen.add(candidate_doc_id)
        if len(related) >= 4:
            break

    if profile.document_family == "formulario":
        return related[:2]
    return related[:4]


def _hierarchy_summary(profile: NormativeDocumentProfile, *, llm_payload: dict[str, str]) -> str:
    if llm_payload.get("hierarchy_summary"):
        return llm_payload["hierarchy_summary"]
    # No LLM content → suppress this section instead of showing generic boilerplate.
    return ""


def _applicability_summary(context: dict[str, Any], *, profile: NormativeDocumentProfile, preview_facts: list[dict[str, str]], llm_payload: dict[str, str]) -> str:
    if llm_payload.get("applicability_summary"):
        return llm_payload["applicability_summary"]
    # Don't repeat facts that are already shown in the facts grid above.
    # Suppress this section when there's no LLM-generated content.
    return ""


def _professional_impact(context: dict[str, Any], *, llm_payload: dict[str, str]) -> str:
    if llm_payload.get("professional_impact"):
        return llm_payload["professional_impact"]
    texts = _collect_texts(context)
    grounded = _find_best_sentence(texts, ("contador", "contable", "declaración", "declaracion", "presentación", "presentacion", "soporte"))
    if grounded:
        return grounded
    # No LLM content and no grounded sentence → suppress instead of generic boilerplate.
    return ""


_SCAFFOLD_RE = re.compile(r"scaffold debe evolucionar|resumen tecnico inicial para seed", re.IGNORECASE)
_LIA_INTERNAL_RE = re.compile(r"buscar primero en esta fuente|verificar claim contra|excluir claims de", re.IGNORECASE)


def _clean_html_entities(text: str) -> str:
    """Decode HTML entities and clean whitespace."""
    decoded = html_mod.unescape(text)
    decoded = decoded.replace("\xa0", " ")
    return re.sub(r"\s+", " ", decoded).strip()


def _extract_bullet_items(section_text: str) -> list[str]:
    """Extract clean bullet-point items from a markdown section."""
    items: list[str] = []
    for line in section_text.splitlines():
        line = line.strip()
        match = re.match(r"^[-*]\s+(?:\[.\]\s*)?(.+)$", line)
        if not match:
            continue
        item = _clean_html_entities(match.group(1).strip().rstrip("."))
        if not item or len(item) < 8:
            continue
        if _SCAFFOLD_RE.search(item) or _LIA_INTERNAL_RE.search(item):
            continue
        if _INTERNAL_METADATA_RE.search(item):
            continue
        # Skip items that are internal field metadata (key: value for doc_id, etc.)
        if re.match(r"^(?:doc_id|authority|source_type|article_id|source_url|last_verified_date|validation_status)\s*:", item, re.IGNORECASE):
            continue
        items.append(item)
    return items


def _build_corpus_grounded_sections(context: dict[str, Any]) -> list[dict[str, str]]:
    """Build sections directly from RAG-ready markdown structured content.

    Maps corpus sections to accountant-facing cards with bullet points.
    Returns only sections with substantive, non-scaffold content.
    """
    raw_text = str(context.get("requested_raw_text") or "")
    if not raw_text:
        raw_text = str((context.get("material") or {}).get("raw_text") or "")
    if not raw_text:
        return []

    from .ui_text_utilities import _markdown_section_map
    section_map = _markdown_section_map(raw_text)

    sections: list[dict[str, str]] = []

    # --- "Condiciones de aplicación" --------------------------------
    condiciones_text = (
        section_map.get("condiciones de aplicacion")
        or section_map.get("condiciones de aplicación")
        or ""
    )
    condiciones_items = _extract_bullet_items(condiciones_text)
    if condiciones_items:
        body = "\n".join(f"- {item}" for item in condiciones_items)
        sections.append({
            "id": "condiciones",
            "title": "Condiciones de aplicación",
            "body": body,
        })

    # --- "Riesgos de interpretación" --------------------------------
    riesgos_text = (
        section_map.get("riesgos de interpretacion")
        or section_map.get("riesgos de interpretación")
        or ""
    )
    riesgos_items = _extract_bullet_items(riesgos_text)
    if riesgos_items:
        body = "\n".join(f"- {item}" for item in riesgos_items)
        sections.append({
            "id": "riesgos",
            "title": "Riesgos de interpretación",
            "body": body,
        })

    # --- "Relaciones normativas" (bullet items only) ----------------
    relaciones_text = section_map.get("relaciones normativas", "")
    relaciones_items = _extract_bullet_items(relaciones_text)
    # Filter out items that are just URLs or internal instructions
    relaciones_clean = [
        item for item in relaciones_items
        if not item.startswith("http") and "fuente principal enlazada" not in item.lower()
    ]
    if relaciones_clean:
        body = "\n".join(f"- {item}" for item in relaciones_clean)
        sections.append({
            "id": "relaciones_corpus",
            "title": "Relaciones normativas identificadas",
            "body": body,
        })

    return sections


def _build_sections(context: dict[str, Any], *, profile: NormativeDocumentProfile, preview_facts: list[dict[str, str]], llm_payload: dict[str, str]) -> list[dict[str, str]]:
    # LLM-generated sections (only included when the LLM produced real content)
    llm_sections: list[dict[str, str]] = []
    hierarchy = _hierarchy_summary(profile, llm_payload=llm_payload)
    if hierarchy:
        llm_sections.append({"id": "hierarchy", "title": "Jerarquía y fuerza normativa", "body": hierarchy})
    applicability = _applicability_summary(context, profile=profile, preview_facts=preview_facts, llm_payload=llm_payload)
    if applicability:
        llm_sections.append({"id": "applicability", "title": "Aplicabilidad y vigencia", "body": applicability})
    impact = _professional_impact(context, llm_payload=llm_payload)
    if impact:
        llm_sections.append({"id": "professional_impact", "title": "Impacto para la labor contable", "body": impact})

    # Corpus-grounded sections from RAG-ready markdown (condiciones,
    # riesgos, relaciones) — always added when available since they
    # contain curated, document-specific content.
    corpus_sections = _build_corpus_grounded_sections(context)

    sections = llm_sections + corpus_sections

    caution = _clean_text(llm_payload.get("caution_text"), max_chars=320)
    if caution and (not profile.caution_banner or caution.lower() not in str(profile.caution_banner.get("body", "")).lower()):
        sections.append({"id": "editorial_caution", "title": "Precaución de lectura", "body": caution})
    return sections


def _build_recommended_actions(
    *,
    source_action: dict[str, Any] | None,
    companion_action: dict[str, Any] | None,
) -> list[dict[str, str]]:
    actions: list[dict[str, str]] = []
    source = dict(source_action or {})
    if str(source.get("url") or "").strip():
        actions.append(
            {
                "id": "source_action",
                "kind": "source",
                "label": _clean_text(source.get("label"), max_chars=80) or "Ir a documento original",
                "url": str(source.get("url") or "").strip(),
                "helper_text": _clean_text(source.get("helper_text"), max_chars=180),
            }
        )
    companion = dict(companion_action or {})
    if str(companion.get("state") or "").strip() == "available" and str(companion.get("url") or "").strip():
        actions.append(
            {
                "id": "companion_action",
                "kind": "companion",
                "label": _clean_text(companion.get("label"), max_chars=80) or "Abrir recurso relacionado",
                "url": str(companion.get("url") or "").strip(),
                "helper_text": _clean_text(companion.get("helper_text"), max_chars=180),
            }
        )
    return actions


def build_normative_analysis_payload(
    context: dict[str, Any],
    *,
    preview_facts: list[dict[str, str]] | None,
    source_action: dict[str, Any] | None,
    companion_action: dict[str, Any] | None,
    runtime_config_path: str,
) -> dict[str, Any]:
    del runtime_config_path
    profile = _profile_from_context(context)
    title = _clean_text(context.get("title"), max_chars=180) or "Documento"
    facts = [dict(item) for item in list(preview_facts or []) if isinstance(item, dict)]
    synthesis = NormativaSynthesis()
    try:
        _diagnostics, runtime_payload = run_normativa_surface(context)
        candidate = runtime_payload.get("synthesis")
        if isinstance(candidate, NormativaSynthesis):
            synthesis = candidate
    except Exception:  # noqa: BLE001
        synthesis = NormativaSynthesis()

    if not synthesis.lead:
        synthesis = replace(
            synthesis,
            lead=_fallback_lead(title=title, profile=profile, texts=_collect_texts(context)),
        )
    if not synthesis.sections:
        synthesis = replace(
            synthesis,
            sections=tuple(
                NormativaSection(
                    id=str(item.get("id") or "").strip() or "normativa_section",
                    title=_clean_text(item.get("title"), max_chars=120),
                    body=_clean_text(item.get("body"), max_chars=420),
                )
                for item in _build_corpus_grounded_sections(context)
                if _clean_text(item.get("title"), max_chars=120)
                and _clean_text(item.get("body"), max_chars=420)
            ),
        )

    return _assemble_normativa_analysis_payload(
        title=title,
        context=context,
        profile=profile.to_public_dict(),
        preview_facts=facts,
        source_action=source_action,
        companion_action=companion_action,
        synthesis=synthesis,
        timeline_events=_build_timeline_events(context),
        related_documents=_build_related_documents(context, profile=profile),
        recommended_actions=_build_recommended_actions(
            source_action=source_action,
            companion_action=companion_action,
        ),
    )
