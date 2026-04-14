import { beforeEach, describe, expect, it, vi } from "vitest";
import { createCorpusLifecycleController } from "@/features/ops/opsCorpusLifecycleController";

function mockJsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

async function flushUi(): Promise<void> {
  await Promise.resolve();
  await new Promise((resolve) => window.setTimeout(resolve, 0));
  await Promise.resolve();
}

describe("ops corpus lifecycle controller", () => {
  beforeEach(() => {
    document.body.innerHTML = `<div id="root"></div>`;
    vi.restoreAllMocks();
    vi.spyOn(window, "setInterval").mockImplementation(
      ((..._args: Parameters<typeof window.setInterval>) => 1 as ReturnType<typeof window.setInterval>) as typeof window.setInterval,
    );
    vi.spyOn(window, "clearInterval").mockImplementation(
      ((_id: ReturnType<typeof window.setInterval>) => {}) as typeof window.clearInterval,
    );
  });

  it("renders backend running state with transparent phase and checkpoint details", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url === "/api/ops/corpus-status") {
          return mockJsonResponse({
            production: { available: true, generation_id: "prod_01", documents: 10, chunks: 20, embeddings_complete: true },
            wip: { available: true, generation_id: "wip_01", documents: 12, chunks: 26, embeddings_complete: true },
            delta: { documents: "+2", chunks: "+6", promotable: true },
            preflight_ready: true,
            preflight_reasons: [],
            rollback_available: false,
            rollback_reason: "Rollback is not available yet.",
            current_operation: {
              job_id: "job_running",
              job_type: "corpus_rebuild_from_wip",
              kind: "rebuild",
              mode: "promote",
              status: "running",
              severity: "yellow",
              operation_state_code: "running",
              stage: "promote_from_wip",
              stage_label: "Promote from WIP",
              current_phase: "chunks_upsert",
              heartbeat_at: new Date(Date.now() - 4_000).toISOString(),
              source_generation_id: "wip_01",
              target_generation_id: "prod_next",
              last_checkpoint: {
                phase: "chunks_upsert",
                cursor: 50,
                total: 200,
                at: new Date(Date.now() - 6_000).toISOString(),
              },
              stages: [
                { id: "preflight", label: "Preflight", state: "completed" },
                { id: "promote_from_wip", label: "Promote from WIP", state: "active" },
              ],
              checks: [{ id: "plan", label: "Promotion plan", ok: true, detail: "200 chunks queued." }],
              failures: [],
            },
            last_operation: null,
          });
        }
        throw new Error(`Unexpected fetch: ${url}`);
      }),
    );

    const flashes: string[] = [];
    const controller = createCorpusLifecycleController({
      dom: { container: document.getElementById("root") as HTMLElement },
      setFlash: (message) => {
        if (message) flashes.push(message);
      },
    });

    controller.bindEvents();
    await controller.refresh();
    await flushUi();

    const root = document.getElementById("root") as HTMLElement;
    expect(root.textContent).toContain("Running");
    expect(root.textContent).toContain("Promote WIP to Production");
    expect(root.textContent).toContain("chunks upsert");
    expect(root.textContent).toContain("50 / 200");
    expect(root.textContent).toContain("Promotion plan");
    expect((root.querySelector("#corpus-promote-btn") as HTMLButtonElement).disabled).toBe(true);
    expect((root.querySelector("#corpus-rollback-btn") as HTMLButtonElement).disabled).toBe(true);
    expect(flashes).toEqual([]);
  });

  it("shows an orphaned queued job as orphaned before start", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url === "/api/ops/corpus-status") {
          return mockJsonResponse({
            production: { available: true, generation_id: "prod_01", documents: 10, chunks: 20, embeddings_complete: true },
            wip: { available: true, generation_id: "wip_01", documents: 12, chunks: 26, embeddings_complete: true },
            delta: { documents: "+2", chunks: "+6", promotable: true },
            preflight_ready: true,
            preflight_reasons: [],
            rollback_available: false,
            rollback_reason: "Rollback is not available yet.",
            current_operation: null,
            last_operation: {
              job_id: "job_orphaned",
              job_type: "corpus_rebuild_from_wip",
              kind: "rebuild",
              mode: "promote",
              status: "queued",
              severity: "red",
              operation_state_code: "orphaned_queue",
              heartbeat_at: new Date(Date.now() - 45_000).toISOString(),
              checks: [],
              failures: [],
            },
          });
        }
        throw new Error(`Unexpected fetch: ${url}`);
      }),
    );

    const controller = createCorpusLifecycleController({
      dom: { container: document.getElementById("root") as HTMLElement },
      setFlash: () => {},
    });

    controller.bindEvents();
    await controller.refresh();
    await flushUi();

    const root = document.getElementById("root") as HTMLElement;
    expect(root.textContent).toContain("Orphaned before start");
    expect(root.textContent).not.toContain("Heartbeat perdido");
    expect(root.querySelector("#corpus-resume-btn")).toBeNull();
  });

  it("copies the backend log tail", async () => {
    const clipboardWrite = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(window.navigator, "clipboard", {
      configurable: true,
      value: { writeText: clipboardWrite },
    });

    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url === "/api/ops/corpus-status") {
          return mockJsonResponse({
            production: { available: true, generation_id: "prod_01", documents: 10, chunks: 20, embeddings_complete: true },
            wip: { available: true, generation_id: "wip_01", documents: 12, chunks: 26, embeddings_complete: true },
            delta: { documents: "+2", chunks: "+6", promotable: true },
            preflight_ready: true,
            preflight_reasons: [],
            rollback_available: false,
            rollback_reason: "Rollback is not available yet.",
            current_operation: {
              job_id: "job_running",
              job_type: "corpus_rebuild_from_wip",
              kind: "rebuild",
              mode: "promote",
              status: "running",
              severity: "yellow",
              operation_state_code: "running",
              stage: "promote_from_wip",
              stage_label: "Promote from WIP",
              current_phase: "chunks_upsert",
              heartbeat_at: new Date().toISOString(),
              source_generation_id: "wip_01",
              target_generation_id: "prod_next",
              log_tail: "line 1\nline 2",
              stages: [{ id: "promote_from_wip", label: "Promote from WIP", state: "active" }],
              checks: [],
              failures: [],
            },
            last_operation: null,
          });
        }
        throw new Error(`Unexpected fetch: ${url}`);
      }),
    );

    const flashes: string[] = [];
    const controller = createCorpusLifecycleController({
      dom: { container: document.getElementById("root") as HTMLElement },
      setFlash: (message) => {
        if (message) flashes.push(message);
      },
    });

    controller.bindEvents();
    await controller.refresh();
    await flushUi();

    const copyBtn = document.querySelector<HTMLButtonElement>("#corpus-copy-log-tail-btn");
    expect(copyBtn).not.toBeNull();
    copyBtn?.click();
    await flushUi();

    expect(clipboardWrite).toHaveBeenCalledWith("line 1\nline 2");
    expect(flashes.some((message) => message.includes("Log tail copied."))).toBe(true);
  });

  it("shows resume after a stalled promote and posts the resume endpoint", async () => {
    let statusCall = 0;
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/ops/corpus-status") {
        statusCall += 1;
        if (statusCall === 1) {
          return mockJsonResponse({
            production: { available: true, generation_id: "prod_failed", documents: 5, chunks: 10, embeddings_complete: true },
            wip: { available: true, generation_id: "wip_01", documents: 12, chunks: 26, embeddings_complete: true },
            delta: { documents: "+7", chunks: "+16", promotable: true },
            preflight_ready: true,
            preflight_reasons: [],
            rollback_available: false,
            rollback_reason: "Rollback is not available yet.",
            current_operation: null,
            last_operation: {
              job_id: "job_failed",
              job_type: "corpus_rebuild_from_wip",
              kind: "rebuild",
              mode: "promote",
              status: "failed",
              severity: "red",
              operation_state_code: "failed_resumable",
              stage: "promote_from_wip",
              stage_label: "Promote from WIP",
              current_phase: "chunks_upsert",
              heartbeat_at: new Date(Date.now() - 20_000).toISOString(),
              source_generation_id: "wip_01",
              target_generation_id: "prod_next",
              resume_supported: true,
              resume_job_id: "job_failed",
              last_checkpoint: {
                phase: "chunks_upsert",
                cursor: 40,
                total: 100,
                at: new Date(Date.now() - 25_000).toISOString(),
              },
              failures: [{ message: "chunk timeout", stage: "promote_from_wip" }],
              checks: [{ id: "plan", label: "Promotion plan", ok: true, detail: "checkpoint persisted", phase: "promote_from_wip" }],
              stages: [
                { id: "preflight", label: "Preflight", state: "completed" },
                { id: "promote_from_wip", label: "Promote from WIP", state: "failed" },
              ],
            },
          });
        }
        return mockJsonResponse({
          production: { available: true, generation_id: "prod_failed", documents: 5, chunks: 10, embeddings_complete: true },
          wip: { available: true, generation_id: "wip_01", documents: 12, chunks: 26, embeddings_complete: true },
          delta: { documents: "+7", chunks: "+16", promotable: true },
          preflight_ready: true,
          preflight_reasons: [],
          rollback_available: false,
          rollback_reason: "Rollback is not available yet.",
          current_operation: {
            job_id: "job_failed",
            job_type: "corpus_rebuild_from_wip",
            kind: "rebuild",
            mode: "promote",
            status: "running",
            severity: "yellow",
            operation_state_code: "running",
            stage: "promote_from_wip",
            stage_label: "Promote from WIP",
            current_phase: "chunks_upsert",
            heartbeat_at: new Date().toISOString(),
            source_generation_id: "wip_01",
            target_generation_id: "prod_next",
            stages: [{ id: "promote_from_wip", label: "Promote from WIP", state: "active" }],
            checks: [],
            failures: [],
          },
          last_operation: null,
        });
      }
      if (url === "/api/ops/corpus/rebuild-from-wip/resume" && init?.method === "POST") {
        return mockJsonResponse({ ok: true, job_id: "job_failed", status: "failed" }, 202);
      }
      throw new Error(`Unexpected fetch: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    const flashes: string[] = [];
    const controller = createCorpusLifecycleController({
      dom: { container: document.getElementById("root") as HTMLElement },
      setFlash: (message) => {
        if (message) flashes.push(message);
      },
    });

    controller.bindEvents();
    await controller.refresh();
    await flushUi();

    const root = document.getElementById("root") as HTMLElement;
    const resumeBtn = root.querySelector("#corpus-resume-btn") as HTMLButtonElement | null;
    expect(resumeBtn).not.toBeNull();
    resumeBtn?.click();
    await flushUi();

    const confirmBtn = document.querySelector<HTMLButtonElement>('.corpus-confirm-overlay [data-action="confirm"]');
    confirmBtn?.click();
    await flushUi();
    await flushUi();

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/ops/corpus/rebuild-from-wip/resume",
      expect.objectContaining({ method: "POST" }),
    );
    expect(flashes.some((message) => message.includes("Resume started."))).toBe(true);
    expect(root.textContent).toContain("Running");
  });

  it("keeps the confirm dialog open across refresh re-renders", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/ops/corpus-status") {
        return mockJsonResponse({
          production: { available: true, generation_id: "prod_01", documents: 10, chunks: 20, embeddings_complete: true },
          wip: { available: true, generation_id: "wip_01", documents: 12, chunks: 26, embeddings_complete: true },
          delta: { documents: "+2", chunks: "+6", promotable: true },
          preflight_ready: true,
          preflight_reasons: [],
          rollback_available: false,
          rollback_reason: "Rollback is not available yet.",
          current_operation: null,
          last_operation: null,
        });
      }
      if (url === "/api/ops/corpus/rebuild-from-wip" && init?.method === "POST") {
        return mockJsonResponse({ ok: true, job_id: "job_promote_1", status: "queued" }, 202);
      }
      throw new Error(`Unexpected fetch: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    const flashes: string[] = [];
    const controller = createCorpusLifecycleController({
      dom: { container: document.getElementById("root") as HTMLElement },
      setFlash: (message) => {
        if (message) flashes.push(message);
      },
    });

    controller.bindEvents();
    await controller.refresh();
    await flushUi();

    const root = document.getElementById("root") as HTMLElement;
    (root.querySelector("#corpus-promote-btn") as HTMLButtonElement).click();
    await flushUi();

    expect(document.querySelector(".corpus-confirm-overlay")).not.toBeNull();

    await controller.refresh();
    await flushUi();

    const confirmBtn = document.querySelector<HTMLButtonElement>('.corpus-confirm-overlay [data-action="confirm"]');
    expect(confirmBtn).not.toBeNull();
    confirmBtn?.click();
    await flushUi();
    await flushUi();

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/ops/corpus/rebuild-from-wip",
      expect.objectContaining({ method: "POST" }),
    );
    expect(flashes.some((message) => message.includes("Promotion started."))).toBe(true);
  });

  it("keeps promote launch failures visible inline instead of failing silently", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/ops/corpus-status") {
        return mockJsonResponse({
          production: { available: true, generation_id: "prod_01", documents: 10, chunks: 20, embeddings_complete: true },
          wip: { available: true, generation_id: "wip_01", documents: 12, chunks: 26, embeddings_complete: true },
          delta: { documents: "+2", chunks: "+6", promotable: true },
          preflight_ready: true,
          preflight_reasons: [],
          rollback_available: false,
          rollback_reason: "Rollback is not available yet.",
          current_operation: null,
          last_operation: null,
        });
      }
      if (url === "/api/ops/corpus/rebuild-from-wip" && init?.method === "POST") {
        return mockJsonResponse({ status: "failed", error: "tenant_id missing" }, 500);
      }
      throw new Error(`Unexpected fetch: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    const controller = createCorpusLifecycleController({
      dom: { container: document.getElementById("root") as HTMLElement },
      setFlash: () => {},
    });

    controller.bindEvents();
    await controller.refresh();
    await flushUi();

    const root = document.getElementById("root") as HTMLElement;
    (root.querySelector("#corpus-promote-btn") as HTMLButtonElement).click();
    await flushUi();

    const confirmBtn = document.querySelector<HTMLButtonElement>('.corpus-confirm-overlay [data-action="confirm"]');
    confirmBtn?.click();
    await flushUi();
    await flushUi();

    expect(root.textContent).toContain("Request failed");
    expect(root.textContent).toContain("tenant_id missing");
    expect(root.textContent).toContain("Ready");
  });
});
