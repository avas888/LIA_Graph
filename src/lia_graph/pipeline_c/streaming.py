from __future__ import annotations

from dataclasses import dataclass
import re

_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+\S")
_BULLET_RE = re.compile(r"^\s*(?:[-*+]\s+\S|\d+[\.\)]\s+\S)")
_BLOCKQUOTE_RE = re.compile(r"^\s*>\s+\S")
_TABLE_RE = re.compile(r"^\s*\|.*\|\s*$")
_TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$")
_FENCE_RE = re.compile(r"^\s*```")
_DOUBLE_ASTERISK_RE = re.compile(r"(?<!\*)\*\*(?!\*)")
_DOUBLE_UNDERSCORE_RE = re.compile(r"(?<!_)__(?!_)")
_INCOMPLETE_TAIL_RE = re.compile(r"[,;:/\-([{]$")


@dataclass(frozen=True)
class StreamBlock:
    index: int
    markdown: str
    block_kind: str


def normalize_streamed_markdown(value: str) -> str:
    text = str(value or "").replace("\r\n", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def markdowns_equivalent(left: str, right: str) -> bool:
    return normalize_streamed_markdown(left) == normalize_streamed_markdown(right)


def _has_balanced_inline_markdown(text: str) -> bool:
    value = str(text or "")
    if value.count("`") % 2 == 1:
        return False
    if len(_DOUBLE_ASTERISK_RE.findall(value)) % 2 == 1:
        return False
    if len(_DOUBLE_UNDERSCORE_RE.findall(value)) % 2 == 1:
        return False
    return True


def _looks_like_complete_terminal_line(text: str) -> bool:
    stripped = str(text or "").rstrip()
    if not stripped:
        return False
    if stripped.endswith(("...", "\u2014")):
        return False
    if _INCOMPLETE_TAIL_RE.search(stripped):
        return False
    if not _has_balanced_inline_markdown(stripped):
        return False
    if stripped[-1] in ".!?:)]}\"'`":
        return True
    return bool(_BULLET_RE.match(stripped) or _HEADING_RE.match(stripped) or _BLOCKQUOTE_RE.match(stripped))


def _consume_fenced_block(text: str, *, allow_partial_final: bool) -> tuple[str | None, int]:
    if not _FENCE_RE.match(text):
        return None, 0
    closing_match = re.search(r"\n```[^\n]*\n?", text[1:])
    if closing_match:
        end = closing_match.end() + 1
        return text[:end].strip(), end
    if allow_partial_final and text.strip().endswith("```"):
        return text.strip(), len(text)
    return None, 0


def _consume_table_block(text: str, *, allow_partial_final: bool) -> tuple[str | None, int]:
    lines = text.splitlines(keepends=True)
    if not lines or not _TABLE_RE.match(lines[0].rstrip("\n")):
        return None, 0
    consumed = 0
    block_lines: list[str] = []
    for idx, line in enumerate(lines):
        stripped = line.rstrip("\n")
        if idx == 1 and not (_TABLE_RE.match(stripped) or _TABLE_SEPARATOR_RE.match(stripped)):
            return None, 0
        if stripped.strip() == "":
            break
        if not (_TABLE_RE.match(stripped) or _TABLE_SEPARATOR_RE.match(stripped)):
            return None, 0
        consumed += len(line)
        block_lines.append(stripped)
    else:
        if not allow_partial_final:
            return None, 0
    if len(block_lines) < 2:
        return None, 0
    return "\n".join(block_lines).strip(), consumed


def _consume_line_block(
    text: str,
    *,
    matcher: re.Pattern[str],
    block_kind: str,
    allow_partial_final: bool,
) -> tuple[str | None, int, str | None]:
    newline_index = text.find("\n")
    if newline_index == -1:
        if not allow_partial_final:
            return None, 0, None
        candidate = text.strip()
        if candidate and matcher.match(candidate) and _has_balanced_inline_markdown(candidate):
            return candidate, len(text), block_kind
        return None, 0, None
    line = text[:newline_index].rstrip()
    if not matcher.match(line):
        return None, 0, None
    if not _has_balanced_inline_markdown(line):
        return None, 0, None
    return line, newline_index + 1, block_kind


def _consume_paragraph(text: str, *, allow_partial_final: bool) -> tuple[str | None, int]:
    double_newline = text.find("\n\n")
    if double_newline != -1:
        candidate = text[:double_newline].strip()
        if candidate and _has_balanced_inline_markdown(candidate):
            return candidate, double_newline + 2
        return None, 0
    if not allow_partial_final:
        return None, 0
    candidate = text.strip()
    if not candidate:
        return None, 0
    if not _looks_like_complete_terminal_line(candidate.splitlines()[-1]):
        return None, 0
    return candidate, len(text)


class StructuredMarkdownStreamAssembler:
    def __init__(self) -> None:
        self._buffer = ""
        self._next_index = 0
        self._rendered_markdown_parts: list[str] = []

    @property
    def rendered_markdown(self) -> str:
        return normalize_streamed_markdown("\n\n".join(self._rendered_markdown_parts))

    def feed(self, delta: str) -> list[StreamBlock]:
        self._buffer += str(delta or "")
        return self._drain(allow_partial_final=False)

    def finalize(self, *, finish_reason: str | None = None) -> list[StreamBlock]:
        allow_partial_final = str(finish_reason or "").strip().lower() not in {"length", "max_tokens"}
        blocks = self._drain(allow_partial_final=allow_partial_final)
        if allow_partial_final:
            trailing = normalize_streamed_markdown(self._buffer)
            if trailing:
                block = StreamBlock(index=self._next_index, markdown=trailing, block_kind="paragraph")
                self._next_index += 1
                self._rendered_markdown_parts.append(trailing)
                blocks.append(block)
                self._buffer = ""
        return blocks

    def _drain(self, *, allow_partial_final: bool) -> list[StreamBlock]:
        blocks: list[StreamBlock] = []
        while True:
            stripped_leading = len(self._buffer) - len(self._buffer.lstrip("\n"))
            if stripped_leading:
                self._buffer = self._buffer[stripped_leading:]
            if not self._buffer:
                break

            block_markdown: str | None = None
            consumed = 0
            block_kind = "paragraph"

            block_markdown, consumed = _consume_fenced_block(self._buffer, allow_partial_final=allow_partial_final)
            if block_markdown:
                block_kind = "code"
            else:
                block_markdown, consumed = _consume_table_block(self._buffer, allow_partial_final=allow_partial_final)
                if block_markdown:
                    block_kind = "table"
            if not block_markdown:
                block_markdown, consumed, maybe_kind = _consume_line_block(
                    self._buffer,
                    matcher=_HEADING_RE,
                    block_kind="heading",
                    allow_partial_final=allow_partial_final,
                )
                if block_markdown:
                    block_kind = maybe_kind or "heading"
            if not block_markdown:
                block_markdown, consumed, maybe_kind = _consume_line_block(
                    self._buffer,
                    matcher=_BULLET_RE,
                    block_kind="list_item",
                    allow_partial_final=allow_partial_final,
                )
                if block_markdown:
                    block_kind = maybe_kind or "list_item"
            if not block_markdown:
                block_markdown, consumed, maybe_kind = _consume_line_block(
                    self._buffer,
                    matcher=_BLOCKQUOTE_RE,
                    block_kind="blockquote",
                    allow_partial_final=allow_partial_final,
                )
                if block_markdown:
                    block_kind = maybe_kind or "blockquote"
            if not block_markdown:
                block_markdown, consumed = _consume_paragraph(self._buffer, allow_partial_final=allow_partial_final)
                if block_markdown:
                    block_kind = "paragraph"

            if not block_markdown or consumed <= 0:
                break

            normalized = normalize_streamed_markdown(block_markdown)
            if normalized:
                block = StreamBlock(index=self._next_index, markdown=normalized, block_kind=block_kind)
                self._next_index += 1
                self._rendered_markdown_parts.append(normalized)
                blocks.append(block)
            self._buffer = self._buffer[consumed:]
        return blocks
