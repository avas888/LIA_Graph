#!/usr/bin/env python3
"""SME spot-review applier — atomically applies the 7 q-decisions from
docs/aa_next/taxonomy_v2_sme_spot_review.md.

Usage:
    python artifacts/sme_pending/apply_sme_decisions.py \
        --decisions q10:A,q13:A,q14:B,q15:A,q16:A,q26:A,q28:A [--dry-run]

After a successful apply, run `make eval-taxonomy-v2` to re-measure.
If chat-resolver accuracy >= 27/30, gate 8 of next_v3 §9 clears.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLD = REPO_ROOT / "evals/gold_taxonomy_v2_validation.jsonl"
TAXONOMY = REPO_ROOT / "config/topic_taxonomy.json"
ROUTER = REPO_ROOT / "src/lia_graph/topic_router.py"
MAKEFILE = REPO_ROOT / "Makefile"

VALID_LETTERS: dict[str, tuple[str, ...]] = {
    "q10": ("A", "B"),
    "q13": ("A", "B"),
    "q14": ("A", "B"),
    "q15": ("A", "B", "C"),
    "q16": ("A", "B"),
    "q26": ("A", "B"),
    "q28": ("A", "B"),
}

# Markers placed in the chat-resolver prompt so the applier can find + extend
# them idempotently across multiple runs.
NO_COLLAPSE_MARKER = "# SME_NO_COLLAPSE_EXCEPTIONS"
META_RULE_MARKER = "# SME_META_RULE_OP_VS_DEF"

# ─── parsing ─────────────────────────────────────────────────────────────────

def parse_decisions(spec: str) -> dict[str, str]:
    decisions: dict[str, str] = {}
    for tok in spec.split(","):
        tok = tok.strip()
        if not tok or ":" not in tok:
            raise SystemExit(f"Bad token: {tok!r}")
        qid, letter = tok.split(":", 1)
        qid, letter = qid.strip().lower(), letter.strip().upper()
        if qid not in VALID_LETTERS:
            raise SystemExit(f"Unknown qid: {qid}")
        if letter not in VALID_LETTERS[qid]:
            raise SystemExit(f"Invalid letter for {qid}: {letter} (allowed {VALID_LETTERS[qid]})")
        decisions[qid] = letter
    missing = set(VALID_LETTERS) - set(decisions)
    if missing:
        raise SystemExit(f"Missing decisions for: {sorted(missing)}")
    return decisions

# ─── gold-file widening ──────────────────────────────────────────────────────

def gold_widen(qid_int: int, accept_topic: str) -> Callable[[dict[str, Any]], None]:
    """Return a transform that widens row's ambiguous_acceptable to include accept_topic."""
    def _apply(state: dict[str, Any]) -> None:
        rows = state["gold_rows"]
        for row in rows:
            if int(row.get("qid", -1)) != qid_int:
                continue
            existing = row.get("ambiguous_acceptable") or [row["expected_topic"]]
            existing = [str(x).strip() for x in existing]
            if accept_topic not in existing:
                existing.append(accept_topic)
            row["ambiguous_acceptable"] = existing
            return
        raise RuntimeError(f"qid {qid_int} not found in gold")
    return _apply

# ─── prompt edit (q10/q16:A) ─────────────────────────────────────────────────

