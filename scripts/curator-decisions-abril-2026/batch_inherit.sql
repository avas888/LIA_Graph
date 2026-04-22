-- Batch-inherit SQL updates (case c): sibling triplets share a subtopic
-- Generated: 2026-04-21
-- Run AFTER parent_topic_corrections.sql and AFTER applying alias_additions.json + new_subtopics.json

-- Pattern: %/LEYES/OTROS_SECTORIALES/%
-- Parent topic: otros_sectoriales
-- Target subtopic: cumplimiento_normativo_sectorial_pymes
-- Affected docs: 353 (flagged rows 136-488)
UPDATE documents
SET parent_topic_key = 'otros_sectoriales',
    subtema = 'cumplimiento_normativo_sectorial_pymes'
WHERE relative_path LIKE '%/LEYES/OTROS_SECTORIALES/%'
  AND subtema IS NULL;

