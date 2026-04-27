# Fix plan v2 — Lia Graph re-engineering (skill-integrated)

> **⚠️ SUPERSEDED 2026-04-27 by `fixplan_v3.md`.** v2 is preserved as historical record of the per-document-column persistence approach v3 replaces. Do NOT execute from this file. Read `fixplan_v3.md` (the plan) + `state_fixplan_v3.md` (the execution ledger) instead.
>
> **What v3 changed (summary):**
> - Persistence redesigned from columns on `documents` to three append-only tables (`norms`, `norm_vigencia_history`, `norm_citations`) per fixplan_v3 §0.3.
> - State enum extended from 7 to 11 states (added VC, VL, DI, RV) per fixplan_v3 §0.4.
> - Free-text `vigencia_basis` replaced by structured `change_source` discriminated union per fixplan_v3 §0.3.3.
> - Sub-units (parágrafos, numerales) promoted to first-class norm-ids per fixplan_v3 §0.5.
> - Two resolver functions (`norm_vigencia_at_date` for instantaneous tax / procedimiento; `norm_vigencia_for_period` for impuestos de período) per fixplan_v3 §0.6 — Art. 338 CP forces this.
> - Cron-driven cascade orchestration (1F sub-fix) for reviviscencia + future-dated state flips per fixplan_v3 §0.7.
> - v2's sub-fix 1C renamed 1B-ε; v2's 1B-γ split into 1B-γ (catalog + history) + 1B-δ (citations link backfill).
> - Activity 1.7 ✅ shipped 2026-04-26 (DT/SP/EC fixtures); skill eval seed at 7/30. Activity 1.5b ✅ shipped 2026-04-27 04:15 UTC (4 veredictos persisted to staging).
>
> **Funded:** USD 525K (v1: $500K + $25K skill-integration bump approved 2026-04-26 evening). Decision per `makeorbreak_v1.md`: **SAVE**.
> **Timeline target:** 14 weeks to soft-launch readiness.
> **Team shape recommended:** 1 tech lead + 2 senior backend engineers + 0.5 SME bandwidth + 0.25 ops/data + 0.5 frontend.
> **Companion docs:** `makeorbreak_v1.md` (the why), `exec_summary_v1.md` (one-page founder view), `skill_integration_v1.md` (the change-driver behind v2), `sme_corpus_inventory_2026-04-26.md` (SME's authoritative law inventory), `vigencia-checker` skill at `.claude/skills/vigencia-checker/`.
> **Reader assumption:** **none.** A fresh engineer or fresh LLM with zero project context can start at §0 and execute. If you've worked in this repo before, skim §0–§0.7 and jump to §1.
> **Supersedes:** `fixplan_v1.md` (preserved as historical record of the pre-skill-integration plan).
> **Superseded by:** `fixplan_v3.md` (preserved here as historical record).

---

## §0 — What happened with vigencia in the graph (honest diagnosis)

Code-level audit done 2026-04-26 evening. Unchanged from v1.

The architecture was designed with vigencia in mind — `:ArticleNode.status`, edge types `SUPERSEDES / DEROGATES / MODIFIES / SUSPENDS / STRUCK_DOWN_BY / ANULA`, Supabase columns `vigencia / vigencia_basis / vigencia_ruling_id`. **But the engineers built the right house and never plumbed it:**

1. The classifier (`ingestion_classifier.py:279-298`) emits zero vigencia metadata. Only the `parser.py:234` regex (`status = "derogado" if "derogado" appears in text`) writes anything.
2. The sink (`supabase_sink.py:639,646`) writes the binary flag but `vigencia_basis` and `vigencia_ruling_id` stay NULL forever.
3. The retriever's vigencia filter is silently bypassed when `filter_effective_date_max` is passed (the common case). Activity 1 (2026-04-29) fixed this — but the binary flag's coverage is too sparse to bite.
4. The user-visible historical features (`answer_historical_recap.py`, `answer_comparative_regime.py`) are post-retrieval narrative formatters; they cannot prevent retrieval from surfacing a derogated article in the first place.
5. The corpus's source documents (ET, normograma, Mintic normograma) contain vigencia info as PROSE ("Derogado por Ley 1819/2016 Art. 5"), not extractable structured data.

**v2 closes all 5 breaks via skill-driven extraction + structural retrieval changes.**

## §0.1 — What changed since v1 (the deep re-engineering)

| Change | Source | Impact |
|---|---|---|
| **Vigencia ontology**: 6 states → **7 states** (V/VM/DE/DT/SP/IE/EC); single timeline → **2D (formal × period)** model | Expert vigencia-checker skill | Fix 1A redesign; Fix 1D retriever now needs `vigencia_at_date` planner signal; Fix 1E expands from 4 to 7 chip variants |
| **Burden of proof inverted**: extractor MUST consult ≥ 2 primary sources or refuse veredicto | Expert skill | Fix 1B becomes a tool-using agent loop, not a single LLM call |
| **Fix 1B re-scoped** into 1B-α (scrapers, NEW) + 1B-β (skill-guided extractor) + 1B-γ (materialization, was Fix 1C) | Skill's source-discipline mandate | +$45K scrapers; +$30K extractor (vs $30K naive); −$15K (Fix 1C folded) |
| **Fix 5 judge schema** = skill's audit-LIA TRANCHE format (INCORRECTO/INCOMPLETO/OMISIÓN + GRAVEDAD CRÍTICO/MAYOR/MENOR) | Skill's `patrones-citacion.md` | −$3K (don't design from scratch); higher consistency with rest of system |
| **Activity 1 result embedded as gate-3 evidence** | Live measurement 2026-04-29 | Proves the architectural fix works AND that binary flag is too coarse to alone bite — validates Fix 1B priority |
| **Budget**: $500K → $525K | Skill-driven new work absorbed mostly into the $60K reserve; +$25K residual | Operator-approved 2026-04-26 evening |
| **Timeline shape**: Fix 1B-α (scrapers) on critical path week 1 | Without scrapers, skill-guided extraction at corpus scale is prohibitively expensive | Fix 1A goes faster (skill closes Gate 1+2 of design); Fix 1B-β starts week 4 once scrapers exist |
| **Decreto 1474/2025 = unambiguous SP candidate** | SME inventory + skill | Activity 1.5 now skill-guided per-article, not wholesale |

## §0.5 — Required reading before you write any code (60 min, in this order)

1. **`CLAUDE.md`** (repo root, ~6 KB) — non-negotiables, run modes, hot path, decision rules. **Pay attention to the six-gate lifecycle policy.** Mandatory.
2. **`AGENTS.md`** (repo root) — layer ownership and surface boundaries (`main chat` vs `Normativa` vs `Interpretación` are distinct surfaces).
3. **`docs/orchestration/orchestration.md`** (~30 KB) — full architecture. The versioned env matrix at the bottom is authoritative.
4. **`docs/orchestration/retrieval-runbook.md`** — line-level walkthrough of `pipeline_d/retriever_supabase.py` + `retriever_falkor.py`. Fix 1C rewrites parts of these.
5. **`docs/orchestration/coherence-gate-runbook.md`** — every refusal mode (`fallback_reason`) mapped to its origin file:line. Fix 1C + Fix 3 both interact here.
6. **`docs/learnings/README.md`** + scan the file list under `docs/learnings/{retrieval,ingestion,process}/` — 25 closed-fix lessons (Activity 1's `hybrid_search-overload-2026-04-27` lives here too). Read fully any whose title sounds adjacent to your fix.
7. **`docs/re-engineer/makeorbreak_v1.md`** §0 ("Honest answer to 'what happened with vigencia in the graph?'") + §2 ("five structural defects") (~15 min).
8. **`docs/re-engineer/skill_integration_v1.md`** — the change-driver behind v2; explains the skill, lists what changed, why, and the budget shift.
9. **`docs/re-engineer/sme_corpus_inventory_2026-04-26.md`** — the SME's 24-law authoritative inventory; binding for any "is this doc safe to flag?" question.
10. **`.claude/skills/vigencia-checker/SKILL.md`** + scan of references and checklists (~20 min). The skill IS the verification protocol. Every Fix 1 sub-fix consumes it.
11. **`docs/re-engineer/fixplan_v2.md`** — this document, §0–§0.7 then your assigned Fix.

If you read nothing else: read `CLAUDE.md`, the two runbooks, the skill's `SKILL.md`, and `skill_integration_v1.md`. Everything else is reference.

## §0.6 — Project conventions every fix must follow

These are not preferences; they are mandatory. Items marked **(NEW v2)** are the skill-integration deltas vs v1.

| Convention | Where it lives | What it means for your fix |
|---|---|---|
| **Six-gate lifecycle** | `docs/aa_next/README.md` + `CLAUDE.md` | Every pipeline change passes idea → plan → measurable success criterion → test plan → greenlight → refine-or-discard. **Unit tests green ≠ improvement.** |
| **Tests via `make test-batched`** | `Makefile` + `tests/conftest.py` guard | Conftest aborts unless `LIA_BATCHED_RUNNER=1`. Single tests: `PYTHONPATH=src:. uv run pytest tests/test_X.py -q`. |
| **Migrations apply via `supabase db push --linked`** | per Activity 1 + v5 §1.D workflow | Cloud writes pre-authorized for Lia Graph (NOT LIA_contadores). Announce in one line, then execute. |
| **`CREATE OR REPLACE FUNCTION` requires explicit `DROP FUNCTION IF EXISTS` first when changing parameter list** | `docs/learnings/retrieval/hybrid_search-overload-2026-04-27.md` | Verified the hard way 2026-04-27. Do NOT relearn. |
| **Env matrix bump on any launcher / `LIA_*` / `query_mode` change** | `docs/orchestration/orchestration.md` | Bump version + change-log row + mirror tables in `env_guide.md` + `CLAUDE.md` + `/orchestration` HTML. |
| **Time format: Bogotá AM/PM for user surfaces; UTC ISO for machine logs** | `feedback_time_format_bogota.md` | Helpers in `scripts/eval/engine.py:bogota_now_human()`. |
| **Reuse `scripts/eval/engine.py` for any new chat-based eval** | (extracted 2026-04-27 §1.G) | `ChatClient`, `post_json`, `append_jsonl`, `completed_ids`, `git_sha`, `write_manifest`. Do not write a third copy. |
| **Atomic-design first for any UI** | `feedback_atomic_design_first.md` | Read `frontend/src/shared/ui/atoms+molecules` BEFORE writing UI. Fix 1D vigencia chips mirror `subtopicChip.ts`. |
| **Plain-language reports to operator** | `feedback_plain_language_communication.md` | Status reports default to short, jargon-free. |
| **No threshold lowering on missed gates** | `feedback_thresholds_no_lower.md` | Document exception per case; do NOT relax. |
| **Long-running Python jobs: detached + heartbeat** | `CLAUDE.md` last section | `nohup + disown + > log 2>&1` (NO tee). Fix 1B-β extractor batch hits this hard. |
| **`pyproject.toml` entry points + run modes** | repo root + `scripts/dev-launcher.mjs` | `lia-ui`, `lia-graph-artifacts`, `lia-deps-check`. Validation runs on `dev:staging`. |
| **(NEW v2) Vigencia veredicto requires skill invocation** | `.claude/skills/vigencia-checker/SKILL.md` | Any code or content that asserts vigencia/derogación MUST consume the skill's veredicto. No code path may write a `Vigencia` value object that wasn't produced by the skill or by an SME-signed manual override (with audit trail). |
| **(NEW v2) Burden-of-proof inversion** | Skill's principle rector | Extractor / classifier MUST refuse to emit a veredicto if double-primary-source verification is incomplete. Refusing is success; guessing is failure. |
| **(NEW v2) Per-parágrafo granularity** | Skill's `tipologia-modificaciones.md` "Tabla resumen" | Vigencia state is per-parágrafo, not just per-article. Implementations must accept "Inciso 1 → V; Parágrafo 1 → VM; Parágrafo 2 → DE." |
| **(NEW v2) Audit-LIA TRANCHE as judge schema** | Skill's `patrones-citacion.md` §"Integración" | Fix 5 golden judge MUST emit INCORRECTO/INCOMPLETO/OMISIÓN + GRAVEDAD CRÍTICO/MAYOR/MENOR. Replaces my v1 PASS/SOFT_FAIL/HARD_FAIL — they map cleanly. |

## §0.7 — The vigencia-checker skill (15 min skim)

**What it is.** A complete verification protocol for Colombian tax-law vigencia, delivered by SME 2026-04-26 evening, installed at `.claude/skills/vigencia-checker/`. 8 files, 1428 LOC. Acts as both:

1. **A reference taxonomy + procedure** that engineers and the LLM consult when reasoning about vigencia.
2. **An invocable agent loop** that produces structured veredictos for any specific norm + period.

**The 7 states.** All vigencia analysis collapses into exactly one:

| Code | Meaning | Citation rule |
|---|---|---|
| **V** | Vigente sin modificaciones | Cite freely |
| **VM** | Vigente modificada | Cite ONLY vigente text + chain of modifications |
| **DE** | Derogada expresa | NEVER cite as vigente; historical-only |
| **DT** | Derogada tácita | Only cite if pronouncement official; otherwise NO veredicto |
| **SP** | Suspendida provisional | Mandatory advertencia + T-series link |
| **IE** | Inexequible | NEVER cite (unless effects diferidos active) |
| **EC** | Exequibilidad condicionada | Cite WITH literal condicionamiento de la Corte |

**The 2D model.** A norm's veredicto is `(state, applicability_to_period)`. State is global; applicability is per-period. A norm can be DE today but apply to AG 2023 by ultractividad. A norm can be V today but not apply to AG 2025 by Art. 338 CP.

**The 5-step flow** (mandatory):
1. Identification (norm type, number, parágrafo)
2. ≥ 2 primary sources (Senado / SUIN / DIAN / Corte / CE per source-type rules)
3. Temporal-fiscal verification (Art. 363 + 338 CP)
4. Tácita-derogation + active-demands check
5. Structured veredicto OR refusal-with-incertidumbre

**When to invoke.** Skill activates automatically when LLM activity touches: artículo / decreto / ley / resolución number; verbs *aplica / rige / vigente / fue modificado / fue derogado*; questions like *¿puedo aplicar X para AG 2024?*; or any mention of recent reforms (Ley 2277/2022, Ley 2294/2023, Decreto 1474/2025). It does NOT activate for abstract conceptual questions or pure aritmética.

**When the skill refuses.** No primary source available; primary sources contradict; demanda activa without sentencia o medida cautelar; speculative future reforms; municipal norms without gaceta digital. **Refusing IS the correct output in those cases.**

---

## §0.8 — Skill invocation mechanics + data contracts

The skill design is complete. This section pins down **how Python code calls it** and **what data flows between sub-fixes** so a fresh engineer or LLM can implement Activity 1.5, Fix 1B-β, Fix 1B-γ, Fix 5 judge, and Fix 6 without re-deriving the integration shape.

### §0.8.1 — Invocation mechanism (decided)

**Choice: Gemini 2.5 Pro via the project's existing OpenAI-compatible adapter (`src/lia_graph/gemini_runtime.py`).** Rejected alternatives:
- ❌ Claude Code CLI subprocess — couples runtime to dev tooling; not portable to CI / production extractor batch.
- ❌ Pure-Python re-implementation of the protocol — discards the LLM's reasoning capacity that the skill was designed around (e.g. "is this norma posterior incompatible with the anterior?" requires legal interpretation).
- ❌ Any other provider — the project already has a Gemini API key wired and a working OpenAI-compat adapter. Introducing a second provider is unnecessary surface.

**Why the project's existing Gemini adapter:**
- Already used by ingestion classifier + retrieval planner; same convention end-to-end.
- Uses Gemini's OpenAI-compatibility endpoint (`https://generativelanguage.googleapis.com/v1beta/openai`) — supports tool calling natively via the `tools` parameter.
- Pure stdlib (`urllib.request`); no new SDK dependency.
- Extends cleanly: the harness wraps the existing `GeminiChatAdapter` with a tool-use loop + scraper-tool registry.

**Model selection:**
- **`gemini-2.5-pro`** for ALL skill invocations (batch extraction in Fix 1B-β, Fix 5 judge, Activity 1.5, Fix 6 editorial). Single model simplifies the harness — Gemini 2.5 Pro is the right capability tier for legal-reasoning + tool-use, and the cost differential to Flash isn't worth the accuracy trade on a verification path where a single confident-wrong answer kills credibility.
- Explicitly NOT `gemini-2.5-flash`: the operator memory and `feedback_thresholds_no_lower` discipline both apply — we don't trade quality for cost on the path that determines whether an answer is safe to send to a client.

**Per-article extraction cost:** ~$0.039 with Gemini 2.5 Pro at the OpenAI-compat endpoint. For 7,883 articles: ~$307 total. Detailed breakdown in §0.8.5.

**Context caching note.** Gemini's native API supports explicit context caching (~75% discount on cached tokens), but the project's existing OpenAI-compat path doesn't expose it yet. The cost delta from skipping caching is small (~$40 across the entire 7,883-article batch) — not worth introducing a second SDK or breaking the project's adapter convention. If batch cost ever becomes a constraint, switching the adapter to Gemini's native client is a focused 1-day change.

### §0.8.2 — The harness API (Python contract)

The single Python entry point all sub-fixes consume. Mirrors the existing `GeminiChatAdapter` pattern in `src/lia_graph/gemini_runtime.py` exactly — pure stdlib (`urllib.request`), OpenAI-compat endpoint, no new SDK dependency.

```python
# src/lia_graph/vigencia_extractor.py

from typing import Literal
from datetime import date
from dataclasses import dataclass
from lia_graph.gemini_runtime import GeminiChatAdapter, DEFAULT_GEMINI_OPENAI_BASE_URL
from lia_graph.vigencia import Vigencia, PeriodoFiscal
from lia_graph.scrapers import ScraperRegistry

class VigenciaSkillHarness:
    """Single entry point for invoking vigencia-checker from Python.

    Loads skill content once at construction (~20 KB across SKILL.md +
    4 references + 3 checklists) and prepends it as the system message
    on every invocation. Wraps the project's GeminiChatAdapter with a
    tool-use loop that exposes the 5 scrapers as OpenAI-compat tools.

    Exposes a single method sub-fixes call:
        verify_norm(norm_type, norm_id, parágrafo, periodo) -> VigenciaResult
    """

    def __init__(
        self,
        *,
        scrapers: ScraperRegistry,
        model: str = "gemini-2.5-pro",
        api_key: str,                          # from env LIA_GEMINI_API_KEY
        base_url: str = DEFAULT_GEMINI_OPENAI_BASE_URL,
        max_tool_iterations: int = 10,
        timeout_seconds: float = 60.0,
        temperature: float = 0.1,              # low — verification is not creative
    ):
        self._adapter = GeminiChatAdapter(
            model=model,
            api_key=api_key,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            temperature=temperature,
        )
        self._scrapers = scrapers
        self._max_iterations = max_tool_iterations
        self._system_prompt = _load_skill_system_prompt()  # reads .claude/skills/vigencia-checker/

    def verify_norm(
        self,
        *,
        norm_type: Literal["articulo_et", "decreto", "resolucion_dian", "ley", "concepto", "sentencia"],
        norm_id: str,                 # "Art. 689-3 ET" | "D. 1474/2025" | "Res. DIAN 000162/2023"
        parágrafo: str | None,        # "Parágrafo 2" | "Inciso 1" | None for whole article
        periodo: PeriodoFiscal,
    ) -> "VigenciaResult":
        """Invokes the skill with scraper tools available; returns structured result.

        Internally runs an OpenAI-compat chat-completion loop with `tools` set to
        the 5 scraper tool definitions. Loop terminates on (a) the model emitting
        the structured veredicto block, (b) the model declaring refusal, or (c)
        max_tool_iterations exhausted (logged as a refusal with reason).
        """
        ...

@dataclass(frozen=True)
class VigenciaResult:
    """Either a successful veredicto OR a documented refusal — never an unverified guess."""
    veredicto: Vigencia | None        # None ↔ refusal
    refusal_reason: str | None        # set when veredicto is None
    missing_sources: tuple[str, ...]  # sources the skill needed but couldn't reach
    audit: ExtractionAudit            # always populated
```

**Tool-use loop.** The harness exposes the 5 scraper modules from Fix 1B-α as OpenAI-compat tool definitions (Gemini's compatibility layer accepts the standard `tools` + `tool_choice` parameters). The skill (running in the LLM) decides which scraper to invoke per the source-selection rules in `fuentes-primarias.md`. The harness enforces:
- Max 10 tool iterations per article (prevents runaway loops).
- Each scraper call must succeed OR the skill must record the failure as a `missing_source` and decide whether to refuse or continue with one source (refusing is correct per the burden-of-proof rule).
- Tool results are accumulated into the conversation as `role=tool` messages; the skill's final assistant message is parsed for the structured veredicto block (the bordered `═══...═══` format from `patrones-citacion.md`).
- `temperature=0.1` — verification is not creative work; the model should be deterministic about reading sources.

**API key.** Read from `LIA_GEMINI_API_KEY` env var, set per the existing `.env.local` / `.env.staging` convention (same key already used by classifier + planner). No new credential to provision.

**Output parsing.** The skill produces the veredicto in the format defined in `patrones-citacion.md` §"Output mínimo." The harness regexes the bordered block (`═══...═══`) and parses each labeled line into the `Vigencia` dataclass.

### §0.8.3 — Data schemas (4 contracts)

**(1) `Vigencia` JSON serialization** (consumed by Fix 1B-γ materialization, Fix 1C retriever, Fix 1D chips, Fix 5 judge):

```json
{
  "state": "VM",
  "vigente_desde": "2021-09-14",
  "vigente_hasta": null,
  "derogado_por": null,
  "modificado_por": [
    {
      "norm_type": "ley",
      "norm_id": "Ley 2294/2023",
      "article": "Art. 69",
      "fecha": "2023-05-19",
      "primary_source_url": "https://www.secretariasenado.gov.co/senado/basedoc/ley_2294_2023_pr001.html#69"
    }
  ],
  "suspension": null,
  "inexequibilidad": null,
  "condicionamiento": null,
  "regimen_transicion": null,
  "fuentes_primarias_consultadas": [
    {"norm_type": "url", "norm_id": "secretaria_senado", "primary_source_url": "https://...", "fecha": "2026-05-01"},
    {"norm_type": "url", "norm_id": "dian_normograma",   "primary_source_url": "https://...", "fecha": "2026-05-01"}
  ],
  "extraction_audit": {
    "skill_version": "vigencia-checker@1.0",
    "model": "gemini-2.5-pro",
    "tool_iterations": 3,
    "wall_ms": 8400,
    "cost_usd_estimate": 0.062
  }
}
```

**(2) Per-article extraction file** (`evals/vigencia_extraction_v1/<article_id>.json` — written by Fix 1B-β, read by Fix 1B-γ):

```json
{
  "article_id": "art-689-3-ET",
  "norm_type": "articulo_et",
  "norm_id": "Art. 689-3 ET",
  "parágrafo": null,
  "periodo": {"impuesto": "renta", "year": 2026, "period_label": "AG 2026", "period_start": "2026-01-01", "period_end": "2026-12-31"},
  "extraction_run_id": "20260501T120000Z",
  "extracted_at_utc": "2026-05-01T12:00:00Z",
  "result": {
    "veredicto": { /* Vigencia JSON from §0.8.3(1), or null */ },
    "refusal_reason": null,
    "missing_sources": []
  }
}
```

**(3) Scraper cache schema** (SQLite at `var/scraper_cache.db` — written + read by Fix 1B-α):

```sql
CREATE TABLE scraper_cache (
    source            TEXT     NOT NULL,  -- 'secretaria_senado' | 'dian_normograma' | 'suin_juriscol' | 'corte_constitucional' | 'consejo_estado'
    norm_id           TEXT     NOT NULL,  -- canonical norm identifier; SAME format as Vigencia.modificado_por[].norm_id
    fetched_at_utc    TEXT     NOT NULL,  -- ISO 8601
    expires_at_utc    TEXT     NOT NULL,  -- 90 days from fetch for current-AG queries; longer for historical
    http_status       INTEGER  NOT NULL,
    raw_html_gzip     BLOB,                -- gzipped raw HTML for re-parsing if selectors evolve
    parsed_json       TEXT,                -- structured extraction (article body, modification notes, judicial pointers)
    parser_version    TEXT     NOT NULL,   -- SemVer of the scraper module that wrote this row
    PRIMARY KEY (source, norm_id)
);
CREATE INDEX idx_scraper_cache_expires ON scraper_cache(expires_at_utc);
CREATE INDEX idx_scraper_cache_source  ON scraper_cache(source);
```

**Cache invalidation policy:** the Re-Verify Cron (Fix 1B-α §11.5) deletes rows where `expires_at_utc < now()` then re-fetches via the next scheduled extraction pass. It also wholesale-invalidates by `source` after any reforma tributaria detected in the source.

**(4) Skill Eval case fixture** (`evals/skill_eval_v1/cases/<case_id>.yaml` — see §0.8.4 for usage):

```yaml
case_id: art_689_3_AG2025_vigente_modificada
norm_type: articulo_et
norm_id: "Art. 689-3 ET"
parágrafo: null
periodo: {impuesto: renta, year: 2025, period_label: "AG 2025"}
expected_state: VM
expected_modificado_por:
  - {norm_id: "Ley 2294/2023", articulo: "Art. 69", fecha: "2023-05-19"}
expected_applies_to_periodo: {aplica: "Sí", justificacion: "Vigente desde 2021; aplica plenamente a AG 2025"}
expected_min_primary_sources: 2
sme_signoff: alejandro_2026-04-30
notes: |
  Caso canónico VM. La modificación de Ley 2294/2023 prorroga la vigencia
  del beneficio de auditoría hasta AG 2026. Skill debe citar Senado +
  DIAN Normograma + (opcional) Sentencia de prórroga si existe.
```

### §0.8.4 — Skill Eval set design

**Purpose.** Tests if the skill captures the errors it claims to. Without this gate, we cannot trust the skill at corpus scale (Fix 1B-β).

**Composition (30 cases by state coverage):**
- 4 cases per state × 7 states = 28
- Plus 2 boundary cases: 1 case where the skill should refuse (DT without official pronouncement); 1 case where the skill should detect EC and emit literal condicionamiento

**Sourcing the cases:**
- 13 from the LIA-known-errors found in §1.G SME review (e.g. art. 689-1 cited as vigente; firmeza 6 años; dividend 10%)
- 7 from the corpus T-series (each T-series file documents a vigencia-sensitive case the SME already analyzed)
- 10 clean controls drafted by the SME explicitly for skill validation, covering the states that don't appear in the LIA errors or T-series

**Authoring cadence:** SME drafts 5/week starting week 1; complete by week 6 (when Fix 1B-β kill switch needs them).

**Judge mechanism:**
- For each case: invoke `VigenciaSkillHarness.verify_norm(...)` with the case's `norm_id` + `periodo`.
- Compare the emitted `VigenciaResult` against the case's `expected_*` fields.
- **Hard checks (auto-failable):**
  - `result.veredicto.state == case.expected_state` — exact enum match
  - `len(result.veredicto.fuentes_primarias_consultadas) >= case.expected_min_primary_sources`
  - For VM: every entry in `case.expected_modificado_por` is present in `result.veredicto.modificado_por`
  - For SP: `result.veredicto.suspension` is non-null AND cites the expected auto
  - For IE: `result.veredicto.inexequibilidad` is non-null AND cites the expected sentencia
  - For EC: `result.veredicto.condicionamiento` exact-substring matches the expected literal Court text (no paraphrase)
  - For refusal cases: `result.veredicto is None AND result.refusal_reason matches case.expected_refusal_reason`
- **Soft check (LLM-judged, score 0-10):**
  - `result.veredicto.applies_to(case.periodo).justificacion` semantic similarity to `case.expected_applies_to_periodo.justificacion` ≥ 0.85

**Gate criterion (binding for Fix 1B-β go-ahead):**
- ≥ 90% PASS on hard checks (≥ 27/30)
- 0 false-positive veredictos (skill emitting a state when expected refusal)
- Soft-check median score ≥ 8.0

**Output shape:** `evals/skill_eval_v1/runs/<utc_iso>/{report.md, classified.jsonl, verbatim.md}` — mirrors the §1.G runner output exactly so the same eval engine (`scripts/eval/engine.py`) is reused.

**Files.**
- *Read first:* `scripts/eval/engine.py` (reuse — do NOT write a 4th copy of the runner plumbing); `scripts/eval/run_sme_validation.py` + `sme_validation_report.py` (precedent shape).
- *Create:* `evals/skill_eval_v1/cases/*.yaml` (30 SME-authored YAML files); `scripts/eval/run_skill_eval.py` (loads cases, invokes harness, classifies, reports); `scripts/eval/skill_eval_judge.py` (hard checks + soft LLM-judged check).

### §0.8.5 — Cost economics (per-article batch extraction)

Gemini 2.5 Pro pricing via the OpenAI-compat endpoint (≤200K context tier):
- Input: $1.25 per 1M tokens
- Output: $10.00 per 1M tokens
- Tool/function-call payloads: same input/output tokenization (no separate fee)

| Phase | Cost per article | 7,883 articles |
|---|---:|---:|
| Input tokens per call (system prompt ~5K + article body + tool results ~10K = ~15K) | $0.0188 | $148 |
| Output tokens per call (veredicto + intermediate tool-call thinking ~2K) | $0.0200 | $158 |
| Scraper tool calls per article (~3 fetches × $0 LLM cost — fully borne by 1B-α infra) | $0 | $0 |
| **Per-article total** | **$0.039** | **$306** |

**Versus naive (no scrapers, live web fetch every call, longer prompts):** ~$0.12/article × 7,883 = $946. **Scrapers save ~$640** vs the naive path. The rest of Fix 1B-α's $45K budget is justified by the latency win (cached fetches ~50ms vs live ~2-5s) and reliability (offline-capable extraction, retryable from cache).

**Versus Gemini 2.5 Flash:** Flash is ~10× cheaper (~$30 total batch) but explicitly REJECTED per §0.8.1 — verification accuracy is the load-bearing axis; the operator's "no off flags" + `feedback_thresholds_no_lower` discipline applies.

**Throughput:** with rate-limited scrapers (≤ 2 req/s per source) + 4 parallel extraction workers + Gemini 2.5 Pro's typical ~3-8s response time, expected wall time ≈ 6–10 hours for the full 7,883-article batch. Use the long-running-job pattern (`nohup + disown + heartbeat` per `CLAUDE.md`).

**Total Fix 1 LLM spend (Fix 1B-β extraction + Fix 5 judge + Activity 1.5):** ≈ $400 across 14 weeks. Trivial against the $525K total — the budget envelope for "LLM extraction" line in §11 ($1K) covers it with room.

---

## §1 — Fix overview (v2)

| Fix | Title | Weeks | Engineers | $K | Status gate |
|---|---|---|---|---|---|
| **Activity 1** ✅ | SQL-only vigencia filter ship (DONE 2026-04-29) | — | — | — | ✅ shipped; measured outcome in `docs/learnings/retrieval/vigencia-binary-flag-too-coarse.md`; learnings folded into Fix 1C |
| **Activity 1.5** ✅ | Skill-guided verification — Decreto 1474/2025 (DONE 2026-04-26 ev) | — | — | — | ✅ outcome in `docs/re-engineer/activity_1_5_outcome.md`; veredicto in `evals/activity_1_5/decreto_1474_2025_veredicto.json`; surfaced corpus hallucination → Fix 6 expansion |
| **Activity 1.6** ✅ | Skill-guided verification — 3 canonical norms (DONE 2026-04-26 ev) | — | — | — | ✅ 3 veredicto fixtures (`art_689_3 / art_158_1 / art_290_num5`) seed Fix 5 skill eval set |
| **Activity 1.5b** | **NEW** — manual persistence of 4 veredictos to staging Supabase + Falkor (no full Fix 1B-γ yet) | 1 | 0.5 | 1 | week-1 |
| **Activity 1.7** | Skill-guided verification — 3 norms covering states DT / SP / EC (NEW — completes 7-state coverage) | 1 | 0.5 | 1 | week-1 |
| **Activity 1.8** | Per-article skill verification on Ley 1429 articles (deferred until 1B-α scrapers live) | post-1B-α | 0.5 | 3 | week-5 |
| **Fix 1A** | Vigencia ontology Python implementation (skill-defined; just code it) | 1–2 | 0.5 | 8 | week-2 |
| **Fix 1B-α** | **NEW** — scraper + cache infra (Senado / SUIN / DIAN / Corte / CE) | 1–4 | 1.0 | 45 | week-4 |
| **Fix 1B-β** | Skill-guided extractor batch over 7,883 articles | 4–6 | 1.0 | 30 | week-6 |
| **Fix 1B-γ** | Materialize vigencia in Supabase + Falkor (was Fix 1C in v1) | 6–7 | 1.0 | 15 | week-7 |
| **Fix 1C** | Plumb 2D vigencia model into retrieval (was Fix 1D in v1) | 7–9 | 1.5 | 30 | week-9 |
| **Fix 1D** | User-facing 7-variant vigencia chips (was Fix 1E in v1) | 9–10 | 0.5 frontend | 28 | week-10 |
| **Fix 2** | Parámetros móviles map (UVT/SMMLV/IPC/topical thresholds) + runtime injection | 2–6 | 1.0 | 80 | week-6 |
| **Fix 3** | Anti-hallucination guard on partial mode | 7–10 | 1.0 | 50 | week-10 |
| **Fix 4** | Ghost-topic kill + corpus completeness audit | 8–13 | 0.5 + SME | 70 | week-13 |
| **Fix 5** | Golden-answer regression suite (TRANCHE schema, skill-as-judge) | 1–14 | 0.5 + SME | 27 | week-14 |
| **Fix 6** | Internal corpus consistency editorial pass + corpus-wide hallucination audit (skill as diagnostic) | 11–13 | 0.5 + SME | 40 | week-13 |
| **Skill Eval** | **NEW** — 30-case eval set for vigencia-checker itself (4 cases already authored from Activities 1.5+1.6) | 4–6 | 0.5 + SME | 15 | week-6 |
| **Re-Verify Cron** | **MOVED** week 13 → week 4 per `docs/learnings/process/re-verify-cron-criticality.md` (Activity 1.5 found stale corpus + criticality elevated) | 4–5 | 0.5 | 8 | week-5 |
| | **Reserve / contingency** (after $52K absorbed by skill work; $4K consumed by Activities 1.7+1.8) | — | — | 4 | unallocated |
| | **Total** | 14 wks | 5–6 FTE-weeks/wk avg | **525** | |

---

## §2 — Fix 1 (vigencia structural)

The biggest fix. Now decomposed into 6 sub-fixes (was 5 in v1). Skill-guided throughout.

### 2.1 Sub-fix 1A — Vigencia ontology Python implementation

**What.** The skill's 7-state taxonomy is the design. We implement it in Python. The dataclass + Pydantic model + helper methods.

**The dataclass** (skeleton — full impl in Sub-fix code):

```python
# src/lia_graph/vigencia.py
from enum import Enum
from datetime import date
from dataclasses import dataclass

class VigenciaState(str, Enum):
    V  = "vigente_sin_modificaciones"
    VM = "vigente_modificada"
    DE = "derogada_expresa"
    DT = "derogada_tacita"
    SP = "suspendida_provisional"
    IE = "inexequible"
    EC = "exequibilidad_condicionada"

@dataclass(frozen=True)
class Citation:
    norm_type: str
    norm_id: str
    article: str | None
    fecha: date | None
    primary_source_url: str | None

@dataclass(frozen=True)
class Vigencia:
    state: VigenciaState
    vigente_desde: date | None
    vigente_hasta: date | None
    derogado_por: Citation | None         # set when DE
    modificado_por: tuple[Citation, ...]  # cronological chain when VM
    suspension: Citation | None           # set when SP — must link to T-series
    inexequibilidad: Citation | None      # set when IE — includes effects timing
    condicionamiento: str | None          # set when EC — LITERAL Court text
    regimen_transicion: Citation | None
    fuentes_primarias_consultadas: tuple[Citation, ...]   # ≥ 2 for veredicto
    extraction_audit: dict
    # The 2D applicability dimension — the v1 ontology was missing this
    def applies_to(self, periodo: 'PeriodoFiscal') -> 'AplicabilidadVerdict':
        """Returns (Sí | No | Parcial, justification) per skill's reglas-temporales."""
        ...

@dataclass(frozen=True)
class PeriodoFiscal:
    """An evaluation period. Year for renta, bimester/quarter for IVA, month for retención."""
    impuesto: str  # 'renta' | 'iva' | 'retencion_fuente' | 'ica' | 'patrimonio'
    year: int
    period_label: str  # 'AG 2025' | 'bimestre 3-4 2026' | 'mes 06-2025'
    period_start: date
    period_end: date

@dataclass(frozen=True)
class AplicabilidadVerdict:
    aplica: str  # 'Sí' | 'No' | 'Parcial'
    justificacion: str  # 'Art. 338 CP' | 'ultractividad' | 'régimen de transición' | etc.
    norm_version_aplicable: str | None  # for VM: which version of the text applies to this period
```

**Success criteria.**
- The dataclass + 12 unit tests covering the canonical Colombian patterns from `tipologia-modificaciones.md` (one per state, plus 5 edge cases: parágrafo divergence, IE diferred, EC literal text, ultractividad, Art. 338 CP).
- Round-trip: serialize to JSON / deserialize → identity preserved.
- The `applies_to` method correctly returns Sí/No/Parcial for 8 SME-curated `(norm, period)` pairs.

**How to test.**
- 12 unit tests per the canonical patterns.
- 8 `applies_to` integration tests against SME fixtures.
- SME walkthrough: implementer presents ontology + 5 worked examples; SME signs off in writing that the implementation faithfully renders the skill's intent.

**Effort.** 0.5 senior engineer × 2 weeks (week 1–2) + SME × 0.2 week.

**Files.**
- *Read first:* `.claude/skills/vigencia-checker/references/tipologia-modificaciones.md` + `reglas-temporales.md` + `patrones-citacion.md` (the design); `src/lia_graph/graph/schema.py:166-190` (existing schema to extend); `supabase/migrations/20260417000000_baseline.sql:264-450,795` (existing columns to populate); `src/lia_graph/ingestion_classifier.py:279-298` (extend `AutogenerarResult` shape).
- *Create:* `src/lia_graph/vigencia.py` (the dataclass + enum + helper methods), `tests/test_vigencia_ontology.py` (12 patterns), `tests/test_vigencia_aplicabilidad.py` (8 fiscal-period cases), `docs/re-engineer/vigencia_ontology_implementation.md` (engineer notes; the skill is the design ref).
- *Modify:* none yet (modifications start in 1B-γ).

### 2.2 Sub-fix 1B-α — Scraper + cache infrastructure (NEW)

**What.** The skill mandates double-primary-source verification per article. At corpus scale (7,883 articles), live web fetch per call is too slow + rate-limited. Build cached scrapers for the 5 primary sources.

Per source: a Python module with rate-limiting, HTML-stable parsing, version-tolerant selectors (with golden HTML fixtures so we detect when the source restructures), and a SQLite cache keyed by `(source, norm_id, fetched_at)`.

The 5 scrapers:

| Module | Source | Coverage |
|---|---|---|
| `scrapers/secretaria_senado.py` | https://www.secretariasenado.gov.co/senado/basedoc/ | Leyes (incluye ET); modification notes per artículo |
| `scrapers/dian_normograma.py` | https://normograma.dian.gov.co/ | Decretos tributarios + resoluciones DIAN + conceptos DIAN |
| `scrapers/suin_juriscol.py` | https://www.suin-juriscol.gov.co/ | Toda la legislación nacional con histórico |
| `scrapers/corte_constitucional.py` | https://www.corteconstitucional.gov.co/relatoria/ | Sentencias C-, autos de suspensión |
| `scrapers/consejo_estado.py` | https://www.consejodeestado.gov.co/ | Sentencias de nulidad, autos de suspensión |

**Success criteria.**
- All 5 scrapers can fetch + parse + cache a request for ≥ 30 known-vigente norms with 100% success rate.
- Cache hit rate after Fix 1B-β finishes ≥ 70% (i.e., ≥ 70% of skill invocations during extraction read from cache, not from live fetch).
- Rate-limited politely: each source ≤ 2 requests/second (configurable per source).
- Detection of source restructure: each scraper has a "smoke fixture" HTML file checked into the repo; CI test fails if scraper can't parse the smoke fixture (cheap, runs fast).

**How to test.**
- Per scraper: `tests/scrapers/test_<source>.py` with the smoke fixture + 3 live-fetch integration tests (gated behind `LIA_LIVE_SCRAPER_TESTS=1` env to avoid hitting sources in CI).
- Aggregate: `scripts/scrapers/probe_all.py` runs the same 30-norm fetch against all 5; reports success rate + latency + cache size.

**Effort.** 1 senior engineer × 3 weeks (week 1–4 — overlaps Fix 1A weeks 1–2).

**Files.**
- *Read first:* `.claude/skills/vigencia-checker/references/fuentes-primarias.md` (the source hierarchy + URLs + selection rules); `scripts/sync_subtopic_taxonomy_to_supabase.py` (precedent for "external-source-fetch + cache + sync" Python module); any existing scraping or HTTP-cache code in the repo (`grep -r "requests" src/`).
- *Create:* `src/lia_graph/scrapers/__init__.py`, `src/lia_graph/scrapers/{secretaria_senado,dian_normograma,suin_juriscol,corte_constitucional,consejo_estado}.py`, `src/lia_graph/scrapers/cache.py` (SQLite-backed, shared by all 5), `tests/scrapers/test_*.py` (one per scraper + smoke fixtures under `tests/scrapers/fixtures/`), `scripts/scrapers/probe_all.py`, `Makefile` target `scrapers-probe`.
- *Modify:* `pyproject.toml` (add `requests`, `beautifulsoup4`, `lxml` if not already present), `.gitignore` (exclude `var/scraper_cache.db`).

**Hosting.** Cache lives at `var/scraper_cache.db` locally; in production deploy, mount a persistent volume. Size estimate: ~7,883 articles × 5 sources × ~50 KB avg = ~2 GB total. Fits comfortably.

### 2.3 Sub-fix 1B-β — Skill-guided extractor batch

**What.** Wraps `vigencia-checker` skill as a callable agent loop. Per article in the corpus: invoke skill (which reads scrapers via 1B-α), produce veredicto, write to `evals/vigencia_extraction_v1/<article_id>.json`. Resumable, parallelizable.

The agent loop per article:
1. Identify: extract `(norm_type, norm_id, article, parágrafo)` from the article record.
2. Invoke skill: pass identification + period (default: `today` for current vigencia).
3. Skill flow: ≥ 2 primary sources via 1B-α scrapers → judicial check → state classification → veredicto OR refusal.
4. Write output: structured `Vigencia` JSON if veredicto; `null` + reason if refusal.
5. Log to `evals/vigencia_extraction_v1/audit.jsonl`: per-article `(qid, state | null, sources_consulted, time_ms, cost_estimate)`.

**Cost target.** With 70% cache hit (per Fix 1B-α success criterion): ~$0.02-0.05 per article × 7,883 = $150-400 total LLM spend. Within Fix 1 budget envelope.

**Success criteria.**
- ≥ 95% of articles produce a `Vigencia` record OR a documented refusal (no silent crashes).
- ≥ 80% of articles have `extraction_confidence ≥ 0.7` (i.e., skill emitted a veredicto, not a refusal).
- 100% of `derogada_expresa` extractions cite the deroganting norm with full Citation (no naked DE).
- 100% of `inexequible` extractions cite the sentencia C- with effects timing.
- 100% of `exequibilidad_condicionada` extractions include the literal condicionamiento (verified by exact-match against the Corte source).
- A 100-article SME spot-check shows ≥ 95 correct extractions.
- The skill's audit log shows ≥ 2 primary sources consulted per non-refusal veredicto (no shortcuts).

**How to test.**
- After extraction completes: `scripts/audit_vigencia_extraction.py` reports the % at each confidence/state bucket.
- SME spot-check: 10 articles per state × 7 states + 10 random = 80 articles, SME marks correct/incorrect.
- Per-state minimum tests: 3 known-V, 3 known-VM, 3 known-DE, 3 known-DT, 3 known-SP, 3 known-IE, 3 known-EC (the 21 cases come from the Skill Eval set — see §10).
- Gate: if SME spot-check < 95%, the prompt or skill invocation is wrong; iterate before proceeding to Fix 1B-γ materialization.

**Effort.** 1 senior engineer × 2 weeks (week 4–6).

**Files.**
- *Read first:* `.claude/skills/vigencia-checker/SKILL.md` + all checklists; `src/lia_graph/ingestion_classifier.py` (precedent for LLM-call-with-structured-output discipline); `scripts/launch_phase9a.sh` + `scripts/monitoring/ingest_heartbeat.py` (the long-running-job launcher pattern); `artifacts/parsed_articles.jsonl` (the corpus to iterate over); `src/lia_graph/scrapers/` (your new infra from 1B-α).
- *Create:* `src/lia_graph/vigencia_extractor.py` (the agent loop module), `scripts/extract_vigencia.py` (one-off batch driver, launched detached per long-running-job convention), `evals/vigencia_extraction_v1/` (output dir), `scripts/audit_vigencia_extraction.py` (the bucket reporter), `Makefile` target `phase2-extract-vigencia`.
- *Modify:* none in this sub-fix; Fix 1B-γ does the writes.

### 2.4 Sub-fix 1B-γ — Materialize vigencia in Supabase + Falkor (was Fix 1C in v1)

**What.** Read the extraction outputs from Sub-fix 1B-β; populate Supabase `documents.vigencia*` columns + add new structured columns; populate Falkor `:ArticleNode.vigencia` properties; materialize structured edges (`DEROGATED_BY {fecha, ruling_id}`, `MODIFIED_BY {...}`, `SUSPENDED_BY {...}`, `INEXEQUIBLE_BY {...}`, `CONDITIONALLY_EXEQUIBLE_BY {...}`).

**Success criteria.**
- `SELECT COUNT(*) FROM documents WHERE vigencia_basis IS NULL AND vigencia IN ('derogada','suspendida','proyecto')` returns 0.
- `MATCH (a:ArticleNode {status: 'derogado'}) WHERE NOT EXISTS((a)-[:DEROGATED_BY]->()) RETURN count(a)` returns 0.
- The Vigencia value object round-trips: write to Supabase + Falkor, read back, verify identity on 50 random articles.
- All 7 states are represented in the populated data (not just V/DE/SP from before).

**How to test.**
- Migration scripts have unit tests against local Supabase + local Falkor docker.
- Post-deployment audit query (`scripts/audit_vigencia_integrity.py`) returns the four-zero counts.

**Effort.** 1 senior engineer × 1 week (week 6–7).

**Files.**
- *Read first:* `src/lia_graph/ingestion/supabase_sink.py:639,646` (where binary vigencia is written today — extend); `src/lia_graph/ingestion/loader.py` (Falkor loader); `src/lia_graph/graph/client.py` (`stage_detach_delete` + `stage_delete_outbound_edges` patterns from v5 §6.5); `scripts/sync_article_secondary_topics_to_falkor.py` (precedent for "back-fill a property to existing Falkor nodes without re-ingest").
- *Create:* `supabase/migrations/20260YYYY000000_vigencia_structural.sql` (adds `vigente_desde`, `vigente_hasta`, `modificado_por jsonb`, `suspension_actual jsonb`, `inexequibilidad jsonb`, `condicionamiento text`, `regimen_transicion jsonb` columns + populates from extraction output), `scripts/sync_vigencia_to_falkor.py` (mirrors `sync_article_secondary_topics_to_falkor.py`), `scripts/audit_vigencia_integrity.py`.
- *Modify:* `src/lia_graph/ingestion/supabase_sink.py` (write all vigencia fields), `src/lia_graph/ingestion/loader.py` (emit structured edges with full properties).
- **Convention reminder:** explicit `DROP FUNCTION IF EXISTS` before any SQL function change; per `hybrid_search-overload-2026-04-27.md`.

### 2.5 Sub-fix 1C — Plumb 2D vigencia model into retrieval (was Fix 1D in v1)

**What.** The retriever now reasons in 2D: `(retrieved_chunk.vigencia, planner.vigencia_at_date) → demotion_factor`.

Two changes:
1. **Active demotion.** Default mode (`vigencia_at_date = today`):
   - V → factor 1.0
   - VM → 1.0 (the vigente text is current)
   - EC → 1.0 (cited with condicionamiento)
   - DT → 0.3 (uncertain; allow with low weight)
   - DE → 0.0 (filter out)
   - SP → 0.0 (filter out for default; UI surfaces SP via a different path — Fix 4 partial-mode escalation)
   - IE → 0.0 (filter out unless effects diferidos active)
2. **Period-aware retrieval.** When the planner extracts a year context (`para 2018`, `antes de 2017`), `vigencia_at_date` is set to that year-end. The retriever computes `vigencia.applies_to(vigencia_at_date)` per chunk and demotes accordingly. Articles now-DE that were V in 2018 are CITABLE for AG 2018 questions (ultractividad).

The Falkor traversal symmetrically: `MATCH ... WHERE state_at_date(a.vigencia, $date).aplica IN ('Sí', 'Parcial')`. `[:DEROGATED_BY]` edges aren't traversed unless planner historical-context flag is set.

**Success criteria.**
- For 30 canonical "vigente law" questions: **0 derogated articles** in top-5 primaries.
- For 10 canonical "historical law" questions ("¿Qué decía art. 147 ET antes de Ley 1819?"): the derogated article is correctly retrieved AND labeled as historical.
- Re-run §1.G SME 36-question fixture: zero `art. 689-1` citations (currently 2 after Activity 1; binary fix won't catch the rest), zero "6 años firmeza" claims, zero pre-Ley-2277 dividend tariffs.
- The §1.G `served_acceptable+` count moves from 21/36 (post-Activity-1 baseline) to ≥ 24/36.

**How to test.**
- 40-question regression set in `evals/vigencia_v1/` (extends v1's planned set with the 7-state coverage).
- Re-run the §1.G SME fixture; SME re-classifies any answer that changed class.
- A/B harness: same 30-question set against pre-Fix-1C and post-Fix-1C; compare derogated-article appearance rate.

**Effort.** 1.5 senior engineers × 2 weeks (week 7–9).

**Files.**
- *Read first:* `src/lia_graph/pipeline_d/retriever_supabase.py:47-189` (full hybrid-search call site); `src/lia_graph/pipeline_d/retriever_falkor.py` (full); `supabase/migrations/20260427000000_topic_boost.sql` (precedent for adding RPC parameter); `supabase/migrations/20260428000000_drop_legacy_hybrid_search.sql` + `20260429000000_vigencia_filter_unconditional.sql` (Activity 1's surgical precursors); `src/lia_graph/pipeline_d/contracts.py` (planner contract — `vigencia_at_date` is a new signal); `src/lia_graph/pipeline_d/answer_comparative_regime.py` (precedent for cue-detection in planner — same pattern for `vigencia_at_date` cue).
- *Create:* `supabase/migrations/20260YYYY000000_hybrid_search_2d_vigencia.sql` (drops the v5 §1.D 15-arg + Activity 1 16-arg; recreates with `vigencia_filter_mode` + `vigencia_at_date` parameters), `evals/vigencia_v1/` (40-question regression set), `tests/test_retriever_vigencia_2d.py`.
- *Modify:* `src/lia_graph/pipeline_d/retriever_supabase.py` (compute demotion factor from Vigencia at date), `src/lia_graph/pipeline_d/retriever_falkor.py` (analogous Cypher predicates), `src/lia_graph/pipeline_d/planner.py` (`vigencia_at_date` cue extraction), `src/lia_graph/pipeline_d/contracts.py` (new field on `GraphRetrievalPlan`).
- **Env matrix bump required:** new RPC parameters change retrieval shape → version bump + change-log row + `LIA_VIGENCIA_FILTER_MODE` env (default `enforce` per `project_beta_riskforward_flag_stance` memory).

### 2.6 Sub-fix 1D — User-facing 7-variant vigencia chips (was Fix 1E in v1)

**What.** Every cited article in an answer carries a chip that maps to its vigencia state:

| State | Chip | Tone |
|---|---|---|
| V | (no chip — default) | — |
| VM | "modificada por X" | blue |
| DE | "derogada por X desde fecha" | red |
| DT | "derogada tácitamente — verificar" | orange |
| SP | "suspendida por auto X — ver T-Y" + mandatory T-series link | yellow |
| IE | "inexequible — sentencia C-X" | red |
| EC | "exequibilidad condicionada — ver condicionamiento" + expandable text | purple |

Composer policy enforces: any answer that cites a DE/DT/SP/IE article MUST include the chip; any answer about historical regimes MUST display the comparative-regime table; EC chips MUST display the literal condicionamiento on hover/expand (no paraphrase).

**Success criteria.**
- 100% of cited DE/DT/SP/IE/EC articles in test answers carry a chip.
- The chip styling mirrors the existing `subtopicChip.ts` atomic pattern.
- Component test passes: render all 7 variants; SP variant has working T-series link; EC variant shows literal Court text on expand.

**How to test.**
- Component tests in `frontend/tests/vigenciaChip.test.ts` for all 7 variants.
- E2E test: the 10 historical questions from §2.5 produce answers with vigencia chips visible in the rendered HTML.
- Visual regression: screenshot snapshots for each chip variant.

**Effort.** 0.5 frontend engineer × 2 weeks (week 9–10).

**Files.**
- *Read first:* `frontend/src/shared/ui/atoms/subtopicChip.ts` (mirror exactly); `frontend/src/shared/ui/molecules/intakeFileRow.ts` (precedent for chip composition into a row); the atomic-design memory (`feedback_atomic_design_first.md`).
- *Create:* `frontend/src/shared/ui/atoms/vigenciaChip.ts` (7 variants), `frontend/tests/vigenciaChip.test.ts`.
- *Modify:* whichever existing molecule renders citation labels in `frontend/src/features/chat/` — extend it to consume the new chip atom.
- *Backend contract:* the chat response payload's `citations[].vigencia` field must already be populated by Sub-fix 1C's retriever changes; verify before touching frontend.

### 2.7 Fix 1 — kill-switch metric (week 6 midpoint)

After Sub-fix 1B-β ships (end of week 6), re-run the §1.G SME questions on `beneficio_auditoria`, `firmeza_declaraciones`, `dividendos_y_distribucion_utilidades`. Required result:

- **Zero** citations of `art. 689-1` (currently 2 after Activity 1).
- **Zero** "6 años" claims for firmeza con pérdidas.
- **Zero** dividend tariff claims at 10%.
- **Skill audit log shows ≥ 2 primary sources consulted** for every veredicto fed into retrieval.

If any of those persist after week 6 (or if skill audit shows shortcuts), **the project is in trouble**. Per `makeorbreak_v1.md`, this triggers the brand/risk perspective: pause and reassess.

---

## §3 — Fix 2 — Parámetros móviles map (UVT/SMMLV/IPC + topical thresholds)

Largely unchanged from v1 — Colombia-specific annual amounts (UVT, SMMLV, IPC, plus topical thresholds the SME identified) live in per-year YAML; resolver injects current-year values; composer-side rewrite pass replaces stale values with canonical current ones.

**v2 enrichment:** parameter resolution composes with the Vigencia 2D model. When LIA answers a question about AG 2018, the resolver returns 2018 UVT (not 2026 UVT). When LIA answers about AG 2026, returns 2026 UVT. The `applies_to(periodo)` method on Vigencia tells the composer which year-context to use.

**Success criteria.** Same as v1 §3.3: 8 SME questions whose right answer requires a 2026 parameter all produce 2026 values; 0% false rewrites in 50-answer regression.

**Effort.** 1 senior engineer × 4 weeks (week 2–6, parallel with Fix 1).

**Files.**
- *Read first:* `src/lia_graph/ui_text_utilities.py:_UVT_REF_RE`; `src/lia_graph/pipeline_d/answer_synthesis.py` (stable facade — do NOT edit; identify implementation module); `src/lia_graph/pipeline_d/answer_synthesis_helpers.py`; `src/lia_graph/pipeline_d/answer_llm_polish.py`; `config/subtopic_taxonomy.json` (precedent JSON-config loader).
- *Create:* `config/parametros_moviles/{2020,2021,2022,2023,2024,2025,2026}.yaml`, `src/lia_graph/parametros.py` (resolver), `src/lia_graph/parametros_schema.py` (Pydantic model), `tests/test_parametros_resolver.py`, `tests/test_parametros_year_detection.py`, `evals/parametros_v1/8_uvt_questions.jsonl`, `scripts/audit_parametros_yaml.py`.
- *Modify:* `src/lia_graph/pipeline_d/answer_synthesis_helpers.py` (insert rewrite pass after retrieval, before polish), `src/lia_graph/pipeline_d/answer_llm_polish.py` (extend polish prompt with parameter-protection rule).

---

## §4 — Fix 3 — Anti-hallucination guard on partial mode

Unchanged from v1. `Cobertura pendiente` strings must propagate as a typed `PartialCoverage` value object; composer can never wrap them in fabricated "Ruta sugerida" / "Riesgos" templates; LLM polish prompt forbidden from synthesizing content for partial sub-questions; post-polish regex strip fires if fabricated article references slip through.

**v2 enrichment:** integrates with skill — when retriever fires `PartialCoverage`, the composer can optionally invoke the `vigencia-checker` skill on the user's specific question. If the skill produces a clean veredicto for the relevant norm, the answer can fill the partial sub-question with the skill's output (and the corresponding citation chips). If the skill also refuses, the user gets an honest "no encontré evidencia primaria" with explicit recommendation.

**Effort.** 1 senior engineer × 4 weeks (week 7–10).

**Files.** As v1 §4 + skill invocation hook in `pipeline_d/answer_synthesis_helpers.py`.

---

## §5 — Fix 4 — Ghost-topic kill + corpus completeness audit

Unchanged from v1 in goal: every registered topic has ≥ 5 docs OR is de-registered. `tarifas_renta_y_ttd` populate, `regimen_cambiario` promote from `to_upload/`, preflight gate.

**v2 enrichment:** every populated doc runs through `vigencia-checker` skill at ingest time. The doc's frontmatter includes its skill-emitted vigencia veredicto. So instead of "add 5 docs and hope," it's "add 5 docs that have been verified against ≥ 2 primary sources, with full vigencia veredicto attached." Higher quality bar; same wall-time effort because the skill does the verification.

**Effort.** 0.5 SME FTE × 5 weeks (week 8–13) + 0.5 engineer for index, retrieval validation, skill-at-ingest hook.

**Files.** As v1 §5 + a new ingest-time hook that calls the skill on each new doc.

---

## §6 — Fix 5 — Golden-answer regression suite (TRANCHE schema, skill as judge)

**Major v2 change: judge schema replaced with skill's audit-LIA TRANCHE format.**

**Pre-existing seed (DONE 2026-04-26 evening):** Activities 1.5 + 1.6 already produced **4 pre-validated test cases** covering vigencia states V (Art. 290 #5 ET), VM (Art. 689-3 ET), DE (Art. 158-1 ET), IE (Decreto 1474/2025). Each fixture's `fix_5_skill_eval_seed` block includes `expected_state`, `expected_must_cite`, `expected_must_not_say`. Activity 1.7 (queued week 1) adds 3 more covering DT/SP/EC. **Skill eval set is therefore 7 of 30 cases pre-seeded before Fix 5 formally begins.**

Plus 2 pre-validated TRANCHE test cases from Activity 1.5's `tranches_de_correccion_pendientes` block — these become the first golden-answer regressions for the corpus's Decreto 1474/2025 content.

Each golden question carries the canonical answer + must-cite + must-not-say. The judge:
1. Posts the question to LIA.
2. Captures LIA's answer.
3. Invokes `vigencia-checker` skill on each citation in LIA's answer.
4. Emits a TRANCHE per skill's `patrones-citacion.md`:

```yaml
output_evaluado: <LIA's verbatim answer>
clasificacion_hallazgo: INCORRECTO | INCOMPLETO | OMISION_COMPLETA | OK
descripcion_error: <if not OK, what's wrong>
norma_real_aplicable: <skill's vigencia veredicto for the relevant norm>
gravedad: CRITICO | MAYOR | MENOR | NONE
correccion_propuesta: <what LIA should have said>
evidencia_fuente_primaria: [<primary source URLs>]
articulo_norma_afectada: <e.g., Art. 689-3 ET>
```

CI gate mapping:
- CRITICO → blocks merge (was HARD_FAIL in v1)
- MAYOR → warns + flags for human review (was SOFT_FAIL)
- MENOR → logs only (was NO_FAIL)
- OK → passes

**Success criteria.** ≥ 100 golden questions by week 14; ≥ 90% OK; zero CRITICO. Suite runs in < 15 min (parallel via the engine's `ChatClient`).

**Effort.** SME × 0.5 FTE for authoring (week 1–14) + 0.5 engineer for judge + CI wiring (week 1–4).

**Files.**
- *Read first:* `scripts/eval/engine.py` (reuse — do NOT write a 3rd copy); `scripts/eval/run_sme_validation.py` (parser/runner/classifier); `scripts/eval/sme_validation_report.py` (aggregator/verbatim shape); `scripts/judge_100qs.py` (precedent LLM-judge pattern); `evals/100qs_accountant.jsonl` (precedent JSONL fixture); `Makefile` (`eval-c-gold`/`eval-c-full` patterns); `.claude/skills/vigencia-checker/references/patrones-citacion.md` (TRANCHE format definitive ref).
- *Create:* `evals/golden_answers_v1/questions/<qid>.yaml` (one per golden question), `scripts/eval/run_golden.py` (chat runner — thin wrapper over `engine.ChatClient`), `scripts/eval/judge_golden.py` (TRANCHE-emitting judge that invokes vigencia-checker), `scripts/eval/golden_report.py` (CRITICO/MAYOR/MENOR/OK dashboard), `.github/workflows/golden_ci.yml` (merge-blocking on CRITICO), `Makefile` target `eval-golden`.
- *Modify:* root `CLAUDE.md` Commands section.

---

## §7 — Fix 6 — Internal corpus consistency editorial pass + corpus-wide hallucination audit

Unchanged from v1 in core goal (reconcile internal contradictions; mark superseded sections). **Two v2 enrichments:**

**v2 enrichment 1 — skill as diagnostic tool.** SME runs the skill on each topic's anchor norms; the skill produces the canonical veredicto; the SME marks displaced sections with `superseded_by: <doc_id>` frontmatter (skill's output is the audit trail).

**v2 enrichment 2 (NEW post-Activity-1.5) — corpus-wide hallucination audit.** Activity 1.5 found `EME-A01-addendum-estado-actual-decretos-1474-240-2026.md` cites a non-existent `Sentencia C-077/2025` despite a "verificación: 20 marzo 2026" header. Other corpus files likely have similar issues. Per `docs/learnings/ingestion/corpus-hallucinated-content-EME-A01.md`, run this audit:

```bash
# Files claiming verification:
grep -rl "verificación\|verificado\|fuentes verificadas\|URLs verificadas" knowledge_base/

# Files with internal citation of specific sentencias / autos:
grep -rE "Sentencia C-[0-9]{3}/(20[0-9]{2})|Auto [0-9]+/(20[0-9]{2})" knowledge_base/

# Files with addendum / estado actual / post-suspension naming:
find knowledge_base -name "*addendum*" -o -name "*estado-actual*" -o -name "*post-suspension*"
```

For each match, run the `vigencia-checker` skill on the cited sentencia/auto. If the cited ruling does not exist OR its date doesn't match: flag as hallucinated content; corpus document needs editorial rewrite or deprecation.

**Success criteria.**
- Re-run a 30-question subset of golden answers: zero contradictions detected.
- Each touched document has a clear "canonical | superseded | historical" classification.
- Corpus-wide hallucination audit completes; each "verificación" claim is either re-verified by the skill or the document is flagged for editorial rewrite.
- At minimum: EME-A01 is rewritten with verified facts (replace fabricated C-077/2025 with real C-079/2026); T-I is updated to reflect SP→IE transition (Apr 15 2026); deprecated T-I marked as `superseded_by` the new T-I.

**How to test.**
- The judge from §6.2 detects internal contradictions when LIA's answer cites two values that disagree.
- SME spot-check on the 20 reviewed topics.
- Hallucination audit script (`scripts/audit_corpus_hallucinations.py`) reports: total `verificación` claims found, % verified, % flagged.

**Effort.** SME × 0.5 FTE × 5 weeks (week 11–13) + 0.5 engineer for the `superseded_by` retrieval support + the corpus-wide hallucination audit script (~2 days incremental).

**Files.**
- *Read first:* the docs flagged in `evals/activity_1_5/decreto_1474_2025_veredicto.json` `fix_6_findings` block (EME-A01 + T-I); `docs/learnings/ingestion/corpus-hallucinated-content-EME-A01.md` for the audit pattern; `docs/learnings/process/skill-as-verification-engine.md` for the discipline.
- *Create:* `docs/re-engineer/corpus_consistency_audit.md` (SME's per-topic findings + reconciliation decisions); `scripts/audit_corpus_hallucinations.py` (greps + skill invocations); per-document frontmatter additions (`superseded_by: <doc_id>`); `evals/corpus_consistency_v1/30q_subset.jsonl`.
- *Modify:* knowledge_base files flagged for supersession; `src/lia_graph/pipeline_d/retriever_supabase.py` + `retriever_falkor.py` (extend Fix 1C demotion to also demote on `superseded_by`); `src/lia_graph/ingestion/parser.py` (read the new `superseded_by` frontmatter field).

---

## §8 — Activity series (surgical pre-cursors)

Activities are small, isolated, measurable ships that prove a structural fix's hypothesis before the full fix lands. They are not throwaway — they integrate cleanly into the corresponding Fix.

### Activity 1 ✅ — SQL-only vigencia filter (DONE 2026-04-29)

**Shipped.** Migration `20260429000000_vigencia_filter_unconditional.sql` removes the silent bypass that disabled the existing `vigencia NOT IN ('derogada', ...)` filter when `filter_effective_date_max` was passed.

**Measured outcome (clean before/after on §1.G fixture):**
- `art. 689-1` mentions: 13 → 2 (−85% — the binary flag DOES catch this case).
- `Ley 1429` mentions: 303 → 286 (essentially unchanged — flag too sparse).
- `6 años firmeza`: 13 → 19 (regression — chunk reshuffle let stale "6-año" patterns through).
- §1.G `served_acceptable+`: 21/36 unchanged.

**Learning embedded in v2:** the binary flag's coverage is too sparse to be useful at scale. **Real impact comes when Fix 1B-β populates structured Vigencia for every article**, at which point the same retrieval filter (now enriched in Sub-fix 1C) fires correctly across 100% of the corpus.

**Status:** ✅ Shipped to staging cloud. Does NOT need rolling back; remains correct. Will be superseded by Sub-fix 1C's richer retrieval logic.

### Activity 1.5 ✅ — Skill-guided verification of Decreto 1474/2025 (DONE 2026-04-26 evening)

**What we did.** Walked the `vigencia-checker` skill protocol manually on Decreto 1474/2025 (cleanest SP candidate from SME inventory) using WebSearch as primary-source proxy (Fix 1B-α scrapers don't exist yet). Produced structured veredicto.

**Outcomes** (full report at `docs/re-engineer/activity_1_5_outcome.md`):

1. ✅ **Veredicto produced**: state IE (inexequible per Sentencia C-079/2026 of April 15, 2026), NOT the SP I/the SME inventory expected. Saved at `evals/activity_1_5/decreto_1474_2025_veredicto.json`.
2. ✅ **Corpus internal contradiction surfaced**: `EME-A01-addendum-estado-actual-decretos-1474-240-2026.md` (NORMATIVA layer) contradicts `T-I-decreto-1474-2025-estado-post-suspension-corte-constitucional.md` (EXPERTOS layer) on dates AND ruling. Two corpus docs — different "facts" about the same Decreto.
3. ✅ **Hallucinated corpus content discovered**: EME-A01 cites a non-existent "Sentencia C-077/2025"; the real ruling is C-079/2026. Verification stamp ("verificación: 20 marzo 2026") is meaningless. **This is the single highest-value finding of the round.**
4. ✅ **No Supabase UPDATE applied** (correct decision per skill discrimination): the corpus contains interpretation docs about the Decreto, not the Decreto's text itself. Wholesale-flagging interpretations as `derogada` would have hidden them from retrieval. Right action is editorial (Fix 6), not metadata-flag.

**Lesson** captured in `docs/learnings/ingestion/corpus-hallucinated-content-EME-A01.md` + `docs/learnings/process/skill-as-verification-engine.md`.

**Downstream impacts (already reflected elsewhere in this plan):**
- Fix 6 (§7) gains corpus-wide hallucination audit subscope.
- Re-Verify Cron moved week 13 → week 5 per `re-verify-cron-criticality.md`.
- 2 pre-validated TRANCHE test cases for Fix 5 (in the veredicto JSON's `tranches_de_correccion_pendientes` block).

### Activity 1.6 ✅ — Skill on 3 canonical norms covering V / VM / DE states (DONE 2026-04-26 evening)

**What we did.** Manual skill protocol on three high-coverage norms to validate the skill produces correct veredictos on canonical vigencia state cases.

**Outcomes** (3 fixtures in `evals/activity_1_5/`):

| Fixture | Norm | State produced | Validates |
|---|---|---|---|
| `art_689_3_ET_AG2025_veredicto.json` | Art. 689-3 ET (beneficio de auditoría) | **VM** (Ley 2155/2021 → Ley 2294/2023 prórroga) | Clean modification chain; cite ONLY current text, not Ley 2010/2019's pre-2021 Art. 689-1 |
| `art_158_1_ET_AG2025_veredicto.json` | Art. 158-1 ET (CTeI deduction) | **DE** (Art. 96 Ley 2277/2022, efectos 2023-01-01) | Clean derogación expresa; ultractividad note for AG 2022 economic events |
| `art_290_num5_ET_AG2025_veredicto.json` | Art. 290 #5 ET (régimen transición pérdidas pre-2017) | **V** with `regimen_transicion` populated | Vigente sin modificaciones; transition regime distinct from a modification |

Combined with Activity 1.5's Decreto 1474/2025 → IE: **4 of 7 vigencia states (V / VM / DE / IE) now have validated real-norm test cases.** Each fixture includes a `fix_5_skill_eval_seed` block.

**Lesson** captured in `docs/learnings/process/activity-as-surgical-precursor.md` and `docs/learnings/retrieval/vigencia-2d-model.md` (worked-examples table).

**Downstream impacts:**
- Fix 5 skill eval set design (§0.8.4) — 4 of 30 cases already authored.
- Fix 1B-β cost-throughput data validated: ~1 minute of WebSearch-as-primary-source proxy per norm.

### Activity 1.5b — Manual veredicto persistence to staging DBs (queued, week 1, ~3 hours)

**Why this exists.** As of Round 3 (2026-04-26 evening), the 4 veredictos produced by Activities 1.5 + 1.6 live ONLY as JSON fixtures in `evals/activity_1_5/`. Staging cloud Supabase has the columns (`documents.vigencia` + `vigencia_basis` + `vigencia_ruling_id`) but they're NULL for the 4 documents we've now verified. Staging cloud Falkor has the edge types defined (`DEROGATED_BY`, `MODIFIED_BY`, `SUSPENDED_BY`, `INEXEQUIBLE_BY`) but no instances for these cases.

This Activity bridges the gap: persist the 4 veredictos to staging now (small, validated set) instead of waiting for Fix 1B-γ at week 6–7 (large, full corpus). Validates the persistence path end-to-end + makes the discoveries "real" in the running staging system + de-risks Fix 1B-γ.

**What.** A small one-shot script that:
1. Reads the 4 veredicto fixtures from `evals/activity_1_5/{decreto_1474_2025, art_689_3_ET_AG2025, art_158_1_ET_AG2025, art_290_num5_ET_AG2025}_veredicto.json`.
2. For each → locates corresponding `documents` rows in staging Supabase (by `relative_path` glob OR canonical norm-id match).
3. Populates `documents.vigencia` (mapping skill state → existing enum: V/VM → `vigente`; DE/IE → `derogada`; SP → `suspendida`; DT → `parcial`; EC → `vigente` with `vigencia_basis` flagged), `documents.vigencia_basis` (free-text from the skill veredicto), `documents.vigencia_ruling_id` (the canonical norm-id of the deroganting/modificando/suspending/inexequibilidad citation).
4. Mirrors to staging cloud Falkor: `MERGE (d:Document {doc_id: $doc_id}) SET d.vigencia = $state` + emits the 1-2 structured edges per case via `MERGE (d)-[:DEROGATED_BY {ruling_id, fecha, scope}]->(:Citation {norm_id})` shapes.
5. Writes an audit log to `evals/activity_1_5/persistence_audit.jsonl` recording every write (rollback-ready).

**Success criteria.**
- 4 veredictos persisted to staging Supabase: `SELECT vigencia, vigencia_basis, vigencia_ruling_id FROM documents WHERE relative_path LIKE ANY(...)` returns populated values for all 4.
- Corresponding edges in staging Falkor: `MATCH (d:Document)-[r:DEROGATED_BY|MODIFIED_BY|SUSPENDED_BY|INEXEQUIBLE_BY]->(c) WHERE d.doc_id IN [...]` returns ≥ 4 edges with full properties.
- Audit log shows every write with timestamp + before/after snapshot.
- No regressions: re-run §1.G — auto-rubric must stay ≥ 21/36 served_acceptable+.

**How to test.**
- Pre-write: `psql` query confirms the 4 docs have NULL vigencia_basis + vigencia_ruling_id.
- Post-write: same query confirms populated values.
- Cypher query against Falkor confirms edge presence.
- §1.G re-run via `scripts/eval/run_sme_validation.py` (delete cached responses first).

**What this does NOT do (binding scope).**
- Does NOT touch local Supabase docker — next `supabase db reset` will pick up the Activity 1 SQL filter migration, but the manual UPDATEs would need to be re-run locally via this same script. Document the gap in the Activity outcome doc.
- Does NOT touch production (Railway). Production sync is gated on full Fix 1 ship + week 14 launch readiness review.
- Does NOT apply per-article granularity. These are document-level updates. Per-article granularity is Fix 1B-γ scope.
- Does NOT correct the corpus content (EME-A01 hallucination, T-I staleness). That's Fix 6 editorial.

**Effort.** 0.5 engineer × 0.5 day (3 hours).

**Cost.** $1K from reserve (was $4K after Activities 1.7 + 1.8; now $3K after 1.5b).

**Files.**
- *Read first:* the 4 veredicto fixtures in `evals/activity_1_5/`; `src/lia_graph/ingestion/supabase_sink.py:639,646` (current vigencia write site — mirror the column-write pattern); `scripts/sync_article_secondary_topics_to_falkor.py` (precedent for "back-fill a property to existing Falkor nodes via Cypher MERGE without re-ingest").
- *Create:* `scripts/persist_veredictos_to_staging.py` (the one-shot persistence script); `evals/activity_1_5/persistence_audit.jsonl` (the rollback-ready log).
- *Modify:* staging cloud Supabase `documents` table (4 rows); staging cloud Falkor (4 nodes' `vigencia` property + 4–8 new edges).

**Pre-validates:** Fix 1B-γ at smaller scale. The mapping decisions (state enum mapping, ruling_id format, edge property shape) made here become the contract Fix 1B-γ implements at full scale.

### Activity 1.7 — Skill on 3 norms covering DT / SP / EC states (queued, week 1)

**What.** Complete the 7-state coverage of the skill eval set's seed by running the skill manually on 3 more norms covering the missing states:

- **DT (derogada tácita)**: a norm where a posterior law regulates the same matter incompatibly without express derogation. SME-suggested candidates: certain procedural articles displaced by Decretos Reglamentarios. SME picks the canonical case in week-1 ontology session.
- **SP (suspendida provisional, current)**: a norm currently under medida cautelar from Consejo de Estado without sentencia de fondo. SME picks per current judicial calendar.
- **EC (exequibilidad condicionada)**: a norm declared exequible CON condicionamiento literal. Strong candidate: any article with a recent C- sentencia "en el entendido que..." — SME picks.

**Success criteria.**
- 3 veredicto fixtures saved at `evals/activity_1_5/<case_id>_veredicto.json` matching `fixplan_v2.md §0.8.3(2)` shape.
- Each fixture includes a `fix_5_skill_eval_seed` block with expected_state, expected_must_cite, expected_must_not_say.
- Total: skill eval set seeded with 7 of 30 cases (one per state), pre-validated.

**Effort.** 0.5 engineer × 1 day (week 1) + ~15 min SME consultation per case for canonical-pick.

**Files.** Same shape as Activity 1.6: 3 new JSON fixtures in `evals/activity_1_5/`. No code changes.

**Pre-validates:** Fix 5 (golden judge) — completes the state-coverage matrix; Fix 1B-β extractor's expected output distribution.

### Activity 1.8 — Per-article skill on Ley 1429 (queued, week 5)

**What.** Once Fix 1B-α scrapers are operational (week 4), run the skill against ~30 Ley 1429/2010 articles to produce per-article veredictos. Apply UPDATE based on the per-article `state` (most expected DE; some V if survivors). Re-run §1.G; measure `Ley 1429` citation drop.

**Why this is queued, not now.** The original Activity 1.5 plan included Ley 1429, but at 30+ articles the manual WebSearch-walkthrough is impractical (~10 hours of operator time vs the 30 min Activity 1.5 took on a single Decreto). Wait for scrapers; then it's a 1-hour automated batch.

**Success criteria.**
- Per-article veredictos for ≥ 30 Ley 1429 articles in `evals/activity_1_8/ley_1429_veredictos.jsonl`.
- UPDATE applied: ≥ 80% of articles flagged DE; vigente articles preserved.
- §1.G `Ley 1429` mentions drop from 303 → < 50.

**Effort.** 0.5 engineer × 1 day (week 5).

**Files.** New fixture set; one-shot UPDATE script.

**Pre-validates:** Fix 1B-β at smaller scale (Ley 1429 is a microcosm of the full corpus extraction).

### Future activities (queued, post-launch)

- **Activity 2 — Surgical: drop `Ley-1429-2010.md` chunks from vector index** if Fix 1B-β's results show those chunks are still bleeding into retrieval despite the flag.
- **Activity 3 — Surgical: planner-side `vigencia_at_date` cue extraction.** If Fix 1C is delayed, ship the planner's date-extraction logic standalone — it's useful diagnostic even before retrieval consumes it.
- **Activity 4 — Skill on labor norms (CST, Ley 50/1990, Ley 789/2002).** Same pattern as the tax-law skill; new source hierarchy (MinTrabajo + Cortes laborales). Out of v1 launch scope per `fixplan_v2.md §12`.
- **Activity 5 — Skill on cambiario (Resolución Externa 1/2018 JDBR + DCIN-83).** Banco de la República as primary source. Out of v1 launch scope.

---

## §9 — Cross-fix dependencies (updated)

```
Week:    1  2  3  4  5  6  7  8  9 10 11 12 13 14
A1.5:    ✅  (DONE 2026-04-26 ev — Decreto 1474/2025 → IE veredicto + corpus hallucination found)
A1.6:    ✅  (DONE 2026-04-26 ev — 3 norms VM/DE/V seeded skill eval set)
A1.7:    ██  (skill on DT/SP/EC norms; 3 days; completes 7-state coverage)
A1.8:                ██  (skill on Ley 1429 articles; needs scrapers; week 5)
F1A:     ████  (skill is the design — implement Vigencia dataclass + applies_to)
F1B-α:   ████████████  (scrapers; CRITICAL PATH; everything else waits)
F1B-β:               ██████████  (skill-guided extraction at corpus scale)
F1B-γ:                        ██████  (materialize Supabase + Falkor)
F1C:                                ██████████  (2D vigencia retrieval)
F1D:                                          ██████  (UI chips, 7 variants)
F2:        ████████████   (parámetros móviles, parallel)
F3:                              ████████████  (anti-hallucination)
F4:                              █████████████████  (ghost topic + populate)
F5:      █████████████████████████████  (TRANCHE judge — 4 cases pre-seeded; 26 to author)
F6:                                    ████████████  (corpus consistency + hallucination audit)
SkillEval:               ██████████  (30 SME cases against skill — 4 pre-seeded)
ReVerifyCron:        ████  (MOVED from week 13; deploys week 4-5 once scrapers exist)
                       ↑                                         ↑
                       wk-4 KILL                            wk-14 LAUNCH
                       SWITCH                                 GATE
```

**Hard ordering constraints:**
- Fix 1B-α (scrapers) is the new critical path — without scrapers, Fix 1B-β cannot run at acceptable cost.
- Fix 1B-β cannot start until Fix 1A ontology lands AND Fix 1B-α scrapers exist.
- Fix 1C cannot ship its 2D retrieval until Fix 1B-γ has materialized vigencia for all articles.
- Fix 2 needs Fix 1's `applies_to(periodo)` for year-aware parameter resolution → Fix 2 finalizes after Fix 1A but ships parameters incrementally.
- Fix 3 finalizes after Fix 1C (so partial-mode escalation can use the skill on uncovered queries).
- Fix 6 needs Fix 4's SME bandwidth (weeks 11-13 overlap is tight — SME must split focus).

---

## §10 — Decision checkpoints (updated)

| Week | Gate | Pass criterion | Fail action |
|---|---|---|---|
| **0** ✅ | Activities 1.5 + 1.6 (DONE) | 4 of 7 vigencia states validated; corpus hallucination found; skill eval set seeded 4/30 | Reflected in plan; no further action |
| **1** | Activity 1.7 — DT/SP/EC state coverage | 3 more veredicto fixtures saved; skill eval set at 7/30 | Iterate; not project-threatening |
| **2** | Fix 1A ontology Python implementation | 12 unit tests pass; SME signs off on dataclass fidelity to skill design | Fast iterate; not project-threatening |
| **4** | Fix 1B-α scraper integration | All 5 scrapers fetch ≥ 30 known norms; cache hit rate measured | If any scraper structurally broken: pause; redesign cache key or selector strategy |
| **5** | Re-Verify Cron deployment (MOVED earlier) | Cron operational; first re-verification pass over the 4 already-extracted veredictos detects the T-I staleness (SP→IE) and re-emits IE | Engineering iteration on cron triggers |
| **5** | Activity 1.8 — Ley 1429 per-article | ≥ 30 articles classified; UPDATE applied; §1.G `Ley 1429` mentions < 50 | Pre-Fix-1B-β validation of the extraction pattern at small scale |
| **6** | **Fix 1B-β kill switch** (the critical one) | Zero `art. 689-1`/`6 años`/`10% dividendo` citations in §1.G re-run; skill audit shows ≥ 2 primary sources per veredicto | **Project in trouble.** Pause to reassess per `makeorbreak_v1.md`. |
| **6** | Skill-eval set | 30-case eval shows skill ≥ 90% correct on known cases | Iterate skill prompts before Fix 1B-β at scale |
| **9** | Fix 1C 2D retrieval | 30 vigente questions: 0 derogated leaks; 10 historical questions: ultractividad correct | Engineer-level fix; not project-threatening |
| **10** | Anti-hallucination + 7-chip UI | 0 fabricated article refs in 12-question fixture; all 7 chip variants render | Engineer-level fix |
| **13** | Topic-completeness + corpus-wide hallucination audit | Every registered topic ≥ 5 docs OR de-registered; every `verificación` claim re-verified by skill or doc flagged | SME backlog overflow; defer 3+ topics to v2 |
| **14** | Final pre-launch gate | §1.G ≥ 24/36 in 🟨 or better; zero ❌; golden suite ≥ 90% OK, zero CRITICO; skill audit log clean | Soft-launch denied; data-driven extend-or-liquidate decision |

---

## §11 — Budget allocation ($525K)

| Line | Amount (USD K) | Notes |
|---|---|---|
| Engineering: 2 senior backend × 14 wks | 200 | Lead the structural fixes |
| Engineering: 1 senior backend × 8 wks | 60 | Floats across Fix 2 + Fix 3 + Fix 4 |
| Frontend: 0.5 FTE × 4 wks | 28 | 7 chip variants (was 4) |
| SME: 0.5 FTE × 14 wks | 75 | Skill design free; remaining: extraction QC + golden answers + editorial pass |
| LLM extraction (Fix 1B-β) | 1 | With 70% cache hit, ~$150-400 of LLM spend |
| Cloud infra delta | 6 | Supabase + Falkor + scraper hosting + cache storage |
| QA + CI tooling (Fix 5) | 27 | Judge schema reused from skill; lighter than v1 |
| Tooling: data-eng / ops 0.25 × 14 wks | 30 | Migration ops, deploy gating |
| **Skill scraper infrastructure (NEW)** | 45 | 5 scrapers + cache + smoke fixtures |
| **Skill invocation harness (NEW)** | 15 | `verify_norm(norm_id, periodo) -> Vigencia` API |
| **Skill eval set 30 SME cases (NEW)** | 15 | Tests if skill captures known LIA errors + T-series cases + clean controls |
| **Re-verification cron + scheduled hosting (NEW)** | 8 | 90-day cadence + reform-trigger |
| **Skill smoke + integration tests (NEW)** | 7 | Per-scraper smoke fixtures + skill invocation tests |
| Reserve / contingency | 8 | After absorbing $52K of new skill work |
| **Total** | **525** | |

---

## §12 — What this plan deliberately does NOT do

- **No more incremental gates** (`§1.H`, `§1.I`...) on `next_v5.md`. Chain closed; reopen only after Fix 1+2+3 ship.
- **No threshold relaxation.** Per `feedback_thresholds_no_lower`. The bar stays "safe to send to a client."
- **No soft-launch with disclaimer.** Disclaimers don't transfer the risk.
- **No corpus expansion until Fix 1B-γ lands.** Adding documents without vigencia tracking multiplies contamination surface.
- **No retriever rewrite.** Architecture is sound; Fix 1C changes inputs (vigencia metadata) and the demotion expression — not the algorithm.
- **No LLM model upgrade as first-line fix.** Better model fed contradictory or stale evidence still produces wrong answers.
- **No skill-bypass for "convenience" extractions.** The skill's burden-of-proof discipline is the safety contract — engineers may not write code that emits a `Vigencia` value object without skill or SME-signed manual override.
- **No "trust the binary parser flag" for derived decisions.** Activity 1 proved the flag is too sparse. Use Vigencia value objects (skill-emitted) for any retrieval / display / judge decision.
- **No "lite" conversational mode for the skill in v2 launch.** Deferred to v2.
- **No version-comparator scrapers in v2 launch.** Useful future feature; not on critical path.
- **No municipal-norm verification (ICA, predial) at launch.** Skill's `fuentes-primarias.md` notes this is heterogeneous; out of scope.

---

## §13 — What "done" looks like (updated launch readiness report)

At week 14, the operator runs `make eval-launch-readiness`. The output:

```
=== Launch Readiness Report ===
Vigencia integrity (per Fix 1B-γ):
  vigencia_basis NULL on non-vigente rows:                  0 / N        ✅
  ArticleNode {state in DE,DT,SP,IE} without back-edge:     0 / M        ✅
  Skill audit log: ≥ 2 primary sources per veredicto:       100%         ✅
  EC veredictos with literal condicionamiento:              N / N        ✅
  Topics with 0 docs:                                       0 / 89       ✅

Retrieval safety (per Fix 1C):
  Default-mode queries with derogated-article leaks:        0 / 30       ✅
  Historical queries (vigencia_at_date past) — ultract OK:  10 / 10      ✅
  Pre-Ley-2277 dividend tariff in vigente queries:          0 / 12       ✅
  6-year firmeza claims in vigente queries:                 0 / 8        ✅
  art. 689-1 leaks anywhere:                                0 / 30       ✅

Anti-hallucination (per Fix 3):
  Fabricated article refs in partial-mode answers:          0 / 20       ✅
  Skill refusal rate on poorly-covered queries:             reasonable    ✅

Quality (per Fix 5):
  §1.G SME re-run, 🟨 or better:                          26 / 36      ✅ (≥ 24)
  §1.G SME re-run, ❌:                                      0 / 36       ✅
  Golden answers OK + MENOR:                              96 / 100      ✅ (≥ 90%)
  Golden answers CRITICO:                                   0 / 100      ✅

Skill operational (per Skill Eval + Re-Verify Cron):
  Skill 30-case eval correctness:                          ≥ 90%         ✅
  Re-verification cron last 90 days:                       all green     ✅

LAUNCH READINESS: GREEN — soft-launch to 10–20 friendly cohort APPROVED.
```

If GREEN: soft-launch with explicit beta framing + instrumented client-incident tracking. If RED on any line: data tells us what's broken.

---

## §14 — Glossary (updated)

**Colombian tax law (unchanged from v1):**
- **AG / DIAN / ET / UVT / SMMLV / IPC / vigente / derogado / suspendido / régimen de transición / TTD / IA / INR / RLG / PN / PJ / SAS / ZOMAC / ZESE / Zonas Francas / Concepto DIAN / Consejo de Estado / Sentencia C-/T-/SU-** — see v1 §13.

**Vigencia state codes (NEW v2 — from skill):**
- **V** — Vigente sin modificaciones; cite freely
- **VM** — Vigente modificada; cite ONLY vigente text + chain
- **DE** — Derogada expresa; never cite as vigente
- **DT** — Derogada tácita; cite only with official pronouncement
- **SP** — Suspendida provisional; advertencia + T-series link mandatory
- **IE** — Inexequible; never cite (unless effects diferidos active)
- **EC** — Exequibilidad condicionada; cite WITH literal condicionamiento

**Skill terms (NEW v2):**
- **Veredicto** — Skill's structured output for a (norm, period) query.
- **TRANCHE** — Skill's audit-LIA output format (INCORRECTO/INCOMPLETO/OMISIÓN + GRAVEDAD).
- **Burden of proof inversion** — Skill must refuse veredicto without ≥ 2 primary sources.
- **Aplicabilidad fiscal** — The 2D dimension: vigente *for what period*. Not the same as vigente *today*.
- **Doble fuente primaria** — Mandatory pair of authoritative sources per source-type rules.
- **Ultractividad** — Derogated norm continues to apply to past hechos económicos when it was vigente.

**Project terms (unchanged from v1):**
- **`pipeline_d` / `main chat` / `Normativa` / `Interpretación` / `graph_native` / `graph_native_partial` / `topic_safety_abstention` / Coherence gate Cases A/B/C / `router_topic` vs `effective_topic` / TEMA-first retrieval / Six-gate lifecycle / Status emoji convention** — see v1 §13.

---

## §15 — First-day playbook for a fresh engineer / LLM (updated)

If you are starting on this fix plan with zero context, follow this exact sequence.

**Hour 1 — orient**
1. Read `CLAUDE.md` end-to-end (~15 min).
2. Read `docs/re-engineer/exec_summary_v1.md` (~5 min — the founder's view).
3. Read `docs/re-engineer/makeorbreak_v1.md` §0 + §2 (~15 min).
4. Read `docs/re-engineer/skill_integration_v1.md` (~15 min — the change-driver behind v2).
5. Skim `.claude/skills/vigencia-checker/SKILL.md` (~10 min — the skill router).

**Hour 2 — orient (continued)**
1. Read this document's §0–§0.8 (~20 min — yes, including §0.8 data contracts).
2. Skim `docs/orchestration/orchestration.md` table of contents + env matrix (~10 min).
3. Read `docs/re-engineer/sme_corpus_inventory_2026-04-26.md` (~10 min — the SME's authoritative law map).
4. Skim 1 reference + 1 checklist in `.claude/skills/vigencia-checker/` to get the skill flow concretely (~10 min).
5. **Read the 4 already-extracted veredictos** in `evals/activity_1_5/*.json` to see what the skill output looks like in practice (~10 min).
6. Skim the Round-3 learnings (each ~5 min): `docs/learnings/retrieval/vigencia-binary-flag-too-coarse.md` (Activity 1 measurement), `docs/learnings/retrieval/vigencia-2d-model.md` (the formal × period 2D shape), `docs/learnings/ingestion/corpus-hallucinated-content-EME-A01.md` (the hallucination pattern), `docs/learnings/process/skill-as-verification-engine.md` (the design discipline), `docs/learnings/process/activity-as-surgical-precursor.md` (the Activity → Fix mapping rule), `docs/learnings/process/re-verify-cron-criticality.md` (why the cron moved week 13 → week 5).

**Hour 3 — hands on, low-risk**
1. `make supabase-start && make supabase-status` to bring up local Supabase.
2. `npm run dev:check` to verify launcher preflight passes.
3. `PYTHONPATH=src:. uv run pytest tests/test_phase1_runtime_seams.py -q` — should pass; validates environment.
4. Open `evals/sme_validation_v1/runs/20260427T021512Z_activity1_vigencia_filter/verbatim.md` and read 5 of the 36 verbatim answers. This is the post-Activity-1 ground truth your fix has to improve.

**Hour 4 — locate your fix's anchor files**
1. Find your assigned Sub-fix's "Files — Read first" list in §2-§7.
2. Open each. Read enough to orient.
3. Sketch your plan against the gate-1 + gate-2 template in `docs/aa_next/README.md`.
4. Push the gate-1 + gate-2 sketch to your tech lead for sign-off BEFORE writing any code.

**Day 2 onwards — the discipline**
- Every code change: update the relevant runbook in the same PR.
- Every `LIA_*` flag or migration: bump env matrix + change-log row.
- Every ship: produce gate-3 numeric evidence (not just unit tests) before 🧪.
- Every ship: produce gate-5 target-env evidence before ✅.
- Every status report: Bogotá AM/PM time, plain language, end with concrete next-step.
- **(NEW v2)** Any code that touches vigencia, derogación, modificación: invoke `vigencia-checker` skill. Don't write your own classification logic.

**When you hit something this document doesn't cover**
- Convention question → `CLAUDE.md` first, then `AGENTS.md`.
- Architecture question → `docs/orchestration/orchestration.md` first, then runbook.
- Failure-mode question → `docs/orchestration/coherence-gate-runbook.md` for refusals, `retrieval-runbook.md` for retrieval issues.
- Vigencia question → `.claude/skills/vigencia-checker/` first, NEVER your training-data memory.
- Lessons from past incidents → `docs/learnings/`. Search before reinvention.
- This document is wrong / incomplete → submit a PR adding the section. Don't work around the gap silently.

---

*v2, drafted 2026-04-26 evening immediately after expert vigencia-checker skill delivery + Activity 1 measurement. Supersedes `fixplan_v1.md` (preserved as historical record). Open for amendment by adding numbered sub-sections rather than overwriting.*
