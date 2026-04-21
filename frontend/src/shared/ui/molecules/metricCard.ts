import { createMetricValue, type MetricValueOptions } from "@/shared/ui/atoms/metricValue";

export interface MetricCardOptions {
  label: string;
  value: string | number;
  unit?: string;
  hint?: string;
  size?: MetricValueOptions["size"];
  tone?: "neutral" | "success" | "warning" | "error";
  className?: string;
}

export function createMetricCard(opts: MetricCardOptions): HTMLDivElement {
  const { label, value, unit, hint, size = "lg", tone = "neutral", className = "" } = opts;
  const root = document.createElement("div");
  root.className = ["lia-metric-card", `lia-metric-card--${tone}`, className]
    .filter(Boolean)
    .join(" ");
  root.setAttribute("data-lia-component", "metric-card");

  const labelEl = document.createElement("p");
  labelEl.className = "lia-metric-card__label";
  labelEl.textContent = label;
  root.appendChild(labelEl);

  root.appendChild(createMetricValue({ value, unit, size }));

  if (hint) {
    const hintEl = document.createElement("p");
    hintEl.className = "lia-metric-card__hint";
    hintEl.textContent = hint;
    root.appendChild(hintEl);
  }

  return root;
}
