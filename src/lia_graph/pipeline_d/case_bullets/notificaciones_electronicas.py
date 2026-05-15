"""v16 b3 — notificaciones electrónicas DIAN (art. 566-1 ET)."""
from __future__ import annotations

from ..case_detectors import is_notificaciones_electronicas_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="notificaciones_electronicas",
    detector=is_notificaciones_electronicas_case,
    bullets=(
        "La **notificación electrónica al buzón electrónico registrado en el RUT** es el **medio preferente y obligatorio** para los actos de la DIAN (art. 566-1 ET, introducido por Ley 1607/2012, modificado por Ley 2010/2019 art. 95).",
        "**Fecha de notificación = quinto día hábil siguiente al envío.** La DIAN envía el acto al buzón electrónico; la notificación se entiende surtida al **5° día hábil**, independientemente de si el contribuyente abrió el mensaje. Desde ese día corren los plazos procesales.",
        "**Actos que se notifican electrónicamente:** requerimientos ordinarios (art. 684 ET); emplazamientos para corregir (art. 685 ET) y para declarar (art. 715 ET); requerimientos especiales (art. 703 ET); liquidaciones oficiales (arts. 710+ ET); resoluciones sanción; citaciones; resoluciones de devolución/compensación.",
        "**Subsidiariedad (art. 568 ET):** si la notificación electrónica falla por causa **imputable a la DIAN** (caída del sistema oficial, comprobada), se procede por otros medios. **La falla del correo del contribuyente NO es causa de subsidiariedad** — recae sobre el contribuyente.",
        "**Gestión del buzón:** correo institucional dedicado (no personal del representante); revisión **mínimo semanal**, diaria en períodos de fiscalización; reglas para correos del dominio `dian.gov.co`; actualizar inmediatamente al cambiar representante legal, contador, correo o dirección.",
        "**Defensa procesal:** única vía viable: demostrar que el correo **nunca fue registrado** en el RUT o que la DIAN envió a un correo distinto. Argumentos como \"no lo vi\", \"estaba en spam\", \"no abrí el mensaje\" **no proceden** procesalmente.",
        "**Soporte normativo adicional:** **Resolución DIAN 000038 de 2020** reglamenta la notificación electrónica; **Decreto 358 de 2020** modificó el procedimiento.",
    ),
    keywords=(
        "notificación", "notificacion",
        "notificaciones",
        "electrónica", "electronica",
        "buzón electrónico", "buzon electronico",
        "566-1", "555-2", "565", "568", "684", "685", "703", "710", "715",
        "rut",
        "muisca",
        "quinto día hábil", "quinto dia habil", "5 dia habil",
        "correo",
        "dian",
        "resolución 000038", "resolucion 000038",
        "decreto 358",
        "ley 2010",
        "apoderado",
        "fiscalización", "fiscalizacion",
        "requerimiento",
        "emplazamiento",
        "liquidación oficial", "liquidacion oficial",
    ),
    anchor_articles=("566-1",),
    search_queries=(
        "notificacion electronica dian buzon rut quinto dia habil art 566-1 et",
        "ley 2010 2019 notificacion electronica art 566-1 resolucion 000038",
    ),
    source_label="notificaciones_electronicas_anchor",
)
