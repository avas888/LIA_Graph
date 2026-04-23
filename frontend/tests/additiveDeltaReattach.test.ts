/**
 * @vitest-environment jsdom
 */
import { describe, expect, it } from "vitest";

import {
  ADDITIVE_DELTA_STORAGE_KEY,
  createAdditiveDeltaReattachStore,
  reconcileReattachSource,
} from "@/features/ingest/additiveDeltaReattach";

class FakeStorage implements Storage {
  private map = new Map<string, string>();
  get length(): number {
    return this.map.size;
  }
  clear(): void {
    this.map.clear();
  }
  getItem(key: string): string | null {
    return this.map.get(key) ?? null;
  }
  key(index: number): string | null {
    return Array.from(this.map.keys())[index] ?? null;
  }
  removeItem(key: string): void {
    this.map.delete(key);
  }
  setItem(key: string, value: string): void {
    this.map.set(key, value);
  }
}

describe("reattach store", () => {
  // (a) empty store — get returns null.
  it("empty store returns null", () => {
    const store = createAdditiveDeltaReattachStore(new FakeStorage());
    expect(store.get()).toBeNull();
  });

  // (b) set/get round-trip.
  it("persists and retrieves a job_id", () => {
    const storage = new FakeStorage();
    const store = createAdditiveDeltaReattachStore(storage);
    store.set("job_abc123");
    expect(store.get()).toBe("job_abc123");
    expect(storage.getItem(ADDITIVE_DELTA_STORAGE_KEY)).toBe("job_abc123");
  });

  // (c) clear removes the key.
  it("clears the persisted job_id", () => {
    const storage = new FakeStorage();
    const store = createAdditiveDeltaReattachStore(storage);
    store.set("job_X");
    store.clear();
    expect(store.get()).toBeNull();
  });

  // (d) server-live wins over stale localStorage.
  it("server-live job_id wins over stale local storage", () => {
    const storage = new FakeStorage();
    const store = createAdditiveDeltaReattachStore(storage);
    store.set("stale_local");
    const resolved = reconcileReattachSource({
      serverLiveJobId: "server_fresh",
      localJobId: store.get(),
      store,
    });
    expect(resolved).toBe("server_fresh");
    expect(store.get()).toBe("server_fresh");
  });

  // (e) no-server + local points to no-op returns local (controller probes status).
  it("returns local when server has no live job", () => {
    const storage = new FakeStorage();
    const store = createAdditiveDeltaReattachStore(storage);
    store.set("job_only_local");
    const resolved = reconcileReattachSource({
      serverLiveJobId: null,
      localJobId: store.get(),
      store,
    });
    expect(resolved).toBe("job_only_local");
  });

  // (extra) disabled storage yields no-op store.
  it("falls back to noop store when Storage is null", () => {
    const store = createAdditiveDeltaReattachStore(null);
    store.set("x");
    expect(store.get()).toBeNull();
  });
});
