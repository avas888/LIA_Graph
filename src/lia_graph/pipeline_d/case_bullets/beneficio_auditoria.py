"""v16 (2026-05-14) — beneficio de auditoría (art. 689-3 ET)."""
from __future__ import annotations

from ..case_detectors import is_beneficio_auditoria_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="beneficio_auditoria",
    detector=is_beneficio_auditoria_case,
    bullets=(
        "El **art. 689-3 ET** permite que la declaración de renta quede en firme en **6 meses** (incremento del impuesto neto de renta ≥ **35 %**) o **12 meses** (incremento ≥ **25 %** y < 35 %) frente al AG anterior. Si el incremento es < 25 %, aplica la **firmeza ordinaria de 3 años** (art. 714 ET). Vigencia: **AG 2022 a AG 2026** (Ley 2277/2022 art. 51).",
        "**Cálculo:** la comparación se hace sobre el **impuesto neto de renta** (renglón del formulario 110 o 210), **no** sobre la renta líquida ni el impuesto a cargo. Tome el renglón del AG anterior y compárelo con el proyectado del AG actual.",
        "**Requisitos formales acumulativos:** (i) declaración presentada **dentro del plazo legal**, (ii) impuesto **pagado dentro del plazo** (no procede con acuerdo de pago que cruce el vencimiento), (iii) **no haber sido emplazado** para corregir antes de la firmeza, (iv) que la **declaración del AG anterior** esté presentada y en firme o cumpla los requisitos del beneficio.",
        "**Pérdidas fiscales bloquean el beneficio.** Si el contribuyente generó pérdida fiscal en el AG en curso o **compensa pérdidas anteriores (art. 147 ET)**, la firmeza es de **5 años** y NO aplica el art. 689-3 ET. Confirmado por jurisprudencia reiterada del Consejo de Estado.",
        "**RST excluido.** Los contribuyentes del Régimen Simple (arts. 903-916 ET) no acceden — su firmeza es propia del régimen.",
        "**No protege contra exógena ni IVA.** Solo opera sobre la declaración de renta. Información exógena, IVA, retenciones y demás obligaciones siguen su firmeza ordinaria. La DIAN puede iniciar revisión de esas obligaciones sin tocar la renta.",
        "**Documentación.** No hay marcación específica en el formulario 110 ni acto administrativo. La firmeza opera **de pleno derecho**. Conservar papel de trabajo con cálculo del incremento, constancia de presentación oportuna, recibo de pago en plazo y verificación de no emplazamiento.",
    ),
    keywords=(
        "beneficio de auditoría", "beneficio de auditoria",
        "beneficio auditoría", "beneficio auditoria",
        "689-3", "714", "147", "643",
        "firmeza", "firme",
        "6 meses", "12 meses",
        "35%", "25%",
        "impuesto neto",
        "ley 2155", "ley 2277",
        "ag 2022", "ag 2023", "ag 2024", "ag 2025", "ag 2026",
        "emplazamiento", "emplazado",
        "pérdida fiscal", "perdida fiscal",
        "pérdidas fiscales", "perdidas fiscales",
        "compensación", "compensacion",
        "acuerdo de pago",
        "rst", "régimen simple", "regimen simple",
        "exógena", "exogena",
        "iva",
        "renglón", "renglon",
    ),
    anchor_articles=("689-3",),
    search_queries=(
        "beneficio de auditoria firmeza reducida 6 12 meses art 689-3 et",
        "incremento 35 25 por ciento impuesto neto art 689-3 ley 2277 2022",
    ),
    source_label="beneficio_auditoria_anchor",
)
