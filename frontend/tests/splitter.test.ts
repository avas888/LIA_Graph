import { beforeEach, describe, expect, it, vi } from "vitest";

// Shared store accessible from tests
const mockStore = new Map<string, string>();

vi.mock("@/shared/browser/storage", () => ({
  getLocalStorage: () => ({
    getItem: (k: string) => mockStore.get(k) ?? null,
    setItem: (k: string, v: string) => mockStore.set(k, v),
    removeItem: (k: string) => mockStore.delete(k),
    clear: () => mockStore.clear(),
  }),
  getSessionStorage: () => ({
    getItem: () => null,
    setItem: () => {},
    removeItem: () => {},
    clear: () => {},
  }),
  readStorageValue: (_s: unknown, k: string) => mockStore.get(k) ?? null,
}));

import { initSplitter } from "@/features/chat/splitter";

function createLayout(): { layout: HTMLElement; splitter: HTMLElement } {
  const layout = document.createElement("div");
  Object.defineProperty(layout, "clientWidth", { value: 1200, configurable: true });
  const origGetCS = window.getComputedStyle;
  vi.spyOn(window, "getComputedStyle").mockImplementation((el) => {
    if (el === layout) {
      return { columnGap: "16" } as unknown as CSSStyleDeclaration;
    }
    return origGetCS(el);
  });

  const chatPanel = document.createElement("div");
  chatPanel.className = "chat-panel";
  Object.defineProperty(chatPanel, "offsetWidth", { value: 600, configurable: true });
  layout.appendChild(chatPanel);

  const splitter = document.createElement("div");
  Object.defineProperty(splitter, "offsetWidth", { value: 6, configurable: true });
  splitter.setPointerCapture = vi.fn();
  splitter.releasePointerCapture = vi.fn();

  return { layout, splitter };
}

describe("initSplitter", () => {
  beforeEach(() => {
    mockStore.clear();
  });

  it("initializes without errors", () => {
    const { layout, splitter } = createLayout();
    expect(() => initSplitter(layout, splitter)).not.toThrow();
  });

  it("applies saved split on init", () => {
    mockStore.set("lia_chat_splitter_v4", "700");
    const { layout, splitter } = createLayout();
    initSplitter(layout, splitter);
    expect(layout.style.gridTemplateColumns).toContain("700px");
  });

  it("handles pointer drag to resize", () => {
    const { layout, splitter } = createLayout();
    initSplitter(layout, splitter);

    splitter.dispatchEvent(
      new PointerEvent("pointerdown", { button: 0, clientX: 600, pointerId: 1 } as PointerEventInit),
    );
    expect(splitter.classList.contains("is-dragging")).toBe(true);

    splitter.dispatchEvent(
      new PointerEvent("pointermove", { clientX: 650, pointerId: 1 } as PointerEventInit),
    );
    expect(layout.style.gridTemplateColumns).toContain("px");

    splitter.dispatchEvent(new PointerEvent("pointerup", { pointerId: 1 } as PointerEventInit));
    expect(splitter.classList.contains("is-dragging")).toBe(false);
  });

  it("ignores non-primary button", () => {
    const { layout, splitter } = createLayout();
    initSplitter(layout, splitter);

    splitter.dispatchEvent(
      new PointerEvent("pointerdown", { button: 2, clientX: 600, pointerId: 1 } as PointerEventInit),
    );
    expect(splitter.classList.contains("is-dragging")).toBe(false);
  });

  it("resets split on double-click", () => {
    const { layout, splitter } = createLayout();
    initSplitter(layout, splitter);

    layout.style.gridTemplateColumns = "500px 6px minmax(0, 1fr)";
    splitter.dispatchEvent(new MouseEvent("dblclick"));
    expect(layout.style.gridTemplateColumns).toBe("");
  });

  it("handles keyboard arrows", () => {
    const { layout, splitter } = createLayout();
    initSplitter(layout, splitter);

    splitter.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight" }));
    expect(layout.style.gridTemplateColumns).toContain("px");
  });

  it("handles Home key to reset", () => {
    const { layout, splitter } = createLayout();
    initSplitter(layout, splitter);

    layout.style.gridTemplateColumns = "500px 6px minmax(0, 1fr)";
    splitter.dispatchEvent(new KeyboardEvent("keydown", { key: "Home" }));
    expect(layout.style.gridTemplateColumns).toBe("");
  });
});
