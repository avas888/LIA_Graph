/**
 * Sub-topics curation page template — slots only.
 *
 * The render function returns empty slot containers. The
 * `subtopicController` mounts the actual organism (`subtopicCurationBoard`)
 * into the named slot.
 *
 * Pure template: no event handlers, no business logic, no API calls.
 */

export function renderSubtopicShellMarkup(): string {
  return `
    <main id="lia-subtopic-shell" class="lia-subtopic-shell" data-lia-template="subtopic-curation">
      <header class="lia-subtopic-shell__header">
        <p class="lia-subtopic-shell__eyebrow">Lia Graph · Lane 0 · Subtopic v1</p>
        <h1 class="lia-subtopic-shell__title">Sub-temas</h1>
        <p class="lia-subtopic-shell__lede">
          Curación de la taxonomía de subtemas propuesta por el pase de recolección
          AUTOGENERAR. Cada propuesta se acepta, rechaza, fusiona con otra o se
          renombra. Las decisiones se registran en
          <code>artifacts/subtopic_decisions.jsonl</code> y se promueven a
          <code>config/subtopic_taxonomy.json</code> desde la CLI.
        </p>
      </header>

      <div class="lia-subtopic-shell__row" data-slot="curation-board"></div>
      <div class="lia-subtopic-shell__row" data-slot="taxonomy-sidebar"></div>
    </main>
  `;
}
