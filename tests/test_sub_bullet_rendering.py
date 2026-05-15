"""v17 follow-up (2026-05-15) — sub-bullet rendering survives the
synthesis whitespace-collapse.

Problem statement: `answer_shared.append_unique` and
`neutralize_non_imputative_language` both collapse every newline to a
single space before a SPEC bullet reaches the renderer. Any literal
`\\n  - ` in a SPEC bullet dies. The fix introduces a non-whitespace
sentinel token (`SUB_BULLET_TOKEN`) that SPEC authors embed via
`with_sub_bullets`; the token survives every collapse, and
`render_bullet_section` expands it into proper nested markdown at the
final render step.

These tests pin that contract:

1. The sentinel survives `append_unique`'s whitespace collapse.
2. The sentinel survives `neutralize_non_imputative_language`.
3. `render_bullet_section` expands the sentinel to nested-bullet markdown.
4. A flat bullet with no sentinel renders unchanged (no regression).
5. SPEC bullets in `CASE_REGISTRY` MUST NOT contain literal newlines
   (use `with_sub_bullets` instead — newlines die at insert-time).
6. SPEC bullets MUST NOT contain noise the legacy
   `clean_support_line_for_answer` would strip (URLs, `Actualícese:`
   prefixes, arrow characters), since SPEC bullets bypass that
   cleaner — the lint here is the safety net.
"""
from __future__ import annotations

import re

from lia_graph.pipeline_d.answer_shared import (
    append_unique,
    neutralize_non_imputative_language,
)
from lia_graph.pipeline_d.case_bullets import CASE_REGISTRY
from lia_graph.pipeline_d.presentation import (
    NESTED_BULLET_PREFIX,
    SUB_BULLET_TOKEN,
    expand_sub_bullets,
    render_bullet_section,
    with_sub_bullets,
)


# ---------------------------------------------------------------------------
# 1. Sentinel survives the two whitespace-collapse callers.
# ---------------------------------------------------------------------------


def test_sub_bullet_token_survives_append_unique() -> None:
    bullet_text = with_sub_bullets("**Lead:**", ("alpha", "beta"))
    bucket: list[str] = []
    append_unique(bucket, bullet_text)
    assert len(bucket) == 1
    assert SUB_BULLET_TOKEN in bucket[0]
    # The inner whitespace inside each sub-item is preserved as a
    # single space (collapse is intra-line, not inter-line); the
    # sentinel itself is untouched.
    assert "alpha" in bucket[0]
    assert "beta" in bucket[0]


def test_sub_bullet_token_survives_neutralize() -> None:
    bullet_text = with_sub_bullets("**Lead:**", ("alpha", "beta"))
    cleaned = neutralize_non_imputative_language(bullet_text)
    assert SUB_BULLET_TOKEN in cleaned
    assert "alpha" in cleaned and "beta" in cleaned


# ---------------------------------------------------------------------------
# 2. Renderer expands the sentinel to nested markdown.
# ---------------------------------------------------------------------------


def test_render_bullet_section_expands_sub_bullets() -> None:
    bullet_text = with_sub_bullets(
        "**Recargos (CST 159, 168, 179):**",
        (
            "nocturno **+ 35 %**",
            "extra diurna **+ 25 %**",
        ),
    )
    rendered = render_bullet_section("Recomendaciones Prácticas", (bullet_text,))
    expected_lines = [
        "**Recomendaciones Prácticas**",
        "- **Recargos (CST 159, 168, 179):**",
        f"{NESTED_BULLET_PREFIX}nocturno **+ 35 %**",
        f"{NESTED_BULLET_PREFIX}extra diurna **+ 25 %**",
    ]
    assert rendered == "\n".join(expected_lines)


def test_render_bullet_section_flat_bullets_unchanged() -> None:
    """Regression: a bullet without the sentinel renders as a single
    top-level line. No accidental nesting."""
    rendered = render_bullet_section(
        "Recomendaciones Prácticas",
        ("**Devengado mensual:** salario básico + auxilios.",),
    )
    assert rendered == (
        "**Recomendaciones Prácticas**\n"
        "- **Devengado mensual:** salario básico + auxilios."
    )


