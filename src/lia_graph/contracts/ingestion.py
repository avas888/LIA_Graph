from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class IngestionStage(str, Enum):
    QUEUED = "queued"
    UPLOADING = "uploading"
    EXTRACTING = "extracting"
    ETL = "etl"
    WRITING = "writing"
    GATES = "gates"
    DONE = "done"
    FAILED = "failed"
    SKIPPED_DUPLICATE = "skipped_duplicate"
    RAW = "raw"
    PENDING_DEDUP = "pending_dedup"
    BOUNCED = "bounced"


@dataclass(frozen=True)
class IngestionError:
    code: str
    message: str
    guidance: str
    next_step: str

    def to_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "message": self.message,
            "guidance": self.guidance,
            "next_step": self.next_step,
        }


@dataclass(frozen=True)
class IngestionDocumentState:
    doc_id: str
    filename: str
    mime: str
    bytes: int
    checksum: str
    status: str
    stage: str
    progress: int
    attempts: int = 0
    duplicate_of: str | None = None
    output_raw_relative_path: str | None = None
    output_normalized_relative_paths: tuple[str, ...] = ()
    processed_upload_artifact_path: str | None = None
    archived_at: str | None = None
    batch_type: str = "normative_base"
    error: IngestionError | None = None
    created_at: str = ""
    updated_at: str = ""
    heartbeat_at: str = ""
    # Campos de clasificacion (Phase 4)
    detected_topic: str | None = None
    topic_confidence: float = 0.0
    detected_type: str | None = None
    type_confidence: float = 0.0
    combined_confidence: float = 0.0
    classification_source: str | None = None  # "keywords" | "llm" | "manual" | None
    is_raw: bool = False
    suggestion_topic: str | None = None
    suggestion_type: str | None = None
    # Campos de autogenerar (Phase 5)
    autogenerar_label: str | None = None
    autogenerar_rationale: str | None = None
    autogenerar_resolved_topic: str | None = None
    autogenerar_synonym_confidence: float = 0.0
    autogenerar_is_new: bool = False
    autogenerar_suggested_key: str | None = None
    # Campos de dedup (Phase 4)
    dedup_match_type: str | None = None  # "exact_duplicate" | "near_duplicate" | "revision"
    dedup_match_reason: str | None = None  # "hash" | "filename" | "heading"
    dedup_existing_doc_id: str | None = None
    dedup_existing_filename: str | None = None
    # Campos de delta/lineage
    derived_from_doc_id: str | None = None
    delta_section_count: int = 0
    # Campos de progreso (Phase 4)
    chunk_count: int = 0
    elapsed_ms: float = 0.0
    replaced_doc_id: str | None = None
    # Folder ingestion: relative path within the uploaded folder
    source_relative_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "doc_id": self.doc_id,
            "filename": self.filename,
            "mime": self.mime,
            "bytes": self.bytes,
            "checksum": self.checksum,
            "status": self.status,
            "stage": self.stage,
            "progress": int(self.progress),
            "attempts": int(self.attempts),
            "duplicate_of": self.duplicate_of,
            "output_raw_relative_path": self.output_raw_relative_path,
            "output_normalized_relative_paths": list(self.output_normalized_relative_paths),
            "processed_upload_artifact_path": self.processed_upload_artifact_path,
            "archived_at": self.archived_at,
            "batch_type": self.batch_type,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "heartbeat_at": self.heartbeat_at,
            # Clasificacion
            "detected_topic": self.detected_topic,
            "topic_confidence": self.topic_confidence,
            "detected_type": self.detected_type,
            "type_confidence": self.type_confidence,
            "combined_confidence": self.combined_confidence,
            "classification_source": self.classification_source,
            "is_raw": self.is_raw,
            "suggestion_topic": self.suggestion_topic,
            "suggestion_type": self.suggestion_type,
            # Autogenerar
            "autogenerar_label": self.autogenerar_label,
            "autogenerar_rationale": self.autogenerar_rationale,
            "autogenerar_resolved_topic": self.autogenerar_resolved_topic,
            "autogenerar_synonym_confidence": self.autogenerar_synonym_confidence,
            "autogenerar_is_new": self.autogenerar_is_new,
            "autogenerar_suggested_key": self.autogenerar_suggested_key,
            # Dedup
            "dedup_match_type": self.dedup_match_type,
            "dedup_match_reason": self.dedup_match_reason,
            "dedup_existing_doc_id": self.dedup_existing_doc_id,
            "dedup_existing_filename": self.dedup_existing_filename,
            # Delta/lineage
            "derived_from_doc_id": self.derived_from_doc_id,
            "delta_section_count": self.delta_section_count,
            # Progreso
            "chunk_count": self.chunk_count,
            "elapsed_ms": self.elapsed_ms,
            "replaced_doc_id": self.replaced_doc_id,
            "source_relative_path": self.source_relative_path,
        }
        if self.error is not None:
            payload["error"] = self.error.to_dict()
        else:
            payload["error"] = None
        return payload


@dataclass(frozen=True)
class IngestionBatchSummary:
    total: int
    queued: int
    processing: int
    done: int
    failed: int
    skipped_duplicate: int
    pending_batch_gate: int
    bounced: int = 0

    def to_dict(self) -> dict[str, int]:
        return {
            "total": int(self.total),
            "queued": int(self.queued),
            "processing": int(self.processing),
            "done": int(self.done),
            "failed": int(self.failed),
            "skipped_duplicate": int(self.skipped_duplicate),
            "pending_batch_gate": int(self.pending_batch_gate),
            "bounced": int(self.bounced),
        }


@dataclass(frozen=True)
class IngestionSession:
    session_id: str
    corpus: str
    status: str
    created_at: str
    updated_at: str
    documents: tuple[IngestionDocumentState, ...] = ()
    batch_summary: IngestionBatchSummary = field(
        default_factory=lambda: IngestionBatchSummary(
            total=0,
            queued=0,
            processing=0,
            done=0,
            failed=0,
            skipped_duplicate=0,
            pending_batch_gate=0,
            bounced=0,
        )
    )
    last_error: IngestionError | None = None
    heartbeat_at: str = ""
    gate_sub_stage: str = ""
    wip_sync_status: str = ""  # "" | "in_progress" | "success" | "skipped"
    auto_processing: bool = False
    gate_pending_doc_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "corpus": self.corpus,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "heartbeat_at": self.heartbeat_at,
            "gate_sub_stage": self.gate_sub_stage,
            "wip_sync_status": self.wip_sync_status,
            "auto_processing": self.auto_processing,
            "gate_pending_doc_ids": list(self.gate_pending_doc_ids),
            "batch_summary": self.batch_summary.to_dict(),
            "documents": [doc.to_dict() for doc in self.documents],
            "last_error": self.last_error.to_dict() if self.last_error else None,
        }
