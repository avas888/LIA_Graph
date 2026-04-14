import { getLocalStorage, type StorageLike } from "@/shared/browser/storage";
import { getAuthContext, getDisplayName, clearAuthContext, isAuthenticated } from "@/shared/auth/authContext";
import { clearApiAccessToken } from "@/shared/api/client";
import { createChatSessionStore } from "@/features/chat/chatSessionStore";
import { createIconButton } from "@/shared/ui/atoms/button";
import { renderBrandMarkHtml } from "@/shared/ui/atoms/brandMark";
import { icons } from "@/shared/ui/icons";

export type TabCategory = "user" | "admin";

export type BrowserTabId =
  | "chat"
  | "record"
  | "ingestion"
  | "backstage"
  | "orchestration"
  | "ratings"
  | "activity"
  | "api";

export interface BrowserTabConfig {
  id: BrowserTabId;
  label: string;
  category: TabCategory;
}

export interface BrowserChromeBrand {
  logoSrc: string;
  logoAlt: string;
  tagline: string;
}

const STORAGE_KEY = "lia_browser_tab";

export function readStoredBrowserTab(storage: StorageLike = getLocalStorage()): BrowserTabId {
  try {
    const raw = storage.getItem(STORAGE_KEY);
    if (
      raw === "chat" ||
      raw === "record" ||
      raw === "ingestion" ||
      raw === "backstage" ||
      raw === "ratings" ||
      raw === "activity"
    )
      return raw;
  } catch {
    // Ignore storage failures.
  }
  return "chat";
}

export function storeBrowserTab(id: BrowserTabId, storage: StorageLike = getLocalStorage()): void {
  if (id === "orchestration") return; // navigates away; don't persist
  try {
    storage.setItem(STORAGE_KEY, id);
  } catch {
    // Ignore storage failures.
  }
}

export function renderBrowserChrome(
  tabs: BrowserTabConfig[],
  activeId: BrowserTabId,
  brand?: BrowserChromeBrand,
): string {
  const userTabs = tabs.filter((t) => t.category === "user");
  const adminTabs = tabs.filter((t) => t.category === "admin");

  const renderButton = (tab: BrowserTabConfig): string =>
    `<button class="browser-tab${tab.id === activeId ? " is-active" : ""}" type="button" role="tab" data-browser-tab="${tab.id}" data-tab-category="${tab.category}" aria-selected="${tab.id === activeId}">${tab.label}</button>`;

  const userButtons = userTabs.map(renderButton).join("");
  const adminButtons = adminTabs.map(renderButton).join("");
  const divider = adminTabs.length > 0 ? `<span class="tab-category-divider" aria-hidden="true"></span>` : "";

  const buttons = userButtons + divider + adminButtons;

  // Brand slot (logo + tagline) sits in the empty dark strip between the
  // tabs and the user menu on desktop. Composed via the `brandMark` atom
  // so the public banner consumes the same canonical contract.
  const brandSlot = brand
    ? renderBrandMarkHtml({
        logoSrc: brand.logoSrc,
        logoAlt: brand.logoAlt,
        tagline: brand.tagline,
      })
    : "";

  // User menu (top-right) — always visible
  const auth = getAuthContext();
  const loggedIn = isAuthenticated();
  const roleLabels: Record<string, string> = {
    platform_admin: "Admin",
    tenant_admin: "Admin Tenant",
    tenant_user: "Usuario",
  };
  const displayRole = loggedIn ? (roleLabels[auth.role] || "") : "";
  const gearBtnHtml = createIconButton({
    iconHtml: icons.gear,
    tone: "ghost",
    className: "user-menu-trigger",
    attrs: { "aria-label": "Menu de usuario", "data-user-menu-trigger": "" },
  }).outerHTML;

  const userMenu = loggedIn
    ? `<div class="user-menu-area">
        <span class="user-menu-role">${displayRole}</span>
        ${gearBtnHtml}
        <div class="user-menu-dropdown" data-user-menu-dropdown hidden>
          <div class="user-menu-info">
            <span class="user-menu-email">${getDisplayName()}</span>
          </div>
          <hr class="user-menu-sep">
          <button class="user-menu-item" type="button" data-user-logout>Cerrar sesion</button>
        </div>
      </div>`
    : `<div class="user-menu-area">
        <a href="/login" class="user-menu-login-link">Iniciar sesion</a>
      </div>`;

  const panels = tabs
    .map(
      (tab) =>
        `<div id="tab-panel-${tab.id}" class="browser-tab-panel${tab.id === activeId ? " is-active" : ""}" role="tabpanel"></div>`,
    )
    .join("");

  return `<div class="browser-chrome"><nav class="browser-tab-bar" role="tablist" aria-label="LIA">${buttons}${brandSlot}${userMenu}</nav><div class="browser-viewport">${panels}</div></div>`;
}

export function mountBrowserTabs(
  bar: HTMLElement,
  onChange: (id: BrowserTabId) => void,
  options: { storage?: StorageLike } = {},
): { switchTo: (id: BrowserTabId) => void } {
  const storage = options.storage ?? getLocalStorage();

  function activate(id: BrowserTabId): void {
    bar.querySelectorAll<HTMLElement>(".browser-tab").forEach((btn) => {
      const match = btn.dataset.browserTab === id;
      btn.classList.toggle("is-active", match);
      btn.setAttribute("aria-selected", String(match));
    });
    storeBrowserTab(id, storage);
    onChange(id);
  }

  bar.addEventListener("click", (e) => {
    const btn = (e.target as HTMLElement).closest<HTMLElement>("[data-browser-tab]");
    if (btn) activate(btn.dataset.browserTab as BrowserTabId);
  });

  bar.addEventListener("keydown", (e) => {
    if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
    const btns = Array.from(bar.querySelectorAll<HTMLElement>(".browser-tab"));
    const idx = btns.findIndex((b) => b.classList.contains("is-active"));
    const next =
      e.key === "ArrowRight"
        ? (idx + 1) % btns.length
        : (idx - 1 + btns.length) % btns.length;
    e.preventDefault();
    btns[next].focus();
    activate(btns[next].dataset.browserTab as BrowserTabId);
  });

  // User menu: toggle dropdown + logout
  const menuTrigger = bar.querySelector<HTMLElement>("[data-user-menu-trigger]");
  const menuDropdown = bar.querySelector<HTMLElement>("[data-user-menu-dropdown]");
  const logoutBtn = bar.querySelector<HTMLElement>("[data-user-logout]");

  if (menuTrigger && menuDropdown) {
    menuTrigger.addEventListener("click", (e) => {
      e.stopPropagation();
      const open = !menuDropdown.hidden;
      menuDropdown.hidden = open;
    });
    document.addEventListener("click", () => {
      menuDropdown.hidden = true;
    });
    menuDropdown.addEventListener("click", (e) => e.stopPropagation());
  }

  if (logoutBtn) {
    logoutBtn.addEventListener("click", () => {
      // Clear chat session data before removing auth — prevents next user
      // from seeing the previous user's conversation on this browser.
      const chatStore = createChatSessionStore();
      chatStore.clearSessionSnapshots();
      chatStore.writeWindowScopedSessionId("");
      clearApiAccessToken();
      clearAuthContext();
      window.location.href = "/login";
    });
  }

  return { switchTo: activate };
}
