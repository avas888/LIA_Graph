"""Single parsing authority for normative references in free text.

Public contract:
- `extract_normative_references(text)` collapses to one row per logical
  `reference_key`. Use it when you only need to know which source was
  mentioned.
- `extract_normative_reference_mentions(text)` preserves distinct mention
  identities, including article locators. Use it when multiplicity matters,
  such as `arts. 147 y 290 ET`.

Keep parsing semantics here instead of rebuilding ad-hoc heuristics in
surface- or planner-specific modules.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


@dataclass(frozen=True, slots=True)
class ReferenceCandidate:
    reference_key: str
    reference_type: str
    reference_text: str
    context: str
    start: int
    end: int
    locator_text: str | None = None
    locator_kind: str | None = None
    locator_start: str | None = None
    locator_end: str | None = None

    @property
    def has_locator(self) -> bool:
        return any(
            str(value or "").strip()
            for value in (self.locator_text, self.locator_kind, self.locator_start, self.locator_end)
        )

    @property
    def sort_key(self) -> tuple[int, int, int]:
        return (
            int(self.start),
            _REFERENCE_TYPE_PRIORITY.get(str(self.reference_type or "").strip().lower(), 99),
            -len(str(self.locator_text or "")),
        )

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "reference_key": self.reference_key,
            "reference_type": self.reference_type,
            "reference_text": self.reference_text,
            "locator_text": self.locator_text,
            "locator_kind": self.locator_kind,
            "locator_start": self.locator_start,
            "locator_end": self.locator_end,
            "context": self.context,
            "start": self.start,
            "end": self.end,
        }

    def to_mention_dict(self, *, reference_identity: str) -> dict[str, Any]:
        payload = self.to_public_dict()
        payload["reference_identity"] = reference_identity
        return payload

_YEAR_MIN = 1900
_YEAR_MAX = 2100
_DOC_PART_SUFFIX_RE = re.compile(r"_part_[0-9]+$", re.IGNORECASE)
_ARTICLE_NUMBER_PATTERN = r"\d+(?:[\.\-]\d+)*"
_ET_INSERTED_ARTICLE_RE = re.compile(r"^\d+(?:\.\d+)+$")
_FORM_REFERENCE_MODIFIER_PATTERN = (
    r"(?:"
    r"oficial(?:\s+de\s+la\s+dian)?"
    r"|prescrito(?:\s+por\s+la\s+dian)?"
    r"|dian"
    r"|electr[oó]nico"
    r"|virtual"
    r"|vigente"
    r")"
)
_FORM_REFERENCE_NUMBER_HINT_PATTERN = r"(?:n(?:u|ú)mero|no|nro)\.?"

_GENERIC_REFERENCE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("ley", re.compile(r"\bley\s+(\d{1,6})(?:\s*(?:/|de)\s*(\d{4}))?\b", re.IGNORECASE)),
    (
        "decreto",
        re.compile(
            r"\bdecreto(?!\s+[uú]nico\s+reglamentario)\s+(\d{1,6})(?:\s*(?:/|de)\s*(\d{4}))?\b",
            re.IGNORECASE,
        ),
    ),
    ("circular", re.compile(r"\bcircular\s+(\d{1,6})(?:\s*(?:/|de)\s*(\d{4}))?\b", re.IGNORECASE)),
    (
        "resolucion",
        re.compile(
            r"\bresoluci[oó]n(?:\s+(DIAN))?\s+(\d{1,6})(?:\s*(?:/|de)\s*(\d{4}))?\b",
            re.IGNORECASE,
        ),
    ),
    (
        "concepto",
        re.compile(
            r"\bconcepto(?:\s+(DIAN))?\s+(\d{1,10})(?:\s*(?:/|de)\s*(\d{4}))?\b",
            re.IGNORECASE,
        ),
    ),
    (
        "formulario",
        re.compile(
            rf"\b(formulario|formato|f)\.?\s*"
            rf"(?:(?:{_FORM_REFERENCE_MODIFIER_PATTERN})\s+)*"
            rf"(?:{_FORM_REFERENCE_NUMBER_HINT_PATTERN}\s*)?"
            rf"(\d{{2,6}})(?![\.\-\/]\d)\b",
            re.IGNORECASE,
        ),
    ),
)

_ET_SOURCE_HEAD = r"(?:\bestatuto\s+tributario(?:\s*\(ET\))?|\bET\b|\bE\.\s*T\.)"
_ET_SOURCE_TAIL = r"(?:ET|E\.\s*T\.?|estatuto\s+tributario)\b"
_ET_ARTICLE_CUE_PATTERN = r"\bart(?:[íi]culos?|s?)(?:\.(?=\s|\d|$)|\b)"
_ET_LIST_PATTERN = rf"{_ARTICLE_NUMBER_PATTERN}(?:\s*(?:,|y|e|o)\s*{_ARTICLE_NUMBER_PATTERN})*"
_ET_LIST_NUMBER_RE = re.compile(_ARTICLE_NUMBER_PATTERN, re.IGNORECASE)
_ET_CUE_LIST_RE = re.compile(
    rf"{_ET_ARTICLE_CUE_PATTERN}\s*(?P<list>{_ET_LIST_PATTERN})"
    rf"(?:\s*(?:del?\s*)?{_ET_SOURCE_TAIL})?"
    r"(?!"
    r"\s+(?:"
    r"de(?:\s+la|\s+los|\s+las|\s+lo|l)?\s+"
    r"|del?\s+"
    r")"
    r"(?:ley|decreto|dur|decreto\s+[uú]nico\s+reglamentario|c[oó]digo|circular|resoluci[oó]n|concepto)\b"
    r")",
    re.IGNORECASE,
)
_ET_HEAD_RE = re.compile(
    rf"{_ET_SOURCE_HEAD}"
    rf"(?:\s*[:,-]?\s*(?:art(?:[íi]culos?|s?)\.?)\s*({_ARTICLE_NUMBER_PATTERN})"
    rf"(?:\s*(?:a|al|hasta|–)\s*({_ARTICLE_NUMBER_PATTERN}))?)?",
    re.IGNORECASE,
)
_ET_TAIL_RE = re.compile(
    rf"\bart(?:[íi]culos?|s?)\.?\s*({_ARTICLE_NUMBER_PATTERN})"
    rf"(?:\s*(?:a|al|hasta|–)\s*({_ARTICLE_NUMBER_PATTERN}))?"
    rf"\s*(?:del?\s*)?{_ET_SOURCE_TAIL}",
    re.IGNORECASE,
)
_ET_BARE_ARTICLE_RE = re.compile(
    rf"{_ET_SOURCE_HEAD}\s+({_ARTICLE_NUMBER_PATTERN})\b",
    re.IGNORECASE,
)
_ET_HEAD_LIST_RE = re.compile(
    rf"{_ET_SOURCE_HEAD}\s*(?:[:,-]?\s*)?(?P<list>{_ET_LIST_PATTERN})\b",
    re.IGNORECASE,
)
_ET_TAIL_LIST_RE = re.compile(
    rf"(?P<list>{_ET_LIST_PATTERN})\s*(?:del?\s*)?{_ET_SOURCE_TAIL}",
    re.IGNORECASE,
)
_ET_NUMBER_BEFORE_TAIL_RE = re.compile(
    rf"\b({_ARTICLE_NUMBER_PATTERN})\s*(?:del?\s*)?{_ET_SOURCE_TAIL}",
    re.IGNORECASE,
)
_ET_NON_REFERENCE_SUFFIX_RE = re.compile(
    r"^\s*(?:"
    r"a[nñ]os?"
    r"|mes(?:es)?"
    r"|semanas?"
    r"|d[ií]as?"
    r"|horas?"
    r"|periodos?"
    r"|per[ií]odos?"
    r"|vigencias?"
    r"|%|por\s+ciento"
    r"|uvt"
    r"|pesos?"
    r"|cop"
    r"|miles?"
    r"|millones?"
    r")\b",
    re.IGNORECASE,
)
_YEAR_LIKE_ARTICLE_TOKEN_RE = re.compile(r"^(?:19|20)\d{2}(?:-(?:19|20)\d{2})?$")
# Standalone bare article without explicit ET context — defaults to ET in
# Colombian tax domain, matching the frontend's normalizeMentionReference
# fallback.  Negative lookahead prevents false positives when the article
# clearly belongs to another law/decree.
_ET_STANDALONE_ARTICLE_RE = re.compile(
    rf"{_ET_ARTICLE_CUE_PATTERN}\s*({_ARTICLE_NUMBER_PATTERN})\b"
    rf"(?:\s*(?:a|al|hasta|–)\s*({_ARTICLE_NUMBER_PATTERN})\b)?"
    r"(?!"
    r"\s+(?:"
    r"de(?:\s+la|\s+los|\s+las|\s+lo|l)?\s+"
    r"|del?\s+"
    r")"
    r"(?:ley|decreto|dur|decreto\s+[uú]nico\s+reglamentario|c[oó]digo|circular|resoluci[oó]n|concepto)\b"
    r")",
    re.IGNORECASE,
)
_DUR_HEAD_RE = re.compile(
    r"(?:\bdecreto\s+[uú]nico\s+reglamentario(?:\s*\(DUR\))?\s*1625(?:\s+de\s+2016)?(?:\s*\(DUR\s*1625\))?"
    r"|\bDUR\s*1625(?:\s+de\s+2016)?\b)"
    r"(?:\s*[:,-]?\s*((?:(?:parte|t[íi]tulo|cap[íi]tulo|libro|secci[oó]n|art(?:[íi]culos?|s?)\.?)"
    r"[^.;\n]{0,120})))?",
    re.IGNORECASE,
)
_DUR_TAIL_RE = re.compile(
    rf"\bart(?:[íi]culos?|s?)\.?\s*({_ARTICLE_NUMBER_PATTERN})"
    rf"(?:\s*(?:a|al|hasta|–)\s*({_ARTICLE_NUMBER_PATTERN}))?"
    r"\s*(?:del?\s*)?"
    r"(?:DUR\s*1625|decreto\s+[uú]nico\s+reglamentario\s+1625(?:\s+de\s+2016)?)\b",
    re.IGNORECASE,
)
_DUR_BARE_ARTICLE_RE = re.compile(
    rf"(?:\bDUR\s*1625(?:\s+de\s+2016)?\b|\bdecreto\s+[uú]nico\s+reglamentario\s+1625(?:\s+de\s+2016)?\b)"
    rf"\s*(?:[:,-]?\s*(?:art(?:[íi]culos?|s?)\.?)\s*({_ARTICLE_NUMBER_PATTERN}))\b",
    re.IGNORECASE,
)
_DUR_STRUCTURE_HINT_RE = re.compile(
    r"(?:(?:parte|t[íi]tulo|cap[íi]tulo|libro|secci[oó]n)\s+[0-9A-Za-z.\-]+(?:\s*,\s*)?){1,4}",
    re.IGNORECASE,
)
_REFERENCE_TYPE_PRIORITY = {
    "et": 0,
    "dur": 1,
    "resolucion_dian": 2,
    "concepto_dian": 3,
    "ley": 4,
    "decreto": 5,
    "resolucion": 6,
    "concepto": 7,
    "circular": 8,
    "formulario": 9,
}


def logical_doc_id(doc_id: str) -> str:
    clean = str(doc_id or "").strip()
    if not clean:
        return clean
    return _DOC_PART_SUFFIX_RE.sub("", clean)


def _sanitize_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_number(value: str) -> str:
    digits = re.sub(r"\D+", "", value or "")
    clean = digits.lstrip("0")
    return clean or "0"


def _normalize_year(value: str | None) -> str | None:
    raw = _sanitize_text(value)
    if not raw:
        return None
    digits = re.sub(r"\D+", "", raw)
    if len(digits) != 4:
        return None
    try:
        year_value = int(digits)
    except ValueError:
        return None
    if year_value < _YEAR_MIN or year_value > _YEAR_MAX:
        return None
    return f"{year_value:04d}"


def _normalize_locator(value: str | None) -> str | None:
    clean = re.sub(r"\s+", " ", str(value or "")).strip(" ,:;")
    return clean or None


def _canonicalize_et_article_number(value: str | None) -> str | None:
    clean = _normalize_locator(value)
    if not clean:
        return None
    if _ET_INSERTED_ARTICLE_RE.fullmatch(clean):
        return clean.replace(".", "-")
    return clean


def _canonicalize_et_article_locator_text(value: str | None) -> str | None:
    clean = _normalize_locator(value)
    if not clean:
        return None
    return re.sub(r"\b\d+(?:\.\d+)+\b", lambda match: match.group(0).replace(".", "-"), clean)


def _extract_context(text: str, *, start: int, end: int, max_chars: int = 220) -> str:
    clean = str(text or "")
    if not clean:
        return ""
    left = max(0, start - 70)
    right = min(len(clean), end + 120)
    window = re.sub(r"\s+", " ", clean[left:right]).strip()
    if len(window) <= max_chars:
        return window
    clipped = window[: max_chars - 3].rstrip()
    return f"{clipped}..."


def _reference_payload(
    *,
    reference_key: str,
    reference_type: str,
    reference_text: str,
    text: str,
    start: int,
    end: int,
    locator_text: str | None = None,
    locator_kind: str | None = None,
    locator_start: str | None = None,
    locator_end: str | None = None,
) -> ReferenceCandidate:
    locator_text_value = _normalize_locator(locator_text)
    locator_kind_value = str(locator_kind or "").strip() or None
    locator_start_value = str(locator_start or "").strip() or None
    locator_end_value = str(locator_end or "").strip() or None
    if reference_key == "et" and locator_kind_value == "articles":
        locator_start_value = _canonicalize_et_article_number(locator_start_value)
        locator_end_value = _canonicalize_et_article_number(locator_end_value)
        locator_text_value = _canonicalize_et_article_locator_text(locator_text_value)
    return ReferenceCandidate(
        reference_key=reference_key,
        reference_type=reference_type,
        reference_text=reference_text,
        context=_extract_context(text, start=start, end=end),
        start=int(start),
        end=int(end),
        locator_text=locator_text_value,
        locator_kind=locator_kind_value,
        locator_start=locator_start_value,
        locator_end=locator_end_value,
    )


def _article_reference_payload(
    *,
    reference_key: str,
    reference_type: str,
    reference_text: str,
    text: str,
    start: int,
    end: int,
    article_start: str,
    article_end: str | None = None,
) -> ReferenceCandidate:
    locator_text = f"Artículos {article_start}"
    if article_end:
        locator_text = f"{locator_text} a {article_end}"
    return _reference_payload(
        reference_key=reference_key,
        reference_type=reference_type,
        reference_text=reference_text,
        text=text,
        start=start,
        end=end,
        locator_text=locator_text,
        locator_kind="articles",
        locator_start=article_start,
        locator_end=article_end,
    )


def _is_year_like_article_token(value: str | None) -> bool:
    clean = _normalize_locator(value)
    if not clean:
        return False
    return bool(_YEAR_LIKE_ARTICLE_TOKEN_RE.fullmatch(clean))


def _has_non_reference_article_suffix(text: str, token_end: int) -> bool:
    return bool(_ET_NON_REFERENCE_SUFFIX_RE.match(str(text or "")[token_end : token_end + 24]))


def _extract_et_article_list_payloads(
    text: str,
    match: re.Match[str],
    *,
    list_group: str = "list",
) -> list[ReferenceCandidate]:
    list_text = str(match.group(list_group) or "").strip()
    if not list_text:
        return []
    list_start = match.start(list_group)
    token_matches = list(_ET_LIST_NUMBER_RE.finditer(list_text))
    if token_matches and _has_non_reference_article_suffix(text, match.end(list_group)):
        token_matches = token_matches[:-1]

    results: list[ReferenceCandidate] = []
    for token_match in token_matches:
        article_start = str(token_match.group(0) or "").strip()
        if not article_start or _is_year_like_article_token(article_start):
            continue
        token_start = list_start + token_match.start()
        token_end = list_start + token_match.end()
        results.append(
            _article_reference_payload(
                reference_key="et",
                reference_type="et",
                reference_text="Estatuto Tributario",
                text=text,
                start=token_start,
                end=token_end,
                article_start=article_start,
            )
        )
    return results


def _extract_et_source_candidates(text: str) -> list[ReferenceCandidate]:
    value = str(text or "")
    results: list[ReferenceCandidate] = []
    for match in _ET_HEAD_RE.finditer(value):
        article_start = str(match.group(1) or "").strip() or None
        article_end = str(match.group(2) or "").strip() or None
        if article_start:
            if _is_year_like_article_token(article_start) or _has_non_reference_article_suffix(value, match.end()):
                continue
            results.append(
                _article_reference_payload(
                    reference_key="et",
                    reference_type="et",
                    reference_text="Estatuto Tributario",
                    text=value,
                    start=match.start(),
                    end=match.end(),
                    article_start=article_start,
                    article_end=article_end,
                )
            )
            continue
        results.append(
            _reference_payload(
                reference_key="et",
                reference_type="et",
                reference_text="Estatuto Tributario",
                text=value,
                start=match.start(),
                end=match.end(),
            )
        )
    return results


def _extract_et_list_candidates(text: str) -> list[ReferenceCandidate]:
    value = str(text or "")
    results: list[ReferenceCandidate] = []
    for pattern in (_ET_CUE_LIST_RE, _ET_HEAD_LIST_RE, _ET_TAIL_LIST_RE):
        for match in pattern.finditer(value):
            results.extend(_extract_et_article_list_payloads(value, match))
    return results


def _extract_et_simple_article_candidates(text: str) -> list[ReferenceCandidate]:
    value = str(text or "")
    results: list[ReferenceCandidate] = []

    for match in _ET_TAIL_RE.finditer(value):
        article_start = str(match.group(1) or "").strip() or None
        article_end = str(match.group(2) or "").strip() or None
        if not article_start or _is_year_like_article_token(article_start):
            continue
        results.append(
            _article_reference_payload(
                reference_key="et",
                reference_type="et",
                reference_text="Estatuto Tributario",
                text=value,
                start=match.start(),
                end=match.end(),
                article_start=article_start,
                article_end=article_end,
            )
        )

    for pattern in (_ET_NUMBER_BEFORE_TAIL_RE, _ET_BARE_ARTICLE_RE, _ET_STANDALONE_ARTICLE_RE):
        for match in pattern.finditer(value):
            article_start = str(match.group(1) or "").strip() or None
            if not article_start or _is_year_like_article_token(article_start):
                continue
            if pattern in (_ET_BARE_ARTICLE_RE, _ET_STANDALONE_ARTICLE_RE) and _has_non_reference_article_suffix(value, match.end()):
                continue
            article_end = None
            if match.lastindex and match.lastindex >= 2:
                article_end = str(match.group(2) or "").strip() or None
            results.append(
                _article_reference_payload(
                    reference_key="et",
                    reference_type="et",
                    reference_text="Estatuto Tributario",
                    text=value,
                    start=match.start(),
                    end=match.end(),
                    article_start=article_start,
                    article_end=article_end,
                )
            )
    return results


def _extract_et_references(text: str) -> list[ReferenceCandidate]:
    return [
        *_extract_et_source_candidates(text),
        *_extract_et_list_candidates(text),
        *_extract_et_simple_article_candidates(text),
    ]


def _extract_dur_structure_candidates(text: str) -> list[ReferenceCandidate]:
    value = str(text or "")
    results: list[ReferenceCandidate] = []
    for match in _DUR_HEAD_RE.finditer(value):
        locator_text = _normalize_locator(match.group(1))
        results.append(
            _reference_payload(
                reference_key="dur:1625:2016",
                reference_type="dur",
                reference_text="DUR 1625 de 2016",
                text=value,
                start=match.start(),
                end=match.end(),
                locator_text=locator_text,
                locator_kind="structure" if locator_text else None,
            )
        )
    return results


def _extract_dur_article_candidates(text: str) -> list[ReferenceCandidate]:
    value = str(text or "")
    results: list[ReferenceCandidate] = []
    for match in _DUR_TAIL_RE.finditer(value):
        article_start = str(match.group(1) or "").strip() or None
        article_end = str(match.group(2) or "").strip() or None
        if not article_start:
            continue
        results.append(
            _article_reference_payload(
                reference_key="dur:1625:2016",
                reference_type="dur",
                reference_text="DUR 1625 de 2016",
                text=value,
                start=match.start(),
                end=match.end(),
                article_start=article_start,
                article_end=article_end,
            )
        )
    return results


def _extract_dur_bare_article_candidates(text: str) -> list[ReferenceCandidate]:
    value = str(text or "")
    results: list[ReferenceCandidate] = []
    for match in _DUR_BARE_ARTICLE_RE.finditer(value):
        article_start = str(match.group(1) or "").strip() or None
        if not article_start:
            continue
        results.append(
            _article_reference_payload(
                reference_key="dur:1625:2016",
                reference_type="dur",
                reference_text="DUR 1625 de 2016",
                text=value,
                start=match.start(),
                end=match.end(),
                article_start=article_start,
            )
        )
    return results


def _extract_dur_references(text: str) -> list[ReferenceCandidate]:
    return [
        *_extract_dur_structure_candidates(text),
        *_extract_dur_article_candidates(text),
        *_extract_dur_bare_article_candidates(text),
    ]


def _normalize_generic_reference(
    *,
    reference_type: str,
    number_raw: str,
    year_raw: str | None,
    form_alias: str | None,
    provider_hint: str | None,
) -> tuple[str, str, str]:
    number = _normalize_number(number_raw)
    year = _normalize_year(year_raw)
    provider = str(provider_hint or "").strip().lower()

    if reference_type == "formulario":
        label = "Formato" if str(form_alias or "").strip().lower() == "formato" else "Formulario"
        return f"formulario:{number}", "formulario", f"{label} {number}"
    if reference_type == "resolucion":
        if provider == "dian":
            return (
                f"resolucion_dian:{number}" + (f":{year}" if year else ""),
                "resolucion_dian",
                f"Resolución DIAN {number}" + (f" de {year}" if year else ""),
            )
        return (
            f"resolucion:{number}" + (f":{year}" if year else ""),
            "resolucion",
            f"Resolución {number}" + (f" de {year}" if year else ""),
        )
    if reference_type == "concepto":
        if provider == "dian":
            return (
                f"concepto_dian:{number}" + (f":{year}" if year else ""),
                "concepto_dian",
                f"Concepto DIAN {number}" + (f" de {year}" if year else ""),
            )
        return (
            f"concepto:{number}" + (f":{year}" if year else ""),
            "concepto",
            f"Concepto {number}" + (f" de {year}" if year else ""),
        )
    return (
        f"{reference_type}:{number}" + (f":{year}" if year else ""),
        reference_type,
        f"{reference_type.capitalize()} {number}" + (f" de {year}" if year else ""),
    )


def _extract_generic_reference_match(
    *,
    reference_type: str,
    match: re.Match[str],
    text: str,
) -> ReferenceCandidate:
    form_alias = None
    provider_hint = None
    if reference_type == "formulario":
        form_alias = _sanitize_text(match.group(1)).lower()
        number_raw = _sanitize_text(match.group(2))
        year_raw = None
    elif reference_type in {"resolucion", "concepto"}:
        provider_hint = _sanitize_text(match.group(1))
        number_raw = _sanitize_text(match.group(2))
        year_raw = match.group(3)
    else:
        number_raw = _sanitize_text(match.group(1))
        year_raw = match.group(2)

    reference_key, normalized_type, reference_text = _normalize_generic_reference(
        reference_type=reference_type,
        number_raw=number_raw,
        year_raw=year_raw,
        form_alias=form_alias,
        provider_hint=provider_hint,
    )
    return _reference_payload(
        reference_key=reference_key,
        reference_type=normalized_type,
        reference_text=reference_text,
        text=text,
        start=match.start(),
        end=match.end(),
    )


def _extract_generic_references(text: str) -> list[ReferenceCandidate]:
    value = str(text or "")
    results: list[ReferenceCandidate] = []
    for reference_type, pattern in _GENERIC_REFERENCE_PATTERNS:
        for match in pattern.finditer(value):
            results.append(
                _extract_generic_reference_match(
                    reference_type=reference_type,
                    match=match,
                    text=value,
                )
            )
    return results


def _candidate_sort_key(item: ReferenceCandidate) -> tuple[int, int, int]:
    return item.sort_key


def _candidate_has_locator(item: ReferenceCandidate) -> bool:
    return item.has_locator


def _is_shadowed_et_fallback_candidate(
    candidate: ReferenceCandidate,
    candidates: list[ReferenceCandidate],
) -> bool:
    if str(candidate.reference_key or "").strip().lower() != "et":
        return False
    if not _candidate_has_locator(candidate):
        return False
    start = int(candidate.start)
    end = int(candidate.end)
    for other in candidates:
        if other is candidate:
            continue
        if str(other.reference_key or "").strip().lower() == "et":
            continue
        other_start = int(other.start)
        other_end = int(other.end)
        if other_start > start:
            continue
        if other_end < end:
            continue
        return True
    return False


def _prefer_candidate(current: ReferenceCandidate | None, candidate: ReferenceCandidate) -> bool:
    if current is None:
        return True
    current_locator_len = len(str(current.locator_text or ""))
    candidate_locator_len = len(str(candidate.locator_text or ""))
    if candidate_locator_len != current_locator_len:
        return candidate_locator_len > current_locator_len
    return int(candidate.start) < int(current.start)


def _collect_reference_candidates(text: str) -> list[ReferenceCandidate]:
    value = str(text or "")
    if not value.strip():
        return []

    candidates: list[ReferenceCandidate] = [
        *_extract_et_references(value),
        *_extract_dur_references(value),
        *_extract_generic_references(value),
    ]
    candidates = [
        candidate
        for candidate in candidates
        if not _is_shadowed_et_fallback_candidate(candidate, candidates)
    ]
    candidates.sort(key=_candidate_sort_key)
    return candidates


def _public_reference_row(row: ReferenceCandidate) -> dict[str, Any]:
    return row.to_public_dict()


def extract_normative_references(text: str) -> list[dict[str, Any]]:
    """Return one normalized row per logical `reference_key`."""
    candidates = _collect_reference_candidates(text)
    if not candidates:
        return []

    best_by_key: dict[str, ReferenceCandidate] = {}
    for row in candidates:
        key = str(row.reference_key or "").strip()
        if not key:
            continue
        current = best_by_key.get(key)
        if not _prefer_candidate(current, row):
            continue
        best_by_key[key] = row

    return [
        _public_reference_row(best_by_key[key])
        for key in sorted(best_by_key, key=lambda item: int(best_by_key[item].start))
    ]


def _normalize_reference_identity_component(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().lower()


def _reference_identity_from_parts(
    *,
    reference_key: Any,
    locator_kind: Any = None,
    locator_start: Any = None,
    locator_end: Any = None,
    locator_text: Any = None,
) -> str:
    key = _normalize_reference_identity_component(reference_key)
    if not key:
        return ""
    locator_kind_raw = locator_kind
    locator_start_raw = locator_start
    locator_end_raw = locator_end
    locator_text_raw = locator_text
    if key == "et" and str(locator_kind_raw or "").strip().lower() == "articles":
        locator_start_raw = _canonicalize_et_article_number(str(locator_start_raw or "").strip() or None)
        locator_end_raw = _canonicalize_et_article_number(str(locator_end_raw or "").strip() or None)
        locator_text_raw = _canonicalize_et_article_locator_text(str(locator_text_raw or "").strip() or None)
    locator_kind = _normalize_reference_identity_component(locator_kind_raw)
    locator_start = _normalize_reference_identity_component(locator_start_raw)
    locator_end = _normalize_reference_identity_component(locator_end_raw)
    locator_text = _normalize_reference_identity_component(locator_text_raw)
    if locator_kind or locator_start or locator_end or locator_text:
        return "::".join((key, locator_kind, locator_start, locator_end, locator_text))
    return key


def _candidate_reference_identity(candidate: ReferenceCandidate) -> str:
    return _reference_identity_from_parts(
        reference_key=candidate.reference_key,
        locator_kind=candidate.locator_kind,
        locator_start=candidate.locator_start,
        locator_end=candidate.locator_end,
        locator_text=candidate.locator_text,
    )


def reference_identity(reference: dict[str, Any] | None) -> str:
    if not isinstance(reference, dict):
        return ""
    return _reference_identity_from_parts(
        reference_key=reference.get("reference_key"),
        locator_kind=reference.get("locator_kind"),
        locator_start=reference.get("locator_start"),
        locator_end=reference.get("locator_end"),
        locator_text=reference.get("locator_text"),
    )


def extract_normative_reference_mentions(text: str) -> list[dict[str, Any]]:
    """Return mention-level rows preserving distinct locator identities."""
    candidates = _collect_reference_candidates(text)
    if not candidates:
        return []

    best_by_identity: dict[str, ReferenceCandidate] = {}
    has_located_variant_by_key: dict[str, bool] = {}
    for row in candidates:
        key = str(row.reference_key or "").strip()
        if not key:
            continue
        identity = _candidate_reference_identity(row)
        if not identity:
            continue
        current = best_by_identity.get(identity)
        if not _prefer_candidate(current, row):
            continue
        best_by_identity[identity] = row
        if _candidate_has_locator(row):
            has_located_variant_by_key[key] = True

    unique: list[dict[str, Any]] = []
    for identity in sorted(best_by_identity, key=lambda item: int(best_by_identity[item].start)):
        row = best_by_identity[identity]
        key = str(row.reference_key or "").strip()
        has_locator = _candidate_has_locator(row)
        if not has_locator and has_located_variant_by_key.get(key):
            continue
        unique.append(row.to_mention_dict(reference_identity=identity))
    return unique


def best_reference_metadata(*values: str) -> dict[str, Any] | None:
    candidates: list[ReferenceCandidate] = []
    for value in values:
        candidates.extend(_collect_reference_candidates(str(value or "")))
    if not candidates:
        return None
    candidates.sort(
        key=lambda item: (
            _REFERENCE_TYPE_PRIORITY.get(str(item.reference_type or "").strip().lower(), 99),
            -len(str(item.locator_text or "")),
            int(item.start),
        )
    )
    best = candidates[0]
    return {
        "reference_key": best.reference_key,
        "reference_type": best.reference_type,
        "reference_text": best.reference_text,
        "reference_detail": {
            "locator_text": best.locator_text,
            "locator_kind": best.locator_kind,
            "locator_start": best.locator_start,
            "locator_end": best.locator_end,
        }
        if best.has_locator
        else None,
    }
