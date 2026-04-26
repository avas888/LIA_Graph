from __future__ import annotations

import json
import logging
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

from .llm_runtime import resolve_llm_adapter
from .topic_guardrails import (
    TopicScope,
    extend_topic_scope_allowed_topics,
    get_supported_topics,
    get_topic_scope,
    normalize_topic_key,
    register_topic_alias,
    register_topic_scope,
)

# Keyword + regex data moved to `topic_router_keywords.py` during
# granularize-v2 round 11 to graduate the host below 1000 LOC.
# Re-imported so in-module references work; `register_topic_keywords`
# still mutates `_TOPIC_KEYWORDS` in place (dict is shared by identity).
from .topic_router_keywords import (
    _SUBTOPIC_OVERRIDE_PATTERNS,
    _TOPIC_KEYWORDS,
    _TOPIC_NOTICE_OVERRIDES,
)


_SUPPORTED_TOPICS: tuple[str, ...] = tuple(sorted(get_supported_topics()))
_LLM_CONFIDENCE_THRESHOLD = 0.75
_MAX_SECONDARY_TOPICS = 3

# Narrow SQL filter for child topics: maps child_topic → frozenset of core DB
# topic values to use in SQL WHERE instead of full inherited scope.
# Populated during _bootstrap_custom_corpora() pass 2.
_PARENT_CORE_TOPICS: dict[str, frozenset[str]] = {}


@dataclass(frozen=True)
class TopicDetection:
    """Resultado de deteccion de tema basada en keywords, reutilizable por ingestion."""

    topic: str | None
    confidence: float
    scores: dict[str, float]
    source: str = "keywords"



def register_topic_keywords(
    topic_key: str,
    strong: tuple[str, ...] | list[str] = (),
    weak: tuple[str, ...] | list[str] = (),
) -> None:
    """Register keyword patterns for a custom topic at runtime."""
    entry: dict[str, tuple[str, ...]] = {}
    if strong:
        entry["strong"] = tuple(strong)
    if weak:
        entry["weak"] = tuple(weak)
    if entry:
        _TOPIC_KEYWORDS[topic_key] = entry


def _bootstrap_custom_corpora() -> None:
    """Carga corpora_custom.json al inicio y registra keywords + scopes para cada corpus custom.

    Esto hace que corpora_custom.json sea la fuente unica de verdad para topicos custom:
    cualquier corpus con topic != null se registra automaticamente en el router y los
    guardrails, sin necesidad de editar topic_guardrails.py ni topic_router.py a mano.
    """
    import json
    from pathlib import Path

    cfg_path = Path("config/corpora_custom.json")
    if not cfg_path.exists():
        # Fallback: ruta relativa al archivo fuente
        cfg_path = Path(__file__).parent.parent.parent / "config" / "corpora_custom.json"
    if not cfg_path.exists():
        return

    try:
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
    except Exception:
        logger.warning("topic_router: error cargando corpora_custom.json en bootstrap", exc_info=True)
        return

    # Pass 1: register keywords + scopes for each custom corpus
    parent_links: list[tuple[str, str]] = []  # (child_topic, parent_topic_key)

    for entry in data.get("custom_corpora", []):
        key = str(entry.get("key") or "").strip()
        topic = str(entry.get("topic") or "").strip()
        if not key or not topic:
            continue  # corpus sin topic (ej. "principal" catch-all)

        # Keywords para N1
        kw = entry.get("keywords") or {}
        register_topic_keywords(topic, strong=list(kw.get("strong") or []), weak=list(kw.get("weak") or []))

        # TopicScope para guardrails (si no existe ya)
        if topic not in get_supported_topics():
            label = str(entry.get("label") or key)
            register_topic_scope(TopicScope(
                key=topic,
                label=label,
                allowed_topics=frozenset({topic}),
                allowed_path_prefixes=(),
            ))
            register_topic_alias(topic, topic)
            if key != topic:
                register_topic_alias(key, topic)

        # Collect parent_topic links for pass 2
        parent_key = str(entry.get("parent_topic") or "").strip()
        if not parent_key and entry.get("active", False):
            logger.warning(
                "topic_router: custom corpus '%s' (topic='%s') has no parent_topic "
                "— retrieval limited to docs tagged '%s'",
                key, topic, topic,
            )
        if parent_key:
            parent_links.append((topic, parent_key))

    # Pass 2: resolve parent_topic inheritance (bidirectional)
    # Child inherits parent's allowed_topics so retrieval finds parent docs.
    # Parent gains child's topic so parent queries still find re-tagged child docs.

    # Snapshot each parent's original allowed_topics BEFORE the loop extends
    # them with child keys — used for _PARENT_CORE_TOPICS narrow SQL filter.
    parent_original: dict[str, frozenset[str]] = {}
    for _child, pkey in parent_links:
        pcanon = normalize_topic_key(pkey) or pkey
        if pcanon not in parent_original:
            ps = get_topic_scope(pcanon)
            if ps is not None:
                parent_original[pcanon] = ps.allowed_topics

    for child_topic, parent_key in parent_links:
        parent_canonical = normalize_topic_key(parent_key)
        if parent_canonical is None:
            parent_canonical = parent_key
        parent_scope = get_topic_scope(parent_canonical)
        if parent_scope is None:
            logger.warning(
                "topic_router: parent_topic '%s' not found for custom corpus '%s'",
                parent_key, child_topic,
            )
            continue
        # Child inherits parent's allowed_topics + path prefixes
        child_scope = get_topic_scope(child_topic)
        if child_scope is not None:
            merged_topics = child_scope.allowed_topics | parent_scope.allowed_topics
            register_topic_scope(TopicScope(
                key=child_scope.key,
                label=child_scope.label,
                allowed_topics=merged_topics,
                allowed_path_prefixes=child_scope.allowed_path_prefixes + parent_scope.allowed_path_prefixes,
            ))
        # Parent gains child's topic key for bidirectional visibility
        extend_topic_scope_allowed_topics(parent_scope.key, frozenset({child_topic}))

        # Build narrow SQL filter for child: {child_topic} ∪ parent's ORIGINAL
        # allowed_topics (before any child extensions).  This gives SQL
        # WHERE topic IN ('costos_deducciones_renta','renta','renta_parametros')
        # instead of the full 17+ inherited set.
        orig = parent_original.get(parent_canonical, frozenset())
        if orig:
            _PARENT_CORE_TOPICS[child_topic] = frozenset({child_topic}) | orig

    # Reconstruir _SUPPORTED_TOPICS para incluir los topics recien registrados
    global _SUPPORTED_TOPICS
    _SUPPORTED_TOPICS = tuple(sorted(get_supported_topics()))


