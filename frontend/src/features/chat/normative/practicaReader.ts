// @ts-nocheck

/**
 * Lightweight reader modal for practica_erp documents.
 * Fetches markdown content and renders it using the same renderer as chat bubbles.
 */

import { renderMarkdown } from "@/content/markdown";

let overlay: HTMLDivElement | null = null;
let titleNode: HTMLHeadingElement | null = null;
let bodyNode: HTMLDivElement | null = null;
let statusNode: HTMLDivElement | null = null;

function ensureDOM(): { overlay: HTMLDivElement; titleNode: HTMLHeadingElement; bodyNode: HTMLDivElement; statusNode: HTMLDivElement } {
  if (overlay) return { overlay, titleNode: titleNode!, bodyNode: bodyNode!, statusNode: statusNode! };

  overlay = document.createElement("div");
  overlay.className = "practica-reader-overlay";
  overlay.hidden = true;

  const modal = document.createElement("div");
  modal.className = "practica-reader-modal";

  const header = document.createElement("div");
  header.className = "practica-reader-header";

  titleNode = document.createElement("h2");
  titleNode.className = "practica-reader-title";

  const closeBtn = document.createElement("button");
  closeBtn.className = "practica-reader-close";
  closeBtn.textContent = "✕";
  closeBtn.setAttribute("aria-label", "Cerrar");
  closeBtn.addEventListener("click", closePracticaReader);

  header.appendChild(titleNode);
  header.appendChild(closeBtn);

  statusNode = document.createElement("div");
  statusNode.className = "practica-reader-status";
  statusNode.hidden = true;

  bodyNode = document.createElement("div");
  bodyNode.className = "practica-reader-body markdown-content";

  modal.appendChild(header);
  modal.appendChild(statusNode);
  modal.appendChild(bodyNode);
  overlay.appendChild(modal);

  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) closePracticaReader();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && overlay && !overlay.hidden) {
      e.stopImmediatePropagation();
      closePracticaReader();
    }
  });

  document.body.appendChild(overlay);
  return { overlay, titleNode, bodyNode, statusNode };
}

export function closePracticaReader(): void {
  if (overlay) overlay.hidden = true;
}

export async function openPracticaReader(docId: string, label: string): Promise<void> {
  const dom = ensureDOM();
  dom.titleNode.textContent = label;
  dom.bodyNode.innerHTML = "";
  dom.statusNode.textContent = "Cargando documento…";
  dom.statusNode.hidden = false;
  dom.overlay.hidden = false;

  try {
    const url = `/source-download?doc_id=${encodeURIComponent(docId)}&view=normalized&format=md`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const markdown = await res.text();
    dom.statusNode.hidden = true;
    await renderMarkdown(dom.bodyNode, markdown, { animate: false });
  } catch {
    dom.statusNode.textContent = "No se pudo cargar el documento.";
  }
}
