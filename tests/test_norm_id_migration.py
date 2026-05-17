"""Tests for `scripts/migrate_falkor_norm_ids.py` derivation rules.

Locks in (source_path, article_number) → norm_id derivation per the
v19 Fase 2 plan. Tests are pure-Python — no Falkor / Supabase access
needed. They exercise the public `derive_norm_id` entry point.

If a new family is added to `_RULES`, append a row here covering it.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT_PATH = REPO_ROOT / "scripts" / "migrate_falkor_norm_ids.py"


def _load_migration_module():
    spec = importlib.util.spec_from_file_location(
        "migrate_falkor_norm_ids", _SCRIPT_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def mig():
    return _load_migration_module()


# ---------------------------------------------------------------------------
# Happy path — each family bucket gets at least one canonical norm_id
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "source_path,article_number,expected_norm_id,expected_rule",
    [
        # CST consolidado — the new corpus addition this migration was designed for
        (
            "knowledge_base/CORE ya Arriba/LEYES/LABORAL_SEGURIDAD_SOCIAL/consolidado/Codigo_Sustantivo_Trabajo.md",
            "64",
            "cst.art.64",
            "cst_consolidado",
        ),
        (
            "knowledge_base/CORE ya Arriba/LEYES/LABORAL_SEGURIDAD_SOCIAL/consolidado/Codigo_Sustantivo_Trabajo.md",
            "127",
            "cst.art.127",
            "cst_consolidado",
        ),
        # CST with letter-suffix composite (parser fix landed 2026-05-15)
        (
            "knowledge_base/CORE ya Arriba/LEYES/LABORAL_SEGURIDAD_SOCIAL/consolidado/Codigo_Sustantivo_Trabajo.md",
            "97-A",
            "cst.art.97-A",
            "cst_consolidado",
        ),
        # CST with digit-suffix composite
        (
            "knowledge_base/CORE ya Arriba/LEYES/LABORAL_SEGURIDAD_SOCIAL/consolidado/Codigo_Sustantivo_Trabajo.md",
            "391-1",
            "cst.art.391-1",
            "cst_consolidado",
        ),

        # Ley laborales — filename embeds Ley NUM YEAR
        (
            "knowledge_base/CORE ya Arriba/LEYES/LABORAL_SEGURIDAD_SOCIAL/consolidado/Ley-50-1990.md",
            "64",
            "ley.50.1990.art.64",
            "ley_filename",
        ),
        (
            "knowledge_base/CORE ya Arriba/LEYES/LABORAL_SEGURIDAD_SOCIAL/consolidado/Ley-789-2002.md",
            "28",
            "ley.789.2002.art.28",
            "ley_filename",
        ),
        (
            "knowledge_base/CORE ya Arriba/LEYES/LABORAL_SEGURIDAD_SOCIAL/consolidado/Ley-100-1993.md",
            "47",
            "ley.100.1993.art.47",
            "ley_filename",
        ),
        # Ley laborales in NORMATIVA folder (parallel path)
        (
            "knowledge_base/CORE ya Arriba/LEYES/LABORAL_SEGURIDAD_SOCIAL/NORMATIVA/Ley-100-1993.md",
            "1",
            "ley.100.1993.art.1",
            "ley_filename",
        ),
        # Ley comercial / societario
        (
            "knowledge_base/CORE ya Arriba/LEYES/COMERCIAL_SOCIETARIO/NORMATIVA/Ley-1231-2008.md",
            "4",
            "ley.1231.2008.art.4",
            "ley_filename",
        ),
        (
            "knowledge_base/CORE ya Arriba/LEYES/COMERCIAL_SOCIETARIO/NORMATIVA/Ley-1258-2008.md",
            "77",
            "ley.1258.2008.art.77",
            "ley_filename",
        ),
        # REFORMA_LABORAL_LEY_2466 — fires the dedicated rule (path keyword),
        # NOT the ley_filename rule (more specific wins via priority order)
        (
            "knowledge_base/CORE ya Arriba/REFORMA_LABORAL_LEY_2466/NORMATIVA/REF-N01-marco-legal-reforma-laboral-ley-2466-2025.md",
            "11",
            "ley.2466.2025.art.11",
            "reforma_laboral_2466",
        ),
        # Also fires when the Ley 2466 consolidado is in the LABORAL_SEGURIDAD_SOCIAL folder
        (
            "knowledge_base/CORE ya Arriba/LEYES/LABORAL_SEGURIDAD_SOCIAL/consolidado/Ley-2466-2025.md",
            "11",
            "ley.2466.2025.art.11",
            "reforma_laboral_2466",
        ),

        # Decretos — DT-NUM-YEAR filename pattern
        (
            "knowledge_base/CORE ya Arriba/NORMATIVA_LEYES/DT-1221-2008-NORMATIVA.md",
            "1",
            "decreto.1221.2008.art.1",
            "decreto_filename",
        ),
        # Decreto with the `decreto-NUM-...` filename pattern
        (
            "knowledge_base/CORE ya Arriba/NUEVOS-DATOS-BRECHAS-MARZO-2026/01-DECRETO-0240-EMERGENCIA-TRIBUTARIA/NORMATIVA/N-D0240-decreto-0240-emergencia-tributaria.md",
            "1",
            "decreto.240.2026.art.1",
            "decreto_filename",
        ),

        # ET — explicit `-ET.md` filename suffix
        (
            "knowledge_base/to upload/AGGRANDIZEMENT-ABRIL-2026/DEPRECIACION_FISCAL/NORMATIVA/DEP-N01-depreciacion-fiscal-arts-137-140-ET.md",
            "137",
            "et.art.137",
            "et_explicit_filename",
        ),
        # ET — explicit `-art-714-ET.md` suffix
        (
            "knowledge_base/CORE ya Arriba/FIRMEZA_DECLARACIONES_ART714/NORMATIVA/FIR-N01-marco-legal-firmeza-declaraciones-tributarias-art-714-ET.md",
            "714",
            "et.art.714",
            "et_explicit_filename",
        ),

        # ET — falls to topic-folder default (IVA / RENTA / Corpus de Contabilidad)
        (
            "knowledge_base/CORE ya Arriba/IVA_COMPLETO/NORMATIVA/IVA-N01-hechos-generadores-responsables-tarifas.md",
            "420",
            "et.art.420",
            "et_topic_folder_default",
        ),
        (
            "knowledge_base/CORE ya Arriba/IVA_COMPLETO/NORMATIVA/IVA-N01-hechos-generadores-responsables-tarifas.md",
            "437",
            "et.art.437",
            "et_topic_folder_default",
        ),
        (
            "knowledge_base/CORE ya Arriba/Corpus de Contabilidad/NORMATIVA/N-ESAL-regimen-tributario-especial.md",
            "19",
            "et.art.19",
            "et_topic_folder_default",
        ),
        (
            "knowledge_base/CORE ya Arriba/DIVIDENDOS_UTILIDADES/NORMATIVA/DIV-N01-marco-legal-dividendos-utilidades-distribucion-retencion.md",
            "242",
            "et.art.242",
            "et_topic_folder_default",
        ),
        (
            "knowledge_base/CORE ya Arriba/PERDIDAS_FISCALES_ART147/NORMATIVA/PER-N01-perdidas-fiscales-art-147.md",
            "147",
            "et.art.147",
            "et_topic_folder_default",
        ),

        # ET — composite article numbers (digit-suffix)
        (
            "knowledge_base/CORE ya Arriba/Corpus de Contabilidad/NORMATIVA/N-INC-impuesto-nacional-consumo.md",
            "512-1",
            "et.art.512-1",
            "et_topic_folder_default",
        ),
        (
            "knowledge_base/to upload/BRECHAS-SEMANA1-ABRIL-2026/FE_OPERATIVA/NORMATIVA/FE-N02-habilitacion-contingencia-radian-marco-legal.md",
            "616-1",
            "et.art.616-1",
            "et_topic_folder_default",
        ),
        (
            "knowledge_base/CORE ya Arriba/BENEFICIARIO_FINAL_RUB/NORMATIVA/N01-registro-unico-beneficiarios-finales-marco-legal.md",
            "631-5",
            "et.art.631-5",
            "et_topic_folder_default",
        ),
        (
            "knowledge_base/to upload/BRECHAS-SEMANA4-ABRIL-2026/FIRMEZA_DECLARACIONES/NORMATIVA/NORMATIVA_FIR-N02-marco-legal-firmeza-AG2025-declaracion-2026.md",
            "689-3",
            "et.art.689-3",
            "et_topic_folder_default",
        ),

        # Resolución DIAN
        (
            "knowledge_base/laboral/Resolucion-532-2024.md",
            "5",
            "res.dian.532.2024.art.5",
            "resolucion_filename",
        ),
    ],
)
def test_known_corpus_path_derives_expected_norm_id(
    mig, source_path, article_number, expected_norm_id, expected_rule,
):
    outcome = mig.derive_norm_id(
        article_id=article_number,
        article_number=article_number,
        source_path=source_path,
    )
    assert outcome.norm_id == expected_norm_id, (
        f"path={source_path!r} art={article_number!r}: "
        f"got norm_id={outcome.norm_id!r} via rule={outcome.rule_name!r} "
        f"(mention={outcome.mention!r}, refusal={outcome.refusal_reason!r})"
    )
    assert outcome.rule_name == expected_rule, (
        f"expected rule {expected_rule!r}, got {outcome.rule_name!r} "
        f"(mention={outcome.mention!r})"
    )


# ---------------------------------------------------------------------------
# Prose-only — empty article_number must NOT produce a norm_id
# ---------------------------------------------------------------------------


def test_prose_only_article_returns_none(mig):
    outcome = mig.derive_norm_id(
        article_id="whole::knowledge_base/...some-prose-only-doc.md",
        article_number="",
        source_path="knowledge_base/CORE ya Arriba/LABORAL_NOMINA/PLAYBOOKS/playbook_laboral_pila_aportes.md",
    )
    assert outcome.norm_id is None
    assert outcome.rule_name == "prose_only"
    assert outcome.refusal_reason is None  # not a refusal — expected behavior


def test_prose_only_with_whitespace_article_number(mig):
    """Trailing whitespace on an empty number must still classify as prose_only."""
    outcome = mig.derive_norm_id(
        article_id="whole::some-doc.md",
        article_number="   ",
        source_path="knowledge_base/CORE ya Arriba/LABORAL_NOMINA/PLAYBOOKS/playbook_a.md",
    )
    assert outcome.rule_name == "prose_only"
    assert outcome.norm_id is None


# ---------------------------------------------------------------------------
# OTHER — unclassifiable paths must abort the dry-run strict gate
# ---------------------------------------------------------------------------


def test_unknown_topic_folder_with_numbered_article_classifies_as_other(mig):
    """A numbered article whose source_path doesn't match any rule must
    fall through to OTHER, not silently default to ET."""
    outcome = mig.derive_norm_id(
        article_id="42",
        article_number="42",
        source_path="some/completely/unknown/path/random.md",
    )
    assert outcome.norm_id is None
    assert outcome.rule_name == "OTHER"
    assert outcome.refusal_reason == "no_path_rule_matched"


def test_empty_source_path_with_numbered_article_is_other(mig):
    outcome = mig.derive_norm_id(
        article_id="64",
        article_number="64",
        source_path="",
    )
    assert outcome.norm_id is None
    assert outcome.rule_name == "OTHER"


# ---------------------------------------------------------------------------
# Idempotency — already-canonical input should be preserved
# ---------------------------------------------------------------------------


def test_already_canonical_input_is_preserved(mig):
    """If a node's `article_id` is already a valid norm_id (re-run case),
    keep it. Don't try to re-derive from source_path."""
    outcome = mig.derive_norm_id(
        article_id="et.art.64",
        article_number="64",
        source_path="knowledge_base/CORE ya Arriba/Corpus de Contabilidad/NORMATIVA/some.md",
    )
    assert outcome.norm_id == "et.art.64"
    assert outcome.rule_name == "idempotent"


