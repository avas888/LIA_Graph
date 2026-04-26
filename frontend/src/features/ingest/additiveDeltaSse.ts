/**
 * SSE subscriber for the additive-corpus-v1 job events endpoint (Phase 8).
 *
 * Auto-reconnects up to ``maxReconnects`` (default 5) with exponential
 * backoff, then falls back to polling GET /api/ingest/additive/status at
 * ``pollingIntervalMs`` (default 10_000). Exposes a stable interface so the
 * controller (and tests) can drive without knowing about EventSource vs
 * fetch internals.
 */

export type AdditiveDeltaSseStatus =
  | "connecting"
  | "connected"
  | "reconnecting"
  | "polling"
  | "closed";

export interface AdditiveDeltaSseEvent {
  jobId: string;
  stage: string;
  progressPct: number;
  lastHeartbeatAt?: string | null;
  cancelRequested: boolean;
  reportJson?: Record<string, unknown> | null;
  errorClass?: string | null;
  errorMessage?: string | null;
}

/**
 * Surfaced when the polling layer can no longer give a confident progress
 * signal. The controller renders this as a visible chip — silent failure
 * is a regression (`gui_ingestion_v1 §3.4`). Cleared by the next clean
 * snapshot via `onHealthOk`.
 */
export interface AdditiveDeltaSseHealthInfo {
  /**
   * - `http_error`: /status returned a non-2xx (server / 5xx / route 404)
   * - `auth_missing`: 401 — token absent / expired
   * - `network_error`: fetch threw (network down, DNS, TLS)
   * - `stall`: row's `last_heartbeat_at` is older than the threshold; the
   *   worker thread is not writing back to Supabase even though we can
   *   reach /status
   */
  kind: "http_error" | "auth_missing" | "network_error" | "stall";
  /** Number of consecutive failed ticks since the last successful one. */
  attemptsSinceLastSuccess: number;
  /** ISO timestamp of the last 2xx /status response, or null if none yet. */
  lastSuccessAt: string | null;
  /** HTTP status when `kind === "http_error" | "auth_missing"`. */
  status?: number;
  /** Human-readable, surfaced verbatim to the operator. */
  message: string;
  /** When `kind === "stall"`: how long the heartbeat has been stale. */
  staleHeartbeatMs?: number;
}

export interface AdditiveDeltaProgressEvent {
  /** The full event_type string emitted by the backend (e.g.
   * `subtopic.ingest.classified`, `ingest.delta.parity.check.done`,
   * `ingest.delta.classifier.summary`). */
  eventType: string;
  /** Bogotá-ISO timestamp from the event. */
  tsUtc: string;
  /** The raw payload — shape depends on `eventType`. Keep loose; the
   * progress pane only reads a few well-known keys (`filename`, `total`,
   * `delta_id`, etc.) and ignores anything else. */
  payload: Record<string, unknown>;
}

export interface AdditiveDeltaSseHandlers {
  onSnapshot: (event: AdditiveDeltaSseEvent) => void;
  onStatusChange?: (status: AdditiveDeltaSseStatus) => void;
  onTerminal?: (event: AdditiveDeltaSseEvent) => void;
  /** Fired when the polling layer crosses the failure threshold OR when a
   * snapshot reveals a stale heartbeat. Re-fires on every subsequent tick
   * the issue persists so the UI's relative-time ("hace 23s") stays fresh. */
  onHealthIssue?: (info: AdditiveDeltaSseHealthInfo) => void;
  /** Fired when a clean tick observes a fresh heartbeat after a prior
   * health issue was surfaced — controller can clear its chip. */
  onHealthOk?: () => void;
  /** Fired for every per-event SSE message that isn't the initial
   * snapshot or a terminal stage transition (those go through onSnapshot
   * / onTerminal). The controller surfaces these as live activity ("now
   * classifying: Resolución-532-2024.md") so operators see motion during
   * the otherwise-silent classifier pass. */
  onProgressEvent?: (event: AdditiveDeltaProgressEvent) => void;
}

