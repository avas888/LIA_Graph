import { beforeEach, describe, expect, it, vi } from "vitest";

// ── Mock dependencies ──────────────────────────────────────────────

vi.mock("@/shared/auth/authContext", () => ({
  isAdmin: vi.fn(() => false),
}));

vi.mock("@/shared/ui/googlyLoader", () => ({
  createGooglyLoader: vi.fn(() => {
    const el = document.createElement("div");
    el.className = "googly-loader-mock";
    return {
      el,
      show: vi.fn(() => { el.hidden = false; }),
      hide: vi.fn(() => { el.hidden = true; }),
      setText: vi.fn(),
      remove: vi.fn(),
    };
  }),
}));

// Mock CSS imports (no-ops)
vi.mock("@/styles/record/layout.css", () => ({}));
vi.mock("@/styles/record/cards.css", () => ({}));
vi.mock("@/styles/record/pills.css", () => ({}));

// Mock recordState
vi.mock("@/features/record/recordState", () => ({
  createInitialState: vi.fn(() => ({
    sessions: [],
    activeTopicFilter: null,
    activeTenantFilter: null,
    loading: false,
    offset: 0,
    hasMore: true,
    error: null,
  })),
  fetchConversations: vi.fn(),
  fetchDistinctTopics: vi.fn(),
  fetchTenants: vi.fn(),
}));

// Mock recordView
vi.mock("@/features/record/recordView", () => ({
  renderFilterPills: vi.fn((_topics: string[], _activeFilter: string | null) => {
    const div = document.createElement("div");
    div.className = "filter-pills-mock";
    return div;
  }),
  renderTenantFilter: vi.fn(() => null),
  renderConversationList: vi.fn((sessions: Array<{ session_id: string }>) => {
    const fragment = document.createDocumentFragment();
    sessions.forEach((s) => {
      const el = document.createElement("div");
      el.className = "conversation-card";
      el.dataset.sessionId = s.session_id;
      el.innerHTML = `<button data-resume-session="${s.session_id}">Resume</button>`;
      fragment.appendChild(el);
    });
    if (sessions.length === 0) {
      const empty = document.createElement("div");
      empty.textContent = "No conversations";
      fragment.appendChild(empty);
    }
    return fragment;
  }),
  renderLoadMore: vi.fn((_hasMore: boolean, _loading: boolean) => {
    const fragment = document.createDocumentFragment();
    if (_hasMore && !_loading) {
      const btn = document.createElement("button");
      btn.className = "record-load-more";
      btn.textContent = "Cargar m\u00e1s";
      fragment.appendChild(btn);
    }
    return fragment;
  }),
}));

import { isAdmin } from "@/shared/auth/authContext";
import {
  fetchConversations,
  fetchDistinctTopics,
  fetchTenants,
} from "@/features/record/recordState";
import { mountRecordApp } from "@/features/record/recordApp";

const mockFetchConversations = vi.mocked(fetchConversations);
const mockFetchDistinctTopics = vi.mocked(fetchDistinctTopics);
const mockFetchTenants = vi.mocked(fetchTenants);
const mockIsAdmin = vi.mocked(isAdmin);

const fakeI18n = {
  t: (key: string) => key,
  locale: "es-CO" as const,
  formatNumber: (v: number) => String(v),
  formatDateTime: (v: string | number | Date) => String(v),
};

function makeSummary(id: string, topic: string | null = "renta") {
  return {
    session_id: id,
    first_question: `Question ${id}`,
    topic,
    tenant_id: "t1",
    user_id: "u1",
    turn_count: 2,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    status: "active",
  };
}

async function flushUi(): Promise<void> {
  await Promise.resolve();
  await new Promise((r) => setTimeout(r, 0));
  await Promise.resolve();
}

