"""Unit tests for `lia_graph.ui_chunk_relevance`.

Locks in the behavior that matters for the source-view and citation-profile
pipelines: intent detection, citation-aware sentence splitting, relevance
scoring, and diverse-chunk selection. These replaced inlined copies that
used to live in `ui_text_utilities.py`.
"""

from __future__ import annotations

from lia_graph.ui_chunk_relevance import (
    _SUMMARY_INTENT_KEYWORDS,
    _SUMMARY_STOPWORDS,
    _detect_intent_tags,
    _first_substantive_sentence,
    _looks_like_reference_list,
    _pick_summary_sentences,
    _sanitize_question_context,
    _score_chunk_relevance,
    _select_diverse_chunks,
    _split_sentences,
    _tokenize_relevance_text,
)


def test_sanitize_question_context_collapses_whitespace() -> None:
    assert _sanitize_question_context("  hello\n\tworld  ") == "hello world"
    assert _sanitize_question_context("a" * 500, max_chars=10) == "aaaaaaaaaa"
    assert _sanitize_question_context(None) == ""


def test_tokenize_drops_stopwords_and_lowercases() -> None:
    tokens = _tokenize_relevance_text("La Reforma de la Ley 1819 De 2016 en Colombia")
    assert "la" not in tokens
    assert "de" not in tokens
    assert "en" not in tokens
    assert "reforma" in tokens
    assert "ley" in tokens
    assert "1819" in tokens


def test_detect_intent_tags_matches_known_keywords() -> None:
    assert _detect_intent_tags("¿Cuáles son los requisitos para presentar la declaración?") >= {
        "requisitos",
        "procedimiento",
    }
    assert _detect_intent_tags("El plazo vence el 15 de abril") == {"plazos"}
    assert _detect_intent_tags("una frase normal") == set()


def test_split_sentences_protects_citation_abbreviations() -> None:
    text = (
        "El art. 290 del ET fue modificado por la Ley 1819 de 2016. "
        "Según el num. 3 del art. 123, el régimen de transición aplica a los activos pendientes por amortizar."
    )
    sentences = _split_sentences(text)
    # Must NOT break on "art." or "num." — the abbreviation is protected.
    assert len(sentences) == 2
    assert "art. 290" in sentences[0].lower()
    assert "num. 3" in sentences[1].lower()


def test_split_sentences_filters_short_and_reference_dense() -> None:
    text = (
        "Ok. "
        "Véase también art. 1, ley 100, decreto 1625, resolución 8, concepto 6083 y radicado 9 para más contexto detallado en extenso al respecto."
    )
    sentences = _split_sentences(text)
    # Short "Ok." dropped; reference-list-dense sentence dropped.
    assert sentences == []


def test_looks_like_reference_list() -> None:
    dense = "ver art. 1, ley 100, decreto 1625, resolución 8, concepto 6083" + ("x" * 100)
    assert _looks_like_reference_list(dense) is True
    assert _looks_like_reference_list("Esta es una frase normal sobre el Art. 290.") is False


def test_score_chunk_relevance_rewards_heading_and_body_overlap() -> None:
    query_profile = {
        "q_tokens": ["regimen", "transicion", "amortizar"],
        "cq_tokens": ["ley", "1819"],
        "intent_tags": {"procedimiento"},
        "need_examples": False,
    }
    chunk = {
        "heading": "Régimen de transición",
        "text": "La regla de amortizar los saldos pendientes se aplica según la Ley 1819.",
        "intent_tags": ["procedimiento"],
    }
    result = _score_chunk_relevance(chunk, query_profile=query_profile)
    assert result["score"] > 0
    assert result["intent_overlap"] == 1


def test_score_chunk_relevance_penalizes_exercise_when_not_requested() -> None:
    query_profile = {
        "q_tokens": ["patrimonio"],
        "cq_tokens": [],
        "intent_tags": set(),
        "need_examples": False,
    }
    base = {"heading": "Patrimonio", "text": "El patrimonio se calcula...", "intent_tags": []}
    exercise = {**base, "is_exercise_chunk": True}
    plain_score = _score_chunk_relevance(base, query_profile=query_profile)["score"]
    exercise_score = _score_chunk_relevance(exercise, query_profile=query_profile)["score"]
    assert exercise_score < plain_score


def test_score_chunk_relevance_empty_query_returns_zero() -> None:
    result = _score_chunk_relevance(
        {"heading": "X", "text": "Y"},
        query_profile={"q_tokens": [], "cq_tokens": [], "intent_tags": []},
    )
    assert result == {"score": 0.0, "intent_overlap": 0}


def test_select_diverse_chunks_prefers_top_scoring_unique_headings() -> None:
    a = {"heading": "Régimen", "text": "uno", "signature": "sig-a"}
    b = {"heading": "Régimen", "text": "dos", "signature": "sig-a"}  # dup signature
    c = {"heading": "Amortización", "text": "tres", "signature": "sig-c"}
    rows = [
        {"chunk": a, "score": 3.0, "index": 0},
        {"chunk": b, "score": 2.5, "index": 1},
        {"chunk": c, "score": 1.0, "index": 2},
    ]
    selected = _select_diverse_chunks(scored_rows=rows, chunks=[a, b, c], max_items=3)
    signatures = {ch["signature"] for ch in selected}
    assert signatures == {"sig-a", "sig-c"}


def test_select_diverse_chunks_falls_back_when_nothing_scores() -> None:
    a = {"heading": "H", "text": "t", "signature": "s"}
    selected = _select_diverse_chunks(scored_rows=[], chunks=[a], max_items=3)
    # Fallback kicks in so the renderer never gets an empty selection.
    assert selected == [a]


def test_pick_summary_sentences_respects_need_examples_flag() -> None:
    chunks = [
        {
            "text": "Esta es la primera frase que describe el régimen de transición aplicable al ET. "
                    "Las pérdidas fiscales originadas antes de la reforma tienen un tratamiento especial.",
            "is_exercise_chunk": True,
        }
    ]
    without = _pick_summary_sentences(chunks, query_profile={"need_examples": False})
    assert without == []

    with_examples = _pick_summary_sentences(chunks, query_profile={"need_examples": True})
    assert len(with_examples) >= 1


def test_first_substantive_sentence_skips_short_leads() -> None:
    text = (
        "Ok. "
        "Este artículo regula el régimen de transición para los contribuyentes del ET. "
        "Más detalles aparecen abajo."
    )
    first = _first_substantive_sentence(text)
    assert first.startswith("Este artículo")


def test_constants_are_stable() -> None:
    assert "procedimiento" in _SUMMARY_INTENT_KEYWORDS
    assert "requisitos" in _SUMMARY_INTENT_KEYWORDS
    assert "de" in _SUMMARY_STOPWORDS
    assert "la" in _SUMMARY_STOPWORDS
