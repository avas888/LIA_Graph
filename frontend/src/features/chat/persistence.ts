// @ts-nocheck

import {
  asCitationArray,
  filterCitedOnly,
  filterNormativeHelperBaseCitations,
  mergeCitations,
} from "@/features/chat/citations";

const CHAT_SESSION_STORAGE_VERSION = 2;

export const TOPIC_LABELS: Record<string, string> = {
  declaracion_renta: "Renta",
  renta: "Renta",
  laboral: "Laboral",
  iva: "IVA",
  ica: "ICA",
  facturacion_electronica: "Facturación",
  estados_financieros_niif: "NIIF",
  calendario_obligaciones: "Calendario",
};

export function deriveDetectedTopic(questionEntries) {
  if (!Array.isArray(questionEntries)) return "";
  for (const entry of questionEntries) {
    const topic = String(entry?.effectiveTopic || entry?.effective_topic || "").trim();
    if (topic) return topic;
  }
  return "";
}

export function deriveThreadLabel(firstQuestion, questionEntries) {
  const topic = deriveDetectedTopic(questionEntries);
  if (TOPIC_LABELS[topic]) return TOPIC_LABELS[topic];
  const q = String(firstQuestion || "").trim();
  return q.length > 50 ? q.slice(0, 47) + "..." : q || "Nueva conversación";
}

function safeParseJson(raw, fallback) {
  try {
    return JSON.parse(raw);
  } catch (_error) {
    return fallback;
  }
}

export function normalizeDocsUsed(raw) {
  if (!Array.isArray(raw)) return [];
  const seen = new Set();
  const docs = [];
  raw.forEach((item) => {
    const value = String(item || "").trim();
    if (!value || seen.has(value)) return;
    seen.add(value);
    docs.push(value);
  });
  return docs;
}

export function normalizeLayerContributions(raw) {
  if (!raw || typeof raw !== "object") return {};
  const normalized = {};
  Object.entries(raw).forEach(([key, value]) => {
    const cleanKey = String(key || "").trim();
    const parsed = Number(value);
    if (!cleanKey || !Number.isFinite(parsed)) return;
    normalized[cleanKey] = Math.max(0, Math.trunc(parsed));
  });
  return normalized;
}

export function normalizeFeedbackRatingValue(raw) {
  const parsed = Number(raw);
  if (!Number.isFinite(parsed)) return null;
  const clamped = Math.trunc(parsed);
  if (clamped < 1 || clamped > 5) return null;
  return clamped;
}

export function normalizeAssistantMeta(raw) {
  if (!raw || typeof raw !== "object") return null;
  return {
    trace_id: String(raw.trace_id || "").trim(),
    chat_run_id: String(raw.chat_run_id || "").trim(),
    session_id: String(raw.session_id || "").trim(),
    requested_topic: String(raw.requested_topic || "").trim(),
    effective_topic: String(raw.effective_topic || raw.topic || "").trim(),
    topic_adjusted: Boolean(raw.topic_adjusted),
    pais: String(raw.pais || "").trim(),
    docs_used: normalizeDocsUsed(raw.docs_used),
    layer_contributions: normalizeLayerContributions(raw.layer_contributions),
    pain_detected: String(raw.pain_detected || "").trim(),
    task_detected: String(raw.task_detected || "").trim(),
    feedback_rating: normalizeFeedbackRatingValue(raw.feedback_rating),
    question_text: String(raw.question_text || "").trim(),
    response_route: String(raw.response_route || "").trim(),
    coverage_notice: String(raw.coverage_notice || "").trim(),
  };
}

export function normalizeTranscriptEntry(raw) {
  if (!raw || typeof raw !== "object") return null;
  const role = raw.role === "assistant" ? "assistant" : raw.role === "user" ? "user" : "";
  const text = String(raw.text || "");
  if (!role || !text.trim()) return null;
  return {
    role,
    text,
    timestamp: typeof raw.timestamp === "string" && raw.timestamp ? raw.timestamp : null,
    meta: role === "assistant" ? normalizeAssistantMeta(raw.meta || {}) : null,
  };
}

