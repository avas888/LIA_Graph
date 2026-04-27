"""Sanity checks on the v3 migration files — sub-fix 1B-γ §0.3.4.

H0 tests: parse the SQL text and confirm the structural invariants hold.
Full migration apply tests live in `tests/integration/` and require a
running Postgres (gated on LIA_INTEGRATION=1).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "supabase" / "migrations"


def _read(name: str) -> str:
    return (MIGRATIONS_DIR / name).read_text(encoding="utf-8")


def test_norms_catalog_migration_present():
    sql = _read("20260501000000_norms_catalog.sql")
    assert "CREATE TABLE IF NOT EXISTS public.norms" in sql
    assert "PRIMARY KEY" in sql
    assert "is_sub_unit" in sql
    assert "sub_unit_kind" in sql
    assert "norms_sub_unit_consistency" in sql
    assert "REFERENCES public.norms" in sql  # parent_norm_id FK


def test_norm_vigencia_history_migration_append_only():
    sql = _read("20260501000001_norm_vigencia_history.sql")
    assert "norm_vigencia_history" in sql
    assert "REVOKE UPDATE, DELETE ON public.norm_vigencia_history" in sql
    assert "GRANT  INSERT, SELECT ON public.norm_vigencia_history" in sql
    # 11-state CHECK constraint
    for state in ("V", "VM", "DE", "DT", "SP", "IE", "EC", "VC", "VL", "DI", "RV"):
        assert f"'{state}'" in sql
    # Forbidden writers block
    assert "synthesis@v1" not in sql or "synthesis@v1" in sql.split("CHECK")[0]
    # extracted_by enum allows the sanctioned writers
    assert "'cron@v1'" in sql
    assert "'ingest@v1'" in sql
    assert "'manual_sme:" in sql
    assert "'v2_to_v3_upgrade'" in sql


def test_norm_vigencia_history_state_until_check():
    sql = _read("20260501000001_norm_vigencia_history.sql")
    # state_until >= state_from constraint must be present
    assert re.search(r"state_until\s*>=\s*state_from", sql)


def test_norm_citations_migration_has_role_and_anchor_strength():
    sql = _read("20260501000002_norm_citations.sql")
    for role in ("anchor", "reference", "comparator", "historical"):
        assert f"'{role}'" in sql
    for strength in ("ley", "decreto", "res_dian", "concepto_dian", "jurisprudencia"):
        assert f"'{strength}'" in sql


def test_resolver_functions_migration_drops_first():
    sql = _read("20260501000003_resolver_functions.sql")
    # explicit DROP FUNCTION IF EXISTS per hybrid_search-overload-2026-04-27 learning
    assert "DROP FUNCTION IF EXISTS public.norm_vigencia_at_date" in sql
    assert "DROP FUNCTION IF EXISTS public.norm_vigencia_for_period" in sql
    # Both functions defined
    assert "CREATE FUNCTION public.norm_vigencia_at_date(as_of_date date)" in sql
    assert "CREATE FUNCTION public.norm_vigencia_for_period" in sql
    # Demotion factors map every state
    for state in ("V", "VM", "DE", "DT", "SP", "IE", "EC", "VC", "VL", "DI", "RV"):
        assert f"WHEN '{state}'" in sql


def test_resolver_for_period_honors_applies_to_kind():
    sql = _read("20260501000003_resolver_functions.sql")
    assert "applies_to_kind = 'always'" in sql
    assert "applies_to_kind = 'per_year'" in sql
    assert "applies_to_kind = 'per_period'" in sql


def test_resolver_for_period_filters_by_impuesto():
    sql = _read("20260501000003_resolver_functions.sql")
    assert "applies_to_payload->>'impuesto' = impuesto" in sql


def test_migration_filenames_form_a_chain():
    """Migrations 000000–000003 land in lexicographic order (a `db push` invariant)."""

    expected = [
        "20260501000000_norms_catalog.sql",
        "20260501000001_norm_vigencia_history.sql",
        "20260501000002_norm_citations.sql",
        "20260501000003_resolver_functions.sql",
    ]
    for name in expected:
        assert (MIGRATIONS_DIR / name).is_file(), f"Missing migration: {name}"