export interface AdditiveDeltaSseOptions {
  maxReconnects?: number;
  pollingIntervalMs?: number;
  eventSourceFactory?: (url: string) => EventSource;
  fetchImpl?: typeof fetch;
  /** Number of consecutive failed ticks before `onHealthIssue` fires.
   * Default 3 — at 2s polling that's 6s of pain before we yell. */
  consecutiveFailureThreshold?: number;
  /** Heartbeat staleness threshold in ms. Default 60_000 — the worker emits
   * `delta_job_store.heartbeat` every 15s, so 60s = 4 missed beats and
   * something is wrong. Past this, even a clean /status snapshot triggers
   * a stall warning. */
  staleHeartbeatThresholdMs?: number;
  /** Override for time-source in tests. */
  nowMs?: () => number;
}

export interface AdditiveDeltaSseHandle {
  close: () => void;
}

const TERMINAL_STAGES = new Set(["completed", "failed", "cancelled"]);

function parseEvent(raw: string): AdditiveDeltaSseEvent | null {
  try {
    const data = JSON.parse(raw);
    if (!data || typeof data !== "object") return null;
    const d = data as Record<string, unknown>;
    const jobId = String(d.job_id ?? "");
    if (!jobId) return null;
    return {
      jobId,
      stage: String(d.stage ?? "queued"),
      progressPct: Number(d.progress_pct ?? 0) || 0,
      lastHeartbeatAt: (d.last_heartbeat_at as string | null) ?? null,
      cancelRequested: Boolean(d.cancel_requested ?? false),
      reportJson: (d.report_json as Record<string, unknown> | null) ?? null,
      errorClass: (d.error_class as string | null) ?? null,
      errorMessage: (d.error_message as string | null) ?? null,
    };
  } catch {
    return null;
  }
}

