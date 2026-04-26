/**
 * @vitest-environment jsdom
 *
 * Tests for the persistent corpus health dashboard (Fase D).
 *
 * Covers:
 * - Renders four metric cards from the snapshot.
 * - Tone is derived correctly per metric (ok / warning / danger / neutral).
 * - Refresh button re-fetches.
 * - Auto-refresh interval ticks.
 * - HTTP failure surfaces a visible error, not silent.
 * - destroy() clears the interval.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  createCorpusHealthCard,
  type CorpusHealthSnapshot,
} from "@/shared/ui/organisms/corpusHealthCard";

function makeSnapshot(over: Partial<CorpusHealthSnapshot> = {}): CorpusHealthSnapshot {
  return {
    generation: {
      id: "gen_active_rolling",
      activated_at: new Date(Date.now() - 600_000).toISOString(),
      documents: 1322,
      chunks: 30859,
      knowledge_class_counts: {},
    },
    parity: { ok: true, supabase_docs: 1322, falkor_docs: 1322, supabase_chunks: 30859, falkor_articles: 1322, supabase_edges: 3247, falkor_edges: 3247, mismatches: [] },
    embeddings: { pending_chunks: 0, pct_complete: 100 },
    last_delta: {
      job_id: "job_x",
      delta_id: "delta_x",
      completed_at: new Date(Date.now() - 120_000).toISOString(),
      started_at: new Date(Date.now() - 180_000).toISOString(),
      target: "production",
      documents_added: 3,
      documents_modified: 0,
      documents_retired: 0,
      chunks_written: 12,
    },
    checked_at_utc: new Date().toISOString(),
    ...over,
  };
}

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("corpusHealthCard", () => {
  it("renders four cards from a healthy snapshot", async () => {
    const snap = makeSnapshot();
    const handle = createCorpusHealthCard({
      autoRefreshMs: 0,
      getJsonImpl: async () => ({ ok: true, ...snap }),
    });

    await vi.advanceTimersByTimeAsync(0);
    const cards = handle.element.querySelectorAll(
      "[data-lia-component='corpus-health-metric']",
    );
    expect(cards).toHaveLength(4);
    const titles = Array.from(cards).map((c) =>
      c.querySelector(".lia-corpus-health-metric__title")?.textContent,
    );
    expect(titles).toEqual([
      "Generación activa",
      "Parity Supabase ↔ Falkor",
      "Embeddings",
      "Última ingesta",
    ]);
    handle.destroy();
  });

  it("derives tones — parity desfasada → danger, embeddings pendientes → warning", async () => {
    const snap = makeSnapshot({
      parity: {
        ok: false,
        supabase_docs: 1322,
        falkor_docs: 1300,
        supabase_chunks: 30859,
        falkor_articles: 1300,
        supabase_edges: 3247,
        falkor_edges: 3000,
        mismatches: [
          { field: "docs", supabase_value: 1322, falkor_value: 1300, delta: 22 },
        ],
      },
      embeddings: { pending_chunks: 12, pct_complete: 99.96 },
    });
    const handle = createCorpusHealthCard({
      autoRefreshMs: 0,
      getJsonImpl: async () => ({ ok: true, ...snap }),
    });

    await vi.advanceTimersByTimeAsync(0);
    const cards = Array.from(
      handle.element.querySelectorAll<HTMLElement>(
        "[data-lia-component='corpus-health-metric']",
      ),
    );
    const tones = cards.map((c) => c.dataset.tone);
    // Generation: ok, Parity: danger, Embeddings: warning, Last delta: ok
    expect(tones).toEqual(["ok", "danger", "warning", "ok"]);
    handle.destroy();
  });

  it("renders a visible error when fetch throws", async () => {
    const handle = createCorpusHealthCard({
      autoRefreshMs: 0,
      getJsonImpl: async () => {
        throw new Error("fetch failed");
      },
    });
    await vi.advanceTimersByTimeAsync(0);
    const empty = handle.element.querySelector(".lia-corpus-health__empty--error");
    expect(empty).not.toBeNull();
    expect(empty?.textContent).toContain("fetch failed");
    handle.destroy();
  });

  it("auto-refreshes on the configured interval and destroy() stops it", async () => {
    let calls = 0;
    const handle = createCorpusHealthCard({
      autoRefreshMs: 1_000,
      getJsonImpl: async () => {
        calls += 1;
        return { ok: true, ...makeSnapshot() };
      },
    });
    // Initial fetch.
    await vi.advanceTimersByTimeAsync(0);
    expect(calls).toBe(1);

    // Tick #1 at 1s.
    await vi.advanceTimersByTimeAsync(1_100);
    expect(calls).toBe(2);
    // Tick #2 at 2s.
    await vi.advanceTimersByTimeAsync(1_100);
    expect(calls).toBe(3);

    handle.destroy();
    // No more ticks after destroy.
    await vi.advanceTimersByTimeAsync(5_000);
    expect(calls).toBe(3);
  });

  it("missing generation (snapshot id=null) renders a neutral/warning state, no crash", async () => {
    const snap = makeSnapshot({
      generation: {
        id: null,
        activated_at: null,
        documents: 0,
        chunks: 0,
        knowledge_class_counts: {},
      },
      parity: { ok: null, mismatches: [] },
      embeddings: { pending_chunks: null, pct_complete: null },
      last_delta: null,
    });
    const handle = createCorpusHealthCard({
      autoRefreshMs: 0,
      getJsonImpl: async () => ({ ok: true, ...snap }),
    });
    await vi.advanceTimersByTimeAsync(0);
    const cards = Array.from(
      handle.element.querySelectorAll<HTMLElement>(
        "[data-lia-component='corpus-health-metric']",
      ),
    );
    expect(cards).toHaveLength(4);
    const tones = cards.map((c) => c.dataset.tone);
    // Generation: warning (no id), Parity: neutral, Embeddings: neutral, Last: neutral
    expect(tones).toEqual(["warning", "neutral", "neutral", "neutral"]);
    handle.destroy();
  });
});
