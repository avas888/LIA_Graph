import {
  createSubtopicProposalCard,
  type SubtopicProposalViewModel,
  type SubtopicDecisionAction,
} from "@/shared/ui/molecules/subtopicProposalCard";
import {
  createSubtopicEvidenceList,
  type SubtopicEvidenceRow,
} from "@/shared/ui/molecules/subtopicEvidenceList";

export interface SubtopicCurationBoardOptions {
  proposals: SubtopicProposalViewModel[];
  currentTaxonomy: Record<string, { key: string; label: string; evidenceCount: number }[]>;
  evidenceByProposalId: Map<string, SubtopicEvidenceRow[]>;
  evidenceLoadingIds: Set<string>;
  expandedProposalIds: Set<string>;
  onAccept: (proposalId: string, finalKey: string, finalLabel: string) => void;
  onReject: (proposalId: string, reason: string) => void;
  onRenameRequest: (proposalId: string, nextLabel: string, nextKey?: string) => void;
  onMergeRequest: (proposalId: string, mergedInto: string) => void;
  onSplitRequest: (proposalId: string, aliases: string[]) => void;
  onExpandEvidence: (proposalId: string) => void;
}

function _renderEmpty(): HTMLElement {
  const block = document.createElement("div");
  block.className = "lia-subtopic-board__empty";
  block.textContent =
    "Sin propuestas disponibles. Corre `make phase2-collect-subtopic-candidates` y luego `make phase3-mine-subtopic-candidates` para generar el archivo de propuestas.";
  return block;
}

function _renderParentColumn(
  parentTopic: string,
  proposals: SubtopicProposalViewModel[],
  opts: SubtopicCurationBoardOptions,
): HTMLElement {
  const column = document.createElement("section");
  column.className = "lia-subtopic-board__column";
  column.setAttribute("data-parent-topic", parentTopic);

  const head = document.createElement("header");
  head.className = "lia-subtopic-board__column-head";
  const title = document.createElement("h2");
  title.className = "lia-subtopic-board__column-title";
  title.textContent = parentTopic;
  head.appendChild(title);

  const pendingCount = proposals.filter((p) => !p.decided).length;
  const meta = document.createElement("p");
  meta.className = "lia-subtopic-board__column-meta";
  meta.textContent = `${pendingCount} pendientes · ${proposals.length} total`;
  head.appendChild(meta);

  column.appendChild(head);

  const list = document.createElement("div");
  list.className = "lia-subtopic-board__column-list";
  for (const proposal of proposals) {
    const card = createSubtopicProposalCard({
      proposal,
      onAccept: (finalKey, finalLabel) =>
        opts.onAccept(proposal.proposalId, finalKey, finalLabel),
      onReject: (reason) => opts.onReject(proposal.proposalId, reason),
      onRenameRequest: () => {
        const nextLabel = window.prompt(
          "Nuevo label (renombrar):",
          proposal.proposedLabel,
        );
        if (!nextLabel || !nextLabel.trim()) return;
        const nextKey = window.prompt(
          "Nuevo key (deja vacío para mantener):",
          proposal.proposedKey,
        );
        opts.onRenameRequest(
          proposal.proposalId,
          nextLabel.trim(),
          (nextKey || "").trim() || undefined,
        );
      },
      onMergeRequest: () => {
        const siblings = proposals.filter((p) => p.proposalId !== proposal.proposalId);
        if (siblings.length === 0) {
          window.alert("No hay otras propuestas en este tema parent para fusionar.");
          return;
        }
        const options = siblings
          .map((p, i) => `${i + 1}. ${p.proposalId} — ${p.proposedLabel}`)
          .join("\n");
        const pick = window.prompt(
          `Fusionar con cuál propuesta? Escribe el número:\n${options}`,
        );
        const idx = Number((pick || "").trim()) - 1;
        if (!Number.isInteger(idx) || idx < 0 || idx >= siblings.length) return;
        opts.onMergeRequest(proposal.proposalId, siblings[idx].proposalId);
      },
      onSplitRequest: () => {
        const raw = window.prompt(
          "Alias para dividir (separados por coma, mínimo 2):",
          proposal.candidateLabels.slice(0, 2).join(","),
        );
        if (!raw) return;
        const aliases = raw
          .split(",")
          .map((a) => a.trim())
          .filter(Boolean);
        if (aliases.length < 2) {
          window.alert("Se requieren al menos 2 aliases para dividir.");
          return;
        }
        opts.onSplitRequest(proposal.proposalId, aliases);
      },
      onExpandEvidence: () => opts.onExpandEvidence(proposal.proposalId),
    });

    list.appendChild(card);

    if (opts.expandedProposalIds.has(proposal.proposalId)) {
      const evidenceRows = opts.evidenceByProposalId.get(proposal.proposalId) ?? [];
      const loading = opts.evidenceLoadingIds.has(proposal.proposalId);
      list.appendChild(createSubtopicEvidenceList({ rows: evidenceRows, loading }));
    }
  }
  column.appendChild(list);

  return column;
}

