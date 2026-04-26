# Deep-trace before debating hypotheses

> **Captured 2026-04-25** from the `next_v4 §3` deep trace that ruled out H1 and structurally confirmed H2+H3 (collapsed into Frontiers 1+2+3) in a single pass — without writing any harness or running any A/B.

## When to reach for this

You have a symptom (a refusal, a contamination, a wrong route) and a small list of "live hypotheses" — each plausible, each with a different intervention. The natural next step is to design A/B tests that distinguish them. **Sometimes that's the wrong next step.**

If the entire causal path from input to symptom is **in code you can read** (no external services with opaque internals, no probabilistic black boxes whose behavior must be measured), a code-anchored end-to-end trace often **collapses the hypotheses faster than empirical testing**:

- It can **structurally rule out** hypotheses (the code path that hypothesis assumes simply doesn't exist).
- It can **structurally confirm** failures the original hypotheses missed entirely.
- It transforms "hypotheses to disambiguate" into "frontiers to choose between" — a different decision shape with different optimal interventions.

Empirical testing is then reserved for the few hypotheses that survive the trace.

## The example — `next_v4 §3`

**Symptom.** A two-turn live UI dialogue produced a `primary_off_topic` refusal on T2 (a follow-up the system had enough state to answer).

**Original "live hypotheses":**

- **H1.** LLM-confidence threshold for abstention promotion is too aggressive — lower `MISALIGNMENT_PROMOTE_TO_ABSTENTION_BELOW`.
- **H2.** Frontend isn't passing the prior turn's effective topic to `/api/chat`.
- **H3.** Backend is missing the conversation_state plumbing into the classifier.

The natural plan: build a harness, run T1→T2 with each fix, compare refusal rates.

**What the deep trace produced instead.** A single code-anchored walk from browser keystroke (T2 keystroke in `requestController.ts`) through to the refusal text (`_coherence_gate.detect_evidence_coherence` Case A → coherence_mode=enforce → refusal_text primary_off_topic branch) revealed:

- **H1 was structurally ruled out.** `topic_safety.detect_topic_misalignment` and `_coherence_gate.detect_evidence_coherence` Case A evaluate the same condition over the same data; their visible difference is only the refusal *text* (which threshold's branch you land in). Lowering the threshold would change the sentence the user sees, not whether they get blocked. **No harness needed; the code says it.**
- **H2 + H3 were both structurally confirmed** — and a third frontier (`ConversationState` dataclass had no `prior_topic` slot) appeared in the trace that wasn't in the original hypothesis list. They collapsed from "competing hypotheses to disambiguate" into "three serial frontier breaks, in series, each independently sufficient to drop the prior topic."

**The decision changed.** Instead of "A/B which hypothesis dominates," the question became "which frontier is cheapest to close + do we want defense-in-depth?" The operator-suggested route was Option A (Frontier 1) primary + Option C (Frontier 3) defense-in-depth on the same task. Both shipped same day.

The harness and fixture (≈ 1 day of work) still got built — for **post-fix verification** of refusal-rate reduction, not for hypothesis selection.

## The technique

Pick a single concrete failing input. Walk the code from input ingestion to the symptom, naming every site where the value of interest passes through. For each site:

1. **What does this site receive?** (function signature, data shape)
2. **What does this site do with it?** (transform, filter, store, forward)
3. **What does this site emit?** (output, side effect, branch decision)

Where "the value of interest" is whatever the hypotheses argue about — a topic anchor, a confidence score, a flag value, a citation.

Anchor every step to a file:line reference. The trace becomes uncontestable — it's not an interpretation, it's a citation chain.

## What it produces

A trace document like the one in `next_v4.md §3 "Mechanism — full code-anchored trace"`. The output shape:

```
T2 keystroke
  ↓
[Frontier 1 — FE] frontend/src/features/chat/requestController.ts:224-228
  payload = { message, ... }
  ❌ payload.topic NOT included
  ↓
POST /api/chat
  ↓
src/lia_graph/ui_chat_payload.py:301
  requested_topic_raw = normalize_topic_key(payload.get("topic")) → None
  ↓
... (continues through every site)
```

Plus a frontier table showing each break, its site, its status (confirmed / ruled out), and its cost-to-close.

## When this is the right move vs when it isn't

**Right move when:**

- The whole causal path is in code you control or can read.
- Hypotheses are ostensibly competing but might be structurally additive (multiple sequential breaks all contributing).
- Empirical testing is expensive (cloud A/B, SME panel, multi-day runs).
- Your hypothesis list is suspiciously short (suggests the model of the system might be incomplete).

**Wrong move when:**

- The bug involves probabilistic LLM behavior (a confidence value, a verdict). You can read the prompt but not the model's internals — measure it.
- The bug is a race condition or a timing issue. The code reads correct in isolation; the failure is emergent.
- The path crosses external services (Supabase RPC body, Falkor query plan) where the read-only trace stops at the boundary.

In those cases the trace is still useful as a **partial** map — it tells you where the deterministic part ends and where empirical testing has to take over.

## Anti-patterns

- **"Run an A/B for every hypothesis."** Cheap when each A/B is a unit test; expensive when each is a cloud run. Trace first; A/B only the survivors.
- **"Pick the most plausible hypothesis and start coding."** Plausibility is correlated with familiarity, not correctness. The trace is what tells you which hypothesis is right.
- **"Trust the original hypothesis list."** The next_v4 §3 trace surfaced Frontier 2 (the `ConversationState` dataclass gap) that wasn't in any of H1/H2/H3. The list is a starting point, not an exhaustive partition.
- **"Stop the trace when the first plausible failure shows up."** Walk all the way to the symptom. The original §3 case had three serial breaks; stopping at the first would have shipped a Frontier 1 patch that's structurally insufficient on its own.

## Relationship to investigation discipline

This complements `process/investigation-discipline.md`:

- **Investigation discipline** says "after a bad eval, the first week is read-only" — don't ship code yet.
- **Deep trace before hypothesis debate** says "during that read-only week, prefer code-anchored traces over A/B harnesses for any failure whose causal path is fully in code." Faster, more precise, surfaces hypotheses you didn't list.

The investigation week's deliverable is still a document. This page is about the highest-leverage technique to use **inside** that week.

## See also

- `docs/aa_next/next_v4.md §3 "Mechanism — full code-anchored trace"` — the worked example
- `docs/learnings/process/investigation-discipline.md` — when not to ship code yet
- `~/.claude/projects/.../memory/feedback_diagnose_before_intervene.md` — same principle, encoded as user-feedback memory for retrieval / coherence-gate work
