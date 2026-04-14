import { getJson, postJson } from "@/shared/api/client";
import type { ReindexStatusPayload, ReindexOperation, ReindexStage } from "./opsTypes";
import { classifyLiveness, buildProgressNode } from "./opsTypes";

export interface CreateOpsReindexControllerOptions {
  dom: { container: HTMLElement };
  setFlash: (msg: string, tone: "success" | "error") => void;
  navigateToEmbeddings: () => void;
}

function esc(value: unknown): string {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function fmtNum(n: number | undefined | null): string {
  return (n ?? 0).toLocaleString("es-CO");
}

function fmtSeconds(seconds: number | null | undefined): string {
  if (seconds == null || seconds <= 0) return "-";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

function renderStages(stages: ReindexStage[]): string {
  if (!stages.length) return "";
  let html = '<ol class="reindex-stage-list">';
  for (const s of stages) {
    const icon = s.state === "completed" ? "ops-dot-ok" : s.state === "active" ? "ops-dot-active" : s.state === "failed" ? "ops-dot-error" : "ops-dot-pending";
    const label = s.state === "active" ? `<strong>${esc(s.label)}</strong>` : esc(s.label);
    html += `<li class="reindex-stage-item reindex-stage-${s.state}"><span class="ops-dot ${icon}">●</span> ${label}</li>`;
  }
  html += "</ol>";
  return html;
}

export function createOpsReindexController({
  dom,
  setFlash,
  navigateToEmbeddings,
}: CreateOpsReindexControllerOptions) {
  const { container } = dom;
  let _lastStatus: ReindexStatusPayload | null = null;
  let _launchingAction: "" | "start" | "stop" = "";

  function _render(): void {
    const s = _lastStatus;
    if (!s) {
      container.innerHTML = '<p class="ops-text-muted">Cargando estado de re-index...</p>';
      return;
    }

    const op = s.current_operation || s.last_operation;
    const isRunning = s.current_operation?.status === "running";
    const isIdle = !s.current_operation;

    let html = "";

    // -- Status header --
    const statusLabel = isRunning ? "En ejecución" : isIdle ? "Inactivo" : (op?.status ?? "—");
    const statusTone = isRunning ? "tone-yellow" : op?.status === "completed" ? "tone-green" : op?.status === "failed" ? "tone-red" : "";
    html += `<div class="reindex-status-row">
      <span class="corpus-status-chip ${statusTone}">${esc(statusLabel)}</span>
      <span class="emb-target-badge">WIP</span>
      ${isRunning ? `<span class="emb-heartbeat ${classifyLiveness(op?.heartbeat_at, op?.updated_at)}">${classifyLiveness(op?.heartbeat_at, op?.updated_at)}</span>` : ""}
    </div>`;

    // -- Controls --
    html += '<div class="reindex-controls">';
    if (isIdle) {
      html += `<button class="corpus-btn corpus-btn-promote" id="reindex-start-btn" ${_launchingAction ? "disabled" : ""}>Iniciar re-index</button>`;
    }
    if (isRunning && op) {
      html += `<button class="corpus-btn corpus-btn-rollback" id="reindex-stop-btn" ${_launchingAction ? "disabled" : ""}>Detener</button>`;
    }
    html += "</div>";

    // -- Phase stepper --
    if (op?.stages?.length) {
      html += renderStages(op.stages);
    }

    // -- Progress stats --
    if (op?.progress) {
      const p = op.progress as Record<string, unknown>;
      const items: string[] = [];
      if (p.documents_processed != null) items.push(`Documentos: ${fmtNum(p.documents_processed as number)} / ${fmtNum(p.documents_total as number)}`);
      if (p.documents_indexed != null) items.push(`Documentos indexados: ${fmtNum(p.documents_indexed as number)}`);
      if (p.elapsed_seconds != null) items.push(`Tiempo: ${fmtSeconds(p.elapsed_seconds as number)}`);
      if (items.length) {
        html += `<div class="reindex-progress-stats">${items.map(i => `<span>${esc(i)}</span>`).join("")}</div>`;
      }
    }

    // -- Quality report --
    if (op?.quality_report) {
      const qr = op.quality_report;
      html += '<div class="reindex-quality-report">';
      html += "<h3>Reporte de calidad</h3>";
      html += `<div class="emb-stats-grid">
        <div class="emb-stat"><span class="emb-stat-value">${fmtNum(qr.documents_indexed)}</span><span class="emb-stat-label">Documentos</span></div>
        <div class="emb-stat"><span class="emb-stat-value">${fmtNum(qr.chunks_generated)}</span><span class="emb-stat-label">Chunks</span></div>
        <div class="emb-stat"><span class="emb-stat-value">${qr.blocking_issues ?? 0}</span><span class="emb-stat-label">Blocking issues</span></div>
      </div>`;
      if (qr.knowledge_class_counts) {
        html += '<div class="reindex-kc-breakdown"><h4>Knowledge classes</h4><dl class="reindex-kc-dl">';
        for (const [kc, count] of Object.entries(qr.knowledge_class_counts)) {
          html += `<dt>${esc(kc)}</dt><dd>${fmtNum(count as number)}</dd>`;
        }
        html += "</dl></div>";
      }
      html += "</div>";

      // "Embed ahora" prompt
      html += `<div class="reindex-embed-prompt">
        <p>Re-index completado. Para aplicar los nuevos summaries a los embeddings:</p>
        <button class="corpus-btn corpus-btn-promote" id="reindex-embed-now-btn">Embed ahora</button>
      </div>`;
    }

    // -- Checks --
    if (op?.checks?.length) {
      html += '<div class="emb-checks">';
      for (const c of op.checks) {
        const icon = c.ok ? '<span class="ops-dot ops-dot-ok">●</span>' : '<span class="ops-dot ops-dot-error">●</span>';
        html += `<div class="emb-check">${icon} <strong>${esc(c.label)}</strong>: ${esc(c.detail)}</div>`;
      }
      html += "</div>";
    }

    // -- Log tail --
    if (op?.log_tail) {
      html += `<details class="emb-log-accordion"><summary>Log</summary><pre class="emb-log-tail">${esc(op.log_tail)}</pre></details>`;
    }

    // -- Error --
    if (op?.error) {
      html += `<p class="emb-error">${esc(op.error)}</p>`;
    }

    container.innerHTML = html;
  }

  function bindEvents(): void {
    container.addEventListener("click", (e) => {
      const target = e.target as HTMLElement;
      if (target.id === "reindex-start-btn") void _handleStart();
      if (target.id === "reindex-stop-btn") void _handleStop();
      if (target.id === "reindex-embed-now-btn") navigateToEmbeddings();
    });
  }

  async function _handleStart(): Promise<void> {
    _launchingAction = "start";
    _render();
    try {
      await postJson("/api/ops/reindex/start", { mode: "from_source" });
      setFlash("Re-index iniciado", "success");
    } catch (err) {
      setFlash(String(err), "error");
    }
    _launchingAction = "";
    await refresh();
  }

  async function _handleStop(): Promise<void> {
    const jobId = _lastStatus?.current_operation?.job_id;
    if (!jobId) return;
    _launchingAction = "stop";
    _render();
    try {
      await postJson("/api/ops/reindex/stop", { job_id: jobId });
      setFlash("Re-index detenido", "success");
    } catch (err) {
      setFlash(String(err), "error");
    }
    _launchingAction = "";
    await refresh();
  }

  async function refresh(): Promise<void> {
    try {
      const data = await getJson<ReindexStatusPayload>("/api/ops/reindex-status");
      _lastStatus = data;
    } catch {
      // Keep last known state
    }
    _render();
  }

  return { bindEvents, refresh };
}
