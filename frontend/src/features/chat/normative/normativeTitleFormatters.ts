/**
 * Per-kind title formatters for normative citations.
 *
 * Each formatter owns one regex + one output shape. Keep them additive and
 * side-effect free so `formatNormativeCitationTitle` can compose them as
 * an ordered ladder without repeating extraction/normalization logic.
 *
 * Contract: every formatter returns a user-ready string when it matches,
 * or `null` when the input is for a different document kind. `null` lets
 * the composer fall through to the next formatter.
 */

import { toSpanishTitleCase } from "@/features/chat/normative/citationParsing";

function normalizeRaw(raw: unknown): string {
  return String(raw || "")
    .replace(/\s+/g, " ")
    .trim();
}

function normalizeRemainder(raw: string | undefined): string {
  return String(raw || "")
    .trim()
    .replace(/^[:\-\u2013,\s]+/, "")
    .trim();
}

function buildNumberedLabel(prefix: string, number: string, year: string, remainder: string): string {
  const stem = `${prefix} ${number} de ${year}`;
  return remainder ? `${stem}: ${toSpanishTitleCase(remainder)}` : stem;
}

const LEY_RE = /^Ley\s+(\d+)\s+de\s+(\d{4})(.*)$/i;
const DECRETO_RE = /^Decreto\s+(\d+)\s+de\s+(\d{4})(.*)$/i;
const RESOLUCION_RE = /^Resoluci[oó]n\s+(\d+)\s+de\s+(\d{4})(.*)$/i;
const FORMULARIO_RE = /^(Formulario|Formato)\s+(\d{2,6})(.*)$/i;

export function formatLeyTitle(raw: unknown): string | null {
  const clean = normalizeRaw(raw);
  const match = LEY_RE.exec(clean);
  if (!match) return null;
  return buildNumberedLabel("Ley", match[1], match[2], normalizeRemainder(match[3]));
}

export function formatDecretoTitle(raw: unknown): string | null {
  const clean = normalizeRaw(raw);
  const match = DECRETO_RE.exec(clean);
  if (!match) return null;
  return buildNumberedLabel("Decreto", match[1], match[2], normalizeRemainder(match[3]));
}

export function formatResolucionTitle(raw: unknown): string | null {
  const clean = normalizeRaw(raw);
  const match = RESOLUCION_RE.exec(clean);
  if (!match) return null;
  return buildNumberedLabel("Resolución", match[1], match[2], normalizeRemainder(match[3]));
}

export function formatFormularioTitle(raw: unknown): string | null {
  const clean = normalizeRaw(raw);
  const match = FORMULARIO_RE.exec(clean);
  if (!match) return null;
  const kind = `${match[1].charAt(0).toUpperCase()}${match[1].slice(1).toLowerCase()}`;
  const number = match[2];
  const remainder = normalizeRemainder(match[3]);
  return remainder ? `${kind} ${number}: ${toSpanishTitleCase(remainder)}` : `${kind} ${number}`;
}
