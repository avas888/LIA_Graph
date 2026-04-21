import { describe, expect, it } from "vitest";
import {
  buildElevatorSummary,
  cleanModalTitle,
  sanitizeExpertText,
  splitTitleAndTopic,
  stripInternalDocCode,
  stripTemaPrincipalTail,
} from "@/features/chat/expertSummaryText";

describe("stripInternalDocCode", () => {
  it("removes a FIR-E01 prefix", () => {
    expect(stripInternalDocCode("FIR-E01 — Firmeza de las declaraciones")).toBe(
      "Firmeza de las declaraciones",
    );
  });

  it("removes a PER-E01 prefix", () => {
    expect(stripInternalDocCode("PER-E01 — Pérdidas fiscales")).toBe("Pérdidas fiscales");
  });

  it("removes an inline doc code that survived concatenation", () => {
    expect(
      stripInternalDocCode("Firmeza de declaraciones. PER-E01 — Pérdidas fiscales"),
    ).toContain("Pérdidas fiscales");
    expect(
      stripInternalDocCode("Firmeza de declaraciones. PER-E01 — Pérdidas fiscales"),
    ).not.toContain("PER-E01");
  });

  it("leaves text without any doc code untouched", () => {
    expect(stripInternalDocCode("Ambito de aplicación y soportes")).toBe(
      "Ambito de aplicación y soportes",
    );
  });

  it("returns empty string for empty input", () => {
    expect(stripInternalDocCode("")).toBe("");
  });
});

describe("stripTemaPrincipalTail", () => {
  it("drops a 'Tema principal: X' tail", () => {
    expect(
      stripTemaPrincipalTail(
        "Firmeza de las declaraciones Tema principal: plazos generales y especiales",
      ),
    ).toBe("Firmeza de las declaraciones");
  });

  it("drops the tail even with a leading colon separator", () => {
    expect(
      stripTemaPrincipalTail("Interpretaciones: Tema principal: compensación de pérdidas"),
    ).toBe("Interpretaciones");
  });

  it("leaves sentences mentioning 'tema' but not the label intact", () => {
    expect(stripTemaPrincipalTail("El tema más controversial es el plazo")).toBe(
      "El tema más controversial es el plazo",
    );
  });

  it("returns empty string for empty input", () => {
    expect(stripTemaPrincipalTail("")).toBe("");
  });
});

describe("sanitizeExpertText", () => {
  it("composes both strippers", () => {
    const raw =
      "FIR-E01 — Firmeza de las Declaraciones Tributarias: Interpretaciones sobre Plazos Tema principal: Firmeza de declaraciones tributarias — plazos generales y especiales,";
    const cleaned = sanitizeExpertText(raw);
    expect(cleaned).not.toContain("FIR-E01");
    expect(cleaned).not.toContain("Tema principal");
    expect(cleaned).toContain("Firmeza de las Declaraciones Tributarias");
  });

  it("normalizes whitespace", () => {
    expect(sanitizeExpertText("  ambito   de   aplicación  ")).toBe("ambito de aplicación");
  });
});

describe("splitTitleAndTopic", () => {
  it("splits '<title> Tema principal: <topic>' into two parts", () => {
    const { title, topic } = splitTitleAndTopic(
      "FIR-E01 — Firmeza de las Declaraciones: Interpretaciones sobre Plazos Tema principal: plazos generales",
    );
    expect(title).toContain("Firmeza de las Declaraciones");
    expect(title).not.toContain("FIR-E01");
    expect(topic).toBe("plazos generales");
  });

  it("returns empty topic when 'Tema principal' is absent", () => {
    const { title, topic } = splitTitleAndTopic("FIR-E01 — Firmeza de las Declaraciones");
    expect(title).toBe("Firmeza de las Declaraciones");
    expect(topic).toBe("");
  });

  it("returns empty fields for empty input", () => {
    expect(splitTitleAndTopic("")).toEqual({ title: "", topic: "" });
  });
});

