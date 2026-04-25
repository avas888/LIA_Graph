#!/usr/bin/env python3
"""ingestionfix_v3 Phase 2.5 Task A.2 — rich per-doc orphan rescue.

After the batched ``sector_classify.py`` loose + strict passes, a residual
~15% of the docs are "effective orphans" — genuinely miscellaneous OR
disguised-catch-all labels (``sector_otros*``) that the strict prompt
couldn't break through. This tool runs a DIFFERENT shape of LLM call:

* **Per-doc**, not batched. Each orphan gets its own Gemini call with
  the full doc content (up to 3,000 chars) — max context to reason over.
* **Closed-world classification target**: the prompt shows the LLM
  ALL known topics (39 existing + ~30 new sectors proposed by the
  batched passes) as a single list. The model picks from that list OR
  proposes a brand-new sector OR declares true orphan — but it can't
  hand-wave with a vague migrate-to-catchall.
* **Richer prompt**: asks "what is this document most about?" before
  "does it fit any of these?" — gives the model room to reason about
  content semantically instead of pattern-matching titles.

Input: orphan doc_ids, typically pulled from BOTH prior proposals (first-
pass ``kind=orphan`` + strict-pass ``kind=orphan`` + strict-pass
``sector_otros*`` labels). See ``--from-proposals`` convenience flag.

Output: ``artifacts/sector_classification_orphans/orphan_rescue_proposal.json``
+ per-doc checkpoint files under ``…/per_doc/<doc_id>.json``. Same
durability shape as ``sector_classify.py`` but finer-grained.

**Same durability contract**: atomic per-doc writes (temp+rename),
resumable on restart, visible heartbeat every doc, SIGINT-safe.

See ``docs/done/next/UI_Ingestion_learnings.md §11.4`` for the pipeline
placement (this is "Pass 3 — rich per-doc" of the Rescue-from-Other
playbook).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import signal
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

BOG = _dt.timezone(_dt.timedelta(hours=-5))

DEFAULT_MODEL = "gemini-2.5-flash"
# Rough cost estimator; gemini-2.5-flash OpenAI-compatible pricing.
COST_PER_1K_INPUT_TOKENS_USD = 0.0003
COST_PER_1K_OUTPUT_TOKENS_USD = 0.0025


# ── Content loader (shared shape with sector_classify) ───────────────


def _doc_id_to_path_candidates(doc_id: str, repo_root: Path) -> list[Path]:
    name = doc_id
    if name.startswith("CORE_ya_Arriba_"):
        rest = name[len("CORE_ya_Arriba_"):]
    else:
        rest = name
    parts = rest.rsplit("_", 1)
    if len(parts) == 2:
        prefix, leaf = parts
        prefix_slashed = prefix.replace("_", "/")
        return [
            repo_root / "knowledge_base" / "CORE ya Arriba" / prefix_slashed / leaf,
            repo_root / "knowledge_base" / "CORE ya Arriba" / rest.replace("_", "/"),
        ]
    return [repo_root / "knowledge_base" / "CORE ya Arriba" / rest.replace("_", "/")]


def load_doc_rich(
    doc_id: str, repo_root: Path, *, max_chars: int = 3000
) -> tuple[str, str]:
    """Return (title, content) — title = first heading, content = up to
    max_chars of body (default 3000, vs sector_classify's ~1200). The
    per-doc prompt can afford more context since we're making one call
    per doc.
    """
    candidates = _doc_id_to_path_candidates(doc_id, repo_root)
    content = ""
    for path in candidates:
        if path.exists():
            content = path.read_text(encoding="utf-8", errors="replace")
            break
    if not content:
        return "", ""
    lines = content.splitlines()
    title = ""
    for line in lines:
        stripped = line.strip()
        if stripped:
            title = stripped.lstrip("# ").strip()
            break
    body = content[:max_chars].strip()
    return title, body


# ── Taxonomy + sector label sources ─────────────────────────────────


def load_existing_topics(taxonomy_path: Path) -> list[str]:
    data = json.loads(taxonomy_path.read_text(encoding="utf-8"))
    return [t["key"] for t in data.get("topics", []) if not t.get("parent_key")]


def extract_proposed_sectors(
    proposal_paths: list[Path], *, min_count: int = 1
) -> list[str]:
    """Union of new-sector labels proposed across previous proposals.

    Filter out ``sector_otros*`` labels (disguised catch-all — we're
    specifically trying to escape those).
    """
    labels: dict[str, int] = {}
    for pp in proposal_paths:
        if not pp.exists():
            continue
        data = json.loads(pp.read_text(encoding="utf-8"))
        for r in data.get("results", []):
            if r.get("kind") != "new_sector":
                continue
            topic = str(r.get("proposed_topic") or "")
            if not topic.startswith("sector_"):
                continue
            if topic.startswith(("sector_otros", "sector_misc", "sector_varios")):
                continue
            labels[topic] = labels.get(topic, 0) + 1
    return sorted(k for k, v in labels.items() if v >= min_count)


def collect_orphan_doc_ids(
    proposal_paths: list[Path], *, include_sector_otros: bool = True
) -> list[str]:
    """Pull every orphan-ish doc_id from the prior proposals.

    Includes: kind='orphan' + (optionally) kind='new_sector' with
    proposed_topic like 'sector_otros*' (the disguised-catch-all
    loophole the strict pass couldn't close).
    """
    seen: set[str] = set()
    out: list[str] = []
    for pp in proposal_paths:
        if not pp.exists():
            continue
        data = json.loads(pp.read_text(encoding="utf-8"))
        for r in data.get("results", []):
            did = str(r.get("doc_id") or "")
            if not did or did in seen:
                continue
            kind = r.get("kind", "")
            topic = str(r.get("proposed_topic") or "")
            if kind == "orphan" or (
                include_sector_otros
                and kind == "new_sector"
                and topic.startswith(("sector_otros", "sector_misc", "sector_varios"))
            ):
                seen.add(did)
                out.append(did)
    return out


# ── Prompt + Gemini call ─────────────────────────────────────────────


_ORPHAN_PROMPT_TEMPLATE = """Eres un experto contador colombiano. Te muestro UN documento normativo que ninguna de nuestras heurísticas anteriores pudo clasificar bien. Necesito que lo leas con atención y me digas exactamente dónde pertenece.

Primero, responde en español con un breve análisis (2-3 oraciones) de:
- ¿De qué trata principalmente este documento?
- ¿Cuál es el sector o área temática dominante?

Segundo, toma UNA decisión entre estas tres opciones:

OPCIÓN 1 — ENCAJA EN UN TOPIC YA EXISTENTE:
Estos son los topics disponibles en nuestra taxonomía actual (39 topics existentes + {sector_count} sectores nuevos recién propuestos). Elige EXACTAMENTE UNO si el documento encaja bien:

{topic_list}

OPCIÓN 2 — PROPONER UN NUEVO SECTOR que no está en la lista:
Si ninguno encaja pero el documento es claramente sectorial, propón un nombre `sector_*` en snake_case que describa el área temática. NO uses `sector_otros` ni variantes genéricas — esas están PROHIBIDAS.

OPCIÓN 3 — HUÉRFANO VERDADERO:
Solo si el documento realmente no trata ningún tema reconocible y no puede agruparse. Usa con extrema cautela — preferir OPCIÓN 2 siempre que haya señal sectorial.

Responde SOLO con este JSON exacto, sin prosa adicional, sin markdown, sin ```json:

{{"analysis": "breve análisis en español (2-3 oraciones)", "decision": "existing|new_sector|orphan", "topic_key": "exact_key_from_list_OR_new_sector_label_OR_orphan", "confidence": "high|medium|low", "reasoning": "por qué este topic es el correcto, máx 25 palabras"}}

---

DOCUMENTO:

**Título:** {title}

**Contenido:**
{content}
"""


@dataclass
class OrphanResult:
    doc_id: str
    title: str
    analysis: str
    decision: str  # existing | new_sector | orphan | error
    topic_key: str
    confidence: str
    reasoning: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "analysis": self.analysis,
            "decision": self.decision,
            "topic_key": self.topic_key,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
        }

    @classmethod
    def error(cls, doc_id: str, title: str, reason: str) -> "OrphanResult":
        return cls(
            doc_id=doc_id,
            title=title,
            analysis="",
            decision="error",
            topic_key="orphan",
            confidence="n/a",
            reasoning=reason[:240],
        )


def _extract_json_object(raw: str) -> dict[str, Any]:
    stripped = raw.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    lb = stripped.find("{")
    rb = stripped.rfind("}")
    if lb == -1 or rb == -1 or rb <= lb:
        raise ValueError("no JSON object found")
    return json.loads(stripped[lb : rb + 1])


def classify_one_orphan(
    adapter: Any,
    *,
    doc_id: str,
    title: str,
    content: str,
    closed_world_topics: list[str],
    total_sectors_in_list: int,
) -> OrphanResult:
    topic_list = "\n".join(f"  - {t}" for t in closed_world_topics)
    prompt = _ORPHAN_PROMPT_TEMPLATE.format(
        topic_list=topic_list,
        sector_count=total_sectors_in_list,
        title=title,
        content=content,
    )
    try:
        raw = adapter.generate(prompt)
        obj = _extract_json_object(raw)
    except Exception as exc:
        return OrphanResult.error(doc_id, title, f"llm_or_parse_failed: {exc}")

    decision = str(obj.get("decision") or "").strip().lower()
    if decision not in ("existing", "new_sector", "orphan"):
        decision = "orphan"
    return OrphanResult(
        doc_id=doc_id,
        title=title,
        analysis=str(obj.get("analysis") or "")[:400],
        decision=decision,
        topic_key=str(obj.get("topic_key") or "orphan")[:80],
        confidence=str(obj.get("confidence") or "low"),
        reasoning=str(obj.get("reasoning") or "")[:240],
    )


# ── Checkpoint helpers ──────────────────────────────────────────────


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(tmp, path)


def _safe_filename(doc_id: str) -> str:
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in doc_id)[:120] + ".json"


# ── Orchestrator ────────────────────────────────────────────────────


def _estimate_cost(prompt_chars: int, output_chars: int) -> float:
    in_tok = prompt_chars / 4
    out_tok = output_chars / 4
    return (
        in_tok / 1000 * COST_PER_1K_INPUT_TOKENS_USD
        + out_tok / 1000 * COST_PER_1K_OUTPUT_TOKENS_USD
    )


def _bog_time(dt: _dt.datetime) -> str:
    return dt.astimezone(BOG).strftime("%-I:%M:%S %p").lstrip("0")


def run(
    *,
    doc_ids: list[str],
    output_dir: Path,
    taxonomy_path: Path,
    proposed_sector_sources: list[Path],
    repo_root: Path,
    model: str,
    api_key: str,
    dry_run: bool = False,
) -> int:
    from lia_graph.gemini_runtime import (
        GeminiChatAdapter,
        DEFAULT_GEMINI_OPENAI_BASE_URL,
    )

    existing_topics = load_existing_topics(taxonomy_path)
    proposed_sectors = extract_proposed_sectors(proposed_sector_sources)
    closed_world = list(existing_topics) + proposed_sectors
    # Dedup while preserving order.
    seen: set[str] = set()
    closed_world = [t for t in closed_world if not (t in seen or seen.add(t))]

    print(
        f"[orphan_rescue] closed-world target list: "
        f"{len(existing_topics)} existing topics + {len(proposed_sectors)} proposed sectors "
        f"= {len(closed_world)} options.",
        flush=True,
    )
    print(f"[orphan_rescue] {len(doc_ids)} orphan docs to classify.", flush=True)

    per_doc_dir = output_dir / "per_doc"
    per_doc_dir.mkdir(parents=True, exist_ok=True)

    adapter = None
    if not dry_run:
        adapter = GeminiChatAdapter(
            model=model,
            api_key=api_key,
            base_url=DEFAULT_GEMINI_OPENAI_BASE_URL,
            timeout_seconds=60.0,
            temperature=0.1,
        )

    # SIGINT-safe: existing per-doc files persist; interrupted doc just retries.
    current_did: list[str] = [""]

    def _on_sigint(signum: int, frame: Any) -> None:
        print(
            f"\n[orphan_rescue] interrupted while processing {current_did[0] or '(between docs)'}; resume later",
            file=sys.stderr,
        )
        sys.exit(130)

    signal.signal(signal.SIGINT, _on_sigint)
    signal.signal(signal.SIGTERM, _on_sigint)

    results: list[OrphanResult] = []
    total_cost = 0.0
    t_run_start = time.time()
    decision_hist: dict[str, int] = {"existing": 0, "new_sector": 0, "orphan": 0, "error": 0}
    topic_hist: dict[str, int] = {}

    for i, did in enumerate(doc_ids, start=1):
        current_did[0] = did
        per_doc_path = per_doc_dir / _safe_filename(did)
        if per_doc_path.exists():
            # Resume: reuse cached result.
            try:
                cached = json.loads(per_doc_path.read_text(encoding="utf-8"))
                r = OrphanResult(
                    doc_id=cached["doc_id"],
                    title=cached.get("title", ""),
                    analysis=cached.get("analysis", ""),
                    decision=cached.get("decision", "orphan"),
                    topic_key=cached.get("topic_key", "orphan"),
                    confidence=cached.get("confidence", "low"),
                    reasoning=cached.get("reasoning", ""),
                )
                results.append(r)
                decision_hist[r.decision] = decision_hist.get(r.decision, 0) + 1
                topic_hist[r.topic_key] = topic_hist.get(r.topic_key, 0) + 1
                continue
            except Exception:
                pass  # fall through to re-classify

        title, body = load_doc_rich(did, repo_root)
        t0 = time.time()
        if dry_run:
            r = OrphanResult(
                doc_id=did,
                title=title,
                analysis="dry-run stub",
                decision="orphan",
                topic_key="orphan",
                confidence="low",
                reasoning="dry-run",
            )
        else:
            assert adapter is not None
            r = classify_one_orphan(
                adapter,
                doc_id=did,
                title=title,
                content=body,
                closed_world_topics=closed_world,
                total_sectors_in_list=len(proposed_sectors),
            )
        elapsed = time.time() - t0

        _atomic_write_json(per_doc_path, r.to_dict())
        results.append(r)
        decision_hist[r.decision] = decision_hist.get(r.decision, 0) + 1
        topic_hist[r.topic_key] = topic_hist.get(r.topic_key, 0) + 1

        prompt_chars = 2500 + len(body)
        output_chars = len(r.analysis) + len(r.reasoning) + 40
        total_cost += _estimate_cost(prompt_chars, output_chars)

        now = _dt.datetime.now(_dt.timezone.utc)
        top_topics = ", ".join(
            f"{k}={v}" for k, v in sorted(topic_hist.items(), key=lambda kv: -kv[1])[:5]
        )
        print(
            f"[orphan_rescue] {i:3d}/{len(doc_ids)} · {_bog_time(now)} · "
            f"{elapsed:4.1f}s · decision={r.decision:12s} · {r.topic_key[:40]:40s} "
            f"· conf={r.confidence:6s} · cost≈${total_cost:.3f}",
            flush=True,
        )
        current_did[0] = ""

    # Aggregate proposal.
    aggregate_path = output_dir / "orphan_rescue_proposal.json"
    summary = {
        "generated_at_utc": _dt.datetime.now(_dt.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "model": model,
        "total_docs": len(doc_ids),
        "total_classified": len(results),
        "decision_counts": decision_hist,
        "topic_key_counts": dict(
            sorted(topic_hist.items(), key=lambda kv: -kv[1])
        ),
        "closed_world_size": len(closed_world),
        "existing_topic_count": len(existing_topics),
        "proposed_sector_count": len(proposed_sectors),
        "estimated_cost_usd": round(total_cost, 4),
        "elapsed_seconds": round(time.time() - t_run_start, 1),
        "results": [r.to_dict() for r in results],
    }
    _atomic_write_json(aggregate_path, summary)
    print(
        f"\n[orphan_rescue] complete · {len(results)}/{len(doc_ids)} classified · "
        f"${total_cost:.3f} · {summary['elapsed_seconds']}s wall",
        flush=True,
    )
    print(
        f"[orphan_rescue] decisions: {decision_hist}",
        flush=True,
    )
    print(f"[orphan_rescue] proposal at {aggregate_path}", flush=True)
    return 0 if decision_hist.get("error", 0) == 0 else 1


# ── CLI ──────────────────────────────────────────────────────────────


def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="classify_orphans",
        description=(
            "Rich per-doc orphan rescue pass. Per-doc LLM calls with full "
            "content + closed-world taxonomy list (existing + newly proposed "
            "sectors). Same durability contract as sector_classify.py but "
            "finer-grained (atomic per-doc checkpoints, resumable, SIGINT-safe)."
        ),
    )
    p.add_argument(
        "--from-proposals",
        nargs="+",
        default=[
            "artifacts/sector_classification/sector_reclassification_proposal.json",
            "artifacts/sector_classification_strict/sector_reclassification_proposal.json",
        ],
        help="One or more prior proposals to harvest orphan doc_ids from.",
    )
    p.add_argument(
        "--output-dir",
        default="artifacts/sector_classification_orphans",
        help="Output directory for per-doc checkpoints + final proposal.",
    )
    p.add_argument(
        "--taxonomy",
        default="config/topic_taxonomy.json",
        help="Path to topic_taxonomy.json for the existing-topic list.",
    )
    p.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Gemini model (default {DEFAULT_MODEL}).",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip Gemini calls; use stub results.",
    )
    p.add_argument(
        "--max-docs",
        type=int,
        default=None,
        help="Classify at most N docs this run (for staged rollout).",
    )
    p.add_argument(
        "--include-sector-otros",
        action="store_true",
        default=True,
        help="Also include strict-pass 'sector_otros*' labels as orphans.",
    )
    return p


def main(argv: Iterable[str] | None = None) -> int:
    args = build_argparser().parse_args(list(argv) if argv is not None else None)
    repo_root = Path(__file__).resolve().parents[3]
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not args.dry_run and not api_key:
        print(
            "[orphan_rescue] ERROR: GEMINI_API_KEY not set. Source .env.local first.",
            file=sys.stderr,
        )
        return 2

    proposal_paths = [Path(p) for p in args.from_proposals]
    doc_ids = collect_orphan_doc_ids(
        proposal_paths, include_sector_otros=args.include_sector_otros
    )
    if args.max_docs is not None:
        doc_ids = doc_ids[: args.max_docs]

    return run(
        doc_ids=doc_ids,
        output_dir=Path(args.output_dir),
        taxonomy_path=Path(args.taxonomy),
        proposed_sector_sources=proposal_paths,
        repo_root=repo_root,
        model=args.model,
        api_key=api_key,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
