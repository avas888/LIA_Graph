"""Normative-reference helpers shared by citations and profiles."""

from __future__ import annotations

import re
from typing import Any

_DOC_PART_SUFFIX_RE = re.compile(r"_part_[0-9]+$", re.IGNORECASE)
_ART_RE = re.compile(r"\bart(?:[íi]culo|\.?)s?\s+(\d+(?:[-.]\d+)*)", re.IGNORECASE)
_LEY_RE = re.compile(r"\bley\s+(\d{1,6})(?:\s+de\s+(\d{4}))?", re.IGNORECASE)
_DEC_RE = re.compile(r"\bdecreto\s+(\d{1,6})(?:\s+de\s+(\d{4}))?", re.IGNORECASE)


def logical_doc_id(doc_id: str) -> str:
    clean = str(doc_id or "").strip()
    if not clean:
        return ""
    return _DOC_PART_SUFFIX_RE.sub("", clean)


def _normalize_article(value: str) -> str:
    return str(value or "").strip().replace(".", "-")


def reference_identity(reference: dict[str, Any] | None) -> str:
    if not isinstance(reference, dict):
        return ""
    key = str(reference.get("reference_key") or "").strip().lower()
    locator = str(reference.get("locator_text") or "").strip().lower()
    return f"{key}::{locator}" if locator else key


def extract_normative_reference_mentions(text: str) -> list[dict[str, Any]]:
    value = str(text or "")
    if not value.strip():
        return []
    rows: list[dict[str, Any]] = []
    for match in _ART_RE.finditer(value):
        article = _normalize_article(match.group(1))
        rows.append(
            {
                "reference_identity": f"et::artículos {article.lower()}",
                "reference_key": "et",
                "reference_type": "et",
                "reference_text": "Estatuto Tributario",
                "locator_text": f"Artículos {article}",
                "locator_kind": "articles",
                "locator_start": article,
                "locator_end": None,
                "context": value[max(0, match.start() - 50) : min(len(value), match.end() + 80)].strip(),
            }
        )
    for pattern, ref_type in ((_LEY_RE, "ley"), (_DEC_RE, "decreto")):
        for match in pattern.finditer(value):
            number = str(match.group(1) or "").strip()
            year = str(match.group(2) or "").strip()
            label = ref_type.capitalize()
            rows.append(
                {
                    "reference_identity": f"{ref_type}:{number}:{year}".rstrip(":"),
                    "reference_key": f"{ref_type}:{number}" + (f":{year}" if year else ""),
                    "reference_type": ref_type,
                    "reference_text": f"{label} {number}" + (f" de {year}" if year else ""),
                    "locator_text": None,
                    "locator_kind": None,
                    "locator_start": None,
                    "locator_end": None,
                    "context": value[max(0, match.start() - 50) : min(len(value), match.end() + 80)].strip(),
                }
            )
    deduped: dict[str, dict[str, Any]] = {}
    for row in rows:
        deduped.setdefault(str(row["reference_identity"]), row)
    return list(deduped.values())


def best_reference_metadata(*values: str) -> dict[str, Any] | None:
    for value in values:
        mentions = extract_normative_reference_mentions(value)
        if not mentions:
            continue
        best = mentions[0]
        return {
            "reference_key": best.get("reference_key"),
            "reference_type": best.get("reference_type"),
            "reference_text": best.get("reference_text"),
            "reference_detail": {
                "locator_text": best.get("locator_text"),
                "locator_kind": best.get("locator_kind"),
                "locator_start": best.get("locator_start"),
                "locator_end": best.get("locator_end"),
            }
            if best.get("locator_text")
            else None,
        }
    return None

