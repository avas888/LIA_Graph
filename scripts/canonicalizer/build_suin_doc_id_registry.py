"""Build the canonical-norm-id → SUIN-doc-id registry — fixplan_v6 §3 step 1.

SUIN documents are keyed by an internal numeric `doc_id` (e.g. `1132325` for
Decreto 624/1989). Our canonical norm_ids are dotted (`decreto.1625.2016`,
`ley.100.1993`, `decreto.624.1989`/`et`, `cst`, …). The vigencia harness
needs to map a canonical norm_id to the SUIN URL that hosts the parent
document so the SUIN scraper can fetch + slice per-article text.

This script walks every harvested `artifacts/suin/*/documents.jsonl`,
parses the document title with a small regex table, and emits a flat JSON
registry at `var/suin_doc_id_registry.json`:

    {
      "decreto.624.1989":  {"suin_doc_id": "1132325",
                             "ruta":        "https://www.suin-juriscol.gov.co/viewDocument.asp?id=1132325",
                             "title":       "DECRETO 624 DE 1989 - Colombia | SUIN Juriscol"},
      "decreto.1625.2016": {...},
      "decreto.1072.2015": {...},
      "ley.100.1993":      {...},
      "cst":               {...},
      ...
    }

Coverage today (as harvested): the 9 legislative spines in
`laboral-tributario/documents.jsonl` (DURs 1625/1072, ET decreto 624,
CST consolidado + decreto 2663/1950, leyes 100/2277/2381/2466). The
jurisprudencia_full scope contains 3,370 sentencias + autos which the
title-regex table intentionally skips — vigencia extraction routes
those through the dedicated CC/CE scrapers.

When SUIN-Juriscol harvests grow new legislative scopes, extend the
`_TITLE_PATTERNS` table below — partial coverage is fine; the script
logs every unmatched title to stderr for triage.

Usage:
    PYTHONPATH=src:. uv run python scripts/canonicalizer/build_suin_doc_id_registry.py
    PYTHONPATH=src:. uv run python scripts/canonicalizer/build_suin_doc_id_registry.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

LOGGER = logging.getLogger("build_suin_doc_id_registry")

DEFAULT_OUTPUT_PATH = Path("var/suin_doc_id_registry.json")
DEFAULT_ARTIFACTS_ROOT = Path("artifacts/suin")
SUIN_BASE_URL = "https://www.suin-juriscol.gov.co/viewDocument.asp"


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
    }.get(auth, "dian")  # default to DIAN — most common
    return f"res.{auth_slug}.{int(m.group('num'))}.{m.group('year')}"


def _concepto(m: re.Match[str]) -> str:
    # SUIN may title these as "CONCEPTO N DE YYYY"; default issuer is DIAN.
    return f"concepto.dian.{int(m.group('num'))}.{m.group('year')}"


# Title-regex table. Order matters: more specific patterns first.
# Each pattern matches the SUIN document title (post strip-whitespace).
_TITLE_PATTERNS: tuple[_Pattern, ...] = (
    # CST consolidado — no number, special canonical id `cst`.
    _Pattern(
        rx=re.compile(r"^C[ÓO]DIGO\s+SUSTANTIVO\s+DEL\s+TRABAJO\b", re.IGNORECASE),
        builder=lambda m: "cst",
        description="CST",
    ),
    # CCo consolidado.
    _Pattern(
        rx=re.compile(r"^C[ÓO]DIGO\s+DE\s+COMERCIO\b", re.IGNORECASE),
        builder=lambda m: "cco",
        description="CCo",
    ),
    # Estatuto Tributario consolidado (dedicated alias on top of decreto.624.1989).
    _Pattern(
        rx=re.compile(r"^ESTATUTO\s+TRIBUTARIO\b", re.IGNORECASE),
        builder=lambda m: "et",
        description="ET (consolidado)",
    ),
    # LEY N DE YYYY
    _Pattern(
        rx=re.compile(
            r"^LEY\s+(?P<num>\d+)\s+DE\s+(?P<year>\d{4})\b",
            re.IGNORECASE,
        ),
        builder=_ley,
        description="LEY N DE YYYY",
    ),
    # DECRETO N DE YYYY (incl. DECRETO LEY, DECRETO LEGISLATIVO, DECRETO ÚNICO)
    _Pattern(
        rx=re.compile(
            r"^DECRETO(?:\s+(?:LEY|LEGISLATIVO|[ÚU]NICO|UNICO|REGLAMENTARIO))?"
            r"\s+(?P<num>\d+)\s+DE\s+(?P<year>\d{4})\b",
            re.IGNORECASE,
        ),
        builder=_decreto,
        description="DECRETO N DE YYYY",
    ),
    # RESOLUCION/RESOLUCIÓN [DIAN|MINHACIENDA|...] N DE YYYY
    _Pattern(
        rx=re.compile(
            r"^RESOLUCI[ÓO]N(?:\s+(?P<auth>DIAN|MINHACIENDA|MINTRABAJO|"
            r"SUPERSOCIEDADES|SUPERSOLIDARIA))?\s+(?P<num>\d+)\s+DE\s+(?P<year>\d{4})\b",
            re.IGNORECASE,
        ),
        builder=_resolucion,
        description="RESOLUCION N DE YYYY",
    ),
    # CONCEPTO N DE YYYY
    _Pattern(
        rx=re.compile(
            r"^CONCEPTO\s+(?P<num>\d+)\s+DE\s+(?P<year>\d{4})\b",
            re.IGNORECASE,
        ),
        builder=_concepto,
        description="CONCEPTO N DE YYYY",
    ),
)

# Aliases — when one canonical id should also resolve under another. Keeps
# the registry reachable from multiple downstream id conventions without
# duplicating SUIN entries. Kept tiny and deliberate.
_ALIASES: dict[str, str] = {
    # The Estatuto Tributario IS Decreto 624/1989 — both ids should point
    # at the same SUIN doc.
    "et": "decreto.624.1989",
    # CST consolidado is pinned to its dedicated SUIN doc (id 30019323),
    # not to decreto.2663.1950 (its origen). Both stay separately in the
    # registry; downstream callers can prefer the consolidado.
}


@dataclass
class _BuildStats:
    documents_seen: int = 0
    matched: int = 0
    unmatched: int = 0
    duplicates: int = 0


def _strip_suffix(title: str) -> str:
    """Strip the trailing ' - Colombia | SUIN Juriscol' SUIN tacks onto every title."""

    return re.sub(r"\s*-\s*Colombia\s*\|\s*SUIN\s*Juriscol\s*$", "", title or "").strip()


def canonical_from_title(title: str) -> str | None:
    """Map a SUIN document title to a canonical norm_id, or None if unmatched."""

    cleaned = _strip_suffix(title or "")
    for pat in _TITLE_PATTERNS:
        m = pat.rx.match(cleaned)
        if m:
            return pat.builder(m)
    return None


def iter_documents(root: Path, *, include_smoke: bool = False) -> Iterable[tuple[Path, dict]]:
    paths = sorted(root.glob("*/documents.jsonl"))
    if not include_smoke:
        paths = [p for p in paths if p.parent.name != "smoke"]
    for documents_path in paths:
        with documents_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield documents_path, json.loads(line)
                except json.JSONDecodeError as err:
                    LOGGER.warning("malformed row in %s: %s", documents_path, err)


def build_registry(
    root: Path,
    *,
    base_url: str = SUIN_BASE_URL,
    include_smoke: bool = False,
    sample_logger: Callable[[str, str, str], None] | None = None,
) -> tuple[dict[str, dict[str, str]], _BuildStats, list[tuple[str, str]]]:
    """Walk every SUIN scope and return (registry, stats, unmatched_samples)."""

    stats = _BuildStats()
    registry: dict[str, dict[str, str]] = {}
    unmatched: list[tuple[str, str]] = []

    for documents_path, row in iter_documents(root, include_smoke=include_smoke):
        stats.documents_seen += 1
        title = (row.get("title") or "").strip()
        doc_id = str(row.get("doc_id") or "").strip()
        ruta = (row.get("ruta") or "").strip() or f"{base_url}?id={doc_id}"
        canonical = canonical_from_title(title)
        if canonical is None:
            stats.unmatched += 1
            if len(unmatched) < 20:
                unmatched.append((doc_id, title))
            continue
        if canonical in registry and registry[canonical]["suin_doc_id"] != doc_id:
            stats.duplicates += 1
            LOGGER.info(
                "duplicate canonical %s — keeping doc_id=%s (existing), saw doc_id=%s in %s",
                canonical,
                registry[canonical]["suin_doc_id"],
                doc_id,
                documents_path.name,
            )
            continue
        registry[canonical] = {
            "suin_doc_id": doc_id,
            "ruta": ruta,
            "title": title,
        }
        stats.matched += 1
        if sample_logger is not None:
            sample_logger(documents_path.name, title, canonical)

    # Apply aliases — only when alias target exists.
    for alias, target in _ALIASES.items():
        if alias in registry:
            continue
        if target in registry:
            entry = dict(registry[target])
            entry["alias_of"] = target
            registry[alias] = entry

    return registry, stats, unmatched


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--root", default=str(DEFAULT_ARTIFACTS_ROOT),
                   help="Root directory containing per-scope documents.jsonl files.")
    p.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH),
                   help="Where to write the registry JSON.")
    p.add_argument("--dry-run", action="store_true",
                   help="Print the first 20 matches and stats; do not write the registry.")
    p.add_argument("--include-smoke", action="store_true",
                   help="Include the smoke/ fixture scope (excluded by default — its "
                        "ruta values are local paths, not real SUIN URLs).")
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    root = Path(args.root)
    if not root.is_dir():
        LOGGER.error("artifacts root not found: %s", root)
        return 2

    samples: list[tuple[str, str, str]] = []

    def _log_sample(scope: str, title: str, canonical: str) -> None:
        if len(samples) < 20:
            samples.append((scope, title, canonical))

    registry, stats, unmatched = build_registry(
        root, include_smoke=args.include_smoke, sample_logger=_log_sample
    )

    print("# Sample matches (first 20):", file=sys.stderr)
    for scope, title, canonical in samples:
        print(f"  {scope:32s}  {canonical:32s}  ← {title}", file=sys.stderr)
    print("", file=sys.stderr)
    print(
        f"# Stats: documents_seen={stats.documents_seen} "
        f"matched={stats.matched} unmatched={stats.unmatched} "
        f"duplicates_skipped={stats.duplicates} "
        f"final_registry_entries={len(registry)}",
        file=sys.stderr,
    )
    if unmatched:
        print(f"# Sample unmatched titles ({len(unmatched)} of {stats.unmatched}):", file=sys.stderr)
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
