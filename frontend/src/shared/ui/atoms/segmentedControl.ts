/**
 * Atom: segmented control (single-select toggle).
 *
 * Renders a row of mutually-exclusive buttons. Exactly one is marked
 * ``aria-pressed="true"``. Used for swapping between peer workflows when
 * only one should be interactive at a time.
 */

export interface SegmentOption {
  value: string;
  label: string;
  /** Optional short hint rendered under the label on wider viewports. */
  hint?: string;
}

export interface SegmentedControlOptions {
  options: SegmentOption[];
  value: string;
  onChange: (nextValue: string) => void;
  ariaLabel?: string;
  className?: string;
}

export interface SegmentedControlHandle {
  element: HTMLElement;
  setValue: (next: string) => void;
  value: () => string;
}

export function createSegmentedControl(
  opts: SegmentedControlOptions,
): SegmentedControlHandle {
  const root = document.createElement("div");
  root.className = ["lia-segmented", opts.className || ""].filter(Boolean).join(" ");
  root.setAttribute("data-lia-component", "segmented-control");
  root.setAttribute("role", "tablist");
  if (opts.ariaLabel) root.setAttribute("aria-label", opts.ariaLabel);

  let current = opts.value;
  const buttons: HTMLButtonElement[] = [];

  for (const option of opts.options) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "lia-segmented__option";
    button.setAttribute("role", "tab");
    button.setAttribute("data-value", option.value);
    button.setAttribute("aria-pressed", option.value === current ? "true" : "false");

    const label = document.createElement("span");
    label.className = "lia-segmented__label";
    label.textContent = option.label;
    button.appendChild(label);

    if (option.hint) {
      const hint = document.createElement("span");
      hint.className = "lia-segmented__hint";
      hint.textContent = option.hint;
      button.appendChild(hint);
    }

    button.addEventListener("click", () => {
      if (current === option.value) return;
      setValue(option.value);
      opts.onChange(option.value);
    });

    buttons.push(button);
    root.appendChild(button);
  }

  function setValue(next: string): void {
    current = next;
    for (const b of buttons) {
      const value = b.getAttribute("data-value") || "";
      b.setAttribute("aria-pressed", value === current ? "true" : "false");
    }
  }

  return {
    element: root,
    setValue,
    value: () => current,
  };
}
