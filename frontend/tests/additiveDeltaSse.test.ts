/**
 * @vitest-environment jsdom
 *
 * Behavior tests for the additive-delta SSE+polling subscriber.
 *
 * Motivated by a 2026-04-26 incident where the operator's apply succeeded
 * end-to-end (worker emitted ``ingest.delta.worker.done``) but the GUI
 * stayed pegged on "EN COLA · sin heartbeat" because the SSE channel
 * closed after its single snapshot and the polling fallback's silent
 * error-swallow + ambiguous status semantics didn't surface anything.
 *
 * Earlier code-review audits passed because the unit tests covered pure
 * helpers (VM mapping, reattach reconcile) but never exercised the
 * subscribe-then-transition behavior end-to-end. These tests close that
 * gap. If the polling-then-terminal path regresses, this file catches it
 * before an operator stares at a stuck spinner.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  subscribeJobEvents,
  type AdditiveDeltaSseEvent,
  type AdditiveDeltaSseStatus,
} from "@/features/ingest/additiveDeltaSse";

type Listener = (ev: Event | MessageEvent) => void;

class FakeEventSource {
  private listeners = new Map<string, Set<Listener>>();
  closed = false;
  constructor(public url: string) {}
  addEventListener(type: string, listener: Listener): void {
    if (!this.listeners.has(type)) this.listeners.set(type, new Set());
    this.listeners.get(type)!.add(listener);
  }
  close(): void {
    this.closed = true;
  }
  /** Test helper: synthesize an SSE event. */
  emit(type: string, data?: string): void {
    const lst = this.listeners.get(type);
    if (!lst) return;
    const ev =
      data !== undefined
        ? ({ data } as MessageEvent)
        : ({} as Event);
    for (const l of lst) l(ev);
  }
}

interface TestHarness {
  events: AdditiveDeltaSseEvent[];
  statuses: AdditiveDeltaSseStatus[];
  terminals: AdditiveDeltaSseEvent[];
  sources: FakeEventSource[];
  fetchCalls: string[];
  fetchResponses: Array<() => Response | Promise<Response>>;
}

