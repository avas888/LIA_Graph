import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderBackstageShell, renderIngestionShell, renderOpsShell } from "@/app/ops/shell";
import { mountOpsApp } from "@/features/ops/opsApp";
import { createI18n } from "@/shared/i18n";

type MockDoc = {
  doc_id: string;
  filename: string;
  bytes: number;
  status: string;
  stage: string;
  progress: number;
  batch_type: string;
  error?: { code?: string; message?: string; guidance?: string; next_step?: string } | null;
  updated_at: string;
};

type MockSession = {
  session_id: string;
  corpus: string;
  status: string;
  created_at: string;
  updated_at: string;
  documents: MockDoc[];
  batch_summary: {
    total: number;
    queued: number;
    processing: number;
    done: number;
    failed: number;
    skipped_duplicate: number;
    pending_batch_gate: number;
  };
  last_error?: { code?: string; message?: string; guidance?: string; next_step?: string } | null;
};

function mockJsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function summarizeSession(docs: MockDoc[]) {
  return {
    total: docs.length,
    queued: docs.filter((doc) => doc.status === "queued").length,
    processing: docs.filter((doc) => doc.status === "in_progress").length,
    done: docs.filter((doc) => doc.status === "done").length,
    failed: docs.filter((doc) => doc.status === "failed").length,
    skipped_duplicate: docs.filter((doc) => doc.status === "skipped_duplicate").length,
    pending_batch_gate: docs.filter((doc) => doc.status === "done_pending_batch_gate").length,
  };
}

