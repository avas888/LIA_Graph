"""Validation and parsing helpers extracted from ui_server.py."""

from __future__ import annotations

import os
from dataclasses import fields
from typing import Any

from .contracts import (
    ALLOWED_CLIENT_MODES,
    ALLOWED_FOLLOWUP_ACTIONS,
    ALLOWED_KNOWLEDGE_LAYER_FILTERS,
    ALLOWED_PAIN_HINTS,
    ALLOWED_RETRIEVAL_PROFILES,
    ALLOWED_RESPONSE_GOALS,
    AccessContext,
    CompanyContext,
    ConversationTurn,
)
from .scope_guardrails import normalize_pais
from .topic_guardrails import get_supported_topics, normalize_topic_key

SUPPORTED_TOPICS = get_supported_topics()

_DEFAULT_CHAT_LIMITS = {
    "message_min_chars": 1,
    "top_k_min": 1,
    "top_k_max": 50,
    "conversation_max_turns": 40,
    "conversation_turn_max_chars": 6000,
    "trace_id_max_chars": 256,
}


def _public_chat_max_input_chars() -> int:
    raw = str(os.getenv("LIA_PUBLIC_MAX_INPUT_CHARS", "3000")).strip() or "3000"
    try:
        return int(raw)
    except ValueError:
        return 3000


def resolve_public_chat_limits() -> dict[str, int]:
    """Return the chat-validation limits for a public visitor request.

    Public visitors get a stricter `conversation_turn_max_chars` (default
    3000 vs 6000) so attackers cannot inflate LLM input cost. All other
    limits stay at the authenticated default.
    """
    return {
        **_DEFAULT_CHAT_LIMITS,
        "conversation_turn_max_chars": _public_chat_max_input_chars(),
    }


_ALLOWED_LAYER_CASCADE_MODE = {"auto", "practica_first", "all_layers", "normativa_only", "practica_first_deferred_normative"}
_ALLOWED_RESPONSE_SECTION_MODE = {"auto", "custom"}
_ALLOWED_ENABLE_EMBEDDINGS = {"off", "on"}


def _validate_chat_payload(
    payload: dict[str, Any],
    *,
    is_public: bool = False,
) -> tuple[bool, str | None]:
    limits = resolve_public_chat_limits() if is_public else None
    return _validate_chat_payload_with_limits(payload, limits=limits)


def _reject_unknown_keys(
    payload: dict[str, Any],
    allowed_keys: set[str],
    *,
    context_label: str,
) -> str | None:
    unknown_payload_keys = sorted(set(payload.keys()) - allowed_keys)
    if unknown_payload_keys:
        return f"Campos no soportados en {context_label}: {', '.join(unknown_payload_keys)}."
    return None


