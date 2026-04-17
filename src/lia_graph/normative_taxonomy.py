from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

_FORM_RE = re.compile(r"\b(?:formulario|formato|f)\.?\s*([0-9]{2,6}[A-Z]?)\b", re.IGNORECASE)
_CONSTITUTION_RE = re.compile(r"\bconstituci[oó]n(?:\s+pol[ií]tica)?\b", re.IGNORECASE)
_ET_RE = re.compile(r"\bestatuto\s+tributario\b|\bET\b", re.IGNORECASE)
_DUR_RE = re.compile(r"\bDUR\s*1625\b|decreto\s+[uú]nico\s+reglamentario\s+1625|dur_1625", re.IGNORECASE)
_LAW_RE = re.compile(r"\bley\s+[0-9A-Za-z\-]+(?:\s*(?:/|de)\s*\d{4})?\b", re.IGNORECASE)
_DECREE_RE = re.compile(r"\bdecreto\s+[0-9A-Za-z\-]+(?:\s*(?:/|de)\s*\d{4})?\b", re.IGNORECASE)
_RESOLUTION_RE = re.compile(r"\bresoluci[oó]n(?:\s+dian)?\s+[0-9A-Za-z\-]+(?:\s*(?:/|de)\s*\d{4})?\b", re.IGNORECASE)
_CONCEPT_RE = re.compile(r"\b(?:concepto|oficio)(?:\s+dian)?\s+[0-9A-Za-z\-]+", re.IGNORECASE)
_CIRCULAR_RE = re.compile(r"\bcircular\s+[0-9A-Za-z\-]+(?:\s*(?:/|de)\s*\d{4})?\b", re.IGNORECASE)
_JURISPRUDENCE_RE = re.compile(r"\b(?:sentencia|auto)\b|corte constitucional|consejo de estado", re.IGNORECASE)


@dataclass(frozen=True)
class NormativeDocumentProfile:
    document_family: str
    family_subtype: str
    hierarchy_tier: str
    binding_force: str
    binding_force_rank: int
    analysis_template_id: str
    ui_surface: str
    relation_types: tuple[str, ...]
    allowed_secondary_overlays: tuple[str, ...]
    caution_banner: dict[str, str] | None = None

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "document_family": self.document_family,
            "family_subtype": self.family_subtype,
            "hierarchy_tier": self.hierarchy_tier,
            "binding_force": self.binding_force,
            "binding_force_rank": self.binding_force_rank,
            "analysis_template_id": self.analysis_template_id,
            "ui_surface": self.ui_surface,
            "relation_types": list(self.relation_types),
            "allowed_secondary_overlays": list(self.allowed_secondary_overlays),
            "caution_banner": dict(self.caution_banner or {}) or None,
        }


def _haystack(citation: dict[str, Any], row: dict[str, Any] | None) -> str:
    payload = citation if isinstance(citation, dict) else {}
    source_row = row if isinstance(row, dict) else {}
    return " ".join(
        [
            str(payload.get("reference_type") or ""),
            str(payload.get("source_label") or ""),
            str(payload.get("legal_reference") or ""),
            str(source_row.get("relative_path") or ""),
            str(source_row.get("title") or ""),
            str(source_row.get("notes") or ""),
            str(source_row.get("subtema") or ""),
            str(source_row.get("authority") or payload.get("authority") or ""),
            str(source_row.get("source_type") or payload.get("source_type") or ""),
        ]
    ).strip()


def _ui_surface_for_family(family: str) -> str:
    if family == "formulario":
        return "form_guide"
    return "deep_analysis"


