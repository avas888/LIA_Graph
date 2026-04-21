/**
 * @vitest-environment jsdom
 */
import { describe, expect, it, vi } from "vitest";

import { createProgressDot } from "@/shared/ui/atoms/progressDot";
import { createFileChip, formatBytes } from "@/shared/ui/atoms/fileChip";

describe("atom: progressDot", () => {
  it("renders a pending dot", () => {
    const node = createProgressDot({ status: "pending" });
    expect(node.tagName).toBe("SPAN");
    expect(node.className).toContain("lia-progress-dot--pending");
    expect(node.className).not.toContain("--pulse");
  });

  it("renders a running dot with a pulse class", () => {
    const node = createProgressDot({ status: "running" });
    expect(node.className).toContain("lia-progress-dot--running");
    expect(node.className).toContain("lia-progress-dot--pulse");
  });

  it("renders a done dot", () => {
    const node = createProgressDot({ status: "done" });
    expect(node.className).toContain("lia-progress-dot--done");
    expect(node.className).not.toContain("--pulse");
  });

  it("renders a failed dot", () => {
    const node = createProgressDot({ status: "failed" });
    expect(node.className).toContain("lia-progress-dot--failed");
    expect(node.className).not.toContain("--pulse");
  });

  it("produces a fresh node with updated status when re-invoked", () => {
    const first = createProgressDot({ status: "pending" });
    const second = createProgressDot({ status: "running" });
    const third = createProgressDot({ status: "done" });
    expect(first.getAttribute("data-status")).toBe("pending");
    expect(second.getAttribute("data-status")).toBe("running");
    expect(third.getAttribute("data-status")).toBe("done");
    expect(first).not.toBe(second);
    expect(second).not.toBe(third);
  });

  it("forwards aria-label when provided", () => {
    const node = createProgressDot({ status: "running", ariaLabel: "Parsing SUIN" });
    expect(node.getAttribute("aria-label")).toBe("Parsing SUIN");
    expect(node.getAttribute("role")).toBe("status");
  });
});

describe("atom: fileChip", () => {
  it("renders filename, formatted size, and a type icon", () => {
    const node = createFileChip({
      filename: "ley-1943.pdf",
      bytes: 1024 * 27,
      mime: "application/pdf",
    });
    expect(node.getAttribute("data-lia-component")).toBe("file-chip");
    expect(node.querySelector(".lia-file-chip__name")?.textContent).toBe("ley-1943.pdf");
    expect(node.querySelector(".lia-file-chip__size")?.textContent).toBe("27 KB");
    const icon = node.querySelector(".lia-file-chip__icon");
    expect(icon).toBeTruthy();
    expect((icon as HTMLElement).textContent?.length).toBeGreaterThan(0);
  });

  it("fires onRemove when the remove button is clicked", () => {
    const handler = vi.fn();
    const node = createFileChip({
      filename: "decreto-1625.md",
      bytes: 4096,
      onRemove: handler,
    });
    const remove = node.querySelector(".lia-file-chip__remove") as HTMLButtonElement;
    expect(remove).toBeTruthy();
    remove.click();
    expect(handler).toHaveBeenCalledTimes(1);
  });

  it("omits the remove button when no handler is provided", () => {
    const node = createFileChip({ filename: "notes.txt", bytes: 1200 });
    expect(node.querySelector(".lia-file-chip__remove")).toBeNull();
  });

  it("carries a title attribute combining filename and size", () => {
    const node = createFileChip({ filename: "oficio.docx", bytes: 2048 });
    expect(node.title).toContain("oficio.docx");
    expect(node.title).toContain("2 KB");
  });
});

describe("helper: formatBytes", () => {
  it("returns '0 B' for zero", () => {
    expect(formatBytes(0)).toBe("0 B");
  });

  it("returns '1 KB' for exactly 1024 bytes", () => {
    expect(formatBytes(1024)).toBe("1 KB");
  });

  it("returns '1 MB' for exactly 1048576 bytes", () => {
    expect(formatBytes(1024 * 1024)).toBe("1 MB");
  });

  it("rounds kilobyte values with one decimal when fractional", () => {
    expect(formatBytes(1536)).toBe("1.5 KB");
  });
});
