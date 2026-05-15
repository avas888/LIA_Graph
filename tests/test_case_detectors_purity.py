"""v15.5+ — ``case_detectors.py`` must not import from any answer_* or
helper module.

Reintroducing such an import would re-create the circular import
``planner → helpers → support → planner`` that v15.5 broke. Adding a
new detector that needs synthesis-layer helpers means a refactor of
that helper to live in a leaf module first.
"""
from __future__ import annotations

import importlib
import inspect


def test_case_detectors_imports_are_pure() -> None:
    module = importlib.import_module("lia_graph.pipeline_d.case_detectors")
    src = inspect.getsource(module)
    # Strip docstrings/comments — they may mention forbidden module names
    # as documentation references without triggering the circular import.
    # We care about real ``import`` statements only.
    import_lines = [
        line.strip()
        for line in src.splitlines()
        if line.strip().startswith(("import ", "from "))
    ]
    joined_imports = "\n".join(import_lines)
    forbidden = (
        "answer_support",
        "answer_synthesis_helpers",
        "answer_synthesis_sections",
        "answer_synthesis_practica",
        "answer_polish",
        ".planner",
        ".orchestrator",
    )
    for needle in forbidden:
        assert needle not in joined_imports, (
            f"case_detectors.py must not import {needle} — reintroduces "
            "the circular import that v15.5 broke. Offending import "
            f"lines:\n{joined_imports}"
        )


def test_case_registry_specs_are_complete() -> None:
    """Every CaseSpec in the registry carries the four load-bearing
    fields (detector, bullets, anchor_articles, source_label) plus the
    keywords + search_queries pair. A row with empty bullets would
    silently drop the topic from `Recomendaciones Prácticas`; an empty
    anchor_articles tuple would silently lose anchoring."""
    from lia_graph.pipeline_d.case_bullets import CASE_REGISTRY

    seen_names: set[str] = set()
    seen_source_labels: set[str] = set()
    for spec in CASE_REGISTRY:
        assert callable(spec.detector), f"{spec.name}: detector must be callable"
        assert spec.bullets, f"{spec.name}: bullets must not be empty"
        assert spec.keywords, f"{spec.name}: keywords must not be empty"
        assert spec.anchor_articles, f"{spec.name}: anchor_articles must not be empty"
        assert spec.search_queries, f"{spec.name}: search_queries must not be empty"
        assert spec.source_label, f"{spec.name}: source_label must be set"
        assert spec.name not in seen_names, f"duplicate name: {spec.name}"
        assert (
            spec.source_label not in seen_source_labels
        ), f"duplicate source_label: {spec.source_label}"
        seen_names.add(spec.name)
        seen_source_labels.add(spec.source_label)
