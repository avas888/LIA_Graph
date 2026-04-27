# corteconstitucional.gov.co — operational notes

**Site:** https://www.corteconstitucional.gov.co/
**Coverage:** Sentencias C-/T-/SU-, autos, comunicados.
**Scraper:** `src/lia_graph/scrapers/corte_constitucional.py`

## Known operational facts (as of 2026-04-27)

### 1. HTTPS works; cert validates with certifi
Reachable, fast (~0.1 s on a warm connection), trusts certifi out of
the box.

### 2. Sentencia URL pattern
Sentencias are at `/relatoria/<YEAR>/<SHORT>-<SEQ>-<YEAR>.htm`, e.g.:
```
https://www.corteconstitucional.gov.co/relatoria/2019/C-481-19.htm
```
The scraper's `_resolve_url` builds this from
`sentencia.cc.<TYPE>.<NUM>.<YEAR>` shapes per the canonicalizer's
norm-id grammar (`fixplan_v3.md` §0.5).

### 3. The `Salvamento de Voto` and `Aclaración de Voto` sections matter
For the EC (exequibilidad condicional) state and the IE (inexequible)
state, the dispositive paragraph and the precise "en el entendido que…"
phrasing carry the interpretive_constraint Gemini extracts. The
scraper's `_parse_html` preserves the full text — the skill prompt
does the substring extraction.

### 4. Polite rate limit at 0.5 s
The site is well-resourced; this is conservative.

## Recovery playbooks

### "Sentencia 404"
Common cause: the sentencia number in the corpus is normalized
differently from the relatoria path. Open the relatoria index for the
year and confirm the canonical shape — sometimes the corpus has
`SU-150-2021` but the file is `SU150-21.htm`. Either fix the corpus
canonical id or extend the resolver with the alternate spellings.

### "Page renders but Gemini extracts the wrong dispositive"
The site occasionally has multiple `<div class="dispositivo">` blocks
when the sentencia has multiple parts (Resuelve I, II, III). The
parser flattens to plaintext; the skill prompt is the right place to
disambiguate, not the scraper.
