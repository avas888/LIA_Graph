// @ts-nocheck

const FOLLOWUP_SECTION_TITLE_RE = /^\s*sugerencias de consultas adicionales\s*:?\s*$/i;
const FOLLOWUP_NUMBERED_QUERY_RE = /^\s*6\.(?:1|2)(?:\.\d+)*\s+(.+)$/;

interface ParsedNumberedLine {
  depth: number;
  numbering: string;
  title: string;
  top: string;
}

interface ParsedLine {
  original: string;
  trimmed: string;
  blank: boolean;
  bulletContent?: string;
  bulletLeadingSpaces?: number;
  numbered?: ParsedNumberedLine;
}

function parseNumberedLine(value: string): ParsedNumberedLine | null {
  const headingMatch = /^#{1,6}\s+(.+)$/.exec(value.trim());
  const candidate = String(headingMatch ? headingMatch[1] : value).trim();
  const numberedMatch = /^(\d+(?:\.\d+)*)[\)\.]?\s+(.+)$/.exec(candidate);
  if (!numberedMatch) {
    return null;
  }

  const numbering = numberedMatch[1];
  const title = numberedMatch[2].trim();
  const segments = numbering.split(".");
  return {
    numbering,
    title,
    depth: segments.length,
    top: segments[0],
  };
}

function parseStructuredLine(line: string): ParsedLine {
  const original = String(line || "");
  const trimmed = original.trim();
  if (!trimmed) {
    return { original, trimmed, blank: true };
  }

  const bulletMatch = /^(\s*)[*+-]\s+(.+)$/.exec(original);
  if (bulletMatch) {
    return {
      original,
      trimmed,
      blank: false,
      bulletLeadingSpaces: bulletMatch[1].length,
      bulletContent: bulletMatch[2].trim(),
    };
  }

  return {
    original,
    trimmed,
    blank: false,
    numbered: parseNumberedLine(original),
  };
}

function hasExplicitInlineFormatting(value: string): boolean {
  return /(\*\*|__|<\/?(?:u|strong|b|em|i)>)/i.test(value);
}

/**
 * Detect group-header bullets: a label ending with ":" and NO body text.
 * e.g. "Información de Terceros:" → true
 *      "Exógena: Cruce de la información…" → false
 */
function isGroupHeaderBullet(content: string): boolean {
  const stripped = content.replace(/\*\*|__|<\/?(?:u|strong|b|em|i)>/gi, "").trim();
  return /^[^:]+:\s*$/.test(stripped);
}

function normalizeStructuredItemContent(
  value: string,
  {
    underlineLabel = false,
    headingLike = false,
  }: {
    underlineLabel?: boolean;
    headingLike?: boolean;
  } = {},
): string {
  const trimmed = String(value || "").trim();
  if (!trimmed) return "";
  if (hasExplicitInlineFormatting(trimmed)) return trimmed;

  const colonIndex = trimmed.indexOf(":");
  if (colonIndex > 0) {
    const label = trimmed.slice(0, colonIndex).trim();
    const body = trimmed.slice(colonIndex + 1).trim();
    if (!label) return trimmed;
    const labelMarkdown = underlineLabel ? `**<u>${label}:</u>**` : `**${label}:**`;
    return body ? `${labelMarkdown} ${body}` : labelMarkdown;
  }

  if (!headingLike) {
    return trimmed;
  }

  const normalizedLabel = trimmed.replace(/[.:]+$/, "").trim() || trimmed;
  const suffix = /[!?]$/.test(trimmed) ? "" : ":";
  return underlineLabel ? `**<u>${normalizedLabel}${suffix}</u>**` : `**${normalizedLabel}${suffix}**`;
}

function indentationForListDepth(depth: number): string {
  return "   ".repeat(Math.max(0, Math.min(depth, 4) - 1));
}

