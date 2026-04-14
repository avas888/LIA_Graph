import type { I18nRuntime } from "@/shared/i18n";
import {
  buildProgressNode,
  classifyLiveness,
  formatBytes,
  formatColombiaDateTime,
  formatElapsed,
  formatGateSubStage,
  statusTone,
  TOPIC_LABELS,
  TYPE_LABELS,
  type IngestionCorpus,
  type IngestionDocument,
  type IngestionSession,
} from "@/features/ops/opsTypes";

/**
 * Kanban column identifiers in display order.
 * 3-column layout per design: Pendiente | En proceso | Procesado.
 * Errors stay in "En proceso" with red card tone.
 */
const KANBAN_COLUMNS = [
  "pending",
  "processing",
  "done",
] as const;

type KanbanColumn = (typeof KANBAN_COLUMNS)[number];

const COLUMN_LABELS: Record<KanbanColumn, string> = {
  pending: "Pendiente",
  processing: "En proceso",
  done: "Procesado",
};

const COLUMN_ICONS: Record<KanbanColumn, string> = {
  pending: "\u23F3",
  processing: "\uD83D\uDD04",
  done: "\u2705",
};

/** Max concurrent docs allowed in the processing column. */
const MAX_PROCESSING = 5;

/**
 * Maps a document status string to a kanban column.
 * Errors land in "processing" so they're visible inline, not hidden in a separate column.
 */
function docStatusToColumn(status: string): KanbanColumn {
  const s = String(status || "").toLowerCase();
  if (s === "done" || s === "completed" || s === "skipped_duplicate" || s === "bounced") return "done";
  if (
    s === "in_progress" ||
    s === "processing" ||
    s === "extracting" ||
    s === "etl" ||
    s === "writing" ||
    s === "gates" ||
    s === "uploading" ||
    s === "running_batch_gates" ||
    s === "needs_retry_batch_gate" ||
    s === "failed" ||
    s === "error" ||
    s === "partial_failed"
  )
    return "processing";
  // pending + classifying + needs_classification + duplicate_detected + queued + uploaded + raw
  return "pending";
}

/**
 * Renders a single kanban card for a document.
 */
function renderClassificationPills(doc: IngestionDocument, session: IngestionSession): string {
  // Resolve topic: per-doc detected_topic > session corpus
  const topicKey = doc.detected_topic || session.corpus || "";
  const topicLabel = _activeTopicLabels[topicKey] || TOPIC_LABELS[topicKey] || (topicKey ? topicKey : "");
  // Resolve type: per-doc detected_type > batch_type
  const typeKey = doc.detected_type || doc.batch_type || "";
  const typeLabel = TYPE_LABELS[typeKey] || (typeKey ? typeKey : "");

  const typeModifier = typeKey === "normative_base"
    ? "normative"
    : typeKey === "interpretative_guidance"
      ? "interpretative"
      : typeKey === "practica_erp"
        ? "practica"
        : "unknown";

  let pills = "";
  if (topicLabel) {
    pills += `<span class="kanban-pill kanban-pill--topic" title="Tema: ${escapeAttr(topicKey)}">${escapeHtml(topicLabel)}</span>`;
  }
  if (typeLabel) {
    pills += `<span class="kanban-pill kanban-pill--type-${typeModifier}" title="Tipo: ${escapeAttr(typeKey)}">${escapeHtml(typeLabel)}</span>`;
  }
  if (!topicLabel && !typeLabel) {
    pills += `<span class="kanban-pill kanban-pill--unclassified">Sin clasificar</span>`;
  }
  return pills;
}

