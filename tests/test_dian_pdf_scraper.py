"""DIAN PDF scraper tests — next_v7 P2 (7th source).

Mirrors the Función Pública / SUIN scraper test shape. Covers:
* registry-backed URL resolution
* per-article slicing on a DIAN-shaped plaintext fixture
  (ARTÍCULO N headings extracted by `pypdf` + the harness regex)
* SQLite cache hit + slice-cache persistence

The live HTTP path is exercised only when ``LIA_LIVE_SCRAPER_TESTS=1``;
the offline tests below stub the cache directly so pytest stays
deterministic.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from lia_graph.scrapers import ScraperCache
from lia_graph.scrapers.dian_pdf import (
    DianPdfScraper,
    _extract_articles_dict,
    _slice_from_articles_dict,
)


REGISTRY = {
    "res.dian.13.2021": {
        "url": "https://www.dian.gov.co/normatividad/Normatividad/Resolución 000013 de 11-02-2021.pdf",
        "number": "000013",
        "date": "11-02-2021",
        "title": "Resolución 13 de 2021",
    },
    "res.dian.94.2020": {
        "url": "https://www.dian.gov.co/normatividad/Normatividad/Resolución 000094 de 30-09-2020.pdf",
        "number": "000094",
        "date": "30-09-2020",
        "title": "Resolución 94 de 2020",
    },
}


# Shape mirrors what `pypdf.PdfReader.extract_text()` returns on a real
# DIAN PDF: ARTÍCULO N headings followed by article body, then the next
# heading. Mixed-case + accents kept.
_FIXTURE_TEXT = """\
RESOLUCIÓN NÚMERO 000013 DE 11 de febrero de 2021

Por la cual se desarrolla el sistema técnico de control de la facturación
electrónica.

ARTÍCULO 1. Ámbito de aplicación. La presente resolución aplica a los
sujetos obligados a expedir factura electrónica de venta.

ARTÍCULO 2. Definiciones. Para los efectos de la presente resolución se
adoptan las siguientes definiciones técnicas.

ARTICULO 3. Documento soporte de pago de nómina electrónica. Es el soporte
de las transacciones relacionadas con los pagos derivados de una vinculación.

ARTÍCULO 5. Información y contenido del documento. El documento soporte
de pago de nómina electrónica deberá contener como mínimo la siguiente
información tributaria.
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def test_extract_articles_dict_returns_numeric_keys():
    out = _extract_articles_dict(_FIXTURE_TEXT)
    assert set(out.keys()) == {"1", "2", "3", "5"}
    assert "Ámbito de aplicación" in out["1"]
    assert "Definiciones" in out["2"]
    assert "Documento soporte" in out["3"]
    assert "Información y contenido" in out["5"]


def test_extract_articles_dict_empty_inputs():
    assert _extract_articles_dict("") == {}
    assert _extract_articles_dict("RESOLUCIÓN sin headings de articulo.") == {}


def test_extract_articles_dict_first_occurrence_wins():
    text = (
        "ARTÍCULO 1. Primer cuerpo del artículo uno.\n"
        "ARTÍCULO 2. Cuerpo del segundo.\n"
        "ARTÍCULO 1. Footer mention re-using article 1 number.\n"
    )
    out = _extract_articles_dict(text)
    # The first match wins; the footer's later "ARTÍCULO 1" is ignored.
    assert "Primer cuerpo" in out["1"]
    assert "Footer mention" not in out["1"]


def test_slice_from_articles_dict_handles_subdotted_keys():
    d = _extract_articles_dict(_FIXTURE_TEXT)
    # If the canonical id is `res.dian.13.2021.art.5`, article_key is "5"
    # → exact lookup. If a sub-unit suffix were present (e.g. "5.par.1"),
    # the slicer takes the leading integer.
    assert _slice_from_articles_dict(d, "5") is not None
    assert _slice_from_articles_dict(d, "5.par.1") is not None
    # Miss
    assert _slice_from_articles_dict(d, "99") is None
    # None / empty input
    assert _slice_from_articles_dict(None, "5") is None
    assert _slice_from_articles_dict(d, None) is None


# ---------------------------------------------------------------------------
# URL resolution
# ---------------------------------------------------------------------------


