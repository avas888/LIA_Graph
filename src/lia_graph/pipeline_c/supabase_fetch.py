from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class SupabaseRetriever:
    client: Any | None = None

    def retrieve(self, *args: object, **kwargs: object) -> list[dict[str, Any]]:
        return []


def _resolve_sync_generation(*args: object, **kwargs: object) -> str | None:
    return None

