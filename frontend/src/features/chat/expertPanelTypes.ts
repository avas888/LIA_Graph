// @ts-nocheck

/**
 * Type declarations for the expert panel controller.
 *
 * Extracted from `expertPanelController.ts` during granularize-v2
 * round 17 — types only, no runtime code — so the host file gets the
 * safest possible trim. Consumed by `expertPanelController.ts` and by
 * the helpers that will follow in subsequent rounds.
 */

import type { I18nRuntime } from "@/shared/i18n";


export interface ExpertProvider {
  name: string;
  url: string | null;
}

export interface ExpertProviderLink {
  url: string;
  label: string;
  provider: string;
}

export interface ExpertSnippet {
  doc_id: string;
  source_doc_id?: string;
  logical_doc_id?: string;
  authority: string;
  title: string;
  snippet: string;
  position_signal: string;
  relevance_score: number;
  trust_tier: string;
  provider_links: ExpertProviderLink[];
  providers: ExpertProvider[];
  source_view_url?: string | null;
  official_url?: string | null;
  open_url?: string | null;
  card_summary: string;
  extended_excerpt?: string;
  summary_origin?: string;
  summary_quality?: string;
  source_hash?: string;
  coverage_axes?: string[];
  requested_match?: boolean;
  selection_reason?: string;
  core_ref_matches?: string[];
  panel_rank?: number | null;
}

export interface ExpertGroup {
  article_ref: string;
  classification: "concordancia" | "divergencia" | "complementario";
  summary_signal: string;
  summary_origin?: string;
  summary_quality?: string;
  providers: ExpertProvider[];
  snippets: ExpertSnippet[];
  relevance_score?: number;
  coverage_axes?: string[];
  requested_match?: boolean;
  selection_reason?: string;
  panel_rank?: number | null;
}

export interface ExpertPanelResponse {
  ok: boolean;
  groups: ExpertGroup[];
  ungrouped: ExpertSnippet[];
  total_available?: number;
  has_more?: boolean;
  next_offset?: number | null;
  retrieval_diagnostics?: Record<string, unknown>;
  trace_id?: string;
}

export type ExpertCardClassification = ExpertGroup["classification"] | "individual";
export type ExpertSignal = "permite" | "restringe" | "condiciona" | "neutral";

export interface ExpertCard {
  id: string;
  classification: ExpertCardClassification;
  dominantSignal: ExpertSignal;
  articleRef: string;
  articleLabel: string;
  heading: string;
  lead: string;
  implication: string;
  checklist: string[];
  sources: ExpertSnippet[];
  providers: ExpertProvider[];
  authorities: string[];
  summarySignal: string;
  maxRelevance: number;
  requestedMatch: boolean;
  panelRank: number;
  posibleRelevancia: string | null;
  resumenNutshell: string | null;
  esRelevante: boolean | null;
}

export interface ExpertPanelLoadOptions {
  traceId: string;
  message: string;
  assistantAnswer?: string;
  normativeArticleRefs?: string[];
  searchSeed?: string;
  searchSeedOrigin?: string;
  topic?: string;
  pais?: string;
}

export interface ExpertPanelPersistedState {
  status: "idle" | "loading" | "empty" | "error" | "populated";
  loadOptions: ExpertPanelLoadOptions | null;
  response: ExpertPanelResponse | null;
  enhancements?: Record<string, { posibleRelevancia: string | null; resumenNutshell: string | null; esRelevante: boolean | null }> | null;
}

export interface ExpertPanelControllerOptions {
  i18n: I18nRuntime;
  contentNode: HTMLElement;
  statusNode: HTMLElement;
  detailModalNode?: HTMLElement | null;
  openModal?: (modal: HTMLElement) => void;
  onSnippetClick?: (docId: string) => void;
  onStateChanged?: (state: ExpertPanelPersistedState | null) => void;
}
