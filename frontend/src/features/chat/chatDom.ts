import { queryRequired } from "@/shared/dom/template";

export interface ChatDomNodes {
  chatForm: HTMLFormElement;
  chatLog: HTMLElement;
  chatLogEmptyNode: HTMLElement;
  chatSessionCountNode: HTMLElement;
  chatSessionDrawerNode: HTMLElement;
  chatSessionDrawerPanelNode: HTMLElement;
  chatSessionDrawerToggleNode: HTMLButtonElement;
  chatSplitterEl: HTMLElement | null;
  citationsList: HTMLElement;
  citationsLoadBtn: HTMLButtonElement | null;
  citationsStatusNode: HTMLElement;
  debugInput: HTMLInputElement | null;
  debugSummaryNode: HTMLElement | null;
  diagnosticsNode: HTMLElement | null;
  bubbleTemplate: HTMLTemplateElement;
  expertDetailModalNode: HTMLElement;
  newThreadBtn: HTMLButtonElement;
  expertPanelContentNode: HTMLElement;
  expertPanelStatusNode: HTMLElement;
  expertTooltipNode: HTMLElement;
  expertTooltipShellNode: HTMLElement;
  expertTooltipTriggerNode: HTMLButtonElement;
  interpretationResultsNode: HTMLElement;
  interpretationStatusNode: HTMLElement;
  layoutEl: HTMLElement | null;
  messageInput: HTMLTextAreaElement;
  modalLayer: HTMLElement;
  modalInterpretations: HTMLElement;
  modalNorma: HTMLElement;
  modalSummary: HTMLElement;
  normaAnalysisBtn: HTMLButtonElement;
  normaAnalysisHelperNode: HTMLElement;
  normaBindingForceNode: HTMLElement;
  normaCautionBannerNode: HTMLElement;
  normaCautionBodyNode: HTMLElement;
  normaCautionTitleNode: HTMLElement;
  normaCompanionBtn: HTMLAnchorElement;
  normaCompanionHelperNode: HTMLElement;
  normaCompanionNode: HTMLElement;
  normaFactsNode: HTMLElement;
  normaHelperNode: HTMLElement;
  normaLeadNode: HTMLElement;
  normaLoadingNode: HTMLElement;
  normaOriginalBtn: HTMLButtonElement;
  normaOriginalHelperNode: HTMLElement;
  normaPrimaryNode: HTMLElement;
  normaSectionsNode: HTMLElement;
  normaTitleNode: HTMLElement;
  normaTopbarNode: HTMLElement;
  resetConversationBtn: HTMLButtonElement;
  root: HTMLElement;
  runtimeConversationTokensNode: HTMLElement | null;
  runtimeLatencyNode: HTMLElement | null;
  runtimeModelNode: HTMLElement | null;
  runtimeRequestTimerNode: HTMLElement | null;
  runtimeTurnTokensNode: HTMLElement | null;
  sendBtn: HTMLButtonElement;
  sessionIdBadgeNode: HTMLElement | null;
  sessionStateBadgeNode: HTMLElement | null;
  sessionSwitcherNode: HTMLElement;
  summaryBodyNode: HTMLElement;
  summaryExternalLinkNode: HTMLAnchorElement;
  summaryGroundingNode: HTMLElement;
  summaryModeNode: HTMLElement;
}

