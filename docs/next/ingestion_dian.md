# DIAN Normograma Ingestion Plan

> **Relation to SUIN:** SUIN carries Leyes, Decretos, sentencias, and a handful of Acuerdos/Circulares — it does **not** carry DIAN's administrative doctrine (Resoluciones, Conceptos, Oficios, Circulares). That doctrine lives at `normograma.dian.gov.co` and requires its own scraper, parser, and bridge. This doc specifies how to bring DIAN's normograma into the same `documents` / `document_chunks` / `normative_edges` / FalkorDB shape SUIN already populates, so downstream retrieval stays consistent.

## Why this matters for a Colombian accountant

Every operational tax question an SMB accountant answers in practice routes through DIAN doctrine at some point:

- **Facturación electrónica**: not in ET or DUR 1625 at implementation detail — lives in Resolución DIAN 000042/2020 + subsequent modifications, plus the *technical annex* (field-level XML specs).
- **Nómina electrónica**: Resolución DIAN 000013/2021 + Decreto 358/2020 (SUIN has 358; DIAN has 000013).
- **Retención en la fuente tables**: Resolución DIAN anual (000022 de 2025 is current; prior years still apply for firmeza).
- **Beneficiario final (RUB)**: Resolución DIAN 000164/2021.
- **Información exógena**: annual Resolución (000124 de 2024 is current) — format + deadlines.
- **Calificaciones de bienes para IVA/ICA**: DIAN Oficios + Conceptos — non-binding but heavily cited.
- **SIMPLE regime operational detail**: Resoluciones on inscripción, declaración, plazos.

Without DIAN doctrine, Lia can answer "what does ET say?" but cannot answer "how do I actually comply?" — the second question is what the accountant asks every day.

---

## Stage tracker

| # | Stage | Status | Artifacts that prove it | Updated |
|---|---|---|---|---|
| 0 | Scope + branch — create `feat/dian-ingestion` off `main` (or off `feat/suin-ingestion-v2` after v2 lands); ensure `docs/next/ingestion_dian.md` merged; `cache/dian/` added to `.gitignore` | pending | branch created; `.gitignore` diff | — |
| 1 | Fetcher — `src/lia_graph/ingestion/dian/fetcher.py` (robots-aware, rate-limited, disk-cached; truststore-backed for TLS if DIAN also has cert-chain quirks) | pending | `tests/test_dian_fetcher.py` green | — |
| 2 | Sitemap / index discovery — `normograma.dian.gov.co` exposes a taxonomy (Resoluciones / Conceptos / Oficios / Circulares). Map each doc type to its index page URL pattern. | pending | `src/lia_graph/ingestion/dian/fetcher.py::DIAN_INDEX_URLS` populated + tested | — |
| 3 | Parser — `src/lia_graph/ingestion/dian/parser.py`; handle the DIAN-specific DOM (differs from SUIN — normograma uses a cleaner compilación layout with headings, footnotes, vigencia annotations inline). | pending | `tests/test_dian_parser.py` with ≥3 real-HTML fixtures (one Resolución, one Concepto, one Oficio); zero `UnknownVerb` failures on a 20-doc smoke crawl | — |
| 4 | Bridge — `src/lia_graph/ingestion/dian/bridge.py`; convert DIAN-parsed docs into `ParsedArticle` / `ClassifiedEdge` / document rows matching the Supabase sink contract. DIAN edges map cleanly: `modifica` → `modifies`, `deroga` → `derogates`, `conceptualiza` (new) → `references`. | pending | `tests/test_dian_bridge.py`; smoke merge into local docker Supabase | — |
| 5 | Ingest wiring — `--include-dian <scope>` flag on `lia_graph.ingest`, parallel to `--include-suin` | pending | WIP merge of ≥5 DIAN docs into local docker Supabase + Falkor | — |
| 6 | WIP smoke — Resolución 000013/2021 + 000042/2020 + Concepto 915/2017 (exoneración parafiscales 114-1 — high-value) | pending | rows in local Supabase under `gen_dian_smoke_v1`; spot-check edges link to ET 114-1 + CST | — |
| 7 | Tier-1 full crawl + WIP merge — full Resoluciones (past 5 years) + current retención en la fuente table + top-100 cited Oficios/Conceptos (discoverable by accountant-value heuristic; see "Crawl strategy" below) | pending | WIP generation carries Resoluciones + top-100 doctrine | — |
| 8 | Embedding backfill against WIP | pending | 0 NULL embeddings on WIP | — |
| 9 | **Production push** (user gate) — same orchestrator shape as SUIN | pending (**awaits user confirmation**) | cloud `gen_dian_prod_v1` active | — |

---

## Source: `normograma.dian.gov.co`

### What's there

| Doc type | Typical URL pattern | Value to accountant |
|---|---|---|
| Resolución | `/dian/compilacion/docs/resolucion_dian_<NNNN>_<YEAR>.htm` | **Highest** — operational rules (facturación, nómina, retención, exógena) |
| Concepto | `/dian/compilacion/docs/concepto_dian_<NNNN>_<YEAR>.htm` | High — DIAN's own interpretation; non-binding but safe harbor |
| Oficio | `/dian/compilacion/docs/oficio_dian_<NNNN>_<YEAR>.htm` | Medium — case-specific answers; useful analogical authority |
| Circular | `/dian/compilacion/docs/circular_dian_<NNNN>_<YEAR>.htm` | Medium — internal/operational guidance |
| Instrucción administrativa | `/dian/compilacion/docs/instruccion_dian_<NNNN>_<YEAR>.htm` | Low — audit procedures |

(URL patterns above are indicative — confirm during Stage 2 discovery. Normograma may also proxy content at other paths.)

### Rate limit + robots

