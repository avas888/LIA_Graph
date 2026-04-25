"""Pin the taxonomy v2 contract.

next_v3.md §2 success criterion: ``config/topic_taxonomy.json`` parses, every
SME-promised topic has a row, renames preserve legacy keys, deprecated topics
carry ``merged_into``, and the 6 mutex rules are greppable.

The intent is to fail loudly if a future PR removes or renames a SME-required
field without updating this gate.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[1]
TAXONOMY_PATH = REPO / "config" / "topic_taxonomy.json"


@pytest.fixture(scope="module")
def taxonomy() -> dict:
    return json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def by_key(taxonomy: dict) -> dict[str, dict]:
    return {t["key"]: t for t in taxonomy["topics"]}


def test_schema_version_is_v2(taxonomy: dict) -> None:
    assert taxonomy.get("schema_version") == 2
    assert str(taxonomy.get("version", "")).startswith("v2026_04_25_v2_taxonomy")


# ---------------------------------------------------------------------------
# SME §1.1 + §1.2 + §1.4 + §7 — the 11 new top-level topics.
# ---------------------------------------------------------------------------

NEW_TOP_LEVELS = (
    "impuesto_timbre",
    "rut_y_responsabilidades_tributarias",
    "parafiscales_seguridad_social",
    "reforma_laboral_ley_2466",
    "proteccion_datos_personales",
    "niif_pymes",
    "niif_plenas",
    "niif_microempresas",
    "regimen_cambiario",
    "dividendos_y_distribucion_utilidades",
    "regimen_tributario_especial_esal",
)


@pytest.mark.parametrize("key", NEW_TOP_LEVELS)
def test_new_top_level_present(by_key: dict[str, dict], key: str) -> None:
    assert key in by_key, f"SME-promised new top-level missing: {key}"
    entry = by_key[key]
    assert "parent_key" not in entry or entry["parent_key"] in (None, "")
    assert entry.get("status", "active") == "active"


@pytest.mark.parametrize("key", NEW_TOP_LEVELS)
def test_new_top_level_has_required_sme_fields(by_key: dict[str, dict], key: str) -> None:
    entry = by_key[key]
    assert entry.get("definition"), f"{key} missing definition"
    assert entry.get("scope_in"), f"{key} missing scope_in"
    assert entry.get("scope_out"), f"{key} missing scope_out"
    assert entry.get("keyword_anchors"), f"{key} missing keyword_anchors"
    # ET-centric topics carry allowed_et_articles; non-ET carry allowed_norm_anchors.
    has_et = bool(entry.get("allowed_et_articles"))
    has_norm = bool(entry.get("allowed_norm_anchors"))
    assert has_et or has_norm, (
        f"{key}: must have either allowed_et_articles or allowed_norm_anchors"
    )


# ---------------------------------------------------------------------------
# Renames — every rename-target carries the old key in legacy_document_topics.
# ---------------------------------------------------------------------------

RENAMES = {
    "cambiario": "regimen_cambiario",
    "dividendos_utilidades": "dividendos_y_distribucion_utilidades",
    "regimen_tributario_especial": "regimen_tributario_especial_esal",
    "tarifas_tasa_minima_renta": "tarifas_renta_y_ttd",
    "anticipos_retenciones_a_favor": "retencion_fuente_general",
}


@pytest.mark.parametrize("old_key,new_key", list(RENAMES.items()))
def test_rename_preserves_legacy(
    by_key: dict[str, dict], old_key: str, new_key: str
) -> None:
    assert old_key not in by_key, f"Old key {old_key} must be removed"
    assert new_key in by_key, f"Rename target {new_key} must exist"
    entry = by_key[new_key]
    assert old_key in entry.get("legacy_document_topics", []), (
        f"{new_key} must list {old_key} in legacy_document_topics"
    )
    assert entry.get("renamed_from") == old_key


# ---------------------------------------------------------------------------
# Deprecation: estados_financieros_niif → niif_pymes / niif_plenas / niif_microempresas.
# ---------------------------------------------------------------------------

def test_estados_financieros_niif_deprecated(by_key: dict[str, dict]) -> None:
    entry = by_key.get("estados_financieros_niif")
    assert entry is not None, "deprecated entry must still be listed (with status=deprecated)"
    assert entry.get("status") == "deprecated"
    assert set(entry.get("merged_into", [])) == {
        "niif_pymes",
        "niif_plenas",
        "niif_microempresas",
    }
    # Aliases must be cleared so successors don't collide.
    assert entry.get("aliases") == []
    assert entry.get("ingestion_aliases") == []


def test_niif_pymes_inherits_legacy_aliases(by_key: dict[str, dict]) -> None:
    entry = by_key["niif_pymes"]
    legacy = set(entry["legacy_document_topics"])
    # niif_pymes is the primary heir of estados_financieros_niif per SME.
    assert "estados_financieros_niif" in legacy
    assert "niif" in legacy


# ---------------------------------------------------------------------------
# Parent-key moves: firmeza, devoluciones, sancionatorio -> procedimiento_tributario.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "key",
    ["firmeza_declaraciones", "devoluciones_saldos_a_favor", "regimen_sancionatorio_extemporaneidad"],
)
def test_moved_to_procedimiento_tributario(by_key: dict[str, dict], key: str) -> None:
    assert by_key[key].get("parent_key") == "procedimiento_tributario"


# ---------------------------------------------------------------------------
# Promotions to top-level.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "key",
    ["ganancia_ocasional", "conciliacion_fiscal", "beneficio_auditoria", "retencion_fuente_general"],
)
def test_promoted_to_top_level(by_key: dict[str, dict], key: str) -> None:
    entry = by_key[key]
    assert "parent_key" not in entry or entry["parent_key"] in (None, "")


# ---------------------------------------------------------------------------
# New subtopics.
# ---------------------------------------------------------------------------

def test_renta_presuntiva_is_under_declaracion_renta(by_key: dict[str, dict]) -> None:
    entry = by_key["renta_presuntiva"]
    assert entry["parent_key"] == "declaracion_renta"


def test_zomac_zese_is_under_inversiones_incentivos(by_key: dict[str, dict]) -> None:
    entry = by_key["zomac_zese_incentivos_geograficos"]
    assert entry["parent_key"] == "inversiones_incentivos"


# ---------------------------------------------------------------------------
# Mutex rules — the 6 SME rules are greppable on the root payload.
# ---------------------------------------------------------------------------

EXPECTED_MUTEX_NAMES = {
    "iva_vs_procedimiento_tributario",
    "iva_vs_familia_renta",
    "comercial_societario_fusion",
    "facturacion_electronica_vs_impuesto_timbre",
    "rub_vs_rut",
    "laboral_family",
}


def test_mutex_rules_count_and_coverage(taxonomy: dict) -> None:
    rules = taxonomy.get("mutex_rules", [])
    assert len(rules) == 6
    names = {r.get("name") for r in rules}
    assert names == EXPECTED_MUTEX_NAMES


# ---------------------------------------------------------------------------
# Magnet redefinitions: iva / procedimiento_tributario / comercial_societario /
# facturacion_electronica / beneficiario_final_rub / laboral all have
# definition + scope_in + scope_out per SME §2.3.
# ---------------------------------------------------------------------------

MAGNETS = (
    "iva",
    "procedimiento_tributario",
    "comercial_societario",
    "facturacion_electronica",
    "beneficiario_final_rub",
    "laboral",
)


@pytest.mark.parametrize("key", MAGNETS)
def test_magnet_has_redefinition(by_key: dict[str, dict], key: str) -> None:
    entry = by_key[key]
    assert entry.get("definition"), f"magnet {key} missing SME definition"
    assert entry.get("scope_in"), f"magnet {key} missing scope_in"
    assert entry.get("scope_out"), f"magnet {key} missing scope_out"
    assert entry.get("keyword_anchors"), f"magnet {key} missing keyword_anchors"


# ---------------------------------------------------------------------------
# Non-ET topics carry allowed_norm_anchors (SME §4.1).
# ---------------------------------------------------------------------------

NON_ET_TOPICS = (
    "laboral",
    "parafiscales_seguridad_social",
    "reforma_laboral_ley_2466",
    "proteccion_datos_personales",
    "regimen_cambiario",
    "niif_pymes",
    "niif_plenas",
    "niif_microempresas",
    "comercial_societario",
)


@pytest.mark.parametrize("key", NON_ET_TOPICS)
def test_non_et_topic_has_norm_anchors(by_key: dict[str, dict], key: str) -> None:
    entry = by_key[key]
    assert entry.get("allowed_norm_anchors"), (
        f"{key}: non-ET topic must declare allowed_norm_anchors per SME §4.1"
    )


# ---------------------------------------------------------------------------
# No duplicate keys, no alias collisions (defense-in-depth — loader already checks).
# ---------------------------------------------------------------------------

def test_no_duplicate_keys(taxonomy: dict) -> None:
    keys = [t["key"] for t in taxonomy["topics"]]
    assert len(keys) == len(set(keys))


def test_no_cross_entry_alias_collision(taxonomy: dict) -> None:
    owner: dict[str, str] = {}
    for t in taxonomy["topics"]:
        for alias in [t["key"], *t.get("aliases", [])]:
            a = alias.strip().lower()
            if not a:
                continue
            prior = owner.get(a)
            if prior and prior != t["key"]:
                raise AssertionError(f"alias {a!r} shared by {prior} and {t['key']}")
            owner[a] = t["key"]
