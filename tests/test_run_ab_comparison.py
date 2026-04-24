"""Tests for scripts/evaluations/run_ab_comparison.py — A/B launcher.

Uses a fake `run_pipeline_d` that reads ``os.environ["LIA_TEMA_FIRST_RETRIEVAL"]``
and returns a deterministic response whose answer_markdown encodes the env
value. This lets tests assert the launcher toggles the flag in the right
order without running real retrieval.

Covers §5 Phase 3 contract in docs/quality_tests/evaluacion_ingestionfixtask_v1.md.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import types
from pathlib import Path

import pytest


_SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "scripts"
    / "evaluations"
    / "run_ab_comparison.py"
)
_spec = importlib.util.spec_from_file_location("run_ab_comparison", _SCRIPT)
assert _spec is not None and _spec.loader is not None
launcher = importlib.util.module_from_spec(_spec)
sys.modules["run_ab_comparison"] = launcher
_spec.loader.exec_module(launcher)  # type: ignore[union-attr]


# ── Fake pipeline ────────────────────────────────────────────────────────


class _FakeResponse:
    def __init__(self, *, answer: str, diag: dict, trace: str) -> None:
        self.answer_markdown = answer
        self.diagnostics = diag
        self.trace_id = trace


class _FakeRouting:
    effective_topic = "declaracion_renta"
    requested_topic = None
    secondary_topics = ()
    topic_adjusted = False
    topic_notice = None
    reason = None
    confidence = 0.9


def _install_fake_pipeline(monkeypatch: pytest.MonkeyPatch, calls: list[dict]) -> None:
    """Stub out the three heavy imports the launcher performs lazily inside
    `_invoke_pipeline`. The fake records each call's env-flag value so
    tests can verify toggling order.
    """
    fake_pc = types.ModuleType("lia_graph.pipeline_c.contracts")

    class _PipelineCRequest:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    fake_pc.PipelineCRequest = _PipelineCRequest  # type: ignore[attr-defined]

    fake_pd = types.ModuleType("lia_graph.pipeline_d")

    def _run_pipeline_d(request):
        env_val = os.environ.get("LIA_TEMA_FIRST_RETRIEVAL", "<unset>")
        calls.append({"env": env_val, "query": request.message})
        return _FakeResponse(
            answer=f"answer for env={env_val}: {request.message}",
            diag={
                "retrieval_backend": "fake",
                "graph_backend": "fake",
                "primary_article_count": 1,
                "connected_article_count": 0,
                "related_reform_count": 0,
                "seed_article_keys": ["FAKE_KEY"],
                "tema_first_mode": env_val,
                "tema_first_topic_key": "declaracion_renta",
                "tema_first_anchor_count": 3 if env_val == "on" else 0,
                "planner_query_mode": "standard",
            },
            trace=f"tr_{env_val}",
        )

    fake_pd.run_pipeline_d = _run_pipeline_d  # type: ignore[attr-defined]

    fake_router = types.ModuleType("lia_graph.topic_router")

    def _resolve_chat_topic(*, message, requested_topic, pais):
        return _FakeRouting()

    fake_router.resolve_chat_topic = _resolve_chat_topic  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "lia_graph.pipeline_c.contracts", fake_pc)
    monkeypatch.setitem(sys.modules, "lia_graph.pipeline_d", fake_pd)
    monkeypatch.setitem(sys.modules, "lia_graph.topic_router", fake_router)


def _write_gold(tmp_path: Path, rows: list[dict]) -> Path:
    p = tmp_path / "gold.jsonl"
    p.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )
    return p


# ── Tests ────────────────────────────────────────────────────────────────


def test_launcher_toggles_env_off_then_on_per_question(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[dict] = []
    _install_fake_pipeline(monkeypatch, calls)
    monkeypatch.delenv("LIA_TEMA_FIRST_RETRIEVAL", raising=False)

    gold = _write_gold(
        tmp_path,
        [
            {
                "qid": "Q1",
                "type": "S",
                "query_shape": "single",
                "macro_area": "a_renta_pj",
                "initial_question_es": "first?",
                "expected_topic": "declaracion_renta",
            },
            {
                "qid": "Q2",
                "type": "S",
                "query_shape": "single",
                "macro_area": "a_iva",
                "initial_question_es": "second?",
                "expected_topic": "iva",
            },
        ],
    )
    rc = launcher.main(
        [
            "--gold",
            str(gold),
            "--output-dir",
            str(tmp_path),
            "--manifest-tag",
            "test",
            "--falkor-baseline",
            "",  # skip baseline load
        ]
    )
    assert rc == 0
    # 2 questions × 2 modes = 4 pipeline calls, alternating off/on.
    assert [c["env"] for c in calls] == ["off", "on", "off", "on"]


def test_launcher_appends_one_row_per_question(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[dict] = []
    _install_fake_pipeline(monkeypatch, calls)
    gold = _write_gold(
        tmp_path,
        [
            {"qid": "Q1", "initial_question_es": "q1?"},
            {"qid": "Q2", "initial_question_es": "q2?"},
            {"qid": "Q3", "initial_question_es": "q3?"},
        ],
    )
    launcher.main(
        [
            "--gold",
            str(gold),
            "--output-dir",
            str(tmp_path),
            "--manifest-tag",
            "t",
            "--falkor-baseline",
            "",
        ]
    )
    jsonls = list(tmp_path.glob("ab_comparison_*_t.jsonl"))
    assert len(jsonls) == 1
    lines = [ln for ln in jsonls[0].read_text().splitlines() if ln.strip()]
    assert len(lines) == 3
    for ln in lines:
        row = json.loads(ln)
        assert "prior" in row and "new" in row


def test_launcher_restores_env_on_exit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[dict] = []
    _install_fake_pipeline(monkeypatch, calls)
    monkeypatch.setenv("LIA_TEMA_FIRST_RETRIEVAL", "shadow")
    gold = _write_gold(tmp_path, [{"qid": "Q1", "initial_question_es": "q?"}])
    launcher.main(
        [
            "--gold",
            str(gold),
            "--output-dir",
            str(tmp_path),
            "--manifest-tag",
            "t",
            "--falkor-baseline",
            "",
        ]
    )
    assert os.environ.get("LIA_TEMA_FIRST_RETRIEVAL") == "shadow"


def test_launcher_restores_unset_env_on_exit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[dict] = []
    _install_fake_pipeline(monkeypatch, calls)
    monkeypatch.delenv("LIA_TEMA_FIRST_RETRIEVAL", raising=False)
    gold = _write_gold(tmp_path, [{"qid": "Q1", "initial_question_es": "q?"}])
    launcher.main(
        [
            "--gold",
            str(gold),
            "--output-dir",
            str(tmp_path),
            "--manifest-tag",
            "t",
            "--falkor-baseline",
            "",
        ]
    )
    assert "LIA_TEMA_FIRST_RETRIEVAL" not in os.environ


def test_launcher_resume_skips_completed_qids(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[dict] = []
    _install_fake_pipeline(monkeypatch, calls)
    gold = _write_gold(
        tmp_path,
        [
            {"qid": "Q1", "initial_question_es": "q1?"},
            {"qid": "Q2", "initial_question_es": "q2?"},
            {"qid": "Q3", "initial_question_es": "q3?"},
        ],
    )
    # Seed an existing JSONL with Q1, Q2 already done.
    existing = tmp_path / "pre_done.jsonl"
    existing.write_text(
        json.dumps({"qid": "Q1", "prior": {}, "new": {}}) + "\n"
        + json.dumps({"qid": "Q2", "prior": {}, "new": {}}) + "\n",
        encoding="utf-8",
    )
    launcher.main(
        [
            "--gold",
            str(gold),
            "--output-dir",
            str(tmp_path),
            "--manifest-tag",
            "t",
            "--resume",
            str(existing),
            "--falkor-baseline",
            "",
        ]
    )
    # Only Q3 should have fired pipeline calls → 2 calls (off + on).
    assert len(calls) == 2
    # Existing file must now hold 3 rows total (Q1, Q2 pre-seeded + Q3 appended).
    lines = [ln for ln in existing.read_text().splitlines() if ln.strip()]
    assert len(lines) == 3


def test_launcher_failure_row_emitted_on_pipeline_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[dict] = []
    _install_fake_pipeline(monkeypatch, calls)
    # Replace fake run_pipeline_d with one that raises on `on` mode.
    import sys as _sys

    original = _sys.modules["lia_graph.pipeline_d"].run_pipeline_d

    def _partial(request):
        env_val = os.environ.get("LIA_TEMA_FIRST_RETRIEVAL")
        if env_val == "on":
            raise RuntimeError("simulated TEMA-first crash")
        return original(request)

    _sys.modules["lia_graph.pipeline_d"].run_pipeline_d = _partial

    gold = _write_gold(tmp_path, [{"qid": "Q1", "initial_question_es": "q?"}])
    rc = launcher.main(
        [
            "--gold",
            str(gold),
            "--output-dir",
            str(tmp_path),
            "--manifest-tag",
            "t",
            "--falkor-baseline",
            "",
        ]
    )
    assert rc == 0  # partial failure is not a run-level failure
    jsonls = list(tmp_path.glob("ab_comparison_*_t.jsonl"))
    lines = [ln for ln in jsonls[0].read_text().splitlines() if ln.strip()]
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert "prior" in row            # prior succeeded
    assert "new_error" in row        # new failed
    assert "TEMA-first crash" in row["new_error"]["traceback"]


def test_launcher_manifest_includes_required_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[dict] = []
    _install_fake_pipeline(monkeypatch, calls)
    gold = _write_gold(tmp_path, [{"qid": "Q1", "initial_question_es": "q?"}])
    launcher.main(
        [
            "--gold",
            str(gold),
            "--output-dir",
            str(tmp_path),
            "--manifest-tag",
            "t",
            "--falkor-baseline",
            "",
        ]
    )
    manifest_path = next(tmp_path.glob("*_manifest.json"))
    body = json.loads(manifest_path.read_text())
    for key in (
        "manifest_tag",
        "gold_path",
        "target",
        "run_started_at_utc",
        "run_completed_at_utc",
        "run_started_at_bogota",
        "run_completed_at_bogota",
        "questions_attempted",
        "questions_succeeded",
        "questions_failed",
        "git_commit_sha",
        "env_flag_matrix",
    ):
        assert key in body, f"manifest missing {key!r}"
    assert body["questions_attempted"] == 1
    assert body["questions_succeeded"] == 1


def test_launcher_limit_flag_truncates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[dict] = []
    _install_fake_pipeline(monkeypatch, calls)
    gold = _write_gold(
        tmp_path,
        [
            {"qid": f"Q{i}", "initial_question_es": f"q{i}?"}
            for i in range(1, 6)
        ],
    )
    launcher.main(
        [
            "--gold",
            str(gold),
            "--output-dir",
            str(tmp_path),
            "--manifest-tag",
            "t",
            "--limit",
            "2",
            "--falkor-baseline",
            "",
        ]
    )
    # 2 questions × 2 modes = 4 pipeline calls.
    assert len(calls) == 4
    jsonls = list(tmp_path.glob("ab_comparison_*_t.jsonl"))
    lines = [ln for ln in jsonls[0].read_text().splitlines() if ln.strip()]
    assert len(lines) == 2
