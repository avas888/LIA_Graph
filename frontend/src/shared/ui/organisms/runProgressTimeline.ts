import {
  createStageProgressItem,
  type StageProgressItemOptions,
} from "@/shared/ui/molecules/stageProgressItem";
import type { ProgressDotStatus } from "@/shared/ui/atoms/progressDot";

/**
 * Organism: vertical run-progress timeline.
 *
 * Renders the six canonical pipeline stages (coerce, audit, chunk, sink,
 * falkor, embeddings) using `stageProgressItem` molecules. Exposes an
 * imperative `update()` so the controller can refresh state in place as
 * progress poll responses arrive — no full re-render required.
 *
 * Connector lines between items are pure CSS (`::before` on each item);
 * no SVG, no inline styles, tokens-only.
 */

export interface ProgressStageState {
  status: ProgressDotStatus | string;
  started_at?: string | number | null;
  finished_at?: string | number | null;
  counts?: Record<string, number> | null;
  error?: string | null;
}

export interface ProgressResponse {
  ok?: boolean;
  job_id?: string;
  status?: string;
  stages?: Partial<Record<StageName, ProgressStageState>> | null;
}

export type StageName = "coerce" | "audit" | "chunk" | "sink" | "falkor" | "embeddings";

export interface RunProgressTimelineHandle {
  element: HTMLElement;
  update: (progress: ProgressResponse) => void;
}

const STAGES: Array<{ name: StageName; label: string }> = [
  { name: "coerce", label: "Coerce" },
  { name: "audit", label: "Audit" },
  { name: "chunk", label: "Chunk" },
  { name: "sink", label: "Sink" },
  { name: "falkor", label: "FalkorDB" },
  { name: "embeddings", label: "Embeddings" },
];

function normalizeStatus(raw: string | undefined | null): ProgressDotStatus {
  if (raw === "running" || raw === "done" || raw === "failed" || raw === "pending") {
    return raw;
  }
  return "pending";
}

function buildStageOptions(
  name: StageName,
  label: string,
  state: ProgressStageState | undefined,
): StageProgressItemOptions {
  return {
    name,
    label,
    status: normalizeStatus(state?.status),
    counts: state?.counts ?? null,
    startedAt: state?.started_at ?? null,
    finishedAt: state?.finished_at ?? null,
    errorMessage: state?.error ?? null,
  };
}

export function createRunProgressTimeline(): RunProgressTimelineHandle {
  const root = document.createElement("section");
  root.className = "lia-run-progress-timeline";
  root.setAttribute("data-lia-component", "run-progress-timeline");

  const header = document.createElement("header");
  header.className = "lia-run-progress-timeline__header";
  const title = document.createElement("h3");
  title.className = "lia-run-progress-timeline__title";
  title.textContent = "Progreso de la corrida";
  header.appendChild(title);
  root.appendChild(header);

  const list = document.createElement("div");
  list.className = "lia-run-progress-timeline__list";

  // Mount initial stages in pending state.
  const itemHosts = new Map<StageName, HTMLElement>();
  STAGES.forEach(({ name, label }) => {
    const host = document.createElement("div");
    host.className = "lia-run-progress-timeline__item";
    host.setAttribute("data-stage", name);
    host.appendChild(
      createStageProgressItem(buildStageOptions(name, label, undefined)),
    );
    list.appendChild(host);
    itemHosts.set(name, host);
  });
  root.appendChild(list);

  function update(progress: ProgressResponse): void {
    const stages = progress?.stages || {};
    STAGES.forEach(({ name, label }) => {
      const host = itemHosts.get(name);
      if (!host) return;
      const stageState = stages[name] || undefined;
      host.replaceChildren(
        createStageProgressItem(buildStageOptions(name, label, stageState)),
      );
    });
  }

  return { element: root, update };
}
