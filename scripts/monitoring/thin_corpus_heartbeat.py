#!/usr/bin/env python3
"""Thin-corpus health heartbeat — v5 §1.D regression watcher.

Runs the 12 thin-corpus probe questions against a live Lia chat server
and reports per-topic served/refused state. Designed to catch regressions
in:

* `§1.A` — multi-topic ArticleNode metadata (article-level boosts)
* `§1.B` — compatible doc-topics map (document-level widening)
* `§1.D` — hybrid_search topic boost (ranking-level boost)

…and any future ingest change that breaks one of the 12 currently-known
thin-corpus topics.

Output shape:
    First line: `STATE: served=10/12 refused=2/12 baseline_drift=0`
    Body: per-topic table + diff vs baseline.

Exit codes:
    0 = all topics in expected state (no regression vs baseline).
    1 = regression detected (a SERVED topic is now refused).
    2 = improvement detected (a REFUSED topic is now served — operator
        should update the baseline).

Usage:
    PYTHONPATH=src:. uv run python scripts/monitoring/thin_corpus_heartbeat.py
    # optional: --baseline path/to/state.json (default: scripts/monitoring/thin_corpus_baseline.json)
    # optional: --server http://127.0.0.1:8787 (default)
    # optional: --update-baseline  (write the current state as new baseline)

Bogotá AM/PM render per repo convention.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any


_BOGOTA = timezone(timedelta(hours=-5), name="America/Bogota")


PROBES: tuple[tuple[str, str], ...] = (
    ("beneficio_auditoria",
     "¿Conviene tomar el beneficio de auditoría del Art. 689-3 ET para una PYME del año gravable 2025?"),
    ("firmeza_declaraciones",
     "¿En qué fecha queda en firme una declaración de renta del año gravable 2025 si NO tomo beneficio de auditoría, según el Art. 714 ET?"),
    ("regimen_sancionatorio_extemporaneidad",
     "¿Cómo se liquida la sanción del Art. 641 ET cuando declaro renta dos meses tarde y aplica reducción del 640?"),
    ("descuentos_tributarios_renta",
     "Una sociedad nacional invirtió en CTeI certificado por COLCIENCIAS. ¿Qué descuento permite el Art. 256 ET?"),
    ("tarifas_renta_y_ttd",
     "¿Cuál es la tarifa general de renta para sociedad nacional en 2026 y cómo aplica la TTD del parágrafo 6 del Art. 240 ET?"),
    ("dividendos_y_distribucion_utilidades",
     "¿Cuál es la tarifa especial sobre dividendos para personas naturales residentes en 2026 según Art. 242 ET?"),
    ("devoluciones_saldos_a_favor",
     "¿Cuál es el plazo del Art. 855 ET para que la DIAN devuelva un saldo a favor de IVA?"),
    ("perdidas_fiscales_art147",
     "¿Cuántos años tengo para compensar pérdidas fiscales según el Art. 147 ET y cómo afecta la firmeza?"),
    ("precios_de_transferencia",
     "¿Cuál es el plazo de firmeza para una declaración con obligación de precios de transferencia según Art. 260-5 ET?"),
    ("impuesto_patrimonio_personas_naturales",
     "¿Cuál es el umbral del impuesto al patrimonio para personas naturales según Art. 292-298 ET en 2026?"),
    ("regimen_cambiario",
     "¿Cuáles son las obligaciones de declaración cambiaria del Banco de la República para una IMC?"),
    ("conciliacion_fiscal",
     "¿Qué reportar en el formato 2516 para conciliar diferencias contables y fiscales?"),
)


SERVED_MODES = ("graph_native", "graph_native_partial")


def _bogota_now_str() -> str:
    return datetime.now(_BOGOTA).strftime("%Y-%m-%d %I:%M:%S %p Bogotá")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _probe_one(server: str, topic: str, message: str, timeout: float = 90.0) -> dict[str, Any]:
    url = f"{server.rstrip('/')}/api/chat"
    payload = json.dumps({"message": message, "pais": "colombia"}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
        latency_ms = int((time.monotonic() - t0) * 1000)
        d = json.loads(body)
        mode = d.get("answer_mode") or "?"
        fb = d.get("fallback_reason") or ""
        cites = len(d.get("citations") or [])
        eff = d.get("effective_topic") or "?"
        return {
            "topic": topic,
            "mode": mode,
            "fallback": fb,
            "cites": cites,
            "effective_topic": eff,
            "latency_ms": latency_ms,
            "served": mode in SERVED_MODES,
            "error": None,
        }
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as exc:
        return {
            "topic": topic,
            "mode": "ERR",
            "fallback": "",
            "cites": 0,
            "effective_topic": "?",
            "latency_ms": int((time.monotonic() - t0) * 1000),
            "served": False,
            "error": str(exc),
        }


def _emit_event(payload: dict[str, Any]) -> None:
    """Append to logs/events.jsonl for observability + cron polling."""
    out_path = Path("logs/events.jsonl")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "ts_utc": _utc_now_iso(),
        "event": "thin_corpus.heartbeat",
        **payload,
    }
    with out_path.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(record, ensure_ascii=False) + "\n")


def _load_baseline(path: Path) -> dict[str, bool]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return {k: bool(v) for k, v in (data.get("served") or {}).items()}


def _save_baseline(path: Path, results: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "captured_utc": _utc_now_iso(),
        "captured_bogota": _bogota_now_str(),
        "served": {r["topic"]: r["served"] for r in results},
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _diff_vs_baseline(
    results: list[dict[str, Any]], baseline: dict[str, bool]
) -> tuple[list[str], list[str]]:
    """Return (regressed_topics, improved_topics)."""
    regressed: list[str] = []
    improved: list[str] = []
    for r in results:
        topic = r["topic"]
        is_served = r["served"]
        was_served = baseline.get(topic)
        if was_served is None:
            continue
        if was_served and not is_served:
            regressed.append(topic)
        elif not was_served and is_served:
            improved.append(topic)
    return regressed, improved


def _render_block(
    results: list[dict[str, Any]],
    regressed: list[str],
    improved: list[str],
    baseline_known: bool,
    server: str,
) -> str:
    served = sum(1 for r in results if r["served"])
    refused = len(results) - served
    drift = len(regressed) + len(improved)
    head = f"STATE: served={served}/{len(results)} refused={refused}/{len(results)} baseline_drift={drift}"
    lines: list[str] = [head, "", f"## Thin-corpus health — {_bogota_now_str()}",
                         f"Server: `{server}`", ""]
    if not baseline_known:
        lines.append("> ⚠ No baseline file. Pass `--update-baseline` once the state is correct.")
        lines.append("")
    lines.append(f"| Topic | State | Mode | Cites | Latency | Reason |")
    lines.append(f"|---|---|---|---:|---:|---|")
    for r in results:
        mark = "✅" if r["served"] else "❌"
        topic = r["topic"]
        if topic in regressed:
            mark = "⚠ REGRESSED"
        elif topic in improved:
            mark = "✨ IMPROVED"
        reason = (r.get("fallback") or "").replace("pipeline_d_", "") if not r["served"] else ""
        if r.get("error"):
            reason = f"ERR: {r['error'][:60]}"
        lines.append(
            f"| `{topic}` | {mark} | `{r['mode']}` | {r['cites']} | {r['latency_ms']} ms | {reason} |"
        )
    lines.append("")
    if regressed:
        lines.append(f"### ⚠ Regressions ({len(regressed)})")
        for t in regressed:
            lines.append(f"- `{t}` was SERVED in baseline; now refused.")
        lines.append("")
    if improved:
        lines.append(f"### ✨ Improvements ({len(improved)})")
        for t in improved:
            lines.append(f"- `{t}` was REFUSED in baseline; now served. Update baseline if expected.")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--server",
        default=os.environ.get("LIA_HEARTBEAT_SERVER", "http://127.0.0.1:8787"),
        help="Lia chat server URL (default: %(default)s).",
    )
    parser.add_argument(
        "--baseline",
        default="scripts/monitoring/thin_corpus_baseline.json",
        help="Baseline state file (default: %(default)s).",
    )
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Write current state as the new baseline. Use after a known-good change.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=90.0,
        help="Per-probe HTTP timeout in seconds (default: %(default)s).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress the markdown body; emit only the STATE: line.",
    )
    args = parser.parse_args()

    baseline_path = Path(args.baseline)
    baseline = _load_baseline(baseline_path)

    results: list[dict[str, Any]] = []
    for topic, msg in PROBES:
        results.append(_probe_one(args.server, topic, msg, timeout=args.timeout))

    regressed, improved = _diff_vs_baseline(results, baseline)
    block = _render_block(results, regressed, improved, bool(baseline), args.server)

    if args.update_baseline:
        _save_baseline(baseline_path, results)
        block += f"\n\n_Baseline updated → {baseline_path}_\n"

    _emit_event({
        "server": args.server,
        "served": sum(1 for r in results if r["served"]),
        "total": len(results),
        "regressed": regressed,
        "improved": improved,
        "results": [
            {k: v for k, v in r.items() if k != "error"}
            for r in results
        ],
    })

    if args.quiet:
        # Only first STATE line.
        print(block.split("\n", 1)[0])
    else:
        print(block)

    if regressed:
        return 1  # Regression: caller should alert.
    if improved and not args.update_baseline:
        return 2  # Improvement: caller should update baseline.
    return 0


if __name__ == "__main__":
    sys.exit(main())
