"""Norm-id canonicalizer tests — fixplan_v3 §0.5.4 round-trip table.

Sub-fix 1A H0 tests. No DB / scrapers. Validates the §0.5 grammar plus the
refusal contract for the four ambiguous cases.
"""

from __future__ import annotations

import pytest

from lia_graph.canon import (
    KNOWN_EMISORES,
    InvalidNormIdError,
    assert_valid_norm_id,
    canonicalize,
    canonicalize_or_refuse,
    display_label,
    find_mentions,
    is_sub_unit,
    is_valid_norm_id,
    norm_type,
    parent_norm_id,
    sub_unit_kind,
)


# ---------------------------------------------------------------------------
# §0.5.4 round-trip table — the binding examples
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "mention, expected",
    [
        ("Art. 689-3 ET", "et.art.689-3"),
        ("art 689-3 et", "et.art.689-3"),
        ("el artículo 689-3 del Estatuto Tributario", "et.art.689-3"),
        ("Estatuto Tributario, articulo 689-3", "et.art.689-3"),
        ("Art. 689-3 ET parágrafo 2", "et.art.689-3.par.2"),
        ("Art. 689-3, par. 2 ET", "et.art.689-3.par.2"),
        ("Ley 2277 de 2022, Art. 96", "ley.2277.2022.art.96"),
        ("art 96 ley 2277/2022", "ley.2277.2022.art.96"),
        ("Decreto 1474 de 2025", "decreto.1474.2025"),
        ("Concepto DIAN 100208192-202 numeral 20", "concepto.dian.100208192-202.num.20"),
        ("Sentencia C-481 de 2019", "sent.cc.C-481.2019"),
    ],
)
def test_canonicalize_table(mention: str, expected: str):
    assert canonicalize(mention) == expected


def test_canonicalize_auto_ce_with_iso_date():
    # Spanish-month form ("16 de diciembre de 2024 (CE Sección Cuarta, expediente 28920)")
    result = canonicalize("Auto 28920 de 2024 del 16 de diciembre (CE Sección Cuarta)")
    # Note: this synthesizes the CE auto id; date may resolve via the rule order.
    assert result is not None
    assert result.startswith("auto.ce.28920.2024")


# ---------------------------------------------------------------------------
# Refusal cases — §0.5.4 binding ambiguous mentions
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "mention, expected_reason",
    [
        ("Decreto 1474", "missing_year"),
        ("Ley 2277", "missing_year"),
        ("Art. 240", "no_law_prefix"),
        ("según la DIAN...", "no_concept_number"),
        ("Sentencia de la Corte sobre zonas francas", "no_court_or_letter_prefix"),
    ],
)
def test_canonicalize_refusal_reasons(mention: str, expected_reason: str):
    norm_id, refusal = canonicalize_or_refuse(mention)
    assert norm_id is None
    assert refusal is not None
    assert refusal.reason == expected_reason


# ---------------------------------------------------------------------------
# Idempotency — already-canonical norm_ids round-trip unchanged
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "norm_id",
    [
        "et",
        "et.art.689-3",
        "et.art.689-3.par.2",
        "et.art.158-1",
        "ley.2277.2022",
        "ley.2277.2022.art.96",
        "decreto.1474.2025",
        "decreto.1625.2016.art.1.2.1.2.1",
        "res.dian.165.2023",
        "res.dian.165.2023.art.5",
        "concepto.dian.100208192-202",
        "concepto.dian.100208192-202.num.20",
        "sent.cc.C-481.2019",
        "sent.cc.T-077.2022",
        "sent.ce.28920.2025.07.03",
        "auto.ce.28920.2024.12.16",
    ],
)
def test_idempotent_already_canonical(norm_id: str):
    assert canonicalize(norm_id) == norm_id
    assert is_valid_norm_id(norm_id)


# ---------------------------------------------------------------------------
# Grammar checker
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad",
    [
        "et.art",  # missing article number
        "ley.2277",  # missing year
        "decreto.1474",  # missing year
        "concepto.dian",  # missing number
        "sent.cc.481.2019",  # missing letter prefix
        "auto.ce.28920.2024",  # missing month/day
        "et.art.689-3.foo.2",  # invalid sub-unit kind
        "RES.DIAN.165.2023",  # uppercase prefix
    ],
)
def test_invalid_norm_ids_rejected(bad: str):
    assert not is_valid_norm_id(bad)
    with pytest.raises(InvalidNormIdError):
        assert_valid_norm_id(bad)


# ---------------------------------------------------------------------------
# Helpers — parent, sub-unit detection, type inference, display label
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "norm_id, expected_parent",
    [
        ("et.art.689-3", "et"),
        ("et.art.689-3.par.2", "et.art.689-3"),
        ("ley.2277.2022.art.96", "ley.2277.2022"),
        ("ley.2277.2022", None),
        ("decreto.1474.2025", None),
        ("concepto.dian.100208192-202.num.20", "concepto.dian.100208192-202"),
        ("sent.cc.C-481.2019", None),
        ("et", None),
    ],
)
def test_parent_norm_id(norm_id: str, expected_parent: str | None):
    assert parent_norm_id(norm_id) == expected_parent


