"""Vigencia value object — fixplan_v3 §0.4 + §0.11.3.

The 11-state taxonomy plus the structured `ChangeSource` discriminated union
that replaces v2's free-text `vigencia_basis`. This module is the single
source of truth for the shape that lands in `norm_vigencia_history.veredicto`
and in `evals/vigencia_extraction_v1/<norm_id>.json`.

Contracts come from `docs/re-engineer/fixplan_v3.md` §0.4, §0.11.3.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Iterable, Literal, Mapping, Sequence


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class VigenciaState(str, Enum):
    """11-state taxonomy from fixplan_v3 §0.4.1."""

    V = "V"
    VM = "VM"
    DE = "DE"
    DT = "DT"
    SP = "SP"
    IE = "IE"
    EC = "EC"
    VC = "VC"
    VL = "VL"
    DI = "DI"
    RV = "RV"


VIGENCIA_STATE_NAMES: Mapping[VigenciaState, str] = {
    VigenciaState.V: "Vigente sin modificaciones",
    VigenciaState.VM: "Vigente modificada",
    VigenciaState.DE: "Derogada expresa",
    VigenciaState.DT: "Derogada tácita",
    VigenciaState.SP: "Suspendida provisional CE",
    VigenciaState.IE: "Inexequible (CC)",
    VigenciaState.EC: "Exequibilidad condicionada",
    VigenciaState.VC: "Vigente condicionada",
    VigenciaState.VL: "Vacatio legis",
    VigenciaState.DI: "Diferida",
    VigenciaState.RV: "Revivida",
}

# Default demotion factors for instantaneous-tax / procedimiento queries
# (per §0.4.1 + §0.4.3). The retriever multiplies a chunk's RRF score by
# `demotion_factor` for every anchor citation it carries.
DEFAULT_DEMOTION: Mapping[VigenciaState, float] = {
    VigenciaState.V: 1.0,
    VigenciaState.VM: 1.0,
    VigenciaState.DE: 0.0,
    VigenciaState.DT: 0.3,
    VigenciaState.SP: 0.0,
    VigenciaState.IE: 0.0,
    VigenciaState.EC: 1.0,
    VigenciaState.VC: 1.0,
    VigenciaState.VL: 0.0,
    VigenciaState.DI: 1.0,
    VigenciaState.RV: 1.0,
}


class ChangeSourceType(str, Enum):
    REFORMA = "reforma"
    DEROGACION_EXPRESA = "derogacion_expresa"
    DEROGACION_TACITA = "derogacion_tacita"
    SENTENCIA_CC = "sentencia_cc"
    AUTO_CE_SUSPENSION = "auto_ce_suspension"
    SENTENCIA_CE_NULIDAD = "sentencia_ce_nulidad"
    REVIVISCENCIA = "reviviscencia"
    VACATIO = "vacatio"
    CONCEPTO_DIAN_MODIFICATORIO = "concepto_dian_modificatorio"
    MODULACION_DOCTRINARIA = "modulacion_doctrinaria"


EffectType = Literal["pro_futuro", "retroactivo", "diferido", "per_period"]
AppliesToKind = Literal["always", "per_year", "per_period"]
AnchorStrength = Literal["ley", "decreto", "res_dian", "concepto_dian", "jurisprudencia"]
CitationRole = Literal["anchor", "reference", "comparator", "historical"]


# State → required `change_source.type` values that are admissible.
_VALID_CHANGE_SOURCE_TYPES: Mapping[VigenciaState, frozenset[ChangeSourceType]] = {
    VigenciaState.V: frozenset(),  # inaugural V row may have no change_source
    VigenciaState.VM: frozenset({ChangeSourceType.REFORMA}),
    VigenciaState.DE: frozenset({ChangeSourceType.DEROGACION_EXPRESA}),
    VigenciaState.DT: frozenset({ChangeSourceType.DEROGACION_TACITA}),
    VigenciaState.SP: frozenset({ChangeSourceType.AUTO_CE_SUSPENSION}),
    VigenciaState.IE: frozenset({ChangeSourceType.SENTENCIA_CC, ChangeSourceType.SENTENCIA_CE_NULIDAD}),
    VigenciaState.EC: frozenset({ChangeSourceType.SENTENCIA_CC}),
    VigenciaState.VC: frozenset(
        {ChangeSourceType.MODULACION_DOCTRINARIA, ChangeSourceType.CONCEPTO_DIAN_MODIFICATORIO}
    ),
    VigenciaState.VL: frozenset({ChangeSourceType.VACATIO}),
    VigenciaState.DI: frozenset({ChangeSourceType.SENTENCIA_CC}),
    VigenciaState.RV: frozenset({ChangeSourceType.REVIVISCENCIA}),
}


# ---------------------------------------------------------------------------
# Helper dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Citation:
    """A single norm citation, used for primary sources, derogación links, etc."""

    norm_id: str
    norm_type: str | None = None
    article: str | None = None
    fecha: date | None = None
    primary_source_url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "norm_id": self.norm_id,
            "norm_type": self.norm_type,
            "article": self.article,
            "fecha": self.fecha.isoformat() if self.fecha else None,
            "primary_source_url": self.primary_source_url,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Citation":
        fecha_raw = data.get("fecha")
        return cls(
            norm_id=str(data["norm_id"]),
            norm_type=data.get("norm_type"),
            article=data.get("article"),
            fecha=_parse_date(fecha_raw),
            primary_source_url=data.get("primary_source_url"),
        )


@dataclass(frozen=True)
class InterpretiveConstraint:
    """Set when state ∈ {EC, VC}. Literal Court text — no paraphrase."""

    sentencia_norm_id: str
    fecha_sentencia: date
    texto_literal: str
    fuente_verificada_directo: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "sentencia_norm_id": self.sentencia_norm_id,
            "fecha_sentencia": self.fecha_sentencia.isoformat(),
            "texto_literal": self.texto_literal,
            "fuente_verificada_directo": self.fuente_verificada_directo,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "InterpretiveConstraint":
        return cls(
            sentencia_norm_id=str(data["sentencia_norm_id"]),
            fecha_sentencia=_require_date(data["fecha_sentencia"], "fecha_sentencia"),
            texto_literal=str(data["texto_literal"]),
            fuente_verificada_directo=bool(data.get("fuente_verificada_directo", False)),
        )


@dataclass(frozen=True)
class ChangeSource:
    """Discriminated union per fixplan_v3 §0.3.3.

    The application-layer Pydantic equivalent lives at the JSONB boundary.
    This dataclass is the in-process representation; `to_dict()` produces the
    JSONB-shaped payload the writer persists.
    """

    type: ChangeSourceType
    source_norm_id: str
    effect_type: EffectType
    effect_payload: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.source_norm_id:
            raise ValueError("change_source.source_norm_id is required")
        # type/effect compatibility — light validation; full per-type schemas
        # are enforced at the Pydantic layer used by the writer.
        if self.type == ChangeSourceType.SENTENCIA_CC:
            allowed = {"pro_futuro", "retroactivo", "diferido"}
            if self.effect_type not in allowed:
                raise ValueError(
                    f"sentencia_cc requires effect_type in {allowed}; got {self.effect_type}"
                )
        elif self.type == ChangeSourceType.REFORMA:
            allowed = {"pro_futuro", "per_period"}
            if self.effect_type not in allowed:
                raise ValueError(
                    f"reforma requires effect_type in {allowed}; got {self.effect_type}"
                )

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type.value,
            "source_norm_id": self.source_norm_id,
            "effect_type": self.effect_type,
            "effect_payload": dict(self.effect_payload),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ChangeSource":
        return cls(
            type=ChangeSourceType(str(data["type"])),
            source_norm_id=str(data["source_norm_id"]),
            effect_type=str(data["effect_type"]),  # type: ignore[arg-type]
            effect_payload=dict(data.get("effect_payload") or {}),
        )


@dataclass(frozen=True)
class AppliesToPayload:
    """Shape varies with applies_to_kind. See fixplan_v3 §0.11.3 contract 1."""

    year_start: int | None = None
    year_end: int | None = None
    impuesto: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    art_338_cp_shift: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "year_start": self.year_start,
            "year_end": self.year_end,
            "impuesto": self.impuesto,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "art_338_cp_shift": self.art_338_cp_shift,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AppliesToPayload":
        return cls(
            year_start=_optional_int(data.get("year_start")),
            year_end=_optional_int(data.get("year_end")),
            impuesto=data.get("impuesto"),
            period_start=_parse_date(data.get("period_start")),
            period_end=_parse_date(data.get("period_end")),
            art_338_cp_shift=bool(data.get("art_338_cp_shift", False)),
        )


@dataclass(frozen=True)
class ExtractionAudit:
    """Audit metadata for a vigencia extraction run (skill or manual)."""

    skill_version: str
    model: str | None = None
    tool_iterations: int | None = None
    wall_ms: int | None = None
    cost_usd_estimate: float | None = None
    run_id: str | None = None
    sources_hash: str | None = None
    method: str | None = None  # 'skill' | 'manual_sme' | 'v2_to_v3_upgrade' | 'cron@v1'

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_version": self.skill_version,
            "model": self.model,
            "tool_iterations": self.tool_iterations,
            "wall_ms": self.wall_ms,
            "cost_usd_estimate": self.cost_usd_estimate,
            "run_id": self.run_id,
            "sources_hash": self.sources_hash,
            "method": self.method,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ExtractionAudit":
        return cls(
            skill_version=str(data.get("skill_version") or "unknown"),
            model=data.get("model"),
            tool_iterations=_optional_int(data.get("tool_iterations")),
            wall_ms=_optional_int(data.get("wall_ms")),
            cost_usd_estimate=_optional_float(data.get("cost_usd_estimate")),
            run_id=data.get("run_id"),
            sources_hash=data.get("sources_hash"),
            method=data.get("method"),
        )


@dataclass(frozen=True)
class CanonicalizerRefusal:
    """Reason a free-text mention could not be canonicalized."""

    mention: str
    reason: str  # e.g. 'missing_year', 'no_law_prefix', 'not_a_citation'
    context: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"mention": self.mention, "reason": self.reason, "context": self.context}


# ---------------------------------------------------------------------------
# Vigencia value object (the load-bearing one)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Vigencia:
    """The v3 Vigencia value object — fixplan_v3 §0.11.3 contract 1.

    Skill-emitted; persisted to `norm_vigencia_history`. Constructed only by
    the skill, by the v2-to-v3 upgrade mapper, or by the SME-signed manual
    override path.
    """

    state: VigenciaState
    state_from: date
    state_until: date | None
    applies_to_kind: AppliesToKind
    applies_to_payload: AppliesToPayload
    change_source: ChangeSource | None
    interpretive_constraint: InterpretiveConstraint | None = None
    derogado_por: Citation | None = None
    modificado_por: tuple[Citation, ...] = ()
    suspension: Citation | None = None
    inexequibilidad: Citation | None = None
    regimen_transicion: Citation | None = None
    revives_text_version: str | None = None
    rige_desde: date | None = None
    fuentes_primarias_consultadas: tuple[Citation, ...] = ()
    extraction_audit: ExtractionAudit | None = None

    def __post_init__(self) -> None:
        # state_until consistency
        if self.state_until is not None and self.state_until < self.state_from:
            raise ValueError(
                f"state_until ({self.state_until}) must be >= state_from ({self.state_from})"
            )
        # interpretive_constraint required for EC + VC
        if self.state in (VigenciaState.EC, VigenciaState.VC):
            if self.interpretive_constraint is None:
                raise ValueError(f"state={self.state.value} requires interpretive_constraint")
        # rige_desde required for VL + DI
        if self.state in (VigenciaState.VL, VigenciaState.DI):
            if self.rige_desde is None:
                raise ValueError(f"state={self.state.value} requires rige_desde")
        # revives_text_version required for RV
        if self.state == VigenciaState.RV and not self.revives_text_version:
            raise ValueError("state=RV requires revives_text_version")
        # change_source / state compatibility
        if self.change_source is not None:
            allowed_types = _VALID_CHANGE_SOURCE_TYPES.get(self.state, frozenset())
            if allowed_types and self.change_source.type not in allowed_types:
                raise ValueError(
                    f"state={self.state.value} not compatible with "
                    f"change_source.type={self.change_source.type.value}"
                )
        elif self.state != VigenciaState.V:
            # Non-V states must declare a change_source (the source of the transition).
            raise ValueError(
                f"state={self.state.value} requires change_source (only V may omit)"
            )

    # ------------------------------------------------------------------
    # Resolver helpers
    # ------------------------------------------------------------------

    def applies_to_date(self, d: date) -> bool:
        """True when this row's [state_from, state_until) window covers `d`."""

        if d < self.state_from:
            return False
        if self.state_until is not None and d >= self.state_until:
            return False
        return True

    def applies_to_period(self, impuesto: str, year: int) -> bool:
        """True when the row applies to the given fiscal period.

        Honors Art. 338 CP for impuestos de período: a reforma vigente in year N
        applies to AG N+1, not AG N. The raw applicability rule lives in
        `applies_to_payload`.
        """

        kind = self.applies_to_kind
        payload = self.applies_to_payload

        if kind == "always":
            return True

        if kind == "per_year":
            if payload.year_start is not None and year < payload.year_start:
                return False
            if payload.year_end is not None and year > payload.year_end:
                return False
            return True

        if kind == "per_period":
            if payload.impuesto and impuesto and payload.impuesto != impuesto:
                return False
            target = date(year, 12, 31)
            if payload.period_start and target < payload.period_start:
                return False
            if payload.period_end and target > payload.period_end:
                return False
            return True

        return False

    def demotion_factor(self) -> float:
        return DEFAULT_DEMOTION.get(self.state, 0.0)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "state_from": self.state_from.isoformat(),
            "state_until": self.state_until.isoformat() if self.state_until else None,
            "applies_to_kind": self.applies_to_kind,
            "applies_to_payload": self.applies_to_payload.to_dict(),
            "change_source": self.change_source.to_dict() if self.change_source else None,
            "interpretive_constraint": self.interpretive_constraint.to_dict()
            if self.interpretive_constraint
            else None,
            "derogado_por": self.derogado_por.to_dict() if self.derogado_por else None,
            "modificado_por": [c.to_dict() for c in self.modificado_por],
            "suspension": self.suspension.to_dict() if self.suspension else None,
            "inexequibilidad": self.inexequibilidad.to_dict() if self.inexequibilidad else None,
            "regimen_transicion": self.regimen_transicion.to_dict()
            if self.regimen_transicion
            else None,
            "revives_text_version": self.revives_text_version,
            "rige_desde": self.rige_desde.isoformat() if self.rige_desde else None,
            "fuentes_primarias_consultadas": [
                c.to_dict() for c in self.fuentes_primarias_consultadas
            ],
            "extraction_audit": self.extraction_audit.to_dict()
            if self.extraction_audit
            else None,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Vigencia":
        return cls(
            state=VigenciaState(str(data["state"])),
            state_from=_require_date(data["state_from"], "state_from"),
            state_until=_parse_date(data.get("state_until")),
            applies_to_kind=str(data.get("applies_to_kind") or "always"),  # type: ignore[arg-type]
            applies_to_payload=AppliesToPayload.from_dict(
                data.get("applies_to_payload") or {}
            ),
            change_source=ChangeSource.from_dict(data["change_source"])
            if data.get("change_source")
            else None,
            interpretive_constraint=InterpretiveConstraint.from_dict(data["interpretive_constraint"])
            if data.get("interpretive_constraint")
            else None,
            derogado_por=_first_citation(data.get("derogado_por")),
            modificado_por=tuple(
                Citation.from_dict(c) for c in (data.get("modificado_por") or ())
            ),
            suspension=_first_citation(data.get("suspension")),
            inexequibilidad=_first_citation(data.get("inexequibilidad")),
            regimen_transicion=_first_citation(data.get("regimen_transicion")),
            revives_text_version=data.get("revives_text_version"),
            rige_desde=_parse_date(data.get("rige_desde")),
            fuentes_primarias_consultadas=tuple(
                Citation.from_dict(c) for c in (data.get("fuentes_primarias_consultadas") or ())
            ),
            extraction_audit=ExtractionAudit.from_dict(data["extraction_audit"])
            if data.get("extraction_audit")
            else None,
        )

    @classmethod
    def from_json(cls, text: str) -> "Vigencia":
        return cls.from_dict(json.loads(text))


