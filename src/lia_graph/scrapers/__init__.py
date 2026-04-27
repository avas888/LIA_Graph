"""fixplan_v3 sub-fix 1B-α — scraper + cache infrastructure for primary sources.

Five scrapers covering the universe of authoritative Colombian tax-law
primary sources (per fixplan_v3 §2.2):

  * `secretaria_senado.py` — Leyes (incluye ET); modification notes.
  * `dian_normograma.py`   — Decretos tributarios + resoluciones DIAN + conceptos.
  * `suin_juriscol.py`     — Toda la legislación nacional con histórico.
  * `corte_constitucional.py` — Sentencias C-, autos de suspensión.
  * `consejo_estado.py`    — Sentencias de nulidad, autos de suspensión.

Each scraper is a thin HTTP fetcher + HTML parser feeding the SQLite cache
(`var/scraper_cache.db`). The cache is keyed by `(source, url)` plus the
fixplan_v3 v3-additive `canonical_norm_id` column for direct lookup by
canonical id.

The skill harness (1B-β) consumes scrapers via the `ScraperRegistry`
protocol — call `registry.fetch(norm_id)` and the registry routes to the
right scraper based on `norm_type`.
"""

from lia_graph.scrapers.base import (
    Scraper,
    ScraperFetchResult,
    ScraperRegistry,
)
from lia_graph.scrapers.cache import ScraperCache

__all__ = [
    "Scraper",
    "ScraperCache",
    "ScraperFetchResult",
    "ScraperRegistry",
]