def test_idempotent_for_cst_canonical(mig):
    outcome = mig.derive_norm_id(
        article_id="cst.art.64",
        article_number="64",
        source_path="anything",
    )
    assert outcome.norm_id == "cst.art.64"
    assert outcome.rule_name == "idempotent"


def test_idempotent_for_decreto_dur_canonical(mig):
    outcome = mig.derive_norm_id(
        article_id="decreto.1625.2016.art.1.6.1.1.10",
        article_number="1.6.1.1.10",
        source_path="anything",
    )
    assert outcome.norm_id == "decreto.1625.2016.art.1.6.1.1.10"
    assert outcome.rule_name == "idempotent"


# ---------------------------------------------------------------------------
# Priority — more-specific rule wins over more-generic
# ---------------------------------------------------------------------------


def test_cst_path_with_ley_in_folder_name_still_picks_cst(mig):
    """Codigo_Sustantivo_Trabajo.md sits inside a LEYES folder. The CST
    rule has higher priority than the ley_filename rule, and the filename
    doesn't match Ley-NUM-YEAR, so CST wins."""
    outcome = mig.derive_norm_id(
        article_id="64",
        article_number="64",
        source_path="knowledge_base/CORE ya Arriba/LEYES/LABORAL_SEGURIDAD_SOCIAL/consolidado/Codigo_Sustantivo_Trabajo.md",
    )
    assert outcome.norm_id == "cst.art.64"
    assert outcome.rule_name == "cst_consolidado"


