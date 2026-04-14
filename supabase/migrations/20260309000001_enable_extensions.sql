-- Enable required PostgreSQL extensions for LIA Contador
-- vector: pgvector for future semantic search (Phase 5)
-- unaccent: accent-insensitive search for Spanish text
-- pg_trgm: trigram similarity for fuzzy matching

CREATE EXTENSION IF NOT EXISTS "vector"    SCHEMA extensions;
CREATE EXTENSION IF NOT EXISTS "unaccent"  SCHEMA extensions;
CREATE EXTENSION IF NOT EXISTS "pg_trgm"   SCHEMA extensions;
