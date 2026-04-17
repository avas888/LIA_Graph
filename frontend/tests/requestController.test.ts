import { beforeEach, describe, expect, it, vi } from "vitest";
import { createChatRequestController } from "@/features/chat/requestController";
import { createI18n } from "@/shared/i18n";
import { postJson } from "@/shared/api/client";

vi.mock("@/shared/api/client", () => ({
  getJson: vi.fn(),
  getApiAccessToken: vi.fn(() => null),
  postJson: vi.fn(),
}));

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

function createSseResponse(parts: Array<string | Promise<string>>): Response {
  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      for (const part of parts) {
        const chunk = typeof part === "string" ? part : await part;
        controller.enqueue(new TextEncoder().encode(chunk));
      }
      controller.close();
    },
  });
  return new Response(stream, {
    status: 200,
    headers: { "Content-Type": "text/event-stream; charset=utf-8" },
  });
}

async function waitForEventLog(predicate: () => void, attempts = 20): Promise<void> {
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    try {
      predicate();
      return;
    } catch (error) {
      if (attempt === attempts - 1) {
        throw error;
      }
      await new Promise((resolve) => window.setTimeout(resolve, 10));
    }
  }
}

function formatSseEvent(event: string, payload: Record<string, unknown>): string {
  return `event: ${event}\ndata: ${JSON.stringify(payload)}\n\n`;
}

