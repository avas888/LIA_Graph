"""Función Pública gestor normativo scraper tests — v6.1 6th-scraper.

Mirrors the SUIN scraper test shape. Covers:
* registry-backed URL resolution
* per-article slicing on a Función Pública-shaped HTML fixture
  (`<a name="N.N.N">` anchors with DUR keys directly)
* SQLite cache hit + slice-cache persistence
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lia_graph.scrapers import ScraperCache
from lia_graph.scrapers.funcion_publica import (
    FuncionPublicaScraper,
    _extract_articles_dict,
    _slice_from_articles_dict,
)


REGISTRY = {
    "decreto.1625.2016": {
        "funcion_publica_doc_id": "83233",
        "ruta": "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=83233",
        "title": "Decreto 1625 de 2016",
    },
    "decreto.1072.2015": {
        "funcion_publica_doc_id": "72173",
        "ruta": "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=72173",
        "title": "Decreto 1072 de 2015",
    },
}


# Fixture HTML matching Función Pública's actual shape: `<a name="N.N.N">`
# anchors with DUR keys directly, body text follows the anchor.
_FIXTURE_HTML = """\
<html><body>
<h1>Decreto 1625 de 2016</h1>
<a name="1.1.1"></a>
<p>1.1.1. Obligaciones de dar, hacer y no hacer. Texto del primer artículo de prueba.</p>
<a name="1.1.2"></a>
<p>1.1.2. Contribuyentes o responsables. Texto del segundo artículo.</p>
<a name="1.6.1.1.10"></a>
<p>1.6.1.1.10. Libros de contabilidad. Texto multi-segmento.</p>
</body></html>
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def test_extract_articles_dict_returns_keyed_bodies():
    out = _extract_articles_dict(_FIXTURE_HTML)
    assert "1-1-1" in out
    assert "1-1-2" in out
    assert "1-6-1-1-10" in out
    assert "primer artículo" in out["1-1-1"]
    assert "segundo artículo" in out["1-1-2"]
    assert "multi-segmento" in out["1-6-1-1-10"]


def test_extract_articles_dict_empty_inputs():
    assert _extract_articles_dict("") == {}
    assert _extract_articles_dict("<html><body><p>no anchors</p></body></html>") == {}


def test_slice_from_articles_dict_normalizes_keys():
    d = _extract_articles_dict(_FIXTURE_HTML)
    # Caller passes dotted form; slicer normalizes to dashed for lookup.
    assert _slice_from_articles_dict(d, "1.1.1") is not None
    assert _slice_from_articles_dict(d, "1.6.1.1.10") is not None
    # Miss
    assert _slice_from_articles_dict(d, "9.9.9") is None
    # Empty
    assert _slice_from_articles_dict(None, "1.1.1") is None
    assert _slice_from_articles_dict({}, "1.1.1") is None


# ---------------------------------------------------------------------------
# Scraper
# ---------------------------------------------------------------------------


def _make_scraper(tmp_path: Path):
    cache = ScraperCache(tmp_path / "scraper_cache.db")
    return FuncionPublicaScraper(
        cache, live_fetch=False, registry=REGISTRY,
    ), cache


def test_resolve_url_via_registry(tmp_path: Path):
    s, _cache = _make_scraper(tmp_path)
    url = s._resolve_url("decreto.1625.2016.art.1.1.1")
    assert url == "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=83233"
    # Article-scoped lookup goes through the parent doc.
    assert (
        s._resolve_url("decreto.1072.2015.art.2.2.1.1")
        == "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=72173"
    )
    # Unknown parent → None.
    assert s._resolve_url("decreto.9999.2030") is None


def test_resolve_url_empty_registry(tmp_path: Path):
    cache = ScraperCache(tmp_path / "scraper_cache.db")
    s = FuncionPublicaScraper(cache, registry={}, live_fetch=False)
    assert s._resolve_url("decreto.1625.2016.art.1.1.1") is None


def test_fetch_returns_none_when_no_cache_and_no_live(tmp_path: Path):
    s, _cache = _make_scraper(tmp_path)
    assert s.fetch("decreto.1625.2016.art.1.1.1") is None


def test_fetch_slices_article_from_sqlite_cache(tmp_path: Path):
    s, cache = _make_scraper(tmp_path)
    url = REGISTRY["decreto.1625.2016"]["ruta"]
    # Pre-populate the SQLite cache with fixture HTML.
    cache.put(
        source="funcion_publica",
        url=url,
        content=_FIXTURE_HTML.encode("utf-8"),
        status_code=200,
        canonical_norm_id="decreto.1625.2016",
        content_type="text/html; charset=utf-8",
        parsed_text="(full doc parsed text)",
        parsed_meta={},  # no articles dict — test the lazy backfill
    )

    res = s.fetch("decreto.1625.2016.art.1.6.1.1.10")
    assert res is not None
    assert res.source == "funcion_publica"
    assert "multi-segmento" in res.parsed_text
    assert res.parsed_meta["sliced_to_article"] == "1.6.1.1.10"
    assert res.parsed_meta["funcion_publica_doc_id"] == "83233"


def test_fetch_persists_slice_cache_across_instances(tmp_path: Path):
    """Option-2 persistence: a fresh scraper instance reading the same
    SQLite cache must NOT re-extract slices — it reads from parsed_meta."""

    s, cache = _make_scraper(tmp_path)
    url = REGISTRY["decreto.1625.2016"]["ruta"]
    cache.put(
        source="funcion_publica",
        url=url,
        content=_FIXTURE_HTML.encode("utf-8"),
        status_code=200,
        canonical_norm_id="decreto.1625.2016",
        content_type="text/html; charset=utf-8",
        parsed_text="(full)",
        parsed_meta={},
    )

    # First fetch: lazy-backfills the slice cache into SQLite parsed_meta.
    res1 = s.fetch("decreto.1625.2016.art.1.1.1")
    assert res1 is not None

    # Verify parsed_meta now has the articles dict.
    entry = cache.get("funcion_publica", url)
    assert entry is not None
    assert "articles" in entry.parsed_meta
    assert "1-1-1" in entry.parsed_meta["articles"]

    # Second instance, same SQLite cache — must hit persisted slices.
    cache2 = ScraperCache(tmp_path / "scraper_cache.db")
    s2 = FuncionPublicaScraper(cache2, live_fetch=False, registry=REGISTRY)
    res2 = s2.fetch("decreto.1625.2016.art.1.1.2")
    assert res2 is not None
    assert "segundo artículo" in res2.parsed_text


# ---------------------------------------------------------------------------
# Real registry sanity check (skipped if not built)
# ---------------------------------------------------------------------------


_REAL_REGISTRY = Path("var/funcionpublica_doc_id_registry.json")


@pytest.mark.skipif(
    not _REAL_REGISTRY.is_file(),
    reason="Función Pública registry not built — run "
           "`uv run python scripts/canonicalizer/build_funcionpublica_registry.py`.",
)
def test_real_registry_has_dur_entries():
    reg = json.loads(_REAL_REGISTRY.read_text(encoding="utf-8"))
    # Must have at least DUR-1625 and DUR-1072.
    assert "decreto.1625.2016" in reg, "DUR-1625 missing from registry"
    assert "decreto.1072.2015" in reg, "DUR-1072 missing from registry"
    for canonical in ("decreto.1625.2016", "decreto.1072.2015"):
        entry = reg[canonical]
        assert entry["funcion_publica_doc_id"]
        assert entry["ruta"].startswith(
            "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i="
        )
