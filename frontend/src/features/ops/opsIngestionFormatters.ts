// @ts-nocheck

/**
 * Pure formatting helpers for the ops ingestion controller.
 *
 * Extracted from `opsIngestionController.ts` during granularize-v2
 * round 19 (Section A · sub-round 1). All functions here take their
 * closure dependencies as explicit arguments rather than via closure
 * capture, so they are testable in isolation.
 *
 * The larger extractions (api / intake / upload / renderers /
 * bindEvents) will follow in subsequent rounds.
 */

import type { I18nRuntime } from "@/shared/i18n";
import type {
  IngestionSession,
  IntakeEntry,
} from "@/features/ops/opsTypes";


export const SUPPORTED_INGESTION_EXTENSIONS = new Set([".pdf", ".md", ".txt", ".docx"]);
export const HIDDEN_FILE_PREFIXES = [".", "__MACOSX"];
export const FOLDER_UPLOAD_CONCURRENCY = 3;
export const FOLDER_PENDING_STORAGE_PREFIX = "lia_folder_pending_";


/** Filter out hidden files and unsupported extensions. */
export function filterSupportedFiles(files: File[]): File[] {
  return files.filter((f) => {
    const name = f.name;
    if (HIDDEN_FILE_PREFIXES.some((p) => name.startsWith(p))) return false;
    const dotIdx = name.lastIndexOf(".");
    const ext = dotIdx >= 0 ? name.slice(dotIdx).toLowerCase() : "";
    return SUPPORTED_INGESTION_EXTENSIONS.has(ext);
  });
}


/** Resolve the relative path for a file — from browser `webkitRelativePath`
 * (native `<input webkitdirectory>`) or from the explicit
 * `folderRelativePaths` map the controller builds when users select a
 * folder via `showDirectoryPicker`. */
export function getRelativePath(
  file: File,
  folderRelativePaths: Map<File, string>,
): string {
  return (file as { webkitRelativePath?: string }).webkitRelativePath
    || folderRelativePaths.get(file)
    || "";
}


/** Fingerprint a file for de-duplication across drops — name + size +
 * lastModified + relativePath. Same fingerprint = same file; used to
 * make `addFilesToIntake` idempotent. */
export function fileKey(
  file: File,
  folderRelativePaths: Map<File, string>,
): string {
  const rel = getRelativePath(file, folderRelativePaths);
  return `${file.name}|${file.size}|${(file as File & { lastModified?: number }).lastModified ?? 0}|${rel}`;
}


/** Human-readable file size (B / KB / MB). */
export function formatFileSize(bytes: number): string {
  return bytes < 1024
    ? `${bytes} B`
    : bytes < 1024 * 1024
      ? `${(bytes / 1024).toFixed(1)} KB`
      : `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}


/** Translate an intake entry's verdict into the user-facing pill label. */
export function verdictLabel(entry: IntakeEntry, i18n: I18nRuntime): string {
  const docId = entry.preflightEntry?.existing_doc_id || "";
  switch (entry.verdict) {
    case "pending":     return i18n.t("ops.ingestion.verdict.pending");
    case "new":         return i18n.t("ops.ingestion.verdict.new");
    case "revision":    return docId
      ? i18n.t("ops.ingestion.verdict.revisionOf", { docId })
      : i18n.t("ops.ingestion.verdict.revision");
    case "duplicate":   return docId
      ? i18n.t("ops.ingestion.verdict.duplicateOf", { docId })
      : i18n.t("ops.ingestion.verdict.duplicate");
    case "artifact":    return i18n.t("ops.ingestion.verdict.artifact");
    case "unreadable":  return i18n.t("ops.ingestion.verdict.unreadable");
  }
}


/** Create the colored verdict-pill span for an intake entry. */
export function makeVerdictPill(entry: IntakeEntry, i18n: I18nRuntime): HTMLSpanElement {
  const pill = document.createElement("span");
  pill.className = `ops-verdict-pill ops-verdict-pill--${entry.verdict}`;
  pill.textContent = verdictLabel(entry, i18n);
  return pill;
}


/** Count documents still in the `raw` / `needs_classification` stage. */
export function countRawDocs(session: IngestionSession): number {
  return session.documents.filter(
    (d) => d.status === "raw" || d.status === "needs_classification",
  ).length;
}
