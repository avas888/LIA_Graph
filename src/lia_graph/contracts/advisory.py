from __future__ import annotations

import functools
import json
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any
from urllib.parse import quote, urlparse

from ..normative_references import best_reference_metadata, logical_doc_id
from ..source_tiers import source_tier_label_for_row
from .company import CompanyContext
from .document import DocumentRecord


_NORMOGRAMA_DIAN_PREFIX = "https://normograma.dian.gov.co/dian/compilacion/docs"
_NORMOGRAMA_MINTIC_PREFIX = "https://normograma.mintic.gov.co/mintic/compilacion/docs"


def _prefer_mintic_normograma(url: str | None) -> str | None:
    """Swap a DIAN Normograma URL for the MinTIC mirror (honors fragment anchors)."""
    if url and url.startswith(_NORMOGRAMA_DIAN_PREFIX):
        return _NORMOGRAMA_MINTIC_PREFIX + url[len(_NORMOGRAMA_DIAN_PREFIX):]
    return url


_ET_ARTICLE_RE = re.compile(r"^et_art_([0-9_]+)(?:_(.+))?$")
_DUR_1625_ARTICLE_RE = re.compile(r"^dur_1625_art_([0-9_]+)(?:_(.+))?$")
_DIAN_RESOLUTION_RE = re.compile(r"^dian_res_0*([0-9]+)_([0-9]{4})(?:_(.+))?$")
_CANONICAL_ET_RE = re.compile(r"^co_et_suin_([0-9]+)(?:_rag_ready)?$")
_CANONICAL_DUR_1625_RE = re.compile(r"^co_dur_1625_2016(?:_rag_ready)?$")
_CANONICAL_DECRETO_RE = re.compile(r"^co_decreto_0*([0-9]+)_([0-9]{4})(?:_rag_ready)?$")
_CANONICAL_LEY_RE = re.compile(r"^co_ley_0*([0-9]+)_([0-9]{4})(?:_rag_ready)?$")
_CANONICAL_RESOLUTION_RE = re.compile(r"^co_res_dian_0*([0-9]+)_([0-9]{4})(?:_rag_ready)?$")
_CANONICAL_CONCEPTO_RE = re.compile(r"^co_dian_concepto_0*([0-9]+)_([0-9]{4})(?:_rag_ready)?$")
_CANONICAL_OFICIO_RE = re.compile(r".*oficio_dian_0*([0-9]+)_([0-9]{4}).*")

_INTERNAL_NOTES_MARKERS = frozenset({
    "ingesta", "checksum", "normalized", "migrated", "corpus",
    "readme", "estrategia", "swimlane", "contenedor", "bloque",
    "refresh", "politica", "curacion", "curados", "enlaces curados",
    "pack curado", "reglas de uso", "reglas de jerarquia",
    "indice operacional", "biblioteca de casos borde",
})

_TIPO_DOC_LABELS_DEFAULT: dict[str, str] = {
    "guia_operativa": "Guía operativa",
    "guía": "Guía operativa",
    "calendario": "Calendario tributario",
    "doctrina": "Doctrina",
    "concepto": "Concepto",
    "resolucion": "Resolución",
    "decreto": "Decreto",
    "ley": "Ley",
    "norma": "Norma",
    "checklist": "Checklist",
    "circular": "Circular",
    "operational_checklist": "Checklist operativo",
    "sentencia": "Sentencia",
    "instructivo": "Instructivo",
}

_CHECKSUM_RE = re.compile(r"\b[0-9a-f]{8}\b")
_INTERNAL_CODE_PREFIX_RE_DEFAULT = re.compile(
    r"^[a-z]{2,4}\s+[a-z]?\d{1,3}\s*[—–\-]\s*", re.IGNORECASE,
)


@functools.lru_cache(maxsize=1)
def _load_display_labels() -> dict:
    """Load centralised display label config (white-label safe)."""
    path = Path(__file__).resolve().parents[3] / "config" / "display_labels.json"
    if path.exists():
        with open(path) as fh:
            return json.load(fh)
    return {}


