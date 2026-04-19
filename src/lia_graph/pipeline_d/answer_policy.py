from __future__ import annotations

import re
import unicodedata

from .contracts import GraphEvidenceItem

FIRST_BUBBLE_ROUTE_LIMIT = 4
FIRST_BUBBLE_RISK_LIMIT = 3
FIRST_BUBBLE_SUPPORT_LIMIT = 2
FIRST_BUBBLE_RECAP_LIMIT = 3

DIRECT_ANSWER_BULLETS_PER_QUESTION = 5
DIRECT_ANSWER_COVERAGE_PENDING = (
    "Cobertura pendiente para esta sub-pregunta; valida el expediente antes de cerrarla con el cliente."
)

PLANNING_FIRST_BUBBLE_SETUP_LIMIT = 3
PLANNING_FIRST_BUBBLE_STRATEGY_LIMIT = 4
PLANNING_FIRST_BUBBLE_CRITERIA_LIMIT = 4
PLANNING_FIRST_BUBBLE_CHECKLIST_LIMIT = 3

ARTICLE_GUIDANCE: dict[str, dict[str, tuple[str, ...]]] = {
    "850": {
        "recommendation": (
            "Toma el caso como una devolución de saldo a favor y valida primero que el saldo esté bien determinado en la declaración base.",
        ),
        "procedure": (
            "Antes de radicar, revisa la declaración que origina el saldo a favor y alinea soportes, anexos y datos del contribuyente.",
            "Si el expediente está completo, usa los términos de 50, 30 o 20 días hábiles como referencia operativa según el soporte con el que se presente la solicitud.",
        ),
        "precaution": (
            "No conviene radicar con cifras o soportes inconsistentes porque eso puede abrir inadmisiones o revisiones posteriores.",
        ),
        "opportunity": (
            "Si el cliente necesita caja, esta es la base para pedir reintegro del saldo a favor.",
        ),
    },
    "589": {
        "recommendation": (
            "Si el saldo a favor cambia por ajustes, corrige primero la declaración antes de mover el trámite frente a la DIAN.",
        ),
        "procedure": (
            "Ordena la secuencia así: corrección si aplica, luego devolución o compensación.",
            "Confirma si todavía estás dentro del año siguiente al vencimiento para corregir a favor del contribuyente.",
        ),
        "precaution": (
            "No mezcles una devolución con una declaración todavía inconsistente o pendiente de corregir.",
            "Recuerda que una corrección a favor reinicia el término de revisión de la DIAN desde la fecha de la corrección.",
        ),
    },
    "815": {
        "recommendation": (
            "Define si al cliente le conviene más devolución en efectivo o compensación contra otras obligaciones.",
        ),
        "procedure": (
            "Revisa las deudas tributarias vigentes del cliente antes de decidir si pides dinero o compensas saldos.",
        ),
        "opportunity": (
            "La compensación puede proteger caja y acelerar el beneficio económico si el cliente ya tiene obligaciones por pagar.",
        ),
    },
    "854": {
        "procedure": (
            "Controla el término para pedir la devolución; el calendario del trámite es parte del análisis, no un detalle posterior.",
        ),
        "precaution": (
            "No confundas el plazo del trámite con el año gravable que originó el saldo a favor.",
        ),
    },
    "855": {
        "procedure": (
            "Si la DIAN inadmite, corrige rápidamente el faltante formal dentro del término y vuelve a radicar con trazabilidad completa.",
        ),
        "precaution": (
            "Un trámite incompleto puede devolver al cliente al inicio del proceso.",
        ),
    },
    "857": {
        "precaution": (
            "La devolución o compensación puede caerse si faltan requisitos formales o el expediente no está bien soportado.",
        ),
    },
    "860": {
        "precaution": (
            "Una devolución improcedente expone al cliente a reintegro y sanciones, así que la revisión previa debe ser conservadora.",
        ),
        "opportunity": (
            "Si el caso permite garantía, evalúa si mejora la velocidad del trámite sin aumentar demasiado el costo del cliente.",
        ),
    },
    "588": {
        "recommendation": (
            "Antes de corregir, define si el ajuste aumenta el impuesto o reduce el saldo a favor, porque eso cambia el mecanismo, el plazo y la sanción.",
        ),
        "procedure": (
            "Si la corrección va en contra del contribuyente, valida primero si sigues dentro de los 3 años y si ya existe un emplazamiento o requerimiento especial.",
        ),
        "precaution": (
            "No uses la lógica del art. 588 cuando en realidad la corrección aumenta el saldo a favor o disminuye el valor a pagar.",
        ),
    },
    "670": {
        "precaution": (
            "Si ya hubo devolución o compensación y luego corriges reduciendo el saldo, evalúa de inmediato el riesgo de improcedencia y reintegro.",
        ),
    },
    "689-3": {
        "recommendation": (
            "Si el cliente está usando beneficio de auditoría, mide ese impacto antes de firmar cualquier corrección.",
        ),
        "procedure": (
            "Simula si la corrección mantiene o destruye la firmeza acelerada de 6 o 12 meses antes de presentarla.",
        ),
        "precaution": (
            "Una corrección que baja el incremento exigido puede hacer que el cliente pierda el beneficio de auditoría y vuelva a una firmeza más larga.",
        ),
    },
    "714": {
        "recommendation": (
            "Calcula la firmeza como una decisión del caso, no como una nota final de compliance.",
        ),
        "procedure": (
            "Define si aplicas la regla general de 3 años, la especial de 5 años o una firmeza acelerada por beneficio de auditoría antes de aconsejar al cliente.",
        ),
        "precaution": (
            "No confundas plazo para corregir con término de firmeza: que la declaración siga abierta a revisión no siempre significa que todavía puedas corregir voluntariamente.",
        ),
    },
    "771-2": {
        "recommendation": (
            "No tomes el costo, la deducción o el IVA descontable hasta validar que el soporte fiscal sí aguanta una revisión.",
        ),
        "procedure": (
            "Arma el expediente del gasto con factura o documento soporte y con evidencia adicional del hecho económico.",
        ),
        "precaution": (
            "Si el soporte es débil, la DIAN puede rechazar costo, deducción o impuesto descontable.",
        ),
    },
    "616-1": {
        "recommendation": (
            "Verifica si el emisor estaba obligado a facturar electrónicamente y si hubo contingencia válida antes de aceptar el soporte.",
        ),
        "procedure": (
            "Si hubo contingencia, deja evidencia del evento y de la normalización posterior de la factura.",
        ),
        "precaution": (
            "No sustituyas la factura electrónica por cualquier soporte cuando la obligación sí existía.",
        ),
    },
    "617": {
        "recommendation": (
            "Revisa los requisitos formales de la factura antes de usarla en renta o IVA.",
        ),
        "procedure": (
            "Haz una revisión mínima de numeración, identificación y datos obligatorios antes del cierre tributario.",
        ),
        "precaution": (
            "Una factura sin requisitos reduce la defensa del cliente si la DIAN cuestiona el soporte.",
        ),
    },
    "743": {
        "precaution": (
            "Conserva medios de prueba adicionales porque la factura sola no siempre agota la carga probatoria.",
        ),
    },
    "115": {
        "recommendation": (
            "Toma como punto de partida el texto vigente hoy del art. 115 ET para definir el tratamiento en renta del impuesto pagado.",
        ),
        "procedure": (
            "Verifica si el valor efectivamente pagado puede tratarse como descuento tributario sin duplicarlo como costo o gasto.",
        ),
        "precaution": (
            "No dupliques el mismo valor como descuento tributario y como costo o gasto dentro de la misma declaración.",
        ),
    },
    "147": {
        "recommendation": (
            "La regla matriz del art. 147 ET es que la sociedad compensa pérdidas fiscales contra rentas líquidas ordinarias futuras; no las traslada a los socios ni las trata como un saldo a favor.",
            "Si además te preocupa la firmeza, mídela aparte: una cosa es la mecánica de compensación y otra el término de revisión de esa pérdida.",
        ),
        "procedure": (
            "Para pérdidas sujetas al régimen vigente, el límite es temporal: doce períodos gravables siguientes y sin tope porcentual anual.",
            "Si el saldo viene de años pre-2017, valida primero el régimen congelado del art. 290 ET antes de aplicar la regla de 12 años.",
            "Haz un inventario de las pérdidas por año de origen, saldo pendiente y renta líquida disponible del período antes de definir cuánto vas a absorber en la declaración.",
            "Compensa solo contra renta líquida ordinaria del período; lo que no alcances a usar sigue arrastrándose hasta el vencimiento de su propio término.",
        ),
        "precaution": (
            "No cierres la posición solo con la palabra 'compensación': aquí el problema principal es pérdidas fiscales en renta, no devolución o compensación de saldos a favor.",
            "No leas la firmeza con la regla ordinaria de 3 años si la declaración origina o compensa pérdidas: en ese frente el expediente debe pensarse a 6 años.",
        ),
        "opportunity": (
            "Si el cliente volvió a tener renta líquida positiva, esta es la norma base para bajar la base gravable con pérdidas acumuladas dentro del marco vigente.",
        ),
    },
    "807": {
        "recommendation": (
            "Define primero cuál es el impuesto neto de renta que sirve de base del anticipo y qué porcentaje aplica según la antigüedad del contribuyente.",
        ),
        "procedure": (
            "Liquida el anticipo del año siguiente sobre el impuesto neto de renta del año base y aplica 25 %, 50 % o 75 % según corresponda por la antigüedad del contribuyente.",
            "Si proyectas que el impuesto del año siguiente será sustancialmente menor, evalúa la solicitud de reducción del anticipo antes del vencimiento con soporte financiero suficiente.",
        ),
        "precaution": (
            "No confundas la regla específica del anticipo con la tarifa general del impuesto ni con otras rentas exentas que no definen por sí solas la base del anticipo.",
        ),
    },
}

