-- Phase 3: Document chunks table for indexed retrieval
-- Replaces artifacts/document_index.jsonl (~25K chunks, 114MB)

CREATE TABLE document_chunks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_id          TEXT NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
    chunk_id        TEXT UNIQUE,
    chunk_text      TEXT NOT NULL,
    summary         TEXT,
    concept_tags    TEXT[] NOT NULL DEFAULT '{}',
    chunk_start     INTEGER,
    chunk_end       INTEGER,
    chunk_sha256    TEXT UNIQUE,

    -- Retrieval metadata
    source_type     TEXT,
    curation_status TEXT,
    topic           TEXT,
    pais            TEXT DEFAULT 'colombia',
    authority       TEXT,
    vigencia        TEXT,
    retrieval_visibility TEXT,
    lane_scores     JSONB,

    -- FTS column — populated by trigger (to_tsvector is not immutable)
    search_vector   tsvector,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Trigger to auto-populate search_vector on INSERT/UPDATE
CREATE OR REPLACE FUNCTION chunks_search_vector_trigger()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector := to_tsvector('spanish',
        coalesce(array_to_string(NEW.concept_tags, ' '), '') || ' ' ||
        coalesce(NEW.summary, '') || ' ' ||
        coalesce(NEW.chunk_text, '')
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_chunks_search_vector
    BEFORE INSERT OR UPDATE ON document_chunks
    FOR EACH ROW EXECUTE FUNCTION chunks_search_vector_trigger();

-- Indexes for retrieval
CREATE INDEX idx_chunks_doc_id          ON document_chunks (doc_id);
CREATE INDEX idx_chunks_topic_pais      ON document_chunks (topic, pais, curation_status, retrieval_visibility);
CREATE INDEX idx_chunks_search_vector   ON document_chunks USING GIN (search_vector);
CREATE INDEX idx_chunks_concept_tags    ON document_chunks USING GIN (concept_tags);
CREATE INDEX idx_chunks_sha256          ON document_chunks (chunk_sha256);

-- Retrieval analytics
CREATE TABLE retrieval_events (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trace_id     TEXT NOT NULL,
    query_text   TEXT NOT NULL,
    cascade_mode TEXT NOT NULL,
    top_k        INTEGER NOT NULL,
    results      JSONB NOT NULL DEFAULT '[]',
    latency_ms   INTEGER NOT NULL,
    retriever    TEXT NOT NULL DEFAULT 'jsonl',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_retrieval_events_created ON retrieval_events (created_at);
CREATE INDEX idx_retrieval_events_trace   ON retrieval_events (trace_id);