def test_reforma_2466_path_wins_over_ley_filename(mig):
    """REFORMA_LABORAL_LEY_2466 folder + Ley-2466-2025.md filename — both rules
    would match. The dedicated reforma rule is higher priority and wins."""
    outcome = mig.derive_norm_id(
        article_id="11",
        article_number="11",
        source_path="knowledge_base/CORE ya Arriba/REFORMA_LABORAL_LEY_2466/NORMATIVA/Ley-2466-2025.md",
    )
    assert outcome.norm_id == "ley.2466.2025.art.11"
    assert outcome.rule_name == "reforma_laboral_2466"


def test_ley_filename_wins_over_et_topic_default(mig):
    """A Ley-NUM-YEAR.md sitting inside a topic folder still classifies as
    Ley, not as ET (ley_filename has higher priority than et_topic_folder_default)."""
    outcome = mig.derive_norm_id(
        article_id="64",
        article_number="64",
        source_path="knowledge_base/CORE ya Arriba/RENTA/NORMATIVA/Ley-2277-2022.md",
    )
    assert outcome.norm_id == "ley.2277.2022.art.64"
    assert outcome.rule_name == "ley_filename"


# ---------------------------------------------------------------------------
# Smoke — derive a small bag, confirm summary buckets balance
# ---------------------------------------------------------------------------


