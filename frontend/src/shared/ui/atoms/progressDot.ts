export type ProgressDotStatus = "pending" | "running" | "done" | "failed";

export interface ProgressDotOptions {
  status: ProgressDotStatus;
  ariaLabel?: string;
  className?: string;
}

/**
 * Atom: visual progress indicator for a pipeline stage.
 *
 * Renders a `<span class="lia-progress-dot lia-progress-dot--{status}">`.
 * The `running` state receives an additional `lia-progress-dot--pulse`
 * class which the stylesheet binds to a keyframe animation.
 */
export function createProgressDot(opts: ProgressDotOptions): HTMLSpanElement {
  const { status, ariaLabel, className = "" } = opts;
  const root = document.createElement("span");
  const classes = [
    "lia-progress-dot",
    `lia-progress-dot--${status}`,
    status === "running" ? "lia-progress-dot--pulse" : "",
    className,
  ].filter(Boolean);
  root.className = classes.join(" ");
  root.setAttribute("data-lia-component", "progress-dot");
  root.setAttribute("role", "status");
  root.setAttribute("data-status", status);
  if (ariaLabel) {
    root.setAttribute("aria-label", ariaLabel);
  }
  return root;
}
