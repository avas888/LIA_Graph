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
    const errMsg =
      data && typeof data === "object" && "error" in (data as Record<string, unknown>)
        ? String((data as { error?: string }).error || response.statusText)
        : response.statusText;
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
import type { GenerationRowViewModel } from "@/shared/ui/molecules/generationRow";
import type { RunStatus } from "@/shared/ui/molecules/runStatusBadge";

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
}

export function createIngestController(rootElement: HTMLElement): IngestController {
  const overviewSlot = rootElement.querySelector<HTMLElement>("[data-slot=corpus-overview]");
  const triggerSlot = rootElement.querySelector<HTMLElement>("[data-slot=run-trigger]");
  const generationsSlot = rootElement.querySelector<HTMLElement>("[data-slot=generations-list]");

  if (!overviewSlot || !triggerSlot || !generationsSlot) {
    // Defensive — if slots are missing, surface clearly without crashing the page.
    rootElement.textContent = "Sesiones: missing render slots.";
    return { refresh: async () => undefined, destroy: () => undefined };
  }

  const state: InternalState = {
    activeJobId: null,
    lastRunStatus: null,
    pollHandle: null,
  };

  function _renderTrigger(): void {
    triggerSlot!.replaceChildren(
      createRunTriggerCard({
        activeJobId: state.activeJobId,
        lastRunStatus: state.lastRunStatus,
        disabled: state.activeJobId !== null,
        onTrigger: ({ suinScope, supabaseTarget }) => {
          void _startRun({ suinScope, supabaseTarget });
        },
      }),
    );
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

  async function _startRun(params: {
    suinScope: string;
    supabaseTarget: "wip" | "production";
  }): Promise<void> {
    state.lastRunStatus = "queued";
    _renderTrigger();
    try {
      const res = await postJsonOrThrow<IngestRunResponse>("/api/ingest/run", {
        suin_scope: params.suinScope,
        supabase_target: params.supabaseTarget,
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
    state.pollHandle = window.setInterval(() => {
      if (!state.activeJobId) {
        _stopPolling();
        return;
      }
      void _pollOnce(state.activeJobId);
    }, 4000);
  }

  function _stopPolling(): void {
    if (state.pollHandle !== null) {
      window.clearInterval(state.pollHandle);
      state.pollHandle = null;
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
  void Promise.all([_renderOverview(), _renderGenerations()]);

  return {
    async refresh(): Promise<void> {
      await Promise.all([_renderOverview(), _renderGenerations()]);
    },
    destroy(): void {
      _stopPolling();
    },
  };
}
