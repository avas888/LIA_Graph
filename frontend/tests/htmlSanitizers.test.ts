import { describe, expect, it } from "vitest";
import {
  escapeAttr,
  escapeHtml,
  formatTextContent,
} from "@/shared/utils/htmlSanitizers";

describe("escapeHtml", () => {
  it("escapes <, >, &", () => {
    expect(escapeHtml("<script>alert(1)</script>")).toBe(
      "&lt;script&gt;alert(1)&lt;/script&gt;",
    );
    expect(escapeHtml("A & B")).toBe("A &amp; B");
  });

  it("returns empty string for null/undefined", () => {
    expect(escapeHtml(null as unknown as string)).toBe("");
    expect(escapeHtml(undefined as unknown as string)).toBe("");
  });

  it("leaves plain text untouched", () => {
    expect(escapeHtml("hola mundo")).toBe("hola mundo");
  });
});

describe("escapeAttr", () => {
  it("escapes double quotes in addition to HTML entities", () => {
    expect(escapeAttr('value="danger"')).toBe("value=&quot;danger&quot;");
  });

  it("preserves single quotes (attrs that use single-quote delimiters still work)", () => {
    expect(escapeAttr("it's fine")).toBe("it's fine");
  });
});

describe("formatTextContent", () => {
  it("splits on blank lines into separate <p> blocks", () => {
    const out = formatTextContent("Primer párrafo.\n\nSegundo párrafo.");
    expect(out).toBe("<p>Primer párrafo.</p><p>Segundo párrafo.</p>");
  });

  it("normalizes CRLF to LF", () => {
    const out = formatTextContent("Uno.\r\n\r\nDos.");
    expect(out).toBe("<p>Uno.</p><p>Dos.</p>");
  });

  it("escapes content inside paragraphs", () => {
    const out = formatTextContent("<b>peligro</b>");
    expect(out).toContain("&lt;b&gt;peligro&lt;/b&gt;");
  });

  it("drops empty paragraphs", () => {
    const out = formatTextContent("\n\n\n\nSolo uno.\n\n\n");
    expect(out).toBe("<p>Solo uno.</p>");
  });

  it("returns empty string for empty input", () => {
    expect(formatTextContent("")).toBe("");
  });
});
