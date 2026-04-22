import{q as ae}from"./bootstrap-BApbUZ11.js";import{g as De,p as Ge,A as et}from"./client-OE0sHIIg.js";import{p as It}from"./colors-ps0hVFT8.js";import{g as gt}from"./index-DF3uq1vv.js";import{getToastController as yn}from"./toasts-Dx3CUztl.js";import{c as $n}from"./badge-UV61UhzD.js";import{c as dt}from"./chip-Bjq03GaS.js";function wn(){return`
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

      <div class="lia-ingest-shell__grid lia-ingest-shell__grid--phase5">
        <div class="lia-ingest-shell__col lia-ingest-shell__col--primary" data-slot="intake-zone"></div>
        <div class="lia-ingest-shell__col lia-ingest-shell__col--secondary" data-slot="progress-timeline"></div>
      </div>

      <div class="lia-ingest-shell__row" data-slot="log-console"></div>

      <div class="lia-ingest-shell__row" data-slot="generations-list"></div>
    </main>
  `}function kn(e){return`
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
  `}function Cn(e){return`
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
  `}function Sn(e){return`
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
        <button
          class="ingestion-subtab"
          type="button"
          role="tab"
          data-ingestion-section="subtopics"
          aria-selected="false"
        >Sub-temas</button>
      </nav>

      <div id="ingestion-section-sesiones" class="ingestion-section" role="tabpanel">
        ${wn()}
      </div>

      <div id="ingestion-section-promocion" class="ingestion-section" role="tabpanel" hidden></div>

      <div id="ingestion-section-subtopics" class="ingestion-section" role="tabpanel" hidden></div>
    </div>
  `}function En(){return`
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
  `}function Pn(e){return`
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
      ${kn()}
    </main>
  `}const ha=Object.freeze(Object.defineProperty({__proto__:null,renderBackstageShell:Cn,renderIngestionShell:Sn,renderOpsShell:Pn,renderPromocionShell:En},Symbol.toStringTag,{value:"Module"})),Nn=2e3;function U(e){return String(e??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#39;")}function ue(e){return(e??0).toLocaleString("es-CO")}function In(e){if(!e)return"-";try{return new Date(e).toLocaleDateString("es-CO",{day:"numeric",month:"short",hour:"2-digit",minute:"2-digit",timeZone:"America/Bogota"})}catch{return e}}function xt(e){if(!e)return"-";const t=Date.parse(e);if(Number.isNaN(t))return e;const n=Math.max(0,Math.floor((Date.now()-t)/1e3));if(n<5)return"ahora";if(n<60)return`hace ${n}s`;const s=Math.floor(n/60),a=n%60;return s<60?`hace ${s}m ${a}s`:`hace ${Math.floor(s/60)}h ${s%60}m`}function je(e){return e?e.length>24?`${e.slice(0,15)}…${e.slice(-8)}`:e:"-"}function xn(e){return e===void 0?'<span class="ops-dot ops-dot-unknown">●</span>':e?'<span class="ops-dot ops-dot-ok">●</span>':'<span class="ops-dot ops-dot-error">●</span>'}function At(e,t){if(!t.available)return`
      <div class="corpus-card corpus-card-unavailable">
        <h4 class="corpus-card-title">${U(e)}</h4>
        <p class="corpus-card-unavail">● no disponible</p>
        ${t.error?`<p class="ops-subcopy">${U(t.error)}</p>`:""}
      </div>`;const n=t.knowledge_class_counts??{};return`
    <div class="corpus-card">
      <h4 class="corpus-card-title">${U(e)}</h4>
      <div class="corpus-card-row"><span>Gen:</span> <code>${U(je(t.generation_id))}</code></div>
      <div class="corpus-card-row"><span>Documentos:</span> <strong>${ue(t.documents)}</strong></div>
      <div class="corpus-card-row"><span>Chunks:</span> <strong>${ue(t.chunks)}</strong></div>
      <div class="corpus-card-row"><span>Embeddings:</span> ${xn(t.embeddings_complete)} ${t.embeddings_complete?"completos":"incompletos"}</div>
      <div class="corpus-card-sep"></div>
      <div class="corpus-card-row corpus-card-row-sm"><span>normative_base:</span> ${ue(n.normative_base)}</div>
      <div class="corpus-card-row corpus-card-row-sm"><span>interpretative:</span> ${ue(n.interpretative_guidance)}</div>
      <div class="corpus-card-row corpus-card-row-sm"><span>practica_erp:</span> ${ue(n.practica_erp)}</div>
      <div class="corpus-card-sep"></div>
      <div class="corpus-card-row corpus-card-row-sm"><span>${e==="PRODUCTION"?"Activado:":"Actualizado:"}</span> ${U(In(t.activated_at))}</div>
    </div>`}function Tt(e,t={}){const{onlyFailures:n=!1}=t,s=(e??[]).filter(a=>n?!a.ok:!0);return s.length===0?"":`
    <ul class="corpus-checks">
      ${s.map(a=>`
            <li class="corpus-check ${a.ok?"is-ok":"is-fail"}">
              <span class="corpus-check-dot"></span>
              <div>
                <strong>${U(a.label)}</strong>
                <span>${U(a.detail)}</span>
              </div>
            </li>`).join("")}
    </ul>`}function An(e){const t=e??[];return t.length===0?"":`
    <ol class="corpus-stage-list">
      ${t.map(n=>`
            <li class="corpus-stage-item state-${U(n.state)}">
              <span class="corpus-stage-dot"></span>
              <span>${U(n.label)}</span>
            </li>`).join("")}
    </ol>`}function pt(e){const t=String(e||"").trim();return t?t.replaceAll("_"," "):"-"}function Tn(e){return e?e.kind==="audit"?"Audit":e.kind==="rollback"?"Rollback":e.mode==="force_reset"?"Force reset":"Promote":"Promote"}function ht(e){const t=e==null?void 0:e.last_checkpoint;if(!(t!=null&&t.phase))return"-";const n=t.cursor??0,s=t.total??0,a=s>0?(n/s*100).toFixed(1):"0";return`${pt(t.phase)} · ${ue(n)} / ${ue(s)} (${a}%)`}function Lt(e){var s,a;const t=((s=e==null?void 0:e.last_checkpoint)==null?void 0:s.cursor)??(e==null?void 0:e.batch_cursor)??0,n=((a=e==null?void 0:e.last_checkpoint)==null?void 0:a.total)??0;return n<=0?0:Math.min(100,Math.max(0,t/n*100))}function Ln(e){if(!(e!=null&&e.heartbeat_at))return{label:"-",className:""};const t=Math.max(0,(Date.now()-Date.parse(e.heartbeat_at))/1e3);return t<15?{label:"Saludable",className:"hb-healthy"}:t<45?{label:"Lento",className:"hb-slow"}:{label:"Sin respuesta",className:"hb-stale"}}function Rn(e,t){var n,s,a,o,c,i;if(e)switch(e.operation_state_code){case"orphaned_queue":return{severity:"red",title:"Orphaned before start",detail:"The request was queued, but the backend worker never started."};case"stalled_resumable":return{severity:"red",title:"Stalled",detail:(n=e.last_checkpoint)!=null&&n.phase?`Backend stalled after ${pt(e.last_checkpoint.phase)}. Resume is available.`:"Backend stalled, but a checkpoint is available to resume."};case"failed_resumable":return{severity:"red",title:"Resumable",detail:e.error||((a=(s=e.failures)==null?void 0:s[0])==null?void 0:a.message)||"The last run failed after writing a checkpoint. Resume is available."};case"completed":return{severity:"green",title:"Completed",detail:e.kind==="audit"?"WIP audit completed. Artifact written.":e.kind==="rollback"?"Rollback completed and verified.":"Promotion completed and verified."};case"running":return{severity:"yellow",title:"Running",detail:e.current_phase?`Backend phase: ${pt(e.current_phase)}.`:e.stage_label?`Stage: ${e.stage_label}.`:"The backend is processing the promotion."};default:return{severity:e.severity??"red",title:e.severity==="yellow"?"Running":"Failed",detail:e.error||((c=(o=e.failures)==null?void 0:o[0])==null?void 0:c.message)||"The operation ended with an error."}}return t!=null&&t.preflight_ready?{severity:"green",title:"Ready",detail:"WIP audit and promotion preflight are green."}:{severity:"red",title:"Blocked",detail:((i=t==null?void 0:t.preflight_reasons)==null?void 0:i[0])||"Production is not ready for a safe promotion."}}function Mn(e){return e?e.kind==="audit"?"WIP Health Audit":e.kind==="rollback"?"Rollback Production":e.mode==="force_reset"?"Force Reset + Promote Production":"Promote WIP to Production":"Promote WIP to Production"}function Rt(e,t){return!t||t.available===!1?`<tr><td>${U(e)}</td><td colspan="2" class="corpus-report-unavail">no disponible</td></tr>`:`
    <tr>
      <td>${U(e)}</td>
      <td><code>${U(je(t.generation_id))}</code></td>
      <td>${ue(t.documents)} docs · ${ue(t.chunks)} chunks</td>
    </tr>`}function Mt(e,t){const n=new Set;for(const a of Object.keys((e==null?void 0:e.knowledge_class_counts)??{}))n.add(a);for(const a of Object.keys((t==null?void 0:t.knowledge_class_counts)??{}))n.add(a);return n.size===0?"":[...n].sort().map(a=>{const o=((e==null?void 0:e.knowledge_class_counts)??{})[a]??0,c=((t==null?void 0:t.knowledge_class_counts)??{})[a]??0,i=c-o,p=i>0?"is-positive":i<0?"is-negative":"",d=i>0?`+${ue(i)}`:i<0?ue(i):"—";return`
        <tr class="corpus-report-kc-row">
          <td>${U(a)}</td>
          <td>${ue(o)}</td>
          <td>${ue(c)}</td>
          <td class="corpus-report-delta ${p}">${d}</td>
        </tr>`}).join("")}function qn(e,t){if(!e||!t)return"-";const n=Date.parse(e),s=Date.parse(t);if(Number.isNaN(n)||Number.isNaN(s))return"-";const a=Math.max(0,Math.floor((s-n)/1e3)),o=Math.floor(a/60),c=a%60;return o===0?`${c}s`:`${o}m ${c}s`}function On(e){const t=e==null?void 0:e.promotion_summary;if(!t)return"";const{before:n,after:s,delta:a,plan_result:o}=t,c=((a==null?void 0:a.documents)??0)>0?`+${ue(a==null?void 0:a.documents)}`:ue(a==null?void 0:a.documents),i=((a==null?void 0:a.chunks)??0)>0?`+${ue(a==null?void 0:a.chunks)}`:ue(a==null?void 0:a.chunks),p=((a==null?void 0:a.documents)??0)>0?"is-positive":((a==null?void 0:a.documents)??0)<0?"is-negative":"",d=((a==null?void 0:a.chunks)??0)>0?"is-positive":((a==null?void 0:a.chunks)??0)<0?"is-negative":"",y=n||s?`
      <table class="corpus-report-table">
        <thead>
          <tr><th></th><th>Generación</th><th>Documentos / Chunks</th></tr>
        </thead>
        <tbody>
          ${Rt("Antes",n)}
          ${Rt("Después",s)}
        </tbody>
        ${a?`
        <tfoot>
          <tr>
            <td>Delta</td>
            <td></td>
            <td>
              <span class="corpus-report-delta ${p}">${c} docs</span> ·
              <span class="corpus-report-delta ${d}">${i} chunks</span>
            </td>
          </tr>
        </tfoot>`:""}
      </table>
      ${Mt(n,s)?`
      <table class="corpus-report-table corpus-report-table-kc">
        <thead><tr><th>Clase</th><th>Antes</th><th>Después</th><th>Delta</th></tr></thead>
        <tbody>${Mt(n,s)}</tbody>
      </table>`:""}`:"",h=o?`
      <div class="corpus-report-grid">
        ${[{label:"Docs staged",key:"docs_staged"},{label:"Docs upserted",key:"docs_upserted"},{label:"Docs new",key:"docs_new"},{label:"Docs removed",key:"docs_removed"},{label:"Chunks new",key:"chunks_new"},{label:"Chunks changed",key:"chunks_changed"},{label:"Chunks removed",key:"chunks_removed"},{label:"Chunks unchanged",key:"chunks_unchanged"},{label:"Chunks embedded",key:"chunks_embedded"}].filter(N=>o[N.key]!==void 0&&o[N.key]!==null).map(N=>`
              <div class="corpus-report-stat">
                <span class="corpus-report-stat-value">${U(String(o[N.key]??"-"))}</span>
                <span class="corpus-report-stat-label">${U(N.label)}</span>
              </div>`).join("")}
      </div>`:"",$=qn(e==null?void 0:e.started_at,e==null?void 0:e.completed_at);return`
    <div class="corpus-section corpus-report-section">
      <h4>Promotion Report</h4>
      ${y}
      ${h}
      ${$!=="-"?`<p class="corpus-report-duration">Duración: <strong>${U($)}</strong></p>`:""}
    </div>`}function Vt({dom:e,setFlash:t}){let n=null,s=null,a=null,o="",c="",i=null,p=null,d=!1,y=!1,E=!1,h=!1,$=0,N=null,g=0;function P(q,w){s&&clearTimeout(s),t(q,w);const _=e.container.querySelector(".corpus-toast");_&&(_.hidden=!1,_.dataset.tone=w,_.textContent=q,_.classList.remove("corpus-toast-enter"),_.offsetWidth,_.classList.add("corpus-toast-enter")),s=setTimeout(()=>{const b=e.container.querySelector(".corpus-toast");b&&(b.hidden=!0)},6e3)}function m(q,w,_,b="promote"){return new Promise(D=>{p==null||p.remove();const R=document.createElement("div");R.className="corpus-confirm-overlay",p=R,R.innerHTML=`
        <div class="corpus-confirm-dialog">
          <h3 class="corpus-confirm-title">${U(q)}</h3>
          <div class="corpus-confirm-body">${w}</div>
          <div class="corpus-confirm-actions">
            <button class="corpus-btn corpus-btn-rollback" data-action="cancel">Cancelar</button>
            <button class="corpus-btn ${b==="rollback"?"corpus-btn-rollback":"corpus-btn-promote"}" data-action="confirm">${U(_)}</button>
          </div>
        </div>
      `,document.body.appendChild(R),requestAnimationFrame(()=>R.classList.add("is-visible"));function fe(T){p===R&&(p=null),R.classList.remove("is-visible"),setTimeout(()=>R.remove(),180),D(T)}R.addEventListener("click",T=>{const ge=T.target.closest("[data-action]");ge?fe(ge.dataset.action==="confirm"):T.target===R&&fe(!1)})})}async function u(q,w,_,b){if(!o){o=_,I();try{const{response:D,data:R}=await Ge(q,w);D.ok&&(R!=null&&R.job_id)?(i={tone:"success",message:`${b} Job ${je(R.job_id)}.`},P(`${b} Job ${je(R.job_id)}.`,"success")):(i={tone:"error",message:(R==null?void 0:R.error)||"No se pudo iniciar la operación."},P((R==null?void 0:R.error)||"No se pudo iniciar la operación.","error"))}catch(D){const R=D instanceof Error?D.message:String(D);i={tone:"error",message:R},P(R,"error")}finally{o="",await W()}}}async function l(){const q=n;if(!q||o||!await m("Promote WIP to Production",`<p>This path reuses the live WIP generation and promotes it incrementally into Production with persisted checkpoints.</p>
       <table class="corpus-confirm-table">
         <tr><td>Production current:</td><td><strong>${ue(q.production.documents)}</strong> docs · <strong>${ue(q.production.chunks)}</strong> chunks</td></tr>
         <tr><td>WIP source:</td><td><strong>${ue(q.wip.documents)}</strong> docs · <strong>${ue(q.wip.chunks)}</strong> chunks</td></tr>
         <tr><td>WIP generation:</td><td><code>${U(je(q.wip.generation_id))}</code></td></tr>
       </table>
       <label style="display:flex;align-items:center;gap:0.4rem;margin:0.75rem 0;font-size:0.85rem;cursor:pointer">
         <input type="checkbox" id="corpus-force-full-upsert" />
         Forzar upsert completo (sincronizar summaries + embeddings aunque chunk_text no haya cambiado)
       </label>
       <p class="corpus-confirm-note">The backend will keep a promotion plan, batch checkpoints, and a resumable cursor before activation.</p>`,"Promote now"))return;const _=document.querySelector("#corpus-force-full-upsert"),b=(_==null?void 0:_.checked)??!1;h=!1,$=0,N=null,g=0,await u("/api/ops/corpus/rebuild-from-wip",{mode:"promote",force_full_upsert:b},"promote",b?"Promotion started (force full upsert).":"Promotion started.")}async function r(){var _;const q=(n==null?void 0:n.current_operation)??(n==null?void 0:n.last_operation)??null;!(q!=null&&q.resume_job_id)||o||!await m("Resume from Checkpoint",`<p>The backend will reuse the persisted promotion plan and continue from the last completed checkpoint.</p>
       <table class="corpus-confirm-table">
         <tr><td>Job:</td><td><code>${U(je(q.resume_job_id))}</code></td></tr>
         <tr><td>Checkpoint:</td><td>${U(ht(q))}</td></tr>
         <tr><td>Target generation:</td><td><code>${U(je(q.target_generation_id))}</code></td></tr>
       </table>`,"Resume now")||(h=!0,$=((_=q.last_checkpoint)==null?void 0:_.cursor)??0,N=null,g=0,await u("/api/ops/corpus/rebuild-from-wip/resume",{job_id:q.resume_job_id},"resume","Resume started."))}async function f(){const q=n;!q||!q.rollback_generation_id||o||!await m("Rollback de Production",`<p>Se va a intentar reactivar una generación previa de production.</p>
       <table class="corpus-confirm-table">
         <tr><td>Production actual:</td><td><code>${U(je(q.production.generation_id))}</code></td></tr>
         <tr><td>Objetivo:</td><td><code>${U(je(q.rollback_generation_id))}</code></td></tr>
       </table>
       <p class="corpus-confirm-note">Solo se habilita si el backend detecta una generación previa todavía utilizable.</p>`,"Revertir ahora","rollback")||await u("/api/ops/corpus/rollback",{generation_id:q.rollback_generation_id},"rollback","Rollback started.")}async function v(){o||await u("/api/ops/corpus/wip-audit",{},"audit","WIP audit started.")}async function S(){o||!await m("Reiniciar promoción",`<p>Cancela cualquier job anterior y lanza una nueva promoción desde WIP a producción.</p>
       <label style="display:flex;align-items:center;gap:0.4rem;margin:0.75rem 0;font-size:0.85rem;cursor:default;opacity:0.55" title="Force upsert es obligatorio en reinicio">
         <input type="checkbox" checked disabled style="opacity:0.55" />
         Forzar upsert completo (sincronizar summaries + embeddings aunque chunk_text no haya cambiado)
       </label>
       <p class="corpus-confirm-note">Reiniciar siempre usa force upsert: todos los ~50K chunks se copian completos.</p>`,"Reiniciar ahora","rollback")||(h=!1,$=0,N=null,g=0,await u("/api/ops/corpus/rebuild-from-wip/restart",{},"restart","Restart submitted (force full upsert)."))}async function x(){if(!(E||o||!await m("Sincronizar JSONL a WIP",`<p>Se va a sincronizar el índice JSONL local ya existente al Supabase WIP (Docker).</p>
       <p class="corpus-confirm-note">Esta operación no ejecuta reindex — solo sincroniza los documentos y chunks que ya existen en el JSONL local. Es segura e idempotente.</p>`,"Sincronizar ahora"))){E=!0,I();try{const{response:w,data:_}=await Ge("/api/ops/corpus/sync-to-wip",{});w.ok&&(_!=null&&_.synced)?P(`WIP sincronizado: ${ue(_.documents)} docs, ${ue(_.chunks)} chunks.`,"success"):P((_==null?void 0:_.error)||"Error sincronizando a WIP.","error")}catch(w){const _=w instanceof Error?w.message:String(w);P(_||"Error sincronizando a WIP.","error")}finally{E=!1,await W()}}}async function j(){const q=(n==null?void 0:n.current_operation)??(n==null?void 0:n.last_operation)??null,w=String((q==null?void 0:q.log_tail)||"").trim();if(w)try{await navigator.clipboard.writeText(w),P("Log tail copied.","success")}catch(_){const b=_ instanceof Error?_.message:"Could not copy log tail.";P(b||"Could not copy log tail.","error")}}function I(){var Pe,Ce,H,we,le,Ne,Me,qe,be,Ae,Te;const q=e.container.querySelector(".corpus-log-accordion");q&&(d=q.open);const w=e.container.querySelector(".corpus-checks-accordion");w&&(y=w.open);const _=n;if(!_){e.container.innerHTML=`<p class="ops-empty">${U(c||"Cargando estado del corpus…")}</p>`;return}const b=_.current_operation??_.last_operation??null,D=Rn(b,_),R=!!(_.current_operation&&["queued","running"].includes(_.current_operation.status))||!!o,fe=R||!_.preflight_ready,T=!R&&!!(b&&b.resume_supported&&b.resume_job_id&&(b.operation_state_code==="stalled_resumable"||b.operation_state_code==="failed_resumable")),ge=R||!_.rollback_available,L=_.delta.documents==="+0"&&_.delta.chunks==="+0"?"Sin delta pendiente":`${_.delta.documents} documentos · ${_.delta.chunks} chunks`,M=Tt(b==null?void 0:b.checks,{onlyFailures:!0}),te=Tt(b==null?void 0:b.checks),V=!!(_.current_operation&&["queued","running"].includes(_.current_operation.status)),ye=i&&!(_.current_operation&&["queued","running"].includes(_.current_operation.status))?`
          <div class="corpus-callout tone-${U(i.tone==="success"?"green":"red")}">
            <strong>${i.tone==="success"?"Request sent":"Request failed"}</strong>
            <span>${U(i.message)}</span>
          </div>`:"",ie=(Pe=b==null?void 0:b.last_checkpoint)!=null&&Pe.phase?(()=>{const re=b.operation_state_code==="completed"?"green":b.operation_state_code==="failed_resumable"||b.operation_state_code==="stalled_resumable"?"red":"yellow",he=Lt(b);return`
            <div class="corpus-callout tone-${U(re)}">
              <strong>Checkpoint</strong>
              <span>${U(ht(b))} · ${U(xt(b.last_checkpoint.at||null))}</span>
              ${he>0&&re!=="green"?`<div class="corpus-progress-bar corpus-progress-bar-sm"><div class="corpus-progress-fill" style="width:${he.toFixed(1)}%"></div></div>`:""}
            </div>`})():"";e.container.innerHTML=`
      <div class="corpus-cards">
        ${At("WIP",_.wip)}
        ${At("PRODUCTION",_.production)}
      </div>
      <div class="corpus-delta">
        <span class="corpus-delta-label">${U(L)}</span>
      </div>
      <section class="corpus-operation-panel severity-${U(D.severity)}">
        <div class="corpus-operation-header">
          <div>
            <div class="corpus-status-chip tone-${U(D.severity)}${D.severity==="yellow"?" is-pulsing":""}">
              ${U(D.title)}
            </div>
            <h3 class="corpus-operation-title">${U(Mn(b))}</h3>
            <p class="corpus-operation-detail">${U(D.detail)}</p>
          </div>
          <dl class="corpus-operation-meta">
            <div><dt>Heartbeat</dt><dd>${U(xt((b==null?void 0:b.heartbeat_at)||(b==null?void 0:b.updated_at)||null))}</dd></div>
            <div><dt>Backend</dt><dd>${U(Tn(b))}${b!=null&&b.force_full_upsert?` <span style="background:${It.amber[100]};color:${It.amber[600]};padding:0.1rem 0.4rem;border-radius:0.3rem;font-size:0.7rem;font-weight:700">FORCE UPSERT</span>`:""}</dd></div>
            <div><dt>Phase</dt><dd>${U(b!=null&&b.current_phase?pt(b.current_phase):(b==null?void 0:b.stage_label)||(_.preflight_ready?"Ready":"Blocked"))}</dd></div>
            <div><dt>Checkpoint</dt><dd>${U(ht(b))}</dd></div>
            <div><dt>WIP</dt><dd><code>${U(je((b==null?void 0:b.source_generation_id)||_.wip.generation_id))}</code></dd></div>
            <div><dt>Target</dt><dd><code>${U(je((b==null?void 0:b.target_generation_id)||(b==null?void 0:b.production_generation_id)||_.production.generation_id))}</code></dd></div>
            <div><dt>Prod</dt><dd><code>${U(je((b==null?void 0:b.production_generation_id)||_.production.generation_id))}</code></dd></div>
          </dl>
        </div>
        ${V?(()=>{var pe,ne;const re=Lt(b),he=((pe=b==null?void 0:b.last_checkpoint)==null?void 0:pe.cursor)??(b==null?void 0:b.batch_cursor)??0,A=((ne=b==null?void 0:b.last_checkpoint)==null?void 0:ne.total)??0,z=Ln(b);if(he>0&&A>0){const oe=Date.now();if(N&&he>N.cursor){const G=Math.max(1,(oe-N.ts)/1e3),Z=(he-N.cursor)/G;g=g>0?g*.7+Z*.3:Z}N={cursor:he,ts:oe}}const ee=g>0?`${g.toFixed(0)} chunks/s`:"",Y=A-he,X=g>0&&Y>0?(()=>{const oe=Math.ceil(Y/g),G=Math.floor(oe/60),Z=oe%60;return G>0?`~${G}m ${Z}s restante`:`~${Z}s restante`})():"";return`
            <div class="corpus-progress-bar"><div class="corpus-progress-fill" style="width:${re.toFixed(1)}%"></div></div>
            <div class="corpus-progress-detail">
              ${h?`<span class="corpus-resume-badge">REANUDADO desde ${ue($)}</span>`:""}
              <span class="corpus-progress-nums">${ue(he)} / ${ue(A)} (${re.toFixed(1)}%)</span>
              ${ee?`<span class="corpus-progress-rate">${U(ee)}</span>`:""}
              ${X?`<span class="corpus-progress-eta">${U(X)}</span>`:""}
              <span class="corpus-hb-badge ${z.className}">${U(z.label)}</span>
            </div>`})():""}
        ${(Ce=b==null?void 0:b.stages)!=null&&Ce.length?An(b.stages):""}
        ${ie}
        ${(H=_.preflight_reasons)!=null&&H.length&&!V&&!_.preflight_ready?`
          <div class="corpus-callout tone-red">
            <strong>Preflight blocked</strong>
            <ul>${_.preflight_reasons.map(re=>`<li>${U(re)}</li>`).join("")}</ul>
          </div>`:""}
        ${ye}
        ${M?`<div class="corpus-section"><h4>Visible failures</h4>${M}</div>`:""}
        ${te?`
          <details class="corpus-section corpus-checks-accordion">
            <summary class="corpus-checks-summary"><h4>Checks</h4><span class="corpus-checks-count">${((b==null?void 0:b.checks)??[]).length}</span></summary>
            ${te}
          </details>`:""}
        ${On(b)}
        ${b!=null&&b.log_tail?`
          <details class="corpus-section corpus-log-accordion">
            <summary class="corpus-log-summary">
              <h4>Backend log tail</h4>
              <button id="corpus-copy-log-tail-btn" type="button" class="corpus-btn corpus-btn-rollback corpus-btn-inline">Copy</button>
            </summary>
            <pre class="corpus-log-tail">${U(b.log_tail)}</pre>
          </details>`:""}
        ${c?`
          <div class="corpus-callout tone-red">
            <strong>Refresh error</strong>
            <span>${U(c)}</span>
          </div>`:""}
      </section>
      <div class="corpus-actions">
        ${_.audit_missing&&!R?`
          <button id="corpus-audit-btn" class="corpus-btn corpus-btn-audit${o==="audit"?" is-busy":""}">
            ${o==="audit"?'<span class="corpus-spinner"></span> Auditing…':"Run WIP Audit"}
          </button>`:""}
        ${!R&&!E?`
          <button id="corpus-sync-wip-btn" class="corpus-btn corpus-btn-sync">Sincronizar JSONL a WIP</button>`:""}
        ${E?`
          <button class="corpus-btn corpus-btn-sync is-busy" disabled><span class="corpus-spinner"></span> Sincronizando…</button>`:""}
        <button id="corpus-promote-btn" class="corpus-btn corpus-btn-promote${o==="promote"?" is-busy":""}" ${fe?"disabled":""}>
          ${o==="promote"?'<span class="corpus-spinner"></span> Starting…':"Promote WIP to Production"}
        </button>
        ${T?`
          <button id="corpus-resume-btn" class="corpus-btn corpus-btn-promote${o==="resume"?" is-busy":""}">
            ${o==="resume"?'<span class="corpus-spinner"></span> Resuming…':"Resume from Checkpoint"}
          </button>`:""}
        <button id="corpus-rollback-btn" class="corpus-btn corpus-btn-rollback${o==="rollback"?" is-busy":""}" ${ge?"disabled":""}>
          ${o==="rollback"?'<span class="corpus-spinner"></span> Starting rollback…':"Rollback"}
        </button>
        <button id="corpus-restart-btn" class="corpus-btn corpus-btn-rollback${o==="restart"?" is-busy":""}" ${R?"disabled":""}>
          ${o==="restart"?'<span class="corpus-spinner"></span> Restarting…':"Reiniciar promoción (force upsert)"}
        </button>
      </div>
      ${_.preflight_ready?"":`
        <p class="corpus-action-note">${U(((we=_.preflight_reasons)==null?void 0:we[0])||"Promotion is blocked by preflight.")}</p>`}
      ${_.rollback_available?"":`
        <p class="corpus-action-note">${U(_.rollback_reason||"Rollback is not available yet.")}</p>`}
      <div class="corpus-toast ops-flash" hidden></div>
    `,(le=e.container.querySelector("#corpus-audit-btn"))==null||le.addEventListener("click",v),(Ne=e.container.querySelector("#corpus-sync-wip-btn"))==null||Ne.addEventListener("click",()=>void x()),(Me=e.container.querySelector("#corpus-promote-btn"))==null||Me.addEventListener("click",l),(qe=e.container.querySelector("#corpus-resume-btn"))==null||qe.addEventListener("click",r),(be=e.container.querySelector("#corpus-rollback-btn"))==null||be.addEventListener("click",f),(Ae=e.container.querySelector("#corpus-restart-btn"))==null||Ae.addEventListener("click",S),(Te=e.container.querySelector("#corpus-copy-log-tail-btn"))==null||Te.addEventListener("click",re=>{re.preventDefault(),re.stopPropagation(),j()});const me=e.container.querySelector(".corpus-log-accordion");me&&d&&(me.open=!0);const Ee=e.container.querySelector(".corpus-checks-accordion");Ee&&y&&(Ee.open=!0)}async function W(){try{n=await De("/api/ops/corpus-status"),c="",n!=null&&n.current_operation&&["queued","running","completed","failed","cancelled"].includes(n.current_operation.status)&&(i=null)}catch(q){c=q instanceof Error?q.message:String(q),n===null&&(n=null)}I()}function K(){I(),a===null&&(a=window.setInterval(()=>{W()},Nn))}return{bindEvents:K,refresh:W}}const va=Object.freeze(Object.defineProperty({__proto__:null,createCorpusLifecycleController:Vt},Symbol.toStringTag,{value:"Module"})),Fn={normative_base:"Normativa",interpretative_guidance:"Interpretación",practica_erp:"Práctica"},Ct={declaracion_renta:"Renta",iva:"IVA",laboral:"Laboral",facturacion_electronica:"Facturación",estados_financieros_niif:"NIIF",ica:"ICA",calendario_obligaciones:"Calendarios",retencion_fuente:"Retención",regimen_sancionatorio:"Sanciones",regimen_cambiario:"Régimen Cambiario",impuesto_al_patrimonio:"Patrimonio",informacion_exogena:"Exógena",proteccion_de_datos:"Datos",obligaciones_mercantiles:"Mercantil",obligaciones_profesionales_contador:"Obligaciones Contador",rut_responsabilidades:"RUT",gravamen_movimiento_financiero_4x1000:"GMF 4×1000",beneficiario_final:"Beneficiario Final",contratacion_estatal:"Contratación Estatal",reforma_pensional:"Reforma Pensional",zomac_incentivos:"ZOMAC"},Xt="lia_backstage_ops_active_tab",yt="lia_backstage_ops_ingestion_session_id";function Dn(){const e=gt();try{const t=String(e.getItem(Xt)||"").trim();return t==="ingestion"||t==="control"||t==="embeddings"||t==="reindex"?t:"monitor"}catch{return"monitor"}}function Bn(e){const t=gt();try{t.setItem(Xt,e)}catch{}}function jn(){const e=gt();try{return String(e.getItem(yt)||"").trim()}catch{return""}}function zn(e){const t=gt();try{if(!e){t.removeItem(yt);return}t.setItem(yt,e)}catch{}}function ft(e){return e==="processing"||e==="running_batch_gates"}function Zt(e){if(!e)return!1;const t=String(e.status||"").toLowerCase();if(t==="done"||t==="completed")return!0;const n=e.documents||[];return n.length===0?!1:n.every(s=>{const a=String(s.status||"").toLowerCase();return a==="done"||a==="completed"||a==="skipped_duplicate"||a==="bounced"})}function it(e){const t=String(e||"").trim().toLowerCase();return t==="failed"||t==="error"?"error":t==="processing"||t==="running_batch_gates"||t==="needs_retry_batch_gate"||t==="queued"||t==="uploading"||t==="extracting"||t==="etl"||t==="writing"||t==="gates"||t==="in_progress"||t==="partial_failed"||t==="raw"||t==="pending_dedup"?"warn":"ok"}function $e(e){return e instanceof et?e.message||`HTTP ${e.status}`:e instanceof Error?e.message:String(e||"unknown_error")}function Un(e,t){switch(String(e||"").trim()){case"normative_base":return t.t("ops.ingestion.batchType.normative");case"interpretative_guidance":return t.t("ops.ingestion.batchType.interpretative");case"practica_erp":return t.t("ops.ingestion.batchType.practical");default:return String(e||"-")}}function Hn(e,t){const n=Number(e||0);return!Number.isFinite(n)||n<=0?"0 B":n>=1024*1024?`${t.formatNumber(n/(1024*1024),{maximumFractionDigits:1})} MB`:n>=1024?`${t.formatNumber(n/1024,{maximumFractionDigits:1})} KB`:`${t.formatNumber(n)} B`}function qt(e,t){const n=e||{total:0,queued:0,done:0,failed:0,pending_batch_gate:0,bounced:0},s=[`${t.t("ops.ingestion.summary.total")} ${n.total||0}`,`${t.t("ops.ingestion.summary.done")} ${n.done||0}`,`${t.t("ops.ingestion.summary.failed")} ${n.failed||0}`,`${t.t("ops.ingestion.summary.queued")} ${n.queued||0}`,`${t.t("ops.ingestion.summary.gate")} ${n.pending_batch_gate||0}`],a=Number(n.bounced||0);return a>0&&s.push(`Rebotados ${a}`),s.join(" · ")}function $t(e,t,n){const s=e||t||"";if(!s)return"stalled";const a=Date.parse(s);if(Number.isNaN(a))return"stalled";const o=Date.now()-a,c=n==="gates",i=c?9e4:3e4,p=c?3e5:12e4;return o<i?"alive":o<p?"slow":"stalled"}function Wn(e,t){const n=e||t||"";if(!n)return"-";const s=Date.parse(n);if(Number.isNaN(s))return"-";const a=Math.max(0,Date.now()-s),o=Math.floor(a/1e3);if(o<5)return"ahora";if(o<60)return`hace ${o}s`;const c=Math.floor(o/60),i=o%60;return c<60?`hace ${c}m ${i}s`:`hace ${Math.floor(c/60)}h ${c%60}m`}const vt={validating:"validando corpus",manifest:"activando manifest",indexing:"reconstruyendo índice","indexing/scanning":"escaneando documentos","indexing/chunking":"generando chunks","indexing/writing_indexes":"escribiendo índices","indexing/syncing":"sincronizando Supabase","indexing/auditing":"auditando calidad"};function Yt(e){if(!e)return"";if(vt[e])return vt[e];const t=e.indexOf(":");if(t>0){const n=e.slice(0,t),s=e.slice(t+1),a=vt[n];if(a)return`${a} (${s})`}return e}function Gn(e){if(!e)return"";const t=Date.parse(e);if(Number.isNaN(t))return"";try{return new Intl.DateTimeFormat("es-CO",{timeZone:"America/Bogota",day:"2-digit",month:"2-digit",year:"numeric",hour:"2-digit",minute:"2-digit",second:"2-digit",hour12:!1}).format(new Date(t))}catch{return""}}function Qt(e,t){const n=Math.max(0,Math.min(100,Number(e||0))),s=document.createElement("div");s.className="ops-progress";const a=document.createElement("div");a.className="ops-progress-bar";const o=document.createElement("span");o.className="ops-progress-fill",t==="gates"&&n>0&&n<100&&o.classList.add("ops-progress-active"),o.style.width=`${n}%`;const c=document.createElement("span");return c.className="ops-progress-label",c.textContent=`${n}%`,a.appendChild(o),s.append(a,c),s}function He(e){return String(e??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#39;")}function Ve(e){return(e??0).toLocaleString("es-CO")}function Ot(e){if(e==null||e<=0)return"-";const t=Math.floor(e/60),n=Math.floor(e%60);return t>0?`${t}m ${n}s`:`${n}s`}function en({dom:e,setFlash:t}){const{container:n}=e;let s=null,a="",o=!1,c=!1,i=0,p=0,d=3e3,y=[];function E(l){if(l<=0)return;const r=Date.now();if(l>i&&p>0){const f=r-p,v=l-i,S=f/v;y.push(S),y.length>10&&y.shift(),d=y.reduce((x,j)=>x+j,0)/y.length}l!==i&&(i=l,p=r)}function h(){if(p===0)return{level:"healthy",label:"Iniciando..."};const l=Date.now()-p,r=Math.max(d*3,1e4),f=Math.max(d*6,3e4);return l<r?{level:"healthy",label:"Saludable"}:l<f?{level:"caution",label:"Lento"}:{level:"failed",label:"Sin respuesta"}}function $(){var te,V,ye,ie,me,Ee,Pe,Ce;const l=s;if(!l){n.innerHTML='<p class="ops-text-muted">Cargando estado de embeddings...</p>';return}const r=l.current_operation||l.last_operation,f=((te=l.current_operation)==null?void 0:te.status)??"",v=f==="running"||f==="queued"||a==="start",S=!l.current_operation&&!a,x=a==="stop",j=!v&&!x&&((r==null?void 0:r.status)==="cancelled"||(r==null?void 0:r.status)==="failed"||(r==null?void 0:r.status)==="stalled");let I="";const W=(r==null?void 0:r.status)??"",K=x?"Deteniendo...":v?"En ejecución":j?W==="stalled"?"Detenido (stalled)":W==="cancelled"?"Cancelado":"Fallido":S?"Inactivo":W||"—",q=v?"tone-yellow":W==="completed"?"tone-green":W==="failed"||W==="stalled"?"tone-red":W==="cancelled"?"tone-yellow":"",w=l.api_health,_=w!=null&&w.ok?"emb-api-ok":"emb-api-error",b=w?w.ok?`API OK (${w.detail})`:`API Error: ${w.detail}`:"API: verificando...";if(I+=`<div class="emb-status-row">
      <span class="corpus-status-chip ${q}">${He(K)}</span>
      <span class="emb-target-badge">WIP</span>
      <span class="emb-api-semaphore ${_}" title="${He(b)}"><span class="emb-api-dot"></span> ${He(w!=null&&w.ok?"API OK":w?"API Error":"...")}</span>
      ${v?(()=>{const H=h();return`<span class="emb-process-health emb-health-${H.level}"><span class="emb-health-dot"></span> ${He(H.label)}</span>`})():""}
    </div>`,I+='<div class="emb-controls">',S?(I+=`<label class="emb-force-label"><input type="checkbox" id="emb-force-check" ${o?"checked":""} /> Forzar re-embed (todas)</label>`,I+=`<button class="corpus-btn corpus-btn-promote" id="emb-start-btn" ${a?"disabled":""}>Iniciar</button>`):x?I+='<span class="emb-running-label">Deteniendo al finalizar batch actual...</span>':v&&r&&(I+='<button class="corpus-btn corpus-btn-rollback" id="emb-stop-btn">Detener</button>',I+='<span class="emb-running-label">Embebiendo chunks...</span>'),j&&r){const H=r.force,we=(V=r.progress)==null?void 0:V.last_cursor_id,le=(ye=r.progress)==null?void 0:ye.pct_complete,Ne=we?`Reanudar desde ${typeof le=="number"?le.toFixed(1)+"%":"checkpoint"}`:"Reiniciar";H&&(I+='<span class="emb-force-label"><input type="checkbox" checked disabled /> Forzar re-embed (continuación)</span>'),I+=`<button class="corpus-btn corpus-btn-promote" id="emb-resume-btn" ${a?"disabled":""}>${He(Ne)}</button>`,I+=`<button class="corpus-btn" id="emb-start-btn" ${a?"disabled":""} style="opacity:0.7">Iniciar desde cero</button>`}I+="</div>";const D=r==null?void 0:r.progress,R=(v||a)&&(D==null?void 0:D.total),fe=R?D.total:l.total_chunks,T=R?D.embedded:l.embedded_chunks,ge=R?D.pending-D.embedded-(D.failed||0):l.null_embedding_chunks,L=R&&D.failed||0,M=R?D.pct_complete:l.coverage_pct;if(I+=`<div class="emb-stats-grid">
      <div class="emb-stat"><span class="emb-stat-value">${Ve(fe)}</span><span class="emb-stat-label">Total</span></div>
      <div class="emb-stat"><span class="emb-stat-value">${Ve(T)}</span><span class="emb-stat-label">Embebidos</span></div>
      <div class="emb-stat"><span class="emb-stat-value">${Ve(Math.max(0,ge))}</span><span class="emb-stat-label">Pendientes</span></div>
      ${L>0?`<div class="emb-stat emb-stat-error"><span class="emb-stat-value">${Ve(L)}</span><span class="emb-stat-label">Fallidos</span></div>`:`<div class="emb-stat"><span class="emb-stat-value">${M.toFixed(1)}%</span><span class="emb-stat-label">Cobertura</span></div>`}
    </div>`,v&&(r!=null&&r.progress)){const H=r.progress;I+='<div class="emb-live-progress">',I+='<div class="emb-progress-bar-wrap" id="emb-progress-mount"></div>',I+=`<div class="emb-rate-line">
        <span>${((ie=H.rate_chunks_per_sec)==null?void 0:ie.toFixed(1))??"-"} chunks/s</span>
        <span>ETA: ${Ot(H.eta_seconds)}</span>
        <span>Elapsed: ${Ot(H.elapsed_seconds)}</span>
        <span>Batch ${Ve(H.current_batch)} / ${Ve(H.total_batches)}</span>
      </div>`,H.failed>0&&(I+=`<p class="emb-failed-notice">${Ve(H.failed)} chunks fallidos (${(H.failed/Math.max(H.pending,1)*100).toFixed(2)}%)</p>`),I+="</div>"}if(r!=null&&r.quality_report){const H=r.quality_report;I+='<div class="emb-quality-report">',I+="<h3>Reporte de calidad</h3>",I+=`<div class="emb-stats-grid">
        <div class="emb-stat"><span class="emb-stat-value">${((me=H.mean_cosine_similarity)==null?void 0:me.toFixed(4))??"-"}</span><span class="emb-stat-label">Coseno medio</span></div>
        <div class="emb-stat"><span class="emb-stat-value">${((Ee=H.min_cosine_similarity)==null?void 0:Ee.toFixed(4))??"-"}</span><span class="emb-stat-label">Min</span></div>
        <div class="emb-stat"><span class="emb-stat-value">${((Pe=H.max_cosine_similarity)==null?void 0:Pe.toFixed(4))??"-"}</span><span class="emb-stat-label">Max</span></div>
        <div class="emb-stat"><span class="emb-stat-value">${Ve(H.sample_pairs)}</span><span class="emb-stat-label">Pares</span></div>
      </div>`,H.collapsed_warning&&(I+='<p class="emb-anomaly-warning">ANOMALIA: Embeddings colapsados (mean &gt; 0.95)</p>'),H.noise_warning&&(I+='<p class="emb-anomaly-warning">ANOMALIA: Embeddings ruidosos (mean &lt; 0.10)</p>'),!H.collapsed_warning&&!H.noise_warning&&(I+='<p class="emb-quality-ok">Distribución saludable</p>'),I+="</div>"}if((Ce=r==null?void 0:r.checks)!=null&&Ce.length){I+='<div class="emb-checks">';for(const H of r.checks){const we=H.ok?'<span class="ops-dot ops-dot-ok">●</span>':'<span class="ops-dot ops-dot-error">●</span>';I+=`<div class="emb-check">${we} <strong>${He(H.label)}</strong>: ${He(H.detail)}</div>`}I+="</div>"}if(r!=null&&r.log_tail){const H=r.log_tail.split(`
`).reverse().join(`
`);I+=`<details class="emb-log-accordion" id="emb-log-details" ${c?"open":""}><summary>Log</summary><pre class="emb-log-tail">${He(H)}</pre></details>`}if(r!=null&&r.error&&(I+=`<p class="emb-error">${He(r.error)}</p>`),n.innerHTML=I,v&&(r!=null&&r.progress)){const H=n.querySelector("#emb-progress-mount");H&&H.appendChild(Qt(r.progress.pct_complete??0,"embedding"))}}function N(){n.addEventListener("click",l=>{const r=l.target;r.id==="emb-start-btn"&&g(),r.id==="emb-stop-btn"&&P(),r.id==="emb-resume-btn"&&m()}),n.addEventListener("change",l=>{const r=l.target;r.id==="emb-force-check"&&(o=r.checked)}),n.addEventListener("toggle",l=>{const r=l.target;r.id==="emb-log-details"&&(c=r.open)},!0)}async function g(){const l=o;a="start",o=!1,$();try{const{response:r,data:f}=await Ge("/api/ops/embedding/start",{force:l});!r.ok||!(f!=null&&f.ok)?(t((f==null?void 0:f.error)||`Error ${r.status}`,"error"),a=""):t("Embedding iniciado","success")}catch(r){t(String(r),"error"),a=""}await u()}async function P(){var r;const l=(r=s==null?void 0:s.current_operation)==null?void 0:r.job_id;if(l){a="stop",$();try{await Ge("/api/ops/embedding/stop",{job_id:l}),t("Stop solicitado — se detendrá al finalizar el batch actual","success")}catch(f){t(String(f),"error"),a=""}}}async function m(){const l=(s==null?void 0:s.current_operation)||(s==null?void 0:s.last_operation);if(l!=null&&l.job_id){a="start",$();try{const{response:r,data:f}=await Ge("/api/ops/embedding/resume",{job_id:l.job_id});!r.ok||!(f!=null&&f.ok)?(t((f==null?void 0:f.error)||`Error ${r.status}`,"error"),a=""):t("Embedding reanudado desde checkpoint","success")}catch(r){t(String(r),"error"),a=""}a="",await u()}}async function u(){try{const l=await De("/api/ops/embedding-status");s=l;const r=l.current_operation;if(r!=null&&r.progress){const f=r.progress.current_batch;typeof f=="number"&&E(f)}a==="stop"&&!l.current_operation&&(a=""),a==="start"&&l.current_operation&&(a=""),l.current_operation||(i=0,p=0,y=[])}catch{}$()}return{bindEvents:N,refresh:u}}const _a=Object.freeze(Object.defineProperty({__proto__:null,createOpsEmbeddingsController:en},Symbol.toStringTag,{value:"Module"})),Jn=["pending","processing","done"],Kn={pending:"Pendiente",processing:"En proceso",done:"Procesado"},Vn={pending:"⏳",processing:"🔄",done:"✅"},Xn=5;function tn(e){const t=String(e||"").toLowerCase();return t==="done"||t==="completed"||t==="skipped_duplicate"||t==="bounced"?"done":t==="in_progress"||t==="processing"||t==="extracting"||t==="etl"||t==="writing"||t==="gates"||t==="uploading"||t==="running_batch_gates"||t==="needs_retry_batch_gate"||t==="failed"||t==="error"||t==="partial_failed"?"processing":"pending"}function Zn(e,t){const n=e.detected_topic||t.corpus||"",s=sn[n]||Ct[n]||n||"",a=e.detected_type||e.batch_type||"",o=Fn[a]||a||"",c=a==="normative_base"?"normative":a==="interpretative_guidance"?"interpretative":a==="practica_erp"?"practica":"unknown";let i="";return s&&(i+=`<span class="kanban-pill kanban-pill--topic" title="Tema: ${_e(n)}">${xe(s)}</span>`),o&&(i+=`<span class="kanban-pill kanban-pill--type-${c}" title="Tipo: ${_e(a)}">${xe(o)}</span>`),!s&&!o&&(i+='<span class="kanban-pill kanban-pill--unclassified">Sin clasificar</span>'),i}function Yn(e,t,n){var v;const s=it(e.status),a=tn(e.status),o=Hn(e.bytes,n),c=Number(e.progress||0),i=new Set(t.gate_pending_doc_ids||[]),p=a==="done"&&i.has(e.doc_id);let d;e.status==="bounced"?d='<span class="meta-chip status-bounced">↩ Ya existe en el corpus</span>':a==="done"&&e.derived_from_doc_id&&(e.delta_section_count||0)>0?d=`<span class="meta-chip status-ok">△ ${e.delta_section_count} secciones nuevas</span>`:a==="done"&&(e.status==="done"||e.status==="completed")?(d='<span class="meta-chip status-ok">✓ Documento listo</span>',p&&(d+='<span class="meta-chip status-gate-pending">Pendiente validación final</span>')):d=`<span class="meta-chip status-${s}">${xe(e.status)}</span>`;const y=Zn(e,t);let E="";if(e.status==="in_progress"||e.status==="processing"){const S=$t(e.heartbeat_at,e.updated_at,e.stage),x=Wn(e.heartbeat_at,e.updated_at);E=`<div class="kanban-liveness ops-liveness-${S}">${x}</div>`}let h="";e.stage==="gates"&&t.gate_sub_stage&&(h=`<div class="kanban-gate-sub">${Yt(t.gate_sub_stage)}</div>`);let $="";a==="processing"&&c>0&&($=`<div class="kanban-progress" data-progress="${c}"></div>`);let N="";(v=e.error)!=null&&v.message&&(N=`<div class="kanban-error">${xe(e.error.message)}</div>`);let g="";e.duplicate_of?g=`<div class="kanban-duplicate">Duplicado de: ${xe(e.duplicate_of)}</div>`:e.derived_from_doc_id&&(g=`<div class="kanban-duplicate">Derivado de: ${xe(e.derived_from_doc_id)}</div>`);let P="";if(a==="done"){const S=Gn(e.updated_at);S&&(P=`<div class="kanban-completed-at">Completado: ${xe(S)}</div>`)}let m="";e.duplicate_of&&a!=="done"&&e.status!=="bounced"?m=as(e):a==="pending"&&(e.status==="raw"||e.status==="needs_classification")&&es(e)?m=ts(e,n):a==="pending"&&(e.status==="raw"||e.status==="needs_classification")?m=Qn(e,n,t):a==="processing"&&(e.status==="failed"||e.status==="error"||e.status==="partial_failed")&&(m=os(e));let u="",l="";(a!=="pending"||e.status==="queued")&&(u=ns(),l=ss(e,t,n));const f=e.stage&&e.stage!==e.status&&a==="processing";return`
    <div class="kanban-card kanban-card--${s}" data-doc-id="${_e(e.doc_id)}">
      <div class="kanban-card-head">
        <span class="kanban-card-title" title="${_e(e.doc_id)}">${xe(e.filename||e.doc_id)}</span>
        ${d}
      </div>
      ${e.source_relative_path?`<div class="kanban-card-relpath" title="${_e(e.source_relative_path)}">${xe(rs(e.source_relative_path))}</div>`:""}
      <div class="kanban-card-pills-row">
        ${y}
        <span class="kanban-card-size">${o}</span>
        ${u}
      </div>
      ${l}
      ${f?`<div class="kanban-card-stage">${xe(e.stage)}</div>`:""}
      ${E}
      ${h}
      ${$}
      ${P}
      ${g}
      ${N}
      ${m}
    </div>
  `}function Qn(e,t,n){const s=e.detected_type||e.batch_type||"",a=e.detected_topic||(n==null?void 0:n.corpus)||"",o=c=>c===s?" selected":"";return`
    <div class="kanban-actions kanban-classify-actions">
      <label class="kanban-action-field">
        <span>Tema</span>
        <select data-field="topic" class="kanban-select">
          ${mt(a)}
        </select>
      </label>
      <label class="kanban-action-field">
        <span>Tipo</span>
        <select data-field="type" class="kanban-select">
          <option value="">Seleccionar...</option>
          <option value="normative_base"${o("normative_base")}>${t.t("ops.ingestion.batchType.normative")}</option>
          <option value="interpretative_guidance"${o("interpretative_guidance")}>${t.t("ops.ingestion.batchType.interpretative")}</option>
          <option value="practica_erp"${o("practica_erp")}>${t.t("ops.ingestion.batchType.practical")}</option>
        </select>
      </label>
      <div class="kanban-action-field kanban-action-field--btn">
        <span>&nbsp;</span>
        <button class="btn btn--sm btn--primary kanban-assign-btn" data-action="assign" data-doc-id="${_e(e.doc_id)}">Asignar</button>
      </div>
    </div>
  `}function es(e){return!!(e.autogenerar_label&&(e.autogenerar_is_new||e.autogenerar_resolved_topic))}function ts(e,t){const n=e.detected_type||e.batch_type||"",s=d=>d===n?" selected":"",a=`
    <label class="kanban-action-field">
      <span>Tipo</span>
      <select data-field="type" class="kanban-select">
        <option value="">Seleccionar...</option>
        <option value="normative_base"${s("normative_base")}>${t.t("ops.ingestion.batchType.normative")}</option>
        <option value="interpretative_guidance"${s("interpretative_guidance")}>${t.t("ops.ingestion.batchType.interpretative")}</option>
        <option value="practica_erp"${s("practica_erp")}>${t.t("ops.ingestion.batchType.practical")}</option>
      </select>
    </label>`;if(e.autogenerar_is_new)return`
      <div class="kanban-actions kanban-autogenerar-actions kanban-autogenerar--new">
        <div class="kanban-autogenerar-header">Nuevo tema detectado</div>
        <label class="kanban-action-field">
          <span>Tema</span>
          <input type="text" class="kanban-input" data-field="autogenerar-label"
            value="${_e(e.autogenerar_label||"")}" />
        </label>
        ${e.autogenerar_rationale?`<div class="kanban-autogenerar-rationale">${xe(e.autogenerar_rationale)}</div>`:""}
        ${a}
        <div class="kanban-action-buttons">
          <button class="btn btn--sm btn--primary" data-action="accept-new-topic" data-doc-id="${_e(e.doc_id)}">Aceptar nuevo tema</button>
          <button class="btn btn--sm kanban-ag-fallback-btn" data-action="show-existing-dropdown" data-doc-id="${_e(e.doc_id)}">Asignar existente</button>
        </div>
        <div class="kanban-ag-fallback-panel" hidden>
          <label class="kanban-action-field">
            <span>Tema existente</span>
            <select data-field="topic" class="kanban-select">
              ${mt("")}
            </select>
          </label>
          <div class="kanban-action-field kanban-action-field--btn">
            <span>&nbsp;</span>
            <button class="btn btn--sm btn--primary kanban-assign-btn" data-action="assign" data-doc-id="${_e(e.doc_id)}">Asignar</button>
          </div>
        </div>
      </div>
    `;const o=e.autogenerar_resolved_topic||"",c=Ct[o]||o,i=e.autogenerar_synonym_confidence??0,p=Math.round(i*100);return`
    <div class="kanban-actions kanban-autogenerar-actions kanban-autogenerar--synonym">
      <div class="kanban-autogenerar-header">Tema sugerido: <strong>${xe(c)}</strong> <span class="kanban-autogenerar-conf">(${p}%)</span></div>
      <div class="kanban-autogenerar-source">Basado en: "${xe(e.autogenerar_label||"")}"</div>
      ${a}
      <div class="kanban-action-buttons">
        <button class="btn btn--sm btn--primary" data-action="accept-synonym" data-doc-id="${_e(e.doc_id)}">Aceptar</button>
        <button class="btn btn--sm kanban-ag-fallback-btn" data-action="show-existing-dropdown" data-doc-id="${_e(e.doc_id)}">Cambiar</button>
      </div>
      <div class="kanban-ag-fallback-panel" hidden>
        <label class="kanban-action-field">
          <span>Tema</span>
          <select data-field="topic" class="kanban-select">
            ${mt(o)}
          </select>
        </label>
        <div class="kanban-action-field kanban-action-field--btn">
          <span>&nbsp;</span>
          <button class="btn btn--sm btn--primary kanban-assign-btn" data-action="assign" data-doc-id="${_e(e.doc_id)}">Asignar</button>
        </div>
      </div>
    </div>
  `}function ns(){return'<button class="kanban-reclassify-toggle" type="button" title="Cambiar clasificación">✎</button>'}function ss(e,t,n){const s=e.detected_topic||t.corpus||"",a=e.detected_type||e.batch_type||"",o=(c,i)=>c===i?" selected":"";return`
    <div class="kanban-reclassify-panel" hidden>
      <label class="kanban-action-field">
        <span>Tema</span>
        <select data-field="topic" class="kanban-select">
          ${mt(s)}
        </select>
      </label>
      <label class="kanban-action-field">
        <span>Tipo</span>
        <select data-field="type" class="kanban-select">
          <option value="">Seleccionar...</option>
          <option value="normative_base"${o("normative_base",a)}>${n.t("ops.ingestion.batchType.normative")}</option>
          <option value="interpretative_guidance"${o("interpretative_guidance",a)}>${n.t("ops.ingestion.batchType.interpretative")}</option>
          <option value="practica_erp"${o("practica_erp",a)}>${n.t("ops.ingestion.batchType.practical")}</option>
        </select>
      </label>
      <div class="kanban-action-field kanban-action-field--btn">
        <span>&nbsp;</span>
        <button class="btn btn--sm btn--primary kanban-assign-btn" data-action="assign" data-doc-id="${_e(e.doc_id)}">Asignar</button>
      </div>
    </div>
  `}function as(e){return`
    <div class="kanban-actions">
      <button class="btn btn--sm btn--primary" data-action="replace-dup" data-doc-id="${_e(e.doc_id)}">Reemplazar</button>
      <button class="btn btn--sm" data-action="add-new-dup" data-doc-id="${_e(e.doc_id)}">Agregar nuevo</button>
      <button class="btn btn--sm btn--danger" data-action="discard-dup" data-doc-id="${_e(e.doc_id)}">Descartar</button>
    </div>
  `}function os(e){return`
    <div class="kanban-actions">
      <button class="btn btn--sm" data-action="retry" data-doc-id="${_e(e.doc_id)}">Reintentar</button>
      <button class="btn btn--sm btn--danger" data-action="discard" data-doc-id="${_e(e.doc_id)}">Descartar</button>
    </div>
  `}const nn=[["declaracion_renta","Renta"],["iva","IVA"],["laboral","Laboral"],["facturacion_electronica","Facturación"],["estados_financieros_niif","NIIF"],["ica","ICA"],["calendario_obligaciones","Calendarios"],["retencion_fuente","Retención"],["regimen_sancionatorio","Sanciones"],["regimen_cambiario","Régimen Cambiario"],["impuesto_al_patrimonio","Patrimonio"],["informacion_exogena","Exógena"],["proteccion_de_datos","Datos"],["obligaciones_mercantiles","Mercantil"],["obligaciones_profesionales_contador","Obligaciones Contador"],["rut_responsabilidades","RUT"],["gravamen_movimiento_financiero_4x1000","GMF 4×1000"],["beneficiario_final","Beneficiario Final"],["contratacion_estatal","Contratación Estatal"],["reforma_pensional","Reforma Pensional"],["zomac_incentivos","ZOMAC"]];function is(e){const t=new Set,n=[];for(const[s,a]of nn)t.add(s),n.push([s,a]);for(const s of e)!s.key||t.has(s.key)||(t.add(s.key),n.push([s.key,s.label||s.key]));return n}let wt=nn,sn={...Ct};function mt(e=""){let t='<option value="">Seleccionar...</option>';for(const[n,s]of wt){const a=n===e?" selected":"";t+=`<option value="${_e(n)}"${a}>${xe(s)}</option>`}return t}function xe(e){const t=document.createElement("span");return t.textContent=e,t.innerHTML}function _e(e){return e.replace(/&/g,"&amp;").replace(/"/g,"&quot;").replace(/'/g,"&#39;").replace(/</g,"&lt;").replace(/>/g,"&gt;")}function rs(e){const t=e.replace(/\/[^/]+$/,"").split("/").filter(Boolean);return t.length<=2?t.join("/")+"/":"…/"+t.slice(-2).join("/")+"/"}function cs(e,t,n,s,a){a&&a.length>0&&(wt=is(a),sn=Object.fromEntries(wt));const o=[...e.documents||[]].sort((m,u)=>Date.parse(String(u.updated_at||0))-Date.parse(String(m.updated_at||0))),c={pending:[],processing:[],done:[]};for(const m of o){const u=tn(m.status);c[u].push(m)}c.pending.sort((m,u)=>{const l=m.status==="raw"||m.status==="needs_classification"?0:1,r=u.status==="raw"||u.status==="needs_classification"?0:1;return l!==r?l-r:Date.parse(String(u.updated_at||0))-Date.parse(String(m.updated_at||0))});const i=e.status==="running_batch_gates",p=e.gate_sub_stage||"";let d="";if(i){const m=p?Yt(p):"Preparando...";d=`
      <div class="kanban-validation-banner kanban-validation-banner--running">
        <span class="kanban-validation-spinner"></span>
        <span>Validación final en curso — ${xe(m)}</span>
      </div>`}else e.status==="needs_retry_batch_gate"?d=`
      <div class="kanban-validation-banner kanban-validation-banner--error">
        <span>⚠ Validación final fallida — use Reintentar o Validar lote</span>
      </div>`:e.status==="completed"&&e.wip_sync_status==="skipped"&&(d=`
      <div class="kanban-validation-banner kanban-validation-banner--warn">
        <span>⚠ Ingesta completada solo localmente — WIP Supabase no estaba disponible. Use Operaciones → Sincronizar a WIP.</span>
      </div>`);let y="";const E=c.processing.length;for(const m of Jn){const u=c[m],l=m==="processing"?`<span class="kanban-column-count">${E}</span><span class="kanban-column-limit">/ ${Xn}</span>`:`<span class="kanban-column-count">${u.length}</span>`,r=u.length===0?'<div class="kanban-column-empty">Sin documentos</div>':u.map(v=>Yn(v,e,n)).join(""),f=m==="done"?d:"";y+=`
      <div class="kanban-column kanban-column--${m}">
        <div class="kanban-column-header">
          <span class="kanban-column-icon">${Vn[m]}</span>
          <span class="kanban-column-label">${Kn[m]}</span>
          ${l}
        </div>
        <div class="kanban-column-cards">
          ${f}
          ${r}
        </div>
      </div>
    `}const h={};t.querySelectorAll(".kanban-column").forEach(m=>{const u=m.classList[1]||"",l=m.querySelector(".kanban-column-cards");u&&l&&(h[u]=l.scrollTop)});const $=[];let N=t;for(;N;)N.scrollTop>0&&$.push([N,N.scrollTop]),N=N.parentElement;const g={};t.querySelectorAll(".kanban-reclassify-panel").forEach(m=>{var u,l;if(!m.hasAttribute("hidden")){const r=m.closest("[data-doc-id]"),f=(r==null?void 0:r.dataset.docId)||"";if(f&&!(s!=null&&s.has(f))){const v=((u=m.querySelector("[data-field='topic']"))==null?void 0:u.value)||"",S=((l=m.querySelector("[data-field='type']"))==null?void 0:l.value)||"";g[f]={topic:v,type:S}}}});const P={};t.querySelectorAll(".kanban-classify-actions").forEach(m=>{var r,f;const u=m.closest("[data-doc-id]"),l=(u==null?void 0:u.dataset.docId)||"";if(l){const v=((r=m.querySelector("[data-field='topic']"))==null?void 0:r.value)||"",S=((f=m.querySelector("[data-field='type']"))==null?void 0:f.value)||"";(v||S)&&(P[l]={topic:v,type:S})}}),t.innerHTML=y;for(const[m,u]of $)m.scrollTop=u;t.querySelectorAll(".kanban-column").forEach(m=>{const u=m.classList[1]||"",l=m.querySelector(".kanban-column-cards");u&&h[u]&&l&&(l.scrollTop=h[u])});for(const[m,u]of Object.entries(g)){const l=t.querySelector(`[data-doc-id="${CSS.escape(m)}"]`);if(!l)continue;const r=l.querySelector(".kanban-reclassify-toggle"),f=l.querySelector(".kanban-reclassify-panel");if(r&&f){f.removeAttribute("hidden"),r.textContent="✖";const v=f.querySelector("[data-field='topic']"),S=f.querySelector("[data-field='type']");v&&u.topic&&(v.value=u.topic),S&&u.type&&(S.value=u.type)}}for(const[m,u]of Object.entries(P)){const l=t.querySelector(`[data-doc-id="${CSS.escape(m)}"]`);if(!l)continue;const r=l.querySelector(".kanban-classify-actions");if(!r)continue;const f=r.querySelector("[data-field='topic']"),v=r.querySelector("[data-field='type']");f&&u.topic&&(f.value=u.topic),v&&u.type&&(v.value=u.type)}t.querySelectorAll(".kanban-progress").forEach(m=>{var f,v;const u=Number(m.dataset.progress||0),l=((v=(f=m.closest(".kanban-card"))==null?void 0:f.querySelector(".kanban-card-stage"))==null?void 0:v.textContent)||void 0,r=Qt(u,l);m.replaceWith(r)}),t.querySelectorAll(".kanban-reclassify-toggle").forEach(m=>{m.addEventListener("click",()=>{const u=m.closest(".kanban-card"),l=u==null?void 0:u.querySelector(".kanban-reclassify-panel");if(!l)return;l.hasAttribute("hidden")?(l.removeAttribute("hidden"),m.textContent="✖"):(l.setAttribute("hidden",""),m.textContent="✎")})})}async function Re(e,t){const n=await fetch(e,t);let s=null;try{s=await n.json()}catch{s=null}if(!n.ok){const a=s&&typeof s=="object"&&"error"in s?String(s.error||n.statusText):n.statusText;throw new et(a,n.status,s)}return s}async function St(e,t){const{response:n,data:s}=await Ge(e,t);if(!n.ok){const a=s&&typeof s=="object"&&"error"in s?String(s.error||n.statusText):n.statusText;throw new et(a,n.status,s)}return s}const ls=new Set([".pdf",".md",".txt",".docx"]),ds=[".","__MACOSX"],kt=3,_t="lia_folder_pending_";function ot(e){return e.filter(t=>{const n=t.name;if(ds.some(o=>n.startsWith(o)))return!1;const s=n.lastIndexOf("."),a=s>=0?n.slice(s).toLowerCase():"";return ls.has(a)})}function rt(e,t){return e.webkitRelativePath||t.get(e)||""}function Xe(e,t){const n=rt(e,t);return`${e.name}|${e.size}|${e.lastModified??0}|${n}`}function us(e){return e<1024?`${e} B`:e<1024*1024?`${(e/1024).toFixed(1)} KB`:`${(e/(1024*1024)).toFixed(1)} MB`}function ps(e,t){var s;const n=((s=e.preflightEntry)==null?void 0:s.existing_doc_id)||"";switch(e.verdict){case"pending":return t.t("ops.ingestion.verdict.pending");case"new":return t.t("ops.ingestion.verdict.new");case"revision":return n?t.t("ops.ingestion.verdict.revisionOf",{docId:n}):t.t("ops.ingestion.verdict.revision");case"duplicate":return n?t.t("ops.ingestion.verdict.duplicateOf",{docId:n}):t.t("ops.ingestion.verdict.duplicate");case"artifact":return t.t("ops.ingestion.verdict.artifact");case"unreadable":return t.t("ops.ingestion.verdict.unreadable")}}function ms(e,t){const n=document.createElement("span");return n.className=`ops-verdict-pill ops-verdict-pill--${e.verdict}`,n.textContent=ps(e,t),n}function ut(e){return e.documents.filter(t=>t.status==="raw"||t.status==="needs_classification").length}function gs(e){const{dom:t,stateController:n,withThinkingWheel:s,setFlash:a}=e;function o(){return e.state.selectedCorpus!=="autogenerar"?e.state.selectedCorpus:"autogenerar"}async function c(){const u=await De("/api/corpora"),l=Array.isArray(u.corpora)?u.corpora:[];n.setCorpora(l);const r=new Set(l.map(f=>f.key));r.add("autogenerar"),r.has(e.state.selectedCorpus)||n.setSelectedCorpus("autogenerar")}async function i(){const u=await De("/api/ingestion/sessions?limit=20");return Array.isArray(u.sessions)?u.sessions:[]}async function p(u){const l=await De(`/api/ingestion/sessions/${encodeURIComponent(u)}`);if(!l.session)throw new Error("missing_session");return l.session}async function d(u){const l=await St("/api/ingestion/sessions",{corpus:u});if(!l.session)throw new Error("missing_session");return l.session}async function y(u,l,r){const f=t.ingestionCorpusSelect.value==="autogenerar"?"":t.ingestionCorpusSelect.value,v={"Content-Type":"application/octet-stream","X-Upload-Filename":l.name,"X-Upload-Mime":l.type||"application/octet-stream","X-Upload-Batch-Type":r};f&&(v["X-Upload-Topic"]=f);const S=rt(l,e.state.folderRelativePaths);S&&(v["X-Upload-Relative-Path"]=S),console.log(`[upload] ${l.name} (${l.size}B) → session=${u} batch=${r}`);const x=await fetch(`/api/ingestion/sessions/${encodeURIComponent(u)}/files`,{method:"POST",headers:v,body:l}),j=await x.text();let I;try{I=JSON.parse(j)}catch{throw console.error(`[upload] ${l.name} — response not JSON (${x.status}):`,j.slice(0,300)),new Error(`Upload response not JSON: ${x.status} ${j.slice(0,100)}`)}if(!x.ok){const W=I.error||x.statusText;throw console.error(`[upload] ${l.name} — HTTP ${x.status}:`,W),new et(W,x.status,I)}if(!I.document)throw console.error(`[upload] ${l.name} — no document in response:`,I),new Error("missing_document");return console.log(`[upload] ${l.name} → OK doc_id=${I.document.doc_id} status=${I.document.status}`),I.document}async function E(u){return Re(`/api/ingestion/sessions/${encodeURIComponent(u)}/process`,{method:"POST"})}async function h(u){return Re(`/api/ingestion/sessions/${encodeURIComponent(u)}/validate-batch`,{method:"POST"})}async function $(u){return Re(`/api/ingestion/sessions/${encodeURIComponent(u)}/retry`,{method:"POST"})}async function N(u,l=!1){const r=l?"?force=true":"";return Re(`/api/ingestion/sessions/${encodeURIComponent(u)}${r}`,{method:"DELETE"})}async function g({showWheel:u=!0,reportError:l=!0,focusSessionId:r=""}={}){const f=async()=>{await c(),e.render();let v=await i();const S=r||e.state.selectedSessionId;if(S&&!v.some(x=>x.session_id===S))try{v=[await p(S),...v.filter(j=>j.session_id!==S)]}catch{S===e.state.selectedSessionId&&n.setSelectedSession(null)}n.setSessions(v.sort((x,j)=>Date.parse(String(j.updated_at||0))-Date.parse(String(x.updated_at||0)))),n.syncSelectedSession(),e.render()};try{u?await s(f):await f()}catch(v){throw l&&a($e(v),"error"),e.render(),v}}async function P({sessionId:u,showWheel:l=!1,reportError:r=!0}){const f=async()=>{const v=await p(u);n.upsertSession(v),e.render()};try{l?await s(f):await f()}catch(v){throw r&&a($e(v),"error"),v}}async function m(){var l,r,f,v;const u=o();if(console.log(`[folder-ingest] ensureSelectedSession: effectiveCorpus="${u}", selectedSession=${((l=e.state.selectedSession)==null?void 0:l.session_id)||"null"} (status=${((r=e.state.selectedSession)==null?void 0:r.status)||"null"}, corpus=${((f=e.state.selectedSession)==null?void 0:f.corpus)||"null"})`),e.state.selectedSession&&!Zt(e.state.selectedSession)&&e.state.selectedSession.status!=="completed"&&(e.state.selectedSession.corpus===u||u==="autogenerar"))return console.log(`[folder-ingest] Reusing session ${e.state.selectedSession.session_id}`),e.state.selectedSession;e.trace(`Creando sesión con corpus="${u}"...`);try{const S=await d(u);return e.trace(`Sesión creada: ${S.session_id} (corpus=${S.corpus})`),n.upsertSession(S),S}catch(S){if(e.trace(`Creación falló para corpus="${u}": ${S instanceof Error?S.message:String(S)}`),u==="autogenerar"){const x=((v=e.state.corpora.find(I=>I.active))==null?void 0:v.key)||"declaracion_renta";e.trace(`Reintentando con corpus="${x}"...`);const j=await d(x);return e.trace(`Sesión fallback: ${j.session_id} (corpus=${j.corpus})`),n.upsertSession(j),j}throw S}}return{resolveSessionCorpus:o,fetchCorpora:c,fetchIngestionSessions:i,fetchIngestionSession:p,createIngestionSession:d,uploadIngestionFile:y,startIngestionProcess:E,validateBatch:h,retryIngestionSession:$,ejectIngestionSession:N,refreshIngestion:g,refreshSelectedSession:P,ensureSelectedSession:m}}function fs(e){const{i18n:t,stateController:n,dom:s,withThinkingWheel:a,setFlash:o}=e,c=yn(t);return{dom:s,i18n:t,stateController:n,withThinkingWheel:a,setFlash:o,toast:c,get state(){return n.state},render:()=>{},trace:()=>{}}}function bs(e,t){const{dom:n,stateController:s,i18n:a}=e,{ingestionUploadProgress:o}=n;async function c(g){var l,r;const P=[],m=[];for(let f=0;f<g.items.length;f++){const v=(r=(l=g.items[f]).webkitGetAsEntry)==null?void 0:r.call(l);v&&m.push(v)}if(!m.some(f=>f.isDirectory))return[];async function u(f){if(f.isFile){const v=await new Promise((S,x)=>{f.file(S,x)});e.state.folderRelativePaths.set(v,f.fullPath.replace(/^\//,"")),P.push(v)}else if(f.isDirectory){const v=f.createReader();let S;do{S=await new Promise((x,j)=>{v.readEntries(x,j)});for(const x of S)await u(x)}while(S.length>0)}}for(const f of m)await u(f);return P}async function i(g,P=""){const m=[];for await(const[u,l]of g.entries()){const r=P?`${P}/${u}`:u;if(l.kind==="file"){const f=await l.getFile();e.state.folderRelativePaths.set(f,r),m.push(f)}else if(l.kind==="directory"){const f=await i(l,r);m.push(...f)}}return m}async function p(g,P,m,u=kt){let l=0,r=0,f=0,v=0;const S=[];return new Promise(x=>{function j(){for(;f<u&&v<P.length;){const I=P[v++];f++,t.uploadIngestionFile(g,I,m).then(()=>{l++}).catch(W=>{r++;const K=W instanceof Error?W.message:String(W);S.push({filename:I.name,error:K}),console.error(`[folder-ingest] Upload failed: ${I.name}`,W)}).finally(()=>{f--,s.setFolderUploadProgress({total:P.length,uploaded:l,failed:r,uploading:v<P.length||f>0}),d(),v<P.length||f>0?j():x({uploaded:l,failed:r,errors:S})})}}s.setFolderUploadProgress({total:P.length,uploaded:0,failed:0,uploading:!0}),d(),j()})}function d(){const g=e.state.folderUploadProgress;if(!g||!g.uploading){o.hidden=!0,o.innerHTML="";return}const P=g.uploaded+g.failed,m=g.total>0?Math.round(P/g.total*100):0,u=Math.max(0,Math.min(kt,g.total-P));o.hidden=!1,o.innerHTML=`
      <div class="ops-upload-progress-header">
        <span>${a.t("ops.ingestion.uploadProgress",{current:P,total:g.total})}</span>
        <span>${m}%</span>
      </div>
      <div class="ops-upload-progress-bar">
        <span class="ops-upload-progress-fill" style="width:${m}%"></span>
      </div>
      <div class="ops-upload-progress-detail">
        ${a.t("ops.ingestion.uploadProgressDetail",{uploaded:g.uploaded,failed:g.failed,inflight:u})}
      </div>
    `}function y(){const g=e.state.preflightScanProgress;if(!g||!g.scanning){o.hidden=!0,o.innerHTML="";return}const P=g.total>0?Math.round(g.hashed/g.total*100):0;o.hidden=!1,o.innerHTML=`
      <div class="ops-preflight-scan">
        <div class="ops-preflight-scan-header">
          <span>${a.t("ops.ingestion.preflight.scanning",{hashed:g.hashed,total:g.total})}</span>
          <span>${P}%</span>
        </div>
        <div class="ops-preflight-scan-bar">
          <span class="ops-preflight-scan-fill" style="width:${P}%"></span>
        </div>
        <div class="ops-preflight-scan-detail">${a.t("ops.ingestion.preflight.scanningDetail")}</div>
      </div>
    `}function E(g){if(e.state.pendingFiles.length!==0&&rt(e.state.pendingFiles[0])!=="")try{const P=e.state.pendingFiles.map(m=>({name:m.name,relativePath:rt(m),size:m.size}));localStorage.setItem(_t+g,JSON.stringify(P))}catch{}}function h(g){try{localStorage.removeItem(_t+g)}catch{}}function $(g){try{const P=localStorage.getItem(_t+g);if(!P)return 0;const m=JSON.parse(P);if(!Array.isArray(m))return 0;const u=e.state.sessions.find(r=>r.session_id===g);if(!u)return m.length;const l=new Set((u.documents||[]).map(r=>r.filename));return m.filter(r=>!l.has(r.name)).length}catch{return 0}}async function N(g,P){return(await St("/api/ingestion/preflight",{corpus:P,files:g})).manifest}return{resolveFolderFiles:c,readDirectoryHandle:i,uploadFilesWithConcurrency:p,renderUploadProgress:d,renderScanProgress:y,persistFolderPending:E,clearFolderPending:h,getStoredFolderPendingCount:$,requestPreflight:N}}function hs(e,t,n,s){const{dom:a,stateController:o,setFlash:c}=e,{ingestionFolderInput:i,ingestionFileInput:p}=a;let d=!1,y=null;const E=150;function h(v){if(v.length===0)return;const S=new Set(e.state.intake.map(j=>Xe(j.file))),x=[];for(const j of v){const I=Xe(j,e.state.folderRelativePaths);S.has(I)||(S.add(I),x.push({file:j,relativePath:rt(j,e.state.folderRelativePaths),contentHash:null,verdict:"pending",preflightEntry:null}))}x.length!==0&&(o.setIntake([...e.state.intake,...x]),e.state.reviewPlan&&o.setReviewPlan({...e.state.reviewPlan,stalePartial:!0}),d=!1,$(),e.render())}function $(){y&&clearTimeout(y);const v=o.bumpPreflightRunId();y=setTimeout(()=>{y=null,N(v)},E)}async function N(v){if(v!==e.state.preflightRunId||e.state.intake.length===0)return;const S=e.state.intake.filter(x=>x.contentHash===null);try{if(S.length>0&&(await g(S),v!==e.state.preflightRunId))return;const x=await P();if(v!==e.state.preflightRunId)return;if(!x){d=!0,e.render();return}m(x),d=!1,e.render()}catch(x){if(v!==e.state.preflightRunId)return;console.error("[intake] preflight failed:",x),d=!0,e.render()}}async function g(v){o.setPreflightScanProgress({total:v.length,hashed:0,scanning:!0}),n.renderScanProgress();for(let S=0;S<v.length;S++){const x=v[S];try{const j=await x.file.arrayBuffer(),I=await crypto.subtle.digest("SHA-256",j),W=Array.from(new Uint8Array(I));x.contentHash=W.map(K=>K.toString(16).padStart(2,"0")).join("")}catch(j){console.warn(`[intake] hash failed for ${x.file.name}:`,j),x.verdict="unreadable",x.contentHash=""}o.setPreflightScanProgress({total:v.length,hashed:S+1,scanning:!0}),n.renderScanProgress()}o.setPreflightScanProgress(null)}async function P(){const v=e.state.intake.filter(S=>S.contentHash&&S.verdict!=="unreadable").map(S=>({filename:S.file.name,relative_path:S.relativePath||S.file.name,size:S.file.size,content_hash:S.contentHash}));if(v.length===0)return{artifacts:[],duplicates:[],revisions:[],new_files:[],scanned:0,elapsed_ms:0};try{return await n.requestPreflight(v,e.state.selectedCorpus)}catch(S){return console.error("[intake] /api/ingestion/preflight failed:",S),null}}function m(v){const S=new Map,x=(K,q)=>{for(const w of q){const _=w.relative_path||w.filename;S.set(_,{verdict:K,preflightEntry:w})}};x("new",v.new_files),x("revision",v.revisions),x("duplicate",v.duplicates),x("artifact",v.artifacts);const j=e.state.intake.map(K=>{if(K.verdict==="unreadable")return K;const q=K.relativePath||K.file.name,w=S.get(q);return w?{...K,verdict:w.verdict,preflightEntry:w.preflightEntry}:{...K,verdict:"pending"}}),I=j.filter(K=>K.verdict==="new"||K.verdict==="revision"),W=j.filter(K=>K.verdict==="duplicate"||K.verdict==="artifact"||K.verdict==="unreadable");o.setIntake(j),o.setReviewPlan({willIngest:I,bounced:W,scanned:v.scanned,elapsedMs:v.elapsed_ms,stalePartial:!1}),o.setPendingFiles(I.map(K=>K.file))}function u(v){const S=x=>Xe(x.file)!==Xe(v.file);if(o.setIntake(e.state.intake.filter(S)),e.state.reviewPlan){const x=e.state.reviewPlan.willIngest.filter(S);o.setReviewPlan({...e.state.reviewPlan,willIngest:x}),o.setPendingFiles(x.map(j=>j.file))}else o.setPendingFiles(e.state.pendingFiles.filter(x=>Xe(x)!==Xe(v.file)));e.render()}function l(){if(!e.state.reviewPlan)return;const v=new Set(e.state.reviewPlan.willIngest.map(x=>Xe(x.file))),S=e.state.intake.filter(x=>!v.has(Xe(x.file)));o.setIntake(S),o.setReviewPlan({...e.state.reviewPlan,willIngest:[]}),o.setPendingFiles([]),e.render()}function r(){y&&(clearTimeout(y),y=null),o.bumpPreflightRunId(),o.setIntake([]),o.setReviewPlan(null),o.setPendingFiles([]),o.setPreflightScanProgress(null),d=!1,e.state.folderRelativePaths.clear()}async function f(){const v=e.state.reviewPlan;if(v&&!v.stalePartial&&v.willIngest.length!==0&&!d){c(),o.setMutating(!0),s.renderControls();try{await s.directFolderIngest(),r(),i.value="",p.value=""}catch(S){o.setFolderUploadProgress(null),n.renderUploadProgress(),c($e(S),"error"),e.state.selectedSessionId&&t.refreshSelectedSession({sessionId:e.state.selectedSessionId,showWheel:!1,reportError:!1})}finally{o.setMutating(!1),s.renderControls()}}}return{addFilesToIntake:h,schedulePreflight:$,runIntakePreflight:N,hashIntakeEntries:g,preflightIntake:P,applyManifestToIntake:m,removeIntakeEntry:u,cancelAllWillIngest:l,clearIntake:r,confirmAndIngest:f,getIntakeError:()=>d,setIntakeError:v=>{d=v}}}function vs(e,t){const{dom:n,i18n:s,stateController:a,setFlash:o}=e,{ingestionAutoStatus:c}=n,i=4e3;let p=null,d="";function y(){p&&(clearTimeout(p),p=null),d="",c.hidden=!0,c.classList.remove("is-running")}function E(N){const g=N.batch_summary,P=ut(N),m=Math.max(0,Number(g.queued??0)-P),u=Number(g.processing??0),l=Number(g.done??0),r=Number(g.failed??0),f=Number(g.bounced??0),v=m+u;c.hidden=!1;const S=f>0?` · ${f} rebotados`:"";v>0||P>0?(c.classList.add("is-running"),c.textContent=s.t("ops.ingestion.auto.running",{queued:m,processing:u,raw:P})+S):r>0?(c.classList.remove("is-running"),c.textContent=s.t("ops.ingestion.auto.done",{done:l,failed:r,raw:P})+S):(c.classList.remove("is-running"),c.textContent=s.t("ops.ingestion.auto.allDone",{done:l})+S)}async function h(){const N=d;if(N)try{const g=await t.fetchIngestionSession(N);a.upsertSession(g),e.render(),E(g);const P=g.batch_summary,m=ut(g),u=Number(P.total??0);if(u===0){y();return}m>0&&await Re(`/api/ingestion/sessions/${encodeURIComponent(N)}/auto-process`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({max_concurrency:5})});const l=m>0?await t.fetchIngestionSession(N):g,r=ut(l),f=Math.max(0,Number(l.batch_summary.queued??0)-r),v=Number(l.batch_summary.processing??0);f>0&&v===0&&await t.startIngestionProcess(N),m>0&&(a.upsertSession(l),e.render(),E(l));const S=f+v;if(u>0&&S===0&&r===0){if(Number(l.batch_summary.pending_batch_gate??0)>0&&l.status!=="running_batch_gates"&&l.status!=="completed")try{await t.validateBatch(N)}catch{}const j=await t.fetchIngestionSession(N);a.upsertSession(j),e.render(),E(j),y(),o(s.t("ops.ingestion.auto.allDone",{done:Number(j.batch_summary.done??0)}),"success");return}if(S===0&&r>0){c.classList.remove("is-running"),c.textContent=s.t("ops.ingestion.auto.done",{done:Number(l.batch_summary.done??0),failed:Number(l.batch_summary.failed??0),raw:r}),y();return}p=setTimeout(()=>void h(),i)}catch(g){y(),o($e(g),"error")}}function $(N){y(),d=N,c.hidden=!1,c.classList.add("is-running"),c.textContent=s.t("ops.ingestion.auto.running",{queued:0,processing:0,raw:0}),p=setTimeout(()=>void h(),2e3)}return{startAutoPilot:$,stopAutoPilot:y,updateAutoStatus:E,autoPilotTick:h}}function _s(e){const{ctx:t,api:n,upload:s,intake:a,autoPilot:o}=e,{dom:c,stateController:i,i18n:p,setFlash:d,toast:y,withThinkingWheel:E}=t,{ingestionDropzone:h,ingestionFileInput:$,ingestionFolderInput:N,ingestionSelectFilesBtn:g,ingestionSelectFolderBtn:P,ingestionCorpusSelect:m,ingestionRefreshBtn:u,ingestionCreateSessionBtn:l,ingestionUploadBtn:r,ingestionProcessBtn:f,ingestionValidateBatchBtn:v,ingestionRetryBtn:S,ingestionDeleteSessionBtn:x,ingestionAutoProcessBtn:j,ingestionLastError:I,ingestionLogBody:W,ingestionLogAccordion:K,ingestionLogCopyBtn:q,ingestionKanban:w,ingestionUploadProgress:_}=c,{addFilesToIntake:b,clearIntake:D,confirmAndIngest:R}=a,{startAutoPilot:fe,stopAutoPilot:T}=o,{createIngestionSession:ge,ejectIngestionSession:L,fetchCorpora:M,refreshIngestion:te,refreshSelectedSession:V,resolveSessionCorpus:ye,retryIngestionSession:ie,startIngestionProcess:me,validateBatch:Ee}=n,{resolveFolderFiles:Pe,readDirectoryHandle:Ce}=s,{render:H,renderCorpora:we,renderControls:le,traceClear:Ne,directFolderIngest:Me,suppressPanelsOnNextRender:qe}=e,{state:be}=i;h.addEventListener("click",()=>{$.disabled||$.click()}),h.addEventListener("keydown",A=>{A.key!=="Enter"&&A.key!==" "||(A.preventDefault(),$.disabled||$.click())});let Ae=0;h.addEventListener("dragenter",A=>{A.preventDefault(),Ae++,$.disabled||h.classList.add("is-dragover")}),h.addEventListener("dragover",A=>{A.preventDefault()}),h.addEventListener("dragleave",()=>{Ae--,Ae<=0&&(Ae=0,h.classList.remove("is-dragover"))}),h.addEventListener("drop",async A=>{var Y;if(A.preventDefault(),Ae=0,h.classList.remove("is-dragover"),$.disabled)return;const z=A.dataTransfer;if(z){const X=await Pe(z);if(X.length>0){b(ot(X));return}}const ee=Array.from(((Y=A.dataTransfer)==null?void 0:Y.files)||[]);ee.length!==0&&b(ot(ee))}),$.addEventListener("change",()=>{const A=Array.from($.files||[]);A.length!==0&&b(ot(A))}),N.addEventListener("change",()=>{const A=Array.from(N.files||[]);A.length!==0&&b(ot(A))}),g.addEventListener("click",()=>{$.disabled||$.click()}),P.addEventListener("click",async()=>{if(!N.disabled){if(typeof window.showDirectoryPicker=="function")try{const A=await window.showDirectoryPicker({mode:"read"}),z=await Ce(A,A.name),ee=ot(z);ee.length>0?b(ee):d(p.t("ops.ingestion.pendingNone"),"error");return}catch(A){if((A==null?void 0:A.name)==="AbortError")return}N.click()}}),m.addEventListener("change",()=>{i.setSelectedCorpus(m.value),i.setSessions([]),i.setSelectedSession(null),D(),d(),H(),te({showWheel:!0,reportError:!0})}),u.addEventListener("click",A=>{A.stopPropagation(),d(),te({showWheel:!0,reportError:!0})}),l.addEventListener("click",async()=>{T(),d(),D(),i.setPreflightManifest(null),i.setFolderUploadProgress(null),be.rejectedArtifacts=[],_.hidden=!0,_.innerHTML="",$.value="",N.value="",I.hidden=!0,Ne(),K.hidden=!0,W.textContent="",i.setMutating(!0),le();try{const A=await E(async()=>ge(ye()));i.upsertSession(A),H(),d(p.t("ops.ingestion.flash.sessionCreated",{id:A.session_id}),"success")}catch(A){d($e(A),"error")}finally{i.setMutating(!1),le()}}),r.addEventListener("click",()=>{R()}),f.addEventListener("click",async()=>{const A=be.selectedSessionId;if(A){d(),i.setMutating(!0),le();try{await E(async()=>me(A)),await V({sessionId:A,showWheel:!1,reportError:!1});const z=p.t("ops.ingestion.flash.processStarted",{id:A});d(z,"success"),y.show({message:z,tone:"success"})}catch(z){const ee=$e(z);d(ee,"error"),y.show({message:ee,tone:"error"})}finally{i.setMutating(!1),le()}}}),v.addEventListener("click",async()=>{const A=be.selectedSessionId;if(A){d(),i.setMutating(!0),le();try{await E(async()=>Ee(A)),await V({sessionId:A,showWheel:!1,reportError:!1});const z="Validación de lote iniciada";d(z,"success"),y.show({message:z,tone:"success"})}catch(z){const ee=$e(z);d(ee,"error"),y.show({message:ee,tone:"error"})}finally{i.setMutating(!1),le()}}}),S.addEventListener("click",async()=>{const A=be.selectedSessionId;if(A){d(),i.setMutating(!0),le();try{await E(async()=>ie(A)),await V({sessionId:A,showWheel:!1,reportError:!1}),d(p.t("ops.ingestion.flash.retryStarted",{id:A}),"success")}catch(z){d($e(z),"error")}finally{i.setMutating(!1),le()}}}),x.addEventListener("click",async()=>{var X;const A=be.selectedSessionId;if(!A)return;const z=Zt(be.selectedSession),ee=z?p.t("ops.ingestion.confirm.ejectPostGate"):p.t("ops.ingestion.confirm.ejectPreGate");if(await y.confirm({title:p.t("ops.ingestion.actions.discardSession"),message:ee,tone:"caution",confirmLabel:p.t("ops.ingestion.confirm.ejectLabel")})){T(),d(),i.setMutating(!0),le();try{const pe=ft(String(((X=be.selectedSession)==null?void 0:X.status)||"")),ne=await E(async()=>L(A,pe||z));i.clearSelectionAfterDelete(),D(),i.setPreflightManifest(null),i.setFolderUploadProgress(null),be.rejectedArtifacts=[],_.hidden=!0,_.innerHTML="",$.value="",N.value="",I.hidden=!0,Ne(),K.hidden=!0,W.textContent="",await te({showWheel:!1,reportError:!1});const oe=Array.isArray(ne.errors)&&ne.errors.length>0,G=ne.path==="rollback"?p.t("ops.ingestion.flash.ejectedRollback",{id:A,count:ne.ejected_files}):p.t("ops.ingestion.flash.ejectedInstant",{id:A,count:ne.ejected_files}),Z=oe?"caution":"success";d(G,oe?"error":"success"),y.show({message:G,tone:Z}),oe&&y.show({message:p.t("ops.ingestion.flash.ejectedPartial"),tone:"caution",durationMs:8e3})}catch(pe){const ne=$e(pe);d(ne,"error"),y.show({message:ne,tone:"error"})}finally{i.setMutating(!1),H()}}}),j.addEventListener("click",async()=>{const A=be.selectedSessionId;if(A){d(),i.setMutating(!0),le();try{await E(async()=>Re(`/api/ingestion/sessions/${encodeURIComponent(A)}/auto-process`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({max_concurrency:5})})),await me(A),await V({sessionId:A,showWheel:!1,reportError:!1}),d(`Auto-procesamiento iniciado para ${A}`,"success"),fe(A)}catch(z){d($e(z),"error")}finally{i.setMutating(!1),le()}}});const Te=document.getElementById("ingestion-log-toggle");Te&&(Te.addEventListener("click",A=>{if(A.target.closest(".ops-log-copy-btn"))return;const z=W.hidden;W.hidden=!z,Te.setAttribute("aria-expanded",String(z));const ee=Te.querySelector(".ops-log-accordion-marker");ee&&(ee.textContent=z?"▾":"▸")}),Te.addEventListener("keydown",A=>{(A.key==="Enter"||A.key===" ")&&(A.preventDefault(),Te.click())})),q.addEventListener("click",A=>{A.preventDefault(),A.stopPropagation();const z=W.textContent||"";navigator.clipboard.writeText(z).then(()=>{const ee=q.textContent;q.textContent=p.t("ops.ingestion.log.copied"),setTimeout(()=>{q.textContent=ee},1500)}).catch(()=>{const ee=document.createRange();ee.selectNodeContents(W);const Y=window.getSelection();Y==null||Y.removeAllRanges(),Y==null||Y.addRange(ee)})}),w.addEventListener("click",async A=>{var oe;const z=A.target.closest("[data-action]");if(!z)return;const ee=z.getAttribute("data-action"),Y=z.getAttribute("data-doc-id"),X=be.selectedSessionId;if(!X||!Y)return;if(ee==="show-existing-dropdown"){const G=z.closest(".kanban-card"),Z=G==null?void 0:G.querySelector(".kanban-ag-fallback-panel");Z&&(Z.hidden=!Z.hidden);return}let pe="",ne="";if(ee==="assign"){const G=z.closest(".kanban-card"),Z=G==null?void 0:G.querySelector("[data-field='topic']"),ke=G==null?void 0:G.querySelector("[data-field='type']");if(pe=(Z==null?void 0:Z.value)||"",ne=(ke==null?void 0:ke.value)||"",!pe||!ne){Z&&!pe&&Z.classList.add("kanban-select--invalid"),ke&&!ne&&ke.classList.add("kanban-select--invalid");return}}d(),i.setMutating(!0),le();try{switch(ee){case"assign":{await E(async()=>Re(`/api/ingestion/sessions/${encodeURIComponent(X)}/documents/${encodeURIComponent(Y)}/classify`,{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify({topic:pe,batch_type:ne})})),qe.add(Y);break}case"replace-dup":{await E(async()=>Re(`/api/ingestion/sessions/${encodeURIComponent(X)}/documents/${encodeURIComponent(Y)}/resolve-duplicate`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action:"replace"})}));break}case"add-new-dup":{await E(async()=>Re(`/api/ingestion/sessions/${encodeURIComponent(X)}/documents/${encodeURIComponent(Y)}/resolve-duplicate`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action:"add_new"})}));break}case"discard-dup":case"discard":{await E(async()=>Re(`/api/ingestion/sessions/${encodeURIComponent(X)}/documents/${encodeURIComponent(Y)}/resolve-duplicate`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action:"discard"})}));break}case"accept-synonym":{const G=z.closest(".kanban-card"),Z=G==null?void 0:G.querySelector("[data-field='type']"),ke=(Z==null?void 0:Z.value)||"";await E(async()=>Re(`/api/ingestion/sessions/${encodeURIComponent(X)}/documents/${encodeURIComponent(Y)}/accept-autogenerar`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action:"accept_synonym",type:ke||void 0})})),qe.add(Y);break}case"accept-new-topic":{const G=z.closest(".kanban-card"),Z=G==null?void 0:G.querySelector("[data-field='autogenerar-label']"),ke=G==null?void 0:G.querySelector("[data-field='type']"),Le=((oe=Z==null?void 0:Z.value)==null?void 0:oe.trim())||"",Ie=(ke==null?void 0:ke.value)||"";if(!Le||Le.length<3){Z&&Z.classList.add("kanban-select--invalid");return}await E(async()=>Re(`/api/ingestion/sessions/${encodeURIComponent(X)}/documents/${encodeURIComponent(Y)}/accept-autogenerar`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action:"accept_new_topic",edited_label:Le,type:Ie||void 0})})),qe.add(Y),await M(),we();break}case"retry":{await E(async()=>Re(`/api/ingestion/sessions/${encodeURIComponent(X)}/documents/${encodeURIComponent(Y)}/retry`,{method:"POST"}));break}case"remove":break}await V({sessionId:X,showWheel:!1,reportError:!1})}catch(G){d($e(G),"error")}finally{i.setMutating(!1),le()}});const re=c.addCorpusDialog,he=c.addCorpusBtn;if(re&&he){let A=function(G){return G.normalize("NFD").replace(/[̀-ͯ]/g,"").toLowerCase().replace(/[^a-z0-9]+/g,"_").replace(/^_|_$/g,"")};const z=re.querySelector("#add-corpus-label"),ee=re.querySelector("#add-corpus-key"),Y=re.querySelector("#add-corpus-kw-strong"),X=re.querySelector("#add-corpus-kw-weak"),pe=re.querySelector("#add-corpus-error"),ne=re.querySelector("#add-corpus-cancel"),oe=re.querySelector("#add-corpus-form");he.addEventListener("click",()=>{z&&(z.value=""),ee&&(ee.value=""),Y&&(Y.value=""),X&&(X.value=""),pe&&(pe.hidden=!0),re.showModal(),z==null||z.focus()}),z==null||z.addEventListener("input",()=>{ee&&(ee.value=A(z.value))}),ne==null||ne.addEventListener("click",()=>{re.close()}),oe==null||oe.addEventListener("submit",async G=>{G.preventDefault(),pe&&(pe.hidden=!0);const Z=(z==null?void 0:z.value.trim())||"";if(!Z)return;const ke=((Y==null?void 0:Y.value)||"").split(",").map(Ie=>Ie.trim()).filter(Boolean),Le=((X==null?void 0:X.value)||"").split(",").map(Ie=>Ie.trim()).filter(Boolean);try{await E(async()=>St("/api/corpora",{label:Z,keywords_strong:ke.length?ke:void 0,keywords_weak:Le.length?Le:void 0})),re.close(),await te({showWheel:!1,reportError:!1});const Ie=A(Z);Ie&&i.setSelectedCorpus(Ie),H(),d(`Categoría "${Z}" creada.`,"success")}catch(Ie){pe&&(pe.textContent=$e(Ie),pe.hidden=!1)}})}}function ys(e){const{i18n:t,stateController:n,dom:s,withThinkingWheel:a,setFlash:o}=e,{ingestionCorpusSelect:c,ingestionBatchTypeSelect:i,ingestionDropzone:p,ingestionFileInput:d,ingestionFolderInput:y,ingestionSelectFilesBtn:E,ingestionSelectFolderBtn:h,ingestionUploadProgress:$,ingestionPendingFiles:N,ingestionOverview:g,ingestionRefreshBtn:P,ingestionCreateSessionBtn:m,ingestionUploadBtn:u,ingestionProcessBtn:l,ingestionAutoProcessBtn:r,ingestionValidateBatchBtn:f,ingestionRetryBtn:v,ingestionDeleteSessionBtn:S,ingestionSessionMeta:x,ingestionSessionsList:j,selectedSessionMeta:I,ingestionLastError:W,ingestionLastErrorMessage:K,ingestionLastErrorGuidance:q,ingestionLastErrorNext:w,ingestionKanban:_,ingestionLogAccordion:b,ingestionLogBody:D,ingestionLogCopyBtn:R,ingestionAutoStatus:fe}=s,{state:T}=n,ge=fs(e);ge.toast;const L=gs(ge),{resolveSessionCorpus:M,fetchCorpora:te,fetchIngestionSessions:V,fetchIngestionSession:ye,createIngestionSession:ie,uploadIngestionFile:me,startIngestionProcess:Ee,validateBatch:Pe,retryIngestionSession:Ce,ejectIngestionSession:H,refreshIngestion:we,refreshSelectedSession:le,ensureSelectedSession:Ne}=L,Me=bs(ge,L),{resolveFolderFiles:qe,readDirectoryHandle:be,uploadFilesWithConcurrency:Ae,renderUploadProgress:Te,renderScanProgress:re,persistFolderPending:he,clearFolderPending:A,getStoredFolderPendingCount:z,requestPreflight:ee}=Me;let Y=[];function X(k){const B=`[${new Date().toISOString().slice(11,23)}] ${k}`;Y.push(B),console.log(`[folder-ingest] ${k}`),b.hidden=!1,D.hidden=!1,D.textContent=Y.join(`
`);const O=document.getElementById("ingestion-log-toggle");if(O){O.setAttribute("aria-expanded","true");const J=O.querySelector(".ops-log-accordion-marker");J&&(J.textContent="▾")}}function pe(){Y=[],ne()}function ne(){const{ingestionBounceLog:k,ingestionBounceBody:C}=s;k&&(k.hidden=!0,k.open=!1),C&&(C.textContent="")}const oe={directFolderIngest:()=>Promise.resolve(),renderControls:()=>{}},G=hs(ge,L,Me,oe),{addFilesToIntake:Z,clearIntake:ke,confirmAndIngest:Le,removeIntakeEntry:Ie,cancelAllWillIngest:Je}=G,Ke=new Set;function ct(){const k=T.selectedCorpus;c.innerHTML="";const C=document.createElement("option");C.value="autogenerar",C.textContent="AUTOGENERAR",C.selected=k==="autogenerar",c.appendChild(C),[...T.corpora].sort((B,O)=>B.label.localeCompare(O.label,"es")).forEach(B=>{var F;const O=document.createElement("option");O.value=B.key;const J=((F=B.attention)==null?void 0:F.length)||0;let Q=B.active?B.label:`${B.label} (${t.t("ops.ingestion.corpusInactiveOption")})`;J>0&&(Q+=` ⚠ ${J}`),O.textContent=Q,O.selected=B.key===k,c.appendChild(O)})}function un(k,C,B){var ve;const O=document.createElement("div");O.className="ops-intake-row",C.verdict==="pending"&&O.classList.add("ops-intake-row--pending"),B.readonly&&O.classList.add("ops-intake-row--readonly");const J=document.createElement("span");J.className="ops-intake-row__icon",J.textContent="📄";const Q=document.createElement("span");Q.className="ops-intake-row__name",Q.textContent=C.relativePath||C.file.name,Q.title=C.relativePath||C.file.name;const F=document.createElement("span");F.className="ops-intake-row__size",F.textContent=us(C.file.size);const se=ms(C,t);if(O.append(J,Q,F,se),B.showReason&&((ve=C.preflightEntry)!=null&&ve.reason)){const ce=document.createElement("span");ce.className="ops-intake-row__reason",ce.textContent=C.preflightEntry.reason,ce.title=C.preflightEntry.reason,O.appendChild(ce)}if(B.removable){const ce=document.createElement("button");ce.type="button",ce.className="ops-intake-row__remove",ce.textContent="✕",ce.title=t.t("ops.ingestion.willIngest.cancelAll"),ce.addEventListener("click",Oe=>{Oe.stopPropagation(),Ie(C)}),O.appendChild(ce)}k.appendChild(O)}function bt(k,C,B,O,J,Q){const F=document.createElement("section");F.className=`ops-intake-panel ops-intake-panel--${k}`;const se=document.createElement("header");se.className="ops-intake-panel__header";const ve=document.createElement("span");ve.className="ops-intake-panel__title",ve.textContent=t.t(C),se.appendChild(ve);const ce=document.createElement("span");if(ce.className="ops-intake-panel__count",ce.textContent=t.t(B,{count:O}),se.appendChild(ce),Q.readonly){const Se=document.createElement("span");Se.className="ops-intake-panel__readonly",Se.textContent=t.t("ops.ingestion.bounced.readonly"),se.appendChild(Se)}if(Q.cancelAllAction){const Se=document.createElement("button");Se.type="button",Se.className="ops-intake-panel__action",Se.textContent=t.t("ops.ingestion.willIngest.cancelAll"),Se.addEventListener("click",ze=>{ze.stopPropagation(),Q.cancelAllAction()}),se.appendChild(Se)}F.appendChild(se);const Oe=document.createElement("div");return Oe.className="ops-intake-panel__body",J.forEach(Se=>un(Oe,Se,Q)),F.appendChild(Oe),F}function pn(){var O,J;if((O=p.querySelector(".ops-intake-windows"))==null||O.remove(),(J=p.querySelector(".dropzone-file-list"))==null||J.remove(),T.intake.length===0){N.textContent=t.t("ops.ingestion.pendingNone"),N.hidden=!0,p.classList.remove("has-files");return}N.hidden=!0,p.classList.add("has-files");const k=document.createElement("div");k.className="ops-intake-windows";const C=mn();C&&k.appendChild(C),k.appendChild(bt("intake","ops.ingestion.intake.title","ops.ingestion.intake.count",T.intake.length,T.intake,{removable:!1,readonly:!1,showReason:!1}));const B=T.reviewPlan;B&&(k.appendChild(bt("will-ingest","ops.ingestion.willIngest.title","ops.ingestion.willIngest.count",B.willIngest.length,B.willIngest,{removable:!0,readonly:!1,showReason:!1,cancelAllAction:B.willIngest.length>0?()=>Je():void 0})),B.bounced.length>0&&k.appendChild(bt("bounced","ops.ingestion.bounced.title","ops.ingestion.bounced.count",B.bounced.length,B.bounced,{removable:!1,readonly:!0,showReason:!0}))),p.appendChild(k)}function mn(){var F;const k=((F=T.reviewPlan)==null?void 0:F.stalePartial)===!0,C=T.intake.some(se=>se.verdict==="pending"),B=G.getIntakeError();if(!k&&!C&&!B)return null;const O=document.createElement("div");if(O.className="ops-intake-banner",B){O.classList.add("ops-intake-banner--error");const se=document.createElement("span");se.className="ops-intake-banner__text",se.textContent=t.t("ops.ingestion.intake.failed");const ve=document.createElement("button");return ve.type="button",ve.className="ops-intake-banner__retry",ve.textContent=t.t("ops.ingestion.intake.retry"),ve.addEventListener("click",ce=>{ce.stopPropagation(),G.setIntakeError(!1),G.schedulePreflight(),nt()}),O.append(se,ve),O}const J=document.createElement("span");J.className="ops-intake-banner__spinner",O.appendChild(J);const Q=document.createElement("span");return Q.className="ops-intake-banner__text",k?(O.classList.add("ops-intake-banner--stale"),Q.textContent=t.t("ops.ingestion.intake.stale")):(O.classList.add("ops-intake-banner--verifying"),Q.textContent=t.t("ops.ingestion.intake.verifying")),O.appendChild(Q),O}function tt(){var Ue,Ye,st,at,de;const k=n.selectedCorpusConfig(),C=T.selectedSession,B=T.selectedCorpus==="autogenerar"?T.corpora.some(Be=>Be.active):!!(k!=null&&k.active),O=ft(String((C==null?void 0:C.status)||""));i.value=i.value||"autogenerar";const J=((Ue=T.folderUploadProgress)==null?void 0:Ue.uploading)??!1,Q=T.reviewPlan,F=(Q==null?void 0:Q.willIngest.length)??0,se=(Q==null?void 0:Q.stalePartial)===!0,ve=G.getIntakeError()===!0,ce=!!Q&&F>0&&!se&&!ve;m.disabled=T.mutating||!B,E.disabled=T.mutating||!B||J,h.disabled=T.mutating||!B||J||O,u.disabled=T.mutating||!B||!ce||J,Q?F===0?u.textContent=t.t("ops.ingestion.approveNone"):u.textContent=t.t("ops.ingestion.approveCount",{count:F}):u.textContent=t.t("ops.ingestion.approve"),l.disabled=T.mutating||!B||!C||O,r.disabled=T.mutating||!B||J||!C||O,r.textContent=`▶ ${t.t("ops.ingestion.actions.autoProcess")}`;const Oe=Number(((Ye=C==null?void 0:C.batch_summary)==null?void 0:Ye.done)||0),Se=Number(((st=C==null?void 0:C.batch_summary)==null?void 0:st.queued)||0)+Number(((at=C==null?void 0:C.batch_summary)==null?void 0:at.processing)||0),ze=Number(((de=C==null?void 0:C.batch_summary)==null?void 0:de.pending_batch_gate)||0),Fe=Oe>=1&&(Se>=1||ze>=1);if(f.disabled=T.mutating||!B||!C||O||!Fe,v.disabled=T.mutating||!B||!C||O,S.disabled=T.mutating||!C,P.disabled=T.mutating,c.disabled=T.mutating||T.corpora.length===0,d.disabled=T.mutating||!B,!B){g.textContent=t.t("ops.ingestion.corpusInactive");return}g.textContent=t.t("ops.ingestion.overview",{active:T.corpora.filter(Be=>Be.active).length,total:T.corpora.length,corpus:T.selectedCorpus==="autogenerar"?"AUTOGENERAR":(k==null?void 0:k.label)||T.selectedCorpus,session:(C==null?void 0:C.session_id)||t.t("ops.ingestion.noSession")})}function gn(){if(j.innerHTML="",x.textContent=T.selectedSession?`${T.selectedSession.session_id} · ${T.selectedSession.status}`:t.t("ops.ingestion.selectedEmpty"),T.sessions.length===0){const k=document.createElement("li");k.className="ops-empty",k.textContent=t.t("ops.ingestion.sessionsEmpty"),j.appendChild(k);return}T.sessions.forEach(k=>{var st,at;const C=document.createElement("li"),B=k.status==="partial_failed",O=document.createElement("button");O.type="button",O.className=`ops-session-item${k.session_id===T.selectedSessionId?" is-active":""}${B?" has-retry-action":""}`,O.dataset.sessionId=k.session_id;const J=document.createElement("div");J.className="ops-session-item-head";const Q=document.createElement("div");Q.className="ops-session-id",Q.textContent=k.session_id;const F=document.createElement("span");F.className=`meta-chip status-${it(k.status)}`,F.textContent=k.status,J.append(Q,F);const se=document.createElement("div");se.className="ops-session-pills";const ve=((st=T.corpora.find(de=>de.key===k.corpus))==null?void 0:st.label)||k.corpus,ce=document.createElement("span");ce.className="meta-chip ops-pill-corpus",ce.textContent=ve,se.appendChild(ce);const Oe=k.documents||[];[...new Set(Oe.map(de=>de.batch_type).filter(Boolean))].forEach(de=>{const Be=document.createElement("span");Be.className="meta-chip ops-pill-batch",Be.textContent=Un(de,t),se.appendChild(Be)});const ze=Oe.map(de=>de.filename).filter(Boolean);let Fe=null;if(ze.length>0){Fe=document.createElement("div"),Fe.className="ops-session-files";const de=ze.slice(0,3),Be=ze.length-de.length;Fe.textContent=de.join(", ")+(Be>0?` +${Be}`:"")}const Ue=document.createElement("div");Ue.className="ops-session-summary",Ue.textContent=qt(k.batch_summary,t);const Ye=document.createElement("div");if(Ye.className="ops-session-summary",Ye.textContent=k.updated_at?t.formatDateTime(k.updated_at,{dateStyle:"short",timeStyle:"short",timeZone:"America/Bogota"}):"-",O.appendChild(J),O.appendChild(se),Fe&&O.appendChild(Fe),O.appendChild(Ue),O.appendChild(Ye),(at=k.last_error)!=null&&at.code){const de=document.createElement("div");de.className="ops-session-summary status-error",de.textContent=k.last_error.code,O.appendChild(de)}if(O.addEventListener("click",async()=>{n.setSelectedSession(k),nt();try{await le({sessionId:k.session_id,showWheel:!0})}catch{}}),C.appendChild(O),B){const de=document.createElement("button");de.type="button",de.className="ops-session-retry-inline",de.textContent=t.t("ops.ingestion.actions.retry"),de.disabled=T.mutating,de.addEventListener("click",async Be=>{Be.stopPropagation(),de.disabled=!0,n.setMutating(!0),tt();try{await a(async()=>Ce(k.session_id)),await we({showWheel:!1,reportError:!0,focusSessionId:k.session_id}),o(t.t("ops.ingestion.flash.retryStarted",{id:k.session_id}),"success")}catch(_n){o($e(_n),"error")}finally{n.setMutating(!1),tt()}}),C.appendChild(de)}j.appendChild(C)})}function fn(k){const C=[],B=()=>new Date().toISOString();if(C.push(t.t("ops.ingestion.log.sessionHeader",{id:k.session_id})),C.push(`Corpus:     ${k.corpus||"-"}`),C.push(`Status:     ${k.status}`),C.push(`Created:    ${k.created_at||"-"}`),C.push(`Updated:    ${k.updated_at||"-"}`),C.push(`Heartbeat:  ${k.heartbeat_at??"-"}`),k.auto_processing&&C.push(`Auto-proc:  ${k.auto_processing}`),k.gate_sub_stage&&C.push(`Gate-stage: ${k.gate_sub_stage}`),k.wip_sync_status&&C.push(`WIP-sync:   ${k.wip_sync_status}`),k.batch_summary){const J=k.batch_summary,Q=(k.documents||[]).filter(se=>se.status==="raw"||se.status==="needs_classification").length,F=(k.documents||[]).filter(se=>se.status==="pending_dedup").length;C.push(""),C.push("── Resumen del lote ──"),C.push(`  Total: ${J.total}  Queued: ${J.queued}  Processing: ${J.processing}  Done: ${J.done}  Failed: ${J.failed}  Duplicados: ${J.skipped_duplicate}  Bounced: ${J.bounced}`),Q>0&&C.push(`  Raw (sin clasificar): ${Q}`),F>0&&C.push(`  Pending dedup: ${F}`)}k.last_error&&(C.push(""),C.push("── Error de sesión ──"),C.push(`  Código:    ${k.last_error.code||"-"}`),C.push(`  Mensaje:   ${k.last_error.message||"-"}`),C.push(`  Guía:      ${k.last_error.guidance||"-"}`),C.push(`  Siguiente: ${k.last_error.next_step||"-"}`));const O=k.documents||[];if(O.length===0)C.push(""),C.push(t.t("ops.ingestion.log.noDocuments"));else{C.push(""),C.push(`── Documentos (${O.length}) ──`);const J={failed:0,processing:1,in_progress:1,queued:2,raw:2,done:3,completed:3,bounced:4,skipped_duplicate:5},Q=[...O].sort((F,se)=>(J[F.status]??3)-(J[se.status]??3));for(const F of Q)C.push(""),C.push(`  ┌─ ${F.filename} (${F.doc_id})`),C.push(`  │  Status:   ${F.status}  │  Stage: ${F.stage||"-"}  │  Progress: ${F.progress??0}%`),C.push(`  │  Bytes:    ${F.bytes??"-"}  │  Batch: ${F.batch_type||"-"}`),F.source_relative_path&&C.push(`  │  Path:     ${F.source_relative_path}`),(F.detected_topic||F.detected_type)&&(C.push(`  │  Topic:    ${F.detected_topic||"-"}  │  Type: ${F.detected_type||"-"}  │  Confidence: ${F.combined_confidence??"-"}`),F.classification_source&&C.push(`  │  Classifier: ${F.classification_source}`)),F.chunk_count!=null&&C.push(`  │  Chunks:   ${F.chunk_count}  │  Elapsed: ${F.elapsed_ms??"-"}ms`),F.dedup_match_type&&C.push(`  │  Dedup:    ${F.dedup_match_type}  │  Match: ${F.dedup_match_doc_id||"-"}`),F.replaced_doc_id&&C.push(`  │  Replaced: ${F.replaced_doc_id}`),F.error&&(C.push("  │  ❌ ERROR"),C.push(`  │    Código:    ${F.error.code||"-"}`),C.push(`  │    Mensaje:   ${F.error.message||"-"}`),C.push(`  │    Guía:      ${F.error.guidance||"-"}`),C.push(`  │    Siguiente: ${F.error.next_step||"-"}`)),C.push(`  │  Created: ${F.created_at||"-"}  │  Updated: ${F.updated_at||"-"}`),C.push("  └─")}return C.push(""),C.push(`Log generado: ${B()}`),C.join(`
`)}function Et(){if(Y.length>0)return;const k=T.selectedSession;if(!k){b.hidden=!0,D.textContent="";return}b.hidden=!1,D.textContent=fn(k)}function bn(){const k=T.selectedSession;if(!k){I.textContent=t.t("ops.ingestion.selectedEmpty"),W.hidden=!0,Y.length===0&&(b.hidden=!0),_.innerHTML="";return}const C=z(k.session_id),B=C>0?` · ${t.t("ops.ingestion.folderResumePending",{count:C})}`:"";if(I.textContent=`${k.session_id} · ${qt(k.batch_summary,t)}${B}`,k.last_error?(W.hidden=!1,K.textContent=k.last_error.message||k.last_error.code||"-",q.textContent=k.last_error.guidance||"",w.textContent=`${t.t("ops.ingestion.lastErrorNext")}: ${k.last_error.next_step||"-"}`):W.hidden=!0,(k.documents||[]).length===0){_.innerHTML=`<p class="ops-empty">${t.t("ops.ingestion.documentsEmpty")}</p>`,_.style.minHeight="0",Et();return}_.style.minHeight="",cs(k,_,t,Ke,T.corpora),Ke.clear(),Et()}function nt(){ct(),pn(),tt(),gn(),bn()}ge.render=nt,ge.trace=X,oe.directFolderIngest=Nt,oe.renderControls=tt;const Pt=vs(ge,L),{startAutoPilot:hn,stopAutoPilot:ca,updateAutoStatus:la}=Pt;async function Nt(){var Oe,Se,ze;X(`directFolderIngest: ${T.pendingFiles.length} archivos pendientes`);const k=await Ne();X(`Sesión asignada: ${k.session_id} (corpus=${k.corpus}, status=${k.status})`);const C=i.value||"autogenerar";X(`Subiendo ${T.pendingFiles.length} archivos con batchType="${C}"...`),he(k.session_id);const B=await Ae(k.session_id,[...T.pendingFiles],C,kt);if(console.log("[folder-ingest] Upload result:",{uploaded:B.uploaded,failed:B.failed}),X(`Upload completo: ${B.uploaded} subidos, ${B.failed} fallidos${B.errors.length>0?" — "+B.errors.slice(0,5).map(Fe=>`${Fe.filename}: ${Fe.error}`).join("; "):""}`),n.setPendingFiles([]),n.setFolderUploadProgress(null),A(k.session_id),y.value="",d.value="",B.failed>0&&B.uploaded===0){const Fe=B.errors.slice(0,3).map(Ue=>`${Ue.filename}: ${Ue.error}`).join("; ");X(`TODOS FALLARON: ${Fe}`),o(`${t.t("ops.ingestion.flash.folderUploadPartial",B)} — ${Fe}`,"error"),await we({showWheel:!1,reportError:!0,focusSessionId:k.session_id});return}X("Consultando estado de sesión post-upload...");const O=await ye(k.session_id),J=Number(((Oe=O.batch_summary)==null?void 0:Oe.bounced)??0),Q=ut(O),F=Number(((Se=O.batch_summary)==null?void 0:Se.queued)??0),se=Number(((ze=O.batch_summary)==null?void 0:ze.total)??0),ve=se-J;if(X(`Sesión post-upload: total=${se} bounced=${J} raw=${Q} queued=${F} actionable=${ve}`),ve===0&&J>0){X(`TODOS REBOTADOS: ${J} archivos ya existen en el corpus`),n.upsertSession(O),o(`${J} archivos ya existen en el corpus (rebotados). 0 archivos nuevos para procesar.`,"error"),X("--- FIN (todo rebotado) ---");return}X("Auto-procesando con threshold=0 (force-queue)..."),await Re(`/api/ingestion/sessions/${encodeURIComponent(k.session_id)}/auto-process`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({max_concurrency:5,auto_accept_threshold:0})}),await Ee(k.session_id),await we({showWheel:!1,reportError:!0,focusSessionId:k.session_id});const ce=[];B.uploaded>0&&ce.push(`${ve} archivos en proceso`),J>0&&ce.push(`${J} rebotados`),B.failed>0&&ce.push(`${B.failed} fallidos`),o(ce.join(" · "),B.failed>0?"error":"success"),X(`Auto-piloto iniciado para ${k.session_id}`),X("--- FIN (éxito) ---"),hn(k.session_id)}function vn(){_s({ctx:ge,api:L,upload:Me,intake:G,autoPilot:Pt,render:nt,renderCorpora:ct,renderControls:tt,traceClear:pe,directFolderIngest:Nt,suppressPanelsOnNextRender:Ke})}return{bindEvents:vn,refreshIngestion:we,refreshSelectedSession:le,render:nt}}function Ze(e){if(e==null)return null;const t=Number(e);return!Number.isFinite(t)||t<0?null:t}function an({i18n:e,stateController:t,dom:n,withThinkingWheel:s,setFlash:a}){const{monitorTabBtn:o,ingestionTabBtn:c,controlTabBtn:i,embeddingsTabBtn:p,reindexTabBtn:d,monitorPanel:y,ingestionPanel:E,controlPanel:h,embeddingsPanel:$,reindexPanel:N,runsBody:g,timelineNode:P,timelineMeta:m,cascadeNote:u,userCascadeNode:l,userCascadeSummary:r,technicalCascadeNode:f,technicalCascadeSummary:v,refreshRunsBtn:S}=n,{state:x}=t;function j(L){const M=Ze(L);return M===null?"-":`${e.formatNumber(M/1e3,{minimumFractionDigits:2,maximumFractionDigits:2})} s`}function I(L){t.setActiveTab(L),W()}function W(){if(!o)return;const L=x.activeTab;o.classList.toggle("is-active",L==="monitor"),o.setAttribute("aria-selected",String(L==="monitor")),c==null||c.classList.toggle("is-active",L==="ingestion"),c==null||c.setAttribute("aria-selected",String(L==="ingestion")),i==null||i.classList.toggle("is-active",L==="control"),i==null||i.setAttribute("aria-selected",String(L==="control")),p==null||p.classList.toggle("is-active",L==="embeddings"),p==null||p.setAttribute("aria-selected",String(L==="embeddings")),d==null||d.classList.toggle("is-active",L==="reindex"),d==null||d.setAttribute("aria-selected",String(L==="reindex")),y&&(y.hidden=L!=="monitor",y.classList.toggle("is-active",L==="monitor")),E&&(E.hidden=L!=="ingestion",E.classList.toggle("is-active",L==="ingestion")),h&&(h.hidden=L!=="control",h.classList.toggle("is-active",L==="control")),$&&($.hidden=L!=="embeddings",$.classList.toggle("is-active",L==="embeddings")),N&&(N.hidden=L!=="reindex",N.classList.toggle("is-active",L==="reindex"))}function K(L){if(P.innerHTML="",!Array.isArray(L)||L.length===0){P.innerHTML=`<li>${e.t("ops.timeline.empty")}</li>`;return}L.forEach(M=>{const te=document.createElement("li");te.innerHTML=`
        <strong>${M.stage||"-"}</strong> · <span class="status-${it(String(M.status||""))}">${M.status||"-"}</span><br/>
        <small>${M.at||"-"} · ${M.duration_ms||0} ms</small>
        <pre>${JSON.stringify(M.details||{},null,2)}</pre>
      `,P.appendChild(te)})}function q(L,M,te){const V=Ze(M==null?void 0:M.total_ms),ye=V===null?e.t("ops.timeline.summaryPending"):j(V),ie=te==="user"&&String((M==null?void 0:M.chat_run_id)||"").trim()?` · chat_run ${String((M==null?void 0:M.chat_run_id)||"").trim()}`:"";L.textContent=`${e.t("ops.timeline.totalLabel")} ${ye}${ie}`}function w(L){var me,Ee,Pe;const M=[],te=String(((me=L.details)==null?void 0:me.source)||"").trim(),V=String(L.status||"").trim();te&&M.push(te),V&&V!=="ok"&&V!=="missing"&&M.push(V);const ye=Number(((Ee=L.details)==null?void 0:Ee.citations_count)||0);Number.isFinite(ye)&&ye>0&&M.push(`${ye} refs`);const ie=String(((Pe=L.details)==null?void 0:Pe.panel_status)||"").trim();return ie&&M.push(ie),M.join(" · ")}function _(L,M,te){L.innerHTML="";const V=Array.isArray(M==null?void 0:M.steps)?(M==null?void 0:M.steps)||[]:[];if(V.length===0){L.innerHTML=`<li class="ops-cascade-step is-empty">${e.t("ops.timeline.waterfallEmpty")}</li>`;return}const ye=Ze(M==null?void 0:M.total_ms)??Math.max(1,...V.map(ie=>Ze(ie.cumulative_ms)??Ze(ie.absolute_elapsed_ms)??0));V.forEach(ie=>{const me=Ze(ie.duration_ms),Ee=Ze(ie.offset_ms)??0,Pe=Ze(ie.absolute_elapsed_ms),Ce=document.createElement("li");Ce.className=`ops-cascade-step ops-cascade-step--${te}${me===null?" is-missing":""}`;const H=document.createElement("div");H.className="ops-cascade-step-head";const we=document.createElement("div"),le=document.createElement("strong");le.textContent=ie.label||"-";const Ne=document.createElement("small");Ne.className="ops-cascade-step-meta",Ne.textContent=me===null?e.t("ops.timeline.missingStep"):`${e.t("ops.timeline.stepLabel")} ${j(me)} · T+${j(Pe??ie.cumulative_ms)}`,we.append(le,Ne);const Me=document.createElement("span");Me.className=`meta-chip status-${it(String(ie.status||""))}`,Me.textContent=String(ie.status||(me===null?"missing":"ok")),H.append(we,Me),Ce.appendChild(H);const qe=document.createElement("div");qe.className="ops-cascade-track";const be=document.createElement("span");be.className="ops-cascade-segment";const Ae=Math.max(0,Math.min(100,Ee/ye*100)),Te=me===null?0:Math.max(me/ye*100,me>0?2.5:0);be.style.left=`${Ae}%`,be.style.width=`${Te}%`,be.setAttribute("aria-label",me===null?`${ie.label}: ${e.t("ops.timeline.missingStep")}`:`${ie.label}: ${j(me)}`),qe.appendChild(be),Ce.appendChild(qe);const re=w(ie);if(re){const he=document.createElement("p");he.className="ops-cascade-step-detail",he.textContent=re,Ce.appendChild(he)}L.appendChild(Ce)})}async function b(){return(await De("/api/ops/runs?limit=30")).runs||[]}async function D(L){return De(`/api/ops/runs/${encodeURIComponent(L)}/timeline`)}function R(L,M){var V;const te=L.run||{};m.textContent=e.t("ops.timeline.label",{id:M}),u.textContent=e.t("ops.timeline.selectedRunMeta",{trace:String(te.trace_id||"-"),chatRun:String(((V=L.user_waterfall)==null?void 0:V.chat_run_id)||te.chat_run_id||"-")}),q(r,L.user_waterfall,"user"),q(v,L.technical_waterfall,"technical"),_(l,L.user_waterfall,"user"),_(f,L.technical_waterfall,"technical"),K(Array.isArray(L.timeline)?L.timeline:[])}function fe(L){if(g.innerHTML="",!Array.isArray(L)||L.length===0){const M=document.createElement("tr");M.innerHTML=`<td colspan="4">${e.t("ops.runs.empty")}</td>`,g.appendChild(M);return}L.forEach(M=>{const te=document.createElement("tr");te.innerHTML=`
        <td><button type="button" class="link-btn" data-run-id="${M.run_id}">${M.run_id}</button></td>
        <td>${M.trace_id||"-"}</td>
        <td class="status-${it(String(M.status||""))}">${M.status||"-"}</td>
        <td>${M.started_at?e.formatDateTime(M.started_at,{dateStyle:"short",timeStyle:"short",timeZone:"America/Bogota"}):"-"}</td>
      `,g.appendChild(te)}),g.querySelectorAll("button[data-run-id]").forEach(M=>{M.addEventListener("click",async()=>{const te=M.getAttribute("data-run-id")||"";try{const V=await s(async()=>D(te));R(V,te)}catch(V){l.innerHTML=`<li class="ops-cascade-step is-empty status-error">${$e(V)}</li>`,f.innerHTML=`<li class="ops-cascade-step is-empty status-error">${$e(V)}</li>`,P.innerHTML=`<li class="status-error">${$e(V)}</li>`}})})}async function T({showWheel:L=!0,reportError:M=!0}={}){const te=async()=>{const V=await b();fe(V)};try{L?await s(te):await te()}catch(V){g.innerHTML=`<tr><td colspan="4" class="status-error">${$e(V)}</td></tr>`,M&&a($e(V),"error")}}function ge(){o==null||o.addEventListener("click",()=>{I("monitor")}),c==null||c.addEventListener("click",()=>{I("ingestion")}),i==null||i.addEventListener("click",()=>{I("control")}),p==null||p.addEventListener("click",()=>{I("embeddings")}),d==null||d.addEventListener("click",()=>{I("reindex")}),S.addEventListener("click",()=>{a(),T({showWheel:!0,reportError:!0})})}return{bindEvents:ge,refreshRuns:T,renderTabs:W}}function We(e){return String(e??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#39;")}function Qe(e){return(e??0).toLocaleString("es-CO")}function $s(e){if(e==null||e<=0)return"-";const t=Math.floor(e/60),n=Math.floor(e%60);return t>0?`${t}m ${n}s`:`${n}s`}function ws(e){if(!e.length)return"";let t='<ol class="reindex-stage-list">';for(const n of e){const s=n.state==="completed"?"ops-dot-ok":n.state==="active"?"ops-dot-active":n.state==="failed"?"ops-dot-error":"ops-dot-pending",a=n.state==="active"?`<strong>${We(n.label)}</strong>`:We(n.label);t+=`<li class="reindex-stage-item reindex-stage-${n.state}"><span class="ops-dot ${s}">●</span> ${a}</li>`}return t+="</ol>",t}function on({dom:e,setFlash:t,navigateToEmbeddings:n}){const{container:s}=e;let a=null,o="";function c(){var u,l,r;const E=a;if(!E){s.innerHTML='<p class="ops-text-muted">Cargando estado de re-index...</p>';return}const h=E.current_operation||E.last_operation,$=((u=E.current_operation)==null?void 0:u.status)==="running",N=!E.current_operation;let g="";const P=$?"En ejecución":N?"Inactivo":(h==null?void 0:h.status)??"—",m=$?"tone-yellow":(h==null?void 0:h.status)==="completed"?"tone-green":(h==null?void 0:h.status)==="failed"?"tone-red":"";if(g+=`<div class="reindex-status-row">
      <span class="corpus-status-chip ${m}">${We(P)}</span>
      <span class="emb-target-badge">WIP</span>
      ${$?`<span class="emb-heartbeat ${$t(h==null?void 0:h.heartbeat_at,h==null?void 0:h.updated_at)}">${$t(h==null?void 0:h.heartbeat_at,h==null?void 0:h.updated_at)}</span>`:""}
    </div>`,g+='<div class="reindex-controls">',N&&(g+=`<button class="corpus-btn corpus-btn-promote" id="reindex-start-btn" ${o?"disabled":""}>Iniciar re-index</button>`),$&&h&&(g+=`<button class="corpus-btn corpus-btn-rollback" id="reindex-stop-btn" ${o?"disabled":""}>Detener</button>`),g+="</div>",(l=h==null?void 0:h.stages)!=null&&l.length&&(g+=ws(h.stages)),h!=null&&h.progress){const f=h.progress,v=[];f.documents_processed!=null&&v.push(`Documentos: ${Qe(f.documents_processed)} / ${Qe(f.documents_total)}`),f.documents_indexed!=null&&v.push(`Documentos indexados: ${Qe(f.documents_indexed)}`),f.elapsed_seconds!=null&&v.push(`Tiempo: ${$s(f.elapsed_seconds)}`),v.length&&(g+=`<div class="reindex-progress-stats">${v.map(S=>`<span>${We(S)}</span>`).join("")}</div>`)}if(h!=null&&h.quality_report){const f=h.quality_report;if(g+='<div class="reindex-quality-report">',g+="<h3>Reporte de calidad</h3>",g+=`<div class="emb-stats-grid">
        <div class="emb-stat"><span class="emb-stat-value">${Qe(f.documents_indexed)}</span><span class="emb-stat-label">Documentos</span></div>
        <div class="emb-stat"><span class="emb-stat-value">${Qe(f.chunks_generated)}</span><span class="emb-stat-label">Chunks</span></div>
        <div class="emb-stat"><span class="emb-stat-value">${f.blocking_issues??0}</span><span class="emb-stat-label">Blocking issues</span></div>
      </div>`,f.knowledge_class_counts){g+='<div class="reindex-kc-breakdown"><h4>Knowledge classes</h4><dl class="reindex-kc-dl">';for(const[v,S]of Object.entries(f.knowledge_class_counts))g+=`<dt>${We(v)}</dt><dd>${Qe(S)}</dd>`;g+="</dl></div>"}g+="</div>",g+=`<div class="reindex-embed-prompt">
        <p>Re-index completado. Para aplicar los nuevos summaries a los embeddings:</p>
        <button class="corpus-btn corpus-btn-promote" id="reindex-embed-now-btn">Embed ahora</button>
      </div>`}if((r=h==null?void 0:h.checks)!=null&&r.length){g+='<div class="emb-checks">';for(const f of h.checks){const v=f.ok?'<span class="ops-dot ops-dot-ok">●</span>':'<span class="ops-dot ops-dot-error">●</span>';g+=`<div class="emb-check">${v} <strong>${We(f.label)}</strong>: ${We(f.detail)}</div>`}g+="</div>"}h!=null&&h.log_tail&&(g+=`<details class="emb-log-accordion"><summary>Log</summary><pre class="emb-log-tail">${We(h.log_tail)}</pre></details>`),h!=null&&h.error&&(g+=`<p class="emb-error">${We(h.error)}</p>`),s.innerHTML=g}function i(){s.addEventListener("click",E=>{const h=E.target;h.id==="reindex-start-btn"&&p(),h.id==="reindex-stop-btn"&&d(),h.id==="reindex-embed-now-btn"&&n()})}async function p(){o="start",c();try{await Ge("/api/ops/reindex/start",{mode:"from_source"}),t("Re-index iniciado","success")}catch(E){t(String(E),"error")}o="",await y()}async function d(){var h;const E=(h=a==null?void 0:a.current_operation)==null?void 0:h.job_id;if(E){o="stop",c();try{await Ge("/api/ops/reindex/stop",{job_id:E}),t("Re-index detenido","success")}catch($){t(String($),"error")}o="",await y()}}async function y(){try{a=await De("/api/ops/reindex-status")}catch{}c()}return{bindEvents:i,refresh:y}}const ya=Object.freeze(Object.defineProperty({__proto__:null,createOpsReindexController:on},Symbol.toStringTag,{value:"Module"})),ks=3e3,Ft=8e3;function rn({stateController:e,withThinkingWheel:t,setFlash:n,refreshRuns:s,refreshIngestion:a,refreshCorpusLifecycle:o,refreshEmbeddings:c,refreshReindex:i,intervalMs:p}){(async()=>{try{await t(async()=>{await Promise.all([s({showWheel:!1,reportError:!1}),a({showWheel:!1,reportError:!1}),o==null?void 0:o(),c==null?void 0:c(),i==null?void 0:i()])})}catch($){n($e($),"error")}})();let d=null,y=p??Ft;function E(){const $=e.state.selectedSession;return $?ft(String($.status||""))?!0:($.documents||[]).some(g=>g.status==="in_progress"||g.status==="processing"||g.status==="extracting"||g.status==="etl"||g.status==="writing"||g.status==="gates"):!1}function h(){const $=p??(E()?ks:Ft);d!==null&&$===y||(d!==null&&window.clearInterval(d),y=$,d=window.setInterval(()=>{s({showWheel:!1,reportError:!1}),a({showWheel:!1,reportError:!1,focusSessionId:e.getFocusedRunningSessionId()}),o==null||o(),c==null||c(),i==null||i(),p||h()},y))}return h(),()=>{d!==null&&(window.clearInterval(d),d=null)}}function cn(){const e={activeTab:Dn(),corpora:[],selectedCorpus:"autogenerar",sessions:[],selectedSessionId:jn(),selectedSession:null,pendingFiles:[],intake:[],reviewPlan:null,preflightRunId:0,mutating:!1,folderUploadProgress:null,folderRelativePaths:new Map,rejectedArtifacts:[],preflightManifest:null,preflightScanProgress:null};function t(){return e.corpora.find(r=>r.key===e.selectedCorpus)}function n(r){e.activeTab=r,Bn(r)}function s(r){e.corpora=[...r]}function a(r){e.folderUploadProgress=r}function o(r){e.preflightManifest=r}function c(r){e.preflightScanProgress=r}function i(r){e.mutating=r}function p(r){e.pendingFiles=[...r]}function d(r){e.intake=[...r]}function y(r){e.reviewPlan=r?{...r,willIngest:[...r.willIngest],bounced:[...r.bounced]}:null}function E(){return e.preflightRunId+=1,e.preflightRunId}function h(r){e.selectedCorpus=r}function $(r){e.selectedSession=r,e.selectedSessionId=(r==null?void 0:r.session_id)||"",zn((r==null?void 0:r.session_id)||null),r&&(P=!1)}function N(){P=!0,$(null)}function g(r){e.sessions=[...r]}let P=!1;function m(){if(e.selectedSessionId){const r=e.sessions.find(f=>f.session_id===e.selectedSessionId)||null;$(r);return}if(P){$(null);return}$(e.sessions[0]||null)}function u(r){const f=e.sessions.filter(v=>v.session_id!==r.session_id);e.sessions=[r,...f].sort((v,S)=>Date.parse(String(S.updated_at||0))-Date.parse(String(v.updated_at||0))),$(r)}function l(){var r;return ft(String(((r=e.selectedSession)==null?void 0:r.status)||""))?e.selectedSessionId:""}return{state:e,clearSelectionAfterDelete:N,getFocusedRunningSessionId:l,selectedCorpusConfig:t,setActiveTab:n,setCorpora:s,setFolderUploadProgress:a,setMutating:i,setPendingFiles:p,setIntake:d,setReviewPlan:y,bumpPreflightRunId:E,setPreflightManifest:o,setPreflightScanProgress:c,setSelectedCorpus:h,setSelectedSession:$,setSessions:g,syncSelectedSession:m,upsertSession:u}}function Cs(e){const{value:t,unit:n,size:s="md",className:a=""}=e,o=document.createElement("span");o.className=["lia-metric-value",`lia-metric-value--${s}`,a].filter(Boolean).join(" "),o.setAttribute("data-lia-component","metric-value");const c=document.createElement("span");if(c.className="lia-metric-value__number",c.textContent=typeof t=="number"?t.toLocaleString("es-CO"):String(t),o.appendChild(c),n){const i=document.createElement("span");i.className="lia-metric-value__unit",i.textContent=n,o.appendChild(i)}return o}function lt(e){const{label:t,value:n,unit:s,hint:a,size:o="lg",tone:c="neutral",className:i=""}=e,p=document.createElement("div");p.className=["lia-metric-card",`lia-metric-card--${c}`,i].filter(Boolean).join(" "),p.setAttribute("data-lia-component","metric-card");const d=document.createElement("p");if(d.className="lia-metric-card__label",d.textContent=t,p.appendChild(d),p.appendChild(Cs({value:n,unit:s,size:o})),a){const y=document.createElement("p");y.className="lia-metric-card__hint",y.textContent=a,p.appendChild(y)}return p}function Ss(e){if(!e)return"sin activar";try{const t=new Date(e);if(Number.isNaN(t.getTime()))return"—";const n=Date.now()-t.getTime(),s=Math.floor(n/6e4);if(s<1)return"hace instantes";if(s<60)return`hace ${s} min`;const a=Math.floor(s/60);return a<24?`hace ${a} h`:`hace ${Math.floor(a/24)} d`}catch{return"—"}}function Es(e){const t=document.createElement("section");t.className="lia-corpus-overview",t.setAttribute("data-lia-component","corpus-overview");const n=document.createElement("header");n.className="lia-corpus-overview__header";const s=document.createElement("h2");s.className="lia-corpus-overview__title",s.textContent="Corpus activo",n.appendChild(s);const a=document.createElement("p");if(a.className="lia-corpus-overview__subtitle",e.activeGenerationId){const c=document.createElement("code");c.textContent=e.activeGenerationId,a.appendChild(document.createTextNode("Generación ")),a.appendChild(c),a.appendChild(document.createTextNode(` · activada ${Ss(e.activatedAt)}`))}else a.textContent="Ninguna generación activa en Supabase.";n.appendChild(a),t.appendChild(n);const o=document.createElement("div");return o.className="lia-corpus-overview__grid",o.appendChild(lt({label:"Documentos servidos",value:e.documents,hint:e.documents>0?`${e.chunks.toLocaleString("es-CO")} chunks indexados`:"—"})),o.appendChild(lt({label:"Grafo de normativa",value:e.graphNodes,unit:"nodos",hint:`${e.graphEdges.toLocaleString("es-CO")} relaciones tipadas`,tone:e.graphOk?"success":"warning"})),o.appendChild(lt({label:"Auditoría del corpus",value:e.auditIncluded,unit:"incluidos",hint:`${e.auditScanned.toLocaleString("es-CO")} escaneados · ${e.auditExcluded.toLocaleString("es-CO")} excluidos`})),o.appendChild(lt({label:"Revisiones pendientes",value:e.auditPendingRevisions,hint:e.auditPendingRevisions===0?"Cuello limpio":"Requieren resolución",tone:e.auditPendingRevisions===0?"success":"warning"})),t.appendChild(o),t}function Ps(e){const{tone:t,pulse:n=!1,ariaLabel:s,className:a=""}=e,o=document.createElement("span");return o.className=["lia-status-dot",`lia-status-dot--${t}`,n?"lia-status-dot--pulse":"",a].filter(Boolean).join(" "),o.setAttribute("data-lia-component","status-dot"),o.setAttribute("role","status"),s&&o.setAttribute("aria-label",s),o}const Ns={active:"active",superseded:"idle",running:"running",queued:"running",failed:"error",pending:"warning"},Dt={active:"Activa",superseded:"Reemplazada",running:"En curso",queued:"En cola",failed:"Falló",pending:"Pendiente"};function ln(e){const{status:t,className:n=""}=e,s=document.createElement("span");s.className=["lia-run-status",`lia-run-status--${t}`,n].filter(Boolean).join(" "),s.setAttribute("data-lia-component","run-status"),s.appendChild(Ps({tone:Ns[t],pulse:t==="running"||t==="queued",ariaLabel:Dt[t]}));const a=document.createElement("span");return a.className="lia-run-status__label",a.textContent=Dt[t],s.appendChild(a),s}function Is(e){if(!e)return"—";try{const t=new Date(e);return Number.isNaN(t.getTime())?"—":t.toLocaleString("es-CO",{day:"numeric",month:"short",hour:"2-digit",minute:"2-digit"})}catch{return e}}function xs(e,t){const n=document.createElement(t?"button":"div");n.className="lia-generation-row",n.setAttribute("data-lia-component","generation-row"),t&&(n.type="button",n.addEventListener("click",()=>t(e.generationId)));const s=document.createElement("span");s.className="lia-generation-row__id",s.textContent=e.generationId,n.appendChild(s),n.appendChild(ln({status:e.status}));const a=document.createElement("span");a.className="lia-generation-row__date",a.textContent=Is(e.generatedAt),n.appendChild(a);const o=document.createElement("span");o.className="lia-generation-row__count",o.textContent=`${e.documents.toLocaleString("es-CO")} docs`,n.appendChild(o);const c=document.createElement("span");if(c.className="lia-generation-row__count lia-generation-row__count--muted",c.textContent=`${e.chunks.toLocaleString("es-CO")} chunks`,n.appendChild(c),e.topClass&&e.topClassCount){const i=document.createElement("span");i.className="lia-generation-row__family",i.textContent=`${e.topClass}: ${e.topClassCount.toLocaleString("es-CO")}`,n.appendChild(i)}if(e.subtopicCoverage){const i=e.subtopicCoverage,p=e.documents>0?e.documents:1,d=Math.round(i.docsWithSubtopic/p*100),y=document.createElement("span");y.className="lia-generation-row__subtopic",y.setAttribute("data-lia-component","generation-row-subtopic");const E=i.docsRequiringReview&&i.docsRequiringReview>0?` (${i.docsRequiringReview} por revisar)`:"";y.textContent=`subtema: ${d}%${E}`,n.appendChild(y)}return n}function Bt(e){const{rows:t,emptyMessage:n="Aún no hay generaciones registradas.",errorMessage:s,onSelect:a}=e,o=document.createElement("section");o.className="lia-generations-list",o.setAttribute("data-lia-component","generations-list");const c=document.createElement("header");c.className="lia-generations-list__header";const i=document.createElement("h2");i.className="lia-generations-list__title",i.textContent="Generaciones recientes",c.appendChild(i);const p=document.createElement("p");p.className="lia-generations-list__subtitle",p.textContent="Cada fila es una corrida de python -m lia_graph.ingest publicada en Supabase.",c.appendChild(p),o.appendChild(c);const d=document.createElement("div");if(d.className="lia-generations-list__body",s){const y=document.createElement("p");y.className="lia-generations-list__feedback lia-generations-list__feedback--error",y.textContent=s,d.appendChild(y)}else if(t.length===0){const y=document.createElement("p");y.className="lia-generations-list__feedback",y.textContent=n,d.appendChild(y)}else{const y=document.createElement("div");y.className="lia-generations-list__head-row",["Generación","Estado","Fecha","Documentos","Chunks","Familia principal"].forEach(E=>{const h=document.createElement("span");h.className="lia-generations-list__head-cell",h.textContent=E,y.appendChild(h)}),d.appendChild(y),t.forEach(E=>d.appendChild(xs(E,a)))}return o.appendChild(d),o}const As=[{key:"knowledge_base",label:"knowledge_base/",sublabel:"snapshot Dropbox"},{key:"wip",label:"WIP",sublabel:"Supabase local + Falkor local"},{key:"cloud",label:"Cloud",sublabel:"Supabase cloud + Falkor cloud"}];function Ts(e){const{activeStage:t,className:n=""}=e,s=document.createElement("nav");return s.className=["lia-pipeline-flow",n].filter(Boolean).join(" "),s.setAttribute("data-lia-component","pipeline-flow"),s.setAttribute("aria-label","Pipeline de ingestión Lia Graph"),As.forEach((a,o)=>{if(o>0){const d=document.createElement("span");d.className="lia-pipeline-flow__arrow",d.setAttribute("aria-hidden","true"),d.textContent="→",s.appendChild(d)}const c=document.createElement("div");c.className=["lia-pipeline-flow__stage",a.key===t?"lia-pipeline-flow__stage--active":""].filter(Boolean).join(" "),c.setAttribute("data-stage",a.key);const i=document.createElement("span");i.className="lia-pipeline-flow__label",i.textContent=a.label,c.appendChild(i);const p=document.createElement("span");p.className="lia-pipeline-flow__sublabel",p.textContent=a.sublabel,c.appendChild(p),s.appendChild(c)}),s}function Ls(e){const{activeJobId:t,lastRunStatus:n,disabled:s,onTrigger:a}=e,o=document.createElement("section");o.className="lia-run-trigger",o.setAttribute("data-lia-component","run-trigger-card");const c=document.createElement("header");c.className="lia-run-trigger__header";const i=document.createElement("h2");i.className="lia-run-trigger__title",i.textContent="Iniciar nueva ingesta",c.appendChild(i);const p=document.createElement("p");p.className="lia-run-trigger__subtitle",p.textContent="Ejecuta make phase2-graph-artifacts-supabase contra knowledge_base/. Por defecto escribe a WIP (Supabase local + FalkorDB local). Cuando WIP esté validado, promueve a Cloud desde la pestaña Promoción.",c.appendChild(p),o.appendChild(c),o.appendChild(Ts({activeStage:"wip"}));const d=document.createElement("form");d.className="lia-run-trigger__form",d.setAttribute("novalidate","");const y=Rs({name:"supabase_target",legend:"Destino Supabase",options:[{value:"wip",label:"WIP (local)",hint:"Supabase docker + FalkorDB docker — ciclo seguro",defaultChecked:!0},{value:"production",label:"Producción (cloud)",hint:"Supabase cloud + FalkorDB cloud — afecta runtime servido"}]});d.appendChild(y);const E=qs({name:"suin_scope",label:"Scope SUIN-Juriscol",placeholder:"vacío para omitir, ej: et",hint:"Cuando es vacío, sólo se reingiere el corpus base. Pasa el scope (et, tributario, laboral, jurisprudencia) para incluir SUIN."});d.appendChild(E);const h=Ms([{name:"skip_embeddings",label:"Saltar embeddings",hint:"Si se marca, la etapa de embeddings no se encadena al final (auto_embed=false).",defaultChecked:!1},{name:"auto_promote",label:"Promover a cloud al terminar",hint:"Si se marca, la corrida encadena una promoción WIP→Cloud al finalizar sin errores.",defaultChecked:!1}]);d.appendChild(h);const $=document.createElement("div");$.className="lia-run-trigger__submit-row";const N=document.createElement("button");if(N.type="submit",N.className="lia-button lia-button--primary lia-run-trigger__submit",N.textContent=t?"Ejecutando…":"Iniciar ingesta",N.disabled=s,$.appendChild(N),n&&$.appendChild(ln({status:n})),t){const g=document.createElement("code");g.className="lia-run-trigger__job-id",g.textContent=t,$.appendChild(g)}return d.appendChild($),d.addEventListener("submit",g=>{if(g.preventDefault(),s)return;const P=new FormData(d),m=P.get("supabase_target")||"wip",u=String(P.get("suin_scope")||"").trim(),l=P.get("skip_embeddings")!=null,r=P.get("auto_promote")!=null;a({suinScope:u,supabaseTarget:m==="production"?"production":"wip",autoEmbed:!l,autoPromote:r})}),o.appendChild(d),o}function Rs(e){const t=document.createElement("fieldset");t.className="lia-run-trigger__field lia-run-trigger__field--radio";const n=document.createElement("legend");return n.className="lia-run-trigger__legend",n.textContent=e.legend,t.appendChild(n),e.options.forEach(s=>{const a=document.createElement("label");a.className="lia-run-trigger__radio-row";const o=document.createElement("input");o.type="radio",o.name=e.name,o.value=s.value,s.defaultChecked&&(o.defaultChecked=!0),a.appendChild(o);const c=document.createElement("span");c.className="lia-run-trigger__radio-text";const i=document.createElement("span");if(i.className="lia-run-trigger__radio-label",i.textContent=s.label,c.appendChild(i),s.hint){const p=document.createElement("span");p.className="lia-run-trigger__radio-hint",p.textContent=s.hint,c.appendChild(p)}a.appendChild(c),t.appendChild(a)}),t}function Ms(e){const t=document.createElement("fieldset");t.className="lia-run-trigger__field lia-run-trigger__field--checkbox";const n=document.createElement("legend");return n.className="lia-run-trigger__legend",n.textContent="Opciones de corrida",t.appendChild(n),e.forEach(s=>{const a=document.createElement("label");a.className="lia-run-trigger__checkbox-row";const o=document.createElement("input");o.type="checkbox",o.name=s.name,s.defaultChecked&&(o.defaultChecked=!0),a.appendChild(o);const c=document.createElement("span");c.className="lia-run-trigger__checkbox-text";const i=document.createElement("span");if(i.className="lia-run-trigger__checkbox-label",i.textContent=s.label,c.appendChild(i),s.hint){const p=document.createElement("span");p.className="lia-run-trigger__checkbox-hint",p.textContent=s.hint,c.appendChild(p)}a.appendChild(c),t.appendChild(a)}),t}function qs(e){const t=document.createElement("div");t.className="lia-run-trigger__field lia-run-trigger__field--text";const n=document.createElement("label");n.className="lia-run-trigger__label",n.htmlFor=`lia-run-trigger-${e.name}`,n.textContent=e.label,t.appendChild(n);const s=document.createElement("input");if(s.type="text",s.id=`lia-run-trigger-${e.name}`,s.name=e.name,s.className="lia-input lia-run-trigger__input",s.autocomplete="off",s.spellcheck=!1,e.placeholder&&(s.placeholder=e.placeholder),t.appendChild(s),e.hint){const a=document.createElement("p");a.className="lia-run-trigger__hint",a.textContent=e.hint,t.appendChild(a)}return t}const jt=["B","KB","MB","GB","TB"];function zt(e){if(!Number.isFinite(e)||e<=0)return"0 B";let t=0,n=e;for(;n>=1024&&t<jt.length-1;)n/=1024,t+=1;const s=t===0?Math.round(n):Math.round(n*10)/10;return`${Number.isInteger(s)?`${s}`:s.toFixed(1)} ${jt[t]}`}function Os(e){const t=e.toLowerCase();return t.endsWith(".pdf")?"📕":t.endsWith(".docx")||t.endsWith(".doc")?"📘":t.endsWith(".md")?"📄":t.endsWith(".txt")?"📃":"📄"}function Fs(e){const{filename:t,bytes:n,onRemove:s,className:a=""}=e,o=document.createElement("span");o.className=["lia-file-chip",a].filter(Boolean).join(" "),o.setAttribute("data-lia-component","file-chip"),o.title=`${t} - ${zt(n)}`;const c=document.createElement("span");c.className="lia-file-chip__icon",c.setAttribute("aria-hidden","true"),c.textContent=Os(t),o.appendChild(c);const i=document.createElement("span");i.className="lia-file-chip__name",i.textContent=t,o.appendChild(i);const p=document.createElement("span");if(p.className="lia-file-chip__size",p.textContent=zt(n),o.appendChild(p),s){const d=document.createElement("button");d.type="button",d.className="lia-file-chip__remove",d.setAttribute("aria-label",`Quitar ${t}`),d.textContent="x",d.addEventListener("click",y=>{y.preventDefault(),y.stopPropagation(),s()}),o.appendChild(d)}return o}function Ut(e){const{subtopicKey:t,label:n,confidence:s,requiresReview:a,isNew:o,className:c=""}=e;let i="brand";a?i="warning":o&&(i="info");const p=n&&n.trim()?n:t,d=s!=null&&!Number.isNaN(s)?`${p} · ${Math.round(s<=1?s*100:s)}%`:p,y=dt({label:d,tone:i,emphasis:"soft",className:["lia-subtopic-chip",c].filter(Boolean).join(" "),dataComponent:"subtopic-chip"});return y.setAttribute("data-subtopic-key",t),a&&y.setAttribute("data-subtopic-review","true"),o&&y.setAttribute("data-subtopic-new","true"),y}function Ds(e){if(e==null||Number.isNaN(e))return"-";const t=e<=1?e*100:e;return`${Math.round(t)}%`}function Bs(e){if(e==null||Number.isNaN(e))return"neutral";const t=e<=1?e*100:e;return t>=80?"success":t>=50?"warning":"error"}function js(e){const{filename:t,bytes:n,detectedTopic:s,topicLabel:a,combinedConfidence:o,requiresReview:c,coercionMethod:i,subtopicKey:p,subtopicLabel:d,subtopicConfidence:y,subtopicIsNew:E,requiresSubtopicReview:h,onRemove:$,className:N=""}=e,g=document.createElement("div");g.className=["lia-intake-file-row",N].filter(Boolean).join(" "),g.setAttribute("data-lia-component","intake-file-row");const P=document.createElement("span");P.className="lia-intake-file-row__file",P.appendChild(Fs({filename:t,bytes:n,onRemove:$})),g.appendChild(P);const m=document.createElement("span");if(m.className="lia-intake-file-row__meta",a||s){const u=$n({label:a||s||"sin tópico",tone:"info",emphasis:"soft",className:"lia-intake-file-row__topic"});s&&u.setAttribute("data-topic",s),m.appendChild(u)}if(o!=null){const u=dt({label:Ds(o),tone:Bs(o),emphasis:"soft",className:"lia-intake-file-row__confidence"});m.appendChild(u)}if(c){const u=dt({label:"requiere revisión",tone:"warning",emphasis:"solid",className:"lia-intake-file-row__review"});u.setAttribute("role","status"),m.appendChild(u)}if(p?m.appendChild(Ut({subtopicKey:p,label:d||null,confidence:y??null,isNew:E,requiresReview:h,className:"lia-intake-file-row__subtopic"})):E&&e.subtopicKey!==void 0&&m.appendChild(Ut({subtopicKey:"(nuevo)",label:d||"subtema propuesto",isNew:!0,className:"lia-intake-file-row__subtopic"})),h&&!p){const u=dt({label:"subtema pendiente",tone:"warning",emphasis:"soft",className:"lia-intake-file-row__subtopic-review"});u.setAttribute("data-subtopic-review","true"),m.appendChild(u)}if(i){const u=document.createElement("span");u.className="lia-intake-file-row__coercion",u.textContent=i,m.appendChild(u)}return g.appendChild(m),g}const zs=[".md",".txt",".json",".pdf",".docx"];function Us(e){const t=e.toLowerCase();return zs.some(n=>t.endsWith(n))}function Hs(e){return e.split("/").filter(Boolean).some(n=>n.startsWith("."))}function Ws(e){return e.includes("__MACOSX/")||e.startsWith("__MACOSX/")}function Gs(e,t){return!(!e||Ws(t)||Hs(t)||e.startsWith(".")||!Us(e))}async function Js(e){const t=[];for(;;){const n=await new Promise(s=>{e.readEntries(a=>s(a||[]))});if(n.length===0)break;t.push(...n)}return t}async function dn(e,t){if(!e)return[];const n=t?`${t}/${e.name}`:e.name;if(e.isFile){if(!e.file)return[];const s=await new Promise(a=>e.file(a));return[{filename:s.name,bytes:s.size,mime:s.type||void 0,relativePath:n,file:s}]}if(e.isDirectory&&e.createReader){const s=e.createReader(),a=await Js(s);return(await Promise.all(a.map(c=>dn(c,n)))).flat()}return[]}async function Ks(e){const t=e.items?Array.from(e.items):[];if(t.length>0&&typeof t[0].webkitGetAsEntry=="function"){const s=[];for(const a of t){const o=a.webkitGetAsEntry();if(!o)continue;const c=await dn(o,"");s.push(...c)}return s}return(e.files?Array.from(e.files):[]).map(s=>({filename:s.name,bytes:s.size,mime:s.type||void 0,relativePath:s.name,file:s}))}function Vs(e,t){return t?{filename:t.filename||e.filename,mime:t.mime||e.mime,bytes:t.bytes??e.bytes,detectedTopic:t.detected_topic??null,topicLabel:t.topic_label??null,combinedConfidence:t.combined_confidence??null,requiresReview:!!t.requires_review,coercionMethod:t.coercion_method??null,subtopicKey:t.subtopic_key??null,subtopicLabel:t.subtopic_label??null,subtopicConfidence:t.subtopic_confidence??null,subtopicIsNew:!!t.subtopic_is_new,requiresSubtopicReview:!!t.requires_subtopic_review}:{filename:e.filename,mime:e.mime,bytes:e.bytes,detectedTopic:null,topicLabel:null,combinedConfidence:null,requiresReview:!1,coercionMethod:null}}function Xs(e){const{onIntake:t,onApprove:n}=e,s=document.createElement("section");s.className="lia-intake-drop-zone",s.setAttribute("data-lia-component","intake-drop-zone");const a=document.createElement("header");a.className="lia-intake-drop-zone__header";const o=document.createElement("h2");o.className="lia-intake-drop-zone__title",o.textContent="Arrastra archivos o carpetas",a.appendChild(o);const c=document.createElement("p");c.className="lia-intake-drop-zone__hint",c.textContent="Acepta .md, .txt, .json, .pdf, .docx. Carpetas se recorren recursivamente. Ocultos y __MACOSX/ se descartan.",a.appendChild(c),s.appendChild(a);const i=document.createElement("div");i.className="lia-intake-drop-zone__zone",i.setAttribute("role","button"),i.setAttribute("tabindex","0"),i.setAttribute("aria-label","Zona de arrastre para ingesta");const p=document.createElement("p");p.className="lia-intake-drop-zone__zone-label",p.textContent="Suelta aquí los archivos para enviarlos al intake",i.appendChild(p),s.appendChild(i);const d=document.createElement("div");d.className="lia-intake-drop-zone__list",d.setAttribute("data-role","intake-file-list"),s.appendChild(d);const y=document.createElement("p");y.className="lia-intake-drop-zone__feedback",y.setAttribute("role","status"),s.appendChild(y);const E=document.createElement("div");E.className="lia-intake-drop-zone__actions";const h=document.createElement("button");h.type="button",h.className="lia-button lia-button--primary lia-intake-drop-zone__approve",h.textContent="Aprobar e ingerir",h.disabled=!0,E.appendChild(h),s.appendChild(E);const $={queued:[],lastResponse:null};function N(){var u;if(d.replaceChildren(),$.queued.length===0){const l=document.createElement("p");l.className="lia-intake-drop-zone__empty",l.textContent="Sin archivos en cola.",d.appendChild(l);return}const m=new Map;if((u=$.lastResponse)!=null&&u.files)for(const l of $.lastResponse.files)l.filename&&m.set(l.filename,l);$.queued.forEach((l,r)=>{const f=m.get(l.filename),v=js({...Vs(l,f),onRemove:()=>{$.queued.splice(r,1),N(),g()}});d.appendChild(v)})}function g(){var u,l;const m=((l=(u=$.lastResponse)==null?void 0:u.summary)==null?void 0:l.placed)??0;h.disabled=m<=0}async function P(m){const u=m.filter(l=>Gs(l.filename,l.relativePath));if(u.length===0){y.textContent="Ningún archivo elegible en el drop.";return}$.queued=u,$.lastResponse=null,N(),g(),y.textContent=`Enviando ${u.length} archivo(s) al intake…`;try{const l=await t(u);$.lastResponse=l,N(),g(),y.textContent=`Intake ok — placed ${l.summary.placed} / deduped ${l.summary.deduped} / rejected ${l.summary.rejected}.`}catch(l){$.lastResponse=null,g();const r=l instanceof Error?l.message:"intake falló";y.textContent=`Intake falló: ${r}`}}return i.addEventListener("dragenter",m=>{m.preventDefault(),i.classList.add("lia-intake-drop-zone__zone--active")}),i.addEventListener("dragover",m=>{m.preventDefault(),i.classList.add("lia-intake-drop-zone__zone--active")}),i.addEventListener("dragleave",m=>{m.preventDefault(),i.classList.remove("lia-intake-drop-zone__zone--active")}),i.addEventListener("drop",m=>{m.preventDefault(),i.classList.remove("lia-intake-drop-zone__zone--active");const u=m.dataTransfer;u&&(async()=>{const l=await Ks(u);await P(l)})()}),h.addEventListener("click",()=>{var u;if(h.disabled)return;const m=(u=$.lastResponse)==null?void 0:u.batch_id;m&&n&&n(m)}),N(),g(),s}function Zs(e){const{status:t,ariaLabel:n,className:s=""}=e,a=document.createElement("span"),o=["lia-progress-dot",`lia-progress-dot--${t}`,t==="running"?"lia-progress-dot--pulse":"",s].filter(Boolean);return a.className=o.join(" "),a.setAttribute("data-lia-component","progress-dot"),a.setAttribute("role","status"),a.setAttribute("data-status",t),n&&a.setAttribute("aria-label",n),a}const Ys=["docs","chunks","edges","embeddings_generated"];function Qs(e){if(!e)return"";const t=[];for(const n of Ys)if(e[n]!=null&&t.push(`${n}: ${e[n]}`),t.length>=3)break;return t.join(", ")}function Ht(e){if(e==null)return null;if(typeof e=="number")return Number.isFinite(e)?e:null;const t=Date.parse(e);return Number.isFinite(t)?t:null}function ea(e,t){const n=Ht(e),s=Ht(t);if(n==null||s==null||s<n)return"";const a=Math.round((s-n)/1e3);if(a<60)return`${a}s`;const o=Math.floor(a/60),c=a%60;return c?`${o}m ${c}s`:`${o}m`}function Wt(e){const{name:t,label:n,status:s,counts:a,startedAt:o,finishedAt:c,errorMessage:i,className:p=""}=e,d=document.createElement("div");d.className=["lia-stage-progress-item",`lia-stage-progress-item--${s}`,p].filter(Boolean).join(" "),d.setAttribute("data-lia-component","stage-progress-item"),d.setAttribute("data-stage-name",t),d.appendChild(Zs({status:s,ariaLabel:n}));const y=document.createElement("span");y.className="lia-stage-progress-item__label",y.textContent=n,d.appendChild(y);const E=Qs(a);if(E){const $=document.createElement("span");$.className="lia-stage-progress-item__counts",$.textContent=E,d.appendChild($)}const h=ea(o,c);if(h){const $=document.createElement("span");$.className="lia-stage-progress-item__duration",$.textContent=h,d.appendChild($)}if(s==="failed"&&i){const $=document.createElement("p");$.className="lia-stage-progress-item__error",$.textContent=i,$.setAttribute("role","alert"),d.appendChild($)}return d}const Gt=[{name:"coerce",label:"Coerce"},{name:"audit",label:"Audit"},{name:"chunk",label:"Chunk"},{name:"sink",label:"Sink"},{name:"falkor",label:"FalkorDB"},{name:"embeddings",label:"Embeddings"}];function ta(e){return e==="running"||e==="done"||e==="failed"||e==="pending"?e:"pending"}function Jt(e,t,n){return{name:e,label:t,status:ta(n==null?void 0:n.status),counts:(n==null?void 0:n.counts)??null,startedAt:(n==null?void 0:n.started_at)??null,finishedAt:(n==null?void 0:n.finished_at)??null,errorMessage:(n==null?void 0:n.error)??null}}function na(){const e=document.createElement("section");e.className="lia-run-progress-timeline",e.setAttribute("data-lia-component","run-progress-timeline");const t=document.createElement("header");t.className="lia-run-progress-timeline__header";const n=document.createElement("h3");n.className="lia-run-progress-timeline__title",n.textContent="Progreso de la corrida",t.appendChild(n),e.appendChild(t);const s=document.createElement("div");s.className="lia-run-progress-timeline__list";const a=new Map;Gt.forEach(({name:c,label:i})=>{const p=document.createElement("div");p.className="lia-run-progress-timeline__item",p.setAttribute("data-stage",c),p.appendChild(Wt(Jt(c,i,void 0))),s.appendChild(p),a.set(c,p)}),e.appendChild(s);function o(c){const i=(c==null?void 0:c.stages)||{};Gt.forEach(({name:p,label:d})=>{const y=a.get(p);if(!y)return;const E=i[p]||void 0;y.replaceChildren(Wt(Jt(p,d,E)))})}return{element:e,update:o}}function sa(e={}){const{initialLines:t=[],autoScroll:n=!0,onCopy:s=null,summaryLabel:a="Log de ejecución",className:o=""}=e,c=document.createElement("div");c.className=["lia-log-tail-viewer",o].filter(Boolean).join(" "),c.setAttribute("data-lia-component","log-tail-viewer");const i=document.createElement("div");i.className="lia-log-tail-viewer__toolbar";const p=document.createElement("button");p.type="button",p.className="lia-log-tail-viewer__copy",p.textContent="Copiar",p.setAttribute("aria-label","Copiar log"),i.appendChild(p);const d=document.createElement("details");d.className="lia-log-tail-viewer__details",d.open=!0;const y=document.createElement("summary");y.className="lia-log-tail-viewer__summary",y.textContent=a,d.appendChild(y);const E=document.createElement("pre");E.className="lia-log-tail-viewer__body",E.textContent=t.join(`
`),d.appendChild(E),c.appendChild(i),c.appendChild(d);const h={lines:[...t]},$=()=>{n&&(E.scrollTop=E.scrollHeight)},N=()=>{E.textContent=h.lines.join(`
`),$()},g=m=>{!m||m.length===0||(h.lines.push(...m),N())},P=()=>{h.lines=[],E.textContent=""};return p.addEventListener("click",()=>{var l;const m=h.lines.join(`
`),u=(l=globalThis.navigator)==null?void 0:l.clipboard;u&&typeof u.writeText=="function"&&u.writeText(m),s&&s()}),n&&$(),{element:c,appendLines:g,clear:P}}function aa(e={}){const{initialLines:t=[],onCopy:n=null,summaryLabel:s="Log de ejecución"}=e,a=document.createElement("section");a.className="lia-run-log-console",a.setAttribute("data-lia-component","run-log-console");const o=document.createElement("header");o.className="lia-run-log-console__header";const c=document.createElement("h3");c.className="lia-run-log-console__title",c.textContent="Log en vivo",o.appendChild(c);const i=document.createElement("p");i.className="lia-run-log-console__subtitle",i.textContent="Streaming del archivo artifacts/jobs/<job>.log — se actualiza cada 1.5s.",o.appendChild(i),a.appendChild(o);const p=sa({initialLines:t,autoScroll:!0,onCopy:n,summaryLabel:s,className:"lia-run-log-console__viewer"});return a.appendChild(p.element),{element:a,appendLines:p.appendLines,clear:p.clear}}async function Kt(e,t){const{response:n,data:s}=await Ge(e,t);if(!n.ok){const a=s&&typeof s=="object"&&"error"in s?String(s.error||n.statusText):n.statusText;throw new et(a,n.status,s)}if(!s)throw new et("Empty response",n.status,null);return s}function oa(e){const t=e.querySelector("[data-slot=corpus-overview]"),n=e.querySelector("[data-slot=run-trigger]"),s=e.querySelector("[data-slot=generations-list]"),a=e.querySelector("[data-slot=intake-zone]"),o=e.querySelector("[data-slot=progress-timeline]"),c=e.querySelector("[data-slot=log-console]");if(!t||!n||!s)return e.textContent="Sesiones: missing render slots.",{refresh:async()=>{},destroy:()=>{}};const i={activeJobId:null,lastRunStatus:null,pollHandle:null,logCursor:0,lastBatchId:null,autoEmbed:!0,autoPromote:!1,supabaseTarget:"wip",suinScope:""};let p=null,d=null;function y(){n.replaceChildren(Ls({activeJobId:i.activeJobId,lastRunStatus:i.lastRunStatus,disabled:i.activeJobId!==null,onTrigger:({suinScope:w,supabaseTarget:_,autoEmbed:b,autoPromote:D})=>{i.autoEmbed=b,i.autoPromote=D,i.supabaseTarget=_,i.suinScope=w,l({suinScope:w,supabaseTarget:_,autoEmbed:b,autoPromote:D,batchId:null})}}))}function E(){a&&a.replaceChildren(Xs({onIntake:w=>P(w),onApprove:w=>{u(w,{autoEmbed:i.autoEmbed,autoPromote:i.autoPromote,supabaseTarget:i.supabaseTarget,suinScope:i.suinScope})}}))}function h(){o&&(p=na(),o.replaceChildren(p.element))}function $(){c&&(d=aa(),c.replaceChildren(d.element))}async function N(){t.replaceChildren(I("overview"));try{const w=await De("/api/ingest/state"),_={documents:w.corpus.documents,chunks:w.corpus.chunks,graphNodes:w.graph.nodes,graphEdges:w.graph.edges,graphOk:w.graph.ok,auditScanned:w.audit.scanned,auditIncluded:w.audit.include_corpus,auditExcluded:w.audit.exclude_internal,auditPendingRevisions:w.audit.pending_revisions,activeGenerationId:w.corpus.active_generation_id,activatedAt:w.corpus.activated_at};t.replaceChildren(Es(_))}catch(w){t.replaceChildren(W("No se pudo cargar el estado del corpus.",w))}}async function g(){s.replaceChildren(I("generations"));try{const _=((await De("/api/ingest/generations?limit=20")).generations||[]).map(b=>{const D=b.knowledge_class_counts||{},R=Object.entries(D).sort((fe,T)=>T[1]-fe[1])[0];return{generationId:b.generation_id,status:b.is_active?"active":"superseded",generatedAt:b.generated_at,documents:Number(b.documents)||0,chunks:Number(b.chunks)||0,topClass:R==null?void 0:R[0],topClassCount:R==null?void 0:R[1]}});s.replaceChildren(Bt({rows:_}))}catch(w){s.replaceChildren(Bt({rows:[],errorMessage:`No se pudieron cargar las generaciones: ${K(w)}`}))}}async function P(w){const b={batch_id:null,files:await Promise.all(w.map(async R=>{const fe=await m(R.file);return{filename:R.filename,content_base64:fe,relative_path:R.relativePath||R.filename}})),options:{mirror_to_dropbox:!1,dropbox_root:null}},D=await Kt("/api/ingest/intake",b);return i.lastBatchId=D.batch_id,D}async function m(w){const _=globalThis;if(typeof _.FileReader=="function"){const b=await new Promise((R,fe)=>{const T=new _.FileReader;T.onerror=()=>fe(T.error||new Error("file read failed")),T.onload=()=>R(String(T.result||"")),T.readAsDataURL(w)}),D=b.indexOf(",");return D>=0?b.slice(D+1):""}if(typeof w.arrayBuffer=="function"){const b=await w.arrayBuffer();return j(b)}return""}async function u(w,_){await l({batchId:w,autoEmbed:_.autoEmbed,autoPromote:_.autoPromote,supabaseTarget:_.supabaseTarget,suinScope:_.suinScope})}async function l(w){i.lastRunStatus="queued",i.logCursor=0,d&&d.clear(),y();try{const _=await Kt("/api/ingest/run",{suin_scope:w.suinScope,supabase_target:w.supabaseTarget,auto_embed:w.autoEmbed,auto_promote:w.autoPromote,batch_id:w.batchId});i.activeJobId=_.job_id,i.lastRunStatus="running",y(),r()}catch(_){i.lastRunStatus="failed",i.activeJobId=null,y(),q(`No se pudo iniciar la ingesta: ${K(_)}`)}}function r(){f();const w=o!==null||c!==null;i.pollHandle=window.setInterval(()=>{if(!i.activeJobId){f();return}w?(v(i.activeJobId),S(i.activeJobId)):x(i.activeJobId)},w?1500:4e3)}function f(){i.pollHandle!==null&&(window.clearInterval(i.pollHandle),i.pollHandle=null)}async function v(w){try{const _=await De(`/api/ingest/job/${w}/progress`);p&&p.update(_);const b=_.status;(b==="done"||b==="failed")&&(i.lastRunStatus=b==="done"?"active":"failed",i.activeJobId=null,y(),f(),b==="done"&&await Promise.all([N(),g()]))}catch{}}async function S(w){try{const _=await De(`/api/ingest/job/${w}/log/tail?cursor=${i.logCursor}&limit=200`);_.lines&&_.lines.length>0&&d&&d.appendLines(_.lines),typeof _.next_cursor=="number"&&(i.logCursor=_.next_cursor)}catch{}}async function x(w){var _;try{const D=(await De(`/api/jobs/${w}`)).job;if(!D)return;if(D.status==="completed"){const R=(((_=D.result_payload)==null?void 0:_.exit_code)??1)===0;i.lastRunStatus=R?"active":"failed",i.activeJobId=null,y(),f(),R&&await Promise.all([N(),g()])}else D.status==="failed"&&(i.lastRunStatus="failed",i.activeJobId=null,y(),f())}catch{}}function j(w){const _=new Uint8Array(w),b=32768;let D="";for(let T=0;T<_.length;T+=b){const ge=_.subarray(T,Math.min(_.length,T+b));D+=String.fromCharCode.apply(null,Array.from(ge))}const R=globalThis;if(typeof R.btoa=="function")return R.btoa(D);const fe=globalThis.Buffer;return fe?fe.from(D,"binary").toString("base64"):""}function I(w){const _=document.createElement("div");return _.className=`lia-ingest-skeleton lia-ingest-skeleton--${w}`,_.setAttribute("aria-hidden","true"),_.textContent="Cargando…",_}function W(w,_){const b=document.createElement("div");b.className="lia-ingest-error",b.setAttribute("role","alert");const D=document.createElement("strong");D.textContent=w,b.appendChild(D);const R=document.createElement("p");return R.className="lia-ingest-error__detail",R.textContent=K(_),b.appendChild(R),b}function K(w){return w instanceof Error?w.message:typeof w=="string"?w:"Error desconocido"}function q(w){const _=document.createElement("div");_.className="lia-ingest-toast",_.textContent=w,e.prepend(_),window.setTimeout(()=>_.remove(),4e3)}return y(),E(),h(),$(),Promise.all([N(),g()]),{async refresh(){await Promise.all([N(),g()])},destroy(){f()}}}function ia(e,{i18n:t}){const n=e,s=n.querySelector("#lia-ingest-shell");let a=null;s&&(a=oa(s),window.setInterval(()=>{a==null||a.refresh()},3e4));const o=s!==null,c=n.querySelector("#ops-tab-monitor"),i=n.querySelector("#ops-tab-ingestion"),p=n.querySelector("#ops-tab-control"),d=n.querySelector("#ops-tab-embeddings"),y=n.querySelector("#ops-tab-reindex"),E=n.querySelector("#ops-panel-monitor"),h=n.querySelector("#ops-panel-ingestion"),$=n.querySelector("#ops-panel-control"),N=n.querySelector("#ops-panel-embeddings"),g=n.querySelector("#ops-panel-reindex"),P=n.querySelector("#runs-body"),m=n.querySelector("#timeline"),u=n.querySelector("#timeline-meta"),l=n.querySelector("#cascade-note"),r=n.querySelector("#user-cascade"),f=n.querySelector("#user-cascade-summary"),v=n.querySelector("#technical-cascade"),S=n.querySelector("#technical-cascade-summary"),x=n.querySelector("#refresh-runs"),j=!!(P&&m&&u&&l&&r&&f&&v&&S&&x),I=o?null:ae(n,"#ingestion-flash"),W=cn();function K(Ke="",ct="success"){if(I){if(!Ke){I.hidden=!0,I.textContent="",I.removeAttribute("data-tone");return}I.hidden=!1,I.dataset.tone=ct,I.textContent=Ke}}const q=o?null:ae(n,"#ingestion-corpus"),w=o?null:ae(n,"#ingestion-batch-type"),_=o?null:ae(n,"#ingestion-dropzone"),b=o?null:ae(n,"#ingestion-file-input"),D=o?null:ae(n,"#ingestion-folder-input"),R=o?null:ae(n,"#ingestion-pending-files"),fe=o?null:ae(n,"#ingestion-overview"),T=o?null:ae(n,"#ingestion-refresh"),ge=o?null:ae(n,"#ingestion-create-session"),L=o?null:ae(n,"#ingestion-select-files"),M=o?null:ae(n,"#ingestion-select-folder"),te=o?null:ae(n,"#ingestion-upload-files"),V=o?null:ae(n,"#ingestion-upload-progress"),ye=o?null:ae(n,"#ingestion-process-session"),ie=o?null:ae(n,"#ingestion-auto-process"),me=o?null:ae(n,"#ingestion-validate-batch"),Ee=o?null:ae(n,"#ingestion-retry-session"),Pe=o?null:ae(n,"#ingestion-delete-session"),Ce=o?null:ae(n,"#ingestion-session-meta"),H=o?null:ae(n,"#ingestion-sessions-list"),we=o?null:ae(n,"#selected-session-meta"),le=o?null:ae(n,"#ingestion-last-error"),Ne=o?null:ae(n,"#ingestion-last-error-message"),Me=o?null:ae(n,"#ingestion-last-error-guidance"),qe=o?null:ae(n,"#ingestion-last-error-next"),be=o?null:ae(n,"#ingestion-kanban"),Ae=o?null:ae(n,"#ingestion-log-accordion"),Te=o?null:ae(n,"#ingestion-log-body"),re=o?null:ae(n,"#ingestion-log-copy"),he=o?null:ae(n,"#ingestion-auto-status"),A=n.querySelector("#ingestion-add-corpus-btn"),z=n.querySelector("#add-corpus-dialog"),ee=n.querySelector("#ingestion-bounce-log"),Y=n.querySelector("#ingestion-bounce-body"),X=n.querySelector("#ingestion-bounce-copy");async function pe(Ke){return Ke()}const ne=j?an({i18n:t,stateController:W,dom:{monitorTabBtn:c,ingestionTabBtn:i,controlTabBtn:p,embeddingsTabBtn:d,reindexTabBtn:y,monitorPanel:E,ingestionPanel:h,controlPanel:$,embeddingsPanel:N,reindexPanel:g,runsBody:P,timelineNode:m,timelineMeta:u,cascadeNote:l,userCascadeNode:r,userCascadeSummary:f,technicalCascadeNode:v,technicalCascadeSummary:S,refreshRunsBtn:x},withThinkingWheel:pe,setFlash:K}):null,oe=o?null:ys({i18n:t,stateController:W,dom:{ingestionCorpusSelect:q,ingestionBatchTypeSelect:w,ingestionDropzone:_,ingestionFileInput:b,ingestionFolderInput:D,ingestionSelectFilesBtn:L,ingestionSelectFolderBtn:M,ingestionUploadProgress:V,ingestionPendingFiles:R,ingestionOverview:fe,ingestionRefreshBtn:T,ingestionCreateSessionBtn:ge,ingestionUploadBtn:te,ingestionProcessBtn:ye,ingestionAutoProcessBtn:ie,ingestionValidateBatchBtn:me,ingestionRetryBtn:Ee,ingestionDeleteSessionBtn:Pe,ingestionSessionMeta:Ce,ingestionSessionsList:H,selectedSessionMeta:we,ingestionLastError:le,ingestionLastErrorMessage:Ne,ingestionLastErrorGuidance:Me,ingestionLastErrorNext:qe,ingestionKanban:be,ingestionLogAccordion:Ae,ingestionLogBody:Te,ingestionLogCopyBtn:re,ingestionAutoStatus:he,addCorpusBtn:A,addCorpusDialog:z,ingestionBounceLog:ee,ingestionBounceBody:Y,ingestionBounceCopy:X},withThinkingWheel:pe,setFlash:K}),G=n.querySelector("#corpus-lifecycle"),Z=G?Vt({dom:{container:G},setFlash:K}):null,ke=n.querySelector("#embeddings-lifecycle"),Le=ke?en({dom:{container:ke},setFlash:K}):null,Ie=n.querySelector("#reindex-lifecycle"),Je=Ie?on({dom:{container:Ie},setFlash:K,navigateToEmbeddings:()=>{W.setActiveTab("embeddings"),ne==null||ne.renderTabs()}}):null;ne==null||ne.bindEvents(),oe==null||oe.bindEvents(),Z==null||Z.bindEvents(),Le==null||Le.bindEvents(),Je==null||Je.bindEvents(),ne==null||ne.renderTabs(),oe==null||oe.render(),rn({stateController:W,withThinkingWheel:pe,setFlash:K,refreshRuns:(ne==null?void 0:ne.refreshRuns)??(async()=>{}),refreshIngestion:(oe==null?void 0:oe.refreshIngestion)??(async()=>{}),refreshCorpusLifecycle:Z==null?void 0:Z.refresh,refreshEmbeddings:Le==null?void 0:Le.refresh,refreshReindex:Je==null?void 0:Je.refresh})}function ra(e,{i18n:t}){const n=e,s=n.querySelector("#runs-body"),a=n.querySelector("#timeline"),o=n.querySelector("#timeline-meta"),c=n.querySelector("#cascade-note"),i=n.querySelector("#user-cascade"),p=n.querySelector("#user-cascade-summary"),d=n.querySelector("#technical-cascade"),y=n.querySelector("#technical-cascade-summary"),E=n.querySelector("#refresh-runs");if(!s||!a||!o||!c||!i||!p||!d||!y||!E)return;const h=cn(),$=async P=>P(),N=()=>{},g=an({i18n:t,stateController:h,dom:{monitorTabBtn:null,ingestionTabBtn:null,controlTabBtn:null,embeddingsTabBtn:null,reindexTabBtn:null,monitorPanel:null,ingestionPanel:null,controlPanel:null,embeddingsPanel:null,reindexPanel:null,runsBody:s,timelineNode:a,timelineMeta:o,cascadeNote:c,userCascadeNode:i,userCascadeSummary:p,technicalCascadeNode:d,technicalCascadeSummary:y,refreshRunsBtn:E},withThinkingWheel:$,setFlash:N});g.bindEvents(),g.renderTabs(),rn({stateController:h,withThinkingWheel:$,setFlash:N,refreshRuns:g.refreshRuns,refreshIngestion:async()=>{}})}const $a=Object.freeze(Object.defineProperty({__proto__:null,mountBackstageApp:ra,mountOpsApp:ia},Symbol.toStringTag,{value:"Module"}));export{ia as a,Pn as b,_a as c,ya as d,$a as e,ra as m,va as o,Cn as r,ha as s};
