"""Smoke test: every form_guide profile dir must be loadable end-to-end.

The chat-side citation modal renders a deterministic profile from the
form_guides bundle (`_deterministic_form_citation_profile`). When either
`guide_manifest.json` or `citation_profile.json` is missing, the loader
silently returns None and the modal falls through to a generic empty-state
payload (no facts, no sections), producing a visibly broken modal.

This test catches that regression at CI time so a new form_guide added
without the required files fails loudly here instead of silently in
production.
"""

from __future__ import annotations

from lia_graph.form_guides import load_guide_package
from lia_graph.ui_server_constants import FORM_GUIDES_ROOT


def test_every_form_guide_profile_loads_with_citation_profile():
    assert FORM_GUIDES_ROOT.is_dir(), f"missing form_guides root: {FORM_GUIDES_ROOT}"

    profile_dirs = [
        profile_dir
        for form_dir in sorted(FORM_GUIDES_ROOT.iterdir())
        if form_dir.is_dir()
        for profile_dir in sorted(form_dir.iterdir())
        if profile_dir.is_dir()
    ]
    assert profile_dirs, "expected at least one form_guide profile directory"

    failures: list[str] = []
    for profile_dir in profile_dirs:
        rel = profile_dir.relative_to(FORM_GUIDES_ROOT)
        if not (profile_dir / "guide_manifest.json").is_file():
            failures.append(f"{rel}: missing guide_manifest.json")
            continue
        if not (profile_dir / "citation_profile.json").is_file():
            failures.append(f"{rel}: missing citation_profile.json")
            continue
        package = load_guide_package(profile_dir)
        if package is None:
            failures.append(f"{rel}: load_guide_package returned None")
            continue
        if package.citation_profile is None:
            failures.append(f"{rel}: citation_profile parsed as None")
            continue
        if not package.citation_profile.lead.strip():
            failures.append(f"{rel}: citation_profile.lead is empty")

    assert not failures, "form_guide bundles incomplete:\n  - " + "\n  - ".join(failures)
