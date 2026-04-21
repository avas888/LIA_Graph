"""Tests for ``POST /api/ingest/intake`` (Phase 2 of ingestfixv1).

The endpoint:
1. validates admin auth
2. rejects empty / oversized / bad-extension uploads
3. classifies via AUTOGENERAR (Phase 1)
4. coerces markdown via Phase 1.5 (heuristic, skip_llm=True at intake time)
5. places the file at ``knowledge_base/<topic>/<filename>`` (Decision A1)
6. optionally mirrors to Dropbox ``to_upload_graph/<topic>/`` (Decision B1)
7. writes a sidecar ``artifacts/intake/<batch_id>.jsonl`` for audit
8. dedups against the active Supabase ``documents.checksum``
9. emits trace events at every stage
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from http import HTTPStatus
from pathlib import Path
from typing import Any

import pytest

from lia_graph import ui_ingest_run_controllers as ctrl
from lia_graph.platform_auth import PlatformAuthError


@dataclass
class _AuthContext:
    role: str = "platform_admin"
    user_id: str = "usr_admin_test"
    tenant_id: str = "tenant-test"


class _FakeHandler:
    def __init__(
        self,
        *,
        role: str = "platform_admin",
        payload: dict[str, Any] | None = None,
    ) -> None:
        self._auth = _AuthContext(role=role)
        self._payload = payload
        self.sent: list[tuple[int, dict[str, Any]]] = []

    def _resolve_auth_context(self, *, required: bool = False) -> _AuthContext:  # noqa: ARG002
        return self._auth

    def _send_auth_error(self, exc: PlatformAuthError) -> None:
        self.sent.append((int(getattr(exc, "http_status", 401)), {"error": str(exc)}))

    def _read_json_payload(self, **_kwargs: Any) -> dict[str, Any] | None:
        return self._payload

    def _send_json(self, status: int, body: dict[str, Any], **_kwargs: Any) -> None:
        self.sent.append((int(status), body))


@pytest.fixture(autouse=True)
def _silence_trace(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, dict[str, Any]]]:
    captured: list[tuple[str, dict[str, Any]]] = []

    def _capture(event: str, payload: dict[str, Any]) -> None:
        captured.append((event, dict(payload)))

    monkeypatch.setattr(ctrl, "_trace", _capture)
    return captured


@pytest.fixture(autouse=True)
def _stub_dedup_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ctrl, "_checksum_already_ingested", lambda checksum: None)


@pytest.fixture(autouse=True)
def _stub_classifier(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make classify_ingestion_document deterministic + offline."""
    from lia_graph import ingestion_classifier as clf

    def _fake_classify(*, filename: str, body_text: str, adapter=None, skip_llm: bool = False):  # noqa: ARG001
        upper = filename.upper()
        body_upper = body_text.upper()
        if (
            upper.startswith("NOM-")
            or "UGPP" in upper
            or "LABORAL" in upper
            or "RESOLUCION-532" in upper
            or "UGPP" in body_upper
        ):
            topic = "laboral"
        elif upper.startswith("IVA-"):
            topic = "iva"
        else:
            topic = "general"
        return clf.AutogenerarResult(
            generated_label=None,
            rationale=None,
            resolved_to_existing=topic,
            synonym_confidence=0.0,
            is_new_topic=False,
            suggested_key=None,
            detected_type="normative_base",
            detected_topic=topic,
            topic_confidence=0.95,
            type_confidence=0.95,
            combined_confidence=0.95,
            classification_source="filename",
            is_raw=False,
            requires_review=False,
        )

    monkeypatch.setattr(ctrl, "_handle_ingest_intake_post", ctrl._handle_ingest_intake_post)
    monkeypatch.setattr("lia_graph.ingestion_classifier.classify_ingestion_document", _fake_classify)


