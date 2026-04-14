import { ApiError } from "@/shared/api/client";
import { getLocalStorage } from "@/shared/browser/storage";
import type { I18nRuntime } from "@/shared/i18n";

export type OpsRun = {
  run_id: string;
  trace_id?: string;
  chat_run_id?: string;
  status?: string;
  started_at?: string;
  ended_at?: string;
  summary?: Record<string, unknown>;
};

export type OpsTimelineEvent = {
  stage?: string;
  status?: string;
  at?: string;
  duration_ms?: number;
  details?: unknown;
};

export type OpsCascadeStep = {
  id: string;
  label: string;
  stage?: string | null;
  status?: string;
  duration_ms?: number | null;
  offset_ms?: number | null;
  cumulative_ms?: number | null;
  absolute_elapsed_ms?: number | null;
  details?: Record<string, unknown>;
  at?: string | null;
  kind?: "user" | "technical";
};

export type OpsWaterfall = {
  kind?: "user" | "technical";
  title?: string;
  total_ms?: number;
  available_steps?: number;
  chat_run_id?: string | null;
  steps?: OpsCascadeStep[];
};

export type OpsRunCascadeResponse = {
  ok?: boolean;
  run_id?: string;
  run?: OpsRun;
  timeline?: OpsTimelineEvent[];
  technical_waterfall?: OpsWaterfall;
  user_waterfall?: OpsWaterfall;
};

export type RejectedArtifact = {
  file: File;
  reason: string;
};

export type IngestionCorpusAttention = {
  session_id: string;
  status: string;
  filenames: string[];
};

export type IngestionCorpus = {
  key: string;
  label: string;
  active: boolean;
  pais?: string;
  topic?: string;
  attention?: IngestionCorpusAttention[];
};

export type IngestionError = {
  code?: string;
  message?: string;
  guidance?: string;
  next_step?: string;
};

export type IngestionDocument = {
  doc_id: string;
  filename: string;
  mime: string;
  bytes: number;
  checksum: string;
  status: string;
  stage: string;
  progress: number;
  attempts: number;
  duplicate_of?: string | null;
  output_raw_relative_path?: string | null;
  output_normalized_relative_paths?: string[];
  processed_upload_artifact_path?: string | null;
  archived_at?: string | null;
  batch_type?: string;
  error?: IngestionError | null;
  created_at?: string;
  updated_at?: string;
  heartbeat_at?: string;

  // Classification
  detected_topic?: string;
  topic_confidence?: number;
  detected_type?: string;
  type_confidence?: number;
  combined_confidence?: number;
  classification_source?: "keywords" | "keywords+llm" | "manual" | "filename_override" | "corpus" | "autogenerar";
  type_label?: string;
  topic_label?: string;
  is_raw?: boolean;
  suggestion?: { topic?: string; type?: string };

  // Autogenerar
  autogenerar_label?: string | null;
  autogenerar_rationale?: string | null;
  autogenerar_resolved_topic?: string | null;
  autogenerar_synonym_confidence?: number;
  autogenerar_is_new?: boolean;
  autogenerar_suggested_key?: string | null;

  // Dedup
  dedup?: {
    match_type: "exact_duplicate" | "near_duplicate" | "revision";
    match_reason: "hash" | "filename" | "heading";
    existing_doc_id: string;
    existing_filename: string;
    existing_chunk_count?: number;
    existing_updated_at?: string;
  };

  // Delta/lineage
  derived_from_doc_id?: string | null;
  delta_section_count?: number;

  // Results
  chunk_count?: number;
  elapsed_ms?: number;
  replaced_doc_id?: string;

  // Folder ingestion
  source_relative_path?: string | null;
};

export type IngestionBatchSummary = {
  total: number;
  queued: number;
  processing: number;
  done: number;
  failed: number;
  skipped_duplicate: number;
  pending_batch_gate: number;
  bounced: number;
  raw_blocked?: number;
};

export type IngestionSession = {
  session_id: string;
  corpus: string;
  status: string;
  created_at: string;
  updated_at: string;
  heartbeat_at?: string;
  gate_sub_stage?: string;
  wip_sync_status?: string;
  gate_pending_doc_ids?: string[];
  documents: IngestionDocument[];
  batch_summary: IngestionBatchSummary;
  last_error?: IngestionError | null;
};

