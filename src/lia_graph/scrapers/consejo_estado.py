"""Scraper for https://www.consejodeestado.gov.co/.

Coverage: Sentencias de nulidad + autos de suspensión provisional.
Primary source for `sent.ce.*` and `auto.ce.*` norm_ids.
"""

from __future__ import annotations

from typing import Any

from lia_graph.scrapers.base import Scraper
from lia_graph.scrapers.secretaria_senado import _html_to_text


_BASE_URL = "https://www.consejodeestado.gov.co/documentos/boletines"


class ConsejoEstadoScraper(Scraper):
    source_id = "consejo_estado"
    rate_limit_seconds = 1.0
    _handled_types = {"sentencia_ce", "auto_ce"}

    def _resolve_url(self, norm_id: str) -> str | None:
        if not (norm_id.startswith("sent.ce.") or norm_id.startswith("auto.ce.")):
            return None
        # Full live-fetch path requires the CE search RPC; for now, the
        # cache is pre-seeded with explicit URLs added by the harness once
        # the SME provides them.
        return f"{_BASE_URL}/{norm_id.replace('.', '_')}.html"

    def _parse_html(self, content: bytes) -> tuple[str, dict[str, Any]]:
        text = _html_to_text(content.decode("utf-8", errors="ignore"))
        return text, {}


__all__ = ["ConsejoEstadoScraper"]
