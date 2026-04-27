"""Unit tests for the v3 Vigencia ontology — fixplan_v3 §0.4 + §0.11.3.

Sub-fix 1A H0 tests. These run as soon as `src/lia_graph/vigencia.py` lands,
no DB or scraper dependency.
"""

from __future__ import annotations

import json
from datetime import date

import pytest

from lia_graph.vigencia import (
    AppliesToPayload,
    CanonicalizerRefusal,
    ChangeSource,
    ChangeSourceType,
    Citation,
    DEFAULT_DEMOTION,
    ExtractionAudit,
    InterpretiveConstraint,
    Vigencia,
    VigenciaResult,
    VigenciaState,
    map_v2_state,
)


# ---------------------------------------------------------------------------
# Enum coverage
# ---------------------------------------------------------------------------


def test_eleven_states_present():
    expected = {"V", "VM", "DE", "DT", "SP", "IE", "EC", "VC", "VL", "DI", "RV"}
    assert {s.value for s in VigenciaState} == expected


def test_default_demotion_covers_every_state():
    for state in VigenciaState:
        assert state in DEFAULT_DEMOTION
    # blocking states are 0.0
    for state in (VigenciaState.DE, VigenciaState.SP, VigenciaState.IE, VigenciaState.VL):
        assert DEFAULT_DEMOTION[state] == 0.0
    # DT is the contested 0.3
    assert DEFAULT_DEMOTION[VigenciaState.DT] == 0.3


# ---------------------------------------------------------------------------
# Construction & validation
# ---------------------------------------------------------------------------


def _v_min(state: VigenciaState, **overrides) -> Vigencia:
    """Minimal valid Vigencia for a given state, for round-trip tests."""

    state_from = overrides.pop("state_from", date(2023, 1, 1))
    interpretive_constraint = None
    rige_desde = None
    revives_text_version = None
    change_source: ChangeSource | None = None

    if state == VigenciaState.V:
        change_source = None
    elif state == VigenciaState.VM:
        change_source = ChangeSource(
            type=ChangeSourceType.REFORMA,
            source_norm_id="ley.2277.2022.art.10",
            effect_type="pro_futuro",
            effect_payload={},
        )
    elif state == VigenciaState.DE:
        change_source = ChangeSource(
            type=ChangeSourceType.DEROGACION_EXPRESA,
            source_norm_id="ley.2277.2022.art.96",
            effect_type="pro_futuro",
            effect_payload={"fecha_efectos": "2023-01-01"},
        )
    elif state == VigenciaState.DT:
        change_source = ChangeSource(
            type=ChangeSourceType.DEROGACION_TACITA,
            source_norm_id="ley.962.2005.art.43",
            effect_type="pro_futuro",
            effect_payload={"contested": True},
        )
    elif state == VigenciaState.SP:
        change_source = ChangeSource(
            type=ChangeSourceType.AUTO_CE_SUSPENSION,
            source_norm_id="auto.ce.28920.2024.12.16",
            effect_type="pro_futuro",
            effect_payload={"autoridad": "CE Sección Cuarta", "alcance": "numeral 20"},
        )
    elif state == VigenciaState.IE:
        change_source = ChangeSource(
            type=ChangeSourceType.SENTENCIA_CC,
            source_norm_id="sent.cc.C-079.2026",
            effect_type="pro_futuro",
            effect_payload={"fecha_sentencia": "2026-04-15"},
        )
    elif state == VigenciaState.EC:
        change_source = ChangeSource(
            type=ChangeSourceType.SENTENCIA_CC,
            source_norm_id="sent.cc.C-384.2023",
            effect_type="pro_futuro",
            effect_payload={"condicionamiento_literal": "EXEQUIBLE en el entendido que..."},
        )
        interpretive_constraint = InterpretiveConstraint(
            sentencia_norm_id="sent.cc.C-384.2023",
            fecha_sentencia=date(2023, 10, 2),
            texto_literal="EXEQUIBLE en el entendido que el régimen tarifario...",
            fuente_verificada_directo=True,
        )
    elif state == VigenciaState.VC:
        change_source = ChangeSource(
            type=ChangeSourceType.MODULACION_DOCTRINARIA,
            source_norm_id="concepto.dian.999",
            effect_type="pro_futuro",
            effect_payload={"fuente": "doctrina_dian", "interpretive_constraint": "limita..."},
        )
        interpretive_constraint = InterpretiveConstraint(
            sentencia_norm_id="concepto.dian.999",
            fecha_sentencia=date(2024, 1, 1),
            texto_literal="limita el alcance a casos X.",
            fuente_verificada_directo=False,
        )
    elif state == VigenciaState.VL:
        change_source = ChangeSource(
            type=ChangeSourceType.VACATIO,
            source_norm_id="ley.9999.2026",
            effect_type="pro_futuro",
            effect_payload={"rige_desde": "2027-01-01"},
        )
        rige_desde = date(2027, 1, 1)
        state_from = date(2026, 8, 1)
    elif state == VigenciaState.DI:
        change_source = ChangeSource(
            type=ChangeSourceType.SENTENCIA_CC,
            source_norm_id="sent.cc.C-100.2025",
            effect_type="diferido",
            effect_payload={"plazo_diferido": "2026-12-31"},
        )
        rige_desde = date(2026, 12, 31)
    elif state == VigenciaState.RV:
        change_source = ChangeSource(
            type=ChangeSourceType.REVIVISCENCIA,
            source_norm_id="ley.1943.2018",
            effect_type="pro_futuro",
            effect_payload={
                "triggering_sentencia_norm_id": "sent.cc.C-481.2019",
                "revives_text_version": "redacción anterior a Ley 1943/2018",
            },
        )
        revives_text_version = "redacción anterior a Ley 1943/2018"

    return Vigencia(
        state=state,
        state_from=state_from,
        state_until=overrides.get("state_until"),
        applies_to_kind=overrides.get("applies_to_kind", "always"),
        applies_to_payload=overrides.get("applies_to_payload", AppliesToPayload()),
        change_source=overrides.get("change_source", change_source),
        interpretive_constraint=overrides.get("interpretive_constraint", interpretive_constraint),
        rige_desde=overrides.get("rige_desde", rige_desde),
        revives_text_version=overrides.get("revives_text_version", revives_text_version),
    )


