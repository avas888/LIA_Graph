"""v23 P3 — Article → source-code resolver (G3).

Stop hardcoding `art. X ET`. Resolve every cited article to its real source
code (ET / CST / C.Co. / Ley 43/1990 / Res. DIAN / Decreto) using a
combination of:

  1. ``node_key`` prefix (highest priority — `cst.art.64` → CST).
  2. Built-in code tables keyed on article number + topic hint (labor topics
     anchor to CST; revisor-fiscal topics anchor to C.Co. + Ley 43/1990).
  3. ``None`` when neither signals fires — caller renders without a code
     suffix instead of inventing one.

Pseudo-citation detection is in `is_real_article_number` — anchor slots
whose value is non-numeric (e.g. `notas-y-fuentes`, `respuesta-operativa`)
are silently dropped at the renderer.

Flag-gated by ``LIA_CITATION_SOURCE_CODE_AWARENESS={off,shadow,enforce}``,
default ``enforce``.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Iterable


_ARTICLE_NUMBER_RX = re.compile(r"^\d+(?:[A-Za-z-]\d+|-\d+)?$")


_NODE_KEY_PREFIX_MAP: dict[str, str] = {
    "cst.": "CST",
    "et.": "ET",
    "cco.": "CCO",
    "ccom.": "CCO",
    "ley.43.1990.": "LEY_43_1990",
    "ley_43_1990.": "LEY_43_1990",
    "res.dian.": "RES_DIAN",
    "resolucion.dian.": "RES_DIAN",
    "decreto.": "DECRETO",
}


_LABOR_TOPICS: frozenset[str] = frozenset({
    "nomina",
    "nomina_electronica",
    "contrato_trabajo",
    "terminacion_contrato",
    "cesantias",
    "auxilio_transporte",
    "liquidacion_laboral",
    "indemnizaciones_laborales",
    "salario",
    "aportes_seguridad_social",
    "cst",
    "labor",
})


_REVISOR_FISCAL_TOPICS: frozenset[str] = frozenset({
    "revisor_fiscal",
    "obligaciones_formales_societarias",
})


# CCo articles relevant to accounting practice. Limited to the ones the
# audit referenced; expand case-by-case as audits surface new gaps.
_CCO_ARTICLES: frozenset[str] = frozenset({"203", "207", "235", "446", "447"})

# Ley 43 de 1990 — contador público + revisor fiscal SAS topes (art. 13).
_LEY_43_1990_ARTICLES: frozenset[str] = frozenset({"13"})


_SOURCE_CODE_DISPLAY: dict[str, str] = {
    "ET": "ET",
    "CST": "CST",
    "CCO": "C.Co.",
    "LEY_43_1990": "Ley 43/1990",
    "RES_DIAN": "Res. DIAN",
    "DECRETO": "Decreto",
}


@dataclass(frozen=True)
class ResolvedAnchor:
    article: str
    source_code: str | None  # None when no confident resolution

    def display(self) -> str:
        if self.source_code is None:
            return f"art. {self.article}"
        suffix = _SOURCE_CODE_DISPLAY.get(self.source_code, self.source_code)
        return f"art. {self.article} {suffix}"


def awareness_mode() -> str:
    raw = (os.getenv("LIA_CITATION_SOURCE_CODE_AWARENESS") or "enforce").strip().lower()
    return raw if raw in ("off", "shadow", "enforce") else "enforce"


def is_real_article_number(value: str) -> bool:
    """True when the value passes the canonical article-number shape
    (``"64"``, ``"401-3"``, ``"102-2"``). Pseudo-citations like
    ``"notas-y-fuentes"`` or ``"respuesta-operativa"`` return False.
    """
    return bool(_ARTICLE_NUMBER_RX.match(str(value or "").strip()))


def resolve_source_code(
    article: str,
    *,
    node_key: str | None = None,
    topic_hint: str | None = None,
    norm_id: str | None = None,
    legacy_default: str | None = "ET",
) -> str | None:
    """Best-effort source-code resolver.

    Priority:
      1. ``node_key`` / ``norm_id`` prefix match (most authoritative).
      2. Article number in a known CCo / Ley 43/1990 table.
      3. ``topic_hint`` membership in labor / revisor-fiscal topic sets.
      4. ``legacy_default`` (defaults to ``"ET"`` for tax topics — preserves
         pre-v23 behavior; pass ``None`` for callers that want to NOT
         emit a fallback code).
    """
    if awareness_mode() == "off":
        return legacy_default

    for raw in (node_key, norm_id):
        if not raw:
            continue
        text = str(raw).strip().lower()
        for prefix, code in _NODE_KEY_PREFIX_MAP.items():
            if text.startswith(prefix):
                return code

    article_clean = str(article or "").strip()
    if article_clean:
        if article_clean in _CCO_ARTICLES and (topic_hint or "").strip().lower() in _REVISOR_FISCAL_TOPICS:
            return "CCO"
        if article_clean in _LEY_43_1990_ARTICLES and (topic_hint or "").strip().lower() in _REVISOR_FISCAL_TOPICS:
            return "LEY_43_1990"

    hint = (topic_hint or "").strip().lower()
    if hint in _LABOR_TOPICS:
        return "CST"
    if hint in _REVISOR_FISCAL_TOPICS:
        # When the article isn't in our small CCo table, default to CCo for
        # revisor-fiscal topics. Wrong is better than ET wrong (which is
        # what the audit caught).
        return "CCO"

    return legacy_default


def render_anchor_phrase(anchors: Iterable[ResolvedAnchor]) -> str:
    """Render a tuple of `ResolvedAnchor` as a comma-grouped citation
    phrase, with each source-code group rendered as its own `art. … <code>`
    clause. Drops anchors whose `article` is not a real article number.
    """
    cleaned: list[ResolvedAnchor] = []
    for a in anchors:
        if not isinstance(a, ResolvedAnchor):
            continue
        if not is_real_article_number(a.article):
            continue
        cleaned.append(a)
    if not cleaned:
        return ""

    # Group by source_code preserving order of first appearance.
    order: list[str | None] = []
    by_code: dict[str | None, list[str]] = {}
    for a in cleaned:
        if a.source_code not in by_code:
            by_code[a.source_code] = []
            order.append(a.source_code)
        if a.article not in by_code[a.source_code]:
            by_code[a.source_code].append(a.article)

    clauses: list[str] = []
    for code in order:
        articles = by_code[code]
        suffix = _SOURCE_CODE_DISPLAY.get(code or "", code or "") if code else None
        if len(articles) == 1:
            clauses.append(
                f"art. {articles[0]} {suffix}" if suffix else f"art. {articles[0]}"
            )
        elif len(articles) == 2:
            head = f"arts. {articles[0]} y {articles[1]}"
            clauses.append(f"{head} {suffix}" if suffix else head)
        else:
            head = f"arts. {', '.join(articles[:-1])} y {articles[-1]}"
            clauses.append(f"{head} {suffix}" if suffix else head)
    return "; ".join(clauses)


__all__ = [
    "ResolvedAnchor",
    "awareness_mode",
    "is_real_article_number",
    "render_anchor_phrase",
    "resolve_source_code",
]
