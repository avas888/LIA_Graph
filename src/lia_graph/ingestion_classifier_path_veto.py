"""next_v3 §13.6 Option K2 — rule-based path-veto layer above the LLM.

2026-04-25 Cypher verification (§13.3) showed the taxonomy-aware prompt
couldn't override pre-existing wrong verdicts on 4 of 5 flip rows — the
LLM treats the PATH VETO clause as guidance, not a hard constraint. This
is the SME-predicted Option K2 (next_v2.md §K): a deterministic post-LLM
sanity check that forces the correct topic when the source_path carries
unambiguous signal.

Rules fire only when the path substring is present. Outside of the
RENTA/NORMATIVA/Normativa/ tree the LLM verdict is left untouched.

Module split per ``feedback_granular_edits``: the rule list grows whenever
a new BRECHAS-SEMANA trilogy lands or a new ET libro folder is curated,
so it lives in its own sibling rather than bloating
``ingestion_classifier.py``.
"""

from __future__ import annotations


# Tuples of (path-substring, canonical_topic). Most-specific patterns MUST
# appear before less-specific ones — first match wins.
_PATH_VETO_RULES: tuple[tuple[str, str], ...] = (
    # --- ET Libro 1 (renta family), chapter-by-chapter ---
    ("02_Libro1_T1_Cap1_Ingresos",              "ingresos_fiscales_renta"),
    ("03_Libro1_T1_Cap2_Costos",                "costos_deducciones_renta"),
    ("04_Libro1_T1_Cap3_Renta_Bruta",           "declaracion_renta"),
    ("05_Libro1_T1_Cap4_Renta_Liquida",         "renta_liquida_gravable"),
    ("06_Libro1_T1_Cap5_Deducciones",           "costos_deducciones_renta"),
    ("07_Libro1_T1_Cap6_Rentas_Especiales_Presuntiva", "renta_presuntiva"),
    ("08_Libro1_T1_Cap7_Rentas_Exentas",        "rentas_exentas"),
    ("09_Libro1_T1_Caps8a11",                   "declaracion_renta"),
    ("10_Libro1_T2_Patrimonio",                 "patrimonio_fiscal_renta"),
    ("11_Libro1_T3_Ganancias_Ocasionales",      "ganancia_ocasional"),
    ("12_Libro1_T4_Remesas",                    "declaracion_renta"),
    ("13_Libro1_T5_Ajustes_Inflacion",          "declaracion_renta"),
    ("14_Libro1_T6_Regimen_Especial",           "regimen_tributario_especial_esal"),
    ("01_Libro1_T1_Sujetos_Pasivos",            "declaracion_renta"),
    ("00_Titulo_Preliminar",                    "declaracion_renta"),
    # --- ET other books ---
    ("15_Libro2_Retencion_Fuente",              "retencion_fuente_general"),
    ("16_Libro3_IVA",                           "iva"),
    ("17_Libro4_Timbre",                        "impuesto_timbre"),
    ("18_Libro5_Procedimiento_P1",              "procedimiento_tributario"),
    ("19_Libro5_Procedimiento_P2",              "procedimiento_tributario"),
    ("20_Libro6_GMF",                           "gravamen_movimiento_financiero_4x1000"),
    ("21_Libro7_ECE_CHC",                       "declaracion_renta"),
    ("22_Libro8_SIMPLE",                        "regimen_simple"),
    # --- BRECHAS-SEMANA gap-fill folders (operator's state.md tracks 5 trilogies).
    # Each trilogy folder IS the topic boundary — the LLM classifier was drifting
    # to adjacent topics (`iva`, `ica`, `procedimiento_tributario` etc.) on the
    # FIRMEZA trilogy because the body content cites cross-topic articles.
    # Per `docs/learnings/ingestion/path-veto-rule-based-classifier-correction.md`:
    # the path encodes ground truth; the override is the right tool. Added
    # 2026-04-26 after the FIRMEZA verification round.
    ("FIRMEZA_DECLARACIONES",                   "firmeza_declaraciones"),
    ("REGIMEN_SANCIONATORIO_EXTEMPORANEIDAD",   "regimen_sancionatorio_extemporaneidad"),
    ("DEVOLUCIONES_SALDOS_FAVOR",               "devoluciones_saldos_a_favor"),
    ("COSTOS_DEDUCCIONES_RENTA",                "costos_deducciones_renta"),
    ("BENEFICIOS_TRIBUTARIOS_AMBIENTALES",      "sector_medio_ambiente"),
)


def _apply_path_veto(
    filename: str, llm_verdict: str | None
) -> tuple[str | None, str | None, bool]:
    """Force the canonical topic for clear path-based signals.

    Returns ``(final_topic, veto_reason, rule_matched)``.

    - ``rule_matched`` is True when ANY rule in ``_PATH_VETO_RULES`` matches
      the filename, regardless of whether the LLM verdict was already correct.
      Downstream consumers MUST honor a matched rule by treating
      ``final_topic`` as authoritative against the document's legacy
      ``topic_key`` (which may carry stale path-inferred or alias-inferred
      values from before classification).
    - ``veto_reason`` is non-None only when the rule actually overrode a
      different LLM verdict — that is the signal to emit the
      ``classifier.path_veto_applied`` instrumentation event.
    """
    if not filename:
        return llm_verdict, None, False
    for needle, canonical in _PATH_VETO_RULES:
        if needle in filename:
            if llm_verdict == canonical:
                # Rule matched but LLM already correct — assert canonical
                # topic anyway so the doc.topic_key gets propagated.
                return canonical, None, True
            return canonical, f"path_veto:{needle}:{canonical}", True
    return llm_verdict, None, False


__all__ = [
    "_PATH_VETO_RULES",
    "_apply_path_veto",
]
