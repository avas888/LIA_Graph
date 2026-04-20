/**
 * Expert-panel text sanitizers and per-expert elevator-summary builder.
 *
 * These utilities isolate the "clean up corpus plumbing" concern so it
 * doesn't bloat `expertPanelController.ts`. The corpus occasionally leaks:
 *   - internal doc codes ("FIR-E01 — …", "PER-P02 — …") that identify the
 *     source file internally and mean nothing to an accountant,
 *   - a "Tema principal: X" metadata tail that is useful as a subtitle but
 *     not when smushed onto the main title line.
 *
 * `buildElevatorSummary` produces a 1–2 sentence per-snippet summary so
 * cards that share a group don't all echo the same template heading.
 */

import { stripMarkdown } from "@/shared/utils/format";

export interface ElevatorSnippetShape {
  snippet?: string;
  card_summary?: string;
  extended_excerpt?: string;
}

const METACOGNITIVE_RE = /(?:la fuente no proporciona|el texto fuente est[áa] vac[ií]o|no es posible generar|no proporciona texto|no contiene informaci[oó]n suficiente|incluya el texto|proporcione el texto|no se puede extraer|no hay contenido|la fuente est[áa] vac[ií]a)/i;

function normalize(value: string): string {
  return stripMarkdown(String(value || "")).replace(/\s+/g, " ").trim();
}

function isMetacognitive(text: string): boolean {
  return METACOGNITIVE_RE.test(text);
}

function ensureSentence(value: string): string {
  const cleaned = normalize(value);
  if (!cleaned) return "";
  return /[.!?…]$/.test(cleaned) ? cleaned : `${cleaned}.`;
}

function clip(value: string, maxChars: number): string {
  const cleaned = normalize(value);
  if (!cleaned || cleaned.length <= maxChars) return cleaned;
  return `${cleaned.slice(0, Math.max(0, maxChars - 1)).trimEnd()}…`;
}

// Prefix match anchored to start: "FIR-E01 — rest" → "rest".
const INTERNAL_DOC_CODE_PREFIX_RE = /^\s*[A-Z]{2,6}-?[A-Z]?\d{1,4}(?:-[A-Z]?\d{1,4})?\s*[—–-]\s*/;
// Inline match (after earlier concatenation): " PER-P02 — " between sentences.
const INTERNAL_DOC_CODE_INLINE_RE = /(?:^|[\s—–-])\s*[A-Z]{2,6}-?[A-Z]?\d{1,4}(?:-[A-Z]?\d{1,4})?\s*[—–-]\s*/;

export function stripInternalDocCode(value: string): string {
  if (!value) return "";
  let out = String(value).replace(INTERNAL_DOC_CODE_PREFIX_RE, "");
  out = out.replace(INTERNAL_DOC_CODE_INLINE_RE, " ");
  return out.replace(/\s+/g, " ").trim();
}

export function stripTemaPrincipalTail(value: string): string {
  if (!value) return "";
  return String(value)
    .replace(/\s*[,;:]?\s*Tema\s+principal\s*[:\-—]\s*.+?$/i, "")
    .replace(/\s+/g, " ")
    .trim();
}

export function sanitizeExpertText(value: string): string {
  return stripTemaPrincipalTail(stripInternalDocCode(normalize(value)));
}

/**
 * Splits "<title> Tema principal: <topic>" into two parts for the modal
 * header. When the tail isn't present, returns the sanitized title and an
 * empty topic so callers can render the fallback single-line heading.
 */
export function splitTitleAndTopic(value: string): { title: string; topic: string } {
  const raw = stripInternalDocCode(normalize(value));
  if (!raw) return { title: "", topic: "" };
  const m = raw.match(/^(.*?)\s*[,;:]?\s*Tema\s+principal\s*[:\-—]\s*(.+?)\s*[,.;]?\s*$/i);
  if (m) {
    return {
      title: m[1].replace(/[,;:]\s*$/g, "").trim(),
      topic: m[2].replace(/[,;.]\s*$/g, "").trim(),
    };
  }
  return { title: raw, topic: "" };
}

function splitSentences(value: string): string[] {
  if (!value) return [];
  const matches = value.match(/[^.!?…]+[.!?…]+/g);
  if (matches && matches.length > 0) return matches.map((s) => s.trim()).filter(Boolean);
  const trimmed = value.trim();
  return trimmed ? [trimmed] : [];
}

/**
 * Produces a 1–2 sentence elevator summary for a single expert snippet so
 * cards sharing a group don't all echo the same template heading. Draws
 * from `extended_excerpt`/`snippet` first (the authored body), falling back
 * to `card_summary` as a last resort.
 */
export function buildElevatorSummary(snippet: ElevatorSnippetShape, maxChars = 320): string {
  const candidates = [
    sanitizeExpertText(String(snippet.extended_excerpt || "")),
    sanitizeExpertText(String(snippet.snippet || "")),
    sanitizeExpertText(String(snippet.card_summary || "")),
  ].filter((value) => value && !isMetacognitive(value));
  for (const candidate of candidates) {
    const sentences = splitSentences(candidate).filter(
      (sentence) => sentence.length >= 24 && !isMetacognitive(sentence),
    );
    if (sentences.length === 0) continue;
    const chosen = sentences.slice(0, 2).join(" ").trim();
    if (chosen.length >= 24) {
      return clip(ensureSentence(chosen), maxChars);
    }
  }
  return "";
}
