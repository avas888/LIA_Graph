"""fix_v18_may §1.5 Issue E — conflict resolver tests.

Covers:
  * Detector (predicate normalization + value extraction + grouping)
  * A1 article-match resolution
  * A2 LLM fallback (with stub adapter)
  * apply_resolutions (line removal)
  * Mode handling (off / shadow / enforce)
  * §4.1 fixture end-to-end (30 vs 45 días)
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from lia_graph.pipeline_d.answer_conflict_resolver import (
    BulletAssertion,
    ConflictGroup,
    apply_resolutions,
    detect_conflicts,
    resolve_answer_conflicts,
    resolve_via_a1,
    resolve_via_a2,
    resolver_mode,
)
from lia_graph.pipeline_d.answer_conflict_resolver import _normalize_value


# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------


@dataclass
class _StubEvidenceItem:
    title: str = ""
    excerpt: str = ""


@dataclass
class _StubEvidenceBundle:
    primary_articles: tuple


class _StubAdapterChooseA:
    """Always returns "A"."""

    calls: list[str]

    def __init__(self) -> None:
        self.calls = []

    def generate(self, prompt: str) -> str:
        self.calls.append(prompt)
        return "A"


class _StubAdapterChooseB:
    def generate(self, prompt: str) -> str:
        return "B"


class _StubAdapterChooseNone:
    def generate(self, prompt: str) -> str:
        return "NINGUNA"


class _StubAdapterRaises:
    def generate(self, prompt: str) -> str:
        raise RuntimeError("adapter unavailable")


class _StubAdapterUnparseable:
    def generate(self, prompt: str) -> str:
        return "no estoy seguro"


# ---------------------------------------------------------------------------
# Mode
# ---------------------------------------------------------------------------


def test_resolver_mode_default_is_shadow(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LIA_CONFLICT_RESOLVER_MODE", raising=False)
    assert resolver_mode() == "shadow"


def test_resolver_mode_off_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LIA_CONFLICT_RESOLVER_MODE", "legacy")
    assert resolver_mode() == "off"


def test_resolver_mode_enforce(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LIA_CONFLICT_RESOLVER_MODE", "enforce")
    assert resolver_mode() == "enforce"


# ---------------------------------------------------------------------------
# Detector
# ---------------------------------------------------------------------------


def test_detector_finds_basic_30_vs_45_dias_conflict() -> None:
    md = (
        "Recomendaciones Prácticas\n"
        "- **Despido injustificado en AÑO 1:** 30 días de salario.\n"
        "- **Despido injustificado en AÑO 1:** 45 días de salario.\n"
    )
    groups = detect_conflicts(md)
    assert len(groups) == 1
    g = groups[0]
    assert "despido injustificado en a" in g.predicate
    values = {b.value_norm for b in g.bullets}
    # value_norm is accent-stripped (`días` → `dias`).
    assert "30 dias" in values
    assert "45 dias" in values


def test_detector_ignores_same_predicate_same_value() -> None:
    # Two bullets, same predicate, same value → not a conflict.
    md = (
        "- **Indemnización por año:** 30 días de salario.\n"
        "- **Indemnización por año:** 30 días de salario.\n"
    )
    assert detect_conflicts(md) == ()


def test_detector_ignores_different_predicates_with_different_values() -> None:
    # Two SPEC bullets with different qualifiers — different predicates.
    md = (
        "- **Indemnización CST 64 — salario menor 10 SMMLV:** 30 días primer año.\n"
        "- **Indemnización CST 64 — salario mayor 10 SMMLV:** 20 días primer año.\n"
    )
    assert detect_conflicts(md) == ()


def test_detector_handles_decimal_separator_drift() -> None:
    # "3,5%" and "3.5%" are the SAME normalized value → not a conflict.
    md = (
        "- **Tarifa Grupo 1:** 3,5%\n"
        "- **Tarifa Grupo 1:** 3.5%\n"
    )
    assert detect_conflicts(md) == ()


def test_detector_skips_bullets_without_colon() -> None:
    md = (
        "- Esto es un bullet sin dos puntos 30 días\n"
        "- Esto es otro bullet sin dos puntos 45 días\n"
    )
    assert detect_conflicts(md) == ()


def test_detector_skips_bullets_without_numeric_value() -> None:
    md = (
        "- **Concepto:** definición sin números aquí.\n"
        "- **Concepto:** otra explicación sin números.\n"
    )
    assert detect_conflicts(md) == ()


def test_detector_ignores_short_predicates() -> None:
    # 1-word predicates would collide too easily; skip them.
    md = (
        "- **A:** 30 días.\n"
        "- **A:** 45 días.\n"
    )
    assert detect_conflicts(md) == ()


def test_detector_groups_three_bullets_when_value_set_differs() -> None:
    md = (
        "- **Plazo de pago:** 30 días.\n"
        "- **Plazo de pago:** 30 días.\n"
        "- **Plazo de pago:** 60 días.\n"
    )
    groups = detect_conflicts(md)
    assert len(groups) == 1
    assert len(groups[0].bullets) == 3


# ---------------------------------------------------------------------------
# A1 — article match
# ---------------------------------------------------------------------------


def _make_group(values: list[str], predicate: str = "concepto generico de prueba") -> ConflictGroup:
    bullets = tuple(
        BulletAssertion(
            line_index=i,
            raw_line=f"- **{predicate}:** {v}",
            predicate=predicate,
            value_raw=v,
            value_norm=_normalize_value(v),
        )
        for i, v in enumerate(values)
    )
    return ConflictGroup(predicate=predicate, bullets=bullets)


def test_a1_picks_value_that_appears_in_excerpts() -> None:
    group = _make_group(["30 días", "45 días"])
    # The excerpt blob must be passed through the same normalizer the
    # resolver uses internally.
    excerpts = _normalize_value(
        "El primer año paga 30 días de salario, per la regla post-Ley 789."
    )
    result = resolve_via_a1(group, excerpts)
    assert result.decision_path == "a1_article_match"
    assert result.winner_line_index is not None
    assert result.loser_line_indices == (1,)
    assert result.a1_match_count == 1


def test_a1_returns_ambiguous_when_both_values_match() -> None:
    group = _make_group(["30 días", "45 días"])
    excerpts = _normalize_value("Antes era 45 días, ahora son 30 días.")
    result = resolve_via_a1(group, excerpts)
    assert result.decision_path == "a1_ambiguous"
    assert result.winner_line_index is None
    assert result.a1_match_count == 2


def test_a1_returns_ambiguous_when_neither_value_matches() -> None:
    group = _make_group(["30 días", "45 días"])
    excerpts = _normalize_value("La norma habla de 60 días en otro contexto.")
    result = resolve_via_a1(group, excerpts)
    assert result.decision_path == "a1_ambiguous"
    assert result.winner_line_index is None
    assert result.a1_match_count == 0


# ---------------------------------------------------------------------------
# A2 — LLM fallback
# ---------------------------------------------------------------------------


def test_a2_returns_a_when_adapter_picks_a() -> None:
    group = _make_group(["30 días", "45 días"])
    excerpts = [_StubEvidenceItem(title="Art. 64 CST", excerpt="30 días por el primer año")]
    adapter = _StubAdapterChooseA()
    result = resolve_via_a2(group, excerpts, adapter)
    assert result.decision_path == "a2_llm_choice"
    assert result.winner_line_index == 0
    assert result.loser_line_indices == (1,)
    assert len(adapter.calls) == 1
    assert "30 días" in adapter.calls[0]
    assert "45 días" in adapter.calls[0]


def test_a2_returns_b_when_adapter_picks_b() -> None:
    group = _make_group(["30 días", "45 días"])
    excerpts = [_StubEvidenceItem(title="Art. 64 CST", excerpt="...")]
    result = resolve_via_a2(group, excerpts, _StubAdapterChooseB())
    assert result.decision_path == "a2_llm_choice"
    assert result.winner_line_index == 1
    assert result.loser_line_indices == (0,)


def test_a2_handles_ninguna_response() -> None:
    group = _make_group(["30 días", "45 días"])
    result = resolve_via_a2(group, [], _StubAdapterChooseNone())
    assert result.decision_path == "a2_no_decision"
    assert result.winner_line_index is None


def test_a2_handles_adapter_error() -> None:
    group = _make_group(["30 días", "45 días"])
    result = resolve_via_a2(group, [], _StubAdapterRaises())
    assert result.decision_path == "a2_error"
    assert result.winner_line_index is None


def test_a2_handles_unparseable_response() -> None:
    group = _make_group(["30 días", "45 días"])
    result = resolve_via_a2(group, [], _StubAdapterUnparseable())
    assert result.decision_path == "a2_unparseable"
    assert result.winner_line_index is None


# ---------------------------------------------------------------------------
# apply_resolutions
# ---------------------------------------------------------------------------


def test_apply_resolutions_drops_loser_lines() -> None:
    md = (
        "Sección\n"
        "- bullet uno con 30 días.\n"
        "- bullet dos con 45 días.\n"
        "- bullet final.\n"
    )
    group = _make_group(["30", "45"])
    # Patch line indices to match real markdown line positions.
    bullets = (
        BulletAssertion(1, "- bullet uno con 30 días.", "concepto", "30", "30"),
        BulletAssertion(2, "- bullet dos con 45 días.", "concepto", "45", "45"),
    )
    group2 = ConflictGroup(predicate="concepto", bullets=bullets)
    from lia_graph.pipeline_d.answer_conflict_resolver import ConflictResolution

    res = ConflictResolution(
        group=group2,
        winner_line_index=1,
        loser_line_indices=(2,),
        decision_path="a1_article_match",
        a1_match_count=1,
        a2_response_preview=None,
    )
    out = apply_resolutions(md, (res,))
    assert "30 días" in out
    assert "45 días" not in out
    assert "bullet final" in out


def test_apply_resolutions_noop_when_no_winners() -> None:
    md = "- bullet a\n- bullet b\n"
    out = apply_resolutions(md, ())
    assert out == md


# ---------------------------------------------------------------------------
# resolve_answer_conflicts — end-to-end
# ---------------------------------------------------------------------------


def test_resolve_off_mode_returns_input_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIA_CONFLICT_RESOLVER_MODE", "off")
    md = (
        "- **Despido injustificado en AÑO 1:** 30 días de salario.\n"
        "- **Despido injustificado en AÑO 1:** 45 días de salario.\n"
    )
    bundle = _StubEvidenceBundle(
        primary_articles=(_StubEvidenceItem(title="Art. 64 CST", excerpt="30 días por año"),)
    )
    out, diag = resolve_answer_conflicts(md, evidence=bundle)
    assert out == md
    assert diag["mode"] == "off"
    assert diag["groups_detected"] == 0


def test_resolve_shadow_mode_detects_but_does_not_modify(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIA_CONFLICT_RESOLVER_MODE", "shadow")
    md = (
        "- **Despido injustificado en AÑO 1:** 30 días de salario.\n"
        "- **Despido injustificado en AÑO 1:** 45 días de salario.\n"
    )
    bundle = _StubEvidenceBundle(
        primary_articles=(
            _StubEvidenceItem(title="Art. 64 CST", excerpt="30 días por el primer año"),
        )
    )
    out, diag = resolve_answer_conflicts(md, evidence=bundle)
    assert out == md  # shadow: output unchanged
    assert diag["mode"] == "shadow"
    assert diag["groups_detected"] == 1
    assert diag["groups_resolved_a1"] == 1
    assert diag["lines_dropped"] == 0


def test_resolve_enforce_mode_drops_loser_for_30_vs_45_dias_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """§4.1 fixture — the canonical regression case."""
    monkeypatch.setenv("LIA_CONFLICT_RESOLVER_MODE", "enforce")
    md = (
        "Recomendaciones Prácticas\n"
        "\n"
        "- **Despido injustificado en AÑO 1:** 30 días de salario.\n"
        "- **Despido injustificado en AÑO 1:** 45 días de salario.\n"
        "- **Otro bullet:** sin conflicto, ningún número en juego aquí.\n"
    )
    bundle = _StubEvidenceBundle(
        primary_articles=(
            _StubEvidenceItem(
                title="Art. 64 CST — Terminación unilateral",
                excerpt=(
                    "En los contratos a término indefinido la indemnización "
                    "comprende 30 días de salario por el primer año de servicios."
                ),
            ),
        )
    )
    out, diag = resolve_answer_conflicts(md, evidence=bundle)
    assert "30 días de salario" in out
    assert "45 días de salario" not in out
    assert diag["groups_detected"] == 1
    assert diag["groups_resolved_a1"] == 1
    assert diag["lines_dropped"] == 1


def test_resolve_enforce_a1_ambiguous_a2_resolves_with_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A1 can't decide (both/neither values in excerpts) → A2 picks."""
    monkeypatch.setenv("LIA_CONFLICT_RESOLVER_MODE", "enforce")
    md = (
        "- **Plazo de pago de obligación:** 30 días.\n"
        "- **Plazo de pago de obligación:** 60 días.\n"
    )
    # Empty excerpts → A1 ambiguous (neither value matches).
    bundle = _StubEvidenceBundle(primary_articles=())
    out, diag = resolve_answer_conflicts(
        md, evidence=bundle, adapter=_StubAdapterChooseA()
    )
    assert "30 días" in out
    assert "60 días" not in out
    assert diag["groups_resolved_a2"] == 1
    assert diag["lines_dropped"] == 1


