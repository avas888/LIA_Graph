"""fix_v13_may §4 — extend `build_recommendations` with bullets drawn
directly from real `practica_erp` chunks.

The dedicated práctica retrieval lane (`practica/retriever_supabase.py`)
hands us a tuple of `PracticaChunkRuntime`s. Each chunk's `chunk_text`
is already grouped/scored at the retriever; here we extract one
operational-guidance bullet per chunk using the same sentence-trim
helpers the unified support-doc pipeline uses.

Granular by design (per `feedback_granular_edits.md`): one focused
sibling file consumed from `answer_synthesis_sections.build_recommendations`,
not appended to that already-large module.
"""

from __future__ import annotations

import logging
import os
import re
from typing import TYPE_CHECKING

from .answer_shared import append_unique
from .answer_support import (
    _support_doc_candidate_lines,
    clean_support_line_for_answer,
)

if TYPE_CHECKING:
    from ..practica.shared import PracticaChunkRuntime


LOGGER = logging.getLogger(__name__)


# fix_v18 b1 §1.1 Issue A — per-line noise filter gate.
_NOISE_FILTER_ENV_FLAG = "LIA_PRACTICA_NOISE_FILTER"


def _noise_filter_mode() -> str:
    """Return ``off | shadow | enforce``. Default ``shadow`` at landing
    per fix_v18 b1 §1.1 — telemetry without altering output until
    operator promotes after panel review."""
    raw = str(os.getenv(_NOISE_FILTER_ENV_FLAG, "shadow") or "").strip().lower()
    if raw in {"enforce", "on", "1", "true"}:
        return "enforce"
    if raw in {"off", "0", "false", "no", "disabled", "legacy"}:
        return "off"
    return "shadow"


def _trace_step(name: str, **payload: object) -> None:
    """Mirror retriever's best-effort trace emit."""
    try:
        from tracers_and_logs import pipeline_trace as _trace
    except Exception:  # pragma: no cover
        return
    try:
        _trace.step(name, **payload)
    except Exception:  # pragma: no cover
        LOGGER.debug("practica synthesis trace %s failed", name, exc_info=True)


# Sentence-level segmentation: same shape the unified support-doc path
# uses for prose chunks, so the resulting bullet reads like an actual
# operational instruction instead of a wall of text.
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[\.\?!])\s+(?=[A-ZÁÉÍÓÚÑ¿¡])")


# fix_v13_may §6 — post-cleanup artifact filter. The dedicated práctica
# lane is the first to expose certain corpus-build markers that the
# article-derived path never saw. The 21-Q `21q_retriever_Practica`
# panel run identified these specific patterns leaking into the
# rendered Recomendaciones Prácticas section; drop them before they
# reach `build_recommendations`.

# Editorial source-marker line emitted by the corpus build:
# `_Material editorial consolidado el 2026-04-15 desde \`A-1_PATCH-...md\`._`
_PRACTICA_EDITORIAL_MARKER_RE = re.compile(
    r"material\s+editorial\s+consolidado",
    re.IGNORECASE,
)

# Build-time stamp at the head of a chunk: "Hoy es 23 de marzo. Las..."
_PRACTICA_TIME_STAMP_RE = re.compile(
    r"^\s*hoy\s+(?:es|estamos)\b",
    re.IGNORECASE,
)

# Markdown section-heading numerals that slipped through the splitter:
# "### 11.8.1", "8. Errores Frecuentes en PYMEs"
_PRACTICA_SECTION_HEADING_RE = re.compile(
    r"^\s*#{1,6}\s+[\d.]+",
)

# v15.1 (2026-05-14): inline `###` markdown heading markers anywhere in
# the line. Catches chunks where the splitter joined a heading line
# with a sub-heading: `Checklist Pre-Cierre Fiscal — Antes del 31 de
# Diciembre ### 27.1.1.` — the leading text reads plausibly but the
# `### N.N` tail betrays the corpus scaffold.
_PRACTICA_INLINE_MARKDOWN_HEADING_RE = re.compile(
    r"#{2,6}\s+\d+(?:\.\d+)*\.?",
)

