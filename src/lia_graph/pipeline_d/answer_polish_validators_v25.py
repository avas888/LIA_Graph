"""fix_v25_may.md — polish-time validators for v25 phases.

Granularized per operator directive 2026-05-17 PM + `feedback_granular_edits`.
Each validator returns ``True`` when the polished output is acceptable,
``False`` when it must be rejected. The POLISH_RULES tuple in
``answer_llm_polish.py`` wires these by id; the dispatcher in that module
already supports the widest validator signature
``(template, polished, evidence, question)``.

Validators in this file:
  - ``framework_coherence`` — P4 / G11. Reject when question said NIIF Pymes
    but polished mentions NIIF 16 / IFRS 16 / right-of-use.
  - ``no_coverage_gap_phrase`` — P5 / G12. Reject when polished contains a
    canonical "I-don't-know" stub like "Cobertura pendiente".
  - ``no_counterfactual_entities`` — P9 / G16. Reject when polished
    introduces named persons / companies / monetary facts that exist in
    neither the question nor the evidence.

Each validator is also guarded by its own LIA_* env flag so it can be
disabled without touching POLISH_RULES.
"""

from __future__ import annotations

import os
import re
from typing import Iterable

from .accounting_framework import (
    awareness_enabled as framework_enabled,
    detect_framework_hint,
)
from .counterfactual_detector import (
    detect_counterfactual_entities,
    detector_enabled as counterfactual_enabled,
)

__all__ = [
    "framework_coherence",
    "no_coverage_gap_phrase",
    "no_counterfactual_entities",
    "coverage_gap_enabled",
]


_COVERAGE_GAP_ENV = "LIA_COVERAGE_GAP_GATE"


def coverage_gap_enabled() -> bool:
    raw = (os.getenv(_COVERAGE_GAP_ENV) or "enforce").strip().lower()
    return raw != "off"


_NIIF16_TOKENS_RX = re.compile(
    r"\b(NIIF\s+16|IFRS\s+16|right.of.use|derecho\s+de\s+uso)\b",
    flags=re.IGNORECASE,
)


def framework_coherence(
    template: str,
    polished: str,
    evidence=None,
    question: str | None = None,
) -> bool:
    """Reject NIIF 16 mentions in a NIIF-Pymes question (P4 / G11)."""
    if not framework_enabled():
        return True
    if not question or not polished:
        return True
    hint = detect_framework_hint(question)
    if hint.framework != "niif_pymes":
        return True
    return _NIIF16_TOKENS_RX.search(polished) is None


_COVERAGE_GAP_STUBS_RX = re.compile(
    r"(?:cobertura\s+pendiente|valida(?:\s+el)?\s+expediente\s+antes|"
    r"no\s+encuentro\s+evidencia\s+(?:para|sobre)|sin\s+evidencia\s+suficiente\s+para)",
    flags=re.IGNORECASE,
)


def no_coverage_gap_phrase(
    template: str,
    polished: str,
    evidence=None,
    question: str | None = None,
) -> bool:
    """Reject polished output containing canonical gap stubs (P5 / G12)."""
    if not coverage_gap_enabled():
        return True
    if not polished:
        return True
    return _COVERAGE_GAP_STUBS_RX.search(polished) is None


def no_counterfactual_entities(
    template: str,
    polished: str,
    evidence=None,
    question: str | None = None,
) -> bool:
    """Reject polished output that introduces invented entities (P9 / G16)."""
    if not counterfactual_enabled():
        return True
    if not polished:
        return True
    evidence_text = _stringify_evidence(evidence)
    findings = detect_counterfactual_entities(
        question or "", evidence_text, polished, template=template
    )
    return not findings


def _stringify_evidence(evidence) -> str:
    """Best-effort flatten an evidence bundle into searchable text."""
    if evidence is None:
        return ""
    if isinstance(evidence, str):
        return evidence
    if isinstance(evidence, Iterable):
        try:
            return "\n".join(str(item) for item in evidence)
        except Exception:  # noqa: BLE001
            return ""
    text_attrs = ("text", "excerpt", "content", "raw_markdown")
    for attr in text_attrs:
        value = getattr(evidence, attr, None)
        if value:
            return str(value)
    return repr(evidence)
