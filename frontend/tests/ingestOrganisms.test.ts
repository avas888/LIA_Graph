/**
 * @vitest-environment jsdom
 */
import { describe, expect, it, vi } from "vitest";

import { createCorpusOverview } from "@/shared/ui/organisms/corpusOverview";
import { createGenerationsList } from "@/shared/ui/organisms/generationsList";
import { createRunTriggerCard } from "@/shared/ui/organisms/runTriggerCard";

describe("organism: corpusOverview", () => {
  const baseVm = {
    documents: 1246,
    chunks: 8400,
    graphNodes: 2617,
    graphEdges: 20345,
    graphOk: true,
    auditScanned: 1385,
    auditIncluded: 1292,
    auditExcluded: 93,
    auditPendingRevisions: 0,
    activeGenerationId: "gen_2026_04_19_smoke",
    activatedAt: new Date(Date.now() - 30 * 60_000).toISOString(),
  };

  it("renders four metric cards", () => {
    const node = createCorpusOverview(baseVm);
    const cards = node.querySelectorAll(".lia-metric-card");
    expect(cards).toHaveLength(4);
  });

  it("displays the active generation id when present", () => {
    const node = createCorpusOverview(baseVm);
    const subtitle = node.querySelector(".lia-corpus-overview__subtitle")!;
    expect(subtitle.textContent).toContain("gen_2026_04_19_smoke");
  });

  it("shows fallback when no generation is active", () => {
    const node = createCorpusOverview({ ...baseVm, activeGenerationId: "", activatedAt: "" });
    const subtitle = node.querySelector(".lia-corpus-overview__subtitle")!;
    expect(subtitle.textContent).toContain("Ninguna generación activa");
  });

  it("colors the graph card amber when graphOk is false", () => {
    const node = createCorpusOverview({ ...baseVm, graphOk: false });
    const cards = node.querySelectorAll(".lia-metric-card");
    // Second card is the graph card (per createCorpusOverview order).
    expect(cards[1].className).toContain("lia-metric-card--warning");
  });

  it("flags pending revisions tone when > 0", () => {
    const node = createCorpusOverview({ ...baseVm, auditPendingRevisions: 3 });
    const cards = node.querySelectorAll(".lia-metric-card");
    expect(cards[3].className).toContain("lia-metric-card--warning");
  });
});

describe("organism: generationsList", () => {
  it("shows empty state when rows are empty", () => {
    const node = createGenerationsList({ rows: [] });
    expect(node.querySelector(".lia-generations-list__feedback")?.textContent).toContain(
      "Aún no hay generaciones",
    );
  });

  it("shows error state when errorMessage provided", () => {
    const node = createGenerationsList({ rows: [], errorMessage: "boom" });
    const fb = node.querySelector(".lia-generations-list__feedback--error")!;
    expect(fb.textContent).toBe("boom");
  });

  it("renders header row + N data rows when populated", () => {
    const node = createGenerationsList({
      rows: [
        {
          generationId: "gen_a",
          status: "active",
          generatedAt: "2026-04-19T18:20:00Z",
          documents: 10,
          chunks: 30,
        },
        {
          generationId: "gen_b",
          status: "superseded",
          generatedAt: "2026-04-18T10:00:00Z",
          documents: 5,
          chunks: 12,
        },
      ],
    });
    expect(node.querySelector(".lia-generations-list__head-row")).toBeTruthy();
    expect(node.querySelectorAll(".lia-generation-row")).toHaveLength(2);
  });
});

describe("organism: runTriggerCard", () => {
  it("renders the pipeline-flow molecule with WIP active by default", () => {
    const node = createRunTriggerCard({
      activeJobId: null,
      lastRunStatus: null,
      disabled: false,
      onTrigger: () => undefined,
    });
    const flow = node.querySelector(".lia-pipeline-flow")!;
    expect(flow).toBeTruthy();
    const active = flow.querySelector(".lia-pipeline-flow__stage--active") as HTMLElement;
    expect(active.getAttribute("data-stage")).toBe("wip");
  });

  it("disables the submit button when in disabled state", () => {
    const node = createRunTriggerCard({
      activeJobId: "job-1",
      lastRunStatus: "running",
      disabled: true,
      onTrigger: () => undefined,
    });
    const submit = node.querySelector("button[type=submit]") as HTMLButtonElement;
    expect(submit.disabled).toBe(true);
    expect(submit.textContent).toBe("Ejecutando…");
  });

  it("invokes onTrigger with form values on submit", () => {
    const onTrigger = vi.fn();
    const node = createRunTriggerCard({
      activeJobId: null,
      lastRunStatus: null,
      disabled: false,
      onTrigger,
    });
    document.body.appendChild(node);

    const suinInput = node.querySelector<HTMLInputElement>("[name=suin_scope]")!;
    suinInput.value = "et";

    const productionRadio = node.querySelector<HTMLInputElement>(
      "[name=supabase_target][value=production]",
    )!;
    productionRadio.checked = true;

    const form = node.querySelector("form")!;
    form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));

    expect(onTrigger).toHaveBeenCalledWith({ suinScope: "et", supabaseTarget: "production" });

    document.body.removeChild(node);
  });

  it("does not invoke onTrigger when disabled", () => {
    const onTrigger = vi.fn();
    const node = createRunTriggerCard({
      activeJobId: "job-x",
      lastRunStatus: "running",
      disabled: true,
      onTrigger,
    });
    document.body.appendChild(node);
    const form = node.querySelector("form")!;
    form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    expect(onTrigger).not.toHaveBeenCalled();
    document.body.removeChild(node);
  });
});
