from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class AccessContext:
    tenant_id: str
    accountant_id: str
    accountant_name: str
    allowed_company_ids: tuple[str, ...]
    active_company_id: str
    pais: str
    claims_source: str = "gateway_claims"

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AccessContext":
        allowed_raw = payload.get("allowed_company_ids", [])
        if isinstance(allowed_raw, str):
            allowed = tuple(item.strip() for item in allowed_raw.split(",") if item.strip())
        else:
            allowed = tuple(str(item).strip() for item in allowed_raw if str(item).strip())

        return cls(
            tenant_id=str(payload.get("tenant_id", "")).strip(),
            accountant_id=str(payload.get("accountant_id", "")).strip(),
            accountant_name=str(payload.get("accountant_name", "")).strip(),
            allowed_company_ids=allowed,
            active_company_id=str(payload.get("active_company_id", "")).strip(),
            pais=str(payload.get("pais", "")).strip(),
            claims_source=str(payload.get("claims_source", "gateway_claims")).strip() or "gateway_claims",
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["allowed_company_ids"] = list(self.allowed_company_ids)
        return payload
