import { describe, expect, it } from "vitest";
import { normalizeExpertPanelState } from "@/features/chat/persistence";

describe("expert panel persistence normalization", () => {
  it("preserves search-seed load options and response metadata", () => {
    const normalized = normalizeExpertPanelState({
      status: "populated",
      loadOptions: {
        traceId: "trace_demo",
        message: "Consulta demo",
        assistantAnswer: "Respuesta demo",
        normativeArticleRefs: ["art_179"],
        searchSeed: "Consulta: demo\nTesis: demo",
        searchSeedOrigin: "deterministic",
        topic: "declaracion_renta",
        pais: "colombia",
      },
      response: {
        ok: true,
        groups: [],
        ungrouped: [],
        total_available: 5,
        has_more: true,
        retrieval_diagnostics: {
          expert_query_seed: "Consulta: demo\nTesis: demo",
          expert_query_seed_origin: "deterministic",
        },
        trace_id: "trace_demo",
      },
    });

    expect(normalized?.loadOptions?.searchSeedOrigin).toBe("deterministic");
    expect(normalized?.loadOptions?.searchSeed).toContain("Tesis:");
    expect(normalized?.response?.total_available).toBe(5);
    expect(normalized?.response?.has_more).toBe(true);
    expect(normalized?.response?.retrieval_diagnostics?.expert_query_seed_origin).toBe("deterministic");
  });
});
