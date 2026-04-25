/**
 * Sub-topics controller — curation surface.
 *
 * Binds the four /api/subtopics/* endpoints to the atomic-design organism
 * (`subtopicCurationBoard`). Read-only for non-admins (the server enforces
 * 403; the UI surfaces the error toast).
 *
 * Source-of-truth: docs/done/next/subtopic_generationv1.md Phase 5.
 */

import { ApiError, getJson, postJson } from "@/shared/api/client";
import {
  createSubtopicCurationBoard,
  createSubtopicTaxonomySidebar,
} from "@/shared/ui/organisms/subtopicCurationBoard";
import type {
  SubtopicProposalViewModel,
  SubtopicDecisionAction,
} from "@/shared/ui/molecules/subtopicProposalCard";
import type { SubtopicEvidenceRow } from "@/shared/ui/molecules/subtopicEvidenceList";

// ── API contracts ───────────────────────────────────────────────────

interface ProposalApiRow {
  proposal_id: string;
  parent_topic: string;
  proposed_key: string;
  proposed_label: string;
  candidate_labels: string[];
  evidence_doc_ids: string[];
  evidence_count: number;
  intra_similarity_min: number;
  intra_similarity_max: number;
  decided: boolean;
  latest_decision: { action?: SubtopicDecisionAction } | null;
}

interface ProposalsResponse {
  ok: boolean;
  source_path: string | null;
  proposals: ProposalApiRow[];
  decided_count: number;
}

interface EvidenceApiRow {
  doc_id: string;
  filename: string;
  corpus_relative_path: string;
  autogenerar_label: string | null;
  autogenerar_rationale: string | null;
  parent_topic: string;
}

interface EvidenceResponse {
  ok: boolean;
  proposal_id: string;
  parent_topic: string;
  proposed_label: string;
  evidence: EvidenceApiRow[];
}

interface TaxonomyEntryApi {
  key: string;
  label: string;
  aliases: string[];
  evidence_count: number;
  curated_at: string;
  curator: string;
}

interface TaxonomyResponse {
  ok: boolean;
  exists: boolean;
  taxonomy: {
    version: string | null;
    generated_from: string | null;
    generated_at: string | null;
    subtopics: Record<string, TaxonomyEntryApi[]>;
  };
}

interface DecisionPayload {
  proposal_id: string;
  action: SubtopicDecisionAction;
  final_key?: string;
  final_label?: string;
  merged_into?: string;
  reason?: string;
  aliases?: string[];
}

interface DecisionResponse {
  ok: boolean;
  decision: Record<string, unknown>;
}

// ── Controller ──────────────────────────────────────────────────────

export interface SubtopicController {
  refresh: () => Promise<void>;
  destroy: () => void;
}

interface InternalState {
  proposals: SubtopicProposalViewModel[];
  taxonomy: Record<string, { key: string; label: string; evidenceCount: number }[]>;
  evidenceByProposalId: Map<string, SubtopicEvidenceRow[]>;
  evidenceLoadingIds: Set<string>;
  expandedProposalIds: Set<string>;
  inflightFetches: Set<AbortController>;
  destroyed: boolean;
}

function _mapProposal(row: ProposalApiRow): SubtopicProposalViewModel {
  return {
    proposalId: row.proposal_id,
    parentTopic: row.parent_topic,
    proposedKey: row.proposed_key,
    proposedLabel: row.proposed_label,
    candidateLabels: row.candidate_labels ?? [],
    evidenceCount: row.evidence_count,
    intraSimilarityMin: row.intra_similarity_min,
    intraSimilarityMax: row.intra_similarity_max,
    decided: Boolean(row.decided),
    latestAction: row.latest_decision?.action ?? null,
  };
}

function _mapEvidence(row: EvidenceApiRow): SubtopicEvidenceRow {
  return {
    docId: row.doc_id,
    filename: row.filename,
    corpusRelativePath: row.corpus_relative_path,
    autogenerarLabel: row.autogenerar_label,
    autogenerarRationale: row.autogenerar_rationale,
  };
}

function _buildToast(message: string, tone: "error" | "success"): HTMLElement {
  const toast = document.createElement("div");
  toast.className = `lia-subtopic-toast lia-subtopic-toast--${tone}`;
  toast.setAttribute("role", "alert");
  toast.textContent = message;
  setTimeout(() => toast.remove(), 5_000);
  return toast;
}

async function postDecision(payload: DecisionPayload): Promise<DecisionResponse> {
  const { response, data } = await postJson<DecisionResponse, DecisionPayload>(
    "/api/subtopics/decision",
    payload,
  );
  if (!response.ok) {
    const errMsg =
      data && typeof data === "object" && "reason" in (data as Record<string, unknown>)
        ? String((data as { reason?: string }).reason || response.statusText)
        : response.statusText;
    throw new ApiError(errMsg, response.status, data);
  }
  if (!data) throw new ApiError("Empty decision response", response.status, null);
  return data;
}

