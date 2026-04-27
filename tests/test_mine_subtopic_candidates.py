"""Tests for ``scripts/ingestion/mine_subtopic_candidates.py`` + ``subtopic_miner``.

Phase 3 of ``docs/done/next/subtopic_generationv1.md``. All tests inject a
deterministic ``embed_fn`` so clustering is reproducible without any
network call.

Coverage map (vs. plan §5 Phase 3):
  (a) normalize_label — accent strip + suffix stem.
  (b) normalize_label — plural-only fallback behavior.
  (c) clustering groups near-identical slugs into one proposal.
  (d) clustering never merges across parent_topics.
  (e) higher threshold produces >= as many clusters.
  (f) min_cluster_size=5 drops smaller clusters into singletons.
  (g) output JSON shape conforms to the contract.
  (h) proposals sorted by evidence_count desc within each parent.
  (i) singletons bucket keyed by parent with per-row metadata.
  (j) reproducibility — two runs yield identical output modulo ts.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Callable

import pytest

from lia_graph.subtopic_miner import (
    build_proposal_json,
    cluster_labels_by_parent_topic,
    normalize_label,
    rank_proposals,
)


_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPT_PATH = _REPO_ROOT / "scripts" / "mine_subtopic_candidates.py"


# ---------------------------------------------------------------------------
# Module loader for the CLI script
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def miner_cli_module():
    spec = importlib.util.spec_from_file_location(
        "mine_subtopic_candidates_under_test", _SCRIPT_PATH
    )
    assert spec and spec.loader, "could not load mine_subtopic_candidates.py"
    module = importlib.util.module_from_spec(spec)
    sys.modules["mine_subtopic_candidates_under_test"] = module
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Embed-fn factories
# ---------------------------------------------------------------------------


def _make_cluster_embed_fn(
    *,
    groups: list[list[str]],
    base_jitter: float = 0.0,
) -> Callable[[list[str]], list[list[float] | None]]:
    """Build an embed_fn where each ``groups`` entry maps to a shared basis
    direction, so within-group cosine similarity ~= 1.0 and cross-group
    is ~= 0.0. Any slug not in ``groups`` gets its own orthogonal axis.
    """

    dim = len(groups) + 200  # extra headroom for unknown slugs

    def embed(texts: list[str]) -> list[list[float] | None]:
        vectors: list[list[float] | None] = []
        unknown_axis = len(groups)
        for text in texts:
            vec = [0.0] * dim
            assigned_axis: int | None = None
            for group_idx, group in enumerate(groups):
                if text in group:
                    assigned_axis = group_idx
                    break
            if assigned_axis is None:
                vec[unknown_axis] = 1.0
                unknown_axis += 1
            else:
                vec[assigned_axis] = 1.0 + base_jitter * (
                    hash(text) % 3  # tiny deterministic variation
                ) * 1e-9
            vectors.append(vec)
        return vectors

    return embed


def _orthogonal_embed_fn(
    texts: list[str],
) -> list[list[float] | None]:
    """Every slug gets its own orthogonal axis — no cross-slug merging."""

    n = len(texts)
    out: list[list[float] | None] = []
    for idx in range(n):
        vec = [0.0] * n
        vec[idx] = 1.0
        out.append(vec)
    return out


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _row(
    *,
    parent: str,
    label: str,
    doc_id: str,
    path: str | None = None,
) -> dict:
    return {
        "parent_topic": parent,
        "autogenerar_label": label,
        "doc_id": doc_id,
        "corpus_relative_path": path or f"{parent}/{doc_id}.md",
        "error": None,
    }


# ---------------------------------------------------------------------------
# (a) normalize_label — accent strip + suffix stem
# ---------------------------------------------------------------------------


def test_normalize_label_strips_accents_and_stems_costos() -> None:
    # "Presunción-Costos " → presuncion_costos → presuncion_costo (stem).
    assert normalize_label("Presunción-Costos ") == "presuncion_costo"


# ---------------------------------------------------------------------------
# (b) normalize_label — "_parafiscales" is not a default stem rule
# ---------------------------------------------------------------------------


def test_normalize_label_plural_outside_stem_rules_preserved() -> None:
    # Decision: built-in stem rules cover costos, aportes, empleadores,
    # trabajadores, independientes. "_parafiscales" is intentionally not
    # in the default rules, so the trailing 's' is preserved.
    # "Aportes Parafiscales" → aportes_parafiscales → aporte_parafiscales
    # (only _aportes matches; it's applied once — first-matching wins).
    assert (
        normalize_label("Aportes Parafiscales") == "aporte_parafiscales"
    )


# ---------------------------------------------------------------------------
# (c) clustering groups near-identical slugs into one proposal
# ---------------------------------------------------------------------------


def test_clustering_groups_near_identical_slugs() -> None:
    rows = [
        _row(parent="laboral", label="presuncion costos indep A", doc_id="d1"),
        _row(parent="laboral", label="presuncion costos indep B", doc_id="d2"),
        _row(parent="laboral", label="presuncion costos indep C", doc_id="d3"),
    ]

    # Groups match the stemmed slug (costos → costo).
    embed_fn = _make_cluster_embed_fn(
        groups=[
            [
                "presuncion_costo_indep_a",
                "presuncion_costo_indep_b",
                "presuncion_costo_indep_c",
            ]
        ]
    )

    result = cluster_labels_by_parent_topic(
        rows,
        cluster_threshold=0.78,
        min_cluster_size=3,
        embed_fn=embed_fn,
    )

    proposals = result["proposals"].get("laboral", [])
    assert len(proposals) == 1, "expected a single clustered proposal"
    assert proposals[0]["evidence_count"] == 3
    assert set(proposals[0]["evidence_doc_ids"]) == {"d1", "d2", "d3"}


# ---------------------------------------------------------------------------
# (d) clustering never merges across parent_topics
# ---------------------------------------------------------------------------


def test_clustering_never_merges_across_parents() -> None:
    rows = [
        _row(parent="iva", label="regimen comun A", doc_id="d1"),
        _row(parent="iva", label="regimen comun B", doc_id="d2"),
        _row(parent="iva", label="regimen comun C", doc_id="d3"),
        _row(parent="laboral", label="regimen comun A", doc_id="d4"),
        _row(parent="laboral", label="regimen comun B", doc_id="d5"),
        _row(parent="laboral", label="regimen comun C", doc_id="d6"),
    ]

    # All six rows share a single semantic cluster — but parent_topic
    # walls must prevent any cross-parent merge.
    embed_fn = _make_cluster_embed_fn(
        groups=[
            [
                "regimen_comun_a",
                "regimen_comun_b",
                "regimen_comun_c",
            ]
        ]
    )

    result = cluster_labels_by_parent_topic(
        rows,
        cluster_threshold=0.78,
        min_cluster_size=3,
        embed_fn=embed_fn,
    )

    assert set(result["proposals"].keys()) == {"iva", "laboral"}
    for parent in ("iva", "laboral"):
        proposals = result["proposals"][parent]
        assert len(proposals) == 1
        # Every evidence doc_id in the iva proposal is from iva rows.
        doc_ids = set(proposals[0]["evidence_doc_ids"])
        if parent == "iva":
            assert doc_ids == {"d1", "d2", "d3"}
        else:
            assert doc_ids == {"d4", "d5", "d6"}


# ---------------------------------------------------------------------------
# (e) higher threshold produces >= as many clusters on the same fixture
# ---------------------------------------------------------------------------


def test_higher_threshold_produces_at_least_as_many_clusters() -> None:
    # Two semantic "neighborhoods" — within-group cosine ~0.80,
    # between-group cosine ~0.0. At threshold 0.78 the two groups stay
    # separate (2 clusters). At 0.95 they also stay separate — so this
    # test checks the monotonic property "higher threshold never
    # produces fewer clusters."
    rows = [
        _row(parent="laboral", label="alpha one", doc_id="d1"),
        _row(parent="laboral", label="alpha two", doc_id="d2"),
        _row(parent="laboral", label="alpha three", doc_id="d3"),
        _row(parent="laboral", label="beta one", doc_id="d4"),
        _row(parent="laboral", label="beta two", doc_id="d5"),
        _row(parent="laboral", label="beta three", doc_id="d6"),
    ]

    # Each slug gets a unique axis plus a shared group axis. Magnitudes
    # chosen so intra-group cosine ≈ 0.85 — clusters at threshold 0.78
    # but shatters at 0.95.  cos = s^2 / (s^2 + u^2) with s=1, u=0.42
    # → 1/(1+0.1764) ≈ 0.85.
    def custom_embed(texts: list[str]) -> list[list[float] | None]:
        vectors: list[list[float] | None] = []
        seen: dict[str, int] = {}
        for text in texts:
            if text not in seen:
                seen[text] = len(seen)
        dim = 2 + len(seen)  # axis 0 = alpha, axis 1 = beta, 2+ = per-slug
        shared = 1.0
        unique = 0.42
        for text in texts:
            vec = [0.0] * dim
            if text.startswith("alpha_"):
                vec[0] = shared
            elif text.startswith("beta_"):
                vec[1] = shared
            vec[2 + seen[text]] = unique
            vectors.append(vec)
        return vectors

    low = cluster_labels_by_parent_topic(
        rows,
        cluster_threshold=0.78,
        min_cluster_size=1,
        embed_fn=custom_embed,
    )
    high = cluster_labels_by_parent_topic(
        rows,
        cluster_threshold=0.95,
        min_cluster_size=1,
        embed_fn=custom_embed,
    )

    low_n = len(low["proposals"].get("laboral", []))
    high_n = len(high["proposals"].get("laboral", []))
    assert high_n >= low_n, (
        "higher cluster threshold must not produce fewer clusters "
        f"(low={low_n}, high={high_n})"
    )
    # And on this fixture specifically: low threshold merges each group
    # into one cluster; high threshold shatters them into singletons.
    assert low_n == 2
    assert high_n > low_n


# ---------------------------------------------------------------------------
# (f) min_cluster_size drops small clusters into singletons
# ---------------------------------------------------------------------------


def test_min_cluster_size_drops_small_clusters_to_singletons() -> None:
    rows = [
        _row(parent="laboral", label=f"presuncion costos indep {i}", doc_id=f"d{i}")
        for i in range(3)
    ]

    embed_fn = _make_cluster_embed_fn(
        groups=[
            [
                "presuncion_costo_indep_0",
                "presuncion_costo_indep_1",
                "presuncion_costo_indep_2",
            ]
        ]
    )

    # With min_cluster_size=5 and only 3 rows, nothing should clear the
    # bar — everything lands in singletons.
    result = cluster_labels_by_parent_topic(
        rows,
        cluster_threshold=0.78,
        min_cluster_size=5,
        embed_fn=embed_fn,
    )

    assert result["proposals"] == {}
    singletons = result["singletons"].get("laboral", [])
    assert len(singletons) == 3
    for row_meta in singletons:
        assert set(row_meta.keys()) >= {"label", "doc_id", "corpus_relative_path"}


# ---------------------------------------------------------------------------
# (g) output JSON shape conforms to the contract
# ---------------------------------------------------------------------------


def test_build_proposal_json_shape_matches_contract() -> None:
    rows = [
        _row(parent="laboral", label="presuncion costos indep A", doc_id="d1"),
        _row(parent="laboral", label="presuncion costos indep B", doc_id="d2"),
        _row(parent="laboral", label="presuncion costos indep C", doc_id="d3"),
        _row(parent="iva", label="unique label", doc_id="d9"),
    ]

    # Groups match the stemmed slug (costos → costo).
    embed_fn = _make_cluster_embed_fn(
        groups=[
            [
                "presuncion_costo_indep_a",
                "presuncion_costo_indep_b",
                "presuncion_costo_indep_c",
            ]
        ]
    )

    payload = build_proposal_json(
        rows,
        cluster_threshold=0.78,
        min_cluster_size=3,
        source_paths=["artifacts/subtopic_candidates/fixture.jsonl"],
        embed_fn=embed_fn,
    )

    # Top-level keys per contract.
    for key in (
        "version",
        "generated_at",
        "source_collection_paths",
        "cluster_threshold",
        "min_cluster_size",
        "proposals",
        "singletons",
        "summary",
    ):
        assert key in payload, f"missing top-level key: {key}"

    # Per-proposal shape.
    laboral_proposals = payload["proposals"]["laboral"]
    assert len(laboral_proposals) == 1
    prop = laboral_proposals[0]
    for key in (
        "proposal_id",
        "proposed_key",
        "proposed_label",
        "candidate_labels",
        "evidence_doc_ids",
        "evidence_count",
        "intra_similarity_min",
        "intra_similarity_max",
    ):
        assert key in prop, f"proposal missing field: {key}"

    # proposal_id matches <parent>::<zero-padded index>.
    assert prop["proposal_id"] == "laboral::001"

    # Summary counters match.
    assert payload["summary"]["total_proposals"] == 1
    assert payload["summary"]["parent_topics_with_proposals"] == 1
    # The single iva row is a singleton (< min_cluster_size=3).
    assert payload["summary"]["total_singletons"] >= 1


# ---------------------------------------------------------------------------
# (h) proposals sorted by evidence_count desc within each parent
# ---------------------------------------------------------------------------


def test_proposals_sorted_by_evidence_count_desc() -> None:
    # Two clusters in laboral: one with 5 members (big), one with 3.
    big_labels = [f"alpha seed {i}" for i in range(5)]
    small_labels = [f"beta seed {i}" for i in range(3)]

    rows: list[dict] = []
    for i, label in enumerate(big_labels):
        rows.append(_row(parent="laboral", label=label, doc_id=f"big{i}"))
    for i, label in enumerate(small_labels):
        rows.append(_row(parent="laboral", label=label, doc_id=f"small{i}"))

    embed_fn = _make_cluster_embed_fn(
        groups=[
            [normalize_label(l) for l in big_labels],
            [normalize_label(l) for l in small_labels],
        ]
    )

    payload = build_proposal_json(
        rows,
        cluster_threshold=0.78,
        min_cluster_size=3,
        source_paths=[],
        embed_fn=embed_fn,
    )

    proposals = payload["proposals"]["laboral"]
    assert len(proposals) == 2
    # First proposal must be the big one.
    assert proposals[0]["evidence_count"] == 5
    assert proposals[1]["evidence_count"] == 3
    # proposal_id indices are re-numbered to reflect rank.
    assert proposals[0]["proposal_id"] == "laboral::001"
    assert proposals[1]["proposal_id"] == "laboral::002"


# ---------------------------------------------------------------------------
# (i) singletons bucket keyed by parent_topic with expected row shape
# ---------------------------------------------------------------------------


def test_singletons_bucket_shape_and_keying() -> None:
    rows = [
        _row(parent="iva", label="unique alpha", doc_id="a1"),
        _row(parent="laboral", label="unique beta", doc_id="b1"),
    ]

    payload = build_proposal_json(
        rows,
        cluster_threshold=0.78,
        min_cluster_size=3,
        source_paths=[],
        embed_fn=_orthogonal_embed_fn,
    )

    singletons = payload["singletons"]
    assert set(singletons.keys()) == {"iva", "laboral"}
    for parent, entries in singletons.items():
        for entry in entries:
            assert set(entry.keys()) >= {
                "label",
                "doc_id",
                "corpus_relative_path",
            }
            # The row's corpus_relative_path convention stays intact.
            assert entry["corpus_relative_path"].startswith(f"{parent}/")


# ---------------------------------------------------------------------------
# (j) reproducibility — running twice yields identical output modulo ts
# ---------------------------------------------------------------------------


def test_build_proposal_json_is_reproducible() -> None:
    rows = [
        _row(parent="laboral", label="presuncion costos indep A", doc_id="d1"),
        _row(parent="laboral", label="presuncion costos indep B", doc_id="d2"),
        _row(parent="laboral", label="presuncion costos indep C", doc_id="d3"),
        _row(parent="iva", label="regimen comun A", doc_id="d4"),
        _row(parent="iva", label="regimen comun B", doc_id="d5"),
        _row(parent="iva", label="regimen comun C", doc_id="d6"),
    ]

    embed_fn = _make_cluster_embed_fn(
        groups=[
            [
                "presuncion_costo_indep_a",
                "presuncion_costo_indep_b",
                "presuncion_costo_indep_c",
            ],
            [
                "regimen_comun_a",
                "regimen_comun_b",
                "regimen_comun_c",
            ],
        ]
    )

    run_one = build_proposal_json(
        rows,
        cluster_threshold=0.78,
        min_cluster_size=3,
        source_paths=["collection.jsonl"],
        embed_fn=embed_fn,
    )
    run_two = build_proposal_json(
        rows,
        cluster_threshold=0.78,
        min_cluster_size=3,
        source_paths=["collection.jsonl"],
        embed_fn=embed_fn,
    )

    # Strip the only field that's allowed to drift between runs.
    run_one.pop("generated_at")
    run_two.pop("generated_at")

    assert json.dumps(run_one, sort_keys=True, ensure_ascii=False) == json.dumps(
        run_two, sort_keys=True, ensure_ascii=False
    )


# ---------------------------------------------------------------------------
# CLI smoke — covers main() end-to-end including file IO + trace events.
# This is bonus verification; plan's 10 tests are (a)-(j) above.
# ---------------------------------------------------------------------------


def test_cli_writes_expected_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, miner_cli_module
) -> None:
    # Build a small collection fixture on disk.
    collection_path = tmp_path / "collection_fixture.jsonl"
    rows = [
        _row(parent="laboral", label="presuncion costos indep A", doc_id="d1"),
        _row(parent="laboral", label="presuncion costos indep B", doc_id="d2"),
        _row(parent="laboral", label="presuncion costos indep C", doc_id="d3"),
    ]
    with collection_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    output_path = tmp_path / "out.json"

    # Redirect the instrumentation event log into tmp so we don't
    # pollute the real logs/events.jsonl file.
    log_path = tmp_path / "events.jsonl"
    import lia_graph.instrumentation as _instr

    monkeypatch.setattr(_instr, "DEFAULT_LOG_PATH", log_path, raising=False)

    rc = miner_cli_module.main(
        [
            "--input",
            str(collection_path),
            "--output",
            str(output_path),
            "--cluster-threshold",
            "0.78",
            "--min-cluster-size",
            "3",
            "--skip-embed",
        ]
    )

    assert rc == 0
    assert output_path.exists()
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    # With --skip-embed each unique slug is its own cluster; three
    # rows that normalize to three distinct slugs go to singletons.
    # That still gives us a valid contract-shaped payload.
    assert "proposals" in payload
    assert "singletons" in payload
