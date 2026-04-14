// @ts-nocheck

/**
 * Deferred citation lifecycle — context, caching, on-demand loading, background resolve.
 * Extracted from requestController.ts during decouple-v1 Phase 4.
 */

import {
  asCitationArray,
  filterCitedOnly,
  filterNormativeHelperBaseCitations,
  mergeCitations,
} from "@/features/chat/citations";
import { normalizeNormativeSupportCache } from "@/features/chat/persistence";

// ── Pure helpers (no deps) ────────────────────────────────────

export function buildNormativeSupportRequestBody(context: Record<string, unknown>) {
  return {
    trace_id: context?.trace_id || `trace_${Date.now()}`,
    message: context?.message || "",
    assistant_answer: context?.assistant_answer || "",
    topic: context?.topic || undefined,
    pais: context?.pais || "colombia",
    primary_scope_mode: context?.primary_scope_mode || "global_overlay",
    top_k: 8,
  };
}

export function buildCitationRequestCacheKey(context: Record<string, unknown> | null): string {
  if (!context || typeof context !== "object") return "";
  const traceId = String(context.trace_id || "").trim();
  if (traceId) return `trace:${traceId}`;
  const msg = String(context.message || "").trim().toLowerCase();
  const answer = String(context.assistant_answer || "").trim().toLowerCase();
  const topic = String(context.topic || "").trim().toLowerCase();
  const pais = String(context.pais || "").trim().toLowerCase();
  return `msg:${msg}|answer:${answer}|topic:${topic}|pais:${pais}`;
}

export function buildCurrentNormativeSupportSnapshot(state) {
  return normalizeNormativeSupportCache({
    citationRequestContext: state.citationRequestContext,
    fallbackCitations: state.deferredCitationsFallback,
    mentionCitations: state.deferredMentionCitations,
    cachedCitations: state.deferredCitationsCache,
    statusText: state.deferredCitationsStatusText,
    placeholderText: state.deferredCitationsPlaceholderText,
  });
}

export function hasOnlyMentionOnlyCitations(citations: Record<string, unknown>[]): boolean {
  return (
    Array.isArray(citations) &&
    citations.length > 0 &&
    citations.every((citation) => Boolean(citation?.mention_only) || !String(citation?.doc_id || "").trim())
  );
}

// ── Citation loading controller factory ───────────────────────

export interface CitationLoadingDeps {
  i18n: any;
  state: any;
  citationsLoadBtn: HTMLButtonElement | null;
  withThinkingWheel: any;
  renderCitations: (citations: Record<string, unknown>[]) => void;
  renderDeferredCitationsState: (label: string, options?: { loading?: boolean }) => void;
  setCitationsStatus: (label: string) => void;
  persistActiveSessionSnapshot?: () => void;
  recordUserMilestone: (milestone: string, opts?: any) => Promise<void>;
  onChatReset?: () => void;
}

