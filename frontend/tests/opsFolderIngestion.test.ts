/**
 * Tests for folder ingestion features (re-ingest v2).
 *
 * Covers:
 *   - filterSupportedFiles() — extension filter + hidden file rejection
 *   - uploadFilesWithConcurrency() — bounded parallel upload, progress tracking
 *   - FolderUploadProgress state transitions
 *   - X-Upload-Relative-Path header sent on upload
 *   - Upload progress visibility (real-time bar rendering)
 *   - "Ingerir carpeta" compound action (upload → auto-process → process)
 *   - Folder select button wiring
 *   - Kanban card shows source_relative_path
 */

import { describe, it, expect, vi, beforeEach } from "vitest";

import { createI18n } from "@/shared/i18n";
import { renderOpsShell } from "@/app/ops/shell";
import { mountOpsApp } from "@/features/ops/opsApp";
import type { IngestionBatchSummary, IngestionDocument } from "@/features/ops/opsTypes";

// ── Helpers ──────────────────────────────────────────────

function mockJsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

type MockDoc = Partial<IngestionDocument> & {
  doc_id: string;
  filename: string;
  status: string;
  stage: string;
};

type MockSession = {
  session_id: string;
  corpus: string;
  status: string;
  created_at: string;
  updated_at: string;
  documents: MockDoc[];
  batch_summary: IngestionBatchSummary;
  last_error: null;
  auto_processing?: boolean;
  [key: string]: unknown;
};

function summarizeSession(docs: MockDoc[]): IngestionBatchSummary {
  return {
    total: docs.length,
    queued: docs.filter((d) => d.status === "queued").length,
    processing: docs.filter((d) => d.status === "processing" || d.status === "in_progress").length,
    done: docs.filter((d) => d.status === "done" || d.status === "completed").length,
    failed: docs.filter((d) => d.status === "failed").length,
    skipped_duplicate: docs.filter((d) => d.status === "skipped_duplicate").length,
    pending_batch_gate: 0,
    bounced: docs.filter((d) => d.status === "bounced").length,
  };
}

function buildSession(id: string, docs: MockDoc[], overrides: Partial<MockSession> = {}): MockSession {
  return {
    session_id: id,
    corpus: "declaracion_renta",
    status: "ready",
    created_at: "2026-03-29T10:00:00Z",
    updated_at: "2026-03-29T10:00:00Z",
    documents: docs,
    batch_summary: summarizeSession(docs),
    last_error: null,
    ...overrides,
  };
}

function headerValue(headers: HeadersInit | undefined, key: string): string {
  if (!headers) return "";
  if (headers instanceof Headers) return headers.get(key) || "";
  if (Array.isArray(headers)) {
    const match = headers.find(([k]) => k.toLowerCase() === key.toLowerCase());
    return match?.[1] || "";
  }
  const raw = headers as Record<string, string>;
  const foundKey = Object.keys(raw).find((k) => k.toLowerCase() === key.toLowerCase());
  return foundKey ? raw[foundKey] || "" : "";
}

function makeFileList(files: File[]): FileList {
  const fileList = {
    length: files.length,
    item: (index: number) => files[index] || null,
    [Symbol.iterator]: function* iterator() {
      yield* files;
    },
  } as Record<number | "length" | "item" | typeof Symbol.iterator, unknown>;
  files.forEach((file, index) => {
    fileList[index] = file;
  });
  return fileList as unknown as FileList;
}

async function flushUi(): Promise<void> {
  await Promise.resolve();
  await new Promise((resolve) => window.setTimeout(resolve, 0));
  await Promise.resolve();
}

// ── Test suite ───────────────────────────────────────────

