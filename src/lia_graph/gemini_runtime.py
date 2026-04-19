"""Minimal Gemini adapters used by the shared LLM runtime."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Iterator
from typing import Any

from .openai_compat_stream import iter_openai_compatible_stream_events

DEFAULT_GEMINI_NATIVE_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_GEMINI_OPENAI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"


class GeminiChatAdapter:
    def __init__(
        self,
        *,
        model: str,
        api_key: str,
        base_url: str = DEFAULT_GEMINI_OPENAI_BASE_URL,
        timeout_seconds: float = 30.0,
        temperature: float = 0.1,
        max_tokens: int | None = None,
        thinking_enabled: bool | None = None,
    ) -> None:
        self.model = model
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.thinking_enabled = thinking_enabled

    def _request(self, payload: dict[str, Any]) -> dict[str, Any]:
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
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace") if exc.fp else str(exc)
            raise RuntimeError(f"Gemini HTTP {exc.code}: {detail}") from exc

    def generate(self, prompt: str) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
        }
        if self.max_tokens is not None:
            payload["max_tokens"] = self.max_tokens
        if self.thinking_enabled is False:
            payload["reasoning_effort"] = "none"
        data = self._request(payload)
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError("Gemini response missing choices.")
        content = ((choices[0].get("message") or {}).get("content") or "").strip()
        if not content:
            raise RuntimeError("Gemini response missing content.")
        return content

    def stream(self, prompt: str) -> Iterator[dict[str, Any]]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "stream": True,
        }
        if self.max_tokens is not None:
            payload["max_tokens"] = self.max_tokens
        if self.thinking_enabled is False:
            payload["reasoning_effort"] = "none"
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
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:
                yield from iter_openai_compatible_stream_events(response)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace") if exc.fp else str(exc)
            raise RuntimeError(f"Gemini HTTP {exc.code}: {detail}") from exc


class GeminiNativeChatAdapter(GeminiChatAdapter):
    def __init__(
        self,
        *,
        model: str,
        api_key: str,
        base_url: str = DEFAULT_GEMINI_NATIVE_BASE_URL,
        timeout_seconds: float = 30.0,
        temperature: float = 0.1,
        max_tokens: int | None = None,
        thinking_enabled: bool | None = None,
    ) -> None:
        super().__init__(
            model=model,
            api_key=api_key,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            temperature=temperature,
            max_tokens=max_tokens,
            thinking_enabled=thinking_enabled,
        )

