import { describe, expect, it } from "vitest";
import {
  extractYearFromReferenceKey,
  extractYearFromText,
} from "@/shared/utils/citationDateExtraction";

describe("extractYearFromReferenceKey", () => {
  it("parses the year from 'resolucion_dian:162:2023'", () => {
    expect(extractYearFromReferenceKey("resolucion_dian:162:2023")).toBe(2023);
  });

  it("parses the year from 'concepto_dian:12345:2020' (3+ digit number, then year)", () => {
    expect(extractYearFromReferenceKey("concepto_dian:12345:2020")).toBe(2020);
  });

  it("returns 0 when the first 4-digit group is a pre-1900 ley number", () => {
    // Current impl matches the FIRST :\d{4}(?=:|$). For 'ley:1819:2016' the
    // regex picks 1819 (the ley number) but the <1900 guard rejects it, so
    // the function returns 0. This pins the legacy behavior — adopting the
    // LAST 4-digit group instead is a separate task.
    expect(extractYearFromReferenceKey("ley:1819:2016")).toBe(0);
  });

  it("returns 0 for bare 'et'", () => {
    expect(extractYearFromReferenceKey("et")).toBe(0);
  });

  it("returns 0 when there is no 4-digit year", () => {
    expect(extractYearFromReferenceKey("ley:1819")).toBe(0);
  });

  it("rejects pre-1900 years as stray", () => {
    expect(extractYearFromReferenceKey("ley:100:1850")).toBe(0);
  });

  it("returns 0 for empty/null input", () => {
    expect(extractYearFromReferenceKey("")).toBe(0);
    expect(extractYearFromReferenceKey(null as unknown as string)).toBe(0);
  });
});

describe("extractYearFromText", () => {
  it("parses 'de YYYY' from Spanish citation titles", () => {
    expect(extractYearFromText("Resolución 233 de 2025")).toBe(2025);
    expect(extractYearFromText("Decreto 1625 de 2016")).toBe(2016);
    expect(extractYearFromText("Ley 1819 de 2016")).toBe(2016);
  });

  it("is case-insensitive on the connector", () => {
    expect(extractYearFromText("Resolución 233 DE 2025")).toBe(2025);
  });

  it("requires a word boundary before 'de'", () => {
    // 'ide 2020' should not match because there's no word boundary before 'de'
    expect(extractYearFromText("Guide 2020")).toBe(0);
  });

  it("rejects pre-1900 years", () => {
    expect(extractYearFromText("Norma antigua de 1850")).toBe(0);
  });

  it("returns 0 when no year is present", () => {
    expect(extractYearFromText("Resolución DIAN sin fecha")).toBe(0);
  });

  it("returns 0 for empty/null input", () => {
    expect(extractYearFromText("")).toBe(0);
    expect(extractYearFromText(null as unknown as string)).toBe(0);
  });
});
