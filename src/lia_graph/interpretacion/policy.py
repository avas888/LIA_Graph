from __future__ import annotations

EXPERT_PANEL_TOP_K = 12
EXPERT_PANEL_PROCESS_LIMIT = 5
EXPERT_PANEL_LOAD_MORE_LIMIT = 3
EXPERT_PANEL_MIN_RELEVANCE_SCORE = 0.22
EXPERT_PANEL_SOURCE_DIVERSITY_VISIBLE_COUNT = 5
EXPERT_PANEL_SOURCE_DIVERSITY_MAX_DIAN = 2
EXPERT_PANEL_ENHANCE_MAX_CARDS = 5
EXPERT_PANEL_EXPLORE_MAX_SNIPPETS = 8

CITATION_INTERPRETATIONS_DEFAULT_TOP_K = 8
CITATION_INTERPRETATIONS_MAX_TOP_K = 20
CITATION_INTERPRETATIONS_DEFAULT_PROCESS_LIMIT = 5

INTERPRETATION_SUMMARY_FALLBACK_MODE = "extractive_fallback"
EXPERT_PANEL_EXPLORE_FALLBACK_MODE = "deterministic_fallback"
EXPERT_PANEL_ENHANCE_FALLBACK_MODE = "deterministic_fallback"


def build_interpretation_summary_prompt(
    *,
    citation_label: str,
    interpretation_title: str,
    message_context: str,
    selected_external_link: str,
    corpus_excerpt: str,
) -> str:
    return (
        "Eres revisor tributario senior para contadores en Colombia.\n"
        "Debes resumir solo con evidencia del corpus incluido.\n"
        "Si algo no aparece en el corpus, escribe exactamente: `No evidenciado en el corpus`.\n\n"
        f"Norma citada: {citation_label}\n"
        f"Documento interpretativo: {interpretation_title}\n"
        f"Contexto adicional: {message_context or 'N/A'}\n"
        f"Link externo seleccionado: {selected_external_link or 'N/A'}\n\n"
        "Responde en markdown con secciones exactas:\n"
        "## Lectura profesional\n"
        "## Impacto operativo para contador\n"
        "## Riesgos y controversias\n"
        "## Contraste contra norma citada\n"
        "## Checklist de verificacion\n\n"
        "CORPUS:\n"
        f"{corpus_excerpt}\n"
    )


def build_expert_enhance_prompt(
    *,
    clipped_message: str,
    clipped_answer: str,
    cards_context: str,
) -> str:
    return (
        "Eres revisor tributario senior para contadores en Colombia.\n"
        "Tu tarea: para cada tarjeta de interpretación experta, genera TRES campos personalizados "
        "según la consulta del usuario y la respuesta principal de LIA.\n\n"
        "Campos por tarjeta:\n"
        "- es_relevante: booleano (true/false). true SOLO si la interpretación aborda directamente "
        "el punto tributario que el usuario preguntó. Si dudas entre relevante y no relevante, prefiere false.\n"
        "- posible_relevancia: específica y concreta al caso del usuario. "
        "Si es_relevante es false, explica brevemente por qué NO aplica. Usa lenguaje directo para contador.\n"
        "- resumen_nutshell: 4-5 frases resumiendo el contenido de la interpretación, contextualizado a la consulta.\n\n"
        "Reglas estrictas:\n"
        "- No menciones nombres de proveedores, autores, títulos de documentos ni boletines.\n"
        "- Redacta en español Colombia, dirigido a un contador en ejercicio.\n"
        "- No inventes información fuera del contenido proporcionado.\n"
        "- Devuelve SOLO un JSON array válido, sin markdown ni texto adicional.\n\n"
        f"CONSULTA DEL USUARIO:\n{clipped_message}\n\n"
        f"RESPUESTA PRINCIPAL DE LIA:\n{clipped_answer or '(no disponible)'}\n\n"
        f"TARJETAS:\n{cards_context}\n\n"
        "Formato de respuesta (JSON array estricto):\n"
        "[\n"
        '  {"card_id": "...", "es_relevante": true, "posible_relevancia": "...", "resumen_nutshell": "..."},\n'
        "  ...\n"
        "]\n"
    )


def build_expert_explore_prompt(
    *,
    mode: str,
    message: str,
    assistant_answer: str,
    classification: str,
    article_ref: str,
    summary_signal: str,
    sources_block: str,
) -> str:
    if mode == "summary":
        return (
            "Eres revisor tributario senior para contadores en Colombia.\n"
            "Genera un resumen ejecutivo de 4 a 5 párrafos cortos sobre el criterio de las fuentes consultadas.\n\n"
            "Estructura obligatoria:\n"
            "- Párrafo 1: Contexto — qué se consultó y cuál es el punto tributario central.\n"
            "- Párrafo 2: Criterio principal — la postura dominante o el consenso entre fuentes.\n"
            "- Párrafo 3: Condiciones y requisitos — soportes, plazos, formalidades necesarias.\n"
            "- Párrafo 4: Riesgos y advertencias — qué puede salir mal y qué fiscaliza la DIAN.\n"
            "- Párrafo 5 (opcional): Matices o divergencias relevantes entre fuentes.\n\n"
            "Reglas estrictas:\n"
            "- No menciones nombres de proveedores, autores, títulos de documentos ni boletines.\n"
            "- Redacta en español Colombia, dirigido a un contador en ejercicio.\n"
            "- No inventes información fuera del contenido proporcionado.\n"
            "- Devuelve solo los párrafos, sin encabezados ni markdown.\n\n"
            f"Consulta del usuario: {message}\n"
            f"Respuesta principal de LIA: {assistant_answer[:2000] or '(no disponible)'}\n"
            f"Clasificación del grupo: {classification or 'N/A'}\n"
            f"Referencia normativa: {article_ref or 'N/A'}\n"
            f"Señal predominante: {summary_signal or 'N/A'}\n\n"
            f"FUENTES:\n{sources_block}\n"
        )
    return (
        "Eres revisor tributario senior para contadores en Colombia.\n"
        "Genera un documento técnico completo y bien estructurado sobre el tema tributario consultado, "
        "usando exclusivamente la evidencia de las fuentes proporcionadas.\n\n"
        "Estructura obligatoria en markdown:\n\n"
        "## Contexto y alcance\n"
        "## Análisis del criterio profesional\n"
        "## Requisitos y condiciones de aplicación\n"
        "## Riesgos tributarios y de fiscalización\n"
        "## Casos prácticos y ejemplos\n"
        "## Checklist operativo para el contador\n"
        "## Conclusión y recomendación\n\n"
        "Reglas estrictas:\n"
        "- No menciones nombres de proveedores, autores, títulos de documentos ni boletines.\n"
        "- Redacta en español Colombia, dirigido a un contador en ejercicio.\n"
        "- Usa listas numeradas y con viñetas para facilitar la lectura.\n"
        "- No inventes normas, artículos ni cifras que no estén en las fuentes.\n"
        "- Si una sección no tiene evidencia suficiente, escribe: 'No evidenciado en las fuentes consultadas.'\n\n"
        f"Consulta del usuario: {message}\n"
        f"Respuesta principal de LIA: {assistant_answer[:2000] or '(no disponible)'}\n"
        f"Clasificación del grupo: {classification or 'N/A'}\n"
        f"Referencia normativa: {article_ref or 'N/A'}\n"
        f"Señal predominante: {summary_signal or 'N/A'}\n\n"
        f"FUENTES:\n{sources_block}\n"
    )
