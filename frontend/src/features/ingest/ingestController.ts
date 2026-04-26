/**
 * Sesiones controller — Lia_Graph native ingest surface.
 *
 * Wires the four /api/ingest endpoints to the atomic-design organisms.
 * The job-status poll piggybacks on the existing /api/jobs/{id} surface
 * already used by Promoción.
 *
 * Source-of-truth for the orchestration path: docs/guide/orchestration.md
 * Lane 0 (Raw → snapshot → ingest → WIP Supabase + local Falkor → Promoción
 * → Cloud Supabase + Cloud Falkor).
 */

import { ApiError, getJson, postJson } from "@/shared/api/client";

async function postJsonOrThrow<T, B = unknown>(url: string, body: B): Promise<T> {
  const { response, data } = await postJson<T, B>(url, body);
  if (!response.ok) {
    // Many handlers emit `{error: <code>, details: <human copy>}` — surface
    // both so the UI message is actionable ("batch_too_large — Max 500
    // archivos por lote.") instead of just a code.
    let errMsg = response.statusText;
    if (data && typeof data === "object") {
      const d = data as Record<string, unknown>;
      const code = typeof d.error === "string" ? d.error : "";
      const details = typeof d.details === "string" ? d.details : "";
      if (code && details) errMsg = `${code} — ${details}`;
      else if (code) errMsg = code;
      else if (details) errMsg = details;
    }
    throw new ApiError(errMsg, response.status, data);
  }
  if (!data) throw new ApiError("Empty response", response.status, null);
  return data;
}
import {
  createCorpusOverview,
  type CorpusOverviewViewModel,
} from "@/shared/ui/organisms/corpusOverview";
import {
  createGenerationsList,
} from "@/shared/ui/organisms/generationsList";
import { createRunTriggerCard } from "@/shared/ui/organisms/runTriggerCard";
import { createAdditiveDeltaCard } from "@/shared/ui/organisms/additiveDeltaCard";
import {
  createIntakeDropZone,
  type IntakeDropZoneFile,
  type IntakeDropZoneResponse,
} from "@/shared/ui/organisms/intakeDropZone";
import {
  createRunProgressTimeline,
  type ProgressResponse,
  type RunProgressTimelineHandle,
} from "@/shared/ui/organisms/runProgressTimeline";
import {
  createRunLogConsole,
  type RunLogConsoleHandle,
} from "@/shared/ui/organisms/runLogConsole";
import type { GenerationRowViewModel } from "@/shared/ui/molecules/generationRow";
import type { RunStatus } from "@/shared/ui/molecules/runStatusBadge";
import {
  bindAdditiveDelta,
  type AdditiveDeltaControllerHandle,
} from "@/features/ingest/additiveDeltaController";
import { createSegmentedControl } from "@/shared/ui/atoms/segmentedControl";
import { getToastController } from "@/shared/ui/toasts";
import type { I18nRuntime } from "@/shared/i18n";

// ── API contracts ────────────────────────────────────────────

interface IngestStateResponse {
  ok: boolean;
  corpus: {
    active_generation_id: string;
    activated_at: string;
    generated_at: string;
    documents: number;
    chunks: number;
    knowledge_class_counts: Record<string, number>;
    countries: string[];
  };
  audit: {
    scanned: number;
    include_corpus: number;
    exclude_internal: number;
    revision_candidates: number;
    pending_revisions: number;
    scanned_at: string;
    taxonomy_version: string;
  };
  graph: { ok: boolean; nodes: number; edges: number; validated_at: string };
  inventory: Record<string, number>;
}

interface GenerationRow {
  generation_id: string;
  generated_at: string;
  activated_at: string;
  documents: number;
  chunks: number;
  knowledge_class_counts: Record<string, number>;
  is_active: boolean;
}

interface IngestGenerationsResponse {
  ok: boolean;
  generations: GenerationRow[];
}

interface IngestRunResponse {
  ok: boolean;
  job_id: string;
}

interface IngestIntakeResponseFile {
  filename: string;
  mime?: string | null;
  bytes?: number | null;
  detected_topic?: string | null;
  topic_label?: string | null;
  combined_confidence?: number | null;
  requires_review?: boolean;
  coercion_method?: string | null;
}

interface IngestIntakeResponse {
  ok: boolean;
  batch_id: string;
  summary: { received: number; placed: number; deduped: number; rejected: number };
  files: IngestIntakeResponseFile[];
}

interface IngestProgressResponse {
  ok: boolean;
  job_id: string;
  status: string;
  stages?: ProgressResponse["stages"];
}

