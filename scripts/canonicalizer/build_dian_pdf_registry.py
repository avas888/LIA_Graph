"""Build the canonical-norm-id → DIAN-PDF URL registry (next_v7 P2).

DIAN's `/normatividad/Normatividad/` PDF layout uses URLs of shape::

    https://www.dian.gov.co/normatividad/Normatividad/Resolución <NNNNNN> de <DD-MM-YYYY>.pdf

The number portion has leading zeros (5 or 6 digits) and the date
suffix can't be reconstructed from the canonical norm_id alone — so
we must scrape DIAN landing pages to enumerate available PDFs and map
canonical → URL.

Discovery strategy: walk a curated set of DIAN normativa landing
pages. Each page lists per-resolution PDF links with anchor text or
href patterns we can map to the canonical norm_id (``res.dian.<num>.<year>``).

Output: ``var/dian_pdf_registry.json`` shape::

    {
      "res.dian.13.2021": {
        "url": "https://www.dian.gov.co/normatividad/Normatividad/Resolución 000013 de 11-02-2021.pdf",
        "number": "000013",
        "date": "11-02-2021",
        "title": "Resolución 000013 de 2021"
      },
      ...
    }

Usage:
    PYTHONPATH=src:. uv run python scripts/canonicalizer/build_dian_pdf_registry.py
    PYTHONPATH=src:. uv run python scripts/canonicalizer/build_dian_pdf_registry.py --dry-run
"""

from __future__ import annotations

import argparse
import html
import json
import logging
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable

LOGGER = logging.getLogger("build_dian_pdf_registry")

DEFAULT_OUTPUT_PATH = Path("var/dian_pdf_registry.json")

# Curated landing pages. Each is a DIAN normativa landing that lists
# resolución PDFs we want to canonicalize. Add new pages here as the
# coverage need grows; the URL-extraction regex is page-agnostic.
LANDING_PAGES: tuple[tuple[str, str], ...] = (
    (
        "https://www.dian.gov.co/impuestos/factura-electronica/documentacion/Paginas/normativa.aspx",
        "Factura electrónica — Normativa",
    ),
    # When new gaps appear, extend this list. Probe candidates:
    #   /normatividad/tributaria/Paginas/Resoluciones.aspx
    #   /normatividad/aduanera/Paginas/Resoluciones.aspx
    # The PDF naming convention is uniform across the site, so the
    # extractor regex below works for any landing page that links to
    # ``/normatividad/Normatividad/Resolución <num> de <date>.pdf``.
)


_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36 "
    "Lia-Graph/1.0 (compliance registry builder)"
)


# Match an href to a Resolución PDF. The site mixes raw UTF-8 ("ó")
# with %20-encoded spaces between tokens. We accept any of: literal
# space, %20, +, -, _ as the inter-token separator.
_SEP = r"(?:%20|\+|\s|[\-_])+"
_PDF_HREF_PATTERN = re.compile(
    r'href="([^"]*?Normatividad/'
    r"(?:Resoluci(?:ón|%C3%B3n)|Resolucion)"
    rf"{_SEP}(\d{{4,6}}){_SEP}de{_SEP}(\d{{2}}-\d{{2}}-\d{{4}})\.pdf)\"",
    re.IGNORECASE,
)


@dataclass
class _BuildStats:
    pages_walked: int = 0
    raw_links: int = 0
    matched: int = 0
    duplicates_skipped: int = 0
    unmatched: int = 0


_SSL_CONTEXT = None


def _ssl_context():
    """SSL context that delegates to the OS trust store via truststore.

    DIAN's cert chain occasionally includes intermediates not in
    certifi's bundle. Mirrors the same pattern as the Función Pública
    registry builder.
    """

    global _SSL_CONTEXT
    if _SSL_CONTEXT is not None:
        return _SSL_CONTEXT
    import ssl
    try:
        import truststore  # type: ignore
        _SSL_CONTEXT = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        return _SSL_CONTEXT
    except ImportError:
        pass
    try:
        import certifi  # type: ignore
        _SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        _SSL_CONTEXT = ssl.create_default_context()
    return _SSL_CONTEXT


def _http_get(url: str) -> str | None:
    """One-shot HTTPS GET with browser UA, OS-store SSL, and 30s timeout."""

    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        ctx = _ssl_context()
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as err:
        LOGGER.warning("HTTP %d on %s", err.code, url)
        return None
    except Exception as err:
        LOGGER.warning("fetch failed for %s: %s", url, err)
        return None