def test_migration_plan_bucketing(mig):
    """Sanity-check that `MigrationPlan.bucket()` populates counts and
    catches duplicate norm_ids correctly."""
    plan = mig.MigrationPlan()
    cases = [
        ("a1", "64", "knowledge_base/CORE ya Arriba/LEYES/LABORAL_SEGURIDAD_SOCIAL/consolidado/Codigo_Sustantivo_Trabajo.md"),
        ("a2", "64", "knowledge_base/CORE ya Arriba/Corpus de Contabilidad/NORMATIVA/N-some-et.md"),  # ET 64
        ("a3", "127", "knowledge_base/CORE ya Arriba/LEYES/LABORAL_SEGURIDAD_SOCIAL/consolidado/Codigo_Sustantivo_Trabajo.md"),
        ("a4", "", "knowledge_base/some/prose-only.md"),
        ("a5", "999", "completely/unknown/path.md"),  # OTHER
        ("a6", "64", "knowledge_base/CORE ya Arriba/LEYES/LABORAL_SEGURIDAD_SOCIAL/consolidado/Ley-50-1990.md"),
    ]
    for aid, num, sp in cases:
        plan.outcomes.append(mig.derive_norm_id(
            article_id=aid, article_number=num, source_path=sp,
        ))
    plan.bucket()

    assert plan.total() == 6
    assert plan.prose_only_count() == 1
    assert plan.other_count() == 1
    # cst.art.64 / et.art.64 / cst.art.127 / ley.50.1990.art.64 — all distinct → no duplicates
    assert plan.duplicates == {}
    assert plan.classified_count() == 4
    assert plan.counts.get("cst_consolidado") == 2
    assert plan.counts.get("ley_filename") == 1


