import { createChip, type ChipOptions } from "@/shared/ui/atoms/chip";

export interface BadgeOptions extends ChipOptions {}

export function createBadge(options: BadgeOptions): HTMLSpanElement {
  return createChip({
    ...options,
    className: ["lia-badge", options.className || ""].filter(Boolean).join(" "),
    dataComponent: options.dataComponent || "badge",
    emphasis: options.emphasis || "solid",
  });
}
