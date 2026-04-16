from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_TERMS_POLICY_PATH = Path("config/terms_of_use.json")
DEFAULT_TERMS_STATE_PATH = Path("artifacts/terms/accepted_terms_state.json")
DEFAULT_TERMS_DOC_PATH = Path("docs/terms_of_use.md")
_DEFAULT_TERMS_STATE_KEY = "global"


class TermsAcceptanceRequiredError(RuntimeError):
    def __init__(self, status: dict[str, Any]) -> None:
        super().__init__("terms_acceptance_required")
        self.status = status


def _to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def load_terms_policy(path: Path = DEFAULT_TERMS_POLICY_PATH) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "enabled": False,
        "operator": "Loggro",
        "version": "0.0.0",
        "enforcement_revision": 1,
        "terms_url": "/terms-of-use",
        "terms_doc_path": str(DEFAULT_TERMS_DOC_PATH),
        "state_file": str(DEFAULT_TERMS_STATE_PATH),
    }
    if not path.exists():
        return defaults

    payload = json.loads(path.read_text(encoding="utf-8"))
    return {**defaults, **payload}


def _use_supabase(state_path: Path) -> bool:
    from .supabase_client import is_supabase_enabled, matches_default_storage_path

    if not matches_default_storage_path(state_path, DEFAULT_TERMS_STATE_PATH):
        return False
    return is_supabase_enabled()


def resolve_terms_doc_path(policy: dict[str, Any]) -> Path:
    return Path(str(policy.get("terms_doc_path", DEFAULT_TERMS_DOC_PATH)))


def resolve_terms_state_path(policy: dict[str, Any], state_path: Path | None = None) -> Path:
    if state_path is not None:
        return state_path
    return Path(str(policy.get("state_file", DEFAULT_TERMS_STATE_PATH)))


def _normalize_terms_state_row(row: dict[str, Any]) -> dict[str, Any]:
    accepted_at = row.get("accepted_at_utc")
    if hasattr(accepted_at, "isoformat"):
        accepted_at = accepted_at.isoformat()
    return {
        "accepted_version": str(row.get("accepted_version", "") or ""),
        "accepted_enforcement_revision": _to_int(row.get("accepted_enforcement_revision"), 0),
        "accepted_at_utc": str(accepted_at or "") or None,
        "accepted_by": str(row.get("accepted_by", "") or "") or None,
        "operator": str(row.get("operator", "") or "") or None,
    }


def _sb_load_terms_state() -> dict[str, Any] | None:
    from .supabase_client import get_supabase_client

    client = get_supabase_client()
    result = (
        client.table("terms_acceptance_state")
        .select("*")
        .eq("state_key", _DEFAULT_TERMS_STATE_KEY)
        .limit(1)
        .execute()
    )
    if not result.data:
        return None
    return _normalize_terms_state_row(dict(result.data[0]))


def _sb_save_terms_state(state: dict[str, Any]) -> None:
    from .supabase_client import get_supabase_client

    client = get_supabase_client()
    accepted_at = str(state.get("accepted_at_utc", "") or "").strip() or None
    client.table("terms_acceptance_state").upsert(
        {
            "state_key": _DEFAULT_TERMS_STATE_KEY,
            "accepted_version": str(state.get("accepted_version", "") or ""),
            "accepted_enforcement_revision": _to_int(state.get("accepted_enforcement_revision"), 0),
            "accepted_at_utc": accepted_at,
            "accepted_by": str(state.get("accepted_by", "") or ""),
            "operator": str(state.get("operator", "") or ""),
        },
        on_conflict="state_key",
    ).execute()


def load_terms_state(state_path: Path) -> dict[str, Any] | None:
    if _use_supabase(state_path):
        return _sb_load_terms_state()
    if not state_path.exists():
        return None

    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def evaluate_terms_status(policy: dict[str, Any], state: dict[str, Any] | None) -> dict[str, Any]:
    enabled = bool(policy.get("enabled", False))
    version = str(policy.get("version", "0.0.0"))
    revision = _to_int(policy.get("enforcement_revision"), 1)

    reason = "accepted"
    requires_acceptance = False

    if enabled:
        if not state:
            reason = "first_use"
            requires_acceptance = True
        else:
            accepted_version = str(state.get("accepted_version", ""))
            accepted_revision = _to_int(state.get("accepted_enforcement_revision"), 0)
            if accepted_version != version:
                reason = "new_terms_version"
                requires_acceptance = True
            elif accepted_revision != revision:
                reason = "operator_refresh_required"
                requires_acceptance = True
    else:
        reason = "terms_disabled"

    return {
        "enabled": enabled,
        "operator": str(policy.get("operator", "Loggro")),
        "version": version,
        "enforcement_revision": revision,
        "terms_url": str(policy.get("terms_url", "/terms-of-use")),
        "requires_acceptance": requires_acceptance,
        "accepted": not requires_acceptance,
        "reason": reason,
        "accepted_version": state.get("accepted_version") if state else None,
        "accepted_enforcement_revision": state.get("accepted_enforcement_revision") if state else None,
        "accepted_at_utc": state.get("accepted_at_utc") if state else None,
        "accepted_by": state.get("accepted_by") if state else None,
    }


def get_terms_status(
    policy_path: Path = DEFAULT_TERMS_POLICY_PATH,
    state_path: Path | None = None,
) -> dict[str, Any]:
    policy = load_terms_policy(policy_path)
    resolved_state_path = resolve_terms_state_path(policy, state_path=state_path)
    state = load_terms_state(resolved_state_path)
    return evaluate_terms_status(policy, state)


def read_terms_text(policy_path: Path = DEFAULT_TERMS_POLICY_PATH) -> str:
    policy = load_terms_policy(policy_path)
    terms_doc_path = resolve_terms_doc_path(policy)
    if not terms_doc_path.exists():
        return ""
    return terms_doc_path.read_text(encoding="utf-8")


def accept_terms(
    accepted_by: str,
    policy_path: Path = DEFAULT_TERMS_POLICY_PATH,
    state_path: Path | None = None,
) -> dict[str, Any]:
    policy = load_terms_policy(policy_path)
    resolved_state_path = resolve_terms_state_path(policy, state_path=state_path)

    accepted_payload = {
        "accepted_version": str(policy.get("version", "0.0.0")),
        "accepted_enforcement_revision": _to_int(policy.get("enforcement_revision"), 1),
        "accepted_at_utc": datetime.now(timezone.utc).isoformat(),
        "accepted_by": accepted_by,
        "operator": str(policy.get("operator", "Loggro")),
    }

    if _use_supabase(resolved_state_path):
        _sb_save_terms_state(accepted_payload)
    else:
        resolved_state_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_state_path.write_text(
            json.dumps(accepted_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    return evaluate_terms_status(policy, accepted_payload)


def assert_terms_accepted(
    policy_path: Path = DEFAULT_TERMS_POLICY_PATH,
    state_path: Path | None = None,
) -> dict[str, Any]:
    status = get_terms_status(policy_path=policy_path, state_path=state_path)
    if status["requires_acceptance"]:
        raise TermsAcceptanceRequiredError(status)
    return status
