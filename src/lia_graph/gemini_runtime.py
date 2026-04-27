"""Minimal Gemini adapters used by the shared LLM runtime.

Retry policy
------------
Gemini's `gemini-2.5-pro` periodically returns HTTP 503 ("model currently
overloaded"); 429 ("Too Many Requests") happens under bursty concurrent
load. Without retry, every transient surge becomes an `adapter_error`
refusal that wastes the per-norm budget.

We retry on:
  * 503 (overloaded) — most common
  * 429 (rate-limited) — when concurrent harnesses pile in
  * 500 / 502 / 504 — transient backend issues
  * URLError / TimeoutError — network blips

Back-off shape: 0 / 4 / 12 / 30 seconds (4 attempts total). The longer
last sleep is intentional — Gemini's overloaded periods can run 30+
seconds; shorter waits just burn the same call again into the same
queue.

4xx other than 429 is terminal (auth, bad request) — no retry.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from typing import Any

from .openai_compat_stream import iter_openai_compatible_stream_events

LOGGER = logging.getLogger(__name__)

DEFAULT_GEMINI_NATIVE_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_GEMINI_OPENAI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"

_RETRY_HTTP_STATUSES = {429, 500, 502, 503, 504}
_RETRY_BACKOFF_SECONDS = (0, 4, 12, 30)  # 4 attempts: immediate / +4s / +12s / +30s


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
        last_err: Exception | None = None
        for attempt, backoff in enumerate(_RETRY_BACKOFF_SECONDS):
            if backoff:
                LOGGER.info(
                    "Gemini retry %d/%d: sleeping %ds (last err: %s)",
                    attempt, len(_RETRY_BACKOFF_SECONDS) - 1, backoff,
                    last_err,
                )
                time.sleep(backoff)
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
                if exc.code in _RETRY_HTTP_STATUSES and attempt < len(_RETRY_BACKOFF_SECONDS) - 1:
                    last_err = RuntimeError(f"Gemini HTTP {exc.code}: {detail[:200]}")
                    continue
                raise RuntimeError(f"Gemini HTTP {exc.code}: {detail}") from exc
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                if attempt < len(_RETRY_BACKOFF_SECONDS) - 1:
                    last_err = exc
                    continue
                raise RuntimeError(f"Gemini network error: {exc}") from exc
        # Unreachable in practice — loop always returns or raises.
        raise last_err if last_err else RuntimeError("Gemini request exhausted retries")

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

