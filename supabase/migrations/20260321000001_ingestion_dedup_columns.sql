-- Dedup support columns for ingestion
ALTER TABLE documents
  ADD COLUMN IF NOT EXISTS corpus text,
  ADD COLUMN IF NOT EXISTS content_hash text,
  ADD COLUMN IF NOT EXISTS filename_normalized text,
  ADD COLUMN IF NOT EXISTS first_heading text;

CREATE INDEX IF NOT EXISTS idx_documents_content_hash
  ON documents (content_hash) WHERE content_hash IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_documents_filename_normalized
  ON documents (corpus, filename_normalized) WHERE filename_normalized IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_documents_first_heading
  ON documents (corpus, first_heading) WHERE first_heading IS NOT NULL;
