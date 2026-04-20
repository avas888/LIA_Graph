/**
 * Expert Panel Controller — "Interpretación de Expertos"
 *
 * Fetches expert interpretations from `/api/expert-panel` and renders
 * accountant-first decision cards in the sidebar. Each card opens a
 * dedicated modal with practical guidance, checklist items, and source drilldown.
 */

import type { I18nRuntime } from "@/shared/i18n";
import { stripMarkdown } from "@/shared/utils/format";
import {
  renderExpertCardList,
  type ExpertCardViewModel,
} from "@/shared/ui/organisms/expertCards";
import { UI_EVENT_EXPERTS_UPDATED, emitUiEvent } from "@/shared/ui/patterns/uiEvents";
import { renderExpertProse } from "@/features/chat/expertProseRenderer";
import {
  buildElevatorSummary,
  sanitizeExpertText,
} from "@/features/chat/expertSummaryText";
import { applySplitTitle } from "@/features/chat/expertModalTitle";

export { extractArticleRefs } from "@/features/chat/expertPanelRefs";

interface ExpertProvider {
  name: string;
  url: string | null;
}

interface ExpertProviderLink {
  url: string;
  label: string;
  provider: string;
}

interface ExpertSnippet {
  doc_id: string;
  source_doc_id?: string;
  logical_doc_id?: string;
  authority: string;
  title: string;
  snippet: string;
  position_signal: string;
  relevance_score: number;
  trust_tier: string;
  provider_links: ExpertProviderLink[];
  providers: ExpertProvider[];
  source_view_url?: string | null;
  official_url?: string | null;
  open_url?: string | null;
  card_summary: string;
  extended_excerpt?: string;
  summary_origin?: string;
  summary_quality?: string;
  source_hash?: string;
  coverage_axes?: string[];
  requested_match?: boolean;
  selection_reason?: string;
  core_ref_matches?: string[];
  panel_rank?: number | null;
}

interface ExpertGroup {
  article_ref: string;
  classification: "concordancia" | "divergencia" | "complementario";
  summary_signal: string;
  summary_origin?: string;
  summary_quality?: string;
  providers: ExpertProvider[];
  snippets: ExpertSnippet[];
  relevance_score?: number;
  coverage_axes?: string[];
  requested_match?: boolean;
  selection_reason?: string;
  panel_rank?: number | null;
}

interface ExpertPanelResponse {
  ok: boolean;
  groups: ExpertGroup[];
  ungrouped: ExpertSnippet[];
  total_available?: number;
  has_more?: boolean;
  next_offset?: number | null;
  retrieval_diagnostics?: Record<string, unknown>;
  trace_id?: string;
}

type ExpertCardClassification = ExpertGroup["classification"] | "individual";
type ExpertSignal = "permite" | "restringe" | "condiciona" | "neutral";

interface ExpertCard {
  id: string;
  classification: ExpertCardClassification;
  dominantSignal: ExpertSignal;
  articleRef: string;
  articleLabel: string;
  heading: string;
  lead: string;
  implication: string;
  checklist: string[];
  sources: ExpertSnippet[];
  providers: ExpertProvider[];
  authorities: string[];
  summarySignal: string;
  maxRelevance: number;
  requestedMatch: boolean;
  panelRank: number;
  posibleRelevancia: string | null;
  resumenNutshell: string | null;
  esRelevante: boolean | null;
}

export interface ExpertPanelLoadOptions {
  traceId: string;
  message: string;
  assistantAnswer?: string;
  normativeArticleRefs?: string[];
  searchSeed?: string;
  searchSeedOrigin?: string;
  topic?: string;
  pais?: string;
}

export interface ExpertPanelPersistedState {
  status: "idle" | "loading" | "empty" | "error" | "populated";
  loadOptions: ExpertPanelLoadOptions | null;
  response: ExpertPanelResponse | null;
  enhancements?: Record<string, { posibleRelevancia: string | null; resumenNutshell: string | null; esRelevante: boolean | null }> | null;
}

interface ExpertPanelControllerOptions {
  i18n: I18nRuntime;
  contentNode: HTMLElement;
  statusNode: HTMLElement;
  detailModalNode?: HTMLElement | null;
  openModal?: (modal: HTMLElement) => void;
  onSnippetClick?: (docId: string) => void;
  onStateChanged?: (state: ExpertPanelPersistedState | null) => void;
}

function authorityBadgeClass(authority: string): string {
  const normalized = (authority || "").trim().toLowerCase();
  if (normalized === "dian") return "expert-authority--dian";
  if (
    ["deloitte", "ey", "kpmg", "pwc", "bdo", "grant thornton", "crowe", "baker tilly"].some(
      (firm) => normalized.includes(firm),
    )
  ) {
    return "expert-authority--big4";
  }
  if (normalized.includes("actualicese") || normalized.includes("gerencie")) {
    return "expert-authority--actualicese";
  }
  return "expert-authority--generic";
}

function normalizeText(value: string): string {
  return stripMarkdown(String(value || "")).replace(/\s+/g, " ").trim();
}

const METACOGNITIVE_RE = /(?:la fuente no proporciona|el texto fuente est[áa] vac[ií]o|no es posible generar|no proporciona texto|no contiene informaci[oó]n suficiente|incluya el texto|proporcione el texto|no se puede extraer|no hay contenido|la fuente est[áa] vac[ií]a)/i;

function isMetacognitive(text: string): boolean {
  return METACOGNITIVE_RE.test(text);
}

function sourceCountLabel(snippets: ExpertSnippet[]): string {
  const sourceCount = snippets.length;
  return `${sourceCount} fuente${sourceCount === 1 ? "" : "s"}`;
}

function clipText(value: string, maxChars: number): string {
  const cleaned = normalizeText(value);
  if (!cleaned || cleaned.length <= maxChars) return cleaned;
  return `${cleaned.slice(0, Math.max(0, maxChars - 1)).trimEnd()}…`;
}

function ensureSentence(value: string): string {
  const cleaned = normalizeText(value);
  if (!cleaned) return "";
  return /[.!?…]$/.test(cleaned) ? cleaned : `${cleaned}.`;
}

function canonicalizeNormativeRef(value: string): string {
  return String(value || "")
    .trim()
    .toLowerCase()
    .replace(/[:.\-–—]/g, "_")
    .replace(/\s+/g, "_")
    .replace(/__+/g, "_")
    .replace(/^_+|_+$/g, "");
}

function buildRequestedRefSet(rawRefs: string[]): Set<string> {
  const requested = new Set<string>();
  for (const rawRef of rawRefs) {
    const normalized = canonicalizeNormativeRef(rawRef);
    if (!normalized) continue;
    requested.add(normalized);
    if (normalized.startsWith("art_")) {
      requested.add(`et_${normalized}`);
    }
    if (normalized.startsWith("et_art_")) {
      requested.add(normalized.slice(3));
    }
  }
  return requested;
}

