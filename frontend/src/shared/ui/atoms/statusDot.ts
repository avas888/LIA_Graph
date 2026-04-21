export type StatusDotTone = "active" | "idle" | "running" | "warning" | "error";

export interface StatusDotOptions {
  tone: StatusDotTone;
  pulse?: boolean;
  ariaLabel?: string;
  className?: string;
}

export function createStatusDot(opts: StatusDotOptions): HTMLSpanElement {
  const { tone, pulse = false, ariaLabel, className = "" } = opts;
  const root = document.createElement("span");
  root.className = [
    "lia-status-dot",
    `lia-status-dot--${tone}`,
    pulse ? "lia-status-dot--pulse" : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");
  root.setAttribute("data-lia-component", "status-dot");
  root.setAttribute("role", "status");
  if (ariaLabel) root.setAttribute("aria-label", ariaLabel);
  return root;
}
