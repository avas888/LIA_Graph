/**
 * Corpus health dashboard (organism, Fase D).
 *
 * Persistent visual summary of the live corpus state so the operator can
 * answer "can I ingest into this right now" without running anything.
 * Auto-refreshes on mount; manual refresh via the button.
 *
 * Read-only — never mutates anything. Mounts above the existing
 * corpusOverview to give a faster "is this thing healthy" verdict.
 */

import { createButton } from "@/shared/ui/atoms/button";
import { getJson } from "@/shared/api/client";
import {
  createCorpusHealthMetric,
  type CorpusHealthMetricViewModel,
} from "@/shared/ui/molecules/corpusHealthMetric";

export interface CorpusHealthSnapshot {
  generation: {
    id: string | null;
    activated_at: string | null;
    documents: number;
    chunks: number;
    knowledge_class_counts: Record<string, number>;
  };
  parity: {
    ok: boolean | null;
    supabase_docs?: number;
    falkor_docs?: number;
    supabase_chunks?: number;
    falkor_articles?: number;
    supabase_edges?: number;
    falkor_edges?: number;
    mismatches: Array<{ field: string; supabase_value: number; falkor_value: number; delta: number }>;
  };
  embeddings: {
    pending_chunks: number | null;
    pct_complete: number | null;
  };
  last_delta: {
    job_id: string;
    delta_id: string;
    completed_at: string | null;
    started_at: string | null;
    target: string;
    documents_added: number;
    documents_modified: number;
    documents_retired: number;
    chunks_written: number;
  } | null;
  checked_at_utc: string;
}

export interface CorpusHealthCardHandle {
  element: HTMLElement;
  /** Refetch from /api/ingest/corpus_health and re-render. */
  refresh: () => Promise<void>;
  destroy: () => void;
}

function relativeBogota(iso: string | null): string {
  if (!iso) return "—";
  const ts = Date.parse(iso);
  if (Number.isNaN(ts)) return "—";
  const diffSec = Math.max(0, Math.floor((Date.now() - ts) / 1000));
  if (diffSec < 60) return `hace ${diffSec}s`;
  if (diffSec < 3600) return `hace ${Math.floor(diffSec / 60)} min`;
  if (diffSec < 86400) return `hace ${Math.floor(diffSec / 3600)} h`;
  return `hace ${Math.floor(diffSec / 86400)} días`;
}

function generationCard(snap: CorpusHealthSnapshot): CorpusHealthMetricViewModel {
  const id = snap.generation.id ?? "(sin generación activa)";
  const docs = snap.generation.documents.toLocaleString("es-CO");
  const chunks = snap.generation.chunks.toLocaleString("es-CO");
  const activated = snap.generation.activated_at
    ? `activada ${relativeBogota(snap.generation.activated_at)}`
    : "sin activar";
  return {
    title: "Generación activa",
    primary: id,
    secondary: `${docs} docs · ${chunks} chunks · ${activated}`,
    tone: snap.generation.id ? "ok" : "warning",
  };
}

function parityCard(snap: CorpusHealthSnapshot): CorpusHealthMetricViewModel {
  const p = snap.parity;
  if (p.ok === null) {
    return {
      title: "Parity Supabase ↔ Falkor",
      primary: "—",
      secondary: "Probe no disponible (Falkor sin configurar)",
      tone: "neutral",
    };
  }
  if (!p.ok) {
    const fields = p.mismatches.map((m) => `${m.field} (Δ${m.delta})`).join(", ");
    return {
      title: "Parity Supabase ↔ Falkor",
      primary: "Desfasada",
      secondary: fields || "mismatches sin nombre",
      tone: "danger",
    };
  }
  return {
    title: "Parity Supabase ↔ Falkor",
    primary: "Alineada ✓",
    secondary: `${p.supabase_docs ?? 0} docs · ${p.supabase_edges ?? 0} aristas`,
    tone: "ok",
  };
}

function embeddingsCard(snap: CorpusHealthSnapshot): CorpusHealthMetricViewModel {
  const e = snap.embeddings;
  if (e.pending_chunks === null) {
    return {
      title: "Embeddings",
      primary: "—",
      secondary: "Sin métrica",
      tone: "neutral",
    };
  }
  if (e.pending_chunks === 0) {
    return {
      title: "Embeddings",
      primary: "Completos ✓",
      secondary: e.pct_complete !== null ? `${e.pct_complete}% al día` : "",
      tone: "ok",
    };
  }
  const pct = e.pct_complete !== null ? `${e.pct_complete}%` : "";
  return {
    title: "Embeddings",
    primary: `${e.pending_chunks.toLocaleString("es-CO")} chunks pendientes`,
    secondary: `${pct} al día — corre \`make phase2-embed-backfill\``,
    tone: "warning",
  };
}

