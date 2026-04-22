/**
 * Ops ingestion API factory. Decouplingv1 Phase 7 extraction.
 *
 * Owns the 13 network-bound entry points the controller calls into:
 * corpora + session CRUD, the upload endpoint, the start/retry/validate/eject
 * actions, and the refresh orchestrators that reconcile the store after
 * network changes.
 *
 * State mutations still go through `ctx.stateController`, so the factory is
 * a pure "do IO + update store + call ctx.render()" layer. `refreshIngestion`
 * and friends call `ctx.render()` / `ctx.trace()` via the live ctx
 * bindings — the controller rebinds those after renderers are constructed.
 */

import { ApiError, getJson } from "@/shared/api/client";
import {
  formatOpsError,
  isCompletedSession,
  type CorporaPayload,
  type EjectResult,
  type IngestionActionPayload,
  type IngestionDocument,
  type IngestionSession,
  type IngestionSessionPayload,
  type IngestionSessionsPayload,
} from "@/features/ops/opsTypes";
import { getRelativePath } from "@/features/ops/opsIngestionFormatters";
import { postJsonOrThrow, requestJson } from "@/features/ops/opsIngestionTypes";

import type { OpsControllerCtx } from "@/features/ops/opsIngestionContext";

export interface OpsApi {
  resolveSessionCorpus: () => string;
  fetchCorpora: () => Promise<void>;
  fetchIngestionSessions: () => Promise<IngestionSession[]>;
  fetchIngestionSession: (sessionId: string) => Promise<IngestionSession>;
  createIngestionSession: (corpus: string) => Promise<IngestionSession>;
  uploadIngestionFile: (
    sessionId: string,
    file: File,
    batchType: string,
  ) => Promise<IngestionDocument>;
  startIngestionProcess: (sessionId: string) => Promise<IngestionActionPayload>;
  validateBatch: (sessionId: string) => Promise<IngestionActionPayload>;
  retryIngestionSession: (sessionId: string) => Promise<IngestionActionPayload>;
  ejectIngestionSession: (sessionId: string, force?: boolean) => Promise<EjectResult>;
  refreshIngestion: (opts?: {
    showWheel?: boolean;
    reportError?: boolean;
    focusSessionId?: string;
  }) => Promise<void>;
  refreshSelectedSession: (opts: {
    sessionId: string;
    showWheel?: boolean;
    reportError?: boolean;
  }) => Promise<void>;
  ensureSelectedSession: () => Promise<IngestionSession>;
}

