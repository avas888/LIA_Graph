import type { I18nRuntime } from "@/shared/i18n";

export function formatDurationSeconds(ms: number, i18n: I18nRuntime): string {
  if (!Number.isFinite(ms)) return "-";
  return `${i18n.formatNumber(ms / 1000, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })} s`;
}

export function safeText(value: unknown, fallback = ""): string {
  return String(value ?? fallback);
}

const INVISIBLE_TEXT_CHARS_RE = /[\u200B-\u200D\u2060\uFEFF]/g;

export function visibleText(value: unknown): string {
  return safeText(value).replace(INVISIBLE_TEXT_CHARS_RE, "").trim();
}

function matchReplacementCase(source: string, replacement: string): string {
  if (source.toUpperCase() === source) return replacement.toUpperCase();
  if (source.toLowerCase() === source) return replacement.toLowerCase();
  if (source[0]?.toUpperCase() === source[0] && source.slice(1).toLowerCase() === source.slice(1)) {
    return replacement[0]?.toUpperCase() + replacement.slice(1);
  }
  return replacement;
}

const SPANISH_PUBLISHED_TEXT_REPLACEMENTS: Array<[RegExp, string]> = [
  [/\bano\b/gi, "año"],
  [/\bseccion\b/gi, "sección"],
  [/\bpagina\b/gi, "página"],
  [/\binstruccion\b/gi, "instrucción"],
  [/\bverificacion\b/gi, "verificación"],
  [/\bespecifico\b/gi, "específico"],
  [/\bguia\b/gi, "guía"],
  [/\bgrafica\b/gi, "gráfica"],
  [/\bjuridica\b/gi, "jurídica"],
  [/\bregimen\b/gi, "régimen"],
  [/\beconomica\b/gi, "económica"],
  [/\bdeclaracion\b/gi, "declaración"],
  [/\binformacion\b/gi, "información"],
  [/\bdigito\b/gi, "dígito"],
  [/\bpodra\b/gi, "podrá"],
  [/\btecnica\b/gi, "técnica"],
  [/\boperacion\b/gi, "operación"],
  [/\boperaciones\b/gi, "operaciones"],
];

/** Strip common markdown inline formatting so corpus text renders as plain text. */
export function stripMarkdown(text: string): string {
  return text
    .replace(/\*\*(.+?)\*\*/g, "$1")
    .replace(/__(.+?)__/g, "$1")
    .replace(/\*(.+?)\*/g, "$1")
    .replace(/_(.+?)_/g, "$1")
    .replace(/^#{1,6}\s+/gm, "")
    .replace(/`([^`]+)`/g, "$1");
}

export function publishedSpanishText(value: unknown): string {
  let result = String(value ?? "");
  for (const [pattern, replacement] of SPANISH_PUBLISHED_TEXT_REPLACEMENTS) {
    result = result.replace(pattern, (match) => matchReplacementCase(match, replacement));
  }
  return result;
}
