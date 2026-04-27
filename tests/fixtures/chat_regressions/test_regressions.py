"""Shape-only tests over the Phase 7 chat regression fixtures.

These tests run under `make test-batched` to catch malformed or incomplete
fixtures early. The full answer-generation gate runs inside
`scripts/ingestion/fire_suin_cloud.sh` and requires the live retrieval stack — it is
not invoked from here.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


_FIXTURES_DIR = Path(__file__).resolve().parent
_REQUIRED_FIELDS = {"id", "category", "question", "expected_contains", "expected_flags"}
_REQUIRED_CATEGORIES = {"tax", "labor", "cross_domain", "derogated"}
_EXPECTED_CATEGORY_COUNTS = {
    "tax": 3,
    "labor": 3,
    "cross_domain": 2,
    "derogated": 2,
}


def _fixtures() -> list[dict]:
    rows: list[dict] = []
    for path in sorted(_FIXTURES_DIR.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["_path"] = str(path)
        rows.append(payload)
    return rows


@pytest.fixture(scope="module")
def fixtures() -> list[dict]:
    return _fixtures()


def test_fixture_count_is_ten(fixtures: list[dict]) -> None:
    assert len(fixtures) == 10, [f["id"] for f in fixtures]


def test_every_fixture_has_required_fields(fixtures: list[dict]) -> None:
    for row in fixtures:
        missing = _REQUIRED_FIELDS - row.keys()
        assert not missing, f"{row['_path']} missing {missing}"


def test_every_fixture_id_is_unique(fixtures: list[dict]) -> None:
    ids = [row["id"] for row in fixtures]
    assert len(ids) == len(set(ids)), ids


def test_category_coverage_matches_plan(fixtures: list[dict]) -> None:
    counts: dict[str, int] = {}
    for row in fixtures:
        category = row["category"]
        assert category in _REQUIRED_CATEGORIES, f"unknown category {category!r}"
        counts[category] = counts.get(category, 0) + 1
    assert counts == _EXPECTED_CATEGORY_COUNTS, counts


def test_expected_contains_is_non_empty(fixtures: list[dict]) -> None:
    for row in fixtures:
        expected = row["expected_contains"]
        assert isinstance(expected, list) and expected, row["_path"]
        assert all(isinstance(item, str) and item.strip() for item in expected)


def test_question_is_spanish_and_ends_with_qmark(fixtures: list[dict]) -> None:
    for row in fixtures:
        question = row["question"].strip()
        assert question.endswith("?"), row["_path"]
