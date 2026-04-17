from __future__ import annotations

import re
import unicodedata
from dataclasses import replace
from typing import Any, Iterable

from ..topic_guardrails import get_topic_scope
from ..topic_router import detect_topic_from_text
from .policy import (
    EXPERT_PANEL_MIN_RELEVANCE_SCORE,
    EXPERT_PANEL_SOURCE_DIVERSITY_MAX_DIAN,
    EXPERT_PANEL_SOURCE_DIVERSITY_VISIBLE_COUNT,
)
from .shared import (
    DecisionFrame,
    ExpertGroup,
    InterpretationCandidate,
    InterpretationCard,
    RankedInterpretation,
    RankedSelection,
)

_ARTICLE_REF_RE = re.compile(r"\b(?:art(?:[ií]culo)?\.?\s*(\d{1,4}(?:\s*[-–]\s*\d{1,4})?))\b", re.IGNORECASE)
_WHITESPACE_RE = re.compile(r"\s+")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
_NORM_ANCHOR_RE = re.compile(
    r"\b(?:art(?:[ií]culo)?\.?\s*\d+(?:[.-]\d+)*|decreto\s+\d+|concepto\s+\d+|sentencia\s+[A-Z]+-\d+|ET\s+art\.?\s*\d+)\b",
    re.IGNORECASE,
)
_LEGAL_ABBREV_RE = re.compile(
    r"\b(?:Art|No|Inc|Lit|Par|Num|Dec|Res|Sent|Exp|Dr|Dra|Sr|Sra|Ej|Cf|Vs)\.\s",
    re.IGNORECASE,
)
_STRONG_RESTRINGE_RE = re.compile(
    r"(?:no\s+procede|improcedente|se\s+proh[ií]be|no\s+es\s+viable|inadmisible|no\s+tiene\s+derecho|no\s+corresponde|no\s+puede)",
    re.IGNORECASE,
)
_STRONG_CONDICIONA_RE = re.compile(
    r"(?:siempre\s+que|bajo\s+condici[oó]n|sujeto\s+a|depende\s+de|en\s+la\s+medida|cuando\s+se\s+cumpl)",
    re.IGNORECASE,
)
_STRONG_PERMITE_RE = re.compile(
    r"(?:se\s+permite|es\s+deducible|procede\s+la\s+deducci[oó]n|tiene\s+derecho|es\s+viable|admisible)",
    re.IGNORECASE,
)
_WEAK_PERMITE_RE = re.compile(r"\b(?:puede|procede|corresponde)\b", re.IGNORECASE)
_ARTICLE_FAMILY_RE = re.compile(r"^(\w+_art_\d+)(?:_\d+)+$")

_TRUST_SCORES = {"high": 1.0, "medium": 0.72, "low": 0.42}
_OFF_TOPIC_PATTERNS: dict[str, tuple[str, ...]] = {
    "ttd": ("ttd", "tasa minima de tributacion", "tasa de tributacion depurada", "impuesto a adicionar"),
    "rst": ("regimen simple", "régimen simple", "rst"),
    "retencion": ("retencion en la fuente", "retención en la fuente", "autorretencion", "autorretención"),
    "conciliacion": ("conciliacion fiscal", "conciliación fiscal", "formato 2516", "f.2516"),
    "facturacion": ("facturacion electronica", "facturación electrónica", "documento soporte", "nomina electronica"),
    "calendario": ("calendario tributario", "extemporanea", "extemporánea"),
}
_ACTIONABILITY_HINTS = (
    "como aplicar",
    "cómo aplicar",
    "valor agregado para el contador",
    "regla operativa",
    "checklist",
    "renglon",
    "renglón",
    "casilla",
    "soporte",
    "soportes",
    "conservar",
    "debe",
    "deben",
    "verificar",
    "documentar",
)
_COMMON_STOPWORDS = frozenset({
    "de", "la", "el", "se", "en", "por", "con", "que", "para", "los", "las", "del", "una", "un",
    "como", "puede", "cuando", "entre", "sobre", "segun", "según", "este", "esta", "ser", "hay",
    "tiene", "son", "sin", "asi", "así", "cada", "mas", "más", "otros", "al", "lo", "su", "mi",
    "sus", "nos", "les", "ya", "si", "sí", "no", "muy", "o", "y", "a",
})
_OPPOSING_PAIRS: frozenset[frozenset[str]] = frozenset(
    {
        frozenset({"permite", "restringe"}),
        frozenset({"restringe", "condiciona"}),
    }
)


def _strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def normalize_text(value: Any) -> str:
    clean = _strip_accents(str(value or "")).lower()
    return _WHITESPACE_RE.sub(" ", clean).strip()


