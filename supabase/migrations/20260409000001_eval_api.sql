-- Robot API v1: service accounts + eval tables
-- Migration: 20260409000001_eval_api.sql

-- ── service_accounts ──
CREATE TABLE IF NOT EXISTS service_accounts (
    service_account_id TEXT PRIMARY KEY,
    tenant_id          TEXT NOT NULL,
    display_name       TEXT NOT NULL,
    role               TEXT NOT NULL DEFAULT 'eval_robot',
    status             TEXT NOT NULL DEFAULT 'active',
    secret_hash        TEXT NOT NULL DEFAULT '',
    secret_hint        TEXT NOT NULL DEFAULT '',
    scopes             TEXT[] NOT NULL DEFAULT '{"eval:read","eval:write","chat:ask"}',
    rate_limit_profile TEXT NOT NULL DEFAULT 'eval_robot',
    metadata           JSONB NOT NULL DEFAULT '{}',
    created_by         TEXT NOT NULL DEFAULT '',
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_used_at       TIMESTAMPTZ,
    expires_at         TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_service_accounts_tenant
    ON service_accounts (tenant_id);
CREATE INDEX IF NOT EXISTS idx_service_accounts_status
    ON service_accounts (status);

-- ── eval_runs ──
CREATE TABLE IF NOT EXISTS eval_runs (
    eval_run_id   TEXT PRIMARY KEY,
    tenant_id     TEXT NOT NULL,
    label         TEXT NOT NULL,
    description   TEXT NOT NULL DEFAULT '',
    dataset_id    TEXT NOT NULL DEFAULT '',
    status        TEXT NOT NULL DEFAULT 'created',
    config        JSONB NOT NULL DEFAULT '{}',
    tags          TEXT[] NOT NULL DEFAULT '{}',
    metadata      JSONB NOT NULL DEFAULT '{}',
    stats         JSONB NOT NULL DEFAULT '{}',
    created_by    TEXT NOT NULL DEFAULT '',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at  TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_eval_runs_tenant
    ON eval_runs (tenant_id);
CREATE INDEX IF NOT EXISTS idx_eval_runs_label
    ON eval_runs (label);
CREATE INDEX IF NOT EXISTS idx_eval_runs_status
    ON eval_runs (status);

-- ── eval_turns ──
CREATE TABLE IF NOT EXISTS eval_turns (
    eval_turn_id            TEXT PRIMARY KEY,
    eval_run_id             TEXT NOT NULL REFERENCES eval_runs(eval_run_id) ON DELETE CASCADE,
    question_id             TEXT NOT NULL DEFAULT '',
    message                 TEXT NOT NULL,
    topic                   TEXT NOT NULL DEFAULT '',
    pais                    TEXT NOT NULL DEFAULT 'colombia',
    config                  JSONB NOT NULL DEFAULT '{}',
    status                  TEXT NOT NULL DEFAULT 'pending',
    pipeline_run_id         TEXT,
    response                JSONB NOT NULL DEFAULT '{}',
    retrieval_trace         JSONB NOT NULL DEFAULT '{}',
    retrieval_trace_summary JSONB NOT NULL DEFAULT '{}',
    error                   TEXT NOT NULL DEFAULT '',
    latency_ms              DOUBLE PRECISION,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at            TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_eval_turns_run
    ON eval_turns (eval_run_id);
CREATE INDEX IF NOT EXISTS idx_eval_turns_question
    ON eval_turns (question_id);

-- ── eval_reviews ──
CREATE TABLE IF NOT EXISTS eval_reviews (
    eval_review_id  TEXT PRIMARY KEY,
    eval_turn_id    TEXT NOT NULL REFERENCES eval_turns(eval_turn_id) ON DELETE CASCADE,
    eval_run_id     TEXT NOT NULL REFERENCES eval_runs(eval_run_id) ON DELETE CASCADE,
    reviewer        TEXT NOT NULL DEFAULT '',
    scores          JSONB NOT NULL DEFAULT '{}',
    overall_score   DOUBLE PRECISION,
    verdict         TEXT NOT NULL DEFAULT '',
    flags           TEXT[] NOT NULL DEFAULT '{}',
    comment         TEXT NOT NULL DEFAULT '',
    metadata        JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_eval_reviews_turn
    ON eval_reviews (eval_turn_id);
CREATE INDEX IF NOT EXISTS idx_eval_reviews_run
    ON eval_reviews (eval_run_id);

-- ── eval_rankings ──
CREATE TABLE IF NOT EXISTS eval_rankings (
    eval_ranking_id TEXT PRIMARY KEY,
    eval_run_id     TEXT NOT NULL REFERENCES eval_runs(eval_run_id) ON DELETE CASCADE,
    question_id     TEXT NOT NULL DEFAULT '',
    ranker          TEXT NOT NULL DEFAULT '',
    candidates      JSONB NOT NULL DEFAULT '[]',
    criteria        TEXT NOT NULL DEFAULT '',
    rationale       TEXT NOT NULL DEFAULT '',
    metadata        JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_eval_rankings_run
    ON eval_rankings (eval_run_id);

-- ── eval_diagnoses ──
CREATE TABLE IF NOT EXISTS eval_diagnoses (
    eval_diagnosis_id TEXT PRIMARY KEY,
    eval_run_id       TEXT NOT NULL REFERENCES eval_runs(eval_run_id) ON DELETE CASCADE,
    eval_turn_id      TEXT REFERENCES eval_turns(eval_turn_id) ON DELETE SET NULL,
    diagnoser         TEXT NOT NULL DEFAULT '',
    category          TEXT NOT NULL DEFAULT '',
    severity          TEXT NOT NULL DEFAULT 'medium',
    title             TEXT NOT NULL DEFAULT '',
    description       TEXT NOT NULL DEFAULT '',
    affected_stages   TEXT[] NOT NULL DEFAULT '{}',
    recommendation    TEXT NOT NULL DEFAULT '',
    evidence          JSONB NOT NULL DEFAULT '{}',
    metadata          JSONB NOT NULL DEFAULT '{}',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_eval_diagnoses_run
    ON eval_diagnoses (eval_run_id);
CREATE INDEX IF NOT EXISTS idx_eval_diagnoses_category
    ON eval_diagnoses (category);
CREATE INDEX IF NOT EXISTS idx_eval_diagnoses_turn
    ON eval_diagnoses (eval_turn_id);

-- ── RLS policies ──
ALTER TABLE service_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE eval_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE eval_turns ENABLE ROW LEVEL SECURITY;
ALTER TABLE eval_reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE eval_rankings ENABLE ROW LEVEL SECURITY;
ALTER TABLE eval_diagnoses ENABLE ROW LEVEL SECURITY;
