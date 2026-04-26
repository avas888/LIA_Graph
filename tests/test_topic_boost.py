"""Tests for v5 §1.D topic boost in `retriever_supabase`."""

from __future__ import annotations

import pytest

from lia_graph.pipeline_d import retriever_supabase as rs


# ─── Factor resolution ─────────────────────────────────────────────────────


def test_default_topic_boost_is_1_5(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LIA_TOPIC_BOOST_FACTOR", raising=False)
    assert rs._resolve_topic_boost_factor() == 1.5


def test_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LIA_TOPIC_BOOST_FACTOR", "2.0")
    assert rs._resolve_topic_boost_factor() == 2.0


def test_env_invalid_falls_back_to_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LIA_TOPIC_BOOST_FACTOR", "not-a-number")
    assert rs._resolve_topic_boost_factor() == 1.5


def test_env_below_one_floored_to_one(monkeypatch: pytest.MonkeyPatch) -> None:
    """Invariant I5 — boost must never penalize."""
    monkeypatch.setenv("LIA_TOPIC_BOOST_FACTOR", "0.5")
    assert rs._resolve_topic_boost_factor() == 1.0


def test_env_explicit_one_disables_boost(monkeypatch: pytest.MonkeyPatch) -> None:
    """Caller can disable §1.D entirely by setting boost = 1.0 — the
    RPC payload then keeps filter_topic = None (back-compat)."""
    monkeypatch.setenv("LIA_TOPIC_BOOST_FACTOR", "1.0")
    assert rs._resolve_topic_boost_factor() == 1.0


# ─── Payload shape — back-compat + boost-enabled ───────────────────────────


class _StubPlan:
    """Minimum surface to drive `_hybrid_search` payload construction."""

    def __init__(
        self,
        *,
        topic_hints: tuple[str, ...] = (),
        sub_topic_intent: str | None = None,
    ) -> None:
        self.topic_hints = topic_hints
        self.sub_topic_intent = sub_topic_intent

        # Shape required by _hybrid_search to compute match_count + dates.
        class _Shape:
            primary_article_limit = 5
            connected_article_limit = 5
            support_document_limit = 5

        class _Temporal:
            cutoff_date = None

        self.evidence_bundle_shape = _Shape()
        self.temporal_context = _Temporal()


class _StubResponse:
    """Mimics `db.rpc(...).execute()` result shape."""

    def __init__(self) -> None:
        self.data = []


class _StubRpc:
    """Captures the payload passed to db.rpc('hybrid_search', payload)."""

    def __init__(self) -> None:
        self.captured_payload: dict | None = None

    def execute(self) -> _StubResponse:
        return _StubResponse()


class _StubDb:
    def __init__(self) -> None:
        self._rpc = _StubRpc()

    def rpc(self, name: str, payload: dict) -> _StubRpc:
        assert name == "hybrid_search"
        self._rpc.captured_payload = payload
        return self._rpc


def test_payload_with_topic_and_boost(monkeypatch: pytest.MonkeyPatch) -> None:
    """When the plan has a router topic AND boost > 1.0, the payload sets
    filter_topic + filter_topic_boost. This is the v5 §1.D happy path."""
    monkeypatch.setenv("LIA_TOPIC_BOOST_FACTOR", "1.5")
    monkeypatch.setenv("LIA_SUBTOPIC_BOOST_FACTOR", "1.5")
    db = _StubDb()
    plan = _StubPlan(topic_hints=("regimen_cambiario",))
    rs._hybrid_search(db, plan=plan, query_text="declaración cambiaria IMC")
    payload = db._rpc.captured_payload
    assert payload is not None
    assert payload["filter_topic"] == "regimen_cambiario"
    assert payload["filter_topic_boost"] == 1.5


def test_payload_back_compat_when_boost_is_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When boost = 1.0 (operator turned §1.D off), filter_topic stays
    None in the payload — preserving pre-§1.D behavior."""
    monkeypatch.setenv("LIA_TOPIC_BOOST_FACTOR", "1.0")
    db = _StubDb()
    plan = _StubPlan(topic_hints=("regimen_cambiario",))
    rs._hybrid_search(db, plan=plan, query_text="declaración cambiaria IMC")
    payload = db._rpc.captured_payload
    assert payload is not None
    assert payload["filter_topic"] is None
    assert "filter_topic_boost" not in payload


def test_payload_back_compat_when_no_router_topic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No router topic → filter_topic stays None regardless of boost."""
    monkeypatch.setenv("LIA_TOPIC_BOOST_FACTOR", "1.5")
    db = _StubDb()
    plan = _StubPlan(topic_hints=())
    rs._hybrid_search(db, plan=plan, query_text="x")
    payload = db._rpc.captured_payload
    assert payload is not None
    assert payload["filter_topic"] is None
    assert "filter_topic_boost" not in payload


def test_subtopic_boost_still_works_alongside(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The two boosts compose; subtopic boost path unchanged."""
    monkeypatch.setenv("LIA_TOPIC_BOOST_FACTOR", "1.5")
    monkeypatch.setenv("LIA_SUBTOPIC_BOOST_FACTOR", "2.0")
    db = _StubDb()
    plan = _StubPlan(
        topic_hints=("regimen_cambiario",),
        sub_topic_intent="declaracion_cambiaria",
    )
    rs._hybrid_search(db, plan=plan, query_text="x")
    payload = db._rpc.captured_payload
    assert payload is not None
    assert payload["filter_topic"] == "regimen_cambiario"
    assert payload["filter_topic_boost"] == 1.5
    assert payload["filter_subtopic"] == "declaracion_cambiaria"
    assert payload["subtopic_boost"] == 2.0
