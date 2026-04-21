/**
 * 3-stage Lia_Graph ingestion pipeline visualization.
 *
 * Source-of-truth: docs/guide/orchestration.md Lane 0.
 *   knowledge_base/  →  ingest (WIP Supabase + local Falkor)  →  Promoción (Cloud Supabase + cloud Falkor)
 */

export type PipelineStage = "knowledge_base" | "wip" | "cloud";

export interface PipelineFlowOptions {
  activeStage: PipelineStage;
  className?: string;
}

const STAGES: ReadonlyArray<{ key: PipelineStage; label: string; sublabel: string }> = [
  { key: "knowledge_base", label: "knowledge_base/", sublabel: "snapshot Dropbox" },
  { key: "wip", label: "WIP", sublabel: "Supabase local + Falkor local" },
  { key: "cloud", label: "Cloud", sublabel: "Supabase cloud + Falkor cloud" },
];

export function createPipelineFlow(opts: PipelineFlowOptions): HTMLElement {
  const { activeStage, className = "" } = opts;
  const root = document.createElement("nav");
  root.className = ["lia-pipeline-flow", className].filter(Boolean).join(" ");
  root.setAttribute("data-lia-component", "pipeline-flow");
  root.setAttribute("aria-label", "Pipeline de ingestión Lia Graph");

  STAGES.forEach((stage, idx) => {
    if (idx > 0) {
      const arrow = document.createElement("span");
      arrow.className = "lia-pipeline-flow__arrow";
      arrow.setAttribute("aria-hidden", "true");
      arrow.textContent = "→";
      root.appendChild(arrow);
    }

    const node = document.createElement("div");
    node.className = [
      "lia-pipeline-flow__stage",
      stage.key === activeStage ? "lia-pipeline-flow__stage--active" : "",
    ]
      .filter(Boolean)
      .join(" ");
    node.setAttribute("data-stage", stage.key);

    const label = document.createElement("span");
    label.className = "lia-pipeline-flow__label";
    label.textContent = stage.label;
    node.appendChild(label);

    const sub = document.createElement("span");
    sub.className = "lia-pipeline-flow__sublabel";
    sub.textContent = stage.sublabel;
    node.appendChild(sub);

    root.appendChild(node);
  });

  return root;
}
