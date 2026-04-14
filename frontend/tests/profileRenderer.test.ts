import { describe, expect, it } from "vitest";
import { buildCitationProfileParams } from "@/features/chat/normative/profileRenderer";

describe("buildCitationProfileParams", () => {
  it("sets doc_id for simple citation", () => {
    const params = buildCitationProfileParams({ doc_id: "doc_123" });
    expect(params.get("doc_id")).toBe("doc_123");
    expect(params.has("reference_key")).toBe(false);
  });

  it("sets reference_key for ET ley citation", () => {
    const params = buildCitationProfileParams({
      doc_id: "renta_corpus_a_et_art_240",
      reference_key: "ley:1819:2016",
    });
    expect(params.get("reference_key")).toBe("ley:1819:2016");
    expect(params.has("doc_id")).toBe(false);
  });

  it("infers ley from label when doc_id is ET", () => {
    const params = buildCitationProfileParams({
      doc_id: "renta_corpus_a_et_art_240",
      reference_key: "et",
      source_label: "Ley 2277 de 2022",
    });
    expect(params.get("reference_key")).toBe("ley:2277:2022");
  });

  it("sets reference_key for formulario", () => {
    const params = buildCitationProfileParams({ reference_key: "formulario:110" });
    expect(params.get("reference_key")).toBe("formulario:110");
  });

  it("includes locator fields when present", () => {
    const params = buildCitationProfileParams({
      doc_id: "doc_1",
      locator_text: "art. 240",
      locator_kind: "articles",
      locator_start: "240",
      locator_end: "242",
    });
    expect(params.get("locator_text")).toBe("art. 240");
    expect(params.get("locator_kind")).toBe("articles");
    expect(params.get("locator_start")).toBe("240");
    expect(params.get("locator_end")).toBe("242");
  });

  it("includes message_context for ET citations", () => {
    const params = buildCitationProfileParams(
      { doc_id: "doc_1", reference_key: "et", locator_start: "240" },
      { messageContext: "context about renta" },
    );
    expect(params.get("message_context")).toBe("context about renta");
  });

  it("omits message_context when not ET/ley", () => {
    const params = buildCitationProfileParams(
      { doc_id: "doc_1" },
      { messageContext: "context" },
    );
    expect(params.has("message_context")).toBe(false);
  });

  it("throws for missing doc_id and reference_key", () => {
    expect(() => buildCitationProfileParams({})).toThrow("citation_profile_missing_doc_id");
  });
});
