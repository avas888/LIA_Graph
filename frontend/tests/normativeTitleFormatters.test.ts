import { describe, expect, it } from "vitest";
import {
  formatDecretoTitle,
  formatFormularioTitle,
  formatLeyTitle,
  formatResolucionTitle,
} from "@/features/chat/normative/normativeTitleFormatters";

describe("formatLeyTitle", () => {
  it("formats 'Ley N de YYYY' with no remainder", () => {
    expect(formatLeyTitle("Ley 1819 de 2016")).toBe("Ley 1819 de 2016");
  });

  it("formats with a remainder, title-casing it", () => {
    expect(formatLeyTitle("Ley 1819 de 2016: reforma tributaria estructural")).toBe(
      "Ley 1819 de 2016: Reforma Tributaria Estructural",
    );
  });

  it("normalizes leading ':' / '–' / ',' separators in the remainder", () => {
    expect(formatLeyTitle("Ley 1819 de 2016 – reforma tributaria")).toBe(
      "Ley 1819 de 2016: Reforma Tributaria",
    );
    expect(formatLeyTitle("Ley 1819 de 2016 , reforma tributaria")).toBe(
      "Ley 1819 de 2016: Reforma Tributaria",
    );
  });

  it("is case-insensitive on the 'Ley' literal", () => {
    expect(formatLeyTitle("ley 100 de 1993")).toBe("Ley 100 de 1993");
  });

  it("returns null when the input isn't a Ley reference", () => {
    expect(formatLeyTitle("Decreto 1625 de 2016")).toBeNull();
    expect(formatLeyTitle("Artículo 147 ET")).toBeNull();
    expect(formatLeyTitle("")).toBeNull();
  });
});

describe("formatDecretoTitle", () => {
  it("formats 'Decreto N de YYYY'", () => {
    expect(formatDecretoTitle("Decreto 1625 de 2016")).toBe("Decreto 1625 de 2016");
  });

  it("appends the title-cased remainder", () => {
    expect(formatDecretoTitle("Decreto 1625 de 2016 - dur tributario")).toBe(
      "Decreto 1625 de 2016: Dur Tributario",
    );
  });

  it("returns null for non-decreto input", () => {
    expect(formatDecretoTitle("Ley 100 de 1993")).toBeNull();
  });
});

describe("formatResolucionTitle", () => {
  it("formats 'Resolución N de YYYY' and normalizes accents", () => {
    expect(formatResolucionTitle("Resolución 233 de 2025")).toBe("Resolución 233 de 2025");
    expect(formatResolucionTitle("Resolucion 233 de 2025")).toBe("Resolución 233 de 2025");
  });

  it("appends a title-cased remainder", () => {
    expect(formatResolucionTitle("Resolución 233 de 2025: medios magnéticos")).toBe(
      "Resolución 233 de 2025: Medios Magnéticos",
    );
  });

  it("returns null for non-resolución input", () => {
    expect(formatResolucionTitle("Formulario 110")).toBeNull();
  });
});

describe("formatFormularioTitle", () => {
  it("formats 'Formulario NNN'", () => {
    expect(formatFormularioTitle("Formulario 110")).toBe("Formulario 110");
  });

  it("formats 'Formato NNN' preserving kind case", () => {
    expect(formatFormularioTitle("formato 2516")).toBe("Formato 2516");
  });

  it("appends a title-cased remainder after a separator", () => {
    expect(formatFormularioTitle("Formulario 110 - declaración renta juridicas")).toBe(
      "Formulario 110: Declaración Renta Juridicas",
    );
  });

  it("returns null when the input is not Formulario/Formato", () => {
    expect(formatFormularioTitle("Ley 100 de 1993")).toBeNull();
  });
});
