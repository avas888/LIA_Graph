from __future__ import annotations

import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from ..expert_providers import extract_expert_providers, provider_labels
from .synthesis_helpers import extract_article_refs

_WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
_MANIFEST_PATH = _WORKSPACE_ROOT / "artifacts" / "canonical_corpus_manifest.json"
_KNOWLEDGE_BASE_ROOT = _WORKSPACE_ROOT / "knowledge_base"
_HEADING_RE = re.compile(r"^\s*#\s+(.+?)\s*$", re.MULTILINE)


def synthetic_interpretation_doc_id(relative_path: str) -> str:
    clean = str(relative_path or "").strip()
    digest = hashlib.sha1(clean.encode("utf-8")).hexdigest()[:16]
    return f"local_interp_{digest}"


def _read_preview_text(path: Path, *, max_chars: int = 12000) -> str:
    try:
        return path.read_text(encoding="utf-8")[:max_chars]
    except (OSError, UnicodeDecodeError):
        return ""


def _first_heading(text: str, *, fallback: str) -> str:
    match = _HEADING_RE.search(str(text or ""))
    if match:
        return str(match.group(1) or "").strip()
    return str(fallback or "").strip()


@lru_cache(maxsize=1)
def list_local_interpretation_rows() -> tuple[dict[str, Any], ...]:
    if not _MANIFEST_PATH.exists():
        return ()
    manifest = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for item in manifest.get("documents", ()) or ():
        if str(item.get("knowledge_class") or "").strip().lower() != "interpretative_guidance":
            continue
        relative_path = str(item.get("relative_path") or item.get("source_path") or "").strip()
        if not relative_path:
            continue
        absolute_path = (_KNOWLEDGE_BASE_ROOT / relative_path).resolve()
        if not absolute_path.exists():
            continue
        preview_text = _read_preview_text(absolute_path)
        providers = extract_expert_providers(preview_text)
        provider_names = provider_labels(providers)
        heading = _first_heading(preview_text, fallback=Path(relative_path).stem)
        normative_refs = list(dict.fromkeys(extract_article_refs(preview_text)))
        authority = provider_names[0] if provider_names else "Fuente profesional"
        row = dict(item)
        row.update(
            {
                "doc_id": str(row.get("doc_id") or "").strip() or synthetic_interpretation_doc_id(relative_path),
                "absolute_path": str(absolute_path),
                "relative_path": relative_path,
                "source_label": heading,
                "legal_reference": heading,
                "authority": str(row.get("authority") or "").strip() or authority,
                "provider_labels": provider_names,
                "providers": providers,
                "normative_refs": normative_refs or list(row.get("normative_refs") or []),
                "topic": str(row.get("topic") or row.get("topic_key") or "unknown").strip() or "unknown",
                "subtema": str(row.get("subtema") or row.get("subtopic_key") or "").strip(),
                "source_type": str(row.get("source_type") or "markdown").strip() or "markdown",
                "category": str(row.get("category") or "interpretative_guidance").strip() or "interpretative_guidance",
                "knowledge_class": "interpretative_guidance",
                "pais": str(row.get("pais") or "colombia").strip().lower() or "colombia",
                "__catalog_preview": preview_text,
            }
        )
        rows.append(row)
    return tuple(rows)


def find_local_interpretation_row(doc_id: str) -> dict[str, Any] | None:
    clean = str(doc_id or "").strip()
    if not clean:
        return None
    for row in list_local_interpretation_rows():
        if str(row.get("doc_id") or "").strip() == clean:
            return dict(row)
    return None


__all__ = [
    "find_local_interpretation_row",
    "list_local_interpretation_rows",
    "synthetic_interpretation_doc_id",
]
