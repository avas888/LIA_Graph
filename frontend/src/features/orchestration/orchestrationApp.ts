import type { I18nRuntime } from "@/shared/i18n";
import type { LaneId, LayoutResult } from "./graph/types";
import { pipelineGraph } from "./graph/pipelineGraph";
import { computeLayout, recomputeLayout } from "./layout/dagLayout";
import { renderNodes, repositionNodes } from "./canvas/nodeRenderer";
import { renderEdges } from "./canvas/edgeRenderer";
import { initMinimap, scrollToLane, initKeyboardNav } from "./canvas/canvasController";

export function mountOrchestrationApp(
  root: HTMLElement,
  _ctx: { i18n: I18nRuntime },
): void {
  const viewport = root.querySelector<HTMLElement>("#orch-viewport");
  const canvas = root.querySelector<HTMLElement>("#orch-canvas");
  const svg = root.querySelector<SVGSVGElement>("#orch-svg");
  const minimapCanvas = root.querySelector<HTMLCanvasElement>("#orch-minimap-canvas");
  const minimapLens = root.querySelector<HTMLElement>("#orch-minimap-lens");

  if (!viewport || !canvas || !svg || !minimapCanvas || !minimapLens) return;

  // Initial layout
  let layout: LayoutResult = computeLayout(pipelineGraph);
  const expandedHeights = new Map<string, number>();

  // Size canvas
  canvas.style.width = `${layout.canvasWidth}px`;
  canvas.style.height = `${layout.canvasHeight}px`;

  // Render nodes and edges
  renderNodes(canvas, pipelineGraph, layout);
  renderEdges(svg, pipelineGraph, layout);

  // Minimap
  let cleanupMinimap = initMinimap(
    { viewport, canvas, minimapCanvas, lens: minimapLens },
    layout,
  );

  // Keyboard navigation
  const cleanupKeyboard = initKeyboardNav(viewport);

  // Lane jump buttons
  const laneButtons = root.querySelectorAll<HTMLButtonElement>(".orch-lane-btn");
  laneButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const laneId = btn.dataset.lane as LaneId;
      scrollToLane(viewport, layout, laneId);
    });
  });

  // Expand/collapse node detail
  canvas.addEventListener("click", (e) => {
    const toggle = (e.target as HTMLElement).closest<HTMLButtonElement>(".orch-node-toggle");
    if (!toggle) return;

    const article = toggle.closest<HTMLElement>(".orch-node");
    if (!article) return;

    const nodeId = article.dataset.nodeId;
    if (!nodeId) return;

    const detail = article.querySelector<HTMLElement>(".orch-node-detail");
    if (!detail) return;

    const isExpanded = toggle.getAttribute("aria-expanded") === "true";

    if (isExpanded) {
      // Collapse
      detail.hidden = true;
      toggle.setAttribute("aria-expanded", "false");
      toggle.textContent = "▸";
      expandedHeights.set(nodeId, 0);
    } else {
      // Expand — temporarily show to measure
      detail.hidden = false;
      toggle.setAttribute("aria-expanded", "true");
      toggle.textContent = "▾";
      const detailH = detail.scrollHeight;
      expandedHeights.set(nodeId, detailH + 16); // 16 = padding
    }

    // Recompute layout and reposition
    layout = recomputeLayout(pipelineGraph, expandedHeights);
    canvas.style.width = `${layout.canvasWidth}px`;
    canvas.style.height = `${layout.canvasHeight}px`;
    repositionNodes(canvas, pipelineGraph, layout);
    renderEdges(svg, pipelineGraph, layout);

    // Rebuild minimap
    cleanupMinimap();
    cleanupMinimap = initMinimap(
      { viewport, canvas, minimapCanvas, lens: minimapLens },
      layout,
    );
  });

  // Cleanup on page unload (not strictly needed for static page, but good practice)
  window.addEventListener("beforeunload", () => {
    cleanupMinimap();
    cleanupKeyboard();
  });
}
