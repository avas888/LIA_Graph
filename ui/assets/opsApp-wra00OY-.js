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
  `}const Xa=Object.freeze(Object.defineProperty({__proto__:null,renderBackstageShell:Rn,renderIngestionShell:qn,renderOpsShell:Dn,renderPromocionShell:Mn},Symbol.toStringTag,{value:"Module"})),On=2e3;function J(e){return String(e??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#39;")}function ge(e){return(e??0).toLocaleString("es-CO")}function Fn(e){if(!e)return"-";try{return new Date(e).toLocaleDateString("es-CO",{day:"numeric",month:"short",hour:"2-digit",minute:"2-digit",timeZone:"America/Bogota"})}catch{return e}}function Mt(e){if(!e)return"-";const t=Date.parse(e);if(Number.isNaN(t))return e;const n=Math.max(0,Math.floor((Date.now()-t)/1e3));if(n<5)return"ahora";if(n<60)return`hace ${n}s`;const a=Math.floor(n/60),s=n%60;return a<60?`hace ${a}m ${s}s`:`hace ${Math.floor(a/60)}h ${a%60}m`}function je(e){return e?e.length>24?`${e.slice(0,15)}…${e.slice(-8)}`:e:"-"}function Bn(e){return e===void 0?'<span class="ops-dot ops-dot-unknown">●</span>':e?'<span class="ops-dot ops-dot-ok">●</span>':'<span class="ops-dot ops-dot-error">●</span>'}function Dt(e,t){if(!t.available)return`
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
      <div class="corpus-card-row"><span>Embeddings:</span> ${Bn(t.embeddings_complete)} ${t.embeddings_complete?"completos":"incompletos"}</div>
      <div class="corpus-card-sep"></div>
      <div class="corpus-card-row corpus-card-row-sm"><span>normative_base:</span> ${ge(n.normative_base)}</div>
      <div class="corpus-card-row corpus-card-row-sm"><span>interpretative:</span> ${ge(n.interpretative_guidance)}</div>
      <div class="corpus-card-row corpus-card-row-sm"><span>practica_erp:</span> ${ge(n.practica_erp)}</div>
      <div class="corpus-card-sep"></div>
      <div class="corpus-card-row corpus-card-row-sm"><span>${e==="PRODUCTION"?"Activado:":"Actualizado:"}</span> ${J(Fn(t.activated_at))}</div>
    </div>`}function Ot(e,t={}){const{onlyFailures:n=!1}=t,a=(e??[]).filter(s=>n?!s.ok:!0);return a.length===0?"":`
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
    </ol>`}function gt(e){const t=String(e||"").trim();return t?t.replaceAll("_"," "):"-"}function zn(e){return e?e.kind==="audit"?"Audit":e.kind==="rollback"?"Rollback":e.mode==="force_reset"?"Force reset":"Promote":"Promote"}function _t(e){const t=e==null?void 0:e.last_checkpoint;if(!(t!=null&&t.phase))return"-";const n=t.cursor??0,a=t.total??0,s=a>0?(n/a*100).toFixed(1):"0";return`${gt(t.phase)} · ${ge(n)} / ${ge(a)} (${s}%)`}function Ft(e){var a,s;const t=((a=e==null?void 0:e.last_checkpoint)==null?void 0:a.cursor)??(e==null?void 0:e.batch_cursor)??0,n=((s=e==null?void 0:e.last_checkpoint)==null?void 0:s.total)??0;return n<=0?0:Math.min(100,Math.max(0,t/n*100))}function Hn(e){if(!(e!=null&&e.heartbeat_at))return{label:"-",className:""};const t=Math.max(0,(Date.now()-Date.parse(e.heartbeat_at))/1e3);return t<15?{label:"Saludable",className:"hb-healthy"}:t<45?{label:"Lento",className:"hb-slow"}:{label:"Sin respuesta",className:"hb-stale"}}function Un(e,t){var n,a,s,o,i,c;if(e)switch(e.operation_state_code){case"orphaned_queue":return{severity:"red",title:"Orphaned before start",detail:"The request was queued, but the backend worker never started."};case"stalled_resumable":return{severity:"red",title:"Stalled",detail:(n=e.last_checkpoint)!=null&&n.phase?`Backend stalled after ${gt(e.last_checkpoint.phase)}. Resume is available.`:"Backend stalled, but a checkpoint is available to resume."};case"failed_resumable":return{severity:"red",title:"Resumable",detail:e.error||((s=(a=e.failures)==null?void 0:a[0])==null?void 0:s.message)||"The last run failed after writing a checkpoint. Resume is available."};case"completed":return{severity:"green",title:"Completed",detail:e.kind==="audit"?"WIP audit completed. Artifact written.":e.kind==="rollback"?"Rollback completed and verified.":"Promotion completed and verified."};case"running":return{severity:"yellow",title:"Running",detail:e.current_phase?`Backend phase: ${gt(e.current_phase)}.`:e.stage_label?`Stage: ${e.stage_label}.`:"The backend is processing the promotion."};default:return{severity:e.severity??"red",title:e.severity==="yellow"?"Running":"Failed",detail:e.error||((i=(o=e.failures)==null?void 0:o[0])==null?void 0:i.message)||"The operation ended with an error."}}return t!=null&&t.preflight_ready?{severity:"green",title:"Ready",detail:"WIP audit and promotion preflight are green."}:{severity:"red",title:"Blocked",detail:((c=t==null?void 0:t.preflight_reasons)==null?void 0:c[0])||"Production is not ready for a safe promotion."}}function Wn(e){return e?e.kind==="audit"?"WIP Health Audit":e.kind==="rollback"?"Rollback Production":e.mode==="force_reset"?"Force Reset + Promote Production":"Promote WIP to Production":"Promote WIP to Production"}function Bt(e,t){return!t||t.available===!1?`<tr><td>${J(e)}</td><td colspan="2" class="corpus-report-unavail">no disponible</td></tr>`:`
    <tr>
      <td>${J(e)}</td>
      <td><code>${J(je(t.generation_id))}</code></td>
      <td>${ge(t.documents)} docs · ${ge(t.chunks)} chunks</td>
    </tr>`}function jt(e,t){const n=new Set;for(const s of Object.keys((e==null?void 0:e.knowledge_class_counts)??{}))n.add(s);for(const s of Object.keys((t==null?void 0:t.knowledge_class_counts)??{}))n.add(s);return n.size===0?"":[...n].sort().map(s=>{const o=((e==null?void 0:e.knowledge_class_counts)??{})[s]??0,i=((t==null?void 0:t.knowledge_class_counts)??{})[s]??0,c=i-o,r=c>0?"is-positive":c<0?"is-negative":"",d=c>0?`+${ge(c)}`:c<0?ge(c):"—";return`
        <tr class="corpus-report-kc-row">
          <td>${J(s)}</td>
          <td>${ge(o)}</td>
          <td>${ge(i)}</td>
          <td class="corpus-report-delta ${r}">${d}</td>
        </tr>`}).join("")}function Gn(e,t){if(!e||!t)return"-";const n=Date.parse(e),a=Date.parse(t);if(Number.isNaN(n)||Number.isNaN(a))return"-";const s=Math.max(0,Math.floor((a-n)/1e3)),o=Math.floor(s/60),i=s%60;return o===0?`${i}s`:`${o}m ${i}s`}function Jn(e){const t=e==null?void 0:e.promotion_summary;if(!t)return"";const{before:n,after:a,delta:s,plan_result:o}=t,i=((s==null?void 0:s.documents)??0)>0?`+${ge(s==null?void 0:s.documents)}`:ge(s==null?void 0:s.documents),c=((s==null?void 0:s.chunks)??0)>0?`+${ge(s==null?void 0:s.chunks)}`:ge(s==null?void 0:s.chunks),r=((s==null?void 0:s.documents)??0)>0?"is-positive":((s==null?void 0:s.documents)??0)<0?"is-negative":"",d=((s==null?void 0:s.chunks)??0)>0?"is-positive":((s==null?void 0:s.chunks)??0)<0?"is-negative":"",g=n||a?`
      <table class="corpus-report-table">
        <thead>
          <tr><th></th><th>Generación</th><th>Documentos / Chunks</th></tr>
        </thead>
        <tbody>
          ${Bt("Antes",n)}
          ${Bt("Después",a)}
        </tbody>
        ${s?`
        <tfoot>
          <tr>
            <td>Delta</td>
            <td></td>
            <td>
              <span class="corpus-report-delta ${r}">${i} docs</span> ·
              <span class="corpus-report-delta ${d}">${c} chunks</span>
            </td>
          </tr>
        </tfoot>`:""}
      </table>
      ${jt(n,a)?`
      <table class="corpus-report-table corpus-report-table-kc">
        <thead><tr><th>Clase</th><th>Antes</th><th>Después</th><th>Delta</th></tr></thead>
        <tbody>${jt(n,a)}</tbody>
      </table>`:""}`:"",_=o?`
      <div class="corpus-report-grid">
        ${[{label:"Docs staged",key:"docs_staged"},{label:"Docs upserted",key:"docs_upserted"},{label:"Docs new",key:"docs_new"},{label:"Docs removed",key:"docs_removed"},{label:"Chunks new",key:"chunks_new"},{label:"Chunks changed",key:"chunks_changed"},{label:"Chunks removed",key:"chunks_removed"},{label:"Chunks unchanged",key:"chunks_unchanged"},{label:"Chunks embedded",key:"chunks_embedded"}].filter(C=>o[C.key]!==void 0&&o[C.key]!==null).map(C=>`
              <div class="corpus-report-stat">
                <span class="corpus-report-stat-value">${J(String(o[C.key]??"-"))}</span>
                <span class="corpus-report-stat-label">${J(C.label)}</span>
              </div>`).join("")}
      </div>`:"",$=Gn(e==null?void 0:e.started_at,e==null?void 0:e.completed_at);return`
    <div class="corpus-section corpus-report-section">
      <h4>Promotion Report</h4>
      ${g}
      ${_}
      ${$!=="-"?`<p class="corpus-report-duration">Duración: <strong>${J($)}</strong></p>`:""}
    </div>`}function an({dom:e,setFlash:t}){let n=null,a=null,s=null,o="",i="",c=null,r=null,d=!1,g=!1,f=!1,_=!1,$=0,C=null,b=0;function k(O,B){a&&clearTimeout(a),t(O,B);const L=e.container.querySelector(".corpus-toast");L&&(L.hidden=!1,L.dataset.tone=B,L.textContent=O,L.classList.remove("corpus-toast-enter"),L.offsetWidth,L.classList.add("corpus-toast-enter")),a=setTimeout(()=>{const E=e.container.querySelector(".corpus-toast");E&&(E.hidden=!0)},6e3)}function h(O,B,L,E="promote"){return new Promise(M=>{r==null||r.remove();const q=document.createElement("div");q.className="corpus-confirm-overlay",r=q,q.innerHTML=`
        <div class="corpus-confirm-dialog">
          <h3 class="corpus-confirm-title">${J(O)}</h3>
          <div class="corpus-confirm-body">${B}</div>
          <div class="corpus-confirm-actions">
            <button class="corpus-btn corpus-btn-rollback" data-action="cancel">Cancelar</button>
            <button class="corpus-btn ${E==="rollback"?"corpus-btn-rollback":"corpus-btn-promote"}" data-action="confirm">${J(L)}</button>
          </div>
        </div>
      `,document.body.appendChild(q),requestAnimationFrame(()=>q.classList.add("is-visible"));function Z(y){r===q&&(r=null),q.classList.remove("is-visible"),setTimeout(()=>q.remove(),180),M(y)}q.addEventListener("click",y=>{const R=y.target.closest("[data-action]");R?Z(R.dataset.action==="confirm"):y.target===q&&Z(!1)})})}async function p(O,B,L,E){if(!o){o=L,I();try{const{response:M,data:q}=await ze(O,B);M.ok&&(q!=null&&q.job_id)?(c={tone:"success",message:`${E} Job ${je(q.job_id)}.`},k(`${E} Job ${je(q.job_id)}.`,"success")):(c={tone:"error",message:(q==null?void 0:q.error)||"No se pudo iniciar la operación."},k((q==null?void 0:q.error)||"No se pudo iniciar la operación.","error"))}catch(M){const q=M instanceof Error?M.message:String(M);c={tone:"error",message:q},k(q,"error")}finally{o="",await U()}}}async function u(){const O=n;if(!O||o||!await h("Promote WIP to Production",`<p>This path reuses the live WIP generation and promotes it incrementally into Production with persisted checkpoints.</p>
       <table class="corpus-confirm-table">
         <tr><td>Production current:</td><td><strong>${ge(O.production.documents)}</strong> docs · <strong>${ge(O.production.chunks)}</strong> chunks</td></tr>
         <tr><td>WIP source:</td><td><strong>${ge(O.wip.documents)}</strong> docs · <strong>${ge(O.wip.chunks)}</strong> chunks</td></tr>
         <tr><td>WIP generation:</td><td><code>${J(je(O.wip.generation_id))}</code></td></tr>
       </table>
       <label style="display:flex;align-items:center;gap:0.4rem;margin:0.75rem 0;font-size:0.85rem;cursor:pointer">
         <input type="checkbox" id="corpus-force-full-upsert" />
         Forzar upsert completo (sincronizar summaries + embeddings aunque chunk_text no haya cambiado)
       </label>
       <p class="corpus-confirm-note">The backend will keep a promotion plan, batch checkpoints, and a resumable cursor before activation.</p>`,"Promote now"))return;const L=document.querySelector("#corpus-force-full-upsert"),E=(L==null?void 0:L.checked)??!1;_=!1,$=0,C=null,b=0,await p("/api/ops/corpus/rebuild-from-wip",{mode:"promote",force_full_upsert:E},"promote",E?"Promotion started (force full upsert).":"Promotion started.")}async function l(){var L;const O=(n==null?void 0:n.current_operation)??(n==null?void 0:n.last_operation)??null;!(O!=null&&O.resume_job_id)||o||!await h("Resume from Checkpoint",`<p>The backend will reuse the persisted promotion plan and continue from the last completed checkpoint.</p>
       <table class="corpus-confirm-table">
         <tr><td>Job:</td><td><code>${J(je(O.resume_job_id))}</code></td></tr>
         <tr><td>Checkpoint:</td><td>${J(_t(O))}</td></tr>
         <tr><td>Target generation:</td><td><code>${J(je(O.target_generation_id))}</code></td></tr>
       </table>`,"Resume now")||(_=!0,$=((L=O.last_checkpoint)==null?void 0:L.cursor)??0,C=null,b=0,await p("/api/ops/corpus/rebuild-from-wip/resume",{job_id:O.resume_job_id},"resume","Resume started."))}async function m(){const O=n;!O||!O.rollback_generation_id||o||!await h("Rollback de Production",`<p>Se va a intentar reactivar una generación previa de production.</p>
       <table class="corpus-confirm-table">
         <tr><td>Production actual:</td><td><code>${J(je(O.production.generation_id))}</code></td></tr>
         <tr><td>Objetivo:</td><td><code>${J(je(O.rollback_generation_id))}</code></td></tr>
       </table>
       <p class="corpus-confirm-note">Solo se habilita si el backend detecta una generación previa todavía utilizable.</p>`,"Revertir ahora","rollback")||await p("/api/ops/corpus/rollback",{generation_id:O.rollback_generation_id},"rollback","Rollback started.")}async function w(){o||await p("/api/ops/corpus/wip-audit",{},"audit","WIP audit started.")}async function v(){o||!await h("Reiniciar promoción",`<p>Cancela cualquier job anterior y lanza una nueva promoción desde WIP a producción.</p>
       <label style="display:flex;align-items:center;gap:0.4rem;margin:0.75rem 0;font-size:0.85rem;cursor:default;opacity:0.55" title="Force upsert es obligatorio en reinicio">
         <input type="checkbox" checked disabled style="opacity:0.55" />
         Forzar upsert completo (sincronizar summaries + embeddings aunque chunk_text no haya cambiado)
       </label>
       <p class="corpus-confirm-note">Reiniciar siempre usa force upsert: todos los ~50K chunks se copian completos.</p>`,"Reiniciar ahora","rollback")||(_=!1,$=0,C=null,b=0,await p("/api/ops/corpus/rebuild-from-wip/restart",{},"restart","Restart submitted (force full upsert)."))}async function N(){if(!(f||o||!await h("Sincronizar JSONL a WIP",`<p>Se va a sincronizar el índice JSONL local ya existente al Supabase WIP (Docker).</p>
       <p class="corpus-confirm-note">Esta operación no ejecuta reindex — solo sincroniza los documentos y chunks que ya existen en el JSONL local. Es segura e idempotente.</p>`,"Sincronizar ahora"))){f=!0,I();try{const{response:B,data:L}=await ze("/api/ops/corpus/sync-to-wip",{});B.ok&&(L!=null&&L.synced)?k(`WIP sincronizado: ${ge(L.documents)} docs, ${ge(L.chunks)} chunks.`,"success"):k((L==null?void 0:L.error)||"Error sincronizando a WIP.","error")}catch(B){const L=B instanceof Error?B.message:String(B);k(L||"Error sincronizando a WIP.","error")}finally{f=!1,await U()}}}async function x(){const O=(n==null?void 0:n.current_operation)??(n==null?void 0:n.last_operation)??null,B=String((O==null?void 0:O.log_tail)||"").trim();if(B)try{await navigator.clipboard.writeText(B),k("Log tail copied.","success")}catch(L){const E=L instanceof Error?L.message:"Could not copy log tail.";k(E||"Could not copy log tail.","error")}}function I(){var Pe,Ce,K,ke,pe,Ae,Me,De,he,Le,Te;const O=e.container.querySelector(".corpus-log-accordion");O&&(d=O.open);const B=e.container.querySelector(".corpus-checks-accordion");B&&(g=B.open);const L=n;if(!L){e.container.innerHTML=`<p class="ops-empty">${J(i||"Cargando estado del corpus…")}</p>`;return}const E=L.current_operation??L.last_operation??null,M=Un(E,L),q=!!(L.current_operation&&["queued","running"].includes(L.current_operation.status))||!!o,Z=q||!L.preflight_ready,y=!q&&!!(E&&E.resume_supported&&E.resume_job_id&&(E.operation_state_code==="stalled_resumable"||E.operation_state_code==="failed_resumable")),R=q||!L.rollback_available,S=L.delta.documents==="+0"&&L.delta.chunks==="+0"?"Sin delta pendiente":`${L.delta.documents} documentos · ${L.delta.chunks} chunks`,T=Ot(E==null?void 0:E.checks,{onlyFailures:!0}),F=Ot(E==null?void 0:E.checks),V=!!(L.current_operation&&["queued","running"].includes(L.current_operation.status)),oe=c&&!(L.current_operation&&["queued","running"].includes(L.current_operation.status))?`
          <div class="corpus-callout tone-${J(c.tone==="success"?"green":"red")}">
            <strong>${c.tone==="success"?"Request sent":"Request failed"}</strong>
            <span>${J(c.message)}</span>
          </div>`:"",le=(Pe=E==null?void 0:E.last_checkpoint)!=null&&Pe.phase?(()=>{const de=E.operation_state_code==="completed"?"green":E.operation_state_code==="failed_resumable"||E.operation_state_code==="stalled_resumable"?"red":"yellow",ve=Ft(E);return`
            <div class="corpus-callout tone-${J(de)}">
              <strong>Checkpoint</strong>
              <span>${J(_t(E))} · ${J(Mt(E.last_checkpoint.at||null))}</span>
              ${ve>0&&de!=="green"?`<div class="corpus-progress-bar corpus-progress-bar-sm"><div class="corpus-progress-fill" style="width:${ve.toFixed(1)}%"></div></div>`:""}
            </div>`})():"";e.container.innerHTML=`
      <div class="corpus-cards">
        ${Dt("WIP",L.wip)}
        ${Dt("PRODUCTION",L.production)}
      </div>
      <div class="corpus-delta">
        <span class="corpus-delta-label">${J(S)}</span>
      </div>
      <section class="corpus-operation-panel severity-${J(M.severity)}">
        <div class="corpus-operation-header">
          <div>
            <div class="corpus-status-chip tone-${J(M.severity)}${M.severity==="yellow"?" is-pulsing":""}">
              ${J(M.title)}
            </div>
            <h3 class="corpus-operation-title">${J(Wn(E))}</h3>
            <p class="corpus-operation-detail">${J(M.detail)}</p>
          </div>
          <dl class="corpus-operation-meta">
            <div><dt>Heartbeat</dt><dd>${J(Mt((E==null?void 0:E.heartbeat_at)||(E==null?void 0:E.updated_at)||null))}</dd></div>
            <div><dt>Backend</dt><dd>${J(zn(E))}${E!=null&&E.force_full_upsert?` <span style="background:${qt.amber[100]};color:${qt.amber[600]};padding:0.1rem 0.4rem;border-radius:0.3rem;font-size:0.7rem;font-weight:700">FORCE UPSERT</span>`:""}</dd></div>
            <div><dt>Phase</dt><dd>${J(E!=null&&E.current_phase?gt(E.current_phase):(E==null?void 0:E.stage_label)||(L.preflight_ready?"Ready":"Blocked"))}</dd></div>
            <div><dt>Checkpoint</dt><dd>${J(_t(E))}</dd></div>
            <div><dt>WIP</dt><dd><code>${J(je((E==null?void 0:E.source_generation_id)||L.wip.generation_id))}</code></dd></div>
            <div><dt>Target</dt><dd><code>${J(je((E==null?void 0:E.target_generation_id)||(E==null?void 0:E.production_generation_id)||L.production.generation_id))}</code></dd></div>
            <div><dt>Prod</dt><dd><code>${J(je((E==null?void 0:E.production_generation_id)||L.production.generation_id))}</code></dd></div>
          </dl>
        </div>
        ${V?(()=>{var fe,ae;const de=Ft(E),ve=((fe=E==null?void 0:E.last_checkpoint)==null?void 0:fe.cursor)??(E==null?void 0:E.batch_cursor)??0,D=((ae=E==null?void 0:E.last_checkpoint)==null?void 0:ae.total)??0,W=Hn(E);if(ve>0&&D>0){const ce=Date.now();if(C&&ve>C.cursor){const X=Math.max(1,(ce-C.ts)/1e3),ee=(ve-C.cursor)/X;b=b>0?b*.7+ee*.3:ee}C={cursor:ve,ts:ce}}const se=b>0?`${b.toFixed(0)} chunks/s`:"",te=D-ve,Q=b>0&&te>0?(()=>{const ce=Math.ceil(te/b),X=Math.floor(ce/60),ee=ce%60;return X>0?`~${X}m ${ee}s restante`:`~${ee}s restante`})():"";return`
            <div class="corpus-progress-bar"><div class="corpus-progress-fill" style="width:${de.toFixed(1)}%"></div></div>
            <div class="corpus-progress-detail">
              ${_?`<span class="corpus-resume-badge">REANUDADO desde ${ge($)}</span>`:""}
              <span class="corpus-progress-nums">${ge(ve)} / ${ge(D)} (${de.toFixed(1)}%)</span>
              ${se?`<span class="corpus-progress-rate">${J(se)}</span>`:""}
              ${Q?`<span class="corpus-progress-eta">${J(Q)}</span>`:""}
              <span class="corpus-hb-badge ${W.className}">${J(W.label)}</span>
            </div>`})():""}
        ${(Ce=E==null?void 0:E.stages)!=null&&Ce.length?jn(E.stages):""}
        ${le}
        ${(K=L.preflight_reasons)!=null&&K.length&&!V&&!L.preflight_ready?`
          <div class="corpus-callout tone-red">
            <strong>Preflight blocked</strong>
            <ul>${L.preflight_reasons.map(de=>`<li>${J(de)}</li>`).join("")}</ul>
          </div>`:""}
        ${oe}
        ${T?`<div class="corpus-section"><h4>Visible failures</h4>${T}</div>`:""}
        ${F?`
          <details class="corpus-section corpus-checks-accordion">
            <summary class="corpus-checks-summary"><h4>Checks</h4><span class="corpus-checks-count">${((E==null?void 0:E.checks)??[]).length}</span></summary>
            ${F}
          </details>`:""}
        ${Jn(E)}
        ${E!=null&&E.log_tail?`
          <details class="corpus-section corpus-log-accordion">
            <summary class="corpus-log-summary">
              <h4>Backend log tail</h4>
              <button id="corpus-copy-log-tail-btn" type="button" class="corpus-btn corpus-btn-rollback corpus-btn-inline">Copy</button>
            </summary>
            <pre class="corpus-log-tail">${J(E.log_tail)}</pre>
          </details>`:""}
        ${i?`
          <div class="corpus-callout tone-red">
            <strong>Refresh error</strong>
            <span>${J(i)}</span>
          </div>`:""}
      </section>
      <div class="corpus-actions">
        ${L.audit_missing&&!q?`
          <button id="corpus-audit-btn" class="corpus-btn corpus-btn-audit${o==="audit"?" is-busy":""}">
            ${o==="audit"?'<span class="corpus-spinner"></span> Auditing…':"Run WIP Audit"}
          </button>`:""}
        ${!q&&!f?`
          <button id="corpus-sync-wip-btn" class="corpus-btn corpus-btn-sync">Sincronizar JSONL a WIP</button>`:""}
        ${f?`
          <button class="corpus-btn corpus-btn-sync is-busy" disabled><span class="corpus-spinner"></span> Sincronizando…</button>`:""}
        <button id="corpus-promote-btn" class="corpus-btn corpus-btn-promote${o==="promote"?" is-busy":""}" ${Z?"disabled":""}>
          ${o==="promote"?'<span class="corpus-spinner"></span> Starting…':"Promote WIP to Production"}
        </button>
        ${y?`
          <button id="corpus-resume-btn" class="corpus-btn corpus-btn-promote${o==="resume"?" is-busy":""}">
            ${o==="resume"?'<span class="corpus-spinner"></span> Resuming…':"Resume from Checkpoint"}
          </button>`:""}
        <button id="corpus-rollback-btn" class="corpus-btn corpus-btn-rollback${o==="rollback"?" is-busy":""}" ${R?"disabled":""}>
          ${o==="rollback"?'<span class="corpus-spinner"></span> Starting rollback…':"Rollback"}
        </button>
        <button id="corpus-restart-btn" class="corpus-btn corpus-btn-rollback${o==="restart"?" is-busy":""}" ${q?"disabled":""}>
          ${o==="restart"?'<span class="corpus-spinner"></span> Restarting…':"Reiniciar promoción (force upsert)"}
        </button>
      </div>
      ${L.preflight_ready?"":`
        <p class="corpus-action-note">${J(((ke=L.preflight_reasons)==null?void 0:ke[0])||"Promotion is blocked by preflight.")}</p>`}
      ${L.rollback_available?"":`
        <p class="corpus-action-note">${J(L.rollback_reason||"Rollback is not available yet.")}</p>`}
      <div class="corpus-toast ops-flash" hidden></div>
    `,(pe=e.container.querySelector("#corpus-audit-btn"))==null||pe.addEventListener("click",w),(Ae=e.container.querySelector("#corpus-sync-wip-btn"))==null||Ae.addEventListener("click",()=>void N()),(Me=e.container.querySelector("#corpus-promote-btn"))==null||Me.addEventListener("click",u),(De=e.container.querySelector("#corpus-resume-btn"))==null||De.addEventListener("click",l),(he=e.container.querySelector("#corpus-rollback-btn"))==null||he.addEventListener("click",m),(Le=e.container.querySelector("#corpus-restart-btn"))==null||Le.addEventListener("click",v),(Te=e.container.querySelector("#corpus-copy-log-tail-btn"))==null||Te.addEventListener("click",de=>{de.preventDefault(),de.stopPropagation(),x()});const be=e.container.querySelector(".corpus-log-accordion");be&&d&&(be.open=!0);const Ee=e.container.querySelector(".corpus-checks-accordion");Ee&&g&&(Ee.open=!0)}async function U(){try{n=await Ne("/api/ops/corpus-status"),i="",n!=null&&n.current_operation&&["queued","running","completed","failed","cancelled"].includes(n.current_operation.status)&&(c=null)}catch(O){i=O instanceof Error?O.message:String(O),n===null&&(n=null)}I()}function G(){I(),s===null&&(s=window.setInterval(()=>{U()},On))}return{bindEvents:G,refresh:U}}const Ya=Object.freeze(Object.defineProperty({__proto__:null,createCorpusLifecycleController:an},Symbol.toStringTag,{value:"Module"})),Vn={normative_base:"Normativa",interpretative_guidance:"Interpretación",practica_erp:"Práctica"},It={declaracion_renta:"Renta",iva:"IVA",laboral:"Laboral",facturacion_electronica:"Facturación",estados_financieros_niif:"NIIF",ica:"ICA",calendario_obligaciones:"Calendarios",retencion_fuente:"Retención",regimen_sancionatorio:"Sanciones",regimen_cambiario:"Régimen Cambiario",impuesto_al_patrimonio:"Patrimonio",informacion_exogena:"Exógena",proteccion_de_datos:"Datos",obligaciones_mercantiles:"Mercantil",obligaciones_profesionales_contador:"Obligaciones Contador",rut_responsabilidades:"RUT",gravamen_movimiento_financiero_4x1000:"GMF 4×1000",beneficiario_final:"Beneficiario Final",contratacion_estatal:"Contratación Estatal",reforma_pensional:"Reforma Pensional",zomac_incentivos:"ZOMAC"},on="lia_backstage_ops_active_tab",St="lia_backstage_ops_ingestion_session_id";function Kn(){const e=bt();try{const t=String(e.getItem(on)||"").trim();return t==="ingestion"||t==="control"||t==="embeddings"||t==="reindex"?t:"monitor"}catch{return"monitor"}}function Xn(e){const t=bt();try{t.setItem(on,e)}catch{}}function Yn(){const e=bt();try{return String(e.getItem(St)||"").trim()}catch{return""}}function Zn(e){const t=bt();try{if(!e){t.removeItem(St);return}t.setItem(St,e)}catch{}}function ht(e){return e==="processing"||e==="running_batch_gates"}function rn(e){if(!e)return!1;const t=String(e.status||"").toLowerCase();if(t==="done"||t==="completed")return!0;const n=e.documents||[];return n.length===0?!1:n.every(a=>{const s=String(a.status||"").toLowerCase();return s==="done"||s==="completed"||s==="skipped_duplicate"||s==="bounced"})}function ct(e){const t=String(e||"").trim().toLowerCase();return t==="failed"||t==="error"?"error":t==="processing"||t==="running_batch_gates"||t==="needs_retry_batch_gate"||t==="queued"||t==="uploading"||t==="extracting"||t==="etl"||t==="writing"||t==="gates"||t==="in_progress"||t==="partial_failed"||t==="raw"||t==="pending_dedup"?"warn":"ok"}function we(e){return e instanceof st?e.message||`HTTP ${e.status}`:e instanceof Error?e.message:String(e||"unknown_error")}function Qn(e,t){switch(String(e||"").trim()){case"normative_base":return t.t("ops.ingestion.batchType.normative");case"interpretative_guidance":return t.t("ops.ingestion.batchType.interpretative");case"practica_erp":return t.t("ops.ingestion.batchType.practical");default:return String(e||"-")}}function es(e,t){const n=Number(e||0);return!Number.isFinite(n)||n<=0?"0 B":n>=1024*1024?`${t.formatNumber(n/(1024*1024),{maximumFractionDigits:1})} MB`:n>=1024?`${t.formatNumber(n/1024,{maximumFractionDigits:1})} KB`:`${t.formatNumber(n)} B`}function zt(e,t){const n=e||{total:0,queued:0,done:0,failed:0,pending_batch_gate:0,bounced:0},a=[`${t.t("ops.ingestion.summary.total")} ${n.total||0}`,`${t.t("ops.ingestion.summary.done")} ${n.done||0}`,`${t.t("ops.ingestion.summary.failed")} ${n.failed||0}`,`${t.t("ops.ingestion.summary.queued")} ${n.queued||0}`,`${t.t("ops.ingestion.summary.gate")} ${n.pending_batch_gate||0}`],s=Number(n.bounced||0);return s>0&&a.push(`Rebotados ${s}`),a.join(" · ")}function Et(e,t,n){const a=e||t||"";if(!a)return"stalled";const s=Date.parse(a);if(Number.isNaN(s))return"stalled";const o=Date.now()-s,i=n==="gates",c=i?9e4:3e4,r=i?3e5:12e4;return o<c?"alive":o<r?"slow":"stalled"}function ts(e,t){const n=e||t||"";if(!n)return"-";const a=Date.parse(n);if(Number.isNaN(a))return"-";const s=Math.max(0,Date.now()-a),o=Math.floor(s/1e3);if(o<5)return"ahora";if(o<60)return`hace ${o}s`;const i=Math.floor(o/60),c=o%60;return i<60?`hace ${i}m ${c}s`:`hace ${Math.floor(i/60)}h ${i%60}m`}const yt={validating:"validando corpus",manifest:"activando manifest",indexing:"reconstruyendo índice","indexing/scanning":"escaneando documentos","indexing/chunking":"generando chunks","indexing/writing_indexes":"escribiendo índices","indexing/syncing":"sincronizando Supabase","indexing/auditing":"auditando calidad"};function ln(e){if(!e)return"";if(yt[e])return yt[e];const t=e.indexOf(":");if(t>0){const n=e.slice(0,t),a=e.slice(t+1),s=yt[n];if(s)return`${s} (${a})`}return e}function ns(e){if(!e)return"";const t=Date.parse(e);if(Number.isNaN(t))return"";try{return new Intl.DateTimeFormat("es-CO",{timeZone:"America/Bogota",day:"2-digit",month:"2-digit",year:"numeric",hour:"2-digit",minute:"2-digit",second:"2-digit",hour12:!1}).format(new Date(t))}catch{return""}}function cn(e,t){const n=Math.max(0,Math.min(100,Number(e||0))),a=document.createElement("div");a.className="ops-progress";const s=document.createElement("div");s.className="ops-progress-bar";const o=document.createElement("span");o.className="ops-progress-fill",t==="gates"&&n>0&&n<100&&o.classList.add("ops-progress-active"),o.style.width=`${n}%`;const i=document.createElement("span");return i.className="ops-progress-label",i.textContent=`${n}%`,s.appendChild(o),a.append(s,i),a}function We(e){return String(e??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#39;")}function Ke(e){return(e??0).toLocaleString("es-CO")}function Ht(e){if(e==null||e<=0)return"-";const t=Math.floor(e/60),n=Math.floor(e%60);return t>0?`${t}m ${n}s`:`${n}s`}function dn({dom:e,setFlash:t}){const{container:n}=e;let a=null,s="",o=!1,i=!1,c=0,r=0,d=3e3,g=[];function f(u){if(u<=0)return;const l=Date.now();if(u>c&&r>0){const m=l-r,w=u-c,v=m/w;g.push(v),g.length>10&&g.shift(),d=g.reduce((N,x)=>N+x,0)/g.length}u!==c&&(c=u,r=l)}function _(){if(r===0)return{level:"healthy",label:"Iniciando..."};const u=Date.now()-r,l=Math.max(d*3,1e4),m=Math.max(d*6,3e4);return u<l?{level:"healthy",label:"Saludable"}:u<m?{level:"caution",label:"Lento"}:{level:"failed",label:"Sin respuesta"}}function $(){var F,V,oe,le,be,Ee,Pe,Ce;const u=a;if(!u){n.innerHTML='<p class="ops-text-muted">Cargando estado de embeddings...</p>';return}const l=u.current_operation||u.last_operation,m=((F=u.current_operation)==null?void 0:F.status)??"",w=m==="running"||m==="queued"||s==="start",v=!u.current_operation&&!s,N=s==="stop",x=!w&&!N&&((l==null?void 0:l.status)==="cancelled"||(l==null?void 0:l.status)==="failed"||(l==null?void 0:l.status)==="stalled");let I="";const U=(l==null?void 0:l.status)??"",G=N?"Deteniendo...":w?"En ejecución":x?U==="stalled"?"Detenido (stalled)":U==="cancelled"?"Cancelado":"Fallido":v?"Inactivo":U||"—",O=w?"tone-yellow":U==="completed"?"tone-green":U==="failed"||U==="stalled"?"tone-red":U==="cancelled"?"tone-yellow":"",B=u.api_health,L=B!=null&&B.ok?"emb-api-ok":"emb-api-error",E=B?B.ok?`API OK (${B.detail})`:`API Error: ${B.detail}`:"API: verificando...";if(I+=`<div class="emb-status-row">
      <span class="corpus-status-chip ${O}">${We(G)}</span>
      <span class="emb-target-badge">WIP</span>
      <span class="emb-api-semaphore ${L}" title="${We(E)}"><span class="emb-api-dot"></span> ${We(B!=null&&B.ok?"API OK":B?"API Error":"...")}</span>
      ${w?(()=>{const K=_();return`<span class="emb-process-health emb-health-${K.level}"><span class="emb-health-dot"></span> ${We(K.label)}</span>`})():""}
    </div>`,I+='<div class="emb-controls">',v?(I+=`<label class="emb-force-label"><input type="checkbox" id="emb-force-check" ${o?"checked":""} /> Forzar re-embed (todas)</label>`,I+=`<button class="corpus-btn corpus-btn-promote" id="emb-start-btn" ${s?"disabled":""}>Iniciar</button>`):N?I+='<span class="emb-running-label">Deteniendo al finalizar batch actual...</span>':w&&l&&(I+='<button class="corpus-btn corpus-btn-rollback" id="emb-stop-btn">Detener</button>',I+='<span class="emb-running-label">Embebiendo chunks...</span>'),x&&l){const K=l.force,ke=(V=l.progress)==null?void 0:V.last_cursor_id,pe=(oe=l.progress)==null?void 0:oe.pct_complete,Ae=ke?`Reanudar desde ${typeof pe=="number"?pe.toFixed(1)+"%":"checkpoint"}`:"Reiniciar";K&&(I+='<span class="emb-force-label"><input type="checkbox" checked disabled /> Forzar re-embed (continuación)</span>'),I+=`<button class="corpus-btn corpus-btn-promote" id="emb-resume-btn" ${s?"disabled":""}>${We(Ae)}</button>`,I+=`<button class="corpus-btn" id="emb-start-btn" ${s?"disabled":""} style="opacity:0.7">Iniciar desde cero</button>`}I+="</div>";const M=l==null?void 0:l.progress,q=(w||s)&&(M==null?void 0:M.total),Z=q?M.total:u.total_chunks,y=q?M.embedded:u.embedded_chunks,R=q?M.pending-M.embedded-(M.failed||0):u.null_embedding_chunks,S=q&&M.failed||0,T=q?M.pct_complete:u.coverage_pct;if(I+=`<div class="emb-stats-grid">
      <div class="emb-stat"><span class="emb-stat-value">${Ke(Z)}</span><span class="emb-stat-label">Total</span></div>
      <div class="emb-stat"><span class="emb-stat-value">${Ke(y)}</span><span class="emb-stat-label">Embebidos</span></div>
      <div class="emb-stat"><span class="emb-stat-value">${Ke(Math.max(0,R))}</span><span class="emb-stat-label">Pendientes</span></div>
      ${S>0?`<div class="emb-stat emb-stat-error"><span class="emb-stat-value">${Ke(S)}</span><span class="emb-stat-label">Fallidos</span></div>`:`<div class="emb-stat"><span class="emb-stat-value">${T.toFixed(1)}%</span><span class="emb-stat-label">Cobertura</span></div>`}
    </div>`,w&&(l!=null&&l.progress)){const K=l.progress;I+='<div class="emb-live-progress">',I+='<div class="emb-progress-bar-wrap" id="emb-progress-mount"></div>',I+=`<div class="emb-rate-line">
        <span>${((le=K.rate_chunks_per_sec)==null?void 0:le.toFixed(1))??"-"} chunks/s</span>
        <span>ETA: ${Ht(K.eta_seconds)}</span>
        <span>Elapsed: ${Ht(K.elapsed_seconds)}</span>
        <span>Batch ${Ke(K.current_batch)} / ${Ke(K.total_batches)}</span>
      </div>`,K.failed>0&&(I+=`<p class="emb-failed-notice">${Ke(K.failed)} chunks fallidos (${(K.failed/Math.max(K.pending,1)*100).toFixed(2)}%)</p>`),I+="</div>"}if(l!=null&&l.quality_report){const K=l.quality_report;I+='<div class="emb-quality-report">',I+="<h3>Reporte de calidad</h3>",I+=`<div class="emb-stats-grid">
        <div class="emb-stat"><span class="emb-stat-value">${((be=K.mean_cosine_similarity)==null?void 0:be.toFixed(4))??"-"}</span><span class="emb-stat-label">Coseno medio</span></div>
        <div class="emb-stat"><span class="emb-stat-value">${((Ee=K.min_cosine_similarity)==null?void 0:Ee.toFixed(4))??"-"}</span><span class="emb-stat-label">Min</span></div>
        <div class="emb-stat"><span class="emb-stat-value">${((Pe=K.max_cosine_similarity)==null?void 0:Pe.toFixed(4))??"-"}</span><span class="emb-stat-label">Max</span></div>
        <div class="emb-stat"><span class="emb-stat-value">${Ke(K.sample_pairs)}</span><span class="emb-stat-label">Pares</span></div>
      </div>`,K.collapsed_warning&&(I+='<p class="emb-anomaly-warning">ANOMALIA: Embeddings colapsados (mean &gt; 0.95)</p>'),K.noise_warning&&(I+='<p class="emb-anomaly-warning">ANOMALIA: Embeddings ruidosos (mean &lt; 0.10)</p>'),!K.collapsed_warning&&!K.noise_warning&&(I+='<p class="emb-quality-ok">Distribución saludable</p>'),I+="</div>"}if((Ce=l==null?void 0:l.checks)!=null&&Ce.length){I+='<div class="emb-checks">';for(const K of l.checks){const ke=K.ok?'<span class="ops-dot ops-dot-ok">●</span>':'<span class="ops-dot ops-dot-error">●</span>';I+=`<div class="emb-check">${ke} <strong>${We(K.label)}</strong>: ${We(K.detail)}</div>`}I+="</div>"}if(l!=null&&l.log_tail){const K=l.log_tail.split(`