_bootstrap_custom_corpora()


def _log_topics_without_keywords() -> None:
    """Warn at boot for any supported topic with no routing keywords.

    Backlog item C (docs/done/next/structuralwork_v1_SEENOW.md): a topic that is
    registered in ``get_supported_topics()`` but has neither strong nor
    weak entries in ``_TOPIC_KEYWORDS`` cannot be picked by the keyword
    scorer. Some of these are legitimately 0/0 because they are served
    exclusively by a ``_SUBTOPIC_OVERRIDE_PATTERNS`` entry (for example
    ``gravamen_movimiento_financiero_4x1000`` — see the ``Tough calls``
    section in the backlog doc); those are surfaced at INFO, not WARNING.
    Everything else is a silent routing hole and deserves a louder signal.
    """
    override_served = {topic for _pattern, topic, _kw in _SUBTOPIC_OVERRIDE_PATTERNS}
    for topic in get_supported_topics():
        entry = _TOPIC_KEYWORDS.get(topic, {})
        has_keywords = bool(entry.get("strong") or entry.get("weak"))
        if has_keywords:
            continue
        if topic in override_served:
            logger.info(
                "topic_router: %r has no keywords but is served by a subtopic-override pattern",
                topic,
            )
        else:
            logger.warning(
                "topic_router: topic %r has no registered keywords — queries in this domain "
                "will fall through to fallback routing or be hijacked by adjacent weak hits",
                topic,
            )


_log_topics_without_keywords()


def get_narrow_topic_filter(topic: str) -> frozenset[str] | None:
    """Return narrow SQL topic values for a child topic, or None if not a child."""
    return _PARENT_CORE_TOPICS.get(topic)


def get_subtopic_search_keywords(topic: str) -> tuple[str, ...]:
    """Return search keywords for a sub-topic, or empty tuple."""
    # _SUBTOPIC_OVERRIDE_PATTERNS is defined later in this module (after
    # keyword dicts), so we build the reverse lookup lazily on first call.
    global _SUBTOPIC_KEYWORDS
    if _SUBTOPIC_KEYWORDS is None:
        _SUBTOPIC_KEYWORDS = {
            t: kw for _, t, kw in _SUBTOPIC_OVERRIDE_PATTERNS
        }
    return _SUBTOPIC_KEYWORDS.get(topic, ())


_SUBTOPIC_KEYWORDS: dict[str, tuple[str, ...]] | None = None


