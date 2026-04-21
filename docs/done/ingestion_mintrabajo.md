# MinTrabajo Doctrine Ingestion Plan

> **Relation to SUIN and UGPP:** SUIN carries Leyes, Decretos, and DURs (1072/2015 included). MinTrabajo (Ministerio del Trabajo) *emits* those Decretos — the enacted Decretos live in SUIN. But MinTrabajo also publishes its own **conceptos jurídicos**, **circulares**, and **resoluciones** at `mintrabajo.gov.co/conceptos-juridicos` and related paths. Those are MinTrabajo's administrative interpretation of the labor code (CST + DUR 1072). UGPP handles aportes fiscalization; MinTrabajo handles labor-law interpretation proper. This plan ingests the latter.

## Why MinTrabajo doctrine matters for a Colombian accountant

SMB accountants are often the *de facto* labor advisors to their clients (per product memory). The questions they take on:

- **Contratos** — *"puedo contratar por prestación de servicios?"* → CST is the legal frame, but MinTrabajo Concepto XXX/YYYY + jurisprudencia is the practical answer.
- **Jornada** — *"cómo se aplica la reducción de jornada de Ley 2101/2021?"* → CST + Decreto reglamentario + MinTrabajo Circular.
- **Reforma Laboral 2466/2025** — MinTrabajo has issued implementation circulares as the reform rolls out; those circulares are the operational bridge between the Ley and daily payroll.
- **Terminación del contrato** — *"cuándo hay justa causa?"* → CST art 62 + MinTrabajo Concepto interpretation.
- **Estabilidad reforzada** (fuero maternal / sindical / discapacidad) — MinTrabajo issues opinions that align with Corte Constitucional jurisprudence but are more operational.
- **Teletrabajo + trabajo remoto** — Ley 2088/2021 + MinTrabajo Circular with operational rules.

MinTrabajo conceptos are **non-binding on private parties** but they are the authority labor inspectors use when investigating complaints. For an accountant managing SMB compliance, the MinTrabajo view is what a labor inspector will apply if a dispute escalates.

---

## Stage tracker

