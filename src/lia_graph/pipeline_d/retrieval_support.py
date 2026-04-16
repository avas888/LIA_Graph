from __future__ import annotations

from pathlib import Path
import re
import unicodedata
from typing import Any

from ..contracts import Citation, DocumentRecord
from .contracts import GraphPathStep, GraphRetrievalPlan

_STOPWORDS = frozenset(
    {
        "que",
        "como",
        "para",
        "con",
        "sin",
        "del",
        "las",
        "los",
        "una",
        "uno",
        "unos",
        "unas",
        "sobre",
        "entre",
        "segun",
        "según",
        "este",
        "esta",
        "estos",
        "estas",
        "cual",
        "cuales",
        "cuando",
        "donde",
        "desde",
        "hasta",
        "articulo",
        "artículos",
        "articulo",
        "art",
        "et",
        "del",
        "la",
        "el",
        "y",
        "o",
        "u",
    }
)
_SUPPORT_DOC_STOPWORDS = _STOPWORDS | frozenset(
    {
        "cliente",
        "clientes",
        "dian",
        "cuales",
        "cual",
        "son",
        "ante",
        "debe",
        "deben",
        "tiene",
        "tienen",
        "tramite",
        "radicarse",
        "cambia",
        "contribuyente",
        "dia",
        "declaracion",
        "renta",
        "persona",
        "juridica",
        "puedo",
        "pagado",
        "pagados",
    }
)
_MODE_EDGE_PREFERENCES: dict[str, tuple[str, ...]] = {
    "article_lookup": ("REFERENCES", "REQUIRES", "DEFINES"),
    "definition_chain": ("DEFINES", "REFERENCES", "REQUIRES"),
    "obligation_chain": ("REQUIRES", "REFERENCES", "MODIFIES"),
    "computation_chain": ("COMPUTATION_DEPENDS_ON", "REQUIRES", "REFERENCES"),
    "reform_chain": ("MODIFIES", "SUPERSEDES", "REFERENCES"),
    "historical_reform_chain": ("SUPERSEDES", "MODIFIES", "REFERENCES", "REQUIRES"),
    "historical_graph_research": ("SUPERSEDES", "MODIFIES", "REFERENCES", "REQUIRES"),
    "general_graph_research": ("REFERENCES", "REQUIRES", "MODIFIES"),
}
_FAMILY_RANK = {"normativa": 0, "interpretacion": 1, "practica": 2}
_GENERIC_QUERY_TOKENS = frozenset(
    {
        "puedo",
        "declaracion",
        "renta",
        "persona",
        "juridica",
        "pagado",
        "pagados",
        "impuesto",
        "impuestos",
        "ano",
        "gravable",
    }
)
_CONCEPT_BUNDLES: tuple[dict[str, object], ...] = (
    {
        "query_terms": ("ica", "industria y comercio", "avisos y tableros"),
        "article_terms": ("industria y comercio", "avisos y tableros"),
        "boost": 4.8,
    },
    {
        "query_terms": ("gmf", "gravamen a los movimientos financieros", "4x1000", "cuatro por mil"),
        "article_terms": ("gravamen a los movimientos financieros", "movimientos financieros", "cuatro por mil"),
        "boost": 4.8,
    },
    {
        "query_terms": ("beneficio de auditoria",),
        "article_terms": ("beneficio de auditoria", "firmeza acelerada"),
        "boost": 3.4,
    },
    {
        "query_terms": ("devolucion", "compensacion", "auto inadmisorio", "devolucion con garantia"),
        "article_terms": ("devolucion", "compensacion", "saldo a favor", "auto inadmisorio"),
        "boost": 3.1,
    },
    {
        "query_terms": ("compensacion",),
        "article_terms": ("compensacion", "compensar"),
        "boost": 2.7,
    },
    {
        "query_terms": ("firmeza",),
        "article_terms": ("firmeza", "termino de revision", "termino de revisión"),
        "boost": 2.8,
    },
)
_TAX_TREATMENT_QUERY_TERMS = (
    "deducir",
    "deducible",
    "deducibles",
    "deduccion",
    "deducción",
    "procedencia",
    "procedente",
    "impuesto pagado",
    "impuestos pagados",
    "descuento tributario",
    "costo o gasto",
    "costo y gasto",
)
_TAX_TREATMENT_ARTICLE_TERMS = (
    "deduccion de impuestos pagados",
    "deducción de impuestos pagados",
    "impuestos pagados",
    "descuento tributario",
    "costo o gasto",
    "costo y gasto",
    "no podra tomarse como costo o gasto",
    "no podrá tomarse como costo o gasto",
)
_TAX_TREATMENT_STRONG_ARTICLE_TERMS = (
    "deduccion de impuestos pagados",
    "deducción de impuestos pagados",
    "descuento tributario",
    "costo o gasto",
    "costo y gasto",
)


