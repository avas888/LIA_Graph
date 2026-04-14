-- Materialized normative relationship edges extracted from document_chunks
-- metadata (normative_refs, mentioned_reference_keys) and seeded from
-- _CROSS_DOMAIN_RELATIONS rules. Queried by recursive CTE in planner.

CREATE TABLE IF NOT EXISTS normative_edges (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_key  text NOT NULL,
    target_key  text NOT NULL,
    relation    text NOT NULL DEFAULT 'references',
    source_chunk_id bigint,
    confidence  float NOT NULL DEFAULT 1.0,
    generation_id text,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_normative_edges_source     ON normative_edges (source_key);
CREATE INDEX idx_normative_edges_target     ON normative_edges (target_key);
CREATE INDEX idx_normative_edges_generation ON normative_edges (generation_id);

ALTER TABLE normative_edges ENABLE ROW LEVEL SECURITY;

CREATE POLICY normative_edges_read_all ON normative_edges
    FOR SELECT USING (true);

CREATE POLICY normative_edges_service_write ON normative_edges
    FOR ALL USING (auth.role() = 'service_role');
