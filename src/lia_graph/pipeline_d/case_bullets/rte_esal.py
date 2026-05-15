"""v16 b5 — RTE para ESAL (art. 19 ET)."""
from __future__ import annotations

from ..case_detectors import is_rte_esal_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="rte_esal",
    detector=is_rte_esal_case,
    bullets=(
        "**Régimen Tributario Especial (art. 19 ET):** **ESAL** (asociaciones, fundaciones, corporaciones sin ánimo de lucro) calificadas en el RTE tributan al **20 %** sobre el beneficio neto o excedente fiscal (art. 356 ET), con **exención total** cuando se reinvierte en el objeto social en el año siguiente (art. 358 ET).",
        "**Requisitos para calificar (art. 19 ET):** legalmente constituida como **asociación, fundación o corporación sin ánimo de lucro**; objeto social en alguna de las **13 actividades meritorias** del art. 359 ET (educación, salud, cultura, ciencia y tecnología, desarrollo social, ambientales, derechos humanos, deporte aficionado, etc.); aportes **no reembolsables**; excedentes **no distribuibles**.",
        "**Solicitud anual de calificación o permanencia:** plazo **1 de enero a 30 de junio**; vía sistema **MUISCA**; documentos: acta de constitución, estatutos vigentes, certificados de actividades meritorias, estados financieros del AG previo firmados por contador/revisor fiscal, **memoria económica** si ingresos > **160.000 UVT** ($7.530.400.000 AG 2025). Publicación pública del registro web durante **10 días hábiles** para comentarios de terceros (art. 364-5 ET).",
        "**Exclusión automática:** si no solicita permanencia en plazo → **excluida del RTE** y tributa al régimen ordinario (**35 % PJ**) desde el AG en curso. Para volver a entrar: solicitar calificación nueva el año siguiente.",
        "**Determinación del beneficio neto o excedente (art. 357 ET):** ingresos del año − egresos procedentes (relacionados con el objeto social) − inversiones efectuadas en cumplimiento del objeto social = beneficio neto fiscal. **Exención (art. 358 ET):** el beneficio destinado al objeto social en el año siguiente, **por decisión de la asamblea**, queda **exento**. Decisión registrada en acta **antes del 31 de marzo**.",
        "**Distribución indirecta de excedentes — prohibición (art. 356-1 ET):** pagos a directivos/fundadores/asociados sobre valor de mercado; préstamos a directivos o asociados; compras a asociados sobre valor de mercado. Cualquiera de estos → **exclusión del RTE** + sanción.",
        "**Tip de planeación:** mantenga al día las **actas de asamblea que destinan el excedente al objeto social** — son la prueba de la exención. DIAN está revisando intensamente desde 2019 ESAL que reportan exención sin acta soporte. Para ingresos > 160.000 UVT, presentar **memoria económica** anual con detalle de actividades, beneficiarios, donaciones recibidas, contratos con vinculados (art. 356-3 ET).",
    ),
    keywords=(
        "rte",
        "régimen tributario especial", "regimen tributario especial",
        "esal",
        "fundación", "fundacion",
        "asociación", "asociacion",
        "corporación", "corporacion",
        "sin ánimo de lucro", "sin animo de lucro",
        "19", "19-4",
        "356", "356-1", "356-3",
        "357", "358", "359",
        "364-5",
        "beneficio neto", "excedente",
        "actividades meritorias",
        "objeto social",
        "20%", "20 %",
        "35%", "35 %",
        "calificación", "calificacion",
        "permanencia",
        "muisca",
        "memoria económica", "memoria economica",
        "160.000 uvt", "160000 uvt",
        "distribución indirecta", "distribucion indirecta",
        "decreto 2150 de 2017",
        "ley 1819",
        "ley 1819 de 2016",
        "31 de marzo", "31 marzo",
        "1 de enero", "30 de junio",
        "exención", "exencion", "exento", "exenta",
    ),
    anchor_articles=("19",),
    search_queries=(
        "regimen tributario especial esal art 19 et 20 por ciento beneficio neto",
        "calificacion permanencia rte enero junio actividades meritorias art 359 et",
    ),
    source_label="rte_esal_anchor",
)
