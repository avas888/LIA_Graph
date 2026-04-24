import { queryRequired } from "@/shared/dom/template";
import type { I18nRuntime } from "@/shared/i18n";
import { createCorpusLifecycleController } from "@/features/ops/opsCorpusLifecycleController";
import { createOpsEmbeddingsController } from "@/features/ops/opsEmbeddingsController";
import { createOpsIngestionController } from "@/features/ops/opsIngestionController";
import { createOpsMonitorController } from "@/features/ops/opsMonitorController";
import { createOpsReindexController } from "@/features/ops/opsReindexController";
import { startOpsPolling } from "@/features/ops/opsPolling";
import { createOpsState } from "@/features/ops/opsState";
import { createIngestController } from "@/features/ingest/ingestController";

export function mountOpsApp(root: HTMLElement | Document, { i18n }: { i18n: I18nRuntime }): void {
  const q = root as ParentNode;

  // ── New Sesiones surface (Lia_Graph native) ────────────────
  // When `#lia-ingest-shell` is present, mount the new ingest controller AND
  // skip the legacy kanban `createOpsIngestionController` further down —
  // its `queryRequired` calls would crash on the new DOM. Other surfaces
  // (monitor, corpus lifecycle, embeddings, re-index) keep mounting normally
  // because they look for their own independent DOM IDs and degrade
  // gracefully when those are absent.
  const newIngestShell = q.querySelector<HTMLElement>("#lia-ingest-shell");
  let newIngestController: { refresh: () => Promise<void>; destroy: () => void } | null = null;
  if (newIngestShell) {
    newIngestController = createIngestController(newIngestShell, { i18n });
    window.setInterval(() => {
      void newIngestController?.refresh();
    }, 30_000);
  }
  const skipLegacyIngestionController = newIngestShell !== null;

  // Subtab buttons are optional (absent in browser-chrome mode).
  const monitorTabBtn = q.querySelector<HTMLButtonElement>("#ops-tab-monitor");
  const ingestionTabBtn = q.querySelector<HTMLButtonElement>("#ops-tab-ingestion");
  const controlTabBtn = q.querySelector<HTMLButtonElement>("#ops-tab-control");
  const embeddingsTabBtn = q.querySelector<HTMLButtonElement>("#ops-tab-embeddings");
  const reindexTabBtn = q.querySelector<HTMLButtonElement>("#ops-tab-reindex");
  const monitorPanel = q.querySelector<HTMLElement>("#ops-panel-monitor");
  const ingestionPanel = q.querySelector<HTMLElement>("#ops-panel-ingestion");
  const controlPanel = q.querySelector<HTMLElement>("#ops-panel-control");
  const embeddingsPanel = q.querySelector<HTMLElement>("#ops-panel-embeddings");
  const reindexPanel = q.querySelector<HTMLElement>("#ops-panel-reindex");

  const runsBody = q.querySelector<HTMLTableSectionElement>("#runs-body");
  const timelineNode = q.querySelector<HTMLUListElement>("#timeline");
  const timelineMeta = q.querySelector<HTMLParagraphElement>("#timeline-meta");
  const cascadeNote = q.querySelector<HTMLParagraphElement>("#cascade-note");
  const userCascadeNode = q.querySelector<HTMLOListElement>("#user-cascade");
  const userCascadeSummary = q.querySelector<HTMLParagraphElement>("#user-cascade-summary");
  const technicalCascadeNode = q.querySelector<HTMLOListElement>("#technical-cascade");
  const technicalCascadeSummary = q.querySelector<HTMLParagraphElement>("#technical-cascade-summary");
  const refreshRunsBtn = q.querySelector<HTMLButtonElement>("#refresh-runs");
  const hasMonitorDom = !!(runsBody && timelineNode && timelineMeta && cascadeNote && userCascadeNode && userCascadeSummary && technicalCascadeNode && technicalCascadeSummary && refreshRunsBtn);

  const ingestionFlash = skipLegacyIngestionController
    ? null
    : queryRequired<HTMLDivElement>(q, "#ingestion-flash");

  const stateController = createOpsState();

  function setFlash(message = "", tone: "success" | "error" = "success"): void {
    if (!ingestionFlash) return;
    if (!message) {
      ingestionFlash.hidden = true;
      ingestionFlash.textContent = "";
      ingestionFlash.removeAttribute("data-tone");
      return;
    }
    ingestionFlash.hidden = false;
    ingestionFlash.dataset.tone = tone;
    ingestionFlash.textContent = message;
  }

  // ── Legacy ingestion (kanban) DOM bindings — only when its DOM is present.
  // Folded into a single block to preserve the original structure for future
  // removal (see decouplingv1.md kill list). When the new Sesiones shell is
  // mounted, this entire block is skipped and the references are null.
  const ingestionCorpusSelect = skipLegacyIngestionController ? null : queryRequired<HTMLSelectElement>(q, "#ingestion-corpus");
  const ingestionBatchTypeSelect = skipLegacyIngestionController ? null : queryRequired<HTMLSelectElement>(q, "#ingestion-batch-type");
  const ingestionDropzone = skipLegacyIngestionController ? null : queryRequired<HTMLElement>(q, "#ingestion-dropzone");
  const ingestionFileInput = skipLegacyIngestionController ? null : queryRequired<HTMLInputElement>(q, "#ingestion-file-input");
  const ingestionFolderInput = skipLegacyIngestionController ? null : queryRequired<HTMLInputElement>(q, "#ingestion-folder-input");
  const ingestionPendingFiles = skipLegacyIngestionController ? null : queryRequired<HTMLParagraphElement>(q, "#ingestion-pending-files");
  const ingestionOverview = skipLegacyIngestionController ? null : queryRequired<HTMLParagraphElement>(q, "#ingestion-overview");
  const ingestionRefreshBtn = skipLegacyIngestionController ? null : queryRequired<HTMLButtonElement>(q, "#ingestion-refresh");
  const ingestionCreateSessionBtn = skipLegacyIngestionController ? null : queryRequired<HTMLButtonElement>(q, "#ingestion-create-session");
  const ingestionSelectFilesBtn = skipLegacyIngestionController ? null : queryRequired<HTMLButtonElement>(q, "#ingestion-select-files");
  const ingestionSelectFolderBtn = skipLegacyIngestionController ? null : queryRequired<HTMLButtonElement>(q, "#ingestion-select-folder");
  const ingestionUploadBtn = skipLegacyIngestionController ? null : queryRequired<HTMLButtonElement>(q, "#ingestion-upload-files");
  const ingestionUploadProgress = skipLegacyIngestionController ? null : queryRequired<HTMLDivElement>(q, "#ingestion-upload-progress");
  const ingestionProcessBtn = skipLegacyIngestionController ? null : queryRequired<HTMLButtonElement>(q, "#ingestion-process-session");
  const ingestionAutoProcessBtn = skipLegacyIngestionController ? null : queryRequired<HTMLButtonElement>(q, "#ingestion-auto-process");
  const ingestionValidateBatchBtn = skipLegacyIngestionController ? null : queryRequired<HTMLButtonElement>(q, "#ingestion-validate-batch");
  const ingestionRetryBtn = skipLegacyIngestionController ? null : queryRequired<HTMLButtonElement>(q, "#ingestion-retry-session");
  const ingestionDeleteSessionBtn = skipLegacyIngestionController ? null : queryRequired<HTMLButtonElement>(q, "#ingestion-delete-session");
  const ingestionSessionMeta = skipLegacyIngestionController ? null : queryRequired<HTMLParagraphElement>(q, "#ingestion-session-meta");
  const ingestionSessionsList = skipLegacyIngestionController ? null : queryRequired<HTMLUListElement>(q, "#ingestion-sessions-list");
  const selectedSessionMeta = skipLegacyIngestionController ? null : queryRequired<HTMLParagraphElement>(q, "#selected-session-meta");
  const ingestionLastError = skipLegacyIngestionController ? null : queryRequired<HTMLDivElement>(q, "#ingestion-last-error");
  const ingestionLastErrorMessage = skipLegacyIngestionController ? null : queryRequired<HTMLParagraphElement>(q, "#ingestion-last-error-message");
  const ingestionLastErrorGuidance = skipLegacyIngestionController ? null : queryRequired<HTMLParagraphElement>(q, "#ingestion-last-error-guidance");
  const ingestionLastErrorNext = skipLegacyIngestionController ? null : queryRequired<HTMLParagraphElement>(q, "#ingestion-last-error-next");
  const ingestionKanban = skipLegacyIngestionController ? null : queryRequired<HTMLDivElement>(q, "#ingestion-kanban");
  const ingestionLogAccordion = skipLegacyIngestionController ? null : queryRequired<HTMLDivElement>(q, "#ingestion-log-accordion");
  const ingestionLogBody = skipLegacyIngestionController ? null : queryRequired<HTMLPreElement>(q, "#ingestion-log-body");
  const ingestionLogCopyBtn = skipLegacyIngestionController ? null : queryRequired<HTMLButtonElement>(q, "#ingestion-log-copy");
  const ingestionAutoStatus = skipLegacyIngestionController ? null : queryRequired<HTMLParagraphElement>(q, "#ingestion-auto-status");
  const addCorpusBtn = q.querySelector<HTMLButtonElement>("#ingestion-add-corpus-btn");
  const addCorpusDialog = q.querySelector<HTMLDialogElement>("#add-corpus-dialog");
  const ingestionBounceLog = q.querySelector<HTMLDetailsElement>("#ingestion-bounce-log");
  const ingestionBounceBody = q.querySelector<HTMLPreElement>("#ingestion-bounce-body");
  const ingestionBounceCopy = q.querySelector<HTMLButtonElement>("#ingestion-bounce-copy");

  async function withThinkingWheel<T>(task: () => Promise<T>): Promise<T> {
    return task();
  }

  const monitorController = hasMonitorDom
    ? createOpsMonitorController({
        i18n,
        stateController,
        dom: {
          monitorTabBtn,
          ingestionTabBtn,
          controlTabBtn,
          embeddingsTabBtn,
          reindexTabBtn,
          monitorPanel,
          ingestionPanel,
          controlPanel,
          embeddingsPanel,
          reindexPanel,
          runsBody: runsBody!,
          timelineNode: timelineNode!,
          timelineMeta: timelineMeta!,
          cascadeNote: cascadeNote!,
          userCascadeNode: userCascadeNode!,
          userCascadeSummary: userCascadeSummary!,
          technicalCascadeNode: technicalCascadeNode!,
          technicalCascadeSummary: technicalCascadeSummary!,
          refreshRunsBtn: refreshRunsBtn!,
        },
        withThinkingWheel,
        setFlash,
      })
    : null;

  const ingestionController = skipLegacyIngestionController
    ? null
    : createOpsIngestionController({
        i18n,
        stateController,
        dom: {
          ingestionCorpusSelect: ingestionCorpusSelect!,
          ingestionBatchTypeSelect: ingestionBatchTypeSelect!,
          ingestionDropzone: ingestionDropzone!,
          ingestionFileInput: ingestionFileInput!,
          ingestionFolderInput: ingestionFolderInput!,
          ingestionSelectFilesBtn: ingestionSelectFilesBtn!,
          ingestionSelectFolderBtn: ingestionSelectFolderBtn!,
          ingestionUploadProgress: ingestionUploadProgress!,
          ingestionPendingFiles: ingestionPendingFiles!,
          ingestionOverview: ingestionOverview!,
          ingestionRefreshBtn: ingestionRefreshBtn!,
          ingestionCreateSessionBtn: ingestionCreateSessionBtn!,
          ingestionUploadBtn: ingestionUploadBtn!,
          ingestionProcessBtn: ingestionProcessBtn!,
          ingestionAutoProcessBtn: ingestionAutoProcessBtn!,
          ingestionValidateBatchBtn: ingestionValidateBatchBtn!,
          ingestionRetryBtn: ingestionRetryBtn!,
          ingestionDeleteSessionBtn: ingestionDeleteSessionBtn!,
          ingestionSessionMeta: ingestionSessionMeta!,
          ingestionSessionsList: ingestionSessionsList!,
          selectedSessionMeta: selectedSessionMeta!,
          ingestionLastError: ingestionLastError!,
          ingestionLastErrorMessage: ingestionLastErrorMessage!,
          ingestionLastErrorGuidance: ingestionLastErrorGuidance!,
          ingestionLastErrorNext: ingestionLastErrorNext!,
          ingestionKanban: ingestionKanban!,
          ingestionLogAccordion: ingestionLogAccordion!,
          ingestionLogBody: ingestionLogBody!,
          ingestionLogCopyBtn: ingestionLogCopyBtn!,
          ingestionAutoStatus: ingestionAutoStatus!,
          addCorpusBtn,
          addCorpusDialog,
          ingestionBounceLog,
          ingestionBounceBody,
          ingestionBounceCopy,
        },
        withThinkingWheel,
        setFlash,
      });

  const corpusLifecycleContainer = q.querySelector<HTMLElement>("#corpus-lifecycle");
  const corpusLifecycleController = corpusLifecycleContainer
    ? createCorpusLifecycleController({
        dom: { container: corpusLifecycleContainer },
        setFlash,
      })
    : null;

  const embeddingsContainer = q.querySelector<HTMLElement>("#embeddings-lifecycle");
  const embeddingsController = embeddingsContainer
    ? createOpsEmbeddingsController({ dom: { container: embeddingsContainer }, setFlash })
    : null;

  const reindexContainer = q.querySelector<HTMLElement>("#reindex-lifecycle");
  const reindexController = reindexContainer
    ? createOpsReindexController({
        dom: { container: reindexContainer },
        setFlash,
        navigateToEmbeddings: () => {
          stateController.setActiveTab("embeddings");
          monitorController?.renderTabs();
        },
      })
    : null;

  monitorController?.bindEvents();
  ingestionController?.bindEvents();
  corpusLifecycleController?.bindEvents();
  embeddingsController?.bindEvents();
  reindexController?.bindEvents();
  monitorController?.renderTabs();
  ingestionController?.render();
  startOpsPolling({
    stateController,
    withThinkingWheel,
    setFlash,
    refreshRuns: monitorController?.refreshRuns ?? (async () => {}),
    refreshIngestion: ingestionController?.refreshIngestion ?? (async () => {}),
    refreshCorpusLifecycle: corpusLifecycleController?.refresh,
    refreshEmbeddings: embeddingsController?.refresh,
    refreshReindex: reindexController?.refresh,
  });
}

