from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any
import re
import unicodedata

from ..contracts import DocumentRecord
from ..governance import parse_operation_date

_AG_RE = re.compile(r"\b(?:ag|ano\s+gravable|año\s+gravable)\s*[:\-]?\s*(20\d{2})\b", flags=re.IGNORECASE)
_FILING_YEAR_RE = re.compile(
    r"\b(?:presentad[oa]s?|presentar|presentacion|declarad[oa]s?|declarar|declaracion|calendario|vencimiento|formulario)\b"
    r"[^\n\r]{0,32}?\b(20\d{2})\b",
    flags=re.IGNORECASE,
)
_BARE_YEAR_RE = re.compile(r"\b(20\d{2})\b")
_CORRECTION_TOKENS = (
    "correccion",
    "corregir",
    "corrijo",
    "rectificar",
    "rectificacion",
    "enmendar",
    "declaracion corregida",
)
_HISTORICAL_TOKENS = (
    "antecedente",
    "antecedentes",
    "historico",
    "historia",
    "evolucion",
    "comparar versiones",
    "comparacion historica",
    "comparación histórica",
    "version anterior",
    "versiones anteriores",
)
_MESSAGE_YEAR_TOKENS = (
    "renta",
    "declaracion",
    "declarar",
    "presentar",
    "presentacion",
    "formulario",
    "calendario",
    "beneficio de auditoria",
    "beneficio de auditoría",
)

_BENEFICIO_AUDITORIA_CURRENT_AG_FROM = 2022
_BENEFICIO_AUDITORIA_CURRENT_AG_TO = 2026
_BENEFICIO_AUDITORIA_CURRENT_DOC_IDS = {
    "renta_doctrina_dian_oficio_608_2021",
    "renta_doctrina_dian_oficio_801_2022",
}
_BENEFICIO_AUDITORIA_CURRENT_PREFIXES = (
    "renta_ingest_t08_beneficio_auditoria_interpretaciones_",
)
_PERIOD_ELIGIBLE_TOPICS = frozenset(
    {
        "declaracion_renta",
        "iva",
        "ica",
        "calendario_obligaciones",
    }
)


def _normalize_text(value: str) -> str:
    lowered = str(value or "").strip().lower()
    normalized = unicodedata.normalize("NFKD", lowered)
    plain = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", plain)


def _contains_any(text: str, tokens: tuple[str, ...]) -> bool:
    return any(token in text for token in tokens)


def _coerce_year(value: Any) -> int | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    try:
        year = int(raw)
    except ValueError:
        return None
    if 2000 <= year <= 2099:
        return year
    return None


def _extract_ag_year(text: str) -> int | None:
    match = _AG_RE.search(_normalize_text(text))
    return _coerce_year(match.group(1)) if match else None


def _extract_filing_year(text: str) -> int | None:
    match = _FILING_YEAR_RE.search(_normalize_text(text))
    return _coerce_year(match.group(1)) if match else None


def _extract_contextual_message_year(text: str) -> int | None:
    normalized = _normalize_text(text)
    if not normalized or not _contains_any(normalized, _MESSAGE_YEAR_TOKENS):
        return None
    years = [_coerce_year(match.group(1)) for match in _BARE_YEAR_RE.finditer(normalized)]
    unique_years = [year for year in years if year is not None]
    if len(set(unique_years)) != 1:
        return None
    return unique_years[0]


@dataclass(frozen=True)
class RequestedPeriodContext:
    ag_year: int | None = None
    filing_year: int | None = None
    period_source: str = "unresolved"
    defaulted_to_current_ag: bool = False
    is_correction: bool = False
    historical_allowed: bool = False

    def is_resolved(self) -> bool:
        return self.ag_year is not None or self.filing_year is not None

    def display_label(self) -> str:
        if self.ag_year is not None and self.filing_year is not None:
            return f"AG {self.ag_year} presentado en {self.filing_year}"
        if self.ag_year is not None:
            return f"AG {self.ag_year}"
        if self.filing_year is not None:
            return f"presentacion {self.filing_year}"
        return "no_resuelto"

    def fingerprint(self) -> str:
        return (
            f"ag:{self.ag_year or 'na'}|filing:{self.filing_year or 'na'}|"
            f"source:{self.period_source}|default:{int(self.defaulted_to_current_ag)}|"
            f"correction:{int(self.is_correction)}|historical:{int(self.historical_allowed)}"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "ag_year": self.ag_year,
            "filing_year": self.filing_year,
            "period_source": self.period_source,
            "defaulted_to_current_ag": self.defaulted_to_current_ag,
            "is_correction": self.is_correction,
            "historical_allowed": self.historical_allowed,
            "resolved": self.is_resolved(),
            "display_label": self.display_label(),
            "fingerprint": self.fingerprint(),
        }


