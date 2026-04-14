import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  deriveSourceTierLabel,
  formatNormativeCitationTitle,
  citationTitleValue,
  createNormativeModalController,
} from "@/features/chat/normativeModals";
import { createI18n } from "@/shared/i18n";

vi.mock("@/features/chat/normative/citationParsing", () => ({
  parseEtLocatorText: vi.fn().mockReturnValue(null),
  formatParsedEtLocator: vi.fn().mockReturnValue(""),
  parseEtTitle: vi.fn().mockReturnValue(null),
  toSpanishTitleCase: (s: string) => s,
  canonicalizeEtArticleToken: (v: unknown) => {
    const s = String(v || "").trim();
    return /^\d+/.test(s) ? s : "";
  },
  expandArticleRange: vi.fn().mockReturnValue(null),
}));

vi.mock("@/features/chat/normative/profileRenderer", () => ({
  fetchCitationProfileInstant: vi.fn().mockResolvedValue({}),
  fetchCitationProfileLlm: vi.fn().mockResolvedValue({}),
  createProfileRenderer: () => ({
    resetNormaProfileCard: vi.fn(),
    setNormaModalStatus: vi.fn(),
    renderProfileContent: vi.fn(),
    applyLlmEnrichment: vi.fn(),
  }),
}));

vi.mock("@/features/chat/normative/interpretationModal", () => ({
  createInterpretationModal: () => ({
    clearInterpretations: vi.fn(),
    clearSummary: vi.fn(),
    openInterpretationsModal: vi.fn(),
    openSummaryModal: vi.fn(),
  }),
}));

vi.mock("@/features/chat/normative/practicaReader", () => ({
  openPracticaReader: vi.fn(),
}));

vi.mock("@/features/chat/normative/articleReader", () => ({
  openArticleReader: vi.fn(),
}));

// ── deriveSourceTierLabel ─────────────────────────────────────

describe("deriveSourceTierLabel", () => {
  it("returns cross-topic label for baseline citations with cross_topic", () => {
    expect(
      deriveSourceTierLabel({ primary_role: "baseline", cross_topic: true })
    ).toBe("Fuente Normativa (Base transversal)");
  });

  it("returns the source_tier verbatim if present", () => {
    expect(
      deriveSourceTierLabel({ source_tier: "Fuente Loggro" })
    ).toBe("Fuente Loggro");
  });

  it("trims whitespace from source_tier", () => {
    expect(
      deriveSourceTierLabel({ source_tier: "  Fuente Normativa  " })
    ).toBe("Fuente Normativa");
  });

  it("returns Fuente Loggro for operational_checklist source_type", () => {
    expect(
      deriveSourceTierLabel({ source_type: "operational_checklist" })
    ).toBe("Fuente Loggro");
  });

  it("returns Fuente Loggro for internal_control source_type", () => {
    expect(
      deriveSourceTierLabel({ source_type: "internal_control" })
    ).toBe("Fuente Loggro");
  });

  it("returns Fuente Loggro for user_upload_practical source_type", () => {
    expect(
      deriveSourceTierLabel({ source_type: "user_upload_practical" })
    ).toBe("Fuente Loggro");
  });

  it("returns Fuente Loggro for local_upload practica_erp", () => {
    expect(
      deriveSourceTierLabel({
        url: "local_upload://file.pdf",
        knowledge_class: "practica_erp",
      })
    ).toBe("Fuente Loggro");
  });

  it("returns Fuente Normativa for normative_base knowledge class", () => {
    expect(
      deriveSourceTierLabel({ knowledge_class: "normative_base" })
    ).toBe("Fuente Normativa");
  });

  it("returns Fuente Expertos for interpretative_guidance", () => {
    expect(
      deriveSourceTierLabel({ knowledge_class: "interpretative_guidance" })
    ).toBe("Fuente Expertos");
  });

  it("returns Fuente Loggro for practica_erp knowledge class", () => {
    expect(
      deriveSourceTierLabel({ knowledge_class: "practica_erp" })
    ).toBe("Fuente Loggro");
  });

  it("defaults to Fuente Expertos for unknown knowledge class", () => {
    expect(deriveSourceTierLabel({ knowledge_class: "something_else" })).toBe("Fuente Expertos");
  });

  it("defaults to Fuente Expertos for null/undefined", () => {
    expect(deriveSourceTierLabel(null)).toBe("Fuente Expertos");
    expect(deriveSourceTierLabel(undefined)).toBe("Fuente Expertos");
  });

  it("defaults to Fuente Expertos for empty object", () => {
    expect(deriveSourceTierLabel({})).toBe("Fuente Expertos");
  });

  it("prefers source_tier over knowledge_class", () => {
    expect(
      deriveSourceTierLabel({
        source_tier: "Custom Tier",
        knowledge_class: "normative_base",
      })
    ).toBe("Custom Tier");
  });

  it("baseline cross_topic has highest priority", () => {
    expect(
      deriveSourceTierLabel({
        primary_role: "baseline",
        cross_topic: true,
        source_tier: "Something Else",
      })
    ).toBe("Fuente Normativa (Base transversal)");
  });
});

