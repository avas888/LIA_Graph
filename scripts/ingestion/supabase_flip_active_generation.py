#!/usr/bin/env python
"""Flip `is_active` on corpus_generations to a new generation.

Two-step deactivate-then-activate flow honoring
`idx_corpus_generations_single_active` (partial unique index allowing exactly
one row with `is_active=true`). Mirrors the activation path inside
`SupabaseCorpusSink.finalize(activate=True)` but runs standalone so the SUIN
production push (`scripts/ingestion/fire_suin_cloud.sh`) can flip an existing generation
without repeating the sink's ingest path.

Invocation:
    PYTHONPATH=src:. uv run python scripts/ingestion/supabase_flip_active_generation.py \
        --target production --generation gen_suin_prod_v1 --confirm

The `--confirm` flag is required. Without it the script prints the planned
flip and exits non-zero so a caller that forgot `--confirm` never mutates
cloud state by accident.

Exit codes:
    0 — flip completed (or --rollback completed)
    1 — refused to run without --confirm
    2 — script failure (credentials missing, target row missing, SQL error)
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _client(target: str):
    from lia_graph.supabase_client import create_supabase_client_for_target

    return create_supabase_client_for_target(target)


def flip_active_generation(
    *,
    target: str,
    generation: str,
    previous_generation: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Deactivate every active row then activate the target generation.

    Returns a dict describing the action. When `dry_run=True` no SQL mutates
    cloud state.
    """
    client = _client(target)

    target_row = client.table("corpus_generations").select(
        "generation_id, is_active"
    ).eq("generation_id", generation).limit(1).execute()
    if not target_row.data:
        raise RuntimeError(
            f"generation {generation!r} does not exist in corpus_generations on {target!r}"
        )

    already_active = bool(target_row.data[0].get("is_active"))

    active_rows = client.table("corpus_generations").select(
        "generation_id"
    ).eq("is_active", True).execute()
    active_ids = [row["generation_id"] for row in (active_rows.data or [])]

    plan = {
        "target": target,
        "generation": generation,
        "already_active": already_active,
        "would_deactivate": [gid for gid in active_ids if gid != generation],
        "dry_run": dry_run,
    }

    if dry_run:
        return plan | {"status": "dry_run"}

    now = _now()
    # Step 1: deactivate every other active row first — keeps the partial
    # unique index satisfied for the moment between the two statements.
    client.table("corpus_generations").update(
        {"is_active": False, "updated_at": now}
    ).neq("generation_id", generation).eq("is_active", True).execute()

    # Step 2: activate target.
    client.table("corpus_generations").update(
        {"is_active": True, "activated_at": now, "updated_at": now}
    ).eq("generation_id", generation).execute()

    return plan | {"status": "activated", "activated_at": now}


def main(argv: list[str] | None = None) -> int:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--target", required=True, choices=["wip", "production"])
    cli.add_argument("--generation", required=True)
    cli.add_argument(
        "--confirm",
        action="store_true",
        help="Required to actually flip. Without it the script shows the plan and exits 1.",
    )
    cli.add_argument(
        "--previous-generation",
        default=None,
        help="(Rollback only) The generation to reactivate instead of --generation.",
    )
    cli.add_argument(
        "--rollback",
        action="store_true",
        help="Reactivate --previous-generation (deactivating --generation).",
    )
    cli.add_argument("--json", action="store_true")
    args = cli.parse_args(argv)

    if args.rollback and not args.previous_generation:
        print("--rollback requires --previous-generation", file=sys.stderr)
        return 2

    if not args.confirm:
        try:
            plan = flip_active_generation(
                target=args.target,
                generation=args.previous_generation if args.rollback else args.generation,
                dry_run=True,
            )
        except Exception as exc:
            print(f"refusing to run (dry-run failed): {exc}", file=sys.stderr)
            return 2
        print(json.dumps({"refused": "missing --confirm", "plan": plan}, indent=2))
        return 1

    try:
        result = flip_active_generation(
            target=args.target,
            generation=args.previous_generation if args.rollback else args.generation,
        )
    except Exception as exc:
        payload = {"ok": False, "error": type(exc).__name__, "message": str(exc)}
        print(json.dumps(payload, indent=2))
        return 2

    if args.json:
        print(json.dumps({"ok": True, **result}, indent=2))
    else:
        print(
            f"activated generation={result['generation']} "
            f"target={result['target']} at={result.get('activated_at')}"
        )
        if result["would_deactivate"]:
            print(f"  deactivated: {result['would_deactivate']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
