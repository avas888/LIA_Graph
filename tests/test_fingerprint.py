"""Fingerprint contract tests (Phase 2 helper, landed early in Phase 1).

These cover the ``src/lia_graph/ingestion/fingerprint.py`` contract. Phase 2
explicitly targets this module; it landed with Phase 1 because the backfill
script ``scripts/backfill_doc_fingerprint.py`` imports it. See
``docs/done/next/additive_corpusv1.md`` §12.1 (subsumption) and the Phase 2 State
Notes for the rationale.

Cases map 1:1 with the plan's Phase 2 test table entries (a)-(e) plus the
reviewer-added (f)/(g) equivalence between backfill-shape and ingest-shape
fingerprint builders.
"""

from __future__ import annotations

import json

from lia_graph.ingestion.fingerprint import (
    CLASSIFIER_FINGERPRINT_FIELDS,
    DEFAULT_PROMPT_VERSION,
    canonical_classifier_json,
    classifier_output_from_corpus_document,
    classifier_output_from_document_row,
    compute_doc_fingerprint,
)


def _sample_classifier_output() -> dict:
    return {
        "topic_key": "iva",
        "subtopic_key": "iva.regimen_responsable",
        "requires_subtopic_review": False,
        "authority_level": "nacional",
        "document_archetype": "ley",
        "knowledge_class": "normative_base",
        "source_type": "article_collection",
        "prompt_version": "paso4_v1",
    }


# (a) stable under key-order permutation of classifier output.
def test_fingerprint_stable_under_key_order_permutation() -> None:
    out_a = _sample_classifier_output()
    out_b = {k: out_a[k] for k in reversed(list(out_a.keys()))}
    fp_a = compute_doc_fingerprint(content_hash="hash-a", classifier_output=out_a)
    fp_b = compute_doc_fingerprint(content_hash="hash-a", classifier_output=out_b)
    assert fp_a == fp_b


# (b) differs when content_hash differs.
def test_fingerprint_differs_on_content_hash_change() -> None:
    out = _sample_classifier_output()
    fp_a = compute_doc_fingerprint(content_hash="hash-a", classifier_output=out)
    fp_b = compute_doc_fingerprint(content_hash="hash-b", classifier_output=out)
    assert fp_a != fp_b


# (c) differs when any CLASSIFIER_FINGERPRINT_FIELDS value differs.
def test_fingerprint_differs_on_classifier_field_changes() -> None:
    base = _sample_classifier_output()
    fp_base = compute_doc_fingerprint(content_hash="hash", classifier_output=base)
    for field in CLASSIFIER_FINGERPRINT_FIELDS:
        drifted = dict(base)
        if field == "requires_subtopic_review":
            drifted[field] = not bool(base[field])
        else:
            drifted[field] = "drifted-value"
        fp_drifted = compute_doc_fingerprint(
            content_hash="hash", classifier_output=drifted
        )
        assert fp_base != fp_drifted, f"field {field!r} should enter the fingerprint"


# (d) ignores fields outside CLASSIFIER_FINGERPRINT_FIELDS.
def test_fingerprint_ignores_unrelated_fields() -> None:
    base = _sample_classifier_output()
    with_extras = dict(base)
    with_extras["source_tier"] = "dropped-per-K1"
    with_extras["some_future_field"] = {"nested": True}
    with_extras["ignored_list"] = [1, 2, 3]
    fp_base = compute_doc_fingerprint(content_hash="hash", classifier_output=base)
    fp_with_extras = compute_doc_fingerprint(
        content_hash="hash", classifier_output=with_extras
    )
    assert fp_base == fp_with_extras


# (e) empty classifier output → deterministic sentinel fingerprint.
def test_fingerprint_empty_classifier_output_deterministic() -> None:
    fp1 = compute_doc_fingerprint(content_hash="hash", classifier_output={})
    fp2 = compute_doc_fingerprint(content_hash="hash", classifier_output={})
    assert fp1 == fp2
    # The canonical JSON for an empty output must still serialize all fields
    # with the missing sentinel (plus the default prompt_version) so absent
    # inputs don't produce the same fingerprint as partially-known inputs.
    canonical = json.loads(canonical_classifier_json({}))
    assert set(canonical.keys()) == set(CLASSIFIER_FINGERPRINT_FIELDS)
    assert canonical["prompt_version"] == DEFAULT_PROMPT_VERSION


# (f) reviewer-added: backfill-mapping ≡ live-ingest-mapping for a
# representative doc. If this fails the first full-rebuild after shipping
# Phase 1 will mark every doc `modified` — Risk 11.
def test_fingerprint_backfill_matches_live_ingest_for_representative_doc() -> None:
    # Shape as held in memory during ingest (keys from CorpusDocument +
    # supabase_sink row-building).
    live = {
        "topic_key": "iva",
        "subtopic_key": "iva.regimen_responsable",
        "requires_subtopic_review": False,
        "authority_level": "nacional",
        "document_archetype": "ley",
        "knowledge_class": "normative_base",
        "source_type": "article_collection",
        "source_tier": "official_compilation",  # dropped by K1
        "prompt_version": "paso4_v1",
    }
    # Shape as persisted in the documents table (keys from baseline schema +
    # supabase_sink.write_documents row assembly).
    persisted_row = {
        "doc_id": "normativa_iva_example",
        "topic": "iva",
        "tema": "iva",
        "subtema": "iva.regimen_responsable",
        "authority": "nacional",
        "tipo_de_documento": "ley",
        "source_type": "article_collection",
        "knowledge_class": "normative_base",
        "requires_subtopic_review": False,
    }
    live_output = classifier_output_from_corpus_document(live)
    backfill_output = classifier_output_from_document_row(persisted_row)
    fp_live = compute_doc_fingerprint(content_hash="hash", classifier_output=live_output)
    fp_backfill = compute_doc_fingerprint(
        content_hash="hash", classifier_output=backfill_output
    )
    assert fp_live == fp_backfill


# (g) reviewer-added: when the persisted row has only `tipo_de_documento` and
# the live doc has only `document_archetype`, the two mappings still converge
# because the mappers normalize to the same key.
def test_fingerprint_backfill_handles_archetype_source_type_fallback() -> None:
    live = {
        "topic_key": "laboral",
        "subtopic_key": None,
        "requires_subtopic_review": True,
        "authority_level": None,
        "document_archetype": "concepto",
        "knowledge_class": "doctrinal",
        "source_type": "consulta",
    }
    persisted_row = {
        "topic": "laboral",
        "subtema": None,
        "authority": None,
        "tipo_de_documento": "concepto",  # mirrors document_archetype
        "source_type": "consulta",
        "knowledge_class": "doctrinal",
        "requires_subtopic_review": True,
    }
    live_output = classifier_output_from_corpus_document(live)
    backfill_output = classifier_output_from_document_row(persisted_row)
    assert compute_doc_fingerprint(
        content_hash="h", classifier_output=live_output
    ) == compute_doc_fingerprint(
        content_hash="h", classifier_output=backfill_output
    )
