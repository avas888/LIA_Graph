"""Unit tests for `lia_graph.pipeline_d.planner_query_modes`.

Locks in the query-mode classification contract that drives
`GraphRetrievalPlan.query_mode` selection. The 9 possible modes each
correspond to a traversal-budget profile in `planner._BUDGETS`, so a
misclassification here means either over-retrieval (slow) or
under-retrieval (wrong answer).
"""

from __future__ import annotations

from lia_graph.pipeline_d.contracts import GraphTemporalContext
from lia_graph.pipeline_d.planner_query_modes import (
    _classify_query_mode,
    _contains_any,
    _count_markers,
    _looks_like_correction_firmness_case,
    _looks_like_loss_compensation_case,
    _looks_like_refund_balance_case,
    _looks_like_tax_planning_case,
    _looks_like_tax_treatment_case,
    _workflow_signal,
    _CORRECTION_FIRMNESS_MARKERS,
    _LOSS_COMPENSATION_MARKERS,
)


def _neutral_context() -> GraphTemporalContext:
    return GraphTemporalContext(historical_query_intent=False)


def _historical_context() -> GraphTemporalContext:
    return GraphTemporalContext(
        historical_query_intent=True,
        requested_period_label="2020",
        cutoff_date="2020-12-31",
    )


def test_contains_any() -> None:
    markers = ("alfa", "beta")
    assert _contains_any("hola alfa mundo", markers) is True
    assert _contains_any("nada aqui", markers) is False
    assert _contains_any("", markers) is False


def test_count_markers_counts_occurrences() -> None:
    assert _count_markers("alfa beta alfa", ("alfa", "beta")) == 2  # distinct markers
    assert _count_markers("nada", ("alfa",)) == 0


def test_workflow_signal_weights_primary_double() -> None:
    result = _workflow_signal(
        normalized_message="perdida fiscal en firmeza",
        primary_markers=("perdida fiscal",),
        context_markers=("firmeza",),
    )
    # primary hit ×2 = 2, plus context hit = 1, total = 3
    assert result == 3


def test_tax_planning_requires_combined_markers() -> None:
    # planning + risk → yes
    assert _looks_like_tax_planning_case("planeacion tributaria con abuso del derecho") is True
    # planning + strategy → yes
    assert _looks_like_tax_planning_case("planeacion tributaria con rst y timing") is True
    # risk + "planeacion" standalone → yes
    assert _looks_like_tax_planning_case("jurisprudencia sobre planeacion y sus limites") is True
    # planning alone → no
    assert _looks_like_tax_planning_case("planeacion tributaria sin contexto") is False
    # none → no
    assert _looks_like_tax_planning_case("hola mundo") is False


def test_tax_treatment_detects_deduction_vocabulary() -> None:
    assert _looks_like_tax_treatment_case("es deducible este gasto") is True
    assert _looks_like_tax_treatment_case("puedo deducir esto") is True
    assert _looks_like_tax_treatment_case("cuanto es la tarifa") is False


def test_loss_compensation_requires_primary_and_score() -> None:
    # primary + plenty of context → fires
    msg = "compensar perdidas fiscales con renta liquida del ano gravable"
    assert _looks_like_loss_compensation_case(msg) is True
    # primary but no context → below score threshold
    assert _looks_like_loss_compensation_case("perdida fiscal") is False
    # no primary marker → no
    assert _looks_like_loss_compensation_case("hola mundo") is False


def test_refund_balance_and_correction_are_mutually_exclusive_with_loss() -> None:
    # loss-compensation message must NOT also be refund_balance or correction
    loss_msg = "compensar perdidas fiscales con renta liquida del ano gravable"
    assert _looks_like_loss_compensation_case(loss_msg) is True
    assert _looks_like_refund_balance_case(loss_msg) is False
    assert _looks_like_correction_firmness_case(loss_msg) is False


def test_refund_balance_fires_on_refund_vocabulary() -> None:
    msg = "devolucion de saldo a favor con requisitos y plazos para solicitar"
    assert _looks_like_refund_balance_case(msg) is True


def test_correction_firmness_fires_on_firmeza_vocabulary() -> None:
    msg = "corregir declaracion de renta antes de la firmeza con emplazamiento"
    assert _looks_like_correction_firmness_case(msg) is True


