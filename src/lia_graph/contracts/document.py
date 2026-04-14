from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _coerce_int(value: Any) -> int | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _coerce_tuple(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        return tuple(item.strip() for item in value.split(",") if item.strip())
    if isinstance(value, (list, tuple, set)):
        return tuple(str(item).strip() for item in value if str(item).strip())
    return ()


def _coerce_provider_tuple(value: Any) -> tuple[dict[str, Any], ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    rows: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or item.get("provider") or "").strip()
        if not name:
            continue
        url = str(item.get("url") or "").strip()
        rows.append({"name": name, "url": url or None})
    return tuple(rows)


def _coerce_optional_str(payload: dict[str, Any], field_name: str) -> str | None:
    value = payload.get(field_name)
    return str(value) if value is not None else None


def _coerce_bool(value: Any, *, default: bool | None) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "si"}


_OPTIONAL_STRING_FIELDS = (
    "curation_status",
    "trust_tier",
    "metadata_schema_version",
    "pipeline_generation",
    "source_origin",
    "authority_claimed",
    "provenance_uri",
    "ingestion_session_id",
    "normative_linkage_status",
    "validation_status",
    "retrieval_visibility",
    "primary_role",
    "jurisdiccion",
    "tema",
    "subtema",
    "tipo_de_accion",
    "tipo_de_riesgo",
    "tipo_de_consulta",
    "tipo_de_documento",
    "vigencia",
    "autoridad",
    "nivel_practicidad",
    "publish_date",
    "effective_date",
    "url",
    "status",
    "notes",
    "knowledge_class",
    "review_cadence",
    "storage_partition",
    "superseded_by",
    "entity_id",
    "entity_type",
    "relation_type",
    "chunk_id",
    "chunk_text",
    "chunk_section_type",
    "retrieval_method",
    "embedding_model",
    "index_version",
    "pain_point",
    "version_group_id",
    "vigencia_basis",
    "vigencia_ruling_id",
    "historical_basis",
    "document_context_summary",
    "applicability_kind",
)
_TUPLE_FIELDS = (
    "reference_identity_keys",
    "mentioned_reference_keys",
    "admissible_surfaces",
    "supports_fields",
    "legal_concepts",
    "aliases",
    "complement_relations",
    "provider_labels",
)


