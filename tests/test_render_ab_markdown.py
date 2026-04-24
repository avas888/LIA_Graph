"""Tests for scripts/evaluations/render_ab_markdown.py — pure renderer.

Locks the §5 Phase 2 contract of docs/quality_tests/evaluacion_ingestionfixtask_v1.md:
  * Each question block carries bold mode labels.
  * Answer markdown is preserved verbatim.
  * Each block ends with a YAML `verdict:` placeholder.
  * Failed rows (prior_error / new_error) render an [ERROR] banner, not
    a crash.
  * Final Aggregate block is present.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


_SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "scripts"
    / "evaluations"
    / "render_ab_markdown.py"
)
_spec = importlib.util.spec_from_file_location("render_ab_markdown", _SCRIPT)
assert _spec is not None and _spec.loader is not None
renderer = importlib.util.module_from_spec(_spec)
sys.modules["render_ab_markdown"] = renderer
_spec.loader.exec_module(renderer)  # type: ignore[union-attr]


def _mode_block(mode: str, answer: str) -> dict:
    return {
        "mode": mode,
        "env_flag_value": "off" if mode == "prior" else "on",
        "answer_markdown": answer,
        "retrieval_backend": "supabase_hybrid",
        "graph_backend": "falkor_live",
        "primary_article_count": 5,
        "connected_article_count": 2,
        "related_reform_count": 1,
        "seed_article_keys": ["ET_ART_107", "ET_ART_771_2"],
        "tema_first_mode": "off" if mode == "prior" else "on",
        "tema_first_topic_key": "declaracion_renta",
        "tema_first_anchor_count": 0 if mode == "prior" else 12,
        "planner_query_mode": "standard",
        "effective_topic": "declaracion_renta",
        "trace_id": f"tr_{mode}_x",
        "wall_ms": 1234,
    }


def _row(qid: str = "Q1", *, with_errors: bool = False) -> dict:
    row = {
        "qid": qid,
        "type": "S",
        "query_shape": "single",
        "macro_area": "a_renta_pj",
        "query": "¿Cuánto puede deducir en costos?",
        "expected_topic": "declaracion_renta",
        "expected_subtopic": "deducciones_art107_renta",
        "expected_article_keys": ["ET_ART_107", "ET_ART_771_2"],
        "sub_questions": None,
    }
    if with_errors:
        row["prior_error"] = {
            "error": "RuntimeError: boom",
            "traceback": "Traceback …\nRuntimeError: boom",
        }
        row["new_error"] = {
            "error": "TimeoutError",
            "traceback": "Traceback …\nTimeoutError",
        }
    else:
        row["prior"] = _mode_block(
            "prior", "### Answer A (prior)\n\nDeducción conforme Art. 107 ET."
        )
        row["new"] = _mode_block(
            "new", "### Answer B (new)\n\nMismo Art. 107 pero con contexto sector."
        )
    return row


def _manifest() -> dict:
    return {
        "manifest_tag": "v5_dry_run",
        "run_started_at_utc": "2026-04-24T12:00:00+00:00",
        "run_completed_at_utc": "2026-04-24T12:25:00+00:00",
        "run_started_at_bogota": "2026-04-24 7:00:00 AM",
        "run_completed_at_bogota": "2026-04-24 7:25:00 AM",
        "git_commit_sha": "abc1234",
        "falkor_baseline": {
            "TopicNode": 65,
            "TEMA_edges": 2400,
            "ArticleNode": 9160,
            "SubTopicNode": 84,
        },
    }


# ── Tests ─────────────────────────────────────────────────────────────────


def test_render_minimal_jsonl_contains_bold_mode_labels() -> None:
    md = renderer.render_md([_row()], _manifest())
    assert "**[PRIOR MODE]**" in md
    assert "**[NEW MODE]**" in md


def test_render_preserves_answer_markdown_verbatim() -> None:
    md = renderer.render_md([_row()], _manifest())
    assert "### Answer A (prior)" in md
    assert "Deducción conforme Art. 107 ET." in md
    assert "### Answer B (new)" in md
    assert "Mismo Art. 107 pero con contexto sector." in md


def test_render_emits_verdict_placeholder_per_question() -> None:
    rows = [_row("Q1"), _row("Q2"), _row("Q3")]
    md = renderer.render_md(rows, _manifest())
    # One YAML verdict placeholder line per question (anchored at column 0).
    verdict_lines = [
        ln for ln in md.splitlines() if ln.startswith("verdict:")
    ]
    assert len(verdict_lines) == 3, f"expected 3 YAML verdict placeholders, got {len(verdict_lines)}"
    # The allowed-value legend appears in the preamble (panel instructions).
    assert "new_better | prior_better | tie | both_wrong | need_clarification" in md


def test_render_skips_failed_rows_with_error_banner() -> None:
    md = renderer.render_md([_row("Q1", with_errors=True)], _manifest())
    assert "**[ERROR]**" in md
    assert "RuntimeError: boom" in md
    assert "TimeoutError" in md
    # Answer-markdown keys from the success path should NOT appear.
    assert "Deducción conforme Art. 107 ET." not in md


def test_render_aggregate_section_present() -> None:
    md = renderer.render_md([_row("Q1")], _manifest())
    assert "## Aggregate (filled by operator after panel review)" in md
    for k in (
        "new_better:",
        "prior_better:",
        "tie:",
        "both_wrong:",
        "need_clarification:",
        "decision:",
        "signed_off_by:",
    ):
        assert k in md, f"aggregate block missing key {k!r}"


def test_render_is_deterministic_on_same_input() -> None:
    rows = [_row("Q1"), _row("Q2")]
    a = renderer.render_md(rows, _manifest())
    b = renderer.render_md(rows, _manifest())
    assert a == b, "renderer must be byte-identical on repeated calls"


def test_render_preamble_includes_falkor_baseline() -> None:
    md = renderer.render_md([_row()], _manifest())
    assert "Falkor baseline" in md
    assert "TopicNode 65" in md
    assert "TEMA edges 2400" in md