export function normalizeTokenTotals(raw) {
  const payload = raw && typeof raw === "object" ? raw : {};
  const inputTokens = Number(payload.input_tokens || 0);
  const outputTokens = Number(payload.output_tokens || 0);
  const totalTokens = Number(payload.total_tokens || inputTokens + outputTokens);
  return {
    input_tokens: Number.isFinite(inputTokens) ? Math.max(0, Math.trunc(inputTokens)) : 0,
    output_tokens: Number.isFinite(outputTokens) ? Math.max(0, Math.trunc(outputTokens)) : 0,
    total_tokens: Number.isFinite(totalTokens) ? Math.max(0, Math.trunc(totalTokens)) : 0,
  };
}

function normalizeSessionId(raw) {
  return String(raw || "").trim();
}

function nowIso() {
  return new Date().toISOString();
}

function normalizeQuestionId(raw) {
  return String(raw || "").trim();
}

function buildSessionStateStorageKey(stateKeyPrefix, sessionId) {
  return `${String(stateKeyPrefix || "").trim()}${normalizeSessionId(sessionId)}`;
}

function readStorageJson(storage, key, fallback) {
  try {
    return safeParseJson(storage?.getItem(key), fallback);
  } catch (_error) {
    return fallback;
  }
}

function writeStorageJson(storage, key, value) {
  try {
    storage?.setItem(key, JSON.stringify(value));
  } catch (_error) {
    // Ignore storage failures.
  }
}

function removeStorageKey(storage, key) {
  try {
    storage?.removeItem(key);
  } catch (_error) {
    // Ignore storage failures.
  }
}

export function readTranscriptCache({
  storage,
  cacheKey,
  limit,
  legacyAssistantGreetings,
}) {
  try {
    const raw = storage?.getItem(cacheKey);
    if (!raw) return [];
    const parsed = safeParseJson(raw, []);
    if (!Array.isArray(parsed)) return [];
    return parsed
      .map((entry) => normalizeTranscriptEntry(entry))
      .filter((entry) => {
        if (!entry) return false;
        if (entry.role !== "assistant") return true;
        const text = String(entry.text || "").trim();
        if (!text) return false;
        return !legacyAssistantGreetings.has(text);
      })
      .slice(-limit);
  } catch (_error) {
    return [];
  }
}

export function writeTranscriptCache({
  storage,
  cacheKey,
  entries,
  limit,
}) {
  const safeEntries = Array.isArray(entries) ? entries.slice(-limit) : [];
  try {
    storage?.setItem(cacheKey, JSON.stringify(safeEntries));
  } catch (_error) {
    // Ignore storage failures.
  }
  return safeEntries;
}

export function persistTranscriptEntry({
  storage,
  cacheKey,
  entries,
  entry,
  limit,
}) {
  const normalized = normalizeTranscriptEntry(entry);
  if (!normalized) return Array.isArray(entries) ? entries : [];
  return writeTranscriptCache({
    storage,
    cacheKey,
    entries: [...(Array.isArray(entries) ? entries : []), normalized],
    limit,
  });
}

export function updateTranscriptFeedbackByTraceId(entries, traceId, rating) {
  const trace = String(traceId || "").trim();
  if (!trace || !Array.isArray(entries)) return Array.isArray(entries) ? entries : [];
  for (let i = entries.length - 1; i >= 0; i -= 1) {
    const row = entries[i];
    if (!row || row.role !== "assistant" || !row.meta) continue;
    if (String(row.meta.trace_id || "").trim() !== trace) continue;
    const nextRow = {
      ...row,
      meta: {
        ...row.meta,
        feedback_rating: Number.isFinite(Number(rating)) ? Math.max(1, Math.min(5, Math.trunc(Number(rating)))) : null,
      },
    };
    const nextEntries = [...entries];
    nextEntries[i] = nextRow;
    return nextEntries;
  }
  return entries;
}

export function normalizeCitationRequestContext(raw) {
  if (!raw || typeof raw !== "object") return null;
  const normalized = {
    trace_id: String(raw.trace_id || "").trim(),
    message: String(raw.message || "").trim(),
    assistant_answer: String(raw.assistant_answer || "").trim(),
    topic: String(raw.topic || "").trim(),
    pais: String(raw.pais || "").trim(),
    primary_scope_mode: String(raw.primary_scope_mode || "").trim(),
  };
  if (!normalized.message) return null;
  return normalized;
}