def _build_resolved_period(
    *,
    ag_year: int,
    period_source: str,
    defaulted_to_current_ag: bool,
    is_correction: bool,
    historical_allowed: bool,
) -> RequestedPeriodContext:
    return RequestedPeriodContext(
        ag_year=ag_year,
        filing_year=ag_year + 1,
        period_source=period_source,
        defaulted_to_current_ag=defaulted_to_current_ag,
        is_correction=is_correction,
        historical_allowed=historical_allowed,
    )


def resolve_requested_period(
    *,
    message: str,
    topic: str | None,
    operation_date: str | None,
    company_context: dict[str, Any] | None,
) -> RequestedPeriodContext:
    normalized_message = _normalize_text(message)
    is_correction = _contains_any(normalized_message, _CORRECTION_TOKENS)
    historical_allowed = _contains_any(normalized_message, _HISTORICAL_TOKENS)
    normalized_topic = str(topic or "").strip().lower() or None
    if normalized_topic is not None and normalized_topic not in _PERIOD_ELIGIBLE_TOPICS:
        return RequestedPeriodContext(
            period_source="not_applicable",
            is_correction=is_correction,
            historical_allowed=historical_allowed,
        )

    ag_year = _extract_ag_year(message)
    if ag_year is not None:
        return _build_resolved_period(
            ag_year=ag_year,
            period_source="message_ag",
            defaulted_to_current_ag=False,
            is_correction=is_correction,
            historical_allowed=historical_allowed,
        )

    context_payload = dict(company_context or {})
    context_fiscal_year = _coerce_year(context_payload.get("fiscal_year"))
    if context_fiscal_year is not None:
        return _build_resolved_period(
            ag_year=context_fiscal_year,
            period_source="company_context_fiscal_year",
            defaulted_to_current_ag=False,
            is_correction=is_correction,
            historical_allowed=historical_allowed,
        )

    context_period = str(context_payload.get("period") or "").strip()
    if context_period:
        period_ag = _extract_ag_year(context_period)
        if period_ag is not None:
            return _build_resolved_period(
                ag_year=period_ag,
                period_source="company_context_period_ag",
                defaulted_to_current_ag=False,
                is_correction=is_correction,
                historical_allowed=historical_allowed,
            )
        period_filing = _extract_filing_year(context_period)
        if period_filing is not None:
            return _build_resolved_period(
                ag_year=period_filing - 1,
                period_source="company_context_period_filing",
                defaulted_to_current_ag=False,
                is_correction=is_correction,
                historical_allowed=historical_allowed,
            )

    filing_year = _extract_filing_year(message)
    if filing_year is None:
        filing_year = _extract_contextual_message_year(message)
    if filing_year is not None:
        return _build_resolved_period(
            ag_year=filing_year - 1,
            period_source="message_filing_year",
            defaulted_to_current_ag=False,
            is_correction=is_correction,
            historical_allowed=historical_allowed,
        )

    if is_correction:
        return RequestedPeriodContext(
            period_source="correction_requires_context",
            is_correction=True,
            historical_allowed=historical_allowed,
        )

    operation = parse_operation_date(operation_date)
    return RequestedPeriodContext(
        ag_year=operation.year - 1,
        filing_year=operation.year,
        period_source="default_current_ag",
        defaulted_to_current_ag=True,
        is_correction=False,
        historical_allowed=historical_allowed,
    )


def _doc_strings(doc: DocumentRecord) -> tuple[str, str, str]:
    doc_id = str(doc.doc_id or "").strip().lower()
    relative_path = str(doc.relative_path or "").strip().lower()
    joined = _normalize_text(
        " ".join(
            [
                doc_id,
                relative_path,
                " ".join(doc.concept_tags),
                " ".join(doc.normative_refs),
                str(doc.tema or ""),
                str(doc.subtema or ""),
                str(doc.notes or ""),
            ]
        )
    )
    return doc_id, relative_path, joined


