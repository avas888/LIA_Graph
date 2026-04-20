import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  createExpertPanelController,
  extractArticleRefs,
} from "@/features/chat/expertPanelController";

const Q6 =
  "Un contribuyente del RST puede acceder al beneficio de auditoria?";
const Q10 =
  "Que diferencia hay entre el regimen simple RST y el regimen ordinario para una SAS con ingresos de 3000 UVT?";

describe("extractArticleRefs", () => {
  it("extracts article numbers from Spanish text", () => {
    const text = "Según el artículo 147 del ET y el Art. 240...";
    const refs = extractArticleRefs(text);
    expect(refs).toContain("art_147");
    expect(refs).toContain("art_240");
  });

  it("extracts hyphenated article numbers used in tax subarticles", () => {
    const refs = extractArticleRefs("La respuesta cita el artículo 689-3 del ET.");
    expect(refs).toEqual(["art_689-3"]);
  });

  it("returns empty array when the text does not mention articles", () => {
    expect(extractArticleRefs("sin referencias normativas")).toEqual([]);
  });
});

function makeI18n() {
  return {
    t: (key: string, vars?: Record<string, string | number>) => {
      const map: Record<string, string> = {
        "chat.experts.defer": "Cuando encontremos interpretaciones de expertos relevantes, éstas aparecen aquí automáticamente.",
        "chat.experts.loading": "Buscando interpretaciones...",
        "chat.experts.empty": "No se encontraron interpretaciones relevantes de profesionales para tu consulta en nuestra base de datos especializada.",
        "chat.experts.error": "No se pudo cargar interpretaciones.",
        "chat.experts.refreshing": "Actualizando interpretaciones...",
        "chat.experts.refreshEmpty": "Se conservan las últimas interpretaciones disponibles.",
        "chat.experts.refreshError": "Se conservan las últimas interpretaciones disponibles.",
        "chat.experts.concordancia": "Coinciden",
        "chat.experts.divergencia": "Divergen",
        "chat.experts.complementario": "Complementario",
        "chat.experts.individual": "Perspectiva individual",
        "chat.experts.modal.title": "Lectura práctica del criterio",
        "chat.experts.card.open": "Abrir detalle",
        "chat.experts.detail.question": "Consulta del turno",
        "chat.experts.detail.reading": "Lectura práctica",
        "chat.experts.detail.checklist": "Qué revisar antes de cerrar",
        "chat.experts.detail.sources": "Fuentes consultadas",
        "chat.experts.detail.experts": "Interpretaciones de Expertos de Posible Relevancia:",
        "chat.experts.detail.expertOpen": "Ver análisis completo",
        "chat.experts.detail.expertClose": "Ocultar análisis",
        "chat.experts.detail.openSource": "Abrir fuente en LIA",
        "chat.experts.detail.externalLink": "Abrir enlace externo",
        "chat.experts.signal.permite": "Permite",
        "chat.experts.signal.restringe": "Restringe",
        "chat.experts.signal.condiciona": "Condiciona",
        "chat.experts.signal.neutral": "Contexto",
        "chat.experts.loadMore": "Buscar más interpretaciones ({count})",
        "chat.experts.loadMore.loading": "Buscando más…",
        "chat.experts.loadMore.retry": "Reintentar búsqueda",
      };
      const template = map[key] ?? key;
      if (!vars) return template;
      return template.replace(/\{(\w+)\}/g, (_match, name) => String(vars[name] ?? `{${name}}`));
    },
    locale: "es-CO",
  };
}

function makeNodes() {
  const contentNode = document.createElement("div");
  contentNode.id = "expert-panel-content";

  const statusNode = document.createElement("p");
  statusNode.id = "expert-panel-status";

  const detailModalNode = document.createElement("section");
  detailModalNode.id = "modal-expert-detail";

  const detailTitleNode = document.createElement("h3");
  detailTitleNode.id = "expert-detail-title";
  detailModalNode.appendChild(detailTitleNode);

  const detailContentNode = document.createElement("div");
  detailContentNode.id = "expert-detail-content";
  detailModalNode.appendChild(detailContentNode);

  document.body.append(contentNode, statusNode, detailModalNode);
  return { contentNode, statusNode, detailModalNode, detailTitleNode, detailContentNode };
}

