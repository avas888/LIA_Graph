import type { I18nRuntime } from "@/shared/i18n";

export function renderFormGuideShell(i18n: I18nRuntime): string {
  return `
    <main class="form-guide-shell">
      <header class="form-guide-header">
        <div class="form-guide-header-info">
          <p id="form-guide-profile" class="form-guide-eyebrow"></p>
          <h1 id="form-guide-title">Cargando guía...</h1>
          <p id="form-guide-version" class="form-guide-meta"></p>
          <p id="form-guide-verified" class="form-guide-meta"></p>
        </div>
        <div class="form-guide-header-actions">
          <button id="form-guide-sources-btn" class="secondary-btn" type="button">Ver fuentes</button>
          <button id="form-guide-pdf-btn" class="primary-btn" type="button">Descargar PDF oficial</button>
          <a href="/" class="nav-link form-guide-back-link">Volver al chat</a>
        </div>
        <div class="form-guide-mobile-controls">
          <button class="form-guide-hamburger" type="button" aria-label="Menú">
            <span></span><span></span><span></span>
          </button>
          <a href="/" class="form-guide-close-btn" aria-label="Cerrar">×</a>
          <div class="form-guide-mobile-menu" hidden>
            <button id="form-guide-sources-btn-mobile" class="form-guide-mobile-menu-item" type="button">Ver fuentes</button>
            <button id="form-guide-pdf-btn-mobile" class="form-guide-mobile-menu-item" type="button">Descargar PDF oficial</button>
          </div>
        </div>
      </header>

      <div id="form-guide-loading" class="form-guide-loading">
        <p>Cargando guía del formulario...</p>
      </div>

      <div id="form-guide-error" class="form-guide-error" hidden>
        <p id="form-guide-error-message">Esta guía aún no está disponible.</p>
        <a href="/" class="primary-btn">Volver al chat principal</a>
      </div>

      <div id="form-guide-content" class="form-guide-layout" hidden>
        <section class="form-guide-main">
          <div class="form-guide-view-toggle" role="tablist" aria-label="Cambiar vista de la guía">
            <button id="view-interactive-btn" class="view-toggle-btn view-toggle-active" type="button" role="tab" aria-selected="true">Guía gráfica</button>
            <button id="view-structured-btn" class="view-toggle-btn" type="button" role="tab" aria-selected="false">Guía texto</button>
          </div>

          <section id="form-guide-interactive-view" class="form-guide-view form-guide-panel">
            <header class="form-guide-panel-header form-guide-panel-header--with-demo">
              <div class="form-guide-panel-header-intro">
                <p class="form-guide-panel-kicker">Guía visual</p>
                <h2>Guía gráfica del formulario</h2>
                <p class="form-guide-panel-note">Toca cualquier <strong>número</strong> sobre el formulario para abrir una <strong>ficha completa</strong> del campo, con el mismo detalle de la guía textual.</p>
              </div>
              <div class="form-guide-panel-demo" aria-hidden="true">
                <svg class="form-guide-panel-illustration" viewBox="0 0 200 120" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Ilustración: un dedo toca un número pequeño sobre el formulario para abrir la ficha del campo">
                  <defs>
                    <radialGradient id="fg-panel-illu-glow-graphic" cx="50%" cy="50%" r="50%">
                      <stop offset="0%" stop-color="rgba(20, 115, 83, 0.3)"/>
                      <stop offset="100%" stop-color="rgba(20, 115, 83, 0)"/>
                    </radialGradient>
                  </defs>
                  <circle cx="26" cy="52" r="26" fill="url(#fg-panel-illu-glow-graphic)"/>
                  <rect x="14" y="10" width="124" height="96" rx="9" fill="#ffffff" stroke="rgba(22,49,41,0.14)" stroke-width="1"/>
                  <path d="M23 10 H129 Q138 10 138 19 V30 H14 V19 Q14 10 23 10 Z" fill="#163129"/>
                  <rect x="22" y="15.5" width="56" height="2.8" rx="1.4" fill="rgba(255,255,255,0.92)"/>
                  <rect x="22" y="21.5" width="36" height="2.2" rx="1.1" fill="rgba(255,255,255,0.55)"/>
                  <circle cx="26" cy="40" r="3.1" fill="#ffffff" stroke="rgba(20,115,83,0.55)" stroke-width="0.85"/>
                  <text x="26" y="41.6" text-anchor="middle" fill="rgba(20,115,83,0.9)" font-family="ui-sans-serif, system-ui" font-size="3.6" font-weight="700">1</text>
                  <rect x="34" y="38.6" width="82" height="2.9" rx="1.45" fill="rgba(22,49,41,0.26)"/>
                  <circle cx="26" cy="52" r="4.1" fill="rgba(20,115,83,0.18)" stroke="rgba(20,115,83,0.95)" stroke-width="1.15"/>
                  <text x="26" y="53.7" text-anchor="middle" fill="rgba(20,115,83,1)" font-family="ui-sans-serif, system-ui" font-size="4.2" font-weight="700">2</text>
                  <rect x="34" y="50.55" width="94" height="2.9" rx="1.45" fill="rgba(22,49,41,0.42)"/>
                  <circle cx="26" cy="64" r="3.1" fill="#ffffff" stroke="rgba(20,115,83,0.55)" stroke-width="0.85"/>
                  <text x="26" y="65.6" text-anchor="middle" fill="rgba(20,115,83,0.9)" font-family="ui-sans-serif, system-ui" font-size="3.6" font-weight="700">3</text>
                  <rect x="34" y="62.6" width="70" height="2.9" rx="1.45" fill="rgba(22,49,41,0.26)"/>
                  <circle cx="26" cy="76" r="3.1" fill="#ffffff" stroke="rgba(20,115,83,0.42)" stroke-width="0.85"/>
                  <text x="26" y="77.6" text-anchor="middle" fill="rgba(20,115,83,0.72)" font-family="ui-sans-serif, system-ui" font-size="3.6" font-weight="700">4</text>
                  <rect x="34" y="74.6" width="76" height="2.9" rx="1.45" fill="rgba(22,49,41,0.2)"/>
                  <circle cx="26" cy="88" r="3.1" fill="#ffffff" stroke="rgba(20,115,83,0.3)" stroke-width="0.85"/>
                  <text x="26" y="89.6" text-anchor="middle" fill="rgba(20,115,83,0.55)" font-family="ui-sans-serif, system-ui" font-size="3.6" font-weight="700">5</text>
                  <rect x="34" y="86.6" width="60" height="2.9" rx="1.45" fill="rgba(22,49,41,0.14)"/>
                  <g class="form-guide-panel-illu-ripple">
                    <circle cx="26" cy="52" r="9" fill="none" stroke="rgba(20,115,83,0.5)" stroke-width="1.2"/>
                    <circle cx="26" cy="52" r="5.5" fill="none" stroke="rgba(20,115,83,0.72)" stroke-width="1.2"/>
                  </g>
                  <g transform="translate(7.6 47.2) scale(1.6)">
                    <g class="form-guide-panel-illu-hand">
                      <path fill="#163129" stroke="#ffffff" stroke-width="0.6" stroke-linejoin="round" d="M9 11.24V7.5C9 6.12 10.12 5 11.5 5S14 6.12 14 7.5v3.74c1.21-.81 2-2.18 2-3.74C16 5.01 13.99 3 11.5 3S7 5.01 7 7.5c0 1.56.79 2.93 2 3.74zm9.84 4.63l-4.54-2.26c-.17-.07-.35-.11-.54-.11H13v-6c0-.83-.67-1.5-1.5-1.5S10 6.67 10 7.5v10.74l-3.43-.72c-.08-.01-.15-.03-.24-.03-.31 0-.59.13-.79.33l-.79.8 4.94 4.94c.27.27.65.44 1.06.44h6.79c.75 0 1.33-.55 1.44-1.28l.75-5.27c.01-.07.02-.14.02-.2 0-.62-.38-1.16-.91-1.38z"/>
                    </g>
                  </g>
                </svg>
              </div>
            </header>
            <div id="interactive-pages" class="interactive-pages"></div>
          </section>

          <section id="form-guide-structured-view" class="form-guide-view form-guide-panel">
            <header class="form-guide-panel-header form-guide-panel-header--with-demo">
              <div class="form-guide-panel-header-intro">
                <p class="form-guide-panel-kicker">Guía textual</p>
                <h2>Guía texto del formulario</h2>
                <p class="form-guide-panel-note">Toca cualquier fila con <strong>Cas. N</strong> para abrir una <strong>ficha completa</strong> del campo. Resumen completo por secciones para revisar antes de diligenciar y presentar.</p>
              </div>
              <div class="form-guide-panel-demo" aria-hidden="true">
                <svg class="form-guide-panel-illustration" viewBox="0 0 200 120" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Ilustración: un dedo toca una fila de la lista para abrir la ficha del campo">
                  <defs>
                    <radialGradient id="fg-panel-illu-glow" cx="50%" cy="50%" r="50%">
                      <stop offset="0%" stop-color="rgba(20, 115, 83, 0.32)"/>
                      <stop offset="100%" stop-color="rgba(20, 115, 83, 0)"/>
                    </radialGradient>
                  </defs>
                  <circle cx="108" cy="60" r="30" fill="url(#fg-panel-illu-glow)"/>
                  <rect x="14" y="10" width="124" height="86" rx="9" fill="#ffffff" stroke="rgba(22,49,41,0.14)" stroke-width="1"/>
                  <rect x="26" y="20" width="46" height="3.5" rx="1.75" fill="rgba(22,49,41,0.38)"/>
                  <rect x="26" y="27" width="28" height="3" rx="1.5" fill="rgba(22,49,41,0.18)"/>
                  <rect x="26" y="40" width="12" height="8" rx="2" fill="rgba(20,115,83,0.18)" stroke="rgba(20,115,83,0.4)" stroke-width="0.7"/>
                  <rect x="42" y="42" width="64" height="3.5" rx="1.75" fill="rgba(22,49,41,0.2)"/>
                  <rect x="22" y="54" width="108" height="18" rx="5" fill="rgba(20,115,83,0.14)" stroke="rgba(20,115,83,0.55)" stroke-width="1.2"/>
                  <rect x="28" y="60" width="14" height="8" rx="2.2" fill="rgba(20,115,83,0.92)"/>
                  <text x="35" y="66" text-anchor="middle" fill="#ffffff" font-family="ui-sans-serif, system-ui" font-size="5.6" font-weight="700">2</text>
                  <rect x="46" y="59.2" width="58" height="3.5" rx="1.75" fill="rgba(20,115,83,0.55)"/>
                  <rect x="46" y="64.8" width="38" height="3" rx="1.5" fill="rgba(20,115,83,0.35)"/>
                  <rect x="26" y="80" width="12" height="8" rx="2" fill="rgba(20,115,83,0.18)" stroke="rgba(20,115,83,0.4)" stroke-width="0.7"/>
                  <rect x="42" y="82" width="50" height="3.5" rx="1.75" fill="rgba(22,49,41,0.2)"/>
                  <g class="form-guide-panel-illu-ripple">
                    <circle cx="108" cy="62.5" r="10" fill="none" stroke="rgba(20,115,83,0.5)" stroke-width="1.3"/>
                    <circle cx="108" cy="62.5" r="5.5" fill="none" stroke="rgba(20,115,83,0.72)" stroke-width="1.3"/>
                  </g>
                  <g transform="translate(87 56.5) scale(1.8)">
                    <g class="form-guide-panel-illu-hand">
                      <path fill="#163129" stroke="#ffffff" stroke-width="0.6" stroke-linejoin="round" d="M9 11.24V7.5C9 6.12 10.12 5 11.5 5S14 6.12 14 7.5v3.74c1.21-.81 2-2.18 2-3.74C16 5.01 13.99 3 11.5 3S7 5.01 7 7.5c0 1.56.79 2.93 2 3.74zm9.84 4.63l-4.54-2.26c-.17-.07-.35-.11-.54-.11H13v-6c0-.83-.67-1.5-1.5-1.5S10 6.67 10 7.5v10.74l-3.43-.72c-.08-.01-.15-.03-.24-.03-.31 0-.59.13-.79.33l-.79.8 4.94 4.94c.27.27.65.44 1.06.44h6.79c.75 0 1.33-.55 1.44-1.28l.75-5.27c.01-.07.02-.14.02-.2 0-.62-.38-1.16-.91-1.38z"/>
                    </g>
                  </g>
                </svg>
              </div>
            </header>
            <div id="structured-sections" class="structured-sections"></div>
          </section>
        </section>

        <aside class="form-guide-chat">
          <header class="form-guide-chat-header">
            <h2>Chatea sobre este formulario</h2>
            <p id="form-guide-chat-context" class="form-guide-chat-context"></p>
          </header>
          <div id="form-guide-chat-log" class="form-guide-chat-log"></div>
          <form id="form-guide-chat-form" class="form-guide-chat-form">
            <textarea id="form-guide-chat-input" rows="2" placeholder="Pregunta sobre este formulario..." required></textarea>
            <button type="submit" class="primary-btn">Enviar</button>
          </form>
          <p id="form-guide-disclaimer" class="form-guide-disclaimer" hidden></p>
        </aside>
      </div>

      <div id="form-guide-profile-selector" class="form-guide-profile-selector" hidden>
        <h2>Selecciona un perfil tributario</h2>
        <p>Esta guía varía según el perfil del contribuyente. Selecciona el que aplica:</p>
        <div id="profile-options" class="profile-options"></div>
      </div>

      <dialog id="form-guide-sources-dialog" class="form-guide-sources-dialog">
        <header>
          <h3>Fuentes de la guía</h3>
          <button id="close-sources-dialog" type="button" class="modal-close">&times;</button>
        </header>
        <div id="sources-list" class="sources-list"></div>
      </dialog>

      <dialog id="form-guide-field-dialog" class="form-guide-field-dialog">
        <div class="form-guide-field-dialog-shell">
          <header class="form-guide-field-dialog-header">
            <div class="form-guide-field-dialog-heading">
              <p id="field-dialog-eyebrow" class="form-guide-eyebrow"></p>
              <h3 id="field-dialog-title">Campo seleccionado</h3>
              <div id="field-dialog-meta" class="field-dialog-meta"></div>
            </div>
            <button id="close-field-dialog" type="button" class="modal-close" aria-label="Cerrar detalle del campo">&times;</button>
          </header>

          <p id="field-dialog-summary" class="field-dialog-summary" hidden></p>
          <div id="field-dialog-body" class="field-dialog-grid"></div>

        </div>
      </dialog>
    </main>
  `;
}
