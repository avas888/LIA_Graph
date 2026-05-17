"""v19 Fase 2/3 — single source of truth for `(source_path, article_number) → norm_id`.

Used by:
- `scripts/migrate_falkor_norm_ids.py` — one-shot migration of the 9,331
  existing :ArticleNodes (Fase 2, applied 2026-05-15).
- `lia_graph.ingestion.loader._build_article_nodes` — emits `norm_id` on
  every new ArticleNode at ingest time so future re-ingests never collide
  on bare article numbers (Fase 3).

Why a separate module: the rules drive a property that downstream
consumers (planner, retriever_falkor, citation allowlist) match against.
The migration script and the loader must agree, byte-for-byte, on the
derived `norm_id` — co-locating the table here eliminates drift.

Per v19 scope doc §2.0.5 Gate 1: Falkor-only. Supabase `chunk_id`
remains `<doc_id>::<article_key>` (anchor-keyed) — embeddings preserved.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


# ---------------------------------------------------------------------------
# Path-rule table — (source_path, article_number) → free-text mention.
#
# Priority-ordered. First match wins. Each rule returns either:
#   - a free-text mention (e.g. "art. 64 CST") for `canon.canonicalize()`
#   - the SKIP sentinel (rule matched but defers canonicalization)
#   - None (no match, fall through to next rule)
#
# Adding a new rule: prepend it (lower index in _RULES) and add a
# matching unit-test row in tests/test_norm_id_migration.py.
# ---------------------------------------------------------------------------

# Sentinel mention prefix — a rule returns this to signal "match but skip,
# no norm_id, but NOT OTHER either". Caught by `derive_norm_id` before the
# canonicalize() call.
SKIP_SENTINEL = "__SKIP__:"


# Filename-embedded Ley NUMBER YEAR — matches `Ley-2466-2025.md`,
# `Ley-50-1990.md`, `Ley_789_2002.md`, `Ley_599_2000_CodigoPenal.md`, etc.
# Lookahead instead of `\b` after year because `_` (common in filenames) is
# a word char — `\b2000_CodigoPenal` fails to match, lookahead succeeds.
_LEY_FILENAME_RE = re.compile(
    r"(?i)\bley[\s_\-]+(?P<num>\d+(?:-\d+)?)[\s_\-]+(?P<year>\d{4})(?=[\s_\-\.]|$)"
)

# Filename-embedded Decreto NUMBER YEAR.
_DECRETO_FILENAME_PATTERNS = (
    re.compile(r"(?i)\b(?:decreto|dec)[\s_\-]+(?P<num>\d+)[\s_\-]+(?P<year>\d{4})\b"),
    re.compile(r"(?i)\bDT[\s_\-]+(?P<num>\d+)[\s_\-]+(?P<year>\d{4})\b"),
    re.compile(r"(?i)\bD(?P<num>\d{3,4})[\s_\-]+(?P<year>\d{4})\b"),
)

# Filename mentions decreto NUMBER but no YEAR (year lives in parent folder).
_DECRETO_NUMBER_ONLY_RE = re.compile(
    r"(?i)\b(?:decreto|dec|D)[\s_\-]+(?P<num>\d{3,4})\b"
)
_YEAR_IN_PATH_RE = re.compile(r"\b(?P<year>(?:19|20)\d{2})\b")

_RESOLUCION_FILENAME_RE = re.compile(
    r"(?i)\bresoluci[oó]n[\s_\-]+(?P<num>\d+)[\s_\-]+(?P<year>\d{4})\b"
)

_SENT_CC_FILENAME_RE = re.compile(
    r"(?i)\bsentencia[\s_\-]+(?P<letter>c|t|su|a)[\s_\-]*(?P<num>\d+)[\s_\-]+(?P<year>\d{4})\b"
)


def _filename_stem(source_path: str) -> str:
    return Path(source_path).name


@dataclass(frozen=True)
class Rule:
    name: str
    description: str
    fn: "callable[[str, str], str | None]"


@dataclass(frozen=True)
class DerivationOutcome:
    article_id: str
    article_number: str
    source_path: str
    norm_id: str | None
    rule_name: str
    mention: str | None
    refusal_reason: str | None


# ---------------------------------------------------------------------------
# Rule implementations
# ---------------------------------------------------------------------------


def _rule_suin_skipped(source_path: str, article_number: str) -> str | None:
    """SUIN nodes — v6 already canonicalized them in `public.norms` + `:Norm`."""
    if source_path.startswith("suin://") or "/SUIN/" in source_path:
        return f"{SKIP_SENTINEL}suin_external_canonical"
    return None


def _rule_cam_n01_ley_9_1991(source_path: str, article_number: str) -> str | None:
    """CAM-N01 marco-legal arts 1-5 → ley.9.1991.art.N (Estatuto Cambiario)."""
    if "CAM_DECLARACION_CAMBIO" not in source_path:
        return None
    if "CAM-N01" not in source_path:
        return None
    if article_number not in {"1", "2", "3", "4", "5"}:
        return None
    return f"Ley 9 de 1991 art. {article_number}"


def _rule_cst_consolidado(source_path: str, article_number: str) -> str | None:
    """Codigo_Sustantivo_Trabajo.md → cst.art.N."""
    sp = source_path.lower()
    if "codigo_sustantivo_trabajo" in sp or "código_sustantivo_trabajo" in sp:
        return f"art. {article_number} CST"
    return None


def _rule_reforma_laboral_2466(source_path: str, article_number: str) -> str | None:
    """REFORMA_LABORAL_LEY_2466 (hyphen or underscore) → ley.2466.2025.art.N."""
    sp = source_path
    if (
        "REFORMA_LABORAL_LEY_2466" in sp
        or "REFORMA-LABORAL-LEY-2466" in sp
        or "Ley_2466" in sp
        or "Ley-2466" in sp
        or "ley-2466" in sp
        or "ley_2466" in sp
    ):
        return f"Ley 2466 de 2025 art. {article_number}"
    return None


def _rule_sentencia_cc_filename(source_path: str, article_number: str) -> str | None:
    """`Sentencia-C-481-2019.md` → sent.cc.<L>-NUM.YEAR. Drops article_number."""
    stem = _filename_stem(source_path)
    m = _SENT_CC_FILENAME_RE.search(stem)
    if not m:
        return None
    return f"Sentencia {m.group('letter')}-{m.group('num')} de {m.group('year')}"


def _rule_resolucion_filename(source_path: str, article_number: str) -> str | None:
    """`Resolucion-NUM-YEAR.md` → res.dian.NUM.YEAR.art.N (DIAN assumed)."""
    stem = _filename_stem(source_path)
    m = _RESOLUCION_FILENAME_RE.search(stem)
    if not m:
        return None
    return f"Resolución DIAN {m.group('num')} de {m.group('year')} art. {article_number}"


def _rule_decreto_filename(source_path: str, article_number: str) -> str | None:
    """`Decreto-NUM-YEAR` / `DT-NUM-YEAR` / `D<NNNN>-YEAR` → decreto.NUM.YEAR.art.N.

    Fallback: NUMBER-only in filename + 4-digit year somewhere in path.
    """
    stem = _filename_stem(source_path)
    for pat in _DECRETO_FILENAME_PATTERNS:
        m = pat.search(stem)
        if m:
            num = m.group("num").lstrip("0") or m.group("num")
            return f"Decreto {num} de {m.group('year')} art. {article_number}"
    num_match = _DECRETO_NUMBER_ONLY_RE.search(stem)
    if num_match:
        year_match = _YEAR_IN_PATH_RE.search(source_path)
        if year_match:
            num = num_match.group("num").lstrip("0") or num_match.group("num")
            return f"Decreto {num} de {year_match.group('year')} art. {article_number}"
    return None


def _rule_ley_filename(source_path: str, article_number: str) -> str | None:
    """`Ley-NUM-YEAR.md` → ley.NUM.YEAR.art.N."""
    stem = _filename_stem(source_path)
    m = _LEY_FILENAME_RE.search(stem)
    if not m:
        return None
    return f"Ley {m.group('num')} de {m.group('year')} art. {article_number}"


# `NC-NNNN-YYYY-...md` — Norma Contable filename convention used in
# `NORMATIVA_LEYES/NC-1314-2009-NORMATIVA.md` etc. Same target as
# `_rule_ley_filename` but with the `NC-` prefix instead of `Ley-`.
_NC_FILENAME_RE = re.compile(
    r"(?i)\bNC[\s_\-]+(?P<num>\d+)[\s_\-]+(?P<year>\d{4})(?=[\s_\-\.]|$)"
)


def _rule_nc_filename(source_path: str, article_number: str) -> str | None:
    """`NC-NUM-YEAR-...md` → ley.NUM.YEAR.art.N (Norma Contable filename alias)."""
    stem = _filename_stem(source_path)
    m = _NC_FILENAME_RE.search(stem)
    if not m:
        return None
    return f"Ley {m.group('num')} de {m.group('year')} art. {article_number}"


def _rule_emergencia_decreto_0240(source_path: str, article_number: str) -> str | None:
    """`Emergencia_Tributaria_Decreto_0240/Normativa_Base/eme_normativa_decreto_0240.md`
    → decreto.0240.2026.art.N. Filename embeds 0240 but no year (year lives in
    the doc body — Decreto 0240 de 2026 emergency tributary)."""
    if "Emergencia_Tributaria_Decreto_0240" not in source_path:
        return None
    if "eme_normativa_decreto_0240" not in source_path.lower():
        return None
    return f"Decreto 0240 de 2026 art. {article_number}"


# Régimen Cambiario expert-summary paths reference Ley 9 de 1991 (Estatuto
# Cambiario, 26 articles). Two specific expert-summary docs surface in the
# 2026-05-16 P1 OTHER bucket. Articles 1-26 are within the Ley 9/1991 range;
# higher numbers are parser artifacts from section headings and stay OTHER.
_LEY_9_1991_VALID_ARTS = {str(n) for n in range(1, 27)}


def _rule_regimen_cambiario_ley_9_1991(source_path: str, article_number: str) -> str | None:
    """Régimen Cambiario expert summaries → ley.9.1991.art.N (arts 1-26 only)."""
    cam_markers = (
        "/Regimen_Cambiario/Normativa_Base/cam_normativa_regimen_cambiario",
        "/REGIMEN_CAMBIARIO_PYME/NORMATIVA/N01-regimen-cambiario-pyme-marco-legal",
    )
    if not any(marker in source_path for marker in cam_markers):
        return None
    if article_number not in _LEY_9_1991_VALID_ARTS:
        return None
    return f"Ley 9 de 1991 art. {article_number}"


def _rule_revisoria_fiscal_cco(source_path: str, article_number: str) -> str | None:
    """Revisoría Fiscal expert summary references Codigo de Comercio arts
    203-217. Map article numbers in that range to cco.art.N; reject out-of-range
    numbers as parser artifacts."""
    if "/Revisoria_Fiscal/Normativa_Base/rev_normativa_revisoria_fiscal" not in source_path:
        return None
    try:
        n = int(article_number)
    except ValueError:
        return None
    if not (203 <= n <= 217):
        return None
    return f"art. {article_number} CCo"


def _rule_cco_filename(source_path: str, article_number: str) -> str | None:
    """Codigo_de_Comercio / codigo-de-comercio / /cco/ → cco.art.N."""
    sp = source_path.lower()
    cco_markers = (
        "codigo_de_comercio",
        "código_de_comercio",
        "codigo-de-comercio",
        "código-de-comercio",
        "/cco/",
    )
    if any(marker in sp for marker in cco_markers):
        return f"art. {article_number} CCo"
    return None


def _rule_et_explicit_filename(source_path: str, article_number: str) -> str | None:
    """Filename suffix `-ET.md` / `_ET.md` or `/et/` folder or `estatuto_tributario`."""
    sp = source_path.lower()
    if "-et.md" in sp or "_et.md" in sp or "/et/" in sp or "estatuto_tributario" in sp or "estatuto-tributario" in sp:
        return f"art. {article_number} ET"
    return None


# Known topic folders whose numbered articles are ET references (per the
# 2026-05-15 audit + the 2026-05-15 staging dry-run OTHER analysis).
_ET_FOLDER_MARKERS = (
    "/RENTA/",
    "/IVA_COMPLETO/",
    "/IVA_",
    "/Corpus de Contabilidad/",
    "/DEPRECIACION_FISCAL/",
    "/PERDIDAS_FISCALES_",
    "/RENTA_PRESUNTIVA_",
    "/DESCUENTOS_TRIBUTARIOS",
    "/RETENCION_FUENTE",
    "/FIRMEZA_DECLARACIONES",
    "/PROCEDIMIENTO_TRIBUTARIO",
    "/procedimiento_tributario/",
    "/DIVIDENDOS_UTILIDADES",
    "/Tributacion_Dividendos",
    "/BENEFICIARIO_FINAL_RUB",
    "/FE_OPERATIVA",
    "/REGIMEN_SIMPLE",
    "-RST-REGIMEN-SIMPLE-TRIBUTACION/",
    "/REGIMEN_SANCIONATORIO",
    "/CONTRATACION_ESTATAL",
    "/RUT_RESPONSABILIDADES",
    "/INFORMACION_EXOGENA",
    "/ECONOMIA_DIGITAL",
    "/IMPUESTO_PATRIMONIO",
    "/FACTURACION",
    "/ACTIVOS_EXTERIOR",
    "/ZOMAC",
    "/EMERGENCIA_TRIBUTARIA",
    "/OBLIGACIONES_PROFESIONALES_CONTADOR",
    "-OBLIGACIONES-PROFESIONALES-JCC/",
    "/NOMINA_ELECTRONICA",
    "/SOC_REFORMA_ESTATUTOS",
    "/OBLIGACIONES_SOCIETARIAS",
    "/Devoluciones_Saldos_Favor",
    "-DEVOLUCIONES-SALDOS-A-FAVOR/",
    "/Precios_Transferencia",
    "/DESCUENTOS_INVENTARIOS_NIIF",
)


def _rule_iva_normativa_default(source_path: str, article_number: str) -> str | None:
    """Topic NORMATIVA folder default → ET (when no explicit Ley/Decreto filename)."""
    if any(marker in source_path for marker in _ET_FOLDER_MARKERS):
        return f"art. {article_number} ET"
    return None


_RULES: tuple[Rule, ...] = (
    # Top priority: SUIN — v6's domain.
    Rule("suin_skipped", "suin:// paths — v6 canonicalized; v19 leaves alone", _rule_suin_skipped),
    # Doc-specific
    Rule("cam_n01_ley_9_1991", "CAM-N01-...marco-legal arts 1-5 → ley.9.1991.art.N", _rule_cam_n01_ley_9_1991),
    Rule("regimen_cambiario_ley_9_1991", "Regimen Cambiario expert summaries → ley.9.1991.art.N (arts 1-26)", _rule_regimen_cambiario_ley_9_1991),
    Rule("revisoria_fiscal_cco", "Revisoría Fiscal expert summary → cco.art.N (arts 203-217)", _rule_revisoria_fiscal_cco),
    Rule("emergencia_decreto_0240", "Emergencia_Tributaria_Decreto_0240 → decreto.0240.2026.art.N", _rule_emergencia_decreto_0240),
    Rule("cst_consolidado", "Codigo_Sustantivo_Trabajo.md → cst.art.N", _rule_cst_consolidado),
    Rule("reforma_laboral_2466", "REFORMA_LABORAL_LEY_2466 → ley.2466.2025.art.N", _rule_reforma_laboral_2466),
    Rule("sentencia_cc_filename", "Sentencia-C-NUM-YEAR.md → sent.cc.<L>-NUM.YEAR", _rule_sentencia_cc_filename),
    Rule("resolucion_filename", "Resolucion-NUM-YEAR.md → res.dian.NUM.YEAR.art.N", _rule_resolucion_filename),
    Rule("decreto_filename", "Decreto-NUM-YEAR.md / DT-NUM-YEAR / D<NNNN>-YEAR → decreto.NUM.YEAR.art.N", _rule_decreto_filename),
    Rule("ley_filename", "Ley-NUM-YEAR.md → ley.NUM.YEAR.art.N", _rule_ley_filename),
    Rule("nc_filename", "NC-NUM-YEAR-...md → ley.NUM.YEAR.art.N (Norma Contable alias)", _rule_nc_filename),
    Rule("cco_explicit", "Codigo_de_Comercio.md / /cco/ → cco.art.N", _rule_cco_filename),
    Rule("et_explicit_filename", "filename / folder names ET explicitly", _rule_et_explicit_filename),
    Rule("et_topic_folder_default", "topic NORMATIVA folder default → ET", _rule_iva_normativa_default),
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _is_already_canonical(s: str) -> bool:
    """Bypass canonicalize() if input is already a canonical norm_id."""
    from lia_graph.canon import is_valid_norm_id

    return is_valid_norm_id(s)


def derive_norm_id(
    *,
    article_id: str,
    article_number: str,
    source_path: str,
) -> DerivationOutcome:
    """Single source of truth for (source_path, article_number) → norm_id.

    Returns a `DerivationOutcome` with:
      - `norm_id`: the canonical dotted id, or None if prose-only / OTHER / skipped.
      - `rule_name`: which rule matched ("prose_only" / "idempotent" /
        "suin_skipped" / "cst_consolidado" / ... / "OTHER").
      - `mention`: the free-text passed to canonicalize() (None for skips).
      - `refusal_reason`: filled when canonicalize() refused or no rule matched.

    Stable contract — the migration script (Fase 2) and the loader (Fase 3)
    must produce identical norm_ids for the same input.
    """
    from lia_graph.canon import canonicalize

    article_number = (article_number or "").strip()
    source_path = (source_path or "").strip()

    # Prose-only — empty article_number means the node is keyed by
    # `whole::<source_path>` per loader.py:51-54. No norm_id.
    if not article_number:
        return DerivationOutcome(
            article_id=article_id,
            article_number="",
            source_path=source_path,
            norm_id=None,
            rule_name="prose_only",
            mention=None,
            refusal_reason=None,
        )

    # Idempotency — already-canonical input survives re-runs unchanged.
    if _is_already_canonical(article_id):
        return DerivationOutcome(
            article_id=article_id,
            article_number=article_number,
            source_path=source_path,
            norm_id=article_id,
            rule_name="idempotent",
            mention=article_id,
            refusal_reason=None,
        )

    for rule in _RULES:
        mention = rule.fn(source_path, article_number)
        if mention is None:
            continue
        if mention.startswith(SKIP_SENTINEL):
            return DerivationOutcome(
                article_id=article_id,
                article_number=article_number,
                source_path=source_path,
                norm_id=None,
                rule_name=rule.name,
                mention=None,
                refusal_reason=mention[len(SKIP_SENTINEL):],
            )
        norm_id = canonicalize(mention)
        if norm_id is None:
            return DerivationOutcome(
                article_id=article_id,
                article_number=article_number,
                source_path=source_path,
                norm_id=None,
                rule_name=f"{rule.name}_canon_refused",
                mention=mention,
                refusal_reason="canon_canonicalize_returned_none",
            )
        return DerivationOutcome(
            article_id=article_id,
            article_number=article_number,
            source_path=source_path,
            norm_id=norm_id,
            rule_name=rule.name,
            mention=mention,
            refusal_reason=None,
        )

    return DerivationOutcome(
        article_id=article_id,
        article_number=article_number,
        source_path=source_path,
        norm_id=None,
        rule_name="OTHER",
        mention=None,
        refusal_reason="no_path_rule_matched",
    )


def rule_names() -> tuple[str, ...]:
    """Names of all configured rules — for telemetry / docs."""
    return tuple(r.name for r in _RULES) + ("prose_only", "idempotent", "OTHER")


__all__ = [
    "DerivationOutcome",
    "Rule",
    "SKIP_SENTINEL",
    "derive_norm_id",
    "rule_names",
]
