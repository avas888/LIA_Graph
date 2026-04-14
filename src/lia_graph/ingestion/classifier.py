"""Deterministic edge typing scaffolds for Phase 2 graph ingestion."""

from __future__ import annotations

from dataclasses import dataclass

from ..graph.schema import EdgeKind, GraphEdgeRecord
from .linker import RawEdgeCandidate


@dataclass(frozen=True)
class ClassifiedEdge:
    record: GraphEdgeRecord
    confidence: float
    rule: str

    def to_dict(self) -> dict[str, object]:
        payload = self.record.to_dict()
        payload["confidence"] = self.confidence
        payload["rule"] = self.rule
        return payload


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
        return _build_edge(candidate, EdgeKind.MODIFIES, 0.95, "keyword_modifies")
    if hint == EdgeKind.SUPERSEDES.value or any(
        keyword in lowered for keyword in ("derog", "reemplaz")
    ):
        return _build_edge(candidate, EdgeKind.SUPERSEDES, 0.92, "keyword_supersedes")
    if hint == EdgeKind.REQUIRES.value or any(
        keyword in lowered for keyword in ("requiere", "debe", "condicion", "acreditar")
    ):
        return _build_edge(candidate, EdgeKind.REQUIRES, 0.75, "keyword_requirement")
    if hint == EdgeKind.DEFINES.value or any(
        keyword in lowered for keyword in ("se entiende por", "define", "definicion")
    ):
        return _build_edge(candidate, EdgeKind.DEFINES, 0.72, "keyword_definition")
    return _build_edge(candidate, EdgeKind.REFERENCES, 0.6, "fallback_reference")


def _build_edge(
    candidate: RawEdgeCandidate,
    edge_kind: EdgeKind,
    confidence: float,
    rule: str,
) -> ClassifiedEdge:
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
            },
        ),
        confidence=confidence,
        rule=rule,
    )
