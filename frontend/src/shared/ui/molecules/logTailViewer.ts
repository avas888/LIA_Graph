export interface LogTailViewerOptions {
  initialLines?: string[];
  autoScroll?: boolean;
  onCopy?: (() => void) | null;
  summaryLabel?: string;
  className?: string;
}

export interface LogTailViewerHandle {
  element: HTMLElement;
  appendLines: (lines: string[]) => void;
  clear: () => void;
}

/**
 * Molecule: collapsible `<pre>` log surface. Exposes imperative
 * `appendLines` + `clear` handles to callers so the controller can
 * stream partial updates without re-rendering.
 */
export function createLogTailViewer(opts: LogTailViewerOptions = {}): LogTailViewerHandle {
  const {
    initialLines = [],
    autoScroll = true,
    onCopy = null,
    summaryLabel = "Log de ejecución",
    className = "",
  } = opts;

  const root = document.createElement("div");
  root.className = ["lia-log-tail-viewer", className].filter(Boolean).join(" ");
  root.setAttribute("data-lia-component", "log-tail-viewer");

  const toolbar = document.createElement("div");
  toolbar.className = "lia-log-tail-viewer__toolbar";

  const copyBtn = document.createElement("button");
  copyBtn.type = "button";
  copyBtn.className = "lia-log-tail-viewer__copy";
  copyBtn.textContent = "Copiar";
  copyBtn.setAttribute("aria-label", "Copiar log");
  toolbar.appendChild(copyBtn);

  const details = document.createElement("details");
  details.className = "lia-log-tail-viewer__details";
  details.open = true;

  const summary = document.createElement("summary");
  summary.className = "lia-log-tail-viewer__summary";
  summary.textContent = summaryLabel;
  details.appendChild(summary);

  const body = document.createElement("pre");
  body.className = "lia-log-tail-viewer__body";
  body.textContent = initialLines.join("\n");
  details.appendChild(body);

  root.appendChild(toolbar);
  root.appendChild(details);

  const state = { lines: [...initialLines] };

  const scrollToBottom = (): void => {
    if (!autoScroll) return;
    body.scrollTop = body.scrollHeight;
  };

  const render = (): void => {
    body.textContent = state.lines.join("\n");
    scrollToBottom();
  };

  const appendLines = (lines: string[]): void => {
    if (!lines || lines.length === 0) return;
    state.lines.push(...lines);
    render();
  };

  const clear = (): void => {
    state.lines = [];
    body.textContent = "";
  };

  copyBtn.addEventListener("click", () => {
    const payload = state.lines.join("\n");
    const clipboard = (globalThis as { navigator?: Navigator }).navigator?.clipboard;
    if (clipboard && typeof clipboard.writeText === "function") {
      void clipboard.writeText(payload);
    }
    if (onCopy) onCopy();
  });

  if (autoScroll) scrollToBottom();

  return { element: root, appendLines, clear };
}
