"""Tests for ``lia_graph.ingestion.article_secondary_topics`` (v5 §1.A)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lia_graph.ingestion import article_secondary_topics as ast


@pytest.fixture(autouse=True)
def _reset_cache() -> None:
    ast.reset_lookup_cache_for_tests()
    yield
    ast.reset_lookup_cache_for_tests()


def test_missing_config_returns_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(
        "LIA_ARTICLE_SECONDARY_TOPICS_PATH", str(tmp_path / "does_not_exist.json")
    )
    assert ast.get_secondary_topics("689-3") == ()


def test_malformed_json_degrades_gracefully(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    p = tmp_path / "bad.json"
    p.write_text("not valid json {", encoding="utf-8")
    monkeypatch.setenv("LIA_ARTICLE_SECONDARY_TOPICS_PATH", str(p))
    assert ast.get_secondary_topics("689-3") == ()
    err = capsys.readouterr().err
    assert "article_secondary_topics" in err


def test_well_formed_config_returns_topics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    p = tmp_path / "good.json"
    p.write_text(
        json.dumps({
            "articles": [
                {
                    "article_id": "689-3",
                    "primary_topic": "firmeza_declaraciones",
                    "secondary_topics": ["beneficio_auditoria"],
                },
                {
                    "article_id": "49",
                    "primary_topic": "ingresos_fiscales_renta",
                    "secondary_topics": ["dividendos_y_distribucion_utilidades"],
                },
            ],
        }),
        encoding="utf-8",
    )
    monkeypatch.setenv("LIA_ARTICLE_SECONDARY_TOPICS_PATH", str(p))
    assert ast.get_secondary_topics("689-3") == ("beneficio_auditoria",)
    assert ast.get_secondary_topics("49") == ("dividendos_y_distribucion_utilidades",)
    assert ast.get_secondary_topics("999") == ()  # not in config


def test_empty_secondary_list_is_skipped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    p = tmp_path / "empty_secondaries.json"
    p.write_text(
        json.dumps({
            "articles": [
                {
                    "article_id": "714",
                    "primary_topic": "firmeza_declaraciones",
                    "secondary_topics": [],
                },
            ],
        }),
        encoding="utf-8",
    )
    monkeypatch.setenv("LIA_ARTICLE_SECONDARY_TOPICS_PATH", str(p))
    # Empty secondary list ⇒ no entry in the lookup ⇒ caller sees ().
    assert ast.get_secondary_topics("714") == ()


def test_articles_field_must_be_list(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    p = tmp_path / "wrong_shape.json"
    p.write_text(
        json.dumps({"articles": {"689-3": ["beneficio_auditoria"]}}),  # dict, not list
        encoding="utf-8",
    )
    monkeypatch.setenv("LIA_ARTICLE_SECONDARY_TOPICS_PATH", str(p))
    assert ast.get_secondary_topics("689-3") == ()
    err = capsys.readouterr().err
    assert "not a list" in err


def test_default_seed_config_loads_in_repo() -> None:
    """The committed `config/article_secondary_topics.json` must parse and
    have the seed entry for Art. 689-3 → beneficio_auditoria so v5 §1.A
    has at least one end-to-end demonstrable case."""
    # Use the default path (no env override) — exercises the committed file.
    assert ast.get_secondary_topics("689-3") == ("beneficio_auditoria",)


def test_default_seed_topics_all_in_canonical_taxonomy() -> None:
    """Operator's binding rule (2026-04-26): every primary/secondary topic
    referenced in `config/article_secondary_topics.json` MUST exist in
    `config/topic_taxonomy.json`. Otherwise we have ghost topics that
    match nothing or break things silently.

    Mirrors the existing `test_path_veto_all_targets_are_valid_taxonomy_keys`
    discipline — same rule, different config surface.
    """
    import json
    from pathlib import Path
    from lia_graph.topic_taxonomy import iter_topic_taxonomy_entries

    valid = {e.key for e in iter_topic_taxonomy_entries()}
    cfg = json.loads(
        Path("config/article_secondary_topics.json").read_text(encoding="utf-8")
    )
    for entry in cfg.get("articles", []):
        aid = entry.get("article_id")
        primary = entry.get("primary_topic")
        if primary:
            assert primary in valid, (
                f"primary_topic {primary!r} for article_id={aid!r} is not in "
                "topic_taxonomy.json"
            )
        for sec in entry.get("secondary_topics", []):
            assert sec in valid, (
                f"secondary_topic {sec!r} for article_id={aid!r} is not in "
                "topic_taxonomy.json"
            )


def test_unknown_secondary_topic_is_dropped_with_warning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An entry with a bogus secondary_topic must be quarantined — the
    article still gets the valid topics, the bogus one is dropped, and a
    warning hits stderr so the operator notices the typo."""
    p = tmp_path / "with_unknown.json"
    p.write_text(
        json.dumps({
            "articles": [
                {
                    "article_id": "999-1",
                    "primary_topic": "beneficio_auditoria",
                    "secondary_topics": [
                        "firmeza_declaraciones",          # valid
                        "topic_that_does_not_exist_v5",   # bogus
                    ],
                },
            ],
        }),
        encoding="utf-8",
    )
    monkeypatch.setenv("LIA_ARTICLE_SECONDARY_TOPICS_PATH", str(p))
    result = ast.get_secondary_topics("999-1")
    assert result == ("firmeza_declaraciones",), (
        "the bogus topic must be dropped; the valid one must survive"
    )
    err = capsys.readouterr().err
    assert "topic_that_does_not_exist_v5" in err
    assert "dropped" in err