const MOCK_RESPONSE_Q6 = {
  ok: true,
  groups: [
    {
      article_ref: "et_art_689_3",
      classification: "concordancia",
      summary_signal: "El beneficio de auditoría no procede para contribuyentes del RST.",
      requested_match: true,
      panel_rank: 1,
      snippets: [
        {
          doc_id: "d801",
          authority: "DIAN",
          title: "Oficio 801/2022",
          snippet:
            "No procede el beneficio de auditoría para los sujetos del RST, porque el artículo 689-3 está diseñado para renta del régimen ordinario.",
          position_signal: "restringe",
          relevance_score: 0.93,
          trust_tier: "high",
          provider_links: [{ url: "https://www.dian.gov.co/oficio801", label: "DIAN", provider: "DIAN" }],
          requested_match: true,
          panel_rank: 1,
        },
        {
          doc_id: "deloitte_rst",
          authority: "Deloitte",
          title: "Tax alert RST 2025",
          snippet:
            "No procede extender el beneficio de auditoría al RST; la lectura práctica es excluirlo del cierre tributario ordinario.",
          position_signal: "restringe",
          relevance_score: 0.84,
          trust_tier: "medium",
          provider_links: [{ url: "https://www2.deloitte.com/co/rst", label: "Deloitte", provider: "Deloitte" }],
          requested_match: true,
          panel_rank: 1,
        },
      ],
    },
  ],
  ungrouped: [],
  total_available: 1,
  has_more: false,
  next_offset: null,
  trace_id: "trace_q6",
};

const MOCK_RESPONSE_MIXED = {
  ok: true,
  groups: [
    {
      article_ref: "et_art_240",
      classification: "divergencia",
      summary_signal: "La tarifa reducida no tiene una sola lectura: una postura la admite y otra la niega si la entidad sigue en el RST.",
      panel_rank: 2,
      snippets: [
        {
          doc_id: "tarifa_dian",
          authority: "DIAN",
          title: "Concepto tarifa general",
          snippet: "Se permite tomar la tarifa general en el escenario descrito.",
          position_signal: "permite",
          relevance_score: 0.96,
          trust_tier: "high",
          provider_links: [],
          panel_rank: 2,
        },
        {
          doc_id: "tarifa_ey",
          authority: "EY",
          title: "Análisis EY",
          snippet: "No procede la tarifa general si la entidad permanece en el RST.",
          position_signal: "restringe",
          relevance_score: 0.87,
          trust_tier: "medium",
          provider_links: [],
          panel_rank: 2,
        },
      ],
    },
    {
      article_ref: "et_art_147",
      classification: "concordancia",
      summary_signal: "Las pérdidas pueden compensarse bajo la regla vigente cuando están determinadas y soportadas.",
      requested_match: true,
      panel_rank: 1,
      snippets: [
        {
          doc_id: "perdidas_dian",
          authority: "DIAN",
          title: "Concepto 6038/2024",
          snippet: "Se permite compensar las pérdidas fiscales en los términos del artículo 147.",
          position_signal: "permite",
          relevance_score: 0.74,
          trust_tier: "high",
          provider_links: [],
          requested_match: true,
          panel_rank: 1,
        },
        {
          doc_id: "perdidas_pwc",
          authority: "PwC",
          title: "Guía pérdidas fiscales",
          snippet: "Procede la compensación cuando la pérdida está determinada y soportada.",
          position_signal: "permite",
          relevance_score: 0.7,
          trust_tier: "medium",
          provider_links: [],
          requested_match: true,
          panel_rank: 1,
        },
      ],
    },
  ],
  ungrouped: [
    {
      doc_id: "rst_individual",
      authority: "Actualícese",
      title: "Lectura operativa RST",
      snippet: "Depende del flujo operativo y de si la empresa migrará de régimen.",
      position_signal: "condiciona",
      relevance_score: 0.6,
      trust_tier: "medium",
      provider_links: [],
      panel_rank: 3,
    },
  ],
  total_available: 4,
  has_more: false,
  next_offset: null,
  trace_id: "trace_q10",
};

