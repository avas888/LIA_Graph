# Canonicalizer doc-anchor recovery — context-free + context-aware

**Source:** First live run of fixplan_v3 sub-fix 1B-δ
(`scripts/backfill_norm_citations.py`) against the populated local
corpus on 2026-04-27 night. Initial pass: 226 refusals on a 200-chunk
sample; doc-anchor recovery dropped that to 127 (44% reduction).

## What the canonicalizer refuses (correctly)

Per fixplan_v3 §0.5.4, the canonicalizer is intentionally context-free.
It refuses ambiguous mentions like:

- `"Ley 1429"` (no year)
- `"Decreto 1474"` (no year)
- `"Art. 240"` (no law prefix)
- `"según la DIAN..."` (no concepto number)

The refusal is the safe default — never silently substring-guess.

## What the corpus actually contains

But Colombian legal prose constantly references "Ley 1429" inside a
document whose filename / title pins the year context. Examples from
the live local corpus:

- File `LEYES_INVERSIONES_INCENTIVOS_consolidado_Ley-1429-2010.md` —
  every chunk references "Ley 1429" without the year.
- File `LEYES_COMERCIAL_SOCIETARIO_LOGGRO_PRACTICA_Ley-222-1995.md` —
  same pattern.
- File `decreto_1625_2016.md` — "Decreto 1625" appears 40+ times.

A human reader unambiguously resolves these because the document's
identity carries the year. The canonicalizer can't know this without
context.

## The fix: context-aware recovery in the BACKFILL, not in canon.py

**Principle:** keep `canon.py` context-free (per §0.5.4 — the contract
is binding). Add the doc-anchor recovery in the backfill loop, where
document context is naturally available via `documents.relative_path`.

The recovery loop:

1. Build a `chunk_id → host_norm_id` map by walking `documents` and
   parsing the filename for `Ley-NNN-YYYY` / `Decreto-NNN-YYYY` patterns
   (`scripts/backfill_norm_citations.py::_path_to_anchor`).
2. When the canonicalizer refuses with `reason='missing_year'`, check if
   the mention's number matches the host norm's number. If yes, accept
   the host's canonical id as the resolution.
3. Otherwise, log to the refusal queue for SME triage.

**Net result on the live corpus**: 7,877 chunks → 4,757 with citations
(60.4% coverage), 11,384 norms cataloged, 40,835 citation rows. Refusals
are now mostly genuine ambiguity (cross-doc references without context),
not the year-implicit pattern.

## Why this is structured context, not a guess

The doc-anchor map is grounded in `documents.relative_path` — a piece of
durable corpus structure, not free-form prose. The canonicalizer remains
context-free; the backfill applies a structured contextual rule that's
auditable per-chunk via the audit log. SME can always inspect:

> chunk `<doc>::<anchor>` mentions "Ley 1429"; host doc encodes
> `ley.1429.2010`; recovery accepted.

If the pattern ever breaks (e.g. a doc named `Ley-1429-2010.md` quotes
"Ley 1429" referring to the OTHER Ley 1429 that doesn't exist), the
audit log shows the recovery and SME can fix in one place.

## Two related bugs caught in the same session

### A. Same `(chunk_id, norm_id, role)` tuple appears multiple times in the same UPSERT batch

Postgres rejects `ON CONFLICT DO UPDATE` when the same row appears twice
in one batch. A chunk that mentions "Ley 1429" three times produced
three identical citation rows.

**Fix:** dedupe by `(chunk_id, norm_id, role)` before sending the batch.

### B. fixture upgrade picks up `vigente_hasta` and writes it as `state_until` for non-V/VM states

The v2 fixture for Art. 158-1 ET (DE state) had:
```json
{
  "state": "DE",
  "vigente_desde": null,
  "vigente_hasta": "2022-12-31",
  ...
}
```

The v2 schema's `vigente_hasta` means "the prior V version was vigente
until this date" — for the current DE row, `state_until` should be NULL
(the article is still derogated today).

The first iteration of `scripts/upgrade_v2_veredictos_to_v3.py` blindly
copied `vigente_hasta` to `state_until` and the DB CHECK
`state_until >= state_from` rejected the row.

**Fix:** only carry `vigente_hasta` into `state_until` when the new state
is V/VM (where it really does mark an end of applicability). For
DE/IE/SP/etc., `state_until` stays NULL.

## Generalizable lesson

When migrating between schema versions where the SEMANTICS of a field
changes (not just the shape), the mapper needs per-state special-casing.
A 1:1 field copy is wrong by default; require explicit per-state handling
or refuse to upgrade.
