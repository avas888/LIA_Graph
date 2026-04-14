import type { I18nRuntime } from "@/shared/i18n";
import { renderChatShell } from "@/app/chat/shell";
import { icons } from "@/shared/ui/icons";

export type MobileShellMode = "default" | "public";

/**
 * Render the complete mobile shell.
 *
 * Strategy: embed the full desktop chat shell HTML inside #mobile-panel-chat
 * so that `mountChatApp` (which calls `collectChatDom`) finds all required
 * DOM nodes.  Mobile CSS hides desktop-only elements (.side-panel, .app-header,
 * .chat-splitter, etc.) while the mobile-specific panels, tab bar, drawer and
 * sheet are layered on top.
 *
 * `mode` controls which drawer/panel affordances are included:
 *   - "default" — full authenticated experience (user info, historial panel +
 *     drawer item, logout).
 *   - "public" — no-login `/public` surface. Skips all auth-only blocks:
 *     no user info, no historial panel, no historial drawer item, no logout.
 *     The three content tabs (chat / normativa / interpretación) and the
 *     "Nueva conversación" drawer action remain so public visitors get
 *     parity with user1@lia.dev minus the auth tools.
 */
export function renderMobileShell(
  i18n: I18nRuntime,
  mode: MobileShellMode = "default",
): string {
  const desktopChatHtml = renderChatShell(i18n);
  const isPublic = mode === "public";

  const historialPanel = isPublic
    ? ""
    : `
        <!-- Historial panel (full screen, hidden by default) -->
        <div id="mobile-panel-historial" class="mobile-panel">
          <div class="mobile-historial-header">
            <h2 class="mobile-historial-title">Historial</h2>
            <button class="mobile-historial-back" type="button" aria-label="Cerrar">${icons.close}</button>
          </div>
          <div class="mobile-historial-search">
            <input type="search" id="mobile-historial-search-input" placeholder="Buscar..." />
          </div>
          <div class="mobile-historial-pills-wrap"><div id="mobile-historial-pills" class="mobile-historial-pills"></div></div>
          <div id="mobile-historial-list" class="mobile-historial-list"></div>
          <div id="mobile-historial-footer" class="mobile-historial-load-more"></div>
        </div>`;

  const drawerUserInfo = isPublic
    ? ""
    : `
          <div class="mobile-drawer-user">
            <div class="mobile-drawer-user-icon">${icons.user}</div>
            <p id="mobile-drawer-user-name" class="mobile-drawer-user-name"></p>
            <p id="mobile-drawer-user-role" class="mobile-drawer-user-role"></p>
          </div>`;

  const drawerHistorialItem = isPublic
    ? ""
    : `
            <button class="mobile-drawer-item" type="button" data-drawer-action="historial">
              <span class="mobile-drawer-item-icon">${icons.clock}</span>
              Historial
            </button>`;

  const drawerFooter = isPublic
    ? ""
    : `
          <div class="mobile-drawer-divider"></div>
          <div class="mobile-drawer-footer">
            <button class="mobile-drawer-item mobile-drawer-item--danger" type="button" data-drawer-action="logout">
              <span class="mobile-drawer-item-icon">${icons.arrowRight}</span>
              Cerrar sesión
            </button>
          </div>`;

  return `
    <div class="mobile-shell${isPublic ? " mobile-shell--public" : ""}" data-lia-component="mobile-shell" data-mobile-mode="${mode}">

      <!-- ── Top Bar ──────────────────────────────────────── -->
      <header class="mobile-topbar">
        <div class="mobile-topbar-brand">
          <img src="/assets/lia-logo.png" alt="LIA" class="mobile-topbar-logo" />
        </div>
        <span class="mobile-topbar-tagline">${i18n.t("chat.hero.taglineMobile")}</span>
        <button class="mobile-hamburger-btn" type="button" aria-label="Menú">
          <span class="mobile-hamburger-icon">${icons.menu}</span>
        </button>
      </header>

      <!-- ── Viewport ─────────────────────────────────────── -->
      <div class="mobile-viewport">

        <!-- Chat panel (default, contains full desktop shell for chatApp) -->
        <div id="mobile-panel-chat" class="mobile-panel is-active">
          ${desktopChatHtml}
        </div>

        <!-- Normativa panel -->
        <div id="mobile-panel-normativa" class="mobile-panel">
          <div class="mobile-panel-header">
            <h2>Soporte Normativo</h2>
          </div>
          <div id="mobile-normativa-list" class="mobile-card-list"></div>
          <div id="mobile-normativa-empty" class="mobile-empty-state">
            <p class="mobile-empty-state-text">
              Las fuentes normativas aparecerán aquí cuando LIA responda tu consulta
            </p>
            <button class="mobile-empty-state-action" type="button" data-go-to-chat>
              ${icons.chat} Ir al chat
            </button>
          </div>
        </div>

        <!-- Interpretación panel -->
        <div id="mobile-panel-interpretacion" class="mobile-panel">
          <div class="mobile-panel-header">
            <h2>Interpretación de Expertos</h2>
          </div>
          <div id="mobile-interp-list" class="mobile-card-list"></div>
          <div id="mobile-interp-empty" class="mobile-empty-state">
            <p class="mobile-empty-state-text">
              Las interpretaciones de expertos aparecerán aquí cuando LIA responda tu consulta
            </p>
            <button class="mobile-empty-state-action" type="button" data-go-to-chat>
              ${icons.chat} Ir al chat
            </button>
          </div>
        </div>
${historialPanel}
      </div>

      <!-- ── Bottom Tab Bar ───────────────────────────────── -->
      <nav class="mobile-tab-bar" aria-label="Navegación principal">
        <button class="mobile-tab is-active" data-tab="chat" type="button">
          <span class="mobile-tab-icon">${icons.chatNew}</span>
          <span class="mobile-tab-label">Chat</span>
        </button>
        <button class="mobile-tab" data-tab="normativa" type="button">
          <span class="mobile-tab-icon">${icons.book}</span>
          <span class="mobile-tab-label">Normativa</span>
          <span class="mobile-tab-badge" hidden></span>
        </button>
        <button class="mobile-tab" data-tab="interpretacion" type="button">
          <span class="mobile-tab-icon">${icons.lightbulb}</span>
          <span class="mobile-tab-label">Interp.</span>
          <span class="mobile-tab-badge" hidden></span>
        </button>
      </nav>

      <!-- ── Drawer (hamburger) ───────────────────────────── -->
      <div class="mobile-drawer" hidden>
        <div class="mobile-drawer-scrim"></div>
        <div class="mobile-drawer-panel">
          <div class="mobile-drawer-header">
            <div class="mobile-drawer-brand">
              <img src="/assets/lia-logo.png" alt="LIA" class="mobile-drawer-logo" />
              <span class="mobile-drawer-brand-name">LIA</span>
            </div>
            <button class="mobile-drawer-close" type="button" aria-label="Cerrar">&times;</button>
          </div>${drawerUserInfo}
          <nav class="mobile-drawer-nav">
            <button class="mobile-drawer-item" type="button" data-drawer-action="new-conversation">
              <span class="mobile-drawer-item-icon">${icons.plus}</span>
              Nueva conversación
            </button>${drawerHistorialItem}
          </nav>${drawerFooter}
        </div>
      </div>

      <!-- ── Bottom Sheet ─────────────────────────────────── -->
      <div class="mobile-sheet-overlay" hidden>
        <div class="mobile-sheet-scrim"></div>
        <div class="mobile-sheet">
          <div class="mobile-sheet-handle"></div>
          <div class="mobile-sheet-header">
            <div>
              <h3 class="mobile-sheet-title"></h3>
              <p class="mobile-sheet-subtitle"></p>
            </div>
            <button class="mobile-sheet-close" type="button" aria-label="Cerrar">&times;</button>
          </div>
          <div class="mobile-sheet-content"></div>
        </div>
      </div>
    </div>
  `;
}
