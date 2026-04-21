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
  `;
}
