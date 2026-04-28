"""H0 tests for the vigencia extractor harness — sub-fix 1B-β.

Uses a fake adapter (no live Gemini call) and a fake scraper registry that
returns canned ScraperFetchResults. Production runs require GEMINI_API_KEY
(legacy alias `LIA_GEMINI_API_KEY` still honored as a fallback).
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, Sequence

import pytest

from lia_graph.scrapers.base import ScraperFetchResult, ScraperRegistry
from lia_graph.vigencia import Vigencia, VigenciaState
from lia_graph.vigencia_extractor import (
    PeriodoFiscal,
    VigenciaSkillHarness,
)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class _FakeScraper:
    def __init__(self, source_id: str, *, returns: ScraperFetchResult | None) -> None:
        self.source_id = source_id
        self._returns = returns

    def handles(self, norm_type_value: str, norm_id: str) -> bool:
        return True

    def fetch(self, norm_id: str) -> ScraperFetchResult | None:
        return self._returns


def _registry_with(*results: ScraperFetchResult | None) -> ScraperRegistry:
    return ScraperRegistry(
        [_FakeScraper(f"fake-{i}", returns=r) for i, r in enumerate(results)]
    )


def _result(source: str = "fake-1", text: str = "Art. 689-3 ET ...") -> ScraperFetchResult:
    return ScraperFetchResult(
        norm_id="et.art.689-3",
        source=source,
        url=f"https://example.com/{source}",
        fetched_at_utc="2026-04-27T00:00:00Z",
        status_code=200,
        parsed_text=text,
        parsed_meta={},
        cache_hit=True,
    )


class _FakeAdapter:
    """Returns a canned skill output."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def generate(self, prompt: str) -> str:
        return json.dumps(self._payload, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_invalid_norm_id_returns_refusal():
    harness = VigenciaSkillHarness(scrapers=_registry_with())
    result = harness.verify_norm(norm_id="not a canonical id")
    assert result.veredicto is None
    assert "invalid_norm_id" in (result.refusal_reason or "")


def test_missing_double_primary_source_refusal():
    harness = VigenciaSkillHarness(scrapers=_registry_with(_result()))
    result = harness.verify_norm(norm_id="et.art.689-3")
    assert result.veredicto is None
    assert result.refusal_reason == "missing_double_primary_source"


def test_skill_emits_v_state(tmp_path: Path):
    payload = {
        "state": "V",
        "state_from": "2017-01-01",
        "state_until": None,
        "applies_to_kind": "always",
        "applies_to_payload": {},
        "change_source": None,
    }
    harness = VigenciaSkillHarness(
        scrapers=_registry_with(_result("a"), _result("b")),
        adapter_factory=lambda: _FakeAdapter(payload),
    )
    result = harness.verify_norm(norm_id="et.art.290.num.5")
    assert result.veredicto is not None
    assert result.veredicto.state == VigenciaState.V


def test_skill_emits_de_state(tmp_path: Path):
    payload = {
        "state": "DE",
        "state_from": "2023-01-01",
        "state_until": None,
        "applies_to_kind": "always",
        "applies_to_payload": {},
        "change_source": {
            "type": "derogacion_expresa",
            "source_norm_id": "ley.2277.2022.art.96",
            "effect_type": "pro_futuro",
            "effect_payload": {"fecha_efectos": "2023-01-01"},
        },
    }
    harness = VigenciaSkillHarness(
        scrapers=_registry_with(_result("a"), _result("b")),
        adapter_factory=lambda: _FakeAdapter(payload),
    )
    result = harness.verify_norm(norm_id="et.art.158-1")
    assert result.veredicto is not None
    assert result.veredicto.state == VigenciaState.DE
    assert result.veredicto.change_source is not None
    assert result.veredicto.change_source.source_norm_id == "ley.2277.2022.art.96"


def test_skill_returns_refusal_payload():
    payload = {
        "refusal_reason": "primary sources contradict",
        "missing_sources": [],
    }
    harness = VigenciaSkillHarness(
        scrapers=_registry_with(_result("a"), _result("b")),
        adapter_factory=lambda: _FakeAdapter(payload),
    )
    result = harness.verify_norm(norm_id="et.art.689-3")
    assert result.veredicto is None
    assert "contradict" in (result.refusal_reason or "")


def test_skill_handles_invalid_json():
    class _BadAdapter:
        def generate(self, prompt: str) -> str:
            return "not actually json {"

    harness = VigenciaSkillHarness(
        scrapers=_registry_with(_result("a"), _result("b")),
        adapter_factory=lambda: _BadAdapter(),
    )
    result = harness.verify_norm(norm_id="et.art.689-3")
    assert result.veredicto is None
    assert "non_json_skill_output" in (result.refusal_reason or "")


def test_write_result_persists_v3_shape(tmp_path: Path):
    payload = {
        "state": "V",
        "state_from": "2017-01-01",
        "state_until": None,
        "applies_to_kind": "always",
        "applies_to_payload": {},
        "change_source": None,
    }
    harness = VigenciaSkillHarness(
        scrapers=_registry_with(_result("a"), _result("b")),
        adapter_factory=lambda: _FakeAdapter(payload),
    )
    result = harness.verify_norm(norm_id="et.art.290.num.5")
    out_path = harness.write_result(result, norm_id="et.art.290.num.5", output_dir=tmp_path)
    assert out_path.exists()
    blob = json.loads(out_path.read_text())
    assert blob["norm_id"] == "et.art.290.num.5"
    assert blob["norm_type"] == "articulo_et"
    assert blob["is_sub_unit"] is True
    assert blob["sub_unit_kind"] == "numeral"
    assert blob["result"]["veredicto"]["state"] == "V"


def _senado_result(text: str, *, norm_id: str = "ley.789.2002") -> ScraperFetchResult:
    """fixplan_v5 #1 Approach B fixture: Senado-shaped fetch result."""

    return ScraperFetchResult(
        norm_id=norm_id,
        source="secretaria_senado",
        url=f"https://www.secretariasenado.gov.co/senado/basedoc/{norm_id}.html",
        fetched_at_utc="2026-04-28T00:00:00Z",
        status_code=200,
        parsed_text=text,
        parsed_meta={},
        cache_hit=True,
    )


def test_single_source_senado_ley_accepted_when_law_num_in_body():
    """Approach B: one Senado hit (with law NUM in body) + DIAN miss → LLM runs."""

    payload = {
        "state": "V",
        "state_from": "2002-12-27",
        "state_until": None,
        "applies_to_kind": "always",
        "applies_to_payload": {},
        "change_source": None,
    }
    senado = _senado_result(
        "Ley 789 de 2002 — por la cual se dictan normas para apoyar el empleo …",
        norm_id="ley.789.2002",
    )
    harness = VigenciaSkillHarness(
        scrapers=_registry_with(senado, None),  # DIAN 404 → None
        adapter_factory=lambda: _FakeAdapter(payload),
    )
    result = harness.verify_norm(norm_id="ley.789.2002")
    assert result.veredicto is not None, result.refusal_reason
    assert result.refusal_reason is None
    assert result.single_source_accepted == "secretaria_senado"
    # Diagnostic survives serialization
    assert result.to_dict()["single_source_accepted"] == "secretaria_senado"


def test_single_source_senado_ley_articulo_requires_article_number_in_body():
    """Approach B: ley.NNN.YYYY.art.MMM requires the article MMM in the body."""

    payload = {
        "state": "VM",
        "state_from": "2003-01-29",
        "state_until": None,
        "applies_to_kind": "always",
        "applies_to_payload": {},
        "change_source": {
            "type": "reforma",
            "source_norm_id": "ley.797.2003.art.9",
            "effect_type": "pro_futuro",
            "effect_payload": {"fecha": "2003-01-29"},
        },
    }
    senado = _senado_result(
        "Artículo 9°. Modifíquese el artículo 33 de la Ley 100 de 1993 …",
        norm_id="ley.797.2003.art.9",
    )
    harness = VigenciaSkillHarness(
        scrapers=_registry_with(senado, None),
        adapter_factory=lambda: _FakeAdapter(payload),
    )
    result = harness.verify_norm(norm_id="ley.797.2003.art.9")
    assert result.veredicto is not None, result.refusal_reason
    assert result.single_source_accepted == "secretaria_senado"


def test_single_source_senado_refused_when_article_number_missing():
    """If MMM is not in the body, refusal must still fire — narrow rule."""

    senado = _senado_result(
        "Artículo 1°. Disposiciones generales …",  # no '9' anywhere
        norm_id="ley.797.2003.art.9",
    )
    harness = VigenciaSkillHarness(
        scrapers=_registry_with(senado, None),
    )
    result = harness.verify_norm(norm_id="ley.797.2003.art.9")
    assert result.veredicto is None
    assert result.refusal_reason == "missing_double_primary_source"
    assert result.single_source_accepted is None


def test_trusted_govco_source_ids_includes_suin():
    """fixplan_v6 §3 step 3 — SUIN-Juriscol joins the trusted .gov.co set."""

    from lia_graph.vigencia_extractor import _TRUSTED_GOVCO_SOURCE_IDS

    assert "suin_juriscol" in _TRUSTED_GOVCO_SOURCE_IDS
    assert "secretaria_senado" in _TRUSTED_GOVCO_SOURCE_IDS
    assert "dian_normograma" in _TRUSTED_GOVCO_SOURCE_IDS


def test_single_source_suin_decreto_articulo_accepted():
    """fixplan_v6 §3 step 3 — SUIN-only veredictos accepted when the body
    references the DUR article (e.g. 1.6.1.1.10 from a sliced SUIN page)."""

    suin_only = ScraperFetchResult(
        norm_id="decreto.1625.2016.art.1.6.1.1.10",
        source="suin_juriscol",
        url="https://www.suin-juriscol.gov.co/viewDocument.asp?id=30030361",
        fetched_at_utc="2026-04-28T00:00:00Z",
        status_code=200,
        parsed_text=(
            "Artículo 1.6.1.1.10. Libros de contabilidad de las "
            "organizaciones sindicales. ... (sliced article body)"
        ),
        parsed_meta={"sliced_to_article": "1.6.1.1.10", "suin_doc_id": "30030361"},
        cache_hit=True,
    )
    harness = VigenciaSkillHarness(
        scrapers=_registry_with(suin_only, None),
        adapter_factory=lambda: _FakeAdapter(
            {
                "state": "V",
                "state_from": "2016-10-11",
                "applies_to_kind": "always",
                "fuentes_primarias_consultadas": [
                    {"norm_id": "suin", "norm_type": "url", "url": suin_only.url}
                ],
            }
        ),
    )
    result = harness.verify_norm(norm_id="decreto.1625.2016.art.1.6.1.1.10")
    assert result.veredicto is not None, result.refusal_reason
    assert result.single_source_accepted == "suin_juriscol"


def test_single_source_non_senado_still_refused():
    """The relaxation is Senado-only — DIAN-only must still refuse."""

    dian_only = ScraperFetchResult(
        norm_id="et.art.689-3",
        source="dian_normograma",
        url="https://normograma.dian.gov.co/dian/docs/estatuto_tributario.html#art_689-3",
        fetched_at_utc="2026-04-28T00:00:00Z",
        status_code=200,
        parsed_text="Artículo 689-3. Beneficio de auditoría …",
        parsed_meta={},
        cache_hit=True,
    )
    harness = VigenciaSkillHarness(
        scrapers=_registry_with(dian_only, None),
    )
    result = harness.verify_norm(norm_id="et.art.689-3")
    assert result.veredicto is None
    assert result.refusal_reason == "missing_double_primary_source"


def test_no_api_key_returns_refusal_when_no_adapter_factory():
    """Production safety: harness must not blow up without an API key."""

    import os
    saved_canonical = os.environ.pop("GEMINI_API_KEY", None)
    saved_legacy = os.environ.pop("LIA_GEMINI_API_KEY", None)
    try:
        harness = VigenciaSkillHarness(
            scrapers=_registry_with(_result("a"), _result("b")),
        )
        result = harness.verify_norm(norm_id="et.art.689-3")
        assert result.veredicto is None
        assert "missing_GEMINI_API_KEY" in (result.refusal_reason or "")
    finally:
        if saved_canonical is not None:
            os.environ["GEMINI_API_KEY"] = saved_canonical
        if saved_legacy is not None:
            os.environ["LIA_GEMINI_API_KEY"] = saved_legacy
