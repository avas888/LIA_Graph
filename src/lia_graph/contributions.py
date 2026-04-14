from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

_CONTRIBUTIONS: list["Contribution"] = []


@dataclass
class Contribution:
    contribution_id: str
    title: str = ""
    body: str = ""
    status: str = "pending"
    metadata: dict[str, Any] = field(default_factory=dict)


def save_contribution(payload: dict[str, Any]) -> Contribution:
    row = Contribution(
        contribution_id=str(payload.get("contribution_id") or f"contrib_{len(_CONTRIBUTIONS)+1}"),
        title=str(payload.get("title") or ""),
        body=str(payload.get("body") or ""),
        metadata=dict(payload.get("metadata") or {}),
    )
    _CONTRIBUTIONS.append(row)
    return row


def list_contributions(*args: Any, **kwargs: Any) -> list[Contribution]:
    return list(_CONTRIBUTIONS)


def approve_contribution(contribution_id: str, *args: Any, **kwargs: Any) -> Contribution | None:
    for row in _CONTRIBUTIONS:
        if row.contribution_id == contribution_id:
            row.status = "approved"
            return row
    return None


def reject_contribution(contribution_id: str, *args: Any, **kwargs: Any) -> Contribution | None:
    for row in _CONTRIBUTIONS:
        if row.contribution_id == contribution_id:
            row.status = "rejected"
            return row
    return None

