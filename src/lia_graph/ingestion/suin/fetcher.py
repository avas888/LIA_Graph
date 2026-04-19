"""SUIN HTTP fetcher — cached, rate-limited, robots-aware."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import logging
import os
from pathlib import Path
import time
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
from xml.etree import ElementTree as ET

import httpx

_log = logging.getLogger(__name__)


SUIN_BASE = "https://www.suin-juriscol.gov.co/"
_DEFAULT_UA = "LIA-IngestionBot/1.0 (+mailto:avasqueza@gmail.com)"
_DEFAULT_CACHE_DIR = Path("cache/suin")
_DEFAULT_RPS = 1.0
_DEFAULT_TIMEOUT = 30.0
_MAX_RETRIES = 4


class SuinFetchError(RuntimeError):
    """Raised when SUIN returns a non-recoverable error or robots disallows."""


@dataclass(frozen=True)
class SitemapEntry:
    """One row of the `SITEMAPS` table — name + URL + required flag."""

    name: str
    url: str
    required: bool = True


SITEMAPS: tuple[SitemapEntry, ...] = (
    SitemapEntry("leyes", urljoin(SUIN_BASE, "sitemapleyes.xml"), required=True),
    SitemapEntry("consejoestado", urljoin(SUIN_BASE, "sitemapconsejoestado.xml"), required=False),
    SitemapEntry("circular", urljoin(SUIN_BASE, "sitemapcircular.xml"), required=False),
    SitemapEntry("instruccion", urljoin(SUIN_BASE, "sitemapinstruccion.xml"), required=False),
    SitemapEntry("acuerdo", urljoin(SUIN_BASE, "sitemapacuerdo.xml"), required=False),
)


# Spine documents per scope. Each URL is an absolute SUIN document URL that must
# be reached regardless of sitemap content — seeds are emitted *before* the
# sitemap walk so the primary norms always land in cache.
#
# Policy (2026-04-19): forward-from-today, not ancestor-chain. We seed with
# currently-vigente consolidated spines (ET, CST, Ley 100, DURs) + the
# recent reforms whose own text isn't yet absorbed into those spines (Ley
# 2466/2025, 2381/2024, 2277/2022). Historical reforms (Ley 1607/2012,
# 1819/2016, etc.) are NOT seeded — SUIN's consolidated spine docs carry
# their modification chain via NotasDestino blocks, which the two-pass
# merge stub-resolves for free. An accountant never reads the old reform
# texts directly.
#
# The `laboral-tributario` scope is used as the single high-value entry
# point: all 9 spine URLs live here so one capped crawl (Phase 2)
# produces the full corpus the downstream retriever needs. Phases 3/4
# would re-crawl the same cached docs (no-op) so they are collapsed into
# Phase 2; see `docs/next/suin_harvestv1.md` state tracker for the
# rationale.
SEED_URLS: dict[str, tuple[str, ...]] = {
    "tributario": (
        "https://www.suin-juriscol.gov.co/viewDocument.asp?id=1132325",   # Decreto 624/1989 (ET)
        "https://www.suin-juriscol.gov.co/viewDocument.asp?id=30030361",  # Decreto 1625/2016 (DUR Tributario)
        "https://www.suin-juriscol.gov.co/viewDocument.asp?id=30045028",  # Ley 2277/2022 (reforma tributaria)
    ),
    "laboral": (
        "https://www.suin-juriscol.gov.co/viewDocument.asp?id=1874133",   # Decreto 2663/1950 (CST — origen)
        "https://www.suin-juriscol.gov.co/viewDocument.asp?id=30019323",  # Código Sustantivo del Trabajo (consolidado)
        "https://www.suin-juriscol.gov.co/viewDocument.asp?id=1635955",   # Ley 100/1993 (SGSSS)
        "https://www.suin-juriscol.gov.co/viewDocument.asp?id=30019522",  # Decreto 1072/2015 (DUR Trabajo)
        "https://www.suin-juriscol.gov.co/viewDocument.asp?id=30055086",  # Ley 2466/2025 (reforma laboral)
        "https://www.suin-juriscol.gov.co/viewDocument.asp?id=30051782",  # Ley 2381/2024 (reforma pensional)
    ),
    "laboral-tributario": (
        # Full 9-seed union — this scope drives the collapsed Phase 2 harvest.
        "https://www.suin-juriscol.gov.co/viewDocument.asp?id=1132325",   # Decreto 624/1989 (ET)
        "https://www.suin-juriscol.gov.co/viewDocument.asp?id=1874133",   # Decreto 2663/1950 (CST — origen)
        "https://www.suin-juriscol.gov.co/viewDocument.asp?id=30019323",  # CST (consolidado)
        "https://www.suin-juriscol.gov.co/viewDocument.asp?id=1635955",   # Ley 100/1993
        "https://www.suin-juriscol.gov.co/viewDocument.asp?id=30019522",  # DUR 1072/2015
        "https://www.suin-juriscol.gov.co/viewDocument.asp?id=30030361",  # DUR 1625/2016
        "https://www.suin-juriscol.gov.co/viewDocument.asp?id=30055086",  # Ley 2466/2025
        "https://www.suin-juriscol.gov.co/viewDocument.asp?id=30051782",  # Ley 2381/2024
        "https://www.suin-juriscol.gov.co/viewDocument.asp?id=30045028",  # Ley 2277/2022
    ),
    "jurisprudencia": (),  # Uses sitemapconsejoestado.xml walk; deferred (see "explore later")
}


@dataclass
class _CacheManifestRow:
    url: str
    sha1: str
    fetched_at: str
    etag: str | None = None
    status: int = 200

    def to_json(self) -> str:
        return json.dumps(
            {
                "url": self.url,
                "sha1": self.sha1,
                "fetched_at": self.fetched_at,
                "etag": self.etag,
                "status": self.status,
            },
            ensure_ascii=False,
        )


@dataclass
class SuinFetcher:
    """HTTP client for SUIN with robots-respect, rate limit, retry, disk cache.

    Construct via keyword args, use `fetch(url)` for individual docs,
    `iter_sitemap(url)` for sitemap walks, and `close()` (or context manager) to
    release the underlying httpx.Client.
    """

    user_agent: str = _DEFAULT_UA
    cache_dir: Path = field(default_factory=lambda: _DEFAULT_CACHE_DIR)
    rps: float = _DEFAULT_RPS
    timeout: float = _DEFAULT_TIMEOUT
    transport: httpx.BaseTransport | None = None

    _client: httpx.Client | None = field(default=None, init=False, repr=False)
    _last_request_at: float = field(default=0.0, init=False, repr=False)
    _robots_by_host: dict[str, RobotFileParser | None] = field(
        default_factory=dict, init=False, repr=False
    )

    def __post_init__(self) -> None:
        env_rps = os.environ.get("LIA_SUIN_RPS", "").strip()
        if env_rps:
            try:
                self.rps = max(0.1, float(env_rps))
            except ValueError:
                _log.warning("LIA_SUIN_RPS=%r is not numeric — ignoring", env_rps)
        self.cache_dir = Path(self.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    # ---- lifecycle ---------------------------------------------------------

    def _ensure_client(self) -> httpx.Client:
        if self._client is None:
            headers = {"User-Agent": self.user_agent, "Accept": "text/html, application/xml;q=0.9, */*;q=0.8"}
            kwargs: dict[str, object] = {
                "headers": headers,
                "timeout": self.timeout,
                "follow_redirects": True,
            }
            if self.transport is not None:
                kwargs["transport"] = self.transport
            else:
                # SUIN (suin-juriscol.gov.co) serves a Sectigo cert without
                # shipping the intermediate during the TLS handshake. curl on
                # macOS works via Keychain's AIA fetch; Python's default SSL
                # context does not. `truststore` delegates verification to the
                # OS trust store, matching curl's behavior. Fall back silently
                # if `truststore` is unavailable (e.g. Linux without
                # truststore-compatible libs).
                import ssl as _ssl

                try:
                    import truststore  # type: ignore

                    kwargs["verify"] = truststore.SSLContext(_ssl.PROTOCOL_TLS_CLIENT)
                except ImportError:
                    pass
            self._client = httpx.Client(**kwargs)
        return self._client

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> "SuinFetcher":
        self._ensure_client()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    # ---- public API --------------------------------------------------------

    def fetch(self, url: str) -> str:
        """Return HTML/XML text for `url`, using cache if fresh and permitted."""
        self._enforce_robots(url)
        cache_path = self._cache_path(url)
        if cache_path.exists():
            return cache_path.read_text(encoding="utf-8")
        text = self._fetch_with_retry(url)
        cache_path.write_text(text, encoding="utf-8")
        self._append_manifest(_CacheManifestRow(
            url=url,
            sha1=self._sha1(url),
            fetched_at=datetime.now(tz=timezone.utc).isoformat(),
        ))
        return text

    def iter_seeds(self, scope: str) -> Iterator[str]:
        """Yield the scope's spine seed URLs in declaration order.

        Scope name resolution follows the alias table — passing `et` returns the
        seeds of `tributario`. Unknown scopes yield nothing (caller decides).
        """
        seeds = SEED_URLS.get(scope)
        if seeds is None and scope == "et":
            seeds = SEED_URLS.get("tributario", ())
        for url in seeds or ():
            yield url

    def iter_sitemap(self, sitemap_url: str) -> Iterator[str]:
        """Yield every document URL reachable from a sitemap (recursive)."""
        stack = [sitemap_url]
        seen: set[str] = set()
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            xml = self.fetch(current)
            try:
                root = ET.fromstring(xml)
            except ET.ParseError as exc:
                raise SuinFetchError(f"malformed XML at {current}: {exc}") from exc
            tag = _localname(root.tag)
            if tag == "sitemapindex":
                for loc in root.iter():
                    if _localname(loc.tag) == "loc" and loc.text:
                        stack.append(loc.text.strip())
            elif tag == "urlset":
                for loc in root.iter():
                    if _localname(loc.tag) == "loc" and loc.text:
                        yield loc.text.strip()
            else:
                raise SuinFetchError(f"unknown sitemap root <{root.tag}> at {current}")

    # ---- internals ---------------------------------------------------------

    def _enforce_robots(self, url: str) -> None:
        host = urlparse(url).netloc
        if host not in self._robots_by_host:
            self._robots_by_host[host] = self._load_robots(host)
        parser = self._robots_by_host[host]
        if parser is None:
            return
        if not parser.can_fetch(self.user_agent, url):
            raise SuinFetchError(f"robots.txt disallows {url}")

    def _load_robots(self, host: str) -> RobotFileParser | None:
        if not host:
            return None
        robots_url = f"https://{host}/robots.txt"
        client = self._ensure_client()
        try:
            response = client.get(robots_url)
        except httpx.HTTPError:
            _log.info("robots.txt unreachable at %s — proceeding", robots_url)
            return None
        if response.status_code >= 400:
            return None
        parser = RobotFileParser()
        parser.parse(response.text.splitlines())
        return parser

    def _fetch_with_retry(self, url: str) -> str:
        client = self._ensure_client()
        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            self._rate_limit()
            try:
                response = client.get(url)
            except httpx.HTTPError as exc:
                last_exc = exc
                _log.warning("SUIN fetch error %s attempt %d: %s", url, attempt + 1, exc)
            else:
                if response.status_code == 200:
                    return response.text
                if response.status_code in {429, 500, 502, 503, 504}:
                    last_exc = SuinFetchError(
                        f"transient {response.status_code} on {url}"
                    )
                    _log.warning(
                        "SUIN transient %s on %s — retry %d", response.status_code, url, attempt + 1
                    )
                else:
                    raise SuinFetchError(
                        f"{response.status_code} on {url} — non-retriable"
                    )
            time.sleep(min(30.0, (2 ** attempt) * 0.5))
        raise SuinFetchError(f"exceeded retries on {url}: {last_exc}")

    def _rate_limit(self) -> None:
        if self.rps <= 0:
            return
        min_interval = 1.0 / self.rps
        delta = time.monotonic() - self._last_request_at
        if delta < min_interval:
            time.sleep(min_interval - delta)
        self._last_request_at = time.monotonic()

    def _cache_path(self, url: str) -> Path:
        return self.cache_dir / f"{self._sha1(url)}.html"

    @staticmethod
    def _sha1(url: str) -> str:
        return hashlib.sha1(url.encode("utf-8")).hexdigest()

    def _append_manifest(self, row: _CacheManifestRow) -> None:
        manifest = self.cache_dir / "_manifest.jsonl"
        with manifest.open("a", encoding="utf-8") as handle:
            handle.write(row.to_json() + "\n")


def _localname(tag: str) -> str:
    """Strip XML namespace from a tag: `{ns}sitemapindex` → `sitemapindex`."""
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def iter_document_urls(
    fetcher: SuinFetcher,
    sitemaps: Iterable[SitemapEntry] = SITEMAPS,
) -> Iterator[str]:
    """Walk every configured sitemap in order; required ones fail loud."""
    for entry in sitemaps:
        try:
            yield from fetcher.iter_sitemap(entry.url)
        except SuinFetchError as exc:
            if entry.required:
                raise
            _log.warning("optional sitemap %s failed: %s", entry.name, exc)


__all__ = [
    "SEED_URLS",
    "SITEMAPS",
    "SitemapEntry",
    "SuinFetcher",
    "SuinFetchError",
    "iter_document_urls",
]