def support_doc_query_tokens(plan: GraphRetrievalPlan) -> tuple[str, ...]:
    tokens: list[str] = []
    for entry in plan.entry_points:
        if entry.kind == "article_search":
            tokens.extend(_tokenize(entry.lookup_value))
        elif entry.kind == "topic":
            tokens.extend(_tokenize(entry.lookup_value.replace("_", " ")))
        elif entry.kind == "article":
            tokens.extend(_tokenize(entry.lookup_value))
        elif entry.kind == "reform":
            tokens.extend(_tokenize(entry.lookup_value.replace("-", " ")))
    return tuple(
        dict.fromkeys(
            token for token in tokens if token and token not in _SUPPORT_DOC_STOPWORDS
        )
    )


def support_doc_query_overlap(row: dict[str, Any], query_tokens: tuple[str, ...]) -> float:
    if not query_tokens:
        return 0.0
    title_tokens = set(
        _tokenize(
            " ".join(
                str(row.get(field) or "")
                for field in ("title_hint", "relative_path", "source_path")
            )
        )
    )
    topic_tokens = set(
        _tokenize(
            " ".join(
                str(row.get(field) or "")
                for field in ("topic_key", "subtopic_key")
            )
        )
    )
    title_hits = sum(1.0 for token in query_tokens if token in title_tokens)
    topic_hits = sum(1.0 for token in query_tokens if token in topic_tokens)
    return title_hits + (topic_hits * 0.35)


def should_keep_connected_article(
    *,
    snapshot: Any,
    article_key: str,
    relation_path: tuple[GraphPathStep, ...],
    plan: GraphRetrievalPlan,
    primary_source_paths: set[str],
    primary_topic_keys: set[str],
) -> bool:
    if not relation_path:
        return True

    article = snapshot.articles.get(article_key) or {}
    source_path = str(article.get("source_path") or "").strip()
    manifest_row = snapshot.docs_by_source_path.get(source_path) or {}
    topic_key = str(manifest_row.get("topic_key") or "").strip()
    hinted_topics = {
        str(topic).strip()
        for topic in plan.topic_hints
        if str(topic or "").strip()
    }
    first_step = relation_path[0]
    supportive_edge = first_step.edge_kind in {
        "REQUIRES",
        "COMPUTATION_DEPENDS_ON",
        "SUPERSEDES",
        "MODIFIES",
        "DEFINES",
    }
    same_primary_source = bool(source_path and source_path in primary_source_paths)
    hinted_topic = bool(topic_key and topic_key in hinted_topics)
    same_primary_topic = bool(topic_key and topic_key in primary_topic_keys)
    parent_source_path = ""
    parent_topic_key = ""
    heading_overlap = False
    if first_step.from_node_kind == "ArticleNode":
        parent_article = snapshot.articles.get(first_step.from_node_key) or {}
        parent_source_path = str(parent_article.get("source_path") or "").strip()
        parent_manifest = snapshot.docs_by_source_path.get(parent_source_path) or {}
        parent_topic_key = str(parent_manifest.get("topic_key") or "").strip()
        heading_overlap = article_heading_overlap(article, parent_article)
    same_parent_source = bool(source_path and source_path == parent_source_path)
    same_parent_topic = bool(topic_key and topic_key == parent_topic_key)

    if plan.temporal_context.historical_query_intent and first_step.edge_kind in {"MODIFIES", "SUPERSEDES"}:
        return any(
            (
                same_parent_source,
                same_parent_topic,
                same_primary_source,
                same_primary_topic,
                hinted_topic,
                heading_overlap,
                article_matches_anchor_reform(article=article, temporal_context=plan.temporal_context)
                is not None,
            )
        )
    if supportive_edge:
        return True
    if first_step.edge_kind == "REFERENCES":
        return same_primary_source or hinted_topic or same_parent_source or heading_overlap
    return same_primary_source or hinted_topic or same_primary_topic


