// @ts-nocheck

/**
 * Pre-controller helpers + types for the chat transcript.
 *
 * Extracted from `transcriptController.ts` during granularize-v2 round 8
 * to graduate the host below 1000 LOC. Everything here is presentation
 * logic — it does not close over controller state, so it is safe to unit
 * test in isolation:
 *
 *   * `ACTION_ICON_SVG_NS` — shared SVG namespace constant.
 *   * `formatBubbleTimestamp` — `YYYY-MM-DDTHH:MMZ` → `"15 abr, 3:24 p.m."`
 *     in Bogotá time.
 *   * `stripFollowupSuggestionLines` — drops the `🔵 ¿También quieres…?`
 *     followup block before clipboard copy.
 *   * `flattenMarkdownForClipboard` — markdown → plain text for
 *     `navigator.clipboard.writeText`.
 *   * `formatConversationCopyPayload` — assembles the full "Pregunta /
 *     Respuesta" copy payload using the i18n runtime for labels.
 *
 * Types exported from here are consumed by `transcriptController.ts` so
 * the controller module stays focused on DOM + event wiring.
 */

import {
  splitAnswerFromFollowupSection,
  stripInlineEvidenceAnnotations,
} from "@/features/chat/formatting";
import type { I18nRuntime } from "@/shared/i18n";
import { bogotaParts } from "@/shared/dates";


export const ACTION_ICON_SVG_NS = "http://www.w3.org/2000/svg";

const _MONTHS_ES = [
  "ene", "feb", "mar", "abr", "may", "jun",
  "jul", "ago", "sep", "oct", "nov", "dic",
];


export function formatBubbleTimestamp(iso: string): string {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "";
  const p = bogotaParts(d);
  const ampm = p.hour >= 12 ? "p.m." : "a.m.";
  const h = p.hour % 12 || 12;
  return `${p.day} ${_MONTHS_ES[p.month]}, ${h}:${String(p.minute).padStart(2, "0")} ${ampm}`;
}


export type BubbleRole = "user" | "assistant";

export type AddBubbleOptions = {
  meta?: Record<string, unknown> | null;
  persist?: boolean;
  skipScroll?: boolean;
  previousUserMessage?: string;
  deferAssistantRender?: boolean;
  onAssistantRenderComplete?: () => void;
  timestamp?: string;
};

export type StreamingAssistantBubbleOptions = {
  meta?: Record<string, unknown> | null;
  previousUserMessage?: string;
};

export type FinalizeStreamingAssistantOptions = {
  finalMarkdown: string;
  meta?: Record<string, unknown> | null;
  persist?: boolean;
  previousUserMessage?: string;
};

export type StreamingAssistantBubbleController = {
  appendMarkdownBlock: (markdown: string) => Promise<void>;
  replaceMarkdown: (markdown: string) => Promise<void>;
  finalize: (options: FinalizeStreamingAssistantOptions) => Promise<void>;
  setStatus: (message: string) => void;
  clearStatus: () => void;
  getNode: () => HTMLElement;
};

export type AssistantBubbleMeta = {
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

export type BubbleScaffold = {
  node: HTMLElement;
  bubbleTextNode: HTMLElement;
  meta: AssistantBubbleMeta;
  timestamp: string;
};

export type FeedbackState = {
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

export type FeedbackGetResponse = {
  feedback?: {
    rating?: number;
  } | null;
};

export type CreateChatTranscriptControllerOptions = {
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


export function stripFollowupSuggestionLines(markdown: unknown): string {
  return splitAnswerFromFollowupSection(markdown).answer;
}


export function flattenMarkdownForClipboard(markdown: unknown): string {
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
  i18n: I18nRuntime,
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
