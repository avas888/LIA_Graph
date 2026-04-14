from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .adapters import LLMAdapter
from .env_loader import load_dotenv_if_present
from .gemini_runtime import (
    DEFAULT_GEMINI_NATIVE_BASE_URL,
    DEFAULT_GEMINI_OPENAI_BASE_URL,
    GeminiChatAdapter,
    GeminiNativeChatAdapter,
)
from .instrumentation import emit_event
from .openai_compat_stream import (
    iter_openai_compatible_stream_events,
    normalize_openai_stream_chunk_payload,
)

_RUNTIME_CONFIG_ENV = "LIA_LLM_RUNTIME_CONFIG_PATH"


def _default_runtime_config_path() -> Path:
    raw = str(os.getenv(_RUNTIME_CONFIG_ENV) or "").strip()
    return Path(raw) if raw else Path("config/llm_runtime.json")


DEFAULT_RUNTIME_CONFIG_PATH = _default_runtime_config_path()


class LLMRuntimeConfigInvalidError(ValueError):
    """Configuracion runtime de LLM invalida o corrupta."""


@dataclass(frozen=True)
class LLMProviderConfig:
    provider_id: str
    provider_type: str
    enabled: bool
    model: str
    transport: str | None = None
    api_key_env: str | None = None
    base_url: str | None = None
    region: str | None = None
    timeout_seconds: float = 30.0
    temperature: float = 0.1
    max_tokens: int | None = None


@dataclass(frozen=True)
class LLMRuntimeConfig:
    strategy: str
    provider_order: tuple[str, ...]
    providers: tuple[LLMProviderConfig, ...]


