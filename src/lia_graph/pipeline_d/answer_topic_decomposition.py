"""v23 P1 — Topic-Gate Decomposition (G1).

When the coherence gate would refuse on `primary_off_topic` /
`chunks_off_topic` (router topic disagrees with retrieved articles' dominant
topic), instead of returning the refusal text, prepend a framing notice and
let normal synthesis + polish produce a substantive answer covering the
multi-domain question.

The audit (2026-05-17) showed 4 of 10 questions (Q1/Q3/Q6/Q8) refused with
"reformula la consulta" — all four were legitimate multi-domain accountant
questions (e.g. "documento soporte facturación electrónica vs deducibilidad").
The retrieved articles had real evidence; the gate just disagreed with the
router classifier's single-topic verdict.

This module is the minimum-viable decomposition path: skip refusal, retain
evidence, mark the answer with a framing line so the reader understands the
answer spans multiple domains. Heavier per-topic synthesis sectioning is
deferred to v24 if needed — v23's audit criterion is "no refusal", which
this closes without re-orchestrating synthesis.

Flag-gated by ``LIA_TOPIC_DECOMPOSITION_MODE={off,shadow,enforce}``,
default ``enforce`` per `project_beta_riskforward_flag_stance`.
"""

from __future__ import annotations

import os
from collections import Counter
from typing import Any, Mapping, Sequence

from .contracts import GraphEvidenceBundle, GraphEvidenceItem


_TOPIC_DISPLAY_NAMES: dict[str, str] = {
    "facturacion_electronica": "facturación electrónica",
    "deducibilidad_renta": "deducibilidad en renta",
    "iva_periodicidad": "periodicidad de IVA",
    "iva": "IVA",
    "retencion_fuente": "retención en la fuente",
    "retencion_fuente_general": "retención en la fuente",
    "nomina": "nómina",
    "nomina_electronica": "nómina electrónica",
    "auxilio_transporte": "auxilio de transporte",
    "regimen_simple": "Régimen Simple",
    "ica": "ICA",
    "inc": "INC",
    "rub": "RUB",
    "beneficiario_final": "beneficiarios finales",
    "regimen_cambiario": "régimen cambiario",
    "informacion_exogena": "información exógena",
    "calendario_obligaciones": "calendario de obligaciones",
    "niif_pymes": "NIIF para Pymes",
    "deterioro_cartera": "deterioro de cartera",
    "activos_fijos": "activos fijos",
    "depreciacion": "depreciación",
    "iva_descontable": "IVA descontable",
    "revisor_fiscal": "revisor fiscal",
    "obligaciones_formales": "obligaciones formales",
    "declaracion_renta": "renta",
    "costos_deducciones_renta": "costos y deducciones en renta",
}


def decomposition_mode() -> str:
    raw = (os.getenv("LIA_TOPIC_DECOMPOSITION_MODE") or "enforce").strip().lower()
    return raw if raw in ("off", "shadow", "enforce") else "enforce"


def _display(topic: str) -> str:
    return _TOPIC_DISPLAY_NAMES.get(topic, topic.replace("_", " "))


def detect_topic_groups(
    evidence: GraphEvidenceBundle,
    router_topic: str,
    *,
    drop_off_topic: bool = True,
) -> list[tuple[str, int]]:
    """Return ranked list of (topic, article_count) for primary articles.

    A primary article's "topic" is the router topic if it is in the article's
    `secondary_topics`, else the first secondary topic, else the router topic
    as a fallback. Articles with no secondary topics contribute to a generic
    bucket keyed by the router topic.

    fix_v25_may.md P11 — when ``drop_off_topic`` is True (default), groups
    whose topic is neither the router topic nor in the
    ``compatible_doc_topics`` allowlist for the router topic are dropped.
    The audit Q1 was polluted because the decomposition rendered a
    ``tarifas_renta_y_ttd`` section (Art. 240-1 ET zona franca) alongside
    the legitimate ``costos_deducciones_renta`` content; the off-topic
    group should never make it into the answer.
    """
    counter: Counter[str] = Counter()
    for item in evidence.primary_articles:
        secondaries = tuple(getattr(item, "secondary_topics", ()) or ())
        if router_topic in secondaries:
            counter[router_topic] += 1
        elif secondaries:
            counter[secondaries[0]] += 1
        else:
            counter[router_topic] += 1

    if not drop_off_topic or not router_topic:
        return counter.most_common()

    try:
        from .compatible_doc_topics import get_compatible_topics
        allowed = {router_topic} | set(get_compatible_topics(router_topic) or ())
    except Exception:  # noqa: BLE001 - allowlist must never break decomposition
        return counter.most_common()

    kept = Counter({t: c for t, c in counter.items() if t in allowed})
    # If filtering wiped out every group (all primary articles are off-topic),
    # fall back to the unfiltered set so we still produce *some* answer.
    if not kept:
        return counter.most_common()
    return kept.most_common()


def effective_router_topic(
    coherence: Mapping[str, Any],
    router_topic_hint: str,
) -> str:
    """Pick the most authoritative router topic available.

    `request.topic` is empty when query-decomposition fan-out is active
    (the parent topic is unset; per-sub-question topics are set on the
    fan-out children). The coherence dict's `router_topic` field is set
    on every coherence detection — including the merged-fanout
    `representative` shape — so it's the right source of truth for the
    bypass / framing decision.
    """
    explicit = (router_topic_hint or "").strip()
    if explicit:
        return explicit
    return str(coherence.get("router_topic") or "").strip()


