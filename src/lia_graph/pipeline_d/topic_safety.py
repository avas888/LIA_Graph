"""Router-routing safety checks for pipeline_d.

Added after the citation-faithfulness harness surfaced a systemic failure
mode: ~15% of non-abstaining answers on the gold set were topically wrong
while citing real articles with authoritative formatting. The citation
precision was still 0.99 — the hallucination was at a higher level, at
topic granularity, where an accountant cannot tell "cites real law,
correctly addresses my question" from "cites real law, answers a
different question".

Two checks live here:

1. **Router silent-failure** — when `topic_router.resolve_chat_topic`
   returned `None` / `confidence=0.0` on a query, today the pipeline
   falls through to `general_graph_research` and synthesizes a confident
   template around whatever grab-bag articles retrieval returned.
   ``detect_router_silent_failure`` fires when confidence is below
   ``ROUTER_SILENT_CONFIDENCE_THRESHOLD`` and no topic resolved, so the
   orchestrator can short-circuit to an honest abstention.

2. **Router↔retrieval misalignment** — when the router did pick a topic
   but the primary retrieved articles' vocabulary doesn't match that
   topic (Q1-class failure). ``detect_topic_misalignment`` scores the
   primary articles' titles+excerpts against the topic-router keyword
   dictionary and flags when the router's topic is demonstrably not
   what the retriever found.

Both checks produce a diagnostics dict the orchestrator stashes in
``response.diagnostics.topic_safety`` so the alignment harness can
score the signal without re-running the pipeline.
"""

from __future__ import annotations

from typing import Any

from ..pipeline_c.contracts import PipelineCRequest
from ..topic_router import _score_topic_keywords
from .contracts import GraphEvidenceBundle


# When the router's confidence on a query is at or below this, and no
# effective topic was resolved, treat routing as silently failed and
# abstain instead of synthesizing from arbitrary evidence.
ROUTER_SILENT_CONFIDENCE_THRESHOLD = 0.15

# When a misalignment is detected and the router's own confidence on
# the query was below this, promote the response to an abstention
# (the router was already unsure — misalignment is the tiebreaker).
# Above this, we serve the answer but mark the misalignment in
# diagnostics so the UI can hedge.
MISALIGNMENT_PROMOTE_TO_ABSTENTION_BELOW = 0.50

# How much dominance the top article-topic needs over the router's
# chosen topic to be flagged as misalignment. Specifically: misalignment
# fires when ``top_score >= 3`` AND ``router_score < top_score * 0.34``.
# Numbers tuned against the 30-gold audit — see
# ``docs/done/next/structuralwork_v1_SEENOW.md`` v5.3 landed-state section.
_MISALIGNMENT_MIN_TOP_SCORE = 3
_MISALIGNMENT_ROUTER_RATIO = 0.34


def detect_router_silent_failure(request: PipelineCRequest) -> dict[str, Any] | None:
    """Return a diagnostics dict when the router was silent, else ``None``.

    Caller short-circuits to an abstention response when this returns
    non-None.
    """
    topic = (request.topic or "").strip()
    confidence = float(request.topic_router_confidence or 0.0)
    if not topic and confidence <= ROUTER_SILENT_CONFIDENCE_THRESHOLD:
        # Follow-up turns that quote a prior answer often dilute the topic
        # signal (the quoted text dominates the lexical surface). When the
        # caller carried forward normative anchors via conversation_state,
        # the planner has enough to ground the answer via article_lookup
        # without trusting the router's silent verdict.
        state = request.conversation_state or {}
        anchors = state.get("normative_anchors") if isinstance(state, dict) else None
        if isinstance(anchors, (list, tuple)) and any(
            isinstance(a, str) and a.strip() for a in anchors
        ):
            return None
        return {
            "kind": "router_silent_failure",
            "confidence": confidence,
            "threshold": ROUTER_SILENT_CONFIDENCE_THRESHOLD,
            "reason": (
                "Router did not confidently classify the query into any "
                "top-level topic; refusing to synthesize from arbitrary evidence."
            ),
        }
    return None


def _evidence_topic_scoring_text(evidence: GraphEvidenceBundle) -> str:
    """Concatenate the primary articles' titles + excerpts for scoring.

    We score primary articles specifically (hop-0 planner anchors) because
    those are what the synthesizer will build the answer around; graph
    neighbours are context, not focus.
    """
    parts: list[str] = []
    for item in evidence.primary_articles:
        title = (item.title or "").strip()
        excerpt = (item.excerpt or "").strip()
        if title:
            parts.append(title)
        if excerpt:
            parts.append(excerpt)
    return "\n".join(parts)


