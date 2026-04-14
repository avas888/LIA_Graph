import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderChatShell } from "@/app/chat/shell";
import { renderBackstageShell } from "@/app/ops/shell";
import {
  buildNormativeSupportRequestBody,
  formatConversationCopyPayload,
  mountChatApp,
} from "@/features/chat/chatApp";
import { createI18n } from "@/shared/i18n";
import type { I18nRuntime } from "@/shared/i18n";

function renderFullShell(i18n: I18nRuntime): string {
  return renderBackstageShell(i18n) + renderChatShell(i18n);
}

const CHAT_SESSION_INDEX_KEY = "lia_chat_session_index_v1";
const CHAT_SESSION_STATE_KEY_PREFIX = "lia_chat_session_state_v1:";
const WINDOW_CHAT_SESSION_KEY = "lia_chat_window_session_v1";
const LEGACY_TRANSCRIPT_CACHE_KEY = "lia_chat_transcript_v2";
const LEGACY_NORMATIVE_SUPPORT_CACHE_KEY = "lia_chat_normative_support_v1";

function createStorageMock(): Storage {
  const store = new Map<string, string>();
  return {
    get length() {
      return store.size;
    },
    clear() {
      store.clear();
    },
    getItem(key: string) {
      return store.has(key) ? store.get(key) ?? null : null;
    },
    key(index: number) {
      return Array.from(store.keys())[index] ?? null;
    },
    removeItem(key: string) {
      store.delete(key);
    },
    setItem(key: string, value: string) {
      store.set(String(key), String(value));
    },
  };
}

function createRecordingStorageMock(history: Array<{ key: string; value: string }>): Storage {
  const store = new Map<string, string>();
  return {
    get length() {
      return store.size;
    },
    clear() {
      store.clear();
    },
    getItem(key: string) {
      return store.has(key) ? store.get(key) ?? null : null;
    },
    key(index: number) {
      return Array.from(store.keys())[index] ?? null;
    },
    removeItem(key: string) {
      store.delete(key);
    },
    setItem(key: string, value: string) {
      const normalizedKey = String(key);
      const normalizedValue = String(value);
      history.push({ key: normalizedKey, value: normalizedValue });
      store.set(normalizedKey, normalizedValue);
    },
  };
}

function mockJsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function mockChatStreamResponse(
  payload: Record<string, unknown>,
  { terminalEvent = "final" }: { terminalEvent?: "final" | "error" } = {}
): Response {
  const body = [
    `event: meta\ndata: ${JSON.stringify({
      trace_id: String(payload.trace_id || "trace_test"),
      session_id: String(payload.session_id || "chat_test"),
      response_route: String(payload.response_route || "decision"),
    })}\n\n`,
    `event: ${terminalEvent}\ndata: ${JSON.stringify(payload)}\n\n`,
  ].join("");
  return new Response(body, {
    status: 200,
    headers: { "Content-Type": "text/event-stream; charset=utf-8" },
  });
}

async function flushUi(): Promise<void> {
  await Promise.resolve();
  await new Promise((resolve) => window.setTimeout(resolve, 0));
  await Promise.resolve();
}

function deriveFirstQuestion(
  transcriptEntries: Array<{ role: "user" | "assistant"; text: string; meta?: Record<string, unknown> | null }>
): string {
  const entry = transcriptEntries.find((item) => item.role === "user" && String(item.text || "").trim());
  return String(entry?.text || "").trim();
}

function buildQuestionEntry({
  questionId,
  questionText,
  userTranscriptIndex,
  assistantTranscriptIndex,
  traceId,
  normativeSupport = null,
  expertPanelState = null,
}: {
  questionId: string;
  questionText: string;
  userTranscriptIndex: number;
  assistantTranscriptIndex: number;
  traceId: string;
  normativeSupport?: Record<string, unknown> | null;
  expertPanelState?: Record<string, unknown> | null;
}) {
  return {
    questionId,
    questionText,
    userTranscriptIndex,
    assistantTranscriptIndex,
    traceId,
    normativeSupport,
    expertPanelState,
    updatedAt: "2026-03-12T10:00:00.000Z",
  };
}

function seedStoredChatSessions({
  sessions,
  activeSessionId = sessions[0]?.sessionId ?? "",
}: {
  sessions: Array<{
    sessionId: string;
    transcriptEntries: Array<{ role: "user" | "assistant"; text: string; meta?: Record<string, unknown> | null }>;
    normativeSupport?: Record<string, unknown> | null;
    conversationTokenTotals?: { input_tokens: number; output_tokens: number; total_tokens: number };
    lastUserMessage?: string;
    lastSubmittedUserMessage?: string;
    lastAssistantAnswerMarkdown?: string;
    firstQuestion?: string;
    updatedAt?: string;
    questionEntries?: Record<string, unknown>[];
    activeQuestionId?: string;
  }>;
  activeSessionId?: string;
}): void {
  const summaries = sessions.map((session, index) => ({
    sessionId: session.sessionId,
    firstQuestion: session.firstQuestion || deriveFirstQuestion(session.transcriptEntries),
    updatedAt: session.updatedAt || `2026-03-12T0${Math.min(index, 9)}:00:00.000Z`,
  }));
  localStorage.setItem(
    CHAT_SESSION_INDEX_KEY,
    JSON.stringify({
      version: 1,
      activeSessionId,
      sessions: summaries,
    })
  );

  sessions.forEach((session, index) => {
    localStorage.setItem(
      `${CHAT_SESSION_STATE_KEY_PREFIX}${session.sessionId}`,
      JSON.stringify({
        version: 1,
        sessionId: session.sessionId,
        firstQuestion: session.firstQuestion || deriveFirstQuestion(session.transcriptEntries),
        updatedAt: session.updatedAt || `2026-03-12T0${Math.min(index, 9)}:00:00.000Z`,
        transcriptEntries: session.transcriptEntries,
        questionEntries: session.questionEntries,
        activeQuestionId: session.activeQuestionId,
        normativeSupport: session.normativeSupport ?? null,
        conversationTokenTotals: session.conversationTokenTotals || {
          input_tokens: 0,
          output_tokens: 0,
          total_tokens: 0,
        },
        lastUserMessage:
          session.lastUserMessage ||
          deriveFirstQuestion(session.transcriptEntries) ||
          String(session.transcriptEntries.at(-1)?.text || ""),
        lastSubmittedUserMessage:
          session.lastSubmittedUserMessage ||
          deriveFirstQuestion(session.transcriptEntries) ||
          String(session.transcriptEntries.at(-1)?.text || ""),
        lastAssistantAnswerMarkdown:
          session.lastAssistantAnswerMarkdown ||
          String(
            [...session.transcriptEntries]
              .reverse()
              .find((entry) => entry.role === "assistant" && String(entry.text || "").trim())?.text || ""
          ),
      })
    );
  });
}

function installFetchMock(): void {
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/llm/status") {
        return Promise.resolve(
          mockJsonResponse({
            llm_runtime: {
              model: "gemini-2.5-flash",
              selected_type: "gemini",
              selected_provider: "gemini_primary",
            },
          })
        );
      }
      if (url === "/api/build-info") {
        return Promise.resolve(mockJsonResponse({ build_info: {} }));
      }
      if (url === "/api/chat/stream") {
        return Promise.resolve(
          mockChatStreamResponse({
            trace_id: "trace_chat_default",
            session_id: "chat_default",
            answer_markdown: "Respuesta por stream de prueba.",
            followup_queries: [],
            citations: [],
            diagnostics: {},
            metrics: {
              llm_runtime: {
                model: "gemini-2.5-flash",
                selected_type: "gemini",
                selected_provider: "gemini_primary",
              },
              token_usage: {
                turn: { input_tokens: 1, output_tokens: 1, total_tokens: 2 },
              },
              conversation: {
                token_usage_total: { input_tokens: 1, output_tokens: 1, total_tokens: 2 },
              },
            },
          })
        );
      }
      if (url.startsWith("/api/feedback")) {
        return Promise.resolve(mockJsonResponse({ feedback: null }));
      }
      return Promise.resolve(mockJsonResponse({}));
    })
  );
}

function installFetchMockWithChatQueue(
  chatResponses: Array<{ payload: Record<string, unknown>; status?: number }>,
  capturedChatBodies: Array<Record<string, unknown>> = []
): void {
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/llm/status") {
        return Promise.resolve(
          mockJsonResponse({
            llm_runtime: {
              model: "gemini-2.5-flash",
              selected_type: "gemini",
              selected_provider: "gemini_primary",
            },
          })
        );
      }
      if (url === "/api/build-info") {
        return Promise.resolve(mockJsonResponse({ build_info: {} }));
      }
      if (url === "/api/chat/stream") {
        const rawBody = typeof init?.body === "string" ? init.body : "";
        capturedChatBodies.push(rawBody ? JSON.parse(rawBody) : {});
        const next = chatResponses.shift();
        if (!next) {
          throw new Error("Unexpected /api/chat/stream call without queued mock response.");
        }
        return Promise.resolve(
          mockChatStreamResponse(next.payload, {
            terminalEvent: (next.status ?? 200) >= 400 ? "error" : "final",
          })
        );
      }
      if (url === "/api/chat") {
        const rawBody = typeof init?.body === "string" ? init.body : "";
        capturedChatBodies.push(rawBody ? JSON.parse(rawBody) : {});
        const next = chatResponses.shift();
        if (!next) {
          throw new Error("Unexpected /api/chat call without queued mock response.");
        }
        return Promise.resolve(mockJsonResponse(next.payload, next.status ?? 200));
      }
      if (url.startsWith("/api/feedback")) {
        return Promise.resolve(mockJsonResponse({ feedback: null }));
      }
      return Promise.resolve(mockJsonResponse({}));
    })
  );
}

function installFetchMockWithBuildInfo(buildInfo: Record<string, unknown>): void {
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/llm/status") {
        return Promise.resolve(
          mockJsonResponse({
            llm_runtime: {
              model: "gemini-2.5-flash",
              selected_type: "gemini",
              selected_provider: "gemini_primary",
            },
          })
        );
      }
      if (url === "/api/build-info") {
        return Promise.resolve(mockJsonResponse({ build_info: buildInfo }));
      }
      if (url === "/api/chat/stream") {
        return Promise.resolve(
          mockChatStreamResponse({
            trace_id: "trace_chat_build_info",
            session_id: "chat_build_info",
            answer_markdown: "Respuesta por stream de build-info.",
            followup_queries: [],
            citations: [],
            diagnostics: {},
            metrics: {
              llm_runtime: {
                model: "gemini-2.5-flash",
                selected_type: "gemini",
                selected_provider: "gemini_primary",
              },
              token_usage: {
                turn: { input_tokens: 1, output_tokens: 1, total_tokens: 2 },
              },
              conversation: {
                token_usage_total: { input_tokens: 1, output_tokens: 1, total_tokens: 2 },
              },
            },
          })
        );
      }
      if (url.startsWith("/api/feedback")) {
        return Promise.resolve(mockJsonResponse({ feedback: null }));
      }
      return Promise.resolve(mockJsonResponse({}));
    })
  );
}

function makeChatSuccessPayload({
  answerMarkdown,
  followupQueries = [
    "¿Quieres cronograma exacto por NIT?",
    "¿Quieres checklist de soportes y controles?",
  ],
  traceId = "trace_chat_1",
  sessionId = "chat_session_1",
}: {
  answerMarkdown: string;
  followupQueries?: string[];
  traceId?: string;
  sessionId?: string;
}): Record<string, unknown> {
  return {
    trace_id: traceId,
    run_id: `run_${traceId}`,
    session_id: sessionId,
    answer_markdown: answerMarkdown,
    answer_concise: answerMarkdown,
    followup_queries: followupQueries,
    citations: [],
    confidence: { score: 0.86, mode: "guided" },
    diagnostics: {},
    llm_runtime: {
      model: "gemini-2.5-flash",
      selected_type: "gemini",
      selected_provider: "gemini_primary",
      attempts: [{ selected: "gemini_primary", status: "ok" }],
    },
    token_usage: {
      turn: { input_tokens: 12, output_tokens: 20, total_tokens: 32, source: "estimated" },
      llm: { input_tokens: 120, output_tokens: 80, total_tokens: 200, source: "provider" },
    },
    timing: {
      pipeline_total_ms: 321.5,
      stages_ms: { compose: 88.2 },
    },
    metrics: {
      llm_runtime: {
        model: "gemini-2.5-flash",
        selected_type: "gemini",
        selected_provider: "gemini_primary",
      },
      token_usage: {
        turn: { input_tokens: 12, output_tokens: 20, total_tokens: 32, source: "estimated" },
      },
      latency_ms: 321.5,
      conversation: {
        session_id: sessionId,
        token_usage_total: { input_tokens: 12, output_tokens: 20, total_tokens: 32 },
      },
      mention_resolution: { mentions_detected: 0, mentions_resolved_to_doc: 0 },
      primary_scope_mode: "global_overlay",
      primary_overlay: { overlay_applied: false, overlay_selected_count: 0, overlay_candidates_count: 0 },
    },
  };
}

