import { describe, expect, it, beforeEach, vi } from "vitest";
import { mountMobileNormativaPanel } from "@/app/mobile/mobileNormativaPanel";
import type { MobileSheet } from "@/app/mobile/mobileSheet";
import type { MobileCitationCardViewModel } from "@/shared/ui/organisms/citationList";
import type { CitationProfileResponse } from "@/features/chat/normative/types";

const mockFetchInstant = vi.fn<(raw: Record<string, unknown>) => Promise<CitationProfileResponse>>();
const mockFetchLlm = vi.fn<(raw: Record<string, unknown>) => Promise<CitationProfileResponse>>();

vi.mock("@/features/chat/normative/profileRenderer", () => ({
  fetchCitationProfileInstant: (...args: unknown[]) => mockFetchInstant(args[0] as Record<string, unknown>),
  fetchCitationProfileLlm: (...args: unknown[]) => mockFetchLlm(args[0] as Record<string, unknown>),
}));

function createDom(): HTMLElement {
  const root = document.createElement("div");
  root.innerHTML = [
    '<div id="mobile-normativa-list" class="mobile-card-list"></div>',
    '<div id="mobile-normativa-empty" class="mobile-empty-state" hidden><p>Empty</p></div>',
    '<div id="modal-layer" hidden><section id="modal-norma"></section></div>',
  ].join("");
  return root;
}

function createCitations(): MobileCitationCardViewModel[] {
  return [
    { action: "modal", id: "et-art-240", meta: "Normativa | DIAN", rawCitation: { doc_id: "et_art_240", reference_key: "et:240" }, title: "Estatuto Tributario Art. 240" },
    { action: "modal", id: "ley-2277", meta: "Ley | Congreso", rawCitation: { doc_id: "ley_2277", reference_key: "ley:2277" }, title: "Ley 2277 de 2022" },
  ];
}

function mockSheet(): MobileSheet {
  return { open: vi.fn(), replaceContent: vi.fn(), close: vi.fn(), isOpen: () => true };
}

function makeProfile(overrides: Partial<CitationProfileResponse> = {}): CitationProfileResponse {
  // Raw taxonomy value from `normative_taxonomy.py` for family=et_dur. The
  // renderer in mobileNormativaPanel prefixes it with "Fuerza vinculante:" at
  // display time; tests assert against that rendered form.
  return {
    title: "Estatuto Tributario Art. 240",
    binding_force: "Compilación tributaria vigente",
    binding_force_rank: 860,
    lead: "La tarifa general del impuesto sobre la renta...",
    facts: [{ label: "Tipo", value: "Articulo del ET" }, { label: "Vigencia", value: "Vigente" }],
    sections: [{ id: "impacto", title: "Impacto tributario", body: "Afecta a personas juridicas..." }],
    original_text: { title: "Texto original del articulo", quote: "La tarifa general del impuesto sobre la renta aplicable a las sociedades nacionales...", source_url: "https://example.com/et-240", evidence_status: "verified" },
    expert_comment: { topic_label: "Analisis de tarifas", body: "Este articulo es fundamental para la planeacion tributaria corporativa.", source_label: "Dr. Experto Tributario", accordion_default: "closed", evidence_status: "verified" },
    additional_depth_sections: [{ title: "Normativa relacionada", items: [{ label: "Decreto 2231 de 2023", url: "https://example.com/d2231" }, { label: "Resolucion 042" }], accordion_default: "closed" }],
    source_action: { label: "Ver documento original", state: "available", url: "https://example.com/source" },
    needs_llm: false,
    skipped: false,
    ...overrides,
  };
}

