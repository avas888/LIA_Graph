ALTER TABLE documents
    ADD COLUMN IF NOT EXISTS applicability_kind TEXT,
    ADD COLUMN IF NOT EXISTS ag_from_year INTEGER,
    ADD COLUMN IF NOT EXISTS ag_to_year INTEGER,
    ADD COLUMN IF NOT EXISTS filing_from_year INTEGER,
    ADD COLUMN IF NOT EXISTS filing_to_year INTEGER;

CREATE INDEX IF NOT EXISTS idx_documents_ag_from_year ON documents (ag_from_year);
CREATE INDEX IF NOT EXISTS idx_documents_ag_to_year ON documents (ag_to_year);
