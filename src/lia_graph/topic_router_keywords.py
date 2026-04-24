"""Keyword + regex data for topic routing.

Extracted from `topic_router.py` during granularize-v2 round 11 to
graduate the host below 1000 LOC. ~637 LOC of pure data lived inline:

  * ``_TOPIC_KEYWORDS`` — per-topic ``strong`` / ``weak`` keyword
    buckets used by ``_score_topic_keywords``. At runtime
    ``register_topic_keywords`` in the host may add custom-corpus
    entries to this dict; because ``from … import`` binds the same
    dict object, mutations are visible to both modules.
  * ``_TOPIC_NOTICE_OVERRIDES`` — per-topic user-facing notice strings
    shown when a detected topic overrides the user's requested topic.
  * ``_SUBTOPIC_OVERRIDE_PATTERNS`` — regex-plus-keywords tuples that
    detect narrow sub-topic intent in natural-language messages. Runs
    BEFORE keyword scoring so dedicated child corpora (GMF, consumo,
    patrimonio fiscal, costos_deducciones_renta, laboral-colloquial)
    win over the broader ``declaracion_renta`` parent.

All of these are consumed only inside `topic_router` today; keeping
them here means changes to the heuristic vocabulary land in a
self-contained file instead of the 600-LOC host.

Weak-bucket design rule
-----------------------
Weak entries must be topic-**characteristic** on their own. A bare
term that is topic-**dominant** but also appears in other domains
(``liquidación`` — labor-dominant, but also means DIAN audit
liquidation, company dissolution, tax self-assessment, contract
settlement; ``prima`` — labor-dominant, but also means equity
colocación premium or insurance premium) does NOT belong in ``weak``.
Two valid relocations:

  * Promote to ``strong`` as a compound phrase (``prima de servicios``,
    ``liquidación de nómina``) — the scorer's ``\\b…\\b`` boundary
    matches compounds as a single unit.
  * Move to ``_SUBTOPIC_OVERRIDE_PATTERNS`` as a proximity regex (the
    laboral-colloquial override already demonstrates this pattern:
    ``\\bliquid\\w*\\b[^.?!]{0,30}\\b(?:emplead[oa]|trabajador[ae]|…)``).

See ``docs/next/structuralwork_v1_SEENOW.md`` (backlog item A) for the
full rationale, the list of terms already migrated, and the "Tough
calls" section listing polysemous-but-labor-dominant terms that remain
in ``weak`` pending adversarial evidence.
"""

from __future__ import annotations

import re