def test_duplicate_norm_ids_are_flagged(mig):
    """Two nodes sharing source_path + article_number should produce the same
    norm_id — and `MigrationPlan.bucket()` should surface it as a duplicate."""
    plan = mig.MigrationPlan()
    sp = "knowledge_base/CORE ya Arriba/Corpus de Contabilidad/NORMATIVA/N-some-et.md"
    plan.outcomes.append(mig.derive_norm_id(article_id="a1", article_number="64", source_path=sp))
    plan.outcomes.append(mig.derive_norm_id(article_id="a2", article_number="64", source_path=sp))
    plan.bucket()
    assert "et.art.64" in plan.duplicates
    assert sorted(plan.duplicates["et.art.64"]) == ["a1", "a2"]


# ---------------------------------------------------------------------------
# Staging-dry-run-driven regressions — added 2026-05-15 from real cloud data
# ---------------------------------------------------------------------------


def test_suin_paths_classify_as_suin_skipped_not_other(mig):
    """SUIN-derived nodes (`suin://N`) — v6's domain. v19 leaves them alone.
    Must bucket as `suin_skipped`, NOT `OTHER` (otherwise strict mode would
    block on 6,805 nodes per the 2026-05-15 staging dry-run)."""
    outcome = mig.derive_norm_id(
        article_id="1003086",
        article_number="1003086",
        source_path="suin://1003082",
    )
    assert outcome.norm_id is None
    assert outcome.rule_name == "suin_skipped"
    # Explicitly DIFFERENT from OTHER — refusal_reason carries context
    assert outcome.refusal_reason == "suin_external_canonical"


def test_suin_composite_numbers_also_skipped(mig):
    outcome = mig.derive_norm_id(
        article_id="1-1",
        article_number="1-1",
        source_path="suin://30033510",
    )
    assert outcome.rule_name == "suin_skipped"
    assert outcome.norm_id is None


def test_ley_filename_with_trailing_underscore_text(mig):
    """`Ley_599_2000_CodigoPenalDelitosF.md` — underscore between year and
    trailing text broke the original `\\b` boundary. Fixed via lookahead.
    Staging dry-run surfaced this 2026-05-15."""
    outcome = mig.derive_norm_id(
        article_id="148",
        article_number="148",
        source_path="knowledge_base/CORE ya Arriba/LEYES/OTROS_SECTORIALES/Ley_599_2000_CodigoPenalDelitosF.md",
    )
    assert outcome.norm_id == "ley.599.2000.art.148"
    assert outcome.rule_name == "ley_filename"


def test_reforma_laboral_hyphenated_path(mig):
    """`NUEVOS-DATOS-BRECHAS-MARZO-2026/03-REFORMA-LABORAL-LEY-2466/...` —
    hyphen-separated folder name, not underscore. Original rule only
    matched underscore form."""
    outcome = mig.derive_norm_id(
        article_id="16-19",
        article_number="16-19",
        source_path="knowledge_base/CORE ya Arriba/NUEVOS-DATOS-BRECHAS-MARZO-2026/03-REFORMA-LABORAL-LEY-2466/NORMATIVA/N-REF-LABORAL-ley-2466-reforma-laboral.md",
    )
    assert outcome.norm_id == "ley.2466.2025.art.16-19"
    assert outcome.rule_name == "reforma_laboral_2466"


def test_nomina_electronica_folder_defaults_to_et(mig):
    """`NOMINA_ELECTRONICA_NOVEDADES/NORMATIVA/...` references ET articles
    by number (186, 187, 192, 227, 249 → ET). Added to whitelist 2026-05-15."""
    outcome = mig.derive_norm_id(
        article_id="249",
        article_number="249",
        source_path="knowledge_base/to upload/BRECHAS-SEMANA2-ABRIL-2026/NOMINA_ELECTRONICA_NOVEDADES/NORMATIVA/NOM-N01-nomina-electronica-novedades-marco-legal.md",
    )
    assert outcome.norm_id == "et.art.249"
    assert outcome.rule_name == "et_topic_folder_default"


