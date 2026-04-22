"""Structural tests for `lia_graph.topic_router_keywords`.

This module is pure data — the heuristic vocabulary that drives
`topic_router.detect_topic_from_text`. Tests here lock in:

  * all declared topics have at least one strong or weak keyword
  * the sub-topic override patterns compile and match their canonical
    example queries to the expected topic key
  * the `_TOPIC_KEYWORDS` dict identity is preserved after
    `register_topic_keywords` mutations on the host
"""

from __future__ import annotations

import re

from lia_graph.topic_router_keywords import (
    _SUBTOPIC_OVERRIDE_PATTERNS,
    _TOPIC_KEYWORDS,
    _TOPIC_NOTICE_OVERRIDES,
)


def test_topic_keywords_every_entry_has_at_least_one_bucket() -> None:
    for topic, buckets in _TOPIC_KEYWORDS.items():
        assert "strong" in buckets or "weak" in buckets, f"{topic} has no keywords"
        for bucket_name, keywords in buckets.items():
            assert bucket_name in {"strong", "weak"}, f"{topic} has unknown bucket {bucket_name}"
            assert isinstance(keywords, tuple)
            assert all(isinstance(k, str) and k.strip() for k in keywords)


def test_topic_notice_overrides_reference_declared_topics() -> None:
    for topic in _TOPIC_NOTICE_OVERRIDES:
        assert topic in _TOPIC_KEYWORDS, f"notice references unknown topic {topic}"


def test_subtopic_override_structure_is_triples_of_pattern_key_keywords() -> None:
    assert len(_SUBTOPIC_OVERRIDE_PATTERNS) >= 1
    for pattern, topic_key, keywords in _SUBTOPIC_OVERRIDE_PATTERNS:
        assert isinstance(pattern, re.Pattern)
        assert isinstance(topic_key, str) and topic_key.strip()
        assert isinstance(keywords, tuple)
        assert all(isinstance(k, str) and k.strip() for k in keywords)


def test_gmf_override_detects_canonical_queries() -> None:
    # First override is GMF; exercise a handful of canonical phrasings.
    gmf = next((p for p, t, _ in _SUBTOPIC_OVERRIDE_PATTERNS if t == "gravamen_movimiento_financiero_4x1000"), None)
    assert gmf is not None
    assert gmf.search("como funciona el gmf en cuentas exentas") is not None
    assert gmf.search("qué es el 4x1000") is not None
    assert gmf.search("cuatro por mil") is not None
    assert gmf.search("artículo 871 del et") is not None


def test_patrimonio_fiscal_override_does_not_shadow_unrelated_queries() -> None:
    pat = next((p for p, t, _ in _SUBTOPIC_OVERRIDE_PATTERNS if t == "patrimonio_fiscal_renta"), None)
    assert pat is not None
    # Should fire on canonical phrasings…
    assert pat.search("valor patrimonial fiscal del inmueble") is not None
    assert pat.search("patrimonio fiscal de la persona jurídica") is not None
    # …but not on plain renta queries that don't mention patrimonio.
    assert pat.search("tarifa de renta personas naturales") is None


def test_laboral_colloquial_override_catches_common_questions() -> None:
    lab = next(
        (p for p, t, _ in _SUBTOPIC_OVERRIDE_PATTERNS if t == "laboral"),
        None,
    )
    assert lab is not None
    assert lab.search("cuanto le pago a una empleada temporal") is not None
    assert lab.search("empleada de servicio doméstico") is not None
    assert lab.search("trabaja 3 dias semanales") is not None


def test_host_module_shares_same_dict_identity() -> None:
    # Round-11 guard: `register_topic_keywords` mutates _TOPIC_KEYWORDS on the
    # host, and that must be visible to the data module (same dict object).
    import lia_graph.topic_router as host
    assert host._TOPIC_KEYWORDS is _TOPIC_KEYWORDS
    assert host._SUBTOPIC_OVERRIDE_PATTERNS is _SUBTOPIC_OVERRIDE_PATTERNS
    assert host._TOPIC_NOTICE_OVERRIDES is _TOPIC_NOTICE_OVERRIDES


# --- Backlog item A (conservative pass) — adversarial guards ---
# Each test below asserts that a bare polysemous term that USED to live in
# `laboral.weak` no longer hijacks an unrelated query. Flip-to-laboral here
# means the removal regressed — investigate which bucket the keyword leaked
# back into.

import pytest
from lia_graph.topic_router import resolve_chat_topic


@pytest.mark.parametrize(
    "query, must_not_route_to",
    [
        # `liquidación` removed — tax / procedural / societario senses stay off laboral.
        ("liquidación oficial de la DIAN por requerimiento especial", "laboral"),
        ("sociedad en proceso de liquidación", "laboral"),
        ("necesito liquidar el impuesto de renta", "laboral"),
        # `prima` removed — equity / insurance senses stay off laboral.
        ("prima en colocación de acciones", "laboral"),
        ("prima de seguro de vida deducible", "laboral"),
        # `aportes` / `aportaciones` removed — capital senses stay off laboral.
        ("aportes de capital a una sociedad", "laboral"),
        ("aportaciones a fondos de inversión", "laboral"),
        # `planilla` removed — generic spreadsheet sense stays off laboral.
        ("planilla de cálculo para conciliación bancaria", "laboral"),
        # `bonificación` removed — commercial sense stays off laboral.
        ("bonificación comercial por volumen de compra", "laboral"),
    ],
)
def test_polysemous_bare_terms_do_not_hijack_adversarial_queries(
    query: str, must_not_route_to: str
) -> None:
    result = resolve_chat_topic(message=query, requested_topic=None)
    assert result.effective_topic != must_not_route_to, (
        f"query {query!r} routed to {must_not_route_to!r} — "
        f"polysemous-weak-keyword anti-pattern regression. "
        f"Reason: {result.reason}"
    )


def test_laboral_real_queries_still_route_via_compounds_or_override() -> None:
    # Recall check: after removing the bare polysemous terms, genuine labor
    # queries must still route to laboral — either via compound strong
    # entries or via the _SUBTOPIC_OVERRIDE_PATTERNS laboral regex.
    for query in (
        "liquidación de nómina mensual",
        "cómo liquido a un empleado con contrato de obra labor",
        "prima de servicios del segundo semestre",
        "aportes a seguridad social del mes",
        "planilla PILA de la empresa",
    ):
        result = resolve_chat_topic(message=query, requested_topic=None)
        assert result.effective_topic == "laboral", (
            f"{query!r} should route to laboral but went to {result.effective_topic!r}"
        )


# --- Backlog item C step 3 (model topic) — retencion_en_la_fuente ---

def test_retencion_en_la_fuente_routes_canonical_queries() -> None:
    for query in (
        "cuál es la tarifa de retención en la fuente para servicios",
        "el cliente es autorretenedor de renta",
        "certificado de retención del agente retenedor",
        "base mínima de retención para compras",
    ):
        result = resolve_chat_topic(message=query, requested_topic=None)
        assert result.effective_topic == "retencion_en_la_fuente", (
            f"{query!r} -> {result.effective_topic!r} (expected retencion_en_la_fuente)"
        )
