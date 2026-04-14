from __future__ import annotations

import json
from pathlib import Path

from lia_contador.retrieve import search


def run(dataset: Path = Path("evals/accountant_qa_es.jsonl"), index: Path = Path("artifacts/document_index.jsonl")) -> dict:
    total = 0
    with_hits = 0

    with dataset.open("r", encoding="utf-8") as f:
        for line in f:
            item = json.loads(line)
            total += 1
            hits = search(item["question"], top_k=3, index_file=index)
            if hits:
                with_hits += 1

    return {
        "cases": total,
        "retrieval_hit_rate": (with_hits / total) if total else 0.0,
    }


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