function renderCard(doc: IngestionDocument, session: IngestionSession, i18n: I18nRuntime): string {
  const tone = statusTone(doc.status);
  const column = docStatusToColumn(doc.status);
  const sizeLabel = formatBytes(doc.bytes, i18n);
  const progress = Number(doc.progress || 0);

  // Gate-pending detection: doc is done but still needs batch validation
  const gatePendingIds = new Set(session.gate_pending_doc_ids || []);
  const isGatePending = column === "done" && gatePendingIds.has(doc.doc_id);

  // Status pill: human-readable labels for done cards
  let statusPill: string;
  if (doc.status === "bounced") {
    statusPill = `<span class="meta-chip status-bounced">\u21a9 Ya existe en el corpus</span>`;
  } else if (column === "done" && doc.derived_from_doc_id && (doc.delta_section_count || 0) > 0) {
    statusPill = `<span class="meta-chip status-ok">\u25b3 ${doc.delta_section_count} secciones nuevas</span>`;
  } else if (column === "done" && (doc.status === "done" || doc.status === "completed")) {
    statusPill = `<span class="meta-chip status-ok">\u2713 Documento listo</span>`;
    if (isGatePending) {
      statusPill += `<span class="meta-chip status-gate-pending">Pendiente validaci\u00f3n final</span>`;
    }
  } else {
    statusPill = `<span class="meta-chip status-${tone}">${escapeHtml(doc.status)}</span>`;
  }

  // Classification pills (topic + type)
  const pillsHtml = renderClassificationPills(doc, session);

  // Liveness indicator for running docs
  let livenessHtml = "";
  if (doc.status === "in_progress" || doc.status === "processing") {
    const liveness = classifyLiveness(doc.heartbeat_at, doc.updated_at, doc.stage);
    const elapsed = formatElapsed(doc.heartbeat_at, doc.updated_at);
    livenessHtml = `<div class="kanban-liveness ops-liveness-${liveness}">${elapsed}</div>`;
  }

  // Gate sub-stage
  let gateHtml = "";
  if (doc.stage === "gates" && session.gate_sub_stage) {
    gateHtml = `<div class="kanban-gate-sub">${formatGateSubStage(session.gate_sub_stage)}</div>`;
  }

  // Progress bar for processing docs
  let progressHtml = "";
  if (column === "processing" && progress > 0) {
    progressHtml = `<div class="kanban-progress" data-progress="${progress}"></div>`;
  }

  // Error info
  let errorHtml = "";
  if (doc.error?.message) {
    errorHtml = `<div class="kanban-error">${escapeHtml(doc.error.message)}</div>`;
  }

  // Duplicate / lineage info
  let duplicateHtml = "";
  if (doc.duplicate_of) {
    duplicateHtml = `<div class="kanban-duplicate">Duplicado de: ${escapeHtml(doc.duplicate_of)}</div>`;
  } else if (doc.derived_from_doc_id) {
    duplicateHtml = `<div class="kanban-duplicate">Derivado de: ${escapeHtml(doc.derived_from_doc_id)}</div>`;
  }

  // Completion timestamp for done cards
  let completedAtHtml = "";
  if (column === "done") {
    const completedAt = formatColombiaDateTime(doc.updated_at);
    if (completedAt) {
      completedAtHtml = `<div class="kanban-completed-at">Completado: ${escapeHtml(completedAt)}</div>`;
    }
  }

  // Action buttons based on column / status
  // Duplicate takes priority over classify — resolve duplicate first
  let actionsHtml = "";
  if (doc.duplicate_of && column !== "done" && doc.status !== "bounced") {
    actionsHtml = renderDuplicateActions(doc);
  } else if (column === "pending" && (doc.status === "raw" || doc.status === "needs_classification") && hasAutogenerarSuggestion(doc)) {
    actionsHtml = renderAutogenerarActions(doc, i18n);
  } else if (column === "pending" && (doc.status === "raw" || doc.status === "needs_classification")) {
    actionsHtml = renderClassifyActions(doc, i18n, session);
  } else if (column === "processing" && (doc.status === "failed" || doc.status === "error" || doc.status === "partial_failed")) {
    actionsHtml = renderErrorActions(doc);
  }

  // Reclassify: inline button in pills row + panel below.
  // Available on queued/pending cards too (so user can fix topic before processing)
  // but not on raw cards (they have the full classify actions panel instead).
  let reclassifyBtnHtml = "";
  let reclassifyPanelHtml = "";
  const showReclassify = column !== "pending" || doc.status === "queued";
  if (showReclassify) {
    reclassifyBtnHtml = renderReclassifyButton();
    reclassifyPanelHtml = renderReclassifyPanel(doc, session, i18n);
  }

  // Stage line — only show when it adds information beyond what the status pill shows
  const showStage = doc.stage && doc.stage !== doc.status && column === "processing";

  return `
    <div class="kanban-card kanban-card--${tone}" data-doc-id="${escapeAttr(doc.doc_id)}">
      <div class="kanban-card-head">
        <span class="kanban-card-title" title="${escapeAttr(doc.doc_id)}">${escapeHtml(doc.filename || doc.doc_id)}</span>
        ${statusPill}
      </div>
      ${doc.source_relative_path ? `<div class="kanban-card-relpath" title="${escapeAttr(doc.source_relative_path)}">${escapeHtml(_truncatePath(doc.source_relative_path))}</div>` : ""}
      <div class="kanban-card-pills-row">
        ${pillsHtml}
        <span class="kanban-card-size">${sizeLabel}</span>
        ${reclassifyBtnHtml}
      </div>
      ${reclassifyPanelHtml}
      ${showStage ? `<div class="kanban-card-stage">${escapeHtml(doc.stage)}</div>` : ""}
      ${livenessHtml}
      ${gateHtml}
      ${progressHtml}
      ${completedAtHtml}
      ${duplicateHtml}
      ${errorHtml}
      ${actionsHtml}
    </div>
  `;
}

