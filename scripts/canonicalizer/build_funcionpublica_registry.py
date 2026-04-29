"""Build the canonical-norm-id → Función Pública doc-id registry.

Función Pública's gestor normativo (`https://www.funcionpublica.gov.co/eva/gestornormativo/`)
exposes legislative documents under opaque numeric `i=<N>` URLs. Like
SUIN, we need a registry mapping our canonical norm_ids
(``decreto.1625.2016``, ``ley.100.1993``, ``cst``) to the right
``i=`` parameter.

Discovery strategy: walk a small set of curated **index pages**
(category landings — e.g. "Decretos Únicos Reglamentarios" at
``i=62255``) and harvest the per-document links. Each link's anchor
text gives us the title, which we map via a regex table to the
canonical norm_id (same approach as SUIN).

The site's `?q=` search is **not** a reliable discovery surface — it
returns the same default 5 docs regardless of the query string. So
this script does NOT use search; it walks index pages and follows
their links.

Output: ``var/funcionpublica_doc_id_registry.json`` with the same
shape as the SUIN registry:

    {
      "decreto.1625.2016": {"funcion_publica_doc_id": "83233",
                             "ruta": "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=83233",
                             "title": "Decreto 1625 de 2016"},
      "decreto.1072.2015": {"funcion_publica_doc_id": "72173", ...},
      ...
    }

Usage:
    PYTHONPATH=src:. uv run python scripts/canonicalizer/build_funcionpublica_registry.py
    PYTHONPATH=src:. uv run python scripts/canonicalizer/build_funcionpublica_registry.py --dry-run
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
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

LOGGER = logging.getLogger("build_funcionpublica_registry")

DEFAULT_OUTPUT_PATH = Path("var/funcionpublica_doc_id_registry.json")
BASE_URL = "https://www.funcionpublica.gov.co/eva/gestornormativo"


# Curated index pages — each is a Función Pública doc that lists OTHER
# Función Pública docs in its body. Walking these gives us the doc-id
# inventory without depending on the broken `?q=` search.
INDEX_PAGES: tuple[tuple[int, str], ...] = (
    (62255, "Decretos Únicos Reglamentarios"),
    # Add more as discovered. Leyes index, resolution index, etc. would
    # extend coverage. For v6.1 MVP the DUR index alone gives us
    # DUR-1625, DUR-1072, and ~25 other DURs as backup primary source.
)


_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36 "
    "Lia-Graph/1.0 (compliance registry builder)"
)


@dataclass(frozen=True)
class _Pattern:
    rx: re.Pattern[str]
    builder: Callable[[re.Match[str]], str]
    description: str


def _ley(m: re.Match[str]) -> str:
    return f"ley.{int(m.group('num'))}.{m.group('year')}"


def _decreto(m: re.Match[str]) -> str:
    return f"decreto.{int(m.group('num'))}.{m.group('year')}"


def _resolucion(m: re.Match[str]) -> str:
    auth = (m.group("auth") or "").lower().strip()
    auth_slug = {
        "dian": "dian",
        "minhacienda": "minhacienda",
        "mintrabajo": "mintrabajo",
        "supersociedades": "supersociedades",
        "supersolidaria": "supersolidaria",
    }.get(auth, "dian")
    return f"res.{auth_slug}.{int(m.group('num'))}.{m.group('year')}"


def _concepto(m: re.Match[str]) -> str:
    return f"concepto.dian.{int(m.group('num'))}.{m.group('year')}"


# Title-regex table. Reuses the SUIN patterns since titles are similar.
# Pattern shapes are case-insensitive to handle "Decreto 1625" / "DECRETO 1625".
_TITLE_PATTERNS: tuple[_Pattern, ...] = (
    _Pattern(
        rx=re.compile(r"^\s*C[ÓO]DIGO\s+SUSTANTIVO\s+DEL\s+TRABAJO", re.IGNORECASE),
        builder=lambda m: "cst",
        description="CST",
    ),
    _Pattern(
        rx=re.compile(r"^\s*C[ÓO]DIGO\s+DE\s+COMERCIO", re.IGNORECASE),
        builder=lambda m: "cco",
        description="CCo",
    ),
    _Pattern(
        rx=re.compile(r"^\s*ESTATUTO\s+TRIBUTARIO", re.IGNORECASE),
        builder=lambda m: "et",
        description="ET",
    ),
    _Pattern(
        rx=re.compile(
            r"^\s*LEY\s+(?P<num>\d+)\s+DE\s+(?P<year>\d{4})",
            re.IGNORECASE,
        ),
        builder=_ley,
        description="LEY N DE YYYY",
    ),
    _Pattern(
        rx=re.compile(
            r"^\s*DECRETO(?:\s+(?:LEY|LEGISLATIVO|[ÚU]NICO|UNICO|REGLAMENTARIO))?"
            r"\s+(?P<num>\d+)\s+DE\s+(?P<year>\d{4})",
            re.IGNORECASE,
        ),
        builder=_decreto,
        description="DECRETO N DE YYYY",
    ),
    _Pattern(
        rx=re.compile(
            r"^\s*RESOLUCI[ÓO]N(?:\s+(?P<auth>DIAN|MINHACIENDA|MINTRABAJO|"
            r"SUPERSOCIEDADES|SUPERSOLIDARIA))?\s+(?P<num>\d+)\s+DE\s+(?P<year>\d{4})",
            re.IGNORECASE,
        ),
        builder=_resolucion,
        description="RESOLUCION N DE YYYY",
    ),
    _Pattern(
        rx=re.compile(
            r"^\s*CONCEPTO\s+(?:UNIFICADO\s+)?(?P<num>\d+)\s+DE\s+(?P<year>\d{4})",
            re.IGNORECASE,
        ),
        builder=_concepto,
        description="CONCEPTO N DE YYYY",
    ),
)


_LINK_PATTERN = re.compile(
    r'href="(?:[^"]*?)norma\.php\?i=(\d+)"[^>]*>([^<]{3,200})',
    re.IGNORECASE,
)


@dataclass
class _BuildStats:
    pages_walked: int = 0
    raw_links: int = 0
    matched: int = 0
    unmatched: int = 0
    duplicates_skipped: int = 0


def _strip_html_entities(text: str) -> str:
    # Unescape entities, normalize NBSPs to regular spaces, collapse runs.
    text = html.unescape(text or "")
    text = text.replace("\xa0", " ").replace("​", "")
    return re.sub(r"\s+", " ", text).strip()


def canonical_from_title(title: str) -> str | None:
    """Map a Función Pública link title to a canonical norm_id, or None."""

    cleaned = _strip_html_entities(title or "")
    for pat in _TITLE_PATTERNS:
        m = pat.rx.search(cleaned)  # search not match — title may have decoration
        if m:
            return pat.builder(m)
    return None


_SSL_CONTEXT = None


def _ssl_context():
    """SSL context that trusts the OS Keychain (via truststore) when
    available, falling back to certifi, then OS default.

    Función Pública's cert chain includes a Sectigo intermediate not
    in certifi's bundle as of 2026. macOS Keychain via truststore
    delegates verification to the system trust store and works.
    Same pattern as ``src/lia_graph/ingestion/suin/fetcher.py``.
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
    """One-shot HTTPS GET with browser UA, certifi SSL, and 30s timeout."""

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