def backfill_document_applicability(doc: DocumentRecord) -> DocumentRecord:
    if any(
        value is not None
        for value in (
            doc.applicability_kind,
            doc.ag_from_year,
            doc.ag_to_year,
            doc.filing_from_year,
            doc.filing_to_year,
        )
    ):
        return doc

    doc_id, relative_path, combined = _doc_strings(doc)

    if "et_art_689_1" in doc_id or "et_art_689_1" in relative_path:
        return replace(
            doc,
            applicability_kind="ag_range",
            ag_from_year=2011,
            ag_to_year=2012,
            filing_from_year=2012,
            filing_to_year=2013,
        )

    if "et_art_689_2" in doc_id or "et_art_689_2" in relative_path:
        return replace(
            doc,
            applicability_kind="ag_range",
            ag_from_year=2020,
            ag_to_year=2021,
            filing_from_year=2021,
            filing_to_year=2022,
        )

    is_current_benefit_doc = (
        "et_art_689_3" in doc_id
        or "et_art_689_3" in relative_path
        or doc_id in _BENEFICIO_AUDITORIA_CURRENT_DOC_IDS
        or any(doc_id.startswith(prefix) for prefix in _BENEFICIO_AUDITORIA_CURRENT_PREFIXES)
        or (
            "beneficio_auditoria" in combined
            and "et_art_689_3" in combined
        )
    )
    if is_current_benefit_doc:
        return replace(
            doc,
            applicability_kind="ag_range",
            ag_from_year=_BENEFICIO_AUDITORIA_CURRENT_AG_FROM,
            ag_to_year=_BENEFICIO_AUDITORIA_CURRENT_AG_TO,
            filing_from_year=_BENEFICIO_AUDITORIA_CURRENT_AG_FROM + 1,
            filing_to_year=_BENEFICIO_AUDITORIA_CURRENT_AG_TO + 1,
        )

    return doc


def classify_document_applicability(
    *,
    doc: DocumentRecord,
    requested_period: RequestedPeriodContext | None,
) -> str:
    if requested_period is None or not requested_period.is_resolved():
        return "not_evaluated"
    if requested_period.historical_allowed:
        return "historical_allowed"

    ag_year = requested_period.ag_year
    filing_year = requested_period.filing_year
    if ag_year is not None and doc.ag_from_year is not None and doc.ag_to_year is not None:
        return "applicable" if doc.ag_from_year <= ag_year <= doc.ag_to_year else "outside_window"
    if filing_year is not None and doc.filing_from_year is not None and doc.filing_to_year is not None:
        return "applicable" if doc.filing_from_year <= filing_year <= doc.filing_to_year else "outside_window"
    return "unknown"


def filter_docs_by_requested_period(
    *,
    docs: tuple[DocumentRecord, ...],
    requested_period: RequestedPeriodContext | None,
) -> tuple[tuple[DocumentRecord, ...], dict[str, Any]]:
    hydrated_docs = tuple(backfill_document_applicability(doc) for doc in docs)
    diagnostics: dict[str, Any] = {
        "requested_period": requested_period.to_dict() if requested_period is not None else None,
        "enabled": bool(requested_period is not None and requested_period.is_resolved() and not requested_period.historical_allowed),
        "matched_applicable_doc_ids": [],
        "rejected_historical_doc_ids": [],
        "unknown_doc_ids": [],
        "fallback_kept_all": False,
    }

    if requested_period is None or not requested_period.is_resolved() or requested_period.historical_allowed:
        return hydrated_docs, diagnostics

    classifications: list[tuple[DocumentRecord, str]] = []
    has_applicable = False
    for doc in hydrated_docs:
        status = classify_document_applicability(doc=doc, requested_period=requested_period)
        classifications.append((doc, status))
        if status == "applicable":
            has_applicable = True
            diagnostics["matched_applicable_doc_ids"].append(doc.doc_id)
        elif status == "outside_window":
            diagnostics["rejected_historical_doc_ids"].append(doc.doc_id)
        elif status == "unknown":
            diagnostics["unknown_doc_ids"].append(doc.doc_id)

    if not has_applicable:
        diagnostics["fallback_kept_all"] = True
        diagnostics["rejected_historical_doc_ids"] = []
        return hydrated_docs, diagnostics

    kept = tuple(doc for doc, status in classifications if status != "outside_window")
    diagnostics["kept_doc_ids"] = [doc.doc_id for doc in kept]
    return kept, diagnostics


__all__ = [
    "RequestedPeriodContext",
    "backfill_document_applicability",
    "classify_document_applicability",
    "filter_docs_by_requested_period",
    "resolve_requested_period",
]
