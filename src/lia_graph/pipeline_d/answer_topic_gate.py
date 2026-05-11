"""Cross-topic content gate for synthesis-time answer assembly (fix_v7 §3c).

Background
----------
Even when the router classifies a turn correctly, the synthesis layer
can still embed bullets that cite off-topic norms. Example from the
2026-05-11 diagnostic probe: Q4/Q5 (beneficio de auditoría) returned
"Ruta sugerida" / "Riesgos" sections composed around Art. 147 ET
(pérdidas fiscales), Art. 290, Art. 588 — all out of scope for a
beneficio-auditoría question.

The polish-side guardrails (`answer_llm_polish.py`) catch *newly
invented* norm lineage / periods that the LLM hallucinates, but they
cannot rewrite the template the polish sees. This gate is the
template-side complement: drop bullets whose cited norms fall outside
the primary topic's allowlist BEFORE polish ever runs.

Design properties
-----------------
- **Safe-by-default.** If `config/topic_norm_allowlist.json` is missing
  or the primary topic has no entry, the gate is a no-op. The gate
  cannot make answers WORSE than today.
- **Bullet-granular.** Drops bullets, never paragraphs / headers / prose
  scaffolding. Section structure is preserved exactly.
- **No-citation bullets pass.** A procedural step like "Verifica las
  declaraciones de los últimos 3 años" has no norm anchor; it stays.
- **Operator override.** `LIA_TOPIC_GATE_MODE=off` short-circuits to
  return the template unchanged without removing the config file.
- **Diagnostics.** Every applied gate emits `synthesis.topic_gate.applied`
  in the pipeline trace with `gate_mode`, `dropped_count`, and the first
  ~5 dropped bullet excerpts so operators can spot over-firing fast.

Implementation notes
--------------------
- Article numbers are matched against the inline anchor regex
  `(art. <N>[, ...]? ET)` / `(arts. <N> y <M> ET)` and the wider form
  `Art. <N> ET`. The Colombian corpus uses both shapes interchangeably.
- A bullet is KEPT if every norm anchor it cites has an article number
  whose canonical key `art:<number>` matches one of the
  `allowed_prefixes` strings for the primary topic, OR if the bullet
  has no norm anchor at all.
- Future expansion: when synthesis exposes per-bullet provenance
  (source chunk topic), the gate will also pass bullets whose chunk
  topic is in `cross_topic_allowed[primary_topic]`. Until then the
  cross-topic carve-out is provided as a hint for the operator
  curating the allowlist (used in tests).
"""

from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

_ALLOWLIST_PATH = (
    Path(__file__).resolve().parents[3]
    / "config"
    / "topic_norm_allowlist.json"
)

