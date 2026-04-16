import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { renderOrchestrationShell } from "@/app/orchestration/shell";
import { mountOrchestrationApp } from "@/features/orchestration/orchestrationApp";
import { createI18n } from "@/shared/i18n";

describe("orchestration app", () => {
  beforeEach(() => {
    const ctx = new Proxy(
      {},
      {
        get: () => () => {},
      },
    ) as CanvasRenderingContext2D;
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockImplementation(
      (() => ctx),
    );
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the graph canvas and expands node detail on toggle", () => {
    const i18n = createI18n("es-CO");
    document.body.innerHTML = `<div id="app">${renderOrchestrationShell(i18n)}</div>`;

    const root = document.getElementById("app");
    if (!root) {
      throw new Error("Missing app root.");
    }

    mountOrchestrationApp(root, { i18n });

    const nodes = Array.from(document.querySelectorAll<HTMLElement>(".orch-node"));
    const lanes = Array.from(document.querySelectorAll<HTMLElement>(".orch-lane"));
    const laneButtons = Array.from(document.querySelectorAll<HTMLButtonElement>(".orch-lane-btn"));
    const firstToggle = document.querySelector<HTMLButtonElement>(".orch-node-toggle");
    const firstDetail = document.querySelector<HTMLElement>(".orch-node-detail");

    expect(lanes.length).toBeGreaterThan(0);
    expect(nodes.length).toBeGreaterThan(0);
    expect(laneButtons.length).toBeGreaterThan(0);
    expect(document.getElementById("orch-minimap-canvas")).not.toBeNull();
    expect(firstToggle).not.toBeNull();
    expect(firstDetail).not.toBeNull();
    expect(firstDetail?.hidden).toBe(true);
    expect(document.body.textContent).toContain("Served Chat (Pipeline D)");
    expect(document.body.textContent).toContain("build_graph_retrieval_plan()");
    expect(document.body.textContent).not.toContain("Pipeline C");

    firstToggle?.click();

    expect(firstToggle?.getAttribute("aria-expanded")).toBe("true");
    expect(firstDetail?.hidden).toBe(false);
  });
});
