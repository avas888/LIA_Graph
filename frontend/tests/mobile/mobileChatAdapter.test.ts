import { describe, expect, it, vi } from "vitest";
import { mountMobileChatAdapter } from "@/app/mobile/mobileChatAdapter";
import {
  UI_EVENT_CITATIONS_PREVIEW,
  UI_EVENT_CITATIONS_UPDATED,
  UI_EVENT_EXPERTS_UPDATED,
} from "@/shared/ui/patterns/uiEvents";
import type { CitationGroupViewModel } from "@/shared/ui/organisms/citationList";
import type { ExpertCardViewModel } from "@/shared/ui/organisms/expertCards";

function createRoot(): HTMLElement {
  const root = document.createElement("div");
  root.innerHTML = `
    <form id="chat-form"></form>
    <textarea id="message"></textarea>
    <button id="send-btn" type="submit">Enviar</button>
    <button id="new-thread-btn" type="button">Nuevo hilo</button>
  `;
  return root;
}

describe("mountMobileChatAdapter", () => {
  it("forwards shared citation and expert events into the mobile shell", () => {
    const root = createRoot();
    const nav = {
      activeTab: vi.fn(() => "chat"),
      resetBadges: vi.fn(),
      switchTab: vi.fn(),
      updateBadge: vi.fn(),
    };
    const normativaPanel = {
      clear: vi.fn(),
      setCitations: vi.fn(),
    };
    const interpPanel = {
      clear: vi.fn(),
      setCards: vi.fn(),
      setResponseReceived: vi.fn(),
    };

    mountMobileChatAdapter({
      interpPanel,
      nav,
      normativaPanel,
      root,
    });

    const citationGroups: CitationGroupViewModel[] = [
      {
        id: "actual",
        label: "Actual",
        items: [
          { action: "modal", id: "citation-1", meta: "DIAN", title: "Artículo 240 ET" },
          {
            action: "external",
            externalUrl: "https://example.com",
            id: "citation-2",
            mentionOnly: true,
            meta: "Ley",
            title: "Ley 1819",
          },
        ],
      },
    ];
    const expertCards: ExpertCardViewModel[] = [
      {
        articleLabel: "Art. 147 ET",
        classification: "concordancia",
        classificationLabel: "Coinciden",
        heading: "Las interpretaciones convergen.",
        id: "expert-1",
        providerLabels: ["DIAN"],
        signal: "permite",
        signalLabel: "Permite",
        sourceCountLabel: "1 fuente",
      },
    ];

    root.dispatchEvent(
      new CustomEvent(UI_EVENT_CITATIONS_UPDATED, {
        bubbles: true,
        detail: { groups: citationGroups, isFinal: true },
      }),
    );
    root.dispatchEvent(
      new CustomEvent(UI_EVENT_EXPERTS_UPDATED, {
        bubbles: true,
        detail: { cards: expertCards },
      }),
    );

    expect(normativaPanel.setCitations).toHaveBeenCalledWith([
      {
        action: "modal",
        externalUrl: null,
        fallbackUrl: null,
        id: "citation-1",
        mentionOnly: false,
        meta: "DIAN",
        rawCitation: null,
        title: "Artículo 240 ET",
      },
      {
        action: "external",
        externalUrl: "https://example.com",
        fallbackUrl: null,
        id: "citation-2",
        mentionOnly: true,
        meta: "Ley",
        rawCitation: null,
        title: "Ley 1819",
      },
    ]);
    expect(interpPanel.setCards).toHaveBeenCalledWith(expertCards);
    expect(nav.updateBadge).toHaveBeenNthCalledWith(1, "normativa", 2);
    expect(nav.updateBadge).toHaveBeenNthCalledWith(2, "interpretacion", 1);
    // Issue 4: citations arriving signals response received
    expect(interpPanel.setResponseReceived).toHaveBeenCalledWith(true);
  });

  it("Issue 4: signals responseReceived even when citations are empty but isFinal is true", () => {
    const root = createRoot();
    const nav = {
      activeTab: vi.fn(() => "chat"),
      resetBadges: vi.fn(),
      switchTab: vi.fn(),
      updateBadge: vi.fn(),
    };
    const normativaPanel = {
      clear: vi.fn(),
      setCitations: vi.fn(),
    };
    const interpPanel = {
      clear: vi.fn(),
      setCards: vi.fn(),
      setResponseReceived: vi.fn(),
    };

    mountMobileChatAdapter({
      interpPanel,
      nav,
      normativaPanel,
      root,
    });

    // Dispatch with empty groups but isFinal=true (response settled with zero citations)
    root.dispatchEvent(
      new CustomEvent(UI_EVENT_CITATIONS_UPDATED, {
        bubbles: true,
        detail: { groups: [], isFinal: true },
      }),
    );

    expect(interpPanel.setResponseReceived).toHaveBeenCalledWith(true);
  });

  it("Issue 4: does NOT signal responseReceived for non-final (loading) citation events", () => {
    const root = createRoot();
    const nav = {
      activeTab: vi.fn(() => "chat"),
      resetBadges: vi.fn(),
      switchTab: vi.fn(),
      updateBadge: vi.fn(),
    };
    const normativaPanel = {
      clear: vi.fn(),
      setCitations: vi.fn(),
    };
    const interpPanel = {
      clear: vi.fn(),
      setCards: vi.fn(),
      setResponseReceived: vi.fn(),
    };

    mountMobileChatAdapter({
      interpPanel,
      nav,
      normativaPanel,
      root,
    });

    // Dispatch with empty groups and no isFinal (loading placeholder)
    root.dispatchEvent(
      new CustomEvent(UI_EVENT_CITATIONS_UPDATED, {
        bubbles: true,
        detail: { groups: [] },
      }),
    );

    expect(interpPanel.setResponseReceived).not.toHaveBeenCalled();
  });

  it("W2 Phase 7: ignores lia:citations-preview events (desktop-only)", () => {
    const root = createRoot();
    const nav = {
      activeTab: vi.fn(() => "chat"),
      resetBadges: vi.fn(),
      switchTab: vi.fn(),
      updateBadge: vi.fn(),
    };
    const normativaPanel = {
      clear: vi.fn(),
      setCitations: vi.fn(),
    };
    const interpPanel = {
      clear: vi.fn(),
      setCards: vi.fn(),
      setResponseReceived: vi.fn(),
    };

    mountMobileChatAdapter({
      interpPanel,
      nav,
      normativaPanel,
      root,
    });

    // W2 Phase 7 decoupling invariant: a preview event must NOT reach the
    // mobile normativa panel. Mobile subscribes only to lia:citations-updated,
    // which is reserved for the final/authoritative payload. If the mobile
    // adapter ever grew a subscription to lia:citations-preview, the badge
    // counter would flicker during thinking and MobileNormativaPanel would
    // need a placeholder-citations concept it currently lacks.
    // See docs/next/soporte_normativo_citation_ordering.md §10.3.
    root.dispatchEvent(
      new CustomEvent(UI_EVENT_CITATIONS_PREVIEW, {
        bubbles: true,
        detail: {
          items: [
            {
              action: "none",
              id: "preview-1",
              meta: "DIAN",
              preview: true,
              title: "Resolución 233 de 2025",
            },
            {
              action: "none",
              id: "preview-2",
              meta: "DIAN",
              preview: true,
              title: "Resolución 162 de 2023",
            },
          ],
        },
      }),
    );

    expect(normativaPanel.setCitations).not.toHaveBeenCalled();
    expect(normativaPanel.clear).not.toHaveBeenCalled();
    expect(nav.updateBadge).not.toHaveBeenCalled();
    expect(interpPanel.setResponseReceived).not.toHaveBeenCalled();
  });

  it("resets mobile panels and badges on submit and on new thread", () => {
    const root = createRoot();
    const nav = {
      activeTab: vi.fn(() => "chat"),
      resetBadges: vi.fn(),
      switchTab: vi.fn(),
      updateBadge: vi.fn(),
    };
    const normativaPanel = {
      clear: vi.fn(),
      setCitations: vi.fn(),
    };
    const interpPanel = {
      clear: vi.fn(),
      setCards: vi.fn(),
      setResponseReceived: vi.fn(),
    };

    mountMobileChatAdapter({
      interpPanel,
      nav,
      normativaPanel,
      root,
    });

    root.querySelector<HTMLFormElement>("#chat-form")!.dispatchEvent(
      new Event("submit", { bubbles: true }),
    );
    root.querySelector<HTMLButtonElement>("#new-thread-btn")!.click();

    expect(nav.resetBadges).toHaveBeenCalledTimes(2);
    expect(normativaPanel.clear).toHaveBeenCalledTimes(2);
    expect(interpPanel.clear).toHaveBeenCalledTimes(2);
    // Issue 4: responseReceived is reset on submit and new thread
    expect(interpPanel.setResponseReceived).toHaveBeenCalledWith(false);
    expect(nav.switchTab).toHaveBeenCalledWith("chat");
  });
});
