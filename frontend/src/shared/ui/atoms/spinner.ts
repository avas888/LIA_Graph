/**
 * Atom: spinner.
 *
 * Minimal circular loading indicator. Size defaults to 1em so it inherits
 * the parent text-size; pass `size="sm" | "md" | "lg"` for fixed tiers.
 * Color inherits from `currentColor` — the spinning ring uses
 * ``border-top-color: currentColor`` so it matches surrounding text.
 */

export type SpinnerSize = "sm" | "md" | "lg" | "inline";

export interface SpinnerOptions {
  size?: SpinnerSize;
  ariaLabel?: string;
  className?: string;
}

export function createSpinner(opts: SpinnerOptions = {}): HTMLSpanElement {
  const { size = "inline", ariaLabel, className = "" } = opts;
  const root = document.createElement("span");
  root.className = [
    "lia-spinner",
    `lia-spinner--${size}`,
    className,
  ]
    .filter(Boolean)
    .join(" ");
  root.setAttribute("data-lia-component", "spinner");
  root.setAttribute("role", "status");
  if (ariaLabel) {
    root.setAttribute("aria-label", ariaLabel);
  } else {
    root.setAttribute("aria-hidden", "true");
  }
  return root;
}
