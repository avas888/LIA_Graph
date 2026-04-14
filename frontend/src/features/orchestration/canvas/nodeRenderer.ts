import type { PipelineGraph, LayoutResult } from "../graph/types";
import { renderActorBadges } from "./actorBadge";

/**
 * Renders all nodes as positioned HTML elements inside the canvas container.
 * Also renders lane backgrounds and labels.
 */
export function renderNodes(
  canvas: HTMLElement,
  graph: PipelineGraph,
  layout: LayoutResult,
): void {
  // Render lane backgrounds
  for (const lane of graph.lanes) {
    const rect = layout.laneRects.get(lane.id);
    if (!rect) continue;

    const laneEl = document.createElement("div");
    laneEl.className = "orch-lane";
    laneEl.dataset.lane = lane.id;
    laneEl.style.cssText = `left:${rect.x}px;top:${rect.y}px;width:${rect.w}px;height:${rect.h}px;`;

    const labelEl = document.createElement("div");
    labelEl.className = "orch-lane-label";
    labelEl.textContent = lane.label;
    laneEl.appendChild(labelEl);

    canvas.appendChild(laneEl);
  }

  // Render node cards
  for (const node of graph.nodes) {
    const pos = layout.nodePositions.get(node.id);
    if (!pos) continue;

    const article = document.createElement("article");
    article.className = "orch-node";
    article.dataset.nodeId = node.id;
    article.dataset.kind = node.kind;
    article.dataset.pipeline = node.lane;
    article.style.cssText = `left:${pos.x}px;top:${pos.y}px;width:${pos.w}px;`;

    const metricsHtml = node.metrics?.length
      ? `<div class="orch-node-metrics">${node.metrics.map((m) => `<span class="orch-metric">${m}</span>`).join("")}</div>`
      : "";

    const detailHtml = node.detailHtml
      ? `<div class="orch-node-detail" hidden>${node.detailHtml}</div>`
      : "";

    const hasDetail = !!node.detailHtml;
    const toggleHtml = hasDetail
      ? `<button class="orch-node-toggle" aria-expanded="false" aria-label="Expandir detalles">▸</button>`
      : "";

    article.innerHTML = `
      <div class="orch-node-head">
        <div class="orch-node-badges">${renderActorBadges(node.actors)}</div>
        <h3 class="orch-node-title">${node.title}</h3>
        ${toggleHtml}
      </div>
      <p class="orch-node-summary">${node.summary}</p>
      ${metricsHtml}
      ${detailHtml}
    `;

    canvas.appendChild(article);
  }
}

/**
 * Reposition all nodes and lane backgrounds after layout recalculation.
 */
export function repositionNodes(
  canvas: HTMLElement,
  graph: PipelineGraph,
  layout: LayoutResult,
): void {
  // Update lane backgrounds
  for (const lane of graph.lanes) {
    const rect = layout.laneRects.get(lane.id);
    if (!rect) continue;
    const laneEl = canvas.querySelector<HTMLElement>(`.orch-lane[data-lane="${lane.id}"]`);
    if (laneEl) {
      laneEl.style.cssText = `left:${rect.x}px;top:${rect.y}px;width:${rect.w}px;height:${rect.h}px;`;
    }
  }

  // Update node positions
  for (const node of graph.nodes) {
    const pos = layout.nodePositions.get(node.id);
    if (!pos) continue;
    const el = canvas.querySelector<HTMLElement>(`.orch-node[data-node-id="${node.id}"]`);
    if (el) {
      el.style.left = `${pos.x}px`;
      el.style.top = `${pos.y}px`;
      el.style.width = `${pos.w}px`;
    }
  }

  // Resize canvas
  canvas.style.width = `${layout.canvasWidth}px`;
  canvas.style.height = `${layout.canvasHeight}px`;
}
