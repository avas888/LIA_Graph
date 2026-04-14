SET LOCAL search_path = public, extensions;

-- Phase 5: Embedding column + HNSW index for semantic search
-- Requires pgvector extension (already enabled in migration 000001)

ALTER TABLE document_chunks
    ADD COLUMN embedding vector(768);

-- HNSW index for approximate nearest neighbor search
-- m=16, ef_construction=64 are good defaults for ~1K vectors
CREATE INDEX idx_chunks_embedding ON document_chunks
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
