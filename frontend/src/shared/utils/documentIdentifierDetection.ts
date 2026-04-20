/**
 * Detection helpers for values that are internal document identifiers
 * rather than human-readable labels. Unified from two near-duplicate
 * implementations (normativeModals.ts and normative/articleReader.ts) so
 * the heuristics evolve in one place.
 *
 * Contract:
 *  - `isTechnicalLabel(value)` — lenient check (≥12 chars) used when the
 *    caller already suspects a technical label and just wants to confirm
 *    before humanizing.
 *  - `isRawDocId(value)` — strict check (≥16 chars + additional doc-id
 *    heuristics) used to decide whether to *replace* a rendered label with
 *    a human-friendly fallback.
 */

const HEX_HASH_RE = /\b[0-9a-f]{8}\b/;
const PART_SUFFIX_RE = /\bpart[_\s-]?\d+\b/i;
const CLEAN_IDENTIFIER_RE = /^[a-z0-9_\-]+$/i;

export function isTechnicalLabel(value: string): boolean {
  if (!value || value.length < 12) return false;
  if (HEX_HASH_RE.test(value)) return true;
  if (PART_SUFFIX_RE.test(value)) return true;
  if (CLEAN_IDENTIFIER_RE.test(value) && value.length >= 16) return true;
  return false;
}

export function isRawDocId(value: unknown): boolean {
  const clean = String(value || "").trim();
  if (!clean || clean.length < 16) return false;
  const hasWhitespace = /\s/.test(clean);
  // Classic underscore-separated lowercase identifiers.
  if (!hasWhitespace && CLEAN_IDENTIFIER_RE.test(clean) && !/[A-Z]/.test(clean.slice(1))) {
    return true;
  }
  // Concatenated identifiers with :: section separators.
  if (/::/.test(clean)) return true;
  // Long strings without whitespace — almost certainly machine identifiers.
  if (clean.length > 40 && !hasWhitespace) return true;
  // Contains "ingest" substring — strong signal of internal doc_id.
  if (/ingest/i.test(clean) && !hasWhitespace) return true;
  // Names containing hex hashes.
  if (HEX_HASH_RE.test(clean)) return true;
  // Names with "part N" suffixes.
  if (PART_SUFFIX_RE.test(clean)) return true;
  return false;
}
