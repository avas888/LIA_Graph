// @ts-nocheck

/**
 * Citation profile card rendering — facts, sections, actions, caution banners.
 * Extracted from normativeModals.ts during decouple-v1 Phase 3.
 */

import { getJson } from "@/shared/api/client";
import { visibleText } from "@/shared/utils/format";
import type {
  CitationProfileAction,
  CitationProfileBanner,
  CitationProfileFact,
  CitationProfileResponse,
  CitationProfileSection,
  NormativeModalDom,
} from "@/features/chat/normative/types";
import {
  appendNormaTextContent,
  boldifyFormularioReferences,
  isRenderableEvidenceStatus,
  openLinkInNewTab,
  sanitizeHref,
} from "@/features/chat/normative/citationParsing";
import { createBadge } from "@/shared/ui/atoms/badge";
import type { LiaChipTone } from "@/shared/ui/atoms/chip";
import { formatBindingForceText } from "@/features/chat/normative/bindingForceFormatter";
import {
  isBulletListBlock,
  splitBlockLines,
  splitParagraphBlocks,
  stripBulletMarker,
} from "@/shared/utils/textBlockFormatter";
import { buildNormaFacts } from "@/features/chat/normative/profileFactsBuilder";
import { buildLinkableListNode } from "@/shared/ui/molecules/linkableList";

// ── Fetch helpers ─────────────────────────────────────────────

export function buildCitationProfileParams(
  citation: Record<string, unknown>,
  options: { messageContext?: string } = {},
): URLSearchParams {
  const params = new URLSearchParams();
  const docId = String(citation?.doc_id || "").trim();
  const referenceKey = String(citation?.reference_key || "").trim();

  // Defense-in-depth: detect ley/ET mismatch via multiple signals.
  // The citation may have reference_key="et" (from the ET doc) even
  // though its display label says "Ley 2277 de 2022".
  const isEtDurDocId = /(?:_et_art_|_dur_art_|^renta_corpus_a_et_)/i.test(docId);
  const isLeyRefKey = /^ley:\d+(?::\d{4})?$/i.test(referenceKey);

  let leyFromLabel = "";
  if (!isLeyRefKey && isEtDurDocId) {
    for (const field of ["source_label", "legal_reference", "title"] as const) {
      const labelMatch = /Ley\s+(\d+)\s+de\s+(\d{4})/i.exec(
        String((citation as Record<string, unknown>)?.[field] || ""),
      );
      if (labelMatch) {
        leyFromLabel = `ley:${labelMatch[1]}:${labelMatch[2]}`;
        break;
      }
    }
  }

  const useLeyReferenceKey = isEtDurDocId && (isLeyRefKey || !!leyFromLabel);
  const effectiveLeyKey = isLeyRefKey ? referenceKey : leyFromLabel;

  if (docId && !useLeyReferenceKey) {
    params.set("doc_id", docId);
  } else if (useLeyReferenceKey && effectiveLeyKey) {
    params.set("reference_key", effectiveLeyKey);
  } else {
    if (!/^formulario:\d{2,6}[a-z]?$/i.test(referenceKey) && !referenceKey) {
      throw new Error("citation_profile_missing_doc_id");
    }
    if (referenceKey) {
      params.set("reference_key", referenceKey);
    }
  }

  const locatorFields = ["locator_text", "locator_kind", "locator_start", "locator_end"] as const;
  locatorFields.forEach((field) => {
    const value = String(citation?.[field] || "").trim();
    if (value) params.set(field, value);
  });

  const messageContext = String(options.messageContext || "").trim();
  const referenceKeyLower = referenceKey.toLowerCase();
  const shouldSendMessageContext =
    !!messageContext &&
    (referenceKeyLower === "et" ||
      referenceKeyLower === "dur:1625:2016" ||
      referenceKeyLower.startsWith("ley:") ||
      locatorFields.some((field) => String(citation?.[field] || "").trim()));
  if (shouldSendMessageContext) {
    params.set("message_context", messageContext);
  }

  return params;
}

export function fetchCitationProfile(
  citation: Record<string, unknown>,
  options: { messageContext?: string } = {},
): Promise<CitationProfileResponse> {
  const params = buildCitationProfileParams(citation, options);
  return getJson<CitationProfileResponse>(`/api/citation-profile?${params.toString()}`);
}

