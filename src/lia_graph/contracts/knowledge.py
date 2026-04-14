from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .advisory import Citation
from .document import DocumentRecord


@dataclass(frozen=True)
class KnowledgeBundle:
    pais: str
    topic: str | None
    operation_date: str
    source_indexes: tuple[str, ...]
    retrieved_docs_count: int
    selected_docs_count: int
    removed_by_scope: int
    removed_by_country: int
    removed_by_lifecycle: int
    lifecycle_exclusions: dict[str, int]
    docs_retrieved: tuple[DocumentRecord, ...]
    docs_selected: tuple[DocumentRecord, ...]
    citations: tuple[Citation, ...]
    source_assessments: tuple[dict[str, Any], ...]
    retrieval_diagnostics: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "topic": self.topic,
            "pais": self.pais,
            "operation_date": self.operation_date,
            "source_indexes": list(self.source_indexes),
            "retrieved_docs_count": self.retrieved_docs_count,
            "selected_docs_count": self.selected_docs_count,
            "removed_by_scope": self.removed_by_scope,
            "removed_by_country": self.removed_by_country,
            "removed_by_lifecycle": self.removed_by_lifecycle,
            "lifecycle_exclusions": dict(self.lifecycle_exclusions),
            "docs_retrieved": [d.to_dict() for d in self.docs_retrieved],
            "docs_selected": [d.to_dict() for d in self.docs_selected],
            "citations": [c.to_dict() for c in self.citations],
            "source_assessments": list(self.source_assessments),
            "retrieval_diagnostics": dict(self.retrieval_diagnostics or {}),
        }