def test_classify_mode_historical_with_refs_is_reform_chain() -> None:
    mode = _classify_query_mode(
        normalized_message="ley 1819 de 2016",
        article_refs=("art_290",),
        reform_refs=(("ley", "1819"),),
        temporal_context=_historical_context(),
        followup_focus=False,
    )
    assert mode == "historical_reform_chain"


def test_classify_mode_historical_without_refs_is_graph_research() -> None:
    mode = _classify_query_mode(
        normalized_message="en 2019 como era",
        article_refs=(),
        reform_refs=(),
        temporal_context=_historical_context(),
        followup_focus=False,
    )
    assert mode == "historical_graph_research"


def test_classify_mode_single_article_followup_is_article_lookup() -> None:
    mode = _classify_query_mode(
        normalized_message="cuentame mas sobre ese",
        article_refs=("art_290",),
        reform_refs=(),
        temporal_context=_neutral_context(),
        followup_focus=True,
    )
    assert mode == "article_lookup"


def test_classify_mode_tax_planning_is_strategy_chain() -> None:
    mode = _classify_query_mode(
        normalized_message="planeacion tributaria y abuso del derecho",
        article_refs=(),
        reform_refs=(),
        temporal_context=_neutral_context(),
        followup_focus=False,
    )
    assert mode == "strategy_chain"


def test_classify_mode_loss_compensation_with_firmeza_is_obligation_chain() -> None:
    # loss + firmeza keyword → obligation_chain (firmeza context override)
    mode = _classify_query_mode(
        normalized_message="compensar perdidas fiscales y firmeza de la declaracion de renta liquida",
        article_refs=(),
        reform_refs=(),
        temporal_context=_neutral_context(),
        followup_focus=False,
    )
    assert mode == "obligation_chain"


def test_classify_mode_loss_compensation_without_firmeza_is_computation_chain() -> None:
    mode = _classify_query_mode(
        normalized_message="compensar perdidas fiscales con renta liquida ano gravable limite anual",
        article_refs=(),
        reform_refs=(),
        temporal_context=_neutral_context(),
        followup_focus=False,
    )
    assert mode == "computation_chain"


def test_classify_mode_reform_refs_force_reform_chain() -> None:
    mode = _classify_query_mode(
        normalized_message="que dice la ley",
        article_refs=(),
        reform_refs=(("ley", "1819"),),
        temporal_context=_neutral_context(),
        followup_focus=False,
    )
    assert mode == "reform_chain"


def test_classify_mode_definition_markers() -> None:
    mode = _classify_query_mode(
        normalized_message="que es el concepto de renta",
        article_refs=(),
        reform_refs=(),
        temporal_context=_neutral_context(),
        followup_focus=False,
    )
    assert mode == "definition_chain"


def test_classify_mode_obligation_markers() -> None:
    mode = _classify_query_mode(
        normalized_message="que sancion aplica si incumplo el requisito",
        article_refs=(),
        reform_refs=(),
        temporal_context=_neutral_context(),
        followup_focus=False,
    )
    assert mode == "obligation_chain"


def test_classify_mode_tax_treatment_is_computation_chain() -> None:
    mode = _classify_query_mode(
        normalized_message="puedo deducir este gasto",
        article_refs=(),
        reform_refs=(),
        temporal_context=_neutral_context(),
        followup_focus=False,
    )
    assert mode == "computation_chain"


def test_classify_mode_single_article_no_context_is_article_lookup() -> None:
    mode = _classify_query_mode(
        normalized_message="describeme",
        article_refs=("art_290",),
        reform_refs=(),
        temporal_context=_neutral_context(),
        followup_focus=False,
    )
    assert mode == "article_lookup"


def test_classify_mode_fallback_is_general_graph_research() -> None:
    mode = _classify_query_mode(
        normalized_message="pregunta generica sin marcadores",
        article_refs=(),
        reform_refs=(),
        temporal_context=_neutral_context(),
        followup_focus=False,
    )
    assert mode == "general_graph_research"


def test_reexport_from_planner_preserves_identity() -> None:
    # Round-9 guard: host must re-import these names, not redefine them.
    from lia_graph.pipeline_d import planner
    assert planner._classify_query_mode is _classify_query_mode
    assert planner._looks_like_tax_planning_case is _looks_like_tax_planning_case
    assert planner._LOSS_COMPENSATION_MARKERS is _LOSS_COMPENSATION_MARKERS
    assert planner._CORRECTION_FIRMNESS_MARKERS is _CORRECTION_FIRMNESS_MARKERS
