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

__all__ = [
    "ClassifiedEdge",
    "GraphLoadExecution",
    "GraphLoadPlan",
    "ParsedArticle",
    "RawEdgeCandidate",
    "build_graph_load_plan",
    "classify_edge_candidates",
    "extract_edge_candidates",
    "load_graph_plan",
    "normalize_classified_edges",
    "parse_article_documents",
    "parse_articles",
]
