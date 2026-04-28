"""fixplan_v3 sub-fix 1B-β — skill-guided vigencia extractor harness.

Wraps the `vigencia-checker@2.0` skill as a callable agent loop. Per
norm_id (article OR sub-unit) cited anywhere in the corpus:

  1. Identify (norm_type, norm_id, parent_norm_id, sub_unit_kind) from canon.
  2. Pull cached primary-source content via the `ScraperRegistry`.
  3. Invoke the skill (Gemini 2.5 Pro through the OpenAI-compatible adapter).
  4. Validate the output via the v3 `Vigencia` Pydantic-equivalent dataclass.
  5. Write to `evals/vigencia_extraction_v1/<norm_id>.json` (success) OR log
     refusal with structured reason.

The harness has no DB knowledge. It produces JSON files; the 1B-γ sink
(`scripts/canonicalizer/ingest_vigencia_veredictos.py`) reads them and writes to
`norm_vigencia_history`.

Env requirements:
  * `GEMINI_API_KEY` (preferred — matches the rest of the repo) or
    `LIA_GEMINI_API_KEY` (legacy alias, still honored).
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from lia_graph.canon import (
    InvalidNormIdError,
    assert_valid_norm_id,
    is_sub_unit,
    norm_type as canon_norm_type,
    parent_norm_id as canon_parent_norm_id,
    sub_unit_kind as canon_sub_unit_kind,
)
from lia_graph.scrapers import ScraperRegistry
from lia_graph.scrapers.base import ScraperFetchResult
from lia_graph.vigencia import (
    ExtractionAudit,
    Vigencia,
    VigenciaResult,
    VigenciaState,
)

LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PeriodoFiscal:
    impuesto: str
    year: int
    period_label: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "impuesto": self.impuesto,
            "year": int(self.year),
            "period_label": self.period_label,
        }


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


DEFAULT_GEMINI_OPENAI_BASE_URL = (
    "https://generativelanguage.googleapis.com/v1beta/openai"
)
DEFAULT_MODEL = "gemini-2.5-pro"
DEFAULT_TIMEOUT_S = 90.0
DEFAULT_MAX_TOOL_ITERATIONS = 12
DEFAULT_TEMPERATURE = 0.1
DEFAULT_OUTPUT_DIR = Path("evals/vigencia_extraction_v1")
SKILL_VERSION = "vigencia-checker@2.0"


class VigenciaSkillHarness:
    """Single Python entry point for invoking vigencia-checker.

    Callers:
      * `scripts/canonicalizer/extract_vigencia.py` — batch driver (1B-β corpus pass).
      * `cron/cascade_consumer.py` — re-verify queue consumer (1F).
      * Activity 1.5/1.6/1.7 manual fixtures — recorded as JSON files (no
        live API call needed).

    The harness's I/O surface is intentionally narrow: `verify_norm(...)` →
    `VigenciaResult`. The caller decides whether to write the result to
    disk or to enqueue for cron.
    """

    def __init__(
        self,
        *,
        scrapers: ScraperRegistry,
        canonicalize_fn=None,
        model: str = DEFAULT_MODEL,
        api_key: str | None = None,
        base_url: str = DEFAULT_GEMINI_OPENAI_BASE_URL,
        max_tool_iterations: int = DEFAULT_MAX_TOOL_ITERATIONS,
        timeout_seconds: float = DEFAULT_TIMEOUT_S,
        temperature: float = DEFAULT_TEMPERATURE,
        # Test seam: a callable taking the prompt + tool results and
        # returning an already-shaped Vigencia. Used by the cascade unit
        # tests to avoid a real API call.
        adapter_factory=None,
    ) -> None:
        self.scrapers = scrapers
        self.canonicalize_fn = canonicalize_fn
        self.model = model
        self.api_key = (
            api_key
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("LIA_GEMINI_API_KEY")  # back-compat: legacy alias
        )
        self.base_url = base_url
        self.max_tool_iterations = int(max_tool_iterations)
        self.timeout_seconds = float(timeout_seconds)
        self.temperature = float(temperature)
        self._adapter_factory = adapter_factory

    @classmethod
    def default(cls) -> "VigenciaSkillHarness":
        """Build a harness from the standard 5-scraper registry + default Gemini config."""

        from lia_graph.scrapers.cache import ScraperCache
        from lia_graph.scrapers.consejo_estado import ConsejoEstadoScraper
        from lia_graph.scrapers.corte_constitucional import CorteConstitucionalScraper
        from lia_graph.scrapers.dian_normograma import DianNormogramaScraper
        from lia_graph.scrapers.secretaria_senado import SecretariaSenadoScraper
        from lia_graph.scrapers.suin_juriscol import SuinJuriscolScraper

        cache = ScraperCache()
        registry = ScraperRegistry(
            [
                SecretariaSenadoScraper(cache),
                DianNormogramaScraper(cache),
                SuinJuriscolScraper(cache),
                CorteConstitucionalScraper(cache),
                ConsejoEstadoScraper(cache),
            ]
        )
        return cls(scrapers=registry)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def verify_norm(
        self,
        *,
        norm_id: str,
        sub_unit: str | None = None,
        periodo: PeriodoFiscal | None = None,
        as_of: date | None = None,
    ) -> VigenciaResult:
        try:
            assert_valid_norm_id(norm_id)
        except InvalidNormIdError as err:
            return VigenciaResult(
                veredicto=None,
                refusal_reason=f"invalid_norm_id: {err}",
                audit=ExtractionAudit(skill_version=SKILL_VERSION, method="harness"),
            )
        if sub_unit and not norm_id.endswith(f".{sub_unit}"):
            # Append the sub-unit if the caller didn't already include it.
            norm_id = f"{norm_id}.{sub_unit}"
            try:
                assert_valid_norm_id(norm_id)
            except InvalidNormIdError as err:
                return VigenciaResult(
                    veredicto=None,
                    refusal_reason=f"invalid_sub_unit: {err}",
                    audit=ExtractionAudit(skill_version=SKILL_VERSION, method="harness"),
                )

        # Fetch primary sources from cache (live HTTP path is gated; production
        # uses pre-warmed cache).
        sources = self.scrapers.fetch_all(norm_id)
        single_source_accepted: str | None = None
        if len(sources) < 2:
            # fixplan_v5 §3 #1 Approach B — many Colombian leyes (789/2002,
            # 797/2003, 1258/2008, 1438/2011, 1751/2015, 2381/2024, …) live
            # ONLY on Senado; DIAN normograma 404s and SUIN is currently
            # disabled. If the lone passing source is `secretaria_senado`
            # AND its content references the norm's article (or law) number,
            # accept it instead of refusing. Senado is an authoritative
            # `.gov.co` site, so this matches the prompt's existing
            # single-source acceptance rule (per fixplan_v4 §2.3 #14).
            if _senado_single_source_accepted(sources, norm_id):
                single_source_accepted = sources[0].source
            else:
                return VigenciaResult(
                    veredicto=None,
                    refusal_reason="missing_double_primary_source",
                    missing_sources=tuple(
                        s.source_id for s in self.scrapers.for_norm(norm_id)
                    ),
                    audit=ExtractionAudit(skill_version=SKILL_VERSION, method="harness"),
                )

        return self._invoke_skill(
            norm_id=norm_id,
            periodo=periodo,
            as_of=as_of or date.today(),
            sources=sources,
            single_source_accepted=single_source_accepted,
        )

    def write_result(self, result: VigenciaResult, *, norm_id: str, output_dir: Path | None = None) -> Path:
        """Persist a VigenciaResult to `evals/vigencia_extraction_v1/<norm_id>.json`.

        Uses atomic temp+rename + fsync so a crash / power-loss mid-write
        cannot leave a half-written JSON. Each veredicto is durable on
        disk before the harness moves to the next norm.
        """

        target_dir = output_dir or DEFAULT_OUTPUT_DIR
        target_dir.mkdir(parents=True, exist_ok=True)
        path = target_dir / f"{_slug(norm_id)}.json"
        payload = {
            "norm_id": norm_id,
            "norm_type": canon_norm_type(norm_id),
            "parent_norm_id": canon_parent_norm_id(norm_id),
            "is_sub_unit": is_sub_unit(norm_id),
            "sub_unit_kind": canon_sub_unit_kind(norm_id),
            "extraction_run_id": result.audit.run_id if result.audit else None,
            "extracted_at_utc": datetime.now(timezone.utc).isoformat(),
            "result": result.to_dict(),
        }
        body = json.dumps(payload, indent=2, ensure_ascii=False)
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        # Write to temp, fsync, then atomic rename. POSIX guarantees the
        # rename is atomic within the same filesystem — a reader can NEVER
        # see a partial JSON.
        with tmp_path.open("w", encoding="utf-8") as fh:
            fh.write(body)
            fh.flush()
            try:
                os.fsync(fh.fileno())
            except OSError:
                pass  # fsync isn't available on all filesystems; rename still atomic
        os.replace(tmp_path, path)
        return path

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _invoke_skill(
        self,
        *,
        norm_id: str,
        periodo: PeriodoFiscal | None,
        as_of: date,
        sources: Sequence[ScraperFetchResult],
        single_source_accepted: str | None = None,
    ) -> VigenciaResult:
        # Factories let tests inject a fake adapter without an API key.
        if self._adapter_factory is not None:
            adapter = self._adapter_factory()
        else:
            if not self.api_key:
                return VigenciaResult(
                    veredicto=None,
                    refusal_reason="missing_GEMINI_API_KEY",
                    audit=ExtractionAudit(skill_version=SKILL_VERSION, method="harness"),
                    single_source_accepted=single_source_accepted,
                )
            adapter = self._default_adapter()

        prompt = self._build_prompt(norm_id=norm_id, periodo=periodo, as_of=as_of, sources=sources)
        # Cross-process throttle: respects the project-wide Gemini RPM cap
        # so concurrent harnesses (parallel runner) don't burst past 150
        # RPM (Tier 1 hard limit on gemini-2.5-pro). Skip via
        # `LIA_GEMINI_GLOBAL_DISABLED=1` for single-batch runs.
        try:
            from lia_graph.gemini_throttle import acquire_token
            acquire_token()
        except Exception as err:
            LOGGER.debug("Gemini throttle acquire skipped: %s", err)
        start = time.monotonic()
        try:
            raw = adapter.generate(prompt)
        except Exception as err:
            return VigenciaResult(
                veredicto=None,
                refusal_reason=f"adapter_error: {err}",
                audit=ExtractionAudit(skill_version=SKILL_VERSION, method="harness"),
            )
        wall_ms = int((time.monotonic() - start) * 1000)

        return self._parse_skill_output(
            raw,
            wall_ms=wall_ms,
            norm_id=norm_id,
            single_source_accepted=single_source_accepted,
        )

    def _default_adapter(self) -> Any:
        """Resolve an LLM adapter via the shared runtime config.

        The runtime config (`config/llm_runtime.json`) declares the
        provider ordering. `resolve_llm_adapter()` walks the ordered
        list, instantiates the first one whose API key env-var is set,
        and returns its adapter. This is how the canonicalizer becomes
        provider-agnostic — set `provider_order: ["deepseek-..."]` to
        route through DeepSeek; set Gemini first to fall back to Gemini.
        Both adapters expose `.generate(prompt) -> str` so the
        downstream parsing path is identical.

        Override per-call by passing `adapter_factory` to the harness
        (test seam) or by setting `LIA_VIGENCIA_PROVIDER=<id>` to force
        a specific provider id from the config.
        """

        from lia_graph.llm_runtime import resolve_llm_adapter

        requested = os.getenv("LIA_VIGENCIA_PROVIDER", "").strip() or None
        adapter, info = resolve_llm_adapter(requested_provider=requested)
        if adapter is None:
            # No provider available — fall back to the legacy Gemini path
            # that uses the harness's own `self.api_key` (which read
            # GEMINI_API_KEY at construction). This preserves
            # back-compat for any caller that pre-loaded the key.
            from lia_graph.gemini_runtime import GeminiChatAdapter
            LOGGER.warning(
                "resolve_llm_adapter found no provider (%s); using direct GeminiChatAdapter as fallback.",
                info.get("fallback_skipped"),
            )
            return GeminiChatAdapter(
                api_key=self.api_key or "",
                model=self.model,
                base_url=self.base_url,
                timeout_seconds=self.timeout_seconds,
                temperature=self.temperature,
            )
        LOGGER.info(
            "vigencia harness using LLM provider: %s (%s, model=%s)",
            info.get("selected_provider"),
            info.get("selected_type"),
            info.get("model"),
        )
        return adapter

    def _build_prompt(
        self,
        *,
        norm_id: str,
        periodo: PeriodoFiscal | None,
        as_of: date,
        sources: Sequence[ScraperFetchResult],
    ) -> str:
        # 16000 chars per source — fits the DIAN article-slice (typically
        # 2–9 KB) plus the Senado segment page (typically 30–50 KB
        # truncated to 16 KB of the relevant article block).
        sources_block = "\n\n".join(
            f"## Fuente {i+1}: {s.source} — {s.url}\n\n{(s.parsed_text or '')[:16000]}"
            for i, s in enumerate(sources)
        )
        periodo_block = (
            json.dumps(periodo.to_dict(), ensure_ascii=False)
            if periodo
            else "null"
        )
        return f"""You are the `vigencia-checker@2.0` skill. Produce a v3 Vigencia