describe("buildElevatorSummary", () => {
  it("returns the first two sentences from snippet", () => {
    const out = buildElevatorSummary({
      snippet:
        "La compensación de pérdidas está sujeta a la regla del artículo 147. El límite anual no aplica bajo la ley vigente. Cualquier duda debe documentarse.",
    });
    expect(out).toContain("La compensación");
    expect(out).toContain("El límite anual");
    // The third sentence is NOT included — cap is two sentences.
    expect(out).not.toContain("Cualquier duda");
  });

  it("prefers extended_excerpt over snippet when available", () => {
    const out = buildElevatorSummary({
      extended_excerpt:
        "Los plazos especiales aplican cuando se compensan pérdidas. Prorroga a seis años el término de firmeza.",
      snippet:
        "FIR-E01 — Firmeza de las Declaraciones Tributarias Tema principal: plazos generales",
    });
    expect(out).toContain("Los plazos especiales");
    expect(out).not.toContain("FIR-E01");
  });

  it("falls back to card_summary when snippet/extended are empty", () => {
    const out = buildElevatorSummary({
      card_summary:
        "Aporta criterio profesional sobre compensación de pérdidas fiscales aterrizado al caso.",
    });
    expect(out).toContain("compensación de pérdidas");
  });

  it("strips doc codes and Tema principal tail from the output", () => {
    const out = buildElevatorSummary({
      snippet:
        "FIR-E01 — La compensación está sujeta a la regla. Tema principal: plazos generales y especiales",
    });
    expect(out).not.toContain("FIR-E01");
    expect(out).not.toContain("Tema principal");
  });

  it("returns empty string when no usable candidate exists", () => {
    const out = buildElevatorSummary({ snippet: "", card_summary: "", extended_excerpt: "" });
    expect(out).toBe("");
  });

  it("clips output to maxChars", () => {
    const long = "a".repeat(300) + ". " + "b".repeat(300) + ".";
    const out = buildElevatorSummary({ snippet: long }, 120);
    expect(out.length).toBeLessThanOrEqual(120);
  });
});

describe("cleanModalTitle", () => {
  it("leaves short clean headings untouched", () => {
    expect(cleanModalTitle("Firmeza de las Declaraciones Tributarias")).toBe(
      "Firmeza de las Declaraciones Tributarias",
    );
  });

  it("cuts a paragraph heading before a Spanish prose-starter clause", () => {
    const raw =
      "Posicion Normativa — Referencia Rapida Los INCRNGO son ingresos que, reuniendo las condiciones para ser gravables, han sido excluidos de la base gravable por norma expresa del ET.";
    expect(cleanModalTitle(raw)).toBe("Posicion Normativa — Referencia Rapida");
  });

  it("prefers the first sentence when no prose-starter pattern matches", () => {
    const raw =
      "Compensación de pérdidas bajo el art. 147 del Estatuto Tributario. El régimen fija el término vigente para aplicar pérdidas acumuladas.";
    const out = cleanModalTitle(raw, 80);
    expect(out).toBe("Compensación de pérdidas bajo el art. 147 del Estatuto Tributario");
  });

  it("hard-caps long titles on a word boundary with ellipsis as a last resort", () => {
    const raw = "Interpretación profesional ".repeat(40);
    const out = cleanModalTitle(raw, 100);
    expect(out.length).toBeLessThanOrEqual(100);
    expect(out.endsWith("…")).toBe(true);
    expect(out).not.toMatch(/Interpretación\s$/);
  });

  it("strips internal doc codes before trimming", () => {
    const raw =
      "FIR-E01 — Firmeza de las Declaraciones Tributarias Los plazos especiales aplican cuando se compensan pérdidas, prorrogando el término a seis años.";
    const out = cleanModalTitle(raw);
    expect(out).not.toContain("FIR-E01");
    expect(out.startsWith("Firmeza")).toBe(true);
  });

  it("returns empty string for empty input", () => {
    expect(cleanModalTitle("")).toBe("");
    expect(cleanModalTitle("   ")).toBe("");
  });
});
