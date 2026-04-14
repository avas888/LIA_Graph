export type LiaChipTone =
  | "neutral"
  | "brand"
  | "success"
  | "warning"
  | "error"
  | "info";

export type LiaChipEmphasis = "soft" | "solid";

export interface ChipOptions {
  className?: string;
  dataComponent?: string;
  emphasis?: LiaChipEmphasis;
  label: string;
  tone?: LiaChipTone;
}

function applyChipClasses(
  element: HTMLElement,
  {
    className = "",
    dataComponent = "chip",
    emphasis = "soft",
    label,
    tone = "neutral",
  }: ChipOptions,
): void {
  element.className = [
    "lia-chip",
    `lia-chip--${tone}`,
    `lia-chip--${emphasis}`,
    className,
  ]
    .filter(Boolean)
    .join(" ");
  element.setAttribute("data-lia-component", dataComponent);
  element.textContent = label;
}

export function createChip(options: ChipOptions): HTMLSpanElement {
  const chip = document.createElement("span");
  applyChipClasses(chip, options);
  return chip;
}

export function createButtonChip(
  options: ChipOptions & { onClick?: ((event: MouseEvent) => void) | null },
): HTMLButtonElement {
  const button = document.createElement("button");
  button.type = "button";
  applyChipClasses(button, {
    ...options,
    dataComponent: options.dataComponent || "chip-button",
  });
  button.classList.add("lia-chip-button");
  if (options.onClick) {
    button.addEventListener("click", options.onClick);
  }
  return button;
}