export function normalizeNormativeSupportCache(raw) {
  if (!raw || typeof raw !== "object") return null;
  const citationRequestContext = normalizeCitationRequestContext(raw.citationRequestContext);
  const fallbackCitations = filterCitedOnly(filterNormativeHelperBaseCitations(raw.fallbackCitations));
  const mentionCitations = asCitationArray(raw.mentionCitations);
  const mergedCachedCitations = mergeCitations(asCitationArray(raw.cachedCitations), mentionCitations);
  const cachedCitations =
    mergedCachedCitations.length > 0
      ? mergedCachedCitations
      : mergeCitations(fallbackCitations, mentionCitations);
  const statusText = String(raw.statusText || raw.status_text || "").trim();
  const placeholderText = String(raw.placeholderText || raw.placeholder_text || "").trim();
  if (
    !citationRequestContext &&
    fallbackCitations.length === 0 &&
    mentionCitations.length === 0 &&
    cachedCitations.length === 0 &&
    !statusText &&
    !placeholderText
  ) {
    return null;
  }
  return {
    citationRequestContext,
    fallbackCitations,
    mentionCitations,
    cachedCitations,
    statusText,
    placeholderText,
  };
}

export function normalizeExpertPanelLoadOptions(raw) {
  if (!raw || typeof raw !== "object") return null;
  const traceId = String(raw.traceId || raw.trace_id || "").trim();
  const message = String(raw.message || "").trim();
  const assistantAnswer = String(raw.assistantAnswer || raw.assistant_answer || "").trim();
  const normativeArticleRefs = Array.isArray(raw.normativeArticleRefs || raw.normative_article_refs)
    ? Array.from(
        new Set(
          (raw.normativeArticleRefs || raw.normative_article_refs)
            .map((value) => String(value || "").trim())
            .filter(Boolean)
        )
      )
    : [];
  const searchSeed = String(raw.searchSeed || raw.search_seed || "").trim();
  const searchSeedOrigin = String(raw.searchSeedOrigin || raw.search_seed_origin || "").trim();
  const topic = String(raw.topic || "").trim();
  const pais = String(raw.pais || "").trim();
  if (
    !traceId &&
    !message &&
    !assistantAnswer &&
    normativeArticleRefs.length === 0 &&
    !searchSeed &&
    !searchSeedOrigin &&
    !topic &&
    !pais
  ) {
    return null;
  }
  return {
    traceId,
    message,
    assistantAnswer,
    normativeArticleRefs,
    searchSeed,
    searchSeedOrigin,
    topic,
    pais,
  };
}

export function normalizeExpertPanelResponse(raw) {
  if (!raw || typeof raw !== "object") return null;
  const groups = Array.isArray(raw.groups) ? raw.groups : [];
  const ungrouped = Array.isArray(raw.ungrouped) ? raw.ungrouped : [];
  const diagnostics =
    raw.retrieval_diagnostics && typeof raw.retrieval_diagnostics === "object" ? raw.retrieval_diagnostics : undefined;
  if (groups.length === 0 && ungrouped.length === 0 && !raw.ok) {
    return null;
  }
  return {
    ok: Boolean(raw.ok),
    groups,
    ungrouped,
    total_available: Number.isFinite(Number(raw.total_available)) ? Math.max(0, Math.trunc(Number(raw.total_available))) : undefined,
    has_more: typeof raw.has_more === "boolean" ? raw.has_more : undefined,
    retrieval_diagnostics: diagnostics,
    trace_id: String(raw.trace_id || "").trim(),
  };
}