def _b64(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def _deps(workspace_root: Path) -> dict[str, Any]:
    return {"workspace_root": workspace_root}


# ── auth + route discovery ────────────────────────────────────


def test_intake_rejects_non_admin(tmp_path: Path) -> None:
    handler = _FakeHandler(role="tenant_user", payload={"files": []})
    assert ctrl.handle_ingest_post(handler, "/api/ingest/intake", deps=_deps(tmp_path)) is True
    status, _body = handler.sent[0]
    assert status == 403


def test_intake_empty_body_rejected(tmp_path: Path) -> None:
    handler = _FakeHandler(payload={"files": []})
    assert ctrl.handle_ingest_post(handler, "/api/ingest/intake", deps=_deps(tmp_path)) is True
    status, body = handler.sent[0]
    assert status == HTTPStatus.BAD_REQUEST
    assert body["error"] == "files_required"


def test_intake_rejects_unsupported_extension(tmp_path: Path) -> None:
    handler = _FakeHandler(
        payload={
            "files": [
                {"filename": "script.sh", "content_base64": _b64("#!/bin/bash\n")},
            ]
        }
    )
    ctrl.handle_ingest_post(handler, "/api/ingest/intake", deps=_deps(tmp_path))
    _status, body = handler.sent[0]
    assert body["ok"] is True
    assert body["summary"]["rejected"] == 1
    assert body["files"][0]["error"] == "unsupported_extension"


def test_intake_rejects_path_traversal(tmp_path: Path) -> None:
    handler = _FakeHandler(
        payload={
            "files": [
                {"filename": "doc.md", "relative_path": "../etc/passwd", "content_base64": _b64("# doc")},
            ]
        }
    )
    ctrl.handle_ingest_post(handler, "/api/ingest/intake", deps=_deps(tmp_path))
    _status, body = handler.sent[0]
    assert body["files"][0]["error"] == "relative_path_traversal"


def test_intake_rejects_unsafe_filename_chars(tmp_path: Path) -> None:
    handler = _FakeHandler(
        payload={"files": [{"filename": "do<c>.md", "content_base64": _b64("x")}]}
    )
    ctrl.handle_ingest_post(handler, "/api/ingest/intake", deps=_deps(tmp_path))
    _status, body = handler.sent[0]
    assert body["files"][0]["error"] == "filename_unsafe_characters"


def test_intake_rejects_bad_base64(tmp_path: Path) -> None:
    handler = _FakeHandler(
        payload={
            "files": [
                {"filename": "doc.md", "content_base64": "this is not base64!!!"},
            ]
        }
    )
    ctrl.handle_ingest_post(handler, "/api/ingest/intake", deps=_deps(tmp_path))
    _status, body = handler.sent[0]
    assert body["files"][0]["error"] == "invalid_base64"


def test_intake_rejects_batch_over_max(tmp_path: Path) -> None:
    files = [
        {"filename": f"doc_{i}.md", "content_base64": _b64("x")}
        for i in range(ctrl._INTAKE_MAX_FILES + 1)
    ]
    handler = _FakeHandler(payload={"files": files})
    ctrl.handle_ingest_post(handler, "/api/ingest/intake", deps=_deps(tmp_path))
    status, body = handler.sent[0]
    assert status == HTTPStatus.BAD_REQUEST
    assert body["error"] == "batch_too_large"


# ── happy path ────────────────────────────────────────────────


def test_intake_places_labor_file_under_topic_directory(
    tmp_path: Path, _silence_trace: list[tuple[str, dict[str, Any]]]
) -> None:
    markdown = "# Resolución 532/2024\n\nUGPP presunción de costos para independientes."
    handler = _FakeHandler(
        payload={
            "batch_id": "test-batch-1",
            "files": [
                {
                    "filename": "Resolucion-532-2024.md",
                    "relative_path": "NORMATIVA/",
                    "content_base64": _b64(markdown),
                }
            ],
        }
    )
    ctrl.handle_ingest_post(handler, "/api/ingest/intake", deps=_deps(tmp_path))
    status, body = handler.sent[0]
    assert status == HTTPStatus.OK
    assert body["ok"] is True
    assert body["batch_id"] == "test-batch-1"
    assert body["summary"]["placed"] == 1
    assert body["summary"]["rejected"] == 0
    placed = tmp_path / "knowledge_base/laboral/Resolucion-532-2024.md"
    assert placed.exists(), f"file not placed: {placed}"
    # The coerced markdown carries the 8-section canonical shape.
    text = placed.read_text(encoding="utf-8")
    assert "## Identificacion" in text
    assert "## Metadata v2" in text


def test_intake_writes_sidecar_jsonl(tmp_path: Path) -> None:
    markdown = "# doc"
    handler = _FakeHandler(
        payload={
            "batch_id": "test-batch-sidecar",
            "files": [{"filename": "NOM-test.md", "content_base64": _b64(markdown)}],
        }
    )
    ctrl.handle_ingest_post(handler, "/api/ingest/intake", deps=_deps(tmp_path))
    _status, body = handler.sent[0]
    sidecar = tmp_path / "artifacts/intake/test-batch-sidecar.jsonl"
    assert sidecar.exists(), f"sidecar missing: {sidecar}"
    rows = [json.loads(line) for line in sidecar.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 1
    row = rows[0]
    assert row["filename"] == "NOM-test.md"
    assert row["detected_topic"] == "laboral"
    assert row["autogenerar_is_new"] is False
    assert row["classification_source"] == "filename"
    assert "placed_path" in row


def test_intake_checksum_deduplicates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Pretend Supabase says the checksum is already known.
    monkeypatch.setattr(
        ctrl,
        "_checksum_already_ingested",
        lambda checksum: {"doc_id": "doc_already_here", "filename": "x.md", "checksum": checksum},
    )
    handler = _FakeHandler(
        payload={
            "files": [{"filename": "NOM-existing.md", "content_base64": _b64("# Exists already\n")}],
        }
    )
    ctrl.handle_ingest_post(handler, "/api/ingest/intake", deps=_deps(tmp_path))
    _status, body = handler.sent[0]
    assert body["summary"]["deduped"] == 1
    assert body["summary"]["placed"] == 0
    assert body["files"][0]["skipped_duplicate"] is True
    assert body["files"][0]["existing_doc_id"] == "doc_already_here"
    # File NOT written.
    assert not (tmp_path / "knowledge_base/laboral/NOM-existing.md").exists()


def test_intake_mirrors_to_dropbox_when_opted_in(tmp_path: Path) -> None:
    dropbox_root = tmp_path / "Dropbox"
    dropbox_root.mkdir()
    handler = _FakeHandler(
        payload={
            "files": [{"filename": "NOM-mirror.md", "content_base64": _b64("# m")}],
            "options": {"mirror_to_dropbox": True, "dropbox_root": str(dropbox_root)},
        }
    )
    ctrl.handle_ingest_post(handler, "/api/ingest/intake", deps=_deps(tmp_path))
    mirrored = dropbox_root / "to_upload_graph/laboral/NOM-mirror.md"
    assert mirrored.exists(), f"mirror not written: {mirrored}"


def test_intake_emits_expected_trace_events_in_order(
    tmp_path: Path, _silence_trace: list[tuple[str, dict[str, Any]]]
) -> None:
    handler = _FakeHandler(
        payload={
            "batch_id": "test-trace",
            "files": [{"filename": "NOM-trace.md", "content_base64": _b64("# d")}],
        }
    )
    ctrl.handle_ingest_post(handler, "/api/ingest/intake", deps=_deps(tmp_path))
    event_names = [name for name, _ in _silence_trace]
    assert event_names[0] == "ingest.intake.received"
    assert "ingest.intake.classified" in event_names
    assert "ingest.intake.placed" in event_names
    assert event_names[-1] == "ingest.intake.summary"


def test_intake_batch_id_generated_when_missing(tmp_path: Path) -> None:
    handler = _FakeHandler(
        payload={"files": [{"filename": "NOM-auto.md", "content_base64": _b64("# a")}]}
    )
    ctrl.handle_ingest_post(handler, "/api/ingest/intake", deps=_deps(tmp_path))
    _status, body = handler.sent[0]
    assert body["batch_id"].startswith("intake_")


def test_intake_mixed_batch_partial_success(tmp_path: Path) -> None:
    handler = _FakeHandler(
        payload={
            "files": [
                {"filename": "NOM-good.md", "content_base64": _b64("# ok")},
                {"filename": "bad.sh", "content_base64": _b64("# rejected")},
                {"filename": "IVA-second.md", "content_base64": _b64("# two")},
            ]
        }
    )
    ctrl.handle_ingest_post(handler, "/api/ingest/intake", deps=_deps(tmp_path))
    _status, body = handler.sent[0]
    assert body["summary"]["placed"] == 2
    assert body["summary"]["rejected"] == 1
