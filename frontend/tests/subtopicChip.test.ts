/**
 * @vitest-environment jsdom
 */
import { describe, expect, it } from "vitest";

import { createSubtopicChip } from "@/shared/ui/atoms/subtopicChip";
import { createIntakeFileRow } from "@/shared/ui/molecules/intakeFileRow";

describe("atom: subtopicChip", () => {
  it("renders the provided label with confidence percentage", () => {
    const chip = createSubtopicChip({
      subtopicKey: "parafiscales_icbf",
      label: "Parafiscales ICBF",
      confidence: 0.92,
    });
    expect(chip.tagName).toBe("SPAN");
    expect(chip.getAttribute("data-lia-component")).toBe("subtopic-chip");
    expect(chip.getAttribute("data-subtopic-key")).toBe("parafiscales_icbf");
    expect(chip.textContent).toContain("Parafiscales ICBF");
    expect(chip.textContent).toContain("92%");
  });

  it("falls back to sub_topic_key when label missing", () => {
    const chip = createSubtopicChip({ subtopicKey: "nomina_electronica" });
    expect(chip.textContent).toBe("nomina_electronica");
  });

  it("flips tone to warning when requires_review is true", () => {
    const chip = createSubtopicChip({
      subtopicKey: "foo",
      requiresReview: true,
    });
    expect(chip.className).toContain("lia-chip--warning");
    expect(chip.getAttribute("data-subtopic-review")).toBe("true");
  });

  it("renders info tone for new subtopics", () => {
    const chip = createSubtopicChip({
      subtopicKey: "foo",
      isNew: true,
    });
    expect(chip.className).toContain("lia-chip--info");
    expect(chip.getAttribute("data-subtopic-new")).toBe("true");
  });
});

describe("molecule: intakeFileRow — subtopic wiring", () => {
  it("renders a subtopic chip when subtopicKey is present", () => {
    const row = createIntakeFileRow({
      filename: "nomina.md",
      bytes: 1024,
      detectedTopic: "laboral",
      subtopicKey: "parafiscales_icbf",
      subtopicLabel: "Parafiscales ICBF",
      subtopicConfidence: 0.9,
    });
    const chip = row.querySelector('[data-lia-component="subtopic-chip"]');
    expect(chip).not.toBeNull();
    expect(chip?.getAttribute("data-subtopic-key")).toBe("parafiscales_icbf");
  });

  it("omits the subtopic chip when subtopicKey is absent", () => {
    const row = createIntakeFileRow({
      filename: "doc.md",
      bytes: 128,
      detectedTopic: "laboral",
    });
    expect(
      row.querySelector('[data-lia-component="subtopic-chip"]'),
    ).toBeNull();
  });

  it("renders a 'subtema pendiente' badge when review flag is on without a key", () => {
    const row = createIntakeFileRow({
      filename: "doc.md",
      bytes: 128,
      detectedTopic: "laboral",
      requiresSubtopicReview: true,
    });
    const badge = row.querySelector('[data-subtopic-review="true"]');
    expect(badge).not.toBeNull();
    expect(badge?.textContent).toContain("subtema pendiente");
  });
});
