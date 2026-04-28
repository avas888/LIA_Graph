"""SUIN scraper tests — fixplan_v6 §3 step 2.

Covers:
* canonical-id helpers (parent-id + article-key extraction);
* registry-backed URL resolution;
* the three-tier fetch path (sqlite cache → cache/suin disk → live fetch);
* per-article slicing via parse_document.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from lia_graph.scrapers import ScraperCache
from lia_graph.scrapers.suin_juriscol import (
    SuinJuriscolScraper,
    _article_key_from_norm_id,
    _canonical_parent_id,
    _disk_cache_path,
    _slice_article_from_suin_html,
)


REGISTRY = {
    "decreto.624.1989": {
        "suin_doc_id": "1132325",
        "ruta": "https://www.suin-juriscol.gov.co/viewDocument.asp?id=1132325",
        "title": "DECRETO 624 DE 1989 - Colombia | SUIN Juriscol",
    },
    "decreto.1625.2016": {
        "suin_doc_id": "30030361",
        "ruta": "https://www.suin-juriscol.gov.co/viewDocument.asp?id=30030361",
        "title": "DECRETO 1625 DE 2016 - Colombia | SUIN Juriscol",
    },
    "ley.100.1993": {
        "suin_doc_id": "1635955",
        "ruta": "https://www.suin-juriscol.gov.co/viewDocument.asp?id=1635955",
        "title": "LEY 100 DE 1993 - Colombia | SUIN Juriscol",
    },
}


# Minimal SUIN-shaped HTML covering two articles. The parser keys on
# `<a name="ver_<n>">` anchors followed by an `articulo_normal` container
# with an "Artículo N" heading.
_FIXTURE_HTML = """\
<?xml version="1.0"?>
<html><body>
<a name="ver_1"></a>
<div class="articulo_normal">
<p>Artículo 1.1.1. Contenido. Texto del primer artículo de prueba.</p>
</div>
<a name="ver_2"></a>
<div class="articulo_normal">
<p>Artículo 1.1.2. Otro título. Texto del segundo artículo de prueba.</p>
</div>
</body></html>
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def test_canonical_parent_id_strips_article_suffix():
    assert _canonical_parent_id("decreto.1625.2016.art.1.6.1.1.10") == "decreto.1625.2016"
    assert _canonical_parent_id("ley.100.1993.art.5") == "ley.100.1993"
    assert _canonical_parent_id("cst.art.45.par.1") == "cst"
    # Already-parent ids pass through unchanged.
    assert _canonical_parent_id("decreto.1625.2016") == "decreto.1625.2016"
    assert _canonical_parent_id("et") == "et"


def test_article_key_from_norm_id_extracts_dotted_path():
    assert _article_key_from_norm_id("decreto.1625.2016.art.1.6.1.1.10") == "1.6.1.1.10"
    assert _article_key_from_norm_id("ley.100.1993.art.5") == "5"
    # Sub-units strip back to the parent article — slicer pulls the article
    # body and the LLM finds the sub-unit inside.
    assert _article_key_from_norm_id("ley.100.1993.art.5.par.2") == "5"
    assert _article_key_from_norm_id("cst.art.45.num.3") == "45"
    # No article suffix → None.
    assert _article_key_from_norm_id("decreto.1625.2016") is None


# ---------------------------------------------------------------------------
# Slicing
# ---------------------------------------------------------------------------


def test_slice_article_from_suin_html_returns_target_body():
    sliced = _slice_article_from_suin_html(
        _FIXTURE_HTML,
        "1.1.1",
        doc_id="fixture",
        ruta="fixture://test",
    )
    assert sliced is not None
    assert "primer artículo" in sliced
    assert "segundo artículo" not in sliced


def test_slice_article_returns_none_on_miss():
    assert _slice_article_from_suin_html(
        _FIXTURE_HTML, "9.9.9", doc_id="fixture", ruta="fixture://test"
    ) is None


def test_slice_article_handles_empty_inputs():
    assert _slice_article_from_suin_html("", "1", doc_id="x", ruta="y") is None
    assert _slice_article_from_suin_html(_FIXTURE_HTML, "", doc_id="x", ruta="y") is None


# ---------------------------------------------------------------------------
# fetch() — three-tier cache path
# ---------------------------------------------------------------------------


def _make_scraper(tmp_path: Path, *, live_fetch: bool = False):
    cache = ScraperCache(tmp_path / "scraper_cache.db")
    disk_dir = tmp_path / "cache_suin"
    disk_dir.mkdir()
    return SuinJuriscolScraper(
        cache,
        live_fetch=live_fetch,
        registry=REGISTRY,
        disk_cache_dir=disk_dir,
    ), cache, disk_dir


def test_fetch_returns_none_when_registry_missing(tmp_path: Path):
    cache = ScraperCache(tmp_path / "scraper_cache.db")
    s = SuinJuriscolScraper(cache, registry={}, disk_cache_dir=tmp_path / "empty")
    assert s.fetch("decreto.1625.2016.art.1.1.1") is None