@dataclass(frozen=True)
class TopicRoutingResult:
    requested_topic: str | None
    effective_topic: str | None
    secondary_topics: tuple[str, ...]
    topic_adjusted: bool
    confidence: float
    reason: str
    topic_notice: str | None = None
    mode: str = "fallback"
    llm_runtime: dict[str, Any] | None = None
    subtopic_search_keywords: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "requested_topic": self.requested_topic,
            "effective_topic": self.effective_topic,
            "secondary_topics": list(self.secondary_topics),
            "topic_adjusted": self.topic_adjusted,
            "confidence": round(float(self.confidence), 4),
            "reason": self.reason,
            "topic_notice": self.topic_notice,
            "mode": self.mode,
            "llm_runtime": dict(self.llm_runtime or {}),
        }


def _strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _normalize_text(value: str) -> str:
    lowered = _strip_accents(value).lower()
    return re.sub(r"\s+", " ", lowered).strip()


def _normalize_secondary_topics(
    topics: tuple[str, ...] | list[str] | None,
    *,
    requested_topic: str | None,
    effective_topic: str | None,
    preserve_requested_topic_as_secondary: bool = True,
) -> tuple[str, ...]:
    ordered: list[str] = []
    for raw_topic in list(topics or ()):
        topic = normalize_topic_key(str(raw_topic or ""))
        if topic is None or topic == effective_topic or topic in ordered:
            continue
        ordered.append(topic)
    if (
        preserve_requested_topic_as_secondary
        and requested_topic is not None
        and requested_topic != effective_topic
        and requested_topic not in ordered
    ):
        ordered.insert(0, requested_topic)
    return tuple(ordered[:_MAX_SECONDARY_TOPICS])


def _build_topic_notice(effective_topic: str | None) -> str | None:
    topic = normalize_topic_key(effective_topic)
    if topic is None:
        return None
    if topic in _TOPIC_NOTICE_OVERRIDES:
        return _TOPIC_NOTICE_OVERRIDES[topic]
    label = topic.replace("_", " ")
    return f"Tu pregunta es de {label}, por lo cual utilizaremos nuestra base de datos {label}."


def _keyword_in_text(keyword: str, text: str) -> bool:
    """Match keyword as a complete word/phrase using word boundaries.

    Prevents false positives where a keyword is accidentally a substring
    of an unrelated word (e.g., 'arl' in 'sumarle', 'iva' in 'negativa').
    """
    return bool(re.search(r"\b" + re.escape(keyword) + r"\b", text))


def _score_topic_keywords(message: str) -> dict[str, dict[str, Any]]:
    normalized = _normalize_text(message)
    scores: dict[str, dict[str, Any]] = {}
    for topic, buckets in _TOPIC_KEYWORDS.items():
        strong_hits = [kw for kw in buckets.get("strong", ()) if _keyword_in_text(_normalize_text(kw), normalized)]
        weak_hits = [kw for kw in buckets.get("weak", ()) if _keyword_in_text(_normalize_text(kw), normalized)]
        if not strong_hits and not weak_hits:
            continue
        score = len(strong_hits) * 3 + len(weak_hits)
        scores[topic] = {
            "score": score,
            "strong_hits": strong_hits,
            "weak_hits": weak_hits,
        }
    return scores


def detect_topic_from_text(
    text: str, filename: str | None = None
) -> TopicDetection:
    """Detecta el tema dominante de un texto usando keywords.

    Funcion publica reutilizable por el clasificador de ingestion y otros modulos
    que necesitan deteccion de tema sin el pipeline completo de topic_router.

    Args:
        text: Texto a analizar (cuerpo del documento o query).
        filename: Nombre de archivo (reservado para uso futuro).

    Returns:
        TopicDetection con topic detectado, confianza y scores por tema.
    """
    raw_scores = _score_topic_keywords(text)
    if not raw_scores:
        return TopicDetection(topic=None, confidence=0.0, scores={})

    flat_scores: dict[str, float] = {
        t: float(d["score"]) for t, d in raw_scores.items()
    }
    ranked = sorted(raw_scores.items(), key=lambda item: int(item[1]["score"]), reverse=True)
    top_topic, top_data = ranked[0]
    top_score = int(top_data["score"])
    second_score = int(ranked[1][1]["score"]) if len(ranked) > 1 else 0

    # Determinar si el tema es dominante
    strong_hits = list(top_data.get("strong_hits", []))
    dominant = (
        top_score >= 5
        or (strong_hits and top_score >= 4)
        or (top_score >= 3 and top_score - second_score >= 2)
    )

    if not dominant:
        # No hay tema dominante claro; devolver mejor candidato con confianza baja
        confidence = min(top_score / 6.0, 1.0) * 0.5
        return TopicDetection(
            topic=top_topic, confidence=confidence, scores=flat_scores
        )

    confidence = min(top_score / 6.0, 1.0)
    return TopicDetection(
        topic=top_topic, confidence=confidence, scores=flat_scores
    )


