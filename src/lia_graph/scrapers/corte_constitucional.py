"""Scraper for https://www.corteconstitucional.gov.co/relatoria/.

Coverage: Sentencias C-, T-, SU-, A-; autos.
Primary source for `sent.cc.*` norm_ids.
"""

from __future__ import annotations

import re
from typing import Any

from lia_graph.scrapers.base import Scraper
from lia_graph.scrapers.secretaria_senado import _html_to_text


_BASE_URL = "https://www.corteconstitucional.gov.co/relatoria"


class CorteConstitucionalScraper(Scraper):
    source_id = "corte_constitucional"
    rate_limit_seconds = 0.5
    _handled_types = {"sentencia_cc"}

    def _resolve_url(self, norm_id: str) -> str | None:
        if not norm_id.startswith("sent.cc."):
            return None
        # sent.cc.C-481.2019 → /2019/c-481-19.htm
        rest = norm_id[len("sent.cc.") :]
        m = re.match(r"([A-Z]+)-(\d+)\.(\d{4})", rest)
        if not m:
            return None
        letter, number, year = m.groups()
        short_year = year[-2:]
        return f"{_BASE_URL}/{year}/{letter.lower()}-{number}-{short_year}.htm"

    def _parse_html(self, content: bytes) -> tuple[str, dict[str, Any]]:
        text = _html_to_text(content.decode("utf-8", errors="ignore"))
        # Pull operative passages — "EXEQUIBLE", "INEXEQUIBLE", "EN EL ENTENDIDO"
        operatives = []
        for m in re.finditer(
            r"\b(?:EXEQUIBLE|INEXEQUIBLE|EXEQUIBLES|INEXEQUIBLES)[,\s][^.]{0,500}\.",
            text,
        ):
            operatives.append(m.group(0).strip())
        return text, {"operative_passages": operatives}


__all__ = ["CorteConstitucionalScraper"]