`).reverse().join(`
`);I+=`<details class="emb-log-accordion" id="emb-log-details" ${i?"open":""}><summary>Log</summary><pre class="emb-log-tail">${We(K)}</pre></details>`}if(l!=null&&l.error&&(I+=`<p class="emb-error">${We(l.error)}</p>`),n.innerHTML=I,w&&(l!=null&&l.progress)){const K=n.querySelector("#emb-progress-mount");K&&K.appendChild(cn(l.progress.pct_complete??0,"embedding"))}}function C(){n.addEventListener("click",u=>{const l=u.target;l.id==="emb-start-btn"&&b(),l.id==="emb-stop-btn"&&k(),l.id==="emb-resume-btn"&&h()}),n.addEventListener("change",u=>{const l=u.target;l.id==="emb-force-check"&&(o=l.checked)}),n.addEventListener("toggle",u=>{const l=u.target;l.id==="emb-log-details"&&(i=l.open)},!0)}async function b(){const u=o;s="start",o=!1,$();try{const{response:l,data:m}=await ze("/api/ops/embedding/start",{force:u});!l.ok||!(m!=null&&m.ok)?(t((m==null?void 0:m.error)||`Error ${l.status}`,"error"),s=""):t("Embedding iniciado","success")}catch(l){t(String(l),"error"),s=""}await p()}async function k(){var l;const u=(l=a==null?void 0:a.current_operation)==null?void 0:l.job_id;if(u){s="stop",$();try{await ze("/api/ops/embedding/stop",{job_id:u}),t("Stop solicitado — se detendrá al finalizar el batch actual","success")}catch(m){t(String(m),"error"),s=""}}}async function h(){const u=(a==null?void 0:a.current_operation)||(a==null?void 0:a.last_operation);if(u!=null&&u.job_id){s="start",$();try{const{response:l,data:m}=await ze("/api/ops/embedding/resume",{job_id:u.job_id});!l.ok||!(m!=null&&m.ok)?(t((m==null?void 0:m.error)||`Error ${l.status}`,"error"),s=""):t("Embedding reanudado desde checkpoint","success")}catch(l){t(String(l),"error"),s=""}s="",await p()}}async function p(){try{const u=await Ne("/api/ops/embedding-status");a=u;const l=u.current_operation;if(l!=null&&l.progress){const m=l.progress.current_batch;typeof m=="number"&&f(m)}s==="stop"&&!u.current_operation&&(s=""),s==="start"&&u.current_operation&&(s=""),u.current_operation||(c=0,r=0,g=[])}catch{}$()}return{bindEvents:C,refresh:p}}const Za=Object.freeze(Object.defineProperty({__proto__:null,createOpsEmbeddingsController:dn},Symbol.toStringTag,{value:"Module"})),ss=["pending","processing","done"],as={pending:"Pendiente",processing:"En proceso",done:"Procesado"},os={pending:"⏳",processing:"🔄",done:"✅"},is=5;function un(e){const t=String(e||"").toLowerCase();return t==="done"||t==="completed"||t==="skipped_duplicate"||t==="bounced"?"done":t==="in_progress"||t==="processing"||t==="extracting"||t==="etl"||t==="writing"||t==="gates"||t==="uploading"||t==="running_batch_gates"||t==="needs_retry_batch_gate"||t==="failed"||t==="error"||t==="partial_failed"?"processing":"pending"}function rs(e,t){const n=e.detected_topic||t.corpus||"",a=mn[n]||It[n]||n||"",s=e.detected_type||e.batch_type||"",o=Vn[s]||s||"",i=s==="normative_base"?"normative":s==="interpretative_guidance"?"interpretative":s==="practica_erp"?"practica":"unknown";let c="";return a&&(c+=`<span class="kanban-pill kanban-pill--topic" title="Tema: ${ye(n)}">${xe(a)}</span>`),o&&(c+=`<span class="kanban-pill kanban-pill--type-${i}" title="Tipo: ${ye(s)}">${xe(o)}</span>`),!a&&!o&&(c+='<span class="kanban-pill kanban-pill--unclassified">Sin clasificar</span>'),c}function ls(e,t,n){var w;const a=ct(e.status),s=un(e.status),o=es(e.bytes,n),i=Number(e.progress||0),c=new Set(t.gate_pending_doc_ids||[]),r=s==="done"&&c.has(e.doc_id);let d;e.status==="bounced"?d='<span class="meta-chip status-bounced">↩ Ya existe en el corpus</span>':s==="done"&&e.derived_from_doc_id&&(e.delta_section_count||0)>0?d=`<span class="meta-chip status-ok">△ ${e.delta_section_count} secciones nuevas</span>`:s==="done"&&(e.status==="done"||e.status==="completed")?(d='<span class="meta-chip status-ok">✓ Documento listo</span>',r&&(d+='<span class="meta-chip status-gate-pending">Pendiente validación final</span>')):d=`<span class="meta-chip status-${a}">${xe(e.status)}</span>`;const g=rs(e,t);let f="";if(e.status==="in_progress"||e.status==="processing"){const v=Et(e.heartbeat_at,e.updated_at,e.stage),N=ts(e.heartbeat_at,e.updated_at);f=`<div class="kanban-liveness ops-liveness-${v}">${N}</div>`}let _="";e.stage==="gates"&&t.gate_sub_stage&&(_=`<div class="kanban-gate-sub">${ln(t.gate_sub_stage)}</div>`);let $="";s==="processing"&&i>0&&($=`<div class="kanban-progress" data-progress="${i}"></div>`);let C="";(w=e.error)!=null&&w.message&&(C=`<div class="kanban-error">${xe(e.error.message)}</div>`);let b="";e.duplicate_of?b=`<div class="kanban-duplicate">Duplicado de: ${xe(e.duplicate_of)}</div>`:e.derived_from_doc_id&&(b=`<div class="kanban-duplicate">Derivado de: ${xe(e.derived_from_doc_id)}</div>`);let k="";if(s==="done"){const v=ns(e.updated_at);v&&(k=`<div class="kanban-completed-at">Completado: ${xe(v)}</div>`)}let h="";e.duplicate_of&&s!=="done"&&e.status!=="bounced"?h=gs(e):s==="pending"&&(e.status==="raw"||e.status==="needs_classification")&&ds(e)?h=us(e,n):s==="pending"&&(e.status==="raw"||e.status==="needs_classification")?h=cs(e,n,t):s==="processing"&&(e.status==="failed"||e.status==="error"||e.status==="partial_failed")&&(h=fs(e));let p="",u="";(s!=="pending"||e.status==="queued")&&(p=ps(),u=ms(e,t,n));const m=e.stage&&e.stage!==e.status&&s==="processing";return`
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
      ${f}
      ${_}
      ${$}
      ${k}
      ${b}
      ${C}
      ${h}
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
    `;const o=e.autogenerar_resolved_topic||"",i=It[o]||o,c=e.autogenerar_synonym_confidence??0,r=Math.round(c*100);return`
    <div class="kanban-actions kanban-autogenerar-actions kanban-autogenerar--synonym">
      <div class="kanban-autogenerar-header">Tema sugerido: <strong>${xe(i)}</strong> <span class="kanban-autogenerar-conf">(${r}%)</span></div>
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
  `}const pn=[["declaracion_renta","Renta"],["iva","IVA"],["laboral","Laboral"],["facturacion_electronica","Facturación"],["estados_financieros_niif","NIIF"],["ica","ICA"],["calendario_obligaciones","Calendarios"],["retencion_fuente","Retención"],["regimen_sancionatorio","Sanciones"],["regimen_cambiario","Régimen Cambiario"],["impuesto_al_patrimonio","Patrimonio"],["informacion_exogena","Exógena"],["proteccion_de_datos","Datos"],["obligaciones_mercantiles","Mercantil"],["obligaciones_profesionales_contador","Obligaciones Contador"],["rut_responsabilidades","RUT"],["gravamen_movimiento_financiero_4x1000","GMF 4×1000"],["beneficiario_final","Beneficiario Final"],["contratacion_estatal","Contratación Estatal"],["reforma_pensional","Reforma Pensional"],["zomac_incentivos","ZOMAC"]];function bs(e){const t=new Set,n=[];for(const[a,s]of pn)t.add(a),n.push([a,s]);for(const a of e)!a.key||t.has(a.key)||(t.add(a.key),n.push([a.key,a.label||a.key]));return n}let Nt=pn,mn={...It};function ft(e=""){let t='<option value="">Seleccionar...</option>';for(const[n,a]of Nt){const s=n===e?" selected":"";t+=`<option value="${ye(n)}"${s}>${xe(a)}</option>`}return t}function xe(e){const t=document.createElement("span");return t.textContent=e,t.innerHTML}function ye(e){return e.replace(/&/g,"&amp;").replace(/"/g,"&quot;").replace(/'/g,"&#39;").replace(/</g,"&lt;").replace(/>/g,"&gt;")}function hs(e){const t=e.replace(/\/[^/]+$/,"").split("/").filter(Boolean);return t.length<=2?t.join("/")+"/":"…/"+t.slice(-2).join("/")+"/"}function vs(e,t,n,a,s){s&&s.length>0&&(Nt=bs(s),mn=Object.fromEntries(Nt));const o=[...e.documents||[]].sort((h,p)=>Date.parse(String(p.updated_at||0))-Date.parse(String(h.updated_at||0))),i={pending:[],processing:[],done:[]};for(const h of o){const p=un(h.status);i[p].push(h)}i.pending.sort((h,p)=>{const u=h.status==="raw"||h.status==="needs_classification"?0:1,l=p.status==="raw"||p.status==="needs_classification"?0:1;return u!==l?u-l:Date.parse(String(p.updated_at||0))-Date.parse(String(h.updated_at||0))});const c=e.status==="running_batch_gates",r=e.gate_sub_stage||"";let d="";if(c){const h=r?ln(r):"Preparando...";d=`
      <div class="kanban-validation-banner kanban-validation-banner--running">
        <span class="kanban-validation-spinner"></span>
        <span>Validación final en curso — ${xe(h)}</span>
      </div>`}else e.status==="needs_retry_batch_gate"?d=`
      <div class="kanban-validation-banner kanban-validation-banner--error">
        <span>⚠ Validación final fallida — use Reintentar o Validar lote</span>
      </div>`:e.status==="completed"&&e.wip_sync_status==="skipped"&&(d=`
      <div class="kanban-validation-banner kanban-validation-banner--warn">
        <span>⚠ Ingesta completada solo localmente — WIP Supabase no estaba disponible. Use Operaciones → Sincronizar a WIP.</span>
      </div>`);let g="";const f=i.processing.length;for(const h of ss){const p=i[h],u=h==="processing"?`<span class="kanban-column-count">${f}</span><span class="kanban-column-limit">/ ${is}</span>`:`<span class="kanban-column-count">${p.length}</span>`,l=p.length===0?'<div class="kanban-column-empty">Sin documentos</div>':p.map(w=>ls(w,e,n)).join(""),m=h==="done"?d:"";g+=`
      <div class="kanban-column kanban-column--${h}">
        <div class="kanban-column-header">
          <span class="kanban-column-icon">${os[h]}</span>
          <span class="kanban-column-label">${as[h]}</span>
          ${u}
        </div>
        <div class="kanban-column-cards">
          ${m}
          ${l}
        </div>
      </div>
    `}const _={};t.querySelectorAll(".kanban-column").forEach(h=>{const p=h.classList[1]||"",u=h.querySelector(".kanban-column-cards");p&&u&&(_[p]=u.scrollTop)});const $=[];let C=t;for(;C;)C.scrollTop>0&&$.push([C,C.scrollTop]),C=C.parentElement;const b={};t.querySelectorAll(".kanban-reclassify-panel").forEach(h=>{var p,u;if(!h.hasAttribute("hidden")){const l=h.closest("[data-doc-id]"),m=(l==null?void 0:l.dataset.docId)||"";if(m&&!(a!=null&&a.has(m))){const w=((p=h.querySelector("[data-field='topic']"))==null?void 0:p.value)||"",v=((u=h.querySelector("[data-field='type']"))==null?void 0:u.value)||"";b[m]={topic:w,type:v}}}});const k={};t.querySelectorAll(".kanban-classify-actions").forEach(h=>{var l,m;const p=h.closest("[data-doc-id]"),u=(p==null?void 0:p.dataset.docId)||"";if(u){const w=((l=h.querySelector("[data-field='topic']"))==null?void 0:l.value)||"",v=((m=h.querySelector("[data-field='type']"))==null?void 0:m.value)||"";(w||v)&&(k[u]={topic:w,type:v})}}),t.innerHTML=g;for(const[h,p]of $)h.scrollTop=p;t.querySelectorAll(".kanban-column").forEach(h=>{const p=h.classList[1]||"",u=h.querySelector(".kanban-column-cards");p&&_[p]&&u&&(u.scrollTop=_[p])});for(const[h,p]of Object.entries(b)){const u=t.querySelector(`[data-doc-id="${CSS.escape(h)}"]`);if(!u)continue;const l=u.querySelector(".kanban-reclassify-toggle"),m=u.querySelector(".kanban-reclassify-panel");if(l&&m){m.removeAttribute("hidden"),l.textContent="✖";const w=m.querySelector("[data-field='topic']"),v=m.querySelector("[data-field='type']");w&&p.topic&&(w.value=p.topic),v&&p.type&&(v.value=p.type)}}for(const[h,p]of Object.entries(k)){const u=t.querySelector(`[data-doc-id="${CSS.escape(h)}"]`);if(!u)continue;const l=u.querySelector(".kanban-classify-actions");if(!l)continue;const m=l.querySelector("[data-field='topic']"),w=l.querySelector("[data-field='type']");m&&p.topic&&(m.value=p.topic),w&&p.type&&(w.value=p.type)}t.querySelectorAll(".kanban-progress").forEach(h=>{var m,w;const p=Number(h.dataset.progress||0),u=((w=(m=h.closest(".kanban-card"))==null?void 0:m.querySelector(".kanban-card-stage"))==null?void 0:w.textContent)||void 0,l=cn(p,u);h.replaceWith(l)}),t.querySelectorAll(".kanban-reclassify-toggle").forEach(h=>{h.addEventListener("click",()=>{const p=h.closest(".kanban-card"),u=p==null?void 0:p.querySelector(".kanban-reclassify-panel");if(!u)return;u.hasAttribute("hidden")?(u.removeAttribute("hidden"),h.textContent="✖"):(u.setAttribute("hidden",""),h.textContent="✎")})})}async function qe(e,t){const n=await fetch(e,t);let a=null;try{a=await n.json()}catch{a=null}if(!n.ok){const s=a&&typeof a=="object"&&"error"in a?String(a.error||n.statusText):n.statusText;throw new st(s,n.status,a)}return a}async function xt(e,t){const{response:n,data:a}=await ze(e,t);if(!n.ok){const s=a&&typeof a=="object"&&"error"in a?String(a.error||n.statusText):n.statusText;throw new st(s,n.status,a)}return a}const _s=new Set([".pdf",".md",".txt",".docx"]),ys=[".","__MACOSX"],Pt=3,wt="lia_folder_pending_";function lt(e){return e.filter(t=>{const n=t.name;if(ys.some(o=>n.startsWith(o)))return!1;const a=n.lastIndexOf("."),s=a>=0?n.slice(a).toLowerCase():"";return _s.has(s)})}function dt(e,t){return e.webkitRelativePath||t.get(e)||""}function Xe(e,t){const n=dt(e,t);return`${e.name}|${e.size}|${e.lastModified??0}|${n}`}function ws(e){return e<1024?`${e} B`:e<1024*1024?`${(e/1024).toFixed(1)} KB`:`${(e/(1024*1024)).toFixed(1)} MB`}function ks(e,t){var a;const n=((a=e.preflightEntry)==null?void 0:a.existing_doc_id)||"";switch(e.verdict){case"pending":return t.t("ops.ingestion.verdict.pending");case"new":return t.t("ops.ingestion.verdict.new");case"revision":return n?t.t("ops.ingestion.verdict.revisionOf",{docId:n}):t.t("ops.ingestion.verdict.revision");case"duplicate":return n?t.t("ops.ingestion.verdict.duplicateOf",{docId:n}):t.t("ops.ingestion.verdict.duplicate");case"artifact":return t.t("ops.ingestion.verdict.artifact");case"unreadable":return t.t("ops.ingestion.verdict.unreadable")}}function $s(e,t){const n=document.createElement("span");return n.className=`ops-verdict-pill ops-verdict-pill--${e.verdict}`,n.textContent=ks(e,t),n}function mt(e){return e.documents.filter(t=>t.status==="raw"||t.status==="needs_classification").length}function Cs(e){const{dom:t,stateController:n,withThinkingWheel:a,setFlash:s}=e;function o(){return e.state.selectedCorpus!=="autogenerar"?e.state.selectedCorpus:"autogenerar"}async function i(){const p=await Ne("/api/corpora"),u=Array.isArray(p.corpora)?p.corpora:[];n.setCorpora(u);const l=new Set(u.map(m=>m.key));l.add("autogenerar"),l.has(e.state.selectedCorpus)||n.setSelectedCorpus("autogenerar")}async function c(){const p=await Ne("/api/ingestion/sessions?limit=20");return Array.isArray(p.sessions)?p.sessions:[]}async function r(p){const u=await Ne(`/api/ingestion/sessions/${encodeURIComponent(p)}`);if(!u.session)throw new Error("missing_session");return u.session}async function d(p){const u=await xt("/api/ingestion/sessions",{corpus:p});if(!u.session)throw new Error("missing_session");return u.session}async function g(p,u,l){const m=t.ingestionCorpusSelect.value==="autogenerar"?"":t.ingestionCorpusSelect.value,w={"Content-Type":"application/octet-stream","X-Upload-Filename":u.name,"X-Upload-Mime":u.type||"application/octet-stream","X-Upload-Batch-Type":l};m&&(w["X-Upload-Topic"]=m);const v=dt(u,e.state.folderRelativePaths);v&&(w["X-Upload-Relative-Path"]=v),console.log(`[upload] ${u.name} (${u.size}B) → session=${p} batch=${l}`);const N=await fetch(`/api/ingestion/sessions/${encodeURIComponent(p)}/files`,{method:"POST",headers:w,body:u}),x=await N.text();let I;try{I=JSON.parse(x)}catch{throw console.error(`[upload] ${u.name} — response not JSON (${N.status}):`,x.slice(0,300)),new Error(`Upload response not JSON: ${N.status} ${x.slice(0,100)}`)}if(!N.ok){const U=I.error||N.statusText;throw console.error(`[upload] ${u.name} — HTTP ${N.status}:`,U),new st(U,N.status,I)}if(!I.document)throw console.error(`[upload] ${u.name} — no document in response:`,I),new Error("missing_document");return console.log(`[upload] ${u.name} → OK doc_id=${I.document.doc_id} status=${I.document.status}`),I.document}async function f(p){return qe(`/api/ingestion/sessions/${encodeURIComponent(p)}/process`,{method:"POST"})}async function _(p){return qe(`/api/ingestion/sessions/${encodeURIComponent(p)}/validate-batch`,{method:"POST"})}async function $(p){return qe(`/api/ingestion/sessions/${encodeURIComponent(p)}/retry`,{method:"POST"})}async function C(p,u=!1){const l=u?"?force=true":"";return qe(`/api/ingestion/sessions/${encodeURIComponent(p)}${l}`,{method:"DELETE"})}async function b({showWheel:p=!0,reportError:u=!0,focusSessionId:l=""}={}){const m=async()=>{await i(),e.render();let w=await c();const v=l||e.state.selectedSessionId;if(v&&!w.some(N=>N.session_id===v))try{w=[await r(v),...w.filter(x=>x.session_id!==v)]}catch{v===e.state.selectedSessionId&&n.setSelectedSession(null)}n.setSessions(w.sort((N,x)=>Date.parse(String(x.updated_at||0))-Date.parse(String(N.updated_at||0)))),n.syncSelectedSession(),e.render()};try{p?await a(m):await m()}catch(w){throw u&&s(we(w),"error"),e.render(),w}}async function k({sessionId:p,showWheel:u=!1,reportError:l=!0}){const m=async()=>{const w=await r(p);n.upsertSession(w),e.render()};try{u?await a(m):await m()}catch(w){throw l&&s(we(w),"error"),w}}async function h(){var u,l,m,w;const p=o();if(console.log(`[folder-ingest] ensureSelectedSession: effectiveCorpus="${p}", selectedSession=${((u=e.state.selectedSession)==null?void 0:u.session_id)||"null"} (status=${((l=e.state.selectedSession)==null?void 0:l.status)||"null"}, corpus=${((m=e.state.selectedSession)==null?void 0:m.corpus)||"null"})`),e.state.selectedSession&&!rn(e.state.selectedSession)&&e.state.selectedSession.status!=="completed"&&(e.state.selectedSession.corpus===p||p==="autogenerar"))return console.log(`[folder-ingest] Reusing session ${e.state.selectedSession.session_id}`),e.state.selectedSession;e.trace(`Creando sesión con corpus="${p}"...`);try{const v=await d(p);return e.trace(`Sesión creada: ${v.session_id} (corpus=${v.corpus})`),n.upsertSession(v),v}catch(v){if(e.trace(`Creación falló para corpus="${p}": ${v instanceof Error?v.message:String(v)}`),p==="autogenerar"){const N=((w=e.state.corpora.find(I=>I.active))==null?void 0:w.key)||"declaracion_renta";e.trace(`Reintentando con corpus="${N}"...`);const x=await d(N);return e.trace(`Sesión fallback: ${x.session_id} (corpus=${x.corpus})`),n.upsertSession(x),x}throw v}}return{resolveSessionCorpus:o,fetchCorpora:i,fetchIngestionSessions:c,fetchIngestionSession:r,createIngestionSession:d,uploadIngestionFile:g,startIngestionProcess:f,validateBatch:_,retryIngestionSession:$,ejectIngestionSession:C,refreshIngestion:b,refreshSelectedSession:k,ensureSelectedSession:h}}function Ss(e){const{i18n:t,stateController:n,dom:a,withThinkingWheel:s,setFlash:o}=e,i=sn(t);return{dom:a,i18n:t,stateController:n,withThinkingWheel:s,setFlash:o,toast:i,get state(){return n.state},render:()=>{},trace:()=>{}}}function Es(e,t){const{dom:n,stateController:a,i18n:s}=e,{ingestionUploadProgress:o}=n;async function i(b){var u,l;const k=[],h=[];for(let m=0;m<b.items.length;m++){const w=(l=(u=b.items[m]).webkitGetAsEntry)==null?void 0:l.call(u);w&&h.push(w)}if(!h.some(m=>m.isDirectory))return[];async function p(m){if(m.isFile){const w=await new Promise((v,N)=>{m.file(v,N)});e.state.folderRelativePaths.set(w,m.fullPath.replace(/^\//,"")),k.push(w)}else if(m.isDirectory){const w=m.createReader();let v;do{v=await new Promise((N,x)=>{w.readEntries(N,x)});for(const N of v)await p(N)}while(v.length>0)}}for(const m of h)await p(m);return k}async function c(b,k=""){const h=[];for await(const[p,u]of b.entries()){const l=k?`${k}/${p}`:p;if(u.kind==="file"){const m=await u.getFile();e.state.folderRelativePaths.set(m,l),h.push(m)}else if(u.kind==="directory"){const m=await c(u,l);h.push(...m)}}return h}async function r(b,k,h,p=Pt){let u=0,l=0,m=0,w=0;const v=[];return new Promise(N=>{function x(){for(;m<p&&w<k.length;){const I=k[w++];m++,t.uploadIngestionFile(b,I,h).then(()=>{u++}).catch(U=>{l++;const G=U instanceof Error?U.message:String(U);v.push({filename:I.name,error:G}),console.error(`[folder-ingest] Upload failed: ${I.name}`,U)}).finally(()=>{m--,a.setFolderUploadProgress({total:k.length,uploaded:u,failed:l,uploading:w<k.length||m>0}),d(),w<k.length||m>0?x():N({uploaded:u,failed:l,errors:v})})}}a.setFolderUploadProgress({total:k.length,uploaded:0,failed:0,uploading:!0}),d(),x()})}function d(){const b=e.state.folderUploadProgress;if(!b||!b.uploading){o.hidden=!0,o.innerHTML="";return}const k=b.uploaded+b.failed,h=b.total>0?Math.round(k/b.total*100):0,p=Math.max(0,Math.min(Pt,b.total-k));o.hidden=!1,o.innerHTML=`
      <div class="ops-upload-progress-header">
        <span>${s.t("ops.ingestion.uploadProgress",{current:k,total:b.total})}</span>
        <span>${h}%</span>
      </div>
      <div class="ops-upload-progress-bar">
        <span class="ops-upload-progress-fill" style="width:${h}%"></span>
      </div>
      <div class="ops-upload-progress-detail">
        ${s.t("ops.ingestion.uploadProgressDetail",{uploaded:b.uploaded,failed:b.failed,inflight:p})}
      </div>
    `}function g(){const b=e.state.preflightScanProgress;if(!b||!b.scanning){o.hidden=!0,o.innerHTML="";return}const k=b.total>0?Math.round(b.hashed/b.total*100):0;o.hidden=!1,o.innerHTML=`
      <div class="ops-preflight-scan">
        <div class="ops-preflight-scan-header">
          <span>${s.t("ops.ingestion.preflight.scanning",{hashed:b.hashed,total:b.total})}</span>
          <span>${k}%</span>
        </div>
        <div class="ops-preflight-scan-bar">
          <span class="ops-preflight-scan-fill" style="width:${k}%"></span>
        </div>
        <div class="ops-preflight-scan-detail">${s.t("ops.ingestion.preflight.scanningDetail")}</div>
      </div>
    `}function f(b){if(e.state.pendingFiles.length!==0&&dt(e.state.pendingFiles[0])!=="")try{const k=e.state.pendingFiles.map(h=>({name:h.name,relativePath:dt(h),size:h.size}));localStorage.setItem(wt+b,JSON.stringify(k))}catch{}}function _(b){try{localStorage.removeItem(wt+b)}catch{}}function $(b){try{const k=localStorage.getItem(wt+b);if(!k)return 0;const h=JSON.parse(k);if(!Array.isArray(h))return 0;const p=e.state.sessions.find(l=>l.session_id===b);if(!p)return h.length;const u=new Set((p.documents||[]).map(l=>l.filename));return h.filter(l=>!u.has(l.name)).length}catch{return 0}}async function C(b,k){return(await xt("/api/ingestion/preflight",{corpus:k,files:b})).manifest}return{resolveFolderFiles:i,readDirectoryHandle:c,uploadFilesWithConcurrency:r,renderUploadProgress:d,renderScanProgress:g,persistFolderPending:f,clearFolderPending:_,getStoredFolderPendingCount:$,requestPreflight:C}}function Ns(e,t,n,a){const{dom:s,stateController:o,setFlash:i}=e,{ingestionFolderInput:c,ingestionFileInput:r}=s;let d=!1,g=null;const f=150;function _(w){if(w.length===0)return;const v=new Set(e.state.intake.map(x=>Xe(x.file))),N=[];for(const x of w){const I=Xe(x,e.state.folderRelativePaths);v.has(I)||(v.add(I),N.push({file:x,relativePath:dt(x,e.state.folderRelativePaths),contentHash:null,verdict:"pending",preflightEntry:null}))}N.length!==0&&(o.setIntake([...e.state.intake,...N]),e.state.reviewPlan&&o.setReviewPlan({...e.state.reviewPlan,stalePartial:!0}),d=!1,$(),e.render())}function $(){g&&clearTimeout(g);const w=o.bumpPreflightRunId();g=setTimeout(()=>{g=null,C(w)},f)}async function C(w){if(w!==e.state.preflightRunId||e.state.intake.length===0)return;const v=e.state.intake.filter(N=>N.contentHash===null);try{if(v.length>0&&(await b(v),w!==e.state.preflightRunId))return;const N=await k();if(w!==e.state.preflightRunId)return;if(!N){d=!0,e.render();return}h(N),d=!1,e.render()}catch(N){if(w!==e.state.preflightRunId)return;console.error("[intake] preflight failed:",N),d=!0,e.render()}}async function b(w){o.setPreflightScanProgress({total:w.length,hashed:0,scanning:!0}),n.renderScanProgress();for(let v=0;v<w.length;v++){const N=w[v];try{const x=await N.file.arrayBuffer(),I=await crypto.subtle.digest("SHA-256",x),U=Array.from(new Uint8Array(I));N.contentHash=U.map(G=>G.toString(16).padStart(2,"0")).join("")}catch(x){console.warn(`[intake] hash failed for ${N.file.name}:`,x),N.verdict="unreadable",N.contentHash=""}o.setPreflightScanProgress({total:w.length,hashed:v+1,scanning:!0}),n.renderScanProgress()}o.setPreflightScanProgress(null)}async function k(){const w=e.state.intake.filter(v=>v.contentHash&&v.verdict!=="unreadable").map(v=>({filename:v.file.name,relative_path:v.relativePath||v.file.name,size:v.file.size,content_hash:v.contentHash}));if(w.length===0)return{artifacts:[],duplicates:[],revisions:[],new_files:[],scanned:0,elapsed_ms:0};try{return await n.requestPreflight(w,e.state.selectedCorpus)}catch(v){return console.error("[intake] /api/ingestion/preflight failed:",v),null}}function h(w){const v=new Map,N=(G,O)=>{for(const B of O){const L=B.relative_path||B.filename;v.set(L,{verdict:G,preflightEntry:B})}};N("new",w.new_files),N("revision",w.revisions),N("duplicate",w.duplicates),N("artifact",w.artifacts);const x=e.state.intake.map(G=>{if(G.verdict==="unreadable")return G;const O=G.relativePath||G.file.name,B=v.get(O);return B?{...G,verdict:B.verdict,preflightEntry:B.preflightEntry}:{...G,verdict:"pending"}}),I=x.filter(G=>G.verdict==="new"||G.verdict==="revision"),U=x.filter(G=>G.verdict==="duplicate"||G.verdict==="artifact"||G.verdict==="unreadable");o.setIntake(x),o.setReviewPlan({willIngest:I,bounced:U,scanned:w.scanned,elapsedMs:w.elapsed_ms,stalePartial:!1}),o.setPendingFiles(I.map(G=>G.file))}function p(w){const v=N=>Xe(N.file)!==Xe(w.file);if(o.setIntake(e.state.intake.filter(v)),e.state.reviewPlan){const N=e.state.reviewPlan.willIngest.filter(v);o.setReviewPlan({...e.state.reviewPlan,willIngest:N}),o.setPendingFiles(N.map(x=>x.file))}else o.setPendingFiles(e.state.pendingFiles.filter(N=>Xe(N)!==Xe(w.file)));e.render()}function u(){if(!e.state.reviewPlan)return;const w=new Set(e.state.reviewPlan.willIngest.map(N=>Xe(N.file))),v=e.state.intake.filter(N=>!w.has(Xe(N.file)));o.setIntake(v),o.setReviewPlan({...e.state.reviewPlan,willIngest:[]}),o.setPendingFiles([]),e.render()}function l(){g&&(clearTimeout(g),g=null),o.bumpPreflightRunId(),o.setIntake([]),o.setReviewPlan(null),o.setPendingFiles([]),o.setPreflightScanProgress(null),d=!1,e.state.folderRelativePaths.clear()}async function m(){const w=e.state.reviewPlan;if(w&&!w.stalePartial&&w.willIngest.length!==0&&!d){i(),o.setMutating(!0),a.renderControls();try{await a.directFolderIngest(),l(),c.value="",r.value=""}catch(v){o.setFolderUploadProgress(null),n.renderUploadProgress(),i(we(v),"error"),e.state.selectedSessionId&&t.refreshSelectedSession({sessionId:e.state.selectedSessionId,showWheel:!1,reportError:!1})}finally{o.setMutating(!1),a.renderControls()}}}return{addFilesToIntake:_,schedulePreflight:$,runIntakePreflight:C,hashIntakeEntries:b,preflightIntake:k,applyManifestToIntake:h,removeIntakeEntry:p,cancelAllWillIngest:u,clearIntake:l,confirmAndIngest:m,getIntakeError:()=>d,setIntakeError:w=>{d=w}}}function Ps(e,t){const{dom:n,i18n:a,stateController:s,setFlash:o}=e,{ingestionAutoStatus:i}=n,c=4e3;let r=null,d="";function g(){r&&(clearTimeout(r),r=null),d="",i.hidden=!0,i.classList.remove("is-running")}function f(C){const b=C.batch_summary,k=mt(C),h=Math.max(0,Number(b.queued??0)-k),p=Number(b.processing??0),u=Number(b.done??0),l=Number(b.failed??0),m=Number(b.bounced??0),w=h+p;i.hidden=!1;const v=m>0?` · ${m} rebotados`:"";w>0||k>0?(i.classList.add("is-running"),i.textContent=a.t("ops.ingestion.auto.running",{queued:h,processing:p,raw:k})+v):l>0?(i.classList.remove("is-running"),i.textContent=a.t("ops.ingestion.auto.done",{done:u,failed:l,raw:k})+v):(i.classList.remove("is-running"),i.textContent=a.t("ops.ingestion.auto.allDone",{done:u})+v)}async function _(){const C=d;if(C)try{const b=await t.fetchIngestionSession(C);s.upsertSession(b),e.render(),f(b);const k=b.batch_summary,h=mt(b),p=Number(k.total??0);if(p===0){g();return}h>0&&await qe(`/api/ingestion/sessions/${encodeURIComponent(C)}/auto-process`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({max_concurrency:5})});const u=h>0?await t.fetchIngestionSession(C):b,l=mt(u),m=Math.max(0,Number(u.batch_summary.queued??0)-l),w=Number(u.batch_summary.processing??0);m>0&&w===0&&await t.startIngestionProcess(C),h>0&&(s.upsertSession(u),e.render(),f(u));const v=m+w;if(p>0&&v===0&&l===0){if(Number(u.batch_summary.pending_batch_gate??0)>0&&u.status!=="running_batch_gates"&&u.status!=="completed")try{await t.validateBatch(C)}catch{}const x=await t.fetchIngestionSession(C);s.upsertSession(x),e.render(),f(x),g(),o(a.t("ops.ingestion.auto.allDone",{done:Number(x.batch_summary.done??0)}),"success");return}if(v===0&&l>0){i.classList.remove("is-running"),i.textContent=a.t("ops.ingestion.auto.done",{done:Number(u.batch_summary.done??0),failed:Number(u.batch_summary.failed??0),raw:l}),g();return}r=setTimeout(()=>void _(),c)}catch(b){g(),o(we(b),"error")}}function $(C){g(),d=C,i.hidden=!1,i.classList.add("is-running"),i.textContent=a.t("ops.ingestion.auto.running",{queued:0,processing:0,raw:0}),r=setTimeout(()=>void _(),2e3)}return{startAutoPilot:$,stopAutoPilot:g,updateAutoStatus:f,autoPilotTick:_}}function As(e){const{ctx:t,api:n,upload:a,intake:s,autoPilot:o}=e,{dom:i,stateController:c,i18n:r,setFlash:d,toast:g,withThinkingWheel:f}=t,{ingestionDropzone:_,ingestionFileInput:$,ingestionFolderInput:C,ingestionSelectFilesBtn:b,ingestionSelectFolderBtn:k,ingestionCorpusSelect:h,ingestionRefreshBtn:p,ingestionCreateSessionBtn:u,ingestionUploadBtn:l,ingestionProcessBtn:m,ingestionValidateBatchBtn:w,ingestionRetryBtn:v,ingestionDeleteSessionBtn:N,ingestionAutoProcessBtn:x,ingestionLastError:I,ingestionLogBody:U,ingestionLogAccordion:G,ingestionLogCopyBtn:O,ingestionKanban:B,ingestionUploadProgress:L}=i,{addFilesToIntake:E,clearIntake:M,confirmAndIngest:q}=s,{startAutoPilot:Z,stopAutoPilot:y}=o,{createIngestionSession:R,ejectIngestionSession:S,fetchCorpora:T,refreshIngestion:F,refreshSelectedSession:V,resolveSessionCorpus:oe,retryIngestionSession:le,startIngestionProcess:be,validateBatch:Ee}=n,{resolveFolderFiles:Pe,readDirectoryHandle:Ce}=a,{render:K,renderCorpora:ke,renderControls:pe,traceClear:Ae,directFolderIngest:Me,suppressPanelsOnNextRender:De}=e,{state:he}=c;_.addEventListener("click",()=>{$.disabled||$.click()}),_.addEventListener("keydown",D=>{D.key!=="Enter"&&D.key!==" "||(D.preventDefault(),$.disabled||$.click())});let Le=0;_.addEventListener("dragenter",D=>{D.preventDefault(),Le++,$.disabled||_.classList.add("is-dragover")}),_.addEventListener("dragover",D=>{D.preventDefault()}),_.addEventListener("dragleave",()=>{Le--,Le<=0&&(Le=0,_.classList.remove("is-dragover"))}),_.addEventListener("drop",async D=>{var te;if(D.preventDefault(),Le=0,_.classList.remove("is-dragover"),$.disabled)return;const W=D.dataTransfer;if(W){const Q=await Pe(W);if(Q.length>0){E(lt(Q));return}}const se=Array.from(((te=D.dataTransfer)==null?void 0:te.files)||[]);se.length!==0&&E(lt(se))}),$.addEventListener("change",()=>{const D=Array.from($.files||[]);D.length!==0&&E(lt(D))}),C.addEventListener("change",()=>{const D=Array.from(C.files||[]);D.length!==0&&E(lt(D))}),b.addEventListener("click",()=>{$.disabled||$.click()}),k.addEventListener("click",async()=>{if(!C.disabled){if(typeof window.showDirectoryPicker=="function")try{const D=await window.showDirectoryPicker({mode:"read"}),W=await Ce(D,D.name),se=lt(W);se.length>0?E(se):d(r.t("ops.ingestion.pendingNone"),"error");return}catch(D){if((D==null?void 0:D.name)==="AbortError")return}C.click()}}),h.addEventListener("change",()=>{c.setSelectedCorpus(h.value),c.setSessions([]),c.setSelectedSession(null),M(),d(),K(),F({showWheel:!0,reportError:!0})}),p.addEventListener("click",D=>{D.stopPropagation(),d(),F({showWheel:!0,reportError:!0})}),u.addEventListener("click",async()=>{y(),d(),M(),c.setPreflightManifest(null),c.setFolderUploadProgress(null),he.rejectedArtifacts=[],L.hidden=!0,L.innerHTML="",$.value="",C.value="",I.hidden=!0,Ae(),G.hidden=!0,U.textContent="",c.setMutating(!0),pe();try{const D=await f(async()=>R(oe()));c.upsertSession(D),K(),d(r.t("ops.ingestion.flash.sessionCreated",{id:D.session_id}),"success")}catch(D){d(we(D),"error")}finally{c.setMutating(!1),pe()}}),l.addEventListener("click",()=>{q()}),m.addEventListener("click",async()=>{const D=he.selectedSessionId;if(D){d(),c.setMutating(!0),pe();try{await f(async()=>be(D)),await V({sessionId:D,showWheel:!1,reportError:!1});const W=r.t("ops.ingestion.flash.processStarted",{id:D});d(W,"success"),g.show({message:W,tone:"success"})}catch(W){const se=we(W);d(se,"error"),g.show({message:se,tone:"error"})}finally{c.setMutating(!1),pe()}}}),w.addEventListener("click",async()=>{const D=he.selectedSessionId;if(D){d(),c.setMutating(!0),pe();try{await f(async()=>Ee(D)),await V({sessionId:D,showWheel:!1,reportError:!1});const W="Validación de lote iniciada";d(W,"success"),g.show({message:W,tone:"success"})}catch(W){const se=we(W);d(se,"error"),g.show({message:se,tone:"error"})}finally{c.setMutating(!1),pe()}}}),v.addEventListener("click",async()=>{const D=he.selectedSessionId;if(D){d(),c.setMutating(!0),pe();try{await f(async()=>le(D)),await V({sessionId:D,showWheel:!1,reportError:!1}),d(r.t("ops.ingestion.flash.retryStarted",{id:D}),"success")}catch(W){d(we(W),"error")}finally{c.setMutating(!1),pe()}}}),N.addEventListener("click",async()=>{var Q;const D=he.selectedSessionId;if(!D)return;const W=rn(he.selectedSession),se=W?r.t("ops.ingestion.confirm.ejectPostGate"):r.t("ops.ingestion.confirm.ejectPreGate");if(await g.confirm({title:r.t("ops.ingestion.actions.discardSession"),message:se,tone:"caution",confirmLabel:r.t("ops.ingestion.confirm.ejectLabel")})){y(),d(),c.setMutating(!0),pe();try{const fe=ht(String(((Q=he.selectedSession)==null?void 0:Q.status)||"")),ae=await f(async()=>S(D,fe||W));c.clearSelectionAfterDelete(),M(),c.setPreflightManifest(null),c.setFolderUploadProgress(null),he.rejectedArtifacts=[],L.hidden=!0,L.innerHTML="",$.value="",C.value="",I.hidden=!0,Ae(),G.hidden=!0,U.textContent="",await F({showWheel:!1,reportError:!1});const ce=Array.isArray(ae.errors)&&ae.errors.length>0,X=ae.path==="rollback"?r.t("ops.ingestion.flash.ejectedRollback",{id:D,count:ae.ejected_files}):r.t("ops.ingestion.flash.ejectedInstant",{id:D,count:ae.ejected_files}),ee=ce?"caution":"success";d(X,ce?"error":"success"),g.show({message:X,tone:ee}),ce&&g.show({message:r.t("ops.ingestion.flash.ejectedPartial"),tone:"caution",durationMs:8e3})}catch(fe){const ae=we(fe);d(ae,"error"),g.show({message:ae,tone:"error"})}finally{c.setMutating(!1),K()}}}),x.addEventListener("click",async()=>{const D=he.selectedSessionId;if(D){d(),c.setMutating(!0),pe();try{await f(async()=>qe(`/api/ingestion/sessions/${encodeURIComponent(D)}/auto-process`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({max_concurrency:5})})),await be(D),await V({sessionId:D,showWheel:!1,reportError:!1}),d(`Auto-procesamiento iniciado para ${D}`,"success"),Z(D)}catch(W){d(we(W),"error")}finally{c.setMutating(!1),pe()}}});const Te=document.getElementById("ingestion-log-toggle");Te&&(Te.addEventListener("click",D=>{if(D.target.closest(".ops-log-copy-btn"))return;const W=U.hidden;U.hidden=!W,Te.setAttribute("aria-expanded",String(W));const se=Te.querySelector(".ops-log-accordion-marker");se&&(se.textContent=W?"▾":"▸")}),Te.addEventListener("keydown",D=>{(D.key==="Enter"||D.key===" ")&&(D.preventDefault(),Te.click())})),O.addEventListener("click",D=>{D.preventDefault(),D.stopPropagation();const W=U.textContent||"";navigator.clipboard.writeText(W).then(()=>{const se=O.textContent;O.textContent=r.t("ops.ingestion.log.copied"),setTimeout(()=>{O.textContent=se},1500)}).catch(()=>{const se=document.createRange();se.selectNodeContents(U);const te=window.getSelection();te==null||te.removeAllRanges(),te==null||te.addRange(se)})}),B.addEventListener("click",async D=>{var ce;const W=D.target.closest("[data-action]");if(!W)return;const se=W.getAttribute("data-action"),te=W.getAttribute("data-doc-id"),Q=he.selectedSessionId;if(!Q||!te)return;if(se==="show-existing-dropdown"){const X=W.closest(".kanban-card"),ee=X==null?void 0:X.querySelector(".kanban-ag-fallback-panel");ee&&(ee.hidden=!ee.hidden);return}let fe="",ae="";if(se==="assign"){const X=W.closest(".kanban-card"),ee=X==null?void 0:X.querySelector("[data-field='topic']"),$e=X==null?void 0:X.querySelector("[data-field='type']");if(fe=(ee==null?void 0:ee.value)||"",ae=($e==null?void 0:$e.value)||"",!fe||!ae){ee&&!fe&&ee.classList.add("kanban-select--invalid"),$e&&!ae&&$e.classList.add("kanban-select--invalid");return}}d(),c.setMutating(!0),pe();try{switch(se){case"assign":{await f(async()=>qe(`/api/ingestion/sessions/${encodeURIComponent(Q)}/documents/${encodeURIComponent(te)}/classify`,{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify({topic:fe,batch_type:ae})})),De.add(te);break}case"replace-dup":{await f(async()=>qe(`/api/ingestion/sessions/${encodeURIComponent(Q)}/documents/${encodeURIComponent(te)}/resolve-duplicate`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action:"replace"})}));break}case"add-new-dup":{await f(async()=>qe(`/api/ingestion/sessions/${encodeURIComponent(Q)}/documents/${encodeURIComponent(te)}/resolve-duplicate`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action:"add_new"})}));break}case"discard-dup":case"discard":{await f(async()=>qe(`/api/ingestion/sessions/${encodeURIComponent(Q)}/documents/${encodeURIComponent(te)}/resolve-duplicate`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action:"discard"})}));break}case"accept-synonym":{const X=W.closest(".kanban-card"),ee=X==null?void 0:X.querySelector("[data-field='type']"),$e=(ee==null?void 0:ee.value)||"";await f(async()=>qe(`/api/ingestion/sessions/${encodeURIComponent(Q)}/documents/${encodeURIComponent(te)}/accept-autogenerar`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action:"accept_synonym",type:$e||void 0})})),De.add(te);break}case"accept-new-topic":{const X=W.closest(".kanban-card"),ee=X==null?void 0:X.querySelector("[data-field='autogenerar-label']"),$e=X==null?void 0:X.querySelector("[data-field='type']"),Re=((ce=ee==null?void 0:ee.value)==null?void 0:ce.trim())||"",Ie=($e==null?void 0:$e.value)||"";if(!Re||Re.length<3){ee&&ee.classList.add("kanban-select--invalid");return}await f(async()=>qe(`/api/ingestion/sessions/${encodeURIComponent(Q)}/documents/${encodeURIComponent(te)}/accept-autogenerar`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action:"accept_new_topic",edited_label:Re,type:Ie||void 0})})),De.add(te),await T(),ke();break}case"retry":{await f(async()=>qe(`/api/ingestion/sessions/${encodeURIComponent(Q)}/documents/${encodeURIComponent(te)}/retry`,{method:"POST"}));break}case"remove":break}await V({sessionId:Q,showWheel:!1,reportError:!1})}catch(X){d(we(X),"error")}finally{c.setMutating(!1),pe()}});const de=i.addCorpusDialog,ve=i.addCorpusBtn;if(de&&ve){let D=function(X){return X.normalize("NFD").replace(/[̀-ͯ]/g,"").toLowerCase().replace(/[^a-z0-9]+/g,"_").replace(/^_|_$/g,"")};const W=de.querySelector("#add-corpus-label"),se=de.querySelector("#add-corpus-key"),te=de.querySelector("#add-corpus-kw-strong"),Q=de.querySelector("#add-corpus-kw-weak"),fe=de.querySelector("#add-corpus-error"),ae=de.querySelector("#add-corpus-cancel"),ce=de.querySelector("#add-corpus-form");ve.addEventListener("click",()=>{W&&(W.value=""),se&&(se.value=""),te&&(te.value=""),Q&&(Q.value=""),fe&&(fe.hidden=!0),de.showModal(),W==null||W.focus()}),W==null||W.addEventListener("input",()=>{se&&(se.value=D(W.value))}),ae==null||ae.addEventListener("click",()=>{de.close()}),ce==null||ce.addEventListener("submit",async X=>{X.preventDefault(),fe&&(fe.hidden=!0);const ee=(W==null?void 0:W.value.trim())||"";if(!ee)return;const $e=((te==null?void 0:te.value)||"").split(",").map(Ie=>Ie.trim()).filter(Boolean),Re=((Q==null?void 0:Q.value)||"").split(",").map(Ie=>Ie.trim()).filter(Boolean);try{await f(async()=>xt("/api/corpora",{label:ee,keywords_strong:$e.length?$e:void 0,keywords_weak:Re.length?Re:void 0})),de.close(),await F({showWheel:!1,reportError:!1});const Ie=D(ee);Ie&&c.setSelectedCorpus(Ie),K(),d(`Categoría "${ee}" creada.`,"success")}catch(Ie){fe&&(fe.textContent=we(Ie),fe.hidden=!1)}})}}function Is(e){const{i18n:t,stateController:n,dom:a,withThinkingWheel:s,setFlash:o}=e,{ingestionCorpusSelect:i,ingestionBatchTypeSelect:c,ingestionDropzone:r,ingestionFileInput:d,ingestionFolderInput:g,ingestionSelectFilesBtn:f,ingestionSelectFolderBtn:_,ingestionUploadProgress:$,ingestionPendingFiles:C,ingestionOverview:b,ingestionRefreshBtn:k,ingestionCreateSessionBtn:h,ingestionUploadBtn:p,ingestionProcessBtn:u,ingestionAutoProcessBtn:l,ingestionValidateBatchBtn:m,ingestionRetryBtn:w,ingestionDeleteSessionBtn:v,ingestionSessionMeta:N,ingestionSessionsList:x,selectedSessionMeta:I,ingestionLastError:U,ingestionLastErrorMessage:G,ingestionLastErrorGuidance:O,ingestionLastErrorNext:B,ingestionKanban:L,ingestionLogAccordion:E,ingestionLogBody:M,ingestionLogCopyBtn:q,ingestionAutoStatus:Z}=a,{state:y}=n,R=Ss(e);R.toast;const S=Cs(R),{resolveSessionCorpus:T,fetchCorpora:F,fetchIngestionSessions:V,fetchIngestionSession:oe,createIngestionSession:le,uploadIngestionFile:be,startIngestionProcess:Ee,validateBatch:Pe,retryIngestionSession:Ce,ejectIngestionSession:K,refreshIngestion:ke,refreshSelectedSession:pe,ensureSelectedSession:Ae}=S,Me=Es(R,S),{resolveFolderFiles:De,readDirectoryHandle:he,uploadFilesWithConcurrency:Le,renderUploadProgress:Te,renderScanProgress:de,persistFolderPending:ve,clearFolderPending:D,getStoredFolderPendingCount:W,requestPreflight:se}=Me;let te=[];function Q(P){const H=`[${new Date().toISOString().slice(11,23)}] ${P}`;te.push(H),console.log(`[folder-ingest] ${P}`),E.hidden=!1,M.hidden=!1,M.textContent=te.join(`
