from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class CompanyContext:
    company_name: str
    period: str
    company_id: str = ""
    tenant_id: str = ""
    pais: str = "colombia"
    currency: str = "COP"
    taxpayer_type: str | None = None
    legal_form: str | None = None
    tax_regime: str | None = None
    fiscal_year: int | None = None
    filing_status: str | None = None
    objective: str | None = None
    available_supports: list[str] | None = None
    constraints: str = ""
    industry: str | None = None
    revenue: float | None = None
    costs: float | None = None
    gross_profit: float | None = None
    taxable_income: float | None = None
    prior_year_tax_losses: float | None = None
    withholding_tax_credits: float | None = None
    tax_advance_credits: float | None = None
    vat_payable: float | None = None
    vat_creditable: float | None = None
    ica_base: float | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_markdown(self) -> str:
        rows: list[str] = [
            f"- Empresa: {self.company_name}",
            f"- Company ID: {self.company_id}",
            f"- Tenant ID: {self.tenant_id}",
            f"- Pais: {self.pais}",
            f"- Periodo: {self.period}",
            f"- Moneda: {self.currency}",
        ]

        optional_rows: list[tuple[str, Any]] = [
            ("Tipo de contribuyente", self.taxpayer_type),
            ("Forma legal", self.legal_form),
            ("Regimen tributario", self.tax_regime),
            ("Ano gravable", self.fiscal_year),
            ("Estado del filing", self.filing_status),
            ("Objetivo del caso", self.objective),
            ("Restricciones", self.constraints),
            ("Sector", self.industry),
            ("Ingresos", self.revenue),
            ("Costos", self.costs),
            ("Utilidad bruta", self.gross_profit),
            ("Renta liquida estimada", self.taxable_income),
            ("Perdidas fiscales anos previos", self.prior_year_tax_losses),
            ("Retenciones o creditos tributarios", self.withholding_tax_credits),
            ("Anticipos tributarios", self.tax_advance_credits),
            ("IVA por pagar", self.vat_payable),
            ("IVA descontable", self.vat_creditable),
            ("Base ICA", self.ica_base),
            ("Notas", self.notes),
        ]

        for label, value in optional_rows:
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            rows.append(f"- {label}: {value}")

        if self.available_supports:
            rows.append(f"- Soportes disponibles: {', '.join(self.available_supports)}")

        return "\n".join(rows)