@dataclass(frozen=True)
class VigenciaResult:
    """Either a successful veredicto OR a documented refusal — never an unverified guess.

    See fixplan_v3 §0.11.3 contract 1. `veredicto is None` ↔ refusal_reason set.
    """

    veredicto: Vigencia | None
    refusal_reason: str | None = None
    missing_sources: tuple[str, ...] = ()
    canonicalizer_refusals: tuple[CanonicalizerRefusal, ...] = ()
    audit: ExtractionAudit | None = None

    def __post_init__(self) -> None:
        if self.veredicto is None and not self.refusal_reason:
            raise ValueError(
                "VigenciaResult: refusal_reason required when veredicto is None"
            )
        if self.veredicto is not None and self.refusal_reason:
            raise ValueError(
                "VigenciaResult: refusal_reason must be None when a veredicto is present"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "veredicto": self.veredicto.to_dict() if self.veredicto else None,
            "refusal_reason": self.refusal_reason,
            "missing_sources": list(self.missing_sources),
            "canonicalizer_refusals": [r.to_dict() for r in self.canonicalizer_refusals],
            "audit": self.audit.to_dict() if self.audit else None,
        }


# ---------------------------------------------------------------------------
# v2 → v3 upgrade mapper (one-shot for the 7 fixtures + the 4 staging rows)
# ---------------------------------------------------------------------------


