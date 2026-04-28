"""Scraper for http://www.secretariasenado.gov.co/senado/basedoc/.

Coverage: Leyes (incluye ET), modification notes per artículo. Use as one
of the two primary sources for any `ley.*` or `et.art.*` norm_id per the
skill's `fuentes-primarias.md` rules.

**Site notes** (see `docs/learnings/sites/secretariasenado.md`):
  * HTTPS port 443 is unreachable from many networks (we've observed
    persistent timeouts; HTTP on port 80 works). Hence `_BASE_URL`
    is `http://` — the site does not redirect to HTTPS.
  * The ET is split across pr001..pr035 segment files. The article →
    segment map is NOT a clean ``article // 10`` formula. We ship a
    pre-built index at ``var/senado_et_pr_index.json`` (rebuild via
    ``scripts/canonicalizer/build_senado_et_index.py``).
  * The path is ``/senado/basedoc/estatuto_tributario_prNNN.html``
    (NO ``/codigo/`` segment — that path 404s).
"""

from __future__ import annotations

import json
import logging
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from lia_graph.scrapers.base import Scraper, ScraperFetchResult


_BASE_URL = "http://www.secretariasenado.gov.co/senado/basedoc"
_ET_FULL_PATH = f"{_BASE_URL}/estatuto_tributario.html"
_ET_INDEX_PATH = Path("var/senado_et_pr_index.json")
_LOGGER = logging.getLogger(__name__)
_INDEX_CACHE: dict[str, str] | None = None


def _load_et_index() -> dict[str, str]:
    """Article → pr-segment map (3-digit zero-padded). Cached at module level."""

    global _INDEX_CACHE
    if _INDEX_CACHE is not None:
        return _INDEX_CACHE
    if not _ET_INDEX_PATH.is_file():
        _LOGGER.warning(
            "Senado ET pr-index missing (%s) — ET article URL resolution disabled. "
            "Build it with `uv run python scripts/canonicalizer/build_senado_et_index.py`.",
            _ET_INDEX_PATH,
        )
        _INDEX_CACHE = {}
        return _INDEX_CACHE
    try:
        _INDEX_CACHE = json.loads(_ET_INDEX_PATH.read_text(encoding="utf-8"))
    except Exception as err:
        _LOGGER.warning("Could not load %s: %s", _ET_INDEX_PATH, err)
        _INDEX_CACHE = {}
    return _INDEX_CACHE


class SecretariaSenadoScraper(Scraper):
    source_id = "secretaria_senado"
    rate_limit_seconds = 0.5
    _handled_types = {"ley", "ley_articulo", "estatuto", "articulo_et"}

    def _resolve_url(self, norm_id: str) -> str | None:
        if norm_id == "et":
            return _ET_FULL_PATH
        if norm_id.startswith("et.art."):
            article = norm_id.split(".", 2)[2]
            # ET sub-units share the article's URL — content is on one page.
            # Try the full article id first ("689-3"), then the integer base
            # ("689") — sub-units that the index didn't enumerate fall back
            # to the parent article's segment.
            index = _load_et_index()
            seg = index.get(article)
            if seg is None:
                article_base = article.split("-")[0]
                seg = index.get(article_base)
            # Nearest-neighbor fallback: the index sweep can miss an article
            # if Senado renders that article's anchor in a non-standard
            # shape (e.g. `name="T714"` instead of `name="714"`). Articles
            # cluster monotonically in segments, so fall back to the segment
            # of the closest enumerated article. See
            # `docs/learnings/sites/secretariasenado.md`.
            if seg is None:
                seg = _nearest_neighbor_segment(article, index)
            if seg is None:
                return None
            return f"{_BASE_URL}/estatuto_tributario_pr{seg}.html"
        if norm_id.startswith("ley."):
            parts = norm_id.split(".")
            if len(parts) < 3:
                return None
            # Senado pads ley NUM to 4 digits in the URL filename
            # (`ley_0100_1993.html`, not `ley_100_1993.html`).
            num4 = parts[1].zfill(4)
            year = parts[2]
            return f"{_BASE_URL}/ley_{num4}_{year}.html"
        return None

    def _parse_html(self, content: bytes) -> tuple[str, dict[str, Any]]:
        # Inject [[ART:N]] markers BEFORE stripping HTML so per-article
        # boundaries survive into parsed_text. The cache stores the marked
        # text once; per-article slicing happens at fetch time.
        html = content.decode("utf-8", errors="ignore")
        text = _html_to_text(_inject_article_markers_senado(html))
        # Extract any "Modificado por" / "Derogado por" notes the page renders.
        notes = []
        for m in re.finditer(
            r"(?:Modificado|Derogado|Adicionado|Sustituido)\s+por[^.]+\.",
            text,
            flags=re.IGNORECASE,
        ):
            notes.append(m.group(0).strip())
        return text, {"modification_notes": notes}

    def fetch(self, norm_id: str) -> ScraperFetchResult | None:
        result = super().fetch(norm_id)
        if result is None:
            return None

        # Article-scoped slicing for ET articles AND ley.*.art.* norms.
        # Both page types use `<a class="bookmarkaj" name="N">` anchors,
        # so the slicer is identical.
        article: str | None = None
        if norm_id.startswith("et.art."):
            article = norm_id.split(".", 2)[2]
        elif norm_id.startswith("ley.") and ".art." in norm_id:
            after_art = norm_id.split(".art.", 1)[1]
            # Sub-units like ".par.1" / ".num.5" → trim to base article id.
            article = after_art.split(".", 1)[0]
        if article is None:
            return result
        sliced = _slice_article_senado(result.parsed_text or "", article)
        if not sliced:
            return result
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


