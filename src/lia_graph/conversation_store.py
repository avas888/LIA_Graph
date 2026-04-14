"""Conversation session persistence.

Supabase is the authoritative backend for chat session state in LIA_Graph.
Filesystem remains only for explicit test/dev path overrides.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


DEFAULT_CONVERSATIONS_DIR = Path("artifacts/conversations")
MAX_TURNS_PER_SESSION = 60
MAX_RECENT_SESSIONS = 20

_log = logging.getLogger(__name__)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _use_supabase(base_dir: Path) -> bool:
    from lia_contador.supabase_client import is_supabase_enabled, matches_default_storage_path

    if not matches_default_storage_path(base_dir, DEFAULT_CONVERSATIONS_DIR):
        return False
    return is_supabase_enabled()


@dataclass
class ConversationTurn:
    role: str
    content: str
    layer_contributions: dict[str, int] | None = None
    trace_id: str | None = None
    timestamp: str | None = None
    turn_metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "layer_contributions": self.layer_contributions,
            "trace_id": self.trace_id,
            "timestamp": self.timestamp,
            "turn_metadata": self.turn_metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConversationTurn:
        return cls(
            role=str(data.get("role", "")).strip(),
            content=str(data.get("content", "")).strip(),
            layer_contributions=data.get("layer_contributions"),
            trace_id=data.get("trace_id"),
            timestamp=data.get("timestamp"),
            turn_metadata=data.get("turn_metadata"),
        )


@dataclass
class ConversationSession:
    session_id: str
    tenant_id: str
    accountant_id: str
    topic: str | None
    pais: str
    user_id: str = ""
    company_id: str = ""
    integration_id: str = ""
    host_session_id: str = ""
    channel: str = "chat"
    status: str = "active"
    memory_summary: str = ""
    turns: list[ConversationTurn] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self) -> None:
        now = _utc_now_iso()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "tenant_id": self.tenant_id,
            "accountant_id": self.accountant_id,
            "topic": self.topic,
            "pais": self.pais,
            "user_id": self.user_id,
            "company_id": self.company_id,
            "integration_id": self.integration_id,
            "host_session_id": self.host_session_id,
            "channel": self.channel,
            "status": self.status,
            "memory_summary": self.memory_summary,
            "turns": [t.to_dict() for t in self.turns],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConversationSession:
        turns = [ConversationTurn.from_dict(t) for t in data.get("turns", [])]
        return cls(
            session_id=str(data.get("session_id", "")),
            tenant_id=str(data.get("tenant_id", "")),
            accountant_id=str(data.get("accountant_id", "")),
            topic=data.get("topic"),
            pais=str(data.get("pais", "")),
            user_id=str(data.get("user_id", "")),
            company_id=str(data.get("company_id", "")),
            integration_id=str(data.get("integration_id", "")),
            host_session_id=str(data.get("host_session_id", "")),
            channel=str(data.get("channel", "chat") or "chat"),
            status=str(data.get("status", "active") or "active"),
            memory_summary=str(data.get("memory_summary", "")),
            turns=turns,
            created_at=str(data.get("created_at", "")),
            updated_at=str(data.get("updated_at", "")),
        )


# ---------------------------------------------------------------------------
# Filesystem implementation
# ---------------------------------------------------------------------------

def _session_path(base_dir: Path, tenant_id: str, session_id: str) -> Path:
    safe_tenant = tenant_id.replace("/", "_").replace("..", "_")[:64]
    safe_session = session_id.replace("/", "_").replace("..", "_")[:64]
    return base_dir / safe_tenant / f"{safe_session}.json"


def _tenant_dir(base_dir: Path, tenant_id: str) -> Path:
    safe_tenant = tenant_id.replace("/", "_").replace("..", "_")[:64]
    return base_dir / safe_tenant


def _fs_save_session(session: ConversationSession, *, base_dir: Path) -> None:
    path = _session_path(base_dir, session.tenant_id, session.session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(session.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")


def _fs_load_session(
    *,
    tenant_id: str,
    session_id: str,
    base_dir: Path,
    user_id: str | None = None,
    company_id: str | None = None,
) -> ConversationSession | None:
    path = _session_path(base_dir, tenant_id, session_id)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    session = ConversationSession.from_dict(data)
    if user_id and session.user_id and session.user_id != user_id:
        return None
    if company_id and session.company_id and session.company_id != company_id:
        return None
    return session


def _fs_list_sessions(
    *,
    tenant_id: str,
    base_dir: Path,
    limit: int,
    user_id: str | None = None,
    company_id: str | None = None,
) -> list[dict[str, Any]]:
    safe_tenant = tenant_id.replace("/", "_").replace("..", "_")[:64]
    tenant_dir = base_dir / safe_tenant
    if not tenant_dir.is_dir():
        return []
    sessions: list[dict[str, Any]] = []
    for path in sorted(tenant_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if user_id and str(data.get("user_id", "")).strip() and str(data.get("user_id", "")).strip() != user_id:
            continue
        if company_id and str(data.get("company_id", "")).strip() and str(data.get("company_id", "")).strip() != company_id:
            continue
        turns = data.get("turns", [])
        first_question = ""
        for t in turns:
            if t.get("role") == "user" and t.get("content"):
                first_question = str(t["content"])[:120]
                break
        sessions.append({
            "session_id": data.get("session_id", ""),
            "topic": data.get("topic"),
            "pais": data.get("pais", ""),
            "created_at": data.get("created_at", ""),
            "updated_at": data.get("updated_at", ""),
            "turn_count": len(turns),
            "first_question": first_question,
            "user_id": data.get("user_id", ""),
            "company_id": data.get("company_id", ""),
            "integration_id": data.get("integration_id", ""),
            "channel": data.get("channel", "chat"),
            "status": data.get("status", "active"),
            "memory_summary": data.get("memory_summary", ""),
        })
        if len(sessions) >= limit:
            break
    return sessions


# ---------------------------------------------------------------------------
# Supabase implementation
# ---------------------------------------------------------------------------

def _sb_create_session(session: ConversationSession) -> None:
    from lia_contador.supabase_client import get_supabase_client
    client = get_supabase_client()
    client.table("conversations").insert({
        "session_id": session.session_id,
        "tenant_id": session.tenant_id,
        "accountant_id": session.accountant_id,
        "topic": session.topic,
        "pais": session.pais,
        "user_id": session.user_id or "",
        "company_id": session.company_id or "",
        "integration_id": session.integration_id or "",
        "host_session_id": session.host_session_id or "",
        "channel": session.channel,
        "status": session.status,
        "memory_summary": session.memory_summary,
    }).execute()


def _sb_upsert_session_shell(session: ConversationSession) -> None:
    from lia_contador.supabase_client import get_supabase_client

    client = get_supabase_client()
    client.table("conversations").upsert(
        {
            "session_id": session.session_id,
            "tenant_id": session.tenant_id,
            "accountant_id": session.accountant_id,
            "topic": session.topic,
            "pais": session.pais,
            "user_id": session.user_id or "",
            "company_id": session.company_id or "",
            "integration_id": session.integration_id or "",
            "host_session_id": session.host_session_id or "",
            "channel": session.channel,
            "status": session.status,
            "memory_summary": session.memory_summary,
        },
        on_conflict="session_id",
    ).execute()


def _sb_save_turn(conversation_id: str, turn: ConversationTurn) -> None:
    from lia_contador.supabase_client import get_supabase_client
    client = get_supabase_client()
    client.table("conversation_turns").insert({
        "conversation_id": conversation_id,
        "role": turn.role,
        "content": turn.content,
        "layer_contributions": turn.layer_contributions,
        "trace_id": turn.trace_id,
        "turn_metadata": turn.turn_metadata,
    }).execute()


def _sb_load_session(
    *,
    tenant_id: str,
    session_id: str,
    user_id: str | None = None,
    company_id: str | None = None,
) -> ConversationSession | None:
    from lia_contador.supabase_client import get_supabase_client
    client = get_supabase_client()
    query = client.table("conversations").select("*").eq("session_id", session_id).eq("tenant_id", tenant_id)
    if user_id:
        query = query.eq("user_id", user_id)
    if company_id:
        query = query.eq("company_id", company_id)
    res = query.execute()
    if not res.data:
        return None
    row = res.data[0]
    conv_id = row["id"]
    turns_res = client.table("conversation_turns").select("*").eq(
        "conversation_id", conv_id
    ).order("created_at").execute()
    turns = [
        ConversationTurn(
            role=t["role"],
            content=t["content"],
            layer_contributions=t.get("layer_contributions"),
            trace_id=t.get("trace_id"),
            timestamp=t.get("created_at"),
            turn_metadata=t.get("turn_metadata"),
        )
        for t in (turns_res.data or [])
    ]
    return ConversationSession(
        session_id=row["session_id"],
        tenant_id=row["tenant_id"],
        accountant_id=row["accountant_id"],
        topic=row.get("topic"),
        pais=row.get("pais", "colombia"),
        user_id=str(row.get("user_id", "") or ""),
        company_id=str(row.get("company_id", "") or ""),
        integration_id=str(row.get("integration_id", "") or ""),
        host_session_id=str(row.get("host_session_id", "") or ""),
        channel=str(row.get("channel", "chat") or "chat"),
        status=str(row.get("status", "active") or "active"),
        memory_summary=str(row.get("memory_summary", "") or ""),
        turns=turns,
        created_at=str(row.get("created_at", "")),
        updated_at=str(row.get("updated_at", "")),
    )


def _sb_get_conversation_id(session_id: str, tenant_id: str = "") -> str | None:
    from lia_contador.supabase_client import get_supabase_client
    client = get_supabase_client()
    query = client.table("conversations").select("id").eq("session_id", session_id)
    if tenant_id:
        query = query.eq("tenant_id", tenant_id)
    res = query.execute()
    if not res.data:
        return None
    return str(res.data[0]["id"])


def _sb_list_sessions_via_view(
    *,
    tenant_id: str | None,
    limit: int,
    user_id: str | None = None,
    company_id: str | None = None,
    topic: str | None = None,
    offset: int = 0,
    status: str | None = None,
) -> list[dict[str, Any]]:
    """Single-query path using the ``conversation_summaries`` view."""
    from lia_contador.supabase_client import get_supabase_client
    client = get_supabase_client()
    query = client.table("conversation_summaries").select(
        "session_id, tenant_id, topic, pais, created_at, updated_at,"
        " user_id, company_id, integration_id, channel, status,"
        " memory_summary, turn_count, first_question"
    )
    if tenant_id:
        query = query.eq("tenant_id", tenant_id)
    if user_id:
        query = query.eq("user_id", user_id)
    if company_id:
        query = query.eq("company_id", company_id)
    if topic:
        query = query.eq("topic", topic)
    if status:
        query = query.eq("status", status)
    res = query.order("updated_at", desc=True).range(offset, offset + limit - 1).execute()
    return [
        {
            "session_id": row["session_id"],
            "tenant_id": str(row.get("tenant_id", "") or ""),
            "topic": row.get("topic"),
            "pais": row.get("pais", ""),
            "created_at": str(row.get("created_at", "")),
            "updated_at": str(row.get("updated_at", "")),
            "turn_count": row.get("turn_count", 0),
            "first_question": str(row.get("first_question", "") or ""),
            "user_id": str(row.get("user_id", "") or ""),
            "company_id": str(row.get("company_id", "") or ""),
            "integration_id": str(row.get("integration_id", "") or ""),
            "channel": str(row.get("channel", "chat") or "chat"),
            "status": str(row.get("status", "active") or "active"),
            "memory_summary": str(row.get("memory_summary", "") or ""),
        }
        for row in (res.data or [])
    ]


def _sb_list_sessions_legacy(
    *,
    tenant_id: str | None,
    limit: int,
    user_id: str | None = None,
    company_id: str | None = None,
    topic: str | None = None,
    offset: int = 0,
    status: str | None = None,
) -> list[dict[str, Any]]:
    """N+1 fallback used when the ``conversation_summaries`` view is missing."""
    from lia_contador.supabase_client import get_supabase_client
    client = get_supabase_client()
    query = client.table("conversations").select(
        "session_id, tenant_id, topic, pais, created_at, updated_at, id, user_id, company_id, integration_id, channel, status, memory_summary"
    )
    if tenant_id:
        query = query.eq("tenant_id", tenant_id)
    if user_id:
        query = query.eq("user_id", user_id)
    if company_id:
        query = query.eq("company_id", company_id)
    if topic:
        query = query.eq("topic", topic)
    if status:
        query = query.eq("status", status)
    res = query.order("updated_at", desc=True).range(offset, offset + limit - 1).execute()
    sessions: list[dict[str, Any]] = []
    for row in res.data or []:
        turns_res = client.table("conversation_turns").select(
            "role, content"
        ).eq("conversation_id", row["id"]).order("created_at").limit(1).execute()
        first_question = ""
        for t in turns_res.data or []:
            if t.get("role") == "user" and t.get("content"):
                first_question = str(t["content"])[:120]
                break
        turn_count_res = client.table("conversation_turns").select(
            "id", count="exact"
        ).eq("conversation_id", row["id"]).execute()
        sessions.append({
            "session_id": row["session_id"],
            "tenant_id": str(row.get("tenant_id", "") or ""),
            "topic": row.get("topic"),
            "pais": row.get("pais", ""),
            "created_at": str(row.get("created_at", "")),
            "updated_at": str(row.get("updated_at", "")),
            "turn_count": turn_count_res.count or 0,
            "first_question": first_question,
            "user_id": str(row.get("user_id", "") or ""),
            "company_id": str(row.get("company_id", "") or ""),
            "integration_id": str(row.get("integration_id", "") or ""),
            "channel": str(row.get("channel", "chat") or "chat"),
            "status": str(row.get("status", "active") or "active"),
            "memory_summary": str(row.get("memory_summary", "") or ""),
        })
    return sessions


def _sb_list_sessions(
    *,
    tenant_id: str | None,
    limit: int,
    user_id: str | None = None,
    company_id: str | None = None,
    topic: str | None = None,
    offset: int = 0,
    status: str | None = None,
) -> list[dict[str, Any]]:
    kwargs = dict(
        tenant_id=tenant_id, limit=limit, user_id=user_id,
        company_id=company_id, topic=topic, offset=offset, status=status,
    )
    try:
        return _sb_list_sessions_via_view(**kwargs)
    except Exception:
        _log.debug("conversation_summaries view not available, falling back to N+1 queries")
        return _sb_list_sessions_legacy(**kwargs)


# ---------------------------------------------------------------------------
# Public API — dispatch based on backend
# ---------------------------------------------------------------------------

def create_session(
    *,
    tenant_id: str,
    accountant_id: str,
    topic: str | None = None,
    pais: str = "colombia",
    session_id: str | None = None,
    user_id: str = "",
    company_id: str = "",
    integration_id: str = "",
    host_session_id: str = "",
    channel: str = "chat",
    status: str = "active",
    memory_summary: str = "",
    base_dir: Path = DEFAULT_CONVERSATIONS_DIR,
) -> ConversationSession:
    resolved_session_id = str(session_id or "").strip() or str(uuid4())
    session = ConversationSession(
        session_id=resolved_session_id,
        tenant_id=tenant_id,
        accountant_id=accountant_id,
        topic=topic,
        pais=pais,
        user_id=user_id,
        company_id=company_id,
        integration_id=integration_id,
        host_session_id=host_session_id,
        channel=channel,
        status=status,
        memory_summary=memory_summary,
    )
    if _use_supabase(base_dir):
        _sb_create_session(session)
    else:
        _fs_save_session(session, base_dir=base_dir)
    return session


def load_session(
    *,
    tenant_id: str,
    session_id: str,
    user_id: str | None = None,
    company_id: str | None = None,
    base_dir: Path = DEFAULT_CONVERSATIONS_DIR,
) -> ConversationSession | None:
    if _use_supabase(base_dir):
        return _sb_load_session(tenant_id=tenant_id, session_id=session_id, user_id=user_id, company_id=company_id)
    return _fs_load_session(
        tenant_id=tenant_id,
        session_id=session_id,
        base_dir=base_dir,
        user_id=user_id,
        company_id=company_id,
    )


def ensure_session(
    *,
    tenant_id: str,
    session_id: str,
    accountant_id: str,
    topic: str | None = None,
    pais: str = "colombia",
    user_id: str = "",
    company_id: str = "",
    integration_id: str = "",
    host_session_id: str = "",
    channel: str = "chat",
    status: str = "active",
    memory_summary: str = "",
    base_dir: Path = DEFAULT_CONVERSATIONS_DIR,
) -> ConversationSession:
    existing = load_session(
        tenant_id=tenant_id,
        session_id=session_id,
        user_id=user_id or None,
        company_id=company_id or None,
        base_dir=base_dir,
    )
    if existing is not None:
        return existing
    return create_session(
        tenant_id=tenant_id,
        session_id=session_id,
        accountant_id=accountant_id,
        topic=topic,
        pais=pais,
        user_id=user_id,
        company_id=company_id,
        integration_id=integration_id,
        host_session_id=host_session_id,
        channel=channel,
        status=status,
        memory_summary=memory_summary,
        base_dir=base_dir,
    )


def ensure_session_shell(
    *,
    tenant_id: str,
    session_id: str,
    accountant_id: str,
    topic: str | None = None,
    pais: str = "colombia",
    user_id: str = "",
    company_id: str = "",
    integration_id: str = "",
    host_session_id: str = "",
    channel: str = "chat",
    status: str = "active",
    memory_summary: str = "",
    base_dir: Path = DEFAULT_CONVERSATIONS_DIR,
) -> None:
    session = ConversationSession(
        session_id=session_id,
        tenant_id=tenant_id,
        accountant_id=accountant_id,
        topic=topic,
        pais=pais,
        user_id=user_id,
        company_id=company_id,
        integration_id=integration_id,
        host_session_id=host_session_id,
        channel=channel,
        status=status,
        memory_summary=memory_summary,
        turns=[],
    )
    if _use_supabase(base_dir):
        _sb_upsert_session_shell(session)
        return
    path = _tenant_dir(base_dir, tenant_id) / f"{session_id}.json"
    if path.exists():
        return
    _fs_save_session(session, base_dir=base_dir)


def append_turn(
    *,
    tenant_id: str,
    session_id: str,
    turn: ConversationTurn,
    user_id: str | None = None,
    company_id: str | None = None,
    base_dir: Path = DEFAULT_CONVERSATIONS_DIR,
) -> ConversationSession | None:
    if not turn.timestamp:
        turn.timestamp = _utc_now_iso()
    if _use_supabase(base_dir):
        conv_id = _sb_get_conversation_id(session_id, tenant_id=tenant_id)
        if conv_id is None:
            return None
        _sb_save_turn(conv_id, turn)
        # Update conversation updated_at
        from lia_contador.supabase_client import get_supabase_client
        client = get_supabase_client()
        client.table("conversations").update(
            {"updated_at": _utc_now_iso()}
        ).eq("session_id", session_id).eq("tenant_id", tenant_id).execute()
        return _sb_load_session(tenant_id=tenant_id, session_id=session_id, user_id=user_id, company_id=company_id)
    session = _fs_load_session(
        tenant_id=tenant_id,
        session_id=session_id,
        base_dir=base_dir,
        user_id=user_id,
        company_id=company_id,
    )
    if session is None:
        return None
    session.turns = session.turns[-MAX_TURNS_PER_SESSION:] + [turn]
    session.updated_at = _utc_now_iso()
    _fs_save_session(session, base_dir=base_dir)
    return session


def update_session_metadata(
    *,
    tenant_id: str,
    session_id: str,
    user_id: str | None = None,
    company_id: str | None = None,
    memory_summary: str | None = None,
    status: str | None = None,
    channel: str | None = None,
    base_dir: Path = DEFAULT_CONVERSATIONS_DIR,
) -> ConversationSession | None:
    session = load_session(
        tenant_id=tenant_id,
        session_id=session_id,
        user_id=user_id,
        company_id=company_id,
        base_dir=base_dir,
    )
    if session is None:
        return None
    if memory_summary is not None:
        session.memory_summary = str(memory_summary or "").strip()
    if status is not None:
        session.status = str(status or "").strip() or session.status
    if channel is not None:
        session.channel = str(channel or "").strip() or session.channel
    session.updated_at = _utc_now_iso()
    if _use_supabase(base_dir):
        from lia_contador.supabase_client import get_supabase_client

        client = get_supabase_client()
        client.table("conversations").update(
            {
                "memory_summary": session.memory_summary,
                "status": session.status,
                "channel": session.channel,
                "updated_at": session.updated_at,
            }
        ).eq("session_id", session_id).eq("tenant_id", tenant_id).execute()
        return _sb_load_session(tenant_id=tenant_id, session_id=session_id, user_id=user_id, company_id=company_id)
    _fs_save_session(session, base_dir=base_dir)
    return session


def list_distinct_topics(
    *,
    tenant_id: str | None,
    user_id: str | None = None,
    company_id: str | None = None,
    status: str | None = None,
    base_dir: Path = DEFAULT_CONVERSATIONS_DIR,
) -> list[str]:
    """Return sorted list of distinct non-null topics across all conversations."""
    if _use_supabase(base_dir):
        from lia_contador.supabase_client import get_supabase_client
        client = get_supabase_client()
        query = client.table("conversations").select("topic").not_.is_("topic", "null")
        if tenant_id:
            query = query.eq("tenant_id", tenant_id)
        if user_id:
            query = query.eq("user_id", user_id)
        if company_id:
            query = query.eq("company_id", company_id)
        if status:
            query = query.eq("status", status)
        res = query.execute()
        topics = sorted({str(r["topic"]) for r in (res.data or []) if r.get("topic")})
        return topics
    # Filesystem fallback: scan session files
    sessions = _fs_list_sessions(
        tenant_id=tenant_id, base_dir=base_dir, limit=9999,
        user_id=user_id, company_id=company_id,
    )
    return sorted({s["topic"] for s in sessions if s.get("topic")})


def list_sessions(
    *,
    tenant_id: str | None,
    user_id: str | None = None,
    company_id: str | None = None,
    base_dir: Path = DEFAULT_CONVERSATIONS_DIR,
    limit: int = MAX_RECENT_SESSIONS,
    topic: str | None = None,
    offset: int = 0,
    status: str | None = None,
) -> list[dict[str, Any]]:
    if _use_supabase(base_dir):
        return _sb_list_sessions(
            tenant_id=tenant_id, limit=limit, user_id=user_id,
            company_id=company_id, topic=topic, offset=offset, status=status,
        )
    return _fs_list_sessions(
        tenant_id=tenant_id or "",
        base_dir=base_dir,
        limit=limit,
        user_id=user_id,
        company_id=company_id,
    )


# ---------------------------------------------------------------------------
# Public visitor (no-login) — captcha pass registry & usage summary
# ---------------------------------------------------------------------------
#
# Backed by `public_captcha_passes` and the existing `conversations` table for
# the `public_anon` tenant. Both helpers fail closed (return False / empty list)
# when Supabase is unavailable so the captcha gate stays effective even during
# DB outages.


def public_captcha_pass_exists(pub_user_id: str) -> bool:
    """Return True if this IP-hash has already solved the captcha."""
    user_id = str(pub_user_id or "").strip()
    if not user_id:
        return False
    try:
        from lia_contador.supabase_client import get_supabase_client
        client = get_supabase_client()
        if client is None:
            return False
        res = (
            client.table("public_captcha_passes")
            .select("ip_hash")
            .eq("ip_hash", user_id)
            .maybe_single()
            .execute()
        )
        return bool(res and getattr(res, "data", None))
    except Exception:
        return False


def public_captcha_pass_record(pub_user_id: str) -> None:
    """Idempotent UPSERT into `public_captcha_passes`.

    Called once per IP-hash after a successful Turnstile siteverify. Subsequent
    visits from the same IP skip the captcha widget.
    """
    user_id = str(pub_user_id or "").strip()
    if not user_id:
        return
    try:
        from lia_contador.supabase_client import get_supabase_client
        client = get_supabase_client()
        if client is None:
            return
        client.table("public_captcha_passes").upsert(
            {"ip_hash": user_id, "last_seen": _utc_now_iso()},
            on_conflict="ip_hash",
        ).execute()
    except Exception:
        # Best-effort: a failed write only means the user solves the captcha
        # again next visit, not a security regression.
        return


def summarize_public_usage(*, days: int = 30) -> list[dict[str, Any]]:
    """Aggregate public visitor activity for the admin observability panel.

    Returns up to 500 rows of `{user_id, msg_count, first_seen, last_seen}`
    for `tenant_id == 'public_anon'`, ordered by `msg_count DESC`. Raw IPs
    never appear; `user_id` is the synthetic `pub_<hash>` identifier.
    """
    try:
        from lia_contador.supabase_client import get_supabase_client
        client = get_supabase_client()
        if client is None:
            return []
        # Pull conversation rows for the public tenant. We aggregate in Python
        # since the row count is bounded by the public surface (and the daily
        # cap × distinct IPs makes brute aggregation cheap enough).
        res = (
            client.table("conversations")
            .select("user_id, created_at, updated_at")
            .eq("tenant_id", "public_anon")
            .order("updated_at", desc=True)
            .limit(5000)
            .execute()
        )
        rows = (res.data or []) if res else []
    except Exception:
        return []

    buckets: dict[str, dict[str, Any]] = {}
    for row in rows:
        user_id = str(row.get("user_id") or "").strip()
        if not user_id:
            continue
        bucket = buckets.setdefault(
            user_id,
            {
                "user_id": user_id,
                "msg_count": 0,
                "first_seen": row.get("created_at"),
                "last_seen": row.get("updated_at"),
            },
        )
        bucket["msg_count"] += 1
        first = row.get("created_at")
        last = row.get("updated_at")
        if first and (not bucket["first_seen"] or first < bucket["first_seen"]):
            bucket["first_seen"] = first
        if last and (not bucket["last_seen"] or last > bucket["last_seen"]):
            bucket["last_seen"] = last

    summary = sorted(buckets.values(), key=lambda b: b["msg_count"], reverse=True)
    return summary[:500]
