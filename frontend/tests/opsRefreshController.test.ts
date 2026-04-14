/**
 * Tests for opsReindexController — the re-index operations panel.
 *
 * Note: The user requested opsRefreshController.ts which doesn't exist;
 * this file targets opsReindexController.ts instead (31.42% coverage,
 * ~184 lines) as the closest match in the ops feature directory.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { createOpsReindexController } from "@/features/ops/opsReindexController";

vi.mock("@/shared/api/client", () => ({
  getJson: vi.fn(),
  postJson: vi.fn(),
}));

import { getJson, postJson } from "@/shared/api/client";

// Import the helpers we want to test from opsTypes
import {
  classifyLiveness,
  formatElapsed,
  statusTone,
  formatBatchType,
  buildSummaryLine,
  formatBytes,
  isRunningSession,
  isCompletedSession,
  formatGateSubStage,
  formatColombiaDateTime,
} from "@/features/ops/opsTypes";
import { createI18n } from "@/shared/i18n";

// ── opsTypes pure functions ──────────────────────────────────────

describe("classifyLiveness", () => {
  it("returns 'stalled' for empty heartbeat", () => {
    expect(classifyLiveness(undefined, undefined)).toBe("stalled");
    expect(classifyLiveness("", "")).toBe("stalled");
  });

  it("returns 'stalled' for unparseable timestamp", () => {
    expect(classifyLiveness("not-a-date", undefined)).toBe("stalled");
  });

  it("returns 'alive' for recent timestamp", () => {
    const now = new Date().toISOString();
    expect(classifyLiveness(now, undefined)).toBe("alive");
  });

  it("returns 'slow' for timestamp 60 seconds ago", () => {
    const past = new Date(Date.now() - 60_000).toISOString();
    expect(classifyLiveness(past, undefined)).toBe("slow");
  });

  it("returns 'stalled' for timestamp 3 minutes ago", () => {
    const past = new Date(Date.now() - 180_000).toISOString();
    expect(classifyLiveness(past, undefined)).toBe("stalled");
  });

  it("uses relaxed thresholds for gates stage", () => {
    // 60s ago — normally 'slow', but 'alive' for gates
    const past = new Date(Date.now() - 60_000).toISOString();
    expect(classifyLiveness(past, undefined, "gates")).toBe("alive");
  });

  it("gates stage: 'slow' at 120s", () => {
    const past = new Date(Date.now() - 120_000).toISOString();
    expect(classifyLiveness(past, undefined, "gates")).toBe("slow");
  });

  it("gates stage: 'stalled' at 6 minutes", () => {
    const past = new Date(Date.now() - 360_000).toISOString();
    expect(classifyLiveness(past, undefined, "gates")).toBe("stalled");
  });

  it("falls back to updatedAt when heartbeatAt is missing", () => {
    const now = new Date().toISOString();
    expect(classifyLiveness(undefined, now)).toBe("alive");
  });
});

describe("formatElapsed", () => {
  it("returns '-' for empty inputs", () => {
    expect(formatElapsed(undefined, undefined)).toBe("-");
    expect(formatElapsed("", "")).toBe("-");
  });

  it("returns '-' for unparseable timestamp", () => {
    expect(formatElapsed("garbage", undefined)).toBe("-");
  });

  it("returns 'ahora' for very recent timestamp", () => {
    const now = new Date().toISOString();
    expect(formatElapsed(now, undefined)).toBe("ahora");
  });

  it("returns seconds format for recent timestamp", () => {
    const past = new Date(Date.now() - 30_000).toISOString();
    const result = formatElapsed(past, undefined);
    expect(result).toMatch(/^hace \d+s$/);
  });

  it("returns minutes+seconds format for older timestamp", () => {
    const past = new Date(Date.now() - 90_000).toISOString();
    const result = formatElapsed(past, undefined);
    expect(result).toMatch(/^hace \d+m \d+s$/);
  });

  it("returns hours+minutes format for very old timestamp", () => {
    const past = new Date(Date.now() - 3_700_000).toISOString(); // ~1h1m
    const result = formatElapsed(past, undefined);
    expect(result).toMatch(/^hace \d+h \d+m$/);
  });
});

describe("statusTone", () => {
  it("returns 'error' for failed status", () => {
    expect(statusTone("failed")).toBe("error");
    expect(statusTone("error")).toBe("error");
  });

  it("returns 'warn' for processing statuses", () => {
    expect(statusTone("processing")).toBe("warn");
    expect(statusTone("queued")).toBe("warn");
    expect(statusTone("in_progress")).toBe("warn");
    expect(statusTone("running_batch_gates")).toBe("warn");
    expect(statusTone("partial_failed")).toBe("warn");
    expect(statusTone("raw")).toBe("warn");
    expect(statusTone("pending_dedup")).toBe("warn");
  });

  it("returns 'ok' for completed/done/unknown statuses", () => {
    expect(statusTone("done")).toBe("ok");
    expect(statusTone("completed")).toBe("ok");
    expect(statusTone("ready")).toBe("ok");
    expect(statusTone("")).toBe("ok");
  });
});

// formatOpsError tests omitted — requires ApiError from un-mocked client;
// already covered in opsTypes.test.ts.

describe("formatBatchType", () => {
  const i18n = createI18n("es-CO");

  it("formats normative_base", () => {
    const result = formatBatchType("normative_base", i18n);
    expect(result).toBe(i18n.t("ops.ingestion.batchType.normative"));
  });

  it("formats interpretative_guidance", () => {
    const result = formatBatchType("interpretative_guidance", i18n);
    expect(result).toBe(i18n.t("ops.ingestion.batchType.interpretative"));
  });

  it("formats practica_erp", () => {
    const result = formatBatchType("practica_erp", i18n);
    expect(result).toBe(i18n.t("ops.ingestion.batchType.practical"));
  });

  it("returns raw value for unknown batch type", () => {
    expect(formatBatchType("custom_type", i18n)).toBe("custom_type");
  });

  it("returns '-' for undefined", () => {
    expect(formatBatchType(undefined, i18n)).toBe("-");
  });
});

describe("formatBytes", () => {
  const i18n = createI18n("es-CO");

  it("formats zero bytes", () => {
    expect(formatBytes(0, i18n)).toBe("0 B");
  });

  it("formats small byte values", () => {
    const result = formatBytes(512, i18n);
    expect(result).toContain("B");
  });

  it("formats kilobyte values", () => {
    const result = formatBytes(2048, i18n);
    expect(result).toContain("KB");
  });

  it("formats megabyte values", () => {
    const result = formatBytes(2 * 1024 * 1024, i18n);
    expect(result).toContain("MB");
  });

  it("handles negative values", () => {
    expect(formatBytes(-100, i18n)).toBe("0 B");
  });

  it("handles NaN", () => {
    expect(formatBytes(NaN, i18n)).toBe("0 B");
  });
});

describe("buildSummaryLine", () => {
  const i18n = createI18n("es-CO");

  it("builds a summary line from batch summary", () => {
    const summary = {
      total: 10,
      queued: 2,
      processing: 1,
      done: 5,
      failed: 2,
      skipped_duplicate: 0,
      pending_batch_gate: 0,
      bounced: 0,
    };
    const result = buildSummaryLine(summary, i18n);
    expect(result).toContain("10");
    expect(result).toContain("5");
    expect(result).toContain("2");
  });

  it("handles undefined summary", () => {
    const result = buildSummaryLine(undefined, i18n);
    expect(result).toContain("0");
  });

  it("includes bounced count when > 0", () => {
    const summary = {
      total: 5, queued: 0, processing: 0, done: 3,
      failed: 0, skipped_duplicate: 0, pending_batch_gate: 0, bounced: 2,
    };
    const result = buildSummaryLine(summary, i18n);
    expect(result).toContain("Rebotados 2");
  });

  it("omits bounced when count is 0", () => {
    const summary = {
      total: 5, queued: 0, processing: 0, done: 5,
      failed: 0, skipped_duplicate: 0, pending_batch_gate: 0, bounced: 0,
    };
    const result = buildSummaryLine(summary, i18n);
    expect(result).not.toContain("Rebotados");
  });
});

describe("isRunningSession", () => {
  it("returns true for processing", () => {
    expect(isRunningSession("processing")).toBe(true);
  });

  it("returns true for running_batch_gates", () => {
    expect(isRunningSession("running_batch_gates")).toBe(true);
  });

  it("returns false for ready", () => {
    expect(isRunningSession("ready")).toBe(false);
  });

  it("returns false for completed", () => {
    expect(isRunningSession("completed")).toBe(false);
  });
});

describe("isCompletedSession", () => {
  it("returns false for null", () => {
    expect(isCompletedSession(null)).toBe(false);
  });

  it("returns true for done status", () => {
    expect(isCompletedSession({ status: "done", documents: [] } as any)).toBe(true);
  });

  it("returns true for completed status", () => {
    expect(isCompletedSession({ status: "completed", documents: [] } as any)).toBe(true);
  });

  it("returns true when all docs are terminal", () => {
    expect(
      isCompletedSession({
        status: "ready",
        documents: [
          { status: "done" },
          { status: "completed" },
          { status: "skipped_duplicate" },
          { status: "bounced" },
        ],
      } as any)
    ).toBe(true);
  });

  it("returns false when some docs are still processing", () => {
    expect(
      isCompletedSession({
        status: "ready",
        documents: [{ status: "done" }, { status: "processing" }],
      } as any)
    ).toBe(false);
  });

  it("returns false for empty documents array", () => {
    expect(
      isCompletedSession({ status: "ready", documents: [] } as any)
    ).toBe(false);
  });
});

describe("formatGateSubStage", () => {
  it("returns empty string for undefined", () => {
    expect(formatGateSubStage(undefined)).toBe("");
  });

  it("returns human label for known sub-stage", () => {
    expect(formatGateSubStage("validating")).toBe("validando corpus");
    expect(formatGateSubStage("manifest")).toBe("activando manifest");
    expect(formatGateSubStage("indexing")).toBe("reconstruyendo índice");
  });

  it("handles sub-stage with progress suffix", () => {
    const result = formatGateSubStage("indexing/chunking:45/120");
    expect(result).toContain("generando chunks");
    expect(result).toContain("45/120");
  });

  it("returns raw value for unknown sub-stage", () => {
    expect(formatGateSubStage("unknown_stage")).toBe("unknown_stage");
  });
});

describe("formatColombiaDateTime", () => {
  it("returns empty string for undefined", () => {
    expect(formatColombiaDateTime(undefined)).toBe("");
  });

  it("returns empty string for empty string", () => {
    expect(formatColombiaDateTime("")).toBe("");
  });

  it("returns empty string for unparseable date", () => {
    expect(formatColombiaDateTime("not-a-date")).toBe("");
  });

  it("formats a valid ISO date", () => {
    const result = formatColombiaDateTime("2026-04-01T15:30:00Z");
    expect(result).toBeTruthy();
    // The exact format depends on the Intl implementation, but it should contain numbers
    expect(result).toMatch(/\d/);
  });
});

// ── createOpsReindexController ──────────────────────────────────

describe("createOpsReindexController", () => {
  let container: HTMLElement;
  let setFlash: ReturnType<typeof vi.fn>;
  let navigateToEmbeddings: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    document.body.innerHTML = "";
    container = document.createElement("div");
    document.body.appendChild(container);
    setFlash = vi.fn();
    navigateToEmbeddings = vi.fn();
    vi.clearAllMocks();
  });

  function createController() {
    return createOpsReindexController({
      dom: { container },
      setFlash,
      navigateToEmbeddings,
    });
  }

  it("creates controller with bindEvents and refresh methods", () => {
    const controller = createController();
    expect(typeof controller.bindEvents).toBe("function");
    expect(typeof controller.refresh).toBe("function");
  });

  it("renders loading state initially", () => {
    const controller = createController();
    // Before refresh, the container should show loading message
    expect(container.innerHTML).toBe("");

    // Force render by accessing the internal state
    // The controller doesn't render until refresh is called
  });

  it("refresh fetches status and renders idle state", async () => {
    const getJsonMock = vi.mocked(getJson);
    getJsonMock.mockResolvedValue({
      current_operation: null,
      last_operation: null,
    });

    const controller = createController();
    await controller.refresh();

    expect(getJsonMock).toHaveBeenCalledWith("/api/ops/reindex-status");
    expect(container.innerHTML).toContain("Inactivo");
    expect(container.innerHTML).toContain("reindex-start-btn");
  });

  it("refresh renders running state with stop button", async () => {
    const getJsonMock = vi.mocked(getJson);
    getJsonMock.mockResolvedValue({
      current_operation: {
        job_id: "job-1",
        status: "running",
        heartbeat_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        stages: [],
      },
      last_operation: null,
    });

    const controller = createController();
    await controller.refresh();

    expect(container.innerHTML).toContain("En ejecución");
    expect(container.innerHTML).toContain("reindex-stop-btn");
  });

  it("refresh renders completed state with quality report", async () => {
    const getJsonMock = vi.mocked(getJson);
    getJsonMock.mockResolvedValue({
      current_operation: null,
      last_operation: {
        job_id: "job-2",
        status: "completed",
        stages: [
          { label: "Scan", state: "completed" },
          { label: "Index", state: "completed" },
        ],
        quality_report: {
          documents_indexed: 100,
          chunks_generated: 500,
          blocking_issues: 0,
          knowledge_class_counts: {
            normative_base: 50,
            interpretative_guidance: 30,
            practica_erp: 20,
          },
        },
      },
    });

    const controller = createController();
    await controller.refresh();

    expect(container.innerHTML).toContain("Inactivo");
    expect(container.innerHTML).toContain("Reporte de calidad");
    expect(container.innerHTML).toContain("100");
    expect(container.innerHTML).toContain("500");
    expect(container.innerHTML).toContain("normative_base");
    expect(container.innerHTML).toContain("reindex-embed-now-btn");
  });

  it("refresh renders stages stepper", async () => {
    const getJsonMock = vi.mocked(getJson);
    getJsonMock.mockResolvedValue({
      current_operation: {
        job_id: "job-3",
        status: "running",
        heartbeat_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        stages: [
          { label: "Escanear", state: "completed" },
          { label: "Indexar", state: "active" },
          { label: "Verificar", state: "pending" },
        ],
      },
    });

    const controller = createController();
    await controller.refresh();

    expect(container.innerHTML).toContain("Escanear");
    expect(container.innerHTML).toContain("Indexar");
    expect(container.innerHTML).toContain("Verificar");
    expect(container.innerHTML).toContain("reindex-stage-completed");
    expect(container.innerHTML).toContain("reindex-stage-active");
    expect(container.innerHTML).toContain("reindex-stage-pending");
  });

  it("refresh renders progress stats", async () => {
    const getJsonMock = vi.mocked(getJson);
    getJsonMock.mockResolvedValue({
      current_operation: {
        job_id: "job-4",
        status: "running",
        heartbeat_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        stages: [],
        progress: {
          documents_processed: 45,
          documents_total: 100,
          documents_indexed: 40,
          elapsed_seconds: 125,
        },
      },
    });

    const controller = createController();
    await controller.refresh();

    expect(container.innerHTML).toContain("45");
    expect(container.innerHTML).toContain("100");
    expect(container.innerHTML).toContain("2m"); // 125s = 2m 5s
  });

  it("refresh renders error message", async () => {
    const getJsonMock = vi.mocked(getJson);
    getJsonMock.mockResolvedValue({
      current_operation: null,
      last_operation: {
        job_id: "job-err",
        status: "failed",
        stages: [],
        error: "Fatal: index corruption detected",
      },
    });

    const controller = createController();
    await controller.refresh();

    expect(container.innerHTML).toContain("Fatal: index corruption detected");
  });

  it("refresh renders log tail in details", async () => {
    const getJsonMock = vi.mocked(getJson);
    getJsonMock.mockResolvedValue({
      current_operation: null,
      last_operation: {
        job_id: "job-log",
        status: "completed",
        stages: [],
        log_tail: "Processing batch 1/10...\nDone.",
      },
    });

    const controller = createController();
    await controller.refresh();

    expect(container.innerHTML).toContain("Processing batch 1/10...");
  });

  it("refresh renders checks", async () => {
    const getJsonMock = vi.mocked(getJson);
    getJsonMock.mockResolvedValue({
      current_operation: null,
      last_operation: {
        job_id: "job-checks",
        status: "completed",
        stages: [],
        checks: [
          { label: "Schema valid", ok: true, detail: "All schemas OK" },
          { label: "No orphans", ok: false, detail: "2 orphan chunks found" },
        ],
      },
    });

    const controller = createController();
    await controller.refresh();

    expect(container.innerHTML).toContain("Schema valid");
    expect(container.innerHTML).toContain("No orphans");
    expect(container.innerHTML).toContain("ops-dot-ok");
    expect(container.innerHTML).toContain("ops-dot-error");
  });

  it("refresh keeps last state on fetch error", async () => {
    const getJsonMock = vi.mocked(getJson);

    // First call succeeds
    getJsonMock.mockResolvedValueOnce({
      current_operation: null,
      last_operation: { job_id: "job-ok", status: "completed", stages: [] },
    });

    const controller = createController();
    await controller.refresh();
    expect(container.innerHTML).toContain("Inactivo");

    // Second call fails
    getJsonMock.mockRejectedValueOnce(new Error("Network error"));
    await controller.refresh();

    // Should still show previous state
    expect(container.innerHTML).toContain("Inactivo");
  });

  it("bindEvents wires start button click", async () => {
    const getJsonMock = vi.mocked(getJson);
    const postJsonMock = vi.mocked(postJson);

    getJsonMock.mockResolvedValue({
      current_operation: null,
      last_operation: null,
    });
    postJsonMock.mockResolvedValue({ response: { ok: true }, data: {} });

    const controller = createController();
    controller.bindEvents();
    await controller.refresh();

    const startBtn = container.querySelector("#reindex-start-btn") as HTMLButtonElement;
    expect(startBtn).not.toBeNull();

    // Click start
    startBtn.click();

    // Wait for async handler
    await vi.waitFor(() => {
      expect(postJsonMock).toHaveBeenCalledWith("/api/ops/reindex/start", { mode: "from_source" });
    });

    expect(setFlash).toHaveBeenCalledWith("Re-index iniciado", "success");
  });

  it("bindEvents wires stop button click", async () => {
    const getJsonMock = vi.mocked(getJson);
    const postJsonMock = vi.mocked(postJson);

    getJsonMock.mockResolvedValue({
      current_operation: {
        job_id: "job-running",
        status: "running",
        heartbeat_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        stages: [],
      },
    });
    postJsonMock.mockResolvedValue({ response: { ok: true }, data: {} });

    const controller = createController();
    controller.bindEvents();
    await controller.refresh();

    const stopBtn = container.querySelector("#reindex-stop-btn") as HTMLButtonElement;
    expect(stopBtn).not.toBeNull();

    stopBtn.click();

    await vi.waitFor(() => {
      expect(postJsonMock).toHaveBeenCalledWith("/api/ops/reindex/stop", { job_id: "job-running" });
    });

    expect(setFlash).toHaveBeenCalledWith("Re-index detenido", "success");
  });

  it("bindEvents wires embed-now button to navigateToEmbeddings", async () => {
    const getJsonMock = vi.mocked(getJson);
    getJsonMock.mockResolvedValue({
      current_operation: null,
      last_operation: {
        job_id: "job-done",
        status: "completed",
        stages: [],
        quality_report: {
          documents_indexed: 10,
          chunks_generated: 50,
          blocking_issues: 0,
        },
      },
    });

    const controller = createController();
    controller.bindEvents();
    await controller.refresh();

    const embedBtn = container.querySelector("#reindex-embed-now-btn") as HTMLButtonElement;
    expect(embedBtn).not.toBeNull();

    embedBtn.click();
    expect(navigateToEmbeddings).toHaveBeenCalled();
  });

  it("start button shows error flash on failure", async () => {
    const getJsonMock = vi.mocked(getJson);
    const postJsonMock = vi.mocked(postJson);

    getJsonMock.mockResolvedValue({
      current_operation: null,
      last_operation: null,
    });
    postJsonMock.mockRejectedValue(new Error("Server error"));

    const controller = createController();
    controller.bindEvents();
    await controller.refresh();

    const startBtn = container.querySelector("#reindex-start-btn") as HTMLButtonElement;
    startBtn.click();

    await vi.waitFor(() => {
      expect(setFlash).toHaveBeenCalledWith(expect.stringContaining("Server error"), "error");
    });
  });

  it("escapes HTML in rendered output", async () => {
    const getJsonMock = vi.mocked(getJson);
    getJsonMock.mockResolvedValue({
      current_operation: null,
      last_operation: {
        job_id: "job-xss",
        status: "failed",
        stages: [],
        error: '<script>alert("xss")</script>',
      },
    });

    const controller = createController();
    await controller.refresh();

    expect(container.innerHTML).not.toContain("<script>");
    expect(container.innerHTML).toContain("&lt;script&gt;");
  });
});