def sorted_neighbors(*, snapshot: Any, node: tuple[str, str], plan: GraphRetrievalPlan) -> tuple[Any, ...]:
    neighbors = snapshot.adjacency.get(node, ())
    preferred = _MODE_EDGE_PREFERENCES.get(plan.query_mode, ())
    edge_rank = {kind: index for index, kind in enumerate(preferred)}
    return tuple(
        sorted(
            neighbors,
            key=lambda neighbor: (
                neighbor_temporal_rank(
                    neighbor=neighbor,
                    temporal_context=plan.temporal_context,
                ),
                edge_rank.get(neighbor.edge.kind, 99),
                neighbor_kind_rank(
                    neighbor=neighbor,
                    temporal_context=plan.temporal_context,
                ),
                neighbor.direction != "out",
                neighbor.other_key,
            ),
        )
    )


def neighbor_bonus(*, plan: GraphRetrievalPlan, neighbor: Any) -> float:
    preferred = _MODE_EDGE_PREFERENCES.get(plan.query_mode, ())
    if neighbor.edge.kind in preferred:
        bonus = float(len(preferred) - preferred.index(neighbor.edge.kind))
    else:
        bonus = 0.5
    if neighbor.other_kind == "ArticleNode":
        bonus += 1.2
    elif neighbor.other_kind == "ReformNode":
        bonus += 0.8
    if neighbor.direction == "out":
        bonus += 0.2
    if neighbor.other_key in set(plan.temporal_context.anchor_reform_keys):
        bonus += 3.0
    cutoff_year = cutoff_year_from_date(plan.temporal_context.cutoff_date)
    if neighbor.other_kind == "ReformNode" and cutoff_year is not None:
        reform_year = reform_year_from_key(neighbor.other_key)
        if reform_year is not None:
            if reform_year <= cutoff_year:
                bonus += 0.9
            elif neighbor.other_key not in set(plan.temporal_context.anchor_reform_keys):
                bonus -= 0.4
    if plan.temporal_context.historical_query_intent and neighbor.edge.kind == "SUPERSEDES":
        bonus += 1.1
    return bonus


def build_relation_path(
    *,
    node: tuple[str, str],
    predecessors: dict[tuple[str, str], tuple[tuple[str, str], Any] | None],
) -> tuple[GraphPathStep, ...]:
    steps: list[GraphPathStep] = []
    current = node
    while True:
        previous = predecessors.get(current)
        if previous is None:
            break
        parent, neighbor = previous
        if neighbor.direction == "out":
            from_node_kind = neighbor.edge.source_kind
            from_node_key = neighbor.edge.source_key
            to_node_kind = neighbor.edge.target_kind
            to_node_key = neighbor.edge.target_key
        else:
            from_node_kind = neighbor.edge.target_kind
            from_node_key = neighbor.edge.target_key
            to_node_kind = neighbor.edge.source_kind
            to_node_key = neighbor.edge.source_key
        steps.append(
            GraphPathStep(
                edge_kind=neighbor.edge.kind,
                direction=neighbor.direction,
                from_node_kind=from_node_kind,
                from_node_key=from_node_key,
                to_node_kind=to_node_kind,
                to_node_key=to_node_key,
            )
        )
        current = parent
    steps.reverse()
    return tuple(steps)


def explain_article_relevance(
    *,
    article: dict[str, Any],
    relation_path: tuple[GraphPathStep, ...],
    plan: GraphRetrievalPlan,
) -> str:
    heading = str(article.get("heading") or "")
    temporal_context = plan.temporal_context
    matched_historical_reform = article_matches_anchor_reform(
        article=article,
        temporal_context=temporal_context,
    )
    if not relation_path:
        fallback_title = heading or f"Art. {article.get('article_key')}"
        if temporal_context.historical_query_intent and matched_historical_reform:
            return f"Anclaje primario del planner con foco histórico previo a {matched_historical_reform}."
        if temporal_context.cutoff_date:
            return f"Anclaje primario del planner para {fallback_title} con corte {temporal_context.cutoff_date}."
        return f"Anclaje primario del planner para {fallback_title}."
    first_step = relation_path[0]
    if temporal_context.historical_query_intent and first_step.to_node_kind == "ReformNode":
        return (
            f"Conectado por {first_step.edge_kind.lower()} hacia el corte histórico "
            f"{first_step.to_node_key} dentro del modo {plan.query_mode}."
        )
    return (
        f"Conectado por {first_step.edge_kind.lower()} desde "
        f"{first_step.from_node_kind.replace('Node', '')} {first_step.from_node_key} "
        f"dentro del modo {plan.query_mode}."
    )


