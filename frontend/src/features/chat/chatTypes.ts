// @ts-nocheck

/**
 * Shared types for the chat feature modules.
 * Extracted from chatApp.ts during decouple-v1 Phase 2.
 */

export interface ConversationTokenTotals {
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
}

export interface ChatState {
  requestTimerInterval: ReturnType<typeof setInterval> | null;
  requestStartedAtMs: number | null;
  latestTurnStartedAtMs: number | null;
  activeChatRunId: string;
  activeCitation: any | null;
  lastUserMessage: string;
  lastAssistantAnswerMarkdown: string;
  lastSubmittedUserMessage: string;
  activeSessionId: string;
  citationRequestContext: any | null;
  deferredCitationsFallback: any[];
  deferredMentionCitations: any[];
  deferredCitationsCache: any[];
  deferredCitationsCacheKey: string;
  deferredCitationsStatusText: string;
  deferredCitationsPlaceholderText: string;
  buildInfoLine: string;
  activeNormaRequestId: number;
  modalStack: any[];
  conversationTokenTotals: ConversationTokenTotals;
  questionEntries: QuestionEntry[];
  activeQuestionId: string;
}

export interface QuestionEntry {
  questionId: string;
  questionText: string;
  userTranscriptIndex: number;
  assistantTranscriptIndex: number;
  traceId: string;
  chatRunId: string;
  effectiveTopic: string;
  pais: string;
  normativeSupport: any | null;
  expertPanelState: any | null;
  updatedAt: string;
  assistantText?: string;
}

export interface QuestionSnapshot {
  sessionId: string;
  tenantId?: string;
  firstQuestion: string;
  transcriptEntries: any[];
  questionEntries: QuestionEntry[];
  activeQuestionId: string;
  normativeSupport: any | null;
  conversationTokenTotals: ConversationTokenTotals;
  lastUserMessage: string;
  lastSubmittedUserMessage: string;
  lastAssistantAnswerMarkdown: string;
  detectedTopic: string;
  threadLabel: string;
}

export interface ExpertPanelLoadOptions {
  traceId: string;
  message: string;
  assistantAnswer?: string;
  normativeArticleRefs?: string[];
  searchSeed?: string;
  searchSeedOrigin?: string;
  topic?: string;
  pais?: string;
}
