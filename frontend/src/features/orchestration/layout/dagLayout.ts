import type { PipelineGraph, LaneId, LayoutRect, LayoutResult } from "../graph/types";

/* ── Layout constants ──────────────────────────────────────── */
const NODE_W = 260;
const NODE_H = 120;
const NODE_GAP_X = 80;
const NODE_GAP_Y = 40;
const LANE_PADDING_X = 60;
const LANE_PADDING_Y = 50;
const LANE_LABEL_H = 44;
const LANE_GAP = 60;
const CANVAS_PAD = 80;

export { NODE_W, NODE_H };

/**
 * Assign (x, y) coordinates to every node in the graph.
 * Nodes are grouped by lane (horizontal swim-lanes stacked vertically).
 * Within each lane, nodes are laid out left-to-right by `order`.
 *
 * Returns positions, lane rects, and total canvas dimensions.
 */
export function computeLayout(graph: PipelineGraph): LayoutResult {
  const nodePositions = new Map<string, LayoutRect>();
  const laneRects = new Map<LaneId, LayoutRect>();

  // Sort lanes by order
  const sortedLanes = [...graph.lanes].sort((a, b) => a.order - b.order);

  let currentY = CANVAS_PAD;
  let maxRight = 0;

  for (const lane of sortedLanes) {
    const laneNodes = graph.nodes
      .filter((n) => n.lane === lane.id)
      .sort((a, b) => a.order - b.order);

    const laneContentW = laneNodes.length * NODE_W + (laneNodes.length - 1) * NODE_GAP_X;
    const laneW = laneContentW + LANE_PADDING_X * 2;
    const laneH = NODE_H + LANE_PADDING_Y * 2 + LANE_LABEL_H + NODE_GAP_Y;

    const laneRect: LayoutRect = {
      x: CANVAS_PAD,
      y: currentY,
      w: laneW,
      h: laneH,
    };
    laneRects.set(lane.id, laneRect);

    // Position nodes within lane
    let nodeX = CANVAS_PAD + LANE_PADDING_X;
    const nodeY = currentY + LANE_LABEL_H + LANE_PADDING_Y;

    for (const node of laneNodes) {
      nodePositions.set(node.id, {
        x: nodeX,
        y: nodeY,
        w: NODE_W,
        h: NODE_H,
      });
      nodeX += NODE_W + NODE_GAP_X;
    }

    const laneRight = CANVAS_PAD + laneW;
    if (laneRight > maxRight) maxRight = laneRight;

    currentY += laneH + LANE_GAP;
  }

  // Normalize lane widths to the widest
  const canvasWidth = maxRight + CANVAS_PAD;
  for (const [, rect] of laneRects) {
    rect.w = canvasWidth - CANVAS_PAD * 2;
  }

  const canvasHeight = currentY + CANVAS_PAD;

  return { nodePositions, laneRects, canvasWidth, canvasHeight };
}

/**
 * Recompute layout after a node expands/collapses.
 * `expandedHeights` maps node IDs to their extra detail height (0 if collapsed).
 */
export function recomputeLayout(
  graph: PipelineGraph,
  expandedHeights: Map<string, number>,
): LayoutResult {
  const nodePositions = new Map<string, LayoutRect>();
  const laneRects = new Map<LaneId, LayoutRect>();

  const sortedLanes = [...graph.lanes].sort((a, b) => a.order - b.order);

  let currentY = CANVAS_PAD;
  let maxRight = 0;

  for (const lane of sortedLanes) {
    const laneNodes = graph.nodes
      .filter((n) => n.lane === lane.id)
      .sort((a, b) => a.order - b.order);

    // Find tallest node in lane (including expanded content)
    let maxNodeH = NODE_H;
    for (const node of laneNodes) {
      const extra = expandedHeights.get(node.id) ?? 0;
      const h = NODE_H + extra;
      if (h > maxNodeH) maxNodeH = h;
    }

    const laneContentW = laneNodes.length * NODE_W + (laneNodes.length - 1) * NODE_GAP_X;
    const laneW = laneContentW + LANE_PADDING_X * 2;
    const laneH = maxNodeH + LANE_PADDING_Y * 2 + LANE_LABEL_H + NODE_GAP_Y;

    const laneRect: LayoutRect = {
      x: CANVAS_PAD,
      y: currentY,
      w: laneW,
      h: laneH,
    };
    laneRects.set(lane.id, laneRect);

    let nodeX = CANVAS_PAD + LANE_PADDING_X;
    const nodeY = currentY + LANE_LABEL_H + LANE_PADDING_Y;

    for (const node of laneNodes) {
      const extra = expandedHeights.get(node.id) ?? 0;
      nodePositions.set(node.id, {
        x: nodeX,
        y: nodeY,
        w: NODE_W,
        h: NODE_H + extra,
      });
      nodeX += NODE_W + NODE_GAP_X;
    }

    const laneRight = CANVAS_PAD + laneW;
    if (laneRight > maxRight) maxRight = laneRight;

    currentY += laneH + LANE_GAP;
  }

  const canvasWidth = maxRight + CANVAS_PAD;
  for (const [, rect] of laneRects) {
    rect.w = canvasWidth - CANVAS_PAD * 2;
  }

  const canvasHeight = currentY + CANVAS_PAD;

  return { nodePositions, laneRects, canvasWidth, canvasHeight };
}
