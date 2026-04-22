/**
 * Ops ingestion Events binder. Decouplingv1 Phase 12 extraction.
 *
 * The 600-LOC `bindEvents` body that previously lived in
 * `createOpsIngestionController` now lives here. It attaches every DOM
 * listener the ops ingestion surface needs: dropzone drag-drop, file/folder
 * pickers, corpus switch, the refresh/create/upload/process/retry/validate/
 * delete buttons, auto-process, the kanban delegated-click handler, the
 * add-corpus dialog form submission, and the log accordion toggle/copy.
 *
 * Binding a single function signature (a big `OpsEventDeps` bundle) keeps
 * the callers type-checked without forcing us to refactor the per-listener
 * shape. The controller populates `deps` after all factories and local
 * callbacks (directFolderIngest, render/renderCorpora/renderControls,
 * traceClear, suppressPanelsOnNextRender) are defined.
 */

import {
  filterSupportedFiles,
} from "@/features/ops/opsIngestionFormatters";
import {
  formatOpsError,
  isCompletedSession,
  isRunningSession,
  type IngestionActionPayload,
} from "@/features/ops/opsTypes";
import {
  postJsonOrThrow,
  requestJson,
} from "@/features/ops/opsIngestionTypes";

import type { OpsApi } from "@/features/ops/opsIngestionApi";
import type { OpsAutoPilot } from "@/features/ops/opsIngestionAutoPilot";
import type { OpsControllerCtx } from "@/features/ops/opsIngestionContext";
import type { OpsIntake } from "@/features/ops/opsIngestionIntake";
import type { OpsUpload } from "@/features/ops/opsIngestionUpload";

export interface OpsEventDeps {
  ctx: OpsControllerCtx;
  api: OpsApi;
  upload: OpsUpload;
  intake: OpsIntake;
  autoPilot: OpsAutoPilot;
  // Controller-local callbacks (things that still live in the composer).
  render: () => void;
  renderCorpora: () => void;
  renderControls: () => void;
  traceClear: () => void;
  directFolderIngest: () => Promise<void>;
  suppressPanelsOnNextRender: Set<string>;
}

export function bindOpsEvents(deps: OpsEventDeps): void {
  const { ctx, api, upload, intake, autoPilot } = deps;
  const { dom, stateController, i18n, setFlash, toast, withThinkingWheel } = ctx;
  const {
    ingestionDropzone,
    ingestionFileInput,
    ingestionFolderInput,
    ingestionSelectFilesBtn,
    ingestionSelectFolderBtn,
    ingestionCorpusSelect,
    ingestionRefreshBtn,
    ingestionCreateSessionBtn,
    ingestionUploadBtn,
    ingestionProcessBtn,
    ingestionValidateBatchBtn,
    ingestionRetryBtn,
    ingestionDeleteSessionBtn,
    ingestionAutoProcessBtn,
    ingestionLastError,
    ingestionLogBody,
    ingestionLogAccordion,
    ingestionLogCopyBtn,
    ingestionKanban,
    ingestionUploadProgress,
  } = dom;
  const { addFilesToIntake, clearIntake, confirmAndIngest } = intake;
  const { startAutoPilot, stopAutoPilot } = autoPilot;
  const {
    createIngestionSession,
    ejectIngestionSession,
    fetchCorpora,
    refreshIngestion,
    refreshSelectedSession,
    resolveSessionCorpus,
    retryIngestionSession,
    startIngestionProcess,
    validateBatch,
  } = api;
  const { resolveFolderFiles, readDirectoryHandle } = upload;
  const { render, renderCorpora, renderControls, traceClear, directFolderIngest, suppressPanelsOnNextRender } = deps;
  const { state } = stateController;

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
      if (marker) marker.textContent = expanded ? "▾" : "▸";
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
        .replace(/[̀-ͯ]/g, "")
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
        setFlash(`Categoría "${label}" creada.`, "success");
      } catch (error) {
        if (errorEl) {
          errorEl.textContent = formatOpsError(error);
          errorEl.hidden = false;
        }
      }
    });
  }
}