describe("mobileNormativaPanel", () => {
  let root: HTMLElement;

  beforeEach(() => {
    document.body.innerHTML = "";
    root = createDom();
    document.body.appendChild(root);
    mockFetchInstant.mockReset();
    mockFetchLlm.mockReset();
  });

  it("renders citation cards from view models", () => {
    const sheet = mockSheet();
    const panel = mountMobileNormativaPanel(root, sheet);
    panel.setCitations(createCitations());
    const cards = root.querySelectorAll(".mobile-citation-card");
    expect(cards.length).toBe(2);
    expect(cards[0].querySelector(".mobile-citation-card-title")!.textContent).toContain("Estatuto Tributario Art. 240");
  });

  it("shows empty state when no citations", () => {
    const sheet = mockSheet();
    const panel = mountMobileNormativaPanel(root, sheet);
    panel.setCitations([]);
    const empty = root.querySelector<HTMLElement>("#mobile-normativa-empty")!;
    expect(empty.hidden).toBe(false);
    expect(root.querySelectorAll(".mobile-citation-card").length).toBe(0);
  });

  it("clear resets the panel", () => {
    const sheet = mockSheet();
    const panel = mountMobileNormativaPanel(root, sheet);
    panel.setCitations(createCitations());
    expect(root.querySelectorAll(".mobile-citation-card").length).toBe(2);
    panel.clear();
    expect(root.querySelectorAll(".mobile-citation-card").length).toBe(0);
    expect(root.querySelector<HTMLElement>("#mobile-normativa-empty")!.hidden).toBe(false);
  });

  it("citation meta is extracted correctly", () => {
    const sheet = mockSheet();
    const panel = mountMobileNormativaPanel(root, sheet);
    panel.setCitations(createCitations());
    const meta = root.querySelector(".mobile-citation-card-meta");
    expect(meta?.textContent).toContain("Normativa | DIAN");
  });

  it("calls fetchCitationProfileInstant and renders rich profile content", async () => {
    mockFetchInstant.mockResolvedValueOnce(makeProfile());
    const sheet = mockSheet();
    const panel = mountMobileNormativaPanel(root, sheet);
    panel.setCitations(createCitations());
    root.querySelector<HTMLElement>(".mobile-citation-card")!.click();
    await vi.waitFor(() => { expect(mockFetchInstant).toHaveBeenCalledWith({ doc_id: "et_art_240", reference_key: "et:240" }); });
    const openCalls = (sheet.open as ReturnType<typeof vi.fn>).mock.calls;
    const lastCall = openCalls[openCalls.length - 1][0];
    expect(lastCall.title).toBe("Estatuto Tributario Art. 240");
    expect(lastCall.html).toContain("Datos clave");
    expect(lastCall.html).toContain("Impacto tributario");
    expect(lastCall.html).toContain("Texto original del art");
    expect(lastCall.html).toContain("sociedades nacionales");
    expect(lastCall.html).toContain("Ver documento original");
  });

  it("renders binding force badge from API profile", async () => {
    mockFetchInstant.mockResolvedValueOnce(makeProfile({ binding_force: "Compilación tributaria vigente" }));
    const sheet = mockSheet();
    const panel = mountMobileNormativaPanel(root, sheet);
    panel.setCitations(createCitations());
    root.querySelector<HTMLElement>(".mobile-citation-card")!.click();
    await vi.waitFor(() => { expect(mockFetchInstant).toHaveBeenCalled(); });
    const openCalls = (sheet.open as ReturnType<typeof vi.fn>).mock.calls;
    const lastCall = openCalls[openCalls.length - 1][0];
    // Renderer should wrap the raw taxonomy value with the authority prefix.
    expect(lastCall.subtitle).toBe("Fuerza vinculante: Compilación tributaria vigente");
    expect(lastCall.html).toContain("mobile-sheet-badge");
    expect(lastCall.html).toContain("Fuerza vinculante: Compilación tributaria vigente");
    // Tone is driven by binding_force_rank (860 → success), not string
    // matching on the label. See normative_taxonomy.py.
    expect(lastCall.html).toContain('data-tone="success"');
  });

  it("drives badge tone from binding_force_rank tiers", async () => {
    // circular administrativa: rank 320 → "warning" tier
    mockFetchInstant.mockResolvedValueOnce(
      makeProfile({ binding_force: "Circular administrativa", binding_force_rank: 320 }),
    );
    const sheet = mockSheet();
    const panel = mountMobileNormativaPanel(root, sheet);
    panel.setCitations(createCitations());
    root.querySelector<HTMLElement>(".mobile-citation-card")!.click();
    await vi.waitFor(() => { expect(mockFetchInstant).toHaveBeenCalled(); });
    const openCalls = (sheet.open as ReturnType<typeof vi.fn>).mock.calls;
    const lastCall = openCalls[openCalls.length - 1][0];
    expect(lastCall.html).toContain('data-tone="warning"');
    expect(lastCall.html).toContain("Fuerza vinculante: Circular administrativa");
  });

  it("renders caution banner when present", async () => {
    mockFetchInstant.mockResolvedValueOnce(makeProfile({ caution_banner: { title: "Precaucion", body: "Esta norma fue derogada parcialmente.", tone: "warning" } }));
    const sheet = mockSheet();
    const panel = mountMobileNormativaPanel(root, sheet);
    panel.setCitations(createCitations());
    root.querySelector<HTMLElement>(".mobile-citation-card")!.click();
    await vi.waitFor(() => { expect(mockFetchInstant).toHaveBeenCalled(); });
    const openCalls = (sheet.open as ReturnType<typeof vi.fn>).mock.calls;
    const lastCall = openCalls[openCalls.length - 1][0];
    expect(lastCall.html).toContain("Precaucion");
    expect(lastCall.html).toContain("derogada parcialmente");
    expect(lastCall.html).toContain("mobile-sheet-caution");
  });

  it("renders additional depth sections as flat list with badges", async () => {
    mockFetchInstant.mockResolvedValueOnce(makeProfile());
    const sheet = mockSheet();
    const panel = mountMobileNormativaPanel(root, sheet);
    panel.setCitations(createCitations());
    root.querySelector<HTMLElement>(".mobile-citation-card")!.click();
    await vi.waitFor(() => { expect(mockFetchInstant).toHaveBeenCalled(); });
    const openCalls = (sheet.open as ReturnType<typeof vi.fn>).mock.calls;
    const lastCall = openCalls[openCalls.length - 1][0];
    expect(lastCall.html).toContain("Normativa relacionada");
    expect(lastCall.html).toContain("Decreto 2231");
    expect(lastCall.html).toContain("mobile-depth-list");
  });

  it("fetches LLM enrichment when needs_llm is true", async () => {
    const instantProfile = makeProfile({ needs_llm: true, lead: "Initial lead", sections: [] });
    const llmResult: CitationProfileResponse = { lead: "Enriched lead from LLM", sections: [{ id: "analysis", title: "Analisis profundo", body: "Contenido enriquecido." }] };
    mockFetchInstant.mockResolvedValueOnce(instantProfile);
    mockFetchLlm.mockResolvedValueOnce(llmResult);
    const sheet = mockSheet();
    const panel = mountMobileNormativaPanel(root, sheet);
    panel.setCitations(createCitations());
    root.querySelector<HTMLElement>(".mobile-citation-card")!.click();
    await vi.waitFor(() => { expect(mockFetchLlm).toHaveBeenCalled(); });
    const openCalls = (sheet.open as ReturnType<typeof vi.fn>).mock.calls;
    const lastCall = openCalls[openCalls.length - 1][0];
    expect(lastCall.html).toContain("Enriched lead from LLM");
    expect(lastCall.html).toContain("Analisis profundo");
  });

  it("keeps instant profile when LLM enrichment fails", async () => {
    mockFetchInstant.mockResolvedValueOnce(makeProfile({ needs_llm: true }));
    mockFetchLlm.mockRejectedValueOnce(new Error("LLM timeout"));
    const sheet = mockSheet();
    const panel = mountMobileNormativaPanel(root, sheet);
    panel.setCitations(createCitations());
    root.querySelector<HTMLElement>(".mobile-citation-card")!.click();
    await vi.waitFor(() => { expect(mockFetchLlm).toHaveBeenCalled(); });
    await new Promise((resolve) => setTimeout(resolve, 50));
    const openCalls = (sheet.open as ReturnType<typeof vi.fn>).mock.calls;
    const lastCall = openCalls[openCalls.length - 1][0];
    expect(lastCall.title).toBe("Estatuto Tributario Art. 240");
    expect(lastCall.html).toContain("Datos clave");
  });

  it("falls back to mention view when profile is skipped", async () => {
    mockFetchInstant.mockResolvedValueOnce(makeProfile({ skipped: true }));
    const sheet = mockSheet();
    const panel = mountMobileNormativaPanel(root, sheet);
    panel.setCitations(createCitations());
    root.querySelector<HTMLElement>(".mobile-citation-card")!.click();
    await vi.waitFor(() => { expect(mockFetchInstant).toHaveBeenCalled(); });
    const openCalls = (sheet.open as ReturnType<typeof vi.fn>).mock.calls;
    const lastCall = openCalls[openCalls.length - 1][0];
    expect(lastCall.html).toContain("fue mencionada en la respuesta de LIA");
  });

  it("falls back to error view when API call fails", async () => {
    mockFetchInstant.mockRejectedValueOnce(new Error("Network error"));
    const sheet = mockSheet();
    const panel = mountMobileNormativaPanel(root, sheet);
    panel.setCitations(createCitations());
    root.querySelector<HTMLElement>(".mobile-citation-card")!.click();
    await vi.waitFor(() => { expect(mockFetchInstant).toHaveBeenCalled(); });
    await new Promise((resolve) => setTimeout(resolve, 50));
    const openCalls = (sheet.open as ReturnType<typeof vi.fn>).mock.calls;
    const lastCall = openCalls[openCalls.length - 1][0];
    expect(lastCall.html).toContain("No fue posible cargar");
  });

  it("shows mention view for non-modal citations", () => {
    const sheet = mockSheet();
    const panel = mountMobileNormativaPanel(root, sheet);
    const citations: MobileCitationCardViewModel[] = [{ action: "mention", id: "res-167", meta: "Normograma DIAN", title: "Resolucion 167" }];
    panel.setCitations(citations);
    root.querySelector<HTMLElement>(".mobile-citation-card")!.click();
    const openCalls = (sheet.open as ReturnType<typeof vi.fn>).mock.calls;
    const lastCall = openCalls[openCalls.length - 1][0];
    expect(lastCall.html).toContain("Resolucion 167");
    expect(lastCall.html).toContain("no est");
  });

  it("shows mention view when rawCitation is missing", () => {
    const sheet = mockSheet();
    const panel = mountMobileNormativaPanel(root, sheet);
    const citations: MobileCitationCardViewModel[] = [{ action: "modal", id: "et-art-999", meta: "Normativa | DIAN", title: "ET Art. 999" }];
    panel.setCitations(citations);
    root.querySelector<HTMLElement>(".mobile-citation-card")!.click();
    const openCalls = (sheet.open as ReturnType<typeof vi.fn>).mock.calls;
    const lastCall = openCalls[openCalls.length - 1][0];
    expect(lastCall.html).toContain("fue mencionada en la respuesta de LIA");
  });

  it("hides desktop modal layer when opening citation sheet", async () => {
    mockFetchInstant.mockResolvedValueOnce(makeProfile());
    const sheet = mockSheet();
    const panel = mountMobileNormativaPanel(root, sheet);
    panel.setCitations(createCitations());
    const modalLayer = root.querySelector<HTMLElement>("#modal-layer")!;
    modalLayer.hidden = false;
    const modalNorma = root.querySelector<HTMLElement>("#modal-norma")!;
    modalNorma.classList.add("is-open");
    modalNorma.setAttribute("aria-hidden", "false");
    root.querySelector<HTMLElement>(".mobile-citation-card")!.click();
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(modalLayer.hidden).toBe(true);
    expect(modalNorma.classList.contains("is-open")).toBe(false);
    expect(modalNorma.getAttribute("aria-hidden")).toBe("true");
  });
});
