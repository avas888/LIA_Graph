from __future__ import annotations

from typing import Any

from ._compat import send_not_implemented


def _send_if_match(handler: Any, path: str, *, feature: str, exact: tuple[str, ...] = (), prefixes: tuple[str, ...] = ()) -> bool:
    if exact and path in exact:
        send_not_implemented(handler, feature=feature)
        return True
    if prefixes and any(path.startswith(prefix) for prefix in prefixes):
        send_not_implemented(handler, feature=feature)
        return True
    return False


def handle_chat_run_post(handler: Any, path: str, *args: Any, **kwargs: Any) -> bool:
    del args, kwargs
    return _send_if_match(
        handler,
        path,
        feature="Chat run",
        prefixes=("/api/chat/runs/",),
    )


def handle_corpus_operation_post(handler: Any, path: str, *args: Any, **kwargs: Any) -> bool:
    del args, kwargs
    return _send_if_match(
        handler,
        path,
        feature="Corpus operation",
        exact=("/api/corpora",),
        prefixes=(
            "/api/ops/corpus/rebuild-from-wip",
            "/api/ops/corpus/rollback",
            "/api/ops/corpus/wip-audit",
        ),
    )


def handle_corpus_sync_to_wip_post(handler: Any, path: str, *args: Any, **kwargs: Any) -> bool:
    del args, kwargs
    return _send_if_match(
        handler,
        path,
        feature="Corpus sync to WIP",
        exact=("/api/ops/corpus/sync-to-wip",),
    )


def handle_contributions_post(handler: Any, path: str, *args: Any, **kwargs: Any) -> bool:
    del args, kwargs
    return _send_if_match(
        handler,
        path,
        feature="Contributions",
        prefixes=("/api/contributions",),
    )


def handle_embedding_operation_post(handler: Any, path: str, *args: Any, **kwargs: Any) -> bool:
    del args, kwargs
    return _send_if_match(
        handler,
        path,
        feature="Embedding operation",
        prefixes=("/api/ops/embedding/",),
    )


def handle_form_guides_post(handler: Any, path: str, *args: Any, **kwargs: Any) -> bool:
    del args, kwargs
    return _send_if_match(
        handler,
        path,
        feature="Form guides",
        prefixes=("/api/form-guides/",),
    )


def handle_ingestion_post(handler: Any, path: str, *args: Any, **kwargs: Any) -> bool:
    del args, kwargs
    return _send_if_match(
        handler,
        path,
        feature="Ingestion",
        prefixes=("/api/ingestion",),
    )


def handle_platform_post(handler: Any, path: str, *args: Any, **kwargs: Any) -> bool:
    del args, kwargs
    return _send_if_match(
        handler,
        path,
        feature="Platform POST",
        prefixes=("/api/platform",),
    )


def handle_promote_post(handler: Any, path: str, *args: Any, **kwargs: Any) -> bool:
    del args, kwargs
    return _send_if_match(
        handler,
        path,
        feature="Promote",
        prefixes=("/api/promote",),
    )


def handle_reindex_operation_post(handler: Any, path: str, *args: Any, **kwargs: Any) -> bool:
    del args, kwargs
    return _send_if_match(
        handler,
        path,
        feature="Reindex operation",
        prefixes=("/api/ops/reindex/",),
    )


def handle_reindex_post(handler: Any, path: str, *args: Any, **kwargs: Any) -> bool:
    del args, kwargs
    return _send_if_match(
        handler,
        path,
        feature="Reindex",
        prefixes=("/api/reindex",),
    )


def handle_rollback_post(handler: Any, path: str, *args: Any, **kwargs: Any) -> bool:
    del args, kwargs
    return _send_if_match(
        handler,
        path,
        feature="Rollback",
        prefixes=("/api/rollback",),
    )


def handle_terms_feedback_post(handler: Any, path: str, *args: Any, **kwargs: Any) -> bool:
    del args, kwargs
    return _send_if_match(
        handler,
        path,
        feature="Terms feedback",
        prefixes=("/api/terms/feedback",),
    )
