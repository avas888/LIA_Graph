/**
 * Sesiones page template — slots only.
 *
 * The render function returns a string of empty slot containers. The
 * `ingestController` mounts the actual organisms (corpusOverview,
 * runTriggerCard, generationsList) into the named slots.
 *
 * Pure template: no event handlers, no business logic, no API calls.
 */

export function renderIngestShellMarkup(): string {
  return `
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
  `;
}
