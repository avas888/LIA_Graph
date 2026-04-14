export type MobileTabId = "chat" | "normativa" | "interpretacion";

export interface MobileNavOptions {
  onChatTabReclick?: () => void;
}

export interface MobileNav {
  switchTab(id: MobileTabId): void;
  updateBadge(tab: MobileTabId, count: number): void;
  resetBadges(): void;
  activeTab(): MobileTabId;
}

/**
 * Mount the bottom tab bar controller.
 * Handles tab switching, badge updates, and "go to chat" actions.
 */
export function mountMobileNav(root: HTMLElement, options: MobileNavOptions = {}): MobileNav {
  const tabBar = root.querySelector<HTMLElement>(".mobile-tab-bar")!;
  const tabs = tabBar.querySelectorAll<HTMLButtonElement>(".mobile-tab");
  const panels: Record<string, HTMLElement | null> = {
    chat: root.querySelector<HTMLElement>("#mobile-panel-chat"),
    normativa: root.querySelector<HTMLElement>("#mobile-panel-normativa"),
    interpretacion: root.querySelector<HTMLElement>("#mobile-panel-interpretacion"),
  };

  let current: MobileTabId = "chat";

  function switchTab(id: MobileTabId): void {
    current = id;
    // Update tab buttons
    tabs.forEach((btn) => {
      btn.classList.toggle("is-active", btn.dataset.tab === id);
    });
    // Update panels
    for (const [key, panel] of Object.entries(panels)) {
      panel?.classList.toggle("is-active", key === id);
    }
    // Hide historial when switching to main tabs
    const histPanel = root.querySelector<HTMLElement>("#mobile-panel-historial");
    if (histPanel) histPanel.classList.remove("is-active");
  }

  function updateBadge(tab: MobileTabId, count: number): void {
    const btn = tabBar.querySelector<HTMLButtonElement>(
      `.mobile-tab[data-tab="${tab}"]`,
    );
    if (!btn) return;
    const badge = btn.querySelector<HTMLElement>(".mobile-tab-badge");
    if (!badge) return;
    if (count > 0) {
      badge.textContent = String(count);
      badge.hidden = false;
    } else {
      badge.hidden = true;
    }
  }

  function resetBadges(): void {
    updateBadge("normativa", 0);
    updateBadge("interpretacion", 0);
  }

  function activeTab(): MobileTabId {
    return current;
  }

  // ── Click handlers ──────────────────────────────────────

  tabBar.addEventListener("click", (e: Event) => {
    const btn = (e.target as HTMLElement).closest<HTMLButtonElement>(
      ".mobile-tab",
    );
    if (!btn?.dataset.tab) return;
    const id = btn.dataset.tab as MobileTabId;
    if (id === "chat" && current === "chat" && options.onChatTabReclick) {
      options.onChatTabReclick();
      return;
    }
    switchTab(id);
  });

  // "Go to chat" buttons in empty states
  root.addEventListener("click", (e: Event) => {
    const target = e.target as HTMLElement;
    if (target.closest("[data-go-to-chat]")) {
      switchTab("chat");
    }
  });

  return { switchTab, updateBadge, resetBadges, activeTab };
}