def _get_tipo_doc_label(tipo_doc: str) -> str:
    """Resolve a tipo_de_documento slug to its user-facing label."""
    cfg = _load_display_labels()
    labels = cfg.get("tipo_de_documento_labels", _TIPO_DOC_LABELS_DEFAULT)
    return labels.get(tipo_doc, _TIPO_DOC_LABELS_DEFAULT.get(tipo_doc, ""))
_PART_SUFFIX_RE = re.compile(r"\s*part\s+\d+\s*$", re.IGNORECASE)
_SECTION_PREFIX_RE = re.compile(r"^seccion\s+\d+\s+", re.IGNORECASE)
ALLOWED_RETRIEVAL_PROFILES = {
    "baseline_keyword",
    "hybrid_rerank",
    "advanced_corrective",
}
ALLOWED_FOLLOWUP_ACTIONS = {
    "more_depth",
    "normative_support",
    "ask_about_answer",
    "clarify_case_variables",
    "view_erp_process",
    "compare_interpretations",
    "view_original_norm",
}
ALLOWED_PAIN_HINTS = {
    "auto",
    "riesgo",
    "tiempo",
    "decision",
    "soporte",
    "cumplimiento",
}
ALLOWED_RESPONSE_GOALS = {
    "auto",
    "practico",
    "alternativas",
    "justificacion_cliente",
    "riesgos_sancion",
    "actualizacion",
}
ALLOWED_CLIENT_MODES = {
    "auto",
    "contador_a_cliente",
    "solo_contador",
}
ALLOWED_KNOWLEDGE_LAYER_FILTERS = {
    None,
    "practica_erp",
    "interpretative_guidance",
    "normative_base",
}
_PROVIDER_HINTS: tuple[tuple[str, str], ...] = (
    ("pwc.", "PwC"),
    ("deloitte.", "Deloitte"),
    ("kpmg.", "KPMG"),
    ("ey.", "EY"),
    ("bdo.", "BDO"),
    ("grantthornton.", "Grant Thornton"),
    ("crowe.", "Crowe"),
    ("bakertilly.", "Baker Tilly"),
)


def _notes_is_internal(notes: str) -> bool:
    """Return True if notes contain internal pipeline language."""
    if not notes:
        return True
    lower = notes.lower()
    return any(marker in lower for marker in _INTERNAL_NOTES_MARKERS)


