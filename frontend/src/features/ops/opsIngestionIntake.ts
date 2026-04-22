/**
 * Ops ingestion Intake factory. Decouplingv1 Phase 9 extraction.
 *
 * Owns the three-window intake pipeline:
 *
 *   addFilesToIntake → schedulePreflight (debounced) →
 *     runIntakePreflight → hashIntakeEntries → preflightIntake →
 *       applyManifestToIntake → render
 *
 * Plus the controller-local state the pipeline needs that we deliberately
 * keep out of `OpsStateData` (per the pre-existing comment in the
 * controller): `intakeError`, `preflightDebounce`, `PREFLIGHT_DEBOUNCE_MS`.
 *
 * `confirmAndIngest` lives here because it's the entry point "Aprobar e
 * ingerir" calls, but the network work it triggers (`directFolderIngest`
 * + `refreshSelectedSession`) is injected as deps — the controller wires
 * `directFolderIngest` because that orchestrator still lives there, and
 * `renderControls` likewise.
 */

import {
  fileKey,
  getRelativePath,
} from "@/features/ops/opsIngestionFormatters";
import {
  formatOpsError,
  type IntakeEntry,
  type IntakeVerdict,
  type PreflightEntry,
  type PreflightManifest,
} from "@/features/ops/opsTypes";

import type { OpsApi } from "@/features/ops/opsIngestionApi";
import type { OpsControllerCtx } from "@/features/ops/opsIngestionContext";
import type { OpsUpload } from "@/features/ops/opsIngestionUpload";

export interface OpsIntakeDeps {
  /** The "directFolderIngest" orchestrator (lives in the controller closure). */
  directFolderIngest: () => Promise<void>;
  /** Re-render the control strip after mutating `isMutating`. */
  renderControls: () => void;
}

export interface OpsIntake {
  addFilesToIntake: (files: File[]) => void;
  schedulePreflight: () => void;
  runIntakePreflight: (runId: number) => Promise<void>;
  hashIntakeEntries: (entries: IntakeEntry[]) => Promise<void>;
  preflightIntake: () => Promise<PreflightManifest | null>;
  applyManifestToIntake: (manifest: PreflightManifest) => void;
  removeIntakeEntry: (target: IntakeEntry) => void;
  cancelAllWillIngest: () => void;
  clearIntake: () => void;
  confirmAndIngest: () => Promise<void>;
  getIntakeError: () => boolean;
  setIntakeError: (value: boolean) => void;
}

