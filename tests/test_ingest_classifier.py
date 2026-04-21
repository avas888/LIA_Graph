"""Unit tests for ``lia_graph.ingestion_classifier`` — AUTOGENERAR cascade.

Covers every branch described in ``docs/next/ingestfixv1.md`` §3.2 and §3.6:

  (a) each ``_FILENAME_TYPE_PATTERNS`` regex hits correctly
  (b) each ``_FILENAME_TOPIC_PATTERNS`` prefix hits
  (c) body keyword scoring via a monkeypatched ``detect_topic_from_text``
  (d) N1 combined confidence is ``min`` when both present, ``max`` otherwise
  (e) N2 fires only when N1 combined < 0.95
  (f) N2 synonym-high path
  (g) N2 synonym-medium path → is_raw=True
  (h) N2 new-topic path → combined=0.70, classification_source="llm"
  (i) post-LLM sanity: unknown ``resolved_to_existing`` flips to new
  (j) post-LLM sanity: "new" override when N1 topic confidence > 0.7
  (k) confidence fusion boundary cases 0.79 / 0.80 / 0.90 / 0.95
  (l) ``skip_llm=True`` forces N1-only, never calls adapter
  (m) ``adapter=None`` + ``resolve_llm_adapter`` returns None → graceful
  (n) malformed JSON from LLM → treated as parse failure
  (o) ``requires_review`` at the <0.95 boundary

All adapter interactions are mocked with a ``FakeAdapter`` that records
calls — no network, no filesystem.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import pytest

from lia_graph import ingestion_classifier as classifier_module
from lia_graph.ingestion_classifier import (
    AutogenerarResult,
    _apply_filename_patterns,
    _apply_post_llm_sanity,
    _build_n2_prompt,
    _fuse_autogenerar_confidence,
    _N1Result,
    _N2Result,
    _parse_n2_response,
    _run_n1_cascade,
    _slugify,
    classify_ingestion_document,
)


# ---------------------------------------------------------------------------
# Test fixtures / helpers
# ---------------------------------------------------------------------------


@dataclass
class FakeAdapter:
    """Mock LLM adapter that returns a canned JSON payload.

    When ``payload`` is a ``dict`` it is ``json.dumps``-ed before returning.
    When ``payload`` is a ``str`` it is returned verbatim (used for the
    malformed-JSON case). Records every prompt it receives in ``.calls``.
    """

    payload: Any = None
    calls: list[str] | None = None

    def __post_init__(self) -> None:
        if self.calls is None:
            self.calls = []

    def generate(self, prompt: str) -> str:
        assert self.calls is not None
        self.calls.append(prompt)
        if isinstance(self.payload, dict):
            return json.dumps(self.payload)
        return str(self.payload or "")


def _n2_payload(
    *,
    label: str = "tema generado",
    rationale: str = "fragmento coincide con tema existente",
    resolved: str | None = None,
    synonym_confidence: float = 0.0,
    is_new_topic: bool = False,
    suggested_key: str | None = None,
    detected_type: str | None = "normative_base",
) -> dict[str, Any]:
    return {
        "generated_label": label,
        "rationale": rationale,
        "resolved_to_existing": resolved,
        "synonym_confidence": synonym_confidence,
        "is_new_topic": is_new_topic,
        "suggested_key": suggested_key,
        "detected_type": detected_type,
    }


@pytest.fixture(autouse=True)
def _block_real_adapter(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure no test accidentally reaches the real ``llm_runtime``.

    ``_resolve_adapter(None)`` must return ``None`` unless a test
    explicitly monkeypatches it to return an adapter.
    """

    def _always_none(adapter: Any) -> Any | None:
        return adapter  # pass-through; tests that want None simply pass None

    monkeypatch.setattr(classifier_module, "_resolve_adapter", _always_none)


