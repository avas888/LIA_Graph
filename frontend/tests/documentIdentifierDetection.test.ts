import { describe, expect, it } from "vitest";
import {
  isRawDocId,
  isTechnicalLabel,
} from "@/shared/utils/documentIdentifierDetection";

describe("isTechnicalLabel", () => {
  it("detects hex-hash 8-char tokens", () => {
    expect(isTechnicalLabel("pt expertos precios 27555a78 part 03")).toBe(true);
  });

  it("detects 'part N' suffixes", () => {
    expect(isTechnicalLabel("renta ingest part_02 normativa")).toBe(true);
  });

  it("detects ≥16-char underscore/hyphen identifiers", () => {
    expect(isTechnicalLabel("renta_ingest_pt_normativa")).toBe(true);
  });

  it("rejects short or clearly human strings", () => {
    expect(isTechnicalLabel("Ley 100 de 1993")).toBe(false);
    expect(isTechnicalLabel("hola")).toBe(false);
    expect(isTechnicalLabel("")).toBe(false);
  });

  it("rejects strings under 12 chars even when they match other shapes", () => {
    expect(isTechnicalLabel("part01")).toBe(false);
  });
});

describe("isRawDocId", () => {
  it("detects underscore-separated lowercase identifiers", () => {
    expect(isRawDocId("renta_ingest_pt_normativa_2024")).toBe(true);
  });

  it("detects '::' separated compound ids", () => {
    expect(isRawDocId("rentaingestnormativa::section01")).toBe(true);
  });

  it("detects long tokens without whitespace", () => {
    expect(isRawDocId("abcdefghijklmnopqrstuvwxyz0123456789abc")).toBe(true);
  });

  it("detects 'ingest' substring in whitespace-free token", () => {
    expect(isRawDocId("nomina_ingest_2024_v2")).toBe(true);
  });

  it("detects hex-hash tokens even with spaces", () => {
    expect(isRawDocId("pt expertos 27555a78 part 03")).toBe(true);
  });

  it("detects 'part N' suffixes even with spaces", () => {
    expect(isRawDocId("normativa general part 05")).toBe(true);
  });

  it("rejects short strings under 16 chars", () => {
    expect(isRawDocId("Ley 100")).toBe(false);
    expect(isRawDocId("short_id")).toBe(false);
  });

  it("rejects human-titled strings with spaces and mixed case", () => {
    expect(isRawDocId("Estatuto Tributario Artículo 147")).toBe(false);
    expect(isRawDocId("Ley 1943 de 2018")).toBe(false);
  });

  it("returns false for null/empty", () => {
    expect(isRawDocId(null)).toBe(false);
    expect(isRawDocId("")).toBe(false);
    expect(isRawDocId(undefined)).toBe(false);
  });
});
