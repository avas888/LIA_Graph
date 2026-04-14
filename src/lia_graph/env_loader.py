from __future__ import annotations

import os
from pathlib import Path

_STAGING_WIP_PREFIX = "SUPABASE_WIP_"


def _parse_env_line(line: str) -> tuple[str, str] | None:
    raw = line.strip()
    if not raw or raw.startswith("#"):
        return None
    if "=" not in raw:
        return None

    key, value = raw.split("=", 1)
    key = key.strip()
    if not key:
        return None

    value = value.strip()
    if value and value[0] == value[-1] and value[0] in {'"', "'"}:
        value = value[1:-1]
    return key, value


def _candidate_env_files(explicit_path: Path | None = None) -> list[Path]:
    candidates: list[Path] = []
    cwd = Path.cwd()
    candidates.append(cwd / ".env")
    candidates.append(cwd / ".env.local")

    # LIA_ENV-based file: .env.staging, .env.production, etc.
    lia_env = os.getenv("LIA_ENV", "").strip().lower()
    if lia_env and lia_env != "dev":
        candidates.append(cwd / f".env.{lia_env}")

    env_path = os.getenv("LIA_DOTENV_PATH", "").strip()
    if env_path:
        candidates.append(Path(env_path))
    if explicit_path is not None:
        candidates.append(explicit_path)

    unique: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = str(path.resolve()) if path.exists() else str(path)
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return unique


def _parse_env_file(path: Path) -> dict[str, str]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    parsed: dict[str, str] = {}
    for line in text.splitlines():
        item = _parse_env_line(line)
        if item is None:
            continue
        key, value = item
        parsed[key] = value
    return parsed


def _staging_defined_wip_keys(*, cwd: Path) -> set[str]:
    staging_path = cwd / ".env.staging"
    if not staging_path.exists() or not staging_path.is_file():
        return set()
    return {
        key
        for key in _parse_env_file(staging_path)
        if str(key or "").strip().startswith(_STAGING_WIP_PREFIX)
    }


def load_dotenv_if_present(explicit_path: Path | None = None) -> dict[str, str]:
    disable = os.getenv("LIA_DISABLE_DOTENV", "").strip().lower()
    if disable in {"1", "true", "yes"}:
        return {}

    protected_keys = set(os.environ.keys())
    cwd = Path.cwd()
    loaded: dict[str, str] = {}
    file_loaded_keys: set[str] = set()
    for path in _candidate_env_files(explicit_path=explicit_path):
        if not path.exists() or not path.is_file():
            continue
        for key, value in _parse_env_file(path).items():
            if key in protected_keys:
                continue
            os.environ[key] = value
            loaded[key] = value
            file_loaded_keys.add(key)

    lia_env = os.getenv("LIA_ENV", "").strip().lower()
    if lia_env == "staging":
        allowed_wip_keys = _staging_defined_wip_keys(cwd=cwd)
        for key in list(file_loaded_keys):
            if not key.startswith(_STAGING_WIP_PREFIX):
                continue
            if key in allowed_wip_keys or key in protected_keys:
                continue
            os.environ.pop(key, None)
            loaded.pop(key, None)
    return loaded
