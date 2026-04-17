from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import unicodedata

from ..pipeline_c.contracts import PipelineCRequest
from .planner import _looks_like_loss_compensation_case, _looks_like_tax_planning_case
from .contracts import GraphEvidenceItem, GraphSupportDocument

_WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
_SUPPORT_PROCEDURE_MARKERS = (
    "procedimiento",
    "paso",
    "verificar",
    "verifica",
    "revisa",
    "radic",
    "presenta",
    "diligencia",
    "compila",
    "prepara",
    "obtiene",
    "cargue",
    "cargar",
    "adjunta",
    "responde",
    "seguimiento",
    "imputa",
    "compensa",
    "devuelve",
)
_SUPPORT_PAPERWORK_MARKERS = (
    "formato",
    "formulario",
    "certificacion",
    "certificado",
    "soporte",
    "anexo",
    "adjunt",
    "garantia",
    "poliza",
    "bancaria",
    "radicado",
    "pdf",
    "factura",
    "revisor fiscal",
    "papel membretado",
)
_SUPPORT_CONTEXT_MARKERS = (
    "ley ",
    "decreto ",
    "dur ",
    "resolucion",
    "vigencia",
    "modific",
    "reforma",
    "periodo",
    "periodo consultado",
    "ano gravable",
    "año gravable",
    "a partir de",
    "antes de",
    "despues de",
    "después de",
    "corte",
    "historic",
)
_SUPPORT_PRECAUTION_MARKERS = (
    "riesgo",
    "rechazo",
    "inadmit",
    "improcedente",
    "sancion",
    "caduc",
    "no solicitar",
    "no responder",
    "no mezclar",
    "auditoria",
    "fraude",
    "vence",
    "vencimiento",
)
_SUPPORT_STRATEGY_MARKERS = (
    "rst",
    "ordinario",
    "perdidas fiscales",
    "beneficio de auditoria",
    "factura electronica",
    "primer empleo",
    "discapacidad",
    "mujeres victimas",
    "donacion",
    "donaciones",
    "timing",
    "timing de ingresos",
    "timing de gastos",
    "leasing",
    "dividendos",
    "remuneracion",
    "nomina",
    "aportes voluntarios",
    "energia renovable",
    "energias renovables",
    "ctei",
    "planeacion debe hacerse antes del cierre",
)
_SUPPORT_JURISPRUDENCE_MARKERS = (
    "economia de opcion",
    "economia de opcion",
    "abuso en materia tributaria",
    "simulacion",
    "elusion",
    "evasion",
    "proposito comercial",
    "proposito economico",
    "actos o negocios juridicos artificiosos",
    "artificiosos",
    "recaracterizar",
    "reconfigurar",
    "beneficio fiscal",
    "riesgos economicos",
    "requerimiento especial",
    "sentencia",
    "consejo de estado",
    "corte suprema",
    "corte constitucional",
)
_SUPPORT_CHECKLIST_MARKERS = (
    "proyeccion de cierre",
    "proyectar ingresos",
    "proyectar costos",
    "inventariar perdidas",
    "simular",
    "verificar",
    "formalice",
    "documente",
    "deje constancia",
    "papeles de trabajo",
    "certificacion",
    "certificaciones",
    "soportes",
)
_SUPPORT_DEADLINE_MARKERS = (
    "dia",
    "dias",
    "días",
    "mes",
    "meses",
    "ano",
    "año",
    "anos",
    "años",
    "plazo",
    "plazos",
    "termino",
    "término",
    "habiles",
    "hábiles",
)
_SUPPORT_LINE_DROP_PREFIXES = (
    "tema principal:",
    "tipo de corpus:",
    "fecha de ultima verificacion:",
    "fecha de última verificación:",
    "alcance:",
    "serie:",
    "version:",
    "audiencia:",
    "proposito:",
    "propósito:",
    "fuentes directas:",
    "fuentes secundarias:",
    "cross-references:",
    "escenario real:",
    "caso real:",
)
_SUPPORT_LINE_DROP_CONTAINS = (
    "consultado:",
    "disponible en:",
    "verificado contra:",
    "normograma",
    "loggro",
    "http://",
    "https://",
    "www.",
)
_QUERY_TOKEN_STOPWORDS = frozenset(
    {
        "que",
        "como",
        "para",
        "con",
        "sin",
        "del",
        "las",
        "los",
        "una",
        "uno",
        "unos",
        "unas",
        "sobre",
        "entre",
        "cliente",
        "clientes",
        "dian",
        "ante",
        "caso",
        "tema",
        "ser",
        "esta",
        "este",
        "estos",
        "estas",
        "cual",
        "cuales",
        "cuando",
        "donde",
        "debe",
        "deben",
        "tiene",
        "tienen",
        "dia",
        "ano",
        "gravable",
        "declaracion",
        "renta",
        "persona",
        "juridica",
        "puedo",
        "pagado",
        "pagados",
        "impuesto",
        "impuestos",
    }
)
_TRUNCATION_MARKERS = ("...", "…", "[truncated]")
_SUPPORT_DOC_BUCKET_LIMITS = {
    "procedure": 6,
    "paperwork": 4,
    "context": 3,
    "precaution": 4,
    "strategy": 6,
    "jurisprudence": 5,
    "checklist": 5,
}
_ARTICLE_BUCKET_LIMITS = {
    "procedure": 4,
    "paperwork": 3,
    "context": 4,
    "precaution": 3,
    "jurisprudence": 4,
}


