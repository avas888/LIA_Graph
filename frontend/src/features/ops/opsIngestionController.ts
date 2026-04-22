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
import { createOpsAutoPilot } from "@/features/ops/opsIngestionAutoPilot";
import { bindOpsEvents } from "@/features/ops/opsIngestionEvents";
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

  // Decouplingv1 Phase 10: the auto-pilot polling loop lives in
  // `createOpsAutoPilot`. Exposes the same surface (start/stop/update +
  // tick) the rest of this controller + the bindEvents block consumes.
  const autoPilot = createOpsAutoPilot(ctx, api);
  const { startAutoPilot, stopAutoPilot, updateAutoStatus } = autoPilot;

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
    bindOpsEvents({
      ctx, api, upload, intake, autoPilot,
      render, renderCorpora, renderControls, traceClear,
      directFolderIngest, suppressPanelsOnNextRender,
    });
  }

  return {
    bindEvents,
    refreshIngestion,
    refreshSelectedSession,
    render,
  };
}