def _profile_for_family(family: str, *, subtype: str) -> NormativeDocumentProfile:
    if family == "constitucion":
        return NormativeDocumentProfile(
            document_family=family,
            family_subtype=subtype,
            hierarchy_tier="constitucional",
            binding_force="Rango constitucional",
            binding_force_rank=1000,
            analysis_template_id="constitutional_norm_analysis",
            ui_surface=_ui_surface_for_family(family),
            relation_types=("superior_norm", "interpreted_by", "questioned_by", "summarized_by"),
            allowed_secondary_overlays=("jurisprudencia", "concepto_dian", "interpretacion_secundaria"),
            caution_banner={
                "tone": "authority",
                "title": "Máxima jerarquía normativa",
                "body": "Su lectura debe conectarse con leyes, decretos y sentencias que desarrollan el principio constitucional aplicable.",
            },
        )
    if family == "ley":
        return NormativeDocumentProfile(
            document_family=family,
            family_subtype=subtype,
            hierarchy_tier="legal_primario",
            binding_force="Ley o estatuto",
            binding_force_rank=900,
            analysis_template_id="primary_law_analysis",
            ui_surface=_ui_surface_for_family(family),
            relation_types=("superior_norm", "regulated_by", "modified_by", "superseded_by", "interpreted_by", "questioned_by", "prescribes_form", "summarized_by"),
            allowed_secondary_overlays=("jurisprudencia", "concepto_dian", "interpretacion_secundaria"),
            caution_banner=None,
        )
    if family == "et_dur":
        return NormativeDocumentProfile(
            document_family=family,
            family_subtype=subtype,
            hierarchy_tier="compilacion_vigente",
            binding_force="Compilación tributaria vigente",
            binding_force_rank=860,
            analysis_template_id="compiled_norm_analysis",
            ui_surface=_ui_surface_for_family(family),
            relation_types=("superior_norm", "regulated_by", "modified_by", "superseded_by", "interpreted_by", "questioned_by", "prescribes_form", "summarized_by"),
            allowed_secondary_overlays=("jurisprudencia", "concepto_dian", "interpretacion_secundaria"),
            caution_banner=None,
        )
    if family == "decreto":
        return NormativeDocumentProfile(
            document_family=family,
            family_subtype=subtype,
            hierarchy_tier="reglamentario",
            binding_force="Decreto reglamentario",
            binding_force_rank=800,
            analysis_template_id="decree_analysis",
            ui_surface=_ui_surface_for_family(family),
            relation_types=("superior_norm", "develops", "modified_by", "superseded_by", "interpreted_by", "summarized_by"),
            allowed_secondary_overlays=("jurisprudencia", "concepto_dian", "interpretacion_secundaria"),
            caution_banner=None,
        )
    if family == "jurisprudencia":
        return NormativeDocumentProfile(
            document_family=family,
            family_subtype=subtype,
            hierarchy_tier="judicial",
            binding_force="Precedente judicial",
            binding_force_rank=760,
            analysis_template_id="jurisprudence_analysis",
            ui_surface=_ui_surface_for_family(family),
            relation_types=("superior_norm", "questioned_by", "summarized_by"),
            allowed_secondary_overlays=("ley", "decreto", "resolucion_dian", "concepto_dian", "interpretacion_secundaria"),
            caution_banner={
                "tone": "authority",
                "title": "Interpretación judicial relevante",
                "body": "La sentencia debe leerse junto con la norma aplicada y con su vigencia procesal o material actual.",
            },
        )
    if family == "resolucion":
        return NormativeDocumentProfile(
            document_family=family,
            family_subtype=subtype,
            hierarchy_tier="acto_administrativo_prescriptivo",
            binding_force="Resolución DIAN",
            binding_force_rank=700,
            analysis_template_id="resolution_analysis",
            ui_surface=_ui_surface_for_family(family),
            relation_types=("superior_norm", "develops", "modified_by", "superseded_by", "prescribes_form", "interpreted_by", "summarized_by"),
            allowed_secondary_overlays=("concepto_dian", "jurisprudencia", "interpretacion_secundaria"),
            caution_banner=None,
        )
    if family == "formulario":
        return NormativeDocumentProfile(
            document_family=family,
            family_subtype=subtype,
            hierarchy_tier="instrumento_prescrito",
            binding_force="Instrumento operativo prescrito",
            binding_force_rank=620,
            analysis_template_id="form_guide_preview",
            ui_surface=_ui_surface_for_family(family),
            relation_types=("regulated_by", "superseded_by", "summarized_by"),
            allowed_secondary_overlays=("resolucion_dian", "concepto_dian", "interpretacion_secundaria"),
            caution_banner={
                "tone": "info",
                "title": "Instrumento de diligenciamiento",
                "body": "El formulario no sustituye la norma matriz; sirve para materializar obligaciones ya definidas en ley, decreto o resolución.",
            },
        )
    if family == "concepto":
        return NormativeDocumentProfile(
            document_family=family,
            family_subtype=subtype,
            hierarchy_tier="doctrina_administrativa",
            binding_force="Doctrina administrativa",
            binding_force_rank=360,
            analysis_template_id="concept_analysis",
            ui_surface=_ui_surface_for_family(family),
            relation_types=("superior_norm", "questioned_by", "summarized_by"),
            allowed_secondary_overlays=("ley", "decreto", "resolucion_dian", "jurisprudencia", "interpretacion_secundaria"),
            caution_banner={
                "tone": "warning",
                "title": "No prevalece sobre la norma superior",
                "body": "El concepto orienta criterio administrativo, pero no reemplaza ley, decreto, resolución ni sentencia aplicable.",
            },
        )
    if family == "circular":
        return NormativeDocumentProfile(
            document_family=family,
            family_subtype=subtype,
            hierarchy_tier="lineamiento_administrativo",
            binding_force="Circular administrativa",
            binding_force_rank=320,
            analysis_template_id="circular_analysis",
            ui_surface=_ui_surface_for_family(family),
            relation_types=("superior_norm", "questioned_by", "summarized_by"),
            allowed_secondary_overlays=("ley", "decreto", "resolucion_dian", "jurisprudencia", "interpretacion_secundaria"),
            caution_banner={
                "tone": "warning",
                "title": "Lineamiento de menor fuerza vinculante",
                "body": "La circular debe interpretarse subordinada a la norma que desarrolla y al precedente judicial vigente.",
            },
        )
    return NormativeDocumentProfile(
        document_family="generic",
        family_subtype="documento_general",
        hierarchy_tier="documental",
        binding_force="Documento de soporte",
        binding_force_rank=100,
        analysis_template_id="generic_document_analysis",
        ui_surface="deep_analysis",
        relation_types=("summarized_by",),
        allowed_secondary_overlays=("interpretacion_secundaria",),
        caution_banner=None,
    )