JSON object for the norm_id below.

# Hard rules — read carefully

1. **Output ONLY a single JSON object.** No prose, no markdown fences, no
   explanation. The very first character of your output must be `{{` and the
   last must be `}}`.

2. **Every date field must be `YYYY-MM-DD`.** NEVER put a norm_id, a free
   text date, or `null` as a string into a date field. If you don't know
   the date, omit the field or use the literal `null` (no quotes).

3. **`state` must be one of**: `V`, `VM`, `DE`, `DT`, `SP`, `IE`, `EC`,
   `VC`, `VL`, `DI`, `RV`.

3a. **For state `V` (vigente, never modified)**: `change_source` MUST be
    `null`. Do NOT invent a `compilacion`-style change_source for an
    article that's been in force unchanged since enactment. Use
    `state_from` = the date the article was first issued.

3b. **For EVERY OTHER state** (`VM`, `DE`, `DT`, `SP`, `IE`, `EC`, `VC`,
    `VL`, `DI`, `RV`): `change_source` is REQUIRED — it must be a
    non-null JSON object. The state-to-type alignment is:
      - `VM` → `change_source.type = "reforma"`
      - `DE` → `change_source.type = "derogacion_expresa"`
      - `DT` → `change_source.type = "derogacion_tacita"`
      - `SP` → `change_source.type = "auto_ce_suspension"`
      - `IE` → `change_source.type = "sentencia_cc"` or `"sentencia_ce_nulidad"`
      - `EC` → `change_source.type = "sentencia_cc"`
      - `VC` → `change_source.type = "modulacion_doctrinaria"` or `"concepto_dian_modificatorio"`
      - `VL` → `change_source.type = "vacatio"`
      - `DI` → `change_source.type = "sentencia_cc"`
      - `RV` → `change_source.type = "reviviscencia"`