def prompt_add_meta_rule_op_vs_def() -> Callable[[dict[str, Any]], None]:
    """Insert the SME meta-rule 'el topic es el que opera, no el que define' at
    the top of _build_classifier_prompt, before the catalog block. Idempotent."""
    def _apply(state: dict[str, Any]) -> None:
        text = state["router_text"]
        if META_RULE_MARKER in text:
            return  # already present
        anchor = '"═══ CATÁLOGO DE TEMAS (elige uno) — formato `N. key — label — definición`:\\n\\n"'
        if anchor not in text:
            raise RuntimeError("catalog anchor not found in topic_router._build_classifier_prompt")
        meta_block = (
            f'        # {META_RULE_MARKER} (managed by artifacts/sme_pending/apply_sme_decisions.py)\n'
            '        "═══ HEURÍSTICA META — antes de cualquier otra regla:\\n\\n"\n'
            '        "El TEMA es el que OPERA, no el que DEFINE. Cuando una pregunta toca\\n"\n'
            '        "dos áreas, el tema es el área donde se EJECUTA la respuesta operativa,\\n"\n'
            '        "no el área donde se definen los conceptos involucrados. Ejemplos:\\n"\n'
            '        "  · \'Patrimonio alto pero pérdida → renta presuntiva\' → opera en presuntiva (no patrimonio).\\n"\n'
            '        "  · \'Descuento del IVA en bienes de capital\' → opera en descuentos de renta (no iva).\\n"\n'
            '        "  · \'Tarifa en zona franca\' → opera en tarifas (no zonas_francas).\\n"\n'
            '        "  · \'Emplazamiento sobre IVA\' → opera en procedimiento (no iva).\\n\\n"\n'
            '        '
        )
        state["router_text"] = text.replace(anchor, meta_block + anchor, 1)
    return _apply


def prompt_add_no_collapse(topic_keys: list[str]) -> Callable[[dict[str, Any]], None]:
    """Add a 'no collapse to parent' exception clause to _build_classifier_prompt."""
    def _apply(state: dict[str, Any]) -> None:
        text = state["router_text"]
        target_str = ('"REGLA POR DEFECTO — si la consulta abarca varios subtemas del mismo padre\\n"\n'
                      '        "top-level, devuelve el PADRE. No fuerces un subtema cuando el contenido es\\n"\n'
                      '        "transversal.\\n\\n"')
        if target_str not in text:
            raise RuntimeError("default-to-parent block not found in topic_router._build_classifier_prompt")
        sorted_keys = sorted(set(topic_keys))
        list_str = ", ".join(f"`{k}`" for k in sorted_keys)
        replacement = (
            '"REGLA POR DEFECTO — si la consulta abarca varios subtemas del mismo padre\\n"\n'
            '        "top-level, devuelve el PADRE. No fuerces un subtema cuando el contenido es\\n"\n'
            '        "transversal.\\n\\n"\n'
            f'        # {NO_COLLAPSE_MARKER} (managed by artifacts/sme_pending/apply_sme_decisions.py)\n'
            '        "EXCEPCIONES — los siguientes subtemas son consultados POR NOMBRE por contadores;\\n"\n'
            '        "NO los colapses al padre cuando la consulta los menciona explícita o\\n"\n'
            f'        "implícitamente: {list_str}.\\n\\n"'
        )
        state["router_text"] = text.replace(target_str, replacement, 1)
    return _apply

# ─── taxonomy edits ──────────────────────────────────────────────────────────

def taxonomy_deprecate_v1_retencion() -> Callable[[dict[str, Any]], None]:
    """q15:A — mark retencion_en_la_fuente as deprecated, merged_into v2 key."""
    def _apply(state: dict[str, Any]) -> None:
        tax = state["taxonomy"]
        for topic in tax.get("topics", []):
            if topic.get("key") == "retencion_en_la_fuente":
                topic["status"] = "deprecated"
                topic.setdefault("merged_into", []).append("retencion_fuente_general") \
                    if "retencion_fuente_general" not in topic.get("merged_into", []) else None
                # Actually do the append cleanly:
                merged = topic.get("merged_into") or []
                if "retencion_fuente_general" not in merged:
                    merged.append("retencion_fuente_general")
                topic["merged_into"] = merged
                state["q15_corpus_migration_todo"] = True
                return
        raise RuntimeError("retencion_en_la_fuente not found in taxonomy")
    return _apply