@pytest.mark.parametrize("state", list(VigenciaState))
def test_minimal_vigencia_constructs_for_every_state(state: VigenciaState):
    v = _v_min(state)
    assert v.state == state


@pytest.mark.parametrize("state", [VigenciaState.EC, VigenciaState.VC])
def test_ec_vc_require_interpretive_constraint(state: VigenciaState):
    cs = (
        ChangeSource(
            type=ChangeSourceType.SENTENCIA_CC,
            source_norm_id="sent.cc.C-384.2023",
            effect_type="pro_futuro",
            effect_payload={},
        )
        if state == VigenciaState.EC
        else ChangeSource(
            type=ChangeSourceType.MODULACION_DOCTRINARIA,
            source_norm_id="concepto.dian.999",
            effect_type="pro_futuro",
            effect_payload={},
        )
    )
    with pytest.raises(ValueError, match="interpretive_constraint"):
        Vigencia(
            state=state,
            state_from=date(2023, 1, 1),
            state_until=None,
            applies_to_kind="always",
            applies_to_payload=AppliesToPayload(),
            change_source=cs,
            interpretive_constraint=None,
        )


@pytest.mark.parametrize("state", [VigenciaState.VL, VigenciaState.DI])
def test_vl_di_require_rige_desde(state: VigenciaState):
    cs = (
        ChangeSource(
            type=ChangeSourceType.VACATIO,
            source_norm_id="ley.9999.2026",
            effect_type="pro_futuro",
            effect_payload={},
        )
        if state == VigenciaState.VL
        else ChangeSource(
            type=ChangeSourceType.SENTENCIA_CC,
            source_norm_id="sent.cc.C-100.2025",
            effect_type="diferido",
            effect_payload={},
        )
    )
    with pytest.raises(ValueError, match="rige_desde"):
        Vigencia(
            state=state,
            state_from=date(2026, 8, 1),
            state_until=None,
            applies_to_kind="always",
            applies_to_payload=AppliesToPayload(),
            change_source=cs,
        )


