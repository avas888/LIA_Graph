import { describe, expect, it } from "vitest";
import {
  SPANISH_SMALL_WORDS,
  spanishTitleCase,
  titleCaseHeadings,
} from "@/shared/utils/spanishTextFormatters";

describe("SPANISH_SMALL_WORDS", () => {
  it("exposes connectors that should stay lowercase mid-sentence", () => {
    for (const word of ["de", "del", "en", "la", "los", "y", "o", "para"]) {
      expect(SPANISH_SMALL_WORDS.has(word)).toBe(true);
    }
  });
});

describe("spanishTitleCase", () => {
  it("capitalizes each word", () => {
    expect(spanishTitleCase("firmeza de las declaraciones tributarias")).toBe(
      "Firmeza de las Declaraciones Tributarias",
    );
  });

  it("keeps connectors lowercase mid-sentence", () => {
    expect(spanishTitleCase("compensación de pérdidas y descuentos")).toBe(
      "Compensación de Pérdidas y Descuentos",
    );
  });

  it("capitalizes the first word even if it is a connector", () => {
    expect(spanishTitleCase("de pérdidas fiscales")).toBe("De Pérdidas Fiscales");
  });

  it("preserves all-uppercase acronyms", () => {
    expect(spanishTitleCase("declaraciones DIAN y UVT")).toBe("Declaraciones DIAN y UVT");
  });

  it("preserves markdown emphasis markers", () => {
    expect(spanishTitleCase("**firmeza** de declaraciones")).toBe("**firmeza** de Declaraciones");
  });

  it("returns empty string for empty input", () => {
    expect(spanishTitleCase("")).toBe("");
  });

  it("tolerates null / undefined", () => {
    expect(spanishTitleCase(null as unknown as string)).toBe("");
    expect(spanishTitleCase(undefined as unknown as string)).toBe("");
  });
});

describe("titleCaseHeadings", () => {
  it("title-cases H1/H2/H3 headings only", () => {
    const md = [
      "# firmeza de declaraciones",
      "## compensación de pérdidas",
      "### plazo especial en el ET",
      "",
      "cuerpo del párrafo no se modifica",
    ].join("\n");
    const out = titleCaseHeadings(md);
    expect(out).toContain("# Firmeza de Declaraciones");
    expect(out).toContain("## Compensación de Pérdidas");
    // Acronyms stay uppercase when the input is already uppercase; small
    // words ("en", "el") stay lowercase mid-sentence.
    expect(out).toContain("### Plazo Especial en el ET");
    expect(out).toContain("cuerpo del párrafo no se modifica");
  });

  it("leaves H4–H6 headings untouched", () => {
    const md = "#### mantener";
    expect(titleCaseHeadings(md)).toBe("#### mantener");
  });

  it("handles empty input", () => {
    expect(titleCaseHeadings("")).toBe("");
  });
});