def taxonomy_strengthen_iva_proc_mutex() -> Callable[[dict[str, Any]], None]:
    """q26:A — add explicit override clause to mutex rule 1 (iva_vs_procedimiento_tributario)."""
    def _apply(state: dict[str, Any]) -> None:
        tax = state["taxonomy"]
        rules = tax.get("mutex_rules", [])
        for rule in rules:
            if rule.get("id") == 1:
                addition = ("OVERRIDE EXPLÍCITO — Si la consulta menciona cualquiera de "
                            "{emplazamiento, requerimiento especial, liquidación oficial, sanción, "
                            "corregir declaración}, el tema es SIEMPRE procedimiento_tributario, "
                            "sin importar el impuesto sustantivo (renta/IVA/ICA) que se esté corrigiendo.")
                existing = rule.get("override_explicit", "")
                if addition not in existing:
                    rule["override_explicit"] = (existing + " " + addition).strip() if existing else addition
                return
        raise RuntimeError("mutex rule id=1 not found")
    return _apply

def taxonomy_add_carve_out_mutex(rule_name: str, key: str, text: str) -> Callable[[dict[str, Any]], None]:
    """q13:B / q14:A / q28:B — append a carve-out clause to a mutex rule (or create one)."""
    def _apply(state: dict[str, Any]) -> None:
        tax = state["taxonomy"]
        rules = tax.setdefault("mutex_rules", [])
        for rule in rules:
            if rule.get("name") == rule_name:
                if text not in (rule.get(key) or ""):
                    rule[key] = (rule.get(key, "") + " " + text).strip()
                return
        # New rule — id is max+1
        next_id = max((r.get("id", 0) for r in rules), default=0) + 1
        rules.append({"id": next_id, "name": rule_name, key: text})
    return _apply

def taxonomy_extend_keyword_anchors(topic_key: str, additions: list[str]) -> Callable[[dict[str, Any]], None]:
    """q10:A bonus — extend keyword_anchors of a topic with new phrases."""
    def _apply(state: dict[str, Any]) -> None:
        tax = state["taxonomy"]
        for topic in tax.get("topics", []):
            if topic.get("key") == topic_key:
                anchors = topic.get("keyword_anchors") or []
                anchors = list(anchors)
                for phrase in additions:
                    if phrase not in anchors:
                        anchors.append(phrase)
                topic["keyword_anchors"] = anchors
                return
        raise RuntimeError(f"{topic_key} not in taxonomy")
    return _apply


def taxonomy_q13_renta_presuntiva_vs_patrimonio() -> Callable[[dict[str, Any]], None]:
    """q13:B — Alejandro's mutex carve-out for renta presuntiva vs patrimonio."""
    rule_text = (
        "Renta presuntiva (art. 188 ET) y patrimonio (arts. 261 ET y patrimonio_*) son distintos. "
        "El patrimonio aparece como dato de entrada en preguntas de presuntiva — el contador "
        "ya hizo la valoración. Cuando la pregunta opera SOBRE la comparación renta_líquida vs "
        "renta_presuntiva, el topic es renta_presuntiva (o renta_liquida_gravable como cross-ref), "
        "NUNCA impuesto_patrimonio_*. "
        "Generalización: si la pregunta menciona dos cantidades en tensión comparativa, el topic "
        "es el que opera SOBRE la comparación, no el que las define."
    )
    return taxonomy_add_carve_out_mutex("renta_presuntiva_vs_patrimonio", "rule", rule_text)


def taxonomy_q14_descuento_iva_bienes_capital() -> Callable[[dict[str, Any]], None]:
    """q14:A — mutex carve-out + scope_out clarification on `iva` topic."""
    mutex_fn = taxonomy_add_carve_out_mutex(
        "descuento_iva_bienes_capital",
        "rule",
        "'Descuento del IVA en bienes de capital' (art. 258-1 ET) es 100% impuesto de renta — "
        "el IVA pagado se descuenta DEL impuesto de renta, no como IVA. Topic SIEMPRE "
        "descuentos_tributarios_renta, NUNCA iva. "
        "Generalización (cubre RST por aportes a pensión, IVA en obras por impuestos, etc.): "
        "cuando la consulta es sobre cómo el IVA pagado se RECUPERA en otro impuesto "
        "(renta, RST, ICA), el topic es el del otro impuesto."
    )
    scope_fn = taxonomy_add_scope_out(
        "iva",
        "Cuando la consulta es sobre cómo el IVA pagado se recupera en otro impuesto "
        "(renta, RST, ICA), el topic es el de ese otro impuesto, no IVA. El IVA aquí es un "
        "costo cuya recuperación se discute en otro régimen."
    )
    def _apply(state: dict[str, Any]) -> None:
        mutex_fn(state)
        scope_fn(state)
    return _apply


