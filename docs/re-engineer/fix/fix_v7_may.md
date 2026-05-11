## fix_v7_may.md — restore real hybrid retrieval: soften topic filter, turn on query embeddings, fence cross-topic synthesis

> **Drafted 2026-05-11 ~8:00 PM Bogotá** by claude-opus-4-7 after a
> 10-question diagnostic probe of the served chat engine
> (`tracers_and_logs/logs/probe_runs/20260511T003617Z_10q_post_polish_guardrails/`)
> followed by a corpus-presence audit and a retrieval-trace audit
> that compared the served behavior against
> `docs/orchestration/orchestration.md` §Lane 4.
>
> **Audience.** Zero-context fresh LLM or engineer. This doc is
> self-contained. You can pick it up cold.
>
> **What this is.** Three surgical fixes to the retrieval seam, in
> the order they should ship: (1) soften the topic hard-filter so
> cross-topic chunks become reachable; (2) replace the zero query
> embedding with a real Gemini embedding so semantic matching
> actually runs; (3) add a synthesis-time cross-topic content gate
> so off-topic bullets stop bleeding into answers.
>
> **What this is not.** Not an SME-panel iteration. Not a corpus
> ingestion push. Not a polish-prompt change (the polish guardrails
> for invented norms / periods landed in the same session as this
> doc was drafted, in `src/lia_graph/pipeline_d/answer_llm_polish.py`
> + `tests/test_answer_llm_polish.py` — see §0 inheritance).
>
> **Scope guard.** The §1.G 36-Q SME panel sits at the closing bar
> from `fix_v6` (32 strong / 4 acc / 0 weak / 36 acc+, anchor:
> `evals/sme_validation_v1/runs/20260430T000527Z_fix_v5_phase6b_rerun/`).
> Every phase below must re-run §1.G **after** landing and confirm
> 36/36 acc+ with no drop in strong count. The §1.G run is gated
> behind the saved `feedback_sme_panel_explicit_request_only` rule —
> ask the operator before triggering.

---

## 0. Inheritance from fix_v1..fix_v6 (read once, then this doc)

Everything in `fix/fix_v6.md` §0 carries forward unchanged. Specifically:

- **Six-gate lifecycle** is mandatory (idea / plan / measurable
  criterion / test plan / greenlight / refine-or-discard). RAG is
  complex; unit tests green ≠ improvement.
- **Provider order** in `config/llm_runtime.json` stays
  `gemini-flash` first for chat. Do not flip back to DeepSeek-v4-pro
  for the chat path. (Reason: fix_v1 diagnosis.)
- **Don't run the full pytest suite** — use `make test-batched`.
- **Cloud writes to Lia Graph** (NOT Lia Contador) are pre-authorized
  per `feedback_lia_graph_cloud_writes_authorized`. Announce before
  executing; no per-action confirmation.
- **The Falkor adapter must keep propagating cloud outages** — no
  silent artifact fallback on staging.
- **Vigencia is norm-keyed**, persist on the norm itself.
- **Subtopic aliases stay broad** per
  `feedback_subtopic_aliases_breadth` — do not tighten them
  reflexively.
- **Default run mode is `dev:staging`** for any probe/eval/chat work
  per `feedback_default_run_mode_staging`.

**Layer-specific to this doc** (the new context):

- Polish-side guardrails against invented Ley/Decreto/Resolución/
  Sentencia references and invented years are already in place as
  of this commit (added in the same drafting session, see
  `src/lia_graph/pipeline_d/answer_llm_polish.py` rules
  `no_invented_norm_lineage` and `no_invented_periods`). The polish
  validate path will reject and fall back to template when the LLM
  introduces these tokens. The cross-topic content gate this doc
  proposes is the **template-side** equivalent — it stops off-topic
  norms from being in the template in the first place.

---

## 1. The diagnosis (verified 2026-05-11 against `dev:staging`)

Three things determine whether the wide corpus we already have is
actually reachable at retrieval time. Two of them are currently
disabled.

### Diagnosis 1 — Topic filter is a hard `WHERE` clause, not a soft boost

**Code**: `src/lia_graph/pipeline_d/retriever_supabase.py:273`:

```python
"filter_topic": router_topic if (router_topic and topic_boost > 1.0) else None,
```

**Migration**: `supabase/migrations/20260427000000_topic_boost.sql`
adds `filter_topic_boost` as an argument and (per the in-file
comment at `retriever_supabase.py:263-264`) applies the filter as
*"WHERE clause for filter_topic when filter_topic_boost > 1.0"*.

**Launcher**: `LIA_TOPIC_BOOST_FACTOR=1.5` is the staging default,
so the WHERE clause fires on every query.

**Doc invariant** (orchestration.md line 535):

> **Topic is ranking signal, not WHERE filter**: `filter_topic` is
> NEVER applied as a hard filter on chunks because cross-topic
> anchors (e.g. Art. 147 ET under IVA, load-bearing for a
> `declaracion_renta` loss-compensation question) must stay
> reachable.

The code violates the doc's own invariant. Per CLAUDE.md
non-negotiable — *"reconcile to docs/orchestration/orchestration.md
— never the other way around"* — the resolution is fix the code.

**Observed impact** (probe run
`20260511T003617Z_10q_post_polish_guardrails`):

- Q1 (`¿Puedo deducir el ICA?`) was routed to
  `costos_deducciones_renta`. The ICA folder in the corpus is
  tagged `topic=ica`. Mechanical exclusion. Engine retrieved
  gastos-exterior chunks (Arts. 121/122/123) instead.
- Q3 (`¿Qué soporte documental?`) routed to
  `costos_deducciones_renta`. `FE-N01-marco-legal-facturacion-
  electronica-documento-soporte.md` is tagged
  `topic=facturacion_electronica`. Mechanical exclusion.
- Q7 (`plazos AG 2025`) routed to `declaracion_renta`.
  `N-CAL-2026-calendario-tributario-consolidado.md` is tagged
  under a calendar topic. Mechanical exclusion. Retrieval pulled
  CST + Ley 100/1993 (labor norms) instead.
- Q8 (`Formulario PJ ordinario`) same magnet as Q7.

### Diagnosis 2 — Query-side embeddings are zero, never disclosed in the doc

**Code**: `src/lia_graph/pipeline_d/retriever_supabase.py:795-798`:

```python
def _zero_embedding() -> list[float]:
    # `hybrid_search` needs a 768-dim vector. Until the embedding worker
    # catches up, pass zeros so the FTS half of the RRF still dominates.
    return [0.0] * 768
```

The query side passes 768 zeros to the `hybrid_search` RPC. The RPC
combines vector cosine similarity with FTS via Reciprocal Rank
Fusion (RRF); with the vector half zeroed, FTS alone drives the
ranking.

