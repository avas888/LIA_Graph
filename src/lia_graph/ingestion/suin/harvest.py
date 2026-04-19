"""SUIN harvest CLI.

Invocation convention (see `docs/next/ingestion_suin.md` handoff):

    PYTHONPATH=src:. uv run python -m lia_graph.ingestion.suin.harvest \
        --scope et --out artifacts/suin/et

Writes `documents.jsonl`, `articles.jsonl`, `edges.jsonl`, `_harvest_manifest.json`
under `--out`. These are the inputs `lia_graph.ingestion.suin.bridge` converts
into the `ParsedArticle` / `ClassifiedEdge` rows the existing pipeline already
persists to Supabase + Falkor.

The CLI is deliberately simple — real crawl logic lives in `fetcher.py`, real
parsing in `parser.py`. This module is the thin orchestrator that binds them
and writes intermediate JSONL.
"""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any

from .fetcher import SITEMAPS, SEED_URLS, SitemapEntry, SuinFetcher, SuinFetchError
from .parser import (
    SuinDocument,
    UnknownVerb,
    normalize_doc_id,
    parse_document,
)

_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScopeDefinition:
    """Resolved scope: which sitemaps to walk, which seeds to pre-fetch, anchors."""

    sitemaps: tuple[SitemapEntry, ...]
    seed_urls: tuple[str, ...] = ()
    topic_anchors: tuple[tuple[str, str], ...] = ()
    deprecated: bool = False
    alias_of: str | None = None


_SCOPES: dict[str, ScopeDefinition] = {
    "tributario": ScopeDefinition(
        sitemaps=(SITEMAPS[0],),
        seed_urls=SEED_URLS.get("tributario", ()),
        topic_anchors=(
            ("decreto_624_1989", "Estatuto Tributario"),
            ("decreto_1625_2016", "Decreto Único Reglamentario Tributario"),
            ("ley_2277_2022", "Reforma Tributaria 2022"),
        ),
    ),
    "laboral": ScopeDefinition(
        sitemaps=(SITEMAPS[0],),
        seed_urls=SEED_URLS.get("laboral", ()),
        topic_anchors=(
            ("decreto_ley_2663_1950", "Código Sustantivo del Trabajo"),
            ("ley_100_1993", "Sistema General de Seguridad Social"),
            ("decreto_1072_2015", "Decreto Único Reglamentario del Sector Trabajo"),
            ("ley_2466_2025", "Reforma Laboral 2025"),
            ("ley_2381_2024", "Reforma Pensional 2024"),
        ),
    ),
    "laboral-tributario": ScopeDefinition(
        sitemaps=(SITEMAPS[0],),
        seed_urls=SEED_URLS.get("laboral-tributario", ()),
        topic_anchors=(
            ("et_art_114_1", "ET art 114-1 — Exoneración de parafiscales"),
            ("et_art_383_a_388", "ET arts 383–388 — Retención por pagos laborales"),
            ("ley_1607_2012", "Ley 1607/2012 — Origen exoneración parafiscales"),
        ),
    ),
    "jurisprudencia": ScopeDefinition(
        sitemaps=(SITEMAPS[1],),
        seed_urls=SEED_URLS.get("jurisprudencia", ()),
        topic_anchors=(
            ("consejo_estado_sala_tercera", "Consejo de Estado — Sala Tercera"),
            ("consejo_estado_sala_segunda", "Consejo de Estado — Sala Segunda"),
            ("corte_constitucional", "Corte Constitucional"),
        ),
    ),
    "full": ScopeDefinition(
        sitemaps=SITEMAPS,
        seed_urls=tuple(url for urls in SEED_URLS.values() for url in urls),
    ),
    "et": ScopeDefinition(
        sitemaps=(SITEMAPS[0],),
        seed_urls=SEED_URLS.get("tributario", ()),
        deprecated=True,
        alias_of="tributario",
    ),
}


def parser() -> argparse.ArgumentParser:
    cli = argparse.ArgumentParser(
        description=(
            "Harvest SUIN-Juriscol documents into artifacts/suin/<scope>/*.jsonl "
            "for the Lia_Graph pipeline."
        )
    )
    cli.add_argument(
        "--scope",
        required=True,
        choices=sorted(_SCOPES.keys()),
        help=(
            "Which crawl scope to run. `et` is a deprecated alias of `tributario`. "
            "New scopes: tributario, laboral, laboral-tributario, jurisprudencia, full."
        ),
    )
    cli.add_argument(
        "--out",
        required=True,
        type=Path,
        help="Output directory (e.g. artifacts/suin/et).",
    )
    cli.add_argument(
        "--cache-dir",
        type=Path,
        default=Path("cache/suin"),
        help="Local HTTP cache directory (default: cache/suin, gitignored).",
    )
    cli.add_argument(
        "--max-documents",
        type=int,
        default=0,
        help="Cap on documents harvested. 0 = no cap. Use >0 for smoke runs.",
    )
    cli.add_argument(
        "--rps",
        type=float,
        default=1.0,
        help="Max requests per second against SUIN.",
    )
    cli.add_argument(
        "--no-strict-verbs",
        dest="strict_verbs",
        action="store_false",
        help=(
            "Tolerate unknown SUIN verbs (skip the edge). Off by default — we "
            "prefer loud failures so the vocabulary stays up-to-date."
        ),
    )
    cli.set_defaults(strict_verbs=True)
    cli.add_argument(
        "--json",
        action="store_true",
        help="Emit a machine-readable summary on stdout.",
    )
    return cli


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
    return count