def _clean_subtema(raw: str | None) -> str:
    """Strip checksums, part suffixes, section prefixes, and internal code prefixes from subtema."""
    if not raw:
        return ""
    cleaned = _slug_to_text(raw)
    # Strip internal code prefixes (e.g. "san l01 — ", "ret f03 — ")
    cfg = _load_display_labels()
    pattern_str = cfg.get("internal_code_prefix_pattern", "")
    if pattern_str:
        try:
            cleaned = re.sub(pattern_str, "", cleaned, flags=re.IGNORECASE)
        except re.error:
            cleaned = _INTERNAL_CODE_PREFIX_RE_DEFAULT.sub("", cleaned)
    else:
        cleaned = _INTERNAL_CODE_PREFIX_RE_DEFAULT.sub("", cleaned)
    cleaned = _CHECKSUM_RE.sub("", cleaned)
    cleaned = _PART_SUFFIX_RE.sub("", cleaned)
    cleaned = _SECTION_PREFIX_RE.sub("", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _clean_tema(raw: str | None) -> str:
    """Turn tema slug into human-readable label."""
    if not raw:
        return ""
    text = _slug_to_text(raw)
    # Capitalize first letter only
    return text[0].upper() + text[1:] if text else ""


def _build_metadata_reference(doc: DocumentRecord) -> str:
    """Build a meaningful display reference respecting knowledge_class provenance.

    - normative_base / official_doctrine → authority is the real author
    - interpretative_guidance → provider name or "Análisis profesional"
    - practica_erp → configurable prefix (default "Perspectiva para tu consideración"),
      NEVER shows authority as author (white-label safe)
    """
    cfg = _load_display_labels()
    kc = str(getattr(doc, "knowledge_class", "") or "").strip().lower()
    kc_cfg = cfg.get("knowledge_class_labels", {}).get(kc, {})

    subtema_clean = _clean_subtema(doc.subtema)
    tema_clean = _clean_tema(doc.tema)
    subject = subtema_clean if (subtema_clean and subtema_clean.lower() != "readme") else tema_clean

    if not subject:
        return ""

    prefix = kc_cfg.get("prefix")
    separator = kc_cfg.get("separator", " — ")
    show_authority = kc_cfg.get("show_authority", True)

    if prefix:
        # practica_erp: "Perspectiva para tu consideración: cálculo de sanciones..."
        result = f"{prefix}{separator}{subject}"
    else:
        tipo_doc = (doc.tipo_de_documento or doc.source_type or "").strip().lower()
        doc_label = _get_tipo_doc_label(tipo_doc)
        if doc_label:
            result = f"{doc_label} — {subject}"
        else:
            result = subject[0].upper() + subject[1:]

    if show_authority:
        autoridad = (doc.autoridad or doc.authority or "").strip()
        if autoridad and autoridad.lower() not in ("unknown", ""):
            result = f"{result} ({autoridad})"

    return result


def _slug_to_text(value: str | None) -> str:
    if not value:
        return ""
    cleaned = re.sub(r"[_\-]+", " ", str(value).strip())
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _article_number(token: str | None) -> str:
    if not token:
        return ""
    return ".".join(part for part in str(token).split("_") if part).strip(".")


def _et_article_number(token: str | None) -> str:
    if not token:
        return ""
    return "-".join(part for part in str(token).split("_") if part).strip("-")


def _derive_legal_reference_from_normative_refs(doc: DocumentRecord) -> str:
    refs = [str(item).strip().lower() for item in tuple(doc.normative_refs or ()) if str(item).strip()]
    for item in refs:
        if item.startswith("et_art_"):
            article = _et_article_number(item.replace("et_art_", "", 1))
            if article:
                return f"Estatuto Tributario, articulo {article}"
        if item.startswith("decreto_"):
            number = item.replace("decreto_", "", 1).strip("._-")
            if number:
                return f"Decreto {number}"
        if item.startswith("dian_concepto_"):
            number = item.replace("dian_concepto_", "", 1).strip("._-")
            if number:
                return f"Concepto DIAN {number}"
    return ""


def _derive_legal_reference(doc: DocumentRecord) -> str:
    stem = Path(doc.relative_path or doc.doc_id).stem.lower()
    notes = _slug_to_text(doc.notes)

    et_match = _ET_ARTICLE_RE.match(stem)
    if et_match:
        article = _et_article_number(et_match.group(1))
        topic = _slug_to_text(et_match.group(2))
        return (
            f"Estatuto Tributario, articulo {article} ({topic})"
            if topic
            else f"Estatuto Tributario, articulo {article}"
        )

    dur_match = _DUR_1625_ARTICLE_RE.match(stem)
    if dur_match:
        article = _article_number(dur_match.group(1))
        topic = _slug_to_text(dur_match.group(2))
        return (
            f"DUR 1625 de 2016, articulo {article} ({topic})"
            if topic
            else f"DUR 1625 de 2016, articulo {article}"
        )

    dian_res_match = _DIAN_RESOLUTION_RE.match(stem)
    if dian_res_match:
        number = str(dian_res_match.group(1)).lstrip("0") or "0"
        year = dian_res_match.group(2)
        topic = _slug_to_text(dian_res_match.group(3))
        return (
            f"Resolucion DIAN {number} de {year} ({topic})"
            if topic
            else f"Resolucion DIAN {number} de {year}"
        )

    canonical_et_match = _CANONICAL_ET_RE.match(stem)
    if canonical_et_match:
        suin_id = canonical_et_match.group(1)
        return f"Estatuto Tributario (SUIN {suin_id})"

    canonical_dur_match = _CANONICAL_DUR_1625_RE.match(stem)
    if canonical_dur_match:
        return "DUR 1625 de 2016"

    canonical_dec_match = _CANONICAL_DECRETO_RE.match(stem)
    if canonical_dec_match:
        number = str(canonical_dec_match.group(1)).lstrip("0") or "0"
        year = canonical_dec_match.group(2)
        return f"Decreto {number} de {year}"

    canonical_ley_match = _CANONICAL_LEY_RE.match(stem)
    if canonical_ley_match:
        number = str(canonical_ley_match.group(1)).lstrip("0") or "0"
        year = canonical_ley_match.group(2)
        return f"Ley {number} de {year}"

    canonical_res_match = _CANONICAL_RESOLUTION_RE.match(stem)
    if canonical_res_match:
        number = str(canonical_res_match.group(1)).lstrip("0") or "0"
        year = canonical_res_match.group(2)
        return f"Resolucion DIAN {number} de {year}"

    canonical_con_match = _CANONICAL_CONCEPTO_RE.match(stem)
    if canonical_con_match:
        number = str(canonical_con_match.group(1)).lstrip("0") or "0"
        year = canonical_con_match.group(2)
        return f"Concepto DIAN {number} de {year}"

    canonical_oficio_match = _CANONICAL_OFICIO_RE.match(stem)
    if canonical_oficio_match:
        number = str(canonical_oficio_match.group(1)).lstrip("0") or "0"
        year = canonical_oficio_match.group(2)
        return f"Oficio DIAN {number} de {year}"

    if str(doc.knowledge_class or "").strip().lower() == "practica_erp":
        meta_ref = _build_metadata_reference(doc)
        if meta_ref:
            return meta_ref
        if notes and not _notes_is_internal(notes):
            return notes
        return _slug_to_text(stem) or doc.doc_id

    normative_ref = _derive_legal_reference_from_normative_refs(doc)
    if normative_ref:
        return normative_ref

    # Use notes only if they contain real legal info (not internal pipeline text)
    if notes and not _notes_is_internal(notes):
        return notes

    # Build from rich metadata (tema, subtema, tipo_de_documento, autoridad)
    meta_ref = _build_metadata_reference(doc)
    if meta_ref:
        return meta_ref

    return _slug_to_text(stem) or doc.doc_id


def _derive_source_label(legal_reference: str) -> str:
    lowered = legal_reference.lower()
    if lowered.startswith("estatuto tributario, articulo "):
        article = legal_reference.split("articulo ", 1)[-1].split(" ", 1)[0]
        return f"ET art. {article}"
    if lowered.startswith("estatuto tributario (suin "):
        return "Estatuto Tributario"
    if lowered.startswith("dur 1625 de 2016, articulo "):
        article = legal_reference.split("articulo ", 1)[-1].split(" ", 1)[0]
        return f"DUR 1625 art. {article}"
    if lowered.startswith("dur 1625 de 2016"):
        return "DUR 1625 de 2016"
    if lowered.startswith("resolucion dian "):
        base = legal_reference.split("(", 1)[0].strip()
        return base
    if lowered.startswith("decreto "):
        return legal_reference.split("(", 1)[0].strip()
    if lowered.startswith("concepto dian ") or lowered.startswith("oficio dian "):
        return legal_reference.split("(", 1)[0].strip()
    return legal_reference if len(legal_reference) <= 96 else f"{legal_reference[:93].rstrip()}..."


def _derive_search_query(doc: DocumentRecord, legal_reference: str) -> str:
    parts = [legal_reference]
    if doc.authority and doc.authority.lower() != "unknown":
        parts.append(doc.authority)
    if doc.pais:
        parts.append(doc.pais)
    if doc.notes and not _notes_is_internal(doc.notes):
        parts.append(_slug_to_text(doc.notes))
    query = " ".join(part.strip() for part in parts if str(part).strip())
    query = re.sub(r"\s+", " ", query).strip()
    return query[:220]


def _is_http_url(url: str | None) -> bool:
    raw = str(url or "").strip().lower()
    return raw.startswith(("http://", "https://"))


def _is_local_upload_url(url: str | None) -> bool:
    raw = str(url or "").strip().lower()
    return raw.startswith("local_upload://")


def _source_view_url(doc_id: str) -> str | None:
    clean_doc_id = str(doc_id or "").strip()
    if not clean_doc_id:
        return None
    return f"/source-view?doc_id={quote(clean_doc_id, safe='')}"


def _source_download_url(doc_id: str, *, view: str = "normalized", fmt: str = "pdf") -> str | None:
    clean_doc_id = str(doc_id or "").strip()
    clean_view = str(view or "").strip().lower() or "normalized"
    clean_fmt = str(fmt or "").strip().lower() or "pdf"
    if not clean_doc_id:
        return None
    return f"/source-download?doc_id={quote(clean_doc_id, safe='')}&view={quote(clean_view, safe='')}&format={quote(clean_fmt, safe='')}"


def _provider_from_url(url: str | None) -> str | None:
    value = str(url or "").strip().lower()
    if not value:
        return None
    for token, provider in _PROVIDER_HINTS:
        if token in value:
            return provider
    domain = urlparse(value).netloc.lower().replace("www.", "")
    return domain or None


def _resolve_source_profile_fields(
    *,
    knowledge_class: str | None,
    source_type: str | None,
    source_url: str | None,
    authority: str | None,
    tipo_de_documento: str | None = None,
) -> tuple[str, str, str | None]:
    klass = str(knowledge_class or "").strip().lower()
    stype = str(source_type or "").strip().lower()
    url = str(source_url or "").strip()
    auth = str(authority or "").strip()
    tipo_doc = str(tipo_de_documento or "").strip().lower()

    # Recomendacion Oficial DIAN — DIAN instructivo content only
    if (
        auth.upper() == "DIAN"
        and stype in {"official_primary", "official_secondary"}
        and tipo_doc == "instructivo"
    ):
        provider_url = url if _is_http_url(url) else None
        return "Recomendacion Oficial DIAN", "DIAN", provider_url

    tier = source_tier_label_for_row(knowledge_class=klass, source_type=stype, source_url=url)

    provider_url = url if _is_http_url(url) else None
    if tier == "Fuente Loggro":
        provider = "Fuente Loggro"
    elif tier == "Fuente Normativa":
        provider = auth or "Fuente oficial"
    else:
        provider = auth or _provider_from_url(provider_url) or "Fuente Expertos"
    return tier, provider, provider_url


@dataclass(frozen=True)
class ConversationTurn:
    role: str
    content: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ConversationTurn":
        return cls(
            role=str(payload.get("role", "")).strip().lower(),
            content=str(payload.get("content", "")).strip(),
        )

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass(frozen=True)
class Citation:
    doc_id: str
    relative_path: str
    authority: str
    topic: str
    pais: str
    url: str | None = None
    source_label: str | None = None
    legal_reference: str | None = None
    search_query: str | None = None
    knowledge_class: str | None = None
    source_type: str | None = None
    cross_topic: bool = False
    topic_domains: tuple[str, ...] | None = None
    primary_role: str | None = None
    curation_status: str | None = None
    usage_context: str | None = None
    usage_intents: tuple[str, ...] | None = None
    tipo_de_documento: str | None = None

    @classmethod
    def from_document(cls, doc: DocumentRecord) -> "Citation":
        legal_reference = _derive_legal_reference(doc)
        return cls(
            doc_id=doc.doc_id,
            relative_path=doc.relative_path,
            authority=doc.authority,
            topic=doc.topic,
            pais=doc.pais,
            url=doc.url,
            source_label=_derive_source_label(legal_reference),
            legal_reference=legal_reference,
            search_query=_derive_search_query(doc, legal_reference),
            knowledge_class=doc.knowledge_class,
            source_type=doc.source_type,
            cross_topic=bool(doc.cross_topic),
            topic_domains=tuple(doc.topic_domains or ()),
            primary_role=doc.primary_role,
            curation_status=doc.curation_status,
            tipo_de_documento=getattr(doc, "tipo_de_documento", None),
        )

    def to_dict(self) -> dict[str, Any]:
        source_view_url = _source_view_url(self.doc_id)
        download_url = _source_download_url(self.doc_id, view="normalized", fmt="pdf")
        download_md_url = _source_download_url(self.doc_id, view="normalized", fmt="md")
        official_url = _prefer_mintic_normograma(self.url) if _is_http_url(self.url) else None
        is_local_upload = _is_local_upload_url(self.url)
        reference_meta = best_reference_metadata(
            str(self.source_label or ""),
            str(self.legal_reference or ""),
            str(self.doc_id or ""),
        ) or {}
        if is_local_upload or official_url is None:
            open_url = source_view_url or official_url
        else:
            open_url = official_url
        return {
            "doc_id": self.doc_id,
            "logical_doc_id": logical_doc_id(self.doc_id),
            "relative_path": self.relative_path,
            "authority": self.authority,
            "topic": self.topic,
            "pais": self.pais,
            "url": self.url,
            "official_url": official_url,
            "source_view_url": source_view_url,
            "open_url": open_url,
            "download_url": download_url,
            "download_md_url": download_md_url,
            "download_original_url": None,
            "is_local_upload": is_local_upload,
            "source_label": self.source_label,
            "legal_reference": self.legal_reference,
            "search_query": self.search_query,
            "reference_key": reference_meta.get("reference_key"),
            "reference_type": reference_meta.get("reference_type"),
            "reference_detail": reference_meta.get("reference_detail"),
            "knowledge_class": self.knowledge_class,
            "source_type": self.source_type,
            "cross_topic": self.cross_topic,
            "topic_domains": list(self.topic_domains or ()),
            "primary_role": self.primary_role,
            "curation_status": self.curation_status,
            "usage_context": self.usage_context,
            "usage_intents": list(self.usage_intents) if self.usage_intents else None,
        }

    def to_public_dict(self) -> dict[str, Any]:
        """Return user-facing fields for UI citation flow."""
        source_view_url = _source_view_url(self.doc_id)
        download_url = _source_download_url(self.doc_id, view="normalized", fmt="pdf")
        download_md_url = _source_download_url(self.doc_id, view="normalized", fmt="md")
        official_url = _prefer_mintic_normograma(self.url) if _is_http_url(self.url) else None
        is_local_upload = _is_local_upload_url(self.url)
        reference_meta = best_reference_metadata(
            str(self.source_label or ""),
            str(self.legal_reference or ""),
            str(self.doc_id or ""),
        ) or {}
        source_tier, source_provider, source_provider_url = _resolve_source_profile_fields(
            knowledge_class=self.knowledge_class,
            source_type=self.source_type,
            source_url=self.url,
            authority=self.authority,
            tipo_de_documento=self.tipo_de_documento,
        )
        if is_local_upload or official_url is None:
            open_url = source_view_url or official_url
        else:
            open_url = official_url
        return {
            "doc_id": self.doc_id,
            "logical_doc_id": logical_doc_id(self.doc_id),
            "authority": self.authority,
            "topic": self.topic,
            "pais": self.pais,
            "url": self.url,
            "official_url": official_url,
            "source_view_url": source_view_url,
            "open_url": open_url,
            "download_url": download_url,
            "download_md_url": download_md_url,
            "download_original_url": None,
            "is_local_upload": is_local_upload,
            "source_label": self.source_label,
            "legal_reference": self.legal_reference,
            "search_query": self.search_query,
            "reference_key": reference_meta.get("reference_key"),
            "reference_type": reference_meta.get("reference_type"),
            "reference_detail": reference_meta.get("reference_detail"),
            "knowledge_class": self.knowledge_class,
            "source_type": self.source_type,
            "cross_topic": self.cross_topic,
            "topic_domains": list(self.topic_domains or ()),
            "primary_role": self.primary_role,
            "source_tier": source_tier,
            "source_provider": source_provider,
            "source_provider_url": source_provider_url,
            "usage_context": self.usage_context,
            "usage_intents": list(self.usage_intents) if self.usage_intents else None,
        }


@dataclass(frozen=True)
class EvidenceItem:
    doc_id: str
    citation: str
    article_ref: str | None
    confidence: float
    source_url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "citation": self.citation,
            "article_ref": self.article_ref,
            "confidence": round(float(self.confidence), 4),
            "source_url": self.source_url,
        }


