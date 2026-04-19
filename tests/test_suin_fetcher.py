"""SUIN fetcher tests — all network calls go through an httpx.MockTransport.

We never talk to real SUIN during tests. The fixtures verify:

- robots.txt disallow fails loud (no cached HTML, no manifest row).
- Rate limit is enforced across back-to-back calls.
- 2xx responses are cached to disk; the second call never hits the transport.
- 5xx bodies retry with backoff and eventually succeed.
"""

from __future__ import annotations

from pathlib import Path
import time
from urllib.parse import urlparse

import httpx
import pytest

from lia_graph.ingestion.suin import harvest as harvest_mod
from lia_graph.ingestion.suin.fetcher import (
    SEED_URLS,
    SITEMAPS,
    SuinFetcher,
    SuinFetchError,
)


class _Recorder:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def add(self, url: str) -> None:
        self.calls.append(url)


def _transport(
    handler,
) -> httpx.MockTransport:
    return httpx.MockTransport(handler)


def test_respects_robots_disallow(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(
                200,
                text="User-agent: *\nDisallow: /blocked\n",
            )
        return httpx.Response(200, text="<html></html>")

    fetcher = SuinFetcher(
        cache_dir=tmp_path / "cache",
        rps=10.0,
        transport=_transport(handler),
    )
    with fetcher:
        with pytest.raises(SuinFetchError):
            fetcher.fetch("https://www.suin-juriscol.gov.co/blocked/doc?id=1")


def test_rate_limit_enforced(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        return httpx.Response(200, text="<html>ok</html>")

    # 5 rps → each fetch must be ≥0.2s apart. 3 fetches must exceed 0.4s total.
    fetcher = SuinFetcher(
        cache_dir=tmp_path / "cache",
        rps=5.0,
        transport=_transport(handler),
    )
    start = time.monotonic()
    with fetcher:
        fetcher.fetch("https://www.suin-juriscol.gov.co/doc1")
        fetcher.fetch("https://www.suin-juriscol.gov.co/doc2")
        fetcher.fetch("https://www.suin-juriscol.gov.co/doc3")
    elapsed = time.monotonic() - start
    assert elapsed >= 0.4, f"rate limit not enforced: {elapsed=:.3f}s"


def test_cache_hit_avoids_refetch(tmp_path: Path) -> None:
    rec = _Recorder()

    def handler(request: httpx.Request) -> httpx.Response:
        rec.add(str(request.url))
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        return httpx.Response(200, text="<html>cached</html>")

    fetcher = SuinFetcher(
        cache_dir=tmp_path / "cache",
        rps=50.0,
        transport=_transport(handler),
    )
    target = "https://www.suin-juriscol.gov.co/doc?id=42"
    with fetcher:
        first = fetcher.fetch(target)
        second = fetcher.fetch(target)
    assert first == second == "<html>cached</html>"
    # Only the first fetch (+ robots) should hit the transport.
    hits = [url for url in rec.calls if url == target]
    assert len(hits) == 1, rec.calls


def test_5xx_backoff_then_succeed(tmp_path: Path) -> None:
    attempts: dict[str, int] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        attempts.setdefault(str(request.url), 0)
        attempts[str(request.url)] += 1
        if attempts[str(request.url)] < 3:
            return httpx.Response(503, text="")
        return httpx.Response(200, text="<html>recovered</html>")

    fetcher = SuinFetcher(
        cache_dir=tmp_path / "cache",
        rps=100.0,
        transport=_transport(handler),
    )
    with fetcher:
        text = fetcher.fetch("https://www.suin-juriscol.gov.co/doc?id=99")
    assert text == "<html>recovered</html>"
    assert attempts["https://www.suin-juriscol.gov.co/doc?id=99"] == 3


def test_scope_catalog_has_every_expected_scope() -> None:
    expected = {
        "tributario",
        "laboral",
        "laboral-tributario",
        "jurisprudencia",
        "full",
        "et",
    }
    assert expected.issubset(harvest_mod._SCOPES.keys())
    assert harvest_mod._SCOPES["et"].alias_of == "tributario"
    assert harvest_mod._SCOPES["et"].deprecated is True
    canonical, definition = harvest_mod._resolve_scope("et")
    assert canonical == "tributario"
    assert definition is harvest_mod._SCOPES["tributario"]


def test_scope_seed_urls_are_well_formed() -> None:
    for scope, definition in harvest_mod._SCOPES.items():
        for url in definition.seed_urls:
            parsed = urlparse(url)
            assert parsed.scheme == "https", f"{scope}: {url} not https"
            assert parsed.netloc == "www.suin-juriscol.gov.co", (
                f"{scope}: {url} not on suin-juriscol.gov.co"
            )
            assert parsed.path, f"{scope}: {url} has empty path"


def test_full_scope_is_union_of_narrower_scopes() -> None:
    narrow_sitemaps: set[str] = set()
    for scope in ("tributario", "laboral", "laboral-tributario", "jurisprudencia"):
        for entry in harvest_mod._SCOPES[scope].sitemaps:
            narrow_sitemaps.add(entry.name)
    full_sitemaps = {entry.name for entry in harvest_mod._SCOPES["full"].sitemaps}
    assert narrow_sitemaps.issubset(full_sitemaps), (
        f"full missing sitemaps: {narrow_sitemaps - full_sitemaps}"
    )


def test_fetcher_emits_seeds_before_sitemap_walk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With SEED_URLS patched, iter_seeds must return seeds in declaration order."""
    seed = "https://www.suin-juriscol.gov.co/viewDocument.asp?id=seed-1"
    monkeypatch.setitem(SEED_URLS, "tributario", (seed,))

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        return httpx.Response(200, text="<html></html>")

    fetcher = SuinFetcher(
        cache_dir=tmp_path / "cache",
        rps=100.0,
        transport=httpx.MockTransport(handler),
    )
    with fetcher:
        emitted = list(fetcher.iter_seeds("tributario"))
    assert emitted == [seed]

    # `et` alias resolves to tributario seeds.
    with SuinFetcher(
        cache_dir=tmp_path / "cache2",
        rps=100.0,
        transport=httpx.MockTransport(handler),
    ) as aliased:
        assert list(aliased.iter_seeds("et")) == [seed]


def test_manifest_appended_on_cache_miss(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        return httpx.Response(200, text="<html></html>")

    fetcher = SuinFetcher(
        cache_dir=tmp_path / "cache",
        rps=100.0,
        transport=_transport(handler),
    )
    with fetcher:
        fetcher.fetch("https://www.suin-juriscol.gov.co/one")
        fetcher.fetch("https://www.suin-juriscol.gov.co/two")
    manifest = (tmp_path / "cache" / "_manifest.jsonl").read_text(encoding="utf-8")
    assert manifest.count("\n") == 2
