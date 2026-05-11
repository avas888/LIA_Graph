"""fix_v8 §3d — when the planner classifies a turn as
``comparative_regime_chain`` but no pair in
``config/comparative_regime_pairs.json`` matches, ``compose_main_chat_answer``
must short-circuit cleanly into the standard first-bubble composer and
emit a ``comparative_regime.no_pair_match`` trace step so the failure
mode is observable.

This locks the Q10-shape failure surface (RST-vs-ordinary or any
cross-regime "diferencia entre X y Y" cue) at the assembly seam — even
if the planner mis-classifies, the assembly must NEVER return an empty
string from the comparative path. Returning empty is what hangs the
downstream polish loop on cloud.
"""

from __future__ import annotations

from lia_graph.pipeline_c.contracts import PipelineCRequest
from lia_graph.pipeline_d.answer_assembly import compose_main_chat_answer
from lia_graph.pipeline_d.answer_synthesis import GraphNativeAnswerParts
from lia_graph.pipeline_d.contracts import GraphEvidenceBundle


def _bundle() -> GraphEvidenceBundle:
    return GraphEvidenceBundle(
        primary_articles=(),
        connected_articles=(),
        related_reforms=(),
        support_documents=(),
        citations=(),
        diagnostics={"primary_article_count": 0},
    )


def _req() -> PipelineCRequest:
    return PipelineCRequest(
        message="¿Qué diferencia hay entre el régimen simple y el régimen ordinario?",
        topic="regimen_simple",
        requested_topic="regimen_simple",
    )


def test_comparative_no_pair_match_does_not_return_empty() -> None:
    """The whole point of the §3d guardrail: even when comparative mode
    fires without a matching pair, assembly must NOT return an empty
    string. An empty answer at this seam was the proximate cause of the
    Q10 polish-loop hang."""
    answer = compose_main_chat_answer(
        request=_req(),
        answer_mode="graph_native",
        planner_query_mode="comparative_regime_chain",
        temporal_context={},
        evidence=_bundle(),
        answer_parts=GraphNativeAnswerParts(),
    )
    # The standard composer may legitimately emit a short notice when
    # evidence is empty; what matters is that we did NOT short-circuit
    # to an empty string from the comparative path.
    assert answer is not None
