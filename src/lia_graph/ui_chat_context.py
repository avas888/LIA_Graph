from __future__ import annotations

import os as _os
import re as _re
from typing import Any, TypedDict

from .pipeline_c.conversation_state import build_conversation_state
from .pipeline_c.streaming import StructuredMarkdownStreamAssembler


# ---------------------------------------------------------------------------
# Citations preview (W2 Phase 6 — normativa preview during thinking)
# ---------------------------------------------------------------------------

# Max number of candidate citations surfaced in the early preview SSE event.
# Kept intentionally small: the preview is a perception affordance, not a
# replacement for the final citation list. See
# ``docs/next/soporte_normativo_citation_ordering.md`` §§10–15.
_CITATIONS_PREVIEW_MAX: int = 5

_CITATIONS_PREVIEW_ENV: str = "LIA_CITATIONS_PREVIEW"


def _citations_preview_enabled() -> bool:
    """Return True when the ``citations_preview`` SSE event is active.

    Default is ``on``; operators disable it via ``LIA_CITATIONS_PREVIEW=off``
    on Railway for an instant kill switch (no rebuild, no revert).
    """

    raw = _os.environ.get(_CITATIONS_PREVIEW_ENV, "on").strip().lower()
    return raw not in {"0", "false", "no", "n", "off", "disabled"}


# ---------------------------------------------------------------------------
# Shared types
# ---------------------------------------------------------------------------


class ChatRequestContext(TypedDict, total=False):
    payload: dict[str, Any]
    trace_id: str
    session_id: str
    message: str
    normalized_pais: str
    topic: str | None
    requested_topic: str | None
    effective_topic: str | None
    secondary_topics: tuple[str, ...]
    topic_adjusted: bool
    topic_notice: str | None
    topic_adjustment_reason: str
    topic_router_confidence: float
    topic_router_mode: str
    primary_scope_mode: str
    response_route: str
    retrieval_profile: str
    response_depth: str
    first_response_mode: str
    pipeline_message: str
    pipeline_response_route: str
    pipeline_route_override: str | None
    pipeline_route_source: str
    requested_pipeline_variant: str
    pipeline_variant: str
    shadow_pipeline_variant: str | None
    resolved_pipeline_route: Any
    debug_mode: bool
    operation_date: Any
    company_context_payload: Any
    clarification_state: dict[str, Any] | None
    clear_clarification_on_success: bool
    auth_context: Any
    tenant_id: str
    user_id: str
    company_id: str
    integration_id: str
    host_session_id: str
    accountant_id: str
    endpoint: str
    clarification_session_id: str
    conversation_session: Any
    user_turn_persisted: bool
    client_turn_id: str
    chat_run_id: str
    request_fingerprint: str
    chat_run_owner: bool
    conversation_state: dict[str, Any] | None


def _optional_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_NORM_ANCHOR_RE = _re.compile(
    r"\b(?:"
    r"(?:ET\s+)?[Aa]rt(?:\.|[íi]culo)?s?\s*\d+(?:[.\-]\d+)*"
    r"|[Ll]ey\s+\d+(?:\s+de\s+\d{4})?"
    r"|[Dd]ecreto\s+\d+(?:\s+de\s+\d{4})?"
    r"|[Rr]esoluci[oó]n\s+\d+(?:\s+de\s+\d{4})?"
    r"|DUR\s+\d+"
    r")",
)

