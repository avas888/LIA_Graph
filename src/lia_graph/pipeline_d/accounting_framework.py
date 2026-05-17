"""fix_v25_may.md §3.4 — Phase 4 / G11: accounting framework awareness.

External SME Q19 (leasing under "NIIF para Pymes") was answered using the
IFRS Full / NIIF Plenas lessee model (NIIF 16 / right-of-use asset).
Colombia's Decreto 2420/2015 keeps NIIF para Pymes Section 20 (finance vs
operating lease classification) for SMB lessees; NIIF 16 is the wrong
framework for that question. This module detects the framework cue and
produces a polish-prompt directive + a validator (lives in
``answer_polish_validators_v25.py``).

Flag: ``LIA_FRAMEWORK_AWARENESS={off,shadow,enforce}`` (default
``enforce``).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

__all__ = [
    "FrameworkHint",
    "detect_framework_hint",
    "framework_directive",
    "awareness_enabled",
    "awareness_mode",
]


_ENV_FLAG = "LIA_FRAMEWORK_AWARENESS"


def awareness_mode() -> str:
    raw = (os.getenv(_ENV_FLAG) or "enforce").strip().lower()
    if raw in {"off", "shadow", "enforce"}:
        return raw
    return "enforce"


def awareness_enabled() -> bool:
    return awareness_mode() != "off"


@dataclass(frozen=True)
class FrameworkHint:
    framework: str  # niif_pymes | niif_plenas | niif_microempresas | decreto_2649_2706 | none
    cue: str | None = None


# Most specific first.
_NIIF_PYMES_RX = re.compile(
    r"\b(NIIF\s+para\s+(?:las\s+)?[Pp]ymes|para\s+[Pp]ymes|pyme\b|"
    r"microempresa\s+contable|Decreto\s+2420(?:\s*de\s*2015)?)\b",
    flags=re.IGNORECASE,
)
_NIIF_PLENAS_RX = re.compile(
    r"\b(NIIF\s+[Pp]lenas|IFRS\s+(?:Full|16|9|15)|NIC\s+\d+|NIIF\s+\d+(?:\s|$))\b",
    flags=re.IGNORECASE,
)
_NIIF_MICRO_RX = re.compile(
    r"\b(microempresa(?:s)?\s+(?:contable|NIIF)|grupo\s+3\b)",
    flags=re.IGNORECASE,
)
_DECRETO_2649_RX = re.compile(r"\bDecreto\s+(?:2649|2706)\b", flags=re.IGNORECASE)


def detect_framework_hint(question: str) -> FrameworkHint:
    if not question:
        return FrameworkHint(framework="none")
    if m := _NIIF_PYMES_RX.search(question):
        return FrameworkHint(framework="niif_pymes", cue=m.group(0))
    if m := _NIIF_MICRO_RX.search(question):
        return FrameworkHint(framework="niif_microempresas", cue=m.group(0))
    if m := _NIIF_PLENAS_RX.search(question):
        return FrameworkHint(framework="niif_plenas", cue=m.group(0))
    if m := _DECRETO_2649_RX.search(question):
        return FrameworkHint(framework="decreto_2649_2706", cue=m.group(0))
    return FrameworkHint(framework="none")


def framework_directive(hint: FrameworkHint) -> str:
    """Polish-prompt block enforcing the detected framework."""
    if hint.framework == "niif_pymes":
        return (
            "MARCO TÉCNICO CONTABLE: **NIIF para las Pymes** (Decreto 2420/"
            "2015 y modificatorios). NO uses NIIF Plenas, IFRS Full, NIC ni "
            "ninguna NIIF numerada (NIIF 15, NIIF 16, NIIF 9). En "
            "arrendamientos aplica **Sección 20** — clasificación financiero/"
            "operativo según transferencia de riesgos y beneficios; NO uses "
            "el modelo right-of-use de IFRS 16. En deterioro de cartera "
            "aplica **Sección 11**. En impuesto diferido aplica **Sección 29**."
        )
    if hint.framework == "niif_microempresas":
        return (
            "MARCO TÉCNICO CONTABLE: **NIIF Microempresas (Grupo 3, Decreto "
            "2420/2015 Anexo 3)**. Aplica reglas simplificadas — NO uses "
            "NIIF Plenas ni NIIF para Pymes."
        )
    if hint.framework == "niif_plenas":
        return (
            "MARCO TÉCNICO CONTABLE: **NIIF Plenas / IFRS Full** (Grupo 1, "
            "Decreto 2420/2015 Anexo 1). En arrendamientos aplica NIIF 16; "
            "en impuesto diferido NIC 12; en deterioro NIC 36."
        )
    if hint.framework == "decreto_2649_2706":
        return (
            "MARCO TÉCNICO CONTABLE: Decreto 2649/2706 (marco anterior). "
            "Aplica solo para entidades no obligadas a NIIF; explícita que el "
            "marco vigente para la mayoría es NIIF Pymes/Plenas según grupo."
        )
    return ""
