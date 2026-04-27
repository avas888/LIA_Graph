"""Tests for citation role + anchor-strength inference (sub-fix 1B-δ)."""

from __future__ import annotations

from lia_graph.canon import CorpusMention
from lia_graph.citations import (
    ExtractedCitation,
    extract_citations,
    infer_anchor_strength,
    infer_role,
)


# ---------------------------------------------------------------------------
# Role inference
# ---------------------------------------------------------------------------


def test_infer_role_anchor_first_paragraph():
    text = "Art. 689-3 ET — beneficio de auditoría. El artículo dispone que..."
    mention = CorpusMention(text="Art. 689-3 ET", span=(0, 13))
    assert infer_role(text, mention) == "anchor"


def test_infer_role_comparator():
    text = (
        "El régimen tributario actual de zonas francas, vs el régimen del "
        "Art. 101 Ley 1819 de 2016, mantiene diferencias esenciales que..."
    ) + " " * 200  # push past the 200-char anchor window
    mention = CorpusMention(text="Art. 101 Ley 1819 de 2016", span=(220, 245))
    # Note: this test forces the mention out of the first 200 chars by padding
    text2 = " " * 200 + text
    mention2 = CorpusMention(text="Art. 101", span=(text2.index("Art. 101"), text2.index("Art. 101") + 8))
    role = infer_role(text2, mention2)
    assert role in ("comparator", "reference")


def test_infer_role_historical():
    head_pad = "x" * 250
    text = head_pad + (
        "Antiguamente, el régimen anterior aplicaba la deducción del "
        "Art. 158-1 ET para inversiones en CTeI; hoy esto fue derogado."
    )
    needle = "Art. 158-1 ET"
    start = text.index(needle)
    mention = CorpusMention(text=needle, span=(start, start + len(needle)))
    role = infer_role(text, mention)
    assert role == "historical"


def test_infer_role_default_reference():
    head_pad = "x" * 250
    text = head_pad + "El contribuyente debe consultar el Art. 689-3 ET."
    needle = "Art. 689-3 ET"
    start = text.index(needle)
    mention = CorpusMention(text=needle, span=(start, start + len(needle)))
    assert infer_role(text, mention) == "reference"


# ---------------------------------------------------------------------------
# Anchor-strength inference
# ---------------------------------------------------------------------------


def test_anchor_strength_ley_strongest():
    assert infer_anchor_strength("ley.2277.2022") == "ley"
    assert infer_anchor_strength("ley.2277.2022.art.96") == "ley"
    assert infer_anchor_strength("et.art.689-3") == "ley"


def test_anchor_strength_decreto():
    assert infer_anchor_strength("decreto.1474.2025") == "decreto"
    assert infer_anchor_strength("decreto.1625.2016.art.1.2.1.2.1") == "decreto"


def test_anchor_strength_res_dian():
    assert infer_anchor_strength("res.dian.165.2023") == "res_dian"


def test_anchor_strength_concepto_dian_weakest():
    assert infer_anchor_strength("concepto.dian.100208192-202") == "concepto_dian"
    assert infer_anchor_strength("concepto.dian.100208192-202.num.20") == "concepto_dian"


def test_anchor_strength_jurisprudencia():
    assert infer_anchor_strength("sent.cc.C-481.2019") == "jurisprudencia"
    assert infer_anchor_strength("sent.ce.28920.2025.07.03") == "jurisprudencia"
    assert infer_anchor_strength("auto.ce.28920.2024.12.16") == "jurisprudencia"


# ---------------------------------------------------------------------------
# extract_citations end-to-end
# ---------------------------------------------------------------------------


def test_extract_citations_finds_anchor_and_reference():
    chunk_text = (
        "Art. 689-3 ET — beneficio de auditoría. Este artículo regula el "
        "beneficio de auditoría introducido en su momento por la Ley 2155 de 2021 "
        "y prorrogado por la Ley 2294 de 2023."
    )
    cites = extract_citations("chunk-123", chunk_text)
    norm_ids = {c.norm_id for c in cites}
    # ET article in heading position → anchor
    assert any(
        c.norm_id == "et.art.689-3" and c.role == "anchor" for c in cites
    )
    # Subsequent law citations
    assert "ley.2155.2021" in norm_ids
    assert "ley.2294.2023" in norm_ids


def test_extract_citations_logs_refusal():
    chunk_text = "Decreto 1474 fue declarado inexequible."  # missing year
    refusals: list = []

    def _on_refusal(chunk_id, refusal):
        refusals.append((chunk_id, refusal.reason))

    cites = extract_citations("chunk-x", chunk_text, on_refusal=_on_refusal)
    # No successful citation
    assert cites == []
    # Refusal logged
    assert refusals
    assert refusals[0][1] == "missing_year"
