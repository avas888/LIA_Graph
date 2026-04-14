from __future__ import annotations

import json
import logging
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

from .llm_runtime import resolve_llm_adapter
from .topic_guardrails import (
    TopicScope,
    extend_topic_scope_allowed_topics,
    get_supported_topics,
    get_topic_scope,
    normalize_topic_key,
    register_topic_alias,
    register_topic_scope,
)

_SUPPORTED_TOPICS: tuple[str, ...] = tuple(sorted(get_supported_topics()))
_LLM_CONFIDENCE_THRESHOLD = 0.75
_MAX_SECONDARY_TOPICS = 3

# Narrow SQL filter for child topics: maps child_topic → frozenset of core DB
# topic values to use in SQL WHERE instead of full inherited scope.
# Populated during _bootstrap_custom_corpora() pass 2.
_PARENT_CORE_TOPICS: dict[str, frozenset[str]] = {}


@dataclass(frozen=True)
class TopicDetection:
    """Resultado de deteccion de tema basada en keywords, reutilizable por ingestion."""

    topic: str | None
    confidence: float
    scores: dict[str, float]
    source: str = "keywords"

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
            "liquidar",
            "liquidacion",
            "liquidación",
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
}

_TOPIC_NOTICE_OVERRIDES = {
    "laboral": "Tu pregunta es de laboral, por lo cual utilizaremos nuestra base de datos laboral.",
}


def register_topic_keywords(
    topic_key: str,
    strong: tuple[str, ...] | list[str] = (),
    weak: tuple[str, ...] | list[str] = (),
) -> None:
    """Register keyword patterns for a custom topic at runtime."""
    entry: dict[str, tuple[str, ...]] = {}
    if strong:
        entry["strong"] = tuple(strong)
    if weak:
        entry["weak"] = tuple(weak)
    if entry:
        _TOPIC_KEYWORDS[topic_key] = entry


def _bootstrap_custom_corpora() -> None:
    """Carga corpora_custom.json al inicio y registra keywords + scopes para cada corpus custom.

    Esto hace que corpora_custom.json sea la fuente unica de verdad para topicos custom:
    cualquier corpus con topic != null se registra automaticamente en el router y los
    guardrails, sin necesidad de editar topic_guardrails.py ni topic_router.py a mano.
    """
    import json
    from pathlib import Path

    cfg_path = Path("config/corpora_custom.json")
    if not cfg_path.exists():
        # Fallback: ruta relativa al archivo fuente
        cfg_path = Path(__file__).parent.parent.parent / "config" / "corpora_custom.json"
    if not cfg_path.exists():
        return

    try:
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
    except Exception:
        logger.warning("topic_router: error cargando corpora_custom.json en bootstrap", exc_info=True)
        return

    # Pass 1: register keywords + scopes for each custom corpus
    parent_links: list[tuple[str, str]] = []  # (child_topic, parent_topic_key)

    for entry in data.get("custom_corpora", []):
        key = str(entry.get("key") or "").strip()
        topic = str(entry.get("topic") or "").strip()
        if not key or not topic:
            continue  # corpus sin topic (ej. "principal" catch-all)

        # Keywords para N1
        kw = entry.get("keywords") or {}
        register_topic_keywords(topic, strong=list(kw.get("strong") or []), weak=list(kw.get("weak") or []))

        # TopicScope para guardrails (si no existe ya)
        if topic not in get_supported_topics():
            label = str(entry.get("label") or key)
            register_topic_scope(TopicScope(
                key=topic,
                label=label,
                allowed_topics=frozenset({topic}),
                allowed_path_prefixes=(),
            ))
            register_topic_alias(topic, topic)
            if key != topic:
                register_topic_alias(key, topic)

        # Collect parent_topic links for pass 2
        parent_key = str(entry.get("parent_topic") or "").strip()
        if not parent_key and entry.get("active", False):
            logger.warning(
                "topic_router: custom corpus '%s' (topic='%s') has no parent_topic "
                "— retrieval limited to docs tagged '%s'",
                key, topic, topic,
            )
        if parent_key:
            parent_links.append((topic, parent_key))

    # Pass 2: resolve parent_topic inheritance (bidirectional)
    # Child inherits parent's allowed_topics so retrieval finds parent docs.
    # Parent gains child's topic so parent queries still find re-tagged child docs.

    # Snapshot each parent's original allowed_topics BEFORE the loop extends
    # them with child keys — used for _PARENT_CORE_TOPICS narrow SQL filter.
    parent_original: dict[str, frozenset[str]] = {}
    for _child, pkey in parent_links:
        pcanon = normalize_topic_key(pkey) or pkey
        if pcanon not in parent_original:
            ps = get_topic_scope(pcanon)
            if ps is not None:
                parent_original[pcanon] = ps.allowed_topics

    for child_topic, parent_key in parent_links:
        parent_canonical = normalize_topic_key(parent_key)
        if parent_canonical is None:
            parent_canonical = parent_key
        parent_scope = get_topic_scope(parent_canonical)
        if parent_scope is None:
            logger.warning(
                "topic_router: parent_topic '%s' not found for custom corpus '%s'",
                parent_key, child_topic,
            )
            continue
        # Child inherits parent's allowed_topics + path prefixes
        child_scope = get_topic_scope(child_topic)
        if child_scope is not None:
            merged_topics = child_scope.allowed_topics | parent_scope.allowed_topics
            register_topic_scope(TopicScope(
                key=child_scope.key,
                label=child_scope.label,
                allowed_topics=merged_topics,
                allowed_path_prefixes=child_scope.allowed_path_prefixes + parent_scope.allowed_path_prefixes,
            ))
        # Parent gains child's topic key for bidirectional visibility
        extend_topic_scope_allowed_topics(parent_scope.key, frozenset({child_topic}))

        # Build narrow SQL filter for child: {child_topic} ∪ parent's ORIGINAL
        # allowed_topics (before any child extensions).  This gives SQL
        # WHERE topic IN ('costos_deducciones_renta','renta','renta_parametros')
        # instead of the full 17+ inherited set.
        orig = parent_original.get(parent_canonical, frozenset())
        if orig:
            _PARENT_CORE_TOPICS[child_topic] = frozenset({child_topic}) | orig

    # Reconstruir _SUPPORTED_TOPICS para incluir los topics recien registrados
    global _SUPPORTED_TOPICS
    _SUPPORTED_TOPICS = tuple(sorted(get_supported_topics()))


