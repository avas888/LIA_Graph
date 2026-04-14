// @ts-nocheck

/**
 * Pure parsing and text-formatting functions for normative citations.
 * Extracted from normativeModals.ts during decouple-v1 Phase 3.
 */

import type { ParsedEtLocator } from "@/features/chat/normative/types";

// ── Constants ─────────────────────────────────────────────────

const FORM_TITLE_SMALL_WORDS = new Set([
  "a", "al", "con", "contra", "de", "del", "desde", "e", "el", "en",
  "la", "las", "los", "o", "para", "por", "sin", "u", "un", "una", "y",
]);

const ET_ARTICLE_TOKEN_RE = /^\d+(?:-\d+)*(?:-[a-z])?$/i;
const ET_ARTICLE_RANGE_CONNECTOR_RE = /\s+(?:-|–|—)\s+|\s+(?:a|al|hasta)\s+/i;
const ET_ARTICLE_LIST_CONNECTOR_RE = /\s*(?:,|;|\by\b|\be\b|\bo\b|\bu\b)\s*/i;

// ── Href sanitization ─────────────────────────────────────────

export function sanitizeHref(raw: unknown): string {
  const value = String(raw || "").trim();
  if (!value) return "";
  if (value.startsWith("/")) return value;
  if (/^https?:\/\//i.test(value)) return value;
  if (/^mailto:/i.test(value)) return value;
  if (/^tel:/i.test(value)) return value;
  return "";
}

export function openLinkInNewTab(url: unknown): void {
  const href = sanitizeHref(url);
  if (!href) return;
  window.open(href, "_blank", "noopener,noreferrer");
}

// ── Text normalization ────────────────────────────────────────

export function normalizeNormaBulletText(value: unknown): string {
  const clean = String(value || "")
    .replace(/\s+/g, " ")
    .replace(/^[•\-–—]\s*/, "")
    .trim();
  if (!clean) return "";
  return /[.!?]$/.test(clean) ? clean : `${clean}.`;
}

export function splitNormaTextItems(text: unknown): string[] {
  const raw = String(text || "").replace(/\r\n/g, "\n").trim();
  if (!raw) return [];

  const explicitLines = raw
    .split(/\n+/)
    .map((item) => normalizeNormaBulletText(item))
    .filter(Boolean);
  if (explicitLines.length > 1) return explicitLines;

  // Metadata-style fields separated by " > " (e.g. "**Serie:** … > **Parte:** …")
  if (/\s>\s/.test(raw) && /\*\*\w[^*]*\*\*/.test(raw)) {
    const fieldParts = raw
      .split(/\s*>\s*/)
      .map((item) => normalizeNormaBulletText(item))
      .filter(Boolean);
    if (fieldParts.length > 1) return fieldParts;
  }

  const semicolonParts = raw
    .split(/\s*;\s+/)
    .map((item) => normalizeNormaBulletText(item))
    .filter(Boolean);
  if (semicolonParts.length > 1) return semicolonParts;

  const sentenceParts = raw
    .split(/(?<=[.!?])\s+/)
    .map((item) => normalizeNormaBulletText(item))
    .filter(Boolean);
  if (sentenceParts.length > 1) return sentenceParts;

  return [normalizeNormaBulletText(raw)];
}

export function shouldForceNormaBullets(label: unknown): boolean {
  const clean = String(label || "").trim();
  return (
    clean === "Para qué sirve" ||
    clean === "Desde cuándo es obligatorio" ||
    clean === "Última actualización identificada" ||
    clean === "Normas base" ||
    /ámbito de aplicación/i.test(clean) ||
    /impacta la labor contable/i.test(clean) ||
    /impacto para la profesión contable/i.test(clean) ||
    /implicación práctica para contadores/i.test(clean) ||
    /impacto contable\/procedimental/i.test(clean)
  );
}

function appendInlineBold(el: HTMLElement, text: string): void {
  const BOLD_RE = /\*\*([^*]+)\*\*/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  let hasBold = false;
  while ((match = BOLD_RE.exec(text)) !== null) {
    hasBold = true;
    if (match.index > lastIndex) {
      el.appendChild(document.createTextNode(text.slice(lastIndex, match.index)));
    }
    const strong = document.createElement("strong");
    strong.textContent = match[1];
    el.appendChild(strong);
    lastIndex = BOLD_RE.lastIndex;
  }
  if (!hasBold) {
    el.textContent = text;
    return;
  }
  if (lastIndex < text.length) {
    el.appendChild(document.createTextNode(text.slice(lastIndex)));
  }
}

export function appendNormaTextContent(container: HTMLElement, text: unknown, label: unknown): void {
  const items = splitNormaTextItems(text);
  if (items.length === 0) {
    container.textContent = "";
    return;
  }

  const forceBullets = shouldForceNormaBullets(label);
  if (forceBullets || items.length > 1) {
    const list = document.createElement("ul");
    list.className = "norma-bullet-list";
    items.forEach((item) => {
      const bullet = document.createElement("li");
      appendInlineBold(bullet, item);
      list.appendChild(bullet);
    });
    container.appendChild(list);
    return;
  }

  const paragraph = document.createElement("p");
  paragraph.className = "norma-text-block";
  appendInlineBold(paragraph, items[0]);
  container.appendChild(paragraph);
}

export function boldifyFormularioReferences(container: HTMLElement): void {
  const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT, null);
  const pattern = /((?:Formulario|Formato)\s+\d{2,6})/gi;
  const textNodes: Text[] = [];

  while (walker.nextNode()) {
    const node = walker.currentNode as Text;
    if (node.parentElement?.tagName === "STRONG") continue;
    pattern.lastIndex = 0;
    if (pattern.test(node.nodeValue || "")) {
      textNodes.push(node);
    }
  }

  textNodes.forEach((node) => {
    const text = node.nodeValue || "";
    const fragment = document.createDocumentFragment();
    let lastIndex = 0;
    let match: RegExpExecArray | null;
    pattern.lastIndex = 0;

    while ((match = pattern.exec(text)) !== null) {
      if (match.index > lastIndex) {
        fragment.appendChild(document.createTextNode(text.slice(lastIndex, match.index)));
      }
      const strong = document.createElement("strong");
      strong.textContent = match[1];
      fragment.appendChild(strong);
      lastIndex = pattern.lastIndex;
    }

    if (lastIndex < text.length) {
      fragment.appendChild(document.createTextNode(text.slice(lastIndex)));
    }

    node.parentNode?.replaceChild(fragment, node);
  });
}