function normalizeExpertPanelEnhancements(raw) {
  if (!raw || typeof raw !== "object") return null;
  const result: Record<string, { posibleRelevancia: string | null; resumenNutshell: string | null }> = {};
  for (const [cardId, value] of Object.entries(raw)) {
    if (!cardId || !value || typeof value !== "object") continue;
    const v = value as Record<string, unknown>;
    const posibleRelevancia = String(v.posibleRelevancia || "").trim() || null;
    const resumenNutshell = String(v.resumenNutshell || "").trim() || null;
    if (posibleRelevancia || resumenNutshell) {
      result[cardId] = { posibleRelevancia, resumenNutshell };
    }
  }
  return Object.keys(result).length > 0 ? result : null;
}

export function normalizeExpertPanelState(raw) {
  if (!raw || typeof raw !== "object") return null;
  const statusRaw = String(raw.status || "").trim().toLowerCase();
  const status = ["idle", "loading", "empty", "error", "populated"].includes(statusRaw) ? statusRaw : "";
  const loadOptions = normalizeExpertPanelLoadOptions(raw.loadOptions || raw.load_options);
  const response = normalizeExpertPanelResponse(raw.response);
  if (!status && !loadOptions && !response) return null;
  if (status === "populated" && !response) return null;
  const enhancements = normalizeExpertPanelEnhancements(raw.enhancements);
  return {
    status: status || (response ? "populated" : "idle"),
    loadOptions,
    response,
    enhancements,
  };
}

export function readNormativeSupportCache({
  storage,
  cacheKey,
}) {
  try {
    const raw = storage?.getItem(cacheKey);
    if (!raw) return null;
    const parsed = safeParseJson(raw, null);
    return normalizeNormativeSupportCache(parsed);
  } catch (_error) {
    return null;
  }
}

export function writeNormativeSupportCache({
  storage,
  cacheKey,
  payload,
}) {
  const normalized = normalizeNormativeSupportCache(payload);
  if (!normalized || !normalized.citationRequestContext) {
    try {
      storage?.removeItem(cacheKey);
    } catch (_error) {
      // Ignore storage failures.
    }
    return null;
  }
  try {
    storage?.setItem(cacheKey, JSON.stringify(normalized));
  } catch (_error) {
    // Ignore storage failures.
  }
  return normalized;
}

export function deriveFirstQuestionFromTranscriptEntries(entries) {
  if (!Array.isArray(entries)) return "";
  for (const entry of entries) {
    if (!entry || entry.role !== "user") continue;
    const question = String(entry.text || "").trim();
    if (question) return question;
  }
  return "";
}

function deriveLastTranscriptText(entries, role) {
  if (!Array.isArray(entries)) return "";
  for (let index = entries.length - 1; index >= 0; index -= 1) {
    const entry = entries[index];
    if (!entry || entry.role !== role) continue;
    const text = String(entry.text || "").trim();
    if (text) return text;
  }
  return "";
}

function findLatestAssistantTraceId(entries) {
  if (!Array.isArray(entries)) return "";
  for (let index = entries.length - 1; index >= 0; index -= 1) {
    const entry = entries[index];
    if (!entry || entry.role !== "assistant" || !entry.meta) continue;
    const traceId = String(entry.meta.trace_id || "").trim();
    if (traceId) return traceId;
  }
  return "";
}

function findSessionIdFromTranscriptEntries(entries) {
  if (!Array.isArray(entries)) return "";
  for (let index = entries.length - 1; index >= 0; index -= 1) {
    const entry = entries[index];
    if (!entry || entry.role !== "assistant" || !entry.meta) continue;
    const sessionId = normalizeSessionId(entry.meta.session_id);
    if (sessionId) return sessionId;
  }
  return "";
}

function buildDerivedQuestionEntries(transcriptEntries) {
  if (!Array.isArray(transcriptEntries)) return [];
  const derivedEntries = [];
  let pendingUserIndex = -1;
  let pendingQuestionText = "";

  transcriptEntries.forEach((entry, index) => {
    if (!entry) return;
    if (entry.role === "user") {
      pendingUserIndex = index;
      pendingQuestionText = String(entry.text || "").trim();
      return;
    }
    if (entry.role !== "assistant" || pendingUserIndex < 0) return;
    const traceId = String(entry.meta?.trace_id || "").trim();
    derivedEntries.push({
      questionId: normalizeQuestionId(traceId || `question_${pendingUserIndex}_${index}`),
      questionText: pendingQuestionText,
      userTranscriptIndex: pendingUserIndex,
      assistantTranscriptIndex: index,
      traceId,
      effectiveTopic: String(entry.meta?.effective_topic || "").trim(),
      pais: String(entry.meta?.pais || "").trim(),
      normativeSupport: null,
      expertPanelState: null,
      updatedAt: nowIso(),
    });
    pendingUserIndex = -1;
    pendingQuestionText = "";
  });

  return derivedEntries;
}

