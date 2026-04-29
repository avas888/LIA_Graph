#!/usr/bin/env python
"""Embedding backfill CLI wrapper over `lia_graph.embedding_ops`.

Contract (from docs/next/suin_harvestv1.md Phase 0 / Phase 6):

    --target {wip,production} --generation <id> [--batch-size N] [--json]

Semantics:
    * Runs the in-process embedding job runner (not the detached subprocess
      path used by the GUI) so that this CLI exits only when the backfill
      completes and the process return code reflects success/failure.
    * `--generation` is accepted for plan-alignment: today the embedding
      runner already backfills *every* row in the target with a NULL
      embedding, which is a superset of "fill rows for this generation".
      The argument is surfaced in the manifest for audit.
    * On completion writes `artifacts/suin/_embedding_<target>_<ts>.json`
      with the job payload.

Exit codes:
    0 — NULL embedding count for the target reached 0
    1 — job completed but NULL embeddings remain (backfill incomplete)
    2 — job failed or script error
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC_DIR = _REPO_ROOT / "src"
for _candidate in (_SRC_DIR, _REPO_ROOT):
    _candidate_str = str(_candidate)
    if _candidate.is_dir() and _candidate_str not in sys.path:
        sys.path.insert(0, _candidate_str)

from lia_graph.env_loader import load_dotenv_if_present  # noqa: E402


_ARTIFACTS_DIR = Path("artifacts/suin")


def _ts() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _run(
    target: str,
    batch_size: int,
    force: bool,
    *,
    shard_x: int | None = None,
    shard_n: int | None = None,
) -> dict[str, Any]:
    """Drive the runner in-process (synchronous, not threaded).

    Uses `_EmbeddingJobRunner._run_embedding` directly so the CLI exits
    only when backfill completes and its return code reflects success.

    When ``shard_x`` / ``shard_n`` are set, the runner processes only the
    rows whose ``chunk_id`` hashes into shard X (next_v7 P4). Run 4
    concurrent processes with shards 0/4..3/4 for ~4x throughput.
    """
    from lia_graph.embedding_ops import (
        _EmbeddingJobCtx,
        _EmbeddingJobRunner,
        EMBEDDING_JOBS_DIR,
        _utc_now_iso,
        build_embedding_status,
    )
    from lia_graph.jobs_store import create_job

    os.environ.setdefault("LIA_EMBEDDING_BATCH_SIZE", str(int(batch_size)))

    request_payload: dict[str, Any] = {"target": target, "force": bool(force)}
    if shard_n is not None:
        request_payload["shard_x"] = int(shard_x)
        request_payload["shard_n"] = int(shard_n)

    record = create_job(
        job_type="embedding_backfill",
        request_payload=request_payload,
    )
    runner = _EmbeddingJobRunner(
        record.job_id, target=target, force=force,
        shard_x=shard_x, shard_n=shard_n,
    )
    ctx = _EmbeddingJobCtx(
        job_id=record.job_id,
        base_dir=EMBEDDING_JOBS_DIR,
        payload={
            "target": target,
            "force": bool(force),
            "started_at": _utc_now_iso(),
            "stage": "embedding",
            "stage_status": "running",
            "log_tail": "",
            "checks": [],
            "progress": {},
            "quality_report": None,
        },
    )
    ctx.start()
    try:
        runner._run_embedding(ctx)
        ctx.finish(ok=True, status="completed")
    except Exception as exc:
        ctx.finish(ok=False, status="failed", error=str(exc))
        raise
    finally:
        ctx.stop()

    status = build_embedding_status(target=target)
    return {
        "job_id": record.job_id,
        "status": status,
        "finished_at": _ts(),
    }


def main(argv: list[str] | None = None) -> int:
    load_dotenv_if_present()
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--target", required=True, choices=["wip", "production"])
    cli.add_argument(
        "--generation",
        required=True,
        help=(
            "Generation_id being embedded (informational; the runner fills "
            "every NULL-embedding row in the target, a superset)."
        ),
    )
    cli.add_argument("--batch-size", type=int, default=100)
    cli.add_argument(
        "--force",
        action="store_true",
        help="Re-embed even rows that already have an embedding.",
    )
    cli.add_argument(
        "--shard",
        default=None,
        metavar="X/N",
        help=(
            "Process only one of N disjoint shards (X in [0, N)). Stable "
            "MD5(chunk_id) mod N partition. Run 4 concurrent processes with "
            "--shard 0/4 .. --shard 3/4 for ~4x throughput. Each shard "
            "over-fetches by N to keep batch_size effective rows after "
            "client-side filter."
        ),
    )
    cli.add_argument("--json", action="store_true")
    args = cli.parse_args(argv)

    _ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    shard_x: int | None = None
    shard_n: int | None = None
    if args.shard:
        try:
            shard_x_str, shard_n_str = args.shard.split("/", 1)
            shard_x = int(shard_x_str)
            shard_n = int(shard_n_str)
            if shard_n < 1 or not (0 <= shard_x < shard_n):
                raise ValueError(f"--shard X/N requires 0 <= X < N >= 1, got {args.shard}")
        except ValueError as exc:
            print(json.dumps({"ok": False, "error": "BadShard", "message": str(exc)}, indent=2))
            return 2

    try:
        payload = _run(
            target=args.target,
            batch_size=max(1, args.batch_size),
            force=bool(args.force),
            shard_x=shard_x,
            shard_n=shard_n,
        )
    except Exception as exc:
        out = {"ok": False, "error": type(exc).__name__, "message": str(exc)}
        print(json.dumps(out, indent=2))
        return 2

    null_count = int(payload["status"].get("null_embedding_chunks") or 0)
    total = int(payload["status"].get("total_chunks") or 0)
    # Sharded runs cannot drive null_count to 0 on their own — only the
    # union of all shards can. Treat shard exit as ok when its OWN slice
    # is processed (the runner's loop terminated cleanly because no rows
    # in this shard's window remained).
    if shard_n is not None:
        ok = True
    else:
        ok = null_count == 0

    shard_tag = f"_shard{shard_x}of{shard_n}" if shard_n is not None else ""
    manifest_path = _ARTIFACTS_DIR / f"_embedding_{args.target}{shard_tag}_{_ts()}.json"
    manifest_path.write_text(
        json.dumps(
            {
                "ok": ok,
                "target": args.target,
                "generation": args.generation,
                "shard": (f"{shard_x}/{shard_n}" if shard_n is not None else None),
                "total_chunks": total,
                "null_embedding_chunks": null_count,
                "coverage_pct": payload["status"].get("coverage_pct"),
                **payload,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    if args.json:
        print(
            json.dumps(
                {
                    "ok": ok,
                    "target": args.target,
                    "generation": args.generation,
                    "null_embedding_chunks": null_count,
                    "total_chunks": total,
                    "manifest_path": str(manifest_path),
                },
                indent=2,
            )
        )
    else:
        flag = "OK" if ok else "INCOMPLETE"
        print(
            f"embedding_backfill: {flag} target={args.target} "
            f"null={null_count}/{total} manifest={manifest_path}"
        )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