@dataclass(frozen=True)
class _InsightExtractionContext:
    normalized_message: str
    query_tokens: tuple[str, ...]
    is_tax_planning_case: bool
    is_loss_compensation_case: bool
    query_mentions_rst: bool


@dataclass(frozen=True)
class _InsightLineSignals:
    has_procedure_marker: bool
    has_paperwork_marker: bool
    has_context_marker: bool
    has_precaution_marker: bool
    has_strategy_marker: bool
    has_jurisprudence_marker: bool
    has_checklist_marker: bool
    has_deadline_marker: bool


@dataclass(frozen=True)
class _InsightCandidate:
    line: str
    bucket_scores: tuple[tuple[str, float], ...]


def extract_support_doc_insights(
    *,
    request: PipelineCRequest,
    support_documents: tuple[GraphSupportDocument, ...],
) -> dict[str, tuple[str, ...]]:
    context = _build_insight_extraction_context(request)
    candidates = _collect_support_doc_insight_candidates(
        context=context,
        support_documents=support_documents,
    )
    return _project_ranked_insight_buckets(
        candidates,
        bucket_limits=_support_doc_bucket_limits(context),
    )


def extract_article_insights(
    *,
    request: PipelineCRequest,
    temporal_context: dict[str, object],
    primary_articles: tuple[GraphEvidenceItem, ...],
    connected_articles: tuple[GraphEvidenceItem, ...],
) -> dict[str, tuple[str, ...]]:
    context = _build_insight_extraction_context(request)
    candidates = _collect_article_insight_candidates(
        context=context,
        temporal_context=temporal_context,
        primary_articles=primary_articles,
        connected_articles=connected_articles,
    )
    return _project_ranked_insight_buckets(
        candidates,
        bucket_limits=_article_bucket_limits(context),
    )


