// @ts-nocheck

/**
 * Linkable-list molecule — renders a `<ul>` where each `<li>` is either an
 * anchor (`<a target="_blank" rel="noopener noreferrer">`) when the source
 * item carries a valid href, or plain text otherwise.
 *
 * Created during granularize-v1 to make bullet references clickable inside
 * the normative article modal (Doctrina Concordante / Concordancias /
 * Notas de Vigencia tabs). The helper is framework-free and reusable by any
 * modal, sub-modal, or panel that receives a pre-parsed
 * `Array<{ text, href? }>` from the backend — see
 * `src/lia_graph/ui_article_annotations.py` for the canonical producer.
 *
 * Intentionally minimal: no icons, no badges, no tooltip chrome. Callers
 * pass a `className` so the molecule inherits the consumer's visual
 * language (e.g. `norma-annot-list`). Add new props here only when a
 * second consumer genuinely needs them.
 */

import { sanitizeHref } from "@/features/chat/normative/citationParsing";

export interface LinkableListItem {
  text?: string | null;
  href?: string | null;
}

export interface LinkableListOptions {
  className?: string;
  anchorClassName?: string;
  linkTarget?: "_blank" | "_self";
}

export function buildLinkableListNode(
  items: readonly (LinkableListItem | null | undefined)[] | null | undefined,
  options: LinkableListOptions = {},
): HTMLUListElement | null {
  const normalized = Array.isArray(items)
    ? items
        .map((raw) => ({
          text: String(raw?.text ?? "").trim(),
          href: sanitizeHref(raw?.href ?? ""),
        }))
        .filter((item) => item.text || item.href)
    : [];
  if (normalized.length === 0) return null;

  const list = document.createElement("ul");
  if (options.className) list.className = options.className;

  const target = options.linkTarget ?? "_blank";
  for (const item of normalized) {
    const li = document.createElement("li");
    if (item.href) {
      const anchor = document.createElement("a");
      anchor.href = item.href;
      if (target === "_blank") {
        anchor.target = "_blank";
        anchor.rel = "noopener noreferrer";
      }
      if (options.anchorClassName) anchor.className = options.anchorClassName;
      anchor.textContent = item.text || item.href;
      li.appendChild(anchor);
    } else {
      li.textContent = item.text;
    }
    list.appendChild(li);
  }
  return list;
}
