# 09. Conceptos DIAN Individuales + Oficios DIAN

**Master:** ../corpus_population_plan.md §4.4 (Phase H) + §7 (Gap #2)  
**Owner:** unassigned  
**Status:** 🟡 not started  
**Target norm count:** ~430  
**Phase batches affected:** H1, H2, H3a, H3b, H4a, H4b, H5, H6

---

## What

Phase H covers two doctrinal families: (a) individual **Conceptos DIAN** (short-form doctrinal responses to specific tax questions, numbered in the range 1–100k, typically issued over years not compilations), and (b) **Oficios DIAN** (official letters responding to taxpayer inquiries, numbered by year, e.g., `oficio.dian.018424.2024`). Together, ~430 norms represent the "long tail" of DIAN guidance — more granular and recent than the unified conceptos (G1–G5), but not systematized into unified compilations. The canonicalizer batch slices for H1–H6 use regex patterns; this brief includes a **regex-tightening deliverable** (§7 Gap #2) to fix observed false-positive over-matches (5,608 phantom matches in current YAML).

---

## Source URLs (primary)

| URL | What's there |
|---|---|
| https://normograma.dian.gov.co/dian/compilacion/docs/oficio_dian_<NUM>_<YEAR>.htm | Individual concepto or oficio full text |
| https://normograma.dian.gov.co/dian/compilacion/docs/concepto_tributario_dian_NNNNNN.htm | Individual concepto (6-digit number, non-unified) |
| https://www.dian.gov.co/fizcalizacioncontrol/herramienconsulta/NIIF/ConceptosDian/Paginas/default.aspx | Master index (filters for "individual" vs "unified") |
| https://www.dian.gov.co/normatividad/Paginas/Oficios.aspx | Master oficios index (by year, topic) |

**Canonical examples (verified by existence in DIAN normograma):**
- Individual concepto: `concepto_tributario_dian_003028_2024.htm` → `concepto.dian.003028` (or `concepto.dian.3028` without zero-padding — verify existing corpus)
- Oficio: `oficio_dian_018424_2024.htm` → `oficio.dian.018424.2024`

---

## Canonical norm_id shape

**Individual concepto:** `concepto.dian.<NUM>` where NUM is typically 3–6 digits (e.g., `concepto.dian.3028`, `concepto.dian.100208192` non-hyphenated; do NOT include the suffix `-202` etc. unless it's part of the official numbering)

**Oficio:** `oficio.dian.<NUM>.<YEAR>` where NUM is typically 5–6 digits and YEAR is 4 digits.

> **Examples vary in verification:** `oficio.dian.018424.2024` is listed in the "Canonical examples (verified by existence in DIAN normograma)" block above (§What → Canonical examples). Any other oficio number is illustrative — verify against the DIAN normograma oficios index before pasting into a real row. Do not invent oficio numbers.

**Round-trip:** Via `lia_graph.canon.canonicalize(...)` both forms must survive round-trip unchanged.

**Distinction from unified conceptos:** Individual `concepto.dian.NNNN` (no suffix) vs unified `concepto.dian.100208192-202` (hyphenated suffix). The regex filter must distinguish them cleanly to avoid false positives.

---

## Parsing strategy

### Part A: Individual Conceptos

1. **Fetch individual concepto page** — e.g., `oficio_dian_003028_2024.htm` or `concepto_tributario_dian_003028_2024.htm` (naming patterns vary; check DIAN normograma index to map between internal number and URL).
2. **Extract full text** — Most conceptos are single-topic documents (5–30 pages). Emit one row per concepto (not per numeral or sub-question, unlike unified conceptos).
3. **Emit row:**
   ```json
   {
     "norm_id": "concepto.dian.003028",
     "norm_type": "concepto_dian",
     "article_key": "Concepto 3028",
     "body": "<full verbatim concepto text>",
     "source_url": "https://normograma.dian.gov.co/dian/compilacion/docs/concepto_tributario_dian_003028_2024.htm",
     "fecha_emision": "2024-03-15",
     "emisor": "DIAN",
     "tema": "Retención"
   }
   ```
   **Note:** The norm_id is **without the year** because DIAN sometimes re-issues conceptos with the same number but updated guidance. The canonicalizer identifies vigencia by content matching, not by year suffix.

### Part B: Oficios DIAN

1. **Fetch oficio HTML page** — e.g., `oficio_dian_018424_2024.htm`.
2. **Extract full text** — Oficios are typically shorter (1–5 pages), often a response to a specific taxpayer question. Emit one row per oficio.
3. **Emit row:**
   ```json
   {
     "norm_id": "oficio.dian.018424.2024",
     "norm_type": "oficio_dian",
     "article_key": "Oficio 018424 de 2024",
     "body": "<full verbatim oficio text>",
     "source_url": "https://normograma.dian.gov.co/dian/compilacion/docs/oficio_dian_018424_2024.htm",
     "fecha_emision": "2024-02-28",
     "emisor": "DIAN",
     "tema": "Renta"
   }
   ```
   **Note:** Oficios are included in the year in the norm_id because they are time-bound responses; year is material.

### Part C: Batch assignment (H1–H6)

Assign individual conceptos and oficios to batches by topic. The master plan specifies:
- **H1** — Régimen Simple conceptos/oficios
- **H2** — Retención en la Fuente conceptos/oficios
- **H3a / H3b** — Renta conceptos/oficios (split if >200)
- **H4a / H4b** — IVA conceptos/oficios (split if >200)
- **H5** — Procedimiento conceptos/oficios
- **H6** — Mixed oficios (scan for top-cited of icio numbers by year, e.g., oficios related to fiscal defense, obligaciones, cambio de domicilio)

### Part D: Scraper gap #2 — oficio.dian.* URL resolution

**Current state:** The DIAN normograma scraper (`src/lia_graph/scrapers/dian_normograma.py`) handles `concepto.*` URLs but has **no case for `oficio.dian.*`**. The canonicalizer's `_resolve_url` method does not know how to map `oficio.dian.018424.2024` → the corresponding HTML URL.

**Fix (non-negotiable for H6):** Add a resolver case in `dian_normograma.py`:

```python
elif norm_id.startswith("oficio.dian."):
    # Parse: oficio.dian.NNNNN.YYYY
    parts = norm_id.split(".")
    if len(parts) == 4 and parts[0] == "oficio" and parts[1] == "dian":
        num, year = parts[2], parts[3]
        # Map to: oficio_dian_NNNNN_YYYY.htm
        url = f"https://normograma.dian.gov.co/dian/compilacion/docs/oficio_dian_{num}_{year}.htm"
        return url
    raise ValueError(f"Invalid oficio.dian ID: {norm_id}")
```

**Fallback (if scraper extension is deferred):** Fixture the oficio HTML text directly in `tests/fixtures/scrapers/dian/oficio_dian_<NUM>_<YEAR>.htm` and never attempt live-fetch. This is acceptable for H6 (a small subset of high-citation oficios) but not pragmatic for hundreds of conceptos/oficios in H1–H5.

---

## Edge cases observed

- **Zero-padding in concepto numbers** — Some conceptos use `concepto.dian.003028` (zero-padded) while others are `concepto.dian.3028` (non-padded). **Verify the actual pattern used in the existing corpus and standardize before ingest.** The canonicalize function may accept both, but the batch filters (regex) will not match if the corpus uses one form and the YAML expects the other.
- **Oficio misidentification** — Some entries in the DIAN normograma index labeled "Oficio" are actually conceptos, and vice versa. Check the document header (first page) to confirm whether it's a formal "CONCEPTO" or "OFICIO" before assigning norm_type.
- **Multiple recipients in oficio** — An oficio may address multiple parties or reference prior oficios (e.g., "En respuesta a su Oficio 018423 de 2024…"). Keep the entire text as one row; do not split by recipient.
- **Legacy numbering (pre-2005)** — Oficios from 2005 and earlier may use a different numbering scheme (e.g., `oficio.dian.908128.2021` has 6 digits). The regex must accommodate variable-length NUM fields.

**Concepto vs Oficio.** Two distinct families with two distinct canonical id shapes: a Concepto DIAN is identified by number only (`concepto.dian.<NUM>`), while an Oficio DIAN is identified by number + year (`oficio.dian.<NUM>.<YEAR>`). Do not collapse them. If a source document is titled "Oficio Nº 018424 del 2024", emit `oficio.dian.018424.2024`; if it's titled "Concepto Unificado de Renta Nº 0912", emit `concepto.dian.0912`. Mixing them will produce non-canonical ids that the writer rejects.

---

## Regex tightening (deliverable for Gap #2)

**Current YAML problem:** The H1–H6 batch slices use regex patterns that over-match (5,608 false positives observed). Example current pattern:

```yaml
H1:
  norm_filter:
    pattern: ".*concepto.*simple.*"  # ❌ Too broad; matches noise
```

**Corrected patterns:** Use **anchored, tight regex** that explicitly targets the canonical shape:

```yaml
H1:
  norm_filter:
    pattern: "^(concepto\\.dian\\.\\d{4,6}|oficio\\.dian\\.\\d{5,6}\\.202[0-9]).*simple.*"
    # Matches: concepto.dian.NNNN, oficio.dian.NNNNN.YYYY, with "simple" keyword

H2:
  norm_filter:
    pattern: "^(concepto\\.dian\\.\\d{4,6}|oficio\\.dian\\.\\d{5,6}\\.202[0-9]).*retencion.*"
    # Matches: concepto/oficio containing "retencion" keyword

H3a:
  norm_filter:
    pattern: "^(concepto\\.dian\\.\\d{4,6}|oficio\\.dian\\.\\d{5,6}\\.202[0-9]).*renta.*"
    # etc.
```

**Action before ingest:** Edit `config/canonicalizer_run_v1/batches.yaml` to replace the H1–H6 `pattern` entries with tightened regex (anchored to `^`, explicit digit ranges, keyword-scoped). Test the new regex against the current corpus to confirm it eliminates false positives while preserving true matches.

**Verification code:**

```bash
import re
from pathlib import Path

# Load the new regex patterns
new_patterns = {
    'H1': r'^(concepto\.dian\.\d{4,6}|oficio\.dian\.\d{5,6}\.202[0-9]).*simple.*',
    'H2': r'^(concepto\.dian\.\d{4,6}|oficio\.dian\.\d{5,6}\.202[0-9]).*retencion.*',
    # etc. — add all H1-H6 patterns
}

# Count matches in corpus
with open('evals/vigencia_extraction_v1/input_set.jsonl') as f:
    for batch, pattern in new_patterns.items():
        matches = sum(1 for line in f if re.match(pattern, json.loads(line)['norm_id'], re.I))
        f.seek(0)
        print(f'{batch}: {matches} matches (expected: <<< 500 false positives)')
```

---

## Smoke verification

After ingest and regex tightening, run:

```bash
PYTHONPATH=src:. uv run python -c "
import sys
sys.path.insert(0, 'scripts/canonicalizer')
from extract_vigencia import _resolve_batch_input_set
from pathlib import Path
for bid in ['H1', 'H2', 'H3a', 'H3b', 'H4a', 'H4b', 'H5', 'H6']:
    norms = _resolve_batch_input_set(
        batches_config=Path('config/canonicalizer_run_v1/batches.yaml'),
        batch_id=bid,
        corpus_input_set=Path('evals/vigencia_extraction_v1/input_set.jsonl'),
        limit=None,
    )
    print(f'{bid}: {len(norms)} norms')
"
```

**Expected:** H1–H6 combined ≥350 norms (80% of target 430). No false-positive spikes.

---

## Dependencies on other briefs

- **Upstream:** **G1–G5 (unified conceptos) must be ingested before H1–H6** to avoid numeral-ID collisions. The unified conceptos use `concepto.dian.NUM.num.X` (with `.num.` sub-unit), while individual conceptos use `concepto.dian.NUM` (no sub-unit). They coexist, but ingesting them in the wrong order (H before G) can confuse the canonicalizer's batch filtering.
- **Downstream:** Oficios in H6 may reference resoluciones (F), leyes (E), or unified conceptos (G). Once those are populated, the canonicalizer can trace vigencia links across families.

---

## Priority staging

Given the complexity of this brief (regex tightening + scraper gap + two norm families), recommend:

1. **Phase 1** (low risk): Ingest individual conceptos (H1–H5) using fixture-only approach (no live scraper; hardcode URLs in parsed_articles.jsonl).
2. **Phase 2** (depends on Gap #2 fix): Ingest oficios (H6) after implementing the `oficio.dian.*` scraper case OR after fixturen the top-200 oficios.
3. **Parallel:** Tighten H-batch regex in YAML (non-blocking; can happen anytime before the smoke test).

---

**Ingestion notes:**

- Schema validation before commit: run §6.1 round-trip check on all `concepto.dian.*` and `oficio.dian.*` norm_ids.
- Commit message pattern: 
  - `corpus(conceptos-individuales): ingest ~180 individual conceptos Phase H1-H5` (first commit)
  - `corpus(oficios-dian): ingest ~250 oficios Phase H6 (requires scraper Gap #2)` (second commit, conditional on Gap #2 fix)
- Before final merge, run the smoke test and confirm no regex false-positive spikes.