@dataclass(frozen=True)
class DocumentRecord:
    doc_id: str
    relative_path: str
    absolute_path: str
    category: str
    source_type: str = "unknown"
    curation_status: str | None = None
    trust_tier: str | None = None
    metadata_schema_version: str | None = None
    pipeline_generation: str | None = None
    source_origin: str | None = None
    authority_claimed: str | None = None
    authority_verified: bool | None = None
    provenance_uri: str | None = None
    ingestion_session_id: str | None = None
    normative_linkage_status: str | None = None
    normative_refs: tuple[str, ...] = ()
    validation_status: str | None = None
    retrieval_visibility: str | None = None
    cross_topic: bool = False
    topic_domains: tuple[str, ...] = ()
    primary_role: str | None = None
    topic: str = "unknown"
    authority: str = "unknown"
    pais: str = "colombia"
    locale: str | None = "es-CO"
    concept_tags: tuple[str, ...] = ()
    provider_labels: tuple[str, ...] = ()
    providers: tuple[dict[str, Any], ...] = ()
    jurisdiccion: str | None = None
    tema: str | None = None
    subtema: str | None = None
    tipo_de_accion: str | None = None
    tipo_de_riesgo: str | None = None
    tipo_de_consulta: str | None = None
    tipo_de_documento: str | None = None
    vigencia: str | None = None
    autoridad: str | None = None
    nivel_practicidad: str | None = None
    publish_date: str | None = None
    effective_date: str | None = None
    url: str | None = None
    status: str | None = None
    notes: str | None = None
    knowledge_class: str | None = None
    review_cadence: str | None = None
    storage_partition: str | None = None
    superseded_by: str | None = None
    entity_id: str | None = None
    entity_type: str | None = None
    relation_type: str | None = None
    reference_identity_keys: tuple[str, ...] = ()
    mentioned_reference_keys: tuple[str, ...] = ()
    admissible_surfaces: tuple[str, ...] = ()
    supports_fields: tuple[str, ...] = ()
    chunk_id: str | None = None
    chunk_text: str | None = None
    chunk_start: int | None = None
    chunk_end: int | None = None
    chunk_section_type: str | None = None
    retrieval_score: float | None = None
    retrieval_method: str | None = None
    embedding_model: str | None = None
    index_version: str | None = None
    lane_scores: dict[str, float] | None = None
    pain_point: str | None = None
    legal_concepts: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()
    complement_relations: tuple[str, ...] = ()
    version_group_id: str | None = None
    is_current_text: bool | None = None
    vigencia_basis: str | None = None
    vigencia_ruling_id: str | None = None
    historical_basis: str | None = None
    document_context_summary: str | None = None
    applicability_kind: str | None = None
    ag_from_year: int | None = None
    ag_to_year: int | None = None
    filing_from_year: int | None = None
    filing_to_year: int | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "DocumentRecord":
        kwargs: dict[str, Any] = dict(
            doc_id=str(payload.get("doc_id", "")),
            relative_path=str(payload.get("relative_path", "")),
            absolute_path=str(payload.get("absolute_path", "")),
            category=str(payload.get("category", "unknown")),
            source_type=str(payload.get("source_type", "unknown")),
            topic=str(payload.get("topic", "unknown")),
            authority=str(payload.get("authority", "unknown")),
            pais=str(payload.get("pais", "colombia")).strip().lower() or "colombia",
            locale=str(payload.get("locale", "es-CO")) if payload.get("locale") is not None else "es-CO",
            authority_verified=_coerce_bool(payload.get("authority_verified"), default=None),
            normative_refs=_coerce_tuple(payload.get("normative_refs")),
            cross_topic=bool(_coerce_bool(payload.get("cross_topic"), default=False)),
            topic_domains=_coerce_tuple(payload.get("topic_domains")),
            concept_tags=_coerce_tuple(payload.get("concept_tags")),
            providers=_coerce_provider_tuple(payload.get("providers")),
            chunk_start=_coerce_int(payload.get("chunk_start")),
            chunk_end=_coerce_int(payload.get("chunk_end")),
            retrieval_score=_coerce_float(payload.get("retrieval_score")),
            lane_scores=dict(payload.get("lane_scores")) if isinstance(payload.get("lane_scores"), dict) else None,
            is_current_text=_coerce_bool(payload.get("is_current_text"), default=None),
            ag_from_year=_coerce_int(payload.get("ag_from_year")),
            ag_to_year=_coerce_int(payload.get("ag_to_year")),
            filing_from_year=_coerce_int(payload.get("filing_from_year")),
            filing_to_year=_coerce_int(payload.get("filing_to_year")),
        )
        for field_name in _OPTIONAL_STRING_FIELDS:
            kwargs[field_name] = _coerce_optional_str(payload, field_name)
        for field_name in _TUPLE_FIELDS:
            kwargs[field_name] = _coerce_tuple(payload.get(field_name))
        return cls(**kwargs)

    def to_dict(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "relative_path": self.relative_path,
            "absolute_path": self.absolute_path,
            "category": self.category,
            "source_type": self.source_type,
            "curation_status": self.curation_status,
            "trust_tier": self.trust_tier,
            "metadata_schema_version": self.metadata_schema_version,
            "pipeline_generation": self.pipeline_generation,
            "source_origin": self.source_origin,
            "authority_claimed": self.authority_claimed,
            "authority_verified": self.authority_verified,
            "provenance_uri": self.provenance_uri,
            "ingestion_session_id": self.ingestion_session_id,
            "normative_linkage_status": self.normative_linkage_status,
            "normative_refs": list(self.normative_refs),
            "validation_status": self.validation_status,
            "retrieval_visibility": self.retrieval_visibility,
            "cross_topic": self.cross_topic,
            "topic_domains": list(self.topic_domains),
            "primary_role": self.primary_role,
            "topic": self.topic,
            "authority": self.authority,
            "pais": self.pais,
            "locale": self.locale,
            "concept_tags": list(self.concept_tags),
            "provider_labels": list(self.provider_labels),
            "providers": [dict(item) for item in self.providers],
            "jurisdiccion": self.jurisdiccion,
            "tema": self.tema,
            "subtema": self.subtema,
            "tipo_de_accion": self.tipo_de_accion,
            "tipo_de_riesgo": self.tipo_de_riesgo,
            "tipo_de_consulta": self.tipo_de_consulta,
            "tipo_de_documento": self.tipo_de_documento,
            "vigencia": self.vigencia,
            "autoridad": self.autoridad,
            "nivel_practicidad": self.nivel_practicidad,
            "publish_date": self.publish_date,
            "effective_date": self.effective_date,
            "url": self.url,
            "status": self.status,
            "notes": self.notes,
            "knowledge_class": self.knowledge_class,
            "review_cadence": self.review_cadence,
            "storage_partition": self.storage_partition,
            "superseded_by": self.superseded_by,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "relation_type": self.relation_type,
            "reference_identity_keys": list(self.reference_identity_keys),
            "mentioned_reference_keys": list(self.mentioned_reference_keys),
            "admissible_surfaces": list(self.admissible_surfaces),
            "supports_fields": list(self.supports_fields),
            "chunk_id": self.chunk_id,
            "chunk_text": self.chunk_text,
            "chunk_start": self.chunk_start,
            "chunk_end": self.chunk_end,
            "chunk_section_type": self.chunk_section_type,
            "retrieval_score": self.retrieval_score,
            "retrieval_method": self.retrieval_method,
            "embedding_model": self.embedding_model,
            "index_version": self.index_version,
            "lane_scores": dict(self.lane_scores or {}),
            "pain_point": self.pain_point,
            "legal_concepts": list(self.legal_concepts),
            "aliases": list(self.aliases),
            "complement_relations": list(self.complement_relations),
            "version_group_id": self.version_group_id,
            "is_current_text": self.is_current_text,
            "vigencia_basis": self.vigencia_basis,
            "vigencia_ruling_id": self.vigencia_ruling_id,
            "historical_basis": self.historical_basis,
            "document_context_summary": self.document_context_summary,
            "applicability_kind": self.applicability_kind,
            "ag_from_year": self.ag_from_year,
            "ag_to_year": self.ag_to_year,
            "filing_from_year": self.filing_from_year,
            "filing_to_year": self.filing_to_year,
        }
