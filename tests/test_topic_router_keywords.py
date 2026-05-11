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


def _deprecated_topics_from_taxonomy() -> set[str]:
    """Read deprecated topic keys from config/topic_taxonomy.json so the
    invariant test honors authoritative deprecation state instead of a
    duplicated python list."""
    import json
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "config" / "topic_taxonomy.json"
    if not path.exists():
        return set()
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    deprecated: set[str] = set()
    for entry in data.get("topics", []) if isinstance(data, dict) else data:
        if not isinstance(entry, dict):
            continue
        if entry.get("status") == "deprecated" and entry.get("key"):
            deprecated.add(str(entry["key"]))
    return deprecated


def test_no_silent_routing_holes_among_active_supported_topics() -> None:
    """Every active (non-deprecated) supported topic must have at least
    one strong keyword OR be served by a `_SUBTOPIC_OVERRIDE_PATTERNS`
    entry — otherwise it's a silent routing hole (the keyword scorer
    returns 0, the topic-safety guard fires false positives, and queries
    in that domain abstain).

    Companion invariant to ``test_subtopic_override_targets_are_all_gate_
    scoreable``: that one catches override targets missing from the gate
    vocabulary; this one catches gate-known topics with empty buckets.
    Together they pin "no router-producible topic is unscoreable."

    next_v5 §9.2 — surfaced by the long-standing `retencion_en_la_fuente`
    + `rentas_exentas` warnings on every server boot.
    """
    from lia_graph.topic_router import get_supported_topics

    deprecated = _deprecated_topics_from_taxonomy()
    override_served = {entry[1] for entry in _SUBTOPIC_OVERRIDE_PATTERNS}
    silent_holes: list[str] = []
    for topic in get_supported_topics():
        if topic in deprecated:
            continue
        if topic in override_served:
            continue  # served via override, vocabulary is intentional
        entry = _TOPIC_KEYWORDS.get(topic, {})
        if entry.get("strong") or entry.get("weak"):
            continue
        silent_holes.append(topic)
    assert not silent_holes, (
        f"Active supported topics with no scoring vocabulary: "
        f"{sorted(silent_holes)}. Add strong/weak keyword buckets in "
        f"_TOPIC_KEYWORDS or mark the topic as deprecated in topic_taxonomy.json."
    )


def test_subtopic_override_targets_are_all_gate_scoreable() -> None:
    """Every topic the router can produce via _SUBTOPIC_OVERRIDE_PATTERNS
    must also be a key in _TOPIC_KEYWORDS so the coherence-gate has
    vocabulary to score it.

    Without this invariant, the gate scores router-target topics as 0
    by definition; any retrieved article scoring >0 on an in-vocabulary
    neighbor topic then trips the topic-safety guard with a false
    positive (every query in the affected topic refuses to answer).
    Surfaced 2026-05-10 by `art. 107 ET` query refusing on the
    `costos_deducciones_renta` route — see next_v5 §9.
    """
    override_targets = {entry[1] for entry in _SUBTOPIC_OVERRIDE_PATTERNS}
    gate_topics = set(_TOPIC_KEYWORDS.keys())
    gap = override_targets - gate_topics
    assert not gap, (
        f"Router-target topics missing from _TOPIC_KEYWORDS: {sorted(gap)}. "
        f"Add strong/weak keyword buckets so the coherence gate can score them."
    )


def test_costos_deducciones_renta_keywords_match_art_107_query() -> None:
    """Regression for the 2026-05-10 art. 107 topic-safety false positive.
    Confirms the new vocabulary actually scores this canonical query."""
    buckets = _TOPIC_KEYWORDS["costos_deducciones_renta"]
    query = "¿Qué requisitos debe cumplir un gasto para ser deducible bajo el artículo 107 del ET?"
    query_lower = query.lower()
    matched_strong = [kw for kw in buckets["strong"] if kw in query_lower]
    assert matched_strong, (
        f"No strong keyword matches the canonical art. 107 query. "
        f"Tried: {buckets['strong'][:5]}…"
    )


def test_topics_are_parent_child_compatible_honors_taxonomy_axis() -> None:
    """§9.1 regression — parent↔child topic pairs are compatible so the
    safety guard doesn't false-positive when a parent-routed query
    retrieves child-tagged articles."""
    from lia_graph.topic_router_keywords import topics_are_parent_child_compatible

    assert topics_are_parent_child_compatible("declaracion_renta", "costos_deducciones_renta")
    assert topics_are_parent_child_compatible("costos_deducciones_renta", "declaracion_renta")
    assert topics_are_parent_child_compatible("declaracion_renta", "rentas_exentas")
    # Same topic is compatible with itself.
    assert topics_are_parent_child_compatible("iva", "iva")
    # Siblings (two children sharing a parent) are NOT compatible —
    # that would loosen the guard too far.
    assert not topics_are_parent_child_compatible(
        "costos_deducciones_renta", "rentas_exentas"
    )
    # Unrelated topics stay incompatible.
    assert not topics_are_parent_child_compatible("iva", "laboral")
    # Empty strings short-circuit to False.
    assert not topics_are_parent_child_compatible("", "iva")
    assert not topics_are_parent_child_compatible("iva", "")


def test_rentas_exentas_keywords_match_canonical_query() -> None:
    """§9.2 regression: rentas_exentas was previously empty; this confirms
    the new vocabulary scores a canonical art. 206 ET query."""
    buckets = _TOPIC_KEYWORDS["rentas_exentas"]
    query = "¿cómo se aplica la exención del 25% laboral del artículo 206 del ET?"
    query_lower = query.lower()
    matched_strong = [kw for kw in buckets["strong"] if kw in query_lower]
    assert matched_strong, (
        f"No strong keyword matches the canonical rentas_exentas query. "
        f"Tried: {buckets['strong'][:5]}…"
    )


def test_impuesto_consumo_keywords_match_inc_query() -> None:
    """Sister regression: the same gap closure must score INC queries."""
    buckets = _TOPIC_KEYWORDS["impuesto_consumo"]
    query = "¿cómo se declara el impuesto al consumo en restaurantes y bares?"
    query_lower = query.lower()
    matched_strong = [kw for kw in buckets["strong"] if kw in query_lower]
    assert matched_strong, (
        f"No strong keyword matches the canonical INC query. "
        f"Tried: {buckets['strong'][:5]}…"
    )


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


# --- Backlog item C step 3 (model topic) — retencion routing ---
# `retencion_en_la_fuente` was deprecated 2026-04-25 (see comment in
# topic_router_keywords.py line 644 + topic_taxonomy.json status:deprecated,
# merged_into:["retencion_fuente_general"]). The canonical topic for
# retention queries is now `retencion_fuente_general`. next_v5 §9.2.

def test_retencion_routes_canonical_queries_to_merged_topic() -> None:
    for query in (
        "cuál es la tarifa de retención en la fuente para servicios",
        "el cliente es autorretenedor de renta",
        "certificado de retención del agente retenedor",
        "base mínima de retención para compras",
    ):
        result = resolve_chat_topic(message=query, requested_topic=None)
        assert result.effective_topic == "retencion_fuente_general", (
            f"{query!r} -> {result.effective_topic!r} (expected retencion_fuente_general)"
        )
