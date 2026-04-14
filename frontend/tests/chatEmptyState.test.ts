import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderChatShell } from "@/app/chat/shell";
import { renderBackstageShell } from "@/app/ops/shell";
import { mountChatApp } from "@/features/chat/chatApp";
import { createI18n } from "@/shared/i18n";
import type { I18nRuntime } from "@/shared/i18n";

const CHAT_SESSION_INDEX_KEY = "lia_chat_session_index_v1";
const CHAT_SESSION_STATE_KEY_PREFIX = "lia_chat_session_state_v1:";

function renderFullShell(i18n: I18nRuntime): string {
  return renderBackstageShell(i18n) + renderChatShell(i18n);
}

function mockJsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

async function flushUi(): Promise<void> {
  await Promise.resolve();
  await new Promise((resolve) => window.setTimeout(resolve, 0));
  await Promise.resolve();
}

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

function seedOneStoredSession(): void {
  localStorage.setItem(
    CHAT_SESSION_INDEX_KEY,
    JSON.stringify({
      version: 1,
      activeSessionId: "chat_seeded_1",
      sessions: [{ sessionId: "chat_seeded_1", firstQuestion: "Consulta guardada", updatedAt: "2026-03-13T10:00:00.000Z" }],
    })
  );
  localStorage.setItem(
    `${CHAT_SESSION_STATE_KEY_PREFIX}chat_seeded_1`,
    JSON.stringify({
      version: 1,
      sessionId: "chat_seeded_1",
      firstQuestion: "Consulta guardada",
      updatedAt: "2026-03-13T10:00:00.000Z",
      transcriptEntries: [
        { role: "user", text: "Consulta guardada" },
        { role: "assistant", text: "Respuesta guardada", meta: { session_id: "chat_seeded_1", trace_id: "trace_seeded_1" } },
      ],
      normativeSupport: null,
      conversationTokenTotals: { input_tokens: 0, output_tokens: 0, total_tokens: 0 },
      lastUserMessage: "Consulta guardada",
      lastSubmittedUserMessage: "Consulta guardada",
      lastAssistantAnswerMarkdown: "Respuesta guardada",
    })
  );
}

describe("chat empty state", () => {
  beforeEach(() => {
    const storage = createStorageMock();
    vi.stubGlobal("localStorage", storage);
    Object.defineProperty(window, "localStorage", {
      configurable: true,
      value: storage,
    });
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
        return Promise.resolve(mockJsonResponse({}));
      })
    );
  });

  it("renders the hola ice breaker as the first bubble in the chat log", async () => {
    const i18n = createI18n("es-CO");
    document.body.innerHTML = renderFullShell(i18n);

    mountChatApp(document.body, { i18n });
    await flushUi();

    const chatLog = document.querySelector<HTMLElement>("#chat-log");
    const emptyBubble = document.querySelector<HTMLElement>("#chat-log-empty");

    expect(chatLog).not.toBeNull();
    expect(emptyBubble).not.toBeNull();
    expect(chatLog?.firstElementChild?.id).toBe("chat-log-empty");
    expect(emptyBubble?.hidden).toBe(false);
    expect(emptyBubble?.textContent).toContain("¡Hola! Hazme tu pregunta. Estoy acá para ayudarte...");
  });

  it("hides the session drawer when there are no sessions", async () => {
    const i18n = createI18n("es-CO");
    document.body.innerHTML = renderFullShell(i18n);

    mountChatApp(document.body, { i18n });
    await flushUi();

    expect(document.querySelector<HTMLElement>("#chat-session-drawer")?.hidden).toBe(true);
    expect(document.querySelector("#chat-session-switcher")?.childElementCount).toBe(0);
  });

  it("hides the session drawer for a single stored session", async () => {
    seedOneStoredSession();
    const i18n = createI18n("es-CO");
    document.body.innerHTML = renderFullShell(i18n);

    mountChatApp(document.body, { i18n });
    await flushUi();

    const drawer = document.querySelector<HTMLElement>("#chat-session-drawer");
    const composer = document.querySelector<HTMLElement>("#chat-form");
    const siblings = Array.from(composer?.parentElement?.children || []);

    // Single session → drawer hidden (thread count ≤1)
    expect(drawer?.hidden).toBe(true);
    expect(siblings.indexOf(drawer as Element)).toBeGreaterThan(siblings.indexOf(composer as Element));
  });
});
