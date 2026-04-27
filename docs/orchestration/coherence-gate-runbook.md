# Coherence-gate runbook — refusal modes + decision tree

When Lia answers `"Detecté que..."` / `"No pude ubicar evidencia..."` / `"Evidencia insuficiente..."`, that's a **topic-safety abstention**. The response carries a `fallback_reason` string. This runbook maps each reason to its exact code path + fix candidates.

## The 7 abstention reasons + where each fires

| `fallback_reason` | Origin file:line | Layer | Visible refusal text |
|---|---|---|---|
| `pipeline_d_router_silent_failure` | `orchestrator.py:detect_router_silent_failure` | Pre-retrieval | "No pude clasificar esta pregunta..." |
| `pipeline_d_no_graph_primary_articles` | `orchestrator.py:547-549` | Pre-gate (post-retrieval) | "Evidencia insuficiente para responder..." (general) |
| `pipeline_d_coherence_primary_off_topic` | `_coherence_gate.py:67-72` | Coherence-gate Case A | "Detecté que los artículos primarios recuperados pertenecen al tema **X**, no al tema clasificado **Y**..." |
| `pipeline_d_coherence_chunks_off_topic` | `_coherence_gate.py:86-99` | Coherence-gate Case B | "No pude ubicar evidencia del tema **Y** en el grafo. Los documentos de apoyo recuperados pertenecen al tema **X**..." |
| `pipeline_d_coherence_zero_evidence` | `_coherence_gate.py:101-104` | Coherence-gate Case C | "Evidencia insuficiente para responder con respaldo normativo en el tema **Y**..." |
| `topic_safety_promote_misalignment` | `topic_safety.py:should_promote_misalignment_to_abstention` | Post-coherence escalation | Same as primary_off_topic; promoted to firm abstention when router confidence is low |
| `pipeline_d_evidence_threshold` | (rare) | Pre-gate evidence-floor check | "Evidencia insuficiente..." |

## Decision tree — start from the API response's `fallback_reason`