def neighbor_temporal_rank(*, neighbor: Any, temporal_context: Any) -> int:
    anchor_reforms = set(temporal_context.anchor_reform_keys)
    if neighbor.other_key in anchor_reforms:
        return 0
    if temporal_context.historical_query_intent and neighbor.edge.kind == "SUPERSEDES":
        return 1
    cutoff_year = cutoff_year_from_date(temporal_context.cutoff_date)
    reform_year = reform_year_from_key(neighbor.other_key) if neighbor.other_kind == "ReformNode" else None
    if cutoff_year is not None and reform_year is not None and reform_year <= cutoff_year:
        return 2
    if temporal_context.historical_query_intent and neighbor.other_kind == "ReformNode":
        return 3
    return 4


def neighbor_kind_rank(*, neighbor: Any, temporal_context: Any) -> int:
    if temporal_context.historical_query_intent and neighbor.other_kind == "ReformNode":
        return 0
    return 0 if neighbor.other_kind == "ArticleNode" else 1


def article_temporal_bonus(*, article: dict[str, Any], temporal_context: Any) -> float:
    if not article:
        return 0.0
    bonus = 0.0
    status = _normalize_text(str(article.get("status") or ""))
    body = _normalize_text(str(article.get("body") or article.get("full_text") or ""))
    if temporal_context.historical_query_intent and status in {"derogado", "suspendido"}:
        bonus += 1.0
    if temporal_context.historical_query_intent and (
        "texto vigente antes" in body
        or "version anterior" in body
        or "modificacion introducida" in body
    ):
        bonus += 1.2
    if article_matches_anchor_reform(article=article, temporal_context=temporal_context):
        bonus += 2.4
    cutoff_year = cutoff_year_from_date(temporal_context.cutoff_date)
    if cutoff_year is not None and article_has_reform_year_at_or_before(article=article, year=cutoff_year):
        bonus += 0.4
    return bonus


def article_excerpt(*, article: dict[str, Any], temporal_context: Any, limit: int) -> str:
    text = str(article.get("body") or article.get("full_text") or "")
    if temporal_context.historical_query_intent:
        focused = historical_excerpt(text=text, temporal_context=temporal_context, limit=limit)
        if focused:
            return focused
    return snippet(text, limit=limit)


def historical_excerpt(*, text: str, temporal_context: Any, limit: int) -> str | None:
    collapsed = re.sub(r"\s+", " ", str(text or "")).strip()
    if not collapsed:
        return None
    prior_text_match = re.search(
        r"texto vigente antes de la modificaci[oó]n introducida por[^:]*:\s*(.+)",
        collapsed,
        flags=re.IGNORECASE,
    )
    if prior_text_match is not None:
        return snippet(prior_text_match.group(1).strip(), limit=limit)
    needles = list(temporal_context.anchor_reform_labels)
    cutoff_year = cutoff_year_from_date(temporal_context.cutoff_date)
    if cutoff_year is not None:
        needles.append(str(cutoff_year + 1))
    needles.extend(("Texto vigente antes", "versión anterior", "version anterior", "Notas de Vigencia"))
    for needle in needles:
        pattern = re.compile(re.escape(str(needle)), flags=re.IGNORECASE)
        match = pattern.search(collapsed)
        if match is None:
            continue
        start = match.start()
        end = min(len(collapsed), start + limit)
        excerpt = collapsed[start:end].strip()
        if start > 0:
            excerpt = "..." + excerpt
        if end < len(collapsed):
            excerpt = excerpt.rstrip() + "..."
        return excerpt
    return None