def detect_topic_misalignment(
    request: PipelineCRequest,
    evidence: GraphEvidenceBundle,
) -> dict[str, Any]:
    """Score primary articles against topic keywords; compare to router.

    Returns an always-populated diagnostics dict with ``misaligned: bool``
    and the raw scores. The orchestrator decides what to do with the
    signal (abstain vs hedge vs ignore) based on other context.

    v5 §1.A — Multi-topic ArticleNode override: if any primary article
    declares the router_topic in its `secondary_topics` (set via
    `config/article_secondary_topics.json`), treat as on-topic regardless
    of lexical scoring. This is the structural fix for the
    thin-corpus-topic + cross-topic-primary-article pattern measured in
    `docs/learnings/ingestion/coherence-gate-thin-corpus-diagnostic-2026-04-26.md`.
    """
    router_topic = (request.topic or "").strip()
    if not router_topic or not evidence.primary_articles:
        return {
            "misaligned": False,
            "router_topic": router_topic or None,
            "articles_top_topic": None,
            "reason": "no_router_topic" if not router_topic else "no_primary_articles",
        }

    # v5 §1.A — short-circuit on secondary_topics match BEFORE lexical scoring.
    # If even one primary article is curated as also serving the router topic,
    # the article-evidence is by-construction on-topic. Lexical scoring stays
    # the fallback for un-curated articles, which preserves Q1-class
    # contamination guard for the long tail.
    matching_secondary_articles = tuple(
        item.node_key
        for item in evidence.primary_articles
        if router_topic in tuple(getattr(item, "secondary_topics", ()) or ())
    )
    if matching_secondary_articles:
        return {
            "misaligned": False,
            "router_topic": router_topic,
            "articles_top_topic": router_topic,
            "reason": "secondary_topic_match",
            "secondary_topic_matches": list(matching_secondary_articles),
        }

    text = _evidence_topic_scoring_text(evidence)
    scores = _score_topic_keywords(text)
    scored = sorted(
        ((topic, int(data.get("score", 0))) for topic, data in scores.items()),
        key=lambda pair: -pair[1],
    )
    scored = [pair for pair in scored if pair[1] > 0]
    if not scored:
        return {
            "misaligned": False,
            "router_topic": router_topic,
            "articles_top_topic": None,
            "reason": "articles_have_no_topic_keyword_hits",
        }

    top_topic, top_score = scored[0]
    router_score = next((score for topic, score in scored if topic == router_topic), 0)

    misaligned = (
        top_topic != router_topic
        and top_score >= _MISALIGNMENT_MIN_TOP_SCORE
        and router_score < max(1, int(top_score * _MISALIGNMENT_ROUTER_RATIO))
    )

    return {
        "misaligned": bool(misaligned),
        "router_topic": router_topic,
        "articles_top_topic": top_topic,
        "router_score_on_articles": router_score,
        "top_score_on_articles": top_score,
        "ranked_article_topics": scored[:5],
        # v5 §1.A — uniformise the contract so callers can rely on
        # `result['reason']` regardless of which branch fired.
        "reason": "lexical_misaligned" if misaligned else "lexical_aligned",
    }


def should_promote_misalignment_to_abstention(
    request: PipelineCRequest,
    misalignment: dict[str, Any],
) -> bool:
    """Hedge vs abstain decision for a flagged misalignment.

    Abstain when the router was already borderline; keep-but-hedge when
    the router was confident (the harness will still catch the
    misalignment via its own metric even if we serve the answer).
    """
    if not misalignment.get("misaligned"):
        return False
    confidence = float(request.topic_router_confidence or 0.0)
    return confidence < MISALIGNMENT_PROMOTE_TO_ABSTENTION_BELOW


# Abstention text tuned to Lia's existing voice — matches the
# "Cobertura pendiente" and "Con la evidencia disponible todavía no
# alcanzo…" patterns already used for other abstention cases.
def abstention_text_for_router_silent() -> str:
    return (
        "No pude clasificar esta pregunta con confianza dentro del marco "
        "normativo que Lia cubre hoy. Revísala manualmente antes de "
        "responder al cliente; posibles causas: terminología ambigua, "
        "dominio fuera de cobertura, o pregunta multi-tema que requiere "
        "desagregar en consultas más específicas."
    )


def abstention_text_for_misalignment(misalignment: dict[str, Any]) -> str:
    router = misalignment.get("router_topic") or "desconocido"
    articles = misalignment.get("articles_top_topic") or "desconocido"
    return (
        "Detecté un desajuste entre la clasificación de tu pregunta "
        f"(tema: {router}) y los artículos que encontré en el grafo "
        f"(dominan el tema: {articles}). Para evitar darte una "
        "recomendación autoritativa sobre el tema equivocado, prefiero "
        "que confirmes manualmente o reformules la consulta."
    )


__all__ = [
    "ROUTER_SILENT_CONFIDENCE_THRESHOLD",
    "MISALIGNMENT_PROMOTE_TO_ABSTENTION_BELOW",
    "abstention_text_for_misalignment",
    "abstention_text_for_router_silent",
    "detect_router_silent_failure",
    "detect_topic_misalignment",
    "should_promote_misalignment_to_abstention",
]