def clean_support_line_for_answer(value: str) -> str:
    line = re.sub(r"\s+", " ", str(value or "")).strip(" -")
    if not line:
        return ""
    if "→" in line or "➜" in line:
        return ""
    if _looks_truncated_line(line):
        return ""
    line = re.sub(r"https?://\S+", "", line)
    line = re.sub(
        r"^(?:Actual[íi]cese|Gerencie\.com|Gerencie|[ÁA]mbito Jur[ií]dico|DIAN)\s*(?::|[-—])\s*",
        "",
        line,
        flags=re.IGNORECASE,
    )
    line = re.sub(r"^\(?[a-z0-9]+\)\s*", "", line, flags=re.IGNORECASE)
    line = re.sub(r"^\d+\.\s*", "", line)
    line = re.sub(r"^\d+\s+", "", line)
    line = re.sub(r"^(?:acci[oó]n|paso)\s*:\s*", "", line, flags=re.IGNORECASE)
    line = re.sub(r"^\[[^\]]+\]\s*", "", line)
    line = re.sub(r"^\[paso\s*\d+\]\s*", "", line, flags=re.IGNORECASE)
    line = re.sub(r"^(?:estrategia|paso|convergencia|fase)\s*\d*\s*[—:-]\s*", "", line, flags=re.IGNORECASE)
    line = re.sub(r"^divergencia\s*[a-z0-9-]*\s*[—:-]\s*", "", line, flags=re.IGNORECASE)
    line = re.sub(r"^[→➜]+\s*", "", line)
    line = re.sub(r"^\[\s*\]\s*", "", line)
    line = line.strip(" -:")
    normalized = _normalize_text(line)
    if normalized.startswith(("escenario real", "caso real")):
        return ""
    if not line or any(token in normalized for token in _SUPPORT_LINE_DROP_CONTAINS):
        return ""
    if re.match(r'^[\"“].+[\"”]\s*\([^)]*\d{4}[^)]*\)\.?$', line):
        return ""
    if _looks_like_heading_line(line):
        return ""
    if line and line[-1] not in ".!?":
        line += "."
    return line


def _build_insight_extraction_context(request: PipelineCRequest) -> _InsightExtractionContext:
    normalized_message = _normalize_text(request.message)
    return _InsightExtractionContext(
        normalized_message=normalized_message,
        query_tokens=_query_tokens(request.message),
        is_tax_planning_case=_looks_like_tax_planning_case(normalized_message),
        is_loss_compensation_case=_looks_like_loss_compensation_case(normalized_message),
        query_mentions_rst=any(
            marker in normalized_message
            for marker in (
                "rst",
                "regimen simple",
                "regimen simple de tributacion",
            )
        ),
    )


def _support_doc_bucket_limits(context: _InsightExtractionContext) -> dict[str, int]:
    _ = context
    return dict(_SUPPORT_DOC_BUCKET_LIMITS)


def _article_bucket_limits(context: _InsightExtractionContext) -> dict[str, int]:
    _ = context
    return dict(_ARTICLE_BUCKET_LIMITS)


def _collect_support_doc_insight_candidates(
    *,
    context: _InsightExtractionContext,
    support_documents: tuple[GraphSupportDocument, ...],
) -> list[_InsightCandidate]:
    candidates: list[_InsightCandidate] = []
    for doc in support_documents:
        if str(doc.family or "") not in {"practica", "interpretacion"}:
            continue
        text = _load_support_doc_text(doc)
        if not text:
            continue
        family_bonus = 0.6 if str(doc.family or "") == "practica" else 0.35
        is_tax_planning_doc = _is_tax_planning_support_doc(doc)
        if is_tax_planning_doc and not (context.is_tax_planning_case or context.query_mentions_rst):
            continue
        candidate_lines = list(_support_doc_candidate_lines(text))
        if context.is_tax_planning_case and is_tax_planning_doc:
            candidate_lines.extend(_support_doc_table_row_candidates(text))
        for line in candidate_lines:
            candidate = _build_support_doc_insight_candidate(
                context=context,
                line=line,
                family_bonus=family_bonus,
                is_tax_planning_doc=is_tax_planning_doc,
            )
            if candidate is not None:
                candidates.append(candidate)
    return candidates


def _build_support_doc_insight_candidate(
    *,
    context: _InsightExtractionContext,
    line: str,
    family_bonus: float,
    is_tax_planning_doc: bool,
) -> _InsightCandidate | None:
    normalized_line = _normalize_text(line)
    if not normalized_line:
        return None
    query_overlap = _query_overlap_count(normalized_line, context.query_tokens)
    signals = _detect_line_signals(normalized_line)
    planning_relevant_line = (
        context.is_tax_planning_case
        and is_tax_planning_doc
        and (
            signals.has_strategy_marker
            or signals.has_jurisprudence_marker
            or signals.has_checklist_marker
        )
    )
    loss_compensation_relevant_line = (
        context.is_loss_compensation_case
        and any(
            marker in normalized_line
            for marker in (
                "perdida fiscal",
                "perdidas fiscales",
                "compensacion",
                "renta liquida",
                "firmeza",
                "termino de revision",
            )
        )
    )
    if query_overlap == 0 and not planning_relevant_line:
        return None
    if context.is_loss_compensation_case and not loss_compensation_relevant_line:
        return None
    score = _support_line_score(
        normalized_line,
        context.query_tokens,
        family_bonus=family_bonus,
    )
    if planning_relevant_line:
        score += 1.2
    if score < (1.8 if planning_relevant_line else 2.2):
        return None
    bucket_scores = _support_doc_bucket_scores(
        context=context,
        signals=signals,
        score=score,
    )
    if not bucket_scores:
        return None
    return _InsightCandidate(
        line=line,
        bucket_scores=bucket_scores,
    )