def article_matches_anchor_reform(*, article: dict[str, Any], temporal_context: Any) -> str | None:
    if not temporal_context.anchor_reform_labels:
        return None
    article_text = _normalize_text(str(article.get("body") or article.get("full_text") or ""))
    reform_refs = {
        _normalize_text(str(item))
        for item in (article.get("reform_references") or [])
        if str(item or "").strip()
    }
    for label in temporal_context.anchor_reform_labels:
        normalized_label = _normalize_text(label)
        if normalized_label in article_text or normalized_label in reform_refs:
            return label
    return None


def article_has_reform_year_at_or_before(*, article: dict[str, Any], year: int) -> bool:
    for item in article.get("reform_references") or []:
        reform_year = reform_year_from_label(str(item))
        if reform_year is not None and reform_year <= year:
            return True
    return False


def reform_priority_rank(*, reform_key: str, temporal_context: Any) -> tuple[int, int]:
    if reform_key in set(temporal_context.anchor_reform_keys):
        return (0, 0)
    cutoff_year = cutoff_year_from_date(temporal_context.cutoff_date)
    reform_year = reform_year_from_key(reform_key)
    if cutoff_year is not None and reform_year is not None and reform_year <= cutoff_year:
        return (1, abs(cutoff_year - reform_year))
    if temporal_context.historical_query_intent:
        return (2, reform_year or 9999)
    return (3, reform_year or 9999)


def reform_why(*, reform_key: str, temporal_context: Any) -> str:
    if reform_key in set(temporal_context.anchor_reform_keys):
        return "Acto normativo usado como ancla explícita del corte histórico solicitado."
    cutoff_year = cutoff_year_from_date(temporal_context.cutoff_date)
    reform_year = reform_year_from_key(reform_key)
    if cutoff_year is not None and reform_year is not None and reform_year <= cutoff_year:
        return f"Acto normativo priorizado por quedar dentro del corte temporal {cutoff_year}."
    return "Acto normativo conectado a los artículos recuperados."