# ---------------------------------------------------------------------------
# (a) filename → type patterns
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "filename,expected_type,expected_conf",
    [
        ("interpretaciones_ley_1819.md", "interpretative_guidance", 0.97),
        ("fuentes-secundarias-dian.md", "interpretative_guidance", 0.97),
        ("marco_legal_laboral.md", "normative_base", 0.97),
        ("guia-practica-nomina.md", "practica_erp", 0.97),
        ("ET_art_107.md", "normative_base", 0.95),
        ("Ley_1819_2016.md", "normative_base", 0.95),
        ("Decreto_1625.md", "normative_base", 0.95),
        ("Res_000013_2025.md", "normative_base", 0.95),
        ("DUR_1625_titulo2.md", "normative_base", 0.95),
        ("concepto_dian_100202208.md", "interpretative_guidance", 0.85),
        ("oficio_dian_014.md", "interpretative_guidance", 0.85),
        ("L0_guia_iva.md", "practica_erp", 0.90),
        ("guia_nomina.md", "practica_erp", 0.90),
        ("plantilla_checklist.md", "practica_erp", 0.90),
        ("checklist_cierre_fiscal.md", "practica_erp", 0.90),
        ("nomina_erp_loggro.md", "practica_erp", 0.85),
        ("rev_normativa_ley_1819.md", "normative_base", 0.95),
        ("rev_expertos_dian.md", "interpretative_guidance", 0.95),
        ("rev_practica_siigo.md", "practica_erp", 0.95),
    ],
)
def test_filename_type_patterns_match(
    filename: str, expected_type: str, expected_conf: float
) -> None:
    detected_type, conf, source, _, _ = _apply_filename_patterns(filename)
    assert detected_type == expected_type
    assert conf == pytest.approx(expected_conf)
    assert source == "filename"


# ---------------------------------------------------------------------------
# (b) filename → topic prefix patterns
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "filename,expected_topic",
    [
        ("IVA-formulario-300.md", "iva"),
        ("ICA-bogota.md", "ica"),
        ("GMF-4x1000.md", "gmf"),
        ("RET-ica-bogota.md", "retencion"),
        ("NIIF-seccion-25.md", "niif"),
        ("NOM-liquidacion.md", "laboral"),
        ("FE-electronica.md", "facturacion"),
        ("EXO-informacion.md", "exogena"),
        ("RFL-reforma-laboral.md", "reforma_laboral_2466"),
        ("RST-regimen-simple.md", "rst_regimen_simple"),
        ("SAG-sagrilaft.md", "sagrilaft_ptee"),
    ],
)
def test_filename_topic_prefix_patterns_match(
    filename: str, expected_topic: str
) -> None:
    _, _, _, fn_topic, fn_conf = _apply_filename_patterns(filename)
    assert fn_topic == expected_topic
    assert fn_conf == pytest.approx(0.95)


# ---------------------------------------------------------------------------
# (c) body keyword scoring via monkeypatched topic_router
# ---------------------------------------------------------------------------


def test_body_keyword_detection_drives_n1_topic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from lia_graph.topic_router import TopicDetection

    def fake_detect(text: str, filename: str | None = None) -> TopicDetection:
        return TopicDetection(
            topic="iva", confidence=0.80, scores={"iva": 6.0}, source="keywords"
        )

    monkeypatch.setattr(
        classifier_module, "detect_topic_from_text", fake_detect
    )

    # Filename with NO prefix hints so only body keywords speak.
    n1 = _run_n1_cascade(filename="random_doc.md", body_text="IVA en Colombia")
    assert n1.detected_topic == "iva"
    assert n1.topic_source == "keywords"
    assert n1.topic_confidence == pytest.approx(0.80)


# ---------------------------------------------------------------------------
# (d) N1 combined = min when both, max when only one, 0 when neither
# ---------------------------------------------------------------------------


