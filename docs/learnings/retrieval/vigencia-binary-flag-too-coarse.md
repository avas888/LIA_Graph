# Vigencia binary flag is too coarse to bite at scale

**Source:** Activity 1 (`docs/re-engineer/fixplan_v2.md §8`) — the SQL-only surgical fix shipped 2026-04-29. Migration `supabase/migrations/20260429000000_vigencia_filter_unconditional.sql`. Companion learning to `docs/learnings/retrieval/hybrid_search-overload-2026-04-27.md`.

## What we shipped

The `hybrid_search` SQL function had an existing vigencia filter (`vigencia NOT IN ('derogada', 'proyecto', 'suspendida')`) but it was **silently disabled** when the planner passed `filter_effective_date_max` (the common case). Activity 1 removed the bypass — vigencia filter now applies unconditionally. One SQL line; idempotent migration; zero new code.

## What we measured

Clean before/after on the §1.G SME 36-question fixture:

| Probe | Before | After | Delta | Read |
|---|---:|---:|---:|---|
| `art. 689-1` mentions (target) | 13 occurrences in 2 qids | 2 occurrences in 1 qid | **−85%** ✅ | Clean structural win on the one case the binary flag DOES catch |
| `Ley 1429/2010` mentions | 303 occurrences in 23/36 qids | 286 occurrences in 23/36 qids | **−5%** ⚠️ | Binary flag does NOT catch this — Ley 1429 article bodies don't self-announce derogation |
| `6 años firmeza` (stale claim) | 13 occurrences in 2 qids | 19 occurrences in 4 qids | **+46%** ❌ | Spread to 2 NEW qids — chunk reshuffle let stale "6-año" patterns through |
| `10%` dividend tariff (stale) | 0 | 3 in `dividendos_P2` | **new** ❌ | Same chunk-reshuffle dynamic |
| Auto-rubric `served_acceptable+` | 21/36 | 21/36 | **0** ➡️ | Class assignments unchanged; auto-rubric measures form, not fact |

## What we learned

**Activity 1 was structurally correct AND structurally insufficient.** The bypass really was a bug; removing it was the right thing. But the impact was bounded by the binary flag's coverage, which is set by a regex at `parser.py:234`:

```python
status = "derogado" if DEROGATED_RE.search(full_text) else "vigente"
```

This catches articles that **self-announce derogation in their own text** (e.g., `art. 689-1` has "derogado por art. 51 Ley 2155/2021" in its body — caught). It does NOT catch:

- Documents that don't self-announce (Ley 1429/2010 article bodies don't say "derogado" — most are repealed but the text doesn't say so)
- Stale claims about firmeza, plazos, tarifas that pre-date a law change but don't say "derogado" anywhere
- Articles whose vigencia depends on a court ruling (IE / SP / EC), not a legislative repeal
- Articles with parágrafo-level vigencia divergence (one parágrafo derogated, others vigente)

## The chunk-reshuffle gotcha

Removing chunks that were `derogada=true` from the result set let DIFFERENT chunks rise to the top — sometimes chunks containing the same stale claim from a non-derogated source. This produced a measurable regression on `6 años firmeza` (+46%) and `10% dividendo` (+3 from 0). **The lesson:** binary filters in retrieval can be net-zero or worse if the filter's coverage doesn't dominate the chunk pool.

## The rule that survives

**Surgical activities measure two things at once:**

1. The thing they targeted (here: derogated-article citation rate).
2. The chunk-reshuffle ripple (here: what fills the gap when filtered-out chunks disappear).

Always grep for at least 3-4 stale-content patterns in the verbatim, not just the targeted one. Use `regex_per_pattern × before/after × {qids, occurrences}` as the measurement matrix. A clean win on probe 1 with a regression on probe 2 is a real result, not a failure — but it must be reported, not hidden.

## What this motivates downstream

The full structured `Vigencia` value object (Fix 1A in `fixplan_v2.md`), populated by skill-guided extraction (Fix 1B-β), populates the existing `documents.vigencia*` columns + new structured fields with **per-article granularity** based on **double-primary-source verification**, not regex on the article's own text. The same retrieval filter then fires correctly across 100% of the corpus, not just the regex-caught subset.

**Activity 1's measured outcome is the gate-3 evidence that justifies Fix 1B-β's $30K LLM-extractor budget + Fix 1B-α's $45K scraper-infrastructure budget.** Without Activity 1's data, we'd be guessing about whether the structural rebuild was worth it. With it, we know: yes, and approximately how much it must move the needle to be worth shipping.
