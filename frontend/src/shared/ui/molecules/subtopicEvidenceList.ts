export interface SubtopicEvidenceRow {
  docId: string;
  filename: string;
  corpusRelativePath: string;
  autogenerarLabel: string | null;
  autogenerarRationale: string | null;
}

export interface SubtopicEvidenceListOptions {
  rows: SubtopicEvidenceRow[];
  loading?: boolean;
  error?: string | null;
}

export function createSubtopicEvidenceList(
  opts: SubtopicEvidenceListOptions,
): HTMLElement {
  const { rows, loading = false, error = null } = opts;

  const root = document.createElement("section");
  root.className = "lia-subtopic-evidence";
  root.setAttribute("data-lia-component", "subtopic-evidence-list");

  const header = document.createElement("header");
  header.className = "lia-subtopic-evidence__header";
  const heading = document.createElement("h4");
  heading.className = "lia-subtopic-evidence__title";
  heading.textContent = "Evidencia";
  header.appendChild(heading);
  const count = document.createElement("p");
  count.className = "lia-subtopic-evidence__count";
  count.textContent = loading ? "Cargando…" : `${rows.length} docs`;
  header.appendChild(count);
  root.appendChild(header);

  if (error) {
    const err = document.createElement("p");
    err.className = "lia-subtopic-evidence__error";
    err.textContent = error;
    root.appendChild(err);
    return root;
  }

  if (loading) {
    const skeleton = document.createElement("div");
    skeleton.className = "lia-subtopic-evidence__skeleton";
    skeleton.textContent = "Cargando evidencia…";
    root.appendChild(skeleton);
    return root;
  }

  if (rows.length === 0) {
    const empty = document.createElement("p");
    empty.className = "lia-subtopic-evidence__empty";
    empty.textContent = "Sin evidencia para esta propuesta.";
    root.appendChild(empty);
    return root;
  }

  const list = document.createElement("ul");
  list.className = "lia-subtopic-evidence__list";
  for (const row of rows) {
    const item = document.createElement("li");
    item.className = "lia-subtopic-evidence__item";
    item.setAttribute("data-doc-id", row.docId);

    const pathEl = document.createElement("p");
    pathEl.className = "lia-subtopic-evidence__path";
    pathEl.textContent = row.corpusRelativePath || row.filename;
    item.appendChild(pathEl);

    if (row.autogenerarLabel) {
      const labelEl = document.createElement("p");
      labelEl.className = "lia-subtopic-evidence__label";
      labelEl.textContent = `label: ${row.autogenerarLabel}`;
      item.appendChild(labelEl);
    }
    if (row.autogenerarRationale) {
      const rationaleEl = document.createElement("p");
      rationaleEl.className = "lia-subtopic-evidence__rationale";
      rationaleEl.textContent = row.autogenerarRationale;
      item.appendChild(rationaleEl);
    }

    list.appendChild(item);
  }
  root.appendChild(list);

  return root;
}