def test_n1_combined_min_when_both_topic_and_type(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from lia_graph.topic_router import TopicDetection

    monkeypatch.setattr(
        classifier_module,
        "detect_topic_from_text",
        lambda text, filename=None: TopicDetection(
            topic="iva", confidence=0.60, scores={}, source="keywords"
        ),
    )
    # ET_art_ → normative_base @ 0.95; body keywords → iva @ 0.60
    n1 = _run_n1_cascade(filename="ET_art_420.md", body_text="IVA body")
    assert n1.detected_topic == "iva"
    assert n1.detected_type == "normative_base"
    assert n1.combined_confidence == pytest.approx(0.60)


def test_n1_combined_max_when_only_type(monkeypatch: pytest.MonkeyPatch) -> None:
    from lia_graph.topic_router import TopicDetection

    monkeypatch.setattr(
        classifier_module,
        "detect_topic_from_text",
        lambda text, filename=None: TopicDetection(
            topic=None, confidence=0.0, scores={}, source="keywords"
        ),
    )
    n1 = _run_n1_cascade(filename="ET_art_107.md", body_text="")
    assert n1.detected_topic is None
    assert n1.detected_type == "normative_base"
    assert n1.combined_confidence == pytest.approx(0.95)


def test_n1_combined_zero_when_neither(monkeypatch: pytest.MonkeyPatch) -> None:
    from lia_graph.topic_router import TopicDetection

    monkeypatch.setattr(
        classifier_module,
        "detect_topic_from_text",
        lambda text, filename=None: TopicDetection(
            topic=None, confidence=0.0, scores={}, source="keywords"
        ),
    )
    n1 = _run_n1_cascade(filename="misc.md", body_text="no signals")
    assert n1.combined_confidence == 0.0


# ---------------------------------------------------------------------------
# (e) N2 only fires when N1 combined < 0.95
# ---------------------------------------------------------------------------


def test_n2_skipped_when_n1_confidence_at_or_above_threshold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from lia_graph.topic_router import TopicDetection

    monkeypatch.setattr(
        classifier_module,
        "detect_topic_from_text",
        lambda text, filename=None: TopicDetection(
            topic="iva", confidence=0.95, scores={}, source="keywords"
        ),
    )
    adapter = FakeAdapter(payload=_n2_payload())
    # IVA- filename prefix + iva body both at 0.95 → combined 0.95.
    result = classify_ingestion_document(
        filename="IVA-formulario-300.md",
        body_text="texto de iva",
        adapter=adapter,
    )
    assert result.combined_confidence == pytest.approx(0.95)
    assert result.classification_source in {"keywords", "filename"}
    assert result.is_raw is False
    assert adapter.calls == []


# ---------------------------------------------------------------------------
# (f) N2 synonym-high
# ---------------------------------------------------------------------------


def test_n2_synonym_high_sets_topic_and_lowers_raw_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from lia_graph.topic_router import TopicDetection

    # N1 keywords ALSO land on "iva" (but below 0.95) so the agreement
    # boost lands; without the boost combined maxes out at 0.90 and is_raw
    # stays True. This matches plan §3.2 fusion: base 0.85 + 0.10 agree
    # + 0.05 high-syn = 1.0 → is_raw=False.
    monkeypatch.setattr(
        classifier_module,
        "detect_topic_from_text",
        lambda text, filename=None: TopicDetection(
            topic="iva", confidence=0.60, scores={}, source="keywords"
        ),
    )
    adapter = FakeAdapter(
        payload=_n2_payload(
            label="impuesto al valor agregado",
            resolved="iva",
            synonym_confidence=0.90,
            is_new_topic=False,
            detected_type="normative_base",
        )
    )
    result = classify_ingestion_document(
        filename="documento_ambiguo.md",
        body_text="texto sin senales claras",
        adapter=adapter,
    )
    assert result.resolved_to_existing == "iva"
    assert result.detected_topic == "iva"
    assert result.combined_confidence >= 0.85
    assert result.classification_source == "llm"
    assert result.is_raw is False
    assert adapter.calls  # adapter actually invoked


# ---------------------------------------------------------------------------
# (g) N2 synonym-medium forces raw
# ---------------------------------------------------------------------------


def test_n2_synonym_medium_forces_raw(monkeypatch: pytest.MonkeyPatch) -> None:
    from lia_graph.topic_router import TopicDetection

    monkeypatch.setattr(
        classifier_module,
        "detect_topic_from_text",
        lambda text, filename=None: TopicDetection(
            topic=None, confidence=0.0, scores={}, source="keywords"
        ),
    )
    adapter = FakeAdapter(
        payload=_n2_payload(
            label="quiza un tema de iva",
            resolved="iva",
            synonym_confidence=0.60,
            detected_type="normative_base",
        )
    )
    result = classify_ingestion_document(
        filename="doc_medio.md",
        body_text="texto tibio",
        adapter=adapter,
    )
    assert result.combined_confidence == 0.0
    assert result.is_raw is True
    assert result.requires_review is True


# ---------------------------------------------------------------------------
# (h) N2 new-topic → combined=0.70, classification_source="llm"
# ---------------------------------------------------------------------------


def test_n2_new_topic_sets_combined_to_seventy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from lia_graph.topic_router import TopicDetection

    monkeypatch.setattr(
        classifier_module,
        "detect_topic_from_text",
        lambda text, filename=None: TopicDetection(
            topic=None, confidence=0.0, scores={}, source="keywords"
        ),
    )
    adapter = FakeAdapter(
        payload=_n2_payload(
            label="Nuevo Tema Especifico",
            is_new_topic=True,
            suggested_key="nuevo_tema_especifico",
            detected_type="normative_base",
        )
    )
    result = classify_ingestion_document(
        filename="misterioso.md",
        body_text="contenido novedoso",
        adapter=adapter,
    )
    assert result.is_new_topic is True
    assert result.suggested_key == "nuevo_tema_especifico"
    assert result.detected_topic == "nuevo_tema_especifico"
    assert result.combined_confidence == pytest.approx(0.70)
    assert result.classification_source == "llm"
    assert result.is_raw is True


# ---------------------------------------------------------------------------
# (i) Post-LLM sanity: unknown resolved → flipped to new topic
# ---------------------------------------------------------------------------


def test_post_llm_flips_unknown_resolved_to_new_topic() -> None:
    n1 = _N1Result(
        detected_topic=None,
        topic_confidence=0.0,
        topic_source=None,
        detected_type=None,
        type_confidence=0.0,
        type_source=None,
        combined_confidence=0.0,
    )
    n2 = _N2Result(
        generated_label="Tema Inventado Por El LLM",
        rationale="…",
        resolved_to_existing="unknown_topic_key_that_is_fictional",
        synonym_confidence=0.90,
        is_new_topic=False,
        suggested_key=None,
        detected_type="normative_base",
    )
    fixed = _apply_post_llm_sanity(n2, n1)
    assert fixed.is_new_topic is True
    assert fixed.resolved_to_existing is None
    assert fixed.suggested_key == "tema_inventado_por_el_llm"


# ---------------------------------------------------------------------------
# (j) Post-LLM override: LLM says "new" but N1 topic_confidence > 0.7
# ---------------------------------------------------------------------------


def test_post_llm_override_when_n1_has_strong_topic() -> None:
    n1 = _N1Result(
        detected_topic="iva",
        topic_confidence=0.85,
        topic_source="keywords",
        detected_type="normative_base",
        type_confidence=0.95,
        type_source="filename",
        combined_confidence=0.85,
    )
    n2 = _N2Result(
        generated_label="algo novel",
        rationale="parece nuevo",
        resolved_to_existing=None,
        synonym_confidence=0.0,
        is_new_topic=True,
        suggested_key="algo_novel",
        detected_type="normative_base",
    )
    fixed = _apply_post_llm_sanity(n2, n1)
    assert fixed.is_new_topic is False
    assert fixed.resolved_to_existing == "iva"
    assert fixed.suggested_key is None
    assert fixed.synonym_confidence == pytest.approx(0.85)


# ---------------------------------------------------------------------------
# (k) Confidence fusion boundary cases 0.79 / 0.80 / 0.90 / 0.95
# ---------------------------------------------------------------------------


def _n1_empty() -> _N1Result:
    return _N1Result(
        detected_topic=None,
        topic_confidence=0.0,
        topic_source=None,
        detected_type=None,
        type_confidence=0.0,
        type_source=None,
        combined_confidence=0.0,
    )


def _n2_with_synonym(conf: float, resolved: str | None = "iva") -> _N2Result:
    return _N2Result(
        generated_label="etiqueta",
        rationale="",
        resolved_to_existing=resolved,
        synonym_confidence=conf,
        is_new_topic=False,
        suggested_key=None,
        detected_type="normative_base",
    )


def test_fusion_synonym_079_is_zero() -> None:
    assert _fuse_autogenerar_confidence(_n1_empty(), _n2_with_synonym(0.79)) == 0.0


def test_fusion_synonym_080_is_base_085() -> None:
    assert _fuse_autogenerar_confidence(
        _n1_empty(), _n2_with_synonym(0.80)
    ) == pytest.approx(0.85)


def test_fusion_synonym_090_adds_high_boost() -> None:
    # N1 has no topic → no agreement boost; only the +0.05 high-synonym boost.
    assert _fuse_autogenerar_confidence(
        _n1_empty(), _n2_with_synonym(0.90)
    ) == pytest.approx(0.90)


def test_fusion_synonym_090_with_n1_agreement() -> None:
    n1 = _N1Result(
        detected_topic="iva",
        topic_confidence=0.60,
        topic_source="keywords",
        detected_type=None,
        type_confidence=0.0,
        type_source=None,
        combined_confidence=0.60,
    )
    assert _fuse_autogenerar_confidence(
        n1, _n2_with_synonym(0.90, resolved="iva")
    ) == pytest.approx(1.0)


def test_fusion_synonym_095_capped_at_one() -> None:
    n1 = _N1Result(
        detected_topic="iva",
        topic_confidence=0.60,
        topic_source="keywords",
        detected_type=None,
        type_confidence=0.0,
        type_source=None,
        combined_confidence=0.60,
    )
    assert _fuse_autogenerar_confidence(
        n1, _n2_with_synonym(0.95, resolved="iva")
    ) == pytest.approx(1.0)


def test_fusion_new_topic_is_seventy() -> None:
    n2 = _N2Result(
        generated_label="nuevo",
        rationale="",
        resolved_to_existing=None,
        synonym_confidence=0.0,
        is_new_topic=True,
        suggested_key="nuevo",
        detected_type="normative_base",
    )
    assert _fuse_autogenerar_confidence(_n1_empty(), n2) == pytest.approx(0.70)


# ---------------------------------------------------------------------------
# (l) skip_llm=True forces N1-only
# ---------------------------------------------------------------------------


def test_skip_llm_never_calls_adapter(monkeypatch: pytest.MonkeyPatch) -> None:
    from lia_graph.topic_router import TopicDetection

    monkeypatch.setattr(
        classifier_module,
        "detect_topic_from_text",
        lambda text, filename=None: TopicDetection(
            topic=None, confidence=0.0, scores={}, source="keywords"
        ),
    )
    adapter = FakeAdapter(payload=_n2_payload())
    result = classify_ingestion_document(
        filename="doc_misterioso.md",
        body_text="bla bla",
        adapter=adapter,
        skip_llm=True,
    )
    assert adapter.calls == []
    assert result.is_raw is True
    assert result.combined_confidence == 0.0
    assert result.classification_source == "keywords"


# ---------------------------------------------------------------------------
# (m) adapter=None + resolve_llm_adapter returns None → graceful
# ---------------------------------------------------------------------------


def test_adapter_none_gracefully_degrades(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from lia_graph.topic_router import TopicDetection

    monkeypatch.setattr(
        classifier_module,
        "detect_topic_from_text",
        lambda text, filename=None: TopicDetection(
            topic=None, confidence=0.0, scores={}, source="keywords"
        ),
    )
    # Override the autouse fixture: make _resolve_adapter always return None.
    monkeypatch.setattr(
        classifier_module, "_resolve_adapter", lambda adapter: None
    )

    result = classify_ingestion_document(
        filename="unknown.md",
        body_text="nada que ver",
        adapter=None,
    )
    assert result.is_raw is True
    assert result.combined_confidence == 0.0
    assert result.classification_source == "keywords"
    assert result.generated_label is None


# ---------------------------------------------------------------------------
# (n) Malformed JSON from LLM → parse failure → is_raw=True + keywords
# ---------------------------------------------------------------------------


def test_malformed_llm_json_falls_back_to_n1(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from lia_graph.topic_router import TopicDetection

    monkeypatch.setattr(
        classifier_module,
        "detect_topic_from_text",
        lambda text, filename=None: TopicDetection(
            topic=None, confidence=0.0, scores={}, source="keywords"
        ),
    )
    adapter = FakeAdapter(payload="this is not JSON at all, just noise.")
    result = classify_ingestion_document(
        filename="ambiguo.md",
        body_text="algo",
        adapter=adapter,
    )
    assert adapter.calls  # adapter was actually called
    assert result.is_raw is True
    assert result.classification_source == "keywords"
    assert result.generated_label is None


def test_parse_n2_response_rejects_empty_generated_label() -> None:
    raw = json.dumps(
        {
            "generated_label": "",
            "resolved_to_existing": None,
            "is_new_topic": False,
        }
    )
    assert _parse_n2_response(raw) is None


def test_parse_n2_response_extracts_from_noise() -> None:
    raw = (
        "Aqui esta tu respuesta:\n\n"
        + json.dumps(_n2_payload(label="algo", resolved="iva", synonym_confidence=0.8))
        + "\n\nGracias"
    )
    parsed = _parse_n2_response(raw)
    assert parsed is not None
    assert parsed.generated_label == "algo"
    assert parsed.resolved_to_existing == "iva"


# ---------------------------------------------------------------------------
# (o) requires_review at the <0.95 boundary
# ---------------------------------------------------------------------------


def test_requires_review_flag_below_threshold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from lia_graph.topic_router import TopicDetection

    monkeypatch.setattr(
        classifier_module,
        "detect_topic_from_text",
        lambda text, filename=None: TopicDetection(
            topic=None, confidence=0.0, scores={}, source="keywords"
        ),
    )
    adapter = FakeAdapter(
        payload=_n2_payload(
            label="prestaciones sociales",
            resolved="iva",  # arbitrary valid topic key
            synonym_confidence=0.82,
            detected_type="normative_base",
        )
    )
    result = classify_ingestion_document(
        filename="doc.md",
        body_text="texto",
        adapter=adapter,
    )
    # synonym=0.82 → fused=0.85 → is_raw=True → requires_review=True.
    assert result.combined_confidence == pytest.approx(0.85)
    assert result.is_raw is True
    assert result.requires_review is True


def test_requires_review_false_above_threshold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from lia_graph.topic_router import TopicDetection

    monkeypatch.setattr(
        classifier_module,
        "detect_topic_from_text",
        lambda text, filename=None: TopicDetection(
            topic="iva", confidence=0.95, scores={}, source="keywords"
        ),
    )
    # IVA- prefix + ET_art_ filename → filename type 0.95, topic 0.95 → combined 0.95.
    result = classify_ingestion_document(
        filename="IVA-ET_art_420.md",
        body_text="texto",
        adapter=None,
        skip_llm=True,
    )
    assert result.combined_confidence == pytest.approx(0.95)
    assert result.is_raw is False
    assert result.requires_review is False


# ---------------------------------------------------------------------------
# Ancillary coverage: slugify + prompt building
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Reforma Laboral 2024", "reforma_laboral_2024"),
        ("Impuesto   al    Valor   Agregado", "impuesto_al_valor_agregado"),
        ("  Niñez  ", "ninez"),
        ("Régimen Simple de Tributación", "regimen_simple_de_tributacion"),
        ("hola-mundo", "hola_mundo"),
    ],
)
def test_slugify_normalizes_spanish_text(text: str, expected: str) -> None:
    assert _slugify(text) == expected


def test_n2_prompt_includes_topic_list_and_filename() -> None:
    prompt = _build_n2_prompt(
        filename="ejemplo.md", body_text="fragmento de prueba"
    )
    assert "ejemplo.md" in prompt
    assert "fragmento de prueba" in prompt
    assert "PASO 1" in prompt and "PASO 2" in prompt and "PASO 3" in prompt
    # topic_list_with_labels should have at least one "- key: label" line
    assert "- iva" in prompt.lower()


def test_generate_with_options_preferred_when_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from lia_graph.topic_router import TopicDetection

    monkeypatch.setattr(
        classifier_module,
        "detect_topic_from_text",
        lambda text, filename=None: TopicDetection(
            topic=None, confidence=0.0, scores={}, source="keywords"
        ),
    )

    class RichAdapter:
        def __init__(self) -> None:
            self.options_calls: list[dict[str, Any]] = []
            self.generate_calls: list[str] = []

        def generate_with_options(
            self,
            prompt: str,
            *,
            temperature: float,
            max_tokens: int,
            timeout_seconds: float,
        ) -> dict[str, str]:
            self.options_calls.append(
                {
                    "prompt": prompt,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "timeout_seconds": timeout_seconds,
                }
            )
            return {
                "content": json.dumps(
                    _n2_payload(
                        label="tema iva",
                        resolved="iva",
                        synonym_confidence=0.90,
                        detected_type="normative_base",
                    )
                )
            }

        def generate(self, prompt: str) -> str:  # pragma: no cover - defensive
            self.generate_calls.append(prompt)
            return ""

    adapter = RichAdapter()
    result = classify_ingestion_document(
        filename="doc.md", body_text="cuerpo", adapter=adapter
    )
    assert adapter.options_calls, "generate_with_options should have been preferred"
    assert adapter.generate_calls == []
    assert adapter.options_calls[0]["temperature"] == 0.0
    assert adapter.options_calls[0]["max_tokens"] == 300
    assert adapter.options_calls[0]["timeout_seconds"] == 10.0
    assert result.detected_topic == "iva"


def test_autogenerar_result_is_frozen() -> None:
    # Simple smoke test that the dataclass is immutable (frozen=True).
    result = classify_ingestion_document(
        filename="ET_art_107.md",
        body_text="articulo 107",
        skip_llm=True,
    )
    assert isinstance(result, AutogenerarResult)
    with pytest.raises((AttributeError, Exception)):
        result.detected_topic = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Phase 1 (subtopic_generationv1) — always_emit_label kwarg
# ---------------------------------------------------------------------------


def test_always_emit_label_fires_n2_when_n1_is_high_confidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """N1 already hits 0.95 but the collection pass still wants a label.

    N1's primary assignment wins (topic=iva, combined=0.95, source=filename
    or keywords), but the LLM-generated label + rationale are populated.
    """
    from lia_graph.topic_router import TopicDetection

    monkeypatch.setattr(
        classifier_module,
        "detect_topic_from_text",
        lambda text, filename=None: TopicDetection(
            topic="iva", confidence=0.95, scores={}, source="keywords"
        ),
    )
    adapter = FakeAdapter(
        payload=_n2_payload(
            label="impuesto al valor agregado aplicado",
            rationale="documento describe aplicacion de IVA en nomina",
            resolved="iva",
            synonym_confidence=0.95,
        )
    )
    result = classify_ingestion_document(
        filename="IVA-formulario-300.md",
        body_text="texto de iva",
        adapter=adapter,
        always_emit_label=True,
    )
    # N2 was invoked despite N1 at 0.95.
    assert adapter.calls, "always_emit_label should have forced N2"
    # N1 still owns the primary verdict.
    assert result.detected_topic == "iva"
    assert result.combined_confidence == pytest.approx(0.95)
    assert result.is_raw is False
    assert result.classification_source in {"keywords", "filename"}
    # Label + rationale captured as metadata.
    assert result.generated_label == "impuesto al valor agregado aplicado"
    assert result.rationale and "IVA" in result.rationale


def test_always_emit_label_false_preserves_current_behavior(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Default kwarg value — N1 high-confidence → N2 not called, label None."""
    from lia_graph.topic_router import TopicDetection

    monkeypatch.setattr(
        classifier_module,
        "detect_topic_from_text",
        lambda text, filename=None: TopicDetection(
            topic="iva", confidence=0.95, scores={}, source="keywords"
        ),
    )
    adapter = FakeAdapter(payload=_n2_payload())
    result = classify_ingestion_document(
        filename="IVA-formulario-300.md",
        body_text="texto de iva",
        adapter=adapter,
    )
    assert adapter.calls == []
    assert result.generated_label is None
    assert result.rationale is None


def test_always_emit_label_graceful_when_adapter_unresolvable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """N1 high-confidence + always_emit_label=True + adapter unresolvable →
    fall back to N1-only; classification_source stays 'keywords'/'filename'."""
    from lia_graph.topic_router import TopicDetection

    monkeypatch.setattr(
        classifier_module,
        "detect_topic_from_text",
        lambda text, filename=None: TopicDetection(
            topic="iva", confidence=0.95, scores={}, source="keywords"
        ),
    )
    monkeypatch.setattr(
        classifier_module, "_resolve_adapter", lambda adapter: None
    )
    result = classify_ingestion_document(
        filename="IVA-formulario-300.md",
        body_text="texto de iva",
        adapter=None,
        always_emit_label=True,
    )
    assert result.generated_label is None
    assert result.detected_topic == "iva"
    assert result.combined_confidence == pytest.approx(0.95)
    assert result.is_raw is False
    assert result.classification_source in {"keywords", "filename"}


def test_always_emit_label_malformed_llm_json_keeps_n1_verdict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """N1 high-confidence + always_emit_label=True + LLM returns garbage →
    primary assignment unaffected; generated_label stays None."""
    from lia_graph.topic_router import TopicDetection

    monkeypatch.setattr(
        classifier_module,
        "detect_topic_from_text",
        lambda text, filename=None: TopicDetection(
            topic="iva", confidence=0.95, scores={}, source="keywords"
        ),
    )
    adapter = FakeAdapter(payload="no json here, just ramblings.")
    result = classify_ingestion_document(
        filename="IVA-formulario-300.md",
        body_text="texto de iva",
        adapter=adapter,
        always_emit_label=True,
    )
    assert adapter.calls, "adapter should have been invoked"
    assert result.generated_label is None
    assert result.detected_topic == "iva"
    assert result.combined_confidence == pytest.approx(0.95)
    assert result.is_raw is False


def test_always_emit_label_does_not_promote_new_topic_over_n1(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Even if the LLM proposes a new topic, N1 high-confidence wins the
    primary assignment. The collection pass is label-only metadata, not
    a re-classification."""
    from lia_graph.topic_router import TopicDetection

    monkeypatch.setattr(
        classifier_module,
        "detect_topic_from_text",
        lambda text, filename=None: TopicDetection(
            topic="iva", confidence=0.95, scores={}, source="keywords"
        ),
    )
    adapter = FakeAdapter(
        payload=_n2_payload(
            label="concepto novedoso especifico",
            is_new_topic=True,
            suggested_key="concepto_novedoso_especifico",
        )
    )
    result = classify_ingestion_document(
        filename="IVA-formulario-300.md",
        body_text="texto de iva",
        adapter=adapter,
        always_emit_label=True,
    )
    # Label captured…
    assert result.generated_label == "concepto novedoso especifico"
    # …but N1 still owns the topic.
    assert result.detected_topic == "iva"
    assert result.combined_confidence == pytest.approx(0.95)
    assert result.is_raw is False


def test_always_emit_label_low_confidence_behaves_like_baseline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When N1 is already below 0.95, always_emit_label is a no-op — N2
    fires either way, and fusion proceeds normally."""
    from lia_graph.topic_router import TopicDetection

    monkeypatch.setattr(
        classifier_module,
        "detect_topic_from_text",
        lambda text, filename=None: TopicDetection(
            topic=None, confidence=0.0, scores={}, source="keywords"
        ),
    )
    adapter = FakeAdapter(
        payload=_n2_payload(
            label="tema iva",
            resolved="iva",
            synonym_confidence=0.90,
        )
    )
    result_baseline = classify_ingestion_document(
        filename="ambiguo.md",
        body_text="texto",
        adapter=FakeAdapter(
            payload=_n2_payload(
                label="tema iva",
                resolved="iva",
                synonym_confidence=0.90,
            )
        ),
    )
    result_always = classify_ingestion_document(
        filename="ambiguo.md",
        body_text="texto",
        adapter=adapter,
        always_emit_label=True,
    )
    # Both pathways should land on the same verdict.
    assert result_always.detected_topic == result_baseline.detected_topic
    assert result_always.combined_confidence == pytest.approx(
        result_baseline.combined_confidence
    )
    assert result_always.classification_source == result_baseline.classification_source
