# 14. Jurisprudencia Consejo de Estado — sentencias unificación + autos suspensión (gap-fill)

**Master:** ../corpus_population_plan.md §4.5 (Phase I)
**Owner:** unassigned
**Status:** 🟡 not started
**Target norm count:** ~40 (I3: ~25 sentencias · I4: ~15 autos)
**Phase batches affected:** I3, I4 (gap-fill; I2 already covered by Brief 10)

---

## What

Brief 10 (already delivered) covered Corte Constitucional sentencias on tax principles (I2) and the 5-acid-test I1 sentencias. The first-pass campaign smoke check on 2026-04-28 found:

| Batch | Status after Brief 10 | Reason |
|---|---|---|
| I1 (CC reformas — acid test) | PASS (5/4 norms) | Already in `explicit_list` |
| I2 (CC principios) | YAML-mismatch | YAML pattern uses literal `338` keyword which canonical sentencia form `sent.cc.C-NNN.YYYY` cannot embed; brief 10's 16 CC sentencias are in input set but YAML regex fails |
| I3 (CE Sección Cuarta unificación) | MISS (0 norms) | No CE sentencias delivered — expert deferred CE work |
| I4 (CE autos suspensión) | MISS (0 norms) | No CE autos delivered — Gap #1 (CE auto scraper) and CE site is JS-rendered SPA |

This brief fills I3 + I4. CC work stays in Brief 10. The brief is fixture-only-friendly (no live scraper required); the canonicalizer's vigencia harness consumes the parsed_articles row body verbatim.

---

## Source URLs (primary)

| URL | What | Status |
|---|---|---|
| https://www.consejodeestado.gov.co/decisiones_u/ | CE unificación decisions index. JS-rendered SPA — interactive navigation often required. | ⚠️ JS-rendered; URLs not always stable |
| https://www.consejodeestado.gov.co/seccion-cuarta/ | Sección Cuarta (tax/fiscal) landing | ✅ Live |
| https://normograma.dian.gov.co/dian/compilacion/ | DIAN republishes many CE decisions on tax law; URL pattern uses radicado | ✅ Live; verified for radicado 28920 |
| Example: `https://normograma.dian.gov.co/dian/compilacion/docs/25000-23-37-000-2014-00507-01_2022CE-SUJ-4-002.htm` | One Sección Cuarta unification ruling (DIAN-mirrored) | ✅ verified |

**Recommendation:** when the same ruling exists on both CE.gov.co and DIAN normograma, prefer the DIAN URL — it's stable and HTML-rendered.

---

## Canonical norm_id shape

Per master plan §5:

- **Sentencia CE:** `sent.ce.<RADICADO-NUM>.<YEAR>.<MM>.<DD>`
  Example: `sent.ce.28920.2025.07.03` (Sección Cuarta unificación, radicado 28920, decided 2025-07-03).
  The id is keyed by the **radicado number** plus the **decision date** — NOT by sección. The sección lives in the body as metadata. Full radicado (`25000-23-37-000-YYYY-NNNNN-01`) lives in the body too; the canonical id uses only the integer radicado-number suffix.
  Round-trip: `canonicalize("sent.ce.28920.2025.07.03")` → `"sent.ce.28920.2025.07.03"` ✓

- **Auto CE:** `auto.ce.<RADICADO-NUM>.<YEAR>.<MM>.<DD>`
  **Verified-real examples** (from `batches.yaml` E4 + G6 explicit_lists):
  - `auto.ce.082.2026.04.15` — Decreto 1474/2025 IE provisions (suspended).
  - `auto.ce.084.2026.04.15` — Decreto 1474/2025 IE provisions (suspended).
  - `auto.ce.28920.2024.12.16` — I.A. dividendos NCRGO.
  Round-trip: `canonicalize("auto.ce.082.2026.04.15")` → `"auto.ce.082.2026.04.15"` ✓

**Critical:** date in `YYYY.MM.DD` is **mandatory**. The radicado-only form (`auto.ce.082.2026`) is rejected by the writer at insert time. All sentencia/auto IDs must round-trip cleanly through `lia_graph.canon.canonicalize` or the writer rejects them.

---

## Parsing strategy

### I3 — CE Sección Cuarta unificación sentencias

1. **Discover candidates** by browsing the CE site and the DIAN normograma. Topical anchors:
   - Alcance de deducciones (Art. 107 ET) — necesidad, causalidad, proporcionalidad.
   - Corrección de declaraciones y firmeza.
   - Devoluciones de saldos a favor.
   - Compensaciones de retención en la fuente.
   - IVA on specific transactions (arrendamientos, servicios públicos domiciliarios).
2. **Per sentencia, capture:**
   - Full radicado as printed (`25000-23-37-000-YYYY-NNNNN-01(NNNNN)`).
   - Internal radicado number (the integer in parentheses or trailing position).
   - Decision date (`YYYY-MM-DD`).
   - Sección (e.g., "Cuarta").
   - Full text — facts, considerandos, RESUELVE.
