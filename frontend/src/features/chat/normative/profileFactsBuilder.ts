/**
 * Pure data transform that builds the fact rows rendered in the normative
 * profile modal.
 *
 * Single concern: given a CitationProfileResponse, return the list of
 * {label, value} fact rows that the renderer should display. No DOM, no
 * i18n, no fetch — pure in, pure out. This lets the caller (desktop
 * renderer, mobile panel, tests) stay focused on rendering.
 *
 * Rules (kept in sync with the legacy inline version in profileRenderer):
 *   - ET articles with vigente text suppress the generic fact list; the
 *     original-text block carries the authority on its own.
 *   - A "Vigencia específica" row is appended (or replaces any prior
 *     "vigencia" row) when vigencia_detail is renderable and labelled.
 *   - The vigencia value defaults to `summary`; when absent it falls back
 *     to a newline-joined (label + basis + notes + última verificación).
 */

import type {
  CitationProfileFact,
  CitationProfileResponse,
} from "@/features/chat/normative/types";
import { isRenderableEvidenceStatus } from "@/features/chat/normative/citationParsing";

function buildVigenciaFact(
  vigencia: NonNullable<CitationProfileResponse["vigencia_detail"]>,
): CitationProfileFact | null {
  const label = String(vigencia.label || "").trim();
  if (!label) return null;
  if (!isRenderableEvidenceStatus(vigencia.evidence_status)) return null;
  const summary = String(vigencia.summary || "").trim();
  if (summary) return { label: "Vigencia específica", value: summary };

  const lastVerified = String(vigencia.last_verified_date || "").trim();
  const value = [
    label,
    String(vigencia.basis || "").trim(),
    String(vigencia.notes || "").trim(),
    lastVerified ? `Última verificación del corpus: ${lastVerified}` : "",
  ]
    .filter(Boolean)
    .join("\n");
  return { label: "Vigencia específica", value };
}

export function buildNormaFacts(profile: CitationProfileResponse): CitationProfileFact[] {
  const hideBaseFacts =
    String(profile?.document_family || "").trim() === "et_dur" &&
    Boolean(profile?.original_text);
  if (hideBaseFacts) return [];

  const rows: CitationProfileFact[] = Array.isArray(profile?.facts) ? [...profile.facts] : [];
  const vigenciaFact = profile?.vigencia_detail ? buildVigenciaFact(profile.vigencia_detail) : null;
  if (!vigenciaFact) return rows;

  const existingIdx = rows.findIndex((fact) => /vigencia/i.test(String(fact?.label || "")));
  if (existingIdx >= 0) {
    rows.splice(existingIdx, 1, vigenciaFact);
  } else {
    rows.push(vigenciaFact);
  }
  return rows;
}
