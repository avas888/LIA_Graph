"""Graph proximity signal for rerank.

Topology of `ArticleNode -[*]- ArticleNode` is identical between the artifact
graph (typed_edges.jsonl) and the live FalkorDB instance — both are seeded
from the same edge file. So for proximity scoring we always read the artifact
file. No `LIA_GRAPH_MODE` branching needed; mode only matters when reading
*live* node properties, which proximity does not need.

Public API: `score_candidates(query_refs, candidate_refs_by_doc)` returns
`{doc_id: 0..1 proximity}` where 1.0 means a query article ref is itself in
the candidate's refs.
"""

from __future__ import annotations

import json
from collections import defaultdict, deque
from functools import lru_cache
from pathlib import Path
from typing import Mapping

# Match the artifacts directory the rest of pipeline_d uses by default. Keeping
# this aligned with `pipeline_d/retriever.py` means we don't have to thread
# `artifacts_dir` through the rerank surface.
_DEFAULT_ARTIFACTS_DIR = Path(__file__).resolve().parents[4] / "artifacts"
_TYPED_EDGES_FILENAME = "typed_edges.jsonl"

# Capping BFS hops keeps the proximity score from being dominated by very
# distant nodes that happen to be reachable through generic edges. 4 hops
# matches the planner's upper traversal budget.
_MAX_HOPS = 4


def score_candidates(
    *,
    query_refs: tuple[str, ...],
    candidate_refs_by_doc: Mapping[str, tuple[str, ...]],
) -> dict[str, float]:
    """Multi-source BFS from query refs; per-candidate score = `1/(1+hops)`.

    `query_refs` and per-candidate refs are normalized article identifiers
    (e.g. `et_art_147`). Returns 0.0 for candidates with no refs or no path
    within `_MAX_HOPS`.
    """
    query_keys = tuple(_to_article_key(ref) for ref in query_refs if ref)
    query_keys = tuple(key for key in query_keys if key)
    if not query_keys or not candidate_refs_by_doc:
        return {doc_id: 0.0 for doc_id in candidate_refs_by_doc}

    distances = _bfs_distances(query_keys)
    scores: dict[str, float] = {}
    for doc_id, refs in candidate_refs_by_doc.items():
        candidate_keys = tuple(_to_article_key(ref) for ref in refs if ref)
        candidate_keys = tuple(key for key in candidate_keys if key)
        if not candidate_keys:
            scores[doc_id] = 0.0
            continue
        best_distance: int | None = None
        for key in candidate_keys:
            d = distances.get(key)
            if d is None:
                continue
            if best_distance is None or d < best_distance:
                best_distance = d
        scores[doc_id] = 1.0 / (1.0 + float(best_distance)) if best_distance is not None else 0.0
    return scores


# --- BFS helpers ------------------------------------------------------------


def _bfs_distances(seeds: tuple[str, ...]) -> dict[str, int]:
    """Breadth-first distance from any seed to every reachable article key."""
    adjacency = _load_adjacency(str(_DEFAULT_ARTIFACTS_DIR))
    distances: dict[str, int] = {seed: 0 for seed in seeds if seed in adjacency or seed}
    queue: deque[str] = deque(distances.keys())
    while queue:
        node = queue.popleft()
        depth = distances[node]
        if depth >= _MAX_HOPS:
            continue
        for neighbor in adjacency.get(node, ()):
            if neighbor in distances:
                continue
            distances[neighbor] = depth + 1
            queue.append(neighbor)
    return distances


@lru_cache(maxsize=2)
def _load_adjacency(artifacts_dir: str) -> dict[str, frozenset[str]]:
    """Parse typed_edges.jsonl once, return symmetric ArticleNode adjacency.

    Cached because the file is ~25k rows; rebuilding per request is wasteful
    and the file only changes between full ingestion runs.
    """
    path = Path(artifacts_dir) / _TYPED_EDGES_FILENAME
    if not path.is_file():
        return {}
    raw_adjacency: dict[str, set[str]] = defaultdict(set)
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("source_kind") != "ArticleNode" or row.get("target_kind") != "ArticleNode":
                continue
            source = str(row.get("source_key") or "").strip()
            target = str(row.get("target_key") or "").strip()
            if not source or not target or source == target:
                continue
            raw_adjacency[source].add(target)
            raw_adjacency[target].add(source)
    return {key: frozenset(neighbors) for key, neighbors in raw_adjacency.items()}


def _to_article_key(ref: str) -> str:
    """Strip the `et_art_` prefix used by `extract_article_refs` to get the
    bare article number that typed_edges.jsonl uses as `source_key`."""
    clean = str(ref or "").strip().lower()
    if not clean:
        return ""
    if clean.startswith("et_art_"):
        return clean[len("et_art_") :].replace("_", "-")
    if clean.startswith("art_"):
        return clean[len("art_") :].replace("_", "-")
    return clean.replace("_", "-")
