import { createListSectionHeading } from "@/shared/ui/molecules/listSection";
import { createStateBlock } from "@/shared/ui/molecules/stateBlock";
import { icons } from "@/shared/ui/icons";
import {
  createVigenciaChip,
  type VigenciaChipOptions,
} from "@/shared/ui/atoms/vigenciaChip";

export type CitationActionKind = "modal" | "external" | "none";

export interface CitationItemViewModel {
  action: CitationActionKind;
  externalHint?: string | null;
  externalLabel?: string | null;
  externalUrl?: string | null;
  fallbackUrl?: string | null;
  hint?: string | null;
  id: string;
  mentionOnly?: boolean;
  meta: string;
  /**
   * True for W2 Phase 7 pre-populated preview items shown while LIA is still
   * thinking. The renderer forces `action` to `"none"`, skips click handler
   * binding, and applies the `.citation-preview` CSS class. Preview items are
   * overwritten atomically when the final citation list arrives.
   */
  preview?: boolean;
  rawCitation?: Record<string, unknown> | null;
  title: string;
  /**
   * fixplan_v3 §0.4 / sub-fix 1D — v3 vigencia chip annotation. When present,
   * `createDesktopCitationItem` appends a `<span data-lia-component=
   * "vigencia-chip">` to the body. None for chunks whose anchor is V (no
   * chip) or whose document has no anchor citation in `norm_citations`.
   */
  vigenciaV3?: VigenciaChipOptions | null;
}

export interface CitationGroupViewModel {
  id: string;
  items: CitationItemViewModel[];
  label: string;
}

export interface MobileCitationCardViewModel {
  action: CitationActionKind;
  externalUrl?: string | null;
  fallbackUrl?: string | null;
  id: string;
  mentionOnly?: boolean;
  meta: string;
  rawCitation?: Record<string, unknown> | null;
  title: string;
}

export function flattenCitationGroups(groups: CitationGroupViewModel[]): MobileCitationCardViewModel[] {
  return groups.flatMap((group) =>
    group.items.map((item) => ({
      action: item.action,
      externalUrl: item.externalUrl || null,
      fallbackUrl: item.fallbackUrl || null,
      id: item.id,
      mentionOnly: Boolean(item.mentionOnly),
      meta: item.meta,
      rawCitation: item.rawCitation || null,
      title: item.title,
    })),
  );
}

function createMetaNode(meta: string): HTMLElement | null {
  if (!meta) return null;
  const node = document.createElement("span");
  node.className = "citation-meta";
  node.textContent = meta;
  return node;
}

function maybeAppendVigenciaChip(parent: HTMLElement, opts: VigenciaChipOptions | null | undefined): void {
  if (!opts || !opts.state) return;
  const chip = createVigenciaChip(opts);
  if (chip) parent.appendChild(chip);
}

function createDesktopCitationItem(
  item: CitationItemViewModel,
  onItemClick?: ((item: CitationItemViewModel) => void) | null,
): HTMLLIElement {
  const li = document.createElement("li");
  li.setAttribute("data-lia-component", "citation-item");
  li.dataset.citationId = item.id;
  if (item.mentionOnly && item.action !== "modal") {
    li.classList.add("citation-mention-item");
  }
  if (item.action === "external") {
    li.classList.add("citation-has-external");
  }

  // W2 Phase 7 — preview short-circuit. Renders the same button structure as
  // the final tab but muted/whitish so the tab size is identical between
  // preview and final (no layout shift). Click handler is NOT bound; the
  // button is disabled and the li has pointer-events: none as a guard.
  if (item.preview) {
    li.classList.add("citation-preview");
    li.setAttribute("aria-disabled", "true");
    const button = document.createElement("button");
    button.type = "button";
    button.className = "citation-trigger";
    button.disabled = true;

    const body = document.createElement("span");
    body.className = "citation-trigger__body";
    const titleEl = document.createElement("span");
    titleEl.className = "citation-trigger__title";
    titleEl.textContent = item.title;
    body.appendChild(titleEl);
    const meta = createMetaNode(item.meta);
    if (meta) body.appendChild(meta);
    button.appendChild(body);

    const cta = document.createElement("span");
    cta.className = "citation-trigger__cta";
    cta.textContent = "Ver m\u00e1s \u203A";
    button.appendChild(cta);

    li.appendChild(button);
    return li;
  }

  if (item.action === "modal") {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "citation-trigger";

    const body = document.createElement("span");
    body.className = "citation-trigger__body";
    const titleEl = document.createElement("span");
    titleEl.className = "citation-trigger__title";
    titleEl.textContent = item.title;
    body.appendChild(titleEl);
    const meta = createMetaNode(item.meta);
    if (meta) body.appendChild(meta);
    maybeAppendVigenciaChip(body, item.vigenciaV3);
    button.appendChild(body);

    const cta = document.createElement("span");
    cta.className = "citation-trigger__cta";
    cta.textContent = "Ver m\u00e1s \u203A";
    button.appendChild(cta);

    if (onItemClick) {
      button.addEventListener("click", () => onItemClick(item));
    }
    li.appendChild(button);
    if (item.mentionOnly && item.hint) {
      const hint = document.createElement("span");
      hint.className = "citation-mention-hint";
      if (item.externalUrl) {
        const link = document.createElement("a");
        link.href = item.externalUrl;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.className = "citation-external-secondary";
        link.textContent = item.hint;
        hint.appendChild(link);
      } else {
        hint.textContent = item.hint;
      }
      li.appendChild(hint);
    }
    return li;
  }

  if (item.action === "external" && item.externalUrl) {
    const link = document.createElement("a");
    link.href = item.externalUrl;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.className = "citation-external-link";
    link.textContent = item.title;
    const meta = createMetaNode(item.meta);
    if (meta) link.appendChild(meta);
    li.appendChild(link);
    maybeAppendVigenciaChip(li, item.vigenciaV3);

    if (item.externalHint) {
      const hint = document.createElement("span");
      hint.className = "citation-mention-hint";
      hint.textContent = item.externalHint;
      li.appendChild(hint);
    }

    return li;
  }

  const title = document.createElement("p");
  title.className = "citation-mention-title";
  title.textContent = item.title;
  li.appendChild(title);

  const meta = createMetaNode(item.meta);
  if (meta) li.appendChild(meta);
  maybeAppendVigenciaChip(li, item.vigenciaV3);

  if (item.hint) {
    const hint = document.createElement("span");
    hint.className = "citation-mention-hint";
    hint.textContent = item.hint;
    li.appendChild(hint);
  }
  return li;
}

