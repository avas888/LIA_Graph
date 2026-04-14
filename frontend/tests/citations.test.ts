import { describe, expect, it } from "vitest";

import {
  extractMentionCitations,
  mergeCitations,
  resolveExternalNormativeUrl,
} from "../src/features/chat/citations";
import { citationTitleValue, formatNormativeCitationTitle } from "../src/features/chat/normativeModals";

describe("citation mention parsing", () => {
  it("treats colombian hyphenated ET articles as a single locator", () => {
    const citations = extractMentionCitations("Aplica el ET art. 689-3 para el beneficio de auditoría.");
    const etCitation = citations.find((citation) => citation.reference_key === "et");

    expect(etCitation).toBeTruthy();
    expect(etCitation?.locator_start).toBe("689-3");
    expect(etCitation?.locator_end).toBeUndefined();
    expect(etCitation?.source_label).toBe("ET art. 689-3");
  });

  it("canonicalizes dotted ET inserted articles to the colombian hyphen form", () => {
    const citations = extractMentionCitations("Aplica el ET art. 689.3 para el beneficio de auditoría.");
    const etCitation = citations.find((citation) => citation.reference_key === "et");

    expect(etCitation).toBeTruthy();
    expect(etCitation?.locator_start).toBe("689-3");
    expect(etCitation?.locator_end).toBeUndefined();
    expect(etCitation?.source_label).toBe("ET art. 689-3");
  });

  it("keeps colombian article ranges only when they use an explicit connector", () => {
    const citations = extractMentionCitations("El SIMPLE se regula en el ET art. 903 a 916.");
    const etCitation = citations.find((citation) => citation.reference_key === "et");

    expect(etCitation).toBeTruthy();
    expect(etCitation?.locator_start).toBe("903");
    expect(etCitation?.locator_end).toBe("916");
    expect(etCitation?.source_label).toBe("ET arts. 903 a 916");
  });

  it("supports the colombian al connector but does not turn article lists into ranges", () => {
    const ranged = extractMentionCitations("Revise el ET art. 107 al 108 antes del cierre.");
    const listed = extractMentionCitations("Revise el ET art. 107 y 108 antes del cierre.");
    const rangedEt = ranged.find((citation) => citation.reference_key === "et");
    const listedEt = listed.find((citation) => citation.reference_key === "et");

    expect(rangedEt?.locator_start).toBe("107");
    expect(rangedEt?.locator_end).toBe("108");
    expect(listedEt?.locator_start).toBe("107");
    expect(listedEt?.locator_end).toBeUndefined();
  });

  it("extracts ET tail-form article mentions introduced with del Estatuto Tributario", () => {
    const citations = extractMentionCitations(
      "Según el Artículo 179 del Estatuto Tributario y el Artículo 196 del Estatuto Tributario, " +
        "la utilidad se depura con base en el Artículo 300 del Estatuto Tributario. " +
        "Además, revise el Artículo 73 del ET y el Artículo 281 del Estatuto Tributario. " +
        "Luego valide el Formulario 110."
    );

    const etLocators = citations
      .filter((citation) => citation.reference_key === "et")
      .map((citation) => citation.locator_start)
      .sort();

    expect(etLocators).toEqual(["179", "196", "281", "300", "73"]);
    expect(citations.some((citation) => citation.reference_key === "formulario:110")).toBe(true);
    expect(citations.some((citation) => citation.reference_key === "et" && citation.source_label === "Estatuto Tributario")).toBe(false);
  });

  it("extracts ET head-form article mentions introduced with coma after Estatuto Tributario", () => {
    const citations = extractMentionCitations(
      "Esto se fundamenta en el Estatuto Tributario, artículo 179. " +
        "Base legal: Estatuto Tributario, artículo 300. " +
        "Según el Estatuto Tributario, artículo 196. " +
        "Además, revise el Formulario 110."
    );

    const etLocators = citations
      .filter((citation) => citation.reference_key === "et")
      .map((citation) => citation.locator_start)
      .sort();

    expect(etLocators).toEqual(["179", "196", "300"]);
    expect(citations.some((citation) => citation.reference_key === "formulario:110")).toBe(true);
    expect(citations.some((citation) => citation.reference_key === "et" && citation.source_label === "Estatuto Tributario")).toBe(false);
  });

  it("extracts DUR tail-form article mentions introduced with del DUR 1625", () => {
    const citations = extractMentionCitations("Revise el Artículo 1.6.1.13.2.11 del DUR 1625 de 2016.");
    const durCitation = citations.find((citation) => citation.reference_key === "dur:1625:2016");

    expect(durCitation).toBeTruthy();
    expect(durCitation?.locator_start).toBe("1.6.1.13.2.11");
  });

  it("merges ET dotted and hyphenated inserted article variants into one citation identity", () => {
    const merged = mergeCitations(
      [
        {
          source_label: "Estatuto Tributario, Artículos 689.3",
          legal_reference: "Estatuto Tributario, Artículos 689.3",
          reference_key: "et",
          locator_text: "Artículos 689.3",
          locator_kind: "articles",
          locator_start: "689.3",
          usage_context: "Citado en la respuesta.",
        },
      ],
      extractMentionCitations("ET art. 689-3")
    );

    expect(merged).toHaveLength(1);
  });

  it("merges ET singular and plural locator metadata into one citation identity", () => {
    const merged = mergeCitations(
      [
        {
          doc_id: "doc_et",
          source_label: "Estatuto Tributario",
          legal_reference: "Estatuto Tributario",
          reference_key: "et",
          locator_text: "Artículo 259",
          locator_kind: "article",
          locator_start: "259",
          usage_context: "Artículo 259 del Estatuto Tributario.",
        },
      ],
      extractMentionCitations("Revisa el artículo 259 del Estatuto Tributario.")
    );

    expect(merged).toHaveLength(1);
    expect(merged[0]?.doc_id).toBe("doc_et");
    expect(merged[0]?.mention_only).toBe(false);
  });

  it("formats ET titles with a canonical Estatuto Tributario label", () => {
    expect(formatNormativeCitationTitle("ET art. 689.3")).toBe("Estatuto Tributario, Artículo 689-3");
    expect(formatNormativeCitationTitle("Estatuto Tributario Artículo 54")).toBe(
      "Estatuto Tributario, Artículo 54"
    );
    expect(formatNormativeCitationTitle("ET arts. 54 a 62")).toBe("Estatuto Tributario, Artículos 54 - 62");
    expect(formatNormativeCitationTitle("Estatuto Tributario, Artículos 54 y 55-b")).toBe(
      "Estatuto Tributario, Artículos 54, 55-b"
    );
  });

  it("extracts bare article references without explicit ET context as ET citations", () => {
    // LLM responses often use "artículo N" without "del ET" — in Colombian tax domain, default to ET
    const text =
      "El Estatuto Tributario, en su artículo 115-1, establece requisitos. " +
      "El artículo 634 regula intereses moratorios. " +
      "Según el artículo 585 del Estatuto Tributario se aplica intercambio.";
    const citations = extractMentionCitations(text);

    const art115 = citations.find((c) => c.locator_start === "115-1");
    expect(art115).toBeTruthy();
    expect(art115?.reference_key).toBe("et");

    const art634 = citations.find((c) => c.locator_start === "634");
    expect(art634).toBeTruthy();
    expect(art634?.reference_key).toBe("et");

    const art585 = citations.find((c) => c.locator_start === "585");
    expect(art585).toBeTruthy();
    expect(art585?.reference_key).toBe("et");

    // All three distinct articles should be present
    expect(citations.filter((c) => c.reference_key === "et").length).toBeGreaterThanOrEqual(3);
  });

  it("prefers locator metadata to render canonical ET titles", () => {
    expect(
      citationTitleValue({
        reference_key: "et",
        locator_text: "Artículos 260.11",
        locator_kind: "articles",
        locator_start: "260.11",
        source_label: "ET art. 260.11",
      })
    ).toBe("Estatuto Tributario, Artículo 260-11");
  });
});

