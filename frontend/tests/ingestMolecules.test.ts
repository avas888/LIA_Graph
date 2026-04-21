/**
 * @vitest-environment jsdom
 */
import { describe, expect, it } from "vitest";

import { createMetricCard } from "@/shared/ui/molecules/metricCard";
import { createRunStatusBadge } from "@/shared/ui/molecules/runStatusBadge";
import { createGenerationRow } from "@/shared/ui/molecules/generationRow";
import { createPipelineFlow } from "@/shared/ui/molecules/pipelineFlow";

describe("molecule: metricCard", () => {
  it("composes label + value + hint", () => {
    const node = createMetricCard({
      label: "Documentos servidos",
      value: 1246,
      hint: "8.400 chunks",
    });
    expect(node.querySelector(".lia-metric-card__label")?.textContent).toBe("Documentos servidos");
    expect(node.querySelector(".lia-metric-value")).toBeTruthy();
    expect(node.querySelector(".lia-metric-card__hint")?.textContent).toBe("8.400 chunks");
  });

  it("applies tone modifier", () => {
    const node = createMetricCard({ label: "X", value: 0, tone: "warning" });
    expect(node.className).toContain("lia-metric-card--warning");
  });

  it("omits hint slot when not provided", () => {
    const node = createMetricCard({ label: "X", value: 1 });
    expect(node.querySelector(".lia-metric-card__hint")).toBeNull();
  });
});

describe("molecule: runStatusBadge", () => {
  it("maps every status to a Spanish label", () => {
    const cases: Array<[string, string]> = [
      ["active", "Activa"],
      ["superseded", "Reemplazada"],
      ["running", "En curso"],
      ["queued", "En cola"],
      ["failed", "Falló"],
      ["pending", "Pendiente"],
    ];
    for (const [status, label] of cases) {
      const node = createRunStatusBadge({ status: status as never });
      expect(node.querySelector(".lia-run-status__label")?.textContent).toBe(label);
      expect(node.className).toContain(`lia-run-status--${status}`);
    }
  });

  it("pulses for running and queued only", () => {
    expect(createRunStatusBadge({ status: "running" }).querySelector(".lia-status-dot--pulse")).toBeTruthy();
    expect(createRunStatusBadge({ status: "queued" }).querySelector(".lia-status-dot--pulse")).toBeTruthy();
    expect(createRunStatusBadge({ status: "active" }).querySelector(".lia-status-dot--pulse")).toBeNull();
    expect(createRunStatusBadge({ status: "failed" }).querySelector(".lia-status-dot--pulse")).toBeNull();
  });
});

describe("molecule: generationRow", () => {
  const baseVm = {
    generationId: "gen_2026_04_19_smoke",
    status: "active" as const,
    generatedAt: "2026-04-19T18:20:00Z",
    documents: 1246,
    chunks: 8400,
  };

  it("emits a non-button when no onClick is provided", () => {
    const node = createGenerationRow(baseVm);
    expect(node.tagName).toBe("DIV");
    expect(node.querySelector(".lia-generation-row__id")?.textContent).toBe(
      "gen_2026_04_19_smoke",
    );
  });

  it("emits a button + dispatches onClick when handler provided", () => {
    let received: string | null = null;
    const node = createGenerationRow(baseVm, (id) => {
      received = id;
    });
    expect(node.tagName).toBe("BUTTON");
    (node as unknown as HTMLButtonElement).click();
    expect(received).toBe("gen_2026_04_19_smoke");
  });

  it("renders top-class metadata when present", () => {
    const node = createGenerationRow({ ...baseVm, topClass: "normativa", topClassCount: 1044 });
    const family = node.querySelector(".lia-generation-row__family")!;
    expect(family.textContent).toContain("normativa");
    expect(family.textContent).toContain("1.044");
  });

  it("renders an em-dash for missing date", () => {
    const node = createGenerationRow({ ...baseVm, generatedAt: "" });
    expect(node.querySelector(".lia-generation-row__date")?.textContent).toBe("—");
  });
});

describe("molecule: pipelineFlow", () => {
  it("renders three stages separated by arrows", () => {
    const node = createPipelineFlow({ activeStage: "wip" });
    const stages = node.querySelectorAll(".lia-pipeline-flow__stage");
    const arrows = node.querySelectorAll(".lia-pipeline-flow__arrow");
    expect(stages).toHaveLength(3);
    expect(arrows).toHaveLength(2);
  });

  it("marks only the active stage", () => {
    const node = createPipelineFlow({ activeStage: "cloud" });
    const active = node.querySelectorAll(".lia-pipeline-flow__stage--active");
    expect(active).toHaveLength(1);
    expect((active[0] as HTMLElement).getAttribute("data-stage")).toBe("cloud");
  });

  it("uses canonical stage labels reflecting orchestration.md", () => {
    const node = createPipelineFlow({ activeStage: "wip" });
    const labels = Array.from(node.querySelectorAll(".lia-pipeline-flow__label")).map(
      (el) => el.textContent,
    );
    expect(labels).toEqual(["knowledge_base/", "WIP", "Cloud"]);
  });
});
