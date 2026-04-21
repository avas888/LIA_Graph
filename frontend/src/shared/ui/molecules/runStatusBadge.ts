import { createStatusDot, type StatusDotTone } from "@/shared/ui/atoms/statusDot";

export type RunStatus =
  | "active"
  | "superseded"
  | "running"
  | "queued"
  | "failed"
  | "pending";

const TONE_BY_STATUS: Record<RunStatus, StatusDotTone> = {
  active: "active",
  superseded: "idle",
  running: "running",
  queued: "running",
  failed: "error",
  pending: "warning",
};

const LABEL_BY_STATUS: Record<RunStatus, string> = {
  active: "Activa",
  superseded: "Reemplazada",
  running: "En curso",
  queued: "En cola",
  failed: "Falló",
  pending: "Pendiente",
};

export interface RunStatusBadgeOptions {
  status: RunStatus;
  className?: string;
}

export function createRunStatusBadge(opts: RunStatusBadgeOptions): HTMLSpanElement {
  const { status, className = "" } = opts;
  const root = document.createElement("span");
  root.className = ["lia-run-status", `lia-run-status--${status}`, className]
    .filter(Boolean)
    .join(" ");
  root.setAttribute("data-lia-component", "run-status");

  root.appendChild(
    createStatusDot({
      tone: TONE_BY_STATUS[status],
      pulse: status === "running" || status === "queued",
      ariaLabel: LABEL_BY_STATUS[status],
    }),
  );

  const label = document.createElement("span");
  label.className = "lia-run-status__label";
  label.textContent = LABEL_BY_STATUS[status];
  root.appendChild(label);

  return root;
}
