import { describe, expect, it } from "vitest";
import {
  canonicalizeEtArticleToken,
  expandArticleRange,
  formatParsedEtLocator,
  normalizeNormaBulletText,
  parseEtLocatorText,
  parseEtTitle,
  sanitizeHref,
  shouldForceNormaBullets,
  splitNormaTextItems,
  toSpanishTitleCase,
  isRenderableEvidenceStatus,
} from "@/features/chat/normative/citationParsing";
import {
  citationTitleValue,
  deriveSourceTierLabel,
  formatNormativeCitationTitle,
} from "@/features/chat/normativeModals";

// ---------------------------------------------------------------------------
// sanitizeHref
// ---------------------------------------------------------------------------
describe("sanitizeHref", () => {
  it("allows relative paths", () => {
    expect(sanitizeHref("/source-view?doc_id=x")).toBe("/source-view?doc_id=x");
  });

  it("allows https", () => {
    expect(sanitizeHref("https://www.dian.gov.co")).toBe("https://www.dian.gov.co");
  });

  it("allows mailto", () => {
    expect(sanitizeHref("mailto:x@y.com")).toBe("mailto:x@y.com");
  });

  it("blocks javascript:", () => {
    expect(sanitizeHref("javascript:alert(1)")).toBe("");
  });

  it("blocks data:", () => {
    expect(sanitizeHref("data:text/html,<h1>x</h1>")).toBe("");
  });

  it("returns empty for null/empty", () => {
    expect(sanitizeHref("")).toBe("");
    expect(sanitizeHref(null)).toBe("");
  });
});

// ---------------------------------------------------------------------------
// normalizeNormaBulletText
// ---------------------------------------------------------------------------
describe("normalizeNormaBulletText", () => {
  it("strips bullet prefix", () => {
    expect(normalizeNormaBulletText("- Hello")).toBe("Hello.");
  });

  it("collapses whitespace", () => {
    expect(normalizeNormaBulletText("  hello   world  ")).toBe("hello world.");
  });

  it("preserves trailing punctuation", () => {
    expect(normalizeNormaBulletText("done!")).toBe("done!");
    expect(normalizeNormaBulletText("ok?")).toBe("ok?");
  });

  it("adds period if missing", () => {
    expect(normalizeNormaBulletText("hello")).toBe("hello.");
  });

  it("returns empty for empty input", () => {
    expect(normalizeNormaBulletText("")).toBe("");
  });
});

