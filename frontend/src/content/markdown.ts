// @ts-nocheck

import DOMPurify from "dompurify";
import { marked } from "marked";
import { sanitizeHref } from "@/features/chat/normative/citationParsing";

export interface SmartScrollController {
  /** Force scroll to bottom (e.g., user's own message). */
  scrollToBottom: () => void;
  /** Scroll only if user is near the bottom (hasn't scrolled away to read). */
  scrollIfTracking: () => void;
  /** Remove scroll listener. */
  destroy: () => void;
}

const NEAR_BOTTOM_PX = 80;

export function createSmartScroller(scrollContainer: HTMLElement): SmartScrollController {
  let _userIsNearBottom = true;
  let _rafPending = false;

  function onScroll(): void {
    const { scrollTop, scrollHeight, clientHeight } = scrollContainer;
    _userIsNearBottom = scrollHeight - scrollTop - clientHeight <= NEAR_BOTTOM_PX;
  }

  scrollContainer.addEventListener("scroll", onScroll, { passive: true });

  function doScroll(): void {
    if (_rafPending) return;
    _rafPending = true;
    requestAnimationFrame(() => {
      _rafPending = false;
      scrollContainer.scrollTop = scrollContainer.scrollHeight;
      _userIsNearBottom = true;
    });
  }

  return {
    scrollToBottom: doScroll,
    scrollIfTracking(): void {
      if (_userIsNearBottom) doScroll();
    },
    destroy(): void {
      scrollContainer.removeEventListener("scroll", onScroll);
    },
  };
}

export interface MarkdownRenderOptions {
  scrollContainer?: HTMLElement | null;
  smartScroller?: SmartScrollController;
  onAnchor?: (anchor: HTMLAnchorElement, href: string) => void;
}

function buildFragment(markdown: string): DocumentFragment {
  const rawHtml = marked.parse(markdown, {
    gfm: true,
    breaks: true,
    headerIds: false,
    mangle: false,
  }) as string;

  const cleanHtml = DOMPurify.sanitize(rawHtml, {
    USE_PROFILES: { html: true },
    FORBID_TAGS: ["script", "style", "iframe", "object", "embed", "form", "input", "button"],
    FORBID_ATTR: ["style", "onerror", "onclick", "onload"],
    ALLOW_UNKNOWN_PROTOCOLS: false,
  });

  const template = document.createElement("template");
  template.innerHTML = cleanHtml;
  return template.content.cloneNode(true) as DocumentFragment;
}

export function buildMarkdownFragment(markdown: string, options: MarkdownRenderOptions = {}): DocumentFragment {
  const fragment = buildFragment(markdown);
  configureAnchors(fragment, options.onAnchor);
  return fragment;
}

function configureAnchors(scope: ParentNode, onAnchor?: MarkdownRenderOptions["onAnchor"]): void {
  scope.querySelectorAll("a").forEach((candidate) => {
    const anchor = candidate as HTMLAnchorElement;
    const safeHref = sanitizeHref(anchor.getAttribute("href"));
    if (!safeHref) {
      anchor.replaceWith(document.createTextNode(anchor.textContent || ""));
      return;
    }
    anchor.setAttribute("href", safeHref);
    if (/^https?:\/\//i.test(safeHref)) {
      anchor.setAttribute("target", "_blank");
      anchor.setAttribute("rel", "noopener noreferrer");
    }
    onAnchor?.(anchor, safeHref);
  });
}

let _scrollRafPending = false;
let _scrollTarget: HTMLElement | null = null;

function scrollIntoView(options: MarkdownRenderOptions): void {
  if (options.smartScroller) {
    options.smartScroller.scrollIfTracking();
    return;
  }
  const scrollContainer = options.scrollContainer;
  if (!scrollContainer) return;
  _scrollTarget = scrollContainer;
  if (_scrollRafPending) return;
  _scrollRafPending = true;
  requestAnimationFrame(() => {
    _scrollRafPending = false;
    if (_scrollTarget) {
      _scrollTarget.scrollTop = _scrollTarget.scrollHeight;
    }
  });
}

export async function renderMarkdown(container: HTMLElement, markdown: string, options: MarkdownRenderOptions = {}): Promise<void> {
  container.innerHTML = "";
  const fragment = buildMarkdownFragment(markdown, options);
  container.appendChild(fragment);
  scrollIntoView(options);
}

export async function appendMarkdown(container: HTMLElement, markdown: string, options: MarkdownRenderOptions = {}): Promise<void> {
  const fragment = buildMarkdownFragment(markdown, options);
  container.appendChild(fragment);
  scrollIntoView(options);
}
// @ts-nocheck
