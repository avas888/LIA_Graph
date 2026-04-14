import { getJson, postJson } from "@/shared/api/client";
import type { EmbeddingStatusPayload, EmbeddingOperation } from "./opsTypes";
import { buildProgressNode } from "./opsTypes";

export interface CreateOpsEmbeddingsControllerOptions {
  dom: { container: HTMLElement };
  setFlash: (msg: string, tone: "success" | "error") => void;
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

export function createOpsEmbeddingsController({
  dom,
  setFlash,
}: CreateOpsEmbeddingsControllerOptions) {
  const { container } = dom;
  let _lastStatus: EmbeddingStatusPayload | null = null;
  let _launchingAction: "" | "start" | "stop" | "resume" = "";
  let _forceChecked = false;
  let _logOpen = false;

  // Self-adjusting heartbeat: tracks batch progress timestamps
  let _lastBatchCount = 0;
  let _lastBatchTime = 0;        // Date.now() of last observed batch change
  let _avgBatchMs = 3000;        // rolling average ms per batch (seed 3s)
  let _batchSamples: number[] = []; // last N inter-batch intervals

  function _updateBatchHeartbeat(currentBatch: number): void {
    if (currentBatch <= 0) return;
    const now = Date.now();
    if (currentBatch > _lastBatchCount && _lastBatchTime > 0) {
      const delta = now - _lastBatchTime;
      const batchesDone = currentBatch - _lastBatchCount;
      const perBatch = delta / batchesDone;
      _batchSamples.push(perBatch);
      if (_batchSamples.length > 10) _batchSamples.shift();
      _avgBatchMs = _batchSamples.reduce((a, b) => a + b, 0) / _batchSamples.length;
    }
    if (currentBatch !== _lastBatchCount) {
      _lastBatchCount = currentBatch;
      _lastBatchTime = now;
    }
  }

  function _classifyProcessHealth(): { level: "healthy" | "caution" | "failed"; label: string } {
    if (_lastBatchTime === 0) return { level: "healthy", label: "Iniciando..." };
    const silenceMs = Date.now() - _lastBatchTime;
    const threshold3x = Math.max(_avgBatchMs * 3, 10_000);  // min 10s
    const threshold6x = Math.max(_avgBatchMs * 6, 30_000);  // min 30s
    if (silenceMs < threshold3x) return { level: "healthy", label: "Saludable" };
    if (silenceMs < threshold6x) return { level: "caution", label: "Lento" };
    return { level: "failed", label: "Sin respuesta" };
  }

  function _render(): void {
    const s = _lastStatus;
    if (!s) {
      container.innerHTML = '<p class="ops-text-muted">Cargando estado de embeddings...</p>';
      return;
    }

    const op = s.current_operation || s.last_operation;
    const curStatus = s.current_operation?.status ?? "";
    const isRunning = curStatus === "running" || curStatus === "queued" || _launchingAction === "start";
    const isIdle = !s.current_operation && !_launchingAction;
    const isStopping = _launchingAction === "stop";
    const canResume = !isRunning && !isStopping && (op?.status === "cancelled" || op?.status === "failed" || op?.status === "stalled");

    let html = "";

    // -- Status header --
    const opStatus = op?.status ?? "";
    const statusLabel = isStopping ? "Deteniendo..." : isRunning ? "En ejecución" : canResume ? (opStatus === "stalled" ? "Detenido (stalled)" : opStatus === "cancelled" ? "Cancelado" : "Fallido") : isIdle ? "Inactivo" : opStatus || "—";
    const statusTone = isRunning ? "tone-yellow" : opStatus === "completed" ? "tone-green" : (opStatus === "failed" || opStatus === "stalled") ? "tone-red" : opStatus === "cancelled" ? "tone-yellow" : "";
    // -- API health semaphore --
    const api = s.api_health;
    const apiDot = api?.ok ? "emb-api-ok" : "emb-api-error";
    const apiLabel = api ? (api.ok ? `API OK (${api.detail})` : `API Error: ${api.detail}`) : "API: verificando...";

    html += `<div class="emb-status-row">
      <span class="corpus-status-chip ${statusTone}">${esc(statusLabel)}</span>
      <span class="emb-target-badge">WIP</span>
      <span class="emb-api-semaphore ${apiDot}" title="${esc(apiLabel)}"><span class="emb-api-dot"></span> ${esc(api?.ok ? "API OK" : api ? "API Error" : "...")}</span>
      ${isRunning ? (() => { const h = _classifyProcessHealth(); return `<span class="emb-process-health emb-health-${h.level}"><span class="emb-health-dot"></span> ${esc(h.label)}</span>`; })() : ""}
    </div>`;

    // -- Controls --
    html += '<div class="emb-controls">';
    if (isIdle) {
      html += `<label class="emb-force-label"><input type="checkbox" id="emb-force-check" ${_forceChecked ? "checked" : ""} /> Forzar re-embed (todas)</label>`;
      html += `<button class="corpus-btn corpus-btn-promote" id="emb-start-btn" ${_launchingAction ? "disabled" : ""}>Iniciar</button>`;
    } else if (isStopping) {
      html += `<span class="emb-running-label">Deteniendo al finalizar batch actual...</span>`;
    } else if (isRunning && op) {
      html += `<button class="corpus-btn corpus-btn-rollback" id="emb-stop-btn">Detener</button>`;
      html += `<span class="emb-running-label">Embebiendo chunks...</span>`;
    }
    if (canResume && op) {
      const wasForce = op.force;
      const cursor = (op.progress as Record<string, unknown>)?.last_cursor_id;
      const pct = (op.progress as Record<string, unknown>)?.pct_complete;
      const resumeLabel = cursor ? `Reanudar desde ${typeof pct === "number" ? pct.toFixed(1) + "%" : "checkpoint"}` : "Reiniciar";
      if (wasForce) {
        html += `<span class="emb-force-label"><input type="checkbox" checked disabled /> Forzar re-embed (continuación)</span>`;
      }
      html += `<button class="corpus-btn corpus-btn-promote" id="emb-resume-btn" ${_launchingAction ? "disabled" : ""}>${esc(resumeLabel)}</button>`;
      html += `<button class="corpus-btn" id="emb-start-btn" ${_launchingAction ? "disabled" : ""} style="opacity:0.7">Iniciar desde cero</button>`;
    }
    html += "</div>";

    // -- Stats grid: show job progress when running, DB counts when idle --
    const p = op?.progress;
    const showJobStats = (isRunning || _launchingAction) && p?.total;
    const statTotal = showJobStats ? p!.total : s.total_chunks;
    const statEmbedded = showJobStats ? p!.embedded : s.embedded_chunks;
    const statPending = showJobStats ? (p!.pending - p!.embedded - (p!.failed || 0)) : s.null_embedding_chunks;
    const statFailed = showJobStats ? (p!.failed || 0) : 0;
    const statPct = showJobStats ? p!.pct_complete : s.coverage_pct;

    html += `<div class="emb-stats-grid">
      <div class="emb-stat"><span class="emb-stat-value">${fmtNum(statTotal)}</span><span class="emb-stat-label">Total</span></div>
      <div class="emb-stat"><span class="emb-stat-value">${fmtNum(statEmbedded)}</span><span class="emb-stat-label">Embebidos</span></div>
      <div class="emb-stat"><span class="emb-stat-value">${fmtNum(Math.max(0, statPending))}</span><span class="emb-stat-label">Pendientes</span></div>
      ${statFailed > 0 ? `<div class="emb-stat emb-stat-error"><span class="emb-stat-value">${fmtNum(statFailed)}</span><span class="emb-stat-label">Fallidos</span></div>` : `<div class="emb-stat"><span class="emb-stat-value">${statPct.toFixed(1)}%</span><span class="emb-stat-label">Cobertura</span></div>`}
    </div>`;

    // -- Live progress (when running) --
    if (isRunning && op?.progress) {
      const p = op.progress;
      html += '<div class="emb-live-progress">';
      html += `<div class="emb-progress-bar-wrap" id="emb-progress-mount"></div>`;
      html += `<div class="emb-rate-line">
        <span>${p.rate_chunks_per_sec?.toFixed(1) ?? "-"} chunks/s</span>
        <span>ETA: ${fmtSeconds(p.eta_seconds)}</span>
        <span>Elapsed: ${fmtSeconds(p.elapsed_seconds)}</span>
        <span>Batch ${fmtNum(p.current_batch)} / ${fmtNum(p.total_batches)}</span>
      </div>`;
      if (p.failed > 0) {
        html += `<p class="emb-failed-notice">${fmtNum(p.failed)} chunks fallidos (${(p.failed / Math.max(p.pending, 1) * 100).toFixed(2)}%)</p>`;
      }
      html += "</div>";
    }

    // -- Quality report (after completion) --
    if (op?.quality_report) {
      const qr = op.quality_report;
      html += '<div class="emb-quality-report">';
      html += "<h3>Reporte de calidad</h3>";
      html += `<div class="emb-stats-grid">
        <div class="emb-stat"><span class="emb-stat-value">${qr.mean_cosine_similarity?.toFixed(4) ?? "-"}</span><span class="emb-stat-label">Coseno medio</span></div>
        <div class="emb-stat"><span class="emb-stat-value">${qr.min_cosine_similarity?.toFixed(4) ?? "-"}</span><span class="emb-stat-label">Min</span></div>
        <div class="emb-stat"><span class="emb-stat-value">${qr.max_cosine_similarity?.toFixed(4) ?? "-"}</span><span class="emb-stat-label">Max</span></div>
        <div class="emb-stat"><span class="emb-stat-value">${fmtNum(qr.sample_pairs)}</span><span class="emb-stat-label">Pares</span></div>
      </div>`;
      if (qr.collapsed_warning) html += '<p class="emb-anomaly-warning">ANOMALIA: Embeddings colapsados (mean &gt; 0.95)</p>';
      if (qr.noise_warning) html += '<p class="emb-anomaly-warning">ANOMALIA: Embeddings ruidosos (mean &lt; 0.10)</p>';
      if (!qr.collapsed_warning && !qr.noise_warning) html += '<p class="emb-quality-ok">Distribución saludable</p>';
      html += "</div>";
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

    // -- Log tail (latest first) --
    if (op?.log_tail) {
      const reversedLog = op.log_tail.split("\n").reverse().join("\n");
      html += `<details class="emb-log-accordion" id="emb-log-details" ${_logOpen ? "open" : ""}><summary>Log</summary><pre class="emb-log-tail">${esc(reversedLog)}</pre></details>`;
    }

    // -- Error --
    if (op?.error) {
      html += `<p class="emb-error">${esc(op.error)}</p>`;
    }

    container.innerHTML = html;

    // Mount progress bar widget
    if (isRunning && op?.progress) {
      const mount = container.querySelector("#emb-progress-mount");
      if (mount) {
        mount.appendChild(buildProgressNode(op.progress.pct_complete ?? 0, "embedding"));
      }
    }
  }

  function bindEvents(): void {
    container.addEventListener("click", (e) => {
      const target = e.target as HTMLElement;
      if (target.id === "emb-start-btn") void _handleStart();
      if (target.id === "emb-stop-btn") void _handleStop();
      if (target.id === "emb-resume-btn") void _handleResume();
    });
    container.addEventListener("change", (e) => {
      const target = e.target as HTMLInputElement;
      if (target.id === "emb-force-check") {
        _forceChecked = target.checked;
      }
    });
    container.addEventListener("toggle", (e) => {
      const target = e.target as HTMLElement;
      if (target.id === "emb-log-details") {
        _logOpen = (target as HTMLDetailsElement).open;
      }
    }, true);
  }

  async function _handleStart(): Promise<void> {
    const force = _forceChecked;
    _launchingAction = "start";
    _forceChecked = false;
    _render();
    try {
      const { response, data } = await postJson<{ ok?: boolean; error?: string }>("/api/ops/embedding/start", { force });
      if (!response.ok || !(data?.ok)) {
        setFlash(data?.error || `Error ${response.status}`, "error");
        _launchingAction = "";
      } else {
        setFlash("Embedding iniciado", "success");
      }
    } catch (err) {
      setFlash(String(err), "error");
      _launchingAction = "";
    }
    await refresh();
  }

  async function _handleStop(): Promise<void> {
    const jobId = _lastStatus?.current_operation?.job_id;
    if (!jobId) return;
    _launchingAction = "stop";
    _render();
    try {
      await postJson("/api/ops/embedding/stop", { job_id: jobId });
      setFlash("Stop solicitado — se detendrá al finalizar el batch actual", "success");
    } catch (err) {
      setFlash(String(err), "error");
      _launchingAction = "";
    }
    // Don't clear _launchingAction="stop" — keep showing "Deteniendo..."
    // until the next poll confirms the job is no longer running.
  }

  async function _handleResume(): Promise<void> {
    const op = _lastStatus?.current_operation || _lastStatus?.last_operation;
    if (!op?.job_id) return;
    _launchingAction = "start";
    _render();
    try {
      const { response, data } = await postJson<{ ok?: boolean; error?: string }>("/api/ops/embedding/resume", { job_id: op.job_id });
      if (!response.ok || !(data?.ok)) {
        setFlash(data?.error || `Error ${response.status}`, "error");
        _launchingAction = "";
      } else {
        setFlash("Embedding reanudado desde checkpoint", "success");
      }
    } catch (err) {
      setFlash(String(err), "error");
      _launchingAction = "";
    }
    _launchingAction = "";
    await refresh();
  }

  async function refresh(): Promise<void> {
    try {
      const data = await getJson<EmbeddingStatusPayload>("/api/ops/embedding-status");
      _lastStatus = data;
      // Feed batch progress into heartbeat tracker
      const curOp = data.current_operation;
      if (curOp?.progress) {
        const batch = (curOp.progress as Record<string, unknown>).current_batch;
        if (typeof batch === "number") _updateBatchHeartbeat(batch);
      }
      // Clear "stopping" state once job is no longer running
      if (_launchingAction === "stop" && !data.current_operation) {
        _launchingAction = "";
      }
      // Clear "starting" state once job appears
      if (_launchingAction === "start" && data.current_operation) {
        _launchingAction = "";
      }
      // Reset heartbeat tracker when job finishes
      if (!data.current_operation) {
        _lastBatchCount = 0;
        _lastBatchTime = 0;
        _batchSamples = [];
      }
    } catch {
      // Keep last known state
    }
    _render();
  }

  return { bindEvents, refresh };
}