// Skipped: this entire suite tests the legacy kanban folder-upload flow.
// The Sesiones surface was rewritten in v2026-04-20-ui14 (see
// docs/guide/orchestration.md change log) and `renderIngestionShell` no longer
// emits the kanban DOM (`#ingestion-folder-input`, `#ingestion-select-folder`,
// `#ingestion-kanban`, etc.). The new Sesiones flow runs ingestion via
// `make phase2-graph-artifacts-supabase` against `knowledge_base/`, not via
// per-file browser uploads. Ingest-run coverage now lives in
// `tests/ingestOrganisms.test.ts` + `tests/test_ui_ingest_run_controllers.py`.
// The legacy `opsIngestionController` source is preserved pending removal per
// `docs/next/decouplingv1.md` Phase 7+.
describe.skip("folder ingestion (legacy kanban — see v2026-04-20-ui14)", () => {
  beforeEach(() => {
    document.body.innerHTML = `<div id="app">${renderOpsShell(createI18n("es-CO"))}</div>`;
    vi.restoreAllMocks();
    vi.spyOn(window, "setInterval").mockImplementation(
      ((..._args: Parameters<typeof window.setInterval>) => 1 as ReturnType<typeof window.setInterval>) as typeof window.setInterval,
    );
    vi.spyOn(window, "clearInterval").mockImplementation(
      ((_id: ReturnType<typeof window.setInterval>) => {}) as typeof window.clearInterval,
    );
    // Mock crypto.subtle.digest for pre-flight hashing
    if (!globalThis.crypto?.subtle?.digest) {
      const mockDigest = vi.fn(async () => new ArrayBuffer(32));
      vi.stubGlobal("crypto", {
        ...globalThis.crypto,
        subtle: { ...globalThis.crypto?.subtle, digest: mockDigest },
      });
    }
    try {
      window.localStorage.removeItem("lia_backstage_ops_active_tab");
      window.localStorage.removeItem("lia_backstage_ops_ingestion_session_id");
    } catch (_e) { /* ignore */ }
  });

  // ── Shell renders new elements ──

  it("renders folder input, select folder button, and ingest folder button", () => {
    expect(document.getElementById("ingestion-folder-input")).toBeTruthy();
    expect(document.getElementById("ingestion-select-folder")).toBeTruthy();
    expect(document.getElementById("ingestion-ingest-folder")).toBeTruthy();
    expect(document.getElementById("ingestion-upload-progress")).toBeTruthy();

    // Folder input has webkitdirectory attribute
    const folderInput = document.getElementById("ingestion-folder-input") as HTMLInputElement;
    expect(folderInput.hasAttribute("webkitdirectory")).toBe(true);
  });

  it("ingest folder button is disabled when no files are pending", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.startsWith("/api/corpora")) {
        return mockJsonResponse({
          corpora: [{ key: "declaracion_renta", label: "Renta", active: true }],
        });
      }
      if (url.startsWith("/api/ops/runs")) return mockJsonResponse({ runs: [] });
      if (url.startsWith("/api/ingestion/sessions?")) return mockJsonResponse({ sessions: [] });
      return mockJsonResponse({ ok: true });
    }));

    const root = document.getElementById("app")!;
    mountOpsApp(root, { i18n: createI18n("es-CO") });
    await flushUi();

    const btn = document.getElementById("ingestion-ingest-folder") as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
  });

  // ── Upload sends X-Upload-Relative-Path header ──

  it("sends X-Upload-Relative-Path header when uploading files with webkitRelativePath", async () => {
    const sessions = new Map<string, MockSession>();
    const session = buildSession("ing_folder_01", []);
    sessions.set(session.session_id, session);

    const capturedHeaders: Record<string, string>[] = [];

    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);

      if (url.startsWith("/api/corpora")) {
        return mockJsonResponse({
          corpora: [{ key: "declaracion_renta", label: "Renta", active: true }],
          default: "declaracion_renta",
        });
      }
      if (url.startsWith("/api/ops/runs")) {
        return mockJsonResponse({ runs: [] });
      }
      if (url.startsWith("/api/ingestion/sessions?")) {
        return mockJsonResponse({ sessions: Array.from(sessions.values()) });
      }
      if (url === "/api/ingestion/sessions" && init?.method === "POST") {
        return mockJsonResponse({ ok: true, session });
      }
      const sessionMatch = url.match(/^\/api\/ingestion\/sessions\/([^/]+)$/);
      if (sessionMatch && (!init?.method || init.method === "GET")) {
        const s = sessions.get(decodeURIComponent(sessionMatch[1]));
        return s ? mockJsonResponse({ ok: true, session: s }) : mockJsonResponse({ error: "not_found" }, 404);
      }
      const uploadMatch = url.match(/^\/api\/ingestion\/sessions\/([^/]+)\/files$/);
      if (uploadMatch && init?.method === "POST") {
        const headers: Record<string, string> = {};
        headers["X-Upload-Filename"] = headerValue(init.headers, "X-Upload-Filename");
        headers["X-Upload-Relative-Path"] = headerValue(init.headers, "X-Upload-Relative-Path");
        capturedHeaders.push(headers);

        const s = sessions.get(decodeURIComponent(uploadMatch[1]));
        if (!s) return mockJsonResponse({ error: "not_found" }, 404);
        const doc: MockDoc = {
          doc_id: `doc_${s.documents.length + 1}`,
          filename: headers["X-Upload-Filename"] || "file.txt",
          status: "queued",
          stage: "queued",
          bytes: 64,
          progress: 0,
          batch_type: "normative_base",
          updated_at: "2026-03-29T10:01:00Z",
          source_relative_path: headers["X-Upload-Relative-Path"] || null,
        };
        s.documents.push(doc);
        s.batch_summary = summarizeSession(s.documents);
        return mockJsonResponse({ ok: true, document: doc });
      }

      return mockJsonResponse({ ok: true });
    }));

    const root = document.getElementById("app")!;
    mountOpsApp(root, { i18n: createI18n("es-CO") });
    await flushUi();

    // Select the session
    const sessionBtn = document.querySelector(`[data-session-id="ing_folder_01"]`) as HTMLButtonElement;
    if (sessionBtn) {
      sessionBtn.click();
      await flushUi();
    }

    // Simulate folder input change with files that have webkitRelativePath
    const file1 = new File(["content1"], "ley_2277.pdf", { type: "application/pdf" });
    Object.defineProperty(file1, "webkitRelativePath", {
      value: "corpus_leyes/normativa/ley_2277.pdf",
      writable: false,
    });

    const folderInput = document.getElementById("ingestion-folder-input") as HTMLInputElement;
    Object.defineProperty(folderInput, "files", {
      configurable: true,
      value: makeFileList([file1]),
    });
    folderInput.dispatchEvent(new Event("change", { bubbles: true }));
    await flushUi();

    // Click upload
    const uploadBtn = document.getElementById("ingestion-upload-files") as HTMLButtonElement;
    uploadBtn?.click();
    await flushUi();

    // Verify the header was sent
    expect(capturedHeaders.length).toBeGreaterThanOrEqual(1);
    expect(capturedHeaders[0]["X-Upload-Relative-Path"]).toBe("corpus_leyes/normativa/ley_2277.pdf");
  });

  // ── Folder input filters unsupported extensions ──

  it("shows only supported files after folder selection (filters .DS_Store, hidden files)", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.startsWith("/api/corpora")) {
        return mockJsonResponse({
          corpora: [{ key: "declaracion_renta", label: "Renta", active: true }],
        });
      }
      if (url.startsWith("/api/ops/runs")) return mockJsonResponse({ runs: [] });
      if (url.startsWith("/api/ingestion/sessions?")) return mockJsonResponse({ sessions: [] });
      return mockJsonResponse({ ok: true });
    }));

    const root = document.getElementById("app")!;
    mountOpsApp(root, { i18n: createI18n("es-CO") });
    await flushUi();

    // Create files that would come from folder selection
    const validPdf = new File(["pdf"], "ley_2277.pdf", { type: "application/pdf" });
    const validMd = new File(["md"], "notes.md", { type: "text/markdown" });
    const validTxt = new File(["txt"], "readme.txt", { type: "text/plain" });
    const validDocx = new File(["docx"], "guide.docx");
    const dsStore = new File([""], ".DS_Store");
    const macOsx = new File([""], "__MACOSX");
    const hiddenFile = new File([""], ".hidden_file.md");
    const unsupported = new File([""], "image.png", { type: "image/png" });

    // Set webkitRelativePath on all of them
    for (const f of [validPdf, validMd, validTxt, validDocx, dsStore, macOsx, hiddenFile, unsupported]) {
      Object.defineProperty(f, "webkitRelativePath", { value: `folder/${f.name}`, writable: false });
    }

    const folderInput = document.getElementById("ingestion-folder-input") as HTMLInputElement;
    Object.defineProperty(folderInput, "files", {
      configurable: true,
      value: makeFileList([validPdf, validMd, validTxt, validDocx, dsStore, macOsx, hiddenFile, unsupported]),
    });
    folderInput.dispatchEvent(new Event("change", { bubbles: true }));
    await flushUi();

    // The dropzone should show exactly 4 files (the supported ones)
    const dropzone = document.getElementById("ingestion-dropzone");
    const fileRows = dropzone?.querySelectorAll(".dropzone-file-row");
    expect(fileRows?.length).toBe(4);
  });

  // ── Upload progress div appears during upload ──

  it("upload progress div is hidden by default", () => {
    const progress = document.getElementById("ingestion-upload-progress") as HTMLDivElement;
    expect(progress.hidden).toBe(true);
  });

  // ── Kanban card shows relative path ──

  it("renders source_relative_path on kanban cards when present", async () => {
    const docs: MockDoc[] = [
      {
        doc_id: "doc_1",
        filename: "ley_2277_2022.pdf",
        status: "done",
        stage: "done",
        bytes: 1024,
        progress: 100,
        batch_type: "normative_base",
        updated_at: "2026-03-29T10:05:00Z",
        source_relative_path: "corpus_leyes/normativa/ley_2277_2022.pdf",
      },
      {
        doc_id: "doc_2",
        filename: "analisis.md",
        status: "queued",
        stage: "queued",
        bytes: 512,
        progress: 0,
        batch_type: "interpretative_guidance",
        updated_at: "2026-03-29T10:04:00Z",
        // No source_relative_path
      },
    ];
    const session = buildSession("ing_kanban_01", docs);
    const sessions = new Map<string, MockSession>();
    sessions.set(session.session_id, session);

    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.startsWith("/api/corpora")) {
        return mockJsonResponse({
          corpora: [{ key: "declaracion_renta", label: "Renta", active: true }],
        });
      }
      if (url.startsWith("/api/ops/runs")) return mockJsonResponse({ runs: [] });
      if (url.startsWith("/api/ingestion/sessions?")) {
        return mockJsonResponse({ sessions: [session] });
      }
      const sessionMatch = url.match(/^\/api\/ingestion\/sessions\/([^/]+)$/);
      if (sessionMatch && (!init?.method || init.method === "GET")) {
        const s = sessions.get(decodeURIComponent(sessionMatch[1]));
        return s ? mockJsonResponse({ ok: true, session: s }) : mockJsonResponse({ error: "not_found" }, 404);
      }
      return mockJsonResponse({ ok: true });
    }));

    const root = document.getElementById("app")!;
    mountOpsApp(root, { i18n: createI18n("es-CO") });
    await flushUi();

    // Click on the session to load it
    const sessionBtn = document.querySelector(`[data-session-id="ing_kanban_01"]`) as HTMLButtonElement;
    sessionBtn?.click();
    await flushUi();

    // Check that relative path appears on the first card
    const kanban = document.getElementById("ingestion-kanban");
    const relPaths = kanban?.querySelectorAll(".kanban-card-relpath");
    expect(relPaths?.length).toBe(1);
    expect(relPaths?.[0]?.textContent).toBe("corpus_leyes/normativa/");

    // Second card should NOT have a relative path
    const cards = kanban?.querySelectorAll(".kanban-card");
    const secondCard = Array.from(cards || []).find((c) => c.getAttribute("data-doc-id") === "doc_2");
    expect(secondCard?.querySelector(".kanban-card-relpath")).toBeNull();
  });

  // ── Log accordion ──

  it("renders log accordion with verbose session details when session has documents", async () => {
    const docs: MockDoc[] = [
      {
        doc_id: "doc_ok",
        filename: "ley_ok.pdf",
        status: "done",
        stage: "complete",
        bytes: 2048,
        progress: 100,
        batch_type: "normative_base",
        updated_at: "2026-03-29T10:05:00Z",
        created_at: "2026-03-29T10:00:00Z",
        chunk_count: 12,
        elapsed_ms: 450,
        source_relative_path: "corpus/normativa/ley_ok.pdf",
      },
      {
        doc_id: "doc_fail",
        filename: "broken.pdf",
        status: "failed",
        stage: "failed",
        bytes: 64,
        progress: 18,
        batch_type: "normative_base",
        updated_at: "2026-03-29T10:03:00Z",
        created_at: "2026-03-29T10:00:00Z",
        error: {
          code: "parse_error_pdf",
          message: "PDF parsing failed",
          guidance: "Verify PDF integrity",
          next_step: "Replace with a valid PDF",
        },
      },
    ];
    const session = buildSession("ing_log_01", docs);
    const sessions = new Map<string, MockSession>();
    sessions.set(session.session_id, session);

    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.startsWith("/api/corpora")) {
        return mockJsonResponse({
          corpora: [{ key: "declaracion_renta", label: "Renta", active: true }],
        });
      }
      if (url.startsWith("/api/ops/runs")) return mockJsonResponse({ runs: [] });
      if (url.startsWith("/api/ingestion/sessions?")) {
        return mockJsonResponse({ sessions: [session] });
      }
      const sessionMatch = url.match(/^\/api\/ingestion\/sessions\/([^/]+)$/);
      if (sessionMatch && (!init?.method || init.method === "GET")) {
        const s = sessions.get(decodeURIComponent(sessionMatch[1]));
        return s ? mockJsonResponse({ ok: true, session: s }) : mockJsonResponse({ error: "not_found" }, 404);
      }
      return mockJsonResponse({ ok: true });
    }));

    const root = document.getElementById("app")!;
    mountOpsApp(root, { i18n: createI18n("es-CO") });
    await flushUi();

    // Select the session
    const sessionBtn = document.querySelector(`[data-session-id="ing_log_01"]`) as HTMLButtonElement;
    sessionBtn?.click();
    await flushUi();

    // Log accordion should be visible
    const accordion = document.getElementById("ingestion-log-accordion") as HTMLDetailsElement;
    expect(accordion.hidden).toBe(false);

    // Open the accordion
    accordion.open = true;
    const logBody = document.getElementById("ingestion-log-body") as HTMLPreElement;
    const logText = logBody.textContent || "";

    // Verify verbose content
    expect(logText).toContain("ing_log_01");
    expect(logText).toContain("ley_ok.pdf");
    expect(logText).toContain("broken.pdf");
    expect(logText).toContain("corpus/normativa/ley_ok.pdf");  // relative path
    expect(logText).toContain("parse_error_pdf");               // error code
    expect(logText).toContain("PDF parsing failed");            // error message
    expect(logText).toContain("Verify PDF integrity");          // guidance
    expect(logText).toContain("Chunks");                        // chunk info for done doc
    expect(logText).toContain("ERROR");                         // error marker

    // Copy button exists
    const copyBtn = document.getElementById("ingestion-log-copy") as HTMLButtonElement;
    expect(copyBtn).toBeTruthy();
  });

  it("hides log accordion when no session is selected", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.startsWith("/api/corpora")) {
        return mockJsonResponse({
          corpora: [{ key: "declaracion_renta", label: "Renta", active: true }],
        });
      }
      if (url.startsWith("/api/ops/runs")) return mockJsonResponse({ runs: [] });
      if (url.startsWith("/api/ingestion/sessions?")) return mockJsonResponse({ sessions: [] });
      return mockJsonResponse({ ok: true });
    }));

    const root = document.getElementById("app")!;
    mountOpsApp(root, { i18n: createI18n("es-CO") });
    await flushUi();

    const accordion = document.getElementById("ingestion-log-accordion") as HTMLDetailsElement;
    expect(accordion.hidden).toBe(true);
  });

  // ── Upload failure error surfacing ──

  it("surfaces upload errors in flash when all uploads fail", async () => {
    const session = buildSession("ing_fail_all", []);
    const sessions = new Map<string, MockSession>();
    sessions.set(session.session_id, session);

    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.startsWith("/api/corpora")) {
        return mockJsonResponse({
          corpora: [{ key: "declaracion_renta", label: "Renta", active: true }],
        });
      }
      if (url.startsWith("/api/ops/runs")) return mockJsonResponse({ runs: [] });
      if (url.startsWith("/api/ingestion/sessions?")) {
        return mockJsonResponse({ sessions: Array.from(sessions.values()) });
      }
      if (url === "/api/ingestion/sessions" && init?.method === "POST") {
        return mockJsonResponse({ ok: true, session });
      }
      // Pre-flight endpoint: all files are "new"
      if (url === "/api/ingestion/preflight" && init?.method === "POST") {
        const body = JSON.parse(typeof init.body === "string" ? init.body : "{}");
        const files = body.files || [];
        return mockJsonResponse({
          ok: true,
          manifest: {
            artifacts: [],
            duplicates: [],
            revisions: [],
            new_files: files.map((f: { filename: string; relative_path: string; size: number; content_hash: string }) => ({
              ...f, category: "new", reason: "Documento nuevo",
              existing_doc_id: null, existing_filename: null, existing_chunk_count: null, revision_direction: null,
            })),
            scanned: files.length,
            elapsed_ms: 10,
          },
        });
      }
      const sessionMatch = url.match(/^\/api\/ingestion\/sessions\/([^/]+)$/);
      if (sessionMatch && (!init?.method || init.method === "GET")) {
        const s = sessions.get(decodeURIComponent(sessionMatch[1]));
        return s ? mockJsonResponse({ ok: true, session: s }) : mockJsonResponse({ error: "not_found" }, 404);
      }
      // ALL uploads fail with 400
      const uploadMatch = url.match(/\/files$/);
      if (uploadMatch && init?.method === "POST") {
        return mockJsonResponse({ error: "Body vacio en upload." }, 400);
      }
      return mockJsonResponse({ ok: true });
    }));

    const root = document.getElementById("app")!;
    mountOpsApp(root, { i18n: createI18n("es-CO") });
    await flushUi();

    // Select session
    const sessionBtn = document.querySelector(`[data-session-id="ing_fail_all"]`) as HTMLButtonElement;
    sessionBtn?.click();
    await flushUi();

    // Add folder files
    const file1 = new File(["a"], "bad1.pdf", { type: "application/pdf" });
    const file2 = new File(["b"], "bad2.pdf", { type: "application/pdf" });
    Object.defineProperty(file1, "webkitRelativePath", { value: "test/bad1.pdf", writable: false });
    Object.defineProperty(file2, "webkitRelativePath", { value: "test/bad2.pdf", writable: false });

    const folderInput = document.getElementById("ingestion-folder-input") as HTMLInputElement;
    Object.defineProperty(folderInput, "files", {
      configurable: true,
      value: makeFileList([file1, file2]),
    });
    folderInput.dispatchEvent(new Event("change", { bubbles: true }));
    await flushUi();

    // Click Ingerir carpeta → triggers preflight scan + review
    const ingestBtn = document.getElementById("ingestion-ingest-folder") as HTMLButtonElement;
    ingestBtn?.click();
    await new Promise((resolve) => window.setTimeout(resolve, 50));
    await flushUi();

    // Preflight review should appear — click "Ingerir N archivos" to proceed to upload
    const preflightIngestBtn = document.getElementById("preflight-ingest-btn") as HTMLButtonElement;
    preflightIngestBtn?.click();
    await new Promise((resolve) => window.setTimeout(resolve, 50));
    await flushUi();

    // Flash should show error with file names
    const flash = document.getElementById("ingestion-flash");
    const flashText = flash?.textContent || "";
    expect(flash?.hidden).toBe(false);
    expect(flashText).toContain("bad1.pdf");
  });

  it("surfaces partial upload failures with error details in flash", async () => {
    const session = buildSession("ing_partial", []);
    const sessions = new Map<string, MockSession>();
    sessions.set(session.session_id, session);
    let uploadCount = 0;

    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.startsWith("/api/corpora")) {
        return mockJsonResponse({
          corpora: [{ key: "declaracion_renta", label: "Renta", active: true }],
        });
      }
      if (url.startsWith("/api/ops/runs")) return mockJsonResponse({ runs: [] });
      if (url.startsWith("/api/ingestion/sessions?")) {
        return mockJsonResponse({ sessions: Array.from(sessions.values()) });
      }
      if (url === "/api/ingestion/sessions" && init?.method === "POST") {
        return mockJsonResponse({ ok: true, session });
      }
      // Pre-flight endpoint: all files are "new"
      if (url === "/api/ingestion/preflight" && init?.method === "POST") {
        const body = JSON.parse(typeof init.body === "string" ? init.body : "{}");
        const files = body.files || [];
        return mockJsonResponse({
          ok: true,
          manifest: {
            artifacts: [],
            duplicates: [],
            revisions: [],
            new_files: files.map((f: { filename: string; relative_path: string; size: number; content_hash: string }) => ({
              ...f, category: "new", reason: "Documento nuevo",
              existing_doc_id: null, existing_filename: null, existing_chunk_count: null, revision_direction: null,
            })),
            scanned: files.length,
            elapsed_ms: 10,
          },
        });
      }
      const sessionMatch = url.match(/^\/api\/ingestion\/sessions\/([^/]+)$/);
      if (sessionMatch && (!init?.method || init.method === "GET")) {
        const s = sessions.get(decodeURIComponent(sessionMatch[1]));
        return s ? mockJsonResponse({ ok: true, session: s }) : mockJsonResponse({ error: "not_found" }, 404);
      }
      const uploadMatch = url.match(/\/files$/);
      if (uploadMatch && init?.method === "POST") {
        uploadCount++;
        // First file succeeds, second fails
        if (uploadCount === 1) {
          const s = sessions.get("ing_partial")!;
          const doc: MockDoc = {
            doc_id: "doc_1",
            filename: headerValue(init.headers, "X-Upload-Filename"),
            status: "queued",
            stage: "queued",
            bytes: 64,
            progress: 0,
          };
          s.documents.push(doc);
          s.batch_summary = summarizeSession(s.documents);
          return mockJsonResponse({ ok: true, document: doc });
        }
        return mockJsonResponse({ error: "upload_failed" }, 500);
      }
      // auto-process + process
      if (url.match(/auto-process/) || url.match(/\/process$/)) {
        return mockJsonResponse({ ok: true });
      }
      return mockJsonResponse({ ok: true });
    }));

    const root = document.getElementById("app")!;
    mountOpsApp(root, { i18n: createI18n("es-CO") });
    await flushUi();

    const sessionBtn = document.querySelector(`[data-session-id="ing_partial"]`) as HTMLButtonElement;
    sessionBtn?.click();
    await flushUi();

    const file1 = new File(["ok"], "good.md", { type: "text/markdown" });
    const file2 = new File(["bad"], "broken.pdf", { type: "application/pdf" });
    Object.defineProperty(file1, "webkitRelativePath", { value: "test/good.md", writable: false });
    Object.defineProperty(file2, "webkitRelativePath", { value: "test/broken.pdf", writable: false });

    const folderInput = document.getElementById("ingestion-folder-input") as HTMLInputElement;
    Object.defineProperty(folderInput, "files", {
      configurable: true,
      value: makeFileList([file1, file2]),
    });
    folderInput.dispatchEvent(new Event("change", { bubbles: true }));
    await flushUi();

    // Click Ingerir carpeta → triggers preflight
    const ingestBtn = document.getElementById("ingestion-ingest-folder") as HTMLButtonElement;
    ingestBtn?.click();
    await new Promise((resolve) => window.setTimeout(resolve, 50));
    await flushUi();

    // Click through preflight review → "Ingerir N archivos"
    const preflightIngestBtn = document.getElementById("preflight-ingest-btn") as HTMLButtonElement;
    preflightIngestBtn?.click();
    await new Promise((resolve) => window.setTimeout(resolve, 50));
    await flushUi();

    // Flash should indicate partial failure
    const flash = document.getElementById("ingestion-flash");
    expect(flash?.hidden).toBe(false);
    // Should mention failure count
    expect(flash?.textContent).toContain("fallido");
  });

  // ── Auto-status element ──

  it("renders auto-status element in DOM", () => {
    expect(document.getElementById("ingestion-auto-status")).toBeTruthy();
  });

  // ── "Ingerir carpeta" compound flow ──

  it("ingest folder button triggers preflight + direct upload when all files are new", async () => {
    const sessions = new Map<string, MockSession>();
    const session = buildSession("ing_compound_01", []);
    sessions.set(session.session_id, session);

    const apiCalls: string[] = [];

    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);

      if (url.startsWith("/api/corpora")) {
        return mockJsonResponse({
          corpora: [{ key: "declaracion_renta", label: "Renta", active: true }],
        });
      }
      if (url.startsWith("/api/ops/runs")) return mockJsonResponse({ runs: [] });
      if (url.startsWith("/api/ingestion/sessions?")) {
        return mockJsonResponse({ sessions: Array.from(sessions.values()) });
      }
      if (url === "/api/ingestion/sessions" && init?.method === "POST") {
        return mockJsonResponse({ ok: true, session });
      }
      // Pre-flight endpoint: all files are "new" (no interesting findings)
      if (url === "/api/ingestion/preflight" && init?.method === "POST") {
        apiCalls.push("preflight");
        const body = JSON.parse(typeof init.body === "string" ? init.body : "{}");
        const files = body.files || [];
        return mockJsonResponse({
          ok: true,
          manifest: {
            artifacts: [],
            duplicates: [],
            revisions: [],
            new_files: files.map((f: { filename: string; relative_path: string; size: number; content_hash: string }) => ({
              ...f, category: "new", reason: "Documento nuevo",
              existing_doc_id: null, existing_filename: null, existing_chunk_count: null, revision_direction: null,
            })),
            scanned: files.length,
            elapsed_ms: 10,
          },
        });
      }
      const sessionMatch = url.match(/^\/api\/ingestion\/sessions\/([^/]+)$/);
      if (sessionMatch && (!init?.method || init.method === "GET")) {
        const s = sessions.get(decodeURIComponent(sessionMatch[1]));
        return s ? mockJsonResponse({ ok: true, session: s }) : mockJsonResponse({ error: "not_found" }, 404);
      }
      const uploadMatch = url.match(/^\/api\/ingestion\/sessions\/([^/]+)\/files$/);
      if (uploadMatch && init?.method === "POST") {
        apiCalls.push("upload");
        const s = sessions.get(decodeURIComponent(uploadMatch[1]))!;
        const doc: MockDoc = {
          doc_id: `doc_${s.documents.length + 1}`,
          filename: headerValue(init.headers, "X-Upload-Filename"),
          status: "queued",
          stage: "queued",
          bytes: 64,
          progress: 0,
        };
        s.documents.push(doc);
        s.batch_summary = summarizeSession(s.documents);
        return mockJsonResponse({ ok: true, document: doc });
      }
      const autoProcessMatch = url.match(/\/auto-process$/);
      if (autoProcessMatch && init?.method === "POST") {
        apiCalls.push("auto-process");
        return mockJsonResponse({ ok: true, auto_processing: true });
      }
      const processMatch = url.match(/\/process$/);
      if (processMatch && init?.method === "POST") {
        apiCalls.push("process");
        return mockJsonResponse({ ok: true, started: true });
      }

      return mockJsonResponse({ ok: true });
    }));

    const root = document.getElementById("app")!;
    mountOpsApp(root, { i18n: createI18n("es-CO") });
    await flushUi();

    // Select the session
    const sessionBtn = document.querySelector(`[data-session-id="ing_compound_01"]`) as HTMLButtonElement;
    if (sessionBtn) {
      sessionBtn.click();
      await flushUi();
    }

    // Simulate folder selection with two files
    const file1 = new File(["a"], "ley_2277.pdf", { type: "application/pdf" });
    const file2 = new File(["b"], "notes.md", { type: "text/markdown" });
    Object.defineProperty(file1, "webkitRelativePath", { value: "leyes/ley_2277.pdf", writable: false });
    Object.defineProperty(file2, "webkitRelativePath", { value: "leyes/notes.md", writable: false });

    const folderInput = document.getElementById("ingestion-folder-input") as HTMLInputElement;
    Object.defineProperty(folderInput, "files", {
      configurable: true,
      value: makeFileList([file1, file2]),
    });
    folderInput.dispatchEvent(new Event("change", { bubbles: true }));
    await flushUi();

    // Click "Ingerir carpeta" → preflight runs, finds all new, skips review, uploads directly
    const ingestBtn = document.getElementById("ingestion-ingest-folder") as HTMLButtonElement;
    ingestBtn?.click();
    await new Promise((resolve) => window.setTimeout(resolve, 50));
    await flushUi();

    // Wait for uploads to settle
    await new Promise((resolve) => window.setTimeout(resolve, 100));
    await flushUi();

    // Preflight was called but since all files are new, it went straight to upload
    expect(apiCalls).toContain("preflight");
    expect(apiCalls.filter((c) => c === "upload").length).toBe(2);
    expect(apiCalls).toContain("auto-process");
    expect(apiCalls).toContain("process");

    // auto-process should come after all uploads
    const lastUploadIdx = apiCalls.lastIndexOf("upload");
    const autoProcessIdx = apiCalls.indexOf("auto-process");
    expect(autoProcessIdx).toBeGreaterThan(lastUploadIdx);
  });

  it("shows clear message when all files are bounced (already in corpus)", async () => {
    const sessions = new Map<string, MockSession>();

    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.startsWith("/api/corpora")) {
        return mockJsonResponse({
          corpora: [{ key: "declaracion_renta", label: "Renta", active: true }],
        });
      }
      if (url.startsWith("/api/ops/runs")) return mockJsonResponse({ runs: [] });
      if (url.startsWith("/api/ingestion/sessions?")) {
        return mockJsonResponse({ sessions: Array.from(sessions.values()) });
      }
      if (url === "/api/ingestion/sessions" && init?.method === "POST") {
        const session = buildSession("ing_bounce_test", []);
        sessions.set(session.session_id, session);
        return mockJsonResponse({ ok: true, session });
      }
      // Preflight: all files are duplicates (ledger match)
      if (url === "/api/ingestion/preflight" && init?.method === "POST") {
        const body = JSON.parse(typeof init.body === "string" ? init.body : "{}");
        const files = body.files || [];
        return mockJsonResponse({
          ok: true,
          manifest: {
            artifacts: [],
            duplicates: files.map((f: { filename: string; relative_path: string; size: number; content_hash: string }) => ({
              ...f, category: "exact_duplicate",
              reason: `Ya ingresado como ing_${f.filename.replace(/\W/g, "_")}`,
              existing_doc_id: `ing_${f.filename.replace(/\W/g, "_")}`,
              existing_filename: null, existing_chunk_count: 5, revision_direction: null,
            })),
            revisions: [],
            new_files: [],
            scanned: files.length,
            elapsed_ms: 10,
          },
        });
      }
      const sessionMatch = url.match(/^\/api\/ingestion\/sessions\/([^/]+)$/);
      if (sessionMatch && (!init?.method || init.method === "GET")) {
        const s = sessions.get(decodeURIComponent(sessionMatch[1]));
        return s ? mockJsonResponse({ ok: true, session: s }) : mockJsonResponse({ error: "not_found" }, 404);
      }
      return mockJsonResponse({ ok: true });
    }));

    const root = document.getElementById("app")!;
    mountOpsApp(root, { i18n: createI18n("es-CO") });
    await flushUi();

    // Select folder with 2 files
    const file1 = new File(["a"], "ley_123.md", { type: "text/markdown" });
    const file2 = new File(["b"], "ley_456.md", { type: "text/markdown" });
    Object.defineProperty(file1, "webkitRelativePath", { value: "test/ley_123.md", writable: false });
    Object.defineProperty(file2, "webkitRelativePath", { value: "test/ley_456.md", writable: false });

    const folderInput = document.getElementById("ingestion-folder-input") as HTMLInputElement;
    Object.defineProperty(folderInput, "files", { configurable: true, value: makeFileList([file1, file2]) });
    folderInput.dispatchEvent(new Event("change", { bubbles: true }));
    await flushUi();

    // Click "Ingerir carpeta" → preflight finds duplicates → shows review
    const ingestBtn = document.getElementById("ingestion-ingest-folder") as HTMLButtonElement;
    expect(ingestBtn.disabled).toBe(false);
    ingestBtn?.click();
    await new Promise((resolve) => window.setTimeout(resolve, 100));
    await flushUi();

    // Should show preflight review with duplicates (since all are exact_duplicate)
    const reviewArea = document.getElementById("ingestion-upload-progress")!;
    expect(reviewArea.hidden).toBe(false);
    expect(reviewArea.textContent).toContain("duplicado");
  });

  it("does not reuse completed sessions", async () => {
    const completedSession = buildSession("ing_completed", [], { status: "completed" });
    const sessions = new Map<string, MockSession>();
    sessions.set(completedSession.session_id, completedSession);
    let newSessionCreated = false;

    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.startsWith("/api/corpora")) {
        return mockJsonResponse({
          corpora: [{ key: "declaracion_renta", label: "Renta", active: true }],
        });
      }
      if (url.startsWith("/api/ops/runs")) return mockJsonResponse({ runs: [] });
      if (url.startsWith("/api/ingestion/sessions?")) {
        return mockJsonResponse({ sessions: Array.from(sessions.values()) });
      }
      if (url === "/api/ingestion/sessions" && init?.method === "POST") {
        newSessionCreated = true;
        const session = buildSession("ing_fresh_new", []);
        sessions.set(session.session_id, session);
        return mockJsonResponse({ ok: true, session });
      }
      if (url === "/api/ingestion/preflight" && init?.method === "POST") {
        const body = JSON.parse(typeof init.body === "string" ? init.body : "{}");
        const files = body.files || [];
        return mockJsonResponse({
          ok: true,
          manifest: {
            artifacts: [], duplicates: [], revisions: [],
            new_files: files.map((f: { filename: string; relative_path: string; size: number; content_hash: string }) => ({
              ...f, category: "new", reason: "Documento nuevo",
              existing_doc_id: null, existing_filename: null, existing_chunk_count: null, revision_direction: null,
            })),
            scanned: files.length, elapsed_ms: 5,
          },
        });
      }
      const sessionMatch = url.match(/^\/api\/ingestion\/sessions\/([^/]+)$/);
      if (sessionMatch && (!init?.method || init.method === "GET")) {
        const s = sessions.get(decodeURIComponent(sessionMatch[1]));
        return s ? mockJsonResponse({ ok: true, session: s }) : mockJsonResponse({ error: "not_found" }, 404);
      }
      // Upload, auto-process, process
      if (url.match(/\/files$/) && init?.method === "POST") {
        const s = sessions.get("ing_fresh_new")!;
        const doc: MockDoc = {
          doc_id: `doc_${s.documents.length + 1}`,
          filename: headerValue(init.headers, "X-Upload-Filename"),
          status: "queued", stage: "queued", bytes: 64, progress: 0,
        };
        s.documents.push(doc);
        s.batch_summary = summarizeSession(s.documents);
        return mockJsonResponse({ ok: true, document: doc });
      }
      if (url.match(/auto-process/) || url.match(/\/process$/)) {
        return mockJsonResponse({ ok: true });
      }
      return mockJsonResponse({ ok: true });
    }));

    const root = document.getElementById("app")!;
    mountOpsApp(root, { i18n: createI18n("es-CO") });
    await flushUi();

    // Select the completed session
    const sessionBtn = document.querySelector(`[data-session-id="ing_completed"]`) as HTMLButtonElement;
    sessionBtn?.click();
    await flushUi();

    // Add a folder file
    const file1 = new File(["a"], "new_doc.md", { type: "text/markdown" });
    Object.defineProperty(file1, "webkitRelativePath", { value: "test/new_doc.md", writable: false });
    const folderInput = document.getElementById("ingestion-folder-input") as HTMLInputElement;
    Object.defineProperty(folderInput, "files", { configurable: true, value: makeFileList([file1]) });
    folderInput.dispatchEvent(new Event("change", { bubbles: true }));
    await flushUi();

    // Click "Ingerir carpeta" → should create NEW session (not reuse completed)
    const ingestBtn = document.getElementById("ingestion-ingest-folder") as HTMLButtonElement;
    ingestBtn?.click();
    await new Promise((resolve) => window.setTimeout(resolve, 150));
    await flushUi();

    expect(newSessionCreated).toBe(true);
  });
});
