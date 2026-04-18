-- Backfill publish_date/effective_date on document_chunks from parent documents.
-- documents.publish_date is TEXT, document_chunks.publish_date is DATE → need CAST.

-- Phase 1: copy from documents table where format is valid YYYY-MM-DD
UPDATE document_chunks c
SET publish_date   = d.publish_date::date,
    effective_date = COALESCE(d.effective_date, d.publish_date)::date
FROM documents d
WHERE c.doc_id = d.doc_id
  AND c.publish_date IS NULL
  AND d.publish_date IS NOT NULL
  AND d.publish_date ~ '^\d{4}-\d{2}-\d{2}';

-- Phase 2: fix documents that have NULL publish_date
UPDATE documents
SET publish_date   = to_char(CURRENT_DATE, 'YYYY-MM-DD'),
    effective_date = COALESCE(effective_date, to_char(CURRENT_DATE, 'YYYY-MM-DD'))
WHERE publish_date IS NULL
   OR publish_date !~ '^\d{4}-\d{2}-\d{2}';

-- Phase 3: fallback for any chunks still NULL
UPDATE document_chunks
SET publish_date   = CURRENT_DATE,
    effective_date = COALESCE(effective_date, CURRENT_DATE)
WHERE publish_date IS NULL;
