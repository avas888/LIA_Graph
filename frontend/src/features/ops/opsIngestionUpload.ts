/**
 * Ops ingestion Upload factory. Decouplingv1 Phase 8 extraction.
 *
 * Owns the file-picker / folder-walker / concurrency-bounded upload loop
 * plus the upload-progress + preflight-scan-progress renderers and the
 * local-storage tab-crash recovery helpers.
 *
 * The orchestrator `directFolderIngest` stays in the controller closure
 * because it stitches together upload + api + auto-pilot across three
 * factories — keeping it where they are wired together avoids threading
 * four factory handles through this module.
 */

import {
  FOLDER_PENDING_STORAGE_PREFIX,
  FOLDER_UPLOAD_CONCURRENCY,
  getRelativePath,
} from "@/features/ops/opsIngestionFormatters";
import { postJsonOrThrow } from "@/features/ops/opsIngestionTypes";
import type { PreflightManifest } from "@/features/ops/opsTypes";

import type { OpsApi } from "@/features/ops/opsIngestionApi";
import type { OpsControllerCtx } from "@/features/ops/opsIngestionContext";

export interface OpsUpload {
  resolveFolderFiles: (dataTransfer: DataTransfer) => Promise<File[]>;
  readDirectoryHandle: (
    dirHandle: FileSystemDirectoryHandle,
    basePath?: string,
  ) => Promise<File[]>;
  uploadFilesWithConcurrency: (
    sessionId: string,
    files: File[],
    batchType: string,
    concurrency?: number,
  ) => Promise<{
    uploaded: number;
    failed: number;
    errors: Array<{ filename: string; error: string }>;
  }>;
  renderUploadProgress: () => void;
  renderScanProgress: () => void;
  persistFolderPending: (sessionId: string) => void;
  clearFolderPending: (sessionId: string) => void;
  getStoredFolderPendingCount: (sessionId: string) => number;
  requestPreflight: (
    fileEntries: Array<{
      filename: string;
      relative_path: string;
      size: number;
      content_hash: string;
    }>,
    corpus: string,
  ) => Promise<PreflightManifest>;
}