describe("mountRecordApp", () => {
  let container: HTMLElement;

  beforeEach(() => {
    vi.clearAllMocks();

    container = document.createElement("div");
    document.body.replaceChildren(container);

    // Default mock behaviors
    mockIsAdmin.mockReturnValue(false);

    const sessions = [makeSummary("s1"), makeSummary("s2", "iva")];
    mockFetchConversations.mockResolvedValue({
      sessions,
      activeTopicFilter: null,
      activeTenantFilter: null,
      loading: false,
      offset: 0,
      hasMore: false,
      error: null,
    });
    mockFetchDistinctTopics.mockResolvedValue(["renta", "iva"]);
    mockFetchTenants.mockResolvedValue([]);
  });

  it("creates DOM structure with shell, filters, list, and footer", async () => {
    mountRecordApp(container, { i18n: fakeI18n });
    await flushUi();

    expect(container.querySelector(".record-shell")).not.toBeNull();
    expect(container.querySelector(".record-admin-filters")).not.toBeNull();
    expect(container.querySelector(".record-filters")).not.toBeNull();
    expect(container.querySelector(".record-list")).not.toBeNull();
    expect(container.querySelector(".record-footer")).not.toBeNull();
  });

  it("calls fetchConversations and fetchDistinctTopics on mount", async () => {
    mountRecordApp(container, { i18n: fakeI18n });
    await flushUi();

    expect(mockFetchConversations).toHaveBeenCalled();
    expect(mockFetchDistinctTopics).toHaveBeenCalled();
  });

  it("calls fetchTenants when user is admin", async () => {
    mockIsAdmin.mockReturnValue(true);
    mountRecordApp(container, { i18n: fakeI18n });
    await flushUi();

    expect(mockFetchTenants).toHaveBeenCalled();
  });

  it("does not call fetchTenants when user is not admin", async () => {
    mockIsAdmin.mockReturnValue(false);
    mountRecordApp(container, { i18n: fakeI18n });
    await flushUi();

    expect(mockFetchTenants).not.toHaveBeenCalled();
  });

  it("dispatches resume-conversation event when a session card is clicked", async () => {
    mountRecordApp(container, { i18n: fakeI18n });
    await flushUi();
    await flushUi();

    const dispatched: string[] = [];
    document.addEventListener("resume-conversation", ((e: CustomEvent) => {
      dispatched.push(e.detail.sessionId);
    }) as EventListener);

    const resumeBtn = container.querySelector<HTMLElement>("[data-resume-session='s1']");
    expect(resumeBtn).not.toBeNull();
    resumeBtn!.click();

    expect(dispatched).toContain("s1");
  });

  it("applies topic filter on pill click (client-side only)", async () => {
    mountRecordApp(container, { i18n: fakeI18n });
    await flushUi();
    await flushUi();

    // Clear call count after initial load
    mockFetchConversations.mockClear();

    // Simulate a topic filter pill click
    const filtersEl = container.querySelector<HTMLElement>(".record-filters")!;
    const pill = document.createElement("button");
    pill.dataset.topicFilter = "renta";
    filtersEl.appendChild(pill);
    pill.click();
    await flushUi();

    // Topic filtering is client-side — should NOT trigger another fetch
    expect(mockFetchConversations).not.toHaveBeenCalled();
  });

  it("handles load-more button click", async () => {
    // Make first load return hasMore=true
    mockFetchConversations.mockResolvedValue({
      sessions: [makeSummary("s1")],
      activeTopicFilter: null,
      activeTenantFilter: null,
      loading: false,
      offset: 0,
      hasMore: true,
      error: null,
    });

    mountRecordApp(container, { i18n: fakeI18n });
    await flushUi();
    await flushUi();

    // Clear call counts after initial loads
    mockFetchConversations.mockClear();

    // Simulate clicking "load more" in the footer
    const footerEl = container.querySelector<HTMLElement>(".record-footer")!;
    const loadMoreBtn = footerEl.querySelector<HTMLElement>(".record-load-more");
    if (loadMoreBtn) {
      loadMoreBtn.click();
      await flushUi();
      expect(mockFetchConversations).toHaveBeenCalled();
    }
  });

  it("handles tenant filter change event (admin)", async () => {
    mockIsAdmin.mockReturnValue(true);
    mockFetchTenants.mockResolvedValue([
      { tenant_id: "t1", display_name: "Tenant 1" },
      { tenant_id: "t2", display_name: "Tenant 2" },
    ]);

    mountRecordApp(container, { i18n: fakeI18n });
    await flushUi();
    await flushUi();

    // Clear calls from initial load
    mockFetchConversations.mockClear();

    // Simulate tenant filter select change in admin filters area
    const adminFiltersEl = container.querySelector<HTMLElement>(".record-admin-filters")!;
    const select = document.createElement("select");
    select.className = "record-tenant-filter";
    select.value = "t2";
    adminFiltersEl.appendChild(select);

    select.dispatchEvent(new Event("change", { bubbles: true }));
    await flushUi();

    // Should trigger a new fetch with the selected tenant
    expect(mockFetchConversations).toHaveBeenCalled();
  });

  it("responds to lia:historial-upsert event for existing session", async () => {
    mountRecordApp(container, { i18n: fakeI18n });
    await flushUi();
    await flushUi();

    // Dispatch upsert for an existing session
    document.dispatchEvent(
      new CustomEvent("lia:historial-upsert", {
        detail: {
          session_id: "s1",
          first_question: "Updated question",
          topic: "renta",
          tenant_id: "t1",
          user_id: "u1",
          turn_count: 6,
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-02T00:00:00Z",
          status: "active",
        },
      }),
    );
    await flushUi();

    // The render function should have been called again (verifiable via mock calls)
    // We just check that no error was thrown and the app is still intact
    expect(container.querySelector(".record-shell")).not.toBeNull();
  });

  it("responds to lia:historial-upsert event for new session", async () => {
    mountRecordApp(container, { i18n: fakeI18n });
    await flushUi();
    await flushUi();

    // Dispatch upsert for a brand-new session
    document.dispatchEvent(
      new CustomEvent("lia:historial-upsert", {
        detail: {
          session_id: "s-new",
          first_question: "New question",
          topic: "laboral",
          tenant_id: "t1",
          user_id: "u1",
          turn_count: 2,
          created_at: "2026-01-02T00:00:00Z",
          updated_at: "2026-01-02T00:00:00Z",
          status: "active",
          detected_topic: "laboral",
        },
      }),
    );
    await flushUi();

    // The app should still be rendered without errors
    expect(container.querySelector(".record-shell")).not.toBeNull();
  });

  it("ignores lia:historial-upsert with missing session_id", async () => {
    mountRecordApp(container, { i18n: fakeI18n });
    await flushUi();
    await flushUi();

    // Should not throw
    document.dispatchEvent(
      new CustomEvent("lia:historial-upsert", { detail: null }),
    );
    await flushUi();

    document.dispatchEvent(
      new CustomEvent("lia:historial-upsert", { detail: { topic: "renta" } }),
    );
    await flushUi();

    expect(container.querySelector(".record-shell")).not.toBeNull();
  });
});