_bootstrap_custom_corpora()


def get_narrow_topic_filter(topic: str) -> frozenset[str] | None:
    """Return narrow SQL topic values for a child topic, or None if not a child."""
    return _PARENT_CORE_TOPICS.get(topic)


def get_subtopic_search_keywords(topic: str) -> tuple[str, ...]:
    """Return search keywords for a sub-topic, or empty tuple."""
    # _SUBTOPIC_OVERRIDE_PATTERNS is defined later in this module (after
    # keyword dicts), so we build the reverse lookup lazily on first call.
    global _SUBTOPIC_KEYWORDS
    if _SUBTOPIC_KEYWORDS is None:
        _SUBTOPIC_KEYWORDS = {
            t: kw for _, t, kw in _SUBTOPIC_OVERRIDE_PATTERNS
        }
    return _SUBTOPIC_KEYWORDS.get(topic, ())


_SUBTOPIC_KEYWORDS: dict[str, tuple[str, ...]] | None = None


@dataclass(frozen=True)
class TopicRoutingResult:
    requested_topic: str | None
    effective_topic: str | None
    secondary_topics: tuple[str, ...]
    topic_adjusted: bool
    confidence: float
    reason: str
    topic_notice: str | None = None
    mode: str = "fallback"
    llm_runtime: dict[str, Any] | None = None
    subtopic_search_keywords: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "requested_topic": self.requested_topic,
            "effective_topic": self.effective_topic,
            "secondary_topics": list(self.secondary_topics),
            "topic_adjusted": self.topic_adjusted,
            "confidence": round(float(self.confidence), 4),
            "reason": self.reason,
            "topic_notice": self.topic_notice,
            "mode": self.mode,
            "llm_runtime": dict(self.llm_runtime or {}),
        }


def _strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _normalize_text(value: str) -> str:
    lowered = _strip_accents(value).lower()
    return re.sub(r"\s+", " ", lowered).strip()


def _normalize_secondary_topics(
    topics: tuple[str, ...] | list[str] | None,
    *,
    requested_topic: str | None,
    effective_topic: str | None,
    preserve_requested_topic_as_secondary: bool = True,
) -> tuple[str, ...]:
    ordered: list[str] = []
    for raw_topic in list(topics or ()):
        topic = normalize_topic_key(str(raw_topic or ""))
        if topic is None or topic == effective_topic or topic in ordered:
            continue
        ordered.append(topic)
    if (
        preserve_requested_topic_as_secondary
        and requested_topic is not None
        and requested_topic != effective_topic
        and requested_topic not in ordered
    ):
        ordered.insert(0, requested_topic)
    return tuple(ordered[:_MAX_SECONDARY_TOPICS])


