"""fixplan_v3 §0.11.5 — one-shot upgrade of the 7 v2 fixtures to v3 shape.

Reads each `evals/activity_1_5/*_veredicto.json` (v2 shape per Activity
1.5/1.6/1.7) and produces a v3 `Vigencia` JSON suitable for
`scripts/ingest_vigencia_veredictos.py`.

Mapping (v2 → v3):
  * `veredicto.state` → `state` (already aligned for V/VM/DE/DT/SP/IE/EC).
  * `veredicto.derogado_por`     → ChangeSource(type=derogacion_expresa, ...)
  * `veredicto.modificado_por`   → ChangeSource(type=reforma, ...)
  * `veredicto.suspension`       → ChangeSource(type=auto_ce_suspension, ...)
  * `veredicto.inexequibilidad`  → ChangeSource(type=sentencia_cc, ...)
  * `veredicto.condicionamiento` → ChangeSource(type=sentencia_cc) +
                                   InterpretiveConstraint
  * `applies_to_periodo` → applies_to_kind/applies_to_payload
  * `norm_id` is canonicalized via `canon.canonicalize` (the v2 fixtures
    used the natural-language form "Art. 158-1 ET" instead of "et.art.158-1").

Usage:
  PYTHONPATH=src:. uv run python scripts/upgrade_v2_veredictos_to_v3.py \\
      --input-dir evals/activity_1_5 \\
      --output-dir evals/vigencia_extraction_v1 \\
      --run-id v2-to-v3-upgrade-2026-04-27
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Mapping

LOGGER = logging.getLogger("upgrade_v2_veredictos")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--input-dir", default="evals/activity_1_5")
    p.add_argument("--output-dir", default="evals/vigencia_extraction_v1")
    p.add_argument("--run-id", default="v2-to-v3-upgrade-2026-04-27")
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    from lia_graph.canon import canonicalize, is_valid_norm_id

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    upgraded = skipped = errors = 0
    for path in sorted(input_dir.glob("*_veredicto.json")):
        try:
            blob = json.loads(path.read_text(encoding="utf-8"))
        except Exception as err:
            LOGGER.warning("Cannot read %s: %s", path, err)
            errors += 1
            continue

        try:
            v3 = _upgrade(blob, run_id=args.run_id)
        except Exception as err:
            LOGGER.warning("Cannot upgrade %s: %s", path, err)
            errors += 1
            continue

        out_path = output_dir / f"{v3['norm_id'].replace('/', '_')}.json"
        out_path.write_text(json.dumps(v3, indent=2, ensure_ascii=False), encoding="utf-8")
        upgraded += 1
        LOGGER.info("✓ %s → %s (state=%s)", path.name, out_path.name, v3["result"]["veredicto"]["state"])

    LOGGER.info("Upgrade done: upgraded=%d skipped=%d errors=%d", upgraded, skipped, errors)
    return 0 if errors == 0 else 1


# ---------------------------------------------------------------------------
# v2 → v3 mapper
# ---------------------------------------------------------------------------


_V2_STATE_TO_V3 = {
    "V": "V", "VM": "VM", "DE": "DE", "DT": "DT", "SP": "SP", "IE": "IE", "EC": "EC",
    "vigente": "V",
    "vigente_modificada": "VM",
    "derogada": "DE",
    "derogada_expresa": "DE",
    "derogada_tacita": "DT",
    "suspendida": "SP",
    "inexequible": "IE",
    "exequibilidad_condicionada": "EC",
}


def _upgrade(v2_blob: Mapping[str, Any], *, run_id: str) -> dict[str, Any]:
    from lia_graph.canon import canonicalize, is_valid_norm_id

    v2_norm_raw = str(v2_blob.get("norm_id") or "")
    parágrafo = v2_blob.get("parágrafo") or v2_blob.get("paragrafo")

    # Pre-clean fixture-specific quirks before handing to the canonicalizer.
    cleaned = _preclean_norm_label(v2_norm_raw)
    norm_id = canonicalize(cleaned)
    if norm_id is None and parágrafo:
        # Append parágrafo / numeral if the fixture stores it separately.
        joined = canonicalize(f"{cleaned} {parágrafo}")
        if joined is not None:
            norm_id = joined
    if norm_id is None:
        raise ValueError(f"Cannot canonicalize norm_id={v2_norm_raw!r}")

    # If the fixture stores a sub-unit hint AND it's an unambiguous single
    # sub-unit (not a comma-separated list), append it.
    if parágrafo:
        sub_hint = str(parágrafo)
        # Only attach if hint references exactly one sub-unit
        if "," not in sub_hint and " y " not in sub_hint.lower():
            norm_id = _maybe_append_sub_unit(norm_id, sub_hint)

    v2_veredicto = v2_blob.get("veredicto") or {}
    state = _V2_STATE_TO_V3.get(str(v2_veredicto.get("state") or ""))
    if state is None:
        raise ValueError(f"Unknown v2 state: {v2_veredicto.get('state')!r}")

    state_from = _parse_date_relaxed(v2_veredicto.get("vigente_desde"))
    # `vigente_hasta` in the v2 schema means "the prior V version was vigente
    # until this date" — for the current row's perspective (DE/IE/SP active
    # today), state_until should remain NULL. We only carry vigente_hasta as
    # state_until for V/VM rows that have a known end of applicability.
    state_until: date | None = None
    if state in ("V", "VM"):
        state_until = _parse_date_relaxed(v2_veredicto.get("vigente_hasta"))
    if state_from is None:
        # Default to fecha_efectos of the change_source if available.
        if v2_veredicto.get("derogado_por", {}).get("fecha_efectos"):
            state_from = _parse_date_relaxed(v2_veredicto["derogado_por"]["fecha_efectos"])
        elif v2_veredicto.get("modificado_por") and v2_veredicto["modificado_por"]:
            state_from = _parse_date_relaxed(v2_veredicto["modificado_por"][0].get("fecha"))
        elif v2_veredicto.get("inexequibilidad", {}).get("fecha_efectos"):
            state_from = _parse_date_relaxed(v2_veredicto["inexequibilidad"]["fecha_efectos"])
        elif v2_veredicto.get("suspension", {}).get("fecha"):
            state_from = _parse_date_relaxed(v2_veredicto["suspension"]["fecha"])
    if state_from is None:
        # Last resort: 1 Jan of the periodo year, or the publish date of the source.
        periodo = v2_blob.get("periodo_consultado") or {}
        year = periodo.get("year") or 2017
        state_from = date(int(year), 1, 1)

    change_source = _build_change_source(state, v2_veredicto)
    interpretive = _build_interpretive(state, v2_veredicto)

    applies_to_kind, applies_to_payload = _build_applies_to(v2_blob, state, state_from)

    citation_lists = {
        "fuentes_primarias_consultadas": [
            _coerce_citation(c)
            for c in (v2_veredicto.get("fuentes_primarias_consultadas") or [])
        ],
    }

    derogado_por = _coerce_citation(v2_veredicto.get("derogado_por")) if v2_veredicto.get("derogado_por") else None
    suspension = _coerce_citation(v2_veredicto.get("suspension")) if v2_veredicto.get("suspension") else None
    inexequibilidad = _coerce_citation(v2_veredicto.get("inexequibilidad")) if v2_veredicto.get("inexequibilidad") else None
    regimen_transicion = _coerce_citation(v2_veredicto.get("regimen_transicion")) if v2_veredicto.get("regimen_transicion") else None
    modificado_por = [
        _coerce_citation(c)
        for c in (v2_veredicto.get("modificado_por") or [])
    ]

    audit = {
        "skill_version": "vigencia-checker@1.0",
        "model": None,
        "tool_iterations": (v2_veredicto.get("extraction_audit") or {}).get("tool_iterations"),
        "wall_ms": None,
        "cost_usd_estimate": None,
        "run_id": run_id,
        "method": "v2_to_v3_upgrade",
    }

    veredicto_v3 = {
        "state": state,
        "state_from": state_from.isoformat(),
        "state_until": state_until.isoformat() if state_until else None,
        "applies_to_kind": applies_to_kind,
        "applies_to_payload": applies_to_payload,
        "change_source": change_source,
        "interpretive_constraint": interpretive,
        "derogado_por": derogado_por,
        "modificado_por": modificado_por,
        "suspension": suspension,
        "inexequibilidad": inexequibilidad,
        "regimen_transicion": regimen_transicion,
        "revives_text_version": None,
        "rige_desde": None,
        "fuentes_primarias_consultadas": citation_lists["fuentes_primarias_consultadas"],
        "extraction_audit": audit,
    }

    return {
        "norm_id": norm_id,
        "norm_type": _norm_type_from_id(norm_id),
        "parent_norm_id": _parent_from_id(norm_id),
        "is_sub_unit": ".par." in norm_id or ".num." in norm_id or ".inciso." in norm_id or ".lit." in norm_id,
        "sub_unit_kind": _sub_unit_kind(norm_id),
        "extraction_run_id": run_id,
        "extracted_at_utc": datetime.now(timezone.utc).isoformat(),
        "result": {
            "veredicto": veredicto_v3,
            "refusal_reason": None,
            "missing_sources": [],
            "canonicalizer_refusals": [],
        },
    }


def _preclean_norm_label(label: str) -> str:
    """Drop fixture-specific quirks the canonicalizer doesn't model."""

    import re as _re
    text = label or ""
    # Drop parenthetical scope notes: "Arts. ... (en su aplicación a ...)"
    text = _re.sub(r"\s*\([^)]*\)\s*", " ", text)
    # Plural article references — keep the lowest article number; vigencia
    # state is the same for the whole bundle in our v2 fixtures.
    m = _re.match(r"\s*art(?:s|\.|ículos)?\.?\s*(\d+(?:-\d+)?)(?:\s*[,y]\s*\d+(?:-\d+)?)*\s+(et|estatuto.*)", text, _re.IGNORECASE)
    if m:
        text = f"Art. {m.group(1)} {m.group(2)}"
    # "Decreto Legislativo NNN de YYYY" → "Decreto NNN de YYYY"
    text = _re.sub(r"\bdecreto\s+legislativo\b", "Decreto", text, flags=_re.IGNORECASE)
    return text.strip()