def _support_doc_bucket_scores(
    *,
    context: _InsightExtractionContext,
    signals: _InsightLineSignals,
    score: float,
) -> tuple[tuple[str, float], ...]:
    bucket_scores: list[tuple[str, float]] = []
    if signals.has_procedure_marker:
        bucket_scores.append(("procedure", score + 0.6))
    if signals.has_paperwork_marker:
        bucket_scores.append(("paperwork", score + 0.8))
    if signals.has_context_marker:
        bucket_scores.append(("context", score + 0.4))
    if signals.has_precaution_marker:
        bucket_scores.append(("precaution", score + 0.5))
    if context.is_tax_planning_case and signals.has_strategy_marker:
        bucket_scores.append(("strategy", score + 1.2))
    if context.is_tax_planning_case and signals.has_jurisprudence_marker:
        bucket_scores.append(("jurisprudence", score + 1.1))
    if context.is_tax_planning_case and signals.has_checklist_marker:
        bucket_scores.append(("checklist", score + 1.0))
    return tuple(bucket_scores)


def _collect_article_insight_candidates(
    *,
    context: _InsightExtractionContext,
    temporal_context: dict[str, object],
    primary_articles: tuple[GraphEvidenceItem, ...],
    connected_articles: tuple[GraphEvidenceItem, ...],
) -> list[_InsightCandidate]:
    candidates: list[_InsightCandidate] = []
    for item in (*primary_articles, *connected_articles[:2]):
        cleaned_excerpt = _clean_evidence_excerpt_for_answer(
            item.excerpt,
            temporal_context=temporal_context,
        )
        if not cleaned_excerpt:
            continue
        for line in _evidence_candidate_lines(cleaned_excerpt):
            candidate = _build_article_insight_candidate(
                context=context,
                line=line,
                hop_distance=item.hop_distance,
            )
            if candidate is not None:
                candidates.append(candidate)
    return candidates


def _build_article_insight_candidate(
    *,
    context: _InsightExtractionContext,
    line: str,
    hop_distance: int,
) -> _InsightCandidate | None:
    normalized_line = _normalize_text(line)
    if not normalized_line:
        return None
    query_overlap = _query_overlap_count(normalized_line, context.query_tokens)
    signals = _detect_line_signals(normalized_line)
    score = _evidence_line_score(
        normalized_line=normalized_line,
        query_tokens=context.query_tokens,
        hop_distance=hop_distance,
    )
    if score < 2.0:
        return None
    bucket_scores = _article_bucket_scores(
        context=context,
        signals=signals,
        query_overlap=query_overlap,
        normalized_line=normalized_line,
        score=score,
    )
    if not bucket_scores:
        return None
    return _InsightCandidate(
        line=line,
        bucket_scores=bucket_scores,
    )


def _article_bucket_scores(
    *,
    context: _InsightExtractionContext,
    signals: _InsightLineSignals,
    query_overlap: int,
    normalized_line: str,
    score: float,
) -> tuple[tuple[str, float], ...]:
    bucket_scores: list[tuple[str, float]] = []
    if signals.has_procedure_marker and query_overlap > 0:
        bucket_scores.append(("procedure", score + 0.5))
    if signals.has_paperwork_marker and query_overlap > 0:
        bucket_scores.append(("paperwork", score + 0.3))
    if query_overlap > 0 and (signals.has_context_marker or signals.has_deadline_marker):
        bucket_scores.append(("context", score + 0.4))
    if signals.has_precaution_marker and query_overlap > 0:
        bucket_scores.append(("precaution", score + 0.4))
    if (
        context.is_tax_planning_case
        and (
            signals.has_jurisprudence_marker
            or "proposito economico" in normalized_line
            or "proposito comercial" in normalized_line
            or "beneficio fiscal" in normalized_line
        )
    ):
        bucket_scores.append(("jurisprudence", score + 0.8))
    return tuple(bucket_scores)