export function createOpsIntake(
  ctx: OpsControllerCtx,
  api: OpsApi,
  upload: OpsUpload,
  deps: OpsIntakeDeps,
): OpsIntake {
  const { dom, stateController, setFlash } = ctx;
  const { ingestionFolderInput, ingestionFileInput } = dom;

  // ── Intake-window local state (UI-only; deliberately not in OpsStateData) ──
  //
  // `intakeError`       — true if the last preflight call failed (network/500).
  //                       Renders the red retry banner; blocks approval.
  // `preflightDebounce` — trailing debounce timer id so a folder drop of 500
  //                       files only triggers ONE preflight call, not 500.
  let intakeError = false;
  let preflightDebounce: ReturnType<typeof setTimeout> | null = null;
  const PREFLIGHT_DEBOUNCE_MS = 150;

  /** Add raw Files (from drop / file picker / folder picker) to the intake
   * window, dedup by file fingerprint, and schedule a preflight pass. */
  function addFilesToIntake(files: File[]): void {
    if (files.length === 0) return;

    const existing = new Set(ctx.state.intake.map((e) => fileKey(e.file)));
    const newEntries: IntakeEntry[] = [];
    for (const file of files) {
      const key = fileKey(file, ctx.state.folderRelativePaths);
      if (existing.has(key)) continue;
      existing.add(key);
      newEntries.push({
        file,
        relativePath: getRelativePath(file, ctx.state.folderRelativePaths),
        contentHash: null,
        verdict: "pending",
        preflightEntry: null,
      });
    }
    if (newEntries.length === 0) return;

    stateController.setIntake([...ctx.state.intake, ...newEntries]);
    // Mark any existing plan as stale — we're about to re-dedup everything.
    if (ctx.state.reviewPlan) {
      stateController.setReviewPlan({ ...ctx.state.reviewPlan, stalePartial: true });
    }
    intakeError = false;
    schedulePreflight();
    ctx.render();
  }

  /** Trailing debounce: coalesce rapid drops into a single preflight call. */
  function schedulePreflight(): void {
    if (preflightDebounce) clearTimeout(preflightDebounce);
    const runId = stateController.bumpPreflightRunId();
    preflightDebounce = setTimeout(() => {
      preflightDebounce = null;
      void runIntakePreflight(runId);
    }, PREFLIGHT_DEBOUNCE_MS);
  }

  /** Orchestrator: hash → preflight → apply. Race-guarded via `runId`. */
  async function runIntakePreflight(runId: number): Promise<void> {
    if (runId !== ctx.state.preflightRunId) return;
    if (ctx.state.intake.length === 0) return;

    const pending = ctx.state.intake.filter((e) => e.contentHash === null);
    try {
      if (pending.length > 0) {
        await hashIntakeEntries(pending);
        if (runId !== ctx.state.preflightRunId) return;
      }

      const manifest = await preflightIntake();
      if (runId !== ctx.state.preflightRunId) return;
      if (!manifest) {
        intakeError = true;
        ctx.render();
        return;
      }

      applyManifestToIntake(manifest);
      intakeError = false;
      ctx.render();
    } catch (error) {
      if (runId !== ctx.state.preflightRunId) return;
      console.error("[intake] preflight failed:", error);
      intakeError = true;
      ctx.render();
    }
  }

  /** Hash every intake entry whose contentHash is still null. Writes the hash
   * back onto the entry. Files that fail to read become verdict="unreadable". */
  async function hashIntakeEntries(entries: IntakeEntry[]): Promise<void> {
    stateController.setPreflightScanProgress({ total: entries.length, hashed: 0, scanning: true });
    upload.renderScanProgress();

    for (let i = 0; i < entries.length; i++) {
      const entry = entries[i];
      try {
        const buffer = await entry.file.arrayBuffer();
        const hashBuffer = await crypto.subtle.digest("SHA-256", buffer);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        entry.contentHash = hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
      } catch (error) {
        console.warn(`[intake] hash failed for ${entry.file.name}:`, error);
        entry.verdict = "unreadable";
        entry.contentHash = ""; // mark as processed so we don't retry
      }
      stateController.setPreflightScanProgress({ total: entries.length, hashed: i + 1, scanning: true });
      upload.renderScanProgress();
    }
    stateController.setPreflightScanProgress(null);
  }

  /** Call /api/ingestion/preflight with every intake entry that has a hash.
   * Returns the manifest, or null on network failure. */
  async function preflightIntake(): Promise<PreflightManifest | null> {
    const fileEntries = ctx.state.intake
      .filter((e) => e.contentHash && e.verdict !== "unreadable")
      .map((e) => ({
        filename: e.file.name,
        relative_path: e.relativePath || e.file.name,
        size: e.file.size,
        content_hash: e.contentHash!,
      }));
    if (fileEntries.length === 0) {
      // Nothing to preflight (everything was unreadable). Return an empty manifest.
      return {
        artifacts: [],
        duplicates: [],
        revisions: [],
        new_files: [],
        scanned: 0,
        elapsed_ms: 0,
      };
    }
    try {
      return await upload.requestPreflight(fileEntries, ctx.state.selectedCorpus);
    } catch (error) {
      console.error("[intake] /api/ingestion/preflight failed:", error);
      return null;
    }
  }

  /** Apply a preflight manifest to `state.intake`: set each entry's verdict +
   * preflightEntry, then partition the intake into willIngest (new+revision)
   * and bounced (duplicate+artifact+unreadable). Writes `state.reviewPlan`
   * AND the derived `state.pendingFiles` (the File[] that directFolderIngest
   * consumes). */
  function applyManifestToIntake(manifest: PreflightManifest): void {
    // Build a path→(bucket, entry) index for O(1) lookup.
    const byPath = new Map<string, { verdict: IntakeVerdict; preflightEntry: PreflightEntry }>();
    const idx = (bucket: IntakeVerdict, list: PreflightEntry[]) => {
      for (const p of list) {
        const key = p.relative_path || p.filename;
        byPath.set(key, { verdict: bucket, preflightEntry: p });
      }
    };
    idx("new", manifest.new_files);
    idx("revision", manifest.revisions);
    idx("duplicate", manifest.duplicates);
    idx("artifact", manifest.artifacts);

    const updated: IntakeEntry[] = ctx.state.intake.map((entry) => {
      if (entry.verdict === "unreadable") return entry;
      const key = entry.relativePath || entry.file.name;
      const hit = byPath.get(key);
      if (!hit) return { ...entry, verdict: "pending" };
      return { ...entry, verdict: hit.verdict, preflightEntry: hit.preflightEntry };
    });

    const willIngest = updated.filter((e) => e.verdict === "new" || e.verdict === "revision");
    const bounced = updated.filter(
      (e) => e.verdict === "duplicate" || e.verdict === "artifact" || e.verdict === "unreadable",
    );

    stateController.setIntake(updated);
    stateController.setReviewPlan({
      willIngest,
      bounced,
      scanned: manifest.scanned,
      elapsedMs: manifest.elapsed_ms,
      stalePartial: false,
    });
    // pendingFiles is the live "approved" queue directFolderIngest consumes.
    stateController.setPendingFiles(willIngest.map((e) => e.file));
  }

  /** Remove a single entry from window 2 (the user cancelled it). Also
   * removes it from window 1 and the pendingFiles queue. Window 3 rows are
   * read-only so this is never called for bounced entries. */
  function removeIntakeEntry(target: IntakeEntry): void {
    const filter = (e: IntakeEntry) => fileKey(e.file) !== fileKey(target.file);
    stateController.setIntake(ctx.state.intake.filter(filter));
    if (ctx.state.reviewPlan) {
      const nextWill = ctx.state.reviewPlan.willIngest.filter(filter);
      stateController.setReviewPlan({ ...ctx.state.reviewPlan, willIngest: nextWill });
      stateController.setPendingFiles(nextWill.map((e) => e.file));
    } else {
      stateController.setPendingFiles(
        ctx.state.pendingFiles.filter((f) => fileKey(f) !== fileKey(target.file)),
      );
    }
    ctx.render();
  }

  /** "cancelar todo" button on window 2 — drop every will-ingest entry.
   * Leaves window 3 (bounced) visible, leaves window 1 showing the bounced
   * entries with their verdicts, clears the pending queue. */
  function cancelAllWillIngest(): void {
    if (!ctx.state.reviewPlan) return;
    const willPaths = new Set(ctx.state.reviewPlan.willIngest.map((e) => fileKey(e.file)));
    const keptIntake = ctx.state.intake.filter((e) => !willPaths.has(fileKey(e.file)));
    stateController.setIntake(keptIntake);
    stateController.setReviewPlan({ ...ctx.state.reviewPlan, willIngest: [] });
    stateController.setPendingFiles([]);
    ctx.render();
  }

  /** Reset intake to zero state — e.g. after a successful approve+ingest. */
  function clearIntake(): void {
    if (preflightDebounce) {
      clearTimeout(preflightDebounce);
      preflightDebounce = null;
    }
    stateController.bumpPreflightRunId();
    stateController.setIntake([]);
    stateController.setReviewPlan(null);
    stateController.setPendingFiles([]);
    stateController.setPreflightScanProgress(null);
    intakeError = false;
    ctx.state.folderRelativePaths.clear();
  }

  /** "Aprobar e ingerir" handler. Validates preflight has run and at least
   * one file will be ingested, then hands off to the existing
   * directFolderIngest() — which handles session creation, upload, processing
   * and kanban updates exactly as today. */
  async function confirmAndIngest(): Promise<void> {
    const plan = ctx.state.reviewPlan;
    if (!plan) return;
    if (plan.stalePartial) return;
    if (plan.willIngest.length === 0) return;
    if (intakeError) return;

    setFlash();
    stateController.setMutating(true);
    deps.renderControls();
    try {
      await deps.directFolderIngest();
      clearIntake();
      ingestionFolderInput.value = "";
      ingestionFileInput.value = "";
    } catch (error) {
      stateController.setFolderUploadProgress(null);
      upload.renderUploadProgress();
      setFlash(formatOpsError(error), "error");
      if (ctx.state.selectedSessionId) {
        void api.refreshSelectedSession({
          sessionId: ctx.state.selectedSessionId,
          showWheel: false,
          reportError: false,
        });
      }
    } finally {
      stateController.setMutating(false);
      deps.renderControls();
    }
  }

  return {
    addFilesToIntake,
    schedulePreflight,
    runIntakePreflight,
    hashIntakeEntries,
    preflightIntake,
    applyManifestToIntake,
    removeIntakeEntry,
    cancelAllWillIngest,
    clearIntake,
    confirmAndIngest,
    getIntakeError: () => intakeError,
    setIntakeError: (value: boolean) => {
      intakeError = value;
    },
  };
}
