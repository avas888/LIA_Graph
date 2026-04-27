# Phase B — failure catalog
Auto-generated. Use this to re-run weak batches with `--allow-rerun` once the relevant prompt rule / parser fix lands.

Total Phase B batches: 10

## Per-batch summary

| Batch | Run id | Successes | Refusals | Errors | % | Verdict |
|---|---|---:|---:|---:|---:|---|
| B1 | `canonicalizer-B1-20260427T172059Z` | 8 | 26 | 0 | 24% | 🔴 weak |
| B10 | `canonicalizer-B10-20260427T174823Z` | 1 | 2 | 0 | 33% | 🔴 weak |
| B2 | `canonicalizer-B2-20260427T172059Z` | 11 | 34 | 0 | 24% | 🔴 weak |
| B3 | `canonicalizer-B3-20260427T172059Z` | 14 | 23 | 0 | 38% | 🔴 weak |
| B4 | `canonicalizer-B4-20260427T172926Z` | 18 | 20 | 0 | 47% | 🔴 weak |
| B5 | `canonicalizer-B5-20260427T172931Z` | 4 | 14 | 0 | 22% | 🔴 weak |
| B6 | `canonicalizer-B6-20260427T172941Z` | 61 | 38 | 0 | 62% | 🟨 mixed |
| B7 | `canonicalizer-B7-20260427T173246Z` | 5 | 4 | 0 | 56% | 🔴 weak |
| B8 | `canonicalizer-B8-20260427T173627Z` | 30 | 3 | 0 | 91% | 🎯 strong |
| B9 | `canonicalizer-B9-20260427T174037Z` | 25 | 1 | 0 | 96% | 🎯 strong |

## Per-batch refusal detail

### B1 — `canonicalizer-B1-20260427T172059Z`

**Refusal categories:**
- 23× Gemini adapter transient error
- 3× Source coverage gap (alternate-sources path needed)

**Per norm:**

| norm_id | category | reason | debug blob |
|---|---|---|---|
| `et.art.10-15` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.11` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.12` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.12-1.par.5` | Source coverage gap (alternate-sources path needed) | INSUFFICIENT_PRIMARY_SOURCES | _(not captured — early refusal pre-Gemini)_ |
| `et.art.13` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.14` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.14-1` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.14-23` | Source coverage gap (alternate-sources path needed) | INSUFFICIENT_PRIMARY_SOURCES | _(not captured — early refusal pre-Gemini)_ |
| `et.art.16` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.17.num.4` | Source coverage gap (alternate-sources path needed) | missing_double_primary_source | _(not captured — early refusal pre-Gemini)_ |
| `et.art.18` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.19` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.19-1` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.19-2` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.19-4` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.19-5` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.21` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.21-1` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.22` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.23` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.23-1` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.24` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.25` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.7` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.8` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.9` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |

### B10 — `canonicalizer-B10-20260427T174823Z`

**Refusal categories:**
- 2× Source coverage gap (alternate-sources path needed)

**Per norm:**

| norm_id | category | reason | debug blob |
|---|---|---|---|
| `et.art.290.num.5` | Source coverage gap (alternate-sources path needed) | missing_double_primary_source | _(not captured — early refusal pre-Gemini)_ |
| `et.art.290.num.6` | Source coverage gap (alternate-sources path needed) | missing_double_primary_source | _(not captured — early refusal pre-Gemini)_ |

### B2 — `canonicalizer-B2-20260427T172059Z`

**Refusal categories:**
- 31× Gemini adapter transient error
- 2× Other
- 1× Source coverage gap (alternate-sources path needed)

**Per norm:**

| norm_id | category | reason | debug blob |
|---|---|---|---|
| `et.art.26` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.27` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.29-1` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.30` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.31` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.31-4` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.32` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.34` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.35` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.35-1` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.36` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.36-1` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.36-3` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.36-4` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.38` | Other | invalid_vigencia_shape: state=RV requires revives_text_version | `evals/vigencia_extraction_v1/_debug/et.art.38.json` |
| `et.art.40-1` | Other | invalid_vigencia_shape: state=RV requires revives_text_version | `evals/vigencia_extraction_v1/_debug/et.art.40-1.json` |
| `et.art.41` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.42` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.44` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.45` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.46` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.46-1` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.47` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.49.par.a` | Source coverage gap (alternate-sources path needed) | missing_double_primary_source | _(not captured — early refusal pre-Gemini)_ |
| `et.art.50` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.51` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.52` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.53` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.54` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.55` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.56` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.56-1` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.56-2` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.57` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |

