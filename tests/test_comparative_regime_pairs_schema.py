"""fix_v8 §3d — schema floor for `config/comparative_regime_pairs.json`.

The pair config is loaded by `pipeline_d/answer_comparative_regime.py`
via `load_config(...)`. A malformed entry can silently disable the
comparative-regime path (`compose_comparative_regime_answer` returns an
empty render and the orchestrator's downstream polish loop may hang on
the empty template). This file pins the minimum shape every pair must
satisfy so config drift fails at CI time, not at chat time.

Invariants per pair:
1. ``domain`` is a non-empty string.
2. ``trigger_anchors`` is a list of non-empty strings.
3. ``dimensions`` is a non-empty list whose entries are dicts with at
   least a ``label`` field.
4. If ``cutoff_year`` is present and non-null, it is an int in
   [1900, 2100].
"""

from __future__ import annotations

import json
from pathlib import Path


_CONFIG_PATH = (
    Path(__file__).resolve().parents[1]
    / "config"
    / "comparative_regime_pairs.json"
)


def _load_pairs() -> dict:
    raw = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    pairs = raw.get("pairs") or {}
    assert isinstance(pairs, dict)
    return pairs


def test_config_loads_and_is_well_formed() -> None:
    assert _CONFIG_PATH.is_file()
    raw = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    assert isinstance(raw, dict)
    assert isinstance(raw.get("pairs"), dict)
    assert raw["pairs"], "pairs map must not be empty"


def test_every_pair_has_domain_and_triggers() -> None:
    for key, pair in _load_pairs().items():
        assert isinstance(pair, dict), f"pair {key!r} must be a dict"
        domain = pair.get("domain")
        assert isinstance(domain, str) and domain.strip(), (
            f"pair {key!r}: domain must be a non-empty string"
        )
        triggers = pair.get("trigger_anchors") or ()
        assert isinstance(triggers, (list, tuple)) and triggers, (
            f"pair {key!r}: trigger_anchors must be a non-empty list"
        )
        for trigger in triggers:
            assert isinstance(trigger, str) and trigger.strip(), (
                f"pair {key!r}: every trigger_anchor must be a "
                f"non-empty string, got {trigger!r}"
            )


def test_every_pair_has_dimensions() -> None:
    for key, pair in _load_pairs().items():
        dims = pair.get("dimensions") or ()
        assert isinstance(dims, (list, tuple)) and dims, (
            f"pair {key!r}: dimensions must be a non-empty list — without "
            f"them the table renderer emits an empty body and the polish "
            f"loop has nothing to work with"
        )
        for d in dims:
            assert isinstance(d, dict), (
                f"pair {key!r}: each dimension must be a dict"
            )
            label = d.get("label")
            assert isinstance(label, str) and label.strip(), (
                f"pair {key!r}: each dimension must have a non-empty `label`"
            )


def test_cutoff_year_is_plausible_when_present() -> None:
    for key, pair in _load_pairs().items():
        cutoff = pair.get("cutoff_year")
        if cutoff is None:
            continue
        assert isinstance(cutoff, int), (
            f"pair {key!r}: cutoff_year must be an int or null, got "
            f"{type(cutoff).__name__}"
        )
        assert 1900 <= cutoff <= 2100, (
            f"pair {key!r}: cutoff_year {cutoff} outside plausible range"
        )
