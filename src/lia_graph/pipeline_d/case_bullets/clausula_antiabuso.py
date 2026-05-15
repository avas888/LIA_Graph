"""v16 b5 — cláusula antiabuso (arts. 869, 869-1, 869-2 ET)."""
from __future__ import annotations

from ..case_detectors import is_clausula_antiabuso_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="clausula_antiabuso",
    detector=is_clausula_antiabuso_case,
    bullets=(
        "**Concepto de abuso (art. 869 ET):** uno o varios actos o negocios jurídicos **artificiosos** —que individual o en conjunto **carezcan de razón o propósito económico o comercial aparente, distinto al de obtener un provecho tributario**— utilizados para alterar, desfigurar o modificar artificialmente los efectos tributarios.",
        "**Provecho tributario incluye** (art. 869 ET): alteración/desfiguración/modificación de efectos tributarios; **eliminación, reducción o diferimiento del tributo**; incremento del saldo a favor o de pérdidas fiscales; extensión de beneficios o exenciones.",
        "**Supuestos para aplicación (art. 869-1 ET):** la operación es **abusiva** cuando concurren **tres o más** de estas características: operación entre **vinculados económicos**; uso de **paraísos fiscales** o jurisdicciones no cooperantes; involucra **entidades del RTE**, no contribuyentes o exentos; precio o remuneración **difiere notablemente del valor de mercado**; condiciones del negocio omiten una persona, acto, documento o cláusula material que no se habría omitido entre partes independientes.",
        "**Procedimiento (art. 869-2 ET):** **Comité de Fiscalización** de la DIAN (Director General, Director Fiscalización, Director Jurídico, Subdirector Normativa y Doctrina, Defensor del Contribuyente) evalúa la propuesta de recaracterización. Emplazamiento al contribuyente con **3 meses** para responder con pruebas. Aprobada → requerimiento especial o acto definitivo. Recursos: reconsideración (administrativo) y nulidad y restablecimiento (contencioso).",
        "**Efectos de la recaracterización:** desconocer la operación; recaracterizar conforme a su sustancia económica; liquidar mayor impuesto + sanciones (inexactitud art. 647 ET: **100 %** del mayor impuesto, **160 %** si involucra paraíso fiscal) + intereses moratorios.",
        "**Carga de la prueba:** **DIAN** demuestra artificiosidad y falta de propósito comercial aparente. **Contribuyente** acredita propósito comercial real (proyecciones financieras, planes de negocio, valoraciones independientes, actas de junta directiva motivadas, due diligence, contratos con terceros independientes).",
        "**Distinción con planeación legítima:** la planeación es **legítima** cuando elige la **alternativa menos gravosa entre opciones que la norma ofrece** y la operación tiene **sustancia económica real**. El abuso aparece cuando la **única razón verificable es el ahorro tributario** y los demás elementos son simulados. El umbral cuantitativo antiguo (192.000 UVT) **fue eliminado** por Ley 1819/2016 — hoy la cláusula aplica a cualquier monto.",
    ),
    keywords=(
        "cláusula antiabuso", "clausula antiabuso",
        "abuso",
        "abuso en materia tributaria",
        "abuso tributario",
        "recaracterización", "recaracterizacion", "recaracterizar",
        "869", "869-1", "869-2",
        "art. 869", "art 869",
        "gaar",
        "comité de fiscalización", "comite de fiscalizacion",
        "negocios artificiosos",
        "artificiosos",
        "propósito comercial", "proposito comercial",
        "propósito económico", "proposito economico",
        "planeación tributaria", "planeacion tributaria",
        "planeación legítima", "planeacion legitima",
        "vinculados económicos", "vinculados economicos",
        "paraísos fiscales", "paraisos fiscales",
        "jurisdicciones no cooperantes",
        "valor de mercado",
        "192.000 uvt",
        "ley 1607", "ley 1819", "ley 2010",
        "art. 647", "art 647",
        "100%", "160%",
        "consejo de estado",
        "sentencia 21037",
        "due diligence",
        "sustancia económica", "sustancia economica",
    ),
    anchor_articles=("869",),
    search_queries=(
        "clausula antiabuso art 869 869-1 869-2 et recaracterizacion dian",
        "comite fiscalizacion dian negocios artificiosos proposito comercial ley 1819",
    ),
    source_label="clausula_antiabuso_anchor",
)