# v15.1 (2026-05-14): line starts with a Spanish mid-sentence connector
# — almost always a sign the chunker ate the leading "El 1 " / "En el
# año " / etc. and the surviving fragment opens with a preposition or
# subordinator. Well-formed operational guidance never begins this way.
# Tokens chosen are unambiguous mid-sentence-only words in Spanish.
_PRACTICA_FRAGMENT_LEADER_RE = re.compile(
    r"^(?:de|del|al|que|donde|cuando|mientras|porque|según|sino|aunque|para|por|con|sin|sobre)\s+",
    re.IGNORECASE,
)

# Truncated mid-thought endings (chunk got cut on a conjunction or
# half-word): "aparece cuando.", "según ú.", "donde,"
_PRACTICA_TRUNCATION_TAILS: tuple[str, ...] = (
    " cuando.",
    " donde.",
    " mientras.",
    " porque.",
    " si.",
    " según.",
    " según ú.",
    " del.",
    " de la.",
    " del et.",
    " donde,",
    " cuando,",
    " razones.",  # "La respuesta importa por dos razones."
)

# Trailing dangling-numeral parens like "(7)." or "(24)." — corpus
# footnote refs that lost their target on chunking.
_PRACTICA_DANGLING_PAREN_RE = re.compile(r"\(\s*\d+\s*\)\s*\.?\s*$")

# Question-shaped bullets (a chunk's section title written as ¿...?)
_PRACTICA_QUESTION_BULLET_RE = re.compile(
    r"^\s*¿.*\?\.?\s*$",
)


# fix_v18 b1 §1.1 — per-line noise patterns. These fire on INDIVIDUAL
# bullet candidates (after _support_doc_candidate_lines splits the
# chunk), to drop noise that the chunk-level heuristics in
# `chunk_quality_heuristics.py` cannot catch because the chunk as a
# whole still has substantive content.

# Pre-Ley / temporal contrast lead: line starts with "Antes:", "Antes,",
# "Anteriormente,", "Pre-Ley", "Históricamente,", "Versión anterior:".
# These are the headers of "before-and-after" comparisons; the current
# rule belongs in a SPEC bullet, the "before" half is noise.
_PRACTICA_NOISE_PRE_LEY_LEAD_RE = re.compile(
    r"^\s*(?:antes\s*[:,]|anteriormente\s*[:,]|"
    r"pre[\s\-]?ley|"
    r"hist[oó]ric[ao]mente\s*[:,]|"
    r"versi[oó]n\s+anterior\s*[:,]|"
    r"r[eé]gimen\s+anterior\s*[:,]|"
    r"regla\s+anterior\s*[:,])",
    re.IGNORECASE,
)

# Orphan numeric calculation as the entire bullet body. Example caught
# at the 2026-05-15 PM probe: "Antes: 30 días × ($2.200.000 ÷ 30) =
# $2.200.000." — even without the "Antes:" lead, the pure-calculation
# shape is a worked-example fragment that lost its caller question.
_PRACTICA_NOISE_ORPHAN_CALC_RE = re.compile(
    r"\d[\d.,]*\s*(?:d[ií]as?|meses?|a[nñ]os?)?\s*"
    r"(?:×|÷|x|\*|/)\s*"
    r"\(?\s*\$?\d[\d.,]*\s*"
    r"(?:×|÷|x|\*|/|\)|\.)",
    re.IGNORECASE,
)

# DSPNE / PILA software codes referenced as standalone bullets:
# "Despido sin justa causa (...): código 55." Pattern: bullet ends with
# ": código <NN>." or "código <NN>." dominates a short bullet.
_PRACTICA_NOISE_SOFTWARE_CODE_RE = re.compile(
    r":\s*c[oó]d(?:igo|\.)\s+\d{1,3}\s*\.?\s*$",
    re.IGNORECASE,
)


def _is_practica_noise_line(line: str) -> tuple[bool, str | None]:
    """Return ``(is_noise, reason)``.

    fix_v18 b1 §1.1 Issue A — per-line noise filter for práctica
    chunks. Returns ``(False, None)`` for clean lines and
    ``(True, "<reason>")`` for noise. The CALLER decides whether to
    drop or shadow-log based on ``_noise_filter_mode()``.
    """
    if not line:
        return False, None
    stripped = str(line).strip()
    if not stripped:
        return False, None
    if _PRACTICA_NOISE_PRE_LEY_LEAD_RE.match(stripped):
        return True, "pre_ley_lead"
    if _PRACTICA_NOISE_SOFTWARE_CODE_RE.search(stripped):
        return True, "software_code_tail"
    if _PRACTICA_NOISE_ORPHAN_CALC_RE.search(stripped) and len(stripped) <= 160:
        return True, "orphan_numeric_calc"
    return False, None