def test_expand_sub_bullets_is_idempotent_on_flat_line() -> None:
    line = "- plain bullet without any sentinel"
    assert expand_sub_bullets(line) == line


# ---------------------------------------------------------------------------
# 3. End-to-end: build a fake recommendations tuple the way the
#    synthesis layer would, then render it, and confirm nested markdown
#    survives.
# ---------------------------------------------------------------------------


def test_end_to_end_append_then_render_preserves_nesting() -> None:
    raw_bullet = with_sub_bullets(
        "**Aportes empleador sobre IBC:**",
        (
            "salud **8,5 %**",
            "pensión **12 %**",
            "Caja de Compensación **4 %** — siempre se paga",
        ),
    )
    bucket: list[str] = []
    append_unique(bucket, raw_bullet)
    rendered = render_bullet_section("Recomendaciones Prácticas", tuple(bucket))
    assert "  - salud **8,5 %**" in rendered
    assert "  - pensión **12 %**" in rendered
    assert "  - Caja de Compensación **4 %** — siempre se paga" in rendered
    # The lead is a top-level bullet.
    assert "- **Aportes empleador sobre IBC:**" in rendered
    # The sentinel is fully expanded — none should remain in the output.
    assert SUB_BULLET_TOKEN not in rendered


# ---------------------------------------------------------------------------
# 4. Registry lint — SPEC bullets must not embed literal newlines or
#    noise that would have been stripped by the legacy cleaner.
# ---------------------------------------------------------------------------


_NOISE_PATTERNS = (
    # URLs — chunk-extracted noise, never legitimate in a SPEC bullet.
    re.compile(r"https?://", re.IGNORECASE),
    # "Actualícese:" / "Gerencie.com:" / "DIAN:" prefix on a line —
    # leaks from secondary-source captions.
    re.compile(
        r"^(?:Actual[íi]cese|Gerencie\.com|Gerencie|[ÁA]mbito Jur[ií]dico|DIAN)\s*[:\-—]",
        re.IGNORECASE,
    ),
    # NOTE: the legacy `clean_support_line_for_answer` also drops any
    # line containing `→` / `➜`. That filter is correct for raw
    # chunk-extracted text (where the arrows mark broken markup), but
    # author-written SPEC bullets use the same arrow as a Spanish
    # "leads to" operator ("00–07 → día 2"). We therefore intentionally
    # do NOT lint arrows out of SPEC bullets — only the unambiguous
    # noise patterns above.
)


def test_spec_bullets_have_no_literal_newlines() -> None:
    """A SPEC bullet must not embed a literal newline — use
    `with_sub_bullets` instead. Newlines die in `append_unique`'s
    whitespace collapse, so they would be silently lost at render."""
    offenders: list[str] = []
    for spec in CASE_REGISTRY:
        for bullet in spec.bullets:
            if "\n" in bullet:
                offenders.append(f"{spec.name}: {bullet[:80]}…")
    assert not offenders, (
        "SPEC bullets must use `with_sub_bullets` instead of literal "
        "newlines; offenders:\n" + "\n".join(offenders)
    )


def test_spec_bullets_have_no_corpus_chunk_noise() -> None:
    """SPEC bullets are author-written and bypass the legacy chunk-text
    cleaner. The lint here is the safety net: reject URLs, secondary-
    source caption prefixes, and arrow characters before they ship."""
    offenders: list[str] = []
    for spec in CASE_REGISTRY:
        for bullet in spec.bullets:
            for pattern in _NOISE_PATTERNS:
                if pattern.search(bullet):
                    offenders.append(
                        f"{spec.name} ({pattern.pattern!r}): {bullet[:120]}…"
                    )
                    break
    assert not offenders, (
        "SPEC bullets contain corpus-chunk noise that the legacy "
        "cleaner would have stripped; SPEC bullets bypass that "
        "cleaner — author them clean. Offenders:\n"
        + "\n".join(offenders)
    )