export function fetchCitationProfileInstant(
  citation: Record<string, unknown>,
  options: { messageContext?: string } = {},
): Promise<CitationProfileResponse> {
  const params = buildCitationProfileParams(citation, options);
  params.set("phase", "instant");
  return getJson<CitationProfileResponse>(`/api/citation-profile?${params.toString()}`);
}

export function fetchCitationProfileLlm(
  citation: Record<string, unknown>,
  options: { messageContext?: string } = {},
): Promise<CitationProfileResponse> {
  const params = buildCitationProfileParams(citation, options);
  params.set("phase", "llm");
  return getJson<CitationProfileResponse>(`/api/citation-profile?${params.toString()}`);
}

// ── Profile renderer factory ──────────────────────────────────

export interface ProfileRendererDeps {
  i18n: any;
  dom: Pick<
    NormativeModalDom,
    | "normaTitleNode" | "normaBindingForceNode" | "normaOriginalBtn"
    | "normaAnalysisBtn" | "normaOriginalHelperNode" | "normaAnalysisHelperNode"
    | "normaTopbarNode" | "normaLoadingNode" | "normaHelperNode"
    | "normaCautionBannerNode" | "normaCautionTitleNode" | "normaCautionBodyNode"
    | "normaPrimaryNode" | "normaLeadNode" | "normaFactsNode"
    | "normaSectionsNode" | "normaCompanionNode" | "normaCompanionBtn"
    | "normaCompanionHelperNode"
  >;
  formatNormativeCitationTitle: (raw: unknown) => string;
  isRawDocId: (value: unknown) => boolean;
  onPracticaItemClick?: (citation: Record<string, unknown>) => void;
}

