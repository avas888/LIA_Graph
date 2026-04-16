from __future__ import annotations

from pathlib import Path
from typing import Protocol

from ..contracts import DocumentRecord


class RetrieverAdapter(Protocol):
    """Contrato agnostico al proveedor para backends de retrieval."""

    def retrieve(
        self,
        query: str,
        top_k: int,
        index_file: Path,
        topic: str | None = None,
        pais: str | None = None,
        retrieval_profile: str | None = None,
        pain_hint: str | None = None,
        trace_id: str | None = None,
        search_keywords: list[str] | None = None,
    ) -> list[DocumentRecord]:
        """Retorna documentos de soporte ordenados por relevancia."""