_V2_STATE_MAP: Mapping[str, VigenciaState] = {
    "vigente": VigenciaState.V,
    "v": VigenciaState.V,
    "vm": VigenciaState.VM,
    "vigente_modificada": VigenciaState.VM,
    "vigente con modificaciones": VigenciaState.VM,
    "derogada": VigenciaState.DE,
    "de": VigenciaState.DE,
    "derogada_expresa": VigenciaState.DE,
    "derogada expresa": VigenciaState.DE,
    "dt": VigenciaState.DT,
    "derogada_tacita": VigenciaState.DT,
    "derogada tácita": VigenciaState.DT,
    "sp": VigenciaState.SP,
    "suspendida": VigenciaState.SP,
    "ie": VigenciaState.IE,
    "inexequible": VigenciaState.IE,
    "ec": VigenciaState.EC,
    "exequibilidad_condicionada": VigenciaState.EC,
    "exequibilidad condicionada": VigenciaState.EC,
}


def map_v2_state(label: str) -> VigenciaState:
    key = (label or "").strip().lower()
    if key in _V2_STATE_MAP:
        return _V2_STATE_MAP[key]
    try:
        return VigenciaState(label)
    except ValueError as err:
        raise ValueError(f"Unknown vigencia state label: {label!r}") from err


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _first_citation(value: Any) -> Citation | None:
    """Tolerate both single-Citation dict and list-of-Citations input.

    Gemini sometimes emits `derogado_por` / `inexequibilidad` /
    `suspension` / `regimen_transicion` as a list (because conceptually a
    norm could have multiple of these), but the v3 schema models each as
    a single Citation — the most recent / authoritative one. This helper
    accepts either shape: dict → that Citation; list → the first item;
    None / empty → None.
    """

    if not value:
        return None
    if isinstance(value, list):
        if not value:
            return None
        head = value[0]
        if not isinstance(head, dict):
            return None
        return Citation.from_dict(head)
    if isinstance(value, dict):
        return Citation.from_dict(value)
    return None


_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _parse_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        if _DATE_RE.match(value):
            return date.fromisoformat(value)
        # tolerate full ISO datetimes
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        except ValueError as err:
            raise ValueError(f"Cannot parse date from {value!r}") from err
    raise ValueError(f"Unsupported date type: {type(value).__name__}")


def _require_date(value: Any, field_name: str) -> date:
    parsed = _parse_date(value)
    if parsed is None:
        raise ValueError(f"{field_name} is required")
    return parsed


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


__all__ = [
    "AppliesToKind",
    "AppliesToPayload",
    "AnchorStrength",
    "CanonicalizerRefusal",
    "ChangeSource",
    "ChangeSourceType",
    "Citation",
    "CitationRole",
    "DEFAULT_DEMOTION",
    "EffectType",
    "ExtractionAudit",
    "InterpretiveConstraint",
    "VIGENCIA_STATE_NAMES",
    "Vigencia",
    "VigenciaResult",
    "VigenciaState",
    "map_v2_state",
]
