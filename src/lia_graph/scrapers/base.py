"""Common scraper protocol — fixplan_v3 sub-fix 1B-α.

Every primary-source scraper implements this interface. The skill harness
calls `ScraperRegistry.fetch(norm_id)` and the registry routes to the
right scraper based on `norm_type` + `norm_id` prefix.

Live HTTP fetching is gated by `LIA_LIVE_SCRAPER_TESTS=1`. In dev / CI,
scrapers run against fixtures in `tests/fixtures/scrapers/<source>/<url-hash>.bin`.
"""

from __future__ import annotations

import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from lia_graph.canon import norm_type as canon_norm_type
from lia_graph.scrapers.cache import CacheEntry, ScraperCache

LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result shapes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScraperFetchResult:
    """The skill consumes this — text + structured metadata + provenance."""

    norm_id: str
    source: str
    url: str
    fetched_at_utc: str
    status_code: int
    parsed_text: str
    parsed_meta: Mapping[str, Any]
    cache_hit: bool = False


# ---------------------------------------------------------------------------
# Base scraper
# ---------------------------------------------------------------------------


class Scraper(ABC):
    """Implement `_resolve_url` + `_parse_html` for each source."""

    source_id: str = ""  # set by subclasses
    rate_limit_seconds: float = 0.5  # 2 req/sec default per fixplan_v3 §2.2

    def __init__(
        self,
        cache: ScraperCache,
        *,
        live_fetch: bool | None = None,
    ) -> None:
        if not self.source_id:
            raise ValueError(
                f"{type(self).__name__} must set class attribute `source_id`"
            )
        self.cache = cache
        # Default: live fetch only when LIA_LIVE_SCRAPER_TESTS=1.
        if live_fetch is None:
            live_fetch = os.getenv("LIA_LIVE_SCRAPER_TESTS", "0") == "1"
        self.live_fetch = bool(live_fetch)
        self._last_fetch_ts: float = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch(self, norm_id: str) -> ScraperFetchResult | None:
        """Return cached or freshly-fetched content for `norm_id`."""

        url = self._resolve_url(norm_id)
        if url is None:
            return None
        cached = self.cache.get(self.source_id, url)
        if cached:
            return _entry_to_result(norm_id, cached, cache_hit=True)
        if not self.live_fetch:
            LOGGER.debug(
                "Cache miss for %s (%s) and live_fetch disabled — returning None",
                norm_id,
                url,
            )
            return None
        # Live fetch path. Throttle.
        self._throttle()
        try:
            content, status_code, content_type = self._http_get(url)
        except Exception as err:
            LOGGER.warning("HTTP fetch failed for %s: %s", url, err)
            return None
        parsed_text, parsed_meta = self._parse_html(content)
        self.cache.put(
            source=self.source_id,
            url=url,
            content=content,
            status_code=status_code,
            content_type=content_type,
            canonical_norm_id=norm_id,
            parsed_text=parsed_text,
            parsed_meta=parsed_meta,
        )
        new_entry = self.cache.get(self.source_id, url)
        if new_entry is None:
            return None
        return _entry_to_result(norm_id, new_entry, cache_hit=False)

    # ------------------------------------------------------------------
    # Subclass hooks
    # ------------------------------------------------------------------

    @abstractmethod
    def _resolve_url(self, norm_id: str) -> str | None:
        """Map a canonical norm_id to its primary-source URL on this site."""

    @abstractmethod
    def _parse_html(self, content: bytes) -> tuple[str, dict[str, Any]]:
        """Extract plaintext + structured metadata from raw HTML/PDF content."""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _http_get(self, url: str) -> tuple[bytes, int, str | None]:
        """Live HTTP GET. Stdlib only — no external requests dep."""

        import urllib.request

        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Lia-Graph/1.0 (compliance scraper)"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read()
            status_code = int(resp.status)
            content_type = resp.headers.get("Content-Type")
        return content, status_code, content_type

    def _throttle(self) -> None:
        delta = time.monotonic() - self._last_fetch_ts
        if delta < self.rate_limit_seconds:
            time.sleep(self.rate_limit_seconds - delta)
        self._last_fetch_ts = time.monotonic()


def _entry_to_result(
    norm_id: str,
    entry: CacheEntry,
    *,
    cache_hit: bool,
) -> ScraperFetchResult:
    return ScraperFetchResult(
        norm_id=norm_id,
        source=entry.source,
        url=entry.url,
        fetched_at_utc=entry.fetched_at_utc,
        status_code=entry.status_code,
        parsed_text=entry.parsed_text or "",
        parsed_meta=entry.parsed_meta,
        cache_hit=cache_hit,
    )


# ---------------------------------------------------------------------------
# Registry — routes a norm_id to the right scraper(s)
# ---------------------------------------------------------------------------


class ScraperRegistry:
    """Maps `norm_id` → the scrapers that can fetch its primary source.

    A single norm typically has 2+ primary sources (per the skill's double-
    primary-source rule). The registry returns ALL applicable scrapers; the
    harness picks the strongest two per `references/fuentes-primarias.md`.
    """

    def __init__(self, scrapers: Iterable[Scraper]) -> None:
        self._scrapers: list[Scraper] = list(scrapers)

    def for_norm(self, norm_id: str) -> Sequence[Scraper]:
        nt = canon_norm_type(norm_id)
        return [s for s in self._scrapers if s.handles(nt, norm_id)]

    def fetch_all(self, norm_id: str) -> list[ScraperFetchResult]:
        out: list[ScraperFetchResult] = []
        for s in self.for_norm(norm_id):
            res = s.fetch(norm_id)
            if res is not None:
                out.append(res)
        return out


# Helper protocol the registry expects on each scraper. We attach it via a
# default implementation on Scraper (subclasses can override).
def _default_handles(self: Scraper, norm_type_value: str, norm_id: str) -> bool:  # noqa: D401
    """Default: a scraper handles a norm if its source-id is in `_handled_types`."""

    handled = getattr(self, "_handled_types", set())
    return norm_type_value in handled


Scraper.handles = _default_handles  # type: ignore[attr-defined]


__all__ = ["Scraper", "ScraperFetchResult", "ScraperRegistry"]
