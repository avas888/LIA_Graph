# FalkorDB bulk load — best practices and why ours stalled

**Source:** v6 phase 2b cloud-sink post-mortem 2026-04-24; web research summarized against FalkorDB docs, GitHub, redis-py issues.

> **TL;DR.** The v6 cloud sink stalled 15 min on the Falkor load phase writing only 85 / 3,340 ArticleNodes. Root cause is a **stack of four anti-patterns** common in first-time FalkorDB integrations: (1) redis-py default `socket_timeout=None` → indefinite client block; (2) per-record `GRAPH.QUERY` statements instead of batched `UNWIND`; (3) `MERGE` on unindexed properties → label scans that degrade quadratically with graph size; (4) no per-query `TIMEOUT` so server never self-aborts on a slow statement. Fix is phase 2c — **shipped + validated live on 2026-04-24 (commits `deb71d2`, `bea9bf8`)**.
>
> **Phase 2c live-fire results (cloud FalkorDB, commit `bea9bf8`):** sink completed in **7m27s exit 0**, vs the 28-min kill on the pre-2c attempt. The Falkor phase executed ~38 batched UNWIND statements against the indexed graph; per-query `TIMEOUT 30000` never fired (queries completed within budget); `CREATE INDEX` idempotency guard handled the "already indexed" error on re-runs. Net new writes: +569 TEMA edges, +81 HAS_SUBTOPIC, +5 SubTopicNodes. ArticleNode count stayed flat because the v6 corpus's article_ids collapse-onto existing Falkor nodes (per v4 `_graph_article_key` design — not a phase-2c bug). See `docs/done/next/ingestion_tunningv2.md §16 Appendix D` for full phase-6 scorecard.

## The stall signature

Observed on 2026-04-24 at t=7m–22m of the cloud sink run:

- Python process alive, 0.3 % CPU, RSS stable 295 MB
- Single TCP socket to FalkorDB cloud (AWS EC2) in ESTABLISHED
- **`recv()` blocked** — CPU TIME grew 0.4 s per 3 min wall (keepalive only)
- No events emitted
- FalkorDB cloud immediately responsive to `RETURN 1` probe (779 ms) — **server alive, not dead**

