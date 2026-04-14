import { getJson, postJson } from "@/shared/api/client";
import { palette } from "@/shared/ui/colors";
import type {
  CorpusOperationLaunchResult,
  CorpusOperationStage,
  CorpusOperationSummary,
  CorpusStatusPayload,
  CorpusTargetStatus,
  CorpusVerificationCheck,
  PromotionSummary,
  PromotionTargetSnapshot,
} from "./opsTypes";

export interface CorpusLifecycleDom {
  container: HTMLElement;
}

export interface CreateCorpusLifecycleControllerOptions {
  dom: CorpusLifecycleDom;
  setFlash: (msg: string, tone: "success" | "error") => void;
}

const FAST_POLL_INTERVAL_MS = 2_000;

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

function fmtDate(iso: string | undefined | null): string {
  if (!iso) return "-";
  try {
    const d = new Date(iso);
    return d.toLocaleDateString("es-CO", {
      day: "numeric",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
      timeZone: "America/Bogota",
    });
  } catch {
    return iso;
  }
}

function fmtRelative(iso: string | undefined | null): string {
  if (!iso) return "-";
  const ts = Date.parse(iso);
  if (Number.isNaN(ts)) return iso;
  const seconds = Math.max(0, Math.floor((Date.now() - ts) / 1000));
  if (seconds < 5) return "ahora";
  if (seconds < 60) return `hace ${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const rem = seconds % 60;
  if (minutes < 60) return `hace ${minutes}m ${rem}s`;
  const hours = Math.floor(minutes / 60);
  return `hace ${hours}h ${minutes % 60}m`;
}

function shortGen(id: string | null | undefined): string {
  if (!id) return "-";
  return id.length > 24 ? `${id.slice(0, 15)}…${id.slice(-8)}` : id;
}

function dot(ok: boolean | undefined): string {
  if (ok === undefined) return '<span class="ops-dot ops-dot-unknown">●</span>';
  return ok
    ? '<span class="ops-dot ops-dot-ok">●</span>'
    : '<span class="ops-dot ops-dot-error">●</span>';
}

function renderTargetCard(label: string, target: CorpusTargetStatus): string {
  if (!target.available) {
    return `
      <div class="corpus-card corpus-card-unavailable">
        <h4 class="corpus-card-title">${esc(label)}</h4>
        <p class="corpus-card-unavail">● no disponible</p>
        ${target.error ? `<p class="ops-subcopy">${esc(target.error)}</p>` : ""}
      </div>`;
  }

  const kc = target.knowledge_class_counts ?? {};
  return `
    <div class="corpus-card">
      <h4 class="corpus-card-title">${esc(label)}</h4>
      <div class="corpus-card-row"><span>Gen:</span> <code>${esc(shortGen(target.generation_id))}</code></div>
      <div class="corpus-card-row"><span>Documentos:</span> <strong>${fmtNum(target.documents)}</strong></div>
      <div class="corpus-card-row"><span>Chunks:</span> <strong>${fmtNum(target.chunks)}</strong></div>
      <div class="corpus-card-row"><span>Embeddings:</span> ${dot(target.embeddings_complete)} ${target.embeddings_complete ? "completos" : "incompletos"}</div>
      <div class="corpus-card-sep"></div>
      <div class="corpus-card-row corpus-card-row-sm"><span>normative_base:</span> ${fmtNum(kc.normative_base)}</div>
      <div class="corpus-card-row corpus-card-row-sm"><span>interpretative:</span> ${fmtNum(kc.interpretative_guidance)}</div>
      <div class="corpus-card-row corpus-card-row-sm"><span>practica_erp:</span> ${fmtNum(kc.practica_erp)}</div>
      <div class="corpus-card-sep"></div>
      <div class="corpus-card-row corpus-card-row-sm"><span>${label === "PRODUCTION" ? "Activado:" : "Actualizado:"}</span> ${esc(fmtDate(target.activated_at))}</div>
    </div>`;
}

function renderChecks(
  checks: CorpusVerificationCheck[] | undefined,
  options: { onlyFailures?: boolean } = {},
): string {
  const { onlyFailures = false } = options;
  const rows = (checks ?? []).filter((check) => (onlyFailures ? !check.ok : true));
  if (rows.length === 0) return "";
  return `
    <ul class="corpus-checks">
      ${rows
        .map(
          (check) => `
            <li class="corpus-check ${check.ok ? "is-ok" : "is-fail"}">
              <span class="corpus-check-dot"></span>
              <div>
                <strong>${esc(check.label)}</strong>
                <span>${esc(check.detail)}</span>
              </div>
            </li>`,
        )
        .join("")}
    </ul>`;
}

function renderStages(stages: CorpusOperationStage[] | undefined): string {
  const items = stages ?? [];
  if (items.length === 0) return "";
  return `
    <ol class="corpus-stage-list">
      ${items
        .map(
          (stage) => `
            <li class="corpus-stage-item state-${esc(stage.state)}">
              <span class="corpus-stage-dot"></span>
              <span>${esc(stage.label)}</span>
            </li>`,
        )
        .join("")}
    </ol>`;
}

function humanizePhase(value: string | null | undefined): string {
  const raw = String(value || "").trim();
  if (!raw) return "-";
  return raw.replaceAll("_", " ");
}

function modeLabel(operation: CorpusOperationSummary | null): string {
  if (!operation) return "Promote";
  if (operation.kind === "audit") return "Audit";
  if (operation.kind === "rollback") return "Rollback";
  if (operation.mode === "force_reset") return "Force reset";
  return "Promote";
}

function checkpointSummary(operation: CorpusOperationSummary | null): string {
  const checkpoint = operation?.last_checkpoint;
  if (!checkpoint?.phase) return "-";
  const cursor = checkpoint.cursor ?? 0;
  const total = checkpoint.total ?? 0;
  const pct = total > 0 ? ((cursor / total) * 100).toFixed(1) : "0";
  return `${humanizePhase(checkpoint.phase)} · ${fmtNum(cursor)} / ${fmtNum(total)} (${pct}%)`;
}

function progressPct(operation: CorpusOperationSummary | null): number {
  const cursor = operation?.last_checkpoint?.cursor ?? operation?.batch_cursor ?? 0;
  const total = operation?.last_checkpoint?.total ?? 0;
  if (total <= 0) return 0;
  return Math.min(100, Math.max(0, (cursor / total) * 100));
}

function heartbeatHealth(operation: CorpusOperationSummary | null): {
  label: string;
  className: string;
} {
  if (!operation?.heartbeat_at) return { label: "-", className: "" };
  const age = Math.max(0, (Date.now() - Date.parse(operation.heartbeat_at)) / 1000);
  if (age < 15) return { label: "Saludable", className: "hb-healthy" };
  if (age < 45) return { label: "Lento", className: "hb-slow" };
  return { label: "Sin respuesta", className: "hb-stale" };
}

function severityLabel(operation: CorpusOperationSummary | null, status: CorpusStatusPayload | null): {
  severity: "green" | "yellow" | "red";
  title: string;
  detail: string;
} {
  if (operation) {
    switch (operation.operation_state_code) {
      case "orphaned_queue":
        return {
          severity: "red",
          title: "Orphaned before start",
          detail: "The request was queued, but the backend worker never started.",
        };
      case "stalled_resumable":
        return {
          severity: "red",
          title: "Stalled",
          detail: operation.last_checkpoint?.phase
            ? `Backend stalled after ${humanizePhase(operation.last_checkpoint.phase)}. Resume is available.`
            : "Backend stalled, but a checkpoint is available to resume.",
        };
      case "failed_resumable":
        return {
          severity: "red",
          title: "Resumable",
          detail:
            operation.error
            || operation.failures?.[0]?.message
            || "The last run failed after writing a checkpoint. Resume is available.",
        };
      case "completed":
        return {
          severity: "green",
          title: "Completed",
          detail:
            operation.kind === "audit"
              ? "WIP audit completed. Artifact written."
              : operation.kind === "rollback"
                ? "Rollback completed and verified."
                : "Promotion completed and verified.",
        };
      case "running":
        return {
          severity: "yellow",
          title: "Running",
          detail: operation.current_phase
            ? `Backend phase: ${humanizePhase(operation.current_phase)}.`
            : operation.stage_label
              ? `Stage: ${operation.stage_label}.`
              : "The backend is processing the promotion.",
        };
      default:
        return {
          severity: operation.severity ?? "red",
          title: operation.severity === "yellow" ? "Running" : "Failed",
          detail: operation.error || operation.failures?.[0]?.message || "The operation ended with an error.",
        };
    }
  }

  if (status?.preflight_ready) {
    return {
      severity: "green",
      title: "Ready",
      detail: "WIP audit and promotion preflight are green.",
    };
  }
  return {
    severity: "red",
    title: "Blocked",
    detail: status?.preflight_reasons?.[0] || "Production is not ready for a safe promotion.",
  };
}

function operationTitle(operation: CorpusOperationSummary | null): string {
  if (!operation) return "Promote WIP to Production";
  if (operation.kind === "audit") return "WIP Health Audit";
  if (operation.kind === "rollback") return "Rollback Production";
  if (operation.mode === "force_reset") return "Force Reset + Promote Production";
  return "Promote WIP to Production";
}

function renderSnapshotRow(label: string, snap: PromotionTargetSnapshot | null | undefined): string {
  if (!snap || snap.available === false) {
    return `<tr><td>${esc(label)}</td><td colspan="2" class="corpus-report-unavail">no disponible</td></tr>`;
  }
  return `
    <tr>
      <td>${esc(label)}</td>
      <td><code>${esc(shortGen(snap.generation_id))}</code></td>
      <td>${fmtNum(snap.documents)} docs · ${fmtNum(snap.chunks)} chunks</td>
    </tr>`;
}

function renderKnowledgeClassRows(
  before: PromotionTargetSnapshot | null | undefined,
  after: PromotionTargetSnapshot | null | undefined,
): string {
  const allKeys = new Set<string>();
  for (const k of Object.keys(before?.knowledge_class_counts ?? {})) allKeys.add(k);
  for (const k of Object.keys(after?.knowledge_class_counts ?? {})) allKeys.add(k);
  if (allKeys.size === 0) return "";
  const sorted = [...allKeys].sort();
  return sorted
    .map((key) => {
      const bv = (before?.knowledge_class_counts ?? {})[key] ?? 0;
      const av = (after?.knowledge_class_counts ?? {})[key] ?? 0;
      const d = av - bv;
      const deltaClass = d > 0 ? "is-positive" : d < 0 ? "is-negative" : "";
      const deltaLabel = d > 0 ? `+${fmtNum(d)}` : d < 0 ? fmtNum(d) : "—";
      return `
        <tr class="corpus-report-kc-row">
          <td>${esc(key)}</td>
          <td>${fmtNum(bv)}</td>
          <td>${fmtNum(av)}</td>
          <td class="corpus-report-delta ${deltaClass}">${deltaLabel}</td>
        </tr>`;
    })
    .join("");
}

function fmtDuration(startedAt: string | undefined, completedAt: string | undefined | null): string {
  if (!startedAt || !completedAt) return "-";
  const start = Date.parse(startedAt);
  const end = Date.parse(completedAt);
  if (Number.isNaN(start) || Number.isNaN(end)) return "-";
  const totalSec = Math.max(0, Math.floor((end - start) / 1000));
  const minutes = Math.floor(totalSec / 60);
  const seconds = totalSec % 60;
  if (minutes === 0) return `${seconds}s`;
  return `${minutes}m ${seconds}s`;
}

function renderPromotionReport(operation: CorpusOperationSummary | null): string {
  const summary: PromotionSummary | null | undefined = operation?.promotion_summary;
  if (!summary) return "";
  const { before, after, delta, plan_result } = summary;

  const deltaDocLabel = (delta?.documents ?? 0) > 0
    ? `+${fmtNum(delta?.documents)}`
    : fmtNum(delta?.documents);
  const deltaChunkLabel = (delta?.chunks ?? 0) > 0
    ? `+${fmtNum(delta?.chunks)}`
    : fmtNum(delta?.chunks);
  const deltaDocClass = (delta?.documents ?? 0) > 0 ? "is-positive" : (delta?.documents ?? 0) < 0 ? "is-negative" : "";
  const deltaChunkClass = (delta?.chunks ?? 0) > 0 ? "is-positive" : (delta?.chunks ?? 0) < 0 ? "is-negative" : "";

  const beforeAfterTable = (before || after)
    ? `
      <table class="corpus-report-table">
        <thead>
          <tr><th></th><th>Generación</th><th>Documentos / Chunks</th></tr>
        </thead>
        <tbody>
          ${renderSnapshotRow("Antes", before)}
          ${renderSnapshotRow("Después", after)}
        </tbody>
        ${delta ? `
        <tfoot>
          <tr>
            <td>Delta</td>
            <td></td>
            <td>
              <span class="corpus-report-delta ${deltaDocClass}">${deltaDocLabel} docs</span> ·
              <span class="corpus-report-delta ${deltaChunkClass}">${deltaChunkLabel} chunks</span>
            </td>
          </tr>
        </tfoot>` : ""}
      </table>
      ${renderKnowledgeClassRows(before, after) ? `
      <table class="corpus-report-table corpus-report-table-kc">
        <thead><tr><th>Clase</th><th>Antes</th><th>Después</th><th>Delta</th></tr></thead>
        <tbody>${renderKnowledgeClassRows(before, after)}</tbody>
      </table>` : ""}`
    : "";

  const statEntries: Array<{ label: string; key: string }> = [
    { label: "Docs staged", key: "docs_staged" },
    { label: "Docs upserted", key: "docs_upserted" },
    { label: "Docs new", key: "docs_new" },
    { label: "Docs removed", key: "docs_removed" },
    { label: "Chunks new", key: "chunks_new" },
    { label: "Chunks changed", key: "chunks_changed" },
    { label: "Chunks removed", key: "chunks_removed" },
    { label: "Chunks unchanged", key: "chunks_unchanged" },
    { label: "Chunks embedded", key: "chunks_embedded" },
  ];

  const statsGrid = plan_result
    ? `
      <div class="corpus-report-grid">
        ${statEntries
          .filter((entry) => plan_result[entry.key] !== undefined && plan_result[entry.key] !== null)
          .map(
            (entry) => `
              <div class="corpus-report-stat">
                <span class="corpus-report-stat-value">${esc(String(plan_result[entry.key] ?? "-"))}</span>
                <span class="corpus-report-stat-label">${esc(entry.label)}</span>
              </div>`,
          )
          .join("")}
      </div>`
    : "";

  const duration = fmtDuration(operation?.started_at, operation?.completed_at);

  return `
    <div class="corpus-section corpus-report-section">
      <h4>Promotion Report</h4>
      ${beforeAfterTable}
      ${statsGrid}
      ${duration !== "-" ? `<p class="corpus-report-duration">Duración: <strong>${esc(duration)}</strong></p>` : ""}
    </div>`;
}

export function createCorpusLifecycleController({
  dom,
  setFlash,
}: CreateCorpusLifecycleControllerOptions) {
  let _lastStatus: CorpusStatusPayload | null = null;
  let _toastTimer: ReturnType<typeof setTimeout> | null = null;
  let _pollHandle: number | null = null;
  let _launchingAction: "" | "promote" | "resume" | "rollback" | "audit" = "";
  let _lastRefreshError = "";
  let _inlineLaunchNotice: { tone: "success" | "error"; message: string } | null = null;
  let _confirmOverlay: HTMLDivElement | null = null;
  let _logTailOpen = false;
  let _checksOpen = false;
  let _syncingToWip = false;

  // ── Resume progress tracking ──
  let _isResumedRun = false;
  let _resumeStartCursor = 0;
  let _prevCursorSample: { cursor: number; ts: number } | null = null;
  let _estimatedRate = 0; // chunks/sec (smoothed)

  function _showToast(msg: string, tone: "success" | "error"): void {
    if (_toastTimer) clearTimeout(_toastTimer);
    setFlash(msg, tone);
    const el = dom.container.querySelector<HTMLElement>(".corpus-toast");
    if (el) {
      el.hidden = false;
      el.dataset.tone = tone;
      el.textContent = msg;
      el.classList.remove("corpus-toast-enter");
      void el.offsetWidth;
      el.classList.add("corpus-toast-enter");
    }
    _toastTimer = setTimeout(() => {
      const toast = dom.container.querySelector<HTMLElement>(".corpus-toast");
      if (toast) toast.hidden = true;
    }, 6_000);
  }

  function _showConfirm(
    title: string,
    body: string,
    confirmLabel: string,
    confirmTone: "promote" | "rollback" = "promote",
  ): Promise<boolean> {
    return new Promise((resolve) => {
      _confirmOverlay?.remove();
      const overlay = document.createElement("div");
      overlay.className = "corpus-confirm-overlay";
      _confirmOverlay = overlay;
      overlay.innerHTML = `
        <div class="corpus-confirm-dialog">
          <h3 class="corpus-confirm-title">${esc(title)}</h3>
          <div class="corpus-confirm-body">${body}</div>
          <div class="corpus-confirm-actions">
            <button class="corpus-btn corpus-btn-rollback" data-action="cancel">Cancelar</button>
            <button class="corpus-btn ${confirmTone === "rollback" ? "corpus-btn-rollback" : "corpus-btn-promote"}" data-action="confirm">${esc(confirmLabel)}</button>
          </div>
        </div>
      `;
      document.body.appendChild(overlay);
      requestAnimationFrame(() => overlay.classList.add("is-visible"));

      function cleanup(result: boolean): void {
        if (_confirmOverlay === overlay) _confirmOverlay = null;
        overlay.classList.remove("is-visible");
        setTimeout(() => overlay.remove(), 180);
        resolve(result);
      }

      overlay.addEventListener("click", (event) => {
        const btn = (event.target as HTMLElement).closest<HTMLElement>("[data-action]");
        if (btn) cleanup(btn.dataset.action === "confirm");
        else if (event.target === overlay) cleanup(false);
      });
    });
  }

  async function _launchOperation(
    path: string,
    body: Record<string, unknown>,
    action: "" | "promote" | "resume" | "rollback" | "audit",
    successMessage: string,
  ): Promise<void> {
    if (_launchingAction) return;
    _launchingAction = action;
    _render();
    try {
      const { response, data } = await postJson<CorpusOperationLaunchResult>(path, body);
      if (response.ok && data?.job_id) {
        _inlineLaunchNotice = {
          tone: "success",
          message: `${successMessage} Job ${shortGen(data.job_id)}.`,
        };
        _showToast(`${successMessage} Job ${shortGen(data.job_id)}.`, "success");
      } else {
        _inlineLaunchNotice = {
          tone: "error",
          message: data?.error || "No se pudo iniciar la operación.",
        };
        _showToast(data?.error || "No se pudo iniciar la operación.", "error");
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      _inlineLaunchNotice = { tone: "error", message };
      _showToast(message, "error");
    } finally {
      _launchingAction = "";
      await refresh();
    }
  }

  async function _handleRebuild(): Promise<void> {
    const status = _lastStatus;
    if (!status || _launchingAction) return;
    const confirmed = await _showConfirm(
      "Promote WIP to Production",
      `<p>This path reuses the live WIP generation and promotes it incrementally into Production with persisted checkpoints.</p>
       <table class="corpus-confirm-table">
         <tr><td>Production current:</td><td><strong>${fmtNum(status.production.documents)}</strong> docs · <strong>${fmtNum(status.production.chunks)}</strong> chunks</td></tr>
         <tr><td>WIP source:</td><td><strong>${fmtNum(status.wip.documents)}</strong> docs · <strong>${fmtNum(status.wip.chunks)}</strong> chunks</td></tr>
         <tr><td>WIP generation:</td><td><code>${esc(shortGen(status.wip.generation_id))}</code></td></tr>
       </table>
       <label style="display:flex;align-items:center;gap:0.4rem;margin:0.75rem 0;font-size:0.85rem;cursor:pointer">
         <input type="checkbox" id="corpus-force-full-upsert" />
         Forzar upsert completo (sincronizar summaries + embeddings aunque chunk_text no haya cambiado)
       </label>
       <p class="corpus-confirm-note">The backend will keep a promotion plan, batch checkpoints, and a resumable cursor before activation.</p>`,
      "Promote now",
    );
    if (!confirmed) return;
    const forceEl = document.querySelector<HTMLInputElement>("#corpus-force-full-upsert");
    const forceFullUpsert = forceEl?.checked ?? false;
    _isResumedRun = false;
    _resumeStartCursor = 0;
    _prevCursorSample = null;
    _estimatedRate = 0;
    await _launchOperation(
      "/api/ops/corpus/rebuild-from-wip",
      { mode: "promote", force_full_upsert: forceFullUpsert },
      "promote",
      forceFullUpsert ? "Promotion started (force full upsert)." : "Promotion started.",
    );
  }

  async function _handleResume(): Promise<void> {
    const operation = _lastStatus?.current_operation ?? _lastStatus?.last_operation ?? null;
    if (!operation?.resume_job_id || _launchingAction) return;
    const confirmed = await _showConfirm(
      "Resume from Checkpoint",
      `<p>The backend will reuse the persisted promotion plan and continue from the last completed checkpoint.</p>
       <table class="corpus-confirm-table">
         <tr><td>Job:</td><td><code>${esc(shortGen(operation.resume_job_id))}</code></td></tr>
         <tr><td>Checkpoint:</td><td>${esc(checkpointSummary(operation))}</td></tr>
         <tr><td>Target generation:</td><td><code>${esc(shortGen(operation.target_generation_id))}</code></td></tr>
       </table>`,
      "Resume now",
    );
    if (!confirmed) return;
    _isResumedRun = true;
    _resumeStartCursor = operation.last_checkpoint?.cursor ?? 0;
    _prevCursorSample = null;
    _estimatedRate = 0;
    await _launchOperation(
      "/api/ops/corpus/rebuild-from-wip/resume",
      { job_id: operation.resume_job_id },
      "resume",
      "Resume started.",
    );
  }

  async function _handleRollback(): Promise<void> {
    const status = _lastStatus;
    if (!status || !status.rollback_generation_id || _launchingAction) return;
    const confirmed = await _showConfirm(
      "Rollback de Production",
      `<p>Se va a intentar reactivar una generación previa de production.</p>
       <table class="corpus-confirm-table">
         <tr><td>Production actual:</td><td><code>${esc(shortGen(status.production.generation_id))}</code></td></tr>
         <tr><td>Objetivo:</td><td><code>${esc(shortGen(status.rollback_generation_id))}</code></td></tr>
       </table>
       <p class="corpus-confirm-note">Solo se habilita si el backend detecta una generación previa todavía utilizable.</p>`,
      "Revertir ahora",
      "rollback",
    );
    if (!confirmed) return;
    await _launchOperation(
      "/api/ops/corpus/rollback",
      { generation_id: status.rollback_generation_id },
      "rollback",
      "Rollback started.",
    );
  }

  async function _handleAudit(): Promise<void> {
    if (_launchingAction) return;
    await _launchOperation(
      "/api/ops/corpus/wip-audit",
      {},
      "audit",
      "WIP audit started.",
    );
  }

  async function _handleRestart(): Promise<void> {
    if (_launchingAction) return;
    const confirmed = await _showConfirm(
      "Reiniciar promoción",
      `<p>Cancela cualquier job anterior y lanza una nueva promoción desde WIP a producción.</p>
       <label style="display:flex;align-items:center;gap:0.4rem;margin:0.75rem 0;font-size:0.85rem;cursor:default;opacity:0.55" title="Force upsert es obligatorio en reinicio">
         <input type="checkbox" checked disabled style="opacity:0.55" />
         Forzar upsert completo (sincronizar summaries + embeddings aunque chunk_text no haya cambiado)
       </label>
       <p class="corpus-confirm-note">Reiniciar siempre usa force upsert: todos los ~50K chunks se copian completos.</p>`,
      "Reiniciar ahora",
      "rollback",
    );
    if (!confirmed) return;
    _isResumedRun = false;
    _resumeStartCursor = 0;
    _prevCursorSample = null;
    _estimatedRate = 0;
    await _launchOperation(
      "/api/ops/corpus/rebuild-from-wip/restart",
      {},
      "restart",
      "Restart submitted (force full upsert).",
    );
  }

  async function _handleSyncToWip(): Promise<void> {
    if (_syncingToWip || _launchingAction) return;
    const confirmed = await _showConfirm(
      "Sincronizar JSONL a WIP",
      `<p>Se va a sincronizar el índice JSONL local ya existente al Supabase WIP (Docker).</p>
       <p class="corpus-confirm-note">Esta operación no ejecuta reindex — solo sincroniza los documentos y chunks que ya existen en el JSONL local. Es segura e idempotente.</p>`,
      "Sincronizar ahora",
    );
    if (!confirmed) return;
    _syncingToWip = true;
    _render();
    try {
      const { response, data } = await postJson<{
        synced?: boolean;
        documents?: number;
        chunks?: number;
        error?: string;
      }>("/api/ops/corpus/sync-to-wip", {});
      if (response.ok && data?.synced) {
        _showToast(`WIP sincronizado: ${fmtNum(data.documents)} docs, ${fmtNum(data.chunks)} chunks.`, "success");
      } else {
        _showToast(data?.error || "Error sincronizando a WIP.", "error");
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      _showToast(message || "Error sincronizando a WIP.", "error");
    } finally {
      _syncingToWip = false;
      await refresh();
    }
  }

  async function _handleCopyLogTail(): Promise<void> {
    const operation = _lastStatus?.current_operation ?? _lastStatus?.last_operation ?? null;
    const logTail = String(operation?.log_tail || "").trim();
    if (!logTail) return;
    try {
      await navigator.clipboard.writeText(logTail);
      _showToast("Log tail copied.", "success");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not copy log tail.";
      _showToast(message || "Could not copy log tail.", "error");
    }
  }

  function _render(): void {
    const prevLogOpen = dom.container.querySelector<HTMLDetailsElement>(".corpus-log-accordion");
    if (prevLogOpen) _logTailOpen = prevLogOpen.open;
    const prevChecksOpen = dom.container.querySelector<HTMLDetailsElement>(".corpus-checks-accordion");
    if (prevChecksOpen) _checksOpen = prevChecksOpen.open;

    const status = _lastStatus;
    if (!status) {
      dom.container.innerHTML = `<p class="ops-empty">${esc(_lastRefreshError || "Cargando estado del corpus…")}</p>`;
      return;
    }

    const operation = status.current_operation ?? status.last_operation ?? null;
    const header = severityLabel(operation, status);
    const busy = Boolean(status.current_operation && ["queued", "running"].includes(status.current_operation.status)) || Boolean(_launchingAction);
    const promoteDisabled = busy || !status.preflight_ready;
    const resumeVisible = !busy && Boolean(
      operation
      && operation.resume_supported
      && operation.resume_job_id
      && (operation.operation_state_code === "stalled_resumable" || operation.operation_state_code === "failed_resumable"),
    );
    const rollbackDisabled = busy || !status.rollback_available;
    const deltaText =
      status.delta.documents === "+0" && status.delta.chunks === "+0"
        ? "Sin delta pendiente"
        : `${status.delta.documents} documentos · ${status.delta.chunks} chunks`;
    const failureChecks = renderChecks(operation?.checks, { onlyFailures: true });
    const allChecks = renderChecks(operation?.checks);
    const running = Boolean(status.current_operation && ["queued", "running"].includes(status.current_operation.status));
    const inlineNotice =
      _inlineLaunchNotice && !(status.current_operation && ["queued", "running"].includes(status.current_operation.status))
        ? `
          <div class="corpus-callout tone-${esc(_inlineLaunchNotice.tone === "success" ? "green" : "red")}">
            <strong>${_inlineLaunchNotice.tone === "success" ? "Request sent" : "Request failed"}</strong>
            <span>${esc(_inlineLaunchNotice.message)}</span>
          </div>`
        : "";
    const checkpointCallout = operation?.last_checkpoint?.phase
      ? (() => {
          const tone = operation.operation_state_code === "completed" ? "green"
            : (operation.operation_state_code === "failed_resumable" || operation.operation_state_code === "stalled_resumable") ? "red"
            : "yellow";
          const pct = progressPct(operation);
          return `
            <div class="corpus-callout tone-${esc(tone)}">
              <strong>Checkpoint</strong>
              <span>${esc(checkpointSummary(operation))} · ${esc(fmtRelative(operation.last_checkpoint.at || null))}</span>
              ${pct > 0 && tone !== "green" ? `<div class="corpus-progress-bar corpus-progress-bar-sm"><div class="corpus-progress-fill" style="width:${pct.toFixed(1)}%"></div></div>` : ""}
            </div>`;
        })()
      : "";

    dom.container.innerHTML = `
      <div class="corpus-cards">
        ${renderTargetCard("WIP", status.wip)}
        ${renderTargetCard("PRODUCTION", status.production)}
      </div>
      <div class="corpus-delta">
        <span class="corpus-delta-label">${esc(deltaText)}</span>
      </div>
      <section class="corpus-operation-panel severity-${esc(header.severity)}">
        <div class="corpus-operation-header">
          <div>
            <div class="corpus-status-chip tone-${esc(header.severity)}${header.severity === "yellow" ? " is-pulsing" : ""}">
              ${esc(header.title)}
            </div>
            <h3 class="corpus-operation-title">${esc(operationTitle(operation))}</h3>
            <p class="corpus-operation-detail">${esc(header.detail)}</p>
          </div>
          <dl class="corpus-operation-meta">
            <div><dt>Heartbeat</dt><dd>${esc(fmtRelative(operation?.heartbeat_at || operation?.updated_at || null))}</dd></div>
            <div><dt>Backend</dt><dd>${esc(modeLabel(operation))}${operation?.force_full_upsert ? ` <span style="background:${palette.amber[100]};color:${palette.amber[600]};padding:0.1rem 0.4rem;border-radius:0.3rem;font-size:0.7rem;font-weight:700">FORCE UPSERT</span>` : ""}</dd></div>
            <div><dt>Phase</dt><dd>${esc(operation?.current_phase ? humanizePhase(operation.current_phase) : (operation?.stage_label || (status.preflight_ready ? "Ready" : "Blocked")))}</dd></div>
            <div><dt>Checkpoint</dt><dd>${esc(checkpointSummary(operation))}</dd></div>
            <div><dt>WIP</dt><dd><code>${esc(shortGen(operation?.source_generation_id || status.wip.generation_id))}</code></dd></div>
            <div><dt>Target</dt><dd><code>${esc(shortGen(operation?.target_generation_id || operation?.production_generation_id || status.production.generation_id))}</code></dd></div>
            <div><dt>Prod</dt><dd><code>${esc(shortGen(operation?.production_generation_id || status.production.generation_id))}</code></dd></div>
          </dl>
        </div>
        ${running ? (() => {
          const pct = progressPct(operation);
          const cursor = operation?.last_checkpoint?.cursor ?? operation?.batch_cursor ?? 0;
          const total = operation?.last_checkpoint?.total ?? 0;
          const hb = heartbeatHealth(operation);

          // Update rate estimation
          if (cursor > 0 && total > 0) {
            const now = Date.now();
            if (_prevCursorSample && cursor > _prevCursorSample.cursor) {
              const dt = Math.max(1, (now - _prevCursorSample.ts) / 1000);
              const instantRate = (cursor - _prevCursorSample.cursor) / dt;
              _estimatedRate = _estimatedRate > 0
                ? _estimatedRate * 0.7 + instantRate * 0.3
                : instantRate;
            }
            _prevCursorSample = { cursor, ts: now };
          }

          const rateStr = _estimatedRate > 0 ? `${_estimatedRate.toFixed(0)} chunks/s` : "";
          const remaining = total - cursor;
          const etaStr = _estimatedRate > 0 && remaining > 0
            ? (() => {
                const secs = Math.ceil(remaining / _estimatedRate);
                const m = Math.floor(secs / 60);
                const s = secs % 60;
                return m > 0 ? `~${m}m ${s}s restante` : `~${s}s restante`;
              })()
            : "";

          return `
            <div class="corpus-progress-bar"><div class="corpus-progress-fill" style="width:${pct.toFixed(1)}%"></div></div>
            <div class="corpus-progress-detail">
              ${_isResumedRun ? `<span class="corpus-resume-badge">REANUDADO desde ${fmtNum(_resumeStartCursor)}</span>` : ""}
              <span class="corpus-progress-nums">${fmtNum(cursor)} / ${fmtNum(total)} (${pct.toFixed(1)}%)</span>
              ${rateStr ? `<span class="corpus-progress-rate">${esc(rateStr)}</span>` : ""}
              ${etaStr ? `<span class="corpus-progress-eta">${esc(etaStr)}</span>` : ""}
              <span class="corpus-hb-badge ${hb.className}">${esc(hb.label)}</span>
            </div>`;
        })() : ""}
        ${operation?.stages?.length ? renderStages(operation.stages) : ""}
        ${checkpointCallout}
        ${status.preflight_reasons?.length && !running && !status.preflight_ready ? `
          <div class="corpus-callout tone-red">
            <strong>Preflight blocked</strong>
            <ul>${status.preflight_reasons.map((reason) => `<li>${esc(reason)}</li>`).join("")}</ul>
          </div>` : ""}
        ${inlineNotice}
        ${failureChecks ? `<div class="corpus-section"><h4>Visible failures</h4>${failureChecks}</div>` : ""}
        ${allChecks ? `
          <details class="corpus-section corpus-checks-accordion">
            <summary class="corpus-checks-summary"><h4>Checks</h4><span class="corpus-checks-count">${(operation?.checks ?? []).length}</span></summary>
            ${allChecks}
          </details>` : ""}
        ${renderPromotionReport(operation)}
        ${operation?.log_tail ? `
          <details class="corpus-section corpus-log-accordion">
            <summary class="corpus-log-summary">
              <h4>Backend log tail</h4>
              <button id="corpus-copy-log-tail-btn" type="button" class="corpus-btn corpus-btn-rollback corpus-btn-inline">Copy</button>
            </summary>
            <pre class="corpus-log-tail">${esc(operation.log_tail)}</pre>
          </details>` : ""}
        ${_lastRefreshError ? `
          <div class="corpus-callout tone-red">
            <strong>Refresh error</strong>
            <span>${esc(_lastRefreshError)}</span>
          </div>` : ""}
      </section>
      <div class="corpus-actions">
        ${status.audit_missing && !busy ? `
          <button id="corpus-audit-btn" class="corpus-btn corpus-btn-audit${_launchingAction === "audit" ? " is-busy" : ""}">
            ${_launchingAction === "audit" ? '<span class="corpus-spinner"></span> Auditing…' : "Run WIP Audit"}
          </button>` : ""}
        ${!busy && !_syncingToWip ? `
          <button id="corpus-sync-wip-btn" class="corpus-btn corpus-btn-sync">Sincronizar JSONL a WIP</button>` : ""}
        ${_syncingToWip ? `
          <button class="corpus-btn corpus-btn-sync is-busy" disabled><span class="corpus-spinner"></span> Sincronizando…</button>` : ""}
        <button id="corpus-promote-btn" class="corpus-btn corpus-btn-promote${_launchingAction === "promote" ? " is-busy" : ""}" ${promoteDisabled ? "disabled" : ""}>
          ${_launchingAction === "promote" ? '<span class="corpus-spinner"></span> Starting…' : "Promote WIP to Production"}
        </button>
        ${resumeVisible ? `
          <button id="corpus-resume-btn" class="corpus-btn corpus-btn-promote${_launchingAction === "resume" ? " is-busy" : ""}">
            ${_launchingAction === "resume" ? '<span class="corpus-spinner"></span> Resuming…' : "Resume from Checkpoint"}
          </button>` : ""}
        <button id="corpus-rollback-btn" class="corpus-btn corpus-btn-rollback${_launchingAction === "rollback" ? " is-busy" : ""}" ${rollbackDisabled ? "disabled" : ""}>
          ${_launchingAction === "rollback" ? '<span class="corpus-spinner"></span> Starting rollback…' : "Rollback"}
        </button>
        <button id="corpus-restart-btn" class="corpus-btn corpus-btn-rollback${_launchingAction === "restart" ? " is-busy" : ""}" ${busy ? "disabled" : ""}>
          ${_launchingAction === "restart" ? '<span class="corpus-spinner"></span> Restarting…' : "Reiniciar promoción (force upsert)"}
        </button>
      </div>
      ${!status.preflight_ready ? `
        <p class="corpus-action-note">${esc(status.preflight_reasons?.[0] || "Promotion is blocked by preflight.")}</p>` : ""}
      ${!status.rollback_available ? `
        <p class="corpus-action-note">${esc(status.rollback_reason || "Rollback is not available yet.")}</p>` : ""}
      <div class="corpus-toast ops-flash" hidden></div>
    `;

    dom.container.querySelector<HTMLButtonElement>("#corpus-audit-btn")?.addEventListener("click", _handleAudit);
    dom.container.querySelector<HTMLButtonElement>("#corpus-sync-wip-btn")?.addEventListener("click", () => void _handleSyncToWip());
    dom.container.querySelector<HTMLButtonElement>("#corpus-promote-btn")?.addEventListener("click", _handleRebuild);
    dom.container.querySelector<HTMLButtonElement>("#corpus-resume-btn")?.addEventListener("click", _handleResume);
    dom.container.querySelector<HTMLButtonElement>("#corpus-rollback-btn")?.addEventListener("click", _handleRollback);
    dom.container.querySelector<HTMLButtonElement>("#corpus-restart-btn")?.addEventListener("click", _handleRestart);
    dom.container.querySelector<HTMLButtonElement>("#corpus-copy-log-tail-btn")?.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      void _handleCopyLogTail();
    });
    const logAccordion = dom.container.querySelector<HTMLDetailsElement>(".corpus-log-accordion");
    if (logAccordion && _logTailOpen) logAccordion.open = true;
    const checksAccordion = dom.container.querySelector<HTMLDetailsElement>(".corpus-checks-accordion");
    if (checksAccordion && _checksOpen) checksAccordion.open = true;
  }

  async function refresh(): Promise<void> {
    try {
      _lastStatus = await getJson<CorpusStatusPayload>("/api/ops/corpus-status");
      _lastRefreshError = "";
      if (_lastStatus?.current_operation && ["queued", "running", "completed", "failed", "cancelled"].includes(_lastStatus.current_operation.status)) {
        _inlineLaunchNotice = null;
      }
    } catch (error) {
      _lastRefreshError = error instanceof Error ? error.message : String(error);
      if (_lastStatus === null) {
        _lastStatus = null;
      }
    }
    _render();
  }

  function bindEvents(): void {
    _render();
    if (_pollHandle === null) {
      _pollHandle = window.setInterval(() => {
        void refresh();
      }, FAST_POLL_INTERVAL_MS);
    }
  }

  return { bindEvents, refresh };
}