_TOPIC_KEYWORDS: dict[str, dict[str, tuple[str, ...]]] = {
    "laboral": {
        "strong": (
            "seguridad social",
            "fondo de solidaridad pensional",
            "fondo solidaridad pensional",
            "contribución fondo solidaridad pensional",
            "contribucion fondo solidaridad pensional",
            "aporte fondo solidaridad pensional",
            "trabajadores por horas",
            "trabajador por horas",
            "prestaciones sociales",
            "parafiscales",
            "riesgos laborales",
            "salud y pension",
            "salud y pensión",
            "salud y seguridad social",
            "eps",
            "arl",
            "pila",
            "ibc",
            "nomina",
            "nómina",
            # --- sinónimos nuevos ---
            "nómina electrónica",
            "nomina electronica",
            "ugpp",
            "sst",
            "copasst",
            "salario integral",
            "salario mínimo",
            "smmlv",
            "contrato de trabajo",
            "contrato a término fijo",
            "contrato a término indefinido",
            "contrato de prestación de servicios",
            "liquidación de contrato",
            "despido",
            "indemnización por despido",
            # --- nómina electrónica troubleshooting ---
            "error nomina electronica",
            "error nómina electrónica",
            "ajuste nomina electronica",
            "ajuste nómina electrónica",
            "nota ajuste nómina",
            "nota ajuste nomina",
            "rechazo nomina electronica",
            "rechazo nómina electrónica",
            # --- reforma laboral ---
            "reforma laboral",
            "ley 2466",
            # --- aliases web research ---
            "planilla pila",
            "planilla integrada",
            "liquidación de nómina",
            "liquidacion de nomina",
            "liquidación de prestaciones",
            "liquidacion de prestaciones",
            "aportes seguridad social",
            "contrato obra labor",
            "contrato por horas",
            # --- colloquial part-time / liquidation phrasings ---
            "tiempo parcial",
            "media jornada",
            "medio tiempo",
            "jornada parcial",
            "empleada temporal",
            "empleado temporal",
            "trabajador temporal",
            "trabajadora temporal",
            "trabaja por horas",
        ),
        "weak": (
            # NOTE: see the module-level "Weak-bucket design rule" docstring
            # above. Removed polysemous bare entries (backlog item A —
            # docs/next/structuralwork_v1_SEENOW.md):
            #   - "liquidar" / "liquidacion" / "liquidación": DIAN liquidación
            #     oficial, liquidación de sociedad, liquidación de contrato
            #     civil, liquidación privada. Compound labor forms survive in
            #     strong ("liquidación de nómina/contrato/prestaciones") and
            #     the laboral _SUBTOPIC_OVERRIDE_PATTERNS regex still catches
            #     liquidar+empleado within 30 chars.
            #   - "prima": prima en colocación de acciones (societario), prima
            #     de seguros. Compound "prima de servicios" stays in weak
            #     below.
            #   - "aportes" / "aportaciones": aportes de capital (societario),
            #     aportes a fondos de inversión. Compound "aportes seguridad
            #     social" / "aportes en línea" stay in weak below; strong
            #     list covers "parafiscales".
            #   - "planilla": planilla de cálculo genérica. Compounds
            #     "planilla pila", "planilla integrada" stay in strong; "mi
            #     planilla" stays in weak.
            #   - "bonificación": bonificación comercial / fiscal. No compound
            #     kept — labor queries about bonificaciones typically arrive
            #     with empleado/trabajador context, caught by the override
            #     regex.
            # Kept-as-weak polysemous terms (salud, pensión, cotización,
            # dotación) are tracked in docs/next/structuralwork_v1_SEENOW.md
            # under "Tough calls" with the criterion for promoting them later.
            "trabajador",
            "trabajadores",
            "salud",
            "pension",
            "pensión",
            "cesantias",
            "cesantías",
            "vacaciones",
            "contrato laboral",
            # --- sinónimos nuevos ---
            "horas extras",
            "recargo nocturno",
            "dotación",
            "auxilio de transporte",
            "prima de servicios",
            "intereses cesantías",
            "incapacidad",
            "licencia de maternidad",
            "licencia de paternidad",
            "cotización",
            "fondo de cesantías",
            "fondo de pensiones",
            "caja de compensación",
            "sena",
            "icbf",
            "jornada laboral",
            "período de prueba",
            # --- cross-domain weak signals ---
            "prestaciones sociales niif",
            "pasivo laboral niif",
            "beneficios empleados niif",
            # --- aliases web research ---
            "despido sin justa causa",
            "despido con justa causa",
            "estabilidad laboral reforzada",
            "fuero de maternidad",
            "liquidación definitiva",
            "liquidacion definitiva",
            "recargo dominical",
            "jornada máxima legal",
            "jornada maxima legal",
            "soi",
            "mi planilla",
            "aportes en línea",
            "aportes en linea",
        ),
    },
    "facturacion_electronica": {
        "strong": (
            "factura electronica",
            "factura electrónica",
            "facturacion electronica",
            "facturación electrónica",
            "documento soporte",
            "documento equivalente",
            "radian",
            # --- sinónimos nuevos ---
            "cufe",
            "cude",
            "nota crédito electrónica",
            "nota débito electrónica",
            "proveedor tecnológico",
            "resolución de facturación",
            "habilitación facturación",
            "documento soporte de pago",
            "factura de venta",
            "pos electrónico",
            "tiquete pos",
            # --- aliases web research ---
            "sistema de facturación electrónica",
            "sistema de facturacion electronica",
            "factura electrónica de venta",
            "factura electronica de venta",
            "documento soporte no obligado a facturar",
            "dse",
        ),
        "weak": (
            "factura",
            "facturacion",
            "facturación",
            "soporte fiscal",
            "nomina electronica",
            "nómina electrónica",
            # --- sinónimos nuevos ---
            "validación previa",
            "acuse de recibo",
            "título valor electrónico",
            "rechazo comercial",
            "factura de exportación",
            "contingencia facturación",
            "set de pruebas dian",
            "mandato facturación",
            "código qr factura",
            # --- aliases web research ---
            "facturación gratuita dian",
            "facturacion gratuita dian",
            "solución gratuita facturación",
            "solucion gratuita facturacion",
            "resolución de numeración",
            "resolucion de numeracion",
            "rango de numeración",
            "rango de numeracion",
            "xml factura",
            "eventos factura electrónica",
            "eventos factura electronica",
            "facturador electrónico",
            "facturador electronico",
        ),
    },
    "iva": {
        "strong": (
            "iva",
            "impuesto al valor agregado",
            "declaracion de iva",
            "declaración de iva",
            "responsable de iva",
            # --- sinónimos nuevos ---
            "formulario 300",
            "no responsable de iva",
            "iva descontable",
            "iva generado",
            "bienes excluidos",
            "bienes exentos",
            "bienes gravados",
            "tarifa de iva",
            "iva del 19",
            "iva del 5",
            "régimen común",
            "hecho generador iva",
            # --- aliases web research ---
            "impuesto a las ventas",
            "declaración bimestral iva",
            "declaracion bimestral iva",
            "declaración cuatrimestral iva",
            "declaracion cuatrimestral iva",
        ),
        "weak": (
            "bimestral",
            "cuatrimestral",
            "saldo a favor iva",
            # --- sinónimos nuevos ---
            "reteiva",
            "base gravable iva",
            "devolución iva",
            "proporcionalidad iva",
            "iva teórico",
            "iva asumido",
            "impuesto sobre las ventas",
            "servicios excluidos",
            "servicios exentos",
            "iva en importaciones",
            # --- aliases web research ---
            "régimen simplificado",
            "regimen simplificado",
            "aiu iva",
            "impuesto nacional al consumo",
            "impuestos descontables",
            "declaración sugerida iva",
            "declaracion sugerida iva",
        ),
    },
    "ica": {
        "strong": (
            "ica",
            "industria y comercio",
            "impuesto de industria y comercio",
            # --- sinónimos nuevos (reteica promovido de weak) ---
            "reteica",
            "avisos y tableros",
            "declaración de ica",
            "sobretasa bomberil",
            "tarifa ica",
            # --- aliases web research ---
            "impuesto ica",
            "ica bogotá",
            "ica bogota",
            "impuesto avisos y tableros",
        ),
        "weak": (
            # --- sinónimos nuevos ---
            "tarifa por mil",
            "territorialidad ica",
            "base gravable ica",
            "ica distrital",
            "ica municipal",
            "retención ica",
            "impuesto complementario",
            # --- aliases web research ---
            "descuento ica en renta",
            "declaración ica bimestral",
            "declaracion ica bimestral",
            "declaración ica anual",
            "declaracion ica anual",
            "actividades gravadas ica",
            "actividades excluidas ica",
            "ciiu ica",
        ),
    },
    "estados_financieros_niif": {
        "strong": (
            "niif",
            "ifrs",
            "estados financieros",
            "estado de resultados",
            "estado de situacion financiera",
            "estado de situación financiera",
            # --- sinónimos nuevos ---
            "niif plenas",
            "niif pymes",
            "niif grupo 1",
            "niif grupo 2",
            "niif grupo 3",
            "ctcp",
            "normas internacionales de contabilidad",
            "nic",
            "cierre contable",
            "impuesto diferido",
            "propiedad planta y equipo",
            "valor razonable",
            "deterioro de activos",
            "instrumentos financieros",
            # --- NIIF PYMES tercera edición ---
            "niif pymes tercera edicion",
            "niif pymes tercera edición",
            "ifrs for smes",
            "tercera edición niif pymes",
            "marco normativo grupo 2",
            # --- depreciación/amortización cross-domain ---
            "depreciación fiscal vs niif",
            "depreciacion fiscal vs niif",
            # --- aliases web research ---
            "nic 1",
            "nic 12",
            "nic 16",
            "nic 2",
            "nic 19",
        ),
        "weak": (
            "balance",
            "balance general",
            "revelaciones",
            "notas a los estados financieros",
            # --- sinónimos nuevos ---
            "activos biológicos",
            "arrendamientos niif 16",
            "ingresos ordinarios niif 15",
            "costo amortizado",
            "provisión",
            "provisiones",
            "pasivos contingentes",
            "intangibles",
            "plusvalía",
            "consolidación de estados financieros",
            "inventarios niif",
            "flujo de efectivo",
            "estado de flujos de efectivo",
            "otro resultado integral",
            "ori",
            "políticas contables",
            # --- aliases web research ---
            "decreto 2420",
            "marco técnico normativo",
            "marco tecnico normativo",
            "ley 1314",
            "diferencias temporarias",
            "activo por impuesto diferido",
            "pasivo por impuesto diferido",
            "niif 9",
            "niif 15",
            "niif 16",
            "decreto 2649",
        ),
    },
    "calendario_obligaciones": {
        "strong": (
            "calendario tributario",
            "fecha limite",
            "fecha límite",
            "vencimiento",
            "vencimientos",
            "vencen",
            # --- sinónimos nuevos ---
            "cuando vence",
            "plazos dian",
            "último dígito nit",
            "último dígito",
            "fechas de vencimiento",
            "calendario dian",
            "fechas tributarias",
            # --- aliases web research ---
            "calendario tributario 2026",
            "calendario dian 2026",
            "plazos para declarar",
            "vencimientos 2026",
        ),
        "weak": (
            "plazo",
            "cronograma",
            "obligaciones",
            "fecha de presentacion",
            "fecha de presentación",
            # --- sinónimos nuevos ---
            "sanción por extemporaneidad",
            "extemporánea",
            "presentación tardía",
            "declaración tardía",
            "plazos renta",
            "plazos iva",
            "plazos retención",
            "plazos exógena",
            "cuando debo presentar",
            "fecha de pago",
            # --- aliases web research ---
            "plazos grandes contribuyentes",
            "plazos personas naturales",
            "plazos personas jurídicas",
            "plazos personas juridicas",
            "cuando se presenta la renta",
            "cuando se declara",
        ),
    },
    "declaracion_renta": {
        "strong": (
            "declaracion de renta",
            "declaración de renta",
            "formulario 110",
            "formulario 210",
            "impuesto de renta",
            "impuesto sobre la renta",
            "planeacion tributaria",
            "planeación tributaria",
            "planeacion tributaria legitima",
            "planeación tributaria legítima",
            "abuso en materia tributaria",
            "clausula general antielusion",
            "cláusula general antielusión",
            "clausula antielusion",
            "cláusula antielusión",
            # TTD / tasa mínima
            "tributacion depurada",
            "tributación depurada",
            "tasa de tributacion depurada",
            "tasa de tributación depurada",
            "tasa minima de tributacion",
            "tasa mínima de tributación",
            "ttd",
            "utilidad depurada",
            # Core renta concepts
            "renta liquida",
            "renta líquida",
            "renta presuntiva",
            "beneficio de auditoria",
            "beneficio de auditoría",
            # Loss compensation
            "compensacion de perdidas",
            "compensación de pérdidas",
            # --- sinónimos nuevos ---
            "ganancia ocasional",
            # conciliación fiscal, formato 2516/2517 → owned by conciliacion_fiscal corpus
            # costos y deducciones renta → owned by costos_deducciones_renta corpus
            "cédula general",
            "obligados a declarar",
            "topes para declarar",
            "renta cedular",
            "ingreso no constitutivo",
            "renta exenta",
            "rentas de trabajo",
            "rentas de capital",
            # --- aliases web research ---
            "depuración de renta",
            "depuracion de renta",
            "renta ordinaria",
            "renta personas naturales",
            "renta personas jurídicas",
            "renta personas juridicas",
        ),
        "weak": (
            "renta",
            "uvt",
            "depuracion",
            "depuración",
            # "deduccion"/"deducción" removed — too generic, pulls child-topic queries
            # "estatuto tributario" removed — matches nearly everything
            # "tributacion"/"tributación" removed — too generic
            # Broader renta signals
            "depurada",
            "tarifa general",
            "tarifa efectiva",
            "diferencias permanentes",
            "impuesto adicional",
            "anticipo",
            "utilidad contable",
            "elusion",
            "elusión",
            "simulacion",
            "simulación",
            # "declaración"/"declaracion" removed — too generic, assimilates unrelated queries
            # Loss compensation / pérdidas fiscales
            "perdida fiscal",
            "pérdida fiscal",
            "perdidas fiscales",
            "pérdidas fiscales",
            # --- sinónimos nuevos ---
            "límite de beneficios",
            "descuento tributario",
            # conciliación contable fiscal → owned by conciliacion_fiscal corpus
            "renta gravable",
            # --- aliases web research ---
            "renta complementarios",
            "grandes contribuyentes",
            "gran contribuyente",
            "anticipo de renta",
            "provisión impuesto renta",
            "provision impuesto renta",
            "declaración sugerida",
            "declaracion sugerida",
            "rentas no laborales",
            "cédula de pensiones",
            "cedula de pensiones",
            "cédula de dividendos",
            "cedula de dividendos",
            "ingresos no constitutivos",
        ),
    },
    "procedimiento_tributario": {
        "strong": (
            # --- devoluciones / saldos a favor face ---
            "devolucion de saldos a favor",
            "devolución de saldos a favor",
            "solicitud de devolucion",
            "solicitud de devolución",
            "saldo a favor",
            "auto inadmisorio",
            "devolucion improcedente",
            "devolución improcedente",
            "devolucion con garantia",
            "devolución con garantía",
            "compensacion tributaria",
            "compensación tributaria",
            # --- fiscalización / audit-procedure face (actos administrativos DIAN) ---
            "requerimiento ordinario",
            "requerimiento especial",
            "emplazamiento para declarar",
            "emplazamiento para corregir",
            "liquidacion oficial",
            "liquidación oficial",
            "liquidacion de revision",
            "liquidación de revisión",
            "liquidacion de aforo",
            "liquidación de aforo",
            "recurso de reconsideracion",
            "recurso de reconsideración",
            "pliego de cargos",
            "auto de archivo",
            "inspeccion tributaria",
            "inspección tributaria",
        ),
        "weak": (
            "devolucion",
            "devolución",
            "compensacion",
            "compensación",
            "procedimiento",
            "tramite",
            "trámite",
            "radicar",
            "radicacion",
            "radicación",
            "radicarse",
            "requisitos",
            "plazo",
            "plazos",
            "firmeza",
            "correccion de declaracion",
            "corrección de declaración",
            # --- fiscalización / audit-procedure face ---
            "requerimiento",
            "emplazamiento",
            "fiscalizacion",
            "fiscalización",
            "acto administrativo",
        ),
    },
    # Backlog item C step 3 — model entry for populating daily-traffic
    # topics that today sit at 0/0 keywords. Shape:
    #   - strong: multi-word domain-specific phrases, canonical ET/DIAN
    #     vocabulary, compound forms that unambiguously fire on this topic.
    #   - weak: bare terms that are topic-characteristic on their own (pass
    #     the weak-bucket design rule above). Avoid polysemous bare terms;
    #     if a term is domain-dominant but polysemous, lift it to a strong
    #     compound instead.
    # Replicate this shape across: informacion_exogena, ganancia_ocasional,
    # regimen_simple, and the other 40+ unregistered topics flagged in
    # docs/next/structuralwork_v1_SEENOW.md Part 1 item C.
    "retencion_en_la_fuente": {
        "strong": (
            "retencion en la fuente",
            "retención en la fuente",
            "retefuente",
            "reteiva",
            "reteica",
            "agente retenedor",
            "agente de retencion",
            "agente de retención",
            "certificado de retencion",
            "certificado de retención",
            "autorretenedor",
            "autorretencion",
            "autorretención",
            "practicar retencion",
            "practicar retención",
            "tarifa de retencion",
            "tarifa de retención",
            "base de retencion",
            "base de retención",
            "retencion asumida",
            "retención asumida",
            "retencion trasladable",
            "retención trasladable",
            "declaracion de retencion",
            "declaración de retención",
            "exonerado de retencion",
            "exonerado de retención",
            "no sujeto a retencion",
            "no sujeto a retención",
            # --- ET article anchors for retención en la fuente ---
            "articulo 383",
            "artículo 383",
            "articulo 388",
            "artículo 388",
            "articulo 408",
            "artículo 408",
            "articulo 437",
            "artículo 437",
        ),
        "weak": (
            "retenedor",
            "retenedores",
            "retencion",
            "retención",
            "retenciones",
            "base minima",
            "base mínima",
            "tarifa minima",
            "tarifa mínima",
            "rete",
            "dian",
        ),
    },
    # ---- Structural backlog v2 item V2-1: empty-topic keyword coverage -----
    # Populates the 9 gold-touching topics that had no registered keywords
    # and were therefore falling through to `effective_topic=None` (which
    # now triggers `topic_safety_abstention`). Entries below are the
    # unambiguous strong/weak vocabulary — derived from gold queries and
    # Colombian tax/compliance domain knowledge. Long-tail synonyms are
    # pending accountant review via the mining-script workflow
    # (`scripts/mine_topic_keywords.py`). See docs/next/structuralwork_v2.md
    # §V2-1 and the v5.4 change-log row in structuralwork_v1_SEENOW.md.
    "regimen_simple": {
        "strong": (
            "rst",
            "régimen simple",
            "regimen simple",
            "régimen simple de tributación",
            "regimen simple de tributacion",
            "impuesto unificado simple",
            "impuesto unificado bajo el régimen simple",
            "formulario 260",
            "formulario 2593",
            "anticipo bimestral simple",
            "anticipos bimestrales simple",
            "anticipos bimestrales rst",
            "inscripción al rst",
            "inscripcion al rst",
            "sujetos pasivos rst",
            "tarifa consolidada simple",
            "grupo 1 simple",
            "grupo 2 simple",
            "grupo 3 simple",
            "grupo 4 simple",
            "grupo 5 simple",
        ),
        "weak": (
            "simple tributario",
            "tarifa consolidada",
            "sac simple",
            "umbral simple",
            "elegibilidad rst",
            "retiro rst",
        ),
    },
    "impuesto_patrimonio_personas_naturales": {
        "strong": (
            "impuesto al patrimonio",
            "impuesto a la riqueza",
            "patrimonio líquido",
            "patrimonio liquido",
            "declaración de patrimonio",
            "declaracion de patrimonio",
            "art. 292-1",
            "art. 292-3",
            "art. 295-3",
            "art. 297-2",
            "sujetos impuesto al patrimonio",
            "tarifa impuesto al patrimonio",
            "umbral impuesto al patrimonio",
        ),
        "weak": (
            "patrimonio bruto",
            "umbral 72000 uvt",
            "patrimonio gravable",
            "valoración acciones patrimonio",
            "declarantes patrimonio",
        ),
    },
    "sagrilaft_ptee": {
        "strong": (
            "sagrilaft",
            "ptee",
            "autocontrol laft",
            "lavado de activos",
            "financiación del terrorismo",
            "financiacion del terrorismo",
            "programa de transparencia y ética empresarial",
            "programa de transparencia y etica empresarial",
            "transparencia y ética empresarial",
            "transparencia y etica empresarial",
            "beneficiario final laft",
            "circular básica jurídica",
            "circular basica juridica",
            "oficial de cumplimiento",
            "supersociedades laft",
        ),
        "weak": (
            "riesgo laft",
            "debida diligencia reforzada",
            "reporte sospechoso",
            "operación sospechosa",
            "umbral sagrilaft",
            "umbral ptee",
            "política de cumplimiento",
        ),
    },
    "zonas_francas": {
        "strong": (
            "zona franca",
            "zonas francas",
            "zomac",
            "zese",
            "usuario industrial zona franca",
            "usuario comercial zona franca",
            "usuario operador zona franca",
            "tarifa zona franca",
            "beneficio zomac",
            "municipio zomac",
            "decreto 1650",
            "decreto 957 de 2019",
            "ley 1819 art 235",
            "ley 1819 art 236",
            "ley 1819 art 237",
            "ley 1819 art 238",
        ),
        "weak": (
            "extraterritorialidad aduanera",
            "tarifa progresiva zomac",
            "cupo zese",
            "requisitos zomac",
            "incentivos zomac",
        ),
    },
    "obligaciones_profesionales_contador": {
        "strong": (
            "firma del contador",
            "firma contador público",
            "firma contador publico",
            "revisor fiscal",
            "ley 43 de 1990",
            "ley 43",
            "junta central de contadores",
            "jcc contador",
            "dictamen del revisor fiscal",
            "papeles de trabajo",
            "código de ética contador",
            "codigo de etica contador",
            "secreto profesional contador",
            "responsabilidad del contador",
            "responsabilidad del revisor fiscal",
            "art. 658-1",
            "art. 581",
            "art. 596",
            "art. 597",
        ),
        "weak": (
            "certifico contador",
            "sanción al contador",
            "sancion al contador",
            "contador revisor",
            "responsabilidad solidaria contador",
            "suspensión tarjeta profesional",
        ),
    },
    "informacion_exogena": {
        "strong": (
            "información exógena",
            "informacion exogena",
            "medios magnéticos",
            "medios magneticos",
            "resolución dian 000233",
            "resolucion dian 000233",
            "formato 1001",
            "formato 1005",
            "formato 1007",
            "formato 1008",
            "formato 1009",
            "formato 1011",
            "formato 1012",
            "formato 1647",
            "formato 2275",
            "formato 2276",
            "reporte exógena",
            "reporte exogena",
            "obligados a reportar exógena",
            "obligados a reportar exogena",
        ),
        "weak": (
            "umbral exógena",
            "umbral exogena",
            "sanción 651",
            "sancion 651",
            "corrección exógena",
            "correccion exogena",
            "reporte anual exógena",
            "reporte anual exogena",
        ),
    },
    "perdidas_fiscales_art147": {
        "strong": (
            "pérdidas fiscales",
            "perdidas fiscales",
            "compensación de pérdidas",
            "compensacion de perdidas",
            "art. 147 et",
            "articulo 147 et",
            "artículo 147 et",
            "pérdida líquida",
            "perdida liquida",
            "pérdida fiscal acumulada",
            "perdida fiscal acumulada",
            "ajuste pérdidas fiscales",
            "ajuste perdidas fiscales",
        ),
        "weak": (
            "firmeza pérdidas",
            "firmeza perdidas",
            "término pérdidas fiscales",
            "termino perdidas fiscales",
            "reajuste fiscal pérdidas",
            "reajuste fiscal perdidas",
            "compensar pérdida",
            "compensar perdida",
        ),
    },
    "dividendos_utilidades": {
        "strong": (
            "dividendos",
            "distribución de dividendos",
            "distribucion de dividendos",
            "retención sobre dividendos",
            "retencion sobre dividendos",
            "art. 242 et",
            "art. 242-1",
            "art. 245 et",
            "art. 246 et",
            "depuración de dividendos",
            "depuracion de dividendos",
            "dividendos gravados",
            "dividendos no gravados",
            "utilidades gravadas",
            "art. 49 et",
            "tarifa dividendos",
            "dividendos socios personas naturales",
        ),
        "weak": (
            "abono en cuenta dividendos",
            "cuenta 2505",
            "tarifa marginal dividendos",
            "reparto utilidades",
            "utilidades distribuidas",
        ),
    },
    "regimen_sancionatorio": {
        "strong": (
            "régimen sancionatorio",
            "regimen sancionatorio",
            "sanción por extemporaneidad",
            "sancion por extemporaneidad",
            "sanción tributaria",
            "sancion tributaria",
            "art. 641",
            "art. 640",
            "art. 644",
            "art. 647",
            "art. 651",
            "sanción por inexactitud",
            "sancion por inexactitud",
            "reducción de sanciones",
            "reduccion de sanciones",
            "sanción mínima",
            "sancion minima",
            "sanción por corrección",
            "sancion por correccion",
        ),
        "weak": (
            "multa tributaria",
            "graduación de sanciones",
            "graduacion de sanciones",
            "reincidencia dian",
            "gradualidad sanciones",
        ),
    },
    "gravamen_movimiento_financiero_4x1000": {
        "strong": (
            "gravamen movimiento financiero 4x1000",
            "gmf 4x1000",
            "gmf",
            "cuatro por mil",
            "gravamen movimiento financiero",
            "4x1000",
            "cuenta exenta gmf",
        ),
        "weak": (
            "gravamen",
            "movimiento",
            "financiero",
            "cuatro",
            "cuenta",
        ),
    },
    # ── v5 Phase 2: auto-generated keyword entries from config/topic_taxonomy.json ──

    "precios_de_transferencia": {
        "strong": (
            "precios de transferencia",
            "transfer pricing",
        ),
        "weak": (
            "precios",
            "transferencia",
            "transfer",
            "pricing",
        ),
    },
    # ── v5 Phase 2: auto-generated keyword entries from config/topic_taxonomy.json ──

    "cambiario": {
        "strong": (
            "cambiario",
            "régimen cambiario",
            "banrep",
            "inversion extranjera",
        ),
        "weak": (
            "régimen",
            "inversion",
            "extranjera",
        ),
    },
    # ── v5 Phase 2: auto-generated keyword entries from config/topic_taxonomy.json ──

    "comercial_societario": {
        "strong": (
            "comercial societario",
            "comercial y societario",
            "societario",
            "obligaciones societarias",
            "obligaciones mercantiles",
        ),
        "weak": (
            "comercial",
            "obligaciones",
            "societarias",
            "mercantiles",
        ),
    },
    # ── v5 Phase 2: auto-generated keyword entries from config/topic_taxonomy.json ──

    "datos_tecnologia": {
        "strong": (
            "datos tecnologia",
            "datos y tecnología",
            "proteccion datos",
            "teletrabajo",
            "tic",
        ),
        "weak": (
            "datos",
            "tecnologia",
            "tecnología",
            "proteccion",
        ),
    },
    # ── v5 Phase 2: auto-generated keyword entries from config/topic_taxonomy.json ──

    "inversiones_incentivos": {
        "strong": (
            "inversiones incentivos",
            "inversiones e incentivos",
            "incentivos inversion",
        ),
        "weak": (
            "inversiones",
            "incentivos",
            "inversion",
        ),
    },
    # ── v5 Phase 2: auto-generated keyword entries from config/topic_taxonomy.json ──

    "presupuesto_hacienda": {
        "strong": (
            "presupuesto hacienda",
            "presupuesto y hacienda pública",
            "hacienda publica",
        ),
        "weak": (
            "presupuesto",
            "hacienda",
            "pública",
            "publica",
        ),
    },
    # ── v5 Phase 2: auto-generated keyword entries from config/topic_taxonomy.json ──

    "reformas_tributarias": {
        "strong": (
            "reformas tributarias",
            "reforma tributaria",
        ),
        "weak": (
            "reformas",
            "tributarias",
            "reforma",
            "tributaria",
        ),
    },
    # ── v5 Phase 2: auto-generated keyword entries from config/topic_taxonomy.json ──

    "otros_sectoriales": {
        "strong": (
            "otros sectoriales",
            "otras leyes sectoriales",
        ),
        "weak": (
            "otros",
            "sectoriales",
            "otras",
            "leyes",
        ),
    },
    # ── v5 Phase 2: auto-generated keyword entries from config/topic_taxonomy.json ──

    "sector_agropecuario": {
        "strong": (
            "sector agropecuario",
            "agricola",
            "rural",
            "agrario",
            "pesquero",
            "cafe",
        ),
        "weak": (
            "sector",
            "agropecuario",
        ),
    },
    # ── v5 Phase 2: auto-generated keyword entries from config/topic_taxonomy.json ──

    "sector_salud": {
        "strong": (
            "sector salud",
            "salud",
            "seguridad social salud",
            "sistema salud",
        ),
        "weak": (
            "sector",
            "seguridad",
            "social",
            "sistema",
        ),
    },
    # ── v5 Phase 2: auto-generated keyword entries from config/topic_taxonomy.json ──

    "sector_vivienda": {
        "strong": (
            "sector vivienda",
            "vivienda",
            "habitacional",
            "urbanismo",
            "subsidio vivienda",
        ),
        "weak": (
            "sector",
            "subsidio",
        ),
    },
    # ── v5 Phase 2: auto-generated keyword entries from config/topic_taxonomy.json ──

    "sector_financiero": {
        "strong": (
            "sector financiero",
            "financiero",
            "banca",
            "credito",
            "seguros",
            "cooperativas financieras",
        ),
        "weak": (
            "sector",
            "cooperativas",
            "financieras",
        ),
    },
    # ── v5 Phase 2: auto-generated keyword entries from config/topic_taxonomy.json ──

    "sector_cultura": {
        "strong": (
            "sector cultura",
            "cultura",
            "cine",
            "audiovisual",
            "artes",
            "patrimonio",
        ),
        "weak": (
            "sector",
        ),
    },
    # ── v5 Phase 2: auto-generated keyword entries from config/topic_taxonomy.json ──

    "sector_administracion_publica": {
        "strong": (
            "sector administracion publica",
            "sector administración pública",
            "administracion publica",
            "funcion publica",
            "empleado publico",
        ),
        "weak": (
            "sector",
            "administracion",
            "publica",
            "administración",
            "pública",
        ),
    },
    # ── v5 Phase 2: auto-generated keyword entries from config/topic_taxonomy.json ──

    "sector_profesiones_liberales": {
        "strong": (
            "sector profesiones liberales",
            "profesiones liberales",
            "ejercicio profesional",
            "colegios profesionales",
        ),
        "weak": (
            "sector",
            "profesiones",
            "liberales",
            "ejercicio",
            "profesional",
        ),
    },
    # ── v5 Phase 2: auto-generated keyword entries from config/topic_taxonomy.json ──

    "sector_educacion": {
        "strong": (
            "sector educacion",
            "sector educación",
            "educacion",
            "docente",
            "universitario",
            "escuelas",
        ),
        "weak": (
            "sector",
            "educación",
        ),
    },
    # ── v5 Phase 2: auto-generated keyword entries from config/topic_taxonomy.json ──

    "sector_turismo": {
        "strong": (
            "sector turismo",
            "turismo",
            "hotelero",
            "agencias viaje",
        ),
        "weak": (
            "sector",
            "agencias",
            "viaje",
        ),
    },
    # ── v5 Phase 2: auto-generated keyword entries from config/topic_taxonomy.json ──

    "sector_inclusion_social": {
        "strong": (
            "sector inclusion social",
            "sector inclusión social",
            "inclusion social",
            "discapacidad",
            "minorias",
            "victimas",
            "comunidades negras",
        ),
        "weak": (
            "sector",
            "inclusion",
            "social",
            "inclusión",
            "comunidades",
        ),
    },
    # ── v5 Phase 2: auto-generated keyword entries from config/topic_taxonomy.json ──

    "sector_servicios": {
        # v5 Phase 2: "servicios" alone is too generic (collides with
        # labor's "prima de servicios"). Keep only qualified phrases.
        "strong": (
            "sector servicios",
            "servicios publicos domiciliarios",
            "ley 142 de 1994",
            "ley 142/1994",
            "superservicios",
        ),
        "weak": (
            "domiciliarios",
        ),
    },
    # ── v5 Phase 2: auto-generated keyword entries from config/topic_taxonomy.json ──

    "sector_justicia": {
        "strong": (
            "sector justicia",
            "justicia",
            "rama judicial",
            "procesal penal",
            "civil",
        ),
        "weak": (
            "sector",
            "judicial",
            "procesal",
            "penal",
        ),
    },
    # ── v5 Phase 2: auto-generated keyword entries from config/topic_taxonomy.json ──

    "sector_energia_mineria": {
        "strong": (
            "sector energia mineria",
            "sector energía y minería",
            "energia",
            "mineria",
            "hidrocarburos",
            "minero energetico",
            "energias renovables",
        ),
        "weak": (
            "sector",
            "energía",
            "minería",
            "minero",
            "energetico",
        ),
    },
    # ── v5 Phase 2: auto-generated keyword entries from config/topic_taxonomy.json ──

    "sector_politico": {
        "strong": (
            "sector politico",
            "sector político",
            "politico",
            "electoral",
            "partidos politicos",
        ),
        "weak": (
            "sector",
            "político",
            "partidos",
            "politicos",
        ),
    },
    # ── v5 Phase 2: auto-generated keyword entries from config/topic_taxonomy.json ──

    "sector_deporte": {
        "strong": (
            "sector deporte",
            "deporte",
            "deportivo",
            "actividad fisica",
        ),
        "weak": (
            "sector",
            "actividad",
            "fisica",
        ),
    },
    # ── v5 Phase 2: auto-generated keyword entries from config/topic_taxonomy.json ──

    "sector_desarrollo_regional": {
        "strong": (
            "sector desarrollo regional",
            "desarrollo regional",
            "regiones",
            "territorial",
        ),
        "weak": (
            "sector",
            "desarrollo",
            "regional",
        ),
    },
    # ── v5 Phase 2: auto-generated keyword entries from config/topic_taxonomy.json ──

    "sector_ciencia": {
        "strong": (
            "sector ciencia",
            "sector ciencia y tecnología",
            "ciencia",
            "ciencia tecnologia",
            "investigacion",
            "innovacion",
        ),
        "weak": (
            "sector",
            "tecnología",
            "tecnologia",
        ),
    },
    # ── v5 Phase 2: auto-generated keyword entries from config/topic_taxonomy.json ──

    "sector_infancia": {
        "strong": (
            "sector infancia",
            "sector infancia y adolescencia",
            "infancia",
            "adolescencia",
            "menores",
            "niñez",
        ),
        "weak": (
            "sector",
        ),
    },
    # ── v5 Phase 2: auto-generated keyword entries from config/topic_taxonomy.json ──

    "sector_juegos_azar": {
        "strong": (
            "sector juegos azar",
            "sector juegos de azar",
            "juegos azar",
            "loterias",
            "apuestas",
        ),
        "weak": (
            "sector",
            "juegos",
        ),
    },
    # ── v5 Phase 2: auto-generated keyword entries from config/topic_taxonomy.json ──

    "sector_economia": {
        "strong": (
            "sector economia",
            "sector economía",
            "economia",
            "macroeconomico",
            "politica economica",
        ),
        "weak": (
            "sector",
            "economía",
            "politica",
            "economica",
        ),
    },
    # ── v5 Phase 2: auto-generated keyword entries from config/topic_taxonomy.json ──

    "sector_transporte": {
        "strong": (
            "sector transporte",
            "transporte",
            "transito",
            "vial",
        ),
        "weak": (
            "sector",
        ),
    },
    # ── v5 Phase 2: auto-generated keyword entries from config/topic_taxonomy.json ──

    "sector_emprendimiento": {
        "strong": (
            "sector emprendimiento",
            "emprendimiento",
            "startups",
            "empresas pequeñas",
        ),
        "weak": (
            "sector",
            "empresas",
            "pequeñas",
        ),
    },
    # ── v5 Phase 2: auto-generated keyword entries from config/topic_taxonomy.json ──

    "sector_medio_ambiente": {
        "strong": (
            "sector medio ambiente",
            "medio ambiente",
            "ambiental",
            "recursos naturales",
        ),
        "weak": (
            "sector",
            "medio",
            "ambiente",
            "recursos",
            "naturales",
        ),
    },
    # ── v5 Phase 2: auto-generated keyword entries from config/topic_taxonomy.json ──

    "sector_comercio_internacional": {
        "strong": (
            "sector comercio internacional",
            "comercio internacional",
            "aduanas",
            "importaciones",
            "exportaciones",
        ),
        "weak": (
            "sector",
            "comercio",
            "internacional",
        ),
    },
    # ── v5 Phase 2: auto-generated keyword entries from config/topic_taxonomy.json ──

    "sector_puertos": {
        "strong": (
            "sector puertos",
            "puertos",
            "portuario",
            "maritimo",
        ),
        "weak": (
            "sector",
        ),
    },
    # ── v5 Phase 2: auto-generated keyword entries from config/topic_taxonomy.json ──

    "sector_telecomunicaciones": {
        "strong": (
            "sector telecomunicaciones",
            "telecomunicaciones",
            "tic",
            "servicios comunicaciones",
        ),
        "weak": (
            "sector",
            "servicios",
            "comunicaciones",
        ),
    },
    # ── v5 Phase 2: auto-generated keyword entries from config/topic_taxonomy.json ──

    "leyes_derogadas": {
        "strong": (
            "leyes derogadas",
            "derogadas",
        ),
        "weak": (
            "leyes",
        ),
    },
    # ── v5 Phase 2: auto-generated keyword entries from config/topic_taxonomy.json ──

    "beneficiario_final_rub": {
        "strong": (
            "beneficiario final rub",
            "beneficiario final y rub",
            "rub",
            "beneficiarios finales",
        ),
        "weak": (
            "beneficiario",
            "final",
            "beneficiarios",
            "finales",
        ),
    },
    # ── v5 Phase 2: auto-generated keyword entries from config/topic_taxonomy.json ──

    "contratacion_estatal": {
        "strong": (
            "contratacion estatal",
            "contratación estatal",
        ),
        "weak": (
            "contratacion",
            "estatal",
            "contratación",
        ),
    },
    # ── v5 Phase 2: auto-generated keyword entries from config/topic_taxonomy.json ──

    "economia_digital_criptoactivos": {
        "strong": (
            "economia digital criptoactivos",
            "economía digital y criptoactivos",
            "economia digital pes cripto",
            "criptoactivos",
            "activos digitales",
        ),
        "weak": (
            "economia",
            "digital",
            "economía",
            "cripto",
            "activos",
        ),
    },
    # ── v5 Phase 2: auto-generated keyword entries from config/topic_taxonomy.json ──

    "reforma_pensional": {
        "strong": (
            "reforma pensional",
            "pensional",
        ),
        "weak": (
            "reforma",
        ),
    },
    # ── v5 Phase 2: auto-generated keyword entries from config/topic_taxonomy.json ──

    "emergencia_tributaria": {
        "strong": (
            "emergencia tributaria",
            "emergencia tributaria 2026",
            "decreto 0240",
        ),
        "weak": (
            "emergencia",
            "tributaria",
            "decreto",
        ),
    },
    # ── v5 Phase 2: auto-generated keyword entries from config/topic_taxonomy.json ──

    "impuestos_saludables": {
        "strong": (
            "impuestos saludables",
            "ibua",
            "icui",
        ),
        "weak": (
            "impuestos",
            "saludables",
        ),
    },
    # ── v5 Phase 2: auto-generated keyword entries from config/topic_taxonomy.json ──

    "regimen_tributario_especial": {
        "strong": (
            "regimen tributario especial",
            "régimen tributario especial",
            "esal",
        ),
        "weak": (
            "regimen",
            "tributario",
            "especial",
            "régimen",
        ),
    },
    # ── v5 Phase 2: auto-generated keyword entries from config/topic_taxonomy.json ──

    "impuesto_nacional_consumo": {
        "strong": (
            "impuesto nacional consumo",
            "impuesto nacional al consumo",
        ),
        "weak": (
            "impuesto",
            "nacional",
            "consumo",
        ),
    },
    # ── v5 Phase 2: auto-generated keyword entries from config/topic_taxonomy.json ──

    "normas_internacionales_auditoria": {
        "strong": (
            "normas internacionales auditoria",
            "normas internacionales de auditoría",
        ),
        "weak": (
            "normas",
            "internacionales",
            "auditoria",
            "auditoría",
        ),
    },
    # ── v5 Phase 2: auto-generated keyword entries from config/topic_taxonomy.json ──

    "activos_exterior": {
        "strong": (
            "activos exterior",
            "activos en el exterior",
        ),
        "weak": (
            "activos",
            "exterior",
        ),
    },
    # ── v5 Phase 2: auto-generated keyword entries from config/topic_taxonomy.json ──

    "estatuto_tributario": {
        "strong": (
            "estatuto tributario",
        ),
        "weak": (
            "estatuto",
            "tributario",
        ),
    },
}

