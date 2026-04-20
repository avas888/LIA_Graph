/**
 * Pure regex helpers for extracting a four-digit issuance year from
 * citation metadata. Single concern per function — the citation-specific
 * composer that decides *where* to look (reference_key vs title vs
 * legal_reference) stays in the citation renderer.
 *
 * Years before 1900 are rejected as a defensive guard against stray
 * numbers (e.g. "Ley 100 de 100 días…").
 */

const MIN_VALID_YEAR = 1900;

function validYear(match: RegExpExecArray | null): number {
  if (!match) return 0;
  const year = Number.parseInt(match[1], 10);
  return Number.isFinite(year) && year >= MIN_VALID_YEAR ? year : 0;
}

/**
 * Parses a year from structured `reference_key` values like
 * `resolucion_dian:162:2023`, `ley:1819:2016`, `decreto:1070:2013`.
 * Returns 0 when no year is present (e.g. bare `et`).
 */
export function extractYearFromReferenceKey(referenceKey: string): number {
  const clean = String(referenceKey || "").trim();
  if (!clean) return 0;
  return validYear(/:(\d{4})(?::|$)/.exec(clean));
}

/**
 * Parses a year from human text like "Resolución 233 de 2025" or
 * "Decreto 1625 de 2016". Returns 0 when no "de YYYY" pattern matches.
 */
export function extractYearFromText(text: string): number {
  const clean = String(text || "").trim();
  if (!clean) return 0;
  return validYear(/\bde\s+(\d{4})\b/i.exec(clean));
}
