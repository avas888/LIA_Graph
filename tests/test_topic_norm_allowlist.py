"""Config-validation tests for `config/topic_norm_allowlist.json`
(fix_v7 §3c). Runs as part of `make test-batched` so every PR that
touches the allowlist or the topic taxonomy gets a contract check.

Invariants:
1. The file loads as JSON and is a dict.
2. Every non-meta key is a real topic in
   `topic_router_keywords._TOPIC_KEYWORDS` (no hallucinated topics).
3. Every entry has `allowed_prefixes` as a list of canonical-form
   strings (`art:<number>`, lowercased).
4. Every entry's `cross_topic_allowed` (when present) names real topics
   that exist in `_TOPIC_KEYWORDS`.
5. No duplicate prefixes within a single topic entry.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest


_ALLOWLIST_PATH = (
    Path(__file__).resolve().parents[1]
    / "config"
    / "topic_norm_allowlist.json"
)
_CANONICAL_KEY_RE = re.compile(r"^art:\d+(?:-\d+)?[a-z]?$")


def _load_topic_keys() -> set[str]:
    from lia_graph.topic_router_keywords import _TOPIC_KEYWORDS

    return set(_TOPIC_KEYWORDS.keys())


def _allowlist_entries() -> dict[str, dict]:
    raw = json.loads(_ALLOWLIST_PATH.read_text(encoding="utf-8"))
    assert isinstance(raw, dict), "topic_norm_allowlist.json must be a dict"
    return {k: v for k, v in raw.items() if not k.startswith("_") and isinstance(v, dict)}


def test_allowlist_file_exists_and_loads() -> None:
    assert _ALLOWLIST_PATH.is_file()
    raw = json.loads(_ALLOWLIST_PATH.read_text(encoding="utf-8"))
    assert isinstance(raw, dict)


def test_every_topic_key_exists_in_router_taxonomy() -> None:
    valid_topics = _load_topic_keys()
    entries = _allowlist_entries()
    assert entries, (
        "allowlist scaffold must have at least one topic entry — "
        "an empty file makes the whole gate a no-op which is allowed "
        "but should be intentional, not accidental"
    )
    for topic in entries:
        assert topic in valid_topics, (
            f"topic key {topic!r} in topic_norm_allowlist.json does not "
            f"exist in topic_router_keywords._TOPIC_KEYWORDS — either "
            f"add it to the taxonomy or remove it from the allowlist "
            f"(per feedback_no_hallucinated_examples)"
        )


def test_every_entry_has_allowed_prefixes_list() -> None:
    for topic, entry in _allowlist_entries().items():
        prefixes = entry.get("allowed_prefixes")
        assert isinstance(prefixes, list), (
            f"{topic}: allowed_prefixes must be a list"
        )
        assert prefixes, (
            f"{topic}: allowed_prefixes must be non-empty "
            f"(an empty list would make the gate vacuously drop every "
            f"cited bullet for this topic)"
        )


def test_every_prefix_is_a_canonical_article_key() -> None:
    for topic, entry in _allowlist_entries().items():
        for prefix in entry["allowed_prefixes"]:
            assert isinstance(prefix, str)
            assert _CANONICAL_KEY_RE.match(prefix), (
                f"{topic}: prefix {prefix!r} is not a canonical "
                f"`art:<number>` key (lowercase). Examples: "
                f"`art:147`, `art:689-3`, `art:107a`"
            )


def test_no_duplicate_prefixes_within_a_topic() -> None:
    for topic, entry in _allowlist_entries().items():
        prefixes = entry["allowed_prefixes"]
        assert len(prefixes) == len(set(prefixes)), (
            f"{topic}: allowed_prefixes contains duplicates: {prefixes!r}"
        )


def test_cross_topic_allowed_entries_are_real_topics() -> None:
    valid_topics = _load_topic_keys()
    for topic, entry in _allowlist_entries().items():
        for sibling in entry.get("cross_topic_allowed") or ():
            assert sibling in valid_topics, (
                f"{topic}: cross_topic_allowed lists {sibling!r} which "
                f"is not in topic_router_keywords._TOPIC_KEYWORDS"
            )


def test_meta_fields_are_documented() -> None:
    """The top-level `_doc`, `_schema_version`, and validation hints
    must stay present so future maintainers know how to extend the
    file. Removing them is a regression."""

    raw = json.loads(_ALLOWLIST_PATH.read_text(encoding="utf-8"))
    assert raw.get("_schema_version") == 1
    assert "_doc" in raw
    assert "_topic_keys_source" in raw


@pytest.mark.skipif(
    not __import__("os").environ.get("LIA_SUPABASE_TEST"),
    reason="cloud-chunks validation requires LIA_SUPABASE_TEST=1 + Supabase creds",
)
def test_every_prefix_matches_real_chunks() -> None:
    """fix_v8 §3c hard floor: every `allowed_prefix` in
    `topic_norm_allowlist.json` must match at least one
    ``chunks.reference_key`` row in the active Supabase environment.
    Enforces `feedback_no_hallucinated_examples` for the allowlist
    scaffold — a prefix that resolves to zero chunks is either a typo
    or a corpus gap; either way it must not ship.

    Marked `requires_supabase` so `make test-batched` (local-only)
    skips it; runs only when `LIA_SUPABASE_TEST=1` is exported in a
    shell with cloud Supabase credentials available.
    """
    from lia_graph.supabase_client import get_supabase_client  # type: ignore[attr-defined]

    db = get_supabase_client()
    for topic, entry in _allowlist_entries().items():
        for prefix in entry.get("allowed_prefixes") or ():
            res = (
                db.table("chunks")
                .select("reference_key")
                .like("reference_key", f"{prefix}%")
                .limit(1)
                .execute()
            )
            assert (res.data or []), (
                f"{topic}: prefix {prefix!r} matches zero "
                f"`chunks.reference_key` rows — per "
                f"feedback_no_hallucinated_examples, every prefix must "
                f"be verifiable against real chunks before shipping"
            )
