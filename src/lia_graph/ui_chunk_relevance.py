"""Relevance scoring, summary-sentence picking, and chunk selection.

Extracted from `ui_text_utilities.py` during granularize-v2 (2026-04-20)
because the host module was 1525 LOC of mixed concerns and this cluster has
a single clear identity: **given a user question and a pile of retrieved
chunks, turn that into (a) a ranked / diversified chunk list and (b) a
short, citation-aware summary of the most relevant sentences.**

Inputs a caller typically hands in:
  * `question_context` / `citation_context` (free-form user strings)
  * `chunks`: list of dicts with `text`, `heading`, `signature`, and
    metadata flags (`is_exercise_chunk`, `has_money_example`,
    `is_reference_dense`, `intent_tags`)

Outputs:
  * `query_profile` = `{q_tokens, cq_tokens, intent_tags, need_examples}`
  * scored rows, diverse chunk selection, trimmed summary sentences,
    first substantive sentence for expert excerpts.

Scope carefully: Spanish-aware sentence splitting (protects citation
abbreviations like `art.` / `núm.` from premature sentence breaks) lives
here because it is only ever called from the relevance pipeline. If a
second consumer shows up, promote the splitter to a shared module, but do
not scatter it by copy/paste.

Cross-module dependencies are kept minimal:
  * `_clean_markdown_inline` and `_clip_session_content` are imported from
    `ui_text_utilities` (no cycle: that module does not import from here)
  * `_SOURCE_METADATA_LINE_RE` and `_EXPERT_SUMMARY_SKIP_EXACT` are still
    resolved via the `_ui()` lazy accessor to avoid pulling in the
    `ui_server` module eagerly.
"""

from __future__ import annotations

import re
from typing import Any


_SUMMARY_STOPWORDS = {
    "de", "la", "el", "los", "las",
    "un", "una", "unos", "unas",
    "y", "o", "u",
    "en", "con", "sin", "por", "para",
    "a", "al", "del",
    "que", "se", "su", "sus",
    "es", "son", "como", "sobre",
    "este", "esta", "estos", "estas", "ser",
    "si", "no", "lo", "le", "les", "ya",
    "más", "mas", "muy",
    "tu", "tú", "mi", "me", "te", "e",
}

_SUMMARY_INTENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "procedimiento": (
        "paso", "pasos", "procedimiento", "proceso", "tramite", "trámite",
        "como", "cómo", "presentar", "declaracion", "declaración", "diligenciar",
    ),
    "requisitos": (
        "requisito", "requisitos", "condicion", "condición", "soporte",
        "documento", "evidencia", "obligatorio", "obligatoria",
        "causalidad", "proporcionalidad", "necesidad",
    ),
    "riesgos": (
        "riesgo", "sancion", "sanción", "rechazo", "contingencia",
        "incumplimiento", "error", "multa",
    ),
    "plazos": (
        "plazo", "plazos", "fecha", "fechas", "vencimiento", "vencimientos",
        "calendario", "cuando", "cuándo",
    ),
    "ejemplos": (
        "ejemplo", "ejemplos", "caso", "casos", "simulacion", "simulación",
        "escenario", "escenarios",
    ),
}

_SENTENCE_ABBREVIATION_RE = re.compile(
    r"\b(art|arts|num|n[úu]m|no|lit|inc|par)\.(\s+(?=[0-9a-záéíóúñ]))",
    re.IGNORECASE,
)
_SENTENCE_ABBR_PLACEHOLDER = "§§DOT§§"
_CITATION_TAIL_RE = re.compile(r"\b(art|arts|num|n[úu]m|no|lit|inc|par|rad)\.$", re.IGNORECASE)
_CITATION_HEAD_RE = re.compile(r"^\s*(\d+|[ivxlcdm]+)\b", re.IGNORECASE)


def _ui() -> Any:
    """Lazy accessor for `lia_graph.ui_server` (avoids circular import)."""
    from . import ui_server as _mod
    return _mod