def _build_topic_notice(effective_topic: str | None) -> str | None:
    topic = normalize_topic_key(effective_topic)
    if topic is None:
        return None
    if topic in _TOPIC_NOTICE_OVERRIDES:
        return _TOPIC_NOTICE_OVERRIDES[topic]
    label = topic.replace("_", " ")
    return f"Tu pregunta es de {label}, por lo cual utilizaremos nuestra base de datos {label}."


def _keyword_in_text(keyword: str, text: str) -> bool:
    """Match keyword as a complete word/phrase using word boundaries.

    Prevents false positives where a keyword is accidentally a substring
    of an unrelated word (e.g., 'arl' in 'sumarle', 'iva' in 'negativa').
    """
    return bool(re.search(r"\b" + re.escape(keyword) + r"\b", text))


def _score_topic_keywords(message: str) -> dict[str, dict[str, Any]]:
    normalized = _normalize_text(message)
    scores: dict[str, dict[str, Any]] = {}
    for topic, buckets in _TOPIC_KEYWORDS.items():
        strong_hits = [kw for kw in buckets.get("strong", ()) if _keyword_in_text(_normalize_text(kw), normalized)]
        weak_hits = [kw for kw in buckets.get("weak", ()) if _keyword_in_text(_normalize_text(kw), normalized)]
        if not strong_hits and not weak_hits:
            continue
        score = len(strong_hits) * 3 + len(weak_hits)
        scores[topic] = {
            "score": score,
            "strong_hits": strong_hits,
            "weak_hits": weak_hits,
        }
    return scores


def detect_topic_from_text(
    text: str, filename: str | None = None
) -> TopicDetection:
    """Detecta el tema dominante de un texto usando keywords.

    Funcion publica reutilizable por el clasificador de ingestion y otros modulos
    que necesitan deteccion de tema sin el pipeline completo de topic_router.

    Args:
        text: Texto a analizar (cuerpo del documento o query).
        filename: Nombre de archivo (reservado para uso futuro).

    Returns:
        TopicDetection con topic detectado, confianza y scores por tema.
    """
    raw_scores = _score_topic_keywords(text)
    if not raw_scores:
        return TopicDetection(topic=None, confidence=0.0, scores={})

    flat_scores: dict[str, float] = {
        t: float(d["score"]) for t, d in raw_scores.items()
    }
    ranked = sorted(raw_scores.items(), key=lambda item: int(item[1]["score"]), reverse=True)
    top_topic, top_data = ranked[0]
    top_score = int(top_data["score"])
    second_score = int(ranked[1][1]["score"]) if len(ranked) > 1 else 0

    # Determinar si el tema es dominante
    strong_hits = list(top_data.get("strong_hits", []))
    dominant = (
        top_score >= 5
        or (strong_hits and top_score >= 4)
        or (top_score >= 3 and top_score - second_score >= 2)
    )

    if not dominant:
        # No hay tema dominante claro; devolver mejor candidato con confianza baja
        confidence = min(top_score / 6.0, 1.0) * 0.5
        return TopicDetection(
            topic=top_topic, confidence=confidence, scores=flat_scores
        )

    confidence = min(top_score / 6.0, 1.0)
    return TopicDetection(
        topic=top_topic, confidence=confidence, scores=flat_scores
    )


def _build_rule_result(
    *,
    requested_topic: str | None,
    effective_topic: str,
    score: int,
    strong_hits: list[str],
    weak_hits: list[str],
    preserve_requested_topic_as_secondary: bool = True,
) -> TopicRoutingResult:
    hits = [*strong_hits, *weak_hits]
    confidence = min(0.99, 0.62 + score * 0.06)
    adjusted = effective_topic != requested_topic
    # Labor topic: never preserve renta (or any other requested topic) as a
    # secondary. Broad cross-domain fan-out would otherwise pull ET material
    # (for example art. 385 "periodos inferiores a treinta dias") back into a
    # labor bundle and re-introduce the leakage this rule is closing. Targeted
    # laboral<->renta bridging still happens only for explicit cross-domain
    # phrases such as "costos laborales", "nomina electronica", or "art. 108".
    # Applies to both override and keyword-scoring paths.
    preserve_secondary = (
        preserve_requested_topic_as_secondary and effective_topic != "laboral"
    )
    return TopicRoutingResult(
        requested_topic=requested_topic,
        effective_topic=effective_topic,
        secondary_topics=_normalize_secondary_topics(
            (),
            requested_topic=requested_topic,
            effective_topic=effective_topic,
            preserve_requested_topic_as_secondary=preserve_secondary,
        ),
        topic_adjusted=adjusted,
        confidence=confidence,
        reason=f"rule:{effective_topic} matched {', '.join(hits[:6])}",
        topic_notice=_build_topic_notice(effective_topic) if adjusted else None,
        mode="rule",
    )


