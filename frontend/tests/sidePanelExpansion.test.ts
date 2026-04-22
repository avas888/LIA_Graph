import { beforeEach, describe, expect, it, vi } from "vitest";

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

import { initSidePanelExpansion } from "@/features/chat/sidePanelExpansion";

function createSidePanel(): {
  sidePanel: HTMLElement;
  normativaSection: HTMLElement;
  expertosSection: HTMLElement;
  normativaExpandBtn: HTMLButtonElement;
  expertosExpandBtn: HTMLButtonElement;
  normativaRestore: HTMLButtonElement;
  expertosRestore: HTMLButtonElement;
} {
  const sidePanel = document.createElement("aside");
  sidePanel.className = "side-panel";
  sidePanel.dataset.sidePanelExpansion = "idle";

  const normativaSection = document.createElement("section");
  normativaSection.className = "side-panel-section-normativa";
  const normativaExpandBtn = document.createElement("button");
  normativaExpandBtn.dataset.sidePanelTarget = "normativa";
  normativaExpandBtn.setAttribute("aria-pressed", "false");
  const normativaRestore = document.createElement("button");
  normativaRestore.dataset.sidePanelRestore = "normativa";
  normativaRestore.hidden = true;
  normativaSection.append(normativaExpandBtn, normativaRestore);

  const expertosSection = document.createElement("section");
  expertosSection.className = "side-panel-section-expertos";
  const expertosExpandBtn = document.createElement("button");
  expertosExpandBtn.dataset.sidePanelTarget = "expertos";
  expertosExpandBtn.setAttribute("aria-pressed", "false");
  const expertosRestore = document.createElement("button");
  expertosRestore.dataset.sidePanelRestore = "expertos";
  expertosRestore.hidden = true;
  expertosSection.append(expertosExpandBtn, expertosRestore);

  sidePanel.append(normativaSection, expertosSection);
  document.body.appendChild(sidePanel);

  return {
    sidePanel,
    normativaSection,
    expertosSection,
    normativaExpandBtn,
    expertosExpandBtn,
    normativaRestore,
    expertosRestore,
  };
}

describe("initSidePanelExpansion", () => {
  beforeEach(() => {
    mockStore.clear();
    document.body.innerHTML = "";
  });

  it("initializes in idle state with no persisted value", () => {
    const { sidePanel, normativaExpandBtn, expertosExpandBtn } = createSidePanel();
    initSidePanelExpansion(sidePanel);
    expect(sidePanel.dataset.sidePanelExpansion).toBe("idle");
    expect(normativaExpandBtn.getAttribute("aria-pressed")).toBe("false");
    expect(expertosExpandBtn.getAttribute("aria-pressed")).toBe("false");
  });

  it("restores persisted normativa-expanded state on init", () => {
    mockStore.set("lia_side_panel_expansion_v1", "normativa");
    const { sidePanel, normativaExpandBtn, expertosRestore, normativaRestore } =
      createSidePanel();
    initSidePanelExpansion(sidePanel);
    expect(sidePanel.dataset.sidePanelExpansion).toBe("normativa");
    expect(normativaExpandBtn.getAttribute("aria-pressed")).toBe("true");
    expect(expertosRestore.hidden).toBe(false);
    expect(normativaRestore.hidden).toBe(true);
  });

  it("falls back to idle when persisted value is invalid", () => {
    mockStore.set("lia_side_panel_expansion_v1", "garbage");
    const { sidePanel } = createSidePanel();
    initSidePanelExpansion(sidePanel);
    expect(sidePanel.dataset.sidePanelExpansion).toBe("idle");
  });

  it("expands normativa when its button is clicked", () => {
    const { sidePanel, normativaExpandBtn, expertosRestore } = createSidePanel();
    initSidePanelExpansion(sidePanel);
    normativaExpandBtn.click();
    expect(sidePanel.dataset.sidePanelExpansion).toBe("normativa");
    expect(normativaExpandBtn.getAttribute("aria-pressed")).toBe("true");
    expect(expertosRestore.hidden).toBe(false);
    expect(mockStore.get("lia_side_panel_expansion_v1")).toBe("normativa");
  });

  it("toggles back to idle when active expand button is clicked again", () => {
    const { sidePanel, normativaExpandBtn } = createSidePanel();
    initSidePanelExpansion(sidePanel);
    normativaExpandBtn.click();
    normativaExpandBtn.click();
    expect(sidePanel.dataset.sidePanelExpansion).toBe("idle");
    expect(normativaExpandBtn.getAttribute("aria-pressed")).toBe("false");
    expect(mockStore.has("lia_side_panel_expansion_v1")).toBe(false);
  });

  it("switches directly between normativa and expertos expansion", () => {
    const { sidePanel, normativaExpandBtn, expertosExpandBtn } = createSidePanel();
    initSidePanelExpansion(sidePanel);
    normativaExpandBtn.click();
    expect(sidePanel.dataset.sidePanelExpansion).toBe("normativa");
    expertosExpandBtn.click();
    expect(sidePanel.dataset.sidePanelExpansion).toBe("expertos");
    expect(normativaExpandBtn.getAttribute("aria-pressed")).toBe("false");
    expect(expertosExpandBtn.getAttribute("aria-pressed")).toBe("true");
  });

  it("restores idle when the collapsed stub is clicked", () => {
    const { sidePanel, normativaExpandBtn, expertosRestore } = createSidePanel();
    initSidePanelExpansion(sidePanel);
    normativaExpandBtn.click();
    expect(expertosRestore.hidden).toBe(false);
    expertosRestore.click();
    expect(sidePanel.dataset.sidePanelExpansion).toBe("idle");
    expect(expertosRestore.hidden).toBe(true);
  });

  it("ignores clicks on hidden restore stubs", () => {
    const { sidePanel, normativaRestore } = createSidePanel();
    initSidePanelExpansion(sidePanel);
    normativaRestore.click();
    expect(sidePanel.dataset.sidePanelExpansion).toBe("idle");
  });

  it("removes event listeners when dispose is called", () => {
    const { sidePanel, normativaExpandBtn } = createSidePanel();
    const dispose = initSidePanelExpansion(sidePanel);
    dispose();
    normativaExpandBtn.click();
    expect(sidePanel.dataset.sidePanelExpansion).toBe("idle");
  });
});
