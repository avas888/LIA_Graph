"""PASO 4 classifier pass over corpus documents during bulk ingest.

Phase A4 of ingestfix-v2-maximalist (see ``docs/next/ingestfixv2.md``).

The legacy flow ran ``_infer_vocabulary_labels`` (deterministic regex) only.
This module adds a second pass: for every included corpus document, it calls
``classify_ingestion_document`` (the PASO 4 LLM verdict) and, when the N2
verdict is high-confidence AND does not require review, overrides the
legacy subtopic_key. Rate-limited via ``time.sleep`` to stay clear of
Gemini quotas. Per-doc classifier failures are tolerated: the doc keeps
its legacy verdict and gets ``requires_subtopic_review=True``.

Trace events:
    subtopic.ingest.audit_classified   — per doc (success and failure)
    subtopic.ingest.audit_done         — pass end
"""
from __future__ import annotations

import hashlib
import os
import time
from typing import Any, Callable, Iterable, Mapping, Sequence

from .ingest_classifier_pool import (
    classifier_error,
    classify_documents_parallel,
    is_classifier_error,
)
from .ingest_constants import CorpusDocument
from .instrumentation import emit_event

_OVERRIDE_CONFIDENCE_THRESHOLD = 0.80

# Phase 2a (v6): parallelism is the durable default. The classifier is
# I/O-bound on ~1.5 s Gemini responses, and 8 workers × 300 RPM ceiling
# saturates the quota with safe headroom. Callers pass through their own
# worker_count (via CLI flag / env var / delta-worker config) but the
# library default stays at 8 so every code path inherits parallelism
# unless someone explicitly opts out.
_DEFAULT_WORKERS = 8


def _resolve_worker_count(explicit: int | None) -> int:
    if explicit is not None:
        return max(1, int(explicit))
    raw = os.environ.get("LIA_INGEST_CLASSIFIER_WORKERS")
    if raw:
        try:
            return max(1, int(raw))
        except ValueError:
            pass
    return _DEFAULT_WORKERS


def _doc_id_hash(source_path: str) -> str:
    return hashlib.sha1(source_path.encode("utf-8"), usedforsecurity=False).hexdigest()[:12]


def _validate_against_taxonomy(
    *,
    topic_key: str | None,
    subtopic_key: str | None,
    taxonomy: Any,
) -> tuple[str | None, bool]:
    """Return (accepted_key, orphan_flag).

    accepted_key is the subtopic_key iff it exists in taxonomy.lookup_by_key
    under the given topic_key. orphan_flag is True when the LLM suggested a
    key not in the curated taxonomy — caller should drop the key and flag
    the doc for review.
    """
    if not subtopic_key:
        return None, False
    if not topic_key:
        # Can't validate without a parent topic. Conservatively drop.
        return None, True
    lookup = getattr(taxonomy, "lookup_by_key", None) or {}
    if (topic_key, subtopic_key) in lookup:
        return subtopic_key, False
    return None, True


def _resolve_legacy_key(doc: CorpusDocument, lookup_by_key: Mapping) -> str | None:
    raw = doc.subtopic_key
    if raw and doc.topic_key and (doc.topic_key, raw) in lookup_by_key:
        return raw
    return None


def _assemble_doc_from_verdict(
    doc: CorpusDocument,
    verdict: Any,
    *,
    legacy_key: str | None,
    taxonomy: Any,
    override_confidence_threshold: float,
) -> tuple[CorpusDocument, dict]:
    """Apply taxonomy checks + override policy to a classifier verdict.

    Returns ``(updated_doc, event_payload)``. The event is the
    ``subtopic.ingest.audit_classified`` payload with ``status="ok"``;
    the caller emits it after the worker returns.
    """
    n2_key_raw = getattr(verdict, "subtopic_key", None)
    confidence = float(getattr(verdict, "subtopic_confidence", 0.0) or 0.0)
    verdict_requires_review = bool(
        getattr(verdict, "requires_subtopic_review", False)
    )
    detected_topic = getattr(verdict, "detected_topic", None) or doc.topic_key
    if detected_topic is None:
        from .ingest_classifiers import coerce_topic_from_path

        detected_topic = coerce_topic_from_path(
            doc.relative_path or doc.source_path
        )

    accepted_key, orphan = _validate_against_taxonomy(
        topic_key=detected_topic,
        subtopic_key=n2_key_raw,
        taxonomy=taxonomy,
    )

    override_ok = (
        accepted_key is not None
        and confidence >= override_confidence_threshold
        and not verdict_requires_review
    )

    topic_override: str | None = None
    # next_v3 §13.6 — path-veto is a hard rule above the LLM. When the
    # classifier output came from `_apply_path_veto` (classification_source
    # == "path_veto"), force the topic propagation regardless of subtopic
    # confidence. Without this, the path-veto'd topic gets discarded when
    # the doc's subtopic verdict is weak — exactly the failure mode that
    # left art. 148 still bound to `iva` after rebuild #2.
    is_path_veto = (
        getattr(verdict, "classification_source", None) == "path_veto"
    )
    if override_ok:
        next_key: str | None = accepted_key
        next_review = False
        if detected_topic and detected_topic != doc.topic_key:
            topic_override = detected_topic
    elif accepted_key is not None:
        next_key = legacy_key
        next_review = True
    elif orphan:
        next_key = legacy_key
        next_review = True
    else:
        next_key = legacy_key
        next_review = verdict_requires_review

    # Path-veto override fires regardless of the subtopic-side override gate.
    # If the deterministic rule already produced a topic, it wins.
    if is_path_veto and detected_topic and detected_topic != doc.topic_key:
        topic_override = detected_topic

    event = {
        "doc_id_hash": _doc_id_hash(doc.source_path),
        "topic": detected_topic,
        "subtopic_key": next_key,
        "subtopic_confidence": round(confidence, 4),
        "requires_subtopic_review": next_review,
        "status": "ok",
        "override_from_legacy": override_ok and next_key != legacy_key,
        "orphan_dropped": orphan,
        "topic_override_applied": topic_override is not None,
    }
    updated = doc.with_subtopic(
        subtopic_key=next_key,
        requires_subtopic_review=next_review,
        topic_key=topic_override,
    )
    return updated, event