| # | Stage | Status | Artifacts that prove it | Updated |
|---|---|---|---|---|
| 0 | Scope + branch — create `feat/mintrabajo-ingestion` off `main`; `cache/mintrabajo/` in `.gitignore` | pending | branch + gitignore diff | — |
| 1 | Source survey — enumerate `mintrabajo.gov.co/conceptos-juridicos` layout (HTML vs. PDF; pagination; tags/filters) | pending | URL patterns documented here under "Source layout" | — |
| 2 | Fetcher — `src/lia_graph/ingestion/mintrabajo/fetcher.py` (reuse UGPP's PDF-extract path if needed) | pending | `tests/test_mintrabajo_fetcher.py` green | — |
| 3 | Parser — `src/lia_graph/ingestion/mintrabajo/parser.py` — handles both HTML conceptos and PDF circulares | pending | `tests/test_mintrabajo_parser.py` ≥2 fixtures | — |
| 4 | Bridge — `src/lia_graph/ingestion/mintrabajo/bridge.py`; reuse the `interpreta` / `aclara` / `references` canonicals introduced for DIAN/UGPP | pending | smoke merge into local Supabase | — |
| 5 | Ingest wiring — `--include-mintrabajo <scope>` | pending | WIP merge ≥3 MinTrabajo docs | — |
| 6 | WIP smoke — one Concepto on contratación por prestación de servicios + one Circular on Reforma Laboral 2466 implementación + one teletrabajo Circular | pending | local Supabase rows under `gen_mintrabajo_smoke_v1` | — |
| 7 | Full crawl + WIP merge — top-80 Conceptos by citation rank + all vigentes Circulares of last 3 years | pending | WIP generation carries ≥100 MinTrabajo docs | — |
| 8 | Embedding backfill | pending | 0 NULL embeddings on WIP | — |
| 9 | **Production push** (user gate) | pending (**awaits user confirmation**) | cloud `gen_mintrabajo_prod_v1` active | — |

---

## Source layout (to be confirmed at Stage 1)

Known paths (placeholder — Stage 1 verifies):

| Doc type | Index URL | Individual URL |
|---|---|---|
| Concepto jurídico | `/conceptos-juridicos` | likely `/conceptos-juridicos/<slug>` or PDF |
| Circular | `/conceptos/circulares` or `/normatividad/circulares` | mix of HTML + PDF |
| Resolución | `/normatividad/resoluciones` | mostly PDF |
| Oficio | `/normatividad/oficios` | PDF |

**Stage 1 must also answer:**
- Is the Conceptos index searchable by topic (tema)? If yes, we can crawl by topic-relevance rather than chronologically.
- Does MinTrabajo attach formal legal citations (`Fundamento: CST art. XX`) inside the Concepto body? That determines how clean the edge-extraction pass will be.

---

## Parser sketch

### Concepto structure

MinTrabajo Conceptos follow a consistent shape:

1. **Referencia**: radicado number + consultor identity (stripped for PII).
2. **Asunto**: one-line subject.
3. **Problema**: the consultor's question.
4. **Consideraciones**: MinTrabajo's analysis, heavily cited.
5. **Conclusión**: the operative answer.

Store the 5 sections as separate fields on the chunk (`concept_tags` or dedicated columns). The `conclusion` section is the retrieval target 90% of the time.

### Circular structure

Typically a numbered list of instructions. Parse as a single "article" with full body; extract any `Artículo X del CST` / `Ley XXXX/YY art. Y` inline citations as edges.

---

## Edge vocabulary extension (shared with UGPP)

Reuse the UGPP-introduced `CLARIFIES` (`aclara`) and `SANCTIONS` (`sanciona`) canonicals. MinTrabajo also uses:

| Raw MinTrabajo token | Canonical | DB relation |
|---|---|---|
| Reitera Concepto N | `references` | `references` |
| Aclara Concepto N | `aclara` | `references` |
| Modifica Concepto N | `modifica` | `modifies` |
| Fundamento legal: CST art. X | `references` | `references` |
| Deroga Circular N | `deroga` | `derogates` |

No new `EdgeKind` needed — everything maps to what UGPP introduced.

---

## Crawl strategy

### Tier 1 (first production push — highest SMB accountant value)

Target specifically the reform-adjacent + core-ops topics:

1. **Reforma Laboral 2466/2025 implementation** — every MinTrabajo Circular / Concepto issued post-2025-06-25 on the reform. Expected ~15–25 docs; this is the freshest and most asked-about set.
2. **Reforma Pensional 2381/2024 implementation** — similar recency.
3. **Teletrabajo + trabajo remoto** — Ley 2088/2021 implementation Circulares.
4. **Contratación por prestación de servicios** — evergreen question; top 10 Conceptos on desnaturalización.
5. **Terminación del contrato + justa causa** — top 10 Conceptos.
6. **Jornada + horas extra + dominicales** — aligned with Ley 2101/2021.
7. **Estabilidad reforzada** — fuero materno / discapacidad / sindical.

### Tier 2 (follow-up)

- Historical Conceptos cited by Tier 1 docs (stub-resolve via two-pass merge handles most; re-crawl only if text body is needed).
- Older reforms' implementation Circulares.

### Discovery approach

Citation-graph ranking: pull the top-N most-cited Conceptos from Tier 1 crawl's outbound edges, then enrich them in Tier 2.

---

## Architecture (mirrors SUIN / DIAN / UGPP)

```
src/lia_graph/ingestion/mintrabajo/
├── __init__.py
├── fetcher.py
├── parser.py
├── harvest.py
└── bridge.py
```

Doc-id prefix: `mintrabajo_<doc_type>_<id>` — no collision with other sources.

---

## Risks

- **Source pattern instability** — MinTrabajo restructures its web presence more often than SUIN. Expect the URL patterns to drift; plan for a yearly re-survey.
- **PDF extraction noise** — same as UGPP; many Circulares are PDFs. pdfplumber handles well; budget for 5–10% log-and-skip rate on scanned docs.
- **Non-binding disclaimer** — same as UGPP. Tag chunks `concept_tags: ['mintrabajo_interpretive']` so the answer layer surfaces "authority: administrative, non-binding".
- **Reform-implementation race** — Ley 2466/2025 and Ley 2381/2024 are still having implementation Circulares issued. Plan to re-crawl this source monthly for at least the first year post-enactment.
- **Overlap with UGPP** — both bodies opine on aportes. UGPP is authoritative for parafiscales fiscalization; MinTrabajo is authoritative for contract / jornada / terminación. Don't dedup blindly — they can disagree; the corpus should carry both views with source labels.

## Handoff

- Before crawling, verify whether MinTrabajo has a bulk-data or API endpoint (some ministerios expose OData-style feeds). Save bandwidth if possible.
- Coordinate with the UGPP plan — the shared `CLARIFIES` / `SANCTIONS` `EdgeKind` members should land in one PR that benefits both sources.
- Do not crawl before the user explicitly approves the plan.
