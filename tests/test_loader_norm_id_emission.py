"""Tests for v19 Fase 3 — `_build_article_nodes` stamps `norm_id` on
every `:ArticleNode` it emits, using `lia_graph.norm_id_rules.derive_norm_id`
as the single source of truth shared with `scripts/migrate_falkor_norm_ids.py`.

The contract these tests lock in:
1. Numbered articles whose source_path matches a rule → `norm_id` filled.
2. Prose-only articles → `norm_id` is "" (empty string).
3. SUIN nodes (`suin://N`) → `norm_id` is "" (skipped per v6 catalog).
4. Unknown paths → `norm_id` is "" (OTHER bucket, surfaced separately).
5. The `norm_id` value matches what the migration script's
   `derive_norm_id` would produce for the same `(source_path,
   article_number)` — no drift between Fase 2 batch + Fase 3 ingest.
"""

from __future__ import annotations

from lia_graph.ingestion.loader import _build_article_nodes
from lia_graph.ingestion.parser import ParsedArticle
from lia_graph.norm_id_rules import derive_norm_id


def _make_article(
    *,
    article_key: str = "1",
    article_number: str = "1",
    heading: str = "Sample",
    body: str = "body text",
    status: str = "vigente",
    source_path: str | None = "knowledge_base/CORE ya Arriba/Corpus de Contabilidad/NORMATIVA/N-some-et.md",
) -> ParsedArticle:
    return ParsedArticle(
        article_key=article_key,
        article_number=article_number,
        heading=heading,
        body=body,
        full_text=body,
        status=status,
        source_path=source_path,
    )


def _prop(record, name):
    return record.properties.get(name)


def test_cst_consolidado_article_gets_cst_dot_art_norm_id():
    a = _make_article(
        article_key="64",
        article_number="64",
        heading="TERMINACION UNILATERAL DEL CONTRATO DE TRABAJO SIN JUSTA CAUSA",
        source_path="knowledge_base/CORE ya Arriba/LEYES/LABORAL_SEGURIDAD_SOCIAL/consolidado/Codigo_Sustantivo_Trabajo.md",
    )
    nodes = _build_article_nodes((a,))
    assert len(nodes) == 1
    assert _prop(nodes[0], "norm_id") == "cst.art.64"
    # Existing properties still present
    assert _prop(nodes[0], "article_number") == "64"
    assert _prop(nodes[0], "is_prose_only") is False


def test_et_corpus_article_gets_et_dot_art_norm_id():
    a = _make_article(
        article_number="420",
        article_key="420",
        source_path="knowledge_base/CORE ya Arriba/IVA_COMPLETO/NORMATIVA/IVA-N01-hechos-generadores-responsables-tarifas.md",
    )
    nodes = _build_article_nodes((a,))
    assert _prop(nodes[0], "norm_id") == "et.art.420"


def test_ley_filename_article_gets_ley_dot_art_norm_id():
    a = _make_article(
        article_number="28",
        article_key="28",
        source_path="knowledge_base/CORE ya Arriba/LEYES/LABORAL_SEGURIDAD_SOCIAL/consolidado/Ley-789-2002.md",
    )
    nodes = _build_article_nodes((a,))
    assert _prop(nodes[0], "norm_id") == "ley.789.2002.art.28"


def test_decreto_filename_article_gets_decreto_norm_id():
    a = _make_article(
        article_number="1",
        article_key="1",
        source_path="knowledge_base/CORE ya Arriba/NORMATIVA_LEYES/DT-1221-2008-NORMATIVA.md",
    )
    nodes = _build_article_nodes((a,))
    assert _prop(nodes[0], "norm_id") == "decreto.1221.2008.art.1"


def test_reforma_laboral_2466_article_gets_ley_2466_norm_id():
    a = _make_article(
        article_number="11",
        article_key="11",
        source_path="knowledge_base/CORE ya Arriba/REFORMA_LABORAL_LEY_2466/NORMATIVA/REF-N01-marco-legal-reforma-laboral-ley-2466-2025.md",
    )
    nodes = _build_article_nodes((a,))
    assert _prop(nodes[0], "norm_id") == "ley.2466.2025.art.11"


def test_prose_only_article_has_empty_norm_id():
    """Whole-doc-fallback nodes (no article_number) MUST NOT carry a norm_id —
    they're keyed by `whole::<source_path>` per loader.py:51-54 and have no
    statutory anchor to canonicalize."""
    a = _make_article(
        article_key="doc",
        article_number="",
        source_path="knowledge_base/CORE ya Arriba/LABORAL_NOMINA/PLAYBOOKS/playbook_pila_aportes.md",
    )
    nodes = _build_article_nodes((a,))
    assert _prop(nodes[0], "is_prose_only") is True
    assert _prop(nodes[0], "norm_id") == ""


def test_suin_article_has_empty_norm_id():
    """SUIN nodes are v6's domain (`:Norm` catalog handles their identity).
    v19 leaves them alone — they stamp the empty-string norm_id."""
    a = _make_article(
        article_key="1003086",
        article_number="1003086",
        source_path="suin://1003082",
    )
    nodes = _build_article_nodes((a,))
    assert _prop(nodes[0], "norm_id") == ""


def test_unknown_path_article_has_empty_norm_id():
    """Numbered article in an unknown path → OTHER bucket → no norm_id
    stamped. The article still becomes a node (eligibility unchanged); only
    the norm_id property is empty so downstream filters can surface it."""
    a = _make_article(
        article_number="42",
        article_key="42",
        source_path="completely/unknown/path/random.md",
    )
    nodes = _build_article_nodes((a,))
    assert _prop(nodes[0], "norm_id") == ""


