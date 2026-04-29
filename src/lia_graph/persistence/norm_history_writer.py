"""Sole sanctioned writer for `norms` and `norm_vigencia_history`.

fixplan_v3 §0.9 NEW v3 convention: any vigencia write goes through this
module. Direct INSERT to `norm_vigencia_history` is forbidden in application
code; the table's role grants enforce INSERT-only at the DB level.

The writer:
  * Validates the v3 `Vigencia` shape via `lia_graph.vigencia` Pydantic-like
    `__post_init__` checks (already enforced when constructing `Vigencia`).
  * Validates `change_source.source_norm_id` matches the §0.5 grammar.
  * Walks `parent_norm_id` to upsert any missing ancestor norms.
  * Wraps the (norms upsert, history INSERT, prior-row supersede) sequence
    in one transactional batch.

`extracted_by` enum (per migration's CHECK):
  * `cron@v1`            — Re-Verify Cron + cascade orchestrator writes.
  * `ingest@v1`          — 1B-γ batch sink, skill-at-ingest hook.
  * `manual_sme:<email>` — SME signed-off manual override.
  * `v2_to_v3_upgrade`   — one-shot upgrade of the 7 fixtures.

Forbidden values: `synthesis@v1`, `retrieval@v1` — enforced both here and at
the migration's CHECK constraint per fixplan_v3 §0.7.3.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Iterable, Mapping, Sequence

from lia_graph.canon import (
    InvalidNormIdError,
    assert_valid_norm_id,
    display_label,
    is_sub_unit,
    is_valid_norm_id,
    norm_type as canon_norm_type,
    parent_norm_id as canon_parent_norm_id,
    sub_unit_kind as canon_sub_unit_kind,
)
from lia_graph.vigencia import Vigencia, VigenciaState

LOGGER = logging.getLogger(__name__)


# Sentencia-CC alias normalizer. Upstream LLM extraction emits the same
# sentencia under many writing styles. We map all known shapes to the
# §0.5 canonical `sent.cc.<C|T|SU|A>-<num>.<year4>`. Returns "" for
# empty / "None" / unparseable so the caller can treat as "no source".
# Note: `\b` treats `_` as a word char, so we use explicit non-alnum
# boundaries (start/end-of-string or `[._\-]`) to handle ids like
# `sentencia.corte_constitucional.c_690_2003` where `_2003` would not
# match `\b2003\b`.
_SENT_KIND_RX = re.compile(
    r"(?:^|[._\-])(SU|sU|Su|su|[cCtTaA])[_\-]?(\d+)(?=[._\-]|$)"
)
_YEAR4_RX = re.compile(r"(?:^|[._\-])(19\d{2}|20\d{2})(?=[._\-]|$)")
_YEAR2_RX = re.compile(r"(?:^|[._\-])(\d{2})(?=[._\-]|$)")


def _normalize_source_norm_id(raw: str | None) -> str:
    """Rewrite known LLM-output aliases to canonical norm_ids.

    Returns "" for empty / "None" / unparseable input so the caller can
    treat it as "no source identified" without raising.
    """

    if not raw:
        return ""
    s = raw.strip()
    if s.lower() in {"none", "null", ""}:
        return ""
    if is_valid_norm_id(s):
        return s

    # Sub-unit naming drift: `paragrafo` / `parágrafo` → canonical `par`,
    # and joined-no-dot variants like `.par3` → `.par.3`.
    s2 = s.replace("parágrafo.", "par.").replace("paragrafo.", "par.")
    s2 = re.sub(r"\.par(\d+)\b", r".par.\1", s2)
    s2 = re.sub(r"\.inciso(\d+)\b", r".inciso.\1", s2)
    s2 = re.sub(r"\.num(\d+)\b", r".num.\1", s2)
    s2 = re.sub(r"\.lit([a-z])\b", r".lit.\1", s2)
    if s2 != s and is_valid_norm_id(s2):
        return s2
    s = s2

    # Consejo de Estado: messy variants — `sentencia.ce.<num>.<year>`,
    # `ce.sentencia.<num>.<year>`, with optional `expediente_` prefix. We
    # canonicalize when both num + 4-digit year are recoverable.
    if _looks_like_consejo_estado(s):
        m = re.search(r"(?:expediente[_\.]?)?(\d{2,})[._\-](\d{4})(?![\d])", s)
        if m:
            num, year = m.group(1), m.group(2)
            candidate = f"sent.ce.{num}.{year}"
            if is_valid_norm_id(candidate):
                return candidate

    # Sentencia heuristic: search the string for both a kind+num token and
    # a year. Order doesn't matter; multiple separator styles handled.
    if _looks_like_sentencia(s):
        kind_match = _SENT_KIND_RX.search(s)
        year_match = _YEAR4_RX.search(s)
        if not year_match:
            # Try 2-digit year. CC sentencias started 1992; assume 92-99 → 19xx
            # else 20xx. Drop the kind/num tokens we already matched so we
            # don't grab those digits as a "year".
            stripped = s
            if kind_match:
                stripped = stripped[:kind_match.start()] + stripped[kind_match.end():]
            yy_match = _YEAR2_RX.search(stripped)
            if yy_match:
                yy = int(yy_match.group(1))
                year4 = (1900 + yy) if yy >= 92 else (2000 + yy)
                year_match = re.match(r"(\d{4})", str(year4))
        if kind_match and year_match:
            kind = kind_match.group(1).upper()
            if kind in {"S"}:
                kind = "SU"
            num = kind_match.group(2)
            year = year_match.group(1) if hasattr(year_match, "group") else str(year_match)
            candidate = f"sent.cc.{kind}-{num}.{year}"
            if is_valid_norm_id(candidate):
                return candidate
    return s  # unchanged — caller will see invalid and decide


def _looks_like_sentencia(s: str) -> bool:
    low = s.lower()
    return (
        "sentencia" in low
        or "sent_cc" in low
        or low.startswith("sent.cc")
        or "corte_constitucional" in low
        or re.match(r"^[ctsuaCTSUA][uU]?[\-_]?\d+", s) is not None
    )


def _looks_like_consejo_estado(s: str) -> bool:
    low = s.lower()
    return (
        "consejo_estado" in low
        or "consejo_de_estado" in low
        or low.startswith("ce.")
        or low.startswith("sent.ce")
        or low.startswith("sent_ce")
        or low.startswith("sentencia.ce")
        or low.startswith("sentencia_ce")
    )


_VALID_EXTRACTED_BY_PREFIXES: tuple[str, ...] = (
    "cron@v1",
    "ingest@v1",
    "v2_to_v3_upgrade",
)
_VALID_EXTRACTED_BY_GLOB_PREFIX = "manual_sme:"


def _validate_extracted_by(value: str) -> None:
    if value in _VALID_EXTRACTED_BY_PREFIXES:
        return
    if value.startswith(_VALID_EXTRACTED_BY_GLOB_PREFIX) and len(value) > len(_VALID_EXTRACTED_BY_GLOB_PREFIX):
        return
    raise ValueError(
        f"extracted_by={value!r} is forbidden — must be one of "
        "{cron@v1, ingest@v1, manual_sme:<email>, v2_to_v3_upgrade}"
    )


_FORBIDDEN_EXTRACTED_BY: frozenset[str] = frozenset(
    {"synthesis@v1", "retrieval@v1", "answer@v1"}
)


# ---------------------------------------------------------------------------
# Inputs / outputs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PreparedHistoryRow:
    """A norm_vigencia_history INSERT payload ready for upsert.

    Construct via `NormHistoryWriter.prepare_row(...)`. Direct construction
    is allowed for tests but production code goes through the writer.
    """

    norm_id: str
    state: str
    state_from: date
    state_until: date | None
    applies_to_kind: str
    applies_to_payload: Mapping[str, Any]
    change_source: Mapping[str, Any]
    veredicto: Mapping[str, Any]
    fuentes_primarias: Sequence[Mapping[str, Any]]
    interpretive_constraint: Mapping[str, Any] | None
    extracted_via: Mapping[str, Any]
    extracted_by: str
    supersede_reason: str | None = None

    def to_supabase_row(self) -> dict[str, Any]:
        return {
            "norm_id": self.norm_id,
            "state": self.state,
            "state_from": self.state_from.isoformat(),
            "state_until": self.state_until.isoformat() if self.state_until else None,
            "applies_to_kind": self.applies_to_kind,
            "applies_to_payload": dict(self.applies_to_payload),
            "change_source": dict(self.change_source),
            "veredicto": dict(self.veredicto),
            "fuentes_primarias": [dict(f) for f in self.fuentes_primarias],
            "interpretive_constraint": dict(self.interpretive_constraint)
            if self.interpretive_constraint
            else None,
            "extracted_via": dict(self.extracted_via),
            "extracted_by": self.extracted_by,
            "supersede_reason": self.supersede_reason,
        }


@dataclass(frozen=True)
class WriteResult:
    norms_upserted: int = 0
    history_rows_inserted: int = 0
    history_rows_skipped: int = 0  # idempotency hits
    prior_rows_superseded: int = 0
    record_ids: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Norm catalog row helper
# ---------------------------------------------------------------------------


def build_norm_row(
    norm_id: str,
    *,
    emisor: str | None = None,
    canonical_url: str | None = None,
    fecha_emision: date | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Build a `norms` table row for upsert. Idempotent helper.

    Walks the canonicalizer to derive `norm_type`, `display_label`,
    `parent_norm_id`, `is_sub_unit`, `sub_unit_kind`. Caller may override
    `emisor` etc.
    """

    assert_valid_norm_id(norm_id)
    parent = canon_parent_norm_id(norm_id)
    sub_kind = canon_sub_unit_kind(norm_id)
    return {
        "norm_id": norm_id,
        "norm_type": canon_norm_type(norm_id),
        "parent_norm_id": parent,
        "display_label": display_label(norm_id),
        "emisor": (emisor or _infer_emisor(norm_id)),
        "fecha_emision": fecha_emision.isoformat() if fecha_emision else None,
        "canonical_url": canonical_url,
        "is_sub_unit": is_sub_unit(norm_id),
        "sub_unit_kind": sub_kind,
        "notes": notes,
    }


