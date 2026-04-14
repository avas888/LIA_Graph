import { describe, expect, it } from "vitest";
import {
  buildExpertPanelSearchSeed,
  expertPanelSupportCitationsFromSnapshot,
} from "@/features/chat/expertPanelSeed";

describe("expertPanelSeed", () => {
  it("builds a compact seed from the main answer plus cited norms", () => {
    const seed = buildExpertPanelSearchSeed({
      message: "Mi cliente vendió una bodega que tenía como activo fijo hace más de dos años.",
      assistantAnswer:
        "Si la bodega fue activo fijo poseído por dos años o más, la utilidad se trata como ganancia ocasional. La parte que corresponda a recuperación de depreciación previa se lleva como renta ordinaria conforme al artículo 196 del ET. El artículo 300 del ET soporta la ganancia ocasional por enajenación de activos fijos poseídos por dos años o más.",
      supportCitations: [
        {
          doc_id: "et_196",
          legal_reference: "Estatuto Tributario, Artículo 196",
          source_label: "ET art. 196",
        },
        {
          doc_id: "et_300",
          legal_reference: "Estatuto Tributario, Artículo 300",
          source_label: "ET art. 300",
        },
      ],
      normativeArticleRefs: ["art_196", "art_300"],
    });

    expect(seed).toContain("Consulta:");
    expect(seed).toContain("Tesis:");
    expect(seed).toContain("Normas citadas:");
    expect(seed).toContain("Estatuto Tributario, Artículo 196");
    expect(seed).toContain("Estatuto Tributario, Artículo 300");
    expect(seed.length).toBeLessThanOrEqual(900);
  });

  it("dedupes and caps support citations from normative support snapshots", () => {
    const citations = expertPanelSupportCitationsFromSnapshot({
      cachedCitations: [
        {
          doc_id: "et_196_a",
          logical_doc_id: "et_196",
          legal_reference: "Estatuto Tributario, Artículo 196",
        },
        {
          doc_id: "et_196_b",
          logical_doc_id: "et_196",
          legal_reference: "Estatuto Tributario, Artículo 196",
        },
        {
          doc_id: "et_300",
          logical_doc_id: "et_300",
          legal_reference: "Estatuto Tributario, Artículo 300",
        },
      ],
    });

    expect(citations).toHaveLength(2);
    expect(citations.map((item) => item.logical_doc_id)).toEqual(["et_196", "et_300"]);
  });
});