describe("chat assistant actions", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
    vi.restoreAllMocks();
    const storage = createStorageMock();
    const sessionStorageMock = createStorageMock();
    vi.stubGlobal("localStorage", storage);
    vi.stubGlobal("sessionStorage", sessionStorageMock);
    Object.defineProperty(window, "localStorage", {
      configurable: true,
      value: storage,
    });
    Object.defineProperty(window, "sessionStorage", {
      configurable: true,
      value: sessionStorageMock,
    });
    vi.stubGlobal(
      "matchMedia",
      vi.fn().mockReturnValue({
        matches: true,
        addEventListener() {},
        removeEventListener() {},
        addListener() {},
        removeListener() {},
      })
    );
    Object.defineProperty(window.navigator, "clipboard", {
      configurable: true,
      value: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
    });
    installFetchMock();
  });

  it("formats question and answer clipboard payload without raw markdown artifacts", () => {
    const i18n = createI18n("es-CO");

    const payload = formatConversationCopyPayload(
      "¿Qué debo revisar primero?",
      [
        "### Resumen",
        "",
        "1. **Paso inicial:** Revise soportes y calendario.",
        "",
        "* **Formulario 110:** Prepare la versión final.",
        "",
        "Sugerencias de consultas adicionales",
        "6.1 ¿Quieres que lo bajemos a cronograma exacto por tipo de contribuyente y NIT?",
      ].join("\n"),
      i18n
    );

    expect(payload).toContain("Consulta:\n\n¿Qué debo revisar primero?");
    expect(payload).toContain("Respuesta:\n\nResumen");
    expect(payload).toContain("1. Paso inicial: Revise soportes y calendario.");
    expect(payload).toContain("• Formulario 110: Prepare la versión final.");
    expect(payload).not.toContain("**");
    expect(payload).not.toContain("6.1");
  });

  it("keeps visible substantive numbering that is not an explicit followup section", async () => {
    const i18n = createI18n("es-CO");
    seedStoredChatSessions({
      sessions: [
        {
          sessionId: "chat_numbering_1",
          transcriptEntries: [
            { role: "user", text: "¿Qué debo comparar?" },
            {
              role: "assistant",
              text: "6.1 Régimen SIMPLE\n\nCompare tarifa, retenciones y margen antes de decidir.",
              meta: { session_id: "chat_numbering_1" },
            },
          ],
        },
      ],
    });
    document.body.innerHTML = renderFullShell(i18n);

    mountChatApp(document.body, { i18n });
    await flushUi();

    expect(document.querySelector(".bubble-assistant .bubble-text")?.textContent).toContain("6.1 Régimen SIMPLE");
    expect(document.querySelector(".bubble-assistant .bubble-text")?.textContent).toContain(
      "Compare tarifa, retenciones y margen antes de decidir."
    );
  });

  it("renders complex assistant answers with ordered sections and nested bullets in the chat bubble", async () => {
    const i18n = createI18n("es-CO");
    seedStoredChatSessions({
      sessions: [
        {
          sessionId: "chat_nested_sections_1",
          transcriptEntries: [
            { role: "user", text: "Necesito la estructura completa." },
            {
              role: "assistant",
              text: [
                "1. Titulo de seccion",
                "1.1 Sub-seccion",
                "1.1.1 Sub-sub-seccion 1: Aca texto.",
                "1.1.2 Sub-sub-seccion 2",
                "1.1.2.1 Sub-sub-sub seccion A: Va aca.",
              ].join("\n"),
              meta: { session_id: "chat_nested_sections_1" },
            },
          ],
        },
      ],
    });
    document.body.innerHTML = renderFullShell(i18n);

    mountChatApp(document.body, { i18n });
    await flushUi();

    const bubble = document.querySelector(".bubble-assistant .bubble-text");
    expect(bubble?.querySelectorAll("ol")).toHaveLength(1);
    expect(bubble?.querySelectorAll("ol > li")).toHaveLength(1);
    expect(bubble?.querySelectorAll("ol > li > ul")).toHaveLength(1);
    expect(bubble?.querySelectorAll("ol > li > ul > li")).toHaveLength(1);
    expect(bubble?.querySelectorAll("ol > li > ul > li > ul > li")).toHaveLength(2);
    expect(bubble?.textContent).toContain("Titulo de seccion:");
    expect(bubble?.textContent).toContain("Sub-sub-sub seccion A:");
  });

  it("clears cached chat automatically when dev boot nonce changes", async () => {
    const i18n = createI18n("es-CO");
    localStorage.setItem("lia_dev_boot_nonce_v1", "boot-old");
    localStorage.setItem(
      LEGACY_TRANSCRIPT_CACHE_KEY,
      JSON.stringify([
        { role: "user", text: "¿Qué debo comparar?" },
        {
          role: "assistant",
          text: "Respuesta previa persistida",
          meta: { session_id: "chat_prev_1" },
        },
      ])
    );
    installFetchMockWithBuildInfo({
      reset_chat_on_dev_boot: true,
      dev_boot_nonce: "boot-new",
    });
    document.body.innerHTML = renderFullShell(i18n);

    mountChatApp(document.body, { i18n });
    await flushUi();

    expect(localStorage.getItem(LEGACY_TRANSCRIPT_CACHE_KEY)).toBeNull();
    expect(localStorage.getItem("lia_dev_boot_nonce_v1")).toBe("boot-new");
    expect(document.body.textContent).not.toContain("Respuesta previa persistida");
  });

  it("renders copy first and hides feedback buttons when trace data is missing", async () => {
    const i18n = createI18n("es-CO");
    seedStoredChatSessions({
      sessions: [
        {
          sessionId: "chat_copy_only_1",
          transcriptEntries: [
            { role: "user", text: "¿Qué pasos debo seguir?" },
            {
              role: "assistant",
              text: "### Respuesta\n\n1. **Paso uno:** Reúna la información base.",
              meta: { session_id: "chat_copy_only_1" },
            },
          ],
        },
      ],
    });
    document.body.innerHTML = renderFullShell(i18n);

    mountChatApp(document.body, { i18n });
    await flushUi();

    const actions = document.querySelector(".bubble-assistant .bubble-actions");
    const buttons = Array.from(actions?.querySelectorAll(".bubble-action-btn") || []);

    expect(actions?.hasAttribute("hidden")).toBe(false);
    expect(buttons).toHaveLength(1);
    expect(buttons[0]?.getAttribute("data-action")).toBe("copy");
    expect(buttons[0]?.querySelector("svg")).not.toBeNull();
    expect(buttons[0]?.textContent?.trim()).toBe("");
  });

  it("copies paired question and response, and renders icon-only copy plus feedback buttons", async () => {
    const i18n = createI18n("es-CO");
    const clipboardWrite = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(window.navigator, "clipboard", {
      configurable: true,
      value: { writeText: clipboardWrite },
    });

    const assistantAnswer = [
      "### Respuesta operativa",
      "",
      "1. **Paso uno:** Verifique ingresos y costos.",
      "",
      "* **Formulario 110:** Presente la declaración.",
    ].join("\n");
    seedStoredChatSessions({
      sessions: [
        {
          sessionId: "chat_copy_1",
          transcriptEntries: [
            { role: "user", text: "¿Qué hago con la renta 2026?" },
            {
              role: "assistant",
              text: assistantAnswer,
              meta: {
                trace_id: "trace_copy_1",
                session_id: "chat_copy_1",
                question_text: "¿Qué hago con la renta 2026?",
              },
            },
          ],
        },
      ],
    });
    document.body.innerHTML = renderFullShell(i18n);

    mountChatApp(document.body, { i18n });
    await flushUi();

    const actions = document.querySelector(".bubble-assistant .bubble-actions");
    const copyButton = actions?.querySelector<HTMLButtonElement>('.bubble-action-btn[data-action="copy"]');
    const ratingPrompt = actions?.querySelector<HTMLElement>(".bubble-rating-prompt");
    const ratingButtons = Array.from(actions?.querySelectorAll<HTMLButtonElement>(".bubble-rating-btn") || []);

    expect(copyButton).not.toBeNull();
    expect(copyButton?.querySelector("svg")).not.toBeNull();
    expect(copyButton?.textContent?.trim()).toBe("");
    expect(ratingPrompt?.textContent).toBe("¿Cómo te pareció la respuesta?");
    expect(ratingButtons.map((button) => button.getAttribute("data-rating"))).toEqual(["1", "2", "3", "4", "5"]);

    copyButton?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await flushUi();

    expect(clipboardWrite).toHaveBeenCalledWith(
      [
        "Consulta:",
        "",
        "¿Qué hago con la renta 2026?",
        "",
        "Respuesta:",
        "",
        "Respuesta operativa",
        "",
        "1. Paso uno: Verifique ingresos y costos.",
        "• Formulario 110: Presente la declaración.",
      ].join("\n")
    );
    expect(actions?.querySelector(".bubble-action-status")?.textContent).toBe("Copiado");
  });

  it("builds normative support requests with both user message and assistant answer", () => {
    const payload = buildNormativeSupportRequestBody({
      trace_id: "trace_norm_1",
      message: "¿Qué pasos debo seguir para presentar renta?",
      assistant_answer: "Respuesta operativa sin cita estructurada en el payload.",
      topic: "declaracion_renta",
      pais: "colombia",
      primary_scope_mode: "strict_topic",
    });

    expect(payload.message).toBe("¿Qué pasos debo seguir para presentar renta?");
    expect(payload.assistant_answer).toBe("Respuesta operativa sin cita estructurada en el payload.");
    expect(payload.primary_scope_mode).toBe("strict_topic");
  });

  it("omits topic from normative support requests when the chat turn has no detected topic", () => {
    const payload = buildNormativeSupportRequestBody({
      trace_id: "trace_norm_2",
      message: "Necesito orientación general",
      assistant_answer: "Respuesta general",
      pais: "colombia",
    });

    expect(payload.topic).toBeUndefined();
  });

  it("does not render the fixed legal support pill for decision answers", async () => {
    const chatBodies: Array<Record<string, unknown>> = [];
    installFetchMockWithChatQueue(
      [
        {
          payload: makeChatSuccessPayload({
            traceId: "trace_decision_1",
            sessionId: "chat_legal_pill_1",
            answerMarkdown: "Respuesta operativa inicial para el caso planteado.",
          }),
        },
      ],
      chatBodies
    );

    const i18n = createI18n("es-CO");
    document.body.innerHTML = renderFullShell(i18n);
    mountChatApp(document.body, { i18n });
    await flushUi();

    const messageInput = document.querySelector<HTMLTextAreaElement>("#message");
    const form = document.querySelector<HTMLFormElement>("#chat-form");
    expect(messageInput).not.toBeNull();
    expect(form).not.toBeNull();

    messageInput!.value = "¿Qué debo revisar para renta 2026?";
    messageInput!.dispatchEvent(new Event("input", { bubbles: true }));
    form!.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    await flushUi();
    await flushUi();

    const legalSupportButtons = Array.from(document.querySelectorAll<HTMLButtonElement>(".followup-pill")).filter(
      (button) => button.textContent?.trim() === "Cuéntame sobre el soporte legal que contextualiza tu pregunta"
    );
    expect(legalSupportButtons).toHaveLength(0);
    expect(document.body.textContent).not.toContain("Cuéntame sobre el soporte legal que contextualiza tu pregunta");
    expect(chatBodies).toHaveLength(1);
    expect(chatBodies[0]).toMatchObject({
      message: "¿Qué debo revisar para renta 2026?",
      response_route: "decision",
    });
    expect(document.body.textContent).toContain("Respuesta operativa inicial para el caso planteado.");
  });

  it("records response_bubble_highlighted when the final assistant bubble becomes active", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/llm/status") {
        return Promise.resolve(
          mockJsonResponse({
            llm_runtime: {
              model: "gemini-2.5-flash",
              selected_type: "gemini",
              selected_provider: "gemini_primary",
            },
          })
        );
      }
      if (url === "/api/build-info") {
        return Promise.resolve(mockJsonResponse({ build_info: {} }));
      }
      if (url === "/api/chat/stream") {
        return Promise.resolve(
          mockChatStreamResponse({
            ...makeChatSuccessPayload({
              traceId: "trace_bubble_active_1",
              sessionId: "chat_bubble_active_1",
              answerMarkdown: "Respuesta final completa para resaltar la burbuja.",
            }),
            chat_run_id: "cr_bubble_active_1",
          })
        );
      }
      if (url === "/api/chat/runs/cr_bubble_active_1/milestones") {
        return Promise.resolve(mockJsonResponse({ ok: true }));
      }
      if (url.startsWith("/api/feedback")) {
        return Promise.resolve(mockJsonResponse({ feedback: null }));
      }
      return Promise.resolve(mockJsonResponse({}));
    });
    vi.stubGlobal("fetch", fetchMock);

    const i18n = createI18n("es-CO");
    document.body.innerHTML = renderFullShell(i18n);
    mountChatApp(document.body, { i18n });
    await flushUi();

    const messageInput = document.querySelector<HTMLTextAreaElement>("#message");
    const form = document.querySelector<HTMLFormElement>("#chat-form");
    expect(messageInput).not.toBeNull();
    expect(form).not.toBeNull();

    messageInput!.value = "Necesito medir el reborde azul oscuro.";
    messageInput!.dispatchEvent(new Event("input", { bubbles: true }));
    form!.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    await flushUi();
    await flushUi();

    const milestoneCalls = fetchMock.mock.calls.filter(([url]) =>
      String(url) === "/api/chat/runs/cr_bubble_active_1/milestones"
    );
    expect(milestoneCalls.length).toBeGreaterThanOrEqual(2);

    const highlightCall = milestoneCalls.find(([, init]) => {
      const body = typeof init?.body === "string" ? JSON.parse(init.body) : {};
      return body.milestone === "response_bubble_highlighted";
    });
    expect(highlightCall).toBeTruthy();

    const highlightBody = typeof highlightCall?.[1]?.body === "string" ? JSON.parse(highlightCall[1].body) : {};
    expect(highlightBody).toMatchObject({
      milestone: "response_bubble_highlighted",
      source: "bubble_active",
      status: "ok",
      details: { question_id: "trace_bubble_active_1" },
    });
  });

  it("does not regenerate the removed legal support pill when restoring a stored session", async () => {
    const i18n = createI18n("es-CO");
    seedStoredChatSessions({
      sessions: [
        {
          sessionId: "chat_restore_1",
          transcriptEntries: [
            { role: "user", text: "¿Qué debo revisar para renta 2026?" },
            {
              role: "assistant",
              text: "Respuesta restaurada desde cache.",
              meta: {
                trace_id: "trace_restore_1",
                session_id: "chat_restore_1",
                question_text: "¿Qué debo revisar para renta 2026?",
                response_route: "decision",
              },
            },
          ],
        },
      ],
    });
    document.body.innerHTML = renderFullShell(i18n);

    mountChatApp(document.body, { i18n });
    await flushUi();

    const legalSupportButtons = Array.from(document.querySelectorAll<HTMLButtonElement>(".followup-pill")).filter(
      (button) => button.textContent?.trim() === "Cuéntame sobre el soporte legal que contextualiza tu pregunta"
    );
    expect(document.body.textContent).toContain("Respuesta restaurada desde cache.");
    expect(legalSupportButtons).toHaveLength(0);
  });

  it("navigates between persisted questions in the active session and restores normativa plus interpretation", async () => {
    const i18n = createI18n("es-CO");
    seedStoredChatSessions({
      activeSessionId: "chat_session_2",
      sessions: [
        {
          sessionId: "chat_session_2",
          transcriptEntries: [
            { role: "user", text: "¿Qué pasa con dividendos?" },
            {
              role: "assistant",
              text: "Depende de la tarifa del artículo aplicable.",
              meta: { session_id: "chat_session_2", trace_id: "trace_session_1" },
            },
            { role: "user", text: "¿Puedo deducir ICA?" },
            {
              role: "assistant",
              text: "Sí, pero revisa soporte y causalidad.",
              meta: { session_id: "chat_session_2", trace_id: "trace_session_2" },
            },
          ],
          questionEntries: [
            buildQuestionEntry({
              questionId: "trace_session_1",
              questionText: "¿Qué pasa con dividendos?",
              userTranscriptIndex: 0,
              assistantTranscriptIndex: 1,
              traceId: "trace_session_1",
              normativeSupport: {
                citationRequestContext: {
                  trace_id: "trace_session_1",
                  message: "¿Qué pasa con dividendos?",
                  assistant_answer: "Depende de la tarifa del artículo aplicable.",
                  topic: "declaracion_renta",
                  pais: "colombia",
                  primary_scope_mode: "global_overlay",
                },
                fallbackCitations: [
                  {
                    doc_id: "doc_et_240",
                    source_label: "ET art. 240",
                    legal_reference: "ET art. 240",
                    source_provider: "DIAN",
                    authority: "DIAN",
                    source_tier: "Fuente Normativa",
                    knowledge_class: "normative_base",
                    source_type: "official_primary",
                  },
                ],
                mentionCitations: [],
                cachedCitations: [
                  {
                    doc_id: "doc_et_240",
                    source_label: "ET art. 240",
                    legal_reference: "ET art. 240",
                    source_provider: "DIAN",
                    authority: "DIAN",
                    source_tier: "Fuente Normativa",
                    knowledge_class: "normative_base",
                    source_type: "official_primary",
                  },
                ],
                statusText: "Mostrando 1 referencias normativas detectadas en este turno.",
                placeholderText: "",
              },
              expertPanelState: {
                status: "populated",
                loadOptions: {
                  traceId: "trace_session_1",
                  message: "¿Qué pasa con dividendos?",
                  assistantAnswer: "Depende de la tarifa del artículo aplicable.",
                  normativeArticleRefs: ["art_240"],
                  topic: "declaracion_renta",
                  pais: "colombia",
                },
                response: {
                  ok: true,
                  trace_id: "trace_session_1",
                  groups: [
                    {
                      article_ref: "et_art_240",
                      classification: "concordancia",
                      summary_signal: "Interpretación sobre dividendos en ET artículo 240.",
                      providers: [],
                      snippets: [
                        {
                          doc_id: "interp_dividendos",
                          authority: "DIAN",
                          title: "Concepto dividendos",
                          snippet: "Lectura técnica sobre dividendos y tarifa aplicable.",
                          card_summary: "Interpretación sobre dividendos en ET artículo 240.",
                          position_signal: "condiciona",
                          relevance_score: 0.9,
                          trust_tier: "high",
                          provider_links: [],
                          providers: [],
                        },
                      ],
                    },
                  ],
                  ungrouped: [],
                },
              },
            }),
            buildQuestionEntry({
              questionId: "trace_session_2",
              questionText: "¿Puedo deducir ICA?",
              userTranscriptIndex: 2,
              assistantTranscriptIndex: 3,
              traceId: "trace_session_2",
              normativeSupport: {
                citationRequestContext: {
                  trace_id: "trace_session_2",
                  message: "¿Puedo deducir ICA?",
                  assistant_answer: "Sí, pero revisa soporte y causalidad.",
                  topic: "declaracion_renta",
                  pais: "colombia",
                  primary_scope_mode: "global_overlay",
                },
                fallbackCitations: [
                  {
                    doc_id: "doc_et_107",
                    source_label: "ET art. 107",
                    legal_reference: "ET art. 107",
                    source_provider: "SUIN",
                    authority: "SUIN",
                    source_tier: "Fuente Normativa",
                    knowledge_class: "normative_base",
                    source_type: "official_primary",
                  },
                ],
                mentionCitations: [],
                cachedCitations: [
                  {
                    doc_id: "doc_et_107",
                    source_label: "ET art. 107",
                    legal_reference: "ET art. 107",
                    source_provider: "SUIN",
                    authority: "SUIN",
                    source_tier: "Fuente Normativa",
                    knowledge_class: "normative_base",
                    source_type: "official_primary",
                  },
                ],
                statusText: "Mostrando 1 referencias normativas detectadas en este turno.",
                placeholderText: "",
              },
              expertPanelState: {
                status: "populated",
                loadOptions: {
                  traceId: "trace_session_2",
                  message: "¿Puedo deducir ICA?",
                  assistantAnswer: "Sí, pero revisa soporte y causalidad.",
                  normativeArticleRefs: ["art_107"],
                  topic: "declaracion_renta",
                  pais: "colombia",
                },
                response: {
                  ok: true,
                  trace_id: "trace_session_2",
                  groups: [
                    {
                      article_ref: "et_art_107",
                      classification: "concordancia",
                      summary_signal: "Interpretación sobre causalidad del ICA en ET artículo 107.",
                      providers: [],
                      snippets: [
                        {
                          doc_id: "interp_ica",
                          authority: "DIAN",
                          title: "Concepto ICA",
                          snippet: "Lectura técnica sobre causalidad y soporte del ICA.",
                          card_summary: "Interpretación sobre causalidad del ICA en ET artículo 107.",
                          position_signal: "permite",
                          relevance_score: 0.88,
                          trust_tier: "high",
                          provider_links: [],
                          providers: [],
                        },
                      ],
                    },
                  ],
                  ungrouped: [],
                },
              },
            }),
          ],
          activeQuestionId: "trace_session_2",
          normativeSupport: {
            citationRequestContext: {
              trace_id: "trace_session_2",
              message: "¿Puedo deducir ICA?",
              assistant_answer: "Sí, pero revisa soporte y causalidad.",
              topic: "declaracion_renta",
              pais: "colombia",
              primary_scope_mode: "global_overlay",
            },
            fallbackCitations: [
              {
                doc_id: "doc_et_107",
                source_label: "ET art. 107",
                legal_reference: "ET art. 107",
                source_provider: "SUIN",
                authority: "SUIN",
                source_tier: "Fuente Normativa",
                knowledge_class: "normative_base",
                source_type: "official_primary",
              },
            ],
            mentionCitations: [],
            cachedCitations: [
              {
                doc_id: "doc_et_107",
                source_label: "ET art. 107",
                legal_reference: "ET art. 107",
                source_provider: "SUIN",
                authority: "SUIN",
                source_tier: "Fuente Normativa",
                knowledge_class: "normative_base",
                source_type: "official_primary",
              },
            ],
            statusText: "Mostrando 1 referencias normativas detectadas en este turno.",
            placeholderText: "",
          },
          conversationTokenTotals: { input_tokens: 20, output_tokens: 40, total_tokens: 60 },
        },
      ],
    });
    document.body.innerHTML = renderFullShell(i18n);

    mountChatApp(document.body, { i18n });
    await flushUi();
    await flushUi();

    expect(document.body.textContent).toContain("Sí, pero revisa soporte y causalidad.");
    expect(document.querySelector("#runtime-conversation-tokens")?.textContent).toBe("in=20 | out=40 | total=60");

    // Single session → drawer hidden (no per-question chips in multi-thread design)
    const drawer = document.querySelector<HTMLElement>("#chat-session-drawer");
    expect(drawer?.hidden).toBe(true);
    expect(document.querySelectorAll(".chat-session-chip")).toHaveLength(0);

    // Citations show only the active question's data (no "Chat N" dividers)
    const citationsText = document.querySelector("#citations")?.textContent || "";
    expect(citationsText).not.toContain("Chat 1");
    expect(citationsText).not.toContain("Chat 2");
  });

  it("does not persist the transient empty normativa state while a turn is still in flight", async () => {
    const storageWrites: Array<{ key: string; value: string }> = [];
    const storage = createRecordingStorageMock(storageWrites);
    const sessionStorageMock = createStorageMock();
    vi.stubGlobal("localStorage", storage);
    vi.stubGlobal("sessionStorage", sessionStorageMock);
    Object.defineProperty(window, "localStorage", {
      configurable: true,
      value: storage,
    });
    Object.defineProperty(window, "sessionStorage", {
      configurable: true,
      value: sessionStorageMock,
    });

    const i18n = createI18n("es-CO");
    const chatPayload = makeChatSuccessPayload({
      traceId: "trace_normativa_persist",
      sessionId: "chat_normativa_persist",
      answerMarkdown: "Sí. Revisa el ET art. 147 y el ET art. 189 para delimitar la compensación.",
      followupQueries: [],
    });
    chatPayload.support_citations = [
      {
        doc_id: "doc_et_147",
        logical_doc_id: "doc_et",
        source_label: "ET art. 147",
        legal_reference: "ET art. 147",
        source_provider: "DIAN",
        authority: "DIAN",
        source_tier: "Fuente Normativa",
        knowledge_class: "normative_base",
        source_type: "official_primary",
        reference_key: "et",
        reference_type: "et",
        locator_text: "Artículos 147",
        locator_kind: "articles",
        locator_start: "147",
      },
    ];

    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/llm/status") {
        return Promise.resolve(
          mockJsonResponse({
            llm_runtime: {
              model: "gemini-2.5-flash",
              selected_type: "gemini",
              selected_provider: "gemini_primary",
            },
          })
        );
      }
      if (url === "/api/build-info") {
        return Promise.resolve(mockJsonResponse({ build_info: {} }));
      }
      if (url === "/api/chat/stream") {
        return Promise.resolve(mockChatStreamResponse(chatPayload));
      }
      if (url === "/api/chat") {
        return Promise.resolve(mockJsonResponse(chatPayload));
      }
      if (url.startsWith("/api/feedback")) {
        return Promise.resolve(mockJsonResponse({ feedback: null }));
      }
      return Promise.resolve(mockJsonResponse({}));
    });
    vi.stubGlobal("fetch", fetchMock);

    document.body.innerHTML = renderFullShell(i18n);
    mountChatApp(document.body, { i18n });
    await flushUi();

    const messageInput = document.querySelector<HTMLTextAreaElement>("#message");
    const form = document.querySelector<HTMLFormElement>("#chat-form");
    if (!messageInput || !form) {
      throw new Error("Missing chat composer.");
    }

    messageInput.value = "¿Puedo compensar pérdidas fiscales?";
    messageInput.dispatchEvent(new Event("input", { bubbles: true }));
    form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    await flushUi();
    await flushUi();

    const stateWrites = storageWrites
      .filter(({ key }) => key === `${CHAT_SESSION_STATE_KEY_PREFIX}chat_normativa_persist`)
      .map(({ value }) => JSON.parse(value));

    expect(stateWrites.length).toBeGreaterThan(0);
    expect(
      stateWrites.some((snapshot) => {
        const normativeSupport = snapshot?.normativeSupport;
        return (
          normativeSupport &&
          String(normativeSupport.statusText || "").includes("esperando respuesta del turno") &&
          Array.isArray(normativeSupport.cachedCitations) &&
          normativeSupport.cachedCitations.length === 0
        );
      })
    ).toBe(false);
    expect(document.querySelector("#citations")?.textContent).toContain("Estatuto Tributario, Artículo 147");
  });

  it("prefers the browser tab session and restores it again on focus", async () => {
    const i18n = createI18n("es-CO");
    seedStoredChatSessions({
      activeSessionId: "chat_session_2",
      sessions: [
        {
          sessionId: "chat_session_2",
          transcriptEntries: [
            { role: "user", text: "¿Puedo deducir ICA?" },
            {
              role: "assistant",
              text: "Sí, pero revisa soporte y causalidad.",
              meta: { session_id: "chat_session_2", trace_id: "trace_session_2" },
            },
          ],
          normativeSupport: {
            citationRequestContext: {
              trace_id: "trace_session_2",
              message: "¿Puedo deducir ICA?",
              assistant_answer: "Sí, pero revisa soporte y causalidad.",
              topic: "declaracion_renta",
              pais: "colombia",
              primary_scope_mode: "global_overlay",
            },
            fallbackCitations: [
              {
                doc_id: "doc_et_107",
                source_label: "ET art. 107",
                legal_reference: "ET art. 107",
                source_provider: "SUIN",
                authority: "SUIN",
                source_tier: "Fuente Normativa",
                knowledge_class: "normative_base",
                source_type: "official_primary",
              },
            ],
            mentionCitations: [],
            cachedCitations: [
              {
                doc_id: "doc_et_107",
                source_label: "ET art. 107",
                legal_reference: "ET art. 107",
                source_provider: "SUIN",
                authority: "SUIN",
                source_tier: "Fuente Normativa",
                knowledge_class: "normative_base",
                source_type: "official_primary",
              },
            ],
            statusText: "Mostrando 1 referencias normativas detectadas en este turno.",
            placeholderText: "",
          },
          conversationTokenTotals: { input_tokens: 20, output_tokens: 40, total_tokens: 60 },
        },
        {
          sessionId: "chat_session_1",
          transcriptEntries: [
            { role: "user", text: "¿Qué pasa con dividendos?" },
            {
              role: "assistant",
              text: "Depende de la tarifa del artículo aplicable.",
              meta: { session_id: "chat_session_1", trace_id: "trace_session_1" },
            },
          ],
          normativeSupport: {
            citationRequestContext: {
              trace_id: "trace_session_1",
              message: "¿Qué pasa con dividendos?",
              assistant_answer: "Depende de la tarifa del artículo aplicable.",
              topic: "declaracion_renta",
              pais: "colombia",
              primary_scope_mode: "global_overlay",
            },
            fallbackCitations: [
              {
                doc_id: "doc_et_240",
                source_label: "ET art. 240",
                legal_reference: "ET art. 240",
                source_provider: "DIAN",
                authority: "DIAN",
                source_tier: "Fuente Normativa",
                knowledge_class: "normative_base",
                source_type: "official_primary",
              },
            ],
            mentionCitations: [],
            cachedCitations: [
              {
                doc_id: "doc_et_240",
                source_label: "ET art. 240",
                legal_reference: "ET art. 240",
                source_provider: "DIAN",
                authority: "DIAN",
                source_tier: "Fuente Normativa",
                knowledge_class: "normative_base",
                source_type: "official_primary",
              },
            ],
            statusText: "Mostrando 1 referencias normativas detectadas en este turno.",
            placeholderText: "",
          },
          conversationTokenTotals: { input_tokens: 7, output_tokens: 9, total_tokens: 16 },
        },
      ],
    });
    sessionStorage.setItem(WINDOW_CHAT_SESSION_KEY, "chat_session_1");
    document.body.innerHTML = renderFullShell(i18n);

    mountChatApp(document.body, { i18n });
    await flushUi();
    await flushUi();

    expect(document.body.textContent).toContain("Depende de la tarifa del artículo aplicable.");
    expect(document.querySelector("#citations")?.textContent).toContain("Estatuto Tributario, Artículo 240");

    sessionStorage.setItem(WINDOW_CHAT_SESSION_KEY, "chat_session_2");
    window.dispatchEvent(new Event("focus"));
    await flushUi();
    await flushUi();

    expect(document.body.textContent).toContain("Sí, pero revisa soporte y causalidad.");
    expect(document.body.textContent).not.toContain("Depende de la tarifa del artículo aplicable.");
    expect(document.querySelector("#citations")?.textContent).toContain("Estatuto Tributario, Artículo 107");
    expect(document.querySelector("#runtime-conversation-tokens")?.textContent).toBe("in=20 | out=40 | total=60");
  });

  it("clears saved conversations only after explicit toast confirmation", async () => {
    const i18n = createI18n("es-CO");
    seedStoredChatSessions({
      activeSessionId: "chat_saved_a",
      sessions: [
        {
          sessionId: "chat_saved_a",
          transcriptEntries: [
            { role: "user", text: "Consulta A" },
            { role: "assistant", text: "Respuesta A", meta: { session_id: "chat_saved_a" } },
          ],
          conversationTokenTotals: { input_tokens: 1, output_tokens: 2, total_tokens: 3 },
        },
        {
          sessionId: "chat_saved_b",
          transcriptEntries: [
            { role: "user", text: "Consulta B" },
            { role: "assistant", text: "Respuesta B", meta: { session_id: "chat_saved_b" } },
          ],
          conversationTokenTotals: { input_tokens: 4, output_tokens: 5, total_tokens: 9 },
        },
      ],
    });
    document.body.innerHTML = renderFullShell(i18n);

    mountChatApp(document.body, { i18n });
    await flushUi();
    await flushUi();

    expect(document.body.textContent).toContain("Respuesta A");
    document.querySelector<HTMLButtonElement>("#reset-conversation-btn")?.dispatchEvent(
      new MouseEvent("click", { bubbles: true })
    );
    await flushUi();
    await flushUi();

    expect(document.body.textContent).toContain(
      "Esto borrará todas las conversaciones guardadas. ¿Estás seguro?"
    );
    expect(document.body.textContent).toContain("Respuesta A");

    document.querySelector<HTMLButtonElement>(".lia-toast-action-primary")?.dispatchEvent(
      new MouseEvent("click", { bubbles: true })
    );
    await flushUi();
    await flushUi();

    expect(document.body.textContent).not.toContain("Respuesta A");
    expect(document.querySelectorAll(".chat-session-chip")).toHaveLength(0);
    expect(localStorage.getItem(CHAT_SESSION_INDEX_KEY)).toBeNull();
    expect(localStorage.getItem(`${CHAT_SESSION_STATE_KEY_PREFIX}chat_saved_a`)).toBeNull();
    expect(localStorage.getItem(`${CHAT_SESSION_STATE_KEY_PREFIX}chat_saved_b`)).toBeNull();
  });

  it("migrates recoverable legacy chat caches into session snapshots", async () => {
    const i18n = createI18n("es-CO");
    localStorage.setItem(
      LEGACY_TRANSCRIPT_CACHE_KEY,
      JSON.stringify([
        { role: "user", text: "¿Cómo cierro renta?" },
        {
          role: "assistant",
          text: "Revisa el ET art. 107 antes del cierre.",
          meta: { session_id: "chat_legacy_1", trace_id: "trace_legacy_1" },
        },
      ])
    );
    localStorage.setItem(
      LEGACY_NORMATIVE_SUPPORT_CACHE_KEY,
      JSON.stringify({
        citationRequestContext: {
          trace_id: "trace_legacy_1",
          message: "¿Cómo cierro renta?",
          assistant_answer: "Revisa el ET art. 107 antes del cierre.",
          topic: "declaracion_renta",
          pais: "colombia",
          primary_scope_mode: "global_overlay",
        },
        fallbackCitations: [
          {
            doc_id: "doc_et_107",
            source_label: "ET art. 107",
            legal_reference: "ET art. 107",
            source_provider: "SUIN",
            authority: "SUIN",
            source_tier: "Fuente Normativa",
            knowledge_class: "normative_base",
            source_type: "official_primary",
          },
        ],
        mentionCitations: [],
        cachedCitations: [
          {
            doc_id: "doc_et_107",
            source_label: "ET art. 107",
            legal_reference: "ET art. 107",
            source_provider: "SUIN",
            authority: "SUIN",
            source_tier: "Fuente Normativa",
            knowledge_class: "normative_base",
            source_type: "official_primary",
          },
        ],
        statusText: "Mostrando 1 referencias normativas detectadas en este turno.",
      })
    );
    document.body.innerHTML = renderFullShell(i18n);

    mountChatApp(document.body, { i18n });
    await flushUi();
    await flushUi();

    expect(localStorage.getItem(LEGACY_TRANSCRIPT_CACHE_KEY)).toBeNull();
    expect(localStorage.getItem(LEGACY_NORMATIVE_SUPPORT_CACHE_KEY)).toBeNull();
    expect(document.body.textContent).toContain("Revisa el ET art. 107 antes del cierre.");
    expect(document.querySelector("#citations")?.textContent).toContain("Estatuto Tributario, Artículo 107");
    // Single session → drawer hidden (thread count ≤1)
    expect(document.querySelectorAll(".chat-session-chip")).toHaveLength(0);
  });

  it("hides per-question drawer for a single session with multiple questions", async () => {
    const i18n = createI18n("es-CO");
    seedStoredChatSessions({
      activeSessionId: "chat_session_3",
      sessions: [
        {
          sessionId: "chat_session_3",
          transcriptEntries: [
            { role: "user", text: "¿Cómo reporto ingresos por servicios prestados desde el exterior en la declaración de renta?" },
            { role: "assistant", text: "Respuesta 3", meta: { session_id: "chat_session_3", trace_id: "trace_q3" } },
            { role: "user", text: "¿Puedo deducir ICA cuando el gasto está asociado a operaciones gravadas y soportadas?" },
            { role: "assistant", text: "Respuesta 2", meta: { session_id: "chat_session_3", trace_id: "trace_q2" } },
            { role: "user", text: "¿Qué tratamiento tienen las pérdidas fiscales acumuladas de años anteriores?" },
            { role: "assistant", text: "Respuesta 1", meta: { session_id: "chat_session_3", trace_id: "trace_q1" } },
          ],
          activeQuestionId: "trace_q1",
          conversationTokenTotals: { input_tokens: 1, output_tokens: 2, total_tokens: 3 },
        },
      ],
    });
    document.body.innerHTML = renderFullShell(i18n);

    mountChatApp(document.body, { i18n });
    await flushUi();
    await flushUi();

    // Single session → drawer hidden; per-question chips no longer rendered
    const drawer = document.querySelector<HTMLElement>("#chat-session-drawer");
    expect(drawer?.hidden).toBe(true);
    expect(document.querySelectorAll(".chat-session-chip")).toHaveLength(0);
  });

  it("drops corrupt stored sessions without breaking the valid one", async () => {
    const i18n = createI18n("es-CO");
    localStorage.setItem(
      CHAT_SESSION_INDEX_KEY,
      JSON.stringify({
        version: 1,
        activeSessionId: "chat_valid_1",
        sessions: [
          {
            sessionId: "chat_valid_1",
            firstQuestion: "Consulta válida",
            updatedAt: "2026-03-12T01:00:00.000Z",
          },
          {
            sessionId: "chat_corrupt_1",
            firstQuestion: "Consulta dañada",
            updatedAt: "2026-03-12T00:00:00.000Z",
          },
        ],
      })
    );
    localStorage.setItem(
      `${CHAT_SESSION_STATE_KEY_PREFIX}chat_valid_1`,
      JSON.stringify({
        version: 1,
        sessionId: "chat_valid_1",
        firstQuestion: "Consulta válida",
        updatedAt: "2026-03-12T01:00:00.000Z",
        transcriptEntries: [
          { role: "user", text: "Consulta válida" },
          { role: "assistant", text: "Respuesta válida", meta: { session_id: "chat_valid_1" } },
        ],
        normativeSupport: null,
        conversationTokenTotals: { input_tokens: 1, output_tokens: 1, total_tokens: 2 },
        lastUserMessage: "Consulta válida",
        lastSubmittedUserMessage: "Consulta válida",
        lastAssistantAnswerMarkdown: "Respuesta válida",
      })
    );
    localStorage.setItem(`${CHAT_SESSION_STATE_KEY_PREFIX}chat_corrupt_1`, "{not-json");
    document.body.innerHTML = renderFullShell(i18n);

    mountChatApp(document.body, { i18n });
    await flushUi();
    await flushUi();

    expect(document.body.textContent).toContain("Respuesta válida");
    // After dropping corrupt session, only 1 valid session remains → drawer hidden (thread count ≤1)
    expect(document.querySelectorAll(".chat-session-chip")).toHaveLength(0);
  });

  it("fetches and renders the curated normative profile modal with a single top CTA", async () => {
    const i18n = createI18n("es-CO");
    const chatPayload = makeChatSuccessPayload({
      traceId: "trace_norma_modal_1",
      sessionId: "chat_norma_modal_1",
      answerMarkdown: "Revisa el Formulario 110 para preparar la declaración.",
      followupQueries: [],
    });
    chatPayload.citations = [
      {
        doc_id: "doc_form_110",
        source_label: "Formulario 110",
        legal_reference: "Formulario 110",
        source_provider: "DIAN",
        authority: "DIAN",
        source_tier: "Fuente Normativa",
        knowledge_class: "normative_base",
        source_type: "official_primary",
        source_view_url: "/source-view?doc_id=doc_form_110",
        open_url: "/source-view?doc_id=doc_form_110",
        download_url: "/source-download?doc_id=doc_form_110&view=normalized&format=pdf",
        reference_key: "formulario:110",
        reference_type: "formulario",
        usage_context: "Referencia al Formulario 110 de declaración de renta.",
      },
    ];

    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/llm/status") {
        return Promise.resolve(
          mockJsonResponse({
            llm_runtime: {
              model: "gemini-2.5-flash",
              selected_type: "gemini",
              selected_provider: "gemini_primary",
            },
          })
        );
      }
      if (url === "/api/build-info") {
        return Promise.resolve(mockJsonResponse({ build_info: {} }));
      }
      if (url === "/api/chat/stream") {
        expect(init?.method).toBe("POST");
        return Promise.resolve(mockChatStreamResponse(chatPayload));
      }
      if (url === "/api/chat") {
        expect(init?.method).toBe("POST");
        return Promise.resolve(mockJsonResponse(chatPayload));
      }
      if (url.startsWith("/api/citation-profile?doc_id=doc_form_110")) {
        return Promise.resolve(
          mockJsonResponse({
            ok: true,
            title: "Formulario 110",
            document_family: "formulario",
            lead: "Formulario 110 es el instrumento prescrito por la DIAN para presentar la declaración de renta y complementario de personas jurídicas y demás obligados que declaran en este formato.",
            facts: [
              {
                label: "Para qué sirve",
                value: "Sirve para liquidar y presentar la declaración de renta y complementario de personas jurídicas, asimiladas y otros obligados definidos por el art. 591 ET.",
              },
              {
                label: "Desde cuándo es obligatorio",
                value: "Para el año gravable 2025 presentado en 2026, el Formulario 110 sigue siendo el formulario prescrito por la Resolución DIAN 000188 de 2024 para los obligados del art. 591 ET.",
              },
              {
                label: "Última actualización identificada",
                value: "Resolución DIAN 000188 de 2024, vigente para el AG 2025 presentado en 2026.",
              },
            ],
            sections: [
              {
                id: "impacto_profesional",
                title: "Cómo impacta la labor contable",
                body: "Obliga al contador a validar cifras, soportes, conciliación fiscal, RUT y firmas del representante legal, contador o revisor fiscal antes de presentar la declaración.",
              },
            ],
            companion_action: {
              label: "¿Quieres una guía sobre cómo llenarlo?",
              state: "available",
              url: "/form-guide?reference_key=formulario%3A110",
              helper_text: null,
            },
            source_action: {
              label: "Ir a documento original",
              url: "/source-download?doc_id=doc_form_110&view=normalized&format=pdf",
              mode: "normalized_pdf_fallback",
              helper_text: "No se encontró el original; se abrirá el PDF normalizado disponible en LIA.",
            },
          })
        );
      }
      if (url.startsWith("/api/feedback")) {
        return Promise.resolve(mockJsonResponse({ feedback: null }));
      }
      return Promise.resolve(mockJsonResponse({}));
    });
    vi.stubGlobal("fetch", fetchMock);

    document.body.innerHTML = renderFullShell(i18n);
    mountChatApp(document.body, { i18n });
    await flushUi();

    const messageInput = document.querySelector<HTMLTextAreaElement>("#message");
    const form = document.querySelector<HTMLFormElement>("#chat-form");
    expect(messageInput).not.toBeNull();
    expect(form).not.toBeNull();

    messageInput!.value = "¿Cómo debo diligenciar el formulario 110?";
    messageInput!.dispatchEvent(new Event("input", { bubbles: true }));
    form!.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    await flushUi();
    await flushUi();

    const citationTrigger = document.querySelector<HTMLButtonElement>(".citation-trigger");
    expect(citationTrigger?.textContent).toContain("Formulario 110");
    citationTrigger?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await flushUi();
    await flushUi();

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/citation-profile?doc_id=doc_form_110"),
      expect.any(Object)
    );
    expect(document.querySelector("#modal-norma")?.classList.contains("is-open")).toBe(true);
    expect(document.querySelector("#norma-open-doc-btn")).toBeNull();
    expect(document.querySelector("#norma-download-doc-btn")).toBeNull();
    expect(document.querySelector("#norma-loading .modal-inline-googly")).not.toBeNull();
    // Formulario profiles hide the topbar and show footer actions instead
    expect(document.querySelector("#norma-topbar")?.hasAttribute("hidden")).toBe(true);
    // Lead line is now unconditionally hidden (commit 6cfdee0e)
    expect(document.querySelector("#norma-lead")?.hidden).toBe(true);
    expect(document.querySelector("#norma-facts")?.textContent).toContain("Para qué sirve");
    expect(document.querySelector("#norma-facts")?.textContent).toContain("Desde cuándo es obligatorio");
    expect(document.querySelector("#norma-facts")?.textContent).toContain("Última actualización identificada");
    expect(document.querySelector("#norma-facts")?.textContent).toContain("Resolución DIAN 000188 de 2024");
    expect(document.querySelector("#norma-facts .norma-bullet-list li")?.textContent).toMatch(/\.$/);
    expect(document.querySelector("#norma-sections")?.textContent).toContain("Cómo impacta la labor contable");
    expect(document.querySelector("#norma-sections .norma-bullet-list li")?.textContent).toMatch(/\.$/);
    // Footer actions: secondary original button + primary guide button
    const footerActions = document.querySelector(".norma-footer-actions");
    expect(footerActions).not.toBeNull();
    expect(footerActions?.querySelector(".secondary-btn")?.textContent).toBe("Ir a formulario original");
    expect(footerActions?.querySelector(".norma-footer-guide-btn")?.textContent).toBe("Guía gráfica sobre cómo llenarlo");
    expect(document.querySelector("#norma-analysis-btn")?.hasAttribute("hidden")).toBe(true);
    // Lead line is hidden; "Formulario 110" appears in the modal title instead
    expect(document.querySelector("#modal-norma")?.textContent).toContain("Formulario 110");
    const modalText = document.querySelector("#modal-norma")?.textContent?.toLowerCase() ?? "";
  expect(modalText).not.toContain("beneficio de auditoria");
  expect(modalText).not.toContain("corpus critico p0");
  expect(modalText).not.toContain("marzo 3, 2026");
});

