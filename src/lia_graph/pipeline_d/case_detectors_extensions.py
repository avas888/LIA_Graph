"""v16 b3 + b4 (2026-05-14) — case detectors for procedimiento, IVA,
retención, exógena, NIIF case-bullet topics.

Extracted from ``case_detectors.py`` to keep that file under the
1000-LOC ceiling per the divide-and-conquer rule. Re-exported by
``case_detectors`` (the facade) so existing call sites continue to
import ``from .case_detectors import is_<topic>_case`` unchanged.

Detectors here remain **pure** — only ``re`` and types. Adding imports
from any ``answer_*`` / ``planner`` module reintroduces the circular
import that v15.5 broke.
"""
from __future__ import annotations

import re


def is_sancion_extemporaneidad_case(normalized_message: str) -> bool:
    """v16 b3 — sanción por extemporaneidad (art. 641 ET)."""
    if not normalized_message:
        return False
    markers = (
        "extemporaneidad",
        "extemporánea",
        "extemporanea",
        "presentar tarde",
        "presento tarde",
        "presentación tardía",
        "presentacion tardia",
        "art. 641",
        "art 641",
        "art. 642",
        "art 642",
        "sancion por presentar tarde",
        "sanción por presentar tarde",
    )
    if any(marker in normalized_message for marker in markers):
        return True
    if "sancion" in normalized_message or "sanción" in normalized_message:
        if "tarde" in normalized_message or "tardia" in normalized_message or "tardía" in normalized_message:
            return True
    return False


def is_sancion_correccion_case(normalized_message: str) -> bool:
    """v16 b3 — sanción por corrección (art. 644 ET)."""
    if not normalized_message:
        return False
    markers = (
        "sanción por corrección",
        "sancion por correccion",
        "sancion correccion",
        "sanción corrección",
        "corregir la declaración",
        "corregir la declaracion",
        "corregir la renta",
        "art. 644",
        "art 644",
        "art. 588",
        "art 588",
        "art. 589",
        "art 589",
    )
    return any(marker in normalized_message for marker in markers)


def is_sancion_inexactitud_case(normalized_message: str) -> bool:
    """v16 b3 — sanción por inexactitud (art. 647 ET)."""
    if not normalized_message:
        return False
    markers = (
        "inexactitud",
        "art. 647",
        "art 647",
        "art. 648",
        "art 648",
        "omisión de ingresos",
        "omision de ingresos",
        "omisión de activos",
        "omision de activos",
        "pasivos inexistentes",
        "diferencia razonable de criterio",
        "diferencia de criterio",
    )
    return any(marker in normalized_message for marker in markers)


def is_notificaciones_electronicas_case(normalized_message: str) -> bool:
    """v16 b3 — notificaciones electrónicas DIAN (art. 566-1 ET).

    v16 b3 hotfix (2026-05-14): broadened to catch natural verb forms
    (``notifica``, ``notificó``, ``notificar``, ``notificada``,
    ``notificado``) combined with DIAN-context cues. The original detector
    only matched ``notificación`` / ``notificaciones`` (noun forms), so
    questions like "¿cómo me notifica la DIAN ahora?" fell through, the
    topic router pulled unrelated chunks (``sector_infancia``), and the
    safety abstention layer refused to answer.
    """
    if not normalized_message:
        return False
    markers = (
        "notificación electrónica",
        "notificacion electronica",
        "notificaciones electrónicas",
        "notificaciones electronicas",
        "buzón electrónico",
        "buzon electronico",
        "art. 566-1",
        "art 566-1",
        "566-1",
        "correo de la dian",
        "correo del rut",
        "notificación dian",
        "notificacion dian",
        "notificaciones dian",
    )
    if any(marker in normalized_message for marker in markers):
        return True
    # Noun + DIAN-context cue (legacy path)
    if "notificación" in normalized_message or "notificacion" in normalized_message:
        if "dian" in normalized_message or "rut" in normalized_message or "correo" in normalized_message:
            return True
    # Verb / participle forms + DIAN-context cue
    verb_markers = (
        "notifica",
        "notifico",
        "notificó",
        "notificar",
        "notificada",
        "notificadas",
        "notificado",
        "notificados",
    )
    if any(verb in normalized_message for verb in verb_markers):
        context_cues = (
            "dian",
            "rut",
            "correo",
            "buzón",
            "buzon",
            "resolución",
            "resolucion",
            "requerimiento",
            "emplazamiento",
            "liquidación oficial",
            "liquidacion oficial",
            "muisca",
        )
        if any(cue in normalized_message for cue in context_cues):
            return True
    return False


