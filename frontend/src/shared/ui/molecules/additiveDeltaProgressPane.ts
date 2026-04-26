/**
 * Additive-corpus-v1 progress pane (Phase 8).
 *
 * Live progress rendering for a running job. Binds to SSE /events via the
 * update() handle and renders: per-stage dot row, progress percentage,
 * heartbeat relative-time, and a reconnect/polling-fallback indicator.
 */

import { createProgressDot, type ProgressDotStatus } from "@/shared/ui/atoms/progressDot";
import { createChip, type LiaChipTone } from "@/shared/ui/atoms/chip";
import type { AdditiveDeltaSseHealthInfo } from "@/features/ingest/additiveDeltaSse";

export type AdditiveDeltaStage =
  | "queued"
  | "parsing"
  | "supabase"
  | "falkor"
  | "finalize"
  | "completed"
  | "failed"
  | "cancelled";

const STAGE_ORDER: AdditiveDeltaStage[] = [
  "queued",
  "parsing",
  "supabase",
  "falkor",
  "finalize",
];

const STAGE_LABELS: Record<AdditiveDeltaStage, string> = {
  queued: "En cola",
  parsing: "Clasificando",
  supabase: "Supabase",
  falkor: "FalkorDB",
  finalize: "Finalizando",
  completed: "Completado",
  failed: "Falló",
  cancelled: "Cancelado",
};

export type AdditiveDeltaSseStatus =
  | "connecting"
  | "connected"
  | "reconnecting"
  | "polling"
  | "closed";

export interface AdditiveDeltaProgressViewModel {
  jobId: string;
  stage: AdditiveDeltaStage;
  progressPct: number;
  lastHeartbeatAt?: string | null;
  sseStatus: AdditiveDeltaSseStatus;
  cancelRequested: boolean;
  /** Set when the polling layer crosses its failure / stall threshold.
   * Null when the channel is healthy. Renders as a colored chip in the
   * footer so operators stop staring at silent spinners. */
  healthIssue?: AdditiveDeltaSseHealthInfo | null;
  /** Live one-line description of what the worker is doing right now
   * (per-doc classifier event, parity check passing, etc.). Updated by
   * the controller from `onProgressEvent` callbacks. Null = no live
   * line, just the static stage dots. */
  liveActivity?: string | null;
}

export interface AdditiveDeltaProgressHandle {
  element: HTMLElement;
  update: (vm: AdditiveDeltaProgressViewModel) => void;
  /** Stop the elapsed-time ticker. Called when the job transitions to a
   * terminal stage or the pane is about to be replaced. */
  destroy: () => void;
}

function stageStatus(
  current: AdditiveDeltaStage,
  target: AdditiveDeltaStage,
): ProgressDotStatus {
  if (current === "failed" || current === "cancelled") {
    const idxCur = STAGE_ORDER.indexOf(
      current === "failed" || current === "cancelled"
        ? "finalize"
        : (current as AdditiveDeltaStage),
    );
    const idxTgt = STAGE_ORDER.indexOf(target);
    if (idxTgt <= idxCur) return "failed";
    return "pending";
  }
  if (current === "completed") return "done";
  const idxCur = STAGE_ORDER.indexOf(current);
  const idxTgt = STAGE_ORDER.indexOf(target);
  if (idxTgt < idxCur) return "done";
  if (idxTgt === idxCur) return "running";
  return "pending";
}

function relativeTime(isoTimestamp: string | null | undefined): string {
  if (!isoTimestamp) return "sin heartbeat";
  const parsed = Date.parse(isoTimestamp);
  if (Number.isNaN(parsed)) return "sin heartbeat";
  const diffSec = Math.max(0, Math.floor((Date.now() - parsed) / 1000));
  if (diffSec < 5) return "hace un instante";
  if (diffSec < 60) return `hace ${diffSec}s`;
  const mins = Math.floor(diffSec / 60);
  if (mins < 60) return `hace ${mins} min`;
  const hrs = Math.floor(mins / 60);
  return `hace ${hrs} h`;
}

function sseStatusLabel(status: AdditiveDeltaSseStatus): string {
  switch (status) {
    case "connecting":
      return "Conectando…";
    case "connected":
      return "En vivo";
    case "reconnecting":
      return "Reconectando…";
    case "polling":
      return "Sondeando (fallback)";
    case "closed":
      return "Desconectado";
  }
}

export function createAdditiveDeltaProgressPane(
  initial: AdditiveDeltaProgressViewModel,
): AdditiveDeltaProgressHandle {
  const root = document.createElement("section");
  root.className = "lia-adelta-progress";
  root.setAttribute("data-lia-component", "additive-delta-progress");
  root.setAttribute("aria-live", "polite");

  const header = document.createElement("header");
  header.className = "lia-adelta-progress__header";
  const titleWrap = document.createElement("div");
  titleWrap.className = "lia-adelta-progress__title-wrap";
  const title = document.createElement("h3");
  title.className = "lia-adelta-progress__title";
  title.textContent = "Aplicando delta";
  const elapsed = document.createElement("span");
  elapsed.className = "lia-adelta-progress__elapsed";
  elapsed.textContent = "iniciado hace 00:00";
  titleWrap.append(title, elapsed);
  const jobBadge = document.createElement("code");
  jobBadge.className = "lia-adelta-progress__job";
  const sseBadge = document.createElement("span");
  sseBadge.className = "lia-adelta-progress__sse";
  header.append(titleWrap, jobBadge, sseBadge);

  const stageRow = document.createElement("ol");
  stageRow.className = "lia-adelta-progress__stages";
  const stageNodes: Record<AdditiveDeltaStage, HTMLLIElement> = {
    queued: document.createElement("li"),
    parsing: document.createElement("li"),
    supabase: document.createElement("li"),
    falkor: document.createElement("li"),
    finalize: document.createElement("li"),
    completed: document.createElement("li"),
    failed: document.createElement("li"),
    cancelled: document.createElement("li"),
  };
  const stageDots: Partial<Record<AdditiveDeltaStage, HTMLSpanElement>> = {};
  for (const stage of STAGE_ORDER) {
    const li = stageNodes[stage];
    li.className = "lia-adelta-progress__stage";
    const dot = createProgressDot({
      status: "pending",
      ariaLabel: STAGE_LABELS[stage],
    });
    stageDots[stage] = dot;
    const label = document.createElement("span");
    label.className = "lia-adelta-progress__stage-label";
    label.textContent = STAGE_LABELS[stage];
    li.append(dot, label);
    stageRow.appendChild(li);
  }

  const progressBar = document.createElement("div");
  progressBar.className = "lia-adelta-progress__bar";
  progressBar.setAttribute("role", "progressbar");
  progressBar.setAttribute("aria-valuemin", "0");
  progressBar.setAttribute("aria-valuemax", "100");
  const progressFill = document.createElement("div");
  progressFill.className = "lia-adelta-progress__bar-fill";
  progressBar.appendChild(progressFill);

  const liveActivityEl = document.createElement("p");
  liveActivityEl.className = "lia-adelta-progress__live-activity";
  liveActivityEl.setAttribute("aria-live", "polite");
  liveActivityEl.hidden = true;

  const footer = document.createElement("footer");
  footer.className = "lia-adelta-progress__footer";
  const heartbeatEl = document.createElement("span");
  heartbeatEl.className = "lia-adelta-progress__heartbeat";
  const cancelNote = document.createElement("span");
  cancelNote.className = "lia-adelta-progress__cancel-note";
  // Slot for the health chip — atom-based, swapped on every health
  // update so we don't accumulate stale class state. Hidden when there's
  // no issue.
  const healthChipSlot = document.createElement("span");
  healthChipSlot.className = "lia-adelta-progress__health-slot";
  healthChipSlot.hidden = true;
  footer.append(heartbeatEl, cancelNote, healthChipSlot);

  root.append(header, stageRow, progressBar, liveActivityEl, footer);

  function update(vm: AdditiveDeltaProgressViewModel): void {
    jobBadge.textContent = vm.jobId ? `job_id=${vm.jobId}` : "";
    sseBadge.textContent = sseStatusLabel(vm.sseStatus);
    sseBadge.dataset.status = vm.sseStatus;
    for (const stage of STAGE_ORDER) {
      const dot = stageDots[stage];
      if (!dot) continue;
      const status = stageStatus(vm.stage, stage);
      dot.className = `lia-progress-dot lia-progress-dot--${status}` +
        (status === "running" ? " lia-progress-dot--pulse" : "");
      dot.setAttribute("data-status", status);
    }
    const pct = Math.max(0, Math.min(100, Math.round(vm.progressPct)));
    progressFill.style.width = `${pct}%`;
    progressBar.setAttribute("aria-valuenow", String(pct));
    heartbeatEl.textContent = `Último latido del servidor: ${relativeTime(vm.lastHeartbeatAt)}`;
    cancelNote.textContent = vm.cancelRequested
      ? "Cancelación solicitada — finalizará en el próximo punto seguro."
      : "";
    const live = (vm.liveActivity ?? "").trim();
    if (live) {
      liveActivityEl.hidden = false;
      liveActivityEl.textContent = live;
    } else {
      liveActivityEl.hidden = true;
      liveActivityEl.textContent = "";
    }
    if (vm.healthIssue) {
      const tone: LiaChipTone =
        vm.healthIssue.kind === "stall" ? "warning" : "error";
      const prefix = vm.healthIssue.kind === "stall" ? "⚠" : "⛔";
      const attempts = vm.healthIssue.attemptsSinceLastSuccess;
      const tail =
        vm.healthIssue.kind !== "stall" && attempts > 0
          ? ` (${attempts} intentos fallidos consecutivos)`
          : "";
      const chip = createChip({
        label: `${prefix} ${vm.healthIssue.message}${tail}`,
        tone,
        emphasis: "soft",
        dataComponent: "additive-delta-health-chip",
        className: "lia-adelta-progress__health-chip",
      });
      // Pin the kind via dataset so test selectors can target by issue type.
      chip.dataset.kind = vm.healthIssue.kind;
      healthChipSlot.replaceChildren(chip);
      healthChipSlot.hidden = false;
    } else {
      healthChipSlot.replaceChildren();
      healthChipSlot.hidden = true;
    }
  }

  // Wall-clock "alive" indicator. Independent of server events — ticks
  // every second so the operator always sees SOMETHING moving, even
  // before the first /status poll or SSE event lands.
  const startedAt = Date.now();
  function renderElapsed(): void {
    const secs = Math.max(0, Math.floor((Date.now() - startedAt) / 1000));
    const mm = String(Math.floor(secs / 60)).padStart(2, "0");
    const ss = String(secs % 60).padStart(2, "0");
    elapsed.textContent = `iniciado hace ${mm}:${ss}`;
  }
  renderElapsed();
  const tickHandle: ReturnType<typeof setInterval> = setInterval(renderElapsed, 1000);

  update(initial);
  return {
    element: root,
    update,
    destroy: () => clearInterval(tickHandle),
  };
}
