"""fixplan_v4 §6.B — ingest an outside-expert deliverable packet into the corpus.

Reads one of the brief markdown files produced by the corpus-population
campaign (`docs/re-engineer/corpus_population_for_experts/<NN>_<source>.md`
delivered by an outside expert) and emits canonical-id-shaped rows for
`artifacts/parsed_articles.jsonl`.

Each row obeys the §6.1 schema:
  norm_id, norm_type, article_key, body, source_url, fecha_emision, emisor, tema

The body field is prefixed with a `[CITA: ...]` line containing the
natural-language citation form so that
`scripts/canonicalizer/build_extraction_input_set.py` (which runs
`canon.find_mentions()` over body text, NOT a `norm_id` field) picks the
norm up.

Usage:
  PYTHONPATH=src:. uv run python scripts/canonicalizer/ingest_expert_packet.py \\
      --brief-num 11 \\
      --packet "/path/to/brief_11_pensional_salud_parafiscales.md" \\
      --output /tmp/brief_11_staging.jsonl

The script does NOT mutate `artifacts/parsed_articles.jsonl` directly. The
caller validates the staging file via §6.B step 4 round-trip gate, then
appends with `cat <staging> >> artifacts/parsed_articles.jsonl`.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator

LOGGER = logging.getLogger("ingest_expert_packet")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ParentContext:
    """Current normative parent — flows into article norm_ids."""

    family: str  # "ley" | "decreto" | "res_dian" | "concepto_unif" | "oficio_topic" | "concepto_topic" | "sentencia_topic" | "cco" | "cst"
    num: str = ""
    year: str = ""
    label: str = ""
    fecha_emision: str | None = None
    source_url: str | None = None


@dataclass
class Section:
    """One H1/H2 section of the brief."""

    level: int  # 1 or 2
    heading: str
    body_lines: list[str] = field(default_factory=list)


@dataclass
class Issue:
    section_heading: str
    reason: str


# ---------------------------------------------------------------------------
# Brief routing — per-brief parser config
# ---------------------------------------------------------------------------

# Each brief routes to one of these family handlers. The handler decides:
#   1. How to detect parent-context updates from H1/H2 headings.
#   2. How to detect an article heading and produce a canonical norm_id.
#   3. What citation form to inject at the top of the body.
#   4. What `norm_type` and `tema` to assign.

# Brief 11 / 12 handle multiple parent families inside one file (Ley, CCo, etc.)
# — those use a more permissive parent-detector regex.

DEFAULT_LEY_TEMA = "labor_pensional"
DEFAULT_CCO_TEMA = "sociedades_comerciales"


# Parent header detectors -----------------------------------------------------

# "Ley NNN de YYYY (...)" — H1 or H2
_PARENT_LEY_RE = re.compile(
    r"^\s*Ley\s+(?P<num>\d+)\s+de\s+(?P<year>\d{4})\b",
    re.IGNORECASE,
)

# "Decreto Legislativo NNN de YYYY (...)" or "Decreto NNN de YYYY"
_PARENT_DECRETO_RE = re.compile(
    r"^\s*Decreto(?:\s+Legislativo)?\s+(?P<num>\d+)\s+de\s+(?P<year>\d{4})\b",
    re.IGNORECASE,
)

# "Resolución DIAN NNNN de YYYY — ..."
_PARENT_RES_DIAN_RE = re.compile(
    r"^\s*Resoluci[oó]n\s+DIAN\s+(?P<num>\d+)\s+de\s+(?P<year>\d{4})\b",
    re.IGNORECASE,
)

# "Concepto General Unificado <X> — NNNN de YYYY"
# Also matches "Concepto Unificado NNNN de YYYY (topic)" — second-position topic.
_PARENT_CONCEPTO_UNIF_RE = re.compile(
    r"^\s*Concepto(?:\s+General)?\s+Unificado"
    r"(?:\s+[A-Za-zÁÉÍÓÚÑáéíóúñ /\-]+?\s*[—-]\s*)?\s+"
    r"(?P<num>\d+)\s+de\s+(?P<year>\d{4})\b",
    re.IGNORECASE,
)

# "Concepto NNNNNN de YYYY" (individual unified, brief 08 fallback)
_PARENT_CONCEPTO_INDIV_RE = re.compile(
    r"^\s*Concepto\s+(?P<num>\d+)\s+de\s+(?P<year>\d{4})\b",
    re.IGNORECASE,
)

# Topic groupers in brief 09/10
_PARENT_TOPIC_OFICIO_RE = re.compile(r"^\s*Oficios\s+DIAN\b", re.IGNORECASE)
_PARENT_TOPIC_CONCEPTO_RE = re.compile(r"^\s*Conceptos\b", re.IGNORECASE)
_PARENT_TOPIC_SENT_RE = re.compile(r"^\s*I\d\b|^\s*Sentencias\s+(?:CC|CE)\b", re.IGNORECASE)

# "Código de Comercio (...) Libro II" — brief 12
_PARENT_CCO_RE = re.compile(r"^\s*C[oó]digo\s+de\s+Comercio\b", re.IGNORECASE)

# Skip placeholder Ley sections (brief 11 has [FETCH FAILED] notes)
_PARENT_FETCH_FAILED_RE = re.compile(r"\[FETCH FAILED\]", re.IGNORECASE)


# Article header detectors ----------------------------------------------------

# "Artículo N" — also matches "Artículo 1.2.3" and "Artículo 14A" (letter suffix
# captured separately and rejected during canonicalization).
_ART_HEADER_RE = re.compile(
    r"^\s*Art[íi]culo\s+(?P<num>\d+(?:\.\d+)*(?:-\d+)?(?:[A-Z])?)\b",
    re.IGNORECASE,
)

# Bare dotted number (brief 02-04 use "## 1.1.1")
_BARE_DOTTED_RE = re.compile(r"^\s*(?P<num>\d+(?:\.\d+)+)\s*$")

# "Numeral X.Y-Z-W" or "Numeral N" — brief 08
_NUMERAL_HEADER_RE = re.compile(
    r"^\s*Numeral\s+(?P<num>[\d\.\-]+)\s*$",
    re.IGNORECASE,
)

# "Oficio NNN de YYYY" — brief 09
_OFICIO_HEADER_RE = re.compile(
    r"^\s*Oficio\s+(?P<num>\d+)\s+de\s+(?P<year>\d{4})\s*$",
    re.IGNORECASE,
)

# "Concepto NNNNNN" or "Concepto NNNNNN de YYYY" — brief 09 individual conceptos
_CONCEPTO_INDIV_HEADER_RE = re.compile(
    r"^\s*Concepto\s+(?P<num>\d+(?:-\d+)?)(?:\s+de\s+(?P<year>\d{4}))?\s*$",
    re.IGNORECASE,
)

# "Sentencia C/NNN de YY" — brief 10
_SENTENCIA_HEADER_RE = re.compile(
    r"^\s*Sentencia\s+(?P<type>[CTSU][U]?A?)/(?P<num>\d+)\s+de\s+(?P<year>\d{2,4})\s*$",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

_HEADING_RE = re.compile(r"^(?P<hashes>#{1,6})\s+(?P<text>.+?)\s*$")
_URL_LINE_RE = re.compile(r"^\s*\*\*URL:\*\*\s*(?P<url>\S.*?)\s*$", re.IGNORECASE)
_ISSUED_LINE_RE = re.compile(r"^\s*\*\*Issued:\*\*\s*(?P<date>\S.*?)\s*$", re.IGNORECASE)
_DECIDED_LINE_RE = re.compile(r"^\s*\*\*Decided:\*\*\s*(?P<date>\S.*?)\s*$", re.IGNORECASE)
_SOURCE_LINE_RE = re.compile(r"^\s*\*\*Source:\*\*\s*(?P<src>.+?)\s*$", re.IGNORECASE)


def parse_sections(path: Path) -> list[Section]:
    """Walk a brief markdown file and yield H1/H2 sections.

    H3+ headings are kept inside the body of the enclosing H1/H2 (legal text
    sometimes contains them). Front-matter (lines before any heading) is
    discarded.
    """

    sections: list[Section] = []
    current: Section | None = None
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            m = _HEADING_RE.match(line)
            if m and len(m.group("hashes")) <= 2:
                # close out current
                if current is not None:
                    sections.append(current)
                current = Section(level=len(m.group("hashes")), heading=m.group("text").strip())
                continue
            if current is None:
                continue
            current.body_lines.append(line.rstrip("\n"))
    if current is not None:
        sections.append(current)
    return sections


def section_metadata(section: Section) -> tuple[str | None, str | None, str | None]:
    """Pull URL / Issued / Source out of the first metadata block."""

    url: str | None = None
    issued: str | None = None
    source: str | None = None
    for line in section.body_lines[:30]:
        if url is None:
            m = _URL_LINE_RE.match(line)
            if m:
                url = m.group("url").strip()
                continue
        if issued is None:
            m = _ISSUED_LINE_RE.match(line) or _DECIDED_LINE_RE.match(line)
            if m:
                issued = m.group("date").strip()
                continue
        if source is None:
            m = _SOURCE_LINE_RE.match(line)
            if m:
                source = m.group("src").strip()
                continue
    return url, issued, source


def section_body(section: Section, *, drop_meta_lines: bool = True) -> str:
    """Return the section body with meta lines (URL/Issued/Source) removed."""

    out: list[str] = []
    for line in section.body_lines:
        if drop_meta_lines and (
            _URL_LINE_RE.match(line)
            or _ISSUED_LINE_RE.match(line)
            or _DECIDED_LINE_RE.match(line)
            or _SOURCE_LINE_RE.match(line)
        ):
            continue
        out.append(line)
    text = "\n".join(out).strip()
    # Strip horizontal-rule separators that the briefs use between articles.
    text = re.sub(r"\n-{3,}\s*$", "", text)
    return text


# ---------------------------------------------------------------------------
# Per-brief handlers
# ---------------------------------------------------------------------------


@dataclass
class Row:
    norm_id: str
    norm_type: str
    article_key: str
    body: str
    source_url: str
    fecha_emision: str | None
    emisor: str
    tema: str


def _normalize_date(raw: str | None) -> str | None:
    if raw is None:
        return None
    raw = raw.strip()
    # YYYY-MM-DD already
    m = re.match(r"^(\d{4}-\d{2}-\d{2})$", raw)
    if m:
        return raw
    # YYYY-XX-XX (placeholder)
    if re.match(r"^\d{4}-XX-XX$", raw, re.IGNORECASE):
        return None
    return None


def _expand_year(raw: str) -> str:
    """Expand 2-digit year to 4-digit. 00–30 → 2000–2030; 31–99 → 1931–1999."""

    raw = raw.strip()
    if len(raw) == 4:
        return raw
    if len(raw) == 2:
        n = int(raw)
        return f"20{raw}" if n <= 30 else f"19{raw}"
    return raw


def _prepend_citation(body: str, citation: str) -> str:
    return f"[CITA: {citation}]\n\n{body}".strip()


def _is_canonical_article_num(num: str) -> bool:
    """canon allows only digits, dots and a single dash before suffix digits."""

    return bool(re.fullmatch(r"\d+(?:\.\d+)*(?:-\d+)?", num))


def _make_parent_row(
    *,
    norm_id: str,
    norm_type: str,
    label: str,
    citation: str,
    source_url: str,
    fecha_emision: str | None,
    emisor: str,
    tema: str,
) -> Row:
    """Emit a parent row so YAML batches with explicit_list of parent ids resolve.

    The body holds the parent label and a clean parent-level citation that
    `find_mentions()` will pick up as the bare parent norm_id (no article).
    """

    body = (
        f"[CITA: {citation}]\n\n"
        f"{label}\n\n"
        f"Documento normativo de referencia. El cuerpo articulado se encuentra "
        f"en las filas hijas con id `{norm_id}.art.<N>` (o equivalente)."
    )
    return Row(
        norm_id=norm_id,
        norm_type=norm_type,
        article_key=label,
        body=body,
        source_url=source_url,
        fecha_emision=fecha_emision,
        emisor=emisor,
        tema=tema,
    )


# Brief 01 — CST -------------------------------------------------------------


def handle_brief_01(sections: list[Section]) -> tuple[list[Row], list[Issue]]:
    rows: list[Row] = []
    issues: list[Issue] = []
    fallback_url = "https://www.suin-juriscol.gov.co/viewDocument.asp?ruta=Codigo/30019323"
    for sec in sections:
        if sec.level != 2:
            continue
        m = _ART_HEADER_RE.match(sec.heading)
        if not m:
            continue
        num = m.group("num")
        if not _is_canonical_article_num(num):
            issues.append(Issue(sec.heading, f"non-canonical article num: {num!r}"))
            continue
        url, issued, _ = section_metadata(sec)
        body = section_body(sec)
        if not body:
            issues.append(Issue(sec.heading, "empty body"))
            continue
        norm_id = f"cst.art.{num}"
        citation = f"Artículo {num} del Código Sustantivo del Trabajo (CST)"
        rows.append(
            Row(
                norm_id=norm_id,
                norm_type="cst_articulo",
                article_key=f"Art. {num} CST",
                body=_prepend_citation(body, citation),
                source_url=url or fallback_url,
                fecha_emision=_normalize_date(issued) or "1950-08-05",
                emisor="Congreso (CST — Decreto-Ley 2663/1950, adoptado por Ley 141/1961)",
                tema="cst_laboral",
            )
        )
    return rows, issues


# Brief 02-04 — DUR 1625/2016 -----------------------------------------------


def handle_brief_dur(
    sections: list[Section],
    *,
    decreto_num: str,
    year: str,
    fecha_emision: str,
    fallback_url: str,
    tema: str,
) -> tuple[list[Row], list[Issue]]:
    rows: list[Row] = []
    issues: list[Issue] = []
    parent_id = f"decreto.{decreto_num}.{year}"
    rows.append(
        _make_parent_row(
            norm_id=parent_id,
            norm_type="decreto",
            label=f"Decreto Único Reglamentario {decreto_num} de {year}",
            citation=f"Decreto {decreto_num} de {year}",
            source_url=fallback_url,
            fecha_emision=fecha_emision,
            emisor="Presidencia / DIAN" if decreto_num == "1625" else "Presidencia / MinTrabajo",
            tema=tema,
        )
    )
    for sec in sections:
        if sec.level != 2:
            continue
        # Match either "Artículo 1.2.3" or bare "1.2.3".
        m = _ART_HEADER_RE.match(sec.heading) or _BARE_DOTTED_RE.match(sec.heading)
        if not m:
            continue
        num = m.group("num")
        if not _is_canonical_article_num(num):
            issues.append(Issue(sec.heading, f"non-canonical article num: {num!r}"))
            continue
        url, issued, _ = section_metadata(sec)
        body = section_body(sec)
        if not body:
            issues.append(Issue(sec.heading, "empty body"))
            continue
        norm_id = f"decreto.{decreto_num}.{year}.art.{num}"
        citation = f"Decreto {decreto_num} de {year}, Artículo {num}"
        rows.append(
            Row(
                norm_id=norm_id,
                norm_type="decreto_articulo",
                article_key=f"Art. {num} Decreto {decreto_num}/{year}",
                body=_prepend_citation(body, citation),
                source_url=url or fallback_url,
                fecha_emision=_normalize_date(issued) or fecha_emision,
                emisor="Presidencia / DIAN" if decreto_num == "1625" else "Presidencia / MinTrabajo",
                tema=tema,
            )
        )
    return rows, issues


# Brief 06 — Decretos legislativos COVID -------------------------------------


def handle_brief_06(sections: list[Section]) -> tuple[list[Row], list[Issue]]:
    rows: list[Row] = []
    issues: list[Issue] = []
    parent: ParentContext | None = None
    parents_emitted: set[str] = set()
    for sec in sections:
        if sec.level == 1:
            m = _PARENT_DECRETO_RE.match(sec.heading)
            if m:
                _, src_url, _ = section_metadata(sec)
                _, issued, source_line = section_metadata(sec)
                parent = ParentContext(
                    family="decreto",
                    num=m.group("num"),
                    year=m.group("year"),
                    label=sec.heading.strip(),
                    fecha_emision=_normalize_date(issued),
                    source_url=_url_from_source_line(source_line),
                )
                parent_id = f"decreto.{parent.num}.{parent.year}"
                if parent_id not in parents_emitted:
                    rows.append(
                        _make_parent_row(
                            norm_id=parent_id,
                            norm_type="decreto",
                            label=parent.label,
                            citation=f"Decreto {parent.num} de {parent.year}",
                            source_url=parent.source_url
                            or f"https://normograma.dian.gov.co/dian/compilacion/docs/decreto_legislativo_{parent.num}_{parent.year}.htm",
                            fecha_emision=parent.fecha_emision or f"{parent.year}-01-01",
                            emisor="Presidencia (Decreto Legislativo, emergencia económica)",
                            tema="decreto_legislativo_covid",
                        )
                    )
                    parents_emitted.add(parent_id)
                continue
            parent = None
            continue
        if sec.level != 2 or parent is None:
            continue
        m = _ART_HEADER_RE.match(sec.heading)
        if not m:
            continue
        num = m.group("num")
        if not _is_canonical_article_num(num):
            issues.append(Issue(sec.heading, f"non-canonical article num: {num!r}"))
            continue
        url, issued, _ = section_metadata(sec)
        body = section_body(sec)
        if not body:
            issues.append(Issue(sec.heading, "empty body"))
            continue
        norm_id = f"decreto.{parent.num}.{parent.year}.art.{num}"
        # Use plain "Decreto NNN de YYYY" — find_mentions trips over "Decreto Legislativo".
        citation = f"Decreto {parent.num} de {parent.year}, Artículo {num}"
        rows.append(
            Row(
                norm_id=norm_id,
                norm_type="decreto_articulo",
                article_key=f"Art. {num} Decreto Legislativo {parent.num}/{parent.year}",
                body=_prepend_citation(body, citation),
                source_url=url or parent.source_url or "",
                fecha_emision=_normalize_date(issued) or parent.fecha_emision or f"{parent.year}-01-01",
                emisor="Presidencia (Decreto Legislativo, emergencia económica)",
                tema="decreto_legislativo_covid",
            )
        )
    return rows, issues


# Brief 07 — Resoluciones DIAN ----------------------------------------------


def handle_brief_07(sections: list[Section]) -> tuple[list[Row], list[Issue]]:
    rows: list[Row] = []
    issues: list[Issue] = []
    parent: ParentContext | None = None
    parents_emitted: set[str] = set()
    for sec in sections:
        if sec.level == 1:
            m = _PARENT_RES_DIAN_RE.match(sec.heading)
            if m:
                _, issued, source_line = section_metadata(sec)
                parent = ParentContext(
                    family="res_dian",
                    num=m.group("num"),
                    year=m.group("year"),
                    label=sec.heading.strip(),
                    fecha_emision=_normalize_date(issued),
                    source_url=_url_from_source_line(source_line),
                )
                parent_id = f"res.dian.{parent.num}.{parent.year}"
                if parent_id not in parents_emitted:
                    rows.append(
                        _make_parent_row(
                            norm_id=parent_id,
                            norm_type="resolucion",
                            label=parent.label,
                            citation=f"Resolución DIAN {parent.num} de {parent.year}",
                            source_url=parent.source_url
                            or f"https://normograma.dian.gov.co/dian/compilacion/docs/resolucion_dian_{parent.num.zfill(4)}_{parent.year}.htm",
                            fecha_emision=parent.fecha_emision,
                            emisor="DIAN",
                            tema=_classify_res_dian_tema(parent.label),
                        )
                    )
                    parents_emitted.add(parent_id)
                continue
            parent = None
            continue
        if sec.level != 2 or parent is None:
            continue
        m = _ART_HEADER_RE.match(sec.heading)
        if not m:
            continue
        num = m.group("num")
        if not _is_canonical_article_num(num):
            issues.append(Issue(sec.heading, f"non-canonical article num: {num!r}"))
            continue
        url, issued, _ = section_metadata(sec)
        body = section_body(sec)
        if not body:
            issues.append(Issue(sec.heading, "empty body"))
            continue
        norm_id = f"res.dian.{parent.num}.{parent.year}.art.{num}"
        citation = f"Resolución DIAN {parent.num} de {parent.year}, Artículo {num}"
        rows.append(
            Row(
                norm_id=norm_id,
                norm_type="res_articulo",
                article_key=f"Art. {num} Res. DIAN {parent.num}/{parent.year}",
                body=_prepend_citation(body, citation),
                source_url=url or parent.source_url or "",
                fecha_emision=_normalize_date(issued) or parent.fecha_emision,
                emisor="DIAN",
                tema=_classify_res_dian_tema(parent.label),
            )
        )
    return rows, issues


def _classify_res_dian_tema(label: str) -> str:
    text = label.lower()
    if "factura" in text:
        return "factura_electronica"
    if "n[oó]mina" in text or "nomina" in text:
        return "nomina_electronica"
    if "uvt" in text or "calendario" in text or "plazos" in text:
        return "uvt_calendario"
    if "simple" in text:
        return "regimen_simple"
    if "rut" in text or "exógena" in text or "exogena" in text:
        return "rut_exogena"
    return "resolucion_dian"


# Brief 08 — Conceptos DIAN unificados --------------------------------------


def handle_brief_08(sections: list[Section]) -> tuple[list[Row], list[Issue]]:
    rows: list[Row] = []
    issues: list[Issue] = []
    parent: ParentContext | None = None
    parents_emitted: set[str] = set()
    seq_within_parent = 0
    for sec in sections:
        if sec.level == 1:
            m = _PARENT_CONCEPTO_UNIF_RE.match(sec.heading)
            if m:
                _, issued, source_line = section_metadata(sec)
                num = m.group("num")
                year = m.group("year")
                parent = ParentContext(
                    family="concepto_unif",
                    num=num,
                    year=year,
                    label=sec.heading.strip(),
                    fecha_emision=_normalize_date(issued) or (f"{year}-01-01" if year else None),
                    source_url=_url_from_source_line(source_line),
                )
                seq_within_parent = 0
                parent_id = f"concepto.dian.{num}-{year}"
                if parent_id not in parents_emitted:
                    rows.append(
                        _make_parent_row(
                            norm_id=parent_id,
                            norm_type="concepto_dian",
                            label=parent.label,
                            citation=f"Concepto DIAN {num}-{year}",
                            source_url=parent.source_url
                            or f"https://normograma.dian.gov.co/dian/compilacion/docs/concepto_tributario_dian_{num.zfill(7)}_{year}.htm",
                            fecha_emision=parent.fecha_emision,
                            emisor="DIAN",
                            tema=_classify_concepto_unif_tema(parent.label),
                        )
                    )
                    parents_emitted.add(parent_id)
                continue
            parent = None
            continue
        if sec.level != 2 or parent is None:
            continue
        m = _NUMERAL_HEADER_RE.match(sec.heading)
        if not m:
            continue
        raw_num = m.group("num")
        seq_within_parent += 1
        # canon's `concepto.dian.<NUM>.num.<X>` only allows integer X; we use a
        # monotonic sequence and store the source anchor in article_key/body.
        seq = str(seq_within_parent)
        url, issued, _ = section_metadata(sec)
        body = section_body(sec)
        if not body:
            issues.append(Issue(sec.heading, "empty body"))
            continue
        # Combine NUM-YEAR via the canon-supported NUM-SUFFIX form so the
        # parent disambiguates across years (e.g. concepto.dian.0001-2003).
        parent_id = f"concepto.dian.{parent.num}-{parent.year}"
        norm_id = f"{parent_id}.num.{seq}"
        citation = f"Concepto DIAN {parent.num}-{parent.year}, Numeral {seq}"
        rows.append(
            Row(
                norm_id=norm_id,
                norm_type="concepto_dian_numeral",
                article_key=f"Numeral {raw_num} — {parent.label}",
                body=_prepend_citation(body, citation),
                source_url=url or parent.source_url or "",
                fecha_emision=_normalize_date(issued) or parent.fecha_emision,
                emisor="DIAN",
                tema=_classify_concepto_unif_tema(parent.label),
            )
        )
    return rows, issues


def _classify_concepto_unif_tema(label: str) -> str:
    text = label.lower()
    if "iva" in text:
        return "concepto_unificado_iva"
    if "renta" in text:
        return "concepto_unificado_renta"
    if "retenci" in text or "retefuente" in text:
        return "concepto_unificado_retencion"
    if "procedimiento" in text or "sanciones" in text:
        return "concepto_unificado_procedimiento"
    if "simple" in text:
        return "concepto_unificado_simple"
    return "concepto_unificado"


# Brief 09 — Conceptos individuales + Oficios DIAN --------------------------


def handle_brief_09(sections: list[Section]) -> tuple[list[Row], list[Issue]]:
    rows: list[Row] = []
    issues: list[Issue] = []
    current_topic = "individual"  # "oficio" | "concepto_trib" | "concepto_aduana" | "concepto_camb"
    for sec in sections:
        if sec.level == 1:
            heading = sec.heading.lower()
            if "oficio" in heading:
                current_topic = "oficio"
            elif "tributari" in heading:
                current_topic = "concepto_trib"
            elif "aduaner" in heading:
                current_topic = "concepto_aduana"
            elif "cambiari" in heading:
                current_topic = "concepto_camb"
            continue
        if sec.level != 2:
            continue
        url, issued, _ = section_metadata(sec)
        body = section_body(sec)
        if not body:
            issues.append(Issue(sec.heading, "empty body"))
            continue
        m_of = _OFICIO_HEADER_RE.match(sec.heading)
        if m_of:
            num = m_of.group("num")
            year = m_of.group("year")
            padded = num.zfill(4) if len(num) <= 4 else num
            norm_id = f"oficio.dian.{padded}.{year}"
            citation = f"Oficio DIAN {padded} de {year}"
            rows.append(
                Row(
                    norm_id=norm_id,
                    norm_type="oficio_dian",
                    article_key=f"Oficio DIAN {num} de {year}",
                    body=_prepend_citation(body, citation),
                    source_url=url or "",
                    fecha_emision=_normalize_date(issued) or f"{year}-01-01",
                    emisor="DIAN",
                    tema=_classify_oficio_tema(body),
                )
            )
            continue
        m_co = _CONCEPTO_INDIV_HEADER_RE.match(sec.heading)
        if m_co:
            num = m_co.group("num")
            year = m_co.group("year")
            # Individual conceptos use the no-year canonical form per spec.
            norm_id = f"concepto.dian.{num}"
            citation = f"Concepto DIAN {num}"
            rows.append(
                Row(
                    norm_id=norm_id,
                    norm_type="concepto_dian",
                    article_key=f"Concepto DIAN {num}" + (f" de {year}" if year else ""),
                    body=_prepend_citation(body, citation),
                    source_url=url or "",
                    fecha_emision=_normalize_date(issued)
                    or (f"{year}-01-01" if year else None),
                    emisor="DIAN",
                    tema=_classify_concepto_indiv_tema(current_topic, body),
                )
            )
            continue
        # Some oficios in brief 09 may use other forms — log & skip.
        issues.append(Issue(sec.heading, "unrecognized brief-09 article header"))
    return rows, issues


def _classify_oficio_tema(body: str) -> str:
    text = body.lower()
    if "iva" in text:
        return "oficio_iva"
    if "retenci" in text:
        return "oficio_retencion"
    if "renta" in text:
        return "oficio_renta"
    if "simple" in text:
        return "oficio_regimen_simple"
    if "aduaner" in text or "arancel" in text:
        return "oficio_aduanero"
    if "cambiari" in text:
        return "oficio_cambiario"
    return "oficio_dian"


def _classify_concepto_indiv_tema(topic: str, body: str) -> str:
    if topic == "concepto_aduana":
        return "concepto_aduanero"
    if topic == "concepto_camb":
        return "concepto_cambiario"
    if topic == "concepto_trib":
        return "concepto_tributario"
    return _classify_oficio_tema(body)


# Brief 10 — Jurisprudencia CC + CE -----------------------------------------


def handle_brief_10(sections: list[Section]) -> tuple[list[Row], list[Issue]]:
    rows: list[Row] = []
    issues: list[Issue] = []
    for sec in sections:
        if sec.level != 2:
            continue
        m = _SENTENCIA_HEADER_RE.match(sec.heading)
        if not m:
            continue
        type_ = m.group("type").upper()
        num = m.group("num")
        year_raw = m.group("year")
        year = _expand_year(year_raw)
        url, issued, _ = section_metadata(sec)
        body = section_body(sec)
        if not body:
            issues.append(Issue(sec.heading, "empty body"))
            continue
        norm_id = f"sent.cc.{type_}-{num}.{year}"
        citation = f"Sentencia {type_}-{num} de {year}"
        rows.append(
            Row(
                norm_id=norm_id,
                norm_type="sentencia_cc",
                article_key=f"Sentencia {type_}-{num}/{year}",
                body=_prepend_citation(body, citation),
                source_url=url or f"https://www.corteconstitucional.gov.co/relatoria/{year}/{type_}-{num}-{year[-2:]}.htm",
                fecha_emision=_normalize_date(issued) or (f"{year}-01-01" if year else None),
                emisor="Corte Constitucional",
                tema="jurisprudencia_cc_principios",
            )
        )
    return rows, issues


# Brief 11 — Pensional / Salud / Parafiscales (Ley) -------------------------


def handle_brief_11(sections: list[Section]) -> tuple[list[Row], list[Issue]]:
    rows: list[Row] = []
    issues: list[Issue] = []
    parent: ParentContext | None = None
    parents_emitted: set[str] = set()
    for sec in sections:
        # Brief 11 mixes H1 and H2 for parents.
        if sec.level <= 2:
            m = _PARENT_LEY_RE.match(sec.heading)
            if m and not _PARENT_FETCH_FAILED_RE.search(
                "\n".join(sec.body_lines[:30])
            ):
                # New parent. Skip placeholder sections that explicitly say
                # [FETCH FAILED] (the actual content lives further down).
                _, issued, source_line = section_metadata(sec)
                parent = ParentContext(
                    family="ley",
                    num=m.group("num"),
                    year=m.group("year"),
                    label=sec.heading.strip(),
                    fecha_emision=_normalize_date(issued),
                    source_url=_url_from_source_line(source_line),
                )
                parent_id = f"ley.{parent.num}.{parent.year}"
                if parent_id not in parents_emitted:
                    rows.append(
                        _make_parent_row(
                            norm_id=parent_id,
                            norm_type="ley",
                            label=parent.label,
                            citation=f"Ley {parent.num} de {parent.year}",
                            source_url=parent.source_url
                            or f"https://normograma.dian.gov.co/dian/compilacion/docs/ley_{parent.num.zfill(4)}_{parent.year}.htm",
                            fecha_emision=parent.fecha_emision,
                            emisor="Congreso",
                            tema=_classify_ley_pensional_tema(parent.num, parent.label),
                        )
                    )
                    parents_emitted.add(parent_id)
                continue
            elif m and _PARENT_FETCH_FAILED_RE.search("\n".join(sec.body_lines[:30])):
                # placeholder — keep current parent
                continue
        if sec.level != 2 or parent is None:
            continue
        m = _ART_HEADER_RE.match(sec.heading)
        if not m:
            continue
        # extract pure number, dropping ordinal "o" etc.
        num = m.group("num")
        if not _is_canonical_article_num(num):
            issues.append(Issue(sec.heading, f"non-canonical article num: {num!r}"))
            continue
        url, issued, _ = section_metadata(sec)
        body = section_body(sec)
        if not body:
            issues.append(Issue(sec.heading, "empty body"))
            continue
        norm_id = f"ley.{parent.num}.{parent.year}.art.{num}"
        citation = f"Ley {parent.num} de {parent.year}, Artículo {num}"
        rows.append(
            Row(
                norm_id=norm_id,
                norm_type="ley_articulo",
                article_key=f"Art. {num} Ley {parent.num}/{parent.year}",
                body=_prepend_citation(body, citation),
                source_url=url or parent.source_url or "",
                fecha_emision=_normalize_date(issued) or parent.fecha_emision,
                emisor="Congreso",
                tema=_classify_ley_pensional_tema(parent.num, parent.label),
            )
        )
    return rows, issues


def _classify_ley_pensional_tema(num: str, label: str) -> str:
    if num == "100":
        return "pensional_salud"
    if num == "789":
        return "parafiscales_empleo"
    if num == "2381":
        return "reforma_pensional"
    return "labor_pensional"


# Brief 12 — Cambiario + Societario -----------------------------------------


def handle_brief_12(sections: list[Section]) -> tuple[list[Row], list[Issue]]:
    rows: list[Row] = []
    issues: list[Issue] = []
    parent: ParentContext | None = None
    parents_emitted: set[str] = set()
    for sec in sections:
        if sec.level == 1:
            m_cco = _PARENT_CCO_RE.match(sec.heading)
            if m_cco:
                _, issued, source_line = section_metadata(sec)
                parent = ParentContext(
                    family="cco",
                    label=sec.heading.strip(),
                    fecha_emision=_normalize_date(issued) or "1971-03-27",
                    source_url=_url_from_source_line(source_line),
                )
                # CCo has no parent norm_id in canon (only `cco.art.<N>`).
                continue
            m_ley = _PARENT_LEY_RE.match(sec.heading)
            if m_ley:
                _, issued, source_line = section_metadata(sec)
                parent = ParentContext(
                    family="ley",
                    num=m_ley.group("num"),
                    year=m_ley.group("year"),
                    label=sec.heading.strip(),
                    fecha_emision=_normalize_date(issued),
                    source_url=_url_from_source_line(source_line),
                )
                parent_id = f"ley.{parent.num}.{parent.year}"
                if parent_id not in parents_emitted:
                    rows.append(
                        _make_parent_row(
                            norm_id=parent_id,
                            norm_type="ley",
                            label=parent.label,
                            citation=f"Ley {parent.num} de {parent.year}",
                            source_url=parent.source_url
                            or f"https://normograma.dian.gov.co/dian/compilacion/docs/ley_{parent.num.zfill(4)}_{parent.year}.htm",
                            fecha_emision=parent.fecha_emision,
                            emisor="Congreso",
                            tema="sociedades_comerciales",
                        )
                    )
                    parents_emitted.add(parent_id)
                continue
            parent = None
            continue
        if sec.level != 2 or parent is None:
            continue
        m = _ART_HEADER_RE.match(sec.heading)
        if not m:
            continue
        num = m.group("num")
        if not _is_canonical_article_num(num):
            issues.append(Issue(sec.heading, f"non-canonical article num: {num!r}"))
            continue
        url, issued, _ = section_metadata(sec)
        body = section_body(sec)
        if not body:
            issues.append(Issue(sec.heading, "empty body"))
            continue
        if parent.family == "cco":
            norm_id = f"cco.art.{num}"
            citation = f"Artículo {num} del Código de Comercio (CCo)"
            rows.append(
                Row(
                    norm_id=norm_id,
                    norm_type="cco_articulo",
                    article_key=f"Art. {num} CCo",
                    body=_prepend_citation(body, citation),
                    source_url=url or parent.source_url or "",
                    fecha_emision=_normalize_date(issued) or parent.fecha_emision,
                    emisor="Congreso (CCo — Decreto 410/1971)",
                    tema=DEFAULT_CCO_TEMA,
                )
            )
        else:
            norm_id = f"ley.{parent.num}.{parent.year}.art.{num}"
            citation = f"Ley {parent.num} de {parent.year}, Artículo {num}"
            rows.append(
                Row(
                    norm_id=norm_id,
                    norm_type="ley_articulo",
                    article_key=f"Art. {num} Ley {parent.num}/{parent.year}",
                    body=_prepend_citation(body, citation),
                    source_url=url or parent.source_url or "",
                    fecha_emision=_normalize_date(issued) or parent.fecha_emision,
                    emisor="Congreso",
                    tema="sociedades_comerciales",
                )
            )
    return rows, issues


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _url_from_source_line(line: str | None) -> str | None:
    if not line:
        return None
    # source line shape: "<text> — http(s)://..."
    m = re.search(r"https?://\S+", line)
    return m.group(0) if m else None


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------


def route_brief(brief_num: int, sections: list[Section]) -> tuple[list[Row], list[Issue]]:
    if brief_num == 1:
        return handle_brief_01(sections)
    if brief_num == 2:
        return handle_brief_dur(
            sections,
            decreto_num="1625",
            year="2016",
            fecha_emision="2016-08-02",
            fallback_url="https://normograma.dian.gov.co/dian/compilacion/docs/decreto_1625_2016.htm",
            tema="dur_1625_renta",
        )
    if brief_num == 3:
        return handle_brief_dur(
            sections,
            decreto_num="1625",
            year="2016",
            fecha_emision="2016-08-02",
            fallback_url="https://normograma.dian.gov.co/dian/compilacion/docs/decreto_1625_2016.htm",
            tema="dur_1625_iva_retefuente",
        )
    if brief_num == 4:
        return handle_brief_dur(
            sections,
            decreto_num="1625",
            year="2016",
            fecha_emision="2016-08-02",
            fallback_url="https://normograma.dian.gov.co/dian/compilacion/docs/decreto_1625_2016.htm",
            tema="dur_1625_procedimiento",
        )
    if brief_num == 5:
        return handle_brief_dur(
            sections,
            decreto_num="1072",
            year="2015",
            fecha_emision="2015-05-26",
            fallback_url="https://www.suin-juriscol.gov.co/viewDocument.asp?id=30019522",
            tema="dur_1072_laboral_sst",
        )
    if brief_num == 6:
        return handle_brief_06(sections)
    if brief_num == 7:
        return handle_brief_07(sections)
    if brief_num == 8:
        return handle_brief_08(sections)
    if brief_num == 9:
        return handle_brief_09(sections)
    if brief_num == 10:
        return handle_brief_10(sections)
    if brief_num == 11:
        return handle_brief_11(sections)
    if brief_num == 12:
        return handle_brief_12(sections)
    raise ValueError(f"unknown brief number: {brief_num}")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_rows(rows: list[Row]) -> tuple[list[Issue], set[str]]:
    """Validate each row's norm_id + source_url.

    Returns (issues, hard_rejected_ids). Duplicate-norm rows are flagged in
    issues but the *first* occurrence remains valid; only `hard_rejected_ids`
    (non-canonical or missing source_url) are dropped wholesale.
    """

    from lia_graph.canon import canonicalize

    issues: list[Issue] = []
    hard_rejected: set[str] = set()
    seen: set[str] = set()
    for row in rows:
        if not row.source_url:
            issues.append(Issue(row.norm_id, "missing source_url"))
            hard_rejected.add(row.norm_id)
            continue
        canonical = canonicalize(row.norm_id)
        if canonical != row.norm_id:
            issues.append(
                Issue(row.norm_id, f"non-canonical: canonicalize() → {canonical!r}")
            )
            hard_rejected.add(row.norm_id)
            continue
        if row.norm_id in seen:
            issues.append(Issue(row.norm_id, "duplicate norm_id within packet"))
            continue
        seen.add(row.norm_id)
    return issues, hard_rejected


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--brief-num", type=int, required=True, help="Brief number 1-12")
    parser.add_argument("--packet", required=True, help="Path to expert-delivered .md packet")
    parser.add_argument("--output", required=True, help="Path to write staging JSONL")
    parser.add_argument("--issues-output", default=None, help="Path to write parse issues")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--limit", type=int, default=None, help="Cap rows for smoke tests")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    packet = Path(args.packet)
    if not packet.is_file():
        LOGGER.error("packet not found: %s", packet)
        return 2

    sections = parse_sections(packet)
    LOGGER.info("parsed %d top-level sections from %s", len(sections), packet.name)

    rows, parse_issues = route_brief(args.brief_num, sections)
    LOGGER.info("routed brief %d → %d candidate rows (%d parse issues)", args.brief_num, len(rows), len(parse_issues))
    if args.limit is not None:
        rows = rows[: args.limit]

    validation_issues, hard_rejected = validate_rows(rows)
    LOGGER.info("validation: %d issues (%d hard-rejected ids)", len(validation_issues), len(hard_rejected))

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    written_ids: set[str] = set()
    with out_path.open("w", encoding="utf-8") as fh:
        for row in rows:
            if row.norm_id in hard_rejected:
                continue
            if row.norm_id in written_ids:
                # later duplicate of an already-written id
                continue
            written_ids.add(row.norm_id)
            payload = {
                "norm_id": row.norm_id,
                "norm_type": row.norm_type,
                "article_key": row.article_key,
                "body": row.body,
                "source_url": row.source_url,
                "fecha_emision": row.fecha_emision,
                "emisor": row.emisor,
                "tema": row.tema,
            }
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
            written += 1

    LOGGER.info("wrote %d valid rows to %s", written, out_path)
    if parse_issues or validation_issues:
        issues_path = Path(args.issues_output) if args.issues_output else out_path.with_suffix(".issues.txt")
        issues_path.parent.mkdir(parents=True, exist_ok=True)
        with issues_path.open("w", encoding="utf-8") as fh:
            for issue in parse_issues:
                fh.write(f"PARSE\t{issue.section_heading}\t{issue.reason}\n")
            for issue in validation_issues:
                fh.write(f"VALIDATE\t{issue.section_heading}\t{issue.reason}\n")
        LOGGER.info("wrote %d issues to %s", len(parse_issues) + len(validation_issues), issues_path)

    LOGGER.info(
        "summary: brief=%s rows_in=%d rows_out=%d parse_issues=%d validation_issues=%d",
        args.brief_num,
        len(rows),
        written,
        len(parse_issues),
        len(validation_issues),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
