import { beforeEach, describe, expect, it, vi } from "vitest";

// ── Mock dependencies ──────────────────────────────────────────────

vi.mock("@/shared/api/client", () => ({
  getJson: vi.fn(),
}));

vi.mock("@/shared/auth/authContext", () => ({
  getAuthContext: vi.fn(() => ({
    tenantId: "tenant-test",
    userId: "user-1",
    role: "tenant_admin",
    activeCompanyId: "",
    integrationId: "",
  })),
}));

import { getJson } from "@/shared/api/client";
import {
  createInitialState,
  extractTopics,
  fetchConversations,
  fetchDistinctTopics,
  fetchTenants,
  type ConversationSummary,
  type RecordState,
} from "@/features/record/recordState";

const mockGetJson = vi.mocked(getJson);

function makeSummary(overrides: Partial<ConversationSummary> = {}): ConversationSummary {
  return {
    session_id: "sess-1",
    first_question: "Test question",
    topic: "renta",
    tenant_id: "tenant-test",
    user_id: "user-1",
    turn_count: 4,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    status: "active",
    ...overrides,
  };
}

// ── createInitialState ──────────────────────────────────────────────

describe("createInitialState", () => {
  it("returns a default RecordState", () => {
    const state = createInitialState();
    expect(state.sessions).toEqual([]);
    expect(state.activeTopicFilter).toBeNull();
    expect(state.activeTenantFilter).toBeNull();
    expect(state.loading).toBe(false);
    expect(state.offset).toBe(0);
    expect(state.hasMore).toBe(true);
    expect(state.error).toBeNull();
  });
});

// ── extractTopics ────────────────────────────────────────────────────

describe("extractTopics", () => {
  it("extracts unique topics sorted alphabetically", () => {
    const sessions = [
      makeSummary({ topic: "renta" }),
      makeSummary({ topic: "iva" }),
      makeSummary({ topic: "renta" }),
      makeSummary({ topic: "laboral" }),
    ];
    expect(extractTopics(sessions)).toEqual(["iva", "laboral", "renta"]);
  });

  it("ignores null/empty topics", () => {
    const sessions = [
      makeSummary({ topic: null }),
      makeSummary({ topic: "iva" }),
    ];
    expect(extractTopics(sessions)).toEqual(["iva"]);
  });

  it("returns empty array for empty input", () => {
    expect(extractTopics([])).toEqual([]);
  });

  it("returns empty array when all topics are null", () => {
    const sessions = [
      makeSummary({ topic: null }),
      makeSummary({ topic: null }),
    ];
    expect(extractTopics(sessions)).toEqual([]);
  });
});

// ── fetchConversations ──────────────────────────────────────────────

