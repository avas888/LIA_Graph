import { describe, expect, it } from "vitest";
import {
  BULLET_MARKER_RE,
  isBulletListBlock,
  splitBlockLines,
  splitParagraphBlocks,
  stripBulletMarker,
} from "@/shared/utils/textBlockFormatter";

describe("splitParagraphBlocks", () => {
  it("splits on blank-line separators", () => {
    expect(splitParagraphBlocks("Primero.\n\nSegundo.\n\nTercero.")).toEqual([
      "Primero.",
      "Segundo.",
      "Tercero.",
    ]);
  });

  it("normalizes CRLF to LF", () => {
    expect(splitParagraphBlocks("A.\r\n\r\nB.")).toEqual(["A.", "B."]);
  });

  it("drops empty blocks and trims each block", () => {
    expect(splitParagraphBlocks("\n\n  A.  \n\n\n\n B. \n\n")).toEqual(["A.", "B."]);
  });

  it("returns empty array for empty / null input", () => {
    expect(splitParagraphBlocks("")).toEqual([]);
    expect(splitParagraphBlocks("   ")).toEqual([]);
    expect(splitParagraphBlocks(null as unknown as string)).toEqual([]);
  });

  it("returns a single block when no blank lines are present", () => {
    expect(splitParagraphBlocks("una línea sola.")).toEqual(["una línea sola."]);
  });
});

describe("splitBlockLines", () => {
  it("splits on newlines, trims, drops empties", () => {
    expect(splitBlockLines("- uno\n- dos\n\n- tres")).toEqual(["- uno", "- dos", "- tres"]);
  });

  it("returns empty array when block is empty", () => {
    expect(splitBlockLines("")).toEqual([]);
  });
});

describe("isBulletListBlock", () => {
  it("returns true when every line starts with a bullet marker", () => {
    expect(isBulletListBlock(["- uno", "- dos", "• tres", "· cuatro"])).toBe(true);
  });

  it("returns false when any line lacks a bullet marker", () => {
    expect(isBulletListBlock(["- uno", "dos", "- tres"])).toBe(false);
  });

  it("returns false for an empty line list", () => {
    expect(isBulletListBlock([])).toBe(false);
  });
});

describe("stripBulletMarker", () => {
  it("removes '- ' / '• ' / '· ' from the start of a line", () => {
    expect(stripBulletMarker("- texto")).toBe("texto");
    expect(stripBulletMarker("• texto")).toBe("texto");
    expect(stripBulletMarker("· texto")).toBe("texto");
  });

  it("leaves non-bullet lines untouched", () => {
    expect(stripBulletMarker("texto normal")).toBe("texto normal");
  });
});

describe("BULLET_MARKER_RE", () => {
  it("matches leading '-', '•', '·' followed by whitespace", () => {
    expect(BULLET_MARKER_RE.test("- texto")).toBe(true);
    expect(BULLET_MARKER_RE.test("• texto")).toBe(true);
    expect(BULLET_MARKER_RE.test("· texto")).toBe(true);
  });

  it("does not match lines without a trailing space after the marker", () => {
    expect(BULLET_MARKER_RE.test("-texto")).toBe(false);
  });
});
