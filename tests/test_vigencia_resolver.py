"""Tests for the v3 vigencia resolver — fixplan_v3 sub-fix 1B-ε §0.6."""

from __future__ import annotations

from datetime import date

import pytest

from lia_graph.pipeline_d.contracts import (
    EvidenceBundleShape,
    GraphRetrievalPlan,
    PlannerEntryPoint,
    TraversalBudget,
)
from lia_graph.pipeline_d.vigencia_resolver import (
    PlannerVigenciaCue,
    ResolverQuery,
    ResolverRow,
    VigenciaResolver,
    extract_vigencia_cue,
)


# ---------------------------------------------------------------------------
# Cue extraction
# ---------------------------------------------------------------------------


def test_extract_vigencia_cue_for_period_renta():
    cue = extract_vigencia_cue("¿aplicaba Art. 240 ET en AG 2022 para renta?")
    assert cue.kind == "for_period"
    assert cue.payload["impuesto"] == "renta"
    assert cue.payload["periodo_year"] == 2022


def test_extract_vigencia_cue_for_period_iva():
    cue = extract_vigencia_cue("¿qué tarifa de IVA aplicaba en periodo 2024?")
    assert cue.kind == "for_period"
    assert cue.payload["impuesto"] == "iva"
    assert cue.payload["periodo_year"] == 2024


def test_extract_vigencia_cue_at_date():
    cue = extract_vigencia_cue("¿qué decía Art. 689-3 ET en 2018?")
    assert cue.kind == "at_date"
    assert cue.payload["as_of_date"] == "2018-12-31"


def test_extract_vigencia_cue_default_none():
    cue = extract_vigencia_cue("¿cómo deduzco compras de un proveedor del régimen simple?")
    assert cue.kind is None


# ---------------------------------------------------------------------------
# ResolverQuery.from_plan
# ---------------------------------------------------------------------------


def _bare_plan(
    *,
    vigencia_query_kind=None,
    vigencia_query_payload=None,
) -> GraphRetrievalPlan:
    return GraphRetrievalPlan(
        query_mode="hybrid",
        entry_points=(),
        traversal_budget=TraversalBudget(
            max_hops=2,
            max_nodes=20,
            max_edges=40,
            max_paths=10,
            max_support_documents=5,
        ),
        evidence_bundle_shape=EvidenceBundleShape(
            primary_article_limit=10,
            connected_article_limit=5,
            related_reform_limit=5,
            support_document_limit=5,
        ),
        vigencia_query_kind=vigencia_query_kind,
        vigencia_query_payload=vigencia_query_payload,
    )


def test_resolver_query_defaults_to_at_date_today():
    plan = _bare_plan()
    q = ResolverQuery.from_plan(plan, default_today=date(2026, 4, 27))
    assert q.kind == "at_date"
    assert q.payload["as_of_date"] == "2026-04-27"


def test_resolver_query_for_period_passthrough():
    plan = _bare_plan(
        vigencia_query_kind="for_period",
        vigencia_query_payload={"impuesto": "renta", "periodo_year": 2022},
    )
    q = ResolverQuery.from_plan(plan)
    assert q.kind == "for_period"
    assert q.payload["impuesto"] == "renta"
    assert q.payload["periodo_year"] == 2022


# ---------------------------------------------------------------------------
# Resolver — fake-callable mode
# ---------------------------------------------------------------------------


def test_resolver_returns_demotion_factor():
    canned_rows = [
        {
            "norm_id": "et.art.158-1",
            "state": "DE",
            "state_from": "2023-01-01",
            "state_until": None,
            "record_id": "rec-1",
            "change_source": {"type": "derogacion_expresa", "source_norm_id": "ley.2277.2022.art.96"},
            "interpretive_constraint": None,
            "demotion_factor": 0.0,
        },
        {
            "norm_id": "et.art.689-3",
            "state": "VM",
            "state_from": "2023-01-01",
            "state_until": None,
            "record_id": "rec-2",
            "change_source": {"type": "reforma", "source_norm_id": "ley.2294.2023"},
            "interpretive_constraint": None,
            "demotion_factor": 1.0,
        },
    ]

    def at_date(payload):
        assert payload["as_of_date"] == "2026-04-27"
        return canned_rows

    resolver = VigenciaResolver(at_date_fn=at_date, for_period_fn=lambda p: [])
    plan = _bare_plan()
    q = ResolverQuery.from_plan(plan, default_today=date(2026, 4, 27))
    rows = resolver.resolve(q)
    assert {r.norm_id for r in rows} == {"et.art.158-1", "et.art.689-3"}
    assert resolver.demotion_factor_for("et.art.158-1", q) == 0.0
    assert resolver.demotion_factor_for("et.art.689-3", q) == 1.0
    # Unknown norm: default 1.0
    assert resolver.demotion_factor_for("ley.unknown.9999", q) == 1.0


def test_resolver_for_period_calls_correct_fn():
    seen = {}

    def at_date(payload):
        seen["at_date"] = payload
        return []

    def for_period(payload):
        seen["for_period"] = payload
        return [
            {
                "norm_id": "et.art.240",
                "state": "V",
                "state_from": "2017-01-01",
                "state_until": "2022-12-31",
                "record_id": "rec-3",
                "change_source": {"type": "inaugural", "source_norm_id": ""},
                "interpretive_constraint": None,
                "demotion_factor": 1.0,
                "norm_version_aplicable": "redacción anterior a Ley 2277/2022",
                "art_338_cp_applied": True,
            }
        ]

    resolver = VigenciaResolver(at_date_fn=at_date, for_period_fn=for_period)
    plan = _bare_plan(
        vigencia_query_kind="for_period",
        vigencia_query_payload={"impuesto": "renta", "periodo_year": 2022},
    )
    q = ResolverQuery.from_plan(plan)
    rows = resolver.resolve(q)
    assert "for_period" in seen
    assert "at_date" not in seen
    assert rows[0].art_338_cp_applied is True
    assert rows[0].norm_version_aplicable == "redacción anterior a Ley 2277/2022"


# ---------------------------------------------------------------------------
# ResolverRow round-trip
# ---------------------------------------------------------------------------


def test_resolver_row_from_row():
    row = ResolverRow.from_row(
        {
            "norm_id": "ley.2277.2022.art.11",
            "state": "EC",
            "state_from": "2023-10-02",
            "state_until": None,
            "record_id": "rec-4",
            "change_source": {"type": "sentencia_cc"},
            "interpretive_constraint": {"texto_literal": "EXEQUIBLE..."},
            "demotion_factor": 1.0,
        }
    )
    assert row.state == "EC"
    assert row.state_from == date(2023, 10, 2)
    assert row.demotion_factor == 1.0
