# Lia Graph — Executive Summary

> **For:** the founder.
> **Round:** 3 (post-Activity-1.5/1.6 + plan-execution-readiness). This document gets refreshed every round of the re-engineering work — re-read whenever you want a current-state read in 5 minutes.
> **As of:** 2026-04-26 late evening (Bogotá), after we tested the verification engine on 4 real Colombian tax norms and committed all the learnings.
> **Money committed (cumulative):** USD **525K** (Round 2 budget; Round 3 made the plan more rigorous within that envelope, no further bump).
> **Time committed (cumulative):** 14 weeks.
> **Companion docs (only if you want depth):** `makeorbreak_v1.md` (the analysis behind the decision), `fixplan_v2.md` (the current engineering plan; v1 is superseded), `skill_integration_v1.md` (what the skill changed), `activity_1_5_outcome.md` (the corpus-hallucination finding).

---

## ⚡ Latest update — Round 3 / 2026-04-26 late evening (Bogotá)

**What changed since Round 2:**

- **We tested the verification engine on four real Colombian tax norms today.** All four produced clean structured verdicts (1 declared inexequible by the Constitutional Court, 1 vigente-with-modifications, 1 derogated, 1 vigente with a transition regime). The team now has 4 of 7 possible "law states" validated against real cases — enough to move forward with confidence on the structural rebuild.
- **The verification engine caught a corpus hallucination on its first real test.** When we asked it to verify Decreto 1474/2025, it discovered our own corpus contains a fabricated court ruling (a "Sentencia C-077/2025" that does not exist — only Sentencia C-079/2026 is real). Without the engine's "verify with two sources, refuse if they disagree" discipline, this would have shipped to production. **This single finding justifies the entire $25K verification-engine budget bump from Round 2.**
- **Switched the AI model behind the verification engine from Anthropic to Gemini 2.5 Pro** (the version we already have an API key for). Cleaner stack, no new vendor, ~37% cheaper at corpus scale (~$300 vs ~$486). No quality trade-off — we explicitly rejected the cheaper "Flash" variant.
- **Engineering plan is now self-sufficient for a fresh engineer or LLM** to execute end-to-end. Added a "data contracts" section that specifies every script's input/output, the AI invocation mechanism, and the cost math. A new hire can read the plan and start coding any sub-fix without asking "but how do I actually call the verification engine?"
- **Six new engineering doctrine documents committed** to the codebase. Capture the patterns we discovered this round so the next engineer doesn't have to relearn them: how the verification engine catches what binary flags miss, why vigencia is a 2D problem (today's state × applicability per past period), the value of small surgical fixes that prove a hypothesis cheaply before a big rebuild, and why automated re-verification of laws is launch-critical infrastructure (not optional polish).

**What I need from you right now:** nothing this week. One small re-prioritization to flag for awareness — recommend moving the "automated re-verification" workstream from week 13 to week 4 (the new findings make it more critical than originally weighted; no budget impact; reasoning in a new learning doc). Next refresh: end of week 2.

---

## 1. Where we are, in one paragraph

We hired an outside accountant to test our product with 36 real questions; he reported 0 entregables and 6 dangerously wrong answers. We diagnosed the problem (the "outdated stickers" missing from the law library), funded a fix ($500K), and started executing. **Two things happened today that made the plan stronger:**

First, we shipped a small surgical fix (Activity 1 — turn on a vigencia filter that had been silently disabled). Result: the worst single offender (citing the repealed `art. 689-1`) dropped 85% in the answers where it was concentrated, but the overall metric didn't move because the underlying flag was too sparse to bite at scale. **We learned exactly what the next ship must do, with hard data.**

Second, an expert volunteered the design for the verification engine — a complete, rigorous protocol for checking Colombian-tax-law vigencia (when laws are current vs repealed vs suspended vs modified). She delivered ~1,400 lines of documentation in the form of a Claude Code Skill the team can invoke directly. **This collapses ~3 weeks of design work AND raises the quality ceiling significantly.** The trade-off: her protocol mandates double-source verification per article, which needs scraper infrastructure we hadn't budgeted. Net cost: $25K more than the original plan.

## 2. Why we are here, in plain language (unchanged from round 1)

Imagine a law library. Some books are current. Some are old editions of the same book. **Nobody put "OUTDATED" stickers on the old ones.** When somebody asks the librarian a question, the librarian grabs whichever book is closest at hand and reads from it confidently — sometimes the current edition, sometimes the 2010 edition that was repealed in 2016.

