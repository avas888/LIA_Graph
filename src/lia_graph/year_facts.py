"""v23 P2 — Year-Constants Service (G2).

Canonical fiscal-year constants registry (UVT, SMLMV, auxilio de transporte,
sanción mínima) keyed by year. Loaded from `config/year_constants.json`.

Used by:
  * `pipeline_d/answer_llm_polish.py` to inject a `DIRECTIVA DE VALORES
    CANÓNICOS` block into the polish prompt for the detected fiscal year.
  * `pipeline_d/answer_llm_polish.py::_no_invented_uvt_ranges` to seed the
    allowed-token set when a fiscal year is detected for the question.
  * `pipeline_d/case_bullets/retencion_salarios.py` to render the UVT
    constant in the AG-2025 retención bullet (replaces the hardcoded
    stale `47.065` value the audit's Q2 surfaced).

Flag-gated by ``LIA_YEAR_CONSTANTS_INJECTION={off,shadow,enforce}``,
default ``enforce``.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Mapping


_DEFAULT_CONFIG_PATH = (
    Path(__file__).resolve().parent.parent.parent / "config" / "year_constants.json"
)


@dataclass(frozen=True)
class YearConstant:
    key: str
    value_cop: int | None
    value_uvt: int | None
    source: str
    verified: bool


@dataclass(frozen=True)
class YearFacts:
    year: int
    uvt: YearConstant | None
    smlmv: YearConstant | None
    auxilio_transporte: YearConstant | None
    sancion_minima: YearConstant | None
    raw: Mapping[str, Any]

    def directive_lines(self) -> list[str]:
        """Format verified constants as one-line strings for the polish prompt
        directive. Unverified constants are silently skipped — never lie to
        the LLM.
        """
        out: list[str] = []
        if self.uvt and self.uvt.verified and self.uvt.value_cop:
            out.append(
                f"UVT {self.year} = COP {self.uvt.value_cop:,}".replace(",", ".")
            )
        if self.smlmv and self.smlmv.verified and self.smlmv.value_cop:
            out.append(
                f"SMLMV {self.year} = COP {self.smlmv.value_cop:,}".replace(",", ".")
            )
        if (
            self.auxilio_transporte
            and self.auxilio_transporte.verified
            and self.auxilio_transporte.value_cop
        ):
            out.append(
                f"Auxilio de transporte {self.year} = COP "
                f"{self.auxilio_transporte.value_cop:,}".replace(",", ".")
            )
        return out

    def allowed_tokens(self) -> set[str]:
        """Numeric tokens (raw + dotted + comma formats) the polish UVT
        validator should treat as known-good when this year is in play.
        """
        tokens: set[str] = set()
        for c in (self.uvt, self.smlmv, self.auxilio_transporte, self.sancion_minima):
            if c is None:
                continue
            if c.value_cop:
                v = int(c.value_cop)
                tokens.add(str(v))
                tokens.add(f"{v:,}".replace(",", "."))
                tokens.add(f"{v:,}")
            if c.value_uvt:
                tokens.add(str(int(c.value_uvt)))
        return tokens


def injection_mode() -> str:
    raw = (os.getenv("LIA_YEAR_CONSTANTS_INJECTION") or "enforce").strip().lower()
    return raw if raw in ("off", "shadow", "enforce") else "enforce"


@lru_cache(maxsize=1)
def _load_registry() -> Mapping[str, Any]:
    path = Path(os.getenv("LIA_YEAR_CONSTANTS_PATH") or _DEFAULT_CONFIG_PATH)
    if not path.exists():
        return {"years": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"years": {}}


def _build_constant(key: str, raw: Mapping[str, Any] | None) -> YearConstant | None:
    if not isinstance(raw, Mapping):
        return None
    return YearConstant(
        key=key,
        value_cop=int(raw.get("value_cop")) if raw.get("value_cop") else None,
        value_uvt=int(raw.get("value_uvt")) if raw.get("value_uvt") else None,
        source=str(raw.get("source") or ""),
        verified=bool(raw.get("verified", False)),
    )


def get_year_facts(year: int) -> YearFacts | None:
    """Return the populated `YearFacts` for the given year or None when
    the registry has no entry. Verified=False constants are returned but
    flagged so callers can choose to skip them.
    """
    registry = _load_registry()
    years = registry.get("years") or {}
    raw = years.get(str(int(year)))
    if not isinstance(raw, Mapping):
        return None
    return YearFacts(
        year=int(year),
        uvt=_build_constant("uvt", raw.get("uvt")),
        smlmv=_build_constant("smlmv", raw.get("smlmv")),
        auxilio_transporte=_build_constant(
            "auxilio_transporte", raw.get("auxilio_transporte")
        ),
        sancion_minima=_build_constant("sancion_minima_uvt", raw.get("sancion_minima_uvt")),
        raw=dict(raw),
    )


# ---------------------------------------------------------------------------
# Fiscal-year extraction. Priority order:
#   1) explicit year in question text (e.g. "2026", "AG 2025", "año gravable 2024")
#   2) explicit year in conversation_state.fiscal_year (set by prior turn)
#   3) None — never default to date.today().year per D10 (Q-Open-3)
# ---------------------------------------------------------------------------


_YEAR_RX = re.compile(r"\b(20\d{2})\b")
_AG_RX = re.compile(r"\b(?:AG|a[nñ]o\s*gravable|aplicable\s*(?:al?\s*)?a[nñ]o)\s*(20\d{2})\b", re.IGNORECASE)


def extract_fiscal_year(
    question: str | None,
    planner_intent: Mapping[str, Any] | None = None,
    conversation_state: Mapping[str, Any] | None = None,
) -> int | None:
    """Best-effort fiscal-year detector. Returns None when no signal is
    present — never defaults to current year (per D10)."""
    text = (question or "").strip()
    if text:
        m = _AG_RX.search(text)
        if m:
            try:
                return int(m.group(1))
            except (TypeError, ValueError):
                pass
        m = _YEAR_RX.search(text)
        if m:
            try:
                year = int(m.group(1))
                # Plausible fiscal year window — guard against unrelated 20xx
                # numbers (e.g. ZIP codes; we don't have any but be safe).
                if 2010 <= year <= 2035:
                    return year
            except (TypeError, ValueError):
                pass
    if isinstance(planner_intent, Mapping):
        v = planner_intent.get("fiscal_year")
        if isinstance(v, int):
            return v
        if isinstance(v, str) and v.isdigit():
            return int(v)
    if isinstance(conversation_state, Mapping):
        v = conversation_state.get("fiscal_year")
        if isinstance(v, int):
            return v
        if isinstance(v, str) and v.isdigit():
            return int(v)
    return None


def build_directive_block(year: int) -> str | None:
    """Return the polish-prompt directive block for the detected fiscal year,
    or None when no verified constants exist for that year.
    """
    if injection_mode() == "off":
        return None
    facts = get_year_facts(year)
    if facts is None:
        return None
    lines = facts.directive_lines()
    if not lines:
        return None
    bullets = "\n".join(f"   - {line}" for line in lines)
    return (
        f"DIRECTIVA DE VALORES CANÓNICOS PARA AÑO GRAVABLE {year}:\n"
        f"{bullets}\n"
        f"   NO uses otros valores aunque la evidencia los traiga. Si una "
        f"cifra del borrador contradice esta directiva, corregila al valor "
        f"canónico de arriba antes de devolver la respuesta."
    )


def clear_cache() -> None:
    """Test helper — reset the registry cache."""
    _load_registry.cache_clear()


# ---------------------------------------------------------------------------
# v25 P6 — Compliance-deadline registry (G13).
# ---------------------------------------------------------------------------


def deadline_injection_mode() -> str:
    raw = (os.getenv("LIA_DEADLINE_REGISTRY_INJECTION") or "enforce").strip().lower()
    return raw if raw in ("off", "shadow", "enforce") else "enforce"


@dataclass(frozen=True)
class DeadlineFact:
    key: str
    deadline_label: str
    source: str
    verified: bool
    applies_to_topics: tuple[str, ...]


def get_deadlines_for_topic(topic: str | None) -> list[DeadlineFact]:
    """Return verified deadlines that apply to ``topic``.

    Unverified deadlines are skipped (silent — never inject a date you
    cannot back up per `feedback_no_hallucinated_examples`).
    """
    if not topic:
        return []
    topic_norm = topic.strip().lower()
    registry = _load_registry()
    raw_block = registry.get("deadlines")
    if not isinstance(raw_block, Mapping):
        return []
    out: list[DeadlineFact] = []
    for key, raw in raw_block.items():
        if not isinstance(raw, Mapping):
            continue
        if not raw.get("verified", False):
            continue
        applies = tuple(
            str(t).strip().lower() for t in (raw.get("applies_to_topics") or ())
        )
        if topic_norm not in applies:
            continue
        out.append(
            DeadlineFact(
                key=str(key),
                deadline_label=str(raw.get("deadline_label") or ""),
                source=str(raw.get("source") or ""),
                verified=True,
                applies_to_topics=applies,
            )
        )
    return out


def build_deadline_directive(topic: str | None) -> str | None:
    """Polish-prompt block listing the controlling deadlines for ``topic``.

    Returns None when the flag is off, the topic is empty, or no verified
    deadlines apply.
    """
    if deadline_injection_mode() == "off":
        return None
    facts = get_deadlines_for_topic(topic)
    if not facts:
        return None
    bullets = "\n".join(
        f"   - **{f.deadline_label}** — {f.source}" for f in facts
    )
    return (
        f"DIRECTIVA DE PLAZOS CANÓNICOS para `{topic}`:\n"
        f"{bullets}\n"
        f"   Cita estos plazos EXACTAMENTE; no inventes ni redondees fechas. "
        f"Si la evidencia no los confirma, mantenelos igual — son canon."
    )


def multi_uvt(n_uvt: int, year: int) -> int | None:
    """Return precomputed COP value of ``n_uvt`` UVT for ``year``.

    Falls back to ``n_uvt * UVT(year)`` when the helper table does not list
    that multiple but UVT(year) is verified. Returns None when nothing
    verifiable exists.
    """
    registry = _load_registry()
    helpers = registry.get("multi_uvt_helpers") or {}
    year_block = helpers.get(str(int(year))) if isinstance(helpers, Mapping) else None
    if isinstance(year_block, Mapping):
        raw = year_block.get(str(int(n_uvt)))
        if isinstance(raw, int):
            return raw
    # Fallback: derive from UVT registry if verified.
    facts = get_year_facts(year)
    if facts and facts.uvt and facts.uvt.verified and facts.uvt.value_cop:
        return int(n_uvt) * int(facts.uvt.value_cop)
    return None


__all__ = [
    "DeadlineFact",
    "YearConstant",
    "YearFacts",
    "build_deadline_directive",
    "build_directive_block",
    "clear_cache",
    "deadline_injection_mode",
    "extract_fiscal_year",
    "get_deadlines_for_topic",
    "get_year_facts",
    "injection_mode",
    "multi_uvt",
]
