/**
 * @vitest-environment jsdom
 */
import { describe, expect, it } from "vitest";

import { createMetricValue } from "@/shared/ui/atoms/metricValue";
import { createStatusDot } from "@/shared/ui/atoms/statusDot";

describe("atom: metricValue", () => {
  it("renders a localized number with no unit by default", () => {
    const node = createMetricValue({ value: 1234567 });
    expect(node.tagName).toBe("SPAN");
    expect(node.getAttribute("data-lia-component")).toBe("metric-value");
    const number = node.querySelector(".lia-metric-value__number")!;
    // es-CO uses thin spaces / dots — accept either by checking digit presence.
    expect(number.textContent).toMatch(/1[.,\s]234[.,\s]567/);
    expect(node.querySelector(".lia-metric-value__unit")).toBeNull();
  });

  it("renders a unit when provided", () => {
    const node = createMetricValue({ value: 42, unit: "nodos" });
    const unit = node.querySelector(".lia-metric-value__unit")!;
    expect(unit.textContent).toBe("nodos");
  });

  it("supports size variants", () => {
    expect(createMetricValue({ value: 1, size: "sm" }).className).toContain("lia-metric-value--sm");
    expect(createMetricValue({ value: 1, size: "lg" }).className).toContain("lia-metric-value--lg");
  });

  it("accepts string values verbatim", () => {
    const node = createMetricValue({ value: "—" });
    const number = node.querySelector(".lia-metric-value__number")!;
    expect(number.textContent).toBe("—");
  });
});

describe("atom: statusDot", () => {
  it("emits a span with the requested tone class", () => {
    const node = createStatusDot({ tone: "active" });
    expect(node.tagName).toBe("SPAN");
    expect(node.className).toContain("lia-status-dot--active");
    expect(node.getAttribute("role")).toBe("status");
  });

  it("adds pulse class only when requested", () => {
    expect(createStatusDot({ tone: "running" }).className).not.toContain("--pulse");
    expect(createStatusDot({ tone: "running", pulse: true }).className).toContain("--pulse");
  });

  it("forwards aria-label", () => {
    const node = createStatusDot({ tone: "error", ariaLabel: "Falló" });
    expect(node.getAttribute("aria-label")).toBe("Falló");
  });
});