export type CorporaPayload = {
  corpora?: IngestionCorpus[];
  default?: string;
};

export type IngestionSessionsPayload = {
  sessions?: IngestionSession[];
};

export type IngestionSessionPayload = {
  session?: IngestionSession;
};

export type IngestionActionPayload = {
  ok?: boolean;
  session?: IngestionSession;
  document?: IngestionDocument;
  status?: string;
  started?: boolean;
  removed?: number;
};

export type EjectResult = {
  ejected: boolean;
  session_id: string;
  ejected_files: number;
  path: "instant" | "rollback";
  supabase_purged: boolean;
  index_rebuilt?: boolean;
  errors?: string[];
};

export const TYPE_LABELS: Record<string, string> = {
  normative_base: "Normativa",
  interpretative_guidance: "Interpretación",
  practica_erp: "Práctica",
};

export const TOPIC_LABELS: Record<string, string> = {
  declaracion_renta: "Renta",
  iva: "IVA",
  laboral: "Laboral",
  facturacion_electronica: "Facturación",
  estados_financieros_niif: "NIIF",
  ica: "ICA",
  calendario_obligaciones: "Calendarios",
  retencion_fuente: "Retención",
  regimen_sancionatorio: "Sanciones",
  regimen_cambiario: "Régimen Cambiario",
  impuesto_al_patrimonio: "Patrimonio",
  informacion_exogena: "Exógena",
  proteccion_de_datos: "Datos",
  obligaciones_mercantiles: "Mercantil",
  obligaciones_profesionales_contador: "Obligaciones Contador",
  rut_responsabilidades: "RUT",
  gravamen_movimiento_financiero_4x1000: "GMF 4×1000",
  beneficiario_final: "Beneficiario Final",
  contratacion_estatal: "Contratación Estatal",
  reforma_pensional: "Reforma Pensional",
  zomac_incentivos: "ZOMAC",
};

export const TYPE_ALIASES: Record<string, string> = {
  normativa: "normative_base",
  norma: "normative_base",
  interpretacion: "interpretative_guidance",
  "interpretación": "interpretative_guidance",
  expertos: "interpretative_guidance",
  secundaria: "interpretative_guidance",
  practica: "practica_erp",
  "práctica": "practica_erp",
  erp: "practica_erp",
  loggro: "practica_erp",
  terciaria: "practica_erp",
};

export type FolderUploadProgress = {
  total: number;
  uploaded: number;
  failed: number;
  uploading: boolean;
};

// ── Pre-flight types ──────────────────────────────────────────────

export type PreflightEntry = {
  filename: string;
  relative_path: string;
  size: number;
  content_hash: string;
  category: "artifact" | "exact_duplicate" | "revision" | "new";
  reason: string;
  existing_doc_id: string | null;
  existing_filename: string | null;
  existing_chunk_count: number | null;
  revision_direction: string | null;
};

export type PreflightManifest = {
  artifacts: PreflightEntry[];
  duplicates: PreflightEntry[];
  revisions: PreflightEntry[];
  new_files: PreflightEntry[];
  scanned: number;
  elapsed_ms: number;
};

export type PreflightScanProgress = {
  total: number;
  hashed: number;
  scanning: boolean;
};

// ── Three-window intake model ─────────────────────────────────────
//
// Users drop files into the dropzone (window 1 = "Intake", raw).
// Dedup runs automatically: hash → POST /api/ingestion/preflight.
// Results are split into window 2 ("Se ingerirán" = new + revisions,
// user can cancel any) and window 3 ("Rebotados" = duplicates +
// artifacts, read-only). Nothing hits the server until the user
// clicks "Aprobar e ingerir".

export type IntakeVerdict = "pending" | "new" | "revision" | "duplicate" | "artifact" | "unreadable";

