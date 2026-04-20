// @ts-nocheck

/**
 * Enhanced article reader modal for corpus documents across knowledge classes.
 * Shows a category badge (Normativa / Practica / Expertos) and renders
 * markdown content fetched from /source-download.
 */

import { renderMarkdown } from "@/content/markdown";
import { icons } from "@/shared/ui/icons";
import { isMobile } from "@/app/mobile/detectMobile";
import { isTechnicalLabel } from "@/shared/utils/documentIdentifierDetection";
import {
  SPANISH_SMALL_WORDS,
  titleCaseHeadings,
} from "@/shared/utils/spanishTextFormatters";

// ── Category config ─────────────────────────────────────────

interface CategoryMeta {
  label: string;
  cssClass: string;
}

const CATEGORY_MAP: Record<string, CategoryMeta> = {
  normative_base:            { label: "Normativa",  cssClass: "article-reader-badge--normativa" },
  practica_erp:              { label: "Practica",   cssClass: "article-reader-badge--practica" },
  interpretative_guidance:   { label: "Expertos",   cssClass: "article-reader-badge--expertos" },
};

function categoryFor(knowledgeClass: string): CategoryMeta {
  return CATEGORY_MAP[knowledgeClass] || CATEGORY_MAP.normative_base;
}

// ── DOM (lazy singleton) ────────────────────────────────────

let overlay: HTMLDivElement | null = null;
let badgeNode: HTMLSpanElement | null = null;
let titleNode: HTMLHeadingElement | null = null;
let bodyNode: HTMLDivElement | null = null;
let statusNode: HTMLDivElement | null = null;

function ensureDOM(): {
  overlay: HTMLDivElement;
  badgeNode: HTMLSpanElement;
  titleNode: HTMLHeadingElement;
  bodyNode: HTMLDivElement;
  statusNode: HTMLDivElement;
} {
  if (overlay) return { overlay, badgeNode: badgeNode!, titleNode: titleNode!, bodyNode: bodyNode!, statusNode: statusNode! };

  overlay = document.createElement("div");
  overlay.className = "article-reader-overlay";
  overlay.hidden = true;

  const modal = document.createElement("div");
  modal.className = "article-reader-modal";

  const header = document.createElement("div");
  header.className = "article-reader-header";

  const headerLeft = document.createElement("div");
  headerLeft.className = "article-reader-header-left";

  badgeNode = document.createElement("span");
  badgeNode.className = "article-reader-badge";

  titleNode = document.createElement("h2");
  titleNode.className = "article-reader-title";

  headerLeft.appendChild(badgeNode);
  headerLeft.appendChild(titleNode);

  const closeBtn = document.createElement("button");
  closeBtn.className = "article-reader-close";
  closeBtn.innerHTML = icons.close;
  closeBtn.setAttribute("aria-label", "Cerrar");
  closeBtn.addEventListener("click", closeArticleReader);

  header.appendChild(headerLeft);
  header.appendChild(closeBtn);

  statusNode = document.createElement("div");
  statusNode.className = "article-reader-status";
  statusNode.hidden = true;

  bodyNode = document.createElement("div");
  bodyNode.className = "article-reader-body markdown-content";

  modal.appendChild(header);
  modal.appendChild(statusNode);
  modal.appendChild(bodyNode);
  overlay.appendChild(modal);

  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) closeArticleReader();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && overlay && !overlay.hidden) {
      e.stopImmediatePropagation();
      closeArticleReader();
    }
  });

  document.body.appendChild(overlay);
  return { overlay, badgeNode, titleNode, bodyNode, statusNode };
}

// ── Mobile bottom sheet helper ──────────────────────────────

let _mobileSheet: { open(opts: { title: string; subtitle?: string; html: string }): void } | null = null;

export function setMobileSheet(sheet: typeof _mobileSheet): void {
  _mobileSheet = sheet;
}

// ── Title cleaning ────────────────────────────────────────

// isTechnicalLabel now lives in shared/utils/documentIdentifierDetection.ts.

// spanishTitleCase / titleCaseHeadings / SPANISH_SMALL_WORDS live in
// shared/utils/spanishTextFormatters.ts. humanizeTechnicalLabel stays
// here — it mixes regex stripping specific to the article reader with
// a title-case pass that uses the shared small-words set.

/**
 * Clean a technical filename-style label into a human-readable title.
 * Strips hex hashes, "part N" suffixes, corpus-type prefixes, and title-cases.
 */
