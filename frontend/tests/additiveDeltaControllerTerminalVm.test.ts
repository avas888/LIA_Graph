/**
 * @vitest-environment jsdom
 *
 * Locks the wire-level contract between the additive-delta SSE envelope and
 * the terminal-banner VM. The backend nests per-sink counters under
 * ``report_json.sink_result``; the banner reads ``vm.report.documents_added``
 * et al directly. If these drift apart, operators see "0 / 0 / 0" on every
 * successful run. See ingestionfix_v3 §5 Phase 1.
 */
import { describe, expect, it } from "vitest";

import { buildAdditiveDeltaTerminalVm } from "@/features/ingest/additiveDeltaController";

describe("buildAdditiveDeltaTerminalVm", () => {
  it("flattens sink_result fields onto vm.report", () => {
    const vm = buildAdditiveDeltaTerminalVm({
      stage: "completed",
      jobId: "job_abc123",
      reportJson: {
        delta_id: "delta_20260423_185848_b357ed",
        target: "production",
        sink_result: {
          documents_added: 12,
          documents_modified: 3,
          documents_retired: 1,
          chunks_written: 47,
          chunks_deleted: 2,
          edges_written: 19,
          edges_deleted: 0,
        },
      },
      errorClass: null,
      errorMessage: null,
    });

    expect(vm.stage).toBe("completed");
    expect(vm.deltaId).toBe("delta_20260423_185848_b357ed");
    expect(vm.report?.documents_added).toBe(12);
    expect(vm.report?.documents_modified).toBe(3);
    expect(vm.report?.documents_retired).toBe(1);
    expect(vm.report?.chunks_written).toBe(47);
    expect(vm.report?.chunks_deleted).toBe(2);
    expect(vm.report?.edges_written).toBe(19);
    expect(vm.report?.edges_deleted).toBe(0);
  });

  it("does NOT leak envelope fields (regression: v2 Phase 11)", () => {
    const vm = buildAdditiveDeltaTerminalVm({
      stage: "completed",
      jobId: "job_abc123",
      reportJson: {
        delta_id: "delta_42",
        target: "production",
        falkor_statements: 216,
        sink_result: {
          documents_added: 0,
          documents_modified: 0,
          documents_retired: 0,
          chunks_written: 0,
          chunks_deleted: 0,
          edges_written: 0,
          edges_deleted: 0,
        },
      },
      errorClass: null,
      errorMessage: null,
    });

    // Envelope-only keys must not appear on report: report is the sink slice.
    expect(vm.report).not.toHaveProperty("falkor_statements");
    expect(vm.report).not.toHaveProperty("target");
    expect(vm.report).not.toHaveProperty("delta_id");
  });

  it("falls back to jobId as deltaId when reportJson.delta_id is missing", () => {
    const vm = buildAdditiveDeltaTerminalVm({
      stage: "failed",
      jobId: "job_only",
      reportJson: null,
      errorClass: "delta_lock_busy",
      errorMessage: "Another apply is in flight.",
    });
    expect(vm.deltaId).toBe("job_only");
    expect(vm.report).toBeNull();
    expect(vm.errorClass).toBe("delta_lock_busy");
    expect(vm.errorMessage).toBe("Another apply is in flight.");
  });

  it("passes through stage (failed / cancelled) untouched", () => {
    const failed = buildAdditiveDeltaTerminalVm({
      stage: "failed",
      jobId: "j",
      reportJson: null,
      errorClass: null,
      errorMessage: null,
    });
    expect(failed.stage).toBe("failed");

    const cancelled = buildAdditiveDeltaTerminalVm({
      stage: "cancelled",
      jobId: "j",
      reportJson: null,
      errorClass: null,
      errorMessage: null,
    });
    expect(cancelled.stage).toBe("cancelled");
  });

  it("sink_result absent ⇒ report is null (older runs, failed before sink)", () => {
    const vm = buildAdditiveDeltaTerminalVm({
      stage: "completed",
      jobId: "j",
      reportJson: { delta_id: "d" },
      errorClass: null,
      errorMessage: null,
    });
    expect(vm.report).toBeNull();
    expect(vm.deltaId).toBe("d");
  });
});
