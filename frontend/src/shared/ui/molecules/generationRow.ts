import { createRunStatusBadge, type RunStatus } from "@/shared/ui/molecules/runStatusBadge";

export interface GenerationRowViewModel {
  generationId: string;
  status: RunStatus;
  generatedAt: string;
  documents: number;
  chunks: number;
  topClass?: string;
  topClassCount?: number;
  // ingestfix-v2 Phase 7 — subtopic coverage micro-metric.
  subtopicCoverage?: {
    docsWithSubtopic: number;
    docsRequiringReview?: number;
  };
}

function formatDateShort(iso: string): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return "—";
    return d.toLocaleString("es-CO", {
      day: "numeric",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export function createGenerationRow(
  vm: GenerationRowViewModel,
  onClick?: (id: string) => void,
): HTMLDivElement {
  const root = document.createElement(onClick ? "button" : "div") as HTMLDivElement;
  root.className = "lia-generation-row";
  root.setAttribute("data-lia-component", "generation-row");
  if (onClick) {
    (root as unknown as HTMLButtonElement).type = "button";
    root.addEventListener("click", () => onClick(vm.generationId));
  }

  const idCell = document.createElement("span");
  idCell.className = "lia-generation-row__id";
  idCell.textContent = vm.generationId;
  root.appendChild(idCell);

  root.appendChild(createRunStatusBadge({ status: vm.status }));

  const dateCell = document.createElement("span");
  dateCell.className = "lia-generation-row__date";
  dateCell.textContent = formatDateShort(vm.generatedAt);
  root.appendChild(dateCell);

  const docsCell = document.createElement("span");
  docsCell.className = "lia-generation-row__count";
  docsCell.textContent = `${vm.documents.toLocaleString("es-CO")} docs`;
  root.appendChild(docsCell);

  const chunksCell = document.createElement("span");
  chunksCell.className = "lia-generation-row__count lia-generation-row__count--muted";
  chunksCell.textContent = `${vm.chunks.toLocaleString("es-CO")} chunks`;
  root.appendChild(chunksCell);

  if (vm.topClass && vm.topClassCount) {
    const familyCell = document.createElement("span");
    familyCell.className = "lia-generation-row__family";
    familyCell.textContent = `${vm.topClass}: ${vm.topClassCount.toLocaleString("es-CO")}`;
    root.appendChild(familyCell);
  }

  if (vm.subtopicCoverage) {
    const coverage = vm.subtopicCoverage;
    const denominator = vm.documents > 0 ? vm.documents : 1;
    const pct = Math.round((coverage.docsWithSubtopic / denominator) * 100);
    const subtopicCell = document.createElement("span");
    subtopicCell.className = "lia-generation-row__subtopic";
    subtopicCell.setAttribute("data-lia-component", "generation-row-subtopic");
    const reviewSuffix =
      coverage.docsRequiringReview && coverage.docsRequiringReview > 0
        ? ` (${coverage.docsRequiringReview} por revisar)`
        : "";
    subtopicCell.textContent = `subtema: ${pct}%${reviewSuffix}`;
    root.appendChild(subtopicCell);
  }

  return root;
}