@pytest.mark.parametrize(
    "norm_id, expected",
    [
        ("et.art.689-3", False),
        ("et.art.689-3.par.2", True),
        ("ley.2277.2022.art.96", False),
        ("concepto.dian.100208192-202.num.20", True),
    ],
)
def test_is_sub_unit(norm_id: str, expected: bool):
    assert is_sub_unit(norm_id) is expected


@pytest.mark.parametrize(
    "norm_id, expected",
    [
        ("et.art.689-3.par.2", "parágrafo"),
        ("et.art.689-3.num.5", "numeral"),
        ("et.art.689-3.lit.b", "literal"),
        ("et.art.689-3", None),
    ],
)
def test_sub_unit_kind(norm_id: str, expected: str | None):
    assert sub_unit_kind(norm_id) == expected


@pytest.mark.parametrize(
    "norm_id, expected_type",
    [
        ("et", "estatuto"),
        ("et.art.689-3", "articulo_et"),
        ("et.art.689-3.par.2", "articulo_et"),
        ("ley.2277.2022", "ley"),
        ("ley.2277.2022.art.96", "ley_articulo"),
        ("decreto.1474.2025", "decreto"),
        ("decreto.1625.2016.art.1", "decreto_articulo"),
        ("res.dian.165.2023", "resolucion"),
        ("concepto.dian.100208192-202", "concepto_dian"),
        ("concepto.dian.100208192-202.num.20", "concepto_dian_numeral"),
        ("sent.cc.C-481.2019", "sentencia_cc"),
        ("sent.ce.28920.2025.07.03", "sentencia_ce"),
        ("auto.ce.28920.2024.12.16", "auto_ce"),
    ],
)
def test_norm_type_inference(norm_id: str, expected_type: str):
    assert norm_type(norm_id) == expected_type


def test_display_label_examples():
    assert display_label("et") == "Estatuto Tributario"
    assert "689-3" in display_label("et.art.689-3")
    assert "Ley 2277 de 2022" in display_label("ley.2277.2022")
    assert "Sentencia C-481.2019" == display_label("sent.cc.C-481.2019")


# ---------------------------------------------------------------------------
# find_mentions — corpus prose scanning
# ---------------------------------------------------------------------------


def test_find_mentions_finds_multiple():
    chunk = (
        "El Art. 689-3 ET fue modificado por la Ley 2277 de 2022. "
        "Posteriormente, la Sentencia C-481 de 2019 declaró inexequible la Ley 1943 de 2018. "
        "Ver también el Decreto 1474 de 2025 y el Concepto DIAN 100208192-202 numeral 20."
    )
    mentions = find_mentions(chunk)
    raw_texts = [m.text.lower() for m in mentions]
    assert any("689-3" in t and "et" in t for t in raw_texts)
    assert any("ley 2277" in t for t in raw_texts)
    assert any("sentencia c-481" in t for t in raw_texts)
    assert any("decreto 1474" in t for t in raw_texts)
    assert any("concepto" in t and "100208192" in t for t in raw_texts)


def test_find_mentions_returns_sorted_spans():
    chunk = "Ley 2277 de 2022 ... Decreto 1474 de 2025 ... Sentencia C-481 de 2019."
    mentions = find_mentions(chunk)
    starts = [m.span[0] for m in mentions]
    assert starts == sorted(starts)


# ---------------------------------------------------------------------------
# Known emisores registry
# ---------------------------------------------------------------------------


def test_known_emisores_includes_dian():
    assert "dian" in KNOWN_EMISORES
    assert "ugpp" in KNOWN_EMISORES
    assert "mintic" in KNOWN_EMISORES


# ---------------------------------------------------------------------------
# CST / CCo / DCIN / Oficio — new families added 2026-04-28 to unblock Phases E-K
# corpus population (§3 of corpus_population_brief_edits.md).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "mention, expected",
    [
        ("Art. 22 CST", "cst.art.22"),
        ("art 22 cst", "cst.art.22"),
        ("Artículo 158 del Código Sustantivo del Trabajo", "cst.art.158"),
        ("Código Sustantivo del Trabajo, art. 416", "cst.art.416"),
        ("CST Art. 416", "cst.art.416"),
        ("Art. 22 CST parágrafo 1", "cst.art.22.par.1"),
        ("Art. 22 CST literal a", "cst.art.22.lit.a"),
    ],
)
def test_cst_canonicalize(mention: str, expected: str):
    assert canonicalize(mention) == expected