function renderClassifyActions(doc: IngestionDocument, i18n: I18nRuntime, session?: IngestionSession): string {
  const curType = doc.detected_type || doc.batch_type || "";
  const curTopic = doc.detected_topic || session?.corpus || "";
  const s = (val: string) => val === curType ? " selected" : "";
  return `
    <div class="kanban-actions kanban-classify-actions">
      <label class="kanban-action-field">
        <span>Tema</span>
        <select data-field="topic" class="kanban-select">
          ${buildTopicOptions(curTopic)}
        </select>
      </label>
      <label class="kanban-action-field">
        <span>Tipo</span>
        <select data-field="type" class="kanban-select">
          <option value="">Seleccionar...</option>
          <option value="normative_base"${s("normative_base")}>${i18n.t("ops.ingestion.batchType.normative")}</option>
          <option value="interpretative_guidance"${s("interpretative_guidance")}>${i18n.t("ops.ingestion.batchType.interpretative")}</option>
          <option value="practica_erp"${s("practica_erp")}>${i18n.t("ops.ingestion.batchType.practical")}</option>
        </select>
      </label>
      <div class="kanban-action-field kanban-action-field--btn">
        <span>&nbsp;</span>
        <button class="btn btn--sm btn--primary kanban-assign-btn" data-action="assign" data-doc-id="${escapeAttr(doc.doc_id)}">Asignar</button>
      </div>
    </div>
  `;
}

/** Whether the doc has an autogenerar suggestion to render. */
function hasAutogenerarSuggestion(doc: IngestionDocument): boolean {
  return !!(doc.autogenerar_label && (doc.autogenerar_is_new || doc.autogenerar_resolved_topic));
}

/**
 * Renders autogenerar-specific actions for PENDIENTE cards.
 * Two variants: synonym suggestion (existing topic match) or new topic proposal.
 */