`);const j=document.getElementById("ingestion-log-toggle");if(j){j.setAttribute("aria-expanded","true");const Y=j.querySelector(".ops-log-accordion-marker");Y&&(Y.textContent="▾")}}function fe(){te=[],ae()}function ae(){const{ingestionBounceLog:P,ingestionBounceBody:A}=a;P&&(P.hidden=!0,P.open=!1),A&&(A.textContent="")}const ce={directFolderIngest:()=>Promise.resolve(),renderControls:()=>{}},X=Ns(R,S,Me,ce),{addFilesToIntake:ee,clearIntake:$e,confirmAndIngest:Re,removeIntakeEntry:Ie,cancelAllWillIngest:Je}=X,Ve=new Set;function ut(){const P=y.selectedCorpus;i.innerHTML="";const A=document.createElement("option");A.value="autogenerar",A.textContent="AUTOGENERAR",A.selected=P==="autogenerar",i.appendChild(A),[...y.corpora].sort((H,j)=>H.label.localeCompare(j.label,"es")).forEach(H=>{var z;const j=document.createElement("option");j.value=H.key;const Y=((z=H.attention)==null?void 0:z.length)||0;let ne=H.active?H.label:`${H.label} (${t.t("ops.ingestion.corpusInactiveOption")})`;Y>0&&(ne+=` ⚠ ${Y}`),j.textContent=ne,j.selected=H.key===P,i.appendChild(j)})}function kn(P,A,H){var _e;const j=document.createElement("div");j.className="ops-intake-row",A.verdict==="pending"&&j.classList.add("ops-intake-row--pending"),H.readonly&&j.classList.add("ops-intake-row--readonly");const Y=document.createElement("span");Y.className="ops-intake-row__icon",Y.textContent="📄";const ne=document.createElement("span");ne.className="ops-intake-row__name",ne.textContent=A.relativePath||A.file.name,ne.title=A.relativePath||A.file.name;const z=document.createElement("span");z.className="ops-intake-row__size",z.textContent=ws(A.file.size);const ie=$s(A,t);if(j.append(Y,ne,z,ie),H.showReason&&((_e=A.preflightEntry)!=null&&_e.reason)){const ue=document.createElement("span");ue.className="ops-intake-row__reason",ue.textContent=A.preflightEntry.reason,ue.title=A.preflightEntry.reason,j.appendChild(ue)}if(H.removable){const ue=document.createElement("button");ue.type="button",ue.className="ops-intake-row__remove",ue.textContent="✕",ue.title=t.t("ops.ingestion.willIngest.cancelAll"),ue.addEventListener("click",Oe=>{Oe.stopPropagation(),Ie(A)}),j.appendChild(ue)}P.appendChild(j)}function vt(P,A,H,j,Y,ne){const z=document.createElement("section");z.className=`ops-intake-panel ops-intake-panel--${P}`;const ie=document.createElement("header");ie.className="ops-intake-panel__header";const _e=document.createElement("span");_e.className="ops-intake-panel__title",_e.textContent=t.t(A),ie.appendChild(_e);const ue=document.createElement("span");if(ue.className="ops-intake-panel__count",ue.textContent=t.t(H,{count:j}),ie.appendChild(ue),ne.readonly){const Se=document.createElement("span");Se.className="ops-intake-panel__readonly",Se.textContent=t.t("ops.ingestion.bounced.readonly"),ie.appendChild(Se)}if(ne.cancelAllAction){const Se=document.createElement("button");Se.type="button",Se.className="ops-intake-panel__action",Se.textContent=t.t("ops.ingestion.willIngest.cancelAll"),Se.addEventListener("click",He=>{He.stopPropagation(),ne.cancelAllAction()}),ie.appendChild(Se)}z.appendChild(ie);const Oe=document.createElement("div");return Oe.className="ops-intake-panel__body",Y.forEach(Se=>kn(Oe,Se,ne)),z.appendChild(Oe),z}function $n(){var j,Y;if((j=r.querySelector(".ops-intake-windows"))==null||j.remove(),(Y=r.querySelector(".dropzone-file-list"))==null||Y.remove(),y.intake.length===0){C.textContent=t.t("ops.ingestion.pendingNone"),C.hidden=!0,r.classList.remove("has-files");return}C.hidden=!0,r.classList.add("has-files");const P=document.createElement("div");P.className="ops-intake-windows";const A=Cn();A&&P.appendChild(A),P.appendChild(vt("intake","ops.ingestion.intake.title","ops.ingestion.intake.count",y.intake.length,y.intake,{removable:!1,readonly:!1,showReason:!1}));const H=y.reviewPlan;H&&(P.appendChild(vt("will-ingest","ops.ingestion.willIngest.title","ops.ingestion.willIngest.count",H.willIngest.length,H.willIngest,{removable:!0,readonly:!1,showReason:!1,cancelAllAction:H.willIngest.length>0?()=>Je():void 0})),H.bounced.length>0&&P.appendChild(vt("bounced","ops.ingestion.bounced.title","ops.ingestion.bounced.count",H.bounced.length,H.bounced,{removable:!1,readonly:!0,showReason:!0}))),r.appendChild(P)}function Cn(){var z;const P=((z=y.reviewPlan)==null?void 0:z.stalePartial)===!0,A=y.intake.some(ie=>ie.verdict==="pending"),H=X.getIntakeError();if(!P&&!A&&!H)return null;const j=document.createElement("div");if(j.className="ops-intake-banner",H){j.classList.add("ops-intake-banner--error");const ie=document.createElement("span");ie.className="ops-intake-banner__text",ie.textContent=t.t("ops.ingestion.intake.failed");const _e=document.createElement("button");return _e.type="button",_e.className="ops-intake-banner__retry",_e.textContent=t.t("ops.ingestion.intake.retry"),_e.addEventListener("click",ue=>{ue.stopPropagation(),X.setIntakeError(!1),X.schedulePreflight(),ot()}),j.append(ie,_e),j}const Y=document.createElement("span");Y.className="ops-intake-banner__spinner",j.appendChild(Y);const ne=document.createElement("span");return ne.className="ops-intake-banner__text",P?(j.classList.add("ops-intake-banner--stale"),ne.textContent=t.t("ops.ingestion.intake.stale")):(j.classList.add("ops-intake-banner--verifying"),ne.textContent=t.t("ops.ingestion.intake.verifying")),j.appendChild(ne),j}function at(){var Ue,Qe,it,rt,me;const P=n.selectedCorpusConfig(),A=y.selectedSession,H=y.selectedCorpus==="autogenerar"?y.corpora.some(Be=>Be.active):!!(P!=null&&P.active),j=ht(String((A==null?void 0:A.status)||""));c.value=c.value||"autogenerar";const Y=((Ue=y.folderUploadProgress)==null?void 0:Ue.uploading)??!1,ne=y.reviewPlan,z=(ne==null?void 0:ne.willIngest.length)??0,ie=(ne==null?void 0:ne.stalePartial)===!0,_e=X.getIntakeError()===!0,ue=!!ne&&z>0&&!ie&&!_e;h.disabled=y.mutating||!H,f.disabled=y.mutating||!H||Y,_.disabled=y.mutating||!H||Y||j,p.disabled=y.mutating||!H||!ue||Y,ne?z===0?p.textContent=t.t("ops.ingestion.approveNone"):p.textContent=t.t("ops.ingestion.approveCount",{count:z}):p.textContent=t.t("ops.ingestion.approve"),u.disabled=y.mutating||!H||!A||j,l.disabled=y.mutating||!H||Y||!A||j,l.textContent=`▶ ${t.t("ops.ingestion.actions.autoProcess")}`;const Oe=Number(((Qe=A==null?void 0:A.batch_summary)==null?void 0:Qe.done)||0),Se=Number(((it=A==null?void 0:A.batch_summary)==null?void 0:it.queued)||0)+Number(((rt=A==null?void 0:A.batch_summary)==null?void 0:rt.processing)||0),He=Number(((me=A==null?void 0:A.batch_summary)==null?void 0:me.pending_batch_gate)||0),Fe=Oe>=1&&(Se>=1||He>=1);if(m.disabled=y.mutating||!H||!A||j||!Fe,w.disabled=y.mutating||!H||!A||j,v.disabled=y.mutating||!A,k.disabled=y.mutating,i.disabled=y.mutating||y.corpora.length===0,d.disabled=y.mutating||!H,!H){b.textContent=t.t("ops.ingestion.corpusInactive");return}b.textContent=t.t("ops.ingestion.overview",{active:y.corpora.filter(Be=>Be.active).length,total:y.corpora.length,corpus:y.selectedCorpus==="autogenerar"?"AUTOGENERAR":(P==null?void 0:P.label)||y.selectedCorpus,session:(A==null?void 0:A.session_id)||t.t("ops.ingestion.noSession")})}function Sn(){if(x.innerHTML="",N.textContent=y.selectedSession?`${y.selectedSession.session_id} · ${y.selectedSession.status}`:t.t("ops.ingestion.selectedEmpty"),y.sessions.length===0){const P=document.createElement("li");P.className="ops-empty",P.textContent=t.t("ops.ingestion.sessionsEmpty"),x.appendChild(P);return}y.sessions.forEach(P=>{var it,rt;const A=document.createElement("li"),H=P.status==="partial_failed",j=document.createElement("button");j.type="button",j.className=`ops-session-item${P.session_id===y.selectedSessionId?" is-active":""}${H?" has-retry-action":""}`,j.dataset.sessionId=P.session_id;const Y=document.createElement("div");Y.className="ops-session-item-head";const ne=document.createElement("div");ne.className="ops-session-id",ne.textContent=P.session_id;const z=document.createElement("span");z.className=`meta-chip status-${ct(P.status)}`,z.textContent=P.status,Y.append(ne,z);const ie=document.createElement("div");ie.className="ops-session-pills";const _e=((it=y.corpora.find(me=>me.key===P.corpus))==null?void 0:it.label)||P.corpus,ue=document.createElement("span");ue.className="meta-chip ops-pill-corpus",ue.textContent=_e,ie.appendChild(ue);const Oe=P.documents||[];[...new Set(Oe.map(me=>me.batch_type).filter(Boolean))].forEach(me=>{const Be=document.createElement("span");Be.className="meta-chip ops-pill-batch",Be.textContent=Qn(me,t),ie.appendChild(Be)});const He=Oe.map(me=>me.filename).filter(Boolean);let Fe=null;if(He.length>0){Fe=document.createElement("div"),Fe.className="ops-session-files";const me=He.slice(0,3),Be=He.length-me.length;Fe.textContent=me.join(", ")+(Be>0?` +${Be}`:"")}const Ue=document.createElement("div");Ue.className="ops-session-summary",Ue.textContent=zt(P.batch_summary,t);const Qe=document.createElement("div");if(Qe.className="ops-session-summary",Qe.textContent=P.updated_at?t.formatDateTime(P.updated_at,{dateStyle:"short",timeStyle:"short",timeZone:"America/Bogota"}):"-",j.appendChild(Y),j.appendChild(ie),Fe&&j.appendChild(Fe),j.appendChild(Ue),j.appendChild(Qe),(rt=P.last_error)!=null&&rt.code){const me=document.createElement("div");me.className="ops-session-summary status-error",me.textContent=P.last_error.code,j.appendChild(me)}if(j.addEventListener("click",async()=>{n.setSelectedSession(P),ot();try{await pe({sessionId:P.session_id,showWheel:!0})}catch{}}),A.appendChild(j),H){const me=document.createElement("button");me.type="button",me.className="ops-session-retry-inline",me.textContent=t.t("ops.ingestion.actions.retry"),me.disabled=y.mutating,me.addEventListener("click",async Be=>{Be.stopPropagation(),me.disabled=!0,n.setMutating(!0),at();try{await s(async()=>Ce(P.session_id)),await ke({showWheel:!1,reportError:!0,focusSessionId:P.session_id}),o(t.t("ops.ingestion.flash.retryStarted",{id:P.session_id}),"success")}catch(In){o(we(In),"error")}finally{n.setMutating(!1),at()}}),A.appendChild(me)}x.appendChild(A)})}function En(P){const A=[],H=()=>new Date().toISOString();if(A.push(t.t("ops.ingestion.log.sessionHeader",{id:P.session_id})),A.push(`Corpus:     ${P.corpus||"-"}`),A.push(`Status:     ${P.status}`),A.push(`Created:    ${P.created_at||"-"}`),A.push(`Updated:    ${P.updated_at||"-"}`),A.push(`Heartbeat:  ${P.heartbeat_at??"-"}`),P.auto_processing&&A.push(`Auto-proc:  ${P.auto_processing}`),P.gate_sub_stage&&A.push(`Gate-stage: ${P.gate_sub_stage}`),P.wip_sync_status&&A.push(`WIP-sync:   ${P.wip_sync_status}`),P.batch_summary){const Y=P.batch_summary,ne=(P.documents||[]).filter(ie=>ie.status==="raw"||ie.status==="needs_classification").length,z=(P.documents||[]).filter(ie=>ie.status==="pending_dedup").length;A.push(""),A.push("── Resumen del lote ──"),A.push(`  Total: ${Y.total}  Queued: ${Y.queued}  Processing: ${Y.processing}  Done: ${Y.done}  Failed: ${Y.failed}  Duplicados: ${Y.skipped_duplicate}  Bounced: ${Y.bounced}`),ne>0&&A.push(`  Raw (sin clasificar): ${ne}`),z>0&&A.push(`  Pending dedup: ${z}`)}P.last_error&&(A.push(""),A.push("── Error de sesión ──"),A.push(`  Código:    ${P.last_error.code||"-"}`),A.push(`  Mensaje:   ${P.last_error.message||"-"}`),A.push(`  Guía:      ${P.last_error.guidance||"-"}`),A.push(`  Siguiente: ${P.last_error.next_step||"-"}`));const j=P.documents||[];if(j.length===0)A.push(""),A.push(t.t("ops.ingestion.log.noDocuments"));else{A.push(""),A.push(`── Documentos (${j.length}) ──`);const Y={failed:0,processing:1,in_progress:1,queued:2,raw:2,done:3,completed:3,bounced:4,skipped_duplicate:5},ne=[...j].sort((z,ie)=>(Y[z.status]??3)-(Y[ie.status]??3));for(const z of ne)A.push(""),A.push(`  ┌─ ${z.filename} (${z.doc_id})`),A.push(`  │  Status:   ${z.status}  │  Stage: ${z.stage||"-"}  │  Progress: ${z.progress??0}%`),A.push(`  │  Bytes:    ${z.bytes??"-"}  │  Batch: ${z.batch_type||"-"}`),z.source_relative_path&&A.push(`  │  Path:     ${z.source_relative_path}`),(z.detected_topic||z.detected_type)&&(A.push(`  │  Topic:    ${z.detected_topic||"-"}  │  Type: ${z.detected_type||"-"}  │  Confidence: ${z.combined_confidence??"-"}`),z.classification_source&&A.push(`  │  Classifier: ${z.classification_source}`)),z.chunk_count!=null&&A.push(`  │  Chunks:   ${z.chunk_count}  │  Elapsed: ${z.elapsed_ms??"-"}ms`),z.dedup_match_type&&A.push(`  │  Dedup:    ${z.dedup_match_type}  │  Match: ${z.dedup_match_doc_id||"-"}`),z.replaced_doc_id&&A.push(`  │  Replaced: ${z.replaced_doc_id}`),z.error&&(A.push("  │  ❌ ERROR"),A.push(`  │    Código:    ${z.error.code||"-"}`),A.push(`  │    Mensaje:   ${z.error.message||"-"}`),A.push(`  │    Guía:      ${z.error.guidance||"-"}`),A.push(`  │    Siguiente: ${z.error.next_step||"-"}`)),A.push(`  │  Created: ${z.created_at||"-"}  │  Updated: ${z.updated_at||"-"}`),A.push("  └─")}return A.push(""),A.push(`Log generado: ${H()}`),A.join(`
`)}function Lt(){if(te.length>0)return;const P=y.selectedSession;if(!P){E.hidden=!0,M.textContent="";return}E.hidden=!1,M.textContent=En(P)}function Nn(){const P=y.selectedSession;if(!P){I.textContent=t.t("ops.ingestion.selectedEmpty"),U.hidden=!0,te.length===0&&(E.hidden=!0),L.innerHTML="";return}const A=W(P.session_id),H=A>0?` · ${t.t("ops.ingestion.folderResumePending",{count:A})}`:"";if(I.textContent=`${P.session_id} · ${zt(P.batch_summary,t)}${H}`,P.last_error?(U.hidden=!1,G.textContent=P.last_error.message||P.last_error.code||"-",O.textContent=P.last_error.guidance||"",B.textContent=`${t.t("ops.ingestion.lastErrorNext")}: ${P.last_error.next_step||"-"}`):U.hidden=!0,(P.documents||[]).length===0){L.innerHTML=`<p class="ops-empty">${t.t("ops.ingestion.documentsEmpty")}</p>`,L.style.minHeight="0",Lt();return}L.style.minHeight="",vs(P,L,t,Ve,y.corpora),Ve.clear(),Lt()}function ot(){ut(),$n(),at(),Sn(),Nn()}R.render=ot,R.trace=Q,ce.directFolderIngest=Rt,ce.renderControls=at;const Tt=Ps(R,S),{startAutoPilot:Pn,stopAutoPilot:Ba,updateAutoStatus:ja}=Tt;async function Rt(){var Oe,Se,He;Q(`directFolderIngest: ${y.pendingFiles.length} archivos pendientes`);const P=await Ae();Q(`Sesión asignada: ${P.session_id} (corpus=${P.corpus}, status=${P.status})`);const A=c.value||"autogenerar";Q(`Subiendo ${y.pendingFiles.length} archivos con batchType="${A}"...`),ve(P.session_id);const H=await Le(P.session_id,[...y.pendingFiles],A,Pt);if(console.log("[folder-ingest] Upload result:",{uploaded:H.uploaded,failed:H.failed}),Q(`Upload completo: ${H.uploaded} subidos, ${H.failed} fallidos${H.errors.length>0?" — "+H.errors.slice(0,5).map(Fe=>`${Fe.filename}: ${Fe.error}`).join("; "):""}`),n.setPendingFiles([]),n.setFolderUploadProgress(null),D(P.session_id),g.value="",d.value="",H.failed>0&&H.uploaded===0){const Fe=H.errors.slice(0,3).map(Ue=>`${Ue.filename}: ${Ue.error}`).join("; ");Q(`TODOS FALLARON: ${Fe}`),o(`${t.t("ops.ingestion.flash.folderUploadPartial",H)} — ${Fe}`,"error"),await ke({showWheel:!1,reportError:!0,focusSessionId:P.session_id});return}Q("Consultando estado de sesión post-upload...");const j=await oe(P.session_id),Y=Number(((Oe=j.batch_summary)==null?void 0:Oe.bounced)??0),ne=mt(j),z=Number(((Se=j.batch_summary)==null?void 0:Se.queued)??0),ie=Number(((He=j.batch_summary)==null?void 0:He.total)??0),_e=ie-Y;if(Q(`Sesión post-upload: total=${ie} bounced=${Y} raw=${ne} queued=${z} actionable=${_e}`),_e===0&&Y>0){Q(`TODOS REBOTADOS: ${Y} archivos ya existen en el corpus`),n.upsertSession(j),o(`${Y} archivos ya existen en el corpus (rebotados). 0 archivos nuevos para procesar.`,"error"),Q("--- FIN (todo rebotado) ---");return}Q("Auto-procesando con threshold=0 (force-queue)..."),await qe(`/api/ingestion/sessions/${encodeURIComponent(P.session_id)}/auto-process`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({max_concurrency:5,auto_accept_threshold:0})}),await Ee(P.session_id),await ke({showWheel:!1,reportError:!0,focusSessionId:P.session_id});const ue=[];H.uploaded>0&&ue.push(`${_e} archivos en proceso`),Y>0&&ue.push(`${Y} rebotados`),H.failed>0&&ue.push(`${H.failed} fallidos`),o(ue.join(" · "),H.failed>0?"error":"success"),Q(`Auto-piloto iniciado para ${P.session_id}`),Q("--- FIN (éxito) ---"),Pn(P.session_id)}function An(){As({ctx:R,api:S,upload:Me,intake:X,autoPilot:Tt,render:ot,renderCorpora:ut,renderControls:at,traceClear:fe,directFolderIngest:Rt,suppressPanelsOnNextRender:Ve})}return{bindEvents:An,refreshIngestion:ke,refreshSelectedSession:pe,render:ot}}function Ye(e){if(e==null)return null;const t=Number(e);return!Number.isFinite(t)||t<0?null:t}function gn({i18n:e,stateController:t,dom:n,withThinkingWheel:a,setFlash:s}){const{monitorTabBtn:o,ingestionTabBtn:i,controlTabBtn:c,embeddingsTabBtn:r,reindexTabBtn:d,monitorPanel:g,ingestionPanel:f,controlPanel:_,embeddingsPanel:$,reindexPanel:C,runsBody:b,timelineNode:k,timelineMeta:h,cascadeNote:p,userCascadeNode:u,userCascadeSummary:l,technicalCascadeNode:m,technicalCascadeSummary:w,refreshRunsBtn:v}=n,{state:N}=t;function x(S){const T=Ye(S);return T===null?"-":`${e.formatNumber(T/1e3,{minimumFractionDigits:2,maximumFractionDigits:2})} s`}function I(S){t.setActiveTab(S),U()}function U(){if(!o)return;const S=N.activeTab;o.classList.toggle("is-active",S==="monitor"),o.setAttribute("aria-selected",String(S==="monitor")),i==null||i.classList.toggle("is-active",S==="ingestion"),i==null||i.setAttribute("aria-selected",String(S==="ingestion")),c==null||c.classList.toggle("is-active",S==="control"),c==null||c.setAttribute("aria-selected",String(S==="control")),r==null||r.classList.toggle("is-active",S==="embeddings"),r==null||r.setAttribute("aria-selected",String(S==="embeddings")),d==null||d.classList.toggle("is-active",S==="reindex"),d==null||d.setAttribute("aria-selected",String(S==="reindex")),g&&(g.hidden=S!=="monitor",g.classList.toggle("is-active",S==="monitor")),f&&(f.hidden=S!=="ingestion",f.classList.toggle("is-active",S==="ingestion")),_&&(_.hidden=S!=="control",_.classList.toggle("is-active",S==="control")),$&&($.hidden=S!=="embeddings",$.classList.toggle("is-active",S==="embeddings")),C&&(C.hidden=S!=="reindex",C.classList.toggle("is-active",S==="reindex"))}function G(S){if(k.innerHTML="",!Array.isArray(S)||S.length===0){k.innerHTML=`<li>${e.t("ops.timeline.empty")}</li>`;return}S.forEach(T=>{const F=document.createElement("li");F.innerHTML=`
        <strong>${T.stage||"-"}</strong> · <span class="status-${ct(String(T.status||""))}">${T.status||"-"}</span><br/>
        <small>${T.at||"-"} · ${T.duration_ms||0} ms</small>
        <pre>${JSON.stringify(T.details||{},null,2)}</pre>
      `,k.appendChild(F)})}function O(S,T,F){const V=Ye(T==null?void 0:T.total_ms),oe=V===null?e.t("ops.timeline.summaryPending"):x(V),le=F==="user"&&String((T==null?void 0:T.chat_run_id)||"").trim()?` · chat_run ${String((T==null?void 0:T.chat_run_id)||"").trim()}`:"";S.textContent=`${e.t("ops.timeline.totalLabel")} ${oe}${le}`}function B(S){var be,Ee,Pe;const T=[],F=String(((be=S.details)==null?void 0:be.source)||"").trim(),V=String(S.status||"").trim();F&&T.push(F),V&&V!=="ok"&&V!=="missing"&&T.push(V);const oe=Number(((Ee=S.details)==null?void 0:Ee.citations_count)||0);Number.isFinite(oe)&&oe>0&&T.push(`${oe} refs`);const le=String(((Pe=S.details)==null?void 0:Pe.panel_status)||"").trim();return le&&T.push(le),T.join(" · ")}function L(S,T,F){S.innerHTML="";const V=Array.isArray(T==null?void 0:T.steps)?(T==null?void 0:T.steps)||[]:[];if(V.length===0){S.innerHTML=`<li class="ops-cascade-step is-empty">${e.t("ops.timeline.waterfallEmpty")}</li>`;return}const oe=Ye(T==null?void 0:T.total_ms)??Math.max(1,...V.map(le=>Ye(le.cumulative_ms)??Ye(le.absolute_elapsed_ms)??0));V.forEach(le=>{const be=Ye(le.duration_ms),Ee=Ye(le.offset_ms)??0,Pe=Ye(le.absolute_elapsed_ms),Ce=document.createElement("li");Ce.className=`ops-cascade-step ops-cascade-step--${F}${be===null?" is-missing":""}`;const K=document.createElement("div");K.className="ops-cascade-step-head";const ke=document.createElement("div"),pe=document.createElement("strong");pe.textContent=le.label||"-";const Ae=document.createElement("small");Ae.className="ops-cascade-step-meta",Ae.textContent=be===null?e.t("ops.timeline.missingStep"):`${e.t("ops.timeline.stepLabel")} ${x(be)} · T+${x(Pe??le.cumulative_ms)}`,ke.append(pe,Ae);const Me=document.createElement("span");Me.className=`meta-chip status-${ct(String(le.status||""))}`,Me.textContent=String(le.status||(be===null?"missing":"ok")),K.append(ke,Me),Ce.appendChild(K);const De=document.createElement("div");De.className="ops-cascade-track";const he=document.createElement("span");he.className="ops-cascade-segment";const Le=Math.max(0,Math.min(100,Ee/oe*100)),Te=be===null?0:Math.max(be/oe*100,be>0?2.5:0);he.style.left=`${Le}%`,he.style.width=`${Te}%`,he.setAttribute("aria-label",be===null?`${le.label}: ${e.t("ops.timeline.missingStep")}`:`${le.label}: ${x(be)}`),De.appendChild(he),Ce.appendChild(De);const de=B(le);if(de){const ve=document.createElement("p");ve.className="ops-cascade-step-detail",ve.textContent=de,Ce.appendChild(ve)}S.appendChild(Ce)})}async function E(){return(await Ne("/api/ops/runs?limit=30")).runs||[]}async function M(S){return Ne(`/api/ops/runs/${encodeURIComponent(S)}/timeline`)}function q(S,T){var V;const F=S.run||{};h.textContent=e.t("ops.timeline.label",{id:T}),p.textContent=e.t("ops.timeline.selectedRunMeta",{trace:String(F.trace_id||"-"),chatRun:String(((V=S.user_waterfall)==null?void 0:V.chat_run_id)||F.chat_run_id||"-")}),O(l,S.user_waterfall,"user"),O(w,S.technical_waterfall,"technical"),L(u,S.user_waterfall,"user"),L(m,S.technical_waterfall,"technical"),G(Array.isArray(S.timeline)?S.timeline:[])}function Z(S){if(b.innerHTML="",!Array.isArray(S)||S.length===0){const T=document.createElement("tr");T.innerHTML=`<td colspan="4">${e.t("ops.runs.empty")}</td>`,b.appendChild(T);return}S.forEach(T=>{const F=document.createElement("tr");F.innerHTML=`
        <td><button type="button" class="link-btn" data-run-id="${T.run_id}">${T.run_id}</button></td>
        <td>${T.trace_id||"-"}</td>
        <td class="status-${ct(String(T.status||""))}">${T.status||"-"}</td>
        <td>${T.started_at?e.formatDateTime(T.started_at,{dateStyle:"short",timeStyle:"short",timeZone:"America/Bogota"}):"-"}</td>
      `,b.appendChild(F)}),b.querySelectorAll("button[data-run-id]").forEach(T=>{T.addEventListener("click",async()=>{const F=T.getAttribute("data-run-id")||"";try{const V=await a(async()=>M(F));q(V,F)}catch(V){u.innerHTML=`<li class="ops-cascade-step is-empty status-error">${we(V)}</li>`,m.innerHTML=`<li class="ops-cascade-step is-empty status-error">${we(V)}</li>`,k.innerHTML=`<li class="status-error">${we(V)}</li>`}})})}async function y({showWheel:S=!0,reportError:T=!0}={}){const F=async()=>{const V=await E();Z(V)};try{S?await a(F):await F()}catch(V){b.innerHTML=`<tr><td colspan="4" class="status-error">${we(V)}</td></tr>`,T&&s(we(V),"error")}}function R(){o==null||o.addEventListener("click",()=>{I("monitor")}),i==null||i.addEventListener("click",()=>{I("ingestion")}),c==null||c.addEventListener("click",()=>{I("control")}),r==null||r.addEventListener("click",()=>{I("embeddings")}),d==null||d.addEventListener("click",()=>{I("reindex")}),v.addEventListener("click",()=>{s(),y({showWheel:!0,reportError:!0})})}return{bindEvents:R,refreshRuns:y,renderTabs:U}}function Ge(e){return String(e??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#39;")}function et(e){return(e??0).toLocaleString("es-CO")}function xs(e){if(e==null||e<=0)return"-";const t=Math.floor(e/60),n=Math.floor(e%60);return t>0?`${t}m ${n}s`:`${n}s`}function Ls(e){if(!e.length)return"";let t='<ol class="reindex-stage-list">';for(const n of e){const a=n.state==="completed"?"ops-dot-ok":n.state==="active"?"ops-dot-active":n.state==="failed"?"ops-dot-error":"ops-dot-pending",s=n.state==="active"?`<strong>${Ge(n.label)}</strong>`:Ge(n.label);t+=`<li class="reindex-stage-item reindex-stage-${n.state}"><span class="ops-dot ${a}">●</span> ${s}</li>`}return t+="</ol>",t}function fn({dom:e,setFlash:t,navigateToEmbeddings:n}){const{container:a}=e;let s=null,o="";function i(){var p,u,l;const f=s;if(!f){a.innerHTML='<p class="ops-text-muted">Cargando estado de re-index...</p>';return}const _=f.current_operation||f.last_operation,$=((p=f.current_operation)==null?void 0:p.status)==="running",C=!f.current_operation;let b="";const k=$?"En ejecución":C?"Inactivo":(_==null?void 0:_.status)??"—",h=$?"tone-yellow":(_==null?void 0:_.status)==="completed"?"tone-green":(_==null?void 0:_.status)==="failed"?"tone-red":"";if(b+=`<div class="reindex-status-row">
      <span class="corpus-status-chip ${h}">${Ge(k)}</span>
      <span class="emb-target-badge">WIP</span>
      ${$?`<span class="emb-heartbeat ${Et(_==null?void 0:_.heartbeat_at,_==null?void 0:_.updated_at)}">${Et(_==null?void 0:_.heartbeat_at,_==null?void 0:_.updated_at)}</span>`:""}
    </div>`,b+='<div class="reindex-controls">',C&&(b+=`<button class="corpus-btn corpus-btn-promote" id="reindex-start-btn" ${o?"disabled":""}>Iniciar re-index</button>`),$&&_&&(b+=`<button class="corpus-btn corpus-btn-rollback" id="reindex-stop-btn" ${o?"disabled":""}>Detener</button>`),b+="</div>",(u=_==null?void 0:_.stages)!=null&&u.length&&(b+=Ls(_.stages)),_!=null&&_.progress){const m=_.progress,w=[];m.documents_processed!=null&&w.push(`Documentos: ${et(m.documents_processed)} / ${et(m.documents_total)}`),m.documents_indexed!=null&&w.push(`Documentos indexados: ${et(m.documents_indexed)}`),m.elapsed_seconds!=null&&w.push(`Tiempo: ${xs(m.elapsed_seconds)}`),w.length&&(b+=`<div class="reindex-progress-stats">${w.map(v=>`<span>${Ge(v)}</span>`).join("")}</div>`)}if(_!=null&&_.quality_report){const m=_.quality_report;if(b+='<div class="reindex-quality-report">',b+="<h3>Reporte de calidad</h3>",b+=`<div class="emb-stats-grid">
        <div class="emb-stat"><span class="emb-stat-value">${et(m.documents_indexed)}</span><span class="emb-stat-label">Documentos</span></div>
        <div class="emb-stat"><span class="emb-stat-value">${et(m.chunks_generated)}</span><span class="emb-stat-label">Chunks</span></div>
        <div class="emb-stat"><span class="emb-stat-value">${m.blocking_issues??0}</span><span class="emb-stat-label">Blocking issues</span></div>
      </div>`,m.knowledge_class_counts){b+='<div class="reindex-kc-breakdown"><h4>Knowledge classes</h4><dl class="reindex-kc-dl">';for(const[w,v]of Object.entries(m.knowledge_class_counts))b+=`<dt>${Ge(w)}</dt><dd>${et(v)}</dd>`;b+="</dl></div>"}b+="</div>",b+=`<div class="reindex-embed-prompt">
        <p>Re-index completado. Para aplicar los nuevos summaries a los embeddings:</p>
        <button class="corpus-btn corpus-btn-promote" id="reindex-embed-now-btn">Embed ahora</button>
      </div>`}if((l=_==null?void 0:_.checks)!=null&&l.length){b+='<div class="emb-checks">';for(const m of _.checks){const w=m.ok?'<span class="ops-dot ops-dot-ok">●</span>':'<span class="ops-dot ops-dot-error">●</span>';b+=`<div class="emb-check">${w} <strong>${Ge(m.label)}</strong>: ${Ge(m.detail)}</div>`}b+="</div>"}_!=null&&_.log_tail&&(b+=`<details class="emb-log-accordion"><summary>Log</summary><pre class="emb-log-tail">${Ge(_.log_tail)}</pre></details>`),_!=null&&_.error&&(b+=`<p class="emb-error">${Ge(_.error)}</p>`),a.innerHTML=b}function c(){a.addEventListener("click",f=>{const _=f.target;_.id==="reindex-start-btn"&&r(),_.id==="reindex-stop-btn"&&d(),_.id==="reindex-embed-now-btn"&&n()})}async function r(){o="start",i();try{await ze("/api/ops/reindex/start",{mode:"from_source"}),t("Re-index iniciado","success")}catch(f){t(String(f),"error")}o="",await g()}async function d(){var _;const f=(_=s==null?void 0:s.current_operation)==null?void 0:_.job_id;if(f){o="stop",i();try{await ze("/api/ops/reindex/stop",{job_id:f}),t("Re-index detenido","success")}catch($){t(String($),"error")}o="",await g()}}async function g(){try{s=await Ne("/api/ops/reindex-status")}catch{}i()}return{bindEvents:c,refresh:g}}const Qa=Object.freeze(Object.defineProperty({__proto__:null,createOpsReindexController:fn},Symbol.toStringTag,{value:"Module"})),Ts=3e3,Ut=8e3;function bn({stateController:e,withThinkingWheel:t,setFlash:n,refreshRuns:a,refreshIngestion:s,refreshCorpusLifecycle:o,refreshEmbeddings:i,refreshReindex:c,intervalMs:r}){(async()=>{try{await t(async()=>{await Promise.all([a({showWheel:!1,reportError:!1}),s({showWheel:!1,reportError:!1}),o==null?void 0:o(),i==null?void 0:i(),c==null?void 0:c()])})}catch($){n(we($),"error")}})();let d=null,g=r??Ut;function f(){const $=e.state.selectedSession;return $?ht(String($.status||""))?!0:($.documents||[]).some(b=>b.status==="in_progress"||b.status==="processing"||b.status==="extracting"||b.status==="etl"||b.status==="writing"||b.status==="gates"):!1}function _(){const $=r??(f()?Ts:Ut);d!==null&&$===g||(d!==null&&window.clearInterval(d),g=$,d=window.setInterval(()=>{a({showWheel:!1,reportError:!1}),s({showWheel:!1,reportError:!1,focusSessionId:e.getFocusedRunningSessionId()}),o==null||o(),i==null||i(),c==null||c(),r||_()},g))}return _(),()=>{d!==null&&(window.clearInterval(d),d=null)}}function hn(){const e={activeTab:Kn(),corpora:[],selectedCorpus:"autogenerar",sessions:[],selectedSessionId:Yn(),selectedSession:null,pendingFiles:[],intake:[],reviewPlan:null,preflightRunId:0,mutating:!1,folderUploadProgress:null,folderRelativePaths:new Map,rejectedArtifacts:[],preflightManifest:null,preflightScanProgress:null};function t(){return e.corpora.find(l=>l.key===e.selectedCorpus)}function n(l){e.activeTab=l,Xn(l)}function a(l){e.corpora=[...l]}function s(l){e.folderUploadProgress=l}function o(l){e.preflightManifest=l}function i(l){e.preflightScanProgress=l}function c(l){e.mutating=l}function r(l){e.pendingFiles=[...l]}function d(l){e.intake=[...l]}function g(l){e.reviewPlan=l?{...l,willIngest:[...l.willIngest],bounced:[...l.bounced]}:null}function f(){return e.preflightRunId+=1,e.preflightRunId}function _(l){e.selectedCorpus=l}function $(l){e.selectedSession=l,e.selectedSessionId=(l==null?void 0:l.session_id)||"",Zn((l==null?void 0:l.session_id)||null),l&&(k=!1)}function C(){k=!0,$(null)}function b(l){e.sessions=[...l]}let k=!1;function h(){if(e.selectedSessionId){const l=e.sessions.find(m=>m.session_id===e.selectedSessionId)||null;$(l);return}if(k){$(null);return}$(e.sessions[0]||null)}function p(l){const m=e.sessions.filter(w=>w.session_id!==l.session_id);e.sessions=[l,...m].sort((w,v)=>Date.parse(String(v.updated_at||0))-Date.parse(String(w.updated_at||0))),$(l)}function u(){var l;return ht(String(((l=e.selectedSession)==null?void 0:l.status)||""))?e.selectedSessionId:""}return{state:e,clearSelectionAfterDelete:C,getFocusedRunningSessionId:u,selectedCorpusConfig:t,setActiveTab:n,setCorpora:a,setFolderUploadProgress:s,setMutating:c,setPendingFiles:r,setIntake:d,setReviewPlan:g,bumpPreflightRunId:f,setPreflightManifest:o,setPreflightScanProgress:i,setSelectedCorpus:_,setSelectedSession:$,setSessions:b,syncSelectedSession:h,upsertSession:p}}function Rs(e){const{value:t,unit:n,size:a="md",className:s=""}=e,o=document.createElement("span");o.className=["lia-metric-value",`lia-metric-value--${a}`,s].filter(Boolean).join(" "),o.setAttribute("data-lia-component","metric-value");const i=document.createElement("span");if(i.className="lia-metric-value__number",i.textContent=typeof t=="number"?t.toLocaleString("es-CO"):String(t),o.appendChild(i),n){const c=document.createElement("span");c.className="lia-metric-value__unit",c.textContent=n,o.appendChild(c)}return o}function pt(e){const{label:t,value:n,unit:a,hint:s,size:o="lg",tone:i="neutral",className:c=""}=e,r=document.createElement("div");r.className=["lia-metric-card",`lia-metric-card--${i}`,c].filter(Boolean).join(" "),r.setAttribute("data-lia-component","metric-card");const d=document.createElement("p");if(d.className="lia-metric-card__label",d.textContent=t,r.appendChild(d),r.appendChild(Rs({value:n,unit:a,size:o})),s){const g=document.createElement("p");g.className="lia-metric-card__hint",g.textContent=s,r.appendChild(g)}return r}function qs(e){if(!e)return"sin activar";try{const t=new Date(e);if(Number.isNaN(t.getTime()))return"—";const n=Date.now()-t.getTime(),a=Math.floor(n/6e4);if(a<1)return"hace instantes";if(a<60)return`hace ${a} min`;const s=Math.floor(a/60);return s<24?`hace ${s} h`:`hace ${Math.floor(s/24)} d`}catch{return"—"}}function Ms(e){const t=document.createElement("section");t.className="lia-corpus-overview",t.setAttribute("data-lia-component","corpus-overview");const n=document.createElement("header");n.className="lia-corpus-overview__header";const a=document.createElement("h2");a.className="lia-corpus-overview__title",a.textContent="Corpus activo",n.appendChild(a);const s=document.createElement("p");if(s.className="lia-corpus-overview__subtitle",e.activeGenerationId){const i=document.createElement("code");i.textContent=e.activeGenerationId,s.appendChild(document.createTextNode("Generación ")),s.appendChild(i),s.appendChild(document.createTextNode(` · activada ${qs(e.activatedAt)}`))}else s.textContent="Ninguna generación activa en Supabase.";n.appendChild(s),t.appendChild(n);const o=document.createElement("div");return o.className="lia-corpus-overview__grid",o.appendChild(pt({label:"Documentos servidos",value:e.documents,hint:e.documents>0?`${e.chunks.toLocaleString("es-CO")} chunks indexados`:"—"})),o.appendChild(pt({label:"Grafo de normativa",value:e.graphNodes,unit:"nodos",hint:`${e.graphEdges.toLocaleString("es-CO")} relaciones tipadas`,tone:e.graphOk?"success":"warning"})),o.appendChild(pt({label:"Auditoría del corpus",value:e.auditIncluded,unit:"incluidos",hint:`${e.auditScanned.toLocaleString("es-CO")} escaneados · ${e.auditExcluded.toLocaleString("es-CO")} excluidos`})),o.appendChild(pt({label:"Revisiones pendientes",value:e.auditPendingRevisions,hint:e.auditPendingRevisions===0?"Cuello limpio":"Requieren resolución",tone:e.auditPendingRevisions===0?"success":"warning"})),t.appendChild(o),t}function Ds(e){const{tone:t,pulse:n=!1,ariaLabel:a,className:s=""}=e,o=document.createElement("span");return o.className=["lia-status-dot",`lia-status-dot--${t}`,n?"lia-status-dot--pulse":"",s].filter(Boolean).join(" "),o.setAttribute("data-lia-component","status-dot"),o.setAttribute("role","status"),a&&o.setAttribute("aria-label",a),o}const Os={active:"active",superseded:"idle",running:"running",queued:"running",failed:"error",pending:"warning"},Wt={active:"Activa",superseded:"Reemplazada",running:"En curso",queued:"En cola",failed:"Falló",pending:"Pendiente"};function vn(e){const{status:t,className:n=""}=e,a=document.createElement("span");a.className=["lia-run-status",`lia-run-status--${t}`,n].filter(Boolean).join(" "),a.setAttribute("data-lia-component","run-status"),a.appendChild(Ds({tone:Os[t],pulse:t==="running"||t==="queued",ariaLabel:Wt[t]}));const s=document.createElement("span");return s.className="lia-run-status__label",s.textContent=Wt[t],a.appendChild(s),a}function Fs(e){if(!e)return"—";try{const t=new Date(e);return Number.isNaN(t.getTime())?"—":t.toLocaleString("es-CO",{day:"numeric",month:"short",hour:"2-digit",minute:"2-digit"})}catch{return e}}function Bs(e,t){const n=document.createElement(t?"button":"div");n.className="lia-generation-row",n.setAttribute("data-lia-component","generation-row"),t&&(n.type="button",n.addEventListener("click",()=>t(e.generationId)));const a=document.createElement("span");a.className="lia-generation-row__id",a.textContent=e.generationId,n.appendChild(a),n.appendChild(vn({status:e.status}));const s=document.createElement("span");s.className="lia-generation-row__date",s.textContent=Fs(e.generatedAt),n.appendChild(s);const o=document.createElement("span");o.className="lia-generation-row__count",o.textContent=`${e.documents.toLocaleString("es-CO")} docs`,n.appendChild(o);const i=document.createElement("span");if(i.className="lia-generation-row__count lia-generation-row__count--muted",i.textContent=`${e.chunks.toLocaleString("es-CO")} chunks`,n.appendChild(i),e.topClass&&e.topClassCount){const c=document.createElement("span");c.className="lia-generation-row__family",c.textContent=`${e.topClass}: ${e.topClassCount.toLocaleString("es-CO")}`,n.appendChild(c)}if(e.subtopicCoverage){const c=e.subtopicCoverage,r=e.documents>0?e.documents:1,d=Math.round(c.docsWithSubtopic/r*100),g=document.createElement("span");g.className="lia-generation-row__subtopic",g.setAttribute("data-lia-component","generation-row-subtopic");const f=c.docsRequiringReview&&c.docsRequiringReview>0?` (${c.docsRequiringReview} por revisar)`:"";g.textContent=`subtema: ${d}%${f}`,n.appendChild(g)}return n}function Gt(e){const{rows:t,emptyMessage:n="Aún no hay generaciones registradas.",errorMessage:a,onSelect:s}=e,o=document.createElement("section");o.className="lia-generations-list",o.setAttribute("data-lia-component","generations-list");const i=document.createElement("header");i.className="lia-generations-list__header";const c=document.createElement("h2");c.className="lia-generations-list__title",c.textContent="Generaciones recientes",i.appendChild(c);const r=document.createElement("p");r.className="lia-generations-list__subtitle",r.textContent="Cada fila es una corrida de python -m lia_graph.ingest publicada en Supabase.",i.appendChild(r),o.appendChild(i);const d=document.createElement("div");if(d.className="lia-generations-list__body",a){const g=document.createElement("p");g.className="lia-generations-list__feedback lia-generations-list__feedback--error",g.textContent=a,d.appendChild(g)}else if(t.length===0){const g=document.createElement("p");g.className="lia-generations-list__feedback",g.textContent=n,d.appendChild(g)}else{const g=document.createElement("div");g.className="lia-generations-list__head-row",["Generación","Estado","Fecha","Documentos","Chunks","Familia principal"].forEach(f=>{const _=document.createElement("span");_.className="lia-generations-list__head-cell",_.textContent=f,g.appendChild(_)}),d.appendChild(g),t.forEach(f=>d.appendChild(Bs(f,s)))}return o.appendChild(d),o}const js=[{key:"knowledge_base",label:"knowledge_base/",sublabel:"snapshot Dropbox"},{key:"wip",label:"WIP",sublabel:"Supabase local + Falkor local"},{key:"cloud",label:"Cloud",sublabel:"Supabase cloud + Falkor cloud"}];function zs(e){const{activeStage:t,className:n=""}=e,a=document.createElement("nav");return a.className=["lia-pipeline-flow",n].filter(Boolean).join(" "),a.setAttribute("data-lia-component","pipeline-flow"),a.setAttribute("aria-label","Pipeline de ingestión Lia Graph"),js.forEach((s,o)=>{if(o>0){const d=document.createElement("span");d.className="lia-pipeline-flow__arrow",d.setAttribute("aria-hidden","true"),d.textContent="→",a.appendChild(d)}const i=document.createElement("div");i.className=["lia-pipeline-flow__stage",s.key===t?"lia-pipeline-flow__stage--active":""].filter(Boolean).join(" "),i.setAttribute("data-stage",s.key);const c=document.createElement("span");c.className="lia-pipeline-flow__label",c.textContent=s.label,i.appendChild(c);const r=document.createElement("span");r.className="lia-pipeline-flow__sublabel",r.textContent=s.sublabel,i.appendChild(r),a.appendChild(i)}),a}function Hs(e){const{activeJobId:t,lastRunStatus:n,disabled:a,onTrigger:s}=e,o=document.createElement("section");o.className="lia-run-trigger",o.setAttribute("data-lia-component","run-trigger-card");const i=document.createElement("header");i.className="lia-run-trigger__header";const c=document.createElement("h3");c.className="lia-run-trigger__title",c.textContent="Ingesta completa",i.appendChild(c);const r=document.createElement("p");r.className="lia-run-trigger__subtitle",r.innerHTML="Lee <code>knowledge_base/</code> en disco completo y lo reconstruye desde cero: re-audita, re-clasifica, re-parsea y re-publica los ~1.3k documentos. Tarda 30–40 minutos y cuesta aprox. US$ 6–16 en LLM. Úsala cuando cambie el clasificador, la taxonomía, o quieras un baseline limpio. Para cambios puntuales, prefiere Delta aditivo.",i.appendChild(r);const d=document.createElement("p");d.className="lia-run-trigger__safety",d.innerHTML="<strong>Seguridad:</strong> por defecto escribe a la base local (WIP). Solo promueve a la nube cuando el resultado esté validado — desde la pestaña Promoción.",i.appendChild(d),o.appendChild(i),o.appendChild(zs({activeStage:"wip"}));const g=document.createElement("form");g.className="lia-run-trigger__form",g.setAttribute("novalidate","");const f=Us({name:"supabase_target",legend:"¿Dónde escribir?",options:[{value:"wip",label:"Base local (recomendado)",hint:"Escribe a Supabase y FalkorDB locales en Docker. Ciclo seguro: no afecta la base de producción.",defaultChecked:!0},{value:"production",label:"Producción (nube)",hint:"Escribe directo a Supabase y FalkorDB en la nube. Afecta lo que ven los usuarios hoy."}]});g.appendChild(f);const _=Gs({name:"suin_scope",label:"Incluir jurisprudencia SUIN (opcional)",placeholder:"déjalo vacío si solo quieres re-ingerir la base",hint:"Además del corpus base, incluye documentos SUIN-Juriscol descargados. Valores válidos: et · tributario · laboral · jurisprudencia."});g.appendChild(_);const $=Ws([{name:"skip_embeddings",label:"Saltar embeddings",hint:"No recalcula los embeddings al final. Usa esto solo si vas a correrlos manualmente después.",defaultChecked:!1},{name:"auto_promote",label:"Promover a la nube al terminar",hint:"Si la ingesta local termina sin errores, encadena automáticamente una promoción a la nube.",defaultChecked:!1}]);g.appendChild($);const C=document.createElement("div");C.className="lia-run-trigger__submit-row";const b=document.createElement("button");if(b.type="submit",b.className="lia-button lia-button--primary lia-run-trigger__submit",b.textContent=t?"Ejecutando…":"Reconstruir todo",b.disabled=a,C.appendChild(b),n&&C.appendChild(vn({status:n})),t){const k=document.createElement("code");k.className="lia-run-trigger__job-id",k.textContent=t,C.appendChild(k)}return g.appendChild(C),g.addEventListener("submit",k=>{if(k.preventDefault(),a)return;const h=new FormData(g),p=h.get("supabase_target")||"wip",u=String(h.get("suin_scope")||"").trim(),l=h.get("skip_embeddings")!=null,m=h.get("auto_promote")!=null;s({suinScope:u,supabaseTarget:p==="production"?"production":"wip",autoEmbed:!l,autoPromote:m})}),o.appendChild(g),o}function Us(e){const t=document.createElement("fieldset");t.className="lia-run-trigger__field lia-run-trigger__field--radio";const n=document.createElement("legend");return n.className="lia-run-trigger__legend",n.textContent=e.legend,t.appendChild(n),e.options.forEach(a=>{const s=document.createElement("label");s.className="lia-run-trigger__radio-row";const o=document.createElement("input");o.type="radio",o.name=e.name,o.value=a.value,a.defaultChecked&&(o.defaultChecked=!0),s.appendChild(o);const i=document.createElement("span");i.className="lia-run-trigger__radio-text";const c=document.createElement("span");if(c.className="lia-run-trigger__radio-label",c.textContent=a.label,i.appendChild(c),a.hint){const r=document.createElement("span");r.className="lia-run-trigger__radio-hint",r.textContent=a.hint,i.appendChild(r)}s.appendChild(i),t.appendChild(s)}),t}function Ws(e){const t=document.createElement("fieldset");t.className="lia-run-trigger__field lia-run-trigger__field--checkbox";const n=document.createElement("legend");return n.className="lia-run-trigger__legend",n.textContent="Opciones de corrida",t.appendChild(n),e.forEach(a=>{const s=document.createElement("label");s.className="lia-run-trigger__checkbox-row";const o=document.createElement("input");o.type="checkbox",o.name=a.name,a.defaultChecked&&(o.defaultChecked=!0),s.appendChild(o);const i=document.createElement("span");i.className="lia-run-trigger__checkbox-text";const c=document.createElement("span");if(c.className="lia-run-trigger__checkbox-label",c.textContent=a.label,i.appendChild(c),a.hint){const r=document.createElement("span");r.className="lia-run-trigger__checkbox-hint",r.textContent=a.hint,i.appendChild(r)}s.appendChild(i),t.appendChild(s)}),t}function Gs(e){const t=document.createElement("div");t.className="lia-run-trigger__field lia-run-trigger__field--text";const n=document.createElement("label");n.className="lia-run-trigger__label",n.htmlFor=`lia-run-trigger-${e.name}`,n.textContent=e.label,t.appendChild(n);const a=document.createElement("input");if(a.type="text",a.id=`lia-run-trigger-${e.name}`,a.name=e.name,a.className="lia-input lia-run-trigger__input",a.autocomplete="off",a.spellcheck=!1,e.placeholder&&(a.placeholder=e.placeholder),t.appendChild(a),e.hint){const s=document.createElement("p");s.className="lia-run-trigger__hint",s.textContent=e.hint,t.appendChild(s)}return t}const Jt=["B","KB","MB","GB","TB"];function Vt(e){if(!Number.isFinite(e)||e<=0)return"0 B";let t=0,n=e;for(;n>=1024&&t<Jt.length-1;)n/=1024,t+=1;const a=t===0?Math.round(n):Math.round(n*10)/10;return`${Number.isInteger(a)?`${a}`:a.toFixed(1)} ${Jt[t]}`}function Js(e){const t=e.toLowerCase();return t.endsWith(".pdf")?"📕":t.endsWith(".docx")||t.endsWith(".doc")?"📘":t.endsWith(".md")?"📄":t.endsWith(".txt")?"📃":"📄"}function Vs(e){const{filename:t,bytes:n,onRemove:a,className:s=""}=e,o=document.createElement("span");o.className=["lia-file-chip",s].filter(Boolean).join(" "),o.setAttribute("data-lia-component","file-chip"),o.title=`${t} - ${Vt(n)}`;const i=document.createElement("span");i.className="lia-file-chip__icon",i.setAttribute("aria-hidden","true"),i.textContent=Js(t),o.appendChild(i);const c=document.createElement("span");c.className="lia-file-chip__name",c.textContent=t,o.appendChild(c);const r=document.createElement("span");if(r.className="lia-file-chip__size",r.textContent=Vt(n),o.appendChild(r),a){const d=document.createElement("button");d.type="button",d.className="lia-file-chip__remove",d.setAttribute("aria-label",`Quitar ${t}`),d.textContent="x",d.addEventListener("click",g=>{g.preventDefault(),g.stopPropagation(),a()}),o.appendChild(d)}return o}function Kt(e){const{subtopicKey:t,label:n,confidence:a,requiresReview:s,isNew:o,className:i=""}=e;let c="brand";s?c="warning":o&&(c="info");const r=n&&n.trim()?n:t,d=a!=null&&!Number.isNaN(a)?`${r} · ${Math.round(a<=1?a*100:a)}%`:r,g=nt({label:d,tone:c,emphasis:"soft",className:["lia-subtopic-chip",i].filter(Boolean).join(" "),dataComponent:"subtopic-chip"});return g.setAttribute("data-subtopic-key",t),s&&g.setAttribute("data-subtopic-review","true"),o&&g.setAttribute("data-subtopic-new","true"),g}function Ks(e){if(e==null||Number.isNaN(e))return"-";const t=e<=1?e*100:e;return`${Math.round(t)}%`}function Xs(e){if(e==null||Number.isNaN(e))return"neutral";const t=e<=1?e*100:e;return t>=80?"success":t>=50?"warning":"error"}function Ys(e){const{filename:t,bytes:n,detectedTopic:a,topicLabel:s,combinedConfidence:o,requiresReview:i,coercionMethod:c,subtopicKey:r,subtopicLabel:d,subtopicConfidence:g,subtopicIsNew:f,requiresSubtopicReview:_,onRemove:$,className:C=""}=e,b=document.createElement("div");b.className=["lia-intake-file-row",C].filter(Boolean).join(" "),b.setAttribute("data-lia-component","intake-file-row");const k=document.createElement("span");k.className="lia-intake-file-row__file",k.appendChild(Vs({filename:t,bytes:n,onRemove:$})),b.appendChild(k);const h=document.createElement("span");if(h.className="lia-intake-file-row__meta",s||a){const p=xn({label:s||a||"sin tópico",tone:"info",emphasis:"soft",className:"lia-intake-file-row__topic"});a&&p.setAttribute("data-topic",a),h.appendChild(p)}if(o!=null){const p=nt({label:Ks(o),tone:Xs(o),emphasis:"soft",className:"lia-intake-file-row__confidence"});h.appendChild(p)}if(i){const p=nt({label:"requiere revisión",tone:"warning",emphasis:"solid",className:"lia-intake-file-row__review"});p.setAttribute("role","status"),h.appendChild(p)}if(r?h.appendChild(Kt({subtopicKey:r,label:d||null,confidence:g??null,isNew:f,requiresReview:_,className:"lia-intake-file-row__subtopic"})):f&&e.subtopicKey!==void 0&&h.appendChild(Kt({subtopicKey:"(nuevo)",label:d||"subtema propuesto",isNew:!0,className:"lia-intake-file-row__subtopic"})),_&&!r){const p=nt({label:"subtema pendiente",tone:"warning",emphasis:"soft",className:"lia-intake-file-row__subtopic-review"});p.setAttribute("data-subtopic-review","true"),h.appendChild(p)}if(c){const p=document.createElement("span");p.className="lia-intake-file-row__coercion",p.textContent=c,h.appendChild(p)}return b.appendChild(h),b}function _n(e={}){const{size:t="inline",ariaLabel:n,className:a=""}=e,s=document.createElement("span");return s.className=["lia-spinner",`lia-spinner--${t}`,a].filter(Boolean).join(" "),s.setAttribute("data-lia-component","spinner"),s.setAttribute("role","status"),n?s.setAttribute("aria-label",n):s.setAttribute("aria-hidden","true"),s}const At="intake-drop-zone.lastBatch";function Zs(){try{if(typeof localStorage>"u")return null;const e=localStorage.getItem(At);if(!e)return null;const t=JSON.parse(e);return!t||typeof t!="object"?null:t}catch{return null}}function kt(e){try{if(typeof localStorage>"u")return;if(e==null){localStorage.removeItem(At);return}localStorage.setItem(At,JSON.stringify(e))}catch{}}const Qs=[".md",".txt",".json",".pdf",".docx"];function ea(e){const t=e.toLowerCase();return Qs.some(n=>t.endsWith(n))}function ta(e){return e.split("/").filter(Boolean).some(n=>n.startsWith("."))}function na(e){return e.includes("__MACOSX/")||e.startsWith("__MACOSX/")}function sa(e,t){return!(!e||na(t)||ta(t)||e.startsWith(".")||!ea(e))}async function aa(e){const t=[];for(;;){const n=await new Promise(a=>{e.readEntries(s=>a(s||[]))});if(n.length===0)break;t.push(...n)}return t}async function yn(e,t){if(!e)return[];const n=t?`${t}/${e.name}`:e.name;if(e.isFile){if(!e.file)return[];const a=await new Promise(s=>e.file(s));return[{filename:a.name,bytes:a.size,mime:a.type||void 0,relativePath:n,file:a}]}if(e.isDirectory&&e.createReader){const a=e.createReader(),s=await aa(a);return(await Promise.all(s.map(i=>yn(i,n)))).flat()}return[]}async function oa(e){const t=e.items?Array.from(e.items):[];if(t.length>0&&typeof t[0].webkitGetAsEntry=="function"){const a=[];for(const s of t){const o=s.webkitGetAsEntry();if(!o)continue;const i=await yn(o,"");a.push(...i)}return a}return(e.files?Array.from(e.files):[]).map(a=>({filename:a.name,bytes:a.size,mime:a.type||void 0,relativePath:a.name,file:a}))}function ia(e,t){return t?{filename:t.filename||e.filename,mime:t.mime||e.mime,bytes:t.bytes??e.bytes,detectedTopic:t.detected_topic??null,topicLabel:t.topic_label??null,combinedConfidence:t.combined_confidence??null,requiresReview:!!t.requires_review,coercionMethod:t.coercion_method??null,subtopicKey:t.subtopic_key??null,subtopicLabel:t.subtopic_label??null,subtopicConfidence:t.subtopic_confidence??null,subtopicIsNew:!!t.subtopic_is_new,requiresSubtopicReview:!!t.requires_subtopic_review}:{filename:e.filename,mime:e.mime,bytes:e.bytes,detectedTopic:null,topicLabel:null,combinedConfidence:null,requiresReview:!1,coercionMethod:null}}function ra(e){const{onIntake:t,onApprove:n,confirmDestructive:a}=e,s=document.createElement("section");s.className="lia-intake-drop-zone",s.setAttribute("data-lia-component","intake-drop-zone");const o=document.createElement("header");o.className="lia-intake-drop-zone__header";const i=document.createElement("h2");i.className="lia-intake-drop-zone__title",i.textContent="Arrastra archivos o carpetas",o.appendChild(i);const c=document.createElement("p");c.className="lia-intake-drop-zone__hint",c.textContent="Acepta .md, .txt, .json, .pdf, .docx. Carpetas se recorren recursivamente. Ocultos y __MACOSX/ se descartan.",o.appendChild(c),s.appendChild(o);const r=document.createElement("div");r.className="lia-intake-drop-zone__zone",r.setAttribute("role","button"),r.setAttribute("tabindex","0"),r.setAttribute("aria-label","Zona de arrastre para ingesta");const d=document.createElement("p");d.className="lia-intake-drop-zone__zone-label",d.textContent="Suelta aquí los archivos para enviarlos al intake",r.appendChild(d),s.appendChild(r);const g=document.createElement("div");g.className="lia-intake-drop-zone__list",g.setAttribute("data-role","intake-file-list"),s.appendChild(g);const f=document.createElement("p");f.className="lia-intake-drop-zone__feedback",f.setAttribute("role","status"),s.appendChild(f);const _=document.createElement("div");_.className="lia-intake-drop-zone__actions";const $=document.createElement("button");$.type="button",$.className="lia-button lia-button--ghost lia-intake-drop-zone__clear",$.textContent="Borrar todo",$.hidden=!0,_.appendChild($);const C=document.createElement("button");C.type="button",C.className="lia-button lia-button--primary lia-intake-drop-zone__approve",C.disabled=!0;const b=document.createElement("span");b.className="lia-intake-drop-zone__approve-label",b.textContent="Aprobar e ingerir",C.appendChild(b),_.appendChild(C),s.appendChild(_);const k={queued:[],lastResponse:null,analyzing:!1};function h(){var N;if(g.replaceChildren(),k.queued.length===0){const x=document.createElement("p");x.className="lia-intake-drop-zone__empty",x.textContent="Sin archivos en cola.",g.appendChild(x);return}const v=new Map;if((N=k.lastResponse)!=null&&N.files)for(const x of k.lastResponse.files)x.filename&&v.set(x.filename,x);k.queued.forEach((x,I)=>{const U=v.get(x.filename),G=Ys({...ia(x,U),onRemove:()=>{k.queued.splice(I,1),h(),p()}});g.appendChild(G)})}function p(){var N,x;const v=((x=(N=k.lastResponse)==null?void 0:N.summary)==null?void 0:x.placed)??0;if(C.classList.remove("lia-intake-drop-zone__approve--analyzing","lia-intake-drop-zone__approve--ready"),C.replaceChildren(),k.analyzing){C.disabled=!0,C.classList.add("lia-intake-drop-zone__approve--analyzing"),C.appendChild(_n({size:"sm",ariaLabel:"Analizando"}));const I=document.createElement("span");I.className="lia-intake-drop-zone__approve-label",I.textContent="Analizando archivos",C.appendChild(I)}else{const I=document.createElement("span");I.className="lia-intake-drop-zone__approve-label",I.textContent="Ir al siguiente paso →",C.appendChild(I),C.disabled=v<=0,v>0&&C.classList.add("lia-intake-drop-zone__approve--ready")}$.hidden=k.queued.length===0&&k.lastResponse==null&&!k.analyzing}function u(){k.queued=[],k.lastResponse=null,k.analyzing=!1,f.textContent="",kt(null),h(),p()}function l(){if(k.queued.length===0&&k.lastResponse==null){kt(null);return}kt({queuedFilenames:k.queued.map(v=>({filename:v.filename,mime:v.mime,bytes:v.bytes,relativePath:v.relativePath})),lastResponse:k.lastResponse,savedAt:new Date().toISOString()})}function m(){var U,G,O;const v=Zs();if(!v||!((((U=v.queuedFilenames)==null?void 0:U.length)??0)>0||!!v.lastResponse))return;k.queued=(v.queuedFilenames??[]).map(B=>({filename:B.filename,mime:B.mime,bytes:B.bytes,relativePath:B.relativePath,content_base64:""})),k.lastResponse=v.lastResponse??null,k.analyzing=!1,h(),p();const x=((O=(G=v.lastResponse)==null?void 0:G.summary)==null?void 0:O.placed)??0,I=v.savedAt?new Date(v.savedAt).toLocaleString("es-CO",{hour:"2-digit",minute:"2-digit",day:"2-digit",month:"short"}):"";x>0?f.textContent=`Sesión previa restaurada (${I}) — ${x} archivo(s) ya estaban clasificados.`:f.textContent=`Sesión previa restaurada (${I}).`}async function w(v){const N=v.filter(x=>sa(x.filename,x.relativePath));if(N.length===0){f.textContent="Ningún archivo elegible en el drop.";return}k.queued=N,k.lastResponse=null,k.analyzing=!0,h(),p(),f.textContent=`Enviando ${N.length} archivo(s) al intake…`;try{const x=await t(N);k.lastResponse=x,k.analyzing=!1,h(),p(),f.textContent=`Intake ok — placed ${x.summary.placed} / deduped ${x.summary.deduped} / rejected ${x.summary.rejected}.`,l()}catch(x){k.lastResponse=null,k.analyzing=!1,p();const I=x instanceof Error?x.message:"intake falló";f.textContent=`Intake falló: ${I}`}}return r.addEventListener("dragenter",v=>{v.preventDefault(),r.classList.add("lia-intake-drop-zone__zone--active")}),r.addEventListener("dragover",v=>{v.preventDefault(),r.classList.add("lia-intake-drop-zone__zone--active")}),r.addEventListener("dragleave",v=>{v.preventDefault(),r.classList.remove("lia-intake-drop-zone__zone--active")}),r.addEventListener("drop",v=>{v.preventDefault(),r.classList.remove("lia-intake-drop-zone__zone--active");const N=v.dataTransfer;N&&(async()=>{const x=await oa(N);await w(x)})()}),C.addEventListener("click",()=>{var N;if(C.disabled)return;const v=(N=k.lastResponse)==null?void 0:N.batch_id;v&&n&&n(v)}),$.addEventListener("click",()=>{var U;if(k.queued.length===0&&k.lastResponse==null)return;let v,N;if(k.analyzing)v="¿Borrar mientras procesamos?",N="Estamos procesando tus archivos. ¿Estás seguro que quieres borrar todo? El servidor seguirá procesando los archivos que ya recibió; esto solo limpia la vista local.";else if(k.lastResponse!=null){const G=((U=k.lastResponse.summary)==null?void 0:U.placed)??0;v="¿Borrar la vista del batch?",N=`Ya procesamos ${G} archivo(s) y están en knowledge_base/. ¿Borrar esta lista de la vista? Los archivos NO se eliminan del corpus — solo se limpia la vista.`}else v="¿Borrar archivos en cola?",N=`¿Borrar los ${k.queued.length} archivo(s) en cola antes de enviarlos?`;(a??(async()=>Promise.resolve(window.confirm(`${v}

