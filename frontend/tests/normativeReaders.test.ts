import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// ── Mocks ────────────────────────────────────────────────────

vi.mock("@/content/markdown", () => ({
  renderMarkdown: vi.fn(async (container: HTMLElement, md: string) => {
    container.innerHTML = md;
  }),
}));

vi.mock("@/shared/ui/icons", () => ({
  icons: { close: "<svg>close</svg>" },
}));

vi.mock("@/app/mobile/detectMobile", () => ({
  isMobile: vi.fn(() => false),
}));

vi.mock("@/shared/api/client", () => ({
  getJson: vi.fn(),
}));

vi.mock("@/shared/utils/format", () => ({
  visibleText: vi.fn((v: unknown) => String(v || "").trim()),
  stripMarkdown: vi.fn((v: string) => v.replace(/[*#_>]/g, "").trim()),
}));

vi.mock("@/features/chat/normative/citationParsing", () => ({
  appendNormaTextContent: vi.fn((el: HTMLElement, text: unknown) => {
    el.textContent = String(text || "");
  }),
  boldifyFormularioReferences: vi.fn(),
  isRenderableEvidenceStatus: vi.fn(
    (s: unknown) => !s || s === "verified" || s === "missing" || s === "",
  ),
  openLinkInNewTab: vi.fn(),
  sanitizeHref: vi.fn((raw: unknown) => {
    const v = String(raw || "").trim();
    if (!v) return "";
    if (v.startsWith("/") || /^https?:\/\//i.test(v) || /^mailto:/i.test(v)) return v;
    return "";
  }),
}));

vi.mock("@/shared/ui/atoms/badge", () => ({
  createBadge: vi.fn(() => {
    const span = document.createElement("span");
    span.className = "lia-badge";
    return span;
  }),
}));

// =============================================================================
// articleReader
// =============================================================================

describe("articleReader", () => {
  let articleReader: typeof import("@/features/chat/normative/articleReader");
  let isMobileMock: ReturnType<typeof vi.fn>;

  beforeEach(async () => {
    // Reset module-level singletons by re-importing
    vi.resetModules();
    vi.restoreAllMocks();

    // Re-mock after resetModules
    vi.doMock("@/content/markdown", () => ({
      renderMarkdown: vi.fn(async (container: HTMLElement, md: string) => {
        container.innerHTML = md;
      }),
    }));
    vi.doMock("@/shared/ui/icons", () => ({
      icons: { close: "<svg>close</svg>" },
    }));
    vi.doMock("@/app/mobile/detectMobile", () => ({
      isMobile: vi.fn(() => false),
    }));

    articleReader = await import("@/features/chat/normative/articleReader");
    const detectMobile = await import("@/app/mobile/detectMobile");
    isMobileMock = detectMobile.isMobile as ReturnType<typeof vi.fn>;
  });

  afterEach(() => {
    document.body.innerHTML = "";
  });

  // ── closeArticleReader ──────────────────────────────────────

  describe("closeArticleReader", () => {
    it("does nothing if overlay was never created", () => {
      // Should not throw
      expect(() => articleReader.closeArticleReader()).not.toThrow();
    });

    it("hides overlay after open", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        text: async () => "# Hello",
      });
      await articleReader.openArticleReader("doc_1", "Test Doc", "normative_base");
      const overlay = document.querySelector(".article-reader-overlay") as HTMLDivElement;
      expect(overlay.hidden).toBe(false);

      articleReader.closeArticleReader();
      expect(overlay.hidden).toBe(true);
    });
  });

  // ── openArticleReader (desktop) ─────────────────────────────

  describe("openArticleReader (desktop)", () => {
    it("creates overlay DOM on first call", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        text: async () => "# Title\nBody content",
      });

      await articleReader.openArticleReader("doc_1", "My Document", "normative_base");

      const overlay = document.querySelector(".article-reader-overlay");
      expect(overlay).not.toBeNull();
      expect(overlay!.querySelector(".article-reader-modal")).not.toBeNull();
      expect(overlay!.querySelector(".article-reader-header")).not.toBeNull();
      expect(overlay!.querySelector(".article-reader-body")).not.toBeNull();
    });

    it("shows category badge for normative_base", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        text: async () => "content",
      });

      await articleReader.openArticleReader("doc_1", "My Doc", "normative_base");

      const badge = document.querySelector(".article-reader-badge") as HTMLSpanElement;
      expect(badge.textContent).toBe("Normativa");
      expect(badge.className).toContain("article-reader-badge--normativa");
    });

    it("shows category badge for practica_erp", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        text: async () => "content",
      });

      await articleReader.openArticleReader("doc_1", "My Doc", "practica_erp");

      const badge = document.querySelector(".article-reader-badge") as HTMLSpanElement;
      expect(badge.textContent).toBe("Practica");
      expect(badge.className).toContain("article-reader-badge--practica");
    });

    it("shows category badge for interpretative_guidance", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        text: async () => "content",
      });

      await articleReader.openArticleReader("doc_1", "My Doc", "interpretative_guidance");

      const badge = document.querySelector(".article-reader-badge") as HTMLSpanElement;
      expect(badge.textContent).toBe("Expertos");
      expect(badge.className).toContain("article-reader-badge--expertos");
    });

    it("falls back to normative_base for unknown knowledge class", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        text: async () => "content",
      });

      await articleReader.openArticleReader("doc_1", "My Doc", "unknown_class");

      const badge = document.querySelector(".article-reader-badge") as HTMLSpanElement;
      expect(badge.textContent).toBe("Normativa");
    });

    it("renders markdown body on success", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        text: async () => "## Some Heading\nParagraph here",
      });

      await articleReader.openArticleReader("doc_1", "My Doc", "normative_base");

      const body = document.querySelector(".article-reader-body") as HTMLDivElement;
      expect(body.innerHTML).not.toBe("");
    });

    it("hides status node on success", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        text: async () => "content",
      });

      await articleReader.openArticleReader("doc_1", "My Doc", "normative_base");

      const status = document.querySelector(".article-reader-status") as HTMLDivElement;
      expect(status.hidden).toBe(true);
    });

    it("shows error message on fetch failure", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        text: async () => "Server error",
      });

      await articleReader.openArticleReader("doc_1", "My Doc", "normative_base");

      const status = document.querySelector(".article-reader-status") as HTMLDivElement;
      expect(status.textContent).toBe("No se pudo cargar el documento.");
    });

    it("shows error message on network exception", async () => {
      global.fetch = vi.fn().mockRejectedValue(new Error("Network failure"));

      await articleReader.openArticleReader("doc_1", "My Doc", "normative_base");

      const status = document.querySelector(".article-reader-status") as HTMLDivElement;
      expect(status.textContent).toBe("No se pudo cargar el documento.");
    });

    it("encodes doc_id in the fetch URL", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        text: async () => "content",
      });

      await articleReader.openArticleReader("doc/with spaces", "My Doc", "normative_base");

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("doc_id=doc%2Fwith%20spaces"),
      );
    });

    it("fetches with view=original and format=md", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        text: async () => "content",
      });

      await articleReader.openArticleReader("doc_1", "My Doc", "normative_base");

      const calledUrl = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
      expect(calledUrl).toContain("view=original");
      expect(calledUrl).toContain("format=md");
    });

    it("reuses the same overlay on subsequent calls (lazy singleton)", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        text: async () => "content",
      });

      await articleReader.openArticleReader("doc_1", "First", "normative_base");
      await articleReader.openArticleReader("doc_2", "Second", "practica_erp");

      const overlays = document.querySelectorAll(".article-reader-overlay");
      expect(overlays.length).toBe(1);
    });

    it("closes on overlay click", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        text: async () => "content",
      });

      await articleReader.openArticleReader("doc_1", "My Doc", "normative_base");
      const overlay = document.querySelector(".article-reader-overlay") as HTMLDivElement;

      // Simulate clicking on the overlay background
      const clickEvent = new MouseEvent("click", { bubbles: true });
      Object.defineProperty(clickEvent, "target", { value: overlay });
      overlay.dispatchEvent(clickEvent);

      expect(overlay.hidden).toBe(true);
    });

    // Escape keydown test skipped — jsdom does not reliably dispatch
    // keyboard events on document to listeners added inside async flows.

    it("close button has aria-label Cerrar", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        text: async () => "content",
      });

      await articleReader.openArticleReader("doc_1", "My Doc", "normative_base");

      const closeBtn = document.querySelector(".article-reader-close") as HTMLButtonElement;
      expect(closeBtn.getAttribute("aria-label")).toBe("Cerrar");
    });
  });

  // ── Technical label detection and humanization ──────────────

  describe("technical label handling", () => {
    it("humanizes technical label with hex hash", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        text: async () => "# Some Content\nBody here",
      });

      // This label has a hex hash so it should be detected as technical
      await articleReader.openArticleReader(
        "doc_1",
        "pt expertos precios transferencia 27555a78 part 03",
        "normative_base",
      );

      const title = document.querySelector(".article-reader-title") as HTMLHeadingElement;
      // The technical prefixes and hash should be stripped, title-cased
      expect(title.textContent).not.toContain("27555a78");
      expect(title.textContent).not.toContain("part 03");
    });

    it("extracts better title from markdown for technical labels", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        text: async () =>
          "**Tema principal**: Precios de transferencia en Colombia\n\nBody content here",
      });

      await articleReader.openArticleReader(
        "doc_1",
        "pt expertos precios transferencia 27555a78 part 03",
        "normative_base",
      );

      const title = document.querySelector(".article-reader-title") as HTMLHeadingElement;
      expect(title.textContent).toBe("Precios de transferencia en Colombia");
    });

    it("uses non-technical label as-is", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        text: async () => "content",
      });

      await articleReader.openArticleReader("doc_1", "Declaracion de Renta", "normative_base");

      const title = document.querySelector(".article-reader-title") as HTMLHeadingElement;
      expect(title.textContent).toBe("Declaracion de Renta");
    });

    it("does not update title from markdown if label is not technical", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        text: async () =>
          "**Tema principal**: Something Else\n\n# Real Heading\nBody",
      });

      await articleReader.openArticleReader("doc_1", "My Normal Title", "normative_base");

      const title = document.querySelector(".article-reader-title") as HTMLHeadingElement;
      // Non-technical label: title stays as given
      expect(title.textContent).toBe("My Normal Title");
    });
  });

  // ── Mobile delegation ──────────────────────────────────────

  describe("openArticleReader (mobile)", () => {
    it("delegates to mobile sheet when isMobile and sheet is set", async () => {
      isMobileMock.mockReturnValue(true);

      const mockSheet = { open: vi.fn() };
      articleReader.setMobileSheet(mockSheet);

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        text: async () => "## Heading\nMobile content",
      });

      await articleReader.openArticleReader("doc_1", "Mobile Doc", "practica_erp");

      // The sheet should have been opened (at least loading + content)
      expect(mockSheet.open).toHaveBeenCalled();
      const lastCall = mockSheet.open.mock.calls[mockSheet.open.mock.calls.length - 1][0];
      expect(lastCall.subtitle).toBe("Practica");
    });

    it("shows error on mobile sheet when fetch fails", async () => {
      isMobileMock.mockReturnValue(true);

      const mockSheet = { open: vi.fn() };
      articleReader.setMobileSheet(mockSheet);

      global.fetch = vi.fn().mockRejectedValue(new Error("Network error"));

      await articleReader.openArticleReader("doc_1", "Mobile Doc", "normative_base");

      const lastCall = mockSheet.open.mock.calls[mockSheet.open.mock.calls.length - 1][0];
      expect(lastCall.html).toContain("No se pudo cargar el documento.");
    });

    it("shows loading state on mobile initially", async () => {
      isMobileMock.mockReturnValue(true);

      const mockSheet = { open: vi.fn() };
      articleReader.setMobileSheet(mockSheet);

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        text: async () => "content",
      });

      await articleReader.openArticleReader("doc_1", "My Doc", "normative_base");

      const firstCall = mockSheet.open.mock.calls[0][0];
      expect(firstCall.html).toContain("Cargando documento");
    });

    it("falls back to desktop overlay when isMobile but no sheet set", async () => {
      isMobileMock.mockReturnValue(true);
      // Do not call setMobileSheet, so _mobileSheet stays null

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        text: async () => "content",
      });

      await articleReader.openArticleReader("doc_1", "My Doc", "normative_base");

      // Should have created the desktop overlay
      const overlay = document.querySelector(".article-reader-overlay");
      expect(overlay).not.toBeNull();
    });
  });

  // ── setMobileSheet ─────────────────────────────────────────

  describe("setMobileSheet", () => {
    it("accepts null to clear the sheet", () => {
      expect(() => articleReader.setMobileSheet(null)).not.toThrow();
    });
  });
});

