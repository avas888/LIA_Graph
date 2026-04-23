/**
 * Molecule: additive-delta activity feeler.
 *
 * Compact "something is happening" card rendered while a long-running
 * operation (preview or apply) is in flight but no real progress data
 * has arrived yet. Mirrors the ticking clock pattern used by
 * additiveDeltaProgressPane so the operator always sees a live counter.
 *
 * The handle exposes ``setLiveProgress({classified, lastFilename})`` so
 * the controller can feed in real server-side counters (e.g. from the
 * ``/api/ingest/additive/preview-progress`` endpoint tailing the
 * classifier events log).
 *
 * Destroy to stop the ticker.
 */

import { createSpinner } from "@/shared/ui/atoms/spinner";

export interface AdditiveDeltaActivityFeelerOptions {
  title: string;
  /** Prose under the title — explains what the server is doing right now. */
  body: string;
}

export interface AdditiveDeltaActivityFeelerLiveProgress {
  classified: number;
  lastFilename?: string | null;
  /** Real denominator — the number of docs the server actually has to
   * classify (content-hash shortcut has already skipped the rest).
   * When null, we fall back to the vague "~1.300" placeholder. */
  classifierInputCount?: number | null;
  /** How many docs the shortcut skipped. Shown as a reassuring side
   * note so the operator sees the shortcut is working. */
  prematchedCount?: number | null;
  /** Run id — displayed in the header as a grep handle so the operator
   * can pull the exact events for this run from ``logs/events.jsonl``. */
  deltaId?: string | null;
}

export interface AdditiveDeltaActivityFeelerHandle {
  element: HTMLElement;
  setLiveProgress: (p: AdditiveDeltaActivityFeelerLiveProgress) => void;
  destroy: () => void;
}

export function createAdditiveDeltaActivityFeeler(
  opts: AdditiveDeltaActivityFeelerOptions,
): AdditiveDeltaActivityFeelerHandle {
  const root = document.createElement("section");
  root.className = "lia-adelta-feeler";
  root.setAttribute("data-lia-component", "additive-delta-activity-feeler");
  root.setAttribute("aria-live", "polite");

  const header = document.createElement("header");
  header.className = "lia-adelta-feeler__header";

  const spinnerWrap = document.createElement("span");
  spinnerWrap.className = "lia-adelta-feeler__spinner";
  spinnerWrap.appendChild(createSpinner({ size: "md", ariaLabel: "Procesando" }));

  const titleWrap = document.createElement("div");
  titleWrap.className = "lia-adelta-feeler__title-wrap";
  const title = document.createElement("h3");
  title.className = "lia-adelta-feeler__title";
  title.textContent = opts.title;
  const runIdEl = document.createElement("code");
  runIdEl.className = "lia-adelta-feeler__run-id";
  runIdEl.hidden = true;
  const elapsed = document.createElement("span");
  elapsed.className = "lia-adelta-feeler__elapsed";
  elapsed.textContent = "00:00";
  titleWrap.append(title, runIdEl, elapsed);

  header.append(spinnerWrap, titleWrap);
  root.appendChild(header);

  const body = document.createElement("p");
  body.className = "lia-adelta-feeler__body";
  body.textContent = opts.body;
  root.appendChild(body);

  const liveLine = document.createElement("p");
  liveLine.className = "lia-adelta-feeler__live";
  liveLine.hidden = true;
  root.appendChild(liveLine);

  const hint = document.createElement("p");
  hint.className = "lia-adelta-feeler__hint";
  hint.textContent =
    "Puedes cambiar de pestaña — el trabajo sigue corriendo en el servidor.";
  root.appendChild(hint);

  const startedAt = Date.now();
  function renderElapsed(): void {
    const secs = Math.max(0, Math.floor((Date.now() - startedAt) / 1000));
    const mm = String(Math.floor(secs / 60)).padStart(2, "0");
    const ss = String(secs % 60).padStart(2, "0");
    elapsed.textContent = `${mm}:${ss}`;
  }
  renderElapsed();
  const tickHandle = setInterval(renderElapsed, 1000);

  function setLiveProgress(p: AdditiveDeltaActivityFeelerLiveProgress): void {
    const count = Math.max(0, Math.floor(p.classified ?? 0));
    const denom = p.classifierInputCount ?? null;
    const prematched = p.prematchedCount ?? null;
    if (count <= 0 && !p.lastFilename && denom == null) {
      liveLine.hidden = true;
      liveLine.textContent = "";
      return;
    }
    liveLine.hidden = false;
    const shortName = (p.lastFilename ?? "").split("/").pop() ?? "";
    // Use the real denominator when the server knows it; otherwise a
    // vague but honest "~1.300" fallback.
    const totalLabel = denom != null ? String(denom) : "~1.300";
    const skipNote =
      prematched != null && prematched > 0
        ? ` — ${prematched} saltados por shortcut`
        : "";
    if (shortName) {
      liveLine.textContent =
        `Clasificados ${count} de ${totalLabel}${skipNote} — último: ${shortName}`;
    } else {
      liveLine.textContent =
        `Clasificados ${count} de ${totalLabel}${skipNote}`;
    }
  }

  return {
    element: root,
    setLiveProgress,
    destroy: () => clearInterval(tickHandle),
  };
}