This is the textbook `redis-py socket_timeout=None + long server-side query` profile (see redis-py issue #2243, #1232).

## Anti-pattern #1 — per-record `GRAPH.QUERY`

`src/lia_graph/graph/client.py`'s `execute_many` serializes statements over one socket, one `GRAPH.QUERY` per statement. For the v6 corpus that means:

- ~3,300 node-create statements
- ~25,000 edge-create statements
- ≈ **28,000 round-trips**, each incurring a Cypher parse + plan + exec + reply

The Prodopsy FalkorDB bulk-load writeup and FalkorDB's own v4.6 release notes land on the same guidance: batches of **10,000–50,000 rows** via:

```cypher
UNWIND $rows AS r
MERGE (n:ArticleNode {article_key: r.key})
SET n += r.props
```

One parse, one plan, one reply. ~50–100× throughput for the same wall time.

## Anti-pattern #2 — `MERGE` without an index

`MERGE (n:ArticleNode {article_key: $k})` without `CREATE INDEX FOR (n:ArticleNode) ON (n.article_key)` performs a **label scan** on every call. Per FalkorDB indexing docs, the planner uses the index automatically when present — catastrophic difference:

| Graph size | No index | With index |
|---|---|---|
| 100 nodes | ~1 ms | ~1 ms |
| 1,000 nodes | ~10 ms | ~1 ms |
| 10,000 nodes | ~100 ms | ~1 ms |
| 100,000 nodes | **~1,000 ms per MERGE** | ~2 ms |

At 25k edge-writes × 1 s each = 7 hours.

**Fix: always `CREATE INDEX` for every MERGE label before the bulk load.** For Lia_Graph:

```cypher
CREATE INDEX FOR (n:ArticleNode) ON (n.article_id)
CREATE INDEX FOR (n:TopicNode) ON (n.topic_key)
CREATE INDEX FOR (n:SubTopicNode) ON (n.sub_topic_key)
# ... plus ReformNode, ConceptNode, ParameterNode (see schema)
```

### ⚠️ `CREATE INDEX` is NOT idempotent in FalkorDB (correction, 2026-04-24)

**Correction to an earlier draft of this doc.** We originally cited the FalkorDB docs as saying `CREATE INDEX` is idempotent. Live behavior contradicts that: the second run against an already-indexed label returns:

```
FalkorDB returned an error for CreateIndex ArticleNode.article_id:
  Attribute 'article_id' is already indexed
```

Cloud-sink phase-2c run #1 exited code 3 on the **very first `CREATE INDEX`** because the label was already indexed from an earlier smoke test.

**Handle this in the client, not in the schema code.** `src/lia_graph/graph/client.py::_is_benign_index_error` detects:
- Statement description starts with `"CreateIndex"` (restrict scope)
- AND error message contains `"already indexed"`

…and returns a `skipped=True` result with `stats={"indices_already_present": 1}` instead of raising. Other errors on `CreateIndex` (auth, connection) still propagate; the same error text on non-`CreateIndex` statements also propagates.

**Regression test.** `tests/test_graph_client_phase2c.py::test_already_indexed_error_is_benign_for_createindex` — pins the guard's specificity (correct scope on CreateIndex only, correct error-text match). See commit `bea9bf8`.

**Why we didn't use `CREATE INDEX IF NOT EXISTS`.** FalkorDB's Cypher dialect doesn't support that syntax as of v4.6. `CLIENT LIST TYPE normal` + `GRAPH.EXPLAIN` style schema discovery would work but adds a round-trip per index. The catch-and-skip approach is simpler and still bounded by description-prefix + error-text.

## Anti-pattern #3 — no per-query `TIMEOUT`

`GRAPH.QUERY <graph> "<cypher>"` without `TIMEOUT <ms>` runs server-side until it finishes or FalkorDB's `TIMEOUT_DEFAULT` fires. **`TIMEOUT_DEFAULT` is 0 (off) out of the box.** Free-tier cloud doesn't set it. So a slow MERGE runs forever server-side; closing the client socket does **not** abort it.

Fix: append `TIMEOUT 30000` (30 s) to every `GRAPH.QUERY`:

```
GRAPH.QUERY LIA_REGULATORY_GRAPH "UNWIND $rows AS r MERGE ..." TIMEOUT 30000
```

On timeout, **FalkorDB rolls back partial writes** (per docs). Safe default.

## Anti-pattern #4 — `socket_timeout=None`

`redis-py` defaults every connection to `socket_timeout=None` — recv waits forever. The OS TCP keepalive (default ~2h on Linux, longer on macOS) is your only backstop.

Our `GraphClient` calls `sock.settimeout(connect_timeout_seconds)` at connect time but doesn't re-apply a **read** timeout before `_run_graph_query_over_socket`. If the connect-timeout value sticks (usually 3s), reads abort after 3s — too tight for legitimate 10s UNWINDs. If it doesn't stick, reads wait forever.

Fix shape:

```python
# At socket open:
sock.settimeout(config.connect_timeout_seconds)  # auth handshake
# Before each GRAPH.QUERY:
sock.settimeout(config.query_timeout_seconds + grace)  # e.g. 35s for TIMEOUT 30000
# Also:
sock.setsockopt(SOL_SOCKET, SO_KEEPALIVE, 1)
# macOS/Linux: set TCP_KEEPIDLE=30, TCP_KEEPINTVL=10, TCP_KEEPCNT=3
```

## Recommended production shape for our loader

### Indexes first (one-time, idempotent)
```cypher
CREATE INDEX FOR (n:ArticleNode) ON (n.article_key);
CREATE INDEX FOR (n:TopicNode) ON (n.topic_key);
CREATE INDEX FOR (n:SubTopicNode) ON (n.subtopic_key);
```

### Batched node writes
```python
# 500 per batch; tune up if p95 reply < 3s
for batch in _chunk(article_rows, 500):
    stmt = GraphWriteStatement(
        description="article_batch",
        query="""
            UNWIND $rows AS r
            MERGE (n:ArticleNode {article_key: r.article_key})
            SET n += r.props
        """,
        parameters={"rows": batch},
    )
    client.execute(stmt, strict=True, timeout_ms=30_000)
    emit_event("graph.batch_written", {"kind": "ArticleNode", "count": len(batch)})
```

### Batched edge writes
```python
# 1000 per batch; edges are smaller
for batch in _chunk(edge_rows, 1000):
    stmt = GraphWriteStatement(
        description="tema_batch",
        query="""
            UNWIND $rows AS r
            MATCH (a:ArticleNode {article_key: r.article_key})
            MATCH (t:TopicNode {topic_key: r.topic_key})
            MERGE (a)-[:TEMA]->(t)
        """,
        parameters={"rows": batch},
    )
    client.execute(stmt, strict=True, timeout_ms=30_000)
    emit_event("graph.batch_written", {"kind": "TEMA", "count": len(batch)})
```

### Connection lifetime
```python
redis.Redis(
    ...,
    socket_timeout=60,          # default; overridden per-query
    socket_connect_timeout=5,
    socket_keepalive=True,
    socket_keepalive_options={TCP_KEEPIDLE: 30, TCP_KEEPINTVL: 10, TCP_KEEPCNT: 3},
    health_check_interval=30,
)
```

## Observability — "is the write still running?"

`GRAPH.SLOWLOG <graph>` returns the **10 slowest completed** queries. Does NOT show in-flight.

Live in-flight signal from a sibling connection:

```
CLIENT LIST TYPE normal
# → rows with cmd=graph.query, age=<secs-since-start>, idle=<secs-since-last-recv>
```

If your stuck client shows `cmd=graph.query` with growing `age`, the server is still working. If `cmd` is anything else, the query is done and your client is hung waiting for a reply that already arrived and was consumed.

**Kill switch** for a run we want to abort:

```
CLIENT KILL ID <stuck_client_id>
```

FalkorDB rolls back partial writes on forced disconnect (per TIMEOUT docs).

## FalkorDB cloud tier caveats

| Setting | Default | Notes |
|---|---|---|
| `TIMEOUT_MAX` / `TIMEOUT_DEFAULT` | 0 (off) | Cloud doesn't set these. Your client must send `TIMEOUT` per query. |
| `QUERY_MEM_CAPACITY` | unlimited | OOM kills query with `exceeded capacity` error if set. |
| `NODE_CREATION_BUFFER` | 16,384 | Fine for our 3-5k node batches. |
| Free tier memory | 100 MB | Our graph is ~50–80 MB. Tight. |
| Free tier idle | 1 day stop, 7 day delete | Not a concern during a run. |

## Heartbeat / monitor implications (answering the operator's "improve heartbeat" ask)

Add these to `scripts/monitoring/ingest_heartbeat.py` and any inline monitors we arm:

1. **Phase-aware stall thresholds.** Sink and Falkor phases legitimately emit no per-item events pre-fix. Once phase 2c lands `graph.batch_written` events, they should fire every ~3–10 s; stall = no event in 120 s during Falkor phase. Tune after measurement.
2. **CLIENT LIST probe every 3 ticks** — if the monitor has Falkor credentials, opens a sibling connection, checks whether the stuck write is still executing server-side. Enables "is this making progress?" answers without killing anything.
3. **`dep_health.py` Falkor probe is now fixed** (commit TBD) — uses `GraphWriteStatement(RETURN 1)` instead of the wrong `run_query(str)` API. Monitor integrates this at 9-min cadence.

## Anti-patterns the operator / future PR author should NEVER apply

- **"Just retry on timeout."** Retrying a bulk MERGE that timed out at 30 s with an unindexed MERGE will time out again at 30 s. Fix the underlying pattern (add index, batch with UNWIND, set TIMEOUT). Retry is for transient network errors only.
- **"Increase the timeout to 5 minutes."** Defers the stall, doesn't fix it. If 30 s UNWIND over 500 rows isn't fast enough, the MERGE is doing a scan — add the index.
- **"Use a bigger batch to reduce round-trips."** 10k UNWIND beats 100 × 100-row statements, but 100k UNWIND in one shot will OOM at the reply stage (FalkorDB replies one RESP array). Cap 50k.
- **Single-statement-per-record via convenience helpers** (`stage_node`, `stage_edge`). These exist but are for tiny writes. Never use them in a bulk load.

## Sources

- FalkorDB [Indexing docs](https://docs.falkordb.com/cypher/indexing/), [Configuration docs](https://docs.falkordb.com/getting-started/configuration.html), [GRAPH.QUERY docs](https://docs.falkordb.com/commands/graph.query.html), [LOAD CSV announcement v4.6](https://www.falkordb.com/news-updates/falkordbs-v4-6-introduces-load-csv/)
- [FalkorDB/falkordb-bulk-loader](https://github.com/FalkorDB/falkordb-bulk-loader) + [PyPI package](https://pypi.org/project/falkordb-bulk-loader/)
- [Bulk-load large graphs into FalkorDB (Prodopsy)](https://prodopsy.com/bulk-load-large-graphs-into-falkordb/)
- [GRAPH.SLOWLOG](https://docs.falkordb.com/commands/graph.slowlog.html)
- redis-py issues [#2243](https://github.com/redis/redis-py/issues/2243), [#1232](https://github.com/redis/redis-py/issues/1232)
- Cloud tiers: [Free](https://docs.falkordb.com/cloud/free-tier.html), [Startup](https://docs.falkordb.com/cloud/startup-tier.html)

## See also

- [`parallelism-and-rate-limits.md`](parallelism-and-rate-limits.md) — the classifier-pool design (doesn't apply to Falkor because Cypher MERGE has contention across workers).
- [`supabase-sink-parallelization.md`](supabase-sink-parallelization.md) — phase 2b sink pool (Supabase-safe parallelism; Falkor needs different primitives).
- [`falkor-edge-undercount-and-resultset-cap-2026-04-26.md`](falkor-edge-undercount-and-resultset-cap-2026-04-26.md) — the v5 §6.2/§6.3 investigation that exposed two adjacent issues: a label-name bug in the parity probe + a 33% prose-only edge-key mismatch (the linker was writing the slug form to `normative_edges.source_key` while Falkor MERGEd under the `whole::` form per `_graph_article_key`).
- [`edge-key-form-discipline.md`](edge-key-form-discipline.md) — the meta-lesson distilled from §6.3: write-path and delete-path key-forms must mirror each other.
- [`../process/heartbeat-monitoring.md`](../process/heartbeat-monitoring.md) — heartbeat discipline updated for phase 2c.
- `docs/done/next/ingestion_tunningv2.md §16 Appendix D §9` — TPM-aware limiter was already the #1 follow-up; Falkor bulk-load now joins it.
