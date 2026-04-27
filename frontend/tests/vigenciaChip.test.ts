/**
 * @vitest-environment jsdom
 */
import { describe, expect, it } from "vitest";

import {
  createVigenciaChip,
  getVigenciaVariantTone,
  type VigenciaState,
} from "@/shared/ui/atoms/vigenciaChip";

describe("atom: vigenciaChip", () => {
  it("returns null for state V (no chip on default vigente)", () => {
    const chip = createVigenciaChip({ state: "V" });
    expect(chip).toBeNull();
  });

  it("renders VM with the modifying source label", () => {
    const chip = createVigenciaChip({
      state: "VM",
      sourceNormId: "ley.2277.2022.art.10",
    });
    expect(chip).not.toBeNull();
    expect(chip!.tagName).toBe("SPAN");
    expect(chip!.getAttribute("data-lia-component")).toBe("vigencia-chip");
    expect(chip!.getAttribute("data-vigencia-state")).toBe("VM");
    expect(chip!.textContent).toContain("modificada por");
    expect(chip!.textContent).toContain("Ley 2277/2022");
    expect(chip!.className).toContain("lia-vigencia-chip--vm");
  });

  it("renders DE with deroganting law and effective date", () => {
    const chip = createVigenciaChip({
      state: "DE",
      sourceNormId: "ley.2277.2022.art.96",
      stateFrom: "2023-01-01",
    });
    expect(chip).not.toBeNull();
    expect(chip!.textContent).toContain("derogada por");
    expect(chip!.textContent).toContain("2023-01-01");
    expect(chip!.className).toContain("lia-chip--error");
  });

  it("renders DT with the contested-warning text", () => {
    const chip = createVigenciaChip({ state: "DT" });
    expect(chip!.textContent).toContain("derogada tácitamente");
    expect(chip!.className).toContain("lia-chip--warning");
  });

  it("renders SP with the suspending auto", () => {
    const chip = createVigenciaChip({
      state: "SP",
      sourceNormId: "auto.ce.28920.2024.12.16",
    });
    expect(chip!.textContent).toContain("suspendida por");
    expect(chip!.textContent).toContain("Auto CE 28920");
  });

  it("renders IE with the inexequibilidad sentencia", () => {
    const chip = createVigenciaChip({
      state: "IE",
      sourceNormId: "sent.cc.C-079.2026",
    });
    expect(chip!.textContent).toContain("inexequible");
    expect(chip!.textContent).toContain("C-079");
    expect(chip!.className).toContain("lia-chip--error");
  });

  it("renders EC with literal court text in title attribute", () => {
    const literal =
      "EXEQUIBLES, en el entendido que el régimen tarifario establecido " +
      "en el artículo 101 de la Ley 1819 de 2016 continuará rigiendo...";
    const chip = createVigenciaChip({
      state: "EC",
      sourceNormId: "sent.cc.C-384.2023",
      interpretiveConstraintText: literal,
    });
    expect(chip!.textContent).toContain("exequibilidad condicionada");
    expect(chip!.getAttribute("data-interpretive-constraint")).toBe(literal);
    expect(chip!.getAttribute("title")).toBe(literal);
  });

  it("renders VC (modulación doctrinaria)", () => {
    const chip = createVigenciaChip({
      state: "VC",
      sourceNormId: "concepto.dian.999",
      interpretiveConstraintText: "limita el alcance a casos X.",
    });
    expect(chip!.textContent).toContain("vigente con modulación");
    expect(chip!.className).toContain("lia-vigencia-chip--vc");
  });

  it("renders VL with rige_desde fecha", () => {
    const chip = createVigenciaChip({
      state: "VL",
      rigeDesde: "2027-01-01",
    });
    expect(chip!.textContent).toContain("vacatio legis");
    expect(chip!.textContent).toContain("2027-01-01");
  });

  it("renders DI with countdown reference", () => {
    const chip = createVigenciaChip({
      state: "DI",
      rigeDesde: "2026-12-31",
    });
    expect(chip!.textContent).toContain("exequibilidad diferida");
    expect(chip!.textContent).toContain("2026-12-31");
  });

  it("renders RV with the triggering inexequibilidad", () => {
    const chip = createVigenciaChip({
      state: "RV",
      sourceNormId: "ley.1943.2018",
      revivedTriggerNormId: "sent.cc.C-481.2019",
      revivesTextVersion: "redacción anterior a Ley 1943/2018",
    });
    expect(chip!.textContent).toContain("revivida tras");
    expect(chip!.textContent).toContain("C-481");
    expect(chip!.className).toContain("lia-chip--success");
    expect(chip!.getAttribute("aria-label")).toContain(
      "redacción anterior a Ley 1943/2018",
    );
  });

  it("exposes the state via data-vigencia-state attribute on every variant", () => {
    const states: VigenciaState[] = [
      "VM",
      "DE",
      "DT",
      "SP",
      "IE",
      "EC",
      "VC",
      "VL",
      "DI",
      "RV",
    ];
    for (const s of states) {
      const chip = createVigenciaChip({
        state: s,
        sourceNormId: "ley.2277.2022",
        rigeDesde: "2026-12-31",
        interpretiveConstraintText: "literal",
      });
      expect(chip).not.toBeNull();
      expect(chip!.getAttribute("data-vigencia-state")).toBe(s);
    }
  });

  it("getVigenciaVariantTone returns null for V and the right tone for others", () => {
    expect(getVigenciaVariantTone("V")).toBeNull();
    expect(getVigenciaVariantTone("DE")).toBe("error");
    expect(getVigenciaVariantTone("RV")).toBe("success");
    expect(getVigenciaVariantTone("DI")).toBe("warning");
  });
});