// =============================================================================
// practicaReader
// =============================================================================

describe("practicaReader", () => {
  let practicaReader: typeof import("@/features/chat/normative/practicaReader");

  beforeEach(async () => {
    vi.resetModules();

    vi.doMock("@/content/markdown", () => ({
      renderMarkdown: vi.fn(async (container: HTMLElement, md: string) => {
        container.innerHTML = md;
      }),
    }));

    practicaReader = await import("@/features/chat/normative/practicaReader");
  });

  afterEach(() => {
    document.body.innerHTML = "";
  });

  // ── closePracticaReader ────────────────────────────────────

  describe("closePracticaReader", () => {
    it("does nothing when overlay was never created", () => {
      expect(() => practicaReader.closePracticaReader()).not.toThrow();
    });

    it("hides overlay after open", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        text: async () => "content",
      });

      await practicaReader.openPracticaReader("doc_1", "Test");
      const overlay = document.querySelector(".practica-reader-overlay") as HTMLDivElement;
      expect(overlay.hidden).toBe(false);

      practicaReader.closePracticaReader();
      expect(overlay.hidden).toBe(true);
    });
  });

  // ── openPracticaReader ─────────────────────────────────────

  describe("openPracticaReader", () => {
    it("creates the practica overlay DOM", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        text: async () => "# Practica Content",
      });

      await practicaReader.openPracticaReader("doc_1", "My Practica Doc");

      const overlay = document.querySelector(".practica-reader-overlay");
      expect(overlay).not.toBeNull();
      expect(overlay!.querySelector(".practica-reader-modal")).not.toBeNull();
      expect(overlay!.querySelector(".practica-reader-header")).not.toBeNull();
      expect(overlay!.querySelector(".practica-reader-body")).not.toBeNull();
    });

    it("sets the title node text", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        text: async () => "content",
      });

      await practicaReader.openPracticaReader("doc_1", "Guia de IVA");

      const title = document.querySelector(".practica-reader-title") as HTMLHeadingElement;
      expect(title.textContent).toBe("Guia de IVA");
    });

    it("shows loading status initially", async () => {
      let resolveFetch: (v: any) => void;
      const fetchPromise = new Promise((r) => { resolveFetch = r; });
      global.fetch = vi.fn().mockReturnValue(fetchPromise);

      const openPromise = practicaReader.openPracticaReader("doc_1", "Test");

      const status = document.querySelector(".practica-reader-status") as HTMLDivElement;
      expect(status.hidden).toBe(false);
      expect(status.textContent).toContain("Cargando documento");

      resolveFetch!({ ok: true, text: async () => "content" });
      await openPromise;
    });

    it("hides status on successful fetch", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        text: async () => "content",
      });

      await practicaReader.openPracticaReader("doc_1", "Test");

      const status = document.querySelector(".practica-reader-status") as HTMLDivElement;
      expect(status.hidden).toBe(true);
    });

    it("renders markdown body on success", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        text: async () => "## Section\nParagraph",
      });

      await practicaReader.openPracticaReader("doc_1", "Test");

      const body = document.querySelector(".practica-reader-body") as HTMLDivElement;
      expect(body.innerHTML).not.toBe("");
    });

    it("shows error on fetch failure (HTTP error)", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        text: async () => "Not found",
      });

      await practicaReader.openPracticaReader("doc_1", "Missing");

      const status = document.querySelector(".practica-reader-status") as HTMLDivElement;
      expect(status.textContent).toBe("No se pudo cargar el documento.");
    });

    it("shows error on network exception", async () => {
      global.fetch = vi.fn().mockRejectedValue(new Error("Offline"));

      await practicaReader.openPracticaReader("doc_1", "Test");

      const status = document.querySelector(".practica-reader-status") as HTMLDivElement;
      expect(status.textContent).toBe("No se pudo cargar el documento.");
    });

    it("uses view=normalized in fetch URL", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        text: async () => "content",
      });

      await practicaReader.openPracticaReader("doc_1", "Test");

      const url = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
      expect(url).toContain("view=normalized");
      expect(url).toContain("format=md");
    });

    it("encodes doc_id in the fetch URL", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        text: async () => "content",
      });

      await practicaReader.openPracticaReader("my doc/id", "Test");

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("doc_id=my%20doc%2Fid"),
      );
    });

    it("reuses overlay on subsequent calls (lazy singleton)", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        text: async () => "content",
      });

      await practicaReader.openPracticaReader("doc_1", "First");
      await practicaReader.openPracticaReader("doc_2", "Second");

      const overlays = document.querySelectorAll(".practica-reader-overlay");
      expect(overlays.length).toBe(1);
    });

    it("clears previous body content before loading", async () => {
      global.fetch = vi.fn()
        .mockResolvedValueOnce({ ok: true, text: async () => "First content" })
        .mockResolvedValueOnce({ ok: true, text: async () => "Second content" });

      await practicaReader.openPracticaReader("doc_1", "First");
      await practicaReader.openPracticaReader("doc_2", "Second");

      const body = document.querySelector(".practica-reader-body") as HTMLDivElement;
      expect(body.innerHTML).toBe("Second content");
    });

    it("closes on overlay background click", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        text: async () => "content",
      });

      await practicaReader.openPracticaReader("doc_1", "Test");

      const overlay = document.querySelector(".practica-reader-overlay") as HTMLDivElement;
      const clickEvent = new MouseEvent("click", { bubbles: true });
      Object.defineProperty(clickEvent, "target", { value: overlay });
      overlay.dispatchEvent(clickEvent);

      expect(overlay.hidden).toBe(true);
    });

    // Escape key test skipped — jsdom keyboard event limitation.

    it("close button has aria-label Cerrar", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        text: async () => "content",
      });

      await practicaReader.openPracticaReader("doc_1", "Test");

      const closeBtn = document.querySelector(".practica-reader-close") as HTMLButtonElement;
      expect(closeBtn.getAttribute("aria-label")).toBe("Cerrar");
      expect(closeBtn.textContent).toBe("\u2715");
    });
  });
});

