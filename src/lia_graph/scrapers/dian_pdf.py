"""Scraper for DIAN's `/normatividad/Normatividad/*.pdf` resoluciones (next_v7 P2).

DIAN publishes its modern resoluciones (2020+) as PDF files under the
predictable path::

    https://www.dian.gov.co/normatividad/Normatividad/Resolución <NNNNNN> de <DD-MM-YYYY>.pdf

Closes the F2 gap (`res.dian.13.2021.art.*` and similar) that SUIN,
Senado, Función Pública, and DIAN normograma cannot serve. URL
resolution depends on the registry built by
`scripts/canonicalizer/build_dian_pdf_registry.py` (`var/dian_pdf_registry.json`).

Architecture mirrors `FuncionPublicaScraper`:

1. Canonical-norm-id → DIAN PDF URL via the registry.
2. Three-tier cache: SQLite cache → live HTTP via certifi+truststore SSL
   (only when `live_fetch=True`).
3. Per-article slicing using ``pypdf.PdfReader.extract_text()`` plus a
   regex split on ``^ART[IÍ]CULO + digit-run`` headings. Slices persist
   in ``parsed_meta["articles"]``.

Per-source operational notes: `docs/learnings/sites/dian-main.md`.
"""

from __future__ import annotations

import hashlib
import io
import json
import logging
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lia_graph.scrapers.base import Scraper, ScraperFetchResult
from lia_graph.scrapers.cache import CacheEntry
from lia_graph.scrapers.suin_juriscol import (
    _article_key_from_norm_id,
    _canonical_parent_id,
)


LOGGER = logging.getLogger(__name__)


_DIAN_PDF_REGISTRY_PATH = Path("var/dian_pdf_registry.json")


_DIAN_PDF_SSL_CONTEXT: Any = None


def _dian_pdf_ssl_context() -> Any:
    """SSL context that delegates to the OS Keychain via truststore.

    DIAN's cert chain occasionally includes intermediates not present
    in certifi's bundle. Same pattern as the Función Pública scraper.
    """

    global _DIAN_PDF_SSL_CONTEXT
    if _DIAN_PDF_SSL_CONTEXT is not None:
        return _DIAN_PDF_SSL_CONTEXT
    import ssl
    try:
        import truststore  # type: ignore
        _DIAN_PDF_SSL_CONTEXT = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        return _DIAN_PDF_SSL_CONTEXT
    except ImportError:
        from lia_graph.scrapers.base import _ssl_context_with_certifi
        _DIAN_PDF_SSL_CONTEXT = _ssl_context_with_certifi()
        return _DIAN_PDF_SSL_CONTEXT


# ---------------------------------------------------------------------------
# Registry helpers
# ---------------------------------------------------------------------------


def _load_dian_pdf_registry(
    path: Path = _DIAN_PDF_REGISTRY_PATH,
) -> dict[str, dict[str, str]]:
    """Read ``var/dian_pdf_registry.json``. Empty dict if missing."""

    if not path.is_file():
        LOGGER.info(
            "DIAN PDF registry %s missing — scraper will resolve no URLs. "
            "Build via scripts/canonicalizer/build_dian_pdf_registry.py.",
            path,
        )
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as err:
        LOGGER.warning("DIAN PDF registry load failed (%s): %s", path, err)
        return {}


# ---------------------------------------------------------------------------
# PDF parsing helpers
# ---------------------------------------------------------------------------


_ARTICLE_HEADING_RX = re.compile(
    # Matches start-of-line "ARTÍCULO N", "ARTICULO N", "Artículo N",
    # optional grados/parágrafo annotations after the digits. Returns
    # the article number for grouping.
    r"^[ \t]*ART[IÍ]CULO\s+(\d+)\b",
    re.MULTILINE | re.IGNORECASE,
)


def _extract_text_from_pdf(content: bytes) -> str:
    """Best-effort plaintext extraction. Returns "" on parse failure."""

    if not content:
        return ""
    try:
        from pypdf import PdfReader
    except ImportError:
        LOGGER.warning("pypdf not installed — DIAN PDF scraper cannot parse")
        return ""
    try:
        reader = PdfReader(io.BytesIO(content))
        chunks = []
        for page in reader.pages:
            try:
                chunks.append(page.extract_text() or "")
            except Exception as err:
                LOGGER.debug("page extract failed: %s", err)
        return "\n".join(chunks)
    except Exception as err:
        LOGGER.warning("pypdf parse failed: %s", err)
        return ""


def _extract_articles_dict(text: str) -> dict[str, str]:
    """Slice the plaintext into ``{article_number: body_text}``.

    Returns an empty dict when no article headings match. First-occurrence
    wins on duplicate article numbers (some DIAN PDFs include footers
    that re-mention article numbers).
    """

    if not text:
        return {}
    matches = list(_ARTICLE_HEADING_RX.finditer(text))
    if not matches:
        return {}
    out: dict[str, str] = {}
    for i, m in enumerate(matches):
        art_num = m.group(1)
        if art_num in out:
            continue  # first-occurrence wins
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if body:
            out[art_num] = body
    return out


def _slice_from_articles_dict(
    articles_dict: dict[str, str] | None,
    article_key: str | None,
) -> str | None:
    """Return the body for the requested article key, or None."""

    if not articles_dict or not article_key:
        return None
    # Article keys for DIAN resoluciones are typically simple integers; if
    # the canonical id has dotted sub-numbering (rare for resoluciones),
    # take the leading integer.
    target = article_key.split(".", 1)[0]
    return articles_dict.get(target)


