"""next_v4 §5 — comparative-regime planner mode synthesis.

Triggered when the user asks how a regime changed across a temporal cutoff
(e.g. "¿cuánto cambia si parte del saldo es pre-2017?", "¿qué cambió con
la reforma X?"). Today such follow-ups land as generic ``article_lookup``
plans and the synthesis tries to merge two regimes into one prose block —
the comparative structure dissolves and the contador gets an evasive
"yes it changes, validate the transition regime" non-answer.

This module:

* Loads ``config/comparative_regime_pairs.json`` (one entry per
  domain × cutoff_year, see the file's ``_doc`` field for schema).
* Detects the comparative cue + matches a regime pair against the
  conversation's normative anchors.
* Renders a side-by-side markdown table + verdict line + action line +
  curated risk/support sections — exactly the shape a senior contador
  uses when explaining a pre/post-reform difference.

The composer is wired in ``answer_assembly.compose_main_chat_answer``
when the planner emits ``query_mode == "comparative_regime_chain"``.
"""

from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from ..pipeline_c.contracts import PipelineCRequest


_CONFIG_PATH_ENV = "LIA_COMPARATIVE_REGIME_CONFIG"

# Lexical cues. The numeric form ("antes de 2017", "pre-2017", "anterior
# a 2017") captures the cutoff year directly; the keyword-only form
# ("régimen de transición", "viene de antes") matches but leaves the
# year to be derived from conversation_context or config defaults.
_COMPARATIVE_CUE_NUMERIC_RX = re.compile(
    r"\b(?:antes\s+de|anterior\s+a|pre\s*-?\s*)\s*(\d{4})\b",
    re.IGNORECASE,
)
_COMPARATIVE_KEYWORDS: tuple[str, ...] = (
    "qué cambió con la reforma",
    "que cambio con la reforma",
    "régimen de transición",
    "regimen de transicion",
    "régimen anterior",
    "regimen anterior",
    "viene de antes",
    "saldo viene de",
    "antes y después de la reforma",
    "antes y despues de la reforma",
    "antes de la reforma",
    "cambio con la reforma",
)


def _default_config_path() -> Path:
    override = os.getenv(_CONFIG_PATH_ENV)
    if override:
        return Path(override)
    return Path("config/comparative_regime_pairs.json")


@lru_cache(maxsize=4)
def load_config(path: str | None = None) -> dict[str, Any]:
    target = Path(path) if path else _default_config_path()
    if not target.exists():
        return {"version": "none", "pairs": {}}
    return json.loads(target.read_text(encoding="utf-8"))


def detect_comparative_regime_cue(message: str) -> tuple[bool, int | None]:
    """Return ``(matched, cutoff_year)`` for a comparative-regime query.

    ``cutoff_year`` is filled when the message itself mentions a year
    ("pre-2017", "antes de 2022"). Keyword-only matches return
    ``(True, None)`` and the caller is expected to recover the cutoff
    from ``conversation_context`` or fall back to the matched pair's
    config-declared ``cutoff_year``.
    """
    text = (message or "").strip().lower()
    if not text:
        return False, None
    numeric_match = _COMPARATIVE_CUE_NUMERIC_RX.search(text)
    if numeric_match:
        try:
            return True, int(numeric_match.group(1))
        except ValueError:
            pass
    for keyword in _COMPARATIVE_KEYWORDS:
        if keyword in text:
            return True, None
    return False, None


def _conversation_anchors_blob(state: object) -> str:
    if not isinstance(state, dict):
        return ""
    raw = state.get("normative_anchors") or []
    if not isinstance(raw, (list, tuple)):
        return ""
    return " ".join(str(a) for a in raw if isinstance(a, str)).lower()