function normalizeStoredQuestionEntry(raw, transcriptEntries) {
  if (!raw || typeof raw !== "object" || !Array.isArray(transcriptEntries)) return null;
  const userTranscriptIndex = Number.parseInt(String(raw.userTranscriptIndex ?? raw.user_transcript_index ?? ""), 10);
  const assistantTranscriptIndex = Number.parseInt(
    String(raw.assistantTranscriptIndex ?? raw.assistant_transcript_index ?? ""),
    10
  );
  if (!Number.isInteger(userTranscriptIndex) || !Number.isInteger(assistantTranscriptIndex)) return null;
  if (userTranscriptIndex < 0 || assistantTranscriptIndex < 0) return null;
  const userEntry = transcriptEntries[userTranscriptIndex];
  const assistantEntry = transcriptEntries[assistantTranscriptIndex];
  if (!userEntry || userEntry.role !== "user" || !assistantEntry || assistantEntry.role !== "assistant") {
    return null;
  }

  const traceId = String(raw.traceId || raw.trace_id || assistantEntry.meta?.trace_id || "").trim();
  const questionId = normalizeQuestionId(raw.questionId || raw.question_id || traceId || `question_${userTranscriptIndex}_${assistantTranscriptIndex}`);
  if (!questionId) return null;

  return {
    questionId,
    questionText: String(raw.questionText || raw.question_text || userEntry.text || "").trim(),
    userTranscriptIndex,
    assistantTranscriptIndex,
    traceId,
    effectiveTopic: String(raw.effectiveTopic || raw.effective_topic || assistantEntry.meta?.effective_topic || "").trim(),
    pais: String(raw.pais || assistantEntry.meta?.pais || "").trim(),
    normativeSupport: normalizeNormativeSupportCache(raw.normativeSupport || raw.normative_support),
    expertPanelState: normalizeExpertPanelState(raw.expertPanelState || raw.expert_panel_state),
    updatedAt: String(raw.updatedAt || raw.updated_at || "").trim() || nowIso(),
  };
}

function normalizeQuestionEntries(rawEntries, transcriptEntries) {
  const derivedEntries = buildDerivedQuestionEntries(transcriptEntries);
  if (derivedEntries.length === 0) return [];

  const normalizedRawEntries = Array.isArray(rawEntries)
    ? rawEntries.map((entry) => normalizeStoredQuestionEntry(entry, transcriptEntries)).filter(Boolean)
    : [];

  return derivedEntries.map((derivedEntry) => {
    const matchedRawEntry =
      normalizedRawEntries.find((entry) => entry.questionId === derivedEntry.questionId) ||
      normalizedRawEntries.find(
        (entry) =>
          entry.traceId &&
          derivedEntry.traceId &&
          entry.traceId === derivedEntry.traceId
      ) ||
      normalizedRawEntries.find(
        (entry) =>
          entry.userTranscriptIndex === derivedEntry.userTranscriptIndex &&
          entry.assistantTranscriptIndex === derivedEntry.assistantTranscriptIndex
      );

    return {
      ...derivedEntry,
      questionId: normalizeQuestionId(matchedRawEntry?.questionId || derivedEntry.questionId),
      questionText: String(matchedRawEntry?.questionText || derivedEntry.questionText || "").trim(),
      traceId: String(matchedRawEntry?.traceId || derivedEntry.traceId || "").trim(),
      effectiveTopic: String(matchedRawEntry?.effectiveTopic || derivedEntry.effectiveTopic || "").trim(),
      pais: String(matchedRawEntry?.pais || derivedEntry.pais || "").trim(),
      normativeSupport: normalizeNormativeSupportCache(matchedRawEntry?.normativeSupport) || null,
      expertPanelState: normalizeExpertPanelState(matchedRawEntry?.expertPanelState) || null,
      updatedAt: String(matchedRawEntry?.updatedAt || derivedEntry.updatedAt || "").trim() || nowIso(),
    };
  });
}

