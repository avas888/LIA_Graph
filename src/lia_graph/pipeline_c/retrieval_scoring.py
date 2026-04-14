from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_index(index_file: str | Path) -> list[dict[str, Any]]:
    path = Path(index_file)
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows

