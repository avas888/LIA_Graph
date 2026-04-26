"""next_v4 §4 Level 2 — ConversationState prior-topic plumbing.

Covers the four new dataclass fields, their round-trip through
``to_dict`` / ``conversation_state_from_dict``, and the
``build_conversation_state`` reader that lifts ``effective_topic`` /
``secondary_topics`` / ``effective_subtopic`` out of each assistant turn's
``turn_metadata`` (already written by ``ui_chat_persistence._build_turn_metadata``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from lia_graph.pipeline_c.conversation_state import (
    ConversationState,
    build_conversation_state,
    conversation_state_from_dict,
)


@dataclass
class _FakeTurn:
    role: str
    content: str
    turn_metadata: dict[str, Any] | None = None


class _FakeSession:
    def __init__(self, turns: list[_FakeTurn]) -> None:
        self.turns = turns


def test_dataclass_defaults_keep_prior_topic_fields_empty() -> None:
    state = ConversationState()
    assert state.prior_topic is None
    assert state.prior_subtopic is None
    assert state.topic_trajectory == ()
    assert state.prior_secondary_topics == ()


def test_round_trip_via_to_dict_and_from_dict_preserves_prior_topic_fields() -> None:
    original = ConversationState(
        goal="Compensación de pérdidas fiscales",
        prior_topic="perdidas_fiscales_art147",
        prior_subtopic="compensacion_anual",
        topic_trajectory=("perdidas_fiscales_art147", "firmeza_declaraciones"),
        prior_secondary_topics=("declaracion_renta",),
    )
    payload = original.to_dict()
    assert payload["prior_topic"] == "perdidas_fiscales_art147"
    assert payload["prior_subtopic"] == "compensacion_anual"
    assert payload["topic_trajectory"] == [
        "perdidas_fiscales_art147",
        "firmeza_declaraciones",
    ]
    assert payload["prior_secondary_topics"] == ["declaracion_renta"]

    restored = conversation_state_from_dict(payload)
    assert restored is not None
    assert restored.prior_topic == "perdidas_fiscales_art147"
    assert restored.prior_subtopic == "compensacion_anual"
    assert restored.topic_trajectory == (
        "perdidas_fiscales_art147",
        "firmeza_declaraciones",
    )
    assert restored.prior_secondary_topics == ("declaracion_renta",)


def test_build_conversation_state_lifts_effective_topic_from_assistant_turn_metadata() -> None:
    turns = [
        _FakeTurn(role="user", content="¿Cómo se compensan las pérdidas fiscales?"),
        _FakeTurn(
            role="assistant",
            content="El art. 147 ET regula la compensación...",
            turn_metadata={
                "effective_topic": "perdidas_fiscales_art147",
                "secondary_topics": ["declaracion_renta"],
                "effective_subtopic": "compensacion_anual",
            },
        ),
    ]
    state = build_conversation_state(_FakeSession(turns))
    assert state is not None
    assert state.prior_topic == "perdidas_fiscales_art147"
    assert state.prior_subtopic == "compensacion_anual"
    assert state.topic_trajectory == ("perdidas_fiscales_art147",)
    assert state.prior_secondary_topics == ("declaracion_renta",)


def test_build_conversation_state_topic_trajectory_compresses_consecutive_duplicates() -> None:
    turns = [
        _FakeTurn(role="user", content="t1 user"),
        _FakeTurn(
            role="assistant",
            content="t1 a",
            turn_metadata={"effective_topic": "perdidas_fiscales_art147"},
        ),
        _FakeTurn(role="user", content="t2 user"),
        _FakeTurn(
            role="assistant",
            content="t2 a",
            turn_metadata={"effective_topic": "perdidas_fiscales_art147"},  # duplicate
        ),
        _FakeTurn(role="user", content="t3 user"),
        _FakeTurn(
            role="assistant",
            content="t3 a",
            turn_metadata={"effective_topic": "firmeza_declaraciones"},
        ),
    ]
    state = build_conversation_state(_FakeSession(turns))
    assert state is not None
    # Only two entries — the duplicate at t2 collapses; the order reflects
    # the actual movement across the conversation, oldest-to-newest.
    assert state.topic_trajectory == (
        "perdidas_fiscales_art147",
        "firmeza_declaraciones",
    )
    # prior_topic is the last-seen value (most recent assistant turn).
    assert state.prior_topic == "firmeza_declaraciones"


def test_build_conversation_state_skips_when_no_topic_metadata() -> None:
    """Turns without effective_topic don't populate prior_topic — confirms
    the reader is purely additive: behavior pre-Level-2 is preserved when the
    persistence layer hasn't (yet) written topic metadata."""
    turns = [
        _FakeTurn(role="user", content="¿Pregunta?"),
        _FakeTurn(
            role="assistant",
            content="Respuesta sin metadata de tema.",
            turn_metadata={"citations": [{"legal_reference": "ET art. 147"}]},
        ),
    ]
    state = build_conversation_state(_FakeSession(turns))
    assert state is not None
    assert state.prior_topic is None
    assert state.topic_trajectory == ()
    # The pre-existing citation extractor still runs.
    assert any("147" in anchor for anchor in state.normative_anchors)