def _canonical_for_resolucion(number_raw: str, date_str: str) -> str:
    """``res.dian.<int(number)>.<year>`` (leading zeros stripped)."""

    number = int(number_raw)  # strips leading zeros: "000013" → 13
    year = date_str.split("-")[-1]
    return f"res.dian.{number}.{year}"


def _normalize_href(href: str, base_url: str) -> str:
    """Resolve relative hrefs and decode the URL into a clean string."""

    decoded = urllib.parse.unquote(html.unescape(href))
    if decoded.startswith("//"):
        decoded = "https:" + decoded
    elif decoded.startswith("/"):
        parsed = urllib.parse.urlparse(base_url)
        decoded = f"{parsed.scheme}://{parsed.netloc}{decoded}"
    return decoded


def _walk_landing_page(
    url: str,
    *,
    rate_limit: float = 0.5,
) -> Iterable[tuple[str, str, str]]:
    """Yield (canonical_norm_id, decoded_url, raw_href) tuples from a landing page."""

    LOGGER.info("Walking landing page %s ...", url)
    body = _http_get(url)
    time.sleep(rate_limit)
    if body is None:
        return
    seen_canon: set[str] = set()
    for match in _PDF_HREF_PATTERN.finditer(body):
        href = match.group(1)
        number = match.group(2)
        date_str = match.group(3)
        canonical = _canonical_for_resolucion(number, date_str)
        if canonical in seen_canon:
            continue
        seen_canon.add(canonical)
        normalized_url = _normalize_href(href, url)
        yield canonical, normalized_url, href


def build_registry(
    landing_pages: tuple[tuple[str, str], ...] = LANDING_PAGES,
    *,
    rate_limit: float = 0.5,
    sample_logger: Callable[[str, str, str], None] | None = None,
) -> tuple[dict[str, dict[str, str]], _BuildStats, list[tuple[str, str]]]:
    stats = _BuildStats()
    registry: dict[str, dict[str, str]] = {}
    unmatched: list[tuple[str, str]] = []

    for url, label in landing_pages:
        stats.pages_walked += 1
        for canonical, normalized_url, raw_href in _walk_landing_page(url, rate_limit=rate_limit):
            stats.raw_links += 1
            # Pull the number + date back out so we record them too.
            m = re.search(
                r"(\d{4,6})\s+de\s+(\d{2}-\d{2}-\d{4})\.pdf",
                normalized_url,
                re.IGNORECASE,
            )
            number = m.group(1) if m else ""
            date_str = m.group(2) if m else ""
            year = date_str.split("-")[-1] if date_str else ""
            title = f"Resolución {int(number) if number else 0} de {year}" if number and year else canonical

            if canonical in registry:
                if registry[canonical]["url"] != normalized_url:
                    stats.duplicates_skipped += 1
                continue
            registry[canonical] = {
                "url": normalized_url,
                "number": number,
                "date": date_str,
                "title": title,
            }
            stats.matched += 1
            if sample_logger is not None:
                sample_logger(label, title, canonical)

    return registry, stats, unmatched


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    p.add_argument("--dry-run", action="store_true",
                   help="Print the first 20 matches and stats; don't write.")
    p.add_argument("--rate-limit", type=float, default=0.5,
                   help="Seconds between landing-page requests.")
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    samples: list[tuple[str, str, str]] = []

    def _log_sample(page: str, title: str, canonical: str) -> None:
        if len(samples) < 20:
            samples.append((page, title, canonical))

    registry, stats, _ = build_registry(rate_limit=args.rate_limit, sample_logger=_log_sample)

    print("# Sample matches:", file=sys.stderr)
    for page, title, canonical in samples:
        print(f"  {canonical:24s}  ← {title[:60]}", file=sys.stderr)
    print("", file=sys.stderr)
    print(
        f"# Stats: pages={stats.pages_walked} raw_links={stats.raw_links} "
        f"matched={stats.matched} unmatched={stats.unmatched} "
        f"duplicates_skipped={stats.duplicates_skipped} "
        f"final_registry_entries={len(registry)}",
        file=sys.stderr,
    )

    if args.dry_run:
        print("# --dry-run set — not writing.", file=sys.stderr)
        return 0 if registry else 1

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(registry, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"# Wrote {out_path} ({len(registry)} entries).", file=sys.stderr)
    return 0 if registry else 1


if __name__ == "__main__":
    sys.exit(main())