const MOCK_RESPONSE_HAS_MORE = {
  ok: true,
  groups: [
    {
      article_ref: "et_art_689_3",
      classification: "concordancia" as const,
      summary_signal: "El beneficio de auditoría no procede para contribuyentes del RST.",
      requested_match: true,
      panel_rank: 1,
      snippets: [
        {
          doc_id: "d801",
          authority: "DIAN",
          title: "Oficio 801/2022",
          snippet: "No procede el beneficio de auditoría para los sujetos del RST.",
          position_signal: "restringe",
          relevance_score: 0.93,
          trust_tier: "high",
          provider_links: [],
          requested_match: true,
          panel_rank: 1,
        },
        {
          doc_id: "deloitte_rst",
          authority: "Deloitte",
          title: "Tax alert RST 2025",
          snippet: "No procede extender el beneficio de auditoría al RST.",
          position_signal: "restringe",
          relevance_score: 0.84,
          trust_tier: "medium",
          provider_links: [],
          requested_match: true,
          panel_rank: 1,
        },
      ],
    },
  ],
  ungrouped: [],
  total_available: 3,
  has_more: true,
  next_offset: 1,
  trace_id: "trace_has_more",
};

const MOCK_RESPONSE_EXPANDED = {
  ok: true,
  groups: [
    {
      article_ref: "et_art_689_3",
      classification: "concordancia" as const,
      summary_signal: "El beneficio de auditoría no procede para contribuyentes del RST.",
      snippets: [
        {
          doc_id: "d801",
          authority: "DIAN",
          title: "Oficio 801/2022",
          snippet: "No procede el beneficio de auditoría para los sujetos del RST.",
          position_signal: "restringe",
          relevance_score: 0.93,
          trust_tier: "high",
          provider_links: [],
        },
        {
          doc_id: "deloitte_rst",
          authority: "Deloitte",
          title: "Tax alert RST 2025",
          snippet: "No procede extender el beneficio de auditoría al RST.",
          position_signal: "restringe",
          relevance_score: 0.84,
          trust_tier: "medium",
          provider_links: [],
        },
      ],
    },
  ],
  ungrouped: [
    {
      doc_id: "extra_1",
      authority: "Actualícese",
      title: "Lectura complementaria RST",
      snippet: "Depende del flujo operativo del contribuyente.",
      position_signal: "condiciona",
      relevance_score: 0.55,
      trust_tier: "medium",
      provider_links: [],
      panel_rank: 2,
    },
    {
      doc_id: "extra_2",
      authority: "Gerencie",
      title: "Guía RST",
      snippet: "Considera el contexto del régimen simplificado.",
      position_signal: "neutral",
      relevance_score: 0.42,
      trust_tier: "low",
      provider_links: [],
      panel_rank: 3,
    },
  ],
  total_available: 3,
  has_more: false,
  next_offset: null,
  trace_id: "trace_expanded",
};

/** Build a fetch mock that routes /enhance to return curated relevancia for every card. */
function mockFetchWithEnhance(panelResponse: Record<string, unknown>) {
  return vi.fn().mockImplementation((url: string) => {
    if (String(url).includes("/enhance")) {
      // Derive card IDs from the response: groups → "group:{article_ref}", ungrouped → "single:{doc_id}"
      const groups = (panelResponse.groups || []) as Array<{ article_ref: string }>;
      const ungrouped = (panelResponse.ungrouped || []) as Array<{ doc_id: string }>;
      const enhancements = [
        ...groups.map((g) => ({
          card_id: `group:${g.article_ref}`,
          posible_relevancia: "Relevante para la consulta del contador.",
          resumen_nutshell: "Resumen curado de la interpretación.",
          es_relevante: true,
        })),
        ...ungrouped.map((s) => ({
          card_id: `single:${s.doc_id}`,
          posible_relevancia: "Relevante para la consulta del contador.",
          resumen_nutshell: "Resumen curado de la interpretación.",
          es_relevante: true,
        })),
      ];
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ ok: true, enhancements }) });
    }
    return Promise.resolve({ ok: true, json: () => Promise.resolve(panelResponse) });
  });
}