function renderAutogenerarActions(doc: IngestionDocument, i18n: I18nRuntime): string {
  const curType = doc.detected_type || doc.batch_type || "";
  const s = (val: string) => val === curType ? " selected" : "";
  const typeSelect = `
    <label class="kanban-action-field">
      <span>Tipo</span>
      <select data-field="type" class="kanban-select">
        <option value="">Seleccionar...</option>
        <option value="normative_base"${s("normative_base")}>${i18n.t("ops.ingestion.batchType.normative")}</option>
        <option value="interpretative_guidance"${s("interpretative_guidance")}>${i18n.t("ops.ingestion.batchType.interpretative")}</option>
        <option value="practica_erp"${s("practica_erp")}>${i18n.t("ops.ingestion.batchType.practical")}</option>
      </select>
    </label>`;

  if (doc.autogenerar_is_new) {
    // Variant 2: New topic proposed
    return `
      <div class="kanban-actions kanban-autogenerar-actions kanban-autogenerar--new">
        <div class="kanban-autogenerar-header">Nuevo tema detectado</div>
        <label class="kanban-action-field">
          <span>Tema</span>
          <input type="text" class="kanban-input" data-field="autogenerar-label"
            value="${escapeAttr(doc.autogenerar_label || "")}" />
        </label>
        ${doc.autogenerar_rationale ? `<div class="kanban-autogenerar-rationale">${escapeHtml(doc.autogenerar_rationale)}</div>` : ""}
        ${typeSelect}
        <div class="kanban-action-buttons">
          <button class="btn btn--sm btn--primary" data-action="accept-new-topic" data-doc-id="${escapeAttr(doc.doc_id)}">Aceptar nuevo tema</button>
          <button class="btn btn--sm kanban-ag-fallback-btn" data-action="show-existing-dropdown" data-doc-id="${escapeAttr(doc.doc_id)}">Asignar existente</button>
        </div>
        <div class="kanban-ag-fallback-panel" hidden>
          <label class="kanban-action-field">
            <span>Tema existente</span>
            <select data-field="topic" class="kanban-select">
              ${buildTopicOptions("")}
            </select>
          </label>
          <div class="kanban-action-field kanban-action-field--btn">
            <span>&nbsp;</span>
            <button class="btn btn--sm btn--primary kanban-assign-btn" data-action="assign" data-doc-id="${escapeAttr(doc.doc_id)}">Asignar</button>
          </div>
        </div>
      </div>
    `;
  }

  // Variant 1: Synonym suggestion (resolved to existing topic)
  const resolvedKey = doc.autogenerar_resolved_topic || "";
  const resolvedLabel = TOPIC_LABELS[resolvedKey] || resolvedKey;
  const synConf = doc.autogenerar_synonym_confidence ?? 0;
  const pct = Math.round(synConf * 100);

  return `
    <div class="kanban-actions kanban-autogenerar-actions kanban-autogenerar--synonym">
      <div class="kanban-autogenerar-header">Tema sugerido: <strong>${escapeHtml(resolvedLabel)}</strong> <span class="kanban-autogenerar-conf">(${pct}%)</span></div>
      <div class="kanban-autogenerar-source">Basado en: "${escapeHtml(doc.autogenerar_label || "")}"</div>
      ${typeSelect}
      <div class="kanban-action-buttons">
        <button class="btn btn--sm btn--primary" data-action="accept-synonym" data-doc-id="${escapeAttr(doc.doc_id)}">Aceptar</button>
        <button class="btn btn--sm kanban-ag-fallback-btn" data-action="show-existing-dropdown" data-doc-id="${escapeAttr(doc.doc_id)}">Cambiar</button>
      </div>
      <div class="kanban-ag-fallback-panel" hidden>
        <label class="kanban-action-field">
          <span>Tema</span>
          <select data-field="topic" class="kanban-select">
            ${buildTopicOptions(resolvedKey)}
          </select>
        </label>
        <div class="kanban-action-field kanban-action-field--btn">
          <span>&nbsp;</span>
          <button class="btn btn--sm btn--primary kanban-assign-btn" data-action="assign" data-doc-id="${escapeAttr(doc.doc_id)}">Asignar</button>
        </div>
      </div>
    </div>
  `;
}

function renderReclassifyButton(): string {
  return `<button class="kanban-reclassify-toggle" type="button" title="Cambiar clasificaci\u00f3n">\u270E</button>`;
}

