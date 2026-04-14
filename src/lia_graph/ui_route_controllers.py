from __future__ import annotations

import html
import mimetypes
from datetime import datetime
from http import HTTPStatus
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote


_USER_MILESTONE_ORDER: tuple[tuple[str, str], ...] = (
    ("main_chat_displayed", "Main chat"),
    ("response_bubble_highlighted", "Burbuja resaltada"),
    ("normative_displayed", "Normativa"),
    ("expert_panel_displayed", "Interpretación de expertos"),
)
_USER_MILESTONE_EVENT_MAP = {
    "main_chat_displayed": "chat_run.ui.main_chat_displayed",
    "response_bubble_highlighted": "chat_run.ui.response_bubble_highlighted",
    "normative_displayed": "chat_run.ui.normative_displayed",
    "expert_panel_displayed": "chat_run.ui.expert_panel_displayed",
}
_TECHNICAL_STAGE_LABELS = {
    "supabase_gate": "Supabase gate",
    "intake": "Intake",
    "planner": "Planner",
    "retrieval": "Retrieval",
    "compose": "Compose",
    "verify": "Verify",
    "finalize": "Finalize",
    "pipeline": "Pipeline",
}


def _parse_iso_datetime(value: Any) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _coerce_ms(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed < 0:
        return 0.0
    return round(parsed, 2)


def _duration_ms_between(start_value: Any, end_value: Any) -> float | None:
    start = _parse_iso_datetime(start_value)
    end = _parse_iso_datetime(end_value)
    if start is None or end is None:
        return None
    return round(max(0.0, (end - start).total_seconds() * 1000), 2)


def _technical_stage_label(stage: Any) -> str:
    normalized = str(stage or "").strip().lower()
    if normalized in _TECHNICAL_STAGE_LABELS:
        return _TECHNICAL_STAGE_LABELS[normalized]
    if not normalized:
        return "-"
    return normalized.replace("_", " ").strip().title()


def _resolve_pipeline_total_ms(run: dict[str, Any] | None, timeline: list[dict[str, Any]]) -> float:
    summary = dict((run or {}).get("summary") or {})
    direct = _coerce_ms(summary.get("pipeline_total_ms"))
    if direct is not None:
        return direct
    ended = _duration_ms_between((run or {}).get("started_at"), (run or {}).get("ended_at"))
    if ended is not None:
        return ended
    cumulative = 0.0
    for item in timeline:
        duration_ms = _coerce_ms(item.get("duration_ms"))
        cumulative += float(duration_ms or 0.0)
    return round(cumulative, 2)


def _build_technical_waterfall(run: dict[str, Any] | None, timeline: list[dict[str, Any]]) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    offset_ms = 0.0
    for index, event in enumerate(timeline):
        duration_ms = _coerce_ms(event.get("duration_ms"))
        if duration_ms is None:
            duration_ms = 0.0
        cumulative_ms = round(offset_ms + duration_ms, 2)
        steps.append(
            {
                "id": f"technical_{index}",
                "label": _technical_stage_label(event.get("stage")),
                "stage": str(event.get("stage") or "").strip() or None,
                "status": str(event.get("status") or "").strip() or "ok",
                "duration_ms": round(duration_ms, 2),
                "offset_ms": round(offset_ms, 2),
                "cumulative_ms": cumulative_ms,
                "absolute_elapsed_ms": cumulative_ms,
                "details": dict(event.get("details") or {}),
                "at": str(event.get("at") or "").strip() or None,
                "kind": "technical",
            }
        )
        offset_ms = cumulative_ms
    return {
        "kind": "technical",
        "title": "Milestones técnicos",
        "total_ms": _resolve_pipeline_total_ms(run, timeline),
        "available_steps": len(steps),
        "steps": steps,
    }


def _extract_user_milestone_map(chat_run: Any, events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    request_start = getattr(chat_run, "request_received_at", None) if chat_run is not None else None
    milestones: dict[str, dict[str, Any]] = {}
    for milestone_id, event_type in _USER_MILESTONE_EVENT_MAP.items():
        matching_event = next(
            (item for item in events if str(item.get("event_type") or "").strip() == event_type),
            None,
        )
        if matching_event is None:
            continue
        payload = dict(matching_event.get("payload") or {})
        elapsed_ms = _coerce_ms(payload.get("elapsed_ms"))
        if elapsed_ms is None:
            elapsed_ms = _duration_ms_between(request_start, matching_event.get("at"))
        if elapsed_ms is None:
            continue
        milestones[milestone_id] = {
            "elapsed_ms": elapsed_ms,
            "at": str(matching_event.get("at") or "").strip() or None,
            "payload": payload,
        }
    if "main_chat_displayed" not in milestones and chat_run is not None:
        fallback_elapsed_ms = _duration_ms_between(
            getattr(chat_run, "request_received_at", None),
            getattr(chat_run, "first_visible_answer_at", None),
        )
        if fallback_elapsed_ms is not None:
            milestones["main_chat_displayed"] = {
                "elapsed_ms": fallback_elapsed_ms,
                "at": getattr(chat_run, "first_visible_answer_at", None),
                "payload": {"source": "server_fallback"},
            }
    return milestones


def _build_user_waterfall(chat_run: Any, events: list[dict[str, Any]]) -> dict[str, Any]:
    milestone_map = _extract_user_milestone_map(chat_run, events)
    steps: list[dict[str, Any]] = []
    prior_elapsed_ms = 0.0
    for milestone_id, label in _USER_MILESTONE_ORDER:
        milestone = milestone_map.get(milestone_id)
        if milestone is None:
            steps.append(
                {
                    "id": milestone_id,
                    "label": label,
                    "status": "missing",
                    "duration_ms": None,
                    "offset_ms": round(prior_elapsed_ms, 2),
                    "cumulative_ms": None,
                    "absolute_elapsed_ms": None,
                    "details": {},
                    "at": None,
                    "kind": "user",
                }
            )
            continue

        absolute_elapsed_ms = float(milestone["elapsed_ms"])
        duration_ms = round(max(0.0, absolute_elapsed_ms - prior_elapsed_ms), 2)
        cumulative_ms = round(prior_elapsed_ms + duration_ms, 2)
        details = dict(milestone.get("payload") or {})
        if absolute_elapsed_ms < prior_elapsed_ms:
            details["out_of_order"] = True
        steps.append(
            {
                "id": milestone_id,
                "label": label,
                "status": str(details.get("status") or "ok"),
                "duration_ms": duration_ms,
                "offset_ms": round(prior_elapsed_ms, 2),
                "cumulative_ms": cumulative_ms,
                "absolute_elapsed_ms": round(absolute_elapsed_ms, 2),
                "details": details,
                "at": milestone.get("at"),
                "kind": "user",
            }
        )
        prior_elapsed_ms = max(prior_elapsed_ms, absolute_elapsed_ms)

    return {
        "kind": "user",
        "title": "Milestones visibles al usuario",
        "chat_run_id": getattr(chat_run, "chat_run_id", None) if chat_run is not None else None,
        "total_ms": round(prior_elapsed_ms, 2),
        "available_steps": sum(1 for item in steps if item.get("duration_ms") is not None),
        "steps": steps,
    }


def _build_corpus_target_status(target: str) -> dict[str, Any]:
    """Query a single Supabase target for corpus generation status."""
    from .supabase_client import create_supabase_client_for_target

    try:
        client = create_supabase_client_for_target(target)
        gen_row = (
            client.table("corpus_generations")
            .select("*")
            .eq("is_active", True)
            .order("activated_at", desc=True)
            .limit(1)
            .execute()
        )
        if not gen_row.data:
            return {"available": True, "generation_id": None, "documents": 0, "chunks": 0}
        row = gen_row.data[0]

        doc_count = int(
            (client.table("documents")
             .select("doc_id", count="exact")
             .eq("sync_generation", row["generation_id"])
             .limit(0)
             .execute()).count or 0
        )
        chunk_count = int(
            (client.table("document_chunks")
             .select("chunk_id", count="exact")
             .eq("sync_generation", row["generation_id"])
             .limit(0)
             .execute()).count or 0
        )
        null_embeddings = int(
            (client.table("document_chunks")
             .select("chunk_id", count="exact")
             .eq("sync_generation", row["generation_id"])
             .is_("embedding", "null")
             .limit(0)
             .execute()).count or 0
        )

        return {
            "available": True,
            "generation_id": row.get("generation_id"),
            "documents": doc_count,
            "chunks": chunk_count,
            "embeddings_complete": null_embeddings == 0,
            "knowledge_class_counts": row.get("knowledge_class_counts") or {},
            "activated_at": row.get("activated_at") or "",
        }
    except Exception as exc:
        return {"available": False, "error": str(exc)}


def _build_corpus_status(*, jobs_path: Path, workspace_root: Path) -> dict[str, Any]:
    from .corpus_ops import build_corpus_status

    return build_corpus_status(base_dir=jobs_path, workspace_root=workspace_root)


def handle_ops_get(handler: Any, path: str, parsed: Any, *, deps: dict[str, Any]) -> bool:
    if path == "/api/ops/embedding-status":
        try:
            from .embedding_ops import build_embedding_status
            status = build_embedding_status(target="wip")
            handler._send_json(HTTPStatus.OK, status)
        except Exception as exc:
            handler._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
        return True
    if path == "/api/ops/reindex-status":
        try:
            from .reindex_ops import build_reindex_status
            status = build_reindex_status()
            handler._send_json(HTTPStatus.OK, status)
        except Exception as exc:
            handler._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
        return True
    if path == "/api/ops/corpus-status":
        try:
            status = _build_corpus_status(
                jobs_path=deps["jobs_path"],
                workspace_root=deps["workspace_root"],
            )
            handler._send_json(HTTPStatus.OK, status)
        except Exception as exc:
            handler._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
        return True
    if path == "/api/health":
        handler._send_json(HTTPStatus.OK, {"ok": True})
        return True
    if path == "/api/build-info":
        handler._send_json(HTTPStatus.OK, {"ok": True, "build_info": deps["build_info_payload"]()})
        return True
    if path == "/api/chat/runs/metrics":
        query = parse_qs(parsed.query)
        limit_raw = str((query.get("limit") or ["200"])[0]).strip() or "200"
        try:
            limit = int(limit_raw)
        except ValueError:
            handler._send_json(HTTPStatus.BAD_REQUEST, {"error": "`limit` debe ser entero."})
            return True
        metrics = deps["summarize_chat_run_metrics"](
            base_dir=deps["chat_runs_path"],
            limit=limit,
        )
        handler._send_json(HTTPStatus.OK, {"ok": True, "metrics": metrics})
        return True

    chat_session_metrics_match = deps["chat_session_metrics_route_re"].match(path)
    if chat_session_metrics_match:
        session_id = str(chat_session_metrics_match.group(1)).strip()
        try:
            session = deps["get_chat_session_metrics"](
                session_id=session_id,
                path=deps["chat_session_metrics_path"],
            )
        except ValueError as exc:
            handler._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return True
        handler._send_json(HTTPStatus.OK, {"ok": True, "session": session})
        return True

    chat_run_match = deps["chat_run_route_re"].match(path)
    if chat_run_match:
        chat_run_id = str(chat_run_match.group(1) or "").strip()
        query = parse_qs(parsed.query)
        include_events = str((query.get("include_events") or ["0"])[0]).strip().lower() in {"1", "true", "yes"}
        record = deps["get_chat_run"](chat_run_id, base_dir=deps["chat_runs_path"])
        if record is None:
            handler._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "chat_run_not_found", "chat_run_id": chat_run_id})
            return True
        if record.status == "completed" and isinstance(record.response_payload, dict) and record.response_payload:
            payload = dict(record.response_payload)
            if include_events:
                payload.setdefault("chat_run_events", deps["get_chat_run_events"](chat_run_id, base_dir=deps["chat_runs_path"]))
            handler._send_json(HTTPStatus.OK, payload)
            deps["get_chat_run_coordinator"]().mark_response_sent(chat_run_id, base_dir=deps["chat_runs_path"])
            return True
        if record.status == "failed" and isinstance(record.error_payload, dict) and record.error_payload:
            payload = dict(record.error_payload)
            if include_events:
                payload.setdefault("chat_run_events", deps["get_chat_run_events"](chat_run_id, base_dir=deps["chat_runs_path"]))
            error = payload.get("error")
            status = HTTPStatus.INTERNAL_SERVER_ERROR
            if isinstance(error, dict):
                try:
                    status = HTTPStatus(int(error.get("http_status") or HTTPStatus.INTERNAL_SERVER_ERROR))
                except ValueError:
                    status = HTTPStatus.INTERNAL_SERVER_ERROR
            handler._send_json(status, payload)
            deps["get_chat_run_coordinator"]().mark_response_sent(chat_run_id, base_dir=deps["chat_runs_path"])
            return True

        body = {
            "ok": False,
            "status": "in_progress",
            "chat_run_id": record.chat_run_id,
            "trace_id": record.trace_id,
            "session_id": record.session_id,
            "client_turn_id": record.client_turn_id,
            "pipeline_run_id": record.pipeline_run_id,
            "request_received_at": record.request_received_at or None,
            "pipeline_started_at": record.pipeline_started_at or None,
            "first_visible_answer_at": record.first_visible_answer_at or None,
            "request": dict(record.request_payload or {}),
        }
        if include_events:
            body["chat_run_events"] = deps["get_chat_run_events"](chat_run_id, base_dir=deps["chat_runs_path"])
        handler._send_json(HTTPStatus.ACCEPTED, body)
        return True

    if path == "/api/ops/runs":
        query = parse_qs(parsed.query)
        limit_raw = str((query.get("limit") or ["50"])[0]).strip() or "50"
        try:
            limit = int(limit_raw)
        except ValueError:
            handler._send_json(HTTPStatus.BAD_REQUEST, {"error": "`limit` debe ser entero."})
            return True
        runs = deps["list_pipeline_c_runs"](limit=limit)
        handler._send_json(HTTPStatus.OK, {"ok": True, "runs": runs})
        return True

    if path == "/api/ops/citation-gaps":
        query = parse_qs(parsed.query)
        limit_raw = str((query.get("limit") or ["100"])[0]).strip() or "100"
        origin = str((query.get("origin") or ["all"])[0]).strip() or "all"
        reference_type = str((query.get("reference_type") or [""])[0]).strip() or None
        try:
            limit = int(limit_raw)
        except ValueError:
            handler._send_json(HTTPStatus.BAD_REQUEST, {"error": "`limit` debe ser entero."})
            return True
        try:
            result = deps["list_citation_gaps"](
                path=deps["citation_gap_registry_path"],
                limit=limit,
                origin=origin,
                reference_type=reference_type,
            )
        except ValueError as exc:
            handler._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return True
        handler._send_json(
            HTTPStatus.OK,
            {
                "ok": True,
                "filters": result.get("filters"),
                "total_rows": result.get("total_rows"),
                "rows": result.get("rows"),
                "updated_at": result.get("updated_at"),
            },
        )
        return True

    run_match = deps["ops_run_route_re"].match(path)
    if run_match:
        run_id = run_match.group(1)
        run = deps["get_pipeline_c_run"](run_id)
        if run is None:
            handler._send_json(HTTPStatus.NOT_FOUND, {"error": "run_not_found"})
            return True
        handler._send_json(HTTPStatus.OK, {"ok": True, "run": run})
        return True

    timeline_match = deps["ops_run_timeline_route_re"].match(path)
    if timeline_match:
        run_id = timeline_match.group(1)
        timeline = deps["get_pipeline_c_timeline"](run_id)
        run = deps["get_pipeline_c_run"](run_id)
        if run is None:
            handler._send_json(HTTPStatus.NOT_FOUND, {"error": "run_not_found"})
            return True
        chat_run_id = str((run or {}).get("chat_run_id") or "").strip()
        chat_run = deps["get_chat_run"](chat_run_id, base_dir=deps["chat_runs_path"]) if chat_run_id else None
        chat_run_events = deps["get_chat_run_events"](chat_run_id, base_dir=deps["chat_runs_path"]) if chat_run_id else []
        handler._send_json(
            HTTPStatus.OK,
            {
                "ok": True,
                "run_id": run_id,
                "run": run,
                "timeline": timeline,
                "technical_waterfall": _build_technical_waterfall(run, timeline),
                "user_waterfall": _build_user_waterfall(chat_run, chat_run_events),
            },
        )
        return True

    if path == "/api/orchestration/settings":
        try:
            settings, _, _ = deps["load_runtime_orchestration_settings"]()
        except deps["orchestration_settings_invalid_error"] as exc:
            handler._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {
                    "ok": False,
                    "error": "orchestration_settings_invalid",
                    "details": str(exc),
                },
            )
            return True
        handler._send_json(HTTPStatus.OK, {"ok": True, "settings": settings})
        return True

    return False