def _canonical_ref(value: Any) -> str:
    clean = normalize_text(value).replace(":", "_").replace(".", "_").replace("-", "_")
    clean = _NON_ALNUM_RE.sub("_", clean)
    clean = re.sub(r"_+", "_", clean).strip("_")
    return clean


def _clip_reason(value: str, *, max_chars: int = 140) -> str:
    clean = _WHITESPACE_RE.sub(" ", str(value or "")).strip()
    if len(clean) <= max_chars:
        return clean
    clipped = clean[: max_chars - 1].rstrip()
    cut = clipped.rfind(" ")
    if cut >= int(max_chars * 0.6):
        clipped = clipped[:cut]
    return f"{clipped.rstrip(' .,:;')}…"


def extract_article_refs(text: str) -> tuple[str, ...]:
    refs: list[str] = []
    seen: set[str] = set()
    for match in _ARTICLE_REF_RE.finditer(str(text or "")):
        raw = _strip_accents(match.group(1) or "")
        value = raw.replace(" ", "").replace("–", "-").replace("—", "-")
        if not value:
            continue
        ref = f"et_art_{value.replace('-', '_')}"
        if ref in seen:
            continue
        seen.add(ref)
        refs.append(ref)
    return tuple(refs)


def _extract_form_entities(text: str) -> tuple[str, ...]:
    normalized = normalize_text(text)
    found: list[str] = []
    if "formulario 110" in normalized or "f110" in normalized or "f.110" in normalized:
        found.append("formulario:110")
    if "formato 2516" in normalized or "f2516" in normalized or "f.2516" in normalized:
        found.append("formulario:2516")
    return tuple(dict.fromkeys(found))


def _match_any(text: str, patterns: tuple[str, ...]) -> bool:
    normalized = normalize_text(text)
    return any(pattern in normalized for pattern in patterns)


def _collect_candidate_text(doc: Any, row: dict[str, Any] | None, corpus_text: str) -> str:
    parts: list[str] = [
        doc.doc_id,
        doc.relative_path,
        doc.authority,
        doc.topic,
        doc.tema or "",
        doc.subtema or "",
        doc.notes or "",
        doc.tipo_de_consulta or "",
        doc.tipo_de_accion or "",
        doc.tipo_de_documento or "",
        " ".join(doc.normative_refs or ()),
        " ".join(doc.reference_identity_keys or ()),
        " ".join(doc.mentioned_reference_keys or ()),
        " ".join(doc.provider_labels or ()),
        corpus_text[:5000],
    ]
    if row:
        parts.extend(
            [
                str(row.get("notes", "")),
                str(row.get("subtema", "")),
                str(row.get("tema", "")),
                str(row.get("entity_id", "")),
                " ".join(str(item) for item in row.get("normative_refs", ()) or ()),
                " ".join(str(item) for item in row.get("reference_identity_keys", ()) or ()),
                " ".join(str(item) for item in row.get("mentioned_reference_keys", ()) or ()),
            ]
        )
    return "\n".join(part for part in parts if str(part or "").strip())


def _extract_dynamic_signals(combined_text: str) -> tuple[str | None, tuple[str, ...]]:
    detection = detect_topic_from_text(combined_text)
    detected_topic = detection.topic if detection.confidence >= 0.2 else None
    tokens = set(normalize_text(combined_text).split()) - _COMMON_STOPWORDS
    meaningful = [token for token in tokens if len(token) >= 4]
    keyword_cluster = tuple(sorted(meaningful, key=len, reverse=True)[:10])
    return detected_topic, keyword_cluster


def build_expert_query_seed(
    *,
    message: str,
    assistant_answer: str,
    normative_article_refs: list[str],
) -> str:
    parts: list[str] = []
    for ref in normative_article_refs:
        clean = str(ref).strip()
        if clean:
            parts.append(clean)
    question = str(message or "").strip()
    if question:
        parts.append(question)
    answer = str(assistant_answer or "").strip()
    if answer:
        seen = {part.lower() for part in parts}
        for anchor in _NORM_ANCHOR_RE.findall(answer)[:8]:
            normalized = re.sub(r"\s+", " ", anchor).strip()
            if normalized and normalized.lower() not in seen:
                parts.append(normalized)
                seen.add(normalized.lower())
    return " ".join(parts) if parts else ""