export function createProfileRenderer(deps: ProfileRendererDeps) {
  const {
    i18n, dom, formatNormativeCitationTitle, isRawDocId,
  } = deps;
  const {
    normaTitleNode, normaBindingForceNode, normaOriginalBtn, normaAnalysisBtn,
    normaOriginalHelperNode, normaAnalysisHelperNode, normaTopbarNode,
    normaLoadingNode, normaHelperNode, normaCautionBannerNode, normaCautionTitleNode,
    normaCautionBodyNode, normaPrimaryNode, normaLeadNode, normaFactsNode,
    normaSectionsNode, normaCompanionNode, normaCompanionBtn, normaCompanionHelperNode,
  } = dom;

  function setNormaModalStatus(message = "", tone = "loading"): void {
    const cleanMessage = String(message || "").trim();
    normaLoadingNode.hidden = !cleanMessage;
    normaLoadingNode.dataset.tone = cleanMessage ? tone : "";
    normaHelperNode.textContent = cleanMessage;
    (dom as any).modalNorma?.setAttribute?.("aria-busy", cleanMessage && tone === "loading" ? "true" : "false");
  }

  function resetNormaProfileCard(): void {
    normaTopbarNode.hidden = false;
    normaBindingForceNode.textContent = "";
    normaBindingForceNode.hidden = true;
    normaCautionBannerNode.hidden = true;
    normaCautionTitleNode.textContent = "";
    normaCautionBodyNode.textContent = "";
    normaPrimaryNode.innerHTML = "";
    normaPrimaryNode.hidden = true;
    normaLeadNode.textContent = "";
    normaLeadNode.hidden = true;
    normaFactsNode.innerHTML = "";
    normaFactsNode.hidden = true;
    normaSectionsNode.innerHTML = "";
    normaSectionsNode.hidden = true;
    normaOriginalBtn.textContent = i18n.t("chat.modal.norma.original");
    normaOriginalBtn.hidden = true;
    normaOriginalBtn.disabled = true;
    normaOriginalBtn.onclick = null;
    normaOriginalBtn.parentElement?.querySelector(".norma-original-fallback")?.remove();
    normaOriginalHelperNode.textContent = "";
    normaOriginalHelperNode.hidden = true;
    normaAnalysisBtn.hidden = true;
    normaAnalysisBtn.onclick = null;
    normaAnalysisHelperNode.textContent = "";
    normaAnalysisHelperNode.hidden = true;
    normaCompanionNode.hidden = true;
    normaCompanionNode.classList.remove("norma-companion-footer-mode");
    const existingFooterActions = normaCompanionNode.querySelector(".norma-footer-actions");
    if (existingFooterActions) existingFooterActions.remove();
    normaCompanionBtn.hidden = true;
    normaCompanionBtn.removeAttribute("href");
    normaCompanionHelperNode.textContent = "";
    normaCompanionHelperNode.hidden = true;
  }

  function renderNormaFacts(facts: CitationProfileFact[] = []): void {
    normaFactsNode.innerHTML = "";
    const rows = Array.isArray(facts)
      ? facts.filter(
          (fact) =>
            fact && typeof fact === "object" &&
            String(fact.label || "").trim() &&
            String(fact.value || "").trim(),
        )
      : [];
    normaFactsNode.hidden = rows.length === 0;
    rows.forEach((fact) => {
      const article = document.createElement("article");
      article.className = "norma-fact";
      const label = document.createElement("p");
      label.className = "norma-fact-label";
      label.textContent = String(fact.label || "").trim();
      const value = document.createElement("div");
      value.className = "norma-fact-value";
      appendNormaTextContent(value, fact.value, fact.label);
      article.append(label, value);
      normaFactsNode.appendChild(article);
    });
  }

  // buildNormaFacts moved to profileFactsBuilder.ts — pure data transform,
  // unit-testable without DOM or dep bag.

  function renderNormaSections(sections: CitationProfileSection[] = []): void {
    normaSectionsNode.innerHTML = "";
    const rows = Array.isArray(sections)
      ? sections.filter(
          (section) =>
            section && typeof section === "object" &&
            String(section.title || "").trim() &&
            String(section.body || "").trim(),
        )
      : [];
    normaSectionsNode.hidden = rows.length === 0;
    rows.forEach((section) => {
      const article = document.createElement("article");
      article.className = "norma-section-card";
      article.dataset.sectionId = String(section.id || "").trim();
      const title = document.createElement("h4");
      title.className = "norma-section-title";
      title.textContent = String(section.title || "").trim();
      const body = document.createElement("div");
      body.className = "norma-section-body";
      appendNormaTextContent(body, section.body, section.title);
      article.append(title, body);
      normaSectionsNode.appendChild(article);
    });
  }

  function appendQuoteParagraphs(container: HTMLElement, text: unknown): void {
    const blocks = splitParagraphBlocks(String(text ?? ""));
    if (blocks.length === 0) {
      container.textContent = "";
      return;
    }
    for (const block of blocks) {
      const paragraph = document.createElement("p");
      paragraph.className = "norma-quote-paragraph";
      paragraph.textContent = block;
      container.appendChild(paragraph);
    }
  }

  function buildNormaOriginalArticle(
    original,
    introText = "",
    options: { hideInlineSourceLink?: boolean } = {},
  ): HTMLElement | null {
    if (
      !original ||
      !isRenderableEvidenceStatus(original.evidence_status) ||
      !String(original.title || "").trim() ||
      !String(original.quote || "").trim()
    ) {
      return null;
    }
    const article = document.createElement("article");
    article.className = "norma-section-card norma-section-card-quote";
    article.dataset.sectionId = "texto_original_relevante";
    const intro = String(introText || "").trim();
    if (intro) {
      const introNode = document.createElement("p");
      introNode.className = "norma-section-intro";
      introNode.textContent = intro;
      article.appendChild(introNode);
    }
    const title = document.createElement("h4");
    title.className = "norma-section-title";
    title.textContent = String(original.title || "").trim();
    const quote = document.createElement("blockquote");
    quote.className = "norma-quote-block";
    appendQuoteParagraphs(quote, original.quote);
    article.append(title, quote);
    const annotationsNode = buildNormaAnnotationsNode(original.annotations);
    if (annotationsNode) article.appendChild(annotationsNode);
    const sourceHref = sanitizeHref(original.source_url || "");
    if (sourceHref && !options.hideInlineSourceLink) {
      const sourceLink = document.createElement("a");
      sourceLink.className = "norma-inline-source";
      sourceLink.href = sourceHref;
      sourceLink.target = "_blank";
      sourceLink.rel = "noopener noreferrer";
      sourceLink.textContent = "Ver fuente del artículo";
      article.appendChild(sourceLink);
    }
    return article;
  }

  function appendAnnotationPanelBody(
    panel: HTMLElement,
    rawBody: string,
    structuredItems?: Array<{ text?: string; href?: string | null }> | null,
  ): void {
    if (Array.isArray(structuredItems) && structuredItems.length > 0) {
      const linkable = buildLinkableListNode(structuredItems, {
        className: "norma-annot-list",
        splitLongAnchors: true,
        longItemClassName: "norma-annot-list__item--prose",
      });
      if (linkable) {
        panel.appendChild(linkable);
        return;
      }
    }
    for (const block of splitParagraphBlocks(rawBody)) {
      const lines = splitBlockLines(block);
      if (isBulletListBlock(lines)) {
        const list = document.createElement("ul");
        list.className = "norma-annot-list";
        for (const line of lines) {
          const li = document.createElement("li");
          li.textContent = stripBulletMarker(line);
          list.appendChild(li);
        }
        panel.appendChild(list);
      } else {
        const p = document.createElement("p");
        p.textContent = lines.join(" ");
        panel.appendChild(p);
      }
    }
  }

  function buildNormaAnnotationsNode(annotations): HTMLElement | null {
    const items = Array.isArray(annotations)
      ? annotations
          .map((item) => ({
            label: String(item?.label || "").trim(),
            body: String(item?.body || "").trim(),
            items: Array.isArray(item?.items) ? item.items : null,
          }))
          .filter((item) => item.label && (item.body || (item.items && item.items.length > 0)))
      : [];
    if (items.length === 0) return null;

    const wrapper = document.createElement("div");
    wrapper.className = "norma-annot";

    const tabStrip = document.createElement("div");
    tabStrip.className = "norma-annot-tabs";
    tabStrip.setAttribute("role", "tablist");

    const panels: HTMLElement[] = [];
    const buttons: HTMLButtonElement[] = [];

    items.forEach((item, idx) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "norma-annot-tab";
      btn.dataset.tabIndex = String(idx);
      btn.setAttribute("role", "tab");
      btn.setAttribute("aria-selected", "false");
      btn.tabIndex = idx === 0 ? 0 : -1;
      btn.textContent = item.label;
      buttons.push(btn);
      tabStrip.appendChild(btn);

      const panel = document.createElement("div");
      panel.className = "norma-annot-panel";
      panel.dataset.tabIndex = String(idx);
      panel.setAttribute("role", "tabpanel");
      panel.hidden = true;
      appendAnnotationPanelBody(panel, item.body, item.items);
      panels.push(panel);
    });

    const panelHost = document.createElement("div");
    panelHost.className = "norma-annot-panels";
    panels.forEach((p) => panelHost.appendChild(p));

    const select = (targetIndex: number) => {
      const currentlyActive = buttons.findIndex(
        (btn) => btn.getAttribute("aria-selected") === "true",
      );
      const shouldClose = currentlyActive === targetIndex;
      buttons.forEach((btn, i) => {
        const active = !shouldClose && i === targetIndex;
        btn.setAttribute("aria-selected", active ? "true" : "false");
        btn.tabIndex = active || (shouldClose && i === targetIndex) ? 0 : -1;
      });
      panels.forEach((panel, i) => {
        panel.hidden = shouldClose || i !== targetIndex;
      });
    };
    buttons.forEach((btn, idx) => {
      btn.addEventListener("click", () => select(idx));
    });

    wrapper.append(tabStrip, panelHost);
    return wrapper;
  }

  function buildNormaSectionCard(section: CitationProfileSection): HTMLElement | null {
    if (!section || typeof section !== "object" || !String(section.title || "").trim() || !String(section.body || "").trim()) {
      return null;
    }
    const article = document.createElement("article");
    article.className = "norma-section-card";
    article.dataset.sectionId = String(section.id || "").trim();
    const title = document.createElement("h4");
    title.className = "norma-section-title";
    title.textContent = String(section.title || "").trim();
    const body = document.createElement("div");
    body.className = "norma-section-body";
    appendNormaTextContent(body, section.body, section.title);

    // Collapse long bullet lists behind a toggle
    const MAX_VISIBLE_ITEMS = 5;
    const list = body.querySelector("ul.norma-bullet-list");
    if (list && list.children.length > MAX_VISIBLE_ITEMS) {
      const allItems = Array.from(list.children) as HTMLElement[];
      allItems.forEach((li, idx) => {
        if (idx >= MAX_VISIBLE_ITEMS) {
          li.hidden = true;
          li.dataset.collapsed = "true";
        }
      });
      const hiddenCount = allItems.length - MAX_VISIBLE_ITEMS;
      const toggle = document.createElement("button");
      toggle.type = "button";
      toggle.className = "norma-show-more-btn";
      toggle.textContent = `Mostrar ${hiddenCount} más`;
      let expanded = false;
      toggle.addEventListener("click", () => {
        expanded = !expanded;
        allItems.forEach((li, idx) => {
          if (idx >= MAX_VISIBLE_ITEMS) li.hidden = !expanded;
        });
        toggle.textContent = expanded ? "Mostrar menos" : `Mostrar ${hiddenCount} más`;
      });
      body.appendChild(toggle);
    }

    article.append(title, body);
    return article;
  }

  function renderNormaStructuredSections(profile: CitationProfileResponse): void {
    normaPrimaryNode.innerHTML = "";
    normaSectionsNode.innerHTML = "";
    const isEtArticleProfile =
      String(profile?.document_family || "").trim() === "et_dur" && Boolean(profile?.original_text);

    const original = profile?.original_text;
    const useLeadInPrimary = isEtArticleProfile && String(profile?.lead || "").trim().length > 0;
    const originalSourceHref = sanitizeHref(original?.source_url || "");
    const topSourceActionHref = sanitizeHref(profile?.source_action?.url || "");
    const originalArticle = original
      ? buildNormaOriginalArticle(
          original,
          useLeadInPrimary ? String(profile?.lead || "").trim() : "",
          {
            hideInlineSourceLink: Boolean(
              originalSourceHref &&
              topSourceActionHref &&
              originalSourceHref === topSourceActionHref,
            ),
          },
        )
      : null;
    if (originalArticle) normaPrimaryNode.appendChild(originalArticle);

    const additionalDepthSections = Array.isArray(profile?.additional_depth_sections)
      ? profile.additional_depth_sections.filter((section) => {
          const title = String(section?.title || "").trim();
          const items = Array.isArray(section?.items)
            ? section.items.filter((item) => String(item?.label || "").trim())
            : [];
          return Boolean(title && items.length);
        })
      : [];

    // Render each additional_depth section as its own card, respecting accordion_default
    const kindBadgeConfig: Record<string, { label: string; tone: LiaChipTone }> = {
      normative_base: { label: "Normativa", tone: "info" },
      interpretative_guidance: { label: "Expertos", tone: "warning" },
      practica_erp: { label: "Práctico", tone: "success" },
    };
    const onItemClick = deps.onPracticaItemClick;

    // Render open sections first (e.g. "Contenido relacionado"), then closed ones
    const sortedDepthSections = [...additionalDepthSections].sort((a, b) => {
      const aOpen = String(a.accordion_default || "closed") === "open" ? 0 : 1;
      const bOpen = String(b.accordion_default || "closed") === "open" ? 0 : 1;
      return aOpen - bOpen;
    });

    for (const section of sortedDepthSections) {
      const sectionItems = (section.items || []).filter(
        (item) => String(item?.label || "").trim(),
      );
      if (sectionItems.length === 0) continue;

      const article = document.createElement("article");
      article.className = "norma-section-card";
      const isClosed = String(section.accordion_default || "closed") === "closed";
      const heading = document.createElement("h4");
      heading.className = "norma-section-title";
      if (isClosed) heading.classList.add("norma-section-title--toggle");
      heading.textContent = String(section.title || "").trim();
      article.appendChild(heading);
      const list = document.createElement("ul");
      list.className = "norma-bullet-list norma-depth-list";
      if (isClosed) list.classList.add("norma-depth-list--collapsed");

      for (let idx = 0; idx < sectionItems.length; idx++) {
        const item = sectionItems[idx];
        const label = String(item?.label || "").trim();
        const kind = String(item?.kind || "").trim();
        const docId = String(item?.doc_id || "").trim();
        const bullet = document.createElement("li");

        const badgeCfg = kindBadgeConfig[kind];
        if (badgeCfg) {
          const badge = createBadge({ label: badgeCfg.label, tone: badgeCfg.tone, emphasis: "soft" });
          bullet.appendChild(badge);
          bullet.appendChild(document.createTextNode(" "));
        }

        if (docId && onItemClick) {
          const link = document.createElement("a");
          link.href = "#";
          link.className = "norma-practica-link";
          link.textContent = label;
          link.addEventListener("click", (e) => {
            e.preventDefault();
            onItemClick({ doc_id: docId, source_label: label, knowledge_class: kind || "practica_erp" });
          });
          bullet.appendChild(link);
        } else {
          const href = sanitizeHref(item?.url || "");
          if (href) {
            const link = document.createElement("a");
            link.href = href;
            link.target = "_blank";
            link.rel = "noopener noreferrer";
            link.textContent = label;
            bullet.appendChild(link);
          } else {
            bullet.appendChild(document.createTextNode(label));
          }
        }
        list.appendChild(bullet);
      }
      article.appendChild(list);

      if (isClosed) {
        heading.addEventListener("click", () => {
          const wasCollapsed = list.classList.contains("norma-depth-list--collapsed");
          list.classList.toggle("norma-depth-list--collapsed");
          heading.classList.toggle("norma-section-title--expanded", wasCollapsed);
        });
      }

      normaSectionsNode.appendChild(article);
    }

    const legacySections = Array.isArray(profile?.sections)
      ? profile.sections.filter((section) => {
          const sectionId = String(section?.id || "").trim();
          if (sectionId === "texto_original_relevante" && profile?.original_text) return false;
          if (sectionId === "comentario_experto_relevante" && profile?.expert_comment) return false;
          if (sectionId === "impacto_profesional" && isEtArticleProfile) return false;
          if (/instrumento de diligenciamiento/i.test(String(section?.title || "").trim())) return false;
          return true;
        })
      : [];

    const impactSection =
      isEtArticleProfile && Array.isArray(profile?.sections)
        ? profile.sections.find(
            (section) => section && typeof section === "object" && String(section.id || "").trim() === "impacto_profesional",
          ) || null
        : null;
    const impactArticle = impactSection ? buildNormaSectionCard(impactSection) : null;
    if (impactArticle) normaPrimaryNode.appendChild(impactArticle);

    legacySections.forEach((section) => {
      const article = buildNormaSectionCard(section);
      if (article) normaSectionsNode.appendChild(article);
    });

    normaPrimaryNode.hidden = normaPrimaryNode.childElementCount === 0;
    normaSectionsNode.hidden = normaSectionsNode.childElementCount === 0;
  }

  function setNormaOriginalAction(action: CitationProfileAction | null | undefined): void {
    const href = sanitizeHref(action?.url || "");
    const label = String(action?.label || "").trim();
    const helperText = String(action?.helper_text || "").trim();
    const hasAction = Boolean(action && (label || href || helperText));
    normaOriginalBtn.hidden = !hasAction;
    normaOriginalBtn.textContent = label || i18n.t("chat.modal.norma.original");
    normaOriginalBtn.disabled = !href;
    normaOriginalBtn.onclick = href ? () => openLinkInNewTab(href) : null;
    normaOriginalHelperNode.textContent = helperText;
    normaOriginalHelperNode.hidden = !hasAction || !helperText;

    const existingFallback = normaOriginalBtn.parentElement?.querySelector(".norma-original-fallback");
    if (existingFallback) existingFallback.remove();
  }

  function setNormaAnalysisAction(action: CitationProfileAction | null | undefined): void {
    const rowState = String(action?.state || "").trim();
    const href = sanitizeHref(action?.url || "");
    if (!rowState || rowState === "not_applicable") {
      normaAnalysisBtn.hidden = true;
      normaAnalysisBtn.onclick = null;
      normaAnalysisHelperNode.textContent = "";
      normaAnalysisHelperNode.hidden = true;
      return;
    }
    normaAnalysisBtn.hidden = false;
    normaAnalysisBtn.textContent = String(action?.label || i18n.t("chat.modal.norma.deepAnalysis")).trim();
    normaAnalysisBtn.disabled = !href || rowState !== "available";
    normaAnalysisBtn.onclick = href && rowState === "available" ? () => openLinkInNewTab(href) : null;
    const helperText = String(action?.helper_text || "").trim();
    normaAnalysisHelperNode.textContent = helperText;
    normaAnalysisHelperNode.hidden = !helperText;
  }

  function renderNormaCautionBanner(banner: CitationProfileBanner | null | undefined): void {
    const title = visibleText(banner?.title);
    const body = visibleText(banner?.body);
    normaCautionBannerNode.hidden = !(title && body);
    normaCautionBannerNode.dataset.tone = title && body ? String(banner?.tone || "").trim() : "";
    normaCautionTitleNode.textContent = title;
    normaCautionBodyNode.textContent = body;
  }

  function renderNormaCompanionAction(action: CitationProfileAction | null | undefined): void {
    const rowState = String(action?.state || "").trim();
    if (!rowState || rowState === "not_applicable") {
      normaCompanionNode.hidden = true;
      normaCompanionBtn.hidden = true;
      normaCompanionBtn.removeAttribute("href");
      normaCompanionHelperNode.textContent = "";
      normaCompanionHelperNode.hidden = true;
      return;
    }
    normaCompanionNode.hidden = false;
    const label = normaCompanionBtn.querySelector(".norma-companion-link-label");
    if (label) {
      label.textContent = String(action?.label || i18n.t("chat.modal.norma.guidePrompt")).trim();
    }
    if (rowState === "available") {
      const href = sanitizeHref(action?.url || "");
      normaCompanionBtn.hidden = false;
      if (href) {
        normaCompanionBtn.setAttribute("href", href);
      } else {
        normaCompanionBtn.removeAttribute("href");
      }
      normaCompanionHelperNode.textContent = "";
      normaCompanionHelperNode.hidden = true;
      return;
    }
    normaCompanionBtn.hidden = true;
    normaCompanionBtn.removeAttribute("href");
    normaCompanionHelperNode.textContent = String(
      action?.helper_text || i18n.t("chat.modal.norma.guideUnavailable"),
    ).trim();
    normaCompanionHelperNode.hidden = false;
  }

  function renderFormularioFooter(
    sourceAction: CitationProfileAction | null | undefined,
    companionAction: CitationProfileAction | null | undefined,
    kind: "formulario" | "formato" = "formulario",
  ): void {
    normaCompanionBtn.hidden = true;
    normaCompanionHelperNode.hidden = true;
    const existing = normaCompanionNode.querySelector(".norma-footer-actions");
    if (existing) existing.remove();
    normaCompanionNode.classList.add("norma-companion-footer-mode");
    const footer = document.createElement("div");
    footer.className = "norma-footer-actions";
    const sourceHref = sanitizeHref(sourceAction?.url || "");
    const originalBtn = document.createElement("button");
    originalBtn.className = "secondary-btn";
    originalBtn.type = "button";
    originalBtn.textContent = kind === "formato" ? "Ir a formato original" : "Ir a formulario original";
    originalBtn.disabled = !sourceHref;
    if (sourceHref) originalBtn.onclick = () => openLinkInNewTab(sourceHref);
    footer.appendChild(originalBtn);
    const companionHref = sanitizeHref(companionAction?.url || "");
    const guideBtn = document.createElement("a");
    guideBtn.className = "primary-btn norma-footer-guide-btn";
    guideBtn.textContent = "Guía gráfica sobre cómo llenarlo";
    if (companionHref) {
      guideBtn.href = companionHref;
      guideBtn.target = "_blank";
      guideBtn.rel = "noopener noreferrer";
    } else {
      guideBtn.removeAttribute("href");
      guideBtn.classList.add("is-disabled");
    }
    footer.appendChild(guideBtn);
    normaCompanionNode.appendChild(footer);
    normaCompanionNode.hidden = false;
  }

  function renderProfileContent(
    profile: CitationProfileResponse,
    fallbackTitle: string,
    opts: { showLlmSpinner?: boolean } = {},
  ): void {
    const profileTitle = String(profile?.title || "").trim();
    const candidateTitle =
      profileTitle && !isRawDocId(profileTitle)
        ? formatNormativeCitationTitle(profileTitle) || fallbackTitle
        : fallbackTitle;
    normaTitleNode.textContent = candidateTitle;
    const formKindMatch = /^(Formulario|Formato)\s+\d/i.exec(candidateTitle);
    const isFormularioProfile = Boolean(formKindMatch);
    const formKind: "formulario" | "formato" = formKindMatch
      ? (formKindMatch[1].toLowerCase() as "formulario" | "formato")
      : "formulario";

    // Eyebrow text: the backend emits `binding_force` from
    // `normative_taxonomy.py` as a classification label. Prefix delegated
    // to the shared formatter so desktop and mobile stay in sync.
    const bindingForceText = formatBindingForceText(String(profile?.binding_force || ""));
    normaBindingForceNode.textContent = bindingForceText;
    normaBindingForceNode.hidden = !bindingForceText;

    const lead = String(profile?.lead || "").trim();
    const useLeadInPrimary =
      String(profile?.document_family || "").trim() === "et_dur" &&
      Boolean(profile?.original_text) && Boolean(lead);
    const isEtArticleProfile =
      String(profile?.document_family || "").trim() === "et_dur" && Boolean(profile?.original_text);
    normaLeadNode.textContent = "";
    normaLeadNode.hidden = true;

    renderNormaCautionBanner(isFormularioProfile ? null : profile?.caution_banner);
    renderNormaFacts(buildNormaFacts(profile || {}));
    renderNormaStructuredSections(profile || {});

    if (opts.showLlmSpinner) {
      const spinner = document.createElement("div");
      spinner.className = "norma-llm-loading";
      spinner.dataset.role = "llm-spinner";
      spinner.innerHTML =
        '<span class="norma-llm-loading-icon"></span>' +
        '<span class="norma-llm-loading-text">Generando análisis de impacto profesional…</span>';
      normaSectionsNode.appendChild(spinner);
      normaSectionsNode.hidden = false;
    }

    if (isFormularioProfile) {
      normaTopbarNode.hidden = true;
      renderFormularioFooter(profile?.source_action, profile?.companion_action, formKind);
      boldifyFormularioReferences(normaTitleNode);
      const profileContainer = normaPrimaryNode.closest(".norma-profile");
      if (profileContainer instanceof HTMLElement) boldifyFormularioReferences(profileContainer);
    } else {
      setNormaOriginalAction(profile?.source_action);
      if (isEtArticleProfile) {
        normaAnalysisBtn.hidden = true;
        normaAnalysisBtn.onclick = null;
        normaAnalysisHelperNode.textContent = "";
        normaAnalysisHelperNode.hidden = true;
      } else {
        setNormaAnalysisAction(profile?.analysis_action);
      }
      renderNormaCompanionAction(profile?.companion_action);
      normaTopbarNode.hidden = false;
    }

    if (!opts.showLlmSpinner) {
      // Hide the loader entirely once the profile is rendered. Previously the
      // Ley/Decreto branch left it visible with a literal "✓" string, which
      // combined with the CSS-drawn checkmark inside `.modal-inline-googly-core::after`
      // produced a double-checkmark "✓ ✓" banner (see docs/guides/modal_content_layout_leyes_et.md §7).
      setNormaModalStatus("", "done");
    }
  }

  function applyLlmEnrichment(
    baseProfile: CitationProfileResponse,
    llmResult: CitationProfileResponse,
    fallbackTitle: string,
  ): void {
    const enriched: CitationProfileResponse = {
      ...baseProfile,
      lead: String(llmResult?.lead || "").trim() || baseProfile.lead,
      facts: Array.isArray(llmResult?.facts) && llmResult.facts.length > 0 ? llmResult.facts : baseProfile.facts,
      sections: Array.isArray(llmResult?.sections) && llmResult.sections.length > 0 ? llmResult.sections : baseProfile.sections,
      vigencia_detail: llmResult?.vigencia_detail ?? baseProfile.vigencia_detail,
    };
    renderProfileContent(enriched, fallbackTitle);
  }

  return {
    setNormaModalStatus,
    resetNormaProfileCard,
    renderProfileContent,
    applyLlmEnrichment,
  };
}