def _build_rule_result(
    *,
    requested_topic: str | None,
    effective_topic: str,
    score: int,
    strong_hits: list[str],
    weak_hits: list[str],
    preserve_requested_topic_as_secondary: bool = True,
) -> TopicRoutingResult:
    hits = [*strong_hits, *weak_hits]
    confidence = min(0.99, 0.62 + score * 0.06)
    adjusted = effective_topic != requested_topic
    # Labor topic: never preserve renta (or any other requested topic) as a
    # secondary. Broad cross-domain fan-out would otherwise pull ET material
    # (for example art. 385 "periodos inferiores a treinta dias") back into a
    # labor bundle and re-introduce the leakage this rule is closing. Targeted
    # laboral<->renta bridging still happens only for explicit cross-domain
    # phrases such as "costos laborales", "nomina electronica", or "art. 108".
    # Applies to both override and keyword-scoring paths.
    preserve_secondary = (
        preserve_requested_topic_as_secondary and effective_topic != "laboral"
    )
    return TopicRoutingResult(
        requested_topic=requested_topic,
        effective_topic=effective_topic,
        secondary_topics=_normalize_secondary_topics(
            (),
            requested_topic=requested_topic,
            effective_topic=effective_topic,
            preserve_requested_topic_as_secondary=preserve_secondary,
        ),
        topic_adjusted=adjusted,
        confidence=confidence,
        reason=f"rule:{effective_topic} matched {', '.join(hits[:6])}",
        topic_notice=_build_topic_notice(effective_topic) if adjusted else None,
        mode="rule",
    )




def _check_subtopic_overrides(message: str) -> tuple[str, tuple[str, ...]] | None:
    """Return (topic, keywords) for the first matching sub-topic override, or None."""
    normalized = _normalize_text(message)
    for pattern, topic, keywords in _SUBTOPIC_OVERRIDE_PATTERNS:
        if pattern.search(normalized):
            return topic, keywords
    return None


# next_v3 §13.11 / SME 2026-04-25 — two registries that gate the LLM-deferral
# path. Both are intentionally short curated lists, not exhaustive — the goal
# is to catch the structural failure classes Alejandro identified, not enumerate
# every phrase. Extend when a new failure class surfaces (not per-question).
#
# All entries here use _normalize_text form: lowercase, no accents, single space.

# Class 1: phrases that signal "the LLM-with-meta-rule should arbitrate".
# Curated from Alejandro's spot-review of q10/q13/q14/q15/q16/q26/q28 (see
# docs/aa_next/taxonomy_v2_sme_spot_review.md + next_v3 §13.11). When ANY of
# these appears in the normalized query, the router defers to the LLM
# regardless of how dominant its lexical match is.
_LLM_DEFERRAL_PHRASES: tuple[str, ...] = (
    # Procedural artifacts (q26 family) — Libro 5 ET; topic always procedural
    # regardless of which substantive tax (renta/IVA/timbre/retención) is being
    # corrected. Per Alejandro's "rewrite test".
    "emplazamiento",
    "requerimiento especial",
    "liquidacion oficial",
    "corregir declaracion",
    "corregir la declaracion",
    "sancion por no",
    "sancion por extemporaneidad",
    "recurso de reconsideracion",
    # Cross-impuesto recovery (q14 family) — IVA pagado que se recupera EN otro
    # impuesto; topic = otro impuesto, no IVA.
    "descuento del iva en",
    "iva en bienes de capital",
    "se descuenta del impuesto",
    "imputa al impuesto de",
    # Verb-test for regime-vs-mechanic (q28 family) — verbos de aplicación
    # ("cual es la tarifa", "cuanto pago") implican mecánica; verbos de
    # evaluación ("estoy pensando", "vale la pena", "como califico") implican
    # régimen. Cuando coexisten lexicalmente régimen + mecánica, la pregunta
    # casi siempre quiere mecánica.
    "cual es la tarifa",
    "cual la tarifa",
    "cuanto pago de",
    "como liquido",
    # Civil-law / firmeza family (q10) — vocabulario que contadores mezclan
    # del derecho civil al hablar de firmeza tributaria.
    "prescribe la facultad",
    "facultad de la dian de",
    "cuantos anos atras",
    "cuantos anios atras",
    # Comparative tension (q13 family) — "X alto pero Y bajo" implica que la
    # respuesta opera SOBRE la comparación, no sobre los conceptos definidos.
    " alto pero ",
    " bajo pero ",
    " positivo pero ",
    " negativo pero ",
    # Recovery / cross-régimen patterns
    "descuento del simple por",
    "iva en obras por impuestos",
)