# ── Sub-topic override patterns ──────────────────────────────────────────
# Regex patterns that detect specific sub-topic intent in natural language.
# These run BEFORE keyword scoring so that dedicated child corpora win over
# the broad `declaracion_renta` parent even when queries mention "renta".
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


def _check_subtopic_overrides(message: str) -> tuple[str, tuple[str, ...]] | None:
    """Return (topic, keywords) for the first matching sub-topic override, or None."""
    normalized = _normalize_text(message)
    for pattern, topic, keywords in _SUBTOPIC_OVERRIDE_PATTERNS:
        if pattern.search(normalized):
            return topic, keywords
    return None


def _resolve_rule_based_topic(
    message: str,
    requested_topic: str | None,
    *,
    preserve_requested_topic_as_secondary: bool = True,
) -> TopicRoutingResult | None:
    # Check sub-topic overrides first (child corpora that can't win keyword scoring)
    override = _check_subtopic_overrides(message)
    if override is not None:
        override_topic, override_keywords = override
        result = _build_rule_result(
            requested_topic=requested_topic,
            effective_topic=override_topic,
            score=6,
            strong_hits=[f"subtopic_override:{override_topic}"],
            weak_hits=[],
            preserve_requested_topic_as_secondary=preserve_requested_topic_as_secondary,
        )
        return TopicRoutingResult(
            requested_topic=result.requested_topic,
            effective_topic=result.effective_topic,
            secondary_topics=result.secondary_topics,
            topic_adjusted=result.topic_adjusted,
            confidence=result.confidence,
            reason=result.reason,
            topic_notice=result.topic_notice,
            mode=result.mode,
            subtopic_search_keywords=override_keywords,
        )

    scores = _score_topic_keywords(message)
    if not scores:
        return None
    ranked = sorted(scores.items(), key=lambda item: int(item[1]["score"]), reverse=True)
    top_topic, top_data = ranked[0]
    second_score = int(ranked[1][1]["score"]) if len(ranked) > 1 else 0
    top_score = int(top_data["score"])
    strong_hits = list(top_data.get("strong_hits", []))
    weak_hits = list(top_data.get("weak_hits", []))
    dominant = (
        top_score >= 5
        or (strong_hits and top_score >= 4)
        or (top_score >= 3 and top_score - second_score >= 2)
    )
    if not dominant:
        return None
    return _build_rule_result(
        requested_topic=requested_topic,
        effective_topic=top_topic,
        score=top_score,
        strong_hits=strong_hits,
        weak_hits=weak_hits,
        preserve_requested_topic_as_secondary=preserve_requested_topic_as_secondary,
    )


def _should_attempt_llm(message: str, requested_topic: str | None) -> bool:
    scores = _score_topic_keywords(message)
    if len(scores) >= 2:
        return True
    if not scores:
        return False
    only_topic = next(iter(scores.keys()))
    return only_topic != requested_topic


def _build_classifier_prompt(*, message: str, requested_topic: str | None, pais: str) -> str:
    supported_topics = ", ".join(_SUPPORTED_TOPICS)
    return (
        "Eres un clasificador de tema para un asistente contable y legal en Colombia.\n"
        "Tu trabajo es decidir el tema principal de la consulta y opcionalmente temas secundarios.\n"
        "Responde SOLO JSON valido con esta forma exacta:\n"
        '{"primary_topic":"...", "secondary_topics":["..."], "confidence":0.0, "reason":"..."}\n'
        "Reglas:\n"
        f"- primary_topic debe ser uno de: {supported_topics}, o cadena vacia si no hay tema dominante.\n"
        "- secondary_topics debe contener cero a tres temas validos, sin repetir primary_topic.\n"
        "- Si la consulta es ambigua o no es claramente de otro tema, conserva el requested_topic cuando exista.\n"
        "- Si no existe requested_topic y no hay tema dominante, devuelve primary_topic vacio y confidence baja.\n"
        "- Solo cambia de tema si el dominio dominante es claro.\n"
        "- No inventes temas fuera de la lista.\n"
        f"Pais: {pais}\n"
        f"requested_topic: {requested_topic or 'none'}\n"
        f"consulta: {message}\n"
    )


def _safe_json_dict(raw: str) -> dict[str, Any]:
    cleaned = str(raw or "").strip()
    if not cleaned:
        return {}
    try:
        parsed = json.loads(cleaned)
        return dict(parsed) if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if not match:
            return {}
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}
        return dict(parsed) if isinstance(parsed, dict) else {}


