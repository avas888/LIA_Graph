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
(`scripts/ingest_vigencia_veredictos.py`) reads them and writes to
`norm_vigencia_history`.

Env requirements:
  * `LIA_GEMINI_API_KEY` — set in staging + production per CLAUDE.md.
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
      * `scripts/extract_vigencia.py` — batch driver (1B-β corpus pass).
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
        self.api_key = api_key or os.getenv("LIA_GEMINI_API_KEY")
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
        if len(sources) < 2:
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
        )

    def write_result(self, result: VigenciaResult, *, norm_id: str, output_dir: Path | None = None) -> Path:
        """Persist a VigenciaResult to `evals/vigencia_extraction_v1/<norm_id>.json`."""

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
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
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
    ) -> VigenciaResult:
        # Factories let tests inject a fake adapter without an API key.
        if self._adapter_factory is not None:
            adapter = self._adapter_factory()
        else:
            if not self.api_key:
                return VigenciaResult(
                    veredicto=None,
                    refusal_reason="missing_LIA_GEMINI_API_KEY",
                    audit=ExtractionAudit(skill_version=SKILL_VERSION, method="harness"),
                )
            adapter = self._default_adapter()

        prompt = self._build_prompt(norm_id=norm_id, periodo=periodo, as_of=as_of, sources=sources)
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
        )

    def _default_adapter(self) -> Any:
        from lia_graph.gemini_runtime import GeminiChatAdapter
        return GeminiChatAdapter(
            api_key=self.api_key or "",
            model=self.model,
            base_url=self.base_url,
            timeout_seconds=self.timeout_seconds,
            temperature=self.temperature,
        )

    def _build_prompt(
        self,
        *,
        norm_id: str,
        periodo: PeriodoFiscal | None,
        as_of: date,
        sources: Sequence[ScraperFetchResult],
    ) -> str:
        sources_block = "\n\n".join(
            f"## Fuente {i+1}: {s.source} — {s.url}\n\n{s.parsed_text[:6000]}"
            for i, s in enumerate(sources)
        )
        periodo_block = (
            json.dumps(periodo.to_dict(), ensure_ascii=False)
            if periodo
            else "null"
        )
        return f"""You are the `vigencia-checker@2.0` skill. Produce a v3 Vigencia
JSON object for the norm_id below. State must be one of
V/VM/DE/DT/SP/IE/EC/VC/VL/DI/RV. Refuse with `refusal_reason` if you do
not have ≥ 2 primary sources or if their evidence is contradictory.

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

Return ONLY a JSON object matching the v3 Vigencia schema (state /
state_from / state_until / applies_to_kind / applies_to_payload /
change_source / interpretive_constraint / fuentes_primarias_consultadas /
extraction_audit). No prose. No markdown fences."""

    def _parse_skill_output(self, raw: str, *, wall_ms: int) -> VigenciaResult:
        text = raw.strip()
        if text.startswith("```"):
            # Strip code fences if the model added them
            text = text.strip("`")
            text = text.replace("json\n", "", 1).strip()
        try:
            blob = json.loads(text)
        except json.JSONDecodeError as err:
            return VigenciaResult(
                veredicto=None,
                refusal_reason=f"non_json_skill_output: {err}",
                audit=ExtractionAudit(
                    skill_version=SKILL_VERSION,
                    method="skill",
                    wall_ms=wall_ms,
                ),
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
            )
        try:
            veredicto = Vigencia.from_dict(blob)
        except Exception as err:
            return VigenciaResult(
                veredicto=None,
                refusal_reason=f"invalid_vigencia_shape: {err}",
                audit=ExtractionAudit(
                    skill_version=SKILL_VERSION,
                    method="skill",
                    wall_ms=wall_ms,
                ),
            )
        return VigenciaResult(
            veredicto=veredicto,
            audit=ExtractionAudit(
                skill_version=SKILL_VERSION,
                method="skill",
                wall_ms=wall_ms,
            ),
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _slug(norm_id: str) -> str:
    """Filename-safe representation of a canonical norm_id."""

    return norm_id.replace("/", "_")


__all__ = [
    "DEFAULT_OUTPUT_DIR",
    "PeriodoFiscal",
    "SKILL_VERSION",
    "VigenciaSkillHarness",
]