def _project_ranked_insight_buckets(
    candidates: list[_InsightCandidate],
    *,
    bucket_limits: dict[str, int],
) -> dict[str, tuple[str, ...]]:
    ranked: dict[str, list[tuple[float, str]]] = {
        bucket: []
        for bucket in bucket_limits
    }
    for candidate in candidates:
        for bucket, bucket_score in candidate.bucket_scores:
            if bucket in ranked:
                _append_scored_line(ranked[bucket], candidate.line, bucket_score)
    return {
        bucket: _top_ranked_lines(ranked[bucket], limit=limit)
        for bucket, limit in bucket_limits.items()
    }


def _load_support_doc_text(doc: GraphSupportDocument) -> str:
    source_path = str(doc.source_path or "").strip()
    if not source_path:
        return ""
    path = (_WORKSPACE_ROOT / source_path).resolve()
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _support_doc_candidate_lines(text: str) -> tuple[str, ...]:
    lines: list[str] = []
    for raw in str(text or "").splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        if stripped.startswith(("```", "#", ">", "|")) or stripped == "---":
            continue
        cleaned = stripped
        cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleaned)
        cleaned = re.sub(r"https?://\S+", "", cleaned)
        cleaned = cleaned.replace("**", "").replace("__", "").replace("*", "")
        cleaned = re.sub(r"^\s*(?:[-+]|[0-9]+\.)\s*", "", cleaned)
        cleaned = re.sub(r"^\s*[a-z]\)\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"^\[\s*\]\s*", "", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" -:")
        normalized = _normalize_text(cleaned)
        if not cleaned or len(cleaned) < 35 or len(cleaned) > 220:
            continue
        if _looks_truncated_line(cleaned):
            continue
        if any(normalized.startswith(prefix) for prefix in _SUPPORT_LINE_DROP_PREFIXES):
            continue
        if any(token in normalized for token in _SUPPORT_LINE_DROP_CONTAINS):
            continue
        if normalized.count(" - ") > 4:
            continue
        lines.append(cleaned.rstrip(".") + ".")
    return tuple(lines)


def _support_doc_table_row_candidates(text: str) -> tuple[str, ...]:
    lines: list[str] = []
    for raw in str(text or "").splitlines():
        stripped = raw.strip()
        if not stripped.startswith("|"):
            continue
        if set(stripped.replace("|", "").replace("-", "").replace(":", "").strip()) == set():
            continue
        cells = [
            re.sub(r"\s+", " ", cell.replace("**", "").replace("__", "").replace("*", "")).strip()
            for cell in stripped.strip("|").split("|")
        ]
        cells = [cell for cell in cells if cell]
        if len(cells) < 3:
            continue
        if cells[0].lower() in {"#", "concepto", "estrategia", "variable", "aspecto"}:
            continue
        first_cell = _normalize_text(cells[0])
        line = ""
        if re.fullmatch(r"[ed]-\d+", first_cell):
            strategy = cells[1]
            basis = cells[2]
            detail = cells[3] if len(cells) >= 4 else ""
            risk = cells[4] if len(cells) >= 5 else ""
            pieces = [strategy]
            if detail:
                pieces.append(detail)
            if risk:
                pieces.append(f"Riesgo {risk}.")
            line = " ".join(piece.strip() for piece in pieces if piece.strip())
            if basis:
                line = line.rstrip(".") + f" ({basis})."
        elif len(cells) >= 3:
            lead, detail, implication = cells[0], cells[1], cells[2]
            line = f"{lead}: {detail} {implication}".strip()
            if len(cells) >= 4 and cells[3]:
                line = line.rstrip(".") + f" Riesgo {cells[3]}."
        line = re.sub(r"\s+", " ", line).strip()
        if len(line) < 45 or len(line) > 260:
            continue
        lines.append(line.rstrip(".") + ".")
    return tuple(lines)


def _clean_evidence_excerpt_for_answer(
    value: str,
    *,
    temporal_context: dict[str, object],
) -> str:
    line = str(value or "")
    if not line:
        return ""
    line = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", line)
    line = re.sub(r"https?://\S+", "", line)
    line = line.replace("**", "").replace("__", "").replace("*", " ")
    line = line.replace("<", " ").replace(">", " ")
    line = re.sub(r"\(\d+\)", "", line)
    line = re.split(
        r"\b(?:Concordancias|Jurisprudencia|Doctrina|Legislaci[oó]n Anterior|Notas de Vigencia|Notas del Editor)\b",
        line,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    if bool(temporal_context.get("historical_query_intent")):
        line = re.sub(
            r"^.*?texto vigente antes de la modificaci[oó]n introducida por[^:]*:\s*",
            "",
            line,
            flags=re.IGNORECASE,
        )
    line = re.sub(r"^\s*art[ií]culo modificado por[^:]*:\s*", "", line, flags=re.IGNORECASE)
    line = re.sub(r"^\s*el nuevo texto es el siguiente:\s*", "", line, flags=re.IGNORECASE)
    line = re.sub(r"^\s*art[ií]culo\s+\d+(?:-\d+)?\.\s*", "", line, flags=re.IGNORECASE)
    line = re.sub(r"\s+", " ", line).strip(" -:")
    return line


def _evidence_candidate_lines(text: str) -> tuple[str, ...]:
    lines: list[str] = []
    for raw in re.split(r"(?<=[\.;:])\s+", str(text or "")):
        cleaned = re.sub(r"\s+", " ", raw).strip(" -:")
        normalized = _normalize_text(cleaned)
        if not cleaned or len(cleaned) < 45 or len(cleaned) > 240:
            continue
        if _looks_truncated_line(cleaned):
            continue
        if any(token in normalized for token in _SUPPORT_LINE_DROP_CONTAINS):
            continue
        if cleaned.startswith("."):
            cleaned = cleaned.lstrip(". ").strip()
        if cleaned.startswith(":"):
            cleaned = cleaned.lstrip(": ").strip()
        if cleaned.startswith("Artículo modificado"):
            continue
        if cleaned and cleaned[-1] not in ".!?":
            cleaned += "."
        lines.append(cleaned)
    return tuple(lines)


def _support_line_score(
    normalized_line: str,
    query_tokens: tuple[str, ...],
    *,
    family_bonus: float,
) -> float:
    line_tokens = _line_token_set(normalized_line)
    score = family_bonus
    score += sum(1 for token in query_tokens if token in line_tokens) * 1.8
    if _line_matches_any(normalized_line, _SUPPORT_PROCEDURE_MARKERS):
        score += 1.1
    if _line_matches_any(normalized_line, _SUPPORT_PAPERWORK_MARKERS):
        score += 1.2
    if _line_matches_any(normalized_line, _SUPPORT_CONTEXT_MARKERS):
        score += 0.8
    if _line_matches_any(normalized_line, _SUPPORT_PRECAUTION_MARKERS):
        score += 0.7
    if _line_matches_any(normalized_line, _SUPPORT_STRATEGY_MARKERS):
        score += 0.9
    if _line_matches_any(normalized_line, _SUPPORT_JURISPRUDENCE_MARKERS):
        score += 1.0
    if _line_matches_any(normalized_line, _SUPPORT_CHECKLIST_MARKERS):
        score += 0.8
    return score


def _evidence_line_score(
    *,
    normalized_line: str,
    query_tokens: tuple[str, ...],
    hop_distance: int,
) -> float:
    line_tokens = _line_token_set(normalized_line)
    score = 0.8
    score += sum(1 for token in query_tokens if token in line_tokens) * 1.6
    if _line_matches_any(normalized_line, _SUPPORT_PROCEDURE_MARKERS):
        score += 0.9
    if _line_matches_any(normalized_line, _SUPPORT_PAPERWORK_MARKERS):
        score += 0.7
    if _line_matches_any(normalized_line, _SUPPORT_CONTEXT_MARKERS):
        score += 0.8
    if _line_matches_any(normalized_line, _SUPPORT_PRECAUTION_MARKERS):
        score += 0.7
    if _line_matches_any(normalized_line, _SUPPORT_DEADLINE_MARKERS):
        score += 1.0
    if _line_matches_any(normalized_line, _SUPPORT_JURISPRUDENCE_MARKERS):
        score += 0.9
    if hop_distance == 0:
        score += 0.5
    return score


def _is_tax_planning_support_doc(doc: GraphSupportDocument) -> bool:
    joined = " ".join(
        str(value or "")
        for value in (
            doc.title_hint,
            doc.relative_path,
            doc.source_path,
            doc.subtopic_key,
        )
    )
    normalized = _normalize_text(joined)
    return "planeacion" in normalized or "economia de opcion" in normalized or "rst" in normalized


def _query_tokens(text: str) -> tuple[str, ...]:
    tokens = [
        token
        for token in re.split(r"[^a-z0-9]+", _normalize_text(text))
        if len(token) >= 3 and token not in _QUERY_TOKEN_STOPWORDS
    ]
    return tuple(dict.fromkeys(tokens))


def _line_token_set(text: str) -> set[str]:
    return {
        token
        for token in re.split(r"[^a-z0-9]+", _normalize_text(text))
        if len(token) >= 3
    }


def _query_overlap_count(text: str, query_tokens: tuple[str, ...]) -> int:
    line_tokens = _line_token_set(text)
    return sum(1 for token in query_tokens if token in line_tokens)


def _detect_line_signals(normalized_line: str) -> _InsightLineSignals:
    return _InsightLineSignals(
        has_procedure_marker=_line_matches_any(normalized_line, _SUPPORT_PROCEDURE_MARKERS),
        has_paperwork_marker=_line_matches_any(normalized_line, _SUPPORT_PAPERWORK_MARKERS),
        has_context_marker=_line_matches_any(normalized_line, _SUPPORT_CONTEXT_MARKERS),
        has_precaution_marker=_line_matches_any(normalized_line, _SUPPORT_PRECAUTION_MARKERS),
        has_strategy_marker=_line_matches_any(normalized_line, _SUPPORT_STRATEGY_MARKERS),
        has_jurisprudence_marker=_line_matches_any(normalized_line, _SUPPORT_JURISPRUDENCE_MARKERS),
        has_checklist_marker=_line_matches_any(normalized_line, _SUPPORT_CHECKLIST_MARKERS),
        has_deadline_marker=_line_matches_any(normalized_line, _SUPPORT_DEADLINE_MARKERS),
    )


def _line_matches_any(line: str, markers: tuple[str, ...]) -> bool:
    return any(marker in line for marker in markers)


def _looks_truncated_line(value: str) -> bool:
    normalized = _normalize_text(value)
    return any(marker in value for marker in _TRUNCATION_MARKERS) or "[truncated]" in normalized


def _looks_like_heading_line(value: str) -> bool:
    prefix = re.split(r"[\(\.:]", value, maxsplit=1)[0].strip()
    letters = [char for char in prefix if char.isalpha()]
    if len(letters) < 8:
        return False
    uppercase_ratio = sum(1 for char in letters if char.isupper()) / len(letters)
    word_count = len(re.findall(r"[A-Za-zÁÉÍÓÚáéíóúÑñ0-9]+", prefix))
    return uppercase_ratio >= 0.7 and word_count <= 8


def _append_scored_line(bucket: list[tuple[float, str]], line: str, score: float) -> None:
    clean = re.sub(r"\s+", " ", str(line or "")).strip()
    if not clean:
        return
    for index, (_, existing) in enumerate(bucket):
        if existing == clean:
            if score > bucket[index][0]:
                bucket[index] = (score, clean)
            return
    bucket.append((score, clean))


def _top_ranked_lines(items: list[tuple[float, str]], *, limit: int) -> tuple[str, ...]:
    ranked = sorted(items, key=lambda item: (-item[0], item[1]))
    return tuple(line for _, line in ranked[:limit])


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_text).strip().lower()


__all__ = [
    "clean_support_line_for_answer",
    "extract_article_insights",
    "extract_support_doc_insights",
]
