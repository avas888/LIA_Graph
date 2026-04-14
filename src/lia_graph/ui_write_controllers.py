from __future__ import annotations

from typing import Any

from ._compat import send_not_implemented


def handle_chat_run_post(handler: Any, *args: Any, **kwargs: Any) -> None:
    send_not_implemented(handler, feature="Chat run")


def handle_corpus_operation_post(handler: Any, *args: Any, **kwargs: Any) -> None:
    send_not_implemented(handler, feature="Corpus operation")


def handle_corpus_sync_to_wip_post(handler: Any, *args: Any, **kwargs: Any) -> None:
    send_not_implemented(handler, feature="Corpus sync to WIP")


def handle_contributions_post(handler: Any, *args: Any, **kwargs: Any) -> None:
    send_not_implemented(handler, feature="Contributions")


def handle_embedding_operation_post(handler: Any, *args: Any, **kwargs: Any) -> None:
    send_not_implemented(handler, feature="Embedding operation")


def handle_form_guides_post(handler: Any, *args: Any, **kwargs: Any) -> None:
    send_not_implemented(handler, feature="Form guides")


def handle_ingestion_post(handler: Any, *args: Any, **kwargs: Any) -> None:
    send_not_implemented(handler, feature="Ingestion")


def handle_platform_post(handler: Any, *args: Any, **kwargs: Any) -> None:
    send_not_implemented(handler, feature="Platform POST")


def handle_promote_post(handler: Any, *args: Any, **kwargs: Any) -> None:
    send_not_implemented(handler, feature="Promote")


def handle_reindex_operation_post(handler: Any, *args: Any, **kwargs: Any) -> None:
    send_not_implemented(handler, feature="Reindex operation")


def handle_reindex_post(handler: Any, *args: Any, **kwargs: Any) -> None:
    send_not_implemented(handler, feature="Reindex")


def handle_rollback_post(handler: Any, *args: Any, **kwargs: Any) -> None:
    send_not_implemented(handler, feature="Rollback")


def handle_terms_feedback_post(handler: Any, *args: Any, **kwargs: Any) -> None:
    send_not_implemented(handler, feature="Terms feedback")
