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
        # SUIN URLs are keyed by an internal numeric id (`?id=NNNNNN`), not
        # canonical norm-id. Until a registry lookup table is seeded
        # (fixplan_v4 §5.6 backlog item), the `?canonical=` stub URL causes
        # a 400-then-SSL-cert-fail loop that adds 10–15 s of wasted retry
        # budget per norm with no chance of success. Returning None here
        # cleanly skips SUIN so the harness's primary-source chain falls
        # through to DIAN + Senado without paying the penalty.
        return None

    def _parse_html(self, content: bytes) -> tuple[str, dict[str, Any]]:
        text = _html_to_text(content.decode("utf-8", errors="ignore"))
        return text, {}


__all__ = ["SuinJuriscolScraper"]