def build_decision_frame(
    *,
    question: str,
    assistant_answer: str = "",
    citation_label: str = "",
    requested_refs: Iterable[str] = (),
) -> DecisionFrame:
    question_clean = _WHITESPACE_RE.sub(" ", str(question or "")).strip()
    answer_clean = _WHITESPACE_RE.sub(" ", str(assistant_answer or "")).strip()
    citation_clean = _WHITESPACE_RE.sub(" ", str(citation_label or "")).strip()
    combined = "\n".join(part for part in (question_clean, answer_clean, citation_clean) if part)
    normalized = normalize_text(combined)

    refs: list[str] = []
    seen_refs: set[str] = set()
    requested_forms: list[str] = []
    for raw_ref in requested_refs:
        normalized_ref = _canonical_ref(raw_ref)
        if not normalized_ref:
            continue
        if normalized_ref.startswith("art_"):
            normalized_ref = f"et_{normalized_ref}"
        if normalized_ref.startswith("formulario_"):
            requested_forms.append(f"formulario:{normalized_ref.split('formulario_', 1)[1]}")
            continue
        if normalized_ref.startswith("formato_"):
            requested_forms.append(f"formulario:{normalized_ref.split('formato_', 1)[1]}")
            continue
        if normalized_ref.startswith("et_art_") and normalized_ref not in seen_refs:
            seen_refs.add(normalized_ref)
            refs.append(normalized_ref)
    for extracted in extract_article_refs(combined):
        if extracted not in seen_refs:
            seen_refs.add(extracted)
            refs.append(extracted)

    form_entities = tuple(dict.fromkeys((*_extract_form_entities(combined), *requested_forms)))
    detected_topic, keyword_cluster = _extract_dynamic_signals(combined)
    return DecisionFrame(
        question=question_clean,
        assistant_answer=answer_clean,
        citation_label=citation_clean,
        core_refs=tuple(refs),
        form_entities=form_entities,
        normalized_text=normalized,
        detected_topic=detected_topic,
        keyword_cluster=keyword_cluster,
    )


def build_interpretation_candidate(
    *,
    doc: Any,
    row: dict[str, Any] | None,
    corpus_text: str,
) -> InterpretationCandidate:
    text = _collect_candidate_text(doc, row, corpus_text)
    normalized = normalize_text(text)

    refs: list[str] = []
    seen_refs: set[str] = set()
    for bucket in (
        tuple(doc.normative_refs or ()),
        tuple(row.get("normative_refs", ()) or ()) if isinstance(row, dict) else (),
        tuple(doc.reference_identity_keys or ()),
        tuple(doc.mentioned_reference_keys or ()),
        tuple(row.get("reference_identity_keys", ()) or ()) if isinstance(row, dict) else (),
        tuple(row.get("mentioned_reference_keys", ()) or ()) if isinstance(row, dict) else (),
        extract_article_refs(text),
    ):
        for raw_ref in bucket:
            normalized_ref = _canonical_ref(raw_ref)
            if normalized_ref.startswith("art_"):
                normalized_ref = f"et_{normalized_ref}"
            if not normalized_ref.startswith("et_art_"):
                continue
            if normalized_ref in seen_refs:
                continue
            seen_refs.add(normalized_ref)
            refs.append(normalized_ref)

    form_entities = list(_extract_form_entities(text))
    for bucket in (
        tuple(doc.reference_identity_keys or ()),
        tuple(doc.mentioned_reference_keys or ()),
        tuple(row.get("reference_identity_keys", ()) or ()) if isinstance(row, dict) else (),
        tuple(row.get("mentioned_reference_keys", ()) or ()) if isinstance(row, dict) else (),
    ):
        for item in bucket:
            value = str(item or "").strip().lower()
            if value.startswith("formulario:") and value not in form_entities:
                form_entities.append(value)

    off_topic: list[str] = []
    for key, patterns in _OFF_TOPIC_PATTERNS.items():
        if _match_any(text, patterns):
            off_topic.append(key)

    provider_candidates = list(doc.provider_labels or ())
    if not provider_candidates and isinstance(row, dict):
        provider_candidates = [str(item) for item in row.get("provider_labels", ()) or () if str(item).strip()]
    provider_key = normalize_text(provider_candidates[0] if provider_candidates else doc.authority or doc.doc_id)
    actionability_hits = sum(1 for token in _ACTIONABILITY_HINTS if token in normalized)
    actionability_score = min(1.0, 0.35 + (0.12 * actionability_hits)) if actionability_hits else 0.28

    return InterpretationCandidate(
        doc=doc,
        row=row,
        corpus_text=corpus_text,
        provider_key=provider_key or normalize_text(doc.doc_id),
        expanded_refs=tuple(refs),
        form_entities=tuple(dict.fromkeys(form_entities)),
        off_topic_tags=tuple(dict.fromkeys(off_topic)),
        actionability_score=round(actionability_score, 4),
    )


def _topic_match_score(candidate: InterpretationCandidate, frame: DecisionFrame) -> float:
    if not frame.detected_topic:
        return 0.0
    candidate_topic = normalize_text(candidate.doc.topic or "")
    frame_topic = normalize_text(frame.detected_topic)
    if candidate_topic == frame_topic:
        return 1.0
    scope = get_topic_scope(frame.detected_topic)
    if scope is None:
        return 0.15
    try:
        allowed = {normalize_text(item) for item in scope}
    except TypeError:
        allowed = {normalize_text(getattr(scope, "primary", ""))}
        allowed.update(normalize_text(item) for item in getattr(scope, "secondary", ()) or ())
    return 0.9 if candidate_topic in allowed else 0.15