def test_devoluciones_saldos_favor_defaults_to_et(mig):
    """`Documents to branch and improve/Devoluciones_Saldos_Favor/Normativa_Base/`
    references ET articles (855-1, 815, 816, 850). Added to whitelist."""
    outcome = mig.derive_norm_id(
        article_id="855-1",
        article_number="855-1",
        source_path="knowledge_base/CORE ya Arriba/Documents to branch and improve/Devoluciones_Saldos_Favor/Normativa_Base/dev_normativa_devoluciones.md",
    )
    assert outcome.norm_id == "et.art.855-1"


def test_cam_n01_ley_9_1991_explicit_articles(mig):
    """`CAM-N01-declaracion-cambio-marco-legal-...md` Section 1 is the
    Estatuto Cambiario (Ley 9/1991), articles 1-5. Confirmed by reading
    the markdown header 2026-05-15."""
    for num in ["1", "2", "3", "4", "5"]:
        outcome = mig.derive_norm_id(
            article_id=num,
            article_number=num,
            source_path="knowledge_base/to upload/BRECHAS-SEMANA2-ABRIL-2026/CAM_DECLARACION_CAMBIO/NORMATIVA/CAM-N01-declaracion-cambio-marco-legal-formularios-banco-republica.md",
        )
        assert outcome.norm_id == f"ley.9.1991.art.{num}"
        assert outcome.rule_name == "cam_n01_ley_9_1991"


def test_cam_n01_article_6_is_parser_artifact_stays_other(mig):
    """article_number=6 in CAM-N01 comes from parser collapsing the
    `### ARTÍCULO 6.1. CONDUCTAS SANCIONABLES` section heading.
    NOT a Ley 9/1991 article. Stays OTHER deliberately."""
    outcome = mig.derive_norm_id(
        article_id="6",
        article_number="6",
        source_path="knowledge_base/to upload/BRECHAS-SEMANA2-ABRIL-2026/CAM_DECLARACION_CAMBIO/NORMATIVA/CAM-N01-declaracion-cambio-marco-legal-formularios-banco-republica.md",
    )
    assert outcome.rule_name == "OTHER"
    assert outcome.norm_id is None


def test_cam_path_outside_n01_still_other(mig):
    """Other CAM_* docs (CAM-N02, etc., should they exist) don't match
    the CAM-N01 specific rule and stay OTHER for operator review."""
    outcome = mig.derive_norm_id(
        article_id="1",
        article_number="1",
        source_path="knowledge_base/to upload/.../CAM_DECLARACION_CAMBIO/NORMATIVA/CAM-N02-other-doc.md",
    )
    assert outcome.rule_name == "OTHER"


# ---------------------------------------------------------------------------
# v20 P1-T5 regressions — added 2026-05-16 from local-rehearsal OTHER bucket
# (84 articles across 13 paths; below cover every distinct path).
# ---------------------------------------------------------------------------


def test_precios_transferencia_normativa_base_maps_to_et(mig):
    """Precios_Transferencia expert summary references ET 260-N. Without the
    parser splitting `260` + heading `1 ET. ...` into `260-1`, we map the bare
    `260` to et.art.260 so it merges with the canonical ET source."""
    outcome = mig.derive_norm_id(
        article_id="260",
        article_number="260",
        source_path="knowledge_base/CORE ya Arriba/Documents to branch and improve/Precios_Transferencia/Normativa_Base/pt_normativa_precios_transferencia.md",
    )
    assert outcome.norm_id == "et.art.260"
    assert outcome.rule_name == "et_topic_folder_default"


