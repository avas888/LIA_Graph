from __future__ import annotations

from dataclasses import replace
import re
from typing import Any

from ..pipeline_c.contracts import PipelineCRequest
from ..pipeline_d.contracts import PlannerEntryPoint
from ..pipeline_d.planner import build_graph_retrieval_plan
from ..pipeline_d.retriever import retrieve_graph_evidence
from ..topic_guardrails import normalize_topic_key
from .policy import NORMATIVA_QUERY_SUFFIX
from .synthesis import synthesize_normativa_surface


_REF_KEY_RE = re.compile(r"^(ley|decreto|resolucion(?:_dian)?):(\d+)(?::(\d{4}))?$", re.IGNORECASE)
_TITLE_REFORM_RE = re.compile(r"\b(Ley|Decreto|Resoluci[oó]n)\s+(\d+)(?:\s+de\s+(\d{4}))?\b", re.IGNORECASE)


def _build_query(context: dict[str, Any]) -> str:
    citation = dict(context.get("citation") or {})
    parts = [
        str(context.get("title") or "").strip(),
        str(citation.get("legal_reference") or "").strip(),
        str(citation.get("source_label") or "").strip(),
        str(citation.get("locator_text") or "").strip(),
        str(context.get("message_context") or "").strip(),
        NORMATIVA_QUERY_SUFFIX,
    ]
    return " | ".join(part for part in parts if part)


def _topic_hint(context: dict[str, Any]) -> str | None:
    citation = dict(context.get("citation") or {})
    row = dict(context.get("requested_row") or {})
    return normalize_topic_key(
        str(citation.get("topic") or row.get("tema") or row.get("topic") or "").strip() or None
    )


def _reform_entry_from_context(context: dict[str, Any]) -> PlannerEntryPoint | None:
    citation = dict(context.get("citation") or {})
    candidates = [
        str(citation.get("reference_key") or "").strip(),
        str(citation.get("legal_reference") or "").strip(),
        str(context.get("title") or "").strip(),
    ]
    for candidate in candidates:
        match = _REF_KEY_RE.match(candidate.lower())
        if match:
            prefix = "RESOLUCION" if match.group(1).startswith("resolucion") else match.group(1).upper()
            year = match.group(3) or "s_f"
            key = f"{prefix}-{match.group(2)}-{year}"
            label = str(context.get("title") or candidate).strip() or key
            return PlannerEntryPoint(
                kind="reform",
                lookup_value=key,
                source="normativa_context",
                confidence=0.99,
                label=label,
                resolved_key=key,
            )
        title_match = _TITLE_REFORM_RE.search(candidate)
        if title_match:
            prefix = title_match.group(1).upper().replace("Ó", "O")
            year = title_match.group(3) or "s_f"
            key = f"{prefix}-{title_match.group(2)}-{year}"
            return PlannerEntryPoint(
                kind="reform",
                lookup_value=key,
                source="normativa_context",
                confidence=0.95,
                label=title_match.group(0).strip(),
                resolved_key=key,
            )
    return None


def _article_entry_from_context(context: dict[str, Any]) -> PlannerEntryPoint | None:
    citation = dict(context.get("citation") or {})
    locator = str(
        citation.get("locator_start")
        or citation.get("locator_text")
        or context.get("locator_start")
        or ""
    ).strip()
    if not locator:
        return None
    normalized = locator.replace(".", "-").replace("_", "-")
    if not re.fullmatch(r"\d+(?:-\d+)*", normalized):
        return None
    return PlannerEntryPoint(
        kind="article",
        lookup_value=normalized,
        source="normativa_context",
        confidence=0.99,
        label=f"Art. {normalized}",
        resolved_key=normalized,
    )


def _extra_entry_points(context: dict[str, Any]) -> tuple[PlannerEntryPoint, ...]:
    entries: list[PlannerEntryPoint] = []
    article_entry = _article_entry_from_context(context)
    if article_entry is not None:
        entries.append(article_entry)
    reform_entry = _reform_entry_from_context(context)
    if reform_entry is not None:
        entries.append(reform_entry)
    title = str(context.get("title") or "").strip()
    if title:
        entries.append(
            PlannerEntryPoint(
                kind="article_search",
                lookup_value=title,
                source="normativa_title_search",
                confidence=0.72,
                label="normativa title search",
            )
        )
    topic = _topic_hint(context)
    if topic:
        entries.append(
            PlannerEntryPoint(
                kind="topic",
                lookup_value=topic,
                source="normativa_topic_hint",
                confidence=0.7,
                label=topic,
                resolved_key=topic,
            )
        )
    seen: set[tuple[str, str]] = set()
    unique: list[PlannerEntryPoint] = []
    for entry in entries:
        key = (entry.kind, entry.lookup_value)
        if key in seen:
            continue
        seen.add(key)
        unique.append(entry)
    return tuple(unique)


def run_normativa_surface(context: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    request = PipelineCRequest(
        message=_build_query(context),
        topic=_topic_hint(context),
        requested_topic=_topic_hint(context),
        response_route="theoretical_normative",
        retrieval_profile="hybrid_rerank",
        conversation_context=str(context.get("message_context") or "").strip() or None,
        debug=False,
    )
    plan = build_graph_retrieval_plan(request)
    extra = _extra_entry_points(context)
    if extra:
        plan = replace(
            plan,
            entry_points=tuple(extra) + tuple(plan.entry_points),
        )
    plan, evidence = retrieve_graph_evidence(plan)
    synthesis = synthesize_normativa_surface(
        context=context,
        evidence=evidence,
        query_mode=plan.query_mode,
    )
    return synthesis.diagnostics, {
        "synthesis": synthesis,
        "plan": plan,
        "evidence": evidence,
    }