function humanizeArticleRef(articleRef: string): string {
  const raw = String(articleRef || "").trim().toLowerCase();
  const canonical = canonicalizeNormativeRef(articleRef);
  if (!canonical) return "";
  if (canonical.startsWith("et_art_")) {
    return `ET artículo ${canonical.slice("et_art_".length).replace(/_/g, "-")}`;
  }
  if (canonical.startsWith("art_")) {
    return `Artículo ${canonical.slice("art_".length).replace(/_/g, "-")}`;
  }
  const durMatch = /dur[:_](\d+)[:_](\d+)/i.exec(raw);
  if (durMatch) {
    return `DUR ${durMatch[1]} de ${durMatch[2]}`;
  }
  return clipText(raw.replace(/_/g, " "), 48);
}

function sortSources(snippets: ExpertSnippet[]): ExpertSnippet[] {
  return [...snippets].sort((left, right) => {
    const byRelevance = (right.relevance_score || 0) - (left.relevance_score || 0);
    if (Math.abs(byRelevance) > 0.0001) return byRelevance;
    return normalizeText(left.authority).localeCompare(normalizeText(right.authority), "es", {
      sensitivity: "base",
    });
  });
}

function uniqueAuthorities(snippets: ExpertSnippet[]): string[] {
  return Array.from(
    new Set(
      snippets
        .map((snippet) => normalizeText(snippet.authority))
        .filter(Boolean),
    ),
  );
}

function dominantSignal(snippets: ExpertSnippet[]): ExpertSignal {
  const counts = new Map<ExpertSignal, number>();
  for (const snippet of snippets) {
    const signal = normalizeText(snippet.position_signal).toLowerCase() as ExpertSignal;
    const normalizedSignal: ExpertSignal =
      signal === "permite" || signal === "restringe" || signal === "condiciona" ? signal : "neutral";
    counts.set(normalizedSignal, (counts.get(normalizedSignal) || 0) + 1);
  }
  const orderedSignals: ExpertSignal[] = ["restringe", "condiciona", "permite", "neutral"];
  let winner: ExpertSignal = "neutral";
  let winnerCount = -1;
  for (const signal of orderedSignals) {
    const count = counts.get(signal) || 0;
    if (count > winnerCount) {
      winner = signal;
      winnerCount = count;
    }
  }
  return winner;
}

function signalLabel(i18n: I18nRuntime, signal: ExpertSignal): string {
  return i18n.t(`chat.experts.signal.${signal}`);
}



function classificationLabel(i18n: I18nRuntime, classification: ExpertCardClassification): string {
  if (classification === "individual") {
    return i18n.t("chat.experts.individual");
  }
  return i18n.t(`chat.experts.${classification}`);
}

function buildImplication(classification: ExpertCardClassification, signal: ExpertSignal): string {
  if (classification === "divergencia") {
    return "Antes de asesorar, registrar o presentar, define qué postura vas a adoptar y amárrala a la norma base aplicable.";
  }
  if (classification === "complementario") {
    return "Úsalo como checklist de varias aristas: las fuentes no se anulan entre sí, pero tampoco reemplazan la validación normativa.";
  }
  if (classification === "individual") {
    return "Tómalo como insumo de contexto, no como consenso suficiente para cerrar una decisión con riesgo material.";
  }
  if (signal === "restringe") {
    return "Léelo como señal de cierre: si tu caso cae en esta restricción, no tomes la posición sin una excepción expresa y documentada.";
  }
  if (signal === "condiciona") {
    return "No cierres la partida hasta verificar soportes, fechas, requisitos formales y trazabilidad del hecho económico.";
  }
  if (signal === "permite") {
    return "Puedes usarlo como línea operativa de trabajo, pero solo si la norma base y el soporte documental del expediente siguen alineados.";
  }
  return "Úsalo para orientar el análisis, pero confirma la norma aplicable y el soporte del expediente antes de cerrar el caso.";
}

function buildChecklist(
  classification: ExpertCardClassification,
  signal: ExpertSignal,
  authorities: string[],
): string[] {
  const checklist = [
    "Contrasta este criterio con la norma base antes de responder al cliente, contabilizar o presentar.",
  ];
  if (classification === "divergencia") {
    checklist.push("Deja por escrito por qué adoptas una postura y por qué descartas la alternativa.");
  } else if (classification === "complementario") {
    checklist.push("Revisa cada fuente como pieza complementaria: una puede cubrir soporte, otra alcance y otra riesgo.");
  } else if (classification === "individual") {
    checklist.push("Si la decisión es sensible, busca al menos una segunda fuente o respaldo normativo antes de cerrar.");
  } else if (signal === "restringe") {
    checklist.push("Verifica si tu caso cae exactamente en la restricción o si existe una excepción expresa posterior.");
  } else if (signal === "condiciona") {
    checklist.push("Confirma soportes, fechas, requisitos formales y evidencia de negocio antes de aplicar la posición.");
  } else if (signal === "permite") {
    checklist.push("Valida que el hecho económico y los soportes coincidan con el supuesto descrito por las fuentes.");
  } else {
    checklist.push("Usa esta lectura como orientación y documenta cualquier supuesto relevante antes de cerrar.");
  }
  if (authorities.length > 0) {
    checklist.push(`Guarda trazabilidad de las fuentes consultadas: ${clipText(authorities.join(", "), 72)}.`);
  }
  return checklist.map((item) => ensureSentence(item));
}

function normalizeProviders(providers: ExpertProvider[]): ExpertProvider[] {
  const ordered: ExpertProvider[] = [];
  const seen = new Set<string>();
  for (const provider of Array.isArray(providers) ? providers : []) {
    const name = normalizeText(provider?.name || "");
    if (!name || seen.has(name)) continue;
    seen.add(name);
    ordered.push({ name, url: normalizeText(provider?.url || "") || null });
  }
  return ordered;
}

function collectProviders(snippets: ExpertSnippet[], seed: ExpertProvider[] = []): ExpertProvider[] {
  const collected: ExpertProvider[] = [];
  for (const provider of normalizeProviders(seed)) {
    collected.push(provider);
  }
  for (const snippet of snippets) {
    for (const provider of normalizeProviders(snippet.providers || [])) {
      if (!collected.some((item) => item.name === provider.name)) {
        collected.push(provider);
      }
    }
  }
  return collected;
}

function cardSummaryFromSnippet(snippet: ExpertSnippet): string {
  const elevator = buildElevatorSummary(snippet, 480);
  if (elevator) return elevator;
  const summary = ensureSentence(sanitizeExpertText(snippet.card_summary));
  if (summary && !isMetacognitive(summary)) return clipText(summary, 480);
  return "Abre el detalle para revisar el criterio aplicable.";
}

function buildCardFromGroup(group: ExpertGroup, requestedRefs: Set<string>): ExpertCard {
  const sources = sortSources(group.snippets);
  const providers = collectProviders(sources, group.providers || []);
  const authorities = uniqueAuthorities(sources);
  const articleRef = String(group.article_ref || "").trim();
  const articleLabel = humanizeArticleRef(articleRef);
  const signal = dominantSignal(sources);
  const rawGroupSummary = sanitizeExpertText(group.summary_signal);
  const summary = ensureSentence(
    (rawGroupSummary && !isMetacognitive(rawGroupSummary) ? rawGroupSummary : "") || cardSummaryFromSnippet(sources[0] || ({} as ExpertSnippet)),
  );
  return {
    id: `group:${articleRef || group.classification}`,
    classification: group.classification,
    dominantSignal: signal,
    articleRef,
    articleLabel,
    heading: summary,
    lead: summary,
    implication: buildImplication(group.classification, signal),
    checklist: buildChecklist(group.classification, signal, authorities),
    sources,
    providers,
    authorities,
    summarySignal: summary,
    maxRelevance: Number(group.relevance_score) || Math.max(...sources.map((snippet) => Number(snippet.relevance_score) || 0), 0),
    requestedMatch: Boolean(group.requested_match) || requestedRefs.has(canonicalizeNormativeRef(articleRef)),
    panelRank: Number(group.panel_rank) || Number.MAX_SAFE_INTEGER,
    posibleRelevancia: null,
    resumenNutshell: null,
    esRelevante: null,
  };
}

