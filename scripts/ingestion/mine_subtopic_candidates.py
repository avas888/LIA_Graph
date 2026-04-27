#!/usr/bin/env python
"""Phase 3 — subtopic candidate mining CLI.

Reads one or more collection JSONL files (produced by Phase 2's
``scripts/ingestion/collect_subtopic_candidates.py``), clusters the
``autogenerar_label`` values per ``parent_topic``, and writes the
proposal JSON consumed by Phase 4's curation UI.

Usage::

    python scripts/ingestion/mine_subtopic_candidates.py \\
        --input 'artifacts/subtopic_candidates/collection_*.jsonl'

    python scripts/ingestion/mine_subtopic_candidates.py \\
        --input artifacts/subtopic_candidates/collection_20260421T142200Z.jsonl \\
        --output artifacts/subtopic_proposals_manual.json \\
        --cluster-threshold 0.85 --min-cluster-size 5

Exit codes:
    0   — success.
    1   — argparse error (handled by argparse itself).
    2   — no input rows resolved (empty glob or all-filtered).

Trace events (``subtopic.mine.*`` namespace):
    subtopic.mine.start
    subtopic.mine.cluster.formed   (per emitted cluster)
    subtopic.mine.done
"""

from __future__ import annotations

import argparse
import glob as _glob
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, Sequence

# Keep the script runnable both as ``python scripts/ingestion/mine_subtopic_candidates.py``
# and as ``PYTHONPATH=src:. python scripts/ingestion/mine_subtopic_candidates.py``.
_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC_DIR = _REPO_ROOT / "src"
for candidate in (_SRC_DIR, _REPO_ROOT):
    candidate_str = str(candidate)
    if candidate.is_dir() and candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from lia_graph.instrumentation import emit_event  # noqa: E402
from lia_graph.subtopic_miner import build_proposal_json  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utc_stamp(now: datetime | None = None) -> str:
    """UTC timestamp in the ``YYYYMMDDTHHMMSSZ`` convention used by Phase 2."""

    moment = (now or datetime.now(timezone.utc)).replace(microsecond=0)
    return moment.strftime("%Y%m%dT%H%M%SZ")


def _resolve_input_paths(pattern: str) -> list[str]:
    """Resolve a single path OR a shell glob into a sorted path list.

    Matches the file verbatim if it exists; otherwise expands as a glob.
    Output is deterministically sorted so the JSON's
    ``source_collection_paths`` is stable across runs.
    """

    if not pattern:
        return []
    direct = Path(pattern)
    if direct.exists() and direct.is_file():
        return [str(direct)]
    return sorted(_glob.glob(pattern))


def _load_jsonl_rows(paths: Sequence[str]) -> list[dict]:
    """Concatenate rows from all input JSONL files in the given order."""

    rows: list[dict] = []
    for path in paths:
        file_path = Path(path)
        if not file_path.exists():
            continue
        with file_path.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    parsed = json.loads(line)
                except json.JSONDecodeError:
                    # Skip malformed rows silently — the collection
                    # script guarantees one-object-per-line shape.
                    continue
                if isinstance(parsed, dict):
                    rows.append(parsed)
    return rows


def _filter_rows(
    rows: list[dict],
    *,
    only_topic: str | None,
) -> list[dict]:
    """Drop rows that lack a usable label or that ran into a per-doc error.

    - ``autogenerar_label`` must be non-empty.
    - ``error`` (collection-side) must be absent / None.
    - If ``only_topic`` is set, keep only rows whose ``parent_topic``
      matches.
    """

    out: list[dict] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row.get("autogenerar_label") in (None, ""):
            continue
        if row.get("error") not in (None, ""):
            continue
        if only_topic and row.get("parent_topic") != only_topic:
            continue
        out.append(row)
    return out


def _load_stem_rules(path_str: str | None) -> dict[str, str] | None:
    """Load a JSON file of ``{suffix: replacement}`` overrides, or None."""

    if not path_str:
        return None
    file_path = Path(path_str)
    if not file_path.exists():
        raise SystemExit(
            f"--slug-stem-rules path does not exist: {path_str}"
        )
    try:
        raw = json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(
            f"--slug-stem-rules must be JSON-parseable: {exc}"
        ) from exc
    if not isinstance(raw, dict):
        raise SystemExit(
            "--slug-stem-rules JSON must be an object of {suffix: replacement}"
        )
    return {str(k): str(v) for k, v in raw.items()}


def _identity_embed_fn(
    texts: list[str],
) -> list[list[float] | None]:
    """One-hot-per-unique-text embed for ``--skip-embed`` mode.

    Every distinct normalized slug gets its own orthogonal basis vector,
    which means the cosine similarity between any two DIFFERENT slugs
    is exactly 0.0 — no clustering across slug boundaries. Identical
    slugs collapse in the upstream lexical merge before embedding, so
    this is equivalent to "treat every unique slug as its own cluster."
    """

    if not texts:
        return []
    n = len(texts)
    vectors: list[list[float] | None] = []
    for idx in range(n):
        vec = [0.0] * n
        vec[idx] = 1.0
        vectors.append(vec)
    return vectors