def test_loader_emits_same_norm_ids_as_migration_script():
    """Cross-check: loader and `derive_norm_id` must agree byte-for-byte.
    Prevents drift between the Fase 2 batch migration and the Fase 3 fresh
    ingests."""
    fixtures = [
        ("knowledge_base/CORE ya Arriba/LEYES/LABORAL_SEGURIDAD_SOCIAL/consolidado/Codigo_Sustantivo_Trabajo.md", "64"),
        ("knowledge_base/CORE ya Arriba/IVA_COMPLETO/NORMATIVA/IVA-N01-x.md", "420"),
        ("knowledge_base/CORE ya Arriba/LEYES/LABORAL_SEGURIDAD_SOCIAL/consolidado/Ley-50-1990.md", "127-132"),
        ("knowledge_base/CORE ya Arriba/REFORMA_LABORAL_LEY_2466/NORMATIVA/REF-N01-x.md", "11"),
        ("knowledge_base/CORE ya Arriba/NORMATIVA_LEYES/DT-1221-2008-NORMATIVA.md", "1"),
    ]
    articles = [
        _make_article(article_key=num, article_number=num, source_path=sp)
        for sp, num in fixtures
    ]
    nodes = _build_article_nodes(tuple(articles))
    assert len(nodes) == len(fixtures)
    for node, (sp, num) in zip(nodes, fixtures):
        expected = derive_norm_id(article_id=num, article_number=num, source_path=sp).norm_id
        actual = _prop(node, "norm_id")
        # Loader stamps "" for None; derive_norm_id may return a string or None.
        assert actual == (expected or ""), (
            f"loader/migration drift for sp={sp!r} num={num!r}: "
            f"loader={actual!r}, derive_norm_id={expected!r}"
        )


def test_letter_suffix_composite_preserved_through_loader():
    """CST 97-A — parser fix + canon widening + loader emission must all agree."""
    a = _make_article(
        article_key="97-A",
        article_number="97-A",
        heading="ADICIONADO POR LEY 50/1990",
        source_path="knowledge_base/CORE ya Arriba/LEYES/LABORAL_SEGURIDAD_SOCIAL/consolidado/Codigo_Sustantivo_Trabajo.md",
    )
    nodes = _build_article_nodes((a,))
    assert _prop(nodes[0], "norm_id") == "cst.art.97-A"


# ---------------------------------------------------------------------------
# v19 Fase 3 — MERGE key uses norm_id when derivable (prevents CST vs Ley vs
# ET cross-doc collision on bare article_number).
# ---------------------------------------------------------------------------


def test_merge_key_is_norm_id_for_numbered_articles():
    """`_graph_article_key` (the MERGE key) must return the canonical norm_id
    for numbered articles whose path resolves, so CST 64 and Ley 50/1990 art 64
    land on DISTINCT nodes. Empirically validated 2026-05-15."""
    cst_64 = _make_article(
        article_key="64",
        article_number="64",
        heading="TERMINACION UNILATERAL",
        source_path="knowledge_base/CORE ya Arriba/LEYES/LABORAL_SEGURIDAD_SOCIAL/consolidado/Codigo_Sustantivo_Trabajo.md",
    )
    ley_50_64 = _make_article(
        article_key="64",
        article_number="64",
        heading="Indemnización por terminación sin justa causa",
        source_path="knowledge_base/CORE ya Arriba/LEYES/LABORAL_SEGURIDAD_SOCIAL/consolidado/Ley-50-1990.md",
    )
    nodes = _build_article_nodes((cst_64, ley_50_64))
    keys = [n.key for n in nodes]
    assert keys[0] == "cst.art.64", f"CST 64 key={keys[0]!r}"
    assert keys[1] == "ley.50.1990.art.64", f"Ley 50/1990 art 64 key={keys[1]!r}"
    # Critical: distinct keys means MERGE creates two nodes, NOT one.
    assert keys[0] != keys[1]


def test_prose_only_merge_key_still_whole_source_path():
    """Prose-only articles keep their `whole::<source_path>` key — no norm_id
    to derive."""
    a = _make_article(
        article_key="doc",
        article_number="",
        source_path="knowledge_base/CORE ya Arriba/LABORAL_NOMINA/PLAYBOOKS/playbook_pila_aportes.md",
    )
    nodes = _build_article_nodes((a,))
    assert nodes[0].key.startswith("whole::")


def test_suin_merge_key_falls_back_to_article_key():
    """SUIN nodes — `suin_skipped` rule returns no norm_id. MERGE key falls
    back to article.article_key to preserve v6's catalog identity."""
    a = _make_article(
        article_key="1003086",
        article_number="1003086",
        source_path="suin://1003082",
    )
    nodes = _build_article_nodes((a,))
    assert nodes[0].key == "1003086"  # bare article_key, not "suin://..."


def test_other_bucket_merge_key_falls_back_to_article_key():
    """Unknown path → OTHER bucket → no norm_id → MERGE key falls back to
    bare article_key. Identity preserved until a path rule is added."""
    a = _make_article(
        article_key="42",
        article_number="42",
        source_path="some/unknown/path.md",
    )
    nodes = _build_article_nodes((a,))
    assert nodes[0].key == "42"
