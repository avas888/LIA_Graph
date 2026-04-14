// @ts-nocheck

/**
 * Session and question-entry management for the chat feature.
 * Extracted from chatApp.ts during decouple-v1 Phase 2.
 */

import {
  deriveFirstQuestionFromTranscriptEntries,
  deriveDetectedTopic,
  deriveThreadLabel,
  normalizeNormativeSupportCache,
} from "@/features/chat/persistence";
import {
  buildExpertPanelSearchSeed,
  expertPanelSupportCitationsFromSnapshot,
} from "@/features/chat/expertPanelSeed";
import { extractArticleRefs } from "@/features/chat/expertPanelController";
import { formatTokenUsage, normalizeTokenUsage } from "@/features/chat/requestController";
import type { ChatState, QuestionEntry, QuestionSnapshot, ExpertPanelLoadOptions } from "@/features/chat/chatTypes";
import { getAuthContext } from "@/shared/auth/authContext";
import { createButtonChip } from "@/shared/ui/atoms/chip";

export interface SessionControllerDeps {
  i18n: any;
  chatState: ChatState;
  sessionStore: any;
  chatSessionCacheLimit: number;
  /** DOM nodes */
  chatLog: HTMLElement;
  chatLogEmptyNode: HTMLElement;
  runtimeTurnTokensNode: HTMLElement | null;
  runtimeLatencyNode: HTMLElement | null;
  runtimeRequestTimerNode: HTMLElement | null;
  diagnosticsNode: HTMLElement | null;
  debugInput: HTMLInputElement | null;
  messageInput: HTMLTextAreaElement;
  sessionSwitcherNode: HTMLElement;
  chatSessionCountNode: HTMLElement;
  chatSessionDrawerNode: HTMLElement;
  chatSessionDrawerPanelNode: HTMLElement;
  chatSessionDrawerToggleNode: HTMLElement;
  expertPanelContentNode: HTMLElement;
  expertPanelStatusNode: HTMLElement;
  /** Sibling controllers */
  getActiveSessionId: () => string;
  setSurfaceActiveSessionId: (id: string) => void;
  isTurnInFlight: () => boolean;
  resizeComposer: () => void;
  updateWorkspaceControlsSummary: () => void;
  updateChatLogEmptyState: () => void;
  syncReadyState: () => void;
  focusComposer: () => void;
  resetTranscriptState: () => void;
  getTranscriptEntries: () => any[];
  restoreTranscriptEntries: (entries: any[]) => Promise<void>;
  scrollToTranscriptPair: (userIdx: number, assistantIdx: number) => void;
  setBubbleQuestionId?: (transcriptIndex: number, questionId: string) => void;
  updateBubbleSelectionState?: (activeQuestionId: string) => void;
  /** Request controller bridge */
  requestController: {
    stopRequestTimer: () => void;
    setActiveChatRunId: (id: string) => void;
    setConversationTotals: (totals: any, opts?: any) => void;
    clearNormativeSupportState: (opts?: any) => void;
    restoreNormativeSupportState: (ns: any) => void;
    getCurrentNormativeSupportSnapshot: () => any;
    hydrateRuntimeModelFromStatus: () => Promise<void>;
  };
  /** Expert panel bridge */
  expertPanel: {
    clear: () => void;
    restoreState: (state: any, fallbackOpts?: any) => void;
    getPersistedState: () => any;
  };
  /** Modal bridge */
  clearInterpretations: () => void;
  clearSummary: () => void;
  closeAllModals: () => void;
  /** Thinking overlay */
  thinkingOverlay: { stop: () => void };
  /** Citation renderer bridge */
  buildThreadCitationGroups: (entries: QuestionEntry[]) => any[];
  renderCitationsGrouped: (groups: any[]) => void;
  renderAccumulatedExpertPanel: (entries: QuestionEntry[], contentNode: HTMLElement, statusNode: HTMLElement) => void;
}

