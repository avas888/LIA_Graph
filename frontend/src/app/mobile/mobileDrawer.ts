import { getAuthContext, clearAuthContext } from "@/shared/auth/authContext";

export interface MobileDrawer {
  open(): void;
  close(): void;
}

/**
 * Hamburger drawer — slides in from right.
 * Shows user info, new conversation, historial, logout.
 *
 * In public mode (`renderMobileShell(i18n, "public")`) the user-info block,
 * the historial drawer item, and the logout footer are all omitted from the
 * DOM. This function tolerates their absence via querySelector + null guards
 * — no controller rebuild needed for the public path.
 */
export function mountMobileDrawer(
  root: HTMLElement,
  callbacks: {
    onNewConversation: () => void;
    onHistorial?: () => void;
  },
): MobileDrawer {
  const drawerNode = root.querySelector<HTMLElement>(".mobile-drawer");
  const panelNode = drawerNode?.querySelector<HTMLElement>(".mobile-drawer-panel") ?? null;
  const scrimNode = drawerNode?.querySelector<HTMLElement>(".mobile-drawer-scrim") ?? null;
  const closeBtn = drawerNode?.querySelector<HTMLButtonElement>(".mobile-drawer-close") ?? null;
  const hamburgerBtnNode = root.querySelector<HTMLButtonElement>(".mobile-hamburger-btn");

  if (!drawerNode || !panelNode || !scrimNode || !hamburgerBtnNode) {
    // Drawer DOM is incomplete — return a no-op controller instead of
    // throwing. Callers (e.g. public mobile) may rely on a skinnier shell.
    return { open: () => {}, close: () => {} };
  }
  // Narrowed, closure-stable locals so TS knows these are non-null inside
  // the open/close/event-listener closures below.
  const drawer: HTMLElement = drawerNode;
  const panel: HTMLElement = panelNode;
  const scrim: HTMLElement = scrimNode;
  const hamburgerBtn: HTMLButtonElement = hamburgerBtnNode;

  // ── Populate user info (skipped in public mode — elements are absent) ─

  const nameEl = root.querySelector<HTMLElement>("#mobile-drawer-user-name");
  const roleEl = root.querySelector<HTMLElement>("#mobile-drawer-user-role");
  if (nameEl || roleEl) {
    const auth = getAuthContext();
    if (nameEl) nameEl.textContent = auth.userId || "Usuario";
    if (roleEl) {
      const roleLabels: Record<string, string> = {
        tenant_admin: "Administrador",
        platform_admin: "Administrador de Plataforma",
        tenant_user: "Contador",
      };
      roleEl.textContent = roleLabels[auth.role] ?? "Contador";
    }
  }

  // ── Open / close ────────────────────────────────────────

  function open(): void {
    drawer.hidden = false;
    void drawer.offsetHeight;
    drawer.classList.add("is-open");
    document.body.style.overflow = "hidden";
  }

  function close(): void {
    drawer.classList.remove("is-open");
    document.body.style.overflow = "";
    const onEnd = () => {
      drawer.hidden = true;
      panel.removeEventListener("transitionend", onEnd);
    };
    panel.addEventListener("transitionend", onEnd, { once: true });
    setTimeout(() => {
      if (!drawer.classList.contains("is-open")) {
        drawer.hidden = true;
      }
    }, 400);
  }

  // ── Event listeners ─────────────────────────────────────

  hamburgerBtn.addEventListener("click", open);
  closeBtn?.addEventListener("click", close);
  scrim.addEventListener("click", close);

  // Escape key
  document.addEventListener("keydown", (e: KeyboardEvent) => {
    if (e.key === "Escape" && !drawer.hidden) close();
  });

  // Drawer actions
  drawer.addEventListener("click", (e: Event) => {
    const btn = (e.target as HTMLElement).closest<HTMLButtonElement>(
      "[data-drawer-action]",
    );
    if (!btn) return;

    const action = btn.dataset.drawerAction;
    close();

    switch (action) {
      case "new-conversation": {
        callbacks.onNewConversation();
        break;
      }
      case "historial": {
        // In public mode the historial item is absent from the DOM, so
        // this branch never fires. Guard anyway in case a future refactor
        // renders the button but the public path doesn't provide the
        // callback.
        callbacks.onHistorial?.();
        break;
      }
      case "logout": {
        clearAuthContext();
        localStorage.removeItem("lia_access_token");
        localStorage.removeItem("lia_embed_token");
        window.location.href = "/login";
        break;
      }
    }
  });

  return { open, close };
}
