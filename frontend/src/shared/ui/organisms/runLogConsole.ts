import { createLogTailViewer } from "@/shared/ui/molecules/logTailViewer";

/**
 * Organism: run-log console.
 *
 * Thin wrapper around the `logTailViewer` molecule that adds a header
 * card and surfaces imperative `appendLines` / `clear` handles the
 * controller can feed as tail-polling results arrive.
 *
 * The "Copiar" affordance delegates to the molecule's `onCopy`
 * contract, which itself uses `navigator.clipboard?.writeText` guarded
 * for jsdom.
 */

export interface RunLogConsoleOptions {
  initialLines?: string[];
  onCopy?: (() => void) | null;
  summaryLabel?: string;
}

export interface RunLogConsoleHandle {
  element: HTMLElement;
  appendLines: (lines: string[]) => void;
  clear: () => void;
}

export function createRunLogConsole(opts: RunLogConsoleOptions = {}): RunLogConsoleHandle {
  const { initialLines = [], onCopy = null, summaryLabel = "Log de ejecución" } = opts;

  const root = document.createElement("section");
  root.className = "lia-run-log-console";
  root.setAttribute("data-lia-component", "run-log-console");

  const header = document.createElement("header");
  header.className = "lia-run-log-console__header";

  const title = document.createElement("h3");
  title.className = "lia-run-log-console__title";
  title.textContent = "Log en vivo";
  header.appendChild(title);

  const sub = document.createElement("p");
  sub.className = "lia-run-log-console__subtitle";
  sub.textContent = "Streaming del archivo artifacts/jobs/<job>.log — se actualiza cada 1.5s.";
  header.appendChild(sub);

  root.appendChild(header);

  const handle = createLogTailViewer({
    initialLines,
    autoScroll: true,
    onCopy,
    summaryLabel,
    className: "lia-run-log-console__viewer",
  });

  root.appendChild(handle.element);

  return {
    element: root,
    appendLines: handle.appendLines,
    clear: handle.clear,
  };
}
