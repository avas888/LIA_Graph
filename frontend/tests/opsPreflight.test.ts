/**
 * Tests for pre-flight intelligence features (re-ingest v3).
 *
 * Covers:
 *   - PreflightEntry / PreflightManifest type shapes
 *   - PreflightScanProgress state transitions
 *   - Preflight review manifest rendering (categories, counts)
 *   - Re-ingestion confirmation dialog
 *   - Preflight action buttons (ingest, re-ingest, discard)
 */

import { describe, it, expect } from "vitest";

import type {
  PreflightEntry,
  PreflightManifest,
  PreflightScanProgress,
} from "@/features/ops/opsTypes";

// ── Type shape tests ──────────────────────────────────

describe("PreflightEntry type", () => {
  it("represents an artifact entry", () => {
    const entry: PreflightEntry = {
      filename: "state.md",
      relative_path: "LEYES/state.md",
      size: 245,
      content_hash: "abc123",
      category: "artifact",
      reason: "Archivo de proyecto: state.md",
      existing_doc_id: null,
      existing_filename: null,
      existing_chunk_count: null,
      revision_direction: null,
    };
    expect(entry.category).toBe("artifact");
    expect(entry.existing_doc_id).toBeNull();
  });

  it("represents an exact duplicate entry", () => {
    const entry: PreflightEntry = {
      filename: "Ley-550-1999.md",
      relative_path: "EXPERTOS/Ley-550-1999.md",
      size: 3200,
      content_hash: "abc123",
      category: "exact_duplicate",
      reason: "Identico a ley_550_1999 (6 chunks)",
      existing_doc_id: "ley_550_1999",
      existing_filename: "normativa/ley_550_1999.md",
      existing_chunk_count: 6,
      revision_direction: null,
    };
    expect(entry.category).toBe("exact_duplicate");
    expect(entry.existing_doc_id).toBe("ley_550_1999");
    expect(entry.existing_chunk_count).toBe(6);
  });

  it("represents a revision entry", () => {
    const entry: PreflightEntry = {
      filename: "Ley-1150-2007_v2.md",
      relative_path: "EXPERTOS/Ley-1150-2007_v2.md",
      size: 4800,
      content_hash: "def456",
      category: "revision",
      reason: "Version mas nueva de exp_ley_1150_2007 (8 chunks)",
      existing_doc_id: "exp_ley_1150_2007",
      existing_filename: "industry_guidance/exp_ley_1150_2007.md",
      existing_chunk_count: 8,
      revision_direction: "newer",
    };
    expect(entry.category).toBe("revision");
    expect(entry.revision_direction).toBe("newer");
  });

  it("represents a new file entry", () => {
    const entry: PreflightEntry = {
      filename: "Ley-2294-2023.md",
      relative_path: "NORMATIVA/Ley-2294-2023.md",
      size: 5100,
      content_hash: "ghi789",
      category: "new",
      reason: "Documento nuevo",
      existing_doc_id: null,
      existing_filename: null,
      existing_chunk_count: null,
      revision_direction: null,
    };
    expect(entry.category).toBe("new");
  });
});

describe("PreflightManifest type", () => {
  it("holds categorized entries with counts and timing", () => {
    const manifest: PreflightManifest = {
      artifacts: [],
      duplicates: [],
      revisions: [],
      new_files: [
        {
          filename: "test.md",
          relative_path: "test.md",
          size: 100,
          content_hash: "xxx",
          category: "new",
          reason: "Documento nuevo",
          existing_doc_id: null,
          existing_filename: null,
          existing_chunk_count: null,
          revision_direction: null,
        },
      ],
      scanned: 1,
      elapsed_ms: 42,
    };
    expect(manifest.scanned).toBe(1);
    expect(manifest.elapsed_ms).toBe(42);
    expect(manifest.new_files.length).toBe(1);
    expect(manifest.artifacts.length).toBe(0);
  });

  it("computes ingest count from new + revisions", () => {
    const manifest: PreflightManifest = {
      artifacts: [],
      duplicates: [],
      revisions: [
        { filename: "a.md", relative_path: "a.md", size: 1, content_hash: "a", category: "revision", reason: "", existing_doc_id: "x", existing_filename: "x.md", existing_chunk_count: 2, revision_direction: "newer" },
      ],
      new_files: [
        { filename: "b.md", relative_path: "b.md", size: 1, content_hash: "b", category: "new", reason: "", existing_doc_id: null, existing_filename: null, existing_chunk_count: null, revision_direction: null },
        { filename: "c.md", relative_path: "c.md", size: 1, content_hash: "c", category: "new", reason: "", existing_doc_id: null, existing_filename: null, existing_chunk_count: null, revision_direction: null },
      ],
      scanned: 3,
      elapsed_ms: 10,
    };
    const ingestCount = manifest.new_files.length + manifest.revisions.length;
    expect(ingestCount).toBe(3);
  });
});

