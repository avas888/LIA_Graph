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
            <header class="form-guide-panel-header">
              <div>
                <p class="form-guide-panel-kicker">Guía visual</p>
                <h2>Guía gráfica del formulario</h2>
              </div>
              <p class="form-guide-panel-note">Haz clic en cualquier campo para abrir una ficha completa con el mismo nivel de detalle de la guía textual.</p>
            </header>
            <div id="interactive-pages" class="interactive-pages"></div>
          </section>

          <section id="form-guide-structured-view" class="form-guide-view form-guide-panel">
            <header class="form-guide-panel-header">
              <div>
                <p class="form-guide-panel-kicker">Guía textual</p>
                <h2>Guía texto del formulario</h2>
              </div>
              <p class="form-guide-panel-note">Resumen completo por secciones para revisar antes de diligenciar y presentar.</p>
            </header>
            <div id="structured-sections" class="structured-sections"></div>
          </section>

          <button id="mobile-show-graphic-btn" class="mobile-show-graphic-btn" type="button" hidden>Ver guía gráfica del formulario</button>
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
