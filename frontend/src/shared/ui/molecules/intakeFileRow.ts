import { createBadge } from "@/shared/ui/atoms/badge";
import { createChip } from "@/shared/ui/atoms/chip";
import { createFileChip } from "@/shared/ui/atoms/fileChip";
import { createSubtopicChip } from "@/shared/ui/atoms/subtopicChip";

export interface IntakeFileRowOptions {
  filename: string;
  mime?: string;
  bytes: number;
  detectedTopic?: string | null;
  topicLabel?: string | null;
  combinedConfidence?: number | null;
  requiresReview?: boolean;
  coercionMethod?: string | null;
  subtopicKey?: string | null;
  subtopicLabel?: string | null;
  subtopicConfidence?: number | null;
  subtopicIsNew?: boolean;
  requiresSubtopicReview?: boolean;
  onRemove?: (() => void) | null;
  className?: string;
}

function formatConfidence(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "-";
  const pct = value <= 1 ? value * 100 : value;
  return `${Math.round(pct)}%`;
}

function confidenceTone(value: number | null | undefined): "success" | "warning" | "error" | "neutral" {
  if (value == null || Number.isNaN(value)) return "neutral";
  const pct = value <= 1 ? value * 100 : value;
  if (pct >= 80) return "success";
  if (pct >= 50) return "warning";
  return "error";
}

/**
 * Molecule: compact horizontal row showing a file chip + topic badge +
 * confidence pill + optional "requires review" warning marker, separated
 * from surrounding rows by a muted bottom divider.
 */
export function createIntakeFileRow(opts: IntakeFileRowOptions): HTMLDivElement {
  const {
    filename,
    bytes,
    mime,
    detectedTopic,
    topicLabel,
    combinedConfidence,
    requiresReview,
    coercionMethod,
    subtopicKey,
    subtopicLabel,
    subtopicConfidence,
    subtopicIsNew,
    requiresSubtopicReview,
    onRemove,
    className = "",
  } = opts;

  const row = document.createElement("div");
  row.className = ["lia-intake-file-row", className].filter(Boolean).join(" ");
  row.setAttribute("data-lia-component", "intake-file-row");

  const fileCell = document.createElement("span");
  fileCell.className = "lia-intake-file-row__file";
  fileCell.appendChild(createFileChip({ filename, bytes, mime, onRemove }));
  row.appendChild(fileCell);

  const metaCell = document.createElement("span");
  metaCell.className = "lia-intake-file-row__meta";

  if (topicLabel || detectedTopic) {
    const badge = createBadge({
      label: topicLabel || detectedTopic || "sin tópico",
      tone: "info",
      emphasis: "soft",
      className: "lia-intake-file-row__topic",
    });
    if (detectedTopic) badge.setAttribute("data-topic", detectedTopic);
    metaCell.appendChild(badge);
  }

  if (combinedConfidence != null) {
    const conf = createChip({
      label: formatConfidence(combinedConfidence),
      tone: confidenceTone(combinedConfidence),
      emphasis: "soft",
      className: "lia-intake-file-row__confidence",
    });
    metaCell.appendChild(conf);
  }

  if (requiresReview) {
    const warn = createChip({
      label: "requiere revisión",
      tone: "warning",
      emphasis: "solid",
      className: "lia-intake-file-row__review",
    });
    warn.setAttribute("role", "status");
    metaCell.appendChild(warn);
  }

  if (subtopicKey) {
    metaCell.appendChild(
      createSubtopicChip({
        subtopicKey,
        label: subtopicLabel || null,
        confidence: subtopicConfidence ?? null,
        isNew: subtopicIsNew,
        requiresReview: requiresSubtopicReview,
        className: "lia-intake-file-row__subtopic",
      }),
    );
  } else if (subtopicIsNew && opts.subtopicKey !== undefined) {
    // New subtopic proposed but not yet promoted → show a "nuevo subtema"
    // chip so the curator knows what to act on.
    metaCell.appendChild(
      createSubtopicChip({
        subtopicKey: "(nuevo)",
        label: subtopicLabel || "subtema propuesto",
        isNew: true,
        className: "lia-intake-file-row__subtopic",
      }),
    );
  }
  if (requiresSubtopicReview && !subtopicKey) {
    const reviewChip = createChip({
      label: "subtema pendiente",
      tone: "warning",
      emphasis: "soft",
      className: "lia-intake-file-row__subtopic-review",
    });
    reviewChip.setAttribute("data-subtopic-review", "true");
    metaCell.appendChild(reviewChip);
  }

  if (coercionMethod) {
    const coerce = document.createElement("span");
    coerce.className = "lia-intake-file-row__coercion";
    coerce.textContent = coercionMethod;
    metaCell.appendChild(coerce);
  }

  row.appendChild(metaCell);
  return row;
}