export type IntakeEntry = {
  /** Raw File reference — kept so we can hand it to directFolderIngest() later. */
  file: File;
  /** webkitRelativePath or file.name — the key preflight matches on. */
  relativePath: string;
  /** SHA-256 hex, null until hashIntakeEntries has run. */
  contentHash: string | null;
  /** Post-preflight classification; "pending" while preflight is in flight. */
  verdict: IntakeVerdict;
  /** Full preflight row for this file; null until applyManifestToIntake has run. */
  preflightEntry: PreflightEntry | null;
};

export type ReviewPlan = {
  /** window 2 — what the user is about to ingest (new + revision). */
  willIngest: IntakeEntry[];
  /** window 3 — read-only; what was bounced (duplicate + artifact + unreadable). */
  bounced: IntakeEntry[];
  /** how many files were scanned in this preflight pass. */
  scanned: number;
  /** server-reported elapsed ms for the preflight call. */
  elapsedMs: number;
  /** true while a newer drop is re-running preflight; freezes approval. */
  stalePartial: boolean;
};

export type OpsTabKey = "monitor" | "ingestion" | "control" | "embeddings" | "reindex";

export type CorpusTargetStatus = {
  available: boolean;
  generation_id?: string | null;
  documents?: number;
  chunks?: number;
  embeddings_complete?: boolean;
  knowledge_class_counts?: Record<string, number>;
  activated_at?: string;
  error?: string;
};

export type CorpusStatusPayload = {
  production: CorpusTargetStatus;
  wip: CorpusTargetStatus;
  delta: {
    documents: string;
    chunks: string;
    promotable: boolean;
  };
  preflight_ready?: boolean;
  preflight_reasons?: string[];
  preflight_checks?: CorpusVerificationCheck[];
  audit_missing?: boolean;
  current_operation?: CorpusOperationSummary | null;
  last_operation?: CorpusOperationSummary | null;
  rollback_available?: boolean;
  rollback_generation_id?: string | null;
  rollback_reason?: string | null;
};

export type CorpusVerificationCheck = {
  id: string;
  label: string;
  ok: boolean;
  detail: string;
  phase?: string | null;
};

export type CorpusOperationStage = {
  id: string;
  label: string;
  state: "pending" | "active" | "completed" | "failed";
};

export type CorpusOperationFailure = {
  message: string;
  stage?: string | null;
  at?: string | null;
};

export type CorpusOperationCheckpoint = {
  phase?: string | null;
  cursor?: number;
  total?: number;
  at?: string | null;
};

export type CorpusOperationSummary = {
  job_id: string;
  job_type: string;
  kind: "rebuild" | "rollback" | "audit";
  status: "queued" | "running" | "completed" | "failed" | "cancelled";
  severity: "green" | "yellow" | "red";
  operation_state_code?: string | null;
  stage?: string | null;
  stage_label?: string | null;
  stage_status?: string;
  stages?: CorpusOperationStage[];
  started_at?: string;
  updated_at?: string;
  completed_at?: string | null;
  heartbeat_at?: string | null;
  heartbeat_stale?: boolean;
  source_generation_id?: string | null;
  production_generation_id?: string | null;
  target_generation_id?: string | null;
  production_changed?: boolean;
  checks?: CorpusVerificationCheck[];
  failures?: CorpusOperationFailure[];
  log_tail?: string;
  error?: string | null;
  operation_ok?: boolean;
  verification_ok?: boolean;
  artifact_path?: string | null;
  resume_supported?: boolean;
  resume_job_id?: string | null;
  last_checkpoint?: CorpusOperationCheckpoint | null;
  mode?: string | null;
  force_full_upsert?: boolean;
  current_phase?: string | null;
  batch_cursor?: number;
  processed_counts?: Record<string, number>;
  promotion_summary?: PromotionSummary | null;
};

export type PromotionTargetSnapshot = {
  generation_id?: string;
  documents?: number;
  chunks?: number;
  embeddings_complete?: boolean;
  knowledge_class_counts?: Record<string, number>;
  activated_at?: string;
  available?: boolean;
  error?: string;
};

export type PromotionSummary = {
  before?: PromotionTargetSnapshot | null;
  after?: PromotionTargetSnapshot | null;
  delta?: { documents?: number; chunks?: number } | null;
  plan_result?: Record<string, number | string | undefined | null> | null;
};

