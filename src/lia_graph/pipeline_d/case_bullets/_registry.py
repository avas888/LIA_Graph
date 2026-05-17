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

Authoring sub-bullets (v17 follow-up, 2026-05-15)
-------------------------------------------------
The synthesis pipeline collapses any newline in a bullet to a single
space via ``answer_shared.append_unique`` and
``neutralize_non_imputative_language``. So a bullet containing
literal ``\\n  - sub`` will not render as nested markdown.

To author nested bullets, use the helper from
``pipeline_d.presentation``::

    from ..presentation import with_sub_bullets

    SPEC = CaseSpec(
        ...,
        bullets=(
            with_sub_bullets(
                "**Recargos (CST 159, 168, 179):**",
                (
                    "nocturno (21:00–06:00) **+ 35 %**",
                    "extra diurna **+ 25 %**",
                    "extra nocturna **+ 75 %**",
                ),
            ),
            "Single-line bullet without sub-items stays a plain string.",
        ),
        ...,
    )

Under the hood, ``with_sub_bullets`` joins the lead and the items with
``SUB_BULLET_TOKEN`` (a non-whitespace sentinel) so the bullet survives
every whitespace-collapse in the pipeline. ``render_bullet_section``
expands the token to ``\\n  - `` at the very last render step. Polish
is instructed to preserve the nested structure (point 5 of the
primary directive in ``answer_llm_polish._build_polish_prompt``).
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
    # v20 P4: explicit dotted norm_ids. When non-empty, supersedes
    # `anchor_articles` → planner uses these verbatim. When empty
    # (the default), the planner derives `et.art.<N>` from
    # `anchor_articles` — preserves the historical assumption that
    # every case_bullet anchors to the Estatuto Tributario. Set
    # `anchor_norm_ids=("cst.art.64", "ley.50.1990.art.64")` etc.
    # when a case needs to anchor outside the ET.
    anchor_norm_ids: tuple[str, ...] = ()


__all__ = ["CaseSpec"]
