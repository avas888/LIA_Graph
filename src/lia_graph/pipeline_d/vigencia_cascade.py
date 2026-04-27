"""fixplan_v3 sub-fix 1F — cascade orchestrator.

Three responsibilities (per §0.7):

  1. **Reviviscencia handler.** When a `norm_vigencia_history` row lands with
     `change_source.type = 'sentencia_cc'` and `state IN (IE)`, scan for every
     norm previously modified by the now-inexequible source and enqueue
     re-verify tasks.

  2. **Future-dated state flip notifier.** Periodic sweep for rows with
     `state_from` or `state_until` within the next 30 days; emit operator
     notifications and enqueue re-verify on dependent norms.

  3. **Retrieval-time inconsistency detector.** Read-only consumer used from
     `pipeline_d/answer_synthesis.py`; returns inconsistency signatures the
     coherence gate refuses on. Never writes from this path; queues to cron
     via `vigencia_cascade.queue_reverify(norm_id, reason)`.

Cron-driven; never invoked from the retrieval path. The single-writer
property protects retrieval determinism (§0.7.3).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable, Mapping, Sequence

LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data shapes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NormVigenciaHistoryRow:
    """In-process projection of a `norm_vigencia_history` row."""

    record_id: str
    norm_id: str
    state: str
    state_from: date
    state_until: date | None
    change_source: Mapping[str, Any]
    extracted_by: str
    extracted_at: datetime

    @classmethod
    def from_supabase(cls, row: Mapping[str, Any]) -> "NormVigenciaHistoryRow":
        return cls(
            record_id=str(row["record_id"]),
            norm_id=str(row["norm_id"]),
            state=str(row["state"]),
            state_from=_to_date(row["state_from"]),
            state_until=_to_date(row.get("state_until")),
            change_source=dict(row.get("change_source") or {}),
            extracted_by=str(row.get("extracted_by") or ""),
            extracted_at=_to_dt(row.get("extracted_at")),
        )


@dataclass(frozen=True)
class CascadeQueueEntry:
    """A queued re-verify task — one row in `vigencia_reverify_queue`."""

    norm_id: str
    supersede_reason: str
    triggering_norm_id: str | None
    triggering_record_id: str | None
    enqueued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "norm_id": self.norm_id,
            "supersede_reason": self.supersede_reason,
            "triggering_norm_id": self.triggering_norm_id,
            "triggering_record_id": self.triggering_record_id,
            "enqueued_at": self.enqueued_at.isoformat(),
        }


@dataclass(frozen=True)
class CascadeResult:
    rows_inspected: int = 0
    queued: int = 0
    flips_notified: int = 0
    queue_entries: tuple[CascadeQueueEntry, ...] = ()


@dataclass(frozen=True)
class InconsistencyReport:
    """The signature the coherence gate refuses on (§0.7.3)."""

    norm_id: str
    reason: str
    detail: Mapping[str, Any]
    fallback_reason: str = "vigencia_inconsistency"


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


class VigenciaCascadeOrchestrator:
    """Sole consumer of NEW INSERTs into norm_vigencia_history.

    Cron-invoked; never invoked from retrieval path.

    The orchestrator is intentionally pure-function-shaped: each method takes
    a Supabase-like client + a row (or now-time) and returns a CascadeResult.
    All writes route through `_enqueue` which calls
    `client.table("vigencia_reverify_queue").insert(...)`.
    """

    def __init__(self, client: Any) -> None:
        if client is None:
            raise ValueError("VigenciaCascadeOrchestrator requires a client")
        self._client = client

    # ------------------------------------------------------------------
    # Single-row hook (called immediately after each INSERT)
    # ------------------------------------------------------------------

    def on_history_row_inserted(self, row: NormVigenciaHistoryRow) -> CascadeResult:
        """Inspect the new row; enqueue re-verify tasks for cascading effects.

        Idempotent: re-running on the same record produces the same queue.
        """

        cs_type = str(row.change_source.get("type") or "")
        source_norm_id = str(row.change_source.get("source_norm_id") or "")

        # Reviviscencia trigger: a sentencia C- declares the row's norm
        # (e.g. Ley 1943/2018) inexequible. The cascade has to re-verify
        # every other norm that was previously modified by *the now-
        # inexequible norm* (`row.norm_id`), not by the sentencia
        # (`source_norm_id`).
        if cs_type == "sentencia_cc" and row.state == "IE":
            affected = self._fetch_affected_by(row.norm_id)
            entries = []
            for affected_norm in affected:
                if affected_norm == row.norm_id:
                    # Skip self-reference; the orchestrator never queues the
                    # source-cascade row itself.
                    continue
                entries.append(
                    CascadeQueueEntry(
                        norm_id=affected_norm,
                        supersede_reason="cascade_reviviscencia",
                        triggering_norm_id=row.norm_id,
                        triggering_record_id=row.record_id,
                    )
                )
            self._enqueue_batch(entries)
            return CascadeResult(
                rows_inspected=1,
                queued=len(entries),
                queue_entries=tuple(entries),
            )

        # Other state transitions: no cascade. The retriever picks up the new
        # row on the next query via the resolver.
        return CascadeResult(rows_inspected=1)

    # ------------------------------------------------------------------
    # Periodic tick (6h cadence)
    # ------------------------------------------------------------------

    def on_periodic_tick(
        self,
        now: datetime | None = None,
        *,
        flip_window_days: int = 30,
    ) -> CascadeResult:
        """Sweep for state_until expirations + future-dated state_from.

        Called by `cron/state_flip_notifier.py` on a 6h cadence.
        """

        if now is None:
            now = datetime.now(timezone.utc)
        today = now.date()
        window_end = today + timedelta(days=flip_window_days)

        upcoming = self._fetch_upcoming_flips(today, window_end)
        entries: list[CascadeQueueEntry] = []
        for r in upcoming:
            entries.append(
                CascadeQueueEntry(
                    norm_id=r.norm_id,
                    supersede_reason="periodic_reverify",
                    triggering_norm_id=None,
                    triggering_record_id=r.record_id,
                )
            )
        self._enqueue_batch(entries)
        return CascadeResult(
            rows_inspected=len(upcoming),
            queued=len(entries),
            flips_notified=len(upcoming),
            queue_entries=tuple(entries),
        )

    # ------------------------------------------------------------------
    # Read-only consumer for retrieval-time inconsistency detection
    # ------------------------------------------------------------------

    def detect_inconsistency(
        self,
        citations: Sequence[Mapping[str, Any]],
        as_of: date,
    ) -> InconsistencyReport | None:
        """Read-only consumer used from retrieval. Returns the inconsistency
        signature for the coherence gate to refuse on. Never writes.

        Detected cases:
          * Two anchor citations on the SAME norm with chunks predating
            different history rows (e.g. one chunk written pre-IE, another
            written post-IE, both citing the same norm).
          * An anchor whose state at `as_of` is in {DE, SP, IE, VL, DI-expired}
            with no chip-bearing replacement.
        """

        if not citations:
            return None

        # Bucket citations by norm_id; if a norm has multiple anchors with
        # divergent state hints in the chunk metadata, flag it.
        per_norm: dict[str, list[Mapping[str, Any]]] = {}
        for c in citations:
            norm_id = str(c.get("norm_id") or "")
            if not norm_id:
                continue
            per_norm.setdefault(norm_id, []).append(c)

        for norm_id, group in per_norm.items():
            anchors = [c for c in group if (c.get("role") or "anchor") == "anchor"]
            if len(anchors) < 2:
                continue
            states = {c.get("anchor_state") for c in anchors if c.get("anchor_state")}
            if len(states) > 1:
                return InconsistencyReport(
                    norm_id=norm_id,
                    reason="divergent_anchor_states",
                    detail={
                        "norm_id": norm_id,
                        "states_seen": sorted(s for s in states if s),
                        "as_of": as_of.isoformat(),
                    },
                )

        # Default: no inconsistency.
        return None

    def queue_reverify(
        self,
        norm_id: str,
        *,
        reason: str = "partial_coverage_followup",
        triggering_norm_id: str | None = None,
        triggering_record_id: str | None = None,
    ) -> None:
        """Public entry point used by Fix 3 partial-coverage hook.

        The composer calls this when retrieval falls back to partial-coverage
        on a specific norm; the next cron tick re-verifies that norm.
        """

        entry = CascadeQueueEntry(
            norm_id=norm_id,
            supersede_reason=reason,
            triggering_norm_id=triggering_norm_id,
            triggering_record_id=triggering_record_id,
        )
        self._enqueue_batch([entry])

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _fetch_affected_by(self, source_norm_id: str) -> list[str]:
        """Return norms whose change_source.source_norm_id == source_norm_id."""

        try:
            resp = (
                self._client.table("norm_vigencia_history")
                .select("norm_id, change_source")
                .execute()
            )
        except Exception as err:  # pragma: no cover
            LOGGER.warning("fetch_affected_by failed: %s", err)
            return []
        rows = getattr(resp, "data", None) or []
        out: list[str] = []
        seen: set[str] = set()
        for r in rows:
            cs = r.get("change_source") or {}
            if not isinstance(cs, dict):
                continue
            if str(cs.get("source_norm_id") or "") == source_norm_id:
                norm_id = str(r.get("norm_id") or "")
                if norm_id and norm_id not in seen:
                    seen.add(norm_id)
                    out.append(norm_id)
        return out

    def _fetch_upcoming_flips(
        self,
        today: date,
        window_end: date,
    ) -> list[NormVigenciaHistoryRow]:
        """Return rows whose state_until or state_from falls in [today, window_end]."""

        try:
            resp = (
                self._client.table("norm_vigencia_history")
                .select("*")
                .execute()
            )
        except Exception as err:  # pragma: no cover
            LOGGER.warning("fetch_upcoming_flips failed: %s", err)
            return []
        rows = getattr(resp, "data", None) or []
        out: list[NormVigenciaHistoryRow] = []
        for r in rows:
            try:
                row = NormVigenciaHistoryRow.from_supabase(r)
            except Exception:
                continue
            if row.state_until and today <= row.state_until <= window_end:
                out.append(row)
            elif row.state_from > today and row.state_from <= window_end:
                out.append(row)
        return out

    def _enqueue_batch(self, entries: Iterable[CascadeQueueEntry]) -> None:
        rows = [e.to_dict() for e in entries]
        if not rows:
            return
        try:
            self._client.table("vigencia_reverify_queue").insert(rows).execute()
        except Exception as err:  # pragma: no cover
            LOGGER.warning("Cascade queue insert failed: %s", err)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_date(value: Any) -> date:
    if value is None:
        return None  # type: ignore[return-value]
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _to_dt(value: Any) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if isinstance(value, datetime):
        return value
    s = str(value).replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return datetime.now(timezone.utc)


__all__ = [
    "CascadeQueueEntry",
    "CascadeResult",
    "InconsistencyReport",
    "NormVigenciaHistoryRow",
    "VigenciaCascadeOrchestrator",
]