### B3 — `canonicalizer-B3-20260427T172059Z`

**Refusal categories:**
- 21× Gemini adapter transient error
- 2× Source coverage gap (alternate-sources path needed)

**Per norm:**

| norm_id | category | reason | debug blob |
|---|---|---|---|
| `et.art.59.lit.b` | Source coverage gap (alternate-sources path needed) | missing_double_primary_source | _(not captured — early refusal pre-Gemini)_ |
| `et.art.60` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.63` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.69` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.70` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.70.par.a` | Source coverage gap (alternate-sources path needed) | missing_double_primary_source | _(not captured — early refusal pre-Gemini)_ |
| `et.art.71` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.72-18` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.73` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.74` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.74-1` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.75` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.76` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.76-1` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.77` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.81` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.82` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.83` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.84` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.85` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.86` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.87` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.88` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |

### B4 — `canonicalizer-B4-20260427T172926Z`

**Refusal categories:**
- 18× Gemini adapter transient error
- 1× Other
- 1× Source coverage gap (alternate-sources path needed)

**Per norm:**

| norm_id | category | reason | debug blob |
|---|---|---|---|
| `et.art.104` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.107-1` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.107-2` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.108` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.108-5` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.109` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.110` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.111` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.113` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.114` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.114-1` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.114-1.par.1` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.115` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.118` | Other | invalid_vigencia_shape: state=RV requires revives_text_version | `evals/vigencia_extraction_v1/_debug/et.art.118.json` |
| `et.art.118-1` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.118-1.inciso.1` | Source coverage gap (alternate-sources path needed) | INSUFFICIENT_PRIMARY_SOURCES | _(not captured — early refusal pre-Gemini)_ |
| `et.art.119` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.121` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.122` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.123` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |

### B5 — `canonicalizer-B5-20260427T172931Z`

**Refusal categories:**
- 14× Gemini adapter transient error

**Per norm:**

| norm_id | category | reason | debug blob |
|---|---|---|---|
| `et.art.158-1` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.158-3` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.166` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.167` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.168` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.170` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.171` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.172` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.174` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.175` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.176` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.177` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.177-1` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.177-2` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |

### B6 — `canonicalizer-B6-20260427T172941Z`

**Refusal categories:**
- 31× Gemini adapter transient error
- 6× Source coverage gap (alternate-sources path needed)
- 1× Other

**Per norm:**