export type CorpusOperationLaunchResult = {
  ok?: boolean;
  job_id?: string;
  status?: string;
  job_type?: string;
  error?: string;
};

const OPS_ACTIVE_TAB_STORAGE_KEY = "lia_backstage_ops_active_tab";
const INGESTION_SESSION_STORAGE_KEY = "lia_backstage_ops_ingestion_session_id";

export function readStoredTab(): OpsTabKey {
  const storage = getLocalStorage();
  try {
    const value = String(storage.getItem(OPS_ACTIVE_TAB_STORAGE_KEY) || "").trim();
    if (value === "ingestion" || value === "control" || value === "embeddings" || value === "reindex") return value;
    return "monitor";
  } catch (_error) {
    return "monitor";
  }
}

export function storeActiveTab(tab: OpsTabKey): void {
  const storage = getLocalStorage();
  try {
    storage.setItem(OPS_ACTIVE_TAB_STORAGE_KEY, tab);
  } catch (_error) {
    // Ignore storage failures.
  }
}

export function readStoredSessionId(): string {
  const storage = getLocalStorage();
  try {
    return String(storage.getItem(INGESTION_SESSION_STORAGE_KEY) || "").trim();
  } catch (_error) {
    return "";
  }
}

export function storeSessionId(sessionId: string | null): void {
  const storage = getLocalStorage();
  try {
    if (!sessionId) {
      storage.removeItem(INGESTION_SESSION_STORAGE_KEY);
      return;
    }
    storage.setItem(INGESTION_SESSION_STORAGE_KEY, sessionId);
  } catch (_error) {
    // Ignore storage failures.
  }
}

export function isRunningSession(status: string): boolean {
  return status === "processing" || status === "running_batch_gates";
}

/** A session is "completed" when all its documents have been fully processed.
 *  Completed sessions are protected from deletion via UI — only devs via console. */
export function isCompletedSession(session: IngestionSession | null | undefined): boolean {
  if (!session) return false;
  const s = String(session.status || "").toLowerCase();
  if (s === "done" || s === "completed") return true;
  // Also protect sessions where every document is done/completed/skipped
  const docs = session.documents || [];
  if (docs.length === 0) return false;
  return docs.every((d) => {
    const ds = String(d.status || "").toLowerCase();
    return ds === "done" || ds === "completed" || ds === "skipped_duplicate" || ds === "bounced";
  });
}

export function statusTone(status: string): "ok" | "error" | "warn" {
  const normalized = String(status || "").trim().toLowerCase();
  if (normalized === "failed" || normalized === "error") {
    return "error";
  }
  if (
    normalized === "processing" ||
    normalized === "running_batch_gates" ||
    normalized === "needs_retry_batch_gate" ||
    normalized === "queued" ||
    normalized === "uploading" ||
    normalized === "extracting" ||
    normalized === "etl" ||
    normalized === "writing" ||
    normalized === "gates" ||
    normalized === "in_progress" ||
    normalized === "partial_failed" ||
    normalized === "raw" ||
    normalized === "pending_dedup"
  ) {
    return "warn";
  }
  return "ok";
}

export function formatOpsError(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message || `HTTP ${error.status}`;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return String(error || "unknown_error");
}

export function formatBatchType(batchType: string | undefined, i18n: I18nRuntime): string {
  switch (String(batchType || "").trim()) {
    case "normative_base":
      return i18n.t("ops.ingestion.batchType.normative");
    case "interpretative_guidance":
      return i18n.t("ops.ingestion.batchType.interpretative");
    case "practica_erp":
      return i18n.t("ops.ingestion.batchType.practical");
    default:
      return String(batchType || "-");
  }
}

export function formatBytes(bytes: number, i18n: I18nRuntime): string {
  const value = Number(bytes || 0);
  if (!Number.isFinite(value) || value <= 0) return "0 B";
  if (value >= 1024 * 1024) {
    return `${i18n.formatNumber(value / (1024 * 1024), { maximumFractionDigits: 1 })} MB`;
  }
  if (value >= 1024) {
    return `${i18n.formatNumber(value / 1024, { maximumFractionDigits: 1 })} KB`;
  }
  return `${i18n.formatNumber(value)} B`;
}

