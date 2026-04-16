// @ts-nocheck

import { collectChatDom } from "@/features/chat/chatDom";
import { createChatSessionStore } from "@/features/chat/chatSessionStore";
import {
  createNormativeModalController,
} from "@/features/chat/normativeModals";
import {
  buildNormativeSupportRequestBody,
  createChatRequestController,
  formatTokenUsage,
  normalizeTokenUsage,
} from "@/features/chat/requestController";
import {
  createChatTranscriptController,
  formatConversationCopyPayload,
} from "@/features/chat/transcriptController";
import { createChatSurfaceController } from "@/features/chat/chatSurfaceController";
import { createExpertPanelController } from "@/features/chat/expertPanelController";
import { initSplitter } from "@/features/chat/splitter";
import { getThinkingOverlay } from "@/shared/async/thinkingOverlay";
import { getToastController } from "@/shared/ui/toasts";
import { getJson } from "@/shared/api/client";
import { getAuthContext } from "@/shared/auth/authContext";

import { createTooltipManager } from "@/features/chat/chatTooltipManager";
import { createCitationRenderer } from "@/features/chat/chatCitationRenderer";
import { createChatSessionController } from "@/features/chat/chatSessionController";

export { buildNormativeSupportRequestBody };
export { formatConversationCopyPayload };

