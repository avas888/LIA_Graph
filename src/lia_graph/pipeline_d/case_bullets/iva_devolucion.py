"""v16 b3 — devolución de saldos a favor en IVA (art. 481 ET)."""
from __future__ import annotations

from ..case_detectors import is_iva_devolucion_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="iva_devolucion",
    detector=is_iva_devolucion_case,
    bullets=(
        "**Sujetos con derecho a devolución de IVA:** **exportadores** de bienes corporales muebles (art. 481 lit. a ET); **prestadores de servicios exentos** del art. 481 lit. c ET (servicios prestados en Colombia para uso exclusivo en el exterior, no turísticos); **productores de bienes exentos** del art. 477 ET (carne, pollo, leche, huevos); responsables con saldo a favor estructural por exceso de retenciones de IVA.",
        "**Plazo para solicitar:** **2 años** desde el vencimiento del plazo para declarar el bimestre/cuatrimestre que generó el saldo (art. 854 ET). Vencido, el saldo **prescribe** y no es recuperable.",
        "**Plazos DIAN para resolver (art. 855 ET):** **Ordinaria 50 días** desde radicación completa; **con garantía bancaria** o de compañía de seguros (110 % del valor, vigencia 2 años) **20 días**; **automática para exportadores** (Decreto 1422/2015) **15 días** cuando se cumplen los requisitos.",
        "**Modalidad automática — requisitos:** estar al día en obligaciones tributarias y aduaneras; ser **usuario aduanero permanente (UAP)** o estar inscrito en programas DIAN equivalentes; contar con **declaración de exportación (DEX)** trazable; información exógena conciliada; cumplir parámetros de riesgo definidos por la DIAN.",
        "**Documentos del expediente:** **Formulario 010** \"Solicitud de devolución/compensación\"; relación detallada de impuestos descontables (NIT proveedor, número de factura electrónica, CUFE); certificación de revisor fiscal o contador público; documentos de exportación (DEX, factura comercial, BL/AWB, certificado de origen); garantía si aplica.",
        "**Compensación con otras obligaciones:** el saldo a favor de IVA puede compensarse con **renta, retención en la fuente, IVA de otros bimestres, GMF, sanciones e intereses**. Mismo formulario 010 marcando \"compensación\".",
        "**Riesgo de devolución improcedente (art. 670 ET):** si la DIAN encuentra improcedente, sanciona con **10 %** del valor devuelto + intereses moratorios. Con dolo o documentos falsos: **100 %** + denuncia penal.",
    ),
    keywords=(
        "iva",
        "devolución", "devolucion",
        "saldo a favor", "saldos a favor",
        "compensación", "compensacion",
        "481", "477", "850", "854", "855", "857", "863", "670",
        "exportador", "exportadores",
        "productor de exentos",
        "50 días", "50 dias",
        "20 días", "20 dias",
        "15 días", "15 dias",
        "2 años", "dos años",
        "formulario 010",
        "garantía", "garantia",
        "garantía bancaria",
        "110%",
        "automática", "automatica",
        "uap", "usuario aduanero",
        "dex",
        "cufe", "factura electrónica", "factura electronica",
        "revisor fiscal",
        "decreto 1422",
        "10%", "100%",
    ),
    anchor_articles=("481",),
    search_queries=(
        "devolucion iva saldos favor exportadores art 481 et productor bienes exentos",
        "plazos dian devolucion iva 50 20 15 dias automatica garantia art 855 et",
    ),
    source_label="iva_devolucion_anchor",
)
