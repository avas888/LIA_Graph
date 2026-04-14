import { describe, expect, it } from "vitest";
import {
  deriveDetectedTopic,
  deriveFirstQuestionFromTranscriptEntries,
  deriveThreadLabel,
  normalizeAssistantMeta,
  normalizeCitationRequestContext,
  normalizeDocsUsed,
  normalizeExpertPanelLoadOptions,
  normalizeExpertPanelResponse,
  normalizeExpertPanelState,
  normalizeFeedbackRatingValue,
  normalizeLayerContributions,
  normalizeStoredChatSessionIndex,
  normalizeStoredChatSessionState,
  normalizeTokenTotals,
  normalizeTranscriptEntry,
  TOPIC_LABELS,
} from "@/features/chat/persistence";

// ---------------------------------------------------------------------------
// deriveDetectedTopic
// ---------------------------------------------------------------------------
describe("deriveDetectedTopic", () => {
  it("returns first non-empty effectiveTopic", () => {
    const entries = [{ effectiveTopic: "" }, { effectiveTopic: "renta" }];
    expect(deriveDetectedTopic(entries)).toBe("renta");
  });

  it("falls back to effective_topic key", () => {
    expect(deriveDetectedTopic([{ effective_topic: "iva" }])).toBe("iva");
  });

  it("returns empty for non-array", () => {
    expect(deriveDetectedTopic(null)).toBe("");
    expect(deriveDetectedTopic("not array")).toBe("");
  });

  it("returns empty for empty array", () => {
    expect(deriveDetectedTopic([])).toBe("");
  });
});

// ---------------------------------------------------------------------------
// deriveThreadLabel
// ---------------------------------------------------------------------------
describe("deriveThreadLabel", () => {
  it("uses TOPIC_LABELS when topic matches", () => {
    const entries = [{ effectiveTopic: "declaracion_renta" }];
    expect(deriveThreadLabel("ignored", entries)).toBe(TOPIC_LABELS["declaracion_renta"]);
  });

  it("truncates long questions", () => {
    const longQ = "x".repeat(60);
    expect(deriveThreadLabel(longQ, []).length).toBeLessThanOrEqual(50);
  });

  it("falls back to 'Nueva conversación'", () => {
    expect(deriveThreadLabel("", [])).toBe("Nueva conversación");
  });
});