interface IngestLogTailResponse {
  ok: boolean;
  lines: string[];
  next_cursor: number;
  total_lines: number;
  log_relative_path?: string;
}

interface JobStatusResponse {
  ok?: boolean;
  job?: {
    job_id: string;
    status: "queued" | "running" | "completed" | "failed";
    result_payload?: { exit_code?: number; log_relative_path?: string };
    error?: string;
  };
}

// ── Controller surface ───────────────────────────────────────

export interface IngestController {
  refresh: () => Promise<void>;
  destroy: () => void;
}

interface InternalState {
  activeJobId: string | null;
  lastRunStatus: RunStatus | null;
  pollHandle: number | null;
  logCursor: number;
  lastBatchId: string | null;
  autoEmbed: boolean;
  autoPromote: boolean;
  supabaseTarget: "wip" | "production";
  suinScope: string;
}

export interface CreateIngestControllerOptions {
  /** I18n runtime used for the shared toast controller. Optional so
   * legacy call sites (and tests) that instantiate the controller without
   * an i18n runtime still work — the drop zone then falls back to
   * native ``window.confirm()`` for destructive prompts. */
  i18n?: I18nRuntime;
}

export function createIngestController(
  rootElement: HTMLElement,
  options: CreateIngestControllerOptions = {},
): IngestController {
  const overviewSlot = rootElement.querySelector<HTMLElement>("[data-slot=corpus-overview]");
  const triggerSlot = rootElement.querySelector<HTMLElement>("[data-slot=run-trigger]");
  const generationsSlot = rootElement.querySelector<HTMLElement>("[data-slot=generations-list]");
  // Phase 5 slots — optional so the legacy page still works if they are missing.
  const intakeSlot = rootElement.querySelector<HTMLElement>("[data-slot=intake-zone]");
  const timelineSlot = rootElement.querySelector<HTMLElement>("[data-slot=progress-timeline]");
  const logSlot = rootElement.querySelector<HTMLElement>("[data-slot=log-console]");

  if (!overviewSlot || !triggerSlot || !generationsSlot) {
    // Defensive — if slots are missing, surface clearly without crashing the page.
    rootElement.textContent = "Sesiones: missing render slots.";
    return { refresh: async () => undefined, destroy: () => undefined };
  }

  const state: InternalState = {
    activeJobId: null,
    lastRunStatus: null,
    pollHandle: null,
    logCursor: 0,
    lastBatchId: null,
    autoEmbed: true,
    autoPromote: false,
    supabaseTarget: "wip",
    suinScope: "",
  };

  let timelineHandle: RunProgressTimelineHandle | null = null;
  let logHandle: RunLogConsoleHandle | null = null;

  function _renderTrigger(): void {
    triggerSlot!.replaceChildren(
      createRunTriggerCard({
        activeJobId: state.activeJobId,
        lastRunStatus: state.lastRunStatus,
        disabled: state.activeJobId !== null,
        onTrigger: ({ suinScope, supabaseTarget, autoEmbed, autoPromote }) => {
          state.autoEmbed = autoEmbed;
          state.autoPromote = autoPromote;
          state.supabaseTarget = supabaseTarget;
          state.suinScope = suinScope;
          void _startRun({ suinScope, supabaseTarget, autoEmbed, autoPromote, batchId: null });
        },
      }),
    );
  }

  // Build a toast-backed destructive-confirm bridge once, so every
  // re-render of the intake zone reuses the same bound controller. When
  // no i18n runtime was injected (tests / legacy paths) leave it
  // undefined → the drop zone falls back to native window.confirm.
  const toastConfirmDestructive = options.i18n
    ? (opts: {
        title: string;
        message: string;
        confirmLabel: string;
        cancelLabel: string;
      }): Promise<boolean> =>
        getToastController(options.i18n!).confirm({
          title: opts.title,
          message: opts.message,
          tone: "caution",
          confirmLabel: opts.confirmLabel,
          cancelLabel: opts.cancelLabel,
        })
    : undefined;

  function _renderIntakeZone(): void {
    if (!intakeSlot) return;
    intakeSlot.replaceChildren(
      createIntakeDropZone({
        onIntake: (files) => _handleIntakeDrop(files),
        // After AUTOGENERAR placed the files on disk, the green CTA is
        // NOT "run a pipeline" — it's "go to Paso 2 and pick delta vs
        // full". The old auto-trigger of /api/ingest/run was ambiguous
        // with the Delta aditivo workflow; the operator now makes the
        // choice explicitly in the next section.
        onApprove: () => _scrollToProcessingStep(),
        confirmDestructive: toastConfirmDestructive,
      }),
    );
  }

  function _scrollToProcessingStep(): void {
    const target =
      rootElement.querySelector<HTMLElement>("[data-slot=flow-toggle]")?.closest<HTMLElement>("section") ??
      rootElement.querySelector<HTMLElement>("[data-slot=flow-toggle]") ??
      null;
    if (!target) return;
    target.scrollIntoView({ behavior: "smooth", block: "start" });
    target.classList.add("is-highlighted");
    window.setTimeout(() => target.classList.remove("is-highlighted"), 2400);
  }

  function _renderTimeline(): void {
    if (!timelineSlot) return;
    timelineHandle = createRunProgressTimeline();
    timelineSlot.replaceChildren(timelineHandle.element);
  }

  function _renderLogConsole(): void {
    if (!logSlot) return;
    logHandle = createRunLogConsole();
    logSlot.replaceChildren(logHandle.element);
  }

  async function _renderOverview(): Promise<void> {
    overviewSlot!.replaceChildren(_buildLoadingSkeleton("overview"));
    try {
      const data = await getJson<IngestStateResponse>("/api/ingest/state");
      const vm: CorpusOverviewViewModel = {
        documents: data.corpus.documents,
        chunks: data.corpus.chunks,
        graphNodes: data.graph.nodes,
        graphEdges: data.graph.edges,
        graphOk: data.graph.ok,
        auditScanned: data.audit.scanned,
        auditIncluded: data.audit.include_corpus,
        auditExcluded: data.audit.exclude_internal,
        auditPendingRevisions: data.audit.pending_revisions,
        activeGenerationId: data.corpus.active_generation_id,
        activatedAt: data.corpus.activated_at,
      };
      overviewSlot!.replaceChildren(createCorpusOverview(vm));
    } catch (err) {
      overviewSlot!.replaceChildren(_buildErrorBlock("No se pudo cargar el estado del corpus.", err));
    }
  }

  async function _renderGenerations(): Promise<void> {
    generationsSlot!.replaceChildren(_buildLoadingSkeleton("generations"));
    try {
      const data = await getJson<IngestGenerationsResponse>("/api/ingest/generations?limit=20");
      const rows: GenerationRowViewModel[] = (data.generations || []).map((g) => {
        const classes = g.knowledge_class_counts || {};
        const topClassEntry = Object.entries(classes).sort((a, b) => b[1] - a[1])[0];
        return {
          generationId: g.generation_id,
          status: g.is_active ? "active" : "superseded",
          generatedAt: g.generated_at,
          documents: Number(g.documents) || 0,
          chunks: Number(g.chunks) || 0,
          topClass: topClassEntry?.[0],
          topClassCount: topClassEntry?.[1],
        };
      });
      generationsSlot!.replaceChildren(createGenerationsList({ rows }));
    } catch (err) {
      generationsSlot!.replaceChildren(
        createGenerationsList({
          rows: [],
          errorMessage: `No se pudieron cargar las generaciones: ${_errorMessage(err)}`,
        }),
      );
    }
  }

  async function _handleIntakeDrop(
    files: IntakeDropZoneFile[],
  ): Promise<IntakeDropZoneResponse> {
    const encoded = await Promise.all(
      files.map(async (entry) => {
        const content_base64 = await _fileToBase64(entry.file);
        return {
          filename: entry.filename,
          content_base64,
          relative_path: entry.relativePath || entry.filename,
        };
      }),
    );
    const payload = {
      batch_id: null as string | null,
      files: encoded,
      options: { mirror_to_dropbox: false, dropbox_root: null as string | null },
    };
    const res = await postJsonOrThrow<IngestIntakeResponse>("/api/ingest/intake", payload);
    state.lastBatchId = res.batch_id;
    return res;
  }

  async function _fileToBase64(file: File): Promise<string> {
    // Prefer FileReader.readAsDataURL — most universally supported in
    // both real browsers and jsdom. Fall back to arrayBuffer + btoa for
    // environments that provide `Blob.arrayBuffer` but not FileReader.
    const g = globalThis as {
      FileReader?: typeof FileReader;
      btoa?: (s: string) => string;
    };
    if (typeof g.FileReader === "function") {
      const dataUrl = await new Promise<string>((resolve, reject) => {
        const reader = new g.FileReader!();
        reader.onerror = () => reject(reader.error || new Error("file read failed"));
        reader.onload = () => resolve(String(reader.result || ""));
        reader.readAsDataURL(file);
      });
      const comma = dataUrl.indexOf(",");
      return comma >= 0 ? dataUrl.slice(comma + 1) : "";
    }
    if (typeof (file as File & { arrayBuffer?: () => Promise<ArrayBuffer> }).arrayBuffer === "function") {
      const buffer = await (file as File & { arrayBuffer: () => Promise<ArrayBuffer> }).arrayBuffer();
      return _arrayBufferToBase64(buffer);
    }
    return "";
  }

  async function _handleIntakeApprove(
    batchId: string,
    opts: {
      autoEmbed: boolean;
      autoPromote: boolean;
      supabaseTarget: "wip" | "production";
      suinScope: string;
    },
  ): Promise<void> {
    await _startRun({
      batchId,
      autoEmbed: opts.autoEmbed,
      autoPromote: opts.autoPromote,
      supabaseTarget: opts.supabaseTarget,
      suinScope: opts.suinScope,
    });
  }

  async function _startRun(params: {
    suinScope: string;
    supabaseTarget: "wip" | "production";
    autoEmbed: boolean;
    autoPromote: boolean;
    batchId: string | null;
  }): Promise<void> {
    state.lastRunStatus = "queued";
    state.logCursor = 0;
    if (logHandle) logHandle.clear();
    _renderTrigger();
    try {
      const res = await postJsonOrThrow<IngestRunResponse>("/api/ingest/run", {
        suin_scope: params.suinScope,
        supabase_target: params.supabaseTarget,
        auto_embed: params.autoEmbed,
        auto_promote: params.autoPromote,
        batch_id: params.batchId,
      });
      state.activeJobId = res.job_id;
      state.lastRunStatus = "running";
      _renderTrigger();
      _startPolling();
    } catch (err) {
      state.lastRunStatus = "failed";
      state.activeJobId = null;
      _renderTrigger();
      _toast(`No se pudo iniciar la ingesta: ${_errorMessage(err)}`);
    }
  }

  function _startPolling(): void {
    _stopPolling();
    // If the Phase 5 slots are wired, use the progress+log endpoints
    // (1.5s) so the timeline + log surface live updates. Otherwise,
    // fall back to the legacy /api/jobs/{id} poll (4s).
    const phaseFive = timelineSlot !== null || logSlot !== null;
    state.pollHandle = window.setInterval(() => {
      if (!state.activeJobId) {
        _stopPolling();
        return;
      }
      if (phaseFive) {
        void _pollProgress(state.activeJobId);
        void _pollLog(state.activeJobId);
      } else {
        void _pollOnce(state.activeJobId);
      }
    }, phaseFive ? 1500 : 4000);
  }

  function _stopPolling(): void {
    if (state.pollHandle !== null) {
      window.clearInterval(state.pollHandle);
      state.pollHandle = null;
    }
  }

  async function _pollProgress(jobId: string): Promise<void> {
    try {
      const res = await getJson<IngestProgressResponse>(
        `/api/ingest/job/${jobId}/progress`,
      );
      if (timelineHandle) timelineHandle.update(res as ProgressResponse);
      const status = res.status;
      if (status === "done" || status === "failed") {
        state.lastRunStatus = status === "done" ? "active" : "failed";
        state.activeJobId = null;
        _renderTrigger();
        _stopPolling();
        if (status === "done") {
          await Promise.all([_renderOverview(), _renderGenerations()]);
        }
      }
    } catch {
      // Transient — let the next tick retry.
    }
  }

  async function _pollLog(jobId: string): Promise<void> {
    try {
      const res = await getJson<IngestLogTailResponse>(
        `/api/ingest/job/${jobId}/log/tail?cursor=${state.logCursor}&limit=200`,
      );
      if (res.lines && res.lines.length > 0 && logHandle) {
        logHandle.appendLines(res.lines);
      }
      if (typeof res.next_cursor === "number") {
        state.logCursor = res.next_cursor;
      }
    } catch {
      // Transient — let the next tick retry.
    }
  }

  async function _pollOnce(jobId: string): Promise<void> {
    try {
      const res = await getJson<JobStatusResponse>(`/api/jobs/${jobId}`);
      const job = res.job;
      if (!job) return;
      if (job.status === "completed") {
        const ok = (job.result_payload?.exit_code ?? 1) === 0;
        state.lastRunStatus = ok ? "active" : "failed";
        state.activeJobId = null;
        _renderTrigger();
        _stopPolling();
        // Refresh state + generations after a successful run.
        if (ok) {
          await Promise.all([_renderOverview(), _renderGenerations()]);
        }
      } else if (job.status === "failed") {
        state.lastRunStatus = "failed";
        state.activeJobId = null;
        _renderTrigger();
        _stopPolling();
      }
    } catch {
      // Transient — let the next tick retry.
    }
  }

  function _arrayBufferToBase64(buffer: ArrayBuffer): string {
    const bytes = new Uint8Array(buffer);
    // Chunk to avoid blowing the call stack on very large files (btoa).
    const CHUNK = 0x8000;
    let binary = "";
    for (let i = 0; i < bytes.length; i += CHUNK) {
      const slice = bytes.subarray(i, Math.min(bytes.length, i + CHUNK));
      binary += String.fromCharCode.apply(null, Array.from(slice));
    }
    const g = globalThis as { btoa?: (s: string) => string };
    if (typeof g.btoa === "function") return g.btoa(binary);
    // Node fallback path (jsdom normally provides btoa, but guard anyway).
    const nodeBuffer = (globalThis as { Buffer?: { from: (s: string, enc: string) => { toString: (enc: string) => string } } }).Buffer;
    if (nodeBuffer) return nodeBuffer.from(binary, "binary").toString("base64");
    return "";
  }

  // Helpers
  function _buildLoadingSkeleton(kind: "overview" | "generations"): HTMLElement {
    const block = document.createElement("div");
    block.className = `lia-ingest-skeleton lia-ingest-skeleton--${kind}`;
    block.setAttribute("aria-hidden", "true");
    block.textContent = "Cargando…";
    return block;
  }

  function _buildErrorBlock(message: string, err: unknown): HTMLElement {
    const block = document.createElement("div");
    block.className = "lia-ingest-error";
    block.setAttribute("role", "alert");
    const head = document.createElement("strong");
    head.textContent = message;
    block.appendChild(head);
    const detail = document.createElement("p");
    detail.className = "lia-ingest-error__detail";
    detail.textContent = _errorMessage(err);
    block.appendChild(detail);
    return block;
  }

  function _errorMessage(err: unknown): string {
    if (err instanceof Error) return err.message;
    if (typeof err === "string") return err;
    return "Error desconocido";
  }

  function _toast(message: string): void {
    const el = document.createElement("div");
    el.className = "lia-ingest-toast";
    el.textContent = message;
    rootElement.prepend(el);
    window.setTimeout(() => el.remove(), 4000);
  }

  // Initial mount
  _renderTrigger();
  _renderIntakeZone();
  _renderTimeline();
  _renderLogConsole();
  void Promise.all([_renderOverview(), _renderGenerations()]);

  // Paso 2 flow toggle — swaps active card between Delta aditivo and
  // Ingesta completa. The non-selected card is greyed out via CSS targeting
  // [data-active-flow] on the section wrapper.
  const flowToggleSlot = rootElement.querySelector<HTMLElement>("[data-slot=flow-toggle]");
  const flowSection = flowToggleSlot?.closest<HTMLElement>("[data-active-flow]") ?? null;
  if (flowToggleSlot && flowSection) {
    const toggle = createSegmentedControl({
      ariaLabel: "Flujo de ingesta",
      value: "delta",
      options: [
        {
          value: "delta",
          label: "Delta aditivo",
          hint: "Rápido · solo lo que cambió",
        },
        {
          value: "full",
          label: "Ingesta completa",
          hint: "Lento · reconstruye todo",
        },
      ],
      onChange: (next) => {
        flowSection.setAttribute("data-active-flow", next);
      },
    });
    flowToggleSlot.replaceChildren(toggle.element);
  }

  // Additive-corpus-v1 sub-panel (Phase 8). Visual peer of `runTriggerCard`
  // — both cards are organisms so the two ingest flows render at the same
  // atomic level.
  let additiveDelta: AdditiveDeltaControllerHandle | null = null;
  const additiveSlot = rootElement.querySelector<HTMLElement>("[data-slot=additive-delta]");
  if (additiveSlot) {
    const { element, mount } = createAdditiveDeltaCard();
    additiveSlot.replaceChildren(element);
    additiveDelta = bindAdditiveDelta({
      rootElement: mount,
      target: "production",
      onError: (message) => _toast(message),
    });
  }

  return {
    async refresh(): Promise<void> {
      await Promise.all([_renderOverview(), _renderGenerations()]);
    },
    destroy(): void {
      _stopPolling();
      if (additiveDelta) {
        additiveDelta.destroy();
        additiveDelta = null;
      }
    },
  };
}