def test_resolve_url_via_registry():
    sc = DianPdfScraper(ScraperCache(":memory:"), registry=REGISTRY)
    assert sc._resolve_url("res.dian.13.2021") == REGISTRY["res.dian.13.2021"]["url"]
    # Article-level id resolves to the parent doc URL.
    assert sc._resolve_url("res.dian.13.2021.art.5") == REGISTRY["res.dian.13.2021"]["url"]
    assert sc._resolve_url("res.dian.94.2020") == REGISTRY["res.dian.94.2020"]["url"]
    # Unknown norm → None.
    assert sc._resolve_url("res.dian.999.1999") is None


def test_handles_only_res_dian():
    sc = DianPdfScraper(ScraperCache(":memory:"), registry=REGISTRY)
    assert sc.handles("res_articulo", "res.dian.13.2021.art.5") is True
    assert sc.handles("resolucion", "res.dian.13.2021") is True
    # Same norm_type but different emisor — not ours.
    assert sc.handles("res_articulo", "res.minhacienda.42.2024.art.1") is False
    assert sc.handles("decreto", "decreto.1625.2016") is False


# ---------------------------------------------------------------------------
# Cache + slice path (offline)
# ---------------------------------------------------------------------------


def _seed_cache_with_articles(cache, *, url, articles_dict, content=b"%PDF-1.4 fake"):
    """Insert a CacheEntry whose parsed_meta carries pre-sliced articles."""

    cache.put(
        source="dian_pdf",
        url=url,
        content=content,
        status_code=200,
        canonical_norm_id="res.dian.13.2021",
        content_type="application/pdf",
        parsed_text="ignored — slicer reads parsed_meta['articles']",
        parsed_meta={"articles": articles_dict, "article_count": len(articles_dict)},
    )


def test_fetch_cache_hit_returns_sliced_article(tmp_path):
    db_path = tmp_path / "cache.db"
    cache = ScraperCache(str(db_path))
    sc = DianPdfScraper(cache, registry=REGISTRY)
    url = REGISTRY["res.dian.13.2021"]["url"]
    _seed_cache_with_articles(
        cache,
        url=url,
        articles_dict={"5": "Información y contenido del documento ..."},
    )

    res = sc.fetch("res.dian.13.2021.art.5")
    assert res is not None
    assert res.source == "dian_pdf"
    assert res.url == url
    assert res.cache_hit is True
    assert "Información y contenido" in res.parsed_text
    assert res.parsed_meta["sliced_to_article"] == "5"
    assert res.parsed_meta["dian_pdf_number"] == "000013"
    assert res.parsed_meta["dian_pdf_date"] == "11-02-2021"


def test_fetch_unknown_norm_returns_none():
    sc = DianPdfScraper(ScraperCache(":memory:"), registry=REGISTRY)
    assert sc.fetch("res.dian.999.1999.art.1") is None


def test_fetch_doc_level_returns_full_text(tmp_path):
    db_path = tmp_path / "cache.db"
    cache = ScraperCache(str(db_path))
    sc = DianPdfScraper(cache, registry=REGISTRY)
    url = REGISTRY["res.dian.13.2021"]["url"]
    cache.put(
        source="dian_pdf",
        url=url,
        content=b"%PDF-1.4 fake",
        status_code=200,
        canonical_norm_id="res.dian.13.2021",
        content_type="application/pdf",
        parsed_text=_FIXTURE_TEXT,
        parsed_meta={},
    )
    res = sc.fetch("res.dian.13.2021")  # no .art.* — doc-level
    assert res is not None
    assert res.parsed_text == _FIXTURE_TEXT
    assert res.parsed_meta["dian_pdf_number"] == "000013"


def test_fetch_missing_article_returns_none(tmp_path):
    db_path = tmp_path / "cache.db"
    cache = ScraperCache(str(db_path))
    sc = DianPdfScraper(cache, registry=REGISTRY)
    url = REGISTRY["res.dian.13.2021"]["url"]
    _seed_cache_with_articles(cache, url=url, articles_dict={"1": "Other article body."})
    # Article 99 is not in the slice dict.
    assert sc.fetch("res.dian.13.2021.art.99") is None
