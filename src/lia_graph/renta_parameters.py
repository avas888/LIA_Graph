from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_PARAMETERS_DIR = Path("knowledge_base/normativa/renta/tablas_parametros")


def load_renta_parameters(
    fiscal_year: int | None,
    parameters_dir: Path = DEFAULT_PARAMETERS_DIR,
) -> dict[str, Any] | None:
    if fiscal_year is None:
        return None

    target = parameters_dir / f"parametros_renta_{fiscal_year}.json"
    if not target.exists():
        return None

    return json.loads(target.read_text(encoding="utf-8"))


def summarize_renta_parameters(payload: dict[str, Any] | None, max_items: int = 6) -> str:
    if not payload:
        return "- Sin tabla de parametros anual cargada para el ano gravable indicado."

    year = payload.get("fiscal_year")
    params = payload.get("parameters", [])
    if not isinstance(params, list) or not params:
        return f"- Tabla anual {year}: sin parametros definidos."

    lines: list[str] = [f"- Tabla anual cargada: AG {year}"]
    for item in params[:max_items]:
        if not isinstance(item, dict):
            continue
        parameter_id = item.get("parameter_id", "unknown")
        value = item.get("value")
        unit = item.get("unit", "")
        status = item.get("validation_status", "pending_validation")
        source = item.get("source_authority", "unknown")
        lines.append(
            f"- {parameter_id}={value} {unit} | estado={status} | fuente={source}"
        )

    return "\n".join(lines)
