/**
 * User-facing Spanish labels for the `authority` taxonomy that
 * `ingest_classifiers.py` writes on each ingested document.
 *
 * The raw enum keys (`secondary_official_authority`, etc.) are
 * internal — they are ranking/filtering signals, never meant to leak
 * into the UI. They previously did, mangled into one-word pills like
 * `secondaryofficialauthority` because `normalizeText` runs through
 * `stripMarkdown` which interprets `_x_` as Markdown italic and strips
 * the underscores.
 */

const AUTHORITY_LABELS: Record<string, string> = {
  primary_legal_authority: "Norma vinculante",
  secondary_official_authority: "Fuente oficial secundaria",
  expert_interpretive_authority: "Interpretación profesional",
  operational_practice_authority: "Guía operativa",
};

export function labelAuthority(authority: string | null | undefined): string {
  const raw = String(authority || "").trim().toLowerCase();
  if (!raw) return "";
  // Unmapped values (`not_applicable`, `*_unknown`, future additions)
  // collapse to empty so the chip is suppressed at the call site
  // rather than leaking another raw enum.
  return AUTHORITY_LABELS[raw] || "";
}
