"""Tests for ``lia_graph.ingestion.dangling_store``."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from lia_graph.ingestion.dangling_store import (
    DanglingCandidate,
    DanglingStore,
)


@dataclass
class _Execute:
    data: list[dict[str, Any]]


class _Query:
    def __init__(self, parent: "_Table", op: str, payload: Any = None, on_conflict: str | None = None) -> None:
        self._parent = parent
        self._op = op
        self._payload = payload
        self._on_conflict = on_conflict
        self._filters: list[tuple[str, str, Any]] = []
        self._columns: str | None = None

    def select(self, columns: str) -> "_Query":
        self._columns = columns
        return self

    def eq(self, column: str, value: Any) -> "_Query":
        self._filters.append(("eq", column, value))
        return self

    def in_(self, column: str, values: list[Any]) -> "_Query":
        self._filters.append(("in_", column, list(values)))
        return self

    def lt(self, column: str, value: Any) -> "_Query":
        self._filters.append(("lt", column, value))
        return self

    def _matches(self, row: dict[str, Any]) -> bool:
        for op, column, value in self._filters:
            if op == "eq":
                if row.get(column) != value:
                    return False
            elif op == "in_":
                if row.get(column) not in value:
                    return False
            elif op == "lt":
                v = row.get(column)
                if v is None or not (v < value):
                    return False
        return True

    def execute(self) -> _Execute:
        rows = self._parent.rows
        if self._op == "select":
            return _Execute([dict(r) for r in rows if self._matches(r)])
        if self._op == "delete":
            to_delete = [r for r in rows if self._matches(r)]
            for r in to_delete:
                rows.remove(r)
            return _Execute(to_delete)
        if self._op == "upsert":
            # Faithful to PostgREST: when ``on_conflict=`` is set, the server
            # rejects a batch whose rows collide on the conflict key with
            # SQLSTATE 21000 ("ON CONFLICT DO UPDATE command cannot affect row
            # a second time"). The earlier version of this fake was silently
            # tolerant, which masked a real intra-batch-duplicate crash in
            # ``upsert_candidates``. Keep the fake strict so regressions
            # surface at test time.
            if self._on_conflict:
                conflict_cols = [c.strip() for c in self._on_conflict.split(",") if c.strip()]
                seen_in_batch: set[tuple[Any, ...]] = set()
                for p in self._payload or []:
                    tup = tuple(p.get(c) for c in conflict_cols)
                    if tup in seen_in_batch:
                        raise RuntimeError(
                            "PostgREST would return SQLSTATE 21000: "
                            "ON CONFLICT DO UPDATE command cannot affect row "
                            f"a second time (duplicate key {tup!r} on "
                            f"({self._on_conflict}))"
                        )
                    seen_in_batch.add(tup)
            for p in self._payload or []:
                key = (p["source_key"], p["target_key"], p["relation"])
                match = next(
                    (r for r in rows if (r["source_key"], r["target_key"], r["relation"]) == key),
                    None,
                )
                if match:
                    match.update(p)
                else:
                    rows.append(dict(p))
            return _Execute([])
        return _Execute([])


class _Table:
    def __init__(
        self,
        name: str,
        rows: list[dict[str, Any]],
        client: "_FakeClient | None" = None,
    ) -> None:
        self.name = name
        self.rows = rows
        self._client = client

    def select(self, columns: str) -> _Query:
        if self._client is not None:
            self._client.calls.append(("select", self.name, 0, None))
        q = _Query(self, "select")
        q.select(columns)
        return q

    def upsert(self, rows: list[dict[str, Any]], on_conflict: str | None = None) -> _Query:
        payload = list(rows)
        if self._client is not None:
            self._client.calls.append(("upsert", self.name, len(payload), on_conflict))
        return _Query(self, "upsert", payload=payload, on_conflict=on_conflict)

    def delete(self) -> _Query:
        if self._client is not None:
            self._client.calls.append(("delete", self.name, 0, None))
        return _Query(self, "delete")


class _FakeClient:
    def __init__(self, seed: dict[str, list[dict[str, Any]]] | None = None) -> None:
        self._rows: dict[str, list[dict[str, Any]]] = {}
        for name, rows in (seed or {}).items():
            self._rows[name] = [dict(r) for r in rows]
        # Instrumentation — expert edge cases #1 and #8 assert that large
        # payloads get chunked across multiple PostgREST requests instead of
        # one giant call. Each entry is (op, table, count, on_conflict|None).
        self.calls: list[tuple[str, str, int, str | None]] = []

    def table(self, name: str) -> _Table:
        if name not in self._rows:
            self._rows[name] = []
        return _Table(name, self._rows[name], self)

    def rows(self, name: str) -> list[dict[str, Any]]:
        return self._rows.get(name, [])

    def count_calls(self, op: str, table: str | None = None) -> int:
        return sum(
            1 for (o, t, _n, _oc) in self.calls
            if o == op and (table is None or t == table)
        )


TABLE = DanglingStore.TABLE_NAME


# (a) empty load.
def test_empty_load_returns_empty_dict() -> None:
    client = _FakeClient()
    store = DanglingStore(client)
    assert store.load_for_target_keys([]) == {}
    # Target keys with no rows also returns empty dict.
    assert store.load_for_target_keys(["nonexistent"]) == {}


# (b) upsert N candidates → N rows; re-upsert same → still N, last_seen advanced.
def test_upsert_is_idempotent_and_advances_last_seen_delta_id() -> None:
    client = _FakeClient()
    store = DanglingStore(client)
    candidates = [
        DanglingCandidate(
            source_key="src_a",
            target_key="tgt_x",
            relation="references",
            source_doc_id="doc_1",
            raw_reference="art 10",
        ),
        DanglingCandidate(
            source_key="src_b",
            target_key="tgt_y",
            relation="complements",
        ),
    ]
    n1 = store.upsert_candidates(candidates, delta_id="delta_1")
    assert n1 == 2
    rows = client.rows(TABLE)
    assert len(rows) == 2
    for r in rows:
        assert r["first_seen_delta_id"] == "delta_1"
        assert r["last_seen_delta_id"] == "delta_1"

    # Re-upsert: first_seen preserved, last_seen advanced.
    n2 = store.upsert_candidates(candidates, delta_id="delta_2")
    assert n2 == 2
    rows_after = client.rows(TABLE)
    assert len(rows_after) == 2
    for r in rows_after:
        assert r["first_seen_delta_id"] == "delta_1"
        assert r["last_seen_delta_id"] == "delta_2"


# (c) load_for_target_keys returns only matching rows.
def test_load_for_target_keys_filters() -> None:
    client = _FakeClient()
    store = DanglingStore(client)
    store.upsert_candidates(
        [
            DanglingCandidate("s1", "t1", "references"),
            DanglingCandidate("s2", "t2", "references"),
            DanglingCandidate("s3", "t1", "complements"),
        ],
        delta_id="delta_1",
    )
    grouped = store.load_for_target_keys(["t1"])
    assert set(grouped.keys()) == {"t1"}
    assert {r.source_key for r in grouped["t1"]} == {"s1", "s3"}


# (d) delete_promoted removes exactly the named rows.
def test_delete_promoted_removes_exact_rows() -> None:
    client = _FakeClient()
    store = DanglingStore(client)
    store.upsert_candidates(
        [
            DanglingCandidate("s1", "t1", "references"),
            DanglingCandidate("s2", "t2", "references"),
        ],
        delta_id="delta_1",
    )
    removed = store.delete_promoted(
        [DanglingCandidate("s1", "t1", "references")]
    )
    assert removed == 1
    remaining = client.rows(TABLE)
    assert len(remaining) == 1
    assert remaining[0]["source_key"] == "s2"


# (e) gc_older_than removes rows with last_seen_delta_id < threshold.
def test_gc_older_than_filters_by_delta_id_threshold() -> None:
    client = _FakeClient()
    store = DanglingStore(client)
    # Manually seed rows with explicit last_seen_delta_id values.
    store.upsert_candidates(
        [DanglingCandidate("s_old", "t", "references")],
        delta_id="delta_20260101_000000_aaa",
    )
    store.upsert_candidates(
        [DanglingCandidate("s_new", "t", "references")],
        delta_id="delta_20260422_120000_bbb",
    )
    removed = store.gc_older_than("delta_20260201_000000_000")
    assert removed == 1
    remaining = client.rows(TABLE)
    assert len(remaining) == 1
    assert remaining[0]["source_key"] == "s_new"


# (f) unique-key dedup enforced at upsert time (same key merges, no duplicate rows).
def test_upsert_dedups_on_primary_key() -> None:
    client = _FakeClient()
    store = DanglingStore(client)
    payload = [
        DanglingCandidate("s", "t", "references"),
        DanglingCandidate("s", "t", "references", raw_reference="updated"),
    ]
    store.upsert_candidates(payload, delta_id="delta_1")
    rows = client.rows(TABLE)
    # Despite two payload entries with the same PK, we end up with one row.
    assert len(rows) == 1
    assert rows[0]["raw_reference"] == "updated"


# (g) regression: the 2026-04-23 Phase 9.A force-full run crashed when two
# distinct edges (different source_doc_id, different raw_reference) produced
# DanglingCandidates sharing the same (source_key, target_key, relation)
# conflict triple. Real PostgREST rejected the batch with SQLSTATE 21000.
# Our ``_FakeClient`` now mirrors that strictness above; if the dedupe inside
# ``upsert_candidates`` ever regresses, this test is the canary.
def test_upsert_candidates_dedupes_on_conflict_key() -> None:
    client = _FakeClient()
    store = DanglingStore(client)
    payload = [
        DanglingCandidate(
            source_key="article_X",
            target_key="article_Y",
            relation="references",
            source_doc_id="doc_A",
            raw_reference="art 10 (from doc A)",
        ),
        # Second candidate with the SAME (source, target, relation) but
        # different metadata — this is what the classifier emits when two
        # edges carry the same typed reference.
        DanglingCandidate(
            source_key="article_X",
            target_key="article_Y",
            relation="references",
            source_doc_id="doc_B",
            raw_reference="art 10 (from doc B)",
        ),
        # A genuinely distinct candidate should still land.
        DanglingCandidate(
            source_key="article_X",
            target_key="article_Z",
            relation="references",
        ),
    ]
    # Must NOT raise SQLSTATE-21000 — the patch dedupes before upsert.
    n = store.upsert_candidates(payload, delta_id="delta_regression")
    assert n == 2  # two unique (src, tgt, rel) tuples after dedupe
    rows = client.rows(TABLE)
    assert len(rows) == 2
    # Last-observation-wins for the duplicated tuple (matches the docstring's
    # promise that raw_reference + source_doc_id reflect the latest observation).
    duplicated = next(r for r in rows if r["target_key"] == "article_Y")
    assert duplicated["source_doc_id"] == "doc_B"
    assert duplicated["raw_reference"] == "art 10 (from doc B)"


# Extra: incomplete candidates are skipped.
def test_upsert_skips_incomplete_candidates() -> None:
    client = _FakeClient()
    store = DanglingStore(client)
    payload = [
        DanglingCandidate("", "t", "references"),
        DanglingCandidate("s", "", "references"),
        DanglingCandidate("s", "t", ""),
        DanglingCandidate("s", "t", "references"),
    ]
    n = store.upsert_candidates(payload, delta_id="delta_1")
    assert n == 1
    rows = client.rows(TABLE)
    assert len(rows) == 1


# =============================================================================
# Expert-review edge cases (consulted 2026-04-23 before Phase 9.A re-run)
# =============================================================================

# (h) #1: 1,000+ unique candidates must land. Current impl chunks at
# _UPSERT_BATCH_SIZE=500 — assert both that they all end up in the table AND
# that the client issued multiple upsert requests rather than one mega-payload.
def test_upsert_candidates_chunks_large_batches() -> None:
    client = _FakeClient()
    store = DanglingStore(client)
    cands = [
        DanglingCandidate(f"src_{i}", f"tgt_{i}", "references")
        for i in range(1050)
    ]
    n = store.upsert_candidates(cands, delta_id="delta_bulk")
    assert n == 1050
    assert len(client.rows(TABLE)) == 1050
    # With _UPSERT_BATCH_SIZE=500: ceil(1050/500) = 3 upsert calls.
    upsert_calls = client.count_calls("upsert", TABLE)
    assert upsert_calls == 3, f"expected 3 chunked upserts, got {upsert_calls}"


# (i) #4: whitespace-only keys must be rejected like empty strings.
def test_upsert_rejects_whitespace_only_keys() -> None:
    client = _FakeClient()
    store = DanglingStore(client)
    payload = [
        DanglingCandidate("   ", "t", "references"),  # ws-only source
        DanglingCandidate("s", "  ", "references"),   # ws-only target
        DanglingCandidate("s", "t", "\t\n "),         # ws-only relation
        DanglingCandidate("s", "t", "references"),    # valid
    ]
    n = store.upsert_candidates(payload, delta_id="delta_1")
    assert n == 1
    rows = client.rows(TABLE)
    assert len(rows) == 1


# (j) #4 continued: trailing/leading whitespace on valid keys is normalized
# away, so ``"s"`` and ``"s "`` dedupe to one row instead of polluting the DB.
def test_upsert_normalizes_whitespace_on_keys() -> None:
    client = _FakeClient()
    store = DanglingStore(client)
    payload = [
        DanglingCandidate("article_X", "article_Y", "references"),
        DanglingCandidate("article_X ", "article_Y", "references"),   # trailing
        DanglingCandidate(" article_X", " article_Y ", " references "),  # all
    ]
    n = store.upsert_candidates(payload, delta_id="delta_1")
    assert n == 1
    rows = client.rows(TABLE)
    assert len(rows) == 1
    assert rows[0]["source_key"] == "article_X"
    assert rows[0]["target_key"] == "article_Y"
    assert rows[0]["relation"] == "references"


# (k) #10: a later candidate with ``None`` metadata MUST NOT stomp a
# previously-populated ``source_doc_id`` / ``raw_reference`` in the same
# batch. The dedupe coalesces to the last non-None value.
def test_upsert_does_not_stomp_populated_metadata_with_none() -> None:
    client = _FakeClient()
    store = DanglingStore(client)
    payload = [
        DanglingCandidate(
            "s", "t", "references",
            source_doc_id="doc_A", raw_reference="art 10 (from A)",
        ),
        # Same conflict key, but None metadata — must not wipe the above.
        DanglingCandidate("s", "t", "references", source_doc_id=None, raw_reference=None),
    ]
    store.upsert_candidates(payload, delta_id="delta_1")
    rows = client.rows(TABLE)
    assert len(rows) == 1
    assert rows[0]["source_doc_id"] == "doc_A"
    assert rows[0]["raw_reference"] == "art 10 (from A)"


# (l) #5: a pre-existing DB row with ``first_seen_delta_id=None`` (legacy
# / manual insert) gets backfilled to the current delta. Current semantic:
# if there's nothing to preserve, the current delta fills in. Locked here
# so any future change to the splice guard is a deliberate decision.
def test_upsert_backfills_null_first_seen_on_existing_row() -> None:
    client = _FakeClient({
        TABLE: [
            {
                "source_key": "s",
                "target_key": "t",
                "relation": "references",
                "source_doc_id": None,
                "first_seen_delta_id": None,    # legacy NULL
                "last_seen_delta_id": "delta_0",
                "raw_reference": None,
            }
        ]
    })
    store = DanglingStore(client)
    store.upsert_candidates(
        [DanglingCandidate("s", "t", "references")], delta_id="delta_repair"
    )
    rows = client.rows(TABLE)
    assert len(rows) == 1
    # Backfill: current delta fills the NULL.
    assert rows[0]["first_seen_delta_id"] == "delta_repair"
    assert rows[0]["last_seen_delta_id"] == "delta_repair"


# (m) #6: delete_promoted returns the input count regardless of whether
# any DB rows actually existed. Locked so callers know not to treat the
# return as "rows actually deleted" (there's no cheap way to know in a
# PostgREST round-trip without re-querying).
def test_delete_promoted_counts_inputs_not_actual_deletions() -> None:
    client = _FakeClient()
    store = DanglingStore(client)
    store.upsert_candidates(
        [DanglingCandidate("s", "t", "references")], delta_id="delta_1"
    )
    removed = store.delete_promoted(
        [
            DanglingCandidate("s", "t", "references"),       # exists
            DanglingCandidate("s", "t", "references"),       # dup (already gone)
            DanglingCandidate("s", "missing", "references"), # never existed
        ]
    )
    # Contract: returns input cardinality, not actual deletions.
    assert removed == 3
    # DB truth: only one row was ever there, now gone.
    assert client.rows(TABLE) == []


# (n) #7: re-upsert with the same delta_id is a no-op on first_seen — no
# row duplication, no history rewrite, no extra requests beyond the normal
# load-then-upsert pair.
def test_upsert_same_delta_id_retry_is_idempotent() -> None:
    client = _FakeClient()
    store = DanglingStore(client)
    cands = [
        DanglingCandidate("s1", "t1", "references"),
        DanglingCandidate("s2", "t2", "references"),
    ]
    store.upsert_candidates(cands, delta_id="delta_flaky")
    store.upsert_candidates(cands, delta_id="delta_flaky")  # retry
    rows = client.rows(TABLE)
    assert len(rows) == 2
    for r in rows:
        assert r["first_seen_delta_id"] == "delta_flaky"
        assert r["last_seen_delta_id"] == "delta_flaky"


# (o) #8: load_for_target_keys chunks input at _LOAD_BATCH_SIZE=200. Test
# the boundaries (199 / 200 / 201 / 401 + internal dup) to lock the fix
# that keeps the PostgREST URL under httpx's length limit.
@pytest.mark.parametrize("n_keys,expected_select_calls", [
    (199, 1),   # below one batch
    (200, 1),   # exactly one batch
    (201, 2),   # spills into second
    (401, 3),   # three batches (200 + 200 + 1)
])
def test_load_for_target_keys_chunks_at_batch_boundary(n_keys, expected_select_calls) -> None:
    client = _FakeClient()
    store = DanglingStore(client)
    # Seed one row per target so we can validate no duplication across chunks.
    store.upsert_candidates(
        [DanglingCandidate(f"s{i}", f"t{i}", "references") for i in range(n_keys)],
        delta_id="delta_seed",
    )
    client.calls.clear()
    keys = [f"t{i}" for i in range(n_keys)] + ["t0"]  # deliberate dup
    grouped = store.load_for_target_keys(keys)
    assert len(grouped) == n_keys
    # Each target appears exactly once — no leakage across chunks.
    for target_key, rows in grouped.items():
        assert len(rows) == 1, (
            f"target {target_key!r} leaked across chunks: {len(rows)} rows"
        )
    select_calls = client.count_calls("select", TABLE)
    assert select_calls == expected_select_calls, (
        f"expected {expected_select_calls} select calls for {n_keys} keys, "
        f"got {select_calls}"
    )


# (p) #9: Unicode NFC vs NFD keys are treated as distinct. Colombian legal
# text routinely contains accented identifiers ("artículo_5"). Our dedupe
# is codepoint-exact (matching Postgres's default collation); locking the
# contract prevents a silent normalization change from collapsing rows.
def test_upsert_does_not_normalize_unicode() -> None:
    import unicodedata
    client = _FakeClient()
    store = DanglingStore(client)
    nfc = unicodedata.normalize("NFC", "artículo_5")
    nfd = unicodedata.normalize("NFD", "artículo_5")
    assert nfc != nfd  # sanity — they're different byte sequences
    store.upsert_candidates(
        [
            DanglingCandidate(nfc, "t", "references"),
            DanglingCandidate(nfd, "t", "references"),
        ],
        delta_id="delta_1",
    )
    rows = client.rows(TABLE)
    # Contract: two distinct Unicode forms produce two rows. If you ever
    # want to change this, normalize at the edge and update this test.
    assert len(rows) == 2
