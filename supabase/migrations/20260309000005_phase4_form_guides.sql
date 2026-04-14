-- Phase 4: Form guides and binary assets
-- Replaces filesystem discovery in form_guides/loader.py

CREATE TABLE form_guides (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reference_key   TEXT NOT NULL,
    form_version    TEXT,
    profile_id      TEXT,
    title           TEXT,
    description     TEXT,
    guide_data      JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (reference_key, form_version, profile_id)
);

CREATE TABLE form_hotspots (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    guide_id        UUID NOT NULL REFERENCES form_guides(id) ON DELETE CASCADE,
    casilla         TEXT NOT NULL,
    field_name      TEXT,
    bbox_x          REAL,
    bbox_y          REAL,
    bbox_w          REAL,
    bbox_h          REAL,
    page_number     INTEGER,
    tooltip         TEXT,
    help_text       TEXT,
    validation_rule TEXT,
    data_type       TEXT,
    required        BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_form_guides_ref_key    ON form_guides (reference_key);
CREATE INDEX idx_form_hotspots_guide    ON form_hotspots (guide_id);
CREATE INDEX idx_form_hotspots_casilla  ON form_hotspots (casilla);

CREATE TRIGGER trg_form_guides_updated
    BEFORE UPDATE ON form_guides
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
