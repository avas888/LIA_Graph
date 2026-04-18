"""Corpus ingestion scaffolds for the shared regulatory graph."""

from .classifier import ClassifiedEdge, classify_edge_candidates
from .linker import RawEdgeCandidate, extract_edge_candidates
from .loader import (
    GraphLoadExecution,
    GraphLoadPlan,
    build_graph_load_plan,
    load_graph_plan,
    normalize_classified_edges,
)
from .parser import ParsedArticle, parse_article_documents, parse_articles
from .supabase_sink import SupabaseCorpusSink, SupabaseSinkResult, default_generation_id

__all__ = [
    "ClassifiedEdge",
    "GraphLoadExecution",
    "GraphLoadPlan",
    "ParsedArticle",
    "RawEdgeCandidate",
    "SupabaseCorpusSink",
    "SupabaseSinkResult",
    "build_graph_load_plan",
    "classify_edge_candidates",
    "default_generation_id",
    "extract_edge_candidates",
    "load_graph_plan",
    "normalize_classified_edges",
    "parse_article_documents",
    "parse_articles",
]