# Match an inline anchor like `(art. 147 ET)`, `(arts. 147 y 290 ET)`,
# `(arts. 147, 290 y 588 ET)`, or the bare `Art. 147 ET`. The article
# number can include a hyphenated paragraph (`689-3`), a letter suffix
# (`107A`), or be a multi-digit number.
# Matches both the parenthesized inline anchor `(art. 147 ET)` /
# `(arts. 290, 588 y 589 ET)` AND the bare prose form `Art. 147 ET` /
# `Arts. 290, 588 y 589 ET`. The article number can be multi-digit,
# hyphenated (`689-3`), or letter-suffixed (`107A`).
_NORM_INLINE_RE = re.compile(
    r"""
    (?:\(\s*)?                                # optional opening paren
    \bart[s]?\.?\s+                           # art | arts | art. | arts.
    (?P<head>\d+(?:-\d+)?[A-Za-z]?)           # first article number
    (?P<tail>
        (?:\s*[,;]\s*\d+(?:-\d+)?[A-Za-z]?)*  # , 290 ; 588
        (?:\s+y\s+\d+(?:-\d+)?[A-Za-z]?)?     # y 589
    )
    \s+ET                                     # the ET marker
    (?:\s*\))?                                # optional closing paren
    \b
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Pull article numbers out of the `head` + `tail` groups.
_NUM_RE = re.compile(r"\d+(?:-\d+)?[A-Za-z]?")

# Trace seam — no-op when the tracer isn't loaded (e.g. test harness).
try:
    from tracers_and_logs import pipeline_trace as _trace
except ImportError:  # pragma: no cover - tracer always present in served runtime
    _trace = None  # type: ignore[assignment]


def _trace_step(step_name: str, *, status: str = "ok", **details: Any) -> None:
    if _trace is None:
        return
    _trace.step(step_name, status=status, **details)


_GATE_ENV_FLAG = "LIA_TOPIC_GATE_MODE"


def _gate_enabled() -> bool:
    raw = str(os.getenv(_GATE_ENV_FLAG, "enforce") or "").strip().lower()
    # Anything other than the explicit off-switch counts as on so the
    # default behavior matches the launcher default.
    return raw not in {"off", "0", "false", "no", "disabled"}


@lru_cache(maxsize=1)
def _load_allowlist() -> dict[str, Any]:
    if not _ALLOWLIST_PATH.is_file():
        return {}
    try:
        raw = json.loads(_ALLOWLIST_PATH.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — corrupt config must not break chat
        return {}
    if not isinstance(raw, dict):
        return {}
    return raw


def _topic_entry(primary_topic: str | None) -> dict[str, Any] | None:
    if not primary_topic:
        return None
    allowlist = _load_allowlist()
    entry = allowlist.get(primary_topic)
    if not isinstance(entry, dict):
        return None
    return entry


def _normalize_article_key(num: str) -> str:
    """Canonical form for matching against allowed_prefixes.

    Article numbers from `_NORM_INLINE_RE` come in as `147`, `689-3`,
    `107A`. The canonical form is `art:<lowercased-number>`.
    """
    cleaned = num.strip().lower()
    return f"art:{cleaned}"


def _extract_article_keys(bullet: str) -> tuple[str, ...]:
    """Return the canonical article keys anchored in this bullet."""
    keys: list[str] = []
    for match in _NORM_INLINE_RE.finditer(bullet):
        head = match.group("head")
        if head:
            keys.append(_normalize_article_key(head))
        tail = match.group("tail") or ""
        for sub in _NUM_RE.findall(tail):
            keys.append(_normalize_article_key(sub))
    return tuple(dict.fromkeys(keys))  # preserve order, dedupe


def _bullet_passes(
    bullet: str,
    allowed_prefixes: tuple[str, ...],
) -> bool:
    if not allowed_prefixes:
        # Operator did not curate the allowlist for this topic. Treat as
        # noop (pass everything) per the safe-by-default property.
        return True
    article_keys = _extract_article_keys(bullet)
    if not article_keys:
        # Procedural / prose bullet with no norm anchor — keep.
        return True
    for key in article_keys:
        if not any(
            key.startswith(prefix) or key == prefix
            for prefix in allowed_prefixes
        ):
            return False
    return True


# A line starts with one of these markers to be a bullet head.
_BULLET_HEAD_RE = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+")
_INDENTED_CONTINUATION_RE = re.compile(r"^\s{2,}\S")


def _split_bullets(template: str) -> list[dict[str, Any]]:
    """Split the template into a flat list of `{kind, text}`.

    `kind == "bullet"` for any bullet line PLUS its indented
    continuation lines (so multi-line bullets stay intact when one is
    dropped). Everything else is `"prose"` and passes through unfiltered
    so section headers, blank lines, and trailing paragraphs are
    preserved exactly.
    """
    if not template:
        return []
    lines = template.splitlines(keepends=True)
    segments: list[dict[str, Any]] = []
    cursor = 0
    while cursor < len(lines):
        line = lines[cursor]
        if _BULLET_HEAD_RE.match(line):
            # Greedy: this bullet consumes itself + any subsequent
            # indented continuation lines (and blank lines wedged
            # between continuation lines).
            chunk: list[str] = [line]
            scan = cursor + 1
            while scan < len(lines):
                nxt = lines[scan]
                if _BULLET_HEAD_RE.match(nxt):
                    break
                if _INDENTED_CONTINUATION_RE.match(nxt):
                    chunk.append(nxt)
                    scan += 1
                    continue
                break
            segments.append({"kind": "bullet", "text": "".join(chunk)})
            cursor = scan
        else:
            segments.append({"kind": "prose", "text": line})
            cursor += 1
    return segments


def filter_template_bullets(
    template: str,
    *,
    primary_topic: str | None,
    secondary_topics: Iterable[str] = (),
) -> tuple[str, dict[str, Any]]:
    """Drop bullets whose cited norms fall outside the topic allowlist.

    Returns ``(filtered_template, diag)``. The diagnostic dict is also
    written to the pipeline trace under
    ``synthesis.topic_gate.applied`` so SME evals can verify whether
    the gate fired and what was dropped.
    """

    if not template:
        return template, {"gate_mode": "noop_empty_template"}

    if not _gate_enabled():
        diag = {"gate_mode": "disabled_by_env"}
        _trace_step("synthesis.topic_gate.applied", **diag)
        return template, diag

    entry = _topic_entry(primary_topic)
    if entry is None:
        diag = {
            "gate_mode": "noop_no_topic_entry",
            "primary_topic": primary_topic,
        }
        _trace_step("synthesis.topic_gate.applied", **diag)
        return template, diag

    allowed_prefixes = tuple(entry.get("allowed_prefixes") or ())
    cross_topic_allowed = tuple(entry.get("cross_topic_allowed") or ())

    segments = _split_bullets(template)
    kept_segments: list[dict[str, Any]] = []
    dropped: list[str] = []
    for seg in segments:
        if seg["kind"] != "bullet":
            kept_segments.append(seg)
            continue
        if _bullet_passes(seg["text"], allowed_prefixes):
            kept_segments.append(seg)
        else:
            dropped.append(seg["text"])
    filtered = "".join(seg["text"] for seg in kept_segments)

    diag = {
        "gate_mode": "applied",
        "primary_topic": primary_topic,
        "secondary_topics": list(secondary_topics) or [],
        "cross_topic_allowed": list(cross_topic_allowed),
        "allowed_prefix_count": len(allowed_prefixes),
        "kept_count": sum(1 for s in kept_segments if s["kind"] == "bullet"),
        "dropped_count": len(dropped),
        "dropped_excerpts": [d.strip().replace("\n", " ")[:120] for d in dropped[:5]],
    }
    _trace_step("synthesis.topic_gate.applied", **diag)
    return filtered, diag


__all__ = [
    "filter_template_bullets",
]
