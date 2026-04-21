import {
  createGenerationRow,
  type GenerationRowViewModel,
} from "@/shared/ui/molecules/generationRow";

export interface GenerationsListOptions {
  rows: GenerationRowViewModel[];
  emptyMessage?: string;
  errorMessage?: string;
  onSelect?: (id: string) => void;
}

export function createGenerationsList(opts: GenerationsListOptions): HTMLElement {
  const { rows, emptyMessage = "Aún no hay generaciones registradas.", errorMessage, onSelect } = opts;
  const root = document.createElement("section");
  root.className = "lia-generations-list";
  root.setAttribute("data-lia-component", "generations-list");

  const header = document.createElement("header");
  header.className = "lia-generations-list__header";

  const title = document.createElement("h2");
  title.className = "lia-generations-list__title";
  title.textContent = "Generaciones recientes";
  header.appendChild(title);

  const sub = document.createElement("p");
  sub.className = "lia-generations-list__subtitle";
  sub.textContent = "Cada fila es una corrida de python -m lia_graph.ingest publicada en Supabase.";
  header.appendChild(sub);

  root.appendChild(header);

  const body = document.createElement("div");
  body.className = "lia-generations-list__body";

  if (errorMessage) {
    const err = document.createElement("p");
    err.className = "lia-generations-list__feedback lia-generations-list__feedback--error";
    err.textContent = errorMessage;
    body.appendChild(err);
  } else if (rows.length === 0) {
    const empty = document.createElement("p");
    empty.className = "lia-generations-list__feedback";
    empty.textContent = emptyMessage;
    body.appendChild(empty);
  } else {
    const headerRow = document.createElement("div");
    headerRow.className = "lia-generations-list__head-row";
    ["Generación", "Estado", "Fecha", "Documentos", "Chunks", "Familia principal"].forEach((h) => {
      const cell = document.createElement("span");
      cell.className = "lia-generations-list__head-cell";
      cell.textContent = h;
      headerRow.appendChild(cell);
    });
    body.appendChild(headerRow);

    rows.forEach((row) => body.appendChild(createGenerationRow(row, onSelect)));
  }

  root.appendChild(body);
  return root;
}
