/**
 * Corpus health metric (molecule).
 *
 * Title + free-form primary + optional secondary, with a tone-driven
 * left-border accent. Composes with `corpusHealthCard` (organism) which
 * renders four of these for active generation / parity / embeddings /
 * last-delta.
 *
 * Free-form primary is the reason this isn't `metricCard.ts` — that
 * molecule wraps `metricValue` (a numeric atom). Here the primary line
 * is often a string label like "Alineada ✓" or "gen_active_rolling",
 * not a number with a unit.
 */

export type CorpusHealthMetricTone = "ok" | "warning" | "danger" | "neutral";

export interface CorpusHealthMetricViewModel {
  title: string;
  primary: string;
  secondary?: string;
  tone: CorpusHealthMetricTone;
}

export function createCorpusHealthMetric(
  vm: CorpusHealthMetricViewModel,
): HTMLElement {
  const card = document.createElement("article");
  card.className = `lia-corpus-health-metric lia-corpus-health-metric--${vm.tone}`;
  card.setAttribute("data-lia-component", "corpus-health-metric");
  card.setAttribute("data-tone", vm.tone);

  const titleEl = document.createElement("h4");
  titleEl.className = "lia-corpus-health-metric__title";
  titleEl.textContent = vm.title;

  const primaryEl = document.createElement("p");
  primaryEl.className = "lia-corpus-health-metric__primary";
  primaryEl.textContent = vm.primary;

  card.append(titleEl, primaryEl);

  if (vm.secondary && vm.secondary.trim()) {
    const secondaryEl = document.createElement("p");
    secondaryEl.className = "lia-corpus-health-metric__secondary";
    secondaryEl.textContent = vm.secondary;
    card.appendChild(secondaryEl);
  }
  return card;
}
