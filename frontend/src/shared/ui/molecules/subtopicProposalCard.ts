import { createButton } from "@/shared/ui/atoms/button";
import { createChip } from "@/shared/ui/atoms/chip";

export type SubtopicDecisionAction =
  | "accept"
  | "reject"
  | "merge"
  | "rename"
  | "split";

export interface SubtopicProposalViewModel {
  proposalId: string;
  parentTopic: string;
  proposedKey: string;
  proposedLabel: string;
  candidateLabels: string[];
  evidenceCount: number;
  intraSimilarityMin: number;
  intraSimilarityMax: number;
  decided: boolean;
  latestAction?: SubtopicDecisionAction | null;
}

export interface SubtopicProposalCardOptions {
  proposal: SubtopicProposalViewModel;
  onAccept: (finalKey: string, finalLabel: string) => void;
  onReject: (reason: string) => void;
  onRenameRequest: () => void;
  onMergeRequest: () => void;
  onSplitRequest: () => void;
  onExpandEvidence: () => void;
}

function _buildHeader(
  proposal: SubtopicProposalViewModel,
): HTMLElement {
  const header = document.createElement("header");
  header.className = "lia-subtopic-proposal__header";

  const title = document.createElement("h3");
  title.className = "lia-subtopic-proposal__title";
  title.textContent = proposal.proposedLabel;
  header.appendChild(title);

  const meta = document.createElement("p");
  meta.className = "lia-subtopic-proposal__meta";
  meta.textContent = `${proposal.evidenceCount} docs · sim ${proposal.intraSimilarityMin.toFixed(2)}–${proposal.intraSimilarityMax.toFixed(2)}`;
  header.appendChild(meta);

  return header;
}

function _buildAliasList(
  proposal: SubtopicProposalViewModel,
): HTMLElement {
  const row = document.createElement("div");
  row.className = "lia-subtopic-proposal__aliases";
  for (const label of proposal.candidateLabels.slice(0, 6)) {
    row.appendChild(
      createChip({
        label,
        tone: "neutral",
        emphasis: "soft",
        dataComponent: "subtopic-alias-chip",
      }),
    );
  }
  if (proposal.candidateLabels.length > 6) {
    row.appendChild(
      createChip({
        label: `+${proposal.candidateLabels.length - 6} más`,
        tone: "info",
        emphasis: "soft",
        dataComponent: "subtopic-alias-chip-overflow",
      }),
    );
  }
  return row;
}

function _buildDecidedBanner(action: SubtopicDecisionAction | null | undefined): HTMLElement | null {
  if (!action) return null;
  const banner = document.createElement("p");
  banner.className = "lia-subtopic-proposal__decided";
  banner.setAttribute("data-lia-action", action);
  const labels: Record<SubtopicDecisionAction, string> = {
    accept: "Aceptado",
    reject: "Rechazado",
    merge: "Fusionado",
    rename: "Renombrado",
    split: "Dividido",
  };
  banner.textContent = `Decisión registrada: ${labels[action]}`;
  return banner;
}

export function createSubtopicProposalCard(
  opts: SubtopicProposalCardOptions,
): HTMLElement {
  const { proposal, onAccept, onReject, onRenameRequest, onMergeRequest, onSplitRequest, onExpandEvidence } = opts;

  const root = document.createElement("article");
  root.className = "lia-subtopic-proposal";
  if (proposal.decided) {
    root.classList.add("lia-subtopic-proposal--decided");
  }
  root.setAttribute("data-lia-component", "subtopic-proposal-card");
  root.setAttribute("data-proposal-id", proposal.proposalId);
  root.setAttribute("data-parent-topic", proposal.parentTopic);

  root.appendChild(_buildHeader(proposal));

  const body = document.createElement("div");
  body.className = "lia-subtopic-proposal__body";

  const keyLine = document.createElement("p");
  keyLine.className = "lia-subtopic-proposal__key";
  const keyLabel = document.createElement("span");
  keyLabel.className = "lia-subtopic-proposal__key-label";
  keyLabel.textContent = "key: ";
  const keyValue = document.createElement("code");
  keyValue.textContent = proposal.proposedKey;
  keyLine.append(keyLabel, keyValue);
  body.appendChild(keyLine);

  body.appendChild(_buildAliasList(proposal));

  const banner = _buildDecidedBanner(proposal.latestAction ?? null);
  if (banner) body.appendChild(banner);

  root.appendChild(body);

  const actions = document.createElement("footer");
  actions.className = "lia-subtopic-proposal__actions";

  actions.appendChild(
    createButton({
      tone: "primary",
      label: "Aceptar",
      disabled: proposal.decided,
      dataComponent: "subtopic-accept",
      onClick: () => onAccept(proposal.proposedKey, proposal.proposedLabel),
    }),
  );
  actions.appendChild(
    createButton({
      tone: "secondary",
      label: "Renombrar",
      disabled: proposal.decided,
      dataComponent: "subtopic-rename",
      onClick: onRenameRequest,
    }),
  );
  actions.appendChild(
    createButton({
      tone: "secondary",
      label: "Fusionar",
      disabled: proposal.decided,
      dataComponent: "subtopic-merge",
      onClick: onMergeRequest,
    }),
  );
  actions.appendChild(
    createButton({
      tone: "secondary",
      label: "Dividir",
      disabled: proposal.decided,
      dataComponent: "subtopic-split",
      onClick: onSplitRequest,
    }),
  );
  actions.appendChild(
    createButton({
      tone: "destructive",
      label: "Rechazar",
      disabled: proposal.decided,
      dataComponent: "subtopic-reject",
      onClick: () => {
        const reason = window.prompt("Razón para rechazar:");
        if (reason && reason.trim()) onReject(reason.trim());
      },
    }),
  );
  actions.appendChild(
    createButton({
      tone: "ghost",
      label: "Ver evidencia",
      dataComponent: "subtopic-evidence",
      onClick: onExpandEvidence,
    }),
  );

  root.appendChild(actions);

  return root;
}
