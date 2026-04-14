import { describe, expect, it, beforeEach, vi } from "vitest";
import { mountMobileInterpPanel } from "@/app/mobile/mobileInterpPanel";
import type { MobileSheet } from "@/app/mobile/mobileSheet";
import type { ExpertCardViewModel } from "@/shared/ui/organisms/expertCards";

function createDom(): HTMLElement {
  const root = document.createElement("div");
  root.innerHTML = `
    <div id="mobile-interp-list" class="mobile-card-list"></div>
    <div id="mobile-interp-empty" class="mobile-empty-state" hidden>
      <p class="mobile-empty-state-text">Las interpretaciones de expertos aparecerán aquí cuando LIA responda tu consulta</p>
    </div>
    <div id="modal-layer" hidden>
      <section id="modal-expert-detail">
        <div id="expert-detail-content"><p>Expert detail content</p></div>
      </section>
    </div>
  `;
  return root;
}

function createCards(): ExpertCardViewModel[] {
  return [
    {
      articleLabel: "ET artículo 240",
      classification: "concordancia",
      classificationLabel: "Concordancia",
      heading: "Confirma tarifa del 35%",
      id: "group:ET_ART_240",
      providerLabels: ["DIAN"],
      relevancia: null,
      signal: "permite",
      signalLabel: "Permite",
      sourceCountLabel: "2 fuentes",
    },
    {
      articleLabel: "Decreto 1625/2016",
      classification: "complementario",
      classificationLabel: "Complementario",
      heading: "Tarifa reducida en zonas francas",
      id: "group:DEC_1625",
      providerLabels: [],
      relevancia: null,
      signal: "condiciona",
      signalLabel: "Condiciona",
      sourceCountLabel: "1 fuente",
    },
  ];
}

function mockSheet(): MobileSheet {
  return {
    open: vi.fn(),
    close: vi.fn(),
    isOpen: () => false,
  };
}

describe("mobileInterpPanel", () => {
  let root: HTMLElement;

  beforeEach(() => {
    document.body.innerHTML = "";
    root = createDom();
    document.body.appendChild(root);
  });

  it("renders expert cards grouped by classification", () => {
    const sheet = mockSheet();
    const panel = mountMobileInterpPanel(root, sheet);
    panel.setCards(createCards());

    const cards = root.querySelectorAll(".mobile-interp-card");
    expect(cards.length).toBe(2);

    // Check group labels
    const groupLabels = root.querySelectorAll(".mobile-interp-group-label");
    expect(groupLabels.length).toBeGreaterThan(0);
  });

  it("cards show classification, signal, and description", () => {
    const sheet = mockSheet();
    const panel = mountMobileInterpPanel(root, sheet);
    panel.setCards(createCards());

    const firstCard = root.querySelector('.mobile-interp-card[data-card-id="group:ET_ART_240"]')!;
    expect(firstCard).toBeTruthy();
    expect(firstCard.querySelector(".mobile-interp-card-ref")!.textContent).toContain("ET artículo 240");
    expect(firstCard.querySelector(".mobile-interp-card-signal")!.textContent).toContain("Permite");
    expect(firstCard.querySelector(".mobile-interp-card-desc")!.textContent).toContain("Confirma tarifa del 35%");
  });

  it("shows NO relevance percentage in cards (no dedicated % badge or score)", () => {
    const sheet = mockSheet();
    const panel = mountMobileInterpPanel(root, sheet);
    panel.setCards(createCards());

    // Verify there's no dedicated relevance score element with a percentage
    const cards = root.querySelectorAll(".mobile-interp-card");
    for (const card of cards) {
      // No element should show a relevance percentage like "85%" as a score badge
      const header = card.querySelector(".mobile-interp-card-header")!;
      const headerText = header.textContent ?? "";
      // Signal chips show "Permite", "Condiciona" etc — not percentages
      expect(headerText).not.toMatch(/\b\d{1,3}%\s*(relevancia|relevance|score)/i);
    }
  });

  it("shows empty state when no expert cards", () => {
    const sheet = mockSheet();
    const panel = mountMobileInterpPanel(root, sheet);
    panel.setCards([]);

    expect(root.querySelector<HTMLElement>("#mobile-interp-empty")!.hidden).toBe(false);
  });

  it("clear resets the panel", () => {
    const sheet = mockSheet();
    const panel = mountMobileInterpPanel(root, sheet);
    panel.setCards(createCards());
    expect(root.querySelectorAll(".mobile-interp-card").length).toBe(2);

    panel.clear();
    expect(root.querySelectorAll(".mobile-interp-card").length).toBe(0);
    expect(root.querySelector<HTMLElement>("#mobile-interp-empty")!.hidden).toBe(false);
  });

  it("hides hidden expert cards", () => {
    const sheet = mockSheet();
    const panel = mountMobileInterpPanel(root, sheet);
    const cards = createCards();
    cards[0].hidden = true;
    panel.setCards(cards);
    expect(root.querySelectorAll(".mobile-interp-card").length).toBe(1);
  });

  it("card data-classification attribute matches classification", () => {
    const sheet = mockSheet();
    const panel = mountMobileInterpPanel(root, sheet);
    panel.setCards(createCards());

    const concordCard = root.querySelector('.mobile-interp-card[data-classification="concordancia"]');
    expect(concordCard).toBeTruthy();

    const compCard = root.querySelector('.mobile-interp-card[data-classification="complementario"]');
    expect(compCard).toBeTruthy();
  });

  it("Issue 4: shows pre-response empty text before response received", () => {
    const sheet = mockSheet();
    const panel = mountMobileInterpPanel(root, sheet);
    panel.setCards([]);

    const textEl = root.querySelector<HTMLElement>(".mobile-empty-state-text")!;
    expect(textEl.textContent).toContain("aparecerán aquí cuando LIA responda");
  });

  it("Issue 4: shows post-response empty text after response received with no expert cards", () => {
    const sheet = mockSheet();
    const panel = mountMobileInterpPanel(root, sheet);
    panel.setResponseReceived(true);
    panel.setCards([]);

    const textEl = root.querySelector<HTMLElement>(".mobile-empty-state-text")!;
    expect(textEl.textContent).toContain("No se encontraron interpretaciones");
  });

  it("Issue 4: clear resets responseReceived and restores pre-response text", () => {
    const sheet = mockSheet();
    const panel = mountMobileInterpPanel(root, sheet);
    panel.setResponseReceived(true);
    panel.setCards([]);

    panel.clear();

    const textEl = root.querySelector<HTMLElement>(".mobile-empty-state-text")!;
    expect(textEl.textContent).toContain("aparecerán aquí cuando LIA responda");
  });
});
