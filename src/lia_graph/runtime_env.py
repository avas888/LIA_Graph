from __future__ import annotations

import os

_PRODUCTION_LIKE_ENVS = frozenset({"production", "staging"})
_ENV_KEYS = (
    "LIA_ENV",
    "RAILWAY_ENVIRONMENT_NAME",
    "RAILWAY_ENVIRONMENT",
    "APP_ENV",
    "ENVIRONMENT",
)


def _normalize_runtime_env(value: str) -> str:
    clean = str(value or "").strip().lower()
    if not clean:
        return ""
    if clean in {"prod", "production", "live"} or clean.startswith("prod"):
        return "production"
    if clean in {"stage", "staging", "preview", "preprod", "pre-production"}:
        return "staging"
    if clean in {"dev", "development", "local"}:
        return "dev"
    if clean in {"test", "testing"}:
        return "test"
    return clean


def runtime_environment_name() -> str:
    for key in _ENV_KEYS:
        resolved = _normalize_runtime_env(os.getenv(key, ""))
        if resolved:
            return resolved
    if str(os.getenv("RAILWAY_PUBLIC_DOMAIN", "") or "").strip():
        return "production"
    return "dev"


def is_production_like_env() -> bool:
    return runtime_environment_name() in _PRODUCTION_LIKE_ENVS
