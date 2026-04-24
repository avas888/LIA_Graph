/**
 * Additive-corpus-v1 preview banner (Phase 8).
 *
 * Renders the /api/ingest/additive/preview response: four per-bucket cards
 * (added / modified / removed / unchanged) + a monospace footer naming
 * ``delta_id`` and ``baseline_generation_id``. Empty deltas ("sin cambios")
 * are rendered as a single quiet card instead of four empty cards.
 */

import { createChip, type LiaChipTone } from "@/shared/ui/atoms/chip";

export interface AdditiveDeltaBucketChip {
  label: string;
}

export interface AdditiveDeltaBannerViewModel {
  deltaId: string;
  baselineGenerationId: string;
  counts: {
    added: number;
    modified: number;
    removed: number;
    unchanged: number;
  };
  samples?: {
    added?: AdditiveDeltaBucketChip[];
    modified?: AdditiveDeltaBucketChip[];
    removed?: AdditiveDeltaBucketChip[];
  };
  isEmpty: boolean;
}

interface BucketCardSpec {
  key: "added" | "modified" | "removed" | "unchanged";
  title: string;
  tone: LiaChipTone;
  count: number;
  samples: AdditiveDeltaBucketChip[];
  description: string;
}

const SAMPLE_LIMIT = 3;

function renderBucketCard(spec: BucketCardSpec): HTMLElement {
  const card = document.createElement("article");
  card.className = `lia-adelta-bucket lia-adelta-bucket--${spec.tone}`;
  card.setAttribute("data-lia-component", "additive-delta-bucket");
  card.setAttribute("data-bucket", spec.key);

  const header = document.createElement("header");
  header.className = "lia-adelta-bucket__header";

  const title = document.createElement("h4");
  title.className = "lia-adelta-bucket__title";
  title.textContent = spec.title;

  const count = document.createElement("span");
  count.className = "lia-adelta-bucket__count";
  count.textContent = String(spec.count);

  header.append(title, count);

  const body = document.createElement("p");
  body.className = "lia-adelta-bucket__body";
  body.textContent = spec.description;

  const chipRow = document.createElement("div");
  chipRow.className = "lia-adelta-bucket__chips";
  const shown = spec.samples.slice(0, SAMPLE_LIMIT);
  for (const chip of shown) {
    chipRow.appendChild(createChip({ label: chip.label, tone: spec.tone }));
  }
  if (spec.samples.length > SAMPLE_LIMIT) {
    chipRow.appendChild(
      createChip({
        label: `+${spec.samples.length - SAMPLE_LIMIT} más`,
        tone: "neutral",
      }),
    );
  }

  card.append(header, body, chipRow);
  return card;
}

export function createAdditiveDeltaBanner(
  vm: AdditiveDeltaBannerViewModel,
): HTMLElement {
  const root = document.createElement("section");
  root.className = "lia-adelta-banner";
  root.setAttribute("data-lia-component", "additive-delta-banner");
  root.setAttribute("aria-label", "Resumen del delta aditivo");

  if (vm.isEmpty) {
    const empty = document.createElement("div");
    empty.className = "lia-adelta-banner__empty";

    const title = document.createElement("h3");
    title.className = "lia-adelta-banner__empty-title";
    title.textContent = "Sin cambios detectados";

    const body = document.createElement("p");
    body.className = "lia-adelta-banner__empty-body";
    body.textContent =
      "La base ya coincide con el corpus en disco. No hay nada que aplicar.";

    empty.append(title, body);
    root.appendChild(empty);
  } else {
    const specs: BucketCardSpec[] = [
      {
        key: "added",
        title: "Agregados",
        tone: "success",
        count: vm.counts.added,
        samples: vm.samples?.added ?? [],
        description: "Documentos nuevos que entrarán al corpus.",
      },
      {
        key: "modified",
        title: "Modificados",
        tone: "warning",
        count: vm.counts.modified,
        samples: vm.samples?.modified ?? [],
        description: "Documentos con cambios de contenido o clasificación.",
      },
      {
        key: "removed",
        title: "Retirados",
        tone: "error",
        count: vm.counts.removed,
        samples: vm.samples?.removed ?? [],
        description: "Documentos que ya no existen en disco.",
      },
      {
        key: "unchanged",
        title: "Sin cambios",
        tone: "neutral",
        count: vm.counts.unchanged,
        samples: [],
        description: "Documentos que no requieren re-procesamiento.",
      },
    ];
    const grid = document.createElement("div");
    grid.className = "lia-adelta-banner__grid";
    for (const spec of specs) grid.appendChild(renderBucketCard(spec));
    root.appendChild(grid);
  }

  const footer = document.createElement("footer");
  footer.className = "lia-adelta-banner__footer";

  const deltaIdEl = document.createElement("code");
  deltaIdEl.className = "lia-adelta-banner__delta-id";
  deltaIdEl.textContent = `delta_id=${vm.deltaId}`;

  const baselineEl = document.createElement("code");
  baselineEl.className = "lia-adelta-banner__baseline";
  baselineEl.textContent = `baseline=${vm.baselineGenerationId}`;

  footer.append(deltaIdEl, baselineEl);
  root.appendChild(footer);

  return root;
}
