import { getJson } from "@/shared/api/client";
import { getAuthContext } from "@/shared/auth/authContext";
import { bogotaParts, bogotaMidnight, TZ_CO } from "@/shared/dates";
import { createButton } from "@/shared/ui/atoms/button";
import { createButtonChip } from "@/shared/ui/atoms/chip";
import { createGooglyLoader } from "@/shared/ui/googlyLoader";
import { icons } from "@/shared/ui/icons";
import {
  renderMobileHistoryGroups,
  topicColorClass,
  topicDisplayName,
  type MobileHistoryConversationViewModel,
} from "@/shared/ui/organisms/recordCollections";

export interface MobileHistorial {
  show(): void;
  hide(): void;
}

interface ConversationSummary {
  session_id: string;
  first_question: string;
  topic: string | null;
  turn_count: number;
  created_at: string;
  updated_at: string;
}

const PAGE_SIZE = 50;

/**
 * Full-screen historial panel with search, topic pills, and conversation cards.
 * Fetches data from /api/conversations independently (not reusing recordApp state).
 */
export function mountMobileHistorial(
  root: HTMLElement,
  callbacks: {
    onBack: () => void;
    onResumeConversation: (sessionId: string) => void;
  },
): MobileHistorial {
  const panel = root.querySelector<HTMLElement>("#mobile-panel-historial")!;
  const backBtn = panel.querySelector<HTMLButtonElement>(".mobile-historial-back")!;
  const searchInput = panel.querySelector<HTMLInputElement>(
    "#mobile-historial-search-input",
  )!;
  const pillsEl = panel.querySelector<HTMLElement>("#mobile-historial-pills")!;
  const listEl = panel.querySelector<HTMLElement>("#mobile-historial-list")!;
  const footerEl = panel.querySelector<HTMLElement>("#mobile-historial-footer")!;

  let allSessions: ConversationSummary[] = [];
  let allTopics: string[] = [];
  let activeTopicFilter: string | null = null;
  let searchQuery = "";
  let offset = 0;
  let hasMore = true;
  let loading = false;
  let initialLoadDone = false;

  // ── Data fetching ───────────────────────────────────────

  async function loadConversations(append = false): Promise<void> {
    if (loading) return;
    loading = true;

    const ctx = getAuthContext();
    const params = new URLSearchParams({
      tenant_id: ctx.tenantId || "public",
      limit: String(PAGE_SIZE),
      offset: String(offset),
      status: "active",
    });

    try {
      const data = await getJson<{ ok: boolean; sessions: ConversationSummary[] }>(
        `/api/conversations?${params.toString()}`,
      );
      const sessions = data.sessions ?? [];
      if (append) {
        allSessions = [...allSessions, ...sessions];
      } else {
        allSessions = sessions;
      }
      hasMore = sessions.length >= PAGE_SIZE;

      // Extract unique topics
      const topicSet = new Set<string>();
      for (const s of allSessions) {
        if (s.topic) topicSet.add(s.topic);
      }
      allTopics = Array.from(topicSet).sort();
    } catch {
      // Silently fail — historial is non-critical
    } finally {
      loading = false;
    }
  }

  // ── Filtering ───────────────────────────────────────────

  function visibleSessions(): ConversationSummary[] {
    let filtered = allSessions;
    if (activeTopicFilter) {
      filtered = filtered.filter((s) => s.topic === activeTopicFilter);
    }
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (s) => s.first_question.toLowerCase().includes(q),
      );
    }
    return filtered;
  }

  // ── Rendering ───────────────────────────────────────────

  function renderPills(): void {
    const allChip = createButtonChip({
      label: "Todos",
      tone: "neutral",
      className: `mobile-historial-pill${!activeTopicFilter ? " is-active" : ""}`,
    });
    allChip.dataset.topicFilter = "";

    const topicChips = allTopics.map((topic) => {
      const chip = createButtonChip({
        label: topicDisplayName(topic),
        tone: "neutral",
        className: `mobile-historial-pill${activeTopicFilter === topic ? " is-active" : ""}`,
      });
      chip.dataset.topicFilter = topic;
      return chip;
    });

    pillsEl.replaceChildren(allChip, ...topicChips);
  }

  function renderList(): void {
    const sessions = visibleSessions();
    if (sessions.length === 0) {
      listEl.innerHTML = `
        <div class="mobile-empty-state">
          <span class="mobile-empty-state-icon">${icons.document}</span>
          <p class="mobile-empty-state-text">No hay conversaciones registradas</p>
        </div>
      `;
      footerEl.innerHTML = "";
      return;
    }

    const groups = groupByDate(sessions).map(([label, items]) => ({
      items: items.map<MobileHistoryConversationViewModel>((session) => ({
        question: session.first_question,
        sessionId: session.session_id,
        timeAgoLabel: formatTimeAgo(session.updated_at || session.created_at),
        topicClassName: session.topic ? topicColorClass(session.topic) : "topic-default",
        topicLabel: session.topic ? topicDisplayName(session.topic) : "",
      })),
      label,
    }));
    listEl.replaceChildren(renderMobileHistoryGroups(groups));

    // Load more
    if (hasMore) {
      const loadMoreBtn = createButton({ label: "Cargar más", tone: "ghost", className: "mobile-historial-load-more-btn" });
      footerEl.replaceChildren(loadMoreBtn);
    } else {
      footerEl.replaceChildren();
    }
  }

  function render(): void {
    renderPills();
    renderList();
  }

  // ── Show / hide ─────────────────────────────────────────

  function upsertSession(summary: ConversationSummary): void {
    if (!initialLoadDone) return;
    const idx = allSessions.findIndex((s) => s.session_id === summary.session_id);
    if (idx >= 0) {
      allSessions[idx] = { ...allSessions[idx], ...summary };
    } else {
      allSessions.unshift(summary);
    }
    // Add topic if new
    const topic = ((summary as any).detected_topic || summary.topic || "").trim();
    if (topic && !allTopics.includes(topic)) {
      allTopics.push(topic);
    }
    render();
  }

  async function show(): Promise<void> {
    // Reset filters on each open
    activeTopicFilter = null;
    searchQuery = "";
    searchInput.value = "";

    // Switch to historial panel immediately
    const panels = root.querySelectorAll<HTMLElement>(".mobile-panel");
    panels.forEach((p) => p.classList.remove("is-active"));
    panel.classList.add("is-active");

    if (!initialLoadDone) {
      // First open: show loader, fetch, render
      listEl.innerHTML = "";
      footerEl.innerHTML = "";
      pillsEl.innerHTML = "";
      const loader = createGooglyLoader("Cargando historial...");
      listEl.appendChild(loader.el);

      offset = 0;
      await loadConversations(false);
      initialLoadDone = true;
      loader.remove();
      render();
    } else {
      // Subsequent opens: render from cache — no refetch
      render();
    }
  }

  function hide(): void {
    panel.classList.remove("is-active");
    callbacks.onBack();
  }

  // ── Event listeners ─────────────────────────────────────

  backBtn.addEventListener("click", hide);

  pillsEl.addEventListener("click", (e: Event) => {
    const btn = (e.target as HTMLElement).closest<HTMLButtonElement>(
      "[data-topic-filter]",
    );
    if (!btn) return;
    activeTopicFilter = btn.dataset.topicFilter || null;
    render();
  });

  listEl.addEventListener("click", (e: Event) => {
    const card = (e.target as HTMLElement).closest<HTMLElement>(
      "[data-session-id]",
    );
    if (!card) return;
    const sessionId = card.dataset.sessionId!;
    hide();
    callbacks.onResumeConversation(sessionId);
  });

  footerEl.addEventListener("click", async (e: Event) => {
    const btn = (e.target as HTMLElement).closest<HTMLButtonElement>(
      ".mobile-historial-load-more-btn",
    );
    if (!btn || loading) return;
    offset += PAGE_SIZE;
    await loadConversations(true);
    render();
  });

  // Debounced search
  let searchTimer: ReturnType<typeof setTimeout>;
  searchInput.addEventListener("input", () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      searchQuery = searchInput.value.trim();
      renderList();
    }, 250);
  });

  // Listen for upsert events from the chat app
  document.addEventListener("lia:historial-upsert", ((e: CustomEvent) => {
    const summary = e.detail as ConversationSummary | null;
    if (summary?.session_id) upsertSession(summary);
  }) as EventListener);

  return { show, hide, upsertSession };
}

