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

export interface AdditiveDeltaSseHandlers {
  onSnapshot: (event: AdditiveDeltaSseEvent) => void;
  onStatusChange?: (status: AdditiveDeltaSseStatus) => void;
  onTerminal?: (event: AdditiveDeltaSseEvent) => void;
}

export interface AdditiveDeltaSseOptions {
  maxReconnects?: number;
  pollingIntervalMs?: number;
  eventSourceFactory?: (url: string) => EventSource;
  fetchImpl?: typeof fetch;
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
  // EventSource can't send Authorization headers, and the events endpoint
  // is admin-gated with Bearer auth. Skip SSE entirely for v1 and go
  // straight to fast polling. maxReconnects=0 means attemptConnect will
  // immediately schedule a retry, which then falls through to polling.
  const maxReconnects = opts.maxReconnects ?? 0;
  const pollingIntervalMs = opts.pollingIntervalMs ?? 2_000;
  const esFactory =
    opts.eventSourceFactory ??
    ((url: string) => new EventSource(url));
  const fetchImpl = opts.fetchImpl ?? fetch.bind(globalThis);

  const eventsUrl = `/api/ingest/additive/events?job_id=${encodeURIComponent(jobId)}`;
  const statusUrl = `/api/ingest/additive/status?job_id=${encodeURIComponent(jobId)}`;

  let reconnects = 0;
  let closed = false;
  let current: EventSource | null = null;
  let pollingTimer: ReturnType<typeof setInterval> | null = null;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

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
        const headers: Record<string, string> = {};
        if (token && token.trim()) {
          headers["Authorization"] = `Bearer ${token.trim()}`;
        }
        const resp = await fetchImpl(statusUrl, { headers });
        if (!resp.ok) return;
        const data = (await resp.json()) as { job?: Record<string, unknown> };
        if (!data || !data.job) return;
        handleMessage(JSON.stringify(data.job));
      } catch {
        /* transient — next tick will retry */
      }
    };
    void tick();
    pollingTimer = setInterval(tick, pollingIntervalMs);
  }

  function attemptConnect(): void {
    if (closed) return;
    emitStatus(reconnects === 0 ? "connecting" : "reconnecting");
    try {
      current = esFactory(eventsUrl);
    } catch {
      scheduleReconnect();
      return;
    }
    current.addEventListener("open", () => {
      reconnects = 0;
      emitStatus("connected");
    });
    current.addEventListener("snapshot", (ev) => {
      handleMessage((ev as MessageEvent).data);
    });
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
