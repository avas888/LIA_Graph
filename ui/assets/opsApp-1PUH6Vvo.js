import{q as re}from"./bootstrap-BApbUZ11.js";import{g as Ne,p as ze,A as st}from"./client-OE0sHIIg.js";import{p as qt}from"./colors-ps0hVFT8.js";import{g as bt}from"./index-DF3uq1vv.js";import{getToastController as sn}from"./toasts-Dx3CUztl.js";import{c as xn}from"./badge-UV61UhzD.js";import{c as nt}from"./chip-Bjq03GaS.js";import{c as Ze}from"./button-1yFzSXrY.js";function Ln(){return`
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
  `}function Tn(e){return`
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
  `}function Rn(e){return`
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
        ${Ln()}
      </div>

      <div id="ingestion-section-promocion" class="ingestion-section" role="tabpanel" hidden></div>

      <div id="ingestion-section-subtopics" class="ingestion-section" role="tabpanel" hidden></div>
    </div>
  `}function Mn(){return`
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
  `}function Dn(e){return`
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
      ${Tn()}
    </main>
  `}const Ya=Object.freeze(Object.defineProperty({__proto__:null,renderBackstageShell:Rn,renderIngestionShell:qn,renderOpsShell:Dn,renderPromocionShell:Mn},Symbol.toStringTag,{value:"Module"})),Bn=2e3;function J(e){return String(e??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#39;")}function ge(e){return(e??0).toLocaleString("es-CO")}function Fn(e){if(!e)return"-";try{return new Date(e).toLocaleDateString("es-CO",{day:"numeric",month:"short",hour:"2-digit",minute:"2-digit",timeZone:"America/Bogota"})}catch{return e}}function Mt(e){if(!e)return"-";const t=Date.parse(e);if(Number.isNaN(t))return e;const n=Math.max(0,Math.floor((Date.now()-t)/1e3));if(n<5)return"ahora";if(n<60)return`hace ${n}s`;const a=Math.floor(n/60),s=n%60;return a<60?`hace ${a}m ${s}s`:`hace ${Math.floor(a/60)}h ${a%60}m`}function je(e){return e?e.length>24?`${e.slice(0,15)}…${e.slice(-8)}`:e:"-"}function On(e){return e===void 0?'<span class="ops-dot ops-dot-unknown">●</span>':e?'<span class="ops-dot ops-dot-ok">●</span>':'<span class="ops-dot ops-dot-error">●</span>'}function Dt(e,t){if(!t.available)return`
      <div class="corpus-card corpus-card-unavailable">
        <h4 class="corpus-card-title">${J(e)}</h4>
        <p class="corpus-card-unavail">● no disponible</p>
        ${t.error?`<p class="ops-subcopy">${J(t.error)}</p>`:""}
      </div>`;const n=t.knowledge_class_counts??{};return`
    <div class="corpus-card">
      <h4 class="corpus-card-title">${J(e)}</h4>
      <div class="corpus-card-row"><span>Gen:</span> <code>${J(je(t.generation_id))}</code></div>
      <div class="corpus-card-row"><span>Documentos:</span> <strong>${ge(t.documents)}</strong></div>
      <div class="corpus-card-row"><span>Chunks:</span> <strong>${ge(t.chunks)}</strong></div>
      <div class="corpus-card-row"><span>Embeddings:</span> ${On(t.embeddings_complete)} ${t.embeddings_complete?"completos":"incompletos"}</div>
      <div class="corpus-card-sep"></div>
      <div class="corpus-card-row corpus-card-row-sm"><span>normative_base:</span> ${ge(n.normative_base)}</div>
      <div class="corpus-card-row corpus-card-row-sm"><span>interpretative:</span> ${ge(n.interpretative_guidance)}</div>
      <div class="corpus-card-row corpus-card-row-sm"><span>practica_erp:</span> ${ge(n.practica_erp)}</div>
      <div class="corpus-card-sep"></div>
      <div class="corpus-card-row corpus-card-row-sm"><span>${e==="PRODUCTION"?"Activado:":"Actualizado:"}</span> ${J(Fn(t.activated_at))}</div>
    </div>`}function Bt(e,t={}){const{onlyFailures:n=!1}=t,a=(e??[]).filter(s=>n?!s.ok:!0);return a.length===0?"":`
    <ul class="corpus-checks">
      ${a.map(s=>`
            <li class="corpus-check ${s.ok?"is-ok":"is-fail"}">
              <span class="corpus-check-dot"></span>
              <div>
                <strong>${J(s.label)}</strong>
                <span>${J(s.detail)}</span>
              </div>
            </li>`).join("")}
    </ul>`}function jn(e){const t=e??[];return t.length===0?"":`
    <ol class="corpus-stage-list">
      ${t.map(n=>`
            <li class="corpus-stage-item state-${J(n.state)}">
              <span class="corpus-stage-dot"></span>
              <span>${J(n.label)}</span>
            </li>`).join("")}
    </ol>`}function gt(e){const t=String(e||"").trim();return t?t.replaceAll("_"," "):"-"}function zn(e){return e?e.kind==="audit"?"Audit":e.kind==="rollback"?"Rollback":e.mode==="force_reset"?"Force reset":"Promote":"Promote"}function vt(e){const t=e==null?void 0:e.last_checkpoint;if(!(t!=null&&t.phase))return"-";const n=t.cursor??0,a=t.total??0,s=a>0?(n/a*100).toFixed(1):"0";return`${gt(t.phase)} · ${ge(n)} / ${ge(a)} (${s}%)`}function Ft(e){var a,s;const t=((a=e==null?void 0:e.last_checkpoint)==null?void 0:a.cursor)??(e==null?void 0:e.batch_cursor)??0,n=((s=e==null?void 0:e.last_checkpoint)==null?void 0:s.total)??0;return n<=0?0:Math.min(100,Math.max(0,t/n*100))}function Hn(e){if(!(e!=null&&e.heartbeat_at))return{label:"-",className:""};const t=Math.max(0,(Date.now()-Date.parse(e.heartbeat_at))/1e3);return t<15?{label:"Saludable",className:"hb-healthy"}:t<45?{label:"Lento",className:"hb-slow"}:{label:"Sin respuesta",className:"hb-stale"}}function Un(e,t){var n,a,s,o,i,c;if(e)switch(e.operation_state_code){case"orphaned_queue":return{severity:"red",title:"Orphaned before start",detail:"The request was queued, but the backend worker never started."};case"stalled_resumable":return{severity:"red",title:"Stalled",detail:(n=e.last_checkpoint)!=null&&n.phase?`Backend stalled after ${gt(e.last_checkpoint.phase)}. Resume is available.`:"Backend stalled, but a checkpoint is available to resume."};case"failed_resumable":return{severity:"red",title:"Resumable",detail:e.error||((s=(a=e.failures)==null?void 0:a[0])==null?void 0:s.message)||"The last run failed after writing a checkpoint. Resume is available."};case"completed":return{severity:"green",title:"Completed",detail:e.kind==="audit"?"WIP audit completed. Artifact written.":e.kind==="rollback"?"Rollback completed and verified.":"Promotion completed and verified."};case"running":return{severity:"yellow",title:"Running",detail:e.current_phase?`Backend phase: ${gt(e.current_phase)}.`:e.stage_label?`Stage: ${e.stage_label}.`:"The backend is processing the promotion."};default:return{severity:e.severity??"red",title:e.severity==="yellow"?"Running":"Failed",detail:e.error||((i=(o=e.failures)==null?void 0:o[0])==null?void 0:i.message)||"The operation ended with an error."}}return t!=null&&t.preflight_ready?{severity:"green",title:"Ready",detail:"WIP audit and promotion preflight are green."}:{severity:"red",title:"Blocked",detail:((c=t==null?void 0:t.preflight_reasons)==null?void 0:c[0])||"Production is not ready for a safe promotion."}}function Wn(e){return e?e.kind==="audit"?"WIP Health Audit":e.kind==="rollback"?"Rollback Production":e.mode==="force_reset"?"Force Reset + Promote Production":"Promote WIP to Production":"Promote WIP to Production"}function Ot(e,t){return!t||t.available===!1?`<tr><td>${J(e)}</td><td colspan="2" class="corpus-report-unavail">no disponible</td></tr>`:`
    <tr>
      <td>${J(e)}</td>
      <td><code>${J(je(t.generation_id))}</code></td>
      <td>${ge(t.documents)} docs · ${ge(t.chunks)} chunks</td>
    </tr>`}function jt(e,t){const n=new Set;for(const s of Object.keys((e==null?void 0:e.knowledge_class_counts)??{}))n.add(s);for(const s of Object.keys((t==null?void 0:t.knowledge_class_counts)??{}))n.add(s);return n.size===0?"":[...n].sort().map(s=>{const o=((e==null?void 0:e.knowledge_class_counts)??{})[s]??0,i=((t==null?void 0:t.knowledge_class_counts)??{})[s]??0,c=i-o,l=c>0?"is-positive":c<0?"is-negative":"",d=c>0?`+${ge(c)}`:c<0?ge(c):"—";return`
        <tr class="corpus-report-kc-row">
          <td>${J(s)}</td>
          <td>${ge(o)}</td>
          <td>${ge(i)}</td>
          <td class="corpus-report-delta ${l}">${d}</td>
        </tr>`}).join("")}function Gn(e,t){if(!e||!t)return"-";const n=Date.parse(e),a=Date.parse(t);if(Number.isNaN(n)||Number.isNaN(a))return"-";const s=Math.max(0,Math.floor((a-n)/1e3)),o=Math.floor(s/60),i=s%60;return o===0?`${i}s`:`${o}m ${i}s`}function Jn(e){const t=e==null?void 0:e.promotion_summary;if(!t)return"";const{before:n,after:a,delta:s,plan_result:o}=t,i=((s==null?void 0:s.documents)??0)>0?`+${ge(s==null?void 0:s.documents)}`:ge(s==null?void 0:s.documents),c=((s==null?void 0:s.chunks)??0)>0?`+${ge(s==null?void 0:s.chunks)}`:ge(s==null?void 0:s.chunks),l=((s==null?void 0:s.documents)??0)>0?"is-positive":((s==null?void 0:s.documents)??0)<0?"is-negative":"",d=((s==null?void 0:s.chunks)??0)>0?"is-positive":((s==null?void 0:s.chunks)??0)<0?"is-negative":"",g=n||a?`
      <table class="corpus-report-table">
        <thead>
          <tr><th></th><th>Generación</th><th>Documentos / Chunks</th></tr>
        </thead>
        <tbody>
          ${Ot("Antes",n)}
          ${Ot("Después",a)}
        </tbody>
        ${s?`
        <tfoot>
          <tr>
            <td>Delta</td>
            <td></td>
            <td>
              <span class="corpus-report-delta ${l}">${i} docs</span> ·
              <span class="corpus-report-delta ${d}">${c} chunks</span>
            </td>
          </tr>
        </tfoot>`:""}
      </table>
      ${jt(n,a)?`
      <table class="corpus-report-table corpus-report-table-kc">
        <thead><tr><th>Clase</th><th>Antes</th><th>Después</th><th>Delta</th></tr></thead>
        <tbody>${jt(n,a)}</tbody>
      </table>`:""}`:"",v=o?`
      <div class="corpus-report-grid">
        ${[{label:"Docs staged",key:"docs_staged"},{label:"Docs upserted",key:"docs_upserted"},{label:"Docs new",key:"docs_new"},{label:"Docs removed",key:"docs_removed"},{label:"Chunks new",key:"chunks_new"},{label:"Chunks changed",key:"chunks_changed"},{label:"Chunks removed",key:"chunks_removed"},{label:"Chunks unchanged",key:"chunks_unchanged"},{label:"Chunks embedded",key:"chunks_embedded"}].filter(S=>o[S.key]!==void 0&&o[S.key]!==null).map(S=>`
              <div class="corpus-report-stat">
                <span class="corpus-report-stat-value">${J(String(o[S.key]??"-"))}</span>
                <span class="corpus-report-stat-label">${J(S.label)}</span>
              </div>`).join("")}
      </div>`:"",k=Gn(e==null?void 0:e.started_at,e==null?void 0:e.completed_at);return`
    <div class="corpus-section corpus-report-section">
      <h4>Promotion Report</h4>
      ${g}
      ${v}
      ${k!=="-"?`<p class="corpus-report-duration">Duración: <strong>${J(k)}</strong></p>`:""}
    </div>`}function an({dom:e,setFlash:t}){let n=null,a=null,s=null,o="",i="",c=null,l=null,d=!1,g=!1,$=!1,v=!1,k=0,S=null,b=0;function C(B,j){a&&clearTimeout(a),t(B,j);const L=e.container.querySelector(".corpus-toast");L&&(L.hidden=!1,L.dataset.tone=j,L.textContent=B,L.classList.remove("corpus-toast-enter"),L.offsetWidth,L.classList.add("corpus-toast-enter")),a=setTimeout(()=>{const w=e.container.querySelector(".corpus-toast");w&&(w.hidden=!0)},6e3)}function f(B,j,L,w="promote"){return new Promise(M=>{l==null||l.remove();const D=document.createElement("div");D.className="corpus-confirm-overlay",l=D,D.innerHTML=`
        <div class="corpus-confirm-dialog">
          <h3 class="corpus-confirm-title">${J(B)}</h3>
          <div class="corpus-confirm-body">${j}</div>
          <div class="corpus-confirm-actions">
            <button class="corpus-btn corpus-btn-rollback" data-action="cancel">Cancelar</button>
            <button class="corpus-btn ${w==="rollback"?"corpus-btn-rollback":"corpus-btn-promote"}" data-action="confirm">${J(L)}</button>
          </div>
        </div>
      `,document.body.appendChild(D),requestAnimationFrame(()=>D.classList.add("is-visible"));function Z(y){l===D&&(l=null),D.classList.remove("is-visible"),setTimeout(()=>D.remove(),180),M(y)}D.addEventListener("click",y=>{const q=y.target.closest("[data-action]");q?Z(q.dataset.action==="confirm"):y.target===D&&Z(!1)})})}async function p(B,j,L,w){if(!o){o=L,I();try{const{response:M,data:D}=await ze(B,j);M.ok&&(D!=null&&D.job_id)?(c={tone:"success",message:`${w} Job ${je(D.job_id)}.`},C(`${w} Job ${je(D.job_id)}.`,"success")):(c={tone:"error",message:(D==null?void 0:D.error)||"No se pudo iniciar la operación."},C((D==null?void 0:D.error)||"No se pudo iniciar la operación.","error"))}catch(M){const D=M instanceof Error?M.message:String(M);c={tone:"error",message:D},C(D,"error")}finally{o="",await U()}}}async function u(){const B=n;if(!B||o||!await f("Promote WIP to Production",`<p>This path reuses the live WIP generation and promotes it incrementally into Production with persisted checkpoints.</p>
       <table class="corpus-confirm-table">
         <tr><td>Production current:</td><td><strong>${ge(B.production.documents)}</strong> docs · <strong>${ge(B.production.chunks)}</strong> chunks</td></tr>
         <tr><td>WIP source:</td><td><strong>${ge(B.wip.documents)}</strong> docs · <strong>${ge(B.wip.chunks)}</strong> chunks</td></tr>
         <tr><td>WIP generation:</td><td><code>${J(je(B.wip.generation_id))}</code></td></tr>
       </table>
       <label style="display:flex;align-items:center;gap:0.4rem;margin:0.75rem 0;font-size:0.85rem;cursor:pointer">
         <input type="checkbox" id="corpus-force-full-upsert" />
         Forzar upsert completo (sincronizar summaries + embeddings aunque chunk_text no haya cambiado)
       </label>
       <p class="corpus-confirm-note">The backend will keep a promotion plan, batch checkpoints, and a resumable cursor before activation.</p>`,"Promote now"))return;const L=document.querySelector("#corpus-force-full-upsert"),w=(L==null?void 0:L.checked)??!1;v=!1,k=0,S=null,b=0,await p("/api/ops/corpus/rebuild-from-wip",{mode:"promote",force_full_upsert:w},"promote",w?"Promotion started (force full upsert).":"Promotion started.")}async function r(){var L;const B=(n==null?void 0:n.current_operation)??(n==null?void 0:n.last_operation)??null;!(B!=null&&B.resume_job_id)||o||!await f("Resume from Checkpoint",`<p>The backend will reuse the persisted promotion plan and continue from the last completed checkpoint.</p>
       <table class="corpus-confirm-table">
         <tr><td>Job:</td><td><code>${J(je(B.resume_job_id))}</code></td></tr>
         <tr><td>Checkpoint:</td><td>${J(vt(B))}</td></tr>
         <tr><td>Target generation:</td><td><code>${J(je(B.target_generation_id))}</code></td></tr>
       </table>`,"Resume now")||(v=!0,k=((L=B.last_checkpoint)==null?void 0:L.cursor)??0,S=null,b=0,await p("/api/ops/corpus/rebuild-from-wip/resume",{job_id:B.resume_job_id},"resume","Resume started."))}async function m(){const B=n;!B||!B.rollback_generation_id||o||!await f("Rollback de Production",`<p>Se va a intentar reactivar una generación previa de production.</p>
       <table class="corpus-confirm-table">
         <tr><td>Production actual:</td><td><code>${J(je(B.production.generation_id))}</code></td></tr>
         <tr><td>Objetivo:</td><td><code>${J(je(B.rollback_generation_id))}</code></td></tr>
       </table>
       <p class="corpus-confirm-note">Solo se habilita si el backend detecta una generación previa todavía utilizable.</p>`,"Revertir ahora","rollback")||await p("/api/ops/corpus/rollback",{generation_id:B.rollback_generation_id},"rollback","Rollback started.")}async function _(){o||await p("/api/ops/corpus/wip-audit",{},"audit","WIP audit started.")}async function h(){o||!await f("Reiniciar promoción",`<p>Cancela cualquier job anterior y lanza una nueva promoción desde WIP a producción.</p>
       <label style="display:flex;align-items:center;gap:0.4rem;margin:0.75rem 0;font-size:0.85rem;cursor:default;opacity:0.55" title="Force upsert es obligatorio en reinicio">
         <input type="checkbox" checked disabled style="opacity:0.55" />
         Forzar upsert completo (sincronizar summaries + embeddings aunque chunk_text no haya cambiado)
       </label>
       <p class="corpus-confirm-note">Reiniciar siempre usa force upsert: todos los ~50K chunks se copian completos.</p>`,"Reiniciar ahora","rollback")||(v=!1,k=0,S=null,b=0,await p("/api/ops/corpus/rebuild-from-wip/restart",{},"restart","Restart submitted (force full upsert)."))}async function E(){if(!($||o||!await f("Sincronizar JSONL a WIP",`<p>Se va a sincronizar el índice JSONL local ya existente al Supabase WIP (Docker).</p>
       <p class="corpus-confirm-note">Esta operación no ejecuta reindex — solo sincroniza los documentos y chunks que ya existen en el JSONL local. Es segura e idempotente.</p>`,"Sincronizar ahora"))){$=!0,I();try{const{response:j,data:L}=await ze("/api/ops/corpus/sync-to-wip",{});j.ok&&(L!=null&&L.synced)?C(`WIP sincronizado: ${ge(L.documents)} docs, ${ge(L.chunks)} chunks.`,"success"):C((L==null?void 0:L.error)||"Error sincronizando a WIP.","error")}catch(j){const L=j instanceof Error?j.message:String(j);C(L||"Error sincronizando a WIP.","error")}finally{$=!1,await U()}}}async function x(){const B=(n==null?void 0:n.current_operation)??(n==null?void 0:n.last_operation)??null,j=String((B==null?void 0:B.log_tail)||"").trim();if(j)try{await navigator.clipboard.writeText(j),C("Log tail copied.","success")}catch(L){const w=L instanceof Error?L.message:"Could not copy log tail.";C(w||"Could not copy log tail.","error")}}function I(){var Ae,Ce,K,ke,pe,Pe,Me,De,he,Le,Te;const B=e.container.querySelector(".corpus-log-accordion");B&&(d=B.open);const j=e.container.querySelector(".corpus-checks-accordion");j&&(g=j.open);const L=n;if(!L){e.container.innerHTML=`<p class="ops-empty">${J(i||"Cargando estado del corpus…")}</p>`;return}const w=L.current_operation??L.last_operation??null,M=Un(w,L),D=!!(L.current_operation&&["queued","running"].includes(L.current_operation.status))||!!o,Z=D||!L.preflight_ready,y=!D&&!!(w&&w.resume_supported&&w.resume_job_id&&(w.operation_state_code==="stalled_resumable"||w.operation_state_code==="failed_resumable")),q=D||!L.rollback_available,N=L.delta.documents==="+0"&&L.delta.chunks==="+0"?"Sin delta pendiente":`${L.delta.documents} documentos · ${L.delta.chunks} chunks`,T=Bt(w==null?void 0:w.checks,{onlyFailures:!0}),H=Bt(w==null?void 0:w.checks),V=!!(L.current_operation&&["queued","running"].includes(L.current_operation.status)),oe=c&&!(L.current_operation&&["queued","running"].includes(L.current_operation.status))?`
          <div class="corpus-callout tone-${J(c.tone==="success"?"green":"red")}">
            <strong>${c.tone==="success"?"Request sent":"Request failed"}</strong>
            <span>${J(c.message)}</span>
          </div>`:"",le=(Ae=w==null?void 0:w.last_checkpoint)!=null&&Ae.phase?(()=>{const de=w.operation_state_code==="completed"?"green":w.operation_state_code==="failed_resumable"||w.operation_state_code==="stalled_resumable"?"red":"yellow",_e=Ft(w);return`
            <div class="corpus-callout tone-${J(de)}">
              <strong>Checkpoint</strong>
              <span>${J(vt(w))} · ${J(Mt(w.last_checkpoint.at||null))}</span>
              ${_e>0&&de!=="green"?`<div class="corpus-progress-bar corpus-progress-bar-sm"><div class="corpus-progress-fill" style="width:${_e.toFixed(1)}%"></div></div>`:""}
            </div>`})():"";e.container.innerHTML=`
      <div class="corpus-cards">
        ${Dt("WIP",L.wip)}
        ${Dt("PRODUCTION",L.production)}
      </div>
      <div class="corpus-delta">
        <span class="corpus-delta-label">${J(N)}</span>
      </div>
      <section class="corpus-operation-panel severity-${J(M.severity)}">
        <div class="corpus-operation-header">
          <div>
            <div class="corpus-status-chip tone-${J(M.severity)}${M.severity==="yellow"?" is-pulsing":""}">
              ${J(M.title)}
            </div>
            <h3 class="corpus-operation-title">${J(Wn(w))}</h3>
            <p class="corpus-operation-detail">${J(M.detail)}</p>
          </div>
          <dl class="corpus-operation-meta">
            <div><dt>Heartbeat</dt><dd>${J(Mt((w==null?void 0:w.heartbeat_at)||(w==null?void 0:w.updated_at)||null))}</dd></div>
            <div><dt>Backend</dt><dd>${J(zn(w))}${w!=null&&w.force_full_upsert?` <span style="background:${qt.amber[100]};color:${qt.amber[600]};padding:0.1rem 0.4rem;border-radius:0.3rem;font-size:0.7rem;font-weight:700">FORCE UPSERT</span>`:""}</dd></div>
            <div><dt>Phase</dt><dd>${J(w!=null&&w.current_phase?gt(w.current_phase):(w==null?void 0:w.stage_label)||(L.preflight_ready?"Ready":"Blocked"))}</dd></div>
            <div><dt>Checkpoint</dt><dd>${J(vt(w))}</dd></div>
            <div><dt>WIP</dt><dd><code>${J(je((w==null?void 0:w.source_generation_id)||L.wip.generation_id))}</code></dd></div>
            <div><dt>Target</dt><dd><code>${J(je((w==null?void 0:w.target_generation_id)||(w==null?void 0:w.production_generation_id)||L.production.generation_id))}</code></dd></div>
            <div><dt>Prod</dt><dd><code>${J(je((w==null?void 0:w.production_generation_id)||L.production.generation_id))}</code></dd></div>
          </dl>
        </div>
        ${V?(()=>{var fe,ae;const de=Ft(w),_e=((fe=w==null?void 0:w.last_checkpoint)==null?void 0:fe.cursor)??(w==null?void 0:w.batch_cursor)??0,R=((ae=w==null?void 0:w.last_checkpoint)==null?void 0:ae.total)??0,W=Hn(w);if(_e>0&&R>0){const ce=Date.now();if(S&&_e>S.cursor){const X=Math.max(1,(ce-S.ts)/1e3),ee=(_e-S.cursor)/X;b=b>0?b*.7+ee*.3:ee}S={cursor:_e,ts:ce}}const se=b>0?`${b.toFixed(0)} chunks/s`:"",te=R-_e,Q=b>0&&te>0?(()=>{const ce=Math.ceil(te/b),X=Math.floor(ce/60),ee=ce%60;return X>0?`~${X}m ${ee}s restante`:`~${ee}s restante`})():"";return`
            <div class="corpus-progress-bar"><div class="corpus-progress-fill" style="width:${de.toFixed(1)}%"></div></div>
            <div class="corpus-progress-detail">
              ${v?`<span class="corpus-resume-badge">REANUDADO desde ${ge(k)}</span>`:""}
              <span class="corpus-progress-nums">${ge(_e)} / ${ge(R)} (${de.toFixed(1)}%)</span>
              ${se?`<span class="corpus-progress-rate">${J(se)}</span>`:""}
              ${Q?`<span class="corpus-progress-eta">${J(Q)}</span>`:""}
              <span class="corpus-hb-badge ${W.className}">${J(W.label)}</span>
            </div>`})():""}
        ${(Ce=w==null?void 0:w.stages)!=null&&Ce.length?jn(w.stages):""}
        ${le}
        ${(K=L.preflight_reasons)!=null&&K.length&&!V&&!L.preflight_ready?`
          <div class="corpus-callout tone-red">
            <strong>Preflight blocked</strong>
            <ul>${L.preflight_reasons.map(de=>`<li>${J(de)}</li>`).join("")}</ul>
          </div>`:""}
        ${oe}
        ${T?`<div class="corpus-section"><h4>Visible failures</h4>${T}</div>`:""}
        ${H?`
          <details class="corpus-section corpus-checks-accordion">
            <summary class="corpus-checks-summary"><h4>Checks</h4><span class="corpus-checks-count">${((w==null?void 0:w.checks)??[]).length}</span></summary>
            ${H}
          </details>`:""}
        ${Jn(w)}
        ${w!=null&&w.log_tail?`
          <details class="corpus-section corpus-log-accordion">
            <summary class="corpus-log-summary">
              <h4>Backend log tail</h4>
              <button id="corpus-copy-log-tail-btn" type="button" class="corpus-btn corpus-btn-rollback corpus-btn-inline">Copy</button>
            </summary>
            <pre class="corpus-log-tail">${J(w.log_tail)}</pre>
          </details>`:""}
        ${i?`
          <div class="corpus-callout tone-red">
            <strong>Refresh error</strong>
            <span>${J(i)}</span>
          </div>`:""}
      </section>
      <div class="corpus-actions">
        ${L.audit_missing&&!D?`
          <button id="corpus-audit-btn" class="corpus-btn corpus-btn-audit${o==="audit"?" is-busy":""}">
            ${o==="audit"?'<span class="corpus-spinner"></span> Auditing…':"Run WIP Audit"}
          </button>`:""}
        ${!D&&!$?`
          <button id="corpus-sync-wip-btn" class="corpus-btn corpus-btn-sync">Sincronizar JSONL a WIP</button>`:""}
        ${$?`
          <button class="corpus-btn corpus-btn-sync is-busy" disabled><span class="corpus-spinner"></span> Sincronizando…</button>`:""}
        <button id="corpus-promote-btn" class="corpus-btn corpus-btn-promote${o==="promote"?" is-busy":""}" ${Z?"disabled":""}>
          ${o==="promote"?'<span class="corpus-spinner"></span> Starting…':"Promote WIP to Production"}
        </button>
        ${y?`
          <button id="corpus-resume-btn" class="corpus-btn corpus-btn-promote${o==="resume"?" is-busy":""}">
            ${o==="resume"?'<span class="corpus-spinner"></span> Resuming…':"Resume from Checkpoint"}
          </button>`:""}
        <button id="corpus-rollback-btn" class="corpus-btn corpus-btn-rollback${o==="rollback"?" is-busy":""}" ${q?"disabled":""}>
          ${o==="rollback"?'<span class="corpus-spinner"></span> Starting rollback…':"Rollback"}
        </button>
        <button id="corpus-restart-btn" class="corpus-btn corpus-btn-rollback${o==="restart"?" is-busy":""}" ${D?"disabled":""}>
          ${o==="restart"?'<span class="corpus-spinner"></span> Restarting…':"Reiniciar promoción (force upsert)"}
        </button>
      </div>
      ${L.preflight_ready?"":`
        <p class="corpus-action-note">${J(((ke=L.preflight_reasons)==null?void 0:ke[0])||"Promotion is blocked by preflight.")}</p>`}
      ${L.rollback_available?"":`
        <p class="corpus-action-note">${J(L.rollback_reason||"Rollback is not available yet.")}</p>`}
      <div class="corpus-toast ops-flash" hidden></div>
    `,(pe=e.container.querySelector("#corpus-audit-btn"))==null||pe.addEventListener("click",_),(Pe=e.container.querySelector("#corpus-sync-wip-btn"))==null||Pe.addEventListener("click",()=>void E()),(Me=e.container.querySelector("#corpus-promote-btn"))==null||Me.addEventListener("click",u),(De=e.container.querySelector("#corpus-resume-btn"))==null||De.addEventListener("click",r),(he=e.container.querySelector("#corpus-rollback-btn"))==null||he.addEventListener("click",m),(Le=e.container.querySelector("#corpus-restart-btn"))==null||Le.addEventListener("click",h),(Te=e.container.querySelector("#corpus-copy-log-tail-btn"))==null||Te.addEventListener("click",de=>{de.preventDefault(),de.stopPropagation(),x()});const be=e.container.querySelector(".corpus-log-accordion");be&&d&&(be.open=!0);const Ee=e.container.querySelector(".corpus-checks-accordion");Ee&&g&&(Ee.open=!0)}async function U(){try{n=await Ne("/api/ops/corpus-status"),i="",n!=null&&n.current_operation&&["queued","running","completed","failed","cancelled"].includes(n.current_operation.status)&&(c=null)}catch(B){i=B instanceof Error?B.message:String(B),n===null&&(n=null)}I()}function G(){I(),s===null&&(s=window.setInterval(()=>{U()},Bn))}return{bindEvents:G,refresh:U}}const Za=Object.freeze(Object.defineProperty({__proto__:null,createCorpusLifecycleController:an},Symbol.toStringTag,{value:"Module"})),Vn={normative_base:"Normativa",interpretative_guidance:"Interpretación",practica_erp:"Práctica"},It={declaracion_renta:"Renta",iva:"IVA",laboral:"Laboral",facturacion_electronica:"Facturación",estados_financieros_niif:"NIIF",ica:"ICA",calendario_obligaciones:"Calendarios",retencion_fuente:"Retención",regimen_sancionatorio:"Sanciones",regimen_cambiario:"Régimen Cambiario",impuesto_al_patrimonio:"Patrimonio",informacion_exogena:"Exógena",proteccion_de_datos:"Datos",obligaciones_mercantiles:"Mercantil",obligaciones_profesionales_contador:"Obligaciones Contador",rut_responsabilidades:"RUT",gravamen_movimiento_financiero_4x1000:"GMF 4×1000",beneficiario_final:"Beneficiario Final",contratacion_estatal:"Contratación Estatal",reforma_pensional:"Reforma Pensional",zomac_incentivos:"ZOMAC"},on="lia_backstage_ops_active_tab",St="lia_backstage_ops_ingestion_session_id";function Kn(){const e=bt();try{const t=String(e.getItem(on)||"").trim();return t==="ingestion"||t==="control"||t==="embeddings"||t==="reindex"?t:"monitor"}catch{return"monitor"}}function Xn(e){const t=bt();try{t.setItem(on,e)}catch{}}function Yn(){const e=bt();try{return String(e.getItem(St)||"").trim()}catch{return""}}function Zn(e){const t=bt();try{if(!e){t.removeItem(St);return}t.setItem(St,e)}catch{}}function ht(e){return e==="processing"||e==="running_batch_gates"}function rn(e){if(!e)return!1;const t=String(e.status||"").toLowerCase();if(t==="done"||t==="completed")return!0;const n=e.documents||[];return n.length===0?!1:n.every(a=>{const s=String(a.status||"").toLowerCase();return s==="done"||s==="completed"||s==="skipped_duplicate"||s==="bounced"})}function ct(e){const t=String(e||"").trim().toLowerCase();return t==="failed"||t==="error"?"error":t==="processing"||t==="running_batch_gates"||t==="needs_retry_batch_gate"||t==="queued"||t==="uploading"||t==="extracting"||t==="etl"||t==="writing"||t==="gates"||t==="in_progress"||t==="partial_failed"||t==="raw"||t==="pending_dedup"?"warn":"ok"}function we(e){return e instanceof st?e.message||`HTTP ${e.status}`:e instanceof Error?e.message:String(e||"unknown_error")}function Qn(e,t){switch(String(e||"").trim()){case"normative_base":return t.t("ops.ingestion.batchType.normative");case"interpretative_guidance":return t.t("ops.ingestion.batchType.interpretative");case"practica_erp":return t.t("ops.ingestion.batchType.practical");default:return String(e||"-")}}function es(e,t){const n=Number(e||0);return!Number.isFinite(n)||n<=0?"0 B":n>=1024*1024?`${t.formatNumber(n/(1024*1024),{maximumFractionDigits:1})} MB`:n>=1024?`${t.formatNumber(n/1024,{maximumFractionDigits:1})} KB`:`${t.formatNumber(n)} B`}function zt(e,t){const n=e||{total:0,queued:0,done:0,failed:0,pending_batch_gate:0,bounced:0},a=[`${t.t("ops.ingestion.summary.total")} ${n.total||0}`,`${t.t("ops.ingestion.summary.done")} ${n.done||0}`,`${t.t("ops.ingestion.summary.failed")} ${n.failed||0}`,`${t.t("ops.ingestion.summary.queued")} ${n.queued||0}`,`${t.t("ops.ingestion.summary.gate")} ${n.pending_batch_gate||0}`],s=Number(n.bounced||0);return s>0&&a.push(`Rebotados ${s}`),a.join(" · ")}function Et(e,t,n){const a=e||t||"";if(!a)return"stalled";const s=Date.parse(a);if(Number.isNaN(s))return"stalled";const o=Date.now()-s,i=n==="gates",c=i?9e4:3e4,l=i?3e5:12e4;return o<c?"alive":o<l?"slow":"stalled"}function ts(e,t){const n=e||t||"";if(!n)return"-";const a=Date.parse(n);if(Number.isNaN(a))return"-";const s=Math.max(0,Date.now()-a),o=Math.floor(s/1e3);if(o<5)return"ahora";if(o<60)return`hace ${o}s`;const i=Math.floor(o/60),c=o%60;return i<60?`hace ${i}m ${c}s`:`hace ${Math.floor(i/60)}h ${i%60}m`}const yt={validating:"validando corpus",manifest:"activando manifest",indexing:"reconstruyendo índice","indexing/scanning":"escaneando documentos","indexing/chunking":"generando chunks","indexing/writing_indexes":"escribiendo índices","indexing/syncing":"sincronizando Supabase","indexing/auditing":"auditando calidad"};function ln(e){if(!e)return"";if(yt[e])return yt[e];const t=e.indexOf(":");if(t>0){const n=e.slice(0,t),a=e.slice(t+1),s=yt[n];if(s)return`${s} (${a})`}return e}function ns(e){if(!e)return"";const t=Date.parse(e);if(Number.isNaN(t))return"";try{return new Intl.DateTimeFormat("es-CO",{timeZone:"America/Bogota",day:"2-digit",month:"2-digit",year:"numeric",hour:"2-digit",minute:"2-digit",second:"2-digit",hour12:!1}).format(new Date(t))}catch{return""}}function cn(e,t){const n=Math.max(0,Math.min(100,Number(e||0))),a=document.createElement("div");a.className="ops-progress";const s=document.createElement("div");s.className="ops-progress-bar";const o=document.createElement("span");o.className="ops-progress-fill",t==="gates"&&n>0&&n<100&&o.classList.add("ops-progress-active"),o.style.width=`${n}%`;const i=document.createElement("span");return i.className="ops-progress-label",i.textContent=`${n}%`,s.appendChild(o),a.append(s,i),a}function We(e){return String(e??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#39;")}function Ke(e){return(e??0).toLocaleString("es-CO")}function Ht(e){if(e==null||e<=0)return"-";const t=Math.floor(e/60),n=Math.floor(e%60);return t>0?`${t}m ${n}s`:`${n}s`}function dn({dom:e,setFlash:t}){const{container:n}=e;let a=null,s="",o=!1,i=!1,c=0,l=0,d=3e3,g=[];function $(u){if(u<=0)return;const r=Date.now();if(u>c&&l>0){const m=r-l,_=u-c,h=m/_;g.push(h),g.length>10&&g.shift(),d=g.reduce((E,x)=>E+x,0)/g.length}u!==c&&(c=u,l=r)}function v(){if(l===0)return{level:"healthy",label:"Iniciando..."};const u=Date.now()-l,r=Math.max(d*3,1e4),m=Math.max(d*6,3e4);return u<r?{level:"healthy",label:"Saludable"}:u<m?{level:"caution",label:"Lento"}:{level:"failed",label:"Sin respuesta"}}function k(){var H,V,oe,le,be,Ee,Ae,Ce;const u=a;if(!u){n.innerHTML='<p class="ops-text-muted">Cargando estado de embeddings...</p>';return}const r=u.current_operation||u.last_operation,m=((H=u.current_operation)==null?void 0:H.status)??"",_=m==="running"||m==="queued"||s==="start",h=!u.current_operation&&!s,E=s==="stop",x=!_&&!E&&((r==null?void 0:r.status)==="cancelled"||(r==null?void 0:r.status)==="failed"||(r==null?void 0:r.status)==="stalled");let I="";const U=(r==null?void 0:r.status)??"",G=E?"Deteniendo...":_?"En ejecución":x?U==="stalled"?"Detenido (stalled)":U==="cancelled"?"Cancelado":"Fallido":h?"Inactivo":U||"—",B=_?"tone-yellow":U==="completed"?"tone-green":U==="failed"||U==="stalled"?"tone-red":U==="cancelled"?"tone-yellow":"",j=u.api_health,L=j!=null&&j.ok?"emb-api-ok":"emb-api-error",w=j?j.ok?`API OK (${j.detail})`:`API Error: ${j.detail}`:"API: verificando...";if(I+=`<div class="emb-status-row">
      <span class="corpus-status-chip ${B}">${We(G)}</span>
      <span class="emb-target-badge">WIP</span>
      <span class="emb-api-semaphore ${L}" title="${We(w)}"><span class="emb-api-dot"></span> ${We(j!=null&&j.ok?"API OK":j?"API Error":"...")}</span>
      ${_?(()=>{const K=v();return`<span class="emb-process-health emb-health-${K.level}"><span class="emb-health-dot"></span> ${We(K.label)}</span>`})():""}
    </div>`,I+='<div class="emb-controls">',h?(I+=`<label class="emb-force-label"><input type="checkbox" id="emb-force-check" ${o?"checked":""} /> Forzar re-embed (todas)</label>`,I+=`<button class="corpus-btn corpus-btn-promote" id="emb-start-btn" ${s?"disabled":""}>Iniciar</button>`):E?I+='<span class="emb-running-label">Deteniendo al finalizar batch actual...</span>':_&&r&&(I+='<button class="corpus-btn corpus-btn-rollback" id="emb-stop-btn">Detener</button>',I+='<span class="emb-running-label">Embebiendo chunks...</span>'),x&&r){const K=r.force,ke=(V=r.progress)==null?void 0:V.last_cursor_id,pe=(oe=r.progress)==null?void 0:oe.pct_complete,Pe=ke?`Reanudar desde ${typeof pe=="number"?pe.toFixed(1)+"%":"checkpoint"}`:"Reiniciar";K&&(I+='<span class="emb-force-label"><input type="checkbox" checked disabled /> Forzar re-embed (continuación)</span>'),I+=`<button class="corpus-btn corpus-btn-promote" id="emb-resume-btn" ${s?"disabled":""}>${We(Pe)}</button>`,I+=`<button class="corpus-btn" id="emb-start-btn" ${s?"disabled":""} style="opacity:0.7">Iniciar desde cero</button>`}I+="</div>";const M=r==null?void 0:r.progress,D=(_||s)&&(M==null?void 0:M.total),Z=D?M.total:u.total_chunks,y=D?M.embedded:u.embedded_chunks,q=D?M.pending-M.embedded-(M.failed||0):u.null_embedding_chunks,N=D&&M.failed||0,T=D?M.pct_complete:u.coverage_pct;if(I+=`<div class="emb-stats-grid">
      <div class="emb-stat"><span class="emb-stat-value">${Ke(Z)}</span><span class="emb-stat-label">Total</span></div>
      <div class="emb-stat"><span class="emb-stat-value">${Ke(y)}</span><span class="emb-stat-label">Embebidos</span></div>
      <div class="emb-stat"><span class="emb-stat-value">${Ke(Math.max(0,q))}</span><span class="emb-stat-label">Pendientes</span></div>
      ${N>0?`<div class="emb-stat emb-stat-error"><span class="emb-stat-value">${Ke(N)}</span><span class="emb-stat-label">Fallidos</span></div>`:`<div class="emb-stat"><span class="emb-stat-value">${T.toFixed(1)}%</span><span class="emb-stat-label">Cobertura</span></div>`}
    </div>`,_&&(r!=null&&r.progress)){const K=r.progress;I+='<div class="emb-live-progress">',I+='<div class="emb-progress-bar-wrap" id="emb-progress-mount"></div>',I+=`<div class="emb-rate-line">
        <span>${((le=K.rate_chunks_per_sec)==null?void 0:le.toFixed(1))??"-"} chunks/s</span>
        <span>ETA: ${Ht(K.eta_seconds)}</span>
        <span>Elapsed: ${Ht(K.elapsed_seconds)}</span>
        <span>Batch ${Ke(K.current_batch)} / ${Ke(K.total_batches)}</span>
      </div>`,K.failed>0&&(I+=`<p class="emb-failed-notice">${Ke(K.failed)} chunks fallidos (${(K.failed/Math.max(K.pending,1)*100).toFixed(2)}%)</p>`),I+="</div>"}if(r!=null&&r.quality_report){const K=r.quality_report;I+='<div class="emb-quality-report">',I+="<h3>Reporte de calidad</h3>",I+=`<div class="emb-stats-grid">
        <div class="emb-stat"><span class="emb-stat-value">${((be=K.mean_cosine_similarity)==null?void 0:be.toFixed(4))??"-"}</span><span class="emb-stat-label">Coseno medio</span></div>
        <div class="emb-stat"><span class="emb-stat-value">${((Ee=K.min_cosine_similarity)==null?void 0:Ee.toFixed(4))??"-"}</span><span class="emb-stat-label">Min</span></div>
        <div class="emb-stat"><span class="emb-stat-value">${((Ae=K.max_cosine_similarity)==null?void 0:Ae.toFixed(4))??"-"}</span><span class="emb-stat-label">Max</span></div>
        <div class="emb-stat"><span class="emb-stat-value">${Ke(K.sample_pairs)}</span><span class="emb-stat-label">Pares</span></div>
      </div>`,K.collapsed_warning&&(I+='<p class="emb-anomaly-warning">ANOMALIA: Embeddings colapsados (mean &gt; 0.95)</p>'),K.noise_warning&&(I+='<p class="emb-anomaly-warning">ANOMALIA: Embeddings ruidosos (mean &lt; 0.10)</p>'),!K.collapsed_warning&&!K.noise_warning&&(I+='<p class="emb-quality-ok">Distribución saludable</p>'),I+="</div>"}if((Ce=r==null?void 0:r.checks)!=null&&Ce.length){I+='<div class="emb-checks">';for(const K of r.checks){const ke=K.ok?'<span class="ops-dot ops-dot-ok">●</span>':'<span class="ops-dot ops-dot-error">●</span>';I+=`<div class="emb-check">${ke} <strong>${We(K.label)}</strong>: ${We(K.detail)}</div>`}I+="</div>"}if(r!=null&&r.log_tail){const K=r.log_tail.split(`
`).reverse().join(`
`);I+=`<details class="emb-log-accordion" id="emb-log-details" ${i?"open":""}><summary>Log</summary><pre class="emb-log-tail">${We(K)}</pre></details>`}if(r!=null&&r.error&&(I+=`<p class="emb-error">${We(r.error)}</p>`),n.innerHTML=I,_&&(r!=null&&r.progress)){const K=n.querySelector("#emb-progress-mount");K&&K.appendChild(cn(r.progress.pct_complete??0,"embedding"))}}function S(){n.addEventListener("click",u=>{const r=u.target;r.id==="emb-start-btn"&&b(),r.id==="emb-stop-btn"&&C(),r.id==="emb-resume-btn"&&f()}),n.addEventListener("change",u=>{const r=u.target;r.id==="emb-force-check"&&(o=r.checked)}),n.addEventListener("toggle",u=>{const r=u.target;r.id==="emb-log-details"&&(i=r.open)},!0)}async function b(){const u=o;s="start",o=!1,k();try{const{response:r,data:m}=await ze("/api/ops/embedding/start",{force:u});!r.ok||!(m!=null&&m.ok)?(t((m==null?void 0:m.error)||`Error ${r.status}`,"error"),s=""):t("Embedding iniciado","success")}catch(r){t(String(r),"error"),s=""}await p()}async function C(){var r;const u=(r=a==null?void 0:a.current_operation)==null?void 0:r.job_id;if(u){s="stop",k();try{await ze("/api/ops/embedding/stop",{job_id:u}),t("Stop solicitado — se detendrá al finalizar el batch actual","success")}catch(m){t(String(m),"error"),s=""}}}async function f(){const u=(a==null?void 0:a.current_operation)||(a==null?void 0:a.last_operation);if(u!=null&&u.job_id){s="start",k();try{const{response:r,data:m}=await ze("/api/ops/embedding/resume",{job_id:u.job_id});!r.ok||!(m!=null&&m.ok)?(t((m==null?void 0:m.error)||`Error ${r.status}`,"error"),s=""):t("Embedding reanudado desde checkpoint","success")}catch(r){t(String(r),"error"),s=""}s="",await p()}}async function p(){try{const u=await Ne("/api/ops/embedding-status");a=u;const r=u.current_operation;if(r!=null&&r.progress){const m=r.progress.current_batch;typeof m=="number"&&$(m)}s==="stop"&&!u.current_operation&&(s=""),s==="start"&&u.current_operation&&(s=""),u.current_operation||(c=0,l=0,g=[])}catch{}k()}return{bindEvents:S,refresh:p}}const Qa=Object.freeze(Object.defineProperty({__proto__:null,createOpsEmbeddingsController:dn},Symbol.toStringTag,{value:"Module"})),ss=["pending","processing","done"],as={pending:"Pendiente",processing:"En proceso",done:"Procesado"},os={pending:"⏳",processing:"🔄",done:"✅"},is=5;function un(e){const t=String(e||"").toLowerCase();return t==="done"||t==="completed"||t==="skipped_duplicate"||t==="bounced"?"done":t==="in_progress"||t==="processing"||t==="extracting"||t==="etl"||t==="writing"||t==="gates"||t==="uploading"||t==="running_batch_gates"||t==="needs_retry_batch_gate"||t==="failed"||t==="error"||t==="partial_failed"?"processing":"pending"}function rs(e,t){const n=e.detected_topic||t.corpus||"",a=mn[n]||It[n]||n||"",s=e.detected_type||e.batch_type||"",o=Vn[s]||s||"",i=s==="normative_base"?"normative":s==="interpretative_guidance"?"interpretative":s==="practica_erp"?"practica":"unknown";let c="";return a&&(c+=`<span class="kanban-pill kanban-pill--topic" title="Tema: ${ye(n)}">${xe(a)}</span>`),o&&(c+=`<span class="kanban-pill kanban-pill--type-${i}" title="Tipo: ${ye(s)}">${xe(o)}</span>`),!a&&!o&&(c+='<span class="kanban-pill kanban-pill--unclassified">Sin clasificar</span>'),c}function ls(e,t,n){var _;const a=ct(e.status),s=un(e.status),o=es(e.bytes,n),i=Number(e.progress||0),c=new Set(t.gate_pending_doc_ids||[]),l=s==="done"&&c.has(e.doc_id);let d;e.status==="bounced"?d='<span class="meta-chip status-bounced">↩ Ya existe en el corpus</span>':s==="done"&&e.derived_from_doc_id&&(e.delta_section_count||0)>0?d=`<span class="meta-chip status-ok">△ ${e.delta_section_count} secciones nuevas</span>`:s==="done"&&(e.status==="done"||e.status==="completed")?(d='<span class="meta-chip status-ok">✓ Documento listo</span>',l&&(d+='<span class="meta-chip status-gate-pending">Pendiente validación final</span>')):d=`<span class="meta-chip status-${a}">${xe(e.status)}</span>`;const g=rs(e,t);let $="";if(e.status==="in_progress"||e.status==="processing"){const h=Et(e.heartbeat_at,e.updated_at,e.stage),E=ts(e.heartbeat_at,e.updated_at);$=`<div class="kanban-liveness ops-liveness-${h}">${E}</div>`}let v="";e.stage==="gates"&&t.gate_sub_stage&&(v=`<div class="kanban-gate-sub">${ln(t.gate_sub_stage)}</div>`);let k="";s==="processing"&&i>0&&(k=`<div class="kanban-progress" data-progress="${i}"></div>`);let S="";(_=e.error)!=null&&_.message&&(S=`<div class="kanban-error">${xe(e.error.message)}</div>`);let b="";e.duplicate_of?b=`<div class="kanban-duplicate">Duplicado de: ${xe(e.duplicate_of)}</div>`:e.derived_from_doc_id&&(b=`<div class="kanban-duplicate">Derivado de: ${xe(e.derived_from_doc_id)}</div>`);let C="";if(s==="done"){const h=ns(e.updated_at);h&&(C=`<div class="kanban-completed-at">Completado: ${xe(h)}</div>`)}let f="";e.duplicate_of&&s!=="done"&&e.status!=="bounced"?f=gs(e):s==="pending"&&(e.status==="raw"||e.status==="needs_classification")&&ds(e)?f=us(e,n):s==="pending"&&(e.status==="raw"||e.status==="needs_classification")?f=cs(e,n,t):s==="processing"&&(e.status==="failed"||e.status==="error"||e.status==="partial_failed")&&(f=fs(e));let p="",u="";(s!=="pending"||e.status==="queued")&&(p=ps(),u=ms(e,t,n));const m=e.stage&&e.stage!==e.status&&s==="processing";return`
    <div class="kanban-card kanban-card--${a}" data-doc-id="${ye(e.doc_id)}">
      <div class="kanban-card-head">
        <span class="kanban-card-title" title="${ye(e.doc_id)}">${xe(e.filename||e.doc_id)}</span>
        ${d}
      </div>
      ${e.source_relative_path?`<div class="kanban-card-relpath" title="${ye(e.source_relative_path)}">${xe(hs(e.source_relative_path))}</div>`:""}
      <div class="kanban-card-pills-row">
        ${g}
        <span class="kanban-card-size">${o}</span>
        ${p}
      </div>
      ${u}
      ${m?`<div class="kanban-card-stage">${xe(e.stage)}</div>`:""}
      ${$}
      ${v}
      ${k}
      ${C}
      ${b}
      ${S}
      ${f}
    </div>
  `}function cs(e,t,n){const a=e.detected_type||e.batch_type||"",s=e.detected_topic||(n==null?void 0:n.corpus)||"",o=i=>i===a?" selected":"";return`
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
  `}function ds(e){return!!(e.autogenerar_label&&(e.autogenerar_is_new||e.autogenerar_resolved_topic))}function us(e,t){const n=e.detected_type||e.batch_type||"",a=d=>d===n?" selected":"",s=`
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
    `;const o=e.autogenerar_resolved_topic||"",i=It[o]||o,c=e.autogenerar_synonym_confidence??0,l=Math.round(c*100);return`
    <div class="kanban-actions kanban-autogenerar-actions kanban-autogenerar--synonym">
      <div class="kanban-autogenerar-header">Tema sugerido: <strong>${xe(i)}</strong> <span class="kanban-autogenerar-conf">(${l}%)</span></div>
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
  `}function ps(){return'<button class="kanban-reclassify-toggle" type="button" title="Cambiar clasificación">✎</button>'}function ms(e,t,n){const a=e.detected_topic||t.corpus||"",s=e.detected_type||e.batch_type||"",o=(i,c)=>i===c?" selected":"";return`
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
  `}function gs(e){return`
    <div class="kanban-actions">
      <button class="btn btn--sm btn--primary" data-action="replace-dup" data-doc-id="${ye(e.doc_id)}">Reemplazar</button>
      <button class="btn btn--sm" data-action="add-new-dup" data-doc-id="${ye(e.doc_id)}">Agregar nuevo</button>
      <button class="btn btn--sm btn--danger" data-action="discard-dup" data-doc-id="${ye(e.doc_id)}">Descartar</button>
    </div>
  `}function fs(e){return`
    <div class="kanban-actions">
      <button class="btn btn--sm" data-action="retry" data-doc-id="${ye(e.doc_id)}">Reintentar</button>
      <button class="btn btn--sm btn--danger" data-action="discard" data-doc-id="${ye(e.doc_id)}">Descartar</button>
    </div>
  `}const pn=[["declaracion_renta","Renta"],["iva","IVA"],["laboral","Laboral"],["facturacion_electronica","Facturación"],["estados_financieros_niif","NIIF"],["ica","ICA"],["calendario_obligaciones","Calendarios"],["retencion_fuente","Retención"],["regimen_sancionatorio","Sanciones"],["regimen_cambiario","Régimen Cambiario"],["impuesto_al_patrimonio","Patrimonio"],["informacion_exogena","Exógena"],["proteccion_de_datos","Datos"],["obligaciones_mercantiles","Mercantil"],["obligaciones_profesionales_contador","Obligaciones Contador"],["rut_responsabilidades","RUT"],["gravamen_movimiento_financiero_4x1000","GMF 4×1000"],["beneficiario_final","Beneficiario Final"],["contratacion_estatal","Contratación Estatal"],["reforma_pensional","Reforma Pensional"],["zomac_incentivos","ZOMAC"]];function bs(e){const t=new Set,n=[];for(const[a,s]of pn)t.add(a),n.push([a,s]);for(const a of e)!a.key||t.has(a.key)||(t.add(a.key),n.push([a.key,a.label||a.key]));return n}let Nt=pn,mn={...It};function ft(e=""){let t='<option value="">Seleccionar...</option>';for(const[n,a]of Nt){const s=n===e?" selected":"";t+=`<option value="${ye(n)}"${s}>${xe(a)}</option>`}return t}function xe(e){const t=document.createElement("span");return t.textContent=e,t.innerHTML}function ye(e){return e.replace(/&/g,"&amp;").replace(/"/g,"&quot;").replace(/'/g,"&#39;").replace(/</g,"&lt;").replace(/>/g,"&gt;")}function hs(e){const t=e.replace(/\/[^/]+$/,"").split("/").filter(Boolean);return t.length<=2?t.join("/")+"/":"…/"+t.slice(-2).join("/")+"/"}function _s(e,t,n,a,s){s&&s.length>0&&(Nt=bs(s),mn=Object.fromEntries(Nt));const o=[...e.documents||[]].sort((f,p)=>Date.parse(String(p.updated_at||0))-Date.parse(String(f.updated_at||0))),i={pending:[],processing:[],done:[]};for(const f of o){const p=un(f.status);i[p].push(f)}i.pending.sort((f,p)=>{const u=f.status==="raw"||f.status==="needs_classification"?0:1,r=p.status==="raw"||p.status==="needs_classification"?0:1;return u!==r?u-r:Date.parse(String(p.updated_at||0))-Date.parse(String(f.updated_at||0))});const c=e.status==="running_batch_gates",l=e.gate_sub_stage||"";let d="";if(c){const f=l?ln(l):"Preparando...";d=`
      <div class="kanban-validation-banner kanban-validation-banner--running">
        <span class="kanban-validation-spinner"></span>
        <span>Validación final en curso — ${xe(f)}</span>
      </div>`}else e.status==="needs_retry_batch_gate"?d=`
      <div class="kanban-validation-banner kanban-validation-banner--error">
        <span>⚠ Validación final fallida — use Reintentar o Validar lote</span>
      </div>`:e.status==="completed"&&e.wip_sync_status==="skipped"&&(d=`
      <div class="kanban-validation-banner kanban-validation-banner--warn">
        <span>⚠ Ingesta completada solo localmente — WIP Supabase no estaba disponible. Use Operaciones → Sincronizar a WIP.</span>
      </div>`);let g="";const $=i.processing.length;for(const f of ss){const p=i[f],u=f==="processing"?`<span class="kanban-column-count">${$}</span><span class="kanban-column-limit">/ ${is}</span>`:`<span class="kanban-column-count">${p.length}</span>`,r=p.length===0?'<div class="kanban-column-empty">Sin documentos</div>':p.map(_=>ls(_,e,n)).join(""),m=f==="done"?d:"";g+=`
      <div class="kanban-column kanban-column--${f}">
        <div class="kanban-column-header">
          <span class="kanban-column-icon">${os[f]}</span>
          <span class="kanban-column-label">${as[f]}</span>
          ${u}
        </div>
        <div class="kanban-column-cards">
          ${m}
          ${r}
        </div>
      </div>
    `}const v={};t.querySelectorAll(".kanban-column").forEach(f=>{const p=f.classList[1]||"",u=f.querySelector(".kanban-column-cards");p&&u&&(v[p]=u.scrollTop)});const k=[];let S=t;for(;S;)S.scrollTop>0&&k.push([S,S.scrollTop]),S=S.parentElement;const b={};t.querySelectorAll(".kanban-reclassify-panel").forEach(f=>{var p,u;if(!f.hasAttribute("hidden")){const r=f.closest("[data-doc-id]"),m=(r==null?void 0:r.dataset.docId)||"";if(m&&!(a!=null&&a.has(m))){const _=((p=f.querySelector("[data-field='topic']"))==null?void 0:p.value)||"",h=((u=f.querySelector("[data-field='type']"))==null?void 0:u.value)||"";b[m]={topic:_,type:h}}}});const C={};t.querySelectorAll(".kanban-classify-actions").forEach(f=>{var r,m;const p=f.closest("[data-doc-id]"),u=(p==null?void 0:p.dataset.docId)||"";if(u){const _=((r=f.querySelector("[data-field='topic']"))==null?void 0:r.value)||"",h=((m=f.querySelector("[data-field='type']"))==null?void 0:m.value)||"";(_||h)&&(C[u]={topic:_,type:h})}}),t.innerHTML=g;for(const[f,p]of k)f.scrollTop=p;t.querySelectorAll(".kanban-column").forEach(f=>{const p=f.classList[1]||"",u=f.querySelector(".kanban-column-cards");p&&v[p]&&u&&(u.scrollTop=v[p])});for(const[f,p]of Object.entries(b)){const u=t.querySelector(`[data-doc-id="${CSS.escape(f)}"]`);if(!u)continue;const r=u.querySelector(".kanban-reclassify-toggle"),m=u.querySelector(".kanban-reclassify-panel");if(r&&m){m.removeAttribute("hidden"),r.textContent="✖";const _=m.querySelector("[data-field='topic']"),h=m.querySelector("[data-field='type']");_&&p.topic&&(_.value=p.topic),h&&p.type&&(h.value=p.type)}}for(const[f,p]of Object.entries(C)){const u=t.querySelector(`[data-doc-id="${CSS.escape(f)}"]`);if(!u)continue;const r=u.querySelector(".kanban-classify-actions");if(!r)continue;const m=r.querySelector("[data-field='topic']"),_=r.querySelector("[data-field='type']");m&&p.topic&&(m.value=p.topic),_&&p.type&&(_.value=p.type)}t.querySelectorAll(".kanban-progress").forEach(f=>{var m,_;const p=Number(f.dataset.progress||0),u=((_=(m=f.closest(".kanban-card"))==null?void 0:m.querySelector(".kanban-card-stage"))==null?void 0:_.textContent)||void 0,r=cn(p,u);f.replaceWith(r)}),t.querySelectorAll(".kanban-reclassify-toggle").forEach(f=>{f.addEventListener("click",()=>{const p=f.closest(".kanban-card"),u=p==null?void 0:p.querySelector(".kanban-reclassify-panel");if(!u)return;u.hasAttribute("hidden")?(u.removeAttribute("hidden"),f.textContent="✖"):(u.setAttribute("hidden",""),f.textContent="✎")})})}async function qe(e,t){const n=await fetch(e,t);let a=null;try{a=await n.json()}catch{a=null}if(!n.ok){const s=a&&typeof a=="object"&&"error"in a?String(a.error||n.statusText):n.statusText;throw new st(s,n.status,a)}return a}async function xt(e,t){const{response:n,data:a}=await ze(e,t);if(!n.ok){const s=a&&typeof a=="object"&&"error"in a?String(a.error||n.statusText):n.statusText;throw new st(s,n.status,a)}return a}const vs=new Set([".pdf",".md",".txt",".docx"]),ys=[".","__MACOSX"],At=3,wt="lia_folder_pending_";function lt(e){return e.filter(t=>{const n=t.name;if(ys.some(o=>n.startsWith(o)))return!1;const a=n.lastIndexOf("."),s=a>=0?n.slice(a).toLowerCase():"";return vs.has(s)})}function dt(e,t){return e.webkitRelativePath||t.get(e)||""}function Xe(e,t){const n=dt(e,t);return`${e.name}|${e.size}|${e.lastModified??0}|${n}`}function ws(e){return e<1024?`${e} B`:e<1024*1024?`${(e/1024).toFixed(1)} KB`:`${(e/(1024*1024)).toFixed(1)} MB`}function ks(e,t){var a;const n=((a=e.preflightEntry)==null?void 0:a.existing_doc_id)||"";switch(e.verdict){case"pending":return t.t("ops.ingestion.verdict.pending");case"new":return t.t("ops.ingestion.verdict.new");case"revision":return n?t.t("ops.ingestion.verdict.revisionOf",{docId:n}):t.t("ops.ingestion.verdict.revision");case"duplicate":return n?t.t("ops.ingestion.verdict.duplicateOf",{docId:n}):t.t("ops.ingestion.verdict.duplicate");case"artifact":return t.t("ops.ingestion.verdict.artifact");case"unreadable":return t.t("ops.ingestion.verdict.unreadable")}}function $s(e,t){const n=document.createElement("span");return n.className=`ops-verdict-pill ops-verdict-pill--${e.verdict}`,n.textContent=ks(e,t),n}function mt(e){return e.documents.filter(t=>t.status==="raw"||t.status==="needs_classification").length}function Cs(e){const{dom:t,stateController:n,withThinkingWheel:a,setFlash:s}=e;function o(){return e.state.selectedCorpus!=="autogenerar"?e.state.selectedCorpus:"autogenerar"}async function i(){const p=await Ne("/api/corpora"),u=Array.isArray(p.corpora)?p.corpora:[];n.setCorpora(u);const r=new Set(u.map(m=>m.key));r.add("autogenerar"),r.has(e.state.selectedCorpus)||n.setSelectedCorpus("autogenerar")}async function c(){const p=await Ne("/api/ingestion/sessions?limit=20");return Array.isArray(p.sessions)?p.sessions:[]}async function l(p){const u=await Ne(`/api/ingestion/sessions/${encodeURIComponent(p)}`);if(!u.session)throw new Error("missing_session");return u.session}async function d(p){const u=await xt("/api/ingestion/sessions",{corpus:p});if(!u.session)throw new Error("missing_session");return u.session}async function g(p,u,r){const m=t.ingestionCorpusSelect.value==="autogenerar"?"":t.ingestionCorpusSelect.value,_={"Content-Type":"application/octet-stream","X-Upload-Filename":u.name,"X-Upload-Mime":u.type||"application/octet-stream","X-Upload-Batch-Type":r};m&&(_["X-Upload-Topic"]=m);const h=dt(u,e.state.folderRelativePaths);h&&(_["X-Upload-Relative-Path"]=h),console.log(`[upload] ${u.name} (${u.size}B) → session=${p} batch=${r}`);const E=await fetch(`/api/ingestion/sessions/${encodeURIComponent(p)}/files`,{method:"POST",headers:_,body:u}),x=await E.text();let I;try{I=JSON.parse(x)}catch{throw console.error(`[upload] ${u.name} — response not JSON (${E.status}):`,x.slice(0,300)),new Error(`Upload response not JSON: ${E.status} ${x.slice(0,100)}`)}if(!E.ok){const U=I.error||E.statusText;throw console.error(`[upload] ${u.name} — HTTP ${E.status}:`,U),new st(U,E.status,I)}if(!I.document)throw console.error(`[upload] ${u.name} — no document in response:`,I),new Error("missing_document");return console.log(`[upload] ${u.name} → OK doc_id=${I.document.doc_id} status=${I.document.status}`),I.document}async function $(p){return qe(`/api/ingestion/sessions/${encodeURIComponent(p)}/process`,{method:"POST"})}async function v(p){return qe(`/api/ingestion/sessions/${encodeURIComponent(p)}/validate-batch`,{method:"POST"})}async function k(p){return qe(`/api/ingestion/sessions/${encodeURIComponent(p)}/retry`,{method:"POST"})}async function S(p,u=!1){const r=u?"?force=true":"";return qe(`/api/ingestion/sessions/${encodeURIComponent(p)}${r}`,{method:"DELETE"})}async function b({showWheel:p=!0,reportError:u=!0,focusSessionId:r=""}={}){const m=async()=>{await i(),e.render();let _=await c();const h=r||e.state.selectedSessionId;if(h&&!_.some(E=>E.session_id===h))try{_=[await l(h),..._.filter(x=>x.session_id!==h)]}catch{h===e.state.selectedSessionId&&n.setSelectedSession(null)}n.setSessions(_.sort((E,x)=>Date.parse(String(x.updated_at||0))-Date.parse(String(E.updated_at||0)))),n.syncSelectedSession(),e.render()};try{p?await a(m):await m()}catch(_){throw u&&s(we(_),"error"),e.render(),_}}async function C({sessionId:p,showWheel:u=!1,reportError:r=!0}){const m=async()=>{const _=await l(p);n.upsertSession(_),e.render()};try{u?await a(m):await m()}catch(_){throw r&&s(we(_),"error"),_}}async function f(){var u,r,m,_;const p=o();if(console.log(`[folder-ingest] ensureSelectedSession: effectiveCorpus="${p}", selectedSession=${((u=e.state.selectedSession)==null?void 0:u.session_id)||"null"} (status=${((r=e.state.selectedSession)==null?void 0:r.status)||"null"}, corpus=${((m=e.state.selectedSession)==null?void 0:m.corpus)||"null"})`),e.state.selectedSession&&!rn(e.state.selectedSession)&&e.state.selectedSession.status!=="completed"&&(e.state.selectedSession.corpus===p||p==="autogenerar"))return console.log(`[folder-ingest] Reusing session ${e.state.selectedSession.session_id}`),e.state.selectedSession;e.trace(`Creando sesión con corpus="${p}"...`);try{const h=await d(p);return e.trace(`Sesión creada: ${h.session_id} (corpus=${h.corpus})`),n.upsertSession(h),h}catch(h){if(e.trace(`Creación falló para corpus="${p}": ${h instanceof Error?h.message:String(h)}`),p==="autogenerar"){const E=((_=e.state.corpora.find(I=>I.active))==null?void 0:_.key)||"declaracion_renta";e.trace(`Reintentando con corpus="${E}"...`);const x=await d(E);return e.trace(`Sesión fallback: ${x.session_id} (corpus=${x.corpus})`),n.upsertSession(x),x}throw h}}return{resolveSessionCorpus:o,fetchCorpora:i,fetchIngestionSessions:c,fetchIngestionSession:l,createIngestionSession:d,uploadIngestionFile:g,startIngestionProcess:$,validateBatch:v,retryIngestionSession:k,ejectIngestionSession:S,refreshIngestion:b,refreshSelectedSession:C,ensureSelectedSession:f}}function Ss(e){const{i18n:t,stateController:n,dom:a,withThinkingWheel:s,setFlash:o}=e,i=sn(t);return{dom:a,i18n:t,stateController:n,withThinkingWheel:s,setFlash:o,toast:i,get state(){return n.state},render:()=>{},trace:()=>{}}}function Es(e,t){const{dom:n,stateController:a,i18n:s}=e,{ingestionUploadProgress:o}=n;async function i(b){var u,r;const C=[],f=[];for(let m=0;m<b.items.length;m++){const _=(r=(u=b.items[m]).webkitGetAsEntry)==null?void 0:r.call(u);_&&f.push(_)}if(!f.some(m=>m.isDirectory))return[];async function p(m){if(m.isFile){const _=await new Promise((h,E)=>{m.file(h,E)});e.state.folderRelativePaths.set(_,m.fullPath.replace(/^\//,"")),C.push(_)}else if(m.isDirectory){const _=m.createReader();let h;do{h=await new Promise((E,x)=>{_.readEntries(E,x)});for(const E of h)await p(E)}while(h.length>0)}}for(const m of f)await p(m);return C}async function c(b,C=""){const f=[];for await(const[p,u]of b.entries()){const r=C?`${C}/${p}`:p;if(u.kind==="file"){const m=await u.getFile();e.state.folderRelativePaths.set(m,r),f.push(m)}else if(u.kind==="directory"){const m=await c(u,r);f.push(...m)}}return f}async function l(b,C,f,p=At){let u=0,r=0,m=0,_=0;const h=[];return new Promise(E=>{function x(){for(;m<p&&_<C.length;){const I=C[_++];m++,t.uploadIngestionFile(b,I,f).then(()=>{u++}).catch(U=>{r++;const G=U instanceof Error?U.message:String(U);h.push({filename:I.name,error:G}),console.error(`[folder-ingest] Upload failed: ${I.name}`,U)}).finally(()=>{m--,a.setFolderUploadProgress({total:C.length,uploaded:u,failed:r,uploading:_<C.length||m>0}),d(),_<C.length||m>0?x():E({uploaded:u,failed:r,errors:h})})}}a.setFolderUploadProgress({total:C.length,uploaded:0,failed:0,uploading:!0}),d(),x()})}function d(){const b=e.state.folderUploadProgress;if(!b||!b.uploading){o.hidden=!0,o.innerHTML="";return}const C=b.uploaded+b.failed,f=b.total>0?Math.round(C/b.total*100):0,p=Math.max(0,Math.min(At,b.total-C));o.hidden=!1,o.innerHTML=`
      <div class="ops-upload-progress-header">
        <span>${s.t("ops.ingestion.uploadProgress",{current:C,total:b.total})}</span>
        <span>${f}%</span>
      </div>
      <div class="ops-upload-progress-bar">
        <span class="ops-upload-progress-fill" style="width:${f}%"></span>
      </div>
      <div class="ops-upload-progress-detail">
        ${s.t("ops.ingestion.uploadProgressDetail",{uploaded:b.uploaded,failed:b.failed,inflight:p})}
      </div>
    `}function g(){const b=e.state.preflightScanProgress;if(!b||!b.scanning){o.hidden=!0,o.innerHTML="";return}const C=b.total>0?Math.round(b.hashed/b.total*100):0;o.hidden=!1,o.innerHTML=`
      <div class="ops-preflight-scan">
        <div class="ops-preflight-scan-header">
          <span>${s.t("ops.ingestion.preflight.scanning",{hashed:b.hashed,total:b.total})}</span>
          <span>${C}%</span>
        </div>
        <div class="ops-preflight-scan-bar">
          <span class="ops-preflight-scan-fill" style="width:${C}%"></span>
        </div>
        <div class="ops-preflight-scan-detail">${s.t("ops.ingestion.preflight.scanningDetail")}</div>
      </div>
    `}function $(b){if(e.state.pendingFiles.length!==0&&dt(e.state.pendingFiles[0])!=="")try{const C=e.state.pendingFiles.map(f=>({name:f.name,relativePath:dt(f),size:f.size}));localStorage.setItem(wt+b,JSON.stringify(C))}catch{}}function v(b){try{localStorage.removeItem(wt+b)}catch{}}function k(b){try{const C=localStorage.getItem(wt+b);if(!C)return 0;const f=JSON.parse(C);if(!Array.isArray(f))return 0;const p=e.state.sessions.find(r=>r.session_id===b);if(!p)return f.length;const u=new Set((p.documents||[]).map(r=>r.filename));return f.filter(r=>!u.has(r.name)).length}catch{return 0}}async function S(b,C){return(await xt("/api/ingestion/preflight",{corpus:C,files:b})).manifest}return{resolveFolderFiles:i,readDirectoryHandle:c,uploadFilesWithConcurrency:l,renderUploadProgress:d,renderScanProgress:g,persistFolderPending:$,clearFolderPending:v,getStoredFolderPendingCount:k,requestPreflight:S}}function Ns(e,t,n,a){const{dom:s,stateController:o,setFlash:i}=e,{ingestionFolderInput:c,ingestionFileInput:l}=s;let d=!1,g=null;const $=150;function v(_){if(_.length===0)return;const h=new Set(e.state.intake.map(x=>Xe(x.file))),E=[];for(const x of _){const I=Xe(x,e.state.folderRelativePaths);h.has(I)||(h.add(I),E.push({file:x,relativePath:dt(x,e.state.folderRelativePaths),contentHash:null,verdict:"pending",preflightEntry:null}))}E.length!==0&&(o.setIntake([...e.state.intake,...E]),e.state.reviewPlan&&o.setReviewPlan({...e.state.reviewPlan,stalePartial:!0}),d=!1,k(),e.render())}function k(){g&&clearTimeout(g);const _=o.bumpPreflightRunId();g=setTimeout(()=>{g=null,S(_)},$)}async function S(_){if(_!==e.state.preflightRunId||e.state.intake.length===0)return;const h=e.state.intake.filter(E=>E.contentHash===null);try{if(h.length>0&&(await b(h),_!==e.state.preflightRunId))return;const E=await C();if(_!==e.state.preflightRunId)return;if(!E){d=!0,e.render();return}f(E),d=!1,e.render()}catch(E){if(_!==e.state.preflightRunId)return;console.error("[intake] preflight failed:",E),d=!0,e.render()}}async function b(_){o.setPreflightScanProgress({total:_.length,hashed:0,scanning:!0}),n.renderScanProgress();for(let h=0;h<_.length;h++){const E=_[h];try{const x=await E.file.arrayBuffer(),I=await crypto.subtle.digest("SHA-256",x),U=Array.from(new Uint8Array(I));E.contentHash=U.map(G=>G.toString(16).padStart(2,"0")).join("")}catch(x){console.warn(`[intake] hash failed for ${E.file.name}:`,x),E.verdict="unreadable",E.contentHash=""}o.setPreflightScanProgress({total:_.length,hashed:h+1,scanning:!0}),n.renderScanProgress()}o.setPreflightScanProgress(null)}async function C(){const _=e.state.intake.filter(h=>h.contentHash&&h.verdict!=="unreadable").map(h=>({filename:h.file.name,relative_path:h.relativePath||h.file.name,size:h.file.size,content_hash:h.contentHash}));if(_.length===0)return{artifacts:[],duplicates:[],revisions:[],new_files:[],scanned:0,elapsed_ms:0};try{return await n.requestPreflight(_,e.state.selectedCorpus)}catch(h){return console.error("[intake] /api/ingestion/preflight failed:",h),null}}function f(_){const h=new Map,E=(G,B)=>{for(const j of B){const L=j.relative_path||j.filename;h.set(L,{verdict:G,preflightEntry:j})}};E("new",_.new_files),E("revision",_.revisions),E("duplicate",_.duplicates),E("artifact",_.artifacts);const x=e.state.intake.map(G=>{if(G.verdict==="unreadable")return G;const B=G.relativePath||G.file.name,j=h.get(B);return j?{...G,verdict:j.verdict,preflightEntry:j.preflightEntry}:{...G,verdict:"pending"}}),I=x.filter(G=>G.verdict==="new"||G.verdict==="revision"),U=x.filter(G=>G.verdict==="duplicate"||G.verdict==="artifact"||G.verdict==="unreadable");o.setIntake(x),o.setReviewPlan({willIngest:I,bounced:U,scanned:_.scanned,elapsedMs:_.elapsed_ms,stalePartial:!1}),o.setPendingFiles(I.map(G=>G.file))}function p(_){const h=E=>Xe(E.file)!==Xe(_.file);if(o.setIntake(e.state.intake.filter(h)),e.state.reviewPlan){const E=e.state.reviewPlan.willIngest.filter(h);o.setReviewPlan({...e.state.reviewPlan,willIngest:E}),o.setPendingFiles(E.map(x=>x.file))}else o.setPendingFiles(e.state.pendingFiles.filter(E=>Xe(E)!==Xe(_.file)));e.render()}function u(){if(!e.state.reviewPlan)return;const _=new Set(e.state.reviewPlan.willIngest.map(E=>Xe(E.file))),h=e.state.intake.filter(E=>!_.has(Xe(E.file)));o.setIntake(h),o.setReviewPlan({...e.state.reviewPlan,willIngest:[]}),o.setPendingFiles([]),e.render()}function r(){g&&(clearTimeout(g),g=null),o.bumpPreflightRunId(),o.setIntake([]),o.setReviewPlan(null),o.setPendingFiles([]),o.setPreflightScanProgress(null),d=!1,e.state.folderRelativePaths.clear()}async function m(){const _=e.state.reviewPlan;if(_&&!_.stalePartial&&_.willIngest.length!==0&&!d){i(),o.setMutating(!0),a.renderControls();try{await a.directFolderIngest(),r(),c.value="",l.value=""}catch(h){o.setFolderUploadProgress(null),n.renderUploadProgress(),i(we(h),"error"),e.state.selectedSessionId&&t.refreshSelectedSession({sessionId:e.state.selectedSessionId,showWheel:!1,reportError:!1})}finally{o.setMutating(!1),a.renderControls()}}}return{addFilesToIntake:v,schedulePreflight:k,runIntakePreflight:S,hashIntakeEntries:b,preflightIntake:C,applyManifestToIntake:f,removeIntakeEntry:p,cancelAllWillIngest:u,clearIntake:r,confirmAndIngest:m,getIntakeError:()=>d,setIntakeError:_=>{d=_}}}function As(e,t){const{dom:n,i18n:a,stateController:s,setFlash:o}=e,{ingestionAutoStatus:i}=n,c=4e3;let l=null,d="";function g(){l&&(clearTimeout(l),l=null),d="",i.hidden=!0,i.classList.remove("is-running")}function $(S){const b=S.batch_summary,C=mt(S),f=Math.max(0,Number(b.queued??0)-C),p=Number(b.processing??0),u=Number(b.done??0),r=Number(b.failed??0),m=Number(b.bounced??0),_=f+p;i.hidden=!1;const h=m>0?` · ${m} rebotados`:"";_>0||C>0?(i.classList.add("is-running"),i.textContent=a.t("ops.ingestion.auto.running",{queued:f,processing:p,raw:C})+h):r>0?(i.classList.remove("is-running"),i.textContent=a.t("ops.ingestion.auto.done",{done:u,failed:r,raw:C})+h):(i.classList.remove("is-running"),i.textContent=a.t("ops.ingestion.auto.allDone",{done:u})+h)}async function v(){const S=d;if(S)try{const b=await t.fetchIngestionSession(S);s.upsertSession(b),e.render(),$(b);const C=b.batch_summary,f=mt(b),p=Number(C.total??0);if(p===0){g();return}f>0&&await qe(`/api/ingestion/sessions/${encodeURIComponent(S)}/auto-process`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({max_concurrency:5})});const u=f>0?await t.fetchIngestionSession(S):b,r=mt(u),m=Math.max(0,Number(u.batch_summary.queued??0)-r),_=Number(u.batch_summary.processing??0);m>0&&_===0&&await t.startIngestionProcess(S),f>0&&(s.upsertSession(u),e.render(),$(u));const h=m+_;if(p>0&&h===0&&r===0){if(Number(u.batch_summary.pending_batch_gate??0)>0&&u.status!=="running_batch_gates"&&u.status!=="completed")try{await t.validateBatch(S)}catch{}const x=await t.fetchIngestionSession(S);s.upsertSession(x),e.render(),$(x),g(),o(a.t("ops.ingestion.auto.allDone",{done:Number(x.batch_summary.done??0)}),"success");return}if(h===0&&r>0){i.classList.remove("is-running"),i.textContent=a.t("ops.ingestion.auto.done",{done:Number(u.batch_summary.done??0),failed:Number(u.batch_summary.failed??0),raw:r}),g();return}l=setTimeout(()=>void v(),c)}catch(b){g(),o(we(b),"error")}}function k(S){g(),d=S,i.hidden=!1,i.classList.add("is-running"),i.textContent=a.t("ops.ingestion.auto.running",{queued:0,processing:0,raw:0}),l=setTimeout(()=>void v(),2e3)}return{startAutoPilot:k,stopAutoPilot:g,updateAutoStatus:$,autoPilotTick:v}}function Ps(e){const{ctx:t,api:n,upload:a,intake:s,autoPilot:o}=e,{dom:i,stateController:c,i18n:l,setFlash:d,toast:g,withThinkingWheel:$}=t,{ingestionDropzone:v,ingestionFileInput:k,ingestionFolderInput:S,ingestionSelectFilesBtn:b,ingestionSelectFolderBtn:C,ingestionCorpusSelect:f,ingestionRefreshBtn:p,ingestionCreateSessionBtn:u,ingestionUploadBtn:r,ingestionProcessBtn:m,ingestionValidateBatchBtn:_,ingestionRetryBtn:h,ingestionDeleteSessionBtn:E,ingestionAutoProcessBtn:x,ingestionLastError:I,ingestionLogBody:U,ingestionLogAccordion:G,ingestionLogCopyBtn:B,ingestionKanban:j,ingestionUploadProgress:L}=i,{addFilesToIntake:w,clearIntake:M,confirmAndIngest:D}=s,{startAutoPilot:Z,stopAutoPilot:y}=o,{createIngestionSession:q,ejectIngestionSession:N,fetchCorpora:T,refreshIngestion:H,refreshSelectedSession:V,resolveSessionCorpus:oe,retryIngestionSession:le,startIngestionProcess:be,validateBatch:Ee}=n,{resolveFolderFiles:Ae,readDirectoryHandle:Ce}=a,{render:K,renderCorpora:ke,renderControls:pe,traceClear:Pe,directFolderIngest:Me,suppressPanelsOnNextRender:De}=e,{state:he}=c;v.addEventListener("click",()=>{k.disabled||k.click()}),v.addEventListener("keydown",R=>{R.key!=="Enter"&&R.key!==" "||(R.preventDefault(),k.disabled||k.click())});let Le=0;v.addEventListener("dragenter",R=>{R.preventDefault(),Le++,k.disabled||v.classList.add("is-dragover")}),v.addEventListener("dragover",R=>{R.preventDefault()}),v.addEventListener("dragleave",()=>{Le--,Le<=0&&(Le=0,v.classList.remove("is-dragover"))}),v.addEventListener("drop",async R=>{var te;if(R.preventDefault(),Le=0,v.classList.remove("is-dragover"),k.disabled)return;const W=R.dataTransfer;if(W){const Q=await Ae(W);if(Q.length>0){w(lt(Q));return}}const se=Array.from(((te=R.dataTransfer)==null?void 0:te.files)||[]);se.length!==0&&w(lt(se))}),k.addEventListener("change",()=>{const R=Array.from(k.files||[]);R.length!==0&&w(lt(R))}),S.addEventListener("change",()=>{const R=Array.from(S.files||[]);R.length!==0&&w(lt(R))}),b.addEventListener("click",()=>{k.disabled||k.click()}),C.addEventListener("click",async()=>{if(!S.disabled){if(typeof window.showDirectoryPicker=="function")try{const R=await window.showDirectoryPicker({mode:"read"}),W=await Ce(R,R.name),se=lt(W);se.length>0?w(se):d(l.t("ops.ingestion.pendingNone"),"error");return}catch(R){if((R==null?void 0:R.name)==="AbortError")return}S.click()}}),f.addEventListener("change",()=>{c.setSelectedCorpus(f.value),c.setSessions([]),c.setSelectedSession(null),M(),d(),K(),H({showWheel:!0,reportError:!0})}),p.addEventListener("click",R=>{R.stopPropagation(),d(),H({showWheel:!0,reportError:!0})}),u.addEventListener("click",async()=>{y(),d(),M(),c.setPreflightManifest(null),c.setFolderUploadProgress(null),he.rejectedArtifacts=[],L.hidden=!0,L.innerHTML="",k.value="",S.value="",I.hidden=!0,Pe(),G.hidden=!0,U.textContent="",c.setMutating(!0),pe();try{const R=await $(async()=>q(oe()));c.upsertSession(R),K(),d(l.t("ops.ingestion.flash.sessionCreated",{id:R.session_id}),"success")}catch(R){d(we(R),"error")}finally{c.setMutating(!1),pe()}}),r.addEventListener("click",()=>{D()}),m.addEventListener("click",async()=>{const R=he.selectedSessionId;if(R){d(),c.setMutating(!0),pe();try{await $(async()=>be(R)),await V({sessionId:R,showWheel:!1,reportError:!1});const W=l.t("ops.ingestion.flash.processStarted",{id:R});d(W,"success"),g.show({message:W,tone:"success"})}catch(W){const se=we(W);d(se,"error"),g.show({message:se,tone:"error"})}finally{c.setMutating(!1),pe()}}}),_.addEventListener("click",async()=>{const R=he.selectedSessionId;if(R){d(),c.setMutating(!0),pe();try{await $(async()=>Ee(R)),await V({sessionId:R,showWheel:!1,reportError:!1});const W="Validación de lote iniciada";d(W,"success"),g.show({message:W,tone:"success"})}catch(W){const se=we(W);d(se,"error"),g.show({message:se,tone:"error"})}finally{c.setMutating(!1),pe()}}}),h.addEventListener("click",async()=>{const R=he.selectedSessionId;if(R){d(),c.setMutating(!0),pe();try{await $(async()=>le(R)),await V({sessionId:R,showWheel:!1,reportError:!1}),d(l.t("ops.ingestion.flash.retryStarted",{id:R}),"success")}catch(W){d(we(W),"error")}finally{c.setMutating(!1),pe()}}}),E.addEventListener("click",async()=>{var Q;const R=he.selectedSessionId;if(!R)return;const W=rn(he.selectedSession),se=W?l.t("ops.ingestion.confirm.ejectPostGate"):l.t("ops.ingestion.confirm.ejectPreGate");if(await g.confirm({title:l.t("ops.ingestion.actions.discardSession"),message:se,tone:"caution",confirmLabel:l.t("ops.ingestion.confirm.ejectLabel")})){y(),d(),c.setMutating(!0),pe();try{const fe=ht(String(((Q=he.selectedSession)==null?void 0:Q.status)||"")),ae=await $(async()=>N(R,fe||W));c.clearSelectionAfterDelete(),M(),c.setPreflightManifest(null),c.setFolderUploadProgress(null),he.rejectedArtifacts=[],L.hidden=!0,L.innerHTML="",k.value="",S.value="",I.hidden=!0,Pe(),G.hidden=!0,U.textContent="",await H({showWheel:!1,reportError:!1});const ce=Array.isArray(ae.errors)&&ae.errors.length>0,X=ae.path==="rollback"?l.t("ops.ingestion.flash.ejectedRollback",{id:R,count:ae.ejected_files}):l.t("ops.ingestion.flash.ejectedInstant",{id:R,count:ae.ejected_files}),ee=ce?"caution":"success";d(X,ce?"error":"success"),g.show({message:X,tone:ee}),ce&&g.show({message:l.t("ops.ingestion.flash.ejectedPartial"),tone:"caution",durationMs:8e3})}catch(fe){const ae=we(fe);d(ae,"error"),g.show({message:ae,tone:"error"})}finally{c.setMutating(!1),K()}}}),x.addEventListener("click",async()=>{const R=he.selectedSessionId;if(R){d(),c.setMutating(!0),pe();try{await $(async()=>qe(`/api/ingestion/sessions/${encodeURIComponent(R)}/auto-process`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({max_concurrency:5})})),await be(R),await V({sessionId:R,showWheel:!1,reportError:!1}),d(`Auto-procesamiento iniciado para ${R}`,"success"),Z(R)}catch(W){d(we(W),"error")}finally{c.setMutating(!1),pe()}}});const Te=document.getElementById("ingestion-log-toggle");Te&&(Te.addEventListener("click",R=>{if(R.target.closest(".ops-log-copy-btn"))return;const W=U.hidden;U.hidden=!W,Te.setAttribute("aria-expanded",String(W));const se=Te.querySelector(".ops-log-accordion-marker");se&&(se.textContent=W?"▾":"▸")}),Te.addEventListener("keydown",R=>{(R.key==="Enter"||R.key===" ")&&(R.preventDefault(),Te.click())})),B.addEventListener("click",R=>{R.preventDefault(),R.stopPropagation();const W=U.textContent||"";navigator.clipboard.writeText(W).then(()=>{const se=B.textContent;B.textContent=l.t("ops.ingestion.log.copied"),setTimeout(()=>{B.textContent=se},1500)}).catch(()=>{const se=document.createRange();se.selectNodeContents(U);const te=window.getSelection();te==null||te.removeAllRanges(),te==null||te.addRange(se)})}),j.addEventListener("click",async R=>{var ce;const W=R.target.closest("[data-action]");if(!W)return;const se=W.getAttribute("data-action"),te=W.getAttribute("data-doc-id"),Q=he.selectedSessionId;if(!Q||!te)return;if(se==="show-existing-dropdown"){const X=W.closest(".kanban-card"),ee=X==null?void 0:X.querySelector(".kanban-ag-fallback-panel");ee&&(ee.hidden=!ee.hidden);return}let fe="",ae="";if(se==="assign"){const X=W.closest(".kanban-card"),ee=X==null?void 0:X.querySelector("[data-field='topic']"),$e=X==null?void 0:X.querySelector("[data-field='type']");if(fe=(ee==null?void 0:ee.value)||"",ae=($e==null?void 0:$e.value)||"",!fe||!ae){ee&&!fe&&ee.classList.add("kanban-select--invalid"),$e&&!ae&&$e.classList.add("kanban-select--invalid");return}}d(),c.setMutating(!0),pe();try{switch(se){case"assign":{await $(async()=>qe(`/api/ingestion/sessions/${encodeURIComponent(Q)}/documents/${encodeURIComponent(te)}/classify`,{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify({topic:fe,batch_type:ae})})),De.add(te);break}case"replace-dup":{await $(async()=>qe(`/api/ingestion/sessions/${encodeURIComponent(Q)}/documents/${encodeURIComponent(te)}/resolve-duplicate`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action:"replace"})}));break}case"add-new-dup":{await $(async()=>qe(`/api/ingestion/sessions/${encodeURIComponent(Q)}/documents/${encodeURIComponent(te)}/resolve-duplicate`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action:"add_new"})}));break}case"discard-dup":case"discard":{await $(async()=>qe(`/api/ingestion/sessions/${encodeURIComponent(Q)}/documents/${encodeURIComponent(te)}/resolve-duplicate`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action:"discard"})}));break}case"accept-synonym":{const X=W.closest(".kanban-card"),ee=X==null?void 0:X.querySelector("[data-field='type']"),$e=(ee==null?void 0:ee.value)||"";await $(async()=>qe(`/api/ingestion/sessions/${encodeURIComponent(Q)}/documents/${encodeURIComponent(te)}/accept-autogenerar`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action:"accept_synonym",type:$e||void 0})})),De.add(te);break}case"accept-new-topic":{const X=W.closest(".kanban-card"),ee=X==null?void 0:X.querySelector("[data-field='autogenerar-label']"),$e=X==null?void 0:X.querySelector("[data-field='type']"),Re=((ce=ee==null?void 0:ee.value)==null?void 0:ce.trim())||"",Ie=($e==null?void 0:$e.value)||"";if(!Re||Re.length<3){ee&&ee.classList.add("kanban-select--invalid");return}await $(async()=>qe(`/api/ingestion/sessions/${encodeURIComponent(Q)}/documents/${encodeURIComponent(te)}/accept-autogenerar`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action:"accept_new_topic",edited_label:Re,type:Ie||void 0})})),De.add(te),await T(),ke();break}case"retry":{await $(async()=>qe(`/api/ingestion/sessions/${encodeURIComponent(Q)}/documents/${encodeURIComponent(te)}/retry`,{method:"POST"}));break}case"remove":break}await V({sessionId:Q,showWheel:!1,reportError:!1})}catch(X){d(we(X),"error")}finally{c.setMutating(!1),pe()}});const de=i.addCorpusDialog,_e=i.addCorpusBtn;if(de&&_e){let R=function(X){return X.normalize("NFD").replace(/[̀-ͯ]/g,"").toLowerCase().replace(/[^a-z0-9]+/g,"_").replace(/^_|_$/g,"")};const W=de.querySelector("#add-corpus-label"),se=de.querySelector("#add-corpus-key"),te=de.querySelector("#add-corpus-kw-strong"),Q=de.querySelector("#add-corpus-kw-weak"),fe=de.querySelector("#add-corpus-error"),ae=de.querySelector("#add-corpus-cancel"),ce=de.querySelector("#add-corpus-form");_e.addEventListener("click",()=>{W&&(W.value=""),se&&(se.value=""),te&&(te.value=""),Q&&(Q.value=""),fe&&(fe.hidden=!0),de.showModal(),W==null||W.focus()}),W==null||W.addEventListener("input",()=>{se&&(se.value=R(W.value))}),ae==null||ae.addEventListener("click",()=>{de.close()}),ce==null||ce.addEventListener("submit",async X=>{X.preventDefault(),fe&&(fe.hidden=!0);const ee=(W==null?void 0:W.value.trim())||"";if(!ee)return;const $e=((te==null?void 0:te.value)||"").split(",").map(Ie=>Ie.trim()).filter(Boolean),Re=((Q==null?void 0:Q.value)||"").split(",").map(Ie=>Ie.trim()).filter(Boolean);try{await $(async()=>xt("/api/corpora",{label:ee,keywords_strong:$e.length?$e:void 0,keywords_weak:Re.length?Re:void 0})),de.close(),await H({showWheel:!1,reportError:!1});const Ie=R(ee);Ie&&c.setSelectedCorpus(Ie),K(),d(`Categoría "${ee}" creada.`,"success")}catch(Ie){fe&&(fe.textContent=we(Ie),fe.hidden=!1)}})}}function Is(e){const{i18n:t,stateController:n,dom:a,withThinkingWheel:s,setFlash:o}=e,{ingestionCorpusSelect:i,ingestionBatchTypeSelect:c,ingestionDropzone:l,ingestionFileInput:d,ingestionFolderInput:g,ingestionSelectFilesBtn:$,ingestionSelectFolderBtn:v,ingestionUploadProgress:k,ingestionPendingFiles:S,ingestionOverview:b,ingestionRefreshBtn:C,ingestionCreateSessionBtn:f,ingestionUploadBtn:p,ingestionProcessBtn:u,ingestionAutoProcessBtn:r,ingestionValidateBatchBtn:m,ingestionRetryBtn:_,ingestionDeleteSessionBtn:h,ingestionSessionMeta:E,ingestionSessionsList:x,selectedSessionMeta:I,ingestionLastError:U,ingestionLastErrorMessage:G,ingestionLastErrorGuidance:B,ingestionLastErrorNext:j,ingestionKanban:L,ingestionLogAccordion:w,ingestionLogBody:M,ingestionLogCopyBtn:D,ingestionAutoStatus:Z}=a,{state:y}=n,q=Ss(e);q.toast;const N=Cs(q),{resolveSessionCorpus:T,fetchCorpora:H,fetchIngestionSessions:V,fetchIngestionSession:oe,createIngestionSession:le,uploadIngestionFile:be,startIngestionProcess:Ee,validateBatch:Ae,retryIngestionSession:Ce,ejectIngestionSession:K,refreshIngestion:ke,refreshSelectedSession:pe,ensureSelectedSession:Pe}=N,Me=Es(q,N),{resolveFolderFiles:De,readDirectoryHandle:he,uploadFilesWithConcurrency:Le,renderUploadProgress:Te,renderScanProgress:de,persistFolderPending:_e,clearFolderPending:R,getStoredFolderPendingCount:W,requestPreflight:se}=Me;let te=[];function Q(A){const z=`[${new Date().toISOString().slice(11,23)}] ${A}`;te.push(z),console.log(`[folder-ingest] ${A}`),w.hidden=!1,M.hidden=!1,M.textContent=te.join(`
`);const F=document.getElementById("ingestion-log-toggle");if(F){F.setAttribute("aria-expanded","true");const Y=F.querySelector(".ops-log-accordion-marker");Y&&(Y.textContent="▾")}}function fe(){te=[],ae()}function ae(){const{ingestionBounceLog:A,ingestionBounceBody:P}=a;A&&(A.hidden=!0,A.open=!1),P&&(P.textContent="")}const ce={directFolderIngest:()=>Promise.resolve(),renderControls:()=>{}},X=Ns(q,N,Me,ce),{addFilesToIntake:ee,clearIntake:$e,confirmAndIngest:Re,removeIntakeEntry:Ie,cancelAllWillIngest:Je}=X,Ve=new Set;function ut(){const A=y.selectedCorpus;i.innerHTML="";const P=document.createElement("option");P.value="autogenerar",P.textContent="AUTOGENERAR",P.selected=A==="autogenerar",i.appendChild(P),[...y.corpora].sort((z,F)=>z.label.localeCompare(F.label,"es")).forEach(z=>{var O;const F=document.createElement("option");F.value=z.key;const Y=((O=z.attention)==null?void 0:O.length)||0;let ne=z.active?z.label:`${z.label} (${t.t("ops.ingestion.corpusInactiveOption")})`;Y>0&&(ne+=` ⚠ ${Y}`),F.textContent=ne,F.selected=z.key===A,i.appendChild(F)})}function kn(A,P,z){var ve;const F=document.createElement("div");F.className="ops-intake-row",P.verdict==="pending"&&F.classList.add("ops-intake-row--pending"),z.readonly&&F.classList.add("ops-intake-row--readonly");const Y=document.createElement("span");Y.className="ops-intake-row__icon",Y.textContent="📄";const ne=document.createElement("span");ne.className="ops-intake-row__name",ne.textContent=P.relativePath||P.file.name,ne.title=P.relativePath||P.file.name;const O=document.createElement("span");O.className="ops-intake-row__size",O.textContent=ws(P.file.size);const ie=$s(P,t);if(F.append(Y,ne,O,ie),z.showReason&&((ve=P.preflightEntry)!=null&&ve.reason)){const ue=document.createElement("span");ue.className="ops-intake-row__reason",ue.textContent=P.preflightEntry.reason,ue.title=P.preflightEntry.reason,F.appendChild(ue)}if(z.removable){const ue=document.createElement("button");ue.type="button",ue.className="ops-intake-row__remove",ue.textContent="✕",ue.title=t.t("ops.ingestion.willIngest.cancelAll"),ue.addEventListener("click",Be=>{Be.stopPropagation(),Ie(P)}),F.appendChild(ue)}A.appendChild(F)}function _t(A,P,z,F,Y,ne){const O=document.createElement("section");O.className=`ops-intake-panel ops-intake-panel--${A}`;const ie=document.createElement("header");ie.className="ops-intake-panel__header";const ve=document.createElement("span");ve.className="ops-intake-panel__title",ve.textContent=t.t(P),ie.appendChild(ve);const ue=document.createElement("span");if(ue.className="ops-intake-panel__count",ue.textContent=t.t(z,{count:F}),ie.appendChild(ue),ne.readonly){const Se=document.createElement("span");Se.className="ops-intake-panel__readonly",Se.textContent=t.t("ops.ingestion.bounced.readonly"),ie.appendChild(Se)}if(ne.cancelAllAction){const Se=document.createElement("button");Se.type="button",Se.className="ops-intake-panel__action",Se.textContent=t.t("ops.ingestion.willIngest.cancelAll"),Se.addEventListener("click",He=>{He.stopPropagation(),ne.cancelAllAction()}),ie.appendChild(Se)}O.appendChild(ie);const Be=document.createElement("div");return Be.className="ops-intake-panel__body",Y.forEach(Se=>kn(Be,Se,ne)),O.appendChild(Be),O}function $n(){var F,Y;if((F=l.querySelector(".ops-intake-windows"))==null||F.remove(),(Y=l.querySelector(".dropzone-file-list"))==null||Y.remove(),y.intake.length===0){S.textContent=t.t("ops.ingestion.pendingNone"),S.hidden=!0,l.classList.remove("has-files");return}S.hidden=!0,l.classList.add("has-files");const A=document.createElement("div");A.className="ops-intake-windows";const P=Cn();P&&A.appendChild(P),A.appendChild(_t("intake","ops.ingestion.intake.title","ops.ingestion.intake.count",y.intake.length,y.intake,{removable:!1,readonly:!1,showReason:!1}));const z=y.reviewPlan;z&&(A.appendChild(_t("will-ingest","ops.ingestion.willIngest.title","ops.ingestion.willIngest.count",z.willIngest.length,z.willIngest,{removable:!0,readonly:!1,showReason:!1,cancelAllAction:z.willIngest.length>0?()=>Je():void 0})),z.bounced.length>0&&A.appendChild(_t("bounced","ops.ingestion.bounced.title","ops.ingestion.bounced.count",z.bounced.length,z.bounced,{removable:!1,readonly:!0,showReason:!0}))),l.appendChild(A)}function Cn(){var O;const A=((O=y.reviewPlan)==null?void 0:O.stalePartial)===!0,P=y.intake.some(ie=>ie.verdict==="pending"),z=X.getIntakeError();if(!A&&!P&&!z)return null;const F=document.createElement("div");if(F.className="ops-intake-banner",z){F.classList.add("ops-intake-banner--error");const ie=document.createElement("span");ie.className="ops-intake-banner__text",ie.textContent=t.t("ops.ingestion.intake.failed");const ve=document.createElement("button");return ve.type="button",ve.className="ops-intake-banner__retry",ve.textContent=t.t("ops.ingestion.intake.retry"),ve.addEventListener("click",ue=>{ue.stopPropagation(),X.setIntakeError(!1),X.schedulePreflight(),ot()}),F.append(ie,ve),F}const Y=document.createElement("span");Y.className="ops-intake-banner__spinner",F.appendChild(Y);const ne=document.createElement("span");return ne.className="ops-intake-banner__text",A?(F.classList.add("ops-intake-banner--stale"),ne.textContent=t.t("ops.ingestion.intake.stale")):(F.classList.add("ops-intake-banner--verifying"),ne.textContent=t.t("ops.ingestion.intake.verifying")),F.appendChild(ne),F}function at(){var Ue,Qe,it,rt,me;const A=n.selectedCorpusConfig(),P=y.selectedSession,z=y.selectedCorpus==="autogenerar"?y.corpora.some(Oe=>Oe.active):!!(A!=null&&A.active),F=ht(String((P==null?void 0:P.status)||""));c.value=c.value||"autogenerar";const Y=((Ue=y.folderUploadProgress)==null?void 0:Ue.uploading)??!1,ne=y.reviewPlan,O=(ne==null?void 0:ne.willIngest.length)??0,ie=(ne==null?void 0:ne.stalePartial)===!0,ve=X.getIntakeError()===!0,ue=!!ne&&O>0&&!ie&&!ve;f.disabled=y.mutating||!z,$.disabled=y.mutating||!z||Y,v.disabled=y.mutating||!z||Y||F,p.disabled=y.mutating||!z||!ue||Y,ne?O===0?p.textContent=t.t("ops.ingestion.approveNone"):p.textContent=t.t("ops.ingestion.approveCount",{count:O}):p.textContent=t.t("ops.ingestion.approve"),u.disabled=y.mutating||!z||!P||F,r.disabled=y.mutating||!z||Y||!P||F,r.textContent=`▶ ${t.t("ops.ingestion.actions.autoProcess")}`;const Be=Number(((Qe=P==null?void 0:P.batch_summary)==null?void 0:Qe.done)||0),Se=Number(((it=P==null?void 0:P.batch_summary)==null?void 0:it.queued)||0)+Number(((rt=P==null?void 0:P.batch_summary)==null?void 0:rt.processing)||0),He=Number(((me=P==null?void 0:P.batch_summary)==null?void 0:me.pending_batch_gate)||0),Fe=Be>=1&&(Se>=1||He>=1);if(m.disabled=y.mutating||!z||!P||F||!Fe,_.disabled=y.mutating||!z||!P||F,h.disabled=y.mutating||!P,C.disabled=y.mutating,i.disabled=y.mutating||y.corpora.length===0,d.disabled=y.mutating||!z,!z){b.textContent=t.t("ops.ingestion.corpusInactive");return}b.textContent=t.t("ops.ingestion.overview",{active:y.corpora.filter(Oe=>Oe.active).length,total:y.corpora.length,corpus:y.selectedCorpus==="autogenerar"?"AUTOGENERAR":(A==null?void 0:A.label)||y.selectedCorpus,session:(P==null?void 0:P.session_id)||t.t("ops.ingestion.noSession")})}function Sn(){if(x.innerHTML="",E.textContent=y.selectedSession?`${y.selectedSession.session_id} · ${y.selectedSession.status}`:t.t("ops.ingestion.selectedEmpty"),y.sessions.length===0){const A=document.createElement("li");A.className="ops-empty",A.textContent=t.t("ops.ingestion.sessionsEmpty"),x.appendChild(A);return}y.sessions.forEach(A=>{var it,rt;const P=document.createElement("li"),z=A.status==="partial_failed",F=document.createElement("button");F.type="button",F.className=`ops-session-item${A.session_id===y.selectedSessionId?" is-active":""}${z?" has-retry-action":""}`,F.dataset.sessionId=A.session_id;const Y=document.createElement("div");Y.className="ops-session-item-head";const ne=document.createElement("div");ne.className="ops-session-id",ne.textContent=A.session_id;const O=document.createElement("span");O.className=`meta-chip status-${ct(A.status)}`,O.textContent=A.status,Y.append(ne,O);const ie=document.createElement("div");ie.className="ops-session-pills";const ve=((it=y.corpora.find(me=>me.key===A.corpus))==null?void 0:it.label)||A.corpus,ue=document.createElement("span");ue.className="meta-chip ops-pill-corpus",ue.textContent=ve,ie.appendChild(ue);const Be=A.documents||[];[...new Set(Be.map(me=>me.batch_type).filter(Boolean))].forEach(me=>{const Oe=document.createElement("span");Oe.className="meta-chip ops-pill-batch",Oe.textContent=Qn(me,t),ie.appendChild(Oe)});const He=Be.map(me=>me.filename).filter(Boolean);let Fe=null;if(He.length>0){Fe=document.createElement("div"),Fe.className="ops-session-files";const me=He.slice(0,3),Oe=He.length-me.length;Fe.textContent=me.join(", ")+(Oe>0?` +${Oe}`:"")}const Ue=document.createElement("div");Ue.className="ops-session-summary",Ue.textContent=zt(A.batch_summary,t);const Qe=document.createElement("div");if(Qe.className="ops-session-summary",Qe.textContent=A.updated_at?t.formatDateTime(A.updated_at,{dateStyle:"short",timeStyle:"short",timeZone:"America/Bogota"}):"-",F.appendChild(Y),F.appendChild(ie),Fe&&F.appendChild(Fe),F.appendChild(Ue),F.appendChild(Qe),(rt=A.last_error)!=null&&rt.code){const me=document.createElement("div");me.className="ops-session-summary status-error",me.textContent=A.last_error.code,F.appendChild(me)}if(F.addEventListener("click",async()=>{n.setSelectedSession(A),ot();try{await pe({sessionId:A.session_id,showWheel:!0})}catch{}}),P.appendChild(F),z){const me=document.createElement("button");me.type="button",me.className="ops-session-retry-inline",me.textContent=t.t("ops.ingestion.actions.retry"),me.disabled=y.mutating,me.addEventListener("click",async Oe=>{Oe.stopPropagation(),me.disabled=!0,n.setMutating(!0),at();try{await s(async()=>Ce(A.session_id)),await ke({showWheel:!1,reportError:!0,focusSessionId:A.session_id}),o(t.t("ops.ingestion.flash.retryStarted",{id:A.session_id}),"success")}catch(In){o(we(In),"error")}finally{n.setMutating(!1),at()}}),P.appendChild(me)}x.appendChild(P)})}function En(A){const P=[],z=()=>new Date().toISOString();if(P.push(t.t("ops.ingestion.log.sessionHeader",{id:A.session_id})),P.push(`Corpus:     ${A.corpus||"-"}`),P.push(`Status:     ${A.status}`),P.push(`Created:    ${A.created_at||"-"}`),P.push(`Updated:    ${A.updated_at||"-"}`),P.push(`Heartbeat:  ${A.heartbeat_at??"-"}`),A.auto_processing&&P.push(`Auto-proc:  ${A.auto_processing}`),A.gate_sub_stage&&P.push(`Gate-stage: ${A.gate_sub_stage}`),A.wip_sync_status&&P.push(`WIP-sync:   ${A.wip_sync_status}`),A.batch_summary){const Y=A.batch_summary,ne=(A.documents||[]).filter(ie=>ie.status==="raw"||ie.status==="needs_classification").length,O=(A.documents||[]).filter(ie=>ie.status==="pending_dedup").length;P.push(""),P.push("── Resumen del lote ──"),P.push(`  Total: ${Y.total}  Queued: ${Y.queued}  Processing: ${Y.processing}  Done: ${Y.done}  Failed: ${Y.failed}  Duplicados: ${Y.skipped_duplicate}  Bounced: ${Y.bounced}`),ne>0&&P.push(`  Raw (sin clasificar): ${ne}`),O>0&&P.push(`  Pending dedup: ${O}`)}A.last_error&&(P.push(""),P.push("── Error de sesión ──"),P.push(`  Código:    ${A.last_error.code||"-"}`),P.push(`  Mensaje:   ${A.last_error.message||"-"}`),P.push(`  Guía:      ${A.last_error.guidance||"-"}`),P.push(`  Siguiente: ${A.last_error.next_step||"-"}`));const F=A.documents||[];if(F.length===0)P.push(""),P.push(t.t("ops.ingestion.log.noDocuments"));else{P.push(""),P.push(`── Documentos (${F.length}) ──`);const Y={failed:0,processing:1,in_progress:1,queued:2,raw:2,done:3,completed:3,bounced:4,skipped_duplicate:5},ne=[...F].sort((O,ie)=>(Y[O.status]??3)-(Y[ie.status]??3));for(const O of ne)P.push(""),P.push(`  ┌─ ${O.filename} (${O.doc_id})`),P.push(`  │  Status:   ${O.status}  │  Stage: ${O.stage||"-"}  │  Progress: ${O.progress??0}%`),P.push(`  │  Bytes:    ${O.bytes??"-"}  │  Batch: ${O.batch_type||"-"}`),O.source_relative_path&&P.push(`  │  Path:     ${O.source_relative_path}`),(O.detected_topic||O.detected_type)&&(P.push(`  │  Topic:    ${O.detected_topic||"-"}  │  Type: ${O.detected_type||"-"}  │  Confidence: ${O.combined_confidence??"-"}`),O.classification_source&&P.push(`  │  Classifier: ${O.classification_source}`)),O.chunk_count!=null&&P.push(`  │  Chunks:   ${O.chunk_count}  │  Elapsed: ${O.elapsed_ms??"-"}ms`),O.dedup_match_type&&P.push(`  │  Dedup:    ${O.dedup_match_type}  │  Match: ${O.dedup_match_doc_id||"-"}`),O.replaced_doc_id&&P.push(`  │  Replaced: ${O.replaced_doc_id}`),O.error&&(P.push("  │  ❌ ERROR"),P.push(`  │    Código:    ${O.error.code||"-"}`),P.push(`  │    Mensaje:   ${O.error.message||"-"}`),P.push(`  │    Guía:      ${O.error.guidance||"-"}`),P.push(`  │    Siguiente: ${O.error.next_step||"-"}`)),P.push(`  │  Created: ${O.created_at||"-"}  │  Updated: ${O.updated_at||"-"}`),P.push("  └─")}return P.push(""),P.push(`Log generado: ${z()}`),P.join(`
`)}function Lt(){if(te.length>0)return;const A=y.selectedSession;if(!A){w.hidden=!0,M.textContent="";return}w.hidden=!1,M.textContent=En(A)}function Nn(){const A=y.selectedSession;if(!A){I.textContent=t.t("ops.ingestion.selectedEmpty"),U.hidden=!0,te.length===0&&(w.hidden=!0),L.innerHTML="";return}const P=W(A.session_id),z=P>0?` · ${t.t("ops.ingestion.folderResumePending",{count:P})}`:"";if(I.textContent=`${A.session_id} · ${zt(A.batch_summary,t)}${z}`,A.last_error?(U.hidden=!1,G.textContent=A.last_error.message||A.last_error.code||"-",B.textContent=A.last_error.guidance||"",j.textContent=`${t.t("ops.ingestion.lastErrorNext")}: ${A.last_error.next_step||"-"}`):U.hidden=!0,(A.documents||[]).length===0){L.innerHTML=`<p class="ops-empty">${t.t("ops.ingestion.documentsEmpty")}</p>`,L.style.minHeight="0",Lt();return}L.style.minHeight="",_s(A,L,t,Ve,y.corpora),Ve.clear(),Lt()}function ot(){ut(),$n(),at(),Sn(),Nn()}q.render=ot,q.trace=Q,ce.directFolderIngest=Rt,ce.renderControls=at;const Tt=As(q,N),{startAutoPilot:An,stopAutoPilot:ja,updateAutoStatus:za}=Tt;async function Rt(){var Be,Se,He;Q(`directFolderIngest: ${y.pendingFiles.length} archivos pendientes`);const A=await Pe();Q(`Sesión asignada: ${A.session_id} (corpus=${A.corpus}, status=${A.status})`);const P=c.value||"autogenerar";Q(`Subiendo ${y.pendingFiles.length} archivos con batchType="${P}"...`),_e(A.session_id);const z=await Le(A.session_id,[...y.pendingFiles],P,At);if(console.log("[folder-ingest] Upload result:",{uploaded:z.uploaded,failed:z.failed}),Q(`Upload completo: ${z.uploaded} subidos, ${z.failed} fallidos${z.errors.length>0?" — "+z.errors.slice(0,5).map(Fe=>`${Fe.filename}: ${Fe.error}`).join("; "):""}`),n.setPendingFiles([]),n.setFolderUploadProgress(null),R(A.session_id),g.value="",d.value="",z.failed>0&&z.uploaded===0){const Fe=z.errors.slice(0,3).map(Ue=>`${Ue.filename}: ${Ue.error}`).join("; ");Q(`TODOS FALLARON: ${Fe}`),o(`${t.t("ops.ingestion.flash.folderUploadPartial",z)} — ${Fe}`,"error"),await ke({showWheel:!1,reportError:!0,focusSessionId:A.session_id});return}Q("Consultando estado de sesión post-upload...");const F=await oe(A.session_id),Y=Number(((Be=F.batch_summary)==null?void 0:Be.bounced)??0),ne=mt(F),O=Number(((Se=F.batch_summary)==null?void 0:Se.queued)??0),ie=Number(((He=F.batch_summary)==null?void 0:He.total)??0),ve=ie-Y;if(Q(`Sesión post-upload: total=${ie} bounced=${Y} raw=${ne} queued=${O} actionable=${ve}`),ve===0&&Y>0){Q(`TODOS REBOTADOS: ${Y} archivos ya existen en el corpus`),n.upsertSession(F),o(`${Y} archivos ya existen en el corpus (rebotados). 0 archivos nuevos para procesar.`,"error"),Q("--- FIN (todo rebotado) ---");return}Q("Auto-procesando con threshold=0 (force-queue)..."),await qe(`/api/ingestion/sessions/${encodeURIComponent(A.session_id)}/auto-process`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({max_concurrency:5,auto_accept_threshold:0})}),await Ee(A.session_id),await ke({showWheel:!1,reportError:!0,focusSessionId:A.session_id});const ue=[];z.uploaded>0&&ue.push(`${ve} archivos en proceso`),Y>0&&ue.push(`${Y} rebotados`),z.failed>0&&ue.push(`${z.failed} fallidos`),o(ue.join(" · "),z.failed>0?"error":"success"),Q(`Auto-piloto iniciado para ${A.session_id}`),Q("--- FIN (éxito) ---"),An(A.session_id)}function Pn(){Ps({ctx:q,api:N,upload:Me,intake:X,autoPilot:Tt,render:ot,renderCorpora:ut,renderControls:at,traceClear:fe,directFolderIngest:Rt,suppressPanelsOnNextRender:Ve})}return{bindEvents:Pn,refreshIngestion:ke,refreshSelectedSession:pe,render:ot}}function Ye(e){if(e==null)return null;const t=Number(e);return!Number.isFinite(t)||t<0?null:t}function gn({i18n:e,stateController:t,dom:n,withThinkingWheel:a,setFlash:s}){const{monitorTabBtn:o,ingestionTabBtn:i,controlTabBtn:c,embeddingsTabBtn:l,reindexTabBtn:d,monitorPanel:g,ingestionPanel:$,controlPanel:v,embeddingsPanel:k,reindexPanel:S,runsBody:b,timelineNode:C,timelineMeta:f,cascadeNote:p,userCascadeNode:u,userCascadeSummary:r,technicalCascadeNode:m,technicalCascadeSummary:_,refreshRunsBtn:h}=n,{state:E}=t;function x(N){const T=Ye(N);return T===null?"-":`${e.formatNumber(T/1e3,{minimumFractionDigits:2,maximumFractionDigits:2})} s`}function I(N){t.setActiveTab(N),U()}function U(){if(!o)return;const N=E.activeTab;o.classList.toggle("is-active",N==="monitor"),o.setAttribute("aria-selected",String(N==="monitor")),i==null||i.classList.toggle("is-active",N==="ingestion"),i==null||i.setAttribute("aria-selected",String(N==="ingestion")),c==null||c.classList.toggle("is-active",N==="control"),c==null||c.setAttribute("aria-selected",String(N==="control")),l==null||l.classList.toggle("is-active",N==="embeddings"),l==null||l.setAttribute("aria-selected",String(N==="embeddings")),d==null||d.classList.toggle("is-active",N==="reindex"),d==null||d.setAttribute("aria-selected",String(N==="reindex")),g&&(g.hidden=N!=="monitor",g.classList.toggle("is-active",N==="monitor")),$&&($.hidden=N!=="ingestion",$.classList.toggle("is-active",N==="ingestion")),v&&(v.hidden=N!=="control",v.classList.toggle("is-active",N==="control")),k&&(k.hidden=N!=="embeddings",k.classList.toggle("is-active",N==="embeddings")),S&&(S.hidden=N!=="reindex",S.classList.toggle("is-active",N==="reindex"))}function G(N){if(C.innerHTML="",!Array.isArray(N)||N.length===0){C.innerHTML=`<li>${e.t("ops.timeline.empty")}</li>`;return}N.forEach(T=>{const H=document.createElement("li");H.innerHTML=`
        <strong>${T.stage||"-"}</strong> · <span class="status-${ct(String(T.status||""))}">${T.status||"-"}</span><br/>
        <small>${T.at||"-"} · ${T.duration_ms||0} ms</small>
        <pre>${JSON.stringify(T.details||{},null,2)}</pre>
      `,C.appendChild(H)})}function B(N,T,H){const V=Ye(T==null?void 0:T.total_ms),oe=V===null?e.t("ops.timeline.summaryPending"):x(V),le=H==="user"&&String((T==null?void 0:T.chat_run_id)||"").trim()?` · chat_run ${String((T==null?void 0:T.chat_run_id)||"").trim()}`:"";N.textContent=`${e.t("ops.timeline.totalLabel")} ${oe}${le}`}function j(N){var be,Ee,Ae;const T=[],H=String(((be=N.details)==null?void 0:be.source)||"").trim(),V=String(N.status||"").trim();H&&T.push(H),V&&V!=="ok"&&V!=="missing"&&T.push(V);const oe=Number(((Ee=N.details)==null?void 0:Ee.citations_count)||0);Number.isFinite(oe)&&oe>0&&T.push(`${oe} refs`);const le=String(((Ae=N.details)==null?void 0:Ae.panel_status)||"").trim();return le&&T.push(le),T.join(" · ")}function L(N,T,H){N.innerHTML="";const V=Array.isArray(T==null?void 0:T.steps)?(T==null?void 0:T.steps)||[]:[];if(V.length===0){N.innerHTML=`<li class="ops-cascade-step is-empty">${e.t("ops.timeline.waterfallEmpty")}</li>`;return}const oe=Ye(T==null?void 0:T.total_ms)??Math.max(1,...V.map(le=>Ye(le.cumulative_ms)??Ye(le.absolute_elapsed_ms)??0));V.forEach(le=>{const be=Ye(le.duration_ms),Ee=Ye(le.offset_ms)??0,Ae=Ye(le.absolute_elapsed_ms),Ce=document.createElement("li");Ce.className=`ops-cascade-step ops-cascade-step--${H}${be===null?" is-missing":""}`;const K=document.createElement("div");K.className="ops-cascade-step-head";const ke=document.createElement("div"),pe=document.createElement("strong");pe.textContent=le.label||"-";const Pe=document.createElement("small");Pe.className="ops-cascade-step-meta",Pe.textContent=be===null?e.t("ops.timeline.missingStep"):`${e.t("ops.timeline.stepLabel")} ${x(be)} · T+${x(Ae??le.cumulative_ms)}`,ke.append(pe,Pe);const Me=document.createElement("span");Me.className=`meta-chip status-${ct(String(le.status||""))}`,Me.textContent=String(le.status||(be===null?"missing":"ok")),K.append(ke,Me),Ce.appendChild(K);const De=document.createElement("div");De.className="ops-cascade-track";const he=document.createElement("span");he.className="ops-cascade-segment";const Le=Math.max(0,Math.min(100,Ee/oe*100)),Te=be===null?0:Math.max(be/oe*100,be>0?2.5:0);he.style.left=`${Le}%`,he.style.width=`${Te}%`,he.setAttribute("aria-label",be===null?`${le.label}: ${e.t("ops.timeline.missingStep")}`:`${le.label}: ${x(be)}`),De.appendChild(he),Ce.appendChild(De);const de=j(le);if(de){const _e=document.createElement("p");_e.className="ops-cascade-step-detail",_e.textContent=de,Ce.appendChild(_e)}N.appendChild(Ce)})}async function w(){return(await Ne("/api/ops/runs?limit=30")).runs||[]}async function M(N){return Ne(`/api/ops/runs/${encodeURIComponent(N)}/timeline`)}function D(N,T){var V;const H=N.run||{};f.textContent=e.t("ops.timeline.label",{id:T}),p.textContent=e.t("ops.timeline.selectedRunMeta",{trace:String(H.trace_id||"-"),chatRun:String(((V=N.user_waterfall)==null?void 0:V.chat_run_id)||H.chat_run_id||"-")}),B(r,N.user_waterfall,"user"),B(_,N.technical_waterfall,"technical"),L(u,N.user_waterfall,"user"),L(m,N.technical_waterfall,"technical"),G(Array.isArray(N.timeline)?N.timeline:[])}function Z(N){if(b.innerHTML="",!Array.isArray(N)||N.length===0){const T=document.createElement("tr");T.innerHTML=`<td colspan="4">${e.t("ops.runs.empty")}</td>`,b.appendChild(T);return}N.forEach(T=>{const H=document.createElement("tr");H.innerHTML=`
        <td><button type="button" class="link-btn" data-run-id="${T.run_id}">${T.run_id}</button></td>
        <td>${T.trace_id||"-"}</td>
        <td class="status-${ct(String(T.status||""))}">${T.status||"-"}</td>
        <td>${T.started_at?e.formatDateTime(T.started_at,{dateStyle:"short",timeStyle:"short",timeZone:"America/Bogota"}):"-"}</td>
      `,b.appendChild(H)}),b.querySelectorAll("button[data-run-id]").forEach(T=>{T.addEventListener("click",async()=>{const H=T.getAttribute("data-run-id")||"";try{const V=await a(async()=>M(H));D(V,H)}catch(V){u.innerHTML=`<li class="ops-cascade-step is-empty status-error">${we(V)}</li>`,m.innerHTML=`<li class="ops-cascade-step is-empty status-error">${we(V)}</li>`,C.innerHTML=`<li class="status-error">${we(V)}</li>`}})})}async function y({showWheel:N=!0,reportError:T=!0}={}){const H=async()=>{const V=await w();Z(V)};try{N?await a(H):await H()}catch(V){b.innerHTML=`<tr><td colspan="4" class="status-error">${we(V)}</td></tr>`,T&&s(we(V),"error")}}function q(){o==null||o.addEventListener("click",()=>{I("monitor")}),i==null||i.addEventListener("click",()=>{I("ingestion")}),c==null||c.addEventListener("click",()=>{I("control")}),l==null||l.addEventListener("click",()=>{I("embeddings")}),d==null||d.addEventListener("click",()=>{I("reindex")}),h.addEventListener("click",()=>{s(),y({showWheel:!0,reportError:!0})})}return{bindEvents:q,refreshRuns:y,renderTabs:U}}function Ge(e){return String(e??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#39;")}function et(e){return(e??0).toLocaleString("es-CO")}function xs(e){if(e==null||e<=0)return"-";const t=Math.floor(e/60),n=Math.floor(e%60);return t>0?`${t}m ${n}s`:`${n}s`}function Ls(e){if(!e.length)return"";let t='<ol class="reindex-stage-list">';for(const n of e){const a=n.state==="completed"?"ops-dot-ok":n.state==="active"?"ops-dot-active":n.state==="failed"?"ops-dot-error":"ops-dot-pending",s=n.state==="active"?`<strong>${Ge(n.label)}</strong>`:Ge(n.label);t+=`<li class="reindex-stage-item reindex-stage-${n.state}"><span class="ops-dot ${a}">●</span> ${s}</li>`}return t+="</ol>",t}function fn({dom:e,setFlash:t,navigateToEmbeddings:n}){const{container:a}=e;let s=null,o="";function i(){var p,u,r;const $=s;if(!$){a.innerHTML='<p class="ops-text-muted">Cargando estado de re-index...</p>';return}const v=$.current_operation||$.last_operation,k=((p=$.current_operation)==null?void 0:p.status)==="running",S=!$.current_operation;let b="";const C=k?"En ejecución":S?"Inactivo":(v==null?void 0:v.status)??"—",f=k?"tone-yellow":(v==null?void 0:v.status)==="completed"?"tone-green":(v==null?void 0:v.status)==="failed"?"tone-red":"";if(b+=`<div class="reindex-status-row">
      <span class="corpus-status-chip ${f}">${Ge(C)}</span>
      <span class="emb-target-badge">WIP</span>
      ${k?`<span class="emb-heartbeat ${Et(v==null?void 0:v.heartbeat_at,v==null?void 0:v.updated_at)}">${Et(v==null?void 0:v.heartbeat_at,v==null?void 0:v.updated_at)}</span>`:""}
    </div>`,b+='<div class="reindex-controls">',S&&(b+=`<button class="corpus-btn corpus-btn-promote" id="reindex-start-btn" ${o?"disabled":""}>Iniciar re-index</button>`),k&&v&&(b+=`<button class="corpus-btn corpus-btn-rollback" id="reindex-stop-btn" ${o?"disabled":""}>Detener</button>`),b+="</div>",(u=v==null?void 0:v.stages)!=null&&u.length&&(b+=Ls(v.stages)),v!=null&&v.progress){const m=v.progress,_=[];m.documents_processed!=null&&_.push(`Documentos: ${et(m.documents_processed)} / ${et(m.documents_total)}`),m.documents_indexed!=null&&_.push(`Documentos indexados: ${et(m.documents_indexed)}`),m.elapsed_seconds!=null&&_.push(`Tiempo: ${xs(m.elapsed_seconds)}`),_.length&&(b+=`<div class="reindex-progress-stats">${_.map(h=>`<span>${Ge(h)}</span>`).join("")}</div>`)}if(v!=null&&v.quality_report){const m=v.quality_report;if(b+='<div class="reindex-quality-report">',b+="<h3>Reporte de calidad</h3>",b+=`<div class="emb-stats-grid">
        <div class="emb-stat"><span class="emb-stat-value">${et(m.documents_indexed)}</span><span class="emb-stat-label">Documentos</span></div>
        <div class="emb-stat"><span class="emb-stat-value">${et(m.chunks_generated)}</span><span class="emb-stat-label">Chunks</span></div>
        <div class="emb-stat"><span class="emb-stat-value">${m.blocking_issues??0}</span><span class="emb-stat-label">Blocking issues</span></div>
      </div>`,m.knowledge_class_counts){b+='<div class="reindex-kc-breakdown"><h4>Knowledge classes</h4><dl class="reindex-kc-dl">';for(const[_,h]of Object.entries(m.knowledge_class_counts))b+=`<dt>${Ge(_)}</dt><dd>${et(h)}</dd>`;b+="</dl></div>"}b+="</div>",b+=`<div class="reindex-embed-prompt">
        <p>Re-index completado. Para aplicar los nuevos summaries a los embeddings:</p>
        <button class="corpus-btn corpus-btn-promote" id="reindex-embed-now-btn">Embed ahora</button>
      </div>`}if((r=v==null?void 0:v.checks)!=null&&r.length){b+='<div class="emb-checks">';for(const m of v.checks){const _=m.ok?'<span class="ops-dot ops-dot-ok">●</span>':'<span class="ops-dot ops-dot-error">●</span>';b+=`<div class="emb-check">${_} <strong>${Ge(m.label)}</strong>: ${Ge(m.detail)}</div>`}b+="</div>"}v!=null&&v.log_tail&&(b+=`<details class="emb-log-accordion"><summary>Log</summary><pre class="emb-log-tail">${Ge(v.log_tail)}</pre></details>`),v!=null&&v.error&&(b+=`<p class="emb-error">${Ge(v.error)}</p>`),a.innerHTML=b}function c(){a.addEventListener("click",$=>{const v=$.target;v.id==="reindex-start-btn"&&l(),v.id==="reindex-stop-btn"&&d(),v.id==="reindex-embed-now-btn"&&n()})}async function l(){o="start",i();try{await ze("/api/ops/reindex/start",{mode:"from_source"}),t("Re-index iniciado","success")}catch($){t(String($),"error")}o="",await g()}async function d(){var v;const $=(v=s==null?void 0:s.current_operation)==null?void 0:v.job_id;if($){o="stop",i();try{await ze("/api/ops/reindex/stop",{job_id:$}),t("Re-index detenido","success")}catch(k){t(String(k),"error")}o="",await g()}}async function g(){try{s=await Ne("/api/ops/reindex-status")}catch{}i()}return{bindEvents:c,refresh:g}}const eo=Object.freeze(Object.defineProperty({__proto__:null,createOpsReindexController:fn},Symbol.toStringTag,{value:"Module"})),Ts=3e3,Ut=8e3;function bn({stateController:e,withThinkingWheel:t,setFlash:n,refreshRuns:a,refreshIngestion:s,refreshCorpusLifecycle:o,refreshEmbeddings:i,refreshReindex:c,intervalMs:l}){(async()=>{try{await t(async()=>{await Promise.all([a({showWheel:!1,reportError:!1}),s({showWheel:!1,reportError:!1}),o==null?void 0:o(),i==null?void 0:i(),c==null?void 0:c()])})}catch(k){n(we(k),"error")}})();let d=null,g=l??Ut;function $(){const k=e.state.selectedSession;return k?ht(String(k.status||""))?!0:(k.documents||[]).some(b=>b.status==="in_progress"||b.status==="processing"||b.status==="extracting"||b.status==="etl"||b.status==="writing"||b.status==="gates"):!1}function v(){const k=l??($()?Ts:Ut);d!==null&&k===g||(d!==null&&window.clearInterval(d),g=k,d=window.setInterval(()=>{a({showWheel:!1,reportError:!1}),s({showWheel:!1,reportError:!1,focusSessionId:e.getFocusedRunningSessionId()}),o==null||o(),i==null||i(),c==null||c(),l||v()},g))}return v(),()=>{d!==null&&(window.clearInterval(d),d=null)}}function hn(){const e={activeTab:Kn(),corpora:[],selectedCorpus:"autogenerar",sessions:[],selectedSessionId:Yn(),selectedSession:null,pendingFiles:[],intake:[],reviewPlan:null,preflightRunId:0,mutating:!1,folderUploadProgress:null,folderRelativePaths:new Map,rejectedArtifacts:[],preflightManifest:null,preflightScanProgress:null};function t(){return e.corpora.find(r=>r.key===e.selectedCorpus)}function n(r){e.activeTab=r,Xn(r)}function a(r){e.corpora=[...r]}function s(r){e.folderUploadProgress=r}function o(r){e.preflightManifest=r}function i(r){e.preflightScanProgress=r}function c(r){e.mutating=r}function l(r){e.pendingFiles=[...r]}function d(r){e.intake=[...r]}function g(r){e.reviewPlan=r?{...r,willIngest:[...r.willIngest],bounced:[...r.bounced]}:null}function $(){return e.preflightRunId+=1,e.preflightRunId}function v(r){e.selectedCorpus=r}function k(r){e.selectedSession=r,e.selectedSessionId=(r==null?void 0:r.session_id)||"",Zn((r==null?void 0:r.session_id)||null),r&&(C=!1)}function S(){C=!0,k(null)}function b(r){e.sessions=[...r]}let C=!1;function f(){if(e.selectedSessionId){const r=e.sessions.find(m=>m.session_id===e.selectedSessionId)||null;k(r);return}if(C){k(null);return}k(e.sessions[0]||null)}function p(r){const m=e.sessions.filter(_=>_.session_id!==r.session_id);e.sessions=[r,...m].sort((_,h)=>Date.parse(String(h.updated_at||0))-Date.parse(String(_.updated_at||0))),k(r)}function u(){var r;return ht(String(((r=e.selectedSession)==null?void 0:r.status)||""))?e.selectedSessionId:""}return{state:e,clearSelectionAfterDelete:S,getFocusedRunningSessionId:u,selectedCorpusConfig:t,setActiveTab:n,setCorpora:a,setFolderUploadProgress:s,setMutating:c,setPendingFiles:l,setIntake:d,setReviewPlan:g,bumpPreflightRunId:$,setPreflightManifest:o,setPreflightScanProgress:i,setSelectedCorpus:v,setSelectedSession:k,setSessions:b,syncSelectedSession:f,upsertSession:p}}function Rs(e){const{value:t,unit:n,size:a="md",className:s=""}=e,o=document.createElement("span");o.className=["lia-metric-value",`lia-metric-value--${a}`,s].filter(Boolean).join(" "),o.setAttribute("data-lia-component","metric-value");const i=document.createElement("span");if(i.className="lia-metric-value__number",i.textContent=typeof t=="number"?t.toLocaleString("es-CO"):String(t),o.appendChild(i),n){const c=document.createElement("span");c.className="lia-metric-value__unit",c.textContent=n,o.appendChild(c)}return o}function pt(e){const{label:t,value:n,unit:a,hint:s,size:o="lg",tone:i="neutral",className:c=""}=e,l=document.createElement("div");l.className=["lia-metric-card",`lia-metric-card--${i}`,c].filter(Boolean).join(" "),l.setAttribute("data-lia-component","metric-card");const d=document.createElement("p");if(d.className="lia-metric-card__label",d.textContent=t,l.appendChild(d),l.appendChild(Rs({value:n,unit:a,size:o})),s){const g=document.createElement("p");g.className="lia-metric-card__hint",g.textContent=s,l.appendChild(g)}return l}function qs(e){if(!e)return"sin activar";try{const t=new Date(e);if(Number.isNaN(t.getTime()))return"—";const n=Date.now()-t.getTime(),a=Math.floor(n/6e4);if(a<1)return"hace instantes";if(a<60)return`hace ${a} min`;const s=Math.floor(a/60);return s<24?`hace ${s} h`:`hace ${Math.floor(s/24)} d`}catch{return"—"}}function Ms(e){const t=document.createElement("section");t.className="lia-corpus-overview",t.setAttribute("data-lia-component","corpus-overview");const n=document.createElement("header");n.className="lia-corpus-overview__header";const a=document.createElement("h2");a.className="lia-corpus-overview__title",a.textContent="Corpus activo",n.appendChild(a);const s=document.createElement("p");if(s.className="lia-corpus-overview__subtitle",e.activeGenerationId){const i=document.createElement("code");i.textContent=e.activeGenerationId,s.appendChild(document.createTextNode("Generación ")),s.appendChild(i),s.appendChild(document.createTextNode(` · activada ${qs(e.activatedAt)}`))}else s.textContent="Ninguna generación activa en Supabase.";n.appendChild(s),t.appendChild(n);const o=document.createElement("div");return o.className="lia-corpus-overview__grid",o.appendChild(pt({label:"Documentos servidos",value:e.documents,hint:e.documents>0?`${e.chunks.toLocaleString("es-CO")} chunks indexados`:"—"})),o.appendChild(pt({label:"Grafo de normativa",value:e.graphNodes,unit:"nodos",hint:`${e.graphEdges.toLocaleString("es-CO")} relaciones tipadas`,tone:e.graphOk?"success":"warning"})),o.appendChild(pt({label:"Auditoría del corpus",value:e.auditIncluded,unit:"incluidos",hint:`${e.auditScanned.toLocaleString("es-CO")} escaneados · ${e.auditExcluded.toLocaleString("es-CO")} excluidos`})),o.appendChild(pt({label:"Revisiones pendientes",value:e.auditPendingRevisions,hint:e.auditPendingRevisions===0?"Cuello limpio":"Requieren resolución",tone:e.auditPendingRevisions===0?"success":"warning"})),t.appendChild(o),t}function Ds(e){const{tone:t,pulse:n=!1,ariaLabel:a,className:s=""}=e,o=document.createElement("span");return o.className=["lia-status-dot",`lia-status-dot--${t}`,n?"lia-status-dot--pulse":"",s].filter(Boolean).join(" "),o.setAttribute("data-lia-component","status-dot"),o.setAttribute("role","status"),a&&o.setAttribute("aria-label",a),o}const Bs={active:"active",superseded:"idle",running:"running",queued:"running",failed:"error",pending:"warning"},Wt={active:"Activa",superseded:"Reemplazada",running:"En curso",queued:"En cola",failed:"Falló",pending:"Pendiente"};function _n(e){const{status:t,className:n=""}=e,a=document.createElement("span");a.className=["lia-run-status",`lia-run-status--${t}`,n].filter(Boolean).join(" "),a.setAttribute("data-lia-component","run-status"),a.appendChild(Ds({tone:Bs[t],pulse:t==="running"||t==="queued",ariaLabel:Wt[t]}));const s=document.createElement("span");return s.className="lia-run-status__label",s.textContent=Wt[t],a.appendChild(s),a}function Fs(e){if(!e)return"—";try{const t=new Date(e);return Number.isNaN(t.getTime())?"—":t.toLocaleString("es-CO",{day:"numeric",month:"short",hour:"2-digit",minute:"2-digit"})}catch{return e}}function Os(e,t){const n=document.createElement(t?"button":"div");n.className="lia-generation-row",n.setAttribute("data-lia-component","generation-row"),t&&(n.type="button",n.addEventListener("click",()=>t(e.generationId)));const a=document.createElement("span");a.className="lia-generation-row__id",a.textContent=e.generationId,n.appendChild(a),n.appendChild(_n({status:e.status}));const s=document.createElement("span");s.className="lia-generation-row__date",s.textContent=Fs(e.generatedAt),n.appendChild(s);const o=document.createElement("span");o.className="lia-generation-row__count",o.textContent=`${e.documents.toLocaleString("es-CO")} docs`,n.appendChild(o);const i=document.createElement("span");if(i.className="lia-generation-row__count lia-generation-row__count--muted",i.textContent=`${e.chunks.toLocaleString("es-CO")} chunks`,n.appendChild(i),e.topClass&&e.topClassCount){const c=document.createElement("span");c.className="lia-generation-row__family",c.textContent=`${e.topClass}: ${e.topClassCount.toLocaleString("es-CO")}`,n.appendChild(c)}if(e.subtopicCoverage){const c=e.subtopicCoverage,l=e.documents>0?e.documents:1,d=Math.round(c.docsWithSubtopic/l*100),g=document.createElement("span");g.className="lia-generation-row__subtopic",g.setAttribute("data-lia-component","generation-row-subtopic");const $=c.docsRequiringReview&&c.docsRequiringReview>0?` (${c.docsRequiringReview} por revisar)`:"";g.textContent=`subtema: ${d}%${$}`,n.appendChild(g)}return n}function Gt(e){const{rows:t,emptyMessage:n="Aún no hay generaciones registradas.",errorMessage:a,onSelect:s}=e,o=document.createElement("section");o.className="lia-generations-list",o.setAttribute("data-lia-component","generations-list");const i=document.createElement("header");i.className="lia-generations-list__header";const c=document.createElement("h2");c.className="lia-generations-list__title",c.textContent="Generaciones recientes",i.appendChild(c);const l=document.createElement("p");l.className="lia-generations-list__subtitle",l.textContent="Cada fila es una corrida de python -m lia_graph.ingest publicada en Supabase.",i.appendChild(l),o.appendChild(i);const d=document.createElement("div");if(d.className="lia-generations-list__body",a){const g=document.createElement("p");g.className="lia-generations-list__feedback lia-generations-list__feedback--error",g.textContent=a,d.appendChild(g)}else if(t.length===0){const g=document.createElement("p");g.className="lia-generations-list__feedback",g.textContent=n,d.appendChild(g)}else{const g=document.createElement("div");g.className="lia-generations-list__head-row",["Generación","Estado","Fecha","Documentos","Chunks","Familia principal"].forEach($=>{const v=document.createElement("span");v.className="lia-generations-list__head-cell",v.textContent=$,g.appendChild(v)}),d.appendChild(g),t.forEach($=>d.appendChild(Os($,s)))}return o.appendChild(d),o}const js=[{key:"knowledge_base",label:"knowledge_base/",sublabel:"snapshot Dropbox"},{key:"wip",label:"WIP",sublabel:"Supabase local + Falkor local"},{key:"cloud",label:"Cloud",sublabel:"Supabase cloud + Falkor cloud"}];function zs(e){const{activeStage:t,className:n=""}=e,a=document.createElement("nav");return a.className=["lia-pipeline-flow",n].filter(Boolean).join(" "),a.setAttribute("data-lia-component","pipeline-flow"),a.setAttribute("aria-label","Pipeline de ingestión Lia Graph"),js.forEach((s,o)=>{if(o>0){const d=document.createElement("span");d.className="lia-pipeline-flow__arrow",d.setAttribute("aria-hidden","true"),d.textContent="→",a.appendChild(d)}const i=document.createElement("div");i.className=["lia-pipeline-flow__stage",s.key===t?"lia-pipeline-flow__stage--active":""].filter(Boolean).join(" "),i.setAttribute("data-stage",s.key);const c=document.createElement("span");c.className="lia-pipeline-flow__label",c.textContent=s.label,i.appendChild(c);const l=document.createElement("span");l.className="lia-pipeline-flow__sublabel",l.textContent=s.sublabel,i.appendChild(l),a.appendChild(i)}),a}function Hs(e){const{activeJobId:t,lastRunStatus:n,disabled:a,onTrigger:s}=e,o=document.createElement("section");o.className="lia-run-trigger",o.setAttribute("data-lia-component","run-trigger-card");const i=document.createElement("header");i.className="lia-run-trigger__header";const c=document.createElement("h3");c.className="lia-run-trigger__title",c.textContent="Ingesta completa",i.appendChild(c);const l=document.createElement("p");l.className="lia-run-trigger__subtitle",l.innerHTML="Lee <code>knowledge_base/</code> en disco completo y lo reconstruye desde cero: re-audita, re-clasifica, re-parsea y re-publica los ~1.3k documentos. Tarda 30–40 minutos y cuesta aprox. US$ 6–16 en LLM. Úsala cuando cambie el clasificador, la taxonomía, o quieras un baseline limpio. Para cambios puntuales, prefiere Delta aditivo.",i.appendChild(l);const d=document.createElement("p");d.className="lia-run-trigger__safety",d.innerHTML="<strong>Seguridad:</strong> por defecto escribe a la base local (WIP). Solo promueve a la nube cuando el resultado esté validado — desde la pestaña Promoción.",i.appendChild(d),o.appendChild(i),o.appendChild(zs({activeStage:"wip"}));const g=document.createElement("form");g.className="lia-run-trigger__form",g.setAttribute("novalidate","");const $=Us({name:"supabase_target",legend:"¿Dónde escribir?",options:[{value:"wip",label:"Base local (recomendado)",hint:"Escribe a Supabase y FalkorDB locales en Docker. Ciclo seguro: no afecta la base de producción.",defaultChecked:!0},{value:"production",label:"Producción (nube)",hint:"Escribe directo a Supabase y FalkorDB en la nube. Afecta lo que ven los usuarios hoy."}]});g.appendChild($);const v=Gs({name:"suin_scope",label:"Incluir jurisprudencia SUIN (opcional)",placeholder:"déjalo vacío si solo quieres re-ingerir la base",hint:"Además del corpus base, incluye documentos SUIN-Juriscol descargados. Valores válidos: et · tributario · laboral · jurisprudencia."});g.appendChild(v);const k=Ws([{name:"skip_embeddings",label:"Saltar embeddings",hint:"No recalcula los embeddings al final. Usa esto solo si vas a correrlos manualmente después.",defaultChecked:!1},{name:"auto_promote",label:"Promover a la nube al terminar",hint:"Si la ingesta local termina sin errores, encadena automáticamente una promoción a la nube.",defaultChecked:!1}]);g.appendChild(k);const S=document.createElement("div");S.className="lia-run-trigger__submit-row";const b=document.createElement("button");if(b.type="submit",b.className="lia-button lia-button--primary lia-run-trigger__submit",b.textContent=t?"Ejecutando…":"Reconstruir todo",b.disabled=a,S.appendChild(b),n&&S.appendChild(_n({status:n})),t){const C=document.createElement("code");C.className="lia-run-trigger__job-id",C.textContent=t,S.appendChild(C)}return g.appendChild(S),g.addEventListener("submit",C=>{if(C.preventDefault(),a)return;const f=new FormData(g),p=f.get("supabase_target")||"wip",u=String(f.get("suin_scope")||"").trim(),r=f.get("skip_embeddings")!=null,m=f.get("auto_promote")!=null;s({suinScope:u,supabaseTarget:p==="production"?"production":"wip",autoEmbed:!r,autoPromote:m})}),o.appendChild(g),o}function Us(e){const t=document.createElement("fieldset");t.className="lia-run-trigger__field lia-run-trigger__field--radio";const n=document.createElement("legend");return n.className="lia-run-trigger__legend",n.textContent=e.legend,t.appendChild(n),e.options.forEach(a=>{const s=document.createElement("label");s.className="lia-run-trigger__radio-row";const o=document.createElement("input");o.type="radio",o.name=e.name,o.value=a.value,a.defaultChecked&&(o.defaultChecked=!0),s.appendChild(o);const i=document.createElement("span");i.className="lia-run-trigger__radio-text";const c=document.createElement("span");if(c.className="lia-run-trigger__radio-label",c.textContent=a.label,i.appendChild(c),a.hint){const l=document.createElement("span");l.className="lia-run-trigger__radio-hint",l.textContent=a.hint,i.appendChild(l)}s.appendChild(i),t.appendChild(s)}),t}function Ws(e){const t=document.createElement("fieldset");t.className="lia-run-trigger__field lia-run-trigger__field--checkbox";const n=document.createElement("legend");return n.className="lia-run-trigger__legend",n.textContent="Opciones de corrida",t.appendChild(n),e.forEach(a=>{const s=document.createElement("label");s.className="lia-run-trigger__checkbox-row";const o=document.createElement("input");o.type="checkbox",o.name=a.name,a.defaultChecked&&(o.defaultChecked=!0),s.appendChild(o);const i=document.createElement("span");i.className="lia-run-trigger__checkbox-text";const c=document.createElement("span");if(c.className="lia-run-trigger__checkbox-label",c.textContent=a.label,i.appendChild(c),a.hint){const l=document.createElement("span");l.className="lia-run-trigger__checkbox-hint",l.textContent=a.hint,i.appendChild(l)}s.appendChild(i),t.appendChild(s)}),t}function Gs(e){const t=document.createElement("div");t.className="lia-run-trigger__field lia-run-trigger__field--text";const n=document.createElement("label");n.className="lia-run-trigger__label",n.htmlFor=`lia-run-trigger-${e.name}`,n.textContent=e.label,t.appendChild(n);const a=document.createElement("input");if(a.type="text",a.id=`lia-run-trigger-${e.name}`,a.name=e.name,a.className="lia-input lia-run-trigger__input",a.autocomplete="off",a.spellcheck=!1,e.placeholder&&(a.placeholder=e.placeholder),t.appendChild(a),e.hint){const s=document.createElement("p");s.className="lia-run-trigger__hint",s.textContent=e.hint,t.appendChild(s)}return t}function Js(){const e=document.createElement("article");e.className="lia-adelta-card",e.setAttribute("data-lia-component","additive-delta-card");const t=document.createElement("header");t.className="lia-adelta-card__header";const n=document.createElement("h3");n.className="lia-adelta-card__title",n.textContent="Delta aditivo",t.appendChild(n);const a=document.createElement("p");a.className="lia-adelta-card__body",a.innerHTML="Compara <code>knowledge_base/</code> contra la base ya publicada y procesa <strong>solo los archivos nuevos, modificados o borrados</strong>. Esta tarjeta procesa lo que ya esté en la carpeta — los archivos llegan ahí en el <strong>Paso 1 arriba</strong> (arrastre, Dropbox o editor directo).",t.appendChild(a);const s=document.createElement("p");s.className="lia-adelta-card__steps",s.innerHTML="<strong>Previsualizar</strong> muestra el diff sin escribir nada (segundos para deltas pequeños). <strong>Aplicar</strong> procesa el delta con una confirmación explícita (minutos, no horas). Si cambiaste el prompt del clasificador o la taxonomía, usá <strong>Ingesta completa</strong> a la derecha — el delta aditivo no re-clasifica docs byte-idénticos.",t.appendChild(s),e.appendChild(t);const o=document.createElement("div");return o.className="lia-adelta-card__mount",e.appendChild(o),{element:e,mount:o}}const Jt=["B","KB","MB","GB","TB"];function Vt(e){if(!Number.isFinite(e)||e<=0)return"0 B";let t=0,n=e;for(;n>=1024&&t<Jt.length-1;)n/=1024,t+=1;const a=t===0?Math.round(n):Math.round(n*10)/10;return`${Number.isInteger(a)?`${a}`:a.toFixed(1)} ${Jt[t]}`}function Vs(e){const t=e.toLowerCase();return t.endsWith(".pdf")?"📕":t.endsWith(".docx")||t.endsWith(".doc")?"📘":t.endsWith(".md")?"📄":t.endsWith(".txt")?"📃":"📄"}function Ks(e){const{filename:t,bytes:n,onRemove:a,className:s=""}=e,o=document.createElement("span");o.className=["lia-file-chip",s].filter(Boolean).join(" "),o.setAttribute("data-lia-component","file-chip"),o.title=`${t} - ${Vt(n)}`;const i=document.createElement("span");i.className="lia-file-chip__icon",i.setAttribute("aria-hidden","true"),i.textContent=Vs(t),o.appendChild(i);const c=document.createElement("span");c.className="lia-file-chip__name",c.textContent=t,o.appendChild(c);const l=document.createElement("span");if(l.className="lia-file-chip__size",l.textContent=Vt(n),o.appendChild(l),a){const d=document.createElement("button");d.type="button",d.className="lia-file-chip__remove",d.setAttribute("aria-label",`Quitar ${t}`),d.textContent="x",d.addEventListener("click",g=>{g.preventDefault(),g.stopPropagation(),a()}),o.appendChild(d)}return o}function Kt(e){const{subtopicKey:t,label:n,confidence:a,requiresReview:s,isNew:o,className:i=""}=e;let c="brand";s?c="warning":o&&(c="info");const l=n&&n.trim()?n:t,d=a!=null&&!Number.isNaN(a)?`${l} · ${Math.round(a<=1?a*100:a)}%`:l,g=nt({label:d,tone:c,emphasis:"soft",className:["lia-subtopic-chip",i].filter(Boolean).join(" "),dataComponent:"subtopic-chip"});return g.setAttribute("data-subtopic-key",t),s&&g.setAttribute("data-subtopic-review","true"),o&&g.setAttribute("data-subtopic-new","true"),g}function Xs(e){if(e==null||Number.isNaN(e))return"-";const t=e<=1?e*100:e;return`${Math.round(t)}%`}function Ys(e){if(e==null||Number.isNaN(e))return"neutral";const t=e<=1?e*100:e;return t>=80?"success":t>=50?"warning":"error"}function Zs(e){const{filename:t,bytes:n,detectedTopic:a,topicLabel:s,combinedConfidence:o,requiresReview:i,coercionMethod:c,subtopicKey:l,subtopicLabel:d,subtopicConfidence:g,subtopicIsNew:$,requiresSubtopicReview:v,onRemove:k,className:S=""}=e,b=document.createElement("div");b.className=["lia-intake-file-row",S].filter(Boolean).join(" "),b.setAttribute("data-lia-component","intake-file-row");const C=document.createElement("span");C.className="lia-intake-file-row__file",C.appendChild(Ks({filename:t,bytes:n,onRemove:k})),b.appendChild(C);const f=document.createElement("span");if(f.className="lia-intake-file-row__meta",s||a){const p=xn({label:s||a||"sin tópico",tone:"info",emphasis:"soft",className:"lia-intake-file-row__topic"});a&&p.setAttribute("data-topic",a),f.appendChild(p)}if(o!=null){const p=nt({label:Xs(o),tone:Ys(o),emphasis:"soft",className:"lia-intake-file-row__confidence"});f.appendChild(p)}if(i){const p=nt({label:"requiere revisión",tone:"warning",emphasis:"solid",className:"lia-intake-file-row__review"});p.setAttribute("role","status"),f.appendChild(p)}if(l?f.appendChild(Kt({subtopicKey:l,label:d||null,confidence:g??null,isNew:$,requiresReview:v,className:"lia-intake-file-row__subtopic"})):$&&e.subtopicKey!==void 0&&f.appendChild(Kt({subtopicKey:"(nuevo)",label:d||"subtema propuesto",isNew:!0,className:"lia-intake-file-row__subtopic"})),v&&!l){const p=nt({label:"subtema pendiente",tone:"warning",emphasis:"soft",className:"lia-intake-file-row__subtopic-review"});p.setAttribute("data-subtopic-review","true"),f.appendChild(p)}if(c){const p=document.createElement("span");p.className="lia-intake-file-row__coercion",p.textContent=c,f.appendChild(p)}return b.appendChild(f),b}function vn(e={}){const{size:t="inline",ariaLabel:n,className:a=""}=e,s=document.createElement("span");return s.className=["lia-spinner",`lia-spinner--${t}`,a].filter(Boolean).join(" "),s.setAttribute("data-lia-component","spinner"),s.setAttribute("role","status"),n?s.setAttribute("aria-label",n):s.setAttribute("aria-hidden","true"),s}const Pt="intake-drop-zone.lastBatch";function Qs(){try{if(typeof localStorage>"u")return null;const e=localStorage.getItem(Pt);if(!e)return null;const t=JSON.parse(e);return!t||typeof t!="object"?null:t}catch{return null}}function kt(e){try{if(typeof localStorage>"u")return;if(e==null){localStorage.removeItem(Pt);return}localStorage.setItem(Pt,JSON.stringify(e))}catch{}}const ea=[".md",".txt",".json",".pdf",".docx"];function ta(e){const t=e.toLowerCase();return ea.some(n=>t.endsWith(n))}function na(e){return e.split("/").filter(Boolean).some(n=>n.startsWith("."))}function sa(e){return e.includes("__MACOSX/")||e.startsWith("__MACOSX/")}function aa(e,t){return!(!e||sa(t)||na(t)||e.startsWith(".")||!ta(e))}async function oa(e){const t=[];for(;;){const n=await new Promise(a=>{e.readEntries(s=>a(s||[]))});if(n.length===0)break;t.push(...n)}return t}async function yn(e,t){if(!e)return[];const n=t?`${t}/${e.name}`:e.name;if(e.isFile){if(!e.file)return[];const a=await new Promise(s=>e.file(s));return[{filename:a.name,bytes:a.size,mime:a.type||void 0,relativePath:n,file:a}]}if(e.isDirectory&&e.createReader){const a=e.createReader(),s=await oa(a);return(await Promise.all(s.map(i=>yn(i,n)))).flat()}return[]}async function ia(e){const t=e.items?Array.from(e.items):[];if(t.length>0&&typeof t[0].webkitGetAsEntry=="function"){const a=[];for(const s of t){const o=s.webkitGetAsEntry();if(!o)continue;const i=await yn(o,"");a.push(...i)}return a}return(e.files?Array.from(e.files):[]).map(a=>({filename:a.name,bytes:a.size,mime:a.type||void 0,relativePath:a.name,file:a}))}function ra(e,t){return t?{filename:t.filename||e.filename,mime:t.mime||e.mime,bytes:t.bytes??e.bytes,detectedTopic:t.detected_topic??null,topicLabel:t.topic_label??null,combinedConfidence:t.combined_confidence??null,requiresReview:!!t.requires_review,coercionMethod:t.coercion_method??null,subtopicKey:t.subtopic_key??null,subtopicLabel:t.subtopic_label??null,subtopicConfidence:t.subtopic_confidence??null,subtopicIsNew:!!t.subtopic_is_new,requiresSubtopicReview:!!t.requires_subtopic_review}:{filename:e.filename,mime:e.mime,bytes:e.bytes,detectedTopic:null,topicLabel:null,combinedConfidence:null,requiresReview:!1,coercionMethod:null}}function la(e){const{onIntake:t,onApprove:n,confirmDestructive:a}=e,s=document.createElement("section");s.className="lia-intake-drop-zone",s.setAttribute("data-lia-component","intake-drop-zone");const o=document.createElement("header");o.className="lia-intake-drop-zone__header";const i=document.createElement("h2");i.className="lia-intake-drop-zone__title",i.textContent="Arrastra archivos o carpetas",o.appendChild(i);const c=document.createElement("p");c.className="lia-intake-drop-zone__hint",c.textContent="Acepta .md, .txt, .json, .pdf, .docx. Carpetas se recorren recursivamente. Ocultos y __MACOSX/ se descartan.",o.appendChild(c),s.appendChild(o);const l=document.createElement("div");l.className="lia-intake-drop-zone__zone",l.setAttribute("role","button"),l.setAttribute("tabindex","0"),l.setAttribute("aria-label","Zona de arrastre para ingesta");const d=document.createElement("p");d.className="lia-intake-drop-zone__zone-label",d.textContent="Suelta aquí los archivos para enviarlos al intake",l.appendChild(d),s.appendChild(l);const g=document.createElement("div");g.className="lia-intake-drop-zone__list",g.setAttribute("data-role","intake-file-list"),s.appendChild(g);const $=document.createElement("p");$.className="lia-intake-drop-zone__feedback",$.setAttribute("role","status"),s.appendChild($);const v=document.createElement("div");v.className="lia-intake-drop-zone__actions";const k=document.createElement("button");k.type="button",k.className="lia-button lia-button--ghost lia-intake-drop-zone__clear",k.textContent="Borrar todo",k.hidden=!0,v.appendChild(k);const S=document.createElement("button");S.type="button",S.className="lia-button lia-button--primary lia-intake-drop-zone__approve",S.disabled=!0;const b=document.createElement("span");b.className="lia-intake-drop-zone__approve-label",b.textContent="Aprobar e ingerir",S.appendChild(b),v.appendChild(S),s.appendChild(v);const C={queued:[],lastResponse:null,analyzing:!1};function f(){var E;if(g.replaceChildren(),C.queued.length===0){const x=document.createElement("p");x.className="lia-intake-drop-zone__empty",x.textContent="Sin archivos en cola.",g.appendChild(x);return}const h=new Map;if((E=C.lastResponse)!=null&&E.files)for(const x of C.lastResponse.files)x.filename&&h.set(x.filename,x);C.queued.forEach((x,I)=>{const U=h.get(x.filename),G=Zs({...ra(x,U),onRemove:()=>{C.queued.splice(I,1),f(),p()}});g.appendChild(G)})}function p(){var E,x;const h=((x=(E=C.lastResponse)==null?void 0:E.summary)==null?void 0:x.placed)??0;if(S.classList.remove("lia-intake-drop-zone__approve--analyzing","lia-intake-drop-zone__approve--ready"),S.replaceChildren(),C.analyzing){S.disabled=!0,S.classList.add("lia-intake-drop-zone__approve--analyzing"),S.appendChild(vn({size:"sm",ariaLabel:"Analizando"}));const I=document.createElement("span");I.className="lia-intake-drop-zone__approve-label",I.textContent="Analizando archivos",S.appendChild(I)}else{const I=document.createElement("span");I.className="lia-intake-drop-zone__approve-label",I.textContent="Ir al siguiente paso →",S.appendChild(I),S.disabled=h<=0,h>0&&S.classList.add("lia-intake-drop-zone__approve--ready")}k.hidden=C.queued.length===0&&C.lastResponse==null&&!C.analyzing}function u(){C.queued=[],C.lastResponse=null,C.analyzing=!1,$.textContent="",kt(null),f(),p()}function r(){if(C.queued.length===0&&C.lastResponse==null){kt(null);return}kt({queuedFilenames:C.queued.map(h=>({filename:h.filename,mime:h.mime,bytes:h.bytes,relativePath:h.relativePath})),lastResponse:C.lastResponse,savedAt:new Date().toISOString()})}function m(){var U,G,B;const h=Qs();if(!h||!((((U=h.queuedFilenames)==null?void 0:U.length)??0)>0||!!h.lastResponse))return;C.queued=(h.queuedFilenames??[]).map(j=>({filename:j.filename,mime:j.mime,bytes:j.bytes,relativePath:j.relativePath,content_base64:""})),C.lastResponse=h.lastResponse??null,C.analyzing=!1,f(),p();const x=((B=(G=h.lastResponse)==null?void 0:G.summary)==null?void 0:B.placed)??0,I=h.savedAt?new Date(h.savedAt).toLocaleString("es-CO",{hour:"2-digit",minute:"2-digit",day:"2-digit",month:"short"}):"";x>0?$.textContent=`Sesión previa restaurada (${I}) — ${x} archivo(s) ya estaban clasificados.`:$.textContent=`Sesión previa restaurada (${I}).`}async function _(h){const E=h.filter(x=>aa(x.filename,x.relativePath));if(E.length===0){$.textContent="Ningún archivo elegible en el drop.";return}C.queued=E,C.lastResponse=null,C.analyzing=!0,f(),p(),$.textContent=`Enviando ${E.length} archivo(s) al intake…`;try{const x=await t(E);C.lastResponse=x,C.analyzing=!1,f(),p(),$.textContent=`Intake ok — placed ${x.summary.placed} / deduped ${x.summary.deduped} / rejected ${x.summary.rejected}.`,r()}catch(x){C.lastResponse=null,C.analyzing=!1,p();const I=x instanceof Error?x.message:"intake falló";$.textContent=`Intake falló: ${I}`}}return l.addEventListener("dragenter",h=>{h.preventDefault(),l.classList.add("lia-intake-drop-zone__zone--active")}),l.addEventListener("dragover",h=>{h.preventDefault(),l.classList.add("lia-intake-drop-zone__zone--active")}),l.addEventListener("dragleave",h=>{h.preventDefault(),l.classList.remove("lia-intake-drop-zone__zone--active")}),l.addEventListener("drop",h=>{h.preventDefault(),l.classList.remove("lia-intake-drop-zone__zone--active");const E=h.dataTransfer;E&&(async()=>{const x=await ia(E);await _(x)})()}),S.addEventListener("click",()=>{var E;if(S.disabled)return;const h=(E=C.lastResponse)==null?void 0:E.batch_id;h&&n&&n(h)}),k.addEventListener("click",()=>{var U;if(C.queued.length===0&&C.lastResponse==null)return;let h,E;if(C.analyzing)h="¿Borrar mientras procesamos?",E="Estamos procesando tus archivos. ¿Estás seguro que quieres borrar todo? El servidor seguirá procesando los archivos que ya recibió; esto solo limpia la vista local.";else if(C.lastResponse!=null){const G=((U=C.lastResponse.summary)==null?void 0:U.placed)??0;h="¿Borrar la vista del batch?",E=`Ya procesamos ${G} archivo(s) y están en knowledge_base/. ¿Borrar esta lista de la vista? Los archivos NO se eliminan del corpus — solo se limpia la vista.`}else h="¿Borrar archivos en cola?",E=`¿Borrar los ${C.queued.length} archivo(s) en cola antes de enviarlos?`;(a??(async()=>Promise.resolve(window.confirm(`${h}

${E}`))))({title:h,message:E,confirmLabel:"Borrar todo",cancelLabel:"Cancelar"}).then(G=>{G&&u()})}),f(),p(),m(),s}function wn(e){const{status:t,ariaLabel:n,className:a=""}=e,s=document.createElement("span"),o=["lia-progress-dot",`lia-progress-dot--${t}`,t==="running"?"lia-progress-dot--pulse":"",a].filter(Boolean);return s.className=o.join(" "),s.setAttribute("data-lia-component","progress-dot"),s.setAttribute("role","status"),s.setAttribute("data-status",t),n&&s.setAttribute("aria-label",n),s}const ca=["docs","chunks","edges","embeddings_generated"];function da(e){if(!e)return"";const t=[];for(const n of ca)if(e[n]!=null&&t.push(`${n}: ${e[n]}`),t.length>=3)break;return t.join(", ")}function Xt(e){if(e==null)return null;if(typeof e=="number")return Number.isFinite(e)?e:null;const t=Date.parse(e);return Number.isFinite(t)?t:null}function ua(e,t){const n=Xt(e),a=Xt(t);if(n==null||a==null||a<n)return"";const s=Math.round((a-n)/1e3);if(s<60)return`${s}s`;const o=Math.floor(s/60),i=s%60;return i?`${o}m ${i}s`:`${o}m`}function Yt(e){const{name:t,label:n,status:a,counts:s,startedAt:o,finishedAt:i,errorMessage:c,className:l=""}=e,d=document.createElement("div");d.className=["lia-stage-progress-item",`lia-stage-progress-item--${a}`,l].filter(Boolean).join(" "),d.setAttribute("data-lia-component","stage-progress-item"),d.setAttribute("data-stage-name",t),d.appendChild(wn({status:a,ariaLabel:n}));const g=document.createElement("span");g.className="lia-stage-progress-item__label",g.textContent=n,d.appendChild(g);const $=da(s);if($){const k=document.createElement("span");k.className="lia-stage-progress-item__counts",k.textContent=$,d.appendChild(k)}const v=ua(o,i);if(v){const k=document.createElement("span");k.className="lia-stage-progress-item__duration",k.textContent=v,d.appendChild(k)}if(a==="failed"&&c){const k=document.createElement("p");k.className="lia-stage-progress-item__error",k.textContent=c,k.setAttribute("role","alert"),d.appendChild(k)}return d}const Zt=[{name:"coerce",label:"Coerce"},{name:"audit",label:"Audit"},{name:"chunk",label:"Chunk"},{name:"sink",label:"Sink"},{name:"falkor",label:"FalkorDB"},{name:"embeddings",label:"Embeddings"}];function pa(e){return e==="running"||e==="done"||e==="failed"||e==="pending"?e:"pending"}function Qt(e,t,n){return{name:e,label:t,status:pa(n==null?void 0:n.status),counts:(n==null?void 0:n.counts)??null,startedAt:(n==null?void 0:n.started_at)??null,finishedAt:(n==null?void 0:n.finished_at)??null,errorMessage:(n==null?void 0:n.error)??null}}function ma(){const e=document.createElement("section");e.className="lia-run-progress-timeline",e.setAttribute("data-lia-component","run-progress-timeline");const t=document.createElement("header");t.className="lia-run-progress-timeline__header";const n=document.createElement("h3");n.className="lia-run-progress-timeline__title",n.textContent="Progreso de la corrida",t.appendChild(n),e.appendChild(t);const a=document.createElement("div");a.className="lia-run-progress-timeline__list";const s=new Map;Zt.forEach(({name:i,label:c})=>{const l=document.createElement("div");l.className="lia-run-progress-timeline__item",l.setAttribute("data-stage",i),l.appendChild(Yt(Qt(i,c,void 0))),a.appendChild(l),s.set(i,l)}),e.appendChild(a);function o(i){const c=(i==null?void 0:i.stages)||{};Zt.forEach(({name:l,label:d})=>{const g=s.get(l);if(!g)return;const $=c[l]||void 0;g.replaceChildren(Yt(Qt(l,d,$)))})}return{element:e,update:o}}function ga(e={}){const{initialLines:t=[],autoScroll:n=!0,onCopy:a=null,summaryLabel:s="Log de ejecución",className:o=""}=e,i=document.createElement("div");i.className=["lia-log-tail-viewer",o].filter(Boolean).join(" "),i.setAttribute("data-lia-component","log-tail-viewer");const c=document.createElement("div");c.className="lia-log-tail-viewer__toolbar";const l=document.createElement("button");l.type="button",l.className="lia-log-tail-viewer__copy",l.textContent="Copiar",l.setAttribute("aria-label","Copiar log"),c.appendChild(l);const d=document.createElement("details");d.className="lia-log-tail-viewer__details",d.open=!0;const g=document.createElement("summary");g.className="lia-log-tail-viewer__summary",g.textContent=s,d.appendChild(g);const $=document.createElement("pre");$.className="lia-log-tail-viewer__body",$.textContent=t.join(`
`),d.appendChild($),i.appendChild(c),i.appendChild(d);const v={lines:[...t]},k=()=>{n&&($.scrollTop=$.scrollHeight)},S=()=>{$.textContent=v.lines.join(`
`),k()},b=f=>{!f||f.length===0||(v.lines.push(...f),S())},C=()=>{v.lines=[],$.textContent=""};return l.addEventListener("click",()=>{var u;const f=v.lines.join(`
`),p=(u=globalThis.navigator)==null?void 0:u.clipboard;p&&typeof p.writeText=="function"&&p.writeText(f),a&&a()}),n&&k(),{element:i,appendLines:b,clear:C}}function fa(e={}){const{initialLines:t=[],onCopy:n=null,summaryLabel:a="Log de ejecución"}=e,s=document.createElement("section");s.className="lia-run-log-console",s.setAttribute("data-lia-component","run-log-console");const o=document.createElement("header");o.className="lia-run-log-console__header";const i=document.createElement("h3");i.className="lia-run-log-console__title",i.textContent="Log en vivo",o.appendChild(i);const c=document.createElement("p");c.className="lia-run-log-console__subtitle",c.textContent="Streaming del archivo artifacts/jobs/<job>.log — se actualiza cada 1.5s.",o.appendChild(c),s.appendChild(o);const l=ga({initialLines:t,autoScroll:!0,onCopy:n,summaryLabel:a,className:"lia-run-log-console__viewer"});return s.appendChild(l.element),{element:s,appendLines:l.appendLines,clear:l.clear}}function ba(e,t){const n=document.createElement("div");n.className="lia-adelta-modal__backdrop",n.setAttribute("role","dialog"),n.setAttribute("aria-modal","true"),n.setAttribute("aria-label","Confirmar aplicación del delta");const a=document.createElement("div");a.className="lia-adelta-modal";const s=document.createElement("h3");s.className="lia-adelta-modal__title",s.textContent="Confirmar aplicación";const o=document.createElement("p");o.className="lia-adelta-modal__body";const i=e.counts??{added:0,modified:0,removed:0};o.textContent=`Aplicar delta ${e.deltaId??"(pendiente)"} con +${i.added} / ~${i.modified} / -${i.removed} cambios. Esto afecta producción.`;const c=document.createElement("div");c.className="lia-adelta-modal__actions";const l=Ze({label:"Cancelar",tone:"ghost",onClick:()=>n.remove()}),d=Ze({label:"Aplicar delta",tone:"primary",onClick:()=>{n.remove(),t()}});return c.append(l,d),a.append(s,o,c),n.appendChild(a),n}function ha(e,t){const n=document.createElement("div");n.className="lia-adelta-actions",n.setAttribute("data-lia-component","additive-delta-actions");const a=Ze({label:"Previsualizar",tone:"secondary",onClick:()=>t.onPreview()}),s=Ze({label:"Aplicar",tone:"primary",disabled:!0}),o=Ze({label:"Cancelar",tone:"destructive",onClick:()=>t.onCancel()}),i=Ze({label:"Nuevo delta",tone:"ghost",onClick:()=>t.onReset()});s.addEventListener("click",()=>{const d=c;d.state==="previewed"&&document.body.appendChild(ba(d,()=>{s.disabled=!0,s.classList.add("is-pending"),t.onApply()}))}),n.append(a,s,o,i);let c=e;function l(d){c=d;const{state:g}=d;a.disabled=g==="running"||g==="pending",s.disabled=g!=="previewed",s.classList.toggle("is-pending",g==="pending"),o.hidden=g!=="running"&&g!=="pending",i.hidden=g!=="terminal"}return l(e),{element:n,update:l}}const $t=3;function _a(e){const t=document.createElement("article");t.className=`lia-adelta-bucket lia-adelta-bucket--${e.tone}`,t.setAttribute("data-lia-component","additive-delta-bucket"),t.setAttribute("data-bucket",e.key);const n=document.createElement("header");n.className="lia-adelta-bucket__header";const a=document.createElement("h4");a.className="lia-adelta-bucket__title",a.textContent=e.title;const s=document.createElement("span");s.className="lia-adelta-bucket__count",s.textContent=String(e.count),n.append(a,s);const o=document.createElement("p");o.className="lia-adelta-bucket__body",o.textContent=e.description;const i=document.createElement("div");i.className="lia-adelta-bucket__chips";const c=e.samples.slice(0,$t);for(const l of c)i.appendChild(nt({label:l.label,tone:e.tone}));return e.samples.length>$t&&i.appendChild(nt({label:`+${e.samples.length-$t} más`,tone:"neutral"})),t.append(n,o,i),t}function va(e){var o,i,c;const t=document.createElement("section");if(t.className="lia-adelta-banner",t.setAttribute("data-lia-component","additive-delta-banner"),t.setAttribute("aria-label","Resumen del delta aditivo"),e.isEmpty){const l=document.createElement("div");l.className="lia-adelta-banner__empty";const d=document.createElement("h3");d.className="lia-adelta-banner__empty-title",d.textContent="Sin cambios detectados";const g=document.createElement("p");g.className="lia-adelta-banner__empty-body",g.textContent="La base ya coincide con el corpus en disco. No hay nada que aplicar.",l.append(d,g),t.appendChild(l)}else{const l=[{key:"added",title:"Agregados",tone:"success",count:e.counts.added,samples:((o=e.samples)==null?void 0:o.added)??[],description:"Documentos nuevos que entrarán al corpus."},{key:"modified",title:"Modificados",tone:"warning",count:e.counts.modified,samples:((i=e.samples)==null?void 0:i.modified)??[],description:"Documentos con cambios de contenido o clasificación."},{key:"removed",title:"Retirados",tone:"error",count:e.counts.removed,samples:((c=e.samples)==null?void 0:c.removed)??[],description:"Documentos que ya no existen en disco."},{key:"unchanged",title:"Sin cambios",tone:"neutral",count:e.counts.unchanged,samples:[],description:"Documentos que no requieren re-procesamiento."}],d=document.createElement("div");d.className="lia-adelta-banner__grid";for(const g of l)d.appendChild(_a(g));t.appendChild(d)}const n=document.createElement("footer");n.className="lia-adelta-banner__footer";const a=document.createElement("code");a.className="lia-adelta-banner__delta-id",a.textContent=`delta_id=${e.deltaId}`;const s=document.createElement("code");return s.className="lia-adelta-banner__baseline",s.textContent=`baseline=${e.baselineGenerationId}`,n.append(a,s),t.appendChild(n),t}function ya(e){const t=document.createElement("section");t.className="lia-adelta-feeler",t.setAttribute("data-lia-component","additive-delta-activity-feeler"),t.setAttribute("aria-live","polite");const n=document.createElement("header");n.className="lia-adelta-feeler__header";const a=document.createElement("span");a.className="lia-adelta-feeler__spinner",a.appendChild(vn({size:"md",ariaLabel:"Procesando"}));const s=document.createElement("div");s.className="lia-adelta-feeler__title-wrap";const o=document.createElement("h3");o.className="lia-adelta-feeler__title",o.textContent=e.title;const i=document.createElement("code");i.className="lia-adelta-feeler__run-id",i.hidden=!0;const c=document.createElement("span");c.className="lia-adelta-feeler__elapsed",c.textContent="00:00",s.append(o,i,c),n.append(a,s),t.appendChild(n);const l=document.createElement("p");l.className="lia-adelta-feeler__body",l.textContent=e.body,t.appendChild(l);const d=document.createElement("p");d.className="lia-adelta-feeler__live",d.hidden=!0,t.appendChild(d);const g=document.createElement("p");g.className="lia-adelta-feeler__hint",g.textContent="Puedes cambiar de pestaña — el trabajo sigue corriendo en el servidor.",t.appendChild(g);const $=Date.now();function v(){const b=Math.max(0,Math.floor((Date.now()-$)/1e3)),C=String(Math.floor(b/60)).padStart(2,"0"),f=String(b%60).padStart(2,"0");c.textContent=`${C}:${f}`}v();const k=setInterval(v,1e3);function S(b){const C=Math.max(0,Math.floor(b.classified??0)),f=b.classifierInputCount??null,p=b.prematchedCount??null;if(C<=0&&!b.lastFilename&&f==null){d.hidden=!0,d.textContent="";return}d.hidden=!1;const u=(b.lastFilename??"").split("/").pop()??"",r=f!=null?String(f):"~1.300",m=p!=null&&p>0?` — ${p} saltados por shortcut`:"";u?d.textContent=`Clasificados ${C} de ${r}${m} — último: ${u}`:d.textContent=`Clasificados ${C} de ${r}${m}`}return{element:t,setLiveProgress:S,destroy:()=>clearInterval(k)}}const tt=["queued","parsing","supabase","falkor","finalize"],en={queued:"En cola",parsing:"Clasificando",supabase:"Supabase",falkor:"FalkorDB",finalize:"Finalizando",completed:"Completado",failed:"Falló",cancelled:"Cancelado"};function wa(e,t){if(e==="failed"||e==="cancelled"){const s=tt.indexOf(e==="failed"||e==="cancelled"?"finalize":e);return tt.indexOf(t)<=s?"failed":"pending"}if(e==="completed")return"done";const n=tt.indexOf(e),a=tt.indexOf(t);return a<n?"done":a===n?"running":"pending"}function ka(e){if(!e)return"sin heartbeat";const t=Date.parse(e);if(Number.isNaN(t))return"sin heartbeat";const n=Math.max(0,Math.floor((Date.now()-t)/1e3));if(n<5)return"hace un instante";if(n<60)return`hace ${n}s`;const a=Math.floor(n/60);return a<60?`hace ${a} min`:`hace ${Math.floor(a/60)} h`}function $a(e){switch(e){case"connecting":return"Conectando…";case"connected":return"En vivo";case"reconnecting":return"Reconectando…";case"polling":return"Sondeando (fallback)";case"closed":return"Desconectado"}}function Ca(e){const t=document.createElement("section");t.className="lia-adelta-progress",t.setAttribute("data-lia-component","additive-delta-progress"),t.setAttribute("aria-live","polite");const n=document.createElement("header");n.className="lia-adelta-progress__header";const a=document.createElement("div");a.className="lia-adelta-progress__title-wrap";const s=document.createElement("h3");s.className="lia-adelta-progress__title",s.textContent="Aplicando delta";const o=document.createElement("span");o.className="lia-adelta-progress__elapsed",o.textContent="iniciado hace 00:00",a.append(s,o);const i=document.createElement("code");i.className="lia-adelta-progress__job";const c=document.createElement("span");c.className="lia-adelta-progress__sse",n.append(a,i,c);const l=document.createElement("ol");l.className="lia-adelta-progress__stages";const d={queued:document.createElement("li"),parsing:document.createElement("li"),supabase:document.createElement("li"),falkor:document.createElement("li"),finalize:document.createElement("li"),completed:document.createElement("li"),failed:document.createElement("li"),cancelled:document.createElement("li")},g={};for(const r of tt){const m=d[r];m.className="lia-adelta-progress__stage";const _=wn({status:"pending",ariaLabel:en[r]});g[r]=_;const h=document.createElement("span");h.className="lia-adelta-progress__stage-label",h.textContent=en[r],m.append(_,h),l.appendChild(m)}const $=document.createElement("div");$.className="lia-adelta-progress__bar",$.setAttribute("role","progressbar"),$.setAttribute("aria-valuemin","0"),$.setAttribute("aria-valuemax","100");const v=document.createElement("div");v.className="lia-adelta-progress__bar-fill",$.appendChild(v);const k=document.createElement("footer");k.className="lia-adelta-progress__footer";const S=document.createElement("span");S.className="lia-adelta-progress__heartbeat";const b=document.createElement("span");b.className="lia-adelta-progress__cancel-note",k.append(S,b),t.append(n,l,$,k);function C(r){i.textContent=r.jobId?`job_id=${r.jobId}`:"",c.textContent=$a(r.sseStatus),c.dataset.status=r.sseStatus;for(const _ of tt){const h=g[_];if(!h)continue;const E=wa(r.stage,_);h.className=`lia-progress-dot lia-progress-dot--${E}`+(E==="running"?" lia-progress-dot--pulse":""),h.setAttribute("data-status",E)}const m=Math.max(0,Math.min(100,Math.round(r.progressPct)));v.style.width=`${m}%`,$.setAttribute("aria-valuenow",String(m)),S.textContent=`Último latido del servidor: ${ka(r.lastHeartbeatAt)}`,b.textContent=r.cancelRequested?"Cancelación solicitada — finalizará en el próximo punto seguro.":""}const f=Date.now();function p(){const r=Math.max(0,Math.floor((Date.now()-f)/1e3)),m=String(Math.floor(r/60)).padStart(2,"0"),_=String(r%60).padStart(2,"0");o.textContent=`iniciado hace ${m}:${_}`}p();const u=setInterval(p,1e3);return C(e),{element:t,update:C,destroy:()=>clearInterval(u)}}function Sa(e){var n,a;if(e.stage==="cancelled")return{variant:"navy",title:"Delta cancelado",icon:"✕"};if(e.stage==="failed")return{variant:"danger",title:"Delta falló",icon:"!"};const t=(((n=e.report)==null?void 0:n.new_chunks_count)??((a=e.report)==null?void 0:a.chunks_written)??0)>0;return{variant:t?"warning":"success",title:t?"Delta completado — pendiente embeddings":"Delta completado",icon:"✓"}}function Ea(e){const t=e.report??{},n=Number(t.documents_added??0),a=Number(t.documents_modified??0),s=Number(t.documents_retired??0);return`Se procesaron ${n} nuevos, ${a} modificados y ${s} retirados. Ediciones de chunks: +${t.chunks_written??0} / -${t.chunks_deleted??0}. Aristas: +${t.edges_written??0} / -${t.edges_deleted??0}.`}function Na(e){return navigator.clipboard?navigator.clipboard.writeText(e).then(()=>!0).catch(()=>!1):Promise.resolve(!1)}function Aa(e){var c,l,d,g,$,v;const t=Sa(e),n=document.createElement("section");n.className=`lia-adelta-terminal lia-adelta-terminal--${t.variant}`,n.setAttribute("data-lia-component","additive-delta-terminal"),n.setAttribute("data-stage",e.stage),n.setAttribute("role","status"),n.setAttribute("aria-live","polite");const a=document.createElement("header");a.className="lia-adelta-terminal__header";const s=document.createElement("span");s.className="lia-adelta-terminal__icon",s.textContent=t.icon,s.setAttribute("aria-hidden","true");const o=document.createElement("h3");o.className="lia-adelta-terminal__title",o.textContent=t.title;const i=document.createElement("code");if(i.className="lia-adelta-terminal__delta-id",i.textContent=e.deltaId,a.append(s,o,i),n.appendChild(a),e.stage==="completed"){const k=document.createElement("p");k.className="lia-adelta-terminal__summary",k.textContent=Ea(e),n.appendChild(k);const S=Number(((c=e.classifierSummary)==null?void 0:c.degraded_n1_only)??0),b=Number(((l=e.classifierSummary)==null?void 0:l.classified_new_count)??0);if(S>0){const f=document.createElement("p");f.className="lia-adelta-terminal__degraded",f.setAttribute("data-degraded-count",String(S));const p=b>0?b:S;f.textContent=`${S} de ${p} documentos clasificados quedaron con requires_subtopic_review=true (verdicto N1 solamente). Causa típica: backpressure de TPM en Gemini o casos genuinamente ambiguos. Revisa esos doc_ids antes de dar el ingest por cerrado.`,n.appendChild(f)}if((((d=e.report)==null?void 0:d.new_chunks_count)??((g=e.report)==null?void 0:g.chunks_written)??0)>0){const f=document.createElement("div");f.className="lia-adelta-terminal__callout";const p=document.createElement("p");p.className="lia-adelta-terminal__callout-body";const u=(($=e.report)==null?void 0:$.new_chunks_count)??((v=e.report)==null?void 0:v.chunks_written)??0;p.textContent=`${u} chunks nuevos pendientes de embedding — la calidad de retrieval está degradada hasta que corras la actualización.`;const r=document.createElement("code");r.className="lia-adelta-terminal__cmd",r.textContent="make phase2-embed-backfill";const m=Ze({label:"Copiar comando",tone:"secondary",onClick:()=>{Na("make phase2-embed-backfill").then(_=>{m.classList.toggle("is-copied",_),m.querySelector(".lia-btn__label").textContent=_?"Copiado ✓":"Copiar comando"})}});f.append(p,r,m),n.appendChild(f)}}else if(e.stage==="failed"){const k=document.createElement("p");k.className="lia-adelta-terminal__summary",k.textContent="La aplicación del delta se detuvo. La parity con Falkor puede estar desfasada; revisa los eventos antes de reintentar.";const S=document.createElement("pre");S.className="lia-adelta-terminal__error",S.textContent=`${e.errorClass??"unknown_error"}: ${e.errorMessage??"(sin mensaje)"}`,n.append(k,S)}else{const k=document.createElement("p");k.className="lia-adelta-terminal__summary",k.textContent="El operador canceló el delta en un punto seguro. Los cambios parciales no se revierten automáticamente; inspecciona el reporte antes de continuar.",n.appendChild(k)}return n}const Ct="additive-delta.jobId";function Pa(e){const t=e??(typeof localStorage<"u"?localStorage:null);return t?{get:()=>{try{const n=t.getItem(Ct);return n&&n.trim()?n.trim():null}catch{return null}},set:n=>{try{n&&n.trim()&&t.setItem(Ct,n.trim())}catch{}},clear:()=>{try{t.removeItem(Ct)}catch{}}}:{get:()=>null,set:()=>{},clear:()=>{}}}function Ia(e){const{serverLiveJobId:t,localJobId:n,store:a}=e;return t?(n!==t&&a.set(t),t):n||null}const xa=new Set(["completed","failed","cancelled"]);function La(e){try{const t=JSON.parse(e);if(!t||typeof t!="object")return null;const n=t,a=String(n.job_id??"");return a?{jobId:a,stage:String(n.stage??"queued"),progressPct:Number(n.progress_pct??0)||0,lastHeartbeatAt:n.last_heartbeat_at??null,cancelRequested:!!(n.cancel_requested??!1),reportJson:n.report_json??null,errorClass:n.error_class??null,errorMessage:n.error_message??null}:null}catch{return null}}function Ta(e,t,n={}){const a=n.maxReconnects??0,s=n.pollingIntervalMs??2e3,o=n.eventSourceFactory??(m=>new EventSource(m)),i=n.fetchImpl??fetch.bind(globalThis),c=`/api/ingest/additive/events?job_id=${encodeURIComponent(e)}`,l=`/api/ingest/additive/status?job_id=${encodeURIComponent(e)}`;let d=0,g=!1,$=null,v=null,k=null;function S(m){var _;(_=t.onStatusChange)==null||_.call(t,m)}function b(m){var _;xa.has(m.stage)&&((_=t.onTerminal)==null||_.call(t,m),r())}function C(m){const _=La(m);_&&(t.onSnapshot(_),b(_))}function f(){if(S("polling"),v)return;const m=async()=>{if(!g)try{const _=typeof window<"u"?window.localStorage.getItem("lia_access_token"):null,h={};_&&_.trim()&&(h.Authorization=`Bearer ${_.trim()}`);const E=await i(l,{headers:h});if(!E.ok)return;const x=await E.json();if(!x||!x.job)return;C(JSON.stringify(x.job))}catch{}};m(),v=setInterval(m,s)}function p(){if(!g){S(d===0?"connecting":"reconnecting");try{$=o(c)}catch{u();return}$.addEventListener("open",()=>{d=0,S("connected")}),$.addEventListener("snapshot",m=>{C(m.data)}),$.addEventListener("message",m=>{C(m.data)}),$.addEventListener("error",()=>{g||($==null||$.close(),$=null,u())})}}function u(){if(g)return;if(d>=a){f();return}d+=1;const m=Math.min(3e4,500*2**(d-1));S("reconnecting"),k=setTimeout(()=>p(),m)}function r(){g||(g=!0,$&&($.close(),$=null),v&&(clearInterval(v),v=null),k&&(clearTimeout(k),k=null),S("closed"))}return p(),{close:r}}const Ra=["completed","failed","cancelled"];function tn(e){return Ra.includes(e)}function qa(e){var a,s,o;const t=((a=e.reportJson)==null?void 0:a.sink_result)??null,n=((s=e.reportJson)==null?void 0:s.classifier_summary)??null;return{stage:e.stage,deltaId:((o=e.reportJson)==null?void 0:o.delta_id)??e.jobId,report:t,classifierSummary:n,errorClass:e.errorClass,errorMessage:e.errorMessage}}function Ma(e){const t=e.target??"production";e.fetchImpl??fetch.bind(globalThis);const n=Pa(e.storage),a=e.rootElement;a.classList.add("lia-adelta-panel"),a.setAttribute("data-lia-component","additive-delta-controller");const s=document.createElement("div");s.className="lia-adelta-panel__banner";const o=document.createElement("div");o.className="lia-adelta-panel__progress";const i=document.createElement("div");i.className="lia-adelta-panel__terminal";const c=ha({state:"idle"},{onPreview:()=>void _(),onApply:()=>void h(),onCancel:()=>void E(),onReset:()=>r()});a.append(c.element,s,o,i);let l=null,d=null,g=null,$=null,v=null,k=null,S=null,b=!1,C=null;function f(){C&&(clearInterval(C),C=null),g&&(g.destroy(),g=null)}function p(w,M,D=!1){if(f(),g=ya({title:w,body:M}),s.replaceChildren(g.element),D){const Z=async()=>{if(g)try{const y=await Ne("/api/ingest/additive/preview-progress");if(!(y!=null&&y.available))return;g.setLiveProgress({classified:y.classified_since_last_run_boundary??0,lastFilename:y.last_filename??null})}catch{}};Z(),C=setInterval(Z,3e3)}}function u(w,M){c.update({state:w,deltaId:(M==null?void 0:M.deltaId)??(l==null?void 0:l.delta_id),counts:(M==null?void 0:M.counts)??(l?{added:l.summary.added,modified:l.summary.modified,removed:l.summary.removed}:void 0)})}function r(){f(),k=null,S=null,b=!1,v=null,s.replaceChildren(),o.replaceChildren(),i.replaceChildren(),l=null,d&&(d.destroy(),d=null),$&&($.close(),$=null),n.clear(),u("idle")}function m(w){var M;(M=e.onError)==null||M.call(e,w)}async function _(){var w,M,D;k="preview",u("pending"),p("Analizando delta…","Lia compara los archivos de knowledge_base/ contra la base ya publicada por content_hash. Solo re-clasifica los archivos genuinamente nuevos o editados — los demás reutilizan su fingerprint anterior. Rápido para deltas pequeños.",!0);try{const{response:Z,data:y}=await ze("/api/ingest/additive/preview",{target:t});if(k!=="preview")return;if(!Z.ok||!y){f(),k=null,m(`Preview falló (HTTP ${Z.status}).`),u("idle");return}f(),k=null,l=y;const q={deltaId:y.delta_id,baselineGenerationId:y.baseline_generation_id,counts:{added:y.summary.added,modified:y.summary.modified,removed:y.summary.removed,unchanged:y.summary.unchanged},samples:{added:(((w=y.sample_chips)==null?void 0:w.added)??[]).map(N=>({label:N})),modified:(((M=y.sample_chips)==null?void 0:M.modified)??[]).map(N=>({label:N})),removed:(((D=y.sample_chips)==null?void 0:D.removed)??[]).map(N=>({label:N}))},isEmpty:!!y.summary.is_empty};s.replaceChildren(va(q)),o.replaceChildren(),i.replaceChildren(),u(y.summary.is_empty?"previewed-empty":"previewed")}catch(Z){if(k!=="preview")return;f(),k=null,m(String(Z)),u("idle")}}async function h(){if(!l||l.summary.is_empty){m("No hay delta listo para aplicar.");return}k="apply",u("pending"),p("Encolando delta…","Reservando un slot de procesamiento en el servidor y disparando el worker. Esto es rápido (segundos); el procesamiento real arranca inmediatamente después.");try{const{response:w,data:M}=await ze("/api/ingest/additive/apply",{target:t,delta_id:l.delta_id});if(k!=="apply")return;if(w.status===409){const Z=M;m(`Ya hay un delta en curso (${Z.blocking_job_id}). Reattacheando…`),k=null,I(Z.blocking_job_id);return}if(!w.ok||!M){k=null,m(`Apply falló (HTTP ${w.status}).`),u("previewed");return}const D=M;n.set(D.job_id),k=null,I(D.job_id)}catch(w){if(k!=="apply")return;k=null,m(String(w)),u("previewed")}}async function E(){var M;if(b)return;b=!0;const w=x();if(k==="preview"){f(),k=null,b=!1,u("idle"),m("Cancelación en cliente. El clasificador puede seguir corriendo en el servidor — su resultado se descarta.");return}if(k==="apply"&&!w){f(),k=null,b=!1,u(l?"previewed":"idle"),m("Solicitud de apply cancelada antes de encolarse.");return}if(w){try{if(await ze(`/api/ingest/additive/cancel?job_id=${encodeURIComponent(w)}`,{}),d){const D=d.element;D.dataset.cancelRequested="true";const Z=D.dataset.currentStage??"queued",y=parseInt(((M=D.querySelector(".lia-adelta-progress__bar-fill"))==null?void 0:M.style.width)||"0",10)||0;d.update({jobId:w,stage:Z,progressPct:y,lastHeartbeatAt:D.dataset.heartbeat??null,sseStatus:"polling",cancelRequested:!0})}}catch(D){m(`La solicitud de cancelación no pudo enviarse (${String(D)}). Intenta de nuevo o usa Nuevo delta para reiniciar la vista sin tocar el worker.`)}finally{b=!1}return}b=!1,m("No hay operación en curso para cancelar.")}function x(){return S??n.get()}function I(w){f(),k=null,S=w,s.replaceChildren(),i.replaceChildren(),o.replaceChildren(),v={jobId:w,stage:"queued",progressPct:0,lastHeartbeatAt:null,sseStatus:"connecting",cancelRequested:!1},d=Ca(v),o.replaceChildren(d.element),u("running",{deltaId:w,counts:void 0}),$&&$.close(),$=Ta(w,{onSnapshot:M=>G(M),onStatusChange:M=>U(M),onTerminal:M=>B(M)},e.sseOptions??{})}function U(w){!d||!v||(v={...v,sseStatus:w},d.update(v))}function G(w){d&&(v={jobId:w.jobId,stage:w.stage,progressPct:w.progressPct,lastHeartbeatAt:w.lastHeartbeatAt??null,sseStatus:"connected",cancelRequested:w.cancelRequested},d.update(v))}function B(w){if(!tn(w.stage))return;o.replaceChildren(),d&&(d.destroy(),d=null),S=null,b=!1,k=null,v=null;const M=qa(w);i.replaceChildren(Aa(M)),n.clear(),u("terminal")}async function j(){u("idle");try{let w;try{w=await Ne(`/api/ingest/additive/live?target=${encodeURIComponent(t)}`)}catch{w={ok:!1,target:t,job_id:null,job:null}}const M=n.get(),D=Ia({serverLiveJobId:w.job_id,localJobId:M,store:n});if(!D)return;if(w.job_id===D){I(D);return}let Z;try{Z=await Ne(`/api/ingest/additive/status?job_id=${encodeURIComponent(D)}`)}catch{n.clear();return}if(!Z.job){n.clear();return}tn(Z.job.stage)?B({jobId:Z.job.job_id,stage:Z.job.stage,progressPct:Z.job.progress_pct,lastHeartbeatAt:Z.job.last_heartbeat_at,cancelRequested:Z.job.cancel_requested,reportJson:Z.job.report_json,errorClass:Z.job.error_class,errorMessage:Z.job.error_message}):I(D)}catch{}}j();function L(){$&&$.close(),a.replaceChildren()}return{destroy:L}}function Da(e){const t=document.createElement("div");t.className=["lia-segmented",e.className||""].filter(Boolean).join(" "),t.setAttribute("data-lia-component","segmented-control"),t.setAttribute("role","tablist"),e.ariaLabel&&t.setAttribute("aria-label",e.ariaLabel);let n=e.value;const a=[];for(const o of e.options){const i=document.createElement("button");i.type="button",i.className="lia-segmented__option",i.setAttribute("role","tab"),i.setAttribute("data-value",o.value),i.setAttribute("aria-pressed",o.value===n?"true":"false");const c=document.createElement("span");if(c.className="lia-segmented__label",c.textContent=o.label,i.appendChild(c),o.hint){const l=document.createElement("span");l.className="lia-segmented__hint",l.textContent=o.hint,i.appendChild(l)}i.addEventListener("click",()=>{n!==o.value&&(s(o.value),e.onChange(o.value))}),a.push(i),t.appendChild(i)}function s(o){n=o;for(const i of a){const c=i.getAttribute("data-value")||"";i.setAttribute("aria-pressed",c===n?"true":"false")}}return{element:t,setValue:s,value:()=>n}}async function nn(e,t){const{response:n,data:a}=await ze(e,t);if(!n.ok){let s=n.statusText;if(a&&typeof a=="object"){const o=a,i=typeof o.error=="string"?o.error:"",c=typeof o.details=="string"?o.details:"";i&&c?s=`${i} — ${c}`:i?s=i:c&&(s=c)}throw new st(s,n.status,a)}if(!a)throw new st("Empty response",n.status,null);return a}function Ba(e,t={}){const n=e.querySelector("[data-slot=corpus-overview]"),a=e.querySelector("[data-slot=run-trigger]"),s=e.querySelector("[data-slot=generations-list]"),o=e.querySelector("[data-slot=intake-zone]"),i=e.querySelector("[data-slot=progress-timeline]"),c=e.querySelector("[data-slot=log-console]");if(!n||!a||!s)return e.textContent="Sesiones: missing render slots.",{refresh:async()=>{},destroy:()=>{}};const l={activeJobId:null,lastRunStatus:null,pollHandle:null,logCursor:0,lastBatchId:null,autoEmbed:!0,autoPromote:!1,supabaseTarget:"wip",suinScope:""};let d=null,g=null;function $(){a.replaceChildren(Hs({activeJobId:l.activeJobId,lastRunStatus:l.lastRunStatus,disabled:l.activeJobId!==null,onTrigger:({suinScope:y,supabaseTarget:q,autoEmbed:N,autoPromote:T})=>{l.autoEmbed=N,l.autoPromote=T,l.supabaseTarget=q,l.suinScope=y,m({suinScope:y,supabaseTarget:q,autoEmbed:N,autoPromote:T,batchId:null})}}))}const v=t.i18n?y=>sn(t.i18n).confirm({title:y.title,message:y.message,tone:"caution",confirmLabel:y.confirmLabel,cancelLabel:y.cancelLabel}):void 0;function k(){o&&o.replaceChildren(la({onIntake:y=>u(y),onApprove:()=>S(),confirmDestructive:v}))}function S(){var q;const y=((q=e.querySelector("[data-slot=flow-toggle]"))==null?void 0:q.closest("section"))??e.querySelector("[data-slot=flow-toggle]")??null;y&&(y.scrollIntoView({behavior:"smooth",block:"start"}),y.classList.add("is-highlighted"),window.setTimeout(()=>y.classList.remove("is-highlighted"),2400))}function b(){i&&(d=ma(),i.replaceChildren(d.element))}function C(){c&&(g=fa(),c.replaceChildren(g.element))}async function f(){n.replaceChildren(G("overview"));try{const y=await Ne("/api/ingest/state"),q={documents:y.corpus.documents,chunks:y.corpus.chunks,graphNodes:y.graph.nodes,graphEdges:y.graph.edges,graphOk:y.graph.ok,auditScanned:y.audit.scanned,auditIncluded:y.audit.include_corpus,auditExcluded:y.audit.exclude_internal,auditPendingRevisions:y.audit.pending_revisions,activeGenerationId:y.corpus.active_generation_id,activatedAt:y.corpus.activated_at};n.replaceChildren(Ms(q))}catch(y){n.replaceChildren(B("No se pudo cargar el estado del corpus.",y))}}async function p(){s.replaceChildren(G("generations"));try{const q=((await Ne("/api/ingest/generations?limit=20")).generations||[]).map(N=>{const T=N.knowledge_class_counts||{},H=Object.entries(T).sort((V,oe)=>oe[1]-V[1])[0];return{generationId:N.generation_id,status:N.is_active?"active":"superseded",generatedAt:N.generated_at,documents:Number(N.documents)||0,chunks:Number(N.chunks)||0,topClass:H==null?void 0:H[0],topClassCount:H==null?void 0:H[1]}});s.replaceChildren(Gt({rows:q}))}catch(y){s.replaceChildren(Gt({rows:[],errorMessage:`No se pudieron cargar las generaciones: ${j(y)}`}))}}async function u(y){const N={batch_id:null,files:await Promise.all(y.map(async H=>{const V=await r(H.file);return{filename:H.filename,content_base64:V,relative_path:H.relativePath||H.filename}})),options:{mirror_to_dropbox:!1,dropbox_root:null}},T=await nn("/api/ingest/intake",N);return l.lastBatchId=T.batch_id,T}async function r(y){const q=globalThis;if(typeof q.FileReader=="function"){const N=await new Promise((H,V)=>{const oe=new q.FileReader;oe.onerror=()=>V(oe.error||new Error("file read failed")),oe.onload=()=>H(String(oe.result||"")),oe.readAsDataURL(y)}),T=N.indexOf(",");return T>=0?N.slice(T+1):""}if(typeof y.arrayBuffer=="function"){const N=await y.arrayBuffer();return U(N)}return""}async function m(y){l.lastRunStatus="queued",l.logCursor=0,g&&g.clear(),$();try{const q=await nn("/api/ingest/run",{suin_scope:y.suinScope,supabase_target:y.supabaseTarget,auto_embed:y.autoEmbed,auto_promote:y.autoPromote,batch_id:y.batchId});l.activeJobId=q.job_id,l.lastRunStatus="running",$(),_()}catch(q){l.lastRunStatus="failed",l.activeJobId=null,$(),L(`No se pudo iniciar la ingesta: ${j(q)}`)}}function _(){h();const y=i!==null||c!==null;l.pollHandle=window.setInterval(()=>{if(!l.activeJobId){h();return}y?(E(l.activeJobId),x(l.activeJobId)):I(l.activeJobId)},y?1500:4e3)}function h(){l.pollHandle!==null&&(window.clearInterval(l.pollHandle),l.pollHandle=null)}async function E(y){try{const q=await Ne(`/api/ingest/job/${y}/progress`);d&&d.update(q);const N=q.status;(N==="done"||N==="failed")&&(l.lastRunStatus=N==="done"?"active":"failed",l.activeJobId=null,$(),h(),N==="done"&&await Promise.all([f(),p()]))}catch{}}async function x(y){try{const q=await Ne(`/api/ingest/job/${y}/log/tail?cursor=${l.logCursor}&limit=200`);q.lines&&q.lines.length>0&&g&&g.appendLines(q.lines),typeof q.next_cursor=="number"&&(l.logCursor=q.next_cursor)}catch{}}async function I(y){var q;try{const T=(await Ne(`/api/jobs/${y}`)).job;if(!T)return;if(T.status==="completed"){const H=(((q=T.result_payload)==null?void 0:q.exit_code)??1)===0;l.lastRunStatus=H?"active":"failed",l.activeJobId=null,$(),h(),H&&await Promise.all([f(),p()])}else T.status==="failed"&&(l.lastRunStatus="failed",l.activeJobId=null,$(),h())}catch{}}function U(y){const q=new Uint8Array(y),N=32768;let T="";for(let oe=0;oe<q.length;oe+=N){const le=q.subarray(oe,Math.min(q.length,oe+N));T+=String.fromCharCode.apply(null,Array.from(le))}const H=globalThis;if(typeof H.btoa=="function")return H.btoa(T);const V=globalThis.Buffer;return V?V.from(T,"binary").toString("base64"):""}function G(y){const q=document.createElement("div");return q.className=`lia-ingest-skeleton lia-ingest-skeleton--${y}`,q.setAttribute("aria-hidden","true"),q.textContent="Cargando…",q}function B(y,q){const N=document.createElement("div");N.className="lia-ingest-error",N.setAttribute("role","alert");const T=document.createElement("strong");T.textContent=y,N.appendChild(T);const H=document.createElement("p");return H.className="lia-ingest-error__detail",H.textContent=j(q),N.appendChild(H),N}function j(y){return y instanceof Error?y.message:typeof y=="string"?y:"Error desconocido"}function L(y){const q=document.createElement("div");q.className="lia-ingest-toast",q.textContent=y,e.prepend(q),window.setTimeout(()=>q.remove(),4e3)}$(),k(),b(),C(),Promise.all([f(),p()]);const w=e.querySelector("[data-slot=flow-toggle]"),M=(w==null?void 0:w.closest("[data-active-flow]"))??null;if(w&&M){const y=Da({ariaLabel:"Flujo de ingesta",value:"delta",options:[{value:"delta",label:"Delta aditivo",hint:"Rápido · solo lo que cambió"},{value:"full",label:"Ingesta completa",hint:"Lento · reconstruye todo"}],onChange:q=>{M.setAttribute("data-active-flow",q)}});w.replaceChildren(y.element)}let D=null;const Z=e.querySelector("[data-slot=additive-delta]");if(Z){const{element:y,mount:q}=Js();Z.replaceChildren(y),D=Ma({rootElement:q,target:"production",onError:N=>L(N)})}return{async refresh(){await Promise.all([f(),p()])},destroy(){h(),D&&(D.destroy(),D=null)}}}function Fa(e,{i18n:t}){const n=e,a=n.querySelector("#lia-ingest-shell");let s=null;a&&(s=Ba(a,{i18n:t}),window.setInterval(()=>{s==null||s.refresh()},3e4));const o=a!==null,i=n.querySelector("#ops-tab-monitor"),c=n.querySelector("#ops-tab-ingestion"),l=n.querySelector("#ops-tab-control"),d=n.querySelector("#ops-tab-embeddings"),g=n.querySelector("#ops-tab-reindex"),$=n.querySelector("#ops-panel-monitor"),v=n.querySelector("#ops-panel-ingestion"),k=n.querySelector("#ops-panel-control"),S=n.querySelector("#ops-panel-embeddings"),b=n.querySelector("#ops-panel-reindex"),C=n.querySelector("#runs-body"),f=n.querySelector("#timeline"),p=n.querySelector("#timeline-meta"),u=n.querySelector("#cascade-note"),r=n.querySelector("#user-cascade"),m=n.querySelector("#user-cascade-summary"),_=n.querySelector("#technical-cascade"),h=n.querySelector("#technical-cascade-summary"),E=n.querySelector("#refresh-runs"),x=!!(C&&f&&p&&u&&r&&m&&_&&h&&E),I=o?null:re(n,"#ingestion-flash"),U=hn();function G(Ve="",ut="success"){if(I){if(!Ve){I.hidden=!0,I.textContent="",I.removeAttribute("data-tone");return}I.hidden=!1,I.dataset.tone=ut,I.textContent=Ve}}const B=o?null:re(n,"#ingestion-corpus"),j=o?null:re(n,"#ingestion-batch-type"),L=o?null:re(n,"#ingestion-dropzone"),w=o?null:re(n,"#ingestion-file-input"),M=o?null:re(n,"#ingestion-folder-input"),D=o?null:re(n,"#ingestion-pending-files"),Z=o?null:re(n,"#ingestion-overview"),y=o?null:re(n,"#ingestion-refresh"),q=o?null:re(n,"#ingestion-create-session"),N=o?null:re(n,"#ingestion-select-files"),T=o?null:re(n,"#ingestion-select-folder"),H=o?null:re(n,"#ingestion-upload-files"),V=o?null:re(n,"#ingestion-upload-progress"),oe=o?null:re(n,"#ingestion-process-session"),le=o?null:re(n,"#ingestion-auto-process"),be=o?null:re(n,"#ingestion-validate-batch"),Ee=o?null:re(n,"#ingestion-retry-session"),Ae=o?null:re(n,"#ingestion-delete-session"),Ce=o?null:re(n,"#ingestion-session-meta"),K=o?null:re(n,"#ingestion-sessions-list"),ke=o?null:re(n,"#selected-session-meta"),pe=o?null:re(n,"#ingestion-last-error"),Pe=o?null:re(n,"#ingestion-last-error-message"),Me=o?null:re(n,"#ingestion-last-error-guidance"),De=o?null:re(n,"#ingestion-last-error-next"),he=o?null:re(n,"#ingestion-kanban"),Le=o?null:re(n,"#ingestion-log-accordion"),Te=o?null:re(n,"#ingestion-log-body"),de=o?null:re(n,"#ingestion-log-copy"),_e=o?null:re(n,"#ingestion-auto-status"),R=n.querySelector("#ingestion-add-corpus-btn"),W=n.querySelector("#add-corpus-dialog"),se=n.querySelector("#ingestion-bounce-log"),te=n.querySelector("#ingestion-bounce-body"),Q=n.querySelector("#ingestion-bounce-copy");async function fe(Ve){return Ve()}const ae=x?gn({i18n:t,stateController:U,dom:{monitorTabBtn:i,ingestionTabBtn:c,controlTabBtn:l,embeddingsTabBtn:d,reindexTabBtn:g,monitorPanel:$,ingestionPanel:v,controlPanel:k,embeddingsPanel:S,reindexPanel:b,runsBody:C,timelineNode:f,timelineMeta:p,cascadeNote:u,userCascadeNode:r,userCascadeSummary:m,technicalCascadeNode:_,technicalCascadeSummary:h,refreshRunsBtn:E},withThinkingWheel:fe,setFlash:G}):null,ce=o?null:Is({i18n:t,stateController:U,dom:{ingestionCorpusSelect:B,ingestionBatchTypeSelect:j,ingestionDropzone:L,ingestionFileInput:w,ingestionFolderInput:M,ingestionSelectFilesBtn:N,ingestionSelectFolderBtn:T,ingestionUploadProgress:V,ingestionPendingFiles:D,ingestionOverview:Z,ingestionRefreshBtn:y,ingestionCreateSessionBtn:q,ingestionUploadBtn:H,ingestionProcessBtn:oe,ingestionAutoProcessBtn:le,ingestionValidateBatchBtn:be,ingestionRetryBtn:Ee,ingestionDeleteSessionBtn:Ae,ingestionSessionMeta:Ce,ingestionSessionsList:K,selectedSessionMeta:ke,ingestionLastError:pe,ingestionLastErrorMessage:Pe,ingestionLastErrorGuidance:Me,ingestionLastErrorNext:De,ingestionKanban:he,ingestionLogAccordion:Le,ingestionLogBody:Te,ingestionLogCopyBtn:de,ingestionAutoStatus:_e,addCorpusBtn:R,addCorpusDialog:W,ingestionBounceLog:se,ingestionBounceBody:te,ingestionBounceCopy:Q},withThinkingWheel:fe,setFlash:G}),X=n.querySelector("#corpus-lifecycle"),ee=X?an({dom:{container:X},setFlash:G}):null,$e=n.querySelector("#embeddings-lifecycle"),Re=$e?dn({dom:{container:$e},setFlash:G}):null,Ie=n.querySelector("#reindex-lifecycle"),Je=Ie?fn({dom:{container:Ie},setFlash:G,navigateToEmbeddings:()=>{U.setActiveTab("embeddings"),ae==null||ae.renderTabs()}}):null;ae==null||ae.bindEvents(),ce==null||ce.bindEvents(),ee==null||ee.bindEvents(),Re==null||Re.bindEvents(),Je==null||Je.bindEvents(),ae==null||ae.renderTabs(),ce==null||ce.render(),bn({stateController:U,withThinkingWheel:fe,setFlash:G,refreshRuns:(ae==null?void 0:ae.refreshRuns)??(async()=>{}),refreshIngestion:(ce==null?void 0:ce.refreshIngestion)??(async()=>{}),refreshCorpusLifecycle:ee==null?void 0:ee.refresh,refreshEmbeddings:Re==null?void 0:Re.refresh,refreshReindex:Je==null?void 0:Je.refresh})}function Oa(e,{i18n:t}){const n=e,a=n.querySelector("#runs-body"),s=n.querySelector("#timeline"),o=n.querySelector("#timeline-meta"),i=n.querySelector("#cascade-note"),c=n.querySelector("#user-cascade"),l=n.querySelector("#user-cascade-summary"),d=n.querySelector("#technical-cascade"),g=n.querySelector("#technical-cascade-summary"),$=n.querySelector("#refresh-runs");if(!a||!s||!o||!i||!c||!l||!d||!g||!$)return;const v=hn(),k=async C=>C(),S=()=>{},b=gn({i18n:t,stateController:v,dom:{monitorTabBtn:null,ingestionTabBtn:null,controlTabBtn:null,embeddingsTabBtn:null,reindexTabBtn:null,monitorPanel:null,ingestionPanel:null,controlPanel:null,embeddingsPanel:null,reindexPanel:null,runsBody:a,timelineNode:s,timelineMeta:o,cascadeNote:i,userCascadeNode:c,userCascadeSummary:l,technicalCascadeNode:d,technicalCascadeSummary:g,refreshRunsBtn:$},withThinkingWheel:k,setFlash:S});b.bindEvents(),b.renderTabs(),bn({stateController:v,withThinkingWheel:k,setFlash:S,refreshRuns:b.refreshRuns,refreshIngestion:async()=>{}})}const to=Object.freeze(Object.defineProperty({__proto__:null,mountBackstageApp:Oa,mountOpsApp:Fa},Symbol.toStringTag,{value:"Module"}));export{Fa as a,Dn as b,Qa as c,eo as d,to as e,Oa as m,Za as o,Rn as r,Ya as s};