# ---------------------------------------------------------------------------
# Scraper
# ---------------------------------------------------------------------------


class DianPdfScraper(Scraper):
    """DIAN PDF resoluciones scraper — closes the F2 gap.

    Lookup order (mirrors FP / SUIN scrapers):
    1. ``self.cache.get(source_id, url)`` — SQLite cache.
    2. Live HTTPS via truststore-backed SSL — only when ``live_fetch=True``.

    Per-article slicing happens at fetch time. Slices persist in
    ``parsed_meta["articles"]`` so parallel processes share them.
    """

    source_id = "dian_pdf"
    rate_limit_seconds = 1.0  # DIAN main is small; be polite.
    _handled_types = {
        "resolucion", "res_articulo",
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
            self._registry = _load_dian_pdf_registry(
                registry_path or _DIAN_PDF_REGISTRY_PATH
            )
        self._articles_dict_cache: dict[str, dict[str, str]] = {}
        self._articles_dict_lock = threading.Lock()

    def handles(self, norm_type_value: str, norm_id: str) -> bool:  # noqa: D401
        # Limit to res.dian.* — other resoluciones live on different sites.
        if norm_type_value not in self._handled_types:
            return False
        return norm_id.startswith("res.dian.")

    # ------------------------------------------------------------------
    # Hook implementations required by the base class
    # ------------------------------------------------------------------

    def _resolve_url(self, norm_id: str) -> str | None:
        parent_id = _canonical_parent_id(norm_id)
        entry = self._registry.get(parent_id)
        if entry is None:
            return None
        return entry.get("url") or None

    def _parse_html(self, content: bytes) -> tuple[str, dict[str, Any]]:
        """Despite the method name, this is PDF content. Returns text + slice meta."""

        text = _extract_text_from_pdf(content)
        articles_dict = _extract_articles_dict(text)
        meta: dict[str, Any] = {}
        if articles_dict:
            meta["articles"] = articles_dict
            meta["article_count"] = len(articles_dict)
        return text, meta

    def _http_get(self, url: str) -> tuple[bytes, int, str | None]:
        """Override the base HTTP path to use truststore SSL + browser UA.

        DIAN PDF URLs include raw spaces and the literal ``ó`` character
        in the filename; urllib refuses them as-is. We percent-encode
        the path component (preserving the scheme/netloc) before issuing
        the request.
        """

        import time
        import urllib.error
        import urllib.parse
        import urllib.request

        # Quote only the path; leave scheme/netloc/query untouched.
        parsed = urllib.parse.urlsplit(url)
        safe_path = urllib.parse.quote(parsed.path, safe="/")
        encoded_url = urllib.parse.urlunsplit(
            (parsed.scheme, parsed.netloc, safe_path, parsed.query, parsed.fragment)
        )

        ctx = _dian_pdf_ssl_context()
        req = urllib.request.Request(
            encoded_url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 "
                    "Safari/537.36 Lia-Graph/1.0 (compliance scraper)"
                ),
                "Accept": "application/pdf,*/*;q=0.8",
                "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
            },
        )
        last_err: Exception | None = None
        for attempt, backoff in enumerate((0, 2, 6)):
            if backoff:
                time.sleep(backoff)
            try:
                with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
                    content = resp.read()
                    status_code = int(resp.status)
                    content_type = resp.headers.get("Content-Type")
                return content, status_code, content_type
            except urllib.error.HTTPError as err:
                if 500 <= err.code < 600 and attempt < 2:
                    last_err = err
                    LOGGER.info("DIAN PDF %d on %s — retry %d/3", err.code, url, attempt + 2)
                    continue
                raise
            except (urllib.error.URLError, TimeoutError, OSError) as err:
                last_err = err
                if attempt < 2:
                    LOGGER.info("DIAN PDF transient %s on %s — retry %d/3", type(err).__name__, url, attempt + 2)
                    continue
                raise
        raise last_err  # type: ignore[misc]

    # ------------------------------------------------------------------
    # Public override — same shape as FP / SUIN scrapers
    # ------------------------------------------------------------------

    def fetch(self, norm_id: str) -> ScraperFetchResult | None:
        parent_id = _canonical_parent_id(norm_id)
        entry = self._registry.get(parent_id)
        if entry is None:
            return None
        url = entry.get("url")
        if not url:
            return None

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
                    "dian_pdf_number": entry.get("number") or "",
                    "dian_pdf_date": entry.get("date") or "",
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
                "dian_pdf_number": entry.get("number") or "",
                "dian_pdf_date": entry.get("date") or "",
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

        self._throttle()
        try:
            content, status_code, content_type = self._http_get(url)
        except Exception as err:
            LOGGER.warning("DIAN PDF fetch failed for %s: %s", url, err)
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
            LOGGER.info("DIAN PDF cache write failed (%s): %s", url, err)
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

        # Legacy row without persisted slices — extract from cached PDF
        # bytes and lazy-backfill the SQLite parsed_meta.
        text = _extract_text_from_pdf(cache_entry.content or b"")
        articles_dict = _extract_articles_dict(text)
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
            LOGGER.debug("DIAN PDF parsed_meta backfill failed (%s): %s", url, err)

        with self._articles_dict_lock:
            self._articles_dict_cache[url] = articles_dict
        return articles_dict


__all__ = [
    "DianPdfScraper",
    "_load_dian_pdf_registry",
    "_extract_text_from_pdf",
    "_extract_articles_dict",
]
