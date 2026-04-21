import { createChip, type LiaChipTone } from "@/shared/ui/atoms/chip";

export interface SubtopicChipOptions {
  subtopicKey: string;
  label?: string | null;
  confidence?: number | null;
  requiresReview?: boolean;
  isNew?: boolean;
  className?: string;
}

/**
 * Atom: compact chip representing a curated subtopic verdict on a
 * document. Wraps the generic `chip` atom with subtopic-specific tone
 * mapping:
 *   - confirmed + high confidence → brand
 *   - new subtopic (pending curator promotion) → info
 *   - requires_subtopic_review → warning
 */
export function createSubtopicChip(
  opts: SubtopicChipOptions,
): HTMLSpanElement {
  const {
    subtopicKey,
    label,
    confidence,
    requiresReview,
    isNew,
    className = "",
  } = opts;

  let tone: LiaChipTone = "brand";
  if (requiresReview) tone = "warning";
  else if (isNew) tone = "info";

  const body = label && label.trim() ? label : subtopicKey;
  const text = confidence != null && !Number.isNaN(confidence)
    ? `${body} · ${Math.round((confidence <= 1 ? confidence * 100 : confidence))}%`
    : body;

  const chip = createChip({
    label: text,
    tone,
    emphasis: "soft",
    className: ["lia-subtopic-chip", className].filter(Boolean).join(" "),
    dataComponent: "subtopic-chip",
  });
  chip.setAttribute("data-subtopic-key", subtopicKey);
  if (requiresReview) chip.setAttribute("data-subtopic-review", "true");
  if (isNew) chip.setAttribute("data-subtopic-new", "true");
  return chip;
}