That is what our system is doing right now. We always knew Colombian tax law has this problem (laws change every year, articles get repealed, dollar amounts move with UVT every December) and we even built the shelves and labels for the "OUTDATED" stickers. **But we never actually printed the stickers and stuck them on the books.** The good news: the shelving system works. The fix is "go through the books and add the stickers" + "teach the librarian to skip the outdated ones."

**What's new this round:** the expert's skill IS the recipe for the stickers. She defines exactly what an outdated sticker should say (one of 7 categories: outdated, modified, suspended, etc.), what evidence we need before we can apply one (always 2 official sources), and what the librarian has to do when reading a book that has a sticker. She also designed the procedure for auditing what the librarian *already* told customers — "you cited the wrong edition; here's the correct one." This last piece becomes our quality test going forward.

## 3. What we are doing about it — the 6 fixes (unchanged in spirit; sharper in execution)

| # | What we're doing | The outcome you'll be able to verify |
|---|---|---|
| **1** | Mark every law in our system with whether it's still in effect (using the expert's 7-category system + her verification procedure), and teach the system to skip the ones that aren't. | When somebody asks "what's the deadline for declaration X," we never quote a rule that was repealed five years ago. **And** we can correctly answer historical questions like "what was the rule in 2018?" — distinguishing "current law" from "law that applied to that period." |
| **2** | Build a single source of truth for the dollar amounts and percentages that change every year (UVT, minimum wage, all topical thresholds), and inject the current-year value automatically. | When somebody asks a 2026 question, they get 2026 values. Today we sometimes give them 2024 values. |
| **3** | When the system doesn't know the answer, it has to say so cleanly. Today it makes up confident-sounding generic content. | An accountant can tell at a glance whether we actually answered or punted. Today they can't. |
| **4** | Audit every topic we claim to cover. If a topic has zero documents (yes, we found one — "tarifas de renta"), either populate it or stop advertising it. | Every topic we list as covered actually has source material behind it. |
| **5** | Build a fixed set of 100 questions where we already know the correct answer. The expert's "audit format" becomes our test format. If a code change breaks a known-good answer, it can't ship. | A safety net. Today we can ship code that silently breaks an answer that used to work. After this fix, we can't. |
| **6** | Where our own corpus contradicts itself (we found three different versions of the dividend tax table), pick the right one and mark the others as superseded. | The system stops giving answers that disagree with itself depending on which paragraph it happened to read. |

## 4. When you'll know it's working — the checkpoints (sharpened)

Three dates. You don't need to track weekly.

### Week 4 — the foundation check (mid-May)
The team will have built the scrapers (which fetch data from the 5 official sources the expert specified) and started running the verification protocol. **What you'll see:** a 5-minute walkthrough showing the system correctly classifies a sample of 30 articles as outdated/modified/current/etc. — with audit trails showing which official sources were consulted.
**What to do:** if it looks right, keep going. If not, the team adjusts and tells you.

