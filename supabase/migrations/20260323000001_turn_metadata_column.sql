-- Per-turn enrichment: citations, normative support context, topic routing, confidence.
-- Nullable for pre-existing turns (backwards compatible).
ALTER TABLE conversation_turns
  ADD COLUMN IF NOT EXISTS turn_metadata JSONB DEFAULT NULL;

COMMENT ON COLUMN conversation_turns.turn_metadata IS
  'Per-turn enrichment: citations, normative support context, topic routing, confidence. Nullable for pre-existing turns.';
