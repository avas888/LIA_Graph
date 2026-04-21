export type MetricValueSize = "sm" | "md" | "lg";

export interface MetricValueOptions {
  value: string | number;
  unit?: string;
  size?: MetricValueSize;
  className?: string;
}

export function createMetricValue(opts: MetricValueOptions): HTMLSpanElement {
  const { value, unit, size = "md", className = "" } = opts;
  const root = document.createElement("span");
  root.className = ["lia-metric-value", `lia-metric-value--${size}`, className]
    .filter(Boolean)
    .join(" ");
  root.setAttribute("data-lia-component", "metric-value");

  const number = document.createElement("span");
  number.className = "lia-metric-value__number";
  number.textContent = typeof value === "number" ? value.toLocaleString("es-CO") : String(value);
  root.appendChild(number);

  if (unit) {
    const unitEl = document.createElement("span");
    unitEl.className = "lia-metric-value__unit";
    unitEl.textContent = unit;
    root.appendChild(unitEl);
  }

  return root;
}