def _maybe_append_sub_unit(norm_id: str, sub_unit_hint: str) -> str:
    """If `sub_unit_hint` reads like 'numeral 5' / 'parágrafo 2' and `norm_id`
    is an article-level id without a sub-unit, append the sub-unit."""

    import re as _re
    if any(seg in norm_id for seg in (".par.", ".inciso.", ".num.", ".lit.")):
        return norm_id
    text = sub_unit_hint.lower().strip()
    m = _re.match(r"(par(?:agrafo|ágrafo)?|inciso|num(?:eral)?|lit(?:eral)?)\s*(\w+)", text)
    if not m:
        return norm_id
    raw_kind = m.group(1)
    value = m.group(2)
    if raw_kind.startswith("par"):
        return f"{norm_id}.par.{value}"
    if raw_kind.startswith("inciso"):
        return f"{norm_id}.inciso.{value}"
    if raw_kind.startswith("num"):
        return f"{norm_id}.num.{value}"
    if raw_kind.startswith("lit"):
        return f"{norm_id}.lit.{value}"
    return norm_id


def _norm_type_from_id(norm_id: str) -> str:
    from lia_graph.canon import norm_type as canon_norm_type
    return canon_norm_type(norm_id)


def _parent_from_id(norm_id: str) -> str | None:
    from lia_graph.canon import parent_norm_id as canon_parent
    return canon_parent(norm_id)