TITLE_GUIDANCE: tuple[tuple[tuple[str, ...], dict[str, tuple[str, ...]]], ...] = (
    (
        ("devolucion", "saldo a favor"),
        {
            "recommendation": (
                "Trata el asunto como un flujo de recuperación o aplicación del saldo a favor, no solo como una consulta normativa abstracta.",
            ),
        },
    ),
    (
        ("correccion", "saldo a favor"),
        {
            "procedure": (
                "Valida si el saldo a favor necesita corrección previa antes de presentar cualquier solicitud frente a la DIAN.",
            ),
        },
    ),
    (
        ("compensacion",),
        {
            "opportunity": (
                "Revisa si la compensación resuelve mejor la posición de caja o de pasivos del cliente que una espera por devolución.",
            ),
        },
    ),
    (
        ("factura",),
        {
            "recommendation": (
                "Haz una revisión operativa del soporte antes de defenderlo fiscalmente.",
            ),
        },
    ),
    (
        ("requisitos", "factura"),
        {
            "procedure": (
                "Revisa el check mínimo de requisitos antes de incorporar el documento al cierre tributario del cliente.",
            ),
        },
    ),
    (
        ("prueba",),
        {
            "precaution": (
                "Fortalece el expediente con pruebas del negocio real, no solo con el documento principal.",
            ),
        },
    ),
)