// ---------------------------------------------------------------------------
// splitNormaTextItems
// ---------------------------------------------------------------------------
describe("splitNormaTextItems", () => {
  it("splits on newlines", () => {
    expect(splitNormaTextItems("a\nb")).toHaveLength(2);
  });

  it("splits on semicolons when single line", () => {
    expect(splitNormaTextItems("a; b; c")).toHaveLength(3);
  });

  it("splits on sentences when single line", () => {
    const result = splitNormaTextItems("First sentence. Second sentence. Third.");
    expect(result.length).toBeGreaterThanOrEqual(2);
  });

  it("returns single item for simple text", () => {
    expect(splitNormaTextItems("hello")).toEqual(["hello."]);
  });

  it("returns empty for empty input", () => {
    expect(splitNormaTextItems("")).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// shouldForceNormaBullets
// ---------------------------------------------------------------------------
describe("shouldForceNormaBullets", () => {
  it("returns true for known labels", () => {
    expect(shouldForceNormaBullets("Para qué sirve")).toBe(true);
    expect(shouldForceNormaBullets("Normas base")).toBe(true);
  });

  it("returns true for pattern matches", () => {
    expect(shouldForceNormaBullets("Ámbito de aplicación general")).toBe(true);
  });

  it("returns false for unknown labels", () => {
    expect(shouldForceNormaBullets("random label")).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// isRenderableEvidenceStatus
// ---------------------------------------------------------------------------
describe("isRenderableEvidenceStatus", () => {
  it("returns true for valid statuses", () => {
    expect(isRenderableEvidenceStatus("verified")).toBe(true);
    expect(isRenderableEvidenceStatus("missing")).toBe(true);
    expect(isRenderableEvidenceStatus("")).toBe(true);
    expect(isRenderableEvidenceStatus(null)).toBe(true);
  });

  it("returns false for unknown statuses", () => {
    expect(isRenderableEvidenceStatus("pending")).toBe(false);
    expect(isRenderableEvidenceStatus("unknown_status")).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// canonicalizeEtArticleToken
// ---------------------------------------------------------------------------
describe("canonicalizeEtArticleToken", () => {
  it("passes through simple numbers", () => {
    expect(canonicalizeEtArticleToken("240")).toBe("240");
  });

  it("normalizes dots to dashes", () => {
    expect(canonicalizeEtArticleToken("335.1")).toBe("335-1");
  });

  it("normalizes em-dash to dash", () => {
    expect(canonicalizeEtArticleToken("335—1")).toBe("335-1");
  });

  it("handles letter suffix", () => {
    expect(canonicalizeEtArticleToken("240A")).toBe("240-a");
    expect(canonicalizeEtArticleToken("240-A")).toBe("240-a");
  });

  it("returns empty for empty", () => {
    expect(canonicalizeEtArticleToken("")).toBe("");
  });
});

// ---------------------------------------------------------------------------
// expandArticleRange
// ---------------------------------------------------------------------------
describe("expandArticleRange", () => {
  it("expands simple integer range", () => {
    expect(expandArticleRange("20", "23")).toEqual(["20", "21", "22", "23"]);
  });

  it("expands sub-article range", () => {
    expect(expandArticleRange("335-1", "335-3")).toEqual(["335-1", "335-2", "335-3"]);
  });

  it("returns null for reversed range", () => {
    expect(expandArticleRange("25", "20")).toBeNull();
  });

  it("returns null for too-large range", () => {
    expect(expandArticleRange("1", "100")).toBeNull();
  });

  it("returns null for equal values", () => {
    expect(expandArticleRange("20", "20")).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// parseEtLocatorText
// ---------------------------------------------------------------------------
describe("parseEtLocatorText", () => {
  it("parses single article", () => {
    const result = parseEtLocatorText("Artículo 240 del ET");
    expect(result).toEqual({ kind: "single", parts: ["240"] });
  });

  it("parses article range", () => {
    const result = parseEtLocatorText("arts. 20 a 25");
    expect(result).toEqual({ kind: "range", parts: ["20", "25"] });
  });

  it("parses article list", () => {
    const result = parseEtLocatorText("artículos 240, 241 y 242");
    expect(result).toEqual({ kind: "list", parts: ["240", "241", "242"] });
  });

  it("returns null for empty", () => {
    expect(parseEtLocatorText("")).toBeNull();
  });

  it("returns null for non-article text", () => {
    expect(parseEtLocatorText("random text without articles")).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// formatParsedEtLocator
// ---------------------------------------------------------------------------
describe("formatParsedEtLocator", () => {
  it("formats single", () => {
    expect(formatParsedEtLocator({ kind: "single", parts: ["240"] })).toBe(
      "Estatuto Tributario, Artículo 240",
    );
  });

  it("formats range", () => {
    expect(formatParsedEtLocator({ kind: "range", parts: ["20", "25"] })).toBe(
      "Estatuto Tributario, Artículos 20 - 25",
    );
  });

  it("formats list", () => {
    expect(formatParsedEtLocator({ kind: "list", parts: ["240", "241"] })).toBe(
      "Estatuto Tributario, Artículos 240, 241",
    );
  });

  it("handles null", () => {
    expect(formatParsedEtLocator(null)).toBe("Estatuto Tributario");
  });
});

// ---------------------------------------------------------------------------
// parseEtTitle
// ---------------------------------------------------------------------------
describe("parseEtTitle", () => {
  it("parses 'ET, Artículo 240'", () => {
    expect(parseEtTitle("ET, Artículo 240")).toBe("Estatuto Tributario, Artículo 240");
  });

  it("parses 'Estatuto Tributario'", () => {
    expect(parseEtTitle("Estatuto Tributario")).toBe("Estatuto Tributario");
  });

  it("parses 'artículo 240 del ET'", () => {
    expect(parseEtTitle("artículo 240 del ET")).toBe("Estatuto Tributario, Artículo 240");
  });

  it("returns empty for non-ET text", () => {
    expect(parseEtTitle("Ley 1819")).toBe("");
  });
});

// ---------------------------------------------------------------------------
// toSpanishTitleCase
// ---------------------------------------------------------------------------
describe("toSpanishTitleCase", () => {
  it("capitalizes non-small words", () => {
    expect(toSpanishTitleCase("declaracion de renta")).toBe("Declaracion de Renta");
  });

  it("handles empty", () => {
    expect(toSpanishTitleCase("")).toBe("");
  });
});

// ---------------------------------------------------------------------------
// deriveSourceTierLabel
// ---------------------------------------------------------------------------
describe("deriveSourceTierLabel", () => {
  it("returns normative for normative_base", () => {
    expect(deriveSourceTierLabel({ knowledge_class: "normative_base" })).toBe("Fuente Normativa");
  });

  it("returns expertos for interpretative", () => {
    expect(deriveSourceTierLabel({ knowledge_class: "interpretative_guidance" })).toBe("Fuente Expertos");
  });

  it("returns loggro for practica_erp", () => {
    expect(deriveSourceTierLabel({ knowledge_class: "practica_erp" })).toBe("Fuente Loggro");
  });

  it("returns cross-topic label", () => {
    expect(deriveSourceTierLabel({ primary_role: "baseline", cross_topic: true })).toBe(
      "Fuente Normativa (Base transversal)",
    );
  });

  it("uses explicit source_tier when present", () => {
    expect(deriveSourceTierLabel({ source_tier: "Custom Tier" })).toBe("Custom Tier");
  });

  it("returns loggro for operational_checklist", () => {
    expect(deriveSourceTierLabel({ source_type: "operational_checklist" })).toBe("Fuente Loggro");
  });

  it("defaults to expertos", () => {
    expect(deriveSourceTierLabel({})).toBe("Fuente Expertos");
  });
});

// ---------------------------------------------------------------------------
// formatNormativeCitationTitle
// ---------------------------------------------------------------------------
describe("formatNormativeCitationTitle", () => {
  it("formats Ley", () => {
    expect(formatNormativeCitationTitle("Ley 1819 de 2016")).toBe("Ley 1819 de 2016");
  });

  it("formats Ley with remainder", () => {
    const result = formatNormativeCitationTitle("Ley 1819 de 2016: reforma tributaria");
    expect(result).toContain("Ley 1819 de 2016");
    expect(result).toContain("Reforma Tributaria");
  });

  it("formats Decreto", () => {
    expect(formatNormativeCitationTitle("Decreto 1625 de 2016")).toBe("Decreto 1625 de 2016");
  });

  it("formats Resolución", () => {
    expect(formatNormativeCitationTitle("Resolución 000188 de 2024")).toBe("Resolución 000188 de 2024");
  });

  it("formats ET article", () => {
    expect(formatNormativeCitationTitle("ET, Artículo 240")).toBe(
      "Estatuto Tributario, Artículo 240",
    );
  });

  it("formats Formulario", () => {
    expect(formatNormativeCitationTitle("Formulario 110")).toBe("Formulario 110");
  });

  it("passes through unknown", () => {
    expect(formatNormativeCitationTitle("Something else")).toBe("Something else");
  });

  it("returns empty for empty", () => {
    expect(formatNormativeCitationTitle("")).toBe("");
  });
});

// ---------------------------------------------------------------------------
// citationTitleValue
// ---------------------------------------------------------------------------
describe("citationTitleValue", () => {
  it("formats ET reference_key with locator", () => {
    const result = citationTitleValue({ reference_key: "et", locator_start: "240" });
    expect(result).toBe("Estatuto Tributario, Artículo 240");
  });

  it("formats ley reference_key", () => {
    const result = citationTitleValue({ reference_key: "ley:1819:2016" });
    expect(result).toBe("Ley 1819 de 2016");
  });

  it("uses source_label", () => {
    const result = citationTitleValue({ source_label: "Decreto 1625 de 2016" });
    expect(result).toBe("Decreto 1625 de 2016");
  });

  it("falls back to authority + topic", () => {
    const result = citationTitleValue({ authority: "DIAN", topic: "declaracion_renta" });
    expect(result).toContain("DIAN");
    expect(result).toContain("Declaracion Renta");
  });

  it("falls back to 'Referencia normativa'", () => {
    expect(citationTitleValue({})).toBe("Referencia normativa");
  });

  it("handles null", () => {
    expect(citationTitleValue(null)).toBe("Referencia normativa");
  });
});