def _build_form_guides_content_payload(package: Any, *, official_form_pdf: Any, deps: dict[str, Any]) -> dict[str, Any]:
    manifest = package.manifest
    official_form_pdf_url = deps["coerce_http_url"](getattr(official_form_pdf, "url", "")) if official_form_pdf else ""
    return {
        "ok": True,
        "manifest": {
            "reference_key": manifest.reference_key,
            "title": manifest.title,
            "form_version": manifest.form_version,
            "profile_id": manifest.profile_id,
            "profile_label": manifest.profile_label,
            "supported_views": list(manifest.supported_views),
            "last_verified_date": manifest.last_verified_date,
            "disclaimer": manifest.disclaimer,
        },
        "structured_sections": [
            {
                "section_id": section.section_id,
                "title": section.title,
                "purpose": section.purpose,
                "what_to_review": section.what_to_review,
                "profile_differences": section.profile_differences,
                "common_errors": section.common_errors,
                "warnings": section.warnings,
            }
            for section in package.structured_sections
        ],
        "interactive_map": [
            {
                "field_id": hotspot.field_id,
                "label": hotspot.label,
                "page": hotspot.page,
                "bbox": list(hotspot.bbox),
                "marker_bbox": list(hotspot.marker_bbox) if hotspot.marker_bbox is not None else None,
                "section": hotspot.section,
                "casilla": hotspot.casilla,
                "año_gravable": hotspot.año_gravable,
                "profiles": list(hotspot.profiles),
                "instruction_md": hotspot.instruction_md,
                "official_dian_instruction": hotspot.official_dian_instruction,
                "what_to_review_before_filling": hotspot.what_to_review_before_filling,
                "common_errors": hotspot.common_errors,
                "warnings": hotspot.warnings,
                "source_ids": list(hotspot.source_ids),
                "last_verified_date": hotspot.last_verified_date,
            }
            for hotspot in package.interactive_map
        ],
        "sources": [
            {
                "source_id": source.source_id,
                "title": source.title,
                "url": source.url,
                "source_type": source.source_type,
                "authority": source.authority,
                "is_primary": source.is_primary,
                "last_checked_date": source.last_checked_date,
                "notes": source.notes,
            }
            for source in package.sources
        ],
        "official_pdf_url": official_form_pdf_url,
        "official_pdf_authority": getattr(official_form_pdf, "authority", "") if official_form_pdf else "",
        "page_assets": deps["build_form_guide_page_assets"](package),
        "pages": list(package.pages),
        "disclaimer": manifest.disclaimer,
    }