function normalizeStoredChatSessionSummary(raw) {
  if (!raw || typeof raw !== "object") return null;
  const sessionId = normalizeSessionId(raw.sessionId || raw.session_id);
  if (!sessionId) return null;
  return {
    sessionId,
    firstQuestion: String(raw.firstQuestion || raw.first_question || "").trim(),
    updatedAt: String(raw.updatedAt || raw.updated_at || "").trim() || nowIso(),
    threadLabel: String(raw.threadLabel || raw.thread_label || "").trim(),
    detectedTopic: String(raw.detectedTopic || raw.detected_topic || "").trim(),
    questionCount: Number(raw.questionCount || raw.question_count || 0),
  };
}

function sortStoredChatSessionSummaries(items) {
  return [...items].sort((left, right) =>
    String(right.updatedAt || "").localeCompare(String(left.updatedAt || ""))
  );
}

export function normalizeStoredChatSessionState(raw) {
  if (!raw || typeof raw !== "object") return null;
  const sessionId = normalizeSessionId(raw.sessionId || raw.session_id);
  if (!sessionId) return null;

  const transcriptEntries = Array.isArray(raw.transcriptEntries || raw.transcript_entries)
    ? (raw.transcriptEntries || raw.transcript_entries)
        .map((entry) => normalizeTranscriptEntry(entry))
        .filter(Boolean)
    : [];
  if (transcriptEntries.length === 0) return null;

  const firstQuestion =
    String(raw.firstQuestion || raw.first_question || "").trim() ||
    deriveFirstQuestionFromTranscriptEntries(transcriptEntries);
  const sessionNormativeSupport = normalizeNormativeSupportCache(raw.normativeSupport || raw.normative_support);
  const questionEntries = normalizeQuestionEntries(raw.questionEntries || raw.question_entries, transcriptEntries).map(
    (entry, index, items) => {
      if (entry.normativeSupport || !sessionNormativeSupport || index !== items.length - 1) {
        return entry;
      }
      return {
        ...entry,
        normativeSupport: sessionNormativeSupport,
      };
    }
  );
  const latestQuestionId = questionEntries[questionEntries.length - 1]?.questionId || "";
  const requestedActiveQuestionId = normalizeQuestionId(raw.activeQuestionId || raw.active_question_id);
  const activeQuestionId = questionEntries.some((entry) => entry.questionId === requestedActiveQuestionId)
    ? requestedActiveQuestionId
    : latestQuestionId;

  return {
    version: CHAT_SESSION_STORAGE_VERSION,
    sessionId,
    tenantId: String(raw.tenantId || raw.tenant_id || "").trim() || undefined,
    firstQuestion,
    updatedAt: String(raw.updatedAt || raw.updated_at || "").trim() || nowIso(),
    transcriptEntries,
    questionEntries,
    activeQuestionId,
    normativeSupport: sessionNormativeSupport,
    conversationTokenTotals: normalizeTokenTotals(raw.conversationTokenTotals || raw.conversation_token_totals),
    lastUserMessage: String(raw.lastUserMessage || raw.last_user_message || "").trim(),
    lastSubmittedUserMessage: String(raw.lastSubmittedUserMessage || raw.last_submitted_user_message || "").trim(),
    lastAssistantAnswerMarkdown: String(
      raw.lastAssistantAnswerMarkdown || raw.last_assistant_answer_markdown || ""
    ).trim(),
    detectedTopic: deriveDetectedTopic(questionEntries),
    threadLabel: deriveThreadLabel(firstQuestion, questionEntries),
  };
}

