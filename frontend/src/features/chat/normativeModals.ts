// @ts-nocheck

/**
 * Normative modal controller — modal stack, openNormaModal orchestration.
 * Submodules: normative/citationParsing, normative/profileRenderer, normative/interpretationModal.
 * Reduced from ~1,671L to controller during decouple-v1 Phase 3.
 */

import type { I18nRuntime } from "@/shared/i18n";
import type {
  ChatModalState,
  CreateNormativeModalControllerOptions,
  NormativeModalDom,
} from "@/features/chat/normative/types";
import {
  parseEtLocatorText,
  formatParsedEtLocator,
  parseEtTitle,
  toSpanishTitleCase,
  canonicalizeEtArticleToken,
  expandArticleRange,
} from "@/features/chat/normative/citationParsing";
import {
  fetchCitationProfileInstant,
  fetchCitationProfileLlm,
  createProfileRenderer,
} from "@/features/chat/normative/profileRenderer";
import {
  createInterpretationModal,
} from "@/features/chat/normative/interpretationModal";
import { openPracticaReader } from "@/features/chat/normative/practicaReader";
import { openArticleReader } from "@/features/chat/normative/articleReader";
import { isRawDocId } from "@/shared/utils/documentIdentifierDetection";
import {
  formatDecretoTitle,
  formatFormularioTitle,
  formatLeyTitle,
  formatResolucionTitle,
} from "@/features/chat/normative/normativeTitleFormatters";

// ── Public re-exports (used by chatApp, chatCitationRenderer) ──

export function deriveSourceTierLabel(citation: Record<string, unknown> | null | undefined): string {
  if (citation && citation.primary_role === "baseline" && citation.cross_topic) {
    return "Fuente Normativa (Base transversal)";
  }
  if (citation && typeof citation.source_tier === "string" && citation.source_tier.trim()) {
    return citation.source_tier.trim();
  }
  const knowledgeClass = String(citation?.knowledge_class || "").trim().toLowerCase();
  const sourceType = String(citation?.source_type || "").trim().toLowerCase();
  const sourceUrl = String(citation?.url || "").trim().toLowerCase();
  const practicalOverride =
    sourceType === "operational_checklist" ||
    sourceType === "internal_control" ||
    sourceType === "user_upload_practical" ||
    (sourceUrl.startsWith("local_upload://") &&
      (knowledgeClass === "practica_erp" ||
        sourceType === "operational_checklist" ||
        sourceType === "user_upload_practical"));
  if (practicalOverride) return "Fuente Loggro";
  if (knowledgeClass === "normative_base") return "Fuente Normativa";
  if (knowledgeClass === "interpretative_guidance") return "Fuente Expertos";
  if (knowledgeClass === "practica_erp") return "Fuente Loggro";
  return "Fuente Expertos";
}

export function formatNormativeCitationTitle(rawTitle: unknown): string {
  const clean = String(rawTitle || "").replace(/\s+/g, " ").trim();
  if (!clean) return "";

  // Ordered ladder: Ley / Decreto / Resolución first (so parseEtTitle
  // doesn't swallow "Ley 1819 de 2016" as an ET reference), then parseEtTitle,
  // then Formulario/Formato, then fall back to the cleaned input.
  return (
    formatLeyTitle(clean) ||
    formatDecretoTitle(clean) ||
    formatResolucionTitle(clean) ||
    parseEtTitle(rawTitle) ||
    formatFormularioTitle(clean) ||
    clean
  );
}

// isRawDocId now lives in shared/utils/documentIdentifierDetection.ts.

function humanizeCitationFallback(citation: Record<string, unknown> | null | undefined): string {
  const authority = String(citation?.authority || "").trim();
  const tema = String(citation?.tema || citation?.topic || "").trim();
  if (authority && tema) return `${authority} — ${toSpanishTitleCase(tema.replace(/_/g, " "))}`;
  if (authority) return authority;
  if (tema) return toSpanishTitleCase(tema.replace(/_/g, " "));
  return "Referencia normativa";
}

export function citationTitleValue(citation: Record<string, unknown> | null | undefined): string {
  const referenceKey = String(citation?.reference_key || "").trim().toLowerCase();
  if (referenceKey === "et") {
    const locatorText = String(citation?.locator_text || "").trim();
    const locatorStart = String(citation?.locator_start || "").trim();
    const locatorEnd = String(citation?.locator_end || "").trim();
    const locatorFromFields =
      parseEtLocatorText(locatorText) ||
      parseEtLocatorText(locatorStart && locatorEnd ? `${locatorStart} - ${locatorEnd}` : locatorStart);
    if (locatorFromFields) {
      return formatParsedEtLocator(locatorFromFields);
    }
  }
  if (referenceKey.startsWith("ley:")) {
    const parts = referenceKey.split(":");
    if (parts.length >= 3) return `Ley ${parts[1]} de ${parts[2]}`;
    if (parts.length === 2) return `Ley ${parts[1]}`;
  }
  const candidates = [citation?.source_label, citation?.legal_reference, citation?.title];
  for (const candidate of candidates) {
    const value = String(candidate || "").trim();
    if (value && !isRawDocId(value)) {
      return formatNormativeCitationTitle(value);
    }
  }
  const docId = String(citation?.doc_id || "").trim();
  if (docId && !isRawDocId(docId)) {
    return formatNormativeCitationTitle(docId);
  }
  return humanizeCitationFallback(citation);
}