_FILLER_PREFIXES = _re.compile(
    r"^(?:hola|buenos\s+d[ií]as|buenas\s+tardes|buenas\s+noches|por\s+favor|gracias|oye|mira)\s*[,.]?\s*",
    flags=_re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Stream sink
# ---------------------------------------------------------------------------


class _ChatStreamSink:
    def __init__(
        self,
        handler: Any,
        *,
        request_context: dict[str, Any] | None = None,
        deps: dict[str, Any] | None = None,
    ) -> None:
        self.handler = handler
        self.assembler = StructuredMarkdownStreamAssembler()
        self.request_context = request_context or {}
        self.deps = deps or {}
        self._saw_delta = False
        self._saw_visible_block = False
        self._disconnected = False

    @property
    def rendered_markdown(self) -> str:
        return self.assembler.rendered_markdown

    @property
    def client_connected(self) -> bool:
        return not self._disconnected

    def _safe_write_event(self, event_name: str, payload: dict[str, Any]) -> bool:
        if self._disconnected:
            return False
        try:
            self.handler._write_sse_event(event_name, payload)
        except (BrokenPipeError, ConnectionResetError, OSError):
            self._disconnected = True
            return False
        return True

    def status(self, stage: str, message: str) -> None:
        self._safe_write_event(
            "status",
            {
                "stage": str(stage or "").strip() or "unknown",
                "message": str(message or "").strip() or "Procesando respuesta...",
            },
        )

    def citations_preview(self, candidates: list[dict[str, Any]] | None) -> None:
        """Emit an early preview of retrieved citations for the desktop panel.

        Fired by the orchestrator once retrieval has completed and the
        pipeline has cleared both the evidence-insufficient and confidence
        abstention guards, but before compose starts. The desktop frontend
        renders these as muted, non-clickable placeholders (Workstream 2
        Phase 7). Mobile is gated off at the UI-event layer.

        Gated by ``LIA_CITATIONS_PREVIEW`` (default ``on``). The payload is
        capped defensively at ``_CITATIONS_PREVIEW_MAX`` even if the caller
        passes more items.
        """

        if not _citations_preview_enabled():
            return
        items = list(candidates or ())[:_CITATIONS_PREVIEW_MAX]
        self._safe_write_event(
            "citations_preview",
            {
                "candidates": items,
                "max_items": _CITATIONS_PREVIEW_MAX,
            },
        )

    def _mark_chat_run_timing(self, method_name: str) -> None:
        coordinator = self.deps.get("chat_run_coordinator")
        chat_runs_path = self.deps.get("chat_runs_path")
        chat_run_id = str(self.request_context.get("chat_run_id") or "").strip()
        if coordinator is None or not chat_runs_path or not chat_run_id:
            return
        marker = getattr(coordinator, method_name, None)
        if callable(marker):
            marker(chat_run_id, base_dir=chat_runs_path)

    def on_llm_keepalive(self) -> None:
        """Send an SSE comment to keep the connection alive during LLM thinking."""
        if self._disconnected:
            return
        try:
            self.handler.wfile.write(b": keepalive\n\n")
            self.handler.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            self._disconnected = True

    def on_llm_delta(self, delta: str) -> None:
        if not self._saw_delta:
            self._saw_delta = True
            self._mark_chat_run_timing("mark_first_model_delta")
        for block in self.assembler.feed(delta):
            if not self._saw_visible_block and str(block.markdown or "").strip():
                self._saw_visible_block = True
                self._mark_chat_run_timing("mark_first_visible_answer")
            self._safe_write_event(
                "answer_block",
                {
                    "index": block.index,
                    "html": "",
                    "markdown": block.markdown,
                    "block_kind": block.block_kind,
                    "provisional": True,
                },
            )

    def finalize_draft(self, *, finish_reason: str | None = None) -> None:
        for block in self.assembler.finalize(finish_reason=finish_reason):
            if not self._saw_visible_block and str(block.markdown or "").strip():
                self._saw_visible_block = True
                self._mark_chat_run_timing("mark_first_visible_answer")
            self._safe_write_event(
                "answer_block",
                {
                    "index": block.index,
                    "html": "",
                    "markdown": block.markdown,
                    "block_kind": block.block_kind,
                    "provisional": True,
                },
            )


# ---------------------------------------------------------------------------
# Context / memory helpers
# ---------------------------------------------------------------------------


def build_clarification_scope_key(request_context: dict[str, Any]) -> str:
    tenant_id = str(request_context.get("tenant_id") or "public").strip() or "public"
    user_id = str(request_context.get("user_id") or "_").strip() or "_"
    company_id = str(request_context.get("company_id") or "_").strip() or "_"
    session_id = str(request_context.get("session_id") or "").strip()
    return f"{tenant_id}:{company_id}:{user_id}:{session_id}"


def build_memory_summary(session: Any) -> str:
    turns = list(getattr(session, "turns", []) or [])[-6:]
    parts: list[str] = []
    for turn in turns:
        role = str(getattr(turn, "role", "")).strip().lower()
        label = "U" if role == "user" else "A"
        text = " ".join(str(getattr(turn, "content", "")).split()).strip()
        if not text:
            continue
        if len(text) > 180:
            text = f"{text[:177]}..."
        parts.append(f"{label}: {text}")
    return " | ".join(parts)


def _extract_norm_anchors(text: str) -> list[str]:
    """Extract normative references (articles, laws, decrees) from text."""
    matches = _NORM_ANCHOR_RE.findall(str(text or ""))
    seen: set[str] = set()
    result: list[str] = []
    for m in matches:
        normalized = " ".join(m.split()).strip()
        key = normalized.lower()
        if key not in seen:
            seen.add(key)
            result.append(normalized)
    return result


def _compress_user_intent(text: str, max_chars: int = 100) -> str:
    """Compress user question to first sentence or max_chars."""
    cleaned = _FILLER_PREFIXES.sub("", str(text or "").strip()).strip()
    if not cleaned:
        return ""
    for sep in ("?", "."):
        idx = cleaned.find(sep)
        if 0 < idx < max_chars:
            return cleaned[: idx + 1].strip()
    if len(cleaned) > max_chars:
        return cleaned[:max_chars].rstrip() + "..."
    return cleaned


def build_semantic_memory(session: Any) -> str | None:
    state = build_conversation_state(session)
    return state.to_context_text() if state is not None else None


def _extract_conversation_state(request_context: dict[str, Any]) -> dict[str, Any] | None:
    cached = request_context.get("conversation_state")
    if isinstance(cached, dict):
        return cached
    session = request_context.get("conversation_session")
    if session is None:
        return None
    state = build_conversation_state(session)
    if state is None:
        return None
    payload = state.to_dict()
    request_context["conversation_state"] = payload
    return payload


def _extract_conversation_context(request_context: dict[str, Any]) -> str | None:
    """Extract conversation history for LLM context from the current session.

    Uses semantic memory extraction (entity + intent) instead of raw truncation.
    Falls back to the legacy memory_summary if semantic extraction yields nothing.
    Returns None for the first turn.
    """
    session = request_context.get("conversation_session")
    if session is None:
        return None
    semantic = build_semantic_memory(session)
    if semantic:
        return semantic
    summary = str(getattr(session, "memory_summary", "") or "").strip()
    return summary or None


def _default_session_payload(
    *,
    session_id: str,
    trace_id: str,
    run_id: str | None,
) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "turn_count": 0,
        "token_usage_total": None,
        "llm_token_usage_total": None,
        "last_trace_id": trace_id or None,
        "last_run_id": run_id or None,
        "updated_at": None,
        "pending": True,
    }


def _build_turn_metadata(response_payload: dict[str, Any]) -> dict[str, Any] | None:
    """Extract citation/topic metadata from the pipeline response for per-turn persistence."""
    citations = response_payload.get("citations")
    support = response_payload.get("support_citations")
    if not citations and not support:
        return None
    confidence = response_payload.get("confidence")
    return {
        "citations": [dict(c) for c in (citations or []) if isinstance(c, dict)],
        "support_citations": [dict(c) for c in (support or []) if isinstance(c, dict)],
        "effective_topic": response_payload.get("effective_topic"),
        "secondary_topics": list(response_payload.get("secondary_topics") or []),
        "confidence_score": confidence.get("score") if isinstance(confidence, dict) else None,
        "confidence_mode": confidence.get("mode") if isinstance(confidence, dict) else None,
        "coverage_notice": response_payload.get("coverage_notice"),
    }
