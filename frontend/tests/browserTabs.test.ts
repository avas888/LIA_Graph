import { describe, it, expect, beforeEach } from "vitest";
import { clearStorage, createInMemoryStorage, type StorageLike } from "@/shared/browser/storage";
import {
  renderBrowserChrome,
  mountBrowserTabs,
  readStoredBrowserTab,
  storeBrowserTab,
  type BrowserTabId,
} from "@/shared/dom/browserTabs";

let storage: StorageLike;

function setup(activeId: BrowserTabId = "chat") {
  const tabs = [
    { id: "chat" as const, label: "Chat", category: "user" as const },
    { id: "ingestion" as const, label: "Ingesta", category: "admin" as const },
    { id: "backstage" as const, label: "Backstage", category: "admin" as const },
  ];
  const container = document.createElement("div");
  container.innerHTML = renderBrowserChrome(tabs, activeId);
  document.body.appendChild(container);
  return container;
}

function teardown() {
  document.body.innerHTML = "";
  clearStorage(storage);
}

describe("renderBrowserChrome", () => {
  beforeEach(() => {
    storage = createInMemoryStorage();
    teardown();
  });

  it("renders three tab buttons", () => {
    const el = setup();
    const tabs = el.querySelectorAll(".browser-tab");
    expect(tabs).toHaveLength(3);
  });

  it("marks initial active tab", () => {
    const el = setup("ingestion");
    const active = el.querySelector(".browser-tab.is-active");
    expect(active?.getAttribute("data-browser-tab")).toBe("ingestion");
  });

  it("sets aria-selected on initial active tab only", () => {
    const el = setup("backstage");
    const tabs = el.querySelectorAll(".browser-tab");
    const selected = Array.from(tabs).map((t) =>
      t.getAttribute("aria-selected"),
    );
    expect(selected).toEqual(["false", "false", "true"]);
  });

  it("renders one content panel per tab", () => {
    const el = setup();
    expect(el.querySelector("#tab-panel-chat")).toBeTruthy();
    expect(el.querySelector("#tab-panel-ingestion")).toBeTruthy();
    expect(el.querySelector("#tab-panel-backstage")).toBeTruthy();
  });

  it("uses role=tablist on the bar", () => {
    const el = setup();
    const bar = el.querySelector(".browser-tab-bar");
    expect(bar?.getAttribute("role")).toBe("tablist");
  });

  it("uses role=tab on each button", () => {
    const el = setup();
    const tabs = el.querySelectorAll(".browser-tab");
    tabs.forEach((tab) => {
      expect(tab.getAttribute("role")).toBe("tab");
    });
  });

  it("uses role=tabpanel on content panels", () => {
    const el = setup();
    const panels = el.querySelectorAll(".browser-tab-panel");
    panels.forEach((panel) => {
      expect(panel.getAttribute("role")).toBe("tabpanel");
    });
  });
});

