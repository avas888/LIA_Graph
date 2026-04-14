import { beforeEach, describe, expect, it, vi } from "vitest";
import { createCitationRenderer } from "@/features/chat/chatCitationRenderer";
import {
  UI_EVENT_CITATIONS_PREVIEW,
  UI_EVENT_CITATIONS_UPDATED,
} from "@/shared/ui/patterns/uiEvents";

/**
 * W2 Phase 7 — desktop normativa preview renderer.
 *
 * These tests lock the four invariants required by the plan in
 * `docs/next/soporte_normativo_citation_ordering.md` §12:
 *
 *   1. `renderCitationsPreview` produces items with `action: "none"` and
 *      `preview: true`, rendered into the DOM under the
 *      `.citation-preview` CSS class.
 *   2. Preview items are non-interactive — no `.citation-trigger` button, no
 *      click handler bound.
 *   3. A subsequent `renderCitations(finalList)` atomically overwrites the
 *      preview DOM (no leftover preview items).
 *   4. Preview emits on the dedicated `lia:citations-preview` channel and
 *      NOT on `lia:citations-updated` (which is reserved for final state and
 *      is what mobile subscribes to).
 */

describe("chat citation renderer — normativa preview (W2 Phase 7)", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
  });

  function mountRenderer() {
    const root = document.createElement("div");
    const citationsList = document.createElement("ul");
    root.appendChild(citationsList);
    document.body.appendChild(root);
    const openNormaModal = vi.fn();
    const renderer = createCitationRenderer({
      citationsList,
      citationsStatusNode: null,
      openNormaModal,
      root,
    });
    return { renderer, root, citationsList, openNormaModal };
  }

  function makePreviewCandidate(overrides: Record<string, unknown> = {}): Record<string, unknown> {
    // Every candidate needs distinct identity fields so `dedupeCitations`
    // (which matches on reference_key, doc_id, logical_doc_id, and
    // legal_reference) keeps them separate. citationTitleValue() prefers
    // source_label > legal_reference > title, so the rendered title comes
    // from whichever of those is set on the candidate.
    const referenceKey = String(overrides.reference_key || "resolucion_dian:233:2025");
    const humanTitle = String(overrides.title || "Resolución 233 de 2025");
    const derivedDocId = `co_${referenceKey.replace(/:/g, "_")}`;
    return {
      title: humanTitle,
      // Use the same human-readable string for legal_reference so
      // citationTitleValue() picks it up deterministically and the rendered
      // DOM title matches the input.
      legal_reference: humanTitle,
      reference_type: "resolucion_dian",
      reference_key: referenceKey,
      doc_id: derivedDocId,
      source_provider: "DIAN",
      authority: "DIAN",
      ...overrides,
    };
  }

  it("renders preview items as muted, non-clickable placeholders", () => {
    const { renderer, citationsList } = mountRenderer();

    renderer.renderCitationsPreview([
      makePreviewCandidate({ title: "Resolución 233 de 2025", reference_key: "resolucion_dian:233:2025" }),
      makePreviewCandidate({ title: "Resolución 162 de 2023", reference_key: "resolucion_dian:162:2023" }),
    ]);

    const previewItems = citationsList.querySelectorAll("li.citation-preview");
    expect(previewItems.length).toBe(2);

    // Invariant #2: preview items render as a DISABLED button so the tab size
    // is identical between preview and final (no layout shift). No click
    // handler is bound, and the li has pointer-events: none as a guard.
    for (const li of previewItems) {
      expect(li.querySelector("a.citation-external-link")).toBeNull();
      expect(li.getAttribute("aria-disabled")).toBe("true");
      const btn = li.querySelector("button.citation-trigger") as HTMLButtonElement | null;
      expect(btn).not.toBeNull();
      expect(btn!.disabled).toBe(true);
      expect(btn!.textContent).toMatch(/Resolución \d+ de \d{4}/);
    }
  });

  it("emits lia:citations-preview but NOT lia:citations-updated", () => {
    const { renderer, root } = mountRenderer();

    const previewListener = vi.fn();
    const updatedListener = vi.fn();
    root.addEventListener(UI_EVENT_CITATIONS_PREVIEW, previewListener);
    root.addEventListener(UI_EVENT_CITATIONS_UPDATED, updatedListener);

    renderer.renderCitationsPreview([makePreviewCandidate()]);

    expect(previewListener).toHaveBeenCalledTimes(1);
    expect(updatedListener).not.toHaveBeenCalled();

    const [previewEvent] = previewListener.mock.calls[0] as [CustomEvent];
    expect(previewEvent.type).toBe(UI_EVENT_CITATIONS_PREVIEW);
    const detail = previewEvent.detail as { items: Array<{ action: string; preview: boolean; title: string }> };
    expect(Array.isArray(detail.items)).toBe(true);
    expect(detail.items.length).toBe(1);
    expect(detail.items[0].action).toBe("none");
    expect(detail.items[0].preview).toBe(true);
  });

  it("is overwritten atomically by a subsequent renderCitations() call", () => {
    const { renderer, citationsList } = mountRenderer();

    renderer.renderCitationsPreview([
      makePreviewCandidate({ title: "Resolución 233 de 2025", reference_key: "resolucion_dian:233:2025" }),
      makePreviewCandidate({ title: "Resolución 162 de 2023", reference_key: "resolucion_dian:162:2023" }),
    ]);
    expect(citationsList.querySelectorAll("li.citation-preview").length).toBe(2);

    // Simulate the `final` SSE event arriving: renderCitations takes over.
    renderer.renderCitations([
      {
        title: "Resolución 233 de 2025",
        reference_key: "resolucion_dian:233:2025",
        reference_type: "resolucion_dian",
        doc_id: "co_res_dian_233_2025",
        legal_reference: "Resolución DIAN 000233 de 2025",
        source_provider: "DIAN",
        authority: "DIAN",
      },
    ]);

    // Invariant #3: no preview items linger after the final render.
    expect(citationsList.querySelectorAll("li.citation-preview").length).toBe(0);
    // And the final render produces a regular clickable item.
    const triggers = citationsList.querySelectorAll("button.citation-trigger");
    expect(triggers.length).toBe(1);
  });

  it("is a no-op for an empty candidate list (no DOM changes, no events)", () => {
    const { renderer, citationsList, root } = mountRenderer();

    // Seed the panel with some known content so we can detect unwanted
    // clobbering. A dummy LI that does not belong to any preview path.
    const seed = document.createElement("li");
    seed.className = "existing-sentinel";
    seed.textContent = "untouched";
    citationsList.appendChild(seed);

    const previewListener = vi.fn();
    const updatedListener = vi.fn();
    root.addEventListener(UI_EVENT_CITATIONS_PREVIEW, previewListener);
    root.addEventListener(UI_EVENT_CITATIONS_UPDATED, updatedListener);

    renderer.renderCitationsPreview([]);

    // Empty input is a no-op: no preview class, no placeholder swap, no
    // events on either channel. The existing sentinel is still in the DOM.
    expect(citationsList.querySelectorAll("li.citation-preview").length).toBe(0);
    expect(citationsList.querySelector("li.existing-sentinel")).not.toBeNull();
    expect(previewListener).not.toHaveBeenCalled();
    expect(updatedListener).not.toHaveBeenCalled();
  });

  it("does not populate the openCitationById lookup for preview items", () => {
    const { renderer, openNormaModal } = mountRenderer();

    renderer.renderCitationsPreview([
      makePreviewCandidate({
        doc_id: "co_res_dian_preview_probe",
        reference_key: "resolucion_dian:233:2025",
      }),
    ]);

    // Preview items must not leak into the click-through lookup map — that
    // map is the authoritative source for opening a normative modal, and
    // preview items are non-authoritative by design.
    renderer.openCitationById("co_res_dian_preview_probe");
    renderer.openCitationById("resolucion_dian:233:2025");
    expect(openNormaModal).not.toHaveBeenCalled();
  });
});
