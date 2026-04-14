import type { CitationGroupViewModel, CitationItemViewModel } from "@/shared/ui/organisms/citationList";
import type { ExpertCardViewModel } from "@/shared/ui/organisms/expertCards";

export const UI_EVENT_CITATIONS_UPDATED = "lia:citations-updated";
export const UI_EVENT_CITATIONS_PREVIEW = "lia:citations-preview";
export const UI_EVENT_EXPERTS_UPDATED = "lia:experts-updated";

export interface CitationsUpdatedDetail {
  groups: CitationGroupViewModel[];
  /** True when this event represents a final/settled citation update (not a loading placeholder). */
  isFinal?: boolean;
}

/**
 * Emitted while LIA is still thinking, carrying a non-authoritative preview of
 * retrieved citations so the desktop Soporte Normativo panel can pre-populate
 * muted, non-clickable placeholders. W2 Phase 7 — see
 * docs/next/soporte_normativo_citation_ordering.md §§10–15.
 *
 * Desktop-only by design. The mobile adapter does NOT subscribe to this event;
 * mobile continues to see only UI_EVENT_CITATIONS_UPDATED on final.
 */
export interface CitationsPreviewDetail {
  items: CitationItemViewModel[];
}

export interface ExpertsUpdatedDetail {
  cards: ExpertCardViewModel[];
}

export function emitUiEvent<T>(target: EventTarget, name: string, detail: T): void {
  target.dispatchEvent(new CustomEvent<T>(name, { bubbles: true, detail }));
}
