"""Scraper for https://www.consejodeestado.gov.co/.

Coverage: Sentencias de nulidad + autos de suspensión provisional.
Primary source for `sent.ce.*` and `auto.ce.*` norm_ids.

The CE site is a JS-rendered SPA — direct radicado URLs return 404.
Until the live-fetch path lands (Selenium/playwright; out of scope for
fixplan_v5), we resolve known acid-test ids from local HTML fixtures
under ``tests/fixtures/scrapers/consejo_estado/``. Fixture text is
intentionally placeholder — real bodies arrive with the brief 14
expert delivery (per ``docs/re-engineer/fixplan_v5.md`` §3 blocker #2,
"fixture-only path").
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lia_graph.scrapers.base import Scraper, ScraperFetchResult
from lia_graph.scrapers.secretaria_senado import _html_to_text


_BASE_URL = "https://www.consejodeestado.gov.co/documentos/boletines"

# Repo-root-anchored path to the per-source fixture tree.
# ``__file__`` resolves to ``src/lia_graph/scrapers/consejo_estado.py``;
# four ``parent`` hops land on the repo root regardless of CWD.
_FIXTURE_ROOT = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "tests"
    / "fixtures"
    / "scrapers"
    / "consejo_estado"
)


def _fixture_path_for(norm_id: str) -> Path | None:
    """Map a CE norm_id to its expected fixture path on disk.

    ``auto.ce.<rad>.<YYYY>.<MM>.<DD>`` → ``autos/<rad>.<YYYY>.<MM>.<DD>.html``
    ``sent.ce.<rad>.<YYYY>.<MM>.<DD>`` → ``sentencias/<rad>.<YYYY>.<MM>.<DD>.html``

    For ids without a trailing date triple (e.g. unification rulings such
    as ``sent.ce.2022CE-SUJ-4-002``), the suffix after the ``sent.ce.`` /
    ``auto.ce.`` prefix becomes the filename stem verbatim.

    Returns ``None`` for ids the scraper does not own.
    """

    if norm_id.startswith("auto.ce."):
        suffix = norm_id[len("auto.ce.") :]
        return _FIXTURE_ROOT / "autos" / f"{suffix}.html"
    if norm_id.startswith("sent.ce."):
        suffix = norm_id[len("sent.ce.") :]
        return _FIXTURE_ROOT / "sentencias" / f"{suffix}.html"
    return None


class ConsejoEstadoScraper(Scraper):
    source_id = "consejo_estado"
    rate_limit_seconds = 1.0
    _handled_types = {"sentencia_ce", "auto_ce"}

    def _resolve_url(self, norm_id: str) -> str | None:
        if not (norm_id.startswith("sent.ce.") or norm_id.startswith("auto.ce.")):
            return None
        # Fixture-first: when a local HTML fixture exists for this id,
        # prefer it. Lets G6/I3/I4 batches succeed against staged content
        # while the live SPA-fetch path is out of scope.
        fixture = _fixture_path_for(norm_id)
        if fixture is not None and fixture.is_file():
            return f"file://{fixture.resolve()}"
        # Fall back to the legacy boletines URL pattern. Returns 404
        # against the live CE site today (SPA), but preserves the prior
        # behavior so tests / cache lookups that pre-date fixtures keep
        # the same surface.
        return f"{_BASE_URL}/{norm_id.replace('.', '_')}.html"

    def fetch(self, norm_id: str) -> ScraperFetchResult | None:
        """Override base ``fetch`` to short-circuit fixture URLs.

        For ``file://`` URLs (fixture-first hits), read the file directly
        instead of going through ``_http_get`` — keeps the base class free
        of file-scheme handling and avoids urllib's quirks around local
        paths.
        """

        url = self._resolve_url(norm_id)
        if url is None:
            return None
        if not url.startswith("file://"):
            return super().fetch(norm_id)

        cached = self.cache.get(self.source_id, url)
        if cached is not None:
            from lia_graph.scrapers.base import _entry_to_result

            return _entry_to_result(norm_id, cached, cache_hit=True)

        fixture_path = Path(url[len("file://") :])
        try:
            content = fixture_path.read_bytes()
        except OSError:
            return None
        parsed_text, parsed_meta = self._parse_html(content)
        self.cache.put(
            source=self.source_id,
            url=url,
            content=content,
            status_code=200,
            content_type="text/html",
            canonical_norm_id=norm_id,
            parsed_text=parsed_text,
            parsed_meta={**parsed_meta, "fixture_only": True},
        )
        return ScraperFetchResult(
            norm_id=norm_id,
            source=self.source_id,
            url=url,
            fetched_at_utc=datetime.now(timezone.utc).isoformat(),
            status_code=200,
            parsed_text=parsed_text,
            parsed_meta={**parsed_meta, "fixture_only": True},
            cache_hit=False,
        )

    def _parse_html(self, content: bytes) -> tuple[str, dict[str, Any]]:
        text = _html_to_text(content.decode("utf-8", errors="ignore"))
        return text, {}


__all__ = ["ConsejoEstadoScraper"]