${N}`))))({title:v,message:N,confirmLabel:"Borrar todo",cancelLabel:"Cancelar"}).then(G=>{G&&u()})}),h(),p(),m(),s}function wn(e){const{status:t,ariaLabel:n,className:a=""}=e,s=document.createElement("span"),o=["lia-progress-dot",`lia-progress-dot--${t}`,t==="running"?"lia-progress-dot--pulse":"",a].filter(Boolean);return s.className=o.join(" "),s.setAttribute("data-lia-component","progress-dot"),s.setAttribute("role","status"),s.setAttribute("data-status",t),n&&s.setAttribute("aria-label",n),s}const la=["docs","chunks","edges","embeddings_generated"];function ca(e){if(!e)return"";const t=[];for(const n of la)if(e[n]!=null&&t.push(`${n}: ${e[n]}`),t.length>=3)break;return t.join(", ")}function Xt(e){if(e==null)return null;if(typeof e=="number")return Number.isFinite(e)?e:null;const t=Date.parse(e);return Number.isFinite(t)?t:null}function da(e,t){const n=Xt(e),a=Xt(t);if(n==null||a==null||a<n)return"";const s=Math.round((a-n)/1e3);if(s<60)return`${s}s`;const o=Math.floor(s/60),i=s%60;return i?`${o}m ${i}s`:`${o}m`}function Yt(e){const{name:t,label:n,status:a,counts:s,startedAt:o,finishedAt:i,errorMessage:c,className:r=""}=e,d=document.createElement("div");d.className=["lia-stage-progress-item",`lia-stage-progress-item--${a}`,r].filter(Boolean).join(" "),d.setAttribute("data-lia-component","stage-progress-item"),d.setAttribute("data-stage-name",t),d.appendChild(wn({status:a,ariaLabel:n}));const g=document.createElement("span");g.className="lia-stage-progress-item__label",g.textContent=n,d.appendChild(g);const f=ca(s);if(f){const $=document.createElement("span");$.className="lia-stage-progress-item__counts",$.textContent=f,d.appendChild($)}const _=da(o,i);if(_){const $=document.createElement("span");$.className="lia-stage-progress-item__duration",$.textContent=_,d.appendChild($)}if(a==="failed"&&c){const $=document.createElement("p");$.className="lia-stage-progress-item__error",$.textContent=c,$.setAttribute("role","alert"),d.appendChild($)}return d}const Zt=[{name:"coerce",label:"Coerce"},{name:"audit",label:"Audit"},{name:"chunk",label:"Chunk"},{name:"sink",label:"Sink"},{name:"falkor",label:"FalkorDB"},{name:"embeddings",label:"Embeddings"}];function ua(e){return e==="running"||e==="done"||e==="failed"||e==="pending"?e:"pending"}function Qt(e,t,n){return{name:e,label:t,status:ua(n==null?void 0:n.status),counts:(n==null?void 0:n.counts)??null,startedAt:(n==null?void 0:n.started_at)??null,finishedAt:(n==null?void 0:n.finished_at)??null,errorMessage:(n==null?void 0:n.error)??null}}function pa(){const e=document.createElement("section");e.className="lia-run-progress-timeline",e.setAttribute("data-lia-component","run-progress-timeline");const t=document.createElement("header");t.className="lia-run-progress-timeline__header";const n=document.createElement("h3");n.className="lia-run-progress-timeline__title",n.textContent="Progreso de la corrida",t.appendChild(n),e.appendChild(t);const a=document.createElement("div");a.className="lia-run-progress-timeline__list";const s=new Map;Zt.forEach(({name:i,label:c})=>{const r=document.createElement("div");r.className="lia-run-progress-timeline__item",r.setAttribute("data-stage",i),r.appendChild(Yt(Qt(i,c,void 0))),a.appendChild(r),s.set(i,r)}),e.appendChild(a);function o(i){const c=(i==null?void 0:i.stages)||{};Zt.forEach(({name:r,label:d})=>{const g=s.get(r);if(!g)return;const f=c[r]||void 0;g.replaceChildren(Yt(Qt(r,d,f)))})}return{element:e,update:o}}function ma(e={}){const{initialLines:t=[],autoScroll:n=!0,onCopy:a=null,summaryLabel:s="Log de ejecución",className:o=""}=e,i=document.createElement("div");i.className=["lia-log-tail-viewer",o].filter(Boolean).join(" "),i.setAttribute("data-lia-component","log-tail-viewer");const c=document.createElement("div");c.className="lia-log-tail-viewer__toolbar";const r=document.createElement("button");r.type="button",r.className="lia-log-tail-viewer__copy",r.textContent="Copiar",r.setAttribute("aria-label","Copiar log"),c.appendChild(r);const d=document.createElement("details");d.className="lia-log-tail-viewer__details",d.open=!0;const g=document.createElement("summary");g.className="lia-log-tail-viewer__summary",g.textContent=s,d.appendChild(g);const f=document.createElement("pre");f.className="lia-log-tail-viewer__body",f.textContent=t.join(`
`),d.appendChild(f),i.appendChild(c),i.appendChild(d);const _={lines:[...t]},$=()=>{n&&(f.scrollTop=f.scrollHeight)},C=()=>{f.textContent=_.lines.join(`
`),$()},b=h=>{!h||h.length===0||(_.lines.push(...h),C())},k=()=>{_.lines=[],f.textContent=""};return r.addEventListener("click",()=>{var u;const h=_.lines.join(`
`),p=(u=globalThis.navigator)==null?void 0:u.clipboard;p&&typeof p.writeText=="function"&&p.writeText(h),a&&a()}),n&&$(),{element:i,appendLines:b,clear:k}}function ga(e={}){const{initialLines:t=[],onCopy:n=null,summaryLabel:a="Log de ejecución"}=e,s=document.createElement("section");s.className="lia-run-log-console",s.setAttribute("data-lia-component","run-log-console");const o=document.createElement("header");o.className="lia-run-log-console__header";const i=document.createElement("h3");i.className="lia-run-log-console__title",i.textContent="Log en vivo",o.appendChild(i);const c=document.createElement("p");c.className="lia-run-log-console__subtitle",c.textContent="Streaming del archivo artifacts/jobs/<job>.log — se actualiza cada 1.5s.",o.appendChild(c),s.appendChild(o);const r=ma({initialLines:t,autoScroll:!0,onCopy:n,summaryLabel:a,className:"lia-run-log-console__viewer"});return s.appendChild(r.element),{element:s,appendLines:r.appendLines,clear:r.clear}}function fa(e,t){const n=document.createElement("div");n.className="lia-adelta-modal__backdrop",n.setAttribute("role","dialog"),n.setAttribute("aria-modal","true"),n.setAttribute("aria-label","Confirmar aplicación del delta");const a=document.createElement("div");a.className="lia-adelta-modal";const s=document.createElement("h3");s.className="lia-adelta-modal__title",s.textContent="Confirmar aplicación";const o=document.createElement("p");o.className="lia-adelta-modal__body";const i=e.counts??{added:0,modified:0,removed:0};o.textContent=`Aplicar delta ${e.deltaId??"(pendiente)"} con +${i.added} / ~${i.modified} / -${i.removed} cambios. Esto afecta producción.`;const c=document.createElement("div");c.className="lia-adelta-modal__actions";const r=Ze({label:"Cancelar",tone:"ghost",onClick:()=>n.remove()}),d=Ze({label:"Aplicar delta",tone:"primary",onClick:()=>{n.remove(),t()}});return c.append(r,d),a.append(s,o,c),n.appendChild(a),n}function ba(e,t){const n=document.createElement("div");n.className="lia-adelta-actions",n.setAttribute("data-lia-component","additive-delta-actions");const a=Ze({label:"Previsualizar",tone:"secondary",onClick:()=>t.onPreview()}),s=Ze({label:"Análisis profundo",tone:"ghost",className:"lia-adelta-action-row__deep",attrs:{title:"Re-clasifica los ~1.3k documentos con el LLM completo. Úsalo cuando cambie el prompt del clasificador o la taxonomía. Tarda 20-25 min y cuesta ~US$ 6-16 en Gemini."},onClick:()=>t.onDeepPreview()}),o=Ze({label:"Aplicar",tone:"primary",disabled:!0}),i=Ze({label:"Cancelar",tone:"destructive",onClick:()=>t.onCancel()}),c=Ze({label:"Nuevo delta",tone:"ghost",onClick:()=>t.onReset()});o.addEventListener("click",()=>{const g=r;g.state==="previewed"&&document.body.appendChild(fa(g,()=>{o.disabled=!0,o.classList.add("is-pending"),t.onApply()}))}),n.append(a,s,o,i,c);let r=e;function d(g){r=g;const{state:f}=g;a.disabled=f==="running"||f==="pending",s.disabled=f==="running"||f==="pending",s.hidden=f==="running"||f==="terminal",o.disabled=f!=="previewed",o.classList.toggle("is-pending",f==="pending"),i.hidden=f!=="running"&&f!=="pending",c.hidden=f!=="terminal"}return d(e),{element:n,update:d}}const $t=3;function ha(e){const t=document.createElement("article");t.className=`lia-adelta-bucket lia-adelta-bucket--${e.tone}`,t.setAttribute("data-lia-component","additive-delta-bucket"),t.setAttribute("data-bucket",e.key);const n=document.createElement("header");n.className="lia-adelta-bucket__header";const a=document.createElement("h4");a.className="lia-adelta-bucket__title",a.textContent=e.title;const s=document.createElement("span");s.className="lia-adelta-bucket__count",s.textContent=String(e.count),n.append(a,s);const o=document.createElement("p");o.className="lia-adelta-bucket__body",o.textContent=e.description;const i=document.createElement("div");i.className="lia-adelta-bucket__chips";const c=e.samples.slice(0,$t);for(const r of c)i.appendChild(nt({label:r.label,tone:e.tone}));return e.samples.length>$t&&i.appendChild(nt({label:`+${e.samples.length-$t} más`,tone:"neutral"})),t.append(n,o,i),t}function va(e){var o,i,c;const t=document.createElement("section");if(t.className="lia-adelta-banner",t.setAttribute("data-lia-component","additive-delta-banner"),t.setAttribute("aria-label","Resumen del delta aditivo"),e.isEmpty){const r=document.createElement("div");r.className="lia-adelta-banner__empty";const d=document.createElement("h3");d.className="lia-adelta-banner__empty-title",d.textContent="Sin cambios detectados";const g=document.createElement("p");g.className="lia-adelta-banner__empty-body",g.textContent="La base ya coincide con el corpus en disco. No hay nada que aplicar.",r.append(d,g),t.appendChild(r)}else{const r=[{key:"added",title:"Agregados",tone:"success",count:e.counts.added,samples:((o=e.samples)==null?void 0:o.added)??[],description:"Documentos nuevos que entrarán al corpus."},{key:"modified",title:"Modificados",tone:"warning",count:e.counts.modified,samples:((i=e.samples)==null?void 0:i.modified)??[],description:"Documentos con cambios de contenido o clasificación."},{key:"removed",title:"Retirados",tone:"error",count:e.counts.removed,samples:((c=e.samples)==null?void 0:c.removed)??[],description:"Documentos que ya no existen en disco."},{key:"unchanged",title:"Sin cambios",tone:"neutral",count:e.counts.unchanged,samples:[],description:"Documentos que no requieren re-procesamiento."}],d=document.createElement("div");d.className="lia-adelta-banner__grid";for(const g of r)d.appendChild(ha(g));t.appendChild(d)}const n=document.createElement("footer");n.className="lia-adelta-banner__footer";const a=document.createElement("code");a.className="lia-adelta-banner__delta-id",a.textContent=`delta_id=${e.deltaId}`;const s=document.createElement("code");return s.className="lia-adelta-banner__baseline",s.textContent=`baseline=${e.baselineGenerationId}`,n.append(a,s),t.appendChild(n),t}function _a(e){const t=document.createElement("section");t.className="lia-adelta-feeler",t.setAttribute("data-lia-component","additive-delta-activity-feeler"),t.setAttribute("aria-live","polite");const n=document.createElement("header");n.className="lia-adelta-feeler__header";const a=document.createElement("span");a.className="lia-adelta-feeler__spinner",a.appendChild(_n({size:"md",ariaLabel:"Procesando"}));const s=document.createElement("div");s.className="lia-adelta-feeler__title-wrap";const o=document.createElement("h3");o.className="lia-adelta-feeler__title",o.textContent=e.title;const i=document.createElement("code");i.className="lia-adelta-feeler__run-id",i.hidden=!0;const c=document.createElement("span");c.className="lia-adelta-feeler__elapsed",c.textContent="00:00",s.append(o,i,c),n.append(a,s),t.appendChild(n);const r=document.createElement("p");r.className="lia-adelta-feeler__body",r.textContent=e.body,t.appendChild(r);const d=document.createElement("p");d.className="lia-adelta-feeler__live",d.hidden=!0,t.appendChild(d);const g=document.createElement("p");g.className="lia-adelta-feeler__hint",g.textContent="Puedes cambiar de pestaña — el trabajo sigue corriendo en el servidor.",t.appendChild(g);const f=Date.now();function _(){const b=Math.max(0,Math.floor((Date.now()-f)/1e3)),k=String(Math.floor(b/60)).padStart(2,"0"),h=String(b%60).padStart(2,"0");c.textContent=`${k}:${h}`}_();const $=setInterval(_,1e3);function C(b){const k=Math.max(0,Math.floor(b.classified??0)),h=b.classifierInputCount??null,p=b.prematchedCount??null;if(k<=0&&!b.lastFilename&&h==null){d.hidden=!0,d.textContent="";return}d.hidden=!1;const u=(b.lastFilename??"").split("/").pop()??"",l=h!=null?String(h):"~1.300",m=p!=null&&p>0?` — ${p} saltados por shortcut`:"";u?d.textContent=`Clasificados ${k} de ${l}${m} — último: ${u}`:d.textContent=`Clasificados ${k} de ${l}${m}`}return{element:t,setLiveProgress:C,destroy:()=>clearInterval($)}}const tt=["queued","parsing","supabase","falkor","finalize"],en={queued:"En cola",parsing:"Clasificando",supabase:"Supabase",falkor:"FalkorDB",finalize:"Finalizando",completed:"Completado",failed:"Falló",cancelled:"Cancelado"};function ya(e,t){if(e==="failed"||e==="cancelled"){const s=tt.indexOf(e==="failed"||e==="cancelled"?"finalize":e);return tt.indexOf(t)<=s?"failed":"pending"}if(e==="completed")return"done";const n=tt.indexOf(e),a=tt.indexOf(t);return a<n?"done":a===n?"running":"pending"}function wa(e){if(!e)return"sin heartbeat";const t=Date.parse(e);if(Number.isNaN(t))return"sin heartbeat";const n=Math.max(0,Math.floor((Date.now()-t)/1e3));if(n<5)return"hace un instante";if(n<60)return`hace ${n}s`;const a=Math.floor(n/60);return a<60?`hace ${a} min`:`hace ${Math.floor(a/60)} h`}function ka(e){switch(e){case"connecting":return"Conectando…";case"connected":return"En vivo";case"reconnecting":return"Reconectando…";case"polling":return"Sondeando (fallback)";case"closed":return"Desconectado"}}function $a(e){const t=document.createElement("section");t.className="lia-adelta-progress",t.setAttribute("data-lia-component","additive-delta-progress"),t.setAttribute("aria-live","polite");const n=document.createElement("header");n.className="lia-adelta-progress__header";const a=document.createElement("div");a.className="lia-adelta-progress__title-wrap";const s=document.createElement("h3");s.className="lia-adelta-progress__title",s.textContent="Aplicando delta";const o=document.createElement("span");o.className="lia-adelta-progress__elapsed",o.textContent="iniciado hace 00:00",a.append(s,o);const i=document.createElement("code");i.className="lia-adelta-progress__job";const c=document.createElement("span");c.className="lia-adelta-progress__sse",n.append(a,i,c);const r=document.createElement("ol");r.className="lia-adelta-progress__stages";const d={queued:document.createElement("li"),parsing:document.createElement("li"),supabase:document.createElement("li"),falkor:document.createElement("li"),finalize:document.createElement("li"),completed:document.createElement("li"),failed:document.createElement("li"),cancelled:document.createElement("li")},g={};for(const l of tt){const m=d[l];m.className="lia-adelta-progress__stage";const w=wn({status:"pending",ariaLabel:en[l]});g[l]=w;const v=document.createElement("span");v.className="lia-adelta-progress__stage-label",v.textContent=en[l],m.append(w,v),r.appendChild(m)}const f=document.createElement("div");f.className="lia-adelta-progress__bar",f.setAttribute("role","progressbar"),f.setAttribute("aria-valuemin","0"),f.setAttribute("aria-valuemax","100");const _=document.createElement("div");_.className="lia-adelta-progress__bar-fill",f.appendChild(_);const $=document.createElement("footer");$.className="lia-adelta-progress__footer";const C=document.createElement("span");C.className="lia-adelta-progress__heartbeat";const b=document.createElement("span");b.className="lia-adelta-progress__cancel-note",$.append(C,b),t.append(n,r,f,$);function k(l){i.textContent=l.jobId?`job_id=${l.jobId}`:"",c.textContent=ka(l.sseStatus),c.dataset.status=l.sseStatus;for(const w of tt){const v=g[w];if(!v)continue;const N=ya(l.stage,w);v.className=`lia-progress-dot lia-progress-dot--${N}`+(N==="running"?" lia-progress-dot--pulse":""),v.setAttribute("data-status",N)}const m=Math.max(0,Math.min(100,Math.round(l.progressPct)));_.style.width=`${m}%`,f.setAttribute("aria-valuenow",String(m)),C.textContent=`Último latido del servidor: ${wa(l.lastHeartbeatAt)}`,b.textContent=l.cancelRequested?"Cancelación solicitada — finalizará en el próximo punto seguro.":""}const h=Date.now();function p(){const l=Math.max(0,Math.floor((Date.now()-h)/1e3)),m=String(Math.floor(l/60)).padStart(2,"0"),w=String(l%60).padStart(2,"0");o.textContent=`iniciado hace ${m}:${w}`}p();const u=setInterval(p,1e3);return k(e),{element:t,update:k,destroy:()=>clearInterval(u)}}function Ca(e){var n,a;if(e.stage==="cancelled")return{variant:"navy",title:"Delta cancelado",icon:"✕"};if(e.stage==="failed")return{variant:"danger",title:"Delta falló",icon:"!"};const t=(((n=e.report)==null?void 0:n.new_chunks_count)??((a=e.report)==null?void 0:a.chunks_written)??0)>0;return{variant:t?"warning":"success",title:t?"Delta completado — pendiente embeddings":"Delta completado",icon:"✓"}}function Sa(e){const t=e.report??{},n=Number(t.documents_added??0),a=Number(t.documents_modified??0),s=Number(t.documents_retired??0);return`Se procesaron ${n} nuevos, ${a} modificados y ${s} retirados. Ediciones de chunks: +${t.chunks_written??0} / -${t.chunks_deleted??0}. Aristas: +${t.edges_written??0} / -${t.edges_deleted??0}.`}function Ea(e){return navigator.clipboard?navigator.clipboard.writeText(e).then(()=>!0).catch(()=>!1):Promise.resolve(!1)}function Na(e){var c,r,d,g;const t=Ca(e),n=document.createElement("section");n.className=`lia-adelta-terminal lia-adelta-terminal--${t.variant}`,n.setAttribute("data-lia-component","additive-delta-terminal"),n.setAttribute("data-stage",e.stage),n.setAttribute("role","status"),n.setAttribute("aria-live","polite");const a=document.createElement("header");a.className="lia-adelta-terminal__header";const s=document.createElement("span");s.className="lia-adelta-terminal__icon",s.textContent=t.icon,s.setAttribute("aria-hidden","true");const o=document.createElement("h3");o.className="lia-adelta-terminal__title",o.textContent=t.title;const i=document.createElement("code");if(i.className="lia-adelta-terminal__delta-id",i.textContent=e.deltaId,a.append(s,o,i),n.appendChild(a),e.stage==="completed"){const f=document.createElement("p");if(f.className="lia-adelta-terminal__summary",f.textContent=Sa(e),n.appendChild(f),(((c=e.report)==null?void 0:c.new_chunks_count)??((r=e.report)==null?void 0:r.chunks_written)??0)>0){const $=document.createElement("div");$.className="lia-adelta-terminal__callout";const C=document.createElement("p");C.className="lia-adelta-terminal__callout-body";const b=((d=e.report)==null?void 0:d.new_chunks_count)??((g=e.report)==null?void 0:g.chunks_written)??0;C.textContent=`${b} chunks nuevos pendientes de embedding — la calidad de retrieval está degradada hasta que corras la actualización.`;const k=document.createElement("code");k.className="lia-adelta-terminal__cmd",k.textContent="make phase2-embed-backfill";const h=Ze({label:"Copiar comando",tone:"secondary",onClick:()=>{Ea("make phase2-embed-backfill").then(p=>{h.classList.toggle("is-copied",p),h.querySelector(".lia-btn__label").textContent=p?"Copiado ✓":"Copiar comando"})}});$.append(C,k,h),n.appendChild($)}}else if(e.stage==="failed"){const f=document.createElement("p");f.className="lia-adelta-terminal__summary",f.textContent="La aplicación del delta se detuvo. La parity con Falkor puede estar desfasada; revisa los eventos antes de reintentar.";const _=document.createElement("pre");_.className="lia-adelta-terminal__error",_.textContent=`${e.errorClass??"unknown_error"}: ${e.errorMessage??"(sin mensaje)"}`,n.append(f,_)}else{const f=document.createElement("p");f.className="lia-adelta-terminal__summary",f.textContent="El operador canceló el delta en un punto seguro. Los cambios parciales no se revierten automáticamente; inspecciona el reporte antes de continuar.",n.appendChild(f)}return n}const Ct="additive-delta.jobId";function Pa(e){const t=e??(typeof localStorage<"u"?localStorage:null);return t?{get:()=>{try{const n=t.getItem(Ct);return n&&n.trim()?n.trim():null}catch{return null}},set:n=>{try{n&&n.trim()&&t.setItem(Ct,n.trim())}catch{}},clear:()=>{try{t.removeItem(Ct)}catch{}}}:{get:()=>null,set:()=>{},clear:()=>{}}}function Aa(e){const{serverLiveJobId:t,localJobId:n,store:a}=e;return t?(n!==t&&a.set(t),t):n||null}const Ia=new Set(["completed","failed","cancelled"]);function xa(e){try{const t=JSON.parse(e);if(!t||typeof t!="object")return null;const n=t,a=String(n.job_id??"");return a?{jobId:a,stage:String(n.stage??"queued"),progressPct:Number(n.progress_pct??0)||0,lastHeartbeatAt:n.last_heartbeat_at??null,cancelRequested:!!(n.cancel_requested??!1),reportJson:n.report_json??null,errorClass:n.error_class??null,errorMessage:n.error_message??null}:null}catch{return null}}function La(e,t,n={}){const a=n.maxReconnects??0,s=n.pollingIntervalMs??2e3,o=n.eventSourceFactory??(m=>new EventSource(m)),i=n.fetchImpl??fetch.bind(globalThis),c=`/api/ingest/additive/events?job_id=${encodeURIComponent(e)}`,r=`/api/ingest/additive/status?job_id=${encodeURIComponent(e)}`;let d=0,g=!1,f=null,_=null,$=null;function C(m){var w;(w=t.onStatusChange)==null||w.call(t,m)}function b(m){var w;Ia.has(m.stage)&&((w=t.onTerminal)==null||w.call(t,m),l())}function k(m){const w=xa(m);w&&(t.onSnapshot(w),b(w))}function h(){if(C("polling"),_)return;const m=async()=>{if(!g)try{const w=typeof window<"u"?window.localStorage.getItem("lia_access_token"):null,v={};w&&w.trim()&&(v.Authorization=`Bearer ${w.trim()}`);const N=await i(r,{headers:v});if(!N.ok)return;const x=await N.json();if(!x||!x.job)return;k(JSON.stringify(x.job))}catch{}};m(),_=setInterval(m,s)}function p(){if(!g){C(d===0?"connecting":"reconnecting");try{f=o(c)}catch{u();return}f.addEventListener("open",()=>{d=0,C("connected")}),f.addEventListener("snapshot",m=>{k(m.data)}),f.addEventListener("message",m=>{k(m.data)}),f.addEventListener("error",()=>{g||(f==null||f.close(),f=null,u())})}}function u(){if(g)return;if(d>=a){h();return}d+=1;const m=Math.min(3e4,500*2**(d-1));C("reconnecting"),$=setTimeout(()=>p(),m)}function l(){g||(g=!0,f&&(f.close(),f=null),_&&(clearInterval(_),_=null),$&&(clearTimeout($),$=null),C("closed"))}return p(),{close:l}}const Ta=["completed","failed","cancelled"];function tn(e){return Ta.includes(e)}function Ra(e){var n,a;const t=((n=e.reportJson)==null?void 0:n.sink_result)??null;return{stage:e.stage,deltaId:((a=e.reportJson)==null?void 0:a.delta_id)??e.jobId,report:t,errorClass:e.errorClass,errorMessage:e.errorMessage}}function qa(e){const t=e.target??"production";e.fetchImpl??fetch.bind(globalThis);const n=Pa(e.storage),a=e.rootElement;a.classList.add("lia-adelta-panel"),a.setAttribute("data-lia-component","additive-delta-controller");const s=document.createElement("div");s.className="lia-adelta-panel__banner";const o=document.createElement("div");o.className="lia-adelta-panel__progress";const i=document.createElement("div");i.className="lia-adelta-panel__terminal";const c=ba({state:"idle"},{onPreview:()=>void w({deepScan:!1}),onDeepPreview:()=>void N(),onApply:()=>void v(),onCancel:()=>void x(),onReset:()=>l()});a.append(c.element,s,o,i);let r=null,d=null,g=null,f=null,_=null,$=null,C=null,b=!1,k=null;function h(){k&&(clearInterval(k),k=null),g&&(g.destroy(),g=null)}function p(M,q,Z=!1){if(h(),g=_a({title:M,body:q}),s.replaceChildren(g.element),Z){const y=async()=>{if(g)try{const R=await Ne("/api/ingest/additive/preview-progress");if(!(R!=null&&R.available))return;g.setLiveProgress({classified:R.classified_since_last_run_boundary??0,lastFilename:R.last_filename??null})}catch{}};y(),k=setInterval(y,3e3)}}function u(M,q){c.update({state:M,deltaId:(q==null?void 0:q.deltaId)??(r==null?void 0:r.delta_id),counts:(q==null?void 0:q.counts)??(r?{added:r.summary.added,modified:r.summary.modified,removed:r.summary.removed}:void 0)})}function l(){h(),$=null,C=null,b=!1,_=null,s.replaceChildren(),o.replaceChildren(),i.replaceChildren(),r=null,d&&(d.destroy(),d=null),f&&(f.close(),f=null),n.clear(),u("idle")}function m(M){var q;(q=e.onError)==null||q.call(e,M)}async function w(M){var q,Z,y;$="preview",u("pending"),M.deepScan?p("Análisis profundo del corpus…","Lia está re-clasificando TODOS los ~1.3k documentos con el LLM (PASO 4) para detectar drift del clasificador sobre archivos byte-idénticos. Tarda 20–25 minutos y cuesta ~US$ 6-16 en Gemini. Avance en vivo abajo.",!0):p("Analizando delta…","Lia compara los archivos de knowledge_base/ contra la base ya publicada por content_hash. Solo re-clasifica los archivos genuinamente nuevos o editados — los demás reutilizan su fingerprint anterior. Rápido para deltas pequeños.",!0);try{const{response:R,data:S}=await ze("/api/ingest/additive/preview",{target:t,force_full_classify:M.deepScan});if($!=="preview")return;if(!R.ok||!S){h(),$=null,m(`Preview falló (HTTP ${R.status}).`),u("idle");return}h(),$=null,r=S;const T={deltaId:S.delta_id,baselineGenerationId:S.baseline_generation_id,counts:{added:S.summary.added,modified:S.summary.modified,removed:S.summary.removed,unchanged:S.summary.unchanged},samples:{added:(((q=S.sample_chips)==null?void 0:q.added)??[]).map(F=>({label:F})),modified:(((Z=S.sample_chips)==null?void 0:Z.modified)??[]).map(F=>({label:F})),removed:(((y=S.sample_chips)==null?void 0:y.removed)??[]).map(F=>({label:F}))},isEmpty:!!S.summary.is_empty};s.replaceChildren(va(T)),o.replaceChildren(),i.replaceChildren(),u(S.summary.is_empty?"previewed-empty":"previewed")}catch(R){if($!=="preview")return;h(),$=null,m(String(R)),u("idle")}}async function v(){if(!r||r.summary.is_empty){m("No hay delta listo para aplicar.");return}$="apply",u("pending"),p("Encolando delta…","Reservando un slot de procesamiento en el servidor y disparando el worker. Esto es rápido (segundos); el procesamiento real arranca inmediatamente después.");try{const{response:M,data:q}=await ze("/api/ingest/additive/apply",{target:t,delta_id:r.delta_id});if($!=="apply")return;if(M.status===409){const y=q;m(`Ya hay un delta en curso (${y.blocking_job_id}). Reattacheando…`),$=null,U(y.blocking_job_id);return}if(!M.ok||!q){$=null,m(`Apply falló (HTTP ${M.status}).`),u("previewed");return}const Z=q;n.set(Z.job_id),$=null,U(Z.job_id)}catch(M){if($!=="apply")return;$=null,m(String(M)),u("previewed")}}async function N(){await(e.confirmDestructive??(Z=>Promise.resolve(window.confirm(`${Z.title}