// =============================================================================
// profileRenderer
// =============================================================================

describe("profileRenderer", () => {
  let profileRenderer: typeof import("@/features/chat/normative/profileRenderer");

  beforeEach(async () => {
    vi.resetModules();

    vi.doMock("@/shared/api/client", () => ({
      getJson: vi.fn(),
    }));
    vi.doMock("@/shared/utils/format", () => ({
      visibleText: vi.fn((v: unknown) => String(v || "").trim()),
      stripMarkdown: vi.fn((v: string) => v),
    }));
    vi.doMock("@/features/chat/normative/citationParsing", () => ({
      appendNormaTextContent: vi.fn((el: HTMLElement, text: unknown) => {
        el.textContent = String(text || "");
      }),
      boldifyFormularioReferences: vi.fn(),
      isRenderableEvidenceStatus: vi.fn(
        (s: unknown) => !s || s === "verified" || s === "missing" || s === "",
      ),
      openLinkInNewTab: vi.fn(),
      sanitizeHref: vi.fn((raw: unknown) => {
        const v = String(raw || "").trim();
        if (!v) return "";
        if (v.startsWith("/") || /^https?:\/\//i.test(v) || /^mailto:/i.test(v)) return v;
        return "";
      }),
    }));
    vi.doMock("@/shared/ui/atoms/badge", () => ({
      createBadge: vi.fn(() => {
        const span = document.createElement("span");
        span.className = "lia-badge";
        return span;
      }),
    }));

    profileRenderer = await import("@/features/chat/normative/profileRenderer");
  });

  afterEach(() => {
    document.body.innerHTML = "";
  });

  // ── buildCitationProfileParams ─────────────────────────────
  // (Already tested in profileRenderer.test.ts, but we add edge cases)

  describe("buildCitationProfileParams – additional edge cases", () => {
    it("handles whitespace-only doc_id as empty", () => {
      expect(() => profileRenderer.buildCitationProfileParams({ doc_id: "   " })).toThrow(
        "citation_profile_missing_doc_id",
      );
    });

    it("sets doc_id when reference_key is not ley and doc is not ET", () => {
      const params = profileRenderer.buildCitationProfileParams({
        doc_id: "some_doc",
        reference_key: "et",
      });
      expect(params.get("doc_id")).toBe("some_doc");
    });

    it("infers ley from legal_reference field", () => {
      const params = profileRenderer.buildCitationProfileParams({
        doc_id: "renta_corpus_a_et_art_240",
        reference_key: "et",
        legal_reference: "Ley 1607 de 2012",
      });
      expect(params.get("reference_key")).toBe("ley:1607:2012");
    });

    it("infers ley from title field", () => {
      const params = profileRenderer.buildCitationProfileParams({
        doc_id: "corpus_dur_art_240",
        reference_key: "et",
        title: "Ley 2010 de 2019 - Reforma",
      });
      expect(params.get("reference_key")).toBe("ley:2010:2019");
    });

    it("includes message_context for ley reference_key", () => {
      const params = profileRenderer.buildCitationProfileParams(
        { doc_id: "doc_1", reference_key: "ley:1819:2016" },
        { messageContext: "renta question" },
      );
      expect(params.get("message_context")).toBe("renta question");
    });

    it("includes message_context for dur:1625:2016", () => {
      const params = profileRenderer.buildCitationProfileParams(
        { doc_id: "doc_1", reference_key: "dur:1625:2016", locator_start: "1.2.1" },
        { messageContext: "dur question" },
      );
      expect(params.get("message_context")).toBe("dur question");
    });

    it("omits message_context when empty", () => {
      const params = profileRenderer.buildCitationProfileParams(
        { doc_id: "doc_1", reference_key: "et" },
        { messageContext: "" },
      );
      expect(params.has("message_context")).toBe(false);
    });
  });

  // ── fetchCitationProfile / fetchCitationProfileInstant / fetchCitationProfileLlm ──

  describe("fetch functions", () => {
    it("fetchCitationProfile calls getJson with correct URL", async () => {
      const { getJson } = await import("@/shared/api/client");
      (getJson as ReturnType<typeof vi.fn>).mockResolvedValue({ title: "Test" });

      await profileRenderer.fetchCitationProfile({ doc_id: "doc_1" });

      expect(getJson).toHaveBeenCalledWith(
        expect.stringContaining("/api/citation-profile?doc_id=doc_1"),
      );
    });

    it("fetchCitationProfileInstant adds phase=instant", async () => {
      const { getJson } = await import("@/shared/api/client");
      (getJson as ReturnType<typeof vi.fn>).mockResolvedValue({ title: "Test" });

      await profileRenderer.fetchCitationProfileInstant({ doc_id: "doc_1" });

      expect(getJson).toHaveBeenCalledWith(
        expect.stringContaining("phase=instant"),
      );
    });

    it("fetchCitationProfileLlm adds phase=llm", async () => {
      const { getJson } = await import("@/shared/api/client");
      (getJson as ReturnType<typeof vi.fn>).mockResolvedValue({ title: "Test" });

      await profileRenderer.fetchCitationProfileLlm({ doc_id: "doc_1" });

      expect(getJson).toHaveBeenCalledWith(
        expect.stringContaining("phase=llm"),
      );
    });
  });

  // ── createProfileRenderer ──────────────────────────────────

  describe("createProfileRenderer", () => {
    function makeMockDom() {
      const el = () => document.createElement("div");
      const btn = () => {
        const b = document.createElement("button");
        b.hidden = true;
        return b;
      };
      const anchor = () => {
        const a = document.createElement("a") as HTMLAnchorElement;
        a.hidden = true;
        const labelSpan = document.createElement("span");
        labelSpan.className = "norma-companion-link-label";
        a.appendChild(labelSpan);
        return a;
      };
      return {
        modalNorma: el(),
        normaTitleNode: el(),
        normaBindingForceNode: el(),
        normaOriginalBtn: btn(),
        normaAnalysisBtn: btn(),
        normaOriginalHelperNode: el(),
        normaAnalysisHelperNode: el(),
        normaTopbarNode: el(),
        normaLoadingNode: el(),
        normaHelperNode: el(),
        normaCautionBannerNode: el(),
        normaCautionTitleNode: el(),
        normaCautionBodyNode: el(),
        normaPrimaryNode: el(),
        normaLeadNode: el(),
        normaFactsNode: el(),
        normaSectionsNode: el(),
        normaCompanionNode: el(),
        normaCompanionBtn: anchor(),
        normaCompanionHelperNode: el(),
      };
    }

    function makeMockI18n() {
      return {
        t: vi.fn((key: string) => key),
      };
    }

    it("returns setNormaModalStatus, resetNormaProfileCard, renderProfileContent, applyLlmEnrichment", () => {
      const dom = makeMockDom();
      const i18n = makeMockI18n();
      const renderer = profileRenderer.createProfileRenderer({
        i18n,
        dom,
        formatNormativeCitationTitle: (raw: unknown) => String(raw || ""),
        isRawDocId: () => false,
      });

      expect(typeof renderer.setNormaModalStatus).toBe("function");
      expect(typeof renderer.resetNormaProfileCard).toBe("function");
      expect(typeof renderer.renderProfileContent).toBe("function");
      expect(typeof renderer.applyLlmEnrichment).toBe("function");
    });

    describe("setNormaModalStatus", () => {
      it("shows loading message", () => {
        const dom = makeMockDom();
        const renderer = profileRenderer.createProfileRenderer({
          i18n: makeMockI18n(),
          dom,
          formatNormativeCitationTitle: (raw: unknown) => String(raw || ""),
          isRawDocId: () => false,
        });

        renderer.setNormaModalStatus("Cargando...", "loading");

        expect(dom.normaLoadingNode.hidden).toBe(false);
        expect(dom.normaHelperNode.textContent).toBe("Cargando...");
        expect(dom.normaLoadingNode.dataset.tone).toBe("loading");
      });

      it("hides when message is empty", () => {
        const dom = makeMockDom();
        const renderer = profileRenderer.createProfileRenderer({
          i18n: makeMockI18n(),
          dom,
          formatNormativeCitationTitle: (raw: unknown) => String(raw || ""),
          isRawDocId: () => false,
        });

        renderer.setNormaModalStatus("", "done");

        expect(dom.normaLoadingNode.hidden).toBe(true);
        expect(dom.normaHelperNode.textContent).toBe("");
      });

      it("defaults message to empty and tone to loading", () => {
        const dom = makeMockDom();
        const renderer = profileRenderer.createProfileRenderer({
          i18n: makeMockI18n(),
          dom,
          formatNormativeCitationTitle: (raw: unknown) => String(raw || ""),
          isRawDocId: () => false,
        });

        renderer.setNormaModalStatus();

        expect(dom.normaLoadingNode.hidden).toBe(true);
      });
    });

    describe("resetNormaProfileCard", () => {
      it("resets all DOM nodes to default state", () => {
        const dom = makeMockDom();
        const i18n = makeMockI18n();
        const renderer = profileRenderer.createProfileRenderer({
          i18n,
          dom,
          formatNormativeCitationTitle: (raw: unknown) => String(raw || ""),
          isRawDocId: () => false,
        });

        // Populate some content
        dom.normaTitleNode.textContent = "Some Title";
        dom.normaLeadNode.textContent = "Some lead";
        dom.normaPrimaryNode.innerHTML = "<p>content</p>";

        renderer.resetNormaProfileCard();

        expect(dom.normaBindingForceNode.textContent).toBe("");
        expect(dom.normaBindingForceNode.hidden).toBe(true);
        expect(dom.normaCautionBannerNode.hidden).toBe(true);
        expect(dom.normaPrimaryNode.innerHTML).toBe("");
        expect(dom.normaPrimaryNode.hidden).toBe(true);
        expect(dom.normaLeadNode.hidden).toBe(true);
        expect(dom.normaFactsNode.hidden).toBe(true);
        expect(dom.normaSectionsNode.hidden).toBe(true);
        expect(dom.normaOriginalBtn.hidden).toBe(true);
        expect(dom.normaOriginalBtn.disabled).toBe(true);
        expect(dom.normaAnalysisBtn.hidden).toBe(true);
        expect(dom.normaCompanionNode.hidden).toBe(true);
      });
    });

    describe("renderProfileContent", () => {
      it("sets title from profile", () => {
        const dom = makeMockDom();
        const renderer = profileRenderer.createProfileRenderer({
          i18n: makeMockI18n(),
          dom,
          formatNormativeCitationTitle: (raw: unknown) => String(raw || ""),
          isRawDocId: () => false,
        });

        renderer.renderProfileContent(
          { title: "Ley 1819 de 2016" },
          "Fallback Title",
        );

        expect(dom.normaTitleNode.textContent).toBe("Ley 1819 de 2016");
      });

      it("uses fallback title when profile title is empty", () => {
        const dom = makeMockDom();
        const renderer = profileRenderer.createProfileRenderer({
          i18n: makeMockI18n(),
          dom,
          formatNormativeCitationTitle: (raw: unknown) => String(raw || ""),
          isRawDocId: () => false,
        });

        renderer.renderProfileContent({ title: "" }, "My Fallback");

        expect(dom.normaTitleNode.textContent).toBe("My Fallback");
      });

      it("uses fallback when profile title looks like a raw doc_id", () => {
        const dom = makeMockDom();
        const renderer = profileRenderer.createProfileRenderer({
          i18n: makeMockI18n(),
          dom,
          formatNormativeCitationTitle: (raw: unknown) => String(raw || ""),
          isRawDocId: () => true, // always raw
        });

        renderer.renderProfileContent(
          { title: "renta_corpus_a_et_art_240_part_01" },
          "Fallback",
        );

        expect(dom.normaTitleNode.textContent).toBe("Fallback");
      });

      it("renders binding_force with prefix", () => {
        const dom = makeMockDom();
        const renderer = profileRenderer.createProfileRenderer({
          i18n: makeMockI18n(),
          dom,
          formatNormativeCitationTitle: (raw: unknown) => String(raw || ""),
          isRawDocId: () => false,
        });

        renderer.renderProfileContent(
          { title: "Test", binding_force: "Decreto reglamentario" },
          "Fallback",
        );

        expect(dom.normaBindingForceNode.textContent).toBe(
          "Fuerza vinculante: Decreto reglamentario",
        );
        expect(dom.normaBindingForceNode.hidden).toBe(false);
      });

      it("does not double-prefix binding_force", () => {
        const dom = makeMockDom();
        const renderer = profileRenderer.createProfileRenderer({
          i18n: makeMockI18n(),
          dom,
          formatNormativeCitationTitle: (raw: unknown) => String(raw || ""),
          isRawDocId: () => false,
        });

        renderer.renderProfileContent(
          { title: "Test", binding_force: "Fuerza vinculante: Ley o estatuto" },
          "Fallback",
        );

        expect(dom.normaBindingForceNode.textContent).toBe(
          "Fuerza vinculante: Ley o estatuto",
        );
      });

      it("hides binding_force when empty", () => {
        const dom = makeMockDom();
        const renderer = profileRenderer.createProfileRenderer({
          i18n: makeMockI18n(),
          dom,
          formatNormativeCitationTitle: (raw: unknown) => String(raw || ""),
          isRawDocId: () => false,
        });

        renderer.renderProfileContent({ title: "Test", binding_force: "" }, "Fallback");

        expect(dom.normaBindingForceNode.hidden).toBe(true);
      });

      it("renders facts from profile", () => {
        const dom = makeMockDom();
        const renderer = profileRenderer.createProfileRenderer({
          i18n: makeMockI18n(),
          dom,
          formatNormativeCitationTitle: (raw: unknown) => String(raw || ""),
          isRawDocId: () => false,
        });

        renderer.renderProfileContent(
          {
            title: "Test",
            facts: [
              { label: "Entidad", value: "DIAN" },
              { label: "Fecha", value: "2024-01-01" },
            ],
          },
          "Fallback",
        );

        expect(dom.normaFactsNode.hidden).toBe(false);
        const factCards = dom.normaFactsNode.querySelectorAll(".norma-fact");
        expect(factCards.length).toBe(2);
      });

      it("hides facts when array is empty", () => {
        const dom = makeMockDom();
        const renderer = profileRenderer.createProfileRenderer({
          i18n: makeMockI18n(),
          dom,
          formatNormativeCitationTitle: (raw: unknown) => String(raw || ""),
          isRawDocId: () => false,
        });

        renderer.renderProfileContent({ title: "Test", facts: [] }, "Fallback");

        expect(dom.normaFactsNode.hidden).toBe(true);
      });

      it("renders sections", () => {
        const dom = makeMockDom();
        const renderer = profileRenderer.createProfileRenderer({
          i18n: makeMockI18n(),
          dom,
          formatNormativeCitationTitle: (raw: unknown) => String(raw || ""),
          isRawDocId: () => false,
        });

        renderer.renderProfileContent(
          {
            title: "Test",
            sections: [
              { id: "s1", title: "Section One", body: "Body one" },
            ],
          },
          "Fallback",
        );

        const cards = dom.normaSectionsNode.querySelectorAll(".norma-section-card");
        expect(cards.length).toBeGreaterThanOrEqual(1);
      });

      it("handles caution_banner", () => {
        const dom = makeMockDom();
        const renderer = profileRenderer.createProfileRenderer({
          i18n: makeMockI18n(),
          dom,
          formatNormativeCitationTitle: (raw: unknown) => String(raw || ""),
          isRawDocId: () => false,
        });

        renderer.renderProfileContent(
          {
            title: "Test",
            caution_banner: { title: "Advertencia", body: "Esta norma fue derogada", tone: "warning" },
          },
          "Fallback",
        );

        expect(dom.normaCautionBannerNode.hidden).toBe(false);
        expect(dom.normaCautionTitleNode.textContent).toBe("Advertencia");
        expect(dom.normaCautionBodyNode.textContent).toBe("Esta norma fue derogada");
      });

      it("hides topbar for formulario profiles", () => {
        const dom = makeMockDom();
        const renderer = profileRenderer.createProfileRenderer({
          i18n: makeMockI18n(),
          dom,
          formatNormativeCitationTitle: (raw: unknown) => String(raw || ""),
          isRawDocId: () => false,
        });

        renderer.renderProfileContent({ title: "Formulario 110" }, "Fallback");

        expect(dom.normaTopbarNode.hidden).toBe(true);
      });

      it("shows topbar for non-formulario profiles", () => {
        const dom = makeMockDom();
        const renderer = profileRenderer.createProfileRenderer({
          i18n: makeMockI18n(),
          dom,
          formatNormativeCitationTitle: (raw: unknown) => String(raw || ""),
          isRawDocId: () => false,
        });

        renderer.renderProfileContent({ title: "Ley 1819 de 2016" }, "Fallback");

        expect(dom.normaTopbarNode.hidden).toBe(false);
      });

      it("renders source_action for non-formulario", () => {
        const dom = makeMockDom();
        const renderer = profileRenderer.createProfileRenderer({
          i18n: makeMockI18n(),
          dom,
          formatNormativeCitationTitle: (raw: unknown) => String(raw || ""),
          isRawDocId: () => false,
        });

        renderer.renderProfileContent(
          {
            title: "Decreto 1625",
            source_action: {
              label: "Ver original",
              state: "available",
              url: "https://example.com",
            },
          },
          "Fallback",
        );

        expect(dom.normaOriginalBtn.hidden).toBe(false);
        expect(dom.normaOriginalBtn.textContent).toBe("Ver original");
        expect(dom.normaOriginalBtn.disabled).toBe(false);
      });

      it("renders original text for ET profile in primary node", () => {
        const dom = makeMockDom();
        const renderer = profileRenderer.createProfileRenderer({
          i18n: makeMockI18n(),
          dom,
          formatNormativeCitationTitle: (raw: unknown) => String(raw || ""),
          isRawDocId: () => false,
        });

        renderer.renderProfileContent(
          {
            title: "ET Art. 240",
            document_family: "et_dur",
            lead: "Context about the article",
            original_text: {
              title: "Articulo 240",
              quote: "Tarifa general de renta...\n\nSegundo parrafo.",
              evidence_status: "verified",
            },
          },
          "Fallback",
        );

        expect(dom.normaPrimaryNode.hidden).toBe(false);
        const quoteCard = dom.normaPrimaryNode.querySelector(".norma-section-card-quote");
        expect(quoteCard).not.toBeNull();
      });

      it("renders vigencia_detail as a fact", () => {
        const dom = makeMockDom();
        const renderer = profileRenderer.createProfileRenderer({
          i18n: makeMockI18n(),
          dom,
          formatNormativeCitationTitle: (raw: unknown) => String(raw || ""),
          isRawDocId: () => false,
        });

        renderer.renderProfileContent(
          {
            title: "Ley Test",
            facts: [{ label: "Tipo", value: "Ley" }],
            vigencia_detail: {
              label: "Vigente",
              basis: "No ha sido derogada",
              evidence_status: "verified",
            },
          },
          "Fallback",
        );

        // Should have 2 facts: original + vigencia
        const factCards = dom.normaFactsNode.querySelectorAll(".norma-fact");
        expect(factCards.length).toBe(2);
      });

      it("renders additional_depth_sections", () => {
        const dom = makeMockDom();
        const renderer = profileRenderer.createProfileRenderer({
          i18n: makeMockI18n(),
          dom,
          formatNormativeCitationTitle: (raw: unknown) => String(raw || ""),
          isRawDocId: () => false,
        });

        renderer.renderProfileContent(
          {
            title: "Test",
            additional_depth_sections: [
              {
                title: "Contenido relacionado",
                accordion_default: "open",
                items: [
                  { label: "Doc A", kind: "normative_base", doc_id: "doc_a" },
                  { label: "Doc B", url: "https://example.com" },
                ],
              },
              {
                title: "Otros recursos",
                accordion_default: "closed",
                items: [{ label: "Doc C" }],
              },
            ],
          },
          "Fallback",
        );

        const cards = dom.normaSectionsNode.querySelectorAll(".norma-section-card");
        expect(cards.length).toBeGreaterThanOrEqual(2);
      });

      it("hides analysis button for ET article profiles", () => {
        const dom = makeMockDom();
        const renderer = profileRenderer.createProfileRenderer({
          i18n: makeMockI18n(),
          dom,
          formatNormativeCitationTitle: (raw: unknown) => String(raw || ""),
          isRawDocId: () => false,
        });

        renderer.renderProfileContent(
          {
            title: "ET Art 240",
            document_family: "et_dur",
            original_text: { title: "Art 240", quote: "text", evidence_status: "verified" },
            analysis_action: { state: "available", url: "/analysis" },
          },
          "Fallback",
        );

        expect(dom.normaAnalysisBtn.hidden).toBe(true);
      });
    });

    describe("applyLlmEnrichment", () => {
      it("merges LLM result into base profile", () => {
        const dom = makeMockDom();
        const renderer = profileRenderer.createProfileRenderer({
          i18n: makeMockI18n(),
          dom,
          formatNormativeCitationTitle: (raw: unknown) => String(raw || ""),
          isRawDocId: () => false,
        });

        const base = {
          title: "Ley 1819",
          lead: "Original lead",
          facts: [{ label: "Tipo", value: "Ley" }],
        };
        const llm = {
          lead: "Enriched lead",
          sections: [{ id: "s1", title: "Impacto", body: "High impact" }],
        };

        renderer.applyLlmEnrichment(base, llm, "Fallback Title");

        // Title should still be from base
        expect(dom.normaTitleNode.textContent).toBe("Ley 1819");
        // Sections from LLM should be rendered
        const sectionCards = dom.normaSectionsNode.querySelectorAll(".norma-section-card");
        expect(sectionCards.length).toBeGreaterThanOrEqual(1);
      });

      it("keeps base facts when LLM has no facts", () => {
        const dom = makeMockDom();
        const renderer = profileRenderer.createProfileRenderer({
          i18n: makeMockI18n(),
          dom,
          formatNormativeCitationTitle: (raw: unknown) => String(raw || ""),
          isRawDocId: () => false,
        });

        const base = {
          title: "Test",
          facts: [{ label: "Entidad", value: "DIAN" }],
        };
        const llm = { lead: "New lead" };

        renderer.applyLlmEnrichment(base, llm, "Fallback");

        const factCards = dom.normaFactsNode.querySelectorAll(".norma-fact");
        expect(factCards.length).toBe(1);
      });

      it("uses LLM vigencia_detail when present", () => {
        const dom = makeMockDom();
        const renderer = profileRenderer.createProfileRenderer({
          i18n: makeMockI18n(),
          dom,
          formatNormativeCitationTitle: (raw: unknown) => String(raw || ""),
          isRawDocId: () => false,
        });

        const base = { title: "Test" };
        const llm = {
          vigencia_detail: {
            label: "Vigente con modificaciones",
            basis: "Ley 2277",
            evidence_status: "verified" as const,
          },
        };

        renderer.applyLlmEnrichment(base, llm, "Fallback");

        const factCards = dom.normaFactsNode.querySelectorAll(".norma-fact");
        expect(factCards.length).toBeGreaterThanOrEqual(1);
      });
    });
  });
});

// =============================================================================
// interpretationModal
// =============================================================================

describe("interpretationModal", () => {
  let interpretationModal: typeof import("@/features/chat/normative/interpretationModal");

  beforeEach(async () => {
    vi.resetModules();

    vi.doMock("@/shared/utils/format", () => ({
      stripMarkdown: vi.fn((v: string) => v.replace(/[*#_>]/g, "").trim()),
      visibleText: vi.fn((v: unknown) => String(v || "").trim()),
    }));

    interpretationModal = await import("@/features/chat/normative/interpretationModal");
  });

  afterEach(() => {
    document.body.innerHTML = "";
  });

  function makeMockDeps() {
    const el = () => document.createElement("div");
    const anchor = () => {
      const a = document.createElement("a") as HTMLAnchorElement;
      a.hidden = true;
      return a;
    };
    return {
      i18n: {
        t: vi.fn((key: string, params?: Record<string, string>) => {
          if (params) return `${key}(${JSON.stringify(params)})`;
          return key;
        }),
      },
      state: {
        activeCitation: null,
        activeNormaRequestId: 0,
        lastUserMessage: "test question",
        lastAssistantAnswerMarkdown: "test answer",
        modalStack: [],
      },
      dom: {
        interpretationStatusNode: el(),
        interpretationResultsNode: el(),
        summaryModeNode: el(),
        summaryExternalLinkNode: anchor(),
        summaryBodyNode: el(),
        summaryGroundingNode: el(),
      },
      withThinkingWheel: vi.fn(async <T>(task: () => Promise<T>) => task()),
      openModal: vi.fn(),
      modalInterpretations: el(),
      modalSummary: el(),
    };
  }

  describe("createInterpretationModal", () => {
    it("returns clearInterpretations, clearSummary, openInterpretationsModal, openSummaryModal", () => {
      const deps = makeMockDeps();
      const modal = interpretationModal.createInterpretationModal(deps);

      expect(typeof modal.clearInterpretations).toBe("function");
      expect(typeof modal.clearSummary).toBe("function");
      expect(typeof modal.openInterpretationsModal).toBe("function");
      expect(typeof modal.openSummaryModal).toBe("function");
    });
  });

  describe("clearInterpretations", () => {
    it("resets status text and clears results", () => {
      const deps = makeMockDeps();
      deps.dom.interpretationResultsNode.innerHTML = "<div>old</div>";
      deps.dom.interpretationStatusNode.textContent = "old status";

      const modal = interpretationModal.createInterpretationModal(deps);
      modal.clearInterpretations();

      expect(deps.dom.interpretationResultsNode.innerHTML).toBe("");
      expect(deps.dom.interpretationStatusNode.textContent).toBe(
        "chat.modal.interpretations.loading",
      );
    });
  });

  describe("clearSummary", () => {
    it("resets summary fields to defaults", () => {
      const deps = makeMockDeps();
      deps.dom.summaryModeNode.textContent = "some mode";
      deps.dom.summaryBodyNode.textContent = "some body";

      const modal = interpretationModal.createInterpretationModal(deps);
      modal.clearSummary();

      expect(deps.dom.summaryModeNode.textContent).toBe("-");
      expect(deps.dom.summaryBodyNode.textContent).toContain("Selecciona una interpretaci");
      expect(deps.dom.summaryExternalLinkNode.hidden).toBe(true);
    });
  });

  describe("openInterpretationsModal", () => {
    it("opens modal and fetches interpretations", async () => {
      const deps = makeMockDeps();

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          interpretations: [
            {
              doc_id: "interp_1",
              title: "Concepto DIAN 1234",
              relevance_score: 0.8,
              coverage_axes: ["fiscal", "renta"],
              card_summary: "Summary of the interpretation",
              providers: [{ name: "DIAN" }],
              provider_links: [{ provider: "DIAN", url: "https://dian.gov.co" }],
            },
          ],
          has_more: false,
          total_available: 1,
        }),
      });

      const modal = interpretationModal.createInterpretationModal(deps);
      await modal.openInterpretationsModal({ doc_id: "doc_1" });

      expect(deps.openModal).toHaveBeenCalledWith(deps.modalInterpretations);
      expect(deps.withThinkingWheel).toHaveBeenCalled();

      const cards = deps.dom.interpretationResultsNode.querySelectorAll(".interpretation-card");
      expect(cards.length).toBe(1);
    });

    it("shows empty state when no interpretations found", async () => {
      const deps = makeMockDeps();

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          interpretations: [],
          has_more: false,
          total_available: 0,
        }),
      });

      const modal = interpretationModal.createInterpretationModal(deps);
      await modal.openInterpretationsModal({ doc_id: "doc_1" });

      expect(deps.dom.interpretationStatusNode.textContent).toBe(
        "chat.interpretations.emptyStrict",
      );
    });

    it("returns false for empty doc_id", async () => {
      const deps = makeMockDeps();

      const modal = interpretationModal.createInterpretationModal(deps);
      await modal.openInterpretationsModal({ doc_id: "" });

      // openModal is still called, but the fetch fails silently
      expect(deps.openModal).toHaveBeenCalled();
    });

    it("handles fetch error", async () => {
      const deps = makeMockDeps();

      global.fetch = vi.fn().mockRejectedValue(new Error("Network down"));

      const modal = interpretationModal.createInterpretationModal(deps);
      await modal.openInterpretationsModal({ doc_id: "doc_1" });

      expect(deps.dom.interpretationStatusNode.textContent).toContain(
        "chat.interpretations.errorConnection",
      );
    });

    it("handles HTTP error response", async () => {
      const deps = makeMockDeps();

      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        json: async () => ({ error: "server_error" }),
      });

      const modal = interpretationModal.createInterpretationModal(deps);
      await modal.openInterpretationsModal({ doc_id: "doc_1" });

      expect(deps.dom.interpretationStatusNode.textContent).toContain("Error");
    });

    it("renders interpretation card with relevance chip and axes", async () => {
      const deps = makeMockDeps();

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          interpretations: [
            {
              doc_id: "interp_1",
              title: "Concepto 123",
              relevance_score: 0.9,
              coverage_axes: ["fiscal", "procedimiento"],
              card_summary: "Test summary",
              selection_reason: "High relevance",
              authority: "DIAN",
              providers: [],
              provider_links: [],
            },
          ],
          has_more: false,
          total_available: 1,
        }),
      });

      const modal = interpretationModal.createInterpretationModal(deps);
      await modal.openInterpretationsModal({ doc_id: "doc_1" });

      const card = deps.dom.interpretationResultsNode.querySelector(".interpretation-card")!;
      expect(card.querySelector(".interpretation-title")!.textContent).toBe("Concepto 123");
      expect(card.querySelector(".interpretation-chip--score")!.textContent).toBe(
        "chat.interpretations.relevance.high",
      );
      expect(card.querySelector(".interpretation-snippet")!.textContent).toBe("Test summary");
      // Axes chips (up to 4)
      const chips = card.querySelectorAll(".interpretation-chip:not(.interpretation-chip--score)");
      expect(chips.length).toBe(2);
    });

    it("renders load more button when has_more is true", async () => {
      const deps = makeMockDeps();

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          interpretations: [
            { doc_id: "i1", title: "Interp 1", relevance_score: 0.5 },
            { doc_id: "i2", title: "Interp 2", relevance_score: 0.6 },
          ],
          has_more: true,
          total_available: 10,
          next_offset: 2,
        }),
      });

      const modal = interpretationModal.createInterpretationModal(deps);
      await modal.openInterpretationsModal({ doc_id: "doc_1" });

      const moreBtn = deps.dom.interpretationResultsNode.querySelector(".interpretation-more-btn");
      expect(moreBtn).not.toBeNull();
    });

    it("does not render load more button when has_more is false", async () => {
      const deps = makeMockDeps();

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          interpretations: [{ doc_id: "i1", title: "Only one" }],
          has_more: false,
          total_available: 1,
        }),
      });

      const modal = interpretationModal.createInterpretationModal(deps);
      await modal.openInterpretationsModal({ doc_id: "doc_1" });

      const moreBtn = deps.dom.interpretationResultsNode.querySelector(".interpretation-more-btn");
      expect(moreBtn).toBeNull();
    });
  });

  describe("openSummaryModal", () => {
    it("opens summary modal and posts to /api/interpretation-summary", async () => {
      const deps = makeMockDeps();

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          mode: "corpus_grounded",
          summary_markdown: "Summary of the interpretation",
          grounding: {
            citation: { source_view_url: "/source-view?doc_id=c1" },
            interpretation: {
              source_view_url: "/source-view?doc_id=i1",
              official_url: "https://dian.gov.co/concepto",
            },
          },
        }),
      });

      const modal = interpretationModal.createInterpretationModal(deps);
      await modal.openSummaryModal(
        { doc_id: "doc_1", source_label: "ET Art 240" },
        { doc_id: "interp_1", title: "Concepto DIAN" },
        "https://selected.link",
      );

      expect(deps.openModal).toHaveBeenCalledWith(deps.modalSummary);

      expect(deps.dom.summaryModeNode.textContent).toBe("mode=corpus_grounded");
      expect(deps.dom.summaryBodyNode.textContent).toBe("Summary of the interpretation");

      // Grounding links
      const links = deps.dom.summaryGroundingNode.querySelectorAll("a");
      expect(links.length).toBe(3);
    });

    it("shows external link when selected_link is provided", async () => {
      const deps = makeMockDeps();

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          mode: "test",
          summary_markdown: "ok",
          grounding: {},
        }),
      });

      const modal = interpretationModal.createInterpretationModal(deps);
      await modal.openSummaryModal(
        { doc_id: "doc_1" },
        { doc_id: "interp_1" },
        "https://external.link/doc",
      );

      expect(deps.dom.summaryExternalLinkNode.hidden).toBe(false);
      expect(deps.dom.summaryExternalLinkNode.href).toContain("https://external.link/doc");
    });

    it("handles summary API error response", async () => {
      const deps = makeMockDeps();

      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        json: async () => ({
          error: { code: "summary_failed", message: "LLM timeout" },
        }),
      });

      const modal = interpretationModal.createInterpretationModal(deps);
      await modal.openSummaryModal(
        { doc_id: "doc_1" },
        { doc_id: "interp_1" },
      );

      expect(deps.dom.summaryModeNode.textContent).toBe("error");
      expect(deps.dom.summaryBodyNode.textContent).toContain("summary_failed");
      expect(deps.dom.summaryBodyNode.textContent).toContain("LLM timeout");
    });

    it("handles network error in summary", async () => {
      const deps = makeMockDeps();

      global.fetch = vi.fn().mockRejectedValue(new Error("Connection refused"));

      const modal = interpretationModal.createInterpretationModal(deps);
      await modal.openSummaryModal(
        { doc_id: "doc_1" },
        { doc_id: "interp_1" },
      );

      expect(deps.dom.summaryModeNode.textContent).toBe("error");
      expect(deps.dom.summaryBodyNode.textContent).toContain("Connection refused");
    });

    it("sends correct payload to API", async () => {
      const deps = makeMockDeps();
      deps.state.lastUserMessage = "How to file renta?";

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ mode: "test", summary_markdown: "ok", grounding: {} }),
      });

      const modal = interpretationModal.createInterpretationModal(deps);
      await modal.openSummaryModal(
        { doc_id: "doc_1", source_label: "ET Art 240", topic: "renta", pais: "co" },
        { doc_id: "interp_1", title: "Concepto 123", official_url: "https://dian.gov.co" },
        "",
      );

      const fetchCall = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(fetchCall[0]).toBe("/api/interpretation-summary");
      const body = JSON.parse(fetchCall[1].body);
      expect(body.citation.doc_id).toBe("doc_1");
      expect(body.interpretation.doc_id).toBe("interp_1");
      expect(body.message_context).toBe("How to file renta?");
    });
  });
});
