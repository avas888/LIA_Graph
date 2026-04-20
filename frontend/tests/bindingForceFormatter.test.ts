import { describe, expect, it } from "vitest";
import {
  bindingForceTone,
  formatBindingForceText,
} from "@/features/chat/normative/bindingForceFormatter";

describe("formatBindingForceText", () => {
  it("prefixes raw labels with 'Fuerza vinculante:'", () => {
    expect(formatBindingForceText("Decreto reglamentario")).toBe(
      "Fuerza vinculante: Decreto reglamentario",
    );
  });

  it("is idempotent when the prefix is already present", () => {
    expect(formatBindingForceText("Fuerza vinculante: Ley o estatuto")).toBe(
      "Fuerza vinculante: Ley o estatuto",
    );
  });

  it("is idempotent case-insensitively", () => {
    expect(formatBindingForceText("fuerza Vinculante: Resolución DIAN")).toBe(
      "fuerza Vinculante: Resolución DIAN",
    );
  });

  it("returns empty string for empty input", () => {
    expect(formatBindingForceText("")).toBe("");
    expect(formatBindingForceText("   ")).toBe("");
  });
});

describe("bindingForceTone", () => {
  it("maps rank ≥ 700 to success", () => {
    expect(bindingForceTone("anything", 1000)).toBe("success");
    expect(bindingForceTone("anything", 700)).toBe("success");
  });

  it("maps rank 300–699 to warning", () => {
    expect(bindingForceTone("anything", 300)).toBe("warning");
    expect(bindingForceTone("anything", 500)).toBe("warning");
  });

  it("maps rank 1–299 to neutral", () => {
    expect(bindingForceTone("anything", 100)).toBe("neutral");
    expect(bindingForceTone("anything", 1)).toBe("neutral");
  });

  it("falls back to label heuristics when rank is zero", () => {
    expect(bindingForceTone("Alta vinculación", 0)).toBe("success");
    expect(bindingForceTone("Media vinculación", 0)).toBe("warning");
    expect(bindingForceTone("Rango constitucional", 0)).toBe("success");
    expect(bindingForceTone("Resolución DIAN", 0)).toBe("success");
    expect(bindingForceTone("Doctrina administrativa", 0)).toBe("warning");
    expect(bindingForceTone("Instrumento operativo", 0)).toBe("warning");
    expect(bindingForceTone("Documento genérico", 0)).toBe("neutral");
  });

  it("returns neutral for empty label + zero rank", () => {
    expect(bindingForceTone("", 0)).toBe("neutral");
  });
});
