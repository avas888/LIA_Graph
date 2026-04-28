"""Tests for --rerun-only-refusals — fixplan_v6 §3 step 4.

The flag opens each existing per-norm JSON before deciding to skip:
* veredicto != null → skip (success preserved across cascade reruns)
* veredicto == null (refusal) → re-extract under the new pipeline
* malformed JSON → re-extract (defensive — never silently drop a norm)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lia_graph.scrapers.base import ScraperFetchResult, ScraperRegistry
from lia_graph.vigencia import VigenciaState
import scripts.canonicalizer.extract_vigencia as extract_vigencia


class _FakeScraper:
    source_id = "fake"

    def handles(self, norm_type_value: str, norm_id: str) -> bool:  # noqa: D401
        return True

    def fetch(self, norm_id: str) -> ScraperFetchResult | None:
        return None  # we don't actually need to fetch — extracted JSONs already exist


class _RecordingHarness:
    """Stand-in for VigenciaSkillHarness that records calls without doing work."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def verify_norm(self, *, norm_id: str):
        self.calls.append(norm_id)
        # Re-extracting a refusal that's now successful: return a stub with
        # a veredicto so the script writes a fresh JSON. Use the minimal
        # shape that VigenciaSkillHarness.write_result accepts.
        from lia_graph.vigencia import (
            ExtractionAudit,
            Vigencia,
            VigenciaResult,
        )
        veredicto = Vigencia.from_dict(
            {
                "state": "V",
                "state_from": "2020-01-01",
                "applies_to_kind": "always",
                "fuentes_primarias_consultadas": [
                    {"norm_id": "stub", "norm_type": "url", "url": "https://example.com"}
                ],
            }
        )
        return VigenciaResult(
            veredicto=veredicto,
            audit=ExtractionAudit(skill_version="vigencia-checker@2.0", method="harness"),
        )

    def write_result(self, result, *, norm_id: str, output_dir: Path | None = None) -> Path:
        # Persist a minimal JSON so the run-once guard can detect re-extraction.
        path = (output_dir or Path()) / f"{norm_id.replace('/', '_')}.json"
        path.write_text(
            json.dumps(
                {
                    "norm_id": norm_id,
                    "result": {"veredicto": {"state": "V"}},
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return path


def _seed_input_set(tmp_path: Path, norm_ids: list[str]) -> Path:
    p = tmp_path / "input_set.jsonl"
    p.write_text(
        "\n".join(json.dumps({"norm_id": n}) for n in norm_ids) + "\n",
        encoding="utf-8",
    )
    return p


def _seed_existing_json(out_dir: Path, norm_id: str, *, veredicto: dict | None) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / f"{norm_id}.json"
    p.write_text(
        json.dumps(
            {
                "norm_id": norm_id,
                "result": {"veredicto": veredicto},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return p


def _run_extractor(
    *,
    tmp_path: Path,
    norm_ids: list[str],
    existing: dict[str, dict | None | str],
    rerun_only_refusals: bool,
):
    """Run extract_vigencia.main with a recording harness; return (rc, harness, out_dir)."""

    out_dir = tmp_path / "out"
    out_dir.mkdir()
    for norm_id, payload in existing.items():
        if payload == "MALFORMED":
            (out_dir / f"{norm_id}.json").write_text("{not json", encoding="utf-8")
        else:
            _seed_existing_json(out_dir, norm_id, veredicto=payload)

    input_set_path = _seed_input_set(tmp_path, norm_ids)
    audit_log = tmp_path / "audit.jsonl"
    events_log = tmp_path / "events.jsonl"

    harness = _RecordingHarness()

    # Patch the harness factory so VigenciaSkillHarness.default() is never
    # called (it would try to load a registry / API key).
    import lia_graph.vigencia_extractor as ve

    saved = ve.VigenciaSkillHarness.default
    ve.VigenciaSkillHarness.default = staticmethod(lambda: harness)
    try:
        argv = [
            "--input-set", str(input_set_path),
            "--output-dir", str(out_dir),
            "--run-id", "test-rerun-refusals",
            "--audit-log", str(audit_log),
            "--events-log", str(events_log),
            "--allow-rerun",  # we already seeded JSONs in out_dir
        ]
        if rerun_only_refusals:
            argv.append("--rerun-only-refusals")
        rc = extract_vigencia.main(argv)
    finally:
        ve.VigenciaSkillHarness.default = staticmethod(saved)

    return rc, harness, out_dir


def test_rerun_only_refusals_skips_successes_and_reruns_refusals(tmp_path: Path):
    rc, harness, _out_dir = _run_extractor(
        tmp_path=tmp_path,
        norm_ids=["norm.success", "norm.refusal"],
        existing={
            "norm.success": {"state": "V", "state_from": "2020-01-01"},
            "norm.refusal": None,  # null veredicto → must re-extract
        },
        rerun_only_refusals=True,
    )
    assert rc == 0
    # Only the refusal got re-processed.
    assert harness.calls == ["norm.refusal"]


def test_rerun_only_refusals_re_extracts_malformed_existing(tmp_path: Path):
    rc, harness, _out_dir = _run_extractor(
        tmp_path=tmp_path,
        norm_ids=["norm.malformed"],
        existing={"norm.malformed": "MALFORMED"},
        rerun_only_refusals=True,
    )
    assert rc == 0
    # Malformed JSON falls through and re-extracts (defensive).
    assert harness.calls == ["norm.malformed"]


def test_rerun_only_refusals_off_means_resume_from_checkpoint_owns_skipping(tmp_path: Path):
    """Without the new flag, existing JSONs (success or refusal) are processed
    again by default — only ``--resume-from-checkpoint`` skips them. Confirms
    the new flag is opt-in and doesn't change the historical default."""

    rc, harness, _out_dir = _run_extractor(
        tmp_path=tmp_path,
        norm_ids=["norm.success", "norm.refusal"],
        existing={
            "norm.success": {"state": "V", "state_from": "2020-01-01"},
            "norm.refusal": None,
        },
        rerun_only_refusals=False,
    )
    assert rc == 0
    # Both processed again (no skip).
    assert sorted(harness.calls) == ["norm.refusal", "norm.success"]
