import { describe, expect, it } from "vitest";
import {
  applyKernelHierarchyFormattingMarkdown,
  splitAnswerFromFollowupSection,
  stripInlineEvidenceAnnotations,
} from "@/features/chat/formatting";

// ---------------------------------------------------------------------------
// applyKernelHierarchyFormattingMarkdown
// ---------------------------------------------------------------------------
describe("applyKernelHierarchyFormattingMarkdown", () => {
  it("returns empty for empty", () => {
    expect(applyKernelHierarchyFormattingMarkdown("")).toBe("");
  });

  it("processes plain markdown", () => {
    const result = applyKernelHierarchyFormattingMarkdown("1. Section\n1.1. Sub\n1.1.1. Item");
    expect(result).toContain("Section");
  });

  it("preserves code blocks", () => {
    const input = "Some text\n```\ncode here\n```\nMore text";
    const result = applyKernelHierarchyFormattingMarkdown(input);
    expect(result).toContain("```\ncode here\n```");
  });

  it("collapses excessive newlines", () => {
    const result = applyKernelHierarchyFormattingMarkdown("a\n\n\n\nb");
    expect(result).not.toContain("\n\n\n");
  });
});

// ---------------------------------------------------------------------------
// stripInlineEvidenceAnnotations
// ---------------------------------------------------------------------------
describe("stripInlineEvidenceAnnotations", () => {
  it("removes [Evidencia:...] annotations", () => {
    const input = "Hello [Evidencia: doc_1, art. 240] world";
    const result = stripInlineEvidenceAnnotations(input);
    expect(result).not.toContain("[Evidencia:");
    expect(result).toContain("Hello");
    expect(result).toContain("world");
  });

  it("removes [Evidence:...] annotations (English)", () => {
    const input = "Text [Evidence: source] more";
    const result = stripInlineEvidenceAnnotations(input);
    expect(result).not.toContain("[Evidence:");
  });

  it("handles nested brackets", () => {
    const input = "A [Evidencia: [nested]] B";
    const result = stripInlineEvidenceAnnotations(input);
    expect(result).toContain("A");
    expect(result).toContain("B");
  });

  it("returns empty for empty", () => {
    expect(stripInlineEvidenceAnnotations("")).toBe("");
  });

  it("leaves text without annotations unchanged", () => {
    expect(stripInlineEvidenceAnnotations("plain text")).toBe("plain text");
  });
});

// ---------------------------------------------------------------------------
// splitAnswerFromFollowupSection
// ---------------------------------------------------------------------------
describe("splitAnswerFromFollowupSection", () => {
  it("splits answer from followup section", () => {
    const input = [
      "Main answer text.",
      "",
      "Sugerencias de consultas adicionales:",
      "6.1 ¿Cómo calcular la base gravable?",
      "6.2 ¿Cuál es la tarifa aplicable?",
    ].join("\n");

    const result = splitAnswerFromFollowupSection(input);
    expect(result.answer).toBe("Main answer text.");
    expect(result.followupQueries).toHaveLength(2);
    expect(result.followupQueries[0]).toContain("base gravable");
  });

  it("returns full text when no followup section", () => {
    const result = splitAnswerFromFollowupSection("Just a normal answer.");
    expect(result.answer).toBe("Just a normal answer.");
    expect(result.followupQueries).toHaveLength(0);
  });

  it("returns empty for empty input", () => {
    const result = splitAnswerFromFollowupSection("");
    expect(result.answer).toBe("");
    expect(result.followupQueries).toHaveLength(0);
  });

  it("ignores section title without numbered queries", () => {
    const input = [
      "Main answer.",
      "Sugerencias de consultas adicionales:",
      "Some text that is not a numbered query.",
    ].join("\n");

    const result = splitAnswerFromFollowupSection(input);
    expect(result.followupQueries).toHaveLength(0);
  });
});
