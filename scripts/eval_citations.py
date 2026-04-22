"""Citation-faithfulness harness — sibling to `scripts/eval_retrieval.py`.

Purpose
-------
Retrieval quality and answer quality are two different axes. The retrieval
harness asks "did we find the right law article". This harness asks "is
the answer we actually show the accountant grounded in what we found".

Two metrics, both derived entirely from `PipelineCResponse` — no new
curator annotations needed:

- **citation_precision** — fraction of inline anchors in the answer that
  appear in the retrieved evidence bundle (``primary_articles`` plus
  ``connected_articles``). An unbacked cite is a hallucinated cite,
  the fatal failure mode in regulated domain.
- **primary_anchor_recall** — fraction of hop-0 planner anchors that
  survived into the answer's inline anchors. The retriever found the
  right article; did the synthesizer drop it?

Both reported under the strict and loose normalizer from
`eval_retrieval.py` (see that file for the strict/loose rules). The
retrieval "universe" for precision is ``with_connected`` (everything
the composer saw); recall is against ``primary_only`` (graph neighbours
aren't obligated to be cited, seeds are). So the output is 4 numbers:
``{precision, recall} × {strict, loose}``.

A third observability stat — **abstention_rate** — counts answers with
zero inline anchors. Prevents the "game precision by not citing anything"
failure mode.

What v1 scopes
--------------
- Inline anchors of the form ``(art. X ET)`` / ``(arts. X y Y ET)`` /
  ``(arts. X, Y y Z ET)``. Deterministic, machine-emitted by
  ``pipeline_d/answer_inline_anchors.py::render_article_anchor_phrase``.
  Regex audited against 5 real queries — 100% coverage of
  the shape we measure.
- Non-ET regulatory cites in body text (`(Res. 000225/2024)`,
  `Ley 2277 de 2022`, `Decreto 1625 de 2016`) are counted as an
  observability stat but not scored. v2 axis.
- LLM-polished-answer faithfulness is not tested here
  (``LIA_LLM_POLISH_ENABLED=0`` is the eval default). The polish module
  already has anchor-preservation invariants; measuring them properly
  is a separate harness.

Usage
-----
    # CI-style: regression gate against committed baseline (default)
    make eval-faithfulness

    # Aspirational mode: fail if precision drops below product red line
    make eval-faithfulness ASPIRATIONAL=1

    # Re-freeze baseline after a judged improvement
    make eval-faithfulness UPDATE_BASELINE=1

    # JSON dump
    make eval-faithfulness JSON=1
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence


TOP_K_DEFAULT = 10
BASELINE_PATH_DEFAULT = Path("evals/faithfulness_baseline.json")
TOLERANCE_PP_DEFAULT = 2.0


# Aspirational red lines. Reported as targets, **not** the CI gate (same
# rationale as the retrieval harness: at n=30 the CI on any rate-style
# metric is wide enough that absolute floors would be statistical theater).
#
# Regulated domain — hallucinated cites are fatal. 0.95 precision is the
# line below which we refuse to call a run clean. Recall is softer; some
# primary anchors are intentionally suppressed (duplicates, low-salience).
# Abstention caps at 0.25 — too high means the system is refusing to
# answer; too low means it's pretending to answer with thin evidence.
ASPIRATIONAL_RED_LINES: dict[str, float] = {
    "citation_precision_loose": 0.95,        # lower bound (higher is better)
    "primary_anchor_recall_loose": 0.70,     # lower bound
    "abstention_rate_upper": 0.25,           # upper bound (lower is better)
}


VARIANT_KEYS: tuple[str, ...] = ("strict", "loose")


# ---------------------------------------------------------------------------
# Gold record loading (reuses the same JSONL — we only need the queries)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class GoldQuery:
    qid: str
    text_es: str


def load_gold_queries(path: Path) -> list[GoldQuery]:
    if not path.exists():
        raise FileNotFoundError(f"gold file not found: {path}")
    out: list[GoldQuery] = []
    with path.open("r", encoding="utf-8") as f:
        for idx, line in enumerate(f, 1):
            stripped = line.strip()
            if not stripped:
                continue
            raw = json.loads(stripped)
            out.append(
                GoldQuery(
                    qid=str(raw["qid"]),
                    text_es=str(raw.get("initial_question_es", "")).strip(),
                )
            )
    return out


# ---------------------------------------------------------------------------
# Inline-anchor parsing
# ---------------------------------------------------------------------------
# Shape: `(art. X ET)` or `(arts. X y Y ET)` or `(arts. X, Y y Z ET)`.
# Emitted by `render_article_anchor_phrase` in answer_inline_anchors.py
# with `X`, `Y`, `Z` being bare ArticleNode keys (e.g., "771-2", "240").
_ANCHOR_RE = re.compile(
    r"\(\s*arts?\.\s+([^)]+?)\s+(?:ET|E\.T\.)\s*\)",
    re.IGNORECASE,
)

# Splits the body of a multi-article anchor. Accepts commas and the
# Spanish "y" conjunction, case-insensitive.
_SPLIT_RE = re.compile(r"\s*(?:,|\s+y\s+)\s*", re.IGNORECASE)

# Regulatory cite observability pattern — counted but not scored in v1.
_REGULATORY_CITE_RE = re.compile(
    r"\((?:Res\.|Resoluci[oó]n|Decreto|Ley|Concepto)\s+[^)]{1,80}\)",
    re.IGNORECASE,
)


def extract_inline_anchors(answer_markdown: str) -> list[str]:
    """Return the list of bare article keys cited inline.

    Example: ``"La deducción procede (art. 771-2 ET) y (arts. 771-2 y 617 ET)."``
    returns ``["771-2", "771-2", "617"]`` (duplicates preserved — used
    for a counting-based precision metric).
    """
    out: list[str] = []
    for match in _ANCHOR_RE.finditer(answer_markdown or ""):
        body = match.group(1)
        for piece in _SPLIT_RE.split(body):
            key = piece.strip()
            if key:
                out.append(key)
    return out


def count_regulatory_cites(answer_markdown: str) -> int:
    """Observability stat: non-ET regulatory cites in the body text
    (e.g., ``(Res. 000225/2024)``, ``(Decreto 1625 de 2016)``). Not scored
    in v1 — v2 faithfulness axis.
    """
    return len(_REGULATORY_CITE_RE.findall(answer_markdown or ""))


# ---------------------------------------------------------------------------
# Gold-key / node-key canonicalization — copied from eval_retrieval.py.
# TODO: when a third harness lands, extract `_canonical_forms` +
# `_any_match` + the retrieved-keys extractor into a shared module.
# Duplicating for two call sites is cheaper than premature abstraction.
# ---------------------------------------------------------------------------
def _strip_et_article_prefix(gold_key: str) -> str | None:
    if not gold_key.startswith("ET_ART_"):
        return None
    tail = gold_key[len("ET_ART_"):]
    return tail.replace("_", "-").lower()


def _canonical_forms(key: str, *, strict: bool) -> tuple[str, ...]:
    stripped = key.strip()
    if not stripped:
        return ()
    forms: set[str] = set()
    forms.add(stripped)
    forms.add(stripped.lower())

    et = _strip_et_article_prefix(stripped)
    if et is not None:
        forms.add(et)
        if not strict:
            for suffix in ("-par-", "-parag-", "-par_"):
                if suffix in et:
                    forms.add(et.split(suffix, 1)[0])

    if stripped.startswith(("LEY_", "DECRETO_", "RES_", "RESOLUCION_")):
        kebab = stripped.replace("_", "-")
        forms.add(kebab)
        forms.add(kebab.lower())
        if not strict:
            if "-ART-" in kebab.upper():
                trimmed = kebab[: kebab.upper().index("-ART-")]
                forms.add(trimmed)
                forms.add(trimmed.lower())

    return tuple(sorted(forms))


def _canonicalize_retrieved(keys: Sequence[str]) -> set[str]:
    return {str(k).strip().lower() for k in keys if str(k).strip()}


def _any_match(expected: str, retrieved_lower: set[str], *, strict: bool) -> bool:
    for form in _canonical_forms(expected, strict=strict):
        if form.lower() in retrieved_lower:
            return True
    return False


def _extract_ranked_keys(
    diagnostics: dict[str, Any],
    *,
    top_k: int,
    scope: str,
) -> tuple[str, ...]:
    bundle = diagnostics.get("evidence_bundle") or {}
    primary = bundle.get("primary_articles") or []
    connected = bundle.get("connected_articles") or []
    groups: list[Any] = [primary]
    if scope == "with_connected":
        groups.append(connected)
    elif scope != "primary_only":
        raise ValueError(f"unknown scope: {scope}")
    seen: set[str] = set()
    ranked: list[str] = []
    for group in groups:
        for item in group:
            key = str(item.get("node_key", "")).strip()
            if not key or key in seen:
                continue
            seen.add(key)
            ranked.append(key)
            if len(ranked) >= top_k:
                return tuple(ranked)
    return tuple(ranked)


# ---------------------------------------------------------------------------
# Per-query faithfulness
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class PipelineProbe:
    answer_markdown: str
    primary_keys: tuple[str, ...]
    with_connected_keys: tuple[str, ...]
    retrieval_backend: str | None
    reranker_mode: str | None


def probe_pipeline(query: str, *, top_k: int = TOP_K_DEFAULT) -> PipelineProbe:
    from lia_graph.pipeline_c.contracts import PipelineCRequest
    from lia_graph.pipeline_d import run_pipeline_d
    from lia_graph.topic_router import resolve_chat_topic

    routing = resolve_chat_topic(message=query, requested_topic=None, pais="colombia")
    request = PipelineCRequest(
        message=query,
        pais="colombia",
        topic=routing.effective_topic,
        requested_topic=routing.requested_topic,
        secondary_topics=routing.secondary_topics,
        topic_adjusted=routing.topic_adjusted,
        topic_notice=routing.topic_notice,
        topic_adjustment_reason=routing.reason,
        topic_router_confidence=routing.confidence,
    )
    response = run_pipeline_d(request)
    diag = dict(response.diagnostics or {})
    primary = _extract_ranked_keys(diag, top_k=top_k, scope="primary_only")
    with_conn = _extract_ranked_keys(diag, top_k=top_k, scope="with_connected")
    reranker_diag = diag.get("reranker") or {}
    return PipelineProbe(
        answer_markdown=str(response.answer_markdown or ""),
        primary_keys=primary,
        with_connected_keys=with_conn,
        retrieval_backend=diag.get("retrieval_backend"),
        reranker_mode=(reranker_diag.get("mode") if isinstance(reranker_diag, dict) else None),
    )


# ---------------------------------------------------------------------------
# Metric primitives
# ---------------------------------------------------------------------------
def citation_precision(
    cites: Sequence[str],
    retrieved_universe: Sequence[str],
    *,
    strict: bool,
) -> float | None:
    """Fraction of cites backed by retrieved evidence. ``None`` for
    abstention (no cites) — those queries feed the abstention stat, not
    the precision numerator.
    """
    if not cites:
        return None
    universe = _canonicalize_retrieved(retrieved_universe)
    backed = sum(1 for c in cites if _any_match(c, universe, strict=strict))
    return backed / len(cites)


def primary_anchor_recall(
    primary_articles: Sequence[str],
    cites: Sequence[str],
    *,
    strict: bool,
) -> float | None:
    """Fraction of primary articles that appear (as any canonical form)
    among the answer's cites. ``None`` when there are no primary articles
    to recall (evidence bundle empty)."""
    if not primary_articles:
        return None
    cite_forms_per: list[set[str]] = []
    for c in cites:
        cite_forms_per.append({f.lower() for f in _canonical_forms(c, strict=strict)})
    hit = 0
    for p in primary_articles:
        primary_forms = {f.lower() for f in _canonical_forms(p, strict=strict)}
        if any(cf & primary_forms for cf in cite_forms_per):
            hit += 1
    return hit / len(primary_articles)


# ---------------------------------------------------------------------------
# Per-entry scoring
# ---------------------------------------------------------------------------
@dataclass
class EntryScore:
    qid: str
    cite_count: int
    regulatory_cite_count: int
    primary_count: int
    precision_strict: float | None
    precision_loose: float | None
    recall_strict: float | None
    recall_loose: float | None
    abstained: bool             # cite_count == 0
    retrieval_backend: str | None
    reranker_mode: str | None


def _score_entry(query: GoldQuery, *, top_k: int) -> EntryScore:
    probe = probe_pipeline(query.text_es, top_k=top_k)
    cites = extract_inline_anchors(probe.answer_markdown)
    regulatory = count_regulatory_cites(probe.answer_markdown)
    return EntryScore(
        qid=query.qid,
        cite_count=len(cites),
        regulatory_cite_count=regulatory,
        primary_count=len(probe.primary_keys),
        precision_strict=citation_precision(cites, probe.with_connected_keys, strict=True),
        precision_loose=citation_precision(cites, probe.with_connected_keys, strict=False),
        recall_strict=primary_anchor_recall(probe.primary_keys, cites, strict=True),
        recall_loose=primary_anchor_recall(probe.primary_keys, cites, strict=False),
        abstained=(len(cites) == 0),
        retrieval_backend=probe.retrieval_backend,
        reranker_mode=probe.reranker_mode,
    )


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------
def _mean(values: Iterable[float | None]) -> float | None:
    lst = [v for v in values if v is not None]
    if not lst:
        return None
    return sum(lst) / len(lst)


@dataclass
class Aggregate:
    entry_scores: list[EntryScore]
    citation_precision_strict: float | None
    citation_precision_loose: float | None
    primary_anchor_recall_strict: float | None
    primary_anchor_recall_loose: float | None
    abstention_rate: float
    precision_denominator: int
    recall_denominator: int
    abstention_denominator: int
    total_cites: int
    total_regulatory_cites: int

    def to_flat(self) -> dict[str, float | None]:
        return {
            "citation_precision_strict": self.citation_precision_strict,
            "citation_precision_loose": self.citation_precision_loose,
            "primary_anchor_recall_strict": self.primary_anchor_recall_strict,
            "primary_anchor_recall_loose": self.primary_anchor_recall_loose,
            "abstention_rate": self.abstention_rate,
        }


def aggregate(entry_scores: list[EntryScore]) -> Aggregate:
    precision_strict_vals = [e.precision_strict for e in entry_scores if e.precision_strict is not None]
    precision_loose_vals = [e.precision_loose for e in entry_scores if e.precision_loose is not None]
    recall_strict_vals = [e.recall_strict for e in entry_scores if e.recall_strict is not None]
    recall_loose_vals = [e.recall_loose for e in entry_scores if e.recall_loose is not None]
    abstained = sum(1 for e in entry_scores if e.abstained)
    return Aggregate(
        entry_scores=entry_scores,
        citation_precision_strict=_mean(precision_strict_vals),
        citation_precision_loose=_mean(precision_loose_vals),
        primary_anchor_recall_strict=_mean(recall_strict_vals),
        primary_anchor_recall_loose=_mean(recall_loose_vals),
        abstention_rate=(abstained / len(entry_scores)) if entry_scores else 0.0,
        precision_denominator=len(precision_loose_vals),
        recall_denominator=len(recall_loose_vals),
        abstention_denominator=len(entry_scores),
        total_cites=sum(e.cite_count for e in entry_scores),
        total_regulatory_cites=sum(e.regulatory_cite_count for e in entry_scores),
    )


# ---------------------------------------------------------------------------
# Baseline I/O (same pattern as eval_retrieval.py — methodology-gated)
# ---------------------------------------------------------------------------
def dump_baseline(
    agg: Aggregate,
    path: Path,
    *,
    gold_path: Path,
    methodology: dict[str, Any],
) -> None:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gold_path": str(gold_path),
        "gold_entry_count": len(agg.entry_scores),
        "methodology": methodology,
        "metrics": agg.to_flat(),
        "observability": {
            "total_cites": agg.total_cites,
            "total_regulatory_cites": agg.total_regulatory_cites,
            "precision_denominator": agg.precision_denominator,
            "recall_denominator": agg.recall_denominator,
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_baseline(path: Path) -> tuple[dict[str, float | None], dict[str, Any]] | None:
    if not path.exists():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    metrics = raw.get("metrics")
    if not isinstance(metrics, dict):
        return None
    methodology = raw.get("methodology") or {}
    if not isinstance(methodology, dict):
        methodology = {}
    out: dict[str, float | None] = {}
    for k, v in metrics.items():
        if v is None:
            out[k] = None
        else:
            try:
                out[k] = float(v)
            except (TypeError, ValueError):
                out[k] = None
    return out, methodology


def methodology_matches(current: dict[str, Any], baseline: dict[str, Any]) -> list[str]:
    mismatches: list[str] = []
    for key, cur_val in current.items():
        if key not in baseline:
            continue
        if baseline[key] != cur_val:
            mismatches.append(f"{key}: current={cur_val!r}, baseline={baseline[key]!r}")
    return mismatches


# ---------------------------------------------------------------------------
# Regression gate
# ---------------------------------------------------------------------------
# Precision, recall: higher is better → regression is a DROP > tolerance.
# Abstention rate:   lower is better → regression is a RISE > tolerance.
_HIGHER_BETTER = {
    "citation_precision_strict",
    "citation_precision_loose",
    "primary_anchor_recall_strict",
    "primary_anchor_recall_loose",
}
_LOWER_BETTER = {"abstention_rate"}


def compute_regressions(
    current: dict[str, float | None],
    baseline: dict[str, float | None],
    *,
    tolerance_pp: float,
) -> list[str]:
    tol = tolerance_pp / 100.0
    failures: list[str] = []
    for key, base_val in baseline.items():
        if base_val is None:
            continue
        cur_val = current.get(key)
        if cur_val is None:
            failures.append(f"{key}: current=None, baseline={base_val:.3f}")
            continue
        delta = cur_val - base_val
        if key in _HIGHER_BETTER and delta < -tol:
            failures.append(
                f"{key}: {cur_val:.3f} vs baseline {base_val:.3f} (Δ={delta:+.3f}, tolerance -{tol:.3f})"
            )
        elif key in _LOWER_BETTER and delta > tol:
            failures.append(
                f"{key}: {cur_val:.3f} vs baseline {base_val:.3f} (Δ={delta:+.3f}, tolerance +{tol:.3f}, lower-is-better)"
            )
    return failures


def check_red_lines(agg: Aggregate) -> list[str]:
    failures: list[str] = []
    p = agg.citation_precision_loose
    r = agg.primary_anchor_recall_loose
    a = agg.abstention_rate
    if p is None:
        failures.append("citation_precision_loose: no data (all answers abstained)")
    elif p < ASPIRATIONAL_RED_LINES["citation_precision_loose"]:
        failures.append(
            f"citation_precision_loose: {p:.3f} < red line {ASPIRATIONAL_RED_LINES['citation_precision_loose']:.2f}"
        )
    if r is None:
        failures.append("primary_anchor_recall_loose: no data (no primary anchors anywhere)")
    elif r < ASPIRATIONAL_RED_LINES["primary_anchor_recall_loose"]:
        failures.append(
            f"primary_anchor_recall_loose: {r:.3f} < red line {ASPIRATIONAL_RED_LINES['primary_anchor_recall_loose']:.2f}"
        )
    if a > ASPIRATIONAL_RED_LINES["abstention_rate_upper"]:
        failures.append(
            f"abstention_rate: {a:.3f} > red line {ASPIRATIONAL_RED_LINES['abstention_rate_upper']:.2f} (lower-is-better)"
        )
    return failures


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------
def _fmt(value: float | None, width: int = 5) -> str:
    if value is None:
        return f"{'n/a':>{width}s}"
    return f"{value:>{width}.3f}"


def render_human(
    agg: Aggregate,
    *,
    gold_path: Path,
    baseline_metrics: dict[str, float | None] | None,
    tolerance_pp: float,
) -> str:
    lines: list[str] = []
    lines.append(f"# Citation-faithfulness harness — {gold_path} ({len(agg.entry_scores)} entries)")
    lines.append("")
    backends = {e.retrieval_backend for e in agg.entry_scores if e.retrieval_backend}
    rerankers = {e.reranker_mode for e in agg.entry_scores if e.reranker_mode}
    if backends:
        lines.append(f"  retrieval_backend seen: {sorted(backends)}")
    if rerankers:
        lines.append(f"  reranker_mode seen:     {sorted(rerankers)}")
    lines.append("")

    lines.append("## Core metrics (strict | loose normalizer)")
    lines.append("")
    lines.append(f"  citation_precision        {_fmt(agg.citation_precision_strict)} | {_fmt(agg.citation_precision_loose)}   n={agg.precision_denominator}")
    lines.append(f"  primary_anchor_recall     {_fmt(agg.primary_anchor_recall_strict)} | {_fmt(agg.primary_anchor_recall_loose)}   n={agg.recall_denominator}")
    lines.append(f"  abstention_rate                       {_fmt(agg.abstention_rate)}   (lower is better)   n={agg.abstention_denominator}")
    lines.append("")
    lines.append(f"  total inline cites across all answers:   {agg.total_cites}")
    lines.append(f"  total regulatory cites (v2, not scored): {agg.total_regulatory_cites}")
    lines.append("")

    lines.append(f"## Regression vs baseline (tolerance ±{tolerance_pp:.1f}pp)")
    if baseline_metrics is None:
        lines.append("  No baseline file — run `--update-baseline` to commit one.")
    else:
        current = agg.to_flat()
        for key in sorted(baseline_metrics.keys()):
            base = baseline_metrics[key]
            cur = current.get(key)
            tol = tolerance_pp / 100.0
            if cur is None or base is None:
                status = "  n/a"
                delta_str = "   n/a"
            else:
                delta = cur - base
                delta_str = f"{delta:+.3f}"
                if key in _HIGHER_BETTER:
                    status = "  OK" if delta >= -tol else "  FAIL"
                elif key in _LOWER_BETTER:
                    status = "  OK" if delta <= tol else "  FAIL"
                else:
                    status = "  OK"
            lines.append(
                f"  {key:<36s} {_fmt(cur, 6)} vs {_fmt(base, 6)}  Δ={delta_str}  {status}"
            )
    lines.append("")

    lines.append("## Aspirational red lines (report only — loose normalizer)")
    lines.append(
        f"  citation_precision_loose       target >= {ASPIRATIONAL_RED_LINES['citation_precision_loose']:.2f}   "
        f"actual {_fmt(agg.citation_precision_loose)}"
    )
    lines.append(
        f"  primary_anchor_recall_loose    target >= {ASPIRATIONAL_RED_LINES['primary_anchor_recall_loose']:.2f}   "
        f"actual {_fmt(agg.primary_anchor_recall_loose)}"
    )
    lines.append(
        f"  abstention_rate                target <= {ASPIRATIONAL_RED_LINES['abstention_rate_upper']:.2f}   "
        f"actual {_fmt(agg.abstention_rate)}"
    )
    lines.append("")

    lines.append("## Per-entry breakdown")
    lines.append(
        f"  {'qid':<6s} {'#cite':>5s} {'#prim':>5s} {'prec_s':>7s} {'prec_l':>7s} {'rec_s':>6s} {'rec_l':>6s} {'abst':>5s} {'#reg':>5s}"
    )
    for e in agg.entry_scores:
        abst = "  yes" if e.abstained else "   no"
        lines.append(
            f"  {e.qid:<6s} {e.cite_count:>5d} {e.primary_count:>5d} "
            f"{_fmt(e.precision_strict, 7)} {_fmt(e.precision_loose, 7)} "
            f"{_fmt(e.recall_strict, 6)} {_fmt(e.recall_loose, 6)} "
            f"{abst:>5s} {e.regulatory_cite_count:>5d}"
        )
    lines.append("")
    lines.append(
        "Scope: v1 measures inline `(art. X ET)` anchors only. Regulatory "
        "body-text cites (`(Res. X/Y)`, `Ley X de Y`, `Decreto X de Y`) are "
        "counted but not scored — v2 axis."
    )
    return "\n".join(lines)


def render_json(
    agg: Aggregate,
    *,
    baseline_metrics: dict[str, float | None] | None,
    tolerance_pp: float,
) -> str:
    current = agg.to_flat()
    regressions: list[str] = []
    if baseline_metrics is not None:
        regressions = compute_regressions(current, baseline_metrics, tolerance_pp=tolerance_pp)
    payload = {
        "metrics": current,
        "baseline_metrics": baseline_metrics,
        "regressions": regressions,
        "tolerance_pp": tolerance_pp,
        "aspirational_red_lines": dict(ASPIRATIONAL_RED_LINES),
        "observability": {
            "total_cites": agg.total_cites,
            "total_regulatory_cites": agg.total_regulatory_cites,
            "precision_denominator": agg.precision_denominator,
            "recall_denominator": agg.recall_denominator,
            "abstention_denominator": agg.abstention_denominator,
        },
        "entries": [
            {
                "qid": e.qid,
                "cite_count": e.cite_count,
                "primary_count": e.primary_count,
                "regulatory_cite_count": e.regulatory_cite_count,
                "precision_strict": e.precision_strict,
                "precision_loose": e.precision_loose,
                "recall_strict": e.recall_strict,
                "recall_loose": e.recall_loose,
                "abstained": e.abstained,
                "retrieval_backend": e.retrieval_backend,
                "reranker_mode": e.reranker_mode,
            }
            for e in agg.entry_scores
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Citation-faithfulness harness (sibling to eval_retrieval.py).")
    parser.add_argument(
        "--gold",
        type=Path,
        default=Path("evals/gold_retrieval_v1.jsonl"),
        help="Gold JSONL — only `qid` and `initial_question_es` are used.",
    )
    parser.add_argument("--top-k", type=int, default=TOP_K_DEFAULT)
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--baseline",
        type=Path,
        default=BASELINE_PATH_DEFAULT,
    )
    parser.add_argument(
        "--fail-on-regression",
        action="store_true",
        help="CI gate: exit non-zero if any metric regressed more than --tolerance-pp.",
    )
    parser.add_argument(
        "--tolerance-pp",
        type=float,
        default=TOLERANCE_PP_DEFAULT,
    )
    parser.add_argument(
        "--fail-under-red-lines",
        action="store_true",
        help="Aspirational: exit non-zero if precision/recall/abstention cross their product red lines.",
    )
    parser.add_argument("--update-baseline", action="store_true")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)

    queries = load_gold_queries(args.gold)
    if not queries:
        print(f"[eval_citations] gold file is empty: {args.gold}", file=sys.stderr)
        return 2

    scored: list[EntryScore] = []
    for q in queries:
        scored.append(_score_entry(q, top_k=args.top_k))
    agg = aggregate(scored)

    current_methodology: dict[str, Any] = {
        "top_k": int(args.top_k),
        "reranker_mode": str(os.getenv("LIA_RERANKER_MODE", "off")).strip().lower() or "off",
        "polish_enabled": bool(str(os.getenv("LIA_LLM_POLISH_ENABLED", "")).strip().lower() in {"1", "true", "yes", "on"}),
        "decompose_enabled": str(os.getenv("LIA_QUERY_DECOMPOSE", "off")).strip().lower() == "on",
    }

    loaded = load_baseline(args.baseline)
    baseline_metrics: dict[str, float | None] | None = None
    baseline_methodology: dict[str, Any] = {}
    if loaded is not None:
        baseline_metrics, baseline_methodology = loaded

    if args.update_baseline:
        dump_baseline(agg, args.baseline, gold_path=args.gold, methodology=current_methodology)
        print(f"[eval_citations] baseline written: {args.baseline}", file=sys.stderr)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            render_json(agg, baseline_metrics=baseline_metrics, tolerance_pp=args.tolerance_pp),
            encoding="utf-8",
        )

    if args.json:
        print(render_json(agg, baseline_metrics=baseline_metrics, tolerance_pp=args.tolerance_pp))
    else:
        print(
            render_human(
                agg,
                gold_path=args.gold,
                baseline_metrics=baseline_metrics,
                tolerance_pp=args.tolerance_pp,
            )
        )

    exit_code = 0
    if args.fail_on_regression:
        if baseline_metrics is None:
            print(
                f"[eval_citations] --fail-on-regression requested but no baseline at {args.baseline}",
                file=sys.stderr,
            )
            return 3
        method_mismatches = methodology_matches(current_methodology, baseline_methodology)
        if method_mismatches:
            print("", file=sys.stderr)
            print(
                "[eval_citations] METHODOLOGY MISMATCH vs baseline — refusing to gate:",
                file=sys.stderr,
            )
            for msg in method_mismatches:
                print(f"  - {msg}", file=sys.stderr)
            print(
                "  Re-freeze the baseline with `--update-baseline` under the new methodology before gating.",
                file=sys.stderr,
            )
            return 4
        regressions = compute_regressions(
            agg.to_flat(), baseline_metrics, tolerance_pp=args.tolerance_pp
        )
        if regressions:
            print("", file=sys.stderr)
            print(
                f"[eval_citations] REGRESSION (tolerance ±{args.tolerance_pp:.1f}pp):",
                file=sys.stderr,
            )
            for msg in regressions:
                print(f"  - {msg}", file=sys.stderr)
            exit_code = 1

    if args.fail_under_red_lines:
        failures = check_red_lines(agg)
        if failures:
            print("", file=sys.stderr)
            print("[eval_citations] ASPIRATIONAL RED LINE FAILURES:", file=sys.stderr)
            for msg in failures:
                print(f"  - {msg}", file=sys.stderr)
            exit_code = exit_code or 1

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
