#!/usr/bin/env python3
"""ingestionfix_v3 Phase 2.5 Task B preparation — canonical sector merge map.

Deterministic post-processor (no LLM calls). Reads all three prior
proposals (first pass + strict retry + orphan rescue) and collapses
the ~187 raw `sector_*` labels into ~30 canonical buckets.

## Merge strategy

Three rules, applied in order:

1. **Prefix/primary-keyword grouping.** Each label is split on `_` after
   the `sector_` prefix; the first keyword is the primary group key
   (e.g. `sector_cultura_cine` → primary `cultura`; `sector_vivienda_urbana`
   → primary `vivienda`). The canonical name is the shortest label in
   the group, preferring the bare `sector_<primary>` form if present.
2. **Explicit synonym merges** (hand-curated below) catch cases the
   prefix rule misses (e.g. `sector_minero_energetico` + `sector_energia`
   → one `sector_energia_mineria`; `sector_cine_audiovisual` folds into
   `sector_cultura`).
3. **Exclude disguised-catch-all** labels (`sector_otros*`, `sector_misc*`,
   `sector_varios*`) — these are not real sectors and the operator
   should keep them as orphan rather than canonicalize.

## Output

`artifacts/sector_classification/sector_merge_map.json`:

```json
{
  "generated_at_utc": "...",
  "sources": ["artifacts/.../proposal.json", ...],
  "canonical_count": 30,
  "raw_count": 187,
  "unmerged_labels": [ ... ],  // flagged for operator attention
  "groups": [
    {
      "canonical": "sector_salud",
      "doc_count": 22,
      "absorbs": ["sector_salud", "sector_salud_seguridad_social"],
      "example_doc_ids": ["...", "..."]
    },
    ...
  ]
}
```

Operator reviews this, may tweak the synonym table below, re-runs, and
uses the final output as input to `apply_sector_reclassification.py`
(Phase 2.5 Task E).

Usage:
    PYTHONPATH=src:. uv run python \\
      scripts/monitoring/monitor_sector_reclassification/build_merge_map.py
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


# ── Hand-curated synonym merges ──────────────────────────────────────
# These catch semantically equivalent labels the prefix rule misses.
# The LHS is the canonical; RHS is the list of raw labels to absorb.

SYNONYM_MERGES: dict[str, list[str]] = {
    "sector_energia_mineria": [
        "sector_energia",
        "sector_energia_electrica",
        "sector_energias",
        "sector_energias_renovables",
        "sector_mineria",
        "sector_minero",
        "sector_minero_energetico",
    ],
    "sector_cultura": [
        "sector_cine_audiovisual",
        "sector_bibliotecologia",
    ],
    "sector_administracion_publica": [
        "sector_gobierno_territorial",
        "sector_gobierno_local",
        "sector_transparencia_gobernanza",
        "sector_transparencia",
        "sector_transparencia_informacion",
        "sector_transparencia_informacion_publica",
        "sector_anticorrupcion_gobernanza",
        "sector_administracion",
        "sector_administracion_publica_anticorrupcion",
        "sector_administracion_publica_municipal",
        "sector_administracion_territorial",
        "sector_archivos_publicos",
        "sector_archivistica_gestion_documental",
        "sector_gestion_documental_archivos",
        "sector_gestion_riesgos_desastres",
        "sector_contabilidad_publica",
        "sector_responsabilidad_social_empresarial",
        "sector_sistema_nacional_archivos",
        "sector_politica_publica",
        "sector_politica",
        "sector_politica_social",
        "sector_regimen",
        "sector_regimen_municipal",
    ],
    "sector_justicia": [
        "sector_seguridad_justicia",
        "sector_seguridad_emergencias",
        "sector_seguridad_nacional",
        "sector_seguridad_democratica",
        "sector_seguridad",
        "sector_seguridad_vial",
        "sector_seguridad_internacional_derechos_humanos",
        "sector_derecho_penal",
        "sector_derecho_constitucional",
        "sector_derecho",
        "sector_derecho_administrativo",
        "sector_derecho_internacional",
        "sector_derechos_humanos",
        "sector_derechos_fundamentales",
    ],
    "sector_agropecuario": [
        "sector_agropecuario_rural",
        "sector_agropecuario_pesquero",
        "sector_agropecuario_tierras",
        "sector_agrario_rural",
        "sector_propiedad_tierra",
        "sector_rural",
        "sector_rural_agrario",
        "sector_rural_desarrollo",
        "sector_desarrollo",
        "sector_desarrollo_agricola",
        "sector_desarrollo_rural",
        "sector_recursos",
        "sector_recursos_hidricos",
        "sector_recursos_naturales",
        "sector_cafe",
        "sector_cafetero",
    ],
    "sector_vivienda": [
        "sector_vivienda_urbana",
        "sector_vivienda_urbano",
        "sector_propiedad_inmueble",
        "sector_propiedad_horizontal",
        "sector_ordenamiento_territorial",
        "sector_desarrollo_urbano",
    ],
    "sector_financiero": [
        "sector_financiero_seguros",
        "sector_financiero_credito",
        "sector_financiero_consumidor",
        "sector_financiero_libranzas",
        "sector_economia_solidaria",
        "sector_cooperativo",
        "sector_proteccion_consumidor",
        "sector_banca",
        "sector_banca_central",
        "sector_cajas",
        "sector_cajas_compensacion",
        "sector_cajas_compensacion_familiar",
        "sector_mercado",
        "sector_mercado_valores",
        "sector_reactivacion",
        "sector_reactivacion_economica",
        "sector_reactivacion_regional",
        "sector_sistema_financiero",
        "sector_sistema",
    ],
    "sector_deporte": [
        "sector_deporte_recreacion",
    ],
    "sector_inclusion_social": [
        "sector_inclusion_discapacidad",
        "sector_genero_violencia",
        "sector_genero_equidad",
        "sector_etnias_afrocolombianas",
        "sector_etnico",
        "sector_etnico_racial",
        "sector_derechos",
        "sector_derechos_etnicos",
        "sector_victimas",
        "sector_victimas_conflicto",
        "sector_juventud",
        "sector_memoria",
        "sector_memoria_historica",
        "sector_memoria_victimas",
        "sector_asistencia",
        "sector_asistencia_social",
        "sector_migracion",
    ],
    "sector_salud": [
        "sector_salud_seguridad_social",
        "sector_seguridad_social",
        "sector_proteccion_animal",
    ],
    "sector_juegos_azar": [
        "sector_juegos_suerte_azar",
    ],
    "sector_desarrollo_regional": [
        "sector_fronteras_desarrollo_regional",
        "sector_planificacion_nacional",
        "sector_administracion_territorial",
    ],
    "sector_profesiones_liberales": [
        "sector_regulacion_profesional",
        "sector_profesion_economista",
        "sector_profesion_diseno_industrial",
        "sector_profesion_periodismo",
        "sector_profesion_psicologia",
        "sector_psicologia",
        "sector_profesiones",
        "sector_profesiones_salud",
        "sector_belleza",
        "sector_belleza_estetica",
        "sector_zonas_especiales",  # rare edge case; operator can split out
    ],
    "sector_medio_ambiente": [
        "sector_medio",
        "sector_medio_ambiente_fauna",
    ],
    "sector_comercio_internacional": [
        "sector_aduanas",
        "sector_aduanas_comercio_exterior",
        "sector_comercio",
    ],
}

# Disguised catch-all — flagged, not merged (operator treats as orphan).
CATCH_ALL_PREFIXES = ("sector_otros", "sector_misc", "sector_varios")


# ── Data loaders ─────────────────────────────────────────────────────


def load_proposals(paths: Iterable[Path]) -> list[dict[str, Any]]:
    """Load all prior proposals; return the flattened list of result records."""
    out: list[dict[str, Any]] = []
    for p in paths:
        if not p.exists():
            print(f"[merge_map] WARNING: source missing: {p}", file=sys.stderr)
            continue
        data = json.loads(p.read_text(encoding="utf-8"))
        for r in data.get("results", []):
            r = dict(r)
            r["_source"] = str(p.name)
            out.append(r)
    return out


def collect_sector_labels(
    results: list[dict[str, Any]],
) -> tuple[dict[str, int], dict[str, list[str]]]:
    """Return (label → doc count, label → sample doc_ids)."""
    counts: dict[str, int] = defaultdict(int)
    samples: dict[str, list[str]] = defaultdict(list)
    for r in results:
        if r.get("kind") != "new_sector":
            continue
        label = str(r.get("proposed_topic") or "").strip()
        if not label.startswith("sector_"):
            continue
        counts[label] += 1
        if len(samples[label]) < 3:
            samples[label].append(str(r.get("doc_id", "")))
    return dict(counts), dict(samples)


# ── Merge strategy ───────────────────────────────────────────────────


def build_reverse_synonym_map() -> dict[str, str]:
    """Flatten SYNONYM_MERGES into label → canonical."""
    m: dict[str, str] = {}
    for canonical, raws in SYNONYM_MERGES.items():
        for r in raws:
            m[r] = canonical
    return m


def primary_keyword(label: str) -> str:
    rest = label[len("sector_") :] if label.startswith("sector_") else label
    return rest.split("_", 1)[0] if rest else ""


def is_catch_all(label: str) -> bool:
    return label.startswith(CATCH_ALL_PREFIXES)


def merge(
    counts: dict[str, int], samples: dict[str, list[str]]
) -> tuple[list[dict[str, Any]], list[str]]:
    """Collapse raw labels into canonical groups.

    Returns (groups, catch_all_labels).
    """
    synonyms = build_reverse_synonym_map()
    # Also treat every canonical as its own synonym (identity) so the
    # prefix rule doesn't fight the explicit map.
    for canonical in SYNONYM_MERGES:
        synonyms.setdefault(canonical, canonical)

    groups: dict[str, dict[str, Any]] = {}
    catch_all: list[str] = []

    for label, cnt in counts.items():
        if is_catch_all(label):
            catch_all.append(label)
            continue

        canonical = synonyms.get(label)
        if canonical is None:
            # Prefix-rule fallback: bare `sector_<primary>`.
            canonical = f"sector_{primary_keyword(label)}" if primary_keyword(label) else label

        grp = groups.setdefault(
            canonical,
            {
                "canonical": canonical,
                "doc_count": 0,
                "absorbs": [],
                "example_doc_ids": [],
            },
        )
        grp["doc_count"] += cnt
        grp["absorbs"].append({"label": label, "doc_count": cnt})
        for did in samples.get(label, []):
            if len(grp["example_doc_ids"]) < 5:
                grp["example_doc_ids"].append(did)

    # Sort by doc_count descending; within each group, sort absorbs by count.
    out = sorted(groups.values(), key=lambda g: -g["doc_count"])
    for g in out:
        g["absorbs"] = sorted(g["absorbs"], key=lambda x: -x["doc_count"])

    return out, sorted(set(catch_all))


# ── CLI ──────────────────────────────────────────────────────────────


def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="build_merge_map",
        description=(
            "Deterministically collapse raw `sector_*` labels from the prior "
            "Gemini classification passes into canonical buckets. No LLM calls."
        ),
    )
    p.add_argument(
        "--from-proposals",
        nargs="+",
        default=[
            "artifacts/sector_classification/sector_reclassification_proposal.json",
            "artifacts/sector_classification_strict/sector_reclassification_proposal.json",
            "artifacts/sector_classification_orphans/orphan_rescue_proposal.json",
        ],
        help="Proposals to read (default: all three from Phase 2.5 Tasks A + A.2).",
    )
    p.add_argument(
        "--output",
        default="artifacts/sector_classification/sector_merge_map.json",
        help="Output path for the merge map.",
    )
    return p


def main(argv: Iterable[str] | None = None) -> int:
    args = build_argparser().parse_args(list(argv) if argv is not None else None)

    paths = [Path(p) for p in args.from_proposals]
    results = load_proposals(paths)
    counts, samples = collect_sector_labels(results)
    groups, catch_all = merge(counts, samples)

    payload = {
        "generated_at_utc": _dt.datetime.now(_dt.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "sources": [str(p) for p in paths],
        "raw_label_count": len(counts),
        "canonical_group_count": len(groups),
        "catch_all_excluded": catch_all,
        "total_docs_covered": sum(g["doc_count"] for g in groups),
        "groups": groups,
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"[merge_map] wrote {out_path}")
    print(
        f"[merge_map] {len(counts)} raw labels → {len(groups)} canonical groups "
        f"({sum(g['doc_count'] for g in groups)} docs covered)"
    )
    print(f"[merge_map] catch-all excluded: {len(catch_all)} labels")
    print()
    print("Top 15 canonical groups by doc count:")
    for g in groups[:15]:
        absorbed = ", ".join(a["label"] for a in g["absorbs"][:5])
        more = f" +{len(g['absorbs']) - 5} more" if len(g["absorbs"]) > 5 else ""
        print(f"  {g['doc_count']:4d}  {g['canonical']:40s}  ← {absorbed}{more}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
