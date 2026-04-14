from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lia_contador.contracts import DocumentRecord
from lia_contador.pipeline_c.knowledge_bundle import _default_retriever


@dataclass(frozen=True)
class RetrievalCase:
    query: str
    pais: str
    topic: str | None
    gold_doc_ids: tuple[str, ...]
    gold_chunk_ids: tuple[str, ...]
    gold_chunk_prefixes: tuple[str, ...]


def _parse_case(payload: dict[str, Any]) -> RetrievalCase | None:
    query = str(payload.get("query", "")).strip()
    if not query:
        return None
    pais = str(payload.get("pais", "colombia")).strip().lower() or "colombia"
    topic_raw = payload.get("topic")
    topic = str(topic_raw).strip() if isinstance(topic_raw, str) and str(topic_raw).strip() else None
    gold_doc_ids = tuple(str(item).strip() for item in payload.get("gold_doc_ids", []) if str(item).strip())
    gold_chunk_ids = tuple(str(item).strip() for item in payload.get("gold_chunk_ids", []) if str(item).strip())
    gold_chunk_prefixes = tuple(
        str(item).strip() for item in payload.get("gold_chunk_prefixes", []) if str(item).strip()
    )
    if not gold_doc_ids and not gold_chunk_ids and not gold_chunk_prefixes:
        return None
    return RetrievalCase(
        query=query,
        pais=pais,
        topic=topic,
        gold_doc_ids=gold_doc_ids,
        gold_chunk_ids=gold_chunk_ids,
        gold_chunk_prefixes=gold_chunk_prefixes,
    )


def load_cases(dataset: Path) -> list[RetrievalCase]:
    cases: list[RetrievalCase] = []
    if not dataset.exists():
        return cases
    with dataset.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line)
            case = _parse_case(payload)
            if case is not None:
                cases.append(case)
    return cases


def _precision_at_k(relevance: list[bool], k: int) -> float:
    if k <= 0:
        return 0.0
    top = relevance[:k]
    if not top:
        return 0.0
    return sum(1 for rel in top if rel) / k


def _recall_at_k(relevance: list[bool], total_relevant: int, k: int) -> float:
    if total_relevant <= 0:
        return 0.0
    top = relevance[:k]
    return sum(1 for rel in top if rel) / total_relevant


def _mrr_at_k(relevance: list[bool], k: int) -> float:
    for idx, rel in enumerate(relevance[:k], start=1):
        if rel:
            return 1.0 / idx
    return 0.0


def _ndcg_at_k(relevance: list[bool], total_relevant: int, k: int) -> float:
    dcg = 0.0
    for idx, rel in enumerate(relevance[:k], start=1):
        if rel:
            dcg += 1.0 / math.log2(idx + 1)
    ideal_hits = min(total_relevant, k)
    if ideal_hits <= 0:
        return 0.0
    idcg = sum(1.0 / math.log2(i + 1) for i in range(1, ideal_hits + 1))
    if idcg <= 0.0:
        return 0.0
    return dcg / idcg


def _doc_relevant(result: DocumentRecord, case: RetrievalCase) -> bool:
    if not case.gold_doc_ids:
        return False
    return result.doc_id in set(case.gold_doc_ids)


def _chunk_relevant(result: DocumentRecord, case: RetrievalCase) -> bool:
    chunk_id = str(result.chunk_id or "").strip()
    if not chunk_id:
        return False
    if case.gold_chunk_ids and chunk_id in set(case.gold_chunk_ids):
        return True
    if case.gold_chunk_prefixes and any(chunk_id.startswith(prefix) for prefix in case.gold_chunk_prefixes):
        return True
    return False


def _run_profile(
    *,
    cases: list[RetrievalCase],
    index_file: Path,
    profile: str,
    enable_embeddings: str = "off",
) -> dict[str, Any]:
    retriever = _default_retriever(enable_embeddings=enable_embeddings)
    doc_ndcg10: list[float] = []
    doc_mrr10: list[float] = []
    doc_precision5: list[float] = []
    doc_recall20: list[float] = []
    ctx_precision10: list[float] = []
    ctx_recall10: list[float] = []
    case_rows: list[dict[str, Any]] = []

    for case in cases:
        docs = retriever.retrieve(
            query=case.query,
            top_k=20,
            index_file=index_file,
            topic=case.topic,
            pais=case.pais,
            retrieval_profile=profile,
        )
        doc_rel = [_doc_relevant(doc, case) for doc in docs]
        doc_total_relevant = max(len(case.gold_doc_ids), 1)

        doc_ndcg10.append(_ndcg_at_k(doc_rel, total_relevant=doc_total_relevant, k=10))
        doc_mrr10.append(_mrr_at_k(doc_rel, k=10))
        doc_precision5.append(_precision_at_k(doc_rel, k=5))
        doc_recall20.append(_recall_at_k(doc_rel, total_relevant=doc_total_relevant, k=20))

        has_chunk_labels = bool(case.gold_chunk_ids or case.gold_chunk_prefixes)
        if has_chunk_labels:
            chunk_rel = [_chunk_relevant(doc, case) for doc in docs]
            total_chunk_relevant = max(len(case.gold_chunk_ids) + len(case.gold_chunk_prefixes), 1)
            ctx_precision10.append(_precision_at_k(chunk_rel, k=10))
            ctx_recall10.append(_recall_at_k(chunk_rel, total_relevant=total_chunk_relevant, k=10))
            hit_chunk = any(chunk_rel[:10])
        else:
            ctx_precision10.append(_precision_at_k(doc_rel, k=10))
            ctx_recall10.append(_recall_at_k(doc_rel, total_relevant=doc_total_relevant, k=10))
            hit_chunk = any(doc_rel[:10])

        case_rows.append(
            {
                "query": case.query,
                "topic": case.topic,
                "pais": case.pais,
                "hits_doc_top10": int(sum(1 for rel in doc_rel[:10] if rel)),
                "hit_doc_top10": bool(any(doc_rel[:10])),
                "hit_context_top10": bool(hit_chunk),
                "top_result_doc_id": docs[0].doc_id if docs else None,
                "top_result_chunk_id": docs[0].chunk_id if docs else None,
            }
        )

    count = len(cases) or 1
    return {
        "profile": profile,
        "cases": len(cases),
        "metrics": {
            "ndcg_at_10": round(sum(doc_ndcg10) / count, 6),
            "mrr_at_10": round(sum(doc_mrr10) / count, 6),
            "precision_at_5": round(sum(doc_precision5) / count, 6),
            "recall_at_20": round(sum(doc_recall20) / count, 6),
            "context_precision_at_10": round(sum(ctx_precision10) / count, 6),
            "context_recall_at_10": round(sum(ctx_recall10) / count, 6),
        },
        "per_case": case_rows,
    }


