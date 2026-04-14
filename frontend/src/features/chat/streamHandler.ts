// @ts-nocheck

/**
 * SSE streaming, event parsing, polling fallback, and request watchdog.
 * Extracted from requestController.ts during decouple-v1 Phase 4.
 */

// ── Constants ─────────────────────────────────────────────────

export const STREAM_INITIAL_TIMEOUT_MS = 12000;
export const STREAM_IDLE_TIMEOUT_MS = 45000;
export const CHAT_RUN_POLL_INTERVAL_MS = 750;
export const CHAT_RUN_POLL_TIMEOUT_MS = 45000;

// ── Types ─────────────────────────────────────────────────────

export type ChatStreamEvent = {
  event: string;
  id: string | null;
  data: unknown;
};

// ── Watchdog ──────────────────────────────────────────────────

export class RequestWatchdogError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "RequestWatchdogError";
  }
}

export function createRequestWatchdog({
  initialTimeoutMs,
  idleTimeoutMs,
}: {
  initialTimeoutMs: number;
  idleTimeoutMs: number;
}) {
  const controller = new AbortController();
  let timeoutId: number | null = null;
  let lastReason = "request_timeout";

  function clear(): void {
    if (timeoutId !== null) {
      window.clearTimeout(timeoutId);
      timeoutId = null;
    }
  }

  function arm(ms: number, reason: string): void {
    clear();
    lastReason = reason;
    timeoutId = window.setTimeout(() => {
      controller.abort(new RequestWatchdogError(reason));
    }, ms);
  }

  return {
    signal: controller.signal,
    start(): void {
      arm(initialTimeoutMs, "stream_initial_timeout");
    },
    touch(): void {
      arm(idleTimeoutMs, "stream_idle_timeout");
    },
    stop(): void {
      clear();
    },
    rethrowIfAborted(error: unknown): never {
      if (controller.signal.aborted) {
        const reason = controller.signal.reason;
        if (reason instanceof Error) throw reason;
        throw new RequestWatchdogError(String(reason || lastReason));
      }
      throw error instanceof Error ? error : new Error(String(error));
    },
  };
}

// ── Helpers ───────────────────────────────────────────────────

export function isRecoverableStreamError(error: unknown): boolean {
  const message =
    error && typeof error === "object" && "message" in error ? String((error as Error).message || "") : String(error || "");
  return [
    "stream_transport_unavailable",
    "stream_initial_timeout",
    "stream_idle_timeout",
    "stream_incomplete",
  ].includes(message.trim());
}

export function isEventStreamResponse(response: Response): boolean {
  return String(response.headers.get("Content-Type") || "")
    .toLowerCase()
    .includes("text/event-stream");
}

export function buildClientTurnId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `turn_${Date.now()}_${Math.random().toString(16).slice(2, 10)}`;
}

export async function readJsonPayload<T>(response: Response): Promise<T | null> {
  try {
    return (await response.json()) as T;
  } catch (_error) {
    return null;
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

// ── SSE consumer ──────────────────────────────────────────────

export async function consumeEventStream(
  response: Response,
  onEvent: (event: ChatStreamEvent) => Promise<void> | void,
  options: { onActivity?: () => void } = {},
): Promise<void> {
  const reader = response.body?.getReader();
  if (!reader) throw new Error("stream_body_missing");

  const decoder = new TextDecoder();
  let buffer = "";
  let eventName = "message";
  let eventId: string | null = null;
  let dataLines: string[] = [];

  async function flushEvent(): Promise<void> {
    if (dataLines.length === 0 && !eventId && eventName === "message") return;
    const rawData = dataLines.join("\n");
    let parsedData: unknown = null;
    if (rawData) {
      try {
        parsedData = JSON.parse(rawData);
      } catch (_error) {
        parsedData = rawData;
      }
    }
    await onEvent({ event: eventName || "message", id: eventId, data: parsedData });
    eventName = "message";
    eventId = null;
    dataLines = [];
  }

  while (true) {
    const { value, done } = await reader.read();
    options.onActivity?.();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done });

    let lineBreakIndex = buffer.indexOf("\n");
    while (lineBreakIndex >= 0) {
      const line = buffer.slice(0, lineBreakIndex).replace(/\r$/, "");
      buffer = buffer.slice(lineBreakIndex + 1);

      if (!line) {
        await flushEvent();
        lineBreakIndex = buffer.indexOf("\n");
        continue;
      }

      if (line.startsWith(":")) {
        lineBreakIndex = buffer.indexOf("\n");
        continue;
      }

      const separatorIndex = line.indexOf(":");
      const field = separatorIndex >= 0 ? line.slice(0, separatorIndex) : line;
      const rawValue = separatorIndex >= 0 ? line.slice(separatorIndex + 1).replace(/^ /, "") : "";

      if (field === "event") eventName = rawValue || "message";
      else if (field === "id") eventId = rawValue || null;
      else if (field === "data") dataLines.push(rawValue);

      lineBreakIndex = buffer.indexOf("\n");
    }

    if (done) break;
  }

  if (buffer.trim()) dataLines.push(buffer.replace(/\r$/, ""));
  await flushEvent();
}

// ── Polling fallback ──────────────────────────────────────────

export async function waitForChatRunCompletion(
  chatRunId: string,
  {
    timeoutMs = CHAT_RUN_POLL_TIMEOUT_MS,
    pollIntervalMs = CHAT_RUN_POLL_INTERVAL_MS,
  }: { timeoutMs?: number; pollIntervalMs?: number } = {},
): Promise<{ response: Response; data: Record<string, unknown> | null }> {
  const deadline = Date.now() + Math.max(1000, timeoutMs);
  let lastResponse: Response | null = null;
  let lastData: Record<string, unknown> | null = null;

  while (Date.now() < deadline) {
    const response = await fetch(`/api/chat/runs/${encodeURIComponent(chatRunId)}`);
    const data = await readJsonPayload<Record<string, unknown>>(response);
    lastResponse = response;
    lastData = data;
    if (response.status !== 202) return { response, data };
    await sleep(pollIntervalMs);
  }

  if (lastResponse) return { response: lastResponse, data: lastData };

  const timeoutResponse = new Response(
    JSON.stringify({
      ok: false,
      chat_run_id: chatRunId,
      error: {
        code: "CHAT_RUN_TIMEOUT",
        message: "La ejecución sigue en curso. Usa reintentar para consultar nuevamente.",
      },
    }),
    { status: 504, headers: { "Content-Type": "application/json" } },
  );
  return {
    response: timeoutResponse,
    data: (await readJsonPayload<Record<string, unknown>>(timeoutResponse.clone())) || null,
  };
}
