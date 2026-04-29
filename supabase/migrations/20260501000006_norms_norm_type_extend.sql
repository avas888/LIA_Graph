-- next_v7 P1 (post-launch fix) — extend norms.norm_type CHECK to cover
-- the Códigos (CST, CCo) and the additional decreto subtypes.
--
-- The original baseline (`20260501000000_norms_catalog.sql`) restricted
-- norm_type to a closed set that omitted:
--   * cst, cst_articulo  (Código Sustantivo del Trabajo)
--   * cco, cco_articulo  (Código de Comercio)
--   * decreto_legislativo, decreto_legislativo_articulo (CP Art. 215)
--   * decreto_ley, decreto_ley_articulo (Ley de Facultades)
--   * oficio_dian, dcin_numeral (already returned by canon.norm_type
--     but never enumerated in the CHECK)
--
-- The cloud promotion run `v6-cloud-promotion-20260429T131407Z` tripped
-- fail-fast on J1+J2 (CST batches) with:
--   ERROR: new row for relation "norms" violates check constraint
--          "norms_norm_type_valid"
--   Failing row contains (cst.art.22, cst_articulo, cst, ..., t)
--
-- This migration drops the old constraint and re-adds it with the full
-- enumerated set the canon.py grammar can produce. Strictly additive —
-- every previously-valid value remains valid.
--
-- Reversibility: re-applying `20260501000000_norms_catalog.sql` restores
-- the narrow constraint.

ALTER TABLE public.norms
    DROP CONSTRAINT IF EXISTS norms_norm_type_valid;

ALTER TABLE public.norms
    ADD CONSTRAINT norms_norm_type_valid CHECK (norm_type IN (
        'estatuto', 'articulo_et',
        'ley', 'ley_articulo',
        'decreto', 'decreto_articulo',
        'decreto_legislativo', 'decreto_legislativo_articulo',
        'decreto_ley', 'decreto_ley_articulo',
        'resolucion', 'res_articulo',
        'concepto_dian', 'concepto_dian_numeral',
        'oficio_dian',
        'sentencia_cc', 'auto_ce', 'sentencia_ce',
        'cst', 'cst_articulo',
        'cco', 'cco_articulo',
        'dcin_numeral',
        'unknown'
    ));

COMMENT ON CONSTRAINT norms_norm_type_valid ON public.norms IS
    'next_v7 P1 fix — extended to cover Códigos (CST/CCo) and additional decreto subtypes (legislativo, ley) returned by canon.norm_type().';
