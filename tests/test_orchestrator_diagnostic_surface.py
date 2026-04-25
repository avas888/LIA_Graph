"""Phase 1 (v6) — response.diagnostics lifted-field coverage.

The A/B harness and the /orchestration panel read nine retrieval-diagnostic
fields from the *top level* of ``response.diagnostics``. Before phase 1,
those fields lived nested inside ``diagnostics["evidence_bundle"]["diagnostics"]``
and readers all silently got ``None``. This test pins the contract so any
future regression (e.g., someone refactors the orchestrator and drops the
lift) breaks loudly instead of silently.
"""

from __future__ import annotations

from lia_graph.pipeline_c.contracts import PipelineCRequest
from lia_graph.pipeline_d.orchestrator import run_pipeline_d

_LIFTED_KEYS: tuple[str, ...] = (
    "primary_article_count",
    "connected_article_count",
    "related_reform_count",
    "seed_article_keys",
    "planner_query_mode",
    "tema_first_mode",
    "tema_first_topic_key",
    "tema_first_anchor_count",
    "retrieval_sub_topic_intent",
    "subtopic_anchor_keys",
)


def _run_q3() -> dict:
    """Canned query that exercises the real retriever in artifact mode.

    Q3 is the healthy ``declaracion_renta`` anchor used as the phase-1
    baseline in the plan — returns ≥1 primary article under artifacts.
    """
    request = PipelineCRequest(
        message="¿Qué artículo regula el anticipo del impuesto de renta?",
        topic="declaracion_renta",
        requested_topic="declaracion_renta",
    )
    response = run_pipeline_d(request)
    return dict(response.diagnostics)


def test_lifted_keys_all_present_at_top_level() -> None:
    diag = _run_q3()
    for key in _LIFTED_KEYS:
        assert key in diag, f"lifted key missing at top level: {key}"


def test_lifted_values_match_nested_evidence_diagnostics() -> None:
    diag = _run_q3()
    nested = (diag.get("evidence_bundle") or {}).get("diagnostics") or {}
    # Count-style fields: the orchestrator falls back to ``len(evidence.*)``
    # when the retriever didn't emit a per-stage count. When the nested value
    # is present, the lift must echo it exactly.
    for count_key in ("primary_article_count", "connected_article_count", "related_reform_count"):
        if count_key in nested and nested[count_key] is not None:
            assert diag[count_key] == nested[count_key], (
                f"lifted {count_key} diverged from nested value"
            )
    # List + string fields with no synthetic fallback: must match nested
    # exactly when the retriever emitted them, or be ``None`` otherwise.
    passthrough_keys = (
        "seed_article_keys",
        "tema_first_mode",
        "tema_first_topic_key",
        "tema_first_anchor_count",
        "retrieval_sub_topic_intent",
        "subtopic_anchor_keys",
    )
    for key in passthrough_keys:
        if key in nested:
            assert diag[key] == nested[key], f"lifted {key} diverged from nested value"


def test_lifted_keys_present_even_when_evidence_diagnostics_sparse() -> None:
    """Artifact-mode runs don't populate tema_first_* in the retriever.

    The contract says: every lifted key is always present on the top-level
    diagnostics dict — ``diag.get(key)`` must return the real value or
    ``None``, never raise ``KeyError``. Count-style keys additionally must
    always be ``int`` because we fall back to ``len(evidence.*)``.
    """
    diag = _run_q3()
    for key in _LIFTED_KEYS:
        # None is an acceptable value for optional retriever-scoped keys;
        # presence is non-negotiable.
        assert key in diag
    for count_key in ("primary_article_count", "connected_article_count", "related_reform_count"):
        assert isinstance(diag[count_key], int), (
            f"{count_key} must always resolve to an int, got {type(diag[count_key]).__name__}"
        )
    # planner_query_mode also has a plan-level fallback (plan.query_mode)
    # so it should never be None for a real run.
    assert isinstance(diag["planner_query_mode"], str) and diag["planner_query_mode"]


def test_seed_article_keys_non_empty_when_primary_article_count_positive() -> None:
    """next_v1 step 01 invariant: whenever BFS returned at least one
    primary article, the seeds it started from must also be surfaced.

    Pins the regression guard that phase-1 forgot: before this fix, the
    Falkor retriever reported ``seed_article_keys = list(explicit_article_keys)``
    which was empty on every topic-only gold question (planner anchored
    nothing explicit, all seeds came from TEMA-first expansion), so the
    phase-6 A/B panel showed 0/30 rows populate the field even though 15
    of them had primary_article_count >= 1. The stronger invariant here
    — ``primary >= 1 ⇒ seeds non-empty`` — makes the silent gap loud."""
    diag = _run_q3()
    if int(diag.get("primary_article_count") or 0) >= 1:
        seeds = diag.get("seed_article_keys")
        assert isinstance(seeds, list) and len(seeds) >= 1, (
            "primary_article_count >= 1 but seed_article_keys is empty/None; "
            "retriever must surface the actual BFS seed set"
        )