def handle_form_guides_get(
    handler: Any,
    path: str,
    parsed: Any,
    *,
    form_guides_root: Path,
    deps: dict[str, Any],
) -> bool:
    if path == "/api/form-guides/catalog":
        query = parse_qs(parsed.query)
        reference_key = str((query.get("reference_key") or [""])[0]).strip()
        entries = deps["list_available_guides"](root=form_guides_root)
        if reference_key:
            entry = deps["find_catalog_entry_by_reference_key"](entries, reference_key)
            if entry is None:
                handler._send_json(HTTPStatus.NOT_FOUND, {"error": "guide_not_found"})
                return True
            handler._send_json(
                HTTPStatus.OK,
                {
                    "ok": True,
                    **entry,
                    "guide": dict(entry),
                    "guides": [dict(entry)],
                },
            )
            return True

        handler._send_json(
            HTTPStatus.OK,
            {
                "ok": True,
                "guides": [deps["serialize_guide_catalog_entry"](entry) for entry in entries],
            },
        )
        return True

    if path == "/api/form-guides/content":
        query = parse_qs(parsed.query)
        reference_key = str((query.get("reference_key") or [""])[0]).strip()
        if not reference_key:
            handler._send_json(HTTPStatus.BAD_REQUEST, {"error": "`reference_key` requerido."})
            return True
        profile = str((query.get("profile") or [""])[0]).strip() or None
        package = deps["resolve_guide"](reference_key, profile=profile, root=form_guides_root)
        if package is None:
            handler._send_json(HTTPStatus.NOT_FOUND, {"error": "guide_not_found"})
            return True
        official_form_pdf = deps["find_official_form_pdf_source"](package)
        handler._send_json(
            HTTPStatus.OK,
            _build_form_guides_content_payload(package, official_form_pdf=official_form_pdf, deps=deps),
        )
        return True

    if path == "/api/form-guides/asset":
        query = parse_qs(parsed.query)
        reference_key = str((query.get("reference_key") or [""])[0]).strip()
        asset_name = str((query.get("name") or [""])[0]).strip()
        if not reference_key or not asset_name:
            handler._send_json(
                HTTPStatus.BAD_REQUEST,
                {"error": "`reference_key` y `name` son requeridos."},
            )
            return True
        profile = str((query.get("profile") or [""])[0]).strip() or None
        package = deps["resolve_guide"](reference_key, profile=profile, root=form_guides_root)
        if package is None:
            handler._send_json(HTTPStatus.NOT_FOUND, {"error": "guide_not_found"})
            return True
        if asset_name not in set(package.pages):
            handler._send_json(HTTPStatus.NOT_FOUND, {"error": "guide_asset_not_found"})
            return True
        guide_dir = form_guides_root / reference_key.replace(":", "_") / package.manifest.profile_id
        asset_path = (guide_dir / "assets" / asset_name).resolve()
        assets_root = (guide_dir / "assets").resolve()
        if assets_root not in asset_path.parents or not asset_path.is_file():
            handler._send_json(HTTPStatus.NOT_FOUND, {"error": "guide_asset_not_found"})
            return True

        payload = asset_path.read_bytes()
        content_type = mimetypes.guess_type(asset_path.name)[0] or "application/octet-stream"
        handler.send_response(HTTPStatus.OK)
        handler.send_header("Content-Type", content_type)
        handler.send_header("Content-Length", str(len(payload)))
        handler.send_header("Cache-Control", "no-store")
        handler.end_headers()
        handler.wfile.write(payload)
        return True

    if path != "/api/form-guides/download":
        return False

    query = parse_qs(parsed.query)
    reference_key = str((query.get("reference_key") or [""])[0]).strip()
    if not reference_key:
        handler._send_json(HTTPStatus.BAD_REQUEST, {"error": "`reference_key` requerido."})
        return True
    profile = str((query.get("profile") or [""])[0]).strip() or None
    download_format = str((query.get("format") or ["pdf"])[0]).strip().lower() or "pdf"
    package = deps["resolve_guide"](reference_key, profile=profile, root=form_guides_root)
    if package is None:
        handler._send_json(HTTPStatus.NOT_FOUND, {"error": "guide_not_found"})
        return True
    markdown_text = deps["build_guide_markdown_for_pdf"](package)
    if download_format == "md":
        payload = markdown_text.encode("utf-8")
        handler.send_response(HTTPStatus.OK)
        handler.send_header("Content-Type", "text/markdown; charset=utf-8")
        handler.send_header("Content-Length", str(len(payload)))
        handler.send_header("Content-Disposition", f"attachment; filename=\"guia_{reference_key.replace(':', '_')}.md\"")
        handler.end_headers()
        handler.wfile.write(payload)
        return True
    if download_format not in {"pdf", "md"}:
        handler._send_json(HTTPStatus.BAD_REQUEST, {"error": "`format` debe ser pdf|md."})
        return True
    official_form_pdf = deps["find_official_form_pdf_source"](package)
    official_form_pdf_url = deps["coerce_http_url"](getattr(official_form_pdf, "url", "")) if official_form_pdf else ""
    if not official_form_pdf_url:
        handler._send_json(HTTPStatus.NOT_FOUND, {"error": "official_form_pdf_not_found"})
        return True
    handler.send_response(HTTPStatus.FOUND)
    handler.send_header("Location", official_form_pdf_url)
    handler.end_headers()
    return True


