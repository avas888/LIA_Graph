import { describe, it, expect, vi, beforeEach } from "vitest";
import { createI18n } from "@/shared/i18n";
import type { I18nRuntime } from "@/shared/i18n";
import type { OpsStateController, OpsStateData } from "@/features/ops/opsState";
import type { IngestionSession, IngestionBatchSummary, IngestionCorpus } from "@/features/ops/opsTypes";

// We cannot easily test the full createOpsIngestionController because it
// requires a complex DOM scaffold and many interconnected features.
// Instead we test the supporting pure-logic functions and types exported
// from opsTypes, plus we test the controller factory at the integration
// level with a minimal DOM stub where possible.

// ── Mock fetch globally ───────────────────────────────────────

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

vi.mock("@/shared/api/client", () => ({
  ApiError: class ApiError extends Error {
    status: number;
    data: unknown;
    constructor(message: string, status: number, data?: unknown) {
      super(message);
      this.name = "ApiError";
      this.status = status;
      this.data = data;
    }
  },
  getJson: vi.fn(),
  postJson: vi.fn(),
}));

vi.mock("@/features/ops/opsKanbanView", () => ({
  renderKanbanBoard: vi.fn(),
}));

import { createOpsIngestionController } from "@/features/ops/opsIngestionController";
import { getJson, postJson } from "@/shared/api/client";

// ── Helpers ──────────────────────────────────────────────────

function summarizeSession(docs: Array<{ status: string }>): IngestionBatchSummary {
  return {
    total: docs.length,
    queued: docs.filter((d) => d.status === "queued").length,
    processing: docs.filter((d) => d.status === "processing" || d.status === "in_progress").length,
    done: docs.filter((d) => d.status === "done").length,
    failed: docs.filter((d) => d.status === "failed").length,
    skipped_duplicate: docs.filter((d) => d.status === "skipped_duplicate").length,
    pending_batch_gate: 0,
    bounced: docs.filter((d) => d.status === "bounced").length,
  };
}

function buildSession(id: string, docs: any[] = [], overrides: Record<string, unknown> = {}): IngestionSession {
  return {
    session_id: id,
    corpus: "declaracion_renta",
    status: "ready",
    created_at: "2026-04-01T10:00:00Z",
    updated_at: "2026-04-01T10:00:00Z",
    documents: docs,
    batch_summary: summarizeSession(docs),
    last_error: null,
    ...overrides,
  } as IngestionSession;
}

function createDomElements(): Record<string, any> {
  const els: Record<string, HTMLElement> = {};

  // Create all needed DOM elements. These must stay in sync with
  // OpsIngestionDom in opsIngestionController.ts — add here when the
  // controller starts consuming a new DOM ref.
  const names = [
    "ingestionCorpusSelect", "ingestionBatchTypeSelect",
    "ingestionDropzone", "ingestionFileInput", "ingestionFolderInput",
    "ingestionSelectFilesBtn", "ingestionSelectFolderBtn",
    "ingestionUploadProgress",
    "ingestionPendingFiles", "ingestionOverview",
    "ingestionRefreshBtn", "ingestionCreateSessionBtn",
    "ingestionUploadBtn", "ingestionProcessBtn",
    "ingestionAutoProcessBtn", "ingestionValidateBatchBtn",
    "ingestionRetryBtn",
    "ingestionDeleteSessionBtn", "ingestionSessionMeta",
    "ingestionSessionsList", "selectedSessionMeta",
    "ingestionLastError", "ingestionLastErrorMessage",
    "ingestionLastErrorGuidance", "ingestionLastErrorNext",
    "ingestionKanban", "ingestionLogAccordion",
    "ingestionLogBody", "ingestionLogCopyBtn",
    "ingestionAutoStatus",
  ];

  for (const name of names) {
    // Determine element type based on suffix
    if (name.includes("Select")) {
      els[name] = document.createElement("select");
    } else if (name.includes("Input")) {
      const input = document.createElement("input");
      if (name === "ingestionFolderInput") {
        input.setAttribute("webkitdirectory", "");
      }
      els[name] = input;
    } else if (name.includes("Btn")) {
      els[name] = document.createElement("button");
    } else if (name === "ingestionSessionsList") {
      els[name] = document.createElement("ul");
    } else if (name === "ingestionLogBody") {
      els[name] = document.createElement("pre");
    } else {
      els[name] = document.createElement("div");
    }

    document.body.appendChild(els[name]);
  }

  // addCorpusBtn and addCorpusDialog are optional
  els.addCorpusBtn = null as any;
  els.addCorpusDialog = null as any;

  return els;
}

