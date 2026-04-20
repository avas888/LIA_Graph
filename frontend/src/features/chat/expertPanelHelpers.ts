// @ts-nocheck

/**
 * Pre-controller helpers for the expert panel.
 *
 * Extracted from `expertPanelController.ts` during granularize-v2
 * round 17 (second attempt, cautious). All functions here are pure —
 * no closure over controller state. The host re-imports every name.
 *
 * Explicitly imports all external symbols (stripMarkdown,
 * sanitizeExpertText, buildElevatorSummary, I18nRuntime type) to avoid
 * the "stripMarkdown is not defined" regression from round 8.
 */

import type { I18nRuntime } from "@/shared/i18n";
import { stripMarkdown } from "@/shared/utils/format";
import {
  buildElevatorSummary,
  sanitizeExpertText,
} from "@/features/chat/expertSummaryText";

import type {
  ExpertCard,
  ExpertCardClassification,
  ExpertGroup,
  ExpertPanelLoadOptions,
  ExpertPanelResponse,
  ExpertProvider,
  ExpertSignal,
  ExpertSnippet,
} from "@/features/chat/expertPanelTypes";


export function authorityBadgeClass(authority: string): string {
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

export function normalizeText(value: string): string {
  return stripMarkdown(String(value || "")).replace(/\s+/g, " ").trim();
}

export const METACOGNITIVE_RE = /(?:la fuente no proporciona|el texto fuente est[áa] vac[ií]o|no es posible generar|no proporciona texto|no contiene informaci[oó]n suficiente|incluya el texto|proporcione el texto|no se puede extraer|no hay contenido|la fuente est[áa] vac[ií]a)/i;

export function isMetacognitive(text: string): boolean {
  return METACOGNITIVE_RE.test(text);
}

export function sourceCountLabel(snippets: ExpertSnippet[]): string {
  const sourceCount = snippets.length;
  return `${sourceCount} fuente${sourceCount === 1 ? "" : "s"}`;
}

export function clipText(value: string, maxChars: number): string {
  const cleaned = normalizeText(value);
  if (!cleaned || cleaned.length <= maxChars) return cleaned;
  return `${cleaned.slice(0, Math.max(0, maxChars - 1)).trimEnd()}…`;
}

export function ensureSentence(value: string): string {
  const cleaned = normalizeText(value);
  if (!cleaned) return "";
  return /[.!?…]$/.test(cleaned) ? cleaned : `${cleaned}.`;
}

export function canonicalizeNormativeRef(value: string): string {
  return String(value || "")
    .trim()
    .toLowerCase()
    .replace(/[:.\-–—]/g, "_")
    .replace(/\s+/g, "_")
    .replace(/__+/g, "_")
    .replace(/^_+|_+$/g, "");
}

export function buildRequestedRefSet(rawRefs: string[]): Set<string> {
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

export function humanizeArticleRef(articleRef: string): string {
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

export function sortSources(snippets: ExpertSnippet[]): ExpertSnippet[] {
  return [...snippets].sort((left, right) => {
    const byRelevance = (right.relevance_score || 0) - (left.relevance_score || 0);
    if (Math.abs(byRelevance) > 0.0001) return byRelevance;
    return normalizeText(left.authority).localeCompare(normalizeText(right.authority), "es", {
      sensitivity: "base",
    });
  });
}

export function uniqueAuthorities(snippets: ExpertSnippet[]): string[] {
  return Array.from(
    new Set(
      snippets
        .map((snippet) => normalizeText(snippet.authority))
        .filter(Boolean),
    ),
  );
}

export function dominantSignal(snippets: ExpertSnippet[]): ExpertSignal {
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

export function signalLabel(i18n: I18nRuntime, signal: ExpertSignal): string {
  return i18n.t(`chat.experts.signal.${signal}`);
}



export function classificationLabel(i18n: I18nRuntime, classification: ExpertCardClassification): string {
  if (classification === "individual") {
    return i18n.t("chat.experts.individual");
  }
  return i18n.t(`chat.experts.${classification}`);
}

export function buildImplication(classification: ExpertCardClassification, signal: ExpertSignal): string {
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

export function buildChecklist(
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

export function normalizeProviders(providers: ExpertProvider[]): ExpertProvider[] {
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

export function collectProviders(snippets: ExpertSnippet[], seed: ExpertProvider[] = []): ExpertProvider[] {
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

export function cardSummaryFromSnippet(snippet: ExpertSnippet): string {
  const elevator = buildElevatorSummary(snippet, 480);
  if (elevator) return elevator;
  const summary = ensureSentence(sanitizeExpertText(snippet.card_summary));
  if (summary && !isMetacognitive(summary)) return clipText(summary, 480);
  return "Abre el detalle para revisar el criterio aplicable.";
}

export function buildCardFromGroup(group: ExpertGroup, requestedRefs: Set<string>): ExpertCard {
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

export function buildCardFromSnippet(snippet: ExpertSnippet): ExpertCard {
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

export function classificationRank(classification: ExpertCardClassification): number {
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

export function signalRank(signal: ExpertSignal): number {
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

export function buildCards(data: ExpertPanelResponse, requestedRefs: Set<string>): ExpertCard[] {
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

export function groupKey(group: ExpertGroup): string {
  return `${canonicalizeNormativeRef(group.article_ref)}::${normalizeText(group.classification)}`;
}

export function snippetKey(snippet: ExpertSnippet): string {
  return normalizeText(snippet.doc_id);
}

export function mergeExpertPanelResponses(
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

export function visibleProviders(providers: ExpertProvider[]): { visible: ExpertProvider[]; hiddenCount: number } {
  const normalized = normalizeProviders(providers);
  return {
    visible: normalized.slice(0, 4),
    hiddenCount: Math.max(0, normalized.length - 4),
  };
}

export function cloneLoadOptions(loadOptions: ExpertPanelLoadOptions | null): ExpertPanelLoadOptions | null {
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

export function cloneExpertPanelResponse(response: ExpertPanelResponse | null): ExpertPanelResponse | null {
  if (!response) return null;
  return JSON.parse(JSON.stringify(response));
}


export function renderMarkdownContent(markdown: string): HTMLElement {
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
