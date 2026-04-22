"""Tests for scripts/debug_query.py (lexical-layer query tracer).

No mocking — the CLI deliberately uses only lexical layers (topic router,
subtopic classifier, planner). Tests run against the real in-process
routing stack, so they also serve as regression guards for the router
itself.
"""

from __future__ import annotations

import importlib.util
import io
import json
from contextlib import redirect_stdout
from pathlib import Path


_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "debug_query.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("debug_query_cli", _SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_cli(*args: str) -> dict:
    module = _load_module()
    buf = io.StringIO()
    with redirect_stdout(buf):
        exit_code = module.main(list(args))
    assert exit_code == 0
    return json.loads(buf.getvalue())


def test_returns_effective_topic_and_subtopic_for_known_query() -> None:
    # Audit-procedure query — expected to route to procedimiento_tributario
    # via the narrow fix landed earlier. Serves as a regression guard.
    query = (
        "La DIAN le envió un requerimiento ordinario a mi cliente por "
        "diferencias entre retenciones declaradas y exógena. "
        "¿Cuáles son los términos para responder?"
    )
    result = _run_cli(query)
    assert result["query"] == query
    assert result["topic"]["effective_topic"] == "procedimiento_tributario"
    assert (
        result["subtopic"]["sub_topic_intent"]
        == "simplificacion_tramites_administrativos_y_tributarios"
    )
    # Keyword-score payload is diagnostic, always a dict, ordered by score.
    assert isinstance(result["topic"]["keyword_scores"], dict)


def test_per_sub_question_produces_one_trace_per_split() -> None:
    query = (
        "¿Cuáles son los términos para responder? "
        "¿Qué pruebas son admisibles?"
    )
    result = _run_cli("--per-sub-question", query)
    assert len(result["sub_questions"]) == 2
    assert "per_sub_question" in result
    assert len(result["per_sub_question"]) == 2
    for entry in result["per_sub_question"]:
        assert "topic" in entry and "subtopic" in entry


def test_pinned_requested_topic_is_passed_through() -> None:
    # --topic pins the raw requested_topic passed to the router; the router
    # then normalizes aliases (e.g. "renta" -> "declaracion_renta"). The CLI
    # surfaces both: the original arg on `result["requested_topic"]`, and
    # the normalized form on `result["topic"]["requested_topic"]`.
    result = _run_cli("--topic", "renta", "cualquier consulta")
    assert result["requested_topic"] == "renta"
    assert result["topic"]["requested_topic"] in {"renta", "declaracion_renta"}


def test_full_flag_attaches_graph_retrieval_plan() -> None:
    # --full builds a real GraphRetrievalPlan in-process. No I/O, no cloud.
    # If the planner contract changes in a way that breaks plan.to_dict(),
    # this test fails loudly so we notice.
    result = _run_cli("--full", "¿Cómo liquido a un empleado?")
    assert "plan" in result
    plan = result["plan"]
    assert isinstance(plan, dict)
    # Contract sanity: the plan dict must expose these keys.
    for key in ("query_mode", "entry_points", "sub_questions", "sub_topic_intent"):
        assert key in plan