it("keeps the original document action hidden while the normative profile is still loading", async () => {
  const i18n = createI18n("es-CO");
  const chatPayload = makeChatSuccessPayload({
    traceId: "trace_norma_modal_loading",
    sessionId: "chat_norma_modal_loading",
    answerMarkdown: "Revisa el Formulario 110 para preparar la declaración.",
    followupQueries: [],
  });
  chatPayload.citations = [
    {
      doc_id: "doc_form_110",
      source_label: "Formulario 110",
      legal_reference: "Formulario 110",
      source_provider: "DIAN",
      authority: "DIAN",
      source_tier: "Fuente Normativa",
      knowledge_class: "normative_base",
      source_type: "official_primary",
      source_view_url: "/source-view?doc_id=doc_form_110",
      open_url: "/source-view?doc_id=doc_form_110",
      download_url: "/source-download?doc_id=doc_form_110&view=normalized&format=pdf",
      reference_key: "formulario:110",
      reference_type: "formulario",
      usage_context: "Referencia al Formulario 110 de declaración de renta.",
    },
  ];

  let resolveCitationProfile: ((value: Response) => void) | null = null;
  const citationProfilePromise = new Promise<Response>((resolve) => {
    resolveCitationProfile = resolve;
  });

  const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url === "/api/llm/status") {
      return Promise.resolve(
        mockJsonResponse({
          llm_runtime: {
            model: "gemini-2.5-flash",
            selected_type: "gemini",
            selected_provider: "gemini_primary",
          },
        })
      );
    }
    if (url === "/api/build-info") {
      return Promise.resolve(mockJsonResponse({ build_info: {} }));
    }
    if (url === "/api/chat/stream") {
      expect(init?.method).toBe("POST");
      return Promise.resolve(mockChatStreamResponse(chatPayload));
    }
    if (url === "/api/chat") {
      expect(init?.method).toBe("POST");
      return Promise.resolve(mockJsonResponse(chatPayload));
    }
    if (url.startsWith("/api/citation-profile?doc_id=doc_form_110")) {
      return citationProfilePromise;
    }
    if (url.startsWith("/api/feedback")) {
      return Promise.resolve(mockJsonResponse({ feedback: null }));
    }
    return Promise.resolve(mockJsonResponse({}));
  });
  vi.stubGlobal("fetch", fetchMock);

  document.body.innerHTML = renderFullShell(i18n);
  mountChatApp(document.body, { i18n });
  await flushUi();

  const messageInput = document.querySelector<HTMLTextAreaElement>("#message");
  const form = document.querySelector<HTMLFormElement>("#chat-form");
  if (!messageInput || !form) {
    throw new Error("Missing chat composer.");
  }

  messageInput.value = "¿Cómo debo diligenciar el formulario 110?";
  messageInput.dispatchEvent(new Event("input", { bubbles: true }));
  form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
  await flushUi();
  await flushUi();

  const citationTrigger = document.querySelector<HTMLButtonElement>(".citation-trigger");
  expect(citationTrigger).not.toBeNull();
  expect(citationTrigger?.textContent).toContain("Formulario 110");
  citationTrigger?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  await flushUi();

  expect(document.querySelector("#modal-norma")?.classList.contains("is-open")).toBe(true);
  expect(document.querySelector("#norma-loading")?.hasAttribute("hidden")).toBe(false);
  expect(document.querySelector("#norma-original-btn")?.hasAttribute("hidden")).toBe(true);

  resolveCitationProfile?.(
      mockJsonResponse({
        ok: true,
        title: "Formulario 110",
        document_family: "formulario",
        lead: "Formulario 110 es el instrumento prescrito por la DIAN para presentar la declaración de renta.",
        facts: [{ label: "Qué regula", value: "Sirve para liquidar y presentar la declaración." }],
        sections: [],
        source_action: {
          label: "Ir a documento original",
          url: "/source-view?doc_id=doc_form_110",
          helper_text: "Abre la fuente primaria.",
        },
      })
  );
  await flushUi();
  await flushUi();

  expect(document.querySelector("#norma-loading")?.textContent?.trim()).toBe("");
  expect(document.querySelector("#norma-loading")?.hasAttribute("hidden")).toBe(true);
  // Formulario profiles hide topbar and show footer actions
  expect(document.querySelector("#norma-topbar")?.hasAttribute("hidden")).toBe(true);
  const footerActions = document.querySelector(".norma-footer-actions");
  expect(footerActions).not.toBeNull();
  expect(footerActions?.querySelector(".secondary-btn")?.textContent).toBe("Ir a formulario original");
});

