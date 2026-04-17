import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { renderOrchestrationShell } from "@/app/orchestration/shell";
import { mountOrchestrationApp } from "@/features/orchestration/orchestrationApp";
import { createI18n } from "@/shared/i18n";

describe("orchestration app", () => {
  beforeEach(() => {
    Object.defineProperty(HTMLElement.prototype, "scrollIntoView", {
      configurable: true,
      value: vi.fn(),
      writable: true,
    });
    Object.defineProperty(window, "scrollTo", {
      configurable: true,
      value: vi.fn(),
      writable: true,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the new information architecture map and filters modules by scope", () => {
    const i18n = createI18n("es-CO");
    document.body.innerHTML = `<div id="app">${renderOrchestrationShell(i18n)}</div>`;

    const root = document.getElementById("app");
    if (!root) {
      throw new Error("Missing app root.");
    }

    mountOrchestrationApp(root, { i18n });

    const sections = Array.from(document.querySelectorAll<HTMLElement>(".orch-section"));
    const navButtons = Array.from(document.querySelectorAll<HTMLElement>(".orch-nav-btn"));
    const filterButtons = Array.from(document.querySelectorAll<HTMLButtonElement>(".orch-filter-btn"));
    const moduleCards = Array.from(document.querySelectorAll<HTMLElement>(".orch-module-card"));
    const normativaFilter = document.querySelector<HTMLButtonElement>('[data-scope-filter="normativa"]');
    const mainChatCards = Array.from(document.querySelectorAll<HTMLElement>('.orch-module-card[data-scope="main-chat"]'));
    const normativaCards = Array.from(document.querySelectorAll<HTMLElement>('.orch-module-card[data-scope="normativa"]'));
    const modulesButton = document.querySelector<HTMLElement>('[data-target="orch-modules"]');

    expect(sections.length).toBeGreaterThan(0);
    expect(navButtons.length).toBeGreaterThan(0);
    expect(filterButtons.length).toBeGreaterThan(0);
    expect(moduleCards.length).toBeGreaterThan(0);
    expect(document.body.textContent).toContain("Arquitectura de Información y Orquestación");
    expect(document.body.textContent).toContain("GraphEvidenceBundle");
    expect(document.body.textContent).toContain("answer_synthesis.py");
    expect(document.body.textContent).toContain("answer_inline_anchors.py");
    expect(document.body.textContent).toContain("src/lia_graph/normativa/orchestrator.py");
    expect(document.body.textContent).toContain("src/lia_graph/interpretacion/orchestrator.py");
    expect(document.body.textContent).toContain("ui_citation_profile_builders.py");
    expect(document.body.textContent).toContain("ui_source_view_processors.py");
    expect(document.body.textContent).toContain("ui_analysis_controllers.py");
    expect(document.body.textContent).toContain("Bubble primero; Normativa e Interpretación arrancan después con el mismo kernel mínimo");
    expect(document.body.textContent).not.toContain("Normativa facade (target)");
    expect(document.body.textContent).not.toContain("Futuras superficies");
    expect(document.body.textContent).not.toContain("Pipeline C");

    normativaFilter?.click();

    expect(normativaFilter?.getAttribute("aria-pressed")).toBe("true");
    expect(mainChatCards.every((card) => card.hidden)).toBe(true);
    expect(normativaCards.some((card) => !card.hidden)).toBe(true);

    modulesButton?.click();

    expect(window.scrollTo).toHaveBeenCalled();
  });
});