def test_rv_requires_revives_text_version():
    cs = ChangeSource(
        type=ChangeSourceType.REVIVISCENCIA,
        source_norm_id="ley.1943.2018",
        effect_type="pro_futuro",
        effect_payload={},
    )
    with pytest.raises(ValueError, match="revives_text_version"):
        Vigencia(
            state=VigenciaState.RV,
            state_from=date(2019, 10, 1),
            state_until=None,
            applies_to_kind="always",
            applies_to_payload=AppliesToPayload(),
            change_source=cs,
        )


def test_state_until_must_be_after_state_from():
    cs = ChangeSource(
        type=ChangeSourceType.REFORMA,
        source_norm_id="ley.2277.2022",
        effect_type="pro_futuro",
        effect_payload={},
    )
    with pytest.raises(ValueError, match="state_until"):
        Vigencia(
            state=VigenciaState.VM,
            state_from=date(2024, 1, 1),
            state_until=date(2023, 1, 1),
            applies_to_kind="always",
            applies_to_payload=AppliesToPayload(),
            change_source=cs,
        )


def test_non_v_state_requires_change_source():
    with pytest.raises(ValueError, match="change_source"):
        Vigencia(
            state=VigenciaState.VM,
            state_from=date(2023, 1, 1),
            state_until=None,
            applies_to_kind="always",
            applies_to_payload=AppliesToPayload(),
            change_source=None,
        )


def test_v_state_allows_no_change_source():
    v = Vigencia(
        state=VigenciaState.V,
        state_from=date(2017, 1, 1),
        state_until=None,
        applies_to_kind="always",
        applies_to_payload=AppliesToPayload(),
        change_source=None,
    )
    assert v.state == VigenciaState.V


def test_change_source_state_compatibility_rejected():
    cs = ChangeSource(
        type=ChangeSourceType.DEROGACION_EXPRESA,
        source_norm_id="ley.2277.2022.art.96",
        effect_type="pro_futuro",
        effect_payload={},
    )
    with pytest.raises(ValueError, match="not compatible"):
        Vigencia(
            state=VigenciaState.VM,
            state_from=date(2023, 1, 1),
            state_until=None,
            applies_to_kind="always",
            applies_to_payload=AppliesToPayload(),
            change_source=cs,
        )


# ---------------------------------------------------------------------------
# Round-trip serialization
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("state", list(VigenciaState))
def test_round_trip_to_dict_from_dict(state: VigenciaState):
    v = _v_min(state)
    blob = v.to_dict()
    v2 = Vigencia.from_dict(blob)
    assert v2.state == v.state
    assert v2.state_from == v.state_from
    assert v2.applies_to_kind == v.applies_to_kind
    if v.change_source:
        assert v2.change_source is not None
        assert v2.change_source.type == v.change_source.type
        assert v2.change_source.source_norm_id == v.change_source.source_norm_id


@pytest.mark.parametrize("state", list(VigenciaState))
def test_round_trip_via_json(state: VigenciaState):
    v = _v_min(state)
    text = v.to_json()
    decoded = json.loads(text)
    rebuilt = Vigencia.from_dict(decoded)
    assert rebuilt.state == v.state


# ---------------------------------------------------------------------------
# Resolver helper methods
# ---------------------------------------------------------------------------


def test_applies_to_date_window_inclusive_start_exclusive_end():
    v = _v_min(VigenciaState.VM, state_from=date(2023, 1, 1), state_until=date(2024, 1, 1))
    assert v.applies_to_date(date(2023, 1, 1)) is True
    assert v.applies_to_date(date(2023, 6, 15)) is True
    assert v.applies_to_date(date(2024, 1, 1)) is False
    assert v.applies_to_date(date(2022, 12, 31)) is False


def test_applies_to_period_per_period_filters_by_impuesto():
    v = _v_min(
        VigenciaState.VM,
        applies_to_kind="per_period",
        applies_to_payload=AppliesToPayload(
            impuesto="renta",
            period_start=date(2023, 1, 1),
            period_end=None,
            art_338_cp_shift=True,
        ),
    )
    assert v.applies_to_period("renta", 2023) is True
    assert v.applies_to_period("renta", 2022) is False
    assert v.applies_to_period("iva", 2023) is False