export function createSubtopicController(
  rootElement: HTMLElement,
): SubtopicController {
  const boardSlot = rootElement.querySelector<HTMLElement>("[data-slot=curation-board]");
  const sidebarSlot = rootElement.querySelector<HTMLElement>("[data-slot=taxonomy-sidebar]");
  if (!boardSlot || !sidebarSlot) {
    rootElement.textContent = "Sub-topics: missing render slots.";
    return { refresh: async () => undefined, destroy: () => undefined };
  }

  const state: InternalState = {
    proposals: [],
    taxonomy: {},
    evidenceByProposalId: new Map(),
    evidenceLoadingIds: new Set(),
    expandedProposalIds: new Set(),
    inflightFetches: new Set(),
    destroyed: false,
  };

  function _render(): void {
    if (state.destroyed) return;
    boardSlot!.replaceChildren(
      createSubtopicCurationBoard({
        proposals: state.proposals,
        currentTaxonomy: state.taxonomy,
        evidenceByProposalId: state.evidenceByProposalId,
        evidenceLoadingIds: state.evidenceLoadingIds,
        expandedProposalIds: state.expandedProposalIds,
        onAccept: (pid, finalKey, finalLabel) =>
          void _submit({ proposal_id: pid, action: "accept", final_key: finalKey, final_label: finalLabel }),
        onReject: (pid, reason) =>
          void _submit({ proposal_id: pid, action: "reject", reason }),
        onRenameRequest: (pid, nextLabel, nextKey) =>
          void _submit({
            proposal_id: pid,
            action: "rename",
            final_label: nextLabel,
            ...(nextKey ? { final_key: nextKey } : {}),
          }),
        onMergeRequest: (pid, mergedInto) =>
          void _submit({ proposal_id: pid, action: "merge", merged_into: mergedInto }),
        onSplitRequest: (pid, aliases) =>
          void _submit({ proposal_id: pid, action: "split", aliases }),
        onExpandEvidence: (pid) => void _toggleEvidence(pid),
      }),
    );
    sidebarSlot!.replaceChildren(createSubtopicTaxonomySidebar(state.taxonomy));
  }

  function _flashToast(message: string, tone: "error" | "success"): void {
    rootElement.appendChild(_buildToast(message, tone));
  }

  async function _loadProposals(): Promise<void> {
    try {
      const data = await getJson<ProposalsResponse>("/api/subtopics/proposals");
      state.proposals = (data.proposals ?? []).map(_mapProposal);
    } catch (err) {
      state.proposals = [];
      _flashToast(
        `Error cargando propuestas: ${err instanceof Error ? err.message : String(err)}`,
        "error",
      );
    }
  }

  async function _loadTaxonomy(): Promise<void> {
    try {
      const data = await getJson<TaxonomyResponse>("/api/subtopics/taxonomy");
      const subtopics = data.taxonomy?.subtopics ?? {};
      const mapped: InternalState["taxonomy"] = {};
      for (const [parent, entries] of Object.entries(subtopics)) {
        mapped[parent] = (entries || []).map((e) => ({
          key: e.key,
          label: e.label,
          evidenceCount: e.evidence_count,
        }));
      }
      state.taxonomy = mapped;
    } catch (err) {
      state.taxonomy = {};
      _flashToast(
        `Error cargando taxonomía: ${err instanceof Error ? err.message : String(err)}`,
        "error",
      );
    }
  }

  async function _submit(payload: DecisionPayload): Promise<void> {
    try {
      await postDecision(payload);
      _flashToast(`Decisión registrada: ${payload.action}`, "success");
      await refresh();
    } catch (err) {
      _flashToast(
        `No se pudo registrar la decisión: ${err instanceof Error ? err.message : String(err)}`,
        "error",
      );
    }
  }

  async function _toggleEvidence(proposalId: string): Promise<void> {
    if (state.expandedProposalIds.has(proposalId)) {
      state.expandedProposalIds.delete(proposalId);
      _render();
      return;
    }
    state.expandedProposalIds.add(proposalId);
    state.evidenceLoadingIds.add(proposalId);
    _render();
    try {
      const data = await getJson<EvidenceResponse>(
        `/api/subtopics/evidence?proposal_id=${encodeURIComponent(proposalId)}`,
      );
      state.evidenceByProposalId.set(
        proposalId,
        (data.evidence ?? []).map(_mapEvidence),
      );
    } catch (err) {
      state.evidenceByProposalId.set(proposalId, []);
      _flashToast(
        `Error cargando evidencia: ${err instanceof Error ? err.message : String(err)}`,
        "error",
      );
    } finally {
      state.evidenceLoadingIds.delete(proposalId);
      _render();
    }
  }

  async function refresh(): Promise<void> {
    await Promise.all([_loadProposals(), _loadTaxonomy()]);
    _render();
  }

  function destroy(): void {
    state.destroyed = true;
    for (const controller of state.inflightFetches) {
      try {
        controller.abort();
      } catch {
        /* noop */
      }
    }
    state.inflightFetches.clear();
    state.expandedProposalIds.clear();
    state.evidenceByProposalId.clear();
    state.evidenceLoadingIds.clear();
    boardSlot!.replaceChildren();
    sidebarSlot!.replaceChildren();
  }

  return { refresh, destroy };
}