# Class 2: topic keys known to over-attract — querys que mencionan estos
# topics verbatim suelen estar pidiendo OTRO topic (por la meta-regla "opera
# vs define"). Cuando el router elige un magnet como top y hay segundo bucket
# con CUALQUIER strong hit (más permisivo que el "competing dominantly" check),
# defer al LLM.
_MAGNET_TOPICS: frozenset[str] = frozenset({
    "iva",
    "declaracion_renta",
    "zonas_francas",
    "regimen_simple",
    "impuesto_patrimonio_personas_naturales",
    "regimen_tributario_especial_esal",
    "facturacion_electronica",  # over-attracts on "factura" mentions
})


def _should_defer_to_llm(
    *, message: str, top_topic: str, ranked: list[tuple[str, dict[str, Any]]]
) -> bool:
    """Generic LLM-deferral check — three independent gates.

    Called AFTER the router has identified a dominant top topic, BEFORE the
    rule-based result is returned. Each gate fires independently; any True
    forces deferral. Designed to catch the structural failure classes from
    Alejandro's 2026-04-25 spot-review (see next_v3 §13.11) without per-question
    patches.

    Gates:
      1. *Trigger phrase*: the normalized query contains any phrase from
         ``_LLM_DEFERRAL_PHRASES``. Catches comparative-tension, procedural-
         artifact, cross-impuesto, civil-law, and verb-test queries.
      2. *Magnet + competing strong*: top_topic is in ``_MAGNET_TOPICS`` AND
         the second bucket has any strong hit (regardless of score). Catches
         queries where a magnet topic is lexically dominant but a competing
         topic is plausible by the LLM's mutex/meta-rule reasoning.
      3. *Competing dominantly* (legacy from this same change): second bucket
         has score >= 3 AND strong hits. Catches genuinely ambiguous lexical
         signals that the LLM should arbitrate.

    Extension policy: add a new phrase to ``_LLM_DEFERRAL_PHRASES`` only when a
    new failure class surfaces (not per-question — for that, prefer the
    surgical bucket fix in topic_router_keywords.py). Add a new key to
    ``_MAGNET_TOPICS`` only when post-hoc analysis shows the topic over-attracts
    in production logs.
    """
    normalized = _normalize_text(message)

    # Gate 1: trigger phrase
    for phrase in _LLM_DEFERRAL_PHRASES:
        if phrase in normalized:
            return True

    # Gate 2: magnet + competing strong
    if top_topic in _MAGNET_TOPICS and len(ranked) > 1:
        second_data = ranked[1][1]
        if second_data.get("strong_hits"):
            return True

    # Gate 3: competing dominantly (legacy from the same change)
    if len(ranked) > 1:
        second_score = int(ranked[1][1].get("score", 0) or 0)
        second_strong = bool(ranked[1][1].get("strong_hits"))
        if second_score >= 3 and second_strong:
            return True

    return False


def _resolve_rule_based_topic(
    message: str,
    requested_topic: str | None,
    *,
    preserve_requested_topic_as_secondary: bool = True,
) -> TopicRoutingResult | None:
    # Check sub-topic overrides first (child corpora that can't win keyword scoring)
    override = _check_subtopic_overrides(message)
    if override is not None:
        override_topic, override_keywords = override
        result = _build_rule_result(
            requested_topic=requested_topic,
            effective_topic=override_topic,
            score=6,
            strong_hits=[f"subtopic_override:{override_topic}"],
            weak_hits=[],
            preserve_requested_topic_as_secondary=preserve_requested_topic_as_secondary,
        )
        return TopicRoutingResult(
            requested_topic=result.requested_topic,
            effective_topic=result.effective_topic,
            secondary_topics=result.secondary_topics,
            topic_adjusted=result.topic_adjusted,
            confidence=result.confidence,
            reason=result.reason,
            topic_notice=result.topic_notice,
            mode=result.mode,
            subtopic_search_keywords=override_keywords,
        )

    scores = _score_topic_keywords(message)
    if not scores:
        return None
    ranked = sorted(scores.items(), key=lambda item: int(item[1]["score"]), reverse=True)
    top_topic, top_data = ranked[0]
    second_score = int(ranked[1][1]["score"]) if len(ranked) > 1 else 0
    top_score = int(top_data["score"])
    strong_hits = list(top_data.get("strong_hits", []))
    weak_hits = list(top_data.get("weak_hits", []))
    dominant = (
        top_score >= 5
        or (strong_hits and top_score >= 4)
        or (top_score >= 3 and top_score - second_score >= 2)
    )
    if not dominant:
        return None
    # next_v3 §13.11 — generic LLM deferral checks. Three independent gates
    # that each force the LLM path even when the router has a dominant lexical
    # match. Goal: catch any query with a "complex linguistic structure" that
    # the LLM-with-meta-rule + mutex rules can resolve, instead of patching
    # individual question failures one by one. See _should_defer_to_llm docstring
    # for the design + extension policy.
    if _should_defer_to_llm(message=message, top_topic=top_topic, ranked=ranked):
        return None
    return _build_rule_result(
        requested_topic=requested_topic,
        effective_topic=top_topic,
        score=top_score,
        strong_hits=strong_hits,
        weak_hits=weak_hits,
        preserve_requested_topic_as_secondary=preserve_requested_topic_as_secondary,
    )


