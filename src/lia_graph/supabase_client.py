"""Supabase client singleton and strict runtime helpers.

LIA_STORAGE_BACKEND=supabase | filesystem
"""

from __future__ import annotations

import atexit
import os
from pathlib import Path
import threading
from typing import Any

from .env_loader import load_dotenv_if_present
from .runtime_env import is_production_like_env, runtime_environment_name

_client_local = threading.local()
_backend: str | None = None
_dotenv_loaded = False


def _ensure_dotenv_loaded() -> None:
    global _dotenv_loaded
    if _dotenv_loaded:
        return
    load_dotenv_if_present()
    _dotenv_loaded = True


def get_storage_backend() -> str:
    global _backend
    if _backend is None:
        _ensure_dotenv_loaded()
        _backend = os.getenv("LIA_STORAGE_BACKEND", "supabase").strip().lower() or "supabase"
    return _backend


def reset_backend_cache() -> None:
    """For testing: reset cached backend value."""
    global _backend, _client_local, _dotenv_loaded
    _backend = None
    _client_local = threading.local()
    _dotenv_loaded = False


def require_supabase_backend() -> None:
    backend = get_storage_backend()
    if backend != "supabase":
        raise RuntimeError(
            "LIA_STORAGE_BACKEND debe ser 'supabase' para operar en modo estricto."
        )


_SUPABASE_TIMEOUT_SECONDS = 20


def _create_supabase_client(url: str, key: str) -> Any:
    try:
        from supabase import ClientOptions, create_client
    except ImportError as exc:
        raise RuntimeError(
            "supabase package not installed. Run: uv sync --extra dev"
        ) from exc
    try:
        import httpx
        http_client = httpx.Client(timeout=httpx.Timeout(_SUPABASE_TIMEOUT_SECONDS))
        options = ClientOptions(httpx_client=http_client)
    except Exception:
        options = ClientOptions(postgrest_client_timeout=_SUPABASE_TIMEOUT_SECONDS)
    return create_client(url, key, options=options)


_TARGET_ALIASES: dict[str, str] = {"mother": "production", "child": "wip"}


def _lia_env() -> str:
    _ensure_dotenv_loaded()
    return runtime_environment_name()


def _resolve_service_role_key(*, service_key_var: str) -> str:
    key = str(os.getenv(service_key_var, "") or "").strip()
    if not key:
        raise RuntimeError(f"{service_key_var} required for secure Supabase access.")
    return key


def resolve_supabase_target(target: str | None) -> str:
    clean = str(target or "").strip().lower() or "production"
    clean = _TARGET_ALIASES.get(clean, clean)
    if clean not in {"production", "wip", "both"}:
        raise RuntimeError("Supabase target invalido. Usa production, wip o both.")
    return clean


def get_supabase_target_config(target: str) -> dict[str, str]:
    resolved = resolve_supabase_target(target)
    if resolved == "both":
        raise RuntimeError("`both` no es un target de cliente individual.")

    _ensure_dotenv_loaded()
    if resolved == "production":
        url_var = "SUPABASE_URL"
        service_key_var = "SUPABASE_SERVICE_ROLE_KEY"
    else:
        url_var = "SUPABASE_WIP_URL"
        service_key_var = "SUPABASE_WIP_SERVICE_ROLE_KEY"

    url = str(os.getenv(url_var, "")).strip()
    if not url:
        raise RuntimeError(f"{url_var} required for supabase target '{resolved}'.")
    key = _resolve_service_role_key(service_key_var=service_key_var)
    return {
        "target": resolved,
        "url": url,
        "key": key,
    }


def create_supabase_client_for_target(target: str) -> Any:
    config = get_supabase_target_config(target)
    return _create_supabase_client(config["url"], config["key"])


def get_supabase_client() -> Any:
    """Lazy per-thread Supabase client (REST, supabase-py)."""
    client = getattr(_client_local, "client", None)
    if client is not None:
        return client
    _ensure_dotenv_loaded()
    require_supabase_backend()
    url = str(os.getenv("SUPABASE_URL", "")).strip()
    if not url:
        raise RuntimeError(
            "SUPABASE_URL required for supabase mode. No localhost default is used."
        )
    service_role_key = str(os.getenv("SUPABASE_SERVICE_ROLE_KEY", "") or "").strip()
    anon_key = str(os.getenv("SUPABASE_ANON_KEY", "") or "").strip()
    if is_production_like_env() and not service_role_key:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY required in staging/production.")
    key = service_role_key or anon_key
    if not key:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY required")
    client = _create_supabase_client(url, key)
    _client_local.client = client
    return client


def is_supabase_enabled() -> bool:
    try:
        require_supabase_backend()
    except RuntimeError:
        return False
    return True


def matches_default_storage_path(path: Path, default_path: Path) -> bool:
    current = Path(path).expanduser()
    default = Path(default_path).expanduser()
    if not default.is_absolute():
        default = Path(__file__).resolve().parents[2] / default
    try:
        return current.resolve() == default.resolve()
    except OSError:
        return current == default


def get_supabase_generation_status(
    *,
    generation_id: str,
    expected_documents: int | None = None,
    expected_chunks: int | None = None,
) -> dict[str, Any]:
    generation = str(generation_id or "").strip()
    if not generation:
        raise RuntimeError("generation_id es obligatorio para verificar Supabase.")

    client = get_supabase_client()

    doc_q = (
        client.table("documents")
        .select("doc_id", count="exact")
        .eq("sync_generation", generation)
        .limit(0)
        .execute()
    )
    chunk_q = (
        client.table("document_chunks")
        .select("chunk_id", count="exact")
        .eq("sync_generation", generation)
        .limit(0)
        .execute()
    )

    documents = int(doc_q.count or 0)
    chunks = int(chunk_q.count or 0)
    expected_docs_value = int(expected_documents or 0)
    expected_chunks_value = int(expected_chunks or 0)
    ready = (
        documents > 0
        and chunks > 0
        and documents >= expected_docs_value
        and chunks >= expected_chunks_value
    )
    return {
        "generation_id": generation,
        "documents": documents,
        "chunks": chunks,
        "expected_documents": expected_docs_value,
        "expected_chunks": expected_chunks_value,
        "ready": ready,
    }


def _cleanup() -> None:
    global _client_local, _backend, _dotenv_loaded
    _client_local = threading.local()
    _backend = None
    _dotenv_loaded = False


atexit.register(_cleanup)
