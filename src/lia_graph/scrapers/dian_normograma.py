"""Scraper for https://normograma.dian.gov.co/.

Coverage:
  * Decretos tributarios + resoluciones DIAN + conceptos DIAN
  * **Estatuto Tributario** — DIAN hosts the full ET as one large page
    (`estatuto_tributario.htm`, ~3.9 MB). We use it as the SECOND primary
    source for every `et.*` norm_id, complementing
    `secretariasenado.gov.co` on the first source.

Article-scoped slicing for ET: the full DIAN ET page is too large for a
Gemini prompt context. We pre-inject ``[[ART:N]]`` markers at every
``<a name="N">`` anchor during parse, store the marked text in the
cache once, and then slice down to the requested article in
``fetch()``. See `docs/learnings/sites/normograma-dian.md`.

Primary source for `decreto.*`, `res.dian.*`, `concepto.dian.*`,
and `et.*` norm_ids.
"""

from __future__ import annotations

import re
from typing import Any

from lia_graph.scrapers.base import Scraper, ScraperFetchResult
from lia_graph.scrapers.secretaria_senado import _html_to_text


_BASE_URL = "https://normograma.dian.gov.co/dian/compilacion/docs"
_ET_FULL_URL = f"{_BASE_URL}/estatuto_tributario.htm"

# Inserted into parsed_text at every <a name="ART"> anchor. Preserves the
# article boundary across the cache layer.
_ART_MARKER_RX = re.compile(r"\[\[ART:([0-9]+(?:-[0-9]+)?)\]\]")
_ANCHOR_RX = re.compile(
    r'<a\s+[^>]*name="([0-9]+(?:-[0-9]+)?)"[^>]*>',
    re.IGNORECASE,
)


def _inject_article_markers(html: str) -> str:
    """Replace each `<a name="N">` with `<a name="N">\n[[ART:N]]\n` so the
    article boundary survives the HTML→text parse."""

    return _ANCHOR_RX.sub(
        lambda m: f'<a name="{m.group(1)}">\n[[ART:{m.group(1)}]]\n',
        html,
    )


def _slice_article(text: str, article: str) -> str | None:
    """Return the substring containing exactly the requested article.

    For an ET sub-unit like ``689-3``, slice that sub-unit's segment;
    if the sub-unit isn't anchored separately, fall back to the parent
    article's segment (which contains all sub-units inline).
    """

    targets = [article]
    if "-" in article:
        targets.append(article.split("-")[0])
    for target in targets:
        marker = f"[[ART:{target}]]"
        start_idx = text.find(marker)
        if start_idx < 0:
            continue
        # End is the next [[ART:M]] marker (any M, including sub-units).
        nxt = _ART_MARKER_RX.search(text, start_idx + len(marker))
        end_idx = nxt.start() if nxt else len(text)
        return text[start_idx:end_idx].strip()
    return None


