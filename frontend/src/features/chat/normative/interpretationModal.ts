// @ts-nocheck

/**
 * Interpretation browsing + summary modal logic.
 * Extracted from normativeModals.ts during decouple-v1 Phase 3.
 */

import { stripMarkdown } from "@/shared/utils/format";
import type { AsyncTaskRunner, ChatModalState, NormativeModalDom } from "@/features/chat/normative/types";

export interface InterpretationModalDeps {
  i18n: any;
  state: ChatModalState;
  dom: Pick<
    NormativeModalDom,
    | "interpretationStatusNode" | "interpretationResultsNode"
    | "summaryModeNode" | "summaryExternalLinkNode" | "summaryBodyNode" | "summaryGroundingNode"
  >;
  withThinkingWheel: AsyncTaskRunner;
  openModal: (modal: HTMLElement | null) => void;
  modalInterpretations: HTMLElement;
  modalSummary: HTMLElement;
}

export function createInterpretationModal(deps: InterpretationModalDeps) {
  const {
    i18n, state, dom, withThinkingWheel, openModal,
    modalInterpretations, modalSummary,
  } = deps;
  const {
    interpretationStatusNode, interpretationResultsNode,
    summaryModeNode, summaryExternalLinkNode, summaryBodyNode, summaryGroundingNode,
  } = dom;

  let interpretationRequestId = 0;
  let activeInterpretationCitation: Record<string, unknown> | null = null;
  let interpretationNextOffset = 0;
  let interpretationHasMore = false;
  let interpretationTotalAvailable = 0;

  function clearInterpretations(): void {
    interpretationRequestId += 1;
    activeInterpretationCitation = null;
    interpretationNextOffset = 0;
    interpretationHasMore = false;
    interpretationTotalAvailable = 0;
    interpretationStatusNode.textContent = i18n.t("chat.modal.interpretations.loading");
    interpretationResultsNode.innerHTML = "";
  }

  function clearSummary(): void {
    summaryModeNode.textContent = "-";
    summaryBodyNode.textContent = "Selecciona una interpretación para resumir.";
    summaryGroundingNode.innerHTML = "";
    summaryExternalLinkNode.hidden = true;
    summaryExternalLinkNode.removeAttribute("href");
  }

  function removeInterpretationMoreButton(): void {
    interpretationResultsNode.querySelector(".interpretation-more-btn")?.remove();
  }

  function updateInterpretationStatus(): void {
    const visibleCount = interpretationResultsNode.querySelectorAll(".interpretation-card").length;
    if (visibleCount === 0) return;
    if (interpretationTotalAvailable > visibleCount) {
      interpretationStatusNode.textContent = i18n.t("chat.interpretations.statusProgress", {
        visible: String(visibleCount),
        total: String(interpretationTotalAvailable),
      });
      return;
    }
    interpretationStatusNode.textContent = i18n.t("chat.interpretations.statusCount", {
      count: String(visibleCount),
    });
  }

  function interpretationAxisLabel(axis: unknown): string {
    const key = `chat.interpretations.axis.${String(axis || "").trim()}`;
    const translated = i18n.t(key);
    return translated === key ? String(axis || "").trim() : translated;
  }

  function interpretationRelevanceLabel(score: number): string {
    if (score >= 0.75) return i18n.t("chat.interpretations.relevance.high");
    if (score >= 0.5) return i18n.t("chat.interpretations.relevance.medium");
    return i18n.t("chat.interpretations.relevance.low");
  }

  function addGroundingLink(label: string, href: unknown): void {
    if (!href) return;
    const link = document.createElement("a");
    link.href = String(href);
    link.textContent = label;
    if (/^https?:\/\//i.test(link.href)) {
      link.target = "_blank";
      link.rel = "noopener noreferrer";
    }
    summaryGroundingNode.appendChild(link);
  }

  async function openSummaryModal(
    citation: Record<string, unknown>,
    interpretation: Record<string, unknown>,
    selectedLink = "",
  ): Promise<void> {
    clearSummary();
    openModal(modalSummary);
    summaryModeNode.textContent = "Procesando...";
    summaryBodyNode.textContent = "Generando resumen corpus-grounded...";

    const linkValue = String(selectedLink || "").trim();
    if (linkValue) {
      summaryExternalLinkNode.hidden = false;
      summaryExternalLinkNode.href = linkValue;
    }

    const payload = {
      citation: {
        doc_id: citation.doc_id,
        source_label: citation.source_label || citation.legal_reference || "",
        legal_reference: citation.legal_reference || "",
        topic: citation.topic || "",
        pais: citation.pais || "",
        authority: citation.authority || "",
      },
      interpretation: {
        doc_id: interpretation.doc_id,
        title: interpretation.title || "",
        url: linkValue || interpretation.official_url || "",
        selected_link: linkValue,
      },
      selected_link: linkValue,
      message_context: state.lastUserMessage,
    };

    try {
      const summaryResult = await withThinkingWheel(async () => {
        const response = await fetch("/api/interpretation-summary", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const data = await response.json();
        return { response, data };
      });
      const { response, data } = summaryResult;
      if (!response.ok) {
        const errorObj = data && typeof data.error === "object" ? data.error : null;
        const errorCode = String((errorObj && errorObj.code) || data.error || "interpretation_summary_failed");
        const errorMessage = String((errorObj && errorObj.message) || "No fue posible generar el resumen.");
        summaryModeNode.textContent = "error";
        summaryBodyNode.textContent = `Error ${errorCode}: ${errorMessage}`;
        return;
      }
      summaryModeNode.textContent = `mode=${data.mode || "unknown"}`;
      summaryBodyNode.textContent = data.summary_markdown || "Sin resumen.";
      const grounding = data.grounding && typeof data.grounding === "object" ? data.grounding : {};
      const citationGrounding = grounding.citation && typeof grounding.citation === "object" ? grounding.citation : {};
      const interpretationGrounding =
        grounding.interpretation && typeof grounding.interpretation === "object" ? grounding.interpretation : {};
      addGroundingLink("Norma en corpus", citationGrounding.source_view_url);
      addGroundingLink("Interpretación en corpus", interpretationGrounding.source_view_url);
      addGroundingLink("Fuente oficial interpretación", interpretationGrounding.official_url);
      const external = String(grounding.selected_external_link || "").trim();
      if (external) {
        summaryExternalLinkNode.hidden = false;
        summaryExternalLinkNode.href = external;
      }
    } catch (error) {
      summaryModeNode.textContent = "error";
      summaryBodyNode.textContent = `Error de conexión: ${error}`;
    }
  }

  function renderInterpretationCard(
    citation: Record<string, unknown>,
    item: Record<string, unknown>,
  ): HTMLElement {
    const article = document.createElement("article");
    article.className = "interpretation-card";

    const title = document.createElement("h4");
    title.className = "interpretation-title";
    title.textContent = String(item.title || item.doc_id || "Interpretación");
    article.appendChild(title);

    const providers = Array.isArray(item.providers)
      ? item.providers
          .filter((provider) => provider && typeof provider === "object")
          .map((provider) => String((provider as Record<string, unknown>).name || "").trim())
          .filter(Boolean)
      : [];
    const meta = document.createElement("div");
    meta.className = "interpretation-meta";

    const relevanceChip = document.createElement("span");
    relevanceChip.className = "interpretation-chip interpretation-chip--score";
    relevanceChip.textContent = interpretationRelevanceLabel(Number(item.relevance_score || 0));
    meta.appendChild(relevanceChip);

    const coverageAxes = Array.isArray(item.coverage_axes) ? item.coverage_axes : [];
    coverageAxes.slice(0, 4).forEach((axis) => {
      const chip = document.createElement("span");
      chip.className = "interpretation-chip";
      chip.textContent = interpretationAxisLabel(axis);
      meta.appendChild(chip);
    });
    article.appendChild(meta);

    const scoreText = [
      String(item.selection_reason || "").trim(),
      providers.join(", ") || String(item.authority || "").trim(),
    ].filter(Boolean).join(" · ");
    if (scoreText) {
      const score = document.createElement("p");
      score.className = "interpretation-score";
      score.textContent = scoreText;
      article.appendChild(score);
    }

    const snippet = document.createElement("p");
    snippet.className = "interpretation-snippet";
    snippet.textContent = stripMarkdown(String(item.card_summary || item.snippet || "Sin extracto disponible en corpus."));
    article.appendChild(snippet);

    const linksWrap = document.createElement("div");
    linksWrap.className = "interpretation-links";
    const providerLinks = Array.isArray(item.provider_links) ? item.provider_links : [];
    providerLinks.forEach((linkItem) => {
      if (!linkItem || typeof linkItem !== "object") return;
      const providerBtn = document.createElement("button");
      providerBtn.type = "button";
      providerBtn.className = "provider-link";
      providerBtn.textContent = String(linkItem.provider || linkItem.domain || "Fuente");
      providerBtn.title = String(linkItem.url || "");
      providerBtn.addEventListener("click", () => {
        void openSummaryModal(citation, item, String(linkItem.url || ""));
      });
      linksWrap.appendChild(providerBtn);
    });
    article.appendChild(linksWrap);

    const actionWrap = document.createElement("div");
    actionWrap.className = "interpretation-actions";

    const openDocBtn = document.createElement("button");
    openDocBtn.type = "button";
    openDocBtn.className = "secondary-btn";
    openDocBtn.textContent = i18n.t("chat.summary.openDoc");
    openDocBtn.disabled = !item.open_url;
    openDocBtn.addEventListener("click", () => {
      if (item.open_url) window.open(String(item.open_url), "_blank", "noopener,noreferrer");
    });
    actionWrap.appendChild(openDocBtn);

    const summarizeBtn = document.createElement("button");
    summarizeBtn.type = "button";
    summarizeBtn.className = "primary-btn";
    summarizeBtn.textContent = i18n.t("chat.summary.summarize");
    summarizeBtn.addEventListener("click", () => void openSummaryModal(citation, item, ""));
    actionWrap.appendChild(summarizeBtn);

    article.appendChild(actionWrap);
    return article;
  }

  function renderInterpretationLoadMoreButton(citation: Record<string, unknown>): void {
    removeInterpretationMoreButton();
    if (!interpretationHasMore) return;
    const visibleCount = interpretationResultsNode.querySelectorAll(".interpretation-card").length;
    const remaining = Math.max(0, interpretationTotalAvailable - visibleCount);
    const nextBatchSize = Math.min(3, remaining || 3);
    const moreBtn = document.createElement("button");
    moreBtn.type = "button";
    moreBtn.className = "secondary-btn interpretation-more-btn";
    moreBtn.textContent = i18n.t("chat.interpretations.loadMore", { count: String(nextBatchSize) });
    moreBtn.addEventListener("click", async () => {
      moreBtn.disabled = true;
      moreBtn.textContent = i18n.t("chat.interpretations.loadMore.loading");
      const ok = await fetchInterpretationsPage(citation, {
        offset: interpretationNextOffset,
        limit: 3,
        append: true,
        useThinkingWheel: false,
      });
      if (!ok) {
        moreBtn.disabled = false;
        moreBtn.textContent = i18n.t("chat.interpretations.loadMore.retry");
      }
    });
    interpretationResultsNode.appendChild(moreBtn);
  }

  async function fetchInterpretationsPage(
    citation: Record<string, unknown>,
    opts: { offset: number; limit: number; append: boolean; useThinkingWheel: boolean },
  ): Promise<boolean> {
    const citationDocId = String(citation?.doc_id || "").trim();
    if (!citationDocId) return false;
    activeInterpretationCitation = citation;
    const requestId = ++interpretationRequestId;
    removeInterpretationMoreButton();

    const payload = {
      citation,
      message_context: state.lastUserMessage,
      assistant_answer: state.lastAssistantAnswerMarkdown || "",
      process_limit: opts.limit,
      offset: opts.offset,
    };

    try {
      const runRequest = async () => {
        const response = await fetch("/api/citation-interpretations", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const data = await response.json();
        return { response, data };
      };
      const interpretationsResult = opts.useThinkingWheel
        ? await withThinkingWheel(runRequest)
        : await runRequest();
      const { response, data } = interpretationsResult;

      if (requestId !== interpretationRequestId) return false;
      if (String(activeInterpretationCitation?.doc_id || "").trim() !== citationDocId) return false;

      if (!response.ok) {
        interpretationStatusNode.textContent = `Error: ${data.error || "citation_interpretations_failed"}`;
        return false;
      }

      const items = Array.isArray(data.interpretations) ? data.interpretations : [];
      if (!opts.append) interpretationResultsNode.innerHTML = "";

      interpretationHasMore = Boolean(data.has_more);
      interpretationNextOffset = Number.isFinite(Number(data.next_offset))
        ? Number(data.next_offset)
        : opts.offset + items.length;

      if (items.length === 0 && !opts.append) {
        interpretationTotalAvailable = 0;
        interpretationStatusNode.textContent = i18n.t("chat.interpretations.emptyStrict");
        const emptyState = document.createElement("article");
        emptyState.className = "interpretation-card";
        emptyState.textContent = i18n.t("chat.interpretations.nextStep");
        interpretationResultsNode.appendChild(emptyState);
        return true;
      }

      items.forEach((item) => {
        if (!item || typeof item !== "object") return;
        interpretationResultsNode.appendChild(renderInterpretationCard(citation, item));
      });

      const visibleCount = interpretationResultsNode.querySelectorAll(".interpretation-card").length;
      interpretationTotalAvailable = Math.max(Number(data.total_available || 0), visibleCount);
      updateInterpretationStatus();
      renderInterpretationLoadMoreButton(citation);
      return true;
    } catch (error) {
      if (requestId !== interpretationRequestId) return false;
      interpretationStatusNode.textContent = i18n.t("chat.interpretations.errorConnection", {
        message: String(error),
      });
      return false;
    }
  }

  async function openInterpretationsModal(citation: Record<string, unknown>): Promise<void> {
    clearInterpretations();
    openModal(modalInterpretations);
    await fetchInterpretationsPage(citation, {
      offset: 0,
      limit: 5,
      append: false,
      useThinkingWheel: true,
    });
  }

  return {
    clearInterpretations,
    clearSummary,
    openInterpretationsModal,
    openSummaryModal,
  };
}