def _normalize_csv_like_tuple(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        return tuple(item.strip() for item in value.split(",") if item.strip())
    if isinstance(value, (list, tuple, set)):
        return tuple(str(item).strip() for item in value if str(item).strip())
    return ()


def _validate_optional_enum_value(
    value: Any,
    *,
    field_name: str,
    allowed_values: set[str],
    message: str | None = None,
) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or value.strip().lower() not in allowed_values:
        if message:
            return message
        allowed = ", ".join(sorted(allowed_values))
        return f"`{field_name}` debe ser uno de: {allowed}."
    return None


def _validate_chat_top_level_fields(
    payload: dict[str, Any],
    *,
    resolved_limits: dict[str, int],
) -> tuple[str | None, str | None]:
    message = payload.get("message")
    if not isinstance(message, str) or not message.strip():
        return "`message` es obligatorio y debe ser texto no vacio.", None
    if len(message.strip()) < resolved_limits["message_min_chars"]:
        return (
            f"`message` debe tener minimo {resolved_limits['message_min_chars']} caracteres.",
            None,
        )

    top_k = payload.get("top_k", 5)
    if (
        not isinstance(top_k, int)
        or top_k < resolved_limits["top_k_min"]
        or top_k > resolved_limits["top_k_max"]
    ):
        return (
            "`top_k` debe ser entero entre "
            f"{resolved_limits['top_k_min']} y {resolved_limits['top_k_max']}.",
            None,
        )

    operation_date = payload.get("operation_date")
    if operation_date is not None and (not isinstance(operation_date, str) or len(operation_date.strip()) < 8):
        return "`operation_date` debe ser string en formato YYYY-MM-DD si se envia.", None

    period_month = payload.get("period_month")
    if period_month is not None and (not isinstance(period_month, int) or period_month < 1 or period_month > 12):
        return "`period_month` debe ser entero entre 1 y 12.", None

    fiscal_year = payload.get("fiscal_year")
    if fiscal_year is not None and (not isinstance(fiscal_year, int) or fiscal_year < 2000 or fiscal_year > 2099):
        return "`fiscal_year` debe ser entero en rango 2000..2099.", None

    topic = payload.get("topic")
    if topic is not None and (not isinstance(topic, str) or normalize_topic_key(topic) not in SUPPORTED_TOPICS):
        allowed = ", ".join(sorted(SUPPORTED_TOPICS))
        return f"`topic` debe ser uno de: {allowed} cuando se envia.", None

    normalized_pais = normalize_pais(payload.get("pais"))
    if normalized_pais is None:
        return "`pais` es obligatorio y debe ser uno de: colombia, peru, mexico.", None
    return None, normalized_pais


def _validate_access_context_payload(
    access_payload: Any,
    *,
    normalized_pais: str,
) -> tuple[str | None, dict[str, Any] | None, str | None]:
    if not isinstance(access_payload, dict):
        return "`access_context` es obligatorio y debe ser objeto JSON.", None, None

    allowed_access_keys = {
        "tenant_id",
        "accountant_id",
        "accountant_name",
        "allowed_company_ids",
        "active_company_id",
        "pais",
        "claims_source",
    }
    unknown_access_keys = sorted(set(access_payload.keys()) - allowed_access_keys)
    if unknown_access_keys:
        return f"Campos no soportados en access_context: {', '.join(unknown_access_keys)}.", None, None

    required_access_fields = ("tenant_id", "accountant_id", "accountant_name", "active_company_id")
    for field_name in required_access_fields:
        value = access_payload.get(field_name)
        if not isinstance(value, str) or not value.strip():
            return f"`access_context.{field_name}` es obligatorio y debe ser texto no vacio.", None, None

    allowed_company_ids = access_payload.get("allowed_company_ids")
    if not isinstance(allowed_company_ids, list) or not allowed_company_ids:
        return "`access_context.allowed_company_ids` es obligatorio y debe ser lista no vacia.", None, None
    allowed_set = {str(item).strip() for item in allowed_company_ids if str(item).strip()}
    if not allowed_set:
        return "`access_context.allowed_company_ids` debe incluir company_ids validos.", None, None

    active_company_id = str(access_payload.get("active_company_id", "")).strip()
    if active_company_id not in allowed_set:
        return "`access_context.active_company_id` debe pertenecer a `allowed_company_ids`.", None, None

    access_pais = normalize_pais(access_payload.get("pais"))
    if access_pais is None:
        return "`access_context.pais` es obligatorio y debe ser valido.", None, None
    if access_pais != normalized_pais:
        return "`access_context.pais` debe coincidir con `pais`.", None, None

    return None, access_payload, active_company_id


def _validate_company_context_payload(
    company_context_payload: Any,
    *,
    access_payload: dict[str, Any],
    active_company_id: str,
    normalized_pais: str,
) -> str | None:
    if company_context_payload is None:
        return None
    if not isinstance(company_context_payload, dict):
        return "`company_context` debe ser objeto JSON si se envia."

    allowed_company_keys = {f.name for f in fields(CompanyContext)}
    unknown_company_keys = sorted(set(company_context_payload.keys()) - allowed_company_keys)
    if unknown_company_keys:
        return f"Campos no soportados en company_context: {', '.join(unknown_company_keys)}."

    company_name = str(company_context_payload.get("company_name", "")).strip()
    period = str(company_context_payload.get("period", "")).strip()
    tenant_id = str(company_context_payload.get("tenant_id", "")).strip()
    company_id = str(company_context_payload.get("company_id", "")).strip()
    company_pais = normalize_pais(company_context_payload.get("pais"))
    if not company_name or not period or not tenant_id or not company_id or company_pais is None:
        return (
            "`company_context` debe incluir `company_name`, `period`, `tenant_id`, `company_id` y `pais` validos."
        )
    if tenant_id != str(access_payload.get("tenant_id", "")).strip():
        return "`company_context.tenant_id` debe coincidir con `access_context.tenant_id`."
    if company_id != active_company_id:
        return "`company_context.company_id` debe coincidir con `access_context.active_company_id`."
    if company_pais != normalized_pais:
        return "`company_context.pais` debe coincidir con `pais`."
    return None


def _validate_chat_optional_fields(
    payload: dict[str, Any],
    *,
    resolved_limits: dict[str, int],
) -> str | None:
    llm_provider = payload.get("llm_provider")
    if llm_provider is not None and not isinstance(llm_provider, str):
        return "`llm_provider` debe ser string si se envia."

    enum_validations = (
        (
            "strict_scope",
            {"renta_only", "default"},
            "`strict_scope` debe ser `renta_only` o `default`.",
        ),
        (
            "primary_scope_mode",
            {"global_overlay", "strict_topic"},
            "`primary_scope_mode` debe ser `global_overlay` o `strict_topic`.",
        ),
        (
            "interaction_mode",
            {"auto", "narrowing", "direct"},
            "`interaction_mode` debe ser `auto`, `narrowing` o `direct`.",
        ),
        (
            "reasoning_profile",
            {"balanced", "deep"},
            "`reasoning_profile` debe ser `balanced` o `deep`.",
        ),
        (
            "retrieval_profile",
            {"baseline_keyword", "hybrid_rerank", "hybrid_semantic", "advanced_corrective"},
            (
                "`retrieval_profile` debe ser `baseline_keyword`, `hybrid_rerank`, "
                "`hybrid_semantic` o `advanced_corrective`."
            ),
        ),
        (
            "response_depth",
            {"auto", "concise", "deep"},
            "`response_depth` debe ser `auto`, `concise` o `deep`.",
        ),
        (
            "first_response_mode",
            {"fast_action", "balanced_action"},
            "`first_response_mode` debe ser `fast_action` o `balanced_action`.",
        ),
        (
            "intent_hint",
            {"procedimiento", "calculo", "ambas"},
            "`intent_hint` debe ser `procedimiento`, `calculo` o `ambas`.",
        ),
        (
            "followup_action",
            ALLOWED_FOLLOWUP_ACTIONS,
            f"`followup_action` debe ser uno de: {', '.join(sorted(ALLOWED_FOLLOWUP_ACTIONS))}.",
        ),
        (
            "pain_hint",
            ALLOWED_PAIN_HINTS,
            f"`pain_hint` debe ser uno de: {', '.join(sorted(ALLOWED_PAIN_HINTS))}.",
        ),
        (
            "response_goal",
            ALLOWED_RESPONSE_GOALS,
            f"`response_goal` debe ser uno de: {', '.join(sorted(ALLOWED_RESPONSE_GOALS))}.",
        ),
        (
            "client_mode",
            ALLOWED_CLIENT_MODES,
            f"`client_mode` debe ser uno de: {', '.join(sorted(ALLOWED_CLIENT_MODES))}.",
        ),
        (
            "layer_cascade_mode",
            _ALLOWED_LAYER_CASCADE_MODE,
            f"`layer_cascade_mode` debe ser uno de: {', '.join(sorted(_ALLOWED_LAYER_CASCADE_MODE))}.",
        ),
        (
            "response_section_mode",
            _ALLOWED_RESPONSE_SECTION_MODE,
            f"`response_section_mode` debe ser uno de: {', '.join(sorted(_ALLOWED_RESPONSE_SECTION_MODE))}.",
        ),
        (
            "enable_embeddings",
            _ALLOWED_ENABLE_EMBEDDINGS,
            f"`enable_embeddings` debe ser uno de: {', '.join(sorted(_ALLOWED_ENABLE_EMBEDDINGS))}.",
        ),
        (
            "knowledge_layer_filter",
            ALLOWED_KNOWLEDGE_LAYER_FILTERS,
            (
                "`knowledge_layer_filter` debe ser uno de: "
                f"{', '.join(sorted(v for v in ALLOWED_KNOWLEDGE_LAYER_FILTERS if v is not None))}."
            ),
        ),
    )
    for field_name, allowed_values, message in enum_validations:
        error = _validate_optional_enum_value(
            payload.get(field_name),
            field_name=field_name,
            allowed_values=allowed_values,
            message=message,
        )
        if error:
            return error

    debug_flag = payload.get("debug")
    if debug_flag is not None and not isinstance(debug_flag, bool):
        return "`debug` debe ser booleano si se envia."

    trace_id = payload.get("trace_id")
    if trace_id is not None:
        if not isinstance(trace_id, str) or not trace_id.strip():
            return "`trace_id` debe ser string no vacio si se envia."
        if len(trace_id.strip()) > resolved_limits["trace_id_max_chars"]:
            return f"`trace_id` no puede superar {resolved_limits['trace_id_max_chars']} caracteres."

    conversation = payload.get("conversation")
    if conversation is not None:
        if not isinstance(conversation, list):
            return "`conversation` debe ser una lista de mensajes si se envia."
        if len(conversation) > resolved_limits["conversation_max_turns"]:
            return (
                "`conversation` soporta maximo "
                f"{resolved_limits['conversation_max_turns']} mensajes."
            )
        for idx, turn in enumerate(conversation):
            if not isinstance(turn, dict):
                return f"`conversation[{idx}]` debe ser objeto JSON."
            role = str(turn.get("role", "")).strip().lower()
            content = turn.get("content")
            if role not in {"user", "assistant"}:
                return f"`conversation[{idx}].role` debe ser `user` o `assistant`."
            if not isinstance(content, str) or not content.strip():
                return f"`conversation[{idx}].content` debe ser texto no vacio."
            if len(content.strip()) > resolved_limits["conversation_turn_max_chars"]:
                return (
                    f"`conversation[{idx}].content` excede "
                    f"{resolved_limits['conversation_turn_max_chars']} caracteres."
                )
    return None


def _validate_pipeline_c_payload(
    payload: dict[str, Any],
    *,
    is_public: bool = False,
) -> tuple[bool, str | None]:
    allowed_payload_keys = {
        "message",
        "trace_id",
        "client_turn_id",
        "chat_run_id",
        "session_id",
        "pais",
        "topic",
        "operation_date",
        "company_context",
        "primary_scope_mode",
        "response_route",
        "retrieval_profile",
        "response_depth",
        "first_response_mode",
        "debug",
    }
    error = _reject_unknown_keys(payload, allowed_payload_keys, context_label="request")
    if error:
        return False, error

    message = payload.get("message")
    if not isinstance(message, str) or not message.strip():
        return False, "`message` es obligatorio y debe ser texto no vacio."

    if is_public:
        public_max = _public_chat_max_input_chars()
        if len(message) > public_max:
            return False, f"`message` excede {public_max} caracteres en modo público."

    normalized_pais = normalize_pais(payload.get("pais", "colombia"))
    if normalized_pais is None:
        return False, "`pais` debe ser uno de: colombia, peru, mexico."

    topic = payload.get("topic")
    normalized_topic = normalize_topic_key(topic) if topic is not None else None
    if topic is not None and normalized_topic not in SUPPORTED_TOPICS:
        allowed = ", ".join(sorted(SUPPORTED_TOPICS))
        return False, f"`topic` debe ser uno de: {allowed} cuando se envia."

    operation_date = payload.get("operation_date")
    if operation_date is not None:
        if not isinstance(operation_date, str) or len(operation_date.strip()) < 8:
            return False, "`operation_date` debe ser string en formato YYYY-MM-DD si se envia."

    primary_scope_mode = str(payload.get("primary_scope_mode", "global_overlay")).strip().lower() or "global_overlay"
    if primary_scope_mode not in {"global_overlay", "strict_topic"}:
        return False, "`primary_scope_mode` debe ser `global_overlay` o `strict_topic`."

    response_route = str(payload.get("response_route", "decision")).strip().lower() or "decision"
    if response_route not in {"decision", "theoretical_normative"}:
        return False, "`response_route` debe ser `decision` o `theoretical_normative`."

    retrieval_profile = str(payload.get("retrieval_profile", "hybrid_rerank")).strip().lower() or "hybrid_rerank"
    if retrieval_profile not in {"baseline_keyword", "hybrid_rerank", "hybrid_semantic", "advanced_corrective"}:
        return (
            False,
            "`retrieval_profile` debe ser `baseline_keyword`, `hybrid_rerank`, `hybrid_semantic` o `advanced_corrective`.",
        )

    response_depth = str(payload.get("response_depth", "auto")).strip().lower() or "auto"
    if response_depth not in {"auto", "concise", "deep"}:
        return False, "`response_depth` debe ser `auto`, `concise` o `deep`."

    first_response_mode = str(payload.get("first_response_mode", "fast_action")).strip().lower() or "fast_action"
    if first_response_mode not in {"fast_action", "balanced_action"}:
        return False, "`first_response_mode` debe ser `fast_action` o `balanced_action`."

    debug = payload.get("debug")
    if debug is not None and not isinstance(debug, bool):
        return False, "`debug` debe ser booleano si se envia."

    trace_id = payload.get("trace_id")
    if trace_id is not None and (not isinstance(trace_id, str) or not trace_id.strip()):
        return False, "`trace_id` debe ser string no vacio si se envia."

    client_turn_id = payload.get("client_turn_id")
    if client_turn_id is not None and (not isinstance(client_turn_id, str) or not client_turn_id.strip()):
        return False, "`client_turn_id` debe ser string no vacio si se envia."

    chat_run_id = payload.get("chat_run_id")
    if chat_run_id is not None and (not isinstance(chat_run_id, str) or not chat_run_id.strip()):
        return False, "`chat_run_id` debe ser string no vacio si se envia."

    session_id = payload.get("session_id")
    if session_id is not None and (not isinstance(session_id, str) or not session_id.strip()):
        return False, "`session_id` debe ser string no vacio si se envia."

    company_context = payload.get("company_context")
    if company_context is not None and not isinstance(company_context, dict):
        return False, "`company_context` debe ser objeto JSON si se envia."

    return True, None


def _coerce_limit_int(
    limits: dict[str, Any],
    key: str,
    *,
    default: int,
    min_allowed: int = 1,
) -> int:
    value = limits.get(key, default)
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return max(min_allowed, value)
    if isinstance(value, float) and float(value).is_integer():
        return max(min_allowed, int(value))
    return default


def _coerce_limit_float(
    limits: dict[str, Any],
    key: str,
    *,
    default: float,
    min_allowed: float = 0.1,
) -> float:
    value = limits.get(key, default)
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return max(min_allowed, float(value))
    return default


def _resolve_chat_limits(limits: dict[str, Any] | None) -> dict[str, int]:
    source = limits if isinstance(limits, dict) else {}
    resolved = {
        key: _coerce_limit_int(source, key, default=value)
        for key, value in _DEFAULT_CHAT_LIMITS.items()
    }
    top_k_min = resolved["top_k_min"]
    top_k_max = resolved["top_k_max"]
    if top_k_min > top_k_max:
        resolved["top_k_min"] = min(top_k_min, top_k_max)
        resolved["top_k_max"] = max(top_k_min, top_k_max)
    return resolved


def _validate_chat_payload_with_limits(
    payload: dict[str, Any],
    *,
    limits: dict[str, Any] | None,
) -> tuple[bool, str | None]:
    allowed_payload_keys = {
        "message",
        "top_k",
        "operation_date",
        "period_month",
        "fiscal_year",
        "topic",
        "pais",
        "access_context",
        "company_context",
        "llm_provider",
        "strict_scope",
        "interaction_mode",
        "reasoning_profile",
        "retrieval_profile",
        "response_depth",
        "first_response_mode",
        "intent_hint",
        "followup_action",
        "pain_hint",
        "response_goal",
        "client_mode",
        "layer_cascade_mode",
        "response_section_mode",
        "primary_scope_mode",
        "enable_embeddings",
        "knowledge_layer_filter",
        "debug",
        "trace_id",
        "conversation",
        "session_id",
    }
    error = _reject_unknown_keys(payload, allowed_payload_keys, context_label="request")
    if error:
        return False, error

    resolved_limits = _resolve_chat_limits(limits)
    error, normalized_pais = _validate_chat_top_level_fields(payload, resolved_limits=resolved_limits)
    if error or normalized_pais is None:
        return False, error

    access_error, access_payload, active_company_id = _validate_access_context_payload(
        payload.get("access_context"),
        normalized_pais=normalized_pais,
    )
    if access_error or access_payload is None or active_company_id is None:
        return False, access_error

    company_context_error = _validate_company_context_payload(
        payload.get("company_context"),
        access_payload=access_payload,
        active_company_id=active_company_id,
        normalized_pais=normalized_pais,
    )
    if company_context_error:
        return False, company_context_error

    optional_fields_error = _validate_chat_optional_fields(payload, resolved_limits=resolved_limits)
    if optional_fields_error:
        return False, optional_fields_error

    return True, None


def _parse_access_context(payload: dict[str, Any], normalized_pais: str) -> AccessContext:
    access_payload = dict(payload.get("access_context", {}))
    access_payload["pais"] = normalize_pais(access_payload.get("pais")) or normalized_pais
    return AccessContext.from_dict(access_payload)


def _parse_company_context(payload: dict[str, Any], normalized_pais: str) -> CompanyContext | None:
    raw = payload.get("company_context")
    if raw is None:
        return None

    allowed = {f.name for f in fields(CompanyContext)}
    filtered = {k: v for k, v in raw.items() if k in allowed}
    filtered["pais"] = normalize_pais(raw.get("pais")) or normalized_pais
    return CompanyContext(**filtered)


def _parse_conversation(payload: dict[str, Any]) -> tuple[ConversationTurn, ...]:
    raw = payload.get("conversation")
    if not isinstance(raw, list):
        return ()
    turns: list[ConversationTurn] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        turns.append(ConversationTurn.from_dict(item))
    return tuple(turns)
