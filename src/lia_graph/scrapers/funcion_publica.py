"""Scraper for https://www.funcionpublica.gov.co/eva/gestornormativo/.

Función Pública's gestor normativo is a backup primary source for
DURs (Decretos Únicos Reglamentarios). Mirrors the SUIN scraper
architecture: registry-backed URL resolution + three-tier cache +
persisted slice cache (Option 2).

**Why this exists.** When SUIN is down, struggling, or doesn't
include a doc, Función Pública covers most DURs and adds redundancy.
Its anchors are `<a name="N.N.N">` with the DUR key directly — even
cleaner than SUIN's `ver_NNN` pattern. See
`docs/learnings/sites/per-source-fetch-playbook.md` for the
cross-source comparison.

**What this does NOT cover (verified).** DIAN-specific resoluciones
(`res.dian.*`) and DIAN conceptos (`concepto.dian.*`) are not in
Función Pública's harvest — those need a different source.
F2 (res.dian.13.2021.art.*) and G1 (concepto.dian.0001.2003) gaps
remain open after this scraper lands.

**Coverage in v6.1 MVP.** Walks the DUR index page (i=62255) and
finds 26 DURs including DUR-1625, DUR-1072, etc. Operators extend
the registry by adding more index pages to
`scripts/canonicalizer/build_funcionpublica_registry.py::INDEX_PAGES`.
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
from lia_graph.scrapers.suin_juriscol import (
    _article_key_from_norm_id,
    _canonical_parent_id,
)


LOGGER = logging.getLogger(__name__)


_FP_BASE_URL = "https://www.funcionpublica.gov.co/eva/gestornormativo"
_REGISTRY_PATH = Path("var/funcionpublica_doc_id_registry.json")


_FP_SSL_CONTEXT: Any = None


def _fp_ssl_context() -> Any:
    """SSL context that trusts the OS Keychain via truststore.

    Función Pública's cert chain has a Sectigo intermediate that
    certifi's bundle doesn't include (as of certifi 2026.02.25).
    truststore delegates to the OS trust store and works.
    """

    global _FP_SSL_CONTEXT
    if _FP_SSL_CONTEXT is not None:
        return _FP_SSL_CONTEXT
    import ssl
    try:
        import truststore  # type: ignore
        _FP_SSL_CONTEXT = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        return _FP_SSL_CONTEXT
    except ImportError:
        # Fall back to base's certifi context — will likely fail TLS for
        # this site, but the harness gracefully treats fetch errors as
        # "source returned None" and falls through to other scrapers.
        from lia_graph.scrapers.base import _ssl_context_with_certifi
        _FP_SSL_CONTEXT = _ssl_context_with_certifi()
        return _FP_SSL_CONTEXT


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_funcion_publica_registry(
    path: Path = _REGISTRY_PATH,
) -> dict[str, dict[str, str]]:
    """Read ``var/funcionpublica_doc_id_registry.json``. Empty dict if missing."""

    if not path.is_file():
        LOGGER.info(
            "Función Pública registry %s missing — scraper will resolve no URLs. "
            "Build via scripts/canonicalizer/build_funcionpublica_registry.py.",
            path,
        )
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as err:
        LOGGER.warning("Función Pública registry load failed (%s): %s", path, err)
        return {}


def _extract_articles_dict(html: str) -> dict[str, str]:
    """Extract ``{article_key: body_text}`` from a Función Pública doc HTML.

    Función Pública uses ``<a name="<DUR-key>">`` anchors directly — much
    cleaner than SUIN's ``ver_<n>`` indirection. Each anchor is followed
    by the article body until the next anchor.

    The implementation slices on anchor positions: find every
    ``<a name="N.N.N..."`` (numeric-only key like ``1.1.1`` or
    ``1.6.1.1.10``); the body is the HTML between this anchor and the
    next one, stripped to plain text.

    Returns an empty dict on parse failure.
    """

    if not html:
        return {}

    import re as _re

    # Strict DUR-key shape: digits, optional dotted/dashed extensions.
    anchor_rx = _re.compile(
        r'<a\s+[^>]*name="(\d+(?:[-.]\d+)*)"[^>]*>',
        _re.IGNORECASE,
    )
    matches = list(anchor_rx.finditer(html))
    if not matches:
        return {}

    out: dict[str, str] = {}
    for i, m in enumerate(matches):
        key = m.group(1)
        # Normalize the key the same way the parser does for consistency
        # with how callers pass article_key (dotted form).
        from lia_graph.ingestion.suin.parser import normalize_article_key

        normalized = normalize_article_key(key)
        if not normalized or normalized in out:
            continue
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(html)
        body_html = html[start:end]
        body_text = _html_to_text(body_html).strip()
        if body_text:
            out[normalized] = body_text
    return out


def _slice_from_articles_dict(
    articles_dict: dict[str, str] | None, article_key: str
) -> str | None:
    """Look up ``article_key`` in a Función Pública slice dict."""

    from lia_graph.ingestion.suin.parser import normalize_article_key

    if not articles_dict or not article_key:
        return None
    target = normalize_article_key(article_key)
    if not target:
        return None
    return (articles_dict.get(target) or None) or None


# ---------------------------------------------------------------------------
# Scraper
# ---------------------------------------------------------------------------


class FuncionPublicaScraper(Scraper):
    """Función Pública gestor normativo scraper — backup primary source.

    Lookup order (mirrors SUIN scraper):
    1. ``self.cache.get(source_id, url)`` — SQLite cache.
    2. Live HTTP via certifi + truststore SSL — only when ``live_fetch=True``.

    Per-article slicing happens at fetch time. Slices are persisted in
    ``parsed_meta["articles"]`` so parallel processes can share them.
    """

    source_id = "funcion_publica"
    rate_limit_seconds = 1.0  # Política respetuosa con un sitio gov pequeño
    _handled_types = {
        "decreto", "decreto_articulo",
        "ley", "ley_articulo",
        "estatuto", "articulo_et",
        "cst_articulo", "cco_articulo",
    }

    def __init__(
        self,
        cache,
        *,
        live_fetch: bool | None = None,
        registry: dict[str, dict[str, str]] | None = None,
        registry_path: Path | None = None,
    ) -> None:
        super().__init__(cache, live_fetch=live_fetch)
        if registry is not None:
            self._registry = dict(registry)
        else:
            self._registry = _load_funcion_publica_registry(
                registry_path or _REGISTRY_PATH
            )
        self._articles_dict_cache: dict[str, dict[str, str]] = {}
        self._articles_dict_lock = threading.Lock()

    # ------------------------------------------------------------------
    # Hook implementations required by the base class
    # ------------------------------------------------------------------

    def _resolve_url(self, norm_id: str) -> str | None:
        """Map ``norm_id`` to its parent Función Pública URL."""

        parent_id = _canonical_parent_id(norm_id)
        entry = self._registry.get(parent_id)
        if entry is None:
            return None
        return entry.get("ruta") or None

    def _parse_html(self, content: bytes) -> tuple[str, dict[str, Any]]:
        """Whole-doc plaintext + per-article slice dict in meta."""

        html_str = content.decode("utf-8", errors="ignore")
        text = _html_to_text(html_str)
        articles_dict = _extract_articles_dict(html_str)
        meta: dict[str, Any] = {}
        if articles_dict:
            meta["articles"] = articles_dict
            meta["article_count"] = len(articles_dict)
        return text, meta

    def _http_get(self, url: str) -> tuple[bytes, int, str | None]:
        """Override the base class HTTP path to use truststore SSL.

        The base class uses certifi, whose 2026.02.25 bundle doesn't
        include the Sectigo intermediate Función Pública's cert chains
        through. truststore (OS Keychain) does.
        """

        import time
        import urllib.error
        import urllib.request

        ctx = _fp_ssl_context()
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 "
                    "Safari/537.36 Lia-Graph/1.0 (compliance scraper)"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
            },
        )
        last_err: Exception | None = None
        for attempt, backoff in enumerate((0, 2, 6)):
            if backoff:
                time.sleep(backoff)
            try:
                with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
                    content = resp.read()
                    status_code = int(resp.status)
                    content_type = resp.headers.get("Content-Type")
                return content, status_code, content_type
            except urllib.error.HTTPError as err:
                if 500 <= err.code < 600 and attempt < 2:
                    last_err = err
                    LOGGER.info(
                        "Función Pública %d on %s — retry %d/3",
                        err.code, url, attempt + 2,
                    )
                    continue
                raise
            except (urllib.error.URLError, TimeoutError, OSError) as err:
                last_err = err
                if attempt < 2:
                    LOGGER.info(
                        "Función Pública transient %s on %s — retry %d/3",
                        type(err).__name__, url, attempt + 2,
                    )
                    continue
                raise
        raise last_err  # type: ignore[misc]

    # ------------------------------------------------------------------
    # Public override — same shape as SuinJuriscolScraper
    # ------------------------------------------------------------------

    def fetch(self, norm_id: str) -> ScraperFetchResult | None:
        parent_id = _canonical_parent_id(norm_id)
        entry = self._registry.get(parent_id)
        if entry is None:
            return None
        url = entry.get("ruta")
        if not url:
            return None
        fp_doc_id = str(entry.get("funcion_publica_doc_id") or "")

        cache_entry, cache_hit = self._materialize_cache_entry(norm_id, url)
        if cache_entry is None:
            return None

        article_key = _article_key_from_norm_id(norm_id)
        if article_key is None:
            return ScraperFetchResult(
                norm_id=norm_id,
                source=self.source_id,
                url=url,
                fetched_at_utc=cache_entry.fetched_at_utc,
                status_code=cache_entry.status_code,
                parsed_text=cache_entry.parsed_text or "",
                parsed_meta={
                    **dict(cache_entry.parsed_meta or {}),
                    "funcion_publica_doc_id": fp_doc_id,
                },
                cache_hit=cache_hit,
            )

        articles_dict = self._articles_dict_for_url(
            url=url,
            cache_entry=cache_entry,
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
                "funcion_publica_doc_id": fp_doc_id,
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
        """SQLite cache → live HTTP → populate cache + return entry."""

        cached = self.cache.get(self.source_id, url)
        if cached is not None:
            return cached, True

        if not self.live_fetch:
            return None, False

        # Live HTTP fetch via the base class's _http_get (certifi-backed).
        self._throttle()
        try:
            content, status_code, content_type = self._http_get(url)
        except Exception as err:
            LOGGER.warning("Función Pública fetch failed for %s: %s", url, err)
            return None, False

        parsed_text, parsed_meta = self._parse_html(content)
        try:
            self.cache.put(
                source=self.source_id,
                url=url,
                content=content,
                status_code=status_code,
                canonical_norm_id=norm_id,
                content_type=content_type,
                parsed_text=parsed_text,
                parsed_meta=parsed_meta,
            )
        except Exception as err:
            LOGGER.info("Función Pública cache write failed (%s): %s", url, err)
            return (
                CacheEntry(
                    source=self.source_id,
                    url=url,
                    canonical_norm_id=norm_id,
                    fetched_at_utc=datetime.now(timezone.utc).isoformat(),
                    status_code=status_code,
                    content_sha256=hashlib.sha256(content).hexdigest(),
                    content=content,
                    content_type=content_type,
                    parsed_text=parsed_text,
                    parsed_meta=parsed_meta,
                ),
                False,
            )
        new_entry = self.cache.get(self.source_id, url)
        return new_entry, False

    def _articles_dict_for_url(
        self,
        *,
        url: str,
        cache_entry: CacheEntry,
    ) -> dict[str, str] | None:
        """Return persisted slice dict (per-process LRU on top of SQLite)."""

        with self._articles_dict_lock:
            cached = self._articles_dict_cache.get(url)
            if cached is not None:
                return cached

        meta = dict(cache_entry.parsed_meta or {})
        articles_obj = meta.get("articles")
        if isinstance(articles_obj, dict) and articles_obj:
            articles_dict = {str(k): str(v) for k, v in articles_obj.items()}
            with self._articles_dict_lock:
                self._articles_dict_cache[url] = articles_dict
            return articles_dict

        # Legacy row without persisted slices — extract from cached HTML
        # and lazy-backfill the SQLite parsed_meta.
        html_str = (cache_entry.content or b"").decode("utf-8", errors="ignore")
        articles_dict = _extract_articles_dict(html_str)
        if not articles_dict:
            return None

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
            LOGGER.debug("Función Pública parsed_meta backfill failed (%s): %s", url, err)

        with self._articles_dict_lock:
            self._articles_dict_cache[url] = articles_dict
        return articles_dict


__all__ = [
    "FuncionPublicaScraper",
    "_load_funcion_publica_registry",
    "_extract_articles_dict",
    "_slice_from_articles_dict",
]
