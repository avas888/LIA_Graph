-- Add publish_date and effective_date to document_chunks
-- so governance scoring can compute freshness without joining documents.
ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS publish_date DATE;
ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS effective_date DATE;