def is_iva_hecho_generador_case(normalized_message: str) -> bool:
    """v16 b3 — hecho generador del IVA (arts. 420 y 421 ET)."""
    if not normalized_message:
        return False
    markers = (
        "hecho generador del iva",
        "hechos generadores del iva",
        "hecho generador iva",
        "art. 420",
        "art 420",
        "art. 421",
        "art 421",
        "art. 429",
        "art 429",
        "causación del iva",
        "causacion del iva",
        "qué grava el iva",
        "que grava el iva",
        "retiro de inventario",
    )
    if any(marker in normalized_message for marker in markers):
        return True
    if "iva" in normalized_message and (
        "genera" in normalized_message or "causa" in normalized_message
    ):
        return True
    return False


def is_iva_responsables_case(normalized_message: str) -> bool:
    """v16 b3 — responsables y no responsables de IVA (art. 437 ET)."""
    if not normalized_message:
        return False
    markers = (
        "responsable de iva",
        "responsables de iva",
        "no responsable de iva",
        "no responsable iva",
        "régimen común",
        "regimen comun",
        "régimen simplificado",
        "regimen simplificado",
        "art. 437",
        "art 437",
        "art. 437-1",
        "art 437-1",
        "art. 437-2",
        "art 437-2",
        "art. 508-1",
        "art. 508-2",
        "3.500 uvt",
        "3500 uvt",
        "agente de retención de iva",
        "agente de retencion de iva",
    )
    return any(marker in normalized_message for marker in markers)


def is_iva_descontable_case(normalized_message: str) -> bool:
    """v16 b3 — IVA descontable y prorrateo (arts. 488-491 ET)."""
    if not normalized_message:
        return False
    markers = (
        "iva descontable",
        "iva en compras",
        "descontar el iva",
        "descontar iva",
        "prorrateo del iva",
        "prorrateo iva",
        "proporcionalidad del iva",
        "proporcionalidad iva",
        "art. 488",
        "art 488",
        "art. 489",
        "art 489",
        "art. 490",
        "art 490",
        "art. 491",
        "art 491",
        "art. 496",
        "art 496",
    )
    return any(marker in normalized_message for marker in markers)


def is_iva_devolucion_case(normalized_message: str) -> bool:
    """v16 b3 — devolución de saldos a favor en IVA (art. 481 ET)."""
    if not normalized_message:
        return False
    markers = (
        "devolución del iva",
        "devolucion del iva",
        "devolución de iva",
        "devolucion de iva",
        "saldo a favor en iva",
        "saldos a favor en iva",
        "saldo a favor del iva",
        "saldo a favor de iva",
        "art. 481",
        "art 481",
        "iva exportadores",
        "iva al exportador",
        "iva para exportadores",
    )
    if any(marker in normalized_message for marker in markers):
        return True
    if "iva" in normalized_message and (
        "devol" in normalized_message
        or ("saldo a favor" in normalized_message)
    ):
        return True
    return False


def is_iva_excluidos_exentos_case(normalized_message: str) -> bool:
    """v16 b3 — bienes excluidos vs exentos del IVA (arts. 424, 476, 477 ET)."""
    if not normalized_message:
        return False
    markers = (
        "excluidos del iva",
        "exentos del iva",
        "excluidos vs exentos",
        "exentos vs excluidos",
        "bienes excluidos",
        "bienes exentos",
        "servicios excluidos",
        "servicios exentos",
        "art. 424",
        "art 424",
        "art. 476",
        "art 476",
        "art. 477",
        "art 477",
        "art. 478",
        "art 478",
        "tarifa 0%",
        "tarifa 0 %",
        "tarifa cero",
    )
    if any(marker in normalized_message for marker in markers):
        return True
    if ("excluido" in normalized_message or "exento" in normalized_message) and "iva" in normalized_message:
        return True
    return False


