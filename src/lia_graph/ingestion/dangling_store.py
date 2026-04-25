"""Persistent dangling-edge-candidate store (Decision D1).

See ``docs/done/next/additive_corpusv1.md`` §4 Decision D1 and §5 Phase 4.

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

    _LOAD_BATCH_SIZE = 200
    _UPSERT_BATCH_SIZE = 500

    def load_for_target_keys(
        self, target_keys: Iterable[str]
    ) -> dict[str, list[DanglingRow]]:
        """Return all candidates grouped by ``target_key``.

        Input strings are deduplicated before querying. Returns an empty dict
        when the input iterable is empty (no PostgREST call). The key list is
        chunked into ``_LOAD_BATCH_SIZE`` sub-requests so the PostgREST query
        string stays under httpx's URL-length limit (large deltas can easily
        touch thousands of article keys).
        """
        keys = [k for k in {str(k).strip() for k in target_keys if k} if k]
        if not keys:
            return {}
        grouped: dict[str, list[DanglingRow]] = {}
        for start in range(0, len(keys), self._LOAD_BATCH_SIZE):
            batch = keys[start : start + self._LOAD_BATCH_SIZE]
            resp = (
                self._client.table(self.TABLE_NAME)
                .select(
                    "source_key, target_key, relation, source_doc_id, "
                    "first_seen_delta_id, last_seen_delta_id, raw_reference"
                )
                .in_("target_key", batch)
                .execute()
            )
            for raw in list(getattr(resp, "data", None) or []):
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
        # Build + dedupe by the on_conflict key in one pass. Multiple source
        # edges can legitimately emit the same (source_key, target_key,
        # relation) candidate (e.g. two articles both referencing the same
        # target with the same relation); PostgREST's ON CONFLICT DO UPDATE
        # rejects a batch containing intra-payload duplicates with SQLSTATE
        # 21000 ("cannot affect row a second time"). We collapse dupes here
        # with **last-observation-wins** semantics for ``source_doc_id`` /
        # ``raw_reference`` — matching the docstring's promise that those
        # fields reflect the most recent observation — but coalesce so a
        # later ``None`` does NOT stomp a previously-populated value
        # (provenance loss is silent and hard to debug).
        # ``first_seen_delta_id`` is later spliced back from the DB row if
        # one already exists.
        dedup: dict[tuple[str, str, str], dict[str, Any]] = {}
        for cand in candidates:
            source_key = (cand.source_key or "").strip()
            target_key = (cand.target_key or "").strip()
            relation = (cand.relation or "").strip()
            # Reject empty AND whitespace-only keys. The latter would pass a
            # naive truthiness check and pollute the DB with unmatchable rows.
            if not source_key or not target_key or not relation:
                continue
            key = (source_key, target_key, relation)
            prior_payload = dedup.get(key)
            dedup[key] = {
                "source_key": source_key,
                "target_key": target_key,
                "relation": relation,
                "source_doc_id": cand.source_doc_id
                    or (prior_payload and prior_payload.get("source_doc_id"))
                    or None,
                "first_seen_delta_id": delta_id,
                "last_seen_delta_id": delta_id,
                "raw_reference": cand.raw_reference
                    or (prior_payload and prior_payload.get("raw_reference"))
                    or None,
            }
        payloads: list[dict[str, Any]] = list(dedup.values())
        if not payloads:
            return 0

        # Pre-existing rows win the first_seen fight: load them first and
        # splice their first_seen_delta_id into the payload so the upsert
        # doesn't stomp history.
        existing = self._load_exact(dedup.keys())
        for payload in payloads:
            key = (payload["source_key"], payload["target_key"], payload["relation"])
            prior = existing.get(key)
            if prior is not None and prior.first_seen_delta_id:
                payload["first_seen_delta_id"] = prior.first_seen_delta_id

        # Chunk the write so a very large delta's candidate set doesn't blow
        # the PostgREST request body limit (~5 MB default). 500 rows × ~200 B
        # per row keeps us well under the ceiling with headroom.
        for start in range(0, len(payloads), self._UPSERT_BATCH_SIZE):
            batch = payloads[start : start + self._UPSERT_BATCH_SIZE]
            self._client.table(self.TABLE_NAME).upsert(
                batch, on_conflict="source_key,target_key,relation"
            ).execute()
        return len(payloads)

    def delete_promoted(
        self,
        candidates: Sequence[DanglingCandidate],
    ) -> int:
        """Delete rows matching the supplied candidate keys.

        Best-effort: on httpx timeout for any individual DELETE, log and
        continue. Leaving stale dangling_candidates rows is not a
        correctness issue — the next successful run re-loads them and
        re-promotes (idempotent on normative_edges natural key) before
        re-attempting cleanup.

        Patched in v4 Phase 4 (batch 6 triage 2026-04-24 AM Bogotá) after
        two consecutive batch-6 runs died on the same Supabase DELETE
        timeout mid-sink. Followup F13 tracks a proper batched-DELETE or
        DELETE-with-composite-IN rewrite.
        """
        import httpx as _httpx  # local import — kept out of module top to
                                 # avoid importing httpx for test-fixture users.

        n = 0
        failed = 0
        for cand in candidates:
            if not cand.source_key or not cand.target_key or not cand.relation:
                continue
            try:
                self._client.table(self.TABLE_NAME).delete().eq(
                    "source_key", cand.source_key
                ).eq("target_key", cand.target_key).eq(
                    "relation", cand.relation
                ).execute()
                n += 1
            except (_httpx.ReadTimeout, _httpx.ConnectTimeout, _httpx.PoolTimeout):
                failed += 1
                continue
        if failed:
            import sys as _sys
            print(
                f"[dangling_store.delete_promoted] {failed} DELETEs timed out; "
                f"{n} succeeded. Stale rows will be cleaned up on next run.",
                file=_sys.stderr,
            )
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