export function normalizeStoredChatSessionIndex(raw) {
  const payload = raw && typeof raw === "object" ? raw : {};
  const seen = new Set();
  const sessions = sortStoredChatSessionSummaries(
    Array.isArray(payload.sessions)
      ? payload.sessions
          .map((item) => normalizeStoredChatSessionSummary(item))
          .filter((item) => {
            if (!item || seen.has(item.sessionId)) return false;
            seen.add(item.sessionId);
            return true;
          })
      : []
  );
  return {
    version: CHAT_SESSION_STORAGE_VERSION,
    activeSessionId: normalizeSessionId(payload.activeSessionId || payload.active_session_id),
    sessions,
  };
}

function writeStoredChatSessionIndex({
  storage,
  indexKey,
  index,
}) {
  const normalized = normalizeStoredChatSessionIndex(index);
  writeStorageJson(storage, indexKey, normalized);
  return normalized;
}

function removeStoredChatSessionState({
  storage,
  stateKeyPrefix,
  sessionId,
}) {
  const normalizedSessionId = normalizeSessionId(sessionId);
  if (!normalizedSessionId) return;
  removeStorageKey(storage, buildSessionStateStorageKey(stateKeyPrefix, normalizedSessionId));
}

export function readStoredChatSessionState({
  storage,
  stateKeyPrefix,
  sessionId,
}) {
  const normalizedSessionId = normalizeSessionId(sessionId);
  if (!normalizedSessionId) return null;
  const key = buildSessionStateStorageKey(stateKeyPrefix, normalizedSessionId);
  const parsed = readStorageJson(storage, key, null);
  const normalized = normalizeStoredChatSessionState(parsed);
  if (normalized) return normalized;
  removeStorageKey(storage, key);
  return null;
}

function writeStoredChatSessionState({
  storage,
  stateKeyPrefix,
  sessionState,
}) {
  const normalized = normalizeStoredChatSessionState(sessionState);
  if (!normalized) return null;
  writeStorageJson(storage, buildSessionStateStorageKey(stateKeyPrefix, normalized.sessionId), normalized);
  return normalized;
}

export function readStoredChatSessionIndex({
  storage,
  indexKey,
  stateKeyPrefix,
}) {
  const normalized = normalizeStoredChatSessionIndex(readStorageJson(storage, indexKey, null));
  const sessions = [];
  const seen = new Set();

  normalized.sessions.forEach((summary) => {
    if (seen.has(summary.sessionId)) return;
    const state = readStoredChatSessionState({
      storage,
      stateKeyPrefix,
      sessionId: summary.sessionId,
    });
    if (!state) return;
    seen.add(summary.sessionId);
    sessions.push({
      sessionId: state.sessionId,
      firstQuestion: state.firstQuestion || summary.firstQuestion,
      updatedAt: state.updatedAt || summary.updatedAt || nowIso(),
      threadLabel: state.threadLabel || summary.threadLabel || "",
      detectedTopic: state.detectedTopic || summary.detectedTopic || "",
      questionCount: Array.isArray(state.questionEntries) ? state.questionEntries.length : (summary.questionCount || 0),
    });
  });

  const repairedSessions = sortStoredChatSessionSummaries(sessions);
  const activeSessionId = normalized.activeSessionId
    ? repairedSessions.some((item) => item.sessionId === normalized.activeSessionId)
      ? normalized.activeSessionId
      : repairedSessions[0]?.sessionId || ""
    : "";

  const repaired = {
    version: CHAT_SESSION_STORAGE_VERSION,
    activeSessionId,
    sessions: repairedSessions,
  };

  if (
    repaired.activeSessionId !== normalized.activeSessionId ||
    repaired.sessions.length !== normalized.sessions.length ||
    repaired.sessions.some((item, index) => {
      const current = normalized.sessions[index];
      return !current || current.sessionId !== item.sessionId || current.updatedAt !== item.updatedAt;
    })
  ) {
    writeStoredChatSessionIndex({
      storage,
      indexKey,
      index: repaired,
    });
  }

  return repaired;
}

export function readActiveStoredChatSession({
  storage,
  indexKey,
  stateKeyPrefix,
}) {
  const index = readStoredChatSessionIndex({
    storage,
    indexKey,
    stateKeyPrefix,
  });
  if (!index.activeSessionId) return null;
  return readStoredChatSessionState({
    storage,
    stateKeyPrefix,
    sessionId: index.activeSessionId,
  });
}