def _keyword_overlap_score(candidate: InterpretationCandidate, frame: DecisionFrame) -> float:
    if not frame.keyword_cluster:
        return 0.0
    candidate_tokens = set(normalize_text(candidate.corpus_text[:2000]).split()) - _COMMON_STOPWORDS
    candidate_meaningful = {token for token in candidate_tokens if len(token) >= 4}
    frame_set = set(frame.keyword_cluster)
    if not frame_set:
        return 0.0
    intersection = frame_set & candidate_meaningful
    return min(1.0, len(intersection) / max(1, len(frame_set)))


def score_interpretation_candidate(candidate: InterpretationCandidate, frame: DecisionFrame) -> RankedInterpretation:
    core_ref_matches = tuple(ref for ref in frame.core_refs if ref in set(candidate.expanded_refs))
    form_matches = set(candidate.form_entities).intersection(frame.form_entities)
    core_ref_score = 0.0
    if frame.core_refs:
        core_ref_score = min(1.0, len(core_ref_matches) / max(1, min(2, len(frame.core_refs))))
    elif form_matches:
        core_ref_score = 1.0

    retrieval_score = max(0.0, min(1.0, float(candidate.doc.retrieval_score or 0.0)))
    trust_score = _TRUST_SCORES.get(normalize_text(candidate.doc.trust_tier or "medium"), 0.58)
    penalties: list[str] = []
    penalty_score = 0.0
    frame_off_topic = {
        key
        for key, patterns in _OFF_TOPIC_PATTERNS.items()
        if any(pattern in frame.normalized_text for pattern in patterns)
    }
    for tag in candidate.off_topic_tags:
        if tag not in frame_off_topic:
            penalties.append(f"off_topic:{tag}")
            penalty_score += 0.20

    requested_match = bool(core_ref_matches or form_matches)
    topic_score = _topic_match_score(candidate, frame)
    keyword_score = _keyword_overlap_score(candidate, frame)
    total_score = (
        (0.45 * retrieval_score)
        + (0.20 * topic_score)
        + (0.15 * core_ref_score)
        + (0.10 * keyword_score)
        + (0.05 * trust_score)
        + (0.05 * candidate.actionability_score)
        - penalty_score
    )
    total_score = max(0.0, min(1.0, total_score))
    if topic_score >= 0.9:
        reason = f"Cubre el tema de la consulta ({frame.detected_topic})."
    elif core_ref_matches:
        reason = "Se ancla a una referencia normativa central del caso."
    elif form_matches:
        reason = "Sirve como companion operativo del formulario citado."
    elif keyword_score >= 0.3:
        reason = "Relevante por afinidad semántica con la consulta."
    else:
        reason = "Contexto complementario para la consulta."
    return RankedInterpretation(
        candidate=candidate,
        total_score=round(total_score, 4),
        requested_match=requested_match,
        core_ref_matches=core_ref_matches,
        penalties=tuple(penalties),
        selection_reason=_clip_reason(reason),
    )


def _rank_sort_key(item: RankedInterpretation) -> tuple[float, str]:
    requested_bonus = 0.05 if item.requested_match else 0.0
    return (-(item.total_score + requested_bonus), item.candidate.doc.doc_id)


def order_ranked_interpretations(
    ranked_items: Iterable[RankedInterpretation],
    *,
    frame: DecisionFrame,
) -> tuple[RankedInterpretation, ...]:
    del frame
    remaining = sorted(tuple(ranked_items), key=_rank_sort_key)
    if not remaining:
        return ()
    ordered: list[RankedInterpretation] = []
    while remaining:
        best_item: RankedInterpretation | None = None
        best_score: float | None = None
        for item in remaining:
            score = float(item.total_score)
            if ordered and len(ordered) < 5 and ordered[-1].provider_key == item.provider_key:
                score -= 0.05
            if best_score is None or score > best_score:
                best_item = item
                best_score = score
        assert best_item is not None
        ordered.append(best_item)
        remaining.remove(best_item)
    return tuple(ordered)