describe("mountBrowserTabs", () => {
  beforeEach(() => {
    storage = createInMemoryStorage();
    teardown();
  });

  it("calls onChange when a tab is clicked", () => {
    const el = setup("chat");
    const bar = el.querySelector<HTMLElement>(".browser-tab-bar")!;
    const calls: BrowserTabId[] = [];
    mountBrowserTabs(bar, (id) => calls.push(id), { storage });

    const ingestionBtn = bar.querySelector<HTMLButtonElement>(
      '[data-browser-tab="ingestion"]',
    )!;
    ingestionBtn.click();

    expect(calls).toEqual(["ingestion"]);
  });

  it("updates aria-selected on switch", () => {
    const el = setup("chat");
    const bar = el.querySelector<HTMLElement>(".browser-tab-bar")!;
    mountBrowserTabs(bar, () => {}, { storage });

    const backstageBtn = bar.querySelector<HTMLButtonElement>(
      '[data-browser-tab="backstage"]',
    )!;
    backstageBtn.click();

    expect(backstageBtn.getAttribute("aria-selected")).toBe("true");
    const chatBtn = bar.querySelector<HTMLButtonElement>(
      '[data-browser-tab="chat"]',
    )!;
    expect(chatBtn.getAttribute("aria-selected")).toBe("false");
  });

  it("toggles is-active class", () => {
    const el = setup("chat");
    const bar = el.querySelector<HTMLElement>(".browser-tab-bar")!;
    mountBrowserTabs(bar, () => {}, { storage });

    const backstageBtn = bar.querySelector<HTMLButtonElement>(
      '[data-browser-tab="backstage"]',
    )!;
    backstageBtn.click();

    expect(backstageBtn.classList.contains("is-active")).toBe(true);
    const chatBtn = bar.querySelector<HTMLButtonElement>(
      '[data-browser-tab="chat"]',
    )!;
    expect(chatBtn.classList.contains("is-active")).toBe(false);
  });

  it("persists tab to localStorage", () => {
    const el = setup("chat");
    const bar = el.querySelector<HTMLElement>(".browser-tab-bar")!;
    mountBrowserTabs(bar, () => {}, { storage });

    bar
      .querySelector<HTMLButtonElement>('[data-browser-tab="backstage"]')!
      .click();

    expect(readStoredBrowserTab(storage)).toBe("backstage");
  });

  it("switchTo method works programmatically", () => {
    const el = setup("chat");
    const bar = el.querySelector<HTMLElement>(".browser-tab-bar")!;
    const calls: BrowserTabId[] = [];
    const ctrl = mountBrowserTabs(bar, (id) => calls.push(id), { storage });

    ctrl.switchTo("ingestion");

    expect(calls).toEqual(["ingestion"]);
    const ingestionBtn = bar.querySelector<HTMLButtonElement>(
      '[data-browser-tab="ingestion"]',
    )!;
    expect(ingestionBtn.classList.contains("is-active")).toBe(true);
  });

  it("supports keyboard navigation with ArrowRight", () => {
    const el = setup("chat");
    const bar = el.querySelector<HTMLElement>(".browser-tab-bar")!;
    const calls: BrowserTabId[] = [];
    mountBrowserTabs(bar, (id) => calls.push(id), { storage });

    bar.dispatchEvent(
      new KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true }),
    );

    expect(calls).toEqual(["ingestion"]);
  });

  it("supports keyboard navigation with ArrowLeft", () => {
    const el = setup("ingestion");
    const bar = el.querySelector<HTMLElement>(".browser-tab-bar")!;
    const calls: BrowserTabId[] = [];
    mountBrowserTabs(bar, (id) => calls.push(id), { storage });

    bar.dispatchEvent(
      new KeyboardEvent("keydown", { key: "ArrowLeft", bubbles: true }),
    );

    expect(calls).toEqual(["chat"]);
  });

  it("wraps around with ArrowLeft from first tab", () => {
    const el = setup("chat");
    const bar = el.querySelector<HTMLElement>(".browser-tab-bar")!;
    const calls: BrowserTabId[] = [];
    mountBrowserTabs(bar, (id) => calls.push(id), { storage });

    bar.dispatchEvent(
      new KeyboardEvent("keydown", { key: "ArrowLeft", bubbles: true }),
    );

    expect(calls).toEqual(["backstage"]);
  });

  it("wraps around with ArrowRight from last tab", () => {
    const el = setup("backstage");
    const bar = el.querySelector<HTMLElement>(".browser-tab-bar")!;
    const calls: BrowserTabId[] = [];
    mountBrowserTabs(bar, (id) => calls.push(id), { storage });

    bar.dispatchEvent(
      new KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true }),
    );

    expect(calls).toEqual(["chat"]);
  });

  it("ignores irrelevant keys", () => {
    const el = setup("chat");
    const bar = el.querySelector<HTMLElement>(".browser-tab-bar")!;
    const calls: BrowserTabId[] = [];
    mountBrowserTabs(bar, (id) => calls.push(id), { storage });

    bar.dispatchEvent(
      new KeyboardEvent("keydown", { key: "Enter", bubbles: true }),
    );

    expect(calls).toEqual([]);
  });
});

describe("storeBrowserTab / readStoredBrowserTab", () => {
  beforeEach(() => {
    storage = createInMemoryStorage();
    clearStorage(storage);
  });

  it("returns chat by default", () => {
    expect(readStoredBrowserTab(storage)).toBe("chat");
  });

  it("round-trips stored value", () => {
    storeBrowserTab("backstage", storage);
    expect(readStoredBrowserTab(storage)).toBe("backstage");
  });

  it("round-trips ingestion value", () => {
    storeBrowserTab("ingestion", storage);
    expect(readStoredBrowserTab(storage)).toBe("ingestion");
  });

  it("falls back to chat for invalid values", () => {
    storage.setItem("lia_browser_tab", "invalid");
    expect(readStoredBrowserTab(storage)).toBe("chat");
  });
});