def taxonomy_q26_strengthen_iva_proc_with_rewrite_test() -> Callable[[dict[str, Any]], None]:
    """q26:A — strengthen mutex 1 with explicit override + rewrite-test heuristic."""
    base = taxonomy_strengthen_iva_proc_mutex()
    def _apply(state: dict[str, Any]) -> None:
        base(state)
        # Add the rewrite-test heuristic as a separate decision_rule augmentation
        for rule in state["taxonomy"].get("mutex_rules", []):
            if rule.get("id") == 1:
                heuristic = (
                    "TEST DE REESCRITURA — Si la pregunta puede reescribirse cambiando el "
                    "impuesto sustantivo (renta/IVA/timbre/retención/ICA) sin cambiar la "
                    "respuesta operativa, el topic es procedimiento_tributario."
                )
                existing = rule.get("rewrite_test", "")
                if heuristic not in existing:
                    rule["rewrite_test"] = heuristic
                return
    return _apply


def taxonomy_q28_regime_vs_mechanic() -> Callable[[dict[str, Any]], None]:
    """q28:B — Alejandro's regime-vs-mechanic mutex with the verb test."""
    rule_text = (
        "Cuando coexisten un régimen geográfico/sectorial (zona franca, ZESE, ZOMAC, RST, ESAL) "
        "y una mecánica fiscal (tarifa, base, exención): "
        "si la pregunta es sobre ESCOGER/EVALUAR el régimen → topic = régimen "
        "(zonas_francas, regimen_simple, regimen_tributario_especial_esal, etc.); "
        "si es sobre APLICAR la mecánica una vez ya estás en el régimen → "
        "topic = mecánica (tarifas_renta_y_ttd, etc.), con régimen como secondary. "
        "Verbo-test: 'estoy pensando / vale la pena / qué régimen / cómo califico' → régimen; "
        "'cuál es la tarifa / cuánto pago / cómo liquido' → mecánica."
    )
    return taxonomy_add_carve_out_mutex("regime_vs_mechanic_routing", "rule", rule_text)


def taxonomy_add_scope_out(topic_key: str, scope_out_text: str) -> Callable[[dict[str, Any]], None]:
    """q15:C — add scope_out clarification text to a topic."""
    def _apply(state: dict[str, Any]) -> None:
        tax = state["taxonomy"]
        for topic in tax.get("topics", []):
            if topic.get("key") == topic_key:
                existing = topic.get("scope_out", "")
                if scope_out_text not in existing:
                    topic["scope_out"] = (existing + " " + scope_out_text).strip() if existing else scope_out_text
                return
        raise RuntimeError(f"{topic_key} not in taxonomy")
    return _apply

# ─── makefile (always-on) ────────────────────────────────────────────────────

def ensure_makefile_use_llm() -> Callable[[dict[str, Any]], None]:
    def _apply(state: dict[str, Any]) -> None:
        text = state["makefile_text"]
        if "--threshold 27 --verbose --use-llm" in text:
            return  # already correct
        old = "--threshold 27 --verbose"
        if old not in text:
            raise RuntimeError("eval-taxonomy-v2 target shape changed — manual review needed")
        state["makefile_text"] = text.replace(old + "\n", old + " --use-llm\n", 1)
    return _apply

# ─── per-qid edit selection ──────────────────────────────────────────────────

