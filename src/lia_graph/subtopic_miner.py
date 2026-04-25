"""Subtopic mining primitives (Phase 3 of subtopic_generationv1).

Pure, side-effect-free helpers consumed by
``scripts/mine_subtopic_candidates.py``:

- :func:`normalize_label` — Spanish-slug normalization + light stemming.
- :func:`cluster_labels_by_parent_topic` — group candidate labels per
  parent topic via (1) slug-merge (lexical) then (2) agglomerative
  single-linkage clustering over cosine similarity of embeddings.
- :func:`rank_proposals` — deterministic ordering within each parent.
- :func:`build_proposal_json` — ties it all together into the final
  JSON payload (does not write to disk).

Contract: see ``docs/done/next/subtopic_generationv1-contracts.md`` — field
names and JSON shape are pinned there.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Callable, Iterable

# Default Spanish suffix stemming rules. Applied longest-suffix-first so
# e.g. ``_independientes`` wins over ``_independiente``. The values are
# the canonical form we collapse to.
_DEFAULT_STEM_RULES: dict[str, str] = {
    "_independientes": "_independiente",
    "_empleadores": "_empleador",
    "_trabajadores": "_trabajador",
    "_costos": "_costo",
    "_aportes": "_aporte",
}


# ---------------------------------------------------------------------------
# Label normalization
# ---------------------------------------------------------------------------


def normalize_label(label: str, *, stem_rules: dict[str, str] | None = None) -> str:
    """Normalize a free-form Spanish label into a stable slug.

    Steps:
      1. Lowercase.
      2. Strip accents via ``unicodedata`` NFKD (mirrors
         ``ingestion_classifier._slugify``).
      3. Replace any run of non-word characters with ``_``.
      4. Strip leading/trailing ``_``.
      5. Apply Spanish suffix stemming (longest suffix first).

    The ``stem_rules`` parameter, if provided, fully replaces the
    built-in defaults — tests use it to assert deterministic behavior
    without shadow-copying the module-level map.
    """

    rules = stem_rules if stem_rules is not None else _DEFAULT_STEM_RULES

    if not label:
        return ""

    lowered = unicodedata.normalize("NFKD", str(label).lower())
    stripped = "".join(ch for ch in lowered if not unicodedata.combining(ch))
    stripped = re.sub(r"[^\w\s-]", " ", stripped)
    stripped = re.sub(r"[\s\-_]+", "_", stripped.strip())
    stripped = stripped.strip("_")

    if not stripped:
        return ""

    # Apply stem rules to each ``_``-separated token. Each rule key is
    # of the form ``_<suffix>`` so we test-match by prepending ``_`` to
    # the token; the longest rule wins per token (so
    # ``_independientes`` beats ``_independiente``). Token-wise instead
    # of whole-string-suffix-only because plurals appear both as full
    # words ("aportes parafiscales") and as trailing suffixes
    # ("presuncion_costos").
    rule_keys = sorted(rules.keys(), key=len, reverse=True)
    tokens = stripped.split("_")
    stemmed_tokens: list[str] = []
    for token in tokens:
        if not token:
            continue
        anchored = "_" + token
        replaced_token = token
        for suffix in rule_keys:
            if anchored.endswith(suffix):
                # Replacement keeps the leading "_" prefix form, so drop
                # the first char to recover the bare-token form.
                replacement = rules[suffix]
                replaced_token = (
                    anchored[: -len(suffix)] + replacement
                ).lstrip("_")
                break
        stemmed_tokens.append(replaced_token)

    return "_".join(stemmed_tokens)


# ---------------------------------------------------------------------------
# Similarity helpers
# ---------------------------------------------------------------------------


def _cosine(a: list[float] | None, b: list[float] | None) -> float:
    """Cosine similarity for two equal-length vectors; 0.0 on missing data."""

    if not a or not b:
        return 0.0
    if len(a) != len(b):
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na <= 0.0 or nb <= 0.0:
        return 0.0
    return dot / math.sqrt(na * nb)


def _agglomerative_single_linkage(
    vectors: list[list[float] | None],
    *,
    threshold: float,
) -> list[list[int]]:
    """Single-linkage agglomerative clustering over cosine similarity.

    Returns a list of index-lists — each sublist is one cluster. Items
    with no embedding (None) become their own singleton clusters so
    they do not pull anything else in.
    """

    n = len(vectors)
    if n == 0:
        return []

    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i: int, j: int) -> None:
        ri, rj = find(i), find(j)
        if ri == rj:
            return
        # Keep the lower index as root for deterministic cluster order.
        if ri < rj:
            parent[rj] = ri
        else:
            parent[ri] = rj

    for i in range(n):
        for j in range(i + 1, n):
            sim = _cosine(vectors[i], vectors[j])
            if sim >= threshold:
                union(i, j)

    clusters_by_root: dict[int, list[int]] = defaultdict(list)
    for idx in range(n):
        clusters_by_root[find(idx)].append(idx)

    # Deterministic ordering by smallest member index.
    return [clusters_by_root[root] for root in sorted(clusters_by_root.keys())]


# ---------------------------------------------------------------------------
# Clustering entry point
# ---------------------------------------------------------------------------


def _pick_default_embed_fn() -> Callable[[list[str]], list[list[float] | None]]:
    # Lazy import so tests that inject ``embed_fn`` never touch the net.
    from lia_graph.embeddings import compute_embeddings_batch

    return compute_embeddings_batch


def cluster_labels_by_parent_topic(
    rows: list[dict],
    *,
    cluster_threshold: float = 0.78,
    min_cluster_size: int = 3,
    embed_fn: Callable[[list[str]], list[list[float] | None]] | None = None,
    stem_rules: dict[str, str] | None = None,
) -> dict:
    """Cluster candidate labels per ``parent_topic``.

    Pipeline:
      1. Drop rows missing ``autogenerar_label`` or ``parent_topic``.
      2. Per parent: bucket rows by normalized slug (lexical merge).
      3. Embed each UNIQUE normalized slug once (semantic signal).
      4. Run agglomerative single-linkage clustering at
         ``cluster_threshold``.
      5. Proposals with ``>= min_cluster_size`` members land in
         ``proposals``; the rest land in ``singletons``.

    Returns a dict with two keys: ``"proposals"`` (dict[parent, list])
    and ``"singletons"`` (dict[parent, list]). Proposals carry the full
    JSON shape; singletons carry ``{label, doc_id, corpus_relative_path}``
    so the curator can inspect them in Phase 4.
    """

    embed = embed_fn if embed_fn is not None else _pick_default_embed_fn()

    # Bucket rows by parent_topic. Rows without a parent_topic or label
    # are dropped silently — the collection script is expected to filter
    # these before calling, but we guard anyway.
    by_parent: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        parent = row.get("parent_topic")
        label = row.get("autogenerar_label")
        if not parent or not label:
            continue
        by_parent[parent].append(row)

    proposals_by_parent: dict[str, list[dict]] = {}
    singletons_by_parent: dict[str, list[dict]] = {}

    for parent in sorted(by_parent.keys()):
        parent_rows = by_parent[parent]

        # Step 1 — lexical merge: group rows by normalized slug.
        slug_to_rows: dict[str, list[dict]] = defaultdict(list)
        slug_original_labels: dict[str, list[str]] = defaultdict(list)
        for row in parent_rows:
            slug = normalize_label(row["autogenerar_label"], stem_rules=stem_rules)
            if not slug:
                continue
            slug_to_rows[slug].append(row)
            slug_original_labels[slug].append(str(row["autogenerar_label"]))

        if not slug_to_rows:
            continue

        # Step 2 — embed unique slugs. Stable order for reproducibility.
        unique_slugs = sorted(slug_to_rows.keys())
        vectors = embed(unique_slugs) if unique_slugs else []
        if len(vectors) != len(unique_slugs):
            # Defensive: pad to expected length so index math stays sane.
            vectors = list(vectors) + [None] * (len(unique_slugs) - len(vectors))

        # Step 3 — agglomerative clustering over slug-level vectors.
        clusters = _agglomerative_single_linkage(
            vectors, threshold=cluster_threshold
        )

        # Step 4 — materialize proposals vs. singletons.
        parent_proposals: list[dict] = []
        parent_singletons: list[dict] = []
        proposal_index = 0

        for cluster in clusters:
            member_slugs = [unique_slugs[i] for i in cluster]
            member_rows: list[dict] = []
            for slug in member_slugs:
                member_rows.extend(slug_to_rows[slug])

            # Evidence count is rows, not unique slugs.
            evidence_count = len(member_rows)

            if evidence_count < min_cluster_size:
                for row in member_rows:
                    parent_singletons.append(
                        {
                            "label": row.get("autogenerar_label"),
                            "doc_id": row.get("doc_id"),
                            "corpus_relative_path": row.get(
                                "corpus_relative_path"
                            ),
                        }
                    )
                continue

            # Pick most-frequent slug as ``proposed_key``; ties break by
            # slug-ascending for determinism. Then pick the most-common
            # original human-readable label for that slug as
            # ``proposed_label``.
            slug_counter: Counter[str] = Counter()
            for row in member_rows:
                slug = normalize_label(
                    row["autogenerar_label"], stem_rules=stem_rules
                )
                slug_counter[slug] += 1

            dominant_slug = sorted(
                slug_counter.items(), key=lambda kv: (-kv[1], kv[0])
            )[0][0]

            label_counter: Counter[str] = Counter(
                slug_original_labels[dominant_slug]
            )
            dominant_label = sorted(
                label_counter.items(), key=lambda kv: (-kv[1], kv[0])
            )[0][0]

            # Intra-cluster similarity bounds — pairwise over vectors.
            member_indices = cluster
            if len(member_indices) == 1:
                sim_min = 1.0
                sim_max = 1.0
            else:
                sims: list[float] = []
                for i_idx, gi in enumerate(member_indices):
                    for gj in member_indices[i_idx + 1 :]:
                        sims.append(_cosine(vectors[gi], vectors[gj]))
                if sims:
                    sim_min = min(sims)
                    sim_max = max(sims)
                else:
                    sim_min = 1.0
                    sim_max = 1.0

            proposal_index += 1
            proposal_id = f"{parent}::{proposal_index:03d}"

            parent_proposals.append(
                {
                    "proposal_id": proposal_id,
                    "proposed_key": dominant_slug,
                    "proposed_label": dominant_label,
                    "candidate_labels": sorted(member_slugs),
                    "evidence_doc_ids": sorted(
                        {
                            str(r.get("doc_id"))
                            for r in member_rows
                            if r.get("doc_id")
                        }
                    ),
                    "evidence_count": evidence_count,
                    "intra_similarity_min": round(float(sim_min), 6),
                    "intra_similarity_max": round(float(sim_max), 6),
                }
            )

        if parent_proposals:
            proposals_by_parent[parent] = parent_proposals
        if parent_singletons:
            singletons_by_parent[parent] = parent_singletons

    return {
        "proposals": proposals_by_parent,
        "singletons": singletons_by_parent,
    }


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------


def rank_proposals(clusters_by_parent: dict) -> dict:
    """Sort proposals within each parent by evidence_count desc, key asc.

    Returns a NEW dict with proposals re-indexed so ``proposal_id``
    reflects the final sort order (contract requires stable
    ``<parent>::<zero-padded index>``).
    """

    proposals_map = dict(clusters_by_parent.get("proposals", {}))
    singletons_map = dict(clusters_by_parent.get("singletons", {}))

    reindexed: dict[str, list[dict]] = {}
    for parent in sorted(proposals_map.keys()):
        items = list(proposals_map[parent])
        items.sort(
            key=lambda p: (-int(p.get("evidence_count", 0)), str(p.get("proposed_key", "")))
        )
        out: list[dict] = []
        for idx, item in enumerate(items, start=1):
            new_item = dict(item)
            new_item["proposal_id"] = f"{parent}::{idx:03d}"
            out.append(new_item)
        reindexed[parent] = out

    return {"proposals": reindexed, "singletons": singletons_map}


# ---------------------------------------------------------------------------
# Top-level orchestration
# ---------------------------------------------------------------------------


def build_proposal_json(
    collection_rows: list[dict],
    *,
    cluster_threshold: float,
    min_cluster_size: int,
    source_paths: list[str],
    embed_fn: Callable[[list[str]], list[list[float] | None]] | None = None,
    stem_rules: dict[str, str] | None = None,
    version: str = "2026-04-21-v1",
    now_fn: Callable[[], datetime] | None = None,
) -> dict:
    """Build the full proposal JSON payload described in the contract.

    Does NOT write anything to disk. The caller is responsible for
    emitting trace events and persisting the return value.
    """

    clustered = cluster_labels_by_parent_topic(
        collection_rows,
        cluster_threshold=cluster_threshold,
        min_cluster_size=min_cluster_size,
        embed_fn=embed_fn,
        stem_rules=stem_rules,
    )
    ranked = rank_proposals(clustered)

    proposals = ranked["proposals"]
    singletons = ranked["singletons"]

    total_proposals = sum(len(v) for v in proposals.values())
    total_singletons = sum(len(v) for v in singletons.values())

    now = (now_fn or (lambda: datetime.now(timezone.utc)))()
    # Stable timestamp serialization (no microseconds).
    generated_at = now.replace(microsecond=0).isoformat().replace("+00:00", "Z")

    return {
        "version": version,
        "generated_at": generated_at,
        "source_collection_paths": list(source_paths),
        "cluster_threshold": float(cluster_threshold),
        "min_cluster_size": int(min_cluster_size),
        "proposals": proposals,
        "singletons": singletons,
        "summary": {
            "total_proposals": total_proposals,
            "total_singletons": total_singletons,
            "parent_topics_with_proposals": len(proposals),
        },
    }


__all__ = [
    "normalize_label",
    "cluster_labels_by_parent_topic",
    "rank_proposals",
    "build_proposal_json",
]
