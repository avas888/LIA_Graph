"""fix_v14_may §4 (A2) — chunk-quality heuristics on the unified bullet
pipeline.

Extends the práctica-specific filter (fix_v13 §6,
`answer_synthesis_practica._is_practica_artifact_line`) into a shared
module applied to the raw `chunk_rows` returned by `_hybrid_search`
BEFORE `_classify_article_rows` collapses them into the evidence
bundle. Multiplies each row's `rrf_score` by a penalty in `[0.1, 1.0]`
and attaches a `chunk_quality_demotion_reason` for trace visibility.

Targets the off-topic chunk-text leak pattern observed in 10+/42 turns
of the 2026-05-13 panel-judge:

* portal-login boilerplate: `"Inicie sesión con su número de cédula y
  contraseña…"` — leaked into GMF marcación, PT umbrales, autorretención
* cross-topic operational fragments: `"Matrícula Mercantil
  (Renovación) — Vence: 31 de marzo"` (calendario, retención F.350),
  `"Jornada nocturna … 35%"` (PILA, tabla 383, UGPP)
* chunk captions: `"Caso de estudio:"`, `"Texto normativo clave —"`,
  `"… (fragmento relevante)"`
* section-numeral headings: `"### 11.8.1"` alone
* question-as-bullet echoes: bullets that are pure interrogatives

Each pattern is a regex with an explicit reason string. Mode is
controlled by `LIA_CHUNK_QUALITY_HEURISTIC_MODE ∈ {off, shadow,
enforce}`. Default `shadow` at landing — emits diagnostics but does
NOT alter ranking. Floor at 0.1 per Invariant I5 (never penalize to
zero).
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any


LOGGER = logging.getLogger(__name__)


_GATE_ENV_FLAG = "LIA_CHUNK_QUALITY_HEURISTIC_MODE"


def heuristic_mode() -> str:
    """Return the gate mode. Default ``shadow`` at landing — emit
    diagnostics, do NOT alter ranking. Promote to ``enforce`` only
    after panel-judge confirms INCLUDE per fix_v14_may §4."""
    raw = str(os.getenv(_GATE_ENV_FLAG, "shadow") or "").strip().lower()
    if raw in {"enforce", "on", "1", "true"}:
        return "enforce"
    if raw in {"off", "0", "false", "no", "disabled"}:
        return "off"
    return "shadow"


# Penalty factors per pattern class. All ≥ 0.1 (Invariant I5: never
# penalize to zero so a chunk can still surface if it's the only
# candidate the retriever found).
PENALTY_HEAVY = 0.2   # portal-login boilerplate, pure captions
PENALTY_MEDIUM = 0.4  # cross-topic operational leaks
PENALTY_LIGHT = 0.6   # section-numeral headings, question-as-bullet


# --- Pattern catalog (verbatim from 2026-05-13 panel-judge) -----------

# Portal-login boilerplate — leaks into ANY topic when the corpus
# chunk happens to mention authentication steps.
_PORTAL_LOGIN_RE = re.compile(
    r"inicie\s+sesi[oó]n\s+con\s+su?\s+(?:n[uú]mero\s+de\s+)?c[eé]dula",
    re.IGNORECASE,
)

# Chunk caption shape that should never read as guidance:
# "Texto normativo clave — par. N, art. M ET (fragmento relevante)"
_NORMATIVE_KEY_CAPTION_RE = re.compile(
    r"texto\s+normativo\s+clave\s*[—\-:]",
    re.IGNORECASE,
)

# Caption "(fragmento relevante)" / "(fragmento)" anywhere
_FRAGMENT_CAPTION_RE = re.compile(
    r"\(\s*fragmento(?:\s+relevante)?\s*\)",
    re.IGNORECASE,
)

# Case-study chunk caption: "Caso de estudio: Tienda de abarrotes..."
_CASE_STUDY_RE = re.compile(
    r"^\s*caso\s+de\s+estudio\s*:",
    re.IGNORECASE,
)

# Cross-topic operational leak — "Matrícula Mercantil (Renovación)..."
# bleeds into calendario, retención. The string ALONE is the trigger;
# its appearance outside `comercial_societario` is what we penalize.
_MATRICULA_MERCANTIL_RE = re.compile(
    r"matr[ií]cula\s+mercantil",
    re.IGNORECASE,
)

# Jornada nocturna recargo 35% — Ley 2466 content; leaks into PILA,
# tabla 383, UGPP when those questions don't actually need it. Windows
# widened: in real chunk_text the elements can be separated by full
# sentences (e.g. "comienza a las 7:00 p.m. y se extiende hasta las
# 6:00 a.m. Todo trabajo en este horario genera un recargo del 35%").
_JORNADA_NOCTURNA_LEAK_RE = re.compile(
    r"jornada\s+nocturna.{0,200}?(?:recargo|35\s*%)",
    re.IGNORECASE | re.DOTALL,
)

# Markdown section-heading numeral alone: "### 11.8.1" or "### 6.9
# Resumen" or "## 8. Errores Frecuentes" — when these are the dominant
# content of a chunk, the chunk is a heading not guidance.
_SECTION_HEADING_NUMERAL_RE = re.compile(
    r"^\s*#{1,6}\s+\d+(?:[.\-]\d+)*",
    re.MULTILINE,
)

# Bullet-or-paragraph that is itself a question echo (`¿…?`). When the
# chunk_text is dominated by interrogatives, it's a section index
# pretending to be content.
_QUESTION_DOMINANT_RE = re.compile(
    r"¿[^?]{10,200}\?",
)


# Cross-topic markers — keyed by trigger pattern → list of topics for
# which the trigger is LEGITIMATE. Outside those topics, the trigger
# is treated as cross-topic leak and gets PENALTY_MEDIUM.
_CROSS_TOPIC_LEAK_RULES: tuple[tuple[re.Pattern[str], frozenset[str]], ...] = (
    (
        _MATRICULA_MERCANTIL_RE,
        frozenset({"comercial_societario", "rut_y_responsabilidades_tributarias"}),
    ),
    (
        _JORNADA_NOCTURNA_LEAK_RE,
        frozenset({"laboral", "reforma_laboral_ley_2466", "parafiscales_seguridad_social"}),
    ),
)


def score_chunk_quality(
    row: dict[str, Any],
    *,
    routed_topic: str | None = None,
) -> tuple[float, str | None]:
    """Score the chunk for quality artifacts.

    Returns ``(penalty_factor, reason)`` where:
      * ``penalty_factor`` ∈ ``[0.1, 1.0]`` (1.0 = no demotion).
      * ``reason`` is the human-readable trigger key, or ``None`` if
        the chunk is clean.

    The CALLER multiplies the row's ``rrf_score`` by ``penalty_factor``
    and stores ``reason`` in ``chunk_quality_demotion_reason`` for
    trace visibility. The function itself does NOT mutate the row.
    """
    text = str(row.get("chunk_text") or "").strip()
    if not text:
        # Empty chunk should already have been filtered earlier; defensive
        # passthrough.
        return 1.0, None

    # Heavy penalties first — these patterns are unambiguous artifacts.
    if _PORTAL_LOGIN_RE.search(text):
        return PENALTY_HEAVY, "portal_login_boilerplate"
    if _NORMATIVE_KEY_CAPTION_RE.search(text):
        # Only penalize if the caption DOMINATES the chunk (short text
        # whose primary substance is the caption itself).
        if len(text) < 200:
            return PENALTY_HEAVY, "normative_key_caption"
    if _FRAGMENT_CAPTION_RE.search(text) and len(text) < 200:
        return PENALTY_HEAVY, "fragmento_relevante_caption"
    if _CASE_STUDY_RE.match(text):
        return PENALTY_HEAVY, "case_study_caption"

    # Cross-topic operational leaks — only when the routed topic is
    # NOT the trigger's natural home.
    if routed_topic:
        for pattern, allowed_topics in _CROSS_TOPIC_LEAK_RULES:
            if pattern.search(text) and routed_topic not in allowed_topics:
                return PENALTY_MEDIUM, "cross_topic_operational_leak"

    # Section-numeral headings as dominant content.
    heading_matches = _SECTION_HEADING_NUMERAL_RE.findall(text)
    # A chunk dominated by section headings is one where heading lines
    # make up a large fraction of the lines.
    if heading_matches:
        total_lines = max(1, text.count("\n") + 1)
        if len(heading_matches) / total_lines >= 0.5 and len(text) < 400:
            return PENALTY_LIGHT, "section_heading_dominant"

    # Question-dominant text — when > 50 % of the substance is `¿…?`
    # echoes of section subtitles.
    q_matches = _QUESTION_DOMINANT_RE.findall(text)
    if q_matches and len(text) < 400:
        q_chars = sum(len(m) for m in q_matches)
        if q_chars / max(1, len(text)) >= 0.5:
            return PENALTY_LIGHT, "question_dominant_caption"

    return 1.0, None


def apply_heuristics(
    chunk_rows: list[dict[str, Any]],
    *,
    routed_topic: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Apply the heuristics across a list of chunk rows.

    Returns ``(annotated_rows, diagnostics_dict)``. Each row in
    ``annotated_rows`` is a copy with:
      * ``rrf_score`` multiplied by the penalty (in enforce mode only).
      * ``chunk_quality_demotion_reason`` set to the trigger string
        when a penalty fired (in shadow mode too — visibility).

    The mode (``off | shadow | enforce``) is read from the environment.
    In ``shadow`` mode the diagnostic is recorded but ``rrf_score`` is
    unchanged. In ``off`` mode the function is a noop and returns the
    input rows unmodified.
    """
    mode = heuristic_mode()
    diag: dict[str, Any] = {
        "gate_mode": mode,
        "rows_seen": len(chunk_rows),
        "rows_demoted": 0,
        "reasons": {},
        "samples": [],
    }
    if mode == "off" or not chunk_rows:
        return list(chunk_rows), diag

    annotated: list[dict[str, Any]] = []
    reason_counts: dict[str, int] = {}
    sample: list[dict[str, Any]] = []
    for row in chunk_rows:
        if not isinstance(row, dict):
            annotated.append(row)
            continue
        penalty, reason = score_chunk_quality(row, routed_topic=routed_topic)
        if reason is None:
            annotated.append(row)
            continue
        # Always attach the diagnostic; only mutate score in enforce.
        new_row = dict(row)
        new_row["chunk_quality_demotion_reason"] = reason
        if mode == "enforce":
            try:
                base = float(new_row.get("rrf_score") or new_row.get("fts_rank") or 0.0)
                new_row["rrf_score"] = max(0.0, base * penalty)
            except (TypeError, ValueError):
                pass
        annotated.append(new_row)
        diag["rows_demoted"] += 1
        reason_counts[reason] = reason_counts.get(reason, 0) + 1
        if len(sample) < 6:
            sample.append({
                "chunk_id": str(new_row.get("chunk_id") or "")[:80],
                "doc_id": str(new_row.get("doc_id") or "")[:80],
                "reason": reason,
                "penalty": round(penalty, 3),
                "text_preview": (str(new_row.get("chunk_text") or "")[:120]),
            })
    diag["reasons"] = reason_counts
    diag["samples"] = sample

    if mode != "off" and diag["rows_demoted"]:
        LOGGER.info(
            "chunk_quality_heuristics mode=%s seen=%d demoted=%d reasons=%s",
            mode,
            diag["rows_seen"],
            diag["rows_demoted"],
            sorted(reason_counts.items(), key=lambda kv: -kv[1]),
        )
    return annotated, diag


__all__ = [
    "apply_heuristics",
    "heuristic_mode",
    "score_chunk_quality",
]
