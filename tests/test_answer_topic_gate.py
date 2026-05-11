"""Contract tests for the synthesis-time cross-topic content gate
(fix_v7 §3c). Locks four invariants the runtime depends on:

1. No-op when the primary topic isn't in the allowlist (safety: never
   make answers worse than today).
2. Bullets that cite a norm outside the allowlist are dropped.
3. Bullets with no norm citation pass unchanged.
4. The `LIA_TOPIC_GATE_MODE=off` operator override bypasses everything.
"""

from __future__ import annotations

import pytest

from lia_graph.pipeline_d.answer_topic_gate import (
    _bullet_passes,
    _extract_article_keys,
    _load_allowlist,
    filter_template_bullets,
)


def _clear_caches():
    _load_allowlist.cache_clear()


@pytest.fixture(autouse=True)
def _autoclear_caches(monkeypatch):
    _clear_caches()
    monkeypatch.setenv("LIA_TOPIC_GATE_MODE", "enforce")
    yield
    _clear_caches()


# --- regex extraction -------------------------------------------------------


def test_extracts_parenthesized_single_anchor() -> None:
    assert _extract_article_keys("Aplica (art. 147 ET) al caso.") == ("art:147",)


def test_extracts_parenthesized_multi_anchor() -> None:
    keys = _extract_article_keys("Combina (arts. 290, 588 y 589 ET).")
    assert set(keys) == {"art:290", "art:588", "art:589"}


def test_extracts_bare_prose_anchor() -> None:
    assert _extract_article_keys("Revisa Art. 905 ET.") == ("art:905",)


def test_extracts_hyphenated_article_number() -> None:
    assert _extract_article_keys("(Art. 689-3 ET)") == ("art:689-3",)


def test_no_citation_returns_empty() -> None:
    assert _extract_article_keys("Verifica con un CP autorizado.") == ()


# --- _bullet_passes ---------------------------------------------------------


def test_bullet_with_no_citation_passes() -> None:
    assert _bullet_passes(
        "- Verifica con un CP autorizado.",
        allowed_prefixes=("art:147", "art:290"),
    )


def test_bullet_with_matching_citation_passes() -> None:
    assert _bullet_passes(
        "- Aplica el art. 147 ET y verifica el plazo.",
        allowed_prefixes=("art:147", "art:290"),
    )


def test_bullet_with_unlisted_citation_drops() -> None:
    assert not _bullet_passes(
        "- Revisa Art. 905 ET porque rige el régimen simple.",
        allowed_prefixes=("art:147", "art:290"),
    )


def test_bullet_passes_only_if_every_anchor_matches() -> None:
    # 290 is allowed; 588 is not — bullet must drop.
    assert not _bullet_passes(
        "- (arts. 290 y 588 ET)",
        allowed_prefixes=("art:290",),
    )


def test_bullet_passes_with_empty_allowed_prefixes() -> None:
    # When the topic entry has no curated prefixes, the gate treats the
    # bullet as passable rather than vacuously failing every bullet.
    assert _bullet_passes(
        "- (art. 905 ET)",
        allowed_prefixes=(),
    )


# --- filter_template_bullets ------------------------------------------------


def test_gate_is_noop_for_unlisted_topic() -> None:
    template = (
        "## Sección\n"
        "- (art. 905 ET) régimen simple.\n"
        "- (art. 999 ET) un norma inexistente.\n"
    )
    filtered, diag = filter_template_bullets(
        template, primary_topic="topic_does_not_exist"
    )
    assert filtered == template, "gate must be a no-op for unlisted topics"
    assert diag["gate_mode"] == "noop_no_topic_entry"


def test_gate_drops_perdidas_unlisted_bullets() -> None:
    template = (
        "## Ruta sugerida\n"
        "- Aplica la deducción por pérdidas conforme al art. 147 ET.\n"
        "- Revisa Art. 905 ET porque rige el régimen simple.\n"
        "- Verifica con un CP autorizado.\n"
    )
    filtered, diag = filter_template_bullets(
        template, primary_topic="perdidas_fiscales_art147"
    )
    assert "- Aplica la deducción por pérdidas conforme al art. 147 ET." in filtered
    assert "Art. 905 ET" not in filtered, (
        "régimen-simple bullet must be dropped under perdidas_fiscales_art147"
    )
    assert "- Verifica con un CP autorizado." in filtered
    assert diag["gate_mode"] == "applied"
    assert diag["dropped_count"] == 1
    assert "Art. 905 ET" in (diag["dropped_excerpts"][0] or "")


def test_bullets_without_citations_pass_unchanged() -> None:
    template = (
        "## Práctico\n"
        "- Reúne soportes de tu cliente.\n"
        "- Confirma el archivo de declaraciones.\n"
        "- Coordina con el revisor fiscal.\n"
    )
    filtered, diag = filter_template_bullets(
        template, primary_topic="perdidas_fiscales_art147"
    )
    assert filtered == template
    assert diag["gate_mode"] == "applied"
    assert diag["dropped_count"] == 0
    assert diag["kept_count"] == 3


def test_gate_disabled_by_env_returns_template_unchanged(monkeypatch) -> None:
    monkeypatch.setenv("LIA_TOPIC_GATE_MODE", "off")
    _clear_caches()
    template = (
        "## Ruta sugerida\n"
        "- Revisa Art. 905 ET porque rige el régimen simple.\n"
    )
    filtered, diag = filter_template_bullets(
        template, primary_topic="perdidas_fiscales_art147"
    )
    assert filtered == template
    assert diag["gate_mode"] == "disabled_by_env"


def test_gate_preserves_section_headers_and_prose() -> None:
    template = (
        "## Encabezado\n"
        "\n"
        "Lia te recomienda lo siguiente:\n"
        "\n"
        "- (art. 147 ET) caso permitido.\n"
        "- (art. 905 ET) caso prohibido.\n"
        "\n"
        "Recuerda confirmar con un experto.\n"
    )
    filtered, _diag = filter_template_bullets(
        template, primary_topic="perdidas_fiscales_art147"
    )
    assert "## Encabezado" in filtered
    assert "Lia te recomienda lo siguiente:" in filtered
    assert "Recuerda confirmar con un experto." in filtered
    assert "- (art. 147 ET) caso permitido." in filtered
    assert "art. 905 ET" not in filtered


def test_gate_diagnostic_carries_excerpts() -> None:
    template = (
        "- (art. 905 ET) primer prohibido.\n"
        "- (art. 906 ET) segundo prohibido.\n"
        "- (art. 147 ET) permitido.\n"
    )
    _filtered, diag = filter_template_bullets(
        template, primary_topic="perdidas_fiscales_art147"
    )
    assert diag["dropped_count"] == 2
    assert any("905" in excerpt for excerpt in diag["dropped_excerpts"])
    assert any("906" in excerpt for excerpt in diag["dropped_excerpts"])


def test_gate_returns_template_when_primary_topic_is_none() -> None:
    template = "- (art. 905 ET) sin topic."
    filtered, diag = filter_template_bullets(template, primary_topic=None)
    assert filtered == template
    assert diag["gate_mode"] == "noop_no_topic_entry"