// ---------------------------------------------------------------------------
// normalizeDocsUsed
// ---------------------------------------------------------------------------
describe("normalizeDocsUsed", () => {
  it("deduplicates and trims", () => {
    expect(normalizeDocsUsed(["a", " a ", "b", "b"])).toEqual(["a", "b"]);
  });

  it("skips empty items", () => {
    expect(normalizeDocsUsed(["", null, "a"])).toEqual(["a"]);
  });

  it("returns empty for non-array", () => {
    expect(normalizeDocsUsed(null)).toEqual([]);
    expect(normalizeDocsUsed("string")).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// normalizeLayerContributions
// ---------------------------------------------------------------------------
describe("normalizeLayerContributions", () => {
  it("normalizes numeric values", () => {
    expect(normalizeLayerContributions({ a: "5.7", b: 3 })).toEqual({ a: 5, b: 3 });
  });

  it("skips non-finite values", () => {
    expect(normalizeLayerContributions({ a: "bad" })).toEqual({});
  });

  it("returns empty for null", () => {
    expect(normalizeLayerContributions(null)).toEqual({});
  });
});

// ---------------------------------------------------------------------------
// normalizeFeedbackRatingValue
// ---------------------------------------------------------------------------
describe("normalizeFeedbackRatingValue", () => {
  it("clamps to 1-5", () => {
    expect(normalizeFeedbackRatingValue(3)).toBe(3);
    expect(normalizeFeedbackRatingValue(0)).toBeNull();
    expect(normalizeFeedbackRatingValue(6)).toBeNull();
  });

  it("truncates floats", () => {
    expect(normalizeFeedbackRatingValue(4.9)).toBe(4);
  });

  it("returns null for non-finite", () => {
    expect(normalizeFeedbackRatingValue("bad")).toBeNull();
    expect(normalizeFeedbackRatingValue(null)).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// normalizeAssistantMeta
// ---------------------------------------------------------------------------
describe("normalizeAssistantMeta", () => {
  it("normalizes all fields", () => {
    const meta = normalizeAssistantMeta({
      trace_id: " t1 ",
      chat_run_id: "cr1",
      session_id: "s1",
      requested_topic: "renta",
      effective_topic: "renta",
      pais: "colombia",
      docs_used: ["d1"],
      layer_contributions: { a: 2 },
      feedback_rating: 4,
      question_text: "q1",
      response_route: "decision",
    });
    expect(meta.trace_id).toBe("t1");
    expect(meta.pais).toBe("colombia");
    expect(meta.feedback_rating).toBe(4);
    expect(meta.docs_used).toEqual(["d1"]);
  });

  it("returns null for null input", () => {
    expect(normalizeAssistantMeta(null)).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// normalizeTranscriptEntry
// ---------------------------------------------------------------------------
describe("normalizeTranscriptEntry", () => {
  it("normalizes user entry", () => {
    const entry = normalizeTranscriptEntry({ role: "user", text: "Hola", timestamp: "2026-01-01" });
    expect(entry.role).toBe("user");
    expect(entry.meta).toBeNull();
  });

  it("normalizes assistant entry with meta", () => {
    const entry = normalizeTranscriptEntry({
      role: "assistant",
      text: "Respuesta",
      meta: { trace_id: "t1" },
    });
    expect(entry.role).toBe("assistant");
    expect(entry.meta).toBeTruthy();
    expect(entry.meta.trace_id).toBe("t1");
  });

  it("returns null for empty text", () => {
    expect(normalizeTranscriptEntry({ role: "user", text: "" })).toBeNull();
  });

  it("returns null for invalid role", () => {
    expect(normalizeTranscriptEntry({ role: "system", text: "x" })).toBeNull();
  });

  it("returns null for null", () => {
    expect(normalizeTranscriptEntry(null)).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// normalizeTokenTotals
// ---------------------------------------------------------------------------
describe("normalizeTokenTotals", () => {
  it("normalizes values", () => {
    const result = normalizeTokenTotals({ input_tokens: 10, output_tokens: 20 });
    expect(result.input_tokens).toBe(10);
    expect(result.output_tokens).toBe(20);
    expect(result.total_tokens).toBe(30);
  });

  it("defaults to zero for missing", () => {
    const result = normalizeTokenTotals(null);
    expect(result).toEqual({ input_tokens: 0, output_tokens: 0, total_tokens: 0 });
  });
});

// ---------------------------------------------------------------------------
// normalizeCitationRequestContext
// ---------------------------------------------------------------------------
describe("normalizeCitationRequestContext", () => {
  it("normalizes valid context", () => {
    const result = normalizeCitationRequestContext({
      trace_id: "t1",
      message: " hola ",
      topic: "renta",
      pais: "colombia",
    });
    expect(result.message).toBe("hola");
    expect(result.topic).toBe("renta");
  });

  it("returns null for empty message", () => {
    expect(normalizeCitationRequestContext({ trace_id: "t1", message: "" })).toBeNull();
  });

  it("returns null for null", () => {
    expect(normalizeCitationRequestContext(null)).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// normalizeExpertPanelLoadOptions
// ---------------------------------------------------------------------------
describe("normalizeExpertPanelLoadOptions", () => {
  it("normalizes valid options", () => {
    const result = normalizeExpertPanelLoadOptions({
      traceId: "t1",
      message: "q1",
      topic: "renta",
      normativeArticleRefs: ["art. 240", "", "art. 240"],
    });
    expect(result.traceId).toBe("t1");
    expect(result.normativeArticleRefs).toEqual(["art. 240"]);
  });

  it("returns null for all-empty", () => {
    expect(normalizeExpertPanelLoadOptions({ traceId: "", message: "" })).toBeNull();
  });

  it("returns null for null", () => {
    expect(normalizeExpertPanelLoadOptions(null)).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// normalizeExpertPanelResponse
// ---------------------------------------------------------------------------
describe("normalizeExpertPanelResponse", () => {
  it("normalizes valid response", () => {
    const result = normalizeExpertPanelResponse({
      ok: true,
      groups: [{ id: "g1" }],
      ungrouped: [],
      total_available: 5,
      trace_id: "t1",
    });
    expect(result.ok).toBe(true);
    expect(result.groups).toHaveLength(1);
    expect(result.total_available).toBe(5);
  });

  it("returns null for empty response", () => {
    expect(normalizeExpertPanelResponse({ ok: false, groups: [], ungrouped: [] })).toBeNull();
  });

  it("returns null for null", () => {
    expect(normalizeExpertPanelResponse(null)).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// normalizeExpertPanelState
// ---------------------------------------------------------------------------
describe("normalizeExpertPanelState", () => {
  it("normalizes populated state", () => {
    const result = normalizeExpertPanelState({
      status: "populated",
      response: { ok: true, groups: [{}], ungrouped: [] },
    });
    expect(result.status).toBe("populated");
    expect(result.response).toBeTruthy();
  });

  it("returns null for populated without response", () => {
    expect(normalizeExpertPanelState({ status: "populated" })).toBeNull();
  });

  it("returns null for null", () => {
    expect(normalizeExpertPanelState(null)).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// deriveFirstQuestionFromTranscriptEntries
// ---------------------------------------------------------------------------
describe("deriveFirstQuestionFromTranscriptEntries", () => {
  it("returns first user text", () => {
    const entries = [
      { role: "assistant", text: "Hola" },
      { role: "user", text: "Mi pregunta" },
    ];
    expect(deriveFirstQuestionFromTranscriptEntries(entries)).toBe("Mi pregunta");
  });

  it("returns empty for no user entries", () => {
    expect(deriveFirstQuestionFromTranscriptEntries([{ role: "assistant", text: "x" }])).toBe("");
  });

  it("returns empty for non-array", () => {
    expect(deriveFirstQuestionFromTranscriptEntries(null)).toBe("");
  });
});

// ---------------------------------------------------------------------------
// normalizeStoredChatSessionState
// ---------------------------------------------------------------------------
describe("normalizeStoredChatSessionState", () => {
  const validState = {
    sessionId: "s1",
    transcriptEntries: [
      { role: "user", text: "Hola" },
      { role: "assistant", text: "Respuesta" },
    ],
    firstQuestion: "Hola",
  };

  it("normalizes valid state", () => {
    const result = normalizeStoredChatSessionState(validState);
    expect(result).toBeTruthy();
    expect(result.sessionId).toBe("s1");
    expect(result.transcriptEntries).toHaveLength(2);
  });

  it("returns null for missing sessionId", () => {
    expect(normalizeStoredChatSessionState({ ...validState, sessionId: "" })).toBeNull();
  });

  it("returns null for empty transcript", () => {
    expect(normalizeStoredChatSessionState({ ...validState, transcriptEntries: [] })).toBeNull();
  });

  it("returns null for null", () => {
    expect(normalizeStoredChatSessionState(null)).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// normalizeStoredChatSessionIndex
// ---------------------------------------------------------------------------
describe("normalizeStoredChatSessionIndex", () => {
  it("normalizes valid index", () => {
    const result = normalizeStoredChatSessionIndex({
      activeSessionId: "s1",
      sessions: [
        { sessionId: "s1", firstQuestion: "Q1", updatedAt: "2026-01-01" },
        { sessionId: "s2", firstQuestion: "Q2", updatedAt: "2026-01-02" },
      ],
    });
    expect(result.activeSessionId).toBe("s1");
    expect(result.sessions).toHaveLength(2);
    // Should be sorted by updatedAt descending
    expect(result.sessions[0].sessionId).toBe("s2");
  });

  it("deduplicates sessions by id", () => {
    const result = normalizeStoredChatSessionIndex({
      sessions: [
        { sessionId: "s1", firstQuestion: "Q1", updatedAt: "2026-01-01" },
        { sessionId: "s1", firstQuestion: "Q1 dup", updatedAt: "2026-01-02" },
      ],
    });
    expect(result.sessions).toHaveLength(1);
  });

  it("returns default for null", () => {
    const result = normalizeStoredChatSessionIndex(null);
    expect(result.sessions).toEqual([]);
    expect(result.activeSessionId).toBe("");
  });
});