@pytest.mark.parametrize(
    "mention, expected",
    [
        ("Art. 98 CCo", "cco.art.98"),
        ("Artículo 98 del Código de Comercio", "cco.art.98"),
        ("Código de Comercio, art. 515", "cco.art.515"),
        ("art. 98 c.co.", "cco.art.98"),
        ("Art. 98 CCo parágrafo 2", "cco.art.98.par.2"),
        ("Art. 98 CCo literal a", "cco.art.98.lit.a"),
    ],
)
def test_cco_canonicalize(mention: str, expected: str):
    assert canonicalize(mention) == expected


@pytest.mark.parametrize(
    "mention, expected",
    [
        ("DCIN-83 capítulo 5 numeral 3", "dcin.83.cap.5.num.3"),
        ("DCIN 83 cap. 5 num. 3", "dcin.83.cap.5.num.3"),
        ("dcin-83 capitulo 1 numeral 2", "dcin.83.cap.1.num.2"),
        ("DCIN-83 cap 1 num 1", "dcin.83.cap.1.num.1"),
    ],
)
def test_dcin_canonicalize(mention: str, expected: str):
    assert canonicalize(mention) == expected


def test_dcin_requires_both_cap_and_num():
    # DCIN without both cap+num is ambiguous; must refuse.
    assert canonicalize("DCIN-83") is None
    assert canonicalize("DCIN-83 capítulo 5") is None
    assert canonicalize("DCIN-83 numeral 3") is None


@pytest.mark.parametrize(
    "mention, expected",
    [
        ("Oficio DIAN 018424 de 2024", "oficio.dian.018424.2024"),
        ("Oficio DIAN Nº 908128 del 2021", "oficio.dian.908128.2021"),
        ("oficio dian 12345 de 2020", "oficio.dian.12345.2020"),
        ("Oficio DIAN N° 12345-1 del 2024", "oficio.dian.12345-1.2024"),
    ],
)
def test_oficio_canonicalize(mention: str, expected: str):
    assert canonicalize(mention) == expected


def test_oficio_without_year_falls_to_concepto():
    """Backward-compat: a no-year 'Oficio DIAN 12345' falls through to _rule_concepto
    (legacy permissive form). The oficio family proper requires a year."""
    assert canonicalize("Oficio DIAN 12345") == "concepto.dian.12345"


def test_concepto_with_year_is_still_concepto_not_oficio():
    """A 'Concepto' keyword always emits concepto.dian.<NUM> — year is metadata only."""
    assert canonicalize("Concepto DIAN 100208192-202") == "concepto.dian.100208192-202"


# Round-trip: every new canonical id must canonicalize to itself
@pytest.mark.parametrize(
    "norm_id",
    [
        "cst.art.22",
        "cst.art.158",
        "cst.art.22.par.1",
        "cst.art.22.lit.a",
        "cco.art.98",
        "cco.art.515",
        "cco.art.98.par.2",
        "dcin.83.cap.5.num.3",
        "dcin.83.cap.1.num.2",
        "oficio.dian.018424.2024",
        "oficio.dian.908128.2021",
        "oficio.dian.12345-1.2024",
    ],
)
def test_new_families_round_trip(norm_id: str):
    assert canonicalize(norm_id) == norm_id
    assert is_valid_norm_id(norm_id)


# norm_type for new families
@pytest.mark.parametrize(
    "norm_id, expected_type",
    [
        ("cst.art.22", "cst_articulo"),
        ("cst.art.158.par.1", "cst_articulo"),
        ("cco.art.98", "cco_articulo"),
        ("cco.art.98.lit.a", "cco_articulo"),
        ("dcin.83.cap.5.num.3", "dcin_numeral"),
        ("oficio.dian.018424.2024", "oficio_dian"),
    ],
)
def test_new_families_norm_type(norm_id: str, expected_type: str):
    assert norm_type(norm_id) == expected_type


# display_label for new families
def test_new_families_display_label():
    assert display_label("cst.art.22") == "Art. 22 CST"
    assert display_label("cco.art.98") == "Art. 98 CCo"
    assert display_label("dcin.83.cap.5.num.3") == "DCIN-83 capítulo 5 numeral 3"
    assert display_label("oficio.dian.018424.2024") == "Oficio DIAN 018424 de 2024"


# find_mentions picks up the new families in real prose
def test_find_mentions_picks_up_cst_cco_dcin_oficio():
    chunk = (
        "El Art. 22 CST regula el contrato de trabajo. "
        "El Art. 98 del Código de Comercio aplica a sociedades. "
        "DCIN-83 capítulo 5 numeral 3 establece el procedimiento. "
        "Ver Oficio DIAN 018424 de 2024."
    )
    mentions = find_mentions(chunk)
    raw_texts = [m.text.lower() for m in mentions]
    assert any("art. 22" in t and "cst" in t for t in raw_texts)
    assert any("art. 98" in t.replace(" ", "") or ("art" in t and "98" in t and "comercio" in t) for t in raw_texts)
    assert any("dcin" in t and "5" in t and "3" in t for t in raw_texts)
    assert any("oficio" in t and "018424" in t for t in raw_texts)