describe("fetchConversations", () => {
  beforeEach(() => {
    vi.mocked(getJson).mockReset();
  });

  it("fetches conversations and updates state", async () => {
    const sessions = [makeSummary({ session_id: "s1" }), makeSummary({ session_id: "s2" })];
    mockGetJson.mockResolvedValue({ ok: true, sessions });

    const state = createInitialState();
    const next = await fetchConversations(state, false);

    expect(next.sessions).toHaveLength(2);
    expect(next.loading).toBe(false);
    expect(next.error).toBeNull();
  });

  it("builds URL with activeTenantFilter when set", async () => {
    mockGetJson.mockResolvedValue({ ok: true, sessions: [] });

    const state: RecordState = {
      ...createInitialState(),
      activeTenantFilter: "tenant-override",
    };
    await fetchConversations(state, false);

    const calledUrl = mockGetJson.mock.calls[0][0] as string;
    expect(calledUrl).toContain("tenant_id=tenant-override");
  });

  it("falls back to authContext tenantId when activeTenantFilter is null", async () => {
    mockGetJson.mockResolvedValue({ ok: true, sessions: [] });

    const state = createInitialState();
    await fetchConversations(state, false);

    const calledUrl = mockGetJson.mock.calls[0][0] as string;
    expect(calledUrl).toContain("tenant_id=tenant-test");
  });

  it("includes limit, offset, and status in URL params", async () => {
    mockGetJson.mockResolvedValue({ ok: true, sessions: [] });

    const state: RecordState = { ...createInitialState(), offset: 100 };
    await fetchConversations(state, false);

    const calledUrl = mockGetJson.mock.calls[0][0] as string;
    expect(calledUrl).toContain("limit=50");
    expect(calledUrl).toContain("offset=100");
    expect(calledUrl).toContain("status=active");
  });

  it("appends sessions when append=true", async () => {
    const existingSessions = [makeSummary({ session_id: "s1" })];
    const newSessions = [makeSummary({ session_id: "s2" })];
    mockGetJson.mockResolvedValue({ ok: true, sessions: newSessions });

    const state: RecordState = { ...createInitialState(), sessions: existingSessions };
    const next = await fetchConversations(state, true);

    expect(next.sessions).toHaveLength(2);
    expect(next.sessions[0].session_id).toBe("s1");
    expect(next.sessions[1].session_id).toBe("s2");
  });

  it("replaces sessions when append=false", async () => {
    const newSessions = [makeSummary({ session_id: "s-new" })];
    mockGetJson.mockResolvedValue({ ok: true, sessions: newSessions });

    const state: RecordState = {
      ...createInitialState(),
      sessions: [makeSummary({ session_id: "s-old" })],
    };
    const next = await fetchConversations(state, false);

    expect(next.sessions).toHaveLength(1);
    expect(next.sessions[0].session_id).toBe("s-new");
  });

  it("sets hasMore=true when response has PAGE_SIZE (50) sessions", async () => {
    const sessions = Array.from({ length: 50 }, (_, i) =>
      makeSummary({ session_id: `s${i}` }),
    );
    mockGetJson.mockResolvedValue({ ok: true, sessions });

    const next = await fetchConversations(createInitialState(), false);
    expect(next.hasMore).toBe(true);
  });

  it("sets hasMore=false when response has fewer than PAGE_SIZE sessions", async () => {
    const sessions = [makeSummary({ session_id: "s1" })];
    mockGetJson.mockResolvedValue({ ok: true, sessions });

    const next = await fetchConversations(createInitialState(), false);
    expect(next.hasMore).toBe(false);
  });

  it("handles missing sessions field in response", async () => {
    mockGetJson.mockResolvedValue({ ok: true });

    const next = await fetchConversations(createInitialState(), false);
    expect(next.sessions).toEqual([]);
    expect(next.hasMore).toBe(false);
  });

  it("handles API error gracefully", async () => {
    mockGetJson.mockRejectedValue(new Error("Server error"));

    const next = await fetchConversations(createInitialState(), false);
    expect(next.loading).toBe(false);
    expect(next.error).toBe("Server error");
    expect(next.sessions).toEqual([]);
  });

  it("uses generic error message for non-Error throws", async () => {
    mockGetJson.mockRejectedValue("something went wrong");

    const next = await fetchConversations(createInitialState(), false);
    expect(next.error).toBe("Error cargando conversaciones");
  });
});

// ── fetchTenants ──────────────────────────────────────────────────────

describe("fetchTenants", () => {
  beforeEach(() => {
    vi.mocked(getJson).mockReset();
  });

  it("returns sorted tenants from API", async () => {
    mockGetJson.mockResolvedValue({
      ok: true,
      tenants: [
        { tenant_id: "t2", display_name: "Zeta Corp" },
        { tenant_id: "t1", display_name: "Alpha Inc" },
      ],
    });

    const result = await fetchTenants();
    expect(result).toHaveLength(2);
    expect(result[0].display_name).toBe("Alpha Inc");
    expect(result[1].display_name).toBe("Zeta Corp");
  });

  it("returns empty array on API error", async () => {
    mockGetJson.mockRejectedValue(new Error("fail"));
    const result = await fetchTenants();
    expect(result).toEqual([]);
  });

  it("returns empty array when tenants field is missing", async () => {
    mockGetJson.mockResolvedValue({ ok: true });
    const result = await fetchTenants();
    expect(result).toEqual([]);
  });

  it("calls the admin tenants endpoint", async () => {
    mockGetJson.mockResolvedValue({ ok: true, tenants: [] });
    await fetchTenants();
    expect(mockGetJson).toHaveBeenCalledWith("/api/admin/tenants");
  });
});

// ── fetchDistinctTopics ──────────────────────────────────────────────

describe("fetchDistinctTopics", () => {
  beforeEach(() => {
    vi.mocked(getJson).mockReset();
  });

  it("returns sorted topics from API", async () => {
    mockGetJson.mockResolvedValue({ ok: true, topics: ["renta", "iva", "laboral"] });

    const result = await fetchDistinctTopics();
    expect(result).toEqual(["iva", "laboral", "renta"]);
  });

  it("includes tenant_id and status in request URL", async () => {
    mockGetJson.mockResolvedValue({ ok: true, topics: [] });
    await fetchDistinctTopics();

    const calledUrl = mockGetJson.mock.calls[0][0] as string;
    expect(calledUrl).toContain("tenant_id=tenant-test");
    expect(calledUrl).toContain("status=active");
    expect(calledUrl).toContain("/api/conversations/topics");
  });

  it("returns empty array on error", async () => {
    mockGetJson.mockRejectedValue(new Error("fail"));
    const result = await fetchDistinctTopics();
    expect(result).toEqual([]);
  });

  it("returns empty array when topics field is missing", async () => {
    mockGetJson.mockResolvedValue({ ok: true });
    const result = await fetchDistinctTopics();
    expect(result).toEqual([]);
  });
});