export function isRenderableEvidenceStatus(value: unknown): boolean {
  const status = String(value || "").trim();
  return !status || status === "verified" || status === "missing";
}

// ── ET locator parsing ────────────────────────────────────────

export function canonicalizeEtArticleToken(value: unknown): string {
  let clean = String(value || "")
    .trim()
    .replace(/\s+/g, "")
    .replace(/[–—]/g, "-");
  if (!clean) return "";
  if (/^\d+(?:\.\d+)+$/i.test(clean)) {
    clean = clean.replace(/\./g, "-");
  }
  clean = clean.replace(/^(\d+(?:-\d+)*)[.-]([a-z])$/i, (_match, base, suffix) => `${base}-${suffix.toLowerCase()}`);
  clean = clean.replace(/^(\d+(?:-\d+)*)([a-z])$/i, (_match, base, suffix) => `${base}-${suffix.toLowerCase()}`);
  return clean;
}

/**
 * Expand an article range like "20"→"25" into individual article numbers.
 * Returns null if the range is invalid or too large (>maxCount).
 * Handles simple integers (20→25) and compound sub-articles (335-1→335-5).
 */
export function expandArticleRange(startStr: string, endStr: string, maxCount = 30): string[] | null {
  const startInt = parseInt(startStr, 10);
  const endInt = parseInt(endStr, 10);

  if (String(startInt) === startStr && String(endInt) === endStr) {
    if (startInt > 0 && endInt > startInt && (endInt - startInt) < maxCount) {
      const result: string[] = [];
      for (let i = startInt; i <= endInt; i++) result.push(String(i));
      return result;
    }
    return null;
  }

  const csMatch = startStr.match(/^(\d+)-(\d+)$/);
  const ceMatch = endStr.match(/^(\d+)-(\d+)$/);
  if (csMatch && ceMatch && csMatch[1] === ceMatch[1]) {
    const base = csMatch[1];
    const subStart = parseInt(csMatch[2], 10);
    const subEnd = parseInt(ceMatch[2], 10);
    if (subEnd > subStart && (subEnd - subStart) < maxCount) {
      const result: string[] = [];
      for (let i = subStart; i <= subEnd; i++) result.push(`${base}-${i}`);
      return result;
    }
  }

  return null;
}

