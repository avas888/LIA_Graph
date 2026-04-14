from .llm import LLMAdapter
from .retriever import RetrieverAdapter

# SupabaseRetriever is lazy-loaded to avoid circular imports:
# adapters -> pipeline_c -> orchestrator -> llm_runtime -> adapters
def __getattr__(name: str):
    if name == "SupabaseRetriever":
        from lia_contador.pipeline_c.supabase_fetch import SupabaseRetriever
        globals()["SupabaseRetriever"] = SupabaseRetriever
        return SupabaseRetriever
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["LLMAdapter", "RetrieverAdapter", "SupabaseRetriever"]