def _should_attempt_llm(message: str, requested_topic: str | None) -> bool:
    scores = _score_topic_keywords(message)
    if len(scores) >= 2:
        return True
    if not scores:
        # next_v3 2026-04-25: when the keyword router finds zero matches,
        # the LLM IS the only signal — don't gate it behind ambiguity. SME
        # 30Q validation showed ~5/30 queries return nothing from lexical
        # routing; skipping the LLM here guaranteed those questions miss
        # their expected topic, pulling the chat-resolver accuracy below
        # the 27/30 threshold. Prior behavior (return False) was a safeguard
        # against cost, but LLM cost is bounded by _LLM_CONFIDENCE_THRESHOLD
        # on the response side — a low-confidence verdict still drops to None.
        return True
    only_topic = next(iter(scores.keys()))
    return only_topic != requested_topic


def _build_classifier_prompt(
    *,
    message: str,
    requested_topic: str | None,
    pais: str,
    conversation_state: dict[str, Any] | None = None,
) -> str:
    """Chat-resolver LLM prompt — taxonomy-aware (v2, 2026-04-25).

    Enumerates active v2 topics with one-line definitions and ships the 6
    SME mutex rules alongside. Mirrors the taxonomy-aware ingestion-classifier
    prompt (see ``ingestion_classifier._TAXONOMY_AWARE_PROMPT_TEMPLATE``) but
    trimmed for query classification (no path-veto clause since queries don't
    have a source_path, no subtopic block).

    next_v4 §4 Level 2 — when ``conversation_state`` carries a ``prior_topic``,
    surface it to the LLM as a soft hint mirroring the existing
    ``requested_topic`` retention rule. Reads the field from conversation_state
    only — the dataclass shape is owned by pipeline_c.conversation_state.
    """
    # Late import to avoid a circular dependency at module-load time —
    # topic_router is imported by ingestion_classifier, which defines these
    # builders. By the time a query hits the LLM path, both modules are loaded.
    try:
        from .ingestion_classifier import (
            _build_mutex_block,
            _build_numbered_taxonomy_block,
        )
        taxonomy_block = _build_numbered_taxonomy_block()
        mutex_block = _build_mutex_block()
    except Exception:
        taxonomy_block = ", ".join(_SUPPORTED_TOPICS)
        mutex_block = "(mutex rules unavailable)"

    prior_topic_line = ""
    if isinstance(conversation_state, dict):
        prior_topic_normalized = normalize_topic_key(conversation_state.get("prior_topic"))
        if prior_topic_normalized and prior_topic_normalized in _SUPPORTED_TOPICS:
            prior_topic_line = (
                f"prior_topic (turno anterior): {prior_topic_normalized}\n"
                "Si la consulta actual es ambigua y plausiblemente continúa el mismo hilo, "
                "conserva prior_topic como primary_topic.\n"
            )

    return (
        "Eres un clasificador de tema para un asistente contable y legal en Colombia.\n"
        "Taxonomía v2 (2026-04-25). Decide el tema principal de la consulta.\n\n"
                # # SME_META_RULE_OP_VS_DEF (managed by artifacts/sme_pending/apply_sme_decisions.py)
        "═══ HEURÍSTICA META — antes de cualquier otra regla:\n\n"
        "El TEMA es el que OPERA, no el que DEFINE. Cuando una pregunta toca\n"
        "dos áreas, el tema es el área donde se EJECUTA la respuesta operativa,\n"
        "no el área donde se definen los conceptos involucrados. Ejemplos:\n"
        "  · 'Patrimonio alto pero pérdida → renta presuntiva' → opera en presuntiva (no patrimonio).\n"
        "  · 'Descuento del IVA en bienes de capital' → opera en descuentos de renta (no iva).\n"
        "  · 'Tarifa en zona franca' → opera en tarifas (no zonas_francas).\n"
        "  · 'Emplazamiento sobre IVA' → opera en procedimiento (no iva).\n\n"
        "═══ CATÁLOGO DE TEMAS (elige uno) — formato `N. key — label — definición`:\n\n"
        f"{taxonomy_block}\n\n"
        "REGLA POR DEFECTO — si la consulta abarca varios subtemas del mismo padre\n"
        "top-level, devuelve el PADRE. No fuerces un subtema cuando el contenido es\n"
        "transversal.\n\n"
        # # SME_NO_COLLAPSE_EXCEPTIONS (managed by artifacts/sme_pending/apply_sme_decisions.py)
        "EXCEPCIONES — los siguientes subtemas son consultados POR NOMBRE por contadores;\n"
        "NO los colapses al padre cuando la consulta los menciona explícita o\n"
        "implícitamente: `beneficio_auditoria`, `firmeza_declaraciones`.\n\n"
        "═══ REGLAS DURAS DE MUTUA EXCLUSIVIDAD (no son sugerencias):\n\n"
        f"{mutex_block}\n\n"
        "═══ FORMATO DE RESPUESTA — SOLO JSON válido:\n"
        '{"primary_topic":"topic_key", "secondary_topics":["topic_key", ...],\n'
        ' "confidence":0.0, "reason":"cita la regla/mutex que aplicaste"}\n\n'
        "Reglas operativas:\n"
        "- primary_topic DEBE ser exactamente una de las `key` del catálogo, o cadena vacía.\n"
        "- secondary_topics: 0–3 temas del catálogo, sin repetir primary_topic.\n"
        "- Si la consulta es ambigua, conserva requested_topic cuando exista.\n"
        "- Si no hay tema dominante y no hay requested_topic, primary_topic vacío + confidence baja.\n"
        "- No inventes keys fuera del catálogo.\n\n"
        f"Pais: {pais}\n"
        f"requested_topic: {requested_topic or 'none'}\n"
        f"{prior_topic_line}"
        f"consulta: {message}\n"
    )