_ART_MARKER_RX = re.compile(r"\[\[ART:([0-9]+(?:-[0-9]+)?)\]\]")
_SENADO_ANCHOR_RX = re.compile(
    r'<a\s+[^>]*name="([0-9]+(?:-[0-9]+)?)"[^>]*>',
    re.IGNORECASE,
)


def _inject_article_markers_senado(html: str) -> str:
    """Add `[[ART:N]]` text markers at every numeric-name anchor before parse.

    Senado uses `<a class="bookmarkaj" name="555">` shapes; we only key on
    numeric names (``555``, ``555-2``) and ignore section anchors like
    ``LIBRO QUINTO`` / ``TITULO I-V``.
    """

    return _SENADO_ANCHOR_RX.sub(
        lambda m: f'<a name="{m.group(1)}">\n[[ART:{m.group(1)}]]\n',
        html,
    )


def _nearest_neighbor_segment(article: str, index: dict[str, str]) -> str | None:
    """Find the pr-segment of the nearest-numbered article in the index.

    Used when the index sweep didn't enumerate the article we want. Walks
    out from the article number alternating ±1 until it finds an entry,
    capped at 30 steps in either direction (most ET segments cover ~25
    articles, so a 30-step search will always cross a boundary).
    """

    base_str = article.split("-")[0]
    try:
        base = int(base_str)
    except ValueError:
        return None
    for delta in range(1, 31):
        for cand in (str(base - delta), str(base + delta)):
            seg = index.get(cand)
            if seg is not None:
                return seg
    return None


def _slice_article_senado(text: str, article: str) -> str | None:
    """Return the substring containing exactly the requested article."""

    targets = [article]
    if "-" in article:
        targets.append(article.split("-")[0])
    for target in targets:
        marker = f"[[ART:{target}]]"
        start_idx = text.find(marker)
        if start_idx < 0:
            continue
        nxt = _ART_MARKER_RX.search(text, start_idx + len(marker))
        end_idx = nxt.start() if nxt else len(text)
        return text[start_idx:end_idx].strip()
    return None


# ---------------------------------------------------------------------------
# Lightweight HTML→text (stdlib-only)
# ---------------------------------------------------------------------------


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._buf: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs):  # type: ignore[override]
        if tag in ("script", "style"):
            self._skip_depth += 1

    def handle_endtag(self, tag: str):  # type: ignore[override]
        if tag in ("script", "style") and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str):  # type: ignore[override]
        if self._skip_depth == 0:
            self._buf.append(data)

    def get_text(self) -> str:
        return re.sub(r"\s+", " ", "".join(self._buf)).strip()


def _html_to_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    return parser.get_text()


__all__ = ["SecretariaSenadoScraper"]
