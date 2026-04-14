from __future__ import annotations

from dataclasses import dataclass

from .contracts import AccessContext, CompanyContext

_ALLOWED_BLOCK_REASONS = {
    "access_denied_company_not_allowed",
    "access_denied_tenant_mismatch",
    "scope_denied_country_mismatch",
}


@dataclass(frozen=True)
class AccessCheckResult:
    allowed: bool
    reason: str | None = None


def validate_access_scope(
    access_context: AccessContext,
    request_pais: str,
    company_context: CompanyContext | None,
) -> AccessCheckResult:
    if access_context.active_company_id not in set(access_context.allowed_company_ids):
        return AccessCheckResult(allowed=False, reason="access_denied_company_not_allowed")

    if access_context.pais != request_pais:
        return AccessCheckResult(allowed=False, reason="scope_denied_country_mismatch")

    if company_context is None:
        return AccessCheckResult(allowed=True)

    if company_context.company_id != access_context.active_company_id:
        return AccessCheckResult(allowed=False, reason="access_denied_company_not_allowed")

    if company_context.tenant_id != access_context.tenant_id:
        return AccessCheckResult(allowed=False, reason="access_denied_tenant_mismatch")

    if company_context.pais != request_pais:
        return AccessCheckResult(allowed=False, reason="scope_denied_country_mismatch")

    return AccessCheckResult(allowed=True)


def build_access_scope_refusal(reason: str) -> str:
    safe_reason = reason if reason in _ALLOWED_BLOCK_REASONS else "access_denied_company_not_allowed"
    return (
        "1) Resumen ejecutivo\\n"
        "La respuesta fue bloqueada por control de acceso multitenant.\\n\\n"
        "2) Motivo de bloqueo\\n"
        f"{safe_reason}\\n\\n"
        "3) Siguiente paso\\n"
        "Verifica tenant, compania activa, companias permitidas y pais de la solicitud."
    )