export function buildSummaryLine(summary: IngestionBatchSummary | undefined, i18n: I18nRuntime): string {
  const safe = summary || {
    total: 0,
    queued: 0,
    processing: 0,
    done: 0,
    failed: 0,
    skipped_duplicate: 0,
    pending_batch_gate: 0,
    bounced: 0,
  };
  const parts = [
    `${i18n.t("ops.ingestion.summary.total")} ${safe.total || 0}`,
    `${i18n.t("ops.ingestion.summary.done")} ${safe.done || 0}`,
    `${i18n.t("ops.ingestion.summary.failed")} ${safe.failed || 0}`,
    `${i18n.t("ops.ingestion.summary.queued")} ${safe.queued || 0}`,
    `${i18n.t("ops.ingestion.summary.gate")} ${safe.pending_batch_gate || 0}`,
  ];
  const bouncedCount = Number(safe.bounced || 0);
  if (bouncedCount > 0) {
    parts.push(`Rebotados ${bouncedCount}`);
  }
  return parts.join(" · ");
}

export type LivenessLevel = "alive" | "slow" | "stalled";

/**
 * Determine liveness based on the most recent heartbeat/update timestamp.
 * Thresholds are stage-aware: the gates stage (index rebuild, Supabase sync)
 * legitimately runs for 1-3 minutes between heartbeats, so it uses relaxed
 * thresholds to avoid false "stalled" signals.
 *
 * Default thresholds:
 * - alive:   < 30s since last signal
 * - slow:    30s–120s
 * - stalled: > 120s
 *
 * Gates thresholds:
 * - alive:   < 90s since last signal
 * - slow:    90s–300s
 * - stalled: > 300s
 */
export function classifyLiveness(
  heartbeatAt: string | undefined,
  updatedAt: string | undefined,
  stage?: string,
): LivenessLevel {
  const raw = heartbeatAt || updatedAt || "";
  if (!raw) return "stalled";
  const ts = Date.parse(raw);
  if (Number.isNaN(ts)) return "stalled";
  const elapsedMs = Date.now() - ts;
  const isGates = stage === "gates";
  const aliveThreshold = isGates ? 90_000 : 30_000;
  const slowThreshold = isGates ? 300_000 : 120_000;
  if (elapsedMs < aliveThreshold) return "alive";
  if (elapsedMs < slowThreshold) return "slow";
  return "stalled";
}

/**
 * Human-readable elapsed label in Spanish (e.g. "hace 3m 22s").
 */
export function formatElapsed(heartbeatAt: string | undefined, updatedAt: string | undefined): string {
  const raw = heartbeatAt || updatedAt || "";
  if (!raw) return "-";
  const ts = Date.parse(raw);
  if (Number.isNaN(ts)) return "-";
  const elapsedMs = Math.max(0, Date.now() - ts);
  const totalSeconds = Math.floor(elapsedMs / 1000);
  if (totalSeconds < 5) return "ahora";
  if (totalSeconds < 60) return `hace ${totalSeconds}s`;
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (minutes < 60) return `hace ${minutes}m ${seconds}s`;
  const hours = Math.floor(minutes / 60);
  return `hace ${hours}h ${minutes % 60}m`;
}

const _GATE_SUB_STAGE_LABELS: Record<string, string> = {
  validating: "validando corpus",
  manifest: "activando manifest",
  indexing: "reconstruyendo índice",
  "indexing/scanning": "escaneando documentos",
  "indexing/chunking": "generando chunks",
  "indexing/writing_indexes": "escribiendo índices",
  "indexing/syncing": "sincronizando Supabase",
  "indexing/auditing": "auditando calidad",
};

export function formatGateSubStage(subStage: string | undefined): string {
  if (!subStage) return "";
  // Exact match first, then try without the chunking progress suffix (e.g. "indexing/chunking:45/120")
  if (_GATE_SUB_STAGE_LABELS[subStage]) return _GATE_SUB_STAGE_LABELS[subStage];
  const colonIdx = subStage.indexOf(":");
  if (colonIdx > 0) {
    const base = subStage.slice(0, colonIdx);
    const detail = subStage.slice(colonIdx + 1);
    const label = _GATE_SUB_STAGE_LABELS[base];
    if (label) return `${label} (${detail})`;
  }
  return subStage;
}