describe("createExpertPanelController", () => {
  let contentNode: HTMLElement;
  let statusNode: HTMLElement;
  let detailModalNode: HTMLElement;
  let detailTitleNode: HTMLElement;
  let detailContentNode: HTMLElement;

  beforeEach(() => {
    const nodes = makeNodes();
    contentNode = nodes.contentNode;
    statusNode = nodes.statusNode;
    detailModalNode = nodes.detailModalNode;
    detailTitleNode = nodes.detailTitleNode;
    detailContentNode = nodes.detailContentNode;
  });

  afterEach(() => {
    document.body.innerHTML = "";
    vi.restoreAllMocks();
  });

  it("renders accountant-first cards for ranking question Q6", async () => {
    vi.stubGlobal("fetch", mockFetchWithEnhance(MOCK_RESPONSE_Q6));

    const controller = createExpertPanelController({
      i18n: makeI18n() as never,
      contentNode,
      statusNode,
      detailModalNode,
      openModal: (modal) => modal.classList.add("is-open"),
    });

    await controller.load({
      traceId: "trace_q6",
      message: Q6,
      normativeArticleRefs: ["art_689-3"],
    });

    const cards = contentNode.querySelectorAll(".expert-card");
    expect(cards).toHaveLength(1);
    expect(contentNode.textContent || "").toContain("ET artículo 689-3");
    expect(contentNode.textContent || "").toContain("2 fuentes");
  });

  it("opens a practical detail modal with per-expert tabs that reveal real prose on click", async () => {
    vi.stubGlobal("fetch", mockFetchWithEnhance(MOCK_RESPONSE_Q6));

    const controller = createExpertPanelController({
      i18n: makeI18n() as never,
      contentNode,
      statusNode,
      detailModalNode,
      openModal: (modal) => modal.classList.add("is-open"),
    });

    await controller.load({
      traceId: "trace_q6",
      message: Q6,
      normativeArticleRefs: ["art_689-3"],
    });

    (contentNode.querySelector(".expert-card") as HTMLElement).click();

    expect(detailModalNode.classList.contains("is-open")).toBe(true);
    expect(detailTitleNode.textContent || "").toContain("beneficio de auditoría no procede");
    // "Consulta del turno" is intentionally NOT rendered — the user already
    // knows the question they asked; showing it back is plumbing.
    expect(detailContentNode.textContent || "").not.toContain(Q6);
    // "Posible relevancia" is also omitted — the card's presence IS the
    // signal of relevance, restating it is redundant.
    expect(detailContentNode.textContent || "").not.toContain("Posible relevancia");
    expect(detailContentNode.textContent || "").toContain("Qué revisar antes de cerrar");
    expect(detailContentNode.textContent || "").toContain(
      "Interpretaciones de Expertos de Posible Relevancia:",
    );

    // Per-expert tabs render — one per source — and start collapsed.
    // The eyebrow chip (DIAN, Deloitte) identifies the source; the snippet
    // title field is intentionally not rendered as a separate subtitle to
    // avoid duplicating the modal heading.
    const tabs = detailContentNode.querySelectorAll(".expert-detail-tab");
    expect(tabs.length).toBe(2);
    const eyebrowText = Array.from(detailContentNode.querySelectorAll(".expert-detail-tab-authority"))
      .map((el) => el.textContent || "")
      .join(" ");
    expect(eyebrowText).toContain("DIAN");
    expect(eyebrowText).toContain("Deloitte");
    const firstTab = tabs[0] as HTMLElement;
    const firstHeader = firstTab.querySelector(".expert-detail-tab-header") as HTMLButtonElement;
    const firstBody = firstTab.querySelector(".expert-detail-tab-body") as HTMLElement;
    expect(firstBody.hidden).toBe(true);
    expect(firstHeader.getAttribute("aria-expanded")).toBe("false");

    // Clicking expands the tab — no LLM round-trip; the snippet text is rendered directly.
    firstHeader.click();
    expect(firstBody.hidden).toBe(false);
    expect(firstHeader.getAttribute("aria-expanded")).toBe("true");
    expect(firstTab.classList.contains("expert-detail-tab--expanded")).toBe(true);

    // The expanded body contains real expert text from snippet/extended_excerpt
    // (the test fixture provides `snippet` since the mock has no extended_excerpt).
    const proseText = firstBody.textContent || "";
    expect(proseText).toContain("beneficio de auditoría");
  });

  it("prioritizes the article requested by the chat answer over unrelated expert groups", async () => {
    vi.stubGlobal("fetch", mockFetchWithEnhance(MOCK_RESPONSE_MIXED));

    const controller = createExpertPanelController({
      i18n: makeI18n() as never,
      contentNode,
      statusNode,
      detailModalNode,
      openModal: (modal) => modal.classList.add("is-open"),
    });

    await controller.load({
      traceId: "trace_q10",
      message: Q10,
      normativeArticleRefs: ["art_147"],
    });

    const firstCardText = contentNode.querySelector(".expert-card")?.textContent || "";
    expect(firstCardText).toContain("ET artículo 147");
  });

  it("shows a loading state while the request is in flight", () => {
    vi.stubGlobal("fetch", vi.fn().mockReturnValue(new Promise(() => {})));

    const controller = createExpertPanelController({
      i18n: makeI18n() as never,
      contentNode,
      statusNode,
    });

    void controller.load({ traceId: "trace_loading", message: "test" });
    expect(contentNode.querySelector(".expert-panel-spinner")).toBeTruthy();
  });

  it("shows an empty state when there are no expert results", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            ok: true,
            groups: [],
            ungrouped: [],
          }),
      }),
    );

    const controller = createExpertPanelController({
      i18n: makeI18n() as never,
      contentNode,
      statusNode,
    });

    await controller.load({ traceId: "trace_empty", message: "test" });
    expect(statusNode.textContent).toContain("No se encontraron");
  });

  it("returns to the idle state on clear", async () => {
    vi.stubGlobal("fetch", mockFetchWithEnhance(MOCK_RESPONSE_Q6));

    const controller = createExpertPanelController({
      i18n: makeI18n() as never,
      contentNode,
      statusNode,
      detailModalNode,
      openModal: (modal) => modal.classList.add("is-open"),
    });

    await controller.load({ traceId: "trace_q6", message: Q6 });
    expect(contentNode.children.length).toBeGreaterThan(0);

    controller.clear();
    expect(contentNode.innerHTML).toBe("");
    expect(statusNode.textContent).toContain("aparecen aquí automáticamente");
    expect(detailTitleNode.textContent).toBe("Lectura práctica del criterio");
  });

  it("sends process_limit=5 in the initial request", async () => {
    const fetchSpy = mockFetchWithEnhance(MOCK_RESPONSE_Q6);
    vi.stubGlobal("fetch", fetchSpy);

    const controller = createExpertPanelController({
      i18n: makeI18n() as never,
      contentNode,
      statusNode,
    });

    await controller.load({ traceId: "trace_limit", message: Q6 });

    const callBody = JSON.parse(fetchSpy.mock.calls[0][1].body);
    expect(callBody.process_limit).toBe(5);
    expect(callBody.top_k).toBe(12);
  });

  it("includes a compact search seed in the expert-panel request body", async () => {
    const fetchSpy = mockFetchWithEnhance(MOCK_RESPONSE_Q6);
    vi.stubGlobal("fetch", fetchSpy);

    const controller = createExpertPanelController({
      i18n: makeI18n() as never,
      contentNode,
      statusNode,
    });

    await controller.load({
      traceId: "trace_seed",
      message: Q6,
      assistantAnswer: "La respuesta final concluye que no procede por el artículo 689-3 del ET.",
      searchSeed:
        "Consulta: Un contribuyente del RST puede acceder al beneficio de auditoria?\nTesis: No procede por el artículo 689-3 del ET.",
      searchSeedOrigin: "deterministic",
    });

    const callBody = JSON.parse(fetchSpy.mock.calls[0][1].body);
    expect(callBody.search_seed).toContain("Tesis:");
    expect(callBody.search_seed_origin).toBe("deterministic");
  });

  it("shows a 'load more' button when has_more is true", async () => {
    vi.stubGlobal("fetch", mockFetchWithEnhance(MOCK_RESPONSE_HAS_MORE));

    const controller = createExpertPanelController({
      i18n: makeI18n() as never,
      contentNode,
      statusNode,
    });

    await controller.load({ traceId: "trace_has_more", message: Q6 });

    const moreBtn = contentNode.querySelector(".expert-panel-more-btn");
    expect(moreBtn).toBeTruthy();
    expect(moreBtn?.textContent).toContain("Buscar más interpretaciones");
  });

  it("does not show 'load more' button when has_more is false", async () => {
    vi.stubGlobal("fetch", mockFetchWithEnhance(MOCK_RESPONSE_Q6));

    const controller = createExpertPanelController({
      i18n: makeI18n() as never,
      contentNode,
      statusNode,
    });

    await controller.load({ traceId: "trace_q6", message: Q6 });

    const moreBtn = contentNode.querySelector(".expert-panel-more-btn");
    expect(moreBtn).toBeNull();
  });

  it("fetches the next page with process_limit=3 and offset when 'load more' is clicked", async () => {
    let panelCallCount = 0;
    function enhanceFor(response: Record<string, unknown>) {
      const groups = (response.groups || []) as Array<{ article_ref: string }>;
      const ungrouped = (response.ungrouped || []) as Array<{ doc_id: string }>;
      return [
        ...groups.map((g) => ({ card_id: `group:${g.article_ref}`, posible_relevancia: "Relevante.", resumen_nutshell: "Resumen.", es_relevante: true })),
        ...ungrouped.map((s) => ({ card_id: `single:${s.doc_id}`, posible_relevancia: "Relevante.", resumen_nutshell: "Resumen.", es_relevante: true })),
      ];
    }
    const fetchSpy = vi.fn().mockImplementation((url: string) => {
      if (String(url).includes("/enhance")) {
        // Return enhancements for all known cards (merged responses)
        const all = [...enhanceFor(MOCK_RESPONSE_HAS_MORE), ...enhanceFor(MOCK_RESPONSE_EXPANDED)];
        return Promise.resolve({ ok: true, json: () => Promise.resolve({ ok: true, enhancements: all }) });
      }
      panelCallCount++;
      const data = panelCallCount === 1 ? MOCK_RESPONSE_HAS_MORE : MOCK_RESPONSE_EXPANDED;
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(data),
      });
    });
    vi.stubGlobal("fetch", fetchSpy);

    const controller = createExpertPanelController({
      i18n: makeI18n() as never,
      contentNode,
      statusNode,
    });

    await controller.load({ traceId: "trace_expand", message: Q6 });

    const moreBtn = contentNode.querySelector(".expert-panel-more-btn") as HTMLButtonElement;
    expect(moreBtn).toBeTruthy();

    moreBtn.click();
    // Wait for async loadMore to complete (2 panel calls, enhance calls are extra)
    await vi.waitFor(() => {
      expect(panelCallCount).toBe(2);
    });

    // Find the second /api/expert-panel call (not the enhance calls)
    const panelCalls = fetchSpy.mock.calls.filter(([url]: [string]) => !String(url).includes("/enhance"));
    const secondCallBody = JSON.parse(panelCalls[1][1].body);
    expect(secondCallBody.process_limit).toBe(3);
    expect(secondCallBody.offset).toBe(1);
    expect(secondCallBody.top_k).toBe(12);

    // After expansion, the "load more" button should be gone
    await vi.waitFor(() => {
      expect(contentNode.querySelector(".expert-panel-more-btn")).toBeNull();
    });

    // Should have more cards than before (groups + ungrouped)
    const cards = contentNode.querySelectorAll(".expert-card");
    expect(cards.length).toBe(3);
  });

  it("keeps the last populated cards when a same-trace refresh returns empty", async () => {
    let panelCallCount = 0;
    vi.stubGlobal("fetch", vi.fn().mockImplementation((url: string) => {
      if (String(url).includes("/enhance")) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve({
          ok: true,
          enhancements: [{ card_id: "group:et_art_689_3", posible_relevancia: "Relevante.", resumen_nutshell: "Resumen.", es_relevante: true }],
        }) });
      }
      panelCallCount++;
      const data = panelCallCount === 1 ? MOCK_RESPONSE_Q6 : { ok: true, groups: [], ungrouped: [] };
      return Promise.resolve({ ok: true, json: () => Promise.resolve(data) });
    }));

    const controller = createExpertPanelController({
      i18n: makeI18n() as never,
      contentNode,
      statusNode,
    });

    await controller.load({ traceId: "trace_q6", message: Q6 });
    expect(contentNode.textContent || "").toContain("ET artículo 689-3");

    await controller.load({ traceId: "trace_q6", message: Q6, searchSeed: "seed refresh" });

    expect(contentNode.textContent || "").toContain("ET artículo 689-3");
    expect(statusNode.textContent || "").toContain("últimas interpretaciones disponibles");
    expect(controller.getPersistedState()?.status).toBe("populated");
  });

  it("keeps the last populated cards when a same-trace refresh errors", async () => {
    let panelCallCount = 0;
    vi.stubGlobal("fetch", vi.fn().mockImplementation((url: string) => {
      if (String(url).includes("/enhance")) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve({
          ok: true,
          enhancements: [{ card_id: "group:et_art_689_3", posible_relevancia: "Relevante.", resumen_nutshell: "Resumen.", es_relevante: true }],
        }) });
      }
      panelCallCount++;
      if (panelCallCount === 1) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(MOCK_RESPONSE_Q6) });
      }
      return Promise.reject(new Error("network_down"));
    }));

    const controller = createExpertPanelController({
      i18n: makeI18n() as never,
      contentNode,
      statusNode,
    });

    await controller.load({ traceId: "trace_q6", message: Q6 });
    await controller.load({ traceId: "trace_q6", message: Q6, searchSeed: "seed refresh" });

    expect(contentNode.textContent || "").toContain("ET artículo 689-3");
    expect(statusNode.textContent || "").toContain("últimas interpretaciones disponibles");
    expect(controller.getPersistedState()?.status).toBe("populated");
  });

  it("renderCard sets data-card-id on each rendered card button", async () => {
    vi.stubGlobal("fetch", mockFetchWithEnhance(MOCK_RESPONSE_Q6));

    const controller = createExpertPanelController({
      i18n: makeI18n() as never,
      contentNode,
      statusNode,
    });

    await controller.load({ traceId: "trace_cardid", message: Q6 });

    const cards = contentNode.querySelectorAll<HTMLElement>(".expert-card");
    expect(cards.length).toBeGreaterThan(0);
    for (const card of cards) {
      expect(card.dataset.cardId).toBeTruthy();
    }
    // The group card id should encode the article ref
    const groupCard = cards[0];
    expect(groupCard.dataset.cardId).toContain("689");
  });

  it("load waits for enhancement and renders curated cards with relevancia and nutshell", async () => {
    let enhanceResolve!: (value: unknown) => void;
    const enhancePromise = new Promise((res) => { enhanceResolve = res; });

    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((url: string) => {
        if (String(url).includes("/enhance")) {
          return enhancePromise.then(() => ({
            ok: true,
            json: () => Promise.resolve({
              ok: true,
              enhancements: [
                {
                  card_id: "group:et_art_689_3",
                  posible_relevancia: "Relevante porque trata el beneficio de auditoría en el RST.",
                  resumen_nutshell: "El artículo 689-3 no aplica al RST según criterio uniforme de las fuentes.",
                },
              ],
            }),
          }));
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(MOCK_RESPONSE_Q6),
        });
      }),
    );

    const controller = createExpertPanelController({
      i18n: makeI18n() as never,
      contentNode,
      statusNode,
    });

    // Start load (blocks on enhance) and resolve enhance concurrently
    const loadPromise = controller.load({ traceId: "trace_enhance_dom", message: Q6 });
    enhanceResolve(undefined);
    await loadPromise;

    // Cards render with enhancements already applied (curated-first)
    const card = contentNode.querySelector<HTMLElement>('[data-card-id="group:et_art_689_3"]');
    expect(card).toBeTruthy();
    const relevanciaEl = card!.querySelector<HTMLElement>(".expert-card-relevancia");
    const nutshellEl = card!.querySelector<HTMLElement>(".expert-card-nutshell");
    expect(relevanciaEl).toBeTruthy();
    expect(nutshellEl).toBeTruthy();

    expect(relevanciaEl!.hidden).toBe(false);
    expect(relevanciaEl!.textContent).toContain("beneficio de auditoría");
    expect(relevanciaEl!.classList.contains("expert-card-relevancia--visible")).toBe(true);
    expect(nutshellEl!.hidden).toBe(false);
    expect(nutshellEl!.textContent).toContain("689-3");
    expect(nutshellEl!.classList.contains("expert-card-nutshell--visible")).toBe(true);

    // Title should be hidden when nutshell is present
    const titleEl = card!.querySelector<HTMLElement>(".expert-card-title");
    expect(titleEl!.hidden).toBe(true);
  });
});
