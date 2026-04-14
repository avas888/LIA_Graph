-- Durable cache for normalized query embeddings.

CREATE TABLE IF NOT EXISTS query_embedding_cache (
    cache_key       TEXT PRIMARY KEY,
    normalized_text TEXT NOT NULL DEFAULT '',
    embedding       JSONB NOT NULL DEFAULT '[]',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_query_embedding_cache_updated
    ON query_embedding_cache (updated_at DESC);

DROP TRIGGER IF EXISTS trg_query_embedding_cache_updated ON query_embedding_cache;
CREATE TRIGGER trg_query_embedding_cache_updated
    BEFORE UPDATE ON query_embedding_cache
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
