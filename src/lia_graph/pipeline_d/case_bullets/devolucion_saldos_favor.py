"""v16 (2026-05-14) — devolución de saldos a favor (art. 850 ET)."""
from __future__ import annotations

from ..case_detectors import is_devolucion_saldos_favor_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="devolucion_saldos_favor",
    detector=is_devolucion_saldos_favor_case,
    bullets=(
        "El **saldo a favor** de la declaración de renta puede solicitarse en **devolución** o **compensación** dentro de los **2 años** siguientes al vencimiento (art. 854 ET). Vencido este término, el saldo prescribe y no es recuperable.",
        "**Modalidades y plazos DIAN para resolver (art. 855 ET):** **devolución ordinaria 50 días**; **devolución con garantía bancaria o de compañía de seguros** (110 % del saldo, vigencia 2 años) **20 días**; **devolución automática** (Res. DIAN 000151 de 2012) **15 días** — aplica a contribuyentes con cumplimiento alto en exógena, IVA, retención y parámetros DIAN.",
        "**Compensación:** el saldo se aplica al pago de otras obligaciones (renta del año siguiente, IVA, retención, autorretención). La compensación se hace por orden cronológico de exigibilidad. Misma solicitud, modalidad \"compensación\" en el formulario 010.",
        "**Documentos del expediente:** **Formulario 010** \"Solicitud de devolución/compensación\"; relación detallada de retenciones (NIT del agente retenedor + certificados); relación de anticipos pagados; estados financieros (si aplica); garantía (si modalidad con garantía); poder vigente si actúa apoderado.",
        "**Intereses (art. 863 ET):** **A favor del contribuyente** — si la DIAN se demora más allá del plazo legal, paga intereses corrientes (DTF) desde la radicación; si la mora se prolonga, intereses moratorios (tasa del art. 635 ET) desde la ejecutoria del acto. **A favor de la DIAN** — devolución improcedente se reintegra con intereses moratorios desde la fecha de recibo.",
        "**Causales típicas de rechazo o inadmisión (art. 857 ET):** solicitud extemporánea; saldo inexistente o ya devuelto; **inconsistencias con exógena** (la primera causa de inadmisión en la práctica); falta de soportes de retención; procesos de fiscalización abiertos sobre la misma declaración.",
        "**Riesgo de devolución improcedente — sanción art. 670 ET:** si la DIAN encuentra improcedente la devolución, sanciona con **10 % del valor devuelto** + intereses moratorios. Si hubo dolo o documentos falsos, **100 %** + denuncia penal.",
    ),
    keywords=(
        "devolución", "devolucion",
        "devoluciones",
        "saldo a favor", "saldos a favor",
        "compensación", "compensacion", "compensar",
        "850", "854", "855", "857", "863", "670", "635",
        "50 días", "50 dias",
        "20 días", "20 dias",
        "15 días", "15 dias",
        "2 años", "dos años", "dos anos",
        "formulario 010",
        "garantía bancaria", "garantia bancaria",
        "garantía", "garantia",
        "devolución automática", "devolucion automatica",
        "exógena", "exogena",
        "intereses corrientes",
        "intereses moratorios",
        "improcedente",
        "retención", "retencion",
        "certificado de retención", "certificado de retencion",
        "agente retenedor",
        "anticipo", "anticipos",
        "res. dian 000151",
        "dur 1625",
    ),
    anchor_articles=("850",),
    search_queries=(
        "devolucion compensacion saldos a favor renta art 850 et 2 anos",
        "plazos dian devolucion ordinaria automatica garantia art 855 et",
    ),
    source_label="devolucion_saldos_favor_anchor",
)