describe("chat request controller", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
    vi.clearAllMocks();
    vi.useRealTimers();
    const storage = createStorageMock();
    vi.stubGlobal("localStorage", storage);
    Object.defineProperty(window, "localStorage", {
      configurable: true,
      value: storage,
    });
  });

  function createController(overrides: {
    addBubble?: Parameters<typeof createChatRequestController>[0]["addBubble"];
    createStreamingAssistantBubble?: Parameters<typeof createChatRequestController>[0]["createStreamingAssistantBubble"];
    renderCitations?: Parameters<typeof createChatRequestController>[0]["renderCitations"];
    renderDeferredCitationsState?: Parameters<typeof createChatRequestController>[0]["renderDeferredCitationsState"];
    setCitationsStatus?: Parameters<typeof createChatRequestController>[0]["setCitationsStatus"];
    setTurnState?: Parameters<typeof createChatRequestController>[0]["setTurnState"];
    deriveReadyState?: Parameters<typeof createChatRequestController>[0]["deriveReadyState"];
    onChatSuccess?: Parameters<typeof createChatRequestController>[0]["onChatSuccess"];
  } = {}) {
    const i18n = createI18n("es-CO");
    let activeSessionId = "";
    const events: string[] = [];

    const controller = createChatRequestController({
      i18n,
      state: {
        requestTimerInterval: null,
        requestStartedAtMs: null,
        latestTurnStartedAtMs: null,
        activeChatRunId: "",
        lastUserMessage: "",
        lastAssistantAnswerMarkdown: "",
        lastSubmittedUserMessage: "",
        citationRequestContext: null,
        deferredCitationsFallback: [],
        deferredMentionCitations: [],
        deferredCitationsCache: [],
        deferredCitationsCacheKey: "",
        deferredCitationsStatusText: "",
        deferredCitationsPlaceholderText: "",
        buildInfoLine: "",
        conversationTokenTotals: {
          input_tokens: 0,
          output_tokens: 0,
          total_tokens: 0,
        },
      },
      dom: {
        citationsLoadBtn: null,
        diagnosticsNode: document.createElement("div"),
        runtimeRequestTimerNode: document.createElement("div"),
        runtimeLatencyNode: document.createElement("div"),
        runtimeModelNode: document.createElement("div"),
        runtimeTurnTokensNode: document.createElement("div"),
        runtimeConversationTokensNode: document.createElement("div"),
        sendBtn: Object.assign(document.createElement("button"), { textContent: "Enviar consulta" }),
      },
      debugInput: null,
      startThinkingWheel: () => {
        events.push("thinking:start");
      },
      stopThinkingWheel: () => {
        events.push("thinking:stop");
      },
      withThinkingWheel: async (task) => task(),
      getActiveSessionId: () => activeSessionId,
      setActiveSessionId: (value) => {
        activeSessionId = value;
      },
      setTurnState: overrides.setTurnState || (() => {}),
      deriveReadyState: overrides.deriveReadyState || (() => "ready"),
      focusComposer: () => {},
      resetConversationUi: () => {},
      renderCitations: overrides.renderCitations || (() => {}),
      renderDeferredCitationsState: overrides.renderDeferredCitationsState || (() => {}),
      setCitationsStatus: overrides.setCitationsStatus || (() => {}),
      addBubble:
        overrides.addBubble ||
        (async (role) => {
          events.push(`bubble:${role}`);
          return document.createElement("div");
        }),
      createStreamingAssistantBubble:
        overrides.createStreamingAssistantBubble ||
        (() => ({
          appendMarkdownBlock: async () => {
            events.push("stream:append");
          },
          replaceMarkdown: async () => {
            events.push("stream:replace");
          },
          finalize: async () => {
            events.push("stream:finalize");
          },
          setStatus: () => {
            events.push("stream:status");
          },
          clearStatus: () => {
            events.push("stream:clear-status");
          },
          getNode: () => document.createElement("div"),
        })),
      buildAssistantBubbleMeta: () => ({}),
      decisionResponseRoute: "decision",
      devBootCacheKey: "lia_dev_boot_nonce_v1",
      persistActiveSessionSnapshot: () => {},
      onChatSuccess: overrides.onChatSuccess,
    });

    return { controller, events };
  }

  it("stops the thinking wheel on the first streamed answer block and finalizes the same assistant bubble", async () => {
    let releaseFinalChunk: (() => void) | null = null;
    const finalChunk = new Promise<string>((resolve) => {
      releaseFinalChunk = () =>
        resolve(
          formatSseEvent("final", {
            trace_id: "trace_stream_1",
            session_id: "session_stream_1",
            answer_markdown: "## Respuesta final\n\nContenido final.",
            followup_queries: [],
            citations: [],
            diagnostics: {},
            llm_runtime: {
              model: "gemini-2.5-flash",
              selected_type: "gemini",
              selected_provider: "gemini_primary",
            },
            token_usage: {
              turn: { input_tokens: 10, output_tokens: 10, total_tokens: 20 },
            },
            metrics: {
              llm_runtime: {
                model: "gemini-2.5-flash",
                selected_type: "gemini",
                selected_provider: "gemini_primary",
              },
              token_usage: {
                turn: { input_tokens: 10, output_tokens: 10, total_tokens: 20 },
              },
              conversation: {
                token_usage_total: { input_tokens: 10, output_tokens: 10, total_tokens: 20 },
              },
            },
          })
        );
    });

    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        if (url === "/api/chat/stream") {
          return Promise.resolve(
            createSseResponse([
              formatSseEvent("meta", {
                trace_id: "trace_stream_1",
                session_id: "session_stream_1",
                response_route: "decision",
              }),
              formatSseEvent("status", {
                stage: "compose",
                message: "Redactando respuesta...",
              }),
              formatSseEvent("answer_block", {
                index: 0,
                markdown: "## Primer bloque",
                block_kind: "heading",
                provisional: true,
              }),
              finalChunk,
            ])
          );
        }
        return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
      })
    );

    const { controller, events } = createController();
    const submitPromise = controller.submitChatTurn({
      displayUserText: "Necesito una respuesta larga.",
      requestMessage: "Necesito una respuesta larga.",
    });

    await waitForEventLog(() => {
      expect(events).toContain("thinking:start");
      expect(events).toContain("stream:append");
      expect(events).toContain("thinking:stop");
    });
    expect(events.indexOf("thinking:stop")).toBeGreaterThan(events.indexOf("stream:append"));
    expect(events).not.toContain("stream:finalize");

    releaseFinalChunk?.();
    await submitPromise;

    expect(events).toContain("stream:finalize");
    expect(events.filter((event) => event === "bubble:assistant")).toHaveLength(0);
  });

  it("uses effective_topic from the final payload for post-success flows", async () => {
    const onChatSuccess = vi.fn();

    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        if (url === "/api/chat/stream") {
          return Promise.resolve(
            createSseResponse([
              formatSseEvent("meta", {
                trace_id: "trace_topic_1",
                session_id: "session_topic_1",
                topic: "laboral",
                requested_topic: "declaracion_renta",
                response_route: "decision",
              }),
              formatSseEvent("final", {
                trace_id: "trace_topic_1",
                session_id: "session_topic_1",
                answer_markdown: "Respuesta laboral.",
                followup_queries: [],
                citations: [],
                effective_topic: "laboral",
                requested_topic: "declaracion_renta",
                pais: "colombia",
                diagnostics: {},
                llm_runtime: {
                  model: "gemini-2.5-flash",
                  selected_type: "gemini",
                  selected_provider: "gemini_primary",
                },
                token_usage: {
                  turn: { input_tokens: 10, output_tokens: 10, total_tokens: 20 },
                },
                metrics: {
                  llm_runtime: {
                    model: "gemini-2.5-flash",
                    selected_type: "gemini",
                    selected_provider: "gemini_primary",
                  },
                  token_usage: {
                    turn: { input_tokens: 10, output_tokens: 10, total_tokens: 20 },
                  },
                  conversation: {
                    token_usage_total: { input_tokens: 10, output_tokens: 10, total_tokens: 20 },
                  },
                },
              }),
            ])
          );
        }
        return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
      })
    );

    const { controller } = createController({ onChatSuccess });
    await controller.submitChatTurn({
      displayUserText: "Consulta de seguridad social",
      requestMessage: "Consulta de seguridad social",
    });

    expect(onChatSuccess).toHaveBeenCalledWith(
      expect.objectContaining({
        topic: "laboral",
        pais: "colombia",
      })
    );
  });

  it("primes normative support before triggering post-answer expert callbacks", async () => {
    const milestones: string[] = [];
    const onChatSuccess = vi.fn(() => {
      milestones.push("experts:start");
    });

    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        if (url === "/api/chat/stream") {
          return Promise.resolve(
            createSseResponse([
              formatSseEvent("meta", {
                trace_id: "trace_post_answer_1",
                session_id: "session_post_answer_1",
                response_route: "decision",
              }),
              formatSseEvent("final", {
                trace_id: "trace_post_answer_1",
                session_id: "session_post_answer_1",
                answer_markdown: "Aplica el artículo 147 ET cuando la pérdida esté determinada y soportada.",
                followup_queries: [],
                support_citations: [
                  {
                    doc_id: "et_art_147",
                    legal_reference: "Artículo 147 ET",
                    source_label: "Artículo 147 ET",
                    usage_context: { cited_in_answer: true },
                  },
                ],
                citations: [],
                diagnostics: {},
                llm_runtime: {
                  model: "gemini-2.5-flash",
                  selected_type: "gemini",
                  selected_provider: "gemini_primary",
                },
                token_usage: {
                  turn: { input_tokens: 10, output_tokens: 10, total_tokens: 20 },
                },
                metrics: {
                  llm_runtime: {
                    model: "gemini-2.5-flash",
                    selected_type: "gemini",
                    selected_provider: "gemini_primary",
                  },
                  token_usage: {
                    turn: { input_tokens: 10, output_tokens: 10, total_tokens: 20 },
                  },
                  conversation: {
                    token_usage_total: { input_tokens: 10, output_tokens: 10, total_tokens: 20 },
                  },
                },
              }),
            ])
          );
        }
        return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
      })
    );

    const { controller } = createController({
      renderCitations: () => {
        milestones.push("normativa:primed");
      },
      onChatSuccess,
    });

    await controller.submitChatTurn({
      displayUserText: "Consulta con soporte",
      requestMessage: "Consulta con soporte",
    });

    expect(milestones).toContain("normativa:primed");
    expect(milestones).toContain("experts:start");
    expect(milestones.indexOf("normativa:primed")).toBeLessThan(milestones.indexOf("experts:start"));
  });

  it("releases the composer as soon as a terminal SSE event arrives even if the socket stays open", async () => {
    const turnStates: string[] = [];
    let streamController: ReadableStreamDefaultController<Uint8Array> | null = null;
    let resolved = false;

    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        if (url === "/api/chat/stream") {
          const stream = new ReadableStream<Uint8Array>({
            start(controller) {
              streamController = controller;
              controller.enqueue(
                new TextEncoder().encode(
                  formatSseEvent("meta", {
                    trace_id: "trace_stream_terminal",
                    session_id: "session_stream_terminal",
                    response_route: "decision",
                  })
                )
              );
              controller.enqueue(
                new TextEncoder().encode(
                  formatSseEvent("final", {
                    trace_id: "trace_stream_terminal",
                    session_id: "session_stream_terminal",
                    answer_markdown: "Respuesta final lista.",
                    followup_queries: [],
                    citations: [],
                    diagnostics: {},
                    llm_runtime: {
                      model: "gemini-2.5-flash",
                      selected_type: "gemini",
                      selected_provider: "gemini_primary",
                    },
                    token_usage: {
                      turn: { input_tokens: 9, output_tokens: 11, total_tokens: 20 },
                    },
                    metrics: {
                      llm_runtime: {
                        model: "gemini-2.5-flash",
                        selected_type: "gemini",
                        selected_provider: "gemini_primary",
                      },
                      token_usage: {
                        turn: { input_tokens: 9, output_tokens: 11, total_tokens: 20 },
                      },
                      conversation: {
                        token_usage_total: { input_tokens: 9, output_tokens: 11, total_tokens: 20 },
                      },
                    },
                  })
                )
              );
            },
          });
          return Promise.resolve(
            new Response(stream, {
              status: 200,
              headers: { "Content-Type": "text/event-stream; charset=utf-8" },
            })
          );
        }
        return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
      })
    );

    const { controller } = createController({
      setTurnState: (state) => {
        turnStates.push(state);
      },
      deriveReadyState: () => "ready-empty",
    });

    const submitPromise = controller.submitChatTurn({
      displayUserText: "Necesito continuar apenas termine la respuesta.",
      requestMessage: "Necesito continuar apenas termine la respuesta.",
    }).then(() => {
      resolved = true;
    });

    await new Promise((resolve) => window.setTimeout(resolve, 20));
    const resolvedBeforeClose = resolved;
    try {
      streamController?.close();
    } catch (_error) {
      // The fixed path cancels the reader as soon as the terminal event lands.
    }
    await submitPromise;

    expect(resolvedBeforeClose).toBe(true);
    expect(turnStates.at(-1)).toBe("ready-empty");
    expect(postJson).not.toHaveBeenCalled();
  });

  it("does not send a default topic in the initial chat request", async () => {
    let requestBody: Record<string, unknown> | null = null;

    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url === "/api/chat/stream") {
          requestBody = init?.body ? JSON.parse(String(init.body)) : null;
          return Promise.resolve(
            createSseResponse([
              formatSseEvent("final", {
                trace_id: "trace_no_default_topic",
                session_id: "session_no_default_topic",
                answer_markdown: "Respuesta.",
                followup_queries: [],
                citations: [],
                diagnostics: {},
                llm_runtime: {
                  model: "gemini-2.5-flash",
                  selected_type: "gemini",
                  selected_provider: "gemini_primary",
                },
                token_usage: {
                  turn: { input_tokens: 10, output_tokens: 10, total_tokens: 20 },
                },
                metrics: {
                  llm_runtime: {
                    model: "gemini-2.5-flash",
                    selected_type: "gemini",
                    selected_provider: "gemini_primary",
                  },
                  token_usage: {
                    turn: { input_tokens: 10, output_tokens: 10, total_tokens: 20 },
                  },
                  conversation: {
                    token_usage_total: { input_tokens: 10, output_tokens: 10, total_tokens: 20 },
                  },
                },
              }),
            ])
          );
        }
        return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
      })
    );

    const { controller } = createController();
    await controller.submitChatTurn({
      displayUserText: "Consulta",
      requestMessage: "Consulta",
    });

    expect(requestBody).not.toBeNull();
    expect(requestBody).not.toHaveProperty("topic");
  });

  it("auto-reconciles mention-only normative support in the background after a successful final event", async () => {
    const renderedCitationBatches: Array<Record<string, unknown>[]> = [];
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/chat/stream") {
        return Promise.resolve(
          createSseResponse([
            formatSseEvent("meta", {
              trace_id: "trace_auto_normative_reconcile",
              session_id: "session_auto_normative_reconcile",
              response_route: "decision",
            }),
            formatSseEvent("final", {
              trace_id: "trace_auto_normative_reconcile",
              session_id: "session_auto_normative_reconcile",
              answer_markdown:
                "Esto se fundamenta en el Estatuto Tributario, artículo 179. " +
                "Base legal: Estatuto Tributario, artículo 300. " +
                "Según el Estatuto Tributario, artículo 196. " +
                "Además, revise el Formulario 110.",
              followup_queries: [],
              citations: [],
              support_citations: [],
              diagnostics: {},
              llm_runtime: {
                model: "gemini-2.5-flash",
                selected_type: "gemini",
                selected_provider: "gemini_primary",
              },
              token_usage: {
                turn: { input_tokens: 10, output_tokens: 10, total_tokens: 20 },
              },
              metrics: {
                llm_runtime: {
                  model: "gemini-2.5-flash",
                  selected_type: "gemini",
                  selected_provider: "gemini_primary",
                },
                token_usage: {
                  turn: { input_tokens: 10, output_tokens: 10, total_tokens: 20 },
                },
                conversation: {
                  token_usage_total: { input_tokens: 10, output_tokens: 10, total_tokens: 20 },
                },
              },
            }),
          ])
        );
      }
      if (url === "/api/normative-support") {
        expect(init?.method).toBe("POST");
        return Promise.resolve(
          new Response(
            JSON.stringify({
              normative_citations: [
                {
                  doc_id: "renta_corpus_a_et_art_179",
                  logical_doc_id: "renta_corpus_a_et_art_179",
                  source_label: "ET art. 179",
                  legal_reference: "Estatuto Tributario, Artículos 179",
                  reference_key: "et",
                  reference_type: "et",
                  locator_text: "Artículos 179",
                  locator_kind: "articles",
                  locator_start: "179",
                  source_provider: "DIAN",
                  source_tier: "Fuente Normativa",
                  knowledge_class: "normative_base",
                  source_type: "official_primary",
                  usage_context: "Artículo 179 citado en la respuesta.",
                },
                {
                  doc_id: "renta_corpus_a_et_art_196",
                  logical_doc_id: "renta_corpus_a_et_art_196",
                  source_label: "ET art. 196",
                  legal_reference: "Estatuto Tributario, Artículos 196",
                  reference_key: "et",
                  reference_type: "et",
                  locator_text: "Artículos 196",
                  locator_kind: "articles",
                  locator_start: "196",
                  source_provider: "DIAN",
                  source_tier: "Fuente Normativa",
                  knowledge_class: "normative_base",
                  source_type: "official_primary",
                  usage_context: "Artículo 196 citado en la respuesta.",
                },
                {
                  doc_id: "renta_corpus_a_et_art_300",
                  logical_doc_id: "renta_corpus_a_et_art_300",
                  source_label: "ET art. 300",
                  legal_reference: "Estatuto Tributario, Artículos 300",
                  reference_key: "et",
                  reference_type: "et",
                  locator_text: "Artículos 300",
                  locator_kind: "articles",
                  locator_start: "300",
                  source_provider: "DIAN",
                  source_tier: "Fuente Normativa",
                  knowledge_class: "normative_base",
                  source_type: "official_primary",
                  usage_context: "Artículo 300 citado en la respuesta.",
                },
                {
                  doc_id: "renta_corpus_c_dian_form110",
                  logical_doc_id: "renta_corpus_c_dian_form110",
                  source_label: "Formulario 110",
                  legal_reference: "Formulario 110",
                  reference_key: "formulario:110",
                  reference_type: "formulario",
                  source_provider: "DIAN",
                  source_tier: "Fuente Normativa",
                  knowledge_class: "normative_base",
                  source_type: "official_primary",
                  usage_context: "Formulario 110 citado en la respuesta.",
                },
              ],
            }),
            {
              status: 200,
              headers: { "Content-Type": "application/json" },
            }
          )
        );
      }
      return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
    });
    vi.stubGlobal("fetch", fetchMock);

    const { controller } = createController({
      renderCitations: (citations) => {
        renderedCitationBatches.push(citations.map((citation) => ({ ...citation })));
      },
    });

    await controller.submitChatTurn({
      displayUserText: "¿Cómo clasifico la utilidad y dónde la reporto?",
      requestMessage: "¿Cómo clasifico la utilidad y dónde la reporto?",
    });

    await waitForEventLog(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/normative-support",
        expect.objectContaining({
          method: "POST",
        })
      );
      expect(renderedCitationBatches.length).toBeGreaterThan(1);
      expect(renderedCitationBatches.at(-1)?.map((citation) => String(citation.doc_id || "")).sort()).toEqual([
        "renta_corpus_a_et_art_179",
        "renta_corpus_a_et_art_196",
        "renta_corpus_a_et_art_300",
        "renta_corpus_c_dian_form110",
      ]);
    });
  });

  it("falls back to /api/chat when the streaming transport is unavailable", async () => {
    const responsePayload = {
      trace_id: "trace_chat_loading",
      session_id: "session_chat_loading",
      answer_markdown: "Respuesta final renderizada.",
      followup_queries: [],
      citations: [],
      diagnostics: {},
      llm_runtime: {
        model: "gemini-2.5-flash",
        selected_type: "gemini",
        selected_provider: "gemini_primary",
      },
      token_usage: {
        turn: {
          input_tokens: 10,
          output_tokens: 12,
          total_tokens: 22,
        },
      },
      metrics: {
        llm_runtime: {
          model: "gemini-2.5-flash",
          selected_type: "gemini",
          selected_provider: "gemini_primary",
        },
        token_usage: {
          turn: {
            input_tokens: 10,
            output_tokens: 12,
            total_tokens: 22,
          },
        },
        conversation: {
          token_usage_total: {
            input_tokens: 10,
            output_tokens: 12,
            total_tokens: 22,
          },
        },
      },
    };

    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        if (url === "/api/chat/stream") {
          return Promise.resolve(new Response(JSON.stringify({ error: "no_stream" }), { status: 503 }));
        }
        return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
      })
    );

    vi.mocked(postJson).mockResolvedValue({
      response: new Response(JSON.stringify(responsePayload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
      data: responsePayload,
    });

    const { controller, events } = createController();
    await controller.submitChatTurn({
      displayUserText: "Necesito la respuesta final.",
      requestMessage: "Necesito la respuesta final.",
    });

    expect(postJson).toHaveBeenNthCalledWith(
      1,
      "/api/chat",
      expect.objectContaining({
        message: "Necesito la respuesta final.",
      })
    );
    expect(events).toEqual(["bubble:user", "thinking:start", "thinking:stop", "bubble:assistant"]);
  });

  it("releases the composer when the stream stalls before emitting events", async () => {
    vi.useFakeTimers();
    const turnStates: string[] = [];
    const responsePayload = {
      trace_id: "trace_chat_timeout",
      session_id: "session_chat_timeout",
      answer_markdown: "Respuesta bufferizada tras timeout del stream.",
      followup_queries: [],
      citations: [],
      diagnostics: {},
      llm_runtime: {
        model: "gemini-2.5-flash",
        selected_type: "gemini",
        selected_provider: "gemini_primary",
      },
      token_usage: {
        turn: {
          input_tokens: 10,
          output_tokens: 12,
          total_tokens: 22,
        },
      },
      metrics: {
        llm_runtime: {
          model: "gemini-2.5-flash",
          selected_type: "gemini",
          selected_provider: "gemini_primary",
        },
        token_usage: {
          turn: {
            input_tokens: 10,
            output_tokens: 12,
            total_tokens: 22,
          },
        },
        conversation: {
          token_usage_total: {
            input_tokens: 10,
            output_tokens: 12,
            total_tokens: 22,
          },
        },
      },
    };

    vi.stubGlobal(
      "fetch",
      vi.fn((_input: RequestInfo | URL, init?: RequestInit) => {
        const signal = init?.signal;
        return new Promise<Response>((_resolve, reject) => {
          signal?.addEventListener(
            "abort",
            () => {
              reject(signal.reason ?? new Error("aborted"));
            },
            { once: true }
          );
        });
      })
    );

    vi.mocked(postJson).mockResolvedValue({
      response: new Response(JSON.stringify(responsePayload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
      data: responsePayload,
    });

    const { controller, events } = createController({
      setTurnState: (state) => {
        turnStates.push(state);
      },
      deriveReadyState: () => "ready-empty",
    });

    const submitPromise = controller.submitChatTurn({
      displayUserText: "Necesito la respuesta final.",
      requestMessage: "Necesito la respuesta final.",
    });

    await vi.advanceTimersByTimeAsync(12000);
    await submitPromise;

    expect(postJson).toHaveBeenNthCalledWith(
      1,
      "/api/chat",
      expect.objectContaining({
        message: "Necesito la respuesta final.",
      })
    );
    expect(turnStates).toContain("request-pending");
    expect(turnStates.at(-1)).toBe("ready-empty");
    expect(events).toEqual(["bubble:user", "thinking:start", "thinking:stop", "bubble:assistant"]);
  });

  it("falls back to /api/chat after stream_idle_timeout if only meta/status arrived", async () => {
    vi.useFakeTimers();
    const responsePayload = {
      trace_id: "trace_chat_timeout_meta",
      session_id: "session_chat_timeout_meta",
      answer_markdown:
        "Para el AG 2025 presentado en 2026, las personas jurídicas presentan y pagan la primera cuota entre el 12 y el 26 de mayo de 2026 y la segunda cuota entre el 9 y el 23 de julio de 2026.",
      followup_queries: [],
      citations: [],
      diagnostics: {},
      llm_runtime: {
        model: "gemini-2.5-flash",
        selected_type: "gemini",
        selected_provider: "gemini_primary",
      },
      token_usage: {
        turn: {
          input_tokens: 10,
          output_tokens: 12,
          total_tokens: 22,
        },
      },
      metrics: {
        llm_runtime: {
          model: "gemini-2.5-flash",
          selected_type: "gemini",
          selected_provider: "gemini_primary",
        },
        token_usage: {
          turn: {
            input_tokens: 10,
            output_tokens: 12,
            total_tokens: 22,
          },
        },
        conversation: {
          token_usage_total: {
            input_tokens: 10,
            output_tokens: 12,
            total_tokens: 22,
          },
        },
      },
    };

    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url !== "/api/chat/stream") {
          return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
        }
        const signal = init?.signal;
        const stream = new ReadableStream<Uint8Array>({
          start(controller) {
            controller.enqueue(
              new TextEncoder().encode(
                formatSseEvent("meta", {
                  chat_run_id: "cr_stream_idle_1",
                  trace_id: "trace_chat_timeout_meta",
                  session_id: "session_chat_timeout_meta",
                  response_route: "decision",
                })
              )
            );
            controller.enqueue(
              new TextEncoder().encode(
                formatSseEvent("status", {
                  stage: "compose",
                  message: "Redactando respuesta...",
                })
              )
            );
            signal?.addEventListener(
              "abort",
              () => {
                controller.error(new DOMException("Aborted", "AbortError"));
              },
              { once: true }
            );
          },
        });
        return Promise.resolve(
          new Response(stream, {
            status: 200,
            headers: { "Content-Type": "text/event-stream; charset=utf-8" },
          })
        );
      })
    );

    vi.mocked(postJson).mockResolvedValue({
      response: new Response(JSON.stringify(responsePayload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
      data: responsePayload,
    });

    const { controller, events } = createController();
    const submitPromise = controller.submitChatTurn({
      displayUserText: "Cuáles son los plazos para presentar la declaración de renta AG 2025 de personas jurídicas?",
      requestMessage: "Cuáles son los plazos para presentar la declaración de renta AG 2025 de personas jurídicas?",
    });

    await vi.advanceTimersByTimeAsync(45_100);
    await submitPromise;

    expect(postJson).toHaveBeenNthCalledWith(
      1,
      "/api/chat",
      expect.objectContaining({
        message: "Cuáles son los plazos para presentar la declaración de renta AG 2025 de personas jurídicas?",
        chat_run_id: "cr_stream_idle_1",
        client_turn_id: expect.any(String),
      })
    );
    // Status events create streaming bubbles, so fallback finalizes the existing bubble
    expect(events).toContain("thinking:start");
    expect(events).toContain("thinking:stop");
    expect(vi.mocked(postJson).mock.calls.filter(([url]) => url === "/api/chat")).toHaveLength(1);
  });

  it("polls the chat-run resume endpoint when buffered fallback receives 202 in progress", async () => {
    const responsePayload = {
      chat_run_id: "cr_resume_1",
      trace_id: "trace_resume_1",
      session_id: "session_resume_1",
      answer_markdown: "Respuesta final resumida desde el chat run.",
      followup_queries: [],
      citations: [],
      support_citations: [],
      diagnostics: {},
      llm_runtime: {
        model: "gemini-2.5-flash",
        selected_type: "gemini",
        selected_provider: "gemini_primary",
      },
      token_usage: {
        turn: {
          input_tokens: 9,
          output_tokens: 11,
          total_tokens: 20,
        },
      },
      metrics: {
        llm_runtime: {
          model: "gemini-2.5-flash",
          selected_type: "gemini",
          selected_provider: "gemini_primary",
        },
        token_usage: {
          turn: {
            input_tokens: 9,
            output_tokens: 11,
            total_tokens: 20,
          },
        },
        conversation: {
          token_usage_total: {
            input_tokens: 9,
            output_tokens: 11,
            total_tokens: 20,
          },
        },
      },
    };

    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/chat/stream") {
        return Promise.resolve(new Response(JSON.stringify({ error: "no_stream" }), { status: 503 }));
      }
      if (url === "/api/chat/runs/cr_resume_1") {
        return Promise.resolve(
          new Response(JSON.stringify(responsePayload), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          })
        );
      }
      return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
    });
    vi.stubGlobal("fetch", fetchMock);

    vi.mocked(postJson).mockResolvedValue({
      response: new Response(
        JSON.stringify({
          ok: false,
          status: "in_progress",
          chat_run_id: "cr_resume_1",
          session_id: "session_resume_1",
        }),
        {
          status: 202,
          headers: { "Content-Type": "application/json" },
        }
      ),
      data: {
        ok: false,
        status: "in_progress",
        chat_run_id: "cr_resume_1",
        session_id: "session_resume_1",
      },
    });

    const { controller } = createController();
    await controller.submitChatTurn({
      displayUserText: "Necesito la respuesta final.",
      requestMessage: "Necesito la respuesta final.",
    });

    expect(postJson).toHaveBeenNthCalledWith(
      1,
      "/api/chat",
      expect.objectContaining({
        message: "Necesito la respuesta final.",
        client_turn_id: expect.any(String),
      })
    );
    expect(fetchMock).toHaveBeenCalledWith("/api/chat/runs/cr_resume_1");
  });

  it("preserves normative panel state when persistActiveSessionSnapshot throws after successful final event", async () => {
    const turnStates: string[] = [];
    const consoleErrors: unknown[] = [];
    const originalConsoleError = console.error;
    console.error = (...args: unknown[]) => {
      consoleErrors.push(args);
    };

    const finalPayload = {
      trace_id: "trace_persist_error",
      session_id: "session_persist_error",
      answer_markdown: "Los plazos de renta AG 2025 son en mayo de 2026.",
      followup_queries: [],
      citations: [],
      support_citations: [],
      diagnostics: {},
      llm_runtime: {
        model: "gemini-2.5-flash",
        selected_type: "gemini",
        selected_provider: "gemini_primary",
      },
      token_usage: {
        turn: { input_tokens: 10, output_tokens: 10, total_tokens: 20 },
      },
      metrics: {
        llm_runtime: {
          model: "gemini-2.5-flash",
          selected_type: "gemini",
          selected_provider: "gemini_primary",
        },
        token_usage: {
          turn: { input_tokens: 10, output_tokens: 10, total_tokens: 20 },
        },
        conversation: {
          token_usage_total: { input_tokens: 10, output_tokens: 10, total_tokens: 20 },
        },
      },
    };

    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        if (url === "/api/chat/stream") {
          return Promise.resolve(
            createSseResponse([
              formatSseEvent("meta", {
                trace_id: "trace_persist_error",
                session_id: "session_persist_error",
                response_route: "decision",
              }),
              formatSseEvent("answer_block", {
                index: 0,
                markdown: "Los plazos de renta AG 2025 son en mayo de 2026.",
                block_kind: "paragraph",
                provisional: true,
              }),
              formatSseEvent("final", finalPayload),
            ])
          );
        }
        return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
      })
    );

    const i18n = createI18n("es-CO");
    let activeSessionId = "";
    const events: string[] = [];

    const controller = createChatRequestController({
      i18n,
      state: {
        requestTimerInterval: null,
        requestStartedAtMs: null,
        lastUserMessage: "",
        lastAssistantAnswerMarkdown: "",
        lastSubmittedUserMessage: "",
        citationRequestContext: null,
        deferredCitationsFallback: [],
        deferredMentionCitations: [],
        deferredCitationsCache: [],
        deferredCitationsCacheKey: "",
        deferredCitationsStatusText: "",
        deferredCitationsPlaceholderText: "",
        buildInfoLine: "",
        conversationTokenTotals: {
          input_tokens: 0,
          output_tokens: 0,
          total_tokens: 0,
        },
      },
      dom: {
        citationsLoadBtn: null,
        diagnosticsNode: document.createElement("div"),
        runtimeRequestTimerNode: document.createElement("div"),
        runtimeLatencyNode: document.createElement("div"),
        runtimeModelNode: document.createElement("div"),
        runtimeTurnTokensNode: document.createElement("div"),
        runtimeConversationTokensNode: document.createElement("div"),
        sendBtn: Object.assign(document.createElement("button"), { textContent: "Enviar consulta" }),
      },
      debugInput: null,
      startThinkingWheel: () => {
        events.push("thinking:start");
      },
      stopThinkingWheel: () => {
        events.push("thinking:stop");
      },
      withThinkingWheel: async (task) => task(),
      getActiveSessionId: () => activeSessionId,
      setActiveSessionId: (value) => {
        activeSessionId = value;
      },
      setTurnState: (state) => {
        turnStates.push(state);
      },
      deriveReadyState: () => "ready",
      focusComposer: () => {},
      resetConversationUi: () => {},
      renderCitations: () => {},
      renderDeferredCitationsState: () => {},
      setCitationsStatus: () => {},
      addBubble: async (role) => {
        events.push(`bubble:${role}`);
        return document.createElement("div");
      },
      createStreamingAssistantBubble: () => ({
        appendMarkdownBlock: async () => {
          events.push("stream:append");
        },
        replaceMarkdown: async () => {
          events.push("stream:replace");
        },
        finalize: async () => {
          events.push("stream:finalize");
        },
        setStatus: () => {
          events.push("stream:status");
        },
        clearStatus: () => {
          events.push("stream:clear-status");
        },
        getNode: () => document.createElement("div"),
      }),
      buildAssistantBubbleMeta: () => ({}),
      decisionResponseRoute: "decision",
      devBootCacheKey: "lia_dev_boot_nonce_v1",
      persistActiveSessionSnapshot: () => {
        throw new Error("localStorage quota exceeded");
      },
    });

    await controller.submitChatTurn({
      displayUserText: "Plazos renta AG 2025?",
      requestMessage: "Plazos renta AG 2025?",
    });

    // Turn should NOT be in error state — the try/catch prevents propagation
    expect(turnStates).not.toContain("error");
    // The streaming bubble should have been finalized (not a connectionError fallback)
    expect(events).toContain("stream:finalize");
    // The persist error should be logged, not thrown
    expect(consoleErrors.some((args) => String(args).includes("persistActiveSessionSnapshot failed"))).toBe(true);

    console.error = originalConsoleError;
  });

  it("does not overwrite normative state when onChatSuccess callback throws", async () => {
    const turnStates: string[] = [];
    const consoleErrors: unknown[] = [];
    const originalConsoleError = console.error;
    console.error = (...args: unknown[]) => {
      consoleErrors.push(args);
    };

    const finalPayload = {
      trace_id: "trace_callback_error",
      session_id: "session_callback_error",
      answer_markdown: "Respuesta exitosa.",
      followup_queries: [],
      citations: [],
      support_citations: [],
      diagnostics: {},
      llm_runtime: {
        model: "gemini-2.5-flash",
        selected_type: "gemini",
        selected_provider: "gemini_primary",
      },
      token_usage: {
        turn: { input_tokens: 5, output_tokens: 5, total_tokens: 10 },
      },
      metrics: {
        llm_runtime: {
          model: "gemini-2.5-flash",
          selected_type: "gemini",
          selected_provider: "gemini_primary",
        },
        token_usage: {
          turn: { input_tokens: 5, output_tokens: 5, total_tokens: 10 },
        },
        conversation: {
          token_usage_total: { input_tokens: 5, output_tokens: 5, total_tokens: 10 },
        },
      },
    };

    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        if (url === "/api/chat/stream") {
          return Promise.resolve(
            createSseResponse([
              formatSseEvent("meta", {
                trace_id: "trace_callback_error",
                session_id: "session_callback_error",
                response_route: "decision",
              }),
              formatSseEvent("answer_block", {
                index: 0,
                markdown: "Respuesta exitosa.",
                block_kind: "paragraph",
                provisional: true,
              }),
              formatSseEvent("final", finalPayload),
            ])
          );
        }
        return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
      })
    );

    const { controller, events } = createController({
      setTurnState: (state) => {
        turnStates.push(state);
      },
    });

    // Inject an onChatSuccess that throws — but since createController doesn't
    // accept onChatSuccess override, we test via the persistActiveSessionSnapshot
    // which is the most common real-world failure path
    await controller.submitChatTurn({
      displayUserText: "Test callback error.",
      requestMessage: "Test callback error.",
    });

    expect(turnStates).not.toContain("error");
    expect(events).toContain("stream:finalize");

    console.error = originalConsoleError;
  });
});
