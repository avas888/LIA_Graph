from __future__ import annotations

from typing import Any

from .shared import NormativaSynthesis


def build_normativa_modal_payload(result: NormativaSynthesis) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "lead": result.lead,
        "hierarchy_summary": result.hierarchy_summary,
        "applicability_summary": result.applicability_summary,
        "professional_impact": result.professional_impact,
        "caution_text": result.caution_text,
        "next_step_1": result.next_steps[0] if result.next_steps else "",
        "next_step_2": result.next_steps[1] if len(result.next_steps) > 1 else "",
        "sections_payload": [section.to_dict() for section in result.sections],
        "diagnostics": dict(result.diagnostics),
    }
    return {key: value for key, value in payload.items() if value not in ("", [], None)}


def build_normativa_analysis_payload(
    *,
    title: str,
    context: dict[str, Any],
    profile: dict[str, Any],
    preview_facts: list[dict[str, str]],
    source_action: dict[str, Any] | None,
    companion_action: dict[str, Any] | None,
    synthesis: NormativaSynthesis,
    timeline_events: list[dict[str, Any]],
    related_documents: list[dict[str, Any]],
    recommended_actions: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "title": title,
        "document_family": str(profile.get("document_family") or context.get("document_family") or "generic").strip(),
        "family_subtype": str(profile.get("family_subtype") or "").strip(),
        "hierarchy_tier": str(profile.get("hierarchy_tier") or "").strip(),
        "binding_force": str(profile.get("binding_force") or "").strip(),
        "binding_force_rank": int(profile.get("binding_force_rank") or 0),
        "analysis_template_id": str(profile.get("analysis_template_id") or "").strip(),
        "ui_surface": str(profile.get("ui_surface") or "").strip(),
        "allowed_secondary_overlays": list(profile.get("allowed_secondary_overlays") or []),
        "lead": synthesis.lead,
        "preview_facts": list(preview_facts or []),
        "caution_banner": dict(profile.get("caution_banner") or {}) or None,
        "sections": [section.to_dict() for section in synthesis.sections],
        "timeline_events": list(timeline_events or []),
        "related_documents": list(related_documents or []),
        "recommended_actions": list(recommended_actions or []),
        "source_action": dict(source_action or {}) or None,
        "companion_action": dict(companion_action or {}) or None,
        "normativa_diagnostics": dict(synthesis.diagnostics),
    }
