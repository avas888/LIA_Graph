# UGPP Doctrine Ingestion Plan

> **Relation to SUIN:** SUIN carries the enacting norms (Ley 1607/2012 art 156 created UGPP; Decreto 575/2013 reglamenta), but it does **not** carry UGPP's own conceptos, circulares, or acuerdos — those are administrative doctrine published by UGPP at `ugpp.gov.co/normatividad`. This plan brings that doctrine into the same `documents` / `document_chunks` / `normative_edges` shape SUIN populates.

## Why UGPP matters for a Colombian accountant

UGPP (**Unidad de Gestión Pensional y Parafiscales**) is the fiscalization body for payroll contributions in Colombia. Every SMB accountant who runs nómina eventually faces one of:

- A **requerimiento** for inexact PILA aportes.
- A **sanción** under Acuerdo 1035/2015 (UGPP's sanctioning regime).
- A **planilla de corrección** for historical periods.
- A **fiscalización de IBC** (ingreso base de cotización) when UGPP questions the declared base.

Answering those questions routes through UGPP doctrine at four levels:

1. **Acuerdos** — UGPP's binding rules (e.g., Acuerdo 1035/2015 — régimen sancionatorio; Acuerdo 003/2017 — procedimientos).
2. **Conceptos** — UGPP's answers to recurring questions (IBC de independientes, categorización de bonificaciones, etc.).
3. **Circulares** — operational guidance (plazos de cobro, procedimientos internos).
4. **Resoluciones** — individual rulings (less useful as doctrine but occasionally authoritative).

Without UGPP doctrine, an accountant asked "can UGPP cobrar por IBC calculado con base en facturación?" gets a partial answer citing ET 108 and Decreto 1072; they don't see UGPP's own interpretation in Concepto XXX/YYYY, which is what UGPP inspectors actually use.

---

## Stage tracker

| # | Stage | Status | Artifacts that prove it | Updated |
|---|---|---|---|---|
| 0 | Scope + branch — create `feat/ugpp-ingestion` off `main`; `cache/ugpp/` in `.gitignore` | pending | branch + gitignore diff | — |
| 1 | Source survey — enumerate what `ugpp.gov.co/normatividad` actually exposes. Are Acuerdos / Conceptos / Circulares in a searchable database, a PDF repository, or HTML pages? | pending | a one-page summary in this doc under "Source layout" with URL patterns | — |
| 2 | Fetcher — `src/lia_graph/ingestion/ugpp/fetcher.py`; if the source serves PDFs, include a PDF→text extractor (pdfminer.six or pdfplumber) | pending | `tests/test_ugpp_fetcher.py`; 1 sample PDF extracted | — |
| 3 | Parser — `src/lia_graph/ingestion/ugpp/parser.py`; Acuerdos have a regular article structure (fits `ParsedArticle` cleanly); Conceptos are free-form prose (one article per doc) | pending | `tests/test_ugpp_parser.py` with ≥2 fixtures (one Acuerdo, one Concepto) | — |
| 4 | Bridge — `src/lia_graph/ingestion/ugpp/bridge.py`; map UGPP edges: `modifica Acuerdo X` → `modifies`; `interpreta art. Y Decreto 1072` → `references`; `sanciona incumplimiento art. Z` → new `EdgeKind` `SANCTIONS` mapped to `references` | pending | `tests/test_ugpp_bridge.py`; smoke merge local | — |
| 5 | Ingest wiring — `--include-ugpp <scope>` on `lia_graph.ingest` | pending | WIP merge ≥3 UGPP docs into local Supabase + Falkor | — |
| 6 | WIP smoke — Acuerdo 1035/2015 + Concepto on IBC de independientes + one recent Circular | pending | rows in local Supabase under `gen_ugpp_smoke_v1` | — |
| 7 | Full crawl + WIP merge — all vigentes Acuerdos + top-50 Conceptos (citation-ranked) + Circulares of last 3 years | pending | WIP generation carries ≥60 UGPP docs | — |
| 8 | Embedding backfill | pending | 0 NULL embeddings on WIP | — |
| 9 | **Production push** (user gate) — same orchestrator shape as SUIN/DIAN | pending (**awaits user confirmation**) | cloud `gen_ugpp_prod_v1` active | — |

---

## Source layout (to be confirmed at Stage 1)

Best-guess URL patterns based on public exploration — **treat as placeholder until Stage 1 confirms**:

| Doc type | Index URL | Individual URL pattern |
|---|---|---|
| Acuerdo | `/normatividad/acuerdos` | `/normatividad/acuerdos/acuerdo-<NNNN>-<YEAR>.pdf` (likely PDFs) |
| Concepto | `/normatividad/conceptos` | `/normatividad/conceptos/concepto-<NNNN>-<YEAR>.pdf` |
| Circular | `/normatividad/circulares` | `/normatividad/circulares/circular-<NNNN>-<YEAR>.pdf` |
| Resolución | `/normatividad/resoluciones` | `/normatividad/resoluciones/...` |

**Stage 1 must answer:**
- PDF vs. HTML — determines whether we need pdfplumber.
- Pagination shape (is the Conceptos index a single long page or paginated?).
- Whether UGPP exposes a search/filter by topic (IBC, bonificaciones, independientes, etc.) that we can use to rank Conceptos.

---

## Parser sketch

### Acuerdos

Structured like Resoluciones / Decretos. Article anchor pattern is `Artículo 1°`, `Artículo 2°`, etc. Headings in bold. Fits `ParsedArticle` directly.

### Conceptos

Free-form prose. Typically structured as:
- **Problema jurídico** — one-paragraph statement of the question.
- **Tesis** — UGPP's answer.
- **Análisis** — reasoning.
- **Conclusión** — operative holding.

Treat the whole Concepto as one "article" with `article_number="concepto"`. Store `problema`, `tesis`, `conclusion` as separate `concept_tags` fields on the chunk so the retriever can surface them explicitly.

### Citation patterns

UGPP Conceptos cite the ET and CST heavily. Outbound edges:

- `Fuente legal: ET art. 114-1` → `references`
- `Fuente legal: CST art. 127` → `references`
- `Fuente legal: Decreto 1072/2015 art. 2.2.x.y` → `references`
- `Reitera Concepto UGPP N° AAAA/YYYY` → `references`
- `Aclara Concepto UGPP N° AAAA/YYYY` → new canonical `aclara` → DB relation `references`

---

## Edge vocabulary extension

| Raw UGPP token | Canonical | DB relation |
|---|---|---|
| Modificado por Acuerdo X | `modifica` | `modifies` |
| Derogado por Acuerdo X | `deroga` | `derogates` |
| Sanciona incumplimiento art. Y | `sanciona` (**new canonical**) | `references` |
| Fuente legal: art. Z | `references` | `references` |
| Aclara Concepto N | `aclara` (**new canonical**) | `references` |
| Reitera Concepto N | `references` | `references` |

Two new `EdgeKind` members: `SANCTIONS`, `CLARIFIES`. Both map to the existing `references` DB relation — no schema change.

---

## Crawl strategy

### Tier 1 (first production push)

- **All currently-vigente Acuerdos** (~15–20 docs).
- **Top 50 Conceptos** by in-degree from Acuerdos + cross-references. Identify via a discovery pass.
- **Circulares of the last 3 years** (~10–15 docs).

### Tier 2 (follow-up)

- Older conceptos cited by Tier 1.
- Resoluciones specific to SMB-relevant sectors.

---

## Architecture (mirrors SUIN/DIAN)

```
src/lia_graph/ingestion/ugpp/
├── __init__.py
├── fetcher.py       # HTTP + cache + rate limit + optional PDF extract
├── parser.py        # DOM/PDF → UgppDocument
├── harvest.py       # CLI orchestrator
└── bridge.py        # UgppDocument → ParsedArticle / ClassifiedEdge / document_rows
```

Doc-id prefix: `ugpp_<doc_type>_<NNNN>_<YEAR>` — no collision with `suin_*` or `dian_*`.

---

## Risks

- **PDF extraction noise** — UGPP publishes many docs as PDFs. pdfplumber handles most well but not all (scanned PDFs need OCR). Log-and-skip unreadable; flag count in the manifest.
- **Legal-standing disclaimer** — UGPP Conceptos are **non-binding on taxpayers** but are the internal authority UGPP inspectors use. Tag `concept_tags: ['ugpp_internal_authority']` on chunks so answers surface this nuance.
- **Normativity drift** — UGPP publishes new Conceptos frequently. Quarterly re-crawl is advisable once in production.
- **Sanctioning-regime sensitivity** — Acuerdo 1035/2015 is frequently updated. The change history from SUIN's `Decreto 575/2013` stubs in v1 should resolve to the current Acuerdo once we ingest it — v1 already has the stub nodes waiting.

## Handoff

- UGPP has historically been responsive to bulk-data requests via official channels. If normograma-style automated crawling is not advisable, consider a one-time manual download of the Acuerdos set + an automated Concepto crawl only.
- Do not crawl before the user explicitly approves the plan.
