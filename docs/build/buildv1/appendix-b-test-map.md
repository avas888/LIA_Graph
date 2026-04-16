# Appendix B — Test Map

## Phase 1

- contract compatibility tests
- pipeline routing tests
- chat run dedupe/resume tests
- stream draft/final parity tests

## Phase 2

- corpus audit tests for `include_corpus`, `revision_candidate`, and `exclude_internal`
- all-file audit tests across markdown and non-markdown assets
- exclusion tests for `state.md`, working `README.md`, `.DS_Store`, crawler helpers, deprecated mirrors, and roadmap notes
- reconnaissance quality-gate tests for `ready_for_canonical_blessing`, `review_required`, and `blocked`
- manual-review queue tests across archetype, authority, family, ambiguity, and revision linkage
- revision-candidate tests for `PATCH` and `UPSERT` markdown files
- corpus inventory tests across `normativa`, `interpretacion`, and `practica`
- labeling tests for `family`, `knowledge_class`, `source_type`, and `vocabulary_status`
- parse-strategy and document-archetype tests
- canonical-topic tests that prefer ratified vocabulary keys while preserving backward runtime aliases
- custom-topic tests for valid corpus domains that sit outside the current ratified vocabulary version
- canonical manifest tests for base docs plus attached pending revisions
- non-markdown corpus asset tests for inventory-only admission without accidental graph parsing
- parser tests for articles and subarticles
- linker tests for normative references
- edge taxonomy classification tests
- graph integrity validation tests
- normative multi-hop canary tests, con ET como slice importante pero no unico

## Phase 3

- planner output contract tests
- query mode selection tests
- time-scope and vigencia tests
- entry point resolution tests
- retrieval quality tests
- fallback semantic tests

## Phase 4

- tenant isolation tests
- company-context scoping tests
- session/history isolation tests
- runtime context persistence tests

## Phase 5

- citation precision/completeness tests
- answer actionability rubric tests
- verifier block/warn tests
- compiled cache hit/miss tests
- invalidation tests

## Phase 6

- dual-run integration tests
- shadow logging tests
- pairwise eval harness tests
- regression tests on current public surfaces

## Phase 7

- deployment smoke tests
- feature flag / pipeline selection tests
- rollback drill checks
- graph health and cache health smoke checks