export function collectChatDom(root: HTMLElement, backstageScope: ParentNode = document): ChatDomNodes {
  return {
    chatForm: queryRequired<HTMLFormElement>(root, "#chat-form"),
    chatLog: queryRequired<HTMLElement>(root, "#chat-log"),
    chatLogEmptyNode: queryRequired<HTMLElement>(root, "#chat-log-empty"),
    chatSessionCountNode: queryRequired<HTMLElement>(root, "#chat-session-count"),
    chatSessionDrawerNode: queryRequired<HTMLElement>(root, "#chat-session-drawer"),
    chatSessionDrawerPanelNode: queryRequired<HTMLElement>(root, "#chat-session-drawer-panel"),
    chatSessionDrawerToggleNode: queryRequired<HTMLButtonElement>(root, "#chat-session-drawer-toggle"),
    chatSplitterEl: root.querySelector<HTMLElement>(".chat-splitter"),
    citationsList: queryRequired<HTMLElement>(root, "#citations"),
    citationsLoadBtn: root.querySelector<HTMLButtonElement>("#citations-load-btn"),
    citationsStatusNode: queryRequired<HTMLElement>(root, "#citations-status"),
    debugInput: backstageScope.querySelector<HTMLInputElement>("#debug"),
    debugSummaryNode: backstageScope.querySelector<HTMLElement>("#debug-summary"),
    diagnosticsNode: backstageScope.querySelector<HTMLElement>("#diagnostics"),
    bubbleTemplate: queryRequired<HTMLTemplateElement>(root, "#bubble-template"),
    expertDetailModalNode: queryRequired<HTMLElement>(root, "#modal-expert-detail"),
    newThreadBtn: queryRequired<HTMLButtonElement>(root, "#new-thread-btn"),
    expertPanelContentNode: queryRequired<HTMLElement>(root, "#expert-panel-content"),
    expertPanelStatusNode: queryRequired<HTMLElement>(root, "#expert-panel-status"),
    expertTooltipNode: queryRequired<HTMLElement>(root, "#expert-panel-title-tooltip"),
    expertTooltipShellNode: queryRequired<HTMLElement>(root, "#expert-panel-title-tooltip-shell"),
    expertTooltipTriggerNode: queryRequired<HTMLButtonElement>(root, "#expert-panel-title-tooltip-trigger"),
    interpretationResultsNode: queryRequired<HTMLElement>(root, "#interpretation-results"),
    interpretationStatusNode: queryRequired<HTMLElement>(root, "#interpretation-status"),
    layoutEl: root.querySelector<HTMLElement>(".chat-layout"),
    messageInput: queryRequired<HTMLTextAreaElement>(root, "#message"),
    modalLayer: queryRequired<HTMLElement>(root, "#modal-layer"),
    modalInterpretations: queryRequired<HTMLElement>(root, "#modal-interpretations"),
    modalNorma: queryRequired<HTMLElement>(root, "#modal-norma"),
    modalSummary: queryRequired<HTMLElement>(root, "#modal-summary"),
    normaAnalysisBtn: queryRequired<HTMLButtonElement>(root, "#norma-analysis-btn"),
    normaAnalysisHelperNode: queryRequired<HTMLElement>(root, "#norma-analysis-helper"),
    normaBindingForceNode: queryRequired<HTMLElement>(root, "#norma-binding-force"),
    normaCautionBannerNode: queryRequired<HTMLElement>(root, "#norma-caution-banner"),
    normaCautionBodyNode: queryRequired<HTMLElement>(root, "#norma-caution-body"),
    normaCautionTitleNode: queryRequired<HTMLElement>(root, "#norma-caution-title"),
    normaCompanionBtn: queryRequired<HTMLAnchorElement>(root, "#norma-companion-btn"),
    normaCompanionHelperNode: queryRequired<HTMLElement>(root, "#norma-companion-helper"),
    normaCompanionNode: queryRequired<HTMLElement>(root, "#norma-companion"),
    normaFactsNode: queryRequired<HTMLElement>(root, "#norma-facts"),
    normaHelperNode: queryRequired<HTMLElement>(root, "#norma-helper"),
    normaLeadNode: queryRequired<HTMLElement>(root, "#norma-lead"),
    normaLoadingNode: queryRequired<HTMLElement>(root, "#norma-loading"),
    normaOriginalBtn: queryRequired<HTMLButtonElement>(root, "#norma-original-btn"),
    normaOriginalHelperNode: queryRequired<HTMLElement>(root, "#norma-original-helper"),
    normaPrimaryNode: queryRequired<HTMLElement>(root, "#norma-primary"),
    normaSectionsNode: queryRequired<HTMLElement>(root, "#norma-sections"),
    normaTitleNode: queryRequired<HTMLElement>(root, "#norma-title"),
    normaTopbarNode: queryRequired<HTMLElement>(root, "#norma-topbar"),
    resetConversationBtn: queryRequired<HTMLButtonElement>(root, "#reset-conversation-btn"),
    root,
    runtimeConversationTokensNode: backstageScope.querySelector<HTMLElement>("#runtime-conversation-tokens"),
    runtimeLatencyNode: backstageScope.querySelector<HTMLElement>("#runtime-latency"),
    runtimeModelNode: backstageScope.querySelector<HTMLElement>("#runtime-model"),
    runtimeRequestTimerNode: backstageScope.querySelector<HTMLElement>("#runtime-request-timer"),
    runtimeTurnTokensNode: backstageScope.querySelector<HTMLElement>("#runtime-turn-tokens"),
    sendBtn: queryRequired<HTMLButtonElement>(root, "#send-btn"),
    sessionIdBadgeNode: root.querySelector<HTMLElement>("#session-id-badge"),
    sessionStateBadgeNode: root.querySelector<HTMLElement>("#session-state-badge"),
    sessionSwitcherNode: queryRequired<HTMLElement>(root, "#chat-session-switcher"),
    summaryBodyNode: queryRequired<HTMLElement>(root, "#summary-body"),
    summaryExternalLinkNode: queryRequired<HTMLAnchorElement>(root, "#summary-external-link"),
    summaryGroundingNode: queryRequired<HTMLElement>(root, "#summary-grounding"),
    summaryModeNode: queryRequired<HTMLElement>(root, "#summary-mode"),
  };
}
