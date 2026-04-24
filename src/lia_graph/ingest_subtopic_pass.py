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
import time
from typing import Any, Callable, Iterable, Mapping, Sequence

from .ingest_constants import CorpusDocument
from .instrumentation import emit_event

_OVERRIDE_CONFIDENCE_THRESHOLD = 0.80


def _doc_id_hash(source_path: str) -> str:
    return hashlib.sha1(source_path.encode("utf-8"), usedforsecurity=False).hexdigest()[:12]


def _apply_rate_limit(rpm: int, last_tick: float | None) -> float:
    if rpm <= 0:
        return time.monotonic()
    min_gap = 60.0 / max(rpm, 1)
    now = time.monotonic()
    if last_tick is None:
        return now
    delta = now - last_tick
    if delta < min_gap:
        time.sleep(min_gap - delta)
        return time.monotonic()
    return now


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


def classify_corpus_documents(
    documents: Sequence[CorpusDocument],
    *,
    skip_llm: bool = False,
    rate_limit_rpm: int = 60,
    classifier: Callable[..., Any] | None = None,
    taxonomy_loader: Callable[[], Any] | None = None,
    override_confidence_threshold: float = _OVERRIDE_CONFIDENCE_THRESHOLD,
) -> tuple[CorpusDocument, ...]:
    """Run PASO 4 over every document and return replaced copies.

    When ``skip_llm`` is True the input tuple is returned unchanged (the
    legacy ``_infer_vocabulary_labels`` verdict that was already on the
    audit record stays authoritative). This is the fast-dev / CI-smoke
    path.

    Per-doc classifier failures do not abort the pass. The failing doc
    keeps its legacy subtopic_key and is flagged ``requires_subtopic_review``.
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

    start = time.monotonic()
    classified = 0
    failed = 0
    last_tick: float | None = None

    lookup_by_key_early = getattr(taxonomy, "lookup_by_key", None) or {}
    out: list[CorpusDocument] = []
    for doc in documents_tuple:
        # The audit gate only admits graph-targeted markdown for the Falkor
        # load, but we classify *every* included doc so the Supabase sink
        # also gets subtema coverage (interpretacion + practica flow too).
        if not doc.markdown.strip():
            out.append(doc)
            continue

        last_tick = _apply_rate_limit(rate_limit_rpm, last_tick)
        # Validate legacy regex verdict against taxonomy before treating it as
        # a trusted fallback. `_infer_vocabulary_labels` is permissive and can
        # produce subtopic_keys that no longer exist in the curated taxonomy.
        raw_legacy_key = doc.subtopic_key
        if raw_legacy_key and doc.topic_key:
            if (doc.topic_key, raw_legacy_key) in lookup_by_key_early:
                legacy_key = raw_legacy_key
            else:
                legacy_key = None
        else:
            legacy_key = None
        filename = doc.relative_path or doc.source_path
        try:
            verdict = classifier(
                filename=filename,
                body_text=doc.markdown,
            )
        except Exception as exc:  # noqa: BLE001 — per-doc tolerance
            failed += 1
            emit_event(
                "subtopic.ingest.audit_classified",
                {
                    "doc_id_hash": _doc_id_hash(doc.source_path),
                    "topic": doc.topic_key,
                    "subtopic_key": legacy_key,
                    "subtopic_confidence": 0.0,
                    "requires_subtopic_review": True,
                    "status": "failed",
                    "error": str(exc)[:200],
                },
            )
            out.append(
                doc.with_subtopic(
                    subtopic_key=legacy_key,
                    requires_subtopic_review=True,
                )
            )
            continue

        n2_key_raw = getattr(verdict, "subtopic_key", None)
        confidence = float(getattr(verdict, "subtopic_confidence", 0.0) or 0.0)
        verdict_requires_review = bool(
            getattr(verdict, "requires_subtopic_review", False)
        )
        detected_topic = (
            getattr(verdict, "detected_topic", None) or doc.topic_key
        )
        # ingestionfix_v2 §4 Phase 3 defense-in-depth: if both the legacy
        # regex pass AND the PASO 4 LLM returned no topic, fall back to
        # the path-inferred topic so the subtopic.ingest.audit_classified
        # event never emits with a null topic when the folder layout is a
        # clear signal (e.g. retencion_en_la_fuente/X.md).
        if detected_topic is None:
            from .ingest_classifiers import coerce_topic_from_path

            detected_topic = coerce_topic_from_path(
                doc.relative_path or doc.source_path
            )

        # Taxonomy consistency: drop orphan keys and flag.
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
        if override_ok:
            next_key: str | None = accepted_key
            next_review = False
            # Only override topic_key when the LLM gave us a topic that
            # is also consistent with the taxonomy (i.e. we already used
            # (detected_topic, accepted_key) to validate). Propagate so
            # Phase A5 binding can find (topic, subtopic) in the taxonomy.
            if detected_topic and detected_topic != doc.topic_key:
                topic_override = detected_topic
        elif accepted_key is not None:
            # Classifier returned a legit key but low confidence / review needed
            next_key = legacy_key
            next_review = True
        elif orphan:
            # Classifier hallucinated a subtopic outside the taxonomy
            next_key = legacy_key
            next_review = True
        else:
            # Classifier returned no subtopic. Preserve legacy verdict, flag for
            # review only if classifier itself flagged.
            next_key = legacy_key
            next_review = verdict_requires_review

        classified += 1
        emit_event(
            "subtopic.ingest.audit_classified",
            {
                "doc_id_hash": _doc_id_hash(doc.source_path),
                "topic": detected_topic,
                "subtopic_key": next_key,
                "subtopic_confidence": round(confidence, 4),
                "requires_subtopic_review": next_review,
                "status": "ok",
                "override_from_legacy": override_ok and next_key != legacy_key,
                "orphan_dropped": orphan,
                "topic_override_applied": topic_override is not None,
            },
        )
        out.append(
            doc.with_subtopic(
                subtopic_key=next_key,
                requires_subtopic_review=next_review,
                topic_key=topic_override,
            )
        )

    elapsed = time.monotonic() - start
    emit_event(
        "subtopic.ingest.audit_done",
        {
            "docs_total": len(documents_tuple),
            "docs_classified": classified,
            "docs_failed": failed,
            "elapsed_s": round(elapsed, 2),
            "skip_llm": False,
        },
    )
    return tuple(out)


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