def _extract_candidate_paragraphs(text: str, *, max_items: int = 6) -> list[str]:
    # Imported lazily to avoid a circular import at module load: ui_text_utilities
    # itself stays independent of this module.
    from .ui_text_utilities import _clean_markdown_inline

    paragraphs: list[str] = []
    seen: set[str] = set()
    for block in re.split(r"\n{2,}", str(text or "")):
        clean = _clean_markdown_inline(block)
        if len(clean) < 45:
            continue
        if _ui()._SOURCE_METADATA_LINE_RE.match(clean):
            continue
        key = clean.lower()
        if key in seen:
            continue
        seen.add(key)
        paragraphs.append(clean)
        if len(paragraphs) >= max_items:
            break
    return paragraphs


def _sanitize_question_context(text: str, *, max_chars: int = 320) -> str:
    clean = re.sub(r"\s+", " ", str(text or "")).strip()
    if not clean:
        return ""
    return clean[:max_chars].strip()


def _tokenize_relevance_text(text: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9áéíóúñü]{2,}", str(text or "").lower())
    return [token for token in tokens if token not in _SUMMARY_STOPWORDS]


def _detect_intent_tags(text: str) -> set[str]:
    lower = str(text or "").lower()
    tags: set[str] = set()
    for tag, keywords in _SUMMARY_INTENT_KEYWORDS.items():
        if any(keyword in lower for keyword in keywords):
            tags.add(tag)
    return tags


def _score_chunk_relevance(
    chunk: dict[str, Any],
    *,
    query_profile: dict[str, Any],
) -> dict[str, Any]:
    q_tokens = list(query_profile.get("q_tokens") or [])
    cq_tokens = list(query_profile.get("cq_tokens") or [])
    intent_tags = set(str(tag) for tag in (query_profile.get("intent_tags") or []))
    need_examples = bool(query_profile.get("need_examples"))
    if not q_tokens and not cq_tokens and not intent_tags:
        return {"score": 0.0, "intent_overlap": 0}

    heading_tokens = set(_tokenize_relevance_text(chunk.get("heading", "")))
    body_tokens = _tokenize_relevance_text(chunk.get("text", ""))
    if not body_tokens and not heading_tokens:
        return {"score": 0.0, "intent_overlap": 0}

    body_counts: dict[str, int] = {}
    for token in body_tokens:
        body_counts[token] = body_counts.get(token, 0) + 1
    body_set = set(body_tokens)

    score = 0.0
    for token in q_tokens:
        if token in heading_tokens:
            score += 2.9
        if token in body_set:
            score += 1.75
            repeats = max(0, body_counts.get(token, 1) - 1)
            score += min(repeats, 2) * 0.28
    for token in cq_tokens:
        if token in heading_tokens:
            score += 2.35
        if token in body_set:
            score += 1.45
            repeats = max(0, body_counts.get(token, 1) - 1)
            score += min(repeats, 2) * 0.2

    chunk_intents = set(str(tag) for tag in (chunk.get("intent_tags") or []))
    intent_overlap = len(intent_tags.intersection(chunk_intents))
    score += intent_overlap * 1.25
    if chunk.get("heading"):
        score += 0.15

    penalty = 0.0
    if bool(chunk.get("is_exercise_chunk")) and not need_examples:
        penalty += 2.6
    if bool(chunk.get("has_money_example")) and not need_examples:
        penalty += 1.35
    if bool(chunk.get("is_reference_dense")):
        penalty += 0.9
        if "procedimiento" in intent_tags:
            penalty += 0.45
    score -= penalty

    return {
        "score": score,
        "intent_overlap": intent_overlap,
    }


def _looks_like_reference_list(sentence: str) -> bool:
    lower = str(sentence or "").lower()
    references = len(
        re.findall(
            r"\bart\.?\b|\bley\b|\bdecreto\b|\bresoluci[oó]n\b|\bconcepto\b|\bradicado\b",
            lower,
        )
    )
    return references >= 4 and len(lower) >= 120


