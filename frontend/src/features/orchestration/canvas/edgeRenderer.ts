import type { PipelineGraph, LayoutResult } from "../graph/types";
import { NODE_W, NODE_H } from "../layout/dagLayout";

const ARROW_ID = "orch-arrowhead";
const ARROW_CROSS_ID = "orch-arrowhead-cross";

/**
 * Render all edges as SVG paths inside the SVG overlay.
 */
export function renderEdges(
  svg: SVGSVGElement,
  graph: PipelineGraph,
  layout: LayoutResult,
): void {
  // Clear previous
  svg.innerHTML = "";

  // Set SVG dimensions
  svg.setAttribute("width", String(layout.canvasWidth));
  svg.setAttribute("height", String(layout.canvasHeight));
  svg.setAttribute("viewBox", `0 0 ${layout.canvasWidth} ${layout.canvasHeight}`);

  // Define arrowhead markers
  const defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
  defs.innerHTML = `
    <marker id="${ARROW_ID}" viewBox="0 0 10 7" refX="10" refY="3.5"
            markerWidth="8" markerHeight="6" orient="auto-start-reverse">
      <polygon points="0 0, 10 3.5, 0 7" fill="var(--orch-edge-color)" />
    </marker>
    <marker id="${ARROW_CROSS_ID}" viewBox="0 0 10 7" refX="10" refY="3.5"
            markerWidth="8" markerHeight="6" orient="auto-start-reverse">
      <polygon points="0 0, 10 3.5, 0 7" fill="var(--orch-edge-cross-color)" />
    </marker>
  `;
  svg.appendChild(defs);

  // Build node lookup for lane detection
  const nodeMap = new Map(graph.nodes.map((n) => [n.id, n]));

  for (const edge of graph.edges) {
    const fromPos = layout.nodePositions.get(edge.from);
    const toPos = layout.nodePositions.get(edge.to);
    if (!fromPos || !toPos) continue;

    const fromNode = nodeMap.get(edge.from);
    const toNode = nodeMap.get(edge.to);
    const isCross = edge.crossLane ?? (fromNode?.lane !== toNode?.lane);

    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    const d = isCross
      ? crossLanePath(fromPos, toPos)
      : sameLanePath(fromPos, toPos);

    path.setAttribute("d", d);
    path.setAttribute("class", isCross ? "orch-edge orch-edge--cross" : "orch-edge");
    path.setAttribute("marker-end", `url(#${isCross ? ARROW_CROSS_ID : ARROW_ID})`);
    svg.appendChild(path);

    // Optional label
    if (edge.label) {
      const midX = (fromPos.x + fromPos.w + toPos.x) / 2;
      const midY = (fromPos.y + fromPos.h / 2 + toPos.y + toPos.h / 2) / 2;

      const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
      text.setAttribute("x", String(midX));
      text.setAttribute("y", String(midY - 6));
      text.setAttribute("class", "orch-edge-label");
      text.textContent = edge.label;
      svg.appendChild(text);
    }
  }
}

interface Rect { x: number; y: number; w: number; h: number }

function sameLanePath(from: Rect, to: Rect): string {
  const x1 = from.x + NODE_W;
  const y1 = from.y + NODE_H / 2;
  const x2 = to.x;
  const y2 = to.y + NODE_H / 2;
  const mx = (x1 + x2) / 2;
  return `M ${x1},${y1} C ${mx},${y1} ${mx},${y2} ${x2},${y2}`;
}

function crossLanePath(from: Rect, to: Rect): string {
  const x1 = from.x + NODE_W / 2;
  const y1 = from.y + from.h;
  const x2 = to.x + NODE_W / 2;
  const y2 = to.y;

  // Vertical-first with rounded corners
  const midY = (y1 + y2) / 2;
  const r = 12; // corner radius

  if (Math.abs(x1 - x2) < 2) {
    // Straight vertical
    return `M ${x1},${y1} L ${x2},${y2}`;
  }

  const dx = x2 > x1 ? 1 : -1;
  return `M ${x1},${y1} L ${x1},${midY - r} Q ${x1},${midY} ${x1 + r * dx},${midY} L ${x2 - r * dx},${midY} Q ${x2},${midY} ${x2},${midY + r} L ${x2},${y2}`;
}