function createMockStateController(overrides: Partial<OpsStateData> = {}): OpsStateController {
  const state: OpsStateData = {
    activeTab: "ingestion",
    corpora: [
      { key: "declaracion_renta", label: "Renta", active: true },
      { key: "iva", label: "IVA", active: true },
    ],
    selectedCorpus: "autogenerar",
    sessions: [],
    selectedSessionId: "",
    selectedSession: null,
    pendingFiles: [],
    intake: [],
    reviewPlan: null,
    preflightRunId: 0,
    mutating: false,
    folderUploadProgress: null,
    folderRelativePaths: new Map(),
    rejectedArtifacts: [],
    preflightManifest: null,
    preflightScanProgress: null,
    ...overrides,
  };

  return {
    state,
    clearSelectionAfterDelete: vi.fn(),
    getFocusedRunningSessionId: vi.fn().mockReturnValue(""),
    selectedCorpusConfig: () => state.corpora.find((c) => c.key === state.selectedCorpus),
    setActiveTab: vi.fn((tab) => { state.activeTab = tab; }),
    setCorpora: vi.fn((corpora) => { state.corpora = [...corpora]; }),
    setFolderUploadProgress: vi.fn((p) => { state.folderUploadProgress = p; }),
    setMutating: vi.fn((v) => { state.mutating = v; }),
    setPendingFiles: vi.fn((f) => { state.pendingFiles = [...f]; }),
    setIntake: vi.fn((entries) => { state.intake = [...entries]; }),
    setReviewPlan: vi.fn((plan) => { state.reviewPlan = plan; }),
    bumpPreflightRunId: vi.fn(() => { state.preflightRunId += 1; return state.preflightRunId; }),
    setPreflightManifest: vi.fn((m) => { state.preflightManifest = m; }),
    setPreflightScanProgress: vi.fn((p) => { state.preflightScanProgress = p; }),
    setSelectedCorpus: vi.fn((c) => { state.selectedCorpus = c; }),
    setSelectedSession: vi.fn((s) => {
      state.selectedSession = s;
      state.selectedSessionId = s?.session_id || "";
    }),
    setSessions: vi.fn((sessions) => { state.sessions = [...sessions]; }),
    syncSelectedSession: vi.fn(),
    upsertSession: vi.fn((session) => {
      const idx = state.sessions.findIndex((s) => s.session_id === session.session_id);
      if (idx >= 0) {
        state.sessions[idx] = session;
      } else {
        state.sessions.push(session);
      }
      if (state.selectedSessionId === session.session_id) {
        state.selectedSession = session;
      }
    }),
  };
}

