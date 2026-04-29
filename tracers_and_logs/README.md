# `tracers_and_logs/`

Single home for the deep-trace collector and its log destination. Created
2026-04-29 in response to `docs/re-engineer/fix/fix_v1.md` — the §1.G SME
panel regressed from 21/36 to 8/36 acc+, and the served pipeline strips
diagnostics down to `retrieval_health` only, leaving no signal for
operators to localize the failure.

## What lives here

| Path | What |
|---|---|
| `pipeline_trace.py` | Context-local trace collector + `step(...)` facade. |
| `logs/pipeline_trace.jsonl` | Append-only JSONL of every step from every served request. |
| `logs/.gitkeep` | Keep the directory tracked even when the JSONL is gitignored. |

## Trace shape

Every step emits one row to `logs/pipeline_trace.jsonl`:

```json
{
  "ts_utc": "2026-04-29T17:42:11.123456+00:00",
  "trace_id": "095b9b48-5878-...",
  "qid_hint": "beneficio_auditoria_P2",
  "session_id": "chat_69c5b58a...",
  "step": "topic_router.llm.outcome",
  "status": "fallback",
  "elapsed_ms": 124.6,
  "message": "LLM verdict below confidence threshold; falling through to keyword fallback",
  "details": {
    "adapter_class": "DeepSeekChatAdapter",
    "model": "deepseek-v4-pro",
    "confidence": 0.32,
    "threshold": 0.55,
    "raw_content_preview": "{\"primary_topic\":\"declaracion_renta\",\"confidence\":0.32}"
  }
}
```

Status values: `ok | fallback | error | skipped | info`.

The same dict (minus the JSON formatting overhead) is also attached to
`response.diagnostics["pipeline_trace"]` so the eval harness picks it up
without having to tail the file.

## Instrumented stages

The doc `docs/re-engineer/fix/fix_v1.md` §6 step 2 lists the keys the
diagnostic must surface. Each one maps to a step name:

| Stage | Step name(s) |
|---|---|
| Trace boundary | `trace.start`, `trace.finish` |
| Topic resolution | `topic_router.rule_route`, `topic_router.llm.attempt`, `topic_router.llm.outcome`, `topic_router.fallback` |
| Planner | `planner.build`, `planner.subtopic_intent` |
| Retrieval — Supabase chunks | `retriever.hybrid_search.in/out`, `retriever.subtopic_boost`, `retriever.anchor_articles`, `retriever.vigencia_v3.in/out` |
| Retrieval — Falkor graph | `retriever.graph.in/out` (when applicable) |
| Reranker | `rerank.in/out` |
| Coherence gate | `coherence.detect`, `coherence.refusal` |
| Topic-misalignment safety | `safety.misalignment` |
| Citation allowlist | `citations.allowlist` |
| LLM polish | `polish.attempt`, `polish.outcome` |

## Reading the log

```bash
# Tail in real time as a request flows:
tail -f tracers_and_logs/logs/pipeline_trace.jsonl | jq -c '{step, status, elapsed_ms, msg: .message}'

# All steps for one trace_id:
jq -c 'select(.trace_id == "<TRACE_ID>")' tracers_and_logs/logs/pipeline_trace.jsonl

# All fallback / error events in the last run:
jq -c 'select(.status == "fallback" or .status == "error")' tracers_and_logs/logs/pipeline_trace.jsonl
```

## Enabling the trace

The trace is **always on** for the served pipeline. The collector is cheap
when nothing reads the active trace, and the per-step write is one
`json.dumps` + one append. If you ever need to disable it (perf
regression, disk-full), set `LIA_PIPELINE_TRACE=0` in the env and the
orchestrator will skip installing the active trace.