it("opens a supported formulario mention by reference_key when the citation has no doc_id", async () => {
    const i18n = createI18n("es-CO");
    const chatPayload = makeChatSuccessPayload({
      traceId: "trace_norma_modal_refkey",
      sessionId: "chat_norma_modal_refkey",
      answerMarkdown: "Revisa el Formulario 110 para preparar la declaracion.",
      followupQueries: [],
    });
    chatPayload.citations = [];

    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/llm/status") {
        return Promise.resolve(
          mockJsonResponse({
            llm_runtime: {
              model: "gemini-2.5-flash",
              selected_type: "gemini",
              selected_provider: "gemini_primary",
            },
          })
        );
      }
      if (url === "/api/build-info") {
        return Promise.resolve(mockJsonResponse({ build_info: {} }));
      }
      if (url === "/api/chat/stream") {
        expect(init?.method).toBe("POST");
        return Promise.resolve(mockChatStreamResponse(chatPayload));
      }
      if (url === "/api/chat") {
        expect(init?.method).toBe("POST");
        return Promise.resolve(mockJsonResponse(chatPayload));
      }
      if (url.startsWith("/api/citation-profile?reference_key=formulario%3A110")) {
        return Promise.resolve(
          mockJsonResponse({
            ok: true,
            title: "Formulario 110",
            document_family: "formulario",
            lead: "Formulario 110 es el instrumento prescrito por la DIAN para presentar la declaracion de renta y complementario de personas juridicas.",
            facts: [
              {
                label: "Para que sirve",
                value: "Sirve para liquidar y presentar la declaracion de renta de personas juridicas.",
              },
            ],
            sections: [],
            companion_action: {
              label: "¿Quieres una guia sobre como llenarlo?",
              state: "available",
              url: "/form-guide?reference_key=formulario%3A110",
              helper_text: null,
            },
            source_action: {
              label: "Ir a documento original",
              url: "https://www.dian.gov.co/atencionciudadano/formulariosinstructivos/Formularios/2025/Formulario_110_2025.pdf",
              mode: "official_link",
              helper_text: "Abre la fuente oficial primaria.",
            },
          })
        );
      }
      if (url.startsWith("/api/feedback")) {
        return Promise.resolve(mockJsonResponse({ feedback: null }));
      }
      return Promise.resolve(mockJsonResponse({}));
    });
    vi.stubGlobal("fetch", fetchMock);

    document.body.innerHTML = renderFullShell(i18n);
    mountChatApp(document.body, { i18n });
    await flushUi();

    const messageInput = document.querySelector<HTMLTextAreaElement>("#message");
    const form = document.querySelector<HTMLFormElement>("#chat-form");
    if (!messageInput || !form) {
      throw new Error("Missing chat composer.");
    }

    messageInput.value = "¿Como debo diligenciar el formulario 110?";
    messageInput.dispatchEvent(new Event("input", { bubbles: true }));
    form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    await flushUi();
    await flushUi();
    await flushUi();

    const citationTrigger = document.querySelector<HTMLButtonElement>(".citation-trigger");
    expect(citationTrigger?.textContent).toContain("Formulario 110");
    // Formulario mentions no longer show a hint (card is itself a modal trigger)

    citationTrigger?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await flushUi();
    await flushUi();

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/citation-profile?reference_key=formulario%3A110"),
      expect.any(Object)
    );
    expect(document.querySelector("#modal-norma")?.classList.contains("is-open")).toBe(true);
    // Lead line is now unconditionally hidden; verify modal opens and facts render
    expect(document.querySelector("#norma-lead")?.hidden).toBe(true);
    expect(document.querySelector("#norma-facts")?.textContent).toContain("Para que sirve");
  });

  it("keeps formulario references from the user quote visible in normativa even when the assistant does not cite them", async () => {
    const i18n = createI18n("es-CO");
    const chatPayload = makeChatSuccessPayload({
      traceId: "trace_user_quote_form",
      sessionId: "chat_user_quote_form",
      answerMarkdown: "Voy a revisar el fragmento que compartiste y te respondo con el criterio aplicable.",
      followupQueries: [],
    });
    chatPayload.citations = [];

    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/llm/status") {
        return Promise.resolve(
          mockJsonResponse({
            llm_runtime: {
              model: "gemini-2.5-flash",
              selected_type: "gemini",
              selected_provider: "gemini_primary",
            },
          })
        );
      }
      if (url === "/api/build-info") {
        return Promise.resolve(mockJsonResponse({ build_info: {} }));
      }
      if (url === "/api/chat/stream") {
        expect(init?.method).toBe("POST");
        return Promise.resolve(mockChatStreamResponse(chatPayload));
      }
      if (url === "/api/chat") {
        expect(init?.method).toBe("POST");
        return Promise.resolve(mockJsonResponse(chatPayload));
      }
      if (url.startsWith("/api/citation-profile?reference_key=formulario%3A110")) {
        return Promise.resolve(
          mockJsonResponse({
            ok: true,
            title: "Formulario 110",
            document_family: "formulario",
            lead: "Formulario 110 es el instrumento prescrito por la DIAN para presentar la declaracion de renta y complementario de personas juridicas.",
            facts: [
              {
                label: "Para que sirve",
                value: "Sirve para liquidar y presentar la declaracion de renta y complementario.",
              },
            ],
            sections: [
              {
                id: "impacto_profesional",
                title: "Cómo impacta la labor contable",
                body: "Exige revisar soportes, conciliacion fiscal y firmas antes de presentar.",
              },
            ],
            companion_action: {
              label: "¿Quieres una guia sobre como llenarlo?",
              state: "available",
              url: "/form-guide?reference_key=formulario%3A110",
              helper_text: null,
            },
            source_action: {
              label: "Ir a documento original",
              url: "https://www.dian.gov.co/atencionciudadano/formulariosinstructivos/Formularios/2025/Formulario_110_2025.pdf",
              mode: "official_link",
              helper_text: null,
            },
          })
        );
      }
      if (url.startsWith("/api/feedback")) {
        return Promise.resolve(mockJsonResponse({ feedback: null }));
      }
      return Promise.resolve(mockJsonResponse({}));
    });
    vi.stubGlobal("fetch", fetchMock);

    document.body.innerHTML = renderFullShell(i18n);
    mountChatApp(document.body, { i18n });
    await flushUi();

    const messageInput = document.querySelector<HTMLTextAreaElement>("#message");
    const form = document.querySelector<HTMLFormElement>("#chat-form");
    if (!messageInput || !form) {
      throw new Error("Missing chat composer.");
    }

    messageInput.value = "> Extracto DIAN\n> Formulario 110\n\n¿Qué errores debo revisar aquí?";
    messageInput.dispatchEvent(new Event("input", { bubbles: true }));
    form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    await flushUi();
    await flushUi();
    await flushUi();

    const citationTrigger = document.querySelector<HTMLButtonElement>(".citation-trigger");
    expect(citationTrigger?.textContent).toContain("Formulario 110");
    // Formulario mentions no longer show a hint (card is itself a modal trigger)

    citationTrigger?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await flushUi();
    await flushUi();

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/citation-profile?reference_key=formulario%3A110"),
      expect.any(Object)
    );
    expect(document.querySelector("#modal-norma")?.classList.contains("is-open")).toBe(true);
    // Formulario profiles use footer actions instead of the companion link
    const guideBtn = document.querySelector<HTMLAnchorElement>(".norma-footer-guide-btn");
    expect(guideBtn?.getAttribute("href")).toBe(
      "/form-guide?reference_key=formulario%3A110"
    );
  });

  it("renders the helper with normativo rows and collapses duplicate mentions", async () => {
    const i18n = createI18n("es-CO");
    const chatPayload = makeChatSuccessPayload({
      traceId: "trace_primary_helper_only",
      sessionId: "chat_primary_helper_only",
      answerMarkdown: "Revisa el Formulario 110 y el DUR 1625 de 2016. El Formulario 110 debe validarse antes de presentar.",
      followupQueries: [],
    });
    chatPayload.citations = [
      {
        doc_id: "doc_form_110",
        logical_doc_id: "doc_form_110",
        source_label: "Formulario 110",
        legal_reference: "Formulario 110",
        source_provider: "DIAN",
        authority: "DIAN",
        source_tier: "Fuente Normativa",
        knowledge_class: "normative_base",
        source_type: "official_primary",
        source_view_url: "/source-view?doc_id=doc_form_110",
        open_url: "/source-view?doc_id=doc_form_110",
        download_url: "/source-download?doc_id=doc_form_110&view=normalized&format=pdf",
        download_md_url: "/source-download?doc_id=doc_form_110&view=normalized&format=md",
        reference_key: "formulario:110",
        reference_type: "formulario",
        usage_context: "Formulario 110 referenciado en respuesta.",
      },
      {
        doc_id: "doc_interp_form_110",
        logical_doc_id: "doc_interp_form_110",
        source_label: "Guia operativa Formulario 110",
        legal_reference: "Formulario 110",
        source_provider: "DIAN",
        authority: "DIAN",
        source_tier: "Fuente Expertos",
        knowledge_class: "interpretative_guidance",
        source_type: "official_secondary",
        reference_key: "formulario:110",
        reference_type: "formulario",
        usage_context: "Guía interpretativa del Formulario 110.",
      },
      {
        doc_id: "doc_dur_1625",
        logical_doc_id: "doc_dur_1625",
        source_label: "DUR 1625 de 2016",
        legal_reference: "DUR 1625 de 2016",
        source_provider: "DIAN",
        authority: "DIAN",
        source_tier: "Fuente Normativa",
        knowledge_class: "normative_base",
        source_type: "official_primary",
        source_view_url: "/source-view?doc_id=doc_dur_1625",
        open_url: "/source-view?doc_id=doc_dur_1625",
        download_url: "/source-download?doc_id=doc_dur_1625&view=normalized&format=pdf",
        download_md_url: "/source-download?doc_id=doc_dur_1625&view=normalized&format=md",
        reference_key: "dur:1625:2016",
        reference_type: "dur",
        usage_context: "DUR 1625 de 2016 referenciado en respuesta.",
      },
      {
        doc_id: "doc_interp_checklist",
        logical_doc_id: "doc_interp_checklist",
        source_label: "Checklist presentación renta",
        legal_reference: "Checklist presentación renta",
        source_provider: "DIAN",
        authority: "DIAN",
        source_tier: "Fuente Expertos",
        knowledge_class: "interpretative_guidance",
        source_type: "official_secondary",
        usage_context: "Checklist operativo de presentación.",
      },
    ];

    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/llm/status") {
        return Promise.resolve(
          mockJsonResponse({
            llm_runtime: {
              model: "gemini-2.5-flash",
              selected_type: "gemini",
              selected_provider: "gemini_primary",
            },
          })
        );
      }
      if (url === "/api/build-info") {
        return Promise.resolve(mockJsonResponse({ build_info: {} }));
      }
      if (url === "/api/chat/stream") {
        return Promise.resolve(mockChatStreamResponse(chatPayload));
      }
      if (url === "/api/chat") {
        return Promise.resolve(mockJsonResponse(chatPayload));
      }
      if (url.startsWith("/api/feedback")) {
        return Promise.resolve(mockJsonResponse({ feedback: null }));
      }
      return Promise.resolve(mockJsonResponse({}));
    });
    vi.stubGlobal("fetch", fetchMock);

    document.body.innerHTML = renderFullShell(i18n);
    mountChatApp(document.body, { i18n });
    await flushUi();

    const messageInput = document.querySelector<HTMLTextAreaElement>("#message");
    const form = document.querySelector<HTMLFormElement>("#chat-form");
    if (!messageInput || !form) {
      throw new Error("Missing chat composer.");
    }

    messageInput.value = "¿Qué debo revisar en el Formulario 110 según el DUR 1625 de 2016?";
    messageInput.dispatchEvent(new Event("input", { bubbles: true }));
    form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    await flushUi();
    await flushUi();

    const citationItems = Array.from(document.querySelectorAll("#citations li")).map((item) =>
      item.textContent?.replace(/\s+/g, " ").trim() || ""
    );

    expect(citationItems).toHaveLength(2);
    // W1 Phase 1 sort: DUR (family rank 3) before Formulario (rank 6)
    expect(citationItems[0]).toContain("DUR 1625 de 2016");
    expect(citationItems[1]).toContain("Formulario 110");
    expect(document.querySelector("#citations")?.textContent || "").not.toContain("Fuente Expertos");
    expect(document.querySelector("#citations")?.textContent || "").not.toContain("Checklist presentación renta");
    expect((document.querySelector("#citations")?.textContent || "").match(/Formulario 110/g)?.length ?? 0).toBe(1);
  });

  it("keeps multiple ET locator citations from the same document as separate helper rows", async () => {
    const i18n = createI18n("es-CO");
    const chatPayload = makeChatSuccessPayload({
      traceId: "trace_multi_et_helper",
      sessionId: "chat_multi_et_helper",
      answerMarkdown:
        "Revisa la procedencia de costos y deducciones conforme al ET art. 107 y aplica la tarifa general del ET art. 240.",
      followupQueries: [],
    });
    chatPayload.support_citations = [
      {
        doc_id: "doc_form_110",
        logical_doc_id: "doc_form_110",
        source_label: "Formulario 110",
        legal_reference: "Formulario 110",
        source_provider: "DIAN",
        authority: "DIAN",
        source_tier: "Fuente Normativa",
        knowledge_class: "normative_base",
        source_type: "official_primary",
        reference_key: "formulario:110",
        reference_type: "formulario",
        usage_context: "Formulario 110 citado en la respuesta.",
      },
      {
        doc_id: "doc_form_2516",
        logical_doc_id: "doc_form_2516",
        source_label: "Formato 2516",
        legal_reference: "Formato 2516",
        source_provider: "DIAN",
        authority: "DIAN",
        source_tier: "Fuente Normativa",
        knowledge_class: "normative_base",
        source_type: "official_primary",
        reference_key: "formulario:2516",
        reference_type: "formulario",
        usage_context: "Formato 2516 citado en la respuesta.",
      },
      {
        doc_id: "doc_et",
        logical_doc_id: "doc_et",
        source_label: "Estatuto Tributario, Artículos 107",
        legal_reference: "Estatuto Tributario, Artículos 107",
        source_provider: "DIAN",
        authority: "DIAN",
        source_tier: "Fuente Normativa",
        knowledge_class: "normative_base",
        source_type: "official_primary",
        reference_key: "et",
        reference_type: "et",
        locator_text: "Artículos 107",
        locator_kind: "articles",
        locator_start: "107",
        usage_context: "ET art. 107 citado en la respuesta.",
      },
      {
        doc_id: "doc_et",
        logical_doc_id: "doc_et",
        source_label: "Estatuto Tributario, Artículos 240",
        legal_reference: "Estatuto Tributario, Artículos 240",
        source_provider: "DIAN",
        authority: "DIAN",
        source_tier: "Fuente Normativa",
        knowledge_class: "normative_base",
        source_type: "official_primary",
        reference_key: "et",
        reference_type: "et",
        locator_text: "Artículos 240",
        locator_kind: "articles",
        locator_start: "240",
        usage_context: "ET art. 240 citado en la respuesta.",
      },
    ];

    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/llm/status") {
        return Promise.resolve(
          mockJsonResponse({
            llm_runtime: {
              model: "gemini-2.5-flash",
              selected_type: "gemini",
              selected_provider: "gemini_primary",
            },
          })
        );
      }
      if (url === "/api/build-info") {
        return Promise.resolve(mockJsonResponse({ build_info: {} }));
      }
      if (url === "/api/chat/stream") {
        return Promise.resolve(mockChatStreamResponse(chatPayload));
      }
      if (url === "/api/chat") {
        return Promise.resolve(mockJsonResponse(chatPayload));
      }
      if (url.startsWith("/api/feedback")) {
        return Promise.resolve(mockJsonResponse({ feedback: null }));
      }
      return Promise.resolve(mockJsonResponse({}));
    });
    vi.stubGlobal("fetch", fetchMock);

    document.body.innerHTML = renderFullShell(i18n);
    mountChatApp(document.body, { i18n });
    await flushUi();

    const messageInput = document.querySelector<HTMLTextAreaElement>("#message");
    const form = document.querySelector<HTMLFormElement>("#chat-form");
    if (!messageInput || !form) {
      throw new Error("Missing chat composer.");
    }

    messageInput.value = "¿Qué debo revisar para presentar la declaración de renta?";
    messageInput.dispatchEvent(new Event("input", { bubbles: true }));
    form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    await flushUi();
    await flushUi();

    const citationItems = Array.from(document.querySelectorAll("#citations li")).map((item) =>
      item.textContent?.replace(/\s+/g, " ").trim() || ""
    );

    expect(citationItems).toHaveLength(4);
    expect(citationItems.some((item) => item.includes("Formulario 110"))).toBe(true);
    expect(citationItems.some((item) => item.includes("Formato 2516"))).toBe(true);
    expect(citationItems.some((item) => item.includes("Artículo 107"))).toBe(true);
    expect(citationItems.some((item) => item.includes("Artículo 240"))).toBe(true);
  });

  it("drops unmatched fallback ET locators and backfills missing ET locator mentions from the answer", async () => {
    const i18n = createI18n("es-CO");
    const chatPayload = makeChatSuccessPayload({
      traceId: "trace_et_locator_backfill",
      sessionId: "chat_et_locator_backfill",
      answerMarkdown:
        "Elabora el Formato 2516 y revisa el Formulario 110. La procedencia de costos y deducciones depende del ET art. 107 y la tarifa general aplicable sigue el ET art. 240.",
      followupQueries: [],
    });
    chatPayload.support_citations = [
      {
        doc_id: "doc_form_110",
        logical_doc_id: "doc_form_110",
        source_label: "Formulario 110",
        legal_reference: "Formulario 110",
        source_provider: "DIAN",
        authority: "DIAN",
        source_tier: "Fuente Normativa",
        knowledge_class: "normative_base",
        source_type: "official_primary",
        reference_key: "formulario:110",
        reference_type: "formulario",
        usage_context: "Formulario 110 citado en la respuesta.",
      },
      {
        doc_id: "doc_form_2516",
        logical_doc_id: "doc_form_2516",
        source_label: "Formato 2516",
        legal_reference: "Formato 2516",
        source_provider: "DIAN",
        authority: "DIAN",
        source_tier: "Fuente Normativa",
        knowledge_class: "normative_base",
        source_type: "official_primary",
        reference_key: "formulario:2516",
        reference_type: "formulario",
        usage_context: "Formato 2516 citado en la respuesta.",
      },
      {
        doc_id: "doc_et_107",
        logical_doc_id: "doc_et",
        source_label: "ET art. 107",
        legal_reference: "ET art. 107",
        source_provider: "SUIN",
        authority: "SUIN",
        source_tier: "Fuente Normativa",
        knowledge_class: "normative_base",
        source_type: "official_primary",
        reference_key: "et",
        reference_type: "et",
        locator_text: "Artículos 107",
        locator_kind: "articles",
        locator_start: "107",
        usage_context: "ET art. 107 citado en la respuesta.",
      },
      {
        doc_id: "doc_et_114_1",
        logical_doc_id: "doc_et",
        source_label: "ET art. 114.1",
        legal_reference: "ET art. 114.1",
        source_provider: "DIAN",
        authority: "DIAN",
        source_tier: "Fuente Normativa",
        knowledge_class: "normative_base",
        source_type: "official_primary",
        reference_key: "et",
        reference_type: "et",
        locator_text: "Artículos 114.1",
        locator_kind: "articles",
        locator_start: "114.1",
        usage_context: "ET art. 114.1 arrastrado por retrieval.",
      },
    ];

    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/llm/status") {
        return Promise.resolve(
          mockJsonResponse({
            llm_runtime: {
              model: "gemini-2.5-flash",
              selected_type: "gemini",
              selected_provider: "gemini_primary",
            },
          })
        );
      }
      if (url === "/api/build-info") {
        return Promise.resolve(mockJsonResponse({ build_info: {} }));
      }
      if (url === "/api/chat") {
        return Promise.resolve(mockJsonResponse(chatPayload));
      }
      if (url.startsWith("/api/feedback")) {
        return Promise.resolve(mockJsonResponse({ feedback: null }));
      }
      return Promise.resolve(mockJsonResponse({}));
    });
    vi.stubGlobal("fetch", fetchMock);

    document.body.innerHTML = renderFullShell(i18n);
    mountChatApp(document.body, { i18n });
    await flushUi();

    const messageInput = document.querySelector<HTMLTextAreaElement>("#message");
    const form = document.querySelector<HTMLFormElement>("#chat-form");
    if (!messageInput || !form) {
      throw new Error("Missing chat composer.");
    }

    messageInput.value = "¿Qué debo revisar para presentar la declaración de renta?";
    messageInput.dispatchEvent(new Event("input", { bubbles: true }));
    form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    await flushUi();
    await flushUi();

    const citationItems = Array.from(document.querySelectorAll("#citations li")).map((item) =>
      item.textContent?.replace(/\s+/g, " ").trim() || ""
    );

    expect(citationItems).toHaveLength(4);
    expect(citationItems.some((item) => item.includes("Formulario 110"))).toBe(true);
    expect(citationItems.some((item) => item.includes("Formato 2516"))).toBe(true);
    expect(citationItems.some((item) => item.includes("Estatuto Tributario, Artículo 107"))).toBe(true);
    expect(citationItems.some((item) => item.includes("Estatuto Tributario, Artículo 240"))).toBe(true);
    expect(citationItems.some((item) => item.includes("Estatuto Tributario, Artículo 114-1"))).toBe(false);
  });

  it("shows corpus-backed citations before mention-only rows", async () => {
    const i18n = createI18n("es-CO");
    const chatPayload = makeChatSuccessPayload({
      traceId: "trace_corpus_first_order",
      sessionId: "chat_corpus_first_order",
      answerMarkdown:
        "Revisa la Ley 1607 de 2012, la Ley 1819 de 2016 y la Ley 2010 de 2019. Para este caso pesan el ET art. 147 y el ET art. 714.",
      followupQueries: [],
    });
    chatPayload.support_citations = [
      {
        doc_id: "doc_et_147",
        logical_doc_id: "doc_et",
        source_label: "ET art. 147",
        legal_reference: "ET art. 147",
        source_provider: "DIAN",
        authority: "DIAN",
        source_tier: "Fuente Normativa",
        knowledge_class: "normative_base",
        source_type: "official_primary",
        reference_key: "et",
        reference_type: "et",
        locator_text: "Artículos 147",
        locator_kind: "articles",
        locator_start: "147",
        usage_context: "ET art. 147 citado en la respuesta.",
      },
      {
        doc_id: "doc_et_714",
        logical_doc_id: "doc_et",
        source_label: "ET art. 714",
        legal_reference: "ET art. 714",
        source_provider: "DIAN",
        authority: "DIAN",
        source_tier: "Fuente Normativa",
        knowledge_class: "normative_base",
        source_type: "official_primary",
        reference_key: "et",
        reference_type: "et",
        locator_text: "Artículos 714",
        locator_kind: "articles",
        locator_start: "714",
        usage_context: "ET art. 714 citado en la respuesta.",
      },
    ];

    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/llm/status") {
        return Promise.resolve(
          mockJsonResponse({
            llm_runtime: {
              model: "gemini-2.5-flash",
              selected_type: "gemini",
              selected_provider: "gemini_primary",
            },
          })
        );
      }
      if (url === "/api/build-info") {
        return Promise.resolve(mockJsonResponse({ build_info: {} }));
      }
      if (url === "/api/chat/stream") {
        return Promise.resolve(mockChatStreamResponse(chatPayload));
      }
      if (url === "/api/chat") {
        return Promise.resolve(mockJsonResponse(chatPayload));
      }
      if (url.startsWith("/api/feedback")) {
        return Promise.resolve(mockJsonResponse({ feedback: null }));
      }
      return Promise.resolve(mockJsonResponse({}));
    });
    vi.stubGlobal("fetch", fetchMock);

    document.body.innerHTML = renderFullShell(i18n);
    mountChatApp(document.body, { i18n });
    await flushUi();

    const messageInput = document.querySelector<HTMLTextAreaElement>("#message");
    const form = document.querySelector<HTMLFormElement>("#chat-form");
    if (!messageInput || !form) {
      throw new Error("Missing chat composer.");
    }

    messageInput.value = "¿Qué normas debo revisar sobre pérdidas fiscales y firmeza?";
    messageInput.dispatchEvent(new Event("input", { bubbles: true }));
    form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    await flushUi();
    await flushUi();

    const citationItems = Array.from(document.querySelectorAll("#citations li")).map((item) =>
      item.textContent?.replace(/\s+/g, " ").trim() || ""
    );

    expect(citationItems).toHaveLength(5);
    // W1 Phase 1 sort: corpus-backed first, then mention-only by family rank + year desc.
    // Note: citationIssuanceYear extracts ley NUMBER from reference_key when >= 1900,
    // so ley:2010:2019 gets year=2010, ley:1819:2016 falls back to text → year=2016.
    expect(citationItems[0]).toContain("Estatuto Tributario, Artículo 147");
    expect(citationItems[1]).toContain("Estatuto Tributario, Artículo 714");
    expect(citationItems[2]).toContain("Ley 1819 de 2016");
    expect(citationItems[3]).toContain("Ley 1607 de 2012");
    expect(citationItems[4]).toContain("Ley 2010 de 2019");
  });

  it("keeps normative support in clarification mode for semantic 422 turns", async () => {
    const i18n = createI18n("es-CO");
    installFetchMockWithChatQueue([
      {
        status: 422,
        payload: {
          ok: false,
          session_id: "chat_clarification_1",
          error: {
            code: "PC_EVIDENCE_INSUFFICIENT",
            message: "No hay evidencia suficiente para cerrar la respuesta.",
            user_message:
              "Buena pregunta. Para poder asesorarte, necesito un poco mas de informacion:\n\n(1) Precisar periodo exacto y subtema principal que se quiere resolver.\n(2) Indicar tipo de contribuyente y contexto operativo del caso.\n(3) Aportar referencia normativa o formulario clave, si ya existe.\n\n¿Que dato puntual del periodo o del supuesto quieres priorizar para buscar evidencia valida?",
            interaction: {
              mode: "clarification",
              current_question:
                "¿Que dato puntual del periodo o del supuesto quieres priorizar para buscar evidencia valida?",
              turn_index: 0,
              turn_limit: 8,
              route: "decision",
              requirements: [
                "Precisar periodo exacto y subtema principal que se quiere resolver.",
                "Indicar tipo de contribuyente y contexto operativo del caso.",
                "Aportar referencia normativa o formulario clave, si ya existe.",
              ],
            },
          },
        },
      },
    ]);

    document.body.innerHTML = renderFullShell(i18n);
    mountChatApp(document.body, { i18n });
    await flushUi();

    const messageInput = document.querySelector<HTMLTextAreaElement>("#message");
    const form = document.querySelector<HTMLFormElement>("#chat-form");
    if (!messageInput || !form) {
      throw new Error("Missing chat composer.");
    }

    messageInput.value = "cuales son los principales pasos para presentar la declaracion de renta de una pyme en 2026?";
    messageInput.dispatchEvent(new Event("input", { bubbles: true }));
    form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    await flushUi();
    await flushUi();

    const assistantMessages = Array.from(document.querySelectorAll(".bubble-assistant .bubble-text")).map(
      (item) => item.textContent?.replace(/\s+/g, " ").trim() || ""
    );
    const citationItems = Array.from(document.querySelectorAll("#citations li")).map(
      (item) => item.textContent?.replace(/\s+/g, " ").trim() || ""
    );
    const citationsStatus = document.querySelector("#citations-status")?.textContent?.replace(/\s+/g, " ").trim() || "";

    expect(assistantMessages.some((item) => item.includes("Buena pregunta. Para poder asesorarte"))).toBe(true);
    expect(citationItems).toContain("Normativa en espera: falta aclarar el caso actual.");
    expect(citationsStatus).toContain("Comparte el dato solicitado para habilitar soporte normativo.");
    expect(citationsStatus).toContain("Precisar periodo exacto y subtema principal");
    expect(citationsStatus).not.toContain("No se habilitó normativa por error del turno.");
  });

  it("shows deep analysis CTA and caution banner for legal documents", async () => {
    const i18n = createI18n("es-CO");
    const openSpy = vi.fn();
    vi.stubGlobal("open", openSpy);
    const chatPayload = makeChatSuccessPayload({
      traceId: "trace_norma_modal_2",
      sessionId: "chat_norma_modal_2",
      answerMarkdown: "Revisa la Ley 2277 de 2022 para validar el cambio aplicable.",
      followupQueries: [],
    });
    chatPayload.citations = [
      {
        doc_id: "doc_law_2277",
        source_label: "Ley 2277 de 2022",
        legal_reference: "Ley 2277 de 2022",
        source_provider: "Congreso de la República",
        authority: "Congreso de la República",
        source_tier: "Fuente Normativa",
        knowledge_class: "normative_base",
        source_type: "official_primary",
        source_view_url: "/source-view?doc_id=doc_law_2277",
        open_url: "/source-view?doc_id=doc_law_2277",
        reference_type: "ley",
        usage_context: "Ley 2277 de 2022 referenciada en la respuesta.",
      },
    ];

    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/llm/status") {
        return Promise.resolve(
          mockJsonResponse({
            llm_runtime: {
              model: "gemini-2.5-flash",
              selected_type: "gemini",
              selected_provider: "gemini_primary",
            },
          })
        );
      }
      if (url === "/api/build-info") {
        return Promise.resolve(mockJsonResponse({ build_info: {} }));
      }
      if (url === "/api/chat/stream") {
        expect(init?.method).toBe("POST");
        return Promise.resolve(mockChatStreamResponse(chatPayload));
      }
      if (url === "/api/chat") {
        expect(init?.method).toBe("POST");
        return Promise.resolve(mockJsonResponse(chatPayload));
      }
      if (url.startsWith("/api/citation-profile?doc_id=doc_law_2277")) {
        return Promise.resolve(
          mockJsonResponse({
            ok: true,
            title: "Ley 2277 de 2022",
            document_family: "ley",
            binding_force: "Ley o estatuto",
            lead: "Ley ordinaria que modificó reglas de renta relevantes para cierre y cumplimiento.",
            facts: [{ label: "Qué regula", value: "Modifica reglas sustantivas del impuesto sobre la renta." }],
            sections: [
              {
                id: "vigencia",
                title: "Vigencia y lectura práctica",
                body: "Confirma la cadena de modificaciones antes de aplicar el artículo.",
              },
            ],
            caution_banner: {
              title: "Interpretación con jerarquía",
              body: "Prioriza la ley y su reglamentación por encima de conceptos o circulares.",
              tone: "warning",
            },
            analysis_action: {
              label: "Abrir análisis profundo",
              state: "available",
              url: "/normative-analysis?doc_id=doc_law_2277",
              helper_text: "Abre timeline, relaciones y capas secundarias permitidas.",
            },
            companion_action: {
              state: "not_applicable",
            },
            source_action: {
              label: "Ir a documento original",
              url: "/source-view?doc_id=doc_law_2277",
              mode: "official_link",
              helper_text: "Abre la fuente oficial primaria.",
            },
          })
        );
      }
      if (url.startsWith("/api/feedback")) {
        return Promise.resolve(mockJsonResponse({ feedback: null }));
      }
      return Promise.resolve(mockJsonResponse({}));
    });
    vi.stubGlobal("fetch", fetchMock);

    document.body.innerHTML = renderFullShell(i18n);
    mountChatApp(document.body, { i18n });
    await flushUi();

    const messageInput = document.querySelector<HTMLTextAreaElement>("#message");
    const form = document.querySelector<HTMLFormElement>("#chat-form");
    if (!messageInput || !form) {
      throw new Error("Missing chat composer.");
    }

    messageInput.value = "¿Cómo afecta la Ley 2277 la declaración de renta?";
    messageInput.dispatchEvent(new Event("input", { bubbles: true }));
    form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    await flushUi();
    await flushUi();

    document.querySelector<HTMLButtonElement>(".citation-trigger")?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await flushUi();
    await flushUi();

    expect(document.querySelector("#norma-binding-force")?.textContent).toContain("Ley o estatuto");
    expect(document.querySelector("#norma-caution-banner")?.hasAttribute("hidden")).toBe(false);
    expect(document.querySelector("#norma-analysis-btn")?.textContent).toContain("Abrir análisis profundo");
    expect(document.querySelector("#norma-analysis-helper")?.textContent).toContain("timeline, relaciones");

    document.querySelector<HTMLButtonElement>("#norma-analysis-btn")?.click();
    expect(openSpy).toHaveBeenCalledWith("/normative-analysis?doc_id=doc_law_2277", "_blank", "noopener,noreferrer");
  });

  it("keeps the normative caution banner hidden when the payload only contains invisible text", async () => {
    const i18n = createI18n("es-CO");
    const chatPayload = makeChatSuccessPayload({
      traceId: "trace_norma_modal_hidden_banner",
      sessionId: "chat_norma_modal_hidden_banner",
      answerMarkdown: "Revisa el soporte normativo asociado.",
      followupQueries: [],
    });
    chatPayload.citations = [
      {
        doc_id: "doc_law_hidden_banner",
        source_label: "Ley 2277 de 2022",
        legal_reference: "Ley 2277 de 2022",
        source_provider: "Congreso de la República",
        authority: "Congreso de la República",
        source_tier: "Fuente Normativa",
        knowledge_class: "normative_base",
        source_type: "official_primary",
        source_view_url: "/source-view?doc_id=doc_law_hidden_banner",
        open_url: "/source-view?doc_id=doc_law_hidden_banner",
        reference_type: "ley",
      },
    ];

    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/llm/status") {
        return Promise.resolve(
          mockJsonResponse({
            llm_runtime: {
              model: "gemini-2.5-flash",
              selected_type: "gemini",
              selected_provider: "gemini_primary",
            },
          })
        );
      }
      if (url === "/api/build-info") {
        return Promise.resolve(mockJsonResponse({ build_info: {} }));
      }
      if (url === "/api/chat/stream") {
        expect(init?.method).toBe("POST");
        return Promise.resolve(mockChatStreamResponse(chatPayload));
      }
      if (url === "/api/chat") {
        expect(init?.method).toBe("POST");
        return Promise.resolve(mockJsonResponse(chatPayload));
      }
      if (url.startsWith("/api/citation-profile?doc_id=doc_law_hidden_banner")) {
        return Promise.resolve(
          mockJsonResponse({
            ok: true,
            title: "Ley 2277 de 2022",
            document_family: "ley",
            binding_force: "Ley o estatuto",
            lead: "Reforma tributaria con impacto en renta.",
            facts: [{ label: "Qué regula", value: "Ajusta reglas sustantivas del impuesto sobre la renta." }],
            sections: [],
            caution_banner: {
              title: "\u200B",
              body: "\u2060\uFEFF",
              tone: "warning",
            },
            source_action: {
              label: "Ir a documento original",
              url: "/source-view?doc_id=doc_law_hidden_banner",
            },
          })
        );
      }
      if (url.startsWith("/api/feedback")) {
        return Promise.resolve(mockJsonResponse({ feedback: null }));
      }
      return Promise.resolve(mockJsonResponse({}));
    });
    vi.stubGlobal("fetch", fetchMock);

    document.body.innerHTML = renderFullShell(i18n);
    mountChatApp(document.body, { i18n });
    await flushUi();

    const messageInput = document.querySelector<HTMLTextAreaElement>("#message");
    const form = document.querySelector<HTMLFormElement>("#chat-form");
    if (!messageInput || !form) {
      throw new Error("Missing chat composer.");
    }

    messageInput.value = "Muéstrame el soporte normativo";
    messageInput.dispatchEvent(new Event("input", { bubbles: true }));
    form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    await flushUi();
    await flushUi();

    document.querySelector<HTMLButtonElement>(".citation-trigger")?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await flushUi();
    await flushUi();

    expect(document.querySelector("#norma-caution-banner")?.hasAttribute("hidden")).toBe(true);
    expect(document.querySelector("#norma-caution-title")?.textContent).toBe("");
    expect(document.querySelector("#norma-caution-body")?.textContent).toBe("");
  });

  it("renders structured ET article modal content with quote and expert accordion", async () => {
    const i18n = createI18n("es-CO");
    const chatPayload = makeChatSuccessPayload({
      traceId: "trace_norma_modal_et_259",
      sessionId: "chat_norma_modal_et_259",
      answerMarkdown: "Revisa el artículo 259 del Estatuto Tributario para validar el límite de descuentos.",
      followupQueries: [],
    });
    chatPayload.citations = [
      {
        doc_id: "doc_et",
        source_label: "Estatuto Tributario",
        legal_reference: "Estatuto Tributario",
        source_provider: "DIAN",
        authority: "DIAN",
        source_tier: "Fuente Normativa",
        knowledge_class: "normative_base",
        source_type: "official_primary",
        source_view_url: "/source-view?doc_id=doc_et",
        open_url: "/source-view?doc_id=doc_et",
        reference_key: "et",
        reference_type: "et_dur",
        locator_text: "Artículo 259",
        locator_kind: "article",
        locator_start: "259",
        usage_context: "Artículo 259 del Estatuto Tributario.",
      },
    ];

    const expectedProfileUrl = "/api/citation-profile?doc_id=doc_et";

    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/llm/status") {
        return Promise.resolve(
          mockJsonResponse({
            llm_runtime: {
              model: "gemini-2.5-flash",
              selected_type: "gemini",
              selected_provider: "gemini_primary",
            },
          })
        );
      }
      if (url === "/api/build-info") {
        return Promise.resolve(mockJsonResponse({ build_info: {} }));
      }
      if (url === "/api/chat/stream") {
        expect(init?.method).toBe("POST");
        return Promise.resolve(mockChatStreamResponse(chatPayload));
      }
      if (url === "/api/chat") {
        expect(init?.method).toBe("POST");
        return Promise.resolve(mockJsonResponse(chatPayload));
      }
      if (url.startsWith(expectedProfileUrl)) {
        return Promise.resolve(
          mockJsonResponse({
            ok: true,
            title: "Estatuto Tributario, Artículo 259",
            document_family: "et_dur",
            binding_force: "Ley o estatuto",
            lead: "Texto vigente del Artículo 259 del Estatuto Tributario.",
            facts: [{ label: "Artículo consultado", value: "ET Artículo 259. Límite de los descuentos." }],
            vigencia_detail: {
              label: "Texto vigente verificado en compilación oficial",
              basis: "Base actual: artículo 29 de la Ley 383 de 1997.",
              notes: "Parágrafo 2 modificado por el artículo 22 de la Ley 633 de 2000.",
              last_verified_date: "2026-03-12",
              evidence_status: "verified",
            },
            original_text: {
              title: "Texto original relevante",
              quote:
                "ARTICULO 259. LIMITE DE LOS DESCUENTOS. En ningún caso los descuentos tributarios pueden exceder el valor del impuesto básico de renta.",
              source_url: "https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario.htm#259",
              evidence_status: "verified",
            },
            expert_comment: {
              topic_label: "Respecto al límite de descuentos tributarios",
              body: "Ahora bien, los DTC están sometidos al límite de que trata el artículo 259 del Estatuto Tributario.",
              source_label: "Concepto DIAN 6363 de 2023 - TTD",
              source_url: "https://www.dian.gov.co/",
              accordion_default: "closed",
              evidence_status: "verified",
            },
            sections: [
              {
                id: "texto_original_relevante",
                title: "Texto original relevante",
                body: "No debería renderizarse porque existe bloque estructurado.",
              },
            ],
            analysis_action: {
              label: "Abrir análisis normativo",
              state: "available",
              url: "/normative-analysis?doc_id=doc_et",
            },
            companion_action: { state: "not_applicable" },
            source_action: {
              label: "Ir a documento original",
              url: "https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario.htm#259",
              mode: "official_link",
            },
          })
        );
      }
      if (url.startsWith("/api/feedback")) {
        return Promise.resolve(mockJsonResponse({ feedback: null }));
      }
      return Promise.resolve(mockJsonResponse({}));
    });
    vi.stubGlobal("fetch", fetchMock);

    document.body.innerHTML = renderFullShell(i18n);
    mountChatApp(document.body, { i18n });
    await flushUi();

    const messageInput = document.querySelector<HTMLTextAreaElement>("#message");
    const form = document.querySelector<HTMLFormElement>("#chat-form");
    if (!messageInput || !form) {
      throw new Error("Missing chat composer.");
    }

    messageInput.value = "descuentos tributarios";
    messageInput.dispatchEvent(new Event("input", { bubbles: true }));
    form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    await flushUi();
    await flushUi();

    const citationTrigger = document.querySelector<HTMLButtonElement>("#citations .citation-trigger");
    expect(citationTrigger?.textContent).toContain("Artículo 259");
    citationTrigger?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await flushUi();
    await flushUi();

    await vi.waitFor(() => {
      expect(
        fetchMock.mock.calls.some(([url]) => String(url).includes(expectedProfileUrl))
      ).toBe(true);
    });
    // ET article profiles with original_text hide base facts (including vigencia)
    expect(document.querySelector("#norma-facts")?.hidden).toBe(true);
    expect(document.querySelector(".norma-quote-block")?.textContent).toContain(
      "En ningún caso los descuentos tributarios pueden exceder el valor del impuesto básico de renta."
    );
    // Expert comment accordion rendering was removed; expert_comment is accepted but not displayed
    expect(document.querySelector("#norma-sections")?.textContent).not.toContain(
      "No debería renderizarse porque existe bloque estructurado."
    );
  });

  it("normalizes formulario and formato titles in normative support cards", async () => {
    const i18n = createI18n("es-CO");
    const chatPayload = makeChatSuccessPayload({
      traceId: "trace_form_title_case_1",
      sessionId: "chat_form_title_case_1",
      answerMarkdown: "Revisa los soportes normativos detectados.",
      followupQueries: [],
    });
    chatPayload.citations = [
      {
        doc_id: "doc_form_110",
        source_label: "Formulario 110 declaracion de renta y complementario para personas juridicas",
        legal_reference: "Formulario 110 declaracion de renta y complementario para personas juridicas",
        source_provider: "DIAN",
        authority: "DIAN",
        source_tier: "Fuente Normativa",
        knowledge_class: "normative_base",
        source_type: "official_primary",
        reference_key: "formulario:110",
        reference_type: "formulario",
        usage_context: "Formulario 110 detectado en la respuesta.",
      },
      {
        doc_id: "doc_form_2516",
        source_label: "Formato 2516 conciliacion fiscal para obligados a llevar contabilidad",
        legal_reference: "Formato 2516 conciliacion fiscal para obligados a llevar contabilidad",
        source_provider: "DIAN",
        authority: "DIAN",
        source_tier: "Fuente Normativa",
        knowledge_class: "normative_base",
        source_type: "official_primary",
        reference_key: "formulario:2516",
        reference_type: "formulario",
        usage_context: "Formato 2516 detectado en la respuesta.",
      },
    ];

    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url === "/api/llm/status") {
          return Promise.resolve(
            mockJsonResponse({
              llm_runtime: {
                model: "gemini-2.5-flash",
                selected_type: "gemini",
                selected_provider: "gemini_primary",
              },
            })
          );
        }
        if (url === "/api/build-info") {
          return Promise.resolve(mockJsonResponse({ build_info: {} }));
        }
        if (url === "/api/chat/stream") {
          expect(init?.method).toBe("POST");
          return Promise.resolve(mockChatStreamResponse(chatPayload));
        }
        if (url === "/api/chat") {
          expect(init?.method).toBe("POST");
          return Promise.resolve(mockJsonResponse(chatPayload));
        }
        if (url.startsWith("/api/feedback")) {
          return Promise.resolve(mockJsonResponse({ feedback: null }));
        }
        return Promise.resolve(mockJsonResponse({}));
      })
    );

    document.body.innerHTML = renderFullShell(i18n);
    mountChatApp(document.body, { i18n });
    await flushUi();

    const messageInput = document.querySelector<HTMLTextAreaElement>("#message");
    const form = document.querySelector<HTMLFormElement>("#chat-form");
    if (!messageInput || !form) {
      throw new Error("Missing chat composer.");
    }

    messageInput.value = "Muéstrame la normativa detectada";
    messageInput.dispatchEvent(new Event("input", { bubbles: true }));
    form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    await flushUi();
    await flushUi();

    const citationTitles = Array.from(
      document.querySelectorAll<HTMLElement>(".citation-trigger .citation-trigger__title"),
    ).map((item) => item.textContent?.replace(/\s+/g, " ").trim() || "");

    expect(citationTitles).toContain(
      "Formulario 110: Declaracion de Renta y Complementario para Personas Juridicas"
    );
    expect(citationTitles).toContain(
      "Formato 2516: Conciliacion Fiscal para Obligados a Llevar Contabilidad"
    );
  });

  it("hydrates the composer draft from the handoff prefill query", async () => {
    const i18n = createI18n("es-CO");
    installFetchMock();
    window.history.pushState({}, "", "/?prefill=%C2%BFEste%20formulario%20es%20obligatorio%3F");

    document.body.innerHTML = renderFullShell(i18n);
    mountChatApp(document.body, { i18n });
    await flushUi();

    const messageInput = document.querySelector<HTMLTextAreaElement>("#message");
    expect(messageInput?.value).toBe("¿Este formulario es obligatorio?");
    expect(window.location.search).toBe("");
  });
});