def _safe_json_dict(raw: str) -> dict[str, Any]:
    cleaned = str(raw or "").strip()
    if not cleaned:
        return {}
    try:
        parsed = json.loads(cleaned)
        return dict(parsed) if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if not match:
            return {}
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}
        return dict(parsed) if isinstance(parsed, dict) else {}


def _classify_topic_with_llm(
    *,
    message: str,
    requested_topic: str | None,
    pais: str,
    runtime_config_path: Path,
    preserve_requested_topic_as_secondary: bool = True,
    conversation_state: dict[str, Any] | None = None,
) -> TopicRoutingResult | None:
    adapter, runtime = resolve_llm_adapter(runtime_config_path=runtime_config_path)
    if adapter is None:
        return None
    prompt = _build_classifier_prompt(
        message=message,
        requested_topic=requested_topic,
        pais=pais,
        conversation_state=conversation_state,
    )
    try:
        if hasattr(adapter, "generate_with_options"):
            result = adapter.generate_with_options(  # type: ignore[attr-defined]
                prompt,
                temperature=0.0,
                max_tokens=180,
                timeout_seconds=8.0,
            )
            raw_content = str((result or {}).get("content") or "").strip()
        else:
            raw_content = str(adapter.generate(prompt) or "").strip()
    except Exception:
        return None

    parsed = _safe_json_dict(raw_content)
    effective_topic = normalize_topic_key(str(parsed.get("primary_topic") or ""))
    if effective_topic not in _SUPPORTED_TOPICS:
        return None
    try:
        confidence = float(parsed.get("confidence"))
    except (TypeError, ValueError):
        confidence = 0.0
    if confidence < _LLM_CONFIDENCE_THRESHOLD:
        return None
    # Labor topic: never preserve renta as a secondary (see _build_rule_result
    # for full reasoning). Also drop any LLM-suggested secondaries that aren't
    # the labor primary itself — if the LLM thinks renta is a labor secondary,
    # the cross-domain fan-out re-pulls ET docs and reintroduces the leakage.
    if effective_topic == "laboral":
        secondary_topics: tuple[str, ...] = ()
    else:
        secondary_topics = _normalize_secondary_topics(
            parsed.get("secondary_topics") if isinstance(parsed.get("secondary_topics"), list) else (),
            requested_topic=requested_topic,
            effective_topic=effective_topic,
            preserve_requested_topic_as_secondary=preserve_requested_topic_as_secondary,
        )
    adjusted = effective_topic != requested_topic
    return TopicRoutingResult(
        requested_topic=requested_topic,
        effective_topic=effective_topic,
        secondary_topics=secondary_topics,
        topic_adjusted=adjusted,
        confidence=min(1.0, max(0.0, confidence)),
        reason=str(parsed.get("reason") or "llm_topic_classifier"),
        topic_notice=_build_topic_notice(effective_topic) if adjusted else None,
        mode="llm",
        llm_runtime=runtime,
    )


