import { queryRequired } from "@/shared/dom/template";
import type { I18nRuntime } from "@/shared/i18n";
import { createCorpusLifecycleController } from "@/features/ops/opsCorpusLifecycleController";
import { createOpsEmbeddingsController } from "@/features/ops/opsEmbeddingsController";
import { createOpsIngestionController } from "@/features/ops/opsIngestionController";
import { createOpsMonitorController } from "@/features/ops/opsMonitorController";
import { createOpsReindexController } from "@/features/ops/opsReindexController";
import { startOpsPolling } from "@/features/ops/opsPolling";
import { createOpsState } from "@/features/ops/opsState";

export function mountOpsApp(root: HTMLElement | Document, { i18n }: { i18n: I18nRuntime }): void {
  const q = root as ParentNode;

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

  const ingestionCorpusSelect = queryRequired<HTMLSelectElement>(q, "#ingestion-corpus");
  const ingestionBatchTypeSelect = queryRequired<HTMLSelectElement>(q, "#ingestion-batch-type");
  const ingestionDropzone = queryRequired<HTMLElement>(q, "#ingestion-dropzone");
  const ingestionFileInput = queryRequired<HTMLInputElement>(q, "#ingestion-file-input");
  const ingestionFolderInput = queryRequired<HTMLInputElement>(q, "#ingestion-folder-input");
  const ingestionPendingFiles = queryRequired<HTMLParagraphElement>(q, "#ingestion-pending-files");
  const ingestionOverview = queryRequired<HTMLParagraphElement>(q, "#ingestion-overview");
  const ingestionFlash = queryRequired<HTMLDivElement>(q, "#ingestion-flash");
  const ingestionRefreshBtn = queryRequired<HTMLButtonElement>(q, "#ingestion-refresh");
  const ingestionCreateSessionBtn = queryRequired<HTMLButtonElement>(q, "#ingestion-create-session");
  const ingestionSelectFilesBtn = queryRequired<HTMLButtonElement>(q, "#ingestion-select-files");
  const ingestionSelectFolderBtn = queryRequired<HTMLButtonElement>(q, "#ingestion-select-folder");
  const ingestionUploadBtn = queryRequired<HTMLButtonElement>(q, "#ingestion-upload-files");
  const ingestionUploadProgress = queryRequired<HTMLDivElement>(q, "#ingestion-upload-progress");
  const ingestionProcessBtn = queryRequired<HTMLButtonElement>(q, "#ingestion-process-session");
  const ingestionAutoProcessBtn = queryRequired<HTMLButtonElement>(q, "#ingestion-auto-process");
  const ingestionValidateBatchBtn = queryRequired<HTMLButtonElement>(q, "#ingestion-validate-batch");
  const ingestionRetryBtn = queryRequired<HTMLButtonElement>(q, "#ingestion-retry-session");
  const ingestionDeleteSessionBtn = queryRequired<HTMLButtonElement>(q, "#ingestion-delete-session");
  const ingestionSessionMeta = queryRequired<HTMLParagraphElement>(q, "#ingestion-session-meta");
  const ingestionSessionsList = queryRequired<HTMLUListElement>(q, "#ingestion-sessions-list");
  const selectedSessionMeta = queryRequired<HTMLParagraphElement>(q, "#selected-session-meta");
  const ingestionLastError = queryRequired<HTMLDivElement>(q, "#ingestion-last-error");
  const ingestionLastErrorMessage = queryRequired<HTMLParagraphElement>(q, "#ingestion-last-error-message");
  const ingestionLastErrorGuidance = queryRequired<HTMLParagraphElement>(q, "#ingestion-last-error-guidance");
  const ingestionLastErrorNext = queryRequired<HTMLParagraphElement>(q, "#ingestion-last-error-next");
  const ingestionKanban = queryRequired<HTMLDivElement>(q, "#ingestion-kanban");
  const ingestionLogAccordion = queryRequired<HTMLDivElement>(q, "#ingestion-log-accordion");
  const ingestionLogBody = queryRequired<HTMLPreElement>(q, "#ingestion-log-body");
  const ingestionLogCopyBtn = queryRequired<HTMLButtonElement>(q, "#ingestion-log-copy");
  const ingestionAutoStatus = queryRequired<HTMLParagraphElement>(q, "#ingestion-auto-status");
  const addCorpusBtn = q.querySelector<HTMLButtonElement>("#ingestion-add-corpus-btn");
  const addCorpusDialog = q.querySelector<HTMLDialogElement>("#add-corpus-dialog");
  const ingestionBounceLog = q.querySelector<HTMLDetailsElement>("#ingestion-bounce-log");
  const ingestionBounceBody = q.querySelector<HTMLPreElement>("#ingestion-bounce-body");
  const ingestionBounceCopy = q.querySelector<HTMLButtonElement>("#ingestion-bounce-copy");

  const stateController = createOpsState();

  function setFlash(message = "", tone: "success" | "error" = "success"): void {
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

  const ingestionController = createOpsIngestionController({
    i18n,
    stateController,
    dom: {
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
  ingestionController.bindEvents();
  corpusLifecycleController?.bindEvents();
  embeddingsController?.bindEvents();
  reindexController?.bindEvents();
  monitorController?.renderTabs();
  ingestionController.render();
  startOpsPolling({
    stateController,
    withThinkingWheel,
    setFlash,
    refreshRuns: monitorController?.refreshRuns ?? (async () => {}),
    refreshIngestion: ingestionController.refreshIngestion,
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
