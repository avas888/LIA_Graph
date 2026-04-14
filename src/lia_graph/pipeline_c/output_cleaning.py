from __future__ import annotations

import re

_PATH_LIKE_REFERENCE_RE = re.compile(
    r"(?:\b[A-Za-z0-9_.-]+\s*\|\s*)?(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+\.(?:md|pdf|jsonl?)",
    flags=re.IGNORECASE,
)
_UPLOAD_REFERENCE_RE = re.compile(r"local_upload://\S+", flags=re.IGNORECASE)


def strip_inline_evidence_annotations(text: str) -> str:
    source = str(text or "")
    if not source:
        return ""
    cleaned = source
    cleaned = re.sub(r"\[(?:evidencia|evidence):[^\]]*\]", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.replace(" [practica_erp]", "").replace("[practica_erp] ", "")
    cleaned = _PATH_LIKE_REFERENCE_RE.sub("", cleaned)
    cleaned = _UPLOAD_REFERENCE_RE.sub("", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"\s+([,.;:!?])", r"\1", cleaned)
    return cleaned.strip()

