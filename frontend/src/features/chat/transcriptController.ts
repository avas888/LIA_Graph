// @ts-nocheck

import {
  applyKernelHierarchyFormattingMarkdown,
  splitAnswerFromFollowupSection,
  stripInlineEvidenceAnnotations,
} from "@/features/chat/formatting";
import { isMobile } from "@/app/mobile/detectMobile";
import { boldNormativeReferencesMarkdown } from "@/features/chat/citations";
import {
  normalizeAssistantMeta,
  normalizeDocsUsed,
  normalizeFeedbackRatingValue,
  normalizeLayerContributions,
  normalizeTranscriptEntry,
  updateTranscriptFeedbackByTraceId,
} from "@/features/chat/persistence";
import { appendMarkdown, renderMarkdown, createSmartScroller } from "@/content/markdown";
import type { SmartScrollController } from "@/content/markdown";
import { getJson, postJson } from "@/shared/api/client";
import { createButton, createIconButton } from "@/shared/ui/atoms/button";
import { createTextarea } from "@/shared/ui/atoms/input";
import { icons } from "@/shared/ui/icons";
import type { I18nRuntime } from "@/shared/i18n";
import { bogotaParts } from "@/shared/dates";

const ACTION_ICON_SVG_NS = "http://www.w3.org/2000/svg";

const _MONTHS_ES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];

function formatBubbleTimestamp(iso: string): string {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "";
  const p = bogotaParts(d);
  const ampm = p.hour >= 12 ? "p.m." : "a.m.";
  const h = p.hour % 12 || 12;
  return `${p.day} ${_MONTHS_ES[p.month]}, ${h}:${String(p.minute).padStart(2, "0")} ${ampm}`;
}

type BubbleRole = "user" | "assistant";

type AddBubbleOptions = {
  meta?: Record<string, unknown> | null;
  persist?: boolean;
  skipScroll?: boolean;
  previousUserMessage?: string;
  deferAssistantRender?: boolean;
  onAssistantRenderComplete?: () => void;
  timestamp?: string;
};

type StreamingAssistantBubbleOptions = {
  meta?: Record<string, unknown> | null;
  previousUserMessage?: string;
};

type FinalizeStreamingAssistantOptions = {
  finalMarkdown: string;
  meta?: Record<string, unknown> | null;
  persist?: boolean;
  previousUserMessage?: string;
};

type StreamingAssistantBubbleController = {
  appendMarkdownBlock: (markdown: string) => Promise<void>;
  replaceMarkdown: (markdown: string) => Promise<void>;
  finalize: (options: FinalizeStreamingAssistantOptions) => Promise<void>;
  setStatus: (message: string) => void;
  clearStatus: () => void;
  getNode: () => HTMLElement;
};

type BubbleScaffold = {
  node: HTMLElement;
  bubbleTextNode: HTMLElement;
  meta: AssistantBubbleMeta;
  timestamp: string;
};

type AssistantBubbleMeta = {
  trace_id: string;
  chat_run_id: string;
  session_id: string;
  requested_topic: string;
  effective_topic: string;
  topic_adjusted: boolean;
  pais: string;
  docs_used: string[];
  layer_contributions: Record<string, number>;
  pain_detected: string;
  task_detected: string;
  feedback_rating: number | null;
  question_text: string;
  response_route: string;
  coverage_notice: string;
} | null;

type FeedbackState = {
  traceId: string;
  sessionId: string;
  markdown: string;
  docsUsed: string[];
  layerContributions: Record<string, number>;
  painDetected: string;
  taskDetected: string;
  rating: number | null;
  questionText: string;
  inFlight: boolean;
  copyBtn: HTMLButtonElement | null;
  ratingBtns: HTMLButtonElement[];
  commentPopupNode: HTMLElement | null;
  statusNode: HTMLElement | null;
};

type FeedbackGetResponse = {
  feedback?: {
    rating?: number;
  } | null;
};

type CreateChatTranscriptControllerOptions = {
  i18n: I18nRuntime;
  chatLog: HTMLElement;
  bubbleTemplate: HTMLTemplateElement;
  feedbackGetRoute: string;
  feedbackPostRoute: string;
  feedbackRatingUp: number;
  feedbackRatingDown: number;
  setActiveSessionId: (value: string) => void;
  updateChatLogEmptyState: () => void;
  onTranscriptEntriesChanged?: () => void;
};

function stripFollowupSuggestionLines(markdown: unknown): string {
  return splitAnswerFromFollowupSection(markdown).answer;
}

