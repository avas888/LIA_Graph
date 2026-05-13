"""fix_v13_may — dataclasses for the dedicated práctica retrieval lane.

Mirrors `interpretacion/shared.py` but trimmed: no `ExpertPanelSurface`,
no `InterpretationCard`. The práctica lane has no side-panel surface —
it only feeds chunks into `build_recommendations`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PracticaChunkRuntime:
    """One práctica chunk that survived the dedicated lane's gates and
    is eligible to feed `extend_from_practica_chunks`.

    Mirrors the read-side fields downstream synthesis already consumes
    from `DocumentRecord` (source_label / authority / relative_path),
    plus the chunk-level body text and the retrieval score so the
    section can rank when fewer than `LIA_PRACTICA_RESERVED_SLOTS`
    survive the gates.
    """

    doc_id: str
    relative_path: str
    source_label: str
    authority: str
    chunk_text: str
    retrieval_score: float
    knowledge_class: str = "practica_erp"
    normative_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class PracticaKnowledgeBundle:
    """Return shape of `fetch_practica_candidates`. Parallels the
    `InterpretationKnowledgeBundle` duck-type produced by the
    interpretacion lane, but trimmed to chunk-level granularity
    (no DocumentRecord materialization — the bundle's consumer is
    synthesis, not the expert-panel surface).
    """

    chunks_selected: tuple[PracticaChunkRuntime, ...] = ()
    retrieval_diagnostics: dict[str, Any] = field(default_factory=dict)


__all__ = [
    "PracticaChunkRuntime",
    "PracticaKnowledgeBundle",
]