// ── formatNormativeCitationTitle ──────────────────────────────

describe("formatNormativeCitationTitle", () => {
  it("returns empty string for falsy input", () => {
    expect(formatNormativeCitationTitle(null)).toBe("");
    expect(formatNormativeCitationTitle(undefined)).toBe("");
    expect(formatNormativeCitationTitle("")).toBe("");
  });

  it("formats Ley title", () => {
    expect(formatNormativeCitationTitle("Ley 1819 de 2016")).toBe("Ley 1819 de 2016");
  });

  it("formats Ley title with remainder", () => {
    const result = formatNormativeCitationTitle("Ley 1819 de 2016: reforma tributaria");
    expect(result).toContain("Ley 1819 de 2016:");
    expect(result).toContain("reforma tributaria");
  });

  it("formats Ley title case-insensitively", () => {
    expect(formatNormativeCitationTitle("ley 2277 de 2022")).toBe("Ley 2277 de 2022");
  });

  it("formats Decreto title", () => {
    expect(formatNormativeCitationTitle("Decreto 1625 de 2016")).toBe("Decreto 1625 de 2016");
  });

  it("formats Decreto with remainder", () => {
    const result = formatNormativeCitationTitle("Decreto 1625 de 2016 - único reglamentario");
    expect(result).toContain("Decreto 1625 de 2016:");
  });

  it("formats Resolución title", () => {
    expect(formatNormativeCitationTitle("Resolución 42 de 2020")).toBe("Resolución 42 de 2020");
  });

  it("formats Resolucion (without accent) title", () => {
    expect(formatNormativeCitationTitle("Resolucion 42 de 2020")).toBe("Resolución 42 de 2020");
  });

  it("formats Formulario title", () => {
    expect(formatNormativeCitationTitle("Formulario 110")).toBe("Formulario 110");
  });

  it("formats Formulario title with remainder", () => {
    const result = formatNormativeCitationTitle("Formulario 110: declaración de renta");
    expect(result).toContain("Formulario 110:");
    expect(result).toContain("declaración de renta");
  });

  it("formats Formato title", () => {
    expect(formatNormativeCitationTitle("Formato 2516")).toBe("Formato 2516");
  });

  it("passes through unrecognized titles", () => {
    expect(formatNormativeCitationTitle("Concepto DIAN 12345")).toBe("Concepto DIAN 12345");
  });

  it("collapses whitespace", () => {
    expect(formatNormativeCitationTitle("Ley  1819   de  2016")).toBe("Ley 1819 de 2016");
  });
});

// ── citationTitleValue ─────────────────────────────────────────

