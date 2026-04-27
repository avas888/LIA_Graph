"""H0 tests for the vigencia extractor harness — sub-fix 1B-β.

Uses a fake adapter (no live Gemini call) and a fake scraper registry that
returns canned ScraperFetchResults. Production runs require LIA_GEMINI_API_KEY.
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


def test_no_api_key_returns_refusal_when_no_adapter_factory():
    """Production safety: harness must not blow up without an API key."""

    import os
    saved = os.environ.pop("LIA_GEMINI_API_KEY", None)
    try:
        harness = VigenciaSkillHarness(
            scrapers=_registry_with(_result("a"), _result("b")),
        )
        result = harness.verify_norm(norm_id="et.art.689-3")
        assert result.veredicto is None
        assert "missing_LIA_GEMINI_API_KEY" in (result.refusal_reason or "")
    finally:
        if saved is not None:
            os.environ["LIA_GEMINI_API_KEY"] = saved
