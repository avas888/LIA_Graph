/**
 * Additive-corpus-v1 controller (Phase 8).
 *
 * Orchestrates the 5-state UI machine (Idle → Previewed → Running →
 * Terminal, with transient Error) atop the 6 /api/ingest/additive/*
 * endpoints. Plan references: §8.C (UI components), §8.D (state model +
 * reload-safe mount), §8.E (failure-mode matrix F1-F12).
 */

import {
  createAdditiveDeltaActionRow,
  type AdditiveDeltaActionRowHandle,
  type AdditiveDeltaActionRowViewModel,
  type AdditiveDeltaUiState,
} from "@/shared/ui/molecules/additiveDeltaActionRow";
import {
  createAdditiveDeltaBanner,
  type AdditiveDeltaBannerViewModel,
} from "@/shared/ui/molecules/additiveDeltaBanner";
import {
  createAdditiveDeltaActivityFeeler,
  type AdditiveDeltaActivityFeelerHandle,
} from "@/shared/ui/molecules/additiveDeltaActivityFeeler";
import {
  createAdditiveDeltaProgressPane,
  type AdditiveDeltaProgressHandle,
  type AdditiveDeltaProgressViewModel,
  type AdditiveDeltaStage,
} from "@/shared/ui/molecules/additiveDeltaProgressPane";
import {
  createAdditiveDeltaTerminalBanner,
  type AdditiveDeltaTerminalStage,
  type AdditiveDeltaTerminalViewModel,
} from "@/shared/ui/molecules/additiveDeltaTerminalBanner";

import {
  createAdditiveDeltaReattachStore,
  reconcileReattachSource,
  type AdditiveDeltaReattachStore,
} from "@/features/ingest/additiveDeltaReattach";
import {
  subscribeJobEvents,
  type AdditiveDeltaSseEvent,
  type AdditiveDeltaSseHandle,
  type AdditiveDeltaSseOptions,
  type AdditiveDeltaSseStatus,
} from "@/features/ingest/additiveDeltaSse";
import { getJson, postJson } from "@/shared/api/client";

// ── API contracts ────────────────────────────────────────────

interface PreviewResponse {
  ok: boolean;
  target: string;
  delta_id: string;
  baseline_generation_id: string;
  summary: {
    delta_id: string;
    baseline_generation_id: string;
    added: number;
    modified: number;
    removed: number;
    unchanged: number;
    is_empty: boolean;
  };
  sample_chips?: {
    added?: string[];
    modified?: string[];
    removed?: string[];
  };
}

interface ApplyResponse {
  ok: boolean;
  job_id: string;
  delta_id?: string | null;
  events_url?: string;
  status_url?: string;
  cancel_url?: string;
}

interface ApplyBusyResponse {
  ok: false;
  error: "delta_lock_busy";
  blocking_job_id: string;
  target: string;
}

interface StatusResponse {
  ok: boolean;
  job: {
    job_id: string;
    lock_target: string;
    stage: string;
    delta_id: string | null;
    progress_pct: number;
    started_at: string | null;
    last_heartbeat_at: string | null;
    completed_at: string | null;
    created_by: string | null;
    cancel_requested: boolean;
    error_class: string | null;
    error_message: string | null;
    report_json: Record<string, unknown> | null;
  } | null;
}

interface LiveResponse {
  ok: boolean;
  target: string;
  job_id: string | null;
  job: StatusResponse["job"];
}

// ── Binding options ─────────────────────────────────────────────

export interface AdditiveDeltaBindingOptions {
  rootElement: HTMLElement;
  target?: string; // defaults to "production"
  fetchImpl?: typeof fetch;
  storage?: Storage | null;
  sseOptions?: AdditiveDeltaSseOptions;
  onError?: (message: string) => void;
  /** Optional toast-based confirm bridge (same shape as the one the
   * intake drop zone consumes). When present, the deep-preview path uses
   * it instead of the native ``window.confirm()``. */
  confirmDestructive?: (opts: {
    title: string;
    message: string;
    confirmLabel: string;
    cancelLabel: string;
  }) => Promise<boolean>;
}

export interface AdditiveDeltaControllerHandle {
  destroy: () => void;
  /** Programmatically trigger Previsualizar (as if the user clicked it).
   * Used by the intake drop-zone when flow="delta" is selected — the
   * operator expects "approve" to map to "preview the delta" then explicit
   * Aplicar confirmation, not silent apply. */
  preview: () => Promise<void>;
}

// ── Controller ──────────────────────────────────────────────────

