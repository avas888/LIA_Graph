"""Schema for the case-bullet registry.

A :class:`CaseSpec` collects everything one case topic needs to wire:

* ``name`` — short slug, used for trace + tests.
* ``detector`` — pure ``Callable[[str], bool]`` from
  ``pipeline_d.case_detectors``.
* ``bullets`` — verbatim ``Recomendaciones Prácticas`` bullets, in the
  exact order they should be appended. Each bullet ≤ ~280 chars per
  ``clean_support_line_for_answer`` truncation guarantee.
* ``keywords`` — off-topic-filter whitelist tokens; if a generated
  bullet does not contain any of these, it is dropped before render
  when ``detector`` fires (see ``answer_synthesis_sections._filter_offtopic_bullets_for_case``).
* ``anchor_articles`` — ET article ids the planner pulls explicitly
  when ``detector`` fires (the load-bearing field for the
  case-anchor registry).
* ``search_queries`` — text-search-half phrases the planner adds to
  ``hybrid_search`` when ``detector`` fires.
* ``source_label`` — diagnostic source tag, surfaces in
  ``planner.diagnostics.anchor_sources``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class CaseSpec:
    name: str
    detector: Callable[[str], bool]
    bullets: tuple[str, ...]
    keywords: tuple[str, ...]
    anchor_articles: tuple[str, ...]
    search_queries: tuple[str, ...]
    source_label: str


__all__ = ["CaseSpec"]
