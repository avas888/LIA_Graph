"""Phase 4 (v6) — citation allow-list.

Eight plan-specified cases plus config-load + extraction regression.
"""

from __future__ import annotations

from lia_graph.contracts.advisory import Citation
from lia_graph.pipeline_d._citation_allowlist import (
    allowlist_mode,
    extract_et_article,
    filter_citations,
    load_config,
)


def _cite(
    article: str | None = None,
    *,
    authority: str = "DIAN",
    topic: str = "laboral",
    source_type: str | None = None,
) -> Citation:
    legal_ref = f"Art. {article} del Estatuto Tributario" if article else None
    return Citation(
        doc_id=f"doc_{article or 'none'}",
        relative_path="x.md",
        authority=authority,
        topic=topic,
        pais="CO",
        legal_reference=legal_ref,
        source_type=source_type,
    )


def test_config_loads_four_topics() -> None:
    # Clear lru_cache between tests so env overrides propagate.
    load_config.cache_clear()
    cfg = load_config()
    topics = cfg.get("topics") or {}
    for expected in ("laboral", "sagrilaft_ptee", "facturacion_electronica", "regimen_simple"):
        assert expected in topics, f"missing topic entry: {expected}"
    assert cfg.get("version", "").startswith("v2026")


def test_laboral_drops_et_148(monkeypatch) -> None:
    monkeypatch.setenv("LIA_POLICY_CITATION_ALLOWLIST", "enforce")
    kept, dropped = filter_citations([_cite("148")], "laboral")
    assert kept == ()
    assert len(dropped) == 1
    assert dropped[0]["article"] == "148"
    assert dropped[0]["topic"] == "laboral"


def test_laboral_keeps_et_383(monkeypatch) -> None:
    monkeypatch.setenv("LIA_POLICY_CITATION_ALLOWLIST", "enforce")
    kept, dropped = filter_citations([_cite("383")], "laboral")
    assert len(kept) == 1
    assert dropped == []


def test_sagrilaft_drops_et_148(monkeypatch) -> None:
    monkeypatch.setenv("LIA_POLICY_CITATION_ALLOWLIST", "enforce")
    kept, dropped = filter_citations([_cite("148")], "sagrilaft_ptee")
    assert kept == ()
    assert len(dropped) == 1


def test_sagrilaft_keeps_circular_basica(monkeypatch) -> None:
    monkeypatch.setenv("LIA_POLICY_CITATION_ALLOWLIST", "enforce")
    cite = _cite(authority="CIRCULAR_BASICA_JURIDICA", topic="sagrilaft_ptee")
    kept, dropped = filter_citations([cite], "sagrilaft_ptee")
    assert len(kept) == 1
    assert dropped == []


def test_facturacion_drops_et_516_q11_case(monkeypatch) -> None:
    monkeypatch.setenv("LIA_POLICY_CITATION_ALLOWLIST", "enforce")
    kept, dropped = filter_citations([_cite("516")], "facturacion_electronica")
    assert kept == ()
    assert dropped[0]["article"] == "516"


def test_regimen_simple_drops_et_392(monkeypatch) -> None:
    monkeypatch.setenv("LIA_POLICY_CITATION_ALLOWLIST", "enforce")
    kept, dropped = filter_citations([_cite("392")], "regimen_simple")
    assert kept == ()
    assert dropped[0]["article"] == "392"


def test_mode_off_keeps_all_citations(monkeypatch) -> None:
    monkeypatch.setenv("LIA_POLICY_CITATION_ALLOWLIST", "off")
    assert allowlist_mode() == "off"
    citations = [_cite("148"), _cite("516"), _cite("392")]
    kept, dropped = filter_citations(citations, "laboral")
    assert len(kept) == 3
    assert dropped == []


def test_extract_et_article_handles_hyphenated_variants() -> None:
    assert extract_et_article(_cite("387-1")) == "387-1"
    assert extract_et_article(_cite("114-1")) == "114-1"
    assert extract_et_article(_cite(None)) is None