def _is_practica_artifact_line(line: str) -> bool:
    """Return True for lines we want to drop from práctica bullets.

    These patterns are corpus-build artifacts that don't read as
    operational guidance to an accountant: editorial source markers,
    time stamps from chunk generation, section-heading numerals that
    slipped through markdown splitting, truncated mid-thought endings,
    dangling footnote-ref parens, and question-shaped section titles.

    The unified article-guidance path never surfaces these (article
    `guidance.recommendation` fields are curated lists), so this
    filter is specific to the new práctica retrieval lane.
    """
    if not line:
        return True
    stripped = str(line).strip()
    if not stripped:
        return True
    if _PRACTICA_EDITORIAL_MARKER_RE.search(stripped):
        return True
    if _PRACTICA_TIME_STAMP_RE.search(stripped):
        return True
    if _PRACTICA_SECTION_HEADING_RE.search(stripped):
        return True
    if _PRACTICA_INLINE_MARKDOWN_HEADING_RE.search(stripped):
        return True
    if _PRACTICA_FRAGMENT_LEADER_RE.match(stripped):
        return True
    if _PRACTICA_QUESTION_BULLET_RE.match(stripped):
        return True
    if _PRACTICA_DANGLING_PAREN_RE.search(stripped):
        return True
    lowered = stripped.lower()
    if any(lowered.endswith(tail) for tail in _PRACTICA_TRUNCATION_TAILS):
        return True
    return False


def _candidate_lines_from_chunk(chunk: "PracticaChunkRuntime") -> tuple[str, ...]:
    """Pull one or more candidate bullets from a single chunk.

    Strategy:
      1. Try the existing markdown-aware splitter on the full chunk text
         (catches `- ...` bullet lists and short paragraphs the chunk
         already wrote in a usable shape).
      2. If that yields nothing usable, fall back to sentence-level
         segmentation and run each sentence through `clean_support_line_for_answer`.
    """
    text = str(getattr(chunk, "chunk_text", "") or "").strip()
    if not text:
        return ()

    candidates = [
        line
        for line in _support_doc_candidate_lines(text)
        if not _is_practica_artifact_line(line)
    ]
    if candidates:
        return tuple(candidates)

    sentences: list[str] = []
    for sentence in _SENTENCE_SPLIT_RE.split(text):
        cleaned = clean_support_line_for_answer(sentence)
        if not cleaned or _is_practica_artifact_line(cleaned):
            continue
        if 35 <= len(cleaned) <= 260:
            sentences.append(cleaned)
        if len(sentences) >= 3:
            break
    return tuple(sentences)