function buildCardFromSnippet(snippet: ExpertSnippet): ExpertCard {
  const sources = sortSources([snippet]);
  const providers = collectProviders(sources, snippet.providers || []);
  const authorities = uniqueAuthorities(sources);
  const signal = dominantSignal(sources);
  const summary = cardSummaryFromSnippet(snippet);
  return {
    id: `single:${snippet.doc_id}`,
    classification: "individual",
    dominantSignal: signal,
    articleRef: "",
    articleLabel: "",
    heading: summary,
    lead: summary,
    implication: buildImplication("individual", signal),
    checklist: buildChecklist("individual", signal, authorities),
    sources,
    providers,
    authorities,
    summarySignal: summary,
    maxRelevance: Number(snippet.relevance_score) || 0,
    requestedMatch: Boolean(snippet.requested_match),
    panelRank: Number(snippet.panel_rank) || Number.MAX_SAFE_INTEGER,
    posibleRelevancia: null,
    resumenNutshell: null,
    esRelevante: null,
  };
}

function classificationRank(classification: ExpertCardClassification): number {
  switch (classification) {
    case "divergencia":
      return 0;
    case "complementario":
      return 1;
    case "concordancia":
      return 2;
    case "individual":
    default:
      return 3;
  }
}

function signalRank(signal: ExpertSignal): number {
  switch (signal) {
    case "restringe":
      return 0;
    case "condiciona":
      return 1;
    case "permite":
      return 2;
    case "neutral":
    default:
      return 3;
  }
}

function buildCards(data: ExpertPanelResponse, requestedRefs: Set<string>): ExpertCard[] {
  const groupCards = (Array.isArray(data.groups) ? data.groups : []).map((group) =>
    buildCardFromGroup(group, requestedRefs),
  );
  const individualCards = (Array.isArray(data.ungrouped) ? data.ungrouped : []).map((snippet) =>
    buildCardFromSnippet(snippet),
  );
  return [...groupCards, ...individualCards].sort((left, right) => {
    const byPanelRank = left.panelRank - right.panelRank;
    if (Number.isFinite(byPanelRank) && byPanelRank !== 0) {
      return byPanelRank;
    }
    if (left.requestedMatch !== right.requestedMatch) {
      return left.requestedMatch ? -1 : 1;
    }
    const byClassification = classificationRank(left.classification) - classificationRank(right.classification);
    if (byClassification !== 0) return byClassification;
    const bySignal = signalRank(left.dominantSignal) - signalRank(right.dominantSignal);
    if (bySignal !== 0) return bySignal;
    const byRelevance = right.maxRelevance - left.maxRelevance;
    if (Math.abs(byRelevance) > 0.0001) return byRelevance;
    return left.heading.localeCompare(right.heading, "es", { sensitivity: "base" });
  });
}

function groupKey(group: ExpertGroup): string {
  return `${canonicalizeNormativeRef(group.article_ref)}::${normalizeText(group.classification)}`;
}

function snippetKey(snippet: ExpertSnippet): string {
  return normalizeText(snippet.doc_id);
}

function mergeExpertPanelResponses(
  current: ExpertPanelResponse | null,
  incoming: ExpertPanelResponse | null,
): ExpertPanelResponse | null {
  if (!incoming) return cloneExpertPanelResponse(current);
  if (!current) return cloneExpertPanelResponse(incoming);

  const mergedGroups = new Map<string, ExpertGroup>();
  for (const group of Array.isArray(current.groups) ? current.groups : []) {
    mergedGroups.set(groupKey(group), JSON.parse(JSON.stringify(group)));
  }
  for (const group of Array.isArray(incoming.groups) ? incoming.groups : []) {
    mergedGroups.set(groupKey(group), JSON.parse(JSON.stringify(group)));
  }

  const mergedUngrouped = new Map<string, ExpertSnippet>();
  for (const snippet of Array.isArray(current.ungrouped) ? current.ungrouped : []) {
    mergedUngrouped.set(snippetKey(snippet), JSON.parse(JSON.stringify(snippet)));
  }
  for (const snippet of Array.isArray(incoming.ungrouped) ? incoming.ungrouped : []) {
    mergedUngrouped.set(snippetKey(snippet), JSON.parse(JSON.stringify(snippet)));
  }

  return {
    ok: incoming.ok ?? current.ok,
    groups: Array.from(mergedGroups.values()),
    ungrouped: Array.from(mergedUngrouped.values()),
    total_available: incoming.total_available ?? current.total_available,
    has_more: incoming.has_more ?? current.has_more,
    next_offset:
      incoming.next_offset !== undefined
        ? incoming.next_offset
        : current.next_offset,
    retrieval_diagnostics: incoming.retrieval_diagnostics || current.retrieval_diagnostics,
    trace_id: incoming.trace_id || current.trace_id,
  };
}

function visibleProviders(providers: ExpertProvider[]): { visible: ExpertProvider[]; hiddenCount: number } {
  const normalized = normalizeProviders(providers);
  return {
    visible: normalized.slice(0, 4),
    hiddenCount: Math.max(0, normalized.length - 4),
  };
}

function cloneLoadOptions(loadOptions: ExpertPanelLoadOptions | null): ExpertPanelLoadOptions | null {
  if (!loadOptions) return null;
  return {
    traceId: normalizeText(loadOptions.traceId),
    message: normalizeText(loadOptions.message),
    assistantAnswer: normalizeText(loadOptions.assistantAnswer || "") || undefined,
    normativeArticleRefs: Array.isArray(loadOptions.normativeArticleRefs)
      ? loadOptions.normativeArticleRefs.map((value) => normalizeText(value)).filter(Boolean)
      : [],
    searchSeed: normalizeText(loadOptions.searchSeed || "") || undefined,
    searchSeedOrigin: normalizeText(loadOptions.searchSeedOrigin || "") || undefined,
    topic: normalizeText(loadOptions.topic || "") || undefined,
    pais: normalizeText(loadOptions.pais || "") || undefined,
  };
}

function cloneExpertPanelResponse(response: ExpertPanelResponse | null): ExpertPanelResponse | null {
  if (!response) return null;
  return JSON.parse(JSON.stringify(response));
}

