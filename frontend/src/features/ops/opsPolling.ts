import { formatOpsError, isRunningSession } from "@/features/ops/opsTypes";
import type { OpsStateController } from "@/features/ops/opsState";

type AsyncTaskRunner = <T>(task: () => Promise<T>) => Promise<T>;

/** Polling interval when docs are actively being processed. */
const ACTIVE_POLL_MS = 3000;
/** Polling interval when no active processing is detected. */
const IDLE_POLL_MS = 8000;

interface StartOpsPollingOptions {
  stateController: OpsStateController;
  withThinkingWheel: AsyncTaskRunner;
  setFlash: (message?: string, tone?: "success" | "error") => void;
  refreshRuns: (options?: { showWheel?: boolean; reportError?: boolean }) => Promise<void>;
  refreshIngestion: (options?: {
    showWheel?: boolean;
    reportError?: boolean;
    focusSessionId?: string;
  }) => Promise<void>;
  refreshCorpusLifecycle?: () => Promise<void>;
  refreshEmbeddings?: () => Promise<void>;
  refreshReindex?: () => Promise<void>;
  intervalMs?: number;
}

export function startOpsPolling({
  stateController,
  withThinkingWheel,
  setFlash,
  refreshRuns,
  refreshIngestion,
  refreshCorpusLifecycle,
  refreshEmbeddings,
  refreshReindex,
  intervalMs,
}: StartOpsPollingOptions): () => void {
  void (async () => {
    try {
      await withThinkingWheel(async () => {
        await Promise.all([
          refreshRuns({ showWheel: false, reportError: false }),
          refreshIngestion({ showWheel: false, reportError: false }),
          refreshCorpusLifecycle?.(),
          refreshEmbeddings?.(),
          refreshReindex?.(),
        ]);
      });
    } catch (error) {
      setFlash(formatOpsError(error), "error");
    }
  })();

  let currentIntervalId: number | null = null;
  let currentIntervalMs: number = intervalMs ?? IDLE_POLL_MS;

  function hasActiveProcessing(): boolean {
    const session = stateController.state.selectedSession;
    if (!session) return false;
    if (isRunningSession(String(session.status || ""))) return true;
    const docs = session.documents || [];
    return docs.some(
      (d) =>
        d.status === "in_progress" ||
        d.status === "processing" ||
        d.status === "extracting" ||
        d.status === "etl" ||
        d.status === "writing" ||
        d.status === "gates",
    );
  }

  function schedulePoll(): void {
    const desiredMs = intervalMs ?? (hasActiveProcessing() ? ACTIVE_POLL_MS : IDLE_POLL_MS);
    if (currentIntervalId !== null && desiredMs === currentIntervalMs) return;

    if (currentIntervalId !== null) {
      window.clearInterval(currentIntervalId);
    }
    currentIntervalMs = desiredMs;
    currentIntervalId = window.setInterval(() => {
      void refreshRuns({ showWheel: false, reportError: false });
      void refreshIngestion({
        showWheel: false,
        reportError: false,
        focusSessionId: stateController.getFocusedRunningSessionId(),
      });
      void refreshCorpusLifecycle?.();
      void refreshEmbeddings?.();
      void refreshReindex?.();
      // Re-evaluate adaptive interval after each poll
      if (!intervalMs) {
        schedulePoll();
      }
    }, currentIntervalMs);
  }

  schedulePoll();

  return () => {
    if (currentIntervalId !== null) {
      window.clearInterval(currentIntervalId);
      currentIntervalId = null;
    }
  };
}
