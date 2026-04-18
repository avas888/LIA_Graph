-- Phase 2: Document manifest as structured table
-- Source: DocumentRecord dataclass (contracts/document.py)
-- Source: document_manifest.csv (33 columns, 985 rows)

CREATE TYPE vigencia_status AS ENUM ('vigente', 'derogada', 'proyecto', 'desconocida');
CREATE TYPE curation_status AS ENUM ('curated', 'reviewed', 'raw', 'deprecated');

CREATE TABLE documents (
    doc_id                    TEXT PRIMARY KEY,
    relative_path             TEXT NOT NULL,
    source_type               TEXT NOT NULL DEFAULT 'unknown',
    topic                     TEXT NOT NULL DEFAULT 'unknown',
    authority                 TEXT NOT NULL DEFAULT 'unknown',
    pais                      TEXT NOT NULL DEFAULT 'colombia',
    locale                    TEXT DEFAULT 'es-CO',

    -- Classification
    knowledge_class           TEXT,
    jurisdiccion              TEXT,
    tema                      TEXT,
    subtema                   TEXT,
    tipo_de_accion            TEXT,
    tipo_de_riesgo            TEXT,
    tipo_de_documento         TEXT,
    nivel_practicidad         TEXT,

    -- Lifecycle
    vigencia                  vigencia_status DEFAULT 'desconocida',
    autoridad                 TEXT,
    publish_date              TEXT,
    effective_date            TEXT,
    status                    TEXT,
    review_cadence            TEXT,
    superseded_by             TEXT,
    curation_status           curation_status,

    -- References & relations
    entity_id                 TEXT,
    entity_type               TEXT,
    relation_type             TEXT,
    reference_identity_keys   TEXT[] NOT NULL DEFAULT '{}',
    mentioned_reference_keys  TEXT[] NOT NULL DEFAULT '{}',
    concept_tags              TEXT[] NOT NULL DEFAULT '{}',
    normative_refs            TEXT[] NOT NULL DEFAULT '{}',
    topic_domains             TEXT[] NOT NULL DEFAULT '{}',
    admissible_surfaces       TEXT[] NOT NULL DEFAULT '{}',
    supports_fields           TEXT[] NOT NULL DEFAULT '{}',

    -- Storage & retrieval
    storage_partition         TEXT,
    url                       TEXT,
    notes                     TEXT,
    cross_topic               BOOLEAN NOT NULL DEFAULT FALSE,

    -- Metadata
    created_at                TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for retrieval pre-filter
CREATE INDEX idx_documents_topic       ON documents (topic);
CREATE INDEX idx_documents_pais        ON documents (pais);
CREATE INDEX idx_documents_vigencia    ON documents (vigencia);
CREATE INDEX idx_documents_curation    ON documents (curation_status);
CREATE INDEX idx_documents_authority   ON documents (authority);
CREATE INDEX idx_documents_concept_tags ON documents USING GIN (concept_tags);

CREATE TRIGGER trg_documents_updated
    BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
