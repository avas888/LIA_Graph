from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class PipelineCStrictError(Exception):
    code: str
    stage: str
    message: str
    http_status: int
    remediation: tuple[str, ...] = field(default_factory=tuple)
    details: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


class ComparativeDataMissingError(PipelineCStrictError):
    def __init__(
        self,
        *,
        message: str = "No hay variables suficientes para un comparativo fiscal confiable.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="PC_COMPARATIVE_DATA_MISSING",
            stage="compose",
            message=message,
            http_status=422,
            remediation=(
                "Incluir ingresos anuales, costos deducibles y actividad CIIU exacta.",
                "Agregar retenciones/anticipos y pérdidas compensables del periodo.",
                "Reintentar la consulta con cifras explícitas, no descriptores ambiguos.",
            ),
            details=dict(details or {}),
        )


class EvidenceInsufficientError(PipelineCStrictError):
    def __init__(
        self,
        *,
        message: str = "La evidencia recuperada es insuficiente para emitir una respuesta.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="PC_EVIDENCE_INSUFFICIENT",
            stage="retrieval",
            message=message,
            http_status=422,
            remediation=(
                "Refinar la consulta con más contexto del caso y periodo.",
                "Verificar que el corpus indexado incluya fuentes relevantes al tema.",
                "Ejecutar reindexación si hubo cambios recientes de corpus.",
            ),
            details=dict(details or {}),
        )


class SupabaseRequiredError(PipelineCStrictError):
    def __init__(
        self,
        *,
        message: str = "La ruta de respuesta activa requiere Supabase con la generacion vigente indexada.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="PC_SUPABASE_REQUIRED",
            stage="retrieval",
            message=message,
            http_status=503,
            remediation=(
                "Configurar `LIA_STORAGE_BACKEND=supabase`.",
                "Verificar `SUPABASE_URL` y credenciales activas para el proceso.",
                "Reindexar y confirmar que Supabase contiene la generación activa del corpus.",
            ),
            details=dict(details or {}),
        )


class VerifierBlockedError(PipelineCStrictError):
    def __init__(
        self,
        *,
        message: str = "El verificador bloqueó la respuesta por riesgo de confiabilidad.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="PC_VERIFIER_BLOCKED",
            stage="verify",
            message=message,
            http_status=422,
            remediation=(
                "Aportar evidencia normativa adicional para reducir riesgo.",
                "Evitar afirmaciones legales cerradas sin soporte en citas.",
                "Reintentar con una consulta más acotada al supuesto validado.",
            ),
            details=dict(details or {}),
        )


class LLMProviderUnavailableError(PipelineCStrictError):
    def __init__(
        self,
        *,
        message: str = "No hay proveedor LLM disponible para la ruta estricta.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="PC_LLM_PROVIDER_UNAVAILABLE",
            stage="compose",
            message=message,
            http_status=424,
            remediation=(
                "Configurar un único proveedor activo en config/llm_runtime.json.",
                "Verificar API key y variables de entorno requeridas.",
                "Probar conectividad del proveedor con `uv run python -m lia_graph.dependency_smoke --only gemini`.",
            ),
            details=dict(details or {}),
        )


class LLMProviderExecutionError(PipelineCStrictError):
    def __init__(
        self,
        *,
        message: str = "Falló la ejecución del proveedor LLM.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="PC_LLM_PROVIDER_ERROR",
            stage="compose",
            message=message,
            http_status=424,
            remediation=(
                "Revisar timeout, modelo y credenciales del proveedor seleccionado.",
                "Inspeccionar `error` y `attempts` en `llm` dentro del payload.",
                "Reintentar cuando el proveedor recupere disponibilidad.",
            ),
            details=dict(details or {}),
        )


class LLMOutputQualityError(PipelineCStrictError):
    def __init__(self, *, reason: str, details: dict[str, Any] | None = None) -> None:
        reason_key = str(reason or "").strip().lower()
        if reason_key == "llm_empty":
            code = "PC_LLM_OUTPUT_EMPTY"
            message = "El LLM devolvió salida vacía."
        elif reason_key in {"llm_too_short", "llm_truncated"}:
            code = "PC_LLM_OUTPUT_TRUNCATED"
            message = "La salida LLM falló por truncamiento o longitud insuficiente."
        else:
            code = "PC_LLM_OUTPUT_LOW_QUALITY"
            message = "La salida LLM no pasó la validación de calidad estricta."
        detail_payload = dict(details or {})
        detail_payload["quality_reason"] = reason_key or "unknown"
        super().__init__(
            code=code,
            stage="compose",
            message=message,
            http_status=424,
            remediation=(
                "Reintentar la consulta para obtener una generación completa.",
                "Reducir ambigüedad del prompt y explicitar variables críticas.",
                "Revisar límites de tokens y latencia del proveedor activo.",
            ),
            details=detail_payload,
        )


class StrictConfigError(PipelineCStrictError):
    def __init__(
        self,
        *,
        message: str = "La configuración estricta de LLM es inválida.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="PC_STRICT_CONFIG_INVALID",
            stage="config",
            message=message,
            http_status=500,
            remediation=(
                "Usar `strategy=single_provider` en config/llm_runtime.json.",
                "Mantener exactamente un proveedor `enabled=true` para respuestas.",
                "Alinear `provider_order` con el proveedor activo único.",
            ),
            details=dict(details or {}),
        )


class PipelineCInternalError(PipelineCStrictError):
    def __init__(
        self,
        *,
        message: str = "Error interno en la ruta de respuesta activa.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="PC_INTERNAL_ERROR",
            stage="pipeline",
            message=message,
            http_status=500,
            remediation=(
                "Reintentar la operación.",
                "Revisar trazas del run_id y timeline de ejecucion.",
                "Escalar con trace_id y diagnostics completos si persiste.",
            ),
            details=dict(details or {}),
        )


def as_public_error(
    error: PipelineCStrictError,
    *,
    trace_id: str | None,
    run_id: str | None,
    llm_runtime: dict[str, Any] | None,
    timing: dict[str, Any] | None,
    diagnostics: dict[str, Any] | None,
) -> dict[str, Any]:
    llm_payload = dict(llm_runtime or {})
    public_llm = {
        "selected_provider": llm_payload.get("selected_provider"),
        "selected_type": llm_payload.get("selected_type"),
        "model": llm_payload.get("model") or llm_payload.get("selected_model"),
        "finish_reason": llm_payload.get("finish_reason"),
        "compose_call_count": llm_payload.get("compose_call_count"),
        "attempts": list(llm_payload.get("attempts") or []),
    }
    timing_payload = dict(timing or {})
    public_timing = {
        "pipeline_total_ms": float(timing_payload.get("pipeline_total_ms") or 0.0),
        "stages_ms": dict(timing_payload.get("stages_ms") or {}),
    }
    public_diagnostics: dict[str, Any] = {
        "error_details": dict(error.details or {}),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "error_type": error.__class__.__name__,
    }
    if diagnostics:
        public_diagnostics["pipeline"] = dict(diagnostics)

    return {
        "code": error.code,
        "message": error.message,
        "stage": error.stage,
        "trace_id": str(trace_id or "").strip() or None,
        "run_id": str(run_id or "").strip() or None,
        "http_status": int(error.http_status),
        "remediation": [str(item) for item in error.remediation],
        "llm": public_llm,
        "timing": public_timing,
        "diagnostics": public_diagnostics,
    }
