"""fixplan_v3 sub-fix 1B-ε — Python wrapper around the v3 resolver functions.

Picks `norm_vigencia_at_date` vs `norm_vigencia_for_period` based on the
planner's `vigencia_query_kind` cue. Both call the corresponding Postgres
function via the Supabase RPC client; the Falkor side runs an analogous
period-applicability check in Python after pulling property-bag data.

This module is the single read entry point for the retriever's vigencia
gate. Retrievers do NOT compute period applicability themselves; they ask
the resolver and trust the answer.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Iterable, Mapping, Sequence

from lia_graph.pipeline_d.contracts import GraphRetrievalPlan
from lia_graph.vigencia import DEFAULT_DEMOTION, VigenciaState

LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResolverRow:
    """One row of the resolver output for a given norm at a given query."""

    norm_id: str
    state: str
    state_from: date
    state_until: date | None
    record_id: str
    change_source: Mapping[str, Any]
    interpretive_constraint: Mapping[str, Any] | None
    demotion_factor: float
    norm_version_aplicable: str | None = None
    art_338_cp_applied: bool = False

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "ResolverRow":
        return cls(
            norm_id=str(row["norm_id"]),
            state=str(row["state"]),
            state_from=_to_date(row["state_from"]),
            state_until=_to_date(row.get("state_until")),
            record_id=str(row.get("record_id") or ""),
            change_source=row.get("change_source") or {},
            interpretive_constraint=row.get("interpretive_constraint"),
            demotion_factor=float(row.get("demotion_factor") or 0.0),
            norm_version_aplicable=row.get("norm_version_aplicable"),
            art_338_cp_applied=bool(row.get("art_338_cp_applied") or False),
        )


@dataclass(frozen=True)
class ResolverQuery:
    """The shape of a resolver call for a single retrieval turn."""

    kind: str  # 'at_date' | 'for_period'
    payload: Mapping[str, Any]

    @classmethod
    def from_plan(cls, plan: GraphRetrievalPlan, *, default_today: date | None = None) -> "ResolverQuery":
        """Map a planner contract to a resolver call shape.

        Default (None on plan): `at_date` with today's date.
        """

        kind = plan.vigencia_query_kind or "at_date"
        payload: Mapping[str, Any] = plan.vigencia_query_payload or {}
        if kind == "at_date" and "as_of_date" not in payload:
            d = default_today or date.today()
            payload = {"as_of_date": d.isoformat()}
        return cls(kind=kind, payload=dict(payload))


# ---------------------------------------------------------------------------
# Resolver protocol
# ---------------------------------------------------------------------------


class VigenciaResolver:
    """Reads `norm_vigencia_history` via the SQL resolver functions.

    Production: backed by a Supabase client invoking RPC.
    Tests: pass a fake `_resolver_callable` that returns canned rows.
    """

    def __init__(
        self,
        *,
        client: Any | None = None,
        at_date_fn=None,
        for_period_fn=None,
    ) -> None:
        if client is None and (at_date_fn is None or for_period_fn is None):
            raise ValueError("Provide a Supabase client or both *_fn callables")
        self._client = client
        self._at_date_fn = at_date_fn
        self._for_period_fn = for_period_fn

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve(self, query: ResolverQuery) -> list[ResolverRow]:
        """Return one row per norm, applicable to the query."""

        if query.kind == "at_date":
            rows = self._call_at_date(query.payload)
        elif query.kind == "for_period":
            rows = self._call_for_period(query.payload)
        else:
            raise ValueError(f"Unknown vigencia_query_kind: {query.kind!r}")
        return [ResolverRow.from_row(r) for r in rows]

    def state_for(self, norm_id: str, query: ResolverQuery) -> ResolverRow | None:
        """Return the resolver row for a single norm, or None if not found."""

        rows = self.resolve(query)
        for r in rows:
            if r.norm_id == norm_id:
                return r
        return None

    def demotion_factor_for(self, norm_id: str, query: ResolverQuery) -> float:
        """Convenience for the retriever — returns 0.0 if the norm has no history."""

        row = self.state_for(norm_id, query)
        if row is None:
            # No history → treat as unknown vigente. Tests prefer 1.0; production
            # callers may prefer 0.0. Default: 1.0 (don't penalize unrecorded
            # norms). The retriever can override.
            return 1.0
        return row.demotion_factor

    # ------------------------------------------------------------------
    # SQL plumbing
    # ------------------------------------------------------------------

    def _call_at_date(self, payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        if self._at_date_fn is not None:
            return list(self._at_date_fn(payload))
        as_of = payload.get("as_of_date") or date.today().isoformat()
        try:
            resp = self._client.rpc(
                "norm_vigencia_at_date",
                {"as_of_date": as_of},
            ).execute()
        except Exception as err:  # pragma: no cover
            LOGGER.warning("norm_vigencia_at_date RPC failed: %s", err)
            return []
        return list(getattr(resp, "data", None) or [])

    def _call_for_period(self, payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        if self._for_period_fn is not None:
            return list(self._for_period_fn(payload))
        impuesto = payload.get("impuesto") or "renta"
        periodo_year = int(payload.get("periodo_year") or date.today().year)
        periodo_label = payload.get("periodo_label")
        try:
            resp = self._client.rpc(
                "norm_vigencia_for_period",
                {
                    "impuesto": impuesto,
                    "periodo_year": periodo_year,
                    "periodo_label": periodo_label,
                },
            ).execute()
        except Exception as err:  # pragma: no cover
            LOGGER.warning("norm_vigencia_for_period RPC failed: %s", err)
            return []
        return list(getattr(resp, "data", None) or [])


# ---------------------------------------------------------------------------
# Planner cue extraction (called from pipeline_d/planner.py)
# ---------------------------------------------------------------------------


# Cues for "for_period" — look for AG / año gravable / período tag with year.
_PERIOD_RE = re.compile(
    r"\b(?:AG|a[ñn]o\s+gravable|per[ií]odo|periodo)\s*(?P<year>\d{4})\b",
    re.IGNORECASE,
)
_AT_DATE_RE = re.compile(
    r"\b(?:en|a|al|para|en el a[ñn]o|en el)\s+(?P<year>(?:19|20)\d{2})\b",
    re.IGNORECASE,
)
_IMPUESTO_KEYWORDS: dict[str, tuple[str, ...]] = {
    "renta": ("renta", "rentas", "impuesto sobre la renta", "rentas y complementarios"),
    "iva": ("iva", "impuesto sobre las ventas", "impuesto al valor agregado"),
    "retefuente": ("retefuente", "retención en la fuente", "retencion en la fuente"),
    "ica": ("ica", "industria y comercio"),
    "patrimonio": ("patrimonio", "impuesto al patrimonio"),
}


@dataclass(frozen=True)
class PlannerVigenciaCue:
    kind: str | None
    payload: Mapping[str, Any]


def extract_vigencia_cue(query: str, *, default_today: date | None = None) -> PlannerVigenciaCue:
    """Inspect a free-text query and return the vigencia cue, or kind=None.

    Per fixplan_v3 §0.6.3 + §1B-ε. The retriever then calls the matching
    resolver function via VigenciaResolver.
    """

    if not query or not query.strip():
        return PlannerVigenciaCue(kind=None, payload={})

    period = _PERIOD_RE.search(query)
    if period:
        impuesto = _infer_impuesto(query) or "renta"
        return PlannerVigenciaCue(
            kind="for_period",
            payload={
                "impuesto": impuesto,
                "periodo_year": int(period.group("year")),
                "periodo_label": period.group(0),
            },
        )

    at = _AT_DATE_RE.search(query)
    if at:
        year = int(at.group("year"))
        return PlannerVigenciaCue(
            kind="at_date",
            payload={"as_of_date": date(year, 12, 31).isoformat()},
        )

    return PlannerVigenciaCue(kind=None, payload={})


def _infer_impuesto(query: str) -> str | None:
    text = query.lower()
    for canonical, keywords in _IMPUESTO_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                return canonical
    return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
            except ValueError:
                return None
    return None


__all__ = [
    "PlannerVigenciaCue",
    "ResolverQuery",
    "ResolverRow",
    "VigenciaResolver",
    "extract_vigencia_cue",
]
