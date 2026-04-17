from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .normative_references import extract_normative_references


@dataclass(frozen=True)
class PracticalDocMetadata:
    mentioned_reference_keys: tuple[str, ...] = ()


def read_referenceable_text(path: Path, *, max_chars: int = 80_000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:max_chars]
    except OSError:
        return ""


def derive_practical_doc_metadata(
    *,
    doc: dict[str, Any] | None,
    body_text: str,
    manifest_normative_refs: Iterable[str] = (),
) -> PracticalDocMetadata:
    keys: list[str] = []
    for item in manifest_normative_refs:
        clean = str(item or "").strip()
        if clean:
            keys.append(clean)
    for reference in extract_normative_references(body_text):
        clean = str(reference.get("reference_key") or "").strip()
        if clean:
            keys.append(clean)
    seen: set[str] = set()
    ordered: list[str] = []
    for item in keys:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return PracticalDocMetadata(mentioned_reference_keys=tuple(ordered))


def derive_practical_identity_keys(row: dict[str, Any] | None) -> tuple[str, ...]:
    payload = row if isinstance(row, dict) else {}
    candidates: list[str] = []
    for field in ("reference_identity_keys", "normative_refs"):
        for item in payload.get(field) or ():
            clean = str(item or "").strip()
            if clean:
                candidates.append(clean)
    seen: set[str] = set()
    ordered: list[str] = []
    for item in candidates:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return tuple(ordered)


def is_allowed_practical_identity_key(value: str | None) -> bool:
    return bool(str(value or "").strip())
