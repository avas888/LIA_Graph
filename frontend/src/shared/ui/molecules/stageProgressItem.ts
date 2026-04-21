import { createProgressDot, type ProgressDotStatus } from "@/shared/ui/atoms/progressDot";

export interface StageProgressItemOptions {
  name: string;
  label: string;
  status: ProgressDotStatus;
  counts?: Record<string, number> | null;
  startedAt?: string | number | null;
  finishedAt?: string | number | null;
  errorMessage?: string | null;
  className?: string;
}

const COUNT_KEY_ORDER = ["docs", "chunks", "edges", "embeddings_generated"];

function formatCounts(counts: Record<string, number> | null | undefined): string {
  if (!counts) return "";
  const pairs: string[] = [];
  for (const key of COUNT_KEY_ORDER) {
    if (counts[key] != null) pairs.push(`${key}: ${counts[key]}`);
    if (pairs.length >= 3) break;
  }
  return pairs.join(", ");
}

function parseTs(value: string | number | null | undefined): number | null {
  if (value == null) return null;
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function formatDuration(startedAt: string | number | null | undefined, finishedAt: string | number | null | undefined): string {
  const start = parseTs(startedAt);
  const end = parseTs(finishedAt);
  if (start == null || end == null || end < start) return "";
  const seconds = Math.round((end - start) / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;
  return remainder ? `${minutes}m ${remainder}s` : `${minutes}m`;
}

/**
 * Molecule: one row inside the stage-progress timeline. Composes a
 * `progressDot` atom with a label, optional counts, duration, and an
 * error message when the stage failed.
 */
export function createStageProgressItem(opts: StageProgressItemOptions): HTMLDivElement {
  const { name, label, status, counts, startedAt, finishedAt, errorMessage, className = "" } = opts;
  const row = document.createElement("div");
  row.className = [
    "lia-stage-progress-item",
    `lia-stage-progress-item--${status}`,
    className,
  ].filter(Boolean).join(" ");
  row.setAttribute("data-lia-component", "stage-progress-item");
  row.setAttribute("data-stage-name", name);

  row.appendChild(createProgressDot({ status, ariaLabel: label }));

  const labelEl = document.createElement("span");
  labelEl.className = "lia-stage-progress-item__label";
  labelEl.textContent = label;
  row.appendChild(labelEl);

  const countsText = formatCounts(counts);
  if (countsText) {
    const countsEl = document.createElement("span");
    countsEl.className = "lia-stage-progress-item__counts";
    countsEl.textContent = countsText;
    row.appendChild(countsEl);
  }

  const duration = formatDuration(startedAt, finishedAt);
  if (duration) {
    const durEl = document.createElement("span");
    durEl.className = "lia-stage-progress-item__duration";
    durEl.textContent = duration;
    row.appendChild(durEl);
  }

  if (status === "failed" && errorMessage) {
    const err = document.createElement("p");
    err.className = "lia-stage-progress-item__error";
    err.textContent = errorMessage;
    err.setAttribute("role", "alert");
    row.appendChild(err);
  }

  return row;
}