export function createExpertPanelController(options: ExpertPanelControllerOptions) {
  const { i18n, contentNode, statusNode, detailModalNode, openModal, onStateChanged } = options;
  const detailTitleNode = detailModalNode?.querySelector<HTMLElement>("#expert-detail-title") || null;
  const detailContentNode = detailModalNode?.querySelector<HTMLElement>("#expert-detail-content") || null;
  let abortController: AbortController | null = null;
  let lastLoadOptions: ExpertPanelLoadOptions | null = null;
  let lastResponse: ExpertPanelResponse | null = null;
  let lastEnhancements: Record<string, { posibleRelevancia: string | null; resumenNutshell: string | null; esRelevante: boolean | null }> = {};
  let lastRenderedCards: ExpertCard[] = [];
  let currentStatus: ExpertPanelPersistedState["status"] = "idle";
  let loadSequence = 0;
  let enhanceFallbackAttempted = false;

  function emitStateChanged(): void {
    onStateChanged?.({
      status: currentStatus,
      loadOptions: cloneLoadOptions(lastLoadOptions),
      response: cloneExpertPanelResponse(lastResponse),
      enhancements: Object.keys(lastEnhancements).length > 0 ? { ...lastEnhancements } : null,
    });
  }

  function appendInlineNode(target: HTMLElement, node: HTMLElement): void {
    if (target.childNodes.length > 0) {
      target.appendChild(document.createTextNode(" "));
    }
    target.appendChild(node);
  }

  function appendProviderPills(
    target: HTMLElement,
    providers: ExpertProvider[],
    prefix = "expert-card-chip",
  ): void {
    const { visible, hiddenCount } = visibleProviders(providers);
    for (const provider of visible) {
      const pill = document.createElement("span");
      pill.className = `${prefix} expert-card-chip--provider ${authorityBadgeClass(provider.name)}`;
      pill.textContent = provider.name;
      appendInlineNode(target, pill);
    }
    if (hiddenCount > 0) {
      const overflow = document.createElement("span");
      overflow.className = `${prefix} expert-card-chip--provider expert-card-chip--provider-overflow`;
      overflow.textContent = i18n.t("chat.experts.providers.overflow", { count: String(hiddenCount) });
      appendInlineNode(target, overflow);
    }
  }

  function hasStableResults(): boolean {
    return currentStatus === "populated" && Boolean(lastResponse?.ok);
  }

  function showStatusNote(message: string): void {
    statusNode.textContent = message;
    statusNode.hidden = false;
    emitStateChanged();
  }

  function emitRenderedCards(cards: ExpertCard[]): void {
    lastRenderedCards = [...cards];
    emitUiEvent(contentNode, UI_EVENT_EXPERTS_UPDATED, {
      cards: cards.map((card) => toExpertCardViewModel(card)),
    });
  }

  function setStatus(status: "idle" | "loading" | "empty" | "error" | "populated"): void {
    currentStatus = status;
    contentNode.replaceChildren();
    switch (status) {
      case "idle":
        statusNode.textContent = i18n.t("chat.experts.defer");
        statusNode.hidden = false;
        emitRenderedCards([]);
        break;
      case "loading":
        statusNode.hidden = true;
        contentNode.innerHTML = `
          <div class="expert-panel-loading">
            <div class="expert-panel-spinner"></div>
            <span>${i18n.t("chat.experts.loading")}</span>
          </div>`;
        emitRenderedCards([]);
        break;
      case "empty":
        statusNode.textContent = i18n.t("chat.experts.empty");
        statusNode.hidden = false;
        emitRenderedCards([]);
        break;
      case "error":
        statusNode.textContent = i18n.t("chat.experts.error");
        statusNode.hidden = false;
        emitRenderedCards([]);
        break;
      case "populated":
        statusNode.hidden = true;
        break;
    }
    emitStateChanged();
  }

  function renderSourceActions(snippet: ExpertSnippet): HTMLElement | null {
    const links = Array.isArray(snippet.provider_links) ? snippet.provider_links.slice(0, 3) : [];
    const hasSnippetClick = typeof options.onSnippetClick === "function" && Boolean(normalizeText(snippet.doc_id));
    const sourceViewUrl = normalizeText(snippet.source_view_url || "");
    if (links.length === 0 && !hasSnippetClick && !sourceViewUrl) {
      return null;
    }
    const actions = document.createElement("div");
    actions.className = "expert-detail-source-actions";

    if (hasSnippetClick) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "secondary-mini-btn";
      button.textContent = "Abrir detalle";
      button.addEventListener("click", () => {
        options.onSnippetClick?.(normalizeText(snippet.doc_id));
      });
      actions.appendChild(button);
    }

    for (const link of links) {
      const url = normalizeText(link.url);
      if (!url) continue;
      const anchor = document.createElement("a");
      anchor.className = "expert-detail-link";
      anchor.href = url;
      anchor.target = "_blank";
      anchor.rel = "noopener noreferrer";
      anchor.textContent = normalizeText(link.provider || link.label) || i18n.t("chat.experts.detail.externalLink");
      actions.appendChild(anchor);
    }

    if (links.length === 0 && sourceViewUrl) {
      const anchor = document.createElement("a");
      anchor.className = "expert-detail-link";
      anchor.href = sourceViewUrl;
      anchor.textContent = "Ver en corpus";
      actions.appendChild(anchor);
    }

    return actions.children.length > 0 ? actions : null;
  }

  function humanSourceTitle(snippet: ExpertSnippet): string {
    const raw = normalizeText(snippet.title);
    // Reject slug-like titles: no spaces and longer than 30 chars (raw doc_id artifacts)
    const isSlug = raw.length > 30 && !/\s/.test(raw);
    if (raw && !isSlug) return raw;
    return normalizeText(snippet.authority) || "Fuente profesional";
  }

  function renderSourceCard(snippet: ExpertSnippet): HTMLElement {
    const source = document.createElement("article");
    source.className = "expert-detail-source";

    const links = Array.isArray(snippet.provider_links) ? snippet.provider_links : [];
    const firstUrl = normalizeText(links.find((link) => normalizeText(link.url))?.url || snippet.source_view_url || "");
    const titleText = humanSourceTitle(snippet);

    const title = document.createElement("h4");
    title.className = "expert-detail-source-title";
    title.textContent = titleText;
    source.appendChild(title);

    if (firstUrl) {
      const sourceLink = document.createElement("a");
      sourceLink.className = "expert-detail-source-original-link";
      sourceLink.href = firstUrl;
      sourceLink.target = "_blank";
      sourceLink.rel = "noopener noreferrer";
      sourceLink.textContent = "(ver fuente original)";
      source.appendChild(sourceLink);
    }

    const excerpt = normalizeText(snippet.card_summary || snippet.snippet || "");
    if (excerpt) {
      const body = document.createElement("p");
      body.className = "expert-detail-source-body";
      body.textContent = excerpt;
      source.appendChild(body);
    }

    const actions = renderSourceActions(snippet);
    if (actions) {
      source.appendChild(actions);
    }

    return source;
  }

  function renderMarkdownContent(markdown: string): HTMLElement {
    const container = document.createElement("div");
    container.className = "expert-explore-content";
    const lines = markdown.split("\n");
    let currentList: HTMLElement | null = null;
    let currentListType: "ul" | "ol" | null = null;

    function flushList(): void {
      if (currentList) {
        container.appendChild(currentList);
        currentList = null;
        currentListType = null;
      }
    }

    for (const rawLine of lines) {
      const line = rawLine;
      const headingMatch = /^(#{1,4})\s+(.+)$/.exec(line);
      if (headingMatch) {
        flushList();
        const level = Math.min(headingMatch[1].length + 1, 5);
        const heading = document.createElement(`h${level}` as keyof HTMLElementTagNameMap);
        heading.className = "expert-explore-heading";
        heading.textContent = headingMatch[2];
        container.appendChild(heading);
        continue;
      }
      const bulletMatch = /^\s*[-*+]\s+(.+)$/.exec(line);
      if (bulletMatch) {
        if (currentListType !== "ul") {
          flushList();
          currentList = document.createElement("ul");
          currentList.className = "expert-explore-list";
          currentListType = "ul";
        }
        const li = document.createElement("li");
        li.textContent = bulletMatch[1];
        currentList?.appendChild(li);
        continue;
      }
      const numberedMatch = /^\s*(\d+)[.)]\s+(.+)$/.exec(line);
      if (numberedMatch) {
        if (currentListType !== "ol") {
          flushList();
          currentList = document.createElement("ol");
          currentList.className = "expert-explore-list";
          currentListType = "ol";
        }
        const li = document.createElement("li");
        li.textContent = numberedMatch[2];
        currentList?.appendChild(li);
        continue;
      }
      const trimmed = line.trim();
      if (!trimmed) {
        flushList();
        continue;
      }
      flushList();
      const p = document.createElement("p");
      p.className = "expert-explore-paragraph";
      p.textContent = trimmed.replace(/\*\*([^*]+)\*\*/g, "$1");
      container.appendChild(p);
    }
    flushList();
    return container;
  }

  async function fetchEnhance(cards: ExpertCard[]): Promise<void> {
    const message = normalizeText(lastLoadOptions?.message || "");
    const assistantAnswer = normalizeText(lastLoadOptions?.assistantAnswer || "");
    if (!message || cards.length === 0) return;

    const cardPayloads = cards.map((card) => ({
      card_id: card.id,
      article_ref: card.articleRef,
      classification: card.classification,
      summary_signal: card.summarySignal,
      dominant_signal: card.dominantSignal,
      snippets: card.sources.slice(0, 3).map((s) => ({
        card_summary: s.card_summary,
        snippet: s.snippet,
      })),
    }));

    try {
      const raw = await fetch("/api/expert-panel/enhance", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          trace_id: lastLoadOptions?.traceId || "",
          message,
          assistant_answer: assistantAnswer,
          cards: cardPayloads,
        }),
      });
      const response = raw.ok ? await raw.json() : null;
      if (response?.ok && Array.isArray(response.enhancements)) {
        applyEnhancements(response.enhancements, cards);
      }
    } catch {
      // Enhancement is best-effort; silent failure keeps cards intact
    }
  }

  function applyEnhancements(
    enhancements: Array<{ card_id: string; es_relevante?: boolean; posible_relevancia: string; resumen_nutshell: string }>,
    cards: ExpertCard[],
  ): void {
    for (const enhancement of enhancements) {
      const cardId = String(enhancement.card_id || "").trim();
      if (!cardId) continue;
      const relevancia = String(enhancement.posible_relevancia || "").trim();
      // Text is authoritative: if posible_relevancia starts with "No aplica", override the boolean
      const textSaysNoAplica = relevancia.toLowerCase().startsWith("no aplica");
      const esRelevante = enhancement.es_relevante !== false && !textSaysNoAplica; // default true for backwards compat
      const nutshell = String(enhancement.resumen_nutshell || "").trim();

      // Update in-memory card for modal use
      const card = cards.find((c) => c.id === cardId);
      if (card) {
        card.posibleRelevancia = relevancia || null;
        card.resumenNutshell = nutshell || null;
        card.esRelevante = esRelevante;
      }

      // Persist enhancement for cross-question restore
      lastEnhancements[cardId] = {
        posibleRelevancia: relevancia || null,
        resumenNutshell: nutshell || null,
        esRelevante,
      };

      // Patch DOM on the rendered card button.
      // Card ids appear in a quoted attribute value, so only " needs escaping (not CSS.escape).
      const safeCardId = cardId.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
      const cardEl = contentNode.querySelector<HTMLElement>(`[data-card-id="${safeCardId}"]`);
      if (!cardEl) continue;

      // Hide irrelevant cards entirely
      if (!esRelevante) {
        cardEl.hidden = true;
        cardEl.classList.add("expert-card--irrelevant");
        continue;
      }

      // Quality gate: relevant but no articulated reason → noise
      if (esRelevante && !relevancia) {
        cardEl.hidden = true;
        cardEl.classList.add("expert-card--low-quality");
        continue;
      }

      if (relevancia) {
        const rel = cardEl.querySelector<HTMLElement>(".expert-card-relevancia");
        if (rel) {
          rel.textContent = relevancia;
          rel.hidden = false;
          rel.classList.add("expert-card-relevancia--visible");
        }
      }

      if (nutshell) {
        const nut = cardEl.querySelector<HTMLElement>(".expert-card-nutshell");
        if (nut) {
          nut.textContent = nutshell;
          nut.hidden = false;
          nut.classList.add("expert-card-nutshell--visible");
        }
        // Hide the generic lead title once nutshell is ready
        const title = cardEl.querySelector<HTMLElement>(".expert-card-title");
        if (title) {
          title.hidden = true;
        }
      }
    }

    // Persist enhancements so question-switching restores curated state
    emitStateChanged();
  }

  async function fetchExplore(
    card: ExpertCard,
    mode: "summary" | "deep",
    targetNode: HTMLElement,
  ): Promise<void> {
    const message = normalizeText(lastLoadOptions?.message || "");
    if (!message) return;

    targetNode.innerHTML = `
      <div class="expert-panel-loading expert-explore-loading">
        <div class="expert-panel-spinner"></div>
        <span>${mode === "summary" ? "Generando síntesis…" : "Generando análisis a profundidad…"}</span>
      </div>`;

    try {
      const body = {
        trace_id: lastLoadOptions?.traceId || "",
        mode,
        message,
        assistant_answer: normalizeText(lastLoadOptions?.assistantAnswer || "") || undefined,
        classification: card.classification,
        article_ref: card.articleRef,
        summary_signal: card.summarySignal,
        snippets: card.sources.map((s) => ({
          authority: s.authority,
          card_summary: s.card_summary,
          snippet: s.snippet,
          position_signal: s.position_signal,
        })),
      };
      const raw = await fetch("/api/expert-panel/explore", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const response = raw.ok ? await raw.json() : null;
      if (response?.ok && response.content) {
        targetNode.innerHTML = "";
        targetNode.appendChild(renderMarkdownContent(response.content));
      } else {
        targetNode.innerHTML = `<p class="expert-explore-error">No fue posible generar el análisis. Intenta de nuevo.</p>`;
      }
    } catch {
      targetNode.innerHTML = `<p class="expert-explore-error">Error de conexión. Intenta de nuevo.</p>`;
    }
  }

  function renderExpertTab(snippet: ExpertSnippet, card: ExpertCard): HTMLElement {
    const tab = document.createElement("article");
    tab.className = "expert-detail-tab";

    const header = document.createElement("button");
    header.type = "button";
    header.className = "expert-detail-tab-header";
    header.setAttribute("aria-expanded", "false");

    const headerInner = document.createElement("div");
    headerInner.className = "expert-detail-tab-header-inner";

    const eyebrow = document.createElement("div");
    eyebrow.className = "expert-detail-tab-eyebrow";
    const authorityName = normalizeText(snippet.authority);
    if (authorityName) {
      const authorityChip = document.createElement("span");
      authorityChip.className = `expert-detail-tab-authority ${authorityBadgeClass(authorityName)}`;
      authorityChip.textContent = authorityName;
      eyebrow.appendChild(authorityChip);
    }
    if (card.articleLabel) {
      const articleHint = document.createElement("span");
      articleHint.className = "expert-detail-tab-article";
      articleHint.textContent = card.articleLabel;
      eyebrow.appendChild(articleHint);
    }

    // Intentionally no separate "title" element here — the eyebrow chip
    // (provider) + article hint already say WHO and WHAT, and the body's
    // first `### ` heading immediately frames the section once expanded.
    // The snippet's `title` field is often the doc's full multi-line name
    // ("FIR-E01 — Firmeza de las Declaraciones Tributarias: …"), which
    // duplicates the modal header and crowds the collapsed tab.
    // Per-expert elevator summary — each expert's body preview must be
    // distinct from its siblings. Falls through the sanitizer so the
    // internal doc code and "Tema principal:" plumbing never leak here.
    const previewText = clipText(
      buildElevatorSummary(snippet, 220) || sanitizeExpertText(snippet.card_summary || snippet.snippet || ""),
      220,
    );
    headerInner.append(eyebrow);
    if (previewText) {
      const preview = document.createElement("p");
      preview.className = "expert-detail-tab-preview";
      preview.textContent = previewText;
      headerInner.append(preview);
    }

    const toggle = document.createElement("span");
    toggle.className = "expert-detail-tab-toggle";
    const toggleLabel = document.createElement("span");
    toggleLabel.className = "expert-detail-tab-toggle-label";
    toggleLabel.textContent = i18n.t("chat.experts.detail.expertOpen");
    const toggleIcon = document.createElement("span");
    toggleIcon.className = "expert-detail-tab-toggle-icon";
    toggleIcon.setAttribute("aria-hidden", "true");
    toggle.append(toggleLabel, toggleIcon);

    header.append(headerInner, toggle);

    const body = document.createElement("div");
    body.className = "expert-detail-tab-body";
    body.hidden = true;

    // Render the actual expert prose. `extended_excerpt` carries a clean
    // markdown subset (### headings, - bullets, **bold** inline, | tables)
    // emitted by the backend extractor. We pass it raw to renderExpertProse —
    // running it through normalizeText would strip the markdown markers and
    // collapse table-row newlines into spaces. The legacy `snippet` fallback
    // is also routed through renderExpertProse so embedded tables survive
    // even when the extended excerpt is missing.
    const extended = String(snippet.extended_excerpt || "").trim();
    const fallbackBody = String(snippet.snippet || snippet.card_summary || "").trim();
    const proseHost = document.createElement("div");
    proseHost.className = "expert-detail-tab-prose";
    if (extended) {
      renderExpertProse(proseHost, extended);
    } else if (fallbackBody) {
      renderExpertProse(proseHost, fallbackBody);
    } else {
      const empty = document.createElement("p");
      empty.className = "expert-detail-tab-paragraph expert-detail-tab-paragraph--empty";
      empty.textContent =
        "Sin extracto disponible para esta fuente. Abre el enlace original para leer el material completo.";
      proseHost.appendChild(empty);
    }
    body.appendChild(proseHost);

    const links = Array.isArray(snippet.provider_links) ? snippet.provider_links : [];
    const sourceUrl = normalizeText(
      links.find((link) => normalizeText(link.url))?.url || snippet.source_view_url || "",
    );
    if (sourceUrl) {
      const footer = document.createElement("div");
      footer.className = "expert-detail-tab-footer";
      const sourceLink = document.createElement("a");
      sourceLink.className = "expert-detail-source-original-link";
      sourceLink.href = sourceUrl;
      sourceLink.target = "_blank";
      sourceLink.rel = "noopener noreferrer";
      sourceLink.textContent = "(ver fuente original)";
      footer.appendChild(sourceLink);
      body.appendChild(footer);
    }

    header.addEventListener("click", () => {
      const expanded = header.getAttribute("aria-expanded") === "true";
      header.setAttribute("aria-expanded", expanded ? "false" : "true");
      body.hidden = expanded;
      tab.classList.toggle("expert-detail-tab--expanded", !expanded);
      toggleLabel.textContent = i18n.t(
        expanded ? "chat.experts.detail.expertOpen" : "chat.experts.detail.expertClose",
      );
    });

    tab.append(header, body);
    return tab;
  }

  function openCardDetail(card: ExpertCard): void {
    if (!detailModalNode || !detailTitleNode || !detailContentNode || typeof openModal !== "function") {
      return;
    }
    applySplitTitle(detailTitleNode, card.heading);
    detailContentNode.innerHTML = "";

    const banner = document.createElement("section");
    banner.className = `expert-detail-banner expert-detail-banner--${card.classification}`;

    const bannerMeta = document.createElement("div");
    bannerMeta.className = "expert-detail-banner-meta";

    if (card.classification !== "individual" || card.providers.length === 0) {
      const classBadge = document.createElement("span");
      classBadge.className = `expert-card-chip expert-card-chip--${card.classification}`;
      classBadge.textContent = classificationLabel(i18n, card.classification);
      appendInlineNode(bannerMeta, classBadge);
    }

    if (card.articleLabel) {
      const articleBadge = document.createElement("span");
      articleBadge.className = "expert-card-chip expert-card-chip--article";
      articleBadge.textContent = card.articleLabel;
      appendInlineNode(bannerMeta, articleBadge);
    }

    appendProviderPills(bannerMeta, card.providers);

    if (card.dominantSignal !== "neutral") {
      const signalBadge = document.createElement("span");
      signalBadge.className = `expert-card-chip expert-card-chip--signal expert-card-chip--signal-${card.dominantSignal}`;
      signalBadge.textContent = signalLabel(i18n, card.dominantSignal);
      appendInlineNode(bannerMeta, signalBadge);
    }

    // "Consulta del turno" and "Posible relevancia" intentionally omitted:
    // the user already knows their own question, and showing a card IS the
    // signal of possible relevance — stating it is redundant plumbing.
    banner.appendChild(bannerMeta);

    const evidence = document.createElement("p");
    evidence.className = "expert-detail-evidence";
    evidence.textContent = sourceCountLabel(card.sources);
    banner.append(evidence);

    if (card.resumenNutshell) {
      const nutshellBlock = document.createElement("p");
      nutshellBlock.className = "expert-detail-nutshell-lead";
      nutshellBlock.textContent = card.resumenNutshell;
      banner.append(nutshellBlock);
    }

    // --- Per-expert tabs lead the modal ---
    const tabsSection = document.createElement("section");
    tabsSection.className = "expert-detail-tabs-shell";
    const tabsTitle = document.createElement("h4");
    tabsTitle.className = "expert-detail-section-title";
    tabsTitle.textContent = i18n.t("chat.experts.detail.experts");
    const tabs = document.createElement("div");
    tabs.className = "expert-detail-tabs";
    for (const source of card.sources) {
      tabs.appendChild(renderExpertTab(source, card));
    }
    tabsSection.append(tabsTitle, tabs);

    // --- Practical reading + checklist ---
    const grid = document.createElement("div");
    grid.className = "expert-detail-grid";

    const implicationPanel = document.createElement("section");
    implicationPanel.className = "expert-detail-panel";
    const implicationTitle = document.createElement("h4");
    implicationTitle.className = "expert-detail-panel-title";
    implicationTitle.textContent = i18n.t("chat.experts.detail.reading");
    const implicationBody = document.createElement("p");
    implicationBody.className = "expert-detail-panel-body";
    implicationBody.textContent = card.implication;
    implicationPanel.append(implicationTitle, implicationBody);

    const checklistPanel = document.createElement("section");
    checklistPanel.className = "expert-detail-panel";
    const checklistTitle = document.createElement("h4");
    checklistTitle.className = "expert-detail-panel-title";
    checklistTitle.textContent = i18n.t("chat.experts.detail.checklist");
    const checklist = document.createElement("ul");
    checklist.className = "expert-detail-checklist";
    for (const item of card.checklist) {
      const li = document.createElement("li");
      li.textContent = item;
      checklist.appendChild(li);
    }
    checklistPanel.append(checklistTitle, checklist);

    grid.append(implicationPanel, checklistPanel);

    detailContentNode.append(banner, tabsSection, grid);
    openModal(detailModalNode);
  }

  function toExpertCardViewModel(card: ExpertCard): ExpertCardViewModel {
    const { visible, hiddenCount } = visibleProviders(card.providers);
    // Nutshell fallback: when the enhance API hasn't returned a curated
    // `resumenNutshell`, synthesize a per-card elevator summary from the
    // primary source so cards never display a bare template title.
    const primarySource = card.sources[0];
    const fallbackNutshell = primarySource ? buildElevatorSummary(primarySource, 320) : "";
    return {
      articleLabel: card.articleLabel,
      classification: card.classification,
      classificationLabel: classificationLabel(i18n, card.classification),
      heading: sanitizeExpertText(card.lead) || card.lead,
      hidden: card.esRelevante === false || !card.posibleRelevancia || Boolean((card.posibleRelevancia || "").trim().toLowerCase().startsWith("no aplica")),
      id: card.id,
      nutshell: card.resumenNutshell || fallbackNutshell || null,
      providerLabels: visible.map((provider) => provider.name),
      providerOverflowLabel: hiddenCount > 0
        ? i18n.t("chat.experts.providers.overflow", { count: String(hiddenCount) })
        : null,
      relevancia: card.posibleRelevancia || null,
      signal: card.dominantSignal,
      signalLabel: card.dominantSignal !== "neutral" ? signalLabel(i18n, card.dominantSignal) : "",
      sourceCountLabel: sourceCountLabel(card.sources),
    };
  }

  function renderResults(
    data: ExpertPanelResponse,
    { preserveExistingOnEmpty = false }: { preserveExistingOnEmpty?: boolean } = {},
  ): boolean {
    const requestedRefs = buildRequestedRefSet(lastLoadOptions?.normativeArticleRefs || []);
    const cards = buildCards(data, requestedRefs);
    if (cards.length === 0) {
      if (preserveExistingOnEmpty && hasStableResults()) {
        showStatusNote(i18n.t("chat.experts.refreshEmpty"));
        return false;
      }
      lastResponse = cloneExpertPanelResponse(data);
      setStatus("empty");
      return false;
    }

    lastResponse = cloneExpertPanelResponse(data);
    setStatus("populated");

    // Pre-apply cached enhancements so restored cards render curated immediately
    for (const card of cards) {
      const cached = lastEnhancements[card.id];
      if (cached) {
        card.posibleRelevancia = cached.posibleRelevancia;
        card.resumenNutshell = cached.resumenNutshell;
        card.esRelevante = cached.esRelevante;
      }
    }

    // Relevance pre-filter: only show cards that have passed the enhance curation gate
    const visibleCards: ExpertCard[] = [];
    for (const card of cards) {
      if (card.esRelevante === false) continue;
      if ((card.posibleRelevancia || "").trim().toLowerCase().startsWith("no aplica")) continue;
      if (!card.posibleRelevancia) continue; // require relevance phrase — no uncurated cards
      if (visibleCards.length < 5) visibleCards.push(card);
    }

    renderExpertCardList(
      contentNode,
      visibleCards.map((card) => toExpertCardViewModel(card)),
      { onCardClick: (cardViewModel) => {
        const fullCard = visibleCards.find((card) => card.id === cardViewModel.id);
        if (fullCard) openCardDetail(fullCard);
      } },
    );
    emitRenderedCards(visibleCards);

    // Fallback: if no visible cards because enhance hasn't run yet, try enhancing
    // all cards once (guard prevents infinite re-render loop)
    if (visibleCards.length === 0 && cards.length > 0 && !enhanceFallbackAttempted) {
      const unenhanced = cards.filter((c) => !c.posibleRelevancia && !c.resumenNutshell);
      if (unenhanced.length > 0) {
        enhanceFallbackAttempted = true;
        void fetchEnhance(unenhanced).then(() => {
          if (lastResponse) renderResults(lastResponse);
        });
      }
    }

    if (data.has_more) {
      const totalAvailable = data.total_available ?? 0;
      const remaining = Math.max(0, totalAvailable - cards.length);
      const moreCount = Math.min(3, remaining);
      const moreBtn = document.createElement("button");
      moreBtn.type = "button";
      moreBtn.className = "expert-panel-more-btn";
      moreBtn.textContent = moreCount > 0
        ? i18n.t("chat.experts.loadMore", { count: String(moreCount) })
        : i18n.t("chat.experts.loadMore", { count: "+" });
      moreBtn.addEventListener("click", () => loadMore(moreBtn));
      contentNode.appendChild(moreBtn);
    }
    return true;
  }

  async function loadMore(button: HTMLButtonElement): Promise<void> {
    if (!lastLoadOptions) return;
    button.disabled = true;
    button.textContent = i18n.t("chat.experts.loadMore.loading");

    try {
      const requestedRefs = buildRequestedRefSet(lastLoadOptions.normativeArticleRefs || []);
      const alreadyLoadedCount = buildCards(lastResponse || { ok: true, groups: [], ungrouped: [] }, requestedRefs).length;
      const nextOffset = Number(lastResponse?.next_offset);
      const body = {
        trace_id: lastLoadOptions.traceId,
        message: lastLoadOptions.message,
        assistant_answer: lastLoadOptions.assistantAnswer || null,
        normative_article_refs: lastLoadOptions.normativeArticleRefs || [],
        search_seed: lastLoadOptions.searchSeed || null,
        search_seed_origin: lastLoadOptions.searchSeedOrigin || null,
        topic: lastLoadOptions.topic || undefined,
        pais: lastLoadOptions.pais || "colombia",
        top_k: 12,
        process_limit: 3,
        offset: Number.isFinite(nextOffset) ? nextOffset : alreadyLoadedCount,
      };

      const raw = await fetch("/api/expert-panel", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const response: ExpertPanelResponse | null = raw.ok ? await raw.json() : null;

      if (response?.ok) {
        // Enhance new cards BEFORE rendering so renderResults filters irrelevant ones immediately
        const requestedRefs = buildRequestedRefSet(lastLoadOptions?.normativeArticleRefs || []);
        const newCards = buildCards(response, requestedRefs).filter((c) => !lastEnhancements[c.id]);
        if (newCards.length > 0) {
          await fetchEnhance(newCards);
        }
        const mergedResponse = mergeExpertPanelResponses(lastResponse, response);
        if (mergedResponse) {
          renderResults(mergedResponse);
        } else {
          button.disabled = false;
          button.textContent = i18n.t("chat.experts.loadMore.retry");
        }
      } else {
        button.disabled = false;
        button.textContent = i18n.t("chat.experts.loadMore.retry");
      }
    } catch {
      button.disabled = false;
      button.textContent = i18n.t("chat.experts.loadMore.retry");
    }
  }

  async function load(opts: ExpertPanelLoadOptions): Promise<void> {
    if (abortController) {
      abortController.abort();
    }
    abortController = new AbortController();
    const { signal } = abortController;
    const requestSequence = ++loadSequence;
    const nextLoadOptions = cloneLoadOptions(opts);
    const nextTraceId = normalizeText(nextLoadOptions?.traceId || "");
    const activeTraceId = normalizeText(lastLoadOptions?.traceId || "");
    const sameTraceRefresh = Boolean(nextTraceId) && nextTraceId === activeTraceId && hasStableResults();
    lastLoadOptions = nextLoadOptions;

    if (sameTraceRefresh) {
      showStatusNote(i18n.t("chat.experts.refreshing"));
    } else {
      if (!nextTraceId || nextTraceId !== activeTraceId) {
        lastResponse = null;
        lastEnhancements = {};
        enhanceFallbackAttempted = false;
      }
      setStatus("loading");
    }

    try {
      const body = {
        trace_id: nextLoadOptions?.traceId || "",
        message: nextLoadOptions?.message || "",
        assistant_answer: nextLoadOptions?.assistantAnswer || null,
        normative_article_refs: nextLoadOptions?.normativeArticleRefs || [],
        search_seed: nextLoadOptions?.searchSeed || null,
        search_seed_origin: nextLoadOptions?.searchSeedOrigin || null,
        topic: nextLoadOptions?.topic || undefined,
        pais: nextLoadOptions?.pais || "colombia",
        top_k: 12,
        process_limit: 5,
        offset: 0,
      };

      const raw = await fetch("/api/expert-panel", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        signal,
      });
      if (signal.aborted || requestSequence !== loadSequence) return;
      const response: ExpertPanelResponse | null = raw.ok ? await raw.json() : null;

      if (response && response.ok) {
        // Build cards and curate via enhance BEFORE rendering (show spinner until ready)
        const requestedRefs = buildRequestedRefSet(lastLoadOptions?.normativeArticleRefs || []);
        const preCards = buildCards(response, requestedRefs);
        const unenhanced = preCards.filter((c) => !c.posibleRelevancia && !c.resumenNutshell && !lastEnhancements[c.id]);
        if (unenhanced.length > 0) {
          const loadingLabel = contentNode.querySelector<HTMLElement>(".expert-panel-loading span");
          if (loadingLabel) loadingLabel.textContent = i18n.t("chat.experts.curating");
          await fetchEnhance(unenhanced);
          if (signal.aborted || requestSequence !== loadSequence) return;
        }
        renderResults(response, { preserveExistingOnEmpty: sameTraceRefresh });
      } else {
        if (sameTraceRefresh && hasStableResults()) {
          showStatusNote(i18n.t("chat.experts.refreshEmpty"));
          return;
        }
        lastResponse = null;
        setStatus("empty");
      }
    } catch (err: unknown) {
      if (signal.aborted || requestSequence !== loadSequence) return;
      if (err instanceof DOMException && err.name === "AbortError") return;
      if (sameTraceRefresh && hasStableResults()) {
        showStatusNote(i18n.t("chat.experts.refreshError"));
        return;
      }
      lastResponse = null;
      setStatus("error");
    }
  }

  function restoreState(
    snapshot: ExpertPanelPersistedState | null,
    fallbackLoadOptions: ExpertPanelLoadOptions | null = null
  ): void {
    const normalizedSnapshot =
      snapshot && typeof snapshot === "object"
        ? {
            status:
              snapshot.status === "idle" ||
              snapshot.status === "loading" ||
              snapshot.status === "empty" ||
              snapshot.status === "error" ||
              snapshot.status === "populated"
                ? snapshot.status
                : "idle",
            loadOptions: cloneLoadOptions(snapshot.loadOptions || null),
            response: cloneExpertPanelResponse(snapshot.response || null),
            enhancements: snapshot.enhancements && typeof snapshot.enhancements === "object"
              ? { ...snapshot.enhancements }
              : null,
          }
        : null;

    if (abortController) {
      abortController.abort();
      abortController = null;
    }
    loadSequence += 1;

    if (!normalizedSnapshot) {
      lastLoadOptions = cloneLoadOptions(fallbackLoadOptions);
      lastResponse = null;
      lastEnhancements = {};
      if (fallbackLoadOptions?.traceId) {
        void load(fallbackLoadOptions);
      } else {
        setStatus("idle");
      }
      return;
    }

    lastLoadOptions = normalizedSnapshot.loadOptions;
    lastResponse = normalizedSnapshot.response;
    lastEnhancements = normalizedSnapshot.enhancements && typeof normalizedSnapshot.enhancements === "object"
      ? { ...normalizedSnapshot.enhancements }
      : {};

    if (normalizedSnapshot.status === "populated" && normalizedSnapshot.response?.ok) {
      renderResults(normalizedSnapshot.response);
      return;
    }

    if (normalizedSnapshot.status === "loading" && normalizedSnapshot.loadOptions?.traceId) {
      void load(normalizedSnapshot.loadOptions);
      return;
    }

    setStatus(normalizedSnapshot.status);
  }

  function getPersistedState(): ExpertPanelPersistedState | null {
    return {
      status: currentStatus,
      loadOptions: cloneLoadOptions(lastLoadOptions),
      response: cloneExpertPanelResponse(lastResponse),
      enhancements: Object.keys(lastEnhancements).length > 0 ? { ...lastEnhancements } : null,
    };
  }

  function clear(): void {
    if (abortController) {
      abortController.abort();
      abortController = null;
    }
    loadSequence += 1;
    lastLoadOptions = null;
    lastResponse = null;
    lastEnhancements = {};
    lastRenderedCards = [];
    if (detailTitleNode) {
      detailTitleNode.textContent = i18n.t("chat.experts.modal.title");
    }
    if (detailContentNode) {
      detailContentNode.innerHTML = "";
    }
    setStatus("idle");
  }

  setStatus("idle");

  return {
    load,
    clear,
    restoreState,
    getPersistedState,
    openCardById(cardId: string) {
      const match = lastRenderedCards.find((card) => card.id === String(cardId || "").trim());
      if (match) {
        openCardDetail(match);
      }
    },
  };
}