def extend_from_practica_chunks(
    bucket: list[str],
    chunks: tuple["PracticaChunkRuntime", ...],
    *,
    max_bullets_per_chunk: int = 6,
) -> None:
    """Append bullets from each práctica chunk to `bucket` (de-duped).

    v15.1 (2026-05-14): caps on Recomendaciones Prácticas lifted per
    operator directive — the section can run as long as the chunk
    content warrants. Per-chunk default raised from 1 to 6 so every
    reserved `practica_erp` chunk can surface its full operational
    detail; `build_recommendations` no longer truncates the merged
    list.
    """
    if not chunks:
        _trace_step(
            "practica.synthesis.extend",
            status="noop",
            chunk_count=0,
            bullets_emitted=0,
        )
        return
    noise_mode = _noise_filter_mode()
    noise_dropped_reasons: dict[str, int] = {}
    noise_shadow_reasons: dict[str, int] = {}
    per_chunk_emitted: list[dict[str, object]] = []
    bucket_size_before = len(bucket)
    for chunk in chunks:
        candidates = _candidate_lines_from_chunk(chunk)
        emitted_lines: list[str] = []
        emitted = 0
        for line in candidates:
            cleaned = clean_support_line_for_answer(line)
            if not cleaned:
                continue
            # Belt-and-suspenders: catch the rare case where the
            # markdown-splitter at `_candidate_lines_from_chunk` let
            # something through that only `clean_support_line_for_answer`
            # could shape into the artifact signature (e.g., trailing
            # period appended to a `cuando` mid-thought).
            if _is_practica_artifact_line(cleaned):
                continue
            # fix_v18 b1 §1.1 Issue A — noise filter (shadow/enforce).
            is_noise, noise_reason = _is_practica_noise_line(cleaned)
            if is_noise:
                if noise_mode == "enforce":
                    noise_dropped_reasons[noise_reason or "unknown"] = (
                        noise_dropped_reasons.get(noise_reason or "unknown", 0) + 1
                    )
                    continue
                if noise_mode == "shadow":
                    noise_shadow_reasons[noise_reason or "unknown"] = (
                        noise_shadow_reasons.get(noise_reason or "unknown", 0) + 1
                    )
            append_unique(bucket, cleaned)
            emitted += 1
            emitted_lines.append(cleaned[:120])
            if emitted >= max_bullets_per_chunk:
                break
        per_chunk_emitted.append(
            {
                "doc_id": str(getattr(chunk, "doc_id", "")),
                "authority": str(getattr(chunk, "authority", "")),
                "candidates_found": len(candidates),
                "bullets_emitted": emitted,
                "first_bullet_preview": emitted_lines[0] if emitted_lines else None,
            }
        )
    total_emitted = len(bucket) - bucket_size_before
    LOGGER.info(
        "practica.synthesis.extend chunks=%d bullets_emitted=%d",
        len(chunks),
        total_emitted,
    )
    _trace_step(
        "practica.synthesis.extend",
        status="ok",
        chunk_count=len(chunks),
        bullets_emitted=total_emitted,
        per_chunk=per_chunk_emitted,
    )
    # fix_v18 b1 §1.1 Issue A — emit noise-filter outcome separately so
    # the dev:staging shadow run can be queried via `jq` against
    # `tracers_and_logs/logs/pipeline_trace.jsonl` to count drop/shadow
    # rates and reasons before promoting to enforce.
    noise_outcome: str
    if noise_mode == "off":
        noise_outcome = "noop"
    elif noise_mode == "enforce" and noise_dropped_reasons:
        noise_outcome = "suppressed"
    elif noise_mode == "shadow" and noise_shadow_reasons:
        noise_outcome = "shadow_hit"
    else:
        noise_outcome = "pass"
    _trace_step(
        "practica.noise_filter.applied",
        filter_mode=noise_mode,
        outcome=noise_outcome,
        dropped_total=sum(noise_dropped_reasons.values()),
        dropped_reasons=dict(noise_dropped_reasons),
        shadow_total=sum(noise_shadow_reasons.values()),
        shadow_reasons=dict(noise_shadow_reasons),
    )


def filter_practica_chunks_by_topic(
    chunks: tuple["PracticaChunkRuntime", ...],
    allowed_topics: frozenset[str] | set[str] | None,
) -> tuple[tuple["PracticaChunkRuntime", ...], dict]:
    """fix_v25_may.md P13 — drop práctica chunks whose ``topic_key`` is not
    in ``allowed_topics``.

    Chunks with no topic_key (``None`` / empty string) are kept — we don't
    want to penalize gaps in tagging. When ``allowed_topics`` is None or
    empty, the function is a no-op.

    Returns ``(kept_chunks, diag)``.
    """
    diag = {
        "chunks_in": len(chunks),
        "chunks_kept": len(chunks),
        "chunks_dropped": 0,
        "dropped_topics": [],
    }
    if not chunks or not allowed_topics:
        return chunks, diag
    allowed = set(allowed_topics)
    kept: list = []
    dropped_topics: dict[str, int] = {}
    for chunk in chunks:
        tk = (getattr(chunk, "topic_key", None) or "").strip()
        if not tk or tk in allowed:
            kept.append(chunk)
            continue
        dropped_topics[tk] = dropped_topics.get(tk, 0) + 1
    diag["chunks_kept"] = len(kept)
    diag["chunks_dropped"] = len(chunks) - len(kept)
    diag["dropped_topics"] = [
        {"topic": t, "count": c} for t, c in sorted(dropped_topics.items(), key=lambda x: -x[1])
    ]
    return tuple(kept), diag


__all__ = [
    "extend_from_practica_chunks",
    "filter_practica_chunks_by_topic",
    "_is_practica_artifact_line",
    "_is_practica_noise_line",
    "_noise_filter_mode",
]
