import { beforeEach, describe, expect, it, vi } from "vitest";

// Mock storage for readStoredTab/storeActiveTab
const mockStore = new Map<string, string>();
vi.mock("@/shared/browser/storage", () => ({
  getLocalStorage: () => ({
    getItem: (k: string) => mockStore.get(k) ?? null,
    setItem: (k: string, v: string) => mockStore.set(k, v),
    removeItem: (k: string) => mockStore.delete(k),
    clear: () => mockStore.clear(),
  }),
  getSessionStorage: () => ({
    getItem: () => null,
    setItem: () => {},
    removeItem: () => {},
    clear: () => {},
  }),
  readStorageValue: (_s: unknown, k: string) => mockStore.get(k) ?? null,
}));

import {
  classifyLiveness,
  formatColombiaDateTime,
  formatElapsed,
  formatGateSubStage,
  isCompletedSession,
  isRunningSession,
  readStoredTab,
  statusTone,
  storeActiveTab,
} from "@/features/ops/opsTypes";

// ---------------------------------------------------------------------------
// statusTone
// ---------------------------------------------------------------------------
describe("statusTone", () => {
  it("returns 'error' for failed/error", () => {
    expect(statusTone("failed")).toBe("error");
    expect(statusTone("error")).toBe("error");
    expect(statusTone("FAILED")).toBe("error");
  });

  it("returns 'warn' for in-progress states", () => {
    expect(statusTone("processing")).toBe("warn");
    expect(statusTone("running_batch_gates")).toBe("warn");
    expect(statusTone("queued")).toBe("warn");
    expect(statusTone("extracting")).toBe("warn");
    expect(statusTone("in_progress")).toBe("warn");
    expect(statusTone("partial_failed")).toBe("warn");
  });

  it("returns 'ok' for done/completed/unknown", () => {
    expect(statusTone("done")).toBe("ok");
    expect(statusTone("completed")).toBe("ok");
    expect(statusTone("promoted")).toBe("ok");
    expect(statusTone("")).toBe("ok");
  });
});

