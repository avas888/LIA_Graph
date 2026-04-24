-- ingestionfix_v2 §4 Phase 4 — typed edges on normative_edges.
-- Adds a Spanish-taxonomy ``edge_type`` column and a numeric ``weight``
-- so downstream retrieval can distinguish authoritative statutory
-- references (MODIFICA / DEROGA / CITA, weight 1.0) from operational
-- and interpretive references (PRACTICA_DE / INTERPRETA_A, weight 0.6)
-- and from casual prose mentions (MENCIONA, weight 0.2).
--
-- Both columns are NULLable with sensible defaults so existing rows
-- (written by the pre-fix pipeline, all normativa-sourced) stay valid
-- and can be back-filled asynchronously if desired.

ALTER TABLE normative_edges
    ADD COLUMN IF NOT EXISTS edge_type text,
    ADD COLUMN IF NOT EXISTS weight double precision DEFAULT 1.0;

-- Back-compat constraint: if edge_type is populated it must be one of
-- the Phase-4 taxonomy values. NULL is allowed for legacy rows.
ALTER TABLE normative_edges
    DROP CONSTRAINT IF EXISTS normative_edges_edge_type_check;
ALTER TABLE normative_edges
    ADD CONSTRAINT normative_edges_edge_type_check CHECK (
        edge_type IS NULL
        OR edge_type IN ('MODIFICA', 'DEROGA', 'CITA', 'PRACTICA_DE', 'INTERPRETA_A', 'MENCIONA')
    );

CREATE INDEX IF NOT EXISTS normative_edges_edge_type_idx
    ON normative_edges (edge_type)
    WHERE edge_type IS NOT NULL;
