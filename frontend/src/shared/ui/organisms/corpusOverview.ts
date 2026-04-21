import { createMetricCard } from "@/shared/ui/molecules/metricCard";

export interface CorpusOverviewViewModel {
  documents: number;
  chunks: number;
  graphNodes: number;
  graphEdges: number;
  graphOk: boolean;
  auditScanned: number;
  auditIncluded: number;
  auditExcluded: number;
  auditPendingRevisions: number;
  activeGenerationId: string;
  activatedAt: string;
}

function formatRelativeAgo(iso: string): string {
  if (!iso) return "sin activar";
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return "—";
    const diffMs = Date.now() - d.getTime();
    const mins = Math.floor(diffMs / 60_000);
    if (mins < 1) return "hace instantes";
    if (mins < 60) return `hace ${mins} min`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `hace ${hours} h`;
    const days = Math.floor(hours / 24);
    return `hace ${days} d`;
  } catch {
    return "—";
  }
}

export function createCorpusOverview(vm: CorpusOverviewViewModel): HTMLElement {
  const root = document.createElement("section");
  root.className = "lia-corpus-overview";
  root.setAttribute("data-lia-component", "corpus-overview");

  const header = document.createElement("header");
  header.className = "lia-corpus-overview__header";

  const title = document.createElement("h2");
  title.className = "lia-corpus-overview__title";
  title.textContent = "Corpus activo";
  header.appendChild(title);

  const subtitle = document.createElement("p");
  subtitle.className = "lia-corpus-overview__subtitle";
  if (vm.activeGenerationId) {
    const code = document.createElement("code");
    code.textContent = vm.activeGenerationId;
    subtitle.appendChild(document.createTextNode("Generación "));
    subtitle.appendChild(code);
    subtitle.appendChild(
      document.createTextNode(` · activada ${formatRelativeAgo(vm.activatedAt)}`),
    );
  } else {
    subtitle.textContent = "Ninguna generación activa en Supabase.";
  }
  header.appendChild(subtitle);
  root.appendChild(header);

  const grid = document.createElement("div");
  grid.className = "lia-corpus-overview__grid";

  grid.appendChild(
    createMetricCard({
      label: "Documentos servidos",
      value: vm.documents,
      hint: vm.documents > 0 ? `${vm.chunks.toLocaleString("es-CO")} chunks indexados` : "—",
    }),
  );

  grid.appendChild(
    createMetricCard({
      label: "Grafo de normativa",
      value: vm.graphNodes,
      unit: "nodos",
      hint: `${vm.graphEdges.toLocaleString("es-CO")} relaciones tipadas`,
      tone: vm.graphOk ? "success" : "warning",
    }),
  );

  grid.appendChild(
    createMetricCard({
      label: "Auditoría del corpus",
      value: vm.auditIncluded,
      unit: "incluidos",
      hint: `${vm.auditScanned.toLocaleString("es-CO")} escaneados · ${vm.auditExcluded.toLocaleString(
        "es-CO",
      )} excluidos`,
    }),
  );

  grid.appendChild(
    createMetricCard({
      label: "Revisiones pendientes",
      value: vm.auditPendingRevisions,
      hint: vm.auditPendingRevisions === 0 ? "Cuello limpio" : "Requieren resolución",
      tone: vm.auditPendingRevisions === 0 ? "success" : "warning",
    }),
  );

  root.appendChild(grid);
  return root;
}