def _resolve_source_material(handler: Any, *, doc_id: str, view: str, deps: dict[str, Any]) -> Any | None:
    material = deps["resolve_source_view_material"](doc_id=doc_id, view=view)
    if material is None:
        handler._send_json(HTTPStatus.NOT_FOUND, {"error": "Fuente no encontrada."})
        return None
    if bool(material.get("read_error")):
        handler._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "No se pudo leer el documento local."})
        return None
    return material


def _send_download_bytes(handler: Any, *, payload: bytes, content_type: str, filename: str) -> bool:
    handler.send_response(HTTPStatus.OK)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(payload)))
    handler.send_header("Content-Disposition", f"attachment; filename=\"{filename}\"")
    handler.end_headers()
    handler.wfile.write(payload)
    return True


def _handle_source_view(handler: Any, parsed: Any, *, deps: dict[str, Any]) -> bool:
    query = parse_qs(parsed.query)
    doc_id = str((query.get("doc_id") or [""])[0]).strip()
    view = str((query.get("view") or ["normalized"])[0]).strip().lower() or "normalized"
    question_context = deps["sanitize_question_context"](str((query.get("q") or [""])[0]))
    citation_context = deps["sanitize_question_context"](str((query.get("cq") or [""])[0]), max_chars=240)
    full_raw = str((query.get("full") or [""])[0]).strip().lower()
    show_full_guide = full_raw in {"1", "true", "yes", "full"}
    if not doc_id:
        handler._send_json(HTTPStatus.BAD_REQUEST, {"error": "`doc_id` es obligatorio."})
        return True

    material = _resolve_source_material(handler, doc_id=doc_id, view=view, deps=deps)
    if material is None:
        return True

    requested_row = dict(material.get("requested_row") or {})
    row = dict(material.get("resolved_row") or requested_row or {})
    source_url = str(row.get("url", "")).strip()
    preview_file = material.get("source_file")
    selected_view = str(material.get("selected_view") or view)
    upload_artifact = material.get("upload_artifact")
    if preview_file is None:
        if source_url.startswith(("http://", "https://")):
            handler.send_response(HTTPStatus.FOUND)
            handler.send_header("Location", source_url)
            handler.end_headers()
            return True
        handler._send_json(HTTPStatus.NOT_FOUND, {"error": "Documento local no disponible."})
        return True

    public_text = str(material.get("public_text") or "")
    raw_text = str(material.get("raw_text") or "")
    source_profile = deps["build_user_source_profile"](row, public_text)
    doc_id_q = quote(doc_id, safe="")
    title_plain = deps["resolve_source_display_title"](
        row=requested_row or row,
        doc_id=doc_id,
        raw_text=raw_text,
        public_text=public_text,
    )
    if requested_row:
        title_plain = deps["pick_source_display_title"](
            requested_row=requested_row,
            resolved_row=row,
            doc_id=doc_id,
            raw_text=raw_text,
            public_text=public_text,
        )
    title = html.escape(title_plain)
    local_support_href = deps["build_source_view_href"](
        doc_id=doc_id,
        view=selected_view,
        question_context=question_context,
        citation_context=citation_context,
        full=False,
    )
    full_guide_href = deps["build_source_view_href"](
        doc_id=doc_id,
        view=selected_view,
        question_context=question_context,
        citation_context=citation_context,
        full=True,
    )
    if deps["is_et_article_doc_id"](doc_id):
        summary_markdown = deps["build_et_article_source_view_markdown"](
            doc_id=doc_id,
            source_title=title_plain,
            public_text=public_text,
        )
    elif show_full_guide:
        summary_markdown = deps["build_clean_guide_markdown"](title=title_plain, public_text=public_text)
    else:
        summary_markdown = deps["build_source_view_summary_markdown"](
            doc_id=doc_id,
            source_profile=source_profile,
            source_title=title_plain,
            question_context=question_context,
            citation_context=citation_context,
            full_guide_href=full_guide_href,
            public_text=public_text,
        )
    rendered_content_html = deps["render_source_view_markdown_html"](summary_markdown)
    raw_fallback_html = ""
    if not rendered_content_html and summary_markdown.strip():
        raw_fallback_html = f"<pre class='page-raw' id='raw-content'>{html.escape(summary_markdown)}</pre>"

    tier_label_html = html.escape(str(source_profile.get("tier_label", "")).strip() or "No clasificada")
    provider_label_html = html.escape(str(source_profile.get("provider_label", "")).strip() or "No identificado")
    provider_url = deps["coerce_http_url"](source_profile.get("provider_url", ""))
    warning_text = deps["coerce_optional_text"](source_profile.get("warning", ""))
    if provider_url:
        reference_link_html = (
            f"<a href='{html.escape(provider_url)}' target='_blank' rel='noopener noreferrer'>"
            f"{html.escape(provider_url)}"
            "</a>"
        )
    else:
        reference_link_html = f"<a href='{html.escape(local_support_href)}'>Soporte local en LIA</a>"
        if warning_text:
            reference_link_html = (
                f"{reference_link_html}<br><span style='font-size:.76rem;color:#6b645b;'>"
                f"{html.escape(warning_text)}"
                "</span>"
            )

    reference_button_url = provider_url
    if not reference_button_url and source_url.startswith(("http://", "https://")):
        reference_button_url = source_url

    doc_id_html = html.escape(doc_id)
    official_link_html = (
        f"<a class='btn' href='{html.escape(reference_button_url)}' target='_blank' rel='noopener noreferrer'>"
        "<svg viewBox='0 0 24 24'><path d='M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6'/>"
        "<polyline points='15 3 21 3 21 9'/><line x1='10' y1='14' x2='21' y2='3'/></svg>"
        "Abrir enlace de referencia</a>"
        if reference_button_url.startswith(("http://", "https://"))
        else ""
    )
    switch_view_html = ""
    if preview_file is not None and upload_artifact is not None:
        swap_svg = (
            "<svg viewBox='0 0 24 24'><polyline points='16 3 21 3 21 8'/>"
            "<line x1='4' y1='20' x2='21' y2='3'/>"
            "<polyline points='21 16 21 21 16 21'/>"
            "<line x1='15' y1='15' x2='21' y2='21'/></svg>"
        )
        if selected_view == "original":
            normalized_href = deps["build_source_view_href"](
                doc_id=doc_id,
                view="normalized",
                question_context=question_context,
                citation_context=citation_context,
                full=show_full_guide,
            )
            switch_view_html = (
                f"<a class='btn' href='{html.escape(normalized_href)}'>"
                f"{swap_svg}Ver documento normalizado</a>"
            )
        else:
            original_href = deps["build_source_view_href"](
                doc_id=doc_id,
                view="original",
                question_context=question_context,
                citation_context=citation_context,
                full=show_full_guide,
            )
            switch_view_html = (
                f"<a class='btn' href='{html.escape(original_href)}'>"
                f"{swap_svg}Ver archivo original cargado</a>"
            )
    artifact_label = (
        f"Archivo original cargado ({html.escape(str(preview_file.name))})"
        if selected_view == "original"
        else "Documento normalizado del repositorio"
    )
    download_href = (
        f"/source-download?doc_id={doc_id_q}&view=original&format=original"
        if selected_view == "original"
        else f"/source-download?doc_id={doc_id_q}&view=normalized&format=pdf"
    )
    body = deps["build_source_view_html"](
        title=title,
        doc_id_html=doc_id_html,
        tier_label_html=tier_label_html,
        provider_label_html=provider_label_html,
        reference_link_html=reference_link_html,
        artifact_label=artifact_label,
        download_href=download_href,
        switch_view_html=switch_view_html,
        official_link_html=official_link_html,
        rendered_content_html=rendered_content_html,
        raw_fallback_html=raw_fallback_html,
        show_meta_card=not show_full_guide,
        viewer_note="Documento completo en vista limpia." if show_full_guide else "Resumen enfocado en tu pregunta.",
    ).encode("utf-8")
    handler._send_bytes(
        HTTPStatus.OK,
        body,
        "text/html; charset=utf-8",
        extra_headers={"Cache-Control": "no-store"},
    )
    return True