function mapBulletDepth(leadingSpaces: number): number {
  if (leadingSpaces === 0) return 1;
  if (leadingSpaces <= 2) return 2;
  if (leadingSpaces <= 4) return 3;
  return 4;
}

function resolveBulletDepth(
  leadingSpaces: number,
  {
    insideNumberedSection,
    activeListDepth,
  }: {
    insideNumberedSection: boolean;
    activeListDepth: number;
  }
): number {
  if (!insideNumberedSection) {
    return mapBulletDepth(leadingSpaces);
  }

  // The first bullet under `1.` is often indented just to satisfy markdown nesting,
  // so normalize that to the first nested level instead of treating it as deeper content.
  if (activeListDepth <= 1 && leadingSpaces <= 4) {
    return 2;
  }

  return Math.min(4, mapBulletDepth(leadingSpaces) + 1);
}

function hasNestedStructuredContent(lines: ParsedLine[], startIndex: number): boolean {
  const current = lines[startIndex]?.numbered;
  if (!current) return false;

  for (let index = startIndex + 1; index < lines.length; index += 1) {
    const next = lines[index];
    if (!next || next.blank) continue;
    if (next.bulletContent) return true;
    if (!next.numbered) return false;
    if (next.numbered.top !== current.top) return false;
    if (next.numbered.depth <= current.depth) return false;
    return next.numbered.numbering.startsWith(`${current.numbering}.`);
  }

  return false;
}

function formatKernelHierarchyPlainMarkdown(text: string): string {
  const raw = String(text || "");
  if (!raw) return "";

  const lines = raw.split(/\r?\n/).map(parseStructuredLine);
  const formatted: string[] = [];
  let activeTop = "";
  let activeListDepth = 0;
  let groupHeaderDepth = 0;
  let groupHeaderBaseSpaces = -1;

  lines.forEach((line, index) => {
    if (line.blank) {
      if (formatted.length > 0 && formatted[formatted.length - 1] !== "") {
        formatted.push("");
      }
      groupHeaderDepth = 0;
      groupHeaderBaseSpaces = -1;
      return;
    }

    if (line.bulletContent) {
      const rawSpaces = line.bulletLeadingSpaces || 0;
      const depth = resolveBulletDepth(rawSpaces, {
        insideNumberedSection: Boolean(activeTop),
        activeListDepth,
      });

      // Reset group if we moved above the group header level
      if (groupHeaderDepth > 0 && rawSpaces < groupHeaderBaseSpaces) {
        groupHeaderDepth = 0;
        groupHeaderBaseSpaces = -1;
      }

      if (isGroupHeaderBullet(line.bulletContent)) {
        // New or replacement group header at same/higher level
        if (rawSpaces <= groupHeaderBaseSpaces || groupHeaderDepth === 0) {
          groupHeaderDepth = depth;
          groupHeaderBaseSpaces = rawSpaces;
        }
        const content = normalizeStructuredItemContent(line.bulletContent, { headingLike: true });
        formatted.push(`${indentationForListDepth(depth)}* ${content}`);
        activeListDepth = depth;
      } else if (groupHeaderDepth > 0 && rawSpaces === groupHeaderBaseSpaces) {
        // Same raw indentation as group header → nest as child
        const childDepth = Math.min(4, groupHeaderDepth + 1);
        const content = normalizeStructuredItemContent(line.bulletContent);
        formatted.push(`${indentationForListDepth(childDepth)}* ${content}`);
        activeListDepth = childDepth;
      } else {
        const content = normalizeStructuredItemContent(line.bulletContent);
        formatted.push(`${indentationForListDepth(depth)}* ${content}`);
        activeListDepth = depth;
      }
      return;
    }

    if (!line.numbered) {
      if (activeListDepth > 0) {
        formatted.push(`${indentationForListDepth(activeListDepth)}${line.trimmed}`);
      } else {
        formatted.push(line.original);
      }
      return;
    }

    const { depth, title, top } = line.numbered;

    if (depth === 1) {
      if (formatted.length > 0 && formatted[formatted.length - 1] !== "") {
        formatted.push("");
      }
      formatted.push(`${top}. ${normalizeStructuredItemContent(title, { underlineLabel: true, headingLike: true })}`);
      activeTop = top;
      activeListDepth = 1;
      groupHeaderDepth = 0;
      groupHeaderBaseSpaces = -1;
      return;
    }

    if (!activeTop || activeTop !== top) {
      formatted.push(line.original);
      activeTop = "";
      activeListDepth = 0;
      groupHeaderDepth = 0;
      groupHeaderBaseSpaces = -1;
      return;
    }

    const bulletDepth = Math.min(depth, 4);
    const content = normalizeStructuredItemContent(title, {
      headingLike: hasNestedStructuredContent(lines, index),
    });
    formatted.push(`${indentationForListDepth(bulletDepth)}* ${content}`);
    activeListDepth = bulletDepth;
  });

  return formatted.join("\n").replace(/\n{3,}/g, "\n\n");
}

