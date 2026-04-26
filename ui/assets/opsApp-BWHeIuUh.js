import{q as ce}from"./bootstrap-BApbUZ11.js";import{g as Ne,p as ze,A as st}from"./client-OE0sHIIg.js";import{p as qt}from"./colors-ps0hVFT8.js";import{g as bt}from"./index-DF3uq1vv.js";import{getToastController as an}from"./toasts-Dx3CUztl.js";import{c as Ze}from"./button-1yFzSXrY.js";import{c as Ln}from"./badge-UV61UhzD.js";import{c as Qe}from"./chip-Bjq03GaS.js";function Tn(){return`
    <main id="lia-ingest-shell" class="lia-ingest-shell" data-lia-template="ingest-sesiones">
      <header class="lia-ingest-shell__header">
        <p class="lia-ingest-shell__eyebrow">Lia Graph · Lane 0</p>
        <h1 class="lia-ingest-shell__title">Sesiones de ingesta</h1>
        <p class="lia-ingest-shell__lede">
          Surface administrativa de la pipeline de ingestión Lia Graph.
          Tres flujos disponibles: <strong>delta aditivo</strong> (solo cambios),
          <strong>ingesta completa</strong> (reconstrucción total) y
          <strong>intake de archivos</strong> (arrastre puntual).
          Para promover WIP → Cloud, usa la pestaña Promoción.
        </p>
      </header>

      <section class="lia-ingest-shell__section">
        <header class="lia-ingest-shell__section-header">
          <p class="lia-ingest-shell__section-eyebrow">Contexto</p>
          <h2 class="lia-ingest-shell__section-title">Corpus activo</h2>
        </header>
        <div class="lia-ingest-shell__row" data-slot="corpus-health"></div>
        <div class="lia-ingest-shell__row" data-slot="corpus-overview"></div>
      </section>

      <section class="lia-ingest-shell__section lia-ingest-shell__section--howto">
        <header class="lia-ingest-shell__section-header">
          <p class="lia-ingest-shell__section-eyebrow">Cómo funciona</p>
          <h2 class="lia-ingest-shell__section-title">El corpus vive en <code>knowledge_base/</code></h2>
          <p class="lia-ingest-shell__section-lede">
            Lia no usa una carpeta de uploads: todos los documentos viven en
            <code>knowledge_base/</code> en disco (~1.3k archivos markdown hoy).
            Los tres flujos de abajo interactúan con esa carpeta así:
          </p>
        </header>
        <ol class="lia-ingest-shell__howto-steps">
          <li>
            <strong>1. Agregar / cambiar / borrar archivos</strong> en
            <code>knowledge_base/</code>. Tres formas:
            (a) <em>arrastrar archivos</em> abajo (los clasifica AUTOGENERAR
            y los guarda ahí); (b) sincronizar desde Dropbox; (c) editar
            directamente los <code>.md</code> con tu editor.
          </li>
          <li>
            <strong>2. Procesar esos cambios hacia Supabase + FalkorDB</strong>
            usando Delta aditivo (rápido, solo el diff) o Ingesta completa
            (lento, reconstruye todo).
          </li>
          <li>
            <strong>3. Promover a la nube</strong> desde la pestaña Promoción
            cuando la base local esté validada.
          </li>
        </ol>
      </section>

      <section class="lia-ingest-shell__section">
        <header class="lia-ingest-shell__section-header">
          <p class="lia-ingest-shell__section-eyebrow">Paso 1 · Agregar archivos al corpus</p>
          <h2 class="lia-ingest-shell__section-title">Arrastrar archivos</h2>
          <p class="lia-ingest-shell__section-lede">
            Sube archivos individuales o carpetas. AUTOGENERAR los clasifica
            (tema, subtema, tipo) y los escribe a <code>knowledge_base/</code>.
            Si ya pones los archivos ahí por Dropbox o editor directo, puedes
            saltarte este paso.
          </p>
        </header>
        <div class="lia-ingest-shell__grid lia-ingest-shell__grid--phase5">
          <div class="lia-ingest-shell__col lia-ingest-shell__col--primary" data-slot="intake-zone"></div>
          <div class="lia-ingest-shell__col lia-ingest-shell__col--secondary" data-slot="progress-timeline"></div>
        </div>
      </section>

      <section class="lia-ingest-shell__section" data-active-flow="delta">
        <header class="lia-ingest-shell__section-header">
          <p class="lia-ingest-shell__section-eyebrow">Paso 2 · Procesar cambios</p>
          <h2 class="lia-ingest-shell__section-title">Elige el flujo correcto</h2>
          <p class="lia-ingest-shell__section-lede">
            Ambos flujos <strong>leen de <code>knowledge_base/</code></strong> en
            disco — no hay upload aquí. Elige UN flujo a la vez: el otro se
            deshabilita para evitar doble-click.
          </p>
        </header>
        <div class="lia-ingest-shell__flow-toggle" data-slot="flow-toggle"></div>
        <div class="lia-ingest-shell__grid lia-ingest-shell__grid--flow">
          <div class="lia-ingest-shell__col lia-ingest-shell__col--primary" data-flow-card="delta" data-slot="additive-delta"></div>
          <div class="lia-ingest-shell__col lia-ingest-shell__col--secondary" data-flow-card="full" data-slot="run-trigger"></div>
        </div>
      </section>

      <section class="lia-ingest-shell__section lia-ingest-shell__section--promote-hint">
        <header class="lia-ingest-shell__section-header">
          <p class="lia-ingest-shell__section-eyebrow">Paso 3 · Promover a la nube</p>
          <h2 class="lia-ingest-shell__section-title">(vive en otra pestaña)</h2>
          <p class="lia-ingest-shell__section-lede">
            Cuando el paso 2 termine y la base local esté validada, ve a la
            pestaña <strong>Promoción</strong> (arriba, junto a "Ingesta") para
            empujar los cambios de la base local a Supabase + FalkorDB en la
            nube. Esto afecta lo que ven los usuarios en producción.
          </p>
        </header>
      </section>

      <section class="lia-ingest-shell__section">
        <header class="lia-ingest-shell__section-header">
          <p class="lia-ingest-shell__section-eyebrow">Telemetría compartida</p>
          <h2 class="lia-ingest-shell__section-title">Progreso y bitácora</h2>
        </header>
        <div class="lia-ingest-shell__row" data-slot="log-console"></div>
        <div class="lia-ingest-shell__row" data-slot="generations-list"></div>
      </section>
    </main>
  `}function Rn(e){return`
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
  `}function Mn(e){return`
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
  `}function qn(e){return`
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
        ${Tn()}
      </div>

      <div id="ingestion-section-promocion" class="ingestion-section" role="tabpanel" hidden></div>

      <div id="ingestion-section-subtopics" class="ingestion-section" role="tabpanel" hidden></div>
    </div>
  `}function Dn(){return`
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
  `}function Fn(e){return`
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
      ${Rn()}
    </main>
  `}const oo=Object.freeze(Object.defineProperty({__proto__:null,renderBackstageShell:Mn,renderIngestionShell:qn,renderOpsShell:Fn,renderPromocionShell:Dn},Symbol.toStringTag,{value:"Module"})),On=2e3;function V(e){return String(e??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#39;")}function fe(e){return(e??0).toLocaleString("es-CO")}function Bn(e){if(!e)return"-";try{return new Date(e).toLocaleDateString("es-CO",{day:"numeric",month:"short",hour:"2-digit",minute:"2-digit",timeZone:"America/Bogota"})}catch{return e}}function Dt(e){if(!e)return"-";const t=Date.parse(e);if(Number.isNaN(t))return e;const n=Math.max(0,Math.floor((Date.now()-t)/1e3));if(n<5)return"ahora";if(n<60)return`hace ${n}s`;const a=Math.floor(n/60),s=n%60;return a<60?`hace ${a}m ${s}s`:`hace ${Math.floor(a/60)}h ${a%60}m`}function je(e){return e?e.length>24?`${e.slice(0,15)}…${e.slice(-8)}`:e:"-"}function jn(e){return e===void 0?'<span class="ops-dot ops-dot-unknown">●</span>':e?'<span class="ops-dot ops-dot-ok">●</span>':'<span class="ops-dot ops-dot-error">●</span>'}function Ft(e,t){if(!t.available)return`
      <div class="corpus-card corpus-card-unavailable">
        <h4 class="corpus-card-title">${V(e)}</h4>
        <p class="corpus-card-unavail">● no disponible</p>
        ${t.error?`<p class="ops-subcopy">${V(t.error)}</p>`:""}
      </div>`;const n=t.knowledge_class_counts??{};return`
    <div class="corpus-card">
      <h4 class="corpus-card-title">${V(e)}</h4>
      <div class="corpus-card-row"><span>Gen:</span> <code>${V(je(t.generation_id))}</code></div>
      <div class="corpus-card-row"><span>Documentos:</span> <strong>${fe(t.documents)}</strong></div>
      <div class="corpus-card-row"><span>Chunks:</span> <strong>${fe(t.chunks)}</strong></div>
      <div class="corpus-card-row"><span>Embeddings:</span> ${jn(t.embeddings_complete)} ${t.embeddings_complete?"completos":"incompletos"}</div>
      <div class="corpus-card-sep"></div>
      <div class="corpus-card-row corpus-card-row-sm"><span>normative_base:</span> ${fe(n.normative_base)}</div>
      <div class="corpus-card-row corpus-card-row-sm"><span>interpretative:</span> ${fe(n.interpretative_guidance)}</div>
      <div class="corpus-card-row corpus-card-row-sm"><span>practica_erp:</span> ${fe(n.practica_erp)}</div>
      <div class="corpus-card-sep"></div>
      <div class="corpus-card-row corpus-card-row-sm"><span>${e==="PRODUCTION"?"Activado:":"Actualizado:"}</span> ${V(Bn(t.activated_at))}</div>
    </div>`}function Ot(e,t={}){const{onlyFailures:n=!1}=t,a=(e??[]).filter(s=>n?!s.ok:!0);return a.length===0?"":`
    <ul class="corpus-checks">
      ${a.map(s=>`
            <li class="corpus-check ${s.ok?"is-ok":"is-fail"}">
              <span class="corpus-check-dot"></span>
              <div>
                <strong>${V(s.label)}</strong>
                <span>${V(s.detail)}</span>
              </div>
            </li>`).join("")}
    </ul>`}function zn(e){const t=e??[];return t.length===0?"":`
    <ol class="corpus-stage-list">
      ${t.map(n=>`
            <li class="corpus-stage-item state-${V(n.state)}">
              <span class="corpus-stage-dot"></span>
              <span>${V(n.label)}</span>
            </li>`).join("")}
    </ol>`}function gt(e){const t=String(e||"").trim();return t?t.replaceAll("_"," "):"-"}function Hn(e){return e?e.kind==="audit"?"Audit":e.kind==="rollback"?"Rollback":e.mode==="force_reset"?"Force reset":"Promote":"Promote"}function vt(e){const t=e==null?void 0:e.last_checkpoint;if(!(t!=null&&t.phase))return"-";const n=t.cursor??0,a=t.total??0,s=a>0?(n/a*100).toFixed(1):"0";return`${gt(t.phase)} · ${fe(n)} / ${fe(a)} (${s}%)`}function Bt(e){var a,s;const t=((a=e==null?void 0:e.last_checkpoint)==null?void 0:a.cursor)??(e==null?void 0:e.batch_cursor)??0,n=((s=e==null?void 0:e.last_checkpoint)==null?void 0:s.total)??0;return n<=0?0:Math.min(100,Math.max(0,t/n*100))}function Un(e){if(!(e!=null&&e.heartbeat_at))return{label:"-",className:""};const t=Math.max(0,(Date.now()-Date.parse(e.heartbeat_at))/1e3);return t<15?{label:"Saludable",className:"hb-healthy"}:t<45?{label:"Lento",className:"hb-slow"}:{label:"Sin respuesta",className:"hb-stale"}}function Wn(e,t){var n,a,s,o,i,l;if(e)switch(e.operation_state_code){case"orphaned_queue":return{severity:"red",title:"Orphaned before start",detail:"The request was queued, but the backend worker never started."};case"stalled_resumable":return{severity:"red",title:"Stalled",detail:(n=e.last_checkpoint)!=null&&n.phase?`Backend stalled after ${gt(e.last_checkpoint.phase)}. Resume is available.`:"Backend stalled, but a checkpoint is available to resume."};case"failed_resumable":return{severity:"red",title:"Resumable",detail:e.error||((s=(a=e.failures)==null?void 0:a[0])==null?void 0:s.message)||"The last run failed after writing a checkpoint. Resume is available."};case"completed":return{severity:"green",title:"Completed",detail:e.kind==="audit"?"WIP audit completed. Artifact written.":e.kind==="rollback"?"Rollback completed and verified.":"Promotion completed and verified."};case"running":return{severity:"yellow",title:"Running",detail:e.current_phase?`Backend phase: ${gt(e.current_phase)}.`:e.stage_label?`Stage: ${e.stage_label}.`:"The backend is processing the promotion."};default:return{severity:e.severity??"red",title:e.severity==="yellow"?"Running":"Failed",detail:e.error||((i=(o=e.failures)==null?void 0:o[0])==null?void 0:i.message)||"The operation ended with an error."}}return t!=null&&t.preflight_ready?{severity:"green",title:"Ready",detail:"WIP audit and promotion preflight are green."}:{severity:"red",title:"Blocked",detail:((l=t==null?void 0:t.preflight_reasons)==null?void 0:l[0])||"Production is not ready for a safe promotion."}}function Jn(e){return e?e.kind==="audit"?"WIP Health Audit":e.kind==="rollback"?"Rollback Production":e.mode==="force_reset"?"Force Reset + Promote Production":"Promote WIP to Production":"Promote WIP to Production"}function jt(e,t){return!t||t.available===!1?`<tr><td>${V(e)}</td><td colspan="2" class="corpus-report-unavail">no disponible</td></tr>`:`
    <tr>
      <td>${V(e)}</td>
      <td><code>${V(je(t.generation_id))}</code></td>
      <td>${fe(t.documents)} docs · ${fe(t.chunks)} chunks</td>
    </tr>`}function zt(e,t){const n=new Set;for(const s of Object.keys((e==null?void 0:e.knowledge_class_counts)??{}))n.add(s);for(const s of Object.keys((t==null?void 0:t.knowledge_class_counts)??{}))n.add(s);return n.size===0?"":[...n].sort().map(s=>{const o=((e==null?void 0:e.knowledge_class_counts)??{})[s]??0,i=((t==null?void 0:t.knowledge_class_counts)??{})[s]??0,l=i-o,d=l>0?"is-positive":l<0?"is-negative":"",r=l>0?`+${fe(l)}`:l<0?fe(l):"—";return`
        <tr class="corpus-report-kc-row">
          <td>${V(s)}</td>
          <td>${fe(o)}</td>
          <td>${fe(i)}</td>
          <td class="corpus-report-delta ${d}">${r}</td>
        </tr>`}).join("")}function Gn(e,t){if(!e||!t)return"-";const n=Date.parse(e),a=Date.parse(t);if(Number.isNaN(n)||Number.isNaN(a))return"-";const s=Math.max(0,Math.floor((a-n)/1e3)),o=Math.floor(s/60),i=s%60;return o===0?`${i}s`:`${o}m ${i}s`}function Kn(e){const t=e==null?void 0:e.promotion_summary;if(!t)return"";const{before:n,after:a,delta:s,plan_result:o}=t,i=((s==null?void 0:s.documents)??0)>0?`+${fe(s==null?void 0:s.documents)}`:fe(s==null?void 0:s.documents),l=((s==null?void 0:s.chunks)??0)>0?`+${fe(s==null?void 0:s.chunks)}`:fe(s==null?void 0:s.chunks),d=((s==null?void 0:s.documents)??0)>0?"is-positive":((s==null?void 0:s.documents)??0)<0?"is-negative":"",r=((s==null?void 0:s.chunks)??0)>0?"is-positive":((s==null?void 0:s.chunks)??0)<0?"is-negative":"",b=n||a?`
      <table class="corpus-report-table">
        <thead>
          <tr><th></th><th>Generación</th><th>Documentos / Chunks</th></tr>
        </thead>
        <tbody>
          ${jt("Antes",n)}
          ${jt("Después",a)}
        </tbody>
        ${s?`
        <tfoot>
          <tr>
            <td>Delta</td>
            <td></td>
            <td>
              <span class="corpus-report-delta ${d}">${i} docs</span> ·
              <span class="corpus-report-delta ${r}">${l} chunks</span>
            </td>
          </tr>
        </tfoot>`:""}
      </table>
      ${zt(n,a)?`
      <table class="corpus-report-table corpus-report-table-kc">
        <thead><tr><th>Clase</th><th>Antes</th><th>Después</th><th>Delta</th></tr></thead>
        <tbody>${zt(n,a)}</tbody>
      </table>`:""}`:"",f=o?`
      <div class="corpus-report-grid">
        ${[{label:"Docs staged",key:"docs_staged"},{label:"Docs upserted",key:"docs_upserted"},{label:"Docs new",key:"docs_new"},{label:"Docs removed",key:"docs_removed"},{label:"Chunks new",key:"chunks_new"},{label:"Chunks changed",key:"chunks_changed"},{label:"Chunks removed",key:"chunks_removed"},{label:"Chunks unchanged",key:"chunks_unchanged"},{label:"Chunks embedded",key:"chunks_embedded"}].filter(E=>o[E.key]!==void 0&&o[E.key]!==null).map(E=>`
              <div class="corpus-report-stat">
                <span class="corpus-report-stat-value">${V(String(o[E.key]??"-"))}</span>
                <span class="corpus-report-stat-label">${V(E.label)}</span>
              </div>`).join("")}
      </div>`:"",w=Gn(e==null?void 0:e.started_at,e==null?void 0:e.completed_at);return`
    <div class="corpus-section corpus-report-section">
      <h4>Promotion Report</h4>
      ${b}
      ${f}
      ${w!=="-"?`<p class="corpus-report-duration">Duración: <strong>${V(w)}</strong></p>`:""}
    </div>`}function on({dom:e,setFlash:t}){let n=null,a=null,s=null,o="",i="",l=null,d=null,r=!1,b=!1,C=!1,f=!1,w=0,E=null,p=0;function _(q,j){a&&clearTimeout(a),t(q,j);const N=e.container.querySelector(".corpus-toast");N&&(N.hidden=!1,N.dataset.tone=j,N.textContent=q,N.classList.remove("corpus-toast-enter"),N.offsetWidth,N.classList.add("corpus-toast-enter")),a=setTimeout(()=>{const $=e.container.querySelector(".corpus-toast");$&&($.hidden=!0)},6e3)}function g(q,j,N,$="promote"){return new Promise(z=>{d==null||d.remove();const O=document.createElement("div");O.className="corpus-confirm-overlay",d=O,O.innerHTML=`
        <div class="corpus-confirm-dialog">
          <h3 class="corpus-confirm-title">${V(q)}</h3>
          <div class="corpus-confirm-body">${j}</div>
          <div class="corpus-confirm-actions">
            <button class="corpus-btn corpus-btn-rollback" data-action="cancel">Cancelar</button>
            <button class="corpus-btn ${$==="rollback"?"corpus-btn-rollback":"corpus-btn-promote"}" data-action="confirm">${V(N)}</button>
          </div>
        </div>
      `,document.body.appendChild(O),requestAnimationFrame(()=>O.classList.add("is-visible"));function M(I){d===O&&(d=null),O.classList.remove("is-visible"),setTimeout(()=>O.remove(),180),z(I)}O.addEventListener("click",I=>{const K=I.target.closest("[data-action]");K?M(K.dataset.action==="confirm"):I.target===O&&M(!1)})})}async function m(q,j,N,$){if(!o){o=N,A();try{const{response:z,data:O}=await ze(q,j);z.ok&&(O!=null&&O.job_id)?(l={tone:"success",message:`${$} Job ${je(O.job_id)}.`},_(`${$} Job ${je(O.job_id)}.`,"success")):(l={tone:"error",message:(O==null?void 0:O.error)||"No se pudo iniciar la operación."},_((O==null?void 0:O.error)||"No se pudo iniciar la operación.","error"))}catch(z){const O=z instanceof Error?z.message:String(z);l={tone:"error",message:O},_(O,"error")}finally{o="",await B()}}}async function u(){const q=n;if(!q||o||!await g("Promote WIP to Production",`<p>This path reuses the live WIP generation and promotes it incrementally into Production with persisted checkpoints.</p>
       <table class="corpus-confirm-table">
         <tr><td>Production current:</td><td><strong>${fe(q.production.documents)}</strong> docs · <strong>${fe(q.production.chunks)}</strong> chunks</td></tr>
         <tr><td>WIP source:</td><td><strong>${fe(q.wip.documents)}</strong> docs · <strong>${fe(q.wip.chunks)}</strong> chunks</td></tr>
         <tr><td>WIP generation:</td><td><code>${V(je(q.wip.generation_id))}</code></td></tr>
       </table>
       <label style="display:flex;align-items:center;gap:0.4rem;margin:0.75rem 0;font-size:0.85rem;cursor:pointer">
         <input type="checkbox" id="corpus-force-full-upsert" />
         Forzar upsert completo (sincronizar summaries + embeddings aunque chunk_text no haya cambiado)
       </label>
       <p class="corpus-confirm-note">The backend will keep a promotion plan, batch checkpoints, and a resumable cursor before activation.</p>`,"Promote now"))return;const N=document.querySelector("#corpus-force-full-upsert"),$=(N==null?void 0:N.checked)??!1;f=!1,w=0,E=null,p=0,await m("/api/ops/corpus/rebuild-from-wip",{mode:"promote",force_full_upsert:$},"promote",$?"Promotion started (force full upsert).":"Promotion started.")}async function c(){var N;const q=(n==null?void 0:n.current_operation)??(n==null?void 0:n.last_operation)??null;!(q!=null&&q.resume_job_id)||o||!await g("Resume from Checkpoint",`<p>The backend will reuse the persisted promotion plan and continue from the last completed checkpoint.</p>
       <table class="corpus-confirm-table">
         <tr><td>Job:</td><td><code>${V(je(q.resume_job_id))}</code></td></tr>
         <tr><td>Checkpoint:</td><td>${V(vt(q))}</td></tr>
         <tr><td>Target generation:</td><td><code>${V(je(q.target_generation_id))}</code></td></tr>
       </table>`,"Resume now")||(f=!0,w=((N=q.last_checkpoint)==null?void 0:N.cursor)??0,E=null,p=0,await m("/api/ops/corpus/rebuild-from-wip/resume",{job_id:q.resume_job_id},"resume","Resume started."))}async function y(){const q=n;!q||!q.rollback_generation_id||o||!await g("Rollback de Production",`<p>Se va a intentar reactivar una generación previa de production.</p>
       <table class="corpus-confirm-table">
         <tr><td>Production actual:</td><td><code>${V(je(q.production.generation_id))}</code></td></tr>
         <tr><td>Objetivo:</td><td><code>${V(je(q.rollback_generation_id))}</code></td></tr>
       </table>
       <p class="corpus-confirm-note">Solo se habilita si el backend detecta una generación previa todavía utilizable.</p>`,"Revertir ahora","rollback")||await m("/api/ops/corpus/rollback",{generation_id:q.rollback_generation_id},"rollback","Rollback started.")}async function v(){o||await m("/api/ops/corpus/wip-audit",{},"audit","WIP audit started.")}async function k(){o||!await g("Reiniciar promoción",`<p>Cancela cualquier job anterior y lanza una nueva promoción desde WIP a producción.</p>
       <label style="display:flex;align-items:center;gap:0.4rem;margin:0.75rem 0;font-size:0.85rem;cursor:default;opacity:0.55" title="Force upsert es obligatorio en reinicio">
         <input type="checkbox" checked disabled style="opacity:0.55" />
         Forzar upsert completo (sincronizar summaries + embeddings aunque chunk_text no haya cambiado)
       </label>
       <p class="corpus-confirm-note">Reiniciar siempre usa force upsert: todos los ~50K chunks se copian completos.</p>`,"Reiniciar ahora","rollback")||(f=!1,w=0,E=null,p=0,await m("/api/ops/corpus/rebuild-from-wip/restart",{},"restart","Restart submitted (force full upsert)."))}async function P(){if(!(C||o||!await g("Sincronizar JSONL a WIP",`<p>Se va a sincronizar el índice JSONL local ya existente al Supabase WIP (Docker).</p>
       <p class="corpus-confirm-note">Esta operación no ejecuta reindex — solo sincroniza los documentos y chunks que ya existen en el JSONL local. Es segura e idempotente.</p>`,"Sincronizar ahora"))){C=!0,A();try{const{response:j,data:N}=await ze("/api/ops/corpus/sync-to-wip",{});j.ok&&(N!=null&&N.synced)?_(`WIP sincronizado: ${fe(N.documents)} docs, ${fe(N.chunks)} chunks.`,"success"):_((N==null?void 0:N.error)||"Error sincronizando a WIP.","error")}catch(j){const N=j instanceof Error?j.message:String(j);_(N||"Error sincronizando a WIP.","error")}finally{C=!1,await B()}}}async function T(){const q=(n==null?void 0:n.current_operation)??(n==null?void 0:n.last_operation)??null,j=String((q==null?void 0:q.log_tail)||"").trim();if(j)try{await navigator.clipboard.writeText(j),_("Log tail copied.","success")}catch(N){const $=N instanceof Error?N.message:"Could not copy log tail.";_($||"Could not copy log tail.","error")}}function A(){var Pe,Se,X,$e,me,Ae,qe,De,he,Le,Te;const q=e.container.querySelector(".corpus-log-accordion");q&&(r=q.open);const j=e.container.querySelector(".corpus-checks-accordion");j&&(b=j.open);const N=n;if(!N){e.container.innerHTML=`<p class="ops-empty">${V(i||"Cargando estado del corpus…")}</p>`;return}const $=N.current_operation??N.last_operation??null,z=Wn($,N),O=!!(N.current_operation&&["queued","running"].includes(N.current_operation.status))||!!o,M=O||!N.preflight_ready,I=!O&&!!($&&$.resume_supported&&$.resume_job_id&&($.operation_state_code==="stalled_resumable"||$.operation_state_code==="failed_resumable")),K=O||!N.rollback_available,h=N.delta.documents==="+0"&&N.delta.chunks==="+0"?"Sin delta pendiente":`${N.delta.documents} documentos · ${N.delta.chunks} chunks`,S=Ot($==null?void 0:$.checks,{onlyFailures:!0}),D=Ot($==null?void 0:$.checks),F=!!(N.current_operation&&["queued","running"].includes(N.current_operation.status)),Q=l&&!(N.current_operation&&["queued","running"].includes(N.current_operation.status))?`
          <div class="corpus-callout tone-${V(l.tone==="success"?"green":"red")}">
            <strong>${l.tone==="success"?"Request sent":"Request failed"}</strong>
            <span>${V(l.message)}</span>
          </div>`:"",se=(Pe=$==null?void 0:$.last_checkpoint)!=null&&Pe.phase?(()=>{const ue=$.operation_state_code==="completed"?"green":$.operation_state_code==="failed_resumable"||$.operation_state_code==="stalled_resumable"?"red":"yellow",_e=Bt($);return`
            <div class="corpus-callout tone-${V(ue)}">
              <strong>Checkpoint</strong>
              <span>${V(vt($))} · ${V(Dt($.last_checkpoint.at||null))}</span>
              ${_e>0&&ue!=="green"?`<div class="corpus-progress-bar corpus-progress-bar-sm"><div class="corpus-progress-fill" style="width:${_e.toFixed(1)}%"></div></div>`:""}
            </div>`})():"";e.container.innerHTML=`
      <div class="corpus-cards">
        ${Ft("WIP",N.wip)}
        ${Ft("PRODUCTION",N.production)}
      </div>
      <div class="corpus-delta">
        <span class="corpus-delta-label">${V(h)}</span>
      </div>
      <section class="corpus-operation-panel severity-${V(z.severity)}">
        <div class="corpus-operation-header">
          <div>
            <div class="corpus-status-chip tone-${V(z.severity)}${z.severity==="yellow"?" is-pulsing":""}">
              ${V(z.title)}
            </div>
            <h3 class="corpus-operation-title">${V(Jn($))}</h3>
            <p class="corpus-operation-detail">${V(z.detail)}</p>
          </div>
          <dl class="corpus-operation-meta">
            <div><dt>Heartbeat</dt><dd>${V(Dt(($==null?void 0:$.heartbeat_at)||($==null?void 0:$.updated_at)||null))}</dd></div>
            <div><dt>Backend</dt><dd>${V(Hn($))}${$!=null&&$.force_full_upsert?` <span style="background:${qt.amber[100]};color:${qt.amber[600]};padding:0.1rem 0.4rem;border-radius:0.3rem;font-size:0.7rem;font-weight:700">FORCE UPSERT</span>`:""}</dd></div>
            <div><dt>Phase</dt><dd>${V($!=null&&$.current_phase?gt($.current_phase):($==null?void 0:$.stage_label)||(N.preflight_ready?"Ready":"Blocked"))}</dd></div>
            <div><dt>Checkpoint</dt><dd>${V(vt($))}</dd></div>
            <div><dt>WIP</dt><dd><code>${V(je(($==null?void 0:$.source_generation_id)||N.wip.generation_id))}</code></dd></div>
            <div><dt>Target</dt><dd><code>${V(je(($==null?void 0:$.target_generation_id)||($==null?void 0:$.production_generation_id)||N.production.generation_id))}</code></dd></div>
            <div><dt>Prod</dt><dd><code>${V(je(($==null?void 0:$.production_generation_id)||N.production.generation_id))}</code></dd></div>
          </dl>
        </div>
        ${F?(()=>{var be,re;const ue=Bt($),_e=((be=$==null?void 0:$.last_checkpoint)==null?void 0:be.cursor)??($==null?void 0:$.batch_cursor)??0,R=((re=$==null?void 0:$.last_checkpoint)==null?void 0:re.total)??0,G=Un($);if(_e>0&&R>0){const de=Date.now();if(E&&_e>E.cursor){const Y=Math.max(1,(de-E.ts)/1e3),te=(_e-E.cursor)/Y;p=p>0?p*.7+te*.3:te}E={cursor:_e,ts:de}}const ie=p>0?`${p.toFixed(0)} chunks/s`:"",ne=R-_e,ee=p>0&&ne>0?(()=>{const de=Math.ceil(ne/p),Y=Math.floor(de/60),te=de%60;return Y>0?`~${Y}m ${te}s restante`:`~${te}s restante`})():"";return`
            <div class="corpus-progress-bar"><div class="corpus-progress-fill" style="width:${ue.toFixed(1)}%"></div></div>
            <div class="corpus-progress-detail">
              ${f?`<span class="corpus-resume-badge">REANUDADO desde ${fe(w)}</span>`:""}
              <span class="corpus-progress-nums">${fe(_e)} / ${fe(R)} (${ue.toFixed(1)}%)</span>
              ${ie?`<span class="corpus-progress-rate">${V(ie)}</span>`:""}
              ${ee?`<span class="corpus-progress-eta">${V(ee)}</span>`:""}
              <span class="corpus-hb-badge ${G.className}">${V(G.label)}</span>
            </div>`})():""}
        ${(Se=$==null?void 0:$.stages)!=null&&Se.length?zn($.stages):""}
        ${se}
        ${(X=N.preflight_reasons)!=null&&X.length&&!F&&!N.preflight_ready?`
          <div class="corpus-callout tone-red">
            <strong>Preflight blocked</strong>
            <ul>${N.preflight_reasons.map(ue=>`<li>${V(ue)}</li>`).join("")}</ul>
          </div>`:""}
        ${Q}
        ${S?`<div class="corpus-section"><h4>Visible failures</h4>${S}</div>`:""}
        ${D?`
          <details class="corpus-section corpus-checks-accordion">
            <summary class="corpus-checks-summary"><h4>Checks</h4><span class="corpus-checks-count">${(($==null?void 0:$.checks)??[]).length}</span></summary>
            ${D}
          </details>`:""}
        ${Kn($)}
        ${$!=null&&$.log_tail?`
          <details class="corpus-section corpus-log-accordion">
            <summary class="corpus-log-summary">
              <h4>Backend log tail</h4>
              <button id="corpus-copy-log-tail-btn" type="button" class="corpus-btn corpus-btn-rollback corpus-btn-inline">Copy</button>
            </summary>
            <pre class="corpus-log-tail">${V($.log_tail)}</pre>
          </details>`:""}
        ${i?`
          <div class="corpus-callout tone-red">
            <strong>Refresh error</strong>
            <span>${V(i)}</span>
          </div>`:""}
      </section>
      <div class="corpus-actions">
        ${N.audit_missing&&!O?`
          <button id="corpus-audit-btn" class="corpus-btn corpus-btn-audit${o==="audit"?" is-busy":""}">
            ${o==="audit"?'<span class="corpus-spinner"></span> Auditing…':"Run WIP Audit"}
          </button>`:""}
        ${!O&&!C?`
          <button id="corpus-sync-wip-btn" class="corpus-btn corpus-btn-sync">Sincronizar JSONL a WIP</button>`:""}
        ${C?`
          <button class="corpus-btn corpus-btn-sync is-busy" disabled><span class="corpus-spinner"></span> Sincronizando…</button>`:""}
        <button id="corpus-promote-btn" class="corpus-btn corpus-btn-promote${o==="promote"?" is-busy":""}" ${M?"disabled":""}>
          ${o==="promote"?'<span class="corpus-spinner"></span> Starting…':"Promote WIP to Production"}
        </button>
        ${I?`
          <button id="corpus-resume-btn" class="corpus-btn corpus-btn-promote${o==="resume"?" is-busy":""}">
            ${o==="resume"?'<span class="corpus-spinner"></span> Resuming…':"Resume from Checkpoint"}
          </button>`:""}
        <button id="corpus-rollback-btn" class="corpus-btn corpus-btn-rollback${o==="rollback"?" is-busy":""}" ${K?"disabled":""}>
          ${o==="rollback"?'<span class="corpus-spinner"></span> Starting rollback…':"Rollback"}
        </button>
        <button id="corpus-restart-btn" class="corpus-btn corpus-btn-rollback${o==="restart"?" is-busy":""}" ${O?"disabled":""}>
          ${o==="restart"?'<span class="corpus-spinner"></span> Restarting…':"Reiniciar promoción (force upsert)"}
        </button>
      </div>
      ${N.preflight_ready?"":`
        <p class="corpus-action-note">${V((($e=N.preflight_reasons)==null?void 0:$e[0])||"Promotion is blocked by preflight.")}</p>`}
      ${N.rollback_available?"":`
        <p class="corpus-action-note">${V(N.rollback_reason||"Rollback is not available yet.")}</p>`}
      <div class="corpus-toast ops-flash" hidden></div>
    `,(me=e.container.querySelector("#corpus-audit-btn"))==null||me.addEventListener("click",v),(Ae=e.container.querySelector("#corpus-sync-wip-btn"))==null||Ae.addEventListener("click",()=>void P()),(qe=e.container.querySelector("#corpus-promote-btn"))==null||qe.addEventListener("click",u),(De=e.container.querySelector("#corpus-resume-btn"))==null||De.addEventListener("click",c),(he=e.container.querySelector("#corpus-rollback-btn"))==null||he.addEventListener("click",y),(Le=e.container.querySelector("#corpus-restart-btn"))==null||Le.addEventListener("click",k),(Te=e.container.querySelector("#corpus-copy-log-tail-btn"))==null||Te.addEventListener("click",ue=>{ue.preventDefault(),ue.stopPropagation(),T()});const ae=e.container.querySelector(".corpus-log-accordion");ae&&r&&(ae.open=!0);const we=e.container.querySelector(".corpus-checks-accordion");we&&b&&(we.open=!0)}async function B(){try{n=await Ne("/api/ops/corpus-status"),i="",n!=null&&n.current_operation&&["queued","running","completed","failed","cancelled"].includes(n.current_operation.status)&&(l=null)}catch(q){i=q instanceof Error?q.message:String(q),n===null&&(n=null)}A()}function J(){A(),s===null&&(s=window.setInterval(()=>{B()},On))}return{bindEvents:J,refresh:B}}const io=Object.freeze(Object.defineProperty({__proto__:null,createCorpusLifecycleController:on},Symbol.toStringTag,{value:"Module"})),Vn={normative_base:"Normativa",interpretative_guidance:"Interpretación",practica_erp:"Práctica"},It={declaracion_renta:"Renta",iva:"IVA",laboral:"Laboral",facturacion_electronica:"Facturación",estados_financieros_niif:"NIIF",ica:"ICA",calendario_obligaciones:"Calendarios",retencion_fuente:"Retención",regimen_sancionatorio:"Sanciones",regimen_cambiario:"Régimen Cambiario",impuesto_al_patrimonio:"Patrimonio",informacion_exogena:"Exógena",proteccion_de_datos:"Datos",obligaciones_mercantiles:"Mercantil",obligaciones_profesionales_contador:"Obligaciones Contador",rut_responsabilidades:"RUT",gravamen_movimiento_financiero_4x1000:"GMF 4×1000",beneficiario_final:"Beneficiario Final",contratacion_estatal:"Contratación Estatal",reforma_pensional:"Reforma Pensional",zomac_incentivos:"ZOMAC"},rn="lia_backstage_ops_active_tab",St="lia_backstage_ops_ingestion_session_id";function Xn(){const e=bt();try{const t=String(e.getItem(rn)||"").trim();return t==="ingestion"||t==="control"||t==="embeddings"||t==="reindex"?t:"monitor"}catch{return"monitor"}}function Yn(e){const t=bt();try{t.setItem(rn,e)}catch{}}function Zn(){const e=bt();try{return String(e.getItem(St)||"").trim()}catch{return""}}function Qn(e){const t=bt();try{if(!e){t.removeItem(St);return}t.setItem(St,e)}catch{}}function ht(e){return e==="processing"||e==="running_batch_gates"}function ln(e){if(!e)return!1;const t=String(e.status||"").toLowerCase();if(t==="done"||t==="completed")return!0;const n=e.documents||[];return n.length===0?!1:n.every(a=>{const s=String(a.status||"").toLowerCase();return s==="done"||s==="completed"||s==="skipped_duplicate"||s==="bounced"})}function ct(e){const t=String(e||"").trim().toLowerCase();return t==="failed"||t==="error"?"error":t==="processing"||t==="running_batch_gates"||t==="needs_retry_batch_gate"||t==="queued"||t==="uploading"||t==="extracting"||t==="etl"||t==="writing"||t==="gates"||t==="in_progress"||t==="partial_failed"||t==="raw"||t==="pending_dedup"?"warn":"ok"}function ke(e){return e instanceof st?e.message||`HTTP ${e.status}`:e instanceof Error?e.message:String(e||"unknown_error")}function es(e,t){switch(String(e||"").trim()){case"normative_base":return t.t("ops.ingestion.batchType.normative");case"interpretative_guidance":return t.t("ops.ingestion.batchType.interpretative");case"practica_erp":return t.t("ops.ingestion.batchType.practical");default:return String(e||"-")}}function ts(e,t){const n=Number(e||0);return!Number.isFinite(n)||n<=0?"0 B":n>=1024*1024?`${t.formatNumber(n/(1024*1024),{maximumFractionDigits:1})} MB`:n>=1024?`${t.formatNumber(n/1024,{maximumFractionDigits:1})} KB`:`${t.formatNumber(n)} B`}function Ht(e,t){const n=e||{total:0,queued:0,done:0,failed:0,pending_batch_gate:0,bounced:0},a=[`${t.t("ops.ingestion.summary.total")} ${n.total||0}`,`${t.t("ops.ingestion.summary.done")} ${n.done||0}`,`${t.t("ops.ingestion.summary.failed")} ${n.failed||0}`,`${t.t("ops.ingestion.summary.queued")} ${n.queued||0}`,`${t.t("ops.ingestion.summary.gate")} ${n.pending_batch_gate||0}`],s=Number(n.bounced||0);return s>0&&a.push(`Rebotados ${s}`),a.join(" · ")}function Et(e,t,n){const a=e||t||"";if(!a)return"stalled";const s=Date.parse(a);if(Number.isNaN(s))return"stalled";const o=Date.now()-s,i=n==="gates",l=i?9e4:3e4,d=i?3e5:12e4;return o<l?"alive":o<d?"slow":"stalled"}function ns(e,t){const n=e||t||"";if(!n)return"-";const a=Date.parse(n);if(Number.isNaN(a))return"-";const s=Math.max(0,Date.now()-a),o=Math.floor(s/1e3);if(o<5)return"ahora";if(o<60)return`hace ${o}s`;const i=Math.floor(o/60),l=o%60;return i<60?`hace ${i}m ${l}s`:`hace ${Math.floor(i/60)}h ${i%60}m`}const yt={validating:"validando corpus",manifest:"activando manifest",indexing:"reconstruyendo índice","indexing/scanning":"escaneando documentos","indexing/chunking":"generando chunks","indexing/writing_indexes":"escribiendo índices","indexing/syncing":"sincronizando Supabase","indexing/auditing":"auditando calidad"};function cn(e){if(!e)return"";if(yt[e])return yt[e];const t=e.indexOf(":");if(t>0){const n=e.slice(0,t),a=e.slice(t+1),s=yt[n];if(s)return`${s} (${a})`}return e}function ss(e){if(!e)return"";const t=Date.parse(e);if(Number.isNaN(t))return"";try{return new Intl.DateTimeFormat("es-CO",{timeZone:"America/Bogota",day:"2-digit",month:"2-digit",year:"numeric",hour:"2-digit",minute:"2-digit",second:"2-digit",hour12:!1}).format(new Date(t))}catch{return""}}function dn(e,t){const n=Math.max(0,Math.min(100,Number(e||0))),a=document.createElement("div");a.className="ops-progress";const s=document.createElement("div");s.className="ops-progress-bar";const o=document.createElement("span");o.className="ops-progress-fill",t==="gates"&&n>0&&n<100&&o.classList.add("ops-progress-active"),o.style.width=`${n}%`;const i=document.createElement("span");return i.className="ops-progress-label",i.textContent=`${n}%`,s.appendChild(o),a.append(s,i),a}function We(e){return String(e??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#39;")}function Ve(e){return(e??0).toLocaleString("es-CO")}function Ut(e){if(e==null||e<=0)return"-";const t=Math.floor(e/60),n=Math.floor(e%60);return t>0?`${t}m ${n}s`:`${n}s`}function un({dom:e,setFlash:t}){const{container:n}=e;let a=null,s="",o=!1,i=!1,l=0,d=0,r=3e3,b=[];function C(u){if(u<=0)return;const c=Date.now();if(u>l&&d>0){const y=c-d,v=u-l,k=y/v;b.push(k),b.length>10&&b.shift(),r=b.reduce((P,T)=>P+T,0)/b.length}u!==l&&(l=u,d=c)}function f(){if(d===0)return{level:"healthy",label:"Iniciando..."};const u=Date.now()-d,c=Math.max(r*3,1e4),y=Math.max(r*6,3e4);return u<c?{level:"healthy",label:"Saludable"}:u<y?{level:"caution",label:"Lento"}:{level:"failed",label:"Sin respuesta"}}function w(){var D,F,Q,se,ae,we,Pe,Se;const u=a;if(!u){n.innerHTML='<p class="ops-text-muted">Cargando estado de embeddings...</p>';return}const c=u.current_operation||u.last_operation,y=((D=u.current_operation)==null?void 0:D.status)??"",v=y==="running"||y==="queued"||s==="start",k=!u.current_operation&&!s,P=s==="stop",T=!v&&!P&&((c==null?void 0:c.status)==="cancelled"||(c==null?void 0:c.status)==="failed"||(c==null?void 0:c.status)==="stalled");let A="";const B=(c==null?void 0:c.status)??"",J=P?"Deteniendo...":v?"En ejecución":T?B==="stalled"?"Detenido (stalled)":B==="cancelled"?"Cancelado":"Fallido":k?"Inactivo":B||"—",q=v?"tone-yellow":B==="completed"?"tone-green":B==="failed"||B==="stalled"?"tone-red":B==="cancelled"?"tone-yellow":"",j=u.api_health,N=j!=null&&j.ok?"emb-api-ok":"emb-api-error",$=j?j.ok?`API OK (${j.detail})`:`API Error: ${j.detail}`:"API: verificando...";if(A+=`<div class="emb-status-row">
      <span class="corpus-status-chip ${q}">${We(J)}</span>
      <span class="emb-target-badge">WIP</span>
      <span class="emb-api-semaphore ${N}" title="${We($)}"><span class="emb-api-dot"></span> ${We(j!=null&&j.ok?"API OK":j?"API Error":"...")}</span>
      ${v?(()=>{const X=f();return`<span class="emb-process-health emb-health-${X.level}"><span class="emb-health-dot"></span> ${We(X.label)}</span>`})():""}
    </div>`,A+='<div class="emb-controls">',k?(A+=`<label class="emb-force-label"><input type="checkbox" id="emb-force-check" ${o?"checked":""} /> Forzar re-embed (todas)</label>`,A+=`<button class="corpus-btn corpus-btn-promote" id="emb-start-btn" ${s?"disabled":""}>Iniciar</button>`):P?A+='<span class="emb-running-label">Deteniendo al finalizar batch actual...</span>':v&&c&&(A+='<button class="corpus-btn corpus-btn-rollback" id="emb-stop-btn">Detener</button>',A+='<span class="emb-running-label">Embebiendo chunks...</span>'),T&&c){const X=c.force,$e=(F=c.progress)==null?void 0:F.last_cursor_id,me=(Q=c.progress)==null?void 0:Q.pct_complete,Ae=$e?`Reanudar desde ${typeof me=="number"?me.toFixed(1)+"%":"checkpoint"}`:"Reiniciar";X&&(A+='<span class="emb-force-label"><input type="checkbox" checked disabled /> Forzar re-embed (continuación)</span>'),A+=`<button class="corpus-btn corpus-btn-promote" id="emb-resume-btn" ${s?"disabled":""}>${We(Ae)}</button>`,A+=`<button class="corpus-btn" id="emb-start-btn" ${s?"disabled":""} style="opacity:0.7">Iniciar desde cero</button>`}A+="</div>";const z=c==null?void 0:c.progress,O=(v||s)&&(z==null?void 0:z.total),M=O?z.total:u.total_chunks,I=O?z.embedded:u.embedded_chunks,K=O?z.pending-z.embedded-(z.failed||0):u.null_embedding_chunks,h=O&&z.failed||0,S=O?z.pct_complete:u.coverage_pct;if(A+=`<div class="emb-stats-grid">
      <div class="emb-stat"><span class="emb-stat-value">${Ve(M)}</span><span class="emb-stat-label">Total</span></div>
      <div class="emb-stat"><span class="emb-stat-value">${Ve(I)}</span><span class="emb-stat-label">Embebidos</span></div>
      <div class="emb-stat"><span class="emb-stat-value">${Ve(Math.max(0,K))}</span><span class="emb-stat-label">Pendientes</span></div>
      ${h>0?`<div class="emb-stat emb-stat-error"><span class="emb-stat-value">${Ve(h)}</span><span class="emb-stat-label">Fallidos</span></div>`:`<div class="emb-stat"><span class="emb-stat-value">${S.toFixed(1)}%</span><span class="emb-stat-label">Cobertura</span></div>`}
    </div>`,v&&(c!=null&&c.progress)){const X=c.progress;A+='<div class="emb-live-progress">',A+='<div class="emb-progress-bar-wrap" id="emb-progress-mount"></div>',A+=`<div class="emb-rate-line">
        <span>${((se=X.rate_chunks_per_sec)==null?void 0:se.toFixed(1))??"-"} chunks/s</span>
        <span>ETA: ${Ut(X.eta_seconds)}</span>
        <span>Elapsed: ${Ut(X.elapsed_seconds)}</span>
        <span>Batch ${Ve(X.current_batch)} / ${Ve(X.total_batches)}</span>
      </div>`,X.failed>0&&(A+=`<p class="emb-failed-notice">${Ve(X.failed)} chunks fallidos (${(X.failed/Math.max(X.pending,1)*100).toFixed(2)}%)</p>`),A+="</div>"}if(c!=null&&c.quality_report){const X=c.quality_report;A+='<div class="emb-quality-report">',A+="<h3>Reporte de calidad</h3>",A+=`<div class="emb-stats-grid">
        <div class="emb-stat"><span class="emb-stat-value">${((ae=X.mean_cosine_similarity)==null?void 0:ae.toFixed(4))??"-"}</span><span class="emb-stat-label">Coseno medio</span></div>
        <div class="emb-stat"><span class="emb-stat-value">${((we=X.min_cosine_similarity)==null?void 0:we.toFixed(4))??"-"}</span><span class="emb-stat-label">Min</span></div>
        <div class="emb-stat"><span class="emb-stat-value">${((Pe=X.max_cosine_similarity)==null?void 0:Pe.toFixed(4))??"-"}</span><span class="emb-stat-label">Max</span></div>
        <div class="emb-stat"><span class="emb-stat-value">${Ve(X.sample_pairs)}</span><span class="emb-stat-label">Pares</span></div>
      </div>`,X.collapsed_warning&&(A+='<p class="emb-anomaly-warning">ANOMALIA: Embeddings colapsados (mean &gt; 0.95)</p>'),X.noise_warning&&(A+='<p class="emb-anomaly-warning">ANOMALIA: Embeddings ruidosos (mean &lt; 0.10)</p>'),!X.collapsed_warning&&!X.noise_warning&&(A+='<p class="emb-quality-ok">Distribución saludable</p>'),A+="</div>"}if((Se=c==null?void 0:c.checks)!=null&&Se.length){A+='<div class="emb-checks">';for(const X of c.checks){const $e=X.ok?'<span class="ops-dot ops-dot-ok">●</span>':'<span class="ops-dot ops-dot-error">●</span>';A+=`<div class="emb-check">${$e} <strong>${We(X.label)}</strong>: ${We(X.detail)}</div>`}A+="</div>"}if(c!=null&&c.log_tail){const X=c.log_tail.split(`
`).reverse().join(`
`);A+=`<details class="emb-log-accordion" id="emb-log-details" ${i?"open":""}><summary>Log</summary><pre class="emb-log-tail">${We(X)}</pre></details>`}if(c!=null&&c.error&&(A+=`<p class="emb-error">${We(c.error)}</p>`),n.innerHTML=A,v&&(c!=null&&c.progress)){const X=n.querySelector("#emb-progress-mount");X&&X.appendChild(dn(c.progress.pct_complete??0,"embedding"))}}function E(){n.addEventListener("click",u=>{const c=u.target;c.id==="emb-start-btn"&&p(),c.id==="emb-stop-btn"&&_(),c.id==="emb-resume-btn"&&g()}),n.addEventListener("change",u=>{const c=u.target;c.id==="emb-force-check"&&(o=c.checked)}),n.addEventListener("toggle",u=>{const c=u.target;c.id==="emb-log-details"&&(i=c.open)},!0)}async function p(){const u=o;s="start",o=!1,w();try{const{response:c,data:y}=await ze("/api/ops/embedding/start",{force:u});!c.ok||!(y!=null&&y.ok)?(t((y==null?void 0:y.error)||`Error ${c.status}`,"error"),s=""):t("Embedding iniciado","success")}catch(c){t(String(c),"error"),s=""}await m()}async function _(){var c;const u=(c=a==null?void 0:a.current_operation)==null?void 0:c.job_id;if(u){s="stop",w();try{await ze("/api/ops/embedding/stop",{job_id:u}),t("Stop solicitado — se detendrá al finalizar el batch actual","success")}catch(y){t(String(y),"error"),s=""}}}async function g(){const u=(a==null?void 0:a.current_operation)||(a==null?void 0:a.last_operation);if(u!=null&&u.job_id){s="start",w();try{const{response:c,data:y}=await ze("/api/ops/embedding/resume",{job_id:u.job_id});!c.ok||!(y!=null&&y.ok)?(t((y==null?void 0:y.error)||`Error ${c.status}`,"error"),s=""):t("Embedding reanudado desde checkpoint","success")}catch(c){t(String(c),"error"),s=""}s="",await m()}}async function m(){try{const u=await Ne("/api/ops/embedding-status");a=u;const c=u.current_operation;if(c!=null&&c.progress){const y=c.progress.current_batch;typeof y=="number"&&C(y)}s==="stop"&&!u.current_operation&&(s=""),s==="start"&&u.current_operation&&(s=""),u.current_operation||(l=0,d=0,b=[])}catch{}w()}return{bindEvents:E,refresh:m}}const ro=Object.freeze(Object.defineProperty({__proto__:null,createOpsEmbeddingsController:un},Symbol.toStringTag,{value:"Module"})),as=["pending","processing","done"],os={pending:"Pendiente",processing:"En proceso",done:"Procesado"},is={pending:"⏳",processing:"🔄",done:"✅"},rs=5;function pn(e){const t=String(e||"").toLowerCase();return t==="done"||t==="completed"||t==="skipped_duplicate"||t==="bounced"?"done":t==="in_progress"||t==="processing"||t==="extracting"||t==="etl"||t==="writing"||t==="gates"||t==="uploading"||t==="running_batch_gates"||t==="needs_retry_batch_gate"||t==="failed"||t==="error"||t==="partial_failed"?"processing":"pending"}function ls(e,t){const n=e.detected_topic||t.corpus||"",a=gn[n]||It[n]||n||"",s=e.detected_type||e.batch_type||"",o=Vn[s]||s||"",i=s==="normative_base"?"normative":s==="interpretative_guidance"?"interpretative":s==="practica_erp"?"practica":"unknown";let l="";return a&&(l+=`<span class="kanban-pill kanban-pill--topic" title="Tema: ${ye(n)}">${xe(a)}</span>`),o&&(l+=`<span class="kanban-pill kanban-pill--type-${i}" title="Tipo: ${ye(s)}">${xe(o)}</span>`),!a&&!o&&(l+='<span class="kanban-pill kanban-pill--unclassified">Sin clasificar</span>'),l}function cs(e,t,n){var v;const a=ct(e.status),s=pn(e.status),o=ts(e.bytes,n),i=Number(e.progress||0),l=new Set(t.gate_pending_doc_ids||[]),d=s==="done"&&l.has(e.doc_id);let r;e.status==="bounced"?r='<span class="meta-chip status-bounced">↩ Ya existe en el corpus</span>':s==="done"&&e.derived_from_doc_id&&(e.delta_section_count||0)>0?r=`<span class="meta-chip status-ok">△ ${e.delta_section_count} secciones nuevas</span>`:s==="done"&&(e.status==="done"||e.status==="completed")?(r='<span class="meta-chip status-ok">✓ Documento listo</span>',d&&(r+='<span class="meta-chip status-gate-pending">Pendiente validación final</span>')):r=`<span class="meta-chip status-${a}">${xe(e.status)}</span>`;const b=ls(e,t);let C="";if(e.status==="in_progress"||e.status==="processing"){const k=Et(e.heartbeat_at,e.updated_at,e.stage),P=ns(e.heartbeat_at,e.updated_at);C=`<div class="kanban-liveness ops-liveness-${k}">${P}</div>`}let f="";e.stage==="gates"&&t.gate_sub_stage&&(f=`<div class="kanban-gate-sub">${cn(t.gate_sub_stage)}</div>`);let w="";s==="processing"&&i>0&&(w=`<div class="kanban-progress" data-progress="${i}"></div>`);let E="";(v=e.error)!=null&&v.message&&(E=`<div class="kanban-error">${xe(e.error.message)}</div>`);let p="";e.duplicate_of?p=`<div class="kanban-duplicate">Duplicado de: ${xe(e.duplicate_of)}</div>`:e.derived_from_doc_id&&(p=`<div class="kanban-duplicate">Derivado de: ${xe(e.derived_from_doc_id)}</div>`);let _="";if(s==="done"){const k=ss(e.updated_at);k&&(_=`<div class="kanban-completed-at">Completado: ${xe(k)}</div>`)}let g="";e.duplicate_of&&s!=="done"&&e.status!=="bounced"?g=fs(e):s==="pending"&&(e.status==="raw"||e.status==="needs_classification")&&us(e)?g=ps(e,n):s==="pending"&&(e.status==="raw"||e.status==="needs_classification")?g=ds(e,n,t):s==="processing"&&(e.status==="failed"||e.status==="error"||e.status==="partial_failed")&&(g=bs(e));let m="",u="";(s!=="pending"||e.status==="queued")&&(m=ms(),u=gs(e,t,n));const y=e.stage&&e.stage!==e.status&&s==="processing";return`
    <div class="kanban-card kanban-card--${a}" data-doc-id="${ye(e.doc_id)}">
      <div class="kanban-card-head">
        <span class="kanban-card-title" title="${ye(e.doc_id)}">${xe(e.filename||e.doc_id)}</span>
        ${r}
      </div>
      ${e.source_relative_path?`<div class="kanban-card-relpath" title="${ye(e.source_relative_path)}">${xe(_s(e.source_relative_path))}</div>`:""}
      <div class="kanban-card-pills-row">
        ${b}
        <span class="kanban-card-size">${o}</span>
        ${m}
      </div>
      ${u}
      ${y?`<div class="kanban-card-stage">${xe(e.stage)}</div>`:""}
      ${C}
      ${f}
      ${w}
      ${_}
      ${p}
      ${E}
      ${g}
    </div>
  `}function ds(e,t,n){const a=e.detected_type||e.batch_type||"",s=e.detected_topic||(n==null?void 0:n.corpus)||"",o=i=>i===a?" selected":"";return`
    <div class="kanban-actions kanban-classify-actions">
      <label class="kanban-action-field">
        <span>Tema</span>
        <select data-field="topic" class="kanban-select">
          ${ft(s)}
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
        <button class="btn btn--sm btn--primary kanban-assign-btn" data-action="assign" data-doc-id="${ye(e.doc_id)}">Asignar</button>
      </div>
    </div>
  `}function us(e){return!!(e.autogenerar_label&&(e.autogenerar_is_new||e.autogenerar_resolved_topic))}function ps(e,t){const n=e.detected_type||e.batch_type||"",a=r=>r===n?" selected":"",s=`
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
            value="${ye(e.autogenerar_label||"")}" />
        </label>
        ${e.autogenerar_rationale?`<div class="kanban-autogenerar-rationale">${xe(e.autogenerar_rationale)}</div>`:""}
        ${s}
        <div class="kanban-action-buttons">
          <button class="btn btn--sm btn--primary" data-action="accept-new-topic" data-doc-id="${ye(e.doc_id)}">Aceptar nuevo tema</button>
          <button class="btn btn--sm kanban-ag-fallback-btn" data-action="show-existing-dropdown" data-doc-id="${ye(e.doc_id)}">Asignar existente</button>
        </div>
        <div class="kanban-ag-fallback-panel" hidden>
          <label class="kanban-action-field">
            <span>Tema existente</span>
            <select data-field="topic" class="kanban-select">
              ${ft("")}
            </select>
          </label>
          <div class="kanban-action-field kanban-action-field--btn">
            <span>&nbsp;</span>
            <button class="btn btn--sm btn--primary kanban-assign-btn" data-action="assign" data-doc-id="${ye(e.doc_id)}">Asignar</button>
          </div>
        </div>
      </div>
    `;const o=e.autogenerar_resolved_topic||"",i=It[o]||o,l=e.autogenerar_synonym_confidence??0,d=Math.round(l*100);return`
    <div class="kanban-actions kanban-autogenerar-actions kanban-autogenerar--synonym">
      <div class="kanban-autogenerar-header">Tema sugerido: <strong>${xe(i)}</strong> <span class="kanban-autogenerar-conf">(${d}%)</span></div>
      <div class="kanban-autogenerar-source">Basado en: "${xe(e.autogenerar_label||"")}"</div>
      ${s}
      <div class="kanban-action-buttons">
        <button class="btn btn--sm btn--primary" data-action="accept-synonym" data-doc-id="${ye(e.doc_id)}">Aceptar</button>
        <button class="btn btn--sm kanban-ag-fallback-btn" data-action="show-existing-dropdown" data-doc-id="${ye(e.doc_id)}">Cambiar</button>
      </div>
      <div class="kanban-ag-fallback-panel" hidden>
        <label class="kanban-action-field">
          <span>Tema</span>
          <select data-field="topic" class="kanban-select">
            ${ft(o)}
          </select>
        </label>
        <div class="kanban-action-field kanban-action-field--btn">
          <span>&nbsp;</span>
          <button class="btn btn--sm btn--primary kanban-assign-btn" data-action="assign" data-doc-id="${ye(e.doc_id)}">Asignar</button>
        </div>
      </div>
    </div>
  `}function ms(){return'<button class="kanban-reclassify-toggle" type="button" title="Cambiar clasificación">✎</button>'}function gs(e,t,n){const a=e.detected_topic||t.corpus||"",s=e.detected_type||e.batch_type||"",o=(i,l)=>i===l?" selected":"";return`
    <div class="kanban-reclassify-panel" hidden>
      <label class="kanban-action-field">
        <span>Tema</span>
        <select data-field="topic" class="kanban-select">
          ${ft(a)}
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
        <button class="btn btn--sm btn--primary kanban-assign-btn" data-action="assign" data-doc-id="${ye(e.doc_id)}">Asignar</button>
      </div>
    </div>
  `}function fs(e){return`
    <div class="kanban-actions">
      <button class="btn btn--sm btn--primary" data-action="replace-dup" data-doc-id="${ye(e.doc_id)}">Reemplazar</button>
      <button class="btn btn--sm" data-action="add-new-dup" data-doc-id="${ye(e.doc_id)}">Agregar nuevo</button>
      <button class="btn btn--sm btn--danger" data-action="discard-dup" data-doc-id="${ye(e.doc_id)}">Descartar</button>
    </div>
  `}function bs(e){return`
    <div class="kanban-actions">
      <button class="btn btn--sm" data-action="retry" data-doc-id="${ye(e.doc_id)}">Reintentar</button>
      <button class="btn btn--sm btn--danger" data-action="discard" data-doc-id="${ye(e.doc_id)}">Descartar</button>
    </div>
  `}const mn=[["declaracion_renta","Renta"],["iva","IVA"],["laboral","Laboral"],["facturacion_electronica","Facturación"],["estados_financieros_niif","NIIF"],["ica","ICA"],["calendario_obligaciones","Calendarios"],["retencion_fuente","Retención"],["regimen_sancionatorio","Sanciones"],["regimen_cambiario","Régimen Cambiario"],["impuesto_al_patrimonio","Patrimonio"],["informacion_exogena","Exógena"],["proteccion_de_datos","Datos"],["obligaciones_mercantiles","Mercantil"],["obligaciones_profesionales_contador","Obligaciones Contador"],["rut_responsabilidades","RUT"],["gravamen_movimiento_financiero_4x1000","GMF 4×1000"],["beneficiario_final","Beneficiario Final"],["contratacion_estatal","Contratación Estatal"],["reforma_pensional","Reforma Pensional"],["zomac_incentivos","ZOMAC"]];function hs(e){const t=new Set,n=[];for(const[a,s]of mn)t.add(a),n.push([a,s]);for(const a of e)!a.key||t.has(a.key)||(t.add(a.key),n.push([a.key,a.label||a.key]));return n}let Nt=mn,gn={...It};function ft(e=""){let t='<option value="">Seleccionar...</option>';for(const[n,a]of Nt){const s=n===e?" selected":"";t+=`<option value="${ye(n)}"${s}>${xe(a)}</option>`}return t}function xe(e){const t=document.createElement("span");return t.textContent=e,t.innerHTML}function ye(e){return e.replace(/&/g,"&amp;").replace(/"/g,"&quot;").replace(/'/g,"&#39;").replace(/</g,"&lt;").replace(/>/g,"&gt;")}function _s(e){const t=e.replace(/\/[^/]+$/,"").split("/").filter(Boolean);return t.length<=2?t.join("/")+"/":"…/"+t.slice(-2).join("/")+"/"}function vs(e,t,n,a,s){s&&s.length>0&&(Nt=hs(s),gn=Object.fromEntries(Nt));const o=[...e.documents||[]].sort((g,m)=>Date.parse(String(m.updated_at||0))-Date.parse(String(g.updated_at||0))),i={pending:[],processing:[],done:[]};for(const g of o){const m=pn(g.status);i[m].push(g)}i.pending.sort((g,m)=>{const u=g.status==="raw"||g.status==="needs_classification"?0:1,c=m.status==="raw"||m.status==="needs_classification"?0:1;return u!==c?u-c:Date.parse(String(m.updated_at||0))-Date.parse(String(g.updated_at||0))});const l=e.status==="running_batch_gates",d=e.gate_sub_stage||"";let r="";if(l){const g=d?cn(d):"Preparando...";r=`
      <div class="kanban-validation-banner kanban-validation-banner--running">
        <span class="kanban-validation-spinner"></span>
        <span>Validación final en curso — ${xe(g)}</span>
      </div>`}else e.status==="needs_retry_batch_gate"?r=`
      <div class="kanban-validation-banner kanban-validation-banner--error">
        <span>⚠ Validación final fallida — use Reintentar o Validar lote</span>
      </div>`:e.status==="completed"&&e.wip_sync_status==="skipped"&&(r=`
      <div class="kanban-validation-banner kanban-validation-banner--warn">
        <span>⚠ Ingesta completada solo localmente — WIP Supabase no estaba disponible. Use Operaciones → Sincronizar a WIP.</span>
      </div>`);let b="";const C=i.processing.length;for(const g of as){const m=i[g],u=g==="processing"?`<span class="kanban-column-count">${C}</span><span class="kanban-column-limit">/ ${rs}</span>`:`<span class="kanban-column-count">${m.length}</span>`,c=m.length===0?'<div class="kanban-column-empty">Sin documentos</div>':m.map(v=>cs(v,e,n)).join(""),y=g==="done"?r:"";b+=`
      <div class="kanban-column kanban-column--${g}">
        <div class="kanban-column-header">
          <span class="kanban-column-icon">${is[g]}</span>
          <span class="kanban-column-label">${os[g]}</span>
          ${u}
        </div>
        <div class="kanban-column-cards">
          ${y}
          ${c}
        </div>
      </div>
    `}const f={};t.querySelectorAll(".kanban-column").forEach(g=>{const m=g.classList[1]||"",u=g.querySelector(".kanban-column-cards");m&&u&&(f[m]=u.scrollTop)});const w=[];let E=t;for(;E;)E.scrollTop>0&&w.push([E,E.scrollTop]),E=E.parentElement;const p={};t.querySelectorAll(".kanban-reclassify-panel").forEach(g=>{var m,u;if(!g.hasAttribute("hidden")){const c=g.closest("[data-doc-id]"),y=(c==null?void 0:c.dataset.docId)||"";if(y&&!(a!=null&&a.has(y))){const v=((m=g.querySelector("[data-field='topic']"))==null?void 0:m.value)||"",k=((u=g.querySelector("[data-field='type']"))==null?void 0:u.value)||"";p[y]={topic:v,type:k}}}});const _={};t.querySelectorAll(".kanban-classify-actions").forEach(g=>{var c,y;const m=g.closest("[data-doc-id]"),u=(m==null?void 0:m.dataset.docId)||"";if(u){const v=((c=g.querySelector("[data-field='topic']"))==null?void 0:c.value)||"",k=((y=g.querySelector("[data-field='type']"))==null?void 0:y.value)||"";(v||k)&&(_[u]={topic:v,type:k})}}),t.innerHTML=b;for(const[g,m]of w)g.scrollTop=m;t.querySelectorAll(".kanban-column").forEach(g=>{const m=g.classList[1]||"",u=g.querySelector(".kanban-column-cards");m&&f[m]&&u&&(u.scrollTop=f[m])});for(const[g,m]of Object.entries(p)){const u=t.querySelector(`[data-doc-id="${CSS.escape(g)}"]`);if(!u)continue;const c=u.querySelector(".kanban-reclassify-toggle"),y=u.querySelector(".kanban-reclassify-panel");if(c&&y){y.removeAttribute("hidden"),c.textContent="✖";const v=y.querySelector("[data-field='topic']"),k=y.querySelector("[data-field='type']");v&&m.topic&&(v.value=m.topic),k&&m.type&&(k.value=m.type)}}for(const[g,m]of Object.entries(_)){const u=t.querySelector(`[data-doc-id="${CSS.escape(g)}"]`);if(!u)continue;const c=u.querySelector(".kanban-classify-actions");if(!c)continue;const y=c.querySelector("[data-field='topic']"),v=c.querySelector("[data-field='type']");y&&m.topic&&(y.value=m.topic),v&&m.type&&(v.value=m.type)}t.querySelectorAll(".kanban-progress").forEach(g=>{var y,v;const m=Number(g.dataset.progress||0),u=((v=(y=g.closest(".kanban-card"))==null?void 0:y.querySelector(".kanban-card-stage"))==null?void 0:v.textContent)||void 0,c=dn(m,u);g.replaceWith(c)}),t.querySelectorAll(".kanban-reclassify-toggle").forEach(g=>{g.addEventListener("click",()=>{const m=g.closest(".kanban-card"),u=m==null?void 0:m.querySelector(".kanban-reclassify-panel");if(!u)return;u.hasAttribute("hidden")?(u.removeAttribute("hidden"),g.textContent="✖"):(u.setAttribute("hidden",""),g.textContent="✎")})})}async function Me(e,t){const n=await fetch(e,t);let a=null;try{a=await n.json()}catch{a=null}if(!n.ok){const s=a&&typeof a=="object"&&"error"in a?String(a.error||n.statusText):n.statusText;throw new st(s,n.status,a)}return a}async function xt(e,t){const{response:n,data:a}=await ze(e,t);if(!n.ok){const s=a&&typeof a=="object"&&"error"in a?String(a.error||n.statusText):n.statusText;throw new st(s,n.status,a)}return a}const ys=new Set([".pdf",".md",".txt",".docx"]),ks=[".","__MACOSX"],Pt=3,kt="lia_folder_pending_";function lt(e){return e.filter(t=>{const n=t.name;if(ks.some(o=>n.startsWith(o)))return!1;const a=n.lastIndexOf("."),s=a>=0?n.slice(a).toLowerCase():"";return ys.has(s)})}function dt(e,t){return e.webkitRelativePath||t.get(e)||""}function Xe(e,t){const n=dt(e,t);return`${e.name}|${e.size}|${e.lastModified??0}|${n}`}function ws(e){return e<1024?`${e} B`:e<1024*1024?`${(e/1024).toFixed(1)} KB`:`${(e/(1024*1024)).toFixed(1)} MB`}function $s(e,t){var a;const n=((a=e.preflightEntry)==null?void 0:a.existing_doc_id)||"";switch(e.verdict){case"pending":return t.t("ops.ingestion.verdict.pending");case"new":return t.t("ops.ingestion.verdict.new");case"revision":return n?t.t("ops.ingestion.verdict.revisionOf",{docId:n}):t.t("ops.ingestion.verdict.revision");case"duplicate":return n?t.t("ops.ingestion.verdict.duplicateOf",{docId:n}):t.t("ops.ingestion.verdict.duplicate");case"artifact":return t.t("ops.ingestion.verdict.artifact");case"unreadable":return t.t("ops.ingestion.verdict.unreadable")}}function Cs(e,t){const n=document.createElement("span");return n.className=`ops-verdict-pill ops-verdict-pill--${e.verdict}`,n.textContent=$s(e,t),n}function mt(e){return e.documents.filter(t=>t.status==="raw"||t.status==="needs_classification").length}function Ss(e){const{dom:t,stateController:n,withThinkingWheel:a,setFlash:s}=e;function o(){return e.state.selectedCorpus!=="autogenerar"?e.state.selectedCorpus:"autogenerar"}async function i(){const m=await Ne("/api/corpora"),u=Array.isArray(m.corpora)?m.corpora:[];n.setCorpora(u);const c=new Set(u.map(y=>y.key));c.add("autogenerar"),c.has(e.state.selectedCorpus)||n.setSelectedCorpus("autogenerar")}async function l(){const m=await Ne("/api/ingestion/sessions?limit=20");return Array.isArray(m.sessions)?m.sessions:[]}async function d(m){const u=await Ne(`/api/ingestion/sessions/${encodeURIComponent(m)}`);if(!u.session)throw new Error("missing_session");return u.session}async function r(m){const u=await xt("/api/ingestion/sessions",{corpus:m});if(!u.session)throw new Error("missing_session");return u.session}async function b(m,u,c){const y=t.ingestionCorpusSelect.value==="autogenerar"?"":t.ingestionCorpusSelect.value,v={"Content-Type":"application/octet-stream","X-Upload-Filename":u.name,"X-Upload-Mime":u.type||"application/octet-stream","X-Upload-Batch-Type":c};y&&(v["X-Upload-Topic"]=y);const k=dt(u,e.state.folderRelativePaths);k&&(v["X-Upload-Relative-Path"]=k),console.log(`[upload] ${u.name} (${u.size}B) → session=${m} batch=${c}`);const P=await fetch(`/api/ingestion/sessions/${encodeURIComponent(m)}/files`,{method:"POST",headers:v,body:u}),T=await P.text();let A;try{A=JSON.parse(T)}catch{throw console.error(`[upload] ${u.name} — response not JSON (${P.status}):`,T.slice(0,300)),new Error(`Upload response not JSON: ${P.status} ${T.slice(0,100)}`)}if(!P.ok){const B=A.error||P.statusText;throw console.error(`[upload] ${u.name} — HTTP ${P.status}:`,B),new st(B,P.status,A)}if(!A.document)throw console.error(`[upload] ${u.name} — no document in response:`,A),new Error("missing_document");return console.log(`[upload] ${u.name} → OK doc_id=${A.document.doc_id} status=${A.document.status}`),A.document}async function C(m){return Me(`/api/ingestion/sessions/${encodeURIComponent(m)}/process`,{method:"POST"})}async function f(m){return Me(`/api/ingestion/sessions/${encodeURIComponent(m)}/validate-batch`,{method:"POST"})}async function w(m){return Me(`/api/ingestion/sessions/${encodeURIComponent(m)}/retry`,{method:"POST"})}async function E(m,u=!1){const c=u?"?force=true":"";return Me(`/api/ingestion/sessions/${encodeURIComponent(m)}${c}`,{method:"DELETE"})}async function p({showWheel:m=!0,reportError:u=!0,focusSessionId:c=""}={}){const y=async()=>{await i(),e.render();let v=await l();const k=c||e.state.selectedSessionId;if(k&&!v.some(P=>P.session_id===k))try{v=[await d(k),...v.filter(T=>T.session_id!==k)]}catch{k===e.state.selectedSessionId&&n.setSelectedSession(null)}n.setSessions(v.sort((P,T)=>Date.parse(String(T.updated_at||0))-Date.parse(String(P.updated_at||0)))),n.syncSelectedSession(),e.render()};try{m?await a(y):await y()}catch(v){throw u&&s(ke(v),"error"),e.render(),v}}async function _({sessionId:m,showWheel:u=!1,reportError:c=!0}){const y=async()=>{const v=await d(m);n.upsertSession(v),e.render()};try{u?await a(y):await y()}catch(v){throw c&&s(ke(v),"error"),v}}async function g(){var u,c,y,v;const m=o();if(console.log(`[folder-ingest] ensureSelectedSession: effectiveCorpus="${m}", selectedSession=${((u=e.state.selectedSession)==null?void 0:u.session_id)||"null"} (status=${((c=e.state.selectedSession)==null?void 0:c.status)||"null"}, corpus=${((y=e.state.selectedSession)==null?void 0:y.corpus)||"null"})`),e.state.selectedSession&&!ln(e.state.selectedSession)&&e.state.selectedSession.status!=="completed"&&(e.state.selectedSession.corpus===m||m==="autogenerar"))return console.log(`[folder-ingest] Reusing session ${e.state.selectedSession.session_id}`),e.state.selectedSession;e.trace(`Creando sesión con corpus="${m}"...`);try{const k=await r(m);return e.trace(`Sesión creada: ${k.session_id} (corpus=${k.corpus})`),n.upsertSession(k),k}catch(k){if(e.trace(`Creación falló para corpus="${m}": ${k instanceof Error?k.message:String(k)}`),m==="autogenerar"){const P=((v=e.state.corpora.find(A=>A.active))==null?void 0:v.key)||"declaracion_renta";e.trace(`Reintentando con corpus="${P}"...`);const T=await r(P);return e.trace(`Sesión fallback: ${T.session_id} (corpus=${T.corpus})`),n.upsertSession(T),T}throw k}}return{resolveSessionCorpus:o,fetchCorpora:i,fetchIngestionSessions:l,fetchIngestionSession:d,createIngestionSession:r,uploadIngestionFile:b,startIngestionProcess:C,validateBatch:f,retryIngestionSession:w,ejectIngestionSession:E,refreshIngestion:p,refreshSelectedSession:_,ensureSelectedSession:g}}function Es(e){const{i18n:t,stateController:n,dom:a,withThinkingWheel:s,setFlash:o}=e,i=an(t);return{dom:a,i18n:t,stateController:n,withThinkingWheel:s,setFlash:o,toast:i,get state(){return n.state},render:()=>{},trace:()=>{}}}function Ns(e,t){const{dom:n,stateController:a,i18n:s}=e,{ingestionUploadProgress:o}=n;async function i(p){var u,c;const _=[],g=[];for(let y=0;y<p.items.length;y++){const v=(c=(u=p.items[y]).webkitGetAsEntry)==null?void 0:c.call(u);v&&g.push(v)}if(!g.some(y=>y.isDirectory))return[];async function m(y){if(y.isFile){const v=await new Promise((k,P)=>{y.file(k,P)});e.state.folderRelativePaths.set(v,y.fullPath.replace(/^\//,"")),_.push(v)}else if(y.isDirectory){const v=y.createReader();let k;do{k=await new Promise((P,T)=>{v.readEntries(P,T)});for(const P of k)await m(P)}while(k.length>0)}}for(const y of g)await m(y);return _}async function l(p,_=""){const g=[];for await(const[m,u]of p.entries()){const c=_?`${_}/${m}`:m;if(u.kind==="file"){const y=await u.getFile();e.state.folderRelativePaths.set(y,c),g.push(y)}else if(u.kind==="directory"){const y=await l(u,c);g.push(...y)}}return g}async function d(p,_,g,m=Pt){let u=0,c=0,y=0,v=0;const k=[];return new Promise(P=>{function T(){for(;y<m&&v<_.length;){const A=_[v++];y++,t.uploadIngestionFile(p,A,g).then(()=>{u++}).catch(B=>{c++;const J=B instanceof Error?B.message:String(B);k.push({filename:A.name,error:J}),console.error(`[folder-ingest] Upload failed: ${A.name}`,B)}).finally(()=>{y--,a.setFolderUploadProgress({total:_.length,uploaded:u,failed:c,uploading:v<_.length||y>0}),r(),v<_.length||y>0?T():P({uploaded:u,failed:c,errors:k})})}}a.setFolderUploadProgress({total:_.length,uploaded:0,failed:0,uploading:!0}),r(),T()})}function r(){const p=e.state.folderUploadProgress;if(!p||!p.uploading){o.hidden=!0,o.innerHTML="";return}const _=p.uploaded+p.failed,g=p.total>0?Math.round(_/p.total*100):0,m=Math.max(0,Math.min(Pt,p.total-_));o.hidden=!1,o.innerHTML=`
      <div class="ops-upload-progress-header">
        <span>${s.t("ops.ingestion.uploadProgress",{current:_,total:p.total})}</span>
        <span>${g}%</span>
      </div>
      <div class="ops-upload-progress-bar">
        <span class="ops-upload-progress-fill" style="width:${g}%"></span>
      </div>
      <div class="ops-upload-progress-detail">
        ${s.t("ops.ingestion.uploadProgressDetail",{uploaded:p.uploaded,failed:p.failed,inflight:m})}
      </div>
    `}function b(){const p=e.state.preflightScanProgress;if(!p||!p.scanning){o.hidden=!0,o.innerHTML="";return}const _=p.total>0?Math.round(p.hashed/p.total*100):0;o.hidden=!1,o.innerHTML=`
      <div class="ops-preflight-scan">
        <div class="ops-preflight-scan-header">
          <span>${s.t("ops.ingestion.preflight.scanning",{hashed:p.hashed,total:p.total})}</span>
          <span>${_}%</span>
        </div>
        <div class="ops-preflight-scan-bar">
          <span class="ops-preflight-scan-fill" style="width:${_}%"></span>
        </div>
        <div class="ops-preflight-scan-detail">${s.t("ops.ingestion.preflight.scanningDetail")}</div>
      </div>
    `}function C(p){if(e.state.pendingFiles.length!==0&&dt(e.state.pendingFiles[0])!=="")try{const _=e.state.pendingFiles.map(g=>({name:g.name,relativePath:dt(g),size:g.size}));localStorage.setItem(kt+p,JSON.stringify(_))}catch{}}function f(p){try{localStorage.removeItem(kt+p)}catch{}}function w(p){try{const _=localStorage.getItem(kt+p);if(!_)return 0;const g=JSON.parse(_);if(!Array.isArray(g))return 0;const m=e.state.sessions.find(c=>c.session_id===p);if(!m)return g.length;const u=new Set((m.documents||[]).map(c=>c.filename));return g.filter(c=>!u.has(c.name)).length}catch{return 0}}async function E(p,_){return(await xt("/api/ingestion/preflight",{corpus:_,files:p})).manifest}return{resolveFolderFiles:i,readDirectoryHandle:l,uploadFilesWithConcurrency:d,renderUploadProgress:r,renderScanProgress:b,persistFolderPending:C,clearFolderPending:f,getStoredFolderPendingCount:w,requestPreflight:E}}function Ps(e,t,n,a){const{dom:s,stateController:o,setFlash:i}=e,{ingestionFolderInput:l,ingestionFileInput:d}=s;let r=!1,b=null;const C=150;function f(v){if(v.length===0)return;const k=new Set(e.state.intake.map(T=>Xe(T.file))),P=[];for(const T of v){const A=Xe(T,e.state.folderRelativePaths);k.has(A)||(k.add(A),P.push({file:T,relativePath:dt(T,e.state.folderRelativePaths),contentHash:null,verdict:"pending",preflightEntry:null}))}P.length!==0&&(o.setIntake([...e.state.intake,...P]),e.state.reviewPlan&&o.setReviewPlan({...e.state.reviewPlan,stalePartial:!0}),r=!1,w(),e.render())}function w(){b&&clearTimeout(b);const v=o.bumpPreflightRunId();b=setTimeout(()=>{b=null,E(v)},C)}async function E(v){if(v!==e.state.preflightRunId||e.state.intake.length===0)return;const k=e.state.intake.filter(P=>P.contentHash===null);try{if(k.length>0&&(await p(k),v!==e.state.preflightRunId))return;const P=await _();if(v!==e.state.preflightRunId)return;if(!P){r=!0,e.render();return}g(P),r=!1,e.render()}catch(P){if(v!==e.state.preflightRunId)return;console.error("[intake] preflight failed:",P),r=!0,e.render()}}async function p(v){o.setPreflightScanProgress({total:v.length,hashed:0,scanning:!0}),n.renderScanProgress();for(let k=0;k<v.length;k++){const P=v[k];try{const T=await P.file.arrayBuffer(),A=await crypto.subtle.digest("SHA-256",T),B=Array.from(new Uint8Array(A));P.contentHash=B.map(J=>J.toString(16).padStart(2,"0")).join("")}catch(T){console.warn(`[intake] hash failed for ${P.file.name}:`,T),P.verdict="unreadable",P.contentHash=""}o.setPreflightScanProgress({total:v.length,hashed:k+1,scanning:!0}),n.renderScanProgress()}o.setPreflightScanProgress(null)}async function _(){const v=e.state.intake.filter(k=>k.contentHash&&k.verdict!=="unreadable").map(k=>({filename:k.file.name,relative_path:k.relativePath||k.file.name,size:k.file.size,content_hash:k.contentHash}));if(v.length===0)return{artifacts:[],duplicates:[],revisions:[],new_files:[],scanned:0,elapsed_ms:0};try{return await n.requestPreflight(v,e.state.selectedCorpus)}catch(k){return console.error("[intake] /api/ingestion/preflight failed:",k),null}}function g(v){const k=new Map,P=(J,q)=>{for(const j of q){const N=j.relative_path||j.filename;k.set(N,{verdict:J,preflightEntry:j})}};P("new",v.new_files),P("revision",v.revisions),P("duplicate",v.duplicates),P("artifact",v.artifacts);const T=e.state.intake.map(J=>{if(J.verdict==="unreadable")return J;const q=J.relativePath||J.file.name,j=k.get(q);return j?{...J,verdict:j.verdict,preflightEntry:j.preflightEntry}:{...J,verdict:"pending"}}),A=T.filter(J=>J.verdict==="new"||J.verdict==="revision"),B=T.filter(J=>J.verdict==="duplicate"||J.verdict==="artifact"||J.verdict==="unreadable");o.setIntake(T),o.setReviewPlan({willIngest:A,bounced:B,scanned:v.scanned,elapsedMs:v.elapsed_ms,stalePartial:!1}),o.setPendingFiles(A.map(J=>J.file))}function m(v){const k=P=>Xe(P.file)!==Xe(v.file);if(o.setIntake(e.state.intake.filter(k)),e.state.reviewPlan){const P=e.state.reviewPlan.willIngest.filter(k);o.setReviewPlan({...e.state.reviewPlan,willIngest:P}),o.setPendingFiles(P.map(T=>T.file))}else o.setPendingFiles(e.state.pendingFiles.filter(P=>Xe(P)!==Xe(v.file)));e.render()}function u(){if(!e.state.reviewPlan)return;const v=new Set(e.state.reviewPlan.willIngest.map(P=>Xe(P.file))),k=e.state.intake.filter(P=>!v.has(Xe(P.file)));o.setIntake(k),o.setReviewPlan({...e.state.reviewPlan,willIngest:[]}),o.setPendingFiles([]),e.render()}function c(){b&&(clearTimeout(b),b=null),o.bumpPreflightRunId(),o.setIntake([]),o.setReviewPlan(null),o.setPendingFiles([]),o.setPreflightScanProgress(null),r=!1,e.state.folderRelativePaths.clear()}async function y(){const v=e.state.reviewPlan;if(v&&!v.stalePartial&&v.willIngest.length!==0&&!r){i(),o.setMutating(!0),a.renderControls();try{await a.directFolderIngest(),c(),l.value="",d.value=""}catch(k){o.setFolderUploadProgress(null),n.renderUploadProgress(),i(ke(k),"error"),e.state.selectedSessionId&&t.refreshSelectedSession({sessionId:e.state.selectedSessionId,showWheel:!1,reportError:!1})}finally{o.setMutating(!1),a.renderControls()}}}return{addFilesToIntake:f,schedulePreflight:w,runIntakePreflight:E,hashIntakeEntries:p,preflightIntake:_,applyManifestToIntake:g,removeIntakeEntry:m,cancelAllWillIngest:u,clearIntake:c,confirmAndIngest:y,getIntakeError:()=>r,setIntakeError:v=>{r=v}}}function As(e,t){const{dom:n,i18n:a,stateController:s,setFlash:o}=e,{ingestionAutoStatus:i}=n,l=4e3;let d=null,r="";function b(){d&&(clearTimeout(d),d=null),r="",i.hidden=!0,i.classList.remove("is-running")}function C(E){const p=E.batch_summary,_=mt(E),g=Math.max(0,Number(p.queued??0)-_),m=Number(p.processing??0),u=Number(p.done??0),c=Number(p.failed??0),y=Number(p.bounced??0),v=g+m;i.hidden=!1;const k=y>0?` · ${y} rebotados`:"";v>0||_>0?(i.classList.add("is-running"),i.textContent=a.t("ops.ingestion.auto.running",{queued:g,processing:m,raw:_})+k):c>0?(i.classList.remove("is-running"),i.textContent=a.t("ops.ingestion.auto.done",{done:u,failed:c,raw:_})+k):(i.classList.remove("is-running"),i.textContent=a.t("ops.ingestion.auto.allDone",{done:u})+k)}async function f(){const E=r;if(E)try{const p=await t.fetchIngestionSession(E);s.upsertSession(p),e.render(),C(p);const _=p.batch_summary,g=mt(p),m=Number(_.total??0);if(m===0){b();return}g>0&&await Me(`/api/ingestion/sessions/${encodeURIComponent(E)}/auto-process`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({max_concurrency:5})});const u=g>0?await t.fetchIngestionSession(E):p,c=mt(u),y=Math.max(0,Number(u.batch_summary.queued??0)-c),v=Number(u.batch_summary.processing??0);y>0&&v===0&&await t.startIngestionProcess(E),g>0&&(s.upsertSession(u),e.render(),C(u));const k=y+v;if(m>0&&k===0&&c===0){if(Number(u.batch_summary.pending_batch_gate??0)>0&&u.status!=="running_batch_gates"&&u.status!=="completed")try{await t.validateBatch(E)}catch{}const T=await t.fetchIngestionSession(E);s.upsertSession(T),e.render(),C(T),b(),o(a.t("ops.ingestion.auto.allDone",{done:Number(T.batch_summary.done??0)}),"success");return}if(k===0&&c>0){i.classList.remove("is-running"),i.textContent=a.t("ops.ingestion.auto.done",{done:Number(u.batch_summary.done??0),failed:Number(u.batch_summary.failed??0),raw:c}),b();return}d=setTimeout(()=>void f(),l)}catch(p){b(),o(ke(p),"error")}}function w(E){b(),r=E,i.hidden=!1,i.classList.add("is-running"),i.textContent=a.t("ops.ingestion.auto.running",{queued:0,processing:0,raw:0}),d=setTimeout(()=>void f(),2e3)}return{startAutoPilot:w,stopAutoPilot:b,updateAutoStatus:C,autoPilotTick:f}}function Is(e){const{ctx:t,api:n,upload:a,intake:s,autoPilot:o}=e,{dom:i,stateController:l,i18n:d,setFlash:r,toast:b,withThinkingWheel:C}=t,{ingestionDropzone:f,ingestionFileInput:w,ingestionFolderInput:E,ingestionSelectFilesBtn:p,ingestionSelectFolderBtn:_,ingestionCorpusSelect:g,ingestionRefreshBtn:m,ingestionCreateSessionBtn:u,ingestionUploadBtn:c,ingestionProcessBtn:y,ingestionValidateBatchBtn:v,ingestionRetryBtn:k,ingestionDeleteSessionBtn:P,ingestionAutoProcessBtn:T,ingestionLastError:A,ingestionLogBody:B,ingestionLogAccordion:J,ingestionLogCopyBtn:q,ingestionKanban:j,ingestionUploadProgress:N}=i,{addFilesToIntake:$,clearIntake:z,confirmAndIngest:O}=s,{startAutoPilot:M,stopAutoPilot:I}=o,{createIngestionSession:K,ejectIngestionSession:h,fetchCorpora:S,refreshIngestion:D,refreshSelectedSession:F,resolveSessionCorpus:Q,retryIngestionSession:se,startIngestionProcess:ae,validateBatch:we}=n,{resolveFolderFiles:Pe,readDirectoryHandle:Se}=a,{render:X,renderCorpora:$e,renderControls:me,traceClear:Ae,directFolderIngest:qe,suppressPanelsOnNextRender:De}=e,{state:he}=l;f.addEventListener("click",()=>{w.disabled||w.click()}),f.addEventListener("keydown",R=>{R.key!=="Enter"&&R.key!==" "||(R.preventDefault(),w.disabled||w.click())});let Le=0;f.addEventListener("dragenter",R=>{R.preventDefault(),Le++,w.disabled||f.classList.add("is-dragover")}),f.addEventListener("dragover",R=>{R.preventDefault()}),f.addEventListener("dragleave",()=>{Le--,Le<=0&&(Le=0,f.classList.remove("is-dragover"))}),f.addEventListener("drop",async R=>{var ne;if(R.preventDefault(),Le=0,f.classList.remove("is-dragover"),w.disabled)return;const G=R.dataTransfer;if(G){const ee=await Pe(G);if(ee.length>0){$(lt(ee));return}}const ie=Array.from(((ne=R.dataTransfer)==null?void 0:ne.files)||[]);ie.length!==0&&$(lt(ie))}),w.addEventListener("change",()=>{const R=Array.from(w.files||[]);R.length!==0&&$(lt(R))}),E.addEventListener("change",()=>{const R=Array.from(E.files||[]);R.length!==0&&$(lt(R))}),p.addEventListener("click",()=>{w.disabled||w.click()}),_.addEventListener("click",async()=>{if(!E.disabled){if(typeof window.showDirectoryPicker=="function")try{const R=await window.showDirectoryPicker({mode:"read"}),G=await Se(R,R.name),ie=lt(G);ie.length>0?$(ie):r(d.t("ops.ingestion.pendingNone"),"error");return}catch(R){if((R==null?void 0:R.name)==="AbortError")return}E.click()}}),g.addEventListener("change",()=>{l.setSelectedCorpus(g.value),l.setSessions([]),l.setSelectedSession(null),z(),r(),X(),D({showWheel:!0,reportError:!0})}),m.addEventListener("click",R=>{R.stopPropagation(),r(),D({showWheel:!0,reportError:!0})}),u.addEventListener("click",async()=>{I(),r(),z(),l.setPreflightManifest(null),l.setFolderUploadProgress(null),he.rejectedArtifacts=[],N.hidden=!0,N.innerHTML="",w.value="",E.value="",A.hidden=!0,Ae(),J.hidden=!0,B.textContent="",l.setMutating(!0),me();try{const R=await C(async()=>K(Q()));l.upsertSession(R),X(),r(d.t("ops.ingestion.flash.sessionCreated",{id:R.session_id}),"success")}catch(R){r(ke(R),"error")}finally{l.setMutating(!1),me()}}),c.addEventListener("click",()=>{O()}),y.addEventListener("click",async()=>{const R=he.selectedSessionId;if(R){r(),l.setMutating(!0),me();try{await C(async()=>ae(R)),await F({sessionId:R,showWheel:!1,reportError:!1});const G=d.t("ops.ingestion.flash.processStarted",{id:R});r(G,"success"),b.show({message:G,tone:"success"})}catch(G){const ie=ke(G);r(ie,"error"),b.show({message:ie,tone:"error"})}finally{l.setMutating(!1),me()}}}),v.addEventListener("click",async()=>{const R=he.selectedSessionId;if(R){r(),l.setMutating(!0),me();try{await C(async()=>we(R)),await F({sessionId:R,showWheel:!1,reportError:!1});const G="Validación de lote iniciada";r(G,"success"),b.show({message:G,tone:"success"})}catch(G){const ie=ke(G);r(ie,"error"),b.show({message:ie,tone:"error"})}finally{l.setMutating(!1),me()}}}),k.addEventListener("click",async()=>{const R=he.selectedSessionId;if(R){r(),l.setMutating(!0),me();try{await C(async()=>se(R)),await F({sessionId:R,showWheel:!1,reportError:!1}),r(d.t("ops.ingestion.flash.retryStarted",{id:R}),"success")}catch(G){r(ke(G),"error")}finally{l.setMutating(!1),me()}}}),P.addEventListener("click",async()=>{var ee;const R=he.selectedSessionId;if(!R)return;const G=ln(he.selectedSession),ie=G?d.t("ops.ingestion.confirm.ejectPostGate"):d.t("ops.ingestion.confirm.ejectPreGate");if(await b.confirm({title:d.t("ops.ingestion.actions.discardSession"),message:ie,tone:"caution",confirmLabel:d.t("ops.ingestion.confirm.ejectLabel")})){I(),r(),l.setMutating(!0),me();try{const be=ht(String(((ee=he.selectedSession)==null?void 0:ee.status)||"")),re=await C(async()=>h(R,be||G));l.clearSelectionAfterDelete(),z(),l.setPreflightManifest(null),l.setFolderUploadProgress(null),he.rejectedArtifacts=[],N.hidden=!0,N.innerHTML="",w.value="",E.value="",A.hidden=!0,Ae(),J.hidden=!0,B.textContent="",await D({showWheel:!1,reportError:!1});const de=Array.isArray(re.errors)&&re.errors.length>0,Y=re.path==="rollback"?d.t("ops.ingestion.flash.ejectedRollback",{id:R,count:re.ejected_files}):d.t("ops.ingestion.flash.ejectedInstant",{id:R,count:re.ejected_files}),te=de?"caution":"success";r(Y,de?"error":"success"),b.show({message:Y,tone:te}),de&&b.show({message:d.t("ops.ingestion.flash.ejectedPartial"),tone:"caution",durationMs:8e3})}catch(be){const re=ke(be);r(re,"error"),b.show({message:re,tone:"error"})}finally{l.setMutating(!1),X()}}}),T.addEventListener("click",async()=>{const R=he.selectedSessionId;if(R){r(),l.setMutating(!0),me();try{await C(async()=>Me(`/api/ingestion/sessions/${encodeURIComponent(R)}/auto-process`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({max_concurrency:5})})),await ae(R),await F({sessionId:R,showWheel:!1,reportError:!1}),r(`Auto-procesamiento iniciado para ${R}`,"success"),M(R)}catch(G){r(ke(G),"error")}finally{l.setMutating(!1),me()}}});const Te=document.getElementById("ingestion-log-toggle");Te&&(Te.addEventListener("click",R=>{if(R.target.closest(".ops-log-copy-btn"))return;const G=B.hidden;B.hidden=!G,Te.setAttribute("aria-expanded",String(G));const ie=Te.querySelector(".ops-log-accordion-marker");ie&&(ie.textContent=G?"▾":"▸")}),Te.addEventListener("keydown",R=>{(R.key==="Enter"||R.key===" ")&&(R.preventDefault(),Te.click())})),q.addEventListener("click",R=>{R.preventDefault(),R.stopPropagation();const G=B.textContent||"";navigator.clipboard.writeText(G).then(()=>{const ie=q.textContent;q.textContent=d.t("ops.ingestion.log.copied"),setTimeout(()=>{q.textContent=ie},1500)}).catch(()=>{const ie=document.createRange();ie.selectNodeContents(B);const ne=window.getSelection();ne==null||ne.removeAllRanges(),ne==null||ne.addRange(ie)})}),j.addEventListener("click",async R=>{var de;const G=R.target.closest("[data-action]");if(!G)return;const ie=G.getAttribute("data-action"),ne=G.getAttribute("data-doc-id"),ee=he.selectedSessionId;if(!ee||!ne)return;if(ie==="show-existing-dropdown"){const Y=G.closest(".kanban-card"),te=Y==null?void 0:Y.querySelector(".kanban-ag-fallback-panel");te&&(te.hidden=!te.hidden);return}let be="",re="";if(ie==="assign"){const Y=G.closest(".kanban-card"),te=Y==null?void 0:Y.querySelector("[data-field='topic']"),Ce=Y==null?void 0:Y.querySelector("[data-field='type']");if(be=(te==null?void 0:te.value)||"",re=(Ce==null?void 0:Ce.value)||"",!be||!re){te&&!be&&te.classList.add("kanban-select--invalid"),Ce&&!re&&Ce.classList.add("kanban-select--invalid");return}}r(),l.setMutating(!0),me();try{switch(ie){case"assign":{await C(async()=>Me(`/api/ingestion/sessions/${encodeURIComponent(ee)}/documents/${encodeURIComponent(ne)}/classify`,{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify({topic:be,batch_type:re})})),De.add(ne);break}case"replace-dup":{await C(async()=>Me(`/api/ingestion/sessions/${encodeURIComponent(ee)}/documents/${encodeURIComponent(ne)}/resolve-duplicate`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action:"replace"})}));break}case"add-new-dup":{await C(async()=>Me(`/api/ingestion/sessions/${encodeURIComponent(ee)}/documents/${encodeURIComponent(ne)}/resolve-duplicate`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action:"add_new"})}));break}case"discard-dup":case"discard":{await C(async()=>Me(`/api/ingestion/sessions/${encodeURIComponent(ee)}/documents/${encodeURIComponent(ne)}/resolve-duplicate`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action:"discard"})}));break}case"accept-synonym":{const Y=G.closest(".kanban-card"),te=Y==null?void 0:Y.querySelector("[data-field='type']"),Ce=(te==null?void 0:te.value)||"";await C(async()=>Me(`/api/ingestion/sessions/${encodeURIComponent(ee)}/documents/${encodeURIComponent(ne)}/accept-autogenerar`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action:"accept_synonym",type:Ce||void 0})})),De.add(ne);break}case"accept-new-topic":{const Y=G.closest(".kanban-card"),te=Y==null?void 0:Y.querySelector("[data-field='autogenerar-label']"),Ce=Y==null?void 0:Y.querySelector("[data-field='type']"),Re=((de=te==null?void 0:te.value)==null?void 0:de.trim())||"",Ie=(Ce==null?void 0:Ce.value)||"";if(!Re||Re.length<3){te&&te.classList.add("kanban-select--invalid");return}await C(async()=>Me(`/api/ingestion/sessions/${encodeURIComponent(ee)}/documents/${encodeURIComponent(ne)}/accept-autogenerar`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action:"accept_new_topic",edited_label:Re,type:Ie||void 0})})),De.add(ne),await S(),$e();break}case"retry":{await C(async()=>Me(`/api/ingestion/sessions/${encodeURIComponent(ee)}/documents/${encodeURIComponent(ne)}/retry`,{method:"POST"}));break}case"remove":break}await F({sessionId:ee,showWheel:!1,reportError:!1})}catch(Y){r(ke(Y),"error")}finally{l.setMutating(!1),me()}});const ue=i.addCorpusDialog,_e=i.addCorpusBtn;if(ue&&_e){let R=function(Y){return Y.normalize("NFD").replace(/[̀-ͯ]/g,"").toLowerCase().replace(/[^a-z0-9]+/g,"_").replace(/^_|_$/g,"")};const G=ue.querySelector("#add-corpus-label"),ie=ue.querySelector("#add-corpus-key"),ne=ue.querySelector("#add-corpus-kw-strong"),ee=ue.querySelector("#add-corpus-kw-weak"),be=ue.querySelector("#add-corpus-error"),re=ue.querySelector("#add-corpus-cancel"),de=ue.querySelector("#add-corpus-form");_e.addEventListener("click",()=>{G&&(G.value=""),ie&&(ie.value=""),ne&&(ne.value=""),ee&&(ee.value=""),be&&(be.hidden=!0),ue.showModal(),G==null||G.focus()}),G==null||G.addEventListener("input",()=>{ie&&(ie.value=R(G.value))}),re==null||re.addEventListener("click",()=>{ue.close()}),de==null||de.addEventListener("submit",async Y=>{Y.preventDefault(),be&&(be.hidden=!0);const te=(G==null?void 0:G.value.trim())||"";if(!te)return;const Ce=((ne==null?void 0:ne.value)||"").split(",").map(Ie=>Ie.trim()).filter(Boolean),Re=((ee==null?void 0:ee.value)||"").split(",").map(Ie=>Ie.trim()).filter(Boolean);try{await C(async()=>xt("/api/corpora",{label:te,keywords_strong:Ce.length?Ce:void 0,keywords_weak:Re.length?Re:void 0})),ue.close(),await D({showWheel:!1,reportError:!1});const Ie=R(te);Ie&&l.setSelectedCorpus(Ie),X(),r(`Categoría "${te}" creada.`,"success")}catch(Ie){be&&(be.textContent=ke(Ie),be.hidden=!1)}})}}function xs(e){const{i18n:t,stateController:n,dom:a,withThinkingWheel:s,setFlash:o}=e,{ingestionCorpusSelect:i,ingestionBatchTypeSelect:l,ingestionDropzone:d,ingestionFileInput:r,ingestionFolderInput:b,ingestionSelectFilesBtn:C,ingestionSelectFolderBtn:f,ingestionUploadProgress:w,ingestionPendingFiles:E,ingestionOverview:p,ingestionRefreshBtn:_,ingestionCreateSessionBtn:g,ingestionUploadBtn:m,ingestionProcessBtn:u,ingestionAutoProcessBtn:c,ingestionValidateBatchBtn:y,ingestionRetryBtn:v,ingestionDeleteSessionBtn:k,ingestionSessionMeta:P,ingestionSessionsList:T,selectedSessionMeta:A,ingestionLastError:B,ingestionLastErrorMessage:J,ingestionLastErrorGuidance:q,ingestionLastErrorNext:j,ingestionKanban:N,ingestionLogAccordion:$,ingestionLogBody:z,ingestionLogCopyBtn:O,ingestionAutoStatus:M}=a,{state:I}=n,K=Es(e);K.toast;const h=Ss(K),{resolveSessionCorpus:S,fetchCorpora:D,fetchIngestionSessions:F,fetchIngestionSession:Q,createIngestionSession:se,uploadIngestionFile:ae,startIngestionProcess:we,validateBatch:Pe,retryIngestionSession:Se,ejectIngestionSession:X,refreshIngestion:$e,refreshSelectedSession:me,ensureSelectedSession:Ae}=h,qe=Ns(K,h),{resolveFolderFiles:De,readDirectoryHandle:he,uploadFilesWithConcurrency:Le,renderUploadProgress:Te,renderScanProgress:ue,persistFolderPending:_e,clearFolderPending:R,getStoredFolderPendingCount:G,requestPreflight:ie}=qe;let ne=[];function ee(x){const W=`[${new Date().toISOString().slice(11,23)}] ${x}`;ne.push(W),console.log(`[folder-ingest] ${x}`),$.hidden=!1,z.hidden=!1,z.textContent=ne.join(`
`);const H=document.getElementById("ingestion-log-toggle");if(H){H.setAttribute("aria-expanded","true");const Z=H.querySelector(".ops-log-accordion-marker");Z&&(Z.textContent="▾")}}function be(){ne=[],re()}function re(){const{ingestionBounceLog:x,ingestionBounceBody:L}=a;x&&(x.hidden=!0,x.open=!1),L&&(L.textContent="")}const de={directFolderIngest:()=>Promise.resolve(),renderControls:()=>{}},Y=Ps(K,h,qe,de),{addFilesToIntake:te,clearIntake:Ce,confirmAndIngest:Re,removeIntakeEntry:Ie,cancelAllWillIngest:Ge}=Y,Ke=new Set;function ut(){const x=I.selectedCorpus;i.innerHTML="";const L=document.createElement("option");L.value="autogenerar",L.textContent="AUTOGENERAR",L.selected=x==="autogenerar",i.appendChild(L),[...I.corpora].sort((W,H)=>W.label.localeCompare(H.label,"es")).forEach(W=>{var U;const H=document.createElement("option");H.value=W.key;const Z=((U=W.attention)==null?void 0:U.length)||0;let oe=W.active?W.label:`${W.label} (${t.t("ops.ingestion.corpusInactiveOption")})`;Z>0&&(oe+=` ⚠ ${Z}`),H.textContent=oe,H.selected=W.key===x,i.appendChild(H)})}function $n(x,L,W){var ve;const H=document.createElement("div");H.className="ops-intake-row",L.verdict==="pending"&&H.classList.add("ops-intake-row--pending"),W.readonly&&H.classList.add("ops-intake-row--readonly");const Z=document.createElement("span");Z.className="ops-intake-row__icon",Z.textContent="📄";const oe=document.createElement("span");oe.className="ops-intake-row__name",oe.textContent=L.relativePath||L.file.name,oe.title=L.relativePath||L.file.name;const U=document.createElement("span");U.className="ops-intake-row__size",U.textContent=ws(L.file.size);const le=Cs(L,t);if(H.append(Z,oe,U,le),W.showReason&&((ve=L.preflightEntry)!=null&&ve.reason)){const pe=document.createElement("span");pe.className="ops-intake-row__reason",pe.textContent=L.preflightEntry.reason,pe.title=L.preflightEntry.reason,H.appendChild(pe)}if(W.removable){const pe=document.createElement("button");pe.type="button",pe.className="ops-intake-row__remove",pe.textContent="✕",pe.title=t.t("ops.ingestion.willIngest.cancelAll"),pe.addEventListener("click",Fe=>{Fe.stopPropagation(),Ie(L)}),H.appendChild(pe)}x.appendChild(H)}function _t(x,L,W,H,Z,oe){const U=document.createElement("section");U.className=`ops-intake-panel ops-intake-panel--${x}`;const le=document.createElement("header");le.className="ops-intake-panel__header";const ve=document.createElement("span");ve.className="ops-intake-panel__title",ve.textContent=t.t(L),le.appendChild(ve);const pe=document.createElement("span");if(pe.className="ops-intake-panel__count",pe.textContent=t.t(W,{count:H}),le.appendChild(pe),oe.readonly){const Ee=document.createElement("span");Ee.className="ops-intake-panel__readonly",Ee.textContent=t.t("ops.ingestion.bounced.readonly"),le.appendChild(Ee)}if(oe.cancelAllAction){const Ee=document.createElement("button");Ee.type="button",Ee.className="ops-intake-panel__action",Ee.textContent=t.t("ops.ingestion.willIngest.cancelAll"),Ee.addEventListener("click",He=>{He.stopPropagation(),oe.cancelAllAction()}),le.appendChild(Ee)}U.appendChild(le);const Fe=document.createElement("div");return Fe.className="ops-intake-panel__body",Z.forEach(Ee=>$n(Fe,Ee,oe)),U.appendChild(Fe),U}function Cn(){var H,Z;if((H=d.querySelector(".ops-intake-windows"))==null||H.remove(),(Z=d.querySelector(".dropzone-file-list"))==null||Z.remove(),I.intake.length===0){E.textContent=t.t("ops.ingestion.pendingNone"),E.hidden=!0,d.classList.remove("has-files");return}E.hidden=!0,d.classList.add("has-files");const x=document.createElement("div");x.className="ops-intake-windows";const L=Sn();L&&x.appendChild(L),x.appendChild(_t("intake","ops.ingestion.intake.title","ops.ingestion.intake.count",I.intake.length,I.intake,{removable:!1,readonly:!1,showReason:!1}));const W=I.reviewPlan;W&&(x.appendChild(_t("will-ingest","ops.ingestion.willIngest.title","ops.ingestion.willIngest.count",W.willIngest.length,W.willIngest,{removable:!0,readonly:!1,showReason:!1,cancelAllAction:W.willIngest.length>0?()=>Ge():void 0})),W.bounced.length>0&&x.appendChild(_t("bounced","ops.ingestion.bounced.title","ops.ingestion.bounced.count",W.bounced.length,W.bounced,{removable:!1,readonly:!0,showReason:!0}))),d.appendChild(x)}function Sn(){var U;const x=((U=I.reviewPlan)==null?void 0:U.stalePartial)===!0,L=I.intake.some(le=>le.verdict==="pending"),W=Y.getIntakeError();if(!x&&!L&&!W)return null;const H=document.createElement("div");if(H.className="ops-intake-banner",W){H.classList.add("ops-intake-banner--error");const le=document.createElement("span");le.className="ops-intake-banner__text",le.textContent=t.t("ops.ingestion.intake.failed");const ve=document.createElement("button");return ve.type="button",ve.className="ops-intake-banner__retry",ve.textContent=t.t("ops.ingestion.intake.retry"),ve.addEventListener("click",pe=>{pe.stopPropagation(),Y.setIntakeError(!1),Y.schedulePreflight(),ot()}),H.append(le,ve),H}const Z=document.createElement("span");Z.className="ops-intake-banner__spinner",H.appendChild(Z);const oe=document.createElement("span");return oe.className="ops-intake-banner__text",x?(H.classList.add("ops-intake-banner--stale"),oe.textContent=t.t("ops.ingestion.intake.stale")):(H.classList.add("ops-intake-banner--verifying"),oe.textContent=t.t("ops.ingestion.intake.verifying")),H.appendChild(oe),H}function at(){var Ue,et,it,rt,ge;const x=n.selectedCorpusConfig(),L=I.selectedSession,W=I.selectedCorpus==="autogenerar"?I.corpora.some(Be=>Be.active):!!(x!=null&&x.active),H=ht(String((L==null?void 0:L.status)||""));l.value=l.value||"autogenerar";const Z=((Ue=I.folderUploadProgress)==null?void 0:Ue.uploading)??!1,oe=I.reviewPlan,U=(oe==null?void 0:oe.willIngest.length)??0,le=(oe==null?void 0:oe.stalePartial)===!0,ve=Y.getIntakeError()===!0,pe=!!oe&&U>0&&!le&&!ve;g.disabled=I.mutating||!W,C.disabled=I.mutating||!W||Z,f.disabled=I.mutating||!W||Z||H,m.disabled=I.mutating||!W||!pe||Z,oe?U===0?m.textContent=t.t("ops.ingestion.approveNone"):m.textContent=t.t("ops.ingestion.approveCount",{count:U}):m.textContent=t.t("ops.ingestion.approve"),u.disabled=I.mutating||!W||!L||H,c.disabled=I.mutating||!W||Z||!L||H,c.textContent=`▶ ${t.t("ops.ingestion.actions.autoProcess")}`;const Fe=Number(((et=L==null?void 0:L.batch_summary)==null?void 0:et.done)||0),Ee=Number(((it=L==null?void 0:L.batch_summary)==null?void 0:it.queued)||0)+Number(((rt=L==null?void 0:L.batch_summary)==null?void 0:rt.processing)||0),He=Number(((ge=L==null?void 0:L.batch_summary)==null?void 0:ge.pending_batch_gate)||0),Oe=Fe>=1&&(Ee>=1||He>=1);if(y.disabled=I.mutating||!W||!L||H||!Oe,v.disabled=I.mutating||!W||!L||H,k.disabled=I.mutating||!L,_.disabled=I.mutating,i.disabled=I.mutating||I.corpora.length===0,r.disabled=I.mutating||!W,!W){p.textContent=t.t("ops.ingestion.corpusInactive");return}p.textContent=t.t("ops.ingestion.overview",{active:I.corpora.filter(Be=>Be.active).length,total:I.corpora.length,corpus:I.selectedCorpus==="autogenerar"?"AUTOGENERAR":(x==null?void 0:x.label)||I.selectedCorpus,session:(L==null?void 0:L.session_id)||t.t("ops.ingestion.noSession")})}function En(){if(T.innerHTML="",P.textContent=I.selectedSession?`${I.selectedSession.session_id} · ${I.selectedSession.status}`:t.t("ops.ingestion.selectedEmpty"),I.sessions.length===0){const x=document.createElement("li");x.className="ops-empty",x.textContent=t.t("ops.ingestion.sessionsEmpty"),T.appendChild(x);return}I.sessions.forEach(x=>{var it,rt;const L=document.createElement("li"),W=x.status==="partial_failed",H=document.createElement("button");H.type="button",H.className=`ops-session-item${x.session_id===I.selectedSessionId?" is-active":""}${W?" has-retry-action":""}`,H.dataset.sessionId=x.session_id;const Z=document.createElement("div");Z.className="ops-session-item-head";const oe=document.createElement("div");oe.className="ops-session-id",oe.textContent=x.session_id;const U=document.createElement("span");U.className=`meta-chip status-${ct(x.status)}`,U.textContent=x.status,Z.append(oe,U);const le=document.createElement("div");le.className="ops-session-pills";const ve=((it=I.corpora.find(ge=>ge.key===x.corpus))==null?void 0:it.label)||x.corpus,pe=document.createElement("span");pe.className="meta-chip ops-pill-corpus",pe.textContent=ve,le.appendChild(pe);const Fe=x.documents||[];[...new Set(Fe.map(ge=>ge.batch_type).filter(Boolean))].forEach(ge=>{const Be=document.createElement("span");Be.className="meta-chip ops-pill-batch",Be.textContent=es(ge,t),le.appendChild(Be)});const He=Fe.map(ge=>ge.filename).filter(Boolean);let Oe=null;if(He.length>0){Oe=document.createElement("div"),Oe.className="ops-session-files";const ge=He.slice(0,3),Be=He.length-ge.length;Oe.textContent=ge.join(", ")+(Be>0?` +${Be}`:"")}const Ue=document.createElement("div");Ue.className="ops-session-summary",Ue.textContent=Ht(x.batch_summary,t);const et=document.createElement("div");if(et.className="ops-session-summary",et.textContent=x.updated_at?t.formatDateTime(x.updated_at,{dateStyle:"short",timeStyle:"short",timeZone:"America/Bogota"}):"-",H.appendChild(Z),H.appendChild(le),Oe&&H.appendChild(Oe),H.appendChild(Ue),H.appendChild(et),(rt=x.last_error)!=null&&rt.code){const ge=document.createElement("div");ge.className="ops-session-summary status-error",ge.textContent=x.last_error.code,H.appendChild(ge)}if(H.addEventListener("click",async()=>{n.setSelectedSession(x),ot();try{await me({sessionId:x.session_id,showWheel:!0})}catch{}}),L.appendChild(H),W){const ge=document.createElement("button");ge.type="button",ge.className="ops-session-retry-inline",ge.textContent=t.t("ops.ingestion.actions.retry"),ge.disabled=I.mutating,ge.addEventListener("click",async Be=>{Be.stopPropagation(),ge.disabled=!0,n.setMutating(!0),at();try{await s(async()=>Se(x.session_id)),await $e({showWheel:!1,reportError:!0,focusSessionId:x.session_id}),o(t.t("ops.ingestion.flash.retryStarted",{id:x.session_id}),"success")}catch(xn){o(ke(xn),"error")}finally{n.setMutating(!1),at()}}),L.appendChild(ge)}T.appendChild(L)})}function Nn(x){const L=[],W=()=>new Date().toISOString();if(L.push(t.t("ops.ingestion.log.sessionHeader",{id:x.session_id})),L.push(`Corpus:     ${x.corpus||"-"}`),L.push(`Status:     ${x.status}`),L.push(`Created:    ${x.created_at||"-"}`),L.push(`Updated:    ${x.updated_at||"-"}`),L.push(`Heartbeat:  ${x.heartbeat_at??"-"}`),x.auto_processing&&L.push(`Auto-proc:  ${x.auto_processing}`),x.gate_sub_stage&&L.push(`Gate-stage: ${x.gate_sub_stage}`),x.wip_sync_status&&L.push(`WIP-sync:   ${x.wip_sync_status}`),x.batch_summary){const Z=x.batch_summary,oe=(x.documents||[]).filter(le=>le.status==="raw"||le.status==="needs_classification").length,U=(x.documents||[]).filter(le=>le.status==="pending_dedup").length;L.push(""),L.push("── Resumen del lote ──"),L.push(`  Total: ${Z.total}  Queued: ${Z.queued}  Processing: ${Z.processing}  Done: ${Z.done}  Failed: ${Z.failed}  Duplicados: ${Z.skipped_duplicate}  Bounced: ${Z.bounced}`),oe>0&&L.push(`  Raw (sin clasificar): ${oe}`),U>0&&L.push(`  Pending dedup: ${U}`)}x.last_error&&(L.push(""),L.push("── Error de sesión ──"),L.push(`  Código:    ${x.last_error.code||"-"}`),L.push(`  Mensaje:   ${x.last_error.message||"-"}`),L.push(`  Guía:      ${x.last_error.guidance||"-"}`),L.push(`  Siguiente: ${x.last_error.next_step||"-"}`));const H=x.documents||[];if(H.length===0)L.push(""),L.push(t.t("ops.ingestion.log.noDocuments"));else{L.push(""),L.push(`── Documentos (${H.length}) ──`);const Z={failed:0,processing:1,in_progress:1,queued:2,raw:2,done:3,completed:3,bounced:4,skipped_duplicate:5},oe=[...H].sort((U,le)=>(Z[U.status]??3)-(Z[le.status]??3));for(const U of oe)L.push(""),L.push(`  ┌─ ${U.filename} (${U.doc_id})`),L.push(`  │  Status:   ${U.status}  │  Stage: ${U.stage||"-"}  │  Progress: ${U.progress??0}%`),L.push(`  │  Bytes:    ${U.bytes??"-"}  │  Batch: ${U.batch_type||"-"}`),U.source_relative_path&&L.push(`  │  Path:     ${U.source_relative_path}`),(U.detected_topic||U.detected_type)&&(L.push(`  │  Topic:    ${U.detected_topic||"-"}  │  Type: ${U.detected_type||"-"}  │  Confidence: ${U.combined_confidence??"-"}`),U.classification_source&&L.push(`  │  Classifier: ${U.classification_source}`)),U.chunk_count!=null&&L.push(`  │  Chunks:   ${U.chunk_count}  │  Elapsed: ${U.elapsed_ms??"-"}ms`),U.dedup_match_type&&L.push(`  │  Dedup:    ${U.dedup_match_type}  │  Match: ${U.dedup_match_doc_id||"-"}`),U.replaced_doc_id&&L.push(`  │  Replaced: ${U.replaced_doc_id}`),U.error&&(L.push("  │  ❌ ERROR"),L.push(`  │    Código:    ${U.error.code||"-"}`),L.push(`  │    Mensaje:   ${U.error.message||"-"}`),L.push(`  │    Guía:      ${U.error.guidance||"-"}`),L.push(`  │    Siguiente: ${U.error.next_step||"-"}`)),L.push(`  │  Created: ${U.created_at||"-"}  │  Updated: ${U.updated_at||"-"}`),L.push("  └─")}return L.push(""),L.push(`Log generado: ${W()}`),L.join(`
`)}function Tt(){if(ne.length>0)return;const x=I.selectedSession;if(!x){$.hidden=!0,z.textContent="";return}$.hidden=!1,z.textContent=Nn(x)}function Pn(){const x=I.selectedSession;if(!x){A.textContent=t.t("ops.ingestion.selectedEmpty"),B.hidden=!0,ne.length===0&&($.hidden=!0),N.innerHTML="";return}const L=G(x.session_id),W=L>0?` · ${t.t("ops.ingestion.folderResumePending",{count:L})}`:"";if(A.textContent=`${x.session_id} · ${Ht(x.batch_summary,t)}${W}`,x.last_error?(B.hidden=!1,J.textContent=x.last_error.message||x.last_error.code||"-",q.textContent=x.last_error.guidance||"",j.textContent=`${t.t("ops.ingestion.lastErrorNext")}: ${x.last_error.next_step||"-"}`):B.hidden=!0,(x.documents||[]).length===0){N.innerHTML=`<p class="ops-empty">${t.t("ops.ingestion.documentsEmpty")}</p>`,N.style.minHeight="0",Tt();return}N.style.minHeight="",vs(x,N,t,Ke,I.corpora),Ke.clear(),Tt()}function ot(){ut(),Cn(),at(),En(),Pn()}K.render=ot,K.trace=ee,de.directFolderIngest=Mt,de.renderControls=at;const Rt=As(K,h),{startAutoPilot:An,stopAutoPilot:Va,updateAutoStatus:Xa}=Rt;async function Mt(){var Fe,Ee,He;ee(`directFolderIngest: ${I.pendingFiles.length} archivos pendientes`);const x=await Ae();ee(`Sesión asignada: ${x.session_id} (corpus=${x.corpus}, status=${x.status})`);const L=l.value||"autogenerar";ee(`Subiendo ${I.pendingFiles.length} archivos con batchType="${L}"...`),_e(x.session_id);const W=await Le(x.session_id,[...I.pendingFiles],L,Pt);if(console.log("[folder-ingest] Upload result:",{uploaded:W.uploaded,failed:W.failed}),ee(`Upload completo: ${W.uploaded} subidos, ${W.failed} fallidos${W.errors.length>0?" — "+W.errors.slice(0,5).map(Oe=>`${Oe.filename}: ${Oe.error}`).join("; "):""}`),n.setPendingFiles([]),n.setFolderUploadProgress(null),R(x.session_id),b.value="",r.value="",W.failed>0&&W.uploaded===0){const Oe=W.errors.slice(0,3).map(Ue=>`${Ue.filename}: ${Ue.error}`).join("; ");ee(`TODOS FALLARON: ${Oe}`),o(`${t.t("ops.ingestion.flash.folderUploadPartial",W)} — ${Oe}`,"error"),await $e({showWheel:!1,reportError:!0,focusSessionId:x.session_id});return}ee("Consultando estado de sesión post-upload...");const H=await Q(x.session_id),Z=Number(((Fe=H.batch_summary)==null?void 0:Fe.bounced)??0),oe=mt(H),U=Number(((Ee=H.batch_summary)==null?void 0:Ee.queued)??0),le=Number(((He=H.batch_summary)==null?void 0:He.total)??0),ve=le-Z;if(ee(`Sesión post-upload: total=${le} bounced=${Z} raw=${oe} queued=${U} actionable=${ve}`),ve===0&&Z>0){ee(`TODOS REBOTADOS: ${Z} archivos ya existen en el corpus`),n.upsertSession(H),o(`${Z} archivos ya existen en el corpus (rebotados). 0 archivos nuevos para procesar.`,"error"),ee("--- FIN (todo rebotado) ---");return}ee("Auto-procesando con threshold=0 (force-queue)..."),await Me(`/api/ingestion/sessions/${encodeURIComponent(x.session_id)}/auto-process`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({max_concurrency:5,auto_accept_threshold:0})}),await we(x.session_id),await $e({showWheel:!1,reportError:!0,focusSessionId:x.session_id});const pe=[];W.uploaded>0&&pe.push(`${ve} archivos en proceso`),Z>0&&pe.push(`${Z} rebotados`),W.failed>0&&pe.push(`${W.failed} fallidos`),o(pe.join(" · "),W.failed>0?"error":"success"),ee(`Auto-piloto iniciado para ${x.session_id}`),ee("--- FIN (éxito) ---"),An(x.session_id)}function In(){Is({ctx:K,api:h,upload:qe,intake:Y,autoPilot:Rt,render:ot,renderCorpora:ut,renderControls:at,traceClear:be,directFolderIngest:Mt,suppressPanelsOnNextRender:Ke})}return{bindEvents:In,refreshIngestion:$e,refreshSelectedSession:me,render:ot}}function Ye(e){if(e==null)return null;const t=Number(e);return!Number.isFinite(t)||t<0?null:t}function fn({i18n:e,stateController:t,dom:n,withThinkingWheel:a,setFlash:s}){const{monitorTabBtn:o,ingestionTabBtn:i,controlTabBtn:l,embeddingsTabBtn:d,reindexTabBtn:r,monitorPanel:b,ingestionPanel:C,controlPanel:f,embeddingsPanel:w,reindexPanel:E,runsBody:p,timelineNode:_,timelineMeta:g,cascadeNote:m,userCascadeNode:u,userCascadeSummary:c,technicalCascadeNode:y,technicalCascadeSummary:v,refreshRunsBtn:k}=n,{state:P}=t;function T(h){const S=Ye(h);return S===null?"-":`${e.formatNumber(S/1e3,{minimumFractionDigits:2,maximumFractionDigits:2})} s`}function A(h){t.setActiveTab(h),B()}function B(){if(!o)return;const h=P.activeTab;o.classList.toggle("is-active",h==="monitor"),o.setAttribute("aria-selected",String(h==="monitor")),i==null||i.classList.toggle("is-active",h==="ingestion"),i==null||i.setAttribute("aria-selected",String(h==="ingestion")),l==null||l.classList.toggle("is-active",h==="control"),l==null||l.setAttribute("aria-selected",String(h==="control")),d==null||d.classList.toggle("is-active",h==="embeddings"),d==null||d.setAttribute("aria-selected",String(h==="embeddings")),r==null||r.classList.toggle("is-active",h==="reindex"),r==null||r.setAttribute("aria-selected",String(h==="reindex")),b&&(b.hidden=h!=="monitor",b.classList.toggle("is-active",h==="monitor")),C&&(C.hidden=h!=="ingestion",C.classList.toggle("is-active",h==="ingestion")),f&&(f.hidden=h!=="control",f.classList.toggle("is-active",h==="control")),w&&(w.hidden=h!=="embeddings",w.classList.toggle("is-active",h==="embeddings")),E&&(E.hidden=h!=="reindex",E.classList.toggle("is-active",h==="reindex"))}function J(h){if(_.innerHTML="",!Array.isArray(h)||h.length===0){_.innerHTML=`<li>${e.t("ops.timeline.empty")}</li>`;return}h.forEach(S=>{const D=document.createElement("li");D.innerHTML=`
        <strong>${S.stage||"-"}</strong> · <span class="status-${ct(String(S.status||""))}">${S.status||"-"}</span><br/>
        <small>${S.at||"-"} · ${S.duration_ms||0} ms</small>
        <pre>${JSON.stringify(S.details||{},null,2)}</pre>
      `,_.appendChild(D)})}function q(h,S,D){const F=Ye(S==null?void 0:S.total_ms),Q=F===null?e.t("ops.timeline.summaryPending"):T(F),se=D==="user"&&String((S==null?void 0:S.chat_run_id)||"").trim()?` · chat_run ${String((S==null?void 0:S.chat_run_id)||"").trim()}`:"";h.textContent=`${e.t("ops.timeline.totalLabel")} ${Q}${se}`}function j(h){var ae,we,Pe;const S=[],D=String(((ae=h.details)==null?void 0:ae.source)||"").trim(),F=String(h.status||"").trim();D&&S.push(D),F&&F!=="ok"&&F!=="missing"&&S.push(F);const Q=Number(((we=h.details)==null?void 0:we.citations_count)||0);Number.isFinite(Q)&&Q>0&&S.push(`${Q} refs`);const se=String(((Pe=h.details)==null?void 0:Pe.panel_status)||"").trim();return se&&S.push(se),S.join(" · ")}function N(h,S,D){h.innerHTML="";const F=Array.isArray(S==null?void 0:S.steps)?(S==null?void 0:S.steps)||[]:[];if(F.length===0){h.innerHTML=`<li class="ops-cascade-step is-empty">${e.t("ops.timeline.waterfallEmpty")}</li>`;return}const Q=Ye(S==null?void 0:S.total_ms)??Math.max(1,...F.map(se=>Ye(se.cumulative_ms)??Ye(se.absolute_elapsed_ms)??0));F.forEach(se=>{const ae=Ye(se.duration_ms),we=Ye(se.offset_ms)??0,Pe=Ye(se.absolute_elapsed_ms),Se=document.createElement("li");Se.className=`ops-cascade-step ops-cascade-step--${D}${ae===null?" is-missing":""}`;const X=document.createElement("div");X.className="ops-cascade-step-head";const $e=document.createElement("div"),me=document.createElement("strong");me.textContent=se.label||"-";const Ae=document.createElement("small");Ae.className="ops-cascade-step-meta",Ae.textContent=ae===null?e.t("ops.timeline.missingStep"):`${e.t("ops.timeline.stepLabel")} ${T(ae)} · T+${T(Pe??se.cumulative_ms)}`,$e.append(me,Ae);const qe=document.createElement("span");qe.className=`meta-chip status-${ct(String(se.status||""))}`,qe.textContent=String(se.status||(ae===null?"missing":"ok")),X.append($e,qe),Se.appendChild(X);const De=document.createElement("div");De.className="ops-cascade-track";const he=document.createElement("span");he.className="ops-cascade-segment";const Le=Math.max(0,Math.min(100,we/Q*100)),Te=ae===null?0:Math.max(ae/Q*100,ae>0?2.5:0);he.style.left=`${Le}%`,he.style.width=`${Te}%`,he.setAttribute("aria-label",ae===null?`${se.label}: ${e.t("ops.timeline.missingStep")}`:`${se.label}: ${T(ae)}`),De.appendChild(he),Se.appendChild(De);const ue=j(se);if(ue){const _e=document.createElement("p");_e.className="ops-cascade-step-detail",_e.textContent=ue,Se.appendChild(_e)}h.appendChild(Se)})}async function $(){return(await Ne("/api/ops/runs?limit=30")).runs||[]}async function z(h){return Ne(`/api/ops/runs/${encodeURIComponent(h)}/timeline`)}function O(h,S){var F;const D=h.run||{};g.textContent=e.t("ops.timeline.label",{id:S}),m.textContent=e.t("ops.timeline.selectedRunMeta",{trace:String(D.trace_id||"-"),chatRun:String(((F=h.user_waterfall)==null?void 0:F.chat_run_id)||D.chat_run_id||"-")}),q(c,h.user_waterfall,"user"),q(v,h.technical_waterfall,"technical"),N(u,h.user_waterfall,"user"),N(y,h.technical_waterfall,"technical"),J(Array.isArray(h.timeline)?h.timeline:[])}function M(h){if(p.innerHTML="",!Array.isArray(h)||h.length===0){const S=document.createElement("tr");S.innerHTML=`<td colspan="4">${e.t("ops.runs.empty")}</td>`,p.appendChild(S);return}h.forEach(S=>{const D=document.createElement("tr");D.innerHTML=`
        <td><button type="button" class="link-btn" data-run-id="${S.run_id}">${S.run_id}</button></td>
        <td>${S.trace_id||"-"}</td>
        <td class="status-${ct(String(S.status||""))}">${S.status||"-"}</td>
        <td>${S.started_at?e.formatDateTime(S.started_at,{dateStyle:"short",timeStyle:"short",timeZone:"America/Bogota"}):"-"}</td>
      `,p.appendChild(D)}),p.querySelectorAll("button[data-run-id]").forEach(S=>{S.addEventListener("click",async()=>{const D=S.getAttribute("data-run-id")||"";try{const F=await a(async()=>z(D));O(F,D)}catch(F){u.innerHTML=`<li class="ops-cascade-step is-empty status-error">${ke(F)}</li>`,y.innerHTML=`<li class="ops-cascade-step is-empty status-error">${ke(F)}</li>`,_.innerHTML=`<li class="status-error">${ke(F)}</li>`}})})}async function I({showWheel:h=!0,reportError:S=!0}={}){const D=async()=>{const F=await $();M(F)};try{h?await a(D):await D()}catch(F){p.innerHTML=`<tr><td colspan="4" class="status-error">${ke(F)}</td></tr>`,S&&s(ke(F),"error")}}function K(){o==null||o.addEventListener("click",()=>{A("monitor")}),i==null||i.addEventListener("click",()=>{A("ingestion")}),l==null||l.addEventListener("click",()=>{A("control")}),d==null||d.addEventListener("click",()=>{A("embeddings")}),r==null||r.addEventListener("click",()=>{A("reindex")}),k.addEventListener("click",()=>{s(),I({showWheel:!0,reportError:!0})})}return{bindEvents:K,refreshRuns:I,renderTabs:B}}function Je(e){return String(e??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#39;")}function tt(e){return(e??0).toLocaleString("es-CO")}function Ls(e){if(e==null||e<=0)return"-";const t=Math.floor(e/60),n=Math.floor(e%60);return t>0?`${t}m ${n}s`:`${n}s`}function Ts(e){if(!e.length)return"";let t='<ol class="reindex-stage-list">';for(const n of e){const a=n.state==="completed"?"ops-dot-ok":n.state==="active"?"ops-dot-active":n.state==="failed"?"ops-dot-error":"ops-dot-pending",s=n.state==="active"?`<strong>${Je(n.label)}</strong>`:Je(n.label);t+=`<li class="reindex-stage-item reindex-stage-${n.state}"><span class="ops-dot ${a}">●</span> ${s}</li>`}return t+="</ol>",t}function bn({dom:e,setFlash:t,navigateToEmbeddings:n}){const{container:a}=e;let s=null,o="";function i(){var m,u,c;const C=s;if(!C){a.innerHTML='<p class="ops-text-muted">Cargando estado de re-index...</p>';return}const f=C.current_operation||C.last_operation,w=((m=C.current_operation)==null?void 0:m.status)==="running",E=!C.current_operation;let p="";const _=w?"En ejecución":E?"Inactivo":(f==null?void 0:f.status)??"—",g=w?"tone-yellow":(f==null?void 0:f.status)==="completed"?"tone-green":(f==null?void 0:f.status)==="failed"?"tone-red":"";if(p+=`<div class="reindex-status-row">
      <span class="corpus-status-chip ${g}">${Je(_)}</span>
      <span class="emb-target-badge">WIP</span>
      ${w?`<span class="emb-heartbeat ${Et(f==null?void 0:f.heartbeat_at,f==null?void 0:f.updated_at)}">${Et(f==null?void 0:f.heartbeat_at,f==null?void 0:f.updated_at)}</span>`:""}
    </div>`,p+='<div class="reindex-controls">',E&&(p+=`<button class="corpus-btn corpus-btn-promote" id="reindex-start-btn" ${o?"disabled":""}>Iniciar re-index</button>`),w&&f&&(p+=`<button class="corpus-btn corpus-btn-rollback" id="reindex-stop-btn" ${o?"disabled":""}>Detener</button>`),p+="</div>",(u=f==null?void 0:f.stages)!=null&&u.length&&(p+=Ts(f.stages)),f!=null&&f.progress){const y=f.progress,v=[];y.documents_processed!=null&&v.push(`Documentos: ${tt(y.documents_processed)} / ${tt(y.documents_total)}`),y.documents_indexed!=null&&v.push(`Documentos indexados: ${tt(y.documents_indexed)}`),y.elapsed_seconds!=null&&v.push(`Tiempo: ${Ls(y.elapsed_seconds)}`),v.length&&(p+=`<div class="reindex-progress-stats">${v.map(k=>`<span>${Je(k)}</span>`).join("")}</div>`)}if(f!=null&&f.quality_report){const y=f.quality_report;if(p+='<div class="reindex-quality-report">',p+="<h3>Reporte de calidad</h3>",p+=`<div class="emb-stats-grid">
        <div class="emb-stat"><span class="emb-stat-value">${tt(y.documents_indexed)}</span><span class="emb-stat-label">Documentos</span></div>
        <div class="emb-stat"><span class="emb-stat-value">${tt(y.chunks_generated)}</span><span class="emb-stat-label">Chunks</span></div>
        <div class="emb-stat"><span class="emb-stat-value">${y.blocking_issues??0}</span><span class="emb-stat-label">Blocking issues</span></div>
      </div>`,y.knowledge_class_counts){p+='<div class="reindex-kc-breakdown"><h4>Knowledge classes</h4><dl class="reindex-kc-dl">';for(const[v,k]of Object.entries(y.knowledge_class_counts))p+=`<dt>${Je(v)}</dt><dd>${tt(k)}</dd>`;p+="</dl></div>"}p+="</div>",p+=`<div class="reindex-embed-prompt">
        <p>Re-index completado. Para aplicar los nuevos summaries a los embeddings:</p>
        <button class="corpus-btn corpus-btn-promote" id="reindex-embed-now-btn">Embed ahora</button>
      </div>`}if((c=f==null?void 0:f.checks)!=null&&c.length){p+='<div class="emb-checks">';for(const y of f.checks){const v=y.ok?'<span class="ops-dot ops-dot-ok">●</span>':'<span class="ops-dot ops-dot-error">●</span>';p+=`<div class="emb-check">${v} <strong>${Je(y.label)}</strong>: ${Je(y.detail)}</div>`}p+="</div>"}f!=null&&f.log_tail&&(p+=`<details class="emb-log-accordion"><summary>Log</summary><pre class="emb-log-tail">${Je(f.log_tail)}</pre></details>`),f!=null&&f.error&&(p+=`<p class="emb-error">${Je(f.error)}</p>`),a.innerHTML=p}function l(){a.addEventListener("click",C=>{const f=C.target;f.id==="reindex-start-btn"&&d(),f.id==="reindex-stop-btn"&&r(),f.id==="reindex-embed-now-btn"&&n()})}async function d(){o="start",i();try{await ze("/api/ops/reindex/start",{mode:"from_source"}),t("Re-index iniciado","success")}catch(C){t(String(C),"error")}o="",await b()}async function r(){var f;const C=(f=s==null?void 0:s.current_operation)==null?void 0:f.job_id;if(C){o="stop",i();try{await ze("/api/ops/reindex/stop",{job_id:C}),t("Re-index detenido","success")}catch(w){t(String(w),"error")}o="",await b()}}async function b(){try{s=await Ne("/api/ops/reindex-status")}catch{}i()}return{bindEvents:l,refresh:b}}const lo=Object.freeze(Object.defineProperty({__proto__:null,createOpsReindexController:bn},Symbol.toStringTag,{value:"Module"})),Rs=3e3,Wt=8e3;function hn({stateController:e,withThinkingWheel:t,setFlash:n,refreshRuns:a,refreshIngestion:s,refreshCorpusLifecycle:o,refreshEmbeddings:i,refreshReindex:l,intervalMs:d}){(async()=>{try{await t(async()=>{await Promise.all([a({showWheel:!1,reportError:!1}),s({showWheel:!1,reportError:!1}),o==null?void 0:o(),i==null?void 0:i(),l==null?void 0:l()])})}catch(w){n(ke(w),"error")}})();let r=null,b=d??Wt;function C(){const w=e.state.selectedSession;return w?ht(String(w.status||""))?!0:(w.documents||[]).some(p=>p.status==="in_progress"||p.status==="processing"||p.status==="extracting"||p.status==="etl"||p.status==="writing"||p.status==="gates"):!1}function f(){const w=d??(C()?Rs:Wt);r!==null&&w===b||(r!==null&&window.clearInterval(r),b=w,r=window.setInterval(()=>{a({showWheel:!1,reportError:!1}),s({showWheel:!1,reportError:!1,focusSessionId:e.getFocusedRunningSessionId()}),o==null||o(),i==null||i(),l==null||l(),d||f()},b))}return f(),()=>{r!==null&&(window.clearInterval(r),r=null)}}function _n(){const e={activeTab:Xn(),corpora:[],selectedCorpus:"autogenerar",sessions:[],selectedSessionId:Zn(),selectedSession:null,pendingFiles:[],intake:[],reviewPlan:null,preflightRunId:0,mutating:!1,folderUploadProgress:null,folderRelativePaths:new Map,rejectedArtifacts:[],preflightManifest:null,preflightScanProgress:null};function t(){return e.corpora.find(c=>c.key===e.selectedCorpus)}function n(c){e.activeTab=c,Yn(c)}function a(c){e.corpora=[...c]}function s(c){e.folderUploadProgress=c}function o(c){e.preflightManifest=c}function i(c){e.preflightScanProgress=c}function l(c){e.mutating=c}function d(c){e.pendingFiles=[...c]}function r(c){e.intake=[...c]}function b(c){e.reviewPlan=c?{...c,willIngest:[...c.willIngest],bounced:[...c.bounced]}:null}function C(){return e.preflightRunId+=1,e.preflightRunId}function f(c){e.selectedCorpus=c}function w(c){e.selectedSession=c,e.selectedSessionId=(c==null?void 0:c.session_id)||"",Qn((c==null?void 0:c.session_id)||null),c&&(_=!1)}function E(){_=!0,w(null)}function p(c){e.sessions=[...c]}let _=!1;function g(){if(e.selectedSessionId){const c=e.sessions.find(y=>y.session_id===e.selectedSessionId)||null;w(c);return}if(_){w(null);return}w(e.sessions[0]||null)}function m(c){const y=e.sessions.filter(v=>v.session_id!==c.session_id);e.sessions=[c,...y].sort((v,k)=>Date.parse(String(k.updated_at||0))-Date.parse(String(v.updated_at||0))),w(c)}function u(){var c;return ht(String(((c=e.selectedSession)==null?void 0:c.status)||""))?e.selectedSessionId:""}return{state:e,clearSelectionAfterDelete:E,getFocusedRunningSessionId:u,selectedCorpusConfig:t,setActiveTab:n,setCorpora:a,setFolderUploadProgress:s,setMutating:l,setPendingFiles:d,setIntake:r,setReviewPlan:b,bumpPreflightRunId:C,setPreflightManifest:o,setPreflightScanProgress:i,setSelectedCorpus:f,setSelectedSession:w,setSessions:p,syncSelectedSession:g,upsertSession:m}}function Ms(e){const{value:t,unit:n,size:a="md",className:s=""}=e,o=document.createElement("span");o.className=["lia-metric-value",`lia-metric-value--${a}`,s].filter(Boolean).join(" "),o.setAttribute("data-lia-component","metric-value");const i=document.createElement("span");if(i.className="lia-metric-value__number",i.textContent=typeof t=="number"?t.toLocaleString("es-CO"):String(t),o.appendChild(i),n){const l=document.createElement("span");l.className="lia-metric-value__unit",l.textContent=n,o.appendChild(l)}return o}function pt(e){const{label:t,value:n,unit:a,hint:s,size:o="lg",tone:i="neutral",className:l=""}=e,d=document.createElement("div");d.className=["lia-metric-card",`lia-metric-card--${i}`,l].filter(Boolean).join(" "),d.setAttribute("data-lia-component","metric-card");const r=document.createElement("p");if(r.className="lia-metric-card__label",r.textContent=t,d.appendChild(r),d.appendChild(Ms({value:n,unit:a,size:o})),s){const b=document.createElement("p");b.className="lia-metric-card__hint",b.textContent=s,d.appendChild(b)}return d}function qs(e){if(!e)return"sin activar";try{const t=new Date(e);if(Number.isNaN(t.getTime()))return"—";const n=Date.now()-t.getTime(),a=Math.floor(n/6e4);if(a<1)return"hace instantes";if(a<60)return`hace ${a} min`;const s=Math.floor(a/60);return s<24?`hace ${s} h`:`hace ${Math.floor(s/24)} d`}catch{return"—"}}function Ds(e){const t=document.createElement("section");t.className="lia-corpus-overview",t.setAttribute("data-lia-component","corpus-overview");const n=document.createElement("header");n.className="lia-corpus-overview__header";const a=document.createElement("h2");a.className="lia-corpus-overview__title",a.textContent="Corpus activo",n.appendChild(a);const s=document.createElement("p");if(s.className="lia-corpus-overview__subtitle",e.activeGenerationId){const i=document.createElement("code");i.textContent=e.activeGenerationId,s.appendChild(document.createTextNode("Generación ")),s.appendChild(i),s.appendChild(document.createTextNode(` · activada ${qs(e.activatedAt)}`))}else s.textContent="Ninguna generación activa en Supabase.";n.appendChild(s),t.appendChild(n);const o=document.createElement("div");return o.className="lia-corpus-overview__grid",o.appendChild(pt({label:"Documentos servidos",value:e.documents,hint:e.documents>0?`${e.chunks.toLocaleString("es-CO")} chunks indexados`:"—"})),o.appendChild(pt({label:"Grafo de normativa",value:e.graphNodes,unit:"nodos",hint:`${e.graphEdges.toLocaleString("es-CO")} relaciones tipadas`,tone:e.graphOk?"success":"warning"})),o.appendChild(pt({label:"Auditoría del corpus",value:e.auditIncluded,unit:"incluidos",hint:`${e.auditScanned.toLocaleString("es-CO")} escaneados · ${e.auditExcluded.toLocaleString("es-CO")} excluidos`})),o.appendChild(pt({label:"Revisiones pendientes",value:e.auditPendingRevisions,hint:e.auditPendingRevisions===0?"Cuello limpio":"Requieren resolución",tone:e.auditPendingRevisions===0?"success":"warning"})),t.appendChild(o),t}function Fs(e){const{tone:t,pulse:n=!1,ariaLabel:a,className:s=""}=e,o=document.createElement("span");return o.className=["lia-status-dot",`lia-status-dot--${t}`,n?"lia-status-dot--pulse":"",s].filter(Boolean).join(" "),o.setAttribute("data-lia-component","status-dot"),o.setAttribute("role","status"),a&&o.setAttribute("aria-label",a),o}const Os={active:"active",superseded:"idle",running:"running",queued:"running",failed:"error",pending:"warning"},Jt={active:"Activa",superseded:"Reemplazada",running:"En curso",queued:"En cola",failed:"Falló",pending:"Pendiente"};function vn(e){const{status:t,className:n=""}=e,a=document.createElement("span");a.className=["lia-run-status",`lia-run-status--${t}`,n].filter(Boolean).join(" "),a.setAttribute("data-lia-component","run-status"),a.appendChild(Fs({tone:Os[t],pulse:t==="running"||t==="queued",ariaLabel:Jt[t]}));const s=document.createElement("span");return s.className="lia-run-status__label",s.textContent=Jt[t],a.appendChild(s),a}function Bs(e){if(!e)return"—";try{const t=new Date(e);return Number.isNaN(t.getTime())?"—":t.toLocaleString("es-CO",{day:"numeric",month:"short",hour:"2-digit",minute:"2-digit"})}catch{return e}}function js(e,t){const n=document.createElement(t?"button":"div");n.className="lia-generation-row",n.setAttribute("data-lia-component","generation-row"),t&&(n.type="button",n.addEventListener("click",()=>t(e.generationId)));const a=document.createElement("span");a.className="lia-generation-row__id",a.textContent=e.generationId,n.appendChild(a),n.appendChild(vn({status:e.status}));const s=document.createElement("span");s.className="lia-generation-row__date",s.textContent=Bs(e.generatedAt),n.appendChild(s);const o=document.createElement("span");o.className="lia-generation-row__count",o.textContent=`${e.documents.toLocaleString("es-CO")} docs`,n.appendChild(o);const i=document.createElement("span");if(i.className="lia-generation-row__count lia-generation-row__count--muted",i.textContent=`${e.chunks.toLocaleString("es-CO")} chunks`,n.appendChild(i),e.topClass&&e.topClassCount){const l=document.createElement("span");l.className="lia-generation-row__family",l.textContent=`${e.topClass}: ${e.topClassCount.toLocaleString("es-CO")}`,n.appendChild(l)}if(e.subtopicCoverage){const l=e.subtopicCoverage,d=e.documents>0?e.documents:1,r=Math.round(l.docsWithSubtopic/d*100),b=document.createElement("span");b.className="lia-generation-row__subtopic",b.setAttribute("data-lia-component","generation-row-subtopic");const C=l.docsRequiringReview&&l.docsRequiringReview>0?` (${l.docsRequiringReview} por revisar)`:"";b.textContent=`subtema: ${r}%${C}`,n.appendChild(b)}return n}function Gt(e){const{rows:t,emptyMessage:n="Aún no hay generaciones registradas.",errorMessage:a,onSelect:s}=e,o=document.createElement("section");o.className="lia-generations-list",o.setAttribute("data-lia-component","generations-list");const i=document.createElement("header");i.className="lia-generations-list__header";const l=document.createElement("h2");l.className="lia-generations-list__title",l.textContent="Generaciones recientes",i.appendChild(l);const d=document.createElement("p");d.className="lia-generations-list__subtitle",d.textContent="Cada fila es una corrida de python -m lia_graph.ingest publicada en Supabase.",i.appendChild(d),o.appendChild(i);const r=document.createElement("div");if(r.className="lia-generations-list__body",a){const b=document.createElement("p");b.className="lia-generations-list__feedback lia-generations-list__feedback--error",b.textContent=a,r.appendChild(b)}else if(t.length===0){const b=document.createElement("p");b.className="lia-generations-list__feedback",b.textContent=n,r.appendChild(b)}else{const b=document.createElement("div");b.className="lia-generations-list__head-row",["Generación","Estado","Fecha","Documentos","Chunks","Familia principal"].forEach(C=>{const f=document.createElement("span");f.className="lia-generations-list__head-cell",f.textContent=C,b.appendChild(f)}),r.appendChild(b),t.forEach(C=>r.appendChild(js(C,s)))}return o.appendChild(r),o}const zs=[{key:"knowledge_base",label:"knowledge_base/",sublabel:"snapshot Dropbox"},{key:"wip",label:"WIP",sublabel:"Supabase local + Falkor local"},{key:"cloud",label:"Cloud",sublabel:"Supabase cloud + Falkor cloud"}];function Hs(e){const{activeStage:t,className:n=""}=e,a=document.createElement("nav");return a.className=["lia-pipeline-flow",n].filter(Boolean).join(" "),a.setAttribute("data-lia-component","pipeline-flow"),a.setAttribute("aria-label","Pipeline de ingestión Lia Graph"),zs.forEach((s,o)=>{if(o>0){const r=document.createElement("span");r.className="lia-pipeline-flow__arrow",r.setAttribute("aria-hidden","true"),r.textContent="→",a.appendChild(r)}const i=document.createElement("div");i.className=["lia-pipeline-flow__stage",s.key===t?"lia-pipeline-flow__stage--active":""].filter(Boolean).join(" "),i.setAttribute("data-stage",s.key);const l=document.createElement("span");l.className="lia-pipeline-flow__label",l.textContent=s.label,i.appendChild(l);const d=document.createElement("span");d.className="lia-pipeline-flow__sublabel",d.textContent=s.sublabel,i.appendChild(d),a.appendChild(i)}),a}function Us(e){const{activeJobId:t,lastRunStatus:n,disabled:a,onTrigger:s}=e,o=document.createElement("section");o.className="lia-run-trigger",o.setAttribute("data-lia-component","run-trigger-card");const i=document.createElement("header");i.className="lia-run-trigger__header";const l=document.createElement("h3");l.className="lia-run-trigger__title",l.textContent="Ingesta completa",i.appendChild(l);const d=document.createElement("p");d.className="lia-run-trigger__subtitle",d.innerHTML="Lee <code>knowledge_base/</code> en disco completo y lo reconstruye desde cero: re-audita, re-clasifica, re-parsea y re-publica los ~1.3k documentos. Tarda 30–40 minutos y cuesta aprox. US$ 6–16 en LLM. Úsala cuando cambie el clasificador, la taxonomía, o quieras un baseline limpio. Para cambios puntuales, prefiere Delta aditivo.",i.appendChild(d);const r=document.createElement("p");r.className="lia-run-trigger__safety",r.innerHTML="<strong>Seguridad:</strong> por defecto escribe a la base local (WIP). Solo promueve a la nube cuando el resultado esté validado — desde la pestaña Promoción.",i.appendChild(r),o.appendChild(i),o.appendChild(Hs({activeStage:"wip"}));const b=document.createElement("form");b.className="lia-run-trigger__form",b.setAttribute("novalidate","");const C=Ws({name:"supabase_target",legend:"¿Dónde escribir?",options:[{value:"wip",label:"Base local (recomendado)",hint:"Escribe a Supabase y FalkorDB locales en Docker. Ciclo seguro: no afecta la base de producción.",defaultChecked:!0},{value:"production",label:"Producción (nube)",hint:"Escribe directo a Supabase y FalkorDB en la nube. Afecta lo que ven los usuarios hoy."}]});b.appendChild(C);const f=Gs({name:"suin_scope",label:"Incluir jurisprudencia SUIN (opcional)",placeholder:"déjalo vacío si solo quieres re-ingerir la base",hint:"Además del corpus base, incluye documentos SUIN-Juriscol descargados. Valores válidos: et · tributario · laboral · jurisprudencia."});b.appendChild(f);const w=Js([{name:"skip_embeddings",label:"Saltar embeddings",hint:"No recalcula los embeddings al final. Usa esto solo si vas a correrlos manualmente después.",defaultChecked:!1},{name:"auto_promote",label:"Promover a la nube al terminar",hint:"Si la ingesta local termina sin errores, encadena automáticamente una promoción a la nube.",defaultChecked:!1}]);b.appendChild(w);const E=document.createElement("div");E.className="lia-run-trigger__submit-row";const p=document.createElement("button");if(p.type="submit",p.className="lia-button lia-button--primary lia-run-trigger__submit",p.textContent=t?"Ejecutando…":"Reconstruir todo",p.disabled=a,E.appendChild(p),n&&E.appendChild(vn({status:n})),t){const _=document.createElement("code");_.className="lia-run-trigger__job-id",_.textContent=t,E.appendChild(_)}return b.appendChild(E),b.addEventListener("submit",_=>{if(_.preventDefault(),a)return;const g=new FormData(b),m=g.get("supabase_target")||"wip",u=String(g.get("suin_scope")||"").trim(),c=g.get("skip_embeddings")!=null,y=g.get("auto_promote")!=null;s({suinScope:u,supabaseTarget:m==="production"?"production":"wip",autoEmbed:!c,autoPromote:y})}),o.appendChild(b),o}function Ws(e){const t=document.createElement("fieldset");t.className="lia-run-trigger__field lia-run-trigger__field--radio";const n=document.createElement("legend");return n.className="lia-run-trigger__legend",n.textContent=e.legend,t.appendChild(n),e.options.forEach(a=>{const s=document.createElement("label");s.className="lia-run-trigger__radio-row";const o=document.createElement("input");o.type="radio",o.name=e.name,o.value=a.value,a.defaultChecked&&(o.defaultChecked=!0),s.appendChild(o);const i=document.createElement("span");i.className="lia-run-trigger__radio-text";const l=document.createElement("span");if(l.className="lia-run-trigger__radio-label",l.textContent=a.label,i.appendChild(l),a.hint){const d=document.createElement("span");d.className="lia-run-trigger__radio-hint",d.textContent=a.hint,i.appendChild(d)}s.appendChild(i),t.appendChild(s)}),t}function Js(e){const t=document.createElement("fieldset");t.className="lia-run-trigger__field lia-run-trigger__field--checkbox";const n=document.createElement("legend");return n.className="lia-run-trigger__legend",n.textContent="Opciones de corrida",t.appendChild(n),e.forEach(a=>{const s=document.createElement("label");s.className="lia-run-trigger__checkbox-row";const o=document.createElement("input");o.type="checkbox",o.name=a.name,a.defaultChecked&&(o.defaultChecked=!0),s.appendChild(o);const i=document.createElement("span");i.className="lia-run-trigger__checkbox-text";const l=document.createElement("span");if(l.className="lia-run-trigger__checkbox-label",l.textContent=a.label,i.appendChild(l),a.hint){const d=document.createElement("span");d.className="lia-run-trigger__checkbox-hint",d.textContent=a.hint,i.appendChild(d)}s.appendChild(i),t.appendChild(s)}),t}function Gs(e){const t=document.createElement("div");t.className="lia-run-trigger__field lia-run-trigger__field--text";const n=document.createElement("label");n.className="lia-run-trigger__label",n.htmlFor=`lia-run-trigger-${e.name}`,n.textContent=e.label,t.appendChild(n);const a=document.createElement("input");if(a.type="text",a.id=`lia-run-trigger-${e.name}`,a.name=e.name,a.className="lia-input lia-run-trigger__input",a.autocomplete="off",a.spellcheck=!1,e.placeholder&&(a.placeholder=e.placeholder),t.appendChild(a),e.hint){const s=document.createElement("p");s.className="lia-run-trigger__hint",s.textContent=e.hint,t.appendChild(s)}return t}function Ks(){const e=document.createElement("article");e.className="lia-adelta-card",e.setAttribute("data-lia-component","additive-delta-card");const t=document.createElement("header");t.className="lia-adelta-card__header";const n=document.createElement("h3");n.className="lia-adelta-card__title",n.textContent="Delta aditivo",t.appendChild(n);const a=document.createElement("p");a.className="lia-adelta-card__body",a.innerHTML="Compara <code>knowledge_base/</code> contra la base ya publicada y procesa <strong>solo agregados y modificados</strong>. Los archivos llegan a la carpeta en el <strong>Paso 1 arriba</strong> (arrastre, Dropbox o editor directo). <strong>Nunca retira docs de producción</strong>: si un archivo está en la base pero falta en disco, este flujo lo marca como diagnóstico y sigue. El borrado de cloud es CLI-only y explícito (<code>--allow-retirements</code>).",t.appendChild(a);const s=document.createElement("p");s.className="lia-adelta-card__steps",s.innerHTML="<strong>Previsualizar</strong> muestra el diff sin escribir nada (segundos para deltas pequeños). <strong>Aplicar</strong> procesa el delta con una confirmación explícita (minutos, no horas). Si cambiaste el prompt del clasificador o la taxonomía, usá <strong>Ingesta completa</strong> a la derecha — el delta aditivo no re-clasifica docs byte-idénticos.",t.appendChild(s),e.appendChild(t);const o=document.createElement("div");return o.className="lia-adelta-card__mount",e.appendChild(o),{element:e,mount:o}}function Vs(e){const t=document.createElement("article");t.className=`lia-corpus-health-metric lia-corpus-health-metric--${e.tone}`,t.setAttribute("data-lia-component","corpus-health-metric"),t.setAttribute("data-tone",e.tone);const n=document.createElement("h4");n.className="lia-corpus-health-metric__title",n.textContent=e.title;const a=document.createElement("p");if(a.className="lia-corpus-health-metric__primary",a.textContent=e.primary,t.append(n,a),e.secondary&&e.secondary.trim()){const s=document.createElement("p");s.className="lia-corpus-health-metric__secondary",s.textContent=e.secondary,t.appendChild(s)}return t}function Lt(e){if(!e)return"—";const t=Date.parse(e);if(Number.isNaN(t))return"—";const n=Math.max(0,Math.floor((Date.now()-t)/1e3));return n<60?`hace ${n}s`:n<3600?`hace ${Math.floor(n/60)} min`:n<86400?`hace ${Math.floor(n/3600)} h`:`hace ${Math.floor(n/86400)} días`}function Xs(e){const t=e.generation.id??"(sin generación activa)",n=e.generation.documents.toLocaleString("es-CO"),a=e.generation.chunks.toLocaleString("es-CO"),s=e.generation.activated_at?`activada ${Lt(e.generation.activated_at)}`:"sin activar";return{title:"Generación activa",primary:t,secondary:`${n} docs · ${a} chunks · ${s}`,tone:e.generation.id?"ok":"warning"}}function Ys(e){const t=e.parity;return t.ok===null?{title:"Parity Supabase ↔ Falkor",primary:"—",secondary:"Probe no disponible (Falkor sin configurar)",tone:"neutral"}:t.ok?{title:"Parity Supabase ↔ Falkor",primary:"Alineada ✓",secondary:`${t.supabase_docs??0} docs · ${t.supabase_edges??0} aristas`,tone:"ok"}:{title:"Parity Supabase ↔ Falkor",primary:"Desfasada",secondary:t.mismatches.map(a=>`${a.field} (Δ${a.delta})`).join(", ")||"mismatches sin nombre",tone:"danger"}}function Zs(e){const t=e.embeddings;if(t.pending_chunks===null)return{title:"Embeddings",primary:"—",secondary:"Sin métrica",tone:"neutral"};if(t.pending_chunks===0)return{title:"Embeddings",primary:"Completos ✓",secondary:t.pct_complete!==null?`${t.pct_complete}% al día`:"",tone:"ok"};const n=t.pct_complete!==null?`${t.pct_complete}%`:"";return{title:"Embeddings",primary:`${t.pending_chunks.toLocaleString("es-CO")} chunks pendientes`,secondary:`${n} al día — corre \`make phase2-embed-backfill\``,tone:"warning"}}function Qs(e){const t=e.last_delta;return t?{title:"Última ingesta",primary:Lt(t.completed_at),secondary:`+${t.documents_added} / ~${t.documents_modified} / -${t.documents_retired} docs · ${t.chunks_written.toLocaleString("es-CO")} chunks (${t.target})`,tone:"ok"}:{title:"Última ingesta",primary:"Sin runs registrados",secondary:"El historial de delta_jobs está vacío",tone:"neutral"}}function ea(e={}){const t=e.fetchPath??"/api/ingest/corpus_health",n=e.autoRefreshMs??6e4,a=e.getJsonImpl??Ne,s=document.createElement("section");s.className="lia-corpus-health",s.setAttribute("data-lia-component","corpus-health-card");const o=document.createElement("header");o.className="lia-corpus-health__header";const i=document.createElement("h3");i.className="lia-corpus-health__title",i.textContent="Salud del corpus";const l=document.createElement("span");l.className="lia-corpus-health__checked-at",l.textContent="verificando…";const d=Ze({label:"Refrescar",tone:"ghost",onClick:()=>void p()});o.append(i,l,d),s.appendChild(o);const r=document.createElement("div");r.className="lia-corpus-health__grid",s.appendChild(r);const b=document.createElement("p");b.className="lia-corpus-health__empty",b.textContent="Cargando…",r.appendChild(b);let C=null,f=!1;function w(_){r.replaceChildren();const g=[Xs(_),Ys(_),Zs(_),Qs(_)];for(const m of g)r.appendChild(Vs(m));l.textContent=`verificado ${Lt(_.checked_at_utc)}`}function E(_){r.replaceChildren();const g=document.createElement("p");g.className="lia-corpus-health__empty lia-corpus-health__empty--error",g.textContent=`No se pudo cargar la salud del corpus: ${_}`,r.appendChild(g),l.textContent="error"}async function p(){if(!f){d.disabled=!0;try{const _=await a(t);if(f)return;if(!_||!("ok"in _)||!_.ok){E("respuesta sin ok=true");return}w(_)}catch(_){if(f)return;E(_ instanceof Error?_.message:String(_))}finally{d.disabled=!1}}}return p(),n>0&&(C=setInterval(()=>void p(),n)),{element:s,refresh:p,destroy(){f=!0,C&&(clearInterval(C),C=null)}}}const Kt=["B","KB","MB","GB","TB"];function Vt(e){if(!Number.isFinite(e)||e<=0)return"0 B";let t=0,n=e;for(;n>=1024&&t<Kt.length-1;)n/=1024,t+=1;const a=t===0?Math.round(n):Math.round(n*10)/10;return`${Number.isInteger(a)?`${a}`:a.toFixed(1)} ${Kt[t]}`}function ta(e){const t=e.toLowerCase();return t.endsWith(".pdf")?"📕":t.endsWith(".docx")||t.endsWith(".doc")?"📘":t.endsWith(".md")?"📄":t.endsWith(".txt")?"📃":"📄"}function na(e){const{filename:t,bytes:n,onRemove:a,className:s=""}=e,o=document.createElement("span");o.className=["lia-file-chip",s].filter(Boolean).join(" "),o.setAttribute("data-lia-component","file-chip"),o.title=`${t} - ${Vt(n)}`;const i=document.createElement("span");i.className="lia-file-chip__icon",i.setAttribute("aria-hidden","true"),i.textContent=ta(t),o.appendChild(i);const l=document.createElement("span");l.className="lia-file-chip__name",l.textContent=t,o.appendChild(l);const d=document.createElement("span");if(d.className="lia-file-chip__size",d.textContent=Vt(n),o.appendChild(d),a){const r=document.createElement("button");r.type="button",r.className="lia-file-chip__remove",r.setAttribute("aria-label",`Quitar ${t}`),r.textContent="x",r.addEventListener("click",b=>{b.preventDefault(),b.stopPropagation(),a()}),o.appendChild(r)}return o}function Xt(e){const{subtopicKey:t,label:n,confidence:a,requiresReview:s,isNew:o,className:i=""}=e;let l="brand";s?l="warning":o&&(l="info");const d=n&&n.trim()?n:t,r=a!=null&&!Number.isNaN(a)?`${d} · ${Math.round(a<=1?a*100:a)}%`:d,b=Qe({label:r,tone:l,emphasis:"soft",className:["lia-subtopic-chip",i].filter(Boolean).join(" "),dataComponent:"subtopic-chip"});return b.setAttribute("data-subtopic-key",t),s&&b.setAttribute("data-subtopic-review","true"),o&&b.setAttribute("data-subtopic-new","true"),b}function sa(e){if(e==null||Number.isNaN(e))return"-";const t=e<=1?e*100:e;return`${Math.round(t)}%`}function aa(e){if(e==null||Number.isNaN(e))return"neutral";const t=e<=1?e*100:e;return t>=80?"success":t>=50?"warning":"error"}function oa(e){const{filename:t,bytes:n,detectedTopic:a,topicLabel:s,combinedConfidence:o,requiresReview:i,coercionMethod:l,subtopicKey:d,subtopicLabel:r,subtopicConfidence:b,subtopicIsNew:C,requiresSubtopicReview:f,onRemove:w,className:E=""}=e,p=document.createElement("div");p.className=["lia-intake-file-row",E].filter(Boolean).join(" "),p.setAttribute("data-lia-component","intake-file-row");const _=document.createElement("span");_.className="lia-intake-file-row__file",_.appendChild(na({filename:t,bytes:n,onRemove:w})),p.appendChild(_);const g=document.createElement("span");if(g.className="lia-intake-file-row__meta",s||a){const m=Ln({label:s||a||"sin tópico",tone:"info",emphasis:"soft",className:"lia-intake-file-row__topic"});a&&m.setAttribute("data-topic",a),g.appendChild(m)}if(o!=null){const m=Qe({label:sa(o),tone:aa(o),emphasis:"soft",className:"lia-intake-file-row__confidence"});g.appendChild(m)}if(i){const m=Qe({label:"requiere revisión",tone:"warning",emphasis:"solid",className:"lia-intake-file-row__review"});m.setAttribute("role","status"),g.appendChild(m)}if(d?g.appendChild(Xt({subtopicKey:d,label:r||null,confidence:b??null,isNew:C,requiresReview:f,className:"lia-intake-file-row__subtopic"})):C&&e.subtopicKey!==void 0&&g.appendChild(Xt({subtopicKey:"(nuevo)",label:r||"subtema propuesto",isNew:!0,className:"lia-intake-file-row__subtopic"})),f&&!d){const m=Qe({label:"subtema pendiente",tone:"warning",emphasis:"soft",className:"lia-intake-file-row__subtopic-review"});m.setAttribute("data-subtopic-review","true"),g.appendChild(m)}if(l){const m=document.createElement("span");m.className="lia-intake-file-row__coercion",m.textContent=l,g.appendChild(m)}return p.appendChild(g),p}function yn(e={}){const{size:t="inline",ariaLabel:n,className:a=""}=e,s=document.createElement("span");return s.className=["lia-spinner",`lia-spinner--${t}`,a].filter(Boolean).join(" "),s.setAttribute("data-lia-component","spinner"),s.setAttribute("role","status"),n?s.setAttribute("aria-label",n):s.setAttribute("aria-hidden","true"),s}const At="intake-drop-zone.lastBatch";function ia(){try{if(typeof localStorage>"u")return null;const e=localStorage.getItem(At);if(!e)return null;const t=JSON.parse(e);return!t||typeof t!="object"?null:t}catch{return null}}function wt(e){try{if(typeof localStorage>"u")return;if(e==null){localStorage.removeItem(At);return}localStorage.setItem(At,JSON.stringify(e))}catch{}}const ra=[".md",".txt",".json",".pdf",".docx"];function la(e){const t=e.toLowerCase();return ra.some(n=>t.endsWith(n))}function ca(e){return e.split("/").filter(Boolean).some(n=>n.startsWith("."))}function da(e){return e.includes("__MACOSX/")||e.startsWith("__MACOSX/")}function ua(e,t){return!(!e||da(t)||ca(t)||e.startsWith(".")||!la(e))}async function pa(e){const t=[];for(;;){const n=await new Promise(a=>{e.readEntries(s=>a(s||[]))});if(n.length===0)break;t.push(...n)}return t}async function kn(e,t){if(!e)return[];const n=t?`${t}/${e.name}`:e.name;if(e.isFile){if(!e.file)return[];const a=await new Promise(s=>e.file(s));return[{filename:a.name,bytes:a.size,mime:a.type||void 0,relativePath:n,file:a}]}if(e.isDirectory&&e.createReader){const a=e.createReader(),s=await pa(a);return(await Promise.all(s.map(i=>kn(i,n)))).flat()}return[]}async function ma(e){const t=e.items?Array.from(e.items):[];if(t.length>0&&typeof t[0].webkitGetAsEntry=="function"){const a=[];for(const s of t){const o=s.webkitGetAsEntry();if(!o)continue;const i=await kn(o,"");a.push(...i)}return a}return(e.files?Array.from(e.files):[]).map(a=>({filename:a.name,bytes:a.size,mime:a.type||void 0,relativePath:a.name,file:a}))}function ga(e,t){return t?{filename:t.filename||e.filename,mime:t.mime||e.mime,bytes:t.bytes??e.bytes,detectedTopic:t.detected_topic??null,topicLabel:t.topic_label??null,combinedConfidence:t.combined_confidence??null,requiresReview:!!t.requires_review,coercionMethod:t.coercion_method??null,subtopicKey:t.subtopic_key??null,subtopicLabel:t.subtopic_label??null,subtopicConfidence:t.subtopic_confidence??null,subtopicIsNew:!!t.subtopic_is_new,requiresSubtopicReview:!!t.requires_subtopic_review}:{filename:e.filename,mime:e.mime,bytes:e.bytes,detectedTopic:null,topicLabel:null,combinedConfidence:null,requiresReview:!1,coercionMethod:null}}function fa(e){const{onIntake:t,onApprove:n,confirmDestructive:a}=e,s=document.createElement("section");s.className="lia-intake-drop-zone",s.setAttribute("data-lia-component","intake-drop-zone");const o=document.createElement("header");o.className="lia-intake-drop-zone__header";const i=document.createElement("h2");i.className="lia-intake-drop-zone__title",i.textContent="Arrastra archivos o carpetas",o.appendChild(i);const l=document.createElement("p");l.className="lia-intake-drop-zone__hint",l.textContent="Acepta .md, .txt, .json, .pdf, .docx. Carpetas se recorren recursivamente. Ocultos y __MACOSX/ se descartan.",o.appendChild(l),s.appendChild(o);const d=document.createElement("div");d.className="lia-intake-drop-zone__zone",d.setAttribute("role","button"),d.setAttribute("tabindex","0"),d.setAttribute("aria-label","Zona de arrastre para ingesta");const r=document.createElement("p");r.className="lia-intake-drop-zone__zone-label",r.textContent="Suelta aquí los archivos para enviarlos al intake",d.appendChild(r),s.appendChild(d);const b=document.createElement("div");b.className="lia-intake-drop-zone__list",b.setAttribute("data-role","intake-file-list"),s.appendChild(b);const C=document.createElement("p");C.className="lia-intake-drop-zone__feedback",C.setAttribute("role","status"),s.appendChild(C);const f=document.createElement("div");f.className="lia-intake-drop-zone__actions";const w=document.createElement("button");w.type="button",w.className="lia-button lia-button--ghost lia-intake-drop-zone__clear",w.textContent="Borrar todo",w.hidden=!0,f.appendChild(w);const E=document.createElement("button");E.type="button",E.className="lia-button lia-button--primary lia-intake-drop-zone__approve",E.disabled=!0;const p=document.createElement("span");p.className="lia-intake-drop-zone__approve-label",p.textContent="Aprobar e ingerir",E.appendChild(p),f.appendChild(E),s.appendChild(f);const _={queued:[],lastResponse:null,analyzing:!1};function g(){var P;if(b.replaceChildren(),_.queued.length===0){const T=document.createElement("p");T.className="lia-intake-drop-zone__empty",T.textContent="Sin archivos en cola.",b.appendChild(T);return}const k=new Map;if((P=_.lastResponse)!=null&&P.files)for(const T of _.lastResponse.files)T.filename&&k.set(T.filename,T);_.queued.forEach((T,A)=>{const B=k.get(T.filename),J=oa({...ga(T,B),onRemove:()=>{_.queued.splice(A,1),g(),m()}});b.appendChild(J)})}function m(){var P,T;const k=((T=(P=_.lastResponse)==null?void 0:P.summary)==null?void 0:T.placed)??0;if(E.classList.remove("lia-intake-drop-zone__approve--analyzing","lia-intake-drop-zone__approve--ready"),E.replaceChildren(),_.analyzing){E.disabled=!0,E.classList.add("lia-intake-drop-zone__approve--analyzing"),E.appendChild(yn({size:"sm",ariaLabel:"Analizando"}));const A=document.createElement("span");A.className="lia-intake-drop-zone__approve-label",A.textContent="Analizando archivos",E.appendChild(A)}else{const A=document.createElement("span");A.className="lia-intake-drop-zone__approve-label",A.textContent="Ir al siguiente paso →",E.appendChild(A),E.disabled=k<=0,k>0&&E.classList.add("lia-intake-drop-zone__approve--ready")}w.hidden=_.queued.length===0&&_.lastResponse==null&&!_.analyzing}function u(){_.queued=[],_.lastResponse=null,_.analyzing=!1,C.textContent="",wt(null),g(),m()}function c(){if(_.queued.length===0&&_.lastResponse==null){wt(null);return}wt({queuedFilenames:_.queued.map(k=>({filename:k.filename,mime:k.mime,bytes:k.bytes,relativePath:k.relativePath})),lastResponse:_.lastResponse,savedAt:new Date().toISOString()})}function y(){var B,J,q;const k=ia();if(!k||!((((B=k.queuedFilenames)==null?void 0:B.length)??0)>0||!!k.lastResponse))return;_.queued=(k.queuedFilenames??[]).map(j=>({filename:j.filename,mime:j.mime,bytes:j.bytes,relativePath:j.relativePath,content_base64:""})),_.lastResponse=k.lastResponse??null,_.analyzing=!1,g(),m();const T=((q=(J=k.lastResponse)==null?void 0:J.summary)==null?void 0:q.placed)??0,A=k.savedAt?new Date(k.savedAt).toLocaleString("es-CO",{hour:"2-digit",minute:"2-digit",day:"2-digit",month:"short"}):"";T>0?C.textContent=`Sesión previa restaurada (${A}) — ${T} archivo(s) ya estaban clasificados.`:C.textContent=`Sesión previa restaurada (${A}).`}async function v(k){const P=k.filter(T=>ua(T.filename,T.relativePath));if(P.length===0){C.textContent="Ningún archivo elegible en el drop.";return}_.queued=P,_.lastResponse=null,_.analyzing=!0,g(),m(),C.textContent=`Enviando ${P.length} archivo(s) al intake…`;try{const T=await t(P);_.lastResponse=T,_.analyzing=!1,g(),m(),C.textContent=`Intake ok — placed ${T.summary.placed} / deduped ${T.summary.deduped} / rejected ${T.summary.rejected}.`,c()}catch(T){_.lastResponse=null,_.analyzing=!1,m();const A=T instanceof Error?T.message:"intake falló";C.textContent=`Intake falló: ${A}`}}return d.addEventListener("dragenter",k=>{k.preventDefault(),d.classList.add("lia-intake-drop-zone__zone--active")}),d.addEventListener("dragover",k=>{k.preventDefault(),d.classList.add("lia-intake-drop-zone__zone--active")}),d.addEventListener("dragleave",k=>{k.preventDefault(),d.classList.remove("lia-intake-drop-zone__zone--active")}),d.addEventListener("drop",k=>{k.preventDefault(),d.classList.remove("lia-intake-drop-zone__zone--active");const P=k.dataTransfer;P&&(async()=>{const T=await ma(P);await v(T)})()}),E.addEventListener("click",()=>{var P;if(E.disabled)return;const k=(P=_.lastResponse)==null?void 0:P.batch_id;k&&n&&n(k)}),w.addEventListener("click",()=>{var B;if(_.queued.length===0&&_.lastResponse==null)return;let k,P;if(_.analyzing)k="¿Borrar mientras procesamos?",P="Estamos procesando tus archivos. ¿Estás seguro que quieres borrar todo? El servidor seguirá procesando los archivos que ya recibió; esto solo limpia la vista local.";else if(_.lastResponse!=null){const J=((B=_.lastResponse.summary)==null?void 0:B.placed)??0;k="¿Borrar la vista del batch?",P=`Ya procesamos ${J} archivo(s) y están en knowledge_base/. ¿Borrar esta lista de la vista? Los archivos NO se eliminan del corpus — solo se limpia la vista.`}else k="¿Borrar archivos en cola?",P=`¿Borrar los ${_.queued.length} archivo(s) en cola antes de enviarlos?`;(a??(async()=>Promise.resolve(window.confirm(`${k}

${P}`))))({title:k,message:P,confirmLabel:"Borrar todo",cancelLabel:"Cancelar"}).then(J=>{J&&u()})}),g(),m(),y(),s}function wn(e){const{status:t,ariaLabel:n,className:a=""}=e,s=document.createElement("span"),o=["lia-progress-dot",`lia-progress-dot--${t}`,t==="running"?"lia-progress-dot--pulse":"",a].filter(Boolean);return s.className=o.join(" "),s.setAttribute("data-lia-component","progress-dot"),s.setAttribute("role","status"),s.setAttribute("data-status",t),n&&s.setAttribute("aria-label",n),s}const ba=["docs","chunks","edges","embeddings_generated"];function ha(e){if(!e)return"";const t=[];for(const n of ba)if(e[n]!=null&&t.push(`${n}: ${e[n]}`),t.length>=3)break;return t.join(", ")}function Yt(e){if(e==null)return null;if(typeof e=="number")return Number.isFinite(e)?e:null;const t=Date.parse(e);return Number.isFinite(t)?t:null}function _a(e,t){const n=Yt(e),a=Yt(t);if(n==null||a==null||a<n)return"";const s=Math.round((a-n)/1e3);if(s<60)return`${s}s`;const o=Math.floor(s/60),i=s%60;return i?`${o}m ${i}s`:`${o}m`}function Zt(e){const{name:t,label:n,status:a,counts:s,startedAt:o,finishedAt:i,errorMessage:l,className:d=""}=e,r=document.createElement("div");r.className=["lia-stage-progress-item",`lia-stage-progress-item--${a}`,d].filter(Boolean).join(" "),r.setAttribute("data-lia-component","stage-progress-item"),r.setAttribute("data-stage-name",t),r.appendChild(wn({status:a,ariaLabel:n}));const b=document.createElement("span");b.className="lia-stage-progress-item__label",b.textContent=n,r.appendChild(b);const C=ha(s);if(C){const w=document.createElement("span");w.className="lia-stage-progress-item__counts",w.textContent=C,r.appendChild(w)}const f=_a(o,i);if(f){const w=document.createElement("span");w.className="lia-stage-progress-item__duration",w.textContent=f,r.appendChild(w)}if(a==="failed"&&l){const w=document.createElement("p");w.className="lia-stage-progress-item__error",w.textContent=l,w.setAttribute("role","alert"),r.appendChild(w)}return r}const Qt=[{name:"coerce",label:"Coerce"},{name:"audit",label:"Audit"},{name:"chunk",label:"Chunk"},{name:"sink",label:"Sink"},{name:"falkor",label:"FalkorDB"},{name:"embeddings",label:"Embeddings"}];function va(e){return e==="running"||e==="done"||e==="failed"||e==="pending"?e:"pending"}function en(e,t,n){return{name:e,label:t,status:va(n==null?void 0:n.status),counts:(n==null?void 0:n.counts)??null,startedAt:(n==null?void 0:n.started_at)??null,finishedAt:(n==null?void 0:n.finished_at)??null,errorMessage:(n==null?void 0:n.error)??null}}function ya(){const e=document.createElement("section");e.className="lia-run-progress-timeline",e.setAttribute("data-lia-component","run-progress-timeline");const t=document.createElement("header");t.className="lia-run-progress-timeline__header";const n=document.createElement("h3");n.className="lia-run-progress-timeline__title",n.textContent="Progreso de la corrida",t.appendChild(n),e.appendChild(t);const a=document.createElement("div");a.className="lia-run-progress-timeline__list";const s=new Map;Qt.forEach(({name:i,label:l})=>{const d=document.createElement("div");d.className="lia-run-progress-timeline__item",d.setAttribute("data-stage",i),d.appendChild(Zt(en(i,l,void 0))),a.appendChild(d),s.set(i,d)}),e.appendChild(a);function o(i){const l=(i==null?void 0:i.stages)||{};Qt.forEach(({name:d,label:r})=>{const b=s.get(d);if(!b)return;const C=l[d]||void 0;b.replaceChildren(Zt(en(d,r,C)))})}return{element:e,update:o}}function ka(e={}){const{initialLines:t=[],autoScroll:n=!0,onCopy:a=null,summaryLabel:s="Log de ejecución",className:o=""}=e,i=document.createElement("div");i.className=["lia-log-tail-viewer",o].filter(Boolean).join(" "),i.setAttribute("data-lia-component","log-tail-viewer");const l=document.createElement("div");l.className="lia-log-tail-viewer__toolbar";const d=document.createElement("button");d.type="button",d.className="lia-log-tail-viewer__copy",d.textContent="Copiar",d.setAttribute("aria-label","Copiar log"),l.appendChild(d);const r=document.createElement("details");r.className="lia-log-tail-viewer__details",r.open=!0;const b=document.createElement("summary");b.className="lia-log-tail-viewer__summary",b.textContent=s,r.appendChild(b);const C=document.createElement("pre");C.className="lia-log-tail-viewer__body",C.textContent=t.join(`
`),r.appendChild(C),i.appendChild(l),i.appendChild(r);const f={lines:[...t]},w=()=>{n&&(C.scrollTop=C.scrollHeight)},E=()=>{C.textContent=f.lines.join(`
`),w()},p=g=>{!g||g.length===0||(f.lines.push(...g),E())},_=()=>{f.lines=[],C.textContent=""};return d.addEventListener("click",()=>{var u;const g=f.lines.join(`
`),m=(u=globalThis.navigator)==null?void 0:u.clipboard;m&&typeof m.writeText=="function"&&m.writeText(g),a&&a()}),n&&w(),{element:i,appendLines:p,clear:_}}function wa(e={}){const{initialLines:t=[],onCopy:n=null,summaryLabel:a="Log de ejecución"}=e,s=document.createElement("section");s.className="lia-run-log-console",s.setAttribute("data-lia-component","run-log-console");const o=document.createElement("header");o.className="lia-run-log-console__header";const i=document.createElement("h3");i.className="lia-run-log-console__title",i.textContent="Log en vivo",o.appendChild(i);const l=document.createElement("p");l.className="lia-run-log-console__subtitle",l.textContent="Streaming del archivo artifacts/jobs/<job>.log — se actualiza cada 1.5s.",o.appendChild(l),s.appendChild(o);const d=ka({initialLines:t,autoScroll:!0,onCopy:n,summaryLabel:a,className:"lia-run-log-console__viewer"});return s.appendChild(d.element),{element:s,appendLines:d.appendLines,clear:d.clear}}function $a(e,t){const n=document.createElement("div");n.className="lia-adelta-modal__backdrop",n.setAttribute("role","dialog"),n.setAttribute("aria-modal","true"),n.setAttribute("aria-label","Confirmar aplicación del delta");const a=document.createElement("div");a.className="lia-adelta-modal";const s=document.createElement("h3");s.className="lia-adelta-modal__title",s.textContent="Confirmar aplicación";const o=document.createElement("p");o.className="lia-adelta-modal__body";const i=e.counts??{added:0,modified:0,removed:0};o.textContent=`Aplicar delta ${e.deltaId??"(pendiente)"} con +${i.added} / ~${i.modified} / -${i.removed} cambios. Esto afecta producción.`;const l=document.createElement("div");l.className="lia-adelta-modal__actions";const d=Ze({label:"Cancelar",tone:"ghost",onClick:()=>n.remove()}),r=Ze({label:"Aplicar delta",tone:"primary",onClick:()=>{n.remove(),t()}});return l.append(d,r),a.append(s,o,l),n.appendChild(a),n}function Ca(e,t){const n=document.createElement("div");n.className="lia-adelta-actions",n.setAttribute("data-lia-component","additive-delta-actions");const a=Ze({label:"Previsualizar",tone:"secondary",onClick:()=>t.onPreview()}),s=Ze({label:"Aplicar",tone:"primary",disabled:!0}),o=Ze({label:"Cancelar",tone:"destructive",onClick:()=>t.onCancel()}),i=Ze({label:"Nuevo delta",tone:"ghost",onClick:()=>t.onReset()});s.addEventListener("click",()=>{const r=l;r.state==="previewed"&&document.body.appendChild($a(r,()=>{s.disabled=!0,s.classList.add("is-pending"),t.onApply()}))}),n.append(a,s,o,i);let l=e;function d(r){l=r;const{state:b}=r;a.disabled=b==="running"||b==="pending",s.disabled=b!=="previewed",s.classList.toggle("is-pending",b==="pending"),o.hidden=b!=="running"&&b!=="pending",i.hidden=b!=="terminal"}return d(e),{element:n,update:d}}const $t=3;function Sa(e){const t=document.createElement("article");t.className=`lia-adelta-bucket lia-adelta-bucket--${e.tone}`,t.setAttribute("data-lia-component","additive-delta-bucket"),t.setAttribute("data-bucket",e.key);const n=document.createElement("header");n.className="lia-adelta-bucket__header";const a=document.createElement("h4");a.className="lia-adelta-bucket__title",a.textContent=e.title;const s=document.createElement("span");s.className="lia-adelta-bucket__count",s.textContent=String(e.count),n.append(a,s);const o=document.createElement("p");o.className="lia-adelta-bucket__body",o.textContent=e.description;const i=document.createElement("div");i.className="lia-adelta-bucket__chips";const l=e.samples.slice(0,$t);for(const d of l)i.appendChild(Qe({label:d.label,tone:e.tone}));return e.samples.length>$t&&i.appendChild(Qe({label:`+${e.samples.length-$t} más`,tone:"neutral"})),t.append(n,o,i),t}function Ea(e){var o,i,l;const t=document.createElement("section");if(t.className="lia-adelta-banner",t.setAttribute("data-lia-component","additive-delta-banner"),t.setAttribute("aria-label","Resumen del delta aditivo"),e.isEmpty){const d=document.createElement("div");d.className="lia-adelta-banner__empty";const r=document.createElement("h3");r.className="lia-adelta-banner__empty-title",r.textContent="Sin cambios detectados";const b=document.createElement("p");b.className="lia-adelta-banner__empty-body",b.textContent="La base ya coincide con el corpus en disco. No hay nada que aplicar.",d.append(r,b),t.appendChild(d)}else{const d=[{key:"added",title:"Agregados",tone:"success",count:e.counts.added,samples:((o=e.samples)==null?void 0:o.added)??[],description:"Documentos nuevos que entrarán al corpus."},{key:"modified",title:"Modificados",tone:"warning",count:e.counts.modified,samples:((i=e.samples)==null?void 0:i.modified)??[],description:"Documentos con cambios de contenido o clasificación."},{key:"removed",title:"Faltan en disco (no se retiran)",tone:"warning",count:e.counts.removed,samples:((l=e.samples)==null?void 0:l.removed)??[],description:"Estos archivos están en la base publicada pero no en disco. Por seguridad, este flujo NO los retira de Supabase + Falkor. Si genuinamente querés retirarlos, hacelo por CLI explícito: `lia-graph-artifacts --additive --allow-retirements`."},{key:"unchanged",title:"Sin cambios",tone:"neutral",count:e.counts.unchanged,samples:[],description:"Documentos que no requieren re-procesamiento."}],r=document.createElement("div");r.className="lia-adelta-banner__grid";for(const b of d)r.appendChild(Sa(b));t.appendChild(r)}const n=document.createElement("footer");n.className="lia-adelta-banner__footer";const a=document.createElement("code");a.className="lia-adelta-banner__delta-id",a.textContent=`delta_id=${e.deltaId}`;const s=document.createElement("code");return s.className="lia-adelta-banner__baseline",s.textContent=`baseline=${e.baselineGenerationId}`,n.append(a,s),t.appendChild(n),t}function Na(e){const t=document.createElement("section");t.className="lia-adelta-feeler",t.setAttribute("data-lia-component","additive-delta-activity-feeler"),t.setAttribute("aria-live","polite");const n=document.createElement("header");n.className="lia-adelta-feeler__header";const a=document.createElement("span");a.className="lia-adelta-feeler__spinner",a.appendChild(yn({size:"md",ariaLabel:"Procesando"}));const s=document.createElement("div");s.className="lia-adelta-feeler__title-wrap";const o=document.createElement("h3");o.className="lia-adelta-feeler__title",o.textContent=e.title;const i=document.createElement("code");i.className="lia-adelta-feeler__run-id",i.hidden=!0;const l=document.createElement("span");l.className="lia-adelta-feeler__elapsed",l.textContent="00:00",s.append(o,i,l),n.append(a,s),t.appendChild(n);const d=document.createElement("p");d.className="lia-adelta-feeler__body",d.textContent=e.body,t.appendChild(d);const r=document.createElement("p");r.className="lia-adelta-feeler__live",r.hidden=!0,t.appendChild(r);const b=document.createElement("p");b.className="lia-adelta-feeler__hint",b.textContent="Puedes cambiar de pestaña — el trabajo sigue corriendo en el servidor.",t.appendChild(b);const C=Date.now();function f(){const p=Math.max(0,Math.floor((Date.now()-C)/1e3)),_=String(Math.floor(p/60)).padStart(2,"0"),g=String(p%60).padStart(2,"0");l.textContent=`${_}:${g}`}f();const w=setInterval(f,1e3);function E(p){const _=Math.max(0,Math.floor(p.classified??0)),g=p.classifierInputCount??null,m=p.prematchedCount??null;if(_<=0&&!p.lastFilename&&g==null){r.hidden=!0,r.textContent="";return}r.hidden=!1;const u=(p.lastFilename??"").split("/").pop()??"",c=g!=null?String(g):"~1.300",y=m!=null&&m>0?` — ${m} saltados por shortcut`:"";u?r.textContent=`Clasificados ${_} de ${c}${y} — último: ${u}`:r.textContent=`Clasificados ${_} de ${c}${y}`}return{element:t,setLiveProgress:E,destroy:()=>clearInterval(w)}}const nt=["queued","parsing","supabase","falkor","finalize"],tn={queued:"En cola",parsing:"Clasificando",supabase:"Supabase",falkor:"FalkorDB",finalize:"Finalizando",completed:"Completado",failed:"Falló",cancelled:"Cancelado"};function Pa(e,t){if(e==="failed"||e==="cancelled"){const s=nt.indexOf(e==="failed"||e==="cancelled"?"finalize":e);return nt.indexOf(t)<=s?"failed":"pending"}if(e==="completed")return"done";const n=nt.indexOf(e),a=nt.indexOf(t);return a<n?"done":a===n?"running":"pending"}function Aa(e){if(!e)return"sin heartbeat";const t=Date.parse(e);if(Number.isNaN(t))return"sin heartbeat";const n=Math.max(0,Math.floor((Date.now()-t)/1e3));if(n<5)return"hace un instante";if(n<60)return`hace ${n}s`;const a=Math.floor(n/60);return a<60?`hace ${a} min`:`hace ${Math.floor(a/60)} h`}function Ia(e){switch(e){case"connecting":return"Conectando…";case"connected":return"En vivo";case"reconnecting":return"Reconectando…";case"polling":return"Sondeando (fallback)";case"closed":return"Desconectado"}}function xa(e){const t=document.createElement("section");t.className="lia-adelta-progress",t.setAttribute("data-lia-component","additive-delta-progress"),t.setAttribute("aria-live","polite");const n=document.createElement("header");n.className="lia-adelta-progress__header";const a=document.createElement("div");a.className="lia-adelta-progress__title-wrap";const s=document.createElement("h3");s.className="lia-adelta-progress__title",s.textContent="Aplicando delta";const o=document.createElement("span");o.className="lia-adelta-progress__elapsed",o.textContent="iniciado hace 00:00",a.append(s,o);const i=document.createElement("code");i.className="lia-adelta-progress__job";const l=document.createElement("span");l.className="lia-adelta-progress__sse",n.append(a,i,l);const d=document.createElement("ol");d.className="lia-adelta-progress__stages";const r={queued:document.createElement("li"),parsing:document.createElement("li"),supabase:document.createElement("li"),falkor:document.createElement("li"),finalize:document.createElement("li"),completed:document.createElement("li"),failed:document.createElement("li"),cancelled:document.createElement("li")},b={};for(const v of nt){const k=r[v];k.className="lia-adelta-progress__stage";const P=wn({status:"pending",ariaLabel:tn[v]});b[v]=P;const T=document.createElement("span");T.className="lia-adelta-progress__stage-label",T.textContent=tn[v],k.append(P,T),d.appendChild(k)}const C=document.createElement("div");C.className="lia-adelta-progress__bar",C.setAttribute("role","progressbar"),C.setAttribute("aria-valuemin","0"),C.setAttribute("aria-valuemax","100");const f=document.createElement("div");f.className="lia-adelta-progress__bar-fill",C.appendChild(f);const w=document.createElement("p");w.className="lia-adelta-progress__live-activity",w.setAttribute("aria-live","polite"),w.hidden=!0;const E=document.createElement("footer");E.className="lia-adelta-progress__footer";const p=document.createElement("span");p.className="lia-adelta-progress__heartbeat";const _=document.createElement("span");_.className="lia-adelta-progress__cancel-note";const g=document.createElement("span");g.className="lia-adelta-progress__health-slot",g.hidden=!0,E.append(p,_,g),t.append(n,d,C,w,E);function m(v){i.textContent=v.jobId?`job_id=${v.jobId}`:"",l.textContent=Ia(v.sseStatus),l.dataset.status=v.sseStatus;for(const T of nt){const A=b[T];if(!A)continue;const B=Pa(v.stage,T);A.className=`lia-progress-dot lia-progress-dot--${B}`+(B==="running"?" lia-progress-dot--pulse":""),A.setAttribute("data-status",B)}const k=Math.max(0,Math.min(100,Math.round(v.progressPct)));f.style.width=`${k}%`,C.setAttribute("aria-valuenow",String(k)),p.textContent=`Último latido del servidor: ${Aa(v.lastHeartbeatAt)}`,_.textContent=v.cancelRequested?"Cancelación solicitada — finalizará en el próximo punto seguro.":"";const P=(v.liveActivity??"").trim();if(P?(w.hidden=!1,w.textContent=P):(w.hidden=!0,w.textContent=""),v.healthIssue){const T=v.healthIssue.kind==="stall"?"warning":"error",A=v.healthIssue.kind==="stall"?"⚠":"⛔",B=v.healthIssue.attemptsSinceLastSuccess,J=v.healthIssue.kind!=="stall"&&B>0?` (${B} intentos fallidos consecutivos)`:"",q=Qe({label:`${A} ${v.healthIssue.message}${J}`,tone:T,emphasis:"soft",dataComponent:"additive-delta-health-chip",className:"lia-adelta-progress__health-chip"});q.dataset.kind=v.healthIssue.kind,g.replaceChildren(q),g.hidden=!1}else g.replaceChildren(),g.hidden=!0}const u=Date.now();function c(){const v=Math.max(0,Math.floor((Date.now()-u)/1e3)),k=String(Math.floor(v/60)).padStart(2,"0"),P=String(v%60).padStart(2,"0");o.textContent=`iniciado hace ${k}:${P}`}c();const y=setInterval(c,1e3);return m(e),{element:t,update:m,destroy:()=>clearInterval(y)}}function La(e){var n,a;if(e.stage==="cancelled")return{variant:"navy",title:"Delta cancelado",icon:"✕"};if(e.stage==="failed")return{variant:"danger",title:"Delta falló",icon:"!"};const t=(((n=e.report)==null?void 0:n.new_chunks_count)??((a=e.report)==null?void 0:a.chunks_written)??0)>0;return{variant:t?"warning":"success",title:t?"Delta completado — pendiente embeddings":"Delta completado",icon:"✓"}}function Ta(e){const t=e.report??{},n=Number(t.documents_added??0),a=Number(t.documents_modified??0),s=Number(t.documents_retired??0);return`Se procesaron ${n} nuevos, ${a} modificados y ${s} retirados. Ediciones de chunks: +${t.chunks_written??0} / -${t.chunks_deleted??0}. Aristas: +${t.edges_written??0} / -${t.edges_deleted??0}.`}function Ra(e){return navigator.clipboard?navigator.clipboard.writeText(e).then(()=>!0).catch(()=>!1):Promise.resolve(!1)}function Ma(e){var l,d,r,b,C,f;const t=La(e),n=document.createElement("section");n.className=`lia-adelta-terminal lia-adelta-terminal--${t.variant}`,n.setAttribute("data-lia-component","additive-delta-terminal"),n.setAttribute("data-stage",e.stage),n.setAttribute("role","status"),n.setAttribute("aria-live","polite");const a=document.createElement("header");a.className="lia-adelta-terminal__header";const s=document.createElement("span");s.className="lia-adelta-terminal__icon",s.textContent=t.icon,s.setAttribute("aria-hidden","true");const o=document.createElement("h3");o.className="lia-adelta-terminal__title",o.textContent=t.title;const i=document.createElement("code");if(i.className="lia-adelta-terminal__delta-id",i.textContent=e.deltaId,a.append(s,o,i),n.appendChild(a),e.stage==="completed"){const w=document.createElement("p");w.className="lia-adelta-terminal__summary",w.textContent=Ta(e),n.appendChild(w);const E=Number(((l=e.classifierSummary)==null?void 0:l.degraded_n1_only)??0),p=Number(((d=e.classifierSummary)==null?void 0:d.classified_new_count)??0);if(E>0){const g=document.createElement("p");g.className="lia-adelta-terminal__degraded",g.setAttribute("data-degraded-count",String(E));const m=p>0?p:E;g.textContent=`${E} de ${m} documentos clasificados quedaron con requires_subtopic_review=true (verdicto N1 solamente). Causa típica: backpressure de TPM en Gemini o casos genuinamente ambiguos. Revisa esos doc_ids antes de dar el ingest por cerrado.`,n.appendChild(g)}if((((r=e.report)==null?void 0:r.new_chunks_count)??((b=e.report)==null?void 0:b.chunks_written)??0)>0){const g=document.createElement("div");g.className="lia-adelta-terminal__callout";const m=document.createElement("p");m.className="lia-adelta-terminal__callout-body";const u=((C=e.report)==null?void 0:C.new_chunks_count)??((f=e.report)==null?void 0:f.chunks_written)??0;m.textContent=`${u} chunks nuevos pendientes de embedding — la calidad de retrieval está degradada hasta que corras la actualización.`;const c=document.createElement("code");c.className="lia-adelta-terminal__cmd",c.textContent="make phase2-embed-backfill";const y=Ze({label:"Copiar comando",tone:"secondary",onClick:()=>{Ra("make phase2-embed-backfill").then(v=>{y.classList.toggle("is-copied",v),y.querySelector(".lia-btn__label").textContent=v?"Copiado ✓":"Copiar comando"})}});g.append(m,c,y),n.appendChild(g)}}else if(e.stage==="failed"){const w=document.createElement("p");w.className="lia-adelta-terminal__summary",w.textContent="La aplicación del delta se detuvo. La parity con Falkor puede estar desfasada; revisa los eventos antes de reintentar.";const E=document.createElement("pre");E.className="lia-adelta-terminal__error",E.textContent=`${e.errorClass??"unknown_error"}: ${e.errorMessage??"(sin mensaje)"}`,n.append(w,E)}else{const w=document.createElement("p");w.className="lia-adelta-terminal__summary",w.textContent="El operador canceló el delta en un punto seguro. Los cambios parciales no se revierten automáticamente; inspecciona el reporte antes de continuar.",n.appendChild(w)}return n}const Ct="additive-delta.jobId";function qa(e){const t=e===void 0?typeof localStorage<"u"?localStorage:null:e;return t?{get:()=>{try{const n=t.getItem(Ct);return n&&n.trim()?n.trim():null}catch{return null}},set:n=>{try{n&&n.trim()&&t.setItem(Ct,n.trim())}catch{}},clear:()=>{try{t.removeItem(Ct)}catch{}}}:{get:()=>null,set:()=>{},clear:()=>{}}}function Da(e){const{serverLiveJobId:t,localJobId:n,store:a}=e;return t?(n!==t&&a.set(t),t):n||null}const Fa=new Set(["completed","failed","cancelled"]);function Oa(e){try{const t=JSON.parse(e);if(!t||typeof t!="object")return null;const n=t,a=String(n.job_id??"");return a?{jobId:a,stage:String(n.stage??"queued"),progressPct:Number(n.progress_pct??0)||0,lastHeartbeatAt:n.last_heartbeat_at??null,cancelRequested:!!(n.cancel_requested??!1),reportJson:n.report_json??null,errorClass:n.error_class??null,errorMessage:n.error_message??null}:null}catch{return null}}function Ba(e,t,n={}){const a=n.maxReconnects??5,s=n.pollingIntervalMs??2e3,o=n.eventSourceFactory??(N=>new EventSource(N)),i=n.fetchImpl??fetch.bind(globalThis),l=n.consecutiveFailureThreshold??3,d=n.staleHeartbeatThresholdMs??6e4,r=n.nowMs??(()=>Date.now());function b(){if(typeof window>"u")return"";try{return(window.localStorage.getItem("lia_access_token")??"").trim()}catch{return""}}function C(){const N=`/api/ingest/additive/events?job_id=${encodeURIComponent(e)}`,$=b();return $?`${N}&token=${encodeURIComponent($)}`:N}const f=`/api/ingest/additive/status?job_id=${encodeURIComponent(e)}`;let w=0,E=!1,p=null,_=null,g=null,m=0,u=null,c=!1;function y(N){var $;($=t.onStatusChange)==null||$.call(t,N)}function v(N){var $;Fa.has(N.stage)&&(($=t.onTerminal)==null||$.call(t,N),j())}function k(N){const $=Oa(N);$&&(t.onSnapshot($),v($))}function P(N,$,z){var O;m+=1,!(m<l)&&(c=!0,(O=t.onHealthIssue)==null||O.call(t,{kind:N,attemptsSinceLastSuccess:m,lastSuccessAt:u,status:z,message:$}))}function T(N){var $,z;if(m=0,u=new Date(r()).toISOString(),N){const O=Date.parse(N);if(!Number.isNaN(O)){const M=r()-O;if(M>d){c=!0,($=t.onHealthIssue)==null||$.call(t,{kind:"stall",attemptsSinceLastSuccess:0,lastSuccessAt:u,staleHeartbeatMs:M,message:`El worker no escribe heartbeat hace ${Math.round(M/1e3)}s. El thread puede estar trabado o sin permisos contra Supabase.`});return}}}c&&(c=!1,(z=t.onHealthOk)==null||z.call(t))}function A(){if(y("polling"),_)return;const N=async()=>{if(!E)try{const $=typeof window<"u"?window.localStorage.getItem("lia_access_token"):null;if(!$||!$.trim()){P("auth_missing","No hay token de sesión en localStorage (`lia_access_token`). Recargá la página o re-loguéate antes de aplicar otro delta.");return}const z={Authorization:`Bearer ${$.trim()}`},O=await i(f,{headers:z});if(!O.ok){const K=O.status===401?"auth_missing":"http_error";P(K,K==="auth_missing"?"/status devolvió 401 — el token expiró. Re-loguéate.":`/status devolvió HTTP ${O.status}. El servidor o la base pueden estar caídos; verificá logs.`,O.status);return}const M=await O.json();if(!M||!M.job){P("http_error","El job desapareció de la base. Pudo haber sido recogido por `phase2-reap-stalled-jobs` o eliminado manualmente.",O.status);return}const I=M.job;T(I.last_heartbeat_at??null),k(JSON.stringify(I))}catch($){P("network_error",`Fetch a /status falló: ${$ instanceof Error?$.message:String($)}`)}};N(),_=setInterval(N,s)}function B(N,$){if(t.onProgressEvent)try{const z=JSON.parse($);if(!z||typeof z!="object")return;const O=z.payload&&typeof z.payload=="object"?z.payload:{},M=String(z.ts_utc??"");t.onProgressEvent({eventType:N,tsUtc:M,payload:O})}catch{}}function J(){if(!E){y(w===0?"connecting":"reconnecting");try{p=o(C())}catch{q();return}p.addEventListener("open",()=>{w=0,y("connected")}),p.addEventListener("snapshot",N=>{k(N.data)});for(const N of["ingest.delta.worker.stage","ingest.delta.worker.heartbeat","ingest.delta.worker.done","ingest.delta.worker.failed"])p.addEventListener(N,$=>{var O,M;const z=$.data;B(N,z),N==="ingest.delta.worker.done"?((O=t.onTerminal)==null||O.call(t,{jobId:e,stage:"completed",progressPct:100,lastHeartbeatAt:null,cancelRequested:!1,reportJson:null}),j()):N==="ingest.delta.worker.failed"&&((M=t.onTerminal)==null||M.call(t,{jobId:e,stage:"failed",progressPct:0,lastHeartbeatAt:null,cancelRequested:!1,reportJson:null}),j())});for(const N of["subtopic.ingest.classified","subtopic.graph.binding_built","subtopic.graph.bindings_summary","ingest.delta.classifier.summary","ingest.delta.parity.check.start","ingest.delta.parity.check.done","ingest.delta.parity.check.mismatch","ingest.delta.falkor.indexes_verified","ingest.delta.falkor.indexes_skipped","ingest.delta.shortcut.computed","ingest.delta.plan.computed"])p.addEventListener(N,$=>{B(N,$.data)});p.addEventListener("message",N=>{k(N.data)}),p.addEventListener("error",()=>{E||(p==null||p.close(),p=null,q())})}}function q(){if(E)return;if(w>=a){A();return}w+=1;const N=Math.min(3e4,500*2**(w-1));y("reconnecting"),g=setTimeout(()=>J(),N)}function j(){E||(E=!0,p&&(p.close(),p=null),_&&(clearInterval(_),_=null),g&&(clearTimeout(g),g=null),y("closed"))}return J(),{close:j}}const ja=["completed","failed","cancelled"];function nn(e){return ja.includes(e)}function za(e){const t=e.payload;switch(e.eventType){case"subtopic.ingest.classified":{const n=String(t.filename??t.relative_path??"").trim(),a=String(t.topic_key??"").trim();return n?a?`Clasificando: ${n} → ${a}`:`Clasificando: ${n}`:null}case"subtopic.graph.binding_built":return"Vinculando subtema → artículo";case"subtopic.graph.bindings_summary":{const n=Number(t.built??0),a=Number(t.total??n);return`Vínculos subtema/artículo: ${n}/${a}`}case"ingest.delta.parity.check.start":return"Verificando parity Supabase ↔ Falkor…";case"ingest.delta.parity.check.done":return!!(t.ok??!0)?"Parity Supabase ↔ Falkor: ✓ alineada":"Parity Supabase ↔ Falkor: desfasada (revisá warnings)";case"ingest.delta.parity.check.mismatch":return`Parity mismatch en ${String(t.field??"?")}`;case"ingest.delta.classifier.summary":{const n=Number(t.classified_new_count??0),a=Number(t.prematched_count??0),s=Number(t.degraded_n1_only??0),o=s>0?` · ${s} con review`:"";return`Classifier: ${n} re-clasificados, ${a} con shortcut${o}`}case"ingest.delta.shortcut.computed":{const n=Number(t.prematched_count??0),a=Number(t.classifier_input_count??0);return`Shortcut: ${n} skipped, ${a} pendientes de LLM`}case"ingest.delta.plan.computed":{const n=Number(t.added??0),a=Number(t.modified??0),s=Number(t.removed??0);return`Plan listo: +${n} / ~${a} / -${s}`}case"ingest.delta.falkor.indexes_verified":return"Falkor: índices verificados";case"ingest.delta.falkor.indexes_skipped":return"Falkor: índices saltados (best-effort, ver warnings)";case"ingest.delta.worker.stage":{const n=String(t.stage??"");return n?`Stage → ${n}`:null}case"ingest.delta.worker.heartbeat":return null;default:return null}}function Ha(e){var a,s,o;const t=((a=e.reportJson)==null?void 0:a.sink_result)??null,n=((s=e.reportJson)==null?void 0:s.classifier_summary)??null;return{stage:e.stage,deltaId:((o=e.reportJson)==null?void 0:o.delta_id)??e.jobId,report:t,classifierSummary:n,errorClass:e.errorClass,errorMessage:e.errorMessage}}function Ua(e){const t=e.target??"production";e.fetchImpl??fetch.bind(globalThis);const n=qa(e.storage),a=e.rootElement;a.classList.add("lia-adelta-panel"),a.setAttribute("data-lia-component","additive-delta-controller");const s=document.createElement("div");s.className="lia-adelta-panel__banner";const o=document.createElement("div");o.className="lia-adelta-panel__progress";const i=document.createElement("div");i.className="lia-adelta-panel__terminal";const l=Ca({state:"idle"},{onPreview:()=>void v(),onApply:()=>void k(),onCancel:()=>void P(),onReset:()=>c()});a.append(l.element,s,o,i);let d=null,r=null,b=null,C=null,f=null,w=null,E=null,p=!1,_=null;function g(){_&&(clearInterval(_),_=null),b&&(b.destroy(),b=null)}function m(M,I,K=!1){if(g(),b=Na({title:M,body:I}),s.replaceChildren(b.element),K){const h=async()=>{if(b)try{const S=await Ne("/api/ingest/additive/preview-progress");if(!(S!=null&&S.available))return;b.setLiveProgress({classified:S.classified_since_last_run_boundary??0,lastFilename:S.last_filename??null})}catch{}};h(),_=setInterval(h,3e3)}}function u(M,I){l.update({state:M,deltaId:(I==null?void 0:I.deltaId)??(d==null?void 0:d.delta_id),counts:(I==null?void 0:I.counts)??(d?{added:d.summary.added,modified:d.summary.modified,removed:d.summary.removed}:void 0)})}function c(){g(),w=null,E=null,p=!1,f=null,s.replaceChildren(),o.replaceChildren(),i.replaceChildren(),d=null,r&&(r.destroy(),r=null),C&&(C.close(),C=null),n.clear(),u("idle")}function y(M){var I;(I=e.onError)==null||I.call(e,M)}async function v(){var M,I,K;w="preview",u("pending"),m("Analizando delta…","Lia compara los archivos de knowledge_base/ contra la base ya publicada por content_hash. Solo re-clasifica los archivos genuinamente nuevos o editados — los demás reutilizan su fingerprint anterior. Rápido para deltas pequeños.",!0);try{const{response:h,data:S}=await ze("/api/ingest/additive/preview",{target:t});if(w!=="preview")return;if(!h.ok||!S){g(),w=null,y(`Preview falló (HTTP ${h.status}).`),u("idle");return}g(),w=null,d=S;const D={deltaId:S.delta_id,baselineGenerationId:S.baseline_generation_id,counts:{added:S.summary.added,modified:S.summary.modified,removed:S.summary.removed,unchanged:S.summary.unchanged},samples:{added:(((M=S.sample_chips)==null?void 0:M.added)??[]).map(F=>({label:F})),modified:(((I=S.sample_chips)==null?void 0:I.modified)??[]).map(F=>({label:F})),removed:(((K=S.sample_chips)==null?void 0:K.removed)??[]).map(F=>({label:F}))},isEmpty:!!S.summary.is_empty};s.replaceChildren(Ea(D)),o.replaceChildren(),i.replaceChildren(),u(S.summary.is_empty?"previewed-empty":"previewed")}catch(h){if(w!=="preview")return;g(),w=null,y(String(h)),u("idle")}}async function k(){if(!d||d.summary.is_empty){y("No hay delta listo para aplicar.");return}w="apply",u("pending"),m("Encolando delta…","Reservando un slot de procesamiento en el servidor y disparando el worker. Esto es rápido (segundos); el procesamiento real arranca inmediatamente después.");try{const{response:M,data:I}=await ze("/api/ingest/additive/apply",{target:t,delta_id:d.delta_id});if(w!=="apply")return;if(M.status===409){const h=I;y(`Ya hay un delta en curso (${h.blocking_job_id}). Reattacheando…`),w=null,A(h.blocking_job_id);return}if(!M.ok||!I){w=null,y(`Apply falló (HTTP ${M.status}).`),u("previewed");return}const K=I;n.set(K.job_id),w=null,A(K.job_id)}catch(M){if(w!=="apply")return;w=null,y(String(M)),u("previewed")}}async function P(){var I;if(p)return;p=!0;const M=T();if(w==="preview"){g(),w=null,p=!1,u("idle"),y("Cancelación en cliente. El clasificador puede seguir corriendo en el servidor — su resultado se descarta.");return}if(w==="apply"&&!M){g(),w=null,p=!1,u(d?"previewed":"idle"),y("Solicitud de apply cancelada antes de encolarse.");return}if(M){try{if(await ze(`/api/ingest/additive/cancel?job_id=${encodeURIComponent(M)}`,{}),r){const K=r.element;K.dataset.cancelRequested="true";const h=K.dataset.currentStage??"queued",S=parseInt(((I=K.querySelector(".lia-adelta-progress__bar-fill"))==null?void 0:I.style.width)||"0",10)||0;r.update({jobId:M,stage:h,progressPct:S,lastHeartbeatAt:K.dataset.heartbeat??null,sseStatus:"polling",cancelRequested:!0})}}catch(K){y(`La solicitud de cancelación no pudo enviarse (${String(K)}). Intenta de nuevo o usa Nuevo delta para reiniciar la vista sin tocar el worker.`)}finally{p=!1}return}p=!1,y("No hay operación en curso para cancelar.")}function T(){return E??n.get()}function A(M){g(),w=null,E=M,s.replaceChildren(),i.replaceChildren(),o.replaceChildren(),f={jobId:M,stage:"queued",progressPct:0,lastHeartbeatAt:null,sseStatus:"connecting",cancelRequested:!1},r=xa(f),o.replaceChildren(r.element),u("running",{deltaId:M,counts:void 0}),C&&C.close(),C=Ba(M,{onSnapshot:I=>J(I),onStatusChange:I=>B(I),onTerminal:I=>$(I),onHealthIssue:I=>q(I),onHealthOk:()=>j(),onProgressEvent:I=>N(I)},e.sseOptions??{})}function B(M){!r||!f||(f={...f,sseStatus:M},r.update(f))}function J(M){r&&(f={jobId:M.jobId,stage:M.stage,progressPct:M.progressPct,lastHeartbeatAt:M.lastHeartbeatAt??null,sseStatus:"connected",cancelRequested:M.cancelRequested,healthIssue:(f==null?void 0:f.healthIssue)??null,liveActivity:(f==null?void 0:f.liveActivity)??null},r.update(f))}function q(M){!r||!f||(f={...f,healthIssue:M},r.update(f))}function j(){!r||!f||(f={...f,healthIssue:null},r.update(f))}function N(M){if(!r||!f)return;const I=za(M);I&&(f={...f,liveActivity:I},r.update(f))}function $(M){if(!nn(M.stage))return;o.replaceChildren(),r&&(r.destroy(),r=null),E=null,p=!1,w=null,f=null;const I=Ha(M);i.replaceChildren(Ma(I)),n.clear(),u("terminal")}async function z(){u("idle");try{let M;try{M=await Ne(`/api/ingest/additive/live?target=${encodeURIComponent(t)}`)}catch{M={ok:!1,target:t,job_id:null,job:null}}const I=n.get(),K=Da({serverLiveJobId:M.job_id,localJobId:I,store:n});if(!K)return;if(M.job_id===K){A(K);return}let h;try{h=await Ne(`/api/ingest/additive/status?job_id=${encodeURIComponent(K)}`)}catch{n.clear();return}if(!h.job){n.clear();return}nn(h.job.stage)?$({jobId:h.job.job_id,stage:h.job.stage,progressPct:h.job.progress_pct,lastHeartbeatAt:h.job.last_heartbeat_at,cancelRequested:h.job.cancel_requested,reportJson:h.job.report_json,errorClass:h.job.error_class,errorMessage:h.job.error_message}):A(K)}catch{}}z();function O(){C&&C.close(),a.replaceChildren()}return{destroy:O}}function Wa(e){const t=document.createElement("div");t.className=["lia-segmented",e.className||""].filter(Boolean).join(" "),t.setAttribute("data-lia-component","segmented-control"),t.setAttribute("role","tablist"),e.ariaLabel&&t.setAttribute("aria-label",e.ariaLabel);let n=e.value;const a=[];for(const o of e.options){const i=document.createElement("button");i.type="button",i.className="lia-segmented__option",i.setAttribute("role","tab"),i.setAttribute("data-value",o.value),i.setAttribute("aria-pressed",o.value===n?"true":"false");const l=document.createElement("span");if(l.className="lia-segmented__label",l.textContent=o.label,i.appendChild(l),o.hint){const d=document.createElement("span");d.className="lia-segmented__hint",d.textContent=o.hint,i.appendChild(d)}i.addEventListener("click",()=>{n!==o.value&&(s(o.value),e.onChange(o.value))}),a.push(i),t.appendChild(i)}function s(o){n=o;for(const i of a){const l=i.getAttribute("data-value")||"";i.setAttribute("aria-pressed",l===n?"true":"false")}}return{element:t,setValue:s,value:()=>n}}async function sn(e,t){const{response:n,data:a}=await ze(e,t);if(!n.ok){let s=n.statusText;if(a&&typeof a=="object"){const o=a,i=typeof o.error=="string"?o.error:"",l=typeof o.details=="string"?o.details:"";i&&l?s=`${i} — ${l}`:i?s=i:l&&(s=l)}throw new st(s,n.status,a)}if(!a)throw new st("Empty response",n.status,null);return a}function Ja(e,t={}){const n=e.querySelector("[data-slot=corpus-health]"),a=e.querySelector("[data-slot=corpus-overview]"),s=e.querySelector("[data-slot=run-trigger]"),o=e.querySelector("[data-slot=generations-list]"),i=e.querySelector("[data-slot=intake-zone]"),l=e.querySelector("[data-slot=progress-timeline]"),d=e.querySelector("[data-slot=log-console]");if(!a||!s||!o)return e.textContent="Sesiones: missing render slots.",{refresh:async()=>{},destroy:()=>{}};const r={activeJobId:null,lastRunStatus:null,pollHandle:null,logCursor:0,lastBatchId:null,autoEmbed:!0,autoPromote:!1,supabaseTarget:"wip",suinScope:""};let b=null,C=null;function f(){s.replaceChildren(Us({activeJobId:r.activeJobId,lastRunStatus:r.lastRunStatus,disabled:r.activeJobId!==null,onTrigger:({suinScope:h,supabaseTarget:S,autoEmbed:D,autoPromote:F})=>{r.autoEmbed=D,r.autoPromote=F,r.supabaseTarget=S,r.suinScope=h,v({suinScope:h,supabaseTarget:S,autoEmbed:D,autoPromote:F,batchId:null})}}))}const w=t.i18n?h=>an(t.i18n).confirm({title:h.title,message:h.message,tone:"caution",confirmLabel:h.confirmLabel,cancelLabel:h.cancelLabel}):void 0;function E(){i&&i.replaceChildren(fa({onIntake:h=>c(h),onApprove:()=>p(),confirmDestructive:w}))}function p(){var S;const h=((S=e.querySelector("[data-slot=flow-toggle]"))==null?void 0:S.closest("section"))??e.querySelector("[data-slot=flow-toggle]")??null;h&&(h.scrollIntoView({behavior:"smooth",block:"start"}),h.classList.add("is-highlighted"),window.setTimeout(()=>h.classList.remove("is-highlighted"),2400))}function _(){l&&(b=ya(),l.replaceChildren(b.element))}function g(){d&&(C=wa(),d.replaceChildren(C.element))}async function m(){a.replaceChildren(q("overview"));try{const h=await Ne("/api/ingest/state"),S={documents:h.corpus.documents,chunks:h.corpus.chunks,graphNodes:h.graph.nodes,graphEdges:h.graph.edges,graphOk:h.graph.ok,auditScanned:h.audit.scanned,auditIncluded:h.audit.include_corpus,auditExcluded:h.audit.exclude_internal,auditPendingRevisions:h.audit.pending_revisions,activeGenerationId:h.corpus.active_generation_id,activatedAt:h.corpus.activated_at};a.replaceChildren(Ds(S))}catch(h){a.replaceChildren(j("No se pudo cargar el estado del corpus.",h))}}async function u(){o.replaceChildren(q("generations"));try{const S=((await Ne("/api/ingest/generations?limit=20")).generations||[]).map(D=>{const F=D.knowledge_class_counts||{},Q=Object.entries(F).sort((se,ae)=>ae[1]-se[1])[0];return{generationId:D.generation_id,status:D.is_active?"active":"superseded",generatedAt:D.generated_at,documents:Number(D.documents)||0,chunks:Number(D.chunks)||0,topClass:Q==null?void 0:Q[0],topClassCount:Q==null?void 0:Q[1]}});o.replaceChildren(Gt({rows:S}))}catch(h){o.replaceChildren(Gt({rows:[],errorMessage:`No se pudieron cargar las generaciones: ${N(h)}`}))}}async function c(h){const D={batch_id:null,files:await Promise.all(h.map(async Q=>{const se=await y(Q.file);return{filename:Q.filename,content_base64:se,relative_path:Q.relativePath||Q.filename}})),options:{mirror_to_dropbox:!1,dropbox_root:null}},F=await sn("/api/ingest/intake",D);return r.lastBatchId=F.batch_id,F}async function y(h){const S=globalThis;if(typeof S.FileReader=="function"){const D=await new Promise((Q,se)=>{const ae=new S.FileReader;ae.onerror=()=>se(ae.error||new Error("file read failed")),ae.onload=()=>Q(String(ae.result||"")),ae.readAsDataURL(h)}),F=D.indexOf(",");return F>=0?D.slice(F+1):""}if(typeof h.arrayBuffer=="function"){const D=await h.arrayBuffer();return J(D)}return""}async function v(h){r.lastRunStatus="queued",r.logCursor=0,C&&C.clear(),f();try{const S=await sn("/api/ingest/run",{suin_scope:h.suinScope,supabase_target:h.supabaseTarget,auto_embed:h.autoEmbed,auto_promote:h.autoPromote,batch_id:h.batchId});r.activeJobId=S.job_id,r.lastRunStatus="running",f(),k()}catch(S){r.lastRunStatus="failed",r.activeJobId=null,f(),$(`No se pudo iniciar la ingesta: ${N(S)}`)}}function k(){P();const h=l!==null||d!==null;r.pollHandle=window.setInterval(()=>{if(!r.activeJobId){P();return}h?(T(r.activeJobId),A(r.activeJobId)):B(r.activeJobId)},h?1500:4e3)}function P(){r.pollHandle!==null&&(window.clearInterval(r.pollHandle),r.pollHandle=null)}async function T(h){try{const S=await Ne(`/api/ingest/job/${h}/progress`);b&&b.update(S);const D=S.status;(D==="done"||D==="failed")&&(r.lastRunStatus=D==="done"?"active":"failed",r.activeJobId=null,f(),P(),D==="done"&&await Promise.all([m(),u()]))}catch{}}async function A(h){try{const S=await Ne(`/api/ingest/job/${h}/log/tail?cursor=${r.logCursor}&limit=200`);S.lines&&S.lines.length>0&&C&&C.appendLines(S.lines),typeof S.next_cursor=="number"&&(r.logCursor=S.next_cursor)}catch{}}async function B(h){var S;try{const F=(await Ne(`/api/jobs/${h}`)).job;if(!F)return;if(F.status==="completed"){const Q=(((S=F.result_payload)==null?void 0:S.exit_code)??1)===0;r.lastRunStatus=Q?"active":"failed",r.activeJobId=null,f(),P(),Q&&await Promise.all([m(),u()])}else F.status==="failed"&&(r.lastRunStatus="failed",r.activeJobId=null,f(),P())}catch{}}function J(h){const S=new Uint8Array(h),D=32768;let F="";for(let ae=0;ae<S.length;ae+=D){const we=S.subarray(ae,Math.min(S.length,ae+D));F+=String.fromCharCode.apply(null,Array.from(we))}const Q=globalThis;if(typeof Q.btoa=="function")return Q.btoa(F);const se=globalThis.Buffer;return se?se.from(F,"binary").toString("base64"):""}function q(h){const S=document.createElement("div");return S.className=`lia-ingest-skeleton lia-ingest-skeleton--${h}`,S.setAttribute("aria-hidden","true"),S.textContent="Cargando…",S}function j(h,S){const D=document.createElement("div");D.className="lia-ingest-error",D.setAttribute("role","alert");const F=document.createElement("strong");F.textContent=h,D.appendChild(F);const Q=document.createElement("p");return Q.className="lia-ingest-error__detail",Q.textContent=N(S),D.appendChild(Q),D}function N(h){return h instanceof Error?h.message:typeof h=="string"?h:"Error desconocido"}function $(h){const S=document.createElement("div");S.className="lia-ingest-toast",S.textContent=h,e.prepend(S),window.setTimeout(()=>S.remove(),4e3)}f(),E(),_(),g(),Promise.all([m(),u()]);const z=e.querySelector("[data-slot=flow-toggle]"),O=(z==null?void 0:z.closest("[data-active-flow]"))??null;if(z&&O){const h=Wa({ariaLabel:"Flujo de ingesta",value:"delta",options:[{value:"delta",label:"Delta aditivo",hint:"Rápido · solo lo que cambió"},{value:"full",label:"Ingesta completa",hint:"Lento · reconstruye todo"}],onChange:S=>{O.setAttribute("data-active-flow",S)}});z.replaceChildren(h.element)}let M=null;const I=e.querySelector("[data-slot=additive-delta]");if(I){const{element:h,mount:S}=Ks();I.replaceChildren(h),M=Ua({rootElement:S,target:"production",onError:D=>$(D)})}let K=null;return n&&(K=ea(),n.replaceChildren(K.element)),{async refresh(){await Promise.all([m(),u(),(K==null?void 0:K.refresh())??Promise.resolve()])},destroy(){P(),M&&(M.destroy(),M=null),K&&(K.destroy(),K=null)}}}function Ga(e,{i18n:t}){const n=e,a=n.querySelector("#lia-ingest-shell");let s=null;a&&(s=Ja(a,{i18n:t}),window.setInterval(()=>{s==null||s.refresh()},3e4));const o=a!==null,i=n.querySelector("#ops-tab-monitor"),l=n.querySelector("#ops-tab-ingestion"),d=n.querySelector("#ops-tab-control"),r=n.querySelector("#ops-tab-embeddings"),b=n.querySelector("#ops-tab-reindex"),C=n.querySelector("#ops-panel-monitor"),f=n.querySelector("#ops-panel-ingestion"),w=n.querySelector("#ops-panel-control"),E=n.querySelector("#ops-panel-embeddings"),p=n.querySelector("#ops-panel-reindex"),_=n.querySelector("#runs-body"),g=n.querySelector("#timeline"),m=n.querySelector("#timeline-meta"),u=n.querySelector("#cascade-note"),c=n.querySelector("#user-cascade"),y=n.querySelector("#user-cascade-summary"),v=n.querySelector("#technical-cascade"),k=n.querySelector("#technical-cascade-summary"),P=n.querySelector("#refresh-runs"),T=!!(_&&g&&m&&u&&c&&y&&v&&k&&P),A=o?null:ce(n,"#ingestion-flash"),B=_n();function J(Ke="",ut="success"){if(A){if(!Ke){A.hidden=!0,A.textContent="",A.removeAttribute("data-tone");return}A.hidden=!1,A.dataset.tone=ut,A.textContent=Ke}}const q=o?null:ce(n,"#ingestion-corpus"),j=o?null:ce(n,"#ingestion-batch-type"),N=o?null:ce(n,"#ingestion-dropzone"),$=o?null:ce(n,"#ingestion-file-input"),z=o?null:ce(n,"#ingestion-folder-input"),O=o?null:ce(n,"#ingestion-pending-files"),M=o?null:ce(n,"#ingestion-overview"),I=o?null:ce(n,"#ingestion-refresh"),K=o?null:ce(n,"#ingestion-create-session"),h=o?null:ce(n,"#ingestion-select-files"),S=o?null:ce(n,"#ingestion-select-folder"),D=o?null:ce(n,"#ingestion-upload-files"),F=o?null:ce(n,"#ingestion-upload-progress"),Q=o?null:ce(n,"#ingestion-process-session"),se=o?null:ce(n,"#ingestion-auto-process"),ae=o?null:ce(n,"#ingestion-validate-batch"),we=o?null:ce(n,"#ingestion-retry-session"),Pe=o?null:ce(n,"#ingestion-delete-session"),Se=o?null:ce(n,"#ingestion-session-meta"),X=o?null:ce(n,"#ingestion-sessions-list"),$e=o?null:ce(n,"#selected-session-meta"),me=o?null:ce(n,"#ingestion-last-error"),Ae=o?null:ce(n,"#ingestion-last-error-message"),qe=o?null:ce(n,"#ingestion-last-error-guidance"),De=o?null:ce(n,"#ingestion-last-error-next"),he=o?null:ce(n,"#ingestion-kanban"),Le=o?null:ce(n,"#ingestion-log-accordion"),Te=o?null:ce(n,"#ingestion-log-body"),ue=o?null:ce(n,"#ingestion-log-copy"),_e=o?null:ce(n,"#ingestion-auto-status"),R=n.querySelector("#ingestion-add-corpus-btn"),G=n.querySelector("#add-corpus-dialog"),ie=n.querySelector("#ingestion-bounce-log"),ne=n.querySelector("#ingestion-bounce-body"),ee=n.querySelector("#ingestion-bounce-copy");async function be(Ke){return Ke()}const re=T?fn({i18n:t,stateController:B,dom:{monitorTabBtn:i,ingestionTabBtn:l,controlTabBtn:d,embeddingsTabBtn:r,reindexTabBtn:b,monitorPanel:C,ingestionPanel:f,controlPanel:w,embeddingsPanel:E,reindexPanel:p,runsBody:_,timelineNode:g,timelineMeta:m,cascadeNote:u,userCascadeNode:c,userCascadeSummary:y,technicalCascadeNode:v,technicalCascadeSummary:k,refreshRunsBtn:P},withThinkingWheel:be,setFlash:J}):null,de=o?null:xs({i18n:t,stateController:B,dom:{ingestionCorpusSelect:q,ingestionBatchTypeSelect:j,ingestionDropzone:N,ingestionFileInput:$,ingestionFolderInput:z,ingestionSelectFilesBtn:h,ingestionSelectFolderBtn:S,ingestionUploadProgress:F,ingestionPendingFiles:O,ingestionOverview:M,ingestionRefreshBtn:I,ingestionCreateSessionBtn:K,ingestionUploadBtn:D,ingestionProcessBtn:Q,ingestionAutoProcessBtn:se,ingestionValidateBatchBtn:ae,ingestionRetryBtn:we,ingestionDeleteSessionBtn:Pe,ingestionSessionMeta:Se,ingestionSessionsList:X,selectedSessionMeta:$e,ingestionLastError:me,ingestionLastErrorMessage:Ae,ingestionLastErrorGuidance:qe,ingestionLastErrorNext:De,ingestionKanban:he,ingestionLogAccordion:Le,ingestionLogBody:Te,ingestionLogCopyBtn:ue,ingestionAutoStatus:_e,addCorpusBtn:R,addCorpusDialog:G,ingestionBounceLog:ie,ingestionBounceBody:ne,ingestionBounceCopy:ee},withThinkingWheel:be,setFlash:J}),Y=n.querySelector("#corpus-lifecycle"),te=Y?on({dom:{container:Y},setFlash:J}):null,Ce=n.querySelector("#embeddings-lifecycle"),Re=Ce?un({dom:{container:Ce},setFlash:J}):null,Ie=n.querySelector("#reindex-lifecycle"),Ge=Ie?bn({dom:{container:Ie},setFlash:J,navigateToEmbeddings:()=>{B.setActiveTab("embeddings"),re==null||re.renderTabs()}}):null;re==null||re.bindEvents(),de==null||de.bindEvents(),te==null||te.bindEvents(),Re==null||Re.bindEvents(),Ge==null||Ge.bindEvents(),re==null||re.renderTabs(),de==null||de.render(),hn({stateController:B,withThinkingWheel:be,setFlash:J,refreshRuns:(re==null?void 0:re.refreshRuns)??(async()=>{}),refreshIngestion:(de==null?void 0:de.refreshIngestion)??(async()=>{}),refreshCorpusLifecycle:te==null?void 0:te.refresh,refreshEmbeddings:Re==null?void 0:Re.refresh,refreshReindex:Ge==null?void 0:Ge.refresh})}function Ka(e,{i18n:t}){const n=e,a=n.querySelector("#runs-body"),s=n.querySelector("#timeline"),o=n.querySelector("#timeline-meta"),i=n.querySelector("#cascade-note"),l=n.querySelector("#user-cascade"),d=n.querySelector("#user-cascade-summary"),r=n.querySelector("#technical-cascade"),b=n.querySelector("#technical-cascade-summary"),C=n.querySelector("#refresh-runs");if(!a||!s||!o||!i||!l||!d||!r||!b||!C)return;const f=_n(),w=async _=>_(),E=()=>{},p=fn({i18n:t,stateController:f,dom:{monitorTabBtn:null,ingestionTabBtn:null,controlTabBtn:null,embeddingsTabBtn:null,reindexTabBtn:null,monitorPanel:null,ingestionPanel:null,controlPanel:null,embeddingsPanel:null,reindexPanel:null,runsBody:a,timelineNode:s,timelineMeta:o,cascadeNote:i,userCascadeNode:l,userCascadeSummary:d,technicalCascadeNode:r,technicalCascadeSummary:b,refreshRunsBtn:C},withThinkingWheel:w,setFlash:E});p.bindEvents(),p.renderTabs(),hn({stateController:f,withThinkingWheel:w,setFlash:E,refreshRuns:p.refreshRuns,refreshIngestion:async()=>{}})}const co=Object.freeze(Object.defineProperty({__proto__:null,mountBackstageApp:Ka,mountOpsApp:Ga},Symbol.toStringTag,{value:"Module"}));export{Ga as a,Fn as b,ro as c,lo as d,co as e,Ka as m,io as o,Mn as r,oo as s};
