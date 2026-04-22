"""Tests for ``scripts/promote_subtopic_decisions.py`` (Phase 6).

Covers the full contract from ``docs/next/subtopic_generationv1-contracts.md``:

- (a) 5 accepted proposals across 2 parents → correct grouping / ordering.
- (b) merge chain A→B→C → single entry at C with aggregated aliases + counts.
- (c) rename decision: label reflects ``final_label``; key is ``final_key``.
- (d) rejected proposals do NOT appear in the output.
- (e) idempotency: running twice produces identical dicts (modulo ``generated_at``).
- (f) ``--dry-run`` prints diff and does NOT write the output file.
- (g) last-write-wins: two accept rows for same ``proposal_id`` → last wins.
- (h) split action: 2 aliases → 2 entries in the final taxonomy.

The CLI is imported via ``importlib`` because the script lives under
``scripts/`` rather than an installed package.
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPT_PATH = _REPO_ROOT / "scripts" / "promote_subtopic_decisions.py"


# ---------------------------------------------------------------------------
# Module loader + builder import helpers
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def promote_module():
    spec = importlib.util.spec_from_file_location(
        "promote_subtopic_decisions_under_test", _SCRIPT_PATH
    )
    assert spec and spec.loader, "could not load promote_subtopic_decisions.py"
    module = importlib.util.module_from_spec(spec)
    sys.modules["promote_subtopic_decisions_under_test"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def builder():
    from lia_graph import subtopic_taxonomy_builder

    return subtopic_taxonomy_builder


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _write_decisions(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False))
            fh.write("\n")


def _accept(
    proposal_id: str,
    parent_topic: str,
    final_key: str,
    final_label: str,
    evidence_count: int,
    *,
    aliases: list[str] | None = None,
    ts: str = "2026-04-21T14:50:00Z",
    curator: str = "admin@lia.dev",
) -> dict:
    return {
        "ts": ts,
        "curator": curator,
        "parent_topic": parent_topic,
        "proposal_id": proposal_id,
        "action": "accept",
        "final_key": final_key,
        "final_label": final_label,
        "aliases": aliases or [],
        "merged_into": None,
        "reason": None,
        "evidence_count": evidence_count,
    }


# ---------------------------------------------------------------------------
# (a) five accepts, two parents — grouping + ordering
# ---------------------------------------------------------------------------


def test_a_five_accepts_across_two_parents(builder):
    decisions = [
        _accept("laboral::001", "laboral", "presuncion_costos", "Presunción de costos", 23),
        _accept("laboral::002", "laboral", "aportes_pila", "Aportes PILA", 40),
        _accept("laboral::003", "laboral", "vacaciones", "Vacaciones", 15),
        _accept("iva::001", "iva", "declaracion_iva", "Declaración de IVA", 50),
        _accept("iva::002", "iva", "retefuente_iva", "ReteFuente IVA", 50),
    ]

    taxonomy = builder.build_taxonomy(decisions, version="2026-04-21-v1")

    subtopics = taxonomy["subtopics"]
    # Parents sorted alphabetically: iva, laboral.
    assert list(subtopics.keys()) == ["iva", "laboral"]

    # Within laboral: evidence_count desc, then key asc.
    laboral_keys = [e["key"] for e in subtopics["laboral"]]
    assert laboral_keys == ["aportes_pila", "presuncion_costos", "vacaciones"]

    # Within iva: tie on evidence_count → key asc.
    iva_keys = [e["key"] for e in subtopics["iva"]]
    assert iva_keys == ["declaracion_iva", "retefuente_iva"]

    # Total entries = 5.
    total = sum(len(v) for v in subtopics.values())
    assert total == 5

    # Label + evidence propagate.
    aportes_entry = subtopics["laboral"][0]
    assert aportes_entry["label"] == "Aportes PILA"
    assert aportes_entry["evidence_count"] == 40
    assert aportes_entry["curator"] == "admin@lia.dev"


# ---------------------------------------------------------------------------
# (b) merge chain A→B→C — aggregation
# ---------------------------------------------------------------------------


def test_b_merge_chain_collapses_and_aggregates(builder):
    decisions = [
        {
            "ts": "2026-04-21T14:50:00Z",
            "curator": "admin@lia.dev",
            "parent_topic": "laboral",
            "proposal_id": "laboral::001",
            "action": "merge",
            "final_key": "costos_presuntos_indep",
            "final_label": None,
            "aliases": ["alias_from_A"],
            "merged_into": "laboral::002",
            "reason": None,
            "evidence_count": 5,
        },
        {
            "ts": "2026-04-21T14:51:00Z",
            "curator": "admin@lia.dev",
            "parent_topic": "laboral",
            "proposal_id": "laboral::002",
            "action": "merge",
            "final_key": "presuncion_costos_ugpp",
            "final_label": None,
            "aliases": ["alias_from_B"],
            "merged_into": "laboral::003",
            "reason": None,
            "evidence_count": 8,
        },
        _accept(
            "laboral::003",
            "laboral",
            "presuncion_costos_independientes",
            "Presunción de costos para independientes",
            10,
            aliases=["existing_alias_C"],
        ),
    ]

    taxonomy = builder.build_taxonomy(decisions, version="v1")

    laboral = taxonomy["subtopics"]["laboral"]
    assert len(laboral) == 1, "merge chain should collapse to a single entry"

    entry = laboral[0]
    assert entry["key"] == "presuncion_costos_independientes"
    assert entry["label"] == "Presunción de costos para independientes"
    # Evidence counts sum: A(5) + B(8) + C(10) = 23.
    assert entry["evidence_count"] == 23

    # Aliases include both source final_keys AND their own aliases, plus C's.
    aliases = set(entry["aliases"])
    assert "costos_presuntos_indep" in aliases  # A's final_key
    assert "presuncion_costos_ugpp" in aliases  # B's final_key
    assert "alias_from_A" in aliases
    assert "alias_from_B" in aliases
    assert "existing_alias_C" in aliases


# ---------------------------------------------------------------------------
# (c) rename — label reflects final_label, key stays final_key
# ---------------------------------------------------------------------------


def test_c_rename_applies_to_label_and_key(builder):
    decisions = [
        {
            "ts": "2026-04-21T14:50:00Z",
            "curator": "admin@lia.dev",
            "parent_topic": "iva",
            "proposal_id": "iva::001",
            "action": "rename",
            "final_key": "retencion_iva_servicios",
            "final_label": "Retención de IVA — servicios",
            "aliases": [],
            "merged_into": None,
            "reason": None,
            "evidence_count": 12,
        },
    ]

    taxonomy = builder.build_taxonomy(decisions, version="v1")
    entry = taxonomy["subtopics"]["iva"][0]

    assert entry["key"] == "retencion_iva_servicios"
    assert entry["label"] == "Retención de IVA — servicios"
    assert entry["evidence_count"] == 12


# ---------------------------------------------------------------------------
# (d) rejected proposals excluded
# ---------------------------------------------------------------------------


def test_d_rejected_proposals_excluded(builder):
    decisions = [
        _accept("laboral::001", "laboral", "aportes_pila", "Aportes PILA", 40),
        {
            "ts": "2026-04-21T14:50:00Z",
            "curator": "admin@lia.dev",
            "parent_topic": "laboral",
            "proposal_id": "laboral::002",
            "action": "reject",
            "final_key": None,
            "final_label": None,
            "aliases": [],
            "merged_into": None,
            "reason": "out-of-scope",
            "evidence_count": 4,
        },
    ]

    taxonomy = builder.build_taxonomy(decisions, version="v1")
    keys = [e["key"] for e in taxonomy["subtopics"]["laboral"]]
    assert keys == ["aportes_pila"]


# ---------------------------------------------------------------------------
# (e) idempotency — two builds produce identical dicts (modulo generated_at)
# ---------------------------------------------------------------------------


def test_e_idempotent_modulo_generated_at(builder):
    decisions = [
        _accept("laboral::001", "laboral", "aportes_pila", "Aportes PILA", 40),
        _accept("iva::001", "iva", "declaracion_iva", "Declaración de IVA", 50),
    ]

    first = builder.build_taxonomy(decisions, version="v1")
    second = builder.build_taxonomy(decisions, version="v1")

    first_copy = dict(first)
    second_copy = dict(second)
    first_copy.pop("generated_at", None)
    second_copy.pop("generated_at", None)

    assert first_copy == second_copy


# ---------------------------------------------------------------------------
# (f) --dry-run writes nothing and prints a diff
# ---------------------------------------------------------------------------


def test_f_dry_run_prints_diff_and_does_not_write(promote_module, tmp_path):
    decisions_path = tmp_path / "artifacts" / "subtopic_decisions.jsonl"
    output_path = tmp_path / "config" / "subtopic_taxonomy.json"

    _write_decisions(
        decisions_path,
        [
            _accept("laboral::001", "laboral", "aportes_pila", "Aportes PILA", 40),
            _accept("iva::001", "iva", "declaracion_iva", "Declaración de IVA", 50),
        ],
    )

    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = promote_module.main(
            [
                "--decisions",
                str(decisions_path),
                "--output",
                str(output_path),
                "--dry-run",
                "--version",
                "2026-04-21-v1",
                # Synthetic decisions cover only 2 parents; bypass the
                # zero-subtopic-per-parent invariant that consults the real
                # topic_taxonomy.json (39 parents).
                "--allow-empty-parents",
            ]
        )

    assert rc == 0
    assert not output_path.exists(), "dry-run must not write the output file"

    out = buf.getvalue()
    assert "existing config/subtopic_taxonomy.json" in out
    assert "proposed config/subtopic_taxonomy.json" in out
    assert "+ aportes_pila" in out
    assert "+ declaracion_iva" in out


# ---------------------------------------------------------------------------
# (g) last-write-wins — two accept rows for the same proposal_id
# ---------------------------------------------------------------------------


def test_g_last_write_wins(promote_module, builder, tmp_path):
    decisions_path = tmp_path / "artifacts" / "subtopic_decisions.jsonl"
    _write_decisions(
        decisions_path,
        [
            _accept(
                "laboral::001",
                "laboral",
                "aportes_pila_v1",
                "Aportes PILA (v1)",
                40,
                ts="2026-04-21T14:00:00Z",
            ),
            _accept(
                "laboral::001",
                "laboral",
                "aportes_pila_final",
                "Aportes PILA — final",
                55,
                aliases=["aportes_pila_v1"],
                ts="2026-04-21T15:00:00Z",
            ),
        ],
    )

    loaded = builder.load_decisions(decisions_path)
    assert len(loaded) == 1, "last-write-wins must collapse duplicate proposal_id"
    assert loaded[0]["final_key"] == "aportes_pila_final"

    taxonomy = builder.build_taxonomy(loaded, version="v1")
    entries = taxonomy["subtopics"]["laboral"]
    assert len(entries) == 1
    assert entries[0]["key"] == "aportes_pila_final"
    assert entries[0]["label"] == "Aportes PILA — final"
    assert entries[0]["evidence_count"] == 55


# ---------------------------------------------------------------------------
# (h) split action — two aliases → two entries
# ---------------------------------------------------------------------------


def test_h_split_expands_to_multiple_entries(builder):
    decisions = [
        {
            "ts": "2026-04-21T14:50:00Z",
            "curator": "admin@lia.dev",
            "parent_topic": "laboral",
            "proposal_id": "laboral::001",
            "action": "split",
            "final_key": None,
            "final_label": None,
            "aliases": ["aportes_salud", "aportes_pension"],
            "merged_into": None,
            "reason": None,
            "evidence_count": 20,
        },
    ]

    taxonomy = builder.build_taxonomy(decisions, version="v1")
    laboral = taxonomy["subtopics"]["laboral"]

    assert len(laboral) == 2
    keys = {entry["key"] for entry in laboral}
    assert keys == {"aportes_salud", "aportes_pension"}

    # Evidence split 20 // 2 = 10 each.
    for entry in laboral:
        assert entry["evidence_count"] == 10
