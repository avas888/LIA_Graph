"""Phase 4 (v6) — defensive per-topic citation allow-list.

Ports the Contadores ``prompts/answer_policy_es.md`` mechanism: for a
fixed set of topics, any citation whose extracted ET article number is
not on the allow-list (and whose authority/family isn't allow-listed
either) is dropped as retrieval leakage. The dropped citations are
recorded in ``diagnostics["dropped_by_allowlist"]`` so the panel can
audit false positives.

Flag-gated via ``LIA_POLICY_CITATION_ALLOWLIST={off|enforce}``, default
``off``. Config-driven via ``config/citation_allow_list.json`` so adding
a topic doesn't need code changes.
"""

from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

# Matches "art. 516", "Art 516", "artículo 516", "art. 387-1", etc. The
# trailing ``[\-\d]*`` preserves hyphenated sub-articles (387-1, 114-1).
_ET_ARTICLE_RX = re.compile(
    r"\b(?:art\.?|art[ií]culo)\s*(\d+(?:-\d+)?)", re.IGNORECASE
)
_CONFIG_PATH_ENV = "LIA_CITATION_ALLOWLIST_CONFIG"


def allowlist_mode() -> str:
    # Default `enforce` 2026-04-25 per operator's "no off/shadow flags" directive.
    # Higher-risk flip than coherence_gate: not yet end-to-end verified per the
    # six-gate policy. Watch production for over-filtered citations; if accountants
    # report missing valid cites, revert to `off` and revisit verification.
    raw = (os.getenv("LIA_POLICY_CITATION_ALLOWLIST") or "enforce").strip().lower()
    return raw if raw in ("off", "enforce") else "enforce"


def _default_config_path() -> Path:
    override = os.getenv(_CONFIG_PATH_ENV)
    if override:
        return Path(override)
    # Repo root resolution mirrors how Makefile targets invoke Python:
    # cwd is the repo root, config/ sits alongside src/.
    return Path("config/citation_allow_list.json")


@lru_cache(maxsize=4)
def load_config(path: str | None = None) -> dict[str, Any]:
    target = Path(path) if path else _default_config_path()
    if not target.exists():
        return {"version": "none", "topics": {}}
    return json.loads(target.read_text(encoding="utf-8"))


def extract_et_article(citation) -> str | None:
    """Pull an ET article number out of a Citation's reference fields.

    Returns None if the citation doesn't reference an article (e.g., a
    circular or resolution without an article anchor).
    """
    for attr in ("legal_reference", "search_query", "source_label"):
        value = getattr(citation, attr, None) or ""
        if not value:
            continue
        match = _ET_ARTICLE_RX.search(value)
        if match:
            return match.group(1).lower()
    return None


def _citation_family(citation) -> str | None:
    """Citation family hint — authority, source_type, or tipo_de_documento.

    The allow-list entries use shorthand keys (e.g., CST, RESOLUCION_DIAN).
    """
    for attr in ("authority", "source_type", "tipo_de_documento"):
        value = (getattr(citation, attr, None) or "").strip()
        if value:
            return value.upper().replace(" ", "_")
    return None


def _citation_text_blob(citation) -> str:
    """Concatenated text from a citation's user-visible reference fields.

    Used by the non-ET ``allowed_norm_anchors`` check (SME §4.1): for
    topics whose authority isn't the Estatuto Tributario (laboral, NIIF,
    cambiario, datos, parafiscales), match canonical norm patterns like
    "CST art. 64" or "Decreto 1072 de 2015" against this text blob.
    """
    parts = []
    for attr in ("legal_reference", "search_query", "source_label"):
        value = getattr(citation, attr, None) or ""
        if value:
            parts.append(str(value))
    return " ".join(parts).lower()


def _is_allowed(citation, rule: dict[str, Any]) -> bool:
    """True iff the citation passes the topic's allow rule.

    A citation is allowed when any of the following match:
      - its ET article number is in ``allowed_et_articles`` (SME ET-centric);
      - its family/authority matches ``allowed_article_families``;
      - the citation's reference text contains any ``allowed_norm_anchors``
        pattern (SME §4.1 — for non-ET topics like laboral/NIIF/cambiario).

    Citations with no match against any configured rule are dropped.
    If the topic declares none of the three rule-types, everything is kept
    (conservative fallback; the rule is effectively disabled for that topic).
    """
    allowed_articles = {str(a).lower() for a in (rule.get("allowed_et_articles") or ())}
    allowed_families = {
        str(f).upper().replace(" ", "_") for f in (rule.get("allowed_article_families") or ())
    }
    allowed_norm_anchors = tuple(str(n).lower() for n in (rule.get("allowed_norm_anchors") or ()))

    article = extract_et_article(citation)
    if article and article in allowed_articles:
        return True

    family = _citation_family(citation)
    if family:
        for allowed in allowed_families:
            if family == allowed or family.startswith(allowed + "_") or allowed in family:
                return True

    if allowed_norm_anchors:
        text_blob = _citation_text_blob(citation)
        if text_blob:
            for anchor in allowed_norm_anchors:
                if anchor and anchor in text_blob:
                    return True

    # No article match, no family match, no norm-anchor match.
    if article is None and not allowed_families and not allowed_norm_anchors:
        # Topic has no rules at all → keep conservatively.
        return True
    return False


def filter_citations(
    citations: Iterable,
    topic: str | None,
    mode: str | None = None,
    *,
    config_path: str | None = None,
) -> tuple[tuple, list[dict[str, Any]]]:
    """Return (kept_citations, dropped_diagnostics).

    In ``off`` mode returns the citations unchanged and an empty drops
    list. In ``enforce`` mode, filters per the topic's allow rule; a
    citation that fails ``_is_allowed`` lands in the dropped list with a
    reason string for observability.
    """
    resolved_mode = (mode or allowlist_mode()).strip().lower()
    citations_tuple = tuple(citations)
    if resolved_mode != "enforce" or not topic:
        return citations_tuple, []
    config = load_config(config_path)
    rule = (config.get("topics") or {}).get(topic)
    if not rule:
        return citations_tuple, []

    kept: list = []
    dropped: list[dict[str, Any]] = []
    for citation in citations_tuple:
        if _is_allowed(citation, rule):
            kept.append(citation)
            continue
        dropped.append(
            {
                "article": extract_et_article(citation),
                "family": _citation_family(citation),
                "topic": topic,
                "reason": "not_in_allow_list",
                "legal_reference": getattr(citation, "legal_reference", None),
            }
        )
    return tuple(kept), dropped


__all__ = [
    "allowlist_mode",
    "extract_et_article",
    "filter_citations",
    "load_config",
]
