"""Scraper for https://www.suin-juriscol.gov.co/.

Coverage: toda la legislación nacional con histórico. Useful as the cross-
check second source when secretariasenado.gov.co or normograma.dian.gov.co
disagree.
"""

from __future__ import annotations

from typing import Any

from lia_graph.scrapers.base import Scraper
from lia_graph.scrapers.secretaria_senado import _html_to_text


_BASE_URL = "https://www.suin-juriscol.gov.co/viewDocument.asp"


class SuinJuriscolScraper(Scraper):
    source_id = "suin_juriscol"
    rate_limit_seconds = 1.0  # SUIN is more conservative
    _handled_types = {
        "ley",
        "ley_articulo",
        "decreto",
        "decreto_articulo",
        "estatuto",
        "articulo_et",
    }

    def _resolve_url(self, norm_id: str) -> str | None:
        # SUIN URLs are id-keyed, not norm-keyed; the harness passes the
        # canonical id as a search query in practice. Live-fetch path will
        # populate the cache once the registry's lookup table is seeded.
        if norm_id.startswith("ley.") or norm_id.startswith("decreto."):
            # Convention: cache is pre-seeded with a `?canonical=<norm_id>`
            # marker URL during 1B-α development; live-fetch path resolves
            # via SUIN's search RPC at integration time.
            return f"{_BASE_URL}?canonical={norm_id}"
        return None

    def _parse_html(self, content: bytes) -> tuple[str, dict[str, Any]]:
        text = _html_to_text(content.decode("utf-8", errors="ignore"))
        return text, {}


__all__ = ["SuinJuriscolScraper"]
