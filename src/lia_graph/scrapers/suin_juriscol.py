"""Scraper for https://www.suin-juriscol.gov.co/ — fixplan_v6 §3 step 2.

SUIN-Juriscol is the **preferred** primary source for legislative norms
in the vigencia harness (per fixplan_v6 §3 step 3). The DUR master pages
on DIAN normograma are 3 MB blobs the LLM struggles to slice; SUIN
exposes per-article boundaries via its document DOM and we already
harvested 3 387 HTML files into ``cache/suin/<sha1>.html``.

This scraper implements three things on top of the base ``Scraper``
contract:

1. Canonical-norm-id → SUIN URL resolution via the registry built by
   ``scripts/canonicalizer/build_suin_doc_id_registry.py`` (loaded from
   ``var/suin_doc_id_registry.json``). For article-scoped norms the
   registry lookup goes through the parent doc.
2. A fetch path that prefers (a) the standard scraper cache,
   (b) the SUIN harvester's hash-keyed disk cache (``cache/suin/``),
   (c) live HTTP via ``SuinFetcher`` — but only when ``live_fetch=True``.
3. Per-article slicing using ``parse_document`` from the harvester's
   parser. The result is the article body text (typically 0.5-10 KB)
   instead of the full doc (often 3-17 MB), which is the whole point of
   wiring SUIN in.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lia_graph.scrapers.base import Scraper, ScraperFetchResult
from lia_graph.scrapers.cache import CacheEntry
from lia_graph.scrapers.secretaria_senado import _html_to_text


LOGGER = logging.getLogger(__name__)


_SUIN_BASE_URL = "https://www.suin-juriscol.gov.co/"
_SUIN_VIEW_URL = _SUIN_BASE_URL + "viewDocument.asp"
_REGISTRY_PATH = Path("var/suin_doc_id_registry.json")
_DISK_CACHE_DIR = Path("cache/suin")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _canonical_parent_id(norm_id: str) -> str:
    """Strip the ``.art.<...>`` suffix to get the parent document id.

    Examples
    --------
    ``decreto.1625.2016.art.1.6.1.1.10`` → ``decreto.1625.2016``.
    ``ley.100.1993.art.5`` → ``ley.100.1993``.
    ``cst.art.45.par.1`` → ``cst``.
    Already-parent ids pass through unchanged.
    """

    if ".art." in norm_id:
        return norm_id.split(".art.", 1)[0]
    return norm_id


def _article_key_from_norm_id(norm_id: str) -> str | None:
    """Return the dotted article path after ``.art.``, or None.

    Sub-units (``.par.N`` / ``.inciso.N`` / ``.num.N`` / ``.lit.X``) are
    stripped — they live inside the article body anyway, so the slicer
    pulls the parent article and the LLM finds the sub-unit in the text.

    Examples
    --------
    ``decreto.1625.2016.art.1.6.1.1.10`` → ``"1.6.1.1.10"``.
    ``ley.100.1993.art.5.par.2`` → ``"5"``.
    ``decreto.1625.2016`` → ``None``.
    """

    if ".art." not in norm_id:
        return None
    after = norm_id.split(".art.", 1)[1]
    sub_unit_markers = (".par.", ".inciso.", ".num.", ".lit.")
    for marker in sub_unit_markers:
        if marker in after:
            after = after.split(marker, 1)[0]
            break
    return after or None


def _load_suin_registry(path: Path = _REGISTRY_PATH) -> dict[str, dict[str, str]]:
    """Read ``var/suin_doc_id_registry.json``. Empty dict if missing.

    A missing registry is the steady-state for tests that don't ship one;
    the scraper degrades to "handle nothing" and the harness falls
    through to other primary sources. Build via
    ``scripts/canonicalizer/build_suin_doc_id_registry.py``.
    """

    if not path.is_file():
        LOGGER.info(
            "SUIN registry %s missing — SUIN scraper will resolve no URLs. "
            "Build via scripts/canonicalizer/build_suin_doc_id_registry.py.",
            path,
        )
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as err:
        LOGGER.warning("SUIN registry load failed (%s): %s", path, err)
        return {}


def _disk_cache_path(url: str, *, root: Path = _DISK_CACHE_DIR) -> Path:
    """Mirror ``SuinFetcher._cache_path`` so we can read its on-disk hits."""

    sha1 = hashlib.sha1(url.encode("utf-8")).hexdigest()
    return root / f"{sha1}.html"


def _read_suin_disk_cache(url: str, *, root: Path = _DISK_CACHE_DIR) -> str | None:
    """Return the cached HTML for ``url`` from the SUIN harvester cache, or None."""

    path = _disk_cache_path(url, root=root)
    if not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except Exception as err:
        LOGGER.warning("SUIN disk cache read failed (%s): %s", path, err)
        return None


def _parse_suin_document(html: str, *, doc_id: str, ruta: str):
    """Parse SUIN HTML to a ``SuinDocument``. Returns None on failure.

    Imported lazily so test fixtures that don't install bs4 / lxml can
    still import the scraper module.
    """

    from lia_graph.ingestion.suin.parser import parse_document

    if not html:
        return None
    try:
        return parse_document(
            html,
            doc_id=str(doc_id),
            ruta=str(ruta or ""),
            strict_verbs=False,  # tolerate long-tail SUIN verbs at fetch-time
        )
    except Exception as err:
        LOGGER.warning(
            "SUIN parse failed (doc_id=%s): %s",
            doc_id,
            err,
        )
        return None


def _slice_article_from_suin_doc(doc, article_key: str) -> str | None:
    """Find the article matching ``article_key`` in a parsed ``SuinDocument``.

    Returns the body text (stripped) or None on miss. Article matching
    uses ``normalize_article_key`` on both sides so casing / accents /
    whitespace collapse to one canonical key.
    """

    from lia_graph.ingestion.suin.parser import normalize_article_key

    if doc is None or not article_key:
        return None
    target = normalize_article_key(article_key)
    if not target:
        return None
    for article in doc.articles:
        if normalize_article_key(article.article_number) == target:
            body = (article.body_text or "").strip()
            if body:
                return body
    return None


def _slice_article_from_suin_html(
    html: str,
    article_key: str,
    *,
    doc_id: str,
    ruta: str,
) -> str | None:
    """One-shot helper: parse + slice. Used in tests; production goes via the
    scraper's persisted-slice cache (``SuinJuriscolScraper._articles_dict_for_url``)
    so the 17 MB DUR HTML isn't re-parsed for every norm in a batch.
    """

    if not html or not article_key:
        return None
    doc = _parse_suin_document(html, doc_id=doc_id, ruta=ruta)
    return _slice_article_from_suin_doc(doc, article_key)


def _extract_articles_dict(html: str, *, doc_id: str, ruta: str) -> dict[str, str]:
    """Parse SUIN HTML and return ``{normalize_article_key(art_num): body_text}``.

    First-occurrence wins on duplicate keys (the parser produces
    repeated entries for some article anchors; we want a stable
    canonical body per key). Empty bodies are dropped. Returns an
    empty dict on parse failure or empty input — never raises.

    This is the Option-2 persistence shape: ~3 MB JSON for the entire
    DUR-1625 (vs ~165 MB for retaining the full SuinDocument). Stored
    as ``parsed_meta["articles"]`` in ``var/scraper_cache.db`` so that
    parallel processes share the slice store and don't each re-parse.
    """

    from lia_graph.ingestion.suin.parser import normalize_article_key

    if not html:
        return {}
    doc = _parse_suin_document(html, doc_id=doc_id, ruta=ruta)
    if doc is None:
        return {}
    out: dict[str, str] = {}
    for article in doc.articles:
        key = normalize_article_key(article.article_number or "")
        if not key:
            continue
        body = (article.body_text or "").strip()
        if not body:
            continue
        out.setdefault(key, body)
    return out


def _slice_from_articles_dict(
    articles_dict: dict[str, str] | None, article_key: str
) -> str | None:
    """Look up ``article_key`` in a ``{key: body}`` dict produced by
    ``_extract_articles_dict``. Returns the body or None on miss."""

    from lia_graph.ingestion.suin.parser import normalize_article_key

    if not articles_dict or not article_key:
        return None
    target = normalize_article_key(article_key)
    if not target:
        return None
    body = articles_dict.get(target)
    return body or None


# ---------------------------------------------------------------------------
# Scraper
# ---------------------------------------------------------------------------


class SuinJuriscolScraper(Scraper):
    """SUIN-Juriscol scraper that prefers the per-article slice from cache.

    Lookup order on ``fetch(norm_id)``:

    1. ``self.cache.get(source_id, url)`` — the standard SQLite cache.
    2. ``cache/suin/<sha1>.html`` — the SUIN harvester's disk cache,
       populated by previous ``SuinFetcher`` runs (3 387 files today).
    3. Live HTTP via ``SuinFetcher`` — only when ``live_fetch=True``.

    On (2) and (3) the result is parsed once and persisted to the
    standard cache so the next call short-circuits at (1). Per-article
    slicing happens after the page is materialized.
    """

    source_id = "suin_juriscol"
    rate_limit_seconds = 1.0
    _handled_types = {
        # Top-level legislative artifacts.
        "ley", "ley_articulo",
        "decreto", "decreto_articulo",
        "estatuto", "articulo_et",
        "resolucion", "res_articulo",
        # Codes consolidated on SUIN.
        "cst_articulo", "cco_articulo",
    }

    def __init__(
        self,
        cache,
        *,
        live_fetch: bool | None = None,
        registry: dict[str, dict[str, str]] | None = None,
        registry_path: Path | None = None,
        disk_cache_dir: Path | None = None,
        fetcher=None,
    ) -> None:
        super().__init__(cache, live_fetch=live_fetch)
        if registry is not None:
            self._registry = dict(registry)
        else:
            self._registry = _load_suin_registry(
                registry_path or _REGISTRY_PATH
            )
        self._disk_cache_dir = Path(disk_cache_dir) if disk_cache_dir is not None else _DISK_CACHE_DIR
        self._fetcher = fetcher
        # Per-URL articles-dict cache. Holds the deserialized
        # ``parsed_meta["articles"]`` dict (article_key → body_text) so
        # multiple fetches in the same process don't re-deserialize the
        # ~3 MB JSON from SQLite per call. Memory cost: ~5-10 MB per
        # cached parent doc (vs 165 MB for retaining the full
        # SuinDocument the v0 cache held). Process-shared persistence
        # lives in ``var/scraper_cache.db`` ``parsed_meta`` — see
        # ``_extract_articles_dict`` for the populate path.
        self._articles_dict_cache: dict[str, dict[str, str]] = {}
        self._articles_dict_lock = threading.Lock()

    # ------------------------------------------------------------------
    # Hook implementations required by the base class
    # ------------------------------------------------------------------

    def _resolve_url(self, norm_id: str) -> str | None:
        """Map ``norm_id`` to its parent SUIN document URL.

        Article-scoped norms resolve through their parent: the slicer
        (in :meth:`fetch`) runs against the parent doc HTML. Returns
        ``None`` when the parent is not in the registry.
        """

        parent_id = _canonical_parent_id(norm_id)
        entry = self._registry.get(parent_id)
        if entry is None:
            return None
        return entry.get("ruta") or None

    def _parse_html(self, content: bytes) -> tuple[str, dict[str, Any]]:
        """Whole-doc plaintext + empty meta. Per-article slicing is in fetch()."""

        text = _html_to_text(content.decode("utf-8", errors="ignore"))
        return text, {}

    # ------------------------------------------------------------------
    # Public override
    # ------------------------------------------------------------------

    def fetch(self, norm_id: str) -> ScraperFetchResult | None:
        parent_id = _canonical_parent_id(norm_id)
        entry = self._registry.get(parent_id)
        if entry is None:
            return None
        url = entry.get("ruta")
        if not url:
            return None
        suin_doc_id = str(entry.get("suin_doc_id") or "")

        cache_entry, cache_hit = self._materialize_cache_entry(norm_id, url)
        if cache_entry is None:
            return None

        article_key = _article_key_from_norm_id(norm_id)
        if article_key is None:
            # Top-level doc — return the whole-doc parsed text.
            return ScraperFetchResult(
                norm_id=norm_id,
                source=self.source_id,
                url=url,
                fetched_at_utc=cache_entry.fetched_at_utc,
                status_code=cache_entry.status_code,
                parsed_text=cache_entry.parsed_text or "",
                parsed_meta={
                    **dict(cache_entry.parsed_meta or {}),
                    "suin_doc_id": suin_doc_id,
                },
                cache_hit=cache_hit,
            )

        articles_dict = self._articles_dict_for_url(
            url=url,
            cache_entry=cache_entry,
            suin_doc_id=suin_doc_id,
        )
        sliced = _slice_from_articles_dict(articles_dict, article_key)
        if not sliced:
            return None
        return ScraperFetchResult(
            norm_id=norm_id,
            source=self.source_id,
            url=url,
            fetched_at_utc=cache_entry.fetched_at_utc,
            status_code=cache_entry.status_code,
            parsed_text=sliced,
            parsed_meta={
                "suin_doc_id": suin_doc_id,
                "sliced_to_article": article_key,
                "sliced_chars": len(sliced),
            },
            cache_hit=cache_hit,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _materialize_cache_entry(
        self,
        norm_id: str,
        url: str,
    ) -> tuple[CacheEntry | None, bool]:
        """Ensure ``var/scraper_cache.db`` has an entry for ``url``.

        Returns ``(entry, cache_hit)``. ``cache_hit=True`` means the
        SQLite cache already had it; ``False`` means we just populated
        it from the SUIN disk cache or a live fetch.
        """

        cached = self.cache.get(self.source_id, url)
        if cached is not None:
            return cached, True

        disk_html = _read_suin_disk_cache(url, root=self._disk_cache_dir)
        if disk_html is None:
            if not self.live_fetch:
                return None, False
            try:
                disk_html = self._get_or_create_fetcher().fetch(url)
            except Exception as err:
                LOGGER.warning("SUIN live fetch failed for %s: %s", url, err)
                return None, False

        content_bytes = disk_html.encode("utf-8")
        parsed_text, parsed_meta = self._parse_html(content_bytes)
        # Extract per-article slices ONCE on first parse and persist them
        # in ``parsed_meta["articles"]``. Subsequent fetches — across this
        # process AND across other processes that read the same SQLite
        # cache — get a tiny dict-lookup instead of a 17 MB BeautifulSoup
        # re-parse. This is the persisted-slice cache; it's the difference
        # between ~110 MB steady-state per process and ~50 MB.
        articles_dict = _extract_articles_dict(
            disk_html, doc_id=str(self._registry_doc_id_for_url(url) or ""), ruta=url
        )
        if articles_dict:
            parsed_meta = {
                **parsed_meta,
                "articles": articles_dict,
                "article_count": len(articles_dict),
            }
        try:
            self.cache.put(
                source=self.source_id,
                url=url,
                content=content_bytes,
                status_code=200,
                canonical_norm_id=norm_id,
                content_type="text/html; charset=utf-8",
                parsed_text=parsed_text,
                parsed_meta=parsed_meta,
            )
        except Exception as err:
            # Cache writes shouldn't block the fetch — fall back to a
            # synthetic CacheEntry built from what we just parsed.
            LOGGER.info("SUIN cache write failed (%s): %s", url, err)
            return (
                CacheEntry(
                    source=self.source_id,
                    url=url,
                    canonical_norm_id=norm_id,
                    fetched_at_utc=datetime.now(timezone.utc).isoformat(),
                    status_code=200,
                    content_sha256=hashlib.sha256(content_bytes).hexdigest(),
                    content=content_bytes,
                    content_type="text/html; charset=utf-8",
                    parsed_text=parsed_text,
                    parsed_meta=parsed_meta,
                ),
                False,
            )
        new_entry = self.cache.get(self.source_id, url)
        return new_entry, False

    def _registry_doc_id_for_url(self, url: str) -> str | None:
        for entry in self._registry.values():
            if entry.get("ruta") == url:
                return entry.get("suin_doc_id")
        return None

    def _get_or_create_fetcher(self):
        if self._fetcher is None:
            from lia_graph.ingestion.suin.fetcher import SuinFetcher

            self._fetcher = SuinFetcher(cache_dir=self._disk_cache_dir)
        return self._fetcher

    def _articles_dict_for_url(
        self,
        *,
        url: str,
        cache_entry: CacheEntry,
        suin_doc_id: str,
    ) -> dict[str, str] | None:
        """Return the per-URL article slice dict, populating from SQLite or live parse.

        Lookup order:
          1. Per-process LRU dict (avoid re-deserializing the JSON every fetch).
          2. ``cache_entry.parsed_meta["articles"]`` from SQLite (process-shared).
          3. Live parse from the cached HTML (lazy backfill for legacy rows).

        Cache writes are best-effort — extraction failures fall through to
        an in-memory parse without breaking the fetch.
        """

        with self._articles_dict_lock:
            cached = self._articles_dict_cache.get(url)
            if cached is not None:
                return cached

        # Try the persisted slices in SQLite first (the Option-2 path).
        meta = dict(cache_entry.parsed_meta or {})
        articles_obj = meta.get("articles")
        if isinstance(articles_obj, dict) and articles_obj:
            articles_dict = {str(k): str(v) for k, v in articles_obj.items()}
            with self._articles_dict_lock:
                self._articles_dict_cache[url] = articles_dict
            return articles_dict

        # Legacy row (no articles in parsed_meta) — parse from the HTML
        # blob and backfill the SQLite parsed_meta column so the next call
        # doesn't pay this cost. This branch fires once per (legacy) URL.
        html = (cache_entry.content or b"").decode("utf-8", errors="ignore")
        articles_dict = _extract_articles_dict(
            html, doc_id=str(suin_doc_id or ""), ruta=url
        )
        if not articles_dict:
            return None

        # Lazy backfill — best-effort.
        try:
            new_meta = {
                **meta,
                "articles": articles_dict,
                "article_count": len(articles_dict),
            }
            self.cache.put(
                source=self.source_id,
                url=url,
                content=cache_entry.content or b"",
                status_code=cache_entry.status_code,
                canonical_norm_id=cache_entry.canonical_norm_id,
                content_type=cache_entry.content_type,
                parsed_text=cache_entry.parsed_text,
                parsed_meta=new_meta,
            )
        except Exception as err:
            LOGGER.debug("SUIN parsed_meta backfill failed (%s): %s", url, err)

        with self._articles_dict_lock:
            self._articles_dict_cache[url] = articles_dict
        return articles_dict


__all__ = [
    "SuinJuriscolScraper",
    # Helpers — exported for tests + downstream tools.
    "_canonical_parent_id",
    "_article_key_from_norm_id",
    "_load_suin_registry",
    "_read_suin_disk_cache",
    "_parse_suin_document",
    "_slice_article_from_suin_doc",
    "_slice_article_from_suin_html",
    "_extract_articles_dict",
    "_slice_from_articles_dict",
]