def cutoff_year_from_date(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(str(value)[:4])
    except ValueError:
        return None


def reform_year_from_key(value: str) -> int | None:
    match = re.search(r"-(\d{4})$", str(value or ""))
    if match is None:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def reform_year_from_label(value: str) -> int | None:
    match = re.search(r"\b(19\d{2}|20\d{2})\b", str(value or ""))
    if match is None:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def manifest_row_to_document(row: dict[str, Any], *, workspace_root: Path) -> DocumentRecord:
    authority = derive_authority(row)
    source_path = str(row.get("source_path") or "")
    return DocumentRecord.from_dict(
        {
            "doc_id": manifest_doc_id(row),
            "relative_path": str(row.get("relative_path") or ""),
            "absolute_path": str((workspace_root / source_path).resolve()) if source_path else "",
            "category": str(row.get("family") or "unknown"),
            "source_type": str(row.get("source_type") or "unknown"),
            "curation_status": str(row.get("canonical_blessing_status") or ""),
            "knowledge_class": str(row.get("knowledge_class") or ""),
            "topic": str(row.get("topic_key") or "unknown"),
            "authority": authority,
            "pais": "colombia",
            "tema": str(row.get("topic_key") or ""),
            "subtema": str(row.get("subtopic_key") or ""),
            "primary_role": str(row.get("family") or ""),
            "notes": str(row.get("title_hint") or ""),
        }
    )


def manifest_doc_id(row: dict[str, Any]) -> str:
    relative_path = str(row.get("relative_path") or row.get("source_path") or "")
    stem = Path(relative_path).stem.lower()
    slug = re.sub(r"[^a-z0-9]+", "_", stem).strip("_")
    topic_key = str(row.get("topic_key") or "doc").strip().lower()
    return f"{topic_key}_{slug}" if slug else topic_key or "doc"


def derive_authority(row: dict[str, Any]) -> str:
    source_type = str(row.get("source_type") or "").strip().lower()
    knowledge_class = str(row.get("knowledge_class") or "").strip().lower()
    if source_type.startswith("official") or knowledge_class == "normative_base":
        return "DIAN / fuente oficial"
    if knowledge_class == "practica_erp":
        return "Loggro"
    if knowledge_class == "interpretative_guidance":
        return "Fuente expertos"
    return "Fuente documental"


def lexical_article_matches(
    *,
    snapshot: Any,
    query: str,
    topic_hints: tuple[str, ...],
    limit: int,
) -> tuple[tuple[str, float], ...]:
    normalized_query = _normalize_text(query)
    tokens = [token for token in _tokenize(query) if token not in _STOPWORDS]
    if not tokens:
        return ()
    specific_tokens = [token for token in tokens if token not in _GENERIC_QUERY_TOKENS]
    generic_tokens = [token for token in tokens if token in _GENERIC_QUERY_TOKENS]
    active_concepts = _active_concept_bundles(normalized_query)
    has_specific_query_signal = bool(specific_tokens or active_concepts)
    has_tax_treatment_signal = any(
        _phrase_in_text(term, normalized_query) for term in _TAX_TREATMENT_QUERY_TERMS
    )
    asks_about_sanctions = any(
        _phrase_in_text(term, normalized_query)
        for term in ("sancion", "sanción", "multa", "penalidad")
    )
    asks_about_inadmissory = any(
        _phrase_in_text(term, normalized_query)
        for term in ("inadmisorio", "inadmisoria")
    )
    asks_about_guarantee = any(
        _phrase_in_text(term, normalized_query)
        for term in ("garantia", "garantía")
    )
    scored: list[tuple[str, float]] = []
    topic_hints_set = set(topic_hints)
    for article_key, article in snapshot.articles.items():
        haystack_heading = _normalize_text(str(article.get("heading") or ""))
        haystack_body = _normalize_text(str(article.get("body") or article.get("full_text") or ""))
        heading_tokens = set(_tokenize(haystack_heading))
        body_tokens = set(_tokenize(haystack_body))
        score = 0.0
        exact_specific_hits = 0
        treatment_bonus = _tax_treatment_bonus(
            normalized_query=normalized_query,
            haystack_heading=haystack_heading,
            haystack_body=haystack_body,
        )
        concept_boost = _concept_bundle_boost(
            active_concepts=active_concepts,
            haystack_heading=haystack_heading,
            haystack_body=haystack_body,
            heading_tokens=heading_tokens,
            body_tokens=body_tokens,
        )
        title_alignment_bonus = _title_alignment_bonus(
            normalized_query=normalized_query,
            specific_tokens=tuple(specific_tokens),
            heading_tokens=heading_tokens,
            haystack_heading=haystack_heading,
        )
        for token in specific_tokens:
            if token in heading_tokens:
                score += 2.2
                exact_specific_hits += 1
            elif token in body_tokens:
                score += 1.2
                exact_specific_hits += 1
        for token in generic_tokens:
            if token in heading_tokens:
                score += 0.4
            elif token in body_tokens:
                score += 0.15
        score += concept_boost
        score += treatment_bonus
        score += title_alignment_bonus
        manifest_row = snapshot.docs_by_source_path.get(str(article.get("source_path") or ""))
        topic_key = str(manifest_row.get("topic_key") or "").strip() if manifest_row else ""
        if topic_key and topic_key in topic_hints_set:
            score += 1.1 if (exact_specific_hits or concept_boost) else 0.25
        if not asks_about_sanctions and (
            _phrase_in_text("sancion", haystack_heading) or _phrase_in_text("sancion", haystack_body)
        ):
            score -= 8.0
        if not asks_about_inadmissory and _phrase_in_text("inadmisorio", haystack_heading):
            score -= 4.5
        if not asks_about_guarantee and _phrase_in_text("garantia", haystack_heading):
            score -= 4.0
        if has_tax_treatment_signal and concept_boost > 0.0 and treatment_bonus <= 0.0:
            score -= 2.4
        if has_specific_query_signal and not exact_specific_hits and concept_boost <= 0.0:
            score -= 0.9
        if score <= 0.0:
            continue
        scored.append((article_key, score))
    scored.sort(key=lambda item: (-item[1], item[0]))
    return tuple(scored[:limit])


def _active_concept_bundles(normalized_query: str) -> tuple[dict[str, object], ...]:
    active: list[dict[str, object]] = []
    for bundle in _CONCEPT_BUNDLES:
        if any(_phrase_in_text(str(term), normalized_query) for term in bundle["query_terms"]):
            active.append(bundle)
    return tuple(active)


def _concept_bundle_boost(
    *,
    active_concepts: tuple[dict[str, object], ...],
    haystack_heading: str,
    haystack_body: str,
    heading_tokens: set[str],
    body_tokens: set[str],
) -> float:
    boost = 0.0
    for bundle in active_concepts:
        article_terms = tuple(str(term) for term in bundle["article_terms"])
        if any(
            _term_matches_article(
                term=term,
                haystack_heading=haystack_heading,
                haystack_body=haystack_body,
                heading_tokens=heading_tokens,
                body_tokens=body_tokens,
            )
            for term in article_terms
        ):
            boost += float(bundle["boost"])
    return boost


def _title_alignment_bonus(
    *,
    normalized_query: str,
    specific_tokens: tuple[str, ...],
    heading_tokens: set[str],
    haystack_heading: str,
) -> float:
    query_token_set = {token for token in specific_tokens if token and token not in _GENERIC_QUERY_TOKENS}
    if len(query_token_set) < 2 or not heading_tokens:
        return 0.0
    if _phrase_in_text(normalized_query, haystack_heading):
        return 4.4
    overlap = len(query_token_set.intersection(heading_tokens))
    if overlap <= 0:
        return 0.0
    coverage = overlap / max(1, len(query_token_set))
    if coverage >= 0.85 and overlap >= 3:
        return 3.4
    if coverage >= 0.65 and overlap >= 3:
        return 2.2
    if coverage >= 0.5 and overlap >= 2:
        return 1.1
    return 0.0


def _tax_treatment_bonus(
    *,
    normalized_query: str,
    haystack_heading: str,
    haystack_body: str,
) -> float:
    if not any(_phrase_in_text(term, normalized_query) for term in _TAX_TREATMENT_QUERY_TERMS):
        return 0.0
    heading_strong_hits = sum(
        1 for term in _TAX_TREATMENT_STRONG_ARTICLE_TERMS if _phrase_in_text(term, haystack_heading)
    )
    body_strong_hits = sum(
        1 for term in _TAX_TREATMENT_STRONG_ARTICLE_TERMS if _phrase_in_text(term, haystack_body)
    )
    total_hits = sum(
        1
        for term in _TAX_TREATMENT_ARTICLE_TERMS
        if _phrase_in_text(term, haystack_heading) or _phrase_in_text(term, haystack_body)
    )
    if heading_strong_hits >= 1:
        return 4.2
    if body_strong_hits >= 1 and total_hits >= 2:
        return 3.4
    if total_hits >= 3:
        return 2.2
    return 0.0


def _term_matches_article(
    *,
    term: str,
    haystack_heading: str,
    haystack_body: str,
    heading_tokens: set[str],
    body_tokens: set[str],
) -> bool:
    normalized_term = _normalize_text(term)
    if " " in normalized_term:
        return _phrase_in_text(normalized_term, haystack_heading) or _phrase_in_text(
            normalized_term, haystack_body
        )
    return normalized_term in heading_tokens or normalized_term in body_tokens


def _phrase_in_text(phrase: str, text: str) -> bool:
    normalized_phrase = _normalize_text(phrase)
    if not normalized_phrase or not text:
        return False
    pattern = re.compile(rf"(?<![a-z0-9]){re.escape(normalized_phrase)}(?![a-z0-9])")
    return pattern.search(text) is not None


def article_heading_overlap(article: dict[str, Any], other_article: dict[str, Any]) -> bool:
    left = {
        token
        for token in _tokenize(str(article.get("heading") or ""))
        if token not in _STOPWORDS and not token.isdigit()
    }
    right = {
        token
        for token in _tokenize(str(other_article.get("heading") or ""))
        if token not in _STOPWORDS and not token.isdigit()
    }
    return bool(left and right and left.intersection(right))


def _tokenize(value: str) -> tuple[str, ...]:
    return tuple(token for token in re.split(r"[^a-z0-9]+", _normalize_text(value)) if len(token) >= 3)


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_text).strip().lower()


def snippet(text: str, *, limit: int) -> str:
    collapsed = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: max(0, limit - 3)].rstrip() + "..."


__all__ = [
    "_FAMILY_RANK",
    "article_excerpt",
    "article_heading_overlap",
    "article_temporal_bonus",
    "build_relation_path",
    "explain_article_relevance",
    "lexical_article_matches",
    "manifest_row_to_document",
    "neighbor_bonus",
    "reform_priority_rank",
    "reform_why",
    "should_keep_connected_article",
    "snippet",
    "sorted_neighbors",
    "support_doc_query_overlap",
    "support_doc_query_tokens",
]