class DeepSeekChatAdapter:
    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        timeout_seconds: float = 30.0,
        temperature: float = 0.1,
        max_tokens: int | None = None,
    ) -> None:
        self.model = model
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature
        self.max_tokens = max_tokens

    def _generate_raw(
        self,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout_seconds: float | None = None,
        extra_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "model": model or self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature if temperature is None else temperature,
        }
        resolved_max_tokens = self.max_tokens if max_tokens is None else max_tokens
        if resolved_max_tokens is not None:
            payload["max_tokens"] = resolved_max_tokens
        if extra_payload:
            payload.update(extra_payload)
        req = urllib.request.Request(
            url=f"{self.base_url}/chat/completions",
            method="POST",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout_seconds or self.timeout_seconds) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace") if exc.fp else str(exc)
            raise RuntimeError(f"DeepSeek HTTP {exc.code}: {detail}") from exc
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(f"DeepSeek request failed: {exc}") from exc

        return data

    def _stream_raw(
        self,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout_seconds: float | None = None,
        extra_payload: dict[str, Any] | None = None,
    ) -> Iterator[dict[str, Any]]:
        payload = {
            "model": model or self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature if temperature is None else temperature,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        resolved_max_tokens = self.max_tokens if max_tokens is None else max_tokens
        if resolved_max_tokens is not None:
            payload["max_tokens"] = resolved_max_tokens
        if extra_payload:
            payload.update(extra_payload)
        req = urllib.request.Request(
            url=f"{self.base_url}/chat/completions",
            method="POST",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout_seconds or self.timeout_seconds) as response:
                for event in iter_openai_compatible_stream_events(response):
                    yield event
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace") if exc.fp else str(exc)
            raise RuntimeError(f"DeepSeek HTTP {exc.code}: {detail}") from exc
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(f"DeepSeek request failed: {exc}") from exc

    def generate(self, prompt: str) -> str:
        data = self._generate_raw(prompt)
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise RuntimeError("DeepSeek response missing `choices`.")
        message = choices[0].get("message", {})
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("DeepSeek response missing message content.")
        return content.strip()

    def generate_with_options(
        self,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout_seconds: float | None = None,
        extra_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        data = self._generate_raw(
            prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout_seconds=timeout_seconds,
            extra_payload=extra_payload,
        )
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise RuntimeError("DeepSeek response missing `choices`.")
        choice = choices[0]
        message = choice.get("message", {})
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("DeepSeek response missing message content.")
        reasoning_content = message.get("reasoning_content")
        if isinstance(reasoning_content, str):
            reasoning_content = reasoning_content.strip()
        else:
            reasoning_content = None
        finish_reason = str(choice.get("finish_reason") or "").strip() or None
        usage = data.get("usage")
        if not isinstance(usage, dict):
            usage = None
        return {
            "content": content.strip(),
            "reasoning_content": reasoning_content,
            "finish_reason": finish_reason,
            "usage": usage,
        }

    def stream_with_options(
        self,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout_seconds: float | None = None,
        extra_payload: dict[str, Any] | None = None,
    ) -> Iterator[dict[str, Any]]:
        for payload in self._stream_raw(
            prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout_seconds=timeout_seconds,
            extra_payload=extra_payload,
        ):
            yield normalize_openai_stream_chunk_payload(payload)


def _parse_runtime_payload(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise LLMRuntimeConfigInvalidError(f"No se pudo leer runtime LLM: {exc}") from exc
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LLMRuntimeConfigInvalidError(f"JSON invalido en runtime LLM: {exc}") from exc
    if not isinstance(payload, dict):
        raise LLMRuntimeConfigInvalidError("El runtime LLM debe ser un objeto JSON.")
    return payload


def _coerce_float(name: str, value: Any, *, default: float) -> float:
    if value is None:
        return default
    if isinstance(value, bool):
        raise LLMRuntimeConfigInvalidError(f"`{name}` debe ser numerico, no booleano.")
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip())
    except ValueError as exc:
        raise LLMRuntimeConfigInvalidError(f"`{name}` debe ser numerico.") from exc


def _coerce_int(name: str, value: Any, *, default: int) -> int:
    if value is None:
        return default
    if isinstance(value, bool):
        raise LLMRuntimeConfigInvalidError(f"`{name}` debe ser entero, no booleano.")
    if isinstance(value, int):
        return value
    if isinstance(value, float) and float(value).is_integer():
        return int(value)
    try:
        return int(str(value).strip())
    except ValueError as exc:
        raise LLMRuntimeConfigInvalidError(f"`{name}` debe ser entero.") from exc


def _coerce_optional_int(name: str, value: Any, *, default: int | None = None) -> int | None:
    if value is None:
        return default
    return max(1, _coerce_int(name, value, default=1))


def load_llm_runtime_config(path: Path = DEFAULT_RUNTIME_CONFIG_PATH) -> LLMRuntimeConfig:
    payload = _parse_runtime_payload(path)
    if payload is None:
        return LLMRuntimeConfig(strategy="ordered_fallback", provider_order=(), providers=())

    strategy = str(payload.get("strategy", "ordered_fallback")).strip().lower() or "ordered_fallback"
    if strategy not in {"ordered_fallback", "single_provider"}:
        raise LLMRuntimeConfigInvalidError("`strategy` debe ser `ordered_fallback` o `single_provider`.")

    raw_providers = payload.get("providers", [])
    if not isinstance(raw_providers, list):
        raise LLMRuntimeConfigInvalidError("`providers` debe ser una lista.")
    providers: list[LLMProviderConfig] = []
    for idx, row in enumerate(raw_providers):
        if not isinstance(row, dict):
            raise LLMRuntimeConfigInvalidError(f"`providers[{idx}]` debe ser objeto.")
        provider_id = str(row.get("id", "")).strip()
        if not provider_id:
            continue
        providers.append(
            LLMProviderConfig(
                provider_id=provider_id,
                provider_type=str(row.get("type", "")).strip().lower() or "unknown",
                enabled=bool(row.get("enabled", True)),
                model=str(row.get("model", "")).strip() or "unknown",
                transport=str(row.get("transport", "")).strip().lower() or None,
                api_key_env=str(row.get("api_key_env")).strip() if row.get("api_key_env") else None,
                base_url=str(row.get("base_url")).strip() if row.get("base_url") else None,
                region=str(row.get("region")).strip() if row.get("region") else None,
                timeout_seconds=max(0.1, _coerce_float(f"providers[{idx}].timeout_seconds", row.get("timeout_seconds"), default=30.0)),
                temperature=_coerce_float(f"providers[{idx}].temperature", row.get("temperature"), default=0.1),
                max_tokens=_coerce_optional_int(f"providers[{idx}].max_tokens", row.get("max_tokens"), default=None),
            )
        )

    raw_provider_order = payload.get("provider_order", [])
    if raw_provider_order is None:
        raw_provider_order = []
    if not isinstance(raw_provider_order, list):
        raise LLMRuntimeConfigInvalidError("`provider_order` debe ser una lista.")
    provider_order = tuple(str(x).strip() for x in raw_provider_order if str(x).strip())
    if not provider_order:
        provider_order = tuple(p.provider_id for p in providers)

    return LLMRuntimeConfig(
        strategy=strategy,
        provider_order=provider_order,
        providers=tuple(providers),
    )


def _provider_lookup(cfg: LLMRuntimeConfig) -> dict[str, LLMProviderConfig]:
    return {provider.provider_id: provider for provider in cfg.providers}


def _resolve_provider_transport(provider: LLMProviderConfig) -> str:
    if provider.provider_type != "gemini":
        return str(provider.transport or "").strip().lower() or "standard"
    explicit_transport = str(provider.transport or "").strip().lower()
    if explicit_transport:
        return explicit_transport
    return "openai_compat"


def _instantiate_adapter(provider: LLMProviderConfig) -> tuple[LLMAdapter | None, str | None]:
    if provider.provider_type == "deepseek":
        if not provider.api_key_env:
            return None, "missing_api_key_env"
        api_key = os.getenv(provider.api_key_env, "").strip()
        if not api_key:
            return None, f"missing_env:{provider.api_key_env}"
        return (
            DeepSeekChatAdapter(
                model=provider.model,
                api_key=api_key,
                base_url=provider.base_url or "https://api.deepseek.com",
                timeout_seconds=provider.timeout_seconds,
                temperature=provider.temperature,
                max_tokens=provider.max_tokens,
            ),
            None,
        )

    if provider.provider_type == "gemini":
        if not provider.api_key_env:
            return None, "missing_api_key_env"
        api_key = os.getenv(provider.api_key_env, "").strip()
        if not api_key:
            return None, f"missing_env:{provider.api_key_env}"
        transport = _resolve_provider_transport(provider)
        if transport == "native":
            return (
                GeminiNativeChatAdapter(
                    model=provider.model,
                    api_key=api_key,
                    base_url=provider.base_url or DEFAULT_GEMINI_NATIVE_BASE_URL,
                    timeout_seconds=provider.timeout_seconds,
                    temperature=provider.temperature,
                    max_tokens=provider.max_tokens,
                ),
                None,
            )
        if transport != "openai_compat":
            return None, f"unknown_gemini_transport:{transport}"
        return (
            GeminiChatAdapter(
                model=provider.model,
                api_key=api_key,
                base_url=provider.base_url or DEFAULT_GEMINI_OPENAI_BASE_URL,
                timeout_seconds=provider.timeout_seconds,
                temperature=provider.temperature,
                max_tokens=provider.max_tokens,
            ),
            None,
        )

    return None, f"unknown_provider_type:{provider.provider_type}"


def resolve_llm_adapter(
    runtime_config_path: Path = DEFAULT_RUNTIME_CONFIG_PATH,
    requested_provider: str | None = None,
) -> tuple[LLMAdapter | None, dict[str, Any]]:
    dotenv_loaded = load_dotenv_if_present()
    cfg = load_llm_runtime_config(path=runtime_config_path)
    providers = _provider_lookup(cfg)

    order: list[str] = []
    if cfg.strategy == "single_provider":
        if requested_provider:
            order = [requested_provider]
        elif cfg.provider_order:
            order = [cfg.provider_order[0]]
    else:
        if requested_provider:
            order.append(requested_provider)
        order.extend([item for item in cfg.provider_order if item not in order])

    skipped: list[dict[str, str]] = []
    for provider_id in order:
        provider = providers.get(provider_id)
        if provider is None:
            skipped.append({"provider_id": provider_id, "reason": "not_found_in_config"})
            continue
        if not provider.enabled:
            skipped.append({"provider_id": provider.provider_id, "reason": "disabled"})
            continue

        adapter, reason = _instantiate_adapter(provider)
        if adapter is None:
            skipped.append({"provider_id": provider.provider_id, "reason": reason or "not_available"})
            continue

        emit_event(
            "llm.runtime.provider_selected",
            {
                "provider_id": provider.provider_id,
                "provider_type": provider.provider_type,
                "provider_transport": _resolve_provider_transport(provider),
                "model": provider.model,
                "runtime_config_path": str(runtime_config_path),
                "requested_provider": requested_provider,
            },
        )
        return adapter, {
            "selected_provider": provider.provider_id,
            "selected_type": provider.provider_type,
            "selected_transport": _resolve_provider_transport(provider),
            "model": provider.model,
            "adapter_class": adapter.__class__.__name__,
            "strategy": cfg.strategy,
            "resolution_mode": "deterministic",
            "fallback_skipped": skipped,
            "runtime_config_path": str(runtime_config_path),
            "dotenv_loaded_keys": sorted(dotenv_loaded.keys()),
        }

    emit_event(
        "llm.runtime.provider_unavailable",
        {
            "requested_provider": requested_provider,
            "runtime_config_path": str(runtime_config_path),
            "fallback_skipped": skipped,
        },
    )
    return None, {
        "selected_provider": None,
        "selected_type": None,
        "selected_transport": None,
        "model": None,
        "adapter_class": None,
        "strategy": cfg.strategy,
        "resolution_mode": "deterministic",
        "fallback_skipped": skipped,
        "runtime_config_path": str(runtime_config_path),
        "dotenv_loaded_keys": sorted(dotenv_loaded.keys()),
    }
