"""v16 (2026-05-14) — bancarización / pagos en efectivo (art. 771-5 ET).

Bullet content grounded in:
  * docs/expert_briefs/incoming/playbook_renta_limitacion_pagos_efectivo.md
  * knowledge_base/CORE ya Arriba/RENTA/PLAYBOOKS/playbook_renta_limitacion_pagos_efectivo.md
"""
from __future__ import annotations

from ..case_detectors import is_pagos_efectivo_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="pagos_efectivo",
    detector=is_pagos_efectivo_case,
    bullets=(
        "El **art. 771-5 ET (bancarización)** restringe el reconocimiento fiscal de costos, deducciones, pasivos e impuestos descontables pagados en efectivo. **El efectivo NO es medio bancarizado** para estos efectos.",
        "**Medios de pago bancarizados aceptados (art. 771-5 inciso 1):** depósitos en cuentas bancarias, giros y transferencias, cheques al primer beneficiario con cláusula 'no negociable', tarjetas de crédito/débito/bonos electrónicos, otros medios autorizados por el Gobierno.",
        "**Regla general AG 2025 (Ley 2277/2022 art. 66):** los pagos en efectivo se aceptan hasta el **menor entre dos topes** — el **35%** de los pagos en efectivo del año, o el **40%** de los costos y deducciones totales. El exceso **no es deducible** y no genera IVA descontable.",
        "**Tope individual:** los pagos individuales que excedan de **100 UVT** (UVT 2025 $47.065 → **$4.706.500**) deben canalizarse por medios bancarizados para ser reconocidos fiscalmente. Pago en efectivo sobre ese umbral = rechazo total del pago.",
        "**Pago a tercero distinto del proveedor:** el pago debe ir al beneficiario titular de la factura. Pagar a la cuenta personal del socio del proveedor o a un familiar **no se considera bancarizado** — riesgo de rechazo. Mantén nombre del beneficiario, cuenta receptora y comprobante.",
        "**Cómo aplicar el cálculo:** suma todos los pagos en efectivo del AG; suma costos y deducciones totales; calcula el menor entre 35% de pagos efectivo y 40% de costos y deducciones; si los pagos en efectivo superan ese límite, ajusta el exceso como **no deducible** en F2516 (diferencia permanente).",
        "**Soporte obligatorio:** extracto bancario o comprobante de transferencia + factura electrónica con identificación del beneficiario + conciliación por proveedor cuando hay múltiples pagos. Sin estos soportes la deducción es objetable aunque el pago haya sido bancarizado.",
    ),
    keywords=(
        "bancarización", "bancarizacion", "bancarizar", "bancarizado",
        "efectivo", "pagos en efectivo", "pago en efectivo",
        "medios de pago", "medio de pago",
        "771-5",
        "35%", "40%", "35 %", "40 %",
        "100 uvt", "100uvt",
        "transferencia", "transferencias",
        "consignación", "consignacion",
        "cheque", "cheques",
        "tarjeta", "tarjetas",
        "deducir", "deducible", "deducción", "deduccion",
        "depuración", "depuracion",
        "renglón", "renglon",
        "iva descontable",
        "f2516", "2516",
        "diferencia permanente",
        "ley 2277",
        "tope", "límite", "limite",
        "no negociable",
        "primer beneficiario",
        "extracto bancario",
    ),
    anchor_articles=("771-5",),
    search_queries=(
        "bancarizacion pagos en efectivo art 771-5 et medios de pago",
        "limitacion 35 40 porciento pagos efectivo costos deducciones ley 2277 art 66",
    ),
    source_label="pagos_efectivo_anchor",
)
