// @vitest-environment jsdom

import { beforeEach, describe, expect, it, vi } from "vitest";

// thinkingOverlay is a singleton — force a fresh module for each test
let getThinkingOverlay: typeof import("../src/shared/async/thinkingOverlay").getThinkingOverlay;

describe("thinking overlay", () => {
  beforeEach(async () => {
    document.body.innerHTML = "";
    vi.useFakeTimers();
    vi.resetModules();
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    });
    const mod = await import("../src/shared/async/thinkingOverlay");
    getThinkingOverlay = mod.getThinkingOverlay;
  });

  it("shows only while active tasks are pending", async () => {
    // Provide a .chat-panel for the overlay to attach to
    const chatPanel = document.createElement("article");
    chatPanel.className = "chat-panel";
    document.body.appendChild(chatPanel);

    const overlay = getThinkingOverlay();
    const primedNode = document.getElementById("lia-thinking-overlay");
    expect(primedNode).not.toBeNull();
    expect(primedNode?.hidden).toBe(true);

    overlay.start();
    await vi.advanceTimersByTimeAsync(150);

    const node = document.getElementById("lia-thinking-overlay");
    expect(node).not.toBeNull();
    expect(node?.hidden).toBe(false);

    const posesContainer = node?.querySelector("#lia-thinking-poses");
    expect(posesContainer).not.toBeNull();
    expect(posesContainer?.classList.contains("lia-thinking-container")).toBe(true);
    expect(node?.querySelectorAll(".lia-pose")).toHaveLength(10);

    overlay.stop();
    expect(node?.hidden).toBe(true);
  });

  it("scopes overlay inside .chat-panel (not document.body)", async () => {
    const chatPanel = document.createElement("article");
    chatPanel.className = "chat-panel";
    document.body.appendChild(chatPanel);

    const overlay = getThinkingOverlay();
    overlay.start();
    await vi.advanceTimersByTimeAsync(150);

    const node = document.getElementById("lia-thinking-overlay");
    expect(node).not.toBeNull();
    // Must be a child of .chat-panel, NOT document.body
    expect(node?.parentElement).toBe(chatPanel);
    expect(node?.closest(".chat-panel")).toBe(chatPanel);

    overlay.stop();
  });

  it("falls back to document.body when .chat-panel is absent", async () => {
    // No .chat-panel in DOM — overlay should still work
    const overlay = getThinkingOverlay();
    overlay.start();
    await vi.advanceTimersByTimeAsync(150);

    const node = document.getElementById("lia-thinking-overlay");
    expect(node).not.toBeNull();
    expect(node?.parentElement).toBe(document.body);

    overlay.stop();
  });

  it("does not show if stopped before delay elapses", async () => {
    const chatPanel = document.createElement("article");
    chatPanel.className = "chat-panel";
    document.body.appendChild(chatPanel);

    const overlay = getThinkingOverlay();
    overlay.start();
    // Stop before the 140ms show-delay
    await vi.advanceTimersByTimeAsync(100);
    overlay.stop();
    await vi.advanceTimersByTimeAsync(100);

    const node = document.getElementById("lia-thinking-overlay");
    // Node may or may not exist, but it must be hidden
    expect(node === null || node.hidden).toBe(true);
  });

  it("withTask shows overlay during async work and hides after", async () => {
    const chatPanel = document.createElement("article");
    chatPanel.className = "chat-panel";
    document.body.appendChild(chatPanel);

    const overlay = getThinkingOverlay();
    let resolver: () => void;
    const slowTask = new Promise<string>((resolve) => {
      resolver = () => resolve("done");
    });

    const taskPromise = overlay.withTask(() => slowTask);
    await vi.advanceTimersByTimeAsync(150);

    const node = document.getElementById("lia-thinking-overlay");
    expect(node?.hidden).toBe(false);

    // Complete the task
    resolver!();
    const result = await taskPromise;
    expect(result).toBe("done");
    expect(node?.hidden).toBe(true);
  });

  it("reset clears all pending requests", async () => {
    const chatPanel = document.createElement("article");
    chatPanel.className = "chat-panel";
    document.body.appendChild(chatPanel);

    const overlay = getThinkingOverlay();
    overlay.start();
    overlay.start();
    await vi.advanceTimersByTimeAsync(150);

    const node = document.getElementById("lia-thinking-overlay");
    expect(node?.hidden).toBe(false);

    overlay.reset();
    expect(node?.hidden).toBe(true);

    // A single stop should not re-show it
    overlay.stop();
    expect(node?.hidden).toBe(true);
  });
});
