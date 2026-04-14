import {
  migrateLegacyChatSessionStorage,
  readActiveStoredChatSession,
  readStoredChatSessionIndex,
  readStoredChatSessionState,
  setStoredChatSessionActive,
  upsertStoredChatSession,
} from "@/features/chat/persistence";
import {
  getLocalStorage,
  getSessionStorage,
  listStorageKeys,
  readStorageValue,
  removeStorageValue,
  resolveStorage,
  type StorageLike,
  writeStorageValue,
} from "@/shared/browser/storage";

export const CHAT_SESSION_INDEX_KEY = "lia_chat_session_index_v1";
export const CHAT_SESSION_STATE_KEY_PREFIX = "lia_chat_session_state_v1:";
export const WINDOW_CHAT_SESSION_KEY = "lia_chat_window_session_v1";
export const LEGACY_TRANSCRIPT_CACHE_KEY = "lia_chat_transcript_v2";
export const LEGACY_NORMATIVE_SUPPORT_CACHE_KEY = "lia_chat_normative_support_v1";

interface CreateChatSessionStoreOptions {
  localStorage?: StorageLike;
  sessionStorage?: StorageLike;
}

export function createChatSessionStore(options: CreateChatSessionStoreOptions = {}) {
  const localStore = resolveStorage(options.localStorage, getLocalStorage());
  const sessionStore = resolveStorage(options.sessionStorage, getSessionStorage());

  function readSessionIndex() {
    return readStoredChatSessionIndex({
      storage: localStore,
      indexKey: CHAT_SESSION_INDEX_KEY,
      stateKeyPrefix: CHAT_SESSION_STATE_KEY_PREFIX,
    });
  }

  function readSessionState(sessionId: string) {
    return readStoredChatSessionState({
      storage: localStore,
      stateKeyPrefix: CHAT_SESSION_STATE_KEY_PREFIX,
      sessionId,
    });
  }

  function readWindowScopedSessionId(): string {
    return String(readStorageValue(sessionStore, WINDOW_CHAT_SESSION_KEY) || "").trim();
  }

  function writeWindowScopedSessionId(sessionId = ""): void {
    const normalizedSessionId = String(sessionId || "").trim();
    if (!normalizedSessionId) {
      removeStorageValue(sessionStore, WINDOW_CHAT_SESSION_KEY);
      return;
    }
    writeStorageValue(sessionStore, WINDOW_CHAT_SESSION_KEY, normalizedSessionId);
  }

  function readWindowScopedSessionState() {
    const preferredSessionId = readWindowScopedSessionId();
    if (!preferredSessionId) return null;
    const sessionState = readSessionState(preferredSessionId);
    if (sessionState) return sessionState;
    writeWindowScopedSessionId("");
    return null;
  }

  function readActiveSession() {
    return readActiveStoredChatSession({
      storage: localStore,
      indexKey: CHAT_SESSION_INDEX_KEY,
      stateKeyPrefix: CHAT_SESSION_STATE_KEY_PREFIX,
    });
  }

  function setActiveSession(sessionId: string) {
    return setStoredChatSessionActive({
      storage: localStore,
      indexKey: CHAT_SESSION_INDEX_KEY,
      stateKeyPrefix: CHAT_SESSION_STATE_KEY_PREFIX,
      sessionId,
    });
  }

  function persistSession(sessionState: Record<string, unknown>, maxSessions: number, makeActive = true) {
    return upsertStoredChatSession({
      storage: localStore,
      indexKey: CHAT_SESSION_INDEX_KEY,
      stateKeyPrefix: CHAT_SESSION_STATE_KEY_PREFIX,
      maxSessions,
      sessionState,
      makeActive,
    });
  }

  function clearSessionSnapshots(): void {
    const sessionKeys = listStorageKeys(localStore).filter(
      (key) => key === CHAT_SESSION_INDEX_KEY || key.startsWith(CHAT_SESSION_STATE_KEY_PREFIX)
    );
    [...sessionKeys, LEGACY_TRANSCRIPT_CACHE_KEY, LEGACY_NORMATIVE_SUPPORT_CACHE_KEY].forEach((key) => {
      removeStorageValue(localStore, key);
    });
  }

  function migrateLegacySessionStorage(options: {
    legacyAssistantGreetings: Set<string>;
    maxSessions: number;
  }) {
    return migrateLegacyChatSessionStorage({
      storage: localStore,
      indexKey: CHAT_SESSION_INDEX_KEY,
      stateKeyPrefix: CHAT_SESSION_STATE_KEY_PREFIX,
      maxSessions: options.maxSessions,
      transcriptCacheKey: LEGACY_TRANSCRIPT_CACHE_KEY,
      normativeSupportCacheKey: LEGACY_NORMATIVE_SUPPORT_CACHE_KEY,
      legacyAssistantGreetings: options.legacyAssistantGreetings,
    });
  }

  return {
    clearSessionSnapshots,
    localStore,
    migrateLegacySessionStorage,
    readActiveSession,
    readSessionIndex,
    readSessionState,
    readWindowScopedSessionId,
    readWindowScopedSessionState,
    sessionStore,
    setActiveSession,
    writeWindowScopedSessionId,
    persistSession,
  };
}