4. **`state_from` is required** and must be the date the current state
   took effect (e.g. for `VM`, the date of the modification; for `V`,
   the date the article was originally issued).

5. **`change_source` must be a JSON object**, NEVER a bare string. Its
   shape is `{{"type": "...", "source_norm_id": "...", "effect_type": "...", "effect_payload": {{...}}}}`.

6. **`change_source.type` must be EXACTLY one of these values** (lowercase, snake_case):
     - `reforma` — a `ley` modified the norm (state VM)
     - `derogacion_expresa` — explicit derogation by ley/decreto (state DE)
     - `derogacion_tacita` — implicit/tacit derogation by later ley (state DT)
     - `sentencia_cc` — Corte Constitucional sentencia (state IE / EC / DI)
     - `auto_ce_suspension` — Consejo de Estado suspension (state SP)
     - `sentencia_ce_nulidad` — Consejo de Estado nullity (state IE)
     - `reviviscencia` — revival after IE (state RV)
     - `vacatio` — vacatio legis pending (state VL)
     - `concepto_dian_modificatorio` — DIAN concept modulation (state VC)
     - `modulacion_doctrinaria` — doctrinal modulation (state VC)
   NEVER invent new types like `compilacion`, `adopcion`, `sustitucion`, etc.
   When a norm is modified by another ley, use `reforma`. When it's republished in
   a compilation (e.g. DUR), the underlying state is whatever the original change
   was — use that change_source type, NOT `compilacion`.