def test_resolve_enforce_a1_ambiguous_no_adapter_keeps_both(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A1 ambiguous + no LLM adapter → both bullets survive (safe default)."""
    monkeypatch.setenv("LIA_CONFLICT_RESOLVER_MODE", "enforce")
    md = (
        "- **Plazo de pago de obligación:** 30 días.\n"
        "- **Plazo de pago de obligación:** 60 días.\n"
    )
    bundle = _StubEvidenceBundle(primary_articles=())
    # adapter=None and no runtime_config_path: resolver tries to resolve
    # via default path, gets None, records "a2_no_adapter".
    out, diag = resolve_answer_conflicts(md, evidence=bundle, adapter=None)
    assert "30 días" in out
    assert "60 días" in out
    assert diag["groups_unresolved"] == 1


def test_resolve_catches_polished_section_4_1_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """fix_v18 b2.1 refine — the §4.1 fixture as it appears POST-polish.

    The shadow probe on 2026-05-15 evening showed `no_conflicts` for the
    §4.1 fixture even though the served answer carried both `30 días`
    and `45 días` bullets. Root cause: the resolver was wired pre-polish
    and polish itself normalizes predicate phrasing — the contradictions
    only converge to identical-predicate shape after rendering. The
    wiring was moved post-polish; this test pins that the polished
    shape (bullets with `•` lead, no markdown bold, simple `Predicate:
    value` form) is detected and A1-resolved.
    """
    monkeypatch.setenv("LIA_CONFLICT_RESOLVER_MODE", "enforce")
    md = (
        "Recomendaciones Prácticas\n"
        "• Despido sin justa causa (iniciativa del empleador): código 55.\n"
        "• Despido con justa causa (causal disciplinaria): código 56.\n"
        "• Despido injustificado en AÑO 1: 30 días de salario.\n"
        "• Despido injustificado en AÑO 1: 45 días de salario.\n"
        "• Antes: 30 días × ($2.200.000 ÷ 30) = $2.200.000.\n"
    )
    bundle = _StubEvidenceBundle(
        primary_articles=(
            _StubEvidenceItem(
                title="Art. 64 CST — Terminación unilateral",
                excerpt=(
                    "En los contratos a término indefinido la indemnización "
                    "comprende 30 días de salario por el primer año de servicios."
                ),
            ),
        )
    )
    out, diag = resolve_answer_conflicts(md, evidence=bundle)
    assert "30 días de salario" in out
    assert "45 días de salario" not in out
    assert diag["groups_detected"] == 1
    assert diag["groups_resolved_a1"] == 1
    assert diag["lines_dropped"] == 1
    assert diag["decisions"][0]["path"] == "a1_article_match"


def test_resolve_no_conflicts_returns_input_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIA_CONFLICT_RESOLVER_MODE", "enforce")
    md = "- **Concepto único:** 30 días.\n- **Otro concepto:** 45 días.\n"
    out, diag = resolve_answer_conflicts(md, evidence=None)
    assert out == md
    assert diag["groups_detected"] == 0


def test_resolve_empty_markdown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIA_CONFLICT_RESOLVER_MODE", "shadow")
    out, diag = resolve_answer_conflicts("", evidence=None)
    assert out == ""
    assert diag["groups_detected"] == 0
