import{q as Q}from"./bootstrap-DAARwiGO.js";import{g as Ae,p as je,A as nt}from"./client-OE0sHIIg.js";import{p as qt}from"./colors-ps0hVFT8.js";import{g as vt}from"./index-BAf9D_ld.js";import{getToastController as hs}from"./toasts-Dx3CUztl.js";function vs(){return`
    <main id="lia-ingest-shell" class="lia-ingest-shell" data-lia-template="ingest-sesiones">
      <header class="lia-ingest-shell__header">
        <p class="lia-ingest-shell__eyebrow">Lia Graph · Lane 0</p>
        <h1 class="lia-ingest-shell__title">Sesiones de ingesta</h1>
        <p class="lia-ingest-shell__lede">
          Surface administrativa de la pipeline de ingestión Lia Graph.
          Lee artefactos materializados (<code>artifacts/corpus_audit_report.json</code>,
          <code>graph_validation_report.json</code>) y la tabla cloud
          <code>corpus_generations</code>. Para promover WIP → Cloud Supabase + Cloud Falkor,
          usa la pestaña Promoción.
        </p>
      </header>

      <div class="lia-ingest-shell__grid">
        <div class="lia-ingest-shell__col lia-ingest-shell__col--primary" data-slot="corpus-overview"></div>
        <div class="lia-ingest-shell__col lia-ingest-shell__col--secondary" data-slot="run-trigger"></div>
      </div>

      <div class="lia-ingest-shell__row" data-slot="generations-list"></div>
    </main>
  `}function ys(e){return`
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
        ${vs()}
      </div>

      <div id="ingestion-section-promocion" class="ingestion-section" role="tabpanel" hidden></div>
    </div>
  `}function ws(){return`
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
  `}function ks(e){return`
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
      ${ys()}
    </main>
  `}const qn=Object.freeze(Object.defineProperty({__proto__:null,renderBackstageShell:_s,renderIngestionShell:$s,renderOpsShell:ks,renderPromocionShell:ws},Symbol.toStringTag,{value:"Module"})),Ss=2e3;function j(e){return String(e??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#39;")}function ne(e){return(e??0).toLocaleString("es-CO")}function Cs(e){if(!e)return"-";try{return new Date(e).toLocaleDateString("es-CO",{day:"numeric",month:"short",hour:"2-digit",minute:"2-digit",timeZone:"America/Bogota"})}catch{return e}}function Ot(e){if(!e)return"-";const t=Date.parse(e);if(Number.isNaN(t))return e;const s=Math.max(0,Math.floor((Date.now()-t)/1e3));if(s<5)return"ahora";if(s<60)return`hace ${s}s`;const o=Math.floor(s/60),n=s%60;return o<60?`hace ${o}m ${n}s`:`hace ${Math.floor(o/60)}h ${o%60}m`}function Le(e){return e?e.length>24?`${e.slice(0,15)}…${e.slice(-8)}`:e:"-"}function Es(e){return e===void 0?'<span class="ops-dot ops-dot-unknown">●</span>':e?'<span class="ops-dot ops-dot-ok">●</span>':'<span class="ops-dot ops-dot-error">●</span>'}function Dt(e,t){if(!t.available)return`
      <div class="corpus-card corpus-card-unavailable">
        <h4 class="corpus-card-title">${j(e)}</h4>
        <p class="corpus-card-unavail">● no disponible</p>
        ${t.error?`<p class="ops-subcopy">${j(t.error)}</p>`:""}
      </div>`;const s=t.knowledge_class_counts??{};return`
    <div class="corpus-card">
      <h4 class="corpus-card-title">${j(e)}</h4>
      <div class="corpus-card-row"><span>Gen:</span> <code>${j(Le(t.generation_id))}</code></div>
      <div class="corpus-card-row"><span>Documentos:</span> <strong>${ne(t.documents)}</strong></div>
      <div class="corpus-card-row"><span>Chunks:</span> <strong>${ne(t.chunks)}</strong></div>
      <div class="corpus-card-row"><span>Embeddings:</span> ${Es(t.embeddings_complete)} ${t.embeddings_complete?"completos":"incompletos"}</div>
      <div class="corpus-card-sep"></div>
      <div class="corpus-card-row corpus-card-row-sm"><span>normative_base:</span> ${ne(s.normative_base)}</div>
      <div class="corpus-card-row corpus-card-row-sm"><span>interpretative:</span> ${ne(s.interpretative_guidance)}</div>
      <div class="corpus-card-row corpus-card-row-sm"><span>practica_erp:</span> ${ne(s.practica_erp)}</div>
      <div class="corpus-card-sep"></div>
      <div class="corpus-card-row corpus-card-row-sm"><span>${e==="PRODUCTION"?"Activado:":"Actualizado:"}</span> ${j(Cs(t.activated_at))}</div>
    </div>`}function Bt(e,t={}){const{onlyFailures:s=!1}=t,o=(e??[]).filter(n=>s?!n.ok:!0);return o.length===0?"":`
    <ul class="corpus-checks">
      ${o.map(n=>`
            <li class="corpus-check ${n.ok?"is-ok":"is-fail"}">
              <span class="corpus-check-dot"></span>
              <div>
                <strong>${j(n.label)}</strong>
                <span>${j(n.detail)}</span>
              </div>
            </li>`).join("")}
    </ul>`}function Ps(e){const t=e??[];return t.length===0?"":`
    <ol class="corpus-stage-list">
      ${t.map(s=>`
            <li class="corpus-stage-item state-${j(s.state)}">
              <span class="corpus-stage-dot"></span>
              <span>${j(s.label)}</span>
            </li>`).join("")}
    </ol>`}function bt(e){const t=String(e||"").trim();return t?t.replaceAll("_"," "):"-"}function xs(e){return e?e.kind==="audit"?"Audit":e.kind==="rollback"?"Rollback":e.mode==="force_reset"?"Force reset":"Promote":"Promote"}function wt(e){const t=e==null?void 0:e.last_checkpoint;if(!(t!=null&&t.phase))return"-";const s=t.cursor??0,o=t.total??0,n=o>0?(s/o*100).toFixed(1):"0";return`${bt(t.phase)} · ${ne(s)} / ${ne(o)} (${n}%)`}function jt(e){var o,n;const t=((o=e==null?void 0:e.last_checkpoint)==null?void 0:o.cursor)??(e==null?void 0:e.batch_cursor)??0,s=((n=e==null?void 0:e.last_checkpoint)==null?void 0:n.total)??0;return s<=0?0:Math.min(100,Math.max(0,t/s*100))}function Ns(e){if(!(e!=null&&e.heartbeat_at))return{label:"-",className:""};const t=Math.max(0,(Date.now()-Date.parse(e.heartbeat_at))/1e3);return t<15?{label:"Saludable",className:"hb-healthy"}:t<45?{label:"Lento",className:"hb-slow"}:{label:"Sin respuesta",className:"hb-stale"}}function Is(e,t){var s,o,n,r,m,b;if(e)switch(e.operation_state_code){case"orphaned_queue":return{severity:"red",title:"Orphaned before start",detail:"The request was queued, but the backend worker never started."};case"stalled_resumable":return{severity:"red",title:"Stalled",detail:(s=e.last_checkpoint)!=null&&s.phase?`Backend stalled after ${bt(e.last_checkpoint.phase)}. Resume is available.`:"Backend stalled, but a checkpoint is available to resume."};case"failed_resumable":return{severity:"red",title:"Resumable",detail:e.error||((n=(o=e.failures)==null?void 0:o[0])==null?void 0:n.message)||"The last run failed after writing a checkpoint. Resume is available."};case"completed":return{severity:"green",title:"Completed",detail:e.kind==="audit"?"WIP audit completed. Artifact written.":e.kind==="rollback"?"Rollback completed and verified.":"Promotion completed and verified."};case"running":return{severity:"yellow",title:"Running",detail:e.current_phase?`Backend phase: ${bt(e.current_phase)}.`:e.stage_label?`Stage: ${e.stage_label}.`:"The backend is processing the promotion."};default:return{severity:e.severity??"red",title:e.severity==="yellow"?"Running":"Failed",detail:e.error||((m=(r=e.failures)==null?void 0:r[0])==null?void 0:m.message)||"The operation ended with an error."}}return t!=null&&t.preflight_ready?{severity:"green",title:"Ready",detail:"WIP audit and promotion preflight are green."}:{severity:"red",title:"Blocked",detail:((b=t==null?void 0:t.preflight_reasons)==null?void 0:b[0])||"Production is not ready for a safe promotion."}}function Ts(e){return e?e.kind==="audit"?"WIP Health Audit":e.kind==="rollback"?"Rollback Production":e.mode==="force_reset"?"Force Reset + Promote Production":"Promote WIP to Production":"Promote WIP to Production"}function Ft(e,t){return!t||t.available===!1?`<tr><td>${j(e)}</td><td colspan="2" class="corpus-report-unavail">no disponible</td></tr>`:`
    <tr>
      <td>${j(e)}</td>
      <td><code>${j(Le(t.generation_id))}</code></td>
      <td>${ne(t.documents)} docs · ${ne(t.chunks)} chunks</td>
    </tr>`}function Ht(e,t){const s=new Set;for(const n of Object.keys((e==null?void 0:e.knowledge_class_counts)??{}))s.add(n);for(const n of Object.keys((t==null?void 0:t.knowledge_class_counts)??{}))s.add(n);return s.size===0?"":[...s].sort().map(n=>{const r=((e==null?void 0:e.knowledge_class_counts)??{})[n]??0,m=((t==null?void 0:t.knowledge_class_counts)??{})[n]??0,b=m-r,w=b>0?"is-positive":b<0?"is-negative":"",k=b>0?`+${ne(b)}`:b<0?ne(b):"—";return`
        <tr class="corpus-report-kc-row">
          <td>${j(n)}</td>
          <td>${ne(r)}</td>
          <td>${ne(m)}</td>
          <td class="corpus-report-delta ${w}">${k}</td>
        </tr>`}).join("")}function Ls(e,t){if(!e||!t)return"-";const s=Date.parse(e),o=Date.parse(t);if(Number.isNaN(s)||Number.isNaN(o))return"-";const n=Math.max(0,Math.floor((o-s)/1e3)),r=Math.floor(n/60),m=n%60;return r===0?`${m}s`:`${r}m ${m}s`}function As(e){const t=e==null?void 0:e.promotion_summary;if(!t)return"";const{before:s,after:o,delta:n,plan_result:r}=t,m=((n==null?void 0:n.documents)??0)>0?`+${ne(n==null?void 0:n.documents)}`:ne(n==null?void 0:n.documents),b=((n==null?void 0:n.chunks)??0)>0?`+${ne(n==null?void 0:n.chunks)}`:ne(n==null?void 0:n.chunks),w=((n==null?void 0:n.documents)??0)>0?"is-positive":((n==null?void 0:n.documents)??0)<0?"is-negative":"",k=((n==null?void 0:n.chunks)??0)>0?"is-positive":((n==null?void 0:n.chunks)??0)<0?"is-negative":"",A=s||o?`
      <table class="corpus-report-table">
        <thead>
          <tr><th></th><th>Generación</th><th>Documentos / Chunks</th></tr>
        </thead>
        <tbody>
          ${Ft("Antes",s)}
          ${Ft("Después",o)}
        </tbody>
        ${n?`
        <tfoot>
          <tr>
            <td>Delta</td>
            <td></td>
            <td>
              <span class="corpus-report-delta ${w}">${m} docs</span> ·
              <span class="corpus-report-delta ${k}">${b} chunks</span>
            </td>
          </tr>
        </tfoot>`:""}
      </table>
      ${Ht(s,o)?`
      <table class="corpus-report-table corpus-report-table-kc">
        <thead><tr><th>Clase</th><th>Antes</th><th>Después</th><th>Delta</th></tr></thead>
        <tbody>${Ht(s,o)}</tbody>
      </table>`:""}`:"",h=r?`
      <div class="corpus-report-grid">
        ${[{label:"Docs staged",key:"docs_staged"},{label:"Docs upserted",key:"docs_upserted"},{label:"Docs new",key:"docs_new"},{label:"Docs removed",key:"docs_removed"},{label:"Chunks new",key:"chunks_new"},{label:"Chunks changed",key:"chunks_changed"},{label:"Chunks removed",key:"chunks_removed"},{label:"Chunks unchanged",key:"chunks_unchanged"},{label:"Chunks embedded",key:"chunks_embedded"}].filter(D=>r[D.key]!==void 0&&r[D.key]!==null).map(D=>`
              <div class="corpus-report-stat">
                <span class="corpus-report-stat-value">${j(String(r[D.key]??"-"))}</span>
                <span class="corpus-report-stat-label">${j(D.label)}</span>
              </div>`).join("")}
      </div>`:"",R=Ls(e==null?void 0:e.started_at,e==null?void 0:e.completed_at);return`
    <div class="corpus-section corpus-report-section">
      <h4>Promotion Report</h4>
      ${A}
      ${h}
      ${R!=="-"?`<p class="corpus-report-duration">Duración: <strong>${j(R)}</strong></p>`:""}
    </div>`}function Kt({dom:e,setFlash:t}){let s=null,o=null,n=null,r="",m="",b=null,w=null,k=!1,A=!1,B=!1,h=!1,R=0,D=null,I=0;function N(F,U){o&&clearTimeout(o),t(F,U);const P=e.container.querySelector(".corpus-toast");P&&(P.hidden=!1,P.dataset.tone=U,P.textContent=F,P.classList.remove("corpus-toast-enter"),P.offsetWidth,P.classList.add("corpus-toast-enter")),o=setTimeout(()=>{const v=e.container.querySelector(".corpus-toast");v&&(v.hidden=!0)},6e3)}function y(F,U,P,v="promote"){return new Promise(K=>{w==null||w.remove();const M=document.createElement("div");M.className="corpus-confirm-overlay",w=M,M.innerHTML=`
        <div class="corpus-confirm-dialog">
          <h3 class="corpus-confirm-title">${j(F)}</h3>
          <div class="corpus-confirm-body">${U}</div>
          <div class="corpus-confirm-actions">
            <button class="corpus-btn corpus-btn-rollback" data-action="cancel">Cancelar</button>
            <button class="corpus-btn ${v==="rollback"?"corpus-btn-rollback":"corpus-btn-promote"}" data-action="confirm">${j(P)}</button>
          </div>
        </div>
      `,document.body.appendChild(M),requestAnimationFrame(()=>M.classList.add("is-visible"));function g(ce){w===M&&(w=null),M.classList.remove("is-visible"),setTimeout(()=>M.remove(),180),K(ce)}M.addEventListener("click",ce=>{const he=ce.target.closest("[data-action]");he?g(he.dataset.action==="confirm"):ce.target===M&&g(!1)})})}async function S(F,U,P,v){if(!r){r=P,O();try{const{response:K,data:M}=await je(F,U);K.ok&&(M!=null&&M.job_id)?(b={tone:"success",message:`${v} Job ${Le(M.job_id)}.`},N(`${v} Job ${Le(M.job_id)}.`,"success")):(b={tone:"error",message:(M==null?void 0:M.error)||"No se pudo iniciar la operación."},N((M==null?void 0:M.error)||"No se pudo iniciar la operación.","error"))}catch(K){const M=K instanceof Error?K.message:String(K);b={tone:"error",message:M},N(M,"error")}finally{r="",await re()}}}async function _(){const F=s;if(!F||r||!await y("Promote WIP to Production",`<p>This path reuses the live WIP generation and promotes it incrementally into Production with persisted checkpoints.</p>
       <table class="corpus-confirm-table">
         <tr><td>Production current:</td><td><strong>${ne(F.production.documents)}</strong> docs · <strong>${ne(F.production.chunks)}</strong> chunks</td></tr>
         <tr><td>WIP source:</td><td><strong>${ne(F.wip.documents)}</strong> docs · <strong>${ne(F.wip.chunks)}</strong> chunks</td></tr>
         <tr><td>WIP generation:</td><td><code>${j(Le(F.wip.generation_id))}</code></td></tr>
       </table>
       <label style="display:flex;align-items:center;gap:0.4rem;margin:0.75rem 0;font-size:0.85rem;cursor:pointer">
         <input type="checkbox" id="corpus-force-full-upsert" />
         Forzar upsert completo (sincronizar summaries + embeddings aunque chunk_text no haya cambiado)
       </label>
       <p class="corpus-confirm-note">The backend will keep a promotion plan, batch checkpoints, and a resumable cursor before activation.</p>`,"Promote now"))return;const P=document.querySelector("#corpus-force-full-upsert"),v=(P==null?void 0:P.checked)??!1;h=!1,R=0,D=null,I=0,await S("/api/ops/corpus/rebuild-from-wip",{mode:"promote",force_full_upsert:v},"promote",v?"Promotion started (force full upsert).":"Promotion started.")}async function c(){var P;const F=(s==null?void 0:s.current_operation)??(s==null?void 0:s.last_operation)??null;!(F!=null&&F.resume_job_id)||r||!await y("Resume from Checkpoint",`<p>The backend will reuse the persisted promotion plan and continue from the last completed checkpoint.</p>
       <table class="corpus-confirm-table">
         <tr><td>Job:</td><td><code>${j(Le(F.resume_job_id))}</code></td></tr>
         <tr><td>Checkpoint:</td><td>${j(wt(F))}</td></tr>
         <tr><td>Target generation:</td><td><code>${j(Le(F.target_generation_id))}</code></td></tr>
       </table>`,"Resume now")||(h=!0,R=((P=F.last_checkpoint)==null?void 0:P.cursor)??0,D=null,I=0,await S("/api/ops/corpus/rebuild-from-wip/resume",{job_id:F.resume_job_id},"resume","Resume started."))}async function C(){const F=s;!F||!F.rollback_generation_id||r||!await y("Rollback de Production",`<p>Se va a intentar reactivar una generación previa de production.</p>
       <table class="corpus-confirm-table">
         <tr><td>Production actual:</td><td><code>${j(Le(F.production.generation_id))}</code></td></tr>
         <tr><td>Objetivo:</td><td><code>${j(Le(F.rollback_generation_id))}</code></td></tr>
       </table>
       <p class="corpus-confirm-note">Solo se habilita si el backend detecta una generación previa todavía utilizable.</p>`,"Revertir ahora","rollback")||await S("/api/ops/corpus/rollback",{generation_id:F.rollback_generation_id},"rollback","Rollback started.")}async function q(){r||await S("/api/ops/corpus/wip-audit",{},"audit","WIP audit started.")}async function X(){r||!await y("Reiniciar promoción",`<p>Cancela cualquier job anterior y lanza una nueva promoción desde WIP a producción.</p>
       <label style="display:flex;align-items:center;gap:0.4rem;margin:0.75rem 0;font-size:0.85rem;cursor:default;opacity:0.55" title="Force upsert es obligatorio en reinicio">
         <input type="checkbox" checked disabled style="opacity:0.55" />
         Forzar upsert completo (sincronizar summaries + embeddings aunque chunk_text no haya cambiado)
       </label>
       <p class="corpus-confirm-note">Reiniciar siempre usa force upsert: todos los ~50K chunks se copian completos.</p>`,"Reiniciar ahora","rollback")||(h=!1,R=0,D=null,I=0,await S("/api/ops/corpus/rebuild-from-wip/restart",{},"restart","Restart submitted (force full upsert)."))}async function pe(){if(!(B||r||!await y("Sincronizar JSONL a WIP",`<p>Se va a sincronizar el índice JSONL local ya existente al Supabase WIP (Docker).</p>
       <p class="corpus-confirm-note">Esta operación no ejecuta reindex — solo sincroniza los documentos y chunks que ya existen en el JSONL local. Es segura e idempotente.</p>`,"Sincronizar ahora"))){B=!0,O();try{const{response:U,data:P}=await je("/api/ops/corpus/sync-to-wip",{});U.ok&&(P!=null&&P.synced)?N(`WIP sincronizado: ${ne(P.documents)} docs, ${ne(P.chunks)} chunks.`,"success"):N((P==null?void 0:P.error)||"Error sincronizando a WIP.","error")}catch(U){const P=U instanceof Error?U.message:String(U);N(P||"Error sincronizando a WIP.","error")}finally{B=!1,await re()}}}async function fe(){const F=(s==null?void 0:s.current_operation)??(s==null?void 0:s.last_operation)??null,U=String((F==null?void 0:F.log_tail)||"").trim();if(U)try{await navigator.clipboard.writeText(U),N("Log tail copied.","success")}catch(P){const v=P instanceof Error?P.message:"Could not copy log tail.";N(v||"Could not copy log tail.","error")}}function O(){var Se,$e,W,Ee,Ne,Ie,Pe,Re,ve,Me,qe;const F=e.container.querySelector(".corpus-log-accordion");F&&(k=F.open);const U=e.container.querySelector(".corpus-checks-accordion");U&&(A=U.open);const P=s;if(!P){e.container.innerHTML=`<p class="ops-empty">${j(m||"Cargando estado del corpus…")}</p>`;return}const v=P.current_operation??P.last_operation??null,K=Is(v,P),M=!!(P.current_operation&&["queued","running"].includes(P.current_operation.status))||!!r,g=M||!P.preflight_ready,ce=!M&&!!(v&&v.resume_supported&&v.resume_job_id&&(v.operation_state_code==="stalled_resumable"||v.operation_state_code==="failed_resumable")),he=M||!P.rollback_available,E=P.delta.documents==="+0"&&P.delta.chunks==="+0"?"Sin delta pendiente":`${P.delta.documents} documentos · ${P.delta.chunks} chunks`,L=Bt(v==null?void 0:v.checks,{onlyFailures:!0}),Y=Bt(v==null?void 0:v.checks),z=!!(P.current_operation&&["queued","running"].includes(P.current_operation.status)),ie=b&&!(P.current_operation&&["queued","running"].includes(P.current_operation.status))?`
          <div class="corpus-callout tone-${j(b.tone==="success"?"green":"red")}">
            <strong>${b.tone==="success"?"Request sent":"Request failed"}</strong>
            <span>${j(b.message)}</span>
          </div>`:"",ee=(Se=v==null?void 0:v.last_checkpoint)!=null&&Se.phase?(()=>{const ge=v.operation_state_code==="completed"?"green":v.operation_state_code==="failed_resumable"||v.operation_state_code==="stalled_resumable"?"red":"yellow",me=jt(v);return`
            <div class="corpus-callout tone-${j(ge)}">
              <strong>Checkpoint</strong>
              <span>${j(wt(v))} · ${j(Ot(v.last_checkpoint.at||null))}</span>
              ${me>0&&ge!=="green"?`<div class="corpus-progress-bar corpus-progress-bar-sm"><div class="corpus-progress-fill" style="width:${me.toFixed(1)}%"></div></div>`:""}
            </div>`})():"";e.container.innerHTML=`
      <div class="corpus-cards">
        ${Dt("WIP",P.wip)}
        ${Dt("PRODUCTION",P.production)}
      </div>
      <div class="corpus-delta">
        <span class="corpus-delta-label">${j(E)}</span>
      </div>
      <section class="corpus-operation-panel severity-${j(K.severity)}">
        <div class="corpus-operation-header">
          <div>
            <div class="corpus-status-chip tone-${j(K.severity)}${K.severity==="yellow"?" is-pulsing":""}">
              ${j(K.title)}
            </div>
            <h3 class="corpus-operation-title">${j(Ts(v))}</h3>
            <p class="corpus-operation-detail">${j(K.detail)}</p>
          </div>
          <dl class="corpus-operation-meta">
            <div><dt>Heartbeat</dt><dd>${j(Ot((v==null?void 0:v.heartbeat_at)||(v==null?void 0:v.updated_at)||null))}</dd></div>
            <div><dt>Backend</dt><dd>${j(xs(v))}${v!=null&&v.force_full_upsert?` <span style="background:${qt.amber[100]};color:${qt.amber[600]};padding:0.1rem 0.4rem;border-radius:0.3rem;font-size:0.7rem;font-weight:700">FORCE UPSERT</span>`:""}</dd></div>
            <div><dt>Phase</dt><dd>${j(v!=null&&v.current_phase?bt(v.current_phase):(v==null?void 0:v.stage_label)||(P.preflight_ready?"Ready":"Blocked"))}</dd></div>
            <div><dt>Checkpoint</dt><dd>${j(wt(v))}</dd></div>
            <div><dt>WIP</dt><dd><code>${j(Le((v==null?void 0:v.source_generation_id)||P.wip.generation_id))}</code></dd></div>
            <div><dt>Target</dt><dd><code>${j(Le((v==null?void 0:v.target_generation_id)||(v==null?void 0:v.production_generation_id)||P.production.generation_id))}</code></dd></div>
            <div><dt>Prod</dt><dd><code>${j(Le((v==null?void 0:v.production_generation_id)||P.production.generation_id))}</code></dd></div>
          </dl>
        </div>
        ${z?(()=>{var He,de;const ge=jt(v),me=((He=v==null?void 0:v.last_checkpoint)==null?void 0:He.cursor)??(v==null?void 0:v.batch_cursor)??0,Xe=((de=v==null?void 0:v.last_checkpoint)==null?void 0:de.total)??0,Fe=Ns(v);if(me>0&&Xe>0){const be=Date.now();if(D&&me>D.cursor){const Oe=Math.max(1,(be-D.ts)/1e3),Z=(me-D.cursor)/Oe;I=I>0?I*.7+Z*.3:Z}D={cursor:me,ts:be}}const Ze=I>0?`${I.toFixed(0)} chunks/s`:"",Qe=Xe-me,et=I>0&&Qe>0?(()=>{const be=Math.ceil(Qe/I),Oe=Math.floor(be/60),Z=be%60;return Oe>0?`~${Oe}m ${Z}s restante`:`~${Z}s restante`})():"";return`
            <div class="corpus-progress-bar"><div class="corpus-progress-fill" style="width:${ge.toFixed(1)}%"></div></div>
            <div class="corpus-progress-detail">
              ${h?`<span class="corpus-resume-badge">REANUDADO desde ${ne(R)}</span>`:""}
              <span class="corpus-progress-nums">${ne(me)} / ${ne(Xe)} (${ge.toFixed(1)}%)</span>
              ${Ze?`<span class="corpus-progress-rate">${j(Ze)}</span>`:""}
              ${et?`<span class="corpus-progress-eta">${j(et)}</span>`:""}
              <span class="corpus-hb-badge ${Fe.className}">${j(Fe.label)}</span>
            </div>`})():""}
        ${($e=v==null?void 0:v.stages)!=null&&$e.length?Ps(v.stages):""}
        ${ee}
        ${(W=P.preflight_reasons)!=null&&W.length&&!z&&!P.preflight_ready?`
          <div class="corpus-callout tone-red">
            <strong>Preflight blocked</strong>
            <ul>${P.preflight_reasons.map(ge=>`<li>${j(ge)}</li>`).join("")}</ul>
          </div>`:""}
        ${ie}
        ${L?`<div class="corpus-section"><h4>Visible failures</h4>${L}</div>`:""}
        ${Y?`
          <details class="corpus-section corpus-checks-accordion">
            <summary class="corpus-checks-summary"><h4>Checks</h4><span class="corpus-checks-count">${((v==null?void 0:v.checks)??[]).length}</span></summary>
            ${Y}
          </details>`:""}
        ${As(v)}
        ${v!=null&&v.log_tail?`
          <details class="corpus-section corpus-log-accordion">
            <summary class="corpus-log-summary">
              <h4>Backend log tail</h4>
              <button id="corpus-copy-log-tail-btn" type="button" class="corpus-btn corpus-btn-rollback corpus-btn-inline">Copy</button>
            </summary>
            <pre class="corpus-log-tail">${j(v.log_tail)}</pre>
          </details>`:""}
        ${m?`
          <div class="corpus-callout tone-red">
            <strong>Refresh error</strong>
            <span>${j(m)}</span>
          </div>`:""}
      </section>
      <div class="corpus-actions">
        ${P.audit_missing&&!M?`
          <button id="corpus-audit-btn" class="corpus-btn corpus-btn-audit${r==="audit"?" is-busy":""}">
            ${r==="audit"?'<span class="corpus-spinner"></span> Auditing…':"Run WIP Audit"}
          </button>`:""}
        ${!M&&!B?`
          <button id="corpus-sync-wip-btn" class="corpus-btn corpus-btn-sync">Sincronizar JSONL a WIP</button>`:""}
        ${B?`
          <button class="corpus-btn corpus-btn-sync is-busy" disabled><span class="corpus-spinner"></span> Sincronizando…</button>`:""}
        <button id="corpus-promote-btn" class="corpus-btn corpus-btn-promote${r==="promote"?" is-busy":""}" ${g?"disabled":""}>
          ${r==="promote"?'<span class="corpus-spinner"></span> Starting…':"Promote WIP to Production"}
        </button>
        ${ce?`
          <button id="corpus-resume-btn" class="corpus-btn corpus-btn-promote${r==="resume"?" is-busy":""}">
            ${r==="resume"?'<span class="corpus-spinner"></span> Resuming…':"Resume from Checkpoint"}
          </button>`:""}
        <button id="corpus-rollback-btn" class="corpus-btn corpus-btn-rollback${r==="rollback"?" is-busy":""}" ${he?"disabled":""}>
          ${r==="rollback"?'<span class="corpus-spinner"></span> Starting rollback…':"Rollback"}
        </button>
        <button id="corpus-restart-btn" class="corpus-btn corpus-btn-rollback${r==="restart"?" is-busy":""}" ${M?"disabled":""}>
          ${r==="restart"?'<span class="corpus-spinner"></span> Restarting…':"Reiniciar promoción (force upsert)"}
        </button>
      </div>
      ${P.preflight_ready?"":`
        <p class="corpus-action-note">${j(((Ee=P.preflight_reasons)==null?void 0:Ee[0])||"Promotion is blocked by preflight.")}</p>`}
      ${P.rollback_available?"":`
        <p class="corpus-action-note">${j(P.rollback_reason||"Rollback is not available yet.")}</p>`}
      <div class="corpus-toast ops-flash" hidden></div>
    `,(Ne=e.container.querySelector("#corpus-audit-btn"))==null||Ne.addEventListener("click",q),(Ie=e.container.querySelector("#corpus-sync-wip-btn"))==null||Ie.addEventListener("click",()=>void pe()),(Pe=e.container.querySelector("#corpus-promote-btn"))==null||Pe.addEventListener("click",_),(Re=e.container.querySelector("#corpus-resume-btn"))==null||Re.addEventListener("click",c),(ve=e.container.querySelector("#corpus-rollback-btn"))==null||ve.addEventListener("click",C),(Me=e.container.querySelector("#corpus-restart-btn"))==null||Me.addEventListener("click",X),(qe=e.container.querySelector("#corpus-copy-log-tail-btn"))==null||qe.addEventListener("click",ge=>{ge.preventDefault(),ge.stopPropagation(),fe()});const te=e.container.querySelector(".corpus-log-accordion");te&&k&&(te.open=!0);const _e=e.container.querySelector(".corpus-checks-accordion");_e&&A&&(_e.open=!0)}async function re(){try{s=await Ae("/api/ops/corpus-status"),m="",s!=null&&s.current_operation&&["queued","running","completed","failed","cancelled"].includes(s.current_operation.status)&&(b=null)}catch(F){m=F instanceof Error?F.message:String(F),s===null&&(s=null)}O()}function ke(){O(),n===null&&(n=window.setInterval(()=>{re()},Ss))}return{bindEvents:ke,refresh:re}}const On=Object.freeze(Object.defineProperty({__proto__:null,createCorpusLifecycleController:Kt},Symbol.toStringTag,{value:"Module"})),Rs={normative_base:"Normativa",interpretative_guidance:"Interpretación",practica_erp:"Práctica"},It={declaracion_renta:"Renta",iva:"IVA",laboral:"Laboral",facturacion_electronica:"Facturación",estados_financieros_niif:"NIIF",ica:"ICA",calendario_obligaciones:"Calendarios",retencion_fuente:"Retención",regimen_sancionatorio:"Sanciones",regimen_cambiario:"Régimen Cambiario",impuesto_al_patrimonio:"Patrimonio",informacion_exogena:"Exógena",proteccion_de_datos:"Datos",obligaciones_mercantiles:"Mercantil",obligaciones_profesionales_contador:"Obligaciones Contador",rut_responsabilidades:"RUT",gravamen_movimiento_financiero_4x1000:"GMF 4×1000",beneficiario_final:"Beneficiario Final",contratacion_estatal:"Contratación Estatal",reforma_pensional:"Reforma Pensional",zomac_incentivos:"ZOMAC"},Xt="lia_backstage_ops_active_tab",Pt="lia_backstage_ops_ingestion_session_id";function Ms(){const e=vt();try{const t=String(e.getItem(Xt)||"").trim();return t==="ingestion"||t==="control"||t==="embeddings"||t==="reindex"?t:"monitor"}catch{return"monitor"}}function qs(e){const t=vt();try{t.setItem(Xt,e)}catch{}}function Os(){const e=vt();try{return String(e.getItem(Pt)||"").trim()}catch{return""}}function Ds(e){const t=vt();try{if(!e){t.removeItem(Pt);return}t.setItem(Pt,e)}catch{}}function ft(e){return e==="processing"||e==="running_batch_gates"}function Ut(e){if(!e)return!1;const t=String(e.status||"").toLowerCase();if(t==="done"||t==="completed")return!0;const s=e.documents||[];return s.length===0?!1:s.every(o=>{const n=String(o.status||"").toLowerCase();return n==="done"||n==="completed"||n==="skipped_duplicate"||n==="bounced"})}function lt(e){const t=String(e||"").trim().toLowerCase();return t==="failed"||t==="error"?"error":t==="processing"||t==="running_batch_gates"||t==="needs_retry_batch_gate"||t==="queued"||t==="uploading"||t==="extracting"||t==="etl"||t==="writing"||t==="gates"||t==="in_progress"||t==="partial_failed"||t==="raw"||t==="pending_dedup"?"warn":"ok"}function ue(e){return e instanceof nt?e.message||`HTTP ${e.status}`:e instanceof Error?e.message:String(e||"unknown_error")}function Bs(e,t){switch(String(e||"").trim()){case"normative_base":return t.t("ops.ingestion.batchType.normative");case"interpretative_guidance":return t.t("ops.ingestion.batchType.interpretative");case"practica_erp":return t.t("ops.ingestion.batchType.practical");default:return String(e||"-")}}function js(e,t){const s=Number(e||0);return!Number.isFinite(s)||s<=0?"0 B":s>=1024*1024?`${t.formatNumber(s/(1024*1024),{maximumFractionDigits:1})} MB`:s>=1024?`${t.formatNumber(s/1024,{maximumFractionDigits:1})} KB`:`${t.formatNumber(s)} B`}function zt(e,t){const s=e||{total:0,queued:0,done:0,failed:0,pending_batch_gate:0,bounced:0},o=[`${t.t("ops.ingestion.summary.total")} ${s.total||0}`,`${t.t("ops.ingestion.summary.done")} ${s.done||0}`,`${t.t("ops.ingestion.summary.failed")} ${s.failed||0}`,`${t.t("ops.ingestion.summary.queued")} ${s.queued||0}`,`${t.t("ops.ingestion.summary.gate")} ${s.pending_batch_gate||0}`],n=Number(s.bounced||0);return n>0&&o.push(`Rebotados ${n}`),o.join(" · ")}function xt(e,t,s){const o=e||t||"";if(!o)return"stalled";const n=Date.parse(o);if(Number.isNaN(n))return"stalled";const r=Date.now()-n,m=s==="gates",b=m?9e4:3e4,w=m?3e5:12e4;return r<b?"alive":r<w?"slow":"stalled"}function Fs(e,t){const s=e||t||"";if(!s)return"-";const o=Date.parse(s);if(Number.isNaN(o))return"-";const n=Math.max(0,Date.now()-o),r=Math.floor(n/1e3);if(r<5)return"ahora";if(r<60)return`hace ${r}s`;const m=Math.floor(r/60),b=r%60;return m<60?`hace ${m}m ${b}s`:`hace ${Math.floor(m/60)}h ${m%60}m`}const kt={validating:"validando corpus",manifest:"activando manifest",indexing:"reconstruyendo índice","indexing/scanning":"escaneando documentos","indexing/chunking":"generando chunks","indexing/writing_indexes":"escribiendo índices","indexing/syncing":"sincronizando Supabase","indexing/auditing":"auditando calidad"};function Yt(e){if(!e)return"";if(kt[e])return kt[e];const t=e.indexOf(":");if(t>0){const s=e.slice(0,t),o=e.slice(t+1),n=kt[s];if(n)return`${n} (${o})`}return e}function Hs(e){if(!e)return"";const t=Date.parse(e);if(Number.isNaN(t))return"";try{return new Intl.DateTimeFormat("es-CO",{timeZone:"America/Bogota",day:"2-digit",month:"2-digit",year:"numeric",hour:"2-digit",minute:"2-digit",second:"2-digit",hour12:!1}).format(new Date(t))}catch{return""}}function Zt(e,t){const s=Math.max(0,Math.min(100,Number(e||0))),o=document.createElement("div");o.className="ops-progress";const n=document.createElement("div");n.className="ops-progress-bar";const r=document.createElement("span");r.className="ops-progress-fill",t==="gates"&&s>0&&s<100&&r.classList.add("ops-progress-active"),r.style.width=`${s}%`;const m=document.createElement("span");return m.className="ops-progress-label",m.textContent=`${s}%`,n.appendChild(r),o.append(n,m),o}function De(e){return String(e??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#39;")}function Je(e){return(e??0).toLocaleString("es-CO")}function Wt(e){if(e==null||e<=0)return"-";const t=Math.floor(e/60),s=Math.floor(e%60);return t>0?`${t}m ${s}s`:`${s}s`}function Qt({dom:e,setFlash:t}){const{container:s}=e;let o=null,n="",r=!1,m=!1,b=0,w=0,k=3e3,A=[];function B(_){if(_<=0)return;const c=Date.now();if(_>b&&w>0){const C=c-w,q=_-b,X=C/q;A.push(X),A.length>10&&A.shift(),k=A.reduce((pe,fe)=>pe+fe,0)/A.length}_!==b&&(b=_,w=c)}function h(){if(w===0)return{level:"healthy",label:"Iniciando..."};const _=Date.now()-w,c=Math.max(k*3,1e4),C=Math.max(k*6,3e4);return _<c?{level:"healthy",label:"Saludable"}:_<C?{level:"caution",label:"Lento"}:{level:"failed",label:"Sin respuesta"}}function R(){var Y,z,ie,ee,te,_e,Se,$e;const _=o;if(!_){s.innerHTML='<p class="ops-text-muted">Cargando estado de embeddings...</p>';return}const c=_.current_operation||_.last_operation,C=((Y=_.current_operation)==null?void 0:Y.status)??"",q=C==="running"||C==="queued"||n==="start",X=!_.current_operation&&!n,pe=n==="stop",fe=!q&&!pe&&((c==null?void 0:c.status)==="cancelled"||(c==null?void 0:c.status)==="failed"||(c==null?void 0:c.status)==="stalled");let O="";const re=(c==null?void 0:c.status)??"",ke=pe?"Deteniendo...":q?"En ejecución":fe?re==="stalled"?"Detenido (stalled)":re==="cancelled"?"Cancelado":"Fallido":X?"Inactivo":re||"—",F=q?"tone-yellow":re==="completed"?"tone-green":re==="failed"||re==="stalled"?"tone-red":re==="cancelled"?"tone-yellow":"",U=_.api_health,P=U!=null&&U.ok?"emb-api-ok":"emb-api-error",v=U?U.ok?`API OK (${U.detail})`:`API Error: ${U.detail}`:"API: verificando...";if(O+=`<div class="emb-status-row">
      <span class="corpus-status-chip ${F}">${De(ke)}</span>
      <span class="emb-target-badge">WIP</span>
      <span class="emb-api-semaphore ${P}" title="${De(v)}"><span class="emb-api-dot"></span> ${De(U!=null&&U.ok?"API OK":U?"API Error":"...")}</span>
      ${q?(()=>{const W=h();return`<span class="emb-process-health emb-health-${W.level}"><span class="emb-health-dot"></span> ${De(W.label)}</span>`})():""}
    </div>`,O+='<div class="emb-controls">',X?(O+=`<label class="emb-force-label"><input type="checkbox" id="emb-force-check" ${r?"checked":""} /> Forzar re-embed (todas)</label>`,O+=`<button class="corpus-btn corpus-btn-promote" id="emb-start-btn" ${n?"disabled":""}>Iniciar</button>`):pe?O+='<span class="emb-running-label">Deteniendo al finalizar batch actual...</span>':q&&c&&(O+='<button class="corpus-btn corpus-btn-rollback" id="emb-stop-btn">Detener</button>',O+='<span class="emb-running-label">Embebiendo chunks...</span>'),fe&&c){const W=c.force,Ee=(z=c.progress)==null?void 0:z.last_cursor_id,Ne=(ie=c.progress)==null?void 0:ie.pct_complete,Ie=Ee?`Reanudar desde ${typeof Ne=="number"?Ne.toFixed(1)+"%":"checkpoint"}`:"Reiniciar";W&&(O+='<span class="emb-force-label"><input type="checkbox" checked disabled /> Forzar re-embed (continuación)</span>'),O+=`<button class="corpus-btn corpus-btn-promote" id="emb-resume-btn" ${n?"disabled":""}>${De(Ie)}</button>`,O+=`<button class="corpus-btn" id="emb-start-btn" ${n?"disabled":""} style="opacity:0.7">Iniciar desde cero</button>`}O+="</div>";const K=c==null?void 0:c.progress,M=(q||n)&&(K==null?void 0:K.total),g=M?K.total:_.total_chunks,ce=M?K.embedded:_.embedded_chunks,he=M?K.pending-K.embedded-(K.failed||0):_.null_embedding_chunks,E=M&&K.failed||0,L=M?K.pct_complete:_.coverage_pct;if(O+=`<div class="emb-stats-grid">
      <div class="emb-stat"><span class="emb-stat-value">${Je(g)}</span><span class="emb-stat-label">Total</span></div>
      <div class="emb-stat"><span class="emb-stat-value">${Je(ce)}</span><span class="emb-stat-label">Embebidos</span></div>
      <div class="emb-stat"><span class="emb-stat-value">${Je(Math.max(0,he))}</span><span class="emb-stat-label">Pendientes</span></div>
      ${E>0?`<div class="emb-stat emb-stat-error"><span class="emb-stat-value">${Je(E)}</span><span class="emb-stat-label">Fallidos</span></div>`:`<div class="emb-stat"><span class="emb-stat-value">${L.toFixed(1)}%</span><span class="emb-stat-label">Cobertura</span></div>`}
    </div>`,q&&(c!=null&&c.progress)){const W=c.progress;O+='<div class="emb-live-progress">',O+='<div class="emb-progress-bar-wrap" id="emb-progress-mount"></div>',O+=`<div class="emb-rate-line">
        <span>${((ee=W.rate_chunks_per_sec)==null?void 0:ee.toFixed(1))??"-"} chunks/s</span>
        <span>ETA: ${Wt(W.eta_seconds)}</span>
        <span>Elapsed: ${Wt(W.elapsed_seconds)}</span>
        <span>Batch ${Je(W.current_batch)} / ${Je(W.total_batches)}</span>
      </div>`,W.failed>0&&(O+=`<p class="emb-failed-notice">${Je(W.failed)} chunks fallidos (${(W.failed/Math.max(W.pending,1)*100).toFixed(2)}%)</p>`),O+="</div>"}if(c!=null&&c.quality_report){const W=c.quality_report;O+='<div class="emb-quality-report">',O+="<h3>Reporte de calidad</h3>",O+=`<div class="emb-stats-grid">
        <div class="emb-stat"><span class="emb-stat-value">${((te=W.mean_cosine_similarity)==null?void 0:te.toFixed(4))??"-"}</span><span class="emb-stat-label">Coseno medio</span></div>
        <div class="emb-stat"><span class="emb-stat-value">${((_e=W.min_cosine_similarity)==null?void 0:_e.toFixed(4))??"-"}</span><span class="emb-stat-label">Min</span></div>
        <div class="emb-stat"><span class="emb-stat-value">${((Se=W.max_cosine_similarity)==null?void 0:Se.toFixed(4))??"-"}</span><span class="emb-stat-label">Max</span></div>
        <div class="emb-stat"><span class="emb-stat-value">${Je(W.sample_pairs)}</span><span class="emb-stat-label">Pares</span></div>
      </div>`,W.collapsed_warning&&(O+='<p class="emb-anomaly-warning">ANOMALIA: Embeddings colapsados (mean &gt; 0.95)</p>'),W.noise_warning&&(O+='<p class="emb-anomaly-warning">ANOMALIA: Embeddings ruidosos (mean &lt; 0.10)</p>'),!W.collapsed_warning&&!W.noise_warning&&(O+='<p class="emb-quality-ok">Distribución saludable</p>'),O+="</div>"}if(($e=c==null?void 0:c.checks)!=null&&$e.length){O+='<div class="emb-checks">';for(const W of c.checks){const Ee=W.ok?'<span class="ops-dot ops-dot-ok">●</span>':'<span class="ops-dot ops-dot-error">●</span>';O+=`<div class="emb-check">${Ee} <strong>${De(W.label)}</strong>: ${De(W.detail)}</div>`}O+="</div>"}if(c!=null&&c.log_tail){const W=c.log_tail.split(`
`).reverse().join(`
`);O+=`<details class="emb-log-accordion" id="emb-log-details" ${m?"open":""}><summary>Log</summary><pre class="emb-log-tail">${De(W)}</pre></details>`}if(c!=null&&c.error&&(O+=`<p class="emb-error">${De(c.error)}</p>`),s.innerHTML=O,q&&(c!=null&&c.progress)){const W=s.querySelector("#emb-progress-mount");W&&W.appendChild(Zt(c.progress.pct_complete??0,"embedding"))}}function D(){s.addEventListener("click",_=>{const c=_.target;c.id==="emb-start-btn"&&I(),c.id==="emb-stop-btn"&&N(),c.id==="emb-resume-btn"&&y()}),s.addEventListener("change",_=>{const c=_.target;c.id==="emb-force-check"&&(r=c.checked)}),s.addEventListener("toggle",_=>{const c=_.target;c.id==="emb-log-details"&&(m=c.open)},!0)}async function I(){const _=r;n="start",r=!1,R();try{const{response:c,data:C}=await je("/api/ops/embedding/start",{force:_});!c.ok||!(C!=null&&C.ok)?(t((C==null?void 0:C.error)||`Error ${c.status}`,"error"),n=""):t("Embedding iniciado","success")}catch(c){t(String(c),"error"),n=""}await S()}async function N(){var c;const _=(c=o==null?void 0:o.current_operation)==null?void 0:c.job_id;if(_){n="stop",R();try{await je("/api/ops/embedding/stop",{job_id:_}),t("Stop solicitado — se detendrá al finalizar el batch actual","success")}catch(C){t(String(C),"error"),n=""}}}async function y(){const _=(o==null?void 0:o.current_operation)||(o==null?void 0:o.last_operation);if(_!=null&&_.job_id){n="start",R();try{const{response:c,data:C}=await je("/api/ops/embedding/resume",{job_id:_.job_id});!c.ok||!(C!=null&&C.ok)?(t((C==null?void 0:C.error)||`Error ${c.status}`,"error"),n=""):t("Embedding reanudado desde checkpoint","success")}catch(c){t(String(c),"error"),n=""}n="",await S()}}async function S(){try{const _=await Ae("/api/ops/embedding-status");o=_;const c=_.current_operation;if(c!=null&&c.progress){const C=c.progress.current_batch;typeof C=="number"&&B(C)}n==="stop"&&!_.current_operation&&(n=""),n==="start"&&_.current_operation&&(n=""),_.current_operation||(b=0,w=0,A=[])}catch{}R()}return{bindEvents:D,refresh:S}}const Dn=Object.freeze(Object.defineProperty({__proto__:null,createOpsEmbeddingsController:Qt},Symbol.toStringTag,{value:"Module"})),Us=["pending","processing","done"],zs={pending:"Pendiente",processing:"En proceso",done:"Procesado"},Ws={pending:"⏳",processing:"🔄",done:"✅"},Gs=5;function es(e){const t=String(e||"").toLowerCase();return t==="done"||t==="completed"||t==="skipped_duplicate"||t==="bounced"?"done":t==="in_progress"||t==="processing"||t==="extracting"||t==="etl"||t==="writing"||t==="gates"||t==="uploading"||t==="running_batch_gates"||t==="needs_retry_batch_gate"||t==="failed"||t==="error"||t==="partial_failed"?"processing":"pending"}function Js(e,t){const s=e.detected_topic||t.corpus||"",o=ss[s]||It[s]||s||"",n=e.detected_type||e.batch_type||"",r=Rs[n]||n||"",m=n==="normative_base"?"normative":n==="interpretative_guidance"?"interpretative":n==="practica_erp"?"practica":"unknown";let b="";return o&&(b+=`<span class="kanban-pill kanban-pill--topic" title="Tema: ${le(s)}">${we(o)}</span>`),r&&(b+=`<span class="kanban-pill kanban-pill--type-${m}" title="Tipo: ${le(n)}">${we(r)}</span>`),!o&&!r&&(b+='<span class="kanban-pill kanban-pill--unclassified">Sin clasificar</span>'),b}function Vs(e,t,s){var q;const o=lt(e.status),n=es(e.status),r=js(e.bytes,s),m=Number(e.progress||0),b=new Set(t.gate_pending_doc_ids||[]),w=n==="done"&&b.has(e.doc_id);let k;e.status==="bounced"?k='<span class="meta-chip status-bounced">↩ Ya existe en el corpus</span>':n==="done"&&e.derived_from_doc_id&&(e.delta_section_count||0)>0?k=`<span class="meta-chip status-ok">△ ${e.delta_section_count} secciones nuevas</span>`:n==="done"&&(e.status==="done"||e.status==="completed")?(k='<span class="meta-chip status-ok">✓ Documento listo</span>',w&&(k+='<span class="meta-chip status-gate-pending">Pendiente validación final</span>')):k=`<span class="meta-chip status-${o}">${we(e.status)}</span>`;const A=Js(e,t);let B="";if(e.status==="in_progress"||e.status==="processing"){const X=xt(e.heartbeat_at,e.updated_at,e.stage),pe=Fs(e.heartbeat_at,e.updated_at);B=`<div class="kanban-liveness ops-liveness-${X}">${pe}</div>`}let h="";e.stage==="gates"&&t.gate_sub_stage&&(h=`<div class="kanban-gate-sub">${Yt(t.gate_sub_stage)}</div>`);let R="";n==="processing"&&m>0&&(R=`<div class="kanban-progress" data-progress="${m}"></div>`);let D="";(q=e.error)!=null&&q.message&&(D=`<div class="kanban-error">${we(e.error.message)}</div>`);let I="";e.duplicate_of?I=`<div class="kanban-duplicate">Duplicado de: ${we(e.duplicate_of)}</div>`:e.derived_from_doc_id&&(I=`<div class="kanban-duplicate">Derivado de: ${we(e.derived_from_doc_id)}</div>`);let N="";if(n==="done"){const X=Hs(e.updated_at);X&&(N=`<div class="kanban-completed-at">Completado: ${we(X)}</div>`)}let y="";e.duplicate_of&&n!=="done"&&e.status!=="bounced"?y=en(e):n==="pending"&&(e.status==="raw"||e.status==="needs_classification")&&Xs(e)?y=Ys(e,s):n==="pending"&&(e.status==="raw"||e.status==="needs_classification")?y=Ks(e,s,t):n==="processing"&&(e.status==="failed"||e.status==="error"||e.status==="partial_failed")&&(y=tn(e));let S="",_="";(n!=="pending"||e.status==="queued")&&(S=Zs(),_=Qs(e,t,s));const C=e.stage&&e.stage!==e.status&&n==="processing";return`
    <div class="kanban-card kanban-card--${o}" data-doc-id="${le(e.doc_id)}">
      <div class="kanban-card-head">
        <span class="kanban-card-title" title="${le(e.doc_id)}">${we(e.filename||e.doc_id)}</span>
        ${k}
      </div>
      ${e.source_relative_path?`<div class="kanban-card-relpath" title="${le(e.source_relative_path)}">${we(nn(e.source_relative_path))}</div>`:""}
      <div class="kanban-card-pills-row">
        ${A}
        <span class="kanban-card-size">${r}</span>
        ${S}
      </div>
      ${_}
      ${C?`<div class="kanban-card-stage">${we(e.stage)}</div>`:""}
      ${B}
      ${h}
      ${R}
      ${N}
      ${I}
      ${D}
      ${y}
    </div>
  `}function Ks(e,t,s){const o=e.detected_type||e.batch_type||"",n=e.detected_topic||(s==null?void 0:s.corpus)||"",r=m=>m===o?" selected":"";return`
    <div class="kanban-actions kanban-classify-actions">
      <label class="kanban-action-field">
        <span>Tema</span>
        <select data-field="topic" class="kanban-select">
          ${ht(n)}
        </select>
      </label>
      <label class="kanban-action-field">
        <span>Tipo</span>
        <select data-field="type" class="kanban-select">
          <option value="">Seleccionar...</option>
          <option value="normative_base"${r("normative_base")}>${t.t("ops.ingestion.batchType.normative")}</option>
          <option value="interpretative_guidance"${r("interpretative_guidance")}>${t.t("ops.ingestion.batchType.interpretative")}</option>
          <option value="practica_erp"${r("practica_erp")}>${t.t("ops.ingestion.batchType.practical")}</option>
        </select>
      </label>
      <div class="kanban-action-field kanban-action-field--btn">
        <span>&nbsp;</span>
        <button class="btn btn--sm btn--primary kanban-assign-btn" data-action="assign" data-doc-id="${le(e.doc_id)}">Asignar</button>
      </div>
    </div>
  `}function Xs(e){return!!(e.autogenerar_label&&(e.autogenerar_is_new||e.autogenerar_resolved_topic))}function Ys(e,t){const s=e.detected_type||e.batch_type||"",o=k=>k===s?" selected":"",n=`
    <label class="kanban-action-field">
      <span>Tipo</span>
      <select data-field="type" class="kanban-select">
        <option value="">Seleccionar...</option>
        <option value="normative_base"${o("normative_base")}>${t.t("ops.ingestion.batchType.normative")}</option>
        <option value="interpretative_guidance"${o("interpretative_guidance")}>${t.t("ops.ingestion.batchType.interpretative")}</option>
        <option value="practica_erp"${o("practica_erp")}>${t.t("ops.ingestion.batchType.practical")}</option>
      </select>
    </label>`;if(e.autogenerar_is_new)return`
      <div class="kanban-actions kanban-autogenerar-actions kanban-autogenerar--new">
        <div class="kanban-autogenerar-header">Nuevo tema detectado</div>
        <label class="kanban-action-field">
          <span>Tema</span>
          <input type="text" class="kanban-input" data-field="autogenerar-label"
            value="${le(e.autogenerar_label||"")}" />
        </label>
        ${e.autogenerar_rationale?`<div class="kanban-autogenerar-rationale">${we(e.autogenerar_rationale)}</div>`:""}
        ${n}
        <div class="kanban-action-buttons">
          <button class="btn btn--sm btn--primary" data-action="accept-new-topic" data-doc-id="${le(e.doc_id)}">Aceptar nuevo tema</button>
          <button class="btn btn--sm kanban-ag-fallback-btn" data-action="show-existing-dropdown" data-doc-id="${le(e.doc_id)}">Asignar existente</button>
        </div>
        <div class="kanban-ag-fallback-panel" hidden>
          <label class="kanban-action-field">
            <span>Tema existente</span>
            <select data-field="topic" class="kanban-select">
              ${ht("")}
            </select>
          </label>
          <div class="kanban-action-field kanban-action-field--btn">
            <span>&nbsp;</span>
            <button class="btn btn--sm btn--primary kanban-assign-btn" data-action="assign" data-doc-id="${le(e.doc_id)}">Asignar</button>
          </div>
        </div>
      </div>
    `;const r=e.autogenerar_resolved_topic||"",m=It[r]||r,b=e.autogenerar_synonym_confidence??0,w=Math.round(b*100);return`
    <div class="kanban-actions kanban-autogenerar-actions kanban-autogenerar--synonym">
      <div class="kanban-autogenerar-header">Tema sugerido: <strong>${we(m)}</strong> <span class="kanban-autogenerar-conf">(${w}%)</span></div>
      <div class="kanban-autogenerar-source">Basado en: "${we(e.autogenerar_label||"")}"</div>
      ${n}
      <div class="kanban-action-buttons">
        <button class="btn btn--sm btn--primary" data-action="accept-synonym" data-doc-id="${le(e.doc_id)}">Aceptar</button>
        <button class="btn btn--sm kanban-ag-fallback-btn" data-action="show-existing-dropdown" data-doc-id="${le(e.doc_id)}">Cambiar</button>
      </div>
      <div class="kanban-ag-fallback-panel" hidden>
        <label class="kanban-action-field">
          <span>Tema</span>
          <select data-field="topic" class="kanban-select">
            ${ht(r)}
          </select>
        </label>
        <div class="kanban-action-field kanban-action-field--btn">
          <span>&nbsp;</span>
          <button class="btn btn--sm btn--primary kanban-assign-btn" data-action="assign" data-doc-id="${le(e.doc_id)}">Asignar</button>
        </div>
      </div>
    </div>
  `}function Zs(){return'<button class="kanban-reclassify-toggle" type="button" title="Cambiar clasificación">✎</button>'}function Qs(e,t,s){const o=e.detected_topic||t.corpus||"",n=e.detected_type||e.batch_type||"",r=(m,b)=>m===b?" selected":"";return`
    <div class="kanban-reclassify-panel" hidden>
      <label class="kanban-action-field">
        <span>Tema</span>
        <select data-field="topic" class="kanban-select">
          ${ht(o)}
        </select>
      </label>
      <label class="kanban-action-field">
        <span>Tipo</span>
        <select data-field="type" class="kanban-select">
          <option value="">Seleccionar...</option>
          <option value="normative_base"${r("normative_base",n)}>${s.t("ops.ingestion.batchType.normative")}</option>
          <option value="interpretative_guidance"${r("interpretative_guidance",n)}>${s.t("ops.ingestion.batchType.interpretative")}</option>
          <option value="practica_erp"${r("practica_erp",n)}>${s.t("ops.ingestion.batchType.practical")}</option>
        </select>
      </label>
      <div class="kanban-action-field kanban-action-field--btn">
        <span>&nbsp;</span>
        <button class="btn btn--sm btn--primary kanban-assign-btn" data-action="assign" data-doc-id="${le(e.doc_id)}">Asignar</button>
      </div>
    </div>
  `}function en(e){return`
    <div class="kanban-actions">
      <button class="btn btn--sm btn--primary" data-action="replace-dup" data-doc-id="${le(e.doc_id)}">Reemplazar</button>
      <button class="btn btn--sm" data-action="add-new-dup" data-doc-id="${le(e.doc_id)}">Agregar nuevo</button>
      <button class="btn btn--sm btn--danger" data-action="discard-dup" data-doc-id="${le(e.doc_id)}">Descartar</button>
    </div>
  `}function tn(e){return`
    <div class="kanban-actions">
      <button class="btn btn--sm" data-action="retry" data-doc-id="${le(e.doc_id)}">Reintentar</button>
      <button class="btn btn--sm btn--danger" data-action="discard" data-doc-id="${le(e.doc_id)}">Descartar</button>
    </div>
  `}const ts=[["declaracion_renta","Renta"],["iva","IVA"],["laboral","Laboral"],["facturacion_electronica","Facturación"],["estados_financieros_niif","NIIF"],["ica","ICA"],["calendario_obligaciones","Calendarios"],["retencion_fuente","Retención"],["regimen_sancionatorio","Sanciones"],["regimen_cambiario","Régimen Cambiario"],["impuesto_al_patrimonio","Patrimonio"],["informacion_exogena","Exógena"],["proteccion_de_datos","Datos"],["obligaciones_mercantiles","Mercantil"],["obligaciones_profesionales_contador","Obligaciones Contador"],["rut_responsabilidades","RUT"],["gravamen_movimiento_financiero_4x1000","GMF 4×1000"],["beneficiario_final","Beneficiario Final"],["contratacion_estatal","Contratación Estatal"],["reforma_pensional","Reforma Pensional"],["zomac_incentivos","ZOMAC"]];function sn(e){const t=new Set,s=[];for(const[o,n]of ts)t.add(o),s.push([o,n]);for(const o of e)!o.key||t.has(o.key)||(t.add(o.key),s.push([o.key,o.label||o.key]));return s}let Nt=ts,ss={...It};function ht(e=""){let t='<option value="">Seleccionar...</option>';for(const[s,o]of Nt){const n=s===e?" selected":"";t+=`<option value="${le(s)}"${n}>${we(o)}</option>`}return t}function we(e){const t=document.createElement("span");return t.textContent=e,t.innerHTML}function le(e){return e.replace(/&/g,"&amp;").replace(/"/g,"&quot;").replace(/'/g,"&#39;").replace(/</g,"&lt;").replace(/>/g,"&gt;")}function nn(e){const t=e.replace(/\/[^/]+$/,"").split("/").filter(Boolean);return t.length<=2?t.join("/")+"/":"…/"+t.slice(-2).join("/")+"/"}function an(e,t,s,o,n){n&&n.length>0&&(Nt=sn(n),ss=Object.fromEntries(Nt));const r=[...e.documents||[]].sort((y,S)=>Date.parse(String(S.updated_at||0))-Date.parse(String(y.updated_at||0))),m={pending:[],processing:[],done:[]};for(const y of r){const S=es(y.status);m[S].push(y)}m.pending.sort((y,S)=>{const _=y.status==="raw"||y.status==="needs_classification"?0:1,c=S.status==="raw"||S.status==="needs_classification"?0:1;return _!==c?_-c:Date.parse(String(S.updated_at||0))-Date.parse(String(y.updated_at||0))});const b=e.status==="running_batch_gates",w=e.gate_sub_stage||"";let k="";if(b){const y=w?Yt(w):"Preparando...";k=`
      <div class="kanban-validation-banner kanban-validation-banner--running">
        <span class="kanban-validation-spinner"></span>
        <span>Validación final en curso — ${we(y)}</span>
      </div>`}else e.status==="needs_retry_batch_gate"?k=`
      <div class="kanban-validation-banner kanban-validation-banner--error">
        <span>⚠ Validación final fallida — use Reintentar o Validar lote</span>
      </div>`:e.status==="completed"&&e.wip_sync_status==="skipped"&&(k=`
      <div class="kanban-validation-banner kanban-validation-banner--warn">
        <span>⚠ Ingesta completada solo localmente — WIP Supabase no estaba disponible. Use Operaciones → Sincronizar a WIP.</span>
      </div>`);let A="";const B=m.processing.length;for(const y of Us){const S=m[y],_=y==="processing"?`<span class="kanban-column-count">${B}</span><span class="kanban-column-limit">/ ${Gs}</span>`:`<span class="kanban-column-count">${S.length}</span>`,c=S.length===0?'<div class="kanban-column-empty">Sin documentos</div>':S.map(q=>Vs(q,e,s)).join(""),C=y==="done"?k:"";A+=`
      <div class="kanban-column kanban-column--${y}">
        <div class="kanban-column-header">
          <span class="kanban-column-icon">${Ws[y]}</span>
          <span class="kanban-column-label">${zs[y]}</span>
          ${_}
        </div>
        <div class="kanban-column-cards">
          ${C}
          ${c}
        </div>
      </div>
    `}const h={};t.querySelectorAll(".kanban-column").forEach(y=>{const S=y.classList[1]||"",_=y.querySelector(".kanban-column-cards");S&&_&&(h[S]=_.scrollTop)});const R=[];let D=t;for(;D;)D.scrollTop>0&&R.push([D,D.scrollTop]),D=D.parentElement;const I={};t.querySelectorAll(".kanban-reclassify-panel").forEach(y=>{var S,_;if(!y.hasAttribute("hidden")){const c=y.closest("[data-doc-id]"),C=(c==null?void 0:c.dataset.docId)||"";if(C&&!(o!=null&&o.has(C))){const q=((S=y.querySelector("[data-field='topic']"))==null?void 0:S.value)||"",X=((_=y.querySelector("[data-field='type']"))==null?void 0:_.value)||"";I[C]={topic:q,type:X}}}});const N={};t.querySelectorAll(".kanban-classify-actions").forEach(y=>{var c,C;const S=y.closest("[data-doc-id]"),_=(S==null?void 0:S.dataset.docId)||"";if(_){const q=((c=y.querySelector("[data-field='topic']"))==null?void 0:c.value)||"",X=((C=y.querySelector("[data-field='type']"))==null?void 0:C.value)||"";(q||X)&&(N[_]={topic:q,type:X})}}),t.innerHTML=A;for(const[y,S]of R)y.scrollTop=S;t.querySelectorAll(".kanban-column").forEach(y=>{const S=y.classList[1]||"",_=y.querySelector(".kanban-column-cards");S&&h[S]&&_&&(_.scrollTop=h[S])});for(const[y,S]of Object.entries(I)){const _=t.querySelector(`[data-doc-id="${CSS.escape(y)}"]`);if(!_)continue;const c=_.querySelector(".kanban-reclassify-toggle"),C=_.querySelector(".kanban-reclassify-panel");if(c&&C){C.removeAttribute("hidden"),c.textContent="✖";const q=C.querySelector("[data-field='topic']"),X=C.querySelector("[data-field='type']");q&&S.topic&&(q.value=S.topic),X&&S.type&&(X.value=S.type)}}for(const[y,S]of Object.entries(N)){const _=t.querySelector(`[data-doc-id="${CSS.escape(y)}"]`);if(!_)continue;const c=_.querySelector(".kanban-classify-actions");if(!c)continue;const C=c.querySelector("[data-field='topic']"),q=c.querySelector("[data-field='type']");C&&S.topic&&(C.value=S.topic),q&&S.type&&(q.value=S.type)}t.querySelectorAll(".kanban-progress").forEach(y=>{var C,q;const S=Number(y.dataset.progress||0),_=((q=(C=y.closest(".kanban-card"))==null?void 0:C.querySelector(".kanban-card-stage"))==null?void 0:q.textContent)||void 0,c=Zt(S,_);y.replaceWith(c)}),t.querySelectorAll(".kanban-reclassify-toggle").forEach(y=>{y.addEventListener("click",()=>{const S=y.closest(".kanban-card"),_=S==null?void 0:S.querySelector(".kanban-reclassify-panel");if(!_)return;_.hasAttribute("hidden")?(_.removeAttribute("hidden"),y.textContent="✖"):(_.setAttribute("hidden",""),y.textContent="✎")})})}async function Ce(e,t){const s=await fetch(e,t);let o=null;try{o=await s.json()}catch{o=null}if(!s.ok){const n=o&&typeof o=="object"&&"error"in o?String(o.error||s.statusText):s.statusText;throw new nt(n,s.status,o)}return o}async function St(e,t){const{response:s,data:o}=await je(e,t);if(!s.ok){const n=o&&typeof o=="object"&&"error"in o?String(o.error||s.statusText):s.statusText;throw new nt(n,s.status,o)}return o}const on=new Set([".pdf",".md",".txt",".docx"]),rn=[".","__MACOSX"],Ct=3,Et="lia_folder_pending_";function rt(e){return e.filter(t=>{const s=t.name;if(rn.some(r=>s.startsWith(r)))return!1;const o=s.lastIndexOf("."),n=o>=0?s.slice(o).toLowerCase():"";return on.has(n)})}function ct(e,t){return e.webkitRelativePath||t.get(e)||""}function Ve(e,t){const s=ct(e,t);return`${e.name}|${e.size}|${e.lastModified??0}|${s}`}function cn(e){return e<1024?`${e} B`:e<1024*1024?`${(e/1024).toFixed(1)} KB`:`${(e/(1024*1024)).toFixed(1)} MB`}function ln(e,t){var o;const s=((o=e.preflightEntry)==null?void 0:o.existing_doc_id)||"";switch(e.verdict){case"pending":return t.t("ops.ingestion.verdict.pending");case"new":return t.t("ops.ingestion.verdict.new");case"revision":return s?t.t("ops.ingestion.verdict.revisionOf",{docId:s}):t.t("ops.ingestion.verdict.revision");case"duplicate":return s?t.t("ops.ingestion.verdict.duplicateOf",{docId:s}):t.t("ops.ingestion.verdict.duplicate");case"artifact":return t.t("ops.ingestion.verdict.artifact");case"unreadable":return t.t("ops.ingestion.verdict.unreadable")}}function dn(e,t){const s=document.createElement("span");return s.className=`ops-verdict-pill ops-verdict-pill--${e.verdict}`,s.textContent=ln(e,t),s}function mt(e){return e.documents.filter(t=>t.status==="raw"||t.status==="needs_classification").length}function un({i18n:e,stateController:t,dom:s,withThinkingWheel:o,setFlash:n}){const{ingestionCorpusSelect:r,ingestionBatchTypeSelect:m,ingestionDropzone:b,ingestionFileInput:w,ingestionFolderInput:k,ingestionSelectFilesBtn:A,ingestionSelectFolderBtn:B,ingestionUploadProgress:h,ingestionPendingFiles:R,ingestionOverview:D,ingestionRefreshBtn:I,ingestionCreateSessionBtn:N,ingestionUploadBtn:y,ingestionProcessBtn:S,ingestionAutoProcessBtn:_,ingestionValidateBatchBtn:c,ingestionRetryBtn:C,ingestionDeleteSessionBtn:q,ingestionSessionMeta:X,ingestionSessionsList:pe,selectedSessionMeta:fe,ingestionLastError:O,ingestionLastErrorMessage:re,ingestionLastErrorGuidance:ke,ingestionLastErrorNext:F,ingestionKanban:U,ingestionLogAccordion:P,ingestionLogBody:v,ingestionLogCopyBtn:K,ingestionAutoStatus:M}=s,{state:g}=t,ce=hs(e);let he=[];function E(a){const u=`[${new Date().toISOString().slice(11,23)}] ${a}`;he.push(u),console.log(`[folder-ingest] ${a}`),P.hidden=!1,v.hidden=!1,v.textContent=he.join(`
`);const f=document.getElementById("ingestion-log-toggle");if(f){f.setAttribute("aria-expanded","true");const l=f.querySelector(".ops-log-accordion-marker");l&&(l.textContent="▾")}}function L(){he=[],Y()}function Y(){const{ingestionBounceLog:a,ingestionBounceBody:i}=s;a&&(a.hidden=!0,a.open=!1),i&&(i.textContent="")}let z=!1,ie=null;const ee=150;function te(a){if(a.length===0)return;const i=new Set(g.intake.map(f=>Ve(f.file))),u=[];for(const f of a){const l=Ve(f,g.folderRelativePaths);i.has(l)||(i.add(l),u.push({file:f,relativePath:ct(f,g.folderRelativePaths),contentHash:null,verdict:"pending",preflightEntry:null}))}u.length!==0&&(t.setIntake([...g.intake,...u]),g.reviewPlan&&t.setReviewPlan({...g.reviewPlan,stalePartial:!0}),z=!1,_e(),ae())}function _e(){ie&&clearTimeout(ie);const a=t.bumpPreflightRunId();ie=setTimeout(()=>{ie=null,Se(a)},ee)}async function Se(a){if(a!==g.preflightRunId||g.intake.length===0)return;const i=g.intake.filter(u=>u.contentHash===null);try{if(i.length>0&&(await $e(i),a!==g.preflightRunId))return;const u=await W();if(a!==g.preflightRunId)return;if(!u){z=!0,ae();return}Ee(u),z=!1,ae()}catch(u){if(a!==g.preflightRunId)return;console.error("[intake] preflight failed:",u),z=!0,ae()}}async function $e(a){t.setPreflightScanProgress({total:a.length,hashed:0,scanning:!0}),Mt();for(let i=0;i<a.length;i++){const u=a[i];try{const f=await u.file.arrayBuffer(),l=await crypto.subtle.digest("SHA-256",f),p=Array.from(new Uint8Array(l));u.contentHash=p.map(d=>d.toString(16).padStart(2,"0")).join("")}catch(f){console.warn(`[intake] hash failed for ${u.file.name}:`,f),u.verdict="unreadable",u.contentHash=""}t.setPreflightScanProgress({total:a.length,hashed:i+1,scanning:!0}),Mt()}t.setPreflightScanProgress(null)}async function W(){const a=g.intake.filter(i=>i.contentHash&&i.verdict!=="unreadable").map(i=>({filename:i.file.name,relative_path:i.relativePath||i.file.name,size:i.file.size,content_hash:i.contentHash}));if(a.length===0)return{artifacts:[],duplicates:[],revisions:[],new_files:[],scanned:0,elapsed_ms:0};try{return await gs(a,g.selectedCorpus)}catch(i){return console.error("[intake] /api/ingestion/preflight failed:",i),null}}function Ee(a){const i=new Map,u=(d,$)=>{for(const x of $){const T=x.relative_path||x.filename;i.set(T,{verdict:d,preflightEntry:x})}};u("new",a.new_files),u("revision",a.revisions),u("duplicate",a.duplicates),u("artifact",a.artifacts);const f=g.intake.map(d=>{if(d.verdict==="unreadable")return d;const $=d.relativePath||d.file.name,x=i.get($);return x?{...d,verdict:x.verdict,preflightEntry:x.preflightEntry}:{...d,verdict:"pending"}}),l=f.filter(d=>d.verdict==="new"||d.verdict==="revision"),p=f.filter(d=>d.verdict==="duplicate"||d.verdict==="artifact"||d.verdict==="unreadable");t.setIntake(f),t.setReviewPlan({willIngest:l,bounced:p,scanned:a.scanned,elapsedMs:a.elapsed_ms,stalePartial:!1}),t.setPendingFiles(l.map(d=>d.file))}function Ne(a){const i=u=>Ve(u.file)!==Ve(a.file);if(t.setIntake(g.intake.filter(i)),g.reviewPlan){const u=g.reviewPlan.willIngest.filter(i);t.setReviewPlan({...g.reviewPlan,willIngest:u}),t.setPendingFiles(u.map(f=>f.file))}else t.setPendingFiles(g.pendingFiles.filter(u=>Ve(u)!==Ve(a.file)));ae()}function Ie(){if(!g.reviewPlan)return;const a=new Set(g.reviewPlan.willIngest.map(u=>Ve(u.file))),i=g.intake.filter(u=>!a.has(Ve(u.file)));t.setIntake(i),t.setReviewPlan({...g.reviewPlan,willIngest:[]}),t.setPendingFiles([]),ae()}function Pe(){ie&&(clearTimeout(ie),ie=null),t.bumpPreflightRunId(),t.setIntake([]),t.setReviewPlan(null),t.setPendingFiles([]),t.setPreflightScanProgress(null),z=!1,g.folderRelativePaths.clear()}async function Re(){const a=g.reviewPlan;if(a&&!a.stalePartial&&a.willIngest.length!==0&&!z){n(),t.setMutating(!0),Z();try{await ms(),Pe(),k.value="",w.value=""}catch(i){t.setFolderUploadProgress(null),Fe(),n(ue(i),"error"),g.selectedSessionId&&Ge({sessionId:g.selectedSessionId,showWheel:!1,reportError:!1})}finally{t.setMutating(!1),Z()}}}const ve=new Set;function Me(){const a=g.selectedCorpus;r.innerHTML="";const i=document.createElement("option");i.value="autogenerar",i.textContent="AUTOGENERAR",i.selected=a==="autogenerar",r.appendChild(i),[...g.corpora].sort((u,f)=>u.label.localeCompare(f.label,"es")).forEach(u=>{var d;const f=document.createElement("option");f.value=u.key;const l=((d=u.attention)==null?void 0:d.length)||0;let p=u.active?u.label:`${u.label} (${e.t("ops.ingestion.corpusInactiveOption")})`;l>0&&(p+=` ⚠ ${l}`),f.textContent=p,f.selected=u.key===a,r.appendChild(f)})}function qe(){return g.selectedCorpus!=="autogenerar"?g.selectedCorpus:"autogenerar"}async function ge(a){var l,p;const i=[],u=[];for(let d=0;d<a.items.length;d++){const $=(p=(l=a.items[d]).webkitGetAsEntry)==null?void 0:p.call(l);$&&u.push($)}if(!u.some(d=>d.isDirectory))return[];async function f(d){if(d.isFile){const $=await new Promise((x,T)=>{d.file(x,T)});g.folderRelativePaths.set($,d.fullPath.replace(/^\//,"")),i.push($)}else if(d.isDirectory){const $=d.createReader();let x;do{x=await new Promise((T,J)=>{$.readEntries(T,J)});for(const T of x)await f(T)}while(x.length>0)}}for(const d of u)await f(d);return i}async function me(a,i=""){const u=[];for await(const[f,l]of a.entries()){const p=i?`${i}/${f}`:f;if(l.kind==="file"){const d=await l.getFile();g.folderRelativePaths.set(d,p),u.push(d)}else if(l.kind==="directory"){const d=await me(l,p);u.push(...d)}}return u}async function Xe(a,i,u,f=Ct){let l=0,p=0,d=0,$=0;const x=[];return new Promise(T=>{function J(){for(;d<f&&$<i.length;){const V=i[$++];d++,ls(a,V,u).then(()=>{l++}).catch(H=>{p++;const G=H instanceof Error?H.message:String(H);x.push({filename:V.name,error:G}),console.error(`[folder-ingest] Upload failed: ${V.name}`,H)}).finally(()=>{d--,t.setFolderUploadProgress({total:i.length,uploaded:l,failed:p,uploading:$<i.length||d>0}),Fe(),$<i.length||d>0?J():T({uploaded:l,failed:p,errors:x})})}}t.setFolderUploadProgress({total:i.length,uploaded:0,failed:0,uploading:!0}),Fe(),J()})}function Fe(){const a=g.folderUploadProgress;if(!a||!a.uploading){h.hidden=!0,h.innerHTML="";return}const i=a.uploaded+a.failed,u=a.total>0?Math.round(i/a.total*100):0,f=Math.max(0,Math.min(Ct,a.total-i));h.hidden=!1,h.innerHTML=`
      <div class="ops-upload-progress-header">
        <span>${e.t("ops.ingestion.uploadProgress",{current:i,total:a.total})}</span>
        <span>${u}%</span>
      </div>
      <div class="ops-upload-progress-bar">
        <span class="ops-upload-progress-fill" style="width:${u}%"></span>
      </div>
      <div class="ops-upload-progress-detail">
        ${e.t("ops.ingestion.uploadProgressDetail",{uploaded:a.uploaded,failed:a.failed,inflight:f})}
      </div>
    `}function Ze(a){if(g.pendingFiles.length!==0&&ct(g.pendingFiles[0])!=="")try{const i=g.pendingFiles.map(u=>({name:u.name,relativePath:ct(u),size:u.size}));localStorage.setItem(Et+a,JSON.stringify(i))}catch{}}function Qe(a){try{localStorage.removeItem(Et+a)}catch{}}function et(a){try{const i=localStorage.getItem(Et+a);if(!i)return 0;const u=JSON.parse(i);if(!Array.isArray(u))return 0;const f=g.sessions.find(p=>p.session_id===a);if(!f)return u.length;const l=new Set((f.documents||[]).map(p=>p.filename));return u.filter(p=>!l.has(p.name)).length}catch{return 0}}function He(a,i,u){var x;const f=document.createElement("div");f.className="ops-intake-row",i.verdict==="pending"&&f.classList.add("ops-intake-row--pending"),u.readonly&&f.classList.add("ops-intake-row--readonly");const l=document.createElement("span");l.className="ops-intake-row__icon",l.textContent="📄";const p=document.createElement("span");p.className="ops-intake-row__name",p.textContent=i.relativePath||i.file.name,p.title=i.relativePath||i.file.name;const d=document.createElement("span");d.className="ops-intake-row__size",d.textContent=cn(i.file.size);const $=dn(i,e);if(f.append(l,p,d,$),u.showReason&&((x=i.preflightEntry)!=null&&x.reason)){const T=document.createElement("span");T.className="ops-intake-row__reason",T.textContent=i.preflightEntry.reason,T.title=i.preflightEntry.reason,f.appendChild(T)}if(u.removable){const T=document.createElement("button");T.type="button",T.className="ops-intake-row__remove",T.textContent="✕",T.title=e.t("ops.ingestion.willIngest.cancelAll"),T.addEventListener("click",J=>{J.stopPropagation(),Ne(i)}),f.appendChild(T)}a.appendChild(f)}function de(a,i,u,f,l,p){const d=document.createElement("section");d.className=`ops-intake-panel ops-intake-panel--${a}`;const $=document.createElement("header");$.className="ops-intake-panel__header";const x=document.createElement("span");x.className="ops-intake-panel__title",x.textContent=e.t(i),$.appendChild(x);const T=document.createElement("span");if(T.className="ops-intake-panel__count",T.textContent=e.t(u,{count:f}),$.appendChild(T),p.readonly){const V=document.createElement("span");V.className="ops-intake-panel__readonly",V.textContent=e.t("ops.ingestion.bounced.readonly"),$.appendChild(V)}if(p.cancelAllAction){const V=document.createElement("button");V.type="button",V.className="ops-intake-panel__action",V.textContent=e.t("ops.ingestion.willIngest.cancelAll"),V.addEventListener("click",H=>{H.stopPropagation(),p.cancelAllAction()}),$.appendChild(V)}d.appendChild($);const J=document.createElement("div");return J.className="ops-intake-panel__body",l.forEach(V=>He(J,V,p)),d.appendChild(J),d}function be(){var f,l;if((f=b.querySelector(".ops-intake-windows"))==null||f.remove(),(l=b.querySelector(".dropzone-file-list"))==null||l.remove(),g.intake.length===0){R.textContent=e.t("ops.ingestion.pendingNone"),R.hidden=!0,b.classList.remove("has-files");return}R.hidden=!0,b.classList.add("has-files");const a=document.createElement("div");a.className="ops-intake-windows";const i=Oe();i&&a.appendChild(i),a.appendChild(de("intake","ops.ingestion.intake.title","ops.ingestion.intake.count",g.intake.length,g.intake,{removable:!1,readonly:!1,showReason:!1}));const u=g.reviewPlan;u&&(a.appendChild(de("will-ingest","ops.ingestion.willIngest.title","ops.ingestion.willIngest.count",u.willIngest.length,u.willIngest,{removable:!0,readonly:!1,showReason:!1,cancelAllAction:u.willIngest.length>0?()=>Ie():void 0})),u.bounced.length>0&&a.appendChild(de("bounced","ops.ingestion.bounced.title","ops.ingestion.bounced.count",u.bounced.length,u.bounced,{removable:!1,readonly:!0,showReason:!0}))),b.appendChild(a)}function Oe(){var d;const a=((d=g.reviewPlan)==null?void 0:d.stalePartial)===!0,i=g.intake.some($=>$.verdict==="pending"),u=z;if(!a&&!i&&!u)return null;const f=document.createElement("div");if(f.className="ops-intake-banner",u){f.classList.add("ops-intake-banner--error");const $=document.createElement("span");$.className="ops-intake-banner__text",$.textContent=e.t("ops.ingestion.intake.failed");const x=document.createElement("button");return x.type="button",x.className="ops-intake-banner__retry",x.textContent=e.t("ops.ingestion.intake.retry"),x.addEventListener("click",T=>{T.stopPropagation(),z=!1,_e(),ae()}),f.append($,x),f}const l=document.createElement("span");l.className="ops-intake-banner__spinner",f.appendChild(l);const p=document.createElement("span");return p.className="ops-intake-banner__text",a?(f.classList.add("ops-intake-banner--stale"),p.textContent=e.t("ops.ingestion.intake.stale")):(f.classList.add("ops-intake-banner--verifying"),p.textContent=e.t("ops.ingestion.intake.verifying")),f.appendChild(p),f}function Z(){var oe,xe,ye,it,se;const a=t.selectedCorpusConfig(),i=g.selectedSession,u=g.selectedCorpus==="autogenerar"?g.corpora.some(Te=>Te.active):!!(a!=null&&a.active),f=ft(String((i==null?void 0:i.status)||""));m.value=m.value||"autogenerar";const l=((oe=g.folderUploadProgress)==null?void 0:oe.uploading)??!1,p=g.reviewPlan,d=(p==null?void 0:p.willIngest.length)??0,$=(p==null?void 0:p.stalePartial)===!0,x=z===!0,T=!!p&&d>0&&!$&&!x;N.disabled=g.mutating||!u,A.disabled=g.mutating||!u||l,B.disabled=g.mutating||!u||l||f,y.disabled=g.mutating||!u||!T||l,p?d===0?y.textContent=e.t("ops.ingestion.approveNone"):y.textContent=e.t("ops.ingestion.approveCount",{count:d}):y.textContent=e.t("ops.ingestion.approve"),S.disabled=g.mutating||!u||!i||f,_.disabled=g.mutating||!u||l||!i||f,_.textContent=`▶ ${e.t("ops.ingestion.actions.autoProcess")}`;const J=Number(((xe=i==null?void 0:i.batch_summary)==null?void 0:xe.done)||0),V=Number(((ye=i==null?void 0:i.batch_summary)==null?void 0:ye.queued)||0)+Number(((it=i==null?void 0:i.batch_summary)==null?void 0:it.processing)||0),H=Number(((se=i==null?void 0:i.batch_summary)==null?void 0:se.pending_batch_gate)||0),G=J>=1&&(V>=1||H>=1);if(c.disabled=g.mutating||!u||!i||f||!G,C.disabled=g.mutating||!u||!i||f,q.disabled=g.mutating||!i,I.disabled=g.mutating,r.disabled=g.mutating||g.corpora.length===0,w.disabled=g.mutating||!u,!u){D.textContent=e.t("ops.ingestion.corpusInactive");return}D.textContent=e.t("ops.ingestion.overview",{active:g.corpora.filter(Te=>Te.active).length,total:g.corpora.length,corpus:g.selectedCorpus==="autogenerar"?"AUTOGENERAR":(a==null?void 0:a.label)||g.selectedCorpus,session:(i==null?void 0:i.session_id)||e.t("ops.ingestion.noSession")})}function dt(){if(pe.innerHTML="",X.textContent=g.selectedSession?`${g.selectedSession.session_id} · ${g.selectedSession.status}`:e.t("ops.ingestion.selectedEmpty"),g.sessions.length===0){const a=document.createElement("li");a.className="ops-empty",a.textContent=e.t("ops.ingestion.sessionsEmpty"),pe.appendChild(a);return}g.sessions.forEach(a=>{var ye,it;const i=document.createElement("li"),u=a.status==="partial_failed",f=document.createElement("button");f.type="button",f.className=`ops-session-item${a.session_id===g.selectedSessionId?" is-active":""}${u?" has-retry-action":""}`,f.dataset.sessionId=a.session_id;const l=document.createElement("div");l.className="ops-session-item-head";const p=document.createElement("div");p.className="ops-session-id",p.textContent=a.session_id;const d=document.createElement("span");d.className=`meta-chip status-${lt(a.status)}`,d.textContent=a.status,l.append(p,d);const $=document.createElement("div");$.className="ops-session-pills";const x=((ye=g.corpora.find(se=>se.key===a.corpus))==null?void 0:ye.label)||a.corpus,T=document.createElement("span");T.className="meta-chip ops-pill-corpus",T.textContent=x,$.appendChild(T);const J=a.documents||[];[...new Set(J.map(se=>se.batch_type).filter(Boolean))].forEach(se=>{const Te=document.createElement("span");Te.className="meta-chip ops-pill-batch",Te.textContent=Bs(se,e),$.appendChild(Te)});const H=J.map(se=>se.filename).filter(Boolean);let G=null;if(H.length>0){G=document.createElement("div"),G.className="ops-session-files";const se=H.slice(0,3),Te=H.length-se.length;G.textContent=se.join(", ")+(Te>0?` +${Te}`:"")}const oe=document.createElement("div");oe.className="ops-session-summary",oe.textContent=zt(a.batch_summary,e);const xe=document.createElement("div");if(xe.className="ops-session-summary",xe.textContent=a.updated_at?e.formatDateTime(a.updated_at,{dateStyle:"short",timeStyle:"short",timeZone:"America/Bogota"}):"-",f.appendChild(l),f.appendChild($),G&&f.appendChild(G),f.appendChild(oe),f.appendChild(xe),(it=a.last_error)!=null&&it.code){const se=document.createElement("div");se.className="ops-session-summary status-error",se.textContent=a.last_error.code,f.appendChild(se)}if(f.addEventListener("click",async()=>{t.setSelectedSession(a),ae();try{await Ge({sessionId:a.session_id,showWheel:!0})}catch{}}),i.appendChild(f),u){const se=document.createElement("button");se.type="button",se.className="ops-session-retry-inline",se.textContent=e.t("ops.ingestion.actions.retry"),se.disabled=g.mutating,se.addEventListener("click",async Te=>{Te.stopPropagation(),se.disabled=!0,t.setMutating(!0),Z();try{await o(async()=>Lt(a.session_id)),await We({showWheel:!1,reportError:!0,focusSessionId:a.session_id}),n(e.t("ops.ingestion.flash.retryStarted",{id:a.session_id}),"success")}catch(fs){n(ue(fs),"error")}finally{t.setMutating(!1),Z()}}),i.appendChild(se)}pe.appendChild(i)})}function Ue(a){const i=[],u=()=>new Date().toISOString();if(i.push(e.t("ops.ingestion.log.sessionHeader",{id:a.session_id})),i.push(`Corpus:     ${a.corpus||"-"}`),i.push(`Status:     ${a.status}`),i.push(`Created:    ${a.created_at||"-"}`),i.push(`Updated:    ${a.updated_at||"-"}`),i.push(`Heartbeat:  ${a.heartbeat_at??"-"}`),a.auto_processing&&i.push(`Auto-proc:  ${a.auto_processing}`),a.gate_sub_stage&&i.push(`Gate-stage: ${a.gate_sub_stage}`),a.wip_sync_status&&i.push(`WIP-sync:   ${a.wip_sync_status}`),a.batch_summary){const l=a.batch_summary,p=(a.documents||[]).filter($=>$.status==="raw"||$.status==="needs_classification").length,d=(a.documents||[]).filter($=>$.status==="pending_dedup").length;i.push(""),i.push("── Resumen del lote ──"),i.push(`  Total: ${l.total}  Queued: ${l.queued}  Processing: ${l.processing}  Done: ${l.done}  Failed: ${l.failed}  Duplicados: ${l.skipped_duplicate}  Bounced: ${l.bounced}`),p>0&&i.push(`  Raw (sin clasificar): ${p}`),d>0&&i.push(`  Pending dedup: ${d}`)}a.last_error&&(i.push(""),i.push("── Error de sesión ──"),i.push(`  Código:    ${a.last_error.code||"-"}`),i.push(`  Mensaje:   ${a.last_error.message||"-"}`),i.push(`  Guía:      ${a.last_error.guidance||"-"}`),i.push(`  Siguiente: ${a.last_error.next_step||"-"}`));const f=a.documents||[];if(f.length===0)i.push(""),i.push(e.t("ops.ingestion.log.noDocuments"));else{i.push(""),i.push(`── Documentos (${f.length}) ──`);const l={failed:0,processing:1,in_progress:1,queued:2,raw:2,done:3,completed:3,bounced:4,skipped_duplicate:5},p=[...f].sort((d,$)=>(l[d.status]??3)-(l[$.status]??3));for(const d of p)i.push(""),i.push(`  ┌─ ${d.filename} (${d.doc_id})`),i.push(`  │  Status:   ${d.status}  │  Stage: ${d.stage||"-"}  │  Progress: ${d.progress??0}%`),i.push(`  │  Bytes:    ${d.bytes??"-"}  │  Batch: ${d.batch_type||"-"}`),d.source_relative_path&&i.push(`  │  Path:     ${d.source_relative_path}`),(d.detected_topic||d.detected_type)&&(i.push(`  │  Topic:    ${d.detected_topic||"-"}  │  Type: ${d.detected_type||"-"}  │  Confidence: ${d.combined_confidence??"-"}`),d.classification_source&&i.push(`  │  Classifier: ${d.classification_source}`)),d.chunk_count!=null&&i.push(`  │  Chunks:   ${d.chunk_count}  │  Elapsed: ${d.elapsed_ms??"-"}ms`),d.dedup_match_type&&i.push(`  │  Dedup:    ${d.dedup_match_type}  │  Match: ${d.dedup_match_doc_id||"-"}`),d.replaced_doc_id&&i.push(`  │  Replaced: ${d.replaced_doc_id}`),d.error&&(i.push("  │  ❌ ERROR"),i.push(`  │    Código:    ${d.error.code||"-"}`),i.push(`  │    Mensaje:   ${d.error.message||"-"}`),i.push(`  │    Guía:      ${d.error.guidance||"-"}`),i.push(`  │    Siguiente: ${d.error.next_step||"-"}`)),i.push(`  │  Created: ${d.created_at||"-"}  │  Updated: ${d.updated_at||"-"}`),i.push("  └─")}return i.push(""),i.push(`Log generado: ${u()}`),i.join(`
`)}function at(){if(he.length>0)return;const a=g.selectedSession;if(!a){P.hidden=!0,v.textContent="";return}P.hidden=!1,v.textContent=Ue(a)}function ze(){const a=g.selectedSession;if(!a){fe.textContent=e.t("ops.ingestion.selectedEmpty"),O.hidden=!0,he.length===0&&(P.hidden=!0),U.innerHTML="";return}const i=et(a.session_id),u=i>0?` · ${e.t("ops.ingestion.folderResumePending",{count:i})}`:"";if(fe.textContent=`${a.session_id} · ${zt(a.batch_summary,e)}${u}`,a.last_error?(O.hidden=!1,re.textContent=a.last_error.message||a.last_error.code||"-",ke.textContent=a.last_error.guidance||"",F.textContent=`${e.t("ops.ingestion.lastErrorNext")}: ${a.last_error.next_step||"-"}`):O.hidden=!0,(a.documents||[]).length===0){U.innerHTML=`<p class="ops-empty">${e.t("ops.ingestion.documentsEmpty")}</p>`,U.style.minHeight="0",at();return}U.style.minHeight="",an(a,U,e,ve,g.corpora),ve.clear(),at()}function ae(){Me(),be(),Z(),dt(),ze()}async function ut(){const a=await Ae("/api/corpora"),i=Array.isArray(a.corpora)?a.corpora:[];t.setCorpora(i);const u=new Set(i.map(f=>f.key));u.add("autogenerar"),u.has(g.selectedCorpus)||t.setSelectedCorpus("autogenerar")}async function cs(){const a=await Ae("/api/ingestion/sessions?limit=20");return Array.isArray(a.sessions)?a.sessions:[]}async function tt(a){const i=await Ae(`/api/ingestion/sessions/${encodeURIComponent(a)}`);if(!i.session)throw new Error("missing_session");return i.session}async function yt(a){const i=await St("/api/ingestion/sessions",{corpus:a});if(!i.session)throw new Error("missing_session");return i.session}async function ls(a,i,u){const f=r.value==="autogenerar"?"":r.value,l={"Content-Type":"application/octet-stream","X-Upload-Filename":i.name,"X-Upload-Mime":i.type||"application/octet-stream","X-Upload-Batch-Type":u};f&&(l["X-Upload-Topic"]=f);const p=ct(i,g.folderRelativePaths);p&&(l["X-Upload-Relative-Path"]=p),console.log(`[upload] ${i.name} (${i.size}B) → session=${a} batch=${u}`);const d=await fetch(`/api/ingestion/sessions/${encodeURIComponent(a)}/files`,{method:"POST",headers:l,body:i}),$=await d.text();let x;try{x=JSON.parse($)}catch{throw console.error(`[upload] ${i.name} — response not JSON (${d.status}):`,$.slice(0,300)),new Error(`Upload response not JSON: ${d.status} ${$.slice(0,100)}`)}if(!d.ok){const T=x.error||d.statusText;throw console.error(`[upload] ${i.name} — HTTP ${d.status}:`,T),new nt(T,d.status,x)}if(!x.document)throw console.error(`[upload] ${i.name} — no document in response:`,x),new Error("missing_document");return console.log(`[upload] ${i.name} → OK doc_id=${x.document.doc_id} status=${x.document.status}`),x.document}async function pt(a){return Ce(`/api/ingestion/sessions/${encodeURIComponent(a)}/process`,{method:"POST"})}async function Tt(a){return Ce(`/api/ingestion/sessions/${encodeURIComponent(a)}/validate-batch`,{method:"POST"})}async function Lt(a){return Ce(`/api/ingestion/sessions/${encodeURIComponent(a)}/retry`,{method:"POST"})}async function ds(a,i=!1){const u=i?"?force=true":"";return Ce(`/api/ingestion/sessions/${encodeURIComponent(a)}${u}`,{method:"DELETE"})}async function We({showWheel:a=!0,reportError:i=!0,focusSessionId:u=""}={}){const f=async()=>{await ut(),ae();let l=await cs();const p=u||g.selectedSessionId;if(p&&!l.some(d=>d.session_id===p))try{l=[await tt(p),...l.filter($=>$.session_id!==p)]}catch{p===g.selectedSessionId&&t.setSelectedSession(null)}t.setSessions(l.sort((d,$)=>Date.parse(String($.updated_at||0))-Date.parse(String(d.updated_at||0)))),t.syncSelectedSession(),ae()};try{a?await o(f):await f()}catch(l){throw i&&n(ue(l),"error"),ae(),l}}async function Ge({sessionId:a,showWheel:i=!1,reportError:u=!0}){const f=async()=>{const l=await tt(a);t.upsertSession(l),ae()};try{i?await o(f):await f()}catch(l){throw u&&n(ue(l),"error"),l}}async function us(){var i,u,f,l;const a=qe();if(console.log(`[folder-ingest] ensureSelectedSession: effectiveCorpus="${a}", selectedSession=${((i=g.selectedSession)==null?void 0:i.session_id)||"null"} (status=${((u=g.selectedSession)==null?void 0:u.status)||"null"}, corpus=${((f=g.selectedSession)==null?void 0:f.corpus)||"null"})`),g.selectedSession&&!Ut(g.selectedSession)&&g.selectedSession.status!=="completed"&&(g.selectedSession.corpus===a||a==="autogenerar"))return console.log(`[folder-ingest] Reusing session ${g.selectedSession.session_id}`),g.selectedSession;E(`Creando sesión con corpus="${a}"...`);try{const p=await yt(a);return E(`Sesión creada: ${p.session_id} (corpus=${p.corpus})`),t.upsertSession(p),p}catch(p){if(E(`Creación falló para corpus="${a}": ${p instanceof Error?p.message:String(p)}`),a==="autogenerar"){const d=((l=g.corpora.find(x=>x.active))==null?void 0:l.key)||"declaracion_renta";E(`Reintentando con corpus="${d}"...`);const $=await yt(d);return E(`Sesión fallback: ${$.session_id} (corpus=${$.corpus})`),t.upsertSession($),$}throw p}}const ps=4e3;let ot=null,_t="";function Ye(){ot&&(clearTimeout(ot),ot=null),_t="",M.hidden=!0,M.classList.remove("is-running")}function $t(a){const i=a.batch_summary,u=mt(a),f=Math.max(0,Number(i.queued??0)-u),l=Number(i.processing??0),p=Number(i.done??0),d=Number(i.failed??0),$=Number(i.bounced??0),x=f+l;M.hidden=!1;const T=$>0?` · ${$} rebotados`:"";x>0||u>0?(M.classList.add("is-running"),M.textContent=e.t("ops.ingestion.auto.running",{queued:f,processing:l,raw:u})+T):d>0?(M.classList.remove("is-running"),M.textContent=e.t("ops.ingestion.auto.done",{done:p,failed:d,raw:u})+T):(M.classList.remove("is-running"),M.textContent=e.t("ops.ingestion.auto.allDone",{done:p})+T)}async function At(){const a=_t;if(a)try{const i=await tt(a);t.upsertSession(i),ae(),$t(i);const u=i.batch_summary,f=mt(i),l=Number(u.total??0);if(l===0){Ye();return}f>0&&await Ce(`/api/ingestion/sessions/${encodeURIComponent(a)}/auto-process`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({max_concurrency:5})});const p=f>0?await tt(a):i,d=mt(p),$=Math.max(0,Number(p.batch_summary.queued??0)-d),x=Number(p.batch_summary.processing??0);$>0&&x===0&&await pt(a),f>0&&(t.upsertSession(p),ae(),$t(p));const T=$+x;if(l>0&&T===0&&d===0){if(Number(p.batch_summary.pending_batch_gate??0)>0&&p.status!=="running_batch_gates"&&p.status!=="completed")try{await Tt(a)}catch{}const V=await tt(a);t.upsertSession(V),ae(),$t(V),Ye(),n(e.t("ops.ingestion.auto.allDone",{done:Number(V.batch_summary.done??0)}),"success");return}if(T===0&&d>0){M.classList.remove("is-running"),M.textContent=e.t("ops.ingestion.auto.done",{done:Number(p.batch_summary.done??0),failed:Number(p.batch_summary.failed??0),raw:d}),Ye();return}ot=setTimeout(()=>void At(),ps)}catch(i){Ye(),n(ue(i),"error")}}function Rt(a){Ye(),_t=a,M.hidden=!1,M.classList.add("is-running"),M.textContent=e.t("ops.ingestion.auto.running",{queued:0,processing:0,raw:0}),ot=setTimeout(()=>void At(),2e3)}async function ms(){var J,V,H;E(`directFolderIngest: ${g.pendingFiles.length} archivos pendientes`);const a=await us();E(`Sesión asignada: ${a.session_id} (corpus=${a.corpus}, status=${a.status})`);const i=m.value||"autogenerar";E(`Subiendo ${g.pendingFiles.length} archivos con batchType="${i}"...`),Ze(a.session_id);const u=await Xe(a.session_id,[...g.pendingFiles],i,Ct);if(console.log("[folder-ingest] Upload result:",{uploaded:u.uploaded,failed:u.failed}),E(`Upload completo: ${u.uploaded} subidos, ${u.failed} fallidos${u.errors.length>0?" — "+u.errors.slice(0,5).map(G=>`${G.filename}: ${G.error}`).join("; "):""}`),t.setPendingFiles([]),t.setFolderUploadProgress(null),Qe(a.session_id),k.value="",w.value="",u.failed>0&&u.uploaded===0){const G=u.errors.slice(0,3).map(oe=>`${oe.filename}: ${oe.error}`).join("; ");E(`TODOS FALLARON: ${G}`),n(`${e.t("ops.ingestion.flash.folderUploadPartial",u)} — ${G}`,"error"),await We({showWheel:!1,reportError:!0,focusSessionId:a.session_id});return}E("Consultando estado de sesión post-upload...");const f=await tt(a.session_id),l=Number(((J=f.batch_summary)==null?void 0:J.bounced)??0),p=mt(f),d=Number(((V=f.batch_summary)==null?void 0:V.queued)??0),$=Number(((H=f.batch_summary)==null?void 0:H.total)??0),x=$-l;if(E(`Sesión post-upload: total=${$} bounced=${l} raw=${p} queued=${d} actionable=${x}`),x===0&&l>0){E(`TODOS REBOTADOS: ${l} archivos ya existen en el corpus`),t.upsertSession(f),n(`${l} archivos ya existen en el corpus (rebotados). 0 archivos nuevos para procesar.`,"error"),E("--- FIN (todo rebotado) ---");return}E("Auto-procesando con threshold=0 (force-queue)..."),await Ce(`/api/ingestion/sessions/${encodeURIComponent(a.session_id)}/auto-process`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({max_concurrency:5,auto_accept_threshold:0})}),await pt(a.session_id),await We({showWheel:!1,reportError:!0,focusSessionId:a.session_id});const T=[];u.uploaded>0&&T.push(`${x} archivos en proceso`),l>0&&T.push(`${l} rebotados`),u.failed>0&&T.push(`${u.failed} fallidos`),n(T.join(" · "),u.failed>0?"error":"success"),E(`Auto-piloto iniciado para ${a.session_id}`),E("--- FIN (éxito) ---"),Rt(a.session_id)}async function gs(a,i){return(await St("/api/ingestion/preflight",{corpus:i,files:a})).manifest}function Mt(){const a=g.preflightScanProgress;if(!a||!a.scanning){h.hidden=!0,h.innerHTML="";return}const i=a.total>0?Math.round(a.hashed/a.total*100):0;h.hidden=!1,h.innerHTML=`
      <div class="ops-preflight-scan">
        <div class="ops-preflight-scan-header">
          <span>${e.t("ops.ingestion.preflight.scanning",{hashed:a.hashed,total:a.total})}</span>
          <span>${i}%</span>
        </div>
        <div class="ops-preflight-scan-bar">
          <span class="ops-preflight-scan-fill" style="width:${i}%"></span>
        </div>
        <div class="ops-preflight-scan-detail">${e.t("ops.ingestion.preflight.scanningDetail")}</div>
      </div>
    `}function bs(){b.addEventListener("click",()=>{w.disabled||w.click()}),b.addEventListener("keydown",l=>{l.key!=="Enter"&&l.key!==" "||(l.preventDefault(),w.disabled||w.click())});let a=0;b.addEventListener("dragenter",l=>{l.preventDefault(),a++,w.disabled||b.classList.add("is-dragover")}),b.addEventListener("dragover",l=>{l.preventDefault()}),b.addEventListener("dragleave",()=>{a--,a<=0&&(a=0,b.classList.remove("is-dragover"))}),b.addEventListener("drop",async l=>{var $;if(l.preventDefault(),a=0,b.classList.remove("is-dragover"),w.disabled)return;const p=l.dataTransfer;if(p){const x=await ge(p);if(x.length>0){te(rt(x));return}}const d=Array.from((($=l.dataTransfer)==null?void 0:$.files)||[]);d.length!==0&&te(rt(d))}),w.addEventListener("change",()=>{const l=Array.from(w.files||[]);l.length!==0&&te(rt(l))}),k.addEventListener("change",()=>{const l=Array.from(k.files||[]);l.length!==0&&te(rt(l))}),A.addEventListener("click",()=>{w.disabled||w.click()}),B.addEventListener("click",async()=>{if(!k.disabled){if(typeof window.showDirectoryPicker=="function")try{const l=await window.showDirectoryPicker({mode:"read"}),p=await me(l,l.name),d=rt(p);d.length>0?te(d):n(e.t("ops.ingestion.pendingNone"),"error");return}catch(l){if((l==null?void 0:l.name)==="AbortError")return}k.click()}}),r.addEventListener("change",()=>{t.setSelectedCorpus(r.value),t.setSessions([]),t.setSelectedSession(null),Pe(),n(),ae(),We({showWheel:!0,reportError:!0})}),I.addEventListener("click",l=>{l.stopPropagation(),n(),We({showWheel:!0,reportError:!0})}),N.addEventListener("click",async()=>{Ye(),n(),Pe(),t.setPreflightManifest(null),t.setFolderUploadProgress(null),g.rejectedArtifacts=[],h.hidden=!0,h.innerHTML="",w.value="",k.value="",O.hidden=!0,L(),P.hidden=!0,v.textContent="",t.setMutating(!0),Z();try{const l=await o(async()=>yt(qe()));t.upsertSession(l),ae(),n(e.t("ops.ingestion.flash.sessionCreated",{id:l.session_id}),"success")}catch(l){n(ue(l),"error")}finally{t.setMutating(!1),Z()}}),y.addEventListener("click",()=>{Re()}),S.addEventListener("click",async()=>{const l=g.selectedSessionId;if(l){n(),t.setMutating(!0),Z();try{await o(async()=>pt(l)),await Ge({sessionId:l,showWheel:!1,reportError:!1});const p=e.t("ops.ingestion.flash.processStarted",{id:l});n(p,"success"),ce.show({message:p,tone:"success"})}catch(p){const d=ue(p);n(d,"error"),ce.show({message:d,tone:"error"})}finally{t.setMutating(!1),Z()}}}),c.addEventListener("click",async()=>{const l=g.selectedSessionId;if(l){n(),t.setMutating(!0),Z();try{await o(async()=>Tt(l)),await Ge({sessionId:l,showWheel:!1,reportError:!1});const p="Validación de lote iniciada";n(p,"success"),ce.show({message:p,tone:"success"})}catch(p){const d=ue(p);n(d,"error"),ce.show({message:d,tone:"error"})}finally{t.setMutating(!1),Z()}}}),C.addEventListener("click",async()=>{const l=g.selectedSessionId;if(l){n(),t.setMutating(!0),Z();try{await o(async()=>Lt(l)),await Ge({sessionId:l,showWheel:!1,reportError:!1}),n(e.t("ops.ingestion.flash.retryStarted",{id:l}),"success")}catch(p){n(ue(p),"error")}finally{t.setMutating(!1),Z()}}}),q.addEventListener("click",async()=>{var x;const l=g.selectedSessionId;if(!l)return;const p=Ut(g.selectedSession),d=p?e.t("ops.ingestion.confirm.ejectPostGate"):e.t("ops.ingestion.confirm.ejectPreGate");if(await ce.confirm({title:e.t("ops.ingestion.actions.discardSession"),message:d,tone:"caution",confirmLabel:e.t("ops.ingestion.confirm.ejectLabel")})){Ye(),n(),t.setMutating(!0),Z();try{const T=ft(String(((x=g.selectedSession)==null?void 0:x.status)||"")),J=await o(async()=>ds(l,T||p));t.clearSelectionAfterDelete(),Pe(),t.setPreflightManifest(null),t.setFolderUploadProgress(null),g.rejectedArtifacts=[],h.hidden=!0,h.innerHTML="",w.value="",k.value="",O.hidden=!0,L(),P.hidden=!0,v.textContent="",await We({showWheel:!1,reportError:!1});const V=Array.isArray(J.errors)&&J.errors.length>0,H=J.path==="rollback"?e.t("ops.ingestion.flash.ejectedRollback",{id:l,count:J.ejected_files}):e.t("ops.ingestion.flash.ejectedInstant",{id:l,count:J.ejected_files}),G=V?"caution":"success";n(H,V?"error":"success"),ce.show({message:H,tone:G}),V&&ce.show({message:e.t("ops.ingestion.flash.ejectedPartial"),tone:"caution",durationMs:8e3})}catch(T){const J=ue(T);n(J,"error"),ce.show({message:J,tone:"error"})}finally{t.setMutating(!1),ae()}}}),_.addEventListener("click",async()=>{const l=g.selectedSessionId;if(l){n(),t.setMutating(!0),Z();try{await o(async()=>Ce(`/api/ingestion/sessions/${encodeURIComponent(l)}/auto-process`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({max_concurrency:5})})),await pt(l),await Ge({sessionId:l,showWheel:!1,reportError:!1}),n(`Auto-procesamiento iniciado para ${l}`,"success"),Rt(l)}catch(p){n(ue(p),"error")}finally{t.setMutating(!1),Z()}}});const i=document.getElementById("ingestion-log-toggle");i&&(i.addEventListener("click",l=>{if(l.target.closest(".ops-log-copy-btn"))return;const p=v.hidden;v.hidden=!p,i.setAttribute("aria-expanded",String(p));const d=i.querySelector(".ops-log-accordion-marker");d&&(d.textContent=p?"▾":"▸")}),i.addEventListener("keydown",l=>{(l.key==="Enter"||l.key===" ")&&(l.preventDefault(),i.click())})),K.addEventListener("click",l=>{l.preventDefault(),l.stopPropagation();const p=v.textContent||"";navigator.clipboard.writeText(p).then(()=>{const d=K.textContent;K.textContent=e.t("ops.ingestion.log.copied"),setTimeout(()=>{K.textContent=d},1500)}).catch(()=>{const d=document.createRange();d.selectNodeContents(v);const $=window.getSelection();$==null||$.removeAllRanges(),$==null||$.addRange(d)})}),U.addEventListener("click",async l=>{var V;const p=l.target.closest("[data-action]");if(!p)return;const d=p.getAttribute("data-action"),$=p.getAttribute("data-doc-id"),x=g.selectedSessionId;if(!x||!$)return;if(d==="show-existing-dropdown"){const H=p.closest(".kanban-card"),G=H==null?void 0:H.querySelector(".kanban-ag-fallback-panel");G&&(G.hidden=!G.hidden);return}let T="",J="";if(d==="assign"){const H=p.closest(".kanban-card"),G=H==null?void 0:H.querySelector("[data-field='topic']"),oe=H==null?void 0:H.querySelector("[data-field='type']");if(T=(G==null?void 0:G.value)||"",J=(oe==null?void 0:oe.value)||"",!T||!J){G&&!T&&G.classList.add("kanban-select--invalid"),oe&&!J&&oe.classList.add("kanban-select--invalid");return}}n(),t.setMutating(!0),Z();try{switch(d){case"assign":{await o(async()=>Ce(`/api/ingestion/sessions/${encodeURIComponent(x)}/documents/${encodeURIComponent($)}/classify`,{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify({topic:T,batch_type:J})})),ve.add($);break}case"replace-dup":{await o(async()=>Ce(`/api/ingestion/sessions/${encodeURIComponent(x)}/documents/${encodeURIComponent($)}/resolve-duplicate`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action:"replace"})}));break}case"add-new-dup":{await o(async()=>Ce(`/api/ingestion/sessions/${encodeURIComponent(x)}/documents/${encodeURIComponent($)}/resolve-duplicate`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action:"add_new"})}));break}case"discard-dup":case"discard":{await o(async()=>Ce(`/api/ingestion/sessions/${encodeURIComponent(x)}/documents/${encodeURIComponent($)}/resolve-duplicate`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action:"discard"})}));break}case"accept-synonym":{const H=p.closest(".kanban-card"),G=H==null?void 0:H.querySelector("[data-field='type']"),oe=(G==null?void 0:G.value)||"";await o(async()=>Ce(`/api/ingestion/sessions/${encodeURIComponent(x)}/documents/${encodeURIComponent($)}/accept-autogenerar`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action:"accept_synonym",type:oe||void 0})})),ve.add($);break}case"accept-new-topic":{const H=p.closest(".kanban-card"),G=H==null?void 0:H.querySelector("[data-field='autogenerar-label']"),oe=H==null?void 0:H.querySelector("[data-field='type']"),xe=((V=G==null?void 0:G.value)==null?void 0:V.trim())||"",ye=(oe==null?void 0:oe.value)||"";if(!xe||xe.length<3){G&&G.classList.add("kanban-select--invalid");return}await o(async()=>Ce(`/api/ingestion/sessions/${encodeURIComponent(x)}/documents/${encodeURIComponent($)}/accept-autogenerar`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action:"accept_new_topic",edited_label:xe,type:ye||void 0})})),ve.add($),await ut(),Me();break}case"retry":{await o(async()=>Ce(`/api/ingestion/sessions/${encodeURIComponent(x)}/documents/${encodeURIComponent($)}/retry`,{method:"POST"}));break}case"remove":break}await Ge({sessionId:x,showWheel:!1,reportError:!1})}catch(H){n(ue(H),"error")}finally{t.setMutating(!1),Z()}});const u=s.addCorpusDialog,f=s.addCorpusBtn;if(u&&f){let l=function(H){return H.normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase().replace(/[^a-z0-9]+/g,"_").replace(/^_|_$/g,"")};const p=u.querySelector("#add-corpus-label"),d=u.querySelector("#add-corpus-key"),$=u.querySelector("#add-corpus-kw-strong"),x=u.querySelector("#add-corpus-kw-weak"),T=u.querySelector("#add-corpus-error"),J=u.querySelector("#add-corpus-cancel"),V=u.querySelector("#add-corpus-form");f.addEventListener("click",()=>{p&&(p.value=""),d&&(d.value=""),$&&($.value=""),x&&(x.value=""),T&&(T.hidden=!0),u.showModal(),p==null||p.focus()}),p==null||p.addEventListener("input",()=>{d&&(d.value=l(p.value))}),J==null||J.addEventListener("click",()=>{u.close()}),V==null||V.addEventListener("submit",async H=>{H.preventDefault(),T&&(T.hidden=!0);const G=(p==null?void 0:p.value.trim())||"";if(!G)return;const oe=(($==null?void 0:$.value)||"").split(",").map(ye=>ye.trim()).filter(Boolean),xe=((x==null?void 0:x.value)||"").split(",").map(ye=>ye.trim()).filter(Boolean);try{await o(async()=>St("/api/corpora",{label:G,keywords_strong:oe.length?oe:void 0,keywords_weak:xe.length?xe:void 0})),u.close(),await We({showWheel:!1,reportError:!1});const ye=l(G);ye&&t.setSelectedCorpus(ye),ae(),n(`Categoría "${G}" creada.`,"success")}catch(ye){T&&(T.textContent=ue(ye),T.hidden=!1)}})}}return{bindEvents:bs,refreshIngestion:We,refreshSelectedSession:Ge,render:ae}}function Ke(e){if(e==null)return null;const t=Number(e);return!Number.isFinite(t)||t<0?null:t}function ns({i18n:e,stateController:t,dom:s,withThinkingWheel:o,setFlash:n}){const{monitorTabBtn:r,ingestionTabBtn:m,controlTabBtn:b,embeddingsTabBtn:w,reindexTabBtn:k,monitorPanel:A,ingestionPanel:B,controlPanel:h,embeddingsPanel:R,reindexPanel:D,runsBody:I,timelineNode:N,timelineMeta:y,cascadeNote:S,userCascadeNode:_,userCascadeSummary:c,technicalCascadeNode:C,technicalCascadeSummary:q,refreshRunsBtn:X}=s,{state:pe}=t;function fe(E){const L=Ke(E);return L===null?"-":`${e.formatNumber(L/1e3,{minimumFractionDigits:2,maximumFractionDigits:2})} s`}function O(E){t.setActiveTab(E),re()}function re(){if(!r)return;const E=pe.activeTab;r.classList.toggle("is-active",E==="monitor"),r.setAttribute("aria-selected",String(E==="monitor")),m==null||m.classList.toggle("is-active",E==="ingestion"),m==null||m.setAttribute("aria-selected",String(E==="ingestion")),b==null||b.classList.toggle("is-active",E==="control"),b==null||b.setAttribute("aria-selected",String(E==="control")),w==null||w.classList.toggle("is-active",E==="embeddings"),w==null||w.setAttribute("aria-selected",String(E==="embeddings")),k==null||k.classList.toggle("is-active",E==="reindex"),k==null||k.setAttribute("aria-selected",String(E==="reindex")),A&&(A.hidden=E!=="monitor",A.classList.toggle("is-active",E==="monitor")),B&&(B.hidden=E!=="ingestion",B.classList.toggle("is-active",E==="ingestion")),h&&(h.hidden=E!=="control",h.classList.toggle("is-active",E==="control")),R&&(R.hidden=E!=="embeddings",R.classList.toggle("is-active",E==="embeddings")),D&&(D.hidden=E!=="reindex",D.classList.toggle("is-active",E==="reindex"))}function ke(E){if(N.innerHTML="",!Array.isArray(E)||E.length===0){N.innerHTML=`<li>${e.t("ops.timeline.empty")}</li>`;return}E.forEach(L=>{const Y=document.createElement("li");Y.innerHTML=`
        <strong>${L.stage||"-"}</strong> · <span class="status-${lt(String(L.status||""))}">${L.status||"-"}</span><br/>
        <small>${L.at||"-"} · ${L.duration_ms||0} ms</small>
        <pre>${JSON.stringify(L.details||{},null,2)}</pre>
      `,N.appendChild(Y)})}function F(E,L,Y){const z=Ke(L==null?void 0:L.total_ms),ie=z===null?e.t("ops.timeline.summaryPending"):fe(z),ee=Y==="user"&&String((L==null?void 0:L.chat_run_id)||"").trim()?` · chat_run ${String((L==null?void 0:L.chat_run_id)||"").trim()}`:"";E.textContent=`${e.t("ops.timeline.totalLabel")} ${ie}${ee}`}function U(E){var te,_e,Se;const L=[],Y=String(((te=E.details)==null?void 0:te.source)||"").trim(),z=String(E.status||"").trim();Y&&L.push(Y),z&&z!=="ok"&&z!=="missing"&&L.push(z);const ie=Number(((_e=E.details)==null?void 0:_e.citations_count)||0);Number.isFinite(ie)&&ie>0&&L.push(`${ie} refs`);const ee=String(((Se=E.details)==null?void 0:Se.panel_status)||"").trim();return ee&&L.push(ee),L.join(" · ")}function P(E,L,Y){E.innerHTML="";const z=Array.isArray(L==null?void 0:L.steps)?(L==null?void 0:L.steps)||[]:[];if(z.length===0){E.innerHTML=`<li class="ops-cascade-step is-empty">${e.t("ops.timeline.waterfallEmpty")}</li>`;return}const ie=Ke(L==null?void 0:L.total_ms)??Math.max(1,...z.map(ee=>Ke(ee.cumulative_ms)??Ke(ee.absolute_elapsed_ms)??0));z.forEach(ee=>{const te=Ke(ee.duration_ms),_e=Ke(ee.offset_ms)??0,Se=Ke(ee.absolute_elapsed_ms),$e=document.createElement("li");$e.className=`ops-cascade-step ops-cascade-step--${Y}${te===null?" is-missing":""}`;const W=document.createElement("div");W.className="ops-cascade-step-head";const Ee=document.createElement("div"),Ne=document.createElement("strong");Ne.textContent=ee.label||"-";const Ie=document.createElement("small");Ie.className="ops-cascade-step-meta",Ie.textContent=te===null?e.t("ops.timeline.missingStep"):`${e.t("ops.timeline.stepLabel")} ${fe(te)} · T+${fe(Se??ee.cumulative_ms)}`,Ee.append(Ne,Ie);const Pe=document.createElement("span");Pe.className=`meta-chip status-${lt(String(ee.status||""))}`,Pe.textContent=String(ee.status||(te===null?"missing":"ok")),W.append(Ee,Pe),$e.appendChild(W);const Re=document.createElement("div");Re.className="ops-cascade-track";const ve=document.createElement("span");ve.className="ops-cascade-segment";const Me=Math.max(0,Math.min(100,_e/ie*100)),qe=te===null?0:Math.max(te/ie*100,te>0?2.5:0);ve.style.left=`${Me}%`,ve.style.width=`${qe}%`,ve.setAttribute("aria-label",te===null?`${ee.label}: ${e.t("ops.timeline.missingStep")}`:`${ee.label}: ${fe(te)}`),Re.appendChild(ve),$e.appendChild(Re);const ge=U(ee);if(ge){const me=document.createElement("p");me.className="ops-cascade-step-detail",me.textContent=ge,$e.appendChild(me)}E.appendChild($e)})}async function v(){return(await Ae("/api/ops/runs?limit=30")).runs||[]}async function K(E){return Ae(`/api/ops/runs/${encodeURIComponent(E)}/timeline`)}function M(E,L){var z;const Y=E.run||{};y.textContent=e.t("ops.timeline.label",{id:L}),S.textContent=e.t("ops.timeline.selectedRunMeta",{trace:String(Y.trace_id||"-"),chatRun:String(((z=E.user_waterfall)==null?void 0:z.chat_run_id)||Y.chat_run_id||"-")}),F(c,E.user_waterfall,"user"),F(q,E.technical_waterfall,"technical"),P(_,E.user_waterfall,"user"),P(C,E.technical_waterfall,"technical"),ke(Array.isArray(E.timeline)?E.timeline:[])}function g(E){if(I.innerHTML="",!Array.isArray(E)||E.length===0){const L=document.createElement("tr");L.innerHTML=`<td colspan="4">${e.t("ops.runs.empty")}</td>`,I.appendChild(L);return}E.forEach(L=>{const Y=document.createElement("tr");Y.innerHTML=`
        <td><button type="button" class="link-btn" data-run-id="${L.run_id}">${L.run_id}</button></td>
        <td>${L.trace_id||"-"}</td>
        <td class="status-${lt(String(L.status||""))}">${L.status||"-"}</td>
        <td>${L.started_at?e.formatDateTime(L.started_at,{dateStyle:"short",timeStyle:"short",timeZone:"America/Bogota"}):"-"}</td>
      `,I.appendChild(Y)}),I.querySelectorAll("button[data-run-id]").forEach(L=>{L.addEventListener("click",async()=>{const Y=L.getAttribute("data-run-id")||"";try{const z=await o(async()=>K(Y));M(z,Y)}catch(z){_.innerHTML=`<li class="ops-cascade-step is-empty status-error">${ue(z)}</li>`,C.innerHTML=`<li class="ops-cascade-step is-empty status-error">${ue(z)}</li>`,N.innerHTML=`<li class="status-error">${ue(z)}</li>`}})})}async function ce({showWheel:E=!0,reportError:L=!0}={}){const Y=async()=>{const z=await v();g(z)};try{E?await o(Y):await Y()}catch(z){I.innerHTML=`<tr><td colspan="4" class="status-error">${ue(z)}</td></tr>`,L&&n(ue(z),"error")}}function he(){r==null||r.addEventListener("click",()=>{O("monitor")}),m==null||m.addEventListener("click",()=>{O("ingestion")}),b==null||b.addEventListener("click",()=>{O("control")}),w==null||w.addEventListener("click",()=>{O("embeddings")}),k==null||k.addEventListener("click",()=>{O("reindex")}),X.addEventListener("click",()=>{n(),ce({showWheel:!0,reportError:!0})})}return{bindEvents:he,refreshRuns:ce,renderTabs:re}}function Be(e){return String(e??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#39;")}function st(e){return(e??0).toLocaleString("es-CO")}function pn(e){if(e==null||e<=0)return"-";const t=Math.floor(e/60),s=Math.floor(e%60);return t>0?`${t}m ${s}s`:`${s}s`}function mn(e){if(!e.length)return"";let t='<ol class="reindex-stage-list">';for(const s of e){const o=s.state==="completed"?"ops-dot-ok":s.state==="active"?"ops-dot-active":s.state==="failed"?"ops-dot-error":"ops-dot-pending",n=s.state==="active"?`<strong>${Be(s.label)}</strong>`:Be(s.label);t+=`<li class="reindex-stage-item reindex-stage-${s.state}"><span class="ops-dot ${o}">●</span> ${n}</li>`}return t+="</ol>",t}function as({dom:e,setFlash:t,navigateToEmbeddings:s}){const{container:o}=e;let n=null,r="";function m(){var S,_,c;const B=n;if(!B){o.innerHTML='<p class="ops-text-muted">Cargando estado de re-index...</p>';return}const h=B.current_operation||B.last_operation,R=((S=B.current_operation)==null?void 0:S.status)==="running",D=!B.current_operation;let I="";const N=R?"En ejecución":D?"Inactivo":(h==null?void 0:h.status)??"—",y=R?"tone-yellow":(h==null?void 0:h.status)==="completed"?"tone-green":(h==null?void 0:h.status)==="failed"?"tone-red":"";if(I+=`<div class="reindex-status-row">
      <span class="corpus-status-chip ${y}">${Be(N)}</span>
      <span class="emb-target-badge">WIP</span>
      ${R?`<span class="emb-heartbeat ${xt(h==null?void 0:h.heartbeat_at,h==null?void 0:h.updated_at)}">${xt(h==null?void 0:h.heartbeat_at,h==null?void 0:h.updated_at)}</span>`:""}
    </div>`,I+='<div class="reindex-controls">',D&&(I+=`<button class="corpus-btn corpus-btn-promote" id="reindex-start-btn" ${r?"disabled":""}>Iniciar re-index</button>`),R&&h&&(I+=`<button class="corpus-btn corpus-btn-rollback" id="reindex-stop-btn" ${r?"disabled":""}>Detener</button>`),I+="</div>",(_=h==null?void 0:h.stages)!=null&&_.length&&(I+=mn(h.stages)),h!=null&&h.progress){const C=h.progress,q=[];C.documents_processed!=null&&q.push(`Documentos: ${st(C.documents_processed)} / ${st(C.documents_total)}`),C.documents_indexed!=null&&q.push(`Documentos indexados: ${st(C.documents_indexed)}`),C.elapsed_seconds!=null&&q.push(`Tiempo: ${pn(C.elapsed_seconds)}`),q.length&&(I+=`<div class="reindex-progress-stats">${q.map(X=>`<span>${Be(X)}</span>`).join("")}</div>`)}if(h!=null&&h.quality_report){const C=h.quality_report;if(I+='<div class="reindex-quality-report">',I+="<h3>Reporte de calidad</h3>",I+=`<div class="emb-stats-grid">
        <div class="emb-stat"><span class="emb-stat-value">${st(C.documents_indexed)}</span><span class="emb-stat-label">Documentos</span></div>
        <div class="emb-stat"><span class="emb-stat-value">${st(C.chunks_generated)}</span><span class="emb-stat-label">Chunks</span></div>
        <div class="emb-stat"><span class="emb-stat-value">${C.blocking_issues??0}</span><span class="emb-stat-label">Blocking issues</span></div>
      </div>`,C.knowledge_class_counts){I+='<div class="reindex-kc-breakdown"><h4>Knowledge classes</h4><dl class="reindex-kc-dl">';for(const[q,X]of Object.entries(C.knowledge_class_counts))I+=`<dt>${Be(q)}</dt><dd>${st(X)}</dd>`;I+="</dl></div>"}I+="</div>",I+=`<div class="reindex-embed-prompt">
        <p>Re-index completado. Para aplicar los nuevos summaries a los embeddings:</p>
        <button class="corpus-btn corpus-btn-promote" id="reindex-embed-now-btn">Embed ahora</button>
      </div>`}if((c=h==null?void 0:h.checks)!=null&&c.length){I+='<div class="emb-checks">';for(const C of h.checks){const q=C.ok?'<span class="ops-dot ops-dot-ok">●</span>':'<span class="ops-dot ops-dot-error">●</span>';I+=`<div class="emb-check">${q} <strong>${Be(C.label)}</strong>: ${Be(C.detail)}</div>`}I+="</div>"}h!=null&&h.log_tail&&(I+=`<details class="emb-log-accordion"><summary>Log</summary><pre class="emb-log-tail">${Be(h.log_tail)}</pre></details>`),h!=null&&h.error&&(I+=`<p class="emb-error">${Be(h.error)}</p>`),o.innerHTML=I}function b(){o.addEventListener("click",B=>{const h=B.target;h.id==="reindex-start-btn"&&w(),h.id==="reindex-stop-btn"&&k(),h.id==="reindex-embed-now-btn"&&s()})}async function w(){r="start",m();try{await je("/api/ops/reindex/start",{mode:"from_source"}),t("Re-index iniciado","success")}catch(B){t(String(B),"error")}r="",await A()}async function k(){var h;const B=(h=n==null?void 0:n.current_operation)==null?void 0:h.job_id;if(B){r="stop",m();try{await je("/api/ops/reindex/stop",{job_id:B}),t("Re-index detenido","success")}catch(R){t(String(R),"error")}r="",await A()}}async function A(){try{n=await Ae("/api/ops/reindex-status")}catch{}m()}return{bindEvents:b,refresh:A}}const Bn=Object.freeze(Object.defineProperty({__proto__:null,createOpsReindexController:as},Symbol.toStringTag,{value:"Module"})),gn=3e3,Gt=8e3;function os({stateController:e,withThinkingWheel:t,setFlash:s,refreshRuns:o,refreshIngestion:n,refreshCorpusLifecycle:r,refreshEmbeddings:m,refreshReindex:b,intervalMs:w}){(async()=>{try{await t(async()=>{await Promise.all([o({showWheel:!1,reportError:!1}),n({showWheel:!1,reportError:!1}),r==null?void 0:r(),m==null?void 0:m(),b==null?void 0:b()])})}catch(R){s(ue(R),"error")}})();let k=null,A=w??Gt;function B(){const R=e.state.selectedSession;return R?ft(String(R.status||""))?!0:(R.documents||[]).some(I=>I.status==="in_progress"||I.status==="processing"||I.status==="extracting"||I.status==="etl"||I.status==="writing"||I.status==="gates"):!1}function h(){const R=w??(B()?gn:Gt);k!==null&&R===A||(k!==null&&window.clearInterval(k),A=R,k=window.setInterval(()=>{o({showWheel:!1,reportError:!1}),n({showWheel:!1,reportError:!1,focusSessionId:e.getFocusedRunningSessionId()}),r==null||r(),m==null||m(),b==null||b(),w||h()},A))}return h(),()=>{k!==null&&(window.clearInterval(k),k=null)}}function is(){const e={activeTab:Ms(),corpora:[],selectedCorpus:"autogenerar",sessions:[],selectedSessionId:Os(),selectedSession:null,pendingFiles:[],intake:[],reviewPlan:null,preflightRunId:0,mutating:!1,folderUploadProgress:null,folderRelativePaths:new Map,rejectedArtifacts:[],preflightManifest:null,preflightScanProgress:null};function t(){return e.corpora.find(c=>c.key===e.selectedCorpus)}function s(c){e.activeTab=c,qs(c)}function o(c){e.corpora=[...c]}function n(c){e.folderUploadProgress=c}function r(c){e.preflightManifest=c}function m(c){e.preflightScanProgress=c}function b(c){e.mutating=c}function w(c){e.pendingFiles=[...c]}function k(c){e.intake=[...c]}function A(c){e.reviewPlan=c?{...c,willIngest:[...c.willIngest],bounced:[...c.bounced]}:null}function B(){return e.preflightRunId+=1,e.preflightRunId}function h(c){e.selectedCorpus=c}function R(c){e.selectedSession=c,e.selectedSessionId=(c==null?void 0:c.session_id)||"",Ds((c==null?void 0:c.session_id)||null),c&&(N=!1)}function D(){N=!0,R(null)}function I(c){e.sessions=[...c]}let N=!1;function y(){if(e.selectedSessionId){const c=e.sessions.find(C=>C.session_id===e.selectedSessionId)||null;R(c);return}if(N){R(null);return}R(e.sessions[0]||null)}function S(c){const C=e.sessions.filter(q=>q.session_id!==c.session_id);e.sessions=[c,...C].sort((q,X)=>Date.parse(String(X.updated_at||0))-Date.parse(String(q.updated_at||0))),R(c)}function _(){var c;return ft(String(((c=e.selectedSession)==null?void 0:c.status)||""))?e.selectedSessionId:""}return{state:e,clearSelectionAfterDelete:D,getFocusedRunningSessionId:_,selectedCorpusConfig:t,setActiveTab:s,setCorpora:o,setFolderUploadProgress:n,setMutating:b,setPendingFiles:w,setIntake:k,setReviewPlan:A,bumpPreflightRunId:B,setPreflightManifest:r,setPreflightScanProgress:m,setSelectedCorpus:h,setSelectedSession:R,setSessions:I,syncSelectedSession:y,upsertSession:S}}function bn(e){const{value:t,unit:s,size:o="md",className:n=""}=e,r=document.createElement("span");r.className=["lia-metric-value",`lia-metric-value--${o}`,n].filter(Boolean).join(" "),r.setAttribute("data-lia-component","metric-value");const m=document.createElement("span");if(m.className="lia-metric-value__number",m.textContent=typeof t=="number"?t.toLocaleString("es-CO"):String(t),r.appendChild(m),s){const b=document.createElement("span");b.className="lia-metric-value__unit",b.textContent=s,r.appendChild(b)}return r}function gt(e){const{label:t,value:s,unit:o,hint:n,size:r="lg",tone:m="neutral",className:b=""}=e,w=document.createElement("div");w.className=["lia-metric-card",`lia-metric-card--${m}`,b].filter(Boolean).join(" "),w.setAttribute("data-lia-component","metric-card");const k=document.createElement("p");if(k.className="lia-metric-card__label",k.textContent=t,w.appendChild(k),w.appendChild(bn({value:s,unit:o,size:r})),n){const A=document.createElement("p");A.className="lia-metric-card__hint",A.textContent=n,w.appendChild(A)}return w}function fn(e){if(!e)return"sin activar";try{const t=new Date(e);if(Number.isNaN(t.getTime()))return"—";const s=Date.now()-t.getTime(),o=Math.floor(s/6e4);if(o<1)return"hace instantes";if(o<60)return`hace ${o} min`;const n=Math.floor(o/60);return n<24?`hace ${n} h`:`hace ${Math.floor(n/24)} d`}catch{return"—"}}function hn(e){const t=document.createElement("section");t.className="lia-corpus-overview",t.setAttribute("data-lia-component","corpus-overview");const s=document.createElement("header");s.className="lia-corpus-overview__header";const o=document.createElement("h2");o.className="lia-corpus-overview__title",o.textContent="Corpus activo",s.appendChild(o);const n=document.createElement("p");if(n.className="lia-corpus-overview__subtitle",e.activeGenerationId){const m=document.createElement("code");m.textContent=e.activeGenerationId,n.appendChild(document.createTextNode("Generación ")),n.appendChild(m),n.appendChild(document.createTextNode(` · activada ${fn(e.activatedAt)}`))}else n.textContent="Ninguna generación activa en Supabase.";s.appendChild(n),t.appendChild(s);const r=document.createElement("div");return r.className="lia-corpus-overview__grid",r.appendChild(gt({label:"Documentos servidos",value:e.documents,hint:e.documents>0?`${e.chunks.toLocaleString("es-CO")} chunks indexados`:"—"})),r.appendChild(gt({label:"Grafo de normativa",value:e.graphNodes,unit:"nodos",hint:`${e.graphEdges.toLocaleString("es-CO")} relaciones tipadas`,tone:e.graphOk?"success":"warning"})),r.appendChild(gt({label:"Auditoría del corpus",value:e.auditIncluded,unit:"incluidos",hint:`${e.auditScanned.toLocaleString("es-CO")} escaneados · ${e.auditExcluded.toLocaleString("es-CO")} excluidos`})),r.appendChild(gt({label:"Revisiones pendientes",value:e.auditPendingRevisions,hint:e.auditPendingRevisions===0?"Cuello limpio":"Requieren resolución",tone:e.auditPendingRevisions===0?"success":"warning"})),t.appendChild(r),t}function vn(e){const{tone:t,pulse:s=!1,ariaLabel:o,className:n=""}=e,r=document.createElement("span");return r.className=["lia-status-dot",`lia-status-dot--${t}`,s?"lia-status-dot--pulse":"",n].filter(Boolean).join(" "),r.setAttribute("data-lia-component","status-dot"),r.setAttribute("role","status"),o&&r.setAttribute("aria-label",o),r}const yn={active:"active",superseded:"idle",running:"running",queued:"running",failed:"error",pending:"warning"},Jt={active:"Activa",superseded:"Reemplazada",running:"En curso",queued:"En cola",failed:"Falló",pending:"Pendiente"};function rs(e){const{status:t,className:s=""}=e,o=document.createElement("span");o.className=["lia-run-status",`lia-run-status--${t}`,s].filter(Boolean).join(" "),o.setAttribute("data-lia-component","run-status"),o.appendChild(vn({tone:yn[t],pulse:t==="running"||t==="queued",ariaLabel:Jt[t]}));const n=document.createElement("span");return n.className="lia-run-status__label",n.textContent=Jt[t],o.appendChild(n),o}function _n(e){if(!e)return"—";try{const t=new Date(e);return Number.isNaN(t.getTime())?"—":t.toLocaleString("es-CO",{day:"numeric",month:"short",hour:"2-digit",minute:"2-digit"})}catch{return e}}function $n(e,t){const s=document.createElement(t?"button":"div");s.className="lia-generation-row",s.setAttribute("data-lia-component","generation-row"),t&&(s.type="button",s.addEventListener("click",()=>t(e.generationId)));const o=document.createElement("span");o.className="lia-generation-row__id",o.textContent=e.generationId,s.appendChild(o),s.appendChild(rs({status:e.status}));const n=document.createElement("span");n.className="lia-generation-row__date",n.textContent=_n(e.generatedAt),s.appendChild(n);const r=document.createElement("span");r.className="lia-generation-row__count",r.textContent=`${e.documents.toLocaleString("es-CO")} docs`,s.appendChild(r);const m=document.createElement("span");if(m.className="lia-generation-row__count lia-generation-row__count--muted",m.textContent=`${e.chunks.toLocaleString("es-CO")} chunks`,s.appendChild(m),e.topClass&&e.topClassCount){const b=document.createElement("span");b.className="lia-generation-row__family",b.textContent=`${e.topClass}: ${e.topClassCount.toLocaleString("es-CO")}`,s.appendChild(b)}return s}function Vt(e){const{rows:t,emptyMessage:s="Aún no hay generaciones registradas.",errorMessage:o,onSelect:n}=e,r=document.createElement("section");r.className="lia-generations-list",r.setAttribute("data-lia-component","generations-list");const m=document.createElement("header");m.className="lia-generations-list__header";const b=document.createElement("h2");b.className="lia-generations-list__title",b.textContent="Generaciones recientes",m.appendChild(b);const w=document.createElement("p");w.className="lia-generations-list__subtitle",w.textContent="Cada fila es una corrida de python -m lia_graph.ingest publicada en Supabase.",m.appendChild(w),r.appendChild(m);const k=document.createElement("div");if(k.className="lia-generations-list__body",o){const A=document.createElement("p");A.className="lia-generations-list__feedback lia-generations-list__feedback--error",A.textContent=o,k.appendChild(A)}else if(t.length===0){const A=document.createElement("p");A.className="lia-generations-list__feedback",A.textContent=s,k.appendChild(A)}else{const A=document.createElement("div");A.className="lia-generations-list__head-row",["Generación","Estado","Fecha","Documentos","Chunks","Familia principal"].forEach(B=>{const h=document.createElement("span");h.className="lia-generations-list__head-cell",h.textContent=B,A.appendChild(h)}),k.appendChild(A),t.forEach(B=>k.appendChild($n(B,n)))}return r.appendChild(k),r}const wn=[{key:"knowledge_base",label:"knowledge_base/",sublabel:"snapshot Dropbox"},{key:"wip",label:"WIP",sublabel:"Supabase local + Falkor local"},{key:"cloud",label:"Cloud",sublabel:"Supabase cloud + Falkor cloud"}];function kn(e){const{activeStage:t,className:s=""}=e,o=document.createElement("nav");return o.className=["lia-pipeline-flow",s].filter(Boolean).join(" "),o.setAttribute("data-lia-component","pipeline-flow"),o.setAttribute("aria-label","Pipeline de ingestión Lia Graph"),wn.forEach((n,r)=>{if(r>0){const k=document.createElement("span");k.className="lia-pipeline-flow__arrow",k.setAttribute("aria-hidden","true"),k.textContent="→",o.appendChild(k)}const m=document.createElement("div");m.className=["lia-pipeline-flow__stage",n.key===t?"lia-pipeline-flow__stage--active":""].filter(Boolean).join(" "),m.setAttribute("data-stage",n.key);const b=document.createElement("span");b.className="lia-pipeline-flow__label",b.textContent=n.label,m.appendChild(b);const w=document.createElement("span");w.className="lia-pipeline-flow__sublabel",w.textContent=n.sublabel,m.appendChild(w),o.appendChild(m)}),o}function Sn(e){const{activeJobId:t,lastRunStatus:s,disabled:o,onTrigger:n}=e,r=document.createElement("section");r.className="lia-run-trigger",r.setAttribute("data-lia-component","run-trigger-card");const m=document.createElement("header");m.className="lia-run-trigger__header";const b=document.createElement("h2");b.className="lia-run-trigger__title",b.textContent="Iniciar nueva ingesta",m.appendChild(b);const w=document.createElement("p");w.className="lia-run-trigger__subtitle",w.textContent="Ejecuta make phase2-graph-artifacts-supabase contra knowledge_base/. Por defecto escribe a WIP (Supabase local + FalkorDB local). Cuando WIP esté validado, promueve a Cloud desde la pestaña Promoción.",m.appendChild(w),r.appendChild(m),r.appendChild(kn({activeStage:"wip"}));const k=document.createElement("form");k.className="lia-run-trigger__form",k.setAttribute("novalidate","");const A=Cn({name:"supabase_target",legend:"Destino Supabase",options:[{value:"wip",label:"WIP (local)",hint:"Supabase docker + FalkorDB docker — ciclo seguro",defaultChecked:!0},{value:"production",label:"Producción (cloud)",hint:"Supabase cloud + FalkorDB cloud — afecta runtime servido"}]});k.appendChild(A);const B=En({name:"suin_scope",label:"Scope SUIN-Juriscol",placeholder:"vacío para omitir, ej: et",hint:"Cuando es vacío, sólo se reingiere el corpus base. Pasa el scope (et, tributario, laboral, jurisprudencia) para incluir SUIN."});k.appendChild(B);const h=document.createElement("div");h.className="lia-run-trigger__submit-row";const R=document.createElement("button");if(R.type="submit",R.className="lia-button lia-button--primary lia-run-trigger__submit",R.textContent=t?"Ejecutando…":"Iniciar ingesta",R.disabled=o,h.appendChild(R),s&&h.appendChild(rs({status:s})),t){const D=document.createElement("code");D.className="lia-run-trigger__job-id",D.textContent=t,h.appendChild(D)}return k.appendChild(h),k.addEventListener("submit",D=>{if(D.preventDefault(),o)return;const I=new FormData(k),N=I.get("supabase_target")||"wip",y=String(I.get("suin_scope")||"").trim();n({suinScope:y,supabaseTarget:N==="production"?"production":"wip"})}),r.appendChild(k),r}function Cn(e){const t=document.createElement("fieldset");t.className="lia-run-trigger__field lia-run-trigger__field--radio";const s=document.createElement("legend");return s.className="lia-run-trigger__legend",s.textContent=e.legend,t.appendChild(s),e.options.forEach(o=>{const n=document.createElement("label");n.className="lia-run-trigger__radio-row";const r=document.createElement("input");r.type="radio",r.name=e.name,r.value=o.value,o.defaultChecked&&(r.defaultChecked=!0),n.appendChild(r);const m=document.createElement("span");m.className="lia-run-trigger__radio-text";const b=document.createElement("span");if(b.className="lia-run-trigger__radio-label",b.textContent=o.label,m.appendChild(b),o.hint){const w=document.createElement("span");w.className="lia-run-trigger__radio-hint",w.textContent=o.hint,m.appendChild(w)}n.appendChild(m),t.appendChild(n)}),t}function En(e){const t=document.createElement("div");t.className="lia-run-trigger__field lia-run-trigger__field--text";const s=document.createElement("label");s.className="lia-run-trigger__label",s.htmlFor=`lia-run-trigger-${e.name}`,s.textContent=e.label,t.appendChild(s);const o=document.createElement("input");if(o.type="text",o.id=`lia-run-trigger-${e.name}`,o.name=e.name,o.className="lia-input lia-run-trigger__input",o.autocomplete="off",o.spellcheck=!1,e.placeholder&&(o.placeholder=e.placeholder),t.appendChild(o),e.hint){const n=document.createElement("p");n.className="lia-run-trigger__hint",n.textContent=e.hint,t.appendChild(n)}return t}async function Pn(e,t){const{response:s,data:o}=await je(e,t);if(!s.ok){const n=o&&typeof o=="object"&&"error"in o?String(o.error||s.statusText):s.statusText;throw new nt(n,s.status,o)}if(!o)throw new nt("Empty response",s.status,null);return o}function xn(e){const t=e.querySelector("[data-slot=corpus-overview]"),s=e.querySelector("[data-slot=run-trigger]"),o=e.querySelector("[data-slot=generations-list]");if(!t||!s||!o)return e.textContent="Sesiones: missing render slots.",{refresh:async()=>{},destroy:()=>{}};const n={activeJobId:null,lastRunStatus:null,pollHandle:null};function r(){s.replaceChildren(Sn({activeJobId:n.activeJobId,lastRunStatus:n.lastRunStatus,disabled:n.activeJobId!==null,onTrigger:({suinScope:N,supabaseTarget:y})=>{w({suinScope:N,supabaseTarget:y})}}))}async function m(){t.replaceChildren(h("overview"));try{const N=await Ae("/api/ingest/state"),y={documents:N.corpus.documents,chunks:N.corpus.chunks,graphNodes:N.graph.nodes,graphEdges:N.graph.edges,graphOk:N.graph.ok,auditScanned:N.audit.scanned,auditIncluded:N.audit.include_corpus,auditExcluded:N.audit.exclude_internal,auditPendingRevisions:N.audit.pending_revisions,activeGenerationId:N.corpus.active_generation_id,activatedAt:N.corpus.activated_at};t.replaceChildren(hn(y))}catch(N){t.replaceChildren(R("No se pudo cargar el estado del corpus.",N))}}async function b(){o.replaceChildren(h("generations"));try{const y=((await Ae("/api/ingest/generations?limit=20")).generations||[]).map(S=>{const _=S.knowledge_class_counts||{},c=Object.entries(_).sort((C,q)=>q[1]-C[1])[0];return{generationId:S.generation_id,status:S.is_active?"active":"superseded",generatedAt:S.generated_at,documents:Number(S.documents)||0,chunks:Number(S.chunks)||0,topClass:c==null?void 0:c[0],topClassCount:c==null?void 0:c[1]}});o.replaceChildren(Vt({rows:y}))}catch(N){o.replaceChildren(Vt({rows:[],errorMessage:`No se pudieron cargar las generaciones: ${D(N)}`}))}}async function w(N){n.lastRunStatus="queued",r();try{const y=await Pn("/api/ingest/run",{suin_scope:N.suinScope,supabase_target:N.supabaseTarget});n.activeJobId=y.job_id,n.lastRunStatus="running",r(),k()}catch(y){n.lastRunStatus="failed",n.activeJobId=null,r(),I(`No se pudo iniciar la ingesta: ${D(y)}`)}}function k(){A(),n.pollHandle=window.setInterval(()=>{if(!n.activeJobId){A();return}B(n.activeJobId)},4e3)}function A(){n.pollHandle!==null&&(window.clearInterval(n.pollHandle),n.pollHandle=null)}async function B(N){var y;try{const _=(await Ae(`/api/jobs/${N}`)).job;if(!_)return;if(_.status==="completed"){const c=(((y=_.result_payload)==null?void 0:y.exit_code)??1)===0;n.lastRunStatus=c?"active":"failed",n.activeJobId=null,r(),A(),c&&await Promise.all([m(),b()])}else _.status==="failed"&&(n.lastRunStatus="failed",n.activeJobId=null,r(),A())}catch{}}function h(N){const y=document.createElement("div");return y.className=`lia-ingest-skeleton lia-ingest-skeleton--${N}`,y.setAttribute("aria-hidden","true"),y.textContent="Cargando…",y}function R(N,y){const S=document.createElement("div");S.className="lia-ingest-error",S.setAttribute("role","alert");const _=document.createElement("strong");_.textContent=N,S.appendChild(_);const c=document.createElement("p");return c.className="lia-ingest-error__detail",c.textContent=D(y),S.appendChild(c),S}function D(N){return N instanceof Error?N.message:typeof N=="string"?N:"Error desconocido"}function I(N){const y=document.createElement("div");y.className="lia-ingest-toast",y.textContent=N,e.prepend(y),window.setTimeout(()=>y.remove(),4e3)}return r(),Promise.all([m(),b()]),{async refresh(){await Promise.all([m(),b()])},destroy(){A()}}}function Nn(e,{i18n:t}){const s=e,o=s.querySelector("#lia-ingest-shell");let n=null;o&&(n=xn(o),window.setInterval(()=>{n==null||n.refresh()},3e4));const r=o!==null,m=s.querySelector("#ops-tab-monitor"),b=s.querySelector("#ops-tab-ingestion"),w=s.querySelector("#ops-tab-control"),k=s.querySelector("#ops-tab-embeddings"),A=s.querySelector("#ops-tab-reindex"),B=s.querySelector("#ops-panel-monitor"),h=s.querySelector("#ops-panel-ingestion"),R=s.querySelector("#ops-panel-control"),D=s.querySelector("#ops-panel-embeddings"),I=s.querySelector("#ops-panel-reindex"),N=s.querySelector("#runs-body"),y=s.querySelector("#timeline"),S=s.querySelector("#timeline-meta"),_=s.querySelector("#cascade-note"),c=s.querySelector("#user-cascade"),C=s.querySelector("#user-cascade-summary"),q=s.querySelector("#technical-cascade"),X=s.querySelector("#technical-cascade-summary"),pe=s.querySelector("#refresh-runs"),fe=!!(N&&y&&S&&_&&c&&C&&q&&X&&pe),O=r?null:Q(s,"#ingestion-flash"),re=is();function ke(ae="",ut="success"){if(O){if(!ae){O.hidden=!0,O.textContent="",O.removeAttribute("data-tone");return}O.hidden=!1,O.dataset.tone=ut,O.textContent=ae}}const F=r?null:Q(s,"#ingestion-corpus"),U=r?null:Q(s,"#ingestion-batch-type"),P=r?null:Q(s,"#ingestion-dropzone"),v=r?null:Q(s,"#ingestion-file-input"),K=r?null:Q(s,"#ingestion-folder-input"),M=r?null:Q(s,"#ingestion-pending-files"),g=r?null:Q(s,"#ingestion-overview"),ce=r?null:Q(s,"#ingestion-refresh"),he=r?null:Q(s,"#ingestion-create-session"),E=r?null:Q(s,"#ingestion-select-files"),L=r?null:Q(s,"#ingestion-select-folder"),Y=r?null:Q(s,"#ingestion-upload-files"),z=r?null:Q(s,"#ingestion-upload-progress"),ie=r?null:Q(s,"#ingestion-process-session"),ee=r?null:Q(s,"#ingestion-auto-process"),te=r?null:Q(s,"#ingestion-validate-batch"),_e=r?null:Q(s,"#ingestion-retry-session"),Se=r?null:Q(s,"#ingestion-delete-session"),$e=r?null:Q(s,"#ingestion-session-meta"),W=r?null:Q(s,"#ingestion-sessions-list"),Ee=r?null:Q(s,"#selected-session-meta"),Ne=r?null:Q(s,"#ingestion-last-error"),Ie=r?null:Q(s,"#ingestion-last-error-message"),Pe=r?null:Q(s,"#ingestion-last-error-guidance"),Re=r?null:Q(s,"#ingestion-last-error-next"),ve=r?null:Q(s,"#ingestion-kanban"),Me=r?null:Q(s,"#ingestion-log-accordion"),qe=r?null:Q(s,"#ingestion-log-body"),ge=r?null:Q(s,"#ingestion-log-copy"),me=r?null:Q(s,"#ingestion-auto-status"),Xe=s.querySelector("#ingestion-add-corpus-btn"),Fe=s.querySelector("#add-corpus-dialog"),Ze=s.querySelector("#ingestion-bounce-log"),Qe=s.querySelector("#ingestion-bounce-body"),et=s.querySelector("#ingestion-bounce-copy");async function He(ae){return ae()}const de=fe?ns({i18n:t,stateController:re,dom:{monitorTabBtn:m,ingestionTabBtn:b,controlTabBtn:w,embeddingsTabBtn:k,reindexTabBtn:A,monitorPanel:B,ingestionPanel:h,controlPanel:R,embeddingsPanel:D,reindexPanel:I,runsBody:N,timelineNode:y,timelineMeta:S,cascadeNote:_,userCascadeNode:c,userCascadeSummary:C,technicalCascadeNode:q,technicalCascadeSummary:X,refreshRunsBtn:pe},withThinkingWheel:He,setFlash:ke}):null,be=r?null:un({i18n:t,stateController:re,dom:{ingestionCorpusSelect:F,ingestionBatchTypeSelect:U,ingestionDropzone:P,ingestionFileInput:v,ingestionFolderInput:K,ingestionSelectFilesBtn:E,ingestionSelectFolderBtn:L,ingestionUploadProgress:z,ingestionPendingFiles:M,ingestionOverview:g,ingestionRefreshBtn:ce,ingestionCreateSessionBtn:he,ingestionUploadBtn:Y,ingestionProcessBtn:ie,ingestionAutoProcessBtn:ee,ingestionValidateBatchBtn:te,ingestionRetryBtn:_e,ingestionDeleteSessionBtn:Se,ingestionSessionMeta:$e,ingestionSessionsList:W,selectedSessionMeta:Ee,ingestionLastError:Ne,ingestionLastErrorMessage:Ie,ingestionLastErrorGuidance:Pe,ingestionLastErrorNext:Re,ingestionKanban:ve,ingestionLogAccordion:Me,ingestionLogBody:qe,ingestionLogCopyBtn:ge,ingestionAutoStatus:me,addCorpusBtn:Xe,addCorpusDialog:Fe,ingestionBounceLog:Ze,ingestionBounceBody:Qe,ingestionBounceCopy:et},withThinkingWheel:He,setFlash:ke}),Oe=s.querySelector("#corpus-lifecycle"),Z=Oe?Kt({dom:{container:Oe},setFlash:ke}):null,dt=s.querySelector("#embeddings-lifecycle"),Ue=dt?Qt({dom:{container:dt},setFlash:ke}):null,at=s.querySelector("#reindex-lifecycle"),ze=at?as({dom:{container:at},setFlash:ke,navigateToEmbeddings:()=>{re.setActiveTab("embeddings"),de==null||de.renderTabs()}}):null;de==null||de.bindEvents(),be==null||be.bindEvents(),Z==null||Z.bindEvents(),Ue==null||Ue.bindEvents(),ze==null||ze.bindEvents(),de==null||de.renderTabs(),be==null||be.render(),os({stateController:re,withThinkingWheel:He,setFlash:ke,refreshRuns:(de==null?void 0:de.refreshRuns)??(async()=>{}),refreshIngestion:(be==null?void 0:be.refreshIngestion)??(async()=>{}),refreshCorpusLifecycle:Z==null?void 0:Z.refresh,refreshEmbeddings:Ue==null?void 0:Ue.refresh,refreshReindex:ze==null?void 0:ze.refresh})}function In(e,{i18n:t}){const s=e,o=s.querySelector("#runs-body"),n=s.querySelector("#timeline"),r=s.querySelector("#timeline-meta"),m=s.querySelector("#cascade-note"),b=s.querySelector("#user-cascade"),w=s.querySelector("#user-cascade-summary"),k=s.querySelector("#technical-cascade"),A=s.querySelector("#technical-cascade-summary"),B=s.querySelector("#refresh-runs");if(!o||!n||!r||!m||!b||!w||!k||!A||!B)return;const h=is(),R=async N=>N(),D=()=>{},I=ns({i18n:t,stateController:h,dom:{monitorTabBtn:null,ingestionTabBtn:null,controlTabBtn:null,embeddingsTabBtn:null,reindexTabBtn:null,monitorPanel:null,ingestionPanel:null,controlPanel:null,embeddingsPanel:null,reindexPanel:null,runsBody:o,timelineNode:n,timelineMeta:r,cascadeNote:m,userCascadeNode:b,userCascadeSummary:w,technicalCascadeNode:k,technicalCascadeSummary:A,refreshRunsBtn:B},withThinkingWheel:R,setFlash:D});I.bindEvents(),I.renderTabs(),os({stateController:h,withThinkingWheel:R,setFlash:D,refreshRuns:I.refreshRuns,refreshIngestion:async()=>{}})}const jn=Object.freeze(Object.defineProperty({__proto__:null,mountBackstageApp:In,mountOpsApp:Nn},Symbol.toStringTag,{value:"Module"}));export{Nn as a,ks as b,Dn as c,Bn as d,jn as e,In as m,On as o,_s as r,qn as s};
