"""Cross-encoder reranker hook for pipeline_d (shadow / live).

Structural backlog item #2 from `docs/next/structuralwork_v1_SEENOW.md`.

Modes
-----
- ``off``     (default): no-op. Returned evidence and diagnostics unchanged
  except for ``{"mode": "off"}``.
- ``shadow``: call the sidecar, compute the reranked top-K order, log the
  delta against the hybrid top-K — but serve hybrid order unchanged.
  This is the first production step: it earns trust before it steers.
- ``live``:   call the sidecar and reorder ``primary_articles`` by rerank
  score (stable tiebreak on hybrid position). Falls back to hybrid order
  if the sidecar errors, with ``reranker_fallback=true`` in diagnostics.

Env vars
--------
``LIA_RERANKER_MODE``       off | shadow | live       (default: off)
``LIA_RERANKER_ENDPOINT``   base URL of the sidecar   (e.g. http://rr:8080)
``LIA_RERANKER_TOPK``       how many hybrid candidates to rerank (default: 10)
``LIA_RERANKER_TIMEOUT_MS`` sidecar call timeout in ms (default: 1500)

Sidecar contract
----------------
``POST {endpoint}/rerank``::

    { "query": "<user query>",
      "candidates": [{"id": "<node_key>", "text": "<excerpt>"}, ...] }

Response::

    { "scores": [<float>, ...] }   # same order and length as candidates

Any sidecar error — connection, timeout, malformed payload, length
mismatch — is non-fatal. The pipeline serves hybrid order and logs
``reranker_fallback=true`` so operators can distinguish "rerank live and
healthy" from "rerank nominally on but silently failing."
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Callable, Sequence

from .contracts import GraphEvidenceBundle, GraphEvidenceItem


VALID_MODES: frozenset[str] = frozenset({"off", "shadow", "live"})

_MODE_ENV = "LIA_RERANKER_MODE"
_ENDPOINT_ENV = "LIA_RERANKER_ENDPOINT"
_TOPK_ENV = "LIA_RERANKER_TOPK"
_TIMEOUT_ENV = "LIA_RERANKER_TIMEOUT_MS"
_DEFAULT_TOPK = 10
_DEFAULT_TIMEOUT_MS = 1500


Scorer = Callable[[str, Sequence[GraphEvidenceItem]], list[float]]
"""Pluggable scoring callable. Production uses the HTTP sidecar; tests pass
a pure-Python scorer to exercise the shadow/live branches without a server.
"""


def current_mode() -> str:
    # Default `live` 2026-04-25 (was `off`) per "no off flags" directive.
    # Already at `live` in launcher since 2026-04-22; this aligns the Python
    # default with the launcher + Railway env. Adapter falls back to hybrid when
    # LIA_RERANKER_ENDPOINT is unset, so served answers are unchanged until the
    # bge-reranker-v2-m3 sidecar is deployed — flag tracks methodology, not
    # behavior, until then.
    raw = str(os.getenv(_MODE_ENV, "live") or "").strip().lower()
    return raw if raw in VALID_MODES else "live"


def _topk() -> int:
    try:
        value = int(os.getenv(_TOPK_ENV) or _DEFAULT_TOPK)
    except ValueError:
        return _DEFAULT_TOPK
    return value if value > 0 else _DEFAULT_TOPK


def _timeout_seconds() -> float:
    try:
        ms = int(os.getenv(_TIMEOUT_ENV) or _DEFAULT_TIMEOUT_MS)
    except ValueError:
        ms = _DEFAULT_TIMEOUT_MS
    return max(0.1, ms / 1000.0)


def _hybrid_candidates(evidence: GraphEvidenceBundle) -> list[GraphEvidenceItem]:
    return list(evidence.primary_articles) + list(evidence.connected_articles)


def _candidate_text(item: GraphEvidenceItem) -> str:
    # Prefer the excerpt (what the planner/retriever already selected as
    # the article's most salient slice). Fall back to title so a candidate
    # with a blank excerpt still contributes signal, not a blank string.
    return (item.excerpt or item.title or "").strip()


def _jaccard(a: Sequence[str], b: Sequence[str]) -> float:
    sa, sb = set(a), set(b)
    union = sa | sb
    if not union:
        return 1.0
    return round(len(sa & sb) / len(union), 4)


def _fetch_scores_http(
    *,
    endpoint: str,
    query: str,
    candidates: Sequence[GraphEvidenceItem],
    timeout_s: float,
) -> list[float]:
    payload = json.dumps(
        {
            "query": query,
            "candidates": [
                {"id": item.node_key, "text": _candidate_text(item)}
                for item in candidates
            ],
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        url=endpoint.rstrip("/") + "/rerank",
        data=payload,
        headers={"content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:  # noqa: S310
        body = resp.read().decode("utf-8")
    data = json.loads(body)
    scores = data.get("scores")
    if not isinstance(scores, list) or len(scores) != len(candidates):
        raise ValueError(
            f"reranker returned {len(scores) if isinstance(scores, list) else 'non-list'}"
            f" scores for {len(candidates)} candidates"
        )
    return [float(s) for s in scores]


def rerank_evidence_bundle(
    *,
    query: str,
    evidence: GraphEvidenceBundle,
    scorer: Scorer | None = None,
) -> tuple[GraphEvidenceBundle, dict[str, Any]]:
    """Maybe rerank ``evidence`` and return ``(bundle, diagnostics)``.

    ``scorer`` is a test seam — in production ``None`` triggers the HTTP
    path against ``LIA_RERANKER_ENDPOINT``. The returned bundle is the
    input unchanged in ``off`` and ``shadow`` modes; in ``live`` mode
    ``primary_articles`` are reordered by reranker score.
    """
    mode = current_mode()
    diagnostics: dict[str, Any] = {"mode": mode}

    if mode == "off":
        return evidence, diagnostics

    candidates = _hybrid_candidates(evidence)
    top_k = _topk()
    hybrid_top_keys = tuple(item.node_key for item in candidates[:top_k])
    diagnostics["hybrid_top_keys"] = list(hybrid_top_keys)
    diagnostics["candidate_count"] = len(candidates)

    if not candidates:
        diagnostics.update({"reranker_fallback": True, "reason": "no_candidates"})
        return evidence, diagnostics

    endpoint = os.getenv(_ENDPOINT_ENV, "").strip()
    if scorer is None and not endpoint:
        diagnostics.update({"reranker_fallback": True, "reason": "endpoint_not_configured"})
        return evidence, diagnostics

    try:
        if scorer is not None:
            scores = list(scorer(query, candidates))
        else:
            scores = _fetch_scores_http(
                endpoint=endpoint,
                query=query,
                candidates=candidates,
                timeout_s=_timeout_seconds(),
            )
    except (urllib.error.URLError, ValueError, json.JSONDecodeError, TimeoutError, OSError) as exc:
        diagnostics.update(
            {
                "reranker_fallback": True,
                "reason": "sidecar_error",
                "error": type(exc).__name__,
            }
        )
        return evidence, diagnostics

    if len(scores) != len(candidates):
        diagnostics.update(
            {
                "reranker_fallback": True,
                "reason": "score_length_mismatch",
            }
        )
        return evidence, diagnostics

    # Stable sort: higher score first, break ties by original hybrid rank.
    ranked_pairs = sorted(
        enumerate(candidates),
        key=lambda pair: (-scores[pair[0]], pair[0]),
    )
    reranked_top_keys = tuple(item.node_key for _, item in ranked_pairs[:top_k])
    diagnostics["reranker_top_keys"] = list(reranked_top_keys)
    diagnostics["delta_first_key_change"] = bool(
        hybrid_top_keys
        and reranked_top_keys
        and hybrid_top_keys[0] != reranked_top_keys[0]
    )
    diagnostics["delta_swap_count"] = sum(
        1 for a, b in zip(hybrid_top_keys, reranked_top_keys) if a != b
    )
    diagnostics["delta_jaccard"] = _jaccard(hybrid_top_keys, reranked_top_keys)

    if mode == "shadow":
        return evidence, diagnostics

    # Live: reorder primary first, connected second, preserving group
    # membership — primary = seeds from the planner, connected = graph
    # neighbours. Mixing them would erase that semantic distinction.
    primary_keys = {item.node_key for item in evidence.primary_articles}
    reordered_primary = tuple(
        item for _, item in ranked_pairs if item.node_key in primary_keys
    )
    reordered_connected = tuple(
        item for _, item in ranked_pairs if item.node_key not in primary_keys
    )
    new_evidence = GraphEvidenceBundle(
        primary_articles=reordered_primary,
        connected_articles=reordered_connected,
        related_reforms=evidence.related_reforms,
        support_documents=evidence.support_documents,
        citations=evidence.citations,
        diagnostics=evidence.diagnostics,
    )
    return new_evidence, diagnostics


__all__ = [
    "VALID_MODES",
    "Scorer",
    "current_mode",
    "rerank_evidence_bundle",
]