export function createOpsUpload(ctx: OpsControllerCtx, api: OpsApi): OpsUpload {
  const { dom, stateController, i18n } = ctx;
  const { ingestionUploadProgress } = dom;

  async function resolveFolderFiles(dataTransfer: DataTransfer): Promise<File[]> {
    const files: File[] = [];
    const entries: FileSystemEntry[] = [];

    for (let i = 0; i < dataTransfer.items.length; i++) {
      const entry = dataTransfer.items[i].webkitGetAsEntry?.();
      if (entry) entries.push(entry);
    }

    // If no entries have directories, this is a flat file drop — return null
    if (!entries.some((e) => e.isDirectory)) return [];

    async function walkEntry(entry: FileSystemEntry): Promise<void> {
      if (entry.isFile) {
        const file = await new Promise<File>((resolve, reject) => {
          (entry as FileSystemFileEntry).file(resolve, reject);
        });
        ctx.state.folderRelativePaths.set(file, entry.fullPath.replace(/^\//, ""));
        files.push(file);
      } else if (entry.isDirectory) {
        const reader = (entry as FileSystemDirectoryEntry).createReader();
        let batch: FileSystemEntry[];
        do {
          batch = await new Promise<FileSystemEntry[]>((resolve, reject) => {
            reader.readEntries(resolve, reject);
          });
          for (const child of batch) await walkEntry(child);
        } while (batch.length > 0);
      }
    }

    for (const entry of entries) await walkEntry(entry);
    return files;
  }

  /**
   * Read all files recursively from a FileSystemDirectoryHandle
   * (showDirectoryPicker API — Chrome/Edge). Stores relative paths.
   */
  async function readDirectoryHandle(
    dirHandle: FileSystemDirectoryHandle,
    basePath = "",
  ): Promise<File[]> {
    const files: File[] = [];
    for await (const [name, handle] of (dirHandle as any).entries()) {
      const path = basePath ? `${basePath}/${name}` : name;
      if (handle.kind === "file") {
        const file: File = await (handle as FileSystemFileHandle).getFile();
        ctx.state.folderRelativePaths.set(file, path);
        files.push(file);
      } else if (handle.kind === "directory") {
        const sub = await readDirectoryHandle(handle as FileSystemDirectoryHandle, path);
        files.push(...sub);
      }
    }
    return files;
  }

  async function uploadFilesWithConcurrency(
    sessionId: string,
    files: File[],
    batchType: string,
    concurrency: number = FOLDER_UPLOAD_CONCURRENCY,
  ): Promise<{ uploaded: number; failed: number; errors: Array<{ filename: string; error: string }> }> {
    let uploaded = 0;
    let failed = 0;
    let active = 0;
    let idx = 0;

    const errors: Array<{ filename: string; error: string }> = [];

    return new Promise((resolve) => {
      function next(): void {
        while (active < concurrency && idx < files.length) {
          const file = files[idx++];
          active++;
          api.uploadIngestionFile(sessionId, file, batchType)
            .then(() => { uploaded++; })
            .catch((err) => {
              failed++;
              const msg = err instanceof Error ? err.message : String(err);
              errors.push({ filename: file.name, error: msg });
              console.error(`[folder-ingest] Upload failed: ${file.name}`, err);
            })
            .finally(() => {
              active--;
              stateController.setFolderUploadProgress({
                total: files.length,
                uploaded,
                failed,
                uploading: idx < files.length || active > 0,
              });
              renderUploadProgress();
              if (idx < files.length || active > 0) next();
              else resolve({ uploaded, failed, errors });
            });
        }
      }
      stateController.setFolderUploadProgress({ total: files.length, uploaded: 0, failed: 0, uploading: true });
      renderUploadProgress();
      next();
    });
  }

  function renderUploadProgress(): void {
    const progress = ctx.state.folderUploadProgress;
    if (!progress || !progress.uploading) {
      ingestionUploadProgress.hidden = true;
      ingestionUploadProgress.innerHTML = "";
      return;
    }

    const current = progress.uploaded + progress.failed;
    const pct = progress.total > 0 ? Math.round((current / progress.total) * 100) : 0;
    const inflight = Math.max(0, Math.min(FOLDER_UPLOAD_CONCURRENCY, progress.total - current));

    ingestionUploadProgress.hidden = false;
    ingestionUploadProgress.innerHTML = `
      <div class="ops-upload-progress-header">
        <span>${i18n.t("ops.ingestion.uploadProgress", { current, total: progress.total })}</span>
        <span>${pct}%</span>
      </div>
      <div class="ops-upload-progress-bar">
        <span class="ops-upload-progress-fill" style="width:${pct}%"></span>
      </div>
      <div class="ops-upload-progress-detail">
        ${i18n.t("ops.ingestion.uploadProgressDetail", {
          uploaded: progress.uploaded,
          failed: progress.failed,
          inflight,
        })}
      </div>
    `;
  }

  function renderScanProgress(): void {
    const progress = ctx.state.preflightScanProgress;
    if (!progress || !progress.scanning) {
      ingestionUploadProgress.hidden = true;
      ingestionUploadProgress.innerHTML = "";
      return;
    }

    const pct = progress.total > 0 ? Math.round((progress.hashed / progress.total) * 100) : 0;
    ingestionUploadProgress.hidden = false;
    ingestionUploadProgress.innerHTML = `
      <div class="ops-preflight-scan">
        <div class="ops-preflight-scan-header">
          <span>${i18n.t("ops.ingestion.preflight.scanning", { hashed: progress.hashed, total: progress.total })}</span>
          <span>${pct}%</span>
        </div>
        <div class="ops-preflight-scan-bar">
          <span class="ops-preflight-scan-fill" style="width:${pct}%"></span>
        </div>
        <div class="ops-preflight-scan-detail">${i18n.t("ops.ingestion.preflight.scanningDetail")}</div>
      </div>
    `;
  }

  function persistFolderPending(sessionId: string): void {
    // pendingFiles holds the approved (post-dedup) subset that directFolderIngest uploads.
    if (ctx.state.pendingFiles.length === 0) return;
    if (getRelativePath(ctx.state.pendingFiles[0]) === "") return;
    try {
      const entries = ctx.state.pendingFiles.map((f) => ({
        name: f.name,
        relativePath: getRelativePath(f),
        size: f.size,
      }));
      localStorage.setItem(FOLDER_PENDING_STORAGE_PREFIX + sessionId, JSON.stringify(entries));
    } catch (_e) { /* ignore */ }
  }

  function clearFolderPending(sessionId: string): void {
    try {
      localStorage.removeItem(FOLDER_PENDING_STORAGE_PREFIX + sessionId);
    } catch (_e) { /* ignore */ }
  }

  function getStoredFolderPendingCount(sessionId: string): number {
    try {
      const raw = localStorage.getItem(FOLDER_PENDING_STORAGE_PREFIX + sessionId);
      if (!raw) return 0;
      const entries = JSON.parse(raw);
      if (!Array.isArray(entries)) return 0;
      // Subtract already-uploaded files
      const session = ctx.state.sessions.find((s) => s.session_id === sessionId);
      if (!session) return entries.length;
      const uploadedNames = new Set((session.documents || []).map((d) => d.filename));
      return entries.filter((e: { name: string }) => !uploadedNames.has(e.name)).length;
    } catch (_e) {
      return 0;
    }
  }

  async function requestPreflight(
    fileEntries: Array<{ filename: string; relative_path: string; size: number; content_hash: string }>,
    corpus: string,
  ): Promise<PreflightManifest> {
    const payload = await postJsonOrThrow<
      { ok: boolean; manifest: PreflightManifest },
      { corpus: string; files: typeof fileEntries }
    >(
      "/api/ingestion/preflight",
      { corpus, files: fileEntries },
    );
    return payload.manifest;
  }

  return {
    resolveFolderFiles,
    readDirectoryHandle,
    uploadFilesWithConcurrency,
    renderUploadProgress,
    renderScanProgress,
    persistFolderPending,
    clearFolderPending,
    getStoredFolderPendingCount,
    requestPreflight,
  };
}