### Week 6 — the kill switch (early June)
**This is the date that matters most.** The team will re-run the same 36 questions the SME tested originally, focusing on the three topics where the outdated-law problem was worst. **What you'll see:** a one-page report showing the count of bad citations.
- Citations of the repealed `art. 689-1`: must be **0** (we're at 2 today after Activity 1).
- "6-year deadline for firmeza" claims: must be **0** (it's 5 years since 2019).
- "10% dividend tariff" claims: must be **0** (it's 19%/35% by tier since 2022).
- The verification protocol's audit log must show 2 official sources consulted per check.

**What to do:** if all four pass, we keep going — the foundation is working. **If any fail, the project is in trouble.** Pause and reassess. This is the only checkpoint where I'll ask you to make a real decision.

### Week 14 — launch readiness (early August)
The team runs `make eval-launch-readiness` and you get a one-page green/red dashboard. If everything is green: soft-launch to 10–20 friendly accountants with explicit "beta" framing, instrumented for incidents. If something is red: the dashboard tells us exactly what's still broken.

## 5. What we are NOT doing — and why (unchanged from round 1)

- **No quiet launch with a "beta" disclaimer.** Disclaimers don't transfer the risk.
- **No more small tweaks to retrieval ranking.** We've done seven rounds; none addressed what the SME found. Stopped until foundation is fixed.
- **No lowering the quality bar to make metrics look better.** "Safe to send to a client" stays the standard.
- **No adding more documents to the corpus until the vigencia layer is in.** More docs in a system without vigencia tracking = more contamination.
- **No replacing the AI model with a "better" one as a shortcut.** Bottleneck is not the model.
- **No expanding scope beyond the 12 topics already in the SME validation set.** New topics come after launch.

**(NEW this round)** **No bypassing the expert's verification protocol for "convenience."** Engineers cannot write code that emits a vigencia classification without going through the protocol or getting an SME-signed manual override. This is the safety contract that prevents the kind of confident-hallucination the SME found.

## 6. Money and time — what changed

| Bucket | Round 1 (USD K) | Round 2 (USD K) | Why changed |
|---|---:|---:|---|
| Two senior backend engineers, 14 weeks | 200 | 200 | — |
| One floating senior engineer, 8 weeks | 60 | 60 | — |
| Frontend engineer, 4 weeks | 25 | 28 | 7 chip variants instead of 4 |
| SME (the outside accountant), half-time × 14 weeks | 90 | 75 | Skill design done — saves SME time |
| Cloud infrastructure | 4 | 6 | Added scraper hosting + cache |
| AI extraction cost | 1 | 1 | — |
| QA tooling | 30 | 27 | Skill provides judge schema |
| Data-ops engineer | 30 | 30 | — |
| **NEW: Scraper infrastructure** (5 official sources, cached) | — | 45 | The expert's protocol mandates 2-source verification per article; live web fetch is too slow at corpus scale |
| **NEW: Verification skill harness** | — | 15 | Wires the skill into our codebase |
| **NEW: 30-case skill eval set** | — | 15 | Tests if the skill captures known errors before we trust it at scale |
| **NEW: Re-verification cron + tests** | — | 15 | Vigencia goes stale; need scheduled re-checks |
| Reserve / contingency | 60 | 8 | Most of it absorbed by the new scraper work |
| **Total** | **500** | **525** | **+25** |

The reserve fell from $60K to $8K — most of the new work was absorbed by the existing reserve, with $25K of genuine new spend on top.

## 7. The first measurable results are in — Activities 1, 1.5, 1.6

**Activity 1** (the surgical SQL filter fix, shipped 2026-04-29): moved one specific number significantly (citations of the repealed `art. 689-1` dropped 85% in the answers where it appeared) but didn't move the overall quality metric. Proved the architecture works AND that the binary flag is too coarse to bite at scale — exactly why the bigger Fix 1B is needed.

**Activity 1.5** (verification engine on Decreto 1474/2025, run 2026-04-26 evening): the engine caught a corpus hallucination — our own corpus cites a court ruling ("Sentencia C-077/2025") that does not exist. The engine correctly refused to apply a database update based on the contradictory sources, and surfaced the issue for editorial correction. **Demonstrates the engine works end-to-end; demonstrates its discipline catches what flag-only approaches miss; identifies a corpus-wide audit candidate for the editorial workstream.**

**Activity 1.6** (verification engine on 3 canonical articles, same evening): produced clean verdicts for "vigente modified," "derogated," and "vigente with transition regime" cases. All three are now reusable test fixtures for the regression suite (Fix 5).

**Six hours of small surgical activities saved $80K of speculative full-fix work** by validating (or invalidating) hypotheses cheaply before committing.

## 8. What I need from you, the founder

**This week:**
1. Sign off on the new $525K total (you did, by approving the +$25K bump — but a written "go" to the team locks it in).
2. Tell the team publicly we are not shipping for 14 weeks (unchanged from round 1).

**Week 6, when the kill switch checkpoint runs:**
1. Read the one-page report (5 minutes).
2. Make the call: continue, adjust, or stop. The team gives you a clear recommendation; you make the decision.

**Otherwise:** I produce a refreshed version of this document at the end of weeks 2, 4, 6, 8, 10, 12, and 14. Each refresh is one page. If something goes wrong between refreshes, I tell you immediately.

## 9. The honest one-liner (updated)

**We tested the verification engine on four real Colombian tax norms today, caught a corpus hallucination on the first one, refined the plan to be cheaper and more rigorous, and committed all the learnings to the codebase. The engineering team can start the structural rebuild on Monday with a plan a fresh engineer can execute without asking questions.**

---

*Round 3 of N. Next refresh: end of week 2 (status of vigencia ontology Python implementation + first scraper milestones). After that, every two weeks until launch readiness or kill-switch.*