${Z.message}`))))({title:"Procedimiento largo — ¿estás seguro?",message:"El análisis profundo re-clasifica los ~1.300 documentos del corpus con el LLM completo (PASO 4). Esto es un procedimiento LARGO: tarda 20–25 minutos de reloj real y cuesta aprox. US$ 6–16 en Gemini. Úsalo solo cuando cambie el prompt del clasificador o la taxonomía de subtemas; para uploads rutinarios, la Previsualización normal (ruta rápida) ya detecta archivos nuevos y editados en segundos. ¿Quieres continuar con el análisis profundo?",confirmLabel:"Sí, correr análisis profundo",cancelLabel:"Cancelar"})&&w({deepScan:!0})}async function x(){var q;if(b)return;b=!0;const M=I();if($==="preview"){h(),$=null,b=!1,u("idle"),m("Cancelación en cliente. El clasificador puede seguir corriendo en el servidor — su resultado se descarta.");return}if($==="apply"&&!M){h(),$=null,b=!1,u(r?"previewed":"idle"),m("Solicitud de apply cancelada antes de encolarse.");return}if(M){try{if(await ze(`/api/ingest/additive/cancel?job_id=${encodeURIComponent(M)}`,{}),d){const Z=d.element;Z.dataset.cancelRequested="true";const y=Z.dataset.currentStage??"queued",R=parseInt(((q=Z.querySelector(".lia-adelta-progress__bar-fill"))==null?void 0:q.style.width)||"0",10)||0;d.update({jobId:M,stage:y,progressPct:R,lastHeartbeatAt:Z.dataset.heartbeat??null,sseStatus:"polling",cancelRequested:!0})}}catch(Z){m(`La solicitud de cancelación no pudo enviarse (${String(Z)}). Intenta de nuevo o usa Nuevo delta para reiniciar la vista sin tocar el worker.`)}finally{b=!1}return}b=!1,m("No hay operación en curso para cancelar.")}function I(){return C??n.get()}function U(M){h(),$=null,C=M,s.replaceChildren(),i.replaceChildren(),o.replaceChildren(),_={jobId:M,stage:"queued",progressPct:0,lastHeartbeatAt:null,sseStatus:"connecting",cancelRequested:!1},d=$a(_),o.replaceChildren(d.element),u("running",{deltaId:M,counts:void 0}),f&&f.close(),f=La(M,{onSnapshot:q=>O(q),onStatusChange:q=>G(q),onTerminal:q=>B(q)},e.sseOptions??{})}function G(M){!d||!_||(_={..._,sseStatus:M},d.update(_))}function O(M){d&&(_={jobId:M.jobId,stage:M.stage,progressPct:M.progressPct,lastHeartbeatAt:M.lastHeartbeatAt??null,sseStatus:"connected",cancelRequested:M.cancelRequested},d.update(_))}function B(M){if(!tn(M.stage))return;o.replaceChildren(),d&&(d.destroy(),d=null),C=null,b=!1,$=null,_=null;const q=Ra(M);i.replaceChildren(Na(q)),n.clear(),u("terminal")}async function L(){u("idle");try{let M;try{M=await Ne(`/api/ingest/additive/live?target=${encodeURIComponent(t)}`)}catch{M={ok:!1,target:t,job_id:null,job:null}}const q=n.get(),Z=Aa({serverLiveJobId:M.job_id,localJobId:q,store:n});if(!Z)return;if(M.job_id===Z){U(Z);return}let y;try{y=await Ne(`/api/ingest/additive/status?job_id=${encodeURIComponent(Z)}`)}catch{n.clear();return}if(!y.job){n.clear();return}tn(y.job.stage)?B({jobId:y.job.job_id,stage:y.job.stage,progressPct:y.job.progress_pct,lastHeartbeatAt:y.job.last_heartbeat_at,cancelRequested:y.job.cancel_requested,reportJson:y.job.report_json,errorClass:y.job.error_class,errorMessage:y.job.error_message}):U(Z)}catch{}}L();function E(){f&&f.close(),a.replaceChildren()}return{destroy:E}}function Ma(e){const t=document.createElement("div");t.className=["lia-segmented",e.className||""].filter(Boolean).join(" "),t.setAttribute("data-lia-component","segmented-control"),t.setAttribute("role","tablist"),e.ariaLabel&&t.setAttribute("aria-label",e.ariaLabel);let n=e.value;const a=[];for(const o of e.options){const i=document.createElement("button");i.type="button",i.className="lia-segmented__option",i.setAttribute("role","tab"),i.setAttribute("data-value",o.value),i.setAttribute("aria-pressed",o.value===n?"true":"false");const c=document.createElement("span");if(c.className="lia-segmented__label",c.textContent=o.label,i.appendChild(c),o.hint){const r=document.createElement("span");r.className="lia-segmented__hint",r.textContent=o.hint,i.appendChild(r)}i.addEventListener("click",()=>{n!==o.value&&(s(o.value),e.onChange(o.value))}),a.push(i),t.appendChild(i)}function s(o){n=o;for(const i of a){const c=i.getAttribute("data-value")||"";i.setAttribute("aria-pressed",c===n?"true":"false")}}return{element:t,setValue:s,value:()=>n}}async function nn(e,t){const{response:n,data:a}=await ze(e,t);if(!n.ok){let s=n.statusText;if(a&&typeof a=="object"){const o=a,i=typeof o.error=="string"?o.error:"",c=typeof o.details=="string"?o.details:"";i&&c?s=`${i} — ${c}`:i?s=i:c&&(s=c)}throw new st(s,n.status,a)}if(!a)throw new st("Empty response",n.status,null);return a}function Da(e,t={}){const n=e.querySelector("[data-slot=corpus-overview]"),a=e.querySelector("[data-slot=run-trigger]"),s=e.querySelector("[data-slot=generations-list]"),o=e.querySelector("[data-slot=intake-zone]"),i=e.querySelector("[data-slot=progress-timeline]"),c=e.querySelector("[data-slot=log-console]");if(!n||!a||!s)return e.textContent="Sesiones: missing render slots.",{refresh:async()=>{},destroy:()=>{}};const r={activeJobId:null,lastRunStatus:null,pollHandle:null,logCursor:0,lastBatchId:null,autoEmbed:!0,autoPromote:!1,supabaseTarget:"wip",suinScope:""};let d=null,g=null;function f(){a.replaceChildren(Hs({activeJobId:r.activeJobId,lastRunStatus:r.lastRunStatus,disabled:r.activeJobId!==null,onTrigger:({suinScope:y,supabaseTarget:R,autoEmbed:S,autoPromote:T})=>{r.autoEmbed=S,r.autoPromote=T,r.supabaseTarget=R,r.suinScope=y,m({suinScope:y,supabaseTarget:R,autoEmbed:S,autoPromote:T,batchId:null})}}))}const _=t.i18n?y=>sn(t.i18n).confirm({title:y.title,message:y.message,tone:"caution",confirmLabel:y.confirmLabel,cancelLabel:y.cancelLabel}):void 0;function $(){o&&o.replaceChildren(ra({onIntake:y=>u(y),onApprove:()=>C(),confirmDestructive:_}))}function C(){var R;const y=((R=e.querySelector("[data-slot=flow-toggle]"))==null?void 0:R.closest("section"))??e.querySelector("[data-slot=flow-toggle]")??null;y&&(y.scrollIntoView({behavior:"smooth",block:"start"}),y.classList.add("is-highlighted"),window.setTimeout(()=>y.classList.remove("is-highlighted"),2400))}function b(){i&&(d=pa(),i.replaceChildren(d.element))}function k(){c&&(g=ga(),c.replaceChildren(g.element))}async function h(){n.replaceChildren(G("overview"));try{const y=await Ne("/api/ingest/state"),R={documents:y.corpus.documents,chunks:y.corpus.chunks,graphNodes:y.graph.nodes,graphEdges:y.graph.edges,graphOk:y.graph.ok,auditScanned:y.audit.scanned,auditIncluded:y.audit.include_corpus,auditExcluded:y.audit.exclude_internal,auditPendingRevisions:y.audit.pending_revisions,activeGenerationId:y.corpus.active_generation_id,activatedAt:y.corpus.activated_at};n.replaceChildren(Ms(R))}catch(y){n.replaceChildren(O("No se pudo cargar el estado del corpus.",y))}}async function p(){s.replaceChildren(G("generations"));try{const R=((await Ne("/api/ingest/generations?limit=20")).generations||[]).map(S=>{const T=S.knowledge_class_counts||{},F=Object.entries(T).sort((V,oe)=>oe[1]-V[1])[0];return{generationId:S.generation_id,status:S.is_active?"active":"superseded",generatedAt:S.generated_at,documents:Number(S.documents)||0,chunks:Number(S.chunks)||0,topClass:F==null?void 0:F[0],topClassCount:F==null?void 0:F[1]}});s.replaceChildren(Gt({rows:R}))}catch(y){s.replaceChildren(Gt({rows:[],errorMessage:`No se pudieron cargar las generaciones: ${B(y)}`}))}}async function u(y){const S={batch_id:null,files:await Promise.all(y.map(async F=>{const V=await l(F.file);return{filename:F.filename,content_base64:V,relative_path:F.relativePath||F.filename}})),options:{mirror_to_dropbox:!1,dropbox_root:null}},T=await nn("/api/ingest/intake",S);return r.lastBatchId=T.batch_id,T}async function l(y){const R=globalThis;if(typeof R.FileReader=="function"){const S=await new Promise((F,V)=>{const oe=new R.FileReader;oe.onerror=()=>V(oe.error||new Error("file read failed")),oe.onload=()=>F(String(oe.result||"")),oe.readAsDataURL(y)}),T=S.indexOf(",");return T>=0?S.slice(T+1):""}if(typeof y.arrayBuffer=="function"){const S=await y.arrayBuffer();return U(S)}return""}async function m(y){r.lastRunStatus="queued",r.logCursor=0,g&&g.clear(),f();try{const R=await nn("/api/ingest/run",{suin_scope:y.suinScope,supabase_target:y.supabaseTarget,auto_embed:y.autoEmbed,auto_promote:y.autoPromote,batch_id:y.batchId});r.activeJobId=R.job_id,r.lastRunStatus="running",f(),w()}catch(R){r.lastRunStatus="failed",r.activeJobId=null,f(),L(`No se pudo iniciar la ingesta: ${B(R)}`)}}function w(){v();const y=i!==null||c!==null;r.pollHandle=window.setInterval(()=>{if(!r.activeJobId){v();return}y?(N(r.activeJobId),x(r.activeJobId)):I(r.activeJobId)},y?1500:4e3)}function v(){r.pollHandle!==null&&(window.clearInterval(r.pollHandle),r.pollHandle=null)}async function N(y){try{const R=await Ne(`/api/ingest/job/${y}/progress`);d&&d.update(R);const S=R.status;(S==="done"||S==="failed")&&(r.lastRunStatus=S==="done"?"active":"failed",r.activeJobId=null,f(),v(),S==="done"&&await Promise.all([h(),p()]))}catch{}}async function x(y){try{const R=await Ne(`/api/ingest/job/${y}/log/tail?cursor=${r.logCursor}&limit=200`);R.lines&&R.lines.length>0&&g&&g.appendLines(R.lines),typeof R.next_cursor=="number"&&(r.logCursor=R.next_cursor)}catch{}}async function I(y){var R;try{const T=(await Ne(`/api/jobs/${y}`)).job;if(!T)return;if(T.status==="completed"){const F=(((R=T.result_payload)==null?void 0:R.exit_code)??1)===0;r.lastRunStatus=F?"active":"failed",r.activeJobId=null,f(),v(),F&&await Promise.all([h(),p()])}else T.status==="failed"&&(r.lastRunStatus="failed",r.activeJobId=null,f(),v())}catch{}}function U(y){const R=new Uint8Array(y),S=32768;let T="";for(let oe=0;oe<R.length;oe+=S){const le=R.subarray(oe,Math.min(R.length,oe+S));T+=String.fromCharCode.apply(null,Array.from(le))}const F=globalThis;if(typeof F.btoa=="function")return F.btoa(T);const V=globalThis.Buffer;return V?V.from(T,"binary").toString("base64"):""}function G(y){const R=document.createElement("div");return R.className=`lia-ingest-skeleton lia-ingest-skeleton--${y}`,R.setAttribute("aria-hidden","true"),R.textContent="Cargando…",R}function O(y,R){const S=document.createElement("div");S.className="lia-ingest-error",S.setAttribute("role","alert");const T=document.createElement("strong");T.textContent=y,S.appendChild(T);const F=document.createElement("p");return F.className="lia-ingest-error__detail",F.textContent=B(R),S.appendChild(F),S}function B(y){return y instanceof Error?y.message:typeof y=="string"?y:"Error desconocido"}function L(y){const R=document.createElement("div");R.className="lia-ingest-toast",R.textContent=y,e.prepend(R),window.setTimeout(()=>R.remove(),4e3)}f(),$(),b(),k(),Promise.all([h(),p()]);const E=e.querySelector("[data-slot=flow-toggle]"),M=(E==null?void 0:E.closest("[data-active-flow]"))??null;if(E&&M){const y=Ma({ariaLabel:"Flujo de ingesta",value:"delta",options:[{value:"delta",label:"Delta aditivo",hint:"Rápido · solo lo que cambió"},{value:"full",label:"Ingesta completa",hint:"Lento · reconstruye todo"}],onChange:R=>{M.setAttribute("data-active-flow",R)}});E.replaceChildren(y.element)}let q=null;const Z=e.querySelector("[data-slot=additive-delta]");if(Z){const y=document.createElement("article");y.className="lia-adelta-card",y.setAttribute("data-lia-component","additive-delta-card"),y.innerHTML=`
      <header class="lia-adelta-card__header">
        <h3 class="lia-adelta-card__title">Delta aditivo</h3>
        <p class="lia-adelta-card__body">
          Lee <code>knowledge_base/</code> en disco, lo compara contra la base
          ya publicada y procesa <strong>solo los archivos nuevos, modificados
          o borrados</strong>. No hay upload: primero pon los archivos en esa
          carpeta (paso 3 abajo), después aquí.
        </p>
        <p class="lia-adelta-card__steps">
          <strong>Previsualizar</strong> te muestra el diff sin escribir nada.
          <strong>Aplicar</strong> procesa el delta con una confirmación
          explícita. Rápido — minutos, no horas.
        </p>
      </header>
    `;const R=document.createElement("div");R.className="lia-adelta-card__mount",y.appendChild(R),Z.replaceChildren(y),q=qa({rootElement:R,target:"production",onError:S=>L(S),confirmDestructive:_})}return{async refresh(){await Promise.all([h(),p()])},destroy(){v(),q&&(q.destroy(),q=null)}}}function Oa(e,{i18n:t}){const n=e,a=n.querySelector("#lia-ingest-shell");let s=null;a&&(s=Da(a,{i18n:t}),window.setInterval(()=>{s==null||s.refresh()},3e4));const o=a!==null,i=n.querySelector("#ops-tab-monitor"),c=n.querySelector("#ops-tab-ingestion"),r=n.querySelector("#ops-tab-control"),d=n.querySelector("#ops-tab-embeddings"),g=n.querySelector("#ops-tab-reindex"),f=n.querySelector("#ops-panel-monitor"),_=n.querySelector("#ops-panel-ingestion"),$=n.querySelector("#ops-panel-control"),C=n.querySelector("#ops-panel-embeddings"),b=n.querySelector("#ops-panel-reindex"),k=n.querySelector("#runs-body"),h=n.querySelector("#timeline"),p=n.querySelector("#timeline-meta"),u=n.querySelector("#cascade-note"),l=n.querySelector("#user-cascade"),m=n.querySelector("#user-cascade-summary"),w=n.querySelector("#technical-cascade"),v=n.querySelector("#technical-cascade-summary"),N=n.querySelector("#refresh-runs"),x=!!(k&&h&&p&&u&&l&&m&&w&&v&&N),I=o?null:re(n,"#ingestion-flash"),U=hn();function G(Ve="",ut="success"){if(I){if(!Ve){I.hidden=!0,I.textContent="",I.removeAttribute("data-tone");return}I.hidden=!1,I.dataset.tone=ut,I.textContent=Ve}}const O=o?null:re(n,"#ingestion-corpus"),B=o?null:re(n,"#ingestion-batch-type"),L=o?null:re(n,"#ingestion-dropzone"),E=o?null:re(n,"#ingestion-file-input"),M=o?null:re(n,"#ingestion-folder-input"),q=o?null:re(n,"#ingestion-pending-files"),Z=o?null:re(n,"#ingestion-overview"),y=o?null:re(n,"#ingestion-refresh"),R=o?null:re(n,"#ingestion-create-session"),S=o?null:re(n,"#ingestion-select-files"),T=o?null:re(n,"#ingestion-select-folder"),F=o?null:re(n,"#ingestion-upload-files"),V=o?null:re(n,"#ingestion-upload-progress"),oe=o?null:re(n,"#ingestion-process-session"),le=o?null:re(n,"#ingestion-auto-process"),be=o?null:re(n,"#ingestion-validate-batch"),Ee=o?null:re(n,"#ingestion-retry-session"),Pe=o?null:re(n,"#ingestion-delete-session"),Ce=o?null:re(n,"#ingestion-session-meta"),K=o?null:re(n,"#ingestion-sessions-list"),ke=o?null:re(n,"#selected-session-meta"),pe=o?null:re(n,"#ingestion-last-error"),Ae=o?null:re(n,"#ingestion-last-error-message"),Me=o?null:re(n,"#ingestion-last-error-guidance"),De=o?null:re(n,"#ingestion-last-error-next"),he=o?null:re(n,"#ingestion-kanban"),Le=o?null:re(n,"#ingestion-log-accordion"),Te=o?null:re(n,"#ingestion-log-body"),de=o?null:re(n,"#ingestion-log-copy"),ve=o?null:re(n,"#ingestion-auto-status"),D=n.querySelector("#ingestion-add-corpus-btn"),W=n.querySelector("#add-corpus-dialog"),se=n.querySelector("#ingestion-bounce-log"),te=n.querySelector("#ingestion-bounce-body"),Q=n.querySelector("#ingestion-bounce-copy");async function fe(Ve){return Ve()}const ae=x?gn({i18n:t,stateController:U,dom:{monitorTabBtn:i,ingestionTabBtn:c,controlTabBtn:r,embeddingsTabBtn:d,reindexTabBtn:g,monitorPanel:f,ingestionPanel:_,controlPanel:$,embeddingsPanel:C,reindexPanel:b,runsBody:k,timelineNode:h,timelineMeta:p,cascadeNote:u,userCascadeNode:l,userCascadeSummary:m,technicalCascadeNode:w,technicalCascadeSummary:v,refreshRunsBtn:N},withThinkingWheel:fe,setFlash:G}):null,ce=o?null:Is({i18n:t,stateController:U,dom:{ingestionCorpusSelect:O,ingestionBatchTypeSelect:B,ingestionDropzone:L,ingestionFileInput:E,ingestionFolderInput:M,ingestionSelectFilesBtn:S,ingestionSelectFolderBtn:T,ingestionUploadProgress:V,ingestionPendingFiles:q,ingestionOverview:Z,ingestionRefreshBtn:y,ingestionCreateSessionBtn:R,ingestionUploadBtn:F,ingestionProcessBtn:oe,ingestionAutoProcessBtn:le,ingestionValidateBatchBtn:be,ingestionRetryBtn:Ee,ingestionDeleteSessionBtn:Pe,ingestionSessionMeta:Ce,ingestionSessionsList:K,selectedSessionMeta:ke,ingestionLastError:pe,ingestionLastErrorMessage:Ae,ingestionLastErrorGuidance:Me,ingestionLastErrorNext:De,ingestionKanban:he,ingestionLogAccordion:Le,ingestionLogBody:Te,ingestionLogCopyBtn:de,ingestionAutoStatus:ve,addCorpusBtn:D,addCorpusDialog:W,ingestionBounceLog:se,ingestionBounceBody:te,ingestionBounceCopy:Q},withThinkingWheel:fe,setFlash:G}),X=n.querySelector("#corpus-lifecycle"),ee=X?an({dom:{container:X},setFlash:G}):null,$e=n.querySelector("#embeddings-lifecycle"),Re=$e?dn({dom:{container:$e},setFlash:G}):null,Ie=n.querySelector("#reindex-lifecycle"),Je=Ie?fn({dom:{container:Ie},setFlash:G,navigateToEmbeddings:()=>{U.setActiveTab("embeddings"),ae==null||ae.renderTabs()}}):null;ae==null||ae.bindEvents(),ce==null||ce.bindEvents(),ee==null||ee.bindEvents(),Re==null||Re.bindEvents(),Je==null||Je.bindEvents(),ae==null||ae.renderTabs(),ce==null||ce.render(),bn({stateController:U,withThinkingWheel:fe,setFlash:G,refreshRuns:(ae==null?void 0:ae.refreshRuns)??(async()=>{}),refreshIngestion:(ce==null?void 0:ce.refreshIngestion)??(async()=>{}),refreshCorpusLifecycle:ee==null?void 0:ee.refresh,refreshEmbeddings:Re==null?void 0:Re.refresh,refreshReindex:Je==null?void 0:Je.refresh})}function Fa(e,{i18n:t}){const n=e,a=n.querySelector("#runs-body"),s=n.querySelector("#timeline"),o=n.querySelector("#timeline-meta"),i=n.querySelector("#cascade-note"),c=n.querySelector("#user-cascade"),r=n.querySelector("#user-cascade-summary"),d=n.querySelector("#technical-cascade"),g=n.querySelector("#technical-cascade-summary"),f=n.querySelector("#refresh-runs");if(!a||!s||!o||!i||!c||!r||!d||!g||!f)return;const _=hn(),$=async k=>k(),C=()=>{},b=gn({i18n:t,stateController:_,dom:{monitorTabBtn:null,ingestionTabBtn:null,controlTabBtn:null,embeddingsTabBtn:null,reindexTabBtn:null,monitorPanel:null,ingestionPanel:null,controlPanel:null,embeddingsPanel:null,reindexPanel:null,runsBody:a,timelineNode:s,timelineMeta:o,cascadeNote:i,userCascadeNode:c,userCascadeSummary:r,technicalCascadeNode:d,technicalCascadeSummary:g,refreshRunsBtn:f},withThinkingWheel:$,setFlash:C});b.bindEvents(),b.renderTabs(),bn({stateController:_,withThinkingWheel:$,setFlash:C,refreshRuns:b.refreshRuns,refreshIngestion:async()=>{}})}const eo=Object.freeze(Object.defineProperty({__proto__:null,mountBackstageApp:Fa,mountOpsApp:Oa},Symbol.toStringTag,{value:"Module"}));export{Oa as a,Dn as b,Za as c,Qa as d,eo as e,Fa as m,Ya as o,Rn as r,Xa as s};
