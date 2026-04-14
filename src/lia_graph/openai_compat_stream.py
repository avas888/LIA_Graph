"""Helpers for OpenAI-compatible SSE chat streams."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any


def iter_openai_compatible_stream_events(response: Any) -> Iterator[dict[str, Any]]:
    for raw_line in response:
        line = raw_line.decode("utf-8", errors="replace") if isinstance(raw_line, bytes) else str(raw_line)
        line = line.strip()
        if not line or not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if not payload or payload == "[DONE]":
            continue
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            yield data


def normalize_openai_stream_chunk_payload(chunk: dict[str, Any] | None) -> dict[str, Any]:
    payload = dict(chunk or {})
    text_parts: list[str] = []
    for choice in payload.get("choices") or []:
        if not isinstance(choice, dict):
            continue
        delta = choice.get("delta") or {}
        content = delta.get("content")
        if isinstance(content, str) and content:
            text_parts.append(content)
    return {
        "content": "".join(text_parts),
        "raw": payload,
        "usage": payload.get("usage") if isinstance(payload.get("usage"), dict) else None,
    }