function makeHarness(
  fetchResponses: Array<() => Response | Promise<Response>>,
): TestHarness {
  return {
    events: [],
    statuses: [],
    terminals: [],
    sources: [],
    fetchCalls: [],
    fetchResponses,
  };
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function jobRow(stage: string, extras: Record<string, unknown> = {}) {
  return {
    job_id: "job_test_001",
    lock_target: "production",
    stage,
    delta_id: "delta_x",
    progress_pct: stage === "completed" ? 100 : 10,
    started_at: "2026-04-26T14:00:00Z",
    last_heartbeat_at: null,
    completed_at: stage === "completed" ? "2026-04-26T14:00:18Z" : null,
    created_by: "test",
    cancel_requested: false,
    error_class: null,
    error_message: null,
    report_json: stage === "completed"
      ? {
          delta_id: "delta_x",
          target: "production",
          sink_result: {
            documents_added: 3,
            documents_modified: 0,
            documents_retired: 0,
            chunks_written: 12,
            chunks_deleted: 0,
            edges_written: 5,
            edges_deleted: 0,
          },
        }
      : null,
    ...extras,
  };
}

beforeEach(() => {
  vi.useFakeTimers();
  // Seed an auth token so the polling layer doesn't immediately fire
  // its auth_missing health issue. Tests that exercise the
  // auth-missing path explicitly remove it.
  window.localStorage.setItem("lia_access_token", "fake-token");
});

afterEach(() => {
  vi.useRealTimers();
  window.localStorage.removeItem("lia_access_token");
});

describe("subscribeJobEvents — SSE + polling fallback", () => {
  it("regression: SSE closes immediately, polling picks up the terminal transition", async () => {
    // The exact scenario the operator hit. v1 SSE handler sends a single
    // snapshot then closes; the JS subscriber falls back to polling.
    // Polling tick 1 returns queued; polling tick 2 returns completed.
    // onTerminal MUST fire so the terminal banner renders.
    const h = makeHarness([
      () => jsonResponse({ ok: true, job: jobRow("queued") }),
      () => jsonResponse({ ok: true, job: jobRow("queued") }),
      () => jsonResponse({ ok: true, job: jobRow("completed") }),
    ]);

    subscribeJobEvents(
      "job_test_001",
      {
        onSnapshot: (ev) => h.events.push(ev),
        onStatusChange: (s) => h.statuses.push(s),
        onTerminal: (ev) => h.terminals.push(ev),
      },
      {
        maxReconnects: 0,
        pollingIntervalMs: 100,
        eventSourceFactory: (url) => {
          const src = new FakeEventSource(url);
          h.sources.push(src);
          // Simulate the v1 endpoint behavior: single snapshot then error
          // (the connection close manifests as an "error" event in the
          // EventSource API, which routes us to scheduleReconnect →
          // startPolling since maxReconnects=0).
          queueMicrotask(() => {
            src.emit("snapshot", JSON.stringify(jobRow("queued")));
            src.emit("error");
          });
          return src as unknown as EventSource;
        },
        fetchImpl: async (..._args: unknown[]) => {
          const factory = h.fetchResponses.shift() ?? h.fetchResponses[0];
          return factory();
        },
      },
    );

    // Drain the microtask queue so the SSE error fires.
    await vi.advanceTimersByTimeAsync(0);
    // Polling tick 1 (queued).
    await vi.advanceTimersByTimeAsync(110);
    // Polling tick 2 (still queued).
    await vi.advanceTimersByTimeAsync(110);
    // Polling tick 3 (completed) — terminal fires.
    await vi.advanceTimersByTimeAsync(110);

    // The snapshot from SSE + 3 from polling = 4 total.
    expect(h.events.length).toBeGreaterThanOrEqual(2);
    // Terminal callback fired exactly once with the completed snapshot.
    expect(h.terminals).toHaveLength(1);
    expect(h.terminals[0].stage).toBe("completed");
    expect(h.terminals[0].reportJson).toMatchObject({
      sink_result: { documents_added: 3 },
    });
    // Status sequence eventually transitioned to closed (after terminal).
    expect(h.statuses).toContain("polling");
    expect(h.statuses).toContain("closed");
  });

  it("polling fallback survives HTTP errors without crashing or marking terminal", async () => {
    // /status returns 500 repeatedly. Polling must keep ticking; it must
    // NOT call onTerminal (we have no signal that the job ended); it must
    // NOT crash the subscriber.
    const h = makeHarness([
      () => new Response("oops", { status: 500 }),
      () => new Response("oops", { status: 500 }),
      () => new Response("oops", { status: 500 }),
    ]);

    subscribeJobEvents(
      "job_test_001",
      {
        onSnapshot: (ev) => h.events.push(ev),
        onStatusChange: (s) => h.statuses.push(s),
        onTerminal: (ev) => h.terminals.push(ev),
      },
      {
        maxReconnects: 0,
        pollingIntervalMs: 100,
        eventSourceFactory: (url) => {
          const src = new FakeEventSource(url);
          h.sources.push(src);
          queueMicrotask(() => src.emit("error"));
          return src as unknown as EventSource;
        },
        fetchImpl: async () => {
          const factory = h.fetchResponses.shift() ?? h.fetchResponses[0];
          return factory();
        },
      },
    );

    await vi.advanceTimersByTimeAsync(0);
    await vi.advanceTimersByTimeAsync(350);

    expect(h.events).toHaveLength(0);
    expect(h.terminals).toHaveLength(0);
    expect(h.statuses).toContain("polling");
  });

  it("polling fallback ignores malformed JSON without firing snapshot", async () => {
    // Mutable-response pattern: every tick reads the current factory.
    // Lets us swap mid-test so we can isolate "malformed → discarded"
    // from "completed → terminal" without depending on tick-vs-interval
    // timing of the immediate `void tick()`.
    const h = makeHarness([]);
    let nextResponse: () => Response | Promise<Response> = () =>
      new Response("not json at all", { status: 200 });

    subscribeJobEvents(
      "job_test_001",
      {
        onSnapshot: (ev) => h.events.push(ev),
        onStatusChange: (s) => h.statuses.push(s),
        onTerminal: (ev) => h.terminals.push(ev),
      },
      {
        maxReconnects: 0,
        pollingIntervalMs: 100,
        eventSourceFactory: (url) => {
          const src = new FakeEventSource(url);
          h.sources.push(src);
          queueMicrotask(() => src.emit("error"));
          return src as unknown as EventSource;
        },
        fetchImpl: async () => nextResponse(),
      },
    );

    // Drain microtasks: SSE error → startPolling → immediate void tick
    // hits the malformed response. JSON parse throws, gets swallowed,
    // no snapshot fires.
    await vi.advanceTimersByTimeAsync(0);
    expect(h.events).toHaveLength(0);
    expect(h.terminals).toHaveLength(0);

    // Swap the response. Next polling tick will see "completed" and
    // fire the terminal callback.
    nextResponse = () =>
      jsonResponse({ ok: true, job: jobRow("completed") });
    await vi.advanceTimersByTimeAsync(110);

    expect(h.terminals).toHaveLength(1);
    expect(h.terminals[0].stage).toBe("completed");
  });

  it("polling fallback handles {ok:true, job:null} (job_not_found) without crashing", async () => {
    const h = makeHarness([]);
    let nextResponse: () => Response | Promise<Response> = () =>
      jsonResponse({ ok: true, job: null });

    subscribeJobEvents(
      "job_test_001",
      {
        onSnapshot: (ev) => h.events.push(ev),
        onTerminal: (ev) => h.terminals.push(ev),
      },
      {
        maxReconnects: 0,
        pollingIntervalMs: 100,
        eventSourceFactory: (url) => {
          const src = new FakeEventSource(url);
          h.sources.push(src);
          queueMicrotask(() => src.emit("error"));
          return src as unknown as EventSource;
        },
        fetchImpl: async () => nextResponse(),
      },
    );

    // Immediate tick consumes {job: null}: handler bails on `if (!data.job) return`,
    // no snapshot fires.
    await vi.advanceTimersByTimeAsync(0);
    expect(h.events).toHaveLength(0);
    expect(h.terminals).toHaveLength(0);

    // Swap to a real terminal row; next tick fires onTerminal.
    nextResponse = () =>
      jsonResponse({ ok: true, job: jobRow("completed") });
    await vi.advanceTimersByTimeAsync(110);
    expect(h.terminals).toHaveLength(1);
  });

  it("SSE-delivered terminal snapshot fires onTerminal without polling", async () => {
    // When the SSE channel does deliver a snapshot whose stage is already
    // terminal (e.g., user reattaches to an already-completed job), we
    // should fire onTerminal and close — never start polling.
    const h = makeHarness([]);

    subscribeJobEvents(
      "job_test_001",
      {
        onSnapshot: (ev) => h.events.push(ev),
        onStatusChange: (s) => h.statuses.push(s),
        onTerminal: (ev) => h.terminals.push(ev),
      },
      {
        maxReconnects: 5, // give SSE room — it should succeed
        pollingIntervalMs: 100,
        eventSourceFactory: (url) => {
          const src = new FakeEventSource(url);
          h.sources.push(src);
          queueMicrotask(() => {
            src.emit("snapshot", JSON.stringify(jobRow("completed")));
          });
          return src as unknown as EventSource;
        },
        fetchImpl: async () => {
          throw new Error("polling should never be reached");
        },
      },
    );

    await vi.advanceTimersByTimeAsync(0);
    await vi.advanceTimersByTimeAsync(150);

    expect(h.terminals).toHaveLength(1);
    expect(h.terminals[0].stage).toBe("completed");
    expect(h.statuses).toContain("closed");
    // SSE was closed after the terminal fired.
    expect(h.sources[0].closed).toBe(true);
  });

  it("onTerminal fires exactly once across multiple terminal-stage snapshots", async () => {
    // Defensive: even if /status returns "completed" multiple ticks in a
    // row (operator hovering on the page after the job ended), the
    // terminal callback must not fire twice. The subscriber closes after
    // the first terminal so subsequent ticks won't fire.
    const h = makeHarness([
      () => jsonResponse({ ok: true, job: jobRow("completed") }),
      () => jsonResponse({ ok: true, job: jobRow("completed") }),
      () => jsonResponse({ ok: true, job: jobRow("completed") }),
    ]);

    subscribeJobEvents(
      "job_test_001",
      {
        onSnapshot: (ev) => h.events.push(ev),
        onTerminal: (ev) => h.terminals.push(ev),
      },
      {
        maxReconnects: 0,
        pollingIntervalMs: 100,
        eventSourceFactory: (url) => {
          const src = new FakeEventSource(url);
          h.sources.push(src);
          queueMicrotask(() => src.emit("error"));
          return src as unknown as EventSource;
        },
        fetchImpl: async () => {
          const factory = h.fetchResponses.shift() ?? h.fetchResponses[0];
          return factory();
        },
      },
    );

    await vi.advanceTimersByTimeAsync(0);
    await vi.advanceTimersByTimeAsync(350);

    expect(h.terminals).toHaveLength(1);
  });

  it("close() is idempotent and stops both SSE + polling timers", async () => {
    const h = makeHarness([
      () => jsonResponse({ ok: true, job: jobRow("queued") }),
      () => jsonResponse({ ok: true, job: jobRow("queued") }),
    ]);

    const handle = subscribeJobEvents(
      "job_test_001",
      {
        onSnapshot: (ev) => h.events.push(ev),
        onStatusChange: (s) => h.statuses.push(s),
      },
      {
        maxReconnects: 0,
        pollingIntervalMs: 100,
        eventSourceFactory: (url) => {
          const src = new FakeEventSource(url);
          h.sources.push(src);
          queueMicrotask(() => src.emit("error"));
          return src as unknown as EventSource;
        },
        fetchImpl: async () => {
          const factory = h.fetchResponses.shift() ?? h.fetchResponses[0];
          return factory();
        },
      },
    );

    await vi.advanceTimersByTimeAsync(0);
    await vi.advanceTimersByTimeAsync(110);
    const beforeCloseCount = h.events.length;

    handle.close();
    handle.close(); // second call must be a no-op

    await vi.advanceTimersByTimeAsync(500);
    // No new snapshots after close.
    expect(h.events.length).toBe(beforeCloseCount);
    expect(h.statuses[h.statuses.length - 1]).toBe("closed");
  });

  // ── Fase A: health-detection regression set ────────────────────────

  it("fires onHealthIssue with kind=auth_missing when localStorage has no token", async () => {
    const h = makeHarness([]);
    const healthIssues: import("@/features/ingest/additiveDeltaSse").AdditiveDeltaSseHealthInfo[] = [];
    let nextResponse: () => Response | Promise<Response> = () =>
      jsonResponse({ ok: true, job: jobRow("queued") });

    // Make sure localStorage is empty.
    window.localStorage.removeItem("lia_access_token");

    subscribeJobEvents(
      "job_test_001",
      {
        onSnapshot: (ev) => h.events.push(ev),
        onHealthIssue: (info) => healthIssues.push(info),
      },
      {
        maxReconnects: 0,
        pollingIntervalMs: 100,
        consecutiveFailureThreshold: 1,
        eventSourceFactory: (url) => {
          const src = new FakeEventSource(url);
          h.sources.push(src);
          queueMicrotask(() => src.emit("error"));
          return src as unknown as EventSource;
        },
        fetchImpl: async () => nextResponse(),
      },
    );

    await vi.advanceTimersByTimeAsync(0);
    expect(healthIssues).toHaveLength(1);
    expect(healthIssues[0].kind).toBe("auth_missing");
    expect(healthIssues[0].message).toContain("lia_access_token");
    expect(h.events).toHaveLength(0);
  });

  it("fires onHealthIssue with kind=http_error after N consecutive 500s", async () => {
    const h = makeHarness([]);
    const healthIssues: import("@/features/ingest/additiveDeltaSse").AdditiveDeltaSseHealthInfo[] = [];
    window.localStorage.setItem("lia_access_token", "fake-token");
    let nextResponse: () => Response | Promise<Response> = () =>
      new Response("oops", { status: 500 });

    subscribeJobEvents(
      "job_test_001",
      {
        onSnapshot: (ev) => h.events.push(ev),
        onHealthIssue: (info) => healthIssues.push(info),
      },
      {
        maxReconnects: 0,
        pollingIntervalMs: 100,
        consecutiveFailureThreshold: 3,
        eventSourceFactory: (url) => {
          const src = new FakeEventSource(url);
          h.sources.push(src);
          queueMicrotask(() => src.emit("error"));
          return src as unknown as EventSource;
        },
        fetchImpl: async () => nextResponse(),
      },
    );

    // Tick 1 (immediate via void tick): 1 failure, below threshold.
    await vi.advanceTimersByTimeAsync(0);
    expect(healthIssues).toHaveLength(0);
    // Tick 2 (interval): 2 failures, still below.
    await vi.advanceTimersByTimeAsync(110);
    expect(healthIssues).toHaveLength(0);
    // Tick 3: hits threshold, fires.
    await vi.advanceTimersByTimeAsync(110);
    expect(healthIssues).toHaveLength(1);
    expect(healthIssues[0].kind).toBe("http_error");
    expect(healthIssues[0].status).toBe(500);
    expect(healthIssues[0].attemptsSinceLastSuccess).toBe(3);
    // Tick 4: still failing, fires again so the chip's relative-time
    // stays fresh (avoid silent stuck states).
    await vi.advanceTimersByTimeAsync(110);
    expect(healthIssues).toHaveLength(2);
    expect(healthIssues[1].attemptsSinceLastSuccess).toBe(4);
  });

  it("401 from /status fires onHealthIssue with kind=auth_missing (token expired)", async () => {
    const h = makeHarness([]);
    const healthIssues: import("@/features/ingest/additiveDeltaSse").AdditiveDeltaSseHealthInfo[] = [];
    window.localStorage.setItem("lia_access_token", "expired-token");
    let nextResponse: () => Response | Promise<Response> = () =>
      new Response("unauthorized", { status: 401 });

    subscribeJobEvents(
      "job_test_001",
      {
        onSnapshot: (ev) => h.events.push(ev),
        onHealthIssue: (info) => healthIssues.push(info),
      },
      {
        maxReconnects: 0,
        pollingIntervalMs: 100,
        consecutiveFailureThreshold: 1,
        eventSourceFactory: (url) => {
          const src = new FakeEventSource(url);
          h.sources.push(src);
          queueMicrotask(() => src.emit("error"));
          return src as unknown as EventSource;
        },
        fetchImpl: async () => nextResponse(),
      },
    );

    await vi.advanceTimersByTimeAsync(0);
    expect(healthIssues).toHaveLength(1);
    expect(healthIssues[0].kind).toBe("auth_missing");
    expect(healthIssues[0].status).toBe(401);
  });

  it("network error (fetch throws) fires onHealthIssue with kind=network_error", async () => {
    const h = makeHarness([]);
    const healthIssues: import("@/features/ingest/additiveDeltaSse").AdditiveDeltaSseHealthInfo[] = [];
    window.localStorage.setItem("lia_access_token", "fake-token");

    subscribeJobEvents(
      "job_test_001",
      {
        onSnapshot: (ev) => h.events.push(ev),
        onHealthIssue: (info) => healthIssues.push(info),
      },
      {
        maxReconnects: 0,
        pollingIntervalMs: 100,
        consecutiveFailureThreshold: 1,
        eventSourceFactory: (url) => {
          const src = new FakeEventSource(url);
          h.sources.push(src);
          queueMicrotask(() => src.emit("error"));
          return src as unknown as EventSource;
        },
        fetchImpl: async () => {
          throw new TypeError("fetch failed");
        },
      },
    );

    await vi.advanceTimersByTimeAsync(0);
    expect(healthIssues).toHaveLength(1);
    expect(healthIssues[0].kind).toBe("network_error");
    expect(healthIssues[0].message).toContain("fetch failed");
  });

  it("successful tick fires onHealthOk after a prior health issue", async () => {
    const h = makeHarness([]);
    const healthIssues: import("@/features/ingest/additiveDeltaSse").AdditiveDeltaSseHealthInfo[] = [];
    let healthOkCalls = 0;
    window.localStorage.setItem("lia_access_token", "fake-token");
    let nextResponse: () => Response | Promise<Response> = () =>
      new Response("oops", { status: 500 });

    subscribeJobEvents(
      "job_test_001",
      {
        onSnapshot: (ev) => h.events.push(ev),
        onHealthIssue: (info) => healthIssues.push(info),
        onHealthOk: () => {
          healthOkCalls += 1;
        },
      },
      {
        maxReconnects: 0,
        pollingIntervalMs: 100,
        consecutiveFailureThreshold: 1,
        eventSourceFactory: (url) => {
          const src = new FakeEventSource(url);
          h.sources.push(src);
          queueMicrotask(() => src.emit("error"));
          return src as unknown as EventSource;
        },
        fetchImpl: async () => nextResponse(),
      },
    );

    await vi.advanceTimersByTimeAsync(0);
    expect(healthIssues).toHaveLength(1);

    // Recover: server returns a fresh row with current heartbeat.
    nextResponse = () =>
      jsonResponse({
        ok: true,
        job: jobRow("parsing", {
          last_heartbeat_at: new Date().toISOString(),
        }),
      });
    await vi.advanceTimersByTimeAsync(110);
    expect(healthOkCalls).toBe(1);
    expect(h.events).toHaveLength(1);
  });

  it("stale heartbeat fires onHealthIssue with kind=stall even on a clean snapshot", async () => {
    // The 2026-04-26 incident: /status returns 200 and the row exists,
    // but the worker thread is wedged and `last_heartbeat_at` keeps
    // getting older. We must not stay silent.
    const h = makeHarness([]);
    const healthIssues: import("@/features/ingest/additiveDeltaSse").AdditiveDeltaSseHealthInfo[] = [];
    window.localStorage.setItem("lia_access_token", "fake-token");
    const fixedNow = 1_700_000_000_000;
    const staleHeartbeat = new Date(fixedNow - 90_000).toISOString(); // 90s old
    let nextResponse: () => Response | Promise<Response> = () =>
      jsonResponse({
        ok: true,
        job: jobRow("parsing", { last_heartbeat_at: staleHeartbeat }),
      });

    subscribeJobEvents(
      "job_test_001",
      {
        onSnapshot: (ev) => h.events.push(ev),
        onHealthIssue: (info) => healthIssues.push(info),
      },
      {
        maxReconnects: 0,
        pollingIntervalMs: 100,
        staleHeartbeatThresholdMs: 60_000,
        nowMs: () => fixedNow,
        eventSourceFactory: (url) => {
          const src = new FakeEventSource(url);
          h.sources.push(src);
          queueMicrotask(() => src.emit("error"));
          return src as unknown as EventSource;
        },
        fetchImpl: async () => nextResponse(),
      },
    );

    await vi.advanceTimersByTimeAsync(0);
    expect(healthIssues).toHaveLength(1);
    expect(healthIssues[0].kind).toBe("stall");
    expect(healthIssues[0].staleHeartbeatMs).toBeGreaterThanOrEqual(60_000);
    expect(healthIssues[0].message).toContain("heartbeat");
  });

  it("emits status transitions in order: connecting/reconnecting → polling → closed", async () => {
    const h = makeHarness([
      () => jsonResponse({ ok: true, job: jobRow("completed") }),
    ]);

    subscribeJobEvents(
      "job_test_001",
      {
        onSnapshot: (ev) => h.events.push(ev),
        onStatusChange: (s) => h.statuses.push(s),
        onTerminal: (ev) => h.terminals.push(ev),
      },
      {
        maxReconnects: 0,
        pollingIntervalMs: 100,
        eventSourceFactory: (url) => {
          const src = new FakeEventSource(url);
          h.sources.push(src);
          queueMicrotask(() => src.emit("error"));
          return src as unknown as EventSource;
        },
        fetchImpl: async () => {
          const factory = h.fetchResponses.shift() ?? h.fetchResponses[0];
          return factory();
        },
      },
    );

    await vi.advanceTimersByTimeAsync(0);
    await vi.advanceTimersByTimeAsync(150);

    // The first status is "connecting" (SSE attempt). After the error
    // and maxReconnects=0, we go to "polling". After terminal we close.
    expect(h.statuses[0]).toBe("connecting");
    expect(h.statuses).toContain("polling");
    expect(h.statuses[h.statuses.length - 1]).toBe("closed");
  });
});