def _classify_topic_with_llm(
    *,
    message: str,
    requested_topic: str | None,
    pais: str,
    runtime_config_path: Path,
    preserve_requested_topic_as_secondary: bool = True,
) -> TopicRoutingResult | None:
    adapter, runtime = resolve_llm_adapter(runtime_config_path=runtime_config_path)
    if adapter is None:
        return None
    prompt = _build_classifier_prompt(message=message, requested_topic=requested_topic, pais=pais)
    try:
        if hasattr(adapter, "generate_with_options"):
            result = adapter.generate_with_options(  # type: ignore[attr-defined]
                prompt,
                temperature=0.0,
                max_tokens=180,
                timeout_seconds=8.0,
            )
            raw_content = str((result or {}).get("content") or "").strip()
        else:
            raw_content = str(adapter.generate(prompt) or "").strip()
    except Exception:
        return None

    parsed = _safe_json_dict(raw_content)
    effective_topic = normalize_topic_key(str(parsed.get("primary_topic") or ""))
    if effective_topic not in _SUPPORTED_TOPICS:
        return None
    try:
        confidence = float(parsed.get("confidence"))
    except (TypeError, ValueError):
        confidence = 0.0
    if confidence < _LLM_CONFIDENCE_THRESHOLD:
        return None
    # Labor topic: never preserve renta as a secondary (see _build_rule_result
    # for full reasoning). Also drop any LLM-suggested secondaries that aren't
    # the labor primary itself — if the LLM thinks renta is a labor secondary,
    # the cross-domain fan-out re-pulls ET docs and reintroduces the leakage.
    if effective_topic == "laboral":
        secondary_topics: tuple[str, ...] = ()
    else:
        secondary_topics = _normalize_secondary_topics(
            parsed.get("secondary_topics") if isinstance(parsed.get("secondary_topics"), list) else (),
            requested_topic=requested_topic,
            effective_topic=effective_topic,
            preserve_requested_topic_as_secondary=preserve_requested_topic_as_secondary,
        )
    adjusted = effective_topic != requested_topic
    return TopicRoutingResult(
        requested_topic=requested_topic,
        effective_topic=effective_topic,
        secondary_topics=secondary_topics,
        topic_adjusted=adjusted,
        confidence=min(1.0, max(0.0, confidence)),
        reason=str(parsed.get("reason") or "llm_topic_classifier"),
        topic_notice=_build_topic_notice(effective_topic) if adjusted else None,
        mode="llm",
        llm_runtime=runtime,
    )


def resolve_chat_topic(
    *,
    message: str,
    requested_topic: str | None,
    pais: str = "colombia",
    runtime_config_path: Path | str | None = None,
    preserve_requested_topic_as_secondary: bool = True,
) -> TopicRoutingResult:
    normalized_requested = normalize_topic_key(requested_topic)
    rule_result = _resolve_rule_based_topic(
        message,
        normalized_requested,
        preserve_requested_topic_as_secondary=preserve_requested_topic_as_secondary,
    )
    if rule_result is not None:
        return rule_result

    if runtime_config_path is not None and _should_attempt_llm(message, normalized_requested):
        llm_result = _classify_topic_with_llm(
            message=message,
            requested_topic=normalized_requested,
            pais=pais,
            runtime_config_path=Path(runtime_config_path),
            preserve_requested_topic_as_secondary=preserve_requested_topic_as_secondary,
        )
        if llm_result is not None:
            return llm_result

    if normalized_requested is None:
        scores = _score_topic_keywords(message)
        if scores:
            ranked = sorted(scores.items(), key=lambda item: int(item[1]["score"]), reverse=True)
            top_topic, top_data = ranked[0]
            top_score = int(top_data.get("score", 0) or 0)
            confidence = min(0.55, 0.18 + top_score * 0.06)
            return TopicRoutingResult(
                requested_topic=None,
                effective_topic=top_topic,
                secondary_topics=(),
                topic_adjusted=True,
                confidence=confidence,
                reason="fallback:auto_detected_from_keywords",
                topic_notice=_build_topic_notice(top_topic),
                mode="fallback",
            )
        return TopicRoutingResult(
            requested_topic=None,
            effective_topic=None,
            secondary_topics=(),
            topic_adjusted=False,
            confidence=0.0,
            reason="fallback:no_topic_detected",
            topic_notice=None,
            mode="fallback",
        )

    return TopicRoutingResult(
        requested_topic=normalized_requested,
        effective_topic=normalized_requested,
        secondary_topics=(),
        topic_adjusted=False,
        confidence=0.0,
        reason="fallback:requested_topic_retained",
        topic_notice=None,
        mode="fallback",
    )