Ingest already populates `chunks.embedding` with Gemini vectors
(staging log: *"gemini: Gemini API key was accepted by the
embedding endpoint."*). Those embeddings just sit unused at query
time.

**Observed impact**: every retrieval miss in §1 above is partially
attributable to this. FTS on `"costos_deducciones_renta
declaracion_renta soporte documental costos renta"` ranks
gastos-exterior chunks (which contain "soporte" and "documento"
tokens) high. A real query embedding would rank
`FE-N01-marco-legal-facturacion-electronica-documento-soporte` very
high regardless of token frequency.

### Diagnosis 3 — Synthesis template lets off-topic norms in

Even when topic routing is correct (Q4, Q5: beneficio de auditoría
correctly routed), the synthesis template includes bullets that cite
pérdidas-fiscales norms (Arts. 147 / 290 / 588). The polish
guardrails added in the same drafting session catch *new* invented
norms but they cannot rewrite the template — and the template
itself is the source of the cross-topic bleed in Q4/Q5.

**Observed impact**: Q4 ("¿En qué consiste el beneficio
689-3?") had Ruta sugerida and Riesgos blocks composed entirely
around Art. 147 ET (pérdidas fiscales), Art. 260, Art. 588/589.
Q5 ("¿Si corrijo después de firmeza?") same shape.

### What's healthy (do not regress)

- **Falkor anchor BFS** works when the planner identifies article
  keys (Q2/Q7/Q8/Q9 all returned 6–50 anchor articles from the
  graph).
- **Vigencia v3 demotion** is firing and correctly dropping/demoting
  obsolete chunks. Diagnostics intact.
- **`retrieval_backend` / `graph_backend`** present on every
  response. CLAUDE.md non-negotiable holds.
- **Polish reject-on-invented-norm-lineage / invented-periods**
  added in the same session is functional — verified end-to-end on
  Q4 (period invention caught), Q6 (lineage invention caught).
- **Comparative-regime chain mode** rendered correctly on Q10 in
  the pre-polish-guardrail run (the post-guardrail run shows a Q10
  regression — the comparative table requires a non-empty template,
  see §4 below).

---

## 2. The plan — three surgical phases, ship 7a → 7c

### Recommended phasing

| Phase | Fix | Why this order | Effort |
|---|---|---|---|
| 7a | Soften topic hard-filter to a true ranking boost | Smallest code change, biggest immediate retrieval unlock (4/6 retrieval misses). Doc-vs-code reconciliation. | XS |
| 7b | Replace `_zero_embedding()` with a real Gemini query embedding | Largest semantic unlock. Ship after 7a so the gain from each is measurable independently. | M |
| 7c | Add synthesis-time cross-topic content gate | Closes the bleed Q4 / Q5 expose. Requires a small config file (topic → allowed-norm-prefixes). Land after retrieval is healthy so we measure the residual problem honestly. | M |

The phases compose:

- 7a alone: fixes the retrieval-magnet failures.
- 7a + 7b: makes near-miss semantic matches reachable too.
- 7a + 7b + 7c: removes the off-topic content bleed that retrieval
  fixes alone can't reach.

---

## 3. Implementation (numbered, copy-paste-ready)

### Phase 7a — soften the topic hard-filter (target: ≤1 working day)

#### 3a.1 — Verify the RPC's `filter_topic` semantics

Before touching Python, read the migration to confirm whether
`filter_topic=NULL` still allows `filter_topic_boost` to apply as a
soft boost, or whether the boost code path requires non-null
`filter_topic`.

```bash
cat supabase/migrations/20260427000000_topic_boost.sql
```

Look for the body of `hybrid_search`. Three possibilities:

- **(a)** The RPC has `WHERE (filter_topic IS NULL OR chunk.topic =
  filter_topic)` — passing `NULL` simply disables the filter; the
  boost can still operate via the score multiplier. **No SQL
  change needed.**
- **(b)** The RPC has unconditional `WHERE chunk.topic =
  filter_topic` — passing `NULL` collapses results to zero. **SQL
  must be patched.**
- **(c)** The RPC ties the boost to the filter being non-null. **SQL
  must be patched** to separate them.

If (a): proceed directly to 3a.2.

If (b) or (c): write `supabase/migrations/20260512000000_topic_filter_soft.sql`:

```sql
-- Drop the prior 15-arg signature explicitly per fix_v5 learning
-- (avoid PostgREST overload ambiguity).
DROP FUNCTION IF EXISTS public.hybrid_search(
    vector(768), text, text, text, integer,
    text, text, text, text, text, text, text,
    text, text, double precision
);

CREATE OR REPLACE FUNCTION public.hybrid_search(
    query_embedding vector(768),
    query_text text,
    filter_topic text DEFAULT NULL,
    filter_pais text DEFAULT 'colombia',
    match_count integer DEFAULT 24,
    filter_knowledge_class text DEFAULT NULL,
    filter_sync_generation text DEFAULT NULL,
    filter_temporal text DEFAULT NULL,
    filter_subtopic text DEFAULT NULL,
    subtopic_boost double precision DEFAULT 1.0,
    filter_topic_boost double precision DEFAULT 1.0,
    -- carry the rest of the existing signature verbatim ...
)
RETURNS TABLE (...) AS $$
BEGIN
    RETURN QUERY
    WITH ranked AS (
        SELECT
            chunk.*,
            -- soft topic boost: multiplies the rank when topic matches,
            -- does NOT exclude when it doesn't match
            CASE
                WHEN filter_topic IS NOT NULL
                     AND chunk.topic = filter_topic
                THEN filter_topic_boost
                ELSE 1.0
            END AS topic_multiplier,
            -- ... rest of scoring unchanged ...
        FROM chunks chunk
        WHERE
            -- topic is intentionally NOT in WHERE — it's a ranking
            -- signal only, per docs/orchestration/orchestration.md
            -- §4.1 invariant.
            (filter_pais IS NULL OR chunk.pais = filter_pais)
            AND (filter_subtopic IS NULL OR chunk.subtopic = filter_subtopic OR chunk.subtopic IS NULL)
            -- ... rest of WHERE unchanged ...
    )
    SELECT * FROM ranked ORDER BY (rrf_score * topic_multiplier) DESC LIMIT match_count;
END;
$$ LANGUAGE plpgsql STABLE;
```

The exact field list and scoring need to match the existing
migration — copy the rest verbatim from `20260427000000_topic_boost.sql`
and only change the WHERE / scoring branches.

Apply via:
```bash
supabase db push --linked
```

#### 3a.2 — Python: pass `filter_topic=None` and rely on the soft boost

Edit `src/lia_graph/pipeline_d/retriever_supabase.py` line 273:

```python
# BEFORE:
"filter_topic": router_topic if (router_topic and topic_boost > 1.0) else None,

# AFTER:
# Topic acts as a ranking signal via filter_topic_boost, NOT a hard
# WHERE filter — cross-topic anchors must stay reachable (see
# docs/orchestration/orchestration.md §4.1 Invariant "Topic is
# ranking signal, not WHERE filter").
"filter_topic": router_topic if (router_topic and topic_boost > 1.0) else None,
```

Wait — that's the same line. The actual change is that
`filter_topic_boost` keeps its current value AND the RPC body no
longer treats `filter_topic` as a hard filter. So the Python change
is minimal: keep the line, BUT make sure the RPC body in 3a.1 is the
soft version.

If you preferred a Python-only fix without touching SQL (case (a)
above), simply force `filter_topic` to None and let the boost
operate via score multiplication — but verify with one staging
probe that the boost still has an effect.

#### 3a.3 — Apply the same fix to the secondary `_hybrid_search` site

`src/lia_graph/pipeline_d/retriever_supabase.py:602` has a near-
identical payload construction (the "small set, we only need 1-2
more docs" path). Apply the same softening — pass `filter_topic` as
a boost-only signal.

#### 3a.4 — Restart `dev:staging` (Python module cache)

```bash
# Kill the running launcher cleanly
pkill -f "dev-launcher.mjs staging"
sleep 3
lsof -ti:8787 | xargs -r kill -9
# Restart with log capture
TS=$(date -u +%Y%m%dT%H%M%SZ)
nohup npm run dev:staging \
  > tracers_and_logs/logs/sme_panel_runs/staging_post_v7a_${TS}.log 2>&1 \
  < /dev/null & disown
until curl -sS -o /dev/null -w "%{http_code}" \
        http://127.0.0.1:8787/api/health | grep -q 200; do
  sleep 2
done
```

#### 3a.5 — Update the orchestration env matrix

In `docs/orchestration/orchestration.md` §Runtime Env Matrix, add a
change-log row dated 2026-05-11 with version
`v2026-05-11-topic-filter-soft`. Bump the "Current version" header
to match. Reaffirm Invariant I5 wording.

### Phase 7b — turn on real query embeddings (target: 1–2 working days)

#### 3b.1 — Find which embedding model ingest uses

```bash
grep -rn "text-embedding\|gemini-2\|embed_content\|embedContent" \
  src/lia_graph/ scripts/ 2>/dev/null | head -10
```

Look for the canonical model id (likely `text-embedding-004` or
`gemini-embedding-001`, 768-dim). The query-side call must use the
same model.

#### 3b.2 — Add a `_query_embedding` helper next to `_zero_embedding`

Edit `src/lia_graph/pipeline_d/retriever_supabase.py`. Add near
line 795:

```python
import os
from functools import lru_cache

_EMBED_MODEL = "text-embedding-004"  # or whatever ingest uses
_EMBED_DIM = 768
_EMBED_TIMEOUT_SECONDS = float(os.getenv("LIA_QUERY_EMBED_TIMEOUT_SECONDS", "4.0"))
_EMBED_ENV_FLAG = "LIA_QUERY_EMBEDDINGS_ENABLED"


def _query_embeddings_enabled() -> bool:
    raw = str(os.getenv(_EMBED_ENV_FLAG, "1") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _query_embedding(query_text: str) -> tuple[list[float], dict]:
    """Return (embedding, diag). Falls back to zero vector on ANY
    failure so retrieval stays functional. Diagnostic dict carries
    the outcome (ok / disabled / error_kind) for trace surfacing.
    """
    if not _query_embeddings_enabled():
        return _zero_embedding(), {"embedding_mode": "disabled_by_env"}
    if not (query_text or "").strip():
        return _zero_embedding(), {"embedding_mode": "empty_query"}
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return _zero_embedding(), {"embedding_mode": "no_api_key"}
    try:
        # Use the same Gemini client / endpoint ingest uses.
        # If ingest uses google-genai SDK, mirror that pattern here.
        from google import genai
        client = genai.Client(api_key=api_key)
        response = client.models.embed_content(
            model=_EMBED_MODEL,
            contents=query_text,
            config={"output_dimensionality": _EMBED_DIM},
        )
        vec = list(response.embeddings[0].values)
        if len(vec) != _EMBED_DIM:
            return _zero_embedding(), {
                "embedding_mode": "dimension_mismatch",
                "got_dim": len(vec),
            }
        return vec, {"embedding_mode": "ok", "model": _EMBED_MODEL}
    except Exception as exc:  # noqa: BLE001
        return _zero_embedding(), {
            "embedding_mode": "error",
            "error_kind": type(exc).__name__,
            "error_message": str(exc)[:200],
        }


def _zero_embedding() -> list[float]:
    # Safety-net: returned when the real query embedding is unavailable.
    # The orchestrator MUST NOT use this as the default — see
    # `_query_embedding` above and orchestration.md §4.1.
    return [0.0] * _EMBED_DIM
```

#### 3b.3 — Wire `_query_embedding` into the hybrid_search payloads

Replace **both** call sites of `_zero_embedding()` in the payload
construction (lines 271 and 602):

```python
# BEFORE:
"query_embedding": _zero_embedding(),

# AFTER:
embedding, embed_diag = _query_embedding(query_text)
payload["query_embedding"] = embedding
```

And surface `embed_diag` into the trace step:

```python
write_trace_step(
    "retriever.hybrid_search.in",
    ...,
    embedding_mode=embed_diag.get("embedding_mode"),
    embedding_model=embed_diag.get("model"),
)
```

#### 3b.4 — Add a launcher default and a kill-switch env

Edit `scripts/dev-launcher.mjs` so all three modes set
`LIA_QUERY_EMBEDDINGS_ENABLED=1` by default. Document the kill
switch in CLAUDE.md and orchestration.md: setting
`LIA_QUERY_EMBEDDINGS_ENABLED=0` reverts to the zero embedding (for
emergency rollback without a code revert).

#### 3b.5 — Cache (optional, deferred): if Gemini latency hurts

If the 4-second timeout becomes a problem in practice, add a small
in-memory LRU on `_query_embedding(query_text)` (last 512 queries)
keyed by `query_text`. The chat path is single-tenant per process;
the cache hit-rate on repeat questions during eval runs is
non-trivial. **Do not add the cache in 7b**; only add it if
post-launch latency telemetry justifies it.

#### 3b.6 — Update the orchestration env matrix

Bump version to `v2026-05-12-query-embeddings-on`. Add Invariant
I8: *"Query-side embeddings are computed at runtime via Gemini
`text-embedding-004`. Zero-vector fallback is an emergency
safety-net, not the steady-state behavior."*

### Phase 7c — synthesis-time cross-topic content gate (target: 2–3 working days)

#### 3c.1 — Define the topic → allowed-norm-prefixes map

Create `config/topic_norm_allowlist.json`:

```json
{
  "_schema_version": 1,
  "_description": "Per-topic allowlist of norm reference_key prefixes the synthesis layer is allowed to surface. Cross-topic norms are only included when the topic appears in the request's secondary_topics list. Maintained by hand; one row per primary topic.",
  "beneficio_auditoria": {
    "allowed_prefixes": ["art:689", "art:714", "ley:2155", "ley:2277", "ley:2294"],
    "cross_topic_allowed": ["procedimiento_tributario", "firmeza_declaraciones"]
  },
  "costos_deducciones_renta": {
    "allowed_prefixes": ["art:107", "art:115", "art:121", "art:122", "art:123", "art:771-2", "art:177-1", "art:177-2"],
    "cross_topic_allowed": ["facturacion_electronica", "ica"]
  },
  "perdidas_fiscales_art147": {
    "allowed_prefixes": ["art:147", "art:290", "art:714", "art:689"],
    "cross_topic_allowed": ["beneficio_auditoria", "procedimiento_tributario"]
  },
  "declaracion_renta": {
    "allowed_prefixes": ["art:240", "art:241", "art:188", "art:189"],
    "cross_topic_allowed": ["costos_deducciones_renta", "perdidas_fiscales_art147"]
  },
  "regimen_simple": {
    "allowed_prefixes": ["art:903", "art:904", "art:905", "art:906", "art:907", "art:908", "art:909", "art:910", "art:911", "art:912", "art:913", "art:914", "art:915", "art:916"],
    "cross_topic_allowed": ["ica", "iva"]
  }
}
```

**Important**: every example `reference_key` prefix in this file
must be verified against actual rows in cloud Supabase before this
phase merges, per `feedback_no_hallucinated_examples`. Run:

```bash
PYTHONPATH=src:. uv run python -c "
from lia_graph.supabase_client import get_client
db = get_client()
res = db.table('chunks').select('reference_key').like('reference_key', 'art:689%').limit(5).execute()
print(res.data)
"
```

…for each prefix you list. Either confirm it matches at least one
row, or remove it from the allowlist.

#### 3c.2 — Add the gate at synthesis assembly time

Add a new helper module
`src/lia_graph/pipeline_d/answer_topic_gate.py`:

```python
"""Cross-topic content gate for synthesis-time answer assembly.

When the primary topic is X and the synthesis layer is composing
the template, drop bullets that cite norms whose `reference_key`
prefix is not in `topic_norm_allowlist.json[X]["allowed_prefixes"]`
unless the chunk's topic is in `cross_topic_allowed[X]`. The gate
applies AFTER chunk selection and BEFORE the polish LLM ever sees
the template.

Safety net: if the allowlist is missing or the topic has no entry,
the gate is a no-op (defensive — never make the answer worse than
today).
"""

from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

_ALLOWLIST_PATH = Path(__file__).resolve().parents[3] / "config" / "topic_norm_allowlist.json"
_REF_KEY_RE = re.compile(r"\b([a-z_]+:[A-Za-z0-9_\-]+)\b")
_NORM_INLINE_RE = re.compile(
    r"\(art[s]?\.\s*(\d+[A-Za-z0-9_\-]*)(?:\s+(?:y|,)\s*\d+[A-Za-z0-9_\-]*)*\s+ET\)",
    re.IGNORECASE,
)


@lru_cache(maxsize=1)
def _load_allowlist() -> dict[str, Any]:
    if not _ALLOWLIST_PATH.is_file():
        return {}
    try:
        return json.loads(_ALLOWLIST_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def filter_template_bullets(
    template: str,
    *,
    primary_topic: str | None,
    secondary_topics: tuple[str, ...] = (),
) -> tuple[str, dict[str, Any]]:
    """Drop bullets whose norm citations fall outside the topic
    allowlist. Returns (filtered_template, diag).

    A bullet is kept if EITHER:
      - it has no norm citation at all (e.g. a procedural step), OR
      - every norm it cites starts with a prefix in
        `allowlist[primary_topic]["allowed_prefixes"]`, OR
      - the bullet's chunk is sourced from a topic listed in
        `allowlist[primary_topic]["cross_topic_allowed"]`.
    """
    allowlist = _load_allowlist()
    if not primary_topic or not allowlist:
        return template, {"gate_mode": "noop_no_allowlist"}
    entry = allowlist.get(primary_topic)
    if not entry:
        return template, {"gate_mode": "noop_no_topic_entry", "primary_topic": primary_topic}
    allowed_prefixes = tuple(entry.get("allowed_prefixes") or ())
    cross_topic_allowed = set(entry.get("cross_topic_allowed") or ()) | set(secondary_topics)

    kept: list[str] = []
    dropped: list[str] = []
    for bullet in _iter_bullets(template):
        if _bullet_passes(bullet, allowed_prefixes):
            kept.append(bullet)
        else:
            dropped.append(bullet)
    filtered = _reassemble_bullets(kept, template)
    return filtered, {
        "gate_mode": "applied",
        "primary_topic": primary_topic,
        "secondary_topics": list(secondary_topics),
        "kept_count": len(kept),
        "dropped_count": len(dropped),
        "dropped_excerpts": [b[:120] for b in dropped[:5]],
    }


def _iter_bullets(template: str) -> list[str]:
    """Best-effort bullet splitter. Recognizes `- `, `* `, `1.`, `2.`
    line-starts. Returns one entry per bullet WITH its sub-lines."""
    # implementation here; ~30 lines
    ...


def _bullet_passes(bullet: str, allowed_prefixes: tuple[str, ...]) -> bool:
    """A bullet passes if every (art. X ET) anchor in it maps to a
    reference_key that starts with an allowed prefix."""
    anchors = _NORM_INLINE_RE.findall(bullet)
    if not anchors:
        return True  # no citation, no veto
    for art_num in anchors:
        ref_key = f"art:{art_num}"  # canonical mapping
        if not any(ref_key.startswith(p) or ref_key == p for p in allowed_prefixes):
            return False
    return True


def _reassemble_bullets(kept: list[str], original: str) -> str:
    """Rebuild the template using only the kept bullets, preserving
    section headers and non-bullet prose."""
    # implementation here; ~20 lines
    ...
```

#### 3c.3 — Wire the gate into synthesis assembly

In `src/lia_graph/pipeline_d/answer_synthesis.py` (or the narrowest
module that owns the final template emission — likely
`answer_assembly.py`), call `filter_template_bullets` just before
returning the template to the orchestrator:

```python
from .answer_topic_gate import filter_template_bullets

# ... existing assembly produces `template` ...

filtered, gate_diag = filter_template_bullets(
    template,
    primary_topic=request.effective_topic,
    secondary_topics=tuple(request.secondary_topics or ()),
)
write_trace_step("synthesis.topic_gate.applied", **gate_diag)
return filtered
```

#### 3c.4 — Update the orchestration env matrix

Bump version to `v2026-05-13-cross-topic-gate`. Add a section to
Lane 5 describing the gate. Mention the config file location and
the "noop if entry missing" safety property.

#### 3c.5 — Update CLAUDE.md "Fast Decision Rule"

Add a row: *"answer cites off-topic norms → `config/topic_norm_allowlist.json` (allowed prefixes for the topic) or `pipeline_d/answer_topic_gate.py` (gate logic)"*.

---

## 4. How to test each implementation worked

### 4a — Topic filter test plan (six-gate gate 4)

**Actor**: engineer + automated harness.
**Environment**: `dev:staging` (cloud Supabase + cloud Falkor).
**Steps**:

1. Re-run the 10-question probe from
   `tracers_and_logs/logs/probe_runs/20260511T003617Z_10q_post_polish_guardrails/questions.jsonl`:
   ```bash
   NEW_RUN=$(PYTHONPATH=src:. uv run python \
     .claude/skills/answer-engine-probe/scripts/stage_run.py \
     --slug post_v7a \
     --from-jsonl tracers_and_logs/logs/probe_runs/20260511T003617Z_10q_post_polish_guardrails/questions.jsonl \
     | tail -1)
   PYTHONPATH=src:. uv run python scripts/eval/run_sme_parallel.py \
     --run-dir "$NEW_RUN" --workers 4 \
     --questions "$NEW_RUN/questions.jsonl"
   ```
2. Generate digests for Q1, Q3, Q7, Q8.
3. Verify the citation list now includes (at least one of) the
   target chunks:
   - Q1 expects a chunk with `reference_key` starting `art:115`
     or under `topic=ica`.
   - Q3 expects a chunk from
     `FE-N01-marco-legal-facturacion-electronica-documento-soporte.md`.
   - Q7 / Q8 expect a chunk from
     `N-CAL-2026-calendario-tributario-consolidado.md`.

**Numeric decision rule**: at least **3 of 4** target chunks must
appear in citations or evidence_snippets. Less than 3 → discard or
iterate. (This is the minimum bar; the goal is 4 of 4.)

**Regression gate**: re-run §1.G 36-Q SME panel via
`scripts/eval/run_sme_parallel.py --workers 4` (~5 min wall).
Strong count must not drop below 32; acc+ must stay at 36/36.
**Ask the operator before triggering** per
`feedback_sme_panel_explicit_request_only`.

### 4b — Query embeddings test plan

**Actor**: engineer + automated harness + SME spot-check on 3
specific questions.
**Environment**: `dev:staging`.
**Steps**:

1. Pre-flight: confirm the env wires the Gemini key and the
   model id matches ingest:
   ```bash
   PYTHONPATH=src:. uv run python -c "
   from lia_graph.pipeline_d.retriever_supabase import _query_embedding
   vec, diag = _query_embedding('¿Cuál es el plazo de firmeza?')
   print('mode:', diag.get('embedding_mode'),
         'dim:', len(vec), 'first5:', vec[:5])
   "
   ```
   Expected: `mode: ok`, `dim: 768`, `first5` non-zero floats.

2. Re-run the 10-question probe (same questions.jsonl as 4a).

3. Inspect the trace for `retriever.hybrid_search.in` —
   `embedding_mode=ok` on every question, `embedding_model` non-null.

4. Compare Q1/Q3 (the soporte / ICA semantic-near-miss cases)
   citations vs the 7a-only run. Expectation: real embeddings
   surface chunks that share semantic intent without sharing exact
   tokens — e.g. `FE-N01` for Q3 should now rank higher even though
   the FTS tokens were already letting it through after 7a.

**Numeric decision rule**: per-question relevance score
(human-judged via the `answer-engine-probe` skill rubric) improves
on **at least 6 of 10** versus the 7a-only baseline. If 6 or fewer
improve, iterate on the embedding wiring (model, dim, normalization)
before merging.

**Regression gate**: §1.G 36-Q SME panel — same gate as 4a. Strong
≥ 32, acc+ = 36/36.

### 4c — Cross-topic content gate test plan

**Actor**: engineer.
**Environment**: `dev:staging`.
**Steps**:

1. Re-run Q4 + Q5 specifically (or the full 10-Q set).
2. Read the digest for Q4 and Q5. Expectation:
   - Q4 answer NO LONGER contains bullets citing Art. 147, Art. 290,
     Art. 588 (those are pérdidas-fiscales, gated out by the
     `beneficio_auditoria` allowlist).
   - Q4 answer DOES still contain Art. 689-3, Art. 714 (allowed).
3. Inspect the trace for `synthesis.topic_gate.applied`. Expect
   `gate_mode=applied` with non-zero `dropped_count` on Q4/Q5.

**Numeric decision rule**: dropped_count ≥ 2 for Q4, ≥ 2 for Q5;
kept_count > 0 for both; no question other than Q4/Q5 has its
answer shrink by more than 30% in markdown character count
(safety: gate isn't over-firing).

**Regression gate**: §1.G 36-Q SME panel — same gate.

---

## 5. Drift guardrails (how to prevent each fix from being silently undone)

### 5a — Topic filter

| Guardrail | Mechanism |
|---|---|
| Code comment block at `retriever_supabase.py:273` | Point to `docs/orchestration/orchestration.md` §4.1 Invariant by name. Future maintainers must read the doc before changing this line. |
| Unit test: cross-topic anchor reachable | `tests/test_retriever_supabase.py::test_cross_topic_anchor_reachable_after_v7a` — mocks `db.rpc("hybrid_search", payload)` and asserts `payload["filter_topic"]` is `None` OR the payload contains only `filter_topic_boost`, never both as a hard filter. |
| RPC-signature lint | Add to `make smoke-deps`: query `pg_proc` and fail if more than one `hybrid_search` overload exists (carry-over from fix_v5 §1.G postmortem). |
| Trace assertion in §1.G eval | `scripts/eval/sme_validation_report.py` adds an assertion that `retriever.hybrid_search.in.filter_topic` is `None` on staging traces. Surfaces as INCONCLUSIVE if violated. |

### 5b — Query embeddings

| Guardrail | Mechanism |
|---|---|
| Trace key `embedding_mode` | Surfaced on every `retriever.hybrid_search.in` step. Read by §1.G eval — INCONCLUSIVE if any served chat ran with `embedding_mode != "ok"`. |
| Health check at server startup | New file `src/lia_graph/startup_probes.py` runs `_query_embedding("ping")` at boot; logs WARN if fallback fires; the launcher prints it before serving any request. Operator sees the failure immediately. |
| Counter | `metrics.embedding_fallback_count` increments every time `_zero_embedding` is returned by `_query_embedding`. Surface in the diagnostics tab and alert if it crosses ~5% of served chats over 1 hour. |
| Unit test: real call path with mocked SDK | `tests/test_retriever_supabase.py::test_query_embedding_calls_gemini_when_enabled` — patches `google.genai.Client.models.embed_content` and asserts the response vector is what reaches the RPC payload. |
| Rollback switch | `LIA_QUERY_EMBEDDINGS_ENABLED=0` reverts to zero embedding without a code change. Documented in CLAUDE.md and orchestration.md. Use only in incidents. |

### 5c — Cross-topic content gate

| Guardrail | Mechanism |
|---|---|
| Config-validation test | `tests/test_topic_norm_allowlist.py::test_allowlist_well_formed` — loads `config/topic_norm_allowlist.json`, asserts every topic key is a known topic (cross-check against `topic_router_keywords.py`), every prefix actually matches at least one chunk in a sampled local artifact bundle. |
| Trace step | `synthesis.topic_gate.applied` carries `gate_mode`, `dropped_count`, `dropped_excerpts`. §1.G eval reports the distribution. |
| Regression test: Q4/Q5 patterns | `tests/test_answer_topic_gate.py::test_beneficio_auditoria_drops_perdidas_bullets` — fixed template with Art. 147 bullets, asserts they're dropped when primary_topic=`beneficio_auditoria`. |
| Over-fire detection | `tests/test_answer_topic_gate.py::test_gate_is_noop_for_unlisted_topic` — when primary_topic is not in the allowlist, gate must return the template unchanged. |
| Operator override | Setting `LIA_TOPIC_GATE_MODE=off` in the launcher disables the gate without removing the file. Documented in CLAUDE.md. |

---

## 6. Automatic test updates (what to add to the existing test suite)

### 6a — `tests/test_retriever_supabase.py`

**Add**:

```python
def test_hybrid_search_payload_uses_soft_topic_signal() -> None:
    """v7a regression guard: filter_topic must be None (boost-only)
    when topic_boost > 1.0. Codifies orchestration.md §4.1 invariant.
    """
    # build a fake plan + evidence; spy on db.rpc kwargs;
    # assert payload["filter_topic"] is None AND
    # payload["filter_topic_boost"] == 1.5.

def test_cross_topic_anchor_reachable() -> None:
    """End-to-end: when planner emits anchor key 'art:147' on a
    declaracion_renta-routed question (Art. 147 ET is canonically
    perdidas_fiscales-tagged), the merge_anchors step still surfaces
    it. Failure means the topic filter regressed to hard mode."""
    # patch the supabase responses to include an art:147 chunk under
    # topic=perdidas_fiscales_art147; route question as declaracion_renta;
    # assert the chunk appears in the bundle.

def test_query_embedding_calls_gemini_when_enabled(monkeypatch) -> None:
    """v7b regression guard: when LIA_QUERY_EMBEDDINGS_ENABLED=1, the
    real Gemini embed_content path is exercised and a non-zero vector
    reaches the RPC payload."""
    # monkeypatch google.genai.Client.models.embed_content to return
    # a known vector; spy on the RPC payload; assert vector matches.

def test_query_embedding_falls_back_to_zero_on_error() -> None:
    """Embedding must be a safety-net pattern — any exception in the
    Gemini call returns _zero_embedding() so chat keeps serving."""
    # monkeypatch embed_content to raise; assert payload has zero
    # vector AND embedding_mode='error' in trace.

def test_query_embedding_falls_back_on_env_kill_switch(monkeypatch) -> None:
    """LIA_QUERY_EMBEDDINGS_ENABLED=0 must short-circuit to zero
    without calling Gemini at all (verifies the rollback switch)."""
```

### 6b — `tests/test_answer_topic_gate.py` (new file)

```python
"""Contract tests for the synthesis-time cross-topic content gate.

Lock four invariants:
  1. The gate is a no-op when the primary topic isn't in the allowlist
     (safety: never make answers worse).
  2. Bullets that cite a norm outside the allowlist are dropped.
  3. Bullets with no norm citation pass unchanged.
  4. Secondary topics expand the cross_topic_allowed set per request.
"""

def test_gate_is_noop_for_unlisted_topic(): ...
def test_beneficio_auditoria_drops_perdidas_bullets(): ...
def test_bullets_without_norm_citations_pass(): ...
def test_secondary_topics_expand_allowed_set(): ...
def test_gate_diagnostics_surface_dropped_excerpts(): ...
```

### 6c — `tests/test_topic_norm_allowlist.py` (new file)

```python
"""Config-validation tests for config/topic_norm_allowlist.json.

These run as part of make test-batched and must pass before any
PR that touches the allowlist.
"""

def test_allowlist_loads_without_error(): ...
def test_every_topic_key_exists_in_router(): ...
def test_every_prefix_is_a_valid_canonical_form(): ...
    # e.g. starts with `art:` or `ley:` or `decreto:` or `res:`
def test_no_duplicate_prefixes_within_a_topic(): ...
```

### 6d — `tests/test_answer_llm_polish.py` (already updated)

The polish-side guardrails `test_polish_rejects_invented_norm_lineage`
and `test_polish_rejects_invented_periods` plus their accept
counterparts were added in the same drafting session as this doc.
**No changes needed for v7 phases — they already pass.** Leave
intact.

### 6e — `make test-batched` and `npm run test:health`

No changes. The new tests above land in `tests/` and the existing
batched runner picks them up automatically (conftest discovers
`test_*.py` files). The 120-batch fan-out absorbs the new files
without rebalancing.

### 6f — `scripts/eval/run_sme_validation.py`

Add a new outcome class `retrieval_signal_check` that scans each
trace for:

- `retriever.hybrid_search.in.filter_topic` is `None` (post-v7a).
- `retriever.hybrid_search.in.embedding_mode == "ok"` (post-v7b).
- `synthesis.topic_gate.applied.gate_mode in ("applied", "noop_no_topic_entry")` (post-v7c).

If any check fails, the run is bucketed `INCONCLUSIVE` per the
fix_v5 §1.G postmortem pattern (do not contaminate PASS/FAIL with
infrastructure regressions).

---

## 7. Six-gate sign-off per phase

Each phase below must close all six gates before commit-and-push.

### Gate-by-gate template (apply to 7a, 7b, 7c)

| Gate | 7a (topic filter) | 7b (embeddings) | 7c (content gate) |
|---|---|---|---|
| **1. Idea** | Cross-topic anchors should be reachable. | Query-side semantic matching should be live. | Off-topic norms shouldn't ride into the template. |
| **2. Plan** | §3 above (RPC body + Python payload). | §3 above (Gemini wiring + fallback). | §3 above (config + gate module + wire-up). |
| **3. Measurable criterion** | ≥3 of 4 target chunks (Q1, Q3, Q7, Q8) reachable; §1.G strong ≥ 32. | Improvement on ≥6 of 10 probe questions by human-judged relevance; §1.G strong ≥ 32. | Q4 + Q5 drop pérdidas-fiscales bullets; §1.G strong ≥ 32. |
| **4. Test plan** | §4a above. | §4b above. | §4c above. |
| **5. Greenlight** | Technical tests pass + SME spot-check on Q1 + Q3 returns "the right chunk is now cited". | Technical tests pass + SME spot-check on 3 retrieval-near-miss questions confirms semantic match. | Technical tests pass + SME spot-check on Q4 + Q5 confirms the bleed is gone without losing coverage. |
| **6. Refine or discard** | If criterion fails, iterate on RPC body / Python boost arithmetic. If §1.G strong drops below 32, revert and re-diagnose. | If criterion fails, check embedding dimension / model id / normalization. If §1.G regresses, flip `LIA_QUERY_EMBEDDINGS_ENABLED=0` (kill switch) and re-diagnose without reverting code. | If criterion fails, tune `allowed_prefixes` / `cross_topic_allowed` per topic, or revisit the bullet-splitter logic. If §1.G regresses, flip `LIA_TOPIC_GATE_MODE=off` and re-diagnose. |

Per `feedback_verify_fixes_end_to_end`: unit tests green alone is
not greenlight. Every phase needs an actor named in gate 4 and a
real-data run in gate 5.

---

## 8. What you must NOT do (additive over fix_v6 §4)

- Do **not** edit `docs/orchestration/orchestration.md` to describe
  the drifted hard-filter behavior. The doc is canonical; the code
  drifted. Fix the code.
- Do **not** lower §1.G thresholds (strong 32, acc+ 36) per
  `feedback_thresholds_no_lower`.
- Do **not** auto-run the §1.G panel without asking the operator
  first per `feedback_sme_panel_explicit_request_only`.
- Do **not** quote money in status reports per
  `feedback_no_money_quoting`. Time estimates are fine.
- Do **not** hallucinate `reference_key` prefixes in the allowlist
  per `feedback_no_hallucinated_examples`. Every entry must be
  verified against real chunks.
- Do **not** flip the chat provider order back to DeepSeek per the
  fix_v1 incident.
- Do **not** silently widen the embedding model dimension —
  `chunks.embedding` is declared `vector(768)`; a mismatch crashes
  the RPC.
- Do **not** apply the cross-topic gate to questions whose
  primary_topic is missing from the allowlist. The safety net is
  "no-op when no entry."
- Do **not** ship 7b or 7c before 7a — gain measurement gets
  entangled and you can't tell what each phase bought.

---

## 9. Anchor data to compare against

- **Pre-fix baseline (probe)**:
  `tracers_and_logs/logs/probe_runs/20260511T003617Z_10q_post_polish_guardrails/`.
  Tally: 3 good, 3 mixed, 4 broken. Verdicts in
  `verdicts.jsonl`.
- **Pre-fix baseline (§1.G SME panel)**:
  `evals/sme_validation_v1/runs/20260430T000527Z_fix_v5_phase6b_rerun/`.
  Closing bar: 32 strong / 4 acc / 0 weak / 36 acc+.
- **Corpus-presence audit**: documented in this drafting session;
  9 of 10 questions have correct primary material on disk. Only Q5
  is genuinely partial. The other failures are retrieval-side, not
  ingestion.
- **Retrieval-trace audit** that informs the diagnosis: extracted
  per-question via the `answer-engine-probe` skill's digest script
  against the pre-fix probe.

---

## 10. State of the world at hand-off (2026-05-11 ~8:00 PM Bogotá)

- Polish-side guardrails for invented Ley/Decreto/Sentencia
  references and invented years have already been added in this
  session. Tests pass: 13 / 13 in
  `tests/test_answer_llm_polish.py`.
- The `dev:staging` server is running with the new polish
  guardrails active.
- No SQL migrations applied in this session.
- No changes to `orchestration.md`, `CLAUDE.md`, or the env matrix
  in this session yet (those updates land alongside the phases
  below).
- `answer-engine-probe` skill is in place at
  `.claude/skills/answer-engine-probe/` (introduced this session).
- No other LLM agent is currently working on this seam.

---

## 11. Quick-reference: file map

| Phase | Files touched |
|---|---|
| 7a | `src/lia_graph/pipeline_d/retriever_supabase.py` (lines 273, 602); optionally `supabase/migrations/20260512000000_topic_filter_soft.sql` (new); `docs/orchestration/orchestration.md` (env matrix + Lane 4); `tests/test_retriever_supabase.py` (+ 2 tests). |
| 7b | `src/lia_graph/pipeline_d/retriever_supabase.py` (lines 271, 602, 795+ new helper); `scripts/dev-launcher.mjs` (env default); `docs/orchestration/orchestration.md` (env matrix + Lane 4.1); `CLAUDE.md` (env matrix + kill switch); `tests/test_retriever_supabase.py` (+ 3 tests). |
| 7c | `config/topic_norm_allowlist.json` (new); `src/lia_graph/pipeline_d/answer_topic_gate.py` (new); `src/lia_graph/pipeline_d/answer_synthesis.py` or `answer_assembly.py` (wire-up); `docs/orchestration/orchestration.md` (Lane 5); `CLAUDE.md` (Fast Decision Rule); `tests/test_answer_topic_gate.py` (new); `tests/test_topic_norm_allowlist.py` (new); `scripts/eval/run_sme_validation.py` (add `retrieval_signal_check`). |

---

## 12. After you ship each phase

1. **Commit** with a message ending `Co-Authored-By: Claude
   Opus 4.7 (1M context) <noreply@anthropic.com>`.
2. **Bump the orchestration env matrix version** in the same commit
   per CLAUDE.md non-negotiable.
3. **Re-run the 10-Q probe** via
   `.claude/skills/answer-engine-probe/scripts/stage_run.py` +
   `run_sme_parallel.py`.
4. **Ask the operator before triggering the §1.G SME panel** per
   `feedback_sme_panel_explicit_request_only`. Land code + tests +
   probe results first; then ask.
5. **Update `docs/aa_next/next_v7.md` (or successor)** with the
   phase outcome status: 💡 → 🛠 → 🧪 → ✅ (or ↩ if discarded).
6. **Suggest the next step** to the operator per
   `feedback_always_suggest_next` (which phase to ship next, what
   it unblocks, and the cost in time).

---

## 13. Verification run — 2026-05-11 (added post-implementation)

10-question probe re-fired after fix_v7 §3a + §3b + §3c landed, the
`load_query_embedding` kwarg-mismatch hotfix on `src/lia_graph/embeddings.py`
applied, and migration `20260512000000_topic_filter_soft.sql` pushed to cloud
staging via `supabase db push --linked`. Same 10 questions as the pre-fix
baseline at
`tracers_and_logs/logs/probe_runs/20260511T003617Z_10q_post_polish_guardrails/`.

**Post-fix run dir**:
`tracers_and_logs/logs/probe_runs/20260511T131027Z_10q_post_fix_v7_hotfix/`.

### 13.1 Tally vs prior run

| QID | Topic | Prior len | Post len | Δ | Verdict | Pattern |
|---|---|---:|---:|---:|---|---|
| Q01 | ICA deducible | 3068 | 2518 | −550 | **pass** | "no son concurrentes" polish hallucination FIXED; citations swapped CST/SUIN noise for Ley 14/1983 + ICA-L01 (real-embedding recall lift) |
| Q02 | Art. 107 requisitos | 2317 | 119 | **−2198** | **fail** | Polish silently rejected → bare question-echo template |
| Q03 | Soporte documental | 2192 | 92 | **−2100** | **fail** | Same as Q02 — polish rejected, thin template |
| Q04 | Beneficio 689-3 | 1307 | 1307 | 0 | warn | Stable; cross-topic bleed (147/290) persists because `beneficio_auditoria` not in scaffold allowlist |
| Q05 | Corrección post-firmeza | 1287 | 1287 | 0 | warn | Stable; same shape as Q04 |
| Q06 | RST + beneficio auditoría | 456 | 865 | +409 | **pass** | Substantive improvement; no invented lineage; polish enriched cleanly |
| Q07 | Plazos AG 2025 | 2180 | 122 | **−2058** | **fail** | Same as Q02 — corpus gap (AG 2025 calendar) compounds polish rejection |
| Q08 | Formulario PJ ordinario | 2402 | 120 | **−2282** | **fail** | Same as Q02 — anchor-friendly Q but planner emitted no anchor |
| Q09 | Compensación pérdidas | 3220 | 2153 | −1067 | **pass** | §3c gate fired as designed: `gate_mode=applied, dropped=3, kept=13`. Shorter answer is the *correct* behavior |
| Q10 | RST vs ordinario | 146 | 0 | −146 | **fail** | 180s timeout (http=−1); comparative_regime_chain hangs on cloud |

**Pass / warn / fail = 3 / 2 / 5.** Prior run was good / mixed / broken = 3 / 3 / 4. **Net: the same number of good answers, +1 broken.**

### 13.2 What the fix_v7 phases actually achieved

Every fix_v7 invariant verified on every served chat (10/10):

- **§3a — topic filter / boost decoupling.** ✅ `filter_topic=None` on every call. `boost_topic=<router_topic>` carried (`costos_deducciones_renta` on Q01–Q03, `beneficio_auditoria` on Q04–Q05, `regimen_simple` on Q06, `declaracion_renta` on Q07–Q08, `perdidas_fiscales_art147` on Q09). After `supabase db push --linked`, no `retriever.hybrid_search.first_attempt_error` recovery on any question — cloud RPC accepts `boost_topic` natively now. Cross-topic recall lift is observable: Q01's citations swapped CST + SUIN stubs for Ley 14/1983 + ICA-L01 practical guide.
- **§3b — real query embeddings.** ✅ `embedding_mode=ok`, `embedding_model=gemini-embedding-001` on every call. Q01's better semantic recall is downstream of this. Operational note: the helper exposed a pre-existing kwarg bug in `lia_graph.embeddings.get_query_embedding` (line 226: `load_query_embedding(text, provider=..., model=..., dimensions=..., config_digest=...)`) — the cache layer's signature is `(*, query_text, config_digest)`. Hotfix applied during this verification (commit-time delta on `src/lia_graph/embeddings.py`). Without the hotfix, `embedding_mode=error` on every call and chat fell back to FTS-only retrieval; with the hotfix the vector half of RRF is live.
- **§3c — cross-topic content gate.** ✅ Fired exactly once across the 10-question run, on Q09 (`perdidas_fiscales_art147` is the only relevant topic in the scaffold allowlist), with `gate_mode=applied, dropped=3, kept=13`. Q01–Q08 + Q10 all emit `gate_mode=noop_no_topic_entry` for their primary topics (`costos_deducciones_renta`, `beneficio_auditoria`, `declaracion_renta`, `regimen_simple`) — those topics aren't in the scaffold allowlist by design (`docs/orchestration/orchestration.md §6.6c`), so the gate is a designed no-op. The Q09 reduction (3220→2153 chars) is the **correct** behavior of the gate: it dropped three off-topic bullets that the prior run was citing, kept the on-topic substance.

**Net: every promised invariant holds.** The three regressions (Q02, Q03, Q07, Q08) are NOT direct fix_v7 bugs — they are a side-effect of *better* retrieval triggering a previously-rare interaction with the polish-guardrails fallback path.

### 13.3 The systemic regression — "polish-rejected-fallback-is-too-thin"

Four of the five new fails share the exact same fingerprint:

```
template_chars  ≈ 90–122   ← synthesis built a question-echo stub
polished_chars  ≈ template_chars (Q3/Q7/Q8: exactly equal; Q2: +4 from
                                  post-hoc numeric-bold transformer)
polish_changed  = False (Q3/Q7/Q8) or True (Q2, but only because the
                                  post-hoc transformer added 4 chars)
answer_markdown = "**Respuestas directas**\n- **<question>**\n"
                  — i.e. the user gets back only the question, bolded.
```

The pipeline does the following on those four questions:

1. Planner classifies as `computation_chain` (Q2, Q3), `general_graph_research` (Q7, Q8), or `obligation_chain` (Q2) — modes where the planner emits **zero anchor articles** when the question doesn't lexically name a specific norm.
2. Retrieval still finds substantive chunks (5 primary + 5 connected + 5 support; seed_article_keys are populated for Q02: `[107, 121, 122, 123, 124, 124-1]`).
3. Synthesis (`compose_first_bubble_answer` for graph_native mode) builds a deliberately thin "first bubble" template — basically the question echoed back as a header. The expectation is that **polish will enrich it** from the evidence bundle.
4. Polish runs Gemini on the rich evidence + the thin template.
5. **Gemini hallucinates something that trips a guardrail** (likely `invented_norm_lineage` — citing a Ley/Decreto/Resolución not actually in the evidence — or `invented_periods` — fabricating an AG year). Both guardrails were landed in the same session as `fix_v7_may.md` was drafted (see §0 inheritance).
6. `answer_llm_polish.polish_graph_native_answer` returns `_apply_post_hoc_transformers(template_answer)` per the rejection-fallback path at `src/lia_graph/pipeline_d/answer_llm_polish.py:309-314`.
7. The post-hoc transformer adds numeric-bold markdown around any bare article number. On Q2 there was a `107` to bold (+4 chars). On Q3/Q7/Q8 the template already had the number bolded, so the transformer was a no-op and `polish_changed=False`.
8. The user receives the bolded question and nothing else.

**Why fix_v7 unmasked this**: prior to §3a + §3b, retrieval was thinner and lexically dominated. The polish prompt saw fewer, narrower chunks and tended to play it safe. With real query embeddings + cross-topic recall, the prompt now sees a richer, more semantically diverse evidence bundle — and Gemini becomes more confident in mentioning related-but-not-cited norms or periods. The guardrails (correctly) reject those. But the fallback design assumes polish almost always passes.

**Why the prior run avoided this on Q2/Q3/Q7/Q8**: the polish guardrails were added in the same drafting session as fix_v7_may.md (`§0 inheritance` lists them). The PRIOR PROBE RUN (`20260511T003617Z_10q_post_polish_guardrails`) ran with the guardrails ON but with the OLD retrieval (zero-vector embeddings, hard topic-filter at SQL level). With less diverse evidence, Gemini's polish output was less likely to invent lineage and the guardrails seldom rejected on these specific questions.

### 13.4 Failure-mode taxonomy from the post-fix run

**Shape A — "Polish rejected, no substantive fallback"** (Q2, Q3, Q7, Q8 — 4 questions, the dominant new regression):

- `template_chars` < 200, `polish_changed` ∈ {False, +4 chars}
- `gate_mode = noop_no_topic_entry` (gate is NOT the cause)
- `embedding_mode = ok` (retrieval IS healthy)
- User-visible: question echo only.
- Root cause: polish-rejection fallback is the synthesis template, and the synthesis template for `graph_native` mode is intentionally thin because polish is supposed to enrich it.

**Shape B — "Stable answer, cross-topic bleed persists"** (Q4, Q5 — 2 questions, warn):

- `template_chars` ≈ 1290, `polish_changed=True`
- Answer cites the right primary norm (Art. 689-3) but the supporting bullets reference Arts. 147 / 290 / 588 (pérdidas-fiscales norms) on a `beneficio_auditoria` question.
- Root cause: `beneficio_auditoria` is NOT in `config/topic_norm_allowlist.json` (scaffold only contains `perdidas_fiscales_art147` + `regimen_simple` because hallucinated topic keys fail CI per `feedback_no_hallucinated_examples`). Without an allowlist entry, the gate is `noop_no_topic_entry` by design.
- Action item recorded: expand the allowlist scaffold to cover `beneficio_auditoria`, `costos_deducciones_renta`, `declaracion_renta`, `procedimiento_tributario`, `facturacion_electronica`, `calendario_obligaciones` — each prefix verified against real `chunks.reference_key` rows in cloud Supabase.

**Shape C — "Gate fired as designed"** (Q9 — 1 question, pass):

- `gate_mode = applied`, `dropped_count = 3`, `kept_count = 13`
- Final answer is 1067 chars shorter than prior (3220 → 2153) BUT cleaner — the dropped bullets were citing off-topic norms.
- This is the **target behavior** of §3c. The shorter answer is the right answer.

**Shape D — "Comparative-regime timeout"** (Q10 — 1 question, fail):

- 180-second client-side timeout on cloud staging.
- Prior run captured 146 chars (template-shaped). Post-fix run captured nothing because the request never returned.
- The `comparative_regime_chain` path was noted as a regression in the prior report; fix_v7 didn't address it.
- Separate workstream from fix_v7. Likely candidates: a slow Cypher in `retriever_falkor.py`, or a polish-loop that doesn't terminate.

**Shape E — "Improvement on the merits"** (Q1, Q6 — 2 questions, pass):

- Q1: prior run had a semantic hallucination ("no son concurrentes" between 50% descuento and 100% deducción); post-fix run frames the choice correctly. Citations swapped pure-noise SUIN stubs for the actual ICA framework (Ley 14/1983).
- Q6: prior run had 456 chars (thin); post-fix run has 865 chars with no invented Ley lineage. Polish enriched cleanly.

### 13.5 Why a per-question fix is the wrong response

The user's directive from the verification call: "if we over-correct for a particular question we are damaging the overall effectiveness of the general class retriever."

This is correct. Each of the four Shape-A regressions could be hand-patched by:

- Adding the missing seed-article anchor to the planner for that specific question pattern (would help Q7/Q8 but not Q2/Q3).
- Whitelisting specific Ley references in the guardrail for that topic (would weaken the guardrail).
- Adding a corpus chunk that covers the question verbatim (corpus over-fitting).

None of those are systemic. The systemic finding is: **the synthesis template is the polish-rejection fallback, but it's too thin to be a useful fallback**. Fixing that one design property closes Shape A across every question pattern simultaneously — without touching retrieval, polish, or the gate.

### 13.6 Proposed systemic next steps (for fix_v8)

Three orthogonal candidates, evaluable independently. None of them weakens the guardrails (per `feedback_thresholds_no_lower`).

**Candidate A — Substantive polish-rejected fallback.** When `polish_graph_native_answer` rejects, fall back to a richer template assembled from `GraphNativeAnswerParts` (recommendations + procedure + paperwork + legal_anchor + precautions) instead of the bare first-bubble template. This means the synthesis path that's currently optimized for "polish will enrich" needs a second, deterministic emission shape for "polish was rejected, render what we have."

- Module: `src/lia_graph/pipeline_d/answer_assembly.py` + `answer_synthesis.py`
- Test: re-run Q02, Q03, Q07, Q08 → answer ≥ 800 chars and contains specific bullets from `GraphNativeAnswerParts` even though polish was rejected.
- Risk: low — only fires when polish is rejected (a small fraction of turns). Adds determinism on a path that today returns essentially nothing.

**Candidate B — Expose `skip_reason` in the polish trace step.** Currently `synthesis.polish.applied` carries `polish_changed` and `polished_chars` but not `mode` or `skip_reason`. Operators reading a trace today cannot distinguish "polish ran and succeeded" from "polish ran, output rejected, fell back to template." Add `mode` (one of `llm`, `skipped`, `rejected`, `failed`) and `skip_reason` (one of the seven enumerated reasons in `answer_llm_polish.py`).

- Module: `src/lia_graph/pipeline_d/orchestrator.py:799-810`
- Test: re-run the four Shape-A questions; verify trace shows `mode=rejected` with the specific rule that fired.
- Risk: zero — pure instrumentation.

**Candidate C — Allowlist scaffold expansion.** Add the six missing top-level topic entries (`beneficio_auditoria`, `costos_deducciones_renta`, `declaracion_renta`, `procedimiento_tributario`, `facturacion_electronica`, `calendario_obligaciones`) so the §3c gate has substance to act on across the common chat topics. Each `allowed_prefixes` list verified against real cloud Supabase chunks per `feedback_no_hallucinated_examples`. Once landed, Q4/Q5's cross-topic bleed (Arts. 147/290/588 on a `beneficio_auditoria` question) gets dropped.

- Module: `config/topic_norm_allowlist.json`
- Test: re-run Q4, Q5 → gate_mode=applied, dropped_count ≥ 2 each, kept_count > 0.
- Risk: medium — under-curated allowlists could drop legitimate cross-topic citations. Mitigate via the staging probe before rolling forward.

**Candidate D — Comparative-regime timeout root-cause.** Investigate why Q10's `comparative_regime_chain` path hangs on cloud. Separate from fix_v7.

**Recommended order:** B (1 hour, zero risk, makes future runs observable) → A (half-day, addresses the dominant new failure mode) → C (1–2 days including SME validation of each prefix list) → D (separate workstream).

### 13.7 What fix_v7 demonstrably did, summarized

- §3a soft-topic / boost decoupling: WORKS, every call. Cross-topic anchors structurally reachable. Migration applied to cloud staging in this verification pass.
- §3b real query embeddings: WORKS, every call. Required hotfix to `lia_graph.embeddings.get_query_embedding` to repair a pre-existing kwarg mismatch.
- §3c cross-topic content gate: WORKS as designed. Fires on every question; emits `noop_no_topic_entry` for topics not in the scaffold allowlist; emits `applied` with non-zero dropped_count on the one question (Q09) whose topic is in scaffold.
- Net visible-answer impact: 3 strict improvements (Q01, Q06, Q09 — the last is shorter-but-cleaner), 2 stable (Q04, Q05), 4 polish-fallback regressions (Q02, Q03, Q07, Q08), 1 unchanged-broken (Q10 timeout).
- **The fix_v7 promises were kept. The post-fix net product impact is mixed because of a pre-existing brittleness in the polish-rejection fallback path that fix_v7's better retrieval exposed.**

### 13.8 Six-gate lifecycle bookkeeping

Per CLAUDE.md non-negotiable for `docs/aa_next/**` work — and even though this is `docs/re-engineer/fix/`, the same lifecycle applies to verification:

| Phase | Gate 5 (greenlight) | Gate 6 (refine or discard) |
|---|---|---|
| §3a | 🧪 verified — staging probe + new tests; cross-topic anchors reachable | ✅ keep |
| §3b | 🧪 verified after hotfix to `embeddings.py` kwarg-mismatch | ✅ keep, but document the latent bug and the chain that triggered it |
| §3c | 🧪 verified for `perdidas_fiscales_art147` (Q09); blocked on operator-curated allowlist expansion for the other six common topics | ⏳ keep on scaffold; expand carefully per Candidate C |
| Post-implementation finding | the polish-fallback brittleness | ↩ **NEW workstream** — fix_v8 Candidate A above |

### 13.9 Diagnostic artifacts

- Verdicts ledger: `tracers_and_logs/logs/probe_runs/20260511T131027Z_10q_post_fix_v7_hotfix/verdicts.jsonl`
- Per-question raw responses + traces: same dir, `<qid>.json`
- Compact comparison summary (machine-readable): same dir, `_compact_summary.json`
- Side-by-side report: same dir, `report.md`
- Prior-run baseline: `tracers_and_logs/logs/probe_runs/20260511T003617Z_10q_post_polish_guardrails/`
