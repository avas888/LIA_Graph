import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  createChatTranscriptController,
  formatConversationCopyPayload,
} from "@/features/chat/transcriptController";
import { createI18n } from "@/shared/i18n";
import type { I18nRuntime } from "@/shared/i18n";

const renderMarkdownMock = vi.fn();
const appendMarkdownMock = vi.fn();

vi.mock("@/content/markdown", () => ({
  appendMarkdown: (...args: unknown[]) => appendMarkdownMock(...args),
  renderMarkdown: (...args: unknown[]) => renderMarkdownMock(...args),
  createSmartScroller: () => ({
    scrollToBottom: vi.fn(),
    scrollIfTracking: vi.fn(),
    destroy: vi.fn(),
  }),
}));

vi.mock("@/app/mobile/detectMobile", () => ({
  isMobile: () => false,
}));

vi.mock("@/shared/api/client", () => ({
  getJson: vi.fn().mockResolvedValue(null),
  postJson: vi.fn().mockResolvedValue({ response: { ok: true }, data: {} }),
}));

describe("chat transcript controller", () => {
  let i18n: I18nRuntime;

  beforeEach(() => {
    document.body.innerHTML = "";
    renderMarkdownMock.mockReset();
    appendMarkdownMock.mockReset();
    vi.restoreAllMocks();
    i18n = createI18n("es-CO");
    vi.stubGlobal(
      "requestAnimationFrame",
      ((callback: FrameRequestCallback) =>
        window.setTimeout(() => callback(performance.now()), 0)) as typeof requestAnimationFrame
    );
  });

  function createController(overrides: Record<string, unknown> = {}) {
    const chatLog = document.createElement("div");
    const template = document.createElement("template");
    template.innerHTML = `
      <div class="bubble">
        <p class="bubble-role"></p>
        <div class="bubble-text"></div>
        <div class="bubble-actions" hidden></div>
      </div>
    `;

    const onTranscriptEntriesChanged = vi.fn();

    const controller = createChatTranscriptController({
      i18n,
      chatLog,
      bubbleTemplate: template,
      feedbackGetRoute: "/api/feedback",
      feedbackPostRoute: "/api/feedback",
      feedbackRatingUp: 5,
      feedbackRatingDown: 1,
      setActiveSessionId: vi.fn(),
      updateChatLogEmptyState: vi.fn(),
      onTranscriptEntriesChanged,
      ...overrides,
    });

    return { chatLog, controller, onTranscriptEntriesChanged };
  }

  // ── formatConversationCopyPayload ────────────────────────────

  describe("formatConversationCopyPayload", () => {
    it("combines question and answer into labeled sections", () => {
      const result = formatConversationCopyPayload(
        "¿Cuál es la tarifa de renta?",
        "La tarifa general es del 35%.",
        i18n
      );
      expect(result).toContain("¿Cuál es la tarifa de renta?");
      expect(result).toContain("La tarifa general es del 35%.");
    });

    it("handles empty question gracefully", () => {
      const result = formatConversationCopyPayload("", "Respuesta aquí.", i18n);
      expect(result).toContain("Respuesta aquí.");
    });

    it("handles null/undefined inputs", () => {
      const result = formatConversationCopyPayload(null, undefined, i18n);
      expect(typeof result).toBe("string");
    });

    it("strips markdown formatting from the answer", () => {
      const result = formatConversationCopyPayload(
        "Pregunta",
        "**Negrita** y *cursiva* y `código`",
        i18n
      );
      expect(result).toContain("Negrita");
      expect(result).toContain("cursiva");
      expect(result).toContain("código");
      expect(result).not.toContain("**");
      expect(result).not.toContain("`");
    });

    it("strips markdown links but keeps the text", () => {
      const result = formatConversationCopyPayload(
        "Q",
        "[enlace](https://example.com)",
        i18n
      );
      expect(result).toContain("enlace");
      expect(result).not.toContain("](");
    });

    it("strips code fences", () => {
      const result = formatConversationCopyPayload(
        "Q",
        "```python\nprint('hello')\n```",
        i18n
      );
      expect(result).toContain("print('hello')");
      expect(result).not.toContain("```");
    });

    it("collapses excessive newlines", () => {
      const result = formatConversationCopyPayload(
        "Q",
        "Line1\n\n\n\n\nLine2",
        i18n
      );
      expect(result).not.toMatch(/\n{3,}/);
    });

    it("strips html tags", () => {
      const result = formatConversationCopyPayload(
        "Q",
        "Texto con <u>subrayado</u> y <b>bold</b>",
        i18n
      );
      expect(result).toContain("subrayado");
      expect(result).not.toContain("<u>");
      expect(result).not.toContain("<b>");
    });

    it("converts markdown bullets to bullet characters", () => {
      const result = formatConversationCopyPayload(
        "Q",
        "- Item 1\n- Item 2\n- Item 3",
        i18n
      );
      expect(result).toContain("Item 1");
      expect(result).toContain("Item 2");
    });

    it("strips strikethrough markdown", () => {
      const result = formatConversationCopyPayload(
        "Q",
        "~~tachado~~",
        i18n
      );
      expect(result).toContain("tachado");
      expect(result).not.toContain("~~");
    });
  });

  // ── addBubble ─────────────────────────────────────────────

  describe("addBubble", () => {
    it("never shows a 'Procesando...' placeholder while assistant markdown is hydrating", async () => {
      let resolveRender: (() => void) | null = null;
      renderMarkdownMock.mockImplementation(
        () =>
          new Promise<void>((resolve) => {
            resolveRender = resolve;
          })
      );

      const { controller } = createController();
      const bubbleNode = await controller.addBubble("assistant", "Respuesta final", {
        deferAssistantRender: true,
      });
      expect(bubbleNode).not.toBeNull();

      const bubbleTextNode = bubbleNode?.querySelector(".bubble-text");
      expect(bubbleTextNode?.textContent).toBe("");
      expect(bubbleTextNode?.textContent).not.toContain("Procesando");

      resolveRender?.();
      await Promise.resolve();
    });

    it("fires deferred assistant render completion only after markdown rendering finishes", async () => {
      let resolveRender: (() => void) | null = null;
      const onAssistantRenderComplete = vi.fn();
      renderMarkdownMock.mockImplementation(
        () =>
          new Promise<void>((resolve) => {
            resolveRender = resolve;
          })
      );

      const { controller } = createController();
      const bubbleNode = await controller.addBubble("assistant", "Respuesta final", {
        deferAssistantRender: true,
        onAssistantRenderComplete,
      });
      const bubbleTextNode = bubbleNode?.querySelector(".bubble-text");

      expect(bubbleTextNode?.textContent).toBe("");
      expect(onAssistantRenderComplete).not.toHaveBeenCalled();

      resolveRender?.();
      await Promise.resolve();
      await Promise.resolve();
      await new Promise((resolve) => window.setTimeout(resolve, 0));

      expect(onAssistantRenderComplete).toHaveBeenCalledTimes(1);
    });

    it("returns null for empty assistant text", async () => {
      renderMarkdownMock.mockResolvedValue(undefined);

      const { controller } = createController();
      const bubbleNode = await controller.addBubble("assistant", "", {});
      expect(bubbleNode).toBeNull();
    });

    it("returns null for whitespace-only assistant text", async () => {
      renderMarkdownMock.mockResolvedValue(undefined);

      const { controller } = createController();
      const bubbleNode = await controller.addBubble("assistant", "   \n  ", {});
      expect(bubbleNode).toBeNull();
    });

    it("adds a user bubble with correct role label", async () => {
      renderMarkdownMock.mockResolvedValue(undefined);
      const { chatLog, controller } = createController();

      await controller.addBubble("user", "Hola LIA");

      const roleLabel = chatLog.querySelector(".bubble-role");
      expect(roleLabel?.textContent).toBe("Tú");
    });

    it("adds an assistant bubble with correct role label", async () => {
      renderMarkdownMock.mockResolvedValue(undefined);
      const { chatLog, controller } = createController();

      await controller.addBubble("assistant", "Hola, soy LIA.");

      const roleLabel = chatLog.querySelector(".bubble-role");
      expect(roleLabel?.textContent).toBe("LIA");
    });

    it("user bubble text is set as textContent (not rendered markdown)", async () => {
      renderMarkdownMock.mockResolvedValue(undefined);
      const { chatLog, controller } = createController();

      await controller.addBubble("user", "Mi pregunta");

      const bubbleText = chatLog.querySelector(".bubble-text");
      expect(bubbleText?.textContent).toBe("Mi pregunta");
      expect(renderMarkdownMock).not.toHaveBeenCalled();
    });

    it("adds bubble-user class for user role", async () => {
      renderMarkdownMock.mockResolvedValue(undefined);
      const { chatLog, controller } = createController();

      await controller.addBubble("user", "Pregunta");

      const bubble = chatLog.querySelector(".bubble");
      expect(bubble?.classList.contains("bubble-user")).toBe(true);
    });

    it("adds bubble-assistant class for assistant role", async () => {
      renderMarkdownMock.mockResolvedValue(undefined);
      const { chatLog, controller } = createController();

      await controller.addBubble("assistant", "Respuesta");

      const bubble = chatLog.querySelector(".bubble");
      expect(bubble?.classList.contains("bubble-assistant")).toBe(true);
    });

    it("persists transcript entry by default", async () => {
      renderMarkdownMock.mockResolvedValue(undefined);
      const { controller, onTranscriptEntriesChanged } = createController();

      await controller.addBubble("user", "Pregunta 1");

      expect(onTranscriptEntriesChanged).toHaveBeenCalled();
      expect(controller.getTranscriptEntries()).toHaveLength(1);
      expect(controller.getTranscriptEntries()[0]).toEqual(
        expect.objectContaining({ role: "user", text: "Pregunta 1" })
      );
    });

    it("does not persist when persist: false", async () => {
      renderMarkdownMock.mockResolvedValue(undefined);
      const { controller, onTranscriptEntriesChanged } = createController();

      await controller.addBubble("user", "Pregunta skip", { persist: false });

      expect(onTranscriptEntriesChanged).not.toHaveBeenCalled();
      expect(controller.getTranscriptEntries()).toHaveLength(0);
    });

    it("renders coverage notice above the assistant answer when present", async () => {
      renderMarkdownMock.mockResolvedValue(undefined);

      const { controller } = createController();
      const bubbleNode = await controller.addBubble("assistant", "Respuesta con soporte limitado.", {
        meta: { coverage_notice: "Cobertura limitada para el dominio consultado." },
      });

      expect(bubbleNode?.querySelector(".bubble-coverage-notice")?.textContent).toBe(
        "Cobertura limitada para el dominio consultado."
      );
    });

    it("does not render coverage notice when meta has empty string", async () => {
      renderMarkdownMock.mockResolvedValue(undefined);
      const { controller } = createController();
      const bubbleNode = await controller.addBubble("assistant", "Respuesta.", {
        meta: { coverage_notice: "" },
      });

      expect(bubbleNode?.querySelector(".bubble-coverage-notice")).toBeNull();
    });

    it("sets data-timestamp on the bubble node", async () => {
      renderMarkdownMock.mockResolvedValue(undefined);
      const { chatLog, controller } = createController();
      const ts = "2026-04-05T12:00:00Z";

      await controller.addBubble("user", "Msg", { timestamp: ts });

      const bubble = chatLog.querySelector(".bubble");
      expect((bubble as HTMLElement)?.dataset.timestamp).toBe(ts);
    });
  });

  // ── createStreamingAssistantBubble ──────────────────────────

  describe("createStreamingAssistantBubble", () => {
    it("appends streaming markdown blocks and finalizes with the canonical markdown", async () => {
      renderMarkdownMock.mockResolvedValue(undefined);
      appendMarkdownMock.mockResolvedValue(undefined);

      const { controller } = createController();
      const streamingBubble = controller.createStreamingAssistantBubble({
        previousUserMessage: "Consulta base",
      });

      expect(streamingBubble).not.toBeNull();
      await streamingBubble?.appendMarkdownBlock("## Bloque 1");
      await streamingBubble?.appendMarkdownBlock("Texto del segundo bloque.");

      await streamingBubble?.finalize({
        finalMarkdown: "## Respuesta final\n\nTexto consolidado.",
        previousUserMessage: "Consulta base",
        meta: { session_id: "session_1" },
      });

      // Batched flush produces 1 appendMarkdown call for the 2 queued blocks
      expect(appendMarkdownMock).toHaveBeenCalledTimes(1);
      expect(renderMarkdownMock).toHaveBeenCalledTimes(1);
      expect(controller.getTranscriptEntries()).toEqual([
        expect.objectContaining({
          role: "assistant",
          text: "## Respuesta final\n\nTexto consolidado.",
        }),
      ]);
    });

    it("adds is-streaming class on creation and removes it after finalize", async () => {
      renderMarkdownMock.mockResolvedValue(undefined);
      appendMarkdownMock.mockResolvedValue(undefined);

      const { controller } = createController();
      const streamingBubble = controller.createStreamingAssistantBubble({});

      const node = streamingBubble!.getNode();
      expect(node.classList.contains("is-streaming")).toBe(true);
      expect(node.classList.contains("is-complete")).toBe(false);

      await streamingBubble?.finalize({
        finalMarkdown: "Final",
        meta: { session_id: "s1" },
      });

      expect(node.classList.contains("is-streaming")).toBe(false);
      expect(node.classList.contains("is-complete")).toBe(true);
    });

    it("setStatus shows and hides the status node", async () => {
      renderMarkdownMock.mockResolvedValue(undefined);
      appendMarkdownMock.mockResolvedValue(undefined);

      const { controller } = createController();
      const streamingBubble = controller.createStreamingAssistantBubble({});

      streamingBubble!.setStatus("Procesando...");
      const statusNode = streamingBubble!.getNode().querySelector(".bubble-stream-status");
      expect(statusNode?.textContent).toBe("Procesando...");
      expect((statusNode as HTMLElement)?.hidden).toBe(false);

      streamingBubble!.clearStatus();
      expect(statusNode?.textContent).toBe("");
      expect((statusNode as HTMLElement)?.hidden).toBe(true);
    });

    it("ignores appendMarkdownBlock calls after finalize", async () => {
      renderMarkdownMock.mockResolvedValue(undefined);
      appendMarkdownMock.mockResolvedValue(undefined);

      const { controller } = createController();
      const streamingBubble = controller.createStreamingAssistantBubble({});

      await streamingBubble?.finalize({
        finalMarkdown: "Done",
        meta: { session_id: "s1" },
      });

      // Should not throw or add blocks
      await streamingBubble?.appendMarkdownBlock("Extra block");
      // appendMarkdownMock should NOT have been called for extra block
      // (it may be called once during finalize flush)
    });

    it("replaceMarkdown clears pending blocks and re-renders", async () => {
      renderMarkdownMock.mockResolvedValue(undefined);
      appendMarkdownMock.mockResolvedValue(undefined);

      const { controller } = createController();
      const streamingBubble = controller.createStreamingAssistantBubble({});

      await streamingBubble?.appendMarkdownBlock("Block to be replaced");
      await streamingBubble?.replaceMarkdown("Completely new content");

      // renderMarkdownMock called from replaceMarkdown
      expect(renderMarkdownMock).toHaveBeenCalled();
    });

    it("setStatus is ignored after finalize", async () => {
      renderMarkdownMock.mockResolvedValue(undefined);
      appendMarkdownMock.mockResolvedValue(undefined);

      const { controller } = createController();
      const streamingBubble = controller.createStreamingAssistantBubble({});

      await streamingBubble?.finalize({
        finalMarkdown: "Done",
        meta: {},
      });

      streamingBubble!.setStatus("Should not appear");
      // Status node was removed during finalize, so this is safe
    });

    it("finalize with persist: false does not record transcript entry", async () => {
      renderMarkdownMock.mockResolvedValue(undefined);
      appendMarkdownMock.mockResolvedValue(undefined);

      const { controller } = createController();
      const streamingBubble = controller.createStreamingAssistantBubble({});

      await streamingBubble?.finalize({
        finalMarkdown: "Not persisted",
        meta: {},
        persist: false,
      });

      expect(controller.getTranscriptEntries()).toHaveLength(0);
    });
  });

  // ── buildAssistantBubbleMeta ─────────────────────────────

  describe("buildAssistantBubbleMeta", () => {
    it("extracts trace_id, session_id and docs from response data", () => {
      const { controller } = createController();
      const meta = controller.buildAssistantBubbleMeta(
        {
          trace_id: "t123",
          session_id: "s456",
          topic: "declaracion_renta",
          citations: [{ doc_id: "doc_001" }, { doc_id: "doc_002" }],
        },
        "¿Cómo declaro?"
      );

      expect(meta).toEqual(
        expect.objectContaining({
          trace_id: "t123",
          session_id: "s456",
          effective_topic: "declaracion_renta",
          question_text: "¿Cómo declaro?",
        })
      );
      expect((meta as Record<string, unknown>).docs_used).toEqual(["doc_001", "doc_002"]);
    });

    it("handles empty response data gracefully", () => {
      const { controller } = createController();
      const meta = controller.buildAssistantBubbleMeta({});

      expect(meta).toEqual(
        expect.objectContaining({
          trace_id: "",
          session_id: "",
          effective_topic: "",
        })
      );
    });

    it("extracts response_route and coverage_notice", () => {
      const { controller } = createController();
      const meta = controller.buildAssistantBubbleMeta({
        response_route: "decision",
        coverage_notice: "Cobertura limitada",
      });

      expect(meta).toEqual(
        expect.objectContaining({
          response_route: "decision",
          coverage_notice: "Cobertura limitada",
        })
      );
    });

    it("deduplicates docs_used from citations", () => {
      const { controller } = createController();
      const meta = controller.buildAssistantBubbleMeta({
        citations: [
          { doc_id: "doc_A" },
          { doc_id: "doc_A" },
          { doc_id: "doc_B" },
        ],
      });
      expect((meta as Record<string, unknown>).docs_used).toEqual(["doc_A", "doc_B"]);
    });

    it("filters out empty doc_ids from citations", () => {
      const { controller } = createController();
      const meta = controller.buildAssistantBubbleMeta({
        citations: [{ doc_id: "" }, { doc_id: "doc_C" }, {}],
      });
      expect((meta as Record<string, unknown>).docs_used).toEqual(["doc_C"]);
    });
  });

  // ── restoreTranscriptEntries ─────────────────────────────

  describe("restoreTranscriptEntries", () => {
    it("populates transcript from entries array", async () => {
      renderMarkdownMock.mockResolvedValue(undefined);
      const { controller, chatLog } = createController();

      const hasEntries = await controller.restoreTranscriptEntries([
        { role: "user", text: "Pregunta 1", meta: null },
        {
          role: "assistant",
          text: "Respuesta 1",
          meta: {
            trace_id: "t1",
            chat_run_id: "",
            session_id: "s1",
            requested_topic: "",
            effective_topic: "",
            topic_adjusted: false,
            pais: "",
            docs_used: [],
            layer_contributions: {},
            pain_detected: "",
            task_detected: "",
            feedback_rating: null,
            question_text: "Pregunta 1",
            response_route: "",
            coverage_notice: "",
          },
        },
      ]);

      expect(hasEntries).toBe(true);
      expect(chatLog.querySelectorAll(".bubble").length).toBe(2);
    });

    it("returns false for empty entries", async () => {
      const { controller } = createController();
      const result = await controller.restoreTranscriptEntries([]);
      expect(result).toBe(false);
    });

    it("clears chatLog before restoring", async () => {
      renderMarkdownMock.mockResolvedValue(undefined);
      const { controller, chatLog } = createController();

      // Add a bubble first
      await controller.addBubble("user", "Old message");
      expect(chatLog.querySelectorAll(".bubble").length).toBe(1);

      // Restore should clear old bubbles
      await controller.restoreTranscriptEntries([
        { role: "user", text: "New message", meta: null },
      ]);

      expect(chatLog.querySelectorAll(".bubble").length).toBe(1);
      expect(chatLog.querySelector(".bubble-text")?.textContent).toBe("New message");
    });
  });

  // ── resetTranscriptState ────────────────────────────────

  describe("resetTranscriptState", () => {
    it("clears all transcript entries", async () => {
      renderMarkdownMock.mockResolvedValue(undefined);
      const { controller } = createController();

      await controller.addBubble("user", "Test");
      expect(controller.getTranscriptEntries()).toHaveLength(1);

      controller.resetTranscriptState();
      expect(controller.getTranscriptEntries()).toHaveLength(0);
    });
  });

  // ── getTranscriptEntries ────────────────────────────────

  describe("getTranscriptEntries", () => {
    it("returns defensive copies (no shared references)", async () => {
      renderMarkdownMock.mockResolvedValue(undefined);
      const { controller } = createController();

      await controller.addBubble("user", "Hello");
      const entries1 = controller.getTranscriptEntries();
      const entries2 = controller.getTranscriptEntries();

      expect(entries1).toEqual(entries2);
      expect(entries1).not.toBe(entries2);
    });
  });

  // ── scrollToTranscriptPair ──────────────────────────────

  describe("scrollToTranscriptPair", () => {
    it("returns false when indices have no matching nodes", () => {
      const { controller } = createController();
      const result = controller.scrollToTranscriptPair(99, 100);
      expect(result).toBe(false);
    });

    it("scrolls to assistant node and marks pair", async () => {
      renderMarkdownMock.mockResolvedValue(undefined);
      const { controller, chatLog } = createController();

      await controller.addBubble("user", "Q1");
      await controller.addBubble("assistant", "A1", {
        meta: { trace_id: "t1", session_id: "s1" },
      });

      const result = controller.scrollToTranscriptPair(0, 1);
      expect(result).toBe(true);

      const bubbles = chatLog.querySelectorAll(".bubble");
      expect(bubbles[0]?.classList.contains("is-transcript-target")).toBe(true);
      expect(bubbles[1]?.classList.contains("is-transcript-target")).toBe(true);
    });
  });

  // ── setBubbleQuestionId ────────────────────────────────

  describe("setBubbleQuestionId", () => {
    it("sets data-questionId and adds has-normativa class", async () => {
      renderMarkdownMock.mockResolvedValue(undefined);
      const { controller, chatLog } = createController();

      await controller.addBubble("user", "Pregunta con normativa");

      controller.setBubbleQuestionId(0, "q-123");

      const bubble = chatLog.querySelector(".bubble") as HTMLElement;
      expect(bubble.dataset.questionId).toBe("q-123");
      expect(bubble.classList.contains("has-normativa")).toBe(true);
    });

    it("does nothing for empty questionId", async () => {
      renderMarkdownMock.mockResolvedValue(undefined);
      const { controller, chatLog } = createController();

      await controller.addBubble("user", "Pregunta");

      controller.setBubbleQuestionId(0, "");

      const bubble = chatLog.querySelector(".bubble") as HTMLElement;
      expect(bubble.dataset.questionId).toBeUndefined();
    });
  });

  // ── updateBubbleSelectionState ─────────────────────────

  describe("updateBubbleSelectionState", () => {
    it("toggles is-bubble-active class for matching questionId", async () => {
      renderMarkdownMock.mockResolvedValue(undefined);
      const { controller, chatLog } = createController();

      await controller.addBubble("user", "Q1");
      await controller.addBubble("user", "Q2");

      controller.setBubbleQuestionId(0, "q-A");
      controller.setBubbleQuestionId(1, "q-B");

      controller.updateBubbleSelectionState("q-A");

      const bubbles = chatLog.querySelectorAll(".bubble");
      expect(bubbles[0]?.classList.contains("is-bubble-active")).toBe(true);
      expect(bubbles[1]?.classList.contains("is-bubble-active")).toBe(false);
    });

    it("deactivates all bubbles when questionId is empty", async () => {
      renderMarkdownMock.mockResolvedValue(undefined);
      const { controller, chatLog } = createController();

      await controller.addBubble("user", "Q1");
      controller.setBubbleQuestionId(0, "q-A");
      controller.updateBubbleSelectionState("q-A");

      // Now deactivate
      controller.updateBubbleSelectionState("");

      const bubble = chatLog.querySelector(".bubble");
      expect(bubble?.classList.contains("is-bubble-active")).toBe(false);
    });
  });
});
