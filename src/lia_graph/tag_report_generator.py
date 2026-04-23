"""Tag-review LLM brief builder (ingestionfix_v2 §4 Phase 7).

Assembles a Markdown brief that helps an expert decide how to resolve a
flagged tag review:

  * title + first ~500 words of the doc
  * current tags on the doc
  * top-3 classifier alternatives (from the PASO 4 verdict snapshot)
  * neighborhood samples — 3 similar docs per candidate tag, fetched
    via the existing pgvector-backed ``hybrid_search`` RPC
  * extracted legal references (laws / decrees / resolutions)

The brief is deterministic at assembly time. When an LLM adapter is
available, it's used to polish the free-text framing only; the factual
sections stay structurally intact and regex-extractable. The LLM is a
convenience, not a dependency — if no adapter is configured the
deterministic brief is returned verbatim.

Contract::

    generate_tag_report(
        doc_row,                       # dict from ``documents``
        classifier_alternatives=...,   # list[dict] — optional
        similar_docs_by_tag=...,       # dict[str, list[dict]] — optional
        llm_adapter=...,               # LLMAdapter | None — optional
    ) -> TagReport
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


_LAW_RE = re.compile(
    r"(?i)\b(?:Ley|Decreto|Resoluci[oó]n|Concepto|Sentencia)\s+\d+(?:\s+de\s+\d{4})?"
)


@dataclass(frozen=True)
class TagReport:
    report_id: str
    doc_id: str
    markdown: str
    first_500_words: str
    legal_references: tuple[str, ...] = ()
    llm_polished: bool = False
    skip_reason: str | None = None


def _doc_title(doc_row: Mapping[str, Any]) -> str:
    candidates = (
        doc_row.get("first_heading"),
        doc_row.get("title_hint"),
        doc_row.get("relative_path"),
        doc_row.get("doc_id"),
    )
    for cand in candidates:
        if cand and str(cand).strip():
            return str(cand).strip()
    return "(sin título)"


def _take_first_n_words(markdown: str, n: int = 500) -> str:
    if not markdown:
        return ""
    words = markdown.split()
    if len(words) <= n:
        return markdown.strip()
    return (" ".join(words[:n])).strip() + " …"


def _extract_legal_refs(markdown: str) -> tuple[str, ...]:
    if not markdown:
        return ()
    seen: list[str] = []
    for match in _LAW_RE.finditer(markdown):
        ref = match.group(0).strip()
        if ref not in seen:
            seen.append(ref)
    return tuple(seen[:20])


def _format_alternatives(alternatives: Sequence[Mapping[str, Any]]) -> str:
    if not alternatives:
        return "_No hay alternativas del clasificador disponibles._"
    lines: list[str] = []
    for idx, alt in enumerate(alternatives[:3], start=1):
        topic = alt.get("topic_key") or alt.get("topic") or "—"
        subtopic = alt.get("subtopic_key") or alt.get("subtopic") or "—"
        confidence = alt.get("confidence") or alt.get("subtopic_confidence") or 0.0
        try:
            conf_str = f"{float(confidence):.2f}"
        except (TypeError, ValueError):
            conf_str = str(confidence)
        rationale = str(alt.get("rationale") or alt.get("reason") or "").strip()
        line = f"{idx}. **{topic}** / _{subtopic}_ — confianza `{conf_str}`"
        if rationale:
            line += f"\n    - {rationale}"
        lines.append(line)
    return "\n".join(lines)


def _format_neighborhood(
    similar_docs_by_tag: Mapping[str, Sequence[Mapping[str, Any]]]
) -> str:
    if not similar_docs_by_tag:
        return "_No hay vecinos similares disponibles para esta candidatura._"
    blocks: list[str] = []
    for tag, docs in sorted(similar_docs_by_tag.items()):
        if not docs:
            continue
        blocks.append(f"### Candidato: `{tag}`")
        for doc in list(docs)[:3]:
            title = doc.get("first_heading") or doc.get("relative_path") or doc.get("doc_id") or "—"
            score = doc.get("score")
            score_str = f" — score `{float(score):.3f}`" if isinstance(score, (int, float)) else ""
            blocks.append(f"- {title}{score_str}")
    return "\n".join(blocks) if blocks else "_No hay vecinos similares disponibles._"


def _build_deterministic_markdown(
    *,
    doc_row: Mapping[str, Any],
    first_500: str,
    alternatives: Sequence[Mapping[str, Any]],
    similar_docs_by_tag: Mapping[str, Sequence[Mapping[str, Any]]],
    legal_refs: Sequence[str],
) -> str:
    title = _doc_title(doc_row)
    current_topic = doc_row.get("topic") or doc_row.get("tema") or "—"
    current_subtopic = doc_row.get("subtema") or "—"
    current_confidence = doc_row.get("subtopic_confidence")
    try:
        confidence_str = f"{float(current_confidence):.2f}" if current_confidence is not None else "—"
    except (TypeError, ValueError):
        confidence_str = str(current_confidence) if current_confidence else "—"

    legal_refs_block = (
        "\n".join(f"- {ref}" for ref in legal_refs)
        if legal_refs
        else "_Sin referencias legales detectadas._"
    )

    return (
        f"# Brief de revisión de tags\n\n"
        f"## Documento\n"
        f"**Título.** {title}\n\n"
        f"**Tags actuales:** topic = `{current_topic}`, subtopic = `{current_subtopic}`, "
        f"confianza subtopic = `{confidence_str}`\n\n"
        f"## Extracto (primeras ~500 palabras)\n"
        f"> {first_500}\n\n"
        f"## Alternativas del clasificador\n"
        f"{_format_alternatives(alternatives)}\n\n"
        f"## Vecindario semántico\n"
        f"{_format_neighborhood(similar_docs_by_tag)}\n\n"
        f"## Referencias legales detectadas\n"
        f"{legal_refs_block}\n"
    )


_LLM_POLISH_PROMPT = (
    "Eres un asistente editorial. Recibirás un brief Markdown para revisar "
    "los tags de un documento contable colombiano. Mantén TODAS las secciones "
    "(Documento, Extracto, Alternativas del clasificador, Vecindario semántico, "
    "Referencias legales detectadas), todos los bullets y todas las referencias "
    "intactas. Solo puedes mejorar la prosa del párrafo de 'Documento' para que "
    "sea claro y profesional; NO agregues, reformules ni borres datos factuales "
    "de las demás secciones.\n\n"
    "Brief original:\n\n"
)


def _polish_with_llm(markdown: str, llm_adapter: Any) -> tuple[str, bool, str | None]:
    """Optional Markdown polish. Preserves every heading + bullet."""
    if llm_adapter is None:
        return markdown, False, "no_adapter_available"
    try:
        polished = llm_adapter.generate(_LLM_POLISH_PROMPT + markdown)
    except Exception as exc:  # noqa: BLE001 — polish failure is non-fatal
        return markdown, False, f"adapter_error:{exc.__class__.__name__}"
    if not isinstance(polished, str) or not polished.strip():
        return markdown, False, "empty_llm_output"
    # Structural sanity check: all five H2 sections must survive.
    required_headings = (
        "## Documento",
        "## Extracto",
        "## Alternativas del clasificador",
        "## Vecindario semántico",
        "## Referencias legales detectadas",
    )
    for heading in required_headings:
        if heading not in polished:
            return markdown, False, "heading_stripped_by_llm"
    return polished.strip(), True, None


def generate_tag_report(
    doc_row: Mapping[str, Any],
    *,
    report_id: str,
    classifier_alternatives: Sequence[Mapping[str, Any]] | None = None,
    similar_docs_by_tag: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
    llm_adapter: Any = None,
) -> TagReport:
    """Assemble a tag-review brief for a single document."""
    markdown_body = str(doc_row.get("markdown") or doc_row.get("text_preview") or "")
    first_500 = _take_first_n_words(markdown_body, n=500)
    legal_refs = _extract_legal_refs(markdown_body)

    base_markdown = _build_deterministic_markdown(
        doc_row=doc_row,
        first_500=first_500,
        alternatives=classifier_alternatives or (),
        similar_docs_by_tag=similar_docs_by_tag or {},
        legal_refs=legal_refs,
    )
    polished_markdown, polished, skip_reason = _polish_with_llm(
        base_markdown, llm_adapter
    )

    return TagReport(
        report_id=report_id,
        doc_id=str(doc_row.get("doc_id") or ""),
        markdown=polished_markdown,
        first_500_words=first_500,
        legal_references=legal_refs,
        llm_polished=polished,
        skip_reason=skip_reason,
    )


__all__ = ["TagReport", "generate_tag_report"]