// ── Controller factory ────────────────────────────────────────

export function createNormativeModalController({
  i18n,
  state,
  dom,
  withThinkingWheel,
}: CreateNormativeModalControllerOptions) {
  const {
    modalLayer,
    modalNorma,
    modalInterpretations,
    modalSummary,
    normaTitleNode,
  } = dom;

  // ── Modal stack management ────────────────────────────────

  function openModal(modal: HTMLElement | null): void {
    if (!modal) return;
    modalLayer.hidden = false;
    if (!modal.classList.contains("is-open")) {
      modal.classList.add("is-open");
      modal.setAttribute("aria-hidden", "false");
    }
    if (!state.modalStack.includes(modal.id)) {
      state.modalStack.push(modal.id);
    }
  }

  function closeModal(modal: HTMLElement | null): void {
    if (!modal) return;
    modal.classList.remove("is-open");
    modal.setAttribute("aria-hidden", "true");
    const idx = state.modalStack.lastIndexOf(modal.id);
    if (idx >= 0) state.modalStack.splice(idx, 1);
    if (state.modalStack.length === 0) modalLayer.hidden = true;
  }

  function closeTopModal(): void {
    if (state.modalStack.length === 0) return;
    const topId = state.modalStack[state.modalStack.length - 1];
    const modal = document.getElementById(topId);
    if (!(modal instanceof HTMLElement)) return;
    closeModal(modal);
  }

  function closeAllModals(): void {
    closeModal(modalSummary);
    closeModal(modalInterpretations);
    closeModal(modalNorma);
  }

  // ── Sub-controllers ───────────────────────────────────────

  const profileRenderer = createProfileRenderer({
    i18n,
    dom: { ...dom, modalNorma } as any,
    formatNormativeCitationTitle,
    isRawDocId,
    onPracticaItemClick: (citation) => {
      const docId = String(citation?.doc_id || "").trim();
      const label = String(citation?.source_label || "").trim() || "Guía práctica";
      const knowledgeClass = String(citation?.knowledge_class || "practica_erp").trim();
      if (!docId) return;
      // All depth-section items use the article reader for consistent
      // formatting — corpus normative chunks aren't formal norms with
      // rich citation profiles.
      openArticleReader(docId, label, knowledgeClass);
    },
  });

  const interpretationController = createInterpretationModal({
    i18n,
    state,
    dom,
    withThinkingWheel,
    openModal,
    modalInterpretations,
    modalSummary,
  });

  const { clearInterpretations, clearSummary } = interpretationController;

  // ── Article range picker ─────────────────────────────────

  let articlePickerEl: HTMLElement | null = null;

  function getOrCreateArticlePicker(): HTMLElement {
    if (articlePickerEl) return articlePickerEl;
    articlePickerEl = document.createElement("div");
    articlePickerEl.className = "norma-article-picker-container";
    articlePickerEl.hidden = true;
    dom.normaTopbarNode.parentElement?.insertBefore(articlePickerEl, dom.normaTopbarNode);
    return articlePickerEl;
  }

  function clearArticlePicker(): void {
    if (articlePickerEl) {
      articlePickerEl.innerHTML = "";
      articlePickerEl.hidden = true;
    }
  }

  function showArticleRangePicker(
    articles: string[],
    baseCitation: Record<string, unknown>,
    rangeTitle: string,
  ): void {
    const picker = getOrCreateArticlePicker();
    picker.innerHTML = "";
    picker.hidden = false;

    const hint = document.createElement("p");
    hint.className = "norma-article-picker-hint";
    hint.textContent = "Selecciona un artículo para ver su contenido:";
    picker.appendChild(hint);

    const pillBar = document.createElement("div");
    pillBar.className = "norma-article-picker";

    articles.forEach((articleNum) => {
      const pill = document.createElement("button");
      pill.type = "button";
      pill.className = "norma-article-pill";
      pill.textContent = `Art. ${articleNum}`;
      pill.dataset.article = articleNum;
      pill.addEventListener("click", () => {
        pillBar.querySelectorAll(".norma-article-pill").forEach((p) => p.classList.remove("is-active"));
        pill.classList.add("is-active");

        const singleCitation: Record<string, unknown> = {
          ...baseCitation,
          locator_start: articleNum,
          locator_end: "",
          locator_text: `Artículo ${articleNum}`,
          locator_kind: "article",
        };
        const requestId = ++state.activeNormaRequestId;
        const articleTitle = `Estatuto Tributario, Artículo ${articleNum}`;
        normaTitleNode.textContent = articleTitle;
        profileRenderer.resetNormaProfileCard();
        profileRenderer.setNormaModalStatus(i18n.t("chat.modal.norma.loading"), "loading");
        loadArticleProfile(singleCitation, requestId, articleTitle);
      });
      pillBar.appendChild(pill);
    });

    picker.appendChild(pillBar);
    profileRenderer.setNormaModalStatus("", "done");
  }

  // ── Profile fetch logic ────────────────────────────────────

  function loadArticleProfile(
    citation: Record<string, unknown>,
    requestId: number,
    fallbackTitle: string,
  ): void {
    const fetchOpts = { messageContext: state.lastUserMessage };

    fetchCitationProfileInstant(citation, fetchOpts)
      .then((profile) => {
        if (requestId !== state.activeNormaRequestId) return;
        const needsLlm = Boolean((profile as any)?.needs_llm);
        const isFormularioProfile = /^(?:Formulario|Formato)\s+\d/i.test(
          String(profile?.title || fallbackTitle || "").trim(),
        );
        const isCorpusGap = Boolean((profile as any)?.corpus_gap);
        const suppressCheckmark =
          isFormularioProfile ||
          isCorpusGap ||
          (String(profile?.document_family || "").trim() === "et_dur" && Boolean(profile?.original_text));

        profileRenderer.renderProfileContent(profile, fallbackTitle, { showLlmSpinner: needsLlm });
        if (!needsLlm) {
          if (isCorpusGap) {
            profileRenderer.setNormaModalStatus("Texto no disponible en el corpus", "warning");
            return;
          }
          profileRenderer.setNormaModalStatus(suppressCheckmark ? "" : "✓", "done");
          return;
        }

        fetchCitationProfileLlm(citation, fetchOpts)
          .then((llmResult) => {
            if (requestId !== state.activeNormaRequestId) return;
            if ((llmResult as any)?.skipped) {
              profileRenderer.setNormaModalStatus(suppressCheckmark ? "" : "✓", "done");
              return;
            }
            profileRenderer.applyLlmEnrichment(profile, llmResult, fallbackTitle);
          })
          .catch(() => {
            if (requestId !== state.activeNormaRequestId) return;
            const spinner = dom.normaSectionsNode.querySelector('[data-role="llm-spinner"]');
            if (spinner) spinner.remove();
            profileRenderer.setNormaModalStatus(suppressCheckmark ? "" : "✓", "done");
          });
      })
      .catch(() => {
        if (requestId !== state.activeNormaRequestId) return;
        profileRenderer.resetNormaProfileCard();
        normaTitleNode.textContent = fallbackTitle;
        profileRenderer.setNormaModalStatus(i18n.t("chat.modal.norma.profileError"), "error");
      });
  }

  // ── openNormaModal orchestration ──────────────────────────

  function openNormaModal(citation: Record<string, unknown>): void {
    state.activeCitation = citation;
    const requestId = ++state.activeNormaRequestId;
    const fallbackTitle = citationTitleValue(citation) || "Referencia normativa";
    normaTitleNode.textContent = fallbackTitle;
    profileRenderer.resetNormaProfileCard();
    clearArticlePicker();

    const referenceKey = String(citation?.reference_key || "").trim().toLowerCase();
    const locatorStart = canonicalizeEtArticleToken(citation?.locator_start);
    const locatorEnd = canonicalizeEtArticleToken(citation?.locator_end);

    if (referenceKey === "et" && locatorStart && locatorEnd) {
      const articles = expandArticleRange(locatorStart, locatorEnd);
      if (articles && articles.length > 1) {
        showArticleRangePicker(articles, citation, fallbackTitle);
        openModal(modalNorma);
        return;
      }
    }

    profileRenderer.setNormaModalStatus(i18n.t("chat.modal.norma.loading"), "loading");
    openModal(modalNorma);
    loadArticleProfile(citation, requestId, fallbackTitle);
  }

  // ── Bind modal controls ───────────────────────────────────

  function bindModalControls(): void {
    document.querySelectorAll("[data-close-modal]").forEach((node) => {
      node.addEventListener("click", () => {
        const modalId = node.getAttribute("data-close-modal");
        if (!modalId) return;
        const modal = document.getElementById(modalId);
        if (!(modal instanceof HTMLElement)) return;
        closeModal(modal);
      });
    });

    document.querySelectorAll("[data-back-modal]").forEach((node) => {
      node.addEventListener("click", () => closeTopModal());
    });

    window.addEventListener("keydown", (event) => {
      if (event.key === "Escape") closeTopModal();
    });
  }

  return {
    bindModalControls,
    clearInterpretations,
    clearSummary,
    closeAllModals,
    closeModal,
    closeTopModal,
    openInterpretationsModal: interpretationController.openInterpretationsModal,
    openNormaModal,
    openSummaryModal: interpretationController.openSummaryModal,
    openModal,
  };
}