export function mountChatApp(root, options) {
  const { i18n, mode = "default" } = options || {};
  const isPublicMode = mode === "public";
  const dom = collectChatDom(root);
  const sessionStore = createChatSessionStore();
  const {
    bubbleTemplate, chatForm, chatLog, chatLogEmptyNode,
    expertDetailModalNode, chatSessionCountNode, chatSessionDrawerNode,
    chatSessionDrawerPanelNode, chatSessionDrawerToggleNode, chatSplitterEl,
    citationsList, citationsLoadBtn, citationsStatusNode,
    debugInput, debugSummaryNode, diagnosticsNode,
    expertPanelContentNode, expertPanelStatusNode,
    expertTooltipNode, expertTooltipShellNode, expertTooltipTriggerNode,
    newThreadBtn, interpretationResultsNode, interpretationStatusNode,
    layoutEl: chatLayoutEl, messageInput,
    modalInterpretations, modalLayer, modalNorma, modalSummary,
    normaAnalysisBtn, normaAnalysisHelperNode, normaBindingForceNode,
    normaCautionBannerNode, normaCautionBodyNode, normaCautionTitleNode,
    normaCompanionBtn, normaCompanionHelperNode, normaCompanionNode,
    normaFactsNode, normaHelperNode, normaLeadNode, normaLoadingNode,
    normaOriginalBtn, normaOriginalHelperNode, normaPrimaryNode,
    normaSectionsNode, normaTitleNode, normaTopbarNode,
    resetConversationBtn, runtimeConversationTokensNode,
    runtimeLatencyNode, runtimeModelNode, runtimeRequestTimerNode,
    runtimeTurnTokensNode, sendBtn, sessionIdBadgeNode,
    sessionStateBadgeNode, sessionSwitcherNode,
    summaryBodyNode, summaryExternalLinkNode, summaryGroundingNode, summaryModeNode,
  } = dom;

  const thinkingOverlay = getThinkingOverlay();
  const toastController = getToastController(i18n);

  const chatState = {
    requestTimerInterval: null, requestStartedAtMs: null, latestTurnStartedAtMs: null,
    activeChatRunId: "", activeCitation: null,
    lastUserMessage: "", lastAssistantAnswerMarkdown: "", lastSubmittedUserMessage: "",
    activeSessionId: "", citationRequestContext: null,
    deferredCitationsFallback: [], deferredMentionCitations: [],
    deferredCitationsCache: [], deferredCitationsCacheKey: "",
    deferredCitationsStatusText: "", deferredCitationsPlaceholderText: "",
    buildInfoLine: "", activeNormaRequestId: 0, modalStack: [],
    conversationTokenTotals: { input_tokens: 0, output_tokens: 0, total_tokens: 0 },
    questionEntries: [], activeQuestionId: "",
  };

  const FEEDBACK_GET_ROUTE = "/api/feedback";
  const FEEDBACK_POST_ROUTE = "/api/feedback";
  const CHAT_SESSION_CACHE_LIMIT = 12;
  const FEEDBACK_RATING_UP = 5;
  const FEEDBACK_RATING_DOWN = 1;
  const DEV_BOOT_CACHE_KEY = "lia_dev_boot_nonce_v1";
  const LEGACY_ASSISTANT_GREETINGS = new Set(["¡Hola! Escribe tu caso y buscaré ayudarte..."]);
  const DECISION_RESPONSE_ROUTE = "decision";

  function withThinkingWheel(task) { return thinkingOverlay.withTask(task); }

  // ── Tooltip ─────────────────────────────────────────────────
  const tooltipManager = createTooltipManager({
    expertTooltipNode, expertTooltipShellNode, expertTooltipTriggerNode,
  });
  tooltipManager.bindExpertTooltip();

  // ── Surface controller ──────────────────────────────────────
  const surfaceController = createChatSurfaceController({
    i18n, state: chatState, root, chatLog, chatLogEmptyNode,
    messageInput, sendBtn, resetConversationBtn, newThreadBtn,
    sessionStateBadgeNode, sessionIdBadgeNode, debugInput, debugSummaryNode,
  });
  const {
    consumeComposerPrefillFromUrl, deriveReadyState, focusComposer, getActiveSessionId,
    initializeSurface, isTurnInFlight, resizeComposer,
    setActiveSessionId: setSurfaceActiveSessionId,
    setTurnState, syncReadyState, updateChatLogEmptyState, updateWorkspaceControlsSummary,
  } = surfaceController;

  // ── Transcript controller ───────────────────────────────────
  const transcriptController = createChatTranscriptController({
    i18n, chatLog, bubbleTemplate,
    feedbackGetRoute: FEEDBACK_GET_ROUTE, feedbackPostRoute: FEEDBACK_POST_ROUTE,
    feedbackRatingUp: FEEDBACK_RATING_UP, feedbackRatingDown: FEEDBACK_RATING_DOWN,
    setActiveSessionId: (id) => sessionController.setActiveSessionId(id),
    updateChatLogEmptyState,
    onTranscriptEntriesChanged: () => {
      if (isTurnInFlight()) return;
      sessionController.persistActiveSessionSnapshot();
    },
  });
  const {
    addBubble, buildAssistantBubbleMeta, createStreamingAssistantBubble,
    getTranscriptEntries, resetTranscriptState, restoreTranscriptEntries, scrollToTranscriptPair,
  } = transcriptController;

  // ── Modal controller ────────────────────────────────────────
  const modalController = createNormativeModalController({
    i18n, state: chatState,
    dom: {
      modalLayer, modalNorma, modalInterpretations, modalSummary,
      normaTitleNode, normaBindingForceNode, normaOriginalBtn, normaAnalysisBtn,
      normaOriginalHelperNode, normaAnalysisHelperNode, normaTopbarNode,
      normaLoadingNode, normaHelperNode, normaCautionBannerNode, normaCautionTitleNode,
      normaCautionBodyNode, normaPrimaryNode, normaLeadNode, normaFactsNode,
      normaSectionsNode, normaCompanionNode, normaCompanionBtn, normaCompanionHelperNode,
      interpretationStatusNode, interpretationResultsNode,
      summaryModeNode, summaryExternalLinkNode, summaryBodyNode, summaryGroundingNode,
    },
    withThinkingWheel,
  });
  const { bindModalControls, clearInterpretations, clearSummary, closeAllModals, openModal, openNormaModal } =
    modalController;

  // ── Citation renderer ───────────────────────────────────────
  const citationRenderer = createCitationRenderer({
    citationsList, citationsStatusNode, openNormaModal, root,
  });

  // ── Expert panel ────────────────────────────────────────────
  const expertPanel = createExpertPanelController({
    i18n,
    contentNode: expertPanelContentNode,
    statusNode: expertPanelStatusNode,
    detailModalNode: expertDetailModalNode,
    openModal,
    onSnippetClick: (docId: string) => openNormaModal({ doc_id: docId }),
    onStateChanged: (snapshot) => {
      if (!snapshot) return;
      const traceId = String(snapshot.loadOptions?.traceId || "").trim();
      if (!traceId) return;
      const matchingEntry = sessionController.getQuestionEntries().find(
        (entry) => String(entry.traceId || "").trim() === traceId,
      );
      if (!matchingEntry) return;
      sessionController.upsertQuestionEntry(
        { ...matchingEntry, expertPanelState: snapshot, updatedAt: new Date().toISOString() },
        { persist: !isTurnInFlight(), makeActive: matchingEntry.questionId === chatState.activeQuestionId },
      );
    },
  });

  // ── Session controller ──────────────────────────────────────
  // requestController is created below — pass lambda wrappers so they resolve at call time.
  const _sessionControllerImpl = createChatSessionController({
    i18n, chatState, sessionStore, chatSessionCacheLimit: CHAT_SESSION_CACHE_LIMIT,
    chatLog, chatLogEmptyNode, runtimeTurnTokensNode, runtimeLatencyNode,
    runtimeRequestTimerNode, diagnosticsNode, debugInput, messageInput,
    sessionSwitcherNode, chatSessionCountNode, chatSessionDrawerNode,
    chatSessionDrawerPanelNode, chatSessionDrawerToggleNode,
    expertPanelContentNode, expertPanelStatusNode,
    getActiveSessionId, setSurfaceActiveSessionId, isTurnInFlight,
    resizeComposer, updateWorkspaceControlsSummary, updateChatLogEmptyState,
    syncReadyState, focusComposer, resetTranscriptState,
    getTranscriptEntries, restoreTranscriptEntries, scrollToTranscriptPair,
    setBubbleQuestionId: transcriptController.setBubbleQuestionId,
    updateBubbleSelectionState: transcriptController.updateBubbleSelectionState,
    requestController: {
      stopRequestTimer: (...a) => requestController.stopRequestTimer(...a),
      setActiveChatRunId: (...a) => requestController.setActiveChatRunId(...a),
      setConversationTotals: (...a) => requestController.setConversationTotals(...a),
      clearNormativeSupportState: (...a) => requestController.clearNormativeSupportState(...a),
      restoreNormativeSupportState: (...a) => requestController.restoreNormativeSupportState(...a),
      getCurrentNormativeSupportSnapshot: (...a) => requestController.getCurrentNormativeSupportSnapshot(...a),
      hydrateRuntimeModelFromStatus: (...a) => requestController.hydrateRuntimeModelFromStatus(...a),
    },
    expertPanel, clearInterpretations, clearSummary, closeAllModals, thinkingOverlay,
    buildThreadCitationGroups: citationRenderer.buildThreadCitationGroups,
    renderCitationsGrouped: citationRenderer.renderCitationsGrouped,
    renderAccumulatedExpertPanel: citationRenderer.renderAccumulatedExpertPanel,
  });

  // In public mode the chat surface has no per-user history. We keep the
  // underlying controller (it owns the active session id needed by the
  // request flow) but no-op the persistence + drawer operations so nothing
  // ever lands in localStorage and the (CSS-hidden) drawer never opens.
  const sessionController = isPublicMode
    ? new Proxy(_sessionControllerImpl, {
        get(target, prop) {
          if (
            prop === "persistActiveSessionSnapshot" ||
            prop === "writeSessionsIndex" ||
            prop === "renderSessionList" ||
            prop === "openDrawer" ||
            prop === "closeDrawer" ||
            prop === "toggleDrawer"
          ) {
            return () => {};
          }
          return target[prop];
        },
      })
    : _sessionControllerImpl;

  // ── Conversation lifecycle ──────────────────────────────────

  function startNewConversation({ persistInIndex = true } = {}) {
    if (isTurnInFlight()) return;
    requestController.stopRequestTimer();
    thinkingOverlay.stop();
    sessionController.setActiveSessionId("");
    chatState.activeCitation = null;
    chatState.activeNormaRequestId = 0;
    chatState.modalStack = [];
    chatState.lastUserMessage = "";
    chatState.lastAssistantAnswerMarkdown = "";
    chatState.lastSubmittedUserMessage = "";
    sessionController.replaceQuestionEntries([], "");
    sessionController.resetChatLogContents();
    resetTranscriptState();
    if (runtimeTurnTokensNode) runtimeTurnTokensNode.textContent = formatTokenUsage(normalizeTokenUsage(null));
    requestController.setConversationTotals(null, { persistSnapshot: false });
    if (runtimeLatencyNode) runtimeLatencyNode.textContent = "-";
    if (runtimeRequestTimerNode) runtimeRequestTimerNode.textContent = "0.00 s";
    if (diagnosticsNode) {
      diagnosticsNode.textContent =
        chatState.buildInfoLine || (debugInput?.checked ? i18n.t("chat.debug.on") : i18n.t("chat.debug.off"));
    }
    requestController.clearNormativeSupportState({
      placeholderText: i18n.t("chat.citations.prompt"),
      statusText: i18n.t("chat.support.defer"),
      canLoadOnDemand: false, persistSnapshot: false,
    });
    expertPanel.clear();
    clearInterpretations();
    clearSummary();
    closeAllModals();
    messageInput.value = "";
    chatLog.scrollTop = 0;
    resizeComposer();
    updateWorkspaceControlsSummary();
    updateChatLogEmptyState();
    syncReadyState();
    focusComposer();
    if (persistInIndex) {
      sessionStore.setActiveSession("");
      sessionController.renderSessionSwitcher();
    }
    void requestController.hydrateRuntimeModelFromStatus();
  }

  function resetConversationUi() {
    if (isTurnInFlight()) return;
    sessionController.clearStoredChatSessionSnapshots();
    startNewConversation({ persistInIndex: false });
    sessionController.renderSessionSwitcher();
  }

  // ── Request controller ──────────────────────────────────────
  const requestController = createChatRequestController({
    i18n, state: chatState,
    dom: {
      citationsLoadBtn, diagnosticsNode, runtimeRequestTimerNode,
      runtimeLatencyNode, runtimeModelNode, runtimeTurnTokensNode,
      runtimeConversationTokensNode, sendBtn,
    },
    debugInput,
    startThinkingWheel: () => thinkingOverlay.start(),
    stopThinkingWheel: () => thinkingOverlay.stop(),
    withThinkingWheel, getActiveSessionId,
    setActiveSessionId: (id) => sessionController.setActiveSessionId(id),
    setTurnState: (nextState: string) => {
      setTurnState(nextState);
      sessionController.renderSessionSwitcher();
    },
    deriveReadyState, focusComposer, resetConversationUi,
    renderCitations: citationRenderer.renderCitations,
    renderCitationsPreview: citationRenderer.renderCitationsPreview,
    renderDeferredCitationsState: citationRenderer.renderDeferredCitationsState,
    setCitationsStatus: citationRenderer.setCitationsStatus,
    addBubble, createStreamingAssistantBubble, buildAssistantBubbleMeta,
    decisionResponseRoute: DECISION_RESPONSE_ROUTE,
    devBootCacheKey: DEV_BOOT_CACHE_KEY,
    persistActiveSessionSnapshot: () => sessionController.persistActiveSessionSnapshot(),
    onChatSuccess: (context) => {
      sessionController.captureLatestQuestionEntry({ persist: true });
      // Mark the latest assistant bubble as normativa-enabled and highlight it
      const latestEntries = sessionController.getQuestionEntries();
      const latestQ = latestEntries[latestEntries.length - 1];
      if (latestQ) {
        transcriptController.setBubbleQuestionId(latestQ.assistantTranscriptIndex, latestQ.questionId);
        sessionController.setActiveQuestionId(latestQ.questionId);
        transcriptController.updateBubbleSelectionState(latestQ.questionId);
        void requestController.recordUserMilestone("response_bubble_highlighted", {
          source: "bubble_active",
          status: "ok",
          details: { question_id: latestQ.questionId },
        });
      }
      // Load expert panel for the latest bubble (fresh fetch, not from cache)
      const normativeSupportSnapshot = requestController.getCurrentNormativeSupportSnapshot();
      void expertPanel
        .load(sessionController.buildExpertPanelLoadOptions({
          traceId: context.traceId, message: context.message,
          assistantAnswer: context.assistantAnswer,
          normativeSupport: normativeSupportSnapshot,
          topic: context.topic, pais: context.pais,
        }))
        .then(() => {
          const expertState = expertPanel.getPersistedState?.();
          void requestController.recordUserMilestone("expert_panel_displayed", {
            source: "expert_panel", status: String(expertState?.status || "ok"),
            details: { panel_status: String(expertState?.status || "") },
          });
        });
    },
    onChatReset: () => {
      requestController.setActiveChatRunId("");
      expertPanel.clear();
    },
  });

  // ── Initialize UI ───────────────────────────────────────────
  if (runtimeTurnTokensNode) runtimeTurnTokensNode.textContent = formatTokenUsage(normalizeTokenUsage(null));
  requestController.setConversationTotals(chatState.conversationTokenTotals, { persistSnapshot: false });
  if (runtimeModelNode) runtimeModelNode.textContent = i18n.t("common.notAvailable");
  if (runtimeLatencyNode) runtimeLatencyNode.textContent = "-";
  if (runtimeRequestTimerNode) runtimeRequestTimerNode.textContent = "0.00 s";
  requestController.clearNormativeSupportState({
    placeholderText: i18n.t("chat.citations.prompt"),
    statusText: i18n.t("chat.support.defer"),
    canLoadOnDemand: false, persistSnapshot: false,
  });
  initializeSurface();
  if (chatLayoutEl && chatSplitterEl) initSplitter(chatLayoutEl, chatSplitterEl);

  // ── Active-window focus ring ────────────────────────────────
  const chatPanelEl = root.querySelector<HTMLElement>(".chat-panel");
  const sideSections = Array.from(root.querySelectorAll<HTMLElement>(".side-panel section"));
  const focusablePanels = [chatPanelEl, ...sideSections].filter(Boolean) as HTMLElement[];
  function setFocusWindow(target: HTMLElement): void {
    for (const panel of focusablePanels) panel.classList.toggle("is-focus-window", panel === target);
  }
  for (const panel of focusablePanels) {
    panel.addEventListener("pointerdown", () => setFocusWindow(panel));
    panel.addEventListener("wheel", () => setFocusWindow(panel), { passive: true });
  }
  if (chatPanelEl) setFocusWindow(chatPanelEl);

  sessionController.renderSessionSwitcher();

  // ── Event bindings ──────────────────────────────────────────
  chatSessionDrawerToggleNode.addEventListener("click", () => {
    if (chatSessionDrawerNode.hidden) return;
    const expanded = chatSessionDrawerToggleNode.getAttribute("aria-expanded") === "true";
    chatSessionDrawerToggleNode.setAttribute("aria-expanded", String(!expanded));
    chatSessionDrawerPanelNode.hidden = expanded;
  });

  if (citationsLoadBtn) {
    citationsLoadBtn.addEventListener("click", () => void requestController.loadCitationsOnDemand());
  }
  if (newThreadBtn) {
    newThreadBtn.addEventListener("click", () => {
      if (isTurnInFlight()) return;
      sessionController.persistActiveSessionSnapshot();
      startNewConversation({ persistInIndex: true });
      sessionController.renderSessionSwitcher();
    });
  }
  if (resetConversationBtn) {
    resetConversationBtn.addEventListener("click", async () => {
      if (isTurnInFlight()) return;
      const confirmed = await toastController.confirm({
        message: i18n.t("chat.workspace.reset.caution"), tone: "caution",
        confirmLabel: i18n.t("chat.workspace.reset.confirmAction"),
        cancelLabel: i18n.t("chat.workspace.reset.cancelAction"),
      });
      if (!confirmed || isTurnInFlight()) return;
      resetConversationUi();
    });
  }
  if (debugInput) {
    debugInput.addEventListener("change", () => {
      updateWorkspaceControlsSummary();
      if (!debugInput.checked && !isTurnInFlight() && diagnosticsNode) {
        diagnosticsNode.textContent = chatState.buildInfoLine || i18n.t("chat.debug.off");
      }
    });
  }
  if (messageInput) {
    messageInput.addEventListener("input", () => {
      resizeComposer();
      if (!isTurnInFlight()) syncReadyState();
    });
    messageInput.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" || event.shiftKey) return;
      event.preventDefault();
      chatForm.requestSubmit();
    });
  }

  bindModalControls();
  clearSummary();
  void requestController.hydrateRuntimeModelFromStatus();

  // ── Window/tab session restoration ──────────────────────────
  const restoreWindowScopedSession = () => void sessionController.restoreWindowScopedSessionIfNeeded();
  window.addEventListener("focus", restoreWindowScopedSession);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") restoreWindowScopedSession();
  });
  root.addEventListener("pointerdown", restoreWindowScopedSession);

  // ── Per-bubble normativa selection (click delegation) ───────
  chatLog.addEventListener("click", (event) => {
    const target = event.target as HTMLElement;
    if (target.closest(".bubble-actions") || target.closest("a") || target.closest("button")) return;
    const bubbleNode = target.closest(".bubble-assistant[data-question-id]");
    if (!bubbleNode || !(bubbleNode instanceof HTMLElement)) return;
    const questionId = bubbleNode.dataset.questionId;
    if (!questionId) return;
    const entry = sessionController.findQuestionEntryById(questionId);
    if (!entry) return;
    sessionController.activateQuestionEntry(entry, { persist: true, scroll: false });
  });

  // ── Form submission ─────────────────────────────────────────
  chatForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = messageInput.value.trim();
    if (!message) return;
    messageInput.value = "";
    resizeComposer();
    syncReadyState();
    await requestController.submitChatTurn({ displayUserText: message, requestMessage: message });
  });

  // ── Load external session (from Record tab) ─────────────────
  async function loadExternalSession(sessionId) {
    const normalizedId = String(sessionId || "").trim();
    if (!normalizedId) return;
    try {
      const ctx = getAuthContext();
      const tenantParam = ctx.tenantId || "public";
      const data = await getJson<{ ok: boolean; session: any }>(
        `/api/conversation/${encodeURIComponent(normalizedId)}?tenant_id=${encodeURIComponent(tenantParam)}`,
      );
      const session = data?.session;
      if (!session || !Array.isArray(session.turns)) return;
      const transcriptEntries = session.turns.map((turn) => ({
        role: turn.role === "user" ? "user" : "assistant",
        text: turn.content || "",
        timestamp: turn.timestamp || turn.created_at || "",
        meta: { trace_id: turn.trace_id || "" },
      }));

      // Build questionEntries from turn_metadata for per-bubble normativa recall
      const questionEntries: any[] = [];
      let pendingUserIdx = -1;
      let pendingUserText = "";
      transcriptEntries.forEach((entry, index) => {
        if (entry.role === "user") {
          pendingUserIdx = index;
          pendingUserText = entry.text;
          return;
        }
        if (entry.role !== "assistant" || pendingUserIdx < 0) return;
        const turnMeta = session.turns[index]?.turn_metadata;
        const traceId = String(entry.meta?.trace_id || "").trim();
        const qId = traceId || `q_${pendingUserIdx}_${index}`;
        questionEntries.push({
          questionId: qId,
          questionText: pendingUserText,
          userTranscriptIndex: pendingUserIdx,
          assistantTranscriptIndex: index,
          traceId,
          chatRunId: "",
          effectiveTopic: turnMeta?.effective_topic || session.topic || "",
          pais: session.pais || "colombia",
          normativeSupport: turnMeta ? {
            citationRequestContext: {
              trace_id: traceId,
              message: pendingUserText,
              assistant_answer: entry.text,
              topic: turnMeta.effective_topic || session.topic || "",
              pais: session.pais || "colombia",
            },
            fallbackCitations: turnMeta.support_citations || [],
            mentionCitations: [],
            cachedCitations: turnMeta.citations || [],
            statusText: "",
            placeholderText: "",
          } : null,
          expertPanelState: null,
          updatedAt: entry.timestamp || "",
          assistantText: entry.text,
        });
        pendingUserIdx = -1;
      });

      const lastQId = questionEntries[questionEntries.length - 1]?.questionId || "";
      const firstQuestion = transcriptEntries.find((e) => e.role === "user")?.text || "";
      await sessionController.hydrateStoredSession({
        sessionId: normalizedId, firstQuestion: firstQuestion.slice(0, 120),
        transcriptEntries, questionEntries, activeQuestionId: lastQId,
        normativeSupport: null, conversationTokenTotals: {},
        detectedTopic: session.topic || "", threadLabel: firstQuestion.slice(0, 60),
      });

      // Mark bubbles with normativa and auto-select the last one
      for (const qe of questionEntries) {
        if (qe.normativeSupport) {
          transcriptController.setBubbleQuestionId(qe.assistantTranscriptIndex, qe.questionId);
        }
      }
      if (lastQId) {
        transcriptController.updateBubbleSelectionState(lastQId);
        const lastEntry = questionEntries[questionEntries.length - 1];
        if (lastEntry) sessionController.activateQuestionEntry(lastEntry, { persist: false, scroll: false });
      }

      const divider = document.createElement("div");
      divider.className = "resumed-divider";
      divider.textContent = "Conversación reanudada";
      chatLog.appendChild(divider);
      chatLog.scrollTop = chatLog.scrollHeight;
      focusComposer();
    } catch (err) {
      console.error("[chatApp] loadExternalSession failed:", err);
    }
  }

  // ── Boot sequence ───────────────────────────────────────────
  void (async () => {
    const resetForDevBoot = await requestController.loadBuildInfo();
    if (!resetForDevBoot) {
      sessionStore.migrateLegacySessionStorage({
        legacyAssistantGreetings: LEGACY_ASSISTANT_GREETINGS,
        maxSessions: CHAT_SESSION_CACHE_LIMIT,
      });
      const activeSession = sessionStore.readWindowScopedSessionState() || sessionStore.readActiveSession();

      // Tenant isolation: discard stored sessions that belong to a different tenant.
      const currentAuth = getAuthContext();
      const storedTenant = String(activeSession?.tenantId || "").trim();
      const tenantMatch =
        !currentAuth.tenantId || !storedTenant || storedTenant === currentAuth.tenantId;

      if (activeSession && tenantMatch) {
        await sessionController.hydrateStoredSession(activeSession);
      } else {
        if (activeSession && !tenantMatch) {
          sessionStore.clearSessionSnapshots();
        }
        startNewConversation();
      }
    } else {
      sessionController.renderSessionSwitcher();
    }
    const prefillState = consumeComposerPrefillFromUrl();
    syncReadyState();
    focusComposer();
    if (prefillState?.shouldSubmit) {
      requestAnimationFrame(() => {
        if (isTurnInFlight()) return;
        if (!String(messageInput.value || "").trim()) return;
        chatForm.requestSubmit();
      });
    }
  })();

  return {
    loadExternalSession,
    openCitationById: citationRenderer.openCitationById,
    openExpertCardById: expertPanel.openCardById,
  };
}