function humanizeTechnicalLabel(value: string): string {
  let clean = value;
  // Strip hex hashes
  clean = clean.replace(/\b[0-9a-f]{8}\b/g, "");
  // Strip "part N" / "parte N/M"
  clean = clean.replace(/\bpart[_\s-]?\d+\b/gi, "");
  clean = clean.replace(/\(?\bparte\s+\d+(?:\/\d+)?\)?/gi, "");
  // Clean separators before prefix stripping
  clean = clean.replace(/[_-]/g, " ").replace(/\s+/g, " ").trim();
  // Strip technical prefix tokens iteratively from the left
  const prefixRe = /^(?:t|pt|n|e|ref|san|dat|niif|pen|cam|eme|rut|normativa|expertos|addendum|[a-z]\d{2}|ingest|corpus)(?:\s|$)/i;
  for (let i = 0; i < 6; i++) {
    const m = prefixRe.exec(clean);
    if (!m) break;
    clean = clean.slice(m[0].length).trim();
  }
  if (!clean) return "";
  return clean
    .split(" ")
    .map((w, i) =>
      i === 0 || !SPANISH_SMALL_WORDS.has(w.toLowerCase())
        ? w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()
        : w.toLowerCase(),
    )
    .join(" ");
}

/**
 * Extract a human-readable title from the fetched markdown.
 * Looks for "Tema principal" metadata, "Tema:" blockquote metadata,
 * or the first real heading.
 */
function extractTitleFromMarkdown(markdown: string): string {
  // Try "**Tema principal**: ..." pattern
  const temaMatch = /\*\*Tema principal\*\*\s*:\s*(.+)/i.exec(markdown);
  if (temaMatch) {
    const tema = temaMatch[1].trim().replace(/\*\*/g, "");
    if (tema.length > 8) return tema.length > 120 ? `${tema.slice(0, 117)}…` : tema;
  }
  // Try blockquote "**Tema:** ..." pattern
  const blockquoteTema = />\s*\*\*Tema(?:\s*principal)?\*?\*?\s*:\*?\*?\s*(.+)/i.exec(markdown);
  if (blockquoteTema) {
    const tema = blockquoteTema[1].trim().replace(/\*\*/g, "");
    if (tema.length > 8) return tema.length > 120 ? `${tema.slice(0, 117)}…` : tema;
  }
  // Try first content heading (skip "Ingesta RAG", "Identificacion", scaffolding)
  const headings = markdown.match(/^#{1,3}\s+(.+)$/gm) || [];
  for (const heading of headings) {
    const text = heading.replace(/^#{1,6}\s+/, "").trim();
    if (/ingesta rag|identificaci[oó]n/i.test(text)) continue;
    if (/texto base referenciado/i.test(text)) continue;
    if (text.length > 8) return text.length > 120 ? `${text.slice(0, 117)}…` : text;
  }
  return "";
}

// ── Public API ──────────────────────────────────────────────

export function closeArticleReader(): void {
  if (overlay) overlay.hidden = true;
}

export async function openArticleReader(
  docId: string,
  label: string,
  knowledgeClass: string,
): Promise<void> {
  const category = categoryFor(knowledgeClass);
  const initialTitle = isTechnicalLabel(label)
    ? (humanizeTechnicalLabel(label) || category.label)
    : label;

  // Mobile: delegate to bottom sheet
  if (isMobile() && _mobileSheet) {
    _mobileSheet.open({
      title: initialTitle,
      subtitle: category.label,
      html: `<div class="article-reader-status">Cargando documento\u2026</div>`,
    });
    try {
      const url = `/source-download?doc_id=${encodeURIComponent(docId)}&view=original&format=md`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const markdown = await res.text();
      const betterTitle = isTechnicalLabel(label) ? (extractTitleFromMarkdown(markdown) || initialTitle) : label;
      const tmp = document.createElement("div");
      tmp.className = "article-reader-body markdown-content";
      await renderMarkdown(tmp, titleCaseHeadings(markdown), { animate: false });
      _mobileSheet.open({ title: betterTitle, subtitle: category.label, html: tmp.outerHTML });
    } catch {
      _mobileSheet.open({
        title: initialTitle,
        subtitle: category.label,
        html: `<div class="article-reader-status">No se pudo cargar el documento.</div>`,
      });
    }
    return;
  }

  // Desktop: overlay modal
  const dom = ensureDOM();
  dom.badgeNode.textContent = category.label;
  dom.badgeNode.className = `article-reader-badge ${category.cssClass}`;
  dom.titleNode.textContent = initialTitle;
  dom.bodyNode.innerHTML = "";
  dom.statusNode.textContent = "Cargando documento\u2026";
  dom.statusNode.hidden = false;
  dom.overlay.hidden = false;

  try {
    const url = `/source-download?doc_id=${encodeURIComponent(docId)}&view=original&format=md`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const markdown = await res.text();
    // Update title from markdown content if the label was technical
    if (isTechnicalLabel(label)) {
      const betterTitle = extractTitleFromMarkdown(markdown);
      if (betterTitle) dom.titleNode.textContent = betterTitle;
    }
    dom.statusNode.hidden = true;
    await renderMarkdown(dom.bodyNode, titleCaseHeadings(markdown), { animate: false });
  } catch {
    dom.statusNode.textContent = "No se pudo cargar el documento.";
  }
}
