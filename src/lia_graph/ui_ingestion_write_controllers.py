"""POST surface for ``/api/ingestion/*`` and ``/api/corpora``.

Extracted from `ui_write_controllers.py` during granularize-v2 (2026-04-20)
because the single `handle_ingestion_post` function accounted for 849 LOC
— half of the original "write controllers" dumping ground — and has a
self-contained identity: **the kanban-backed ingestion workflow** (corpus
registration, session create, per-file upload + classify + dedup, auto-
processing, resolve-duplicate / accept-autogenerar workflows, preflight,
batch start/retry/validate/stop/clear, purge-and-replace).

Routes owned by this module:

  * ``POST /api/corpora``                                            — register a new corpus
  * ``POST /api/ingestion/sessions``                                 — create session
  * ``POST /api/ingestion/classify``                                 — classify a preview
  * ``POST /api/ingestion/sessions/{id}/documents/{doc}/classify``   — manual classify
  * ``POST /api/ingestion/sessions/{id}/documents/{doc}/accept-autogenerar``
  * ``POST /api/ingestion/sessions/{id}/documents/{doc}/resolve-duplicate``
  * ``POST /api/ingestion/sessions/{id}/documents/{doc}/retry``      (via regex deps)
  * ``POST /api/ingestion/sessions/{id}/auto-process``               — auto-accept queue
  * ``POST /api/ingestion/sessions/{id}/files``                      (via regex deps)
  * ``POST /api/ingestion/sessions/{id}/process|retry|validate-batch|delete-failed|stop|clear-batch``
  * ``POST /api/ingestion/preflight``                                — checksum + ledger preflight
  * ``POST /api/ingestion/sessions/{id}/purge-and-replace``

Wiring contract (unchanged from the `ui_write_controllers` era):

* signature is ``(handler, path, *, deps) -> bool``; ``False`` means URL
  did not match, ``True`` means request fully handled (response sent).
* ``deps["ingestion_runtime"]`` carries the stateful service; the
  ``ingestion_*_route_re`` regex bundle is injected through ``deps`` as
  well so the dispatcher can share compiled regexes with the GET surface.
* ``ui_write_controllers.py`` re-exports ``handle_ingestion_post`` from
  here so `from .ui_write_controllers import handle_ingestion_post`
  continues to work; `ui_server.py`'s import block is unaffected.
"""

from __future__ import annotations

import hashlib
import json
import re
from http import HTTPStatus
from typing import Any


# ---------------------------------------------------------------------------
# Helpers para ingestion kanban (Phase 4)
# ---------------------------------------------------------------------------

_TYPE_LABELS = {
    "normative_base": "Normativa",
    "interpretative_guidance": "Interpretacion",
    "practica_erp": "Practica",
}

_TOPIC_LABELS = {
    "declaracion_renta": "Renta",
    "iva": "IVA",
    "laboral": "Laboral",
    "facturacion_electronica": "Facturacion",
    "estados_financieros_niif": "NIIF",
    "ica": "ICA",
    "calendario_obligaciones": "Calendarios",
}


def _type_label(t: str | None) -> str:
    return _TYPE_LABELS.get(t or "", t or "?")


def _topic_label(t: str | None) -> str:
    return _TOPIC_LABELS.get(t or "", t or "?")


def _find_doc(docs: list[dict[str, Any]], doc_id: str) -> dict[str, Any] | None:
    return next((d for d in docs if d.get("doc_id") == doc_id), None)


# Regex para rutas de ingestion Phase 4
_INGESTION_CLASSIFY_DOC_RE = re.compile(
    r"^/api/ingestion/sessions/([^/]+)/documents/([^/]+)/classify$"
)
_INGESTION_RESOLVE_DUPLICATE_RE = re.compile(
    r"^/api/ingestion/sessions/([^/]+)/documents/([^/]+)/resolve-duplicate$"
)
_INGESTION_ACCEPT_AUTOGENERAR_RE = re.compile(
    r"^/api/ingestion/sessions/([^/]+)/documents/([^/]+)/accept-autogenerar$"
)
_INGESTION_DOC_RETRY_RE = re.compile(
    r"^/api/ingestion/sessions/([^/]+)/documents/([^/]+)/retry$"
)
_INGESTION_AUTO_PROCESS_RE = re.compile(
    r"^/api/ingestion/sessions/([^/]+)/auto-process$"
)
_INGESTION_PURGE_AND_REPLACE_RE = re.compile(
    r"^/api/ingestion/sessions/([^/]+)/purge-and-replace$"
)


