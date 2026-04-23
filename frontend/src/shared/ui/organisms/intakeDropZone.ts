import {
  createIntakeFileRow,
  type IntakeFileRowOptions,
} from "@/shared/ui/molecules/intakeFileRow";
import { createSpinner } from "@/shared/ui/atoms/spinner";

// localStorage persistence. On first mount we re-render the last known
// intake batch (chips + server response) so a browser reload doesn't
// leave the operator wondering whether their files were placed or lost.
// The raw file bytes are NOT persisted (too large) — only the filenames,
// sizes, and the server response (which contains classifications). If
// the operator wants to re-ingest the same bytes they'd re-drag; the
// server dedupes by sha256 anyway.
const STORAGE_KEY = "intake-drop-zone.lastBatch";

interface PersistedBatch {
  queuedFilenames: Array<{
    filename: string;
    mime: string;
    bytes: number;
    relativePath: string;
  }>;
  lastResponse: IntakeDropZoneResponse | null;
  savedAt: string;
}

function readPersistedBatch(): PersistedBatch | null {
  try {
    if (typeof localStorage === "undefined") return null;
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as PersistedBatch;
    if (!parsed || typeof parsed !== "object") return null;
    return parsed;
  } catch {
    return null;
  }
}

function writePersistedBatch(batch: PersistedBatch | null): void {
  try {
    if (typeof localStorage === "undefined") return;
    if (batch == null) {
      localStorage.removeItem(STORAGE_KEY);
      return;
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(batch));
  } catch {
    /* quota exceeded or disabled — best-effort */
  }
}

/**
 * Organism: drag-and-drop intake zone.
 *
 * Composes `intakeFileRow` molecules. Owns drag/drop handlers + folder
 * traversal (via `DataTransferItem.webkitGetAsEntry()`) and renders a
 * queued-files list. The caller supplies an async `onIntake` callback
 * that performs the `POST /api/ingest/intake` HTTP call; the organism
 * then re-renders its rows using the backend-provided classification.
 *
 * The "Aprobar e ingerir" button stays disabled until the intake call
 * has returned at least one placed file. When clicked, it invokes the
 * `onApprove` callback supplied by the controller.
 */

export interface IntakeDropZoneFile {
  filename: string;
  bytes: number;
  mime?: string;
  relativePath: string;
  /** Kept so the controller can base64-encode + post the payload. */
  file: File;
}

export interface IntakeDropZoneResponseFile {
  filename: string;
  mime?: string | null;
  bytes?: number | null;
  detected_topic?: string | null;
  topic_label?: string | null;
  combined_confidence?: number | null;
  requires_review?: boolean;
  coercion_method?: string | null;
  // ingestfix-v2 Phase 7 — subtopic verdict propagation.
  subtopic_key?: string | null;
  subtopic_label?: string | null;
  subtopic_confidence?: number | null;
  subtopic_is_new?: boolean;
  requires_subtopic_review?: boolean;
}

export interface IntakeDropZoneResponse {
  ok: boolean;
  batch_id: string;
  summary: {
    received: number;
    placed: number;
    deduped: number;
    rejected: number;
  };
  files: IntakeDropZoneResponseFile[];
}

export interface IntakeDropZoneOptions {
  onIntake: (files: IntakeDropZoneFile[]) => Promise<IntakeDropZoneResponse>;
  onApprove?: (batchId: string) => void;
  /** Fires whenever the drawer's batch state changes (drop / intake
   * response / clear / rehydrate). The caller uses this to gate other
   * sections of the page — e.g. Paso 2 buttons stay disabled until at
   * least one file is in the drawer. */
  onBatchStateChange?: (state: {
    hasBatch: boolean;
    placed: number;
    analyzing: boolean;
  }) => void;
  /** Injected confirmation prompt for destructive operations (Borrar todo).
   * Keeps the organism atom-pure: the caller wires in the shared toast
   * confirm via `getToastController(i18n).confirm(...)`. If unset, falls
   * back to native `window.confirm()` so the organism stays usable in
   * fixtures / tests that don't have i18n wired up. */
  confirmDestructive?: (opts: {
    title: string;
    message: string;
    confirmLabel: string;
    cancelLabel: string;
  }) => Promise<boolean>;
}