export function applyKernelHierarchyFormattingMarkdown(text: string): string {
  const raw = String(text || "");
  if (!raw) return "";
  if (!raw.includes("```")) return formatKernelHierarchyPlainMarkdown(raw);

  const segments = raw.split(/(```[\s\S]*?```)/g);
  return segments
    .map((segment) => (segment.startsWith("```") ? segment : formatKernelHierarchyPlainMarkdown(segment)))
    .join("")
    .replace(/\n{3,}/g, "\n\n");
}

export function stripInlineEvidenceAnnotations(text: string): string {
  const source = String(text || "");
  if (!source) return "";

  let output = "";

  for (let index = 0; index < source.length; index += 1) {
    const remainder = source.slice(index);
    const lowerRemainder = remainder.toLowerCase();
    if (!lowerRemainder.startsWith("[evidencia:") && !lowerRemainder.startsWith("[evidence:")) {
      output += source[index];
      continue;
    }

    while (output.endsWith(" ") || output.endsWith("\t")) {
      output = output.slice(0, -1);
    }

    let depth = 0;
    let cursor = index;
    while (cursor < source.length) {
      const char = source[cursor];
      if (char === "[") depth += 1;
      if (char === "]") {
        depth -= 1;
        if (depth <= 0) {
          cursor += 1;
          break;
        }
      }
      cursor += 1;
    }

    index = Math.max(index, cursor - 1);
  }

  return output
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .replace(/\s+([,.;:!?])/g, "$1")
    .trim();
}

export function splitAnswerFromFollowupSection(text: string): { answer: string; followupQueries: string[] } {
  const source = String(text || "");
  if (!source) {
    return { answer: "", followupQueries: [] };
  }

  const lines = source.split(/\r?\n/);
  for (let index = 0; index < lines.length; index += 1) {
    if (!FOLLOWUP_SECTION_TITLE_RE.test(String(lines[index] || "").trim())) continue;

    const queries: string[] = [];
    let hasVisibleTrailingContent = false;
    for (let cursor = index + 1; cursor < lines.length; cursor += 1) {
      const line = String(lines[cursor] || "");
      const trimmed = line.trim();
      if (!trimmed) continue;
      const match = FOLLOWUP_NUMBERED_QUERY_RE.exec(trimmed);
      if (!match) {
        hasVisibleTrailingContent = true;
        break;
      }
      const query = String(match[1] || "").replace(/\s+/g, " ").trim();
      if (query) queries.push(query);
    }

    if (queries.length === 0 || hasVisibleTrailingContent) {
      continue;
    }

    return {
      answer: lines
        .slice(0, index)
        .join("\n")
        .replace(/\n{3,}/g, "\n\n")
        .trim(),
      followupQueries: queries,
    };
  }

  return { answer: source.trim(), followupQueries: [] };
}