export function createOpsApi(ctx: OpsControllerCtx): OpsApi {
  const { dom, stateController, withThinkingWheel, setFlash } = ctx;

  function resolveSessionCorpus(): string {
    if (ctx.state.selectedCorpus !== "autogenerar") return ctx.state.selectedCorpus;
    return "autogenerar";
  }

  async function fetchCorpora(): Promise<void> {
    const payload = await getJson<CorporaPayload>("/api/corpora");
    const corpora = Array.isArray(payload.corpora) ? payload.corpora : [];
    stateController.setCorpora(corpora);

    const availableKeys = new Set(corpora.map((corpus) => corpus.key));
    availableKeys.add("autogenerar");
    if (!availableKeys.has(ctx.state.selectedCorpus)) {
      stateController.setSelectedCorpus("autogenerar");
    }
  }

  async function fetchIngestionSessions(): Promise<IngestionSession[]> {
    const payload = await getJson<IngestionSessionsPayload>(
      `/api/ingestion/sessions?limit=20`,
    );
    return Array.isArray(payload.sessions) ? payload.sessions : [];
  }

  async function fetchIngestionSession(sessionId: string): Promise<IngestionSession> {
    const payload = await getJson<IngestionSessionPayload>(
      `/api/ingestion/sessions/${encodeURIComponent(sessionId)}`,
    );
    if (!payload.session) {
      throw new Error("missing_session");
    }
    return payload.session;
  }

  async function createIngestionSession(corpus: string): Promise<IngestionSession> {
    const payload = await postJsonOrThrow<IngestionSessionPayload, { corpus: string }>(
      "/api/ingestion/sessions",
      { corpus },
    );
    if (!payload.session) {
      throw new Error("missing_session");
    }
    return payload.session;
  }

  async function uploadIngestionFile(
    sessionId: string,
    file: File,
    batchType: string,
  ): Promise<IngestionDocument> {
    const topicValue = dom.ingestionCorpusSelect.value === "autogenerar"
      ? ""
      : dom.ingestionCorpusSelect.value;
    const headers: Record<string, string> = {
      "Content-Type": "application/octet-stream",
      "X-Upload-Filename": file.name,
      "X-Upload-Mime": file.type || "application/octet-stream",
      "X-Upload-Batch-Type": batchType,
    };
    if (topicValue) {
      headers["X-Upload-Topic"] = topicValue;
    }
    const relativePath = getRelativePath(file, ctx.state.folderRelativePaths);
    if (relativePath) {
      headers["X-Upload-Relative-Path"] = relativePath;
    }
    console.log(`[upload] ${file.name} (${file.size}B) → session=${sessionId} batch=${batchType}`);
    const response = await fetch(
      `/api/ingestion/sessions/${encodeURIComponent(sessionId)}/files`,
      { method: "POST", headers, body: file },
    );
    const rawText = await response.text();
    let payload: IngestionActionPayload;
    try {
      payload = JSON.parse(rawText) as IngestionActionPayload;
    } catch {
      console.error(`[upload] ${file.name} — response not JSON (${response.status}):`, rawText.slice(0, 300));
      throw new Error(`Upload response not JSON: ${response.status} ${rawText.slice(0, 100)}`);
    }
    if (!response.ok) {
      const msg = (payload as unknown as { error?: string }).error || response.statusText;
      console.error(`[upload] ${file.name} — HTTP ${response.status}:`, msg);
      throw new ApiError(msg, response.status, payload);
    }
    if (!payload.document) {
      console.error(`[upload] ${file.name} — no document in response:`, payload);
      throw new Error("missing_document");
    }
    console.log(`[upload] ${file.name} → OK doc_id=${payload.document.doc_id} status=${payload.document.status}`);
    return payload.document;
  }

  async function startIngestionProcess(sessionId: string): Promise<IngestionActionPayload> {
    return requestJson<IngestionActionPayload>(
      `/api/ingestion/sessions/${encodeURIComponent(sessionId)}/process`,
      { method: "POST" },
    );
  }

  async function validateBatch(sessionId: string): Promise<IngestionActionPayload> {
    return requestJson<IngestionActionPayload>(
      `/api/ingestion/sessions/${encodeURIComponent(sessionId)}/validate-batch`,
      { method: "POST" },
    );
  }

  async function retryIngestionSession(sessionId: string): Promise<IngestionActionPayload> {
    return requestJson<IngestionActionPayload>(
      `/api/ingestion/sessions/${encodeURIComponent(sessionId)}/retry`,
      { method: "POST" },
    );
  }

  async function ejectIngestionSession(sessionId: string, force = false): Promise<EjectResult> {
    const qs = force ? "?force=true" : "";
    return requestJson<EjectResult>(
      `/api/ingestion/sessions/${encodeURIComponent(sessionId)}${qs}`,
      { method: "DELETE" },
    );
  }

  async function refreshIngestion({
    showWheel = true,
    reportError = true,
    focusSessionId = "",
  }: {
    showWheel?: boolean;
    reportError?: boolean;
    focusSessionId?: string;
  } = {}): Promise<void> {
    const task = async () => {
      await fetchCorpora();
      ctx.render();

      let sessions = await fetchIngestionSessions();
      const candidateId = focusSessionId || ctx.state.selectedSessionId;
      if (candidateId && !sessions.some((session) => session.session_id === candidateId)) {
        try {
          const detail = await fetchIngestionSession(candidateId);
          sessions = [detail, ...sessions.filter((session) => session.session_id !== candidateId)];
        } catch (_error) {
          if (candidateId === ctx.state.selectedSessionId) {
            stateController.setSelectedSession(null);
          }
        }
      }

      stateController.setSessions(
        sessions.sort(
          (left, right) => Date.parse(String(right.updated_at || 0)) - Date.parse(String(left.updated_at || 0)),
        ),
      );
      stateController.syncSelectedSession();
      ctx.render();
    };

    try {
      if (showWheel) {
        await withThinkingWheel(task);
      } else {
        await task();
      }
    } catch (error) {
      if (reportError) {
        setFlash(formatOpsError(error), "error");
      }
      ctx.render();
      throw error;
    }
  }

  async function refreshSelectedSession({
    sessionId,
    showWheel = false,
    reportError = true,
  }: {
    sessionId: string;
    showWheel?: boolean;
    reportError?: boolean;
  }): Promise<void> {
    const task = async () => {
      const session = await fetchIngestionSession(sessionId);
      stateController.upsertSession(session);
      ctx.render();
    };

    try {
      if (showWheel) {
        await withThinkingWheel(task);
      } else {
        await task();
      }
    } catch (error) {
      if (reportError) {
        setFlash(formatOpsError(error), "error");
      }
      throw error;
    }
  }

  async function ensureSelectedSession(): Promise<IngestionSession> {
    const effectiveCorpus = resolveSessionCorpus();
    console.log(
      `[folder-ingest] ensureSelectedSession: effectiveCorpus="${effectiveCorpus}", selectedSession=${
        ctx.state.selectedSession?.session_id || "null"
      } (status=${ctx.state.selectedSession?.status || "null"}, corpus=${ctx.state.selectedSession?.corpus || "null"})`,
    );

    // Reuse the selected session only if it's not completed and matches corpus
    if (
      ctx.state.selectedSession &&
      !isCompletedSession(ctx.state.selectedSession) &&
      ctx.state.selectedSession.status !== "completed" &&
      (ctx.state.selectedSession.corpus === effectiveCorpus || effectiveCorpus === "autogenerar")
    ) {
      console.log(`[folder-ingest] Reusing session ${ctx.state.selectedSession.session_id}`);
      return ctx.state.selectedSession;
    }

    // Create a new session — try requested corpus, fall back to first active
    ctx.trace(`Creando sesión con corpus="${effectiveCorpus}"...`);
    try {
      const session = await createIngestionSession(effectiveCorpus);
      ctx.trace(`Sesión creada: ${session.session_id} (corpus=${session.corpus})`);
      stateController.upsertSession(session);
      return session;
    } catch (error) {
      ctx.trace(
        `Creación falló para corpus="${effectiveCorpus}": ${error instanceof Error ? error.message : String(error)}`,
      );
      if (effectiveCorpus === "autogenerar") {
        const fallback = ctx.state.corpora.find((c) => c.active)?.key || "declaracion_renta";
        ctx.trace(`Reintentando con corpus="${fallback}"...`);
        const session = await createIngestionSession(fallback);
        ctx.trace(`Sesión fallback: ${session.session_id} (corpus=${session.corpus})`);
        stateController.upsertSession(session);
        return session;
      }
      throw error;
    }
  }

  return {
    resolveSessionCorpus,
    fetchCorpora,
    fetchIngestionSessions,
    fetchIngestionSession,
    createIngestionSession,
    uploadIngestionFile,
    startIngestionProcess,
    validateBatch,
    retryIngestionSession,
    ejectIngestionSession,
    refreshIngestion,
    refreshSelectedSession,
    ensureSelectedSession,
  };
}
