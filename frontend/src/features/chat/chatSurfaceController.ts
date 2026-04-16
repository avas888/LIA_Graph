import type { I18nRuntime } from "@/shared/i18n";

interface ChatSurfaceState {
  activeSessionId: string;
}

interface ComposerPrefillState {
  text: string;
  shouldSubmit: boolean;
  source: "message" | "prefill";
}

interface CreateChatSurfaceControllerOptions {
  i18n: I18nRuntime;
  state: ChatSurfaceState;
  root: HTMLElement;
  chatLog: HTMLElement;
  chatLogEmptyNode: HTMLElement;
  messageInput: HTMLTextAreaElement;
  sendBtn: HTMLButtonElement;
  resetConversationBtn: HTMLButtonElement;
  newThreadBtn: HTMLButtonElement;
  sessionStateBadgeNode: HTMLElement | null;
  sessionIdBadgeNode: HTMLElement | null;
  debugInput: HTMLInputElement | null;
  debugSummaryNode: HTMLElement | null;
}

export function createChatSurfaceController({
  i18n,
  state,
  root,
  chatLog,
  chatLogEmptyNode,
  messageInput,
  sendBtn,
  resetConversationBtn,
  newThreadBtn,
  sessionStateBadgeNode,
  sessionIdBadgeNode,
  debugInput,
  debugSummaryNode,
}: CreateChatSurfaceControllerOptions) {
  let turnState = "ready-empty";

  function getActiveSessionId(): string {
    return String(state.activeSessionId || "").trim();
  }

  function isTurnInFlight(): boolean {
    return turnState === "request-pending";
  }

  function deriveReadyState(): string {
    return String(messageInput.value || "").trim() ? "ready-draft" : "ready-empty";
  }

  function syncComposerInteractivity(): void {
    const pending = isTurnInFlight();
    root.dataset.turnState = turnState;
    messageInput.disabled = pending;
    sendBtn.disabled = pending || !String(messageInput.value || "").trim();
    resetConversationBtn.disabled = pending;
    newThreadBtn.disabled = pending;
  }

  function setStatusPill(node: HTMLElement | null, label: unknown, tone: unknown): void {
    if (!node) return;
    node.textContent = String(label || "").trim();
    node.className = `status-pill status-pill-${String(tone || "ready").trim() || "ready"}`;
  }

  function updateSessionChrome(): void {
    const sessionId = getActiveSessionId();
    if (turnState === "request-pending") {
      setStatusPill(sessionStateBadgeNode, i18n.t("chat.session.busy"), "busy");
    } else if (sessionId) {
      setStatusPill(sessionStateBadgeNode, i18n.t("chat.session.live"), "live");
    } else {
      setStatusPill(sessionStateBadgeNode, i18n.t("chat.session.ready"), "ready");
    }

    if (sessionIdBadgeNode) {
      sessionIdBadgeNode.textContent = sessionId
        ? i18n.t("chat.session.label", { id: sessionId.slice(0, 8) })
        : i18n.t("chat.session.new");
      sessionIdBadgeNode.title = sessionId || i18n.t("chat.session.new");
    }
  }

  function setActiveSessionId(value: string): void {
    state.activeSessionId = String(value || "").trim();
    updateSessionChrome();
  }

  function setTurnState(nextState: string): void {
    turnState = String(nextState || "ready-empty").trim() || "ready-empty";
    syncComposerInteractivity();
    updateSessionChrome();
  }

  function syncReadyState(): string {
    const nextState = deriveReadyState();
    setTurnState(nextState);
    return nextState;
  }

  function updateWorkspaceControlsSummary(): void {
    if (!debugSummaryNode) return;
    debugSummaryNode.textContent = debugInput?.checked
      ? i18n.t("chat.debug.active")
      : i18n.t("chat.debug.inactive");
  }

  function updateChatLogEmptyState(): void {
    const hasBubbles = Array.from(chatLog.children).some((node) => node.classList.contains("bubble"));
    chatLogEmptyNode.hidden = hasBubbles;
  }

  function resizeComposer(): void {
    const minHeight = 22;
    const maxHeight = 128;
    messageInput.style.height = "auto";
    const nextHeight = Math.min(Math.max(messageInput.scrollHeight, minHeight), maxHeight);
    messageInput.style.height = `${nextHeight}px`;
    messageInput.style.overflowY = messageInput.scrollHeight > maxHeight ? "auto" : "hidden";
  }

  function focusComposer({ preserveSelection = false }: { preserveSelection?: boolean } = {}): void {
    if (isTurnInFlight()) return;
    requestAnimationFrame(() => {
      if (isTurnInFlight()) return;
      messageInput.focus({ preventScroll: true });
      if (!preserveSelection) {
        const length = messageInput.value.length;
        messageInput.setSelectionRange(length, length);
      }
    });
  }

  function consumeComposerPrefillFromUrl(): ComposerPrefillState | null {
    try {
      const params = new URLSearchParams(window.location.search);
      const rawMessage = String(params.get("message") || "").trim();
      const rawPrefill = String(params.get("prefill") || "").trim();
      const source = rawMessage ? "message" : rawPrefill ? "prefill" : "";
      const rawValue = rawMessage || rawPrefill;
      if (!rawValue || !source) return null;
      messageInput.value = rawValue.slice(0, 600);
      resizeComposer();
      const autoSendParam = String(
        params.get("auto_send") || params.get("autosend") || params.get("submit") || "",
      ).trim().toLowerCase();
      const shouldSubmit = source === "message" || ["1", "true", "yes"].includes(autoSendParam);
      params.delete("message");
      params.delete("prefill");
      params.delete("auto_send");
      params.delete("autosend");
      params.delete("submit");
      const nextQuery = params.toString();
      const nextUrl = `${window.location.pathname}${nextQuery ? `?${nextQuery}` : ""}${window.location.hash || ""}`;
      window.history.replaceState({}, "", nextUrl);
      return {
        text: messageInput.value,
        shouldSubmit,
        source: source as ComposerPrefillState["source"],
      };
    } catch (_error) {
      return null;
    }
  }

  function initializeSurface(): void {
    updateWorkspaceControlsSummary();
    updateChatLogEmptyState();
    resizeComposer();
    syncReadyState();
  }

  return {
    consumeComposerPrefillFromUrl,
    deriveReadyState,
    focusComposer,
    getActiveSessionId,
    initializeSurface,
    isTurnInFlight,
    resizeComposer,
    setActiveSessionId,
    setTurnState,
    syncReadyState,
    updateChatLogEmptyState,
    updateWorkspaceControlsSummary,
  };
}