describe("resolveExternalNormativeUrl", () => {
  it("resolves ET article to normograma anchor", () => {
    expect(resolveExternalNormativeUrl("et", "et", "121")).toBe(
      "https://normograma.mintic.gov.co/mintic/compilacion/docs/estatuto_tributario.htm#121"
    );
  });

  it("resolves ET hyphenated article", () => {
    expect(resolveExternalNormativeUrl("et", "et", "689-3")).toBe(
      "https://normograma.mintic.gov.co/mintic/compilacion/docs/estatuto_tributario.htm#689-3"
    );
  });

  it("resolves ET dotted article to hyphen form", () => {
    expect(resolveExternalNormativeUrl("et", "et", "260.11")).toBe(
      "https://normograma.mintic.gov.co/mintic/compilacion/docs/estatuto_tributario.htm#260-11"
    );
  });

  it("resolves ET without locator to base URL", () => {
    expect(resolveExternalNormativeUrl("et", "et", "")).toBe(
      "https://normograma.mintic.gov.co/mintic/compilacion/docs/estatuto_tributario.htm"
    );
  });

  it("resolves ley with year", () => {
    expect(resolveExternalNormativeUrl("ley:2010:2019", "ley", undefined)).toBe(
      "https://normograma.mintic.gov.co/mintic/compilacion/docs/ley_2010_2019.htm"
    );
  });

  it("resolves ley 1819 de 2016", () => {
    expect(resolveExternalNormativeUrl("ley:1819:2016", "ley", undefined)).toBe(
      "https://normograma.mintic.gov.co/mintic/compilacion/docs/ley_1819_2016.htm"
    );
  });

  it("resolves decreto with zero-padding", () => {
    expect(resolveExternalNormativeUrl("decreto:772:2020", "decreto", undefined)).toBe(
      "https://normograma.mintic.gov.co/mintic/compilacion/docs/decreto_0772_2020.htm"
    );
  });

  it("resolves 4-digit decreto without extra padding", () => {
    expect(resolveExternalNormativeUrl("decreto:2229:2023", "decreto", undefined)).toBe(
      "https://normograma.mintic.gov.co/mintic/compilacion/docs/decreto_2229_2023.htm"
    );
  });

  it("resolves DUR 1625", () => {
    expect(resolveExternalNormativeUrl("dur:1625:2016", undefined, undefined)).toBe(
      "https://normograma.mintic.gov.co/mintic/compilacion/docs/decreto_1625_2016.htm"
    );
  });

  it("returns null for unknown reference types", () => {
    expect(resolveExternalNormativeUrl("formulario:110", "formulario", undefined)).toBeNull();
  });

  it("returns null for empty reference key", () => {
    expect(resolveExternalNormativeUrl("", undefined, undefined)).toBeNull();
  });

  it("attaches external_url to mention-only ley citations", () => {
    const citations = extractMentionCitations("Se aplica la Ley 2010 de 2019 en este caso.");
    const leyCitation = citations.find((c) => c.reference_key === "ley:2010:2019");

    expect(leyCitation).toBeTruthy();
    expect(leyCitation?.external_url).toBe(
      "https://normograma.mintic.gov.co/mintic/compilacion/docs/ley_2010_2019.htm"
    );
    expect(leyCitation?.source_provider).toBe("Normograma DIAN");
  });

  it("attaches external_url to mention-only ET article citations", () => {
    const citations = extractMentionCitations("Según el ET art. 589 se permite corregir.");
    const etCitation = citations.find((c) => c.reference_key === "et");

    expect(etCitation).toBeTruthy();
    expect(etCitation?.external_url).toBe(
      "https://normograma.mintic.gov.co/mintic/compilacion/docs/estatuto_tributario.htm#589"
    );
  });
});
