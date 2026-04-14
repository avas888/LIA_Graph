-- Active corpus generation registry for Supabase-only Pipeline C.

CREATE TABLE IF NOT EXISTS corpus_generations (
    generation_id TEXT PRIMARY KEY,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    activated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    documents INTEGER NOT NULL DEFAULT 0,
    chunks INTEGER NOT NULL DEFAULT 0,
    countries TEXT[] NOT NULL DEFAULT '{}',
    files TEXT[] NOT NULL DEFAULT '{}',
    knowledge_class_counts JSONB NOT NULL DEFAULT '{}'::jsonb,
    index_dir TEXT NOT NULL DEFAULT '',
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_corpus_generations_single_active
    ON corpus_generations (is_active)
    WHERE is_active = TRUE;

CREATE INDEX IF NOT EXISTS idx_corpus_generations_activated_at
    ON corpus_generations (activated_at DESC);

DROP TRIGGER IF EXISTS trg_corpus_generations_updated ON corpus_generations;
CREATE TRIGGER trg_corpus_generations_updated
    BEFORE UPDATE ON corpus_generations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