def _split_sentences(text: str) -> list[str]:
    from .ui_text_utilities import _clip_session_content

    clean = re.sub(r"\s+", " ", str(text or "")).strip()
    if not clean:
        return []
    protected = _SENTENCE_ABBREVIATION_RE.sub(
        lambda match: f"{match.group(1)}{_SENTENCE_ABBR_PLACEHOLDER}{match.group(2)}",
        clean,
    )
    sentences = re.split(r"(?<=[\.\!\?])\s+", protected)
    merged_sentences: list[str] = []
    for sentence in sentences:
        restored = sentence.replace(_SENTENCE_ABBR_PLACEHOLDER, ".").strip()
        if not restored:
            continue
        if merged_sentences:
            previous = merged_sentences[-1].strip()
            prev_lower = previous.lower()
            current_lower = restored.lower()
            should_merge = bool(_CITATION_TAIL_RE.search(prev_lower))
            if not should_merge and prev_lower.endswith(("ley", "decreto", "resolución", "resolucion", "concepto")):
                should_merge = bool(_CITATION_HEAD_RE.match(current_lower))
            if should_merge:
                merged_sentences[-1] = f"{previous} {restored}".strip()
                continue
        merged_sentences.append(restored)

    kept: list[str] = []
    for sentence in merged_sentences:
        value = sentence.strip()
        if len(value) < 35:
            continue
        if _looks_like_reference_list(value):
            continue
        kept.append(_clip_session_content(value, max_chars=220))
    return kept


def _pick_summary_sentences(
    chunks: list[dict[str, Any]],
    *,
    query_profile: dict[str, Any],
    max_items: int = 4,
) -> list[str]:
    need_examples = bool(query_profile.get("need_examples"))
    kept: list[str] = []
    seen: set[str] = set()
    for chunk in chunks:
        if (chunk.get("is_exercise_chunk") or chunk.get("has_money_example")) and not need_examples:
            continue
        for sentence in _split_sentences(chunk.get("text", "")):
            key = sentence.lower()
            if key in seen:
                continue
            seen.add(key)
            kept.append(sentence)
            if len(kept) >= max_items:
                return kept
    return kept


def _select_diverse_chunks(
    *,
    scored_rows: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
    max_items: int = 4,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen_signatures: set[str] = set()
    seen_headings: set[str] = set()
    ranked = sorted(scored_rows, key=lambda item: (-float(item.get("score", 0.0)), int(item.get("index", 0))))
    for row in ranked:
        chunk = row.get("chunk")
        if not isinstance(chunk, dict):
            continue
        signature = str(chunk.get("signature", "")).strip()
        heading_key = str(chunk.get("heading", "")).strip().lower()
        score = float(row.get("score", 0.0))
        if signature and signature in seen_signatures:
            continue
        if heading_key and heading_key in seen_headings and score <= 0.0:
            continue
        if score <= 0.0 and len(selected) >= 2:
            continue
        selected.append(chunk)
        if signature:
            seen_signatures.add(signature)
        if heading_key:
            seen_headings.add(heading_key)
        if len(selected) >= max_items:
            break

    if len(selected) < 2:
        for chunk in chunks:
            if chunk in selected:
                continue
            selected.append(chunk)
            if len(selected) >= 2:
                break
    return selected


def _first_substantive_sentence(text: str) -> str:
    sentences = [item.strip() for item in _split_sentences(text) if item.strip()]
    for sentence in sentences:
        if len(sentence) < 32:
            continue
        if sentence.lower() in _ui()._EXPERT_SUMMARY_SKIP_EXACT:
            continue
        return sentence
    return sentences[0] if sentences else ""


def _flatten_markdown_to_text(text: str, *, max_chars: int = 5000) -> str:
    from .ui_text_utilities import _clean_markdown_inline

    raw = str(text or "")[:max_chars]
    if not raw:
        return ""
    lines = [_clean_markdown_inline(line) for line in raw.splitlines()]
    merged = re.sub(r"\s+", " ", " ".join(line for line in lines if line)).strip()
    return merged
