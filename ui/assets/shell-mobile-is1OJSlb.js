import{a as n}from"./brandMark-dOoUqzyG.js";import{i as a}from"./icons-BZwBwwSI.js";import"./bootstrap-BApbUZ11.js";import"./index-DF3uq1vv.js";import"./authGate-Bb2S6efH.js";import"./client-OE0sHIIg.js";import"./format-CYFfBTRg.js";import"./badge-UV61UhzD.js";import"./chip-Bjq03GaS.js";import"./button-1yFzSXrY.js";import"./input-Byu2cnK9.js";import"./toasts-Dx3CUztl.js";import"./stateBlock-Dqw5sa9X.js";function C(i,t="default"){const l=n(i),e=t==="public",s=e?"":`
        <!-- Historial panel (full screen, hidden by default) -->
        <div id="mobile-panel-historial" class="mobile-panel">
          <div class="mobile-historial-header">
            <h2 class="mobile-historial-title">Historial</h2>
            <button class="mobile-historial-back" type="button" aria-label="Cerrar">${a.close}</button>
          </div>
          <div class="mobile-historial-search">
            <input type="search" id="mobile-historial-search-input" placeholder="Buscar..." />
          </div>
          <div class="mobile-historial-pills-wrap"><div id="mobile-historial-pills" class="mobile-historial-pills"></div></div>
          <div id="mobile-historial-list" class="mobile-historial-list"></div>
          <div id="mobile-historial-footer" class="mobile-historial-load-more"></div>
        </div>`,o=e?"":`
          <div class="mobile-drawer-user">
            <div class="mobile-drawer-user-icon">${a.user}</div>
            <p id="mobile-drawer-user-name" class="mobile-drawer-user-name"></p>
            <p id="mobile-drawer-user-role" class="mobile-drawer-user-role"></p>
          </div>`,r=e?"":`
            <button class="mobile-drawer-item" type="button" data-drawer-action="historial">
              <span class="mobile-drawer-item-icon">${a.clock}</span>
              Historial
            </button>`,b=e?"":`
          <div class="mobile-drawer-divider"></div>
          <div class="mobile-drawer-footer">
            <button class="mobile-drawer-item mobile-drawer-item--danger" type="button" data-drawer-action="logout">
              <span class="mobile-drawer-item-icon">${a.arrowRight}</span>
              Cerrar sesión
            </button>
          </div>`;return`
    <div class="mobile-shell${e?" mobile-shell--public":""}" data-lia-component="mobile-shell" data-mobile-mode="${t}">

      <!-- ── Top Bar ──────────────────────────────────────── -->
      <header class="mobile-topbar">
        <div class="mobile-topbar-brand">
          <img src="/assets/lia-logo.png" alt="LIA" class="mobile-topbar-logo" />
        </div>
        <span class="mobile-topbar-tagline">${i.t("chat.hero.taglineMobile")}</span>
        <button class="mobile-hamburger-btn" type="button" aria-label="Menú">
          <span class="mobile-hamburger-icon">${a.menu}</span>
        </button>
      </header>

      <!-- ── Viewport ─────────────────────────────────────── -->
      <div class="mobile-viewport">

        <!-- Chat panel (default, contains full desktop shell for chatApp) -->
        <div id="mobile-panel-chat" class="mobile-panel is-active">
          ${l}
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
              ${a.chat} Ir al chat
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
              ${a.chat} Ir al chat
            </button>
          </div>
        </div>
${s}
      </div>

      <!-- ── Bottom Tab Bar ───────────────────────────────── -->
      <nav class="mobile-tab-bar" aria-label="Navegación principal">
        <button class="mobile-tab is-active" data-tab="chat" type="button">
          <span class="mobile-tab-icon">${a.chatNew}</span>
          <span class="mobile-tab-label">Chat</span>
        </button>
        <button class="mobile-tab" data-tab="normativa" type="button">
          <span class="mobile-tab-icon">${a.book}</span>
          <span class="mobile-tab-label">Normativa</span>
          <span class="mobile-tab-badge" hidden></span>
        </button>
        <button class="mobile-tab" data-tab="interpretacion" type="button">
          <span class="mobile-tab-icon">${a.lightbulb}</span>
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
          </div>${o}
          <nav class="mobile-drawer-nav">
            <button class="mobile-drawer-item" type="button" data-drawer-action="new-conversation">
              <span class="mobile-drawer-item-icon">${a.plus}</span>
              Nueva conversación
            </button>${r}
          </nav>${b}
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
  `}export{C as renderMobileShell};
