"""tracers_and_logs — deep-trace collector + log destination for pipeline_d.

Created 2026-04-29 in response to fix_v1.md regression hand-off: the
served pipeline strips diagnostics down to ``retrieval_health`` only,
which makes it impossible to tell whether a regression came from the
topic router, the planner, the retriever, the vigencia demotion gate,
the coherence gate, the reranker, or the LLM polish step. This package
gives every stage a single trace channel and a single log destination.

Public surface:

* :func:`pipeline_trace.start` — install a fresh trace as the active
  context-local for the current request.
* :func:`pipeline_trace.step` — append one structured entry to the
  active trace and mirror it to ``tracers_and_logs/logs/pipeline_trace.jsonl``.
* :func:`pipeline_trace.snapshot` — return the active trace as a dict
  that can be attached to ``response.diagnostics["pipeline_trace"]``.
* :func:`pipeline_trace.finish` — clear the active trace.

The collector is contextvars-based, so each in-flight request keeps its
own trace even under concurrent workers.
"""

__all__ = ["pipeline_trace"]
