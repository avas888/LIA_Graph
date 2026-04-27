-- fixplan_v3 §0.3.1 Table 3 + §0.3.4 step 3.
--
-- Link table from corpus chunks to cited norms. Replaces the chunk-level
-- `vigencia` column entirely once the deprecation cycle ships.
--
-- Reversibility: R3 — `DROP TABLE norm_citations CASCADE`.

CREATE TABLE IF NOT EXISTS public.norm_citations (
    citation_id     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    chunk_id        text NOT NULL,
    norm_id         text NOT NULL REFERENCES public.norms(norm_id) ON DELETE CASCADE,
    mention_span    int4range,
    role            text NOT NULL,
    anchor_strength text NOT NULL,
    extracted_at    timestamptz NOT NULL DEFAULT now(),
    extracted_via   text NOT NULL,

    CONSTRAINT nc_role_valid CHECK (
        role IN ('anchor', 'reference', 'comparator', 'historical')
    ),
    CONSTRAINT nc_anchor_strength_valid CHECK (
        anchor_strength IN ('ley', 'decreto', 'res_dian', 'concepto_dian', 'jurisprudencia')
    )
);

-- chunk_id → document_chunks.chunk_id (FK kept loose because the
-- canonicalizer backfill may run before all chunks are ingested in some envs).
-- Promote to a hard FK in a follow-up migration after backfill completes.

CREATE INDEX IF NOT EXISTS idx_nc_chunk
    ON public.norm_citations(chunk_id);
CREATE INDEX IF NOT EXISTS idx_nc_norm_role
    ON public.norm_citations(norm_id, role);
-- The UNIQUE index is the conflict target for the backfill loop's UPSERT
-- (`ON CONFLICT (chunk_id, norm_id, role)`). Discovered the hard way during
-- the live integration smoke 2026-04-27 — ON CONFLICT requires a unique
-- constraint, not just any index.
CREATE UNIQUE INDEX IF NOT EXISTS uq_nc_chunk_norm_role
    ON public.norm_citations(chunk_id, norm_id, role);

COMMENT ON TABLE public.norm_citations IS
    'fixplan_v3 §0.3.1 Table 3 — link from document_chunks to cited norms (with role + anchor strength).';