const ALLOWED_EXTENSIONS = [".md", ".txt", ".json", ".pdf", ".docx"];

function hasAllowedExtension(filename: string): boolean {
  const lower = filename.toLowerCase();
  return ALLOWED_EXTENSIONS.some((ext) => lower.endsWith(ext));
}

function isHiddenPath(path: string): boolean {
  const segments = path.split("/").filter(Boolean);
  return segments.some((seg) => seg.startsWith("."));
}

function isMacOsxPath(path: string): boolean {
  return path.includes("__MACOSX/") || path.startsWith("__MACOSX/");
}

/**
 * Filter the allow-list: reject unsupported extensions, hidden files,
 * and anything that lives under `__MACOSX/` (common zip cruft).
 */
export function isAcceptedIntakeFile(filename: string, relativePath: string): boolean {
  if (!filename) return false;
  if (isMacOsxPath(relativePath)) return false;
  if (isHiddenPath(relativePath) || filename.startsWith(".")) return false;
  if (!hasAllowedExtension(filename)) return false;
  return true;
}

interface FileSystemEntryLike {
  isFile: boolean;
  isDirectory: boolean;
  name: string;
  fullPath?: string;
  file?: (cb: (f: File) => void) => void;
  createReader?: () => {
    readEntries: (cb: (entries: FileSystemEntryLike[]) => void) => void;
  };
}

async function readEntriesAll(
  reader: NonNullable<FileSystemEntryLike["createReader"]> extends () => infer R ? R : never,
): Promise<FileSystemEntryLike[]> {
  const collected: FileSystemEntryLike[] = [];
  // `readEntries` returns in batches until empty — loop until drained.
  // eslint-disable-next-line no-constant-condition
  while (true) {
    const batch: FileSystemEntryLike[] = await new Promise((resolve) => {
      (reader as { readEntries: (cb: (entries: FileSystemEntryLike[]) => void) => void }).readEntries(
        (entries) => resolve(entries || []),
      );
    });
    if (batch.length === 0) break;
    collected.push(...batch);
  }
  return collected;
}

async function walkEntry(
  entry: FileSystemEntryLike | null,
  parentPath: string,
): Promise<IntakeDropZoneFile[]> {
  if (!entry) return [];
  const thisPath = parentPath ? `${parentPath}/${entry.name}` : entry.name;
  if (entry.isFile) {
    if (!entry.file) return [];
    const file: File = await new Promise((resolve) => entry.file!(resolve));
    return [
      {
        filename: file.name,
        bytes: file.size,
        mime: file.type || undefined,
        relativePath: thisPath,
        file,
      },
    ];
  }
  if (entry.isDirectory && entry.createReader) {
    const reader = entry.createReader();
    const entries = await readEntriesAll(reader);
    const nested = await Promise.all(entries.map((e) => walkEntry(e, thisPath)));
    return nested.flat();
  }
  return [];
}

async function extractFromDataTransfer(
  dataTransfer: DataTransfer,
): Promise<IntakeDropZoneFile[]> {
  const items = dataTransfer.items ? Array.from(dataTransfer.items) : [];
  if (items.length > 0 && typeof (items[0] as DataTransferItem & { webkitGetAsEntry?: () => FileSystemEntryLike | null }).webkitGetAsEntry === "function") {
    const results: IntakeDropZoneFile[] = [];
    for (const item of items) {
      const entry = (item as DataTransferItem & { webkitGetAsEntry: () => FileSystemEntryLike | null }).webkitGetAsEntry();
      if (!entry) continue;
      const walked = await walkEntry(entry, "");
      results.push(...walked);
    }
    return results;
  }
  // Fallback: flat files only (no relative-path info available).
  const files = dataTransfer.files ? Array.from(dataTransfer.files) : [];
  return files.map((f) => ({
    filename: f.name,
    bytes: f.size,
    mime: f.type || undefined,
    relativePath: f.name,
    file: f,
  }));
}

