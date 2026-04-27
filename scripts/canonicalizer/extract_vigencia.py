"""Sub-fix 1B-β — batch driver for the skill-guided vigencia extractor.

Detached + heartbeat-friendly: launches read input set → invokes harness
per norm → writes per-norm JSON. Resumable via `--resume-from-checkpoint`.

Usage (per CLAUDE.md long-running-job convention):
  nohup PYTHONPATH=src:. uv run python scripts/canonicalizer/extract_vigencia.py \\
      --input-set evals/vigencia_extraction_v1/input_set.jsonl \\
      --output-dir evals/vigencia_extraction_v1 \\
      --run-id 1Bbeta-batch-2026-05-15 \\
      > logs/extract_vigencia.log 2>&1 &
  disown
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

LOGGER = logging.getLogger("extract_vigencia")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    # Either --input-set OR --batch-id is required.
    p.add_argument("--input-set", default=None,
                   help="Path to a JSONL with `norm_id` per line. Mutually exclusive with --batch-id.")
    p.add_argument("--batch-id", default=None,
                   help="Read norm slice from config/canonicalizer_run_v1/batches.yaml (resolves "
                        "norm_filter against the corpus's deduplicated input set). "
                        "Mutually exclusive with --input-set.")
    p.add_argument("--batches-config",
                   default="config/canonicalizer_run_v1/batches.yaml",
                   help="Path to the batches YAML (used with --batch-id).")
    p.add_argument("--corpus-input-set",
                   default="evals/vigencia_extraction_v1/input_set.jsonl",
                   help="The corpus-wide deduplicated norm_id set (built by "
                        "scripts/canonicalizer/build_extraction_input_set.py). Used as the source "
                        "from which --batch-id slices.")
    p.add_argument("--output-dir", default="evals/vigencia_extraction_v1")
    p.add_argument("--run-id", required=True)
    p.add_argument("--resume-from-checkpoint", action="store_true",
                   help="Skip norm_ids whose JSON already exists.")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--audit-log", default="evals/vigencia_extraction_v1/audit.jsonl")
    p.add_argument("--events-log", default="logs/events.jsonl",
                   help="Per-norm events for the heartbeat shape.")
    p.add_argument("--guard-against-rerun", action="store_true", default=True,
                   help="Refuse to launch if --output-dir already has JSON files (run-once invariant).")
    p.add_argument("--allow-rerun", dest="guard_against_rerun", action="store_false",
                   help="Bypass run-once guard. Operator-explicit only — see canonicalizer_runv1.md §9.5.")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)
    if not args.input_set and not args.batch_id:
        p.error("Either --input-set or --batch-id is required.")
    if args.input_set and args.batch_id:
        p.error("--input-set and --batch-id are mutually exclusive.")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    from lia_graph.vigencia_extractor import VigenciaSkillHarness

    # Per-batch path: scope the output dir to the batch.
    if args.batch_id:
        out_dir = Path(args.output_dir) / args.batch_id
    else:
        out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Run-once guard (per canonicalizer_runv1.md §9.3 & §9.5).
    if args.guard_against_rerun and any(out_dir.glob("*.json")):
        LOGGER.error(
            "REFUSING to launch — %s already has veredicto JSONs. "
            "The Gemini extraction is a ONE-TIME operation per the operator directive. "
            "Either: (a) you mean to RE-PLAY existing JSONs, in which case run "
            "scripts/canonicalizer/ingest_vigencia_veredictos.py --input-dir %s instead; "
            "or (b) you really need to re-extract, in which case pass --allow-rerun "
            "AND get explicit operator approval first.",
            out_dir,
            out_dir,
        )
        return 4

    audit_path = Path(args.audit_log)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    events_path = Path(args.events_log)
    events_path.parent.mkdir(parents=True, exist_ok=True)

    # Resolve the norm_id slice — either from a flat input set OR via batch config.
    if args.batch_id:
        norm_ids = _resolve_batch_input_set(
            batches_config=Path(args.batches_config),
            batch_id=args.batch_id,
            corpus_input_set=Path(args.corpus_input_set),
            limit=args.limit,
        )
        LOGGER.info("Batch %s: %d norm_ids selected", args.batch_id, len(norm_ids))
    else:
        norm_ids = list(_iter_input(Path(args.input_set), args.limit))
        LOGGER.info("Run %s: %d norm_ids in input set", args.run_id, len(norm_ids))

    harness = VigenciaSkillHarness.default()

    _emit_event(events_path, kind="run.started", run_id=args.run_id, norm_count=len(norm_ids))

    successes = refusals = errors = skipped = 0
    for norm_id in norm_ids:
        out_path = out_dir / f"{norm_id.replace('/', '_')}.json"
        if args.resume_from_checkpoint and out_path.exists():
            skipped += 1
            continue
        try:
            result = harness.verify_norm(norm_id=norm_id)
            harness.write_result(result, norm_id=norm_id, output_dir=out_dir)
            if result.veredicto is not None:
                successes += 1
                _emit_event(
                    events_path,
                    kind="norm.success",
                    run_id=args.run_id,
                    norm_id=norm_id,
                    state=result.veredicto.state.value,
                )
            else:
                refusals += 1
                _emit_event(
                    events_path,
                    kind="norm.refusal",
                    run_id=args.run_id,
                    norm_id=norm_id,
                    reason=result.refusal_reason,
                )
            _append_audit(audit_path, {
                "ts": _now(),
                "run_id": args.run_id,
                "norm_id": norm_id,
                "outcome": "veredicto" if result.veredicto else "refusal",
                "state": result.veredicto.state.value if result.veredicto else None,
                "reason": result.refusal_reason,
            })
        except Exception as err:
            errors += 1
            LOGGER.exception("Norm %s failed: %s", norm_id, err)
            _emit_event(
                events_path,
                kind="norm.error",
                run_id=args.run_id,
                norm_id=norm_id,
                error=str(err),
            )

    _emit_event(
        events_path,
        kind="cli.done",
        run_id=args.run_id,
        successes=successes,
        refusals=refusals,
        errors=errors,
        skipped=skipped,
    )
    LOGGER.info(
        "Run %s done: successes=%d refusals=%d errors=%d skipped=%d",
        args.run_id,
        successes,
        refusals,
        errors,
        skipped,
    )
    return 0 if errors == 0 else 1


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_batch_input_set(
    *,
    batches_config: Path,
    batch_id: str,
    corpus_input_set: Path,
    limit: int | None,
) -> list[str]:
    """Resolve a batch_id to its concrete list of norm_ids.

    Reads the batches YAML, finds the matching batch entry, applies its
    `norm_filter` against the corpus's deduplicated input set. Each
    `norm_filter` shape is supported per the YAML schema:
      - prefix          : norm_id starts with `prefix`
      - regex           : norm_id matches `pattern`
      - et_article_range: ET articles in [from, to] inclusive (handles "X-Y" forms)
      - explicit_list   : exact list
    """

    import re as _re
    try:
        import yaml  # type: ignore
    except ImportError:
        LOGGER.error("PyYAML is required for --batch-id; install with `uv pip install pyyaml`")
        return []

    if not batches_config.is_file():
        LOGGER.error("Batches config not found: %s", batches_config)
        return []
    with batches_config.open("r", encoding="utf-8") as fh:
        batches = yaml.safe_load(fh) or []
    entry = next((b for b in batches if b.get("batch_id") == batch_id), None)
    if entry is None:
        LOGGER.error("Batch id %r not found in %s", batch_id, batches_config)
        return []

    nf = entry.get("norm_filter") or {}
    kind = str(nf.get("type") or "").strip()

    # Materialize the corpus input set (lazy — only needed for non-explicit filters).
    def _corpus_norm_ids() -> list[str]:
        if not corpus_input_set.is_file():
            LOGGER.warning(
                "Corpus input set %s not found — falling back to filter-as-direct-list (won't work for prefix/regex). "
                "Run `scripts/canonicalizer/build_extraction_input_set.py` first.",
                corpus_input_set,
            )
            return []
        out: list[str] = []
        with corpus_input_set.open("r", encoding="utf-8") as fh:
            for raw in fh:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    blob = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                norm_id = str(blob.get("norm_id") or "").strip()
                if norm_id:
                    out.append(norm_id)
        return out

    selected: list[str] = []
    if kind == "prefix":
        prefix = str(nf.get("prefix") or "")
        selected = [n for n in _corpus_norm_ids() if n.startswith(prefix)]
    elif kind == "regex":
        pattern = _re.compile(str(nf.get("pattern") or ""))
        selected = [n for n in _corpus_norm_ids() if pattern.search(n)]
    elif kind == "et_article_range":
        lo_raw = nf.get("from")
        hi_raw = nf.get("to")
        # Both bounds may be ints or strings like "580-2".
        def _et_sort_key(norm_id: str) -> tuple[int, int]:
            # `et.art.689-3` → (689, 3); `et.art.580` → (580, 0).
            tail = norm_id[len("et.art."):] if norm_id.startswith("et.art.") else norm_id
            head, _, sub = tail.partition(".")  # drop sub-units
            major, _, minor = head.partition("-")
            try:
                return (int(major), int(minor or 0))
            except ValueError:
                return (-1, -1)
        lo_key = _et_sort_key(f"et.art.{lo_raw}")
        hi_key = _et_sort_key(f"et.art.{hi_raw}")
        for n in _corpus_norm_ids():
            if not n.startswith("et.art."):
                continue
            k = _et_sort_key(n)
            if k == (-1, -1):
                continue
            if lo_key <= k <= hi_key:
                selected.append(n)
    elif kind == "explicit_list":
        selected = list(nf.get("norm_ids") or [])
    else:
        LOGGER.error("Unknown norm_filter type %r in batch %s", kind, batch_id)
        return []

    # Dedup + sort for determinism.
    selected = sorted(set(selected))
    if limit is not None:
        selected = selected[:limit]
    return selected


def _iter_input(path: Path, limit: int | None) -> Iterable[str]:
    if not path.is_file():
        LOGGER.error("Input set not found: %s", path)
        return
    count = 0
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                blob = json.loads(line)
            except json.JSONDecodeError:
                continue
            norm_id = str(blob.get("norm_id") or "")
            if norm_id:
                yield norm_id
                count += 1
                if limit is not None and count >= limit:
                    return


def _append_audit(path: Path, blob: dict[str, Any]) -> None:
    line = json.dumps(blob, ensure_ascii=False, sort_keys=True) + "\n"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line)


def _emit_event(path: Path, **fields: Any) -> None:
    blob = {"ts": _now(), **fields}
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(blob, ensure_ascii=False) + "\n")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    sys.exit(main())