def test_fetch_returns_none_when_no_disk_cache_and_no_live(tmp_path: Path):
    s, _cache, _disk = _make_scraper(tmp_path, live_fetch=False)
    # Disk cache is empty; live_fetch is False → clean None.
    assert s.fetch("decreto.1625.2016.art.1.1.1") is None


def test_fetch_slices_article_from_disk_cache(tmp_path: Path):
    s, cache, disk_dir = _make_scraper(tmp_path, live_fetch=False)
    url = REGISTRY["decreto.1625.2016"]["ruta"]
    # Seed the SUIN harvester's disk cache with a fixture for this URL.
    sha1 = hashlib.sha1(url.encode("utf-8")).hexdigest()
    (disk_dir / f"{sha1}.html").write_text(_FIXTURE_HTML, encoding="utf-8")

    res = s.fetch("decreto.1625.2016.art.1.1.1")
    assert res is not None
    assert res.source == "suin_juriscol"
    assert res.url == url
    assert "primer artículo" in res.parsed_text
    assert "segundo artículo" not in res.parsed_text
    assert res.parsed_meta["sliced_to_article"] == "1.1.1"
    assert res.parsed_meta["suin_doc_id"] == "30030361"
    assert res.cache_hit is False  # populated from disk cache, not sqlite
    # Subsequent calls must short-circuit on the sqlite cache.
    res2 = s.fetch("decreto.1625.2016.art.1.1.2")
    assert res2 is not None
    assert "segundo artículo" in res2.parsed_text
    assert res2.cache_hit is True


def test_fetch_returns_none_when_article_not_present_in_doc(tmp_path: Path):
    s, _cache, disk_dir = _make_scraper(tmp_path, live_fetch=False)
    url = REGISTRY["decreto.1625.2016"]["ruta"]
    sha1 = hashlib.sha1(url.encode("utf-8")).hexdigest()
    (disk_dir / f"{sha1}.html").write_text(_FIXTURE_HTML, encoding="utf-8")
    # Article 9.9.9 doesn't exist in the fixture; slicer returns None.
    assert s.fetch("decreto.1625.2016.art.9.9.9") is None


def test_fetch_full_doc_when_no_article_suffix(tmp_path: Path):
    s, _cache, disk_dir = _make_scraper(tmp_path, live_fetch=False)
    url = REGISTRY["ley.100.1993"]["ruta"]
    sha1 = hashlib.sha1(url.encode("utf-8")).hexdigest()
    (disk_dir / f"{sha1}.html").write_text(_FIXTURE_HTML, encoding="utf-8")

    res = s.fetch("ley.100.1993")
    assert res is not None
    assert "primer artículo" in res.parsed_text
    assert "segundo artículo" in res.parsed_text
    assert res.parsed_meta["suin_doc_id"] == "1635955"
    assert "sliced_to_article" not in res.parsed_meta


def test_fetch_uses_sqlite_cache_first(tmp_path: Path):
    """If the sqlite cache already has the URL, fetch must not touch the disk cache."""

    s, cache, disk_dir = _make_scraper(tmp_path, live_fetch=False)
    url = REGISTRY["decreto.1625.2016"]["ruta"]
    # Pre-populate the sqlite cache directly.
    cache.put(
        source="suin_juriscol",
        url=url,
        content=_FIXTURE_HTML.encode("utf-8"),
        status_code=200,
        canonical_norm_id="decreto.1625.2016",
        content_type="text/html; charset=utf-8",
        parsed_text="(pre-cached parsed_text)",
        parsed_meta={"seeded": True},
    )
    # No disk-cache file exists.
    res = s.fetch("decreto.1625.2016.art.1.1.1")
    assert res is not None
    assert res.cache_hit is True
    assert "primer artículo" in res.parsed_text


def test_disk_cache_path_matches_suin_fetcher_convention(tmp_path: Path):
    """Sanity check: our SHA1 derivation must match SuinFetcher._cache_path."""

    url = "https://www.suin-juriscol.gov.co/viewDocument.asp?id=1132325"
    expected = hashlib.sha1(url.encode("utf-8")).hexdigest() + ".html"
    p = _disk_cache_path(url, root=tmp_path)
    assert p.name == expected
    assert p.parent == tmp_path


# ---------------------------------------------------------------------------
# Real corpus check (skipped if cache + registry not present)
# ---------------------------------------------------------------------------


_REAL_REGISTRY = Path("var/suin_doc_id_registry.json")
_REAL_DISK_CACHE = Path("cache/suin")