def _sub_unit_kind(norm_id: str) -> str | None:
    from lia_graph.canon import sub_unit_kind as canon_sub_unit
    return canon_sub_unit(norm_id)


def _build_change_source(state: str, v2_veredicto: Mapping[str, Any]) -> dict[str, Any] | None:
    from lia_graph.canon import canonicalize
    if state == "V":
        return None
    if state == "DE":
        d = v2_veredicto.get("derogado_por") or {}
        source_id = canonicalize(_compose_norm_label(d)) or "ley.unknown.0000"
        return {
            "type": "derogacion_expresa",
            "source_norm_id": source_id,
            "effect_type": "pro_futuro",
            "effect_payload": {
                "fecha_efectos": d.get("fecha_efectos") or d.get("fecha") or "1900-01-01",
            },
        }
    if state == "VM":
        m_list = v2_veredicto.get("modificado_por") or []
        if not m_list:
            raise ValueError("VM state requires modificado_por")
        m = m_list[0]
        source_id = canonicalize(_compose_norm_label(m)) or "ley.unknown.0000"
        return {
            "type": "reforma",
            "source_norm_id": source_id,
            "effect_type": "pro_futuro",
            "effect_payload": {"fecha": m.get("fecha")},
        }
    if state == "DT":
        # Tácita: source is the displacing norm (often a Sentencia de Unificación
        # or a posterior Ley). Activity 1.7's case identifies "Ley 962/2005 Art. 43"
        # as the displacing norm — that is what we anchor on.
        d = v2_veredicto.get("derogado_por") or {}
        if not d:
            d = (v2_veredicto.get("modificado_por") or [{}])[0]
        source_id = canonicalize(_compose_norm_label(d))
        # Fall back to a known sentencia / ley placeholder per fixture
        if source_id is None:
            # The fixture's `derogado_por.norm_id` may be a sentencia label.
            # Best-effort canonicalize the sentencia hint; otherwise mint a
            # synthetic id that satisfies the grammar so the catalog walks.
            source_id = canonicalize(str(d.get("norm_id") or ""))
        if source_id is None:
            # Synthetic sentencia ce id — this is a fixture-side fallback only
            # used for the v2-to-v3 upgrade smoke. Real production extractions
            # will canonicalize properly via the skill.
            source_id = "sent.ce.0.1900.01.01"
        return {
            "type": "derogacion_tacita",
            "source_norm_id": source_id,
            "effect_type": "pro_futuro",
            "effect_payload": {
                "contested": True,
                "official_pronouncement_norm_id": d.get("primary_source_url"),
            },
        }
    if state == "SP":
        s = v2_veredicto.get("suspension") or {}
        # SP source is an auto CE — fixtures have norm_id like "Auto 28920 del 16-dic-2024 (CE Sección Cuarta)"
        candidate = canonicalize(_compose_norm_label(s)) or canonicalize(str(s.get("norm_id") or ""))
        if not candidate:
            # Fallback to a placeholder
            candidate = "auto.ce.99999.1900.01.01"
        return {
            "type": "auto_ce_suspension",
            "source_norm_id": candidate,
            "effect_type": "pro_futuro",
            "effect_payload": {
                "autoridad": s.get("autoridad") or "CE Sección Cuarta",
                "alcance": s.get("alcance") or "",
            },
        }
    if state == "IE":
        i = v2_veredicto.get("inexequibilidad") or {}
        source_id = canonicalize(_compose_norm_label(i)) or "sent.cc.C-000.1900"
        return {
            "type": "sentencia_cc",
            "source_norm_id": source_id,
            "effect_type": "pro_futuro",
            "effect_payload": {
                "fecha_sentencia": i.get("fecha_sentencia") or i.get("fecha") or "1900-01-01",
            },
        }
    if state == "EC":
        c = v2_veredicto.get("condicionamiento") or {}
        source_id = canonicalize(_compose_norm_label(c)) or "sent.cc.C-000.1900"
        return {
            "type": "sentencia_cc",
            "source_norm_id": source_id,
            "effect_type": "pro_futuro",
            "effect_payload": {
                "fecha_sentencia": c.get("fecha_sentencia") or c.get("fecha") or "1900-01-01",
                "condicionamiento_literal": c.get("texto_literal") or c.get("alcance") or "",
            },
        }
    return None