def classify_normative_document(citation: dict[str, Any] | None, row: dict[str, Any] | None = None) -> NormativeDocumentProfile:
    payload = citation if isinstance(citation, dict) else {}
    source_row = row if isinstance(row, dict) else {}
    reference_type = str(payload.get("reference_type") or "").strip().lower()
    authority = str(source_row.get("authority") or payload.get("authority") or "").strip().lower()
    text = _haystack(payload, source_row)
    lowered = text.lower()

    if reference_type in {"constitucion", "constitución"} or _CONSTITUTION_RE.search(text):
        return _profile_for_family("constitucion", subtype="constitucion_politica")
    if reference_type == "formulario" or _FORM_RE.search(text):
        return _profile_for_family("formulario", subtype="formulario_prescrito")
    if reference_type in {"et", "dur", "et_dur"} or _ET_RE.search(text) or _DUR_RE.search(text):
        subtype = "dur_1625" if _DUR_RE.search(text) else "estatuto_tributario"
        return _profile_for_family("et_dur", subtype=subtype)
    if reference_type == "ley" or ("ley_" in lowered or (_LAW_RE.search(text) and "decreto" not in lowered[:30])):
        subtype = "ley_ordinaria"
        if _ET_RE.search(text):
            subtype = "estatuto_tributario"
        return _profile_for_family("ley", subtype=subtype)
    if reference_type == "decreto" or (_DECREE_RE.search(text) and not _DUR_RE.search(text)) or "decreto_" in lowered:
        subtype = "decreto_con_fuerza_de_ley" if "fuerza_ley" in lowered or "decreto ley" in lowered else "decreto_reglamentario"
        return _profile_for_family("decreto", subtype=subtype)
    if reference_type in {"resolucion", "resolucion_dian"} or _RESOLUTION_RE.search(text) or "resoluci" in lowered:
        if "uvt" in lowered or "parametr" in lowered:
            subtype = "resolucion_parametrica"
        elif "formulario" in lowered or "formato" in lowered:
            subtype = "resolucion_prescriptiva"
        else:
            subtype = "resolucion_operativa"
        return _profile_for_family("resolucion", subtype=subtype)
    if reference_type in {"concepto", "concepto_dian"} or _CONCEPT_RE.search(text) or "concepto" in lowered:
        subtype = "oficio_dian" if "oficio" in lowered else "concepto_dian"
        return _profile_for_family("concepto", subtype=subtype)
    if reference_type == "circular" or _CIRCULAR_RE.search(text):
        return _profile_for_family("circular", subtype="circular_administrativa")
    if (
        "jurisprudencia" in lowered
        or _JURISPRUDENCE_RE.search(text)
        or "corte constitucional" in authority
        or "consejo de estado" in authority
        or "corte suprema" in authority
        or str(source_row.get("source_type") or payload.get("source_type") or "").strip().lower() == "sentencia"
    ):
        subtype = "jurisprudencia_constitucional" if "corte constitucional" in authority or re.search(r"\bc-\d+", lowered) else "jurisprudencia_contenciosa"
        return _profile_for_family("jurisprudencia", subtype=subtype)
    return _profile_for_family("generic", subtype="documento_general")
