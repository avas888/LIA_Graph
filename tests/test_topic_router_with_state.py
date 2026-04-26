"""next_v4 §4 Level 2 — resolve_chat_topic prior-state behavior.

Covers the soft-prior tiebreaker added to ``resolve_chat_topic``:
- prior_topic surfaces as a hint in the LLM prompt
- when the LLM disagrees AND lexical scoring is empty, prior_topic wins
  with a confidence boost (capped to 0.85, mode="prior_state_tiebreaker")
- when lexical clearly points elsewhere, the LLM verdict / lexical match
  wins (no override — confirms the rule's narrowness)
- last-chance fallback when adapter is unreachable AND lexical empty AND
  no requested_topic AND prior_topic exists
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from lia_graph import topic_router
from lia_graph.topic_router import (
    TopicRoutingResult,
    _build_classifier_prompt,
    resolve_chat_topic,
)


# ── Prompt assembly ──────────────────────────────────────────────────────


def test_build_classifier_prompt_omits_prior_topic_line_when_state_absent() -> None:
    prompt = _build_classifier_prompt(
        message="¿hay límite anual?",
        requested_topic=None,
        pais="colombia",
        conversation_state=None,
    )
    assert "prior_topic" not in prompt


def test_build_classifier_prompt_includes_prior_topic_line_when_present() -> None:
    prompt = _build_classifier_prompt(
        message="¿hay límite anual?",
        requested_topic=None,
        pais="colombia",
        conversation_state={"prior_topic": "perdidas_fiscales_art147"},
    )
    assert "prior_topic (turno anterior): perdidas_fiscales_art147" in prompt
    assert "conserva prior_topic" in prompt


def test_build_classifier_prompt_ignores_unknown_prior_topic() -> None:
    """Unknown topic keys mustn't poison the prompt — the LLM would treat them
    as authoritative even though the rest of the system has no idea what to
    do with the resulting verdict. Filter to _SUPPORTED_TOPICS."""
    prompt = _build_classifier_prompt(
        message="¿hay límite anual?",
        requested_topic=None,
        pais="colombia",
        conversation_state={"prior_topic": "not_a_real_topic_key_xyz"},
    )
    assert "not_a_real_topic_key_xyz" not in prompt


# ── Tiebreaker behavior ──────────────────────────────────────────────────


def _stub_llm_classifier(
    monkeypatch: pytest.MonkeyPatch,
    *,
    return_topic: str | None,
    confidence: float,
    secondary_topics: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Replace _classify_topic_with_llm with a stub that returns a controlled
    TopicRoutingResult. Returns a dict the test can mutate to assert call
    args were threaded correctly (e.g., conversation_state)."""
    captured: dict[str, Any] = {}

    def _fake_classify(**kwargs: Any) -> TopicRoutingResult | None:
        captured.update(kwargs)
        if return_topic is None:
            return None
        return TopicRoutingResult(
            requested_topic=kwargs.get("requested_topic"),
            effective_topic=return_topic,
            secondary_topics=secondary_topics,
            topic_adjusted=True,
            confidence=confidence,
            reason="stub:llm",
            topic_notice=None,
            mode="llm",
            llm_runtime={"selected_provider": "stub"},
        )

    monkeypatch.setattr(topic_router, "_classify_topic_with_llm", _fake_classify)
    return captured