export function createChatSessionController(deps: SessionControllerDeps) {
  const {
    i18n,
    chatState,
    sessionStore,
    chatSessionCacheLimit,
    chatLog,
    chatLogEmptyNode,
    runtimeTurnTokensNode,
    runtimeLatencyNode,
    runtimeRequestTimerNode,
    diagnosticsNode,
    debugInput,
    messageInput,
    sessionSwitcherNode,
    chatSessionCountNode,
    chatSessionDrawerNode,
    chatSessionDrawerPanelNode,
    chatSessionDrawerToggleNode,
    expertPanelContentNode,
    expertPanelStatusNode,
    getActiveSessionId,
    setSurfaceActiveSessionId,
    isTurnInFlight,
    resizeComposer,
    updateWorkspaceControlsSummary,
    updateChatLogEmptyState,
    syncReadyState,
    focusComposer,
    resetTranscriptState,
    getTranscriptEntries,
    restoreTranscriptEntries,
    scrollToTranscriptPair,
    setBubbleQuestionId,
    updateBubbleSelectionState,
    requestController,
    expertPanel,
    clearInterpretations,
    clearSummary,
    closeAllModals,
    thinkingOverlay,
    buildThreadCitationGroups,
    renderCitationsGrouped,
    renderAccumulatedExpertPanel,
  } = deps;

  // ── Question entry helpers ──────────────────────────────────

  function normalizeSessionQuestion(value) {
    return String(value || "").replace(/\s+/g, " ").trim();
  }

  function cloneQuestionEntry(entry) {
    if (!entry || typeof entry !== "object") return null;
    return {
      questionId: String(entry.questionId || "").trim(),
      questionText: String(entry.questionText || "").trim(),
      userTranscriptIndex: Number(entry.userTranscriptIndex),
      assistantTranscriptIndex: Number(entry.assistantTranscriptIndex),
      traceId: String(entry.traceId || "").trim(),
      chatRunId: String(entry.chatRunId || entry.chat_run_id || "").trim(),
      effectiveTopic: String(entry.effectiveTopic || entry.effective_topic || "").trim(),
      pais: String(entry.pais || "").trim(),
      normativeSupport: normalizeNormativeSupportCache(entry.normativeSupport),
      expertPanelState: entry.expertPanelState ? JSON.parse(JSON.stringify(entry.expertPanelState)) : null,
      updatedAt: String(entry.updatedAt || "").trim(),
    };
  }

  function setActiveQuestionId(questionId) {
    chatState.activeQuestionId = String(questionId || "").trim();
  }

  function getQuestionEntries(): QuestionEntry[] {
    return Array.isArray(chatState.questionEntries)
      ? chatState.questionEntries.map((entry) => cloneQuestionEntry(entry)).filter(Boolean)
      : [];
  }

  function replaceQuestionEntries(entries, activeQuestionId = "") {
    chatState.questionEntries = Array.isArray(entries) ? entries.map((entry) => cloneQuestionEntry(entry)).filter(Boolean) : [];
    const preferredQuestionId = String(activeQuestionId || "").trim();
    const resolvedQuestionId =
      preferredQuestionId && chatState.questionEntries.some((entry) => entry.questionId === preferredQuestionId)
        ? preferredQuestionId
        : chatState.questionEntries[chatState.questionEntries.length - 1]?.questionId || "";
    setActiveQuestionId(resolvedQuestionId);
  }

  function findLatestQuestionPair() {
    const transcriptEntries = getTranscriptEntries();
    if (!Array.isArray(transcriptEntries) || transcriptEntries.length === 0) return null;

    for (let assistantIndex = transcriptEntries.length - 1; assistantIndex >= 0; assistantIndex -= 1) {
      const assistantEntry = transcriptEntries[assistantIndex];
      if (!assistantEntry || assistantEntry.role !== "assistant") continue;
      for (let userIndex = assistantIndex - 1; userIndex >= 0; userIndex -= 1) {
        const userEntry = transcriptEntries[userIndex];
        if (!userEntry || userEntry.role !== "user") continue;
        const questionText = normalizeSessionQuestion(userEntry.text);
        const traceId = String(assistantEntry.meta?.trace_id || "").trim();
        const chatRunId = String(assistantEntry.meta?.chat_run_id || "").trim();
        const assistantText = String(assistantEntry.text || "").trim();
        return {
          questionId: String(traceId || `question_${userIndex}_${assistantIndex}`).trim(),
          questionText,
          userTranscriptIndex: userIndex,
          assistantTranscriptIndex: assistantIndex,
          traceId,
          chatRunId,
          effectiveTopic: String(assistantEntry.meta?.effective_topic || "").trim(),
          pais: String(assistantEntry.meta?.pais || "").trim(),
          assistantText,
        };
      }
    }
    return null;
  }

  function upsertQuestionEntry(entry, { persist = false, makeActive = true } = {}) {
    const normalized = cloneQuestionEntry(entry);
    if (!normalized || !normalized.questionId) return null;
    const existingEntries = getQuestionEntries().filter((candidate) => candidate.questionId !== normalized.questionId);
    const mergedEntries = [...existingEntries, normalized].sort((left, right) => {
      const byAssistantIndex = Number(left.assistantTranscriptIndex) - Number(right.assistantTranscriptIndex);
      if (byAssistantIndex !== 0) return byAssistantIndex;
      return String(left.updatedAt || "").localeCompare(String(right.updatedAt || ""));
    });
    replaceQuestionEntries(mergedEntries, makeActive ? normalized.questionId : chatState.activeQuestionId);
    if (persist && !isTurnInFlight()) {
      persistActiveSessionSnapshot();
    } else {
      renderSessionSwitcher();
    }
    return normalized;
  }

  function captureLatestQuestionEntry({
    normativeSupport = requestController.getCurrentNormativeSupportSnapshot(),
    expertPanelState = expertPanel.getPersistedState(),
    persist = false,
  } = {}) {
    const pair = findLatestQuestionPair();
    if (!pair) return null;
    return upsertQuestionEntry(
      {
        ...pair,
        normativeSupport,
        expertPanelState,
        updatedAt: new Date().toISOString(),
      },
      { persist, makeActive: true }
    );
  }

  function findQuestionEntryById(questionId) {
    const normalizedQuestionId = String(questionId || "").trim();
    return getQuestionEntries().find((entry) => entry.questionId === normalizedQuestionId) || null;
  }

  // ── Expert panel load options ───────────────────────────────

  function buildExpertPanelLoadOptions({
    traceId,
    message,
    assistantAnswer,
    normativeSupport,
    topic,
    pais = "colombia",
  }): ExpertPanelLoadOptions {
    const supportCitations = expertPanelSupportCitationsFromSnapshot(normativeSupport);
    const normativeArticleRefs = extractArticleRefs(assistantAnswer);
    const searchSeed = buildExpertPanelSearchSeed({
      message,
      assistantAnswer,
      supportCitations,
      normativeArticleRefs,
    });
    return {
      traceId: String(traceId || "").trim(),
      message: String(message || "").trim(),
      assistantAnswer: String(assistantAnswer || "").trim() || undefined,
      normativeArticleRefs,
      searchSeed: searchSeed || undefined,
      searchSeedOrigin: searchSeed ? "deterministic" : undefined,
      topic: String(topic || "").trim() || undefined,
      pais,
    };
  }

  function buildExpertPanelFallbackLoadOptions(questionEntry) {
    if (!questionEntry) return null;
    const persistedLoadOptions = questionEntry.expertPanelState?.loadOptions;
    if (persistedLoadOptions?.traceId) {
      return persistedLoadOptions;
    }
    const transcriptEntries = getTranscriptEntries();
    const assistantText = String(
      transcriptEntries[Number(questionEntry.assistantTranscriptIndex)]?.text || questionEntry.assistantText || ""
    ).trim();
    if (!String(questionEntry.traceId || "").trim() && !assistantText) {
      return null;
    }
    const fallbackTopic =
      String(
        questionEntry.effectiveTopic ||
          questionEntry.normativeSupport?.citationRequestContext?.topic ||
          transcriptEntries[Number(questionEntry.assistantTranscriptIndex)]?.meta?.effective_topic ||
          ""
      ).trim() || undefined;
    const fallbackPais =
      String(
        questionEntry.pais ||
          questionEntry.normativeSupport?.citationRequestContext?.pais ||
          transcriptEntries[Number(questionEntry.assistantTranscriptIndex)]?.meta?.pais ||
          "colombia"
      ).trim() || "colombia";
    return buildExpertPanelLoadOptions({
      traceId: String(questionEntry.traceId || "").trim(),
      message: String(questionEntry.questionText || "").trim(),
      assistantAnswer: assistantText,
      normativeSupport: questionEntry.normativeSupport,
      topic: fallbackTopic,
      pais: fallbackPais,
    });
  }

  // ── Question activation & session switching ─────────────────

  function activateQuestionEntry(questionEntry, { persist = false, scroll = true } = {}) {
    if (!questionEntry) return false;
    setActiveQuestionId(questionEntry.questionId);
    requestController.setActiveChatRunId(String(questionEntry.chatRunId || "").trim());
    requestController.restoreNormativeSupportState(questionEntry.normativeSupport);
    expertPanel.restoreState(questionEntry.expertPanelState, buildExpertPanelFallbackLoadOptions(questionEntry));
    if (scroll) {
      scrollToTranscriptPair(questionEntry.userTranscriptIndex, questionEntry.assistantTranscriptIndex);
    }
    renderSessionSwitcher();
    updateBubbleSelectionState?.(questionEntry.questionId);
    if (persist && !isTurnInFlight()) {
      persistActiveSessionSnapshot();
    }
    return true;
  }

  function buildCurrentStoredSessionSnapshot(sessionId = getActiveSessionId()): QuestionSnapshot | null {
    const normalizedSessionId = String(sessionId || "").trim();
    if (!normalizedSessionId) return null;
    const transcriptEntries = getTranscriptEntries();
    if (!Array.isArray(transcriptEntries) || transcriptEntries.length === 0) return null;
    const questionEntries = getQuestionEntries();
    const firstQuestion = deriveFirstQuestionFromTranscriptEntries(transcriptEntries);
    const auth = getAuthContext();
    return {
      sessionId: normalizedSessionId,
      tenantId: auth.tenantId || undefined,
      firstQuestion,
      transcriptEntries,
      questionEntries,
      activeQuestionId: String(chatState.activeQuestionId || "").trim(),
      normativeSupport: requestController.getCurrentNormativeSupportSnapshot(),
      conversationTokenTotals: { ...chatState.conversationTokenTotals },
      lastUserMessage: String(chatState.lastUserMessage || "").trim(),
      lastSubmittedUserMessage: String(chatState.lastSubmittedUserMessage || "").trim(),
      lastAssistantAnswerMarkdown: String(chatState.lastAssistantAnswerMarkdown || "").trim(),
      detectedTopic: deriveDetectedTopic(questionEntries),
      threadLabel: deriveThreadLabel(firstQuestion, questionEntries),
    };
  }

  function setActiveSessionId(value) {
    const normalizedSessionId = String(value || "").trim();
    setSurfaceActiveSessionId(normalizedSessionId);
    sessionStore.writeWindowScopedSessionId(normalizedSessionId);
  }

  function persistActiveSessionSnapshot() {
    const snapshot = buildCurrentStoredSessionSnapshot();
    if (!snapshot) return;
    sessionStore.writeWindowScopedSessionId(snapshot.sessionId);
    sessionStore.persistSession(snapshot, chatSessionCacheLimit, true);
    renderSessionSwitcher();

    // Notify historial (desktop Record + mobile) so they can upsert
    const questionCount = snapshot.questionCount ?? (snapshot.questionEntries?.length || 0);
    document.dispatchEvent(new CustomEvent("lia:historial-upsert", {
      detail: {
        session_id: snapshot.sessionId,
        first_question: snapshot.firstQuestion || "",
        updated_at: new Date().toISOString(),
        thread_label: snapshot.threadLabel || "",
        detected_topic: snapshot.detectedTopic || "",
        topic: snapshot.detectedTopic || "",
        turn_count: questionCount * 2,
        question_count: questionCount,
      },
    }));
  }

  function renderSessionSwitcher() {
    sessionSwitcherNode.innerHTML = "";
    const index = sessionStore.readSessionIndex();
    const threads = index.sessions;
    const activeId = getActiveSessionId();

    const currentHasContent = getTranscriptEntries().length > 0;
    const currentInIndex = threads.some(s => s.sessionId === activeId);
    const threadCount = threads.length + (currentHasContent && !currentInIndex ? 1 : 0);

    chatSessionDrawerNode.hidden = threadCount <= 1;
    chatSessionCountNode.textContent = String(threadCount);
    if (threadCount <= 1) {
      chatSessionDrawerToggleNode.setAttribute("aria-expanded", "false");
      chatSessionDrawerPanelNode.hidden = true;
      return;
    }

    threads.forEach(summary => {
      const isActive = summary.sessionId === activeId;
      const sessionLabel = summary.threadLabel || i18n.t("chat.session.label", { id: summary.sessionId.slice(0, 8) });
      const chip = createButtonChip({
        label: sessionLabel,
        tone: "neutral",
        className: `chat-session-chip${isActive ? " is-active" : ""}`,
      });
      chip.dataset.sessionId = summary.sessionId;
      chip.setAttribute("aria-pressed", String(isActive));

      // Replace the simple text with cookie + card structure
      chip.textContent = "";

      const cookie = document.createElement("span");
      cookie.className = "chat-session-chip-cookie";
      cookie.textContent = sessionLabel;

      const firstQ = String(summary.firstQuestion || "").trim();
      const cardText = firstQ.length > 160 ? firstQ.slice(0, 157) + "..." : firstQ;

      const card = document.createElement("span");
      card.className = "chat-session-chip-card";
      card.textContent = cardText || sessionLabel;

      if (summary.questionCount && summary.questionCount > 1) {
        const badge = document.createElement("span");
        badge.className = "chat-session-chip-badge";
        badge.textContent = `+${summary.questionCount - 1}`;
        card.appendChild(badge);
      }

      chip.append(cookie, card);
      chip.addEventListener("click", () => {
        if (summary.sessionId === activeId) return;
        persistActiveSessionSnapshot();
        switchToStoredSession(summary.sessionId);
      });
      sessionSwitcherNode.appendChild(chip);
    });
  }

  function clearStoredChatSessionSnapshots() {
    sessionStore.clearSessionSnapshots();
  }

  function resetChatLogContents() {
    chatLog.innerHTML = "";
    chatLog.appendChild(chatLogEmptyNode);
  }

  async function hydrateStoredSession(sessionState) {
    if (!sessionState) return false;
    requestController.stopRequestTimer();
    thinkingOverlay.stop();
    setActiveSessionId(String(sessionState.sessionId || "").trim());
    chatState.activeCitation = null;
    chatState.activeNormaRequestId = 0;
    chatState.modalStack = [];
    chatState.lastUserMessage = String(sessionState.lastUserMessage || "").trim();
    chatState.lastAssistantAnswerMarkdown = String(sessionState.lastAssistantAnswerMarkdown || "").trim();
    chatState.lastSubmittedUserMessage = String(sessionState.lastSubmittedUserMessage || "").trim();
    replaceQuestionEntries(sessionState.questionEntries, sessionState.activeQuestionId);

    resetChatLogContents();
    resetTranscriptState();
    if (runtimeTurnTokensNode) runtimeTurnTokensNode.textContent = formatTokenUsage(normalizeTokenUsage(null));
    requestController.setConversationTotals(sessionState.conversationTokenTotals, { persistSnapshot: false });
    if (runtimeLatencyNode) runtimeLatencyNode.textContent = "-";
    if (runtimeRequestTimerNode) runtimeRequestTimerNode.textContent = "0.00 s";
    if (diagnosticsNode) {
      diagnosticsNode.textContent =
        chatState.buildInfoLine || (debugInput?.checked ? i18n.t("chat.debug.on") : i18n.t("chat.debug.off"));
    }

    expertPanel.clear();
    clearInterpretations();
    clearSummary();
    closeAllModals();
    await restoreTranscriptEntries(sessionState.transcriptEntries);
    // Tag restored bubbles with question IDs so click selection + active border work
    for (const qe of getQuestionEntries()) {
      setBubbleQuestionId?.(qe.assistantTranscriptIndex, qe.questionId);
    }
    const activeQuestionEntry =
      findQuestionEntryById(sessionState.activeQuestionId) ||
      getQuestionEntries()[getQuestionEntries().length - 1] ||
      null;
    if (activeQuestionEntry) {
      activateQuestionEntry(activeQuestionEntry, { persist: false, scroll: false });
    } else {
      requestController.restoreNormativeSupportState(sessionState.normativeSupport);
      expertPanel.restoreState(null);
    }

    messageInput.value = "";
    if (activeQuestionEntry) {
      scrollToTranscriptPair(activeQuestionEntry.userTranscriptIndex, activeQuestionEntry.assistantTranscriptIndex);
    } else {
      chatLog.scrollTop = chatLog.scrollHeight;
    }
    resizeComposer();
    updateWorkspaceControlsSummary();
    updateChatLogEmptyState();
    syncReadyState();
    focusComposer();
    renderSessionSwitcher();
    // Citations + expert panel already restored for the active question via activateQuestionEntry above
    return true;
  }

  async function switchToStoredSession(sessionId) {
    const normalizedSessionId = String(sessionId || "").trim();
    if (!normalizedSessionId) return;
    const sessionState = sessionStore.readSessionState(normalizedSessionId);
    if (!sessionState) {
      renderSessionSwitcher();
      return;
    }
    sessionStore.setActiveSession(normalizedSessionId);
    await hydrateStoredSession(sessionState);
  }

  async function restoreWindowScopedSessionIfNeeded() {
    if (isTurnInFlight()) return false;
    const preferredSessionId = sessionStore.readWindowScopedSessionId();
    if (!preferredSessionId || preferredSessionId === getActiveSessionId()) return false;
    const sessionState = sessionStore.readWindowScopedSessionState();
    if (!sessionState) return false;
    await hydrateStoredSession(sessionState);
    return true;
  }

  return {
    normalizeSessionQuestion,
    cloneQuestionEntry,
    setActiveQuestionId,
    getQuestionEntries,
    replaceQuestionEntries,
    findLatestQuestionPair,
    upsertQuestionEntry,
    captureLatestQuestionEntry,
    findQuestionEntryById,
    buildExpertPanelLoadOptions,
    buildExpertPanelFallbackLoadOptions,
    activateQuestionEntry,
    buildCurrentStoredSessionSnapshot,
    setActiveSessionId,
    persistActiveSessionSnapshot,
    renderSessionSwitcher,
    clearStoredChatSessionSnapshots,
    resetChatLogContents,
    hydrateStoredSession,
    switchToStoredSession,
    restoreWindowScopedSessionIfNeeded,
  };
}