describe("opsIngestionController", () => {
  let i18n: I18nRuntime;

  beforeEach(() => {
    document.body.innerHTML = "";
    vi.clearAllMocks();
    fetchMock.mockReset();
    i18n = createI18n("es-CO");
  });

  function createController(
    stateOverrides: Partial<OpsStateData> = {},
    domOverrides: Record<string, HTMLElement> = {}
  ) {
    const dom = { ...createDomElements(), ...domOverrides };
    const stateController = createMockStateController(stateOverrides);
    const setFlash = vi.fn();
    const withThinkingWheel = vi.fn(async <T>(task: () => Promise<T>) => task());

    const controller = createOpsIngestionController({
      i18n,
      stateController,
      dom: dom as any,
      withThinkingWheel,
      setFlash,
    });

    return { controller, stateController, dom, setFlash, withThinkingWheel };
  }

  // ── Creation ─────────────────────────────────────────────

  it("creates a controller with expected methods", () => {
    const { controller } = createController();
    expect(typeof controller.bindEvents).toBe("function");
    expect(typeof controller.render).toBe("function");
    expect(typeof controller.refreshIngestion).toBe("function");
  });

  // ── render ──────────────────────────────────────────────

  it("render populates corpus select with AUTOGENERAR as first option", () => {
    const { controller, dom } = createController();
    controller.render();

    const select = dom.ingestionCorpusSelect as HTMLSelectElement;
    expect(select.options.length).toBeGreaterThan(0);
    expect(select.options[0].textContent).toBe("AUTOGENERAR");
    expect(select.options[0].value).toBe("autogenerar");
  });

  it("render populates sorted corpora after AUTOGENERAR", () => {
    const { controller, dom } = createController();
    controller.render();

    const select = dom.ingestionCorpusSelect as HTMLSelectElement;
    const labels = Array.from(select.options).map((o) => o.textContent);
    expect(labels[0]).toBe("AUTOGENERAR");
    // Remaining should be sorted alphabetically
    const sorted = labels.slice(1);
    const expected = [...sorted].sort((a, b) => (a || "").localeCompare(b || "", "es"));
    expect(sorted).toEqual(expected);
  });

  it("render shows intake panel when intake has entries", () => {
    const file1 = new File(["a"], "doc1.pdf", { type: "application/pdf" });
    const file2 = new File(["b"], "doc2.pdf", { type: "application/pdf" });
    const { controller, dom } = createController({
      intake: [
        { file: file1, relativePath: "doc1.pdf", contentHash: null, verdict: "pending", preflightEntry: null },
        { file: file2, relativePath: "doc2.pdf", contentHash: null, verdict: "pending", preflightEntry: null },
      ],
    });

    controller.render();

    const dropzone = dom.ingestionDropzone;
    const windows = dropzone.querySelector(".ops-intake-windows");
    expect(windows).not.toBeNull();
    const intakePanel = dropzone.querySelector(".ops-intake-panel--intake");
    expect(intakePanel).not.toBeNull();
    expect(dropzone.classList.contains("has-files")).toBe(true);
  });

  it("render shows will-ingest and bounced panels after preflight", () => {
    const newFile = new File(["a"], "new.pdf", { type: "application/pdf" });
    const dupFile = new File(["b"], "dup.pdf", { type: "application/pdf" });
    const intakeEntries = [
      { file: newFile, relativePath: "new.pdf", contentHash: "h1", verdict: "new" as const, preflightEntry: null },
      { file: dupFile, relativePath: "dup.pdf", contentHash: "h2", verdict: "duplicate" as const, preflightEntry: null },
    ];
    const { controller, dom } = createController({
      intake: intakeEntries,
      reviewPlan: {
        willIngest: [intakeEntries[0]],
        bounced: [intakeEntries[1]],
        scanned: 2,
        elapsedMs: 50,
        stalePartial: false,
      },
      pendingFiles: [newFile],
    });

    controller.render();

    const dropzone = dom.ingestionDropzone;
    expect(dropzone.querySelector(".ops-intake-panel--will-ingest")).not.toBeNull();
    expect(dropzone.querySelector(".ops-intake-panel--bounced")).not.toBeNull();
  });

  it("render shows empty state when intake is empty", () => {
    const { controller, dom } = createController({ intake: [], pendingFiles: [] });
    controller.render();

    const dropzone = dom.ingestionDropzone;
    expect(dropzone.classList.contains("has-files")).toBe(false);
  });

  it("render disables controls when mutating", () => {
    const { controller, dom } = createController({ mutating: true });
    controller.render();

    expect((dom.ingestionCreateSessionBtn as HTMLButtonElement).disabled).toBe(true);
    expect((dom.ingestionRefreshBtn as HTMLButtonElement).disabled).toBe(true);
    expect((dom.ingestionUploadBtn as HTMLButtonElement).disabled).toBe(true);
  });

  it("render shows session list entries for active sessions", () => {
    const session = buildSession("sess-001", [
      { doc_id: "d1", filename: "test.pdf", status: "done", stage: "complete", bytes: 100, batch_type: "normative_base", progress: 100, updated_at: "2026-04-01" },
    ]);
    const { controller, dom } = createController({
      sessions: [session],
    });

    controller.render();

    const items = (dom.ingestionSessionsList as HTMLUListElement).querySelectorAll("li");
    expect(items.length).toBe(1);
  });

  it("render shows empty message when no sessions", () => {
    const { controller, dom } = createController({ sessions: [] });
    controller.render();

    const items = (dom.ingestionSessionsList as HTMLUListElement).querySelectorAll("li");
    expect(items.length).toBe(1);
    expect(items[0].classList.contains("ops-empty")).toBe(true);
  });

  // ── Controls state ──────────────────────────────────────

  it("disables approve button when no review plan has resolved", () => {
    const { controller, dom } = createController({ pendingFiles: [], intake: [], reviewPlan: null });
    controller.render();
    expect((dom.ingestionUploadBtn as HTMLButtonElement).disabled).toBe(true);
  });

  it("disables process button when no session selected", () => {
    const { controller, dom } = createController({ selectedSession: null });
    controller.render();
    expect((dom.ingestionProcessBtn as HTMLButtonElement).disabled).toBe(true);
  });

  it("delete-session button is enabled whenever a session is selected", () => {
    // Post-consolidation UI: the old "stop" and "delete-failed" buttons were
    // merged into ingestionDeleteSessionBtn ("Detener y descartar"), which
    // deliberately stays enabled even while the session is running so the
    // user can stop it. The old stale tests checked ingestionStopBtn /
    // ingestionDeleteFailedBtn, which no longer exist in the DOM interface.
    const session = buildSession("sess-001");
    const { controller, dom } = createController({ selectedSession: session, selectedSessionId: "sess-001" });
    controller.render();
    expect((dom.ingestionDeleteSessionBtn as HTMLButtonElement).disabled).toBe(false);
  });

  it("delete-session button is disabled when no session is selected", () => {
    const { controller, dom } = createController({ selectedSession: null });
    controller.render();
    expect((dom.ingestionDeleteSessionBtn as HTMLButtonElement).disabled).toBe(true);
  });

  it("shows corpus inactive message when selected corpus is not active", () => {
    const { controller, dom } = createController({
      selectedCorpus: "nonexistent_corpus",
      corpora: [{ key: "renta", label: "Renta", active: false }],
    });
    controller.render();
    const overview = dom.ingestionOverview as HTMLElement;
    expect(overview.textContent).toBe(i18n.t("ops.ingestion.corpusInactive"));
  });

  // ── Selected session meta ───────────────────────────────

  it("renders selected session meta with summary line", () => {
    const session = buildSession("sess-001", [
      { doc_id: "d1", filename: "f1.pdf", status: "done", stage: "complete", bytes: 100, batch_type: "", progress: 100, updated_at: "" },
      { doc_id: "d2", filename: "f2.pdf", status: "failed", stage: "upload", bytes: 200, batch_type: "", progress: 0, updated_at: "" },
    ]);
    const { controller, dom } = createController({
      selectedSession: session,
      selectedSessionId: "sess-001",
    });
    controller.render();

    const meta = (dom.selectedSessionMeta as HTMLElement).textContent || "";
    expect(meta).toContain("sess-001");
  });

  // ── Last error display ─────────────────────────────────

  it("shows last error when session has last_error", () => {
    const session = buildSession("sess-err", [], {
      last_error: { code: "UPLOAD_FAILED", message: "Archivo corrupto", guidance: "Reintente", next_step: "Subir de nuevo" },
    });
    const { controller, dom } = createController({
      selectedSession: session,
      selectedSessionId: "sess-err",
    });
    controller.render();

    expect((dom.ingestionLastError as HTMLElement).hidden).toBe(false);
    expect((dom.ingestionLastErrorMessage as HTMLElement).textContent).toBe("Archivo corrupto");
    expect((dom.ingestionLastErrorGuidance as HTMLElement).textContent).toBe("Reintente");
  });

  it("hides last error when session has no error", () => {
    const session = buildSession("sess-ok");
    const { controller, dom } = createController({
      selectedSession: session,
      selectedSessionId: "sess-ok",
    });
    controller.render();
    expect((dom.ingestionLastError as HTMLElement).hidden).toBe(true);
  });

  // ── Session log accordion ──────────────────────────────

  it("builds session log with document details", () => {
    const session = buildSession("sess-log", [
      {
        doc_id: "d1", filename: "report.pdf", status: "done", stage: "complete",
        bytes: 4096, batch_type: "normative_base", progress: 100,
        updated_at: "2026-04-01T12:00:00Z", created_at: "2026-04-01T10:00:00Z",
      },
      {
        doc_id: "d2", filename: "guide.pdf", status: "failed", stage: "etl",
        bytes: 2048, batch_type: "practica_erp", progress: 50,
        updated_at: "2026-04-01T11:00:00Z",
        error: { code: "PARSE_ERROR", message: "Could not parse PDF" },
      },
    ]);
    const { controller, dom } = createController({
      selectedSession: session,
      selectedSessionId: "sess-log",
    });
    controller.render();

    const logBody = (dom.ingestionLogBody as HTMLPreElement).textContent || "";
    expect(logBody).toContain("sess-log");
    expect(logBody).toContain("report.pdf");
    expect(logBody).toContain("guide.pdf");
    expect(logBody).toContain("PARSE_ERROR");
  });

  // ── Kanban display ─────────────────────────────────────

  it("shows empty kanban when session has no documents", () => {
    const session = buildSession("sess-empty");
    const { controller, dom } = createController({
      selectedSession: session,
      selectedSessionId: "sess-empty",
    });
    controller.render();

    const kanban = dom.ingestionKanban as HTMLElement;
    expect(kanban.querySelector(".ops-empty")).not.toBeNull();
  });

  // ── refreshIngestion ──────────────────────────────────

  it("refreshIngestion calls fetchCorpora and fetchSessions", async () => {
    const getJsonMock = vi.mocked(getJson);
    getJsonMock.mockImplementation(async (url: string) => {
      if (url === "/api/corpora") {
        return { corpora: [{ key: "renta", label: "Renta", active: true }] };
      }
      if (url.startsWith("/api/ingestion/sessions")) {
        return { sessions: [] };
      }
      return {};
    });

    const { controller, stateController } = createController();

    await controller.refreshIngestion({ showWheel: false, reportError: false });

    expect(getJsonMock).toHaveBeenCalled();
    expect(stateController.setCorpora).toHaveBeenCalled();
  });

  it("refreshIngestion shows error flash on failure", async () => {
    const getJsonMock = vi.mocked(getJson);
    getJsonMock.mockRejectedValue(new Error("Network error"));

    const { controller, setFlash } = createController();

    await expect(
      controller.refreshIngestion({ showWheel: false, reportError: true })
    ).rejects.toThrow();

    expect(setFlash).toHaveBeenCalledWith(expect.stringContaining("Network error"), "error");
  });

  // ── bindEvents ──────────────────────────────────────────

  it("bindEvents wires corpus select change to refresh", () => {
    const getJsonMock = vi.mocked(getJson);
    getJsonMock.mockResolvedValue({ corpora: [], sessions: [] });

    const { controller, dom, stateController } = createController();
    controller.bindEvents();

    const select = dom.ingestionCorpusSelect as HTMLSelectElement;
    const opt = document.createElement("option");
    opt.value = "declaracion_renta";
    select.appendChild(opt);
    select.value = "declaracion_renta";
    select.dispatchEvent(new Event("change"));

    expect(stateController.setSelectedCorpus).toHaveBeenCalledWith("declaracion_renta");
  });

  it("bindEvents wires file input change to push into intake (not pendingFiles)", () => {
    const { controller, dom, stateController } = createController();
    controller.bindEvents();

    const input = dom.ingestionFileInput as HTMLInputElement;

    // Simulate file selection by defining files property
    const file = new File(["content"], "test.pdf", { type: "application/pdf" });
    Object.defineProperty(input, "files", {
      value: [file],
      writable: true,
    });

    input.dispatchEvent(new Event("change"));

    // New flow: files land in state.intake via setIntake, not directly in pendingFiles.
    // pendingFiles is only written AFTER preflight has partitioned the intake.
    expect(stateController.setIntake).toHaveBeenCalled();
  });

  it("bindEvents wires dropzone click to trigger file input", () => {
    const { controller, dom } = createController();
    controller.bindEvents();

    const fileInput = dom.ingestionFileInput as HTMLInputElement;
    const clickSpy = vi.spyOn(fileInput, "click");

    (dom.ingestionDropzone as HTMLElement).click();

    expect(clickSpy).toHaveBeenCalled();
  });

  it("dropzone does not trigger file input when disabled", () => {
    const { controller, dom } = createController();
    controller.bindEvents();

    const fileInput = dom.ingestionFileInput as HTMLInputElement;
    fileInput.disabled = true;
    const clickSpy = vi.spyOn(fileInput, "click");

    (dom.ingestionDropzone as HTMLElement).click();

    expect(clickSpy).not.toHaveBeenCalled();
  });

  it("bindEvents wires dragenter to add is-dragover class", () => {
    const { controller, dom } = createController();
    controller.bindEvents();

    const dropzone = dom.ingestionDropzone as HTMLElement;
    const dragEvent = new Event("dragenter", { bubbles: true }) as any;
    dragEvent.preventDefault = vi.fn();

    dropzone.dispatchEvent(dragEvent);

    expect(dropzone.classList.contains("is-dragover")).toBe(true);
  });

  it("bindEvents wires dragleave to remove is-dragover class", () => {
    const { controller, dom } = createController();
    controller.bindEvents();

    const dropzone = dom.ingestionDropzone as HTMLElement;

    // Simulate enter then leave
    const enterEvent = new Event("dragenter", { bubbles: true }) as any;
    enterEvent.preventDefault = vi.fn();
    dropzone.dispatchEvent(enterEvent);

    const leaveEvent = new Event("dragleave", { bubbles: true });
    dropzone.dispatchEvent(leaveEvent);

    expect(dropzone.classList.contains("is-dragover")).toBe(false);
  });

  // ── Session status chip rendering ──────────────────────

  it("renders session status chip with correct tone class", () => {
    const session = buildSession("sess-fail", [], { status: "failed" });
    const { controller, dom } = createController({
      sessions: [session],
    });
    controller.render();

    const chip = (dom.ingestionSessionsList as HTMLElement).querySelector(".meta-chip.status-error");
    expect(chip).not.toBeNull();
    expect(chip?.textContent).toBe("failed");
  });

  it("renders session status chip with warn tone for processing", () => {
    const session = buildSession("sess-proc", [], { status: "processing" });
    const { controller, dom } = createController({
      sessions: [session],
    });
    controller.render();

    const chip = (dom.ingestionSessionsList as HTMLElement).querySelector(".meta-chip.status-warn");
    expect(chip).not.toBeNull();
    expect(chip?.textContent).toBe("processing");
  });

  // ── Batch type pills ──────────────────────────────────

  it("renders distinct batch type pills in session list", () => {
    const session = buildSession("sess-pills", [
      { doc_id: "d1", filename: "f1.pdf", status: "done", stage: "complete", bytes: 100, batch_type: "normative_base", progress: 100, updated_at: "" },
      { doc_id: "d2", filename: "f2.pdf", status: "done", stage: "complete", bytes: 200, batch_type: "practica_erp", progress: 100, updated_at: "" },
    ]);
    const { controller, dom } = createController({
      sessions: [session],
    });
    controller.render();

    const pills = (dom.ingestionSessionsList as HTMLElement).querySelectorAll(".ops-pill-batch");
    expect(pills.length).toBe(2);
  });

  // ── Corpus attention badge ────────────────────────────

  it("shows attention count on corpus option label", () => {
    const { controller, dom } = createController({
      corpora: [
        {
          key: "renta",
          label: "Renta",
          active: true,
          attention: [{ session_id: "s1", status: "partial_failed", filenames: ["f.pdf"] }],
        },
      ],
    });
    controller.render();

    const select = dom.ingestionCorpusSelect as HTMLSelectElement;
    const rentaOption = Array.from(select.options).find((o) => o.value === "renta");
    expect(rentaOption?.textContent).toContain("1");
  });

  // ── Inactive corpus label ─────────────────────────────

  it("marks inactive corpus in option label", () => {
    const { controller, dom } = createController({
      corpora: [
        { key: "ica", label: "ICA", active: false },
      ],
    });
    controller.render();

    const select = dom.ingestionCorpusSelect as HTMLSelectElement;
    const icaOption = Array.from(select.options).find((o) => o.value === "ica");
    expect(icaOption?.textContent).toContain(i18n.t("ops.ingestion.corpusInactiveOption"));
  });
});