@dataclass(frozen=True)
class PipelineCRequest:
    message: str
    trace_id: str | None = None
    pais: str = "colombia"
    topic: str | None = None
    requested_topic: str | None = None
    secondary_topics: tuple[str, ...] = ()
    topic_adjusted: bool = False
    topic_notice: str | None = None
    topic_adjustment_reason: str | None = None
    topic_router_confidence: float = 0.0
    operation_date: str | None = None
    company_context: CompanyContext | None = None
    intent_mode: str = "auto"
    primary_scope_mode: str = "global_overlay"
    debug: bool = False


@dataclass(frozen=True)
class RetrievalPlan:
    top_k: int
    cascade_mode: str
    tier_sequence: tuple[str, ...]
    reason: str
    allow_legal_depth_only: bool


@dataclass(frozen=True)
class EvidencePack:
    docs_selected: tuple[DocumentRecord, ...]
    citations: tuple[Citation, ...]
    retrieval_diagnostics: dict[str, Any]
    confidence_score: float


@dataclass(frozen=True)
class VerifierDecision:
    mode: str
    blocked: bool
    confidence_score: float
    flags: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class RunTelemetry:
    run_id: str
    trace_id: str
    started_at: str
    ended_at: str | None = None
    status: str = "running"
    request_snapshot: dict[str, Any] | None = None
    stage_timeline: tuple[dict[str, Any], ...] = ()
    summary: dict[str, Any] | None = None


@dataclass(frozen=True)
class PipelineCResponse:
    trace_id: str
    run_id: str
    answer_markdown: str
    answer_concise: str
    citations: tuple[Citation, ...]
    confidence_score: float
    confidence_mode: str
    diagnostics: dict[str, Any] | None = None
    requested_topic: str | None = None
    effective_topic: str | None = None
    secondary_topics: tuple[str, ...] = ()
    topic_adjusted: bool = False
    topic_notice: str | None = None
    topic_adjustment_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "run_id": self.run_id,
            "answer_markdown": self.answer_markdown,
            "answer_concise": self.answer_concise,
            "citations": [c.to_public_dict() for c in self.citations],
            "confidence": {
                "score": round(float(self.confidence_score), 4),
                "mode": self.confidence_mode,
            },
            "diagnostics": dict(self.diagnostics or {}) if self.diagnostics is not None else None,
            "requested_topic": str(self.requested_topic or "").strip() or None,
            "effective_topic": str(self.effective_topic or "").strip() or None,
            "secondary_topics": [str(item) for item in self.secondary_topics],
            "topic_adjusted": bool(self.topic_adjusted),
            "topic_notice": self.topic_notice,
            "topic_adjustment_reason": self.topic_adjustment_reason,
        }