3. **Emit row:**
   ```json
   {
     "norm_id": "sent.ce.<RADICADO-NUM>.<YEAR>.<MM>.<DD>",
     "norm_type": "sentencia_ce",
     "article_key": "Sentencia de Unificación Radicado <full-radicado>",
     "body": "[CITA: Sentencia CE <RADICADO-NUM> de <YYYY-MM-DD>]\n\n<full text>",
     "source_url": "https://normograma.dian.gov.co/.../<filename>.htm OR https://www.consejodeestado.gov.co/...",
     "fecha_emision": "<YYYY-MM-DD>",
     "emisor": "Consejo de Estado, Sección Cuarta",
     "tema": "ce_unificacion_<topic>"
   }
   ```

### I4 — Autos CE de suspensión provisional

1. **Live autos to find first** (use these as seed):
   - Auto 082/2026, decided 2026-04-15 — Decreto 1474/2025 IE.
   - Auto 084/2026, decided 2026-04-15 — Decreto 1474/2025 IE.
   - Auto radicado 28920, decided 2024-12-16 — I.A. dividendos NCRGO.
   Then sweep CE for additional suspension autos on Decreto 1474/2025 + Ley 2277/2022 reforms.
2. **Per auto, capture:**
   - Radicado number, notification date (`YYYY-MM-DD`).
   - Considerandos + RESUELVE (especially the part ordering the suspension).
3. **Emit row:**
   ```json
   {
     "norm_id": "auto.ce.<RADICADO-NUM>.<YEAR>.<MM>.<DD>",
     "norm_type": "auto_ce",
     "article_key": "Auto de Suspensión Provisional — Radicado <RADICADO>",
     "body": "[CITA: Auto CE <RADICADO> de <YYYY-MM-DD>]\n\n<full text>",
     "source_url": "https://www.consejodeestado.gov.co/... OR fixture path",
     "fecha_emision": "<YYYY-MM-DD>",
     "emisor": "Consejo de Estado",
     "tema": "ce_auto_suspension_provisional"
   }
   ```

The ingester `scripts/canonicalizer/ingest_expert_packet.py` doesn't yet have a `handle_brief_14` — adding one is a 30-line patch (mirror the brief 10 handler with `sent.ce.*` and `auto.ce.*` shapes). The ingester change should land in the same commit as the brief content.

---

## Edge cases observed

- **Radicado-only IDs are rejected.** `auto.ce.082.2026` fails canonical validation; only `auto.ce.082.2026.04.15` passes. Always capture the full date.
- **CE site is JS-rendered.** Some URLs only work after interactive search. When the URL is unstable, prefer the DIAN-hosted mirror; if no mirror exists, save the PDF and use the PDF URL.
- **Two-digit-year notation.** Some CE indices abbreviate the year — always expand to 4 digits in the canonical id.
- **Date confusion.** CE rulings sometimes carry a "fecha de decisión" and a separate "fecha de notificación." For I3 sentencias use the decision date; for I4 autos use the notification date (or the date printed at the head of the document if both appear).

---

## Smoke verification

After ingesting I3/I4 rows, run:

```bash
PYTHONPATH=src:. uv run python -c "
import sys
sys.path.insert(0, 'scripts/canonicalizer')
from extract_vigencia import _resolve_batch_input_set
from pathlib import Path
for bid in ['I3', 'I4']:
    norms = _resolve_batch_input_set(
        batches_config=Path('config/canonicalizer_run_v1/batches.yaml'),
        batch_id=bid,
        corpus_input_set=Path('evals/vigencia_extraction_v1/input_set.jsonl'),
        limit=None,
    )
    print(f'{bid}: {len(norms)} norms')
"
```

**Expected:** I3 ≥ 20, I4 ≥ 12 (≥80% of brief target 25 / 15).

---

## Dependencies on other briefs

- **Upstream:**
  - **Brief 10** delivered the CC sentencias (I2). Brief 14 is independent of brief 10's content but should ingest after brief 10 to keep run-log ordering clean.
  - **Brief 06** (Decretos legislativos COVID) and the Decreto 1474/2025 fixture (E4) — autos suspending those decretos belong to I4. Coordinate so E4 is ingested before I4 if possible (so the suspended-decreto target exists in the corpus when the auto's vigencia is extracted).
- **Downstream:** None.

---

## Scraper coverage and gaps

**Gap #1 (master plan §7) — CE auto scraper:**

- **Impact:** I4 autos cannot be live-fetched without CE scraper extension.
- **Fix path:** Edit `src/lia_graph/scrapers/consejo_estado.py::_resolve_url` to map `auto.ce.<NUM>.<YEAR>.<MM>.<DD>` to the CE search-by-radicado RPC.
- **Recommended fixture fallback:** add auto text directly to `tests/fixtures/scrapers/consejo_estado/autos/<radicado>.<YYYY>.<MM>.<DD>.html` and configure the scraper to check fixtures first. For ~15 autos this is faster than scraper extension.

---

**Last verified:** 2026-04-28
**Status:** Ready for assignment. Fixture-only path acceptable for I4 (recommended); I3 may use DIAN-mirror URLs.
