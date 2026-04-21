export interface FileChipOptions {
  filename: string;
  mime?: string;
  bytes: number;
  onRemove?: (() => void) | null;
  className?: string;
}

const UNITS = ["B", "KB", "MB", "GB", "TB"];

/**
 * Formats a byte count into a human-readable string. Values below 1024 are
 * rendered in bytes (no decimal), larger values are rendered with a single
 * decimal when fractional, integer otherwise.
 */
export function formatBytes(n: number): string {
  if (!Number.isFinite(n) || n <= 0) return "0 B";
  let idx = 0;
  let value = n;
  while (value >= 1024 && idx < UNITS.length - 1) {
    value /= 1024;
    idx += 1;
  }
  const rounded = idx === 0 ? Math.round(value) : Math.round(value * 10) / 10;
  const asText = Number.isInteger(rounded) ? `${rounded}` : rounded.toFixed(1);
  return `${asText} ${UNITS[idx]}`;
}

function iconForFilename(filename: string): string {
  const lower = filename.toLowerCase();
  if (lower.endsWith(".pdf")) return "\u{1F4D5}"; // red notebook
  if (lower.endsWith(".docx") || lower.endsWith(".doc")) return "\u{1F4D8}"; // blue notebook
  if (lower.endsWith(".md")) return "\u{1F4C4}"; // page with curl
  if (lower.endsWith(".txt")) return "\u{1F4C3}"; // page scroll
  return "\u{1F4C4}";
}

/**
 * Atom: file pill. Renders a truncated filename with a size suffix, a
 * lightweight text-based type token, and an optional `x` remove button.
 */
export function createFileChip(opts: FileChipOptions): HTMLSpanElement {
  const { filename, bytes, onRemove, className = "" } = opts;
  const chip = document.createElement("span");
  chip.className = ["lia-file-chip", className].filter(Boolean).join(" ");
  chip.setAttribute("data-lia-component", "file-chip");
  chip.title = `${filename} - ${formatBytes(bytes)}`;

  const icon = document.createElement("span");
  icon.className = "lia-file-chip__icon";
  icon.setAttribute("aria-hidden", "true");
  icon.textContent = iconForFilename(filename);
  chip.appendChild(icon);

  const name = document.createElement("span");
  name.className = "lia-file-chip__name";
  name.textContent = filename;
  chip.appendChild(name);

  const size = document.createElement("span");
  size.className = "lia-file-chip__size";
  size.textContent = formatBytes(bytes);
  chip.appendChild(size);

  if (onRemove) {
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "lia-file-chip__remove";
    remove.setAttribute("aria-label", `Quitar ${filename}`);
    remove.textContent = "x";
    remove.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      onRemove();
    });
    chip.appendChild(remove);
  }

  return chip;
}
