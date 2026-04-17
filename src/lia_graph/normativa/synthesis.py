from __future__ import annotations

from .sections import (
    build_applicability_summary,
    build_caution_text,
    build_hierarchy_summary,
    build_lead,
    build_next_steps,
    build_professional_impact,
    build_relations_summary,
    build_surface_sections,
)
from .shared import NormativaSynthesis, title_hint
from .synthesis_helpers import (
    binding_force_from_context,
    build_normativa_diagnostics,
    collect_anchor_lines,
    collect_relation_lines,
    collect_support_lines,
)


def synthesize_normativa_surface(
    *,
    context: dict[str, object],
    evidence: object,
    query_mode: str,
) -> NormativaSynthesis:
    title = title_hint(context)
    binding_force = binding_force_from_context(context)
    anchor_lines = collect_anchor_lines(evidence)
    relation_lines = collect_relation_lines(evidence)
    support_lines = collect_support_lines(evidence)

    lead = build_lead(anchor_lines)
    hierarchy_summary = build_hierarchy_summary(
        binding_force=binding_force,
        anchor_title=relation_lines[0] if relation_lines else "",
    )
    applicability_summary = build_applicability_summary(list(anchor_lines))
    professional_impact = build_professional_impact(
        support_lines=list(support_lines),
        relation_lines=list(relation_lines),
    )
    relations_summary = build_relations_summary(
        relation_lines=relation_lines,
        support_lines=support_lines,
    )
    caution_text = build_caution_text(
        missing_primary=not bool(anchor_lines),
        has_reforms=bool(relation_lines),
    )
    sections = build_surface_sections(
        context=context,
        applicability_summary=applicability_summary,
        professional_impact=professional_impact,
        relations_summary=relations_summary,
    )
    return NormativaSynthesis(
        lead=lead,
        hierarchy_summary=hierarchy_summary,
        applicability_summary=applicability_summary,
        professional_impact=professional_impact,
        relations_summary=relations_summary,
        caution_text=caution_text,
        next_steps=build_next_steps(
            title=title,
            has_support_docs=bool(support_lines),
            has_reforms=bool(relation_lines),
        ),
        sections=sections,
        diagnostics=build_normativa_diagnostics(query_mode=query_mode, evidence=evidence),
    )
