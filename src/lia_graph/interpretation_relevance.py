from __future__ import annotations

"""Compatibility facade for Interpretación ranking helpers.

The authoritative implementation now lives in `src/lia_graph/interpretacion/`.
Legacy imports keep working through this thin shim so older controller and
dependency wiring can stay stable while the dedicated surface package owns the
real logic.
"""

from .interpretacion.synthesis_helpers import (
    DecisionFrame,
    InterpretationCandidate,
    RankedInterpretation,
    RankedSelection,
    build_decision_frame,
    build_interpretation_candidate,
    select_interpretation_candidates,
    serialize_ranked_interpretation,
)

__all__ = [
    "DecisionFrame",
    "InterpretationCandidate",
    "RankedInterpretation",
    "RankedSelection",
    "build_decision_frame",
    "build_interpretation_candidate",
    "select_interpretation_candidates",
    "serialize_ranked_interpretation",
]