function _renderTaxonomySidebar(
  taxonomy: SubtopicCurationBoardOptions["currentTaxonomy"],
): HTMLElement {
  const sidebar = document.createElement("aside");
  sidebar.className = "lia-subtopic-board__sidebar";
  sidebar.setAttribute("data-lia-component", "subtopic-taxonomy-sidebar");

  const title = document.createElement("h3");
  title.className = "lia-subtopic-board__sidebar-title";
  title.textContent = "Taxonomía actual";
  sidebar.appendChild(title);

  const parents = Object.keys(taxonomy).sort();
  if (parents.length === 0) {
    const empty = document.createElement("p");
    empty.className = "lia-subtopic-board__sidebar-empty";
    empty.textContent = "Aún no se ha promovido ninguna taxonomía.";
    sidebar.appendChild(empty);
    return sidebar;
  }

  for (const parent of parents) {
    const group = document.createElement("section");
    group.className = "lia-subtopic-board__sidebar-group";
    const heading = document.createElement("h4");
    heading.className = "lia-subtopic-board__sidebar-parent";
    heading.textContent = parent;
    group.appendChild(heading);

    const list = document.createElement("ul");
    list.className = "lia-subtopic-board__sidebar-list";
    for (const entry of taxonomy[parent] || []) {
      const li = document.createElement("li");
      li.className = "lia-subtopic-board__sidebar-item";
      li.textContent = `${entry.label} (${entry.evidenceCount})`;
      list.appendChild(li);
    }
    group.appendChild(list);
    sidebar.appendChild(group);
  }

  return sidebar;
}

export function createSubtopicCurationBoard(
  opts: SubtopicCurationBoardOptions,
): HTMLElement {
  const root = document.createElement("div");
  root.className = "lia-subtopic-board";
  root.setAttribute("data-lia-component", "subtopic-curation-board");

  if (opts.proposals.length === 0) {
    root.appendChild(_renderEmpty());
    return root;
  }

  const byParent = new Map<string, SubtopicProposalViewModel[]>();
  for (const proposal of opts.proposals) {
    const existing = byParent.get(proposal.parentTopic) ?? [];
    existing.push(proposal);
    byParent.set(proposal.parentTopic, existing);
  }

  const grid = document.createElement("div");
  grid.className = "lia-subtopic-board__grid";
  for (const parent of Array.from(byParent.keys()).sort()) {
    grid.appendChild(_renderParentColumn(parent, byParent.get(parent)!, opts));
  }
  root.appendChild(grid);

  return root;
}

export function createSubtopicTaxonomySidebar(
  taxonomy: SubtopicCurationBoardOptions["currentTaxonomy"],
): HTMLElement {
  return _renderTaxonomySidebar(taxonomy);
}

export type { SubtopicDecisionAction };
