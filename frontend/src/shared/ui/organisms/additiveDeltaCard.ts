/**
 * Additive-delta intro card (organism).
 *
 * Visual peer of `runTriggerCard.ts` — same atomic level, same layout shape.
 * Renders the "Delta aditivo" title + intro copy + a mount slot where the
 * `bindAdditiveDelta` controller attaches its panel. Pure DOM construction;
 * no event wiring (the inner panel owns its own controller).
 *
 * Returns `{ element, mount }` so callers can append the card to a slot and
 * bind the additive-delta panel to the mount in a single call.
 */

export interface AdditiveDeltaCardHandles {
  /** The full card element — append to the parent slot. */
  element: HTMLElement;
  /** The inner mount slot — pass to `bindAdditiveDelta({ rootElement: mount })`. */
  mount: HTMLElement;
}

export function createAdditiveDeltaCard(): AdditiveDeltaCardHandles {
  const root = document.createElement("article");
  root.className = "lia-adelta-card";
  root.setAttribute("data-lia-component", "additive-delta-card");

  const header = document.createElement("header");
  header.className = "lia-adelta-card__header";

  const title = document.createElement("h3");
  title.className = "lia-adelta-card__title";
  title.textContent = "Delta aditivo";
  header.appendChild(title);

  const body = document.createElement("p");
  body.className = "lia-adelta-card__body";
  body.innerHTML =
    "Compara <code>knowledge_base/</code> contra la base ya publicada y " +
    "procesa <strong>solo agregados y modificados</strong>. Los archivos " +
    "llegan a la carpeta en el <strong>Paso 1 arriba</strong> (arrastre, " +
    "Dropbox o editor directo). " +
    "<strong>Nunca retira docs de producción</strong>: si un archivo está " +
    "en la base pero falta en disco, este flujo lo marca como diagnóstico " +
    "y sigue. El borrado de cloud es CLI-only y explícito " +
    "(<code>--allow-retirements</code>).";
  header.appendChild(body);

  const steps = document.createElement("p");
  steps.className = "lia-adelta-card__steps";
  steps.innerHTML =
    "<strong>Previsualizar</strong> muestra el diff sin escribir nada " +
    "(segundos para deltas pequeños). <strong>Aplicar</strong> procesa el " +
    "delta con una confirmación explícita (minutos, no horas). Si cambiaste " +
    "el prompt del clasificador o la taxonomía, usá <strong>Ingesta " +
    "completa</strong> a la derecha — el delta aditivo no re-clasifica docs " +
    "byte-idénticos.";
  header.appendChild(steps);

  root.appendChild(header);

  const mount = document.createElement("div");
  mount.className = "lia-adelta-card__mount";
  root.appendChild(mount);

  return { element: root, mount };
}