def run(
    *,
    dataset: Path = Path("evals/rag_retrieval_benchmark.jsonl"),
    index: Path = Path("artifacts/document_index.jsonl"),
    profile: str = "hybrid_rerank",
    compare_baseline: bool = True,
    enable_embeddings: str = "off",
) -> dict[str, Any]:
    cases = load_cases(dataset)
    if not cases:
        return {
            "ok": False,
            "error": "dataset_empty_or_invalid",
            "dataset": str(dataset),
            "message": "No se encontraron casos validos con `query` y gold labels.",
        }

    result = {
        "ok": True,
        "dataset": str(dataset),
        "index": str(index),
        "target": _run_profile(cases=cases, index_file=index, profile=profile, enable_embeddings=enable_embeddings),
    }
    if compare_baseline:
        baseline = _run_profile(cases=cases, index_file=index, profile="baseline_keyword", enable_embeddings=enable_embeddings)
        result["baseline"] = baseline
        target_metrics = result["target"]["metrics"]
        baseline_metrics = baseline["metrics"]
        result["delta_vs_baseline"] = {
            key: round(float(target_metrics[key]) - float(baseline_metrics[key]), 6)
            for key in target_metrics
        }
    return result


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Evaluacion IR de retrieval para RAG LIA")
    p.add_argument("--dataset", default="evals/rag_retrieval_benchmark.jsonl")
    p.add_argument("--index", default="artifacts/document_index.jsonl")
    p.add_argument(
        "--profile",
        default="hybrid_rerank",
        choices=["baseline_keyword", "hybrid_rerank", "hybrid_semantic", "advanced_corrective"],
    )
    p.add_argument("--skip-baseline-compare", action="store_true")
    p.add_argument("--enable-embeddings", default="off", choices=["on", "off"])
    p.add_argument("--min-ndcg", type=float, default=None, help="Minimum nDCG@10 threshold (e.g. 0.50)")
    p.add_argument("--min-recall-20", type=float, default=None, help="Minimum recall@20 threshold (e.g. 0.85)")
    p.add_argument("--min-precision-5", type=float, default=None, help="Minimum precision@5 threshold (e.g. 0.60)")
    p.add_argument("--min-ctx-precision-10", type=float, default=None, help="Minimum context_precision@10 threshold")
    return p


def _check_metric_thresholds(
    metrics: dict[str, float],
    *,
    min_ndcg: float | None = None,
    min_recall_20: float | None = None,
    min_precision_5: float | None = None,
    min_ctx_precision_10: float | None = None,
) -> list[str]:
    """Return list of threshold violation descriptions (empty = all passed)."""
    failures: list[str] = []
    checks = [
        ("ndcg_at_10", min_ndcg),
        ("recall_at_20", min_recall_20),
        ("precision_at_5", min_precision_5),
        ("context_precision_at_10", min_ctx_precision_10),
    ]
    for metric_key, threshold in checks:
        if threshold is None:
            continue
        actual = float(metrics.get(metric_key, 0.0))
        if actual < threshold:
            failures.append(
                f"{metric_key}={actual:.4f} < {threshold:.4f}"
            )
    return failures


def main() -> int:
    args = parser().parse_args()
    report = run(
        dataset=Path(args.dataset),
        index=Path(args.index),
        profile=args.profile,
        compare_baseline=not args.skip_baseline_compare,
        enable_embeddings=args.enable_embeddings,
    )

    # Check metric thresholds if any are specified
    threshold_failures: list[str] = []
    if report.get("ok") and report.get("target"):
        target_metrics = report["target"].get("metrics", {})
        threshold_failures = _check_metric_thresholds(
            target_metrics,
            min_ndcg=args.min_ndcg,
            min_recall_20=args.min_recall_20,
            min_precision_5=args.min_precision_5,
            min_ctx_precision_10=args.min_ctx_precision_10,
        )
        if threshold_failures:
            report["ok"] = False
            report["threshold_failures"] = threshold_failures
            report["threshold_gate"] = "FAILED"
        else:
            report["threshold_gate"] = "PASSED"

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
