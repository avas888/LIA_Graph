"""Prompt builder for the rerank LLM judge.

Kept as a single tiny module so the prompt copy lives under version control
in one obvious place — same convention as `interpretacion/policy.py`'s other
`build_*_prompt` helpers.
"""

from __future__ import annotations


def build_rerank_prompt(
    *,
    question: str,
    assistant_answer: str,
    candidate_blocks: str,
    summary_max_chars: int,
) -> str:
    """JSON-only prompt: per-candidate score + question-grounded one-sentence summary.

    The summary is what fixes "card body bunching" — instead of slicing the
    document head (which can straddle two sub-articles in cluster docs), we
    ask the model to write a single sentence about *what this expert says,
    relative to the user's question*.
    """
    return (
        "Eres revisor tributario senior para contadores en Colombia.\n"
        "Tu tarea: para cada candidato (interpretación experta), produce DOS cosas:\n"
        "1. score: entero 0-100 que mide qué tan directamente responde a la consulta del usuario.\n"
        "   - 90-100: aborda exactamente el punto preguntado.\n"
        "   - 60-89: aporta criterio profesional útil sobre la norma o tema preguntado.\n"
        "   - 30-59: tangencial, menciona la norma pero el foco es otro.\n"
        "   - 0-29: irrelevante o no responde.\n"
        f"2. summary: UNA sola oración en español Colombia (máx {summary_max_chars} caracteres) "
        "que diga qué dice este experto, conectado a la consulta. NO copies el título del documento. "
        "NO mezcles varios temas. UNA idea, UNA oración.\n\n"
        "Reglas estrictas:\n"
        "- NO menciones nombres de proveedores, autores, títulos de documentos ni boletines.\n"
        "- NO inventes información fuera del extracto proporcionado.\n"
        "- Devuelve SOLO un JSON array válido, sin markdown ni texto adicional.\n"
        "- Cada objeto del array DEBE incluir doc_id exactamente como lo recibes.\n\n"
        f"CONSULTA DEL USUARIO:\n{question}\n\n"
        f"RESPUESTA PRINCIPAL DE LIA:\n{assistant_answer or '(no disponible)'}\n\n"
        f"CANDIDATOS:\n{candidate_blocks}\n\n"
        "Formato de respuesta (JSON array estricto):\n"
        "[\n"
        '  {"doc_id": "...", "score": 87, "summary": "..."},\n'
        "  ...\n"
        "]\n"
    )


def format_candidate_block(*, index: int, doc_id: str, article_refs: tuple[str, ...], excerpt: str) -> str:
    """Render one candidate block for inclusion in the prompt body.

    Refs are the article references the retrieval pass already extracted —
    surfacing them helps the model anchor its score on the right norm without
    having to re-parse the excerpt.
    """
    refs_label = ", ".join(article_refs) if article_refs else "N/A"
    return (
        f"CANDIDATO {index} (doc_id: {doc_id}):\n"
        f"  referencias normativas: {refs_label}\n"
        f"  extracto:\n  {excerpt}"
    )
