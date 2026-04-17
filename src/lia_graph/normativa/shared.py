from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


_INTERNAL_NOISE_RE = re.compile(
    r"\b(?:doc_id|checksum|part_[0-9]+|pipeline|source_tier|chunk|artifact)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class NormativaSection:
    id: str
    title: str
    body: str

    def to_dict(self) -> dict[str, str]:
        return {"id": self.id, "title": self.title, "body": self.body}


@dataclass(frozen=True)
class NormativaSynthesis:
    lead: str = ""
    hierarchy_summary: str = ""
    applicability_summary: str = ""
    professional_impact: str = ""
    relations_summary: str = ""
    caution_text: str = ""
    next_steps: tuple[str, ...] = ()
    sections: tuple[NormativaSection, ...] = ()
    diagnostics: dict[str, Any] = field(default_factory=dict)


def clean_text(value: Any, *, max_chars: int = 320) -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip())
    if not text:
        return ""
    if _INTERNAL_NOISE_RE.search(text):
        return ""
    if len(text) <= max_chars:
        return text
    clipped = text[:max_chars].rsplit(" ", 1)[0].strip()
    return f"{clipped}..." if clipped else text[:max_chars].strip()


def split_sentences(text: str) -> list[str]:
    clean = re.sub(r"\s+", " ", str(text or "").strip())
    if not clean:
        return []
    return [item.strip() for item in re.split(r"(?<=[\.\?!:;])\s+", clean) if item.strip()]


def first_sentence(value: Any, *, max_chars: int = 320) -> str:
    for sentence in split_sentences(str(value or "")):
        clean = clean_text(sentence, max_chars=max_chars)
        if clean:
            return clean
    return clean_text(value, max_chars=max_chars)


def dedupe_lines(lines: list[str], *, max_items: int = 5) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in lines:
        clean = clean_text(item, max_chars=220)
        if not clean:
            continue
        key = clean.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(clean)
        if len(result) >= max_items:
            break
    return result


def render_bullets(lines: list[str]) -> str:
    cleaned = dedupe_lines(lines)
    if not cleaned:
        return ""
    return "\n".join(f"- {item}" for item in cleaned)


def title_hint(context: dict[str, Any]) -> str:
    return clean_text(
        context.get("title")
        or dict(context.get("citation") or {}).get("legal_reference")
        or dict(context.get("citation") or {}).get("source_label")
        or "Documento",
        max_chars=180,
    )
