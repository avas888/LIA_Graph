# Deprecated: Old-RAG Guidance

This directory contains historical architecture notes that are no longer active steering for LIA_Graph.

Why they were moved:
- they overfit to Pipeline C mental models
- they encourage chunk-first or rerank-first assumptions
- they can accidentally steer graph design back toward the old RAG

Use them only for:
- migration archaeology
- compatibility work
- understanding what was copied from the prior shell

Do not use them as primary guidance for:
- indexing
- tagging
- vocabulary design
- graph schema
- retrieval
- traversal
- composition

Active steering lives in:
- `docs/architecture/FORK-BOUNDARY.md`
- `docs/state/STATE.md`
