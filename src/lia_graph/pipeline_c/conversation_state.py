from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


_NORM_ANCHOR_RE = re.compile(
    r"\b(?:"
    r"(?:ET\s+)?[Aa]rt(?:\.|[íi]culo)?s?\s*\d+(?:[.\-]\d+)*"
    r"|[Ll]ey\s+\d+(?:\s+de\s+\d{4})?"
    r"|[Dd]ecreto\s+\d+(?:\s+de\s+\d{4})?"
    r"|[Rr]esoluci[oó]n\s+\d+(?:\s+de\s+\d{4})?"
    r"|DUR\s+\d+"
    r")",
)
_ENTITY_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("rst", ("rst", "regimen simple", "régimen simple", "simple de tributacion", "simple de tributación")),
    ("regimen_ordinario", ("regimen ordinario", "régimen ordinario", "ordinario")),
    ("beneficio_auditoria", ("beneficio de auditoria", "beneficio de auditoría", "firmeza anticipada")),
    ("ttd", ("ttd", "tasa minima de tributacion", "tasa mínima de tributación")),
    ("2516", ("2516", "formato 2516", "conciliacion fiscal", "conciliación fiscal")),
    ("exogena", ("exogena", "exógena", "formato 1001")),
    ("ica", ("ica", "industria y comercio")),
    ("dian", ("dian", "requerimiento", "liquidacion oficial", "liquidación oficial")),
)
_FOLLOW_UP_MARKERS = (
    "de lo que mencionas",
    "sobre ese punto",
    "en ese caso",
    "si finalmente",
    "si el cliente",
    "si decido",
    "supongamos",
    "y si",
)
_FACT_RE = re.compile(
    r"\b(?:ag\s*\d{4}|a[gñ]o gravable\s*\d{4}|formato\s*\d+|formulario\s*\d+|nit|uvt|"
    r"\d+\s*%|\$\s*[0-9.]+(?:,[0-9]+)?|\d+\s+municipios?)\b",
    flags=re.IGNORECASE,
)


def _dedupe_keep_order(values: list[str] | tuple[str, ...], *, limit: int | None = None) -> tuple[str, ...]:
    seen: set[str] = set()
    items: list[str] = []
    for raw in values:
        value = " ".join(str(raw or "").split()).strip()
        if not value:
            continue
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        items.append(value)
        if limit is not None and len(items) >= limit:
            break
    return tuple(items)


def _compress_user_intent(text: str, *, max_chars: int = 140) -> str:
    cleaned = " ".join(str(text or "").split()).strip()
    if not cleaned:
        return ""
    for marker in ("?", "."):
        idx = cleaned.find(marker)
        if 0 < idx < max_chars:
            return cleaned[: idx + 1].strip()
    if len(cleaned) > max_chars:
        return cleaned[:max_chars].rstrip() + "..."
    return cleaned


def _extract_norm_anchors(text: str) -> tuple[str, ...]:
    return _dedupe_keep_order(list(_NORM_ANCHOR_RE.findall(str(text or ""))), limit=8)


def _extract_entities(text: str) -> tuple[str, ...]:
    lowered = str(text or "").lower()
    hits: list[str] = []
    for label, keywords in _ENTITY_PATTERNS:
        if any(keyword in lowered for keyword in keywords):
            hits.append(label)
    return _dedupe_keep_order(hits, limit=6)


def _extract_facts(text: str) -> tuple[str, ...]:
    matches = [match.group(0).strip() for match in _FACT_RE.finditer(str(text or ""))]
    return _dedupe_keep_order(matches, limit=6)


def _extract_subquestions(text: str) -> tuple[str, ...]:
    normalized = " ".join(str(text or "").split()).strip()
    if not normalized:
        return ()
    segments = [segment.strip(" ?.;") for segment in re.split(r"\?+|;\s+|\.\s+", normalized) if segment.strip()]
    if len(segments) <= 1 and any(marker in normalized.lower() for marker in _FOLLOW_UP_MARKERS):
        return (_compress_user_intent(normalized),)
    return _dedupe_keep_order([_compress_user_intent(segment + "?") for segment in segments if len(segment) >= 18], limit=4)


@dataclass(frozen=True)
class ConversationState:
    goal: str | None = None
    open_subquestions: tuple[str, ...] = ()
    normative_anchors: tuple[str, ...] = ()
    entities: tuple[str, ...] = ()
    working_assumptions: tuple[str, ...] = ()
    carry_forward_facts: tuple[str, ...] = ()
    turn_count: int = 0
    # next_v4 §4 Level 2 — classifier-aware fields. The persistence layer
    # (ui_chat_persistence._build_turn_metadata) already writes effective_topic
    # and secondary_topics into each assistant turn's turn_metadata; these
    # slots make that data first-class on the state so resolve_chat_topic can
    # use it as a soft prior. See topic_router.resolve_chat_topic.
    prior_topic: str | None = None
    prior_subtopic: str | None = None
    topic_trajectory: tuple[str, ...] = ()
    prior_secondary_topics: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "open_subquestions": list(self.open_subquestions),
            "normative_anchors": list(self.normative_anchors),
            "entities": list(self.entities),
            "working_assumptions": list(self.working_assumptions),
            "carry_forward_facts": list(self.carry_forward_facts),
            "turn_count": int(self.turn_count),
            "prior_topic": self.prior_topic,
            "prior_subtopic": self.prior_subtopic,
            "topic_trajectory": list(self.topic_trajectory),
            "prior_secondary_topics": list(self.prior_secondary_topics),
        }

    def to_context_text(self) -> str | None:
        parts: list[str] = []
        if self.goal:
            parts.append(f"Objetivo vigente: {self.goal}")
        if self.open_subquestions:
            parts.append(f"Frentes abiertos: {'; '.join(self.open_subquestions[:3])}")
        if self.normative_anchors:
            parts.append(f"Normas ya citadas: {', '.join(self.normative_anchors[:6])}")
        if self.entities:
            parts.append(f"Entidades/contexto: {', '.join(self.entities[:5])}")
        if self.carry_forward_facts:
            parts.append(f"Hechos acumulados: {', '.join(self.carry_forward_facts[:5])}")
        if not parts:
            return None
        return "\n".join(parts)