function renderReclassifyPanel(doc: IngestionDocument, session: IngestionSession, i18n: I18nRuntime): string {
  const curTopic = doc.detected_topic || session.corpus || "";
  const curType = doc.detected_type || doc.batch_type || "";
  const s = (val: string, cur: string) => val === cur ? " selected" : "";

  return `
    <div class="kanban-reclassify-panel" hidden>
      <label class="kanban-action-field">
        <span>Tema</span>
        <select data-field="topic" class="kanban-select">
          ${buildTopicOptions(curTopic)}
        </select>
      </label>
      <label class="kanban-action-field">
        <span>Tipo</span>
        <select data-field="type" class="kanban-select">
          <option value="">Seleccionar...</option>
          <option value="normative_base"${s("normative_base", curType)}>${i18n.t("ops.ingestion.batchType.normative")}</option>
          <option value="interpretative_guidance"${s("interpretative_guidance", curType)}>${i18n.t("ops.ingestion.batchType.interpretative")}</option>
          <option value="practica_erp"${s("practica_erp", curType)}>${i18n.t("ops.ingestion.batchType.practical")}</option>
        </select>
      </label>
      <div class="kanban-action-field kanban-action-field--btn">
        <span>&nbsp;</span>
        <button class="btn btn--sm btn--primary kanban-assign-btn" data-action="assign" data-doc-id="${escapeAttr(doc.doc_id)}">Asignar</button>
      </div>
    </div>
  `;
}

function renderDuplicateActions(doc: IngestionDocument): string {
  return `
    <div class="kanban-actions">
      <button class="btn btn--sm btn--primary" data-action="replace-dup" data-doc-id="${escapeAttr(doc.doc_id)}">Reemplazar</button>
      <button class="btn btn--sm" data-action="add-new-dup" data-doc-id="${escapeAttr(doc.doc_id)}">Agregar nuevo</button>
      <button class="btn btn--sm btn--danger" data-action="discard-dup" data-doc-id="${escapeAttr(doc.doc_id)}">Descartar</button>
    </div>
  `;
}

function renderErrorActions(doc: IngestionDocument): string {
  return `
    <div class="kanban-actions">
      <button class="btn btn--sm" data-action="retry" data-doc-id="${escapeAttr(doc.doc_id)}">Reintentar</button>
      <button class="btn btn--sm btn--danger" data-action="discard" data-doc-id="${escapeAttr(doc.doc_id)}">Descartar</button>
    </div>
  `;
}

/** Fallback topic option list — used when no dynamic corpora are available. */
const _BASE_TOPIC_OPTIONS: Array<[value: string, label: string]> = [
  ["declaracion_renta",                   "Renta"],
  ["iva",                                 "IVA"],
  ["laboral",                             "Laboral"],
  ["facturacion_electronica",             "Facturación"],
  ["estados_financieros_niif",            "NIIF"],
  ["ica",                                 "ICA"],
  ["calendario_obligaciones",             "Calendarios"],
  ["retencion_fuente",                    "Retención"],
  ["regimen_sancionatorio",               "Sanciones"],
  ["regimen_cambiario",                   "Régimen Cambiario"],
  ["impuesto_al_patrimonio",              "Patrimonio"],
  ["informacion_exogena",                 "Exógena"],
  ["proteccion_de_datos",                 "Datos"],
  ["obligaciones_mercantiles",            "Mercantil"],
  ["obligaciones_profesionales_contador", "Obligaciones Contador"],
  ["rut_responsabilidades",               "RUT"],
  ["gravamen_movimiento_financiero_4x1000", "GMF 4\u00d71000"],
  ["beneficiario_final",                  "Beneficiario Final"],
  ["contratacion_estatal",                "Contrataci\u00f3n Estatal"],
  ["reforma_pensional",                   "Reforma Pensional"],
  ["zomac_incentivos",                    "ZOMAC"],
];