def should_decompose(
    coherence: Mapping[str, Any],
    evidence: GraphEvidenceBundle,
    router_topic: str,
) -> bool:
    """True iff the coherence gate would refuse AND there is at least one
    primary article to anchor a substantive answer. The audit's Q1/Q3/Q6/Q8
    were refused on `primary_off_topic` even when the retrieved evidence
    was real and accountant-useful — refusing helps no one. Threshold is
    deliberately loose: 1 primary article + non-empty effective router
    topic (resolved against the coherence dict so fan-out queries with
    empty request.topic still trigger the bypass).
    """
    if decomposition_mode() == "off":
        return False
    if not coherence.get("misaligned"):
        return False
    reason = (coherence.get("reason") or "").strip()
    if reason not in {"primary_off_topic", "chunks_off_topic"}:
        return False
    effective = effective_router_topic(coherence, router_topic)
    return len(evidence.primary_articles) >= 1 and bool(effective)


def framing_line(
    coherence: Mapping[str, Any],
    evidence: GraphEvidenceBundle,
    router_topic: str,
) -> str:
    """One-line preface so the reader knows the answer spans multiple domains."""
    effective = effective_router_topic(coherence, router_topic)
    groups = detect_topic_groups(evidence, effective)
    distinct = [t for t, _ in groups][:3]
    if len(distinct) < 2:
        # Fall back to router + dominant from coherence diag.
        dominant = (coherence.get("dominant_topic") or "").strip()
        if dominant and dominant != effective:
            distinct = [effective, dominant]
        else:
            distinct = [effective] if effective else []
    if not distinct:
        return ""
    pretty = ", ".join(_display(t) for t in distinct)
    return (
        f"La consulta toca varios ámbitos ({pretty}). "
        "Respondo cubriendo lo aplicable a cada uno con la evidencia disponible.\n\n"
    )


def diagnostics_payload(
    coherence: Mapping[str, Any],
    evidence: GraphEvidenceBundle,
    router_topic: str,
    *,
    applied: bool,
) -> dict[str, Any]:
    groups = detect_topic_groups(evidence, router_topic) if applied else []
    return {
        "topic_decomposition_applied": bool(applied),
        "topic_decomposition_mode": decomposition_mode(),
        "topic_decomposition_router_topic": router_topic or None,
        "topic_decomposition_groups": [
            {"topic": t, "primary_article_count": int(c)} for t, c in groups
        ],
        "topic_decomposition_dominant_from_coherence": coherence.get("dominant_topic"),
        "topic_decomposition_coherence_reason": coherence.get("reason"),
        "topic_decomposition_section_count": len(groups),
    }


def _article_topic_or_router(item, router_topic: str) -> str:
    """Apply the same topic-resolution rule detect_topic_groups uses."""
    secondaries = tuple(getattr(item, "secondary_topics", ()) or ())
    if router_topic in secondaries:
        return router_topic
    if secondaries:
        return secondaries[0]
    return router_topic


def filter_off_topic_articles(
    evidence: GraphEvidenceBundle,
    router_topic: str,
) -> tuple[GraphEvidenceBundle, dict[str, Any]]:
    """fix_v25_may.md P11 — drop primary_articles whose resolved topic is
    neither the router topic nor in the ``compatible_doc_topics`` allowlist.

    Returns ``(filtered_evidence, diag)``. ``diag`` carries:
      - ``primary_in`` / ``primary_kept`` / ``primary_dropped`` counts
      - ``dropped_topics`` — Counter-style list of (topic, count) for the
        topics that lost articles
      - ``dropped_keys`` — first 10 node_keys of dropped items (diagnostic
        only)

    If filtering would wipe out every primary article, the function falls
    back to the unfiltered evidence (we still need *some* anchor to answer).
    """
    primary = list(evidence.primary_articles or ())
    diag: dict[str, Any] = {
        "primary_in": len(primary),
        "primary_kept": len(primary),
        "primary_dropped": 0,
        "dropped_topics": [],
        "dropped_keys": [],
    }
    if not primary or not router_topic:
        return evidence, diag

    try:
        from .compatible_doc_topics import get_compatible_topics
        allowed = {router_topic} | set(get_compatible_topics(router_topic) or ())
    except Exception:  # noqa: BLE001
        return evidence, diag

    kept: list = []
    dropped_topic_counter: Counter[str] = Counter()
    dropped_keys: list[str] = []
    for item in primary:
        topic = _article_topic_or_router(item, router_topic)
        if topic in allowed:
            kept.append(item)
        else:
            dropped_topic_counter[topic] += 1
            key = str(getattr(item, "node_key", "") or "")[:80]
            if key:
                dropped_keys.append(key)

    if not kept:
        # Don't leave the answer without an anchor; degrade to the original
        # set and let synthesis run on it. Caller sees the diag to know we
        # would have filtered everything out.
        diag["filter_skipped_reason"] = "would_drop_all"
        diag["primary_dropped"] = 0
        diag["dropped_topics"] = [
            {"topic": t, "count": int(c)} for t, c in dropped_topic_counter.most_common()
        ]
        diag["dropped_keys"] = dropped_keys[:10]
        return evidence, diag

    diag["primary_kept"] = len(kept)
    diag["primary_dropped"] = len(primary) - len(kept)
    diag["dropped_topics"] = [
        {"topic": t, "count": int(c)} for t, c in dropped_topic_counter.most_common()
    ]
    diag["dropped_keys"] = dropped_keys[:10]

    filtered = GraphEvidenceBundle(
        primary_articles=tuple(kept),
        connected_articles=evidence.connected_articles,
        related_reforms=evidence.related_reforms,
        support_documents=evidence.support_documents,
    )
    return filtered, diag


__all__ = [
    "decomposition_mode",
    "detect_topic_groups",
    "should_decompose",
    "framing_line",
    "filter_off_topic_articles",
    "diagnostics_payload",
]
