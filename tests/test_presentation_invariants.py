"""Pin presentation invariants for the served chat surface.

These tests catch what the LLM polish prompt can only ask for politely:
bullet prefixes, section heading shape, numeric bolding. They are the
deterministic backstop when polish is disabled, the adapter fails, or the
LLM ignores an instruction.
"""

from __future__ import annotations

import pytest

from lia_graph.pipeline_d.presentation import (
    BULLET_PREFIX,
    NESTED_BULLET_PREFIX,
    bold,
    bullet,
    format_numbers_with_bold,
    nested_bullet,
    numbered,
    render_bullet_section,
    render_numbered_section,
    section_heading,
)


class TestBulletAndNumberedPrimitives:
    def test_bullet_prefix_is_canonical(self) -> None:
        assert bullet("Compensa contra renta líquida.") == "- Compensa contra renta líquida."

    def test_nested_bullet_uses_two_space_indent(self) -> None:
        assert nested_bullet("Sub-punto").startswith(NESTED_BULLET_PREFIX)
        assert nested_bullet("Sub-punto") == "  - Sub-punto"

    def test_numbered_starts_at_caller_supplied_index(self) -> None:
        assert numbered(1, "Primero") == "1. Primero"
        assert numbered(7, "Séptimo") == "7. Séptimo"

    def test_bold_wraps_with_double_asterisks(self) -> None:
        assert bold("12") == "**12**"

    def test_section_heading_is_bold(self) -> None:
        assert section_heading("Riesgos y condiciones") == "**Riesgos y condiciones**"


class TestBulletSection:
    def test_each_line_starts_with_bullet_prefix(self) -> None:
        out = render_bullet_section("Ruta sugerida", ("Paso A", "Paso B"))
        lines = out.splitlines()
        assert lines[0] == "**Ruta sugerida**"
        for line in lines[1:]:
            assert line.startswith(BULLET_PREFIX), f"missing prefix: {line!r}"

    def test_empty_lines_are_dropped(self) -> None:
        out = render_bullet_section("X", ("Real", "", "Otra"))
        body = out.splitlines()[1:]
        assert body == ["- Real", "- Otra"]


class TestNumberedSection:
    def test_first_item_starts_with_one(self) -> None:
        out = render_numbered_section("Procedimiento", ("Liquida", "Paga", "Reporta"))
        body = out.splitlines()[1:]
        assert body[0].startswith("1. ")
        assert body[1].startswith("2. ")
        assert body[2].startswith("3. ")

    def test_numbering_skips_blank_entries(self) -> None:
        out = render_numbered_section("X", ("Uno", "", "Dos"))
        body = out.splitlines()[1:]
        assert body == ["1. Uno", "3. Dos"]


class TestFormatNumbersWithBold:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("Aplica por 6 años.", "Aplica por **6** años."),
            ("Tarifa del 25%.", "Tarifa del **25%**."),
            ("Monto: $1.000.000.", "Monto: **$1.000.000**."),
            ("Vence en 2025.", "Vence en **2025**."),
            ("12 períodos gravables.", "**12** períodos gravables."),
            ("Plazo de 6 años y tope de 25%.", "Plazo de **6** años y tope de **25%**."),
        ],
    )
    def test_wraps_standalone_numbers(self, raw: str, expected: str) -> None:
        assert format_numbers_with_bold(raw) == expected

    def test_preserves_legal_anchor_numbers(self) -> None:
        raw = "Compensa según (art. 147 ET) durante 12 años."
        out = format_numbers_with_bold(raw)
        assert "(art. 147 ET)" in out, "anchor must be preserved verbatim"
        assert "**12**" in out, "number outside anchor must be bolded"
        assert "**147**" not in out, "anchor internal number must NOT be bolded"

    def test_preserves_multi_article_anchor(self) -> None:
        raw = "Revisá (arts. 147 y 290 ET) y aplicá durante 6 períodos."
        out = format_numbers_with_bold(raw)
        assert "(arts. 147 y 290 ET)" in out
        assert "**6**" in out

    def test_preserves_decreto_and_ley_anchors(self) -> None:
        raw = "Per (Decreto 624 de 1989) y (Ley 1819 de 2016), aplicá por 6 años."
        out = format_numbers_with_bold(raw)
        assert "(Decreto 624 de 1989)" in out
        assert "(Ley 1819 de 2016)" in out
        assert "**6**" in out
        assert "**624**" not in out
        assert "**1819**" not in out

    def test_idempotent_does_not_double_wrap(self) -> None:
        once = format_numbers_with_bold("Aplica por 6 años.")
        twice = format_numbers_with_bold(once)
        assert once == twice == "Aplica por **6** años."

    def test_empty_and_none_safe(self) -> None:
        assert format_numbers_with_bold("") == ""
        assert format_numbers_with_bold("Sin cifras aquí.") == "Sin cifras aquí."

    def test_real_answer_shape_from_2026_05_10_screenshot(self) -> None:
        # Regression case: the actual rendered text the operator flagged.
        raw = (
            "Para pérdidas sujetas al régimen vigente, el límite es temporal: "
            "doce períodos gravables siguientes y sin tope porcentual anual."
        )
        # Note: spelled-out "doce" stays untouched at the post-hoc layer; the
        # prompt asks the LLM for digit form. This test pins the digit-bold
        # behavior — the spelled-out conversion is a polish-prompt contract,
        # not a deterministic transform.
        out = format_numbers_with_bold(raw + " Plazo de 12 años.")
        assert "**12** años" in out