export function parseEtLocatorText(value: unknown): ParsedEtLocator | null {
  let clean = String(value || "")
    .replace(/\s+/g, " ")
    .replace(/[–—]/g, "-")
    .trim()
    .replace(/^art(?:[íi]culos?|s?)\.?\s*/i, "")
    .replace(/\s*(?:del?\s*)?(?:ET|estatuto tributario)\b.*$/i, "")
    .replace(/^[,:;\-.\s]+|[,:;\-.\s]+$/g, "")
    .trim();
  if (!clean) return null;

  const explicitRange = clean.split(ET_ARTICLE_RANGE_CONNECTOR_RE).map((item) => canonicalizeEtArticleToken(item));
  if (explicitRange.length === 2 && explicitRange.every((item) => ET_ARTICLE_TOKEN_RE.test(item))) {
    return { kind: "range", parts: explicitRange };
  }

  const listParts = clean.split(ET_ARTICLE_LIST_CONNECTOR_RE).map((item) => canonicalizeEtArticleToken(item));
  if (listParts.length > 1 && listParts.every((item) => ET_ARTICLE_TOKEN_RE.test(item))) {
    return { kind: "list", parts: listParts };
  }

  const single = canonicalizeEtArticleToken(clean);
  if (ET_ARTICLE_TOKEN_RE.test(single)) {
    return { kind: "single", parts: [single] };
  }
  return null;
}

export function formatParsedEtLocator(locator: ParsedEtLocator | null): string {
  if (!locator || locator.parts.length === 0) return "Estatuto Tributario";
  if (locator.kind === "single") {
    return `Estatuto Tributario, Artículo ${locator.parts[0]}`;
  }
  if (locator.kind === "range") {
    return `Estatuto Tributario, Artículos ${locator.parts[0]} - ${locator.parts[1]}`;
  }
  return `Estatuto Tributario, Artículos ${locator.parts.join(", ")}`;
}

export function parseEtTitle(rawTitle: unknown): string {
  const clean = String(rawTitle || "").replace(/\s+/g, " ").trim();
  if (!clean) return "";

  const headMatch = /^(?:estatuto tributario(?:\s*\(ET\))?|ET)\b\s*(?:,|:)?\s*(.*)$/i.exec(clean);
  if (headMatch) {
    const remainder = String(headMatch[1] || "").trim();
    if (!remainder) return "Estatuto Tributario";
    const locator = parseEtLocatorText(remainder);
    return formatParsedEtLocator(locator);
  }

  const tailMatch = /^(art(?:[íi]culos?|s?)\.?\s*.+?)\s*(?:del?\s*)?(?:ET|estatuto tributario)\b$/i.exec(clean);
  if (tailMatch) {
    return formatParsedEtLocator(parseEtLocatorText(tailMatch[1]));
  }
  return "";
}

export function toSpanishTitleCase(value: unknown): string {
  const clean = String(value || "").replace(/\s+/g, " ").trim().toLowerCase();
  if (!clean) return "";
  return clean.replace(/(^|[\s(])([\p{L}\d]+)/gu, (_match, prefix, word) => {
    if (prefix && FORM_TITLE_SMALL_WORDS.has(word)) {
      return `${prefix}${word}`;
    }
    return `${prefix}${word.charAt(0).toUpperCase()}${word.slice(1)}`;
  });
}
