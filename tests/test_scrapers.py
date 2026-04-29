"""Sub-fix 1B-α scraper smoke tests.

H0 tests: cache CRUD + URL resolution + parse-fixture round-trip. Live HTTP
tests gated behind LIA_LIVE_SCRAPER_TESTS=1 (run only on demand).
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from lia_graph.scrapers import ScraperCache, ScraperRegistry
from lia_graph.scrapers.consejo_estado import ConsejoEstadoScraper
from lia_graph.scrapers.corte_constitucional import CorteConstitucionalScraper
from lia_graph.scrapers.dian_normograma import DianNormogramaScraper
from lia_graph.scrapers.secretaria_senado import SecretariaSenadoScraper
from lia_graph.scrapers.suin_juriscol import SuinJuriscolScraper


@pytest.fixture
def cache(tmp_path: Path) -> ScraperCache:
    return ScraperCache(tmp_path / "test_scraper_cache.db")


# ---------------------------------------------------------------------------
# Cache CRUD
# ---------------------------------------------------------------------------


def test_cache_put_get_round_trip(cache: ScraperCache):
    cache.put(
        source="secretaria_senado",
        url="https://example.com/ley_2277_2022.html",
        content=b"<html>...</html>",
        status_code=200,
        canonical_norm_id="ley.2277.2022",
        content_type="text/html",
        parsed_text="Ley 2277 de 2022",
        parsed_meta={"modification_notes": []},
    )
    entry = cache.get("secretaria_senado", "https://example.com/ley_2277_2022.html")
    assert entry is not None
    assert entry.canonical_norm_id == "ley.2277.2022"
    assert entry.parsed_text == "Ley 2277 de 2022"
    assert entry.status_code == 200
    assert entry.content_sha256  # populated


def test_cache_get_by_canonical(cache: ScraperCache):
    cache.put(
        source="secretaria_senado",
        url="https://example.com/a",
        content=b"a",
        status_code=200,
        canonical_norm_id="ley.2277.2022",
    )
    cache.put(
        source="dian_normograma",
        url="https://example.com/b",
        content=b"b",
        status_code=200,
        canonical_norm_id="ley.2277.2022",
    )
    entries = cache.get_by_canonical("ley.2277.2022")
    sources = {e.source for e in entries}
    assert sources == {"secretaria_senado", "dian_normograma"}


def test_cache_upsert_replaces(cache: ScraperCache):
    cache.put(source="x", url="u", content=b"v1", status_code=200)
    cache.put(source="x", url="u", content=b"v2", status_code=200)
    entry = cache.get("x", "u")
    assert entry is not None
    assert entry.content == b"v2"


def test_cache_attach_canonical_norm_id(cache: ScraperCache):
    cache.put(source="x", url="u", content=b"v", status_code=200)
    cache.attach_canonical_norm_id(source="x", url="u", canonical_norm_id="ley.1.2026")
    entries = cache.get_by_canonical("ley.1.2026")
    assert len(entries) == 1


def test_cache_stats(cache: ScraperCache):
    cache.put(source="x", url="u1", content=b"a", status_code=200, canonical_norm_id="ley.1.2026")
    cache.put(source="x", url="u2", content=b"b", status_code=200)
    stats = cache.stats()
    assert stats["total_rows"] == 2
    assert stats["rows_with_canonical_id"] == 1
    assert stats["by_source"] == {"x": 2}


# ---------------------------------------------------------------------------
# URL resolution
# ---------------------------------------------------------------------------


def test_secretaria_senado_url_for_et():
    s = SecretariaSenadoScraper(ScraperCache(":memory:"))
    url = s._resolve_url("et")
    assert url is not None
    assert "estatuto_tributario" in url


def test_secretaria_senado_url_for_et_article():
    s = SecretariaSenadoScraper(ScraperCache(":memory:"))
    url = s._resolve_url("et.art.689-3")
    assert url is not None
    assert "estatuto_tributario" in url


def test_secretaria_senado_url_for_ley():
    s = SecretariaSenadoScraper(ScraperCache(":memory:"))
    url = s._resolve_url("ley.2277.2022")
    assert url is not None
    assert "ley_2277_2022" in url


def test_senado_cst_url():
    s = SecretariaSenadoScraper(ScraperCache(":memory:"))
    url = s._resolve_url("cst.art.45")
    assert url is not None
    assert "secretariasenado.gov.co" in url
    assert "codigo_sustantivo_trabajo" in url


def test_senado_cco_url():
    s = SecretariaSenadoScraper(ScraperCache(":memory:"))
    url = s._resolve_url("cco.art.515")
    assert url is not None
    assert "secretariasenado.gov.co" in url
    assert "codigo_comercio" in url


def test_senado_handles_cst_and_cco_norm_types():
    s = SecretariaSenadoScraper(ScraperCache(":memory:"))
    assert "cst_articulo" in s._handled_types
    assert "cco_articulo" in s._handled_types


# next_v7 P7 — Senado decreto resolver (closes E5 COVID decreto gap).


def test_senado_decreto_url_pads_to_4_digits():
    s = SecretariaSenadoScraper(ScraperCache(":memory:"))
    url = s._resolve_url("decreto.417.2020")
    assert url == "http://www.secretariasenado.gov.co/senado/basedoc/decreto_0417_2020.html"


def test_senado_decreto_article_url_matches_doc_url():
    s = SecretariaSenadoScraper(ScraperCache(":memory:"))
    # Article-level requests resolve to the same parent URL; the slicer
    # in fetch() finds the per-article anchor on that page.
    parent = s._resolve_url("decreto.417.2020")
    article = s._resolve_url("decreto.417.2020.art.1")
    assert parent == article
    assert "decreto_0417_2020" in article


def test_senado_decreto_url_other_covid_decretos():
    s = SecretariaSenadoScraper(ScraperCache(":memory:"))
    cases = {
        "decreto.444.2020": "decreto_0444_2020.html",
        "decreto.535.2020": "decreto_0535_2020.html",
        "decreto.568.2020": "decreto_0568_2020.html",
        "decreto.573.2020": "decreto_0573_2020.html",
        "decreto.772.2020": "decreto_0772_2020.html",
    }
    for nid, fragment in cases.items():
        url = s._resolve_url(nid)
        assert url is not None and fragment in url, (nid, url)


def test_senado_decreto_url_low_number_padding_edge_case():
    s = SecretariaSenadoScraper(ScraperCache(":memory:"))
    # Numerically padding edge: a hypothetical decreto 5/1900 should
    # render as decreto_0005_1900.html (mirror of ley_0100_1993.html).
    url = s._resolve_url("decreto.5.1900")
    assert url == "http://www.secretariasenado.gov.co/senado/basedoc/decreto_0005_1900.html"


def test_senado_decreto_url_4_digit_already():
    s = SecretariaSenadoScraper(ScraperCache(":memory:"))
    url = s._resolve_url("decreto.1625.2016")
    assert url == "http://www.secretariasenado.gov.co/senado/basedoc/decreto_1625_2016.html"


def test_senado_decreto_invalid_returns_none():
    s = SecretariaSenadoScraper(ScraperCache(":memory:"))
    # Missing year segment.
    assert s._resolve_url("decreto.417") is None


def test_senado_handles_decreto_norm_types():
    s = SecretariaSenadoScraper(ScraperCache(":memory:"))
    assert "decreto" in s._handled_types
    assert "decreto_articulo" in s._handled_types


def test_dian_normograma_url_for_decreto():
    s = DianNormogramaScraper(ScraperCache(":memory:"))
    assert s._resolve_url("decreto.1474.2025") is not None


def test_dian_normograma_url_for_concepto():
    s = DianNormogramaScraper(ScraperCache(":memory:"))
    # Non-hyphenated NUM still resolves via the historical
    # concepto_dian_<NUM>.htm pattern.
    assert s._resolve_url("concepto.dian.123456") is not None


def test_dian_normograma_concepto_hyphen_url():
    """fixplan_v5 blocker #3 — hyphenated unified conceptos like
    `concepto.dian.100208192-202` are not derivable from the canonical
    suffix alone. Empirical probing (2026-04-28) confirmed the actual host
    file uses the `oficio_dian_<RADICADO>_<YEAR>.htm` shape (e.g.
    `oficio_dian_6038_2024.htm` returns HTTP 200 for this id). Without a
    canonical-suffix → radicado/year lookup table, the resolver returns
    None so the primary-source chain falls through cleanly rather than
     404'ing on the wrong URL.
    """
    s = DianNormogramaScraper(ScraperCache(":memory:"))
    assert s._resolve_url("concepto.dian.100208192-202") is None


def test_corte_constitucional_url_for_sentencia():
    s = CorteConstitucionalScraper(ScraperCache(":memory:"))
    url = s._resolve_url("sent.cc.C-481.2019")
    assert url is not None
    assert "c-481-19" in url


def test_consejo_estado_url_for_auto():
    s = ConsejoEstadoScraper(ScraperCache(":memory:"))
    url = s._resolve_url("auto.ce.28920.2024.12.16")
    assert url is not None


def test_consejo_estado_url_fixture_first():
    """When a local fixture exists for the norm_id, _resolve_url returns
    a file:// URL pointing at it instead of the (404) live boletines URL.

    Covers all 5 G6 acid-test CE ids fixtured at
    tests/fixtures/scrapers/consejo_estado/{autos,sentencias}/.
    """

    s = ConsejoEstadoScraper(ScraperCache(":memory:"))
    fixtured_ids = (
        "auto.ce.28920.2024.12.16",
        "auto.ce.082.2026.04.15",
        "auto.ce.084.2026.04.15",
        "sent.ce.28920.2025.07.03",
        "sent.ce.2022CE-SUJ-4-002",
    )
    for norm_id in fixtured_ids:
        url = s._resolve_url(norm_id)
        assert url is not None, norm_id
        assert url.startswith("file://"), f"{norm_id}: {url}"
        assert "tests/fixtures/scrapers/consejo_estado/" in url, norm_id


def test_consejo_estado_url_falls_back_when_no_fixture():
    """When no fixture is present, _resolve_url falls back to the legacy
    boletines URL (which 404s today — that's the existing behavior we
    preserve until a live SPA-fetch path lands)."""

    s = ConsejoEstadoScraper(ScraperCache(":memory:"))
    url = s._resolve_url("auto.ce.99999.2099.01.01")
    assert url is not None
    assert url.startswith("https://www.consejodeestado.gov.co/")
    assert "auto_ce_99999_2099_01_01" in url


def test_consejo_estado_fetch_reads_fixture(tmp_path: Path):
    """End-to-end: fetch() against a fixtured id returns the fixture body
    without needing live HTTP, and seeds the scraper cache for re-use."""

    cache = ScraperCache(tmp_path / "ce_fixture_cache.db")
    s = ConsejoEstadoScraper(cache, live_fetch=False)
    res = s.fetch("auto.ce.28920.2024.12.16")
    assert res is not None
    assert res.status_code == 200
    assert res.url.startswith("file://")
    assert "auto.ce.28920.2024.12.16" in res.parsed_text
    assert res.parsed_meta.get("fixture_only") is True
    # Re-fetch should now be a cache hit.
    res2 = s.fetch("auto.ce.28920.2024.12.16")
    assert res2 is not None
    assert res2.cache_hit is True


def test_suin_juriscol_url_resolves_through_registry():
    # fixplan_v6 §3 step 2: SUIN scraper now reads var/suin_doc_id_registry.json
    # and resolves canonical norm_ids to SUIN URLs.
    registry = {
        "ley.2277.2022": {
            "suin_doc_id": "30045028",
            "ruta": "https://www.suin-juriscol.gov.co/viewDocument.asp?id=30045028",
            "title": "LEY 2277 DE 2022 - Colombia | SUIN Juriscol",
        },
    }
    s = SuinJuriscolScraper(ScraperCache(":memory:"), registry=registry)
    url = s._resolve_url("ley.2277.2022")
    assert url == "https://www.suin-juriscol.gov.co/viewDocument.asp?id=30045028"
    # Article-scoped lookup goes through the parent doc.
    assert (
        s._resolve_url("ley.2277.2022.art.5")
        == "https://www.suin-juriscol.gov.co/viewDocument.asp?id=30045028"
    )
    # Unknown parent → None (falls through to other scrapers).
    assert s._resolve_url("ley.9999.2030") is None


def test_suin_juriscol_url_returns_none_with_empty_registry():
    # When the registry has not been built yet, the scraper resolves no URLs
    # and the harness falls through to other primary sources cleanly.
    s = SuinJuriscolScraper(ScraperCache(":memory:"), registry={})
    assert s._resolve_url("ley.2277.2022") is None


def test_scraper_does_not_handle_unrelated_norm_type():
    s = SecretariaSenadoScraper(ScraperCache(":memory:"))
    assert s._resolve_url("sent.cc.C-481.2019") is None


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def test_registry_routes_law_to_senado_and_suin(cache: ScraperCache):
    registry = ScraperRegistry([
        SecretariaSenadoScraper(cache),
        DianNormogramaScraper(cache),
        SuinJuriscolScraper(cache),
        CorteConstitucionalScraper(cache),
        ConsejoEstadoScraper(cache),
    ])
    scrapers = registry.for_norm("ley.2277.2022")
    sources = {s.source_id for s in scrapers}
    assert "secretaria_senado" in sources
    assert "suin_juriscol" in sources
    assert "corte_constitucional" not in sources


def test_registry_routes_sentencia_cc(cache: ScraperCache):
    registry = ScraperRegistry([
        SecretariaSenadoScraper(cache),
        CorteConstitucionalScraper(cache),
    ])
    scrapers = registry.for_norm("sent.cc.C-481.2019")
    sources = {s.source_id for s in scrapers}
    assert "corte_constitucional" in sources
    assert "secretaria_senado" not in sources


def test_fetch_returns_none_when_cache_miss_and_no_live_fetch(cache: ScraperCache):
    s = SecretariaSenadoScraper(cache, live_fetch=False)
    res = s.fetch("ley.9999.2030")
    assert res is None


def test_fetch_returns_cached_entry(cache: ScraperCache):
    s = SecretariaSenadoScraper(cache, live_fetch=False)
    url = s._resolve_url("ley.2277.2022")
    cache.put(
        source="secretaria_senado",
        url=url,  # type: ignore[arg-type]
        content=b"<html>Ley 2277 de 2022</html>",
        status_code=200,
        canonical_norm_id="ley.2277.2022",
        parsed_text="Ley 2277 de 2022",
    )
    res = s.fetch("ley.2277.2022")
    assert res is not None
    assert res.cache_hit is True
    assert res.parsed_text == "Ley 2277 de 2022"


# ---------------------------------------------------------------------------
# HTML parser smoke
# ---------------------------------------------------------------------------


def test_secretaria_senado_html_to_text_extracts_modification_notes():
    s = SecretariaSenadoScraper(ScraperCache(":memory:"))
    html = (
        b"<html><body><p>Art. 158-1 ET. <em>Modificado por la Ley 2277 de 2022, "
        b"Art. 96.</em></p></body></html>"
    )
    text, meta = s._parse_html(html)
    assert "Art. 158-1 ET" in text
    assert any("Modificado por" in note for note in meta["modification_notes"])
