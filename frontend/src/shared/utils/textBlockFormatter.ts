/**
 * Pure text-segmentation helpers shared between desktop profile renderer
 * and mobile normativa panel.
 *
 * Single concern per function — no DOM, no HTML. Callers compose these
 * to build either real DOM nodes (desktop) or HTML strings (mobile).
 *
 * Input model: a multi-line text block where "\n\n" separates paragraph
 * blocks and "\n" inside a block separates lines. Bullet blocks are ones
 * where every non-empty line starts with a `-`, `•`, or `·` marker.
 */

export const BULLET_MARKER_RE = /^[-•·]\s+/;

/**
 * Normalize CRLF → LF, trim, split on blank lines, drop empty blocks.
 */
export function splitParagraphBlocks(text: string): string[] {
  const normalized = String(text ?? "").replace(/\r\n/g, "\n").trim();
  if (!normalized) return [];
  return normalized
    .split(/\n{2,}/)
    .map((block) => block.trim())
    .filter(Boolean);
}

/**
 * Split a single block on hard line breaks, trim each line, drop blanks.
 */
export function splitBlockLines(block: string): string[] {
  return String(block ?? "")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

/**
 * A block is treated as a bullet list only when every non-empty line
 * carries a bullet marker.
 */
export function isBulletListBlock(lines: string[]): boolean {
  return lines.length > 0 && lines.every((line) => BULLET_MARKER_RE.test(line));
}

export function stripBulletMarker(line: string): string {
  return String(line ?? "").replace(BULLET_MARKER_RE, "");
}