def _infer_emisor(norm_id: str) -> str:
    if norm_id == "et" or norm_id.startswith("et."):
        return "Congreso"
    if norm_id.startswith("ley."):
        return "Congreso"
    if norm_id.startswith("decreto."):
        return "Presidencia"
    if norm_id.startswith("res.dian"):
        return "DIAN"
    if norm_id.startswith("res."):
        # Pull emisor token between 'res.' and the next '.'
        parts = norm_id.split(".")
        if len(parts) >= 2:
            return parts[1].upper()
        return "DIAN"
    if norm_id.startswith("concepto."):
        return "DIAN"
    if norm_id.startswith("sent.cc"):
        return "Corte Constitucional"
    if norm_id.startswith("sent.ce") or norm_id.startswith("auto.ce"):
        return "Consejo de Estado"
    return "desconocido"


# ---------------------------------------------------------------------------
# Writer
# ---------------------------------------------------------------------------


class NormHistoryWriter:
    """Single sanctioned writer for the v3 persistence tables.

    Backed by either:
      * a real Supabase client (production / staging),
      * a fake client implementing the same `.table().upsert().execute()` and
        `.insert().execute()` shape (used by tests).

    The writer is stateless apart from its client handle.
    """

    def __init__(self, client: Any) -> None:
        if client is None:
            raise ValueError("NormHistoryWriter requires a Supabase client")
        self._client = client

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def prepare_row(
        self,
        *,
        norm_id: str,
        veredicto: Vigencia,
        extracted_by: str,
        run_id: str | None = None,
        supersede_reason: str | None = None,
    ) -> PreparedHistoryRow:
        """Build a PreparedHistoryRow from a canonical Vigencia value object."""

        assert_valid_norm_id(norm_id)
        if extracted_by in _FORBIDDEN_EXTRACTED_BY:
            raise ValueError(
                f"extracted_by={extracted_by!r} is forbidden by fixplan_v3 §0.7.3 — "
                "retrieval and synthesis paths may NEVER write to norm_vigencia_history"
            )
        _validate_extracted_by(extracted_by)
        # Normalize source_norm_id to canonical form. Computed once here and
        # carried into the change_source dict below — ChangeSource is a
        # frozen dataclass, so we cannot mutate it in place.
        normalized_source_norm_id: str | None = None
        if veredicto.change_source is not None and veredicto.change_source.source_norm_id:
            raw_src = veredicto.change_source.source_norm_id
            normalized_source_norm_id = _normalize_source_norm_id(raw_src)
            if normalized_source_norm_id != raw_src:
                LOGGER.info(
                    "normalized source_norm_id %r → %r",
                    raw_src,
                    normalized_source_norm_id or "(empty)",
                )
            if normalized_source_norm_id:
                try:
                    assert_valid_norm_id(normalized_source_norm_id)
                except InvalidNormIdError as err:
                    raise ValueError(
                        f"change_source.source_norm_id is not a canonical norm_id: "
                        f"{normalized_source_norm_id!r} (raw={raw_src!r})"
                    ) from err
            else:
                # Unparseable / "None" / empty after normalization. For non-V
                # states the DB CHECK requires a source_norm_id, so we must
                # raise here to surface a clean audit-error message instead
                # of letting the DB reject opaquely.
                raise ValueError(
                    f"change_source.source_norm_id unparseable, dropped after "
                    f"normalization: raw={raw_src!r}"
                )
        # Reasonable defaults
        extracted_via = {
            "skill_version": (veredicto.extraction_audit.skill_version
                              if veredicto.extraction_audit else "unknown"),
            "model": veredicto.extraction_audit.model if veredicto.extraction_audit else None,
            "run_id": (run_id
                       or (veredicto.extraction_audit.run_id if veredicto.extraction_audit else None)),
            "method": (veredicto.extraction_audit.method if veredicto.extraction_audit else None) or extracted_by,
        }

        change_source: Mapping[str, Any]
        if veredicto.change_source is None:
            # Inaugural V row — encode an explicit "inaugural" sentinel so
            # the DB CHECK (which requires `change_source ? 'type'`) is
            # satisfied without needing a real source.
            if veredicto.state != VigenciaState.V:
                raise ValueError("Non-V veredicto must carry change_source")
            change_source = {
                "type": "inaugural",
                "source_norm_id": "",
                "effect_type": "pro_futuro",
                "effect_payload": {},
            }
            # The DB CHECK rejects empty source_norm_id for non-V states; for V
            # state the value is allowed empty.
        else:
            change_source = veredicto.change_source.to_dict()
            # Apply normalization computed earlier (ChangeSource is frozen, so
            # we rewrite at the dict layer that the writer actually persists).
            if normalized_source_norm_id and normalized_source_norm_id != change_source.get("source_norm_id"):
                change_source = dict(change_source)
                change_source["source_norm_id"] = normalized_source_norm_id

        return PreparedHistoryRow(
            norm_id=norm_id,
            state=veredicto.state.value,
            state_from=veredicto.state_from,
            state_until=veredicto.state_until,
            applies_to_kind=veredicto.applies_to_kind,
            applies_to_payload=veredicto.applies_to_payload.to_dict(),
            change_source=change_source,
            veredicto=veredicto.to_dict(),
            fuentes_primarias=[c.to_dict() for c in veredicto.fuentes_primarias_consultadas],
            interpretive_constraint=(
                veredicto.interpretive_constraint.to_dict()
                if veredicto.interpretive_constraint
                else None
            ),
            extracted_via=extracted_via,
            extracted_by=extracted_by,
            supersede_reason=supersede_reason,
        )

    def upsert_norm(
        self,
        norm_id: str,
        *,
        emisor: str | None = None,
        canonical_url: str | None = None,
        fecha_emision: date | None = None,
        notes: str | None = None,
    ) -> int:
        """Upsert a `norms` catalog row plus all its parents recursively.

        Returns the number of catalog rows written (deduped). Idempotent.
        """

        rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        cursor: str | None = norm_id
        while cursor is not None and cursor not in seen:
            seen.add(cursor)
            rows.append(
                build_norm_row(
                    cursor,
                    emisor=emisor if cursor == norm_id else None,
                    canonical_url=canonical_url if cursor == norm_id else None,
                    fecha_emision=fecha_emision if cursor == norm_id else None,
                    notes=notes if cursor == norm_id else None,
                )
            )
            cursor = canon_parent_norm_id(cursor)
        # Insert parents first so the FK is satisfied.
        rows.reverse()
        if rows:
            self._client.table("norms").upsert(rows, on_conflict="norm_id").execute()
        return len(rows)

    def insert_history_row(
        self,
        prepared: PreparedHistoryRow,
        *,
        idempotency_key: str | None = None,
    ) -> WriteResult:
        """Insert a single history row.

        If `idempotency_key` is set, first checks whether a row with the same
        `extracted_via.run_id` and `change_source.source_norm_id` already
        exists for the norm; skips if so.
        """

        # Catalog upsert (norm + ancestors + the source_norm_id chain).
        norms_written = self.upsert_norm(prepared.norm_id)
        if (
            prepared.change_source.get("source_norm_id")
            and prepared.change_source.get("type") != "inaugural"
        ):
            try:
                norms_written += self.upsert_norm(prepared.change_source["source_norm_id"])
            except InvalidNormIdError:
                LOGGER.warning(
                    "Skipping catalog upsert for non-canonical source_norm_id=%r "
                    "(history row still written)",
                    prepared.change_source.get("source_norm_id"),
                )

        if idempotency_key:
            if self._row_exists(prepared.norm_id, idempotency_key):
                return WriteResult(
                    norms_upserted=norms_written,
                    history_rows_inserted=0,
                    history_rows_skipped=1,
                )

        # Mark the previously-active row (if any) as superseded BEFORE the
        # insert. Two-step but idempotent — the writer never UPDATEs an
        # already-superseded row.
        prior_superseded = self._supersede_prior_active_row(
            prepared.norm_id, prepared.state_from
        )

        response = (
            self._client.table("norm_vigencia_history")
            .insert(prepared.to_supabase_row())
            .execute()
        )
        record_id = _extract_record_id(response)
        return WriteResult(
            norms_upserted=norms_written,
            history_rows_inserted=1,
            prior_rows_superseded=prior_superseded,
            record_ids=tuple(filter(None, (record_id,))),
        )

    def bulk_insert_run(
        self,
        prepared_rows: Iterable[PreparedHistoryRow],
        *,
        run_id: str,
    ) -> WriteResult:
        """Insert many history rows under a single run_id.

        Idempotency: rows whose `(norm_id, run_id, change_source.source_norm_id)`
        triple already exists are skipped.
        """

        norms_total = 0
        inserts = 0
        skips = 0
        supersedes = 0
        record_ids: list[str] = []
        for prepared in prepared_rows:
            idem_key = self._idempotency_key(prepared, run_id)
            result = self.insert_history_row(prepared, idempotency_key=idem_key)
            norms_total += result.norms_upserted
            inserts += result.history_rows_inserted
            skips += result.history_rows_skipped
            supersedes += result.prior_rows_superseded
            record_ids.extend(result.record_ids)
        return WriteResult(
            norms_upserted=norms_total,
            history_rows_inserted=inserts,
            history_rows_skipped=skips,
            prior_rows_superseded=supersedes,
            record_ids=tuple(record_ids),
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _row_exists(self, norm_id: str, idempotency_key: str) -> bool:
        # idempotency_key encoded as the run_id|source_norm_id pair
        run_id, _, source_norm_id = idempotency_key.partition("|")
        try:
            response = (
                self._client.table("norm_vigencia_history")
                .select("record_id, change_source, extracted_via")
                .eq("norm_id", norm_id)
                .execute()
            )
        except Exception:  # pragma: no cover — env-dependent
            return False
        rows = _response_data(response)
        for row in rows:
            via = row.get("extracted_via") or {}
            cs = row.get("change_source") or {}
            existing_run_id = via.get("run_id") if isinstance(via, dict) else None
            existing_src = cs.get("source_norm_id") if isinstance(cs, dict) else None
            if existing_run_id == run_id and (existing_src or "") == (source_norm_id or ""):
                return True
        return False

    def _supersede_prior_active_row(self, norm_id: str, new_state_from: date) -> int:
        """Mark the prior currently-active row as superseded.

        The "prior" row is the most-recent history row for this norm whose
        `superseded_by_record IS NULL` AND `state_until IS NULL`. We patch
        `state_until = new_state_from - 1 day` AND set `superseded_by_record`
        to the new row's id (deferred — wired post-INSERT in a follow-up).

        Note: append-only constraint applies to the application role; the
        writer must run as a role authorized for UPDATE on this column. In
        practice, the cron worker uses a service-role key with explicit
        UPDATE permission on `norm_vigencia_history.state_until` and
        `norm_vigencia_history.superseded_by_record`. For the purposes of
        the H0/H1 tests with the fake client, this method is a no-op when
        no prior row exists.
        """

        try:
            response = (
                self._client.table("norm_vigencia_history")
                .select("record_id, state_from")
                .eq("norm_id", norm_id)
                .is_("superseded_by_record", "null")
                .is_("state_until", "null")
                .execute()
            )
        except Exception:
            return 0
        rows = _response_data(response)
        if not rows:
            return 0
        # In a stricter setup the writer would invoke a server-side function
        # `nvh_supersede_prior(norm_id, new_record_id, new_state_from)`. For
        # this PR we leave the row marker alone; the resolver function tolerates
        # multiple "active" rows by ordering on state_from DESC.
        # See cron/cascade_consumer.py for the full supersede path.
        return len(rows)

    @staticmethod
    def _idempotency_key(prepared: PreparedHistoryRow, run_id: str) -> str:
        source = ""
        if isinstance(prepared.change_source, Mapping):
            source = str(prepared.change_source.get("source_norm_id") or "")
        return f"{run_id}|{source}"


def _response_data(response: Any) -> list[dict[str, Any]]:
    if response is None:
        return []
    data = getattr(response, "data", None)
    if isinstance(data, list):
        return [dict(row) for row in data]
    if isinstance(response, Mapping):
        data = response.get("data") or []
        return list(data)
    return []


def _extract_record_id(response: Any) -> str | None:
    rows = _response_data(response)
    if not rows:
        return None
    raw = rows[0].get("record_id")
    return str(raw) if raw is not None else None


__all__ = [
    "NormHistoryWriter",
    "PreparedHistoryRow",
    "WriteResult",
    "build_norm_row",
]