| norm_id | category | reason | debug blob |
|---|---|---|---|
| `et.art.181` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.182` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.183` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.184` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.185` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.186` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.187` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.188` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.188-189` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.189` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.189-1` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.191` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.192` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.193` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.195` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.196` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.197` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.201` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.202` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.203` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.203-13` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.204-1` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.205` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.206` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.206-1` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.207` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.207-1` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.207-2` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.211` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.213` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.214` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.237-1` | Other | invalid_vigencia_shape: state=IE not compatible with change_source.type=reforma | `evals/vigencia_extraction_v1/_debug/et.art.237-1.json` |
| `et.art.239-1` | Source coverage gap (alternate-sources path needed) | INSUFFICIENT_PRIMARY_SOURCES | _(not captured — early refusal pre-Gemini)_ |
| `et.art.240.inciso.1` | Source coverage gap (alternate-sources path needed) | missing_double_primary_source | _(not captured — early refusal pre-Gemini)_ |
| `et.art.241-1` | Source coverage gap (alternate-sources path needed) | INSUFFICIENT_PRIMARY_SOURCES | _(not captured — early refusal pre-Gemini)_ |
| `et.art.257.par.1` | Source coverage gap (alternate-sources path needed) | missing_double_primary_source | _(not captured — early refusal pre-Gemini)_ |
| `et.art.260-2.par.a` | Source coverage gap (alternate-sources path needed) | INSUFFICIENT_PRIMARY_SOURCES | _(not captured — early refusal pre-Gemini)_ |
| `et.art.260-5.inciso.1` | Source coverage gap (alternate-sources path needed) | INSUFFICIENT_PRIMARY_SOURCES | _(not captured — early refusal pre-Gemini)_ |

### B7 — `canonicalizer-B7-20260427T173246Z`

**Refusal categories:**
- 3× Gemini adapter transient error
- 1× Missing required field in veredicto

**Per norm:**

| norm_id | category | reason | debug blob |
|---|---|---|---|
| `et.art.240-1` | Missing required field in veredicto | invalid_vigencia_shape: 'norm_id' | `evals/vigencia_extraction_v1/_debug/et.art.240-1.json` |
| `et.art.242` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.243` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |
| `et.art.244` | Gemini adapter transient error | adapter_error: Gemini HTTP 503: [{
  "error": {
    "code": 503,
    "message": "This model is curre | _(not captured — early refusal pre-Gemini)_ |

### B8 — `canonicalizer-B8-20260427T173627Z`

**Refusal categories:**
- 3× Source coverage gap (alternate-sources path needed)

**Per norm:**

| norm_id | category | reason | debug blob |
|---|---|---|---|
| `et.art.257.par.1` | Source coverage gap (alternate-sources path needed) | missing_double_primary_source | _(not captured — early refusal pre-Gemini)_ |
| `et.art.260-2.par.a` | Source coverage gap (alternate-sources path needed) | INSUFFICIENT_PRIMARY_SOURCES | _(not captured — early refusal pre-Gemini)_ |
| `et.art.260-5.inciso.1` | Source coverage gap (alternate-sources path needed) | INSUFFICIENT_PRIMARY_SOURCES | _(not captured — early refusal pre-Gemini)_ |

### B9 — `canonicalizer-B9-20260427T174037Z`

**Refusal categories:**
- 1× Source coverage gap (alternate-sources path needed)

**Per norm:**

| norm_id | category | reason | debug blob |
|---|---|---|---|
| `et.art.31-4` | Source coverage gap (alternate-sources path needed) | INSUFFICIENT_PRIMARY_SOURCES | _(not captured — early refusal pre-Gemini)_ |

## Re-run recommendations

Weak/mixed batches above can be re-extracted with `--allow-rerun` once one of the following fixes lands:

1. **For Citation/list shape failures** — already mostly fixed by `_first_citation` parser tolerance. If a debug blob still fails, inspect for new shape variant.
2. **For source-coverage gaps** — Senado neighbor-segment fallback already in. If still failing, the article may be split across two pr-segments — extend the slicer.
3. **For Gemini adapter timeouts** — re-run; usually transient. If a batch hits >2 timeouts, slow `--max-concurrent` from 3 to 2 to reduce concurrent Gemini load.
4. **Cohort-1 anomaly (B1-B5 ~24-47% success)** — strongly suspect transient Gemini throttle on the first cohort under cold cache. Re-running B1-B5 in a fresh cohort (with cache warm from B8/B9 success) should recover to 80+%.

To re-run a single batch with the latest fixes:
```
# Clean the partial output (this is what `--allow-rerun` would NOT do)
rm -rf evals/vigencia_extraction_v1/<BATCH> evals/canonicalizer_run_v1/<BATCH>
# Then
bash scripts/canonicalizer/launch_batch.sh --batch <BATCH>
```

Or to re-run multiple in parallel:
```
bash scripts/canonicalizer/run_parallel_extract.sh --max-concurrent 2 B1 B2 B3 B5
```

---

## Throttle + retry fix (landed 2026-04-27 ~12:50 PM Bogotá)

**Diagnosis**: 23 of B1's 26 refusals were Gemini HTTP 503 ("model currently
overloaded"). The adapter had no retry — every transient surge propagated as
`adapter_error`. Concurrent launch of 3 batches under shared Gemini quota
amplified this.

**Fix landed**:

1. **`src/lia_graph/gemini_runtime.py::_request`** — exponential back-off
   retry on 429 / 500 / 502 / 503 / 504 + URLError / TimeoutError /
   OSError. 4 attempts, 0/4/12/30 sec back-off. 4xx-non-429 still fails
   fast.

2. **`scripts/canonicalizer/run_parallel_extract.sh`** — default
   `--max-concurrent` lowered from 3 to 2. `gemini-2.5-pro` empirically
   returns 503 under sustained 3-way concurrency even within project
   quota. Retry covers the residual transient case; lower cap covers the
   sustained case.

**Re-run plan for weak batches:**
```bash
# After in-flight orchestrator finishes Phase 2, re-extract the weak set:
bash scripts/canonicalizer/run_parallel_extract.sh \
    --max-concurrent 2 \
    --launcher-flag --allow-rerun \
    B1 B2 B3 B4 B5 B7 B10
```

This produces NEW run_ids per batch; the writer treats them as new
history rows. The previous (weak) run_ids' rows remain in
`norm_vigencia_history` but are superseded by the newer rows on a
`(norm_id, state_until IS NULL)` query. Append-only history is the
durable design — nothing is lost or rewritten.

