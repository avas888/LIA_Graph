import { describe, expect, it } from "vitest";
import {
  asCitationArray,
  boldGroupedFormReferences,
  citationQualityScore,
  dedupeCitations,
  filterCitedOnly,
  filterNormativeHelperBaseCitations,
  logicalDocIdFromDocId,
  mergeCitationPair,
  mergeCitations,
} from "@/features/chat/citations";

// ---------------------------------------------------------------------------
// asCitationArray
// ---------------------------------------------------------------------------
describe("asCitationArray", () => {
  it("filters non-objects", () => {
    expect(asCitationArray([{ a: 1 }, null, "string", 42, { b: 2 }])).toHaveLength(2);
  });

  it("returns empty for non-array", () => {
    expect(asCitationArray(null)).toEqual([]);
    expect(asCitationArray("string")).toEqual([]);
  });

  it("shallow-clones items", () => {
    const original = { doc_id: "d1" };
    const result = asCitationArray([original]);
    expect(result[0]).not.toBe(original);
    expect(result[0]).toEqual(original);
  });
});

// ---------------------------------------------------------------------------
// logicalDocIdFromDocId
// ---------------------------------------------------------------------------
describe("logicalDocIdFromDocId", () => {
  it("strips _part_N suffix", () => {
    expect(logicalDocIdFromDocId("renta_corpus_a_et_art_240_part_03")).toBe("renta_corpus_a_et_art_240");
  });

  it("returns trimmed for no suffix", () => {
    expect(logicalDocIdFromDocId("simple_doc_id")).toBe("simple_doc_id");
  });

  it("returns empty for null", () => {
    expect(logicalDocIdFromDocId(null)).toBe("");
  });
});

// ---------------------------------------------------------------------------
// boldGroupedFormReferences
// ---------------------------------------------------------------------------
describe("boldGroupedFormReferences", () => {
  it("returns empty for empty", () => {
    expect(boldGroupedFormReferences("")).toBe("");
  });

  it("returns input when no form references", () => {
    expect(boldGroupedFormReferences("simple text")).toBe("simple text");
  });
});

// ---------------------------------------------------------------------------
// citationQualityScore
// ---------------------------------------------------------------------------
describe("citationQualityScore", () => {
  it("scores based on fields present", () => {
    expect(citationQualityScore(null)).toBe(0);
    // Empty object gets +1 for not being mention_only
    expect(citationQualityScore({})).toBe(1);
    // doc_id=8 + not_mention=1 = 9
    expect(citationQualityScore({ doc_id: "d1" })).toBe(9);
    expect(citationQualityScore({ doc_id: "d1", reference_key: "et" })).toBe(13);
    expect(citationQualityScore({ doc_id: "d1", logical_doc_id: "l1", reference_key: "et" })).toBe(17);
  });

  it("adds 1 for non-mention citations", () => {
    expect(citationQualityScore({ doc_id: "d1" })).toBe(9); // 8 + 1
    expect(citationQualityScore({ doc_id: "d1", mention_only: true })).toBe(8); // no +1
  });

  it("adds 2 for usage_context", () => {
    // 8 (doc_id) + 2 (usage_context) + 1 (not mention) = 11
    expect(citationQualityScore({ doc_id: "d1", usage_context: "used" })).toBe(11);
  });
});

// ---------------------------------------------------------------------------
// mergeCitationPair
// ---------------------------------------------------------------------------
describe("mergeCitationPair", () => {
  it("merges two citations, higher score wins fields", () => {
    const left = { doc_id: "d1", reference_key: "et", mention_only: true };
    const right = { doc_id: "d1", usage_context: "used", mention_only: false };
    const result = mergeCitationPair(left, right);
    expect(result.reference_key).toBe("et"); // from left (higher score)
    expect(result.mention_only).toBe(false); // both must be mention_only
  });

  it("sets mention_detected when either is mention_only", () => {
    const result = mergeCitationPair({ mention_only: true }, { mention_only: false });
    expect(result.mention_detected).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// dedupeCitations
// ---------------------------------------------------------------------------
describe("dedupeCitations", () => {
  it("deduplicates by doc_id", () => {
    const citations = [
      { doc_id: "d1", title: "First" },
      { doc_id: "d1", title: "Duplicate" },
      { doc_id: "d2", title: "Different" },
    ];
    const result = dedupeCitations(citations);
    expect(result).toHaveLength(2);
  });

  it("handles empty array", () => {
    expect(dedupeCitations([])).toEqual([]);
  });

  it("handles non-array", () => {
    expect(dedupeCitations(null)).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// filterCitedOnly
// ---------------------------------------------------------------------------
describe("filterCitedOnly", () => {
  it("keeps only citations with usage_context or mention flags", () => {
    const citations = [
      { doc_id: "d1", usage_context: "used" },
      { doc_id: "d2" },
      { doc_id: "d3", mention_only: true },
      { doc_id: "d4", mention_detected: true },
    ];
    const result = filterCitedOnly(citations);
    expect(result).toHaveLength(3);
    expect(result.map((c) => c.doc_id)).toEqual(["d1", "d3", "d4"]);
  });
});

// ---------------------------------------------------------------------------
// filterNormativeHelperBaseCitations
// ---------------------------------------------------------------------------
describe("filterNormativeHelperBaseCitations", () => {
  it("keeps normative_base citations", () => {
    const citations = [
      { doc_id: "d1", knowledge_class: "normative_base" },
      { doc_id: "d2", knowledge_class: "practica_erp" },
    ];
    const result = filterNormativeHelperBaseCitations(citations);
    expect(result).toHaveLength(1);
    expect(result[0].doc_id).toBe("d1");
  });

  it("keeps official source_type when no knowledge_class", () => {
    const citations = [{ doc_id: "d1", source_type: "official_primary" }];
    const result = filterNormativeHelperBaseCitations(citations);
    expect(result).toHaveLength(1);
  });
});

// ---------------------------------------------------------------------------
// mergeCitations
// ---------------------------------------------------------------------------
describe("mergeCitations", () => {
  it("merges primary and mention citations", () => {
    const primary = [{ doc_id: "d1", usage_context: "base" }];
    const mentions = [{ doc_id: "d2", mention_only: true }];
    const result = mergeCitations(primary, mentions);
    expect(result.length).toBeGreaterThanOrEqual(2);
  });

  it("deduplicates across arrays", () => {
    const primary = [{ doc_id: "d1" }];
    const mentions = [{ doc_id: "d1", mention_only: true }];
    const result = mergeCitations(primary, mentions);
    expect(result).toHaveLength(1);
  });
});
