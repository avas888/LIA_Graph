from __future__ import annotations

from pathlib import Path


def test_seed_migrations_cover_admin_and_users_1_to_10() -> None:
    root = Path(__file__).resolve().parents[1]
    files = [
        root / "supabase" / "migrations" / "20260325000002_seed_platform_users.sql",
        root / "supabase" / "migrations" / "20260405000002_seed_test_users_shared_password.sql",
        root / "supabase" / "migrations" / "20260408000002_seed_users_4_to_10.sql",
    ]

    combined = "\n".join(path.read_text(encoding="utf-8") for path in files)

    assert "admin@lia.dev" in combined
    for number in range(1, 11):
        assert f"usuario{number}@lia.dev" in combined


def test_seed_migrations_keep_admin_as_platform_admin() -> None:
    root = Path(__file__).resolve().parents[1]
    seed_sql = (
        root
        / "supabase"
        / "migrations"
        / "20260325000002_seed_platform_users.sql"
    ).read_text(encoding="utf-8")

    assert "'usr_admin_001', 'admin@lia.dev'" in seed_sql
    assert "('tenant-dev',   'usr_admin_001', 'platform_admin')" in seed_sql