def classify_corpus_documents(
    documents: Sequence[CorpusDocument],
    *,
    skip_llm: bool = False,
    rate_limit_rpm: int = 60,
    classifier: Callable[..., Any] | None = None,
    taxonomy_loader: Callable[[], Any] | None = None,
    override_confidence_threshold: float = _OVERRIDE_CONFIDENCE_THRESHOLD,
    worker_count: int | None = None,
) -> tuple[CorpusDocument, ...]:
    """Run PASO 4 over every document and return replaced copies.

    Parallelism is the default: ``worker_count`` resolves to the
    ``LIA_INGEST_CLASSIFIER_WORKERS`` env var if set, else 8. Set
    ``worker_count=1`` to force the sequential path (debugging / regression
    only — parallel is the sanctioned default for every production run).

    When ``skip_llm`` is True the input tuple is returned unchanged. Per-doc
    classifier failures do not abort the pass; the failing doc keeps its
    legacy subtopic_key and is flagged ``requires_subtopic_review``.

    Output order is byte-identical to ``documents`` regardless of worker
    count — the pool uses pre-allocated indexed slots.
    """
    documents_tuple = tuple(documents)
    if skip_llm:
        emit_event(
            "subtopic.ingest.audit_done",
            {
                "docs_total": len(documents_tuple),
                "docs_classified": 0,
                "docs_failed": 0,
                "elapsed_s": 0.0,
                "skip_llm": True,
            },
        )
        return documents_tuple

    if classifier is None:
        from .ingestion_classifier import classify_ingestion_document as _classifier

        classifier = _classifier

    if taxonomy_loader is None:
        from .subtopic_taxonomy_loader import load_taxonomy as _load

        taxonomy_loader = _load

    taxonomy = taxonomy_loader()
    lookup_by_key_early = getattr(taxonomy, "lookup_by_key", None) or {}
    resolved_workers = _resolve_worker_count(worker_count)
    start = time.monotonic()

    # Partition: empty-markdown docs bypass the classifier entirely, so
    # they don't consume a worker slot. The pool only sees real work.
    skip_indices: list[int] = []
    work_indices: list[int] = []
    for i, doc in enumerate(documents_tuple):
        if not doc.markdown.strip():
            skip_indices.append(i)
        else:
            work_indices.append(i)
    work_docs = tuple(documents_tuple[i] for i in work_indices)

    def _classify_one(_idx: int, doc: CorpusDocument) -> Any:
        filename = doc.relative_path or doc.source_path
        return classifier(filename=filename, body_text=doc.markdown)

    verdicts = classify_documents_parallel(
        work_docs,
        classify_fn=_classify_one,
        worker_count=resolved_workers,
        rate_limit_rpm=rate_limit_rpm,
    )

    # Merge: assemble the final ordered tuple. Failures slot a
    # legacy-verdict copy with requires_subtopic_review=True.
    out: list[CorpusDocument | None] = [None] * len(documents_tuple)
    classified = 0
    failed = 0
    for local_i, verdict in enumerate(verdicts):
        original_idx = work_indices[local_i]
        doc = documents_tuple[original_idx]
        legacy_key = _resolve_legacy_key(doc, lookup_by_key_early)
        if is_classifier_error(verdict):
            failed += 1
            exc = classifier_error(verdict)
            emit_event(
                "subtopic.ingest.audit_classified",
                {
                    "doc_id_hash": _doc_id_hash(doc.source_path),
                    "topic": doc.topic_key,
                    "subtopic_key": legacy_key,
                    "subtopic_confidence": 0.0,
                    "requires_subtopic_review": True,
                    "status": "failed",
                    "error": str(exc)[:200] if exc else "unknown",
                },
            )
            out[original_idx] = doc.with_subtopic(
                subtopic_key=legacy_key,
                requires_subtopic_review=True,
            )
            continue
        updated, event = _assemble_doc_from_verdict(
            doc,
            verdict,
            legacy_key=legacy_key,
            taxonomy=taxonomy,
            override_confidence_threshold=override_confidence_threshold,
        )
        classified += 1
        emit_event("subtopic.ingest.audit_classified", event)
        out[original_idx] = updated

    for i in skip_indices:
        out[i] = documents_tuple[i]

    # Determinism invariant: every slot filled.
    assert all(item is not None for item in out), "classifier pool left empty slots"

    elapsed = time.monotonic() - start
    emit_event(
        "subtopic.ingest.audit_done",
        {
            "docs_total": len(documents_tuple),
            "docs_classified": classified,
            "docs_failed": failed,
            "elapsed_s": round(elapsed, 2),
            "skip_llm": False,
            "worker_count": resolved_workers,
            "rate_limit_rpm": rate_limit_rpm,
        },
    )
    return tuple(out)  # type: ignore[arg-type]