export function createCitationLoadingController(deps: CitationLoadingDeps) {
  const {
    i18n, state, citationsLoadBtn, withThinkingWheel,
    renderCitations, renderDeferredCitationsState, setCitationsStatus,
    persistActiveSessionSnapshot, recordUserMilestone, onChatReset,
  } = deps;

  let backgroundNormativeResolveTimer: number | null = null;
  let backgroundNormativeResolveCacheKey = "";

  function resetBackgroundNormativeResolve(): void {
    if (backgroundNormativeResolveTimer !== null) {
      window.clearTimeout(backgroundNormativeResolveTimer);
      backgroundNormativeResolveTimer = null;
    }
    backgroundNormativeResolveCacheKey = "";
  }

  function applyNormativeSupportView({
    citations, placeholderText, statusText, canLoadOnDemand,
    loading = false, displaySource = "", displayStatus = "ok", displayDetails = {},
  }) {
    state.deferredCitationsPlaceholderText = String(placeholderText || "").trim();
    state.deferredCitationsStatusText = String(statusText || "").trim();

    if (Array.isArray(citations) && citations.length > 0) {
      renderCitations(citations);
      void recordUserMilestone("normative_displayed", {
        source: displaySource || "render",
        status: displayStatus || "ok",
        details: {
          citations_count: citations.length,
          ...((displayDetails && typeof displayDetails === "object") ? displayDetails : {}),
        },
      });
    } else {
      renderDeferredCitationsState(state.deferredCitationsPlaceholderText, { loading });
    }
    setCitationsStatus(state.deferredCitationsStatusText);

    if (citationsLoadBtn) {
      citationsLoadBtn.disabled = !canLoadOnDemand;
      citationsLoadBtn.textContent = "Ver normativa";
    }
  }

  function clearNormativeSupportState({
    placeholderText = "Sin normativa detectada en este turno.",
    statusText = "La normativa relevante del turno aparecera aqui cuando exista soporte.",
    canLoadOnDemand = false,
    persistSnapshot = false,
    resetStoredState = true,
    loading = false,
  } = {}) {
    if (resetStoredState) {
      resetBackgroundNormativeResolve();
      state.citationRequestContext = null;
      state.deferredCitationsFallback = [];
      state.deferredMentionCitations = [];
      state.deferredCitationsCache = [];
      state.deferredCitationsCacheKey = "";
    }
    applyNormativeSupportView({
      citations: [], placeholderText, statusText, canLoadOnDemand, loading,
    });
    if (persistSnapshot) persistActiveSessionSnapshot?.();
  }

  function resetDeferredCitationsContext(): void {
    state.activeChatRunId = "";
    clearNormativeSupportState({
      placeholderText: "Preparando soporte normativo...",
      statusText: i18n.t("chat.citations.waitingTurn"),
      canLoadOnDemand: false,
      persistSnapshot: false,
      loading: true,
    });
    onChatReset?.();
  }

  async function fetchNormativeCitationsOnDemand(context: Record<string, unknown>): Promise<Record<string, unknown>[]> {
    const payload = buildNormativeSupportRequestBody(context);
    const response = await fetch("/api/normative-support", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "normative_support_failed");
    return asCitationArray(data.normative_citations);
  }

  function queueBackgroundNormativeResolve(): void {
    if (!state.citationRequestContext || !state.citationRequestContext.message) return;
    if (state.deferredMentionCitations.length === 0) return;
    const cacheKey = buildCitationRequestCacheKey(state.citationRequestContext);
    if (!cacheKey || backgroundNormativeResolveCacheKey === cacheKey) return;
    backgroundNormativeResolveCacheKey = cacheKey;
    if (backgroundNormativeResolveTimer !== null) {
      window.clearTimeout(backgroundNormativeResolveTimer);
    }
    backgroundNormativeResolveTimer = window.setTimeout(() => {
      backgroundNormativeResolveTimer = null;
      void loadCitationsOnDemand({ forceRefresh: true, suppressLoadingUi: true });
    }, 0);
  }

  function setDeferredCitationsContext(
    context: Record<string, unknown> | null,
    fallbackCitations: unknown,
    mentionCitations: unknown[] = [],
    { persistSnapshot = true } = {},
  ): void {
    state.citationRequestContext = context && typeof context === "object" ? { ...context } : null;
    state.deferredCitationsFallback = filterCitedOnly(filterNormativeHelperBaseCitations(fallbackCitations));
    state.deferredMentionCitations = asCitationArray(mentionCitations);
    state.deferredCitationsCache = mergeCitations(state.deferredCitationsFallback, state.deferredMentionCitations);
    state.deferredCitationsCacheKey = buildCitationRequestCacheKey(state.citationRequestContext);
    if (state.deferredCitationsCache.length > 0) {
      applyNormativeSupportView({
        citations: state.deferredCitationsCache,
        placeholderText: "",
        statusText: `Mostrando ${state.deferredCitationsCache.length} referencias normativas detectadas en este turno.`,
        canLoadOnDemand: Boolean(state.citationRequestContext),
        displaySource: "auto_detected",
        displayDetails: { mode: "detected" },
      });
      queueBackgroundNormativeResolve();
      if (persistSnapshot) persistActiveSessionSnapshot?.();
      return;
    }
    clearNormativeSupportState({
      placeholderText: "Sin normativa detectada en este turno.",
      statusText: "La normativa relevante del turno aparecera aqui cuando exista soporte.",
      canLoadOnDemand: Boolean(state.citationRequestContext),
      persistSnapshot,
      resetStoredState: false,
    });
  }

  function restoreNormativeSupportState(snapshot: unknown): boolean {
    const normalized = normalizeNormativeSupportCache(snapshot);
    if (!normalized) {
      clearNormativeSupportState({
        placeholderText: "Sin normativa detectada en este turno.",
        statusText: "La normativa relevante del turno aparecera aqui cuando exista soporte.",
        canLoadOnDemand: false, persistSnapshot: false,
      });
      return false;
    }
    state.citationRequestContext = normalized.citationRequestContext;
    state.deferredCitationsFallback = normalized.fallbackCitations;
    state.deferredMentionCitations = normalized.mentionCitations;
    state.deferredCitationsCache = normalized.cachedCitations;
    state.deferredCitationsCacheKey = buildCitationRequestCacheKey(state.citationRequestContext);
    applyNormativeSupportView({
      citations: state.deferredCitationsCache,
      placeholderText: normalized.placeholderText || "Sin normativa detectada en este turno.",
      statusText:
        normalized.statusText ||
        (state.deferredCitationsCache.length > 0
          ? `Mostrando ${state.deferredCitationsCache.length} referencias normativas detectadas en este turno.`
          : "La normativa relevante del turno aparecera aqui cuando exista soporte."),
      canLoadOnDemand: Boolean(state.citationRequestContext),
      displaySource: "restore",
      displayDetails: { mode: "restore" },
    });
    queueBackgroundNormativeResolve();
    return true;
  }

  async function loadCitationsOnDemand(
    { forceRefresh = false, suppressLoadingUi = false } = {},
  ): Promise<void> {
    if (!state.citationRequestContext || !state.citationRequestContext.message) {
      setCitationsStatus("Realiza una consulta para habilitar normativa.");
      return;
    }
    const cacheKey = buildCitationRequestCacheKey(state.citationRequestContext);
    if (!forceRefresh && cacheKey && state.deferredCitationsCacheKey === cacheKey && state.deferredCitationsCache.length > 0) {
      applyNormativeSupportView({
        citations: state.deferredCitationsCache,
        placeholderText: "",
        statusText: `Mostrando ${state.deferredCitationsCache.length} referencias de normativa cargadas bajo demanda.`,
        canLoadOnDemand: Boolean(state.citationRequestContext),
        displaySource: "cache_hit",
        displayDetails: { mode: "cache_hit" },
      });
      return;
    }
    if (!suppressLoadingUi && citationsLoadBtn) {
      citationsLoadBtn.disabled = true;
      citationsLoadBtn.textContent = "Buscando...";
    }
    if (!suppressLoadingUi) {
      setCitationsStatus("Buscando normativa en el repositorio experto...");
      renderDeferredCitationsState("Buscando normativa en el repositorio experto...", { loading: true });
    }
    try {
      let citations = filterCitedOnly(
        filterNormativeHelperBaseCitations(
          suppressLoadingUi
            ? await fetchNormativeCitationsOnDemand(state.citationRequestContext)
            : await withThinkingWheel(async () => fetchNormativeCitationsOnDemand(state.citationRequestContext)),
        ),
      );
      // Guard: context was cleared (e.g. "Borrar conversaciones") while fetch was in-flight
      if (!state.citationRequestContext) return;
      if (citations.length === 0 && state.deferredCitationsFallback.length > 0) {
        citations = asCitationArray(state.deferredCitationsFallback);
        state.deferredCitationsStatusText = `Mostrando ${citations.length} referencias de normativa del turno (fallback).`;
      } else {
        state.deferredCitationsStatusText = suppressLoadingUi
          ? `Mostrando ${citations.length} referencias normativas detectadas en este turno.`
          : `Mostrando ${citations.length} referencias de normativa cargadas bajo demanda.`;
      }
      state.deferredCitationsFallback = asCitationArray(citations);
      state.deferredCitationsCache = mergeCitations(citations, state.deferredMentionCitations);
      state.deferredCitationsCacheKey = cacheKey;
      applyNormativeSupportView({
        citations: state.deferredCitationsCache,
        placeholderText: "",
        statusText: state.deferredCitationsStatusText,
        canLoadOnDemand: Boolean(state.citationRequestContext),
        displaySource: suppressLoadingUi ? "auto_reconcile" : "on_demand",
        displayDetails: { mode: suppressLoadingUi ? "auto_reconcile" : "on_demand" },
      });
      persistActiveSessionSnapshot?.();
    } catch (error) {
      if (suppressLoadingUi || !state.citationRequestContext) return;
      if (state.deferredCitationsFallback.length > 0) {
        state.deferredCitationsCache = mergeCitations(state.deferredCitationsFallback, state.deferredMentionCitations);
        state.deferredCitationsCacheKey = cacheKey;
        applyNormativeSupportView({
          citations: state.deferredCitationsCache,
          placeholderText: "",
          statusText: `No fue posible refrescar normativa (${error}). Se muestran ${state.deferredCitationsCache.length} referencias disponibles.`,
          canLoadOnDemand: Boolean(state.citationRequestContext),
          displaySource: "fallback", displayStatus: "fallback",
          displayDetails: { mode: "fallback" },
        });
        persistActiveSessionSnapshot?.();
      } else if (state.deferredMentionCitations.length > 0) {
        state.deferredCitationsCache = asCitationArray(state.deferredMentionCitations);
        state.deferredCitationsCacheKey = cacheKey;
        applyNormativeSupportView({
          citations: state.deferredCitationsCache,
          placeholderText: "",
          statusText: `No fue posible refrescar normativa (${error}). Se muestran ${state.deferredCitationsCache.length} menciones detectadas.`,
          canLoadOnDemand: Boolean(state.citationRequestContext),
          displaySource: "mentions_only", displayStatus: "fallback",
          displayDetails: { mode: "mentions_only" },
        });
        persistActiveSessionSnapshot?.();
      } else {
        clearNormativeSupportState({
          placeholderText: `Error cargando normativa: ${error}`,
          statusText: "Error al cargar normativa bajo demanda.",
          canLoadOnDemand: Boolean(state.citationRequestContext),
          persistSnapshot: true, resetStoredState: false,
        });
      }
    } finally {
      if (!suppressLoadingUi && citationsLoadBtn) {
        citationsLoadBtn.disabled = !state.citationRequestContext;
        citationsLoadBtn.textContent = "Ver normativa";
      }
    }
  }

  return {
    applyNormativeSupportView,
    clearNormativeSupportState,
    loadCitationsOnDemand,
    resetDeferredCitationsContext,
    restoreNormativeSupportState,
    setDeferredCitationsContext,
    getCurrentNormativeSupportSnapshot: () => buildCurrentNormativeSupportSnapshot(state),
    resetBackgroundNormativeResolve,
  };
}