def handle_ingestion_post(handler: Any, path: str, *, deps: dict[str, Any]) -> bool:
    if not path.startswith("/api/ingestion") and path != "/api/corpora":
        return False

    ingestion_runtime = deps["ingestion_runtime"]

    if path == "/api/corpora":
        payload = handler._read_json_payload()
        if payload is None:
            return True
        label = str(payload.get("label", "")).strip()
        if not label:
            handler._send_json(HTTPStatus.BAD_REQUEST, {"error": "`label` es obligatorio."})
            return True
        slug = str(payload.get("slug", "")).strip() or None
        keywords_strong = payload.get("keywords_strong") or []
        keywords_weak = payload.get("keywords_weak") or []
        if not isinstance(keywords_strong, list):
            keywords_strong = [str(keywords_strong)]
        if not isinstance(keywords_weak, list):
            keywords_weak = [str(keywords_weak)]
        try:
            entry = ingestion_runtime.register_corpus(
                label=label,
                slug=slug,
                keywords_strong=[str(k).strip() for k in keywords_strong if str(k).strip()],
                keywords_weak=[str(k).strip() for k in keywords_weak if str(k).strip()],
            )
        except ValueError as exc:
            error = str(exc)
            if error == "duplicate_key":
                handler._send_json(
                    HTTPStatus.CONFLICT,
                    {"error": "Ya existe una categoría con esa clave."},
                )
                return True
            handler._send_json(HTTPStatus.BAD_REQUEST, {"error": error})
            return True
        handler._send_json(HTTPStatus.CREATED, {"ok": True, "corpus": entry})
        return True

    if path == "/api/ingestion/sessions":
        payload = handler._read_json_payload()
        if payload is None:
            return True

        corpus = str(payload.get("corpus", "")).strip()
        if not corpus:
            handler._send_json(
                HTTPStatus.BAD_REQUEST, {"error": "`corpus` es obligatorio."}
            )
            return True

        # ingestion_fixv1 Phase 2: preflight gate. Refuse to start a new session
        # when WIP corpus_generations is empty AND we are running on the Supabase
        # backend. Local-fs backend (tests) skips this check.
        try:
            from .supabase_client import get_storage_backend

            if (get_storage_backend() or "").strip().lower() == "supabase":
                from .ingest import (
                    WipNoActiveGenerationError,
                    _assert_wip_has_active_generation,
                )

                try:
                    _assert_wip_has_active_generation()
                except WipNoActiveGenerationError as gen_exc:
                    handler._send_json(
                        HTTPStatus.CONFLICT,
                        {
                            "error": "wip_no_active_generation",
                            "details": str(gen_exc),
                        },
                    )
                    return True
        except Exception:  # noqa: BLE001
            pass

        try:
            session = ingestion_runtime.create_session(corpus)
        except ValueError as exc:
            error = str(exc)
            if error == "corpus_inactive":
                handler._send_json(HTTPStatus.BAD_REQUEST, {"error": "corpus_inactive"})
                return True
            handler._send_json(HTTPStatus.BAD_REQUEST, {"error": "unknown_corpus"})
            return True
        handler._send_json(HTTPStatus.OK, {"ok": True, "session": session.to_dict()})
        return True

    if path == "/api/ingestion/classify":
        payload = handler._read_json_payload()
        if payload is None:
            return True
        filename = str(payload.get("filename", "")).strip()
        body_preview = str(payload.get("body_preview", ""))
        if not filename:
            handler._send_json(
                HTTPStatus.BAD_REQUEST, {"error": "`filename` es obligatorio."}
            )
            return True
        try:
            from .ingestion_classifier import classify_upload

            result = classify_upload(filename, body_preview.encode("utf-8"))
            suggestion = None
            if result.is_raw and result.suggestion_topic:
                suggestion = (
                    f"Sugerimos: {_topic_label(result.suggestion_topic)} "
                    f"· {_type_label(result.suggestion_type)} "
                    f"({int(result.combined_confidence * 100)}%)"
                )
            handler._send_json(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "detected_topic": result.detected_topic,
                    "topic_confidence": result.topic_confidence,
                    "topic_source": result.topic_source,
                    "detected_type": result.detected_type,
                    "type_confidence": result.type_confidence,
                    "type_source": result.type_source,
                    "combined_confidence": result.combined_confidence,
                    "llm_invoked": result.llm_invoked,
                    "is_raw": result.is_raw,
                    "suggestion": suggestion,
                },
            )
        except Exception as exc:  # noqa: BLE001
            handler._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": "classify_failed", "details": str(exc)},
            )
        return True

    match_classify_doc = _INGESTION_CLASSIFY_DOC_RE.match(path)
    if match_classify_doc:
        session_id = match_classify_doc.group(1)
        doc_id = match_classify_doc.group(2)
        payload = handler._read_json_payload()
        if payload is None:
            return True
        batch_type = payload.get("batch_type")
        topic = payload.get("topic")
        with ingestion_runtime._lock:
            session = ingestion_runtime._sessions.get(session_id)
            if session is None:
                handler._send_json(
                    HTTPStatus.NOT_FOUND, {"error": "session_not_found"}
                )
                return True
            doc = _find_doc(session.get("documents", []), doc_id)
            if doc is None:
                handler._send_json(
                    HTTPStatus.NOT_FOUND, {"error": "document_not_found"}
                )
                return True
            if batch_type:
                doc["batch_type"] = str(batch_type)
                doc["detected_type"] = str(batch_type)
            if topic:
                doc["detected_topic"] = str(topic)
            doc["combined_confidence"] = 1.0
            doc["classification_source"] = "manual"
            doc["is_raw"] = False
            doc["status"] = "queued"
            doc["updated_at"] = (
                ingestion_runtime._materialize_document(doc).updated_at or ""
            )
            from datetime import datetime, timezone

            doc["updated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            ingestion_runtime._save_session_locked(session)
        handler._send_json(
            HTTPStatus.OK,
            {
                "ok": True,
                "document": {
                    "doc_id": doc_id,
                    "status": "queued",
                    "batch_type": doc.get("batch_type"),
                    "detected_type": doc.get("detected_type"),
                    "detected_topic": doc.get("detected_topic"),
                    "combined_confidence": 1.0,
                    "classification_source": "manual",
                    "is_raw": False,
                },
            },
        )
        return True

    match_accept_ag = _INGESTION_ACCEPT_AUTOGENERAR_RE.match(path)
    if match_accept_ag:
        session_id = match_accept_ag.group(1)
        doc_id = match_accept_ag.group(2)
        payload = handler._read_json_payload()
        if payload is None:
            return True
        action = str(payload.get("action", "")).strip()
        if action not in ("accept_synonym", "accept_new_topic"):
            handler._send_json(
                HTTPStatus.BAD_REQUEST,
                {"error": "action debe ser 'accept_synonym' o 'accept_new_topic'"},
            )
            return True
        with ingestion_runtime._lock:
            session = ingestion_runtime._sessions.get(session_id)
            if session is None:
                handler._send_json(
                    HTTPStatus.NOT_FOUND, {"error": "session_not_found"}
                )
                return True
            doc = _find_doc(session.get("documents", []), doc_id)
            if doc is None:
                handler._send_json(
                    HTTPStatus.NOT_FOUND, {"error": "document_not_found"}
                )
                return True

            batch_type = str(
                payload.get("type") or doc.get("batch_type") or "normative_base"
            )

            if action == "accept_synonym":
                resolved_topic = doc.get("autogenerar_resolved_topic")
                if not resolved_topic:
                    handler._send_json(
                        HTTPStatus.BAD_REQUEST,
                        {"error": "no hay tema existente sugerido"},
                    )
                    return True
                doc["detected_topic"] = resolved_topic
                doc["batch_type"] = batch_type
                doc["detected_type"] = batch_type
                doc["combined_confidence"] = 0.95
                doc["classification_source"] = "autogenerar"
                doc["is_raw"] = False
                doc["status"] = "queued"
                doc["stage"] = "queued"
                from datetime import datetime, timezone

                doc["updated_at"] = (
                    datetime.now(timezone.utc).replace(microsecond=0).isoformat()
                )
                ingestion_runtime._save_session_locked(session)
                handler._send_json(
                    HTTPStatus.OK,
                    {
                        "ok": True,
                        "document": {
                            "doc_id": doc_id,
                            "status": "queued",
                            "batch_type": batch_type,
                            "detected_topic": resolved_topic,
                            "combined_confidence": 0.95,
                            "classification_source": "autogenerar",
                            "is_raw": False,
                        },
                    },
                )
                return True

            edited_label = str(
                payload.get("edited_label") or doc.get("autogenerar_label") or ""
            ).strip()
            if not edited_label or len(edited_label) < 3:
                handler._send_json(
                    HTTPStatus.BAD_REQUEST,
                    {"error": "label demasiado corto (min 3 caracteres)"},
                )
                return True

        try:
            ag_label = doc.get("autogenerar_label") or edited_label
            new_entry = ingestion_runtime.register_corpus(
                label=edited_label,
                keywords_strong=[ag_label] if ag_label != edited_label else [edited_label],
            )
            new_topic_key = new_entry["key"]
        except ValueError as exc:
            if str(exc) == "duplicate_key":
                from .ingestion_runtime import _slugify_key

                new_topic_key = _slugify_key(edited_label)
            else:
                handler._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return True

        with ingestion_runtime._lock:
            session = ingestion_runtime._sessions.get(session_id)
            if session:
                doc = _find_doc(session.get("documents", []), doc_id)
                if doc:
                    doc["detected_topic"] = new_topic_key
                    doc["batch_type"] = batch_type
                    doc["detected_type"] = batch_type
                    doc["combined_confidence"] = 1.0
                    doc["classification_source"] = "autogenerar"
                    doc["is_raw"] = False
                    doc["status"] = "queued"
                    doc["stage"] = "queued"
                    from datetime import datetime, timezone

                    doc["updated_at"] = (
                        datetime.now(timezone.utc).replace(microsecond=0).isoformat()
                    )
                    ingestion_runtime._save_session_locked(session)
        handler._send_json(
            HTTPStatus.OK,
            {
                "ok": True,
                "new_topic": new_topic_key,
                "document": {
                    "doc_id": doc_id,
                    "status": "queued",
                    "batch_type": batch_type,
                    "detected_topic": new_topic_key,
                    "combined_confidence": 1.0,
                    "classification_source": "autogenerar",
                    "is_raw": False,
                },
            },
        )
        return True

    match_resolve_dup = _INGESTION_RESOLVE_DUPLICATE_RE.match(path)
    if match_resolve_dup:
        session_id = match_resolve_dup.group(1)
        doc_id = match_resolve_dup.group(2)
        payload = handler._read_json_payload()
        if payload is None:
            return True
        action = str(payload.get("action", "")).strip()
        if action not in {"replace", "add_new", "discard"}:
            handler._send_json(
                HTTPStatus.BAD_REQUEST, {"error": f"action invalido: {action}"}
            )
            return True
        with ingestion_runtime._lock:
            session = ingestion_runtime._sessions.get(session_id)
            if session is None:
                handler._send_json(
                    HTTPStatus.NOT_FOUND, {"error": "session_not_found"}
                )
                return True
            doc = _find_doc(session.get("documents", []), doc_id)
            if doc is None:
                handler._send_json(
                    HTTPStatus.NOT_FOUND, {"error": "document_not_found"}
                )
                return True

            if action == "replace":
                existing_doc_id = doc.get("dedup_existing_doc_id")
                purged = 0
                if existing_doc_id:
                    try:
                        from .ingestion_dedup import purge_document
                        from .supabase_client import get_supabase_client as get_client

                        client = get_client()
                        purged = purge_document(
                            existing_doc_id, session.get("corpus", ""), client
                        )
                    except Exception:  # noqa: BLE001
                        pass
                    doc["replaced_doc_id"] = existing_doc_id
                    doc["doc_id"] = existing_doc_id
                doc["status"] = "queued"
                doc["dedup_match_type"] = None
                ingestion_runtime._save_session_locked(session)
                handler._send_json(
                    HTTPStatus.OK,
                    {
                        "ok": True,
                        "document": {
                            "doc_id": doc["doc_id"],
                            "status": "queued",
                            "purged_chunks": purged,
                        },
                    },
                )
            elif action == "add_new":
                doc["status"] = "queued"
                doc["dedup_match_type"] = None
                ingestion_runtime._save_session_locked(session)
                handler._send_json(
                    HTTPStatus.OK,
                    {
                        "ok": True,
                        "document": {"doc_id": doc["doc_id"], "status": "queued"},
                    },
                )
            else:  # discard
                session["documents"] = [
                    d for d in session.get("documents", []) if d.get("doc_id") != doc_id
                ]
                ingestion_runtime._save_session_locked(session)
                handler._send_json(
                    HTTPStatus.OK,
                    {
                        "ok": True,
                        "document": {"doc_id": doc_id, "status": "discarded"},
                    },
                )
        return True

    match_auto = _INGESTION_AUTO_PROCESS_RE.match(path)
    if match_auto:
        session_id = match_auto.group(1)
        payload = handler._read_json_payload()
        if payload is None:
            return True
        max_concurrency = int(payload.get("max_concurrency", 5))
        auto_accept_threshold = float(payload.get("auto_accept_threshold", 0.95))
        with ingestion_runtime._lock:
            session = ingestion_runtime._sessions.get(session_id)
            if session is None:
                handler._send_json(
                    HTTPStatus.NOT_FOUND, {"error": "session_not_found"}
                )
                return True
            queued = 0
            auto_queued = 0
            raw_blocked = 0
            from datetime import datetime, timezone

            now_iso = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            force_queue = auto_accept_threshold <= 0.0
            for doc in session.get("documents", []):
                status = doc.get("status", "")
                if status == "queued":
                    queued += 1
                elif status in ("raw", "needs_classification"):
                    conf = float(doc.get("combined_confidence", 0) or 0)
                    has_topic = bool(doc.get("detected_topic"))
                    has_type = bool(doc.get("detected_type"))
                    if force_queue or (
                        conf >= auto_accept_threshold and has_topic and has_type
                    ):
                        doc["status"] = "queued"
                        doc["stage"] = "queued"
                        doc["is_raw"] = False
                        doc["classification_source"] = (
                            doc.get("classification_source") or "auto_accepted"
                        )
                        doc["updated_at"] = now_iso
                        auto_queued += 1
                        queued += 1
                    else:
                        raw_blocked += 1
            session["auto_processing"] = True
            ingestion_runtime._save_session_locked(session)
        handler._send_json(
            HTTPStatus.OK,
            {
                "ok": True,
                "session_id": session_id,
                "auto_processing": True,
                "queued": queued,
                "auto_queued": auto_queued,
                "raw_blocked": raw_blocked,
                "active_slots": 0,
                "max_concurrency": max_concurrency,
            },
        )
        return True

    match_files = deps["ingestion_files_route_re"].match(path)
    if match_files:
        session_id = match_files.group(1)
        filename = str(handler.headers.get("X-Upload-Filename", "")).strip()
        mime = (
            str(handler.headers.get("X-Upload-Mime", "")).strip()
            or "application/octet-stream"
        )
        if not filename:
            handler._send_json(
                HTTPStatus.BAD_REQUEST,
                {"error": "`X-Upload-Filename` es obligatorio."},
            )
            return True

        length_raw = handler.headers.get("Content-Length", "0")
        try:
            length = int(length_raw)
        except ValueError:
            handler._send_json(
                HTTPStatus.BAD_REQUEST, {"error": "Content-Length invalido."}
            )
            return True
        if length <= 0:
            handler._send_json(
                HTTPStatus.BAD_REQUEST, {"error": "Body vacio en upload."}
            )
            return True

        batch_type = (
            str(handler.headers.get("X-Upload-Batch-Type", "")).strip()
            or "normative_base"
        )
        source_relative_path = (
            str(handler.headers.get("X-Upload-Relative-Path", "")).strip() or None
        )
        autodetect = batch_type in ("autogenerar", "autodetectar")
        if not autodetect and batch_type not in {
            "normative_base",
            "interpretative_guidance",
            "practica_erp",
        }:
            handler._send_json(
                HTTPStatus.BAD_REQUEST,
                {"error": f"batch_type invalido: {batch_type}"},
            )
            return True

        content = handler.rfile.read(length)

        content_hash = hashlib.sha256(content).hexdigest()
        dedup_info: dict[str, Any] = {}
        try:
            from .ingestion_dedup import check_duplicate
            from .supabase_client import get_supabase_client as get_client

            client = get_client()
            body_preview_text = content[:5120].decode("utf-8", errors="replace")
            with ingestion_runtime._lock:
                sess = ingestion_runtime._sessions.get(session_id)
            corpus = str((sess or {}).get("corpus", "")) if sess else ""
            dedup_result = check_duplicate(
                filename, content_hash, body_preview_text, corpus, client
            )
            if dedup_result.is_duplicate:
                dedup_info = {
                    "dedup_match_type": dedup_result.match_type,
                    "dedup_match_reason": dedup_result.match_reason,
                    "dedup_existing_doc_id": dedup_result.existing_doc_id,
                    "dedup_existing_filename": dedup_result.existing_filename,
                }
        except Exception:  # noqa: BLE001
            pass

        classify_info: dict[str, Any] = {}
        effective_batch_type = "normative_base" if autodetect else batch_type
        if autodetect:
            try:
                from .ingestion_classifier import classify_upload

                cls_result = classify_upload(filename, content)
                classify_info = {
                    "detected_topic": cls_result.detected_topic,
                    "topic_confidence": cls_result.topic_confidence,
                    "detected_type": cls_result.detected_type,
                    "type_confidence": cls_result.type_confidence,
                    "combined_confidence": cls_result.combined_confidence,
                    "classification_source": cls_result.topic_source or "keywords",
                    "is_raw": cls_result.is_raw,
                    "suggestion_topic": cls_result.suggestion_topic,
                    "suggestion_type": cls_result.suggestion_type,
                }
                if cls_result.detected_type and not cls_result.is_raw:
                    effective_batch_type = cls_result.detected_type
            except Exception:  # noqa: BLE001
                pass

        try:
            document = ingestion_runtime.add_file(
                session_id,
                filename=filename,
                mime=mime,
                content=content,
                batch_type=effective_batch_type,
            )
        except KeyError:
            handler._send_json(HTTPStatus.NOT_FOUND, {"error": "session_not_found"})
            return True
        except RuntimeError as exc:
            if str(exc) == "session_processing":
                handler._send_json(
                    HTTPStatus.CONFLICT,
                    {
                        "error": "session_processing",
                        "details": "No se pueden agregar archivos mientras el lote está en proceso.",
                    },
                )
                return True
            handler._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": "upload_failed", "details": str(exc)},
            )
            return True

        if (dedup_info or classify_info or source_relative_path) and document.status != "bounced":
            with ingestion_runtime._lock:
                sess_data = ingestion_runtime._sessions.get(session_id)
                if sess_data:
                    doc_internal = _find_doc(sess_data.get("documents", []), document.doc_id)
                    if doc_internal and str(doc_internal.get("status")) != "bounced":
                        doc_internal.update(classify_info)
                        doc_internal.update(dedup_info)
                        if source_relative_path:
                            doc_internal["source_relative_path"] = source_relative_path
                        dedup_type = dedup_info.get("dedup_match_type")
                        if dedup_type == "exact_duplicate":
                            doc_internal["status"] = "skipped_duplicate"
                            doc_internal["stage"] = "skipped_duplicate"
                        elif dedup_type in ("near_duplicate", "revision"):
                            doc_internal["status"] = "pending_dedup"
                            doc_internal["stage"] = "pending_dedup"
                            doc_internal["duplicate_of"] = dedup_info.get(
                                "dedup_existing_doc_id"
                            )
                        elif classify_info.get("is_raw"):
                            doc_internal["status"] = "raw"
                            doc_internal["stage"] = "raw"
                        ingestion_runtime._save_session_locked(sess_data)
                    if doc_internal:
                        document = ingestion_runtime._materialize_document(doc_internal)

        handler._send_json(HTTPStatus.OK, {"ok": True, "document": document.to_dict()})
        return True

    match_process = deps["ingestion_process_route_re"].match(path)
    if match_process:
        session_id = match_process.group(1)
        try:
            result = ingestion_runtime.start_processing(session_id)
        except KeyError:
            handler._send_json(HTTPStatus.NOT_FOUND, {"error": "session_not_found"})
            return True
        handler._send_json(HTTPStatus.OK, {"ok": True, **result})
        return True

    match_retry = deps["ingestion_retry_route_re"].match(path)
    if match_retry:
        session_id = match_retry.group(1)
        try:
            result = ingestion_runtime.retry(session_id)
        except KeyError:
            handler._send_json(HTTPStatus.NOT_FOUND, {"error": "session_not_found"})
            return True
        handler._send_json(HTTPStatus.OK, {"ok": True, **result})
        return True

    match_validate = deps["ingestion_validate_batch_route_re"].match(path)
    if match_validate:
        session_id = match_validate.group(1)
        try:
            result = ingestion_runtime.start_processing(
                session_id, retry_failed=False, gate_only=True
            )
        except KeyError:
            handler._send_json(HTTPStatus.NOT_FOUND, {"error": "session_not_found"})
            return True
        except RuntimeError as exc:
            if str(exc) == "session_processing":
                handler._send_json(
                    HTTPStatus.CONFLICT,
                    {"error": "session_processing", "details": "Sesión en proceso."},
                )
                return True
            raise
        handler._send_json(HTTPStatus.OK, {"ok": True, **result})
        return True

    match_delete_failed = deps["ingestion_delete_failed_route_re"].match(path)
    if match_delete_failed:
        session_id = match_delete_failed.group(1)
        try:
            result = ingestion_runtime.delete_failed(session_id)
        except KeyError:
            handler._send_json(HTTPStatus.NOT_FOUND, {"error": "session_not_found"})
            return True
        except RuntimeError as exc:
            if str(exc) == "session_processing":
                handler._send_json(
                    HTTPStatus.CONFLICT,
                    {
                        "error": "session_processing",
                        "details": "No se pueden eliminar fallidos mientras el lote está en proceso.",
                    },
                )
                return True
            handler._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": "delete_failed_error", "details": str(exc)},
            )
            return True
        handler._send_json(HTTPStatus.OK, {"ok": True, **result})
        return True

    match_stop = deps["ingestion_stop_route_re"].match(path)
    if match_stop:
        session_id = match_stop.group(1)
        try:
            result = ingestion_runtime.stop_processing(session_id)
        except KeyError:
            handler._send_json(HTTPStatus.NOT_FOUND, {"error": "session_not_found"})
            return True
        except Exception as exc:  # noqa: BLE001
            handler._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": "stop_error", "details": str(exc)},
            )
            return True
        handler._send_json(HTTPStatus.OK, {"ok": True, **result})
        return True

    match_clear = deps["ingestion_clear_batch_route_re"].match(path)
    if match_clear:
        session_id = match_clear.group(1)
        try:
            result = ingestion_runtime.clear_batch(session_id)
        except KeyError:
            handler._send_json(HTTPStatus.NOT_FOUND, {"error": "session_not_found"})
            return True
        except RuntimeError as exc:
            if str(exc) == "session_processing":
                handler._send_json(
                    HTTPStatus.CONFLICT,
                    {
                        "error": "session_processing",
                        "details": "No se puede limpiar el lote mientras está en proceso.",
                    },
                )
                return True
            handler._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": "clear_batch_error", "details": str(exc)},
            )
            return True
        handler._send_json(HTTPStatus.OK, {"ok": True, **result})
        return True

    if path == "/api/ingestion/preflight":
        payload = handler._read_json_payload()
        if payload is None:
            return True
        files_raw = payload.get("files")
        if not isinstance(files_raw, list) or not files_raw:
            handler._send_json(
                HTTPStatus.BAD_REQUEST, {"error": "`files` debe ser una lista no vacia."}
            )
            return True
        corpus = str(payload.get("corpus", "autogenerar")).strip()
        try:
            from .ingestion_preflight import run_preflight, manifest_to_dict

            client = None
            try:
                from .supabase_client import get_supabase_client

                client = get_supabase_client()
            except Exception:  # noqa: BLE001
                pass
            ledger = None
            try:
                ledger_path = (
                    ingestion_runtime.workspace_root
                    / "artifacts"
                    / "ingestion"
                    / "ledger.json"
                )
                if ledger_path.exists():
                    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                pass
            wip_checksums: dict[str, dict[str, str]] = {}
            try:
                for session in ingestion_runtime._sessions.values():
                    for doc in session.get("documents", []):
                        cs = str(doc.get("checksum", "")).strip()
                        if cs and doc.get("status") not in ("failed", "skipped_duplicate"):
                            wip_checksums[cs] = {
                                "doc_id": str(doc.get("doc_id", "")),
                                "session_id": str(session.get("session_id", "")),
                            }
            except Exception:  # noqa: BLE001
                pass
            manifest = run_preflight(
                files_raw, corpus, client, ledger=ledger, wip_checksums=wip_checksums
            )
            handler._send_json(
                HTTPStatus.OK, {"ok": True, "manifest": manifest_to_dict(manifest)}
            )
        except Exception as exc:  # noqa: BLE001
            handler._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": "preflight_failed", "details": str(exc)},
            )
        return True

    match_purge = _INGESTION_PURGE_AND_REPLACE_RE.match(path)
    if match_purge:
        session_id = match_purge.group(1)
        payload = handler._read_json_payload()
        if payload is None:
            return True
        doc_ids = payload.get("doc_ids")
        if not isinstance(doc_ids, list) or not doc_ids:
            handler._send_json(
                HTTPStatus.BAD_REQUEST, {"error": "`doc_ids` debe ser una lista no vacia."}
            )
            return True
        corpus = str(payload.get("corpus", "")).strip()
        if not corpus:
            with ingestion_runtime._lock:
                sess = ingestion_runtime._sessions.get(session_id)
            if sess:
                corpus = str(sess.get("corpus", ""))
        if not corpus:
            handler._send_json(
                HTTPStatus.BAD_REQUEST, {"error": "`corpus` es obligatorio."}
            )
            return True
        try:
            from .ingestion_dedup import purge_document
            from .supabase_client import get_supabase_client as get_client

            client = get_client()
            details = []
            total_chunks = 0
            for doc_id in doc_ids:
                doc_id = str(doc_id).strip()
                if not doc_id:
                    continue
                chunks_deleted = purge_document(doc_id, corpus, client)
                total_chunks += chunks_deleted
                details.append({"doc_id": doc_id, "chunks_deleted": chunks_deleted})
            handler._send_json(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "purged": len(details),
                    "chunks_deleted": total_chunks,
                    "details": details,
                },
            )
        except Exception as exc:  # noqa: BLE001
            handler._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": "purge_failed", "details": str(exc)},
            )
        return True

    return False