7. **`effect_type` must be one of**: `pro_futuro`, `retroactivo`,
   `diferido`, `per_period`. (For `reforma`, default is `pro_futuro`.)

8. **`applies_to_kind` must be one of**: `always`, `per_year`, `per_period`.
   NEVER use `general`, `universal`, `tributario`, etc. If the norm applies
   regardless of fiscal year (e.g. procedimiento articles like RUT,
   firmeza, sanciones), use `always`. If it varies by año gravable, use
   `per_year`. If it varies by period within a year (e.g. monthly IVA),
   use `per_period`.

9. **`fuentes_primarias_consultadas` is a list of objects**, each with at
   least `{{"norm_id": "...", "norm_type": "url"}}` — never a list of strings.

10. **Citation shape**. The fields `inexequibilidad`, `suspension`,
    `regimen_transicion`, and every item in `derogado_por`,
    `modificado_por`, `fuentes_primarias_consultadas` use ONE shape — the
    Citation: `{{"norm_id": "...", "norm_type": "...", "article": "...",
    "fecha": "YYYY-MM-DD", "primary_source_url": "..."}}`. Only `norm_id`
    is required; the others are optional.
    NEVER invent fields like `type`, `condicion`, `source_norm_id`,
    `effect_type` inside a Citation. Those belong in `change_source`,
    not in citations.

