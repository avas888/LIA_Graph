/**
 * Ops ingestion Auto-Pilot factory. Decouplingv1 Phase 10 extraction.
 *
 * Owns the polling loop that drives a session through auto-process +
 * processing + batch-validation until every document reaches a terminal
 * state. Holds its own `autoPilotTimer` / `autoPilotSessionId` local
 * state so start/stop is idempotent.
 *
 * `updateAutoStatus` is exposed separately because renderSelectedSession
 * calls it outside the polling loop (when a running session is re-selected
 * and needs its status strip repainted).
 */

import { countRawDocs } from "@/features/ops/opsIngestionFormatters";
import { requestJson } from "@/features/ops/opsIngestionTypes";
import {
  formatOpsError,
  type IngestionActionPayload,
  type IngestionSession,
} from "@/features/ops/opsTypes";

import type { OpsApi } from "@/features/ops/opsIngestionApi";
import type { OpsControllerCtx } from "@/features/ops/opsIngestionContext";

export interface OpsAutoPilot {
  startAutoPilot: (sessionId: string) => void;
  stopAutoPilot: () => void;
  updateAutoStatus: (session: IngestionSession) => void;
  autoPilotTick: () => Promise<void>;
}

export function createOpsAutoPilot(
  ctx: OpsControllerCtx,
  api: OpsApi,
): OpsAutoPilot {
  const { dom, i18n, stateController, setFlash } = ctx;
  const { ingestionAutoStatus } = dom;

  const AUTO_POLL_INTERVAL = 4_000; // 4s between polls
  let autoPilotTimer: ReturnType<typeof setTimeout> | null = null;
  let autoPilotSessionId = "";

  function stopAutoPilot(): void {
    if (autoPilotTimer) {
      clearTimeout(autoPilotTimer);
      autoPilotTimer = null;
    }
    autoPilotSessionId = "";
    ingestionAutoStatus.hidden = true;
    ingestionAutoStatus.classList.remove("is-running");
  }

  /** Count raw/needs_classification docs from the document list (batch_summary lumps them into queued). */
  function updateAutoStatus(session: IngestionSession): void {
    const summary = session.batch_summary;
    const rawCount = countRawDocs(session);
    // batch_summary.queued includes raw docs, so subtract them
    const queuedCount = Math.max(0, Number(summary.queued ?? 0) - rawCount);
    const processingCount = Number(summary.processing ?? 0);
    const doneCount = Number(summary.done ?? 0);
    const failedCount = Number(summary.failed ?? 0);
    const bouncedCount = Number(summary.bounced ?? 0);
    const activeCount = queuedCount + processingCount;

    ingestionAutoStatus.hidden = false;

    // Build suffix for bounced docs (always shown if > 0)
    const bouncedSuffix = bouncedCount > 0 ? ` · ${bouncedCount} rebotados` : "";

    if (activeCount > 0 || rawCount > 0) {
      ingestionAutoStatus.classList.add("is-running");
      ingestionAutoStatus.textContent = i18n.t("ops.ingestion.auto.running", {
        queued: queuedCount,
        processing: processingCount,
        raw: rawCount,
      }) + bouncedSuffix;
    } else if (failedCount > 0) {
      ingestionAutoStatus.classList.remove("is-running");
      ingestionAutoStatus.textContent = i18n.t("ops.ingestion.auto.done", {
        done: doneCount,
        failed: failedCount,
        raw: rawCount,
      }) + bouncedSuffix;
    } else {
      ingestionAutoStatus.classList.remove("is-running");
      ingestionAutoStatus.textContent = i18n.t("ops.ingestion.auto.allDone", {
        done: doneCount,
      }) + bouncedSuffix;
    }
  }

  async function autoPilotTick(): Promise<void> {
    const sessionId = autoPilotSessionId;
    if (!sessionId) return;

    try {
      // 1. Refresh session state
      const session = await api.fetchIngestionSession(sessionId);
      stateController.upsertSession(session);
      ctx.render();
      updateAutoStatus(session);

      const summary = session.batch_summary;
      const rawCount = countRawDocs(session);
      const totalCount = Number(summary.total ?? 0);

      // 1b. If session has 0 documents, nothing to do — stop immediately
      if (totalCount === 0) {
        stopAutoPilot();
        return;
      }

      // 2. If there are raw docs that might have been classified since last tick,
      //    re-call auto-process to promote high-confidence ones to queued.
      if (rawCount > 0) {
        await requestJson<IngestionActionPayload>(
          `/api/ingestion/sessions/${encodeURIComponent(sessionId)}/auto-process`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ max_concurrency: 5 }),
          },
        );
      }

      // 3. If there are newly queued docs and nothing is processing, kick off processing.
      const refreshedSession = rawCount > 0
        ? await api.fetchIngestionSession(sessionId)
        : session;
      const refreshedRaw = countRawDocs(refreshedSession);
      const refreshedQueuedReal = Math.max(
        0,
        Number(refreshedSession.batch_summary.queued ?? 0) - refreshedRaw,
      );
      const refreshedProcessing = Number(refreshedSession.batch_summary.processing ?? 0);

      if (refreshedQueuedReal > 0 && refreshedProcessing === 0) {
        await api.startIngestionProcess(sessionId);
      }

      // Update view after any actions
      if (rawCount > 0) {
        stateController.upsertSession(refreshedSession);
        ctx.render();
        updateAutoStatus(refreshedSession);
      }

      // 4. Check termination: all docs done/failed/bounced, none queued/processing/raw
      const stillActive = refreshedQueuedReal + refreshedProcessing;

      if (totalCount > 0 && stillActive === 0 && refreshedRaw === 0) {
        // All documents have reached a terminal state — run batch validation if needed
        const gatePending = Number(refreshedSession.batch_summary.pending_batch_gate ?? 0);
        if (
          gatePending > 0 &&
          refreshedSession.status !== "running_batch_gates" &&
          refreshedSession.status !== "completed"
        ) {
          try {
            await api.validateBatch(sessionId);
          } catch (_e) { /* validation is best-effort */ }
        }
        // Final refresh and stop
        const finalSession = await api.fetchIngestionSession(sessionId);
        stateController.upsertSession(finalSession);
        ctx.render();
        updateAutoStatus(finalSession);
        stopAutoPilot();
        setFlash(
          i18n.t("ops.ingestion.auto.allDone", {
            done: Number(finalSession.batch_summary.done ?? 0),
          }),
          "success",
        );
        return;
      }

      // 5. If only raw docs remain (need manual intervention), stop polling
      //    but keep the status message visible.
      if (stillActive === 0 && refreshedRaw > 0) {
        ingestionAutoStatus.classList.remove("is-running");
        ingestionAutoStatus.textContent = i18n.t("ops.ingestion.auto.done", {
          done: Number(refreshedSession.batch_summary.done ?? 0),
          failed: Number(refreshedSession.batch_summary.failed ?? 0),
          raw: refreshedRaw,
        });
        stopAutoPilot();
        return;
      }

      // 6. Schedule next tick
      autoPilotTimer = setTimeout(() => void autoPilotTick(), AUTO_POLL_INTERVAL);
    } catch (error) {
      // On error, stop the loop and surface the error
      stopAutoPilot();
      setFlash(formatOpsError(error), "error");
    }
  }

  function startAutoPilot(sessionId: string): void {
    stopAutoPilot();
    autoPilotSessionId = sessionId;
    ingestionAutoStatus.hidden = false;
    ingestionAutoStatus.classList.add("is-running");
    ingestionAutoStatus.textContent = i18n.t("ops.ingestion.auto.running", {
      queued: 0,
      processing: 0,
      raw: 0,
    });
    // Start first tick after a short delay to let the server process
    autoPilotTimer = setTimeout(() => void autoPilotTick(), 2_000);
  }

  return {
    startAutoPilot,
    stopAutoPilot,
    updateAutoStatus,
    autoPilotTick,
  };
}
