import { ApiError, getJson, postJson } from "@/shared/api/client";
import type { I18nRuntime } from "@/shared/i18n";
import {
  buildSummaryLine,
  formatBatchType,
  formatOpsError,
  isCompletedSession,
  isRunningSession,
  type CorporaPayload,
  type EjectResult,
  type IngestionActionPayload,
  type IngestionDocument,
  type IngestionSession,
  type IngestionSessionPayload,
  type IngestionSessionsPayload,
  type IntakeEntry,
  type IntakeVerdict,
  type PreflightEntry,
  type PreflightManifest,
  statusTone,
} from "@/features/ops/opsTypes";
import { renderKanbanBoard } from "@/features/ops/opsKanbanView";
import type { OpsStateController } from "@/features/ops/opsState";
import { getToastController } from "@/shared/ui/toasts";

import {
  type AsyncTaskRunner,
  type OpsIngestionDom,
  type CreateOpsIngestionControllerOptions,
  requestJson,
  postJsonOrThrow,
} from "@/features/ops/opsIngestionTypes";
import { createOpsApi } from "@/features/ops/opsIngestionApi";
import { createOpsControllerCtx } from "@/features/ops/opsIngestionContext";
import { createOpsUpload } from "@/features/ops/opsIngestionUpload";
import { createOpsIntake } from "@/features/ops/opsIngestionIntake";
import {
  SUPPORTED_INGESTION_EXTENSIONS as SUPPORTED_EXTENSIONS,
  HIDDEN_FILE_PREFIXES as HIDDEN_PREFIXES,
  FOLDER_UPLOAD_CONCURRENCY,
  FOLDER_PENDING_STORAGE_PREFIX,
  countRawDocs,
  fileKey,
  filterSupportedFiles,
  formatFileSize,
  getRelativePath,
  makeVerdictPill,
  verdictLabel,
} from "@/features/ops/opsIngestionFormatters";
export function createOpsIngestionController(
  options: CreateOpsIngestionControllerOptions,
) {
  const { i18n, stateController, dom, withThinkingWheel, setFlash } = options;
  const {
    ingestionCorpusSelect,
    ingestionBatchTypeSelect,
    ingestionDropzone,
    ingestionFileInput,
    ingestionFolderInput,
    ingestionSelectFilesBtn,
    ingestionSelectFolderBtn,
    ingestionUploadProgress,
    ingestionPendingFiles,
    ingestionOverview,
    ingestionRefreshBtn,
    ingestionCreateSessionBtn,
    ingestionUploadBtn,
    ingestionProcessBtn,
    ingestionAutoProcessBtn,
    ingestionValidateBatchBtn,
    ingestionRetryBtn,
    ingestionDeleteSessionBtn,
    ingestionSessionMeta,
    ingestionSessionsList,
    selectedSessionMeta,
    ingestionLastError,
    ingestionLastErrorMessage,
    ingestionLastErrorGuidance,
    ingestionLastErrorNext,
    ingestionKanban,
    ingestionLogAccordion,
    ingestionLogBody,
    ingestionLogCopyBtn,
    ingestionAutoStatus,
  } = dom;

  const { state } = stateController;
  const ctx = createOpsControllerCtx(options);
  const toast = ctx.toast;

  // Decouplingv1 Phase 7: API calls live in `createOpsApi`. We destructure
  // with the historical names so every existing call site (refreshIngestion,
  // fetchCorpora, uploadIngestionFile, …) keeps working. `ctx.render` and
  // `ctx.trace` are rebound at the bottom of this closure to the `render()`
  // and `trace()` functions defined further down.
  const api = createOpsApi(ctx);
  const {
    resolveSessionCorpus,
    fetchCorpora,
    fetchIngestionSessions,
    fetchIngestionSession,
    createIngestionSession,
    uploadIngestionFile,
    startIngestionProcess,
    validateBatch,
    retryIngestionSession,
    ejectIngestionSession,
    refreshIngestion,
    refreshSelectedSession,
    ensureSelectedSession,
  } = api;

  // Decouplingv1 Phase 8: upload helpers live in `createOpsUpload`.
  const upload = createOpsUpload(ctx, api);
  const {
    resolveFolderFiles,
    readDirectoryHandle,
    uploadFilesWithConcurrency,
    renderUploadProgress,
    renderScanProgress,
    persistFolderPending,
    clearFolderPending,
    getStoredFolderPendingCount,
    requestPreflight,
  } = upload;

  // ── Persistent trace log — dedicated floating panel that nothing can overwrite ──
  let _traceLines: string[] = [];
  let _traceActive = false;
  let _tracePanel: HTMLPreElement | null = null;

  function trace(msg: string): void {
    const ts = new Date().toISOString().slice(11, 23);
    const line = `[${ts}] ${msg}`;
    _traceLines.push(line);
    _traceActive = true;
    console.log(`[folder-ingest] ${msg}`);
    // Write to log accordion body
    ingestionLogAccordion.hidden = false;
    ingestionLogBody.hidden = false;
    ingestionLogBody.textContent = _traceLines.join("\n");
    const toggle = document.getElementById("ingestion-log-toggle");
    if (toggle) {
      toggle.setAttribute("aria-expanded", "true");
      const marker = toggle.querySelector(".ops-log-accordion-marker");
      if (marker) marker.textContent = "\u25BE";
    }
  }
  function traceClear(): void {
    _traceLines = [];
    _traceActive = false;
    _hidePreflightBounceLog();
  }

  function _hidePreflightBounceLog(): void {
    const { ingestionBounceLog, ingestionBounceBody } = dom;
    if (ingestionBounceLog) {
      ingestionBounceLog.hidden = true;
      ingestionBounceLog.open = false;
    }
    if (ingestionBounceBody) ingestionBounceBody.textContent = "";
  }

  // Decouplingv1 Phase 9: the three-window intake pipeline lives in
  // `createOpsIntake`. It owns the local `intakeError` + `preflightDebounce`
  // state. Two callbacks (directFolderIngest + renderControls) still live
  // in this controller closure so we populate them on the deps object
  // *after* those helpers are defined further down.
  const intakeDeps = {
    directFolderIngest: () => Promise.resolve(),
    renderControls: () => {},
  };
  const intake = createOpsIntake(ctx, api, upload, intakeDeps);
  const {
    addFilesToIntake,
    clearIntake,
    confirmAndIngest,
    removeIntakeEntry,
    cancelAllWillIngest,
  } = intake;

  // doc_ids whose reclassify panel must NOT be restored on the next render.
  // Populated on successful assign; consumed and cleared by renderSelectedSession.
  const suppressPanelsOnNextRender = new Set<string>();

  function renderCorpora(): void {
    const current = state.selectedCorpus;
    ingestionCorpusSelect.innerHTML = "";

    // AUTOGENERAR always first, in all caps
    const autoOption = document.createElement("option");
    autoOption.value = "autogenerar";
    autoOption.textContent = "AUTOGENERAR";
    autoOption.selected = current === "autogenerar";
    ingestionCorpusSelect.appendChild(autoOption);

    [...state.corpora].sort((a, b) => a.label.localeCompare(b.label, "es")).forEach((corpus) => {
      const option = document.createElement("option");
      option.value = corpus.key;
      const attentionCount = corpus.attention?.length || 0;
      let label = corpus.active ? corpus.label : `${corpus.label} (${i18n.t("ops.ingestion.corpusInactiveOption")})`;
      if (attentionCount > 0) {
        label += ` ⚠ ${attentionCount}`;
      }
      option.textContent = label;
      option.selected = corpus.key === current;
      ingestionCorpusSelect.appendChild(option);
    });
  }

  // Folder-upload helpers (resolveFolderFiles, readDirectoryHandle,
  // uploadFilesWithConcurrency, renderUploadProgress, persistFolderPending,
  // clearFolderPending, getStoredFolderPendingCount) live in
  // opsIngestionUpload.ts since decouplingv1 Phase 8.

  function appendIntakeRow(
    body: HTMLElement,
    entry: IntakeEntry,
    opts: { removable: boolean; readonly?: boolean; showReason?: boolean },
  ): void {
    const row = document.createElement("div");
    row.className = "ops-intake-row";
    if (entry.verdict === "pending") row.classList.add("ops-intake-row--pending");
    if (opts.readonly) row.classList.add("ops-intake-row--readonly");

    const icon = document.createElement("span");
    icon.className = "ops-intake-row__icon";
    icon.textContent = "\uD83D\uDCC4";

    const name = document.createElement("span");
    name.className = "ops-intake-row__name";
    name.textContent = entry.relativePath || entry.file.name;
    name.title = entry.relativePath || entry.file.name;

    const size = document.createElement("span");
    size.className = "ops-intake-row__size";
    size.textContent = formatFileSize(entry.file.size);

    const pill = makeVerdictPill(entry, i18n);

    row.append(icon, name, size, pill);

    if (opts.showReason && entry.preflightEntry?.reason) {
      const reason = document.createElement("span");
      reason.className = "ops-intake-row__reason";
      reason.textContent = entry.preflightEntry.reason;
      reason.title = entry.preflightEntry.reason;
      row.appendChild(reason);
    }

    if (opts.removable) {
      const removeBtn = document.createElement("button");
      removeBtn.type = "button";
      removeBtn.className = "ops-intake-row__remove";
      removeBtn.textContent = "\u2715";
      removeBtn.title = i18n.t("ops.ingestion.willIngest.cancelAll");
      removeBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        removeIntakeEntry(entry);
      });
      row.appendChild(removeBtn);
    }

    body.appendChild(row);
  }

  function buildIntakePanel(
    variant: "intake" | "will-ingest" | "bounced",
    titleKey: string,
    countKey: string,
    count: number,
    entries: IntakeEntry[],
    opts: { removable: boolean; readonly?: boolean; showReason?: boolean; cancelAllAction?: () => void },
  ): HTMLElement {
    const panel = document.createElement("section");
    panel.className = `ops-intake-panel ops-intake-panel--${variant}`;

    const header = document.createElement("header");
    header.className = "ops-intake-panel__header";

    const title = document.createElement("span");
    title.className = "ops-intake-panel__title";
    title.textContent = i18n.t(titleKey);
    header.appendChild(title);

    const countEl = document.createElement("span");
    countEl.className = "ops-intake-panel__count";
    countEl.textContent = i18n.t(countKey, { count });
    header.appendChild(countEl);

    if (opts.readonly) {
      const ro = document.createElement("span");
      ro.className = "ops-intake-panel__readonly";
      ro.textContent = i18n.t("ops.ingestion.bounced.readonly");
      header.appendChild(ro);
    }
    if (opts.cancelAllAction) {
      const cancelBtn = document.createElement("button");
      cancelBtn.type = "button";
      cancelBtn.className = "ops-intake-panel__action";
      cancelBtn.textContent = i18n.t("ops.ingestion.willIngest.cancelAll");
      cancelBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        opts.cancelAllAction!();
      });
      header.appendChild(cancelBtn);
    }

    panel.appendChild(header);

    const body = document.createElement("div");
    body.className = "ops-intake-panel__body";
    entries.forEach((entry) => appendIntakeRow(body, entry, opts));
    panel.appendChild(body);

    return panel;
  }

  /** Render the three-window intake review inside the dropzone. Replaces the
   * legacy single-list renderer. Window 1 shows every dropped file (including
   * duplicates) with its verdict pill; windows 2 and 3 appear only after a
   * successful preflight has populated `state.reviewPlan`. */
  function renderIntakeWindows(): void {
    // Tear down any previous intake DOM inside the dropzone.
    ingestionDropzone.querySelector(".ops-intake-windows")?.remove();
    ingestionDropzone.querySelector(".dropzone-file-list")?.remove();

    if (state.intake.length === 0) {
      ingestionPendingFiles.textContent = i18n.t("ops.ingestion.pendingNone");
      ingestionPendingFiles.hidden = true;
      ingestionDropzone.classList.remove("has-files");
      return;
    }

    ingestionPendingFiles.hidden = true;
    ingestionDropzone.classList.add("has-files");

    const container = document.createElement("div");
    container.className = "ops-intake-windows";

    // Status banner — verifying / stale / failed
    const banner = buildIntakeBanner();
    if (banner) container.appendChild(banner);

    // Window 1 — raw intake, every dropped file, no remove button in this panel
    // (users remove from window 2 only — window 1 is the observation log).
    container.appendChild(
      buildIntakePanel(
        "intake",
        "ops.ingestion.intake.title",
        "ops.ingestion.intake.count",
        state.intake.length,
        state.intake,
        { removable: false, readonly: false, showReason: false },
      ),
    );

    // Windows 2 + 3 — only appear after preflight has resolved
    const plan = state.reviewPlan;
    if (plan) {
      container.appendChild(
        buildIntakePanel(
          "will-ingest",
          "ops.ingestion.willIngest.title",
          "ops.ingestion.willIngest.count",
          plan.willIngest.length,
          plan.willIngest,
          {
            removable: true,
            readonly: false,
            showReason: false,
            cancelAllAction: plan.willIngest.length > 0 ? () => cancelAllWillIngest() : undefined,
          },
        ),
      );

      if (plan.bounced.length > 0) {
        container.appendChild(
          buildIntakePanel(
            "bounced",
            "ops.ingestion.bounced.title",
            "ops.ingestion.bounced.count",
            plan.bounced.length,
            plan.bounced,
            { removable: false, readonly: true, showReason: true },
          ),
        );
      }
    }

    ingestionDropzone.appendChild(container);
  }

  /** Build the small status banner at the top of the intake windows. Returns
   * null when there's nothing to say. */
  function buildIntakeBanner(): HTMLElement | null {
    const stale = state.reviewPlan?.stalePartial === true;
    const hasPending = state.intake.some((e) => e.verdict === "pending");
    const failed = intake.getIntakeError();

    if (!stale && !hasPending && !failed) return null;

    const banner = document.createElement("div");
    banner.className = "ops-intake-banner";

    if (failed) {
      banner.classList.add("ops-intake-banner--error");
      const text = document.createElement("span");
      text.className = "ops-intake-banner__text";
      text.textContent = i18n.t("ops.ingestion.intake.failed");
      const retry = document.createElement("button");
      retry.type = "button";
      retry.className = "ops-intake-banner__retry";
      retry.textContent = i18n.t("ops.ingestion.intake.retry");
      retry.addEventListener("click", (e) => {
        e.stopPropagation();
        intake.setIntakeError(false);
        intake.schedulePreflight();
        render();
      });
      banner.append(text, retry);
      return banner;
    }

    const spinner = document.createElement("span");
    spinner.className = "ops-intake-banner__spinner";
    banner.appendChild(spinner);

    const text = document.createElement("span");
    text.className = "ops-intake-banner__text";
    if (stale) {
      banner.classList.add("ops-intake-banner--stale");
      text.textContent = i18n.t("ops.ingestion.intake.stale");
    } else {
      banner.classList.add("ops-intake-banner--verifying");
      text.textContent = i18n.t("ops.ingestion.intake.verifying");
    }
    banner.appendChild(text);
    return banner;
  }

  function renderControls(): void {
    const corpus = stateController.selectedCorpusConfig();
    const session = state.selectedSession;
    const selectedActive = state.selectedCorpus === "autogenerar"
      ? state.corpora.some((c) => c.active)
      : Boolean(corpus?.active);
    const running = isRunningSession(String(session?.status || ""));

    ingestionBatchTypeSelect.value = ingestionBatchTypeSelect.value || "autogenerar";
    const isUploading = state.folderUploadProgress?.uploading ?? false;
    const plan = state.reviewPlan;
    const willCount = plan?.willIngest.length ?? 0;
    const preflightStale = plan?.stalePartial === true;
    const preflightFailed = intake.getIntakeError() === true;
    const approveReady = !!plan && willCount > 0 && !preflightStale && !preflightFailed;

    ingestionCreateSessionBtn.disabled = state.mutating || !selectedActive;
    ingestionSelectFilesBtn.disabled = state.mutating || !selectedActive || isUploading;
    ingestionSelectFolderBtn.disabled = state.mutating || !selectedActive || isUploading || running;

    // The old "Subir archivos" button is repurposed as "Aprobar e ingerir" — it
    // only enables after preflight has populated window 2 with at least one file.
    ingestionUploadBtn.disabled = state.mutating || !selectedActive || !approveReady || isUploading;
    if (!plan) {
      ingestionUploadBtn.textContent = i18n.t("ops.ingestion.approve");
    } else if (willCount === 0) {
      ingestionUploadBtn.textContent = i18n.t("ops.ingestion.approveNone");
    } else {
      ingestionUploadBtn.textContent = i18n.t("ops.ingestion.approveCount", { count: willCount });
    }

    ingestionProcessBtn.disabled = state.mutating || !selectedActive || !session || running;
    // Auto-process operates only on the selected session now — the intake window
    // pipeline is the sole path for introducing new files.
    ingestionAutoProcessBtn.disabled = state.mutating || !selectedActive || isUploading || !session || running;
    ingestionAutoProcessBtn.textContent = `\u25B6 ${i18n.t("ops.ingestion.actions.autoProcess")}`;
    // "Validar lote" enabled when: ≥1 done doc AND ≥1 doc still pending/processing, AND gate_pending exists
    const doneCount = Number(session?.batch_summary?.done || 0);
    const pendingOrProcessing = Number(session?.batch_summary?.queued || 0) + Number(session?.batch_summary?.processing || 0);
    const gatePending = Number(session?.batch_summary?.pending_batch_gate || 0);
    const canValidate = doneCount >= 1 && (pendingOrProcessing >= 1 || gatePending >= 1);
    ingestionValidateBatchBtn.disabled = state.mutating || !selectedActive || !session || running || !canValidate;
    ingestionRetryBtn.disabled = state.mutating || !selectedActive || !session || running;
    // "Detener y descartar" — always available when a session exists (stops if running, then deletes)
    ingestionDeleteSessionBtn.disabled = state.mutating || !session;
    ingestionRefreshBtn.disabled = state.mutating;
    ingestionCorpusSelect.disabled = state.mutating || state.corpora.length === 0;
    ingestionFileInput.disabled = state.mutating || !selectedActive;

    if (!selectedActive) {
      ingestionOverview.textContent = i18n.t("ops.ingestion.corpusInactive");
      return;
    }

    ingestionOverview.textContent = i18n.t("ops.ingestion.overview", {
      active: state.corpora.filter((item) => item.active).length,
      total: state.corpora.length,
      corpus: state.selectedCorpus === "autogenerar" ? "AUTOGENERAR" : (corpus?.label || state.selectedCorpus),
      session: session?.session_id || i18n.t("ops.ingestion.noSession"),
    });
  }

  function renderSessions(): void {
    ingestionSessionsList.innerHTML = "";
    ingestionSessionMeta.textContent = state.selectedSession
      ? `${state.selectedSession.session_id} · ${state.selectedSession.status}`
      : i18n.t("ops.ingestion.selectedEmpty");

    if (state.sessions.length === 0) {
      const item = document.createElement("li");
      item.className = "ops-empty";
      item.textContent = i18n.t("ops.ingestion.sessionsEmpty");
      ingestionSessionsList.appendChild(item);
      return;
    }

    state.sessions.forEach((session) => {
      const item = document.createElement("li");
      const isPartialFailed = session.status === "partial_failed";
      const button = document.createElement("button");
      button.type = "button";
      button.className = `ops-session-item${session.session_id === state.selectedSessionId ? " is-active" : ""}${isPartialFailed ? " has-retry-action" : ""}`;
      button.dataset.sessionId = session.session_id;

      const head = document.createElement("div");
      head.className = "ops-session-item-head";

      const title = document.createElement("div");
      title.className = "ops-session-id";
      title.textContent = session.session_id;

      const chip = document.createElement("span");
      chip.className = `meta-chip status-${statusTone(session.status)}`;
      chip.textContent = session.status;

      head.append(title, chip);

      // ── Pills row: corpus + distinct batch types ──
      const pillsRow = document.createElement("div");
      pillsRow.className = "ops-session-pills";

      const corpusLabel = state.corpora.find((c) => c.key === session.corpus)?.label || session.corpus;
      const corpusPill = document.createElement("span");
      corpusPill.className = "meta-chip ops-pill-corpus";
      corpusPill.textContent = corpusLabel;
      pillsRow.appendChild(corpusPill);

      const docs = session.documents || [];
      const batchTypes = [...new Set(docs.map((d) => d.batch_type).filter(Boolean))];
      batchTypes.forEach((bt) => {
        const pill = document.createElement("span");
        pill.className = "meta-chip ops-pill-batch";
        pill.textContent = formatBatchType(bt, i18n);
        pillsRow.appendChild(pill);
      });

      // ── Filenames ──
      const names = docs.map((d) => d.filename).filter(Boolean);
      let filesLine: HTMLDivElement | null = null;
      if (names.length > 0) {
        filesLine = document.createElement("div");
        filesLine.className = "ops-session-files";
        const visible = names.slice(0, 3);
        const rest = names.length - visible.length;
        filesLine.textContent = visible.join(", ") + (rest > 0 ? ` +${rest}` : "");
      }

      const summary = document.createElement("div");
      summary.className = "ops-session-summary";
      summary.textContent = buildSummaryLine(session.batch_summary, i18n);

      const footer = document.createElement("div");
      footer.className = "ops-session-summary";
      footer.textContent = session.updated_at ? i18n.formatDateTime(session.updated_at, { dateStyle: "short", timeStyle: "short", timeZone: "America/Bogota" }) : "-";

      button.appendChild(head);
      button.appendChild(pillsRow);
      if (filesLine) button.appendChild(filesLine);
      button.appendChild(summary);
      button.appendChild(footer);
      if (session.last_error?.code) {
        const issue = document.createElement("div");
        issue.className = "ops-session-summary status-error";
        issue.textContent = session.last_error.code;
        button.appendChild(issue);
      }

      button.addEventListener("click", async () => {
        stateController.setSelectedSession(session);
        render();
        try {
          await refreshSelectedSession({ sessionId: session.session_id, showWheel: true });
        } catch (_error) {
          // Error state is surfaced by refreshSelectedSession.
        }
      });

      item.appendChild(button);

      if (isPartialFailed) {
        const retryBtn = document.createElement("button");
        retryBtn.type = "button";
        retryBtn.className = "ops-session-retry-inline";
        retryBtn.textContent = i18n.t("ops.ingestion.actions.retry");
        retryBtn.disabled = state.mutating;
        retryBtn.addEventListener("click", async (e) => {
          e.stopPropagation();
          retryBtn.disabled = true;
          stateController.setMutating(true);
          renderControls();
          try {
            await withThinkingWheel(async () => retryIngestionSession(session.session_id));
            await refreshIngestion({ showWheel: false, reportError: true, focusSessionId: session.session_id });
            setFlash(i18n.t("ops.ingestion.flash.retryStarted", { id: session.session_id }), "success");
          } catch (error) {
            setFlash(formatOpsError(error), "error");
          } finally {
            stateController.setMutating(false);
            renderControls();
          }
        });
        item.appendChild(retryBtn);
      }

      ingestionSessionsList.appendChild(item);
    });
  }

  // ── Detailed log accordion ──────────────────────────────

  function buildSessionLog(session: IngestionSession): string {
    const lines: string[] = [];
    const ts = () => new Date().toISOString();

    lines.push(i18n.t("ops.ingestion.log.sessionHeader", { id: session.session_id }));
    lines.push(`Corpus:     ${session.corpus || "-"}`);
    lines.push(`Status:     ${session.status}`);
    lines.push(`Created:    ${session.created_at || "-"}`);
    lines.push(`Updated:    ${session.updated_at || "-"}`);
    lines.push(`Heartbeat:  ${(session as Record<string, unknown>).heartbeat_at ?? "-"}`);
    if ((session as Record<string, unknown>).auto_processing) {
      lines.push(`Auto-proc:  ${(session as Record<string, unknown>).auto_processing}`);
    }
    if ((session as Record<string, unknown>).gate_sub_stage) {
      lines.push(`Gate-stage: ${(session as Record<string, unknown>).gate_sub_stage}`);
    }
    if ((session as Record<string, unknown>).wip_sync_status) {
      lines.push(`WIP-sync:   ${(session as Record<string, unknown>).wip_sync_status}`);
    }

    if (session.batch_summary) {
      const s = session.batch_summary;
      const rawCount = (session.documents || []).filter(
        (d) => d.status === "raw" || d.status === "needs_classification",
      ).length;
      const pendingDedup = (session.documents || []).filter((d) => d.status === "pending_dedup").length;
      lines.push("");
      lines.push("── Resumen del lote ──");
      lines.push(`  Total: ${s.total}  Queued: ${s.queued}  Processing: ${s.processing}  Done: ${s.done}  Failed: ${s.failed}  Duplicados: ${s.skipped_duplicate}  Bounced: ${s.bounced}`);
      if (rawCount > 0) lines.push(`  Raw (sin clasificar): ${rawCount}`);
      if (pendingDedup > 0) lines.push(`  Pending dedup: ${pendingDedup}`);
    }

    if (session.last_error) {
      lines.push("");
      lines.push("── Error de sesión ──");
      lines.push(`  Código:    ${session.last_error.code || "-"}`);
      lines.push(`  Mensaje:   ${session.last_error.message || "-"}`);
      lines.push(`  Guía:      ${session.last_error.guidance || "-"}`);
      lines.push(`  Siguiente: ${session.last_error.next_step || "-"}`);
    }

    const docs = session.documents || [];
    if (docs.length === 0) {
      lines.push("");
      lines.push(i18n.t("ops.ingestion.log.noDocuments"));
    } else {
      lines.push("");
      lines.push(`── Documentos (${docs.length}) ──`);

      // Sort: failed first, then processing, then queued, then done
      const order: Record<string, number> = { failed: 0, processing: 1, in_progress: 1, queued: 2, raw: 2, done: 3, completed: 3, bounced: 4, skipped_duplicate: 5 };
      const sorted = [...docs].sort((a, b) => (order[a.status] ?? 3) - (order[b.status] ?? 3));

      for (const doc of sorted) {
        lines.push("");
        lines.push(`  ┌─ ${doc.filename} (${doc.doc_id})`);
        lines.push(`  │  Status:   ${doc.status}  │  Stage: ${doc.stage || "-"}  │  Progress: ${doc.progress ?? 0}%`);
        lines.push(`  │  Bytes:    ${doc.bytes ?? "-"}  │  Batch: ${doc.batch_type || "-"}`);

        if (doc.source_relative_path) {
          lines.push(`  │  Path:     ${doc.source_relative_path}`);
        }

        if (doc.detected_topic || doc.detected_type) {
          lines.push(`  │  Topic:    ${doc.detected_topic || "-"}  │  Type: ${doc.detected_type || "-"}  │  Confidence: ${doc.combined_confidence ?? "-"}`);
          if ((doc as Record<string, unknown>).classification_source) {
            lines.push(`  │  Classifier: ${(doc as Record<string, unknown>).classification_source}`);
          }
        }

        if (doc.chunk_count != null) {
          lines.push(`  │  Chunks:   ${doc.chunk_count}  │  Elapsed: ${doc.elapsed_ms ?? "-"}ms`);
        }

        if (doc.dedup_match_type) {
          lines.push(`  │  Dedup:    ${doc.dedup_match_type}  │  Match: ${(doc as Record<string, unknown>).dedup_match_doc_id || "-"}`);
        }

        if (doc.replaced_doc_id) {
          lines.push(`  │  Replaced: ${doc.replaced_doc_id}`);
        }

        if (doc.error) {
          lines.push(`  │  ❌ ERROR`);
          lines.push(`  │    Código:    ${doc.error.code || "-"}`);
          lines.push(`  │    Mensaje:   ${doc.error.message || "-"}`);
          lines.push(`  │    Guía:      ${doc.error.guidance || "-"}`);
          lines.push(`  │    Siguiente: ${doc.error.next_step || "-"}`);
        }

        lines.push(`  │  Created: ${doc.created_at || "-"}  │  Updated: ${doc.updated_at || "-"}`);
        lines.push(`  └─`);
      }
    }

    lines.push("");
    lines.push(`Log generado: ${ts()}`);
    return lines.join("\n");
  }

  function renderLogAccordion(): void {
    // Don't overwrite if there's an active trace
    if (_traceLines.length > 0) return;

    const session = state.selectedSession;
    if (!session) {
      ingestionLogAccordion.hidden = true;
      ingestionLogBody.textContent = "";
      return;
    }

    ingestionLogAccordion.hidden = false;
    ingestionLogBody.textContent = buildSessionLog(session);
  }

  function renderSelectedSession(): void {
    const session = state.selectedSession;

    if (!session) {
      selectedSessionMeta.textContent = i18n.t("ops.ingestion.selectedEmpty");
      ingestionLastError.hidden = true;
      if (_traceLines.length === 0) {
        ingestionLogAccordion.hidden = true;
      }
      ingestionKanban.innerHTML = "";
      return;
    }

    // Resume hint: check if there are pending files from a prior folder upload
    const pendingResumeCount = getStoredFolderPendingCount(session.session_id);
    const resumeHint = pendingResumeCount > 0
      ? ` · ${i18n.t("ops.ingestion.folderResumePending", { count: pendingResumeCount })}`
      : "";
    selectedSessionMeta.textContent = `${session.session_id} · ${buildSummaryLine(session.batch_summary, i18n)}${resumeHint}`;

    if (session.last_error) {
      ingestionLastError.hidden = false;
      ingestionLastErrorMessage.textContent = session.last_error.message || session.last_error.code || "-";
      ingestionLastErrorGuidance.textContent = session.last_error.guidance || "";
      ingestionLastErrorNext.textContent = `${i18n.t("ops.ingestion.lastErrorNext")}: ${session.last_error.next_step || "-"}`;
    } else {
      ingestionLastError.hidden = true;
    }

    if ((session.documents || []).length === 0) {
      ingestionKanban.innerHTML = `<p class="ops-empty">${i18n.t("ops.ingestion.documentsEmpty")}</p>`;
      ingestionKanban.style.minHeight = "0";
      renderLogAccordion();
      return;
    }
    ingestionKanban.style.minHeight = "";

    renderKanbanBoard(session, ingestionKanban, i18n, suppressPanelsOnNextRender, state.corpora);
    suppressPanelsOnNextRender.clear();
    renderLogAccordion();
  }

  function render(): void {
    renderCorpora();
    renderIntakeWindows();
    renderControls();
    renderSessions();
    renderSelectedSession();
  }

  // Decouplingv1 Phase 7/9: rebind the ctx callbacks now that render/trace
  // (and the intake deps that reach into directFolderIngest + renderControls)
  // are defined. Factories captured `ctx` / `intakeDeps` by reference, so
  // mutating them here is transparent.
  ctx.render = render;
  ctx.trace = trace;
  intakeDeps.directFolderIngest = directFolderIngest;
  intakeDeps.renderControls = renderControls;

  // ── Auto-pilot loop ──────────────────────────────────
  // Polls session, re-calls auto-process to queue newly classified docs,
  // triggers processing, and repeats until all docs are done or need manual review.

  const AUTO_POLL_INTERVAL = 4_000; // 4s between polls
  let autoPilotTimer: ReturnType<typeof setTimeout> | null = null;
  let autoPilotSessionId = "";

  function stopAutoPilot(): void {
    if (autoPilotTimer) {
      clearTimeout(autoPilotTimer);
      autoPilotTimer = null;
    }
    autoPilotSessionId = "";
    ingestionAutoStatus.hidden = true;
    ingestionAutoStatus.classList.remove("is-running");
  }

  /** Count raw/needs_classification docs from the document list (batch_summary lumps them into queued). */
  function updateAutoStatus(session: IngestionSession): void {
    const summary = session.batch_summary;
    const rawCount = countRawDocs(session);
    // batch_summary.queued includes raw docs, so subtract them
    const queuedCount = Math.max(0, Number(summary.queued ?? 0) - rawCount);
    const processingCount = Number(summary.processing ?? 0);
    const doneCount = Number(summary.done ?? 0);
    const failedCount = Number(summary.failed ?? 0);
    const bouncedCount = Number(summary.bounced ?? 0);
    const activeCount = queuedCount + processingCount;

    ingestionAutoStatus.hidden = false;

    // Build suffix for bounced docs (always shown if > 0)
    const bouncedSuffix = bouncedCount > 0 ? ` · ${bouncedCount} rebotados` : "";

    if (activeCount > 0 || rawCount > 0) {
      ingestionAutoStatus.classList.add("is-running");
      ingestionAutoStatus.textContent = i18n.t("ops.ingestion.auto.running", {
        queued: queuedCount,
        processing: processingCount,
        raw: rawCount,
      }) + bouncedSuffix;
    } else if (failedCount > 0) {
      ingestionAutoStatus.classList.remove("is-running");
      ingestionAutoStatus.textContent = i18n.t("ops.ingestion.auto.done", {
        done: doneCount,
        failed: failedCount,
        raw: rawCount,
      }) + bouncedSuffix;
    } else {
      ingestionAutoStatus.classList.remove("is-running");
      ingestionAutoStatus.textContent = i18n.t("ops.ingestion.auto.allDone", {
        done: doneCount,
      }) + bouncedSuffix;
    }
  }

  async function autoPilotTick(): Promise<void> {
    const sessionId = autoPilotSessionId;
    if (!sessionId) return;

    try {
      // 1. Refresh session state
      const session = await fetchIngestionSession(sessionId);
      stateController.upsertSession(session);
      render();
      updateAutoStatus(session);

      const summary = session.batch_summary;
      const rawCount = countRawDocs(session);
      const totalCount = Number(summary.total ?? 0);

      // 1b. If session has 0 documents, nothing to do — stop immediately
      if (totalCount === 0) {
        stopAutoPilot();
        return;
      }

      // 2. If there are raw docs that might have been classified since last tick,
      //    re-call auto-process to promote high-confidence ones to queued.
      if (rawCount > 0) {
        await requestJson<IngestionActionPayload>(
          `/api/ingestion/sessions/${encodeURIComponent(sessionId)}/auto-process`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ max_concurrency: 5 }),
          },
        );
      }

      // 3. If there are newly queued docs and nothing is processing, kick off processing.
      const refreshedSession = rawCount > 0
        ? await fetchIngestionSession(sessionId)
        : session;
      const refreshedRaw = countRawDocs(refreshedSession);
      const refreshedQueuedReal = Math.max(0, Number(refreshedSession.batch_summary.queued ?? 0) - refreshedRaw);
      const refreshedProcessing = Number(refreshedSession.batch_summary.processing ?? 0);

      if (refreshedQueuedReal > 0 && refreshedProcessing === 0) {
        await startIngestionProcess(sessionId);
      }

      // Update view after any actions
      if (rawCount > 0) {
        stateController.upsertSession(refreshedSession);
        render();
        updateAutoStatus(refreshedSession);
      }

      // 4. Check termination: all docs done/failed/bounced, none queued/processing/raw
      const stillActive = refreshedQueuedReal + refreshedProcessing;

      if (totalCount > 0 && stillActive === 0 && refreshedRaw === 0) {
        // All documents have reached a terminal state — run batch validation if needed
        const gatePending = Number(refreshedSession.batch_summary.pending_batch_gate ?? 0);
        if (gatePending > 0 && refreshedSession.status !== "running_batch_gates" && refreshedSession.status !== "completed") {
          try {
            await validateBatch(sessionId);
          } catch (_e) { /* validation is best-effort */ }
        }
        // Final refresh and stop
        const finalSession = await fetchIngestionSession(sessionId);
        stateController.upsertSession(finalSession);
        render();
        updateAutoStatus(finalSession);
        stopAutoPilot();
        setFlash(i18n.t("ops.ingestion.auto.allDone", { done: Number(finalSession.batch_summary.done ?? 0) }), "success");
        return;
      }

      // 5. If only raw docs remain (need manual intervention), stop polling
      //    but keep the status message visible.
      if (stillActive === 0 && refreshedRaw > 0) {
        ingestionAutoStatus.classList.remove("is-running");
        ingestionAutoStatus.textContent = i18n.t("ops.ingestion.auto.done", {
          done: Number(refreshedSession.batch_summary.done ?? 0),
          failed: Number(refreshedSession.batch_summary.failed ?? 0),
          raw: refreshedRaw,
        });
        stopAutoPilot();
        return;
      }

      // 6. Schedule next tick
      autoPilotTimer = setTimeout(() => void autoPilotTick(), AUTO_POLL_INTERVAL);
    } catch (error) {
      // On error, stop the loop and surface the error
      stopAutoPilot();
      setFlash(formatOpsError(error), "error");
    }
  }

  function startAutoPilot(sessionId: string): void {
    stopAutoPilot();
    autoPilotSessionId = sessionId;
    ingestionAutoStatus.hidden = false;
    ingestionAutoStatus.classList.add("is-running");
    ingestionAutoStatus.textContent = i18n.t("ops.ingestion.auto.running", {
      queued: 0, processing: 0, raw: 0,
    });
    // Start first tick after a short delay to let the server process
    autoPilotTimer = setTimeout(() => void autoPilotTick(), 2_000);
  }

  // ── Direct folder ingest (v2 fallback — upload all pending files) ──

  async function directFolderIngest(): Promise<void> {
    trace(`directFolderIngest: ${state.pendingFiles.length} archivos pendientes`);
    const session = await ensureSelectedSession();
    trace(`Sesión asignada: ${session.session_id} (corpus=${session.corpus}, status=${session.status})`);
    const batchTypeValue = ingestionBatchTypeSelect.value || "autogenerar";
    trace(`Subiendo ${state.pendingFiles.length} archivos con batchType="${batchTypeValue}"...`);
    persistFolderPending(session.session_id);

    const result = await uploadFilesWithConcurrency(
      session.session_id,
      [...state.pendingFiles],
      batchTypeValue,
      FOLDER_UPLOAD_CONCURRENCY,
    );
    console.log("[folder-ingest] Upload result:", { uploaded: result.uploaded, failed: result.failed });

    trace(`Upload completo: ${result.uploaded} subidos, ${result.failed} fallidos${result.errors.length > 0 ? " — " + result.errors.slice(0, 5).map((e) => `${e.filename}: ${e.error}`).join("; ") : ""}`);

    stateController.setPendingFiles([]);
    stateController.setFolderUploadProgress(null);
    clearFolderPending(session.session_id);
    ingestionFolderInput.value = "";
    ingestionFileInput.value = "";

    if (result.failed > 0 && result.uploaded === 0) {
      const errorSample = result.errors.slice(0, 3).map((e) => `${e.filename}: ${e.error}`).join("; ");
      trace(`TODOS FALLARON: ${errorSample}`);
      setFlash(`${i18n.t("ops.ingestion.flash.folderUploadPartial", result)} — ${errorSample}`, "error");
      await refreshIngestion({ showWheel: false, reportError: true, focusSessionId: session.session_id });
      return;
    }

    trace(`Consultando estado de sesión post-upload...`);
    const freshSession = await fetchIngestionSession(session.session_id);
    const bouncedCount = Number(freshSession.batch_summary?.bounced ?? 0);
    const rawCount = countRawDocs(freshSession);
    const queuedCount = Number(freshSession.batch_summary?.queued ?? 0);
    const totalDocs = Number(freshSession.batch_summary?.total ?? 0);
    const actionable = totalDocs - bouncedCount;
    trace(`Sesión post-upload: total=${totalDocs} bounced=${bouncedCount} raw=${rawCount} queued=${queuedCount} actionable=${actionable}`);

    // If everything bounced (already in corpus), show clear message and stop
    if (actionable === 0 && bouncedCount > 0) {
      trace(`TODOS REBOTADOS: ${bouncedCount} archivos ya existen en el corpus`);
      stateController.upsertSession(freshSession);
      setFlash(
        `${bouncedCount} archivos ya existen en el corpus (rebotados). 0 archivos nuevos para procesar.`,
        "error",
      );
      trace(`--- FIN (todo rebotado) ---`);
      return;
    }

    // Auto-process with threshold=0 to force-queue all raw docs.
    trace(`Auto-procesando con threshold=0 (force-queue)...`);
    await requestJson<IngestionActionPayload>(
      `/api/ingestion/sessions/${encodeURIComponent(session.session_id)}/auto-process`,
      { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ max_concurrency: 5, auto_accept_threshold: 0.0 }) },
    );
    await startIngestionProcess(session.session_id);
    await refreshIngestion({ showWheel: false, reportError: true, focusSessionId: session.session_id });

    const parts: string[] = [];
    if (result.uploaded > 0) parts.push(`${actionable} archivos en proceso`);
    if (bouncedCount > 0) parts.push(`${bouncedCount} rebotados`);
    if (result.failed > 0) parts.push(`${result.failed} fallidos`);
    setFlash(parts.join(" · "), result.failed > 0 ? "error" : "success");
    trace(`Auto-piloto iniciado para ${session.session_id}`);
    trace(`--- FIN (éxito) ---`);
    startAutoPilot(session.session_id);
  }

  // Preflight + scan-progress helpers (requestPreflight, renderScanProgress)
  // moved to opsIngestionUpload.ts in decouplingv1 Phase 8.

  // NOTE: the legacy post-preflight review UI (renderPreflightReview, the
  // category renderer, handlePreflightIngest/Reingest, showReingestConfirmation)
  // has been removed. Its role is now filled by the inline three-window intake
  // flow: drop → auto-preflight → windows 2/3 → Aprobar e ingerir.
  //
  // The legacy `state.preflightManifest` field is no longer written from this
  // controller but is still in OpsStateData for backward-compat with tests
  // and out-of-tree callers. Deletion of the field is a separate sweep.

  function bindEvents(): void {
    ingestionDropzone.addEventListener("click", () => {
      if (!ingestionFileInput.disabled) {
        ingestionFileInput.click();
      }
    });

    ingestionDropzone.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" && event.key !== " ") return;
      event.preventDefault();
      if (!ingestionFileInput.disabled) {
        ingestionFileInput.click();
      }
    });

    // Track nested drag enter/leave so hovering over child elements (file rows)
    // doesn't flicker the is-dragover class on and off.
    let dragDepth = 0;

    ingestionDropzone.addEventListener("dragenter", (event) => {
      event.preventDefault();
      dragDepth++;
      if (!ingestionFileInput.disabled) {
        ingestionDropzone.classList.add("is-dragover");
      }
    });

    ingestionDropzone.addEventListener("dragover", (event) => {
      event.preventDefault();
    });

    ingestionDropzone.addEventListener("dragleave", () => {
      dragDepth--;
      if (dragDepth <= 0) {
        dragDepth = 0;
        ingestionDropzone.classList.remove("is-dragover");
      }
    });

    ingestionDropzone.addEventListener("drop", async (event) => {
      event.preventDefault();
      dragDepth = 0;
      ingestionDropzone.classList.remove("is-dragover");
      if (ingestionFileInput.disabled) return;

      // Try folder resolution first (drag-drop folder detection)
      const dt = event.dataTransfer;
      if (dt) {
        const folderFiles = await resolveFolderFiles(dt);
        if (folderFiles.length > 0) {
          addFilesToIntake(filterSupportedFiles(folderFiles));
          return;
        }
      }

      // Flat file drop fallback
      const droppedFiles = Array.from(event.dataTransfer?.files || []);
      if (droppedFiles.length === 0) return;
      addFilesToIntake(filterSupportedFiles(droppedFiles));
    });

    ingestionFileInput.addEventListener("change", () => {
      const selected = Array.from(ingestionFileInput.files || []);
      if (selected.length === 0) return;
      addFilesToIntake(filterSupportedFiles(selected));
    });

    // Folder input change handler (webkitdirectory)
    ingestionFolderInput.addEventListener("change", () => {
      const selected = Array.from(ingestionFolderInput.files || []);
      if (selected.length === 0) return;
      // webkitRelativePath is already set by the browser on these files
      addFilesToIntake(filterSupportedFiles(selected));
    });

    ingestionSelectFilesBtn.addEventListener("click", () => {
      if (!ingestionFileInput.disabled) {
        ingestionFileInput.click();
      }
    });

    ingestionSelectFolderBtn.addEventListener("click", async () => {
      if (ingestionFolderInput.disabled) return;

      // Prefer showDirectoryPicker (Chrome/Edge) — it lets the user select a
      // folder by clicking on it WITHOUT navigating into it first.
      if (typeof (window as any).showDirectoryPicker === "function") {
        try {
          const dirHandle: FileSystemDirectoryHandle = await (window as any).showDirectoryPicker({
            mode: "read",
          });
          const allFiles = await readDirectoryHandle(dirHandle, dirHandle.name);
          const supported = filterSupportedFiles(allFiles);
          if (supported.length > 0) {
            addFilesToIntake(supported);
          } else {
            setFlash(i18n.t("ops.ingestion.pendingNone"), "error");
          }
          return;
        } catch (e: any) {
          if (e?.name === "AbortError") return; // user cancelled
          // Fall through to legacy webkitdirectory input
        }
      }

      // Fallback: native <input webkitdirectory> for Safari / Firefox
      ingestionFolderInput.click();
    });

    ingestionCorpusSelect.addEventListener("change", () => {
      stateController.setSelectedCorpus(ingestionCorpusSelect.value);
      stateController.setSessions([]);
      stateController.setSelectedSession(null);
      // Corpus change invalidates any preflight (dedup is per-corpus).
      clearIntake();
      setFlash();
      render();
      void refreshIngestion({ showWheel: true, reportError: true });
    });

    ingestionRefreshBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      setFlash();
      void refreshIngestion({ showWheel: true, reportError: true });
    });

    ingestionCreateSessionBtn.addEventListener("click", async () => {
      stopAutoPilot();
      setFlash();
      // Full slate reset — clear intake pipeline + upload progress
      clearIntake();
      stateController.setPreflightManifest(null);
      stateController.setFolderUploadProgress(null);
      state.rejectedArtifacts = [];
      ingestionUploadProgress.hidden = true;
      ingestionUploadProgress.innerHTML = "";
      ingestionFileInput.value = "";
      ingestionFolderInput.value = "";
      ingestionLastError.hidden = true;
      traceClear();
      ingestionLogAccordion.hidden = true;
      ingestionLogBody.textContent = "";

      stateController.setMutating(true);
      renderControls();
      try {
        const session = await withThinkingWheel(async () => createIngestionSession(resolveSessionCorpus()));
        stateController.upsertSession(session);
        render();
        setFlash(i18n.t("ops.ingestion.flash.sessionCreated", { id: session.session_id }), "success");
      } catch (error) {
        setFlash(formatOpsError(error), "error");
      } finally {
        stateController.setMutating(false);
        renderControls();
      }
    });

    // Repurposed: the old "Subir archivos" button is now "Aprobar e ingerir".
    // It's enabled only after preflight has populated window 2, and it hands
    // the approved willIngest list to directFolderIngest().
    ingestionUploadBtn.addEventListener("click", () => {
      void confirmAndIngest();
    });

    // Note: the old monolithic handleFolderIngest() is gone. Its work is now
    // split across addFilesToIntake → schedulePreflight → runIntakePreflight
    // → applyManifestToIntake → confirmAndIngest → directFolderIngest().
    // See the "Granular intake pipeline" block earlier in this file.

    ingestionProcessBtn.addEventListener("click", async () => {
      const sessionId = state.selectedSessionId;
      if (!sessionId) return;
      setFlash();
      stateController.setMutating(true);
      renderControls();
      try {
        await withThinkingWheel(async () => startIngestionProcess(sessionId));
        await refreshSelectedSession({ sessionId, showWheel: false, reportError: false });
        const msg = i18n.t("ops.ingestion.flash.processStarted", { id: sessionId });
        setFlash(msg, "success");
        toast.show({ message: msg, tone: "success" });
      } catch (error) {
        const errMsg = formatOpsError(error);
        setFlash(errMsg, "error");
        toast.show({ message: errMsg, tone: "error" });
      } finally {
        stateController.setMutating(false);
        renderControls();
      }
    });

    ingestionValidateBatchBtn.addEventListener("click", async () => {
      const sessionId = state.selectedSessionId;
      if (!sessionId) return;
      setFlash();
      stateController.setMutating(true);
      renderControls();
      try {
        await withThinkingWheel(async () => validateBatch(sessionId));
        await refreshSelectedSession({ sessionId, showWheel: false, reportError: false });
        const msg = "Validación de lote iniciada";
        setFlash(msg, "success");
        toast.show({ message: msg, tone: "success" });
      } catch (error) {
        const errMsg = formatOpsError(error);
        setFlash(errMsg, "error");
        toast.show({ message: errMsg, tone: "error" });
      } finally {
        stateController.setMutating(false);
        renderControls();
      }
    });

    ingestionRetryBtn.addEventListener("click", async () => {
      const sessionId = state.selectedSessionId;
      if (!sessionId) return;
      setFlash();
      stateController.setMutating(true);
      renderControls();
      try {
        await withThinkingWheel(async () => retryIngestionSession(sessionId));
        await refreshSelectedSession({ sessionId, showWheel: false, reportError: false });
        setFlash(i18n.t("ops.ingestion.flash.retryStarted", { id: sessionId }), "success");
      } catch (error) {
        setFlash(formatOpsError(error), "error");
      } finally {
        stateController.setMutating(false);
        renderControls();
      }
    });

    // ── "Detener y descartar" — confirm via toast, eject session, full slate reset ──
    ingestionDeleteSessionBtn.addEventListener("click", async () => {
      const sessionId = state.selectedSessionId;
      if (!sessionId) return;

      // Determine if session passed batch gates (point of no return)
      const completed = isCompletedSession(state.selectedSession);
      const confirmMessage = completed
        ? i18n.t("ops.ingestion.confirm.ejectPostGate")
        : i18n.t("ops.ingestion.confirm.ejectPreGate");

      const confirmed = await toast.confirm({
        title: i18n.t("ops.ingestion.actions.discardSession"),
        message: confirmMessage,
        tone: "caution",
        confirmLabel: i18n.t("ops.ingestion.confirm.ejectLabel"),
      });
      if (!confirmed) return;

      stopAutoPilot();
      setFlash();
      stateController.setMutating(true);
      renderControls();
      try {
        const running = isRunningSession(String(state.selectedSession?.status || ""));
        const result = await withThinkingWheel(async () =>
          ejectIngestionSession(sessionId, running || completed),
        );

        // Full slate reset
        stateController.clearSelectionAfterDelete();
        clearIntake();
        stateController.setPreflightManifest(null);
        stateController.setFolderUploadProgress(null);
        state.rejectedArtifacts = [];
        ingestionUploadProgress.hidden = true;
        ingestionUploadProgress.innerHTML = "";
        ingestionFileInput.value = "";
        ingestionFolderInput.value = "";
        ingestionLastError.hidden = true;
        traceClear();
        ingestionLogAccordion.hidden = true;
        ingestionLogBody.textContent = "";
        await refreshIngestion({ showWheel: false, reportError: false });

        // Result toast
        const hasErrors = Array.isArray(result.errors) && result.errors.length > 0;
        const toastMsg = result.path === "rollback"
          ? i18n.t("ops.ingestion.flash.ejectedRollback", { id: sessionId, count: result.ejected_files })
          : i18n.t("ops.ingestion.flash.ejectedInstant", { id: sessionId, count: result.ejected_files });
        const toastTone = hasErrors ? "caution" : "success";
        setFlash(toastMsg, hasErrors ? "error" : "success");
        toast.show({ message: toastMsg, tone: toastTone });
        if (hasErrors) {
          toast.show({ message: i18n.t("ops.ingestion.flash.ejectedPartial"), tone: "caution", durationMs: 8000 });
        }
      } catch (error) {
        const errMsg = formatOpsError(error);
        setFlash(errMsg, "error");
        toast.show({ message: errMsg, tone: "error" });
      } finally {
        stateController.setMutating(false);
        render();
      }
    });

    // --- Auto-process button ---
    // Operates only on the selected session's existing docs. New-file intake
    // goes through the dropzone → three-window flow → "Aprobar e ingerir".
    ingestionAutoProcessBtn.addEventListener("click", async () => {
      const sessionId = state.selectedSessionId;
      if (!sessionId) return;
      setFlash();
      stateController.setMutating(true);
      renderControls();
      try {
        await withThinkingWheel(async () =>
          requestJson<IngestionActionPayload>(
            `/api/ingestion/sessions/${encodeURIComponent(sessionId)}/auto-process`,
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ max_concurrency: 5 }),
            },
          ),
        );
        await startIngestionProcess(sessionId);
        await refreshSelectedSession({ sessionId, showWheel: false, reportError: false });
        setFlash(`Auto-procesamiento iniciado para ${sessionId}`, "success");
        // Start auto-pilot to keep polling, re-queuing, and processing
        startAutoPilot(sessionId);
      } catch (error) {
        setFlash(formatOpsError(error), "error");
      } finally {
        stateController.setMutating(false);
        renderControls();
      }
    });

    // --- Log accordion toggle ---
    const logToggle = document.getElementById("ingestion-log-toggle");
    if (logToggle) {
      logToggle.addEventListener("click", (e) => {
        // Don't toggle if the click target is the copy button
        if ((e.target as HTMLElement).closest(".ops-log-copy-btn")) return;
        const expanded = ingestionLogBody.hidden;
        ingestionLogBody.hidden = !expanded;
        logToggle.setAttribute("aria-expanded", String(expanded));
        const marker = logToggle.querySelector(".ops-log-accordion-marker");
        if (marker) marker.textContent = expanded ? "\u25BE" : "\u25B8";
      });
      logToggle.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          logToggle.click();
        }
      });
    }

    // --- Log accordion copy button ---
    ingestionLogCopyBtn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      const text = ingestionLogBody.textContent || "";
      navigator.clipboard.writeText(text).then(() => {
        const original = ingestionLogCopyBtn.textContent;
        ingestionLogCopyBtn.textContent = i18n.t("ops.ingestion.log.copied");
        setTimeout(() => { ingestionLogCopyBtn.textContent = original; }, 1500);
      }).catch(() => {
        // Fallback: select pre text
        const range = document.createRange();
        range.selectNodeContents(ingestionLogBody);
        const sel = window.getSelection();
        sel?.removeAllRanges();
        sel?.addRange(range);
      });
    });

    // --- Kanban card actions (event delegation) ---
    ingestionKanban.addEventListener("click", async (e) => {
      const btn = (e.target as HTMLElement).closest<HTMLElement>("[data-action]");
      if (!btn) return;
      const action = btn.getAttribute("data-action");
      const docId = btn.getAttribute("data-doc-id");
      const sessionId = state.selectedSessionId;

      if (!sessionId || !docId) return;

      // Toggle fallback dropdown for autogenerar cards
      if (action === "show-existing-dropdown") {
        const card = btn.closest(".kanban-card");
        const panel = card?.querySelector<HTMLElement>(".kanban-ag-fallback-panel");
        if (panel) panel.hidden = !panel.hidden;
        return;
      }

      // For assign: capture select values BEFORE any re-render destroys the DOM
      let assignTopic = "";
      let assignType = "";
      if (action === "assign") {
        const card = btn.closest(".kanban-card");
        const topicSelect = card?.querySelector<HTMLSelectElement>("[data-field='topic']");
        const typeSelect = card?.querySelector<HTMLSelectElement>("[data-field='type']");
        assignTopic = topicSelect?.value || "";
        assignType = typeSelect?.value || "";
        if (!assignTopic || !assignType) {
          // Highlight empty selects
          if (topicSelect && !assignTopic) topicSelect.classList.add("kanban-select--invalid");
          if (typeSelect && !assignType) typeSelect.classList.add("kanban-select--invalid");
          return;
        }
      }

      setFlash();
      stateController.setMutating(true);
      renderControls();

      try {
        switch (action) {
          case "assign": {
            await withThinkingWheel(async () =>
              requestJson<IngestionActionPayload>(
                `/api/ingestion/sessions/${encodeURIComponent(sessionId)}/documents/${encodeURIComponent(docId)}/classify`,
                {
                  method: "PATCH",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ topic: assignTopic, batch_type: assignType }),
                },
              ),
            );
            // Don't re-open the reclassify panel after a successful assign.
            suppressPanelsOnNextRender.add(docId);
            break;
          }
          case "replace-dup": {
            await withThinkingWheel(async () =>
              requestJson<IngestionActionPayload>(
                `/api/ingestion/sessions/${encodeURIComponent(sessionId)}/documents/${encodeURIComponent(docId)}/resolve-duplicate`,
                {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ action: "replace" }),
                },
              ),
            );
            break;
          }
          case "add-new-dup": {
            await withThinkingWheel(async () =>
              requestJson<IngestionActionPayload>(
                `/api/ingestion/sessions/${encodeURIComponent(sessionId)}/documents/${encodeURIComponent(docId)}/resolve-duplicate`,
                {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ action: "add_new" }),
                },
              ),
            );
            break;
          }
          case "discard-dup":
          case "discard": {
            await withThinkingWheel(async () =>
              requestJson<IngestionActionPayload>(
                `/api/ingestion/sessions/${encodeURIComponent(sessionId)}/documents/${encodeURIComponent(docId)}/resolve-duplicate`,
                {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ action: "discard" }),
                },
              ),
            );
            break;
          }
          case "accept-synonym": {
            const card = btn.closest(".kanban-card");
            const typeSelect = card?.querySelector<HTMLSelectElement>("[data-field='type']");
            const typeVal = typeSelect?.value || "";
            await withThinkingWheel(async () =>
              requestJson<IngestionActionPayload>(
                `/api/ingestion/sessions/${encodeURIComponent(sessionId)}/documents/${encodeURIComponent(docId)}/accept-autogenerar`,
                {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ action: "accept_synonym", type: typeVal || undefined }),
                },
              ),
            );
            suppressPanelsOnNextRender.add(docId);
            break;
          }
          case "accept-new-topic": {
            const card = btn.closest(".kanban-card");
            const labelInput = card?.querySelector<HTMLInputElement>("[data-field='autogenerar-label']");
            const typeSelect = card?.querySelector<HTMLSelectElement>("[data-field='type']");
            const editedLabel = labelInput?.value?.trim() || "";
            const typeVal = typeSelect?.value || "";
            if (!editedLabel || editedLabel.length < 3) {
              if (labelInput) labelInput.classList.add("kanban-select--invalid");
              return;
            }
            await withThinkingWheel(async () =>
              requestJson<IngestionActionPayload>(
                `/api/ingestion/sessions/${encodeURIComponent(sessionId)}/documents/${encodeURIComponent(docId)}/accept-autogenerar`,
                {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ action: "accept_new_topic", edited_label: editedLabel, type: typeVal || undefined }),
                },
              ),
            );
            suppressPanelsOnNextRender.add(docId);
            // Refresh corpora so the new topic appears in dropdowns
            await fetchCorpora();
            renderCorpora();
            break;
          }
          case "retry": {
            await withThinkingWheel(async () =>
              requestJson<IngestionActionPayload>(
                `/api/ingestion/sessions/${encodeURIComponent(sessionId)}/documents/${encodeURIComponent(docId)}/retry`,
                { method: "POST" },
              ),
            );
            break;
          }
          case "remove": {
            // No-op: just refresh below
            break;
          }
        }
        await refreshSelectedSession({ sessionId, showWheel: false, reportError: false });
      } catch (error) {
        setFlash(formatOpsError(error), "error");
      } finally {
        stateController.setMutating(false);
        renderControls();
      }
    });

    // --- Add corpus dialog ---
    const addCorpusDialog = dom.addCorpusDialog;
    const addCorpusBtn = dom.addCorpusBtn;
    if (addCorpusDialog && addCorpusBtn) {
      const labelInput = addCorpusDialog.querySelector<HTMLInputElement>("#add-corpus-label");
      const keyInput = addCorpusDialog.querySelector<HTMLInputElement>("#add-corpus-key");
      const kwStrongInput = addCorpusDialog.querySelector<HTMLInputElement>("#add-corpus-kw-strong");
      const kwWeakInput = addCorpusDialog.querySelector<HTMLInputElement>("#add-corpus-kw-weak");
      const errorEl = addCorpusDialog.querySelector<HTMLElement>("#add-corpus-error");
      const cancelBtn = addCorpusDialog.querySelector<HTMLButtonElement>("#add-corpus-cancel");
      const form = addCorpusDialog.querySelector<HTMLFormElement>("#add-corpus-form");

      function slugify(text: string): string {
        return text
          .normalize("NFD")
          .replace(/[\u0300-\u036f]/g, "")
          .toLowerCase()
          .replace(/[^a-z0-9]+/g, "_")
          .replace(/^_|_$/g, "");
      }

      addCorpusBtn.addEventListener("click", () => {
        if (labelInput) labelInput.value = "";
        if (keyInput) keyInput.value = "";
        if (kwStrongInput) kwStrongInput.value = "";
        if (kwWeakInput) kwWeakInput.value = "";
        if (errorEl) errorEl.hidden = true;
        addCorpusDialog.showModal();
        labelInput?.focus();
      });

      labelInput?.addEventListener("input", () => {
        if (keyInput) keyInput.value = slugify(labelInput.value);
      });

      cancelBtn?.addEventListener("click", () => {
        addCorpusDialog.close();
      });

      form?.addEventListener("submit", async (e) => {
        e.preventDefault();
        if (errorEl) errorEl.hidden = true;
        const label = labelInput?.value.trim() || "";
        if (!label) return;
        const kwStrong = (kwStrongInput?.value || "")
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean);
        const kwWeak = (kwWeakInput?.value || "")
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean);
        try {
          await withThinkingWheel(async () =>
            postJsonOrThrow<{ ok: boolean; corpus: Record<string, unknown> }, Record<string, unknown>>(
              "/api/corpora",
              {
                label,
                keywords_strong: kwStrong.length ? kwStrong : undefined,
                keywords_weak: kwWeak.length ? kwWeak : undefined,
              },
            ),
          );
          addCorpusDialog.close();
          await refreshIngestion({ showWheel: false, reportError: false });
          const newKey = slugify(label);
          if (newKey) {
            stateController.setSelectedCorpus(newKey);
          }
          render();
          setFlash(`Categor\u00eda "${label}" creada.`, "success");
        } catch (error) {
          if (errorEl) {
            errorEl.textContent = formatOpsError(error);
            errorEl.hidden = false;
          }
        }
      });
    }
  }

  return {
    bindEvents,
    refreshIngestion,
    refreshSelectedSession,
    render,
  };
}
