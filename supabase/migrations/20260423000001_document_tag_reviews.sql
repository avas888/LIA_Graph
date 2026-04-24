-- ingestionfix_v2 §4 Phase 7 — document tag review queue.
-- One row per (doc_id, review cycle). The sink/classifier inserts a
-- skeleton row (decision_action IS NULL) whenever a doc classifies with
-- low confidence or proposes a new subtopic; an expert later PATCHes the
-- row with a decision via POST /api/tags/review/{doc_id}/decision.

CREATE TABLE IF NOT EXISTS document_tag_reviews (
    review_id            text PRIMARY KEY,
    doc_id               text NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
    -- Snapshot of the classifier verdict that triggered this review. Keeps
    -- the queue row self-contained even if the documents row is later
    -- updated by a delta.
    trigger_reason       text NOT NULL CHECK (
        trigger_reason IN (
            'low_confidence',
            'requires_review_flag',
            'new_subtopic_proposed',
            'manual'
        )
    ),
    snapshot_topic       text,
    snapshot_subtopic    text,
    snapshot_confidence  double precision,

    -- LLM-backed brief, generated on demand.
    report_id            text,
    report_markdown      text,
    report_generated_at  timestamptz,

    -- Expert decision (NULL until decided).
    decision_action      text CHECK (
        decision_action IN (
            'approve',
            'override',
            'promote_new_subtopic',
            'reject'
        )
    ),
    decision_payload     jsonb,
    decided_by           text,
    decided_at           timestamptz,

    created_at           timestamptz NOT NULL DEFAULT now(),
    updated_at           timestamptz NOT NULL DEFAULT now()
);

-- Fast path: list pending reviews ordered by recency.
CREATE INDEX IF NOT EXISTS document_tag_reviews_pending_idx
    ON document_tag_reviews (created_at DESC)
    WHERE decided_at IS NULL;

CREATE INDEX IF NOT EXISTS document_tag_reviews_doc_idx
    ON document_tag_reviews (doc_id);

-- Only one open (undecided) review per doc. Keeps the queue from
-- duplicating when a doc re-classifies multiple times while still open.
CREATE UNIQUE INDEX IF NOT EXISTS document_tag_reviews_open_unique_idx
    ON document_tag_reviews (doc_id)
    WHERE decided_at IS NULL;
