import { beforeEach, describe, expect, it, vi } from "vitest";
import { createCitationRenderer } from "@/features/chat/chatCitationRenderer";

/**
 * W1 Phase 1 — family-aware + year-aware citation sort.
 *
 * Locks the four invariants from
 * `docs/next/soporte_normativo_citation_ordering.md` §3.4:
 *
 *   1. Rule A — within a dated family (resoluciones, leyes, decretos),
 *      sort issuance year descending (latest first).
 *   2. Rule B default — across families, operational norms
 *      (resolucion → circular → concepto → decreto → ley → et → formulario)
 *      come before foundational ones; retriever order is preserved within a
 *      family that lacks an issuance year.
 *   3. Corpus-context still wins — doc_id-bearing items beat mention-only
 *      items regardless of family rank.
 *   4. Missing `reference_type` — title-prefix fallback + year regex on
 *      `legal_reference` / `title` still classify a citation correctly.
 *
 * Tests access the sort via `createCitationRenderer({...stub deps})
 * .sortCitationsForDisplay(...)` — no module-level hoist needed.
 */

describe("sortCitationsForDisplay — W1 Rules A + B", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
  });

  function makeSort() {
    const root = document.createElement("div");
    const citationsList = document.createElement("ul");
    root.appendChild(citationsList);
    document.body.appendChild(root);
    const renderer = createCitationRenderer({
      citationsList,
      citationsStatusNode: null,
      openNormaModal: vi.fn(),
      root,
    });
    return renderer.sortCitationsForDisplay;
  }

  function resolucion(year: number, number: number): Record<string, unknown> {
    return {
      doc_id: `co_res_dian_${number}_${year}`,
      reference_type: "resolucion_dian",
      reference_key: `resolucion_dian:${number}:${year}`,
      legal_reference: `Resolución ${number} de ${year}`,
      title: `Resolución ${number} de ${year}`,
      source_provider: "DIAN",
      authority: "DIAN",
    };
  }

  function ley(year: number, number: number): Record<string, unknown> {
    return {
      doc_id: `co_ley_${number}_${year}`,
      reference_type: "ley",
      reference_key: `ley:${number}:${year}`,
      legal_reference: `Ley ${number} de ${year}`,
      title: `Ley ${number} de ${year}`,
      source_provider: "Congreso",
      authority: "Congreso",
    };
  }

  function etArticle(article: number): Record<string, unknown> {
    return {
      doc_id: `co_et_art_${article}`,
      reference_type: "et",
      reference_key: "et",
      legal_reference: `Estatuto Tributario Art. ${article}`,
      title: `Estatuto Tributario, Art. ${article}`,
      locator_start: String(article),
      source_provider: "DIAN",
      authority: "DIAN",
    };
  }

  function decreto(year: number, number: number): Record<string, unknown> {
    return {
      doc_id: `co_decreto_${number}_${year}`,
      reference_type: "decreto",
      reference_key: `decreto:${number}:${year}`,
      legal_reference: `Decreto ${number} de ${year}`,
      title: `Decreto ${number} de ${year}`,
      source_provider: "Presidencia",
      authority: "Presidencia",
    };
  }

  it("Rule A — within resolucion_dian family, 2025 beats 2023", () => {
    const sortCitationsForDisplay = makeSort();
    const input = [resolucion(2023, 162), resolucion(2025, 233)];
    const out = sortCitationsForDisplay(input);
    expect(out.map((c) => c.reference_key)).toEqual([
      "resolucion_dian:233:2025",
      "resolucion_dian:162:2023",
    ]);
  });

  it("Rule B default — mixed input orders by [res→ley→et], preserving ET retriever order", () => {
    const sortCitationsForDisplay = makeSort();
    // Input order is deliberately shuffled to stress both the family rank
    // and the Rule-B-within-family insertion-index tiebreak for ET items.
    const input = [
      etArticle(634), // index 0 — should stay first among ETs
      resolucion(2023, 162),
      etArticle(641), // index 2 — should stay second among ETs
      ley(2016, 1819),
      resolucion(2025, 233),
    ];
    const out = sortCitationsForDisplay(input);
    expect(out.map((c) => c.reference_key)).toEqual([
      "resolucion_dian:233:2025",
      "resolucion_dian:162:2023",
      "ley:1819:2016",
      "et", // art 634
      "et", // art 641
    ]);
    // Confirm ET items preserved insertion order via locator_start.
    const etSlice = out.slice(3);
    expect(etSlice.map((c) => c.locator_start)).toEqual(["634", "641"]);
  });

  it("Rule B — decreto beats ley (operational before foundational)", () => {
    const sortCitationsForDisplay = makeSort();
    const input = [ley(2016, 1819), decreto(2013, 1070)];
    const out = sortCitationsForDisplay(input);
    expect(out.map((c) => c.reference_type)).toEqual(["decreto", "ley"]);
  });

  it("corpus-context still wins over family rank", () => {
    const sortCitationsForDisplay = makeSort();
    // A mention-only resolucion (no doc_id OR mention_only=true) must NOT
    // beat a corpus-backed ET article, even though resolucion_dian has a
    // lower (better) family rank than et.
    const mentionOnlyResolucion = {
      reference_type: "resolucion_dian",
      reference_key: "resolucion_dian:233:2025",
      legal_reference: "Resolución 233 de 2025",
      title: "Resolución 233 de 2025",
      mention_only: true,
      // NO doc_id → fails citationHasCorpusContext
    };
    const corpusEtArticle = etArticle(634);
    const input = [mentionOnlyResolucion, corpusEtArticle];
    const out = sortCitationsForDisplay(input);
    expect(out[0].reference_type).toBe("et");
    expect(out[1].reference_type).toBe("resolucion_dian");
  });

  it("falls back to title-prefix + year-in-text when reference_type is missing", () => {
    const sortCitationsForDisplay = makeSort();
    // No reference_type field — the comparator must recover rank 0 from the
    // "Resolución …" title prefix and year 2025 from the "de 2025" text.
    const titleOnlyResolucion = {
      doc_id: "co_res_dian_fallback_233_2025",
      legal_reference: "Resolución 233 de 2025",
      title: "Resolución 233 de 2025",
      source_provider: "DIAN",
    };
    const input = [etArticle(634), titleOnlyResolucion];
    const out = sortCitationsForDisplay(input);
    // Fallback-classified resolucion must sort before the ET article.
    expect(out[0].title).toBe("Resolución 233 de 2025");
    expect(out[1].reference_type).toBe("et");
  });

  it("year 0 (missing) sorts LAST within its own family", () => {
    const sortCitationsForDisplay = makeSort();
    // Two resoluciones: one with a year, one without. The year-bearing one
    // must win regardless of insertion order.
    const withoutYear = {
      doc_id: "co_res_dian_no_year",
      reference_type: "resolucion_dian",
      reference_key: "resolucion_dian:000:",
      legal_reference: "Resolución sin fecha",
      title: "Resolución sin fecha",
      source_provider: "DIAN",
    };
    const withYear = resolucion(2024, 100);
    // Put withoutYear first in insertion order to prove year desc beats index asc.
    const out = sortCitationsForDisplay([withoutYear, withYear]);
    expect(out[0].reference_key).toBe("resolucion_dian:100:2024");
    expect(out[1].reference_key).toBe("resolucion_dian:000:");
  });
});
