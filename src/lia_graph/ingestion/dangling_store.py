"""Persistent dangling-edge-candidate store (Decision D1).

See ``docs/next/additive_corpusv1.md`` §4 Decision D1 and §5 Phase 4.

Edges whose target ARTICLE key is unresolved at the moment an edge is
extracted would, under the legacy full-rebuild, be silently dropped by
``normalize_classified_edges`` (see §3.5). Under additive that drop becomes
incorrect: an edge whose target is about to arrive in a future delta would
never be promoted. This module persists those candidates so that each
subsequent delta can consult the store, promote candidates whose target has
since arrived, and record any new dangling references for later.

The store is scoped to ``target_kind=ARTICLE`` per §3.5. Other target kinds
(SUBTOPIC, REFORM, DOCUMENT, …) are either always-present or minted inline
by their own pass.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence


@dataclass(frozen=True)
class DanglingCandidate:
    """A single unresolved-target edge candidate."""

    source_key: str
    target_key: str
    relation: str
    source_doc_id: str | None = None
    raw_reference: str | None = None

    def key(self) -> tuple[str, str, str]:
        return (self.source_key, self.target_key, self.relation)


@dataclass(frozen=True)
class DanglingRow:
    """Row shape returned by the store."""

    source_key: str
    target_key: str
    relation: str
    source_doc_id: str | None
    first_seen_delta_id: str | None
    last_seen_delta_id: str | None
    raw_reference: str | None


def _row_to_dangling(row: Mapping[str, Any]) -> DanglingRow:
    return DanglingRow(
        source_key=str(row.get("source_key") or ""),
        target_key=str(row.get("target_key") or ""),
        relation=str(row.get("relation") or ""),
        source_doc_id=_optional_str(row.get("source_doc_id")),
        first_seen_delta_id=_optional_str(row.get("first_seen_delta_id")),
        last_seen_delta_id=_optional_str(row.get("last_seen_delta_id")),
        raw_reference=_optional_str(row.get("raw_reference")),
    )


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


class DanglingStore:
    """Wraps ``normative_edge_candidates_dangling``."""

    TABLE_NAME = "normative_edge_candidates_dangling"

    def __init__(self, client: Any) -> None:
        self._client = client

    # ---- reads --------------------------------------------------------

    def load_for_target_keys(
        self, target_keys: Iterable[str]
    ) -> dict[str, list[DanglingRow]]:
        """Return all candidates grouped by ``target_key``.

        Input strings are deduplicated before querying. Returns an empty dict
        when the input iterable is empty (no PostgREST call).
        """
        keys = [k for k in {str(k).strip() for k in target_keys if k} if k]
        if not keys:
            return {}
        resp = (
            self._client.table(self.TABLE_NAME)
            .select(
                "source_key, target_key, relation, source_doc_id, "
                "first_seen_delta_id, last_seen_delta_id, raw_reference"
            )
            .in_("target_key", keys)
            .execute()
        )
        rows = list(getattr(resp, "data", None) or [])
        grouped: dict[str, list[DanglingRow]] = {}
        for raw in rows:
            dang = _row_to_dangling(raw)
            grouped.setdefault(dang.target_key, []).append(dang)
        return grouped

    # ---- writes -------------------------------------------------------

    def upsert_candidates(
        self,
        candidates: Sequence[DanglingCandidate],
        *,
        delta_id: str,
    ) -> int:
        """Upsert N candidates; advance ``last_seen_delta_id`` on conflicts.

        On conflict (existing primary key), the store:
        * does NOT overwrite ``first_seen_delta_id`` — the original delta wins;
        * DOES overwrite ``last_seen_delta_id`` to the current delta;
        * refreshes ``raw_reference`` + ``source_doc_id`` with the latest
          observation.
        """
        payloads: list[dict[str, Any]] = []
        for cand in candidates:
            if not cand.source_key or not cand.target_key or not cand.relation:
                continue
            payloads.append(
                {
                    "source_key": cand.source_key,
                    "target_key": cand.target_key,
                    "relation": cand.relation,
                    "source_doc_id": cand.source_doc_id,
                    "first_seen_delta_id": delta_id,
                    "last_seen_delta_id": delta_id,
                    "raw_reference": cand.raw_reference,
                }
            )
        if not payloads:
            return 0

        # Pre-existing rows win the first_seen fight: load them first and
        # splice their first_seen_delta_id into the payload so the upsert
        # doesn't stomp history.
        keys = {(p["source_key"], p["target_key"], p["relation"]) for p in payloads}
        existing = self._load_exact(keys)
        for payload in payloads:
            key = (payload["source_key"], payload["target_key"], payload["relation"])
            prior = existing.get(key)
            if prior is not None and prior.first_seen_delta_id:
                payload["first_seen_delta_id"] = prior.first_seen_delta_id

        self._client.table(self.TABLE_NAME).upsert(
            payloads, on_conflict="source_key,target_key,relation"
        ).execute()
        return len(payloads)

    def delete_promoted(
        self,
        candidates: Sequence[DanglingCandidate],
    ) -> int:
        """Delete rows matching the supplied candidate keys."""
        n = 0
        for cand in candidates:
            if not cand.source_key or not cand.target_key or not cand.relation:
                continue
            self._client.table(self.TABLE_NAME).delete().eq(
                "source_key", cand.source_key
            ).eq("target_key", cand.target_key).eq(
                "relation", cand.relation
            ).execute()
            n += 1
        return n

    def gc_older_than(self, delta_id_threshold: str) -> int:
        """Delete rows whose ``last_seen_delta_id`` is lexicographically
        older than ``delta_id_threshold``.

        delta_ids follow the ``delta_YYYYMMDD_HHMMSS_xxxxxx`` shape, which
        sorts in time order, so the lexicographic comparison matches the
        temporal intent. Operator-driven; no automatic schedule in v1
        (§7 Out of Scope / Risk follow-up).
        """
        resp = (
            self._client.table(self.TABLE_NAME)
            .delete()
            .lt("last_seen_delta_id", delta_id_threshold)
            .execute()
        )
        data = list(getattr(resp, "data", None) or [])
        return len(data)

    # ---- internal -----------------------------------------------------

    def _load_exact(
        self, keys: Iterable[tuple[str, str, str]]
    ) -> dict[tuple[str, str, str], DanglingRow]:
        keys_list = list(keys)
        if not keys_list:
            return {}
        # PostgREST doesn't expose a composite IN; we paginate by source_key.
        by_source: dict[str, list[tuple[str, str, str]]] = {}
        for src, tgt, rel in keys_list:
            by_source.setdefault(src, []).append((src, tgt, rel))
        out: dict[tuple[str, str, str], DanglingRow] = {}
        for source_key, rows in by_source.items():
            resp = (
                self._client.table(self.TABLE_NAME)
                .select(
                    "source_key, target_key, relation, source_doc_id, "
                    "first_seen_delta_id, last_seen_delta_id, raw_reference"
                )
                .eq("source_key", source_key)
                .execute()
            )
            for raw in list(getattr(resp, "data", None) or []):
                dang = _row_to_dangling(raw)
                out[(dang.source_key, dang.target_key, dang.relation)] = dang
        return out


__all__ = [
    "DanglingCandidate",
    "DanglingRow",
    "DanglingStore",
]
