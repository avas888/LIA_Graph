/**
 * Record tab composition root — conversation history with topic filters.
 *
 * All sessions are loaded once from the API. Topic filtering is purely
 * client-side — no round-trip, no loader, instant.
 */

import "@/styles/record/layout.css";
import "@/styles/record/cards.css";
import "@/styles/record/pills.css";
import "@/styles/record/transcript.css";

import {
  createInitialState,
  fetchConversations,
  fetchDistinctTopics,
  fetchTenants,
  type RecordState,
  type ConversationSummary,
  type TenantOption,
} from "./recordState";
import {
  renderFilterPills,
  renderUserFilterDropdown,
  renderConversationList,
  renderLoadMore,
} from "./recordView";
import { showTranscriptModal } from "./recordTranscriptModal";
import { isAdmin } from "@/shared/auth/authContext";
import type { I18nRuntime } from "@/shared/i18n";
import { createGooglyLoader } from "@/shared/ui/googlyLoader";

interface RecordAppOptions {
  i18n: I18nRuntime;
}

export function mountRecordApp(
  container: HTMLElement,
  { i18n }: RecordAppOptions,
): void {
  let state: RecordState = createInitialState();
  let allTopics: string[] = [];
  let allTenants: TenantOption[] = [];
  let allSessions: ConversationSummary[] = [];  // full unfiltered cache

  // ── DOM structure ──────────────────────────────────────
  container.innerHTML = `
    <div class="record-shell">
      <div class="record-admin-filters"></div>
      <div class="record-filters"></div>
      <div class="record-list"></div>
      <div class="record-footer"></div>
      <dialog class="record-transcript-dialog"></dialog>
    </div>
  `;

  const adminFiltersEl = container.querySelector<HTMLElement>(".record-admin-filters")!;
  const filtersEl = container.querySelector<HTMLElement>(".record-filters")!;
  const listEl = container.querySelector<HTMLElement>(".record-list")!;
  const footerEl = container.querySelector<HTMLElement>(".record-footer")!;

  // ── Googly loader for initial load only ─────────────────
  const googly = createGooglyLoader(i18n.t("record.loading"));

  // ── Filtered view ────────────────────────────────────────

  function visibleSessions(): ConversationSummary[] {
    if (!state.activeTopicFilter) return allSessions;
    return allSessions.filter((s) => s.topic === state.activeTopicFilter);
  }

  // ── Render ─────────────────────────────────────────────

  function render(): void {
    const userFilter = renderUserFilterDropdown(allTenants, state.activeUserFilter);
    adminFiltersEl.replaceChildren(...(userFilter ? [userFilter] : []));
    filtersEl.replaceChildren(renderFilterPills(allTopics, state.activeTopicFilter, i18n));

    if (state.loading && allSessions.length === 0) {
      listEl.replaceChildren();
      listEl.appendChild(googly.el);
      googly.show();
    } else {
      googly.hide();
      listEl.replaceChildren(renderConversationList(visibleSessions(), i18n));
    }

    footerEl.replaceChildren(renderLoadMore(state.hasMore, state.loading, i18n));
  }

  // ── Load data (API — only on initial + load-more) ──────

  async function load(append = false): Promise<void> {
    state = { ...state, loading: true };
    render();
    state = await fetchConversations(state, append);
    // Cache all sessions from the API (unfiltered)
    if (append) {
      allSessions = [...allSessions, ...state.sessions.slice(allSessions.length)];
    } else {
      allSessions = state.sessions;
    }
    render();
  }

  // ── Event handlers ─────────────────────────────────────

  // User filter — re-fetches from API
  adminFiltersEl.addEventListener("change", (e) => {
    const select = (e.target as HTMLElement).closest<HTMLSelectElement>(".record-tenant-filter");
    if (!select) return;
    state = { ...state, activeUserFilter: select.value || null, offset: 0, activeTopicFilter: null };
    allSessions = [];
    void load();
  });

  // Topic filter pills — instant client-side filtering
  filtersEl.addEventListener("click", (e) => {
    const btn = (e.target as HTMLElement).closest<HTMLElement>("[data-topic-filter]");
    if (!btn) return;
    const topic = btn.dataset.topicFilter || null;
    state = { ...state, activeTopicFilter: topic };
    render();
  });

  // Open transcript modal on card click (but not on Resume button)
  const dialogEl = container.querySelector<HTMLDialogElement>(".record-transcript-dialog")!;
  listEl.addEventListener("click", (e) => {
    const target = e.target as HTMLElement;
    // Let Resume button pass through to its own handler below
    if (target.closest("[data-resume-session]")) return;
    const card = target.closest<HTMLElement>(".record-card");
    if (!card) return;
    const sessionId = card.dataset.sessionId;
    if (!sessionId) return;
    void showTranscriptModal(dialogEl, sessionId, i18n, card.dataset.tenantId);
  });

  // Resume conversation
  listEl.addEventListener("click", (e) => {
    const btn = (e.target as HTMLElement).closest<HTMLElement>("[data-resume-session]");
    if (!btn) return;
    const sessionId = btn.dataset.resumeSession;
    if (!sessionId) return;
    document.dispatchEvent(
      new CustomEvent("resume-conversation", { detail: { sessionId } }),
    );
  });

  // Load more — always fetches unfiltered from API
  footerEl.addEventListener("click", (e) => {
    const btn = (e.target as HTMLElement).closest<HTMLElement>(".record-load-more");
    if (!btn || state.loading) return;
    state = { ...state, offset: state.offset + 50 };
    void load(true);
  });

  // ── Initial load ───────────────────────────────────────
  const initialLoads: Promise<void>[] = [
    fetchDistinctTopics().then((topics) => { allTopics = topics; }),
    load(),
  ];
  if (isAdmin()) {
    initialLoads.push(fetchTenants().then((tenants) => { allTenants = tenants; }));
  }
  void Promise.all(initialLoads).then(() => render());

  // Listen for upsert events from the chat app
  document.addEventListener("lia:historial-upsert", ((e: CustomEvent) => {
    const summary = e.detail as ConversationSummary | null;
    if (!summary?.session_id) return;
    const idx = allSessions.findIndex((s) => s.session_id === summary.session_id);
    if (idx >= 0) {
      allSessions[idx] = { ...allSessions[idx], ...summary };
    } else {
      allSessions.unshift(summary);
    }
    const topic = (summary.detected_topic || "").trim();
    if (topic && !allTopics.includes(topic)) {
      allTopics.push(topic);
    }
    state = { ...state, sessions: allSessions };
    render();
  }) as EventListener);
}