def is_retencion_salarios_case(normalized_message: str) -> bool:
    """v16 b3 — retención en la fuente por salarios (art. 383 ET)."""
    if not normalized_message:
        return False
    markers = (
        "retención por salarios",
        "retencion por salarios",
        "retención de salarios",
        "retencion de salarios",
        "retención salarios",
        "retencion salarios",
        "retención laboral",
        "retencion laboral",
        "procedimiento 1",
        "procedimiento 2",
        "art. 383",
        "art 383",
        "art. 385",
        "art 385",
        "art. 386",
        "art 386",
        "art. 387",
        "art 387",
        "art. 388",
        "art 388",
        "art. 206",
        "art 206",
        "tabla 383",
        "tabla del 383",
    )
    if any(marker in normalized_message for marker in markers):
        return True
    if ("retención" in normalized_message or "retencion" in normalized_message) and (
        "salario" in normalized_message or "nómina" in normalized_message or "nomina" in normalized_message
    ):
        return True
    return False


def is_retencion_servicios_case(normalized_message: str) -> bool:
    """v16 b4 — retención por servicios y honorarios (art. 392 ET)."""
    if not normalized_message:
        return False
    markers = (
        "retención por servicios", "retencion por servicios",
        "retención de servicios", "retencion de servicios",
        "retención por honorarios", "retencion por honorarios",
        "retención de honorarios", "retencion de honorarios",
        "retención por comisiones", "retencion por comisiones",
        "honorarios y servicios",
        "art. 392", "art 392",
        "tarifa honorarios", "tarifa servicios",
        "servicios técnicos", "servicios tecnicos",
        "3.300 uvt", "3300 uvt",
    )
    if any(marker in normalized_message for marker in markers):
        return True
    if ("retención" in normalized_message or "retencion" in normalized_message) and (
        "honorario" in normalized_message or "servicio" in normalized_message or "comisi" in normalized_message
    ):
        return True
    return False


def is_anticipo_renta_case(normalized_message: str) -> bool:
    """v16 b4 — anticipo del impuesto de renta (arts. 807, 809 ET)."""
    if not normalized_message:
        return False
    markers = (
        "anticipo de renta",
        "anticipo del impuesto de renta",
        "anticipo del impuesto",
        "anticipo de impuesto de renta",
        "anticipo renta",
        "art. 807", "art 807",
        "art. 809", "art 809",
        "art. 808", "art 808",
        "reducción del anticipo", "reduccion del anticipo",
    )
    if any(marker in normalized_message for marker in markers):
        return True
    if "anticipo" in normalized_message and "renta" in normalized_message:
        return True
    return False


def is_soporte_factura_case(normalized_message: str) -> bool:
    """v16 b4 — soporte FE / documento soporte (arts. 771-2, 616-1 ET)."""
    if not normalized_message:
        return False
    markers = (
        "factura electrónica", "factura electronica",
        "fev",
        "documento soporte",
        "documento equivalente",
        "art. 771-2", "art 771-2",
        "art. 616-1", "art 616-1",
        "cufe",
        "resolución 000165", "resolucion 000165",
        "resolución 165 de 2023", "resolucion 165 de 2023",
        "no obligados a facturar",
        "soporte fiscal",
        "soporte documental",
    )
    if any(marker in normalized_message for marker in markers):
        return True
    if "factura" in normalized_message and (
        "deduc" in normalized_message or "soporte" in normalized_message or "electron" in normalized_message
    ):
        return True
    return False


def is_compensacion_perdidas_fiscales_case(normalized_message: str) -> bool:
    """v16 b4 — compensación de pérdidas fiscales (art. 147 ET)."""
    if not normalized_message:
        return False
    markers = (
        "compensación de pérdidas", "compensacion de perdidas",
        "compensar pérdidas", "compensar perdidas",
        "compensación de pérdida", "compensacion de perdida",
        "pérdidas fiscales", "perdidas fiscales",
        "pérdida fiscal", "perdida fiscal",
        "art. 147", "art 147",
        "12 períodos gravables", "12 periodos gravables",
        "art. 290 num. 5", "art 290 num 5",
        "régimen de transición pérdidas", "regimen de transicion perdidas",
    )
    return any(marker in normalized_message for marker in markers)