/**
 * Build the topic option list by merging the base list with dynamic corpora.
 * New topics registered via autogenerar appear automatically.
 */
function buildTopicOptionsFromCorpora(corpora: readonly IngestionCorpus[]): Array<[string, string]> {
  const seen = new Set<string>();
  const result: Array<[string, string]> = [];
  // Start with base options (preserves canonical order)
  for (const [key, label] of _BASE_TOPIC_OPTIONS) {
    seen.add(key);
    result.push([key, label]);
  }
  // Append any corpora entries not in the base list (novel topics)
  for (const corpus of corpora) {
    if (!corpus.key || seen.has(corpus.key)) continue;
    seen.add(corpus.key);
    result.push([corpus.key, corpus.label || corpus.key]);
  }
  return result;
}

/** Module-level cache updated on each renderKanbanBoard call. */
let _activeTopicOptions: Array<[string, string]> = _BASE_TOPIC_OPTIONS;
let _activeTopicLabels: Record<string, string> = { ...TOPIC_LABELS };

function buildTopicOptions(selectedValue = ""): string {
  let html = `<option value="">Seleccionar...</option>`;
  for (const [value, label] of _activeTopicOptions) {
    const sel = value === selectedValue ? " selected" : "";
    html += `<option value="${escapeAttr(value)}"${sel}>${escapeHtml(label)}</option>`;
  }
  return html;
}

function escapeHtml(text: string): string {
  const el = document.createElement("span");
  el.textContent = text;
  return el.innerHTML;
}

