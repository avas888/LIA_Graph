"""v16 (2026-05-14) — firmeza ordinaria (art. 714 ET)."""
from __future__ import annotations

from ..case_detectors import is_firmeza_declaraciones_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="firmeza_declaraciones",
    detector=is_firmeza_declaraciones_case,
    bullets=(
        "**Regla general (art. 714 ET):** la declaración queda en firme a los **3 años** contados desde el **vencimiento del plazo para declarar** (si se presentó dentro del plazo). Pasado ese término sin requerimiento especial notificado, la DIAN pierde la facultad de revisar.",
        "**Presentación extemporánea:** los **3 años** se cuentan desde la **fecha de presentación**, no desde el vencimiento. Presentar tarde alarga la exposición efectiva.",
        "**Pérdidas fiscales — regla especial:** si la declaración determina pérdida fiscal, la firmeza es de **5 años** desde el vencimiento (o presentación si extemporánea). Si en años posteriores se compensa esa pérdida (art. 147 ET), **la declaración del año en que se compensa también queda en firme a los 5 años**.",
        "**Corrección voluntaria (art. 588 ET):** una corrección **reinicia** el cómputo del plazo desde la fecha de la corrección — no extiende el plazo original.",
        "**Suspensión por requerimiento especial:** la notificación del requerimiento (art. 703 ET) suspende la firmeza y abre el proceso de determinación oficial. Si la DIAN no notifica dentro del plazo del art. 705 ET, la declaración queda en firme automáticamente.",
        "**IVA, retención, autorretención:** el art. 714 ET aplica a **todas** las declaraciones tributarias administradas por la DIAN — renta, IVA, retención, GMF. La firmeza se cuenta declaración por declaración.",
        "**Beneficio de auditoría:** cuando aplica el art. 689-3 ET, la firmeza puede reducirse a **6 o 12 meses**. Conservar soporte hasta firmeza + 1 año adicional (la práctica recomendada).",
    ),
    keywords=(
        "firmeza", "firme",
        "714", "689-3", "147", "703", "705", "706", "588", "632",
        "3 años", "tres años", "tres anos",
        "5 años", "cinco años", "cinco anos",
        "declaración", "declaracion",
        "declaraciones",
        "requerimiento especial", "requerimiento",
        "corrección", "correccion",
        "pérdida fiscal", "perdida fiscal",
        "pérdidas fiscales", "perdidas fiscales",
        "compensación", "compensacion",
        "extemporánea", "extemporanea",
        "vencimiento del plazo", "plazo para declarar",
        "fiscalización", "fiscalizacion",
        "renta", "iva", "retención", "retencion",
        "beneficio de auditoría", "beneficio de auditoria",
    ),
    anchor_articles=("714",),
    search_queries=(
        "firmeza ordinaria declaraciones tributarias art 714 et 3 años",
        "firmeza 5 años perdidas fiscales art 147 art 714 et",
    ),
    source_label="firmeza_declaraciones_anchor",
)
