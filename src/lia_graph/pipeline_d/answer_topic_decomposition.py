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
) -> list[tuple[str, int]]:
    """Return ranked list of (topic, article_count) for primary articles.

    A primary article's "topic" is the router topic if it is in the article's
    `secondary_topics`, else the first secondary topic, else the router topic
    as a fallback. Articles with no secondary topics contribute to a generic
    bucket keyed by the router topic.
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
    return counter.most_common()


def should_decompose(
    coherence: Mapping[str, Any],
    evidence: GraphEvidenceBundle,
    router_topic: str,
) -> bool:
    """True iff the gate would refuse AND we have enough primary articles to
    plausibly cover ≥2 domains (raw count threshold = 2).
    """
    if decomposition_mode() == "off":
        return False
    if not coherence.get("misaligned"):
        return False
    reason = (coherence.get("reason") or "").strip()
    if reason not in {"primary_off_topic", "chunks_off_topic"}:
        return False
    return len(evidence.primary_articles) >= 2 and bool(router_topic)


def framing_line(
    coherence: Mapping[str, Any],
    evidence: GraphEvidenceBundle,
    router_topic: str,
) -> str:
    """One-line preface so the reader knows the answer spans multiple domains."""
    groups = detect_topic_groups(evidence, router_topic)
    distinct = [t for t, _ in groups][:3]
    if len(distinct) < 2:
        # Fall back to router + dominant from coherence diag.
        dominant = (coherence.get("dominant_topic") or "").strip()
        if dominant and dominant != router_topic:
            distinct = [router_topic, dominant]
        else:
            distinct = [router_topic]
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


__all__ = [
    "decomposition_mode",
    "detect_topic_groups",
    "should_decompose",
    "framing_line",
    "diagnostics_payload",
]
