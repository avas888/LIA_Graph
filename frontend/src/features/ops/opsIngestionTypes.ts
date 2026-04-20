// @ts-nocheck

/**
 * Types + shared HTTP utilities for the ops ingestion controller.
 *
 * Extracted from `opsIngestionController.ts` during granularize-v2
 * round 15. This module owns the pre-controller material — DOM shape
 * interface, controller-options interface, async-task runner type, and
 * two `ApiError`-wrapping fetch helpers. Kept framework-free so tests
 * can exercise each helper in isolation and so the controller module
 * focuses on DOM orchestration + state management.
 */

import { ApiError, postJson } from "@/shared/api/client";
import type { I18nRuntime } from "@/shared/i18n";
import type { OpsStateController } from "@/features/ops/opsState";


export type AsyncTaskRunner = <T>(task: () => Promise<T>) => Promise<T>;


export interface OpsIngestionDom {
  ingestionCorpusSelect: HTMLSelectElement;
  ingestionBatchTypeSelect: HTMLSelectElement;
  ingestionDropzone: HTMLElement;
  ingestionFileInput: HTMLInputElement;
  ingestionFolderInput: HTMLInputElement;
  ingestionSelectFilesBtn: HTMLButtonElement;
  ingestionSelectFolderBtn: HTMLButtonElement;
  ingestionUploadProgress: HTMLDivElement;
  ingestionPendingFiles: HTMLParagraphElement;
  ingestionOverview: HTMLParagraphElement;
  ingestionRefreshBtn: HTMLButtonElement;
  ingestionCreateSessionBtn: HTMLButtonElement;
  ingestionUploadBtn: HTMLButtonElement;
  ingestionProcessBtn: HTMLButtonElement;
  ingestionAutoProcessBtn: HTMLButtonElement;
  ingestionValidateBatchBtn: HTMLButtonElement;
  ingestionRetryBtn: HTMLButtonElement;
  ingestionDeleteSessionBtn: HTMLButtonElement;
  ingestionSessionMeta: HTMLParagraphElement;
  ingestionSessionsList: HTMLUListElement;
  selectedSessionMeta: HTMLParagraphElement;
  ingestionLastError: HTMLDivElement;
  ingestionLastErrorMessage: HTMLParagraphElement;
  ingestionLastErrorGuidance: HTMLParagraphElement;
  ingestionLastErrorNext: HTMLParagraphElement;
  ingestionKanban: HTMLDivElement;
  ingestionLogAccordion: HTMLDivElement;
  ingestionLogBody: HTMLPreElement;
  ingestionLogCopyBtn: HTMLButtonElement;
  ingestionAutoStatus: HTMLParagraphElement;
  addCorpusBtn: HTMLButtonElement | null;
  addCorpusDialog: HTMLDialogElement | null;
  ingestionBounceLog: HTMLDetailsElement | null;
  ingestionBounceBody: HTMLPreElement | null;
  ingestionBounceCopy: HTMLButtonElement | null;
}


export interface CreateOpsIngestionControllerOptions {
  i18n: I18nRuntime;
  stateController: OpsStateController;
  dom: OpsIngestionDom;
  withThinkingWheel: AsyncTaskRunner;
  setFlash: (message?: string, tone?: "success" | "error") => void;
}


export async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch (_error) {
    payload = null;
  }
  if (!response.ok) {
    const message =
      payload && typeof payload === "object" && "error" in payload
        ? String((payload as { error?: string }).error || response.statusText)
        : response.statusText;
    throw new ApiError(message, response.status, payload);
  }
  return payload as T;
}


export async function postJsonOrThrow<TResponse, TBody>(url: string, body: TBody): Promise<TResponse> {
  const { response, data } = await postJson<TResponse, TBody>(url, body);
  if (!response.ok) {
    const message =
      data && typeof data === "object" && "error" in (data as object)
        ? String((data as { error?: string }).error || response.statusText)
        : response.statusText;
    throw new ApiError(message, response.status, data);
  }
  return data as TResponse;
}