def guidance_for_item(item: GraphEvidenceItem) -> dict[str, tuple[str, ...]]:
    merged: dict[str, list[str]] = {}
    title = _normalize_text(item.title)
    for source in (ARTICLE_GUIDANCE.get(item.node_key, {}), *matched_title_guidance(title)):
        for field, lines in source.items():
            merged.setdefault(field, [])
            for line in lines:
                if line not in merged[field]:
                    merged[field].append(line)
    return {field: tuple(lines) for field, lines in merged.items()}


def matched_title_guidance(title: str) -> tuple[dict[str, tuple[str, ...]], ...]:
    hits: list[dict[str, tuple[str, ...]]] = []
    for markers, payload in TITLE_GUIDANCE:
        if all(marker in title for marker in markers):
            hits.append(payload)
    return tuple(hits)


def build_tax_planning_first_bubble_sources(
    *,
    period_label: str,
    support_signal: str,
) -> dict[str, tuple[str, ...]]:
    strategy_lines = [
        "Modela primero beneficios que la ley abrió expresamente y que el cliente puede cumplir de verdad: primer empleo, discapacidad, mujeres víctimas, factura electrónica, pérdidas fiscales, beneficio de auditoría e inversiones con incentivo. La regla práctica es escoger solo los que puedas documentar antes del cierre y dejar fuera cualquier ahorro que dependa de arreglar papeles después. (art. 869-1 ET, inc. 3; art. 108-5 ET; art. 7 Ley 2277 de 2022; art. 147 ET)",
        "Evalúa RST vs. ordinario como una decisión de modelo de negocio y no de intuición. A una SAS con márgenes bajos, pérdidas por compensar o deducciones fuertes normalmente le conviene correr ambos escenarios y decidir con cifras; el error clásico es irse por tarifa aparente y renunciar a beneficios que sí pesan en el ordinario. (arts. 903-916 ET; art. 908 ET; art. 147 ET)",
        "Usa timing solo cuando el hecho económico manda la fecha: puedes acelerar algo ya ejecutado o diferir algo que realmente ocurrirá después, pero no inventarte entregas, notas crédito o contratos de papel para mover la base. El cierre sano se juega revisando contratos y hitos reales en noviembre y diciembre, no maquillando enero desde contabilidad. (arts. 27 y 28 ET; arts. 869 y 869-1 ET)",
        "Si vas a recomendar donaciones, descuentos o inversiones especiales, modela el efecto completo y no solo el beneficio aislado. En sociedades sujetas a TTD, un incentivo puede verse bonito por separado y perder potencia o incluso empeorar el resultado cuando lo cruzas con la tasa mínima. (art. 257 ET; par. 6 art. 240 ET)",
    ]
    if "donacion" not in support_signal and "ttd" not in support_signal:
        strategy_lines[-1] = (
            "Si el caso pasa por remuneración, leasing o inversiones productivas, baja la recomendación a números y a soporte desde ya. El ahorro legítimo casi siempre nace de escoger mejor la estructura del negocio, no de inventarse una capa jurídica de última hora para bajar el impuesto. (art. 127-1 ET; arts. 107 y 869 ET)"
        )
    return {
        "setup": (
            f"Empieza con una proyección seria de cierre para {period_label}: utilidad, caja, TTD, pérdidas fiscales disponibles y opción de beneficio de auditoría. La planeación buena no arranca preguntando qué descuento cabe, sino qué decisiones sí mejoran el resultado sin deformar el negocio. (par. 6 art. 240 ET; arts. 147 y 689-3 ET)",
            "Haz un inventario corto de decisiones que todavía puedes mover antes del cierre: contrataciones, inversiones, fecha real de entrega o facturación, donaciones, política de dividendos y si el siguiente año conviene seguir en ordinario o modelar RST. Si algo ya ocurrió o no tiene soporte para cambiarse, trátalo como riesgo y no como planeación. (arts. 27 y 28 ET; arts. 903-916 ET)",
            "A un contador nuevo yo le diría que persiga solo palancas con propósito de negocio, soporte y efecto tributario medible. Esa disciplina es la que te mantiene del lado de la economía de opción y te saca de la conversación de simulación. (arts. 869 y 869-1 ET; Ley 1607 de 2012)",
        ),
        "strategy": tuple(strategy_lines),
        "criteria": (
            "La línea que usa la jurisprudencia y la cláusula antiabuso es bastante práctica: la operación debe tener razón comercial o económica visible, riesgo empresarial real y una explicación que siga teniendo sentido aunque la lean sin simpatía en una fiscalización. Si el único motor reconocible es bajar el impuesto, ya entraste en zona de pelea. (art. 869 ET; Consejo de Estado, Sección Cuarta, Exp. 27693 del 6 de junio de 2024)",
            "Lo que más compromete un caso son los actos artificiosos: terceros interpuestos sin función real, precios fuera de mercado sin explicación, contratos que nadie ejecuta, combinaciones circulares y estructuras que producen un beneficio fiscal muy alto sin un riesgo económico equivalente. Ahí es donde la DIAN puede recaracterizar o reconfigurar la operación. (arts. 869 y 869-1 ET; Ley 1819 de 2016)",
            "La defensa práctica no se gana con una etiqueta bonita sino con coherencia: contrato, acta, factura, flujo bancario, nómina, contabilidad y declaración deben contar la misma historia. Cuando cada capa muestra algo distinto, la discusión deja de ser teórica y pasa a ser probatoria. (arts. 869-1 y 869-2 ET)",
            "Usar opciones que la ley sí ofrece no es abuso; pervertir la forma para conseguir un efecto que la norma no quiso dar sí lo es. Esa es, en la práctica, la diferencia entre planeación legítima y elusión agresiva. (art. 869-1 ET, inc. 3; Ley 1607 de 2012)",
        ),
        "checklist": (
            "Deja una simulación de cierre con escenario base y escenario optimizado, mostrando qué cambia, qué no cambia y por qué se escogió una ruta. Ese papel de trabajo es el puente entre la recomendación al cliente y la defensa futura de la decisión. (art. 869 ET)",
            "Por cada beneficio o estrategia, deja el soporte que prueba el hecho económico y el requisito especial: certificaciones laborales, factura electrónica validada y pago electrónico, inventario de pérdidas, actas, estudios o aprobaciones sectoriales. Si el soporte todavía no existe, la estrategia todavía no está lista para venderse como ahorro. (art. 108-5 ET; art. 7 Ley 2277 de 2022; art. 147 ET)",
            "Si la ruta implica cambios contractuales o societarios, deja una nota corta de propósito de negocio, fecha de decisión, responsables y efecto esperado en contabilidad e impuestos. Es una defensa simple, barata y muy poderosa contra la lectura de acto de papel armado al final del año. (arts. 869 y 869-1 ET)",
        ),
    }


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_text).strip().lower()


__all__ = [
    "ARTICLE_GUIDANCE",
    "DIRECT_ANSWER_BULLETS_PER_QUESTION",
    "DIRECT_ANSWER_COVERAGE_PENDING",
    "FIRST_BUBBLE_RECAP_LIMIT",
    "FIRST_BUBBLE_RISK_LIMIT",
    "FIRST_BUBBLE_ROUTE_LIMIT",
    "FIRST_BUBBLE_SUPPORT_LIMIT",
    "PLANNING_FIRST_BUBBLE_CHECKLIST_LIMIT",
    "PLANNING_FIRST_BUBBLE_CRITERIA_LIMIT",
    "PLANNING_FIRST_BUBBLE_SETUP_LIMIT",
    "PLANNING_FIRST_BUBBLE_STRATEGY_LIMIT",
    "TITLE_GUIDANCE",
    "build_tax_planning_first_bubble_sources",
    "guidance_for_item",
    "matched_title_guidance",
]
