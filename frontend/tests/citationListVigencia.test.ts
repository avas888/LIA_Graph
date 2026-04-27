/**
 * @vitest-environment jsdom
 */
import { describe, expect, it } from "vitest";

import {
  renderCitationList,
  type CitationGroupViewModel,
} from "@/shared/ui/organisms/citationList";

describe("citationList renders v3 vigencia chip when annotation present", () => {
  it("renders the IE chip on a derogated/inexequible citation (modal action)", () => {
    const container = document.createElement("ul");
    const groups: CitationGroupViewModel[] = [
      {
        id: "g1",
        label: "Normativa",
        items: [
          {
            action: "modal",
            id: "c1",
            meta: "DIAN — Decreto",
            title: "Decreto 1474 de 2025",
            vigenciaV3: {
              state: "IE",
              sourceNormId: "sent.cc.C-079.2026",
              stateFrom: "2025-12-30",
            },
          },
        ],
      },
    ];
    renderCitationList(container, groups);
    const chip = container.querySelector('[data-lia-component="vigencia-chip"]');
    expect(chip).not.toBeNull();
    expect(chip?.getAttribute("data-vigencia-state")).toBe("IE");
    expect(chip?.textContent).toContain("inexequible");
  });

  it("does NOT render a chip when state is V (default vigente)", () => {
    const container = document.createElement("ul");
    const groups: CitationGroupViewModel[] = [
      {
        id: "g1",
        label: "Normativa",
        items: [
          {
            action: "modal",
            id: "c1",
            meta: "—",
            title: "Vigente",
            vigenciaV3: { state: "V" },
          },
        ],
      },
    ];
    renderCitationList(container, groups);
    expect(container.querySelector('[data-lia-component="vigencia-chip"]')).toBeNull();
  });

  it("does NOT render a chip when vigenciaV3 is omitted (no anchor citation)", () => {
    const container = document.createElement("ul");
    const groups: CitationGroupViewModel[] = [
      {
        id: "g1",
        label: "Normativa",
        items: [{ action: "modal", id: "c1", meta: "—", title: "X" }],
      },
    ];
    renderCitationList(container, groups);
    expect(container.querySelector('[data-lia-component="vigencia-chip"]')).toBeNull();
  });

  it("renders chip on external action items", () => {
    const container = document.createElement("ul");
    const groups: CitationGroupViewModel[] = [
      {
        id: "g1",
        label: "Normativa",
        items: [
          {
            action: "external",
            id: "c1",
            meta: "—",
            title: "External",
            externalUrl: "https://example.com",
            vigenciaV3: { state: "DT" },
          },
        ],
      },
    ];
    renderCitationList(container, groups);
    const chip = container.querySelector('[data-lia-component="vigencia-chip"]');
    expect(chip).not.toBeNull();
    expect(chip?.getAttribute("data-vigencia-state")).toBe("DT");
  });
});
