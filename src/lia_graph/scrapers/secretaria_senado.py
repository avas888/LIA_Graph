"""Scraper for https://www.secretariasenado.gov.co/senado/basedoc/.

Coverage: Leyes (incluye ET), modification notes per artículo. Use as one
of the two primary sources for any `ley.*` or `et.art.*` norm_id per the
skill's `fuentes-primarias.md` rules.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Any

from lia_graph.scrapers.base import Scraper


_BASE_URL = "https://www.secretariasenado.gov.co/senado/basedoc"


class SecretariaSenadoScraper(Scraper):
    source_id = "secretaria_senado"
    rate_limit_seconds = 0.5
    _handled_types = {"ley", "ley_articulo", "estatuto", "articulo_et"}

    def _resolve_url(self, norm_id: str) -> str | None:
        if norm_id == "et":
            return f"{_BASE_URL}/codigo/estatuto_tributario.html"
        if norm_id.startswith("et.art."):
            article = norm_id.split(".", 2)[2]
            # ET sub-units share the article's URL — content is on one page.
            article_base = article.split(".")[0]
            return f"{_BASE_URL}/codigo/estatuto_tributario_pr{_pr_section(article_base)}.html"
        if norm_id.startswith("ley."):
            parts = norm_id.split(".")
            if len(parts) < 3:
                return None
            num = parts[1]
            year = parts[2]
            return f"{_BASE_URL}/ley_{num}_{year}.html"
        return None

    def _parse_html(self, content: bytes) -> tuple[str, dict[str, Any]]:
        text = _html_to_text(content.decode("utf-8", errors="ignore"))
        # Extract any "Modificado por" / "Derogado por" notes the page renders.
        notes = []
        for m in re.finditer(
            r"(?:Modificado|Derogado|Adicionado|Sustituido)\s+por[^.]+\.",
            text,
            flags=re.IGNORECASE,
        ):
            notes.append(m.group(0).strip())
        return text, {"modification_notes": notes}


def _pr_section(article_str: str) -> str:
    """ET pages are bucketed in `_pr0..pr109` files; quick numeric mapping."""

    digits = re.match(r"\d+", article_str)
    if not digits:
        return "0"
    n = int(digits.group(0))
    return str(n // 10)


# ---------------------------------------------------------------------------
# Lightweight HTML→text (stdlib-only)
# ---------------------------------------------------------------------------


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._buf: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs):  # type: ignore[override]
        if tag in ("script", "style"):
            self._skip_depth += 1

    def handle_endtag(self, tag: str):  # type: ignore[override]
        if tag in ("script", "style") and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str):  # type: ignore[override]
        if self._skip_depth == 0:
            self._buf.append(data)

    def get_text(self) -> str:
        return re.sub(r"\s+", " ", "".join(self._buf)).strip()


def _html_to_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    return parser.get_text()


__all__ = ["SecretariaSenadoScraper"]