export function setStoredChatSessionActive({
  storage,
  indexKey,
  stateKeyPrefix,
  sessionId,
}) {
  const index = readStoredChatSessionIndex({
    storage,
    indexKey,
    stateKeyPrefix,
  });
  const normalizedSessionId = normalizeSessionId(sessionId);
  const nextActiveSessionId =
    normalizedSessionId && index.sessions.some((item) => item.sessionId === normalizedSessionId)
      ? normalizedSessionId
      : "";

  return writeStoredChatSessionIndex({
    storage,
    indexKey,
    index: {
      ...index,
      activeSessionId: nextActiveSessionId,
    },
  });
}

export function upsertStoredChatSession({
  storage,
  indexKey,
  stateKeyPrefix,
  maxSessions,
  sessionState,
  makeActive = true,
}) {
  const normalizedState = writeStoredChatSessionState({
    storage,
    stateKeyPrefix,
    sessionState: {
      ...sessionState,
      updatedAt: nowIso(),
    },
  });
  if (!normalizedState) return null;

  const currentIndex = readStoredChatSessionIndex({
    storage,
    indexKey,
    stateKeyPrefix,
  });

  const nextSessions = sortStoredChatSessionSummaries([
    {
      sessionId: normalizedState.sessionId,
      firstQuestion: normalizedState.firstQuestion,
      updatedAt: normalizedState.updatedAt,
      threadLabel: normalizedState.threadLabel || "",
      detectedTopic: normalizedState.detectedTopic || "",
      questionCount: Array.isArray(normalizedState.questionEntries) ? normalizedState.questionEntries.length : 0,
    },
    ...currentIndex.sessions.filter((item) => item.sessionId !== normalizedState.sessionId),
  ]);

  const limit = Math.max(1, Math.trunc(Number(maxSessions) || 0));
  const keptSessions = nextSessions.slice(0, limit);
  const evictedSessions = nextSessions.slice(limit);
  evictedSessions.forEach((item) => {
    removeStoredChatSessionState({
      storage,
      stateKeyPrefix,
      sessionId: item.sessionId,
    });
  });

  const index = writeStoredChatSessionIndex({
    storage,
    indexKey,
    index: {
      version: CHAT_SESSION_STORAGE_VERSION,
      activeSessionId: makeActive ? normalizedState.sessionId : currentIndex.activeSessionId,
      sessions: keptSessions,
    },
  });

  return {
    index,
    sessionState: normalizedState,
  };
}

export function migrateLegacyChatSessionStorage({
  storage,
  indexKey,
  stateKeyPrefix,
  maxSessions,
  transcriptCacheKey,
  normativeSupportCacheKey,
  legacyAssistantGreetings,
}) {
  const transcriptEntries = readTranscriptCache({
    storage,
    cacheKey: transcriptCacheKey,
    limit: 60,
    legacyAssistantGreetings,
  });
  if (transcriptEntries.length === 0) return null;

  const sessionId = findSessionIdFromTranscriptEntries(transcriptEntries);
  if (!sessionId) return null;

  const migrated = upsertStoredChatSession({
    storage,
    indexKey,
    stateKeyPrefix,
    maxSessions,
    sessionState: {
      version: CHAT_SESSION_STORAGE_VERSION,
      sessionId,
      firstQuestion: deriveFirstQuestionFromTranscriptEntries(transcriptEntries),
      transcriptEntries,
      normativeSupport: readNormativeSupportCache({
        storage,
        cacheKey: normativeSupportCacheKey,
      }),
      conversationTokenTotals: normalizeTokenTotals(null),
      lastUserMessage: deriveLastTranscriptText(transcriptEntries, "user"),
      lastSubmittedUserMessage: deriveLastTranscriptText(transcriptEntries, "user"),
      lastAssistantAnswerMarkdown: deriveLastTranscriptText(transcriptEntries, "assistant"),
      activeQuestionId: "",
    },
    makeActive: true,
  });

  if (!migrated) return null;

  removeStorageKey(storage, transcriptCacheKey);
  removeStorageKey(storage, normativeSupportCacheKey);
  return migrated.sessionState.sessionId;
}
// @ts-nocheck
