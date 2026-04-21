/**
 * @vitest-environment jsdom
 */
import { describe, expect, it, vi } from "vitest";

import { createIntakeFileRow } from "@/shared/ui/molecules/intakeFileRow";
import { createStageProgressItem } from "@/shared/ui/molecules/stageProgressItem";
import { createLogTailViewer } from "@/shared/ui/molecules/logTailViewer";

describe("molecule: intakeFileRow", () => {
  const baseVm = {
    filename: "decreto-1625.pdf",
    mime: "application/pdf",
    bytes: 1024 * 512,
    detectedTopic: "renta",
    topicLabel: "Renta",
    combinedConfidence: 0.92,
    requiresReview: false,
    coercionMethod: null,
  };

  it("renders a file chip", () => {
    const node = createIntakeFileRow(baseVm);
    expect(node.querySelector(".lia-file-chip")).toBeTruthy();
    expect(node.querySelector(".lia-file-chip__name")?.textContent).toBe("decreto-1625.pdf");
  });

  it("renders a topic badge tagged with the detected key", () => {
    const node = createIntakeFileRow(baseVm);
    const badge = node.querySelector(".lia-intake-file-row__topic");
    expect(badge).toBeTruthy();
    expect(badge?.textContent).toBe("Renta");
    expect(badge?.getAttribute("data-topic")).toBe("renta");
  });

  it("renders a confidence pill as a percent", () => {
    const node = createIntakeFileRow(baseVm);
    const conf = node.querySelector(".lia-intake-file-row__confidence");
    expect(conf?.textContent).toBe("92%");
  });

  it("adds a requires_review marker only when flagged", () => {
    const without = createIntakeFileRow(baseVm);
    expect(without.querySelector(".lia-intake-file-row__review")).toBeNull();

    const flagged = createIntakeFileRow({ ...baseVm, requiresReview: true });
    const marker = flagged.querySelector(".lia-intake-file-row__review");
    expect(marker).toBeTruthy();
    expect(marker?.textContent).toContain("revisión");
  });

  it("shows the coercion method when provided", () => {
    const node = createIntakeFileRow({ ...baseVm, coercionMethod: "pdf-to-md" });
    expect(node.querySelector(".lia-intake-file-row__coercion")?.textContent).toBe("pdf-to-md");
  });
});

describe("molecule: stageProgressItem", () => {
  it("renders a progress dot that matches the requested status", () => {
    const node = createStageProgressItem({
      name: "parse",
      label: "Parsing",
      status: "running",
    });
    const dot = node.querySelector(".lia-progress-dot");
    expect(dot).toBeTruthy();
    expect(dot?.className).toContain("lia-progress-dot--running");
  });

  it("renders counts text with 2-3 canonical keys joined by commas", () => {
    const node = createStageProgressItem({
      name: "ingest",
      label: "Ingesta",
      status: "done",
      counts: { docs: 12, chunks: 34, edges: 7, embeddings_generated: 88 },
    });
    const counts = node.querySelector(".lia-stage-progress-item__counts");
    expect(counts?.textContent).toBe("docs: 12, chunks: 34, edges: 7");
  });

  it("shows an error callout when status=failed and errorMessage is provided", () => {
    const node = createStageProgressItem({
      name: "embed",
      label: "Embedding",
      status: "failed",
      errorMessage: "timeout calling OpenAI",
    });
    const err = node.querySelector(".lia-stage-progress-item__error");
    expect(err).toBeTruthy();
    expect(err?.textContent).toBe("timeout calling OpenAI");
    expect(err?.getAttribute("role")).toBe("alert");
  });

  it("computes duration text from ISO timestamps", () => {
    const node = createStageProgressItem({
      name: "parse",
      label: "Parsing",
      status: "done",
      startedAt: "2026-04-20T10:00:00Z",
      finishedAt: "2026-04-20T10:01:05Z",
    });
    expect(node.querySelector(".lia-stage-progress-item__duration")?.textContent).toBe("1m 5s");
  });

  it("renders seconds-only duration when under one minute", () => {
    const node = createStageProgressItem({
      name: "parse",
      label: "Parsing",
      status: "done",
      startedAt: 1_000_000,
      finishedAt: 1_045_000,
    });
    expect(node.querySelector(".lia-stage-progress-item__duration")?.textContent).toBe("45s");
  });
});

describe("molecule: logTailViewer", () => {
  it("renders initial lines into the pre body", () => {
    const { element } = createLogTailViewer({ initialLines: ["boot", "ready"] });
    const pre = element.querySelector(".lia-log-tail-viewer__body");
    expect(pre?.textContent).toBe("boot\nready");
  });

  it("appends new lines onto the existing buffer", () => {
    const { element, appendLines } = createLogTailViewer({ initialLines: ["a"] });
    appendLines(["b", "c"]);
    const pre = element.querySelector(".lia-log-tail-viewer__body");
    expect(pre?.textContent).toBe("a\nb\nc");
  });

  it("clears the body when clear() is called", () => {
    const { element, appendLines, clear } = createLogTailViewer({ initialLines: ["x"] });
    appendLines(["y"]);
    clear();
    const pre = element.querySelector(".lia-log-tail-viewer__body");
    expect(pre?.textContent).toBe("");
  });

  it("invokes the onCopy callback when the copy button is clicked", () => {
    const onCopy = vi.fn();
    const { element } = createLogTailViewer({ initialLines: ["hello"], onCopy });
    const btn = element.querySelector(".lia-log-tail-viewer__copy") as HTMLButtonElement;
    btn.click();
    expect(onCopy).toHaveBeenCalledTimes(1);
  });

  it("scrolls the body to the bottom after append when autoScroll is on", () => {
    const { element, appendLines } = createLogTailViewer({
      initialLines: ["1"],
      autoScroll: true,
    });
    const pre = element.querySelector(".lia-log-tail-viewer__body") as HTMLPreElement;

    let observedScrollTop = 0;
    Object.defineProperty(pre, "scrollHeight", { configurable: true, get: () => 999 });
    Object.defineProperty(pre, "scrollTop", {
      configurable: true,
      get: () => observedScrollTop,
      set: (v: number) => {
        observedScrollTop = v;
      },
    });

    appendLines(["2", "3"]);
    expect(observedScrollTop).toBe(999);
  });

  it("renders inside a <details> element with a summary label", () => {
    const { element } = createLogTailViewer({ summaryLabel: "Log de ejecución" });
    const details = element.querySelector("details");
    const summary = element.querySelector("summary");
    expect(details).toBeTruthy();
    expect(summary?.textContent).toBe("Log de ejecución");
  });
});