function flattenMarkdownForClipboard(markdown: unknown): string {
  const source = stripFollowupSuggestionLines(stripInlineEvidenceAnnotations(String(markdown || "")));
  if (!source) return "";

  const decoded = document.createElement("textarea");
  decoded.innerHTML = source;

  return decoded.value
    .replace(/\r\n/g, "\n")
    .replace(/```(?:[\w-]+)?\n?/g, "")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/!\[([^\]]*)\]\([^)]+\)/g, "$1")
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, "$1")
    .replace(/<\/?u>/gi, "")
    .replace(/<\/?[^>]+>/g, "")
    .replace(/^\s{0,3}#{1,6}\s+/gm, "")
    .replace(/^\s*>\s?/gm, "")
    .replace(/^\s*[-*+]\s+/gm, "• ")
    .replace(/^\s*(\d+)\)\s+/gm, "$1. ")
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/__([^_]+)__/g, "$1")
    .replace(/\*([^*\n]+)\*/g, "$1")
    .replace(/_([^_\n]+)_/g, "$1")
    .replace(/~~([^~]+)~~/g, "$1")
    .replace(/\*\*/g, "")
    .replace(/__/g, "")
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

export function formatConversationCopyPayload(
  questionText: unknown,
  answerMarkdown: unknown,
  i18n: I18nRuntime
): string {
  const question = String(questionText || "").trim();
  const answer = flattenMarkdownForClipboard(answerMarkdown);
  const sections = [
    `${i18n.t("chat.feedback.questionLabel")}:`,
    "",
    question,
    "",
    `${i18n.t("chat.feedback.answerLabel")}:`,
    "",
    answer,
  ];
  return sections.join("\n").replace(/\n{3,}/g, "\n\n").trim();
}

export function createChatTranscriptController({
  i18n,
  chatLog,
  bubbleTemplate,
  feedbackGetRoute,
  feedbackPostRoute,
  feedbackRatingUp,
  feedbackRatingDown,
  setActiveSessionId,
  updateChatLogEmptyState,
  onTranscriptEntriesChanged,
}: CreateChatTranscriptControllerOptions) {
  let transcriptEntries: Array<{ role: BubbleRole; text: string; meta: AssistantBubbleMeta }> = [];
  let renderedBubbleNodes: HTMLElement[] = [];
  const feedbackRestoreCache = new Map<string, Promise<number | null>>();
  const smartScroller = createSmartScroller(chatLog);

  function waitForNextPaint(): Promise<void> {
    return new Promise((resolve) => {
      if (typeof window === "undefined" || typeof window.requestAnimationFrame !== "function") {
        window.setTimeout(resolve, 0);
        return;
      }
      window.requestAnimationFrame(() => resolve());
    });
  }

  async function renderAssistantMarkdown(container: HTMLElement, text: unknown, skipScroll = false): Promise<void> {
    const markdown = String(text || "");
    try {
      await renderMarkdown(container, markdown, {
        scrollContainer: skipScroll ? null : chatLog,
      });
    } catch (_error) {
      container.textContent = markdown;
    }
  }

  function formatAssistantMarkdown(text: unknown): string {
    const raw = String(text || "");
    if (!raw.trim()) return "";
    // Fast-path: skip evidence strip when no evidence tags present
    const lower = raw.toLowerCase();
    const answerText = (lower.includes("[evidencia:") || lower.includes("[evidence:"))
      ? stripInlineEvidenceAnnotations(raw)
      : raw;
    if (!answerText.trim()) return "";
    // Fast-path: skip followup strip when no followup section marker present
    const displayMarkdown = lower.includes("sugerencias de consultas adicionales")
      ? stripFollowupSuggestionLines(answerText)
      : answerText;
    const kernelFormatted = applyKernelHierarchyFormattingMarkdown(displayMarkdown || answerText);
    return boldNormativeReferencesMarkdown(kernelFormatted);
  }

  function resolveAssistantBubbleMeta(
    role: BubbleRole,
    options: {
      meta?: Record<string, unknown> | null;
      previousUserMessage?: string;
    } = {}
  ): AssistantBubbleMeta {
    if (role !== "assistant") return null;
    const assistantMetaRaw = {
      ...(options.meta && typeof options.meta === "object" ? options.meta : {}),
      question_text: String(
        options.previousUserMessage ||
          (options.meta && typeof options.meta === "object" ? options.meta.question_text : "") ||
          ""
      ).trim(),
    };
    return normalizeAssistantMeta(assistantMetaRaw || {});
  }

  function createBubbleScaffold(
    role: BubbleRole,
    options: {
      meta?: Record<string, unknown> | null;
      previousUserMessage?: string;
      skipScroll?: boolean;
      timestamp?: string;
    } = {}
  ): BubbleScaffold | null {
    const templateNode = bubbleTemplate.content.firstElementChild;
    if (!(templateNode instanceof HTMLElement)) return null;

    const node = templateNode.cloneNode(true);
    if (!(node instanceof HTMLElement)) return null;

    const bubbleTextNode = node.querySelector(".bubble-text");
    if (!(bubbleTextNode instanceof HTMLElement)) return null;

    node.classList.add(role === "user" ? "bubble-user" : "bubble-assistant");

    const roleNode = node.querySelector(".bubble-role");
    if (roleNode) {
      roleNode.textContent = role === "user" ? "Tú" : "LIA";
    }

    const timestamp = options.timestamp || new Date().toISOString();
    const timestampNode = node.querySelector(".bubble-timestamp");
    if (timestampNode) {
      timestampNode.textContent = formatBubbleTimestamp(timestamp);
    }
    node.dataset.timestamp = timestamp;

    const meta = resolveAssistantBubbleMeta(role, {
      meta: options.meta,
      previousUserMessage: options.previousUserMessage,
    });

    chatLog.appendChild(node);
    if (!options.skipScroll) {
      smartScroller.scrollToBottom();
    }
    updateChatLogEmptyState();

    return {
      node,
      bubbleTextNode,
      meta,
      timestamp,
    };
  }

  function assignTranscriptIndex(node: HTMLElement | null, transcriptIndex: number): void {
    if (!(node instanceof HTMLElement) || !Number.isInteger(transcriptIndex) || transcriptIndex < 0) return;
    node.dataset.transcriptIndex = String(transcriptIndex);
    node.id = `chat-transcript-entry-${transcriptIndex}`;
    renderedBubbleNodes[transcriptIndex] = node;
  }

  function markTranscriptPair(userTranscriptIndex: number, assistantTranscriptIndex: number): void {
    renderedBubbleNodes.forEach((node, index) => {
      if (!(node instanceof HTMLElement)) return;
      const isTarget =
        index === userTranscriptIndex || (Number.isInteger(assistantTranscriptIndex) && index === assistantTranscriptIndex);
      node.classList.toggle("is-transcript-target", isTarget);
    });
  }

  async function hydrateAssistantBubble(node: HTMLElement, bubbleTextNode: HTMLElement, options: {
    answerText: string;
    meta: AssistantBubbleMeta;
    skipScroll?: boolean;
  }): Promise<void> {
    const answerText = stripInlineEvidenceAnnotations(String(options.answerText || ""));
    const coverageNotice = String(options.meta?.coverage_notice || "").trim();
    node.querySelectorAll(".bubble-coverage-notice").forEach((element) => element.remove());
    if (coverageNotice) {
      const coverageNode = document.createElement("div");
      coverageNode.className = "bubble-coverage-notice";
      coverageNode.textContent = coverageNotice;
      bubbleTextNode.before(coverageNode);
    }
    await renderAssistantMarkdown(bubbleTextNode, formatAssistantMarkdown(answerText), options.skipScroll);

    renderAssistantActions(node, answerText, options.meta);
  }

  function persistTranscriptEntry(
    role: BubbleRole,
    text: string,
    meta: AssistantBubbleMeta,
    timestamp: string | null,
    persist = true,
    node: HTMLElement | null = null
  ): number {
    if (!persist) return -1;
    const normalizedEntry = normalizeTranscriptEntry({ role, text, timestamp, meta });
    if (normalizedEntry) {
      transcriptEntries = [...transcriptEntries, normalizedEntry];
      const transcriptIndex = transcriptEntries.length - 1;
      assignTranscriptIndex(node, transcriptIndex);
      onTranscriptEntriesChanged?.();
      return transcriptIndex;
    }
    return -1;
  }

  function feedbackVoteForRating(rating: unknown): number | null {
    const parsed = normalizeFeedbackRatingValue(rating);
    if (parsed === null) return null;
    return Math.max(1, Math.min(5, parsed));
  }

  function setBubbleActionStatus(state: FeedbackState, message: unknown, isError = false): void {
    if (!state.statusNode) return;
    state.statusNode.textContent = String(message || "");
    state.statusNode.classList.toggle("is-error", Boolean(isError));
  }

  function applyFeedbackVisualState(state: FeedbackState): void {
    state.ratingBtns.forEach((btn, idx) => {
      btn.classList.toggle("is-active", typeof state.rating === "number" && state.rating >= idx + 1);
    });
  }

  function applyAssistantActionDisabledState(state: FeedbackState): void {
    const noTrace = !state.traceId;
    state.ratingBtns.forEach((btn) => {
      btn.disabled = state.inFlight || noTrace;
    });
  }

  function buildFeedbackPayload(state: FeedbackState, rating: number) {
    return {
      trace_id: state.traceId,
      session_id: state.sessionId || null,
      rating,
      tags: [],
      comment: "",
      docs_used: [...state.docsUsed],
      layer_contributions: { ...state.layerContributions },
      pain_detected: state.painDetected,
      task_detected: state.taskDetected,
      question_text: state.questionText,
      answer_text: state.markdown,
    };
  }

  async function postFeedbackRating(state: FeedbackState, rating: number): Promise<unknown> {
    const { response, data } = await postJson(feedbackPostRoute, buildFeedbackPayload(state, rating));
    if (!response.ok) {
      throw new Error((data && typeof data === "object" && "error" in data && String(data.error)) || "feedback_request_failed");
    }
    return data;
  }

  async function fetchFeedbackByTraceId(traceId: unknown): Promise<number | null> {
    const trace = String(traceId || "").trim();
    if (!trace) return null;
    if (feedbackRestoreCache.has(trace)) {
      return feedbackRestoreCache.get(trace) as Promise<number | null>;
    }
    const request = (async () => {
      const data = await getJson<FeedbackGetResponse>(`${feedbackGetRoute}?trace_id=${encodeURIComponent(trace)}`);
      const rating = Number(data?.feedback?.rating);
      return Number.isFinite(rating) ? Math.max(1, Math.min(5, Math.trunc(rating))) : null;
    })();
    feedbackRestoreCache.set(trace, request);
    return request;
  }

  async function restoreFeedbackForBubbleState(state: FeedbackState): Promise<void> {
    if (!state.traceId) return;
    try {
      const storedRating = await fetchFeedbackByTraceId(state.traceId);
      state.rating = storedRating;
      if (storedRating !== null && Number.isFinite(storedRating)) {
        transcriptEntries = updateTranscriptFeedbackByTraceId(transcriptEntries, state.traceId, Number(storedRating));
        onTranscriptEntriesChanged?.();
        // Already rated — remove prompt, rating widget and hints, keep copy button
        const actionsNode = state.ratingBtns[0]?.closest(".bubble-actions");
        if (actionsNode) {
          actionsNode.querySelectorAll(".bubble-rating-prompt, .bubble-rating-widget, .bubble-rating-hint").forEach((el) => el.remove());
          state.ratingBtns = [];
        }
      } else {
        applyFeedbackVisualState(state);
      }
    } catch (error) {
      console.warn("No se pudo restaurar feedback:", error);
    }
  }

  function createActionIcon(variant: string): SVGElement {
    const svg = document.createElementNS(ACTION_ICON_SVG_NS, "svg");
    svg.setAttribute("viewBox", "0 0 20 20");
    svg.setAttribute("aria-hidden", "true");
    svg.setAttribute("focusable", "false");

    const path = document.createElementNS(ACTION_ICON_SVG_NS, "path");
    path.setAttribute("fill", "none");
    path.setAttribute("stroke", "currentColor");
    path.setAttribute("stroke-linecap", "round");
    path.setAttribute("stroke-linejoin", "round");
    path.setAttribute("stroke-width", "1.7");

    if (variant === "copy") {
      path.setAttribute(
        "d",
        "M7.5 5.5h6a1.5 1.5 0 0 1 1.5 1.5v8a1.5 1.5 0 0 1-1.5 1.5h-6A1.5 1.5 0 0 1 6 15V7a1.5 1.5 0 0 1 1.5-1.5Zm-3 9V5A1.5 1.5 0 0 1 6 3.5h6"
      );
      svg.appendChild(path);
      return svg;
    }

    if (variant === "thumb_up") {
      path.setAttribute(
        "d",
        "M7 17.2H4.5a1 1 0 0 1-1-1v-6.1a1 1 0 0 1 1-1H7m0 8.1V9.1m0 8.1h6.1a1.5 1.5 0 0 0 1.4-1l1.2-3.8a1.5 1.5 0 0 0-1.4-2H11V6.7c0-1-.4-2-1.1-2.7L8.8 2.9 7 4.8v4.3"
      );
      svg.appendChild(path);
      return svg;
    }

    if (variant === "retry") {
      path.setAttribute(
        "d",
        "M3.5 10a6.5 6.5 0 0 1 11.3-4.4M16.5 10a6.5 6.5 0 0 1-11.3 4.4M14.8 3v2.6h-2.6M5.2 17v-2.6h2.6"
      );
      svg.appendChild(path);
      return svg;
    }

    path.setAttribute(
      "d",
      "M13 2.8h2.5a1 1 0 0 1 1 1v6.1a1 1 0 0 1-1 1H13m0-8.1v8.1m0-8.1H6.9a1.5 1.5 0 0 0-1.4 1L4.3 7.6a1.5 1.5 0 0 0 1.4 2H9v3.7c0 1 .4 2 1.1 2.7l1.1 1.1 1.8-1.9v-4.3"
    );
    svg.appendChild(path);
    return svg;
  }

  function createActionButton(label: string, variant: string): HTMLButtonElement {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "bubble-action-btn";
    button.setAttribute("aria-label", label);
    button.setAttribute("title", label);
    button.dataset.action = String(variant || "").trim();
    button.appendChild(createActionIcon(variant));
    return button;
  }

  async function onCopyAssistantBubble(state: FeedbackState): Promise<void> {
    const payload = formatConversationCopyPayload(state.questionText, state.markdown, i18n);
    if (!payload) return;
    try {
      await navigator.clipboard.writeText(payload);
      state.copyBtn?.classList.add("is-copy-done");
      setBubbleActionStatus(state, i18n.t("chat.feedback.copied"));
      window.setTimeout(() => {
        state.copyBtn?.classList.remove("is-copy-done");
        setBubbleActionStatus(state, "");
      }, 1000);
    } catch (error) {
      setBubbleActionStatus(state, i18n.t("chat.feedback.copyError"), true);
      console.error("Copy failed:", error);
    }
  }

  async function onRatingClick(state: FeedbackState, rating: number): Promise<void> {
    if (!state.traceId || state.inFlight) return;
    if (state.rating === rating) return;
    const previous = state.rating;
    state.rating = rating;
    state.inFlight = true;
    applyFeedbackVisualState(state);
    applyAssistantActionDisabledState(state);
    setBubbleActionStatus(state, i18n.t("chat.feedback.saving"));
    try {
      await postFeedbackRating(state, rating);
      transcriptEntries = updateTranscriptFeedbackByTraceId(transcriptEntries, state.traceId, rating);
      onTranscriptEntriesChanged?.();
      setBubbleActionStatus(state, i18n.t("chat.feedback.saved"));
      showCommentPopup(state);
      window.setTimeout(() => {
        if (state.statusNode?.textContent === i18n.t("chat.feedback.saved")) {
          setBubbleActionStatus(state, "");
        }
      }, 2000);
    } catch (error) {
      state.rating = previous;
      applyFeedbackVisualState(state);
      setBubbleActionStatus(state, i18n.t("chat.feedback.saveError"), true);
      console.error("Feedback submit failed:", error);
    } finally {
      state.inFlight = false;
      applyAssistantActionDisabledState(state);
    }
  }

  function burnFeedbackBar(state: FeedbackState): void {
    state.commentPopupNode?.remove();
    state.commentPopupNode = null;
    const actionsNode = state.ratingBtns[0]?.closest(".bubble-actions");
    if (!actionsNode) return;

    // Remove prompt, rating widget and hints — keep copy button + status
    actionsNode.querySelectorAll(".bubble-rating-prompt, .bubble-rating-widget, .bubble-rating-hint").forEach((el) => el.remove());
    state.ratingBtns = [];

    // Add thank-you banner inline
    const banner = document.createElement("span");
    banner.className = "bubble-feedback-thanks";
    banner.textContent = i18n.t("chat.feedback.thanks") + " 🙏";
    // Insert after copy button, before status
    if (state.statusNode) {
      state.statusNode.before(banner);
    } else {
      actionsNode.append(banner);
    }

    // Fade out the banner after 2.5s
    window.setTimeout(() => {
      banner.classList.add("is-fading");
      banner.addEventListener("transitionend", () => banner.remove(), { once: true });
      window.setTimeout(() => banner.remove(), 600);
    }, 2500);
  }

  function showCommentPopup(state: FeedbackState): void {
    state.commentPopupNode?.remove();

    const popup = document.createElement("div");
    popup.className = "bubble-comment-popup";

    const textarea = createTextarea({
      className: "bubble-comment-textarea",
      placeholder: i18n.t("chat.feedback.commentPlaceholder"),
      rows: 2,
      maxlength: 500,
    });

    const sendBtn = createIconButton({
      iconHtml: icons.send,
      tone: "ghost",
      className: "bubble-comment-send",
      attrs: { "aria-label": i18n.t("chat.feedback.sendComment") },
    });

    sendBtn.addEventListener("click", async () => {
      const comment = textarea.value.trim();
      if (!comment) {
        popup.remove();
        state.commentPopupNode = null;
        burnFeedbackBar(state);
        return;
      }
      sendBtn.disabled = true;
      try {
        await postJson("/api/feedback/comment", { trace_id: state.traceId, comment });
        popup.remove();
        state.commentPopupNode = null;
        setBubbleActionStatus(state, i18n.t("chat.feedback.commentSaved"));
        burnFeedbackBar(state);
        window.setTimeout(() => {
          if (state.statusNode?.textContent === i18n.t("chat.feedback.commentSaved")) {
            setBubbleActionStatus(state, "");
          }
        }, 1200);
      } catch {
        setBubbleActionStatus(state, i18n.t("chat.feedback.commentError"), true);
      } finally {
        sendBtn.disabled = false;
      }
    });

    const dismissHandler = (e: MouseEvent) => {
      if (!popup.contains(e.target as Node)) {
        popup.remove();
        state.commentPopupNode = null;
        document.removeEventListener("click", dismissHandler);
        burnFeedbackBar(state);
      }
    };
    window.setTimeout(() => document.addEventListener("click", dismissHandler), 0);

    popup.append(textarea, sendBtn);
    state.commentPopupNode = popup;

    const actionsNode = state.ratingBtns[0]?.closest(".bubble-actions");
    if (actionsNode) {
      actionsNode.after(popup);
    }
    textarea.focus();
    requestAnimationFrame(() => {
      popup.scrollIntoView({ block: "nearest", behavior: "smooth" });
    });
  }

  function renderAssistantActions(node: HTMLElement, answerText: string, meta: AssistantBubbleMeta): void {
    const actionsNode = node.querySelector(".bubble-actions");
    if (!(actionsNode instanceof HTMLElement)) return;
    actionsNode.innerHTML = "";

    const state: FeedbackState = {
      traceId: String(meta?.trace_id || "").trim(),
      sessionId: String(meta?.session_id || "").trim(),
      markdown: String(answerText || ""),
      docsUsed: normalizeDocsUsed(meta?.docs_used || []),
      layerContributions: normalizeLayerContributions(meta?.layer_contributions),
      painDetected: String(meta?.pain_detected || "").trim(),
      taskDetected: String(meta?.task_detected || "").trim(),
      rating: feedbackVoteForRating(meta?.feedback_rating),
      questionText: String(meta?.question_text || "").trim(),
      inFlight: false,
      copyBtn: null,
      ratingBtns: [],
      commentPopupNode: null,
      statusNode: null,
    };

    if (!state.markdown) {
      actionsNode.hidden = true;
      return;
    }

    actionsNode.hidden = false;

    const copyBtn = createActionButton(i18n.t("chat.feedback.copyConversation"), "copy");
    const statusNode = document.createElement("span");
    statusNode.className = "bubble-action-status";
    statusNode.setAttribute("aria-live", "polite");

    state.copyBtn = copyBtn;
    state.statusNode = statusNode;

    copyBtn.addEventListener("click", () => {
      void onCopyAssistantBubble(state);
    });

    if (state.traceId) {
      const promptLabel = document.createElement("span");
      promptLabel.className = "bubble-rating-prompt";
      promptLabel.textContent = i18n.t("chat.feedback.ratingPrompt");

      const ratingRow = document.createElement("div");
      ratingRow.className = "bubble-rating-row";

      const ratingWidget = document.createElement("div");
      ratingWidget.className = "bubble-rating-widget";

      const badLabel = document.createElement("span");
      badLabel.className = "bubble-rating-hint bubble-rating-hint--low";
      badLabel.textContent = i18n.t("chat.feedback.ratingBad");

      const goodLabel = document.createElement("span");
      goodLabel.className = "bubble-rating-hint bubble-rating-hint--high";
      goodLabel.textContent = i18n.t("chat.feedback.ratingGood");

      for (let n = 1; n <= 5; n++) {
        const ratingValue = n;
        const btn = createIconButton({
          iconHtml: icons.starOutline,
          tone: "ghost",
          className: "bubble-rating-btn",
          attrs: {
            "data-rating": String(n),
            "aria-label": `${n}${n === 1 ? " — " + i18n.t("chat.feedback.ratingBad") : n === 5 ? " — " + i18n.t("chat.feedback.ratingGood") : ""}`,
          },
          onClick: () => {
            void onRatingClick(state, ratingValue);
          },
        });
        ratingWidget.appendChild(btn);
        state.ratingBtns.push(btn);
      }

      ratingRow.append(badLabel, ratingWidget, goodLabel);

      const copyRow = document.createElement("div");
      copyRow.className = "bubble-copy-row";
      copyRow.append(copyBtn, statusNode);

      actionsNode.append(promptLabel, ratingRow, copyRow);
    } else {
      // Error bubble — add retry button if the bubble is retryable
      const isRetryable = node.dataset.retryable === "true";
      if (isRetryable) {
        const retryBtn = document.createElement("button");
        retryBtn.type = "button";
        retryBtn.className = "bubble-retry-btn";
        retryBtn.appendChild(createActionIcon("retry"));
        const retryLabel = document.createElement("span");
        retryLabel.textContent = i18n.t("chat.chat.retry");
        retryBtn.appendChild(retryLabel);
        retryBtn.setAttribute("aria-label", i18n.t("chat.chat.retry"));
        retryBtn.addEventListener("click", () => {
          retryBtn.disabled = true;
          retryBtn.classList.add("is-retrying");
          retryLabel.textContent = i18n.t("chat.chat.retryInProgress");
          node.dispatchEvent(new CustomEvent("lia:retry-turn", { bubbles: true }));
        });
        actionsNode.append(retryBtn, copyBtn, statusNode);
      } else {
        actionsNode.append(copyBtn, statusNode);
      }
    }
    applyFeedbackVisualState(state);
    applyAssistantActionDisabledState(state);
    void restoreFeedbackForBubbleState(state);
  }

  function docsUsedFromCitations(rawCitations: unknown): string[] {
    if (!Array.isArray(rawCitations)) return [];
    return normalizeDocsUsed(
      rawCitations
        .map((citation) => String((citation as Record<string, unknown>)?.doc_id || "").trim())
        .filter((value) => value)
    );
  }

  function buildAssistantBubbleMeta(
    responseData: Record<string, unknown>,
    questionText = ""
  ): Record<string, unknown> {
    const payload = responseData && typeof responseData === "object" ? responseData : {};
    return {
      trace_id: String(payload.trace_id || "").trim(),
      chat_run_id: String(payload.chat_run_id || "").trim(),
      session_id: String(payload.session_id || (payload.session as Record<string, unknown> | undefined)?.session_id || "").trim(),
      requested_topic: String(payload.requested_topic || "").trim(),
      effective_topic: String(payload.effective_topic || payload.topic || "").trim(),
      topic_adjusted: Boolean(payload.topic_adjusted),
      pais: String(payload.pais || "").trim(),
      docs_used: docsUsedFromCitations(payload.citations),
      layer_contributions: normalizeLayerContributions(payload.layer_contributions),
      pain_detected: String(payload.pain_detected || "").trim(),
      task_detected: String(payload.task_detected || "").trim(),
      question_text: String(questionText || "").trim(),
      response_route: String(payload.response_route || "").trim(),
      coverage_notice: String(payload.coverage_notice || "").trim(),
    };
  }

  async function addBubble(role: BubbleRole, text: string, options: AddBubbleOptions = {}): Promise<HTMLElement | null> {
    const normalizedText = String(text || "");
    if (role === "assistant" && !normalizedText.trim()) {
      return null;
    }
    const scaffold = createBubbleScaffold(role, {
      meta: options.meta,
      previousUserMessage: options.previousUserMessage,
      skipScroll: options.skipScroll === true,
      timestamp: options.timestamp,
    });
    if (!scaffold) return null;

    const { node, bubbleTextNode, meta, timestamp } = scaffold;
    const isAssistant = role === "assistant";
    const persist = options.persist !== false;
    const deferAssistantRender = options.deferAssistantRender === true;

    if (isAssistant) {
      const notifyAssistantRenderComplete = (): void => {
        try {
          options.onAssistantRenderComplete?.();
        } catch (_error) {
          // Bubble render completion hooks should not break transcript rendering.
        }
      };
      const answerText = stripInlineEvidenceAnnotations(normalizedText);
      const renderTask = async (): Promise<void> => {
        await hydrateAssistantBubble(node, bubbleTextNode, {
          answerText,
          meta,
          skipScroll: options.skipScroll === true,
        });
      };

      if (deferAssistantRender) {
        await waitForNextPaint();
        void renderTask().catch(() => {
          bubbleTextNode.textContent = answerText;
        }).finally(() => {
          notifyAssistantRenderComplete();
        });
      } else {
        try {
          await renderTask();
        } finally {
          notifyAssistantRenderComplete();
        }
      }
    } else {
      bubbleTextNode.textContent = normalizedText;
    }

    persistTranscriptEntry(role, normalizedText, meta, timestamp, persist, node);
    return node;
  }

  function createStreamingAssistantBubble(
    options: StreamingAssistantBubbleOptions = {}
  ): StreamingAssistantBubbleController | null {
    const scaffold = createBubbleScaffold("assistant", {
      meta: options.meta,
      previousUserMessage: options.previousUserMessage,
      skipScroll: false,
    });
    if (!scaffold) return null;

    const { node, bubbleTextNode, timestamp: scaffoldTimestamp } = scaffold;
    node.classList.add("is-streaming");
    const statusNode = document.createElement("p");
    statusNode.className = "bubble-stream-status";
    statusNode.setAttribute("aria-live", "polite");
    statusNode.hidden = true;
    bubbleTextNode.after(statusNode);

    let finalized = false;
    let latestMarkdown = "";

    // Block batching: collect blocks and flush every 80ms or 4 blocks to reduce
    // per-block parse/sanitize/DOM overhead (~30-40% faster rendering).
    const _pendingBlocks: string[] = [];
    let _flushTimer: ReturnType<typeof setTimeout> | null = null;
    const _BATCH_FLUSH_MS = 80;
    const _BATCH_MAX_BLOCKS = 4;

    async function _flushPendingBlocks(): Promise<void> {
      if (_flushTimer !== null) {
        clearTimeout(_flushTimer);
        _flushTimer = null;
      }
      if (_pendingBlocks.length === 0 || finalized) return;
      const blocks = _pendingBlocks.splice(0);
      const combined = blocks.map((b) => formatAssistantMarkdown(b)).filter((b) => b.trim()).join("\n\n");
      if (!combined.trim()) return;
      for (const block of blocks) {
        const raw = String(block || "").trim();
        if (raw) {
          latestMarkdown = `${latestMarkdown}${latestMarkdown ? "\n\n" : ""}${raw}`.trim();
        }
      }
      try {
        await appendMarkdown(bubbleTextNode, combined, {
          smartScroller,
        });
      } catch (_error) {
        const fallbackNode = document.createElement("p");
        fallbackNode.textContent = stripInlineEvidenceAnnotations(blocks.join("\n\n"));
        bubbleTextNode.appendChild(fallbackNode);
        smartScroller.scrollIfTracking();
      }
    }

    async function appendMarkdownBlock(markdown: string): Promise<void> {
      if (finalized) return;
      const raw = String(markdown || "").trim();
      if (!raw) return;
      _pendingBlocks.push(raw);
      if (_pendingBlocks.length >= _BATCH_MAX_BLOCKS) {
        await _flushPendingBlocks();
        return;
      }
      if (_flushTimer === null) {
        _flushTimer = setTimeout(() => { _flushPendingBlocks(); }, _BATCH_FLUSH_MS);
      }
    }

    async function replaceMarkdown(markdown: string): Promise<void> {
      if (finalized) return;
      _pendingBlocks.length = 0;
      if (_flushTimer !== null) { clearTimeout(_flushTimer); _flushTimer = null; }
      latestMarkdown = String(markdown || "").trim();
      await renderAssistantMarkdown(bubbleTextNode, formatAssistantMarkdown(latestMarkdown));
    }

    async function finalize(finalOptions: FinalizeStreamingAssistantOptions): Promise<void> {
      if (finalized) return;
      await _flushPendingBlocks();
      finalized = true;
      statusNode.remove();
      const finalMarkdown = String(finalOptions.finalMarkdown || latestMarkdown || "").trim();
      const meta = resolveAssistantBubbleMeta("assistant", {
        meta: finalOptions.meta,
        previousUserMessage: finalOptions.previousUserMessage || options.previousUserMessage,
      });

      // Compare streamed vs final content to avoid unnecessary re-render (prevents visual jump)
      const streamedFormatted = formatAssistantMarkdown(latestMarkdown);
      const finalFormatted = formatAssistantMarkdown(finalMarkdown);
      if (streamedFormatted !== finalFormatted) {
        await hydrateAssistantBubble(node, bubbleTextNode, {
          answerText: finalMarkdown,
          meta,
          skipScroll: true,
        });
      } else {
        // Content matches — just add coverage notice + action buttons without re-rendering text
        const coverageNotice = String(meta?.coverage_notice || "").trim();
        node.querySelectorAll(".bubble-coverage-notice").forEach((el) => el.remove());
        if (coverageNotice) {
          const coverageNode = document.createElement("div");
          coverageNode.className = "bubble-coverage-notice";
          coverageNode.textContent = coverageNotice;
          bubbleTextNode.before(coverageNode);
        }
        renderAssistantActions(node, finalMarkdown, meta);
      }

      // Transition: streaming → complete
      node.classList.remove("is-streaming");
      node.classList.add("is-complete");

      // On mobile, scroll so the top of the response bubble is visible
      if (isMobile()) {
        requestAnimationFrame(() => {
          node.scrollIntoView({ block: "start", behavior: "smooth" });
        });
      }

      persistTranscriptEntry("assistant", finalMarkdown, meta, scaffoldTimestamp, finalOptions.persist !== false, node);
    }

    function setStatus(message: string): void {
      if (finalized) return;
      const normalized = String(message || "").trim();
      statusNode.textContent = normalized;
      statusNode.hidden = !normalized;
    }

    function clearStatus(): void {
      statusNode.textContent = "";
      statusNode.hidden = true;
    }

    return {
      appendMarkdownBlock,
      replaceMarkdown,
      finalize,
      setStatus,
      clearStatus,
      getNode: () => node,
    };
  }

  async function restoreTranscriptEntries(
    entries: Array<{ role: BubbleRole; text: string; timestamp?: string | null; meta: AssistantBubbleMeta }> = []
  ): Promise<boolean> {
    const normalizedEntries = Array.isArray(entries)
      ? entries.map((entry) => normalizeTranscriptEntry(entry)).filter(Boolean)
      : [];
    transcriptEntries = normalizedEntries;
    chatLog.innerHTML = "";
    let previousUserMessage = "";
    for (const entry of normalizedEntries) {
      if (entry.role === "user") {
        previousUserMessage = entry.text;
      }
      const bubble = await addBubble(entry.role, entry.text, {
        meta: entry.meta,
        persist: false,
        skipScroll: true,
        deferAssistantRender: false,
        timestamp: entry.timestamp || undefined,
        previousUserMessage:
          entry.role === "assistant" ? String(entry.meta?.question_text || previousUserMessage || "").trim() : "",
      });
      assignTranscriptIndex(bubble, renderedBubbleNodes.length);
    }
    smartScroller.scrollToBottom();
    updateChatLogEmptyState();
    return normalizedEntries.length > 0;
  }

  function resetTranscriptState(): void {
    feedbackRestoreCache.clear();
    transcriptEntries = [];
    renderedBubbleNodes = [];
  }

  function getTranscriptEntries(): Array<{ role: BubbleRole; text: string; timestamp?: string | null; meta: AssistantBubbleMeta }> {
    return transcriptEntries.map((entry) => ({
      role: entry.role,
      text: entry.text,
      timestamp: entry.timestamp || null,
      meta: entry.meta ? { ...entry.meta } : null,
    }));
  }

  function scrollToTranscriptPair(userTranscriptIndex: number, assistantTranscriptIndex: number): boolean {
    const userNode = renderedBubbleNodes[userTranscriptIndex];
    const assistantNode = renderedBubbleNodes[assistantTranscriptIndex];
    const primaryTargetNode = assistantNode instanceof HTMLElement ? assistantNode : userNode;
    if (!(primaryTargetNode instanceof HTMLElement)) return false;
    markTranscriptPair(userTranscriptIndex, assistantTranscriptIndex);
    chatLog.scrollTop = Math.max(0, primaryTargetNode.offsetTop - 16);
    return true;
  }

  function setBubbleQuestionId(transcriptIndex: number, questionId: string): void {
    const node = renderedBubbleNodes[transcriptIndex];
    if (!(node instanceof HTMLElement) || !questionId) return;
    node.dataset.questionId = questionId;
    node.classList.add("has-normativa");
    const indicator = node.querySelector(".bubble-normativa-indicator");
    if (indicator instanceof HTMLElement) {
      indicator.hidden = false;
    }
  }

  function updateBubbleSelectionState(activeQuestionId: string): void {
    const normalizedId = String(activeQuestionId || "").trim();
    renderedBubbleNodes.forEach((node) => {
      if (!(node instanceof HTMLElement)) return;
      const isActive = Boolean(normalizedId && node.dataset.questionId === normalizedId);
      node.classList.toggle("is-bubble-active", isActive);
    });
  }

  return {
    addBubble,
    buildAssistantBubbleMeta,
    createStreamingAssistantBubble,
    getTranscriptEntries,
    resetTranscriptState,
    restoreTranscriptEntries,
    scrollToTranscriptPair,
    setBubbleQuestionId,
    updateBubbleSelectionState,
  };
}
// @ts-nocheck
