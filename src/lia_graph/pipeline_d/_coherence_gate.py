"""Phase 3 (v6) — evidence-topic coherence gate.

Extends topic_safety's misalignment detector to the zero-primary cases
that topic_safety short-circuits through. Three cases:

* A — primary articles exist → delegate to primary_misalignment.
* B — primary empty, support docs present → score support docs' topic_key
      (first-class metadata) and fall back to lexical scoring.
* C — primary empty and support off-topic → refuse on no_evidence.

Flag-gated by ``LIA_EVIDENCE_COHERENCE_GATE={off|shadow|enforce}``, default
``shadow`` so observation comes before enforcement.
"""

from __future__ import annotations

import os
from typing import Any

from ..pipeline_c.contracts import PipelineCRequest
from ..topic_router import _score_topic_keywords
from .contracts import GraphEvidenceBundle

_SUPPORT_DOC_TOP_SCORE_MIN = 3
_SUPPORT_DOC_TOPIC_KEY_MATCH_MIN = 2


def coherence_mode() -> str:
    # Default `enforce` 2026-04-25 per operator's "no off/shadow flags" directive
    # (risk-forward internal-beta stance). Step-04 verification measured
    # would-refuse=1/30, well below the [4,12] safe band — meaning enforce mode
    # at the current threshold refuses ~3% of queries with low contamination
    # upside. Watch production refusal-rate; revert to `shadow` if regressions.
    raw = (os.getenv("LIA_EVIDENCE_COHERENCE_GATE") or "enforce").strip().lower()
    return raw if raw in ("off", "shadow", "enforce") else "enforce"


def _support_doc_topic_scoring_text(evidence: GraphEvidenceBundle) -> str:
    return "\n".join(
        (doc.title_hint or "").strip()
        for doc in evidence.support_documents
        if (doc.title_hint or "").strip()
    )


def _count_support_topic_key_matches(
    evidence: GraphEvidenceBundle, router_topic: str
) -> int:
    return sum(
        1 for doc in evidence.support_documents
        if (doc.topic_key or "").strip() == router_topic
    )


def detect_evidence_coherence(
    request: PipelineCRequest,
    evidence: GraphEvidenceBundle,
    primary_misalignment: dict[str, Any],
) -> dict[str, Any]:
    """Always returns a populated dict. ``misaligned=False`` is the happy case."""
    router_topic = (request.topic or "").strip()
    if not router_topic:
        return {"misaligned": False, "source": "no_router_topic",
                "router_topic": None, "reason": "no_router_topic"}

    # Case A — primary articles exist.
    if evidence.primary_articles:
        if primary_misalignment.get("misaligned"):
            return {"misaligned": True, "source": "primary",
                    "router_topic": router_topic,
                    "dominant_topic": primary_misalignment.get("articles_top_topic"),
                    "reason": "primary_off_topic"}
        return {"misaligned": False, "source": "primary",
                "router_topic": router_topic,
                "dominant_topic": primary_misalignment.get("articles_top_topic") or router_topic,
                "reason": "primary_on_topic"}

    # Cases B & C — primary empty. Prefer first-class topic_key match.
    topic_key_matches = _count_support_topic_key_matches(evidence, router_topic)
    if topic_key_matches >= _SUPPORT_DOC_TOPIC_KEY_MATCH_MIN:
        return {"misaligned": False, "source": "support_documents",
                "router_topic": router_topic, "dominant_topic": router_topic,
                "topic_key_matches": topic_key_matches,
                "reason": "support_docs_on_topic"}

    if evidence.support_documents:
        text = _support_doc_topic_scoring_text(evidence)
        scores = _score_topic_keywords(text) if text else {}
        if scores:
            top_topic, top_data = max(
                scores.items(), key=lambda kv: int(kv[1].get("score", 0))
            )
            top_score = int(top_data.get("score", 0))
            if top_topic != router_topic and top_score >= _SUPPORT_DOC_TOP_SCORE_MIN:
                return {"misaligned": True, "source": "support_documents",
                        "router_topic": router_topic, "dominant_topic": top_topic,
                        "topic_key_matches": topic_key_matches,
                        "top_lexical_score": top_score,
                        "reason": "chunks_off_topic"}

    return {"misaligned": True, "source": "no_evidence",
            "router_topic": router_topic, "dominant_topic": None,
            "topic_key_matches": topic_key_matches,
            "reason": "zero_evidence_for_router_topic"}


def should_refuse(coherence: dict[str, Any], mode: str | None = None) -> bool:
    if not coherence.get("misaligned"):
        return False
    return (mode or coherence_mode()).strip().lower() == "enforce"


def refusal_text(coherence: dict[str, Any]) -> str:
    reason = coherence.get("reason") or "zero_evidence_for_router_topic"
    router = coherence.get("router_topic") or "desconocido"
    dominant = coherence.get("dominant_topic")
    if reason == "chunks_off_topic" and dominant:
        return (f"No pude ubicar evidencia del tema **{router}** en el grafo. "
                f"Los documentos de apoyo recuperados pertenecen al tema "
                f"**{dominant}**; prefiero no responder con evidencia cruzada. "
                "Reformula la consulta o confirma si necesitas orientación de ese otro tema.")
    if reason == "primary_off_topic" and dominant:
        return (f"Detecté que los artículos primarios recuperados pertenecen al tema "
                f"**{dominant}**, no al tema clasificado **{router}**. "
                "Para evitar una respuesta autoritativa sobre el tema equivocado, "
                "confirma manualmente o reformula la consulta.")
    return (f"Evidencia insuficiente para responder con respaldo normativo en el tema "
            f"**{router}**. Reformula la consulta o revisa manualmente antes de "
            "responder al cliente.")


__all__ = ["coherence_mode", "detect_evidence_coherence", "refusal_text", "should_refuse"]