def match_regime_pair_for_request(
    request: PipelineCRequest,
    *,
    config_path: str | None = None,
) -> dict[str, Any] | None:
    """Return the regime-pair dict that best fits the request, or ``None``.

    Match is positive when (a) the message carries a comparative cue, AND
    (b) at least one of the candidate pair's ``trigger_anchors`` appears
    either in ``conversation_state.normative_anchors`` or in the message
    itself.
    """
    matched, cutoff_year = detect_comparative_regime_cue(request.message or "")
    if not matched:
        return None

    anchors_blob = _conversation_anchors_blob(request.conversation_state)
    message_blob = (request.message or "").lower()
    context_blob = (request.conversation_context or "").lower()

    if cutoff_year is None:
        # The keyword-only path: try the conversation_context for a year.
        ctx_year_match = _COMPARATIVE_CUE_NUMERIC_RX.search(context_blob)
        if ctx_year_match:
            try:
                cutoff_year = int(ctx_year_match.group(1))
            except ValueError:
                cutoff_year = None

    config = load_config(config_path)
    pairs = config.get("pairs") or {}
    if not isinstance(pairs, dict):
        return None

    candidates: list[tuple[int, str, dict[str, Any]]] = []
    for pair_key, pair in pairs.items():
        if not isinstance(pair, dict):
            continue
        triggers = pair.get("trigger_anchors") or ()
        if not isinstance(triggers, (list, tuple)):
            continue
        anchor_score = sum(
            1
            for trigger in triggers
            if isinstance(trigger, str)
            and trigger.strip()
            and (
                trigger.lower() in anchors_blob
                or trigger.lower() in message_blob
                or trigger.lower() in context_blob
            )
        )
        if anchor_score == 0:
            continue
        if cutoff_year is not None:
            pair_year = pair.get("cutoff_year")
            if isinstance(pair_year, int) and pair_year != cutoff_year:
                # Hard mismatch on year → drop this candidate. A keyword-only
                # match (cutoff_year=None) doesn't trigger this branch.
                continue
        candidates.append((anchor_score, pair_key, pair))

    if not candidates:
        return None

    # Highest anchor_score wins; ties broken by pair_key for determinism.
    candidates.sort(key=lambda triple: (-triple[0], triple[1]))
    return candidates[0][2]


def render_comparative_table(pair: dict[str, Any]) -> str:
    """Render the side-by-side markdown table for a regime pair."""
    cutoff_year = pair.get("cutoff_year")
    domain_label = pair.get("domain_label") or pair.get("domain") or "Régimen"
    cutoff_label = f"pre-{cutoff_year}" if cutoff_year else "Régimen anterior"
    post_label = "Vigente" if cutoff_year else "Régimen vigente"

    header = f"**Comparativo {domain_label} — {cutoff_label} vs vigente**"
    rows = [
        header,
        "",
        f"| Dimensión | {cutoff_label.capitalize()} | {post_label} |",
        "|---|---|---|",
    ]
    dimensions = pair.get("dimensions") or ()
    if isinstance(dimensions, (list, tuple)):
        for dim in dimensions:
            if not isinstance(dim, dict):
                continue
            label = str(dim.get("label") or "").strip()
            pre = str(dim.get("pre") or "").strip()
            post = str(dim.get("post") or "").strip()
            if not label:
                continue
            # Markdown tables break on literal `|`; replace with HTML escape.
            rows.append(
                f"| {label} | {pre.replace('|', '\\|')} | {post.replace('|', '\\|')} |"
            )
    return "\n".join(rows)


def _render_bullet_section(title: str, lines: tuple[str, ...]) -> str:
    if not lines:
        return ""
    body = "\n".join(f"- {line}" for line in lines if line)
    return f"**{title}**\n{body}"


def compose_comparative_regime_answer(
    *,
    request: PipelineCRequest,
    pair: dict[str, Any],
) -> str:
    """Compose the full comparative-regime answer.

    Layout (top to bottom):

    1. Verdict line ("Sí cambia. …" / "No cambia.").
    2. Side-by-side markdown table.
    3. Action line in bold (`**Acción inmediata.** …`).
    4. Riesgos y condiciones (curated from the pair config).
    5. Soportes clave (curated from the pair config).
    """
    sections: list[str] = []

    verdict = str(pair.get("verdict_yes") or "Sí cambia.").strip()
    sections.append(verdict)

    sections.append(render_comparative_table(pair))

    action = str(pair.get("action_line") or "").strip()
    if action:
        sections.append(f"**Acción inmediata.** {action}")

    risks = pair.get("risk_lines") or ()
    if isinstance(risks, (list, tuple)):
        risk_section = _render_bullet_section(
            "Riesgos y condiciones",
            tuple(str(r).strip() for r in risks if isinstance(r, str) and r.strip()),
        )
        if risk_section:
            sections.append(risk_section)

    supports = pair.get("support_lines") or ()
    if isinstance(supports, (list, tuple)):
        support_section = _render_bullet_section(
            "Soportes clave",
            tuple(str(s).strip() for s in supports if isinstance(s, str) and s.strip()),
        )
        if support_section:
            sections.append(support_section)

    return "\n\n".join(section for section in sections if section.strip())


__all__ = [
    "compose_comparative_regime_answer",
    "detect_comparative_regime_cue",
    "load_config",
    "match_regime_pair_for_request",
    "render_comparative_table",
]
