from __future__ import annotations

from pathlib import Path
import re
import unicodedata

from ..pipeline_c.contracts import PipelineCRequest
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
    "carga",
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
)
_SUPPORT_LINE_DROP_CONTAINS = (
    "consultado:",
    "disponible en:",
    "verificado contra:",
    "normograma",
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


def extract_support_doc_insights(
    *,
    request: PipelineCRequest,
    support_documents: tuple[GraphSupportDocument, ...],
) -> dict[str, tuple[str, ...]]:
    ranked: dict[str, list[tuple[float, str]]] = {
        "procedure": [],
        "paperwork": [],
        "context": [],
        "precaution": [],
    }
    query_tokens = _query_tokens(request.message)
    for doc in support_documents:
        if str(doc.family or "") not in {"practica", "interpretacion"}:
            continue
        text = _load_support_doc_text(doc)
        if not text:
            continue
        family_bonus = 0.6 if str(doc.family or "") == "practica" else 0.35
        for line in _support_doc_candidate_lines(text):
            normalized = _normalize_text(line)
            if not normalized:
                continue
            score = _support_line_score(normalized, query_tokens, family_bonus=family_bonus)
            if score < 2.2:
                continue
            if _line_matches_any(normalized, _SUPPORT_PROCEDURE_MARKERS):
                _append_scored_line(ranked["procedure"], line, score + 0.6)
            if _line_matches_any(normalized, _SUPPORT_PAPERWORK_MARKERS):
                _append_scored_line(ranked["paperwork"], line, score + 0.8)
            if _line_matches_any(normalized, _SUPPORT_CONTEXT_MARKERS):
                _append_scored_line(ranked["context"], line, score + 0.4)
            if _line_matches_any(normalized, _SUPPORT_PRECAUTION_MARKERS):
                _append_scored_line(ranked["precaution"], line, score + 0.5)
    return {
        "procedure": _top_ranked_lines(ranked["procedure"], limit=4),
        "paperwork": _top_ranked_lines(ranked["paperwork"], limit=4),
        "context": _top_ranked_lines(ranked["context"], limit=3),
        "precaution": _top_ranked_lines(ranked["precaution"], limit=3),
    }


def extract_article_insights(
    *,
    request: PipelineCRequest,
    temporal_context: dict[str, object],
    primary_articles: tuple[GraphEvidenceItem, ...],
    connected_articles: tuple[GraphEvidenceItem, ...],
) -> dict[str, tuple[str, ...]]:
    ranked: dict[str, list[tuple[float, str]]] = {
        "procedure": [],
        "paperwork": [],
        "context": [],
        "precaution": [],
    }
    query_tokens = _query_tokens(request.message)
    for item in (*primary_articles, *connected_articles[:2]):
        cleaned_excerpt = _clean_evidence_excerpt_for_answer(
            item.excerpt,
            temporal_context=temporal_context,
        )
        if not cleaned_excerpt:
            continue
        for line in _evidence_candidate_lines(cleaned_excerpt):
            normalized = _normalize_text(line)
            score = _evidence_line_score(
                normalized_line=normalized,
                query_tokens=query_tokens,
                hop_distance=item.hop_distance,
            )
            if score < 2.0:
                continue
            if _line_matches_any(normalized, _SUPPORT_PROCEDURE_MARKERS) or _line_matches_any(
                normalized, _SUPPORT_DEADLINE_MARKERS
            ):
                _append_scored_line(ranked["procedure"], line, score + 0.5)
            if _line_matches_any(normalized, _SUPPORT_PAPERWORK_MARKERS):
                _append_scored_line(ranked["paperwork"], line, score + 0.3)
            if _line_matches_any(normalized, _SUPPORT_CONTEXT_MARKERS) or _line_matches_any(
                normalized, _SUPPORT_DEADLINE_MARKERS
            ):
                _append_scored_line(ranked["context"], line, score + 0.4)
            if _line_matches_any(normalized, _SUPPORT_PRECAUTION_MARKERS):
                _append_scored_line(ranked["precaution"], line, score + 0.4)
    return {
        "procedure": _top_ranked_lines(ranked["procedure"], limit=3),
        "paperwork": _top_ranked_lines(ranked["paperwork"], limit=2),
        "context": _top_ranked_lines(ranked["context"], limit=4),
        "precaution": _top_ranked_lines(ranked["precaution"], limit=2),
    }


def clean_support_line_for_answer(value: str) -> str:
    line = re.sub(r"\s+", " ", str(value or "")).strip(" -")
    if not line:
        return ""
    line = re.sub(r"https?://\S+", "", line)
    line = re.sub(
        r"^(?:Actual[íi]cese|Gerencie\.com|Gerencie|[ÁA]mbito Jur[ií]dico|DIAN)\s*:\s*",
        "",
        line,
        flags=re.IGNORECASE,
    )
    line = re.sub(r"^\(?[a-z0-9]+\)\s*", "", line, flags=re.IGNORECASE)
    line = re.sub(r"^\d+\.\s*", "", line)
    line = re.sub(r"^\d+\s+", "", line)
    line = re.sub(r"^(?:acci[oó]n|paso)\s*:\s*", "", line, flags=re.IGNORECASE)
    line = re.sub(r"^\[\s*\]\s*", "", line)
    line = line.strip(" -:")
    normalized = _normalize_text(line)
    if not line or any(token in normalized for token in _SUPPORT_LINE_DROP_CONTAINS):
        return ""
    if line and line[-1] not in ".!?":
        line += "."
    return line


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
        if any(normalized.startswith(prefix) for prefix in _SUPPORT_LINE_DROP_PREFIXES):
            continue
        if any(token in normalized for token in _SUPPORT_LINE_DROP_CONTAINS):
            continue
        if normalized.count(" - ") > 4:
            continue
        lines.append(cleaned.rstrip(".") + ".")
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
    if hop_distance == 0:
        score += 0.5
    return score


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


def _line_matches_any(line: str, markers: tuple[str, ...]) -> bool:
    return any(marker in line for marker in markers)


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