def conversation_state_from_dict(payload: dict[str, Any] | None) -> ConversationState | None:
    if not isinstance(payload, dict):
        return None
    goal = str(payload.get("goal") or "").strip() or None
    prior_topic_raw = str(payload.get("prior_topic") or "").strip() or None
    prior_subtopic_raw = str(payload.get("prior_subtopic") or "").strip() or None
    return ConversationState(
        goal=goal,
        open_subquestions=_dedupe_keep_order(tuple(payload.get("open_subquestions") or ()), limit=4),
        normative_anchors=_dedupe_keep_order(tuple(payload.get("normative_anchors") or ()), limit=8),
        entities=_dedupe_keep_order(tuple(payload.get("entities") or ()), limit=6),
        working_assumptions=_dedupe_keep_order(tuple(payload.get("working_assumptions") or ()), limit=4),
        carry_forward_facts=_dedupe_keep_order(tuple(payload.get("carry_forward_facts") or ()), limit=6),
        turn_count=int(payload.get("turn_count") or 0),
        prior_topic=prior_topic_raw,
        prior_subtopic=prior_subtopic_raw,
        topic_trajectory=_dedupe_keep_order(tuple(payload.get("topic_trajectory") or ()), limit=4),
        prior_secondary_topics=_dedupe_keep_order(tuple(payload.get("prior_secondary_topics") or ()), limit=4),
    )


def build_conversation_state(session: Any) -> ConversationState | None:
    turns = list(getattr(session, "turns", []) or [])[-8:]
    if not turns:
        return None

    last_user_goal: str | None = None
    open_subquestions: list[str] = []
    normative_anchors: list[str] = []
    entities: list[str] = []
    carry_forward_facts: list[str] = []
    # next_v4 §4 Level 2 — collect topic continuity from per-turn metadata.
    # ui_chat_persistence._build_turn_metadata writes effective_topic /
    # secondary_topics on each assistant turn; walk oldest-to-newest so the
    # last non-empty value wins as `prior_topic`, and the trajectory captures
    # actual movement (consecutive duplicates compressed).
    topic_trajectory_raw: list[str] = []
    prior_topic: str | None = None
    prior_subtopic: str | None = None
    prior_secondary_topics: tuple[str, ...] = ()

    for turn in turns:
        role = str(getattr(turn, "role", "")).strip().lower()
        content = str(getattr(turn, "content", "")).strip()
        turn_metadata = getattr(turn, "turn_metadata", None) or {}
        if not content and not turn_metadata:
            continue
        if role == "user":
            compressed = _compress_user_intent(content)
            if compressed:
                last_user_goal = compressed
            open_subquestions.extend(_extract_subquestions(content))
            entities.extend(_extract_entities(content))
            carry_forward_facts.extend(_extract_facts(content))
        else:
            normative_anchors.extend(_extract_norm_anchors(content))
            entities.extend(_extract_entities(content))
            if isinstance(turn_metadata, dict):
                for cite in list(turn_metadata.get("citations") or []):
                    if not isinstance(cite, dict):
                        continue
                    normative_anchors.extend(
                        _extract_norm_anchors(
                            " ".join(
                                [
                                    str(cite.get("legal_reference") or ""),
                                    str(cite.get("source_label") or ""),
                                    str(cite.get("doc_id") or ""),
                                ]
                            )
                        )
                    )
                effective_topic = str(turn_metadata.get("effective_topic") or "").strip()
                if effective_topic:
                    if not topic_trajectory_raw or topic_trajectory_raw[-1] != effective_topic:
                        topic_trajectory_raw.append(effective_topic)
                    prior_topic = effective_topic
                    secondaries_raw = turn_metadata.get("secondary_topics") or ()
                    if isinstance(secondaries_raw, (list, tuple)):
                        prior_secondary_topics = _dedupe_keep_order(
                            [str(item).strip() for item in secondaries_raw if str(item).strip()],
                            limit=4,
                        )
                effective_subtopic = str(turn_metadata.get("effective_subtopic") or "").strip()
                if effective_subtopic:
                    prior_subtopic = effective_subtopic

    state = ConversationState(
        goal=last_user_goal,
        open_subquestions=_dedupe_keep_order(open_subquestions, limit=4),
        normative_anchors=_dedupe_keep_order(normative_anchors, limit=8),
        entities=_dedupe_keep_order(entities, limit=6),
        working_assumptions=(),
        carry_forward_facts=_dedupe_keep_order(carry_forward_facts, limit=6),
        turn_count=len(turns),
        prior_topic=prior_topic,
        prior_subtopic=prior_subtopic,
        topic_trajectory=_dedupe_keep_order(topic_trajectory_raw, limit=4),
        prior_secondary_topics=prior_secondary_topics,
    )
    return state if any(state.to_dict().values()) else None


__all__ = [
    "ConversationState",
    "build_conversation_state",
    "conversation_state_from_dict",
]