function toIntakeRowVm(
  file: IntakeDropZoneFile,
  response?: IntakeDropZoneResponseFile,
): IntakeFileRowOptions {
  if (!response) {
    return {
      filename: file.filename,
      mime: file.mime,
      bytes: file.bytes,
      detectedTopic: null,
      topicLabel: null,
      combinedConfidence: null,
      requiresReview: false,
      coercionMethod: null,
    };
  }
  return {
    filename: response.filename || file.filename,
    mime: response.mime || file.mime,
    bytes: response.bytes ?? file.bytes,
    detectedTopic: response.detected_topic ?? null,
    topicLabel: response.topic_label ?? null,
    combinedConfidence: response.combined_confidence ?? null,
    requiresReview: !!response.requires_review,
    coercionMethod: response.coercion_method ?? null,
    subtopicKey: response.subtopic_key ?? null,
    subtopicLabel: response.subtopic_label ?? null,
    subtopicConfidence: response.subtopic_confidence ?? null,
    subtopicIsNew: !!response.subtopic_is_new,
    requiresSubtopicReview: !!response.requires_subtopic_review,
  };
}

export function createIntakeDropZone(opts: IntakeDropZoneOptions): HTMLElement {
  const { onIntake, onApprove, onBatchStateChange, confirmDestructive } = opts;
  function _notifyBatchState(): void {
    if (!onBatchStateChange) return;
    const hasBatch = state.queued.length > 0 || state.lastResponse != null;
    const placed = state.lastResponse?.summary?.placed ?? 0;
    onBatchStateChange({ hasBatch, placed, analyzing: state.analyzing });
  }

  const root = document.createElement("section");
  root.className = "lia-intake-drop-zone";
  root.setAttribute("data-lia-component", "intake-drop-zone");

  const header = document.createElement("header");
  header.className = "lia-intake-drop-zone__header";
  const title = document.createElement("h2");
  title.className = "lia-intake-drop-zone__title";
  title.textContent = "Arrastra archivos o carpetas";
  header.appendChild(title);
  const hint = document.createElement("p");
  hint.className = "lia-intake-drop-zone__hint";
  hint.textContent =
    "Acepta .md, .txt, .json, .pdf, .docx. Carpetas se recorren recursivamente. Ocultos y __MACOSX/ se descartan.";
  header.appendChild(hint);
  root.appendChild(header);

  const zone = document.createElement("div");
  zone.className = "lia-intake-drop-zone__zone";
  zone.setAttribute("role", "button");
  zone.setAttribute("tabindex", "0");
  zone.setAttribute("aria-label", "Zona de arrastre para ingesta");
  const zoneLabel = document.createElement("p");
  zoneLabel.className = "lia-intake-drop-zone__zone-label";
  zoneLabel.textContent = "Suelta aquí los archivos para enviarlos al intake";
  zone.appendChild(zoneLabel);
  root.appendChild(zone);

  const list = document.createElement("div");
  list.className = "lia-intake-drop-zone__list";
  list.setAttribute("data-role", "intake-file-list");
  root.appendChild(list);

  const feedback = document.createElement("p");
  feedback.className = "lia-intake-drop-zone__feedback";
  feedback.setAttribute("role", "status");
  root.appendChild(feedback);

  const actions = document.createElement("div");
  actions.className = "lia-intake-drop-zone__actions";
  const clear = document.createElement("button");
  clear.type = "button";
  clear.className =
    "lia-button lia-button--ghost lia-intake-drop-zone__clear";
  clear.textContent = "Borrar todo";
  clear.hidden = true;
  actions.appendChild(clear);
  const approve = document.createElement("button");
  approve.type = "button";
  approve.className = "lia-button lia-button--primary lia-intake-drop-zone__approve";
  approve.disabled = true;
  const approveLabel = document.createElement("span");
  approveLabel.className = "lia-intake-drop-zone__approve-label";
  approveLabel.textContent = "Aprobar e ingerir";
  approve.appendChild(approveLabel);
  actions.appendChild(approve);
  root.appendChild(actions);

  const state: {
    queued: IntakeDropZoneFile[];
    lastResponse: IntakeDropZoneResponse | null;
    analyzing: boolean;
  } = {
    queued: [],
    lastResponse: null,
    analyzing: false,
  };

  function _renderRows(): void {
    list.replaceChildren();
    if (state.queued.length === 0) {
      const empty = document.createElement("p");
      empty.className = "lia-intake-drop-zone__empty";
      empty.textContent = "Sin archivos en cola.";
      list.appendChild(empty);
      return;
    }
    const responseByName = new Map<string, IntakeDropZoneResponseFile>();
    if (state.lastResponse?.files) {
      for (const f of state.lastResponse.files) {
        if (f.filename) responseByName.set(f.filename, f);
      }
    }
    state.queued.forEach((file, index) => {
      const responseFile = responseByName.get(file.filename);
      const row = createIntakeFileRow({
        ...toIntakeRowVm(file, responseFile),
        onRemove: () => {
          state.queued.splice(index, 1);
          _renderRows();
          _syncApproveEnabled();
        },
      });
      list.appendChild(row);
    });
  }

  function _syncApproveEnabled(): void {
    const placed = state.lastResponse?.summary?.placed ?? 0;
    // Three states for the approve button:
    //   1. analyzing   → disabled, spinner + "Analizando archivos"
    //   2. ready-green → enabled, green, "Ir al siguiente paso →"
    //                    (files placed on disk; user now goes to Paso 2
    //                    to explicitly pick delta vs full rebuild)
    //   3. idle        → disabled, navy, "Ir al siguiente paso →"
    approve.classList.remove(
      "lia-intake-drop-zone__approve--analyzing",
      "lia-intake-drop-zone__approve--ready",
    );
    approve.replaceChildren();
    if (state.analyzing) {
      approve.disabled = true;
      approve.classList.add("lia-intake-drop-zone__approve--analyzing");
      approve.appendChild(createSpinner({ size: "sm", ariaLabel: "Analizando" }));
      const label = document.createElement("span");
      label.className = "lia-intake-drop-zone__approve-label";
      label.textContent = "Analizando archivos";
      approve.appendChild(label);
    } else {
      const label = document.createElement("span");
      label.className = "lia-intake-drop-zone__approve-label";
      label.textContent = "Ir al siguiente paso →";
      approve.appendChild(label);
      approve.disabled = placed <= 0;
      if (placed > 0) {
        approve.classList.add("lia-intake-drop-zone__approve--ready");
      }
    }
    // Borrar todo stays visible whenever the zone has anything in it —
    // queued files, a failed response, or a completed batch — so the
    // operator can reset without hunting individual × chips.
    clear.hidden = state.queued.length === 0 && state.lastResponse == null && !state.analyzing;
  }

  function _clearAll(): void {
    state.queued = [];
    state.lastResponse = null;
    state.analyzing = false;
    feedback.textContent = "";
    writePersistedBatch(null);
    _renderRows();
    _syncApproveEnabled();
  }

  function _persistCurrent(): void {
    if (state.queued.length === 0 && state.lastResponse == null) {
      writePersistedBatch(null);
      return;
    }
    writePersistedBatch({
      queuedFilenames: state.queued.map((f) => ({
        filename: f.filename,
        mime: f.mime,
        bytes: f.bytes,
        relativePath: f.relativePath,
      })),
      lastResponse: state.lastResponse,
      savedAt: new Date().toISOString(),
    });
  }

  function _rehydrate(): void {
    const persisted = readPersistedBatch();
    if (!persisted) return;
    const hasAnything = (persisted.queuedFilenames?.length ?? 0) > 0 || !!persisted.lastResponse;
    if (!hasAnything) return;
    // Rehydrate: file content bytes are NOT persisted (too big), so we
    // reconstruct the queue with empty content strings. The classifier
    // already ran server-side, so lastResponse carries the useful data.
    state.queued = (persisted.queuedFilenames ?? []).map((f) => ({
      filename: f.filename,
      mime: f.mime,
      bytes: f.bytes,
      relativePath: f.relativePath,
      content_base64: "",
    }));
    state.lastResponse = persisted.lastResponse ?? null;
    state.analyzing = false;
    _renderRows();
    _syncApproveEnabled();
    const placed = persisted.lastResponse?.summary?.placed ?? 0;
    const when = persisted.savedAt
      ? new Date(persisted.savedAt).toLocaleString("es-CO", {
          hour: "2-digit",
          minute: "2-digit",
          day: "2-digit",
          month: "short",
        })
      : "";
    if (placed > 0) {
      feedback.textContent =
        `Sesión previa restaurada (${when}) — ${placed} archivo(s) ya estaban clasificados.`;
    } else {
      feedback.textContent = `Sesión previa restaurada (${when}).`;
    }
  }

  async function _handleFiles(files: IntakeDropZoneFile[]): Promise<void> {
    const accepted = files.filter((f) => isAcceptedIntakeFile(f.filename, f.relativePath));
    if (accepted.length === 0) {
      feedback.textContent = "Ningún archivo elegible en el drop.";
      return;
    }
    state.queued = accepted;
    state.lastResponse = null;
    state.analyzing = true;
    _renderRows();
    _syncApproveEnabled();
    feedback.textContent = `Enviando ${accepted.length} archivo(s) al intake…`;
    try {
      const resp = await onIntake(accepted);
      state.lastResponse = resp;
      state.analyzing = false;
      _renderRows();
      _syncApproveEnabled();
      feedback.textContent = `Intake ok — placed ${resp.summary.placed} / deduped ${resp.summary.deduped} / rejected ${resp.summary.rejected}.`;
      _persistCurrent();
    } catch (err) {
      state.lastResponse = null;
      state.analyzing = false;
      _syncApproveEnabled();
      const message = err instanceof Error ? err.message : "intake falló";
      feedback.textContent = `Intake falló: ${message}`;
    }
  }

  zone.addEventListener("dragenter", (event) => {
    event.preventDefault();
    zone.classList.add("lia-intake-drop-zone__zone--active");
  });
  zone.addEventListener("dragover", (event) => {
    event.preventDefault();
    zone.classList.add("lia-intake-drop-zone__zone--active");
  });
  zone.addEventListener("dragleave", (event) => {
    event.preventDefault();
    zone.classList.remove("lia-intake-drop-zone__zone--active");
  });
  zone.addEventListener("drop", (event) => {
    event.preventDefault();
    zone.classList.remove("lia-intake-drop-zone__zone--active");
    const dt = (event as DragEvent).dataTransfer;
    if (!dt) return;
    void (async () => {
      const files = await extractFromDataTransfer(dt);
      await _handleFiles(files);
    })();
  });

  approve.addEventListener("click", () => {
    if (approve.disabled) return;
    const batchId = state.lastResponse?.batch_id;
    if (!batchId) return;
    if (onApprove) onApprove(batchId);
  });

  clear.addEventListener("click", () => {
    if (state.queued.length === 0 && state.lastResponse == null) return;
    // Adaptive confirm copy — three cases: analyzing, already processed,
    // or just queued. Prevents the operator from nuking the view state
    // without meaning to (especially dangerous mid-analysis).
    let title: string;
    let message: string;
    if (state.analyzing) {
      title = "¿Borrar mientras procesamos?";
      message =
        "Estamos procesando tus archivos. ¿Estás seguro que quieres borrar todo? " +
        "El servidor seguirá procesando los archivos que ya recibió; esto solo " +
        "limpia la vista local.";
    } else if (state.lastResponse != null) {
      const placed = state.lastResponse.summary?.placed ?? 0;
      title = "¿Borrar la vista del batch?";
      message =
        `Ya procesamos ${placed} archivo(s) y están en knowledge_base/. ` +
        `¿Borrar esta lista de la vista? Los archivos NO se eliminan del ` +
        `corpus — solo se limpia la vista.`;
    } else {
      title = "¿Borrar archivos en cola?";
      message =
        `¿Borrar los ${state.queued.length} archivo(s) en cola antes de enviarlos?`;
    }
    // Prefer the injected toast-based confirm (atomic design, transversal
    // across the app). Fall back to native confirm only if the caller
    // didn't wire one up (tests / fixtures).
    const fallbackConfirm = async (): Promise<boolean> =>
      Promise.resolve(window.confirm(`${title}\n\n${message}`));
    const confirmFn = confirmDestructive ?? fallbackConfirm;
    void confirmFn({
      title,
      message,
      confirmLabel: "Borrar todo",
      cancelLabel: "Cancelar",
    }).then((ok) => {
      if (ok) _clearAll();
    });
  });

  _renderRows();
  _syncApproveEnabled();
  // Restore the last intake batch from localStorage so a browser refresh
  // doesn't make the operator wonder whether their upload vanished.
  _rehydrate();

  return root;
}