def select_interpretation_candidates(
    candidates: Iterable[InterpretationCandidate],
    *,
    frame: DecisionFrame,
    offset: int = 0,
    limit: int = 5,
) -> RankedSelection:
    candidate_items = tuple(candidates)
    ranked = [score_interpretation_candidate(candidate, frame) for candidate in candidate_items]
    eligible = [
        item
        for item in ranked
        if item.total_score >= EXPERT_PANEL_MIN_RELEVANCE_SCORE
        and not any(penalty.startswith("off_topic:") for penalty in item.penalties)
    ]
    ordered = order_ranked_interpretations(eligible, frame=frame)
    safe_offset = max(0, int(offset or 0))
    safe_limit = max(0, int(limit or 0))
    page = ordered[safe_offset:] if safe_limit == 0 else ordered[safe_offset: safe_offset + safe_limit]
    next_offset = safe_offset + len(page)
    has_more = next_offset < len(ordered)
    diagnostics = {
        "decision_frame": frame.to_dict(),
        "retrieved_candidates": len(candidate_items),
        "eligible_candidates": len(eligible),
        "filtered_out_candidates": max(0, len(ranked) - len(eligible)),
    }
    return RankedSelection(
        total_available=len(ordered),
        items=ordered,
        page=page,
        next_offset=next_offset if has_more else None,
        has_more=has_more,
        diagnostics=diagnostics,
    )


def serialize_ranked_interpretation(
    ranked: RankedInterpretation,
    *,
    include_debug: bool = False,
) -> dict[str, Any]:
    payload = {
        "coverage_axes": [],
        "requested_match": ranked.requested_match,
        "selection_reason": ranked.selection_reason,
        "relevance_score": ranked.total_score,
        "core_ref_matches": list(ranked.core_ref_matches),
        "primary_axis_hits": [],
        "secondary_axis_hits": [],
    }
    if include_debug:
        payload["penalties"] = list(ranked.penalties)
    return payload


def _split_signal_sentences(text: str) -> list[str]:
    clean = _WHITESPACE_RE.sub(" ", str(text or "")).strip()
    if not clean:
        return []
    protected = _LEGAL_ABBREV_RE.sub(lambda match: match.group(0).replace(". ", ".\x00"), clean)
    parts = re.split(r"(?<=[.!?])\s+", protected)
    return [part.replace("\x00", " ").strip() for part in parts if part.replace("\x00", " ").strip()]


def extract_position_signal(text: str) -> str:
    scores = {"permite": 0.0, "restringe": 0.0, "condiciona": 0.0}
    for sentence in _split_signal_sentences(text or ""):
        if _STRONG_RESTRINGE_RE.search(sentence):
            scores["restringe"] += 1.0
            continue
        if _STRONG_CONDICIONA_RE.search(sentence):
            scores["condiciona"] += 0.9
            continue
        if _STRONG_PERMITE_RE.search(sentence):
            scores["permite"] += 0.85
            continue
        if _WEAK_PERMITE_RE.search(sentence):
            scores["permite"] += 0.35
    winner = max(scores, key=scores.get)
    return winner if scores[winner] > 0 else "neutral"


def _normalize_article_ref(ref: str) -> str:
    clean = ref.strip().lower()
    if not clean:
        return clean
    if clean.startswith("art_") and not clean.startswith(("art_dec", "art_ley")):
        clean = f"et_{clean}"
    match = _ARTICLE_FAMILY_RE.match(clean)
    if match:
        return match.group(1)
    return clean


def _classification_tiebreak(classification: str) -> int:
    clean = str(classification or "").strip().lower()
    if clean == "divergencia":
        return 0
    if clean == "complementario":
        return 1
    if clean == "concordancia":
        return 2
    return 3


def _dedupe_cards_by_doc_id(cards: Iterable[InterpretationCard]) -> tuple[InterpretationCard, ...]:
    ordered: list[InterpretationCard] = []
    seen_doc_ids: set[str] = set()
    for card in cards:
        doc_id = str(card.doc_id or "").strip()
        if not doc_id or doc_id in seen_doc_ids:
            continue
        seen_doc_ids.add(doc_id)
        ordered.append(card)
    return tuple(ordered)


def _group_classification(cards: tuple[InterpretationCard, ...]) -> str:
    signals_by_identity: dict[str, str] = {}
    for card in cards:
        provider_names = [str(item.get("name") or "").strip() for item in card.providers if isinstance(item, dict)]
        identity = " | ".join(provider_names) or str(card.authority or "").strip() or card.doc_id
        existing = signals_by_identity.get(identity, "neutral")
        if existing == "neutral" and card.position_signal != "neutral":
            signals_by_identity[identity] = card.position_signal
        elif identity not in signals_by_identity:
            signals_by_identity[identity] = card.position_signal
    unique_signals = {signal for signal in signals_by_identity.values() if signal != "neutral"}
    if len(unique_signals) <= 1:
        return "concordancia"
    for pair in _OPPOSING_PAIRS:
        if pair.issubset(unique_signals):
            return "divergencia"
    return "complementario"


def _summary_fragment(card: InterpretationCard) -> str:
    raw = str(card.card_summary or card.snippet or "").strip()
    clean = re.sub(r"\s+", " ", raw).strip().rstrip(".!?:;")
    if not clean or len(clean) < 40:
        return ""
    authority = str(card.authority or "").strip()
    if authority and clean.lower().startswith(authority.lower()):
        return ""
    return clean[:1].lower() + clean[1:] if len(clean) > 1 else clean.lower()


