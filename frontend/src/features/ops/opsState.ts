import {
  isRunningSession,
  readStoredSessionId,
  readStoredTab,
  storeActiveTab,
  storeSessionId,
  type FolderUploadProgress,
  type IngestionCorpus,
  type IntakeEntry,
  type PreflightManifest,
  type PreflightScanProgress,
  type RejectedArtifact,
  type ReviewPlan,
  type IngestionSession,
  type OpsTabKey,
} from "@/features/ops/opsTypes";

export interface OpsStateData {
  activeTab: OpsTabKey;
  corpora: IngestionCorpus[];
  selectedCorpus: string;
  sessions: IngestionSession[];
  selectedSessionId: string;
  selectedSession: IngestionSession | null;
  /** "Will ingest" subset — derived from intake after preflight. `directFolderIngest`
   * consumes this. While preflight is in flight this is empty even though
   * `intake` has rows. */
  pendingFiles: File[];
  /** Window 1 — every file the user has dropped/picked, with per-file verdict. */
  intake: IntakeEntry[];
  /** Windows 2 + 3 after preflight resolves; null while no preflight has run yet
   * or after `clearIntake`. */
  reviewPlan: ReviewPlan | null;
  /** Monotonic id bumped on every new drop. Guards against race when two rapid
   * drops overlap — only the most recent preflight is allowed to commit. */
  preflightRunId: number;
  mutating: boolean;
  folderUploadProgress: FolderUploadProgress | null;
  /** Relative paths for files from folder selection (keyed by File reference). */
  folderRelativePaths: Map<File, string>;
  rejectedArtifacts: RejectedArtifact[];
  preflightManifest: PreflightManifest | null;
  preflightScanProgress: PreflightScanProgress | null;
}

export interface OpsStateController {
  state: OpsStateData;
  clearSelectionAfterDelete: () => void;
  getFocusedRunningSessionId: () => string;
  selectedCorpusConfig: () => IngestionCorpus | undefined;
  setActiveTab: (tab: OpsTabKey) => void;
  setCorpora: (corpora: IngestionCorpus[]) => void;
  setFolderUploadProgress: (progress: FolderUploadProgress | null) => void;
  setMutating: (value: boolean) => void;
  setPendingFiles: (files: File[]) => void;
  setIntake: (entries: IntakeEntry[]) => void;
  setReviewPlan: (plan: ReviewPlan | null) => void;
  bumpPreflightRunId: () => number;
  setPreflightManifest: (manifest: PreflightManifest | null) => void;
  setPreflightScanProgress: (progress: PreflightScanProgress | null) => void;
  setSelectedCorpus: (corpus: string) => void;
  setSelectedSession: (session: IngestionSession | null) => void;
  setSessions: (sessions: IngestionSession[]) => void;
  syncSelectedSession: () => void;
  upsertSession: (session: IngestionSession) => void;
}

export function createOpsState(): OpsStateController {
  const state: OpsStateData = {
    activeTab: readStoredTab(),
    corpora: [],
    selectedCorpus: "autogenerar",
    sessions: [],
    selectedSessionId: readStoredSessionId(),
    selectedSession: null,
    pendingFiles: [],
    intake: [],
    reviewPlan: null,
    preflightRunId: 0,
    mutating: false,
    folderUploadProgress: null,
    folderRelativePaths: new Map(),
    rejectedArtifacts: [],
    preflightManifest: null,
    preflightScanProgress: null,
  };

  function selectedCorpusConfig(): IngestionCorpus | undefined {
    return state.corpora.find((corpus) => corpus.key === state.selectedCorpus);
  }

  function setActiveTab(tab: OpsTabKey): void {
    state.activeTab = tab;
    storeActiveTab(tab);
  }

  function setCorpora(corpora: IngestionCorpus[]): void {
    state.corpora = [...corpora];
  }

  function setFolderUploadProgress(progress: FolderUploadProgress | null): void {
    state.folderUploadProgress = progress;
  }

  function setPreflightManifest(manifest: PreflightManifest | null): void {
    state.preflightManifest = manifest;
  }

  function setPreflightScanProgress(progress: PreflightScanProgress | null): void {
    state.preflightScanProgress = progress;
  }

  function setMutating(value: boolean): void {
    state.mutating = value;
  }

  function setPendingFiles(files: File[]): void {
    state.pendingFiles = [...files];
  }

  function setIntake(entries: IntakeEntry[]): void {
    state.intake = [...entries];
  }

  function setReviewPlan(plan: ReviewPlan | null): void {
    state.reviewPlan = plan ? { ...plan, willIngest: [...plan.willIngest], bounced: [...plan.bounced] } : null;
  }

  function bumpPreflightRunId(): number {
    state.preflightRunId += 1;
    return state.preflightRunId;
  }

  function setSelectedCorpus(corpus: string): void {
    state.selectedCorpus = corpus;
  }

  function setSelectedSession(session: IngestionSession | null): void {
    state.selectedSession = session;
    state.selectedSessionId = session?.session_id || "";
    storeSessionId(session?.session_id || null);
    // If a session was explicitly selected, clear the suppress flag
    if (session) _suppressAutoSelect = false;
  }

  function clearSelectionAfterDelete(): void {
    _suppressAutoSelect = true;
    setSelectedSession(null);
  }

  function setSessions(sessions: IngestionSession[]): void {
    state.sessions = [...sessions];
  }

  // When true, syncSelectedSession will NOT fall back to sessions[0].
  // Set after explicit delete to avoid auto-selecting a different session.
  let _suppressAutoSelect = false;

  function syncSelectedSession(): void {
    if (state.selectedSessionId) {
      const found = state.sessions.find((s) => s.session_id === state.selectedSessionId) || null;
      setSelectedSession(found);
      return;
    }
    // No session selected: auto-select first session only if we aren't
    // in a post-delete state where the user explicitly cleared the selection.
    if (_suppressAutoSelect) {
      setSelectedSession(null);
      return;
    }
    setSelectedSession(state.sessions[0] || null);
  }

  function upsertSession(session: IngestionSession): void {
    const remaining = state.sessions.filter((item) => item.session_id !== session.session_id);
    state.sessions = [session, ...remaining].sort(
      (left, right) => Date.parse(String(right.updated_at || 0)) - Date.parse(String(left.updated_at || 0))
    );
    setSelectedSession(session);
  }

  function getFocusedRunningSessionId(): string {
    return isRunningSession(String(state.selectedSession?.status || "")) ? state.selectedSessionId : "";
  }

  return {
    state,
    clearSelectionAfterDelete,
    getFocusedRunningSessionId,
    selectedCorpusConfig,
    setActiveTab,
    setCorpora,
    setFolderUploadProgress,
    setMutating,
    setPendingFiles,
    setIntake,
    setReviewPlan,
    bumpPreflightRunId,
    setPreflightManifest,
    setPreflightScanProgress,
    setSelectedCorpus,
    setSelectedSession,
    setSessions,
    syncSelectedSession,
    upsertSession,
  };
}