11. **`interpretive_constraint` is NEVER a plain string.** It is either
    `null` (the common case) OR a JSON object with EXACTLY these four
    fields:
      - `sentencia_norm_id` — the C-/T-/SU-/auto.ce.* id whose text imposes the constraint
      - `fecha_sentencia` — `YYYY-MM-DD`
      - `texto_literal` — the verbatim "en el entendido que…" passage from the sentencia
      - `fuente_verificada_directo` — `true` if you saw the literal text in the consulted sentencia source, `false` if you inferred from a secondary source
    Set `interpretive_constraint` to a non-null object ONLY when the state
    is `EC` or `VC` AND a sentencia constrains how the article must be
    interpreted. For ALL other cases (V, VM, DE, DT, IE, SP, RV, VL, DI),
    `interpretive_constraint` MUST be `null`. NEVER use this field for
    free-text editorial notes, transitory comments, or paraphrases.

6. **Refuse only as last resort.** Prefer 2 primary sources with
   independent evidence about the norm. **BUT** if only one source
   contains the specific article you're extracting AND that source is
   an authoritative `.gov.co` site (DIAN normograma, Secretaría del
   Senado, SUIN-Juriscol, Corte Constitucional, Consejo de Estado),
   PROCEED with the extraction using that single source. Note this
   in the audit by setting `fuente_verificada_directo: true` only on
   the source that actually contained the article.

   Refuse with:
   `{{"refusal_reason": "INSUFFICIENT_PRIMARY_SOURCES", "missing_sources": ["..."]}}`
   ONLY when:
   - Zero `.gov.co` sources contain the article, OR
   - The two sources contradict each other on a material point (state,
     date, or change_source) AND you cannot pick the canonical reading.

   Do NOT refuse just because the evidence is "complex" or "ambiguous" —
   pick the best-supported state and explain via `interpretive_constraint`
   when relevant. Do NOT refuse just because the secondary source is
   truncated or covers a different article — work with the source that
   has the article.

# Output schema (literal example — match this shape)

```
{{
  "state": "VM",
  "state_from": "2023-05-19",
  "state_until": null,
  "applies_to_kind": "per_period",
  "applies_to_payload": {{
    "year_start": 2023,
    "year_end": null,
    "impuesto": "renta",
    "period_start": "2023-01-01",
    "period_end": null,
    "art_338_cp_shift": false
  }},
  "change_source": {{
    "type": "reforma",
    "source_norm_id": "ley.2294.2023.art.69",
    "effect_type": "pro_futuro",
    "effect_payload": {{"fecha": "2023-05-19"}}
  }},
  "interpretive_constraint": null,
  "derogado_por": null,
  "modificado_por": [
    {{
      "norm_id": "ley.2294.2023.art.69",
      "norm_type": "ley",
      "article": "Art. 69",
      "fecha": "2023-05-19",
      "primary_source_url": "..."
    }}
  ],
  "suspension": null,
  "inexequibilidad": null,
  "regimen_transicion": null,
  "revives_text_version": null,
  "rige_desde": null,
  "fuentes_primarias_consultadas": [
    {{"norm_id": "<source-id-or-url-key>", "norm_type": "url", "url": "..."}},
    {{"norm_id": "<source-id-or-url-key>", "norm_type": "url", "url": "..."}}
  ]
}}
```

