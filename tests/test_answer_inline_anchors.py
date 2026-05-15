"""v15.3 (2026-05-14) — inline-anchor ranking correctness.

Before v15.3, `select_inline_anchors` had two failure modes that
mis-tagged off-axis bullets with the dominant primary articles:

1. **Free position bonus.** Any primary article got a ~0.9 position
   bonus + ~0.4 hop-0 bonus = 1.3 default score even with zero token
   overlap with the bullet — clearing the 0.75 threshold "for free".
   Consequence: a bullet about *causación* on a GMF query inherited
   the GMF-creation articles (870/871) as its inline anchor, even
   though causación is governed by art. 28 ET.

2. **Auto-fallback to primary[:max_refs].** When no candidate scored
   above 0.75, the function attached the top primary articles anyway.
   Same outcome: off-axis bullets got mis-anchored.

v15.3 fixes both: position bonuses require any content signal (article
number in line, or non-empty title / excerpt overlap), and the
auto-fallback was removed. A bullet that legitimately matches a primary
article via overlap STILL gets correctly anchored; a bullet that
doesn't, renders without an inline citation (Anclaje Legal already
carries the primary norms).
"""

from __future__ import annotations

from lia_graph.pipeline_d.answer_inline_anchors import select_inline_anchors
from lia_graph.pipeline_d.contracts import GraphEvidenceItem


def _art(num: str, title: str, *, hop: int = 0, excerpt: str = "") -> GraphEvidenceItem:
    return GraphEvidenceItem(
        node_kind="article",
        node_key=num,
        title=title,
        excerpt=excerpt,
        source_path=None,
        score=1.0,
        hop_distance=hop,
    )


# ---------------------------------------------------------------------------
# The pre-v15.3 bug: off-axis bullets inherited primary anchors.
# ---------------------------------------------------------------------------


def test_off_axis_bullet_returns_no_anchors() -> None:
    """A bullet about causación on a GMF query must NOT pick up the
    dominant GMF-creation articles. With no token overlap and the
    fallback removed, it returns () so the renderer leaves the bullet
    unanchored."""
    primary = (
        _art("870", "Gravamen a los Movimientos Financieros, GMF"),
        _art("871", "Hecho generador del GMF"),
        _art("872", "Tarifa del gravamen a los movimientos financieros"),
    )
    bullet = (
        "Para la deducción fiscal, considera el principio de causación: "
        "los ingresos y gastos se reconocen cuando ocurren económicamente, "
        "no cuando se recaudan o pagan."
    )
    anchors = select_inline_anchors(
        bullet,
        primary_articles=primary,
        connected_articles=(),
    )
    assert anchors == ()


def test_off_axis_bullet_with_no_overlap_skips_position_bonus() -> None:
    """The position bonus alone (~1.3) used to clear the 0.75 floor
    even with zero token overlap. v15.3 requires content signal first."""
    primary = (_art("870", "Gravamen a los Movimientos Financieros, GMF"),)
    bullet = "Identificar faltantes, sobrantes, obsolescencia y mercancía dañada."
    anchors = select_inline_anchors(
        bullet,
        primary_articles=primary,
        connected_articles=(),
    )
    assert anchors == ()


# ---------------------------------------------------------------------------
# On-axis bullets still anchor correctly (the regression-prevention case).
# ---------------------------------------------------------------------------


def test_bullet_mentioning_article_number_anchors_to_it() -> None:
    """Score += 5.0 when the article number appears in the bullet
    text — that should still beat any threshold."""
    primary = (_art("115", "Deducción de impuestos pagados"),)
    bullet = "El tratamiento del GMF se fundamenta en el art. 115 ET."
    anchors = select_inline_anchors(
        bullet,
        primary_articles=primary,
        connected_articles=(),
    )
    assert anchors == ("115",)


def test_bullet_with_title_token_overlap_anchors() -> None:
    """When the bullet shares non-trivial tokens with the article
    title, the position + overlap bonuses apply and the article
    anchors correctly."""
    primary = (_art("870", "Gravamen a los Movimientos Financieros, GMF"),)
    bullet = (
        "Registra el GMF en la contabilidad con un débito a la cuenta 530505 "
        "— Gravamen a los movimientos financieros por el valor total pagado."
    )
    anchors = select_inline_anchors(
        bullet,
        primary_articles=primary,
        connected_articles=(),
    )
    assert anchors == ("870",)


def test_two_articles_both_overlap_returns_both() -> None:
    primary = (
        _art("870", "Gravamen a los Movimientos Financieros, GMF"),
        _art("872", "Tarifa del gravamen a los movimientos financieros"),
    )
    bullet = (
        "Registra el GMF en la contabilidad con un débito a la cuenta 530505 "
        "— gravamen a los movimientos financieros por el valor total pagado."
    )
    anchors = select_inline_anchors(
        bullet,
        primary_articles=primary,
        connected_articles=(),
        max_refs=2,
    )
    # Both share "gravamen movimientos financieros" tokens with the
    # bullet — both score above threshold.
    assert set(anchors) == {"870", "872"}


def test_empty_candidate_pool_returns_empty() -> None:
    anchors = select_inline_anchors(
        "Cualquier bullet",
        primary_articles=(),
        connected_articles=(),
    )
    assert anchors == ()


def test_excerpt_overlap_alone_can_anchor() -> None:
    """When title doesn't match but the excerpt does, the bullet
    still anchors. Common when the article title is terse."""
    primary = (
        _art(
            "28",
            "Realización del ingreso",
            excerpt=(
                "El principio de causación implica que ingresos y gastos se "
                "reconocen cuando ocurren económicamente, no cuando se pagan."
            ),
        ),
    )
    bullet = (
        "Para la deducción fiscal, considera el principio de causación: "
        "ingresos y gastos se reconocen cuando ocurren económicamente, "
        "no cuando se pagan."
    )
    anchors = select_inline_anchors(
        bullet,
        primary_articles=primary,
        connected_articles=(),
    )
    assert anchors == ("28",)
