export type ActorType = "curator" | "python" | "sql" | "llm" | "embedding";

export type NodeKind = "stage" | "store" | "model" | "config";

export type LaneId = "ingesta" | "parsing" | "almacenamiento" | "retrieval" | "surfaces" | "plataforma" | "mobile";

export interface PipelineNode {
  id: string;
  lane: LaneId;
  kind: NodeKind;
  title: string;
  summary: string;
  actors: ActorType[];
  metrics?: string[];
  detailHtml?: string;
  /** Order within lane (0-based). Used by layout. */
  order: number;
}

export interface PipelineEdge {
  from: string;
  to: string;
  label?: string;
  /** Cross-lane edges are rendered dashed. Auto-detected from node lane. */
  crossLane?: boolean;
}

export interface PipelineLane {
  id: LaneId;
  label: string;
  color: string;
  order: number;
}

export interface PipelineGraph {
  nodes: PipelineNode[];
  edges: PipelineEdge[];
  lanes: PipelineLane[];
}

export interface LayoutRect {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface LayoutResult {
  nodePositions: Map<string, LayoutRect>;
  laneRects: Map<LaneId, LayoutRect>;
  canvasWidth: number;
  canvasHeight: number;
}