describe("citationTitleValue", () => {
  it("returns formatted source_label when available", () => {
    const result = citationTitleValue({
      source_label: "Ley 1819 de 2016",
    });
    expect(result).toBe("Ley 1819 de 2016");
  });

  it("falls back to legal_reference when source_label is missing", () => {
    const result = citationTitleValue({
      legal_reference: "Decreto 1625 de 2016",
    });
    expect(result).toBe("Decreto 1625 de 2016");
  });

  it("falls back to title when other fields are missing", () => {
    const result = citationTitleValue({
      title: "Formulario 110",
    });
    expect(result).toBe("Formulario 110");
  });

  it("falls back to doc_id when labels are missing and doc_id is human-readable", () => {
    const result = citationTitleValue({
      doc_id: "Ley 2277 de 2022",
    });
    expect(result).toBe("Ley 2277 de 2022");
  });

  it("skips raw doc_ids and falls back to authority/tema", () => {
    const result = citationTitleValue({
      source_label: "renta_ingest_pt_normativa_declaracion_2025_01_ab12cd34",
      doc_id: "renta_ingest_pt_normativa_declaracion_2025_01_ab12cd34",
      authority: "DIAN",
      tema: "declaracion_renta",
    });
    expect(result).toContain("DIAN");
    expect(result).toContain("declaracion renta");
  });

  it("returns fallback for null/undefined citation", () => {
    expect(citationTitleValue(null)).toBe("Referencia normativa");
    expect(citationTitleValue(undefined)).toBe("Referencia normativa");
  });

  it("returns fallback for citation with no useful fields", () => {
    expect(citationTitleValue({})).toBe("Referencia normativa");
  });

  it("returns authority alone when tema is empty", () => {
    expect(
      citationTitleValue({ authority: "DIAN" })
    ).toBe("DIAN");
  });

  it("returns tema alone when authority is empty", () => {
    const result = citationTitleValue({ tema: "declaracion_renta" });
    expect(result).toContain("declaracion renta");
  });

  it("formats reference_key ley:1819:2016", () => {
    const result = citationTitleValue({
      reference_key: "ley:1819:2016",
    });
    expect(result).toBe("Ley 1819 de 2016");
  });

  it("formats reference_key ley:2277 (without year)", () => {
    const result = citationTitleValue({
      reference_key: "ley:2277",
    });
    expect(result).toBe("Ley 2277");
  });

  it("skips raw machine-identifier doc_ids with :: separators", () => {
    const result = citationTitleValue({
      source_label: "renta_ingest::section01",
      doc_id: "renta_ingest::section01",
    });
    // Should fall back to humanizeCitationFallback
    expect(result).toBe("Referencia normativa");
  });

  it("skips long identifiers without spaces (>40 chars)", () => {
    const longId = "a".repeat(50);
    const result = citationTitleValue({
      source_label: longId,
      doc_id: longId,
      authority: "DIAN",
    });
    expect(result).toContain("DIAN");
  });

  it("skips identifiers containing 'ingest'", () => {
    const result = citationTitleValue({
      source_label: "renta_ingest_doc_001",
      authority: "DIAN",
    });
    expect(result).toContain("DIAN");
  });

  it("skips identifiers with hex hashes", () => {
    const result = citationTitleValue({
      source_label: "pt expertos renta 27555a78 part 03",
      authority: "Concepto",
    });
    expect(result).toContain("Concepto");
  });

  it("skips identifiers with part N suffixes", () => {
    const result = citationTitleValue({
      source_label: "documento normativo part 5",
      authority: "DIAN",
    });
    expect(result).toContain("DIAN");
  });
});

// ── createNormativeModalController ──────────────────────────────