def build_edits(decisions: dict[str, str], collected_no_collapse: list[str]) -> list[Callable[[dict[str, Any]], None]]:
    """Build the ordered list of edit functions for the chosen letters."""
    edits: list[Callable[[dict[str, Any]], None]] = []

    # q10
    if decisions["q10"] == "A":
        collected_no_collapse.append("firmeza_declaraciones")
        # Bonus per Alejandro 2026-04-25: extend keyword_anchors with the
        # civil-law vocabulary that contadores actually use for firmeza.
        edits.append(taxonomy_extend_keyword_anchors(
            "firmeza_declaraciones",
            ["prescribe", "prescripcion", "fiscalizacion", "cuestionar",
             "DIAN puede mirar atras", "cuantos anios atras"]
        ))
    else:
        edits.append(gold_widen(10, "declaracion_renta"))

    # q13 (per Alejandro 2026-04-25: B with rich generalizable rule)
    if decisions["q13"] == "A":
        edits.append(gold_widen(13, "impuesto_patrimonio_personas_naturales"))
    else:
        edits.append(taxonomy_q13_renta_presuntiva_vs_patrimonio())

    # q14 (per Alejandro 2026-04-25: A with mutex + iva scope_out clarification)
    if decisions["q14"] == "A":
        edits.append(taxonomy_q14_descuento_iva_bienes_capital())
    else:
        edits.append(gold_widen(14, "iva"))

    # q15
    if decisions["q15"] == "A":
        edits.append(taxonomy_deprecate_v1_retencion())
    elif decisions["q15"] == "C":
        edits.append(taxonomy_add_scope_out(
            "retencion_en_la_fuente",
            "Retención general (ET 365-419) → retencion_fuente_general."
        ))
        edits.append(taxonomy_add_scope_out(
            "retencion_fuente_general",
            "Retenciones específicas no cubiertas por ET 365-419 → retencion_en_la_fuente."
        ))
    else:
        # B = demote v2 to subtopic — too large; reject
        raise SystemExit(
            "q15:B (demote retencion_fuente_general to subtopic of retencion_en_la_fuente) "
            "is a large taxonomy refactor; the applier intentionally does not auto-execute it. "
            "Pick A or C, or open a separate engineering ticket."
        )

    # q16
    if decisions["q16"] == "A":
        collected_no_collapse.append("beneficio_auditoria")
    else:
        edits.append(gold_widen(16, "declaracion_renta"))

    # q26 (per Alejandro 2026-04-25: A with rewrite-test heuristic)
    if decisions["q26"] == "A":
        edits.append(taxonomy_q26_strengthen_iva_proc_with_rewrite_test())
    else:
        edits.append(gold_widen(26, "iva"))

    # q28 (per Alejandro 2026-04-25: B with regime-vs-mechanic generalization)
    if decisions["q28"] == "A":
        edits.append(gold_widen(28, "zonas_francas"))
    else:
        edits.append(taxonomy_q28_regime_vs_mechanic())

    # Always-on: bundle q10/q16 prompt edit if any are A
    if collected_no_collapse:
        edits.append(prompt_add_no_collapse(collected_no_collapse))

    # Always-on per Alejandro's meta-rule (2026-04-25): "el topic es el que
    # OPERA, no el que DEFINE" — generalizes to future ambiguities.
    edits.append(prompt_add_meta_rule_op_vs_def())

    # Always-on: makefile use-llm
    edits.append(ensure_makefile_use_llm())

    return edits

# ─── I/O ─────────────────────────────────────────────────────────────────────

def load_state() -> dict[str, Any]:
    return {
        "gold_rows": [json.loads(l) for l in GOLD.read_text(encoding="utf-8").splitlines() if l.strip()],
        "taxonomy": json.loads(TAXONOMY.read_text(encoding="utf-8")),
        "router_text": ROUTER.read_text(encoding="utf-8"),
        "makefile_text": MAKEFILE.read_text(encoding="utf-8"),
        "q15_corpus_migration_todo": False,
    }