export function mountBackstageApp(root: HTMLElement | Document, { i18n }: { i18n: I18nRuntime }): void {
  const q = root as ParentNode;
  const runsBody = q.querySelector<HTMLTableSectionElement>("#runs-body");
  const timelineNode = q.querySelector<HTMLUListElement>("#timeline");
  const timelineMeta = q.querySelector<HTMLParagraphElement>("#timeline-meta");
  const cascadeNote = q.querySelector<HTMLParagraphElement>("#cascade-note");
  const userCascadeNode = q.querySelector<HTMLOListElement>("#user-cascade");
  const userCascadeSummary = q.querySelector<HTMLParagraphElement>("#user-cascade-summary");
  const technicalCascadeNode = q.querySelector<HTMLOListElement>("#technical-cascade");
  const technicalCascadeSummary = q.querySelector<HTMLParagraphElement>("#technical-cascade-summary");
  const refreshRunsBtn = q.querySelector<HTMLButtonElement>("#refresh-runs");

  if (
    !runsBody ||
    !timelineNode ||
    !timelineMeta ||
    !cascadeNote ||
    !userCascadeNode ||
    !userCascadeSummary ||
    !technicalCascadeNode ||
    !technicalCascadeSummary ||
    !refreshRunsBtn
  ) {
    return;
  }

  const stateController = createOpsState();
  const withThinkingWheel = async <T>(task: () => Promise<T>): Promise<T> => task();
  const setFlash = (): void => {};
  const monitorController = createOpsMonitorController({
    i18n,
    stateController,
    dom: {
      monitorTabBtn: null,
      ingestionTabBtn: null,
      controlTabBtn: null,
      embeddingsTabBtn: null,
      reindexTabBtn: null,
      monitorPanel: null,
      ingestionPanel: null,
      controlPanel: null,
      embeddingsPanel: null,
      reindexPanel: null,
      runsBody,
      timelineNode,
      timelineMeta,
      cascadeNote,
      userCascadeNode,
      userCascadeSummary,
      technicalCascadeNode,
      technicalCascadeSummary,
      refreshRunsBtn,
    },
    withThinkingWheel,
    setFlash,
  });

  monitorController.bindEvents();
  monitorController.renderTabs();
  startOpsPolling({
    stateController,
    withThinkingWheel,
    setFlash,
    refreshRuns: monitorController.refreshRuns,
    refreshIngestion: async () => {},
  });
}