_TOPIC_NOTICE_OVERRIDES = {
    "laboral": "Tu pregunta es de laboral, por lo cual utilizaremos nuestra base de datos laboral.",
}


_SUBTOPIC_OVERRIDE_PATTERNS: tuple[tuple[re.Pattern[str], str, tuple[str, ...]], ...] = (
    # Each tuple: (compiled_regex, topic_key, search_keywords_tuple)
    # Keywords bias lexical ranking toward relevant documents within the candidate pool.
    # ── More-specific patterns first (GMF, consumo, patrimonio) ──

    # GMF (4x1000) — triggers on GMF-specific terms
    (re.compile(
        r"(?:"
        r"\bgmf\b|"                                  # GMF
        r"4\s*(?:x|por)\s*(?:1\.?000|mil)|"          # 4x1000, 4 por mil
        r"cuatro\s+por\s+mil|"                       # cuatro por mil
        r"gravamen\s+(?:a\s+los\s+)?movimiento|"     # gravamen movimiento financiero
        r"cuenta\s+exenta\s+(?:de\s+)?gmf|"          # cuenta exenta de GMF
        r"exenci[oó]n\s+(?:de\s+)?gmf|"              # exención de GMF
        r"art[ií]culo\s+87[0-9]"                     # artículos 870-879 ET
        r")", re.IGNORECASE),
     "gravamen_movimiento_financiero_4x1000",
     ("gmf", "gravamen", "movimiento financiero", "4x1000", "exención")),

    # Impuesto al Consumo — triggers on consumo in restaurant/beverage context
    (re.compile(
        r"(?:"
        r"impuesto\s+(?:al\s+)?consumo|"            # impuesto al consumo / impuesto consumo
        r"impoconsumo|"                              # impoconsumo
        r"consumo\s+(?:restaurante|8%|del\s+8)|"     # consumo restaurante, consumo 8%
        r"art[ií]culo\s+512|"                        # artículo 512-1..512-22 ET
        r"(?:restaurante|bar).*(?:iva|consumo|cobr)|" # restaurante + iva/consumo
        r"(?:iva|consumo).*(?:restaurante|bar)"       # iva/consumo + restaurante
        r")", re.IGNORECASE),
     "impuesto_consumo",
     ("impuesto consumo", "impoconsumo", "restaurante", "tarifa 8%", "artículo 512")),

    # Patrimonio Fiscal — triggers on patrimonio in declaración de renta context
    (re.compile(
        r"(?:"
        r"patrimonio\s+fiscal|"                      # patrimonio fiscal
        r"patrimonio\s+(?:bruto|l[ií]quido)\s+(?:fiscal|en\s+(?:la\s+)?(?:declaraci|renta))|"
        r"patrimonio.*(?:declaraci[oó]n\s+de\s+renta|formulario\s+110)|"
        r"valor\s+patrimonial\s+(?:fiscal|de\s+(?:acciones|inmueble|activo))|"
        r"costo\s+fiscal\s+(?:de|del|ajustado)|"     # costo fiscal de/del/ajustado [activo]
        r"aval[uú]o\s+(?:catastral|fiscal)|"         # avalúo catastral/fiscal
        r"art[ií]culo\s+(?:261|267|269|271|277|287)|" # arts. patrimonio fiscal ET
        r"art(?:[ií]culo|\.?)?\s+(?:127-1|145)\b"    # art./artículo 127-1 (leasing), 145 (deterioro)
        r")", re.IGNORECASE),
     "patrimonio_fiscal_renta",
     ("patrimonio fiscal", "valor patrimonial", "activo fiscal", "patrimonio bruto", "patrimonio líquido")),

    # ── Costos y Deducciones (last — broadest pattern) ──
    # Requires cost/deduction-specific terms; single "deducir" alone is
    # too broad (could be GMF deduction, patrimonio context, etc.).
    (re.compile(
        r"(?:"
        r"(?:costo|gasto|expensa|partida)s?\s+(?:no\s+)?deducible(?:s)?|" # costos/gastos (no) deducibles
        r"deducci[oó]n(?:es)?.*(?:procedente|renta|fiscal|tributari)|" # deducción + fiscal context
        r"(?:costo|gasto)s?.*(?:deduci|procedente|rechaz)|" # costos deducibles/procedentes/rechazados
        r"(?:costo|gasto)s?\s+(?:fiscal(?:es|mente)?)|" # costos fiscales / gastos fiscalmente
        r"l[ií]mite\s+(?:de\s+)?(?:deducci|pago.*efectivo)|" # límite de deducciones / pagos en efectivo
        r"expensas?\s+necesaria|"                     # expensas necesarias
        r"art[ií]culo\s+10[57]\b|"                    # artículo 105, 107 ET
        r"art[ií]culo\s+771|"                         # artículo 771-5 ET
        r"art[ií]culo\s+118-?1|"                      # artículo 118-1 ET (subcapitalización)
        r"subcapitalizaci[oó]n|"                      # subcapitalización
        r"documento\s+soporte.*(?:costo|gasto|pago|deduci)|(?:costo|gasto|pago).*documento\s+soporte|" # doc soporte in cost context only
        r"deducibilidad|"                             # deducibilidad
        r"deducci[oó]n.*descuento|descuento.*deducci[oó]n|" # deducción vs descuento (tax classification)
        r"amortiz(?:ar|aci)|"                         # amortizar/amortización (investment deduction)
        r"(?:puedo|puede|debo)\s+deduci\w*\s+(?:esa|esta|la|el|dicha)\s+(?:inversi|donaci)" # deducir inversión/donación
        r")", re.IGNORECASE),
     "costos_deducciones_renta",
     ("deducible", "deducción", "costo fiscal", "gasto deducible", "expensas necesarias")),

    # ── Laboral — colloquial labor liquidation queries ──────────────────
    # Catches questions like "cuanto le debo pagar a una empleada temporal
    # que trabaja 3 dias semanales" — labor-side quantification/liquidation
    # intent that the formal _TOPIC_KEYWORDS["laboral"] list misses because
    # it uses academic vocabulary ("trabajador", "nómina", "contrato de
    # trabajo") instead of colloquial Spanish ("empleada", "pagar",
    # "temporal", "3 dias semanales").
    #
    # IMPORTANT — placement is positional. _check_subtopic_overrides returns
    # the FIRST match, so this MUST stay AFTER costos_deducciones_renta so
    # that legit cost-deduction queries like "puedo deducir lo que le pago
    # a mis empleados" win first claim. The verbs here are deliberately
    # tightened (cuanto/liquidar/debo pagar) rather than bare pago/pagar
    # to avoid shadowing those queries.
    (re.compile(
        r"(?:"
        r"\bcu[aá]nto\b[^.?!]{0,40}\b(?:le\s+)?(?:pago|pagar|debo|tengo\s+que\s+pagar|liquid\w*)\b[^.?!]{0,40}\b(?:emplead[oa]s?|trabajador[ae]s?|obrer[oa]s?|domestic[oa]s?)|"
        r"\bliquid\w*\b[^.?!]{0,30}\b(?:emplead[oa]|trabajador[ae]|contratist[ae]|obrer[oa])|"
        r"(?:emplead[oa]|trabajador[ae]|obrer[oa])\s+(?:temporal|por\s+d[ií]as|por\s+horas|de\s+medio\s+tiempo|de\s+tiempo\s+parcial|de\s+servicio\s+dom[eé]stic)|"
        r"(?:trabaja|labora)\s+\d+\s+d[ií]as?\s+(?:a\s+la\s+semana|semanales?|por\s+semana|al\s+mes|mensuales?)|"
        r"\btiempo\s+parcial\b|\bmedia\s+jornada\b|\bmedio\s+tiempo\b|jornada\s+(?:parcial|reducida)|"
        r"servicio\s+dom[eé]stic[oa]"
        r")", re.IGNORECASE),
     "laboral",
     ("trabajador tiempo parcial", "empleado temporal", "jornada parcial", "liquidación nómina", "prestaciones sociales proporcionales")),
)
