from __future__ import annotations

from typing import Any

from .graph import default_graph_schema
from .ingest import (
    GRAPH_TARGET_FAMILIES,
    INGESTION_DECISION_EXCLUDE,
    INGESTION_DECISION_INCLUDE,
    INGESTION_DECISION_REVISION,
)


def build_graph_scaffold_status() -> dict[str, Any]:
    schema = default_graph_schema()
    return {
        "phase": "phase_2_scaffold",
        "graph_name": schema.graph_name,
        "node_types": sorted(kind.value for kind in schema.node_types),
        "edge_types": sorted(kind.value for kind in schema.edge_types),
        "modules": [
            "src/lia_graph/graph/schema.py",
            "src/lia_graph/graph/client.py",
            "src/lia_graph/graph/validators.py",
            "src/lia_graph/ingestion/parser.py",
            "src/lia_graph/ingestion/linker.py",
            "src/lia_graph/ingestion/classifier.py",
            "src/lia_graph/ingestion/loader.py",
        ],
    }


def build_corpus_status(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return {
        "ok": True,
        "status": "phase_2_scaffold",
        "message": (
            "Phase 2 scaffolding is present. The runner is now audit-first: it "
            "classifies candidate files as include_corpus, revision_candidate, or "
            "exclude_internal, audits the whole source-asset surface, materializes "
            "a reconnaissance quality gate before blessing the canonical manifest, "
            "materializes a canonical corpus manifest for admitted docs and pending "
            "revisions, inventories normativa, interpretacion, and practica from "
            "admitted docs, then graphizes normativa first."
        ),
        "corpus_families": ["normativa", "interpretacion", "practica"],
        "audit_decisions": [
            INGESTION_DECISION_INCLUDE,
            INGESTION_DECISION_REVISION,
            INGESTION_DECISION_EXCLUDE,
        ],
        "audit_artifacts": [
            "artifacts/corpus_audit_report.json",
            "artifacts/corpus_reconnaissance_report.json",
            "artifacts/revision_candidates.json",
            "artifacts/excluded_files.json",
            "artifacts/canonical_corpus_manifest.json",
            "artifacts/corpus_inventory.json",
        ],
        "graph_target_families": sorted(GRAPH_TARGET_FAMILIES),
        "graph_scaffold": build_graph_scaffold_status(),
    }