// ── Helpers ───────────────────────────────────────────────

function escapeHtml(text: string): string {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function groupByDate(
  sessions: ConversationSummary[],
): Array<[string, ConversationSummary[]]> {
  const now = new Date();
  const nowP = bogotaParts(now);
  const today = bogotaMidnight(nowP.year, nowP.month, nowP.day);
  const yesterday = new Date(today.getTime() - 86400000);
  const weekAgo = new Date(today.getTime() - 7 * 86400000);

  const groups: Map<string, ConversationSummary[]> = new Map();

  for (const s of sessions) {
    const d = new Date(s.updated_at || s.created_at);
    let label: string;
    if (d >= today) {
      label = "Hoy";
    } else if (d >= yesterday) {
      label = "Ayer";
    } else if (d >= weekAgo) {
      label = "Esta semana";
    } else {
      const month = d.toLocaleString("es-CO", { month: "long", timeZone: TZ_CO });
      const dp = bogotaParts(d);
      label = `${month.charAt(0).toUpperCase() + month.slice(1)} ${dp.year}`;
    }
    if (!groups.has(label)) groups.set(label, []);
    groups.get(label)!.push(s);
  }

  return Array.from(groups.entries());
}

function formatTimeAgo(dateStr: string): string {
  const d = new Date(dateStr);
  const now = Date.now();
  const diffMs = now - d.getTime();
  const diffMin = Math.floor(diffMs / 60000);

  if (diffMin < 1) return "ahora";
  if (diffMin < 60) return `hace ${diffMin}m`;
  const diffH = Math.floor(diffMin / 60);
  if (diffH < 24) return `hace ${diffH}h`;
  const diffD = Math.floor(diffH / 24);
  if (diffD === 1) return "ayer";
  if (diffD < 7) return `hace ${diffD}d`;
  return d.toLocaleDateString("es-CO", { day: "numeric", month: "short", timeZone: TZ_CO });
}