def build_group_summary_signal(
    classification: str,
    cards: tuple[InterpretationCard, ...],
) -> str:
    primary = cards[0] if cards else None
    secondary = cards[1] if len(cards) > 1 else primary
    primary_fragment = _summary_fragment(primary) if primary else ""
    secondary_fragment = _summary_fragment(secondary) if secondary else ""
    if classification == "concordancia":
        if primary_fragment:
            return f"{primary_fragment}."
        return "Las fuentes apuntan a un criterio consistente."
    if classification == "divergencia":
        if primary_fragment and secondary_fragment:
            return f"La lectura no es unívoca: {primary_fragment}. Otra postura sostiene que {secondary_fragment}."
        return "Hay una diferencia real de criterio sobre este punto."
    if primary_fragment and secondary_fragment:
        tail = secondary_fragment[:1].lower() + secondary_fragment[1:] if len(secondary_fragment) > 1 else secondary_fragment.lower()
        return f"{primary_fragment}. Además, {tail}."
    return "Las fuentes cubren aristas complementarias de este punto."


def classify_expert_groups(cards: list[InterpretationCard]) -> tuple[tuple[ExpertGroup, ...], tuple[InterpretationCard, ...]]:
    ref_groups: dict[str, list[InterpretationCard]] = {}
    ungrouped: list[InterpretationCard] = []
    grouped_doc_ids: set[str] = set()
    for card in cards:
        refs = tuple(card.expanded_refs or ())
        if not refs:
            ungrouped.append(card)
            continue
        for ref in refs:
            normalized = _normalize_article_ref(ref)
            if not normalized:
                continue
            ref_groups.setdefault(normalized, []).append(card)

    groups: list[ExpertGroup] = []
    for article_ref, grouped_cards in sorted(ref_groups.items()):
        unique_cards = list(_dedupe_cards_by_doc_id(grouped_cards))
        identities = {
            " | ".join(
                str(item.get("name") or "").strip()
                for item in card.providers
                if isinstance(item, dict) and str(item.get("name") or "").strip()
            )
            or str(card.authority or "").strip()
            or card.doc_id
            for card in unique_cards
        }
        if len(identities) < 2:
            continue
        ordered_cards = tuple(
            sorted(
                unique_cards,
                key=lambda item: (
                    -float(item.relevance_score or 0.0),
                    item.doc_id,
                ),
            )
        )
        classification = _group_classification(ordered_cards)
        coverage_axes = tuple(
            dict.fromkeys(
                axis
                for card in ordered_cards
                for axis in tuple(card.coverage_axes or ())
                if str(axis).strip()
            )
        )
        providers = tuple(
            {
                str(item.get("name") or "").strip(): dict(item)
                for card in ordered_cards
                for item in card.providers
                if isinstance(item, dict) and str(item.get("name") or "").strip()
            }.values()
        )
        requested_match = any(card.requested_match for card in ordered_cards)
        selection_reason = next((card.selection_reason for card in ordered_cards if card.selection_reason), "")
        top_relevance = max((float(card.relevance_score or 0.0) for card in ordered_cards), default=0.0)
        groups.append(
            ExpertGroup(
                article_ref=article_ref,
                classification=classification,
                snippets=ordered_cards,
                summary_signal=build_group_summary_signal(classification, ordered_cards),
                providers=providers,
                relevance_score=top_relevance,
                coverage_axes=coverage_axes,
                requested_match=requested_match,
                selection_reason=selection_reason,
            )
        )
        grouped_doc_ids.update(card.doc_id for card in ordered_cards)

    for card in cards:
        if card.doc_id not in grouped_doc_ids and card not in ungrouped:
            ungrouped.append(card)
    ungrouped_sorted = tuple(
        sorted(
            _dedupe_cards_by_doc_id(ungrouped),
            key=lambda item: (-float(item.relevance_score or 0.0), item.doc_id),
        )
    )
    groups_sorted = tuple(
        sorted(
            groups,
            key=lambda group: (-float(group.relevance_score or 0.0), group.article_ref),
        )
    )
    return groups_sorted, ungrouped_sorted


def _item_authorities(kind: str, payload: Any) -> list[str]:
    if kind == "group":
        seen: set[str] = set()
        ordered: list[str] = []
        for snippet in tuple(getattr(payload, "snippets", ()) or ()):
            authority = normalize_text(getattr(snippet, "authority", ""))
            if authority and authority not in seen:
                seen.add(authority)
                ordered.append(authority)
        return ordered
    authority = normalize_text(getattr(payload, "authority", ""))
    return [authority] if authority else []


def _item_has_dian(kind: str, payload: Any) -> bool:
    return "dian" in _item_authorities(kind, payload)


