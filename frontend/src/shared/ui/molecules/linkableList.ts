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
  sub_items?: readonly (LinkableListItem | null | undefined)[] | null;
}

export interface LinkableListOptions {
  className?: string;
  anchorClassName?: string;
  linkTarget?: "_blank" | "_self";
  // When true, items whose `text` exceeds `longAnchorThreshold` render as
  // prose inside the `<li>` with a compact trailing source link, instead of
  // wrapping the entire paragraph in one `<a>`. Used by the article
  // annotation modal so Legislación Anterior blocks stay readable.
  splitLongAnchors?: boolean;
  longAnchorThreshold?: number;
  longAnchorLinkLabel?: string;
  longItemClassName?: string;
}

const DEFAULT_LONG_ANCHOR_THRESHOLD = 140;

export function buildLinkableListNode(
  items: readonly (LinkableListItem | null | undefined)[] | null | undefined,
  options: LinkableListOptions = {},
): HTMLUListElement | null {
  const normalized = Array.isArray(items)
    ? items
        .map((raw) => ({
          text: String(raw?.text ?? "").trim(),
          href: sanitizeHref(raw?.href ?? ""),
          subItems: Array.isArray(raw?.sub_items) ? raw!.sub_items! : null,
        }))
        .filter((item) => item.text || item.href)
    : [];
  if (normalized.length === 0) return null;

  const list = document.createElement("ul");
  if (options.className) list.className = options.className;

  const target = options.linkTarget ?? "_blank";
  const splitLong = options.splitLongAnchors === true;
  const longThreshold = options.longAnchorThreshold ?? DEFAULT_LONG_ANCHOR_THRESHOLD;
  const longLinkLabel = options.longAnchorLinkLabel ?? "Ver fuente";
  for (const item of normalized) {
    const li = document.createElement("li");
    const text = item.text;
    const hasLongText = splitLong && text.length > longThreshold;
    if (item.href && !hasLongText) {
      li.appendChild(buildAnchor(item.href, text || item.href, target, options.anchorClassName));
    } else if (item.href && hasLongText) {
      if (options.longItemClassName) li.className = options.longItemClassName;
      const prose = document.createElement("span");
      prose.className = "linkable-list__prose";
      prose.textContent = text;
      const sourceLink = buildAnchor(item.href, longLinkLabel, target, "linkable-list__source");
      li.append(prose, document.createTextNode(" "), sourceLink);
    } else {
      li.textContent = text;
    }
    if (item.subItems && item.subItems.length > 0) {
      const nested = buildLinkableListNode(item.subItems, {
        ...options,
        className: "linkable-list__nested",
        longItemClassName: undefined,
      });
      if (nested) li.appendChild(nested);
    }
    list.appendChild(li);
  }
  return list;
}

function buildAnchor(
  href: string,
  label: string,
  target: "_blank" | "_self",
  className?: string,
): HTMLAnchorElement {
  const anchor = document.createElement("a");
  anchor.href = href;
  if (target === "_blank") {
    anchor.target = "_blank";
    anchor.rel = "noopener noreferrer";
  }
  if (className) anchor.className = className;
  anchor.textContent = label;
  return anchor;
}