export function createCitationPlaceholder(
  label: string,
  tone: "loading" | "empty" | "deferred" = "empty",
): HTMLLIElement {
  const li = document.createElement("li");
  li.className = "citation-placeholder";
  li.setAttribute("data-lia-component", "citation-placeholder");
  if (tone === "loading") {
    li.setAttribute("data-loading", "true");
    li.appendChild(
      createStateBlock({
        className: "citation-placeholder__state",
        compact: true,
        message: label,
        tone: "loading",
      }),
    );
    return li;
  }

  li.appendChild(
    createStateBlock({
      className: "citation-placeholder__state",
      compact: true,
      message: label,
      tone: tone === "deferred" ? "deferred" : "empty",
    }),
  );
  return li;
}

export function renderCitationList(
  container: HTMLElement,
  groups: CitationGroupViewModel[],
  options: {
    emptyLabel?: string;
    onItemClick?: ((item: CitationItemViewModel) => void) | null;
  } = {},
): void {
  const { emptyLabel = "Sin normativa", onItemClick = null } = options;
  container.replaceChildren();

  const nonEmptyGroups = groups.filter((group) => group.items.length > 0);
  if (nonEmptyGroups.length === 0) {
    container.appendChild(createCitationPlaceholder(emptyLabel));
    return;
  }

  const showDividers = nonEmptyGroups.length > 1;
  for (const group of nonEmptyGroups) {
    if (showDividers) {
      const divider = createListSectionHeading({
        className: "citation-group-divider",
        dataComponent: "citation-group-divider",
        label: group.label,
        tagName: "li",
      });
      container.appendChild(divider);
    }
    for (const item of group.items) {
      container.appendChild(createDesktopCitationItem(item, onItemClick));
    }
  }
}

function createMobileCitationCard(
  item: MobileCitationCardViewModel,
  index: number,
): HTMLDivElement {
  const card = document.createElement("div");
  card.className = ["mobile-citation-card", item.mentionOnly ? "is-mention-only" : ""]
    .filter(Boolean)
    .join(" ");
  card.setAttribute("data-lia-component", "mobile-citation-card");
  card.dataset.citationIndex = String(index);
  card.dataset.citationId = item.id;
  card.setAttribute("role", "button");
  card.tabIndex = 0;

  const icon = document.createElement("span");
  icon.className = "mobile-citation-card-icon";
  icon.setAttribute("aria-hidden", "true");
  icon.innerHTML = icons.normGraph;

  const body = document.createElement("div");
  body.className = "mobile-citation-card-body";

  const title = document.createElement("p");
  title.className = "mobile-citation-card-title";
  title.textContent = item.title;
  body.appendChild(title);

  const meta = document.createElement("p");
  meta.className = "mobile-citation-card-meta";
  meta.textContent = item.meta;
  body.appendChild(meta);

  const arrow = document.createElement("span");
  arrow.className = "mobile-citation-card-arrow";
  arrow.setAttribute("aria-hidden", "true");
  arrow.textContent = "\u203A";

  card.append(icon, body, arrow);
  return card;
}

export function renderMobileCitationCards(
  container: HTMLElement,
  items: MobileCitationCardViewModel[],
): void {
  container.replaceChildren();
  const fragment = document.createDocumentFragment();
  items.forEach((item, index) => fragment.appendChild(createMobileCitationCard(item, index)));
  container.appendChild(fragment);
}
