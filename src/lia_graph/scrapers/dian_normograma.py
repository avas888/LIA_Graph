"""Scraper for https://normograma.dian.gov.co/.

Coverage: Decretos tributarios + resoluciones DIAN + conceptos DIAN.
Primary source for any `decreto.*`, `res.dian.*`, `concepto.dian.*` norm_id.
"""

from __future__ import annotations

import re
from typing import Any

from lia_graph.scrapers.base import Scraper
from lia_graph.scrapers.secretaria_senado import _html_to_text


_BASE_URL = "https://normograma.dian.gov.co/dian/compilacion/docs"


class DianNormogramaScraper(Scraper):
    source_id = "dian_normograma"
    rate_limit_seconds = 0.5
    _handled_types = {
        "decreto",
        "decreto_articulo",
        "resolucion",
        "res_articulo",
        "concepto_dian",
        "concepto_dian_numeral",
    }

    def _resolve_url(self, norm_id: str) -> str | None:
        if norm_id.startswith("decreto."):
            parts = norm_id.split(".")
            if len(parts) < 3:
                return None
            return f"{_BASE_URL}/decreto_{parts[1]}_{parts[2]}.htm"
        if norm_id.startswith("res.dian."):
            parts = norm_id.split(".")
            # res.dian.NUM.YEAR
            if len(parts) < 4:
                return None
            return f"{_BASE_URL}/resolucion_dian_{parts[2]}_{parts[3]}.htm"
        if norm_id.startswith("concepto.dian."):
            parts = norm_id.split(".")
            num = parts[2]
            return f"{_BASE_URL}/concepto_dian_{num}.htm"
        return None

    def _parse_html(self, content: bytes) -> tuple[str, dict[str, Any]]:
        text = _html_to_text(content.decode("utf-8", errors="ignore"))
        # DIAN normograma renders a "Notas de vigencia" panel — extract it.
        notes_match = re.search(
            r"Notas?\s+de\s+Vigencia[\s\S]{0,2000}?(?=Notas?\s+del\s+Editor|$)",
            text,
            flags=re.IGNORECASE,
        )
        notes = notes_match.group(0).strip() if notes_match else ""
        return text, {"vigencia_notes": notes}


__all__ = ["DianNormogramaScraper"]
