import { describe, expect, it } from "vitest";
import { buildNormaFacts } from "@/features/chat/normative/profileFactsBuilder";
import type { CitationProfileResponse } from "@/features/chat/normative/types";

function baseProfile(partial: Partial<CitationProfileResponse> = {}): CitationProfileResponse {
  return {
    ok: true,
    facts: [],
    sections: [],
    original_text: null,
    original_action: null,
    analysis_action: null,
    caution_banner: null,
    companion_action: null,
    document_family: "ley",
    binding_force: "",
    binding_force_rank: 0,
    lead: "",
    vigencia_detail: null,
    ...partial,
  } as unknown as CitationProfileResponse;
}

describe("buildNormaFacts", () => {
  it("passes through the profile facts unchanged when no vigencia is present", () => {
    const profile = baseProfile({
      facts: [
        { label: "Fuente", value: "DIAN" },
        { label: "Año", value: "2016" },
      ],
    });
    expect(buildNormaFacts(profile)).toEqual([
      { label: "Fuente", value: "DIAN" },
      { label: "Año", value: "2016" },
    ]);
  });

  it("returns an empty array when the profile is an ET article with original text", () => {
    const profile = baseProfile({
      document_family: "et_dur",
      original_text: { title: "Artículo 147", quote: "Las pérdidas…", evidence_status: "verified" },
      facts: [{ label: "Año", value: "2016" }],
    } as any);
    expect(buildNormaFacts(profile)).toEqual([]);
  });

  it("appends a 'Vigencia específica' row when vigencia_detail is renderable", () => {
    const profile = baseProfile({
      facts: [{ label: "Fuente", value: "DIAN" }],
      vigencia_detail: {
        label: "Vigente",
        summary: "Vigente desde 2016.",
        evidence_status: "verified",
      } as any,
    });
    const rows = buildNormaFacts(profile);
    expect(rows).toHaveLength(2);
    expect(rows[1]).toEqual({ label: "Vigencia específica", value: "Vigente desde 2016." });
  });

  it("replaces an existing 'vigencia' row with the new entry", () => {
    const profile = baseProfile({
      facts: [
        { label: "Vigencia", value: "Desactualizada" },
        { label: "Fuente", value: "DIAN" },
      ],
      vigencia_detail: {
        label: "Vigente",
        summary: "Actualizada por Ley 2010 de 2019.",
        evidence_status: "verified",
      } as any,
    });
    const rows = buildNormaFacts(profile);
    expect(rows).toHaveLength(2);
    expect(rows[0].label).toBe("Vigencia específica");
    expect(rows[0].value).toBe("Actualizada por Ley 2010 de 2019.");
    // The unrelated row survives.
    expect(rows[1]).toEqual({ label: "Fuente", value: "DIAN" });
  });

  it("composes label + basis + notes + last_verified when summary is absent", () => {
    const profile = baseProfile({
      facts: [],
      vigencia_detail: {
        label: "Vigente parcial",
        basis: "Con modificaciones posteriores.",
        notes: "Revisar artículo 54.",
        last_verified_date: "2024-09-01",
        evidence_status: "verified",
      } as any,
    });
    const rows = buildNormaFacts(profile);
    expect(rows).toHaveLength(1);
    expect(rows[0].label).toBe("Vigencia específica");
    expect(rows[0].value).toContain("Vigente parcial");
    expect(rows[0].value).toContain("Con modificaciones posteriores.");
    expect(rows[0].value).toContain("Revisar artículo 54.");
    expect(rows[0].value).toContain("Última verificación del corpus: 2024-09-01");
  });

  it("omits the vigencia row when label is empty even if evidence_status is renderable", () => {
    const profile = baseProfile({
      facts: [{ label: "Fuente", value: "DIAN" }],
      vigencia_detail: { label: "", summary: "algo", evidence_status: "verified" } as any,
    });
    expect(buildNormaFacts(profile)).toEqual([{ label: "Fuente", value: "DIAN" }]);
  });

  it("omits the vigencia row when evidence_status is not renderable", () => {
    const profile = baseProfile({
      facts: [{ label: "Fuente", value: "DIAN" }],
      vigencia_detail: { label: "Sin evidencia", summary: "texto", evidence_status: "unknown" } as any,
    });
    expect(buildNormaFacts(profile)).toEqual([{ label: "Fuente", value: "DIAN" }]);
  });

  it("returns an empty array when facts is not an array", () => {
    const profile = baseProfile({ facts: null as any });
    expect(buildNormaFacts(profile)).toEqual([]);
  });
});