def test_devoluciones_dashed_folder_maps_to_et(mig):
    """`NUEVOS-DATOS-BRECHAS-MARZO-2026/07-DEVOLUCIONES-SALDOS-A-FAVOR/...` —
    dash-form mirror of the existing `/Devoluciones_Saldos_Favor` underscore
    marker. Same target (ET)."""
    outcome = mig.derive_norm_id(
        article_id="855-1",
        article_number="855-1",
        source_path="knowledge_base/CORE ya Arriba/NUEVOS-DATOS-BRECHAS-MARZO-2026/07-DEVOLUCIONES-SALDOS-A-FAVOR/NORMATIVA/N-DEV-devoluciones-saldos-a-favor.md",
    )
    assert outcome.norm_id == "et.art.855-1"
    assert outcome.rule_name == "et_topic_folder_default"


def test_rst_dashed_folder_maps_to_et(mig):
    """`04-RST-REGIMEN-SIMPLE-TRIBUTACION/NORMATIVA/...` — dash-form mirror
    of `/REGIMEN_SIMPLE`."""
    outcome = mig.derive_norm_id(
        article_id="908",
        article_number="908",
        source_path="knowledge_base/CORE ya Arriba/NUEVOS-DATOS-BRECHAS-MARZO-2026/04-RST-REGIMEN-SIMPLE-TRIBUTACION/NORMATIVA/N-RST-regimen-simple-tributacion.md",
    )
    assert outcome.norm_id == "et.art.908"


def test_jcc_dashed_folder_maps_to_et(mig):
    """`09-OBLIGACIONES-PROFESIONALES-JCC/NORMATIVA/...` — dash-form mirror
    of `/OBLIGACIONES_PROFESIONALES_CONTADOR`."""
    outcome = mig.derive_norm_id(
        article_id="572",
        article_number="572",
        source_path="knowledge_base/CORE ya Arriba/NUEVOS-DATOS-BRECHAS-MARZO-2026/09-OBLIGACIONES-PROFESIONALES-JCC/NORMATIVA/N-JCC-obligaciones-profesionales-contador.md",
    )
    assert outcome.norm_id == "et.art.572"


def test_tributacion_dividendos_maps_to_et(mig):
    """`Documents to branch and improve/Tributacion_Dividendos/Normativa_Base/`
    — companion to the existing `/DIVIDENDOS_UTILIDADES` marker."""
    outcome = mig.derive_norm_id(
        article_id="242",
        article_number="242",
        source_path="knowledge_base/CORE ya Arriba/Documents to branch and improve/Tributacion_Dividendos/Normativa_Base/div_normativa_dividendos.md",
    )
    assert outcome.norm_id == "et.art.242"


def test_descuentos_inventarios_niif_maps_to_et(mig):
    """`DESCUENTOS_INVENTARIOS_NIIF/NORMATIVA/DIAN-DESC-*` — ET doctrine."""
    outcome = mig.derive_norm_id(
        article_id="21",
        article_number="21",
        source_path="knowledge_base/CORE ya Arriba/DESCUENTOS_INVENTARIOS_NIIF/NORMATIVA/DIAN-DESC-01-doctrina-descuentos-comerciales-condicionados.md",
    )
    assert outcome.norm_id == "et.art.21"


def test_procedimiento_tributario_lowercase_folder_maps_to_et(mig):
    """Lowercase `/procedimiento_tributario/` path — mirror of uppercase marker.
    Surfaced by `NORMATIVA_FIR-N02-marco-legal-firmeza-AG2025-declaracion-2026.md`."""
    outcome = mig.derive_norm_id(
        article_id="714",
        article_number="714",
        source_path="knowledge_base/procedimiento_tributario/NORMATIVA_FIR-N02-marco-legal-firmeza-AG2025-declaracion-2026.md",
    )
    assert outcome.norm_id == "et.art.714"


def test_nc_filename_ley_1314_2009(mig):
    """`NC-1314-2009-NORMATIVA.md` — Norma Contable filename convention for
    Ley 1314 de 2009 (Marco Técnico Contable)."""
    outcome = mig.derive_norm_id(
        article_id="1",
        article_number="1",
        source_path="knowledge_base/CORE ya Arriba/NORMATIVA_LEYES/NC-1314-2009-NORMATIVA.md",
    )
    assert outcome.norm_id == "ley.1314.2009.art.1"
    assert outcome.rule_name == "nc_filename"


