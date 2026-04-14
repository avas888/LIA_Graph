// @ts-nocheck

/**
 * Shared types for the normative modal subsystem.
 * Extracted from normativeModals.ts during decouple-v1 Phase 3.
 */

import type { I18nRuntime } from "@/shared/i18n";

export type AsyncTaskRunner = <T>(task: () => Promise<T>) => Promise<T>;

export interface CitationProfileFact {
  label?: string;
  value?: string;
}

export interface CitationProfileSection {
  id?: string;
  title?: string;
  body?: string;
}

export interface CitationProfileOriginalText {
  title?: string;
  quote?: string;
  source_url?: string | null;
  evidence_status?: "verified" | "missing" | "rejected_as_generic";
}

export interface CitationProfileVigenciaDetail {
  label?: string;
  basis?: string;
  notes?: string;
  last_verified_date?: string;
  evidence_status?: "verified" | "missing" | "rejected_as_generic";
  summary?: string;
}

export interface CitationProfileExpertComment {
  topic_label?: string;
  body?: string;
  source_label?: string | null;
  source_url?: string | null;
  accordion_default?: "open" | "closed";
  evidence_status?: "verified" | "missing" | "rejected_as_generic";
}

export interface CitationProfileAdditionalDepthItem {
  label?: string;
  url?: string | null;
  kind?: string | null;
  doc_id?: string | null;
}

export interface CitationProfileAdditionalDepthSection {
  title?: string;
  items?: CitationProfileAdditionalDepthItem[];
  accordion_default?: "open" | "closed";
}

export interface CitationProfileBanner {
  title?: string;
  body?: string;
  tone?: string;
}

export interface CitationProfileAction {
  label?: string;
  state?: "available" | "unavailable" | "not_applicable";
  url?: string | null;
  fallback_url?: string | null;
  helper_text?: string | null;
}

export interface CitationProfileResponse {
  title?: string;
  document_family?: string;
  /**
   * Classification label from `normative_taxonomy.py` (e.g. "Decreto
   * reglamentario", "Ley o estatuto"). Rendered prefixed with
   * "Fuerza vinculante:" by the profile renderers — see
   * `docs/guides/modal_content_layout_leyes_et.md` §9.
   */
  binding_force?: string;
  /**
   * Numeric position on the binding-force hierarchy from
   * `normative_taxonomy.py` (1000 = constitutional, 100 = generic support
   * document). Used to drive badge tones without string-matching the label.
   */
  binding_force_rank?: number;
  lead?: string;
  facts?: CitationProfileFact[];
  sections?: CitationProfileSection[];
  original_text?: CitationProfileOriginalText | null;
  vigencia_detail?: CitationProfileVigenciaDetail | null;
  expert_comment?: CitationProfileExpertComment | null;
  additional_depth_sections?: CitationProfileAdditionalDepthSection[] | null;
  caution_banner?: CitationProfileBanner | null;
  analysis_action?: CitationProfileAction;
  companion_action?: CitationProfileAction;
  source_action?: CitationProfileAction;
  needs_llm?: boolean;
  skipped?: boolean;
}

export interface ParsedEtLocator {
  kind: "single" | "range" | "list";
  parts: string[];
}

export interface ChatModalState {
  activeCitation: unknown;
  activeNormaRequestId: number;
  lastUserMessage: string;
  lastAssistantAnswerMarkdown: string;
  modalStack: string[];
}

export interface NormativeModalDom {
  modalLayer: HTMLElement;
  modalNorma: HTMLElement;
  modalInterpretations: HTMLElement;
  modalSummary: HTMLElement;
  normaTitleNode: HTMLElement;
  normaBindingForceNode: HTMLElement;
  normaOriginalBtn: HTMLButtonElement;
  normaAnalysisBtn: HTMLButtonElement;
  normaOriginalHelperNode: HTMLElement;
  normaAnalysisHelperNode: HTMLElement;
  normaTopbarNode: HTMLElement;
  normaLoadingNode: HTMLElement;
  normaHelperNode: HTMLElement;
  normaCautionBannerNode: HTMLElement;
  normaCautionTitleNode: HTMLElement;
  normaCautionBodyNode: HTMLElement;
  normaPrimaryNode: HTMLElement;
  normaLeadNode: HTMLElement;
  normaFactsNode: HTMLElement;
  normaSectionsNode: HTMLElement;
  normaCompanionNode: HTMLElement;
  normaCompanionBtn: HTMLAnchorElement;
  normaCompanionHelperNode: HTMLElement;
  interpretationStatusNode: HTMLElement;
  interpretationResultsNode: HTMLElement;
  summaryModeNode: HTMLElement;
  summaryExternalLinkNode: HTMLAnchorElement;
  summaryBodyNode: HTMLElement;
  summaryGroundingNode: HTMLElement;
}

export interface CreateNormativeModalControllerOptions {
  i18n: I18nRuntime;
  state: ChatModalState;
  dom: NormativeModalDom;
  withThinkingWheel: AsyncTaskRunner;
}