@pytest.mark.skipif(
    not (_REAL_REGISTRY.is_file() and _REAL_DISK_CACHE.is_dir()),
    reason="SUIN registry / disk cache not present — run "
           "`uv run python scripts/canonicalizer/build_suin_doc_id_registry.py`.",
)
def test_real_dur_article_slice(tmp_path: Path):
    """Slice a known DUR-1625 article from the real cache + registry.

    Smoke-asserts that the regex fix in parser._ARTICLE_HEADING_RE
    (multi-segment captures) plus the registry plus the slicer compose
    end-to-end against a real 17-MB SUIN page.
    """

    cache = ScraperCache(tmp_path / "scraper_cache.db")
    s = SuinJuriscolScraper(cache, live_fetch=False, disk_cache_dir=_REAL_DISK_CACHE)
    res = s.fetch("decreto.1625.2016.art.1.1.1")
    assert res is not None, "expected DUR 1625 art 1.1.1 to slice from real SUIN cache"
    assert res.parsed_meta["sliced_to_article"] == "1.1.1"
    assert "Obligaciones" in res.parsed_text or "obligaciones" in res.parsed_text.lower()
    assert len(res.parsed_text) < 50_000, (
        "sliced article body should be ~hundreds-of-bytes, not the full 17-MB doc"
    )


# ---------------------------------------------------------------------------
# Per-URL parsed-doc cache (perf fix — fixplan_v6 step 2 follow-on)
# ---------------------------------------------------------------------------


def test_parsed_doc_cache_avoids_re_parsing_same_url(tmp_path: Path, monkeypatch):
    """Calling fetch() for many norms with the same parent URL must parse
    the doc only once. Without this cache, the 17 MB DUR HTML re-parses
    per norm and 24 thread workers thrash the system into swap."""

    from lia_graph.scrapers import suin_juriscol as mod

    s, cache, disk_dir = _make_scraper(tmp_path, live_fetch=False)
    url = REGISTRY["decreto.1625.2016"]["ruta"]
    sha1 = hashlib.sha1(url.encode("utf-8")).hexdigest()
    (disk_dir / f"{sha1}.html").write_text(_FIXTURE_HTML, encoding="utf-8")

    parse_calls = {"n": 0}
    real_parse = mod._parse_suin_document

    def counting_parse(html, *, doc_id, ruta):
        parse_calls["n"] += 1
        return real_parse(html, doc_id=doc_id, ruta=ruta)

    monkeypatch.setattr(mod, "_parse_suin_document", counting_parse)

    # 5 different article-scoped norm_ids — same parent URL.
    for art in ("1.1.1", "1.1.2", "1.1.1", "1.1.2", "1.1.1"):
        res = s.fetch(f"decreto.1625.2016.art.{art}")
        assert res is not None, f"miss for art={art}"

    # The first call materializes the cache_entry and parses once.
    # Subsequent calls hit the per-URL parsed-doc cache. Total: 1 parse.
    assert parse_calls["n"] == 1, (
        f"expected 1 parse for 5 article fetches sharing one URL, got {parse_calls['n']}"
    )


def test_persisted_slice_cache_avoids_re_parse_across_scraper_instances(tmp_path: Path, monkeypatch):
    """Option 2 persistence: slices are stored in scraper_cache.db parsed_meta
    so a SECOND scraper instance (e.g. a parallel batch process) doesn't
    re-parse the 17 MB DUR HTML — it loads the slice dict from SQLite."""

    from lia_graph.scrapers import suin_juriscol as mod

    cache_path = tmp_path / "scraper_cache.db"
    disk_dir = tmp_path / "cache_suin"
    disk_dir.mkdir()
    url = REGISTRY["decreto.1625.2016"]["ruta"]
    sha1 = hashlib.sha1(url.encode("utf-8")).hexdigest()
    (disk_dir / f"{sha1}.html").write_text(_FIXTURE_HTML, encoding="utf-8")

    parse_calls = {"n": 0}
    real_parse = mod._parse_suin_document

    def counting_parse(html, *, doc_id, ruta):
        parse_calls["n"] += 1
        return real_parse(html, doc_id=doc_id, ruta=ruta)

    monkeypatch.setattr(mod, "_parse_suin_document", counting_parse)

    # --- Process 1: scraper instance A ---
    cache_a = ScraperCache(cache_path)
    s_a = SuinJuriscolScraper(cache_a, live_fetch=False, registry=REGISTRY, disk_cache_dir=disk_dir)
    res_a = s_a.fetch("decreto.1625.2016.art.1.1.1")
    assert res_a is not None
    parses_after_a = parse_calls["n"]
    assert parses_after_a == 1, f"first instance should parse once, got {parses_after_a}"

    # --- Process 2: scraper instance B (fresh, shares the SQLite cache) ---
    cache_b = ScraperCache(cache_path)
    s_b = SuinJuriscolScraper(cache_b, live_fetch=False, registry=REGISTRY, disk_cache_dir=disk_dir)
    res_b = s_b.fetch("decreto.1625.2016.art.1.1.1")
    assert res_b is not None
    assert "primer artículo" in res_b.parsed_text
    # Critical assertion: instance B did NOT re-parse — it read the
    # persisted slice dict from parsed_meta in SQLite.
    assert parse_calls["n"] == parses_after_a, (
        f"instance B should hit the persisted slice cache; got {parse_calls['n']} parses total"
    )

    # And a different article via instance B is also a no-parse hit.
    res_b2 = s_b.fetch("decreto.1625.2016.art.1.1.2")
    assert res_b2 is not None
    assert "segundo artículo" in res_b2.parsed_text
    assert parse_calls["n"] == parses_after_a, "no parse on second article either"
