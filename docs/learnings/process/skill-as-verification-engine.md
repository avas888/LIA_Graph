# The expert-skill pattern: gate-1+2 design closure by external SME

**Source:** Vigencia-checker skill delivered 2026-04-26 evening by an external SME (1,428 LOC across `.claude/skills/vigencia-checker/`). Integration analysis at `docs/re-engineer/skill_integration_v1.md`. Validated end-to-end via Activity 1.5 (`docs/re-engineer/activity_1_5_outcome.md`).

## What happened

I had drafted a Vigencia ontology in `fixplan_v1.md §2.1` — 6 states, single timeline, basic dataclass. Workable but underspecified. An external SME volunteered to design the verification protocol; she delivered a complete Claude Code Skill with:

- 7-state taxonomy (V/VM/DE/DT/SP/IE/EC) where my version had 6 (missed VM, DT distinct from DE, IE distinct from DE, EC entirely)
- 2D model: `(norm, periodo_fiscal) → (state, applicability)` where my version had a single timeline
- Burden-of-proof inversion: no veredicto without ≥ 2 primary sources
- Audit-LIA TRANCHE format for evaluating existing answers
- 3 procedural checklists (artículo-ET, decreto, resolución-DIAN)
- Source hierarchy with explicit URL conventions

**The skill closed Gate 1 + Gate 2 of the six-gate lifecycle for Fix 1A entirely.** I went from "design + implement + iterate over 3 weeks" to "implement what's already designed, in 2 days."

## The cost-side surprise

The skill's protocol mandates double-primary-source verification per article. My naive plan was a single LLM extraction call (~$60-120 batch cost). The skill's protocol requires per-article tool-using agent loops with web fetches against 5 primary sources. At corpus scale (7,883 articles), this needs scraper infrastructure I hadn't budgeted: ~$45K of scraper engineering + ~$15K of harness wiring + ~$15K of skill eval set + ~$8K of re-verification cron = $83K of new work, mostly absorbed by the existing $60K reserve, with $25K residual.

**Net trade:** the skill is "free" as design work but creates ~$25K of delivery cost on top. Worth it: the resulting plan is substantially more rigorous than my $500K original.

## The validation surprise

Activity 1.5 ran the skill manually on Decreto 1474/2025 (the cleanest test case from the SME inventory). The skill protocol's burden-of-proof discipline immediately caught:

- A corpus internal contradiction between two documents about the same Decreto
- Hallucinated content in one of them (a fabricated `Sentencia C-077/2025` that does not exist)
- Stale content in the other (correct as of March 2026 but didn't reflect the April 2026 sentencia of fondo)

A wholesale-flag pipeline (without dual-source verification) would have either trusted the hallucinated source or trusted the stale source. Both produce wrong UPDATE actions. **The skill's discipline of "refusing IS success when sources disagree" prevented a real production write that would have damaged retrieval.**

## The rule that survives

**When an external expert delivers a complete protocol design, treat it as gate-1 + gate-2 closure for the relevant fix.** Implement it (gate 3) and test it (gate 4) directly; don't re-derive the design from scratch. The expert's investment is real value the team should consume, not duplicate.

Two implementation discipline corollaries:

1. **Burden-of-proof inversion is engineering discipline, not just a research norm.** Apply it in code: any function that emits a vigencia / classification / verdict must be CAPABLE of returning "I don't know" structurally (not a `confidence_score` that callers will quietly threshold to 0). The skill's `VigenciaResult.veredicto: Vigencia | None` shape forces this — `None` means refused, full stop.
2. **Skill content + invocation harness are different things.** The expert delivers the protocol (the WHAT). We build the harness (the HOW — Python wrapper, tool registry, output parsing). Don't conflate "the skill is delivered" with "the integration is done." See `fixplan_v2.md §0.8` for the full data-contracts + invocation spec.

## What this changes for future external contributions

Going forward, any complex design problem that has a clear domain expert is a candidate for the expert-skill pattern:

- **Colombian labor law vigencia** (CST, Ley 50/1990, Ley 789/2002, etc.) — same shape; different source hierarchy
- **Cambiario regime verification** (Resolución Externa 1/2018 JDBR + DCIN-83) — same shape; Banco de la República as the primary source
- **Municipal ICA / predial vigencia** — same shape; per-municipio gaceta as the primary source

In each case, the structural fix is the same: external expert designs the protocol; we build the scraper + harness + eval. **Roughly 3-4 weeks of expert time produces 3-4 months of saved engineering design time, plus a higher quality ceiling.** The cost is on the execution side (scrapers + caching + harness), not the design side.

## What this does NOT change

- Engineers still own implementation discipline and test design. The expert's protocol is the spec; the test plan that proves it works is the engineer's responsibility.
- The six-gate lifecycle still applies. Skill delivery closes gates 1+2; the engineer still needs to ship gate 3 (working code), gate 4 (test plan execution), gate 5 (target-env evidence), gate 6 (refine-or-discard if validation fails).
- "It's the expert's design" is not a defense if the implementation drifts from the protocol. The audit-LIA TRANCHE format must produce exactly the schema the skill defines, every time, or downstream consumers (Fix 5 judge, Fix 6 editorial) will silently miscompute.
