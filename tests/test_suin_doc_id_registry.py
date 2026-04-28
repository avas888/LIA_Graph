"""Tests for the SUIN canonical→doc-id registry — fixplan_v6 §3 step 1.

Asserts the title-regex builder maps the spine SUIN documents to the
canonical norm_ids the vigencia harness will look up.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.canonicalizer.build_suin_doc_id_registry import (
    build_registry,
    canonical_from_title,
)


REGISTRY_PATH = Path("var/suin_doc_id_registry.json")


def _make_documents_dir(tmp_path: Path, scope: str, rows: list[dict]) -> Path:
    """Write a minimal `<root>/<scope>/documents.jsonl` and return root."""

    scope_dir = tmp_path / scope
    scope_dir.mkdir(parents=True)
    docs_path = scope_dir / "documents.jsonl"
    docs_path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )
    return tmp_path


def test_canonical_from_title_decreto():
    assert canonical_from_title(
        "DECRETO 624 DE 1989 - Colombia | SUIN Juriscol"
    ) == "decreto.624.1989"
    assert canonical_from_title(
        "DECRETO 1625 DE 2016 - Colombia | SUIN Juriscol"
    ) == "decreto.1625.2016"


def test_canonical_from_title_ley():
    assert canonical_from_title("LEY 100 DE 1993") == "ley.100.1993"
    assert canonical_from_title(
        "LEY 2277 DE 2022 - Colombia | SUIN Juriscol"
    ) == "ley.2277.2022"


def test_canonical_from_title_cst_special():
    assert canonical_from_title(
        "CODIGO SUSTANTIVO DEL TRABAJO - Colombia | SUIN Juriscol"
    ) == "cst"


def test_canonical_from_title_unmatched_jurisprudencia():
    # Sentencias / autos must not be mapped — those are CC/CE territory.
    assert canonical_from_title("AUTO 23795 de 2019") is None
    assert canonical_from_title(
        "SENTENCIA 11001032500020180011400 de 2023"
    ) is None


def test_build_registry_skips_smoke_by_default(tmp_path: Path):
    root = tmp_path
    _make_documents_dir(
        root,
        "real",
        [
            {
                "doc_id": "1132325",
                "ruta": "https://www.suin-juriscol.gov.co/viewDocument.asp?id=1132325",
                "title": "DECRETO 624 DE 1989 - Colombia | SUIN Juriscol",
            },
        ],
    )
    _make_documents_dir(
        root,
        "smoke",
        [
            {
                "doc_id": "SUIN_ET_624_1989",
                "ruta": "Decretos/624_1989",  # bogus path, must not win
                "title": "Estatuto Tributario (fixture)",
            },
        ],
    )
    registry, stats, _unmatched = build_registry(root)
    assert "decreto.624.1989" in registry
    assert registry["decreto.624.1989"]["suin_doc_id"] == "1132325"
    # `et` should be present as an alias of decreto.624.1989, NOT as the
    # smoke fixture (which would have ruta='Decretos/624_1989').
    assert registry["et"]["suin_doc_id"] == "1132325"
    assert registry["et"]["alias_of"] == "decreto.624.1989"
    assert stats.matched == 1


def test_build_registry_includes_smoke_when_asked(tmp_path: Path):
    root = tmp_path
    _make_documents_dir(
        root,
        "smoke",
        [
            {
                "doc_id": "SUIN_LEY_1607_2012",
                "ruta": "Leyes/Ley1607_2012",
                "title": "Ley 1607 de 2012 (fixture)",
            },
        ],
    )
    registry, _stats, _unmatched = build_registry(root, include_smoke=True)
    assert "ley.1607.2012" in registry


@pytest.mark.skipif(
    not REGISTRY_PATH.is_file(),
    reason="Registry not built yet — run `uv run python scripts/canonicalizer/build_suin_doc_id_registry.py`.",
)
def test_real_registry_has_spine_entries():
    """Smoke check the on-disk registry against the v6 §3 step-1 expectations."""

    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    # Must have at least the three spine docs that drive Wave 1 of the cascade.
    for canonical in (
        "decreto.624.1989",
        "decreto.1625.2016",
        "decreto.1072.2015",
        "ley.100.1993",
    ):
        assert canonical in registry, (
            f"missing {canonical} from var/suin_doc_id_registry.json — "
            "rebuild via scripts/canonicalizer/build_suin_doc_id_registry.py"
        )
        entry = registry[canonical]
        assert entry["suin_doc_id"]
        assert entry["ruta"].startswith("https://www.suin-juriscol.gov.co/viewDocument.asp?id=")
        assert entry["title"]
    # `et` alias must point at decreto.624.1989's SUIN doc.
    assert registry["et"]["suin_doc_id"] == registry["decreto.624.1989"]["suin_doc_id"]