/**
 * Formats a UTC timestamp as a human-readable date+time in Colombia time (America/Bogota, UTC-5).
 * Returns an empty string if the timestamp is missing or unparseable.
 */
export function formatColombiaDateTime(isoString: string | undefined): string {
  if (!isoString) return "";
  const ts = Date.parse(isoString);
  if (Number.isNaN(ts)) return "";
  try {
    return new Intl.DateTimeFormat("es-CO", {
      timeZone: "America/Bogota",
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    }).format(new Date(ts));
  } catch {
    return "";
  }
}

export function buildProgressNode(progress: number, stage?: string): HTMLDivElement {
  const clamped = Math.max(0, Math.min(100, Number(progress || 0)));
  const wrapper = document.createElement("div");
  wrapper.className = "ops-progress";

  const bar = document.createElement("div");
  bar.className = "ops-progress-bar";

  const fill = document.createElement("span");
  fill.className = "ops-progress-fill";
  // Add shimmer animation when in gates stage to indicate ongoing work
  if (stage === "gates" && clamped > 0 && clamped < 100) {
    fill.classList.add("ops-progress-active");
  }
  fill.style.width = `${clamped}%`;

  const label = document.createElement("span");
  label.className = "ops-progress-label";
  label.textContent = `${clamped}%`;

  bar.appendChild(fill);
  wrapper.append(bar, label);
  return wrapper;
}

// ── Embedding & Reindex status types ──────────────────────────────

export type EmbeddingProgress = {
  total: number;
  pending: number;
  embedded: number;
  failed: number;
  upsert_failures: number;
  current_batch: number;
  total_batches: number;
  batch_size: number;
  elapsed_seconds: number;
  rate_chunks_per_sec: number;
  eta_seconds: number | null;
  pct_complete: number;
  last_cursor_id: string | null;
};

export type EmbeddingQualityReport = {
  mean_cosine_similarity: number;
  min_cosine_similarity: number;
  max_cosine_similarity: number;
  sample_pairs: number;
  collapsed_warning: boolean;
  noise_warning: boolean;
  too_few_samples?: boolean;
};

export type EmbeddingOperation = {
  job_id: string;
  status: string;
  started_at: string;
  updated_at: string;
  heartbeat_at: string;
  target: string;
  force: boolean;
  progress: EmbeddingProgress;
  quality_report: EmbeddingQualityReport | null;
  checks: Array<{ id: string; label: string; ok: boolean; detail: string }>;
  log_tail: string;
  error: string;
};

export type ApiHealthProbe = {
  ok: boolean;
  detail: string;
  latency_ms?: number;
};

export type EmbeddingStatusPayload = {
  target: string;
  total_chunks: number;
  embedded_chunks: number;
  null_embedding_chunks: number;
  coverage_pct: number;
  current_operation: EmbeddingOperation | null;
  last_operation: EmbeddingOperation | null;
  api_health?: ApiHealthProbe;
};

export type ReindexStage = {
  id: string;
  label: string;
  state: "pending" | "active" | "completed" | "failed";
};

export type ReindexQualityReport = {
  documents_indexed: number;
  chunks_generated?: number;
  knowledge_class_counts?: Record<string, number>;
  blocking_issues?: number;
  anchor_audit_summary?: Record<string, unknown>;
  unique_summaries_pct?: number;
  duplicate_texts?: Record<string, number>;
};

export type ReindexOperation = {
  job_id: string;
  status: string;
  started_at: string;
  updated_at: string;
  heartbeat_at: string;
  mode: string;
  supabase_sync_target: string;
  stages: ReindexStage[];
  progress: Record<string, unknown>;
  quality_report: ReindexQualityReport | null;
  checks: Array<{ id: string; label: string; ok: boolean; detail: string }>;
  log_tail: string;
  error: string;
};

export type ReindexStatusPayload = {
  current_operation: ReindexOperation | null;
  last_operation: ReindexOperation | null;
};
