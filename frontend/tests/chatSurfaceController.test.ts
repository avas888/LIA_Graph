// @vitest-environment jsdom

import { beforeEach, describe, expect, it } from "vitest";

import { createChatSurfaceController } from "../src/features/chat/chatSurfaceController";

function buildController() {
  document.body.innerHTML = `
    <main>
      <section id="root">
        <div id="chat-log"></div>
        <section id="chat-log-empty"></section>
        <textarea id="message"></textarea>
        <button id="send-btn" type="button"></button>
        <button id="reset-conversation-btn" type="button"></button>
        <button id="new-thread-btn" type="button"></button>
        <div id="session-state-badge"></div>
        <div id="session-id-badge"></div>
      </section>
    </main>
  `;

  return createChatSurfaceController({
    i18n: { t: (key: string) => key } as any,
    state: { activeSessionId: "" },
    root: document.querySelector<HTMLElement>("#root")!,
    chatLog: document.querySelector<HTMLElement>("#chat-log")!,
    chatLogEmptyNode: document.querySelector<HTMLElement>("#chat-log-empty")!,
    messageInput: document.querySelector<HTMLTextAreaElement>("#message")!,
    sendBtn: document.querySelector<HTMLButtonElement>("#send-btn")!,
    resetConversationBtn: document.querySelector<HTMLButtonElement>("#reset-conversation-btn")!,
    newThreadBtn: document.querySelector<HTMLButtonElement>("#new-thread-btn")!,
    sessionStateBadgeNode: document.querySelector<HTMLElement>("#session-state-badge"),
    sessionIdBadgeNode: document.querySelector<HTMLElement>("#session-id-badge"),
    debugInput: null,
    debugSummaryNode: null,
  });
}

describe("chat surface controller URL handoff", () => {
  beforeEach(() => {
    window.history.replaceState({}, "", "/public");
    document.body.innerHTML = "";
  });

  it("consumes `prefill` without auto-submitting", () => {
    window.history.replaceState({}, "", "/public?prefill=Consulta%20de%20prueba");
    const controller = buildController();

    const result = controller.consumeComposerPrefillFromUrl();

    expect(result).toEqual({
      text: "Consulta de prueba",
      shouldSubmit: false,
      source: "prefill",
    });
    expect(document.querySelector<HTMLTextAreaElement>("#message")?.value).toBe("Consulta de prueba");
    expect(window.location.search).toBe("");
  });

  it("treats `message` as an immediate-send handoff", () => {
    window.history.replaceState({}, "", "/public?message=Saldo%20a%20favor");
    const controller = buildController();

    const result = controller.consumeComposerPrefillFromUrl();

    expect(result).toEqual({
      text: "Saldo a favor",
      shouldSubmit: true,
      source: "message",
    });
    expect(document.querySelector<HTMLTextAreaElement>("#message")?.value).toBe("Saldo a favor");
    expect(window.location.search).toBe("");
  });

  it("honors explicit auto_send for prefill links", () => {
    window.history.replaceState({}, "", "/public?prefill=RUB&auto_send=true");
    const controller = buildController();

    const result = controller.consumeComposerPrefillFromUrl();

    expect(result?.shouldSubmit).toBe(true);
    expect(result?.source).toBe("prefill");
    expect(window.location.search).toBe("");
  });
});