def build_article_subtopic_bindings(
    *,
    classified_documents: Sequence[CorpusDocument],
    articles: Iterable[Any],
    taxonomy: Any | None = None,
    taxonomy_loader: Callable[[], Any] | None = None,
) -> dict[str, Any]:
    """Correlate classified docs → parsed articles → curated taxonomy bindings.

    Returns a mapping of ``article_key → SubtopicBinding`` suitable for
    ``build_graph_load_plan(article_subtopics=...)``. Articles whose source
    document did not carry a populated ``subtopic_key`` (or whose key is not
    in the taxonomy) are omitted — the loader only emits SubTopicNodes +
    HAS_SUBTOPIC edges for the returned subset.

    Emits ``subtopic.graph.binding_built`` per successful binding and a
    terminal ``subtopic.graph.bindings_summary`` event with counts of
    accepted vs skipped bindings (per reason). The summary is the signal
    that would have caught the B3 bug: a B3 run that shows
    ``skipped_topic_mismatch > 0`` is a red flag.
    """
    from .ingestion.loader import SubtopicBinding, _graph_article_key

    if taxonomy is None:
        if taxonomy_loader is None:
            from .subtopic_taxonomy_loader import load_taxonomy as _load

            taxonomy_loader = _load
        taxonomy = taxonomy_loader()

    lookup_by_key = getattr(taxonomy, "lookup_by_key", None) or {}

    doc_by_path: dict[str, CorpusDocument] = {
        str(doc.source_path): doc for doc in classified_documents
    }

    bindings: dict[str, Any] = {}
    skipped = {
        "missing_article_key_or_path": 0,
        "doc_not_in_corpus": 0,
        "no_subtopic_key": 0,
        "no_topic_key": 0,
        "topic_subtopic_mismatch": 0,  # both set but pair not in taxonomy
    }
    for article in articles:
        article_key = str(getattr(article, "article_key", "") or "")
        source_path = str(getattr(article, "source_path", "") or "")
        if not article_key or not source_path:
            skipped["missing_article_key_or_path"] += 1
            continue
        doc = doc_by_path.get(source_path)
        if doc is None:
            skipped["doc_not_in_corpus"] += 1
            continue
        sub_key = doc.subtopic_key
        parent_topic = doc.topic_key
        if not sub_key:
            skipped["no_subtopic_key"] += 1
            continue
        if not parent_topic:
            skipped["no_topic_key"] += 1
            continue
        entry = lookup_by_key.get((parent_topic, sub_key))
        if entry is None:
            skipped["topic_subtopic_mismatch"] += 1
            continue
        label = getattr(entry, "label", "") or sub_key
        # v4: key bindings by graph-layer article key so HAS_SUBTOPIC edges
        # resolve against the ArticleNode's MERGE key (which differs from
        # `article.article_key` for prose-only docs).
        graph_key = _graph_article_key(article)
        bindings[graph_key] = SubtopicBinding(
            sub_topic_key=sub_key,
            parent_topic=parent_topic,
            label=label,
        )
        emit_event(
            "subtopic.graph.binding_built",
            {
                "article_key": graph_key,
                "sub_topic_key": sub_key,
                "parent_topic": parent_topic,
            },
        )
    emit_event(
        "subtopic.graph.bindings_summary",
        {
            "accepted": len(bindings),
            "distinct_subtopics": len({b.sub_topic_key for b in bindings.values()}),
            **skipped,
        },
    )
    return bindings


__all__ = [
    "build_article_subtopic_bindings",
    "classify_corpus_documents",
]
