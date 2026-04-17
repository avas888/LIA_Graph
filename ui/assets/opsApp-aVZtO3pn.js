import{q as Y}from"./bootstrap-CDL0BdR1.js";import{g as Ze,p as Ye,A as pt}from"./client-OE0sHIIg.js";import{p as At}from"./colors-ps0hVFT8.js";import{g as ut}from"./index-DE07Z79R.js";import{getToastController as ys}from"./toasts-tYrWECOz.js";function Ut(e){return`
    <dialog id="add-corpus-dialog" class="ops-dialog">
      <form id="add-corpus-form" method="dialog" class="ops-dialog-form">
        <h3>Nueva categoría de corpus</h3>

        <label class="ops-field">
          <span>Nombre *</span>
          <input id="add-corpus-label" type="text" required minlength="3" maxlength="80"
                 placeholder="Ej: Procedimiento Tributario" autocomplete="off" />
        </label>

        <label class="ops-field">
          <span>Clave (auto-generada)</span>
          <input id="add-corpus-key" type="text" readonly tabindex="-1"
                 style="opacity:0.65;cursor:default" />
          <small>Identificador interno y slug de ruta en knowledge_base/</small>
        </label>

        <label class="ops-field">
          <span>Palabras clave fuertes (opcional)</span>
          <input id="add-corpus-kw-strong" type="text"
                 placeholder="procedimiento tributario, recurso de reconsideracion" autocomplete="off" />
          <small>Separadas por coma. Ayudan a detectar el tema en chat.</small>
        </label>

        <label class="ops-field">
          <span>Palabras clave débiles (opcional)</span>
          <input id="add-corpus-kw-weak" type="text"
                 placeholder="sancion, emplazamiento" autocomplete="off" />
          <small>Menor peso en la detección automática.</small>
        </label>

        <p id="add-corpus-error" class="ops-flash ops-flash-error" hidden></p>

        <div class="ops-dialog-actions">
          <button type="button" id="add-corpus-cancel" class="secondary-btn">Cancelar</button>
          <button type="submit" id="add-corpus-submit" class="primary-btn">Crear categoría</button>
        </div>
      </form>
    </dialog>
  `}function _s(e){return`
    <main class="ops-shell">
      <header class="app-header app-hero">
        <div class="hero-copy">
          <p class="eyebrow">${e.t("ops.hero.eyebrow")}</p>
          <h1>${e.t("ops.hero.title")}</h1>
          <p class="hero-lede">${e.t("ops.backstage.lede")}</p>
        </div>
        <div class="hero-meta">
          <div class="hero-callout">
            <p class="hero-callout-label">${e.t("ops.hero.callout.label")}</p>
            <p class="hero-callout-value">${e.t("ops.backstage.callout")}</p>
          </div>
        </div>
      </header>

      <section class="ops-backstage">
        <article class="ops-card ops-window">
          <div class="ops-window-head ops-card-head">
            <h2>${e.t("ops.runs.title")}</h2>
            <button id="refresh-runs" type="button" class="secondary-btn">${e.t("ops.runs.refresh")}</button>
          </div>
          <div class="ops-window-body ops-window-body-table">
            <div class="ops-table-wrap">
              <table class="ops-table">
                <thead>
                  <tr>
                    <th>${e.t("ops.runs.run")}</th>
                    <th>${e.t("ops.runs.trace")}</th>
                    <th>${e.t("ops.runs.status")}</th>
                    <th>${e.t("ops.runs.started")}</th>
                  </tr>
                </thead>
                <tbody id="runs-body"></tbody>
              </table>
            </div>
          </div>
        </article>

        <article class="ops-card ops-window">
          <div class="ops-window-head">
            <h2>${e.t("ops.timeline.title")}</h2>
            <p id="timeline-meta">${e.t("ops.timeline.select")}</p>
          </div>
          <div class="ops-window-body">
            <p id="cascade-note" class="ops-subcopy">${e.t("ops.timeline.waterfallNote")}</p>

            <section class="ops-cascade-group" aria-labelledby="user-cascade-title">
              <div class="ops-cascade-group-head">
                <div>
                  <p class="ops-cascade-kicker">${e.t("ops.timeline.userKicker")}</p>
                  <h3 id="user-cascade-title">${e.t("ops.timeline.userTitle")}</h3>
                </div>
                <p id="user-cascade-summary" class="ops-cascade-total">-</p>
              </div>
              <ol id="user-cascade" class="ops-cascade-list"></ol>
            </section>

            <section class="ops-cascade-group" aria-labelledby="technical-cascade-title">
              <div class="ops-cascade-group-head">
                <div>
                  <p class="ops-cascade-kicker">${e.t("ops.timeline.technicalKicker")}</p>
                  <h3 id="technical-cascade-title">${e.t("ops.timeline.technicalTitle")}</h3>
                </div>
                <p id="technical-cascade-summary" class="ops-cascade-total">-</p>
              </div>
              <ol id="technical-cascade" class="ops-cascade-list"></ol>
            </section>

            <details class="ops-timeline-raw">
              <summary>${e.t("ops.timeline.rawTitle")}</summary>
              <ul id="timeline" class="timeline"></ul>
            </details>
          </div>
        </article>

        <article class="ops-card ops-window">
          <div class="ops-window-head">
            <h2>${e.t("chat.workspace.title")}</h2>
          </div>
          <div class="ops-window-body">
            <p class="ops-copy">${e.t("chat.workspace.note")}</p>
            <div class="workspace-summary">
              <div class="workspace-summary-card">
                <p class="workspace-summary-label">${e.t("chat.debug.label")}</p>
                <p id="debug-summary" class="workspace-summary-value">${e.t("chat.debug.inactive")}</p>
              </div>
            </div>
            <div class="backstage-controls">
              <label class="inline-toggle">
                <input id="debug" type="checkbox" />
                ${e.t("chat.debug.label")}
              </label>
            </div>
          </div>
        </article>

        <article class="ops-card ops-window">
          <div class="ops-window-head">
            <h2>${e.t("chat.metrics.title")}</h2>
          </div>
          <div class="ops-window-body">
            <div class="runtime-grid">
              <div class="runtime-card">
                <p class="runtime-label">${e.t("chat.metrics.timer")}</p>
                <p id="runtime-request-timer" class="runtime-value">0.00 s</p>
              </div>
              <div class="runtime-card">
                <p class="runtime-label">${e.t("chat.metrics.latency")}</p>
                <p id="runtime-latency" class="runtime-value">-</p>
              </div>
              <div class="runtime-card">
                <p class="runtime-label">${e.t("chat.metrics.model")}</p>
                <p id="runtime-model" class="runtime-value">-</p>
              </div>
              <div class="runtime-card">
                <p class="runtime-label">${e.t("chat.metrics.turnTokens")}</p>
                <p id="runtime-turn-tokens" class="runtime-value">-</p>
              </div>
              <div class="runtime-card">
                <p class="runtime-label">${e.t("chat.metrics.conversationTokens")}</p>
                <p id="runtime-conversation-tokens" class="runtime-value">-</p>
              </div>
            </div>
          </div>
        </article>

        <article class="ops-card ops-window">
          <div class="ops-window-head">
            <h2>${e.t("chat.audit.title")}</h2>
          </div>
          <div class="ops-window-body">
            <pre id="diagnostics" class="diagnostics">${e.t("chat.debug.off")}</pre>
          </div>
        </article>
      </section>
    </main>
  `}function $s(e){return`
    <div class="ingestion-panel-shell">
      <nav class="ingestion-subtabs" role="tablist" aria-label="${e.t("tabs.ingestion")}">
        <button
          class="ingestion-subtab is-active"
          type="button"
          role="tab"
          data-ingestion-section="sesiones"
          aria-selected="true"
        >Sesiones</button>
        <button
          class="ingestion-subtab"
          type="button"
          role="tab"
          data-ingestion-section="promocion"
          aria-selected="false"
        >Promoción</button>
      </nav>

      <div id="ingestion-section-sesiones" class="ingestion-section" role="tabpanel">
    <main class="ops-shell">
      <header class="app-header app-hero">
        <div class="hero-copy">
          <h1>${e.t("ops.ingestion.title")}</h1>
        </div>
      </header>

      <section class="ops-backstage">
        <details class="ops-card ops-window ops-window--collapsible" open>
          <summary class="ops-window-head ops-card-head">
            <h2>${e.t("ops.ingestion.title")}</h2>
            <button id="ingestion-refresh" type="button" class="secondary-btn">${e.t("ops.ingestion.actions.refresh")}</button>
          </summary>
          <div class="ops-window-body">
            <p class="ops-copy">${e.t("ops.ingestion.lede")}</p>

            <div class="ops-control-grid">
              <label class="ops-field">
                <span>Tema del Corpus</span>
                <div style="display:flex;gap:0.4rem;align-items:center">
                  <select id="ingestion-corpus" aria-label="Tema del Corpus" style="flex:1"></select>
                  <button id="ingestion-add-corpus-btn" type="button" class="secondary-btn" style="padding:0.35rem 0.65rem;font-size:1.1rem;line-height:1" title="Agregar categoría">+</button>
                </div>
              </label>

              <label class="ops-field">
                <span>${e.t("ops.ingestion.batchType")}</span>
                <select id="ingestion-batch-type" aria-label="${e.t("ops.ingestion.batchType")}">
                  <option value="autogenerar">Autogenerar</option>
                  <option value="normative_base">${e.t("ops.ingestion.batchType.normative")}</option>
                  <option value="interpretative_guidance">${e.t("ops.ingestion.batchType.interpretative")}</option>
                  <option value="practica_erp">${e.t("ops.ingestion.batchType.practical")}</option>
                </select>
              </label>
            </div>

            <section
              id="ingestion-dropzone"
              class="ops-dropzone"
              tabindex="0"
              role="button"
              aria-controls="ingestion-file-input"
            >
              <strong>${e.t("ops.ingestion.dropzone")}</strong>
              <p>${e.t("ops.ingestion.dropzoneHelp")}</p>
              <input
                id="ingestion-file-input"
                type="file"
                multiple
                accept=".md,.txt,.json,.pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,text/markdown,application/json"
              />
              <input
                id="ingestion-folder-input"
                type="file"
                webkitdirectory
              />
            </section>

            <div id="ingestion-upload-progress" class="ops-upload-progress" hidden></div>

            <p id="ingestion-pending-files" class="ops-inline-note">${e.t("ops.ingestion.pendingNone")}</p>

            <div class="ops-action-groups">
              <fieldset class="ops-action-group">
                <legend>${e.t("ops.ingestion.groupAuto")}</legend>
                <div class="ops-action-row">
                  <button id="ingestion-select-folder" type="button" class="secondary-btn">${e.t("ops.ingestion.selectFolder")}</button>
                  <button id="ingestion-auto-process" type="button" class="primary-btn">▶ ${e.t("ops.ingestion.actions.autoProcess")}</button>
                </div>
                <p id="ingestion-auto-status" class="ops-auto-status" hidden></p>
              </fieldset>

              <fieldset class="ops-action-group">
                <legend>${e.t("ops.ingestion.groupManual")}</legend>
                <div class="ops-action-row">
                  <button id="ingestion-create-session" type="button" class="secondary-btn success-btn">${e.t("ops.ingestion.newSession")}</button>
                  <button id="ingestion-select-files" type="button" class="secondary-btn">${e.t("ops.ingestion.selectFiles")}</button>
                  <button id="ingestion-upload-files" type="button" class="primary-btn">${e.t("ops.ingestion.upload")}</button>
                  <button id="ingestion-process-session" type="button" class="primary-btn">${e.t("ops.ingestion.actions.process")}</button>
                  <button id="ingestion-validate-batch" type="button" class="primary-btn">${e.t("ops.ingestion.actions.validateBatch")}</button>
                  <button id="ingestion-retry-session" type="button" class="secondary-btn">${e.t("ops.ingestion.actions.retry")}</button>
                  <button id="ingestion-delete-session" type="button" class="secondary-btn danger-btn">${e.t("ops.ingestion.actions.discardSession")}</button>
                </div>
              </fieldset>
            </div>

            <p id="ingestion-overview" class="ops-inline-note"></p>
            <div id="ingestion-flash" class="ops-flash" hidden></div>
          </div>
        </details>

        <details id="ingestion-bounce-log" class="ops-card ops-accordion" hidden>
          <summary class="ops-accordion-head">
            <h2>${e.t("ops.ingestion.bounceLog.title")}</h2>
            <button id="ingestion-bounce-copy" type="button" class="ops-log-copy-btn" title="${e.t("ops.ingestion.log.copy")}">${e.t("ops.ingestion.log.copy")}</button>
          </summary>
          <div class="ops-accordion-body">
            <pre id="ingestion-bounce-body" class="ops-log-body"></pre>
          </div>
        </details>

        <article class="ops-card ops-window">
          <div class="ops-window-head">
            <h2>${e.t("ops.ingestion.selectedTitle")}</h2>
            <p id="selected-session-meta" class="ops-subcopy">${e.t("ops.ingestion.selectedEmpty")}</p>
          </div>
          <div class="ops-window-body ops-window-body-selected">
            <div id="ingestion-last-error" class="ops-guidance" hidden>
              <strong>${e.t("ops.ingestion.lastErrorTitle")}</strong>
              <p id="ingestion-last-error-message"></p>
              <p id="ingestion-last-error-guidance"></p>
              <p id="ingestion-last-error-next"></p>
            </div>

            <div id="ingestion-kanban" class="kanban-board"></div>

            <div id="ingestion-log-accordion" class="ops-log-accordion" hidden>
              <div class="ops-log-accordion-summary" id="ingestion-log-toggle" role="button" tabindex="0" aria-expanded="false">
                <span class="ops-log-accordion-marker">&#9656;</span>
                <span>${e.t("ops.ingestion.log.title")}</span>
                <button id="ingestion-log-copy" type="button" class="ops-log-copy-btn" title="${e.t("ops.ingestion.log.copy")}">${e.t("ops.ingestion.log.copy")}</button>
              </div>
              <pre id="ingestion-log-body" class="ops-log-body" hidden></pre>
            </div>
          </div>
        </article>

        <details class="ops-card ops-accordion">
          <summary class="ops-accordion-head">
            <h2>${e.t("ops.ingestion.sessionsTitle")}</h2>
            <p id="ingestion-session-meta" class="ops-subcopy"></p>
          </summary>
          <div class="ops-accordion-body">
            <ul id="ingestion-sessions-list" class="ops-session-list"></ul>
          </div>
        </details>
      </section>
      ${Ut()}
    </main>
      </div>

      <div id="ingestion-section-promocion" class="ingestion-section" role="tabpanel" hidden></div>
    </div>
  `}function ks(){return`
    <div class="operations-panel-shell">
      <nav class="operations-subtabs" aria-label="Promoción">
        <button class="operations-subtab is-active" type="button" data-ops-section="corpus">Corpus</button>
        <button class="operations-subtab" type="button" data-ops-section="embeddings">Embeddings</button>
        <button class="operations-subtab" type="button" data-ops-section="reindex">Re-index</button>
      </nav>
      <div id="ops-section-corpus" class="operations-section">
        <header class="operations-panel-header">
          <h1 style="font-size:1.25rem;font-weight:700;margin:0">Ciclo de Vida del Corpus</h1>
          <p style="color:var(--text-secondary);font-size:0.875rem;margin:0.25rem 0 0">WIP (Docker) &rarr; Production (Cloud)</p>
        </header>
        <div id="operations-corpus-lifecycle"></div>
      </div>
      <div id="ops-section-embeddings" class="operations-section" hidden>
        <div id="operations-embeddings-lifecycle"></div>
      </div>
      <div id="ops-section-reindex" class="operations-section" hidden>
        <div id="operations-reindex-lifecycle"></div>
      </div>
      <div id="operations-flash" class="ops-flash" hidden></div>
    </div>
  `}function ws(e){return`
    <main class="ops-shell">
      <header class="app-header app-hero">
        <div class="hero-copy">
          <p class="eyebrow">${e.t("ops.hero.eyebrow")}</p>
          <h1>${e.t("ops.hero.title")}</h1>
          <p class="hero-lede">${e.t("ops.hero.lede")}</p>
        </div>
        <div class="hero-meta">
          <nav class="top-nav">
            <a href="/" class="nav-link">${e.t("common.backToChat")}</a>
          </nav>
          <div class="hero-callout">
            <p class="hero-callout-label">${e.t("ops.hero.callout.label")}</p>
            <p class="hero-callout-value">${e.t("ops.hero.callout.value")}</p>
          </div>
        </div>
      </header>

      <section class="ops-backstage">
        <nav class="ops-subtabs" aria-label="${e.t("common.backstageOps")}">
          <button
            id="ops-tab-monitor"
            type="button"
            class="ops-subtab is-active"
            data-ops-tab="monitor"
            role="tab"
            aria-selected="true"
            aria-controls="ops-panel-monitor"
          >
            <span>${e.t("ops.tabs.monitor")}</span>
            <small>${e.t("ops.tabs.monitorHint")}</small>
          </button>
          <button
            id="ops-tab-ingestion"
            type="button"
            class="ops-subtab"
            data-ops-tab="ingestion"
            role="tab"
            aria-selected="false"
            aria-controls="ops-panel-ingestion"
          >
            <span>${e.t("ops.tabs.ingestion")}</span>
            <small>${e.t("ops.tabs.ingestionHint")}</small>
          </button>
          <button
            id="ops-tab-control"
            type="button"
            class="ops-subtab"
            data-ops-tab="control"
            role="tab"
            aria-selected="false"
            aria-controls="ops-panel-control"
          >
            <span>${e.t("ops.tabs.control")}</span>
            <small>${e.t("ops.tabs.controlHint")}</small>
          </button>
          <button
            id="ops-tab-embeddings"
            type="button"
            class="ops-subtab"
            data-ops-tab="embeddings"
            role="tab"
            aria-selected="false"
            aria-controls="ops-panel-embeddings"
          >
            <span>Embeddings</span>
            <small>Vectorizar corpus</small>
          </button>
          <button
            id="ops-tab-reindex"
            type="button"
            class="ops-subtab"
            data-ops-tab="reindex"
            role="tab"
            aria-selected="false"
            aria-controls="ops-panel-reindex"
          >
            <span>Re-index</span>
            <small>Reindexar y sincronizar</small>
          </button>
        </nav>

        <section id="ops-panel-monitor" class="ops-tab-panel ops-tab-panel-monitor is-active" role="tabpanel">
          <article class="ops-card ops-window">
            <div class="ops-window-head ops-card-head">
              <h2>${e.t("ops.runs.title")}</h2>
              <button id="refresh-runs" type="button" class="secondary-btn">${e.t("ops.runs.refresh")}</button>
            </div>
            <div class="ops-window-body ops-window-body-table">
              <div class="ops-table-wrap">
                <table class="ops-table">
                  <thead>
                    <tr>
                      <th>${e.t("ops.runs.run")}</th>
                      <th>${e.t("ops.runs.trace")}</th>
                      <th>${e.t("ops.runs.status")}</th>
                      <th>${e.t("ops.runs.started")}</th>
                    </tr>
                  </thead>
                  <tbody id="runs-body"></tbody>
                </table>
              </div>
            </div>
          </article>

          <article class="ops-card ops-window">
            <div class="ops-window-head">
              <h2>${e.t("ops.timeline.title")}</h2>
              <p id="timeline-meta">${e.t("ops.timeline.select")}</p>
            </div>
            <div class="ops-window-body">
              <p id="cascade-note" class="ops-subcopy">${e.t("ops.timeline.waterfallNote")}</p>

              <section class="ops-cascade-group" aria-labelledby="user-cascade-title">
                <div class="ops-cascade-group-head">
                  <div>
                    <p class="ops-cascade-kicker">${e.t("ops.timeline.userKicker")}</p>
                    <h3 id="user-cascade-title">${e.t("ops.timeline.userTitle")}</h3>
                  </div>
                  <p id="user-cascade-summary" class="ops-cascade-total">-</p>
                </div>
                <ol id="user-cascade" class="ops-cascade-list"></ol>
              </section>

              <section class="ops-cascade-group" aria-labelledby="technical-cascade-title">
                <div class="ops-cascade-group-head">
                  <div>
                    <p class="ops-cascade-kicker">${e.t("ops.timeline.technicalKicker")}</p>
                    <h3 id="technical-cascade-title">${e.t("ops.timeline.technicalTitle")}</h3>
                  </div>
                  <p id="technical-cascade-summary" class="ops-cascade-total">-</p>
                </div>
                <ol id="technical-cascade" class="ops-cascade-list"></ol>
              </section>

              <details class="ops-timeline-raw">
                <summary>${e.t("ops.timeline.rawTitle")}</summary>
                <ul id="timeline" class="timeline"></ul>
              </details>
            </div>
          </article>
        </section>

        <section id="ops-panel-ingestion" class="ops-tab-panel ops-tab-panel-ingestion" role="tabpanel" hidden>
          <details class="ops-card ops-window ops-window--collapsible" open>
            <summary class="ops-window-head ops-card-head">
              <h2>${e.t("ops.ingestion.title")}</h2>
              <button id="ingestion-refresh" type="button" class="secondary-btn">${e.t("ops.ingestion.actions.refresh")}</button>
            </summary>
            <div class="ops-window-body">
              <p class="ops-copy">${e.t("ops.ingestion.lede")}</p>

              <div class="ops-control-grid">
                <label class="ops-field">
                  <span>Tema del Corpus</span>
                  <div style="display:flex;gap:0.4rem;align-items:center">
                    <select id="ingestion-corpus" aria-label="Tema del Corpus" style="flex:1"></select>
                    <button id="ingestion-add-corpus-btn" type="button" class="secondary-btn" style="padding:0.35rem 0.65rem;font-size:1.1rem;line-height:1" title="Agregar categoría">+</button>
                  </div>
                </label>

                <label class="ops-field">
                  <span>${e.t("ops.ingestion.batchType")}</span>
                  <select id="ingestion-batch-type" aria-label="${e.t("ops.ingestion.batchType")}">
                    <option value="autogenerar">Autogenerar</option>
                    <option value="normative_base">${e.t("ops.ingestion.batchType.normative")}</option>
                    <option value="interpretative_guidance">${e.t("ops.ingestion.batchType.interpretative")}</option>
                    <option value="practica_erp">${e.t("ops.ingestion.batchType.practical")}</option>
                  </select>
                </label>
              </div>

              <section
                id="ingestion-dropzone"
                class="ops-dropzone"
                tabindex="0"
                role="button"
                aria-controls="ingestion-file-input"
              >
                <strong>${e.t("ops.ingestion.dropzone")}</strong>
                <p>${e.t("ops.ingestion.dropzoneHelp")}</p>
                <input
                  id="ingestion-file-input"
                  type="file"
                  multiple
                  accept=".md,.txt,.json,.pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,text/markdown,application/json"
                />
                <input
                  id="ingestion-folder-input"
                  type="file"
                  webkitdirectory
                />
              </section>

              <div id="ingestion-upload-progress" class="ops-upload-progress" hidden></div>

              <p id="ingestion-pending-files" class="ops-inline-note">${e.t("ops.ingestion.pendingNone")}</p>

              <div class="ops-action-groups">
                <fieldset class="ops-action-group">
                  <legend>${e.t("ops.ingestion.groupAuto")}</legend>
                  <div class="ops-action-row">
                    <button id="ingestion-select-folder" type="button" class="secondary-btn">${e.t("ops.ingestion.selectFolder")}</button>
                    <button id="ingestion-auto-process" type="button" class="primary-btn">▶ ${e.t("ops.ingestion.actions.autoProcess")}</button>
                  </div>
                  <p id="ingestion-auto-status" class="ops-auto-status" hidden></p>
                </fieldset>

                <fieldset class="ops-action-group">
                  <legend>${e.t("ops.ingestion.groupManual")}</legend>
                  <div class="ops-action-row">
                    <button id="ingestion-create-session" type="button" class="secondary-btn success-btn">${e.t("ops.ingestion.newSession")}</button>
                    <button id="ingestion-select-files" type="button" class="secondary-btn">${e.t("ops.ingestion.selectFiles")}</button>
                    <button id="ingestion-upload-files" type="button" class="primary-btn">${e.t("ops.ingestion.upload")}</button>
                    <button id="ingestion-process-session" type="button" class="primary-btn">${e.t("ops.ingestion.actions.process")}</button>
                    <button id="ingestion-validate-batch" type="button" class="primary-btn">${e.t("ops.ingestion.actions.validateBatch")}</button>
                    <button id="ingestion-retry-session" type="button" class="secondary-btn">${e.t("ops.ingestion.actions.retry")}</button>
                    <button id="ingestion-delete-failed" type="button" class="secondary-btn">${e.t("ops.ingestion.actions.deleteFailed")}</button>
                    <button id="ingestion-stop-session" type="button" class="secondary-btn danger-btn">${e.t("ops.ingestion.actions.stop")}</button>
                    <button id="ingestion-clear-batch" type="button" class="secondary-btn">${e.t("ops.ingestion.actions.clearBatch")}</button>
                    <button id="ingestion-delete-session" type="button" class="secondary-btn danger-btn">${e.t("ops.ingestion.actions.deleteSession")}</button>
                  </div>
                </fieldset>
              </div>

              <p id="ingestion-overview" class="ops-inline-note"></p>
              <div id="ingestion-flash" class="ops-flash" hidden></div>
            </div>
          </details>

          <details id="ingestion-bounce-log" class="ops-card ops-accordion" hidden>
            <summary class="ops-accordion-head">
              <h2>${e.t("ops.ingestion.bounceLog.title")}</h2>
              <button id="ingestion-bounce-copy" type="button" class="ops-log-copy-btn" title="${e.t("ops.ingestion.log.copy")}">${e.t("ops.ingestion.log.copy")}</button>
            </summary>
            <div class="ops-accordion-body">
              <pre id="ingestion-bounce-body" class="ops-log-body"></pre>
            </div>
          </details>

          <article class="ops-card ops-window">
            <div class="ops-window-head">
              <h2>${e.t("ops.ingestion.selectedTitle")}</h2>
              <p id="selected-session-meta" class="ops-subcopy">${e.t("ops.ingestion.selectedEmpty")}</p>
            </div>
            <div class="ops-window-body ops-window-body-selected">
              <div id="ingestion-last-error" class="ops-guidance" hidden>
                <strong>${e.t("ops.ingestion.lastErrorTitle")}</strong>
                <p id="ingestion-last-error-message"></p>
                <p id="ingestion-last-error-guidance"></p>
                <p id="ingestion-last-error-next"></p>
              </div>

              <div id="ingestion-kanban" class="kanban-board"></div>

              <details id="ingestion-log-accordion" class="ops-log-accordion" hidden>
                <summary class="ops-log-accordion-summary">
                  <span>${e.t("ops.ingestion.log.title")}</span>
                  <button id="ingestion-log-copy" type="button" class="ops-log-copy-btn" title="${e.t("ops.ingestion.log.copy")}">${e.t("ops.ingestion.log.copy")}</button>
                </summary>
                <pre id="ingestion-log-body" class="ops-log-body"></pre>
              </details>
            </div>
          </article>

          <details class="ops-card ops-accordion">
            <summary class="ops-accordion-head">
              <h2>${e.t("ops.ingestion.sessionsTitle")}</h2>
              <p id="ingestion-session-meta" class="ops-subcopy"></p>
            </summary>
            <div class="ops-accordion-body">
              <ul id="ingestion-sessions-list" class="ops-session-list"></ul>
            </div>
          </details>
        </section>

        <section id="ops-panel-control" class="ops-tab-panel ops-tab-panel-control" role="tabpanel" hidden>
          <article class="ops-card ops-window">
            <div class="ops-window-head">
              <h2>${e.t("chat.workspace.title")}</h2>
            </div>
            <div class="ops-window-body">
              <p class="ops-copy">${e.t("chat.workspace.note")}</p>
              <div class="workspace-summary">
                <div class="workspace-summary-card">
                  <p class="workspace-summary-label">${e.t("chat.debug.label")}</p>
                  <p id="debug-summary" class="workspace-summary-value">${e.t("chat.debug.inactive")}</p>
                </div>
              </div>
              <div class="backstage-controls">
                <label class="inline-toggle">
                  <input id="debug" type="checkbox" />
                  ${e.t("chat.debug.label")}
                </label>
              </div>
            </div>
          </article>

          <article class="ops-card ops-window">
            <div class="ops-window-head">
              <h2>${e.t("chat.metrics.title")}</h2>
            </div>
            <div class="ops-window-body">
              <div class="runtime-grid">
                <div class="runtime-card">
                  <p class="runtime-label">${e.t("chat.metrics.timer")}</p>
                  <p id="runtime-request-timer" class="runtime-value">0.00 s</p>
                </div>
                <div class="runtime-card">
                  <p class="runtime-label">${e.t("chat.metrics.latency")}</p>
                  <p id="runtime-latency" class="runtime-value">-</p>
                </div>
                <div class="runtime-card">
                  <p class="runtime-label">${e.t("chat.metrics.model")}</p>
                  <p id="runtime-model" class="runtime-value">-</p>
                </div>
                <div class="runtime-card">
                  <p class="runtime-label">${e.t("chat.metrics.turnTokens")}</p>
                  <p id="runtime-turn-tokens" class="runtime-value">-</p>
                </div>
                <div class="runtime-card">
                  <p class="runtime-label">${e.t("chat.metrics.conversationTokens")}</p>
                  <p id="runtime-conversation-tokens" class="runtime-value">-</p>
                </div>
              </div>
            </div>
          </article>

          <article class="ops-card ops-window">
            <div class="ops-window-head">
              <h2>${e.t("chat.audit.title")}</h2>
            </div>
            <div class="ops-window-body">
              <pre id="diagnostics" class="diagnostics">${e.t("chat.debug.off")}</pre>
            </div>
          </article>

          <article class="ops-card ops-window ops-window-lifecycle">
            <div class="ops-window-head">
              <h2>Ciclo de Vida del Corpus</h2>
            </div>
            <div class="ops-window-body">
              <div id="corpus-lifecycle"></div>
            </div>
          </article>
        </section>

        <section id="ops-panel-embeddings" class="ops-tab-panel" role="tabpanel" hidden>
          <article class="ops-card ops-window ops-window-embeddings">
            <div class="ops-window-head">
              <h2>Embeddings</h2>
            </div>
            <div class="ops-window-body">
              <div id="embeddings-lifecycle"></div>
            </div>
          </article>
        </section>

        <section id="ops-panel-reindex" class="ops-tab-panel" role="tabpanel" hidden>
          <article class="ops-card ops-window ops-window-reindex">
            <div class="ops-window-head">
              <h2>Re-index</h2>
            </div>
            <div class="ops-window-body">
              <div id="reindex-lifecycle"></div>
            </div>
          </article>
        </section>
      </section>
      ${Ut()}
    </main>
  `}const hn=Object.freeze(Object.defineProperty({__proto__:null,renderBackstageShell:_s,renderIngestionShell:$s,renderOpsShell:ws,renderPromocionShell:ks},Symbol.toStringTag,{value:"Module"})),Ss=2e3;function M(e){return String(e??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#39;")}function se(e){return(e??0).toLocaleString("es-CO")}function Ps(e){if(!e)return"-";try{return new Date(e).toLocaleDateString("es-CO",{day:"numeric",month:"short",hour:"2-digit",minute:"2-digit",timeZone:"America/Bogota"})}catch{return e}}function Nt(e){if(!e)return"-";const t=Date.parse(e);if(Number.isNaN(t))return e;const n=Math.max(0,Math.floor((Date.now()-t)/1e3));if(n<5)return"ahora";if(n<60)return`hace ${n}s`;const d=Math.floor(n/60),o=n%60;return d<60?`hace ${d}m ${o}s`:`hace ${Math.floor(d/60)}h ${d%60}m`}function Re(e){return e?e.length>24?`${e.slice(0,15)}…${e.slice(-8)}`:e:"-"}function Es(e){return e===void 0?'<span class="ops-dot ops-dot-unknown">●</span>':e?'<span class="ops-dot ops-dot-ok">●</span>':'<span class="ops-dot ops-dot-error">●</span>'}function Rt(e,t){if(!t.available)return`
      <div class="corpus-card corpus-card-unavailable">
        <h4 class="corpus-card-title">${M(e)}</h4>
        <p class="corpus-card-unavail">● no disponible</p>
        ${t.error?`<p class="ops-subcopy">${M(t.error)}</p>`:""}
      </div>`;const n=t.knowledge_class_counts??{};return`
    <div class="corpus-card">
      <h4 class="corpus-card-title">${M(e)}</h4>
      <div class="corpus-card-row"><span>Gen:</span> <code>${M(Re(t.generation_id))}</code></div>
      <div class="corpus-card-row"><span>Documentos:</span> <strong>${se(t.documents)}</strong></div>
      <div class="corpus-card-row"><span>Chunks:</span> <strong>${se(t.chunks)}</strong></div>
      <div class="corpus-card-row"><span>Embeddings:</span> ${Es(t.embeddings_complete)} ${t.embeddings_complete?"completos":"incompletos"}</div>
      <div class="corpus-card-sep"></div>
      <div class="corpus-card-row corpus-card-row-sm"><span>normative_base:</span> ${se(n.normative_base)}</div>
      <div class="corpus-card-row corpus-card-row-sm"><span>interpretative:</span> ${se(n.interpretative_guidance)}</div>
      <div class="corpus-card-row corpus-card-row-sm"><span>practica_erp:</span> ${se(n.practica_erp)}</div>
      <div class="corpus-card-sep"></div>
      <div class="corpus-card-row corpus-card-row-sm"><span>${e==="PRODUCTION"?"Activado:":"Actualizado:"}</span> ${M(Ps(t.activated_at))}</div>
    </div>`}function Mt(e,t={}){const{onlyFailures:n=!1}=t,d=(e??[]).filter(o=>n?!o.ok:!0);return d.length===0?"":`
    <ul class="corpus-checks">
      ${d.map(o=>`
            <li class="corpus-check ${o.ok?"is-ok":"is-fail"}">
              <span class="corpus-check-dot"></span>
              <div>
                <strong>${M(o.label)}</strong>
                <span>${M(o.detail)}</span>
              </div>
            </li>`).join("")}
    </ul>`}function Cs(e){const t=e??[];return t.length===0?"":`
    <ol class="corpus-stage-list">
      ${t.map(n=>`
            <li class="corpus-stage-item state-${M(n.state)}">
              <span class="corpus-stage-dot"></span>
              <span>${M(n.label)}</span>
            </li>`).join("")}
    </ol>`}function ct(e){const t=String(e||"").trim();return t?t.replaceAll("_"," "):"-"}function xs(e){return e?e.kind==="audit"?"Audit":e.kind==="rollback"?"Rollback":e.mode==="force_reset"?"Force reset":"Promote":"Promote"}function vt(e){const t=e==null?void 0:e.last_checkpoint;if(!(t!=null&&t.phase))return"-";const n=t.cursor??0,d=t.total??0,o=d>0?(n/d*100).toFixed(1):"0";return`${ct(t.phase)} · ${se(n)} / ${se(d)} (${o}%)`}function qt(e){var d,o;const t=((d=e==null?void 0:e.last_checkpoint)==null?void 0:d.cursor)??(e==null?void 0:e.batch_cursor)??0,n=((o=e==null?void 0:e.last_checkpoint)==null?void 0:o.total)??0;return n<=0?0:Math.min(100,Math.max(0,t/n*100))}function Ts(e){if(!(e!=null&&e.heartbeat_at))return{label:"-",className:""};const t=Math.max(0,(Date.now()-Date.parse(e.heartbeat_at))/1e3);return t<15?{label:"Saludable",className:"hb-healthy"}:t<45?{label:"Lento",className:"hb-slow"}:{label:"Sin respuesta",className:"hb-stale"}}function Is(e,t){var n,d,o,m,k,y;if(e)switch(e.operation_state_code){case"orphaned_queue":return{severity:"red",title:"Orphaned before start",detail:"The request was queued, but the backend worker never started."};case"stalled_resumable":return{severity:"red",title:"Stalled",detail:(n=e.last_checkpoint)!=null&&n.phase?`Backend stalled after ${ct(e.last_checkpoint.phase)}. Resume is available.`:"Backend stalled, but a checkpoint is available to resume."};case"failed_resumable":return{severity:"red",title:"Resumable",detail:e.error||((o=(d=e.failures)==null?void 0:d[0])==null?void 0:o.message)||"The last run failed after writing a checkpoint. Resume is available."};case"completed":return{severity:"green",title:"Completed",detail:e.kind==="audit"?"WIP audit completed. Artifact written.":e.kind==="rollback"?"Rollback completed and verified.":"Promotion completed and verified."};case"running":return{severity:"yellow",title:"Running",detail:e.current_phase?`Backend phase: ${ct(e.current_phase)}.`:e.stage_label?`Stage: ${e.stage_label}.`:"The backend is processing the promotion."};default:return{severity:e.severity??"red",title:e.severity==="yellow"?"Running":"Failed",detail:e.error||((k=(m=e.failures)==null?void 0:m[0])==null?void 0:k.message)||"The operation ended with an error."}}return t!=null&&t.preflight_ready?{severity:"green",title:"Ready",detail:"WIP audit and promotion preflight are green."}:{severity:"red",title:"Blocked",detail:((y=t==null?void 0:t.preflight_reasons)==null?void 0:y[0])||"Production is not ready for a safe promotion."}}function Ls(e){return e?e.kind==="audit"?"WIP Health Audit":e.kind==="rollback"?"Rollback Production":e.mode==="force_reset"?"Force Reset + Promote Production":"Promote WIP to Production":"Promote WIP to Production"}function Ot(e,t){return!t||t.available===!1?`<tr><td>${M(e)}</td><td colspan="2" class="corpus-report-unavail">no disponible</td></tr>`:`
    <tr>
      <td>${M(e)}</td>
      <td><code>${M(Re(t.generation_id))}</code></td>
      <td>${se(t.documents)} docs · ${se(t.chunks)} chunks</td>
    </tr>`}function Dt(e,t){const n=new Set;for(const o of Object.keys((e==null?void 0:e.knowledge_class_counts)??{}))n.add(o);for(const o of Object.keys((t==null?void 0:t.knowledge_class_counts)??{}))n.add(o);return n.size===0?"":[...n].sort().map(o=>{const m=((e==null?void 0:e.knowledge_class_counts)??{})[o]??0,k=((t==null?void 0:t.knowledge_class_counts)??{})[o]??0,y=k-m,C=y>0?"is-positive":y<0?"is-negative":"",L=y>0?`+${se(y)}`:y<0?se(y):"—";return`
        <tr class="corpus-report-kc-row">
          <td>${M(o)}</td>
          <td>${se(m)}</td>
          <td>${se(k)}</td>
          <td class="corpus-report-delta ${C}">${L}</td>
        </tr>`}).join("")}function As(e,t){if(!e||!t)return"-";const n=Date.parse(e),d=Date.parse(t);if(Number.isNaN(n)||Number.isNaN(d))return"-";const o=Math.max(0,Math.floor((d-n)/1e3)),m=Math.floor(o/60),k=o%60;return m===0?`${k}s`:`${m}m ${k}s`}function Ns(e){const t=e==null?void 0:e.promotion_summary;if(!t)return"";const{before:n,after:d,delta:o,plan_result:m}=t,k=((o==null?void 0:o.documents)??0)>0?`+${se(o==null?void 0:o.documents)}`:se(o==null?void 0:o.documents),y=((o==null?void 0:o.chunks)??0)>0?`+${se(o==null?void 0:o.chunks)}`:se(o==null?void 0:o.chunks),C=((o==null?void 0:o.documents)??0)>0?"is-positive":((o==null?void 0:o.documents)??0)<0?"is-negative":"",L=((o==null?void 0:o.chunks)??0)>0?"is-positive":((o==null?void 0:o.chunks)??0)<0?"is-negative":"",W=n||d?`
      <table class="corpus-report-table">
        <thead>
          <tr><th></th><th>Generación</th><th>Documentos / Chunks</th></tr>
        </thead>
        <tbody>
          ${Ot("Antes",n)}
          ${Ot("Después",d)}
        </tbody>
        ${o?`
        <tfoot>
          <tr>
            <td>Delta</td>
            <td></td>
            <td>
              <span class="corpus-report-delta ${C}">${k} docs</span> ·
              <span class="corpus-report-delta ${L}">${y} chunks</span>
            </td>
          </tr>
        </tfoot>`:""}
      </table>
      ${Dt(n,d)?`
      <table class="corpus-report-table corpus-report-table-kc">
        <thead><tr><th>Clase</th><th>Antes</th><th>Después</th><th>Delta</th></tr></thead>
        <tbody>${Dt(n,d)}</tbody>
      </table>`:""}`:"",f=m?`
      <div class="corpus-report-grid">
        ${[{label:"Docs staged",key:"docs_staged"},{label:"Docs upserted",key:"docs_upserted"},{label:"Docs new",key:"docs_new"},{label:"Docs removed",key:"docs_removed"},{label:"Chunks new",key:"chunks_new"},{label:"Chunks changed",key:"chunks_changed"},{label:"Chunks removed",key:"chunks_removed"},{label:"Chunks unchanged",key:"chunks_unchanged"},{label:"Chunks embedded",key:"chunks_embedded"}].filter(j=>m[j.key]!==void 0&&m[j.key]!==null).map(j=>`
              <div class="corpus-report-stat">
                <span class="corpus-report-stat-value">${M(String(m[j.key]??"-"))}</span>
                <span class="corpus-report-stat-label">${M(j.label)}</span>
              </div>`).join("")}
      </div>`:"",N=As(e==null?void 0:e.started_at,e==null?void 0:e.completed_at);return`
    <div class="corpus-section corpus-report-section">
      <h4>Promotion Report</h4>
      ${W}
      ${f}
      ${N!=="-"?`<p class="corpus-report-duration">Duración: <strong>${M(N)}</strong></p>`:""}
    </div>`}function zt({dom:e,setFlash:t}){let n=null,d=null,o=null,m="",k="",y=null,C=null,L=!1,W=!1,F=!1,f=!1,N=0,j=null,x=0;function V(q,D){d&&clearTimeout(d),t(q,D);const w=e.container.querySelector(".corpus-toast");w&&(w.hidden=!1,w.dataset.tone=D,w.textContent=q,w.classList.remove("corpus-toast-enter"),w.offsetWidth,w.classList.add("corpus-toast-enter")),d=setTimeout(()=>{const b=e.container.querySelector(".corpus-toast");b&&(b.hidden=!0)},6e3)}function S(q,D,w,b="promote"){return new Promise(K=>{C==null||C.remove();const A=document.createElement("div");A.className="corpus-confirm-overlay",C=A,A.innerHTML=`
        <div class="corpus-confirm-dialog">
          <h3 class="corpus-confirm-title">${M(q)}</h3>
          <div class="corpus-confirm-body">${D}</div>
          <div class="corpus-confirm-actions">
            <button class="corpus-btn corpus-btn-rollback" data-action="cancel">Cancelar</button>
            <button class="corpus-btn ${b==="rollback"?"corpus-btn-rollback":"corpus-btn-promote"}" data-action="confirm">${M(w)}</button>
          </div>
        </div>
      `,document.body.appendChild(A),requestAnimationFrame(()=>A.classList.add("is-visible"));function g(oe){C===A&&(C=null),A.classList.remove("is-visible"),setTimeout(()=>A.remove(),180),K(oe)}A.addEventListener("click",oe=>{const he=oe.target.closest("[data-action]");he?g(he.dataset.action==="confirm"):oe.target===A&&g(!1)})})}async function E(q,D,w,b){if(!m){m=w,O();try{const{response:K,data:A}=await Ye(q,D);K.ok&&(A!=null&&A.job_id)?(y={tone:"success",message:`${b} Job ${Re(A.job_id)}.`},V(`${b} Job ${Re(A.job_id)}.`,"success")):(y={tone:"error",message:(A==null?void 0:A.error)||"No se pudo iniciar la operación."},V((A==null?void 0:A.error)||"No se pudo iniciar la operación.","error"))}catch(K){const A=K instanceof Error?K.message:String(K);y={tone:"error",message:A},V(A,"error")}finally{m="",await le()}}}async function v(){const q=n;if(!q||m||!await S("Promote WIP to Production",`<p>This path reuses the live WIP generation and promotes it incrementally into Production with persisted checkpoints.</p>
       <table class="corpus-confirm-table">
         <tr><td>Production current:</td><td><strong>${se(q.production.documents)}</strong> docs · <strong>${se(q.production.chunks)}</strong> chunks</td></tr>
         <tr><td>WIP source:</td><td><strong>${se(q.wip.documents)}</strong> docs · <strong>${se(q.wip.chunks)}</strong> chunks</td></tr>
         <tr><td>WIP generation:</td><td><code>${M(Re(q.wip.generation_id))}</code></td></tr>
       </table>
       <label style="display:flex;align-items:center;gap:0.4rem;margin:0.75rem 0;font-size:0.85rem;cursor:pointer">
         <input type="checkbox" id="corpus-force-full-upsert" />
         Forzar upsert completo (sincronizar summaries + embeddings aunque chunk_text no haya cambiado)
       </label>
       <p class="corpus-confirm-note">The backend will keep a promotion plan, batch checkpoints, and a resumable cursor before activation.</p>`,"Promote now"))return;const w=document.querySelector("#corpus-force-full-upsert"),b=(w==null?void 0:w.checked)??!1;f=!1,N=0,j=null,x=0,await E("/api/ops/corpus/rebuild-from-wip",{mode:"promote",force_full_upsert:b},"promote",b?"Promotion started (force full upsert).":"Promotion started.")}async function c(){var w;const q=(n==null?void 0:n.current_operation)??(n==null?void 0:n.last_operation)??null;!(q!=null&&q.resume_job_id)||m||!await S("Resume from Checkpoint",`<p>The backend will reuse the persisted promotion plan and continue from the last completed checkpoint.</p>
       <table class="corpus-confirm-table">
         <tr><td>Job:</td><td><code>${M(Re(q.resume_job_id))}</code></td></tr>
         <tr><td>Checkpoint:</td><td>${M(vt(q))}</td></tr>
         <tr><td>Target generation:</td><td><code>${M(Re(q.target_generation_id))}</code></td></tr>
       </table>`,"Resume now")||(f=!0,N=((w=q.last_checkpoint)==null?void 0:w.cursor)??0,j=null,x=0,await E("/api/ops/corpus/rebuild-from-wip/resume",{job_id:q.resume_job_id},"resume","Resume started."))}async function $(){const q=n;!q||!q.rollback_generation_id||m||!await S("Rollback de Production",`<p>Se va a intentar reactivar una generación previa de production.</p>
       <table class="corpus-confirm-table">
         <tr><td>Production actual:</td><td><code>${M(Re(q.production.generation_id))}</code></td></tr>
         <tr><td>Objetivo:</td><td><code>${M(Re(q.rollback_generation_id))}</code></td></tr>
       </table>
       <p class="corpus-confirm-note">Solo se habilita si el backend detecta una generación previa todavía utilizable.</p>`,"Revertir ahora","rollback")||await E("/api/ops/corpus/rollback",{generation_id:q.rollback_generation_id},"rollback","Rollback started.")}async function R(){m||await E("/api/ops/corpus/wip-audit",{},"audit","WIP audit started.")}async function X(){m||!await S("Reiniciar promoción",`<p>Cancela cualquier job anterior y lanza una nueva promoción desde WIP a producción.</p>
       <label style="display:flex;align-items:center;gap:0.4rem;margin:0.75rem 0;font-size:0.85rem;cursor:default;opacity:0.55" title="Force upsert es obligatorio en reinicio">
         <input type="checkbox" checked disabled style="opacity:0.55" />
         Forzar upsert completo (sincronizar summaries + embeddings aunque chunk_text no haya cambiado)
       </label>
       <p class="corpus-confirm-note">Reiniciar siempre usa force upsert: todos los ~50K chunks se copian completos.</p>`,"Reiniciar ahora","rollback")||(f=!1,N=0,j=null,x=0,await E("/api/ops/corpus/rebuild-from-wip/restart",{},"restart","Restart submitted (force full upsert)."))}async function me(){if(!(F||m||!await S("Sincronizar JSONL a WIP",`<p>Se va a sincronizar el índice JSONL local ya existente al Supabase WIP (Docker).</p>
       <p class="corpus-confirm-note">Esta operación no ejecuta reindex — solo sincroniza los documentos y chunks que ya existen en el JSONL local. Es segura e idempotente.</p>`,"Sincronizar ahora"))){F=!0,O();try{const{response:D,data:w}=await Ye("/api/ops/corpus/sync-to-wip",{});D.ok&&(w!=null&&w.synced)?V(`WIP sincronizado: ${se(w.documents)} docs, ${se(w.chunks)} chunks.`,"success"):V((w==null?void 0:w.error)||"Error sincronizando a WIP.","error")}catch(D){const w=D instanceof Error?D.message:String(D);V(w||"Error sincronizando a WIP.","error")}finally{F=!1,await le()}}}async function fe(){const q=(n==null?void 0:n.current_operation)??(n==null?void 0:n.last_operation)??null,D=String((q==null?void 0:q.log_tail)||"").trim();if(D)try{await navigator.clipboard.writeText(D),V("Log tail copied.","success")}catch(w){const b=w instanceof Error?w.message:"Could not copy log tail.";V(b||"Could not copy log tail.","error")}}function O(){var ye,_e,U,Se,xe,Te,qe,Pe,Ie,Le,He;const q=e.container.querySelector(".corpus-log-accordion");q&&(L=q.open);const D=e.container.querySelector(".corpus-checks-accordion");D&&(W=D.open);const w=n;if(!w){e.container.innerHTML=`<p class="ops-empty">${M(k||"Cargando estado del corpus…")}</p>`;return}const b=w.current_operation??w.last_operation??null,K=Is(b,w),A=!!(w.current_operation&&["queued","running"].includes(w.current_operation.status))||!!m,g=A||!w.preflight_ready,oe=!A&&!!(b&&b.resume_supported&&b.resume_job_id&&(b.operation_state_code==="stalled_resumable"||b.operation_state_code==="failed_resumable")),he=A||!w.rollback_available,_=w.delta.documents==="+0"&&w.delta.chunks==="+0"?"Sin delta pendiente":`${w.delta.documents} documentos · ${w.delta.chunks} chunks`,I=Mt(b==null?void 0:b.checks,{onlyFailures:!0}),Z=Mt(b==null?void 0:b.checks),H=!!(w.current_operation&&["queued","running"].includes(w.current_operation.status)),ae=y&&!(w.current_operation&&["queued","running"].includes(w.current_operation.status))?`
          <div class="corpus-callout tone-${M(y.tone==="success"?"green":"red")}">
            <strong>${y.tone==="success"?"Request sent":"Request failed"}</strong>
            <span>${M(y.message)}</span>
          </div>`:"",ee=(ye=b==null?void 0:b.last_checkpoint)!=null&&ye.phase?(()=>{const ue=b.operation_state_code==="completed"?"green":b.operation_state_code==="failed_resumable"||b.operation_state_code==="stalled_resumable"?"red":"yellow",be=qt(b);return`
            <div class="corpus-callout tone-${M(ue)}">
              <strong>Checkpoint</strong>
              <span>${M(vt(b))} · ${M(Nt(b.last_checkpoint.at||null))}</span>
              ${be>0&&ue!=="green"?`<div class="corpus-progress-bar corpus-progress-bar-sm"><div class="corpus-progress-fill" style="width:${be.toFixed(1)}%"></div></div>`:""}
            </div>`})():"";e.container.innerHTML=`
      <div class="corpus-cards">
        ${Rt("WIP",w.wip)}
        ${Rt("PRODUCTION",w.production)}
      </div>
      <div class="corpus-delta">
        <span class="corpus-delta-label">${M(_)}</span>
      </div>
      <section class="corpus-operation-panel severity-${M(K.severity)}">
        <div class="corpus-operation-header">
          <div>
            <div class="corpus-status-chip tone-${M(K.severity)}${K.severity==="yellow"?" is-pulsing":""}">
              ${M(K.title)}
            </div>
            <h3 class="corpus-operation-title">${M(Ls(b))}</h3>
            <p class="corpus-operation-detail">${M(K.detail)}</p>
          </div>
          <dl class="corpus-operation-meta">
            <div><dt>Heartbeat</dt><dd>${M(Nt((b==null?void 0:b.heartbeat_at)||(b==null?void 0:b.updated_at)||null))}</dd></div>
            <div><dt>Backend</dt><dd>${M(xs(b))}${b!=null&&b.force_full_upsert?` <span style="background:${At.amber[100]};color:${At.amber[600]};padding:0.1rem 0.4rem;border-radius:0.3rem;font-size:0.7rem;font-weight:700">FORCE UPSERT</span>`:""}</dd></div>
            <div><dt>Phase</dt><dd>${M(b!=null&&b.current_phase?ct(b.current_phase):(b==null?void 0:b.stage_label)||(w.preflight_ready?"Ready":"Blocked"))}</dd></div>
            <div><dt>Checkpoint</dt><dd>${M(vt(b))}</dd></div>
            <div><dt>WIP</dt><dd><code>${M(Re((b==null?void 0:b.source_generation_id)||w.wip.generation_id))}</code></dd></div>
            <div><dt>Target</dt><dd><code>${M(Re((b==null?void 0:b.target_generation_id)||(b==null?void 0:b.production_generation_id)||w.production.generation_id))}</code></dd></div>
            <div><dt>Prod</dt><dd><code>${M(Re((b==null?void 0:b.production_generation_id)||w.production.generation_id))}</code></dd></div>
          </dl>
        </div>
        ${H?(()=>{var Me,Ae;const ue=qt(b),be=((Me=b==null?void 0:b.last_checkpoint)==null?void 0:Me.cursor)??(b==null?void 0:b.batch_cursor)??0,Oe=((Ae=b==null?void 0:b.last_checkpoint)==null?void 0:Ae.total)??0,Ee=Ts(b);if(be>0&&Oe>0){const Be=Date.now();if(j&&be>j.cursor){const $e=Math.max(1,(Be-j.ts)/1e3),je=(be-j.cursor)/$e;x=x>0?x*.7+je*.3:je}j={cursor:be,ts:Be}}const De=x>0?`${x.toFixed(0)} chunks/s`:"",ie=Oe-be,We=x>0&&ie>0?(()=>{const Be=Math.ceil(ie/x),$e=Math.floor(Be/60),je=Be%60;return $e>0?`~${$e}m ${je}s restante`:`~${je}s restante`})():"";return`
            <div class="corpus-progress-bar"><div class="corpus-progress-fill" style="width:${ue.toFixed(1)}%"></div></div>
            <div class="corpus-progress-detail">
              ${f?`<span class="corpus-resume-badge">REANUDADO desde ${se(N)}</span>`:""}
              <span class="corpus-progress-nums">${se(be)} / ${se(Oe)} (${ue.toFixed(1)}%)</span>
              ${De?`<span class="corpus-progress-rate">${M(De)}</span>`:""}
              ${We?`<span class="corpus-progress-eta">${M(We)}</span>`:""}
              <span class="corpus-hb-badge ${Ee.className}">${M(Ee.label)}</span>
            </div>`})():""}
        ${(_e=b==null?void 0:b.stages)!=null&&_e.length?Cs(b.stages):""}
        ${ee}
        ${(U=w.preflight_reasons)!=null&&U.length&&!H&&!w.preflight_ready?`
          <div class="corpus-callout tone-red">
            <strong>Preflight blocked</strong>
            <ul>${w.preflight_reasons.map(ue=>`<li>${M(ue)}</li>`).join("")}</ul>
          </div>`:""}
        ${ae}
        ${I?`<div class="corpus-section"><h4>Visible failures</h4>${I}</div>`:""}
        ${Z?`
          <details class="corpus-section corpus-checks-accordion">
            <summary class="corpus-checks-summary"><h4>Checks</h4><span class="corpus-checks-count">${((b==null?void 0:b.checks)??[]).length}</span></summary>
            ${Z}
          </details>`:""}
        ${Ns(b)}
        ${b!=null&&b.log_tail?`
          <details class="corpus-section corpus-log-accordion">
            <summary class="corpus-log-summary">
              <h4>Backend log tail</h4>
              <button id="corpus-copy-log-tail-btn" type="button" class="corpus-btn corpus-btn-rollback corpus-btn-inline">Copy</button>
            </summary>
            <pre class="corpus-log-tail">${M(b.log_tail)}</pre>
          </details>`:""}
        ${k?`
          <div class="corpus-callout tone-red">
            <strong>Refresh error</strong>
            <span>${M(k)}</span>
          </div>`:""}
      </section>
      <div class="corpus-actions">
        ${w.audit_missing&&!A?`
          <button id="corpus-audit-btn" class="corpus-btn corpus-btn-audit${m==="audit"?" is-busy":""}">
            ${m==="audit"?'<span class="corpus-spinner"></span> Auditing…':"Run WIP Audit"}
          </button>`:""}
        ${!A&&!F?`
          <button id="corpus-sync-wip-btn" class="corpus-btn corpus-btn-sync">Sincronizar JSONL a WIP</button>`:""}
        ${F?`
          <button class="corpus-btn corpus-btn-sync is-busy" disabled><span class="corpus-spinner"></span> Sincronizando…</button>`:""}
        <button id="corpus-promote-btn" class="corpus-btn corpus-btn-promote${m==="promote"?" is-busy":""}" ${g?"disabled":""}>
          ${m==="promote"?'<span class="corpus-spinner"></span> Starting…':"Promote WIP to Production"}
        </button>
        ${oe?`
          <button id="corpus-resume-btn" class="corpus-btn corpus-btn-promote${m==="resume"?" is-busy":""}">
            ${m==="resume"?'<span class="corpus-spinner"></span> Resuming…':"Resume from Checkpoint"}
          </button>`:""}
        <button id="corpus-rollback-btn" class="corpus-btn corpus-btn-rollback${m==="rollback"?" is-busy":""}" ${he?"disabled":""}>
          ${m==="rollback"?'<span class="corpus-spinner"></span> Starting rollback…':"Rollback"}
        </button>
        <button id="corpus-restart-btn" class="corpus-btn corpus-btn-rollback${m==="restart"?" is-busy":""}" ${A?"disabled":""}>
          ${m==="restart"?'<span class="corpus-spinner"></span> Restarting…':"Reiniciar promoción (force upsert)"}
        </button>
      </div>
      ${w.preflight_ready?"":`
        <p class="corpus-action-note">${M(((Se=w.preflight_reasons)==null?void 0:Se[0])||"Promotion is blocked by preflight.")}</p>`}
      ${w.rollback_available?"":`
        <p class="corpus-action-note">${M(w.rollback_reason||"Rollback is not available yet.")}</p>`}
      <div class="corpus-toast ops-flash" hidden></div>
    `,(xe=e.container.querySelector("#corpus-audit-btn"))==null||xe.addEventListener("click",R),(Te=e.container.querySelector("#corpus-sync-wip-btn"))==null||Te.addEventListener("click",()=>void me()),(qe=e.container.querySelector("#corpus-promote-btn"))==null||qe.addEventListener("click",v),(Pe=e.container.querySelector("#corpus-resume-btn"))==null||Pe.addEventListener("click",c),(Ie=e.container.querySelector("#corpus-rollback-btn"))==null||Ie.addEventListener("click",$),(Le=e.container.querySelector("#corpus-restart-btn"))==null||Le.addEventListener("click",X),(He=e.container.querySelector("#corpus-copy-log-tail-btn"))==null||He.addEventListener("click",ue=>{ue.preventDefault(),ue.stopPropagation(),fe()});const Q=e.container.querySelector(".corpus-log-accordion");Q&&L&&(Q.open=!0);const pe=e.container.querySelector(".corpus-checks-accordion");pe&&W&&(pe.open=!0)}async function le(){try{n=await Ze("/api/ops/corpus-status"),k="",n!=null&&n.current_operation&&["queued","running","completed","failed","cancelled"].includes(n.current_operation.status)&&(y=null)}catch(q){k=q instanceof Error?q.message:String(q),n===null&&(n=null)}O()}function Fe(){O(),o===null&&(o=window.setInterval(()=>{le()},Ss))}return{bindEvents:Fe,refresh:le}}const vn=Object.freeze(Object.defineProperty({__proto__:null,createCorpusLifecycleController:zt},Symbol.toStringTag,{value:"Module"})),Rs={normative_base:"Normativa",interpretative_guidance:"Interpretación",practica_erp:"Práctica"},St={declaracion_renta:"Renta",iva:"IVA",laboral:"Laboral",facturacion_electronica:"Facturación",estados_financieros_niif:"NIIF",ica:"ICA",calendario_obligaciones:"Calendarios",retencion_fuente:"Retención",regimen_sancionatorio:"Sanciones",regimen_cambiario:"Régimen Cambiario",impuesto_al_patrimonio:"Patrimonio",informacion_exogena:"Exógena",proteccion_de_datos:"Datos",obligaciones_mercantiles:"Mercantil",obligaciones_profesionales_contador:"Obligaciones Contador",rut_responsabilidades:"RUT",gravamen_movimiento_financiero_4x1000:"GMF 4×1000",beneficiario_final:"Beneficiario Final",contratacion_estatal:"Contratación Estatal",reforma_pensional:"Reforma Pensional",zomac_incentivos:"ZOMAC"},Wt="lia_backstage_ops_active_tab",$t="lia_backstage_ops_ingestion_session_id";function Ms(){const e=ut();try{const t=String(e.getItem(Wt)||"").trim();return t==="ingestion"||t==="control"||t==="embeddings"||t==="reindex"?t:"monitor"}catch{return"monitor"}}function qs(e){const t=ut();try{t.setItem(Wt,e)}catch{}}function Os(){const e=ut();try{return String(e.getItem($t)||"").trim()}catch{return""}}function Ds(e){const t=ut();try{if(!e){t.removeItem($t);return}t.setItem($t,e)}catch{}}function lt(e){return e==="processing"||e==="running_batch_gates"}function Bt(e){if(!e)return!1;const t=String(e.status||"").toLowerCase();if(t==="done"||t==="completed")return!0;const n=e.documents||[];return n.length===0?!1:n.every(d=>{const o=String(d.status||"").toLowerCase();return o==="done"||o==="completed"||o==="skipped_duplicate"||o==="bounced"})}function ot(e){const t=String(e||"").trim().toLowerCase();return t==="failed"||t==="error"?"error":t==="processing"||t==="running_batch_gates"||t==="needs_retry_batch_gate"||t==="queued"||t==="uploading"||t==="extracting"||t==="etl"||t==="writing"||t==="gates"||t==="in_progress"||t==="partial_failed"||t==="raw"||t==="pending_dedup"?"warn":"ok"}function de(e){return e instanceof pt?e.message||`HTTP ${e.status}`:e instanceof Error?e.message:String(e||"unknown_error")}function Bs(e,t){switch(String(e||"").trim()){case"normative_base":return t.t("ops.ingestion.batchType.normative");case"interpretative_guidance":return t.t("ops.ingestion.batchType.interpretative");case"practica_erp":return t.t("ops.ingestion.batchType.practical");default:return String(e||"-")}}function js(e,t){const n=Number(e||0);return!Number.isFinite(n)||n<=0?"0 B":n>=1024*1024?`${t.formatNumber(n/(1024*1024),{maximumFractionDigits:1})} MB`:n>=1024?`${t.formatNumber(n/1024,{maximumFractionDigits:1})} KB`:`${t.formatNumber(n)} B`}function jt(e,t){const n=e||{total:0,queued:0,done:0,failed:0,pending_batch_gate:0,bounced:0},d=[`${t.t("ops.ingestion.summary.total")} ${n.total||0}`,`${t.t("ops.ingestion.summary.done")} ${n.done||0}`,`${t.t("ops.ingestion.summary.failed")} ${n.failed||0}`,`${t.t("ops.ingestion.summary.queued")} ${n.queued||0}`,`${t.t("ops.ingestion.summary.gate")} ${n.pending_batch_gate||0}`],o=Number(n.bounced||0);return o>0&&d.push(`Rebotados ${o}`),d.join(" · ")}function kt(e,t,n){const d=e||t||"";if(!d)return"stalled";const o=Date.parse(d);if(Number.isNaN(o))return"stalled";const m=Date.now()-o,k=n==="gates",y=k?9e4:3e4,C=k?3e5:12e4;return m<y?"alive":m<C?"slow":"stalled"}function Fs(e,t){const n=e||t||"";if(!n)return"-";const d=Date.parse(n);if(Number.isNaN(d))return"-";const o=Math.max(0,Date.now()-d),m=Math.floor(o/1e3);if(m<5)return"ahora";if(m<60)return`hace ${m}s`;const k=Math.floor(m/60),y=m%60;return k<60?`hace ${k}m ${y}s`:`hace ${Math.floor(k/60)}h ${k%60}m`}const yt={validating:"validando corpus",manifest:"activando manifest",indexing:"reconstruyendo índice","indexing/scanning":"escaneando documentos","indexing/chunking":"generando chunks","indexing/writing_indexes":"escribiendo índices","indexing/syncing":"sincronizando Supabase","indexing/auditing":"auditando calidad"};function Gt(e){if(!e)return"";if(yt[e])return yt[e];const t=e.indexOf(":");if(t>0){const n=e.slice(0,t),d=e.slice(t+1),o=yt[n];if(o)return`${o} (${d})`}return e}function Hs(e){if(!e)return"";const t=Date.parse(e);if(Number.isNaN(t))return"";try{return new Intl.DateTimeFormat("es-CO",{timeZone:"America/Bogota",day:"2-digit",month:"2-digit",year:"numeric",hour:"2-digit",minute:"2-digit",second:"2-digit",hour12:!1}).format(new Date(t))}catch{return""}}function Jt(e,t){const n=Math.max(0,Math.min(100,Number(e||0))),d=document.createElement("div");d.className="ops-progress";const o=document.createElement("div");o.className="ops-progress-bar";const m=document.createElement("span");m.className="ops-progress-fill",t==="gates"&&n>0&&n<100&&m.classList.add("ops-progress-active"),m.style.width=`${n}%`;const k=document.createElement("span");return k.className="ops-progress-label",k.textContent=`${n}%`,o.appendChild(m),d.append(o,k),d}function Ue(e){return String(e??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#39;")}function Ke(e){return(e??0).toLocaleString("es-CO")}function Ft(e){if(e==null||e<=0)return"-";const t=Math.floor(e/60),n=Math.floor(e%60);return t>0?`${t}m ${n}s`:`${n}s`}function Vt({dom:e,setFlash:t}){const{container:n}=e;let d=null,o="",m=!1,k=!1,y=0,C=0,L=3e3,W=[];function F(v){if(v<=0)return;const c=Date.now();if(v>y&&C>0){const $=c-C,R=v-y,X=$/R;W.push(X),W.length>10&&W.shift(),L=W.reduce((me,fe)=>me+fe,0)/W.length}v!==y&&(y=v,C=c)}function f(){if(C===0)return{level:"healthy",label:"Iniciando..."};const v=Date.now()-C,c=Math.max(L*3,1e4),$=Math.max(L*6,3e4);return v<c?{level:"healthy",label:"Saludable"}:v<$?{level:"caution",label:"Lento"}:{level:"failed",label:"Sin respuesta"}}function N(){var Z,H,ae,ee,Q,pe,ye,_e;const v=d;if(!v){n.innerHTML='<p class="ops-text-muted">Cargando estado de embeddings...</p>';return}const c=v.current_operation||v.last_operation,$=((Z=v.current_operation)==null?void 0:Z.status)??"",R=$==="running"||$==="queued"||o==="start",X=!v.current_operation&&!o,me=o==="stop",fe=!R&&!me&&((c==null?void 0:c.status)==="cancelled"||(c==null?void 0:c.status)==="failed"||(c==null?void 0:c.status)==="stalled");let O="";const le=(c==null?void 0:c.status)??"",Fe=me?"Deteniendo...":R?"En ejecución":fe?le==="stalled"?"Detenido (stalled)":le==="cancelled"?"Cancelado":"Fallido":X?"Inactivo":le||"—",q=R?"tone-yellow":le==="completed"?"tone-green":le==="failed"||le==="stalled"?"tone-red":le==="cancelled"?"tone-yellow":"",D=v.api_health,w=D!=null&&D.ok?"emb-api-ok":"emb-api-error",b=D?D.ok?`API OK (${D.detail})`:`API Error: ${D.detail}`:"API: verificando...";if(O+=`<div class="emb-status-row">
      <span class="corpus-status-chip ${q}">${Ue(Fe)}</span>
      <span class="emb-target-badge">WIP</span>
      <span class="emb-api-semaphore ${w}" title="${Ue(b)}"><span class="emb-api-dot"></span> ${Ue(D!=null&&D.ok?"API OK":D?"API Error":"...")}</span>
      ${R?(()=>{const U=f();return`<span class="emb-process-health emb-health-${U.level}"><span class="emb-health-dot"></span> ${Ue(U.label)}</span>`})():""}
    </div>`,O+='<div class="emb-controls">',X?(O+=`<label class="emb-force-label"><input type="checkbox" id="emb-force-check" ${m?"checked":""} /> Forzar re-embed (todas)</label>`,O+=`<button class="corpus-btn corpus-btn-promote" id="emb-start-btn" ${o?"disabled":""}>Iniciar</button>`):me?O+='<span class="emb-running-label">Deteniendo al finalizar batch actual...</span>':R&&c&&(O+='<button class="corpus-btn corpus-btn-rollback" id="emb-stop-btn">Detener</button>',O+='<span class="emb-running-label">Embebiendo chunks...</span>'),fe&&c){const U=c.force,Se=(H=c.progress)==null?void 0:H.last_cursor_id,xe=(ae=c.progress)==null?void 0:ae.pct_complete,Te=Se?`Reanudar desde ${typeof xe=="number"?xe.toFixed(1)+"%":"checkpoint"}`:"Reiniciar";U&&(O+='<span class="emb-force-label"><input type="checkbox" checked disabled /> Forzar re-embed (continuación)</span>'),O+=`<button class="corpus-btn corpus-btn-promote" id="emb-resume-btn" ${o?"disabled":""}>${Ue(Te)}</button>`,O+=`<button class="corpus-btn" id="emb-start-btn" ${o?"disabled":""} style="opacity:0.7">Iniciar desde cero</button>`}O+="</div>";const K=c==null?void 0:c.progress,A=(R||o)&&(K==null?void 0:K.total),g=A?K.total:v.total_chunks,oe=A?K.embedded:v.embedded_chunks,he=A?K.pending-K.embedded-(K.failed||0):v.null_embedding_chunks,_=A&&K.failed||0,I=A?K.pct_complete:v.coverage_pct;if(O+=`<div class="emb-stats-grid">
      <div class="emb-stat"><span class="emb-stat-value">${Ke(g)}</span><span class="emb-stat-label">Total</span></div>
      <div class="emb-stat"><span class="emb-stat-value">${Ke(oe)}</span><span class="emb-stat-label">Embebidos</span></div>
      <div class="emb-stat"><span class="emb-stat-value">${Ke(Math.max(0,he))}</span><span class="emb-stat-label">Pendientes</span></div>
      ${_>0?`<div class="emb-stat emb-stat-error"><span class="emb-stat-value">${Ke(_)}</span><span class="emb-stat-label">Fallidos</span></div>`:`<div class="emb-stat"><span class="emb-stat-value">${I.toFixed(1)}%</span><span class="emb-stat-label">Cobertura</span></div>`}
    </div>`,R&&(c!=null&&c.progress)){const U=c.progress;O+='<div class="emb-live-progress">',O+='<div class="emb-progress-bar-wrap" id="emb-progress-mount"></div>',O+=`<div class="emb-rate-line">
        <span>${((ee=U.rate_chunks_per_sec)==null?void 0:ee.toFixed(1))??"-"} chunks/s</span>
        <span>ETA: ${Ft(U.eta_seconds)}</span>
        <span>Elapsed: ${Ft(U.elapsed_seconds)}</span>
        <span>Batch ${Ke(U.current_batch)} / ${Ke(U.total_batches)}</span>
      </div>`,U.failed>0&&(O+=`<p class="emb-failed-notice">${Ke(U.failed)} chunks fallidos (${(U.failed/Math.max(U.pending,1)*100).toFixed(2)}%)</p>`),O+="</div>"}if(c!=null&&c.quality_report){const U=c.quality_report;O+='<div class="emb-quality-report">',O+="<h3>Reporte de calidad</h3>",O+=`<div class="emb-stats-grid">
        <div class="emb-stat"><span class="emb-stat-value">${((Q=U.mean_cosine_similarity)==null?void 0:Q.toFixed(4))??"-"}</span><span class="emb-stat-label">Coseno medio</span></div>
        <div class="emb-stat"><span class="emb-stat-value">${((pe=U.min_cosine_similarity)==null?void 0:pe.toFixed(4))??"-"}</span><span class="emb-stat-label">Min</span></div>
        <div class="emb-stat"><span class="emb-stat-value">${((ye=U.max_cosine_similarity)==null?void 0:ye.toFixed(4))??"-"}</span><span class="emb-stat-label">Max</span></div>
        <div class="emb-stat"><span class="emb-stat-value">${Ke(U.sample_pairs)}</span><span class="emb-stat-label">Pares</span></div>
      </div>`,U.collapsed_warning&&(O+='<p class="emb-anomaly-warning">ANOMALIA: Embeddings colapsados (mean &gt; 0.95)</p>'),U.noise_warning&&(O+='<p class="emb-anomaly-warning">ANOMALIA: Embeddings ruidosos (mean &lt; 0.10)</p>'),!U.collapsed_warning&&!U.noise_warning&&(O+='<p class="emb-quality-ok">Distribución saludable</p>'),O+="</div>"}if((_e=c==null?void 0:c.checks)!=null&&_e.length){O+='<div class="emb-checks">';for(const U of c.checks){const Se=U.ok?'<span class="ops-dot ops-dot-ok">●</span>':'<span class="ops-dot ops-dot-error">●</span>';O+=`<div class="emb-check">${Se} <strong>${Ue(U.label)}</strong>: ${Ue(U.detail)}</div>`}O+="</div>"}if(c!=null&&c.log_tail){const U=c.log_tail.split(`
`).reverse().join(`
`);O+=`<details class="emb-log-accordion" id="emb-log-details" ${k?"open":""}><summary>Log</summary><pre class="emb-log-tail">${Ue(U)}</pre></details>`}if(c!=null&&c.error&&(O+=`<p class="emb-error">${Ue(c.error)}</p>`),n.innerHTML=O,R&&(c!=null&&c.progress)){const U=n.querySelector("#emb-progress-mount");U&&U.appendChild(Jt(c.progress.pct_complete??0,"embedding"))}}function j(){n.addEventListener("click",v=>{const c=v.target;c.id==="emb-start-btn"&&x(),c.id==="emb-stop-btn"&&V(),c.id==="emb-resume-btn"&&S()}),n.addEventListener("change",v=>{const c=v.target;c.id==="emb-force-check"&&(m=c.checked)}),n.addEventListener("toggle",v=>{const c=v.target;c.id==="emb-log-details"&&(k=c.open)},!0)}async function x(){const v=m;o="start",m=!1,N();try{const{response:c,data:$}=await Ye("/api/ops/embedding/start",{force:v});!c.ok||!($!=null&&$.ok)?(t(($==null?void 0:$.error)||`Error ${c.status}`,"error"),o=""):t("Embedding iniciado","success")}catch(c){t(String(c),"error"),o=""}await E()}async function V(){var c;const v=(c=d==null?void 0:d.current_operation)==null?void 0:c.job_id;if(v){o="stop",N();try{await Ye("/api/ops/embedding/stop",{job_id:v}),t("Stop solicitado — se detendrá al finalizar el batch actual","success")}catch($){t(String($),"error"),o=""}}}async function S(){const v=(d==null?void 0:d.current_operation)||(d==null?void 0:d.last_operation);if(v!=null&&v.job_id){o="start",N();try{const{response:c,data:$}=await Ye("/api/ops/embedding/resume",{job_id:v.job_id});!c.ok||!($!=null&&$.ok)?(t(($==null?void 0:$.error)||`Error ${c.status}`,"error"),o=""):t("Embedding reanudado desde checkpoint","success")}catch(c){t(String(c),"error"),o=""}o="",await E()}}async function E(){try{const v=await Ze("/api/ops/embedding-status");d=v;const c=v.current_operation;if(c!=null&&c.progress){const $=c.progress.current_batch;typeof $=="number"&&F($)}o==="stop"&&!v.current_operation&&(o=""),o==="start"&&v.current_operation&&(o=""),v.current_operation||(y=0,C=0,W=[])}catch{}N()}return{bindEvents:j,refresh:E}}const yn=Object.freeze(Object.defineProperty({__proto__:null,createOpsEmbeddingsController:Vt},Symbol.toStringTag,{value:"Module"})),Us=["pending","processing","done"],zs={pending:"Pendiente",processing:"En proceso",done:"Procesado"},Ws={pending:"⏳",processing:"🔄",done:"✅"},Gs=5;function Kt(e){const t=String(e||"").toLowerCase();return t==="done"||t==="completed"||t==="skipped_duplicate"||t==="bounced"?"done":t==="in_progress"||t==="processing"||t==="extracting"||t==="etl"||t==="writing"||t==="gates"||t==="uploading"||t==="running_batch_gates"||t==="needs_retry_batch_gate"||t==="failed"||t==="error"||t==="partial_failed"?"processing":"pending"}function Js(e,t){const n=e.detected_topic||t.corpus||"",d=Zt[n]||St[n]||n||"",o=e.detected_type||e.batch_type||"",m=Rs[o]||o||"",k=o==="normative_base"?"normative":o==="interpretative_guidance"?"interpretative":o==="practica_erp"?"practica":"unknown";let y="";return d&&(y+=`<span class="kanban-pill kanban-pill--topic" title="Tema: ${ce(n)}">${ke(d)}</span>`),m&&(y+=`<span class="kanban-pill kanban-pill--type-${k}" title="Tipo: ${ce(o)}">${ke(m)}</span>`),!d&&!m&&(y+='<span class="kanban-pill kanban-pill--unclassified">Sin clasificar</span>'),y}function Vs(e,t,n){var R;const d=ot(e.status),o=Kt(e.status),m=js(e.bytes,n),k=Number(e.progress||0),y=new Set(t.gate_pending_doc_ids||[]),C=o==="done"&&y.has(e.doc_id);let L;e.status==="bounced"?L='<span class="meta-chip status-bounced">↩ Ya existe en el corpus</span>':o==="done"&&e.derived_from_doc_id&&(e.delta_section_count||0)>0?L=`<span class="meta-chip status-ok">△ ${e.delta_section_count} secciones nuevas</span>`:o==="done"&&(e.status==="done"||e.status==="completed")?(L='<span class="meta-chip status-ok">✓ Documento listo</span>',C&&(L+='<span class="meta-chip status-gate-pending">Pendiente validación final</span>')):L=`<span class="meta-chip status-${d}">${ke(e.status)}</span>`;const W=Js(e,t);let F="";if(e.status==="in_progress"||e.status==="processing"){const X=kt(e.heartbeat_at,e.updated_at,e.stage),me=Fs(e.heartbeat_at,e.updated_at);F=`<div class="kanban-liveness ops-liveness-${X}">${me}</div>`}let f="";e.stage==="gates"&&t.gate_sub_stage&&(f=`<div class="kanban-gate-sub">${Gt(t.gate_sub_stage)}</div>`);let N="";o==="processing"&&k>0&&(N=`<div class="kanban-progress" data-progress="${k}"></div>`);let j="";(R=e.error)!=null&&R.message&&(j=`<div class="kanban-error">${ke(e.error.message)}</div>`);let x="";e.duplicate_of?x=`<div class="kanban-duplicate">Duplicado de: ${ke(e.duplicate_of)}</div>`:e.derived_from_doc_id&&(x=`<div class="kanban-duplicate">Derivado de: ${ke(e.derived_from_doc_id)}</div>`);let V="";if(o==="done"){const X=Hs(e.updated_at);X&&(V=`<div class="kanban-completed-at">Completado: ${ke(X)}</div>`)}let S="";e.duplicate_of&&o!=="done"&&e.status!=="bounced"?S=en(e):o==="pending"&&(e.status==="raw"||e.status==="needs_classification")&&Xs(e)?S=Zs(e,n):o==="pending"&&(e.status==="raw"||e.status==="needs_classification")?S=Ks(e,n,t):o==="processing"&&(e.status==="failed"||e.status==="error"||e.status==="partial_failed")&&(S=tn(e));let E="",v="";(o!=="pending"||e.status==="queued")&&(E=Ys(),v=Qs(e,t,n));const $=e.stage&&e.stage!==e.status&&o==="processing";return`
    <div class="kanban-card kanban-card--${d}" data-doc-id="${ce(e.doc_id)}">
      <div class="kanban-card-head">
        <span class="kanban-card-title" title="${ce(e.doc_id)}">${ke(e.filename||e.doc_id)}</span>
        ${L}
      </div>
      ${e.source_relative_path?`<div class="kanban-card-relpath" title="${ce(e.source_relative_path)}">${ke(nn(e.source_relative_path))}</div>`:""}
      <div class="kanban-card-pills-row">
        ${W}
        <span class="kanban-card-size">${m}</span>
        ${E}
      </div>
      ${v}
      ${$?`<div class="kanban-card-stage">${ke(e.stage)}</div>`:""}
      ${F}
      ${f}
      ${N}
      ${V}
      ${x}
      ${j}
      ${S}
    </div>
  `}function Ks(e,t,n){const d=e.detected_type||e.batch_type||"",o=e.detected_topic||(n==null?void 0:n.corpus)||"",m=k=>k===d?" selected":"";return`
    <div class="kanban-actions kanban-classify-actions">
      <label class="kanban-action-field">
        <span>Tema</span>
        <select data-field="topic" class="kanban-select">
          ${dt(o)}
        </select>
      </label>
      <label class="kanban-action-field">
        <span>Tipo</span>
        <select data-field="type" class="kanban-select">
          <option value="">Seleccionar...</option>
          <option value="normative_base"${m("normative_base")}>${t.t("ops.ingestion.batchType.normative")}</option>
          <option value="interpretative_guidance"${m("interpretative_guidance")}>${t.t("ops.ingestion.batchType.interpretative")}</option>
          <option value="practica_erp"${m("practica_erp")}>${t.t("ops.ingestion.batchType.practical")}</option>
        </select>
      </label>
      <div class="kanban-action-field kanban-action-field--btn">
        <span>&nbsp;</span>
        <button class="btn btn--sm btn--primary kanban-assign-btn" data-action="assign" data-doc-id="${ce(e.doc_id)}">Asignar</button>
      </div>
    </div>
  `}function Xs(e){return!!(e.autogenerar_label&&(e.autogenerar_is_new||e.autogenerar_resolved_topic))}function Zs(e,t){const n=e.detected_type||e.batch_type||"",d=L=>L===n?" selected":"",o=`
    <label class="kanban-action-field">
      <span>Tipo</span>
      <select data-field="type" class="kanban-select">
        <option value="">Seleccionar...</option>
        <option value="normative_base"${d("normative_base")}>${t.t("ops.ingestion.batchType.normative")}</option>
        <option value="interpretative_guidance"${d("interpretative_guidance")}>${t.t("ops.ingestion.batchType.interpretative")}</option>
        <option value="practica_erp"${d("practica_erp")}>${t.t("ops.ingestion.batchType.practical")}</option>
      </select>
    </label>`;if(e.autogenerar_is_new)return`
      <div class="kanban-actions kanban-autogenerar-actions kanban-autogenerar--new">
        <div class="kanban-autogenerar-header">Nuevo tema detectado</div>
        <label class="kanban-action-field">
          <span>Tema</span>
          <input type="text" class="kanban-input" data-field="autogenerar-label"
            value="${ce(e.autogenerar_label||"")}" />
        </label>
        ${e.autogenerar_rationale?`<div class="kanban-autogenerar-rationale">${ke(e.autogenerar_rationale)}</div>`:""}
        ${o}
        <div class="kanban-action-buttons">
          <button class="btn btn--sm btn--primary" data-action="accept-new-topic" data-doc-id="${ce(e.doc_id)}">Aceptar nuevo tema</button>
          <button class="btn btn--sm kanban-ag-fallback-btn" data-action="show-existing-dropdown" data-doc-id="${ce(e.doc_id)}">Asignar existente</button>
        </div>
        <div class="kanban-ag-fallback-panel" hidden>
          <label class="kanban-action-field">
            <span>Tema existente</span>
            <select data-field="topic" class="kanban-select">
              ${dt("")}
            </select>
          </label>
          <div class="kanban-action-field kanban-action-field--btn">
            <span>&nbsp;</span>
            <button class="btn btn--sm btn--primary kanban-assign-btn" data-action="assign" data-doc-id="${ce(e.doc_id)}">Asignar</button>
          </div>
        </div>
      </div>
    `;const m=e.autogenerar_resolved_topic||"",k=St[m]||m,y=e.autogenerar_synonym_confidence??0,C=Math.round(y*100);return`
    <div class="kanban-actions kanban-autogenerar-actions kanban-autogenerar--synonym">
      <div class="kanban-autogenerar-header">Tema sugerido: <strong>${ke(k)}</strong> <span class="kanban-autogenerar-conf">(${C}%)</span></div>
      <div class="kanban-autogenerar-source">Basado en: "${ke(e.autogenerar_label||"")}"</div>
      ${o}
      <div class="kanban-action-buttons">
        <button class="btn btn--sm btn--primary" data-action="accept-synonym" data-doc-id="${ce(e.doc_id)}">Aceptar</button>
        <button class="btn btn--sm kanban-ag-fallback-btn" data-action="show-existing-dropdown" data-doc-id="${ce(e.doc_id)}">Cambiar</button>
      </div>
      <div class="kanban-ag-fallback-panel" hidden>
        <label class="kanban-action-field">
          <span>Tema</span>
          <select data-field="topic" class="kanban-select">
            ${dt(m)}
          </select>
        </label>
        <div class="kanban-action-field kanban-action-field--btn">
          <span>&nbsp;</span>
          <button class="btn btn--sm btn--primary kanban-assign-btn" data-action="assign" data-doc-id="${ce(e.doc_id)}">Asignar</button>
        </div>
      </div>
    </div>
  `}function Ys(){return'<button class="kanban-reclassify-toggle" type="button" title="Cambiar clasificación">✎</button>'}function Qs(e,t,n){const d=e.detected_topic||t.corpus||"",o=e.detected_type||e.batch_type||"",m=(k,y)=>k===y?" selected":"";return`
    <div class="kanban-reclassify-panel" hidden>
      <label class="kanban-action-field">
        <span>Tema</span>
        <select data-field="topic" class="kanban-select">
          ${dt(d)}
        </select>
      </label>
      <label class="kanban-action-field">
        <span>Tipo</span>
        <select data-field="type" class="kanban-select">
          <option value="">Seleccionar...</option>
          <option value="normative_base"${m("normative_base",o)}>${n.t("ops.ingestion.batchType.normative")}</option>
          <option value="interpretative_guidance"${m("interpretative_guidance",o)}>${n.t("ops.ingestion.batchType.interpretative")}</option>
          <option value="practica_erp"${m("practica_erp",o)}>${n.t("ops.ingestion.batchType.practical")}</option>
        </select>
      </label>
      <div class="kanban-action-field kanban-action-field--btn">
        <span>&nbsp;</span>
        <button class="btn btn--sm btn--primary kanban-assign-btn" data-action="assign" data-doc-id="${ce(e.doc_id)}">Asignar</button>
      </div>
    </div>
  `}function en(e){return`
    <div class="kanban-actions">
      <button class="btn btn--sm btn--primary" data-action="replace-dup" data-doc-id="${ce(e.doc_id)}">Reemplazar</button>
      <button class="btn btn--sm" data-action="add-new-dup" data-doc-id="${ce(e.doc_id)}">Agregar nuevo</button>
      <button class="btn btn--sm btn--danger" data-action="discard-dup" data-doc-id="${ce(e.doc_id)}">Descartar</button>
    </div>
  `}function tn(e){return`
    <div class="kanban-actions">
      <button class="btn btn--sm" data-action="retry" data-doc-id="${ce(e.doc_id)}">Reintentar</button>
      <button class="btn btn--sm btn--danger" data-action="discard" data-doc-id="${ce(e.doc_id)}">Descartar</button>
    </div>
  `}const Xt=[["declaracion_renta","Renta"],["iva","IVA"],["laboral","Laboral"],["facturacion_electronica","Facturación"],["estados_financieros_niif","NIIF"],["ica","ICA"],["calendario_obligaciones","Calendarios"],["retencion_fuente","Retención"],["regimen_sancionatorio","Sanciones"],["regimen_cambiario","Régimen Cambiario"],["impuesto_al_patrimonio","Patrimonio"],["informacion_exogena","Exógena"],["proteccion_de_datos","Datos"],["obligaciones_mercantiles","Mercantil"],["obligaciones_profesionales_contador","Obligaciones Contador"],["rut_responsabilidades","RUT"],["gravamen_movimiento_financiero_4x1000","GMF 4×1000"],["beneficiario_final","Beneficiario Final"],["contratacion_estatal","Contratación Estatal"],["reforma_pensional","Reforma Pensional"],["zomac_incentivos","ZOMAC"]];function sn(e){const t=new Set,n=[];for(const[d,o]of Xt)t.add(d),n.push([d,o]);for(const d of e)!d.key||t.has(d.key)||(t.add(d.key),n.push([d.key,d.label||d.key]));return n}let wt=Xt,Zt={...St};function dt(e=""){let t='<option value="">Seleccionar...</option>';for(const[n,d]of wt){const o=n===e?" selected":"";t+=`<option value="${ce(n)}"${o}>${ke(d)}</option>`}return t}function ke(e){const t=document.createElement("span");return t.textContent=e,t.innerHTML}function ce(e){return e.replace(/&/g,"&amp;").replace(/"/g,"&quot;").replace(/'/g,"&#39;").replace(/</g,"&lt;").replace(/>/g,"&gt;")}function nn(e){const t=e.replace(/\/[^/]+$/,"").split("/").filter(Boolean);return t.length<=2?t.join("/")+"/":"…/"+t.slice(-2).join("/")+"/"}function an(e,t,n,d,o){o&&o.length>0&&(wt=sn(o),Zt=Object.fromEntries(wt));const m=[...e.documents||[]].sort((S,E)=>Date.parse(String(E.updated_at||0))-Date.parse(String(S.updated_at||0))),k={pending:[],processing:[],done:[]};for(const S of m){const E=Kt(S.status);k[E].push(S)}k.pending.sort((S,E)=>{const v=S.status==="raw"||S.status==="needs_classification"?0:1,c=E.status==="raw"||E.status==="needs_classification"?0:1;return v!==c?v-c:Date.parse(String(E.updated_at||0))-Date.parse(String(S.updated_at||0))});const y=e.status==="running_batch_gates",C=e.gate_sub_stage||"";let L="";if(y){const S=C?Gt(C):"Preparando...";L=`
      <div class="kanban-validation-banner kanban-validation-banner--running">
        <span class="kanban-validation-spinner"></span>
        <span>Validación final en curso — ${ke(S)}</span>
      </div>`}else e.status==="needs_retry_batch_gate"?L=`
      <div class="kanban-validation-banner kanban-validation-banner--error">
        <span>⚠ Validación final fallida — use Reintentar o Validar lote</span>
      </div>`:e.status==="completed"&&e.wip_sync_status==="skipped"&&(L=`
      <div class="kanban-validation-banner kanban-validation-banner--warn">
        <span>⚠ Ingesta completada solo localmente — WIP Supabase no estaba disponible. Use Operaciones → Sincronizar a WIP.</span>
      </div>`);let W="";const F=k.processing.length;for(const S of Us){const E=k[S],v=S==="processing"?`<span class="kanban-column-count">${F}</span><span class="kanban-column-limit">/ ${Gs}</span>`:`<span class="kanban-column-count">${E.length}</span>`,c=E.length===0?'<div class="kanban-column-empty">Sin documentos</div>':E.map(R=>Vs(R,e,n)).join(""),$=S==="done"?L:"";W+=`
      <div class="kanban-column kanban-column--${S}">
        <div class="kanban-column-header">
          <span class="kanban-column-icon">${Ws[S]}</span>
          <span class="kanban-column-label">${zs[S]}</span>
          ${v}
        </div>
        <div class="kanban-column-cards">
          ${$}
          ${c}
        </div>
      </div>
    `}const f={};t.querySelectorAll(".kanban-column").forEach(S=>{const E=S.classList[1]||"",v=S.querySelector(".kanban-column-cards");E&&v&&(f[E]=v.scrollTop)});const N=[];let j=t;for(;j;)j.scrollTop>0&&N.push([j,j.scrollTop]),j=j.parentElement;const x={};t.querySelectorAll(".kanban-reclassify-panel").forEach(S=>{var E,v;if(!S.hasAttribute("hidden")){const c=S.closest("[data-doc-id]"),$=(c==null?void 0:c.dataset.docId)||"";if($&&!(d!=null&&d.has($))){const R=((E=S.querySelector("[data-field='topic']"))==null?void 0:E.value)||"",X=((v=S.querySelector("[data-field='type']"))==null?void 0:v.value)||"";x[$]={topic:R,type:X}}}});const V={};t.querySelectorAll(".kanban-classify-actions").forEach(S=>{var c,$;const E=S.closest("[data-doc-id]"),v=(E==null?void 0:E.dataset.docId)||"";if(v){const R=((c=S.querySelector("[data-field='topic']"))==null?void 0:c.value)||"",X=(($=S.querySelector("[data-field='type']"))==null?void 0:$.value)||"";(R||X)&&(V[v]={topic:R,type:X})}}),t.innerHTML=W;for(const[S,E]of N)S.scrollTop=E;t.querySelectorAll(".kanban-column").forEach(S=>{const E=S.classList[1]||"",v=S.querySelector(".kanban-column-cards");E&&f[E]&&v&&(v.scrollTop=f[E])});for(const[S,E]of Object.entries(x)){const v=t.querySelector(`[data-doc-id="${CSS.escape(S)}"]`);if(!v)continue;const c=v.querySelector(".kanban-reclassify-toggle"),$=v.querySelector(".kanban-reclassify-panel");if(c&&$){$.removeAttribute("hidden"),c.textContent="✖";const R=$.querySelector("[data-field='topic']"),X=$.querySelector("[data-field='type']");R&&E.topic&&(R.value=E.topic),X&&E.type&&(X.value=E.type)}}for(const[S,E]of Object.entries(V)){const v=t.querySelector(`[data-doc-id="${CSS.escape(S)}"]`);if(!v)continue;const c=v.querySelector(".kanban-classify-actions");if(!c)continue;const $=c.querySelector("[data-field='topic']"),R=c.querySelector("[data-field='type']");$&&E.topic&&($.value=E.topic),R&&E.type&&(R.value=E.type)}t.querySelectorAll(".kanban-progress").forEach(S=>{var $,R;const E=Number(S.dataset.progress||0),v=((R=($=S.closest(".kanban-card"))==null?void 0:$.querySelector(".kanban-card-stage"))==null?void 0:R.textContent)||void 0,c=Jt(E,v);S.replaceWith(c)}),t.querySelectorAll(".kanban-reclassify-toggle").forEach(S=>{S.addEventListener("click",()=>{const E=S.closest(".kanban-card"),v=E==null?void 0:E.querySelector(".kanban-reclassify-panel");if(!v)return;v.hasAttribute("hidden")?(v.removeAttribute("hidden"),S.textContent="✖"):(v.setAttribute("hidden",""),S.textContent="✎")})})}async function we(e,t){const n=await fetch(e,t);let d=null;try{d=await n.json()}catch{d=null}if(!n.ok){const o=d&&typeof d=="object"&&"error"in d?String(d.error||n.statusText):n.statusText;throw new pt(o,n.status,d)}return d}async function _t(e,t){const{response:n,data:d}=await Ye(e,t);if(!n.ok){const o=d&&typeof d=="object"&&"error"in d?String(d.error||n.statusText):n.statusText;throw new pt(o,n.status,d)}return d}function on({i18n:e,stateController:t,dom:n,withThinkingWheel:d,setFlash:o}){const{ingestionCorpusSelect:m,ingestionBatchTypeSelect:k,ingestionDropzone:y,ingestionFileInput:C,ingestionFolderInput:L,ingestionSelectFilesBtn:W,ingestionSelectFolderBtn:F,ingestionUploadProgress:f,ingestionPendingFiles:N,ingestionOverview:j,ingestionRefreshBtn:x,ingestionCreateSessionBtn:V,ingestionUploadBtn:S,ingestionProcessBtn:E,ingestionAutoProcessBtn:v,ingestionValidateBatchBtn:c,ingestionRetryBtn:$,ingestionDeleteSessionBtn:R,ingestionSessionMeta:X,ingestionSessionsList:me,selectedSessionMeta:fe,ingestionLastError:O,ingestionLastErrorMessage:le,ingestionLastErrorGuidance:Fe,ingestionLastErrorNext:q,ingestionKanban:D,ingestionLogAccordion:w,ingestionLogBody:b,ingestionLogCopyBtn:K,ingestionAutoStatus:A}=n,{state:g}=t,oe=ys(e);let he=[];function _(s){const l=`[${new Date().toISOString().slice(11,23)}] ${s}`;he.push(l),console.log(`[folder-ingest] ${s}`),w.hidden=!1,b.hidden=!1,b.textContent=he.join(`
`);const u=document.getElementById("ingestion-log-toggle");if(u){u.setAttribute("aria-expanded","true");const i=u.querySelector(".ops-log-accordion-marker");i&&(i.textContent="▾")}}function I(){he=[],Z()}function Z(){const{ingestionBounceLog:s,ingestionBounceBody:a}=n;s&&(s.hidden=!0,s.open=!1),a&&(a.textContent="")}let H=!1,ae=null;const ee=150;function Q(s){const a=Me(s);return`${s.name}|${s.size}|${s.lastModified??0}|${a}`}function pe(s){if(s.length===0)return;const a=new Set(g.intake.map(u=>Q(u.file))),l=[];for(const u of s){const i=Q(u);a.has(i)||(a.add(i),l.push({file:u,relativePath:Me(u),contentHash:null,verdict:"pending",preflightEntry:null}))}l.length!==0&&(t.setIntake([...g.intake,...l]),g.reviewPlan&&t.setReviewPlan({...g.reviewPlan,stalePartial:!0}),H=!1,ye(),re())}function ye(){ae&&clearTimeout(ae);const s=t.bumpPreflightRunId();ae=setTimeout(()=>{ae=null,_e(s)},ee)}async function _e(s){if(s!==g.preflightRunId||g.intake.length===0)return;const a=g.intake.filter(l=>l.contentHash===null);try{if(a.length>0&&(await U(a),s!==g.preflightRunId))return;const l=await Se();if(s!==g.preflightRunId)return;if(!l){H=!0,re();return}xe(l),H=!1,re()}catch(l){if(s!==g.preflightRunId)return;console.error("[intake] preflight failed:",l),H=!0,re()}}async function U(s){t.setPreflightScanProgress({total:s.length,hashed:0,scanning:!0}),Lt();for(let a=0;a<s.length;a++){const l=s[a];try{const u=await l.file.arrayBuffer(),i=await crypto.subtle.digest("SHA-256",u),p=Array.from(new Uint8Array(i));l.contentHash=p.map(r=>r.toString(16).padStart(2,"0")).join("")}catch(u){console.warn(`[intake] hash failed for ${l.file.name}:`,u),l.verdict="unreadable",l.contentHash=""}t.setPreflightScanProgress({total:s.length,hashed:a+1,scanning:!0}),Lt()}t.setPreflightScanProgress(null)}async function Se(){const s=g.intake.filter(a=>a.contentHash&&a.verdict!=="unreadable").map(a=>({filename:a.file.name,relative_path:a.relativePath||a.file.name,size:a.file.size,content_hash:a.contentHash}));if(s.length===0)return{artifacts:[],duplicates:[],revisions:[],new_files:[],scanned:0,elapsed_ms:0};try{return await fs(s,g.selectedCorpus)}catch(a){return console.error("[intake] /api/ingestion/preflight failed:",a),null}}function xe(s){const a=new Map,l=(r,h)=>{for(const P of h){const T=P.relative_path||P.filename;a.set(T,{verdict:r,preflightEntry:P})}};l("new",s.new_files),l("revision",s.revisions),l("duplicate",s.duplicates),l("artifact",s.artifacts);const u=g.intake.map(r=>{if(r.verdict==="unreadable")return r;const h=r.relativePath||r.file.name,P=a.get(h);return P?{...r,verdict:P.verdict,preflightEntry:P.preflightEntry}:{...r,verdict:"pending"}}),i=u.filter(r=>r.verdict==="new"||r.verdict==="revision"),p=u.filter(r=>r.verdict==="duplicate"||r.verdict==="artifact"||r.verdict==="unreadable");t.setIntake(u),t.setReviewPlan({willIngest:i,bounced:p,scanned:s.scanned,elapsedMs:s.elapsed_ms,stalePartial:!1}),t.setPendingFiles(i.map(r=>r.file))}function Te(s){const a=l=>Q(l.file)!==Q(s.file);if(t.setIntake(g.intake.filter(a)),g.reviewPlan){const l=g.reviewPlan.willIngest.filter(a);t.setReviewPlan({...g.reviewPlan,willIngest:l}),t.setPendingFiles(l.map(u=>u.file))}else t.setPendingFiles(g.pendingFiles.filter(l=>Q(l)!==Q(s.file)));re()}function qe(){if(!g.reviewPlan)return;const s=new Set(g.reviewPlan.willIngest.map(l=>Q(l.file))),a=g.intake.filter(l=>!s.has(Q(l.file)));t.setIntake(a),t.setReviewPlan({...g.reviewPlan,willIngest:[]}),t.setPendingFiles([]),re()}function Pe(){ae&&(clearTimeout(ae),ae=null),t.bumpPreflightRunId(),t.setIntake([]),t.setReviewPlan(null),t.setPendingFiles([]),t.setPreflightScanProgress(null),H=!1,g.folderRelativePaths.clear()}async function Ie(){const s=g.reviewPlan;if(s&&!s.stalePartial&&s.willIngest.length!==0&&!H){o(),t.setMutating(!0),ge();try{await bs(),Pe(),L.value="",C.value=""}catch(a){t.setFolderUploadProgress(null),$e(),o(de(a),"error"),g.selectedSessionId&&Ve({sessionId:g.selectedSessionId,showWheel:!1,reportError:!1})}finally{t.setMutating(!1),ge()}}}const Le=new Set;function He(){const s=g.selectedCorpus;m.innerHTML="";const a=document.createElement("option");a.value="autogenerar",a.textContent="AUTOGENERAR",a.selected=s==="autogenerar",m.appendChild(a),[...g.corpora].sort((l,u)=>l.label.localeCompare(u.label,"es")).forEach(l=>{var r;const u=document.createElement("option");u.value=l.key;const i=((r=l.attention)==null?void 0:r.length)||0;let p=l.active?l.label:`${l.label} (${e.t("ops.ingestion.corpusInactiveOption")})`;i>0&&(p+=` ⚠ ${i}`),u.textContent=p,u.selected=l.key===s,m.appendChild(u)})}function ue(){return g.selectedCorpus!=="autogenerar"?g.selectedCorpus:"autogenerar"}const be=new Set([".pdf",".md",".txt",".docx"]),Oe=[".","__MACOSX"],Ee=3,De="lia_folder_pending_";function ie(s){return s.filter(a=>{const l=a.name;if(Oe.some(p=>l.startsWith(p)))return!1;const u=l.lastIndexOf("."),i=u>=0?l.slice(u).toLowerCase():"";return be.has(i)})}async function We(s){var i,p;const a=[],l=[];for(let r=0;r<s.items.length;r++){const h=(p=(i=s.items[r]).webkitGetAsEntry)==null?void 0:p.call(i);h&&l.push(h)}if(!l.some(r=>r.isDirectory))return[];async function u(r){if(r.isFile){const h=await new Promise((P,T)=>{r.file(P,T)});g.folderRelativePaths.set(h,r.fullPath.replace(/^\//,"")),a.push(h)}else if(r.isDirectory){const h=r.createReader();let P;do{P=await new Promise((T,G)=>{h.readEntries(T,G)});for(const T of P)await u(T)}while(P.length>0)}}for(const r of l)await u(r);return a}function Me(s){return s.webkitRelativePath||g.folderRelativePaths.get(s)||""}async function Ae(s,a=""){const l=[];for await(const[u,i]of s.entries()){const p=a?`${a}/${u}`:u;if(i.kind==="file"){const r=await i.getFile();g.folderRelativePaths.set(r,p),l.push(r)}else if(i.kind==="directory"){const r=await Ae(i,p);l.push(...r)}}return l}async function Be(s,a,l,u=Ee){let i=0,p=0,r=0,h=0;const P=[];return new Promise(T=>{function G(){for(;r<u&&h<a.length;){const J=a[h++];r++,ps(s,J,l).then(()=>{i++}).catch(B=>{p++;const z=B instanceof Error?B.message:String(B);P.push({filename:J.name,error:z}),console.error(`[folder-ingest] Upload failed: ${J.name}`,B)}).finally(()=>{r--,t.setFolderUploadProgress({total:a.length,uploaded:i,failed:p,uploading:h<a.length||r>0}),$e(),h<a.length||r>0?G():T({uploaded:i,failed:p,errors:P})})}}t.setFolderUploadProgress({total:a.length,uploaded:0,failed:0,uploading:!0}),$e(),G()})}function $e(){const s=g.folderUploadProgress;if(!s||!s.uploading){f.hidden=!0,f.innerHTML="";return}const a=s.uploaded+s.failed,l=s.total>0?Math.round(a/s.total*100):0,u=Math.max(0,Math.min(Ee,s.total-a));f.hidden=!1,f.innerHTML=`
      <div class="ops-upload-progress-header">
        <span>${e.t("ops.ingestion.uploadProgress",{current:a,total:s.total})}</span>
        <span>${l}%</span>
      </div>
      <div class="ops-upload-progress-bar">
        <span class="ops-upload-progress-fill" style="width:${l}%"></span>
      </div>
      <div class="ops-upload-progress-detail">
        ${e.t("ops.ingestion.uploadProgressDetail",{uploaded:s.uploaded,failed:s.failed,inflight:u})}
      </div>
    `}function je(s){if(g.pendingFiles.length!==0&&Me(g.pendingFiles[0])!=="")try{const a=g.pendingFiles.map(l=>({name:l.name,relativePath:Me(l),size:l.size}));localStorage.setItem(De+s,JSON.stringify(a))}catch{}}function Ge(s){try{localStorage.removeItem(De+s)}catch{}}function et(s){try{const a=localStorage.getItem(De+s);if(!a)return 0;const l=JSON.parse(a);if(!Array.isArray(l))return 0;const u=g.sessions.find(p=>p.session_id===s);if(!u)return l.length;const i=new Set((u.documents||[]).map(p=>p.filename));return l.filter(p=>!i.has(p.name)).length}catch{return 0}}function gt(s){return s<1024?`${s} B`:s<1024*1024?`${(s/1024).toFixed(1)} KB`:`${(s/(1024*1024)).toFixed(1)} MB`}function ss(s){var l;const a=((l=s.preflightEntry)==null?void 0:l.existing_doc_id)||"";switch(s.verdict){case"pending":return e.t("ops.ingestion.verdict.pending");case"new":return e.t("ops.ingestion.verdict.new");case"revision":return a?e.t("ops.ingestion.verdict.revisionOf",{docId:a}):e.t("ops.ingestion.verdict.revision");case"duplicate":return a?e.t("ops.ingestion.verdict.duplicateOf",{docId:a}):e.t("ops.ingestion.verdict.duplicate");case"artifact":return e.t("ops.ingestion.verdict.artifact");case"unreadable":return e.t("ops.ingestion.verdict.unreadable")}}function ns(s){const a=document.createElement("span");return a.className=`ops-verdict-pill ops-verdict-pill--${s.verdict}`,a.textContent=ss(s),a}function as(s,a,l){var P;const u=document.createElement("div");u.className="ops-intake-row",a.verdict==="pending"&&u.classList.add("ops-intake-row--pending"),l.readonly&&u.classList.add("ops-intake-row--readonly");const i=document.createElement("span");i.className="ops-intake-row__icon",i.textContent="📄";const p=document.createElement("span");p.className="ops-intake-row__name",p.textContent=a.relativePath||a.file.name,p.title=a.relativePath||a.file.name;const r=document.createElement("span");r.className="ops-intake-row__size",r.textContent=gt(a.file.size);const h=ns(a);if(u.append(i,p,r,h),l.showReason&&((P=a.preflightEntry)!=null&&P.reason)){const T=document.createElement("span");T.className="ops-intake-row__reason",T.textContent=a.preflightEntry.reason,T.title=a.preflightEntry.reason,u.appendChild(T)}if(l.removable){const T=document.createElement("button");T.type="button",T.className="ops-intake-row__remove",T.textContent="✕",T.title=e.t("ops.ingestion.willIngest.cancelAll"),T.addEventListener("click",G=>{G.stopPropagation(),Te(a)}),u.appendChild(T)}s.appendChild(u)}function mt(s,a,l,u,i,p){const r=document.createElement("section");r.className=`ops-intake-panel ops-intake-panel--${s}`;const h=document.createElement("header");h.className="ops-intake-panel__header";const P=document.createElement("span");P.className="ops-intake-panel__title",P.textContent=e.t(a),h.appendChild(P);const T=document.createElement("span");if(T.className="ops-intake-panel__count",T.textContent=e.t(l,{count:u}),h.appendChild(T),p.readonly){const J=document.createElement("span");J.className="ops-intake-panel__readonly",J.textContent=e.t("ops.ingestion.bounced.readonly"),h.appendChild(J)}if(p.cancelAllAction){const J=document.createElement("button");J.type="button",J.className="ops-intake-panel__action",J.textContent=e.t("ops.ingestion.willIngest.cancelAll"),J.addEventListener("click",B=>{B.stopPropagation(),p.cancelAllAction()}),h.appendChild(J)}r.appendChild(h);const G=document.createElement("div");return G.className="ops-intake-panel__body",i.forEach(J=>as(G,J,p)),r.appendChild(G),r}function os(){var u,i;if((u=y.querySelector(".ops-intake-windows"))==null||u.remove(),(i=y.querySelector(".dropzone-file-list"))==null||i.remove(),g.intake.length===0){N.textContent=e.t("ops.ingestion.pendingNone"),N.hidden=!0,y.classList.remove("has-files");return}N.hidden=!0,y.classList.add("has-files");const s=document.createElement("div");s.className="ops-intake-windows";const a=is();a&&s.appendChild(a),s.appendChild(mt("intake","ops.ingestion.intake.title","ops.ingestion.intake.count",g.intake.length,g.intake,{removable:!1,readonly:!1,showReason:!1}));const l=g.reviewPlan;l&&(s.appendChild(mt("will-ingest","ops.ingestion.willIngest.title","ops.ingestion.willIngest.count",l.willIngest.length,l.willIngest,{removable:!0,readonly:!1,showReason:!1,cancelAllAction:l.willIngest.length>0?()=>qe():void 0})),l.bounced.length>0&&s.appendChild(mt("bounced","ops.ingestion.bounced.title","ops.ingestion.bounced.count",l.bounced.length,l.bounced,{removable:!1,readonly:!0,showReason:!0}))),y.appendChild(s)}function is(){var r;const s=((r=g.reviewPlan)==null?void 0:r.stalePartial)===!0,a=g.intake.some(h=>h.verdict==="pending"),l=H;if(!s&&!a&&!l)return null;const u=document.createElement("div");if(u.className="ops-intake-banner",l){u.classList.add("ops-intake-banner--error");const h=document.createElement("span");h.className="ops-intake-banner__text",h.textContent=e.t("ops.ingestion.intake.failed");const P=document.createElement("button");return P.type="button",P.className="ops-intake-banner__retry",P.textContent=e.t("ops.ingestion.intake.retry"),P.addEventListener("click",T=>{T.stopPropagation(),H=!1,ye(),re()}),u.append(h,P),u}const i=document.createElement("span");i.className="ops-intake-banner__spinner",u.appendChild(i);const p=document.createElement("span");return p.className="ops-intake-banner__text",s?(u.classList.add("ops-intake-banner--stale"),p.textContent=e.t("ops.ingestion.intake.stale")):(u.classList.add("ops-intake-banner--verifying"),p.textContent=e.t("ops.ingestion.intake.verifying")),u.appendChild(p),u}function ge(){var ne,Ce,ve,at,te;const s=t.selectedCorpusConfig(),a=g.selectedSession,l=g.selectedCorpus==="autogenerar"?g.corpora.some(Ne=>Ne.active):!!(s!=null&&s.active),u=lt(String((a==null?void 0:a.status)||""));k.value=k.value||"autogenerar";const i=((ne=g.folderUploadProgress)==null?void 0:ne.uploading)??!1,p=g.reviewPlan,r=(p==null?void 0:p.willIngest.length)??0,h=(p==null?void 0:p.stalePartial)===!0,P=H===!0,T=!!p&&r>0&&!h&&!P;V.disabled=g.mutating||!l,W.disabled=g.mutating||!l||i,F.disabled=g.mutating||!l||i||u,S.disabled=g.mutating||!l||!T||i,p?r===0?S.textContent=e.t("ops.ingestion.approveNone"):S.textContent=e.t("ops.ingestion.approveCount",{count:r}):S.textContent=e.t("ops.ingestion.approve"),E.disabled=g.mutating||!l||!a||u,v.disabled=g.mutating||!l||i||!a||u,v.textContent=`▶ ${e.t("ops.ingestion.actions.autoProcess")}`;const G=Number(((Ce=a==null?void 0:a.batch_summary)==null?void 0:Ce.done)||0),J=Number(((ve=a==null?void 0:a.batch_summary)==null?void 0:ve.queued)||0)+Number(((at=a==null?void 0:a.batch_summary)==null?void 0:at.processing)||0),B=Number(((te=a==null?void 0:a.batch_summary)==null?void 0:te.pending_batch_gate)||0),z=G>=1&&(J>=1||B>=1);if(c.disabled=g.mutating||!l||!a||u||!z,$.disabled=g.mutating||!l||!a||u,R.disabled=g.mutating||!a,x.disabled=g.mutating,m.disabled=g.mutating||g.corpora.length===0,C.disabled=g.mutating||!l,!l){j.textContent=e.t("ops.ingestion.corpusInactive");return}j.textContent=e.t("ops.ingestion.overview",{active:g.corpora.filter(Ne=>Ne.active).length,total:g.corpora.length,corpus:g.selectedCorpus==="autogenerar"?"AUTOGENERAR":(s==null?void 0:s.label)||g.selectedCorpus,session:(a==null?void 0:a.session_id)||e.t("ops.ingestion.noSession")})}function rs(){if(me.innerHTML="",X.textContent=g.selectedSession?`${g.selectedSession.session_id} · ${g.selectedSession.status}`:e.t("ops.ingestion.selectedEmpty"),g.sessions.length===0){const s=document.createElement("li");s.className="ops-empty",s.textContent=e.t("ops.ingestion.sessionsEmpty"),me.appendChild(s);return}g.sessions.forEach(s=>{var ve,at;const a=document.createElement("li"),l=s.status==="partial_failed",u=document.createElement("button");u.type="button",u.className=`ops-session-item${s.session_id===g.selectedSessionId?" is-active":""}${l?" has-retry-action":""}`,u.dataset.sessionId=s.session_id;const i=document.createElement("div");i.className="ops-session-item-head";const p=document.createElement("div");p.className="ops-session-id",p.textContent=s.session_id;const r=document.createElement("span");r.className=`meta-chip status-${ot(s.status)}`,r.textContent=s.status,i.append(p,r);const h=document.createElement("div");h.className="ops-session-pills";const P=((ve=g.corpora.find(te=>te.key===s.corpus))==null?void 0:ve.label)||s.corpus,T=document.createElement("span");T.className="meta-chip ops-pill-corpus",T.textContent=P,h.appendChild(T);const G=s.documents||[];[...new Set(G.map(te=>te.batch_type).filter(Boolean))].forEach(te=>{const Ne=document.createElement("span");Ne.className="meta-chip ops-pill-batch",Ne.textContent=Bs(te,e),h.appendChild(Ne)});const B=G.map(te=>te.filename).filter(Boolean);let z=null;if(B.length>0){z=document.createElement("div"),z.className="ops-session-files";const te=B.slice(0,3),Ne=B.length-te.length;z.textContent=te.join(", ")+(Ne>0?` +${Ne}`:"")}const ne=document.createElement("div");ne.className="ops-session-summary",ne.textContent=jt(s.batch_summary,e);const Ce=document.createElement("div");if(Ce.className="ops-session-summary",Ce.textContent=s.updated_at?e.formatDateTime(s.updated_at,{dateStyle:"short",timeStyle:"short",timeZone:"America/Bogota"}):"-",u.appendChild(i),u.appendChild(h),z&&u.appendChild(z),u.appendChild(ne),u.appendChild(Ce),(at=s.last_error)!=null&&at.code){const te=document.createElement("div");te.className="ops-session-summary status-error",te.textContent=s.last_error.code,u.appendChild(te)}if(u.addEventListener("click",async()=>{t.setSelectedSession(s),re();try{await Ve({sessionId:s.session_id,showWheel:!0})}catch{}}),a.appendChild(u),l){const te=document.createElement("button");te.type="button",te.className="ops-session-retry-inline",te.textContent=e.t("ops.ingestion.actions.retry"),te.disabled=g.mutating,te.addEventListener("click",async Ne=>{Ne.stopPropagation(),te.disabled=!0,t.setMutating(!0),ge();try{await d(async()=>xt(s.session_id)),await Je({showWheel:!1,reportError:!0,focusSessionId:s.session_id}),o(e.t("ops.ingestion.flash.retryStarted",{id:s.session_id}),"success")}catch(vs){o(de(vs),"error")}finally{t.setMutating(!1),ge()}}),a.appendChild(te)}me.appendChild(a)})}function cs(s){const a=[],l=()=>new Date().toISOString();if(a.push(e.t("ops.ingestion.log.sessionHeader",{id:s.session_id})),a.push(`Corpus:     ${s.corpus||"-"}`),a.push(`Status:     ${s.status}`),a.push(`Created:    ${s.created_at||"-"}`),a.push(`Updated:    ${s.updated_at||"-"}`),a.push(`Heartbeat:  ${s.heartbeat_at??"-"}`),s.auto_processing&&a.push(`Auto-proc:  ${s.auto_processing}`),s.gate_sub_stage&&a.push(`Gate-stage: ${s.gate_sub_stage}`),s.wip_sync_status&&a.push(`WIP-sync:   ${s.wip_sync_status}`),s.batch_summary){const i=s.batch_summary,p=(s.documents||[]).filter(h=>h.status==="raw"||h.status==="needs_classification").length,r=(s.documents||[]).filter(h=>h.status==="pending_dedup").length;a.push(""),a.push("── Resumen del lote ──"),a.push(`  Total: ${i.total}  Queued: ${i.queued}  Processing: ${i.processing}  Done: ${i.done}  Failed: ${i.failed}  Duplicados: ${i.skipped_duplicate}  Bounced: ${i.bounced}`),p>0&&a.push(`  Raw (sin clasificar): ${p}`),r>0&&a.push(`  Pending dedup: ${r}`)}s.last_error&&(a.push(""),a.push("── Error de sesión ──"),a.push(`  Código:    ${s.last_error.code||"-"}`),a.push(`  Mensaje:   ${s.last_error.message||"-"}`),a.push(`  Guía:      ${s.last_error.guidance||"-"}`),a.push(`  Siguiente: ${s.last_error.next_step||"-"}`));const u=s.documents||[];if(u.length===0)a.push(""),a.push(e.t("ops.ingestion.log.noDocuments"));else{a.push(""),a.push(`── Documentos (${u.length}) ──`);const i={failed:0,processing:1,in_progress:1,queued:2,raw:2,done:3,completed:3,bounced:4,skipped_duplicate:5},p=[...u].sort((r,h)=>(i[r.status]??3)-(i[h.status]??3));for(const r of p)a.push(""),a.push(`  ┌─ ${r.filename} (${r.doc_id})`),a.push(`  │  Status:   ${r.status}  │  Stage: ${r.stage||"-"}  │  Progress: ${r.progress??0}%`),a.push(`  │  Bytes:    ${r.bytes??"-"}  │  Batch: ${r.batch_type||"-"}`),r.source_relative_path&&a.push(`  │  Path:     ${r.source_relative_path}`),(r.detected_topic||r.detected_type)&&(a.push(`  │  Topic:    ${r.detected_topic||"-"}  │  Type: ${r.detected_type||"-"}  │  Confidence: ${r.combined_confidence??"-"}`),r.classification_source&&a.push(`  │  Classifier: ${r.classification_source}`)),r.chunk_count!=null&&a.push(`  │  Chunks:   ${r.chunk_count}  │  Elapsed: ${r.elapsed_ms??"-"}ms`),r.dedup_match_type&&a.push(`  │  Dedup:    ${r.dedup_match_type}  │  Match: ${r.dedup_match_doc_id||"-"}`),r.replaced_doc_id&&a.push(`  │  Replaced: ${r.replaced_doc_id}`),r.error&&(a.push("  │  ❌ ERROR"),a.push(`  │    Código:    ${r.error.code||"-"}`),a.push(`  │    Mensaje:   ${r.error.message||"-"}`),a.push(`  │    Guía:      ${r.error.guidance||"-"}`),a.push(`  │    Siguiente: ${r.error.next_step||"-"}`)),a.push(`  │  Created: ${r.created_at||"-"}  │  Updated: ${r.updated_at||"-"}`),a.push("  └─")}return a.push(""),a.push(`Log generado: ${l()}`),a.join(`
`)}function Pt(){if(he.length>0)return;const s=g.selectedSession;if(!s){w.hidden=!0,b.textContent="";return}w.hidden=!1,b.textContent=cs(s)}function ls(){const s=g.selectedSession;if(!s){fe.textContent=e.t("ops.ingestion.selectedEmpty"),O.hidden=!0,he.length===0&&(w.hidden=!0),D.innerHTML="";return}const a=et(s.session_id),l=a>0?` · ${e.t("ops.ingestion.folderResumePending",{count:a})}`:"";if(fe.textContent=`${s.session_id} · ${jt(s.batch_summary,e)}${l}`,s.last_error?(O.hidden=!1,le.textContent=s.last_error.message||s.last_error.code||"-",Fe.textContent=s.last_error.guidance||"",q.textContent=`${e.t("ops.ingestion.lastErrorNext")}: ${s.last_error.next_step||"-"}`):O.hidden=!0,(s.documents||[]).length===0){D.innerHTML=`<p class="ops-empty">${e.t("ops.ingestion.documentsEmpty")}</p>`,D.style.minHeight="0",Pt();return}D.style.minHeight="",an(s,D,e,Le,g.corpora),Le.clear(),Pt()}function re(){He(),os(),ge(),rs(),ls()}async function Et(){const s=await Ze("/api/corpora"),a=Array.isArray(s.corpora)?s.corpora:[];t.setCorpora(a);const l=new Set(a.map(u=>u.key));l.add("autogenerar"),l.has(g.selectedCorpus)||t.setSelectedCorpus("autogenerar")}async function ds(){const s=await Ze("/api/ingestion/sessions?limit=20");return Array.isArray(s.sessions)?s.sessions:[]}async function tt(s){const a=await Ze(`/api/ingestion/sessions/${encodeURIComponent(s)}`);if(!a.session)throw new Error("missing_session");return a.session}async function bt(s){const a=await _t("/api/ingestion/sessions",{corpus:s});if(!a.session)throw new Error("missing_session");return a.session}async function ps(s,a,l){const u=m.value==="autogenerar"?"":m.value,i={"Content-Type":"application/octet-stream","X-Upload-Filename":a.name,"X-Upload-Mime":a.type||"application/octet-stream","X-Upload-Batch-Type":l};u&&(i["X-Upload-Topic"]=u);const p=Me(a);p&&(i["X-Upload-Relative-Path"]=p),console.log(`[upload] ${a.name} (${a.size}B) → session=${s} batch=${l}`);const r=await fetch(`/api/ingestion/sessions/${encodeURIComponent(s)}/files`,{method:"POST",headers:i,body:a}),h=await r.text();let P;try{P=JSON.parse(h)}catch{throw console.error(`[upload] ${a.name} — response not JSON (${r.status}):`,h.slice(0,300)),new Error(`Upload response not JSON: ${r.status} ${h.slice(0,100)}`)}if(!r.ok){const T=P.error||r.statusText;throw console.error(`[upload] ${a.name} — HTTP ${r.status}:`,T),new pt(T,r.status,P)}if(!P.document)throw console.error(`[upload] ${a.name} — no document in response:`,P),new Error("missing_document");return console.log(`[upload] ${a.name} → OK doc_id=${P.document.doc_id} status=${P.document.status}`),P.document}async function it(s){return we(`/api/ingestion/sessions/${encodeURIComponent(s)}/process`,{method:"POST"})}async function Ct(s){return we(`/api/ingestion/sessions/${encodeURIComponent(s)}/validate-batch`,{method:"POST"})}async function xt(s){return we(`/api/ingestion/sessions/${encodeURIComponent(s)}/retry`,{method:"POST"})}async function us(s,a=!1){const l=a?"?force=true":"";return we(`/api/ingestion/sessions/${encodeURIComponent(s)}${l}`,{method:"DELETE"})}async function Je({showWheel:s=!0,reportError:a=!0,focusSessionId:l=""}={}){const u=async()=>{await Et(),re();let i=await ds();const p=l||g.selectedSessionId;if(p&&!i.some(r=>r.session_id===p))try{i=[await tt(p),...i.filter(h=>h.session_id!==p)]}catch{p===g.selectedSessionId&&t.setSelectedSession(null)}t.setSessions(i.sort((r,h)=>Date.parse(String(h.updated_at||0))-Date.parse(String(r.updated_at||0)))),t.syncSelectedSession(),re()};try{s?await d(u):await u()}catch(i){throw a&&o(de(i),"error"),re(),i}}async function Ve({sessionId:s,showWheel:a=!1,reportError:l=!0}){const u=async()=>{const i=await tt(s);t.upsertSession(i),re()};try{a?await d(u):await u()}catch(i){throw l&&o(de(i),"error"),i}}async function gs(){var a,l,u,i;const s=ue();if(console.log(`[folder-ingest] ensureSelectedSession: effectiveCorpus="${s}", selectedSession=${((a=g.selectedSession)==null?void 0:a.session_id)||"null"} (status=${((l=g.selectedSession)==null?void 0:l.status)||"null"}, corpus=${((u=g.selectedSession)==null?void 0:u.corpus)||"null"})`),g.selectedSession&&!Bt(g.selectedSession)&&g.selectedSession.status!=="completed"&&(g.selectedSession.corpus===s||s==="autogenerar"))return console.log(`[folder-ingest] Reusing session ${g.selectedSession.session_id}`),g.selectedSession;_(`Creando sesión con corpus="${s}"...`);try{const p=await bt(s);return _(`Sesión creada: ${p.session_id} (corpus=${p.corpus})`),t.upsertSession(p),p}catch(p){if(_(`Creación falló para corpus="${s}": ${p instanceof Error?p.message:String(p)}`),s==="autogenerar"){const r=((i=g.corpora.find(P=>P.active))==null?void 0:i.key)||"declaracion_renta";_(`Reintentando con corpus="${r}"...`);const h=await bt(r);return _(`Sesión fallback: ${h.session_id} (corpus=${h.corpus})`),t.upsertSession(h),h}throw p}}const ms=4e3;let nt=null,ft="";function Qe(){nt&&(clearTimeout(nt),nt=null),ft="",A.hidden=!0,A.classList.remove("is-running")}function rt(s){return(s.documents||[]).filter(a=>a.status==="raw"||a.status==="needs_classification").length}function ht(s){const a=s.batch_summary,l=rt(s),u=Math.max(0,Number(a.queued??0)-l),i=Number(a.processing??0),p=Number(a.done??0),r=Number(a.failed??0),h=Number(a.bounced??0),P=u+i;A.hidden=!1;const T=h>0?` · ${h} rebotados`:"";P>0||l>0?(A.classList.add("is-running"),A.textContent=e.t("ops.ingestion.auto.running",{queued:u,processing:i,raw:l})+T):r>0?(A.classList.remove("is-running"),A.textContent=e.t("ops.ingestion.auto.done",{done:p,failed:r,raw:l})+T):(A.classList.remove("is-running"),A.textContent=e.t("ops.ingestion.auto.allDone",{done:p})+T)}async function Tt(){const s=ft;if(s)try{const a=await tt(s);t.upsertSession(a),re(),ht(a);const l=a.batch_summary,u=rt(a),i=Number(l.total??0);if(i===0){Qe();return}u>0&&await we(`/api/ingestion/sessions/${encodeURIComponent(s)}/auto-process`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({max_concurrency:5})});const p=u>0?await tt(s):a,r=rt(p),h=Math.max(0,Number(p.batch_summary.queued??0)-r),P=Number(p.batch_summary.processing??0);h>0&&P===0&&await it(s),u>0&&(t.upsertSession(p),re(),ht(p));const T=h+P;if(i>0&&T===0&&r===0){if(Number(p.batch_summary.pending_batch_gate??0)>0&&p.status!=="running_batch_gates"&&p.status!=="completed")try{await Ct(s)}catch{}const J=await tt(s);t.upsertSession(J),re(),ht(J),Qe(),o(e.t("ops.ingestion.auto.allDone",{done:Number(J.batch_summary.done??0)}),"success");return}if(T===0&&r>0){A.classList.remove("is-running"),A.textContent=e.t("ops.ingestion.auto.done",{done:Number(p.batch_summary.done??0),failed:Number(p.batch_summary.failed??0),raw:r}),Qe();return}nt=setTimeout(()=>void Tt(),ms)}catch(a){Qe(),o(de(a),"error")}}function It(s){Qe(),ft=s,A.hidden=!1,A.classList.add("is-running"),A.textContent=e.t("ops.ingestion.auto.running",{queued:0,processing:0,raw:0}),nt=setTimeout(()=>void Tt(),2e3)}async function bs(){var G,J,B;_(`directFolderIngest: ${g.pendingFiles.length} archivos pendientes`);const s=await gs();_(`Sesión asignada: ${s.session_id} (corpus=${s.corpus}, status=${s.status})`);const a=k.value||"autogenerar";_(`Subiendo ${g.pendingFiles.length} archivos con batchType="${a}"...`),je(s.session_id);const l=await Be(s.session_id,[...g.pendingFiles],a,Ee);if(console.log("[folder-ingest] Upload result:",{uploaded:l.uploaded,failed:l.failed}),_(`Upload completo: ${l.uploaded} subidos, ${l.failed} fallidos${l.errors.length>0?" — "+l.errors.slice(0,5).map(z=>`${z.filename}: ${z.error}`).join("; "):""}`),t.setPendingFiles([]),t.setFolderUploadProgress(null),Ge(s.session_id),L.value="",C.value="",l.failed>0&&l.uploaded===0){const z=l.errors.slice(0,3).map(ne=>`${ne.filename}: ${ne.error}`).join("; ");_(`TODOS FALLARON: ${z}`),o(`${e.t("ops.ingestion.flash.folderUploadPartial",l)} — ${z}`,"error"),await Je({showWheel:!1,reportError:!0,focusSessionId:s.session_id});return}_("Consultando estado de sesión post-upload...");const u=await tt(s.session_id),i=Number(((G=u.batch_summary)==null?void 0:G.bounced)??0),p=rt(u),r=Number(((J=u.batch_summary)==null?void 0:J.queued)??0),h=Number(((B=u.batch_summary)==null?void 0:B.total)??0),P=h-i;if(_(`Sesión post-upload: total=${h} bounced=${i} raw=${p} queued=${r} actionable=${P}`),P===0&&i>0){_(`TODOS REBOTADOS: ${i} archivos ya existen en el corpus`),t.upsertSession(u),o(`${i} archivos ya existen en el corpus (rebotados). 0 archivos nuevos para procesar.`,"error"),_("--- FIN (todo rebotado) ---");return}_("Auto-procesando con threshold=0 (force-queue)..."),await we(`/api/ingestion/sessions/${encodeURIComponent(s.session_id)}/auto-process`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({max_concurrency:5,auto_accept_threshold:0})}),await it(s.session_id),await Je({showWheel:!1,reportError:!0,focusSessionId:s.session_id});const T=[];l.uploaded>0&&T.push(`${P} archivos en proceso`),i>0&&T.push(`${i} rebotados`),l.failed>0&&T.push(`${l.failed} fallidos`),o(T.join(" · "),l.failed>0?"error":"success"),_(`Auto-piloto iniciado para ${s.session_id}`),_("--- FIN (éxito) ---"),It(s.session_id)}async function fs(s,a){return(await _t("/api/ingestion/preflight",{corpus:a,files:s})).manifest}function Lt(){const s=g.preflightScanProgress;if(!s||!s.scanning){f.hidden=!0,f.innerHTML="";return}const a=s.total>0?Math.round(s.hashed/s.total*100):0;f.hidden=!1,f.innerHTML=`
      <div class="ops-preflight-scan">
        <div class="ops-preflight-scan-header">
          <span>${e.t("ops.ingestion.preflight.scanning",{hashed:s.hashed,total:s.total})}</span>
          <span>${a}%</span>
        </div>
        <div class="ops-preflight-scan-bar">
          <span class="ops-preflight-scan-fill" style="width:${a}%"></span>
        </div>
        <div class="ops-preflight-scan-detail">${e.t("ops.ingestion.preflight.scanningDetail")}</div>
      </div>
    `}function hs(){y.addEventListener("click",()=>{C.disabled||C.click()}),y.addEventListener("keydown",i=>{i.key!=="Enter"&&i.key!==" "||(i.preventDefault(),C.disabled||C.click())});let s=0;y.addEventListener("dragenter",i=>{i.preventDefault(),s++,C.disabled||y.classList.add("is-dragover")}),y.addEventListener("dragover",i=>{i.preventDefault()}),y.addEventListener("dragleave",()=>{s--,s<=0&&(s=0,y.classList.remove("is-dragover"))}),y.addEventListener("drop",async i=>{var h;if(i.preventDefault(),s=0,y.classList.remove("is-dragover"),C.disabled)return;const p=i.dataTransfer;if(p){const P=await We(p);if(P.length>0){pe(ie(P));return}}const r=Array.from(((h=i.dataTransfer)==null?void 0:h.files)||[]);r.length!==0&&pe(ie(r))}),C.addEventListener("change",()=>{const i=Array.from(C.files||[]);i.length!==0&&pe(ie(i))}),L.addEventListener("change",()=>{const i=Array.from(L.files||[]);i.length!==0&&pe(ie(i))}),W.addEventListener("click",()=>{C.disabled||C.click()}),F.addEventListener("click",async()=>{if(!L.disabled){if(typeof window.showDirectoryPicker=="function")try{const i=await window.showDirectoryPicker({mode:"read"}),p=await Ae(i,i.name),r=ie(p);r.length>0?pe(r):o(e.t("ops.ingestion.pendingNone"),"error");return}catch(i){if((i==null?void 0:i.name)==="AbortError")return}L.click()}}),m.addEventListener("change",()=>{t.setSelectedCorpus(m.value),t.setSessions([]),t.setSelectedSession(null),Pe(),o(),re(),Je({showWheel:!0,reportError:!0})}),x.addEventListener("click",i=>{i.stopPropagation(),o(),Je({showWheel:!0,reportError:!0})}),V.addEventListener("click",async()=>{Qe(),o(),Pe(),t.setPreflightManifest(null),t.setFolderUploadProgress(null),g.rejectedArtifacts=[],f.hidden=!0,f.innerHTML="",C.value="",L.value="",O.hidden=!0,I(),w.hidden=!0,b.textContent="",t.setMutating(!0),ge();try{const i=await d(async()=>bt(ue()));t.upsertSession(i),re(),o(e.t("ops.ingestion.flash.sessionCreated",{id:i.session_id}),"success")}catch(i){o(de(i),"error")}finally{t.setMutating(!1),ge()}}),S.addEventListener("click",()=>{Ie()}),E.addEventListener("click",async()=>{const i=g.selectedSessionId;if(i){o(),t.setMutating(!0),ge();try{await d(async()=>it(i)),await Ve({sessionId:i,showWheel:!1,reportError:!1});const p=e.t("ops.ingestion.flash.processStarted",{id:i});o(p,"success"),oe.show({message:p,tone:"success"})}catch(p){const r=de(p);o(r,"error"),oe.show({message:r,tone:"error"})}finally{t.setMutating(!1),ge()}}}),c.addEventListener("click",async()=>{const i=g.selectedSessionId;if(i){o(),t.setMutating(!0),ge();try{await d(async()=>Ct(i)),await Ve({sessionId:i,showWheel:!1,reportError:!1});const p="Validación de lote iniciada";o(p,"success"),oe.show({message:p,tone:"success"})}catch(p){const r=de(p);o(r,"error"),oe.show({message:r,tone:"error"})}finally{t.setMutating(!1),ge()}}}),$.addEventListener("click",async()=>{const i=g.selectedSessionId;if(i){o(),t.setMutating(!0),ge();try{await d(async()=>xt(i)),await Ve({sessionId:i,showWheel:!1,reportError:!1}),o(e.t("ops.ingestion.flash.retryStarted",{id:i}),"success")}catch(p){o(de(p),"error")}finally{t.setMutating(!1),ge()}}}),R.addEventListener("click",async()=>{var P;const i=g.selectedSessionId;if(!i)return;const p=Bt(g.selectedSession),r=p?e.t("ops.ingestion.confirm.ejectPostGate"):e.t("ops.ingestion.confirm.ejectPreGate");if(await oe.confirm({title:e.t("ops.ingestion.actions.discardSession"),message:r,tone:"caution",confirmLabel:e.t("ops.ingestion.confirm.ejectLabel")})){Qe(),o(),t.setMutating(!0),ge();try{const T=lt(String(((P=g.selectedSession)==null?void 0:P.status)||"")),G=await d(async()=>us(i,T||p));t.clearSelectionAfterDelete(),Pe(),t.setPreflightManifest(null),t.setFolderUploadProgress(null),g.rejectedArtifacts=[],f.hidden=!0,f.innerHTML="",C.value="",L.value="",O.hidden=!0,I(),w.hidden=!0,b.textContent="",await Je({showWheel:!1,reportError:!1});const J=Array.isArray(G.errors)&&G.errors.length>0,B=G.path==="rollback"?e.t("ops.ingestion.flash.ejectedRollback",{id:i,count:G.ejected_files}):e.t("ops.ingestion.flash.ejectedInstant",{id:i,count:G.ejected_files}),z=J?"caution":"success";o(B,J?"error":"success"),oe.show({message:B,tone:z}),J&&oe.show({message:e.t("ops.ingestion.flash.ejectedPartial"),tone:"caution",durationMs:8e3})}catch(T){const G=de(T);o(G,"error"),oe.show({message:G,tone:"error"})}finally{t.setMutating(!1),re()}}}),v.addEventListener("click",async()=>{const i=g.selectedSessionId;if(i){o(),t.setMutating(!0),ge();try{await d(async()=>we(`/api/ingestion/sessions/${encodeURIComponent(i)}/auto-process`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({max_concurrency:5})})),await it(i),await Ve({sessionId:i,showWheel:!1,reportError:!1}),o(`Auto-procesamiento iniciado para ${i}`,"success"),It(i)}catch(p){o(de(p),"error")}finally{t.setMutating(!1),ge()}}});const a=document.getElementById("ingestion-log-toggle");a&&(a.addEventListener("click",i=>{if(i.target.closest(".ops-log-copy-btn"))return;const p=b.hidden;b.hidden=!p,a.setAttribute("aria-expanded",String(p));const r=a.querySelector(".ops-log-accordion-marker");r&&(r.textContent=p?"▾":"▸")}),a.addEventListener("keydown",i=>{(i.key==="Enter"||i.key===" ")&&(i.preventDefault(),a.click())})),K.addEventListener("click",i=>{i.preventDefault(),i.stopPropagation();const p=b.textContent||"";navigator.clipboard.writeText(p).then(()=>{const r=K.textContent;K.textContent=e.t("ops.ingestion.log.copied"),setTimeout(()=>{K.textContent=r},1500)}).catch(()=>{const r=document.createRange();r.selectNodeContents(b);const h=window.getSelection();h==null||h.removeAllRanges(),h==null||h.addRange(r)})}),D.addEventListener("click",async i=>{var J;const p=i.target.closest("[data-action]");if(!p)return;const r=p.getAttribute("data-action"),h=p.getAttribute("data-doc-id"),P=g.selectedSessionId;if(!P||!h)return;if(r==="show-existing-dropdown"){const B=p.closest(".kanban-card"),z=B==null?void 0:B.querySelector(".kanban-ag-fallback-panel");z&&(z.hidden=!z.hidden);return}let T="",G="";if(r==="assign"){const B=p.closest(".kanban-card"),z=B==null?void 0:B.querySelector("[data-field='topic']"),ne=B==null?void 0:B.querySelector("[data-field='type']");if(T=(z==null?void 0:z.value)||"",G=(ne==null?void 0:ne.value)||"",!T||!G){z&&!T&&z.classList.add("kanban-select--invalid"),ne&&!G&&ne.classList.add("kanban-select--invalid");return}}o(),t.setMutating(!0),ge();try{switch(r){case"assign":{await d(async()=>we(`/api/ingestion/sessions/${encodeURIComponent(P)}/documents/${encodeURIComponent(h)}/classify`,{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify({topic:T,batch_type:G})})),Le.add(h);break}case"replace-dup":{await d(async()=>we(`/api/ingestion/sessions/${encodeURIComponent(P)}/documents/${encodeURIComponent(h)}/resolve-duplicate`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action:"replace"})}));break}case"add-new-dup":{await d(async()=>we(`/api/ingestion/sessions/${encodeURIComponent(P)}/documents/${encodeURIComponent(h)}/resolve-duplicate`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action:"add_new"})}));break}case"discard-dup":case"discard":{await d(async()=>we(`/api/ingestion/sessions/${encodeURIComponent(P)}/documents/${encodeURIComponent(h)}/resolve-duplicate`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action:"discard"})}));break}case"accept-synonym":{const B=p.closest(".kanban-card"),z=B==null?void 0:B.querySelector("[data-field='type']"),ne=(z==null?void 0:z.value)||"";await d(async()=>we(`/api/ingestion/sessions/${encodeURIComponent(P)}/documents/${encodeURIComponent(h)}/accept-autogenerar`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action:"accept_synonym",type:ne||void 0})})),Le.add(h);break}case"accept-new-topic":{const B=p.closest(".kanban-card"),z=B==null?void 0:B.querySelector("[data-field='autogenerar-label']"),ne=B==null?void 0:B.querySelector("[data-field='type']"),Ce=((J=z==null?void 0:z.value)==null?void 0:J.trim())||"",ve=(ne==null?void 0:ne.value)||"";if(!Ce||Ce.length<3){z&&z.classList.add("kanban-select--invalid");return}await d(async()=>we(`/api/ingestion/sessions/${encodeURIComponent(P)}/documents/${encodeURIComponent(h)}/accept-autogenerar`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action:"accept_new_topic",edited_label:Ce,type:ve||void 0})})),Le.add(h),await Et(),He();break}case"retry":{await d(async()=>we(`/api/ingestion/sessions/${encodeURIComponent(P)}/documents/${encodeURIComponent(h)}/retry`,{method:"POST"}));break}case"remove":break}await Ve({sessionId:P,showWheel:!1,reportError:!1})}catch(B){o(de(B),"error")}finally{t.setMutating(!1),ge()}});const l=n.addCorpusDialog,u=n.addCorpusBtn;if(l&&u){let i=function(B){return B.normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase().replace(/[^a-z0-9]+/g,"_").replace(/^_|_$/g,"")};const p=l.querySelector("#add-corpus-label"),r=l.querySelector("#add-corpus-key"),h=l.querySelector("#add-corpus-kw-strong"),P=l.querySelector("#add-corpus-kw-weak"),T=l.querySelector("#add-corpus-error"),G=l.querySelector("#add-corpus-cancel"),J=l.querySelector("#add-corpus-form");u.addEventListener("click",()=>{p&&(p.value=""),r&&(r.value=""),h&&(h.value=""),P&&(P.value=""),T&&(T.hidden=!0),l.showModal(),p==null||p.focus()}),p==null||p.addEventListener("input",()=>{r&&(r.value=i(p.value))}),G==null||G.addEventListener("click",()=>{l.close()}),J==null||J.addEventListener("submit",async B=>{B.preventDefault(),T&&(T.hidden=!0);const z=(p==null?void 0:p.value.trim())||"";if(!z)return;const ne=((h==null?void 0:h.value)||"").split(",").map(ve=>ve.trim()).filter(Boolean),Ce=((P==null?void 0:P.value)||"").split(",").map(ve=>ve.trim()).filter(Boolean);try{await d(async()=>_t("/api/corpora",{label:z,keywords_strong:ne.length?ne:void 0,keywords_weak:Ce.length?Ce:void 0})),l.close(),await Je({showWheel:!1,reportError:!1});const ve=i(z);ve&&t.setSelectedCorpus(ve),re(),o(`Categoría "${z}" creada.`,"success")}catch(ve){T&&(T.textContent=de(ve),T.hidden=!1)}})}}return{bindEvents:hs,refreshIngestion:Je,refreshSelectedSession:Ve,render:re}}function Xe(e){if(e==null)return null;const t=Number(e);return!Number.isFinite(t)||t<0?null:t}function Yt({i18n:e,stateController:t,dom:n,withThinkingWheel:d,setFlash:o}){const{monitorTabBtn:m,ingestionTabBtn:k,controlTabBtn:y,embeddingsTabBtn:C,reindexTabBtn:L,monitorPanel:W,ingestionPanel:F,controlPanel:f,embeddingsPanel:N,reindexPanel:j,runsBody:x,timelineNode:V,timelineMeta:S,cascadeNote:E,userCascadeNode:v,userCascadeSummary:c,technicalCascadeNode:$,technicalCascadeSummary:R,refreshRunsBtn:X}=n,{state:me}=t;function fe(_){const I=Xe(_);return I===null?"-":`${e.formatNumber(I/1e3,{minimumFractionDigits:2,maximumFractionDigits:2})} s`}function O(_){t.setActiveTab(_),le()}function le(){if(!m)return;const _=me.activeTab;m.classList.toggle("is-active",_==="monitor"),m.setAttribute("aria-selected",String(_==="monitor")),k==null||k.classList.toggle("is-active",_==="ingestion"),k==null||k.setAttribute("aria-selected",String(_==="ingestion")),y==null||y.classList.toggle("is-active",_==="control"),y==null||y.setAttribute("aria-selected",String(_==="control")),C==null||C.classList.toggle("is-active",_==="embeddings"),C==null||C.setAttribute("aria-selected",String(_==="embeddings")),L==null||L.classList.toggle("is-active",_==="reindex"),L==null||L.setAttribute("aria-selected",String(_==="reindex")),W&&(W.hidden=_!=="monitor",W.classList.toggle("is-active",_==="monitor")),F&&(F.hidden=_!=="ingestion",F.classList.toggle("is-active",_==="ingestion")),f&&(f.hidden=_!=="control",f.classList.toggle("is-active",_==="control")),N&&(N.hidden=_!=="embeddings",N.classList.toggle("is-active",_==="embeddings")),j&&(j.hidden=_!=="reindex",j.classList.toggle("is-active",_==="reindex"))}function Fe(_){if(V.innerHTML="",!Array.isArray(_)||_.length===0){V.innerHTML=`<li>${e.t("ops.timeline.empty")}</li>`;return}_.forEach(I=>{const Z=document.createElement("li");Z.innerHTML=`
        <strong>${I.stage||"-"}</strong> · <span class="status-${ot(String(I.status||""))}">${I.status||"-"}</span><br/>
        <small>${I.at||"-"} · ${I.duration_ms||0} ms</small>
        <pre>${JSON.stringify(I.details||{},null,2)}</pre>
      `,V.appendChild(Z)})}function q(_,I,Z){const H=Xe(I==null?void 0:I.total_ms),ae=H===null?e.t("ops.timeline.summaryPending"):fe(H),ee=Z==="user"&&String((I==null?void 0:I.chat_run_id)||"").trim()?` · chat_run ${String((I==null?void 0:I.chat_run_id)||"").trim()}`:"";_.textContent=`${e.t("ops.timeline.totalLabel")} ${ae}${ee}`}function D(_){var Q,pe,ye;const I=[],Z=String(((Q=_.details)==null?void 0:Q.source)||"").trim(),H=String(_.status||"").trim();Z&&I.push(Z),H&&H!=="ok"&&H!=="missing"&&I.push(H);const ae=Number(((pe=_.details)==null?void 0:pe.citations_count)||0);Number.isFinite(ae)&&ae>0&&I.push(`${ae} refs`);const ee=String(((ye=_.details)==null?void 0:ye.panel_status)||"").trim();return ee&&I.push(ee),I.join(" · ")}function w(_,I,Z){_.innerHTML="";const H=Array.isArray(I==null?void 0:I.steps)?(I==null?void 0:I.steps)||[]:[];if(H.length===0){_.innerHTML=`<li class="ops-cascade-step is-empty">${e.t("ops.timeline.waterfallEmpty")}</li>`;return}const ae=Xe(I==null?void 0:I.total_ms)??Math.max(1,...H.map(ee=>Xe(ee.cumulative_ms)??Xe(ee.absolute_elapsed_ms)??0));H.forEach(ee=>{const Q=Xe(ee.duration_ms),pe=Xe(ee.offset_ms)??0,ye=Xe(ee.absolute_elapsed_ms),_e=document.createElement("li");_e.className=`ops-cascade-step ops-cascade-step--${Z}${Q===null?" is-missing":""}`;const U=document.createElement("div");U.className="ops-cascade-step-head";const Se=document.createElement("div"),xe=document.createElement("strong");xe.textContent=ee.label||"-";const Te=document.createElement("small");Te.className="ops-cascade-step-meta",Te.textContent=Q===null?e.t("ops.timeline.missingStep"):`${e.t("ops.timeline.stepLabel")} ${fe(Q)} · T+${fe(ye??ee.cumulative_ms)}`,Se.append(xe,Te);const qe=document.createElement("span");qe.className=`meta-chip status-${ot(String(ee.status||""))}`,qe.textContent=String(ee.status||(Q===null?"missing":"ok")),U.append(Se,qe),_e.appendChild(U);const Pe=document.createElement("div");Pe.className="ops-cascade-track";const Ie=document.createElement("span");Ie.className="ops-cascade-segment";const Le=Math.max(0,Math.min(100,pe/ae*100)),He=Q===null?0:Math.max(Q/ae*100,Q>0?2.5:0);Ie.style.left=`${Le}%`,Ie.style.width=`${He}%`,Ie.setAttribute("aria-label",Q===null?`${ee.label}: ${e.t("ops.timeline.missingStep")}`:`${ee.label}: ${fe(Q)}`),Pe.appendChild(Ie),_e.appendChild(Pe);const ue=D(ee);if(ue){const be=document.createElement("p");be.className="ops-cascade-step-detail",be.textContent=ue,_e.appendChild(be)}_.appendChild(_e)})}async function b(){return(await Ze("/api/ops/runs?limit=30")).runs||[]}async function K(_){return Ze(`/api/ops/runs/${encodeURIComponent(_)}/timeline`)}function A(_,I){var H;const Z=_.run||{};S.textContent=e.t("ops.timeline.label",{id:I}),E.textContent=e.t("ops.timeline.selectedRunMeta",{trace:String(Z.trace_id||"-"),chatRun:String(((H=_.user_waterfall)==null?void 0:H.chat_run_id)||Z.chat_run_id||"-")}),q(c,_.user_waterfall,"user"),q(R,_.technical_waterfall,"technical"),w(v,_.user_waterfall,"user"),w($,_.technical_waterfall,"technical"),Fe(Array.isArray(_.timeline)?_.timeline:[])}function g(_){if(x.innerHTML="",!Array.isArray(_)||_.length===0){const I=document.createElement("tr");I.innerHTML=`<td colspan="4">${e.t("ops.runs.empty")}</td>`,x.appendChild(I);return}_.forEach(I=>{const Z=document.createElement("tr");Z.innerHTML=`
        <td><button type="button" class="link-btn" data-run-id="${I.run_id}">${I.run_id}</button></td>
        <td>${I.trace_id||"-"}</td>
        <td class="status-${ot(String(I.status||""))}">${I.status||"-"}</td>
        <td>${I.started_at?e.formatDateTime(I.started_at,{dateStyle:"short",timeStyle:"short",timeZone:"America/Bogota"}):"-"}</td>
      `,x.appendChild(Z)}),x.querySelectorAll("button[data-run-id]").forEach(I=>{I.addEventListener("click",async()=>{const Z=I.getAttribute("data-run-id")||"";try{const H=await d(async()=>K(Z));A(H,Z)}catch(H){v.innerHTML=`<li class="ops-cascade-step is-empty status-error">${de(H)}</li>`,$.innerHTML=`<li class="ops-cascade-step is-empty status-error">${de(H)}</li>`,V.innerHTML=`<li class="status-error">${de(H)}</li>`}})})}async function oe({showWheel:_=!0,reportError:I=!0}={}){const Z=async()=>{const H=await b();g(H)};try{_?await d(Z):await Z()}catch(H){x.innerHTML=`<tr><td colspan="4" class="status-error">${de(H)}</td></tr>`,I&&o(de(H),"error")}}function he(){m==null||m.addEventListener("click",()=>{O("monitor")}),k==null||k.addEventListener("click",()=>{O("ingestion")}),y==null||y.addEventListener("click",()=>{O("control")}),C==null||C.addEventListener("click",()=>{O("embeddings")}),L==null||L.addEventListener("click",()=>{O("reindex")}),X.addEventListener("click",()=>{o(),oe({showWheel:!0,reportError:!0})})}return{bindEvents:he,refreshRuns:oe,renderTabs:le}}function ze(e){return String(e??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#39;")}function st(e){return(e??0).toLocaleString("es-CO")}function rn(e){if(e==null||e<=0)return"-";const t=Math.floor(e/60),n=Math.floor(e%60);return t>0?`${t}m ${n}s`:`${n}s`}function cn(e){if(!e.length)return"";let t='<ol class="reindex-stage-list">';for(const n of e){const d=n.state==="completed"?"ops-dot-ok":n.state==="active"?"ops-dot-active":n.state==="failed"?"ops-dot-error":"ops-dot-pending",o=n.state==="active"?`<strong>${ze(n.label)}</strong>`:ze(n.label);t+=`<li class="reindex-stage-item reindex-stage-${n.state}"><span class="ops-dot ${d}">●</span> ${o}</li>`}return t+="</ol>",t}function Qt({dom:e,setFlash:t,navigateToEmbeddings:n}){const{container:d}=e;let o=null,m="";function k(){var E,v,c;const F=o;if(!F){d.innerHTML='<p class="ops-text-muted">Cargando estado de re-index...</p>';return}const f=F.current_operation||F.last_operation,N=((E=F.current_operation)==null?void 0:E.status)==="running",j=!F.current_operation;let x="";const V=N?"En ejecución":j?"Inactivo":(f==null?void 0:f.status)??"—",S=N?"tone-yellow":(f==null?void 0:f.status)==="completed"?"tone-green":(f==null?void 0:f.status)==="failed"?"tone-red":"";if(x+=`<div class="reindex-status-row">
      <span class="corpus-status-chip ${S}">${ze(V)}</span>
      <span class="emb-target-badge">WIP</span>
      ${N?`<span class="emb-heartbeat ${kt(f==null?void 0:f.heartbeat_at,f==null?void 0:f.updated_at)}">${kt(f==null?void 0:f.heartbeat_at,f==null?void 0:f.updated_at)}</span>`:""}
    </div>`,x+='<div class="reindex-controls">',j&&(x+=`<button class="corpus-btn corpus-btn-promote" id="reindex-start-btn" ${m?"disabled":""}>Iniciar re-index</button>`),N&&f&&(x+=`<button class="corpus-btn corpus-btn-rollback" id="reindex-stop-btn" ${m?"disabled":""}>Detener</button>`),x+="</div>",(v=f==null?void 0:f.stages)!=null&&v.length&&(x+=cn(f.stages)),f!=null&&f.progress){const $=f.progress,R=[];$.documents_processed!=null&&R.push(`Documentos: ${st($.documents_processed)} / ${st($.documents_total)}`),$.documents_indexed!=null&&R.push(`Documentos indexados: ${st($.documents_indexed)}`),$.elapsed_seconds!=null&&R.push(`Tiempo: ${rn($.elapsed_seconds)}`),R.length&&(x+=`<div class="reindex-progress-stats">${R.map(X=>`<span>${ze(X)}</span>`).join("")}</div>`)}if(f!=null&&f.quality_report){const $=f.quality_report;if(x+='<div class="reindex-quality-report">',x+="<h3>Reporte de calidad</h3>",x+=`<div class="emb-stats-grid">
        <div class="emb-stat"><span class="emb-stat-value">${st($.documents_indexed)}</span><span class="emb-stat-label">Documentos</span></div>
        <div class="emb-stat"><span class="emb-stat-value">${st($.chunks_generated)}</span><span class="emb-stat-label">Chunks</span></div>
        <div class="emb-stat"><span class="emb-stat-value">${$.blocking_issues??0}</span><span class="emb-stat-label">Blocking issues</span></div>
      </div>`,$.knowledge_class_counts){x+='<div class="reindex-kc-breakdown"><h4>Knowledge classes</h4><dl class="reindex-kc-dl">';for(const[R,X]of Object.entries($.knowledge_class_counts))x+=`<dt>${ze(R)}</dt><dd>${st(X)}</dd>`;x+="</dl></div>"}x+="</div>",x+=`<div class="reindex-embed-prompt">
        <p>Re-index completado. Para aplicar los nuevos summaries a los embeddings:</p>
        <button class="corpus-btn corpus-btn-promote" id="reindex-embed-now-btn">Embed ahora</button>
      </div>`}if((c=f==null?void 0:f.checks)!=null&&c.length){x+='<div class="emb-checks">';for(const $ of f.checks){const R=$.ok?'<span class="ops-dot ops-dot-ok">●</span>':'<span class="ops-dot ops-dot-error">●</span>';x+=`<div class="emb-check">${R} <strong>${ze($.label)}</strong>: ${ze($.detail)}</div>`}x+="</div>"}f!=null&&f.log_tail&&(x+=`<details class="emb-log-accordion"><summary>Log</summary><pre class="emb-log-tail">${ze(f.log_tail)}</pre></details>`),f!=null&&f.error&&(x+=`<p class="emb-error">${ze(f.error)}</p>`),d.innerHTML=x}function y(){d.addEventListener("click",F=>{const f=F.target;f.id==="reindex-start-btn"&&C(),f.id==="reindex-stop-btn"&&L(),f.id==="reindex-embed-now-btn"&&n()})}async function C(){m="start",k();try{await Ye("/api/ops/reindex/start",{mode:"from_source"}),t("Re-index iniciado","success")}catch(F){t(String(F),"error")}m="",await W()}async function L(){var f;const F=(f=o==null?void 0:o.current_operation)==null?void 0:f.job_id;if(F){m="stop",k();try{await Ye("/api/ops/reindex/stop",{job_id:F}),t("Re-index detenido","success")}catch(N){t(String(N),"error")}m="",await W()}}async function W(){try{o=await Ze("/api/ops/reindex-status")}catch{}k()}return{bindEvents:y,refresh:W}}const _n=Object.freeze(Object.defineProperty({__proto__:null,createOpsReindexController:Qt},Symbol.toStringTag,{value:"Module"})),ln=3e3,Ht=8e3;function es({stateController:e,withThinkingWheel:t,setFlash:n,refreshRuns:d,refreshIngestion:o,refreshCorpusLifecycle:m,refreshEmbeddings:k,refreshReindex:y,intervalMs:C}){(async()=>{try{await t(async()=>{await Promise.all([d({showWheel:!1,reportError:!1}),o({showWheel:!1,reportError:!1}),m==null?void 0:m(),k==null?void 0:k(),y==null?void 0:y()])})}catch(N){n(de(N),"error")}})();let L=null,W=C??Ht;function F(){const N=e.state.selectedSession;return N?lt(String(N.status||""))?!0:(N.documents||[]).some(x=>x.status==="in_progress"||x.status==="processing"||x.status==="extracting"||x.status==="etl"||x.status==="writing"||x.status==="gates"):!1}function f(){const N=C??(F()?ln:Ht);L!==null&&N===W||(L!==null&&window.clearInterval(L),W=N,L=window.setInterval(()=>{d({showWheel:!1,reportError:!1}),o({showWheel:!1,reportError:!1,focusSessionId:e.getFocusedRunningSessionId()}),m==null||m(),k==null||k(),y==null||y(),C||f()},W))}return f(),()=>{L!==null&&(window.clearInterval(L),L=null)}}function ts(){const e={activeTab:Ms(),corpora:[],selectedCorpus:"autogenerar",sessions:[],selectedSessionId:Os(),selectedSession:null,pendingFiles:[],intake:[],reviewPlan:null,preflightRunId:0,mutating:!1,folderUploadProgress:null,folderRelativePaths:new Map,rejectedArtifacts:[],preflightManifest:null,preflightScanProgress:null};function t(){return e.corpora.find(c=>c.key===e.selectedCorpus)}function n(c){e.activeTab=c,qs(c)}function d(c){e.corpora=[...c]}function o(c){e.folderUploadProgress=c}function m(c){e.preflightManifest=c}function k(c){e.preflightScanProgress=c}function y(c){e.mutating=c}function C(c){e.pendingFiles=[...c]}function L(c){e.intake=[...c]}function W(c){e.reviewPlan=c?{...c,willIngest:[...c.willIngest],bounced:[...c.bounced]}:null}function F(){return e.preflightRunId+=1,e.preflightRunId}function f(c){e.selectedCorpus=c}function N(c){e.selectedSession=c,e.selectedSessionId=(c==null?void 0:c.session_id)||"",Ds((c==null?void 0:c.session_id)||null),c&&(V=!1)}function j(){V=!0,N(null)}function x(c){e.sessions=[...c]}let V=!1;function S(){if(e.selectedSessionId){const c=e.sessions.find($=>$.session_id===e.selectedSessionId)||null;N(c);return}if(V){N(null);return}N(e.sessions[0]||null)}function E(c){const $=e.sessions.filter(R=>R.session_id!==c.session_id);e.sessions=[c,...$].sort((R,X)=>Date.parse(String(X.updated_at||0))-Date.parse(String(R.updated_at||0))),N(c)}function v(){var c;return lt(String(((c=e.selectedSession)==null?void 0:c.status)||""))?e.selectedSessionId:""}return{state:e,clearSelectionAfterDelete:j,getFocusedRunningSessionId:v,selectedCorpusConfig:t,setActiveTab:n,setCorpora:d,setFolderUploadProgress:o,setMutating:y,setPendingFiles:C,setIntake:L,setReviewPlan:W,bumpPreflightRunId:F,setPreflightManifest:m,setPreflightScanProgress:k,setSelectedCorpus:f,setSelectedSession:N,setSessions:x,syncSelectedSession:S,upsertSession:E}}function dn(e,{i18n:t}){const n=e,d=n.querySelector("#ops-tab-monitor"),o=n.querySelector("#ops-tab-ingestion"),m=n.querySelector("#ops-tab-control"),k=n.querySelector("#ops-tab-embeddings"),y=n.querySelector("#ops-tab-reindex"),C=n.querySelector("#ops-panel-monitor"),L=n.querySelector("#ops-panel-ingestion"),W=n.querySelector("#ops-panel-control"),F=n.querySelector("#ops-panel-embeddings"),f=n.querySelector("#ops-panel-reindex"),N=n.querySelector("#runs-body"),j=n.querySelector("#timeline"),x=n.querySelector("#timeline-meta"),V=n.querySelector("#cascade-note"),S=n.querySelector("#user-cascade"),E=n.querySelector("#user-cascade-summary"),v=n.querySelector("#technical-cascade"),c=n.querySelector("#technical-cascade-summary"),$=n.querySelector("#refresh-runs"),R=!!(N&&j&&x&&V&&S&&E&&v&&c&&$),X=Y(n,"#ingestion-corpus"),me=Y(n,"#ingestion-batch-type"),fe=Y(n,"#ingestion-dropzone"),O=Y(n,"#ingestion-file-input"),le=Y(n,"#ingestion-folder-input"),Fe=Y(n,"#ingestion-pending-files"),q=Y(n,"#ingestion-overview"),D=Y(n,"#ingestion-flash"),w=Y(n,"#ingestion-refresh"),b=Y(n,"#ingestion-create-session"),K=Y(n,"#ingestion-select-files"),A=Y(n,"#ingestion-select-folder"),g=Y(n,"#ingestion-upload-files"),oe=Y(n,"#ingestion-upload-progress"),he=Y(n,"#ingestion-process-session"),_=Y(n,"#ingestion-auto-process"),I=Y(n,"#ingestion-validate-batch"),Z=Y(n,"#ingestion-retry-session"),H=Y(n,"#ingestion-delete-session"),ae=Y(n,"#ingestion-session-meta"),ee=Y(n,"#ingestion-sessions-list"),Q=Y(n,"#selected-session-meta"),pe=Y(n,"#ingestion-last-error"),ye=Y(n,"#ingestion-last-error-message"),_e=Y(n,"#ingestion-last-error-guidance"),U=Y(n,"#ingestion-last-error-next"),Se=Y(n,"#ingestion-kanban"),xe=Y(n,"#ingestion-log-accordion"),Te=Y(n,"#ingestion-log-body"),qe=Y(n,"#ingestion-log-copy"),Pe=Y(n,"#ingestion-auto-status"),Ie=n.querySelector("#ingestion-add-corpus-btn"),Le=n.querySelector("#add-corpus-dialog"),He=n.querySelector("#ingestion-bounce-log"),ue=n.querySelector("#ingestion-bounce-body"),be=n.querySelector("#ingestion-bounce-copy"),Oe=ts();function Ee(et="",gt="success"){if(!et){D.hidden=!0,D.textContent="",D.removeAttribute("data-tone");return}D.hidden=!1,D.dataset.tone=gt,D.textContent=et}async function De(et){return et()}const ie=R?Yt({i18n:t,stateController:Oe,dom:{monitorTabBtn:d,ingestionTabBtn:o,controlTabBtn:m,embeddingsTabBtn:k,reindexTabBtn:y,monitorPanel:C,ingestionPanel:L,controlPanel:W,embeddingsPanel:F,reindexPanel:f,runsBody:N,timelineNode:j,timelineMeta:x,cascadeNote:V,userCascadeNode:S,userCascadeSummary:E,technicalCascadeNode:v,technicalCascadeSummary:c,refreshRunsBtn:$},withThinkingWheel:De,setFlash:Ee}):null,We=on({i18n:t,stateController:Oe,dom:{ingestionCorpusSelect:X,ingestionBatchTypeSelect:me,ingestionDropzone:fe,ingestionFileInput:O,ingestionFolderInput:le,ingestionSelectFilesBtn:K,ingestionSelectFolderBtn:A,ingestionUploadProgress:oe,ingestionPendingFiles:Fe,ingestionOverview:q,ingestionRefreshBtn:w,ingestionCreateSessionBtn:b,ingestionUploadBtn:g,ingestionProcessBtn:he,ingestionAutoProcessBtn:_,ingestionValidateBatchBtn:I,ingestionRetryBtn:Z,ingestionDeleteSessionBtn:H,ingestionSessionMeta:ae,ingestionSessionsList:ee,selectedSessionMeta:Q,ingestionLastError:pe,ingestionLastErrorMessage:ye,ingestionLastErrorGuidance:_e,ingestionLastErrorNext:U,ingestionKanban:Se,ingestionLogAccordion:xe,ingestionLogBody:Te,ingestionLogCopyBtn:qe,ingestionAutoStatus:Pe,addCorpusBtn:Ie,addCorpusDialog:Le,ingestionBounceLog:He,ingestionBounceBody:ue,ingestionBounceCopy:be},withThinkingWheel:De,setFlash:Ee}),Me=n.querySelector("#corpus-lifecycle"),Ae=Me?zt({dom:{container:Me},setFlash:Ee}):null,Be=n.querySelector("#embeddings-lifecycle"),$e=Be?Vt({dom:{container:Be},setFlash:Ee}):null,je=n.querySelector("#reindex-lifecycle"),Ge=je?Qt({dom:{container:je},setFlash:Ee,navigateToEmbeddings:()=>{Oe.setActiveTab("embeddings"),ie==null||ie.renderTabs()}}):null;ie==null||ie.bindEvents(),We.bindEvents(),Ae==null||Ae.bindEvents(),$e==null||$e.bindEvents(),Ge==null||Ge.bindEvents(),ie==null||ie.renderTabs(),We.render(),es({stateController:Oe,withThinkingWheel:De,setFlash:Ee,refreshRuns:(ie==null?void 0:ie.refreshRuns)??(async()=>{}),refreshIngestion:We.refreshIngestion,refreshCorpusLifecycle:Ae==null?void 0:Ae.refresh,refreshEmbeddings:$e==null?void 0:$e.refresh,refreshReindex:Ge==null?void 0:Ge.refresh})}function pn(e,{i18n:t}){const n=e,d=n.querySelector("#runs-body"),o=n.querySelector("#timeline"),m=n.querySelector("#timeline-meta"),k=n.querySelector("#cascade-note"),y=n.querySelector("#user-cascade"),C=n.querySelector("#user-cascade-summary"),L=n.querySelector("#technical-cascade"),W=n.querySelector("#technical-cascade-summary"),F=n.querySelector("#refresh-runs");if(!d||!o||!m||!k||!y||!C||!L||!W||!F)return;const f=ts(),N=async V=>V(),j=()=>{},x=Yt({i18n:t,stateController:f,dom:{monitorTabBtn:null,ingestionTabBtn:null,controlTabBtn:null,embeddingsTabBtn:null,reindexTabBtn:null,monitorPanel:null,ingestionPanel:null,controlPanel:null,embeddingsPanel:null,reindexPanel:null,runsBody:d,timelineNode:o,timelineMeta:m,cascadeNote:k,userCascadeNode:y,userCascadeSummary:C,technicalCascadeNode:L,technicalCascadeSummary:W,refreshRunsBtn:F},withThinkingWheel:N,setFlash:j});x.bindEvents(),x.renderTabs(),es({stateController:f,withThinkingWheel:N,setFlash:j,refreshRuns:x.refreshRuns,refreshIngestion:async()=>{}})}const $n=Object.freeze(Object.defineProperty({__proto__:null,mountBackstageApp:pn,mountOpsApp:dn},Symbol.toStringTag,{value:"Module"}));export{dn as a,ws as b,yn as c,_n as d,$n as e,pn as m,vn as o,_s as r,hn as s};
