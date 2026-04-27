-- fixplan_v3 §0.3.1 Table 1 + §0.3.4 step 1.
--
-- Catalog of every legal artifact ever cited or extracted. Insert-only at
-- ingest time; rows are never deleted (a norm that disappears legally still
-- has a history). Sub-units are first-class rows per §0.5.3.
--
-- Reversibility: R3 — `DROP TABLE norms CASCADE` (see state_fixplan_v3.md
-- §5.1). Empty at creation time, so DOWN is trivial.

CREATE TABLE IF NOT EXISTS public.norms (
    norm_id          text PRIMARY KEY,
    norm_type        text NOT NULL,
    parent_norm_id   text REFERENCES public.norms(norm_id) ON DELETE SET NULL,
    display_label    text NOT NULL,
    emisor           text NOT NULL,
    fecha_emision    date,
    canonical_url    text,
    is_sub_unit      boolean NOT NULL DEFAULT false,
    sub_unit_kind    text,
    created_at       timestamptz NOT NULL DEFAULT now(),
    notes            text,

    CONSTRAINT norms_norm_type_valid CHECK (norm_type IN (
        'estatuto', 'articulo_et',
        'ley', 'ley_articulo',
        'decreto', 'decreto_articulo',
        'resolucion', 'res_articulo',
        'concepto_dian', 'concepto_dian_numeral',
        'sentencia_cc', 'auto_ce', 'sentencia_ce',
        'unknown'
    )),
    CONSTRAINT norms_sub_unit_kind_valid CHECK (
        sub_unit_kind IS NULL OR sub_unit_kind IN ('parágrafo', 'inciso', 'numeral', 'literal')
    ),
    CONSTRAINT norms_sub_unit_consistency CHECK (
        (is_sub_unit = false AND sub_unit_kind IS NULL)
        OR (is_sub_unit = true AND sub_unit_kind IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_norms_parent ON public.norms(parent_norm_id);
CREATE INDEX IF NOT EXISTS idx_norms_type   ON public.norms(norm_type);
CREATE INDEX IF NOT EXISTS idx_norms_emisor ON public.norms(emisor);

COMMENT ON TABLE public.norms IS
    'fixplan_v3 §0.3.1 — canonical catalog of legal artifacts. Sub-units (parágrafos, numerales, etc.) are first-class rows.';
