"""Deterministic builder for ``config/subtopic_taxonomy.json`` (Phase 6).

Pure module consumed by ``scripts/promote_subtopic_decisions.py``. No I/O
beyond the single ``load_decisions`` helper that reads the append-only
``artifacts/subtopic_decisions.jsonl`` file.

Public API:

- ``load_decisions(path)`` — read JSONL; later rows override earlier ones by
  ``proposal_id`` (last-write-wins) for idempotency when the curator changes
  their mind.
- ``resolve_merge_chains(decisions)`` — collapse transitive
  ``A merged_into B → B merged_into C → C accept`` chains into a single
  effective record anchored on the final target. Aliases cascade, evidence
  counts sum.
- ``build_taxonomy(decisions, *, version)`` — produce the taxonomy dict
  matching ``docs/done/next/subtopic_generationv1-contracts.md``.

Emits ``subtopic.promote.merge_resolved`` per resolved chain via
``lia_graph.instrumentation.emit_event``.

Determinism: ``build_taxonomy`` is byte-identical for identical input +
version (the ``generated_at`` timestamp is the only non-deterministic
field — callers snapshot it once and pass it in implicitly through the
dict ordering this module imposes).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from lia_graph.instrumentation import emit_event

__all__ = [
    "EmptyParentTopicError",
    "load_decisions",
    "resolve_merge_chains",
    "build_taxonomy",
    "validate_no_empty_parents",
]


class EmptyParentTopicError(ValueError):
    """Raised when a taxonomy publication would leave a parent with zero subtopics.

    Silent empty parents are a known failure mode (curator strategy memo,
    2026-04-21): docs routed to such a parent in PASO 1 fall through PASO 4
    with no subtopic match candidates and end up flagged-for-review forever.
    The generator should refuse to publish and surface the offending parents.
    """


_VALID_ACTIONS = {"accept", "reject", "merge", "rename", "split"}


def _utc_now_iso() -> str:
    """Return an ISO-8601 UTC timestamp with second precision."""
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_decisions(path: Path) -> list[dict]:
    """Read ``artifacts/subtopic_decisions.jsonl`` with last-write-wins.

    The file is append-only per the contract, but the curator may record
    multiple decisions for the same ``proposal_id`` (e.g. changed mind).
    Later rows override earlier rows for the same ``proposal_id``; ordering
    is preserved by first-seen position.

    Returns a list of decision dicts in first-seen order with later values
    merged in.
    """
    path = Path(path)
    if not path.is_file():
        return []

    order: list[str] = []
    latest: dict[str, dict] = {}
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                # Skip malformed lines — decisions file is append-only and
                # should never contain garbage, but we don't want a stray
                # newline to brick the whole run.
                continue
            if not isinstance(row, dict):
                continue
            proposal_id = row.get("proposal_id")
            if not isinstance(proposal_id, str) or not proposal_id:
                continue
            if proposal_id not in latest:
                order.append(proposal_id)
            latest[proposal_id] = row

    return [latest[pid] for pid in order]


def _aliases_from(decision: dict) -> list[str]:
    aliases = decision.get("aliases") or []
    if not isinstance(aliases, list):
        return []
    return [str(a) for a in aliases if isinstance(a, (str, int))]


def _evidence_count(decision: dict) -> int:
    raw = decision.get("evidence_count", 0)
    try:
        return int(raw or 0)
    except (TypeError, ValueError):
        return 0


def resolve_merge_chains(decisions: list[dict]) -> list[dict]:
    """Collapse transitive merges; return effective accept/rename records.

    Rules:
      * ``reject`` and ``split`` rows are not merge targets; they're handled
        upstream by ``build_taxonomy``.
      * For ``merge`` rows, follow ``merged_into`` until we reach a non-merge
        decision (accept/rename) or a cycle/missing target.
      * Aliases cascade: A merged into B adds A's ``final_key`` plus A's
        existing aliases to the target's aliases.
      * Evidence counts sum through the chain.
      * If the terminal target is itself missing or not accept/rename, the
        chain is dropped (its evidence is lost — curator error).

    Emits ``subtopic.promote.merge_resolved`` once per collapsed chain with
    ``{source_proposal_ids, target_proposal_id, chain_length}``.

    Returns one record per surviving terminal proposal_id (accept/rename
    rows that absorbed zero-or-more merge sources). Order preserved by the
    terminal row's position in the input list.
    """
    by_id: dict[str, dict] = {d["proposal_id"]: d for d in decisions if d.get("proposal_id")}

    # Discover terminal (non-merge) accepted/renamed records first.
    terminals: list[dict] = []
    terminal_ids: set[str] = set()
    for decision in decisions:
        action = decision.get("action")
        if action in {"accept", "rename"}:
            pid = decision.get("proposal_id")
            if isinstance(pid, str) and pid not in terminal_ids:
                terminals.append(decision)
                terminal_ids.add(pid)

    # Build a working copy per terminal so we can mutate aliases / counts.
    effective: dict[str, dict] = {}
    sources_by_target: dict[str, list[str]] = {}
    for term in terminals:
        pid = term["proposal_id"]
        effective[pid] = {
            **term,
            "aliases": list(_aliases_from(term)),
            "evidence_count": _evidence_count(term),
        }
        sources_by_target[pid] = []

    # Resolve each merge row by walking merged_into until we land on a
    # terminal or give up (missing / cycle).
    for decision in decisions:
        if decision.get("action") != "merge":
            continue
        source_id = decision.get("proposal_id")
        if not isinstance(source_id, str):
            continue

        # Walk the chain.
        visited: list[str] = [source_id]
        cursor = decision
        chain_length = 0
        while True:
            target_id = cursor.get("merged_into")
            if not isinstance(target_id, str) or not target_id:
                cursor = None
                break
            chain_length += 1
            if target_id in visited:
                # Cycle — abandon chain.
                cursor = None
                break
            visited.append(target_id)
            nxt = by_id.get(target_id)
            if nxt is None:
                cursor = None
                break
            next_action = nxt.get("action")
            if next_action in {"accept", "rename"}:
                cursor = nxt
                break
            if next_action == "merge":
                cursor = nxt
                continue
            # reject/split as a merge target — chain dies.
            cursor = None
            break

        if cursor is None:
            # Chain didn't resolve to a terminal; skip.
            continue

        terminal_id = cursor["proposal_id"]
        if terminal_id not in effective:
            # Terminal exists in the map (guaranteed by construction above)
            # only if action in {accept, rename}. Defensive guard.
            continue

        # Cascade aliases and evidence count into the terminal.
        target_aliases = effective[terminal_id]["aliases"]
        source_decision = by_id.get(source_id, {})
        # Source's own final_key (if set) becomes an alias of the terminal.
        src_final_key = source_decision.get("final_key")
        if isinstance(src_final_key, str) and src_final_key:
            if src_final_key not in target_aliases:
                target_aliases.append(src_final_key)
        # Source's recorded aliases propagate too.
        for alias in _aliases_from(source_decision):
            if alias and alias not in target_aliases:
                target_aliases.append(alias)
        # Evidence counts sum.
        effective[terminal_id]["evidence_count"] += _evidence_count(source_decision)

        sources_by_target.setdefault(terminal_id, []).append(source_id)

        emit_event(
            "subtopic.promote.merge_resolved",
            {
                "source_proposal_ids": [source_id],
                "target_proposal_id": terminal_id,
                "chain_length": chain_length,
            },
        )

    # Preserve order of terminals as encountered in the input list.
    return [effective[term["proposal_id"]] for term in terminals]


def _entry_from_decision(decision: dict) -> dict:
    """Render a taxonomy entry dict from a resolved decision."""
    key = str(decision.get("final_key") or "").strip()
    label = str(decision.get("final_label") or "").strip()
    aliases = [a for a in _aliases_from(decision) if a and a != key]
    # Deduplicate aliases while preserving first-seen order.
    seen: set[str] = set()
    deduped: list[str] = []
    for alias in aliases:
        if alias in seen:
            continue
        seen.add(alias)
        deduped.append(alias)
    evidence = _evidence_count(decision)
    curated_at = decision.get("ts") or ""
    curator = decision.get("curator") or ""
    return {
        "key": key,
        "label": label,
        "aliases": deduped,
        "evidence_count": evidence,
        "curated_at": str(curated_at),
        "curator": str(curator),
    }


def _split_entries(decision: dict) -> list[dict]:
    """Each split alias becomes its own mini-entry.

    Per contracts, a split decision persists the intent — each alias in
    ``aliases`` is promoted as a separate subtopic. The original
    ``final_key``/``final_label`` is not used; evidence is divided evenly
    (integer division — remainder drops onto the first bucket).
    """
    aliases = [a for a in _aliases_from(decision) if a]
    if not aliases:
        return []
    total_evidence = _evidence_count(decision)
    per_entry, remainder = divmod(total_evidence, len(aliases)) if aliases else (0, 0)
    curated_at = decision.get("ts") or ""
    curator = decision.get("curator") or ""
    entries: list[dict] = []
    for idx, alias in enumerate(aliases):
        extra = 1 if idx < remainder else 0
        label = alias.replace("_", " ").strip().capitalize() or alias
        entries.append(
            {
                "key": alias,
                "label": label,
                "aliases": [],
                "evidence_count": per_entry + extra,
                "curated_at": str(curated_at),
                "curator": str(curator),
            }
        )
    return entries


def build_taxonomy(decisions: list[dict], *, version: str) -> dict:
    """Produce the full ``subtopic_taxonomy.json`` dict.

    Rules:
      * Only ``accept`` and ``rename`` actions (post-merge resolution)
        contribute entries. ``reject`` rows are excluded. ``split`` rows
        are preserved as-is — each alias becomes its own entry.
      * Ordering: parent_topic keys sorted alphabetically; entries within
        each parent sorted by ``evidence_count`` desc then ``key`` asc.
      * The ``generated_at`` timestamp is set to UTC-now; all other fields
        are deterministic for a given input + version.
    """
    # 1. Apply last-write-wins (caller may have done this already via
    #    load_decisions; re-applying is idempotent).
    ordered_ids: list[str] = []
    latest: dict[str, dict] = {}
    for row in decisions:
        pid = row.get("proposal_id")
        if not isinstance(pid, str) or not pid:
            continue
        if pid not in latest:
            ordered_ids.append(pid)
        latest[pid] = row
    collapsed = [latest[pid] for pid in ordered_ids]

    # 2. Resolve merges (side-effect: emits merge_resolved events).
    resolved = resolve_merge_chains(collapsed)

    # 3. Gather split rows separately (not touched by merge resolver).
    splits = [d for d in collapsed if d.get("action") == "split"]

    # 4. Bucket by parent_topic.
    buckets: dict[str, list[dict]] = {}
    for decision in resolved:
        parent = str(decision.get("parent_topic") or "").strip()
        if not parent:
            continue
        entry = _entry_from_decision(decision)
        if not entry["key"]:
            continue
        buckets.setdefault(parent, []).append(entry)

    for decision in splits:
        parent = str(decision.get("parent_topic") or "").strip()
        if not parent:
            continue
        for entry in _split_entries(decision):
            if not entry["key"]:
                continue
            buckets.setdefault(parent, []).append(entry)

    # 5. Deterministic ordering inside each bucket.
    for entries in buckets.values():
        entries.sort(key=lambda e: (-int(e.get("evidence_count") or 0), str(e.get("key") or "")))

    # 6. Assemble output with parent keys sorted alphabetically.
    ordered_buckets: dict[str, list[dict]] = {
        parent: buckets[parent] for parent in sorted(buckets.keys())
    }

    return {
        "version": str(version),
        "generated_from": "artifacts/subtopic_decisions.jsonl",
        "generated_at": _utc_now_iso(),
        "subtopics": ordered_buckets,
    }


def validate_no_empty_parents(taxonomy_output: dict) -> None:
    """Raise ``EmptyParentTopicError`` if any known parent has zero subtopics.

    Invariant: every top-level parent_topic key in the active topic taxonomy
    (``config/topic_taxonomy.json`` — entries with ``parent_key is None``)
    must have at least one subtopic in the generated output. An empty parent
    means every doc routed there in PASO 1 falls through PASO 4 with no
    subtopic match candidates and silently ends up flagged-for-review.

    The validator is intentionally strict: it lists every offender so the
    curator can seed entries (or remove the parent from the topic taxonomy)
    before republishing. It consults ``iter_ingestion_topic_entries`` from
    ``lia_graph.topic_taxonomy`` — the canonical source of truth for the
    active parent list.
    """
    from .topic_taxonomy import iter_ingestion_topic_entries

    known_parents = {
        entry.key
        for entry in iter_ingestion_topic_entries()
        if entry.parent_key is None
    }
    subtopics_map = taxonomy_output.get("subtopics")
    if not isinstance(subtopics_map, dict):
        subtopics_map = {}

    empty_parents = sorted(
        parent
        for parent in known_parents
        if not subtopics_map.get(parent)
    )
    if empty_parents:
        raise EmptyParentTopicError(
            f"Taxonomy generation rejected — {len(empty_parents)} parent_topic(s) "
            f"have zero subtopics: {empty_parents}. Seed at least one subtopic "
            f"per parent before publishing, or remove the parent from the "
            f"active topic taxonomy."
        )


def _ensure_valid_actions(decisions: Iterable[dict]) -> None:
    """Optional guard — raise on unknown actions. Not called by default
    to preserve forward compatibility if the contract grows new actions.
    """
    for decision in decisions:
        action = decision.get("action")
        if action not in _VALID_ACTIONS:
            raise ValueError(f"Unknown action in decision row: {action!r}")


def _coerce_any(value: Any) -> Any:  # pragma: no cover — defensive stub
    """Placeholder for possible future value normalization."""
    return value
