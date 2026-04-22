import type { I18nRuntime } from "@/shared/i18n";

export function renderChatShell(i18n: I18nRuntime): string {
  return `
    <main class="app-shell chat-page-shell">
      <section class="chat-layout">
        <article class="chat-panel">
          <header class="chat-panel-header">
            <div>
              <h2>${i18n.t("chat.panel.title")}</h2>
            </div>
            <div class="chat-panel-actions">
              <button id="new-thread-btn" class="secondary-mini-btn new-thread-btn" type="button">
                <span class="button-plus" aria-hidden="true">+</span>
                <span>${i18n.t("chat.workspace.newThread")}</span>
              </button>
              <button id="reset-conversation-btn" class="secondary-mini-btn reset-chat-btn" type="button" hidden>
                <span class="button-minus" aria-hidden="true">−</span>
                <span>${i18n.t("chat.workspace.reset")}</span>
              </button>
            </div>
          </header>
          <div class="chat-log-shell">
            <div id="chat-log" class="chat-log" aria-live="polite">
              <section id="chat-log-empty" class="chat-log-empty" aria-label="${i18n.t("chat.empty.message")}">
                <p class="chat-log-empty-message">${i18n.t("chat.empty.message")}</p>
              </section>
            </div>
          </div>
          <form id="chat-form" class="chat-form">
            <div class="composer-topline">
              <label class="composer-label" for="message">${i18n.t("chat.composer.label")}</label>
            </div>
            <div class="composer-shell">
              <div class="composer-input-shell">
                <textarea id="message" name="message" rows="1" placeholder="${i18n.t("chat.composer.placeholder")}" required></textarea>
                <div class="composer-idle-cursor" aria-hidden="true" title="${i18n.t("chat.composer.cursor")}"></div>
              </div>
              <div class="composer-actions">
                <button id="send-btn" type="submit">${i18n.t("chat.composer.send")}</button>
              </div>
            </div>
          </form>
          <section id="chat-session-drawer" class="chat-session-drawer" aria-label="${i18n.t("chat.sessions.title")}" hidden>
            <button
              id="chat-session-drawer-toggle"
              class="chat-session-drawer-toggle"
              type="button"
              aria-expanded="false"
              aria-controls="chat-session-drawer-panel"
            >
              <span class="chat-session-drawer-title">${i18n.t("chat.sessions.title")}</span>
              <span id="chat-session-count" class="chat-session-count">0</span>
            </button>
            <div id="chat-session-drawer-panel" class="chat-session-drawer-panel" hidden>
              <div id="chat-session-switcher" class="chat-session-switcher"></div>
            </div>
          </section>
        </article>

        <div class="chat-splitter" role="separator" aria-orientation="vertical" tabindex="0" title="Arrastrar para redimensionar"></div>

        <aside class="side-panel" data-side-panel-expansion="idle">
          <section class="side-panel-section-normativa">
            <header class="side-panel-header">
              <div class="side-panel-heading">
                <div class="side-panel-title-row side-panel-title-row-compact">
                  <h2>${i18n.t("chat.support.title")}</h2>
                  <p id="citations-status" class="section-note side-panel-header-note">${i18n.t("chat.support.defer")}</p>
                </div>
              </div>
              <button
                type="button"
                class="side-panel-expand-btn"
                data-side-panel-target="normativa"
                aria-label="${i18n.t("chat.panel.expand.normativa")}"
                aria-pressed="false"
                title="${i18n.t("chat.panel.expand.normativa")}"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                  <path d="M14 4h6v6" />
                  <path d="M20 4l-7 7" />
                  <path d="M10 20H4v-6" />
                  <path d="M4 20l7-7" />
                </svg>
              </button>
            </header>
            <div class="side-panel-body">
              <ul id="citations" class="citation-list"></ul>
            </div>
            <button
              type="button"
              class="side-panel-restore-hint"
              data-side-panel-restore="normativa"
              aria-label="${i18n.t("chat.panel.restore")}"
              tabindex="-1"
              hidden
            >
              <span class="side-panel-restore-hint-chevron" aria-hidden="true"></span>
              <span class="side-panel-restore-hint-label">${i18n.t("chat.panel.restore")}</span>
            </button>
          </section>
          <section class="side-panel-experts side-panel-section-expertos">
            <header class="side-panel-header">
              <div>
                <div class="side-panel-title-row">
                  <h2>${i18n.t("chat.experts.title")}</h2>
                  <div id="expert-panel-title-tooltip-shell" class="section-tooltip">
                    <button
                      id="expert-panel-title-tooltip-trigger"
                      class="section-tooltip-trigger"
                      type="button"
                      aria-expanded="false"
                      aria-controls="expert-panel-title-tooltip"
                      aria-label="${i18n.t("chat.experts.tooltip.trigger")}"
                    >
                      i
                    </button>
                    <div id="expert-panel-title-tooltip" class="section-tooltip-popover" role="tooltip" hidden>
                      <p>${i18n.t("chat.experts.tooltip.body")}</p>
                    </div>
                  </div>
                </div>
              </div>
              <button
                type="button"
                class="side-panel-expand-btn"
                data-side-panel-target="expertos"
                aria-label="${i18n.t("chat.panel.expand.expertos")}"
                aria-pressed="false"
                title="${i18n.t("chat.panel.expand.expertos")}"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                  <path d="M14 4h6v6" />
                  <path d="M20 4l-7 7" />
                  <path d="M10 20H4v-6" />
                  <path d="M4 20l7-7" />
                </svg>
              </button>
            </header>
            <div class="side-panel-body">
              <p id="expert-panel-status" class="section-note">${i18n.t("chat.experts.defer")}</p>
              <div id="expert-panel-content"></div>
            </div>
            <button
              type="button"
              class="side-panel-restore-hint"
              data-side-panel-restore="expertos"
              aria-label="${i18n.t("chat.panel.restore")}"
              tabindex="-1"
              hidden
            >
              <span class="side-panel-restore-hint-chevron" aria-hidden="true"></span>
              <span class="side-panel-restore-hint-label">${i18n.t("chat.panel.restore")}</span>
            </button>
          </section>
        </aside>
      </section>
    </main>

    <template id="bubble-template">
      <div class="bubble">
        <p class="bubble-role"></p>
        <span class="bubble-timestamp"></span>
        <div class="bubble-normativa-indicator" hidden></div>
        <div class="bubble-text"></div>
        <div class="bubble-actions" hidden></div>
      </div>
    </template>

    <div id="modal-layer" class="modal-layer" hidden>
      <section id="modal-norma" class="lia-modal" aria-hidden="true" aria-label="${i18n.t("chat.modal.norma.title")}">
        <button class="modal-overlay" type="button" data-close-modal="modal-norma" aria-label="Cerrar"></button>
        <article class="modal-sheet" role="dialog" aria-modal="true">
          <header class="modal-header">
            <div>
              <h3 id="norma-title">${i18n.t("chat.modal.norma.title")}</h3>
              <p id="norma-binding-force" class="modal-eyebrow" hidden></p>
            </div>
            <div class="modal-header-actions">
              <div class="norma-original-group">
                <button id="norma-original-btn" class="primary-btn norma-header-action-btn" type="button">${i18n.t("chat.modal.norma.original")}</button>
              </div>
              <button class="modal-close" type="button" data-close-modal="modal-norma" aria-label="Cerrar">×</button>
            </div>
          </header>
          <div class="modal-scroll-body">
          <div id="norma-topbar" class="norma-topbar">
            <button id="norma-analysis-btn" class="secondary-btn" type="button" hidden>${i18n.t("chat.modal.norma.deepAnalysis")}</button>
            <p id="norma-original-helper" class="modal-helper" hidden></p>
            <p id="norma-analysis-helper" class="modal-helper" hidden></p>
          </div>
          <div id="norma-loading" class="modal-inline-loader" hidden>
            <div class="modal-inline-googly" aria-hidden="true">
              <span class="modal-inline-googly-core">
                <span class="lia-thinking-eye-pair">
                  <span class="lia-thinking-eye">
                    <span class="lia-thinking-eye-pupil"></span>
                  </span>
                  <span class="lia-thinking-eye">
                    <span class="lia-thinking-eye-pupil"></span>
                  </span>
                </span>
              </span>
            </div>
            <p id="norma-helper" class="modal-helper">${i18n.t("chat.modal.norma.loading")}</p>
          </div>
          <div class="norma-profile" aria-live="polite">
            <div id="norma-caution-banner" class="norma-caution-banner" hidden>
              <strong id="norma-caution-title"></strong>
              <p id="norma-caution-body"></p>
            </div>
            <div id="norma-primary" class="norma-sections" hidden></div>
            <p id="norma-lead" class="norma-lead"></p>
            <div id="norma-facts" class="norma-facts"></div>
            <div id="norma-sections" class="norma-sections"></div>
            <div id="norma-companion" class="norma-companion" hidden>
              <p id="norma-companion-helper" class="modal-helper" hidden></p>
              <a id="norma-companion-btn" class="norma-companion-link" href="#" target="_blank" rel="noopener noreferrer" hidden>
                <span class="norma-companion-link-label">${i18n.t("chat.modal.norma.guidePrompt")}</span>
                <span class="norma-companion-link-arrow" aria-hidden="true">→</span>
              </a>
            </div>
          </div>
          </div>
        </article>
      </section>

      <section id="modal-interpretations" class="lia-modal" aria-hidden="true" aria-label="${i18n.t("chat.modal.interpretations.title")}">
        <button class="modal-overlay" type="button" data-close-modal="modal-interpretations" aria-label="Cerrar"></button>
        <article class="modal-sheet" role="dialog" aria-modal="true">
          <header class="modal-header">
            <div>
              <p class="modal-eyebrow">${i18n.t("common.window2")}</p>
              <h3>${i18n.t("chat.modal.interpretations.title")}</h3>
            </div>
            <div class="modal-header-actions">
              <button class="modal-back" type="button" data-back-modal aria-label="Volver">Volver</button>
              <button class="modal-close" type="button" data-close-modal="modal-interpretations" aria-label="Cerrar">×</button>
            </div>
          </header>
          <p id="interpretation-status" class="modal-helper">${i18n.t("chat.modal.interpretations.loading")}</p>
          <div id="interpretation-results" class="interpretation-grid"></div>
        </article>
      </section>

      <section id="modal-summary" class="lia-modal" aria-hidden="true" aria-label="${i18n.t("chat.modal.summary.title")}">
        <button class="modal-overlay" type="button" data-close-modal="modal-summary" aria-label="Cerrar"></button>
        <article class="modal-sheet" role="dialog" aria-modal="true">
          <header class="modal-header">
            <div>
              <p class="modal-eyebrow">${i18n.t("common.window3")}</p>
              <h3>${i18n.t("chat.modal.summary.title")}</h3>
            </div>
            <div class="modal-header-actions">
              <button class="modal-back" type="button" data-back-modal aria-label="Volver">Volver</button>
              <button class="modal-close" type="button" data-close-modal="modal-summary" aria-label="Cerrar">×</button>
            </div>
          </header>
          <div class="summary-meta">
            <span id="summary-mode" class="meta-chip">-</span>
            <a id="summary-external-link" href="#" target="_blank" rel="noopener noreferrer" class="summary-link" hidden>${i18n.t("chat.modal.summary.link")}</a>
          </div>
          <pre id="summary-body" class="summary-body">${i18n.t("chat.modal.summary.select")}</pre>
          <div id="summary-grounding" class="summary-grounding"></div>
        </article>
      </section>

      <section id="modal-expert-detail" class="lia-modal" aria-hidden="true" aria-label="${i18n.t("chat.experts.modal.title")}">
        <button class="modal-overlay" type="button" data-close-modal="modal-expert-detail" aria-label="Cerrar"></button>
        <article class="modal-sheet expert-detail-modal" role="dialog" aria-modal="true">
          <header class="modal-header expert-detail-modal-header">
            <div>
              <p class="modal-eyebrow">${i18n.t("chat.experts.title")}</p>
              <h3 id="expert-detail-title" spellcheck="false">${i18n.t("chat.experts.modal.title")}</h3>
            </div>
            <button class="modal-close" type="button" data-close-modal="modal-expert-detail" aria-label="Cerrar">×</button>
          </header>
          <div id="expert-detail-content" class="expert-detail-content"></div>
        </article>
      </section>
    </div>
  `;
}