export function subscribeJobEvents(
  jobId: string,
  handlers: AdditiveDeltaSseHandlers,
  opts: AdditiveDeltaSseOptions = {},
): AdditiveDeltaSseHandle {
  // Fase C — backend SSE now tails events.jsonl and streams every event
  // tagged with this job_id / delta_id. EventSource can't send headers
  // so we pass the bearer via `?token=...`; the backend lifts it into
  // the Authorization header before validating. Default 5 reconnects so
  // a flaky SSE doesn't fall to polling on the first hiccup; polling
  // remains the safety net for sustained outages.
  const maxReconnects = opts.maxReconnects ?? 5;
  const pollingIntervalMs = opts.pollingIntervalMs ?? 2_000;
  const esFactory =
    opts.eventSourceFactory ??
    ((url: string) => new EventSource(url));
  const fetchImpl = opts.fetchImpl ?? fetch.bind(globalThis);
  const consecutiveFailureThreshold = opts.consecutiveFailureThreshold ?? 3;
  const staleHeartbeatThresholdMs = opts.staleHeartbeatThresholdMs ?? 60_000;
  const now = opts.nowMs ?? (() => Date.now());

  function readToken(): string {
    if (typeof window === "undefined") return "";
    try {
      return (window.localStorage.getItem("lia_access_token") ?? "").trim();
    } catch {
      return "";
    }
  }

  function buildEventsUrl(): string {
    const base = `/api/ingest/additive/events?job_id=${encodeURIComponent(jobId)}`;
    const token = readToken();
    return token ? `${base}&token=${encodeURIComponent(token)}` : base;
  }

  const statusUrl = `/api/ingest/additive/status?job_id=${encodeURIComponent(jobId)}`;

  let reconnects = 0;
  let closed = false;
  let current: EventSource | null = null;
  let pollingTimer: ReturnType<typeof setInterval> | null = null;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  // Health tracking — Fase A. The previous behavior was to swallow every
  // failure silently; the operator stared at "EN COLA · sin heartbeat"
  // forever even when the row had moved on (or the worker had hung). Now
  // every tick contributes to either onHealthIssue or onHealthOk.
  let consecutiveFailures = 0;
  let lastSuccessAt: string | null = null;
  let healthIssueActive = false;

  function emitStatus(status: AdditiveDeltaSseStatus): void {
    handlers.onStatusChange?.(status);
  }

  function maybeTerminal(event: AdditiveDeltaSseEvent): void {
    if (TERMINAL_STAGES.has(event.stage)) {
      handlers.onTerminal?.(event);
      close();
    }
  }

  function handleMessage(raw: string): void {
    const event = parseEvent(raw);
    if (!event) return;
    handlers.onSnapshot(event);
    maybeTerminal(event);
  }

  function reportFailure(
    kind: AdditiveDeltaSseHealthInfo["kind"],
    message: string,
    status?: number,
  ): void {
    consecutiveFailures += 1;
    if (consecutiveFailures < consecutiveFailureThreshold) return;
    healthIssueActive = true;
    handlers.onHealthIssue?.({
      kind,
      attemptsSinceLastSuccess: consecutiveFailures,
      lastSuccessAt,
      status,
      message,
    });
  }

  function reportSuccess(snapshotHeartbeatAt: string | null | undefined): void {
    consecutiveFailures = 0;
    lastSuccessAt = new Date(now()).toISOString();
    // Stale-heartbeat check: even a clean fetch is unhealthy if the worker
    // hasn't written `last_heartbeat_at` recently. The worker emits one
    // every 15s; past 60s default = 4 missed beats and the worker thread
    // is wedged (or never started writing back to Supabase, which is the
    // exact 2026-04-26 incident this Fase A closes).
    if (snapshotHeartbeatAt) {
      const beat = Date.parse(snapshotHeartbeatAt);
      if (!Number.isNaN(beat)) {
        const staleMs = now() - beat;
        if (staleMs > staleHeartbeatThresholdMs) {
          healthIssueActive = true;
          handlers.onHealthIssue?.({
            kind: "stall",
            attemptsSinceLastSuccess: 0,
            lastSuccessAt,
            staleHeartbeatMs: staleMs,
            message:
              `El worker no escribe heartbeat hace ${Math.round(staleMs / 1000)}s. ` +
              "El thread puede estar trabado o sin permisos contra Supabase.",
          });
          return;
        }
      }
    }
    if (healthIssueActive) {
      healthIssueActive = false;
      handlers.onHealthOk?.();
    }
  }

  function startPolling(): void {
    emitStatus("polling");
    if (pollingTimer) return;
    const tick = async () => {
      if (closed) return;
      try {
        // Attach the Bearer token from localStorage so admin-gated
        // /status doesn't 401. Kept simple (no import cycle) by reading
        // the token ad-hoc; the shared client's storage key is
        // "lia_access_token".
        const token =
          typeof window !== "undefined"
            ? window.localStorage.getItem("lia_access_token")
            : null;
        if (!token || !token.trim()) {
          reportFailure(
            "auth_missing",
            "No hay token de sesión en localStorage (`lia_access_token`). " +
              "Recargá la página o re-loguéate antes de aplicar otro delta.",
          );
          return;
        }
        const headers: Record<string, string> = {
          Authorization: `Bearer ${token.trim()}`,
        };
        const resp = await fetchImpl(statusUrl, { headers });
        if (!resp.ok) {
          const kind: AdditiveDeltaSseHealthInfo["kind"] =
            resp.status === 401 ? "auth_missing" : "http_error";
          reportFailure(
            kind,
            kind === "auth_missing"
              ? `/status devolvió 401 — el token expiró. Re-loguéate.`
              : `/status devolvió HTTP ${resp.status}. El servidor o la base ` +
                  "pueden estar caídos; verificá logs.",
            resp.status,
          );
          return;
        }
        const data = (await resp.json()) as { job?: Record<string, unknown> };
        if (!data || !data.job) {
          // job_not_found — the row vanished. Treat as a failure (it's
          // anomalous and the operator should know) instead of silently
          // looping forever.
          reportFailure(
            "http_error",
            "El job desapareció de la base. Pudo haber sido recogido por " +
              "`phase2-reap-stalled-jobs` o eliminado manualmente.",
            resp.status,
          );
          return;
        }
        const jobRow = data.job as Record<string, unknown>;
        reportSuccess((jobRow.last_heartbeat_at as string | null) ?? null);
        handleMessage(JSON.stringify(jobRow));
      } catch (err) {
        reportFailure(
          "network_error",
          `Fetch a /status falló: ${err instanceof Error ? err.message : String(err)}`,
        );
      }
    };
    void tick();
    pollingTimer = setInterval(tick, pollingIntervalMs);
  }

  function dispatchProgressEvent(eventType: string, raw: string): void {
    if (!handlers.onProgressEvent) return;
    try {
      const parsed = JSON.parse(raw);
      if (!parsed || typeof parsed !== "object") return;
      const payload =
        (parsed as { payload?: unknown }).payload &&
        typeof (parsed as { payload?: unknown }).payload === "object"
          ? ((parsed as { payload: Record<string, unknown> }).payload)
          : {};
      const tsUtc = String((parsed as { ts_utc?: unknown }).ts_utc ?? "");
      handlers.onProgressEvent({ eventType, tsUtc, payload });
    } catch {
      /* drop malformed event silently — the snapshot path is what
         drives state transitions; per-event progress is enrichment */
    }
  }

  function attemptConnect(): void {
    if (closed) return;
    emitStatus(reconnects === 0 ? "connecting" : "reconnecting");
    try {
      current = esFactory(buildEventsUrl());
    } catch {
      scheduleReconnect();
      return;
    }
    current.addEventListener("open", () => {
      reconnects = 0;
      emitStatus("connected");
    });
    // Initial snapshot drives the row-state machine (queued → running →
    // terminal). The backend sends it as an `event: snapshot` line.
    current.addEventListener("snapshot", (ev) => {
      handleMessage((ev as MessageEvent).data);
    });
    // Per-stage worker events also drive the row state — they carry the
    // same job-row shape under `event.payload`. Keep the snapshot logic
    // in sync by treating worker.stage / worker.done / worker.failed as
    // additional state transitions.
    for (const workerEventType of [
      "ingest.delta.worker.stage",
      "ingest.delta.worker.heartbeat",
      "ingest.delta.worker.done",
      "ingest.delta.worker.failed",
    ]) {
      current.addEventListener(workerEventType, (ev) => {
        const raw = (ev as MessageEvent).data;
        // Worker events carry only deltas in payload; pull current row
        // freshness from the next polling tick or the next snapshot.
        // Still surface them as progress events so the live-activity
        // line updates ("Stage: supabase").
        dispatchProgressEvent(workerEventType, raw);
        if (workerEventType === "ingest.delta.worker.done") {
          // Force a terminal transition without waiting for the row;
          // synthesise a minimal completed snapshot so the UI flips.
          handlers.onTerminal?.({
            jobId,
            stage: "completed",
            progressPct: 100,
            lastHeartbeatAt: null,
            cancelRequested: false,
            reportJson: null,
          });
          close();
        } else if (workerEventType === "ingest.delta.worker.failed") {
          handlers.onTerminal?.({
            jobId,
            stage: "failed",
            progressPct: 0,
            lastHeartbeatAt: null,
            cancelRequested: false,
            reportJson: null,
          });
          close();
        }
      });
    }
    // Per-doc + per-phase progress events. These never carry the row
    // shape; surface them via onProgressEvent only.
    for (const enrichmentEventType of [
      "subtopic.ingest.classified",
      "subtopic.graph.binding_built",
      "subtopic.graph.bindings_summary",
      "ingest.delta.classifier.summary",
      "ingest.delta.parity.check.start",
      "ingest.delta.parity.check.done",
      "ingest.delta.parity.check.mismatch",
      "ingest.delta.falkor.indexes_verified",
      "ingest.delta.falkor.indexes_skipped",
      "ingest.delta.shortcut.computed",
      "ingest.delta.plan.computed",
    ]) {
      current.addEventListener(enrichmentEventType, (ev) => {
        dispatchProgressEvent(enrichmentEventType, (ev as MessageEvent).data);
      });
    }
    // Catch-all for un-typed events.
    current.addEventListener("message", (ev) => {
      handleMessage((ev as MessageEvent).data);
    });
    current.addEventListener("error", () => {
      if (closed) return;
      current?.close();
      current = null;
      scheduleReconnect();
    });
  }

  function scheduleReconnect(): void {
    if (closed) return;
    if (reconnects >= maxReconnects) {
      startPolling();
      return;
    }
    reconnects += 1;
    const backoff = Math.min(30_000, 500 * 2 ** (reconnects - 1));
    emitStatus("reconnecting");
    reconnectTimer = setTimeout(() => attemptConnect(), backoff);
  }

  function close(): void {
    if (closed) return;
    closed = true;
    if (current) {
      current.close();
      current = null;
    }
    if (pollingTimer) {
      clearInterval(pollingTimer);
      pollingTimer = null;
    }
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    emitStatus("closed");
  }

  attemptConnect();

  return { close };
}