def _compose_norm_label(d: Mapping[str, Any]) -> str:
    """Build a free-text label the canonicalizer can resolve."""

    norm_id = str(d.get("norm_id") or "")
    article = d.get("article")
    if article and "Art" not in norm_id:
        return f"{norm_id}, {article}"
    return norm_id


def _build_interpretive(state: str, v2_veredicto: Mapping[str, Any]) -> dict[str, Any] | None:
    if state not in ("EC", "VC"):
        return None
    c = v2_veredicto.get("condicionamiento") or {}
    from lia_graph.canon import canonicalize
    sentencia = canonicalize(_compose_norm_label(c)) or "sent.cc.C-000.1900"
    return {
        "sentencia_norm_id": sentencia,
        "fecha_sentencia": c.get("fecha_sentencia") or c.get("fecha") or "1900-01-01",
        "texto_literal": c.get("texto_literal") or c.get("alcance") or "(SME-fill literal Court text)",
        "fuente_verificada_directo": bool(c.get("fuente_verificada_directo", False)),
    }


def _build_applies_to(v2_blob: Mapping[str, Any], state: str, state_from: date) -> tuple[str, dict[str, Any]]:
    periodo = v2_blob.get("periodo_consultado") or {}
    impuesto = periodo.get("impuesto")
    year = periodo.get("year")
    if impuesto and year:
        return "per_period", {
            "year_start": int(year),
            "year_end": None,
            "impuesto": impuesto,
            "period_start": date(int(year), 1, 1).isoformat(),
            "period_end": None,
            "art_338_cp_shift": False,
        }
    return "always", {}


def _coerce_citation(c: Any) -> dict[str, Any] | None:
    if not c:
        return None
    if not isinstance(c, dict):
        return None
    from lia_graph.canon import canonicalize, is_valid_norm_id
    raw_id = str(c.get("norm_id") or "")
    canonical = canonicalize(_compose_norm_label(c))
    if not canonical and is_valid_norm_id(raw_id):
        canonical = raw_id
    return {
        "norm_id": canonical or raw_id or "unknown",
        "norm_type": c.get("norm_type"),
        "article": c.get("article"),
        "fecha": c.get("fecha"),
        "primary_source_url": c.get("primary_source_url"),
    }


def _parse_date_relaxed(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    s = str(value).strip()
    if not s:
        return None
    # Accept YYYY-MM-DD, YYYY-MM, YYYY/MM/DD, etc.
    s = s.replace("/", "-")
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


if __name__ == "__main__":
    sys.exit(main())
