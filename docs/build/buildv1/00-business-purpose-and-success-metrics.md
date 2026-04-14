# 00 — Business Purpose and Success Metrics

## Purpose Translation

LIA exists to reduce uncertainty for Colombian accountants when they must decide what applies, why it applies, what changed, and what to do next. The system is successful when it shortens the path from question to defensible action.

## Business Outcomes

- improve trust in answers by showing grounded normative support
- reduce time spent reconstructing chains of reforms and exceptions
- preserve tenant and company context without fragmenting the shared corpus
- support operational next steps, not only descriptive explanations

## Product Principles

- purpose over novelty
- traceability over eloquence
- shared knowledge over duplicated tenant knowledge
- tenant safety over runtime ambiguity
- temporal correctness over static relevance
- actionability over generic summarization

## Success Metrics

### User-facing

- accountants can identify the applicable norm chain in one answer
- answers reflect company and period context when provided
- next-action guidance is materially useful
- citations are precise and sufficient for review

### System-facing

- no cross-tenant leakage
- temporal correctness meets or exceeds baseline
- multi-hop retrieval outperforms flat retrieval on target scenarios
- compiled answers improve repeat-query latency without freshness regressions

## Failure Signals

- answers cite the right article but miss the reform or exception
- answers ignore tenant/company scope
- answers are grounded yet operationally useless
- cache serves stale guidance after normative changes
- planner chooses expensive graph traversal for simple questions