def test_applies_to_period_per_year():
    v = _v_min(
        VigenciaState.VM,
        applies_to_kind="per_year",
        applies_to_payload=AppliesToPayload(year_start=2023, year_end=None),
    )
    assert v.applies_to_period("renta", 2023) is True
    assert v.applies_to_period("renta", 2022) is False


def test_demotion_factor_returns_default():
    v = _v_min(VigenciaState.DE)
    assert v.demotion_factor() == 0.0
    v2 = _v_min(VigenciaState.V)
    assert v2.demotion_factor() == 1.0


# ---------------------------------------------------------------------------
# VigenciaResult discriminated shape
# ---------------------------------------------------------------------------


def test_vigencia_result_with_veredicto():
    v = _v_min(VigenciaState.V)
    res = VigenciaResult(veredicto=v)
    assert res.veredicto is v
    assert res.refusal_reason is None


def test_vigencia_result_refusal_requires_reason():
    with pytest.raises(ValueError, match="refusal_reason"):
        VigenciaResult(veredicto=None, refusal_reason=None)


def test_vigencia_result_refusal_payload():
    res = VigenciaResult(
        veredicto=None,
        refusal_reason="missing_primary_sources",
        canonicalizer_refusals=(
            CanonicalizerRefusal(mention="Decreto 1474", reason="missing_year"),
        ),
    )
    blob = res.to_dict()
    assert blob["veredicto"] is None
    assert blob["refusal_reason"] == "missing_primary_sources"
    assert blob["canonicalizer_refusals"][0]["reason"] == "missing_year"


def test_vigencia_result_with_veredicto_and_refusal_rejected():
    v = _v_min(VigenciaState.V)
    with pytest.raises(ValueError):
        VigenciaResult(veredicto=v, refusal_reason="some reason")


# ---------------------------------------------------------------------------
# v2 → v3 mapper
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "label, expected",
    [
        ("vigente", VigenciaState.V),
        ("V", VigenciaState.V),
        ("VM", VigenciaState.VM),
        ("derogada", VigenciaState.DE),
        ("DE", VigenciaState.DE),
        ("derogada_tacita", VigenciaState.DT),
        ("suspendida", VigenciaState.SP),
        ("inexequible", VigenciaState.IE),
        ("exequibilidad_condicionada", VigenciaState.EC),
        ("EC", VigenciaState.EC),
    ],
)
def test_map_v2_state_known_labels(label: str, expected: VigenciaState):
    assert map_v2_state(label) == expected


def test_map_v2_state_unknown_raises():
    with pytest.raises(ValueError):
        map_v2_state("totalmente_inventada")


# ---------------------------------------------------------------------------
# Citation + InterpretiveConstraint round-trip
# ---------------------------------------------------------------------------


def test_citation_round_trip():
    c = Citation(
        norm_id="ley.2277.2022.art.96",
        norm_type="ley_articulo",
        article="96",
        fecha=date(2022, 12, 13),
        primary_source_url="https://senado.gov.co/...",
    )
    rebuilt = Citation.from_dict(c.to_dict())
    assert rebuilt == c


def test_interpretive_constraint_round_trip():
    ic = InterpretiveConstraint(
        sentencia_norm_id="sent.cc.C-384.2023",
        fecha_sentencia=date(2023, 10, 2),
        texto_literal="EXEQUIBLES, en el entendido que...",
        fuente_verificada_directo=True,
    )
    rebuilt = InterpretiveConstraint.from_dict(ic.to_dict())
    assert rebuilt == ic


# ---------------------------------------------------------------------------
# ExtractionAudit round-trip
# ---------------------------------------------------------------------------


def test_extraction_audit_round_trip():
    a = ExtractionAudit(
        skill_version="vigencia-checker@2.0",
        model="gemini-2.5-pro",
        tool_iterations=5,
        wall_ms=360000,
        cost_usd_estimate=0.062,
        run_id="20260501T120000Z",
        method="skill",
    )
    rebuilt = ExtractionAudit.from_dict(a.to_dict())
    assert rebuilt == a