def test_tiebreaker_overrides_llm_when_lexical_empty_and_llm_disagrees(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """T2 = "¿hay alguna manera de ajustar?" — short, no lexical hits,
    LLM picks something different from prior_topic. Tiebreaker wins."""
    captured = _stub_llm_classifier(
        monkeypatch,
        return_topic="descuentos_tributarios_renta",
        confidence=0.55,
    )
    fake_runtime_path = tmp_path / "runtime.json"
    fake_runtime_path.write_text("{}", encoding="utf-8")

    result = resolve_chat_topic(
        message="¿hay alguna manera de ajustar?",
        requested_topic=None,
        runtime_config_path=fake_runtime_path,
        conversation_state={"prior_topic": "perdidas_fiscales_art147"},
    )
    assert result.effective_topic == "perdidas_fiscales_art147"
    assert result.mode == "prior_state_tiebreaker"
    assert result.reason == "tiebreaker:prior_topic_from_conversation_state"
    # Confidence boosted but capped at 0.85.
    assert 0.85 >= result.confidence > 0.55
    # conversation_state was threaded into the LLM call (defense-in-depth —
    # the LLM also sees prior_topic in its prompt).
    assert captured.get("conversation_state") == {"prior_topic": "perdidas_fiscales_art147"}


def test_tiebreaker_does_not_fire_when_llm_agrees_with_prior_topic(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _stub_llm_classifier(
        monkeypatch,
        return_topic="perdidas_fiscales_art147",
        confidence=0.80,
    )
    fake_runtime_path = tmp_path / "runtime.json"
    fake_runtime_path.write_text("{}", encoding="utf-8")

    result = resolve_chat_topic(
        message="¿continúa aplicando el mismo régimen?",
        requested_topic=None,
        runtime_config_path=fake_runtime_path,
        conversation_state={"prior_topic": "perdidas_fiscales_art147"},
    )
    assert result.effective_topic == "perdidas_fiscales_art147"
    # LLM verdict stands as-is — no tiebreaker mode tag.
    assert result.mode == "llm"
    assert result.confidence == pytest.approx(0.80)


def test_tiebreaker_skipped_when_lexical_router_finds_dominant_topic(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """If the rule-based router already returns a winner, the LLM (and
    the tiebreaker) never run — confirms the soft prior never overrides
    a clear lexical topic switch. Uses a real, well-keyworded query so
    _resolve_rule_based_topic produces a result before the LLM path."""
    fake_runtime_path = tmp_path / "runtime.json"
    fake_runtime_path.write_text("{}", encoding="utf-8")

    # Stub the LLM so we can prove it wasn't called.
    captured = _stub_llm_classifier(
        monkeypatch,
        return_topic="perdidas_fiscales_art147",
        confidence=0.99,
    )
    result = resolve_chat_topic(
        message="¿Cuáles son las tarifas de retención en la fuente para honorarios?",
        requested_topic=None,
        runtime_config_path=fake_runtime_path,
        conversation_state={"prior_topic": "perdidas_fiscales_art147"},
    )
    # Lexical router answered; LLM stub was never invoked.
    assert captured == {}
    # The exact key resolves to whichever bucket the keywords map to (the
    # taxonomy may distinguish e.g. retencion_fuente_general); what matters is
    # that we did NOT fall through to the prior-topic prior, and the result is
    # NOT the carried prior_topic.
    assert result.effective_topic != "perdidas_fiscales_art147"
    assert "retencion" in (result.effective_topic or "")
    assert result.mode != "prior_state_tiebreaker"


def test_no_runtime_path_falls_back_to_prior_topic_when_no_other_signal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """LLM adapter unreachable + lexical empty + no requested_topic + prior
    exists → last-chance fallback. Surfaces mode="prior_state_fallback" so
    operators can tell the difference from a confident routing decision."""
    result = resolve_chat_topic(
        message="¿y cuánto es?",  # ~3 tokens, no lexical match
        requested_topic=None,
        runtime_config_path=None,  # no LLM path attempted
        conversation_state={"prior_topic": "regimen_simple"},
    )
    assert result.effective_topic == "regimen_simple"
    assert result.mode == "prior_state_fallback"
    assert result.reason == "fallback:prior_topic_from_conversation_state"
    assert result.confidence == pytest.approx(0.5)


def test_no_state_no_runtime_no_lexical_returns_no_topic_detected() -> None:
    """Sanity: nothing changes for the pre-Level-2 path."""
    result = resolve_chat_topic(
        message="¿y cuánto es?",
        requested_topic=None,
        runtime_config_path=None,
        conversation_state=None,
    )
    assert result.effective_topic is None
    assert result.reason == "fallback:no_topic_detected"