def is_exogena_1001_case(normalized_message: str) -> bool:
    """v16 b4 — Formato 1001 pagos terceros (Res. DIAN 000162/2023 art. 17)."""
    if not normalized_message:
        return False
    markers = (
        "formato 1001",
        "1001",
        "pagos a terceros",
        "exógena 1001", "exogena 1001",
        "concepto 5001", "concepto 5002", "concepto 5004", "concepto 5005",
    )
    if any(marker in normalized_message for marker in markers):
        return True
    if "exógena" in normalized_message or "exogena" in normalized_message:
        if "pago" in normalized_message or "terceros" in normalized_message:
            return True
    return False


def is_exogena_1003_case(normalized_message: str) -> bool:
    """v16 b4 — Formato 1003 retenciones (Res. DIAN 000162/2023 art. 19)."""
    if not normalized_message:
        return False
    markers = (
        "formato 1003",
        "1003",
        "exógena 1003", "exogena 1003",
        "retenciones practicadas",
        "concepto 1301", "concepto 1302", "concepto 1303", "concepto 1304",
        "concepto 1331",
    )
    if any(marker in normalized_message for marker in markers):
        return True
    if ("exógena" in normalized_message or "exogena" in normalized_message) and (
        "retencion" in normalized_message or "retención" in normalized_message
    ):
        return True
    return False


def is_exogena_1005_case(normalized_message: str) -> bool:
    """v16 b4 — Formato 1005 IVA descontable (Res. DIAN 000162/2023 art. 21)."""
    if not normalized_message:
        return False
    markers = (
        "formato 1005",
        "1005",
        "exógena 1005", "exogena 1005",
        "iva descontable exógena", "iva descontable exogena",
        "reporte iva descontable",
    )
    if any(marker in normalized_message for marker in markers):
        return True
    if ("exógena" in normalized_message or "exogena" in normalized_message) and "iva" in normalized_message:
        return True
    return False


def is_exogena_1007_case(normalized_message: str) -> bool:
    """v16 b4 — Formato 1007 ingresos (Res. DIAN 000162/2023 art. 23)."""
    if not normalized_message:
        return False
    markers = (
        "formato 1007",
        "1007",
        "exógena 1007", "exogena 1007",
        "reporte de ingresos",
        "concepto 4001", "concepto 4002", "concepto 4003",
    )
    if any(marker in normalized_message for marker in markers):
        return True
    if ("exógena" in normalized_message or "exogena" in normalized_message) and "ingreso" in normalized_message:
        return True
    return False


def is_exogena_umbrales_case(normalized_message: str) -> bool:
    """v16 b4 — exógena umbrales y plazos AG (Res. DIAN 000162/2023)."""
    if not normalized_message:
        return False
    markers = (
        "umbrales exógena", "umbrales exogena",
        "plazos exógena", "plazos exogena",
        "información exógena", "informacion exogena",
        "exógena ag", "exogena ag",
        "obligado a presentar exógena", "obligado a presentar exogena",
        "obligados a exógena", "obligados a exogena",
        "res. dian 000162", "res dian 000162",
        "resolución 000162", "resolucion 000162",
        "calendario exógena", "calendario exogena",
        "vencimiento exógena", "vencimiento exogena",
        "art. 651", "art 651",
        "sanción por no enviar", "sancion por no enviar",
    )
    if any(marker in normalized_message for marker in markers):
        return True
    if "exógena" in normalized_message or "exogena" in normalized_message:
        if "plazo" in normalized_message or "umbral" in normalized_message or "vencim" in normalized_message:
            return True
    return False


def is_niif_conciliacion_fiscal_case(normalized_message: str) -> bool:
    """v16 b4 — conciliación fiscal F2516 / F2517 (art. 772-1 ET)."""
    if not normalized_message:
        return False
    markers = (
        "conciliación fiscal", "conciliacion fiscal",
        "f2516",
        "f2517",
        "formato 2516", "formato 2517",
        "2516", "2517",
        "art. 772-1", "art 772-1",
        "772-1",
        "diferencia temporaria", "diferencia permanente",
        "diferencias temporarias", "diferencias permanentes",
        "impuesto diferido",
        "estado de resultados integral",
        "niif vs fiscal",
        "niif vs et",
    )
    return any(marker in normalized_message for marker in markers)