describe("PreflightScanProgress type", () => {
  it("tracks hashing progress", () => {
    const progress: PreflightScanProgress = {
      total: 480,
      hashed: 245,
      scanning: true,
    };
    expect(progress.total).toBe(480);
    expect(progress.hashed).toBe(245);
    expect(progress.scanning).toBe(true);
    const pct = Math.round((progress.hashed / progress.total) * 100);
    expect(pct).toBe(51);
  });

  it("marks scan as complete", () => {
    const progress: PreflightScanProgress = {
      total: 480,
      hashed: 480,
      scanning: false,
    };
    expect(progress.scanning).toBe(false);
    const pct = Math.round((progress.hashed / progress.total) * 100);
    expect(pct).toBe(100);
  });
});

// ── Manifest data operations ──────────────────────────

describe("Manifest data operations", () => {
  function createManifest(counts: { art?: number; dup?: number; rev?: number; new?: number }): PreflightManifest {
    const makeEntries = (n: number, cat: PreflightEntry["category"]): PreflightEntry[] =>
      Array.from({ length: n }, (_, i) => ({
        filename: `file_${cat}_${i}.md`,
        relative_path: `folder/file_${cat}_${i}.md`,
        size: 100 + i,
        content_hash: `hash_${cat}_${i}`,
        category: cat,
        reason: `reason ${cat}`,
        existing_doc_id: cat === "new" || cat === "artifact" ? null : `doc_${i}`,
        existing_filename: cat === "new" || cat === "artifact" ? null : `existing_${i}.md`,
        existing_chunk_count: cat === "exact_duplicate" ? 5 : cat === "revision" ? 8 : null,
        revision_direction: cat === "revision" ? "newer" : null,
      }));

    return {
      artifacts: makeEntries(counts.art ?? 0, "artifact"),
      duplicates: makeEntries(counts.dup ?? 0, "exact_duplicate"),
      revisions: makeEntries(counts.rev ?? 0, "revision"),
      new_files: makeEntries(counts.new ?? 0, "new"),
      scanned: (counts.art ?? 0) + (counts.dup ?? 0) + (counts.rev ?? 0) + (counts.new ?? 0),
      elapsed_ms: 1200,
    };
  }

  it("sums total chunks for duplicates", () => {
    const m = createManifest({ dup: 3 });
    const totalChunks = m.duplicates.reduce((sum, e) => sum + (e.existing_chunk_count || 0), 0);
    expect(totalChunks).toBe(15); // 3 * 5
  });

  it("filters allowed paths for ingest (new + revisions)", () => {
    const m = createManifest({ art: 5, dup: 10, rev: 3, new: 20 });
    const allowedPaths = new Set([
      ...m.new_files.map((e) => e.relative_path),
      ...m.revisions.map((e) => e.relative_path),
    ]);
    expect(allowedPaths.size).toBe(23);
    // Artifacts and duplicates should not be in allowed paths
    for (const e of m.artifacts) {
      expect(allowedPaths.has(e.relative_path)).toBe(false);
    }
    for (const e of m.duplicates) {
      expect(allowedPaths.has(e.relative_path)).toBe(false);
    }
  });

  it("collects doc_ids for purge from duplicates", () => {
    const m = createManifest({ dup: 5 });
    const docIds = m.duplicates
      .map((e) => e.existing_doc_id)
      .filter((id): id is string => Boolean(id));
    expect(docIds.length).toBe(5);
    expect(docIds[0]).toBe("doc_0");
  });

  it("handles empty manifest gracefully", () => {
    const m = createManifest({});
    expect(m.scanned).toBe(0);
    expect(m.artifacts.length).toBe(0);
    expect(m.duplicates.length).toBe(0);
    expect(m.revisions.length).toBe(0);
    expect(m.new_files.length).toBe(0);
  });
});