def write_state(state: dict[str, Any], dry_run: bool) -> None:
    if dry_run:
        return
    GOLD.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in state["gold_rows"]) + "\n",
        encoding="utf-8",
    )
    TAXONOMY.write_text(
        json.dumps(state["taxonomy"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    ROUTER.write_text(state["router_text"], encoding="utf-8")
    MAKEFILE.write_text(state["makefile_text"], encoding="utf-8")

def diff_summary(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    """Per-file rough diff summary for dry-run output."""
    notes: list[str] = []
    if before["gold_rows"] != after["gold_rows"]:
        changed = [b["qid"] for b, a in zip(before["gold_rows"], after["gold_rows"]) if b != a]
        notes.append(f"  evals/gold_taxonomy_v2_validation.jsonl  → widened qids: {changed}")
    if json.dumps(before["taxonomy"]) != json.dumps(after["taxonomy"]):
        notes.append(f"  config/topic_taxonomy.json               → mutex/topic edits applied")
    if before["router_text"] != after["router_text"]:
        notes.append(f"  src/lia_graph/topic_router.py            → no-collapse exception list inserted")
    if before["makefile_text"] != after["makefile_text"]:
        notes.append(f"  Makefile                                  → eval-taxonomy-v2 target gains --use-llm")
    if not notes:
        notes.append("  (no changes — everything was already up to date)")
    return notes

# ─── main ────────────────────────────────────────────────────────────────────

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--decisions", required=True, help="comma-separated qN:LETTER pairs")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    decisions = parse_decisions(args.decisions)
    print(f"Decisions parsed: {decisions}")

    state_before = load_state()
    state = {k: (json.loads(json.dumps(v)) if isinstance(v, (list, dict)) else v) for k, v in state_before.items()}

    collected_no_collapse: list[str] = []
    edits = build_edits(decisions, collected_no_collapse)

    for fn in edits:
        fn(state)

    print()
    print("=== File changes ===")
    for line in diff_summary(state_before, state):
        print(line)
    print()
    if state.get("q15_corpus_migration_todo"):
        print("⚠  q15:A FOLLOW-UP — production has 14 docs on `retencion_en_la_fuente` (now deprecated) and 1 on `retencion_fuente_general`.")
        print("   Per Alejandro 2026-04-25: those 14 docs are likely a MIX of three retención conjuncts, not a single bucket:")
        print("     1. Retención que el contador practica como agente sobre pagos a terceros → retencion_fuente_general")
        print("     2. Retención que LE practicaron sobre sus ingresos (certificados art. 381 ET) → declaracion_renta")
        print("     3. Sanciones por no retener / retener mal / no consignar → regimen_sancionatorio_extemporaneidad")
        print("   So a blanket path-veto v1→v2 is INCORRECT — it would mis-route cases (2) and (3).")
        print("   Right approach: deprecate v1 (done by this applier), then re-run `bash scripts/launch_phase2_full_rebuild.sh`")
        print("   with workers=4 + taxonomy_aware=enforce. The classifier will see v1 has been removed from the candidate")
        print("   list and re-route each doc into the correct conjunct based on content. NO path-veto rule needed.")
        print()

    if args.dry_run:
        print("DRY-RUN — no files written. Re-run without --dry-run to apply.")
        return

    write_state(state, dry_run=False)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    revert_path = REPO_ROOT / "artifacts/sme_pending" / f"{ts}_revert.json"
    revert_path.write_text(json.dumps({
        "applied_at_utc": ts,
        "decisions": decisions,
        "before_snapshot": {
            "gold_rows": state_before["gold_rows"],
            "taxonomy": state_before["taxonomy"],
            "router_text": state_before["router_text"],
            "makefile_text": state_before["makefile_text"],
        },
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Applied. Revert snapshot: {revert_path.relative_to(REPO_ROOT)}")
    print()
    print("Next: `make eval-taxonomy-v2`. If chat-resolver >= 27/30, gate 8 ✅.")

if __name__ == "__main__":
    main()