- DIAN normograma has no public rate limit doc. Start at `rps=0.5`; ease to `1.0` only if no 429/5xx over the first 100 requests.
- Respect `robots.txt` same way `SuinFetcher` does. If normograma doesn't publish one, treat the absence as permissive but throttle conservatively.
- User-Agent: `LIA-IngestionBot/1.0 (+mailto:avasqueza@gmail.com)` — same identity SUIN sees, so network operators can correlate traffic.

### TLS

- Verify DIAN's cert chain behaves like SUIN's (incomplete intermediate → truststore needed) OR is clean. If truststore needed, reuse the v1 pattern: detect and inject at `_ensure_client` time.

---

## Parser sketch

### Document shape

```python
@dataclass(frozen=True)
class DianDocument:
    doc_id: str                       # e.g. "resolucion_dian_0013_2021"
    doc_type: str                     # "resolucion" | "concepto" | "oficio" | "circular" | "instruccion"
    numero: str                       # "000013" / "0013"
    year: int                         # 2021
    title: str
    emitter: str = "DIAN"
    fecha_expedicion: str             # ISO date
    vigencia: str                     # "vigente" | "derogada" | "suspendida"
    tema: str                         # DIAN's own taxonomy: "facturación", "nómina", "retención", ...
    articles: tuple[DianArticle, ...]
    outbound_edges: tuple[DianEdge, ...]   # document-level edges (e.g., this Resolución modifies that Decreto)
```

### Article shape

DIAN Resoluciones are structured like Decretos: `Artículo 1°`, `Artículo 2°`, etc. Conceptos/Oficios are free-form prose — treat the whole doc as one "article" with `article_number="concepto"`.

### Edge vocabulary

DIAN doctrine uses a narrower verb set than SUIN:

| Raw DIAN token | Canonical | DB relation |
|---|---|---|
| Modificado / Sustituido | `modifica` | `modifies` |
| Adicionado | `adiciona` | `modifies` |
| Derogado / Suprimido | `deroga` | `derogates` |
| Reglamenta (of an ET article) | `reglamenta` | `complements` |
| Aclara / Precisa (of an earlier Concepto) | `interpreta` (**new canonical**) | `references` |
| Fuente: (source Concepto citation) | `references` | `references` |

Add `interpreta` as a new `EdgeKind` member in `src/lia_graph/graph/schema.py`. Bridge maps it to `references` (no new DB relation needed; the CHECK constraint already allows `references`).

---

## Crawl strategy

### Problem

Normograma has ~tens of thousands of Oficios and Conceptos. Crawling all of them is wasteful — most are low-relevance one-offs.

### Priority by accountant value (same forward-from-today lens as SUIN v1)

1. **All Resoluciones of the last 5 years** (~300 docs). Stable volume; highest operational value.
2. **The ~100 most-cited Conceptos/Oficios** — identifiable by the Conceptos that later docs cite as "Fuente:". Build a citation graph from Tier 1 Resoluciones, rank Conceptos by in-degree, take top 100.
3. **Annual Resoluciones: retención en la fuente, información exógena, calendario tributario** — grab the latest 3 years (current + previous 2, for firmeza-period questions).

### Discovery mechanics

- Normograma publishes compiled index pages per year and per doc type. Scrape index → enumerate doc URLs → fetch individual docs (cache-keyed).
- Alternatively, DIAN exposes a search endpoint (`normograma.dian.gov.co/dian/compilacion/buscar`). Probe its response shape before designing the index crawler — search may be simpler.

### Excluded for now

- Conceptos older than 2015 unless cited by post-2015 docs. Legal opinions evolve; old ones are often superseded.
- Oficios answering hyper-specific taxpayer-identified questions. These are rarely useful as doctrine.

---

## Architecture (mirrors SUIN)

```
src/lia_graph/ingestion/dian/
├── __init__.py
├── fetcher.py       # HTTP + cache + rate limit + truststore
├── parser.py        # BeautifulSoup DOM → DianDocument/Article/Edge
├── harvest.py       # CLI orchestrator + scope definitions
└── bridge.py        # DianDocument → ParsedArticle/ClassifiedEdge/document_rows
```

Reuse every pattern from SUIN: stem-based verb normalizer, per-edge unknown-verb tracking, two-pass stub-resolving merge, `--include-dian <scope>` CLI flag mirroring `--include-suin`.

### Naming convention for doc_ids

Prefix DIAN docs as `dian_<doc_type>_<NNNN>_<YEAR>` — e.g., `dian_resolucion_000013_2021`. Non-collision with SUIN's `suin_*` prefix is guaranteed.

---

## Phase gating

Same shape as SUIN — pending → in_progress → done on the tracker above; one user confirmation gate before Phase 9 (production push).

## Risks

- **DIAN normograma outage** — fetcher is resumable via cache. Retries exponential.
- **Silent DIAN content drift** — rerun-per-year pattern: Tier 1 crawl annual (new year's Resoluciones appear every December/January). Stub old year → new year upserts under new generation.
- **Concepto/Oficio DOM inconsistency** — older docs use a different compilación template. Expect 2–3 parser fixture iterations.
- **Legal standing disclaimer**: DIAN Conceptos are **non-binding** on taxpayers per Ley 1437/2011. Lia's answers must surface this when citing a Concepto as authority. Out of scope for ingestion; capture as a `concept_tags: ['non_binding']` field on the chunk so `answer_policy.py` can render accordingly.

## Handoff

- Read SUIN v1 + v2 plans before starting; the architectural patterns transfer almost verbatim.
- Do not crawl DIAN before the user explicitly approves the ingestion plan. `normograma.dian.gov.co` is a public resource but sustained automated traffic should be communicated to DIAN via their contact form if the volume is large.