class DianNormogramaScraper(Scraper):
    source_id = "dian_normograma"
    rate_limit_seconds = 0.5
    _handled_types = {
        "decreto",
        "decreto_articulo",
        "resolucion",
        "res_articulo",
        "concepto_dian",
        "concepto_dian_numeral",
        "estatuto",
        "articulo_et",
        "ley",
        "ley_articulo",
    }

    def _resolve_url(self, norm_id: str) -> str | None:
        # ET — the entire ET is on one page; same URL for every article.
        # Article-scoped slicing happens in `fetch()` below.
        if norm_id == "et" or norm_id.startswith("et."):
            return _ET_FULL_URL
        # Leyes — DIAN normograma hosts most reform laws as one page each.
        # Per-article slicing applies via `<a name="N">` anchors (same shape
        # as Senado). Pattern: ley_<NUM4>_<YEAR>.htm — DIAN pads NUM to 4
        # digits (`ley_0100_1993.htm`, not `ley_100_1993.htm`).
        if norm_id.startswith("ley."):
            parts = norm_id.split(".")
            if len(parts) < 3:
                return None
            num4 = parts[1].zfill(4)
            return f"{_BASE_URL}/ley_{num4}_{parts[2]}.htm"
        if norm_id.startswith("decreto."):
            parts = norm_id.split(".")
            if len(parts) < 3:
                return None
            return f"{_BASE_URL}/decreto_{parts[1]}_{parts[2]}.htm"
        if norm_id.startswith("res.dian."):
            parts = norm_id.split(".")
            # res.dian.NUM.YEAR — DIAN pads NUM to 4 digits in the filename
            # (`resolucion_dian_0165_2023.htm`, not `resolucion_dian_165_2023.htm`).
            if len(parts) < 4:
                return None
            num4 = parts[2].zfill(4)
            return f"{_BASE_URL}/resolucion_dian_{num4}_{parts[3]}.htm"
        if norm_id.startswith("concepto.dian."):
            parts = norm_id.split(".")
            num = parts[2]
            # Two distinct hyphenated forms exist:
            #   1. year-suffix:  `0001-2003`, `0002-2014` (4-digit padnum + 4-digit year)
            #      → DIAN serves these as concepto_dian_<num>-<year>.htm — keep mapping.
            #   2. unified-radicado: `100208192-202`, `100202208-30` (long radicado +
            #      short subject suffix) → DIAN serves under `oficio_dian_<RADICADO>_<YEAR>.htm`,
            #      not derivable from the canonical id alone. Requires an external
            #      `var/dian_concepto_lookup.json` (fixplan_v5 §3 #3 follow-up).
            #
            # Distinguishing rule: if both halves are 4 digits and the right half
            # parses as a plausible year (1990-2030), it's form #1. Otherwise, fall
            # through to None for form #2.
            if "-" in num:
                left, _, right = num.partition("-")
                if (
                    left.isdigit() and right.isdigit()
                    and len(left) == 4 and len(right) == 4
                    and 1990 <= int(right) <= 2030
                ):
                    return f"{_BASE_URL}/concepto_dian_{num}.htm"
                return None
            return f"{_BASE_URL}/concepto_dian_{num}.htm"
        return None

    def _parse_html(self, content: bytes) -> tuple[str, dict[str, Any]]:
        # Inject [[ART:N]] markers BEFORE stripping HTML so the article
        # boundary survives into parsed_text. The cache stores the full
        # marked text; per-article slicing happens at fetch time.
        html = content.decode("utf-8", errors="ignore")
        text = _html_to_text(_inject_article_markers(html))
        # DIAN normograma renders a "Notas de vigencia" panel — extract it.
        notes_match = re.search(
            r"Notas?\s+de\s+Vigencia[\s\S]{0,2000}?(?=Notas?\s+del\s+Editor|$)",
            text,
            flags=re.IGNORECASE,
        )
        notes = notes_match.group(0).strip() if notes_match else ""
        return text, {"vigencia_notes": notes}

    def fetch(self, norm_id: str) -> ScraperFetchResult | None:
        # Get the full document via the base implementation — single cache
        # hit serves every article in that doc.
        result = super().fetch(norm_id)
        if result is None:
            return None

        # Determine the article id (if any) to slice to. ET sub-units like
        # "et.art.689-3" use the trailing "689-3" segment; ley sub-units like
        # "ley.2155.2021.art.12" use the trailing "12" segment.
        article: str | None = None
        if norm_id.startswith("et.art."):
            article = norm_id.split(".", 2)[2]
        elif ".art." in norm_id and norm_id.startswith("ley."):
            # ley.<NUM>.<YEAR>.art.<X>  →  X is the segment after ".art."
            after_art = norm_id.split(".art.", 1)[1]
            # Sub-unit shapes (e.g. ".par.1") trim to just the article id.
            article = after_art.split(".", 1)[0]
        if article is None:
            return result  # whole-document request (et, ley.NUM.YEAR root, etc.)

        sliced = _slice_article(result.parsed_text or "", article)
        if not sliced:
            # No anchor found for this article — return the original (full)
            # text rather than failing; the prompt can still try to find it.
            return result
        # Build a new ScraperFetchResult with sliced parsed_text + a
        # parsed_meta key noting the slice provenance.
        new_meta = dict(result.parsed_meta)
        new_meta["sliced_article"] = article
        new_meta["sliced_chars"] = len(sliced)
        return ScraperFetchResult(
            norm_id=result.norm_id,
            source=result.source,
            url=result.url,
            fetched_at_utc=result.fetched_at_utc,
            status_code=result.status_code,
            parsed_text=sliced,
            parsed_meta=new_meta,
            cache_hit=result.cache_hit,
        )


__all__ = ["DianNormogramaScraper"]
