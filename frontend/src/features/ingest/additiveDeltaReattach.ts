/**
 * LocalStorage-backed reattach for the additive-corpus-v1 apply flow.
 *
 * Per plan §8.D: persist the ``job_id`` on successful Apply POST, clear it
 * when a terminal stage is observed. On mount the controller consults BOTH
 * this store AND the server's /live endpoint; server-truth wins.
 */

const STORAGE_KEY = "additive-delta.jobId";

export interface AdditiveDeltaReattachStore {
  get: () => string | null;
  set: (jobId: string) => void;
  clear: () => void;
}

export function createAdditiveDeltaReattachStore(
  storage?: Storage | null,
): AdditiveDeltaReattachStore {
  // Differentiate "not passed" (use default localStorage) from "explicitly
  // null" (caller wants the noop store, e.g. SSR / tests). `??` collapsed
  // both — that masked a real test for years until it landed in the
  // curated health suite.
  const resolved =
    storage === undefined
      ? typeof localStorage !== "undefined"
        ? localStorage
        : null
      : storage;
  if (!resolved) {
    // Non-browser / disabled storage — return a noop store so mount logic
    // stays linear. Tests can inject a fake Storage.
    return {
      get: () => null,
      set: () => undefined,
      clear: () => undefined,
    };
  }
  return {
    get: () => {
      try {
        const raw = resolved.getItem(STORAGE_KEY);
        return raw && raw.trim() ? raw.trim() : null;
      } catch {
        return null;
      }
    },
    set: (jobId: string) => {
      try {
        if (jobId && jobId.trim()) {
          resolved.setItem(STORAGE_KEY, jobId.trim());
        }
      } catch {
        /* swallow — reattach is best-effort */
      }
    },
    clear: () => {
      try {
        resolved.removeItem(STORAGE_KEY);
      } catch {
        /* swallow */
      }
    },
  };
}

/**
 * Reconcile local-storage jobId against the server-truth live job. Returns
 * the job_id the controller should bind to (or null to mount Idle).
 *
 * * server-live ∧ local-same → local
 * * server-live ∧ local-differs → server (clear stale local)
 * * server-live ∧ no-local → server (write local)
 * * no-server ∧ local-exists → local (controller then probes /status —
 *   if terminal, clears local and mounts Terminal)
 * * no-server ∧ no-local → null (mount Idle)
 */
export function reconcileReattachSource(opts: {
  serverLiveJobId: string | null;
  localJobId: string | null;
  store: AdditiveDeltaReattachStore;
}): string | null {
  const { serverLiveJobId, localJobId, store } = opts;
  if (serverLiveJobId) {
    if (localJobId !== serverLiveJobId) {
      store.set(serverLiveJobId);
    }
    return serverLiveJobId;
  }
  if (localJobId) return localJobId;
  return null;
}

export const ADDITIVE_DELTA_STORAGE_KEY = STORAGE_KEY;
