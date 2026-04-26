// @ts-nocheck

/**
 * Chat request orchestrator — submitChatTurn + response handling.
 * Sub-modules: streamHandler, citationLoading, requestMetrics.
 * Reduced from ~1,570L during decouple-v1 Phase 4.
 */

import {
  asCitationArray,
  extractMentionCitations,
  extractUserFormMentionCitations,
  mergeCitations,
} from "@/features/chat/citations";
import { stripInlineEvidenceAnnotations } from "@/features/chat/formatting";
import { postJson, getApiAccessToken } from "@/shared/api/client";
import { createButton } from "@/shared/ui/atoms/button";
import { icons } from "@/shared/ui/icons";
import type { I18nRuntime } from "@/shared/i18n";

// Sub-modules
import {
  buildClientTurnId,
  consumeEventStream,
  createRequestWatchdog,
  isEventStreamResponse,
  isRecoverableStreamError,
  waitForChatRunCompletion,
  STREAM_INITIAL_TIMEOUT_MS,
  STREAM_IDLE_TIMEOUT_MS,
} from "@/features/chat/streamHandler";
import {
  buildNormativeSupportRequestBody,
  buildCurrentNormativeSupportSnapshot,
  createCitationLoadingController,
} from "@/features/chat/citationLoading";
import {
  normalizeTokenUsage,
  formatTokenUsage,
  formatDurationSeconds,
  createMetricsController,
} from "@/features/chat/requestMetrics";

// Re-exports for backwards compat (chatApp.ts imports these from here)
export { buildNormativeSupportRequestBody } from "@/features/chat/citationLoading";
export { normalizeTokenUsage, formatTokenUsage } from "@/features/chat/requestMetrics";

// ── Internal helpers (not worth a separate module) ────────────

function createDebugSnapshot(value: unknown, maxDepth = 4, seen = new WeakSet()): unknown {
  if (value === null || value === undefined) return value;
  if (typeof value === "string") {
    return value.length > 500 ? `${value.slice(0, 500)}... [truncado ${value.length - 500} chars]` : value;
  }
  if (typeof value !== "object") return value;
  if (seen.has(value)) return "[circular]";
  seen.add(value);
  if (maxDepth <= 0) return "[max_depth]";
  if (Array.isArray(value)) {
    const capped = value.slice(0, 30).map((item) => createDebugSnapshot(item, maxDepth - 1, seen));
    if (value.length > 30) capped.push(`... [${value.length - 30} elementos truncados]`);
    return capped;
  }
  const entries = Object.entries(value);
  const limitedEntries = entries.slice(0, 40).map(([key, item]) => [key, createDebugSnapshot(item, maxDepth - 1, seen)]);
  if (entries.length > 40) limitedEntries.push(["__truncated__", `${entries.length - 40} claves omitidas`]);
  return Object.fromEntries(limitedEntries);
}

function safeDebugString(value: unknown, fallback = "Debug no disponible."): string {
  try {
    const snapshot = createDebugSnapshot(value, 4);
    const text = JSON.stringify(snapshot, null, 2);
    if (!text) return fallback;
    const maxChars = 26000;
    return text.length > maxChars ? `${text.slice(0, maxChars)}\n... [debug truncado]` : text;
  } catch (_error) { return fallback; }
}

function buildOverlayDebugLine(data: Record<string, unknown>): string {
  const metrics = data && typeof data.metrics === "object" ? data.metrics : {};
  const mode = String((metrics as Record<string, unknown>).primary_scope_mode || "global_overlay").trim();
  const overlay =
    (metrics as Record<string, unknown>).primary_overlay &&
    typeof (metrics as Record<string, unknown>).primary_overlay === "object"
      ? ((metrics as Record<string, unknown>).primary_overlay as Record<string, unknown>)
      : {};
  const applied = Boolean(overlay.overlay_applied);
  const selected = Number(overlay.overlay_selected_count || 0);
  const candidates = Number(overlay.overlay_candidates_count || 0);
  return `Overlay normativo global: ${mode} | applied=${applied ? "yes" : "no"} | selected=${selected} | candidates=${candidates}`;
}