describe("createNormativeModalController", () => {
  let i18n: ReturnType<typeof createI18n>;

  function createDom() {
    const modalLayer = document.createElement("div");
    modalLayer.hidden = true;

    const modalNorma = document.createElement("div");
    modalNorma.id = "modal-norma";

    const modalInterpretations = document.createElement("div");
    modalInterpretations.id = "modal-interpretations";

    const modalSummary = document.createElement("div");
    modalSummary.id = "modal-summary";

    const normaTitleNode = document.createElement("h2");
    const normaTopbarNode = document.createElement("div");
    const parentNode = document.createElement("div");
    parentNode.appendChild(normaTopbarNode);

    const normaSectionsNode = document.createElement("div");
    const normaStatusNode = document.createElement("span");
    const normaFactsNode = document.createElement("div");
    const normaActionsNode = document.createElement("div");

    const interpretationStatusNode = document.createElement("p");
    const interpretationResultsNode = document.createElement("div");
    const summaryModeNode = document.createElement("p");
    const summaryExternalLinkNode = document.createElement("a");
    const summaryBodyNode = document.createElement("div");
    const summaryGroundingNode = document.createElement("div");

    return {
      modalLayer,
      modalNorma,
      modalInterpretations,
      modalSummary,
      normaTitleNode,
      normaTopbarNode,
      normaSectionsNode,
      normaStatusNode,
      normaFactsNode,
      normaActionsNode,
      interpretationStatusNode,
      interpretationResultsNode,
      summaryModeNode,
      summaryExternalLinkNode,
      summaryBodyNode,
      summaryGroundingNode,
    };
  }

  beforeEach(() => {
    document.body.innerHTML = "";
    i18n = createI18n("es-CO");
  });

  it("creates a controller with expected methods", () => {
    const dom = createDom();
    const state = {
      modalStack: [] as string[],
      activeCitation: null as Record<string, unknown> | null,
      activeNormaRequestId: 0,
      lastUserMessage: "",
    };

    const controller = createNormativeModalController({
      i18n,
      state,
      dom: dom as any,
      withThinkingWheel: (fn: () => Promise<unknown>) => fn(),
    });

    expect(typeof controller.openModal).toBe("function");
    expect(typeof controller.closeModal).toBe("function");
    expect(typeof controller.closeTopModal).toBe("function");
    expect(typeof controller.closeAllModals).toBe("function");
    expect(typeof controller.openNormaModal).toBe("function");
    expect(typeof controller.bindModalControls).toBe("function");
    expect(typeof controller.clearInterpretations).toBe("function");
    expect(typeof controller.clearSummary).toBe("function");
  });

  it("openModal shows the modal layer and sets is-open", () => {
    const dom = createDom();
    const state = { modalStack: [] as string[], activeCitation: null, activeNormaRequestId: 0, lastUserMessage: "" };
    const controller = createNormativeModalController({ i18n, state, dom: dom as any, withThinkingWheel: (fn: () => Promise<unknown>) => fn() });

    controller.openModal(dom.modalNorma);

    expect(dom.modalLayer.hidden).toBe(false);
    expect(dom.modalNorma.classList.contains("is-open")).toBe(true);
    expect(dom.modalNorma.getAttribute("aria-hidden")).toBe("false");
    expect(state.modalStack).toContain("modal-norma");
  });

  it("openModal with null does nothing", () => {
    const dom = createDom();
    const state = { modalStack: [] as string[], activeCitation: null, activeNormaRequestId: 0, lastUserMessage: "" };
    const controller = createNormativeModalController({ i18n, state, dom: dom as any, withThinkingWheel: (fn: () => Promise<unknown>) => fn() });

    controller.openModal(null);

    expect(dom.modalLayer.hidden).toBe(true);
    expect(state.modalStack).toHaveLength(0);
  });

  it("openModal does not duplicate id in the stack", () => {
    const dom = createDom();
    const state = { modalStack: [] as string[], activeCitation: null, activeNormaRequestId: 0, lastUserMessage: "" };
    const controller = createNormativeModalController({ i18n, state, dom: dom as any, withThinkingWheel: (fn: () => Promise<unknown>) => fn() });

    controller.openModal(dom.modalNorma);
    controller.openModal(dom.modalNorma);

    expect(state.modalStack.filter((id) => id === "modal-norma")).toHaveLength(1);
  });

  it("closeModal hides and removes from stack", () => {
    const dom = createDom();
    const state = { modalStack: [] as string[], activeCitation: null, activeNormaRequestId: 0, lastUserMessage: "" };
    const controller = createNormativeModalController({ i18n, state, dom: dom as any, withThinkingWheel: (fn: () => Promise<unknown>) => fn() });

    controller.openModal(dom.modalNorma);
    controller.closeModal(dom.modalNorma);

    expect(dom.modalNorma.classList.contains("is-open")).toBe(false);
    expect(dom.modalNorma.getAttribute("aria-hidden")).toBe("true");
    expect(state.modalStack).toHaveLength(0);
    expect(dom.modalLayer.hidden).toBe(true);
  });

  it("closeModal with null does nothing", () => {
    const dom = createDom();
    const state = { modalStack: [] as string[], activeCitation: null, activeNormaRequestId: 0, lastUserMessage: "" };
    const controller = createNormativeModalController({ i18n, state, dom: dom as any, withThinkingWheel: (fn: () => Promise<unknown>) => fn() });

    controller.closeModal(null); // should not throw
    expect(state.modalStack).toHaveLength(0);
  });

  it("closeTopModal closes the most recently opened modal", () => {
    const dom = createDom();
    document.body.appendChild(dom.modalNorma);
    document.body.appendChild(dom.modalInterpretations);
    const state = { modalStack: [] as string[], activeCitation: null, activeNormaRequestId: 0, lastUserMessage: "" };
    const controller = createNormativeModalController({ i18n, state, dom: dom as any, withThinkingWheel: (fn: () => Promise<unknown>) => fn() });

    controller.openModal(dom.modalNorma);
    controller.openModal(dom.modalInterpretations);

    expect(state.modalStack).toHaveLength(2);

    controller.closeTopModal();

    expect(state.modalStack).toEqual(["modal-norma"]);
    expect(dom.modalInterpretations.classList.contains("is-open")).toBe(false);
  });

  it("closeTopModal does nothing when stack is empty", () => {
    const dom = createDom();
    const state = { modalStack: [] as string[], activeCitation: null, activeNormaRequestId: 0, lastUserMessage: "" };
    const controller = createNormativeModalController({ i18n, state, dom: dom as any, withThinkingWheel: (fn: () => Promise<unknown>) => fn() });

    controller.closeTopModal(); // should not throw
    expect(state.modalStack).toHaveLength(0);
  });

  it("closeAllModals closes all three modals and hides layer", () => {
    const dom = createDom();
    const state = { modalStack: [] as string[], activeCitation: null, activeNormaRequestId: 0, lastUserMessage: "" };
    const controller = createNormativeModalController({ i18n, state, dom: dom as any, withThinkingWheel: (fn: () => Promise<unknown>) => fn() });

    controller.openModal(dom.modalNorma);
    controller.openModal(dom.modalInterpretations);
    controller.openModal(dom.modalSummary);

    controller.closeAllModals();

    expect(state.modalStack).toHaveLength(0);
    expect(dom.modalLayer.hidden).toBe(true);
    expect(dom.modalNorma.classList.contains("is-open")).toBe(false);
    expect(dom.modalInterpretations.classList.contains("is-open")).toBe(false);
    expect(dom.modalSummary.classList.contains("is-open")).toBe(false);
  });

  it("modal layer stays visible while at least one modal remains open", () => {
    const dom = createDom();
    document.body.appendChild(dom.modalNorma);
    document.body.appendChild(dom.modalInterpretations);
    const state = { modalStack: [] as string[], activeCitation: null, activeNormaRequestId: 0, lastUserMessage: "" };
    const controller = createNormativeModalController({ i18n, state, dom: dom as any, withThinkingWheel: (fn: () => Promise<unknown>) => fn() });

    controller.openModal(dom.modalNorma);
    controller.openModal(dom.modalInterpretations);

    controller.closeModal(dom.modalInterpretations);

    expect(dom.modalLayer.hidden).toBe(false);
    expect(state.modalStack).toEqual(["modal-norma"]);
  });

  it("openNormaModal sets activeCitation and opens the norma modal", () => {
    const dom = createDom();
    const state = { modalStack: [] as string[], activeCitation: null as Record<string, unknown> | null, activeNormaRequestId: 0, lastUserMessage: "" };
    const controller = createNormativeModalController({ i18n, state, dom: dom as any, withThinkingWheel: (fn: () => Promise<unknown>) => fn() });

    const citation = { reference_key: "et", locator_start: "240", source_label: "ET Art 240" };
    controller.openNormaModal(citation);

    expect(state.activeCitation).toBe(citation);
    expect(dom.modalNorma.classList.contains("is-open")).toBe(true);
    expect(state.activeNormaRequestId).toBeGreaterThan(0);
  });

  it("bindModalControls wires data-close-modal buttons", () => {
    const dom = createDom();
    document.body.appendChild(dom.modalNorma);

    const closeBtn = document.createElement("button");
    closeBtn.setAttribute("data-close-modal", "modal-norma");
    document.body.appendChild(closeBtn);

    const state = { modalStack: [] as string[], activeCitation: null, activeNormaRequestId: 0, lastUserMessage: "" };
    const controller = createNormativeModalController({ i18n, state, dom: dom as any, withThinkingWheel: (fn: () => Promise<unknown>) => fn() });

    controller.bindModalControls();
    controller.openModal(dom.modalNorma);

    expect(dom.modalNorma.classList.contains("is-open")).toBe(true);

    closeBtn.click();

    expect(dom.modalNorma.classList.contains("is-open")).toBe(false);
    expect(state.modalStack).toHaveLength(0);
  });

  it("bindModalControls wires data-back-modal buttons", () => {
    const dom = createDom();
    document.body.appendChild(dom.modalNorma);
    document.body.appendChild(dom.modalInterpretations);

    const backBtn = document.createElement("button");
    backBtn.setAttribute("data-back-modal", "true");
    document.body.appendChild(backBtn);

    const state = { modalStack: [] as string[], activeCitation: null, activeNormaRequestId: 0, lastUserMessage: "" };
    const controller = createNormativeModalController({ i18n, state, dom: dom as any, withThinkingWheel: (fn: () => Promise<unknown>) => fn() });

    controller.bindModalControls();
    controller.openModal(dom.modalNorma);
    controller.openModal(dom.modalInterpretations);

    backBtn.click();

    expect(state.modalStack).toEqual(["modal-norma"]);
  });

  it("Escape key closes top modal via bindModalControls", () => {
    const dom = createDom();
    document.body.appendChild(dom.modalNorma);

    const state = { modalStack: [] as string[], activeCitation: null, activeNormaRequestId: 0, lastUserMessage: "" };
    const controller = createNormativeModalController({ i18n, state, dom: dom as any, withThinkingWheel: (fn: () => Promise<unknown>) => fn() });

    controller.bindModalControls();
    controller.openModal(dom.modalNorma);

    window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));

    expect(state.modalStack).toHaveLength(0);
    expect(dom.modalNorma.classList.contains("is-open")).toBe(false);
  });
});
