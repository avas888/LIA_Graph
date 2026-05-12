"""fix_v11_may Phase 11B — Falkor anchor resolver for the expert panel.

When the panel dispatcher (`orchestrator._retrieve_interpretation_docs`)
has article_refs extracted from the question/payload, this helper turns
them into an ordered tuple of interpretation `doc_id`s by walking the
`INTERPRETS` edges in cloud FalkorDB:

    MATCH (a:ArticleNode {article_number: $num})
          <-[:INTERPRETS]-(i:InterpretationNode)
    RETURN i.doc_id ORDER BY i.trust_tier DESC LIMIT $limit

This replaces the per-request word-shape lookup in
`interpretacion/article_index.py` with a graph traversal that:
  * scales beyond what Python can hold in memory,
  * picks up cross-corpus refresh changes via the next ingest run
    rather than via a Python cache invalidation, and
  * surfaces `trust_tier` ordering at the SQL/Cypher layer instead of
    re-implementing it in the retriever's scorer.

**Architectural note.** The plan in `docs/re-engineer/fix/fix_v11_may.md
§2.B` describes the chat *planner* emitting `interpretation_anchor_doc_ids`
as a seed on the retrieval plan. In the actual codebase the expert
panel is UI-triggered (`/api/expert-panel`) and not invoked from
`pipeline_d/orchestrator.py`; the planner never fires for panel
requests. The shipped wiring keeps the planner deterministic and
resolves the anchor here at the dispatcher boundary instead — the
helper is structured so a future chat-inline interpretation surface
can call the same function from the planner with no changes.

**Failure mode.** Per `feedback_lia_graph_cloud_writes_authorized`, the
anchor is a ranking signal, not a load-bearing surface. If Falkor is
unreachable, the loader hasn't run, or the Cypher errors for any other
reason, this helper returns an empty tuple AND records the reason in
the returned diagnostic. The dispatcher then falls back to the Python
`article_index` path (or, if even that returns nothing, to the
non-anchored hybrid_search ordering). Distinct from the main retrieval
path's "no silent fallback" non-negotiable: the article BFS retriever
in `pipeline_d/retriever_falkor.py` is load-bearing and must propagate
outages; this helper is not, and so degrades.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from ..graph.client import GraphClient, GraphWriteStatement


_DEFAULT_LIMIT_PER_ARTICLE = 8
_DEFAULT_TOTAL_CAP = 24


_ARTICLE_REF_NORMALIZE_RE = re.compile(r"[^0-9_\-]+")


def _normalize_article_ref_to_number(ref: str) -> str:
    """Map any of the article-ref shapes the codebase uses to the bare
    `article_number` value `ArticleNode.article_id` is keyed by for
    numbered articles.

    Accepts:
      * `et_art_115`     → `115`
      * `et_art_124_2`   → `124-2`
      * `art_115_et`     → `115`
      * `art_124_2_et`   → `124-2`
      * `art_115`        → `115`
      * `115`            → `115`
      * `124-2`          → `124-2`

    Returns `""` for shapes that can't be reduced to a bare number
    (e.g. `whole::path/to/doc.md` prose-only article keys — those
    can't be queried as numbered articles).
    """
    s = str(ref or "").strip().lower()
    if not s:
        return ""
    # Strip leading and trailing `et_art_` / `art_` / `_et` decorations.
    for prefix in ("et_art_", "art_"):
        if s.startswith(prefix):
            s = s[len(prefix):]
            break
    if s.endswith("_et"):
        s = s[:-3]
    # Allow `_` or `-` between sub-article digits; normalize to `-`
    # so the value matches the schema's article_id / article_number
    # form for numbered articles.
    s = s.replace("_", "-")
    s = _ARTICLE_REF_NORMALIZE_RE.sub("", s)
    if not re.fullmatch(r"\d{1,4}(?:-\d{1,4})?", s):
        return ""
    return s


def anchor_resolver_enabled(environ: Mapping[str, str] | None = None) -> bool:
    """Honor `LIA_PLANNER_INTERPRETATION_ANCHOR`. Default `on`. Set to
    `off` (or `0`, `false`, `no`) to skip the Falkor anchor and fall
    back to the Python `article_index` path."""
    env = os.environ if environ is None else environ
    raw = str(env.get("LIA_PLANNER_INTERPRETATION_ANCHOR", "on") or "on").strip().lower()
    return raw not in {"off", "0", "false", "no"}


@dataclass(frozen=True)
class AnchorResolution:
    """Resolved anchor doc_ids + diagnostic. Returned as a unit so the
    dispatcher can record the diagnostic on the panel response without
    re-deriving it. `doc_ids` preserves the trust-tier-then-article
    order produced by the Cypher cursor."""

    doc_ids: tuple[str, ...]
    diagnostic: Mapping[str, object] = field(default_factory=dict)


def _build_anchor_statement(article_number: str, limit_per_article: int) -> GraphWriteStatement:
    query = (
        "MATCH (a:ArticleNode {article_number: $num})"
        "<-[:INTERPRETS]-(i:InterpretationNode)\n"
        "RETURN i.doc_id AS doc_id, i.trust_tier AS trust_tier\n"
        "ORDER BY i.trust_tier DESC, i.doc_id ASC\n"
        f"LIMIT {int(limit_per_article)}\n"
    )
    return GraphWriteStatement(
        description=f"PlannerAnchorINTERPRETS(article_number={article_number})",
        query=query,
        parameters={"num": article_number},
    )


def resolve_anchor_doc_ids(
    article_refs: Iterable[str],
    *,
    graph_client: GraphClient | None = None,
    limit_per_article: int = _DEFAULT_LIMIT_PER_ARTICLE,
    total_cap: int = _DEFAULT_TOTAL_CAP,
) -> AnchorResolution:
    """Resolve an ordered, deduplicated tuple of interpretation doc_ids
    for the given article_refs. Returns an empty tuple AND a non-empty
    `diagnostic.reason` when no anchors could be produced (gate off,
    Falkor unavailable, no INTERPRETS edges for any of the refs, etc.).

    The returned `diagnostic` is also surfaced on the retriever's
    `retrieval_diagnostics` so the operator can confirm which path
    supplied the anchor at trace-inspection time.
    """
    refs_tuple = tuple(article_refs or ())
    if not refs_tuple:
        return AnchorResolution(
            doc_ids=(),
            diagnostic={
                "anchor_source": "skipped",
                "reason": "no_article_refs",
                "requested_refs": 0,
            },
        )
    if not anchor_resolver_enabled():
        return AnchorResolution(
            doc_ids=(),
            diagnostic={
                "anchor_source": "skipped",
                "reason": "flag_off",
                "requested_refs": len(refs_tuple),
            },
        )

    # Reduce refs to ArticleNode.article_number values; drop shapes that
    # can't be queried this way (prose-only `whole::...` keys).
    numbers: list[str] = []
    seen_numbers: set[str] = set()
    for ref in refs_tuple:
        number = _normalize_article_ref_to_number(ref)
        if not number or number in seen_numbers:
            continue
        seen_numbers.add(number)
        numbers.append(number)
    if not numbers:
        return AnchorResolution(
            doc_ids=(),
            diagnostic={
                "anchor_source": "skipped",
                "reason": "no_resolvable_numbers",
                "requested_refs": len(refs_tuple),
                "resolved_numbers": 0,
            },
        )

    client = graph_client or GraphClient.from_env()
    matched_doc_ids: list[str] = []
    seen_doc_ids: set[str] = set()
    matched_articles = 0
    errors: list[str] = []
    for number in numbers:
        statement = _build_anchor_statement(number, limit_per_article)
        try:
            result = client.execute(statement, strict=True)
        except Exception as exc:  # noqa: BLE001 — anchor is a ranking signal
            errors.append(f"{number}: {exc}")
            continue
        rows = list(result.rows or ())
        if not rows:
            continue
        matched_articles += 1
        for row in rows:
            doc_id = str(row.get("doc_id") or "").strip()
            if not doc_id or doc_id in seen_doc_ids:
                continue
            seen_doc_ids.add(doc_id)
            matched_doc_ids.append(doc_id)
            if len(matched_doc_ids) >= int(total_cap):
                break
        if len(matched_doc_ids) >= int(total_cap):
            break

    if errors and not matched_doc_ids:
        return AnchorResolution(
            doc_ids=(),
            diagnostic={
                "anchor_source": "falkor_error",
                "reason": "cypher_errors_no_results",
                "requested_refs": len(refs_tuple),
                "resolved_numbers": len(numbers),
                "matched_articles": 0,
                "errors": errors[:5],
            },
        )
    if not matched_doc_ids:
        return AnchorResolution(
            doc_ids=(),
            diagnostic={
                "anchor_source": "falkor_empty",
                "reason": "no_interprets_edges",
                "requested_refs": len(refs_tuple),
                "resolved_numbers": len(numbers),
                "matched_articles": 0,
            },
        )
    diagnostic: dict[str, Any] = {
        "anchor_source": "falkor",
        "requested_refs": len(refs_tuple),
        "resolved_numbers": len(numbers),
        "matched_articles": matched_articles,
        "matched_doc_ids": len(matched_doc_ids),
    }
    if errors:
        diagnostic["partial_errors"] = errors[:5]
    return AnchorResolution(
        doc_ids=tuple(matched_doc_ids),
        diagnostic=diagnostic,
    )


__all__ = [
    "AnchorResolution",
    "anchor_resolver_enabled",
    "resolve_anchor_doc_ids",
]