function lastDeltaCard(snap: CorpusHealthSnapshot): CorpusHealthMetricViewModel {
  const d = snap.last_delta;
  if (!d) {
    return {
      title: "Última ingesta",
      primary: "Sin runs registrados",
      secondary: "El historial de delta_jobs está vacío",
      tone: "neutral",
    };
  }
  const when = relativeBogota(d.completed_at);
  return {
    title: "Última ingesta",
    primary: when,
    secondary:
      `+${d.documents_added} / ~${d.documents_modified} / -${d.documents_retired} docs · ` +
      `${d.chunks_written.toLocaleString("es-CO")} chunks (${d.target})`,
    tone: "ok",
  };
}

// Metric card rendering moved to `corpusHealthMetric` molecule —
// `createCorpusHealthMetric()` is the single source for the title/primary/
// secondary/tone shape. Atomic-design boundary: organism composes
// molecules, never re-implements them.

export interface CorpusHealthCardOptions {
  /** Override the fetch path (tests). */
  fetchPath?: string;
  /** Auto-refresh interval in ms; 0 = manual only. Default 60_000. */
  autoRefreshMs?: number;
  /** Inject a fake getJson for tests. */
  getJsonImpl?: <T>(url: string) => Promise<T>;
}

export function createCorpusHealthCard(
  opts: CorpusHealthCardOptions = {},
): CorpusHealthCardHandle {
  const fetchPath = opts.fetchPath ?? "/api/ingest/corpus_health";
  const autoRefreshMs = opts.autoRefreshMs ?? 60_000;
  const fetchImpl = opts.getJsonImpl ?? getJson;

  const root = document.createElement("section");
  root.className = "lia-corpus-health";
  root.setAttribute("data-lia-component", "corpus-health-card");

  const header = document.createElement("header");
  header.className = "lia-corpus-health__header";
  const title = document.createElement("h3");
  title.className = "lia-corpus-health__title";
  title.textContent = "Salud del corpus";
  const checkedAt = document.createElement("span");
  checkedAt.className = "lia-corpus-health__checked-at";
  checkedAt.textContent = "verificando…";
  const refreshBtn = createButton({
    label: "Refrescar",
    tone: "ghost",
    onClick: () => void refresh(),
  });
  header.append(title, checkedAt, refreshBtn);
  root.appendChild(header);

  const grid = document.createElement("div");
  grid.className = "lia-corpus-health__grid";
  root.appendChild(grid);

  const emptyState = document.createElement("p");
  emptyState.className = "lia-corpus-health__empty";
  emptyState.textContent = "Cargando…";
  grid.appendChild(emptyState);

  let intervalHandle: ReturnType<typeof setInterval> | null = null;
  let destroyed = false;

  function render(snap: CorpusHealthSnapshot): void {
    grid.replaceChildren();
    const cards = [
      generationCard(snap),
      parityCard(snap),
      embeddingsCard(snap),
      lastDeltaCard(snap),
    ];
    for (const spec of cards) grid.appendChild(createCorpusHealthMetric(spec));
    checkedAt.textContent = `verificado ${relativeBogota(snap.checked_at_utc)}`;
  }

  function renderError(message: string): void {
    grid.replaceChildren();
    const err = document.createElement("p");
    err.className = "lia-corpus-health__empty lia-corpus-health__empty--error";
    err.textContent = `No se pudo cargar la salud del corpus: ${message}`;
    grid.appendChild(err);
    checkedAt.textContent = "error";
  }

  async function refresh(): Promise<void> {
    if (destroyed) return;
    refreshBtn.disabled = true;
    try {
      const data = await fetchImpl<{ ok: boolean } & CorpusHealthSnapshot>(
        fetchPath,
      );
      if (destroyed) return;
      if (!data || !("ok" in data) || !data.ok) {
        renderError("respuesta sin ok=true");
        return;
      }
      render(data);
    } catch (err) {
      if (destroyed) return;
      renderError(err instanceof Error ? err.message : String(err));
    } finally {
      refreshBtn.disabled = false;
    }
  }

  void refresh();
  if (autoRefreshMs > 0) {
    intervalHandle = setInterval(() => void refresh(), autoRefreshMs);
  }

  return {
    element: root,
    refresh,
    destroy(): void {
      destroyed = true;
      if (intervalHandle) {
        clearInterval(intervalHandle);
        intervalHandle = null;
      }
    },
  };
}