def _resolve_scope(scope: str) -> tuple[str, ScopeDefinition]:
    """Return (canonical_scope_name, definition), following alias links once."""
    if scope not in _SCOPES:
        raise KeyError(f"unknown scope {scope!r}")
    definition = _SCOPES[scope]
    if definition.alias_of:
        canonical = definition.alias_of
        _log.warning(
            "scope %r is a deprecated alias — resolving to %r", scope, canonical
        )
        return canonical, _SCOPES[canonical]
    return scope, definition


def _iter_scope_urls(
    fetcher: SuinFetcher,
    scope: str,
    *,
    max_documents: int,
) -> Iterable[str]:
    _, definition = _resolve_scope(scope)
    seen: set[str] = set()
    emitted = 0

    # Emit seeds first — they must be reached regardless of sitemap content.
    for seed_url in fetcher.iter_seeds(scope):
        if seed_url in seen:
            continue
        seen.add(seed_url)
        yield seed_url
        emitted += 1
        if max_documents and emitted >= max_documents:
            return

    for entry in definition.sitemaps:
        try:
            urls = fetcher.iter_sitemap(entry.url)
        except SuinFetchError as exc:
            if entry.required:
                raise
            _log.warning("optional sitemap %s failed: %s", entry.name, exc)
            continue
        for url in urls:
            if url in seen:
                continue
            seen.add(url)
            yield url
            emitted += 1
            if max_documents and emitted >= max_documents:
                return


def _url_to_doc_id(url: str) -> str:
    from urllib.parse import parse_qs, urlparse

    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    doc_id = (qs.get("id") or [None])[0]
    if doc_id:
        return str(doc_id)
    # Fallback: sanitize the last two path segments (accent-fold + whitespace-collapse)
    tail = "/".join(parsed.path.strip("/").split("/")[-2:])
    return normalize_doc_id(tail) or parsed.path.strip("/")


def run_harvest(
    *,
    scope: str,
    out: Path,
    cache_dir: Path = Path("cache/suin"),
    max_documents: int = 0,
    rps: float = 1.0,
    strict_verbs: bool = True,
    fetcher: SuinFetcher | None = None,
) -> dict[str, Any]:
    out.mkdir(parents=True, exist_ok=True)
    owns_fetcher = fetcher is None
    active_fetcher = fetcher or SuinFetcher(cache_dir=cache_dir, rps=rps)
    try:
        documents: list[SuinDocument] = []
        urls_seen: list[str] = []
        verb_counter: Counter[str] = Counter()
        unknown_failures: list[dict[str, str]] = []
        for url in _iter_scope_urls(active_fetcher, scope, max_documents=max_documents):
            urls_seen.append(url)
            try:
                html = active_fetcher.fetch(url)
            except SuinFetchError as exc:
                _log.warning("fetch failed for %s: %s", url, exc)
                continue
            doc_id = _url_to_doc_id(url)
            try:
                doc = parse_document(
                    html, doc_id=doc_id, ruta=url, strict_verbs=strict_verbs
                )
            except UnknownVerb as exc:
                unknown_failures.append(
                    {"url": url, "raw_verb": exc.raw, "hint": exc.hint or ""}
                )
                if strict_verbs:
                    raise
                continue
            documents.append(doc)
            for article in doc.articles:
                for edge in article.outbound_edges:
                    verb_counter[edge.verb] += 1
    finally:
        if owns_fetcher:
            active_fetcher.close()

    documents_path = out / "documents.jsonl"
    articles_path = out / "articles.jsonl"
    edges_path = out / "edges.jsonl"
    manifest_path = out / "_harvest_manifest.json"

    doc_rows = [
        {k: v for k, v in doc.to_dict().items() if k != "articles"} for doc in documents
    ]
    article_rows: list[dict[str, Any]] = []
    edge_rows: list[dict[str, Any]] = []
    for doc in documents:
        for article in doc.articles:
            article_row = {k: v for k, v in article.to_dict().items() if k != "outbound_edges"}
            article_row["doc_id"] = doc.doc_id
            article_rows.append(article_row)
            for edge in article.outbound_edges:
                edge_row = edge.to_dict() | {
                    "source_doc_id": doc.doc_id,
                    "source_article_key": article.article_number,
                    "source_article_fragment_id": article.article_fragment_id,
                }
                edge_rows.append(edge_row)

    documents_written = _write_jsonl(documents_path, doc_rows)
    articles_written = _write_jsonl(articles_path, article_rows)
    edges_written = _write_jsonl(edges_path, edge_rows)

    manifest = {
        "scope": scope,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "urls_crawled": len(urls_seen),
        "documents_parsed": documents_written,
        "articles_parsed": articles_written,
        "edges_parsed": edges_written,
        "verb_counts": dict(verb_counter),
        "unknown_verb_failures": unknown_failures,
        "paths": {
            "documents": str(documents_path),
            "articles": str(articles_path),
            "edges": str(edges_path),
        },
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        manifest = run_harvest(
            scope=args.scope,
            out=args.out,
            cache_dir=args.cache_dir,
            max_documents=max(args.max_documents, 0),
            rps=max(args.rps, 0.1),
            strict_verbs=args.strict_verbs,
        )
    except (SuinFetchError, UnknownVerb) as exc:
        payload = {"ok": False, "error": type(exc).__name__, "message": str(exc)}
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"SUIN harvest failed: {exc}")
        return 2

    if args.json:
        print(json.dumps({"ok": True, **manifest}, ensure_ascii=False, indent=2))
    else:
        print(
            f"SUIN harvest ok: scope={manifest['scope']} "
            f"docs={manifest['documents_parsed']} "
            f"articles={manifest['articles_parsed']} "
            f"edges={manifest['edges_parsed']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
