"""Evaluation harnesses that compare retrieval/answer quality across env-flag variants.

v1 — `run_ab_comparison.py` runs the 30-question gold set twice (prior mode vs
new mode via ``LIA_TEMA_FIRST_RETRIEVAL``) and writes a per-question JSONL.
``render_ab_markdown.py`` transforms that JSONL into a panel-reviewable .md.
See docs/done/quality_tests/evaluacion_ingestionfixtask_v1.md for the full plan.
"""
