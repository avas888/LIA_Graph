// @ts-nocheck

/**
 * Citation sorting, formatting, and DOM rendering for the chat sidebar.
 * Extracted from chatApp.ts during decouple-v1 Phase 2.
 */

import { dedupeCitations, mergeCitations, asCitationArray } from "@/features/chat/citations";
import {
  citationTitleValue,
  deriveSourceTierLabel,
} from "@/features/chat/normativeModals";
import type { QuestionEntry } from "@/features/chat/chatTypes";
import {
  createCitationPlaceholder,
  renderCitationList,
  type CitationGroupViewModel,
  type CitationItemViewModel,
} from "@/shared/ui/organisms/citationList";
import {
  UI_EVENT_CITATIONS_PREVIEW,
  UI_EVENT_CITATIONS_UPDATED,
  emitUiEvent,
} from "@/shared/ui/patterns/uiEvents";

export interface CitationRendererDeps {
  citationsList: HTMLElement;
  citationsStatusNode: HTMLElement | null;
  openNormaModal: (citation: any) => void;
  root?: EventTarget | null;
}

export function createCitationRenderer(deps: CitationRendererDeps) {
  const { citationsList, citationsStatusNode, openNormaModal, root = null } = deps;
  let lastGroups: CitationGroupViewModel[] = [];
  let lastCitationMap = new Map<string, any>();

  function setCitationsStatus(text) {
    if (!citationsStatusNode) return;
    citationsStatusNode.textContent = String(text || "").trim();
  }

  function emitGroups(groups: CitationGroupViewModel[], isFinal = false) {
    lastGroups = groups;
    if (root) {
      emitUiEvent(root, UI_EVENT_CITATIONS_UPDATED, { groups, isFinal });
    }
  }

  function rememberCitations(citations) {
    lastCitationMap = new Map(
      (Array.isArray(citations) ? citations : [])
        .map((citation) => [citationId(citation), citation]),
    );
  }

  function renderDeferredCitationsState(label, { loading = false }: { loading?: boolean } = {}) {
    citationsList.replaceChildren(
      createCitationPlaceholder(
        label || (loading ? "Cargando soporte normativo..." : "Sin normativa disponible para este turno."),
        loading ? "loading" : "deferred",
      ),
    );
    emitGroups([], false);
  }

  function citationHasCorpusContext(citation) {
    return Boolean(String(citation?.doc_id || "").trim()) && !Boolean(citation?.mention_only);
  }

  /**
   * W1 Phase 1 — family rank for Rule B.
   *
   * Returns a numeric rank for ordering citations by practical impact to the
   * accountant. Lower rank = more operational/enforceable = shown first:
   *
   *   0. resolucion_dian / resolucion  (operational — annual forms, thresholds)
   *   1. circular                       (official administrative guidance)
   *   2. concepto_dian / concepto       (official interpretive doctrine)
   *   3. decreto / dur                  (regulatory norms)
   *   4. ley                            (statute)
   *   5. et                             (foundational code)
   *   6. formulario                     (form reference)
   *   9. unknown                        (falls to the bottom)
   *
   * Prefers the structured `reference_type` field. Falls back to a title
   * prefix match using `citationTitleValue` when the structured field is
   * absent. See docs/next/soporte_normativo_citation_ordering.md §3.1.
   */
  function citationFamilyRank(citation) {
    const type = String(citation?.reference_type || "").trim().toLowerCase();
    switch (type) {
      case "resolucion_dian":
      case "resolucion":
        return 0;
      case "circular":
        return 1;
      case "concepto_dian":
      case "concepto":
        return 2;
      case "decreto":
      case "dur":
        return 3;
      case "ley":
        return 4;
      case "et":
        return 5;
      case "formulario":
        return 6;
    }
    if (type) return 9;
    const title = String(citationTitleValue(citation) || "").trim().toLowerCase();
    if (!title) return 9;
    if (title.startsWith("resolución") || title.startsWith("resolucion")) return 0;
    if (title.startsWith("circular")) return 1;
    if (title.startsWith("concepto")) return 2;
    if (title.startsWith("decreto")) return 3;
    if (title.startsWith("ley ")) return 4;
    if (title.startsWith("estatuto") || title.startsWith("artículo") || title.startsWith("articulo")) return 5;
    if (title.startsWith("formulario") || title.startsWith("formato")) return 6;
    return 9;
  }

  /**
   * W1 Phase 1 — issuance year for Rule A.
   *
   * Returns the four-digit issuance year of a citation so same-family items
   * can be sorted latest-first. Strategy:
   *
   *   1. Parse from `reference_key` via `/:(\d{4})(?::|$)/` — matches
   *      `resolucion_dian:162:2023`, `ley:1819:2016`, `decreto:1070:2013`.
   *      Bare `et` has no year and returns 0.
   *   2. Fallback: parse `legal_reference` / `title` via `/\bde\s+(\d{4})\b/`
   *      for inputs like "Resolución 233 de 2025".
   *   3. Reject years < 1900 as a defensive guard against stray numbers.
   *   4. Return 0 on no match. A 0 sorts last within its family, which is
   *      correct for bare ET items (all at year 0).
   *
   * See docs/next/soporte_normativo_citation_ordering.md §3.2.
   */
  function citationIssuanceYear(citation) {
    const referenceKey = String(citation?.reference_key || "").trim();
    const keyMatch = /:(\d{4})(?::|$)/.exec(referenceKey);
    if (keyMatch) {
      const year = Number.parseInt(keyMatch[1], 10);
      if (Number.isFinite(year) && year >= 1900) return year;
    }
    const fallbackSource = String(
      citation?.legal_reference || citation?.title || citationTitleValue(citation) || "",
    );
    const textMatch = /\bde\s+(\d{4})\b/i.exec(fallbackSource);
    if (textMatch) {
      const year = Number.parseInt(textMatch[1], 10);
      if (Number.isFinite(year) && year >= 1900) return year;
    }
    return 0;
  }

  /**
   * W1 Phase 1 — family-aware, year-aware citation sort.
   *
   * Order of comparison:
   *   1. Corpus-context priority — items with real `doc_id` (not mention-only)
   *      win over mention-only entries.
   *   2. Family rank ascending (Rule B) — operational norms before
   *      foundational ones.
   *   3. Issuance year descending (Rule A) — latest year first within a
   *      family. Year=0 items sort last in the family, which is correct for
   *      ET articles and other bare references without a year.
   *   4. Original insertion index ascending — the Rule-B-within-family
   *      tiebreak. The retriever's/composer's order is already a relevance
   *      proxy, so ET articles (and other year-less items) show in the
   *      order they were surfaced.
   *
   * Decorate-sort-undecorate over `{ c, i }` so the insertion-index tiebreak
   * is explicit and portable across JS engines.
   *
   * See docs/next/soporte_normativo_citation_ordering.md §3.3.
   */
  function sortCitationsForDisplay(citations) {
    const decorated = [...citations].map((citation, index) => ({ citation, index }));
    decorated.sort((left, right) => {
      const leftCorpusRank = citationHasCorpusContext(left.citation) ? 0 : 1;
      const rightCorpusRank = citationHasCorpusContext(right.citation) ? 0 : 1;
      if (leftCorpusRank !== rightCorpusRank) return leftCorpusRank - rightCorpusRank;
      const leftFamily = citationFamilyRank(left.citation);
      const rightFamily = citationFamilyRank(right.citation);
      if (leftFamily !== rightFamily) return leftFamily - rightFamily;
      const leftYear = citationIssuanceYear(left.citation);
      const rightYear = citationIssuanceYear(right.citation);
      if (leftYear !== rightYear) {
        // Year 0 (missing) sorts LAST within a family, so a 0 should beat
        // nothing except another 0. Descending order for real years, with
        // zeros pushed to the end.
        if (leftYear === 0) return 1;
        if (rightYear === 0) return -1;
        return rightYear - leftYear;
      }
      return left.index - right.index;
    });
    return decorated.map((entry) => entry.citation);
  }

  function formatCitationMeta(tier, provider) {
    const left = String(tier || "").trim();
    const right = String(provider || "").trim();
    if (left && right) {
      if (left.localeCompare(right, "es", { sensitivity: "base" }) === 0) {
        return left;
      }
      return `${left} | ${right}`;
    }
    return left || right || "Sin documento en corpus";
  }

  function citationId(citation) {
    return String(
      citation?.doc_id ||
      citation?.reference_key ||
      citation?.external_url ||
      citation?.locator_start ||
      citation?.title ||
      citation?.label ||
      citation?.source_provider ||
      "citation",
    ).trim();
  }

  function toCitationViewModel(citation): CitationItemViewModel {
    const isMentionOnly = Boolean(citation?.mention_only) || !citation?.doc_id;
    const referenceKey = String(citation?.reference_key || "").trim().toLowerCase();
    const canOpenByReference =
      isMentionOnly && /^formulario:\d{2,6}[a-z]?$/i.test(String(citation?.reference_key || "").trim());
    const canOpenAsEtArticle =
      isMentionOnly && referenceKey === "et" && String(citation?.locator_start || "").trim();
    const canOpenAsLey =
      isMentionOnly && /^ley:\d+(?::\d{4})?$/.test(referenceKey);
    const externalUrl = String(citation?.external_url || "").trim();
    const fallbackUrl = String(citation?.external_fallback_url || "").trim();
    const tier = deriveSourceTierLabel(citation);
    const provider = citation.source_provider || citation.authority || "Sin documento en corpus";
    const title = citationTitleValue(citation) || "Referencia";

    let action: CitationItemViewModel["action"] = "modal";
    let hint = "";
    if (isMentionOnly && externalUrl && !canOpenByReference && !canOpenAsEtArticle && !canOpenAsLey) {
      action = "external";
      hint = "Abrir en normograma.mintic.gov.co";
    } else if (isMentionOnly && !canOpenByReference && !canOpenAsEtArticle && !canOpenAsLey) {
      action = "none";
    }
    // No hint for modal-action items (ET articles, Ley, Formulario).  The card
    // itself is a clickable trigger; extra text like "Abrir visor…" just adds
    // visual noise and makes the tab taller than it needs to be.

    return {
      action,
      externalHint: action === "external" ? hint : "",
      externalUrl: externalUrl || null,
      fallbackUrl: action === "external" && fallbackUrl ? fallbackUrl : null,
      hint,
      id: citationId(citation),
      mentionOnly: isMentionOnly,
      meta: formatCitationMeta(tier, provider),
      rawCitation: citation as Record<string, unknown>,
      title,
    };
  }

  function collectCitationsFromQuestionEntry(entry: QuestionEntry) {
    if (!entry?.normativeSupport) return [];
    const ns = entry.normativeSupport;
    return mergeCitations(
      asCitationArray(ns.cachedCitations),
      asCitationArray(ns.mentionCitations),
    );
  }

  function buildThreadCitationGroups(questionEntries: QuestionEntry[]) {
    return questionEntries
      .map((entry, i) => ({
        label: `Chat ${i + 1}`,
        citations: collectCitationsFromQuestionEntry(entry),
      }))
      .filter(g => g.citations.length > 0);
  }

  function renderAccumulatedExpertPanel(
    questionEntries: QuestionEntry[],
    expertPanelContentNode: HTMLElement,
    expertPanelStatusNode: HTMLElement,
  ) {
    const entriesWithExperts = questionEntries
      .map((entry, i) => ({ label: `Chat ${i + 1}`, state: entry.expertPanelState }))
      .filter(e => e.state && e.state.status === "populated" && e.state.response &&
        typeof e.state.response === "object");

    if (entriesWithExperts.length <= 1) {
      return;
    }

    expertPanelContentNode.innerHTML = "";
    expertPanelStatusNode.textContent = "";
    expertPanelStatusNode.hidden = true;

    entriesWithExperts.forEach(({ label, state }) => {
      const divider = document.createElement("div");
      divider.className = "expert-group-divider";
      divider.textContent = label;
      expertPanelContentNode.appendChild(divider);

      const response = state.response;
      if (!response || typeof response !== "object") return;
      const groups = Array.isArray(response.groups) ? response.groups : [];
      const ungrouped = Array.isArray(response.ungrouped) ? response.ungrouped : [];
      const totalCards = groups.length + ungrouped.length;
      if (totalCards === 0) return;

      const summary = document.createElement("p");
      summary.className = "section-note";
      summary.textContent = `${totalCards} interpretación${totalCards === 1 ? "" : "es"}`;
      expertPanelContentNode.appendChild(summary);
    });
  }

  function renderCitationsGrouped(groups) {
    const rawCitations = groups.flatMap((group) => group.citations || []);
    rememberCitations(rawCitations);
    const viewGroups = groups
      .map((group, index) => ({
        id: `citation-group:${index}`,
        items: sortCitationsForDisplay(dedupeCitations(group.citations)).map(toCitationViewModel),
        label: group.label,
      }))
      .filter((group) => group.items.length > 0);
    renderCitationList(citationsList, viewGroups, {
      emptyLabel: "Sin normativa",
      onItemClick: (item) => {
        const rawCitation = lastCitationMap.get(item.id);
        if (rawCitation) openNormaModal(rawCitation);
      },
    });
    emitGroups(viewGroups, true);
  }

  function renderCitations(citations) {
    const rawCitations = Array.isArray(citations) ? citations : [];
    rememberCitations(rawCitations);
    const group = {
      id: "citation-group:current",
      items: sortCitationsForDisplay(dedupeCitations(rawCitations)).map(toCitationViewModel),
      label: "Actual",
    };
    renderCitationList(citationsList, [group], {
      emptyLabel: "Sin normativa",
      onItemClick: (item) => {
        const rawCitation = lastCitationMap.get(item.id);
        if (rawCitation) openNormaModal(rawCitation);
      },
    });
    emitGroups(group.items.length > 0 ? [group] : [], true);
  }

  /**
   * W2 Phase 7 — normativa preview during thinking.
   *
   * Called by `requestController.ts` when the backend emits a
   * `citations_preview` SSE event (between retrieval and compose). Renders a
   * muted, non-clickable snapshot of the retrieved citations so the panel can
   * feel responsive before the chat bubble lights up.
   *
   * Behavior:
   * - Reuses `sortCitationsForDisplay` + `dedupeCitations`, so the W1
   *   comparator applies automatically if it has landed.
   * - Forces `action: "none"` and `preview: true` on every view model, which
   *   the desktop renderer translates into the `.citation-preview` CSS class
   *   + no click handler.
   * - Deliberately does NOT call `emitGroups()` (which fires the
   *   `lia:citations-updated` event). Instead emits on a dedicated
   *   `lia:citations-preview` channel so mobile (which only listens to
   *   `lia:citations-updated`) stays blind to preview state.
   * - Does NOT populate `lastCitationMap`; that map is the openCitationById
   *   lookup table and must only hold authoritative, clickable citations.
   *
   * The final `renderCitations()` / `renderCitationsGrouped()` call on the
   * `final` SSE event overwrites the preview DOM atomically via
   * `renderCitationList` → `container.replaceChildren()`.
   */
  function renderCitationsPreview(candidates) {
    const rawCitations = Array.isArray(candidates) ? candidates : [];
    // Empty list = no-op. The backend only emits citations_preview AFTER
    // retrieval cleared EvidenceInsufficientError, so an empty payload would
    // be an upstream anomaly. We do NOT fall back to renderDeferredCitations-
    // State here because that path emits on lia:citations-updated (isFinal:
    // false), which would leak preview semantics into the mobile-facing
    // event channel. Leave the panel in whatever state the turn submit left
    // it (typically the "Cargando soporte normativo..." placeholder).
    if (rawCitations.length === 0) {
      return;
    }
    const sorted = sortCitationsForDisplay(dedupeCitations(rawCitations));
    const items: CitationItemViewModel[] = sorted.map((citation) => {
      const vm = toCitationViewModel(citation);
      return { ...vm, action: "none", preview: true };
    });
    const group: CitationGroupViewModel = {
      id: "citation-group:preview",
      items,
      label: "Soporte normativo (preliminar)",
    };
    renderCitationList(citationsList, [group], {
      emptyLabel: "Buscando soporte normativo...",
    });
    if (root) {
      emitUiEvent(root, UI_EVENT_CITATIONS_PREVIEW, { items });
    }
  }

  return {
    getLastGroups: () => lastGroups.slice(),
    openCitationById: (citationIdValue) => {
      const citation = lastCitationMap.get(String(citationIdValue || "").trim());
      if (citation) openNormaModal(citation);
    },
    setCitationsStatus,
    renderDeferredCitationsState,
    sortCitationsForDisplay,
    formatCitationMeta,
    collectCitationsFromQuestionEntry,
    buildThreadCitationGroups,
    renderAccumulatedExpertPanel,
    renderCitationsGrouped,
    renderCitations,
    renderCitationsPreview,
  };
}