def _walk_index_page(
    page_id: int,
    *,
    base_url: str = BASE_URL,
    rate_limit: float = 0.5,
) -> Iterable[tuple[str, str]]:
    """Yield (doc_id, title) tuples for every link out of an index page."""

    url = f"{base_url}/norma.php?i={page_id}"
    LOGGER.info("Walking index page i=%d ...", page_id)
    body = _http_get(url)
    time.sleep(rate_limit)
    if body is None:
        return
    seen: set[str] = set()
    for match in _LINK_PATTERN.finditer(body):
        doc_id = match.group(1)
        title = match.group(2).strip()
        if doc_id in seen:
            continue
        seen.add(doc_id)
        yield doc_id, title


def build_registry(
    index_pages: tuple[tuple[int, str], ...] = INDEX_PAGES,
    *,
    base_url: str = BASE_URL,
    rate_limit: float = 0.5,
    sample_logger: Callable[[str, str, str], None] | None = None,
) -> tuple[dict[str, dict[str, str]], _BuildStats, list[tuple[str, str]]]:
    stats = _BuildStats()
    registry: dict[str, dict[str, str]] = {}
    unmatched: list[tuple[str, str]] = []

    for page_id, page_label in index_pages:
        stats.pages_walked += 1
        for doc_id, raw_title in _walk_index_page(page_id, base_url=base_url, rate_limit=rate_limit):
            stats.raw_links += 1
            title = _strip_html_entities(raw_title)
            canonical = canonical_from_title(raw_title)
            if canonical is None:
                stats.unmatched += 1
                if len(unmatched) < 20:
                    unmatched.append((doc_id, title))
                continue
            if canonical in registry:
                if registry[canonical]["funcion_publica_doc_id"] != doc_id:
                    stats.duplicates_skipped += 1
                continue
            registry[canonical] = {
                "funcion_publica_doc_id": doc_id,
                "ruta": f"{base_url}/norma.php?i={doc_id}",
                "title": title,
            }
            stats.matched += 1
            if sample_logger is not None:
                sample_logger(page_label, title, canonical)

    # Hand-curated additions for known docs the index walk doesn't cover.
    # When an operator finds a new doc_id, add it here AND to the index
    # walk if there's a category page that points to it.
    _SEED_OVERRIDES: dict[str, dict[str, str]] = {
        # decreto.624.1989 (ET) — sometimes appears in the leyes index;
        # if not, this seeds a known good ID. Probe needed before using.
    }
    for canonical, entry in _SEED_OVERRIDES.items():
        if canonical not in registry:
            registry[canonical] = entry
            stats.matched += 1

    return registry, stats, unmatched


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    p.add_argument("--dry-run", action="store_true",
                   help="Print the first 20 matches and stats; don't write.")
    p.add_argument("--rate-limit", type=float, default=0.5,
                   help="Seconds between requests to Función Pública.")
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

    registry, stats, unmatched = build_registry(
        rate_limit=args.rate_limit, sample_logger=_log_sample
    )

    print("# Sample matches:", file=sys.stderr)
    for page, title, canonical in samples:
        print(f"  {canonical:32s}  ← {title[:75]}", file=sys.stderr)
    print("", file=sys.stderr)
    print(
        f"# Stats: pages={stats.pages_walked} raw_links={stats.raw_links} "
        f"matched={stats.matched} unmatched={stats.unmatched} "
        f"duplicates_skipped={stats.duplicates_skipped} "
        f"final_registry_entries={len(registry)}",
        file=sys.stderr,
    )
    if unmatched:
        print(f"# Sample unmatched ({len(unmatched)} of {stats.unmatched}):", file=sys.stderr)
        for doc_id, title in unmatched[:10]:
            print(f"  {doc_id:>10s}  {title[:100]}", file=sys.stderr)

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