function escapeAttr(text: string): string {
  return text.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/'/g, "&#39;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

/** Show only last 2 path segments as a compact breadcrumb. */
function _truncatePath(fullPath: string): string {
  const parts = fullPath.replace(/\/[^/]+$/, "").split("/").filter(Boolean);
  if (parts.length <= 2) return parts.join("/") + "/";
  return "\u2026/" + parts.slice(-2).join("/") + "/";
}

/**
 * Renders the full kanban board into the given container.
 * Groups session documents into columns by status.
 * @param suppressPanels - doc_ids whose reclassify panel state should NOT be restored (e.g. just-assigned docs).
 */
export function renderKanbanBoard(
  session: IngestionSession,
  container: HTMLElement,
  i18n: I18nRuntime,
  suppressPanels?: ReadonlySet<string>,
  corpora?: readonly IngestionCorpus[],
): void {
  // Refresh topic options/labels from dynamic corpora list
  if (corpora && corpora.length > 0) {
    _activeTopicOptions = buildTopicOptionsFromCorpora(corpora);
    _activeTopicLabels = Object.fromEntries(_activeTopicOptions);
  }

  const documents = [...(session.documents || [])].sort(
    (left, right) => Date.parse(String(right.updated_at || 0)) - Date.parse(String(left.updated_at || 0)),
  );

  // Group documents by column
  const groups: Record<KanbanColumn, IngestionDocument[]> = {
    pending: [],
    processing: [],
    done: [],
  };

  for (const doc of documents) {
    const col = docStatusToColumn(doc.status);
    groups[col].push(doc);
  }

  // Docs needing manual classification (raw / needs_classification) float to the top
  // of the pending column so the operator sees actionable items first.
  groups.pending.sort((a, b) => {
    const aNeedsAction = a.status === "raw" || a.status === "needs_classification" ? 0 : 1;
    const bNeedsAction = b.status === "raw" || b.status === "needs_classification" ? 0 : 1;
    if (aNeedsAction !== bNeedsAction) return aNeedsAction - bNeedsAction;
    return Date.parse(String(b.updated_at || 0)) - Date.parse(String(a.updated_at || 0));
  });

  // Build column HTML directly — no wrapper div so that the container's CSS grid
  // (`.kanban-board { display: grid; grid-template-columns: 1fr 1fr 1fr }`) sees the
  // column divs as direct grid children.
  // Session-level validation banner for the "done" column
  const isGateRunning = session.status === "running_batch_gates";
  const gateSubStage = session.gate_sub_stage || "";
  let validationBannerHtml = "";
  if (isGateRunning) {
    const phaseLabel = gateSubStage ? formatGateSubStage(gateSubStage) : "Preparando...";
    validationBannerHtml = `
      <div class="kanban-validation-banner kanban-validation-banner--running">
        <span class="kanban-validation-spinner"></span>
        <span>Validaci\u00f3n final en curso \u2014 ${escapeHtml(phaseLabel)}</span>
      </div>`;
  } else if (session.status === "needs_retry_batch_gate") {
    validationBannerHtml = `
      <div class="kanban-validation-banner kanban-validation-banner--error">
        <span>\u26A0 Validaci\u00f3n final fallida \u2014 use Reintentar o Validar lote</span>
      </div>`;
  } else if (session.status === "completed" && session.wip_sync_status === "skipped") {
    validationBannerHtml = `
      <div class="kanban-validation-banner kanban-validation-banner--warn">
        <span>\u26A0 Ingesta completada solo localmente \u2014 WIP Supabase no estaba disponible. Use Operaciones \u2192 Sincronizar a WIP.</span>
      </div>`;
  }

  let html = "";
  const processingCount = groups["processing"].length;
  for (const col of KANBAN_COLUMNS) {
    const docs = groups[col];
    // Processing column badge shows "X / 5" to reflect the max-concurrency limit.
    const countBadge = col === "processing"
      ? `<span class="kanban-column-count">${processingCount}</span><span class="kanban-column-limit">/ ${MAX_PROCESSING}</span>`
      : `<span class="kanban-column-count">${docs.length}</span>`;
    const bodyContent = docs.length === 0
      ? `<div class="kanban-column-empty">Sin documentos</div>`
      : docs.map((d) => renderCard(d, session, i18n)).join("");
    // Show validation banner at top of "done" column
    const bannerHtml = col === "done" ? validationBannerHtml : "";
    html += `
      <div class="kanban-column kanban-column--${col}">
        <div class="kanban-column-header">
          <span class="kanban-column-icon">${COLUMN_ICONS[col]}</span>
          <span class="kanban-column-label">${COLUMN_LABELS[col]}</span>
          ${countBadge}
        </div>
        <div class="kanban-column-cards">
          ${bannerHtml}
          ${bodyContent}
        </div>
      </div>
    `;
  }

  // --- Save interactive state before DOM replacement ---

  // 1. Scroll positions (from the cards container inside each column)
  const columnScrolls: Record<string, number> = {};
  container.querySelectorAll<HTMLElement>(".kanban-column").forEach((col) => {
    const key = col.classList[1] || "";
    const cards = col.querySelector<HTMLElement>(".kanban-column-cards");
    if (key && cards) columnScrolls[key] = cards.scrollTop;
  });
  const ancestorScrolls: Array<[HTMLElement, number]> = [];
  let el: HTMLElement | null = container;
  while (el) {
    if (el.scrollTop > 0) ancestorScrolls.push([el, el.scrollTop]);
    el = el.parentElement;
  }

  // 2. Open reclassify panels: save open/closed state + select values per doc_id.
  //    Skip doc_ids in suppressPanels (e.g. just successfully assigned — close them).
  const openPanels: Record<string, { topic: string; type: string }> = {};
  container.querySelectorAll<HTMLElement>(".kanban-reclassify-panel").forEach((panel) => {
    if (!panel.hasAttribute("hidden")) {
      const card = panel.closest<HTMLElement>("[data-doc-id]");
      const docId = card?.dataset.docId || "";
      if (docId && !suppressPanels?.has(docId)) {
        const topicVal = panel.querySelector<HTMLSelectElement>("[data-field='topic']")?.value || "";
        const typeVal = panel.querySelector<HTMLSelectElement>("[data-field='type']")?.value || "";
        openPanels[docId] = { topic: topicVal, type: typeVal };
      }
    }
  });

  // 3. Classify actions (raw/pending cards): save select values so polling
  //    doesn't destroy the user's in-progress selection.
  const classifySelections: Record<string, { topic: string; type: string }> = {};
  container.querySelectorAll<HTMLElement>(".kanban-classify-actions").forEach((panel) => {
    const card = panel.closest<HTMLElement>("[data-doc-id]");
    const docId = card?.dataset.docId || "";
    if (docId) {
      const topicVal = panel.querySelector<HTMLSelectElement>("[data-field='topic']")?.value || "";
      const typeVal = panel.querySelector<HTMLSelectElement>("[data-field='type']")?.value || "";
      if (topicVal || typeVal) {
        classifySelections[docId] = { topic: topicVal, type: typeVal };
      }
    }
  });

  // --- Replace DOM ---
  container.innerHTML = html;

  // --- Restore interactive state ---

  // 1. Scroll positions
  for (const [ancestor, scrollTop] of ancestorScrolls) {
    ancestor.scrollTop = scrollTop;
  }
  container.querySelectorAll<HTMLElement>(".kanban-column").forEach((col) => {
    const key = col.classList[1] || "";
    const cards = col.querySelector<HTMLElement>(".kanban-column-cards");
    if (key && columnScrolls[key] && cards) cards.scrollTop = columnScrolls[key];
  });

  // 2. Restore open reclassify panels
  for (const [docId, vals] of Object.entries(openPanels)) {
    const card = container.querySelector<HTMLElement>(`[data-doc-id="${CSS.escape(docId)}"]`);
    if (!card) continue;
    const toggle = card.querySelector<HTMLButtonElement>(".kanban-reclassify-toggle");
    const panel = card.querySelector<HTMLElement>(".kanban-reclassify-panel");
    if (toggle && panel) {
      panel.removeAttribute("hidden");
      toggle.textContent = "\u2716";
      const topicSelect = panel.querySelector<HTMLSelectElement>("[data-field='topic']");
      const typeSelect = panel.querySelector<HTMLSelectElement>("[data-field='type']");
      if (topicSelect && vals.topic) topicSelect.value = vals.topic;
      if (typeSelect && vals.type) typeSelect.value = vals.type;
    }
  }

  // 3. Restore classify action selections for raw/pending cards
  for (const [docId, vals] of Object.entries(classifySelections)) {
    const card = container.querySelector<HTMLElement>(`[data-doc-id="${CSS.escape(docId)}"]`);
    if (!card) continue;
    const panel = card.querySelector<HTMLElement>(".kanban-classify-actions");
    if (!panel) continue;
    const topicSelect = panel.querySelector<HTMLSelectElement>("[data-field='topic']");
    const typeSelect = panel.querySelector<HTMLSelectElement>("[data-field='type']");
    if (topicSelect && vals.topic) topicSelect.value = vals.topic;
    if (typeSelect && vals.type) typeSelect.value = vals.type;
  }

  // Hydrate progress bar placeholders
  container.querySelectorAll<HTMLDivElement>(".kanban-progress").forEach((el) => {
    const progress = Number(el.dataset.progress || 0);
    const stage = el.closest(".kanban-card")?.querySelector(".kanban-card-stage")?.textContent || undefined;
    const node = buildProgressNode(progress, stage);
    el.replaceWith(node);
  });

  // Hydrate reclassify toggle buttons
  container.querySelectorAll<HTMLButtonElement>(".kanban-reclassify-toggle").forEach((btn) => {
    btn.addEventListener("click", () => {
      const card = btn.closest<HTMLElement>(".kanban-card");
      const panel = card?.querySelector<HTMLElement>(".kanban-reclassify-panel");
      if (!panel) return;
      const isHidden = panel.hasAttribute("hidden");
      if (isHidden) {
        panel.removeAttribute("hidden");
        btn.textContent = "\u2716";
      } else {
        panel.setAttribute("hidden", "");
        btn.textContent = "\u270E";
      }
    });
  });
}