```
fallback_reason == "pipeline_d_router_silent_failure"
└─ The topic router returned no topic with sufficient confidence.
   ├─ Diagnostic: check `diagnostics.topic_routing.requested_topic` and
   │  `effective_topic`. If both null and `topic_adjusted=false`, the message
   │  fell out of every keyword bucket AND the LLM classifier didn't fire / was
   │  under threshold.
   ├─ Likely cause: vocabulary mismatch (user phrasing not in topic_taxonomy
   │  keyword_anchors) OR genuinely out-of-scope question.
   └─ Fix candidates:
      • Add keyword_anchors to topic_taxonomy.json for the missing
        vocabulary (see `path-veto-rule-based-classifier-correction.md`
        for the "your path encodes ground truth" pattern).
      • Lower the LLM classifier confidence threshold (NOT recommended —
        feedback_thresholds_no_lower).

fallback_reason == "pipeline_d_no_graph_primary_articles"
└─ `evidence.primary_articles` was empty after retrieval.
   ├─ Origin: orchestrator.py:547-549, BEFORE the coherence-gate runs.
   ├─ This means `_classify_article_rows` returned no primaries, even though
   │  hybrid_search may have returned chunks.
   ├─ Common causes:
   │  • The planner extracted no `article` entry_points (the question doesn't
   │    name a specific article).
   │  • The planner extracted article keys that don't exist as chunks
   │    (e.g., the article numbers are obsolete OR they're prose-only docs
   │    where chunk_ids use `whole::path` form, not the article number).
   │  • Anchor rows weren't found and FTS didn't surface article-keyed chunks
   │    in the top match_count.
   └─ Fix candidates:
      • For prose-only docs whose articles are referenced numerically: extend
        `_fetch_anchor_article_rows` to handle the `whole::` form. Currently
        `chunk_id LIKE %::<key>` only catches numbered articles.
      • Add planner-side enrichment: when a question lacks article anchors,
        fall back to topic-keyword retrieval that still produces classifiable
        primaries.

fallback_reason == "pipeline_d_coherence_primary_off_topic"
└─ `evidence.primary_articles` was non-empty BUT `detect_topic_misalignment`
   said the articles' lexical-scored top topic ≠ router_topic.
   ├─ Origin: _coherence_gate.py:67-72 (Case A path).
   ├─ Mechanism (topic_safety.py:113-163):
   │  1. The article TEXT (title + excerpt) is scored against topic
   │     keyword_anchors via `_score_topic_keywords`.
   │  2. The lexical winner is computed.
   │  3. If `top_topic != router_topic` AND `top_score >= MIN_TOP_SCORE`
   │     AND `router_score < top_score * RATIO`, misaligned=True.
   │  4. v5 §1.A short-circuits BEFORE this lexical path: if any primary
   │     article has `router_topic` in its `secondary_topics`, NOT misaligned.
   ├─ Common causes:
   │  • The article genuinely covers a different topic than the router thinks
   │    — but the router is wrong (vocabulary mismatch) OR the article's
   │    canonical owner is a different topic per the corpus tagging.
   │  • The article's `secondary_topics` curation is incomplete — it should
   │    include the router_topic as a secondary but doesn't yet.
   ├─ Pre-§1.A this would have refused indiscriminately. Post-§1.A only
   │  refuses when no primary article is curated as compatible.
   └─ Fix candidates:
      • CURATION: add the router_topic to the article's `secondary_topics`
        in `config/article_secondary_topics.json` (per the SME-validated
        mappings in `taxonomy_v2_sme_response.md §1.4`). Run
        `scripts/ingestion/sync_article_secondary_topics_to_falkor.py` to write to
        Falkor without re-ingest.
      • If the curation is correct but the SHORT-CIRCUIT still doesn't fire:
        check that the Falkor node has `secondary_topics` written (via
        `MATCH (a:ArticleNode {article_id: 'X'}) RETURN a.secondary_topics`).
        Note: FalkorDB serializes arrays as bracketed strings (e.g.,
        '[a, b]'), not Python lists — see `falkor-bulk-load.md`.

fallback_reason == "pipeline_d_coherence_chunks_off_topic"
└─ `evidence.primary_articles` was empty (Case B/C path) AND support_documents
   exist BUT lexical scoring on their titles says a different topic than
   router_topic AND `topic_key_matches < 2`.
   ├─ Origin: _coherence_gate.py:86-99.
   ├─ Mechanism:
   │  1. `_count_support_topic_key_matches` counts support_docs whose
   │     `topic_key` matches router_topic OR is in the router's
   │     `compatible_topics` (v5 §1.B).
   │  2. If count >= 2 (`_SUPPORT_DOC_TOPIC_KEY_MATCH_MIN`), NOT misaligned.
   │  3. Otherwise, score the support_docs' title text against keyword_anchors.
   │  4. If lexical winner ≠ router_topic AND winner_score >= MIN, misaligned.
   ├─ Common causes (per `next_v5.md §1.C` post-§1.B catalog):
   │  • Hybrid_search ranks umbrella-topic chunks above narrow-topic chunks.
   │    Narrow-topic docs exist but only 1 makes it into support_documents.
   │  • The router's `compatible_topics` doesn't include the umbrella that's
   │    actually being pulled (e.g., `regimen_cambiario.compatible_topics`
   │    can't include `cambiario` because cambiario isn't a registered
   │    topic in `topic_taxonomy.json`; the actual umbrella showing up is
   │    `retencion_fuente_general`, which is too broad to safely add as a
   │    compatible).
   └─ Fix candidates (ordered by general-applicability):
      • Add a `topic_boost` parameter to the hybrid_search SQL function
        (analogous to `subtopic_boost`), boosting chunks where
        `chunk.topic = filter_topic`. Plumb from the planner. This is the
        Lia-wide fix.
      • Reserve slots in `_collect_support` for router-topic docs (2-pass
        selection: first pass picks high-rank, second pass fills with
        router-topic docs from anywhere in chunk_rows).
      • Curate more compatible_topics entries in
        `config/compatible_doc_topics.json` (only when SME validates the
        adjacency — never just "the lexical winner showed up").

fallback_reason == "pipeline_d_coherence_zero_evidence"
└─ Primary articles empty AND support_documents empty.
   ├─ Origin: _coherence_gate.py:101-104.
   ├─ This is the "hybrid_search returned nothing AND no anchor articles
   │  matched" case. Most aggressive abstention.
   ├─ Common causes:
   │  • Sync_generation mismatch — the active gen has no chunks for this
   │    topic. Check `diagnostics.empty_reason` for sub-cause.
   │  • FTS query is too restrictive (rare; the OR-builder usually catches).
   │  • Topic genuinely has zero coverage — corpus deficit.
   └─ Fix candidates: corpus expansion (write content for the topic).

fallback_reason == "topic_safety_promote_misalignment"
└─ Primary_off_topic was detected BUT also the router topic confidence was
   low (`should_promote_misalignment_to_abstention=True`).
   ├─ Origin: topic_safety.py
   ├─ This converts a "soft hedge" into a firm abstention when the router
   │  itself wasn't confident. The accountant should NOT see a hedged answer
   │  rooted in shaky routing.
   └─ Fix candidates: same as primary_off_topic + improve router confidence
      (better keyword_anchors, better LLM classifier prompt).
```

## How to read the diagnostic dict

When the chat refuses, the `/api/chat` response (with `debug=true`) carries:

```json
{
  "answer_mode": "topic_safety_abstention",
  "fallback_reason": "pipeline_d_coherence_chunks_off_topic",
  "diagnostics": {
    "topic_safety": {
      "router_silent": null,
      "misalignment": {
        "misaligned": false,
        "router_topic": "regimen_cambiario",
        "articles_top_topic": null,
        "reason": "no_primary_articles"
      },
      "coherence": {
        "mode": "enforce",
        "misaligned": true,
        "source": "support_documents",
        "router_topic": "regimen_cambiario",
        "dominant_topic": "retencion_fuente_general",
        "topic_key_matches": 1,
        "top_lexical_score": 8,
        "reason": "chunks_off_topic"
      },
      "refusal_reason": "chunks_off_topic",
      "refusal_source": "support_documents"
    }
  }
}
```

Read order:
1. `fallback_reason` at the top level → which row in the table above.
2. `topic_safety.misalignment.reason` → why detect_topic_misalignment voted (no_primary_articles, secondary_topic_match, lexical_aligned, lexical_misaligned, articles_have_no_topic_keyword_hits, no_router_topic).
3. `topic_safety.coherence.reason` → why detect_evidence_coherence voted (primary_off_topic, primary_on_topic, chunks_off_topic, support_docs_on_topic, zero_evidence_for_router_topic, secondary_topic_match).
4. `topic_safety.coherence.dominant_topic` → which topic won the lexical vote (the "wrong" topic that got picked instead).
5. `topic_safety.coherence.topic_key_matches` → how many support_docs had topic_key in router_topic's accepted set (router + compatible_topics).
6. `topic_safety.coherence.top_lexical_score` → the score of the dominant topic. Must be ≥ `_SUPPORT_DOC_TOP_SCORE_MIN` (3) for misalignment to fire.

## Thresholds + their config locations

| Threshold | Constant name | File:line | Default | Operator-overridable? |
|---|---|---|---|---|
| Support-doc topic_key match minimum | `_SUPPORT_DOC_TOPIC_KEY_MATCH_MIN` | `_coherence_gate.py:25` | 2 | NO (hard-coded; per `feedback_thresholds_no_lower`) |
| Support-doc top-lexical score minimum to flag misaligned | `_SUPPORT_DOC_TOP_SCORE_MIN` | `_coherence_gate.py:24` | 3 | NO |
| Misalignment min top score (primary articles) | `_MISALIGNMENT_MIN_TOP_SCORE` | `topic_safety.py` | (check current) | NO |
| Misalignment router-vs-top ratio | `_MISALIGNMENT_ROUTER_RATIO` | `topic_safety.py` | (check current) | NO |
| Coherence-gate mode | env `LIA_EVIDENCE_COHERENCE_GATE` | runtime | `enforce` | YES (`off`, `shadow`, `enforce`) |

## Common diagnostic invocations

**Replicate a failing chat without going through the UI.** Use the `/api/chat` endpoint with `debug=true` (see the response shape above).

**Check whether a specific article has secondary_topics in Falkor.**
```bash
PYTHONPATH=src:. uv run python -c "
from lia_graph.graph.client import GraphClient, GraphWriteStatement
gc = GraphClient.from_env()
res = gc.execute(GraphWriteStatement(description='probe',
    query='MATCH (a:ArticleNode {article_id: \"689-3\"}) RETURN a.secondary_topics AS s', parameters={}), strict=False)
for r in res.rows: print(repr(r))
"
```
Expected output: `{'s': '[beneficio_auditoria]'}` (note the brackets — it's a string, not a list; see `falkor-bulk-load.md`).

**Trace which topic each support_document carries.** Hit `/api/chat` with `debug=true` and inspect the response's `evidence_snippets[]` (each carries the parent doc's topic via `relative_path` lookup). Or read `documents.topic` directly via:
```bash
PYTHONPATH=src:. uv run python -c "
from lia_graph.supabase_client import get_supabase_client
sb = get_supabase_client()
r = sb.table('documents').select('relative_path, topic').like('relative_path', '%FIRMEZA%').execute()
for d in r.data: print(d)
"
```

## See also

- [`retrieval-runbook.md`](retrieval-runbook.md) — for the full retrieval flow that feeds this gate.
- [`docs/learnings/ingestion/coherence-gate-thin-corpus-diagnostic-2026-04-26.md`](../learnings/ingestion/coherence-gate-thin-corpus-diagnostic-2026-04-26.md) — the diagnostic that identified the 12 thin-corpus topics + the 4 still failing post-§1.A/§1.B.
- [`docs/aa_next/next_v5.md §1.C`](../aa_next/next_v5.md) — open difficulties + attempted fixes + hypothesis catalog.
- `src/lia_graph/pipeline_d/_coherence_gate.py` — 130 lines, read it directly.
- `src/lia_graph/pipeline_d/topic_safety.py` — `detect_topic_misalignment` (lexical) + `should_promote_misalignment_to_abstention`.
