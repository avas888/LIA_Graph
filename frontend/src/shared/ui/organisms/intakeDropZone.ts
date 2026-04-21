import {
  createIntakeFileRow,
  type IntakeFileRowOptions,
} from "@/shared/ui/molecules/intakeFileRow";

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
  const { onIntake, onApprove } = opts;

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
  const approve = document.createElement("button");
  approve.type = "button";
  approve.className = "lia-button lia-button--primary lia-intake-drop-zone__approve";
  approve.textContent = "Aprobar e ingerir";
  approve.disabled = true;
  actions.appendChild(approve);
  root.appendChild(actions);

  const state: {
    queued: IntakeDropZoneFile[];
    lastResponse: IntakeDropZoneResponse | null;
  } = {
    queued: [],
    lastResponse: null,
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
    approve.disabled = placed <= 0;
  }

  async function _handleFiles(files: IntakeDropZoneFile[]): Promise<void> {
    const accepted = files.filter((f) => isAcceptedIntakeFile(f.filename, f.relativePath));
    if (accepted.length === 0) {
      feedback.textContent = "Ningún archivo elegible en el drop.";
      return;
    }
    state.queued = accepted;
    state.lastResponse = null;
    _renderRows();
    _syncApproveEnabled();
    feedback.textContent = `Enviando ${accepted.length} archivo(s) al intake…`;
    try {
      const resp = await onIntake(accepted);
      state.lastResponse = resp;
      _renderRows();
      _syncApproveEnabled();
      feedback.textContent = `Intake ok — placed ${resp.summary.placed} / deduped ${resp.summary.deduped} / rejected ${resp.summary.rejected}.`;
    } catch (err) {
      state.lastResponse = null;
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

  _renderRows();
  _syncApproveEnabled();

  return root;
}
