# Re-Verify Cron is launch-critical infrastructure, not a "nice to have"

**Source:** Activity 1.5 outcome (`docs/re-engineer/activity_1_5_outcome.md`). Originally placed at week 13 of the 14-week plan in `fixplan_v2.md §11`; this learning is the case for moving it to week 4.

## What the cron is

A scheduled job that re-runs the vigencia-checker skill on every active corpus citation every N days, AND immediately when:

- A reforma tributaria is detected on Senado / SUIN-Juriscol
- A sentencia of fondo or auto de suspensión is detected on Corte Constitucional / Consejo de Estado
- A concept DIAN reconsideration is detected on DIAN Normograma

When the re-verification produces a different `Vigencia` veredicto than the cached one, the corresponding `documents.vigencia*` columns + Falkor `:ArticleNode.vigencia` properties are updated; flagged for SME review; and the Fix 5 golden judge re-runs the affected golden questions to surface any regressions.

## Why Activity 1.5 made it urgent

The Decreto 1474/2025 case showed three problems the cron exists to catch:

1. **The corpus's `T-I` document was correct in March 2026 but stale by April 2026** — Sentencia C-079/2026 (April 15) escalated SP → IE on a high-impact decreto, and the corpus didn't reflect it 11 days later when Activity 1.5 ran.
2. **The corpus's `EME-A01` document never had verification at all** — it cited a non-existent `Sentencia C-077/2025` and hallucinated dates, despite a "verificación: 20 marzo 2026" header. Without the cron's external-source check, this lives forever.
3. **Without the cron, the skill itself becomes stale** — the `.claude/skills/vigencia-checker/` references and checklists need re-validation as Colombian primary-source URLs evolve, statutes change, etc.

If we ship at week 14 without the cron, we ship a system that knows the right answer on day 1 and is wrong by day 30. **For Colombian tax law specifically, "wrong by day 30" is the regular case, not the edge case** — there's a reforma tributaria most years, sentencias de fondo land monthly, conceptos DIAN reconsiderations are weekly.

## The lag math

Per the data we have:

- Sentencia C-079/2026 was published Apr 15, 2026.
- The stale T-I corpus document was last updated Mar 20, 2026.
- The first time the corpus's wrongness would be caught (without cron) is when the next manual SME audit runs — undefined cadence; in practice, only when somebody noticed (which Activity 1.5 did, by accident).
- An average sentencia-induced staleness window WITHOUT cron: probably 2-12 weeks.
- WITH cron at 90-day cadence: capped at 90 days for routine drift, ~24 hrs for triggered re-verification on detected reforma / sentencia.
- WITH cron at 30-day cadence: capped at 30 days for routine drift; same ~24 hrs for triggered re-verification.

## The cost vs. the launch risk

Cron cost (per `fixplan_v2.md §11`):
- Engineering: 0.5 engineer × 1 week = ~$8K
- LLM cost per re-verification pass (skill on ~7,883 articles, mostly cache-hits after first run): ~$50/month
- Scraper polling cost (5 sources × N articles × ~$0 LLM, just web fetches with cache): ~$10/month

Launch risk WITHOUT the cron: every SME-curated answer ships with a half-life of weeks. The first viral "LIA cited a derogated article" tweet is when the cron's absence becomes a $millions of brand damage. The cron is among the cheapest insurance available — the dollar ratio of cron cost to launch risk is approximately 1 : 1000.

## The rule that survives

**For any product whose correctness depends on a moving target (Colombian tax law, US tax law, regulatory environments, drug labels, security advisories), automated re-verification is launch-critical infrastructure. Treat it as a Fix 1 dependency, not a Fix 6 polish.**

Without the cron:
- The skill protocol can produce correct veredictos on day 1 but provides no mechanism to detect when those veredictos go stale.
- The corpus + the materialized vigencia metadata are point-in-time snapshots that decay.
- Every SME-curated correction (Fix 6) becomes itself a future stale-content candidate.

## What this changes in `fixplan_v2.md`

Moving Re-Verify Cron from week 13 → week 4:
- Engineering hours unchanged ($8K).
- Engineer assignment shifts: pull from Fix 6 SME-supporting bandwidth (which doesn't start until week 9 anyway).
- Cron triggers Fix 5 golden-judge re-runs on detected delta — gives us a sentinel for regression in production.
- Cron polling against external sources also pre-warms the Fix 1B-α scraper cache, reducing Fix 1B-β extractor cost.

Recommended sequence (revised):
- Week 1-2: Fix 1A ontology + cron schema design.
- Week 3-4: Fix 1B-α scrapers (their cache is what the cron consumes).
- Week 4-5: Cron deployment using the scrapers; first wave of re-verifications on existing corpus citations.
- Week 6 onwards: cron runs at 90-day routine + reform/sentencia trigger; results feed Fix 1B-γ materialization continuously.

This sequencing means the cron is operational ~2 months before launch instead of the same week, giving us real data on staleness rates before we commit to a soft-launch.