def _apply_source_diversity(panel_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(panel_items) <= EXPERT_PANEL_SOURCE_DIVERSITY_VISIBLE_COUNT:
        return list(panel_items)

    original_index = {id(item): index for index, item in enumerate(panel_items)}
    dian_items: list[dict[str, Any]] = []
    non_dian_items: list[dict[str, Any]] = []
    for item in panel_items:
        if _item_has_dian(str(item.get("kind") or ""), item.get("payload")):
            dian_items.append(item)
        else:
            non_dian_items.append(item)

    dian_selected = dian_items[:EXPERT_PANEL_SOURCE_DIVERSITY_MAX_DIAN]
    remaining_slots = EXPERT_PANEL_SOURCE_DIVERSITY_VISIBLE_COUNT - len(dian_selected)
    authority_buckets: dict[str, list[dict[str, Any]]] = {}
    for item in non_dian_items:
        authorities = _item_authorities(str(item.get("kind") or ""), item.get("payload"))
        key = authorities[0] if authorities else "_unknown"
        authority_buckets.setdefault(key, []).append(item)

    non_dian_selected: list[dict[str, Any]] = []
    for bucket in authority_buckets.values():
        if len(non_dian_selected) >= remaining_slots:
            break
        non_dian_selected.append(bucket.pop(0))

    if len(non_dian_selected) < remaining_slots:
        for bucket in authority_buckets.values():
            for item in bucket:
                if len(non_dian_selected) >= remaining_slots:
                    break
                non_dian_selected.append(item)
            if len(non_dian_selected) >= remaining_slots:
                break

    selected = dian_selected + non_dian_selected
    selected.sort(key=lambda item: original_index[id(item)])
    selected_ids = {id(item) for item in selected}
    remaining_non_dian = [item for item in panel_items if id(item) not in selected_ids and not _item_has_dian(str(item.get("kind") or ""), item.get("payload"))]
    remaining_dian = [item for item in panel_items if id(item) not in selected_ids and _item_has_dian(str(item.get("kind") or ""), item.get("payload"))]
    return selected + remaining_non_dian + remaining_dian


def build_expert_panel_page(
    *,
    groups: tuple[ExpertGroup, ...],
    ungrouped: tuple[InterpretationCard, ...],
    requested_refs: set[str],
    offset: int,
    limit: int,
) -> tuple[tuple[ExpertGroup, ...], tuple[InterpretationCard, ...], int, bool, int | None]:
    panel_items: list[dict[str, Any]] = []
    for group in groups:
        panel_items.append(
            {
                "kind": "group",
                "payload": group,
                "requested_match": bool(group.requested_match) or group.article_ref in requested_refs,
                "relevance_score": float(group.relevance_score or 0.0),
                "coverage_axes": tuple(group.coverage_axes or ()),
                "classification": str(group.classification or ""),
                "identity": group.article_ref or f"group_{len(panel_items)}",
            }
        )
    for card in ungrouped:
        panel_items.append(
            {
                "kind": "snippet",
                "payload": card,
                "requested_match": bool(card.requested_match),
                "relevance_score": float(card.relevance_score or 0.0),
                "coverage_axes": tuple(card.coverage_axes or ()),
                "classification": "individual",
                "identity": card.doc_id or f"snippet_{len(panel_items)}",
            }
        )

    panel_items.sort(
        key=lambda item: (
            not bool(item["requested_match"]),
            -float(item["relevance_score"]),
            -len(tuple(item["coverage_axes"] or ())),
            _classification_tiebreak(str(item["classification"] or "")),
            str(item["identity"] or ""),
        )
    )
    if offset == 0 and limit > 0:
        panel_items = _apply_source_diversity(panel_items)

    ranked_items: list[dict[str, Any]] = []
    for index, item in enumerate(panel_items, start=1):
        if str(item.get("kind") or "") == "group":
            payload = replace(item["payload"], panel_rank=index)
        else:
            payload = replace(item["payload"], panel_rank=index)
        ranked_items.append({**item, "payload": payload, "panel_rank": index})

    safe_offset = max(0, int(offset or 0))
    safe_limit = max(0, int(limit or 0))
    page_items = ranked_items[safe_offset:] if safe_limit == 0 else ranked_items[safe_offset : safe_offset + safe_limit]
    next_offset = safe_offset + len(page_items)
    has_more = next_offset < len(ranked_items)
    page_groups = tuple(item["payload"] for item in page_items if str(item.get("kind") or "") == "group")
    page_ungrouped = tuple(item["payload"] for item in page_items if str(item.get("kind") or "") != "group")
    return page_groups, page_ungrouped, len(ranked_items), has_more, next_offset if has_more else None


def build_fallback_expert_enhancements(
    *,
    cards: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    enhancements: list[dict[str, Any]] = []
    for index, card in enumerate(cards[:5], start=1):
        card_id = str(card.get("card_id", "")).strip() or f"card_{index}"
        article_ref = str(card.get("article_ref", "")).strip()
        summary_signal = re.sub(r"\s+", " ", str(card.get("summary_signal", "")).strip())
        snippets = card.get("snippets", [])
        if not isinstance(snippets, list):
            snippets = []
        nutshell_parts = [
            re.sub(r"\s+", " ", str(item.get("card_summary", "") or item.get("snippet", "")).strip())
            for item in snippets[:2]
            if re.sub(r"\s+", " ", str(item.get("card_summary", "") or item.get("snippet", "")).strip())
        ]
        nutshell = " ".join(nutshell_parts).strip()
        if not nutshell:
            nutshell = summary_signal or "Aporta una lectura profesional útil para revisar este punto antes de cerrar la recomendación."
        relevancia = (
            f"Aporta criterio profesional sobre {article_ref.replace('_', ' ')} para aterrizar la consulta."
            if article_ref
            else "Aporta contexto profesional útil para aterrizar la consulta."
        )
        enhancements.append(
            {
                "card_id": card_id,
                "es_relevante": True,
                "posible_relevancia": relevancia,
                "resumen_nutshell": _clip_reason(nutshell, max_chars=360),
            }
        )
    return enhancements


def build_fallback_expert_explore_content(
    *,
    mode: str,
    message: str,
    classification: str,
    article_ref: str,
    summary_signal: str,
    snippets: list[dict[str, Any]],
) -> str:
    excerpts = [
        re.sub(r"\s+", " ", str(item.get("card_summary", "") or item.get("snippet", "")).strip())
        for item in snippets[:5]
        if re.sub(r"\s+", " ", str(item.get("card_summary", "") or item.get("snippet", "")).strip())
    ]
    joined = "\n".join(f"- {excerpt}" for excerpt in excerpts) or "- No evidenciado en las fuentes consultadas."
    if mode == "summary":
        paragraphs = [
            f"La consulta gira alrededor de {article_ref.replace('_', ' ') if article_ref else 'un punto tributario específico'} y requiere una lectura profesional aterrizada al caso planteado por el usuario.",
            summary_signal or "Las fuentes consultadas aportan criterio profesional útil para orientar la lectura del caso.",
            "Antes de cerrar la recomendación, conviene verificar soportes, vigencia material y coherencia entre la fuente profesional y la norma base aplicable.",
            "El principal riesgo es convertir una lectura interpretativa en regla absoluta sin revisar los supuestos del caso, el texto vigente y la documentación del expediente.",
        ]
        if classification == "divergencia":
            paragraphs.append("Las fuentes no convergen del todo, así que vale la pena dejar trazada la postura que se adopta y por qué se descarta la alternativa.")
        return "\n\n".join(paragraphs)
    return (
        "## Contexto y alcance\n"
        f"La consulta del usuario es: {message}\n\n"
        "## Análisis del criterio profesional\n"
        f"{summary_signal or 'Las fuentes consultadas aportan criterio profesional útil para este punto.'}\n\n"
        "## Requisitos y condiciones de aplicación\n"
        "1. Confirmar la norma base y la vigencia material.\n"
        "2. Validar el supuesto de hecho del contribuyente.\n"
        "3. Revisar soportes y trazabilidad del expediente.\n\n"
        "## Riesgos tributarios y de fiscalización\n"
        "- Riesgo de extrapolar una interpretación fuera de su supuesto.\n"
        "- Riesgo de omitir soportes o requisitos formales.\n"
        "- Riesgo de no documentar la postura adoptada cuando hay matices o divergencias.\n\n"
        "## Casos prácticos y ejemplos\n"
        "No evidenciado en las fuentes consultadas.\n\n"
        "## Checklist operativo para el contador\n"
        "1. Abrir la norma base.\n"
        "2. Contrastar la fuente profesional con el hecho concreto.\n"
        "3. Documentar la decisión y los soportes.\n\n"
        "## Conclusión y recomendación\n"
        "Usa estas fuentes como criterio profesional de apoyo, no como sustituto de la validación normativa y documental.\n\n"
        "### Extractos usados\n"
        f"{joined}\n"
    )


__all__ = [
    "DecisionFrame",
    "InterpretationCandidate",
    "RankedInterpretation",
    "RankedSelection",
    "build_decision_frame",
    "build_expert_panel_page",
    "build_expert_query_seed",
    "build_fallback_expert_enhancements",
    "build_fallback_expert_explore_content",
    "build_group_summary_signal",
    "build_interpretation_candidate",
    "classify_expert_groups",
    "extract_article_refs",
    "extract_position_signal",
    "normalize_text",
    "order_ranked_interpretations",
    "score_interpretation_candidate",
    "select_interpretation_candidates",
    "serialize_ranked_interpretation",
]
