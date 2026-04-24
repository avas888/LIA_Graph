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
    raw = (os.getenv("LIA_POLICY_CITATION_ALLOWLIST") or "off").strip().lower()
    return raw if raw in ("off", "enforce") else "off"


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


def _is_allowed(citation, rule: dict[str, Any]) -> bool:
    """True iff the citation passes the topic's allow rule.

    A citation is allowed when EITHER its ET article number is in the
    topic's allowed_et_articles list OR its family/authority matches one
    of allowed_article_families. Citations with neither an ET article
    match nor a family match are dropped.
    """
    allowed_articles = {str(a).lower() for a in (rule.get("allowed_et_articles") or ())}
    allowed_families = {
        str(f).upper().replace(" ", "_") for f in (rule.get("allowed_article_families") or ())
    }
    article = extract_et_article(citation)
    if article and article in allowed_articles:
        return True
    family = _citation_family(citation)
    if family:
        # Allow exact match or prefix match (RESOLUCION_DIAN_165 matches RESOLUCION_DIAN)
        for allowed in allowed_families:
            if family == allowed or family.startswith(allowed + "_") or allowed in family:
                return True
    # No ET article and no family match → drop as leakage.
    if article is None and not allowed_families:
        # Topic has no family allow-list and the citation has no article
        # reference → nothing to check against; keep conservatively.
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