// ---------------------------------------------------------------------------
// isRunningSession
// ---------------------------------------------------------------------------
describe("isRunningSession", () => {
  it("returns true for running states", () => {
    expect(isRunningSession("processing")).toBe(true);
    expect(isRunningSession("running_batch_gates")).toBe(true);
  });

  it("returns false for other states", () => {
    expect(isRunningSession("done")).toBe(false);
    expect(isRunningSession("failed")).toBe(false);
    expect(isRunningSession("")).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// isCompletedSession
// ---------------------------------------------------------------------------
describe("isCompletedSession", () => {
  it("returns true for done/completed status", () => {
    expect(isCompletedSession({ status: "done", documents: [] } as any)).toBe(true);
    expect(isCompletedSession({ status: "completed", documents: [] } as any)).toBe(true);
  });

  it("returns true when all docs are terminal", () => {
    expect(
      isCompletedSession({
        status: "processing",
        documents: [{ status: "done" }, { status: "skipped_duplicate" }, { status: "bounced" }],
      } as any),
    ).toBe(true);
  });

  it("returns false when some docs not done", () => {
    expect(
      isCompletedSession({
        status: "processing",
        documents: [{ status: "done" }, { status: "processing" }],
      } as any),
    ).toBe(false);
  });

  it("returns false for null/undefined", () => {
    expect(isCompletedSession(null)).toBe(false);
    expect(isCompletedSession(undefined)).toBe(false);
  });

  it("returns false for empty documents with non-complete status", () => {
    expect(isCompletedSession({ status: "processing", documents: [] } as any)).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// readStoredTab / storeActiveTab
// ---------------------------------------------------------------------------
describe("readStoredTab / storeActiveTab", () => {
  beforeEach(() => mockStore.clear());

  it("defaults to 'monitor'", () => {
    expect(readStoredTab()).toBe("monitor");
  });

  it("round-trips a valid tab", () => {
    storeActiveTab("ingestion");
    expect(readStoredTab()).toBe("ingestion");
  });

  it("ignores invalid stored values", () => {
    mockStore.set("lia_backstage_ops_active_tab", "garbage");
    expect(readStoredTab()).toBe("monitor");
  });
});

// ---------------------------------------------------------------------------
// formatGateSubStage
// ---------------------------------------------------------------------------
describe("formatGateSubStage", () => {
  it("returns label for known stages", () => {
    expect(formatGateSubStage("validating")).toBe("validando corpus");
    expect(formatGateSubStage("indexing")).toBe("reconstruyendo índice");
    expect(formatGateSubStage("indexing/chunking")).toBe("generando chunks");
  });

  it("handles progress suffix", () => {
    const result = formatGateSubStage("indexing/chunking:45/120");
    expect(result).toBe("generando chunks (45/120)");
  });

  it("returns raw for unknown", () => {
    expect(formatGateSubStage("something_else")).toBe("something_else");
  });

  it("returns empty for undefined", () => {
    expect(formatGateSubStage(undefined)).toBe("");
  });
});

// ---------------------------------------------------------------------------
// formatColombiaDateTime
// ---------------------------------------------------------------------------
describe("formatColombiaDateTime", () => {
  it("formats a valid ISO string", () => {
    const result = formatColombiaDateTime("2026-04-06T12:00:00Z");
    // Colombia is UTC-5, so 12:00 UTC → 07:00 local
    expect(result).toContain("07");
    expect(result).toContain("06");
  });

  it("returns empty for undefined", () => {
    expect(formatColombiaDateTime(undefined)).toBe("");
  });

  it("returns empty for invalid date", () => {
    expect(formatColombiaDateTime("not-a-date")).toBe("");
  });
});

// ---------------------------------------------------------------------------
// formatElapsed
// ---------------------------------------------------------------------------
describe("formatElapsed", () => {
  it("returns 'ahora' for recent timestamps", () => {
    const recent = new Date(Date.now() - 2000).toISOString();
    expect(formatElapsed(recent, undefined)).toBe("ahora");
  });

  it("returns seconds for < 60s", () => {
    const ts = new Date(Date.now() - 30_000).toISOString();
    const result = formatElapsed(ts, undefined);
    expect(result).toMatch(/^hace \d+s$/);
  });

  it("returns minutes for < 60m", () => {
    const ts = new Date(Date.now() - 150_000).toISOString(); // 2.5m
    const result = formatElapsed(ts, undefined);
    expect(result).toMatch(/^hace \d+m \d+s$/);
  });

  it("returns hours for >= 60m", () => {
    const ts = new Date(Date.now() - 7_200_000).toISOString(); // 2h
    const result = formatElapsed(ts, undefined);
    expect(result).toMatch(/^hace \d+h \d+m$/);
  });

  it("returns '-' for missing", () => {
    expect(formatElapsed(undefined, undefined)).toBe("-");
  });

  it("falls back to updatedAt", () => {
    const ts = new Date(Date.now() - 2000).toISOString();
    expect(formatElapsed(undefined, ts)).toBe("ahora");
  });
});

// ---------------------------------------------------------------------------
// classifyLiveness
// ---------------------------------------------------------------------------
describe("classifyLiveness", () => {
  it("returns 'alive' for very recent", () => {
    const ts = new Date(Date.now() - 5000).toISOString();
    expect(classifyLiveness(ts, undefined)).toBe("alive");
  });

  it("returns 'slow' between 30-120s", () => {
    const ts = new Date(Date.now() - 60_000).toISOString();
    expect(classifyLiveness(ts, undefined)).toBe("slow");
  });

  it("returns 'stalled' after 120s", () => {
    const ts = new Date(Date.now() - 200_000).toISOString();
    expect(classifyLiveness(ts, undefined)).toBe("stalled");
  });

  it("uses relaxed thresholds for gates stage", () => {
    const ts = new Date(Date.now() - 60_000).toISOString();
    // 60s would be "slow" normally but "alive" for gates
    expect(classifyLiveness(ts, undefined, "gates")).toBe("alive");
  });

  it("returns 'stalled' for missing", () => {
    expect(classifyLiveness(undefined, undefined)).toBe("stalled");
  });
});
