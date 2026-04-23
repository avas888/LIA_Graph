"""Deterministic edge typing scaffolds for Phase 2 graph ingestion.

ingestionfix_v2 §4 Phase 4 introduces a parallel Spanish-taxonomy
``edge_type`` (MODIFICA / DEROGA / CITA / PRACTICA_DE / INTERPRETA_A /
MENCIONA) and a ``weight`` scalar on every classified edge. The legacy
English ``EdgeKind`` enum is unchanged — it still drives the
``normative_edges.relation`` column + the Falkor-side EdgeKind label —
while ``edge_type`` adds a family-origin-aware typing layer used by
downstream retrieval / ranking.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..graph.schema import EdgeKind, GraphEdgeRecord, default_graph_schema
from .linker import RawEdgeCandidate


# Phase-4 taxonomy constants. Spanish string values mirror the
# database CHECK constraint introduced by
# supabase/migrations/20260423000000_normative_edges_typed.sql.
EDGE_TYPE_MODIFICA = "MODIFICA"
EDGE_TYPE_DEROGA = "DEROGA"
EDGE_TYPE_CITA = "CITA"
EDGE_TYPE_PRACTICA_DE = "PRACTICA_DE"
EDGE_TYPE_INTERPRETA_A = "INTERPRETA_A"
EDGE_TYPE_MENCIONA = "MENCIONA"

# Per-type weights. Higher weight = more authoritative. Downstream
# retrieval uses these to rank edge-driven evidence.
_WEIGHT_NORMATIVA_AUTHORITATIVE = 1.0
_WEIGHT_PRACTICA = 0.6
_WEIGHT_INTERPRETACION = 0.6
_WEIGHT_CASUAL_MENTION = 0.2

_INTERPRETIVE_FAMILIES = frozenset({"interpretacion", "expertos"})


@dataclass(frozen=True)
class ClassifiedEdge:
    record: GraphEdgeRecord
    confidence: float
    rule: str
    # ingestionfix_v2 §4 Phase 4 additions. Both optional for back-compat
    # with older pickled edges / third-party callers.
    edge_type: str | None = None
    weight: float = 1.0

    def to_dict(self) -> dict[str, object]:
        payload = self.record.to_dict()
        payload["confidence"] = self.confidence
        payload["rule"] = self.rule
        payload["edge_type"] = self.edge_type
        payload["weight"] = self.weight
        return payload


def _resolve_edge_type_and_weight(
    *,
    source_family: str | None,
    kind: EdgeKind,
    relation_hint: str | None,
) -> tuple[str, float]:
    """Map (source_family, kind, relation_hint) → (edge_type, weight).

    Rules per ingestionfix_v2 §4 Phase 4:
      * normativa + MODIFIES-like → MODIFICA (1.0)
      * normativa + SUPERSEDES-like → DEROGA (1.0)
      * normativa + vanilla citation → CITA (1.0)
      * practica → PRACTICA_DE (0.6)
      * interpretacion / expertos → INTERPRETA_A (0.6)
      * no family known AND no authority hint → MENCIONA (0.2)
    """
    family = (source_family or "").strip().lower() or None
    if family == "normativa":
        if kind is EdgeKind.MODIFIES or relation_hint == EdgeKind.MODIFIES.value:
            return EDGE_TYPE_MODIFICA, _WEIGHT_NORMATIVA_AUTHORITATIVE
        if kind is EdgeKind.SUPERSEDES or relation_hint == EdgeKind.SUPERSEDES.value:
            return EDGE_TYPE_DEROGA, _WEIGHT_NORMATIVA_AUTHORITATIVE
        return EDGE_TYPE_CITA, _WEIGHT_NORMATIVA_AUTHORITATIVE
    if family == "practica":
        return EDGE_TYPE_PRACTICA_DE, _WEIGHT_PRACTICA
    if family in _INTERPRETIVE_FAMILIES:
        return EDGE_TYPE_INTERPRETA_A, _WEIGHT_INTERPRETACION
    # Unknown family, or casual prose reference. If the relation_hint
    # signaled authority (MODIFIES/SUPERSEDES), preserve the authoritative
    # type even when family is unset — legacy rows from before the family
    # plumbing still deserve the right edge_type.
    if relation_hint == EdgeKind.MODIFIES.value:
        return EDGE_TYPE_MODIFICA, _WEIGHT_NORMATIVA_AUTHORITATIVE
    if relation_hint == EdgeKind.SUPERSEDES.value:
        return EDGE_TYPE_DEROGA, _WEIGHT_NORMATIVA_AUTHORITATIVE
    return EDGE_TYPE_MENCIONA, _WEIGHT_CASUAL_MENTION


def classify_edge_candidates(
    candidates: tuple[RawEdgeCandidate, ...] | list[RawEdgeCandidate],
    *,
    min_confidence: float = 0.0,
) -> tuple[ClassifiedEdge, ...]:
    classified: dict[tuple[str, str, str, str], ClassifiedEdge] = {}
    for candidate in candidates:
        edge = _classify_candidate(candidate)
        if edge.confidence < min_confidence:
            continue
        key = (
            edge.record.kind.value,
            edge.record.source_key,
            edge.record.target_kind.value,
            edge.record.target_key,
        )
        current = classified.get(key)
        if current is None or edge.confidence > current.confidence:
            classified[key] = edge
    return tuple(
        classified[key]
        for key in sorted(classified, key=lambda item: (item[1], item[0], item[2], item[3]))
    )


def _classify_candidate(candidate: RawEdgeCandidate) -> ClassifiedEdge:
    lowered = candidate.context.lower()
    hint = (candidate.relation_hint or "").upper()

    if candidate.target_kind.value == "ArticleNode" and (
        hint == EdgeKind.COMPUTATION_DEPENDS_ON.value
        or any(keyword in lowered for keyword in ("conforme", "calcular", "depende", "base gravable"))
    ):
        return _build_edge(
            candidate,
            EdgeKind.COMPUTATION_DEPENDS_ON,
            0.8,
            "keyword_computation_dependency",
        )
    if candidate.target_kind.value == "ArticleNode" and (
        hint == EdgeKind.EXCEPTION_TO.value
        or any(keyword in lowered for keyword in ("excepto", "salvo", "no obstante"))
    ):
        return _build_edge(candidate, EdgeKind.EXCEPTION_TO, 0.84, "keyword_exception")
    if hint == EdgeKind.MODIFIES.value or any(
        keyword in lowered for keyword in ("modific", "adicion", "subrog", "sustituy")
    ):
        edge = _build_edge(candidate, EdgeKind.MODIFIES, 0.95, "keyword_modifies")
        if _edge_is_schema_valid(edge):
            return edge
    if hint == EdgeKind.SUPERSEDES.value or any(
        keyword in lowered for keyword in ("derog", "reemplaz")
    ):
        edge = _build_edge(candidate, EdgeKind.SUPERSEDES, 0.92, "keyword_supersedes")
        if _edge_is_schema_valid(edge):
            return edge
    if hint == EdgeKind.REQUIRES.value or any(
        keyword in lowered for keyword in ("requiere", "debe", "condicion", "acreditar")
    ):
        edge = _build_edge(candidate, EdgeKind.REQUIRES, 0.75, "keyword_requirement")
        if _edge_is_schema_valid(edge):
            return edge
    if hint == EdgeKind.DEFINES.value or any(
        keyword in lowered for keyword in ("se entiende por", "define", "definicion")
    ):
        edge = _build_edge(candidate, EdgeKind.DEFINES, 0.72, "keyword_definition")
        if _edge_is_schema_valid(edge):
            return edge
    return _build_edge(candidate, EdgeKind.REFERENCES, 0.6, "fallback_reference")


def _build_edge(
    candidate: RawEdgeCandidate,
    edge_kind: EdgeKind,
    confidence: float,
    rule: str,
) -> ClassifiedEdge:
    edge_type, weight = _resolve_edge_type_and_weight(
        source_family=candidate.source_family,
        kind=edge_kind,
        relation_hint=candidate.relation_hint,
    )
    return ClassifiedEdge(
        record=GraphEdgeRecord(
            kind=edge_kind,
            source_kind=candidate.source_kind,
            source_key=candidate.source_key,
            target_kind=candidate.target_kind,
            target_key=candidate.target_key,
            properties={
                "raw_reference": candidate.raw_reference,
                "context": candidate.context,
                "relation_hint": candidate.relation_hint,
                "classifier_rule": rule,
                "source_family": candidate.source_family,
                "edge_type": edge_type,
                "weight": weight,
            },
        ),
        confidence=confidence,
        rule=rule,
        edge_type=edge_type,
        weight=weight,
    )


def _edge_is_schema_valid(edge: ClassifiedEdge) -> bool:
    schema = default_graph_schema()
    try:
        schema.validate_edge_record(edge.record)
    except ValueError:
        return False
    return True
