import{q as ee}from"./bootstrap-DAARwiGO.js";import{g as Pe,p as je,A as st}from"./client-OE0sHIIg.js";import{p as Ot}from"./colors-ps0hVFT8.js";import{g as _t}from"./index-BAf9D_ld.js";import{getToastController as Nn}from"./toasts-Dx3CUztl.js";import{c as Pn}from"./badge-UV61UhzD.js";import{c as bt}from"./chip-Bjq03GaS.js";function In(){return`
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
  `}function An(e){return`
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
  `}function Ln(e){return`
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
  `}function Tn(e){return`
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
        ${In()}
      </div>

      <div id="ingestion-section-promocion" class="ingestion-section" role="tabpanel" hidden></div>

      <div id="ingestion-section-subtopics" class="ingestion-section" role="tabpanel" hidden></div>
    </div>
  `}function Rn(){return`
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
  `}function Mn(e){return`
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
      ${An()}
    </main>
  `}const ha=Object.freeze(Object.defineProperty({__proto__:null,renderBackstageShell:Ln,renderIngestionShell:Tn,renderOpsShell:Mn,renderPromocionShell:Rn},Symbol.toStringTag,{value:"Module"})),qn=2e3;function z(e){return String(e??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#39;")}function ae(e){return(e??0).toLocaleString("es-CO")}function On(e){if(!e)return"-";try{return new Date(e).toLocaleDateString("es-CO",{day:"numeric",month:"short",hour:"2-digit",minute:"2-digit",timeZone:"America/Bogota"})}catch{return e}}function Dt(e){if(!e)return"-";const t=Date.parse(e);if(Number.isNaN(t))return e;const n=Math.max(0,Math.floor((Date.now()-t)/1e3));if(n<5)return"ahora";if(n<60)return`hace ${n}s`;const a=Math.floor(n/60),s=n%60;return a<60?`hace ${a}m ${s}s`:`hace ${Math.floor(a/60)}h ${a%60}m`}function Te(e){return e?e.length>24?`${e.slice(0,15)}…${e.slice(-8)}`:e:"-"}function Dn(e){return e===void 0?'<span class="ops-dot ops-dot-unknown">●</span>':e?'<span class="ops-dot ops-dot-ok">●</span>':'<span class="ops-dot ops-dot-error">●</span>'}function Bt(e,t){if(!t.available)return`
      <div class="corpus-card corpus-card-unavailable">
        <h4 class="corpus-card-title">${z(e)}</h4>
        <p class="corpus-card-unavail">● no disponible</p>
        ${t.error?`<p class="ops-subcopy">${z(t.error)}</p>`:""}
      </div>`;const n=t.knowledge_class_counts??{};return`
    <div class="corpus-card">
      <h4 class="corpus-card-title">${z(e)}</h4>
      <div class="corpus-card-row"><span>Gen:</span> <code>${z(Te(t.generation_id))}</code></div>
      <div class="corpus-card-row"><span>Documentos:</span> <strong>${ae(t.documents)}</strong></div>
      <div class="corpus-card-row"><span>Chunks:</span> <strong>${ae(t.chunks)}</strong></div>
      <div class="corpus-card-row"><span>Embeddings:</span> ${Dn(t.embeddings_complete)} ${t.embeddings_complete?"completos":"incompletos"}</div>
      <div class="corpus-card-sep"></div>
      <div class="corpus-card-row corpus-card-row-sm"><span>normative_base:</span> ${ae(n.normative_base)}</div>
      <div class="corpus-card-row corpus-card-row-sm"><span>interpretative:</span> ${ae(n.interpretative_guidance)}</div>
      <div class="corpus-card-row corpus-card-row-sm"><span>practica_erp:</span> ${ae(n.practica_erp)}</div>
      <div class="corpus-card-sep"></div>
      <div class="corpus-card-row corpus-card-row-sm"><span>${e==="PRODUCTION"?"Activado:":"Actualizado:"}</span> ${z(On(t.activated_at))}</div>
    </div>`}function jt(e,t={}){const{onlyFailures:n=!1}=t,a=(e??[]).filter(s=>n?!s.ok:!0);return a.length===0?"":`
    <ul class="corpus-checks">
      ${a.map(s=>`
            <li class="corpus-check ${s.ok?"is-ok":"is-fail"}">
              <span class="corpus-check-dot"></span>
              <div>
                <strong>${z(s.label)}</strong>
                <span>${z(s.detail)}</span>
              </div>
            </li>`).join("")}
    </ul>`}function Bn(e){const t=e??[];return t.length===0?"":`
    <ol class="corpus-stage-list">
      ${t.map(n=>`
            <li class="corpus-stage-item state-${z(n.state)}">
              <span class="corpus-stage-dot"></span>
              <span>${z(n.label)}</span>
            </li>`).join("")}
    </ol>`}function ft(e){const t=String(e||"").trim();return t?t.replaceAll("_"," "):"-"}function jn(e){return e?e.kind==="audit"?"Audit":e.kind==="rollback"?"Rollback":e.mode==="force_reset"?"Force reset":"Promote":"Promote"}function kt(e){const t=e==null?void 0:e.last_checkpoint;if(!(t!=null&&t.phase))return"-";const n=t.cursor??0,a=t.total??0,s=a>0?(n/a*100).toFixed(1):"0";return`${ft(t.phase)} · ${ae(n)} / ${ae(a)} (${s}%)`}function Ft(e){var a,s;const t=((a=e==null?void 0:e.last_checkpoint)==null?void 0:a.cursor)??(e==null?void 0:e.batch_cursor)??0,n=((s=e==null?void 0:e.last_checkpoint)==null?void 0:s.total)??0;return n<=0?0:Math.min(100,Math.max(0,t/n*100))}function Fn(e){if(!(e!=null&&e.heartbeat_at))return{label:"-",className:""};const t=Math.max(0,(Date.now()-Date.parse(e.heartbeat_at))/1e3);return t<15?{label:"Saludable",className:"hb-healthy"}:t<45?{label:"Lento",className:"hb-slow"}:{label:"Sin respuesta",className:"hb-stale"}}function zn(e,t){var n,a,s,o,u,c;if(e)switch(e.operation_state_code){case"orphaned_queue":return{severity:"red",title:"Orphaned before start",detail:"The request was queued, but the backend worker never started."};case"stalled_resumable":return{severity:"red",title:"Stalled",detail:(n=e.last_checkpoint)!=null&&n.phase?`Backend stalled after ${ft(e.last_checkpoint.phase)}. Resume is available.`:"Backend stalled, but a checkpoint is available to resume."};case"failed_resumable":return{severity:"red",title:"Resumable",detail:e.error||((s=(a=e.failures)==null?void 0:a[0])==null?void 0:s.message)||"The last run failed after writing a checkpoint. Resume is available."};case"completed":return{severity:"green",title:"Completed",detail:e.kind==="audit"?"WIP audit completed. Artifact written.":e.kind==="rollback"?"Rollback completed and verified.":"Promotion completed and verified."};case"running":return{severity:"yellow",title:"Running",detail:e.current_phase?`Backend phase: ${ft(e.current_phase)}.`:e.stage_label?`Stage: ${e.stage_label}.`:"The backend is processing the promotion."};default:return{severity:e.severity??"red",title:e.severity==="yellow"?"Running":"Failed",detail:e.error||((u=(o=e.failures)==null?void 0:o[0])==null?void 0:u.message)||"The operation ended with an error."}}return t!=null&&t.preflight_ready?{severity:"green",title:"Ready",detail:"WIP audit and promotion preflight are green."}:{severity:"red",title:"Blocked",detail:((c=t==null?void 0:t.preflight_reasons)==null?void 0:c[0])||"Production is not ready for a safe promotion."}}function Hn(e){return e?e.kind==="audit"?"WIP Health Audit":e.kind==="rollback"?"Rollback Production":e.mode==="force_reset"?"Force Reset + Promote Production":"Promote WIP to Production":"Promote WIP to Production"}function zt(e,t){return!t||t.available===!1?`<tr><td>${z(e)}</td><td colspan="2" class="corpus-report-unavail">no disponible</td></tr>`:`
    <tr>
      <td>${z(e)}</td>
      <td><code>${z(Te(t.generation_id))}</code></td>
      <td>${ae(t.documents)} docs · ${ae(t.chunks)} chunks</td>
    </tr>`}function Ht(e,t){const n=new Set;for(const s of Object.keys((e==null?void 0:e.knowledge_class_counts)??{}))n.add(s);for(const s of Object.keys((t==null?void 0:t.knowledge_class_counts)??{}))n.add(s);return n.size===0?"":[...n].sort().map(s=>{const o=((e==null?void 0:e.knowledge_class_counts)??{})[s]??0,u=((t==null?void 0:t.knowledge_class_counts)??{})[s]??0,c=u-o,b=c>0?"is-positive":c<0?"is-negative":"",h=c>0?`+${ae(c)}`:c<0?ae(c):"—";return`
        <tr class="corpus-report-kc-row">
          <td>${z(s)}</td>
          <td>${ae(o)}</td>
          <td>${ae(u)}</td>
          <td class="corpus-report-delta ${b}">${h}</td>
        </tr>`}).join("")}function Un(e,t){if(!e||!t)return"-";const n=Date.parse(e),a=Date.parse(t);if(Number.isNaN(n)||Number.isNaN(a))return"-";const s=Math.max(0,Math.floor((a-n)/1e3)),o=Math.floor(s/60),u=s%60;return o===0?`${u}s`:`${o}m ${u}s`}function Wn(e){const t=e==null?void 0:e.promotion_summary;if(!t)return"";const{before:n,after:a,delta:s,plan_result:o}=t,u=((s==null?void 0:s.documents)??0)>0?`+${ae(s==null?void 0:s.documents)}`:ae(s==null?void 0:s.documents),c=((s==null?void 0:s.chunks)??0)>0?`+${ae(s==null?void 0:s.chunks)}`:ae(s==null?void 0:s.chunks),b=((s==null?void 0:s.documents)??0)>0?"is-positive":((s==null?void 0:s.documents)??0)<0?"is-negative":"",h=((s==null?void 0:s.chunks)??0)>0?"is-positive":((s==null?void 0:s.chunks)??0)<0?"is-negative":"",E=n||a?`
      <table class="corpus-report-table">
        <thead>
          <tr><th></th><th>Generación</th><th>Documentos / Chunks</th></tr>
        </thead>
        <tbody>
          ${zt("Antes",n)}
          ${zt("Después",a)}
        </tbody>
        ${s?`
        <tfoot>
          <tr>
            <td>Delta</td>
            <td></td>
            <td>
              <span class="corpus-report-delta ${b}">${u} docs</span> ·
              <span class="corpus-report-delta ${h}">${c} chunks</span>
            </td>
          </tr>
        </tfoot>`:""}
      </table>
      ${Ht(n,a)?`
      <table class="corpus-report-table corpus-report-table-kc">
        <thead><tr><th>Clase</th><th>Antes</th><th>Después</th><th>Delta</th></tr></thead>
        <tbody>${Ht(n,a)}</tbody>
      </table>`:""}`:"",$=o?`
      <div class="corpus-report-grid">
        ${[{label:"Docs staged",key:"docs_staged"},{label:"Docs upserted",key:"docs_upserted"},{label:"Docs new",key:"docs_new"},{label:"Docs removed",key:"docs_removed"},{label:"Chunks new",key:"chunks_new"},{label:"Chunks changed",key:"chunks_changed"},{label:"Chunks removed",key:"chunks_removed"},{label:"Chunks unchanged",key:"chunks_unchanged"},{label:"Chunks embedded",key:"chunks_embedded"}].filter(q=>o[q.key]!==void 0&&o[q.key]!==null).map(q=>`
              <div class="corpus-report-stat">
                <span class="corpus-report-stat-value">${z(String(o[q.key]??"-"))}</span>
                <span class="corpus-report-stat-label">${z(q.label)}</span>
              </div>`).join("")}
      </div>`:"",N=Un(e==null?void 0:e.started_at,e==null?void 0:e.completed_at);return`
    <div class="corpus-section corpus-report-section">
      <h4>Promotion Report</h4>
      ${E}
      ${$}
      ${N!=="-"?`<p class="corpus-report-duration">Duración: <strong>${z(N)}</strong></p>`:""}
    </div>`}function an({dom:e,setFlash:t}){let n=null,a=null,s=null,o="",u="",c=null,b=null,h=!1,E=!1,R=!1,$=!1,N=0,q=null,P=0;function H(F,C){a&&clearTimeout(a),t(F,C);const y=e.container.querySelector(".corpus-toast");y&&(y.hidden=!1,y.dataset.tone=C,y.textContent=F,y.classList.remove("corpus-toast-enter"),y.offsetWidth,y.classList.add("corpus-toast-enter")),a=setTimeout(()=>{const f=e.container.querySelector(".corpus-toast");f&&(f.hidden=!0)},6e3)}function w(F,C,y,f="promote"){return new Promise(j=>{b==null||b.remove();const L=document.createElement("div");L.className="corpus-confirm-overlay",b=L,L.innerHTML=`
        <div class="corpus-confirm-dialog">
          <h3 class="corpus-confirm-title">${z(F)}</h3>
          <div class="corpus-confirm-body">${C}</div>
          <div class="corpus-confirm-actions">
            <button class="corpus-btn corpus-btn-rollback" data-action="cancel">Cancelar</button>
            <button class="corpus-btn ${f==="rollback"?"corpus-btn-rollback":"corpus-btn-promote"}" data-action="confirm">${z(y)}</button>
          </div>
        </div>
      `,document.body.appendChild(L),requestAnimationFrame(()=>L.classList.add("is-visible"));function _(X){b===L&&(b=null),L.classList.remove("is-visible"),setTimeout(()=>L.remove(),180),j(X)}L.addEventListener("click",X=>{const be=X.target.closest("[data-action]");be?_(be.dataset.action==="confirm"):X.target===L&&_(!1)})})}async function S(F,C,y,f){if(!o){o=y,D();try{const{response:j,data:L}=await je(F,C);j.ok&&(L!=null&&L.job_id)?(c={tone:"success",message:`${f} Job ${Te(L.job_id)}.`},H(`${f} Job ${Te(L.job_id)}.`,"success")):(c={tone:"error",message:(L==null?void 0:L.error)||"No se pudo iniciar la operación."},H((L==null?void 0:L.error)||"No se pudo iniciar la operación.","error"))}catch(j){const L=j instanceof Error?j.message:String(j);c={tone:"error",message:L},H(L,"error")}finally{o="",await ie()}}}async function v(){const F=n;if(!F||o||!await w("Promote WIP to Production",`<p>This path reuses the live WIP generation and promotes it incrementally into Production with persisted checkpoints.</p>
       <table class="corpus-confirm-table">
         <tr><td>Production current:</td><td><strong>${ae(F.production.documents)}</strong> docs · <strong>${ae(F.production.chunks)}</strong> chunks</td></tr>
         <tr><td>WIP source:</td><td><strong>${ae(F.wip.documents)}</strong> docs · <strong>${ae(F.wip.chunks)}</strong> chunks</td></tr>
         <tr><td>WIP generation:</td><td><code>${z(Te(F.wip.generation_id))}</code></td></tr>
       </table>
       <label style="display:flex;align-items:center;gap:0.4rem;margin:0.75rem 0;font-size:0.85rem;cursor:pointer">
         <input type="checkbox" id="corpus-force-full-upsert" />
         Forzar upsert completo (sincronizar summaries + embeddings aunque chunk_text no haya cambiado)
       </label>
       <p class="corpus-confirm-note">The backend will keep a promotion plan, batch checkpoints, and a resumable cursor before activation.</p>`,"Promote now"))return;const y=document.querySelector("#corpus-force-full-upsert"),f=(y==null?void 0:y.checked)??!1;$=!1,N=0,q=null,P=0,await S("/api/ops/corpus/rebuild-from-wip",{mode:"promote",force_full_upsert:f},"promote",f?"Promotion started (force full upsert).":"Promotion started.")}async function l(){var y;const F=(n==null?void 0:n.current_operation)??(n==null?void 0:n.last_operation)??null;!(F!=null&&F.resume_job_id)||o||!await w("Resume from Checkpoint",`<p>The backend will reuse the persisted promotion plan and continue from the last completed checkpoint.</p>
       <table class="corpus-confirm-table">
         <tr><td>Job:</td><td><code>${z(Te(F.resume_job_id))}</code></td></tr>
         <tr><td>Checkpoint:</td><td>${z(kt(F))}</td></tr>
         <tr><td>Target generation:</td><td><code>${z(Te(F.target_generation_id))}</code></td></tr>
       </table>`,"Resume now")||($=!0,N=((y=F.last_checkpoint)==null?void 0:y.cursor)??0,q=null,P=0,await S("/api/ops/corpus/rebuild-from-wip/resume",{job_id:F.resume_job_id},"resume","Resume started."))}async function I(){const F=n;!F||!F.rollback_generation_id||o||!await w("Rollback de Production",`<p>Se va a intentar reactivar una generación previa de production.</p>
       <table class="corpus-confirm-table">
         <tr><td>Production actual:</td><td><code>${z(Te(F.production.generation_id))}</code></td></tr>
         <tr><td>Objetivo:</td><td><code>${z(Te(F.rollback_generation_id))}</code></td></tr>
       </table>
       <p class="corpus-confirm-note">Solo se habilita si el backend detecta una generación previa todavía utilizable.</p>`,"Revertir ahora","rollback")||await S("/api/ops/corpus/rollback",{generation_id:F.rollback_generation_id},"rollback","Rollback started.")}async function B(){o||await S("/api/ops/corpus/wip-audit",{},"audit","WIP audit started.")}async function Z(){o||!await w("Reiniciar promoción",`<p>Cancela cualquier job anterior y lanza una nueva promoción desde WIP a producción.</p>
       <label style="display:flex;align-items:center;gap:0.4rem;margin:0.75rem 0;font-size:0.85rem;cursor:default;opacity:0.55" title="Force upsert es obligatorio en reinicio">
         <input type="checkbox" checked disabled style="opacity:0.55" />
         Forzar upsert completo (sincronizar summaries + embeddings aunque chunk_text no haya cambiado)
       </label>
       <p class="corpus-confirm-note">Reiniciar siempre usa force upsert: todos los ~50K chunks se copian completos.</p>`,"Reiniciar ahora","rollback")||($=!1,N=0,q=null,P=0,await S("/api/ops/corpus/rebuild-from-wip/restart",{},"restart","Restart submitted (force full upsert)."))}async function le(){if(!(R||o||!await w("Sincronizar JSONL a WIP",`<p>Se va a sincronizar el índice JSONL local ya existente al Supabase WIP (Docker).</p>
       <p class="corpus-confirm-note">Esta operación no ejecuta reindex — solo sincroniza los documentos y chunks que ya existen en el JSONL local. Es segura e idempotente.</p>`,"Sincronizar ahora"))){R=!0,D();try{const{response:C,data:y}=await je("/api/ops/corpus/sync-to-wip",{});C.ok&&(y!=null&&y.synced)?H(`WIP sincronizado: ${ae(y.documents)} docs, ${ae(y.chunks)} chunks.`,"success"):H((y==null?void 0:y.error)||"Error sincronizando a WIP.","error")}catch(C){const y=C instanceof Error?C.message:String(C);H(y||"Error sincronizando a WIP.","error")}finally{R=!1,await ie()}}}async function me(){const F=(n==null?void 0:n.current_operation)??(n==null?void 0:n.last_operation)??null,C=String((F==null?void 0:F.log_tail)||"").trim();if(C)try{await navigator.clipboard.writeText(C),H("Log tail copied.","success")}catch(y){const f=y instanceof Error?y.message:"Could not copy log tail.";H(f||"Could not copy log tail.","error")}}function D(){var Se,we,G,Ee,Ie,Ae,xe,Re,_e,Me,qe;const F=e.container.querySelector(".corpus-log-accordion");F&&(h=F.open);const C=e.container.querySelector(".corpus-checks-accordion");C&&(E=C.open);const y=n;if(!y){e.container.innerHTML=`<p class="ops-empty">${z(u||"Cargando estado del corpus…")}</p>`;return}const f=y.current_operation??y.last_operation??null,j=zn(f,y),L=!!(y.current_operation&&["queued","running"].includes(y.current_operation.status))||!!o,_=L||!y.preflight_ready,X=!L&&!!(f&&f.resume_supported&&f.resume_job_id&&(f.operation_state_code==="stalled_resumable"||f.operation_state_code==="failed_resumable")),be=L||!y.rollback_available,A=y.delta.documents==="+0"&&y.delta.chunks==="+0"?"Sin delta pendiente":`${y.delta.documents} documentos · ${y.delta.chunks} chunks`,O=jt(f==null?void 0:f.checks,{onlyFailures:!0}),Y=jt(f==null?void 0:f.checks),W=!!(y.current_operation&&["queued","running"].includes(y.current_operation.status)),ce=c&&!(y.current_operation&&["queued","running"].includes(y.current_operation.status))?`
          <div class="corpus-callout tone-${z(c.tone==="success"?"green":"red")}">
            <strong>${c.tone==="success"?"Request sent":"Request failed"}</strong>
            <span>${z(c.message)}</span>
          </div>`:"",te=(Se=f==null?void 0:f.last_checkpoint)!=null&&Se.phase?(()=>{const he=f.operation_state_code==="completed"?"green":f.operation_state_code==="failed_resumable"||f.operation_state_code==="stalled_resumable"?"red":"yellow",fe=Ft(f);return`
            <div class="corpus-callout tone-${z(he)}">
              <strong>Checkpoint</strong>
              <span>${z(kt(f))} · ${z(Dt(f.last_checkpoint.at||null))}</span>
              ${fe>0&&he!=="green"?`<div class="corpus-progress-bar corpus-progress-bar-sm"><div class="corpus-progress-fill" style="width:${fe.toFixed(1)}%"></div></div>`:""}
            </div>`})():"";e.container.innerHTML=`
      <div class="corpus-cards">
        ${Bt("WIP",y.wip)}
        ${Bt("PRODUCTION",y.production)}
      </div>
      <div class="corpus-delta">
        <span class="corpus-delta-label">${z(A)}</span>
      </div>
      <section class="corpus-operation-panel severity-${z(j.severity)}">
        <div class="corpus-operation-header">
          <div>
            <div class="corpus-status-chip tone-${z(j.severity)}${j.severity==="yellow"?" is-pulsing":""}">
              ${z(j.title)}
            </div>
            <h3 class="corpus-operation-title">${z(Hn(f))}</h3>
            <p class="corpus-operation-detail">${z(j.detail)}</p>
          </div>
          <dl class="corpus-operation-meta">
            <div><dt>Heartbeat</dt><dd>${z(Dt((f==null?void 0:f.heartbeat_at)||(f==null?void 0:f.updated_at)||null))}</dd></div>
            <div><dt>Backend</dt><dd>${z(jn(f))}${f!=null&&f.force_full_upsert?` <span style="background:${Ot.amber[100]};color:${Ot.amber[600]};padding:0.1rem 0.4rem;border-radius:0.3rem;font-size:0.7rem;font-weight:700">FORCE UPSERT</span>`:""}</dd></div>
            <div><dt>Phase</dt><dd>${z(f!=null&&f.current_phase?ft(f.current_phase):(f==null?void 0:f.stage_label)||(y.preflight_ready?"Ready":"Blocked"))}</dd></div>
            <div><dt>Checkpoint</dt><dd>${z(kt(f))}</dd></div>
            <div><dt>WIP</dt><dd><code>${z(Te((f==null?void 0:f.source_generation_id)||y.wip.generation_id))}</code></dd></div>
            <div><dt>Target</dt><dd><code>${z(Te((f==null?void 0:f.target_generation_id)||(f==null?void 0:f.production_generation_id)||y.production.generation_id))}</code></dd></div>
            <div><dt>Prod</dt><dd><code>${z(Te((f==null?void 0:f.production_generation_id)||y.production.generation_id))}</code></dd></div>
          </dl>
        </div>
        ${W?(()=>{var ze,ue;const he=Ft(f),fe=((ze=f==null?void 0:f.last_checkpoint)==null?void 0:ze.cursor)??(f==null?void 0:f.batch_cursor)??0,Xe=((ue=f==null?void 0:f.last_checkpoint)==null?void 0:ue.total)??0,Fe=Fn(f);if(fe>0&&Xe>0){const ve=Date.now();if(q&&fe>q.cursor){const Oe=Math.max(1,(ve-q.ts)/1e3),Q=(fe-q.cursor)/Oe;P=P>0?P*.7+Q*.3:Q}q={cursor:fe,ts:ve}}const Ye=P>0?`${P.toFixed(0)} chunks/s`:"",Qe=Xe-fe,et=P>0&&Qe>0?(()=>{const ve=Math.ceil(Qe/P),Oe=Math.floor(ve/60),Q=ve%60;return Oe>0?`~${Oe}m ${Q}s restante`:`~${Q}s restante`})():"";return`
            <div class="corpus-progress-bar"><div class="corpus-progress-fill" style="width:${he.toFixed(1)}%"></div></div>
            <div class="corpus-progress-detail">
              ${$?`<span class="corpus-resume-badge">REANUDADO desde ${ae(N)}</span>`:""}
              <span class="corpus-progress-nums">${ae(fe)} / ${ae(Xe)} (${he.toFixed(1)}%)</span>
              ${Ye?`<span class="corpus-progress-rate">${z(Ye)}</span>`:""}
              ${et?`<span class="corpus-progress-eta">${z(et)}</span>`:""}
              <span class="corpus-hb-badge ${Fe.className}">${z(Fe.label)}</span>
            </div>`})():""}
        ${(we=f==null?void 0:f.stages)!=null&&we.length?Bn(f.stages):""}
        ${te}
        ${(G=y.preflight_reasons)!=null&&G.length&&!W&&!y.preflight_ready?`
          <div class="corpus-callout tone-red">
            <strong>Preflight blocked</strong>
            <ul>${y.preflight_reasons.map(he=>`<li>${z(he)}</li>`).join("")}</ul>
          </div>`:""}
        ${ce}
        ${O?`<div class="corpus-section"><h4>Visible failures</h4>${O}</div>`:""}
        ${Y?`
          <details class="corpus-section corpus-checks-accordion">
            <summary class="corpus-checks-summary"><h4>Checks</h4><span class="corpus-checks-count">${((f==null?void 0:f.checks)??[]).length}</span></summary>
            ${Y}
          </details>`:""}
        ${Wn(f)}
        ${f!=null&&f.log_tail?`
          <details class="corpus-section corpus-log-accordion">
            <summary class="corpus-log-summary">
              <h4>Backend log tail</h4>
              <button id="corpus-copy-log-tail-btn" type="button" class="corpus-btn corpus-btn-rollback corpus-btn-inline">Copy</button>
            </summary>
            <pre class="corpus-log-tail">${z(f.log_tail)}</pre>
          </details>`:""}
        ${u?`
          <div class="corpus-callout tone-red">
            <strong>Refresh error</strong>
            <span>${z(u)}</span>
          </div>`:""}
      </section>
      <div class="corpus-actions">
        ${y.audit_missing&&!L?`
          <button id="corpus-audit-btn" class="corpus-btn corpus-btn-audit${o==="audit"?" is-busy":""}">
            ${o==="audit"?'<span class="corpus-spinner"></span> Auditing…':"Run WIP Audit"}
          </button>`:""}
        ${!L&&!R?`
          <button id="corpus-sync-wip-btn" class="corpus-btn corpus-btn-sync">Sincronizar JSONL a WIP</button>`:""}
        ${R?`
          <button class="corpus-btn corpus-btn-sync is-busy" disabled><span class="corpus-spinner"></span> Sincronizando…</button>`:""}
        <button id="corpus-promote-btn" class="corpus-btn corpus-btn-promote${o==="promote"?" is-busy":""}" ${_?"disabled":""}>
          ${o==="promote"?'<span class="corpus-spinner"></span> Starting…':"Promote WIP to Production"}
        </button>
        ${X?`
          <button id="corpus-resume-btn" class="corpus-btn corpus-btn-promote${o==="resume"?" is-busy":""}">
            ${o==="resume"?'<span class="corpus-spinner"></span> Resuming…':"Resume from Checkpoint"}
          </button>`:""}
        <button id="corpus-rollback-btn" class="corpus-btn corpus-btn-rollback${o==="rollback"?" is-busy":""}" ${be?"disabled":""}>
          ${o==="rollback"?'<span class="corpus-spinner"></span> Starting rollback…':"Rollback"}
        </button>
        <button id="corpus-restart-btn" class="corpus-btn corpus-btn-rollback${o==="restart"?" is-busy":""}" ${L?"disabled":""}>
          ${o==="restart"?'<span class="corpus-spinner"></span> Restarting…':"Reiniciar promoción (force upsert)"}
        </button>
      </div>
      ${y.preflight_ready?"":`
        <p class="corpus-action-note">${z(((Ee=y.preflight_reasons)==null?void 0:Ee[0])||"Promotion is blocked by preflight.")}</p>`}
      ${y.rollback_available?"":`
        <p class="corpus-action-note">${z(y.rollback_reason||"Rollback is not available yet.")}</p>`}
      <div class="corpus-toast ops-flash" hidden></div>
    `,(Ie=e.container.querySelector("#corpus-audit-btn"))==null||Ie.addEventListener("click",B),(Ae=e.container.querySelector("#corpus-sync-wip-btn"))==null||Ae.addEventListener("click",()=>void le()),(xe=e.container.querySelector("#corpus-promote-btn"))==null||xe.addEventListener("click",v),(Re=e.container.querySelector("#corpus-resume-btn"))==null||Re.addEventListener("click",l),(_e=e.container.querySelector("#corpus-rollback-btn"))==null||_e.addEventListener("click",I),(Me=e.container.querySelector("#corpus-restart-btn"))==null||Me.addEventListener("click",Z),(qe=e.container.querySelector("#corpus-copy-log-tail-btn"))==null||qe.addEventListener("click",he=>{he.preventDefault(),he.stopPropagation(),me()});const ne=e.container.querySelector(".corpus-log-accordion");ne&&h&&(ne.open=!0);const $e=e.container.querySelector(".corpus-checks-accordion");$e&&E&&($e.open=!0)}async function ie(){try{n=await Pe("/api/ops/corpus-status"),u="",n!=null&&n.current_operation&&["queued","running","completed","failed","cancelled"].includes(n.current_operation.status)&&(c=null)}catch(F){u=F instanceof Error?F.message:String(F),n===null&&(n=null)}D()}function ge(){D(),s===null&&(s=window.setInterval(()=>{ie()},qn))}return{bindEvents:ge,refresh:ie}}const va=Object.freeze(Object.defineProperty({__proto__:null,createCorpusLifecycleController:an},Symbol.toStringTag,{value:"Module"})),Gn={normative_base:"Normativa",interpretative_guidance:"Interpretación",practica_erp:"Práctica"},At={declaracion_renta:"Renta",iva:"IVA",laboral:"Laboral",facturacion_electronica:"Facturación",estados_financieros_niif:"NIIF",ica:"ICA",calendario_obligaciones:"Calendarios",retencion_fuente:"Retención",regimen_sancionatorio:"Sanciones",regimen_cambiario:"Régimen Cambiario",impuesto_al_patrimonio:"Patrimonio",informacion_exogena:"Exógena",proteccion_de_datos:"Datos",obligaciones_mercantiles:"Mercantil",obligaciones_profesionales_contador:"Obligaciones Contador",rut_responsabilidades:"RUT",gravamen_movimiento_financiero_4x1000:"GMF 4×1000",beneficiario_final:"Beneficiario Final",contratacion_estatal:"Contratación Estatal",reforma_pensional:"Reforma Pensional",zomac_incentivos:"ZOMAC"},on="lia_backstage_ops_active_tab",Nt="lia_backstage_ops_ingestion_session_id";function Jn(){const e=_t();try{const t=String(e.getItem(on)||"").trim();return t==="ingestion"||t==="control"||t==="embeddings"||t==="reindex"?t:"monitor"}catch{return"monitor"}}function Kn(e){const t=_t();try{t.setItem(on,e)}catch{}}function Vn(){const e=_t();try{return String(e.getItem(Nt)||"").trim()}catch{return""}}function Xn(e){const t=_t();try{if(!e){t.removeItem(Nt);return}t.setItem(Nt,e)}catch{}}function ht(e){return e==="processing"||e==="running_batch_gates"}function Ut(e){if(!e)return!1;const t=String(e.status||"").toLowerCase();if(t==="done"||t==="completed")return!0;const n=e.documents||[];return n.length===0?!1:n.every(a=>{const s=String(a.status||"").toLowerCase();return s==="done"||s==="completed"||s==="skipped_duplicate"||s==="bounced"})}function lt(e){const t=String(e||"").trim().toLowerCase();return t==="failed"||t==="error"?"error":t==="processing"||t==="running_batch_gates"||t==="needs_retry_batch_gate"||t==="queued"||t==="uploading"||t==="extracting"||t==="etl"||t==="writing"||t==="gates"||t==="in_progress"||t==="partial_failed"||t==="raw"||t==="pending_dedup"?"warn":"ok"}function pe(e){return e instanceof st?e.message||`HTTP ${e.status}`:e instanceof Error?e.message:String(e||"unknown_error")}function Zn(e,t){switch(String(e||"").trim()){case"normative_base":return t.t("ops.ingestion.batchType.normative");case"interpretative_guidance":return t.t("ops.ingestion.batchType.interpretative");case"practica_erp":return t.t("ops.ingestion.batchType.practical");default:return String(e||"-")}}function Yn(e,t){const n=Number(e||0);return!Number.isFinite(n)||n<=0?"0 B":n>=1024*1024?`${t.formatNumber(n/(1024*1024),{maximumFractionDigits:1})} MB`:n>=1024?`${t.formatNumber(n/1024,{maximumFractionDigits:1})} KB`:`${t.formatNumber(n)} B`}function Wt(e,t){const n=e||{total:0,queued:0,done:0,failed:0,pending_batch_gate:0,bounced:0},a=[`${t.t("ops.ingestion.summary.total")} ${n.total||0}`,`${t.t("ops.ingestion.summary.done")} ${n.done||0}`,`${t.t("ops.ingestion.summary.failed")} ${n.failed||0}`,`${t.t("ops.ingestion.summary.queued")} ${n.queued||0}`,`${t.t("ops.ingestion.summary.gate")} ${n.pending_batch_gate||0}`],s=Number(n.bounced||0);return s>0&&a.push(`Rebotados ${s}`),a.join(" · ")}function Pt(e,t,n){const a=e||t||"";if(!a)return"stalled";const s=Date.parse(a);if(Number.isNaN(s))return"stalled";const o=Date.now()-s,u=n==="gates",c=u?9e4:3e4,b=u?3e5:12e4;return o<c?"alive":o<b?"slow":"stalled"}function Qn(e,t){const n=e||t||"";if(!n)return"-";const a=Date.parse(n);if(Number.isNaN(a))return"-";const s=Math.max(0,Date.now()-a),o=Math.floor(s/1e3);if(o<5)return"ahora";if(o<60)return`hace ${o}s`;const u=Math.floor(o/60),c=o%60;return u<60?`hace ${u}m ${c}s`:`hace ${Math.floor(u/60)}h ${u%60}m`}const St={validating:"validando corpus",manifest:"activando manifest",indexing:"reconstruyendo índice","indexing/scanning":"escaneando documentos","indexing/chunking":"generando chunks","indexing/writing_indexes":"escribiendo índices","indexing/syncing":"sincronizando Supabase","indexing/auditing":"auditando calidad"};function rn(e){if(!e)return"";if(St[e])return St[e];const t=e.indexOf(":");if(t>0){const n=e.slice(0,t),a=e.slice(t+1),s=St[n];if(s)return`${s} (${a})`}return e}function es(e){if(!e)return"";const t=Date.parse(e);if(Number.isNaN(t))return"";try{return new Intl.DateTimeFormat("es-CO",{timeZone:"America/Bogota",day:"2-digit",month:"2-digit",year:"numeric",hour:"2-digit",minute:"2-digit",second:"2-digit",hour12:!1}).format(new Date(t))}catch{return""}}function cn(e,t){const n=Math.max(0,Math.min(100,Number(e||0))),a=document.createElement("div");a.className="ops-progress";const s=document.createElement("div");s.className="ops-progress-bar";const o=document.createElement("span");o.className="ops-progress-fill",t==="gates"&&n>0&&n<100&&o.classList.add("ops-progress-active"),o.style.width=`${n}%`;const u=document.createElement("span");return u.className="ops-progress-label",u.textContent=`${n}%`,s.appendChild(o),a.append(s,u),a}function De(e){return String(e??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#39;")}function Je(e){return(e??0).toLocaleString("es-CO")}function Gt(e){if(e==null||e<=0)return"-";const t=Math.floor(e/60),n=Math.floor(e%60);return t>0?`${t}m ${n}s`:`${n}s`}function ln({dom:e,setFlash:t}){const{container:n}=e;let a=null,s="",o=!1,u=!1,c=0,b=0,h=3e3,E=[];function R(v){if(v<=0)return;const l=Date.now();if(v>c&&b>0){const I=l-b,B=v-c,Z=I/B;E.push(Z),E.length>10&&E.shift(),h=E.reduce((le,me)=>le+me,0)/E.length}v!==c&&(c=v,b=l)}function $(){if(b===0)return{level:"healthy",label:"Iniciando..."};const v=Date.now()-b,l=Math.max(h*3,1e4),I=Math.max(h*6,3e4);return v<l?{level:"healthy",label:"Saludable"}:v<I?{level:"caution",label:"Lento"}:{level:"failed",label:"Sin respuesta"}}function N(){var Y,W,ce,te,ne,$e,Se,we;const v=a;if(!v){n.innerHTML='<p class="ops-text-muted">Cargando estado de embeddings...</p>';return}const l=v.current_operation||v.last_operation,I=((Y=v.current_operation)==null?void 0:Y.status)??"",B=I==="running"||I==="queued"||s==="start",Z=!v.current_operation&&!s,le=s==="stop",me=!B&&!le&&((l==null?void 0:l.status)==="cancelled"||(l==null?void 0:l.status)==="failed"||(l==null?void 0:l.status)==="stalled");let D="";const ie=(l==null?void 0:l.status)??"",ge=le?"Deteniendo...":B?"En ejecución":me?ie==="stalled"?"Detenido (stalled)":ie==="cancelled"?"Cancelado":"Fallido":Z?"Inactivo":ie||"—",F=B?"tone-yellow":ie==="completed"?"tone-green":ie==="failed"||ie==="stalled"?"tone-red":ie==="cancelled"?"tone-yellow":"",C=v.api_health,y=C!=null&&C.ok?"emb-api-ok":"emb-api-error",f=C?C.ok?`API OK (${C.detail})`:`API Error: ${C.detail}`:"API: verificando...";if(D+=`<div class="emb-status-row">
      <span class="corpus-status-chip ${F}">${De(ge)}</span>
      <span class="emb-target-badge">WIP</span>
      <span class="emb-api-semaphore ${y}" title="${De(f)}"><span class="emb-api-dot"></span> ${De(C!=null&&C.ok?"API OK":C?"API Error":"...")}</span>
      ${B?(()=>{const G=$();return`<span class="emb-process-health emb-health-${G.level}"><span class="emb-health-dot"></span> ${De(G.label)}</span>`})():""}
    </div>`,D+='<div class="emb-controls">',Z?(D+=`<label class="emb-force-label"><input type="checkbox" id="emb-force-check" ${o?"checked":""} /> Forzar re-embed (todas)</label>`,D+=`<button class="corpus-btn corpus-btn-promote" id="emb-start-btn" ${s?"disabled":""}>Iniciar</button>`):le?D+='<span class="emb-running-label">Deteniendo al finalizar batch actual...</span>':B&&l&&(D+='<button class="corpus-btn corpus-btn-rollback" id="emb-stop-btn">Detener</button>',D+='<span class="emb-running-label">Embebiendo chunks...</span>'),me&&l){const G=l.force,Ee=(W=l.progress)==null?void 0:W.last_cursor_id,Ie=(ce=l.progress)==null?void 0:ce.pct_complete,Ae=Ee?`Reanudar desde ${typeof Ie=="number"?Ie.toFixed(1)+"%":"checkpoint"}`:"Reiniciar";G&&(D+='<span class="emb-force-label"><input type="checkbox" checked disabled /> Forzar re-embed (continuación)</span>'),D+=`<button class="corpus-btn corpus-btn-promote" id="emb-resume-btn" ${s?"disabled":""}>${De(Ae)}</button>`,D+=`<button class="corpus-btn" id="emb-start-btn" ${s?"disabled":""} style="opacity:0.7">Iniciar desde cero</button>`}D+="</div>";const j=l==null?void 0:l.progress,L=(B||s)&&(j==null?void 0:j.total),_=L?j.total:v.total_chunks,X=L?j.embedded:v.embedded_chunks,be=L?j.pending-j.embedded-(j.failed||0):v.null_embedding_chunks,A=L&&j.failed||0,O=L?j.pct_complete:v.coverage_pct;if(D+=`<div class="emb-stats-grid">
      <div class="emb-stat"><span class="emb-stat-value">${Je(_)}</span><span class="emb-stat-label">Total</span></div>
      <div class="emb-stat"><span class="emb-stat-value">${Je(X)}</span><span class="emb-stat-label">Embebidos</span></div>
      <div class="emb-stat"><span class="emb-stat-value">${Je(Math.max(0,be))}</span><span class="emb-stat-label">Pendientes</span></div>
      ${A>0?`<div class="emb-stat emb-stat-error"><span class="emb-stat-value">${Je(A)}</span><span class="emb-stat-label">Fallidos</span></div>`:`<div class="emb-stat"><span class="emb-stat-value">${O.toFixed(1)}%</span><span class="emb-stat-label">Cobertura</span></div>`}
    </div>`,B&&(l!=null&&l.progress)){const G=l.progress;D+='<div class="emb-live-progress">',D+='<div class="emb-progress-bar-wrap" id="emb-progress-mount"></div>',D+=`<div class="emb-rate-line">
        <span>${((te=G.rate_chunks_per_sec)==null?void 0:te.toFixed(1))??"-"} chunks/s</span>
        <span>ETA: ${Gt(G.eta_seconds)}</span>
        <span>Elapsed: ${Gt(G.elapsed_seconds)}</span>
        <span>Batch ${Je(G.current_batch)} / ${Je(G.total_batches)}</span>
      </div>`,G.failed>0&&(D+=`<p class="emb-failed-notice">${Je(G.failed)} chunks fallidos (${(G.failed/Math.max(G.pending,1)*100).toFixed(2)}%)</p>`),D+="</div>"}if(l!=null&&l.quality_report){const G=l.quality_report;D+='<div class="emb-quality-report">',D+="<h3>Reporte de calidad</h3>",D+=`<div class="emb-stats-grid">
        <div class="emb-stat"><span class="emb-stat-value">${((ne=G.mean_cosine_similarity)==null?void 0:ne.toFixed(4))??"-"}</span><span class="emb-stat-label">Coseno medio</span></div>
        <div class="emb-stat"><span class="emb-stat-value">${(($e=G.min_cosine_similarity)==null?void 0:$e.toFixed(4))??"-"}</span><span class="emb-stat-label">Min</span></div>
        <div class="emb-stat"><span class="emb-stat-value">${((Se=G.max_cosine_similarity)==null?void 0:Se.toFixed(4))??"-"}</span><span class="emb-stat-label">Max</span></div>
        <div class="emb-stat"><span class="emb-stat-value">${Je(G.sample_pairs)}</span><span class="emb-stat-label">Pares</span></div>
      </div>`,G.collapsed_warning&&(D+='<p class="emb-anomaly-warning">ANOMALIA: Embeddings colapsados (mean &gt; 0.95)</p>'),G.noise_warning&&(D+='<p class="emb-anomaly-warning">ANOMALIA: Embeddings ruidosos (mean &lt; 0.10)</p>'),!G.collapsed_warning&&!G.noise_warning&&(D+='<p class="emb-quality-ok">Distribución saludable</p>'),D+="</div>"}if((we=l==null?void 0:l.checks)!=null&&we.length){D+='<div class="emb-checks">';for(const G of l.checks){const Ee=G.ok?'<span class="ops-dot ops-dot-ok">●</span>':'<span class="ops-dot ops-dot-error">●</span>';D+=`<div class="emb-check">${Ee} <strong>${De(G.label)}</strong>: ${De(G.detail)}</div>`}D+="</div>"}if(l!=null&&l.log_tail){const G=l.log_tail.split(`
`).reverse().join(`
`);D+=`<details class="emb-log-accordion" id="emb-log-details" ${u?"open":""}><summary>Log</summary><pre class="emb-log-tail">${De(G)}</pre></details>`}if(l!=null&&l.error&&(D+=`<p class="emb-error">${De(l.error)}</p>`),n.innerHTML=D,B&&(l!=null&&l.progress)){const G=n.querySelector("#emb-progress-mount");G&&G.appendChild(cn(l.progress.pct_complete??0,"embedding"))}}function q(){n.addEventListener("click",v=>{const l=v.target;l.id==="emb-start-btn"&&P(),l.id==="emb-stop-btn"&&H(),l.id==="emb-resume-btn"&&w()}),n.addEventListener("change",v=>{const l=v.target;l.id==="emb-force-check"&&(o=l.checked)}),n.addEventListener("toggle",v=>{const l=v.target;l.id==="emb-log-details"&&(u=l.open)},!0)}async function P(){const v=o;s="start",o=!1,N();try{const{response:l,data:I}=await je("/api/ops/embedding/start",{force:v});!l.ok||!(I!=null&&I.ok)?(t((I==null?void 0:I.error)||`Error ${l.status}`,"error"),s=""):t("Embedding iniciado","success")}catch(l){t(String(l),"error"),s=""}await S()}async function H(){var l;const v=(l=a==null?void 0:a.current_operation)==null?void 0:l.job_id;if(v){s="stop",N();try{await je("/api/ops/embedding/stop",{job_id:v}),t("Stop solicitado — se detendrá al finalizar el batch actual","success")}catch(I){t(String(I),"error"),s=""}}}async function w(){const v=(a==null?void 0:a.current_operation)||(a==null?void 0:a.last_operation);if(v!=null&&v.job_id){s="start",N();try{const{response:l,data:I}=await je("/api/ops/embedding/resume",{job_id:v.job_id});!l.ok||!(I!=null&&I.ok)?(t((I==null?void 0:I.error)||`Error ${l.status}`,"error"),s=""):t("Embedding reanudado desde checkpoint","success")}catch(l){t(String(l),"error"),s=""}s="",await S()}}async function S(){try{const v=await Pe("/api/ops/embedding-status");a=v;const l=v.current_operation;if(l!=null&&l.progress){const I=l.progress.current_batch;typeof I=="number"&&R(I)}s==="stop"&&!v.current_operation&&(s=""),s==="start"&&v.current_operation&&(s=""),v.current_operation||(c=0,b=0,E=[])}catch{}N()}return{bindEvents:q,refresh:S}}const _a=Object.freeze(Object.defineProperty({__proto__:null,createOpsEmbeddingsController:ln},Symbol.toStringTag,{value:"Module"})),ts=["pending","processing","done"],ns={pending:"Pendiente",processing:"En proceso",done:"Procesado"},ss={pending:"⏳",processing:"🔄",done:"✅"},as=5;function dn(e){const t=String(e||"").toLowerCase();return t==="done"||t==="completed"||t==="skipped_duplicate"||t==="bounced"?"done":t==="in_progress"||t==="processing"||t==="extracting"||t==="etl"||t==="writing"||t==="gates"||t==="uploading"||t==="running_batch_gates"||t==="needs_retry_batch_gate"||t==="failed"||t==="error"||t==="partial_failed"?"processing":"pending"}function os(e,t){const n=e.detected_topic||t.corpus||"",a=pn[n]||At[n]||n||"",s=e.detected_type||e.batch_type||"",o=Gn[s]||s||"",u=s==="normative_base"?"normative":s==="interpretative_guidance"?"interpretative":s==="practica_erp"?"practica":"unknown";let c="";return a&&(c+=`<span class="kanban-pill kanban-pill--topic" title="Tema: ${de(n)}">${ke(a)}</span>`),o&&(c+=`<span class="kanban-pill kanban-pill--type-${u}" title="Tipo: ${de(s)}">${ke(o)}</span>`),!a&&!o&&(c+='<span class="kanban-pill kanban-pill--unclassified">Sin clasificar</span>'),c}function is(e,t,n){var B;const a=lt(e.status),s=dn(e.status),o=Yn(e.bytes,n),u=Number(e.progress||0),c=new Set(t.gate_pending_doc_ids||[]),b=s==="done"&&c.has(e.doc_id);let h;e.status==="bounced"?h='<span class="meta-chip status-bounced">↩ Ya existe en el corpus</span>':s==="done"&&e.derived_from_doc_id&&(e.delta_section_count||0)>0?h=`<span class="meta-chip status-ok">△ ${e.delta_section_count} secciones nuevas</span>`:s==="done"&&(e.status==="done"||e.status==="completed")?(h='<span class="meta-chip status-ok">✓ Documento listo</span>',b&&(h+='<span class="meta-chip status-gate-pending">Pendiente validación final</span>')):h=`<span class="meta-chip status-${a}">${ke(e.status)}</span>`;const E=os(e,t);let R="";if(e.status==="in_progress"||e.status==="processing"){const Z=Pt(e.heartbeat_at,e.updated_at,e.stage),le=Qn(e.heartbeat_at,e.updated_at);R=`<div class="kanban-liveness ops-liveness-${Z}">${le}</div>`}let $="";e.stage==="gates"&&t.gate_sub_stage&&($=`<div class="kanban-gate-sub">${rn(t.gate_sub_stage)}</div>`);let N="";s==="processing"&&u>0&&(N=`<div class="kanban-progress" data-progress="${u}"></div>`);let q="";(B=e.error)!=null&&B.message&&(q=`<div class="kanban-error">${ke(e.error.message)}</div>`);let P="";e.duplicate_of?P=`<div class="kanban-duplicate">Duplicado de: ${ke(e.duplicate_of)}</div>`:e.derived_from_doc_id&&(P=`<div class="kanban-duplicate">Derivado de: ${ke(e.derived_from_doc_id)}</div>`);let H="";if(s==="done"){const Z=es(e.updated_at);Z&&(H=`<div class="kanban-completed-at">Completado: ${ke(Z)}</div>`)}let w="";e.duplicate_of&&s!=="done"&&e.status!=="bounced"?w=ps(e):s==="pending"&&(e.status==="raw"||e.status==="needs_classification")&&cs(e)?w=ls(e,n):s==="pending"&&(e.status==="raw"||e.status==="needs_classification")?w=rs(e,n,t):s==="processing"&&(e.status==="failed"||e.status==="error"||e.status==="partial_failed")&&(w=ms(e));let S="",v="";(s!=="pending"||e.status==="queued")&&(S=ds(),v=us(e,t,n));const I=e.stage&&e.stage!==e.status&&s==="processing";return`
    <div class="kanban-card kanban-card--${a}" data-doc-id="${de(e.doc_id)}">
      <div class="kanban-card-head">
        <span class="kanban-card-title" title="${de(e.doc_id)}">${ke(e.filename||e.doc_id)}</span>
        ${h}
      </div>
      ${e.source_relative_path?`<div class="kanban-card-relpath" title="${de(e.source_relative_path)}">${ke(bs(e.source_relative_path))}</div>`:""}
      <div class="kanban-card-pills-row">
        ${E}
        <span class="kanban-card-size">${o}</span>
        ${S}
      </div>
      ${v}
      ${I?`<div class="kanban-card-stage">${ke(e.stage)}</div>`:""}
      ${R}
      ${$}
      ${N}
      ${H}
      ${P}
      ${q}
      ${w}
    </div>
  `}function rs(e,t,n){const a=e.detected_type||e.batch_type||"",s=e.detected_topic||(n==null?void 0:n.corpus)||"",o=u=>u===a?" selected":"";return`
    <div class="kanban-actions kanban-classify-actions">
      <label class="kanban-action-field">
        <span>Tema</span>
        <select data-field="topic" class="kanban-select">
          ${vt(s)}
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
        <button class="btn btn--sm btn--primary kanban-assign-btn" data-action="assign" data-doc-id="${de(e.doc_id)}">Asignar</button>
      </div>
    </div>
  `}function cs(e){return!!(e.autogenerar_label&&(e.autogenerar_is_new||e.autogenerar_resolved_topic))}function ls(e,t){const n=e.detected_type||e.batch_type||"",a=h=>h===n?" selected":"",s=`
    <label class="kanban-action-field">
      <span>Tipo</span>
      <select data-field="type" class="kanban-select">
        <option value="">Seleccionar...</option>
        <option value="normative_base"${a("normative_base")}>${t.t("ops.ingestion.batchType.normative")}</option>
        <option value="interpretative_guidance"${a("interpretative_guidance")}>${t.t("ops.ingestion.batchType.interpretative")}</option>
        <option value="practica_erp"${a("practica_erp")}>${t.t("ops.ingestion.batchType.practical")}</option>
      </select>
    </label>`;if(e.autogenerar_is_new)return`
      <div class="kanban-actions kanban-autogenerar-actions kanban-autogenerar--new">
        <div class="kanban-autogenerar-header">Nuevo tema detectado</div>
        <label class="kanban-action-field">
          <span>Tema</span>
          <input type="text" class="kanban-input" data-field="autogenerar-label"
            value="${de(e.autogenerar_label||"")}" />
        </label>
        ${e.autogenerar_rationale?`<div class="kanban-autogenerar-rationale">${ke(e.autogenerar_rationale)}</div>`:""}
        ${s}
        <div class="kanban-action-buttons">
          <button class="btn btn--sm btn--primary" data-action="accept-new-topic" data-doc-id="${de(e.doc_id)}">Aceptar nuevo tema</button>
          <button class="btn btn--sm kanban-ag-fallback-btn" data-action="show-existing-dropdown" data-doc-id="${de(e.doc_id)}">Asignar existente</button>
        </div>
        <div class="kanban-ag-fallback-panel" hidden>
          <label class="kanban-action-field">
            <span>Tema existente</span>
            <select data-field="topic" class="kanban-select">
              ${vt("")}
            </select>
          </label>
          <div class="kanban-action-field kanban-action-field--btn">
            <span>&nbsp;</span>
            <button class="btn btn--sm btn--primary kanban-assign-btn" data-action="assign" data-doc-id="${de(e.doc_id)}">Asignar</button>
          </div>
        </div>
      </div>
    `;const o=e.autogenerar_resolved_topic||"",u=At[o]||o,c=e.autogenerar_synonym_confidence??0,b=Math.round(c*100);return`
    <div class="kanban-actions kanban-autogenerar-actions kanban-autogenerar--synonym">
      <div class="kanban-autogenerar-header">Tema sugerido: <strong>${ke(u)}</strong> <span class="kanban-autogenerar-conf">(${b}%)</span></div>
      <div class="kanban-autogenerar-source">Basado en: "${ke(e.autogenerar_label||"")}"</div>
      ${s}
      <div class="kanban-action-buttons">
        <button class="btn btn--sm btn--primary" data-action="accept-synonym" data-doc-id="${de(e.doc_id)}">Aceptar</button>
        <button class="btn btn--sm kanban-ag-fallback-btn" data-action="show-existing-dropdown" data-doc-id="${de(e.doc_id)}">Cambiar</button>
      </div>
      <div class="kanban-ag-fallback-panel" hidden>
        <label class="kanban-action-field">
          <span>Tema</span>
          <select data-field="topic" class="kanban-select">
            ${vt(o)}
          </select>
        </label>
        <div class="kanban-action-field kanban-action-field--btn">
          <span>&nbsp;</span>
          <button class="btn btn--sm btn--primary kanban-assign-btn" data-action="assign" data-doc-id="${de(e.doc_id)}">Asignar</button>
        </div>
      </div>
    </div>
  `}function ds(){return'<button class="kanban-reclassify-toggle" type="button" title="Cambiar clasificación">✎</button>'}function us(e,t,n){const a=e.detected_topic||t.corpus||"",s=e.detected_type||e.batch_type||"",o=(u,c)=>u===c?" selected":"";return`
    <div class="kanban-reclassify-panel" hidden>
      <label class="kanban-action-field">
        <span>Tema</span>
        <select data-field="topic" class="kanban-select">
          ${vt(a)}
        </select>
      </label>
      <label class="kanban-action-field">
        <span>Tipo</span>
        <select data-field="type" class="kanban-select">
          <option value="">Seleccionar...</option>
          <option value="normative_base"${o("normative_base",s)}>${n.t("ops.ingestion.batchType.normative")}</option>
          <option value="interpretative_guidance"${o("interpretative_guidance",s)}>${n.t("ops.ingestion.batchType.interpretative")}</option>
          <option value="practica_erp"${o("practica_erp",s)}>${n.t("ops.ingestion.batchType.practical")}</option>
        </select>
      </label>
      <div class="kanban-action-field kanban-action-field--btn">
        <span>&nbsp;</span>
        <button class="btn btn--sm btn--primary kanban-assign-btn" data-action="assign" data-doc-id="${de(e.doc_id)}">Asignar</button>
      </div>
    </div>
  `}function ps(e){return`
    <div class="kanban-actions">
      <button class="btn btn--sm btn--primary" data-action="replace-dup" data-doc-id="${de(e.doc_id)}">Reemplazar</button>
      <button class="btn btn--sm" data-action="add-new-dup" data-doc-id="${de(e.doc_id)}">Agregar nuevo</button>
      <button class="btn btn--sm btn--danger" data-action="discard-dup" data-doc-id="${de(e.doc_id)}">Descartar</button>
    </div>
  `}function ms(e){return`
    <div class="kanban-actions">
      <button class="btn btn--sm" data-action="retry" data-doc-id="${de(e.doc_id)}">Reintentar</button>
      <button class="btn btn--sm btn--danger" data-action="discard" data-doc-id="${de(e.doc_id)}">Descartar</button>
    </div>
  `}const un=[["declaracion_renta","Renta"],["iva","IVA"],["laboral","Laboral"],["facturacion_electronica","Facturación"],["estados_financieros_niif","NIIF"],["ica","ICA"],["calendario_obligaciones","Calendarios"],["retencion_fuente","Retención"],["regimen_sancionatorio","Sanciones"],["regimen_cambiario","Régimen Cambiario"],["impuesto_al_patrimonio","Patrimonio"],["informacion_exogena","Exógena"],["proteccion_de_datos","Datos"],["obligaciones_mercantiles","Mercantil"],["obligaciones_profesionales_contador","Obligaciones Contador"],["rut_responsabilidades","RUT"],["gravamen_movimiento_financiero_4x1000","GMF 4×1000"],["beneficiario_final","Beneficiario Final"],["contratacion_estatal","Contratación Estatal"],["reforma_pensional","Reforma Pensional"],["zomac_incentivos","ZOMAC"]];function gs(e){const t=new Set,n=[];for(const[a,s]of un)t.add(a),n.push([a,s]);for(const a of e)!a.key||t.has(a.key)||(t.add(a.key),n.push([a.key,a.label||a.key]));return n}let It=un,pn={...At};function vt(e=""){let t='<option value="">Seleccionar...</option>';for(const[n,a]of It){const s=n===e?" selected":"";t+=`<option value="${de(n)}"${s}>${ke(a)}</option>`}return t}function ke(e){const t=document.createElement("span");return t.textContent=e,t.innerHTML}function de(e){return e.replace(/&/g,"&amp;").replace(/"/g,"&quot;").replace(/'/g,"&#39;").replace(/</g,"&lt;").replace(/>/g,"&gt;")}function bs(e){const t=e.replace(/\/[^/]+$/,"").split("/").filter(Boolean);return t.length<=2?t.join("/")+"/":"…/"+t.slice(-2).join("/")+"/"}function fs(e,t,n,a,s){s&&s.length>0&&(It=gs(s),pn=Object.fromEntries(It));const o=[...e.documents||[]].sort((w,S)=>Date.parse(String(S.updated_at||0))-Date.parse(String(w.updated_at||0))),u={pending:[],processing:[],done:[]};for(const w of o){const S=dn(w.status);u[S].push(w)}u.pending.sort((w,S)=>{const v=w.status==="raw"||w.status==="needs_classification"?0:1,l=S.status==="raw"||S.status==="needs_classification"?0:1;return v!==l?v-l:Date.parse(String(S.updated_at||0))-Date.parse(String(w.updated_at||0))});const c=e.status==="running_batch_gates",b=e.gate_sub_stage||"";let h="";if(c){const w=b?rn(b):"Preparando...";h=`
      <div class="kanban-validation-banner kanban-validation-banner--running">
        <span class="kanban-validation-spinner"></span>
        <span>Validación final en curso — ${ke(w)}</span>
      </div>`}else e.status==="needs_retry_batch_gate"?h=`
      <div class="kanban-validation-banner kanban-validation-banner--error">
        <span>⚠ Validación final fallida — use Reintentar o Validar lote</span>
      </div>`:e.status==="completed"&&e.wip_sync_status==="skipped"&&(h=`
      <div class="kanban-validation-banner kanban-validation-banner--warn">
        <span>⚠ Ingesta completada solo localmente — WIP Supabase no estaba disponible. Use Operaciones → Sincronizar a WIP.</span>
      </div>`);let E="";const R=u.processing.length;for(const w of ts){const S=u[w],v=w==="processing"?`<span class="kanban-column-count">${R}</span><span class="kanban-column-limit">/ ${as}</span>`:`<span class="kanban-column-count">${S.length}</span>`,l=S.length===0?'<div class="kanban-column-empty">Sin documentos</div>':S.map(B=>is(B,e,n)).join(""),I=w==="done"?h:"";E+=`
      <div class="kanban-column kanban-column--${w}">
        <div class="kanban-column-header">
          <span class="kanban-column-icon">${ss[w]}</span>
          <span class="kanban-column-label">${ns[w]}</span>
          ${v}
        </div>
        <div class="kanban-column-cards">
          ${I}
          ${l}
        </div>
      </div>
    `}const $={};t.querySelectorAll(".kanban-column").forEach(w=>{const S=w.classList[1]||"",v=w.querySelector(".kanban-column-cards");S&&v&&($[S]=v.scrollTop)});const N=[];let q=t;for(;q;)q.scrollTop>0&&N.push([q,q.scrollTop]),q=q.parentElement;const P={};t.querySelectorAll(".kanban-reclassify-panel").forEach(w=>{var S,v;if(!w.hasAttribute("hidden")){const l=w.closest("[data-doc-id]"),I=(l==null?void 0:l.dataset.docId)||"";if(I&&!(a!=null&&a.has(I))){const B=((S=w.querySelector("[data-field='topic']"))==null?void 0:S.value)||"",Z=((v=w.querySelector("[data-field='type']"))==null?void 0:v.value)||"";P[I]={topic:B,type:Z}}}});const H={};t.querySelectorAll(".kanban-classify-actions").forEach(w=>{var l,I;const S=w.closest("[data-doc-id]"),v=(S==null?void 0:S.dataset.docId)||"";if(v){const B=((l=w.querySelector("[data-field='topic']"))==null?void 0:l.value)||"",Z=((I=w.querySelector("[data-field='type']"))==null?void 0:I.value)||"";(B||Z)&&(H[v]={topic:B,type:Z})}}),t.innerHTML=E;for(const[w,S]of N)w.scrollTop=S;t.querySelectorAll(".kanban-column").forEach(w=>{const S=w.classList[1]||"",v=w.querySelector(".kanban-column-cards");S&&$[S]&&v&&(v.scrollTop=$[S])});for(const[w,S]of Object.entries(P)){const v=t.querySelector(`[data-doc-id="${CSS.escape(w)}"]`);if(!v)continue;const l=v.querySelector(".kanban-reclassify-toggle"),I=v.querySelector(".kanban-reclassify-panel");if(l&&I){I.removeAttribute("hidden"),l.textContent="✖";const B=I.querySelector("[data-field='topic']"),Z=I.querySelector("[data-field='type']");B&&S.topic&&(B.value=S.topic),Z&&S.type&&(Z.value=S.type)}}for(const[w,S]of Object.entries(H)){const v=t.querySelector(`[data-doc-id="${CSS.escape(w)}"]`);if(!v)continue;const l=v.querySelector(".kanban-classify-actions");if(!l)continue;const I=l.querySelector("[data-field='topic']"),B=l.querySelector("[data-field='type']");I&&S.topic&&(I.value=S.topic),B&&S.type&&(B.value=S.type)}t.querySelectorAll(".kanban-progress").forEach(w=>{var I,B;const S=Number(w.dataset.progress||0),v=((B=(I=w.closest(".kanban-card"))==null?void 0:I.querySelector(".kanban-card-stage"))==null?void 0:B.textContent)||void 0,l=cn(S,v);w.replaceWith(l)}),t.querySelectorAll(".kanban-reclassify-toggle").forEach(w=>{w.addEventListener("click",()=>{const S=w.closest(".kanban-card"),v=S==null?void 0:S.querySelector(".kanban-reclassify-panel");if(!v)return;v.hasAttribute("hidden")?(v.removeAttribute("hidden"),w.textContent="✖"):(v.setAttribute("hidden",""),w.textContent="✎")})})}async function Ce(e,t){const n=await fetch(e,t);let a=null;try{a=await n.json()}catch{a=null}if(!n.ok){const s=a&&typeof a=="object"&&"error"in a?String(a.error||n.statusText):n.statusText;throw new st(s,n.status,a)}return a}async function Ct(e,t){const{response:n,data:a}=await je(e,t);if(!n.ok){const s=a&&typeof a=="object"&&"error"in a?String(a.error||n.statusText):n.statusText;throw new st(s,n.status,a)}return a}const hs=new Set([".pdf",".md",".txt",".docx"]),vs=[".","__MACOSX"],Et=3,xt="lia_folder_pending_";function rt(e){return e.filter(t=>{const n=t.name;if(vs.some(o=>n.startsWith(o)))return!1;const a=n.lastIndexOf("."),s=a>=0?n.slice(a).toLowerCase():"";return hs.has(s)})}function ct(e,t){return e.webkitRelativePath||t.get(e)||""}function Ke(e,t){const n=ct(e,t);return`${e.name}|${e.size}|${e.lastModified??0}|${n}`}function _s(e){return e<1024?`${e} B`:e<1024*1024?`${(e/1024).toFixed(1)} KB`:`${(e/(1024*1024)).toFixed(1)} MB`}function ys(e,t){var a;const n=((a=e.preflightEntry)==null?void 0:a.existing_doc_id)||"";switch(e.verdict){case"pending":return t.t("ops.ingestion.verdict.pending");case"new":return t.t("ops.ingestion.verdict.new");case"revision":return n?t.t("ops.ingestion.verdict.revisionOf",{docId:n}):t.t("ops.ingestion.verdict.revision");case"duplicate":return n?t.t("ops.ingestion.verdict.duplicateOf",{docId:n}):t.t("ops.ingestion.verdict.duplicate");case"artifact":return t.t("ops.ingestion.verdict.artifact");case"unreadable":return t.t("ops.ingestion.verdict.unreadable")}}function $s(e,t){const n=document.createElement("span");return n.className=`ops-verdict-pill ops-verdict-pill--${e.verdict}`,n.textContent=ys(e,t),n}function mt(e){return e.documents.filter(t=>t.status==="raw"||t.status==="needs_classification").length}function ws({i18n:e,stateController:t,dom:n,withThinkingWheel:a,setFlash:s}){const{ingestionCorpusSelect:o,ingestionBatchTypeSelect:u,ingestionDropzone:c,ingestionFileInput:b,ingestionFolderInput:h,ingestionSelectFilesBtn:E,ingestionSelectFolderBtn:R,ingestionUploadProgress:$,ingestionPendingFiles:N,ingestionOverview:q,ingestionRefreshBtn:P,ingestionCreateSessionBtn:H,ingestionUploadBtn:w,ingestionProcessBtn:S,ingestionAutoProcessBtn:v,ingestionValidateBatchBtn:l,ingestionRetryBtn:I,ingestionDeleteSessionBtn:B,ingestionSessionMeta:Z,ingestionSessionsList:le,selectedSessionMeta:me,ingestionLastError:D,ingestionLastErrorMessage:ie,ingestionLastErrorGuidance:ge,ingestionLastErrorNext:F,ingestionKanban:C,ingestionLogAccordion:y,ingestionLogBody:f,ingestionLogCopyBtn:j,ingestionAutoStatus:L}=n,{state:_}=t,X=Nn(e);let be=[];function A(i){const m=`[${new Date().toISOString().slice(11,23)}] ${i}`;be.push(m),console.log(`[folder-ingest] ${i}`),y.hidden=!1,f.hidden=!1,f.textContent=be.join(`
`);const k=document.getElementById("ingestion-log-toggle");if(k){k.setAttribute("aria-expanded","true");const d=k.querySelector(".ops-log-accordion-marker");d&&(d.textContent="▾")}}function O(){be=[],Y()}function Y(){const{ingestionBounceLog:i,ingestionBounceBody:r}=n;i&&(i.hidden=!0,i.open=!1),r&&(r.textContent="")}let W=!1,ce=null;const te=150;function ne(i){if(i.length===0)return;const r=new Set(_.intake.map(k=>Ke(k.file))),m=[];for(const k of i){const d=Ke(k,_.folderRelativePaths);r.has(d)||(r.add(d),m.push({file:k,relativePath:ct(k,_.folderRelativePaths),contentHash:null,verdict:"pending",preflightEntry:null}))}m.length!==0&&(t.setIntake([..._.intake,...m]),_.reviewPlan&&t.setReviewPlan({..._.reviewPlan,stalePartial:!0}),W=!1,$e(),oe())}function $e(){ce&&clearTimeout(ce);const i=t.bumpPreflightRunId();ce=setTimeout(()=>{ce=null,Se(i)},te)}async function Se(i){if(i!==_.preflightRunId||_.intake.length===0)return;const r=_.intake.filter(m=>m.contentHash===null);try{if(r.length>0&&(await we(r),i!==_.preflightRunId))return;const m=await G();if(i!==_.preflightRunId)return;if(!m){W=!0,oe();return}Ee(m),W=!1,oe()}catch(m){if(i!==_.preflightRunId)return;console.error("[intake] preflight failed:",m),W=!0,oe()}}async function we(i){t.setPreflightScanProgress({total:i.length,hashed:0,scanning:!0}),qt();for(let r=0;r<i.length;r++){const m=i[r];try{const k=await m.file.arrayBuffer(),d=await crypto.subtle.digest("SHA-256",k),g=Array.from(new Uint8Array(d));m.contentHash=g.map(p=>p.toString(16).padStart(2,"0")).join("")}catch(k){console.warn(`[intake] hash failed for ${m.file.name}:`,k),m.verdict="unreadable",m.contentHash=""}t.setPreflightScanProgress({total:i.length,hashed:r+1,scanning:!0}),qt()}t.setPreflightScanProgress(null)}async function G(){const i=_.intake.filter(r=>r.contentHash&&r.verdict!=="unreadable").map(r=>({filename:r.file.name,relative_path:r.relativePath||r.file.name,size:r.file.size,content_hash:r.contentHash}));if(i.length===0)return{artifacts:[],duplicates:[],revisions:[],new_files:[],scanned:0,elapsed_ms:0};try{return await Cn(i,_.selectedCorpus)}catch(r){return console.error("[intake] /api/ingestion/preflight failed:",r),null}}function Ee(i){const r=new Map,m=(p,x)=>{for(const T of x){const M=T.relative_path||T.filename;r.set(M,{verdict:p,preflightEntry:T})}};m("new",i.new_files),m("revision",i.revisions),m("duplicate",i.duplicates),m("artifact",i.artifacts);const k=_.intake.map(p=>{if(p.verdict==="unreadable")return p;const x=p.relativePath||p.file.name,T=r.get(x);return T?{...p,verdict:T.verdict,preflightEntry:T.preflightEntry}:{...p,verdict:"pending"}}),d=k.filter(p=>p.verdict==="new"||p.verdict==="revision"),g=k.filter(p=>p.verdict==="duplicate"||p.verdict==="artifact"||p.verdict==="unreadable");t.setIntake(k),t.setReviewPlan({willIngest:d,bounced:g,scanned:i.scanned,elapsedMs:i.elapsed_ms,stalePartial:!1}),t.setPendingFiles(d.map(p=>p.file))}function Ie(i){const r=m=>Ke(m.file)!==Ke(i.file);if(t.setIntake(_.intake.filter(r)),_.reviewPlan){const m=_.reviewPlan.willIngest.filter(r);t.setReviewPlan({..._.reviewPlan,willIngest:m}),t.setPendingFiles(m.map(k=>k.file))}else t.setPendingFiles(_.pendingFiles.filter(m=>Ke(m)!==Ke(i.file)));oe()}function Ae(){if(!_.reviewPlan)return;const i=new Set(_.reviewPlan.willIngest.map(m=>Ke(m.file))),r=_.intake.filter(m=>!i.has(Ke(m.file)));t.setIntake(r),t.setReviewPlan({..._.reviewPlan,willIngest:[]}),t.setPendingFiles([]),oe()}function xe(){ce&&(clearTimeout(ce),ce=null),t.bumpPreflightRunId(),t.setIntake([]),t.setReviewPlan(null),t.setPendingFiles([]),t.setPreflightScanProgress(null),W=!1,_.folderRelativePaths.clear()}async function Re(){const i=_.reviewPlan;if(i&&!i.stalePartial&&i.willIngest.length!==0&&!W){s(),t.setMutating(!0),Q();try{await Sn(),xe(),h.value="",b.value=""}catch(r){t.setFolderUploadProgress(null),Fe(),s(pe(r),"error"),_.selectedSessionId&&Ge({sessionId:_.selectedSessionId,showWheel:!1,reportError:!1})}finally{t.setMutating(!1),Q()}}}const _e=new Set;function Me(){const i=_.selectedCorpus;o.innerHTML="";const r=document.createElement("option");r.value="autogenerar",r.textContent="AUTOGENERAR",r.selected=i==="autogenerar",o.appendChild(r),[..._.corpora].sort((m,k)=>m.label.localeCompare(k.label,"es")).forEach(m=>{var p;const k=document.createElement("option");k.value=m.key;const d=((p=m.attention)==null?void 0:p.length)||0;let g=m.active?m.label:`${m.label} (${e.t("ops.ingestion.corpusInactiveOption")})`;d>0&&(g+=` ⚠ ${d}`),k.textContent=g,k.selected=m.key===i,o.appendChild(k)})}function qe(){return _.selectedCorpus!=="autogenerar"?_.selectedCorpus:"autogenerar"}async function he(i){var d,g;const r=[],m=[];for(let p=0;p<i.items.length;p++){const x=(g=(d=i.items[p]).webkitGetAsEntry)==null?void 0:g.call(d);x&&m.push(x)}if(!m.some(p=>p.isDirectory))return[];async function k(p){if(p.isFile){const x=await new Promise((T,M)=>{p.file(T,M)});_.folderRelativePaths.set(x,p.fullPath.replace(/^\//,"")),r.push(x)}else if(p.isDirectory){const x=p.createReader();let T;do{T=await new Promise((M,K)=>{x.readEntries(M,K)});for(const M of T)await k(M)}while(T.length>0)}}for(const p of m)await k(p);return r}async function fe(i,r=""){const m=[];for await(const[k,d]of i.entries()){const g=r?`${r}/${k}`:k;if(d.kind==="file"){const p=await d.getFile();_.folderRelativePaths.set(p,g),m.push(p)}else if(d.kind==="directory"){const p=await fe(d,g);m.push(...p)}}return m}async function Xe(i,r,m,k=Et){let d=0,g=0,p=0,x=0;const T=[];return new Promise(M=>{function K(){for(;p<k&&x<r.length;){const V=r[x++];p++,yn(i,V,m).then(()=>{d++}).catch(U=>{g++;const J=U instanceof Error?U.message:String(U);T.push({filename:V.name,error:J}),console.error(`[folder-ingest] Upload failed: ${V.name}`,U)}).finally(()=>{p--,t.setFolderUploadProgress({total:r.length,uploaded:d,failed:g,uploading:x<r.length||p>0}),Fe(),x<r.length||p>0?K():M({uploaded:d,failed:g,errors:T})})}}t.setFolderUploadProgress({total:r.length,uploaded:0,failed:0,uploading:!0}),Fe(),K()})}function Fe(){const i=_.folderUploadProgress;if(!i||!i.uploading){$.hidden=!0,$.innerHTML="";return}const r=i.uploaded+i.failed,m=i.total>0?Math.round(r/i.total*100):0,k=Math.max(0,Math.min(Et,i.total-r));$.hidden=!1,$.innerHTML=`
      <div class="ops-upload-progress-header">
        <span>${e.t("ops.ingestion.uploadProgress",{current:r,total:i.total})}</span>
        <span>${m}%</span>
      </div>
      <div class="ops-upload-progress-bar">
        <span class="ops-upload-progress-fill" style="width:${m}%"></span>
      </div>
      <div class="ops-upload-progress-detail">
        ${e.t("ops.ingestion.uploadProgressDetail",{uploaded:i.uploaded,failed:i.failed,inflight:k})}
      </div>
    `}function Ye(i){if(_.pendingFiles.length!==0&&ct(_.pendingFiles[0])!=="")try{const r=_.pendingFiles.map(m=>({name:m.name,relativePath:ct(m),size:m.size}));localStorage.setItem(xt+i,JSON.stringify(r))}catch{}}function Qe(i){try{localStorage.removeItem(xt+i)}catch{}}function et(i){try{const r=localStorage.getItem(xt+i);if(!r)return 0;const m=JSON.parse(r);if(!Array.isArray(m))return 0;const k=_.sessions.find(g=>g.session_id===i);if(!k)return m.length;const d=new Set((k.documents||[]).map(g=>g.filename));return m.filter(g=>!d.has(g.name)).length}catch{return 0}}function ze(i,r,m){var T;const k=document.createElement("div");k.className="ops-intake-row",r.verdict==="pending"&&k.classList.add("ops-intake-row--pending"),m.readonly&&k.classList.add("ops-intake-row--readonly");const d=document.createElement("span");d.className="ops-intake-row__icon",d.textContent="📄";const g=document.createElement("span");g.className="ops-intake-row__name",g.textContent=r.relativePath||r.file.name,g.title=r.relativePath||r.file.name;const p=document.createElement("span");p.className="ops-intake-row__size",p.textContent=_s(r.file.size);const x=$s(r,e);if(k.append(d,g,p,x),m.showReason&&((T=r.preflightEntry)!=null&&T.reason)){const M=document.createElement("span");M.className="ops-intake-row__reason",M.textContent=r.preflightEntry.reason,M.title=r.preflightEntry.reason,k.appendChild(M)}if(m.removable){const M=document.createElement("button");M.type="button",M.className="ops-intake-row__remove",M.textContent="✕",M.title=e.t("ops.ingestion.willIngest.cancelAll"),M.addEventListener("click",K=>{K.stopPropagation(),Ie(r)}),k.appendChild(M)}i.appendChild(k)}function ue(i,r,m,k,d,g){const p=document.createElement("section");p.className=`ops-intake-panel ops-intake-panel--${i}`;const x=document.createElement("header");x.className="ops-intake-panel__header";const T=document.createElement("span");T.className="ops-intake-panel__title",T.textContent=e.t(r),x.appendChild(T);const M=document.createElement("span");if(M.className="ops-intake-panel__count",M.textContent=e.t(m,{count:k}),x.appendChild(M),g.readonly){const V=document.createElement("span");V.className="ops-intake-panel__readonly",V.textContent=e.t("ops.ingestion.bounced.readonly"),x.appendChild(V)}if(g.cancelAllAction){const V=document.createElement("button");V.type="button",V.className="ops-intake-panel__action",V.textContent=e.t("ops.ingestion.willIngest.cancelAll"),V.addEventListener("click",U=>{U.stopPropagation(),g.cancelAllAction()}),x.appendChild(V)}p.appendChild(x);const K=document.createElement("div");return K.className="ops-intake-panel__body",d.forEach(V=>ze(K,V,g)),p.appendChild(K),p}function ve(){var k,d;if((k=c.querySelector(".ops-intake-windows"))==null||k.remove(),(d=c.querySelector(".dropzone-file-list"))==null||d.remove(),_.intake.length===0){N.textContent=e.t("ops.ingestion.pendingNone"),N.hidden=!0,c.classList.remove("has-files");return}N.hidden=!0,c.classList.add("has-files");const i=document.createElement("div");i.className="ops-intake-windows";const r=Oe();r&&i.appendChild(r),i.appendChild(ue("intake","ops.ingestion.intake.title","ops.ingestion.intake.count",_.intake.length,_.intake,{removable:!1,readonly:!1,showReason:!1}));const m=_.reviewPlan;m&&(i.appendChild(ue("will-ingest","ops.ingestion.willIngest.title","ops.ingestion.willIngest.count",m.willIngest.length,m.willIngest,{removable:!0,readonly:!1,showReason:!1,cancelAllAction:m.willIngest.length>0?()=>Ae():void 0})),m.bounced.length>0&&i.appendChild(ue("bounced","ops.ingestion.bounced.title","ops.ingestion.bounced.count",m.bounced.length,m.bounced,{removable:!1,readonly:!0,showReason:!0}))),c.appendChild(i)}function Oe(){var p;const i=((p=_.reviewPlan)==null?void 0:p.stalePartial)===!0,r=_.intake.some(x=>x.verdict==="pending"),m=W;if(!i&&!r&&!m)return null;const k=document.createElement("div");if(k.className="ops-intake-banner",m){k.classList.add("ops-intake-banner--error");const x=document.createElement("span");x.className="ops-intake-banner__text",x.textContent=e.t("ops.ingestion.intake.failed");const T=document.createElement("button");return T.type="button",T.className="ops-intake-banner__retry",T.textContent=e.t("ops.ingestion.intake.retry"),T.addEventListener("click",M=>{M.stopPropagation(),W=!1,$e(),oe()}),k.append(x,T),k}const d=document.createElement("span");d.className="ops-intake-banner__spinner",k.appendChild(d);const g=document.createElement("span");return g.className="ops-intake-banner__text",i?(k.classList.add("ops-intake-banner--stale"),g.textContent=e.t("ops.ingestion.intake.stale")):(k.classList.add("ops-intake-banner--verifying"),g.textContent=e.t("ops.ingestion.intake.verifying")),k.appendChild(g),k}function Q(){var re,Ne,ye,it,se;const i=t.selectedCorpusConfig(),r=_.selectedSession,m=_.selectedCorpus==="autogenerar"?_.corpora.some(Le=>Le.active):!!(i!=null&&i.active),k=ht(String((r==null?void 0:r.status)||""));u.value=u.value||"autogenerar";const d=((re=_.folderUploadProgress)==null?void 0:re.uploading)??!1,g=_.reviewPlan,p=(g==null?void 0:g.willIngest.length)??0,x=(g==null?void 0:g.stalePartial)===!0,T=W===!0,M=!!g&&p>0&&!x&&!T;H.disabled=_.mutating||!m,E.disabled=_.mutating||!m||d,R.disabled=_.mutating||!m||d||k,w.disabled=_.mutating||!m||!M||d,g?p===0?w.textContent=e.t("ops.ingestion.approveNone"):w.textContent=e.t("ops.ingestion.approveCount",{count:p}):w.textContent=e.t("ops.ingestion.approve"),S.disabled=_.mutating||!m||!r||k,v.disabled=_.mutating||!m||d||!r||k,v.textContent=`▶ ${e.t("ops.ingestion.actions.autoProcess")}`;const K=Number(((Ne=r==null?void 0:r.batch_summary)==null?void 0:Ne.done)||0),V=Number(((ye=r==null?void 0:r.batch_summary)==null?void 0:ye.queued)||0)+Number(((it=r==null?void 0:r.batch_summary)==null?void 0:it.processing)||0),U=Number(((se=r==null?void 0:r.batch_summary)==null?void 0:se.pending_batch_gate)||0),J=K>=1&&(V>=1||U>=1);if(l.disabled=_.mutating||!m||!r||k||!J,I.disabled=_.mutating||!m||!r||k,B.disabled=_.mutating||!r,P.disabled=_.mutating,o.disabled=_.mutating||_.corpora.length===0,b.disabled=_.mutating||!m,!m){q.textContent=e.t("ops.ingestion.corpusInactive");return}q.textContent=e.t("ops.ingestion.overview",{active:_.corpora.filter(Le=>Le.active).length,total:_.corpora.length,corpus:_.selectedCorpus==="autogenerar"?"AUTOGENERAR":(i==null?void 0:i.label)||_.selectedCorpus,session:(r==null?void 0:r.session_id)||e.t("ops.ingestion.noSession")})}function dt(){if(le.innerHTML="",Z.textContent=_.selectedSession?`${_.selectedSession.session_id} · ${_.selectedSession.status}`:e.t("ops.ingestion.selectedEmpty"),_.sessions.length===0){const i=document.createElement("li");i.className="ops-empty",i.textContent=e.t("ops.ingestion.sessionsEmpty"),le.appendChild(i);return}_.sessions.forEach(i=>{var ye,it;const r=document.createElement("li"),m=i.status==="partial_failed",k=document.createElement("button");k.type="button",k.className=`ops-session-item${i.session_id===_.selectedSessionId?" is-active":""}${m?" has-retry-action":""}`,k.dataset.sessionId=i.session_id;const d=document.createElement("div");d.className="ops-session-item-head";const g=document.createElement("div");g.className="ops-session-id",g.textContent=i.session_id;const p=document.createElement("span");p.className=`meta-chip status-${lt(i.status)}`,p.textContent=i.status,d.append(g,p);const x=document.createElement("div");x.className="ops-session-pills";const T=((ye=_.corpora.find(se=>se.key===i.corpus))==null?void 0:ye.label)||i.corpus,M=document.createElement("span");M.className="meta-chip ops-pill-corpus",M.textContent=T,x.appendChild(M);const K=i.documents||[];[...new Set(K.map(se=>se.batch_type).filter(Boolean))].forEach(se=>{const Le=document.createElement("span");Le.className="meta-chip ops-pill-batch",Le.textContent=Zn(se,e),x.appendChild(Le)});const U=K.map(se=>se.filename).filter(Boolean);let J=null;if(U.length>0){J=document.createElement("div"),J.className="ops-session-files";const se=U.slice(0,3),Le=U.length-se.length;J.textContent=se.join(", ")+(Le>0?` +${Le}`:"")}const re=document.createElement("div");re.className="ops-session-summary",re.textContent=Wt(i.batch_summary,e);const Ne=document.createElement("div");if(Ne.className="ops-session-summary",Ne.textContent=i.updated_at?e.formatDateTime(i.updated_at,{dateStyle:"short",timeStyle:"short",timeZone:"America/Bogota"}):"-",k.appendChild(d),k.appendChild(x),J&&k.appendChild(J),k.appendChild(re),k.appendChild(Ne),(it=i.last_error)!=null&&it.code){const se=document.createElement("div");se.className="ops-session-summary status-error",se.textContent=i.last_error.code,k.appendChild(se)}if(k.addEventListener("click",async()=>{t.setSelectedSession(i),oe();try{await Ge({sessionId:i.session_id,showWheel:!0})}catch{}}),r.appendChild(k),m){const se=document.createElement("button");se.type="button",se.className="ops-session-retry-inline",se.textContent=e.t("ops.ingestion.actions.retry"),se.disabled=_.mutating,se.addEventListener("click",async Le=>{Le.stopPropagation(),se.disabled=!0,t.setMutating(!0),Q();try{await a(async()=>Tt(i.session_id)),await We({showWheel:!1,reportError:!0,focusSessionId:i.session_id}),s(e.t("ops.ingestion.flash.retryStarted",{id:i.session_id}),"success")}catch(xn){s(pe(xn),"error")}finally{t.setMutating(!1),Q()}}),r.appendChild(se)}le.appendChild(r)})}function He(i){const r=[],m=()=>new Date().toISOString();if(r.push(e.t("ops.ingestion.log.sessionHeader",{id:i.session_id})),r.push(`Corpus:     ${i.corpus||"-"}`),r.push(`Status:     ${i.status}`),r.push(`Created:    ${i.created_at||"-"}`),r.push(`Updated:    ${i.updated_at||"-"}`),r.push(`Heartbeat:  ${i.heartbeat_at??"-"}`),i.auto_processing&&r.push(`Auto-proc:  ${i.auto_processing}`),i.gate_sub_stage&&r.push(`Gate-stage: ${i.gate_sub_stage}`),i.wip_sync_status&&r.push(`WIP-sync:   ${i.wip_sync_status}`),i.batch_summary){const d=i.batch_summary,g=(i.documents||[]).filter(x=>x.status==="raw"||x.status==="needs_classification").length,p=(i.documents||[]).filter(x=>x.status==="pending_dedup").length;r.push(""),r.push("── Resumen del lote ──"),r.push(`  Total: ${d.total}  Queued: ${d.queued}  Processing: ${d.processing}  Done: ${d.done}  Failed: ${d.failed}  Duplicados: ${d.skipped_duplicate}  Bounced: ${d.bounced}`),g>0&&r.push(`  Raw (sin clasificar): ${g}`),p>0&&r.push(`  Pending dedup: ${p}`)}i.last_error&&(r.push(""),r.push("── Error de sesión ──"),r.push(`  Código:    ${i.last_error.code||"-"}`),r.push(`  Mensaje:   ${i.last_error.message||"-"}`),r.push(`  Guía:      ${i.last_error.guidance||"-"}`),r.push(`  Siguiente: ${i.last_error.next_step||"-"}`));const k=i.documents||[];if(k.length===0)r.push(""),r.push(e.t("ops.ingestion.log.noDocuments"));else{r.push(""),r.push(`── Documentos (${k.length}) ──`);const d={failed:0,processing:1,in_progress:1,queued:2,raw:2,done:3,completed:3,bounced:4,skipped_duplicate:5},g=[...k].sort((p,x)=>(d[p.status]??3)-(d[x.status]??3));for(const p of g)r.push(""),r.push(`  ┌─ ${p.filename} (${p.doc_id})`),r.push(`  │  Status:   ${p.status}  │  Stage: ${p.stage||"-"}  │  Progress: ${p.progress??0}%`),r.push(`  │  Bytes:    ${p.bytes??"-"}  │  Batch: ${p.batch_type||"-"}`),p.source_relative_path&&r.push(`  │  Path:     ${p.source_relative_path}`),(p.detected_topic||p.detected_type)&&(r.push(`  │  Topic:    ${p.detected_topic||"-"}  │  Type: ${p.detected_type||"-"}  │  Confidence: ${p.combined_confidence??"-"}`),p.classification_source&&r.push(`  │  Classifier: ${p.classification_source}`)),p.chunk_count!=null&&r.push(`  │  Chunks:   ${p.chunk_count}  │  Elapsed: ${p.elapsed_ms??"-"}ms`),p.dedup_match_type&&r.push(`  │  Dedup:    ${p.dedup_match_type}  │  Match: ${p.dedup_match_doc_id||"-"}`),p.replaced_doc_id&&r.push(`  │  Replaced: ${p.replaced_doc_id}`),p.error&&(r.push("  │  ❌ ERROR"),r.push(`  │    Código:    ${p.error.code||"-"}`),r.push(`  │    Mensaje:   ${p.error.message||"-"}`),r.push(`  │    Guía:      ${p.error.guidance||"-"}`),r.push(`  │    Siguiente: ${p.error.next_step||"-"}`)),r.push(`  │  Created: ${p.created_at||"-"}  │  Updated: ${p.updated_at||"-"}`),r.push("  └─")}return r.push(""),r.push(`Log generado: ${m()}`),r.join(`
`)}function at(){if(be.length>0)return;const i=_.selectedSession;if(!i){y.hidden=!0,f.textContent="";return}y.hidden=!1,f.textContent=He(i)}function Ue(){const i=_.selectedSession;if(!i){me.textContent=e.t("ops.ingestion.selectedEmpty"),D.hidden=!0,be.length===0&&(y.hidden=!0),C.innerHTML="";return}const r=et(i.session_id),m=r>0?` · ${e.t("ops.ingestion.folderResumePending",{count:r})}`:"";if(me.textContent=`${i.session_id} · ${Wt(i.batch_summary,e)}${m}`,i.last_error?(D.hidden=!1,ie.textContent=i.last_error.message||i.last_error.code||"-",ge.textContent=i.last_error.guidance||"",F.textContent=`${e.t("ops.ingestion.lastErrorNext")}: ${i.last_error.next_step||"-"}`):D.hidden=!0,(i.documents||[]).length===0){C.innerHTML=`<p class="ops-empty">${e.t("ops.ingestion.documentsEmpty")}</p>`,C.style.minHeight="0",at();return}C.style.minHeight="",fs(i,C,e,_e,_.corpora),_e.clear(),at()}function oe(){Me(),ve(),Q(),dt(),Ue()}async function ut(){const i=await Pe("/api/corpora"),r=Array.isArray(i.corpora)?i.corpora:[];t.setCorpora(r);const m=new Set(r.map(k=>k.key));m.add("autogenerar"),m.has(_.selectedCorpus)||t.setSelectedCorpus("autogenerar")}async function _n(){const i=await Pe("/api/ingestion/sessions?limit=20");return Array.isArray(i.sessions)?i.sessions:[]}async function tt(i){const r=await Pe(`/api/ingestion/sessions/${encodeURIComponent(i)}`);if(!r.session)throw new Error("missing_session");return r.session}async function yt(i){const r=await Ct("/api/ingestion/sessions",{corpus:i});if(!r.session)throw new Error("missing_session");return r.session}async function yn(i,r,m){const k=o.value==="autogenerar"?"":o.value,d={"Content-Type":"application/octet-stream","X-Upload-Filename":r.name,"X-Upload-Mime":r.type||"application/octet-stream","X-Upload-Batch-Type":m};k&&(d["X-Upload-Topic"]=k);const g=ct(r,_.folderRelativePaths);g&&(d["X-Upload-Relative-Path"]=g),console.log(`[upload] ${r.name} (${r.size}B) → session=${i} batch=${m}`);const p=await fetch(`/api/ingestion/sessions/${encodeURIComponent(i)}/files`,{method:"POST",headers:d,body:r}),x=await p.text();let T;try{T=JSON.parse(x)}catch{throw console.error(`[upload] ${r.name} — response not JSON (${p.status}):`,x.slice(0,300)),new Error(`Upload response not JSON: ${p.status} ${x.slice(0,100)}`)}if(!p.ok){const M=T.error||p.statusText;throw console.error(`[upload] ${r.name} — HTTP ${p.status}:`,M),new st(M,p.status,T)}if(!T.document)throw console.error(`[upload] ${r.name} — no document in response:`,T),new Error("missing_document");return console.log(`[upload] ${r.name} → OK doc_id=${T.document.doc_id} status=${T.document.status}`),T.document}async function pt(i){return Ce(`/api/ingestion/sessions/${encodeURIComponent(i)}/process`,{method:"POST"})}async function Lt(i){return Ce(`/api/ingestion/sessions/${encodeURIComponent(i)}/validate-batch`,{method:"POST"})}async function Tt(i){return Ce(`/api/ingestion/sessions/${encodeURIComponent(i)}/retry`,{method:"POST"})}async function $n(i,r=!1){const m=r?"?force=true":"";return Ce(`/api/ingestion/sessions/${encodeURIComponent(i)}${m}`,{method:"DELETE"})}async function We({showWheel:i=!0,reportError:r=!0,focusSessionId:m=""}={}){const k=async()=>{await ut(),oe();let d=await _n();const g=m||_.selectedSessionId;if(g&&!d.some(p=>p.session_id===g))try{d=[await tt(g),...d.filter(x=>x.session_id!==g)]}catch{g===_.selectedSessionId&&t.setSelectedSession(null)}t.setSessions(d.sort((p,x)=>Date.parse(String(x.updated_at||0))-Date.parse(String(p.updated_at||0)))),t.syncSelectedSession(),oe()};try{i?await a(k):await k()}catch(d){throw r&&s(pe(d),"error"),oe(),d}}async function Ge({sessionId:i,showWheel:r=!1,reportError:m=!0}){const k=async()=>{const d=await tt(i);t.upsertSession(d),oe()};try{r?await a(k):await k()}catch(d){throw m&&s(pe(d),"error"),d}}async function wn(){var r,m,k,d;const i=qe();if(console.log(`[folder-ingest] ensureSelectedSession: effectiveCorpus="${i}", selectedSession=${((r=_.selectedSession)==null?void 0:r.session_id)||"null"} (status=${((m=_.selectedSession)==null?void 0:m.status)||"null"}, corpus=${((k=_.selectedSession)==null?void 0:k.corpus)||"null"})`),_.selectedSession&&!Ut(_.selectedSession)&&_.selectedSession.status!=="completed"&&(_.selectedSession.corpus===i||i==="autogenerar"))return console.log(`[folder-ingest] Reusing session ${_.selectedSession.session_id}`),_.selectedSession;A(`Creando sesión con corpus="${i}"...`);try{const g=await yt(i);return A(`Sesión creada: ${g.session_id} (corpus=${g.corpus})`),t.upsertSession(g),g}catch(g){if(A(`Creación falló para corpus="${i}": ${g instanceof Error?g.message:String(g)}`),i==="autogenerar"){const p=((d=_.corpora.find(T=>T.active))==null?void 0:d.key)||"declaracion_renta";A(`Reintentando con corpus="${p}"...`);const x=await yt(p);return A(`Sesión fallback: ${x.session_id} (corpus=${x.corpus})`),t.upsertSession(x),x}throw g}}const kn=4e3;let ot=null,$t="";function Ze(){ot&&(clearTimeout(ot),ot=null),$t="",L.hidden=!0,L.classList.remove("is-running")}function wt(i){const r=i.batch_summary,m=mt(i),k=Math.max(0,Number(r.queued??0)-m),d=Number(r.processing??0),g=Number(r.done??0),p=Number(r.failed??0),x=Number(r.bounced??0),T=k+d;L.hidden=!1;const M=x>0?` · ${x} rebotados`:"";T>0||m>0?(L.classList.add("is-running"),L.textContent=e.t("ops.ingestion.auto.running",{queued:k,processing:d,raw:m})+M):p>0?(L.classList.remove("is-running"),L.textContent=e.t("ops.ingestion.auto.done",{done:g,failed:p,raw:m})+M):(L.classList.remove("is-running"),L.textContent=e.t("ops.ingestion.auto.allDone",{done:g})+M)}async function Rt(){const i=$t;if(i)try{const r=await tt(i);t.upsertSession(r),oe(),wt(r);const m=r.batch_summary,k=mt(r),d=Number(m.total??0);if(d===0){Ze();return}k>0&&await Ce(`/api/ingestion/sessions/${encodeURIComponent(i)}/auto-process`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({max_concurrency:5})});const g=k>0?await tt(i):r,p=mt(g),x=Math.max(0,Number(g.batch_summary.queued??0)-p),T=Number(g.batch_summary.processing??0);x>0&&T===0&&await pt(i),k>0&&(t.upsertSession(g),oe(),wt(g));const M=x+T;if(d>0&&M===0&&p===0){if(Number(g.batch_summary.pending_batch_gate??0)>0&&g.status!=="running_batch_gates"&&g.status!=="completed")try{await Lt(i)}catch{}const V=await tt(i);t.upsertSession(V),oe(),wt(V),Ze(),s(e.t("ops.ingestion.auto.allDone",{done:Number(V.batch_summary.done??0)}),"success");return}if(M===0&&p>0){L.classList.remove("is-running"),L.textContent=e.t("ops.ingestion.auto.done",{done:Number(g.batch_summary.done??0),failed:Number(g.batch_summary.failed??0),raw:p}),Ze();return}ot=setTimeout(()=>void Rt(),kn)}catch(r){Ze(),s(pe(r),"error")}}function Mt(i){Ze(),$t=i,L.hidden=!1,L.classList.add("is-running"),L.textContent=e.t("ops.ingestion.auto.running",{queued:0,processing:0,raw:0}),ot=setTimeout(()=>void Rt(),2e3)}async function Sn(){var K,V,U;A(`directFolderIngest: ${_.pendingFiles.length} archivos pendientes`);const i=await wn();A(`Sesión asignada: ${i.session_id} (corpus=${i.corpus}, status=${i.status})`);const r=u.value||"autogenerar";A(`Subiendo ${_.pendingFiles.length} archivos con batchType="${r}"...`),Ye(i.session_id);const m=await Xe(i.session_id,[..._.pendingFiles],r,Et);if(console.log("[folder-ingest] Upload result:",{uploaded:m.uploaded,failed:m.failed}),A(`Upload completo: ${m.uploaded} subidos, ${m.failed} fallidos${m.errors.length>0?" — "+m.errors.slice(0,5).map(J=>`${J.filename}: ${J.error}`).join("; "):""}`),t.setPendingFiles([]),t.setFolderUploadProgress(null),Qe(i.session_id),h.value="",b.value="",m.failed>0&&m.uploaded===0){const J=m.errors.slice(0,3).map(re=>`${re.filename}: ${re.error}`).join("; ");A(`TODOS FALLARON: ${J}`),s(`${e.t("ops.ingestion.flash.folderUploadPartial",m)} — ${J}`,"error"),await We({showWheel:!1,reportError:!0,focusSessionId:i.session_id});return}A("Consultando estado de sesión post-upload...");const k=await tt(i.session_id),d=Number(((K=k.batch_summary)==null?void 0:K.bounced)??0),g=mt(k),p=Number(((V=k.batch_summary)==null?void 0:V.queued)??0),x=Number(((U=k.batch_summary)==null?void 0:U.total)??0),T=x-d;if(A(`Sesión post-upload: total=${x} bounced=${d} raw=${g} queued=${p} actionable=${T}`),T===0&&d>0){A(`TODOS REBOTADOS: ${d} archivos ya existen en el corpus`),t.upsertSession(k),s(`${d} archivos ya existen en el corpus (rebotados). 0 archivos nuevos para procesar.`,"error"),A("--- FIN (todo rebotado) ---");return}A("Auto-procesando con threshold=0 (force-queue)..."),await Ce(`/api/ingestion/sessions/${encodeURIComponent(i.session_id)}/auto-process`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({max_concurrency:5,auto_accept_threshold:0})}),await pt(i.session_id),await We({showWheel:!1,reportError:!0,focusSessionId:i.session_id});const M=[];m.uploaded>0&&M.push(`${T} archivos en proceso`),d>0&&M.push(`${d} rebotados`),m.failed>0&&M.push(`${m.failed} fallidos`),s(M.join(" · "),m.failed>0?"error":"success"),A(`Auto-piloto iniciado para ${i.session_id}`),A("--- FIN (éxito) ---"),Mt(i.session_id)}async function Cn(i,r){return(await Ct("/api/ingestion/preflight",{corpus:r,files:i})).manifest}function qt(){const i=_.preflightScanProgress;if(!i||!i.scanning){$.hidden=!0,$.innerHTML="";return}const r=i.total>0?Math.round(i.hashed/i.total*100):0;$.hidden=!1,$.innerHTML=`
      <div class="ops-preflight-scan">
        <div class="ops-preflight-scan-header">
          <span>${e.t("ops.ingestion.preflight.scanning",{hashed:i.hashed,total:i.total})}</span>
          <span>${r}%</span>
        </div>
        <div class="ops-preflight-scan-bar">
          <span class="ops-preflight-scan-fill" style="width:${r}%"></span>
        </div>
        <div class="ops-preflight-scan-detail">${e.t("ops.ingestion.preflight.scanningDetail")}</div>
      </div>
    `}function En(){c.addEventListener("click",()=>{b.disabled||b.click()}),c.addEventListener("keydown",d=>{d.key!=="Enter"&&d.key!==" "||(d.preventDefault(),b.disabled||b.click())});let i=0;c.addEventListener("dragenter",d=>{d.preventDefault(),i++,b.disabled||c.classList.add("is-dragover")}),c.addEventListener("dragover",d=>{d.preventDefault()}),c.addEventListener("dragleave",()=>{i--,i<=0&&(i=0,c.classList.remove("is-dragover"))}),c.addEventListener("drop",async d=>{var x;if(d.preventDefault(),i=0,c.classList.remove("is-dragover"),b.disabled)return;const g=d.dataTransfer;if(g){const T=await he(g);if(T.length>0){ne(rt(T));return}}const p=Array.from(((x=d.dataTransfer)==null?void 0:x.files)||[]);p.length!==0&&ne(rt(p))}),b.addEventListener("change",()=>{const d=Array.from(b.files||[]);d.length!==0&&ne(rt(d))}),h.addEventListener("change",()=>{const d=Array.from(h.files||[]);d.length!==0&&ne(rt(d))}),E.addEventListener("click",()=>{b.disabled||b.click()}),R.addEventListener("click",async()=>{if(!h.disabled){if(typeof window.showDirectoryPicker=="function")try{const d=await window.showDirectoryPicker({mode:"read"}),g=await fe(d,d.name),p=rt(g);p.length>0?ne(p):s(e.t("ops.ingestion.pendingNone"),"error");return}catch(d){if((d==null?void 0:d.name)==="AbortError")return}h.click()}}),o.addEventListener("change",()=>{t.setSelectedCorpus(o.value),t.setSessions([]),t.setSelectedSession(null),xe(),s(),oe(),We({showWheel:!0,reportError:!0})}),P.addEventListener("click",d=>{d.stopPropagation(),s(),We({showWheel:!0,reportError:!0})}),H.addEventListener("click",async()=>{Ze(),s(),xe(),t.setPreflightManifest(null),t.setFolderUploadProgress(null),_.rejectedArtifacts=[],$.hidden=!0,$.innerHTML="",b.value="",h.value="",D.hidden=!0,O(),y.hidden=!0,f.textContent="",t.setMutating(!0),Q();try{const d=await a(async()=>yt(qe()));t.upsertSession(d),oe(),s(e.t("ops.ingestion.flash.sessionCreated",{id:d.session_id}),"success")}catch(d){s(pe(d),"error")}finally{t.setMutating(!1),Q()}}),w.addEventListener("click",()=>{Re()}),S.addEventListener("click",async()=>{const d=_.selectedSessionId;if(d){s(),t.setMutating(!0),Q();try{await a(async()=>pt(d)),await Ge({sessionId:d,showWheel:!1,reportError:!1});const g=e.t("ops.ingestion.flash.processStarted",{id:d});s(g,"success"),X.show({message:g,tone:"success"})}catch(g){const p=pe(g);s(p,"error"),X.show({message:p,tone:"error"})}finally{t.setMutating(!1),Q()}}}),l.addEventListener("click",async()=>{const d=_.selectedSessionId;if(d){s(),t.setMutating(!0),Q();try{await a(async()=>Lt(d)),await Ge({sessionId:d,showWheel:!1,reportError:!1});const g="Validación de lote iniciada";s(g,"success"),X.show({message:g,tone:"success"})}catch(g){const p=pe(g);s(p,"error"),X.show({message:p,tone:"error"})}finally{t.setMutating(!1),Q()}}}),I.addEventListener("click",async()=>{const d=_.selectedSessionId;if(d){s(),t.setMutating(!0),Q();try{await a(async()=>Tt(d)),await Ge({sessionId:d,showWheel:!1,reportError:!1}),s(e.t("ops.ingestion.flash.retryStarted",{id:d}),"success")}catch(g){s(pe(g),"error")}finally{t.setMutating(!1),Q()}}}),B.addEventListener("click",async()=>{var T;const d=_.selectedSessionId;if(!d)return;const g=Ut(_.selectedSession),p=g?e.t("ops.ingestion.confirm.ejectPostGate"):e.t("ops.ingestion.confirm.ejectPreGate");if(await X.confirm({title:e.t("ops.ingestion.actions.discardSession"),message:p,tone:"caution",confirmLabel:e.t("ops.ingestion.confirm.ejectLabel")})){Ze(),s(),t.setMutating(!0),Q();try{const M=ht(String(((T=_.selectedSession)==null?void 0:T.status)||"")),K=await a(async()=>$n(d,M||g));t.clearSelectionAfterDelete(),xe(),t.setPreflightManifest(null),t.setFolderUploadProgress(null),_.rejectedArtifacts=[],$.hidden=!0,$.innerHTML="",b.value="",h.value="",D.hidden=!0,O(),y.hidden=!0,f.textContent="",await We({showWheel:!1,reportError:!1});const V=Array.isArray(K.errors)&&K.errors.length>0,U=K.path==="rollback"?e.t("ops.ingestion.flash.ejectedRollback",{id:d,count:K.ejected_files}):e.t("ops.ingestion.flash.ejectedInstant",{id:d,count:K.ejected_files}),J=V?"caution":"success";s(U,V?"error":"success"),X.show({message:U,tone:J}),V&&X.show({message:e.t("ops.ingestion.flash.ejectedPartial"),tone:"caution",durationMs:8e3})}catch(M){const K=pe(M);s(K,"error"),X.show({message:K,tone:"error"})}finally{t.setMutating(!1),oe()}}}),v.addEventListener("click",async()=>{const d=_.selectedSessionId;if(d){s(),t.setMutating(!0),Q();try{await a(async()=>Ce(`/api/ingestion/sessions/${encodeURIComponent(d)}/auto-process`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({max_concurrency:5})})),await pt(d),await Ge({sessionId:d,showWheel:!1,reportError:!1}),s(`Auto-procesamiento iniciado para ${d}`,"success"),Mt(d)}catch(g){s(pe(g),"error")}finally{t.setMutating(!1),Q()}}});const r=document.getElementById("ingestion-log-toggle");r&&(r.addEventListener("click",d=>{if(d.target.closest(".ops-log-copy-btn"))return;const g=f.hidden;f.hidden=!g,r.setAttribute("aria-expanded",String(g));const p=r.querySelector(".ops-log-accordion-marker");p&&(p.textContent=g?"▾":"▸")}),r.addEventListener("keydown",d=>{(d.key==="Enter"||d.key===" ")&&(d.preventDefault(),r.click())})),j.addEventListener("click",d=>{d.preventDefault(),d.stopPropagation();const g=f.textContent||"";navigator.clipboard.writeText(g).then(()=>{const p=j.textContent;j.textContent=e.t("ops.ingestion.log.copied"),setTimeout(()=>{j.textContent=p},1500)}).catch(()=>{const p=document.createRange();p.selectNodeContents(f);const x=window.getSelection();x==null||x.removeAllRanges(),x==null||x.addRange(p)})}),C.addEventListener("click",async d=>{var V;const g=d.target.closest("[data-action]");if(!g)return;const p=g.getAttribute("data-action"),x=g.getAttribute("data-doc-id"),T=_.selectedSessionId;if(!T||!x)return;if(p==="show-existing-dropdown"){const U=g.closest(".kanban-card"),J=U==null?void 0:U.querySelector(".kanban-ag-fallback-panel");J&&(J.hidden=!J.hidden);return}let M="",K="";if(p==="assign"){const U=g.closest(".kanban-card"),J=U==null?void 0:U.querySelector("[data-field='topic']"),re=U==null?void 0:U.querySelector("[data-field='type']");if(M=(J==null?void 0:J.value)||"",K=(re==null?void 0:re.value)||"",!M||!K){J&&!M&&J.classList.add("kanban-select--invalid"),re&&!K&&re.classList.add("kanban-select--invalid");return}}s(),t.setMutating(!0),Q();try{switch(p){case"assign":{await a(async()=>Ce(`/api/ingestion/sessions/${encodeURIComponent(T)}/documents/${encodeURIComponent(x)}/classify`,{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify({topic:M,batch_type:K})})),_e.add(x);break}case"replace-dup":{await a(async()=>Ce(`/api/ingestion/sessions/${encodeURIComponent(T)}/documents/${encodeURIComponent(x)}/resolve-duplicate`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action:"replace"})}));break}case"add-new-dup":{await a(async()=>Ce(`/api/ingestion/sessions/${encodeURIComponent(T)}/documents/${encodeURIComponent(x)}/resolve-duplicate`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action:"add_new"})}));break}case"discard-dup":case"discard":{await a(async()=>Ce(`/api/ingestion/sessions/${encodeURIComponent(T)}/documents/${encodeURIComponent(x)}/resolve-duplicate`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action:"discard"})}));break}case"accept-synonym":{const U=g.closest(".kanban-card"),J=U==null?void 0:U.querySelector("[data-field='type']"),re=(J==null?void 0:J.value)||"";await a(async()=>Ce(`/api/ingestion/sessions/${encodeURIComponent(T)}/documents/${encodeURIComponent(x)}/accept-autogenerar`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action:"accept_synonym",type:re||void 0})})),_e.add(x);break}case"accept-new-topic":{const U=g.closest(".kanban-card"),J=U==null?void 0:U.querySelector("[data-field='autogenerar-label']"),re=U==null?void 0:U.querySelector("[data-field='type']"),Ne=((V=J==null?void 0:J.value)==null?void 0:V.trim())||"",ye=(re==null?void 0:re.value)||"";if(!Ne||Ne.length<3){J&&J.classList.add("kanban-select--invalid");return}await a(async()=>Ce(`/api/ingestion/sessions/${encodeURIComponent(T)}/documents/${encodeURIComponent(x)}/accept-autogenerar`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action:"accept_new_topic",edited_label:Ne,type:ye||void 0})})),_e.add(x),await ut(),Me();break}case"retry":{await a(async()=>Ce(`/api/ingestion/sessions/${encodeURIComponent(T)}/documents/${encodeURIComponent(x)}/retry`,{method:"POST"}));break}case"remove":break}await Ge({sessionId:T,showWheel:!1,reportError:!1})}catch(U){s(pe(U),"error")}finally{t.setMutating(!1),Q()}});const m=n.addCorpusDialog,k=n.addCorpusBtn;if(m&&k){let d=function(U){return U.normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase().replace(/[^a-z0-9]+/g,"_").replace(/^_|_$/g,"")};const g=m.querySelector("#add-corpus-label"),p=m.querySelector("#add-corpus-key"),x=m.querySelector("#add-corpus-kw-strong"),T=m.querySelector("#add-corpus-kw-weak"),M=m.querySelector("#add-corpus-error"),K=m.querySelector("#add-corpus-cancel"),V=m.querySelector("#add-corpus-form");k.addEventListener("click",()=>{g&&(g.value=""),p&&(p.value=""),x&&(x.value=""),T&&(T.value=""),M&&(M.hidden=!0),m.showModal(),g==null||g.focus()}),g==null||g.addEventListener("input",()=>{p&&(p.value=d(g.value))}),K==null||K.addEventListener("click",()=>{m.close()}),V==null||V.addEventListener("submit",async U=>{U.preventDefault(),M&&(M.hidden=!0);const J=(g==null?void 0:g.value.trim())||"";if(!J)return;const re=((x==null?void 0:x.value)||"").split(",").map(ye=>ye.trim()).filter(Boolean),Ne=((T==null?void 0:T.value)||"").split(",").map(ye=>ye.trim()).filter(Boolean);try{await a(async()=>Ct("/api/corpora",{label:J,keywords_strong:re.length?re:void 0,keywords_weak:Ne.length?Ne:void 0})),m.close(),await We({showWheel:!1,reportError:!1});const ye=d(J);ye&&t.setSelectedCorpus(ye),oe(),s(`Categoría "${J}" creada.`,"success")}catch(ye){M&&(M.textContent=pe(ye),M.hidden=!1)}})}}return{bindEvents:En,refreshIngestion:We,refreshSelectedSession:Ge,render:oe}}function Ve(e){if(e==null)return null;const t=Number(e);return!Number.isFinite(t)||t<0?null:t}function mn({i18n:e,stateController:t,dom:n,withThinkingWheel:a,setFlash:s}){const{monitorTabBtn:o,ingestionTabBtn:u,controlTabBtn:c,embeddingsTabBtn:b,reindexTabBtn:h,monitorPanel:E,ingestionPanel:R,controlPanel:$,embeddingsPanel:N,reindexPanel:q,runsBody:P,timelineNode:H,timelineMeta:w,cascadeNote:S,userCascadeNode:v,userCascadeSummary:l,technicalCascadeNode:I,technicalCascadeSummary:B,refreshRunsBtn:Z}=n,{state:le}=t;function me(A){const O=Ve(A);return O===null?"-":`${e.formatNumber(O/1e3,{minimumFractionDigits:2,maximumFractionDigits:2})} s`}function D(A){t.setActiveTab(A),ie()}function ie(){if(!o)return;const A=le.activeTab;o.classList.toggle("is-active",A==="monitor"),o.setAttribute("aria-selected",String(A==="monitor")),u==null||u.classList.toggle("is-active",A==="ingestion"),u==null||u.setAttribute("aria-selected",String(A==="ingestion")),c==null||c.classList.toggle("is-active",A==="control"),c==null||c.setAttribute("aria-selected",String(A==="control")),b==null||b.classList.toggle("is-active",A==="embeddings"),b==null||b.setAttribute("aria-selected",String(A==="embeddings")),h==null||h.classList.toggle("is-active",A==="reindex"),h==null||h.setAttribute("aria-selected",String(A==="reindex")),E&&(E.hidden=A!=="monitor",E.classList.toggle("is-active",A==="monitor")),R&&(R.hidden=A!=="ingestion",R.classList.toggle("is-active",A==="ingestion")),$&&($.hidden=A!=="control",$.classList.toggle("is-active",A==="control")),N&&(N.hidden=A!=="embeddings",N.classList.toggle("is-active",A==="embeddings")),q&&(q.hidden=A!=="reindex",q.classList.toggle("is-active",A==="reindex"))}function ge(A){if(H.innerHTML="",!Array.isArray(A)||A.length===0){H.innerHTML=`<li>${e.t("ops.timeline.empty")}</li>`;return}A.forEach(O=>{const Y=document.createElement("li");Y.innerHTML=`
        <strong>${O.stage||"-"}</strong> · <span class="status-${lt(String(O.status||""))}">${O.status||"-"}</span><br/>
        <small>${O.at||"-"} · ${O.duration_ms||0} ms</small>
        <pre>${JSON.stringify(O.details||{},null,2)}</pre>
      `,H.appendChild(Y)})}function F(A,O,Y){const W=Ve(O==null?void 0:O.total_ms),ce=W===null?e.t("ops.timeline.summaryPending"):me(W),te=Y==="user"&&String((O==null?void 0:O.chat_run_id)||"").trim()?` · chat_run ${String((O==null?void 0:O.chat_run_id)||"").trim()}`:"";A.textContent=`${e.t("ops.timeline.totalLabel")} ${ce}${te}`}function C(A){var ne,$e,Se;const O=[],Y=String(((ne=A.details)==null?void 0:ne.source)||"").trim(),W=String(A.status||"").trim();Y&&O.push(Y),W&&W!=="ok"&&W!=="missing"&&O.push(W);const ce=Number((($e=A.details)==null?void 0:$e.citations_count)||0);Number.isFinite(ce)&&ce>0&&O.push(`${ce} refs`);const te=String(((Se=A.details)==null?void 0:Se.panel_status)||"").trim();return te&&O.push(te),O.join(" · ")}function y(A,O,Y){A.innerHTML="";const W=Array.isArray(O==null?void 0:O.steps)?(O==null?void 0:O.steps)||[]:[];if(W.length===0){A.innerHTML=`<li class="ops-cascade-step is-empty">${e.t("ops.timeline.waterfallEmpty")}</li>`;return}const ce=Ve(O==null?void 0:O.total_ms)??Math.max(1,...W.map(te=>Ve(te.cumulative_ms)??Ve(te.absolute_elapsed_ms)??0));W.forEach(te=>{const ne=Ve(te.duration_ms),$e=Ve(te.offset_ms)??0,Se=Ve(te.absolute_elapsed_ms),we=document.createElement("li");we.className=`ops-cascade-step ops-cascade-step--${Y}${ne===null?" is-missing":""}`;const G=document.createElement("div");G.className="ops-cascade-step-head";const Ee=document.createElement("div"),Ie=document.createElement("strong");Ie.textContent=te.label||"-";const Ae=document.createElement("small");Ae.className="ops-cascade-step-meta",Ae.textContent=ne===null?e.t("ops.timeline.missingStep"):`${e.t("ops.timeline.stepLabel")} ${me(ne)} · T+${me(Se??te.cumulative_ms)}`,Ee.append(Ie,Ae);const xe=document.createElement("span");xe.className=`meta-chip status-${lt(String(te.status||""))}`,xe.textContent=String(te.status||(ne===null?"missing":"ok")),G.append(Ee,xe),we.appendChild(G);const Re=document.createElement("div");Re.className="ops-cascade-track";const _e=document.createElement("span");_e.className="ops-cascade-segment";const Me=Math.max(0,Math.min(100,$e/ce*100)),qe=ne===null?0:Math.max(ne/ce*100,ne>0?2.5:0);_e.style.left=`${Me}%`,_e.style.width=`${qe}%`,_e.setAttribute("aria-label",ne===null?`${te.label}: ${e.t("ops.timeline.missingStep")}`:`${te.label}: ${me(ne)}`),Re.appendChild(_e),we.appendChild(Re);const he=C(te);if(he){const fe=document.createElement("p");fe.className="ops-cascade-step-detail",fe.textContent=he,we.appendChild(fe)}A.appendChild(we)})}async function f(){return(await Pe("/api/ops/runs?limit=30")).runs||[]}async function j(A){return Pe(`/api/ops/runs/${encodeURIComponent(A)}/timeline`)}function L(A,O){var W;const Y=A.run||{};w.textContent=e.t("ops.timeline.label",{id:O}),S.textContent=e.t("ops.timeline.selectedRunMeta",{trace:String(Y.trace_id||"-"),chatRun:String(((W=A.user_waterfall)==null?void 0:W.chat_run_id)||Y.chat_run_id||"-")}),F(l,A.user_waterfall,"user"),F(B,A.technical_waterfall,"technical"),y(v,A.user_waterfall,"user"),y(I,A.technical_waterfall,"technical"),ge(Array.isArray(A.timeline)?A.timeline:[])}function _(A){if(P.innerHTML="",!Array.isArray(A)||A.length===0){const O=document.createElement("tr");O.innerHTML=`<td colspan="4">${e.t("ops.runs.empty")}</td>`,P.appendChild(O);return}A.forEach(O=>{const Y=document.createElement("tr");Y.innerHTML=`
        <td><button type="button" class="link-btn" data-run-id="${O.run_id}">${O.run_id}</button></td>
        <td>${O.trace_id||"-"}</td>
        <td class="status-${lt(String(O.status||""))}">${O.status||"-"}</td>
        <td>${O.started_at?e.formatDateTime(O.started_at,{dateStyle:"short",timeStyle:"short",timeZone:"America/Bogota"}):"-"}</td>
      `,P.appendChild(Y)}),P.querySelectorAll("button[data-run-id]").forEach(O=>{O.addEventListener("click",async()=>{const Y=O.getAttribute("data-run-id")||"";try{const W=await a(async()=>j(Y));L(W,Y)}catch(W){v.innerHTML=`<li class="ops-cascade-step is-empty status-error">${pe(W)}</li>`,I.innerHTML=`<li class="ops-cascade-step is-empty status-error">${pe(W)}</li>`,H.innerHTML=`<li class="status-error">${pe(W)}</li>`}})})}async function X({showWheel:A=!0,reportError:O=!0}={}){const Y=async()=>{const W=await f();_(W)};try{A?await a(Y):await Y()}catch(W){P.innerHTML=`<tr><td colspan="4" class="status-error">${pe(W)}</td></tr>`,O&&s(pe(W),"error")}}function be(){o==null||o.addEventListener("click",()=>{D("monitor")}),u==null||u.addEventListener("click",()=>{D("ingestion")}),c==null||c.addEventListener("click",()=>{D("control")}),b==null||b.addEventListener("click",()=>{D("embeddings")}),h==null||h.addEventListener("click",()=>{D("reindex")}),Z.addEventListener("click",()=>{s(),X({showWheel:!0,reportError:!0})})}return{bindEvents:be,refreshRuns:X,renderTabs:ie}}function Be(e){return String(e??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#39;")}function nt(e){return(e??0).toLocaleString("es-CO")}function ks(e){if(e==null||e<=0)return"-";const t=Math.floor(e/60),n=Math.floor(e%60);return t>0?`${t}m ${n}s`:`${n}s`}function Ss(e){if(!e.length)return"";let t='<ol class="reindex-stage-list">';for(const n of e){const a=n.state==="completed"?"ops-dot-ok":n.state==="active"?"ops-dot-active":n.state==="failed"?"ops-dot-error":"ops-dot-pending",s=n.state==="active"?`<strong>${Be(n.label)}</strong>`:Be(n.label);t+=`<li class="reindex-stage-item reindex-stage-${n.state}"><span class="ops-dot ${a}">●</span> ${s}</li>`}return t+="</ol>",t}function gn({dom:e,setFlash:t,navigateToEmbeddings:n}){const{container:a}=e;let s=null,o="";function u(){var S,v,l;const R=s;if(!R){a.innerHTML='<p class="ops-text-muted">Cargando estado de re-index...</p>';return}const $=R.current_operation||R.last_operation,N=((S=R.current_operation)==null?void 0:S.status)==="running",q=!R.current_operation;let P="";const H=N?"En ejecución":q?"Inactivo":($==null?void 0:$.status)??"—",w=N?"tone-yellow":($==null?void 0:$.status)==="completed"?"tone-green":($==null?void 0:$.status)==="failed"?"tone-red":"";if(P+=`<div class="reindex-status-row">
      <span class="corpus-status-chip ${w}">${Be(H)}</span>
      <span class="emb-target-badge">WIP</span>
      ${N?`<span class="emb-heartbeat ${Pt($==null?void 0:$.heartbeat_at,$==null?void 0:$.updated_at)}">${Pt($==null?void 0:$.heartbeat_at,$==null?void 0:$.updated_at)}</span>`:""}
    </div>`,P+='<div class="reindex-controls">',q&&(P+=`<button class="corpus-btn corpus-btn-promote" id="reindex-start-btn" ${o?"disabled":""}>Iniciar re-index</button>`),N&&$&&(P+=`<button class="corpus-btn corpus-btn-rollback" id="reindex-stop-btn" ${o?"disabled":""}>Detener</button>`),P+="</div>",(v=$==null?void 0:$.stages)!=null&&v.length&&(P+=Ss($.stages)),$!=null&&$.progress){const I=$.progress,B=[];I.documents_processed!=null&&B.push(`Documentos: ${nt(I.documents_processed)} / ${nt(I.documents_total)}`),I.documents_indexed!=null&&B.push(`Documentos indexados: ${nt(I.documents_indexed)}`),I.elapsed_seconds!=null&&B.push(`Tiempo: ${ks(I.elapsed_seconds)}`),B.length&&(P+=`<div class="reindex-progress-stats">${B.map(Z=>`<span>${Be(Z)}</span>`).join("")}</div>`)}if($!=null&&$.quality_report){const I=$.quality_report;if(P+='<div class="reindex-quality-report">',P+="<h3>Reporte de calidad</h3>",P+=`<div class="emb-stats-grid">
        <div class="emb-stat"><span class="emb-stat-value">${nt(I.documents_indexed)}</span><span class="emb-stat-label">Documentos</span></div>
        <div class="emb-stat"><span class="emb-stat-value">${nt(I.chunks_generated)}</span><span class="emb-stat-label">Chunks</span></div>
        <div class="emb-stat"><span class="emb-stat-value">${I.blocking_issues??0}</span><span class="emb-stat-label">Blocking issues</span></div>
      </div>`,I.knowledge_class_counts){P+='<div class="reindex-kc-breakdown"><h4>Knowledge classes</h4><dl class="reindex-kc-dl">';for(const[B,Z]of Object.entries(I.knowledge_class_counts))P+=`<dt>${Be(B)}</dt><dd>${nt(Z)}</dd>`;P+="</dl></div>"}P+="</div>",P+=`<div class="reindex-embed-prompt">
        <p>Re-index completado. Para aplicar los nuevos summaries a los embeddings:</p>
        <button class="corpus-btn corpus-btn-promote" id="reindex-embed-now-btn">Embed ahora</button>
      </div>`}if((l=$==null?void 0:$.checks)!=null&&l.length){P+='<div class="emb-checks">';for(const I of $.checks){const B=I.ok?'<span class="ops-dot ops-dot-ok">●</span>':'<span class="ops-dot ops-dot-error">●</span>';P+=`<div class="emb-check">${B} <strong>${Be(I.label)}</strong>: ${Be(I.detail)}</div>`}P+="</div>"}$!=null&&$.log_tail&&(P+=`<details class="emb-log-accordion"><summary>Log</summary><pre class="emb-log-tail">${Be($.log_tail)}</pre></details>`),$!=null&&$.error&&(P+=`<p class="emb-error">${Be($.error)}</p>`),a.innerHTML=P}function c(){a.addEventListener("click",R=>{const $=R.target;$.id==="reindex-start-btn"&&b(),$.id==="reindex-stop-btn"&&h(),$.id==="reindex-embed-now-btn"&&n()})}async function b(){o="start",u();try{await je("/api/ops/reindex/start",{mode:"from_source"}),t("Re-index iniciado","success")}catch(R){t(String(R),"error")}o="",await E()}async function h(){var $;const R=($=s==null?void 0:s.current_operation)==null?void 0:$.job_id;if(R){o="stop",u();try{await je("/api/ops/reindex/stop",{job_id:R}),t("Re-index detenido","success")}catch(N){t(String(N),"error")}o="",await E()}}async function E(){try{s=await Pe("/api/ops/reindex-status")}catch{}u()}return{bindEvents:c,refresh:E}}const ya=Object.freeze(Object.defineProperty({__proto__:null,createOpsReindexController:gn},Symbol.toStringTag,{value:"Module"})),Cs=3e3,Jt=8e3;function bn({stateController:e,withThinkingWheel:t,setFlash:n,refreshRuns:a,refreshIngestion:s,refreshCorpusLifecycle:o,refreshEmbeddings:u,refreshReindex:c,intervalMs:b}){(async()=>{try{await t(async()=>{await Promise.all([a({showWheel:!1,reportError:!1}),s({showWheel:!1,reportError:!1}),o==null?void 0:o(),u==null?void 0:u(),c==null?void 0:c()])})}catch(N){n(pe(N),"error")}})();let h=null,E=b??Jt;function R(){const N=e.state.selectedSession;return N?ht(String(N.status||""))?!0:(N.documents||[]).some(P=>P.status==="in_progress"||P.status==="processing"||P.status==="extracting"||P.status==="etl"||P.status==="writing"||P.status==="gates"):!1}function $(){const N=b??(R()?Cs:Jt);h!==null&&N===E||(h!==null&&window.clearInterval(h),E=N,h=window.setInterval(()=>{a({showWheel:!1,reportError:!1}),s({showWheel:!1,reportError:!1,focusSessionId:e.getFocusedRunningSessionId()}),o==null||o(),u==null||u(),c==null||c(),b||$()},E))}return $(),()=>{h!==null&&(window.clearInterval(h),h=null)}}function fn(){const e={activeTab:Jn(),corpora:[],selectedCorpus:"autogenerar",sessions:[],selectedSessionId:Vn(),selectedSession:null,pendingFiles:[],intake:[],reviewPlan:null,preflightRunId:0,mutating:!1,folderUploadProgress:null,folderRelativePaths:new Map,rejectedArtifacts:[],preflightManifest:null,preflightScanProgress:null};function t(){return e.corpora.find(l=>l.key===e.selectedCorpus)}function n(l){e.activeTab=l,Kn(l)}function a(l){e.corpora=[...l]}function s(l){e.folderUploadProgress=l}function o(l){e.preflightManifest=l}function u(l){e.preflightScanProgress=l}function c(l){e.mutating=l}function b(l){e.pendingFiles=[...l]}function h(l){e.intake=[...l]}function E(l){e.reviewPlan=l?{...l,willIngest:[...l.willIngest],bounced:[...l.bounced]}:null}function R(){return e.preflightRunId+=1,e.preflightRunId}function $(l){e.selectedCorpus=l}function N(l){e.selectedSession=l,e.selectedSessionId=(l==null?void 0:l.session_id)||"",Xn((l==null?void 0:l.session_id)||null),l&&(H=!1)}function q(){H=!0,N(null)}function P(l){e.sessions=[...l]}let H=!1;function w(){if(e.selectedSessionId){const l=e.sessions.find(I=>I.session_id===e.selectedSessionId)||null;N(l);return}if(H){N(null);return}N(e.sessions[0]||null)}function S(l){const I=e.sessions.filter(B=>B.session_id!==l.session_id);e.sessions=[l,...I].sort((B,Z)=>Date.parse(String(Z.updated_at||0))-Date.parse(String(B.updated_at||0))),N(l)}function v(){var l;return ht(String(((l=e.selectedSession)==null?void 0:l.status)||""))?e.selectedSessionId:""}return{state:e,clearSelectionAfterDelete:q,getFocusedRunningSessionId:v,selectedCorpusConfig:t,setActiveTab:n,setCorpora:a,setFolderUploadProgress:s,setMutating:c,setPendingFiles:b,setIntake:h,setReviewPlan:E,bumpPreflightRunId:R,setPreflightManifest:o,setPreflightScanProgress:u,setSelectedCorpus:$,setSelectedSession:N,setSessions:P,syncSelectedSession:w,upsertSession:S}}function Es(e){const{value:t,unit:n,size:a="md",className:s=""}=e,o=document.createElement("span");o.className=["lia-metric-value",`lia-metric-value--${a}`,s].filter(Boolean).join(" "),o.setAttribute("data-lia-component","metric-value");const u=document.createElement("span");if(u.className="lia-metric-value__number",u.textContent=typeof t=="number"?t.toLocaleString("es-CO"):String(t),o.appendChild(u),n){const c=document.createElement("span");c.className="lia-metric-value__unit",c.textContent=n,o.appendChild(c)}return o}function gt(e){const{label:t,value:n,unit:a,hint:s,size:o="lg",tone:u="neutral",className:c=""}=e,b=document.createElement("div");b.className=["lia-metric-card",`lia-metric-card--${u}`,c].filter(Boolean).join(" "),b.setAttribute("data-lia-component","metric-card");const h=document.createElement("p");if(h.className="lia-metric-card__label",h.textContent=t,b.appendChild(h),b.appendChild(Es({value:n,unit:a,size:o})),s){const E=document.createElement("p");E.className="lia-metric-card__hint",E.textContent=s,b.appendChild(E)}return b}function xs(e){if(!e)return"sin activar";try{const t=new Date(e);if(Number.isNaN(t.getTime()))return"—";const n=Date.now()-t.getTime(),a=Math.floor(n/6e4);if(a<1)return"hace instantes";if(a<60)return`hace ${a} min`;const s=Math.floor(a/60);return s<24?`hace ${s} h`:`hace ${Math.floor(s/24)} d`}catch{return"—"}}function Ns(e){const t=document.createElement("section");t.className="lia-corpus-overview",t.setAttribute("data-lia-component","corpus-overview");const n=document.createElement("header");n.className="lia-corpus-overview__header";const a=document.createElement("h2");a.className="lia-corpus-overview__title",a.textContent="Corpus activo",n.appendChild(a);const s=document.createElement("p");if(s.className="lia-corpus-overview__subtitle",e.activeGenerationId){const u=document.createElement("code");u.textContent=e.activeGenerationId,s.appendChild(document.createTextNode("Generación ")),s.appendChild(u),s.appendChild(document.createTextNode(` · activada ${xs(e.activatedAt)}`))}else s.textContent="Ninguna generación activa en Supabase.";n.appendChild(s),t.appendChild(n);const o=document.createElement("div");return o.className="lia-corpus-overview__grid",o.appendChild(gt({label:"Documentos servidos",value:e.documents,hint:e.documents>0?`${e.chunks.toLocaleString("es-CO")} chunks indexados`:"—"})),o.appendChild(gt({label:"Grafo de normativa",value:e.graphNodes,unit:"nodos",hint:`${e.graphEdges.toLocaleString("es-CO")} relaciones tipadas`,tone:e.graphOk?"success":"warning"})),o.appendChild(gt({label:"Auditoría del corpus",value:e.auditIncluded,unit:"incluidos",hint:`${e.auditScanned.toLocaleString("es-CO")} escaneados · ${e.auditExcluded.toLocaleString("es-CO")} excluidos`})),o.appendChild(gt({label:"Revisiones pendientes",value:e.auditPendingRevisions,hint:e.auditPendingRevisions===0?"Cuello limpio":"Requieren resolución",tone:e.auditPendingRevisions===0?"success":"warning"})),t.appendChild(o),t}function Ps(e){const{tone:t,pulse:n=!1,ariaLabel:a,className:s=""}=e,o=document.createElement("span");return o.className=["lia-status-dot",`lia-status-dot--${t}`,n?"lia-status-dot--pulse":"",s].filter(Boolean).join(" "),o.setAttribute("data-lia-component","status-dot"),o.setAttribute("role","status"),a&&o.setAttribute("aria-label",a),o}const Is={active:"active",superseded:"idle",running:"running",queued:"running",failed:"error",pending:"warning"},Kt={active:"Activa",superseded:"Reemplazada",running:"En curso",queued:"En cola",failed:"Falló",pending:"Pendiente"};function hn(e){const{status:t,className:n=""}=e,a=document.createElement("span");a.className=["lia-run-status",`lia-run-status--${t}`,n].filter(Boolean).join(" "),a.setAttribute("data-lia-component","run-status"),a.appendChild(Ps({tone:Is[t],pulse:t==="running"||t==="queued",ariaLabel:Kt[t]}));const s=document.createElement("span");return s.className="lia-run-status__label",s.textContent=Kt[t],a.appendChild(s),a}function As(e){if(!e)return"—";try{const t=new Date(e);return Number.isNaN(t.getTime())?"—":t.toLocaleString("es-CO",{day:"numeric",month:"short",hour:"2-digit",minute:"2-digit"})}catch{return e}}function Ls(e,t){const n=document.createElement(t?"button":"div");n.className="lia-generation-row",n.setAttribute("data-lia-component","generation-row"),t&&(n.type="button",n.addEventListener("click",()=>t(e.generationId)));const a=document.createElement("span");a.className="lia-generation-row__id",a.textContent=e.generationId,n.appendChild(a),n.appendChild(hn({status:e.status}));const s=document.createElement("span");s.className="lia-generation-row__date",s.textContent=As(e.generatedAt),n.appendChild(s);const o=document.createElement("span");o.className="lia-generation-row__count",o.textContent=`${e.documents.toLocaleString("es-CO")} docs`,n.appendChild(o);const u=document.createElement("span");if(u.className="lia-generation-row__count lia-generation-row__count--muted",u.textContent=`${e.chunks.toLocaleString("es-CO")} chunks`,n.appendChild(u),e.topClass&&e.topClassCount){const c=document.createElement("span");c.className="lia-generation-row__family",c.textContent=`${e.topClass}: ${e.topClassCount.toLocaleString("es-CO")}`,n.appendChild(c)}if(e.subtopicCoverage){const c=e.subtopicCoverage,b=e.documents>0?e.documents:1,h=Math.round(c.docsWithSubtopic/b*100),E=document.createElement("span");E.className="lia-generation-row__subtopic",E.setAttribute("data-lia-component","generation-row-subtopic");const R=c.docsRequiringReview&&c.docsRequiringReview>0?` (${c.docsRequiringReview} por revisar)`:"";E.textContent=`subtema: ${h}%${R}`,n.appendChild(E)}return n}function Vt(e){const{rows:t,emptyMessage:n="Aún no hay generaciones registradas.",errorMessage:a,onSelect:s}=e,o=document.createElement("section");o.className="lia-generations-list",o.setAttribute("data-lia-component","generations-list");const u=document.createElement("header");u.className="lia-generations-list__header";const c=document.createElement("h2");c.className="lia-generations-list__title",c.textContent="Generaciones recientes",u.appendChild(c);const b=document.createElement("p");b.className="lia-generations-list__subtitle",b.textContent="Cada fila es una corrida de python -m lia_graph.ingest publicada en Supabase.",u.appendChild(b),o.appendChild(u);const h=document.createElement("div");if(h.className="lia-generations-list__body",a){const E=document.createElement("p");E.className="lia-generations-list__feedback lia-generations-list__feedback--error",E.textContent=a,h.appendChild(E)}else if(t.length===0){const E=document.createElement("p");E.className="lia-generations-list__feedback",E.textContent=n,h.appendChild(E)}else{const E=document.createElement("div");E.className="lia-generations-list__head-row",["Generación","Estado","Fecha","Documentos","Chunks","Familia principal"].forEach(R=>{const $=document.createElement("span");$.className="lia-generations-list__head-cell",$.textContent=R,E.appendChild($)}),h.appendChild(E),t.forEach(R=>h.appendChild(Ls(R,s)))}return o.appendChild(h),o}const Ts=[{key:"knowledge_base",label:"knowledge_base/",sublabel:"snapshot Dropbox"},{key:"wip",label:"WIP",sublabel:"Supabase local + Falkor local"},{key:"cloud",label:"Cloud",sublabel:"Supabase cloud + Falkor cloud"}];function Rs(e){const{activeStage:t,className:n=""}=e,a=document.createElement("nav");return a.className=["lia-pipeline-flow",n].filter(Boolean).join(" "),a.setAttribute("data-lia-component","pipeline-flow"),a.setAttribute("aria-label","Pipeline de ingestión Lia Graph"),Ts.forEach((s,o)=>{if(o>0){const h=document.createElement("span");h.className="lia-pipeline-flow__arrow",h.setAttribute("aria-hidden","true"),h.textContent="→",a.appendChild(h)}const u=document.createElement("div");u.className=["lia-pipeline-flow__stage",s.key===t?"lia-pipeline-flow__stage--active":""].filter(Boolean).join(" "),u.setAttribute("data-stage",s.key);const c=document.createElement("span");c.className="lia-pipeline-flow__label",c.textContent=s.label,u.appendChild(c);const b=document.createElement("span");b.className="lia-pipeline-flow__sublabel",b.textContent=s.sublabel,u.appendChild(b),a.appendChild(u)}),a}function Ms(e){const{activeJobId:t,lastRunStatus:n,disabled:a,onTrigger:s}=e,o=document.createElement("section");o.className="lia-run-trigger",o.setAttribute("data-lia-component","run-trigger-card");const u=document.createElement("header");u.className="lia-run-trigger__header";const c=document.createElement("h2");c.className="lia-run-trigger__title",c.textContent="Iniciar nueva ingesta",u.appendChild(c);const b=document.createElement("p");b.className="lia-run-trigger__subtitle",b.textContent="Ejecuta make phase2-graph-artifacts-supabase contra knowledge_base/. Por defecto escribe a WIP (Supabase local + FalkorDB local). Cuando WIP esté validado, promueve a Cloud desde la pestaña Promoción.",u.appendChild(b),o.appendChild(u),o.appendChild(Rs({activeStage:"wip"}));const h=document.createElement("form");h.className="lia-run-trigger__form",h.setAttribute("novalidate","");const E=qs({name:"supabase_target",legend:"Destino Supabase",options:[{value:"wip",label:"WIP (local)",hint:"Supabase docker + FalkorDB docker — ciclo seguro",defaultChecked:!0},{value:"production",label:"Producción (cloud)",hint:"Supabase cloud + FalkorDB cloud — afecta runtime servido"}]});h.appendChild(E);const R=Ds({name:"suin_scope",label:"Scope SUIN-Juriscol",placeholder:"vacío para omitir, ej: et",hint:"Cuando es vacío, sólo se reingiere el corpus base. Pasa el scope (et, tributario, laboral, jurisprudencia) para incluir SUIN."});h.appendChild(R);const $=Os([{name:"skip_embeddings",label:"Saltar embeddings",hint:"Si se marca, la etapa de embeddings no se encadena al final (auto_embed=false).",defaultChecked:!1},{name:"auto_promote",label:"Promover a cloud al terminar",hint:"Si se marca, la corrida encadena una promoción WIP→Cloud al finalizar sin errores.",defaultChecked:!1}]);h.appendChild($);const N=document.createElement("div");N.className="lia-run-trigger__submit-row";const q=document.createElement("button");if(q.type="submit",q.className="lia-button lia-button--primary lia-run-trigger__submit",q.textContent=t?"Ejecutando…":"Iniciar ingesta",q.disabled=a,N.appendChild(q),n&&N.appendChild(hn({status:n})),t){const P=document.createElement("code");P.className="lia-run-trigger__job-id",P.textContent=t,N.appendChild(P)}return h.appendChild(N),h.addEventListener("submit",P=>{if(P.preventDefault(),a)return;const H=new FormData(h),w=H.get("supabase_target")||"wip",S=String(H.get("suin_scope")||"").trim(),v=H.get("skip_embeddings")!=null,l=H.get("auto_promote")!=null;s({suinScope:S,supabaseTarget:w==="production"?"production":"wip",autoEmbed:!v,autoPromote:l})}),o.appendChild(h),o}function qs(e){const t=document.createElement("fieldset");t.className="lia-run-trigger__field lia-run-trigger__field--radio";const n=document.createElement("legend");return n.className="lia-run-trigger__legend",n.textContent=e.legend,t.appendChild(n),e.options.forEach(a=>{const s=document.createElement("label");s.className="lia-run-trigger__radio-row";const o=document.createElement("input");o.type="radio",o.name=e.name,o.value=a.value,a.defaultChecked&&(o.defaultChecked=!0),s.appendChild(o);const u=document.createElement("span");u.className="lia-run-trigger__radio-text";const c=document.createElement("span");if(c.className="lia-run-trigger__radio-label",c.textContent=a.label,u.appendChild(c),a.hint){const b=document.createElement("span");b.className="lia-run-trigger__radio-hint",b.textContent=a.hint,u.appendChild(b)}s.appendChild(u),t.appendChild(s)}),t}function Os(e){const t=document.createElement("fieldset");t.className="lia-run-trigger__field lia-run-trigger__field--checkbox";const n=document.createElement("legend");return n.className="lia-run-trigger__legend",n.textContent="Opciones de corrida",t.appendChild(n),e.forEach(a=>{const s=document.createElement("label");s.className="lia-run-trigger__checkbox-row";const o=document.createElement("input");o.type="checkbox",o.name=a.name,a.defaultChecked&&(o.defaultChecked=!0),s.appendChild(o);const u=document.createElement("span");u.className="lia-run-trigger__checkbox-text";const c=document.createElement("span");if(c.className="lia-run-trigger__checkbox-label",c.textContent=a.label,u.appendChild(c),a.hint){const b=document.createElement("span");b.className="lia-run-trigger__checkbox-hint",b.textContent=a.hint,u.appendChild(b)}s.appendChild(u),t.appendChild(s)}),t}function Ds(e){const t=document.createElement("div");t.className="lia-run-trigger__field lia-run-trigger__field--text";const n=document.createElement("label");n.className="lia-run-trigger__label",n.htmlFor=`lia-run-trigger-${e.name}`,n.textContent=e.label,t.appendChild(n);const a=document.createElement("input");if(a.type="text",a.id=`lia-run-trigger-${e.name}`,a.name=e.name,a.className="lia-input lia-run-trigger__input",a.autocomplete="off",a.spellcheck=!1,e.placeholder&&(a.placeholder=e.placeholder),t.appendChild(a),e.hint){const s=document.createElement("p");s.className="lia-run-trigger__hint",s.textContent=e.hint,t.appendChild(s)}return t}const Xt=["B","KB","MB","GB","TB"];function Zt(e){if(!Number.isFinite(e)||e<=0)return"0 B";let t=0,n=e;for(;n>=1024&&t<Xt.length-1;)n/=1024,t+=1;const a=t===0?Math.round(n):Math.round(n*10)/10;return`${Number.isInteger(a)?`${a}`:a.toFixed(1)} ${Xt[t]}`}function Bs(e){const t=e.toLowerCase();return t.endsWith(".pdf")?"📕":t.endsWith(".docx")||t.endsWith(".doc")?"📘":t.endsWith(".md")?"📄":t.endsWith(".txt")?"📃":"📄"}function js(e){const{filename:t,bytes:n,onRemove:a,className:s=""}=e,o=document.createElement("span");o.className=["lia-file-chip",s].filter(Boolean).join(" "),o.setAttribute("data-lia-component","file-chip"),o.title=`${t} - ${Zt(n)}`;const u=document.createElement("span");u.className="lia-file-chip__icon",u.setAttribute("aria-hidden","true"),u.textContent=Bs(t),o.appendChild(u);const c=document.createElement("span");c.className="lia-file-chip__name",c.textContent=t,o.appendChild(c);const b=document.createElement("span");if(b.className="lia-file-chip__size",b.textContent=Zt(n),o.appendChild(b),a){const h=document.createElement("button");h.type="button",h.className="lia-file-chip__remove",h.setAttribute("aria-label",`Quitar ${t}`),h.textContent="x",h.addEventListener("click",E=>{E.preventDefault(),E.stopPropagation(),a()}),o.appendChild(h)}return o}function Yt(e){const{subtopicKey:t,label:n,confidence:a,requiresReview:s,isNew:o,className:u=""}=e;let c="brand";s?c="warning":o&&(c="info");const b=n&&n.trim()?n:t,h=a!=null&&!Number.isNaN(a)?`${b} · ${Math.round(a<=1?a*100:a)}%`:b,E=bt({label:h,tone:c,emphasis:"soft",className:["lia-subtopic-chip",u].filter(Boolean).join(" "),dataComponent:"subtopic-chip"});return E.setAttribute("data-subtopic-key",t),s&&E.setAttribute("data-subtopic-review","true"),o&&E.setAttribute("data-subtopic-new","true"),E}function Fs(e){if(e==null||Number.isNaN(e))return"-";const t=e<=1?e*100:e;return`${Math.round(t)}%`}function zs(e){if(e==null||Number.isNaN(e))return"neutral";const t=e<=1?e*100:e;return t>=80?"success":t>=50?"warning":"error"}function Hs(e){const{filename:t,bytes:n,detectedTopic:a,topicLabel:s,combinedConfidence:o,requiresReview:u,coercionMethod:c,subtopicKey:b,subtopicLabel:h,subtopicConfidence:E,subtopicIsNew:R,requiresSubtopicReview:$,onRemove:N,className:q=""}=e,P=document.createElement("div");P.className=["lia-intake-file-row",q].filter(Boolean).join(" "),P.setAttribute("data-lia-component","intake-file-row");const H=document.createElement("span");H.className="lia-intake-file-row__file",H.appendChild(js({filename:t,bytes:n,onRemove:N})),P.appendChild(H);const w=document.createElement("span");if(w.className="lia-intake-file-row__meta",s||a){const S=Pn({label:s||a||"sin tópico",tone:"info",emphasis:"soft",className:"lia-intake-file-row__topic"});a&&S.setAttribute("data-topic",a),w.appendChild(S)}if(o!=null){const S=bt({label:Fs(o),tone:zs(o),emphasis:"soft",className:"lia-intake-file-row__confidence"});w.appendChild(S)}if(u){const S=bt({label:"requiere revisión",tone:"warning",emphasis:"solid",className:"lia-intake-file-row__review"});S.setAttribute("role","status"),w.appendChild(S)}if(b?w.appendChild(Yt({subtopicKey:b,label:h||null,confidence:E??null,isNew:R,requiresReview:$,className:"lia-intake-file-row__subtopic"})):R&&e.subtopicKey!==void 0&&w.appendChild(Yt({subtopicKey:"(nuevo)",label:h||"subtema propuesto",isNew:!0,className:"lia-intake-file-row__subtopic"})),$&&!b){const S=bt({label:"subtema pendiente",tone:"warning",emphasis:"soft",className:"lia-intake-file-row__subtopic-review"});S.setAttribute("data-subtopic-review","true"),w.appendChild(S)}if(c){const S=document.createElement("span");S.className="lia-intake-file-row__coercion",S.textContent=c,w.appendChild(S)}return P.appendChild(w),P}const Us=[".md",".txt",".json",".pdf",".docx"];function Ws(e){const t=e.toLowerCase();return Us.some(n=>t.endsWith(n))}function Gs(e){return e.split("/").filter(Boolean).some(n=>n.startsWith("."))}function Js(e){return e.includes("__MACOSX/")||e.startsWith("__MACOSX/")}function Ks(e,t){return!(!e||Js(t)||Gs(t)||e.startsWith(".")||!Ws(e))}async function Vs(e){const t=[];for(;;){const n=await new Promise(a=>{e.readEntries(s=>a(s||[]))});if(n.length===0)break;t.push(...n)}return t}async function vn(e,t){if(!e)return[];const n=t?`${t}/${e.name}`:e.name;if(e.isFile){if(!e.file)return[];const a=await new Promise(s=>e.file(s));return[{filename:a.name,bytes:a.size,mime:a.type||void 0,relativePath:n,file:a}]}if(e.isDirectory&&e.createReader){const a=e.createReader(),s=await Vs(a);return(await Promise.all(s.map(u=>vn(u,n)))).flat()}return[]}async function Xs(e){const t=e.items?Array.from(e.items):[];if(t.length>0&&typeof t[0].webkitGetAsEntry=="function"){const a=[];for(const s of t){const o=s.webkitGetAsEntry();if(!o)continue;const u=await vn(o,"");a.push(...u)}return a}return(e.files?Array.from(e.files):[]).map(a=>({filename:a.name,bytes:a.size,mime:a.type||void 0,relativePath:a.name,file:a}))}function Zs(e,t){return t?{filename:t.filename||e.filename,mime:t.mime||e.mime,bytes:t.bytes??e.bytes,detectedTopic:t.detected_topic??null,topicLabel:t.topic_label??null,combinedConfidence:t.combined_confidence??null,requiresReview:!!t.requires_review,coercionMethod:t.coercion_method??null,subtopicKey:t.subtopic_key??null,subtopicLabel:t.subtopic_label??null,subtopicConfidence:t.subtopic_confidence??null,subtopicIsNew:!!t.subtopic_is_new,requiresSubtopicReview:!!t.requires_subtopic_review}:{filename:e.filename,mime:e.mime,bytes:e.bytes,detectedTopic:null,topicLabel:null,combinedConfidence:null,requiresReview:!1,coercionMethod:null}}function Ys(e){const{onIntake:t,onApprove:n}=e,a=document.createElement("section");a.className="lia-intake-drop-zone",a.setAttribute("data-lia-component","intake-drop-zone");const s=document.createElement("header");s.className="lia-intake-drop-zone__header";const o=document.createElement("h2");o.className="lia-intake-drop-zone__title",o.textContent="Arrastra archivos o carpetas",s.appendChild(o);const u=document.createElement("p");u.className="lia-intake-drop-zone__hint",u.textContent="Acepta .md, .txt, .json, .pdf, .docx. Carpetas se recorren recursivamente. Ocultos y __MACOSX/ se descartan.",s.appendChild(u),a.appendChild(s);const c=document.createElement("div");c.className="lia-intake-drop-zone__zone",c.setAttribute("role","button"),c.setAttribute("tabindex","0"),c.setAttribute("aria-label","Zona de arrastre para ingesta");const b=document.createElement("p");b.className="lia-intake-drop-zone__zone-label",b.textContent="Suelta aquí los archivos para enviarlos al intake",c.appendChild(b),a.appendChild(c);const h=document.createElement("div");h.className="lia-intake-drop-zone__list",h.setAttribute("data-role","intake-file-list"),a.appendChild(h);const E=document.createElement("p");E.className="lia-intake-drop-zone__feedback",E.setAttribute("role","status"),a.appendChild(E);const R=document.createElement("div");R.className="lia-intake-drop-zone__actions";const $=document.createElement("button");$.type="button",$.className="lia-button lia-button--primary lia-intake-drop-zone__approve",$.textContent="Aprobar e ingerir",$.disabled=!0,R.appendChild($),a.appendChild(R);const N={queued:[],lastResponse:null};function q(){var S;if(h.replaceChildren(),N.queued.length===0){const v=document.createElement("p");v.className="lia-intake-drop-zone__empty",v.textContent="Sin archivos en cola.",h.appendChild(v);return}const w=new Map;if((S=N.lastResponse)!=null&&S.files)for(const v of N.lastResponse.files)v.filename&&w.set(v.filename,v);N.queued.forEach((v,l)=>{const I=w.get(v.filename),B=Hs({...Zs(v,I),onRemove:()=>{N.queued.splice(l,1),q(),P()}});h.appendChild(B)})}function P(){var S,v;const w=((v=(S=N.lastResponse)==null?void 0:S.summary)==null?void 0:v.placed)??0;$.disabled=w<=0}async function H(w){const S=w.filter(v=>Ks(v.filename,v.relativePath));if(S.length===0){E.textContent="Ningún archivo elegible en el drop.";return}N.queued=S,N.lastResponse=null,q(),P(),E.textContent=`Enviando ${S.length} archivo(s) al intake…`;try{const v=await t(S);N.lastResponse=v,q(),P(),E.textContent=`Intake ok — placed ${v.summary.placed} / deduped ${v.summary.deduped} / rejected ${v.summary.rejected}.`}catch(v){N.lastResponse=null,P();const l=v instanceof Error?v.message:"intake falló";E.textContent=`Intake falló: ${l}`}}return c.addEventListener("dragenter",w=>{w.preventDefault(),c.classList.add("lia-intake-drop-zone__zone--active")}),c.addEventListener("dragover",w=>{w.preventDefault(),c.classList.add("lia-intake-drop-zone__zone--active")}),c.addEventListener("dragleave",w=>{w.preventDefault(),c.classList.remove("lia-intake-drop-zone__zone--active")}),c.addEventListener("drop",w=>{w.preventDefault(),c.classList.remove("lia-intake-drop-zone__zone--active");const S=w.dataTransfer;S&&(async()=>{const v=await Xs(S);await H(v)})()}),$.addEventListener("click",()=>{var S;if($.disabled)return;const w=(S=N.lastResponse)==null?void 0:S.batch_id;w&&n&&n(w)}),q(),P(),a}function Qs(e){const{status:t,ariaLabel:n,className:a=""}=e,s=document.createElement("span"),o=["lia-progress-dot",`lia-progress-dot--${t}`,t==="running"?"lia-progress-dot--pulse":"",a].filter(Boolean);return s.className=o.join(" "),s.setAttribute("data-lia-component","progress-dot"),s.setAttribute("role","status"),s.setAttribute("data-status",t),n&&s.setAttribute("aria-label",n),s}const ea=["docs","chunks","edges","embeddings_generated"];function ta(e){if(!e)return"";const t=[];for(const n of ea)if(e[n]!=null&&t.push(`${n}: ${e[n]}`),t.length>=3)break;return t.join(", ")}function Qt(e){if(e==null)return null;if(typeof e=="number")return Number.isFinite(e)?e:null;const t=Date.parse(e);return Number.isFinite(t)?t:null}function na(e,t){const n=Qt(e),a=Qt(t);if(n==null||a==null||a<n)return"";const s=Math.round((a-n)/1e3);if(s<60)return`${s}s`;const o=Math.floor(s/60),u=s%60;return u?`${o}m ${u}s`:`${o}m`}function en(e){const{name:t,label:n,status:a,counts:s,startedAt:o,finishedAt:u,errorMessage:c,className:b=""}=e,h=document.createElement("div");h.className=["lia-stage-progress-item",`lia-stage-progress-item--${a}`,b].filter(Boolean).join(" "),h.setAttribute("data-lia-component","stage-progress-item"),h.setAttribute("data-stage-name",t),h.appendChild(Qs({status:a,ariaLabel:n}));const E=document.createElement("span");E.className="lia-stage-progress-item__label",E.textContent=n,h.appendChild(E);const R=ta(s);if(R){const N=document.createElement("span");N.className="lia-stage-progress-item__counts",N.textContent=R,h.appendChild(N)}const $=na(o,u);if($){const N=document.createElement("span");N.className="lia-stage-progress-item__duration",N.textContent=$,h.appendChild(N)}if(a==="failed"&&c){const N=document.createElement("p");N.className="lia-stage-progress-item__error",N.textContent=c,N.setAttribute("role","alert"),h.appendChild(N)}return h}const tn=[{name:"coerce",label:"Coerce"},{name:"audit",label:"Audit"},{name:"chunk",label:"Chunk"},{name:"sink",label:"Sink"},{name:"falkor",label:"FalkorDB"},{name:"embeddings",label:"Embeddings"}];function sa(e){return e==="running"||e==="done"||e==="failed"||e==="pending"?e:"pending"}function nn(e,t,n){return{name:e,label:t,status:sa(n==null?void 0:n.status),counts:(n==null?void 0:n.counts)??null,startedAt:(n==null?void 0:n.started_at)??null,finishedAt:(n==null?void 0:n.finished_at)??null,errorMessage:(n==null?void 0:n.error)??null}}function aa(){const e=document.createElement("section");e.className="lia-run-progress-timeline",e.setAttribute("data-lia-component","run-progress-timeline");const t=document.createElement("header");t.className="lia-run-progress-timeline__header";const n=document.createElement("h3");n.className="lia-run-progress-timeline__title",n.textContent="Progreso de la corrida",t.appendChild(n),e.appendChild(t);const a=document.createElement("div");a.className="lia-run-progress-timeline__list";const s=new Map;tn.forEach(({name:u,label:c})=>{const b=document.createElement("div");b.className="lia-run-progress-timeline__item",b.setAttribute("data-stage",u),b.appendChild(en(nn(u,c,void 0))),a.appendChild(b),s.set(u,b)}),e.appendChild(a);function o(u){const c=(u==null?void 0:u.stages)||{};tn.forEach(({name:b,label:h})=>{const E=s.get(b);if(!E)return;const R=c[b]||void 0;E.replaceChildren(en(nn(b,h,R)))})}return{element:e,update:o}}function oa(e={}){const{initialLines:t=[],autoScroll:n=!0,onCopy:a=null,summaryLabel:s="Log de ejecución",className:o=""}=e,u=document.createElement("div");u.className=["lia-log-tail-viewer",o].filter(Boolean).join(" "),u.setAttribute("data-lia-component","log-tail-viewer");const c=document.createElement("div");c.className="lia-log-tail-viewer__toolbar";const b=document.createElement("button");b.type="button",b.className="lia-log-tail-viewer__copy",b.textContent="Copiar",b.setAttribute("aria-label","Copiar log"),c.appendChild(b);const h=document.createElement("details");h.className="lia-log-tail-viewer__details",h.open=!0;const E=document.createElement("summary");E.className="lia-log-tail-viewer__summary",E.textContent=s,h.appendChild(E);const R=document.createElement("pre");R.className="lia-log-tail-viewer__body",R.textContent=t.join(`
`),h.appendChild(R),u.appendChild(c),u.appendChild(h);const $={lines:[...t]},N=()=>{n&&(R.scrollTop=R.scrollHeight)},q=()=>{R.textContent=$.lines.join(`
`),N()},P=w=>{!w||w.length===0||($.lines.push(...w),q())},H=()=>{$.lines=[],R.textContent=""};return b.addEventListener("click",()=>{var v;const w=$.lines.join(`
`),S=(v=globalThis.navigator)==null?void 0:v.clipboard;S&&typeof S.writeText=="function"&&S.writeText(w),a&&a()}),n&&N(),{element:u,appendLines:P,clear:H}}function ia(e={}){const{initialLines:t=[],onCopy:n=null,summaryLabel:a="Log de ejecución"}=e,s=document.createElement("section");s.className="lia-run-log-console",s.setAttribute("data-lia-component","run-log-console");const o=document.createElement("header");o.className="lia-run-log-console__header";const u=document.createElement("h3");u.className="lia-run-log-console__title",u.textContent="Log en vivo",o.appendChild(u);const c=document.createElement("p");c.className="lia-run-log-console__subtitle",c.textContent="Streaming del archivo artifacts/jobs/<job>.log — se actualiza cada 1.5s.",o.appendChild(c),s.appendChild(o);const b=oa({initialLines:t,autoScroll:!0,onCopy:n,summaryLabel:a,className:"lia-run-log-console__viewer"});return s.appendChild(b.element),{element:s,appendLines:b.appendLines,clear:b.clear}}async function sn(e,t){const{response:n,data:a}=await je(e,t);if(!n.ok){const s=a&&typeof a=="object"&&"error"in a?String(a.error||n.statusText):n.statusText;throw new st(s,n.status,a)}if(!a)throw new st("Empty response",n.status,null);return a}function ra(e){const t=e.querySelector("[data-slot=corpus-overview]"),n=e.querySelector("[data-slot=run-trigger]"),a=e.querySelector("[data-slot=generations-list]"),s=e.querySelector("[data-slot=intake-zone]"),o=e.querySelector("[data-slot=progress-timeline]"),u=e.querySelector("[data-slot=log-console]");if(!t||!n||!a)return e.textContent="Sesiones: missing render slots.",{refresh:async()=>{},destroy:()=>{}};const c={activeJobId:null,lastRunStatus:null,pollHandle:null,logCursor:0,lastBatchId:null,autoEmbed:!0,autoPromote:!1,supabaseTarget:"wip",suinScope:""};let b=null,h=null;function E(){n.replaceChildren(Ms({activeJobId:c.activeJobId,lastRunStatus:c.lastRunStatus,disabled:c.activeJobId!==null,onTrigger:({suinScope:C,supabaseTarget:y,autoEmbed:f,autoPromote:j})=>{c.autoEmbed=f,c.autoPromote=j,c.supabaseTarget=y,c.suinScope=C,v({suinScope:C,supabaseTarget:y,autoEmbed:f,autoPromote:j,batchId:null})}}))}function R(){s&&s.replaceChildren(Ys({onIntake:C=>H(C),onApprove:C=>{S(C,{autoEmbed:c.autoEmbed,autoPromote:c.autoPromote,supabaseTarget:c.supabaseTarget,suinScope:c.suinScope})}}))}function $(){o&&(b=aa(),o.replaceChildren(b.element))}function N(){u&&(h=ia(),u.replaceChildren(h.element))}async function q(){t.replaceChildren(D("overview"));try{const C=await Pe("/api/ingest/state"),y={documents:C.corpus.documents,chunks:C.corpus.chunks,graphNodes:C.graph.nodes,graphEdges:C.graph.edges,graphOk:C.graph.ok,auditScanned:C.audit.scanned,auditIncluded:C.audit.include_corpus,auditExcluded:C.audit.exclude_internal,auditPendingRevisions:C.audit.pending_revisions,activeGenerationId:C.corpus.active_generation_id,activatedAt:C.corpus.activated_at};t.replaceChildren(Ns(y))}catch(C){t.replaceChildren(ie("No se pudo cargar el estado del corpus.",C))}}async function P(){a.replaceChildren(D("generations"));try{const y=((await Pe("/api/ingest/generations?limit=20")).generations||[]).map(f=>{const j=f.knowledge_class_counts||{},L=Object.entries(j).sort((_,X)=>X[1]-_[1])[0];return{generationId:f.generation_id,status:f.is_active?"active":"superseded",generatedAt:f.generated_at,documents:Number(f.documents)||0,chunks:Number(f.chunks)||0,topClass:L==null?void 0:L[0],topClassCount:L==null?void 0:L[1]}});a.replaceChildren(Vt({rows:y}))}catch(C){a.replaceChildren(Vt({rows:[],errorMessage:`No se pudieron cargar las generaciones: ${ge(C)}`}))}}async function H(C){const f={batch_id:null,files:await Promise.all(C.map(async L=>{const _=await w(L.file);return{filename:L.filename,content_base64:_,relative_path:L.relativePath||L.filename}})),options:{mirror_to_dropbox:!1,dropbox_root:null}},j=await sn("/api/ingest/intake",f);return c.lastBatchId=j.batch_id,j}async function w(C){const y=globalThis;if(typeof y.FileReader=="function"){const f=await new Promise((L,_)=>{const X=new y.FileReader;X.onerror=()=>_(X.error||new Error("file read failed")),X.onload=()=>L(String(X.result||"")),X.readAsDataURL(C)}),j=f.indexOf(",");return j>=0?f.slice(j+1):""}if(typeof C.arrayBuffer=="function"){const f=await C.arrayBuffer();return me(f)}return""}async function S(C,y){await v({batchId:C,autoEmbed:y.autoEmbed,autoPromote:y.autoPromote,supabaseTarget:y.supabaseTarget,suinScope:y.suinScope})}async function v(C){c.lastRunStatus="queued",c.logCursor=0,h&&h.clear(),E();try{const y=await sn("/api/ingest/run",{suin_scope:C.suinScope,supabase_target:C.supabaseTarget,auto_embed:C.autoEmbed,auto_promote:C.autoPromote,batch_id:C.batchId});c.activeJobId=y.job_id,c.lastRunStatus="running",E(),l()}catch(y){c.lastRunStatus="failed",c.activeJobId=null,E(),F(`No se pudo iniciar la ingesta: ${ge(y)}`)}}function l(){I();const C=o!==null||u!==null;c.pollHandle=window.setInterval(()=>{if(!c.activeJobId){I();return}C?(B(c.activeJobId),Z(c.activeJobId)):le(c.activeJobId)},C?1500:4e3)}function I(){c.pollHandle!==null&&(window.clearInterval(c.pollHandle),c.pollHandle=null)}async function B(C){try{const y=await Pe(`/api/ingest/job/${C}/progress`);b&&b.update(y);const f=y.status;(f==="done"||f==="failed")&&(c.lastRunStatus=f==="done"?"active":"failed",c.activeJobId=null,E(),I(),f==="done"&&await Promise.all([q(),P()]))}catch{}}async function Z(C){try{const y=await Pe(`/api/ingest/job/${C}/log/tail?cursor=${c.logCursor}&limit=200`);y.lines&&y.lines.length>0&&h&&h.appendLines(y.lines),typeof y.next_cursor=="number"&&(c.logCursor=y.next_cursor)}catch{}}async function le(C){var y;try{const j=(await Pe(`/api/jobs/${C}`)).job;if(!j)return;if(j.status==="completed"){const L=(((y=j.result_payload)==null?void 0:y.exit_code)??1)===0;c.lastRunStatus=L?"active":"failed",c.activeJobId=null,E(),I(),L&&await Promise.all([q(),P()])}else j.status==="failed"&&(c.lastRunStatus="failed",c.activeJobId=null,E(),I())}catch{}}function me(C){const y=new Uint8Array(C),f=32768;let j="";for(let X=0;X<y.length;X+=f){const be=y.subarray(X,Math.min(y.length,X+f));j+=String.fromCharCode.apply(null,Array.from(be))}const L=globalThis;if(typeof L.btoa=="function")return L.btoa(j);const _=globalThis.Buffer;return _?_.from(j,"binary").toString("base64"):""}function D(C){const y=document.createElement("div");return y.className=`lia-ingest-skeleton lia-ingest-skeleton--${C}`,y.setAttribute("aria-hidden","true"),y.textContent="Cargando…",y}function ie(C,y){const f=document.createElement("div");f.className="lia-ingest-error",f.setAttribute("role","alert");const j=document.createElement("strong");j.textContent=C,f.appendChild(j);const L=document.createElement("p");return L.className="lia-ingest-error__detail",L.textContent=ge(y),f.appendChild(L),f}function ge(C){return C instanceof Error?C.message:typeof C=="string"?C:"Error desconocido"}function F(C){const y=document.createElement("div");y.className="lia-ingest-toast",y.textContent=C,e.prepend(y),window.setTimeout(()=>y.remove(),4e3)}return E(),R(),$(),N(),Promise.all([q(),P()]),{async refresh(){await Promise.all([q(),P()])},destroy(){I()}}}function ca(e,{i18n:t}){const n=e,a=n.querySelector("#lia-ingest-shell");let s=null;a&&(s=ra(a),window.setInterval(()=>{s==null||s.refresh()},3e4));const o=a!==null,u=n.querySelector("#ops-tab-monitor"),c=n.querySelector("#ops-tab-ingestion"),b=n.querySelector("#ops-tab-control"),h=n.querySelector("#ops-tab-embeddings"),E=n.querySelector("#ops-tab-reindex"),R=n.querySelector("#ops-panel-monitor"),$=n.querySelector("#ops-panel-ingestion"),N=n.querySelector("#ops-panel-control"),q=n.querySelector("#ops-panel-embeddings"),P=n.querySelector("#ops-panel-reindex"),H=n.querySelector("#runs-body"),w=n.querySelector("#timeline"),S=n.querySelector("#timeline-meta"),v=n.querySelector("#cascade-note"),l=n.querySelector("#user-cascade"),I=n.querySelector("#user-cascade-summary"),B=n.querySelector("#technical-cascade"),Z=n.querySelector("#technical-cascade-summary"),le=n.querySelector("#refresh-runs"),me=!!(H&&w&&S&&v&&l&&I&&B&&Z&&le),D=o?null:ee(n,"#ingestion-flash"),ie=fn();function ge(oe="",ut="success"){if(D){if(!oe){D.hidden=!0,D.textContent="",D.removeAttribute("data-tone");return}D.hidden=!1,D.dataset.tone=ut,D.textContent=oe}}const F=o?null:ee(n,"#ingestion-corpus"),C=o?null:ee(n,"#ingestion-batch-type"),y=o?null:ee(n,"#ingestion-dropzone"),f=o?null:ee(n,"#ingestion-file-input"),j=o?null:ee(n,"#ingestion-folder-input"),L=o?null:ee(n,"#ingestion-pending-files"),_=o?null:ee(n,"#ingestion-overview"),X=o?null:ee(n,"#ingestion-refresh"),be=o?null:ee(n,"#ingestion-create-session"),A=o?null:ee(n,"#ingestion-select-files"),O=o?null:ee(n,"#ingestion-select-folder"),Y=o?null:ee(n,"#ingestion-upload-files"),W=o?null:ee(n,"#ingestion-upload-progress"),ce=o?null:ee(n,"#ingestion-process-session"),te=o?null:ee(n,"#ingestion-auto-process"),ne=o?null:ee(n,"#ingestion-validate-batch"),$e=o?null:ee(n,"#ingestion-retry-session"),Se=o?null:ee(n,"#ingestion-delete-session"),we=o?null:ee(n,"#ingestion-session-meta"),G=o?null:ee(n,"#ingestion-sessions-list"),Ee=o?null:ee(n,"#selected-session-meta"),Ie=o?null:ee(n,"#ingestion-last-error"),Ae=o?null:ee(n,"#ingestion-last-error-message"),xe=o?null:ee(n,"#ingestion-last-error-guidance"),Re=o?null:ee(n,"#ingestion-last-error-next"),_e=o?null:ee(n,"#ingestion-kanban"),Me=o?null:ee(n,"#ingestion-log-accordion"),qe=o?null:ee(n,"#ingestion-log-body"),he=o?null:ee(n,"#ingestion-log-copy"),fe=o?null:ee(n,"#ingestion-auto-status"),Xe=n.querySelector("#ingestion-add-corpus-btn"),Fe=n.querySelector("#add-corpus-dialog"),Ye=n.querySelector("#ingestion-bounce-log"),Qe=n.querySelector("#ingestion-bounce-body"),et=n.querySelector("#ingestion-bounce-copy");async function ze(oe){return oe()}const ue=me?mn({i18n:t,stateController:ie,dom:{monitorTabBtn:u,ingestionTabBtn:c,controlTabBtn:b,embeddingsTabBtn:h,reindexTabBtn:E,monitorPanel:R,ingestionPanel:$,controlPanel:N,embeddingsPanel:q,reindexPanel:P,runsBody:H,timelineNode:w,timelineMeta:S,cascadeNote:v,userCascadeNode:l,userCascadeSummary:I,technicalCascadeNode:B,technicalCascadeSummary:Z,refreshRunsBtn:le},withThinkingWheel:ze,setFlash:ge}):null,ve=o?null:ws({i18n:t,stateController:ie,dom:{ingestionCorpusSelect:F,ingestionBatchTypeSelect:C,ingestionDropzone:y,ingestionFileInput:f,ingestionFolderInput:j,ingestionSelectFilesBtn:A,ingestionSelectFolderBtn:O,ingestionUploadProgress:W,ingestionPendingFiles:L,ingestionOverview:_,ingestionRefreshBtn:X,ingestionCreateSessionBtn:be,ingestionUploadBtn:Y,ingestionProcessBtn:ce,ingestionAutoProcessBtn:te,ingestionValidateBatchBtn:ne,ingestionRetryBtn:$e,ingestionDeleteSessionBtn:Se,ingestionSessionMeta:we,ingestionSessionsList:G,selectedSessionMeta:Ee,ingestionLastError:Ie,ingestionLastErrorMessage:Ae,ingestionLastErrorGuidance:xe,ingestionLastErrorNext:Re,ingestionKanban:_e,ingestionLogAccordion:Me,ingestionLogBody:qe,ingestionLogCopyBtn:he,ingestionAutoStatus:fe,addCorpusBtn:Xe,addCorpusDialog:Fe,ingestionBounceLog:Ye,ingestionBounceBody:Qe,ingestionBounceCopy:et},withThinkingWheel:ze,setFlash:ge}),Oe=n.querySelector("#corpus-lifecycle"),Q=Oe?an({dom:{container:Oe},setFlash:ge}):null,dt=n.querySelector("#embeddings-lifecycle"),He=dt?ln({dom:{container:dt},setFlash:ge}):null,at=n.querySelector("#reindex-lifecycle"),Ue=at?gn({dom:{container:at},setFlash:ge,navigateToEmbeddings:()=>{ie.setActiveTab("embeddings"),ue==null||ue.renderTabs()}}):null;ue==null||ue.bindEvents(),ve==null||ve.bindEvents(),Q==null||Q.bindEvents(),He==null||He.bindEvents(),Ue==null||Ue.bindEvents(),ue==null||ue.renderTabs(),ve==null||ve.render(),bn({stateController:ie,withThinkingWheel:ze,setFlash:ge,refreshRuns:(ue==null?void 0:ue.refreshRuns)??(async()=>{}),refreshIngestion:(ve==null?void 0:ve.refreshIngestion)??(async()=>{}),refreshCorpusLifecycle:Q==null?void 0:Q.refresh,refreshEmbeddings:He==null?void 0:He.refresh,refreshReindex:Ue==null?void 0:Ue.refresh})}function la(e,{i18n:t}){const n=e,a=n.querySelector("#runs-body"),s=n.querySelector("#timeline"),o=n.querySelector("#timeline-meta"),u=n.querySelector("#cascade-note"),c=n.querySelector("#user-cascade"),b=n.querySelector("#user-cascade-summary"),h=n.querySelector("#technical-cascade"),E=n.querySelector("#technical-cascade-summary"),R=n.querySelector("#refresh-runs");if(!a||!s||!o||!u||!c||!b||!h||!E||!R)return;const $=fn(),N=async H=>H(),q=()=>{},P=mn({i18n:t,stateController:$,dom:{monitorTabBtn:null,ingestionTabBtn:null,controlTabBtn:null,embeddingsTabBtn:null,reindexTabBtn:null,monitorPanel:null,ingestionPanel:null,controlPanel:null,embeddingsPanel:null,reindexPanel:null,runsBody:a,timelineNode:s,timelineMeta:o,cascadeNote:u,userCascadeNode:c,userCascadeSummary:b,technicalCascadeNode:h,technicalCascadeSummary:E,refreshRunsBtn:R},withThinkingWheel:N,setFlash:q});P.bindEvents(),P.renderTabs(),bn({stateController:$,withThinkingWheel:N,setFlash:q,refreshRuns:P.refreshRuns,refreshIngestion:async()=>{}})}const $a=Object.freeze(Object.defineProperty({__proto__:null,mountBackstageApp:la,mountOpsApp:ca},Symbol.toStringTag,{value:"Module"}));export{ca as a,Mn as b,_a as c,ya as d,$a as e,la as m,va as o,Ln as r,ha as s};
