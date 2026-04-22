"""Eval harness for `evals/gold_retrieval_v1.jsonl`.

Structural backlog item #1 from `docs/next/structuralwork_v1_SEENOW.md`,
revised 2026-04-22 per senior-RAG expert verdict on `docs/next/package_expert.md`.

What changed vs the first-cut harness
-------------------------------------
The original shipped one "retrieval@10" number that silently conflated two
mechanisms (planner anchors vs graph expansion) and one normalizer style
(loose: paragraph→parent, law-level fallback). Both collapses hid signal.
The fix, applied end-to-end:

- **2×2 metric matrix.** Every retrieval metric is now reported four times:
  ``primary_only × {strict, loose}`` and ``with_connected × {strict, loose}``.
  The deltas across cells are the diagnostic: if `strict_primary_only` is
  0.15 and `loose_with_connected` is 0.45, that's a different story than
  "retrieval is at 0.30".
- **Regression-vs-baseline CI gate.** At n≈25 scoring entries, the 95% CI
  on r@10 is ±~18pp — absolute floors like `>= 0.70` both false-fail clean
  PRs and false-pass real regressions. CI now reads `evals/baseline.json`
  and fails when any metric regressed by more than `--tolerance-pp`
  (default 2pp). Keep the aspirational red lines visible in the human
  report, just not in CI.
- **`topic_accuracy` → `router_accuracy`.** The harness measures the
  resolver (`resolve_chat_topic`), not the pipeline — `run_pipeline_d`
  only echoes `request.topic`. Renamed to stop drawing wrong conclusions.
- **`subtopic_accuracy` dropped from reporting.** Gold `expected_subtopic`
  slugs were written without cross-indexing against
  `config/subtopic_taxonomy.json`; the 0.000 score is a vocabulary
  mismatch, not a retrieval signal. Will return after the accountant
  re-indexes the gold.

Invariants
----------
- No fuzzy matching, no LLM judging. `_canonical_forms` is deterministic
  and the loose/strict difference is two explicit rules documented in
  the function.
- The harness fires through `resolve_chat_topic` → `run_pipeline_d`,
  mirroring the `ui_server.py` production path. The pipeline doesn't
  route; the resolver does.
- Citations, latency, token cost, and citation-faithfulness are **not
  measured here**. The expert verdict flagged citation-faithfulness as
  the load-bearing next axis; build it as a separate harness.

Usage
-----
    # CI-style: regression gate against committed baseline (default)
    make eval-retrieval

    # Aspirational mode: show red-line FAILs for human review
    make eval-retrieval FAIL_UNDER=1

    # Update the committed baseline after a judged improvement
    PYTHONPATH=src:. uv run python scripts/eval_retrieval.py \\
        --update-baseline

    # JSON dump for a machine diff
    PYTHONPATH=src:. uv run python scripts/eval_retrieval.py --json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence


TOP_K_DEFAULT = 10
BASELINE_PATH_DEFAULT = Path("evals/baseline.json")
TOLERANCE_PP_DEFAULT = 2.0


# Aspirational red lines from the senior RAG review in
# `docs/next/structuralwork_v1_SEENOW.md` §#1. Shown in the report as
# targets; **not** the CI gate. CI gates on regression-vs-baseline
# because at n=30 the ±18pp CI on r@10 makes absolute floors noise.
ASPIRATIONAL_RED_LINES: dict[str, float] = {
    "retrieval_at_10": 0.70,
    "router_accuracy": 0.85,
    "sub_question_recall_at_10": 0.60,
}

# The default variant for aspirational display + the per-entry breakdown.
# Loose normalizer + with_connected matches the answerable-reader UX:
# "did the article show up anywhere in what the LLM saw, parent article
# or paragraph". Strict + primary_only is the companion view that shows
# the planner's anchoring skill in isolation.
DEFAULT_DISPLAY_VARIANT = "with_connected_loose"

VARIANT_KEYS: tuple[str, ...] = (
    "primary_only_strict",
    "primary_only_loose",
    "with_connected_strict",
    "with_connected_loose",
)


# ---------------------------------------------------------------------------
# Gold record loading
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class SubQuestion:
    text_es: str
    expected_topic: str | None
    expected_subtopic: str | None
    expected_article_keys: tuple[str, ...]


@dataclass(frozen=True)
class GoldEntry:
    qid: str
    type_: str                       # "S" or "M"
    query_shape: str
    macro_area: str
    initial_question_es: str
    expected_topic: str | None
    expected_subtopic: str | None
    expected_article_keys: tuple[str, ...]
    sub_questions: tuple[SubQuestion, ...]
    expected_topic_uncertain: bool = False


def _tuple_strs(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item).strip() for item in value if str(item).strip())


def _parse_sub_question(raw: dict[str, Any]) -> SubQuestion:
    return SubQuestion(
        text_es=str(raw.get("text_es", "")).strip(),
        expected_topic=(str(raw["expected_topic"]).strip() if raw.get("expected_topic") else None),
        expected_subtopic=(str(raw["expected_subtopic"]).strip() if raw.get("expected_subtopic") else None),
        expected_article_keys=_tuple_strs(raw.get("expected_article_keys")),
    )


def load_gold(path: Path) -> list[GoldEntry]:
    if not path.exists():
        raise FileNotFoundError(f"gold file not found: {path}")
    entries: list[GoldEntry] = []
    with path.open("r", encoding="utf-8") as f:
        for idx, line in enumerate(f, 1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                raw = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"gold line {idx}: invalid JSON: {exc}") from exc
            subs_raw = raw.get("sub_questions") or ()
            sub_questions = tuple(_parse_sub_question(item) for item in subs_raw) if subs_raw else ()
            entries.append(
                GoldEntry(
                    qid=str(raw["qid"]),
                    type_=str(raw.get("type", "S")),
                    query_shape=str(raw.get("query_shape", "single")),
                    macro_area=str(raw.get("macro_area", "")),
                    initial_question_es=str(raw.get("initial_question_es", "")),
                    expected_topic=(str(raw["expected_topic"]).strip() if raw.get("expected_topic") else None),
                    expected_subtopic=(str(raw["expected_subtopic"]).strip() if raw.get("expected_subtopic") else None),
                    expected_article_keys=_tuple_strs(raw.get("expected_article_keys")),
                    sub_questions=sub_questions,
                    expected_topic_uncertain=bool(raw.get("expected_topic_uncertain", False)),
                )
            )
    return entries


# ---------------------------------------------------------------------------
# Gold-key ↔ node-key canonicalization (strict & loose)
# ---------------------------------------------------------------------------
# The gold encodes fully-qualified references (`ET_ART_771_2`,
# `LEY_2277_2022_ART_7`) so the accountant can review at a glance. The
# graph emits bare node keys (`771-2`, `LEY-2277-2022`). We canonicalize
# both sides to a small set of surface forms and set-intersect — no
# fuzzy matching, no LLM judging.
#
# Two rules are **only applied in loose mode**; they trade precision for
# recall by treating "in the same container" as equivalent to "at the
# right anchor":
#
#   (L1) paragraph → parent article
#        ET_ART_240_PAR_6  loose→ {240-par-6, 240}
#        ET_ART_240_PAR_6  strict→ {240-par-6}
#
#   (L2) reform article → parent law
#        LEY_2277_2022_ART_7  loose→ {LEY-2277-2022-ART-7, LEY-2277-2022}
#        LEY_2277_2022_ART_7  strict→ {LEY-2277-2022-ART-7}
#
# The strict/loose delta across the matrix is the expert-flagged
# diagnostic: it shows how much of retrieval@10 is "at the anchor" vs
# "in the anchor's container".
def _strip_et_article_prefix(gold_key: str) -> str | None:
    """``ET_ART_771_2`` -> ``771-2``.  ``ET_ART_240_PAR_6`` -> ``240-par-6``."""
    if not gold_key.startswith("ET_ART_"):
        return None
    tail = gold_key[len("ET_ART_"):]
    return tail.replace("_", "-").lower()


def _canonical_forms(key: str, *, strict: bool) -> tuple[str, ...]:
    """Return the tuple of canonical forms of `key` for equivalence matching.

    `strict=True` drops the loose-mode fallbacks (L1, L2 above). `strict=False`
    is the production UX model: an article cited in the same parent as the
    gold anchor counts as relevant.
    """
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
            # L1: paragraph → parent article
            for suffix in ("-par-", "-parag-", "-par_"):
                if suffix in et:
                    forms.add(et.split(suffix, 1)[0])

    if stripped.startswith(("LEY_", "DECRETO_", "RES_", "RESOLUCION_")):
        kebab = stripped.replace("_", "-")
        forms.add(kebab)
        forms.add(kebab.lower())
        if not strict:
            # L2: reform article → parent law
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


def _retrieved_is_relevant(
    retrieved_key: str,
    expected_forms: Sequence[set[str]],
) -> bool:
    low = retrieved_key.strip().lower()
    for forms in expected_forms:
        if low in forms:
            return True
    return False


# ---------------------------------------------------------------------------
# Per-query retrieval (fires the pipeline + extracts both ranked scopes)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class RetrievalResult:
    ranked_primary_only: tuple[str, ...]
    ranked_with_connected: tuple[str, ...]
    effective_topic: str | None
    sub_topic_intent: str | None
    retrieval_backend: str | None
    graph_backend: str | None
    reranker_mode: str | None
    diagnostics: dict[str, Any] = field(default_factory=dict)


def _extract_ranked_keys(
    diagnostics: dict[str, Any],
    *,
    top_k: int,
    scope: str,
) -> tuple[str, ...]:
    """`scope="primary_only"` pulls planner seeds only; `scope="with_connected"`
    appends graph-expanded neighbours. Deduped while preserving first-seen
    order.
    """
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


def retrieve_for_query(query: str, *, top_k: int = TOP_K_DEFAULT) -> RetrievalResult:
    """Fire a single query through the production-equivalent path.

    Imports are local so the module loads cheaply in `--help` contexts.
    """
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
    ranked_primary = _extract_ranked_keys(diag, top_k=top_k, scope="primary_only")
    ranked_with_connected = _extract_ranked_keys(diag, top_k=top_k, scope="with_connected")
    planner = diag.get("planner") or {}
    reranker_diag = diag.get("reranker") or {}
    return RetrievalResult(
        ranked_primary_only=ranked_primary,
        ranked_with_connected=ranked_with_connected,
        effective_topic=routing.effective_topic,
        sub_topic_intent=planner.get("sub_topic_intent"),
        retrieval_backend=diag.get("retrieval_backend"),
        graph_backend=diag.get("graph_backend"),
        reranker_mode=(reranker_diag.get("mode") if isinstance(reranker_diag, dict) else None),
        diagnostics={
            "planner_query_mode": planner.get("query_mode"),
            "empty_reason": (diag.get("retrieval_health") or {}).get("empty_reason"),
        },
    )


# ---------------------------------------------------------------------------
# Metric primitives — parametrized by strict/loose
# ---------------------------------------------------------------------------
def recall_at_k(
    retrieved: Sequence[str],
    expected: Sequence[str],
    k: int,
    *,
    strict: bool,
) -> float | None:
    if not expected:
        return None
    top = _canonicalize_retrieved(retrieved[:k])
    hits = sum(1 for key in expected if _any_match(key, top, strict=strict))
    return hits / len(expected)


def reciprocal_rank(
    retrieved: Sequence[str],
    expected: Sequence[str],
    *,
    strict: bool,
) -> float | None:
    if not expected:
        return None
    expected_forms = [{form.lower() for form in _canonical_forms(k, strict=strict)} for k in expected]
    for idx, key in enumerate(retrieved, 1):
        if _retrieved_is_relevant(key, expected_forms):
            return 1.0 / idx
    return 0.0


def ndcg_at_k(
    retrieved: Sequence[str],
    expected: Sequence[str],
    k: int,
    *,
    strict: bool,
) -> float | None:
    if not expected:
        return None
    expected_forms = [{form.lower() for form in _canonical_forms(k2, strict=strict)} for k2 in expected]
    dcg = 0.0
    for idx, key in enumerate(retrieved[:k], 1):
        if _retrieved_is_relevant(key, expected_forms):
            dcg += 1.0 / math.log2(idx + 1)
    ideal_count = min(len(expected), k)
    idcg = sum(1.0 / math.log2(i + 1) for i in range(1, ideal_count + 1))
    if idcg == 0.0:
        return 0.0
    return dcg / idcg


# ---------------------------------------------------------------------------
# Per-entry scoring (four variants per entry)
# ---------------------------------------------------------------------------
@dataclass
class VariantMetrics:
    retrieval_at_10: float | None
    ndcg_at_10: float | None
    mrr: float | None
    sub_question_recalls: list[float]


@dataclass
class EntryScore:
    qid: str
    variants: dict[str, VariantMetrics]
    router_match: bool | None
    retrieval_backend: str | None
    reranker_mode: str | None


def _score_one_variant(
    ranked_main: Sequence[str],
    expected_main: Sequence[str],
    sub_question_ranked: list[tuple[Sequence[str], Sequence[str]]],
    *,
    top_k: int,
    strict: bool,
) -> VariantMetrics:
    recall = recall_at_k(ranked_main, expected_main, top_k, strict=strict)
    ndcg = ndcg_at_k(ranked_main, expected_main, top_k, strict=strict)
    mrr = reciprocal_rank(ranked_main, expected_main, strict=strict)

    sub_recalls: list[float] = []
    for ranked, expected in sub_question_ranked:
        if not expected:
            continue
        r = recall_at_k(ranked, expected, top_k, strict=strict)
        if r is not None:
            sub_recalls.append(r)
    return VariantMetrics(
        retrieval_at_10=recall,
        ndcg_at_10=ndcg,
        mrr=mrr,
        sub_question_recalls=sub_recalls,
    )


def _variant_ranked(result: RetrievalResult, variant: str) -> Sequence[str]:
    if variant.startswith("primary_only"):
        return result.ranked_primary_only
    return result.ranked_with_connected


def _score_entry(
    entry: GoldEntry,
    *,
    top_k: int,
    fire_sub_questions: bool,
) -> EntryScore:
    main = retrieve_for_query(entry.initial_question_es, top_k=top_k)

    # Gather sub-question retrievals once per scope. For S-type, the main
    # query doubles as its own sub-question (macro aggregation puts one
    # weight per user intent; expert verdict preferred macro over micro
    # for regulated domain).
    sub_pairs_by_scope: dict[str, list[tuple[Sequence[str], Sequence[str]]]] = {
        "primary_only": [],
        "with_connected": [],
    }
    if fire_sub_questions and entry.sub_questions:
        for sq in entry.sub_questions:
            if not sq.expected_article_keys:
                continue
            sub_result = retrieve_for_query(sq.text_es, top_k=top_k)
            sub_pairs_by_scope["primary_only"].append(
                (sub_result.ranked_primary_only, sq.expected_article_keys)
            )
            sub_pairs_by_scope["with_connected"].append(
                (sub_result.ranked_with_connected, sq.expected_article_keys)
            )
    elif entry.expected_article_keys:
        sub_pairs_by_scope["primary_only"].append(
            (main.ranked_primary_only, entry.expected_article_keys)
        )
        sub_pairs_by_scope["with_connected"].append(
            (main.ranked_with_connected, entry.expected_article_keys)
        )

    variants: dict[str, VariantMetrics] = {}
    for key in VARIANT_KEYS:
        scope = "primary_only" if key.startswith("primary_only") else "with_connected"
        strict = key.endswith("_strict")
        variants[key] = _score_one_variant(
            ranked_main=_variant_ranked(main, key),
            expected_main=entry.expected_article_keys,
            sub_question_ranked=sub_pairs_by_scope[scope],
            top_k=top_k,
            strict=strict,
        )

    # Router accuracy (renamed from topic_accuracy). Uncertain entries
    # drop out of both numerator and denominator until the curator rules.
    if entry.expected_topic_uncertain or entry.expected_topic is None:
        router_match: bool | None = None
    else:
        router_match = (main.effective_topic or "").strip() == entry.expected_topic

    return EntryScore(
        qid=entry.qid,
        variants=variants,
        router_match=router_match,
        retrieval_backend=main.retrieval_backend,
        reranker_mode=main.reranker_mode,
    )


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------
def _mean(values: Iterable[float | None]) -> float | None:
    lst = [v for v in values if v is not None]
    if not lst:
        return None
    return sum(lst) / len(lst)


def _mean_bool(values: Iterable[bool | None]) -> tuple[float | None, int]:
    filtered = [v for v in values if v is not None]
    if not filtered:
        return None, 0
    hits = sum(1 for v in filtered if v)
    return hits / len(filtered), len(filtered)


@dataclass
class VariantAggregate:
    retrieval_at_10: float | None
    ndcg_at_10: float | None
    mrr: float | None
    sub_question_recall_at_10: float | None
    sub_question_count: int


@dataclass
class Aggregate:
    entry_scores: list[EntryScore]
    variants: dict[str, VariantAggregate]
    router_accuracy: float | None
    router_denominator: int

    def to_metrics_dict(self) -> dict[str, Any]:
        return {
            "variants": {
                key: {
                    "retrieval_at_10": v.retrieval_at_10,
                    "ndcg_at_10": v.ndcg_at_10,
                    "mrr": v.mrr,
                    "sub_question_recall_at_10": v.sub_question_recall_at_10,
                    "sub_question_count": v.sub_question_count,
                }
                for key, v in self.variants.items()
            },
            "router_accuracy": self.router_accuracy,
            "router_denominator": self.router_denominator,
        }


def aggregate(entry_scores: list[EntryScore]) -> Aggregate:
    variants: dict[str, VariantAggregate] = {}
    for key in VARIANT_KEYS:
        per_entry = [e.variants[key] for e in entry_scores]
        all_sub_recalls: list[float] = []
        for vm in per_entry:
            all_sub_recalls.extend(vm.sub_question_recalls)
        variants[key] = VariantAggregate(
            retrieval_at_10=_mean(vm.retrieval_at_10 for vm in per_entry),
            ndcg_at_10=_mean(vm.ndcg_at_10 for vm in per_entry),
            mrr=_mean(vm.mrr for vm in per_entry),
            sub_question_recall_at_10=(
                sum(all_sub_recalls) / len(all_sub_recalls) if all_sub_recalls else None
            ),
            sub_question_count=len(all_sub_recalls),
        )

    router_acc, router_denom = _mean_bool(e.router_match for e in entry_scores)
    return Aggregate(
        entry_scores=entry_scores,
        variants=variants,
        router_accuracy=router_acc,
        router_denominator=router_denom,
    )


# ---------------------------------------------------------------------------
# Baseline I/O + regression gate
# ---------------------------------------------------------------------------
def _flatten_metrics(agg: Aggregate) -> dict[str, float | None]:
    """Produce a flat {metric_name: value} map suitable for regression diffing."""
    flat: dict[str, float | None] = {"router_accuracy": agg.router_accuracy}
    for variant_key, v in agg.variants.items():
        flat[f"{variant_key}.retrieval_at_10"] = v.retrieval_at_10
        flat[f"{variant_key}.ndcg_at_10"] = v.ndcg_at_10
        flat[f"{variant_key}.mrr"] = v.mrr
        flat[f"{variant_key}.sub_question_recall_at_10"] = v.sub_question_recall_at_10
    return flat


def dump_baseline(
    agg: Aggregate,
    path: Path,
    *,
    gold_path: Path,
    methodology: dict[str, Any],
) -> None:
    """`methodology` is the frozen set of run flags this baseline was generated
    under (e.g. ``{"skip_sub_questions": True, "top_k": 10, "reranker_mode": "shadow"}``).
    The regression gate refuses to compare across different methodology, so a
    change of flags forces an explicit ``--update-baseline`` rather than
    silently comparing apples to oranges.
    """
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gold_path": str(gold_path),
        "gold_entry_count": len(agg.entry_scores),
        "router_denominator": agg.router_denominator,
        "methodology": methodology,
        "metrics": _flatten_metrics(agg),
        "aggregate": agg.to_metrics_dict(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_baseline(path: Path) -> tuple[dict[str, float | None], dict[str, Any]] | None:
    """Return ``(metrics, methodology)`` or ``None`` if no baseline is committed."""
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


def methodology_matches(
    current: dict[str, Any], baseline: dict[str, Any]
) -> list[str]:
    """Return a list of mismatch descriptions (empty = methodology matches).

    Treats missing keys as "unknown" — a pre-methodology-field baseline
    compares permissively so old baselines don't auto-break CI. Once both
    sides declare, any difference is a hard mismatch.
    """
    mismatches: list[str] = []
    for key, cur_val in current.items():
        if key not in baseline:
            continue
        if baseline[key] != cur_val:
            mismatches.append(
                f"{key}: current={cur_val!r}, baseline={baseline[key]!r}"
            )
    return mismatches


def compute_regressions(
    current: dict[str, float | None],
    baseline: dict[str, float | None],
    *,
    tolerance_pp: float,
) -> list[str]:
    """All reported retrieval metrics are higher-is-better. A regression is a
    drop by more than `tolerance_pp / 100.0` in absolute points. Metrics that
    were `None` in the baseline or current are skipped (denominator=0 etc).
    """
    tol = tolerance_pp / 100.0
    failures: list[str] = []
    for key, base_val in baseline.items():
        if base_val is None:
            continue
        cur_val = current.get(key)
        if cur_val is None:
            failures.append(f"{key}: current=None, baseline={base_val:.3f} — metric disappeared")
            continue
        delta = cur_val - base_val
        if delta < -tol:
            failures.append(
                f"{key}: {cur_val:.3f} vs baseline {base_val:.3f} (Δ={delta:+.3f}, tolerance -{tol:.3f})"
            )
    return failures


def check_red_lines(agg: Aggregate) -> list[str]:
    """Aspirational check — reports which red lines fail against the default
    display variant (`with_connected_loose`). Not the CI gate.
    """
    v = agg.variants[DEFAULT_DISPLAY_VARIANT]
    failures: list[str] = []
    for name, floor in ASPIRATIONAL_RED_LINES.items():
        if name == "retrieval_at_10":
            value = v.retrieval_at_10
        elif name == "sub_question_recall_at_10":
            value = v.sub_question_recall_at_10
        elif name == "router_accuracy":
            value = agg.router_accuracy
        else:
            continue
        if value is None:
            failures.append(f"{name}: no data (denominator=0)")
        elif value < floor:
            failures.append(f"{name}: {value:.3f} < red line {floor:.2f}")
    return failures


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------
def _fmt(value: float | None, width: int = 5) -> str:
    if value is None:
        return f"{'n/a':>{width}s}"
    return f"{value:>{width}.3f}"


def _delta_str(current: float | None, baseline: float | None) -> str:
    if current is None or baseline is None:
        return "   n/a"
    d = current - baseline
    return f"{d:+.3f}"


def render_human(
    agg: Aggregate,
    *,
    gold_path: Path,
    top_k: int,
    baseline_metrics: dict[str, float | None] | None,
    tolerance_pp: float,
) -> str:
    lines: list[str] = []
    lines.append(f"# Eval harness — {gold_path} ({len(agg.entry_scores)} entries, top-k={top_k})")
    lines.append("")
    backends = {e.retrieval_backend for e in agg.entry_scores if e.retrieval_backend}
    rerankers = {e.reranker_mode for e in agg.entry_scores if e.reranker_mode}
    if backends:
        lines.append(f"  retrieval_backend seen: {sorted(backends)}")
    if rerankers:
        lines.append(f"  reranker_mode seen:     {sorted(rerankers)}")
    lines.append("")

    # Router accuracy (separate from the retrieval matrix — it's a
    # different question entirely, about the resolver not the pipeline).
    lines.append("## Router accuracy (resolver, not pipeline)")
    lines.append(
        f"  router_accuracy = {_fmt(agg.router_accuracy, 5)}   n={agg.router_denominator}"
    )
    lines.append("")

    # 2×2 retrieval matrix
    lines.append("## Retrieval metrics — 2×2 matrix (scope × normalizer)")
    lines.append("")
    lines.append("  Metric                   primary_only            with_connected")
    lines.append("                           strict      loose       strict      loose")
    for metric_key, metric_label in (
        ("retrieval_at_10", "retrieval@10"),
        ("ndcg_at_10", "nDCG@10"),
        ("mrr", "MRR"),
        ("sub_question_recall_at_10", "sub_q_recall@10"),
    ):
        row = [f"  {metric_label:<24s}"]
        for scope in ("primary_only", "with_connected"):
            for strict_tag in ("strict", "loose"):
                variant = f"{scope}_{strict_tag}"
                v = agg.variants[variant]
                value = getattr(v, metric_key)
                row.append(f" {_fmt(value, 9)}")
        lines.append("".join(row))
    lines.append("")
    lines.append(
        "  The loose − strict delta tells you how much of the metric is "
        "'at the anchor' vs 'in the anchor's parent container'."
    )
    lines.append(
        "  The with_connected − primary_only delta tells you how much graph "
        "expansion is rescuing vs the planner's direct anchors."
    )
    lines.append("")

    # Regression gate vs baseline
    lines.append(f"## Regression vs baseline (tolerance -{tolerance_pp:.1f}pp)")
    if baseline_metrics is None:
        lines.append("  No baseline file — run `--update-baseline` to commit one.")
    else:
        current = _flatten_metrics(agg)
        shown = 0
        for metric_key in sorted(baseline_metrics.keys()):
            base = baseline_metrics[metric_key]
            cur = current.get(metric_key)
            if base is None and cur is None:
                continue
            delta = _delta_str(cur, base)
            tol = tolerance_pp / 100.0
            status = "  OK"
            if cur is not None and base is not None and (cur - base) < -tol:
                status = "  FAIL"
            lines.append(
                f"  {metric_key:<56s} {_fmt(cur, 6)} vs {_fmt(base, 6)}  Δ={delta}  {status}"
            )
            shown += 1
        if shown == 0:
            lines.append("  baseline has no comparable metrics")
    lines.append("")

    # Aspirational red lines (human reminder, not gating)
    lines.append(
        f"## Aspirational red lines (report only — variant: {DEFAULT_DISPLAY_VARIANT})"
    )
    v = agg.variants[DEFAULT_DISPLAY_VARIANT]
    for name, floor in ASPIRATIONAL_RED_LINES.items():
        if name == "retrieval_at_10":
            value = v.retrieval_at_10
        elif name == "sub_question_recall_at_10":
            value = v.sub_question_recall_at_10
        elif name == "router_accuracy":
            value = agg.router_accuracy
        else:
            continue
        flag = ""
        if value is not None:
            flag = "  OK" if value >= floor else "  FAIL"
        lines.append(f"  {name:<30s} {_fmt(value, 5)}   target >= {floor:.2f}{flag}")
    lines.append("")

    # Per-entry breakdown (default variant)
    lines.append(f"## Per-entry breakdown (variant: {DEFAULT_DISPLAY_VARIANT})")
    lines.append(
        f"  {'qid':<6s} {'r@10':>6s} {'nDCG':>6s} {'MRR':>6s} {'router':>7s}  {'#sq':>4s}"
    )
    for e in agg.entry_scores:
        v = e.variants[DEFAULT_DISPLAY_VARIANT]
        router_str = {True: "    OK", False: "  FAIL", None: "   n/a"}[e.router_match]
        lines.append(
            f"  {e.qid:<6s} {_fmt(v.retrieval_at_10, 5)} {_fmt(v.ndcg_at_10, 5)} "
            f"{_fmt(v.mrr, 5)} {router_str:>7s}  {len(v.sub_question_recalls):>4d}"
        )
    lines.append("")
    lines.append(
        "Note: `subtopic_accuracy` is intentionally not reported. Gold "
        "`expected_subtopic` slugs need to be re-indexed against "
        "`config/subtopic_taxonomy.json` by the accountant before the "
        "metric becomes meaningful."
    )
    return "\n".join(lines)


def render_json(
    agg: Aggregate,
    *,
    baseline_metrics: dict[str, float | None] | None,
    tolerance_pp: float,
) -> str:
    current = _flatten_metrics(agg)
    regressions: list[str] = []
    if baseline_metrics is not None:
        regressions = compute_regressions(current, baseline_metrics, tolerance_pp=tolerance_pp)
    payload = {
        "aggregate": agg.to_metrics_dict(),
        "current_metrics_flat": current,
        "baseline_metrics_flat": baseline_metrics,
        "regressions": regressions,
        "tolerance_pp": tolerance_pp,
        "aspirational_red_lines": dict(ASPIRATIONAL_RED_LINES),
        "default_display_variant": DEFAULT_DISPLAY_VARIANT,
        "entries": [
            {
                "qid": e.qid,
                "router_match": e.router_match,
                "retrieval_backend": e.retrieval_backend,
                "reranker_mode": e.reranker_mode,
                "variants": {
                    k: {
                        "retrieval_at_10": v.retrieval_at_10,
                        "ndcg_at_10": v.ndcg_at_10,
                        "mrr": v.mrr,
                        "sub_question_recalls": v.sub_question_recalls,
                    }
                    for k, v in e.variants.items()
                },
            }
            for e in agg.entry_scores
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Retrieval eval harness (structural backlog #1).")
    parser.add_argument(
        "--gold",
        type=Path,
        default=Path("evals/gold_retrieval_v1.jsonl"),
    )
    parser.add_argument("--top-k", type=int, default=TOP_K_DEFAULT)
    parser.add_argument(
        "--skip-sub-questions",
        action="store_true",
        help="Skip per-sub-question fanout for M-type entries (faster smoke).",
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--baseline",
        type=Path,
        default=BASELINE_PATH_DEFAULT,
        help=f"Path to the committed baseline JSON (default: {BASELINE_PATH_DEFAULT}).",
    )
    parser.add_argument(
        "--fail-on-regression",
        action="store_true",
        help="CI gate: exit non-zero if any metric regressed more than --tolerance-pp vs the baseline.",
    )
    parser.add_argument(
        "--tolerance-pp",
        type=float,
        default=TOLERANCE_PP_DEFAULT,
        help=f"Regression tolerance in percentage points (default: {TOLERANCE_PP_DEFAULT}).",
    )
    parser.add_argument(
        "--fail-under-red-lines",
        action="store_true",
        help="Aspirational mode — exit non-zero if any red line fails on the default display variant. NOT the CI gate.",
    )
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Overwrite the baseline file with the current run's metrics. Use after a judged improvement.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional: also write the full JSON payload to this path.",
    )
    args = parser.parse_args(argv)

    entries = load_gold(args.gold)
    if not entries:
        print(f"[eval_retrieval] gold file is empty: {args.gold}", file=sys.stderr)
        return 2

    scored: list[EntryScore] = []
    for entry in entries:
        scored.append(
            _score_entry(
                entry,
                top_k=args.top_k,
                fire_sub_questions=not args.skip_sub_questions,
            )
        )
    agg = aggregate(scored)

    import os as _os
    current_methodology: dict[str, Any] = {
        "skip_sub_questions": bool(args.skip_sub_questions),
        "top_k": int(args.top_k),
        "reranker_mode": str(_os.getenv("LIA_RERANKER_MODE", "off")).strip().lower() or "off",
        "decompose_enabled": str(_os.getenv("LIA_QUERY_DECOMPOSE", "off")).strip().lower() == "on",
    }

    loaded = load_baseline(args.baseline)
    baseline_metrics: dict[str, float | None] | None = None
    baseline_methodology: dict[str, Any] = {}
    if loaded is not None:
        baseline_metrics, baseline_methodology = loaded

    if args.update_baseline:
        dump_baseline(
            agg,
            args.baseline,
            gold_path=args.gold,
            methodology=current_methodology,
        )
        print(f"[eval_retrieval] baseline written: {args.baseline}", file=sys.stderr)

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
                top_k=args.top_k,
                baseline_metrics=baseline_metrics,
                tolerance_pp=args.tolerance_pp,
            )
        )

    exit_code = 0
    if args.fail_on_regression:
        if baseline_metrics is None:
            print(
                f"[eval_retrieval] --fail-on-regression requested but no baseline at {args.baseline}",
                file=sys.stderr,
            )
            return 3
        method_mismatches = methodology_matches(current_methodology, baseline_methodology)
        if method_mismatches:
            print("", file=sys.stderr)
            print(
                "[eval_retrieval] METHODOLOGY MISMATCH vs baseline — refusing to gate:",
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
            _flatten_metrics(agg), baseline_metrics, tolerance_pp=args.tolerance_pp
        )
        if regressions:
            print("", file=sys.stderr)
            print(
                f"[eval_retrieval] REGRESSION (tolerance -{args.tolerance_pp:.1f}pp):",
                file=sys.stderr,
            )
            for msg in regressions:
                print(f"  - {msg}", file=sys.stderr)
            exit_code = 1

    if args.fail_under_red_lines:
        failures = check_red_lines(agg)
        if failures:
            print("", file=sys.stderr)
            print("[eval_retrieval] ASPIRATIONAL RED LINE FAILURES:", file=sys.stderr)
            for msg in failures:
                print(f"  - {msg}", file=sys.stderr)
            exit_code = exit_code or 1

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