function buildSession(sessionId: string, documents: MockDoc[], overrides: Partial<MockSession> = {}): MockSession {
  return {
    session_id: sessionId,
    corpus: "declaracion_renta",
    status: "ready",
    created_at: "2026-03-10T10:00:00Z",
    updated_at: "2026-03-10T10:00:00Z",
    documents,
    batch_summary: summarizeSession(documents),
    last_error: null,
    ...overrides,
  };
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

function headerValue(headers: HeadersInit | undefined, key: string): string {
  if (!headers) return "";
  if (headers instanceof Headers) {
    return headers.get(key) || "";
  }
  if (Array.isArray(headers)) {
    const match = headers.find(([candidate]) => candidate.toLowerCase() === key.toLowerCase());
    return match?.[1] || "";
  }
  const raw = headers as Record<string, string>;
  const foundKey = Object.keys(raw).find((candidate) => candidate.toLowerCase() === key.toLowerCase());
  return foundKey ? raw[foundKey] || "" : "";
}

describe("ops app", () => {
  beforeEach(() => {
    document.body.innerHTML = `<div id="app">${renderOpsShell(createI18n("es-CO"))}</div>`;
    vi.restoreAllMocks();
    vi.spyOn(window, "setInterval").mockImplementation(
      ((..._args: Parameters<typeof window.setInterval>) => 1 as ReturnType<typeof window.setInterval>) as typeof window.setInterval
    );
    vi.spyOn(window, "clearInterval").mockImplementation(
      ((_id: ReturnType<typeof window.setInterval>) => {}) as typeof window.clearInterval
    );
    try {
      window.localStorage.removeItem("lia_backstage_ops_active_tab");
      window.localStorage.removeItem("lia_backstage_ops_ingestion_session_id");
    } catch (_error) {
      // Ignore storage failures in jsdom.
    }
  });

  it("creates a session, uploads files, and starts ingestion processing from Backstage Ops", async () => {
    const sessions = new Map<string, MockSession>();
    const initial = buildSession("ing_prev_01", []);
    sessions.set(initial.session_id, initial);
    let sessionCounter = 2;

    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);

        if (url.startsWith("/api/corpora")) {
          return mockJsonResponse({
            corpora: [
              { key: "declaracion_renta", label: "Declaración de Renta", active: true },
              { key: "iva", label: "IVA", active: false },
            ],
            default: "declaracion_renta",
          });
        }

        if (url.startsWith("/api/ops/runs")) {
          return mockJsonResponse({
            runs: [
              {
                run_id: "pc_run_01",
                trace_id: "trace_01",
                status: "completed",
                started_at: "2026-03-10T09:00:00Z",
              },
            ],
          });
        }

        if (url.startsWith("/api/ingestion/sessions?")) {
          return mockJsonResponse({
            sessions: Array.from(sessions.values()).sort((left, right) => right.session_id.localeCompare(left.session_id)),
          });
        }

        if (url === "/api/ingestion/sessions" && init?.method === "POST") {
          const raw = String(init.body || "{}");
          const payload = JSON.parse(raw) as { corpus?: string };
          const sessionId = `ing_new_${sessionCounter += 1}`;
          const next = buildSession(sessionId, [], {
            corpus: payload.corpus || "declaracion_renta",
            created_at: "2026-03-10T10:10:00Z",
            updated_at: "2026-03-10T10:10:00Z",
          });
          sessions.set(sessionId, next);
          return mockJsonResponse({ ok: true, session: next });
        }

        const sessionMatch = url.match(/^\/api\/ingestion\/sessions\/([^/]+)$/);
        if (sessionMatch && (!init || !init.method || init.method === "GET")) {
          const session = sessions.get(decodeURIComponent(sessionMatch[1]));
          if (!session) return mockJsonResponse({ error: "session_not_found" }, 404);
          return mockJsonResponse({ ok: true, session });
        }

        const uploadMatch = url.match(/^\/api\/ingestion\/sessions\/([^/]+)\/files$/);
        if (uploadMatch && init?.method === "POST") {
          const session = sessions.get(decodeURIComponent(uploadMatch[1]));
          if (!session) return mockJsonResponse({ error: "session_not_found" }, 404);
          const filename = headerValue(init.headers, "X-Upload-Filename") || "upload.txt";
          const batchType = headerValue(init.headers, "X-Upload-Batch-Type") || "normative_base";
          const nextDoc: MockDoc = {
            doc_id: `doc_${session.documents.length + 1}`,
            filename,
            bytes: 128,
            status: "queued",
            stage: "queued",
            progress: 0,
            batch_type: batchType,
            updated_at: "2026-03-10T10:12:00Z",
            error: null,
          };
          session.documents.push(nextDoc);
          session.updated_at = "2026-03-10T10:12:00Z";
          session.batch_summary = summarizeSession(session.documents);
          return mockJsonResponse({ ok: true, document: nextDoc });
        }

        const processMatch = url.match(/^\/api\/ingestion\/sessions\/([^/]+)\/process$/);
        if (processMatch && init?.method === "POST") {
          const session = sessions.get(decodeURIComponent(processMatch[1]));
          if (!session) return mockJsonResponse({ error: "session_not_found" }, 404);
          session.status = "processing";
          session.updated_at = "2026-03-10T10:13:00Z";
          return mockJsonResponse({ ok: true, started: true, status: session.status });
        }

        throw new Error(`Unexpected fetch: ${url}`);
      })
    );

    const root = document.getElementById("app");
    if (!root) {
      throw new Error("Missing app root.");
    }

    mountOpsApp(root, { i18n: createI18n("es-CO") });
    await flushUi();
    await flushUi();

    expect(document.getElementById("ops-panel-monitor")?.hidden).toBe(false);
    expect(document.getElementById("ops-panel-ingestion")?.hidden).toBe(true);

    const ingestionTab = document.getElementById("ops-tab-ingestion") as HTMLButtonElement | null;
    ingestionTab?.click();
    await flushUi();

    expect(document.getElementById("ops-panel-monitor")?.hidden).toBe(true);
    expect(document.getElementById("ops-panel-ingestion")?.hidden).toBe(false);
    expect(document.getElementById("ingestion-pending-files")?.textContent).toContain("Sin archivos seleccionados");
    expect(document.getElementById("ingestion-sessions-list")?.textContent).toContain("ing_prev_01");

    const createBtn = document.getElementById("ingestion-create-session") as HTMLButtonElement | null;
    createBtn?.click();
    await flushUi();
    await flushUi();

    const selectedMeta = document.getElementById("selected-session-meta");
    expect(selectedMeta?.textContent).toContain("ing_new_3");

    const batchSelect = document.getElementById("ingestion-batch-type") as HTMLSelectElement | null;
    if (!batchSelect) {
      throw new Error("Missing batch type select.");
    }
    batchSelect.value = "interpretative_guidance";

    const input = document.getElementById("ingestion-file-input") as HTMLInputElement | null;
    if (!input) {
      throw new Error("Missing file input.");
    }
    const file = new File(["contenido"], "doctrina-pwc.txt", { type: "text/plain" });
    Object.defineProperty(input, "files", {
      configurable: true,
      value: makeFileList([file]),
    });
    input.dispatchEvent(new Event("change", { bubbles: true }));
    await flushUi();

    // Pending files are now rendered inside the dropzone as a visual list
    expect(document.getElementById("ingestion-dropzone")?.textContent).toContain("doctrina-pwc.txt");

    const uploadBtn = document.getElementById("ingestion-upload-files") as HTMLButtonElement | null;
    uploadBtn?.click();
    await flushUi();
    await flushUi();

    expect(document.getElementById("ingestion-kanban")?.textContent).toContain("doctrina-pwc.txt");
    expect(document.getElementById("ingestion-kanban")?.textContent).toContain("Interpretación");
    expect(document.getElementById("ingestion-flash")?.textContent).toContain("Se cargaron 1 archivo(s)");

    const processBtn = document.getElementById("ingestion-process-session") as HTMLButtonElement | null;
    processBtn?.click();
    await flushUi();
    await flushUi();

    expect(document.getElementById("selected-session-meta")?.textContent).toContain("queued 1");
    expect(document.getElementById("ingestion-flash")?.textContent).toContain("quedó en ejecución");
  });

  it("removes failed documents from the selected ingestion session", async () => {
    const failedSession = buildSession(
      "ing_failed_01",
      [
        {
          doc_id: "doc_failed_01",
          filename: "resolucion-dañada.pdf",
          bytes: 2048,
          status: "failed",
          stage: "failed",
          progress: 17,
          batch_type: "normative_base",
          updated_at: "2026-03-10T11:00:00Z",
          error: {
            code: "parse_error_pdf",
            message: "Falló el parseo de PDF.",
            guidance: "Revisa integridad del PDF.",
            next_step: "Corrige y reintenta.",
          },
        },
      ],
      {
        last_error: {
          code: "parse_error_pdf",
          message: "Falló el parseo de PDF.",
          guidance: "Revisa integridad del PDF.",
          next_step: "Corrige y reintenta.",
        },
      }
    );
    const sessions = new Map<string, MockSession>([[failedSession.session_id, failedSession]]);

    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);

        if (url.startsWith("/api/corpora")) {
          return mockJsonResponse({
            corpora: [{ key: "declaracion_renta", label: "Declaración de Renta", active: true }],
            default: "declaracion_renta",
          });
        }

        if (url.startsWith("/api/ops/runs")) {
          return mockJsonResponse({ runs: [] });
        }

        if (url.startsWith("/api/ingestion/sessions?")) {
          return mockJsonResponse({ sessions: Array.from(sessions.values()) });
        }

        const sessionMatch = url.match(/^\/api\/ingestion\/sessions\/([^/]+)$/);
        if (sessionMatch && (!init || !init.method || init.method === "GET")) {
          return mockJsonResponse({ ok: true, session: sessions.get(sessionMatch[1]) });
        }

        const deleteMatch = url.match(/^\/api\/ingestion\/sessions\/([^/]+)\/delete-failed$/);
        if (deleteMatch && init?.method === "POST") {
          const session = sessions.get(deleteMatch[1]);
          if (!session) return mockJsonResponse({ error: "session_not_found" }, 404);
          const removed = session.documents.filter((doc) => doc.status === "failed").length;
          session.documents = session.documents.filter((doc) => doc.status !== "failed");
          session.batch_summary = summarizeSession(session.documents);
          session.last_error = null;
          session.status = "ready";
          return mockJsonResponse({ ok: true, removed, status: session.status });
        }

        throw new Error(`Unexpected fetch: ${url}`);
      })
    );

    const root = document.getElementById("app");
    if (!root) {
      throw new Error("Missing app root.");
    }

    mountOpsApp(root, { i18n: createI18n("es-CO") });
    await flushUi();
    await flushUi();

    const ingestionTab = document.getElementById("ops-tab-ingestion") as HTMLButtonElement | null;
    ingestionTab?.click();
    await flushUi();

    expect(document.getElementById("ingestion-kanban")?.textContent).toContain("resolucion-dañada.pdf");
    expect(document.getElementById("ingestion-last-error")?.hidden).toBe(false);

    const deleteBtn = document.getElementById("ingestion-delete-failed") as HTMLButtonElement | null;
    deleteBtn?.click();
    await flushUi();
    await flushUi();

    expect(document.getElementById("ingestion-kanban")?.textContent).not.toContain("resolucion-dañada.pdf");
    expect(document.getElementById("ingestion-flash")?.textContent).toContain("Se eliminaron 1 fallidos");
  });

  it("renders user and technical cascade graphs after clicking a run", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);

        if (url.startsWith("/api/corpora")) {
          return mockJsonResponse({
            corpora: [{ key: "declaracion_renta", label: "Declaración de Renta", active: true }],
            default: "declaracion_renta",
          });
        }

        if (url.startsWith("/api/ingestion/sessions?")) {
          return mockJsonResponse({ sessions: [] });
        }

        if (url === "/api/ops/runs?limit=30") {
          return mockJsonResponse({
            runs: [
              {
                run_id: "pc_run_01",
                trace_id: "trace_01",
                chat_run_id: "cr_01",
                status: "completed",
                started_at: "2026-03-10T09:00:00Z",
              },
            ],
          });
        }

        if (url === "/api/ops/runs/pc_run_01/timeline") {
          return mockJsonResponse({
            ok: true,
            run_id: "pc_run_01",
            run: {
              run_id: "pc_run_01",
              trace_id: "trace_01",
              chat_run_id: "cr_01",
              status: "completed",
              summary: { pipeline_total_ms: 5400 },
            },
            timeline: [
              {
                stage: "intake",
                status: "ok",
                duration_ms: 1200,
                at: "2026-03-10T09:00:01Z",
                details: { risk_level: "medium" },
              },
            ],
            user_waterfall: {
              kind: "user",
              chat_run_id: "cr_01",
              total_ms: 4300,
              steps: [
                {
                  id: "main_chat_displayed",
                  label: "Main chat",
                  status: "ok",
                  duration_ms: 2100,
                  offset_ms: 0,
                  cumulative_ms: 2100,
                  absolute_elapsed_ms: 2100,
                  details: { source: "assistant_success" },
                },
                {
                  id: "normative_displayed",
                  label: "Normativa",
                  status: "ok",
                  duration_ms: 900,
                  offset_ms: 2100,
                  cumulative_ms: 3000,
                  absolute_elapsed_ms: 3000,
                  details: { source: "auto_detected", citations_count: 3 },
                },
                {
                  id: "expert_panel_displayed",
                  label: "Interpretación de expertos",
                  status: "populated",
                  duration_ms: 1300,
                  offset_ms: 3000,
                  cumulative_ms: 4300,
                  absolute_elapsed_ms: 4300,
                  details: { source: "expert_panel", panel_status: "populated" },
                },
              ],
            },
            technical_waterfall: {
              kind: "technical",
              total_ms: 5400,
              steps: [
                {
                  id: "technical_0",
                  label: "Intake",
                  status: "ok",
                  duration_ms: 1200,
                  offset_ms: 0,
                  cumulative_ms: 1200,
                  absolute_elapsed_ms: 1200,
                  details: {},
                },
                {
                  id: "technical_1",
                  label: "Compose",
                  status: "ok",
                  duration_ms: 3200,
                  offset_ms: 1200,
                  cumulative_ms: 4400,
                  absolute_elapsed_ms: 4400,
                  details: {},
                },
              ],
            },
          });
        }

        throw new Error(`Unexpected fetch: ${url}`);
      })
    );

    const root = document.getElementById("app");
    if (!root) {
      throw new Error("Missing app root.");
    }

    mountOpsApp(root, { i18n: createI18n("es-CO") });
    await flushUi();
    await flushUi();

    const runButton = document.querySelector<HTMLButtonElement>('button[data-run-id="pc_run_01"]');
    runButton?.click();
    await flushUi();
    await flushUi();

    expect(document.getElementById("user-cascade")?.textContent).toContain("Main chat");
    expect(document.getElementById("user-cascade")?.textContent).toContain("Normativa");
    expect(document.getElementById("user-cascade")?.textContent).toContain("Interpretación de expertos");
    expect(document.getElementById("user-cascade-summary")?.textContent).toContain("4,30 s");
    expect(document.getElementById("technical-cascade")?.textContent).toContain("Compose");
    expect(document.getElementById("technical-cascade-summary")?.textContent).toContain("5,40 s");
    expect(document.getElementById("timeline")?.textContent).toContain("intake");
  });

  it("renders recent runs inside the embedded Backstage shell", async () => {
    document.body.innerHTML = `
      <div id="tab-panel-backstage">${renderBackstageShell(createI18n("es-CO"))}</div>
      <div id="tab-panel-ingestion">${renderIngestionShell(createI18n("es-CO"))}</div>
    `;

    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);

        if (url.startsWith("/api/corpora")) {
          return mockJsonResponse({
            corpora: [{ key: "declaracion_renta", label: "Declaración de Renta", active: true }],
            default: "declaracion_renta",
          });
        }

        if (url.startsWith("/api/ingestion/sessions?")) {
          return mockJsonResponse({ sessions: [] });
        }

        if (url === "/api/ops/runs?limit=30") {
          return mockJsonResponse({
            runs: [
              {
                run_id: "pc_run_01",
                trace_id: "trace_01",
                chat_run_id: "cr_01",
                status: "completed",
                started_at: "2026-03-10T09:00:00Z",
              },
            ],
          });
        }

        throw new Error(`Unexpected fetch: ${url}`);
      })
    );

    mountOpsApp(document, { i18n: createI18n("es-CO") });
    await flushUi();
    await flushUi();

    expect(document.getElementById("runs-body")?.textContent).toContain("pc_run_01");
    expect(document.getElementById("cascade-note")?.textContent).toContain("hitos de usuario y técnicos");
  });

  it("populates corpora dropdown when only ingestion shell is rendered (browser-chrome mode)", async () => {
    document.body.innerHTML = `<div id="ingestion-panel">${renderIngestionShell(createI18n("es-CO"))}</div>`;

    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);

        if (url.startsWith("/api/corpora")) {
          return mockJsonResponse({
            corpora: [
              { key: "declaracion_renta", label: "Declaración de Renta", active: true },
              { key: "iva", label: "IVA", active: true },
            ],
            default: "declaracion_renta",
          });
        }

        if (url.startsWith("/api/ingestion/sessions?")) {
          return mockJsonResponse({ sessions: [] });
        }

        if (url.startsWith("/api/ops/runs")) {
          return mockJsonResponse({ runs: [] });
        }

        throw new Error(`Unexpected fetch: ${url}`);
      })
    );

    const root = document.getElementById("ingestion-panel");
    if (!root) throw new Error("Missing ingestion panel root.");

    mountOpsApp(root, { i18n: createI18n("es-CO") });
    await flushUi();
    await flushUi();

    const select = document.getElementById("ingestion-corpus") as HTMLSelectElement | null;
    expect(select).not.toBeNull();
    expect(select!.options.length).toBeGreaterThanOrEqual(3); // AUTODETECTAR + 2 corpora
    expect(select!.options[0].textContent).toBe("AUTOGENERAR");
    expect(select!.options[1].textContent).toBe("Declaración de Renta");
    expect(select!.options[2].textContent).toBe("IVA");
  });
});
