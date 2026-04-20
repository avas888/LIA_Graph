/**
 * Spanish text-formatting helpers.
 *
 * Single concern: apply Spanish capitalization conventions — capitalize
 * each word except small connectors (de, del, en, …), preserving
 * all-uppercase acronyms (DIAN, UVT, AG) and markdown emphasis markers.
 *
 * Extracted from `features/chat/normative/articleReader.ts` so the same
 * rules can be reused by other surfaces (practica reader, profile
 * renderer, mobile panel) without copy-paste drift.
 *
 * Note: `features/chat/normative/citationParsing.ts` ships a separate
 * `toSpanishTitleCase` with different semantics (lowercase-first, Unicode
 * word boundaries, no acronym preservation). It is intentionally kept
 * distinct — merging would break legacy citation rendering.
 */

export const SPANISH_SMALL_WORDS = new Set([
  "a",
  "al",
  "con",
  "de",
  "del",
  "desde",
  "e",
  "el",
  "en",
  "la",
  "las",
  "los",
  "o",
  "para",
  "por",
  "sin",
  "u",
  "un",
  "una",
  "y",
]);

function isAllUppercaseAcronym(word: string): boolean {
  return word.length >= 2 && word === word.toUpperCase() && /[A-Z]/.test(word);
}

function startsWithMarkdownEmphasis(word: string): boolean {
  return word.startsWith("**") || word.startsWith("__") || word.startsWith("*");
}

export function spanishTitleCase(text: string): string {
  return String(text ?? "")
    .split(" ")
    .map((word, index) => {
      if (!word) return word;
      if (isAllUppercaseAcronym(word)) return word;
      if (startsWithMarkdownEmphasis(word)) return word;
      if (index > 0 && SPANISH_SMALL_WORDS.has(word.toLowerCase())) {
        return word.toLowerCase();
      }
      return word.charAt(0).toUpperCase() + word.slice(1);
    })
    .join(" ");
}

/**
 * Title-cases H1–H3 headings in a markdown document, leaving body text
 * untouched.
 */
export function titleCaseHeadings(markdown: string): string {
  return String(markdown ?? "").replace(
    /^(#{1,3})\s+(.+)$/gm,
    (_, hashes: string, text: string) => `${hashes} ${spanishTitleCase(text)}`,
  );
}
