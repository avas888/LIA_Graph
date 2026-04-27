"""fixplan_v3 sub-fix 1B-δ — citation role + anchor-strength inference.

Each `norm_citations` row carries:
  * `role` ∈ {anchor, reference, comparator, historical} — inferred from
    where in the chunk_text the mention appears.
  * `anchor_strength` ∈ {ley, decreto, res_dian, concepto_dian, jurisprudencia}
    — mechanical from the canonical norm_id's `norm_type`.

Inference is intentionally conservative: when in doubt, mark `reference`
(lowest gate impact). Per fixplan_v3 §0.11.5 / §2.5, the SME spot-check on
50 random rows validates a sample.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Sequence

from lia_graph.canon import CorpusMention, find_mentions, norm_type as canon_norm_type
from lia_graph.vigencia import AnchorStrength, CitationRole


# ---------------------------------------------------------------------------
# Role inference
# ---------------------------------------------------------------------------


# Heading / first-paragraph cues — a mention here is an anchor.
_HEADING_RE = re.compile(r"^\s*(?:#+\s+|\*\*\s*|[A-ZÁÉÍÓÚÑ][^.\n]{0,80}\n[=\-]{3,})", re.MULTILINE)


# Comparator cues
_COMPARATOR_RE = re.compile(
    r"\b(?:vs\.?|frente\s+a|comparad[oa]|equivalente|análog[oa]|en\s+contraste\s+con|"
    r"a\s+diferencia\s+de|tabla\s+comparativa|cuadro\s+comparativo)\b",
    re.IGNORECASE,
)


# Historical cues
_HISTORICAL_RE = re.compile(
    r"\b(?:antiguamente|antes\s+de|antes\s+de\s+(?:la\s+)?(?:Ley|reforma)|"
    r"r[ée]gimen\s+anterior|histórica?mente|en\s+su\s+momento|"
    r"redacci[óo]n\s+anterior|hasta\s+(?:la\s+)?(?:Ley|reforma)|antes\s+del?)\b",
    re.IGNORECASE,
)


def infer_role(chunk_text: str, mention: CorpusMention) -> CitationRole:
    """Return the role of a mention given the chunk it sits in.

    Priority (first match wins):
      1. anchor — mention sits in the first 200 chars of the chunk OR inside a markdown heading.
      2. comparator — comparator-cue word within ~80 chars of the mention.
      3. historical — historical-cue word within ~80 chars of the mention.
      4. reference — default.
    """

    start, end = mention.span
    if start <= 200:
        return "anchor"
    # Heading detection: any heading-shaped line preceding the mention by < 200 chars
    head_window = chunk_text[max(0, start - 200) : start]
    if _HEADING_RE.search(head_window):
        return "anchor"
    surrounding = chunk_text[max(0, start - 80) : min(len(chunk_text), end + 80)]
    if _COMPARATOR_RE.search(surrounding):
        return "comparator"
    if _HISTORICAL_RE.search(surrounding):
        return "historical"
    return "reference"


# ---------------------------------------------------------------------------
# Anchor-strength inference
# ---------------------------------------------------------------------------


_TYPE_TO_STRENGTH: dict[str, AnchorStrength] = {
    "estatuto": "ley",
    "articulo_et": "ley",
    "ley": "ley",
    "ley_articulo": "ley",
    "decreto": "decreto",
    "decreto_articulo": "decreto",
    "resolucion": "res_dian",
    "res_articulo": "res_dian",
    "concepto_dian": "concepto_dian",
    "concepto_dian_numeral": "concepto_dian",
    "sentencia_cc": "jurisprudencia",
    "auto_ce": "jurisprudencia",
    "sentencia_ce": "jurisprudencia",
}


def infer_anchor_strength(norm_id: str) -> AnchorStrength:
    """Return the strength tier for a canonical norm_id.

    Strongest → weakest: ley > decreto > res_dian > jurisprudencia >
    concepto_dian. The retriever's synthesis policy gates on this — a chunk
    anchored only on `concepto_dian` is treated as supporting, not establishing.
    """

    nt = canon_norm_type(norm_id)
    return _TYPE_TO_STRENGTH.get(nt, "concepto_dian")


# ---------------------------------------------------------------------------
# Citation extraction over a chunk
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExtractedCitation:
    chunk_id: str
    norm_id: str
    role: CitationRole
    anchor_strength: AnchorStrength
    mention_text: str
    span: tuple[int, int]


def extract_citations(
    chunk_id: str,
    chunk_text: str,
    *,
    canonicalize_fn=None,
    on_refusal=None,
) -> list[ExtractedCitation]:
    """Walk a chunk, run the canonicalizer over each found mention, return
    successful (role-tagged, strength-tagged) citations. Refusals are passed
    to `on_refusal` for SME-triage logging.
    """

    if canonicalize_fn is None:
        from lia_graph.canon import canonicalize_or_refuse as _default
        canonicalize_fn = _default

    out: list[ExtractedCitation] = []
    for mention in find_mentions(chunk_text):
        norm_id, refusal = canonicalize_fn(mention.text, context=_chunk_context(chunk_text, mention.span))
        if norm_id is None:
            if on_refusal is not None and refusal is not None:
                on_refusal(chunk_id, refusal)
            continue
        role = infer_role(chunk_text, mention)
        strength = infer_anchor_strength(norm_id)
        out.append(
            ExtractedCitation(
                chunk_id=chunk_id,
                norm_id=norm_id,
                role=role,
                anchor_strength=strength,
                mention_text=mention.text,
                span=mention.span,
            )
        )
    return out


def _chunk_context(chunk_text: str, span: tuple[int, int]) -> str:
    s, e = span
    return chunk_text[max(0, s - 30) : min(len(chunk_text), e + 30)]


__all__ = [
    "ExtractedCitation",
    "extract_citations",
    "infer_anchor_strength",
    "infer_role",
]