def _handle_source_download(handler: Any, parsed: Any, *, deps: dict[str, Any]) -> bool:
    query = parse_qs(parsed.query)
    doc_id = str((query.get("doc_id") or [""])[0]).strip()
    view = str((query.get("view") or ["normalized"])[0]).strip().lower() or "normalized"
    download_format = str((query.get("format") or ["pdf"])[0]).strip().lower() or "pdf"
    if not doc_id:
        handler._send_json(HTTPStatus.BAD_REQUEST, {"error": "`doc_id` es obligatorio."})
        return True

    material = _resolve_source_material(handler, doc_id=doc_id, view=view, deps=deps)
    if material is None:
        return True

    requested_row = dict(material.get("requested_row") or {})
    row = dict(material.get("resolved_row") or requested_row or {})
    upload_artifact = material.get("upload_artifact")
    download_file = material.get("source_file")
    selected_view = str(material.get("selected_view") or view)
    if download_file is None:
        handler._send_json(HTTPStatus.NOT_FOUND, {"error": "Documento local no disponible para descarga."})
        return True

    if download_format == "original":
        if selected_view != "original" or upload_artifact is None or not upload_artifact.exists():
            handler._send_json(
                HTTPStatus.NOT_FOUND,
                {"error": "No hay archivo original disponible para descarga."},
            )
            return True
        try:
            payload = upload_artifact.read_bytes()
        except OSError:
            handler._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "No se pudo leer el archivo original."})
            return True
        content_type = mimetypes.guess_type(str(upload_artifact.name))[0] or "application/octet-stream"
        return _send_download_bytes(
            handler,
            payload=payload,
            content_type=content_type,
            filename=upload_artifact.name,
        )

    title_plain = deps["pick_source_display_title"](
        requested_row=requested_row or row,
        resolved_row=row,
        doc_id=doc_id,
        raw_text=str(material.get("raw_text") or ""),
        public_text=str(material.get("public_text") or ""),
    )
    public_text = str(material.get("public_text") or "")
    markdown_payload = deps["build_clean_guide_markdown"](title=title_plain, public_text=public_text)
    download_filename = deps["build_source_download_filename"](
        row=row,
        doc_id=doc_id,
        download_format=download_format,
        fallback_title=title_plain,
    )
    if download_format == "md":
        return _send_download_bytes(
            handler,
            payload=markdown_payload.encode("utf-8"),
            content_type="text/markdown; charset=utf-8",
            filename=download_filename,
        )
    if download_format == "txt":
        return _send_download_bytes(
            handler,
            payload=markdown_payload.encode("utf-8"),
            content_type="text/plain; charset=utf-8",
            filename=download_filename,
        )
    if download_format != "pdf":
        handler._send_json(HTTPStatus.BAD_REQUEST, {"error": "`format` debe ser pdf|md|txt|original."})
        return True
    try:
        payload = deps["build_pdf_from_markdown"](markdown_payload, title=title_plain or doc_id)
    except RuntimeError as exc:
        handler._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
        return True
    return _send_download_bytes(
        handler,
        payload=payload,
        content_type="application/pdf",
        filename=download_filename,
    )


def handle_source_get(handler: Any, path: str, parsed: Any, *, deps: dict[str, Any]) -> bool:
    if path == "/source-view":
        return _handle_source_view(handler, parsed, deps=deps)
    if path == "/source-download":
        return _handle_source_download(handler, parsed, deps=deps)
    return False