function asInteractionPayload(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" ? (value as Record<string, unknown>) : null;
}

function firstClarificationHint(interaction: Record<string, unknown> | null): string {
  if (!interaction) return "";
  const requirements = Array.isArray(interaction.requirements)
    ? interaction.requirements.filter((item): item is string => typeof item === "string" && item.trim()).slice(0, 3)
    : [];
  if (requirements.length > 0) return requirements[0];
  return String(interaction.current_question || "").trim();
}

function buildClarificationNormativeState(i18n: I18nRuntime, interaction: Record<string, unknown> | null) {
  const placeholder = i18n.t("chat.citations.clarificationPending");
  const hint = firstClarificationHint(interaction);
  if (!hint) return { placeholder, status: i18n.t("chat.citations.clarificationStatus") };
  return { placeholder, status: `${i18n.t("chat.citations.clarificationStatus")} ${hint}` };
}

// ── Controller factory ────────────────────────────────────────

export function createChatRequestController({
  i18n, state, dom, debugInput,
  startThinkingWheel, stopThinkingWheel, withThinkingWheel,
  getActiveSessionId, setActiveSessionId, setTurnState, deriveReadyState,
  focusComposer, resetConversationUi,
  renderCitations, renderCitationsPreview, renderDeferredCitationsState, setCitationsStatus,
  addBubble, createStreamingAssistantBubble, buildAssistantBubbleMeta,
  decisionResponseRoute, devBootCacheKey,
  persistActiveSessionSnapshot, onChatSuccess, onChatReset,
}) {
  const {
    citationsLoadBtn, diagnosticsNode, runtimeRequestTimerNode,
    runtimeLatencyNode, runtimeModelNode, runtimeTurnTokensNode,
    runtimeConversationTokensNode, sendBtn,
  } = dom;

  // ── Sub-controllers ───────────────────────────────────────

  const metrics = createMetricsController({
    i18n, state, debugInput, diagnosticsNode,
    runtimeRequestTimerNode, runtimeLatencyNode, runtimeModelNode,
    runtimeTurnTokensNode, runtimeConversationTokensNode,
    devBootCacheKey, resetConversationUi, persistActiveSessionSnapshot,
  });

  const citationCtrl = createCitationLoadingController({
    i18n, state, citationsLoadBtn, withThinkingWheel,
    renderCitations, renderDeferredCitationsState, setCitationsStatus,
    persistActiveSessionSnapshot,
    recordUserMilestone: metrics.recordUserMilestone,
    onChatReset,
  });

  // ── Retry infrastructure ──────────────────────────────────

  type RetryParams = { displayUserText: string; requestMessage: string; responseRoute: string };
  const _retryParams = new WeakMap<HTMLElement, RetryParams>();
  const _retryAttempted = new WeakSet<HTMLElement>();

  function markBubbleRetryable(
    bubbleNode: HTMLElement | null,
    params: RetryParams,
  ): void {
    if (!bubbleNode) return;
    bubbleNode.dataset.retryable = "true";
    _retryParams.set(bubbleNode, params);

    // Inject retry button into the error bubble
    const btn = createButton({
      iconHtml: icons.retry,
      label: i18n.t("chat.chat.retry"),
      tone: "ghost",
      className: "bubble-retry-btn",
      onClick: () => {
        btn.disabled = true;
        btn.classList.add("is-retrying");
        btn.textContent = i18n.t("chat.chat.retryInProgress");
        btn.dispatchEvent(new CustomEvent("lia:retry-turn", { bubbles: true }));
      },
    });
    bubbleNode.appendChild(btn);
  }

  function findLastAssistantBubble(): HTMLElement | null {
    const all = document.querySelectorAll(".bubble-assistant");
    return (all.length > 0 ? all[all.length - 1] : null) as HTMLElement | null;
  }

  document.addEventListener("lia:retry-turn", (evt) => {
    const bubbleNode = (evt.target as HTMLElement)?.closest?.(".bubble-assistant") as HTMLElement | null;
    if (!bubbleNode) return;
    const params = _retryParams.get(bubbleNode);
    if (!params) return;

    // Mark as attempted so second failure shows apology
    _retryAttempted.add(bubbleNode);

    // Remove the error bubble (user bubble stays)
    bubbleNode.remove();

    // Re-submit
    void submitChatTurn({
      displayUserText: params.displayUserText,
      requestMessage: params.requestMessage,
      responseRoute: params.responseRoute,
      _isRetry: true,
    });
  });

  // ── submitChatTurn ────────────────────────────────────────

  async function submitChatTurn({
    displayUserText, requestMessage,
    responseRoute = decisionResponseRoute,
    _isRetry = false,
  }: { displayUserText: string; requestMessage: string; responseRoute?: string; _isRetry?: boolean }) {
    const visibleMessage = String(displayUserText || "").trim();
    const effectiveMessage = String(requestMessage || "").trim();
    if (!visibleMessage || !effectiveMessage) return;
    const isRetryAttempt = _isRetry;

    const normalizedResponseRoute =
      String(responseRoute || decisionResponseRoute).trim().toLowerCase() || decisionResponseRoute;
    setTurnState("request-pending");
    state.lastUserMessage = effectiveMessage;
    state.lastSubmittedUserMessage = visibleMessage;
    state.activeChatRunId = "";
    const clientTurnId = buildClientTurnId();
    const payload: Record<string, unknown> = {
      message: effectiveMessage, pais: "colombia", primary_scope_mode: "global_overlay",
      response_route: normalizedResponseRoute, debug: Boolean(debugInput?.checked),
      client_turn_id: clientTurnId,
    };
    const activeSessionId = getActiveSessionId();
    if (activeSessionId) payload.session_id = activeSessionId;

    // next_v4 §3 Option A / §4 Level 1 — when a prior assistant turn anchored
    // a topic, forward it as `topic` so a short follow-up ("¿hay límite anual?")
    // doesn't get re-classified from scratch and trip the v6 coherence gate's
    // primary_off_topic refusal. The backend already treats this as
    // `requested_topic` (a soft hint, not an override) — see
    // src/lia_graph/topic_router.py:691 for the existing retention rule.
    const priorQuestionEntries = Array.isArray(state.questionEntries) ? state.questionEntries : [];
    for (let i = priorQuestionEntries.length - 1; i >= 0; i -= 1) {
      const candidate = String(priorQuestionEntries[i]?.effectiveTopic || "").trim();
      if (candidate) { payload.topic = candidate; break; }
    }

    if (!isRetryAttempt) await addBubble("user", visibleMessage);
    citationCtrl.resetDeferredCitationsContext();
    setCitationsStatus(i18n.t("chat.citations.waitingTurn"));
    metrics.startRequestTimer();
    startThinkingWheel();

    let streamingBubble = null;
    let thinkingWheelStopped = false;
    let streamSawEvent = false;
    let streamedVisibleContent = false;
    let terminalEventHandled = false;
    let activeChatRunId = "";
    let streamMeta: Record<string, unknown> = {
      response_route: normalizedResponseRoute, client_turn_id: clientTurnId,
    };

    function captureChatRunContext(payloadData) {
      if (!payloadData || typeof payloadData !== "object") return;
      const chatRunId = String(payloadData.chat_run_id || "").trim();
      if (chatRunId) { activeChatRunId = chatRunId; state.activeChatRunId = chatRunId; payload.chat_run_id = chatRunId; }
      const sessionId = String(payloadData.session_id || "").trim();
      if (sessionId) setActiveSessionId(sessionId);
    }

    async function addAssistantBubble(text, options = {}) {
      return await addBubble("assistant", text, options);
    }

    function stopPrimaryLoading() {
      if (thinkingWheelStopped) return;
      thinkingWheelStopped = true;
      stopThinkingWheel();
    }

    function ensureStreamingBubble() {
      if (streamingBubble) return streamingBubble;
      streamingBubble = createStreamingAssistantBubble({
        meta: streamMeta, previousUserMessage: visibleMessage,
      });
      return streamingBubble;
    }

    async function finalizeStreamingBubble(finalMarkdown, options = {}) {
      if (!streamingBubble) return false;
      await streamingBubble.finalize({
        finalMarkdown, meta: options.meta, persist: true, previousUserMessage: visibleMessage,
      });
      return true;
    }

    // ── Error payload handler ─────────────────────────────

    async function handleAssistantErrorPayload(payloadData, elapsedMs) {
      const errorObj = payloadData && typeof payloadData.error === "object" ? payloadData.error : null;
      const errorCode = String((errorObj && errorObj.code) || payloadData.error || "request_failed");
      const errorMessage = String((errorObj && errorObj.message) || "No fue posible completar la respuesta.");
      captureChatRunContext(payloadData);
      setActiveSessionId(String(payloadData.session_id || getActiveSessionId() || "").trim());
      const interaction = asInteractionPayload(errorObj?.interaction);
      const isSecondFailure = isRetryAttempt;
      let assistantMessage = "";
      if (isSecondFailure && !interaction) {
        assistantMessage = i18n.t("chat.chat.retryFailed");
      } else if (interaction) {
        assistantMessage = String((errorObj && errorObj.user_message) || errorMessage || i18n.t("chat.chat.needMoreData"));
      } else {
        const remediationItems = errorObj && Array.isArray(errorObj.remediation)
          ? errorObj.remediation.filter((item) => typeof item === "string" && item.trim()) : [];
        const remediationText = remediationItems.length > 0
          ? `\n\nSiguiente paso:\n- ${remediationItems.slice(0, 3).join("\n- ")}` : "";
        assistantMessage = `${i18n.t("common.error")} ${errorCode}: ${errorMessage}${remediationText}`;
      }
      state.lastAssistantAnswerMarkdown = assistantMessage;
      const renderedInStreamingBubble = await finalizeStreamingBubble(assistantMessage, {
        meta: buildAssistantBubbleMeta({ ...payloadData, response_route: normalizedResponseRoute }, visibleMessage),
      });
      if (!renderedInStreamingBubble) {
        await addAssistantBubble(assistantMessage, { previousUserMessage: visibleMessage });
      }
      // Mark non-interaction errors as retryable (first attempt only)
      if (!interaction && !isSecondFailure) {
        const retryTarget = findLastAssistantBubble();
        markBubbleRetryable(retryTarget, {
          displayUserText: visibleMessage,
          requestMessage: effectiveMessage,
          responseRoute: normalizedResponseRoute,
        });
      }
      void metrics.recordUserMilestone("main_chat_displayed", {
        source: "assistant_error", status: "error", details: { code: errorCode },
      });
      if (diagnosticsNode) diagnosticsNode.textContent = safeDebugString(payloadData, "No fue posible serializar error de request.");
      if (runtimeLatencyNode) runtimeLatencyNode.textContent = formatDurationSeconds(elapsedMs ?? Number.NaN);
      if (interaction) {
        const clarState = buildClarificationNormativeState(i18n, interaction);
        citationCtrl.clearNormativeSupportState({
          placeholderText: clarState.placeholder, statusText: clarState.status,
          canLoadOnDemand: false, persistSnapshot: true,
        });
      } else {
        citationCtrl.clearNormativeSupportState({
          placeholderText: i18n.t("chat.citations.none"), statusText: i18n.t("chat.citations.turnError"),
          canLoadOnDemand: false, persistSnapshot: true,
        });
      }
      persistActiveSessionSnapshot?.();
      setTurnState("error");
      terminalEventHandled = true;
    }

    // ── Success payload handler ───────────────────────────

    async function handleAssistantSuccessPayload(payloadData, elapsedMs) {
      const assistantAnswer = stripInlineEvidenceAnnotations(
        String(payloadData.answer_markdown || i18n.t("chat.chat.defaultAnswer")),
      );
      const resolvedTopic = String(payloadData.effective_topic || payloadData.topic || payload.topic || "").trim() || undefined;
      const resolvedPais = String(payloadData.pais || payload.pais || "colombia").trim() || "colombia";
      state.lastAssistantAnswerMarkdown = String(assistantAnswer || "").trim();
      captureChatRunContext(payloadData);
      setActiveSessionId(String(
        payloadData.session_id || payloadData.session?.session_id || getActiveSessionId() || "",
      ).trim());
      const mentionCitations = mergeCitations(
        extractUserFormMentionCitations(visibleMessage),
        extractMentionCitations(assistantAnswer),
      );
      const assistantMeta = buildAssistantBubbleMeta(
        { ...payloadData, response_route: normalizedResponseRoute }, visibleMessage,
      );
      const renderedInStreamingBubble = await finalizeStreamingBubble(assistantAnswer, { meta: assistantMeta });
      let finalBubbleNode: HTMLElement | null = null;
      if (!renderedInStreamingBubble) {
        finalBubbleNode = await addAssistantBubble(assistantAnswer, { previousUserMessage: visibleMessage, meta: assistantMeta, skipScroll: true });
      } else {
        finalBubbleNode = streamingBubble?.getNode() ?? null;
      }
      // Smart scroller handles scroll position — no forced scroll here to respect
      // the user's reading position during streaming.
      void metrics.recordUserMilestone("main_chat_displayed", {
        source: "assistant_success", status: "ok", details: { response_route: normalizedResponseRoute },
      });
      try {
        citationCtrl.setDeferredCitationsContext(
          {
            trace_id: String(payloadData.trace_id || "").trim(),
            message: effectiveMessage, assistant_answer: assistantAnswer,
            topic: resolvedTopic, pais: resolvedPais, primary_scope_mode: payload.primary_scope_mode,
          },
          Array.isArray(payloadData.support_citations) ? payloadData.support_citations : payloadData.citations,
          mentionCitations,
        );
      } catch (e) { console.error("setDeferredCitationsContext failed:", e); }
      try {
        onChatSuccess?.({
          traceId: String(payloadData.trace_id || "").trim(),
          message: effectiveMessage, assistantAnswer, topic: resolvedTopic, pais: resolvedPais,
        });
      } catch (e) { console.error("onChatSuccess callback failed:", e); }
      try { metrics.updateRuntimePanel(payloadData, elapsedMs); } catch (e) { console.error("updateRuntimePanel failed:", e); }
      try { persistActiveSessionSnapshot?.(); } catch (e) { console.error("persistActiveSessionSnapshot failed:", e); }
      try {
        if (diagnosticsNode) {
          if (debugInput?.checked) {
            const debugJson = safeDebugString(payloadData.diagnostics || {}, "Debug activo sin payload serializable.");
            const prefix = state.buildInfoLine ? `${state.buildInfoLine}\n` : "";
            diagnosticsNode.textContent = `${prefix}${buildOverlayDebugLine(payloadData)}\n\n${debugJson}`;
          } else {
            diagnosticsNode.textContent = state.buildInfoLine || i18n.t("chat.debug.off");
          }
        }
      } catch (e) { console.error("Debug panel update failed:", e); }
      terminalEventHandled = true;
    }

    // ── Streaming submission ──────────────────────────────

    async function submitViaStreaming() {
      const watchdog = createRequestWatchdog({
        initialTimeoutMs: STREAM_INITIAL_TIMEOUT_MS, idleTimeoutMs: STREAM_IDLE_TIMEOUT_MS,
      });
      watchdog.start();
      try {
        const streamHeaders: Record<string, string> = { "Content-Type": "application/json" };
        const token = getApiAccessToken();
        if (token) streamHeaders["Authorization"] = `Bearer ${token}`;
        const response = await fetch("/api/chat/stream", {
          method: "POST", headers: streamHeaders,
          body: JSON.stringify(payload), signal: watchdog.signal,
        });
        watchdog.touch();
        if (!response.ok || !isEventStreamResponse(response) || !response.body) {
          throw new Error("stream_transport_unavailable");
        }
        let sawTerminalEvent = false;
        await consumeEventStream(response, async ({ event, data }) => {
          watchdog.touch();
          streamSawEvent = true;
          const payloadData = data && typeof data === "object" ? data : {};
          if (event === "meta") {
            streamMeta = { ...streamMeta, ...(payloadData || {}) };
            captureChatRunContext(payloadData);
            if (payloadData.session_id) setActiveSessionId(String(payloadData.session_id || "").trim());
            return;
          }
          if (event === "status") {
            if (streamedVisibleContent) return;
            const statusMessage = String(payloadData.message || "").trim();
            if (statusMessage) { const bubble = ensureStreamingBubble(); bubble?.setStatus(statusMessage); }
            return;
          }
          if (event === "citations_preview") {
            // W2 Phase 7 — surface retrieved normativa as muted placeholders
            // while compose is still running. Desktop only; mobile adapter
            // ignores the dedicated lia:citations-preview event. The final
            // `final` event will overwrite these placeholders atomically.
            if (typeof renderCitationsPreview === "function") {
              const candidates = Array.isArray(payloadData.candidates) ? payloadData.candidates : [];
              renderCitationsPreview(candidates);
            }
            return;
          }
          if (event === "answer_block") {
            const markdown = stripInlineEvidenceAnnotations(String(payloadData.markdown || ""));
            if (!markdown.trim()) return;
            const bubble = ensureStreamingBubble();
            if (!bubble) return;
            bubble.clearStatus();
            await bubble.appendMarkdownBlock(markdown);
            streamedVisibleContent = true;
            stopPrimaryLoading();
            return;
          }
          if (event === "answer_replace") {
            const markdown = stripInlineEvidenceAnnotations(String(payloadData.markdown || ""));
            if (!markdown.trim()) return;
            const bubble = ensureStreamingBubble();
            if (!bubble) return;
            bubble.clearStatus();
            await bubble.replaceMarkdown(markdown);
            streamedVisibleContent = true;
            stopPrimaryLoading();
            return;
          }
          if (event === "final") {
            sawTerminalEvent = true;
            const elapsedMs = metrics.stopRequestTimer();
            stopPrimaryLoading();
            await handleAssistantSuccessPayload(payloadData, elapsedMs);
            return { stop: true };
          }
          if (event === "error") {
            sawTerminalEvent = true;
            const elapsedMs = metrics.stopRequestTimer();
            stopPrimaryLoading();
            await handleAssistantErrorPayload(payloadData, elapsedMs);
            return { stop: true };
          }
        }, { onActivity: () => watchdog.touch() });
        if (!sawTerminalEvent) throw new Error("stream_incomplete");
      } catch (error) {
        watchdog.rethrowIfAborted(error);
      } finally {
        watchdog.stop();
      }
    }

    // ── Buffered fallback ─────────────────────────────────

    async function submitViaBufferedFallback() {
      const chatResult = await postJson("/api/chat", payload);
      let { response, data } = chatResult;
      let payloadData = data && typeof data === "object" ? data : {};
      captureChatRunContext(payloadData);
      if (response.status === 202) {
        const resumeChatRunId = String(payloadData.chat_run_id || activeChatRunId || "").trim();
        if (resumeChatRunId) {
          const resumed = await waitForChatRunCompletion(resumeChatRunId);
          response = resumed.response;
          data = resumed.data;
          payloadData = data && typeof data === "object" ? data : {};
          captureChatRunContext(payloadData);
        }
      }
      const elapsedMs = metrics.stopRequestTimer();
      stopPrimaryLoading();
      if (!response.ok) { await handleAssistantErrorPayload(payloadData, elapsedMs); return; }
      await handleAssistantSuccessPayload(payloadData, elapsedMs);
    }

    // ── Main try/catch ────────────────────────────────────

    try {
      try {
        await submitViaStreaming();
      } catch (streamError) {
        if (!streamedVisibleContent && isRecoverableStreamError(streamError)) {
          await submitViaBufferedFallback();
        } else { throw streamError; }
      }
    } catch (error) {
      const elapsedMs = metrics.stopRequestTimer();
      const errorMessage = error && typeof error === "object" && "message" in error
        ? String((error as Error).message || error) : String(error);
      if (streamedVisibleContent && state.lastAssistantAnswerMarkdown) {
        if (runtimeLatencyNode) runtimeLatencyNode.textContent = formatDurationSeconds(elapsedMs ?? Number.NaN);
        const fallbackContext = {
          trace_id: "", message: effectiveMessage,
          assistant_answer: state.lastAssistantAnswerMarkdown,
          topic: streamMeta.effective_topic || streamMeta.topic || payload.topic,
          pais: streamMeta.pais || payload.pais,
          primary_scope_mode: payload.primary_scope_mode,
        };
        const mentionCits = mergeCitations(
          extractUserFormMentionCitations(visibleMessage),
          extractMentionCitations(state.lastAssistantAnswerMarkdown),
        );
        if (mentionCits.length > 0) {
          state.citationRequestContext = fallbackContext;
          state.deferredCitationsFallback = [];
          state.deferredMentionCitations = asCitationArray(mentionCits);
          state.deferredCitationsCache = asCitationArray(mentionCits);
          state.deferredCitationsCacheKey = "";
          citationCtrl.applyNormativeSupportView({
            citations: mentionCits, placeholderText: "",
            statusText: `Mostrando ${mentionCits.length} referencias normativas detectadas en este turno.`,
            canLoadOnDemand: true,
          });
        } else {
          state.citationRequestContext = fallbackContext;
          citationCtrl.clearNormativeSupportState({
            placeholderText: i18n.t("chat.citations.none"),
            statusText: i18n.t("chat.citations.connectionError"),
            canLoadOnDemand: true, persistSnapshot: true, resetStoredState: false,
          });
        }
        setTurnState(deriveReadyState());
      } else {
        const isSecondFailure = isRetryAttempt;
        const connectionErrorMessage = isSecondFailure
          ? i18n.t("chat.chat.retryFailed")
          : i18n.t("chat.chat.connectionError", { message: errorMessage });
        state.lastAssistantAnswerMarkdown = connectionErrorMessage;
        const rendered = await finalizeStreamingBubble(connectionErrorMessage);
        if (!rendered) await addAssistantBubble(connectionErrorMessage, { previousUserMessage: visibleMessage });
        if (!isSecondFailure) {
          const retryTarget = findLastAssistantBubble();
          markBubbleRetryable(retryTarget, {
            displayUserText: visibleMessage,
            requestMessage: effectiveMessage,
            responseRoute: normalizedResponseRoute,
          });
        }
        if (runtimeLatencyNode) runtimeLatencyNode.textContent = formatDurationSeconds(elapsedMs ?? Number.NaN);
        if (runtimeModelNode) runtimeModelNode.textContent = i18n.t("common.notAvailable");
        citationCtrl.clearNormativeSupportState({
          placeholderText: i18n.t("chat.citations.none"),
          statusText: i18n.t("chat.citations.connectionError"),
          canLoadOnDemand: false, persistSnapshot: true,
        });
        setTurnState("error");
      }
      console.error("Chat flow failed:", error);
    } finally {
      stopPrimaryLoading();
      metrics.stopRequestTimer();
      if (!terminalEventHandled && !streamSawEvent) setTurnState("error");
      else setTurnState(deriveReadyState());
      focusComposer();
    }
  }

  // ── Public API ──────────────────────────────────────────

  return {
    getCurrentNormativeSupportSnapshot: citationCtrl.getCurrentNormativeSupportSnapshot,
    formatDurationSeconds,
    formatTokenUsage,
    hydrateRuntimeModelFromStatus: metrics.hydrateRuntimeModelFromStatus,
    loadBuildInfo: metrics.loadBuildInfo,
    loadCitationsOnDemand: citationCtrl.loadCitationsOnDemand,
    normalizeTokenUsage,
    clearNormativeSupportState: citationCtrl.clearNormativeSupportState,
    recordUserMilestone: metrics.recordUserMilestone,
    resetDeferredCitationsContext: citationCtrl.resetDeferredCitationsContext,
    restoreNormativeSupportState: citationCtrl.restoreNormativeSupportState,
    setActiveChatRunId: (chatRunId: string) => { state.activeChatRunId = String(chatRunId || "").trim(); },
    setConversationTotals: metrics.setConversationTotals,
    setDeferredCitationsContext: citationCtrl.setDeferredCitationsContext,
    startRequestTimer: metrics.startRequestTimer,
    stopRequestTimer: metrics.stopRequestTimer,
    submitChatTurn,
  };
}