def test_emergencia_decreto_0240_2026(mig):
    """`Documents to branch and improve/Emergencia_Tributaria_Decreto_0240/
    Normativa_Base/eme_normativa_decreto_0240.md` — Decreto 0240/2026 emergency
    tributary doc, no year in filename so a dedicated rule handles it."""
    outcome = mig.derive_norm_id(
        article_id="1",
        article_number="1",
        source_path="knowledge_base/CORE ya Arriba/Documents to branch and improve/Emergencia_Tributaria_Decreto_0240/Normativa_Base/eme_normativa_decreto_0240.md",
    )
    assert outcome.norm_id == "decreto.0240.2026.art.1"
    assert outcome.rule_name == "emergencia_decreto_0240"


def test_regimen_cambiario_summary_maps_to_ley_9_1991(mig):
    """`Documents to branch and improve/Regimen_Cambiario/Normativa_Base/
    cam_normativa_regimen_cambiario.md` — Estatuto Cambiario expert summary.
    Maps arts 1-26 to Ley 9/1991."""
    outcome = mig.derive_norm_id(
        article_id="2",
        article_number="2",
        source_path="knowledge_base/CORE ya Arriba/Documents to branch and improve/Regimen_Cambiario/Normativa_Base/cam_normativa_regimen_cambiario.md",
    )
    assert outcome.norm_id == "ley.9.1991.art.2"
    assert outcome.rule_name == "regimen_cambiario_ley_9_1991"


def test_regimen_cambiario_pyme_n01_maps_to_ley_9_1991(mig):
    """`REGIMEN_CAMBIARIO_PYME/NORMATIVA/N01-regimen-cambiario-pyme-marco-legal.md`
    — same Estatuto Cambiario, PYME-focused expert summary."""
    outcome = mig.derive_norm_id(
        article_id="10",
        article_number="10",
        source_path="knowledge_base/CORE ya Arriba/REGIMEN_CAMBIARIO_PYME/NORMATIVA/N01-regimen-cambiario-pyme-marco-legal.md",
    )
    assert outcome.norm_id == "ley.9.1991.art.10"
    assert outcome.rule_name == "regimen_cambiario_ley_9_1991"


def test_regimen_cambiario_out_of_range_article_stays_other(mig):
    """Ley 9/1991 has 26 articles. Article numbers > 26 in Régimen Cambiario
    docs are parser artifacts (section headings) — stay OTHER deliberately."""
    outcome = mig.derive_norm_id(
        article_id="99",
        article_number="99",
        source_path="knowledge_base/CORE ya Arriba/Documents to branch and improve/Regimen_Cambiario/Normativa_Base/cam_normativa_regimen_cambiario.md",
    )
    assert outcome.rule_name == "OTHER"
    assert outcome.norm_id is None


def test_revisoria_fiscal_summary_maps_to_cco(mig):
    """`Documents to branch and improve/Revisoria_Fiscal/Normativa_Base/
    rev_normativa_revisoria_fiscal.md` — Revisoría Fiscal is governed by
    Codigo de Comercio arts 203-217. Map in-range articles to CCo."""
    outcome = mig.derive_norm_id(
        article_id="207",
        article_number="207",
        source_path="knowledge_base/CORE ya Arriba/Documents to branch and improve/Revisoria_Fiscal/Normativa_Base/rev_normativa_revisoria_fiscal.md",
    )
    assert outcome.norm_id == "cco.art.207"
    assert outcome.rule_name == "revisoria_fiscal_cco"


def test_revisoria_fiscal_out_of_range_article_stays_other(mig):
    """Article numbers outside the CCo Revisoría Fiscal range (203-217) in
    that expert summary are parser artifacts — stay OTHER."""
    outcome = mig.derive_norm_id(
        article_id="500",
        article_number="500",
        source_path="knowledge_base/CORE ya Arriba/Documents to branch and improve/Revisoria_Fiscal/Normativa_Base/rev_normativa_revisoria_fiscal.md",
    )
    assert outcome.rule_name == "OTHER"
    assert outcome.norm_id is None