const TERMINAL_STAGES: readonly AdditiveDeltaTerminalStage[] = [
  "completed",
  "failed",
  "cancelled",
];

function isTerminalStage(stage: string): stage is AdditiveDeltaTerminalStage {
  return (TERMINAL_STAGES as readonly string[]).includes(stage);
}

export function bindAdditiveDelta(
  opts: AdditiveDeltaBindingOptions,
): AdditiveDeltaControllerHandle {
  const target = opts.target ?? "production";
  const fetchImpl = opts.fetchImpl ?? fetch.bind(globalThis);
  const store: AdditiveDeltaReattachStore = createAdditiveDeltaReattachStore(
    opts.storage,
  );

  const root = opts.rootElement;
  root.classList.add("lia-adelta-panel");
  root.setAttribute("data-lia-component", "additive-delta-controller");

  const bannerSlot = document.createElement("div");
  bannerSlot.className = "lia-adelta-panel__banner";
  const progressSlot = document.createElement("div");
  progressSlot.className = "lia-adelta-panel__progress";
  const terminalSlot = document.createElement("div");
  terminalSlot.className = "lia-adelta-panel__terminal";

  const action = createAdditiveDeltaActionRow(
    { state: "idle" },
    {
      onPreview: () => void runPreview({ deepScan: false }),
      onDeepPreview: () => void runDeepPreviewWithConfirm(),
      onApply: () => void runApply(),
      onCancel: () => void runCancel(),
      onReset: () => resetToIdle(),
    },
  );
  root.append(action.element, bannerSlot, progressSlot, terminalSlot);

  let currentPreview: PreviewResponse | null = null;
  let progressHandle: AdditiveDeltaProgressHandle | null = null;
  let feelerHandle: AdditiveDeltaActivityFeelerHandle | null = null;
  let sseHandle: AdditiveDeltaSseHandle | null = null;
  let uiState: AdditiveDeltaUiState = "idle";
  // Last-known progress VM. Holding it here (instead of re-reading from
  // pane.dataset on every sseStatus change) means renderSseStatus can
  // patch ONE field without clobbering stage/progress/heartbeat that
  // came from the latest snapshot.
  let currentProgressVm: AdditiveDeltaProgressViewModel | null = null;
  // Tracks the currently-active foreground operation so Cancelar knows
  // what to abort/POST. Keeps Cancelar idempotent — clicking it twice
  // while "cancelling" is already in flight is a no-op.
  let inFlight: "preview" | "apply" | null = null;
  let activeJobId: string | null = null;
  let cancelling = false;

  let feelerPollHandle: ReturnType<typeof setInterval> | null = null;

  function clearFeeler(): void {
    if (feelerPollHandle) {
      clearInterval(feelerPollHandle);
      feelerPollHandle = null;
    }
    if (feelerHandle) {
      feelerHandle.destroy();
      feelerHandle = null;
    }
  }

  function showFeeler(title: string, body: string, trackProgress = false): void {
    clearFeeler();
    feelerHandle = createAdditiveDeltaActivityFeeler({ title, body });
    bannerSlot.replaceChildren(feelerHandle.element);
    if (trackProgress) {
      const tick = async () => {
        if (!feelerHandle) return;
        try {
          const data = await getJson<{
            ok?: boolean;
            available?: boolean;
            classified_since_last_run_boundary?: number;
            last_filename?: string | null;
          }>("/api/ingest/additive/preview-progress");
          if (!data?.available) return;
          feelerHandle.setLiveProgress({
            classified: data.classified_since_last_run_boundary ?? 0,
            lastFilename: data.last_filename ?? null,
          });
        } catch {
          /* transient — next poll */
        }
      };
      void tick();
      feelerPollHandle = setInterval(tick, 3_000);
    }
  }

  function setState(next: AdditiveDeltaUiState, vmPatch?: Partial<AdditiveDeltaActionRowViewModel>): void {
    uiState = next;
    action.update({
      state: next,
      deltaId: vmPatch?.deltaId ?? currentPreview?.delta_id,
      counts: vmPatch?.counts ?? (currentPreview
        ? {
            added: currentPreview.summary.added,
            modified: currentPreview.summary.modified,
            removed: currentPreview.summary.removed,
          }
        : undefined),
    });
  }

  function resetToIdle(): void {
    clearFeeler();
    inFlight = null;
    activeJobId = null;
    cancelling = false;
    currentProgressVm = null;
    bannerSlot.replaceChildren();
    progressSlot.replaceChildren();
    terminalSlot.replaceChildren();
    currentPreview = null;
    if (progressHandle) {
      progressHandle.destroy();
      progressHandle = null;
    }
    if (sseHandle) {
      sseHandle.close();
      sseHandle = null;
    }
    store.clear();
    setState("idle");
  }

  function surfaceError(message: string): void {
    opts.onError?.(message);
  }

  // ── actions ──────────────────────────────────────────────────

  async function runPreview(opts: { deepScan: boolean }): Promise<void> {
    inFlight = "preview";
    setState("pending");
    if (opts.deepScan) {
      showFeeler(
        "Análisis profundo del corpus…",
        "Lia está re-clasificando TODOS los ~1.3k documentos con el LLM (PASO 4) para detectar drift del clasificador sobre archivos byte-idénticos. Tarda 20–25 minutos y cuesta ~US$ 6-16 en Gemini. Avance en vivo abajo.",
        true,
      );
    } else {
      showFeeler(
        "Analizando delta…",
        "Lia compara los archivos de knowledge_base/ contra la base ya publicada por content_hash. Solo re-clasifica los archivos genuinamente nuevos o editados — los demás reutilizan su fingerprint anterior. Rápido para deltas pequeños.",
        true,
      );
    }
    try {
      // Use the shared postJson helper so the Bearer token from localStorage
      // lands in the Authorization header — otherwise admin-gated endpoints
      // return 401 and the user has no clue why.
      const { response, data } = await postJson<
        PreviewResponse,
        { target: string; force_full_classify: boolean }
      >("/api/ingest/additive/preview", {
        target,
        force_full_classify: opts.deepScan,
      });
      // If the user clicked Cancelar while we were waiting for this
      // response, inFlight was cleared — don't mutate UI state, just
      // drop the response on the floor.
      if (inFlight !== "preview") {
        return;
      }
      if (!response.ok || !data) {
        clearFeeler();
        inFlight = null;
        surfaceError(`Preview falló (HTTP ${response.status}).`);
        setState("idle");
        return;
      }
      clearFeeler();
      inFlight = null;
      currentPreview = data;
      const vm: AdditiveDeltaBannerViewModel = {
        deltaId: data.delta_id,
        baselineGenerationId: data.baseline_generation_id,
        counts: {
          added: data.summary.added,
          modified: data.summary.modified,
          removed: data.summary.removed,
          unchanged: data.summary.unchanged,
        },
        samples: {
          added: (data.sample_chips?.added ?? []).map((l) => ({ label: l })),
          modified: (data.sample_chips?.modified ?? []).map((l) => ({ label: l })),
          removed: (data.sample_chips?.removed ?? []).map((l) => ({ label: l })),
        },
        isEmpty: Boolean(data.summary.is_empty),
      };
      bannerSlot.replaceChildren(createAdditiveDeltaBanner(vm));
      progressSlot.replaceChildren();
      terminalSlot.replaceChildren();
      setState(data.summary.is_empty ? "previewed-empty" : "previewed");
    } catch (err) {
      // If cancel raced us, don't show an extra error toast.
      if (inFlight !== "preview") return;
      clearFeeler();
      inFlight = null;
      surfaceError(String(err));
      setState("idle");
    }
  }

  async function runApply(): Promise<void> {
    if (!currentPreview || currentPreview.summary.is_empty) {
      surfaceError("No hay delta listo para aplicar.");
      return;
    }
    inFlight = "apply";
    setState("pending");
    showFeeler(
      "Encolando delta…",
      "Reservando un slot de procesamiento en el servidor y disparando el worker. Esto es rápido (segundos); el procesamiento real arranca inmediatamente después.",
    );
    try {
      const { response, data } = await postJson<
        ApplyResponse | ApplyBusyResponse,
        { target: string; delta_id: string }
      >("/api/ingest/additive/apply", {
        target,
        delta_id: currentPreview.delta_id,
      });
      // Cancel raced us — drop the response on the floor; runCancel
      // has already reverted the UI.
      if (inFlight !== "apply") return;
      if (response.status === 409) {
        const busy = data as ApplyBusyResponse;
        surfaceError(
          `Ya hay un delta en curso (${busy.blocking_job_id}). Reattacheando…`,
        );
        inFlight = null;
        attachToJob(busy.blocking_job_id);
        return;
      }
      if (!response.ok || !data) {
        inFlight = null;
        surfaceError(`Apply falló (HTTP ${response.status}).`);
        setState("previewed");
        return;
      }
      const applied = data as ApplyResponse;
      store.set(applied.job_id);
      inFlight = null;
      attachToJob(applied.job_id);
    } catch (err) {
      if (inFlight !== "apply") return;
      inFlight = null;
      surfaceError(String(err));
      setState("previewed");
    }
  }

  async function runDeepPreviewWithConfirm(): Promise<void> {
    // Opt-in confirm before the expensive path. Uses the shared
    // transversal toast confirm (getToastController.confirm) when the
    // controller was wired with i18n; native window.confirm fallback
    // otherwise (tests / fixtures).
    const confirmFn = opts.confirmDestructive ?? ((o) =>
      Promise.resolve(window.confirm(`${o.title}\n\n${o.message}`)));
    const ok = await confirmFn({
      title: "Procedimiento largo — ¿estás seguro?",
      message:
        "El análisis profundo re-clasifica los ~1.300 documentos del corpus " +
        "con el LLM completo (PASO 4). Esto es un procedimiento LARGO: tarda " +
        "20–25 minutos de reloj real y cuesta aprox. US$ 6–16 en Gemini. " +
        "Úsalo solo cuando cambie el prompt del clasificador o la taxonomía " +
        "de subtemas; para uploads rutinarios, la Previsualización normal " +
        "(ruta rápida) ya detecta archivos nuevos y editados en segundos. " +
        "¿Quieres continuar con el análisis profundo?",
      confirmLabel: "Sí, correr análisis profundo",
      cancelLabel: "Cancelar",
    });
    if (!ok) return;
    void runPreview({ deepScan: true });
  }

  async function runCancel(): Promise<void> {
    // Idempotent: if the user spams Cancelar, only the first click does
    // real work. Subsequent clicks are no-ops while the prior cancel is
    // still settling.
    if (cancelling) return;
    cancelling = true;

    const jobId = currentJobId();

    // Branch 1: preview is in flight (the classifier's running on the
    // server). We can't truly stop the server-side classifier from the
    // browser — but we CAN stop showing feedback and revert the UI. The
    // server keeps processing; its result is harmless because it just
    // writes to logs.
    if (inFlight === "preview") {
      clearFeeler();
      inFlight = null;
      cancelling = false;
      setState("idle");
      surfaceError(
        "Cancelación en cliente. El clasificador puede seguir corriendo en el servidor — su resultado se descarta.",
      );
      return;
    }

    // Branch 2: apply POST in flight but no job_id yet (the 202 hasn't
    // returned). Flip the flag and the success path will abort before
    // attaching to the job.
    if (inFlight === "apply" && !jobId) {
      clearFeeler();
      inFlight = null;
      cancelling = false;
      setState(currentPreview ? "previewed" : "idle");
      surfaceError("Solicitud de apply cancelada antes de encolarse.");
      return;
    }

    // Branch 3: a worker job is running. POST cancel to flip
    // cancel_requested=true — the worker stops at the next stage
    // boundary and finalizes as "cancelled". Poll then picks up the
    // terminal stage and renders the terminal banner.
    if (jobId) {
      try {
        await postJson<unknown, Record<string, never>>(
          `/api/ingest/additive/cancel?job_id=${encodeURIComponent(jobId)}`,
          {},
        );
        // Mark the pane as "cancel requested" so the operator sees
        // immediate feedback while the worker winds down.
        if (progressHandle) {
          const pane = progressHandle.element;
          pane.dataset.cancelRequested = "true";
          const stage = (pane.dataset.currentStage as
            | "queued"
            | "parsing"
            | "supabase"
            | "falkor"
            | "finalize") ?? "queued";
          const pct = parseInt(
            pane.querySelector<HTMLElement>(".lia-adelta-progress__bar-fill")?.style.width || "0",
            10,
          ) || 0;
          progressHandle.update({
            jobId,
            stage,
            progressPct: pct,
            lastHeartbeatAt: pane.dataset.heartbeat ?? null,
            sseStatus: "polling",
            cancelRequested: true,
          });
        }
      } catch (err) {
        surfaceError(
          `La solicitud de cancelación no pudo enviarse (${String(err)}). ` +
            "Intenta de nuevo o usa Nuevo delta para reiniciar la vista sin tocar el worker.",
        );
      } finally {
        cancelling = false;
      }
      return;
    }

    // Branch 4: nothing to cancel. Rare but possible (race with terminal
    // arrival). Don't explode — just tell the operator and stay put.
    cancelling = false;
    surfaceError("No hay operación en curso para cancelar.");
  }

  function currentJobId(): string | null {
    return activeJobId ?? store.get();
  }

  function attachToJob(jobId: string): void {
    clearFeeler();
    inFlight = null;
    activeJobId = jobId;
    bannerSlot.replaceChildren();
    terminalSlot.replaceChildren();
    progressSlot.replaceChildren();
    // Seed the VM cell so every subsequent sseStatus/snapshot patch
    // starts from a coherent object — not from reading back stale
    // dataset attributes (which was the bug that froze the pane on
    // "queued/0%" even while the worker progressed through all stages).
    currentProgressVm = {
      jobId,
      stage: "queued",
      progressPct: 0,
      lastHeartbeatAt: null,
      sseStatus: "connecting",
      cancelRequested: false,
    };
    progressHandle = createAdditiveDeltaProgressPane(currentProgressVm);
    progressSlot.replaceChildren(progressHandle.element);
    setState("running", { deltaId: jobId, counts: undefined });

    if (sseHandle) sseHandle.close();
    sseHandle = subscribeJobEvents(
      jobId,
      {
        onSnapshot: (ev) => renderSseSnapshot(ev),
        onStatusChange: (status) => renderSseStatus(status),
        onTerminal: (ev) => renderTerminal(ev),
      },
      opts.sseOptions ?? {},
    );
  }

  function renderSseStatus(status: AdditiveDeltaSseStatus): void {
    if (!progressHandle || !currentProgressVm) return;
    // Patch ONE field. Don't read stale dataset values.
    currentProgressVm = { ...currentProgressVm, sseStatus: status };
    progressHandle.update(currentProgressVm);
  }

  function renderSseSnapshot(ev: AdditiveDeltaSseEvent): void {
    if (!progressHandle) return;
    currentProgressVm = {
      jobId: ev.jobId,
      stage: ev.stage as AdditiveDeltaStage,
      progressPct: ev.progressPct,
      lastHeartbeatAt: ev.lastHeartbeatAt ?? null,
      sseStatus: "connected",
      cancelRequested: ev.cancelRequested,
    };
    progressHandle.update(currentProgressVm);
  }

  function renderTerminal(ev: AdditiveDeltaSseEvent): void {
    if (!isTerminalStage(ev.stage)) return;
    progressSlot.replaceChildren();
    if (progressHandle) {
      progressHandle.destroy();
      progressHandle = null;
    }
    activeJobId = null;
    cancelling = false;
    inFlight = null;
    currentProgressVm = null;
    const vm: AdditiveDeltaTerminalViewModel = {
      stage: ev.stage,
      deltaId: (ev.reportJson?.delta_id as string) ?? ev.jobId,
      report: (ev.reportJson as AdditiveDeltaTerminalViewModel["report"]) ?? null,
      errorClass: ev.errorClass,
      errorMessage: ev.errorMessage,
    };
    terminalSlot.replaceChildren(createAdditiveDeltaTerminalBanner(vm));
    store.clear();
    setState("terminal");
  }

  // ── mount-time reattach ──────────────────────────────────────

  async function mount(): Promise<void> {
    setState("idle");
    try {
      let live: LiveResponse;
      try {
        live = await getJson<LiveResponse>(
          `/api/ingest/additive/live?target=${encodeURIComponent(target)}`,
        );
      } catch {
        live = { ok: false, target, job_id: null, job: null };
      }
      const localJobId = store.get();
      const resolved = reconcileReattachSource({
        serverLiveJobId: live.job_id,
        localJobId,
        store,
      });
      if (!resolved) return;
      // If server-live → bind directly. If only local → probe /status first.
      if (live.job_id === resolved) {
        attachToJob(resolved);
        return;
      }
      let status: StatusResponse;
      try {
        status = await getJson<StatusResponse>(
          `/api/ingest/additive/status?job_id=${encodeURIComponent(resolved)}`,
        );
      } catch {
        store.clear();
        return;
      }
      if (!status.job) {
        store.clear();
        return;
      }
      if (isTerminalStage(status.job.stage)) {
        renderTerminal({
          jobId: status.job.job_id,
          stage: status.job.stage,
          progressPct: status.job.progress_pct,
          lastHeartbeatAt: status.job.last_heartbeat_at,
          cancelRequested: status.job.cancel_requested,
          reportJson: status.job.report_json,
          errorClass: status.job.error_class,
          errorMessage: status.job.error_message,
        });
      } else {
        attachToJob(resolved);
      }
    } catch {
      /* silent — mount failure leaves panel in Idle */
    }
  }

  void mount();

  function destroy(): void {
    if (sseHandle) sseHandle.close();
    root.replaceChildren();
  }

  return { destroy };
}
