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
"""

from __future__ import annotations

import re


_TOPIC_KEYWORDS: dict[str, dict[str, tuple[str, ...]]] = {
    "laboral": {
        "strong": (
            "seguridad social",
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
            # NOTE: bare "liquidar" / "liquidacion" / "liquidación" used to live
            # here but they are polysemous (liquidación oficial DIAN, liquidación
            # privada, liquidación de sociedad, liquidación de contrato civil).
            # The labor compounds are already covered above (strong:
            # "liquidación de contrato", "liquidación de nómina",
            # "liquidación de prestaciones") and by the laboral regex in
            # `_SUBTOPIC_OVERRIDE_PATTERNS` (liquidar + empleado/trabajador
            # within 30 chars), so recall on real labor queries is preserved
            # without routing generic "liquidación" queries to laboral.
            "trabajador",
            "trabajadores",
            "salud",
            "pension",
            "pensión",
            "cesantias",
            "cesantías",
            "prima",
            "vacaciones",
            "contrato laboral",
            "aportes",
            "aportaciones",
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
            "planilla",
            "fondo de cesantías",
            "fondo de pensiones",
            "caja de compensación",
            "sena",
            "icbf",
            "bonificación",
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