The `extraction_audit` field is NOT your responsibility — the harness
fills it. Do not include it.

# Input

norm_id: {norm_id}
norm_type: {canon_norm_type(norm_id)}
parent_norm_id: {canon_parent_norm_id(norm_id)}
is_sub_unit: {is_sub_unit(norm_id)}
sub_unit_kind: {canon_sub_unit_kind(norm_id)}
periodo: {periodo_block}
as_of: {as_of.isoformat()}

# Primary sources

{sources_block}

# Output

A single JSON object matching the schema above. Nothing else."""

    def _parse_skill_output(
        self,
        raw: str,
        *,
        wall_ms: int,
        norm_id: str | None = None,
        single_source_accepted: str | None = None,
    ) -> VigenciaResult:
        text = raw.strip()
        if text.startswith("```"):
            # Strip code fences if the model added them
            text = text.strip("`")
            text = text.replace("json\n", "", 1).strip()
        try:
            blob = json.loads(text)
        except json.JSONDecodeError as err:
            _log_raw_skill_output(norm_id, raw, error=f"non_json: {err}")
            return VigenciaResult(
                veredicto=None,
                refusal_reason=f"non_json_skill_output: {err}",
                audit=ExtractionAudit(
                    skill_version=SKILL_VERSION,
                    method="skill",
                    wall_ms=wall_ms,
                ),
                single_source_accepted=single_source_accepted,
            )
        if blob.get("refusal_reason"):
            return VigenciaResult(
                veredicto=None,
                refusal_reason=str(blob["refusal_reason"]),
                missing_sources=tuple(blob.get("missing_sources") or ()),
                audit=ExtractionAudit(
                    skill_version=SKILL_VERSION,
                    method="skill",
                    wall_ms=wall_ms,
                ),
                single_source_accepted=single_source_accepted,
            )
        try:
            veredicto = Vigencia.from_dict(blob)
        except Exception as err:
            # Persist the raw blob so we can debug the shape mismatch without
            # re-running the (expensive) Gemini call. See
            # `docs/learnings/canonicalizer/`.
            _log_raw_skill_output(norm_id, raw, error=f"invalid_shape: {err}")
            return VigenciaResult(
                veredicto=None,
                refusal_reason=f"invalid_vigencia_shape: {err}",
                audit=ExtractionAudit(
                    skill_version=SKILL_VERSION,
                    method="skill",
                    wall_ms=wall_ms,
                ),
                single_source_accepted=single_source_accepted,
            )
        return VigenciaResult(
            veredicto=veredicto,
            audit=ExtractionAudit(
                skill_version=SKILL_VERSION,
                method="skill",
                wall_ms=wall_ms,
            ),
            single_source_accepted=single_source_accepted,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_SENADO_SOURCE_ID = "secretaria_senado"
# Trusted .gov.co primary sources: any single one of these is acceptable
# under the §3 #1 Approach B relaxation when SUIN is disabled and the
# remaining scrapers don't double up. Adding `dian_normograma` here is what
# unblocks the DUR-articulado batches (E1*/E2*/E3*/J8b/D5/F2) — DIAN
# normograma is the single authoritative source for `decreto.1625.2016.*`,
# `decreto.1072.2015.*`, `res.dian.*` and most `concepto.dian.*`. SUIN is
# excluded because its scraper currently returns None for everything.
_TRUSTED_GOVCO_SOURCE_IDS = frozenset({"secretaria_senado", "dian_normograma"})


def _senado_single_source_accepted(
    sources: Sequence[ScraperFetchResult],
    norm_id: str,
) -> bool:
    """fixplan_v5 §3 #1 Approach B — single-source `.gov.co` acceptance.

    Returns True iff the harness should let the LLM call proceed even though
    fewer than 2 primary sources returned content. The narrow rule: exactly
    one source returned non-empty content AND that source is one of the
    trusted `.gov.co` primary scrapers (`secretaria_senado` for leyes/CST/
    CCo/ET; `dian_normograma` for decretos/resoluciones/conceptos hosted on
    DIAN normograma) AND the fetched content references the norm's article
    number (or the law/decreto NUM, when the norm_id has no article suffix).
    For all other shapes the caller must keep raising
    ``missing_double_primary_source``.

    Function name kept for git-history continuity; behavior now spans both
    Senado and DIAN.
    """

    if len(sources) != 1:
        return False
    only = sources[0]
    if only.source not in _TRUSTED_GOVCO_SOURCE_IDS:
        return False
    body = only.parsed_text or ""
    if not body.strip():
        return False
    needle = _norm_id_acceptance_needle(norm_id)
    if needle is None:
        # Couldn't derive a check — be conservative and refuse.
        return False
    return needle in body


def _norm_id_acceptance_needle(norm_id: str) -> str | None:
    """Return the integer (or dotted DUR article) that must appear in the
    fetched body for single-source acceptance.

    * `et.art.<MMM>[...]`                       → `<MMM>` (article number)
    * `ley.<NNN>.<YYYY>.art.<MMM>[...]`         → `<MMM>` (article number)
    * `ley.<NNN>.<YYYY>`                        → `<NNN>` (law number)
    * `decreto.<NNN>.<YYYY>.art.<A.B.C.D...>`   → `<A.B.C.D...>` (full DUR
      article path joined with dots — matches `[[ART:A.B.C.D]]` markers
      injected by the DIAN scraper, AND matches plain dotted spans in the
      decreto body. Falls back to the shorter form when only one segment.)
    * `decreto.<NNN>.<YYYY>`                    → `<NNN>` (decreto number)
    * `res.dian.<NN>.<YYYY>.art.<MMM>[...]`     → `<MMM>` (article number)
    * `res.dian.<NN>.<YYYY>`                    → `<NN>` (resolution number)
    * `concepto.dian.<num>[.num.<NN>...]`       → `<num>` (concepto identifier)
    * Anything else                              → None (caller refuses).
    """

    parts = norm_id.split(".")
    if ".art." in norm_id:
        try:
            idx = parts.index("art")
        except ValueError:
            return None
        # Consume all numeric segments after `art` so DUR-style articles
        # like `1.1.1.4.10` get matched as a unit (the legacy single-segment
        # path returned just "1", which is too permissive but harmless).
        article_segments: list[str] = []
        for seg in parts[idx + 1:]:
            if seg.isdigit():
                article_segments.append(seg)
            else:
                break
        if not article_segments:
            return None
        return ".".join(article_segments)
    if norm_id.startswith("ley.") and len(parts) >= 3:
        candidate = parts[1]
        if candidate.isdigit():
            return candidate
    if norm_id.startswith("decreto.") and len(parts) >= 3:
        candidate = parts[1]
        if candidate.isdigit():
            return candidate
    if norm_id.startswith("res.dian.") and len(parts) >= 4:
        candidate = parts[2]
        if candidate.isdigit():
            return candidate
    if norm_id.startswith("concepto.dian.") and len(parts) >= 3:
        # Conceptos may carry suffixes like `0001-2003` or `100208192-202` —
        # the bare identifier alone is enough; if DIAN's body talks about it
        # at all, that string will appear.
        return parts[2]
    return None


def _is_dotted_dur_article(value: str) -> bool:
    """DUR articles use dotted form like ``1.2.1.5.4``; treat as opaque tag."""

    return bool(value) and all(seg.isdigit() for seg in value.split("."))


def _slug(norm_id: str) -> str:
    """Filename-safe representation of a canonical norm_id."""

    return norm_id.replace("/", "_")


def _log_raw_skill_output(norm_id: str | None, raw: str, *, error: str) -> None:
    """Persist the raw Gemini output that failed to validate.

    These dumps go to ``evals/vigencia_extraction_v1/_debug/<norm_id>.json``
    (a flat directory — easy to grep when triaging shape patterns). The
    caller continues — this is best-effort logging, not the critical
    path. See `docs/learnings/canonicalizer/`.
    """

    debug_dir = Path("evals/vigencia_extraction_v1/_debug")
    try:
        debug_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        return
    slug = _slug(norm_id or "unknown_norm")
    blob = {
        "norm_id": norm_id,
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "error": error,
        "raw_output": raw,
        "raw_output_len": len(raw),
    }
    try:
        path = debug_dir / f"{slug}.json"
        path.write_text(json.dumps(blob, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        # Never let logging interfere with the extraction outcome.
        return


__all__ = [
    "DEFAULT_OUTPUT_DIR",
    "PeriodoFiscal",
    "SKILL_VERSION",
    "VigenciaSkillHarness",
]