def resolve_chat_topic(
    *,
    message: str,
    requested_topic: str | None,
    pais: str = "colombia",
    runtime_config_path: Path | str | None = None,
    preserve_requested_topic_as_secondary: bool = True,
    conversation_state: dict[str, Any] | None = None,
) -> TopicRoutingResult:
    """Resolve the topic for a chat message.

    next_v4 §4 Level 2 — when ``conversation_state`` is supplied with a
    ``prior_topic``, the classifier prompt receives it as a soft hint AND
    a strict tiebreaker fires after the LLM verdict: if lexical scoring
    found nothing AND the LLM disagreed with prior_topic, the prior topic
    wins with a small confidence boost (capped to 0.85). Tiebreaker only.
    Never override a confident lexical signal pointing at a different topic.
    """
    normalized_requested = normalize_topic_key(requested_topic)
    rule_result = _resolve_rule_based_topic(
        message,
        normalized_requested,
        preserve_requested_topic_as_secondary=preserve_requested_topic_as_secondary,
    )
    if rule_result is not None:
        return rule_result

    prior_topic = (
        normalize_topic_key((conversation_state or {}).get("prior_topic"))
        if isinstance(conversation_state, dict)
        else None
    )
    if prior_topic not in _SUPPORTED_TOPICS:
        prior_topic = None

    if runtime_config_path is not None and _should_attempt_llm(message, normalized_requested):
        llm_result = _classify_topic_with_llm(
            message=message,
            requested_topic=normalized_requested,
            pais=pais,
            runtime_config_path=Path(runtime_config_path),
            preserve_requested_topic_as_secondary=preserve_requested_topic_as_secondary,
            conversation_state=conversation_state,
        )
        if llm_result is not None:
            # Soft prior tiebreaker. The plan binds this narrowly: trip only
            # when the LLM disagreed with prior_topic AND the message had no
            # dominant lexical signal (i.e. truly ambiguous from the rule
            # router's perspective). Confident lexical topic-switch signals
            # would have been caught by _resolve_rule_based_topic above; the
            # check here protects the rare case where _score_topic_keywords
            # had a non-empty bucket but didn't produce a dominant winner.
            if (
                prior_topic
                and llm_result.effective_topic != prior_topic
                and not _score_topic_keywords(message)
            ):
                boosted = min(0.85, max(_LLM_CONFIDENCE_THRESHOLD, llm_result.confidence) + 0.15)
                adjusted = prior_topic != normalized_requested
                return TopicRoutingResult(
                    requested_topic=normalized_requested,
                    effective_topic=prior_topic,
                    secondary_topics=(),
                    topic_adjusted=adjusted,
                    confidence=boosted,
                    reason="tiebreaker:prior_topic_from_conversation_state",
                    topic_notice=_build_topic_notice(prior_topic) if adjusted else None,
                    mode="prior_state_tiebreaker",
                    llm_runtime=llm_result.llm_runtime,
                )
            return llm_result

    if normalized_requested is None:
        scores = _score_topic_keywords(message)
        if scores:
            ranked = sorted(scores.items(), key=lambda item: int(item[1]["score"]), reverse=True)
            top_topic, top_data = ranked[0]
            top_score = int(top_data.get("score", 0) or 0)
            confidence = min(0.55, 0.18 + top_score * 0.06)
            return TopicRoutingResult(
                requested_topic=None,
                effective_topic=top_topic,
                secondary_topics=(),
                topic_adjusted=True,
                confidence=confidence,
                reason="fallback:auto_detected_from_keywords",
                topic_notice=_build_topic_notice(top_topic),
                mode="fallback",
            )
        # next_v4 §4 Level 2 — last-chance prior_topic fallback. When the LLM
        # adapter is unreachable AND lexical produced nothing AND the FE didn't
        # send requested_topic, prior_topic is the only structural signal we
        # have left. Keep confidence modest so downstream gates can still
        # abstain in extreme cases; this is wiring continuity, not authority.
        if prior_topic:
            return TopicRoutingResult(
                requested_topic=None,
                effective_topic=prior_topic,
                secondary_topics=(),
                topic_adjusted=True,
                confidence=0.5,
                reason="fallback:prior_topic_from_conversation_state",
                topic_notice=_build_topic_notice(prior_topic),
                mode="prior_state_fallback",
            )
        return TopicRoutingResult(
            requested_topic=None,
            effective_topic=None,
            secondary_topics=(),
            topic_adjusted=False,
            confidence=0.0,
            reason="fallback:no_topic_detected",
            topic_notice=None,
            mode="fallback",
        )

    return TopicRoutingResult(
        requested_topic=normalized_requested,
        effective_topic=normalized_requested,
        secondary_topics=(),
        topic_adjusted=False,
        confidence=0.0,
        reason="fallback:requested_topic_retained",
        topic_notice=None,
        mode="fallback",
    )