# ---------------------------------------------------------------------------
# Argparse
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mine_subtopic_candidates",
        description=(
            "Cluster autogenerar_label values per parent_topic and emit "
            "the proposal JSON consumed by the Phase 4 curation UI."
        ),
    )
    parser.add_argument(
        "--input",
        required=True,
        help=(
            "Path to a collection JSONL file, or a shell glob (e.g. "
            "artifacts/subtopic_candidates/collection_*.jsonl)."
        ),
    )
    parser.add_argument(
        "--output",
        default=None,
        help=(
            "Path to the proposal JSON to write. Defaults to "
            "artifacts/subtopic_proposals_<UTC>.json."
        ),
    )
    parser.add_argument(
        "--cluster-threshold",
        type=float,
        default=0.78,
        help="Cosine similarity threshold for agglomerative clustering.",
    )
    parser.add_argument(
        "--min-cluster-size",
        type=int,
        default=3,
        help="Clusters below this size land in the singletons bucket.",
    )
    parser.add_argument(
        "--only-topic",
        default=None,
        help="Restrict mining to a single parent_topic (e.g. 'laboral').",
    )
    parser.add_argument(
        "--slug-stem-rules",
        default=None,
        help=(
            "Path to a JSON file with {suffix: replacement} overrides "
            "for Spanish suffix stemming. If omitted, built-in defaults apply."
        ),
    )
    parser.add_argument(
        "--skip-embed",
        action="store_true",
        help=(
            "Skip embedding calls and treat every unique normalized "
            "slug as its own cluster. Intended for tests / CI."
        ),
    )
    parser.add_argument(
        "--artifacts-dir",
        default="artifacts",
        help="Directory the default --output path is resolved against.",
    )
    return parser


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the Phase 3 mining CLI. Returns a process exit code."""

    parser = _build_parser()
    args = parser.parse_args(argv)

    input_paths = _resolve_input_paths(args.input)

    default_output = (
        Path(args.artifacts_dir)
        / f"subtopic_proposals_{_utc_stamp()}.json"
    )
    output_path = Path(args.output) if args.output else default_output

    emit_event(
        "subtopic.mine.start",
        {
            "input_paths": list(input_paths),
            "output_path": str(output_path),
            "cluster_threshold": float(args.cluster_threshold),
            "min_cluster_size": int(args.min_cluster_size),
            "only_topic": args.only_topic,
            "skip_embed": bool(args.skip_embed),
        },
    )

    if not input_paths:
        emit_event(
            "subtopic.mine.done",
            {
                "total_proposals": 0,
                "singletons": 0,
                "output_path": str(output_path),
                "reason": "no_input_paths",
            },
        )
        sys.stderr.write(
            f"mine_subtopic_candidates: no inputs matched '{args.input}'\n"
        )
        return 2

    raw_rows = _load_jsonl_rows(input_paths)
    rows = _filter_rows(raw_rows, only_topic=args.only_topic)

    stem_rules = _load_stem_rules(args.slug_stem_rules)

    embed_fn: Callable[[list[str]], list[list[float] | None]] | None
    if args.skip_embed:
        embed_fn = _identity_embed_fn
    else:
        embed_fn = None  # miner will resolve the default Gemini batch fn

    payload = build_proposal_json(
        rows,
        cluster_threshold=float(args.cluster_threshold),
        min_cluster_size=int(args.min_cluster_size),
        source_paths=input_paths,
        embed_fn=embed_fn,
        stem_rules=stem_rules,
    )

    # Emit per-cluster trace before writing — so a crash during write
    # still leaves an auditable trail of what was discovered.
    for parent, proposals in payload.get("proposals", {}).items():
        for proposal in proposals:
            emit_event(
                "subtopic.mine.cluster.formed",
                {
                    "parent_topic": parent,
                    "proposal_id": proposal.get("proposal_id"),
                    "evidence_count": int(proposal.get("evidence_count", 0)),
                    "intra_sim_min": float(
                        proposal.get("intra_similarity_min", 0.0)
                    ),
                    "intra_sim_max": float(
                        proposal.get("intra_similarity_max", 0.0)
                    ),
                },
            )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    total_singletons = int(
        payload.get("summary", {}).get("total_singletons", 0)
    )
    total_proposals = int(
        payload.get("summary", {}).get("total_proposals", 0)
    )

    emit_event(
        "subtopic.mine.done",
        {
            "total_proposals": total_proposals,
            "singletons": total_singletons,
            "output_path": str(output_path),
        },
    )

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
