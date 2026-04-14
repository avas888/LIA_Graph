export class ApiError<T = unknown> extends Error {
  status: number;
  payload: T | null;

  constructor(message: string, status: number, payload: T | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

const ACCESS_TOKEN_STORAGE_KEY = "lia_platform_access_token";
const PUBLIC_ACCESS_TOKEN_STORAGE_KEY = "lia_public_access_token";

export type ApiClientMode = "platform" | "public";
let apiClientMode: ApiClientMode = "platform";

/**
 * Switch the API client between authenticated and public-visitor mode.
 * Public mode reads tokens from `sessionStorage` (`lia_public_access_token`)
 * and skips the `/login` redirect on 401 — instead it tries one silent
 * `/api/public/session` refresh and reloads `/public` on failure.
 */
export function setApiClientMode(mode: ApiClientMode): void {
  apiClientMode = mode;
}

export function getApiClientMode(): ApiClientMode {
  return apiClientMode;
}

// One-time migration: copy token from sessionStorage → localStorage so
// existing sessions survive the storage switch (sessionStorage is tab-scoped;
// localStorage is shared across tabs).
if (typeof window !== "undefined") {
  const legacy = window.sessionStorage.getItem(ACCESS_TOKEN_STORAGE_KEY);
  if (legacy && !window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)) {
    window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, legacy);
  }
  window.sessionStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
}

function readStoredAccessToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  if (apiClientMode === "public") {
    const token = window.sessionStorage.getItem(PUBLIC_ACCESS_TOKEN_STORAGE_KEY);
    return token && token.trim() ? token.trim() : null;
  }
  const token = window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY);
  return token && token.trim() ? token.trim() : null;
}

function buildHeaders(extraHeaders?: HeadersInit): Headers {
  const headers = new Headers(extraHeaders);
  const token = readStoredAccessToken();
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  return headers;
}

async function readJson<T>(response: Response): Promise<T | null> {
  try {
    return (await response.json()) as T;
  } catch (_error) {
    return null;
  }
}

export function setApiAccessToken(token: string): void {
  if (typeof window === "undefined") {
    return;
  }
  const normalized = token.trim();
  if (!normalized) {
    window.localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
    return;
  }
  window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, normalized);
}

export function clearApiAccessToken(): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
}

export function getApiAccessToken(): string | null {
  return readStoredAccessToken();
}

function handleUnauthorized(status: number): void {
  if (status !== 401 || typeof window === "undefined") return;
  if (apiClientMode === "public") {
    // Public visitors never see the `/login` flow. Try a silent token refresh
    // and only reload `/public` if that fails.
    void (async () => {
      try {
        const response = await fetch("/api/public/session", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({}),
        });
        if (response.ok) {
          const data = (await response.json()) as { token?: string; expires_at?: number } | null;
          if (data && data.token) {
            window.sessionStorage.setItem(PUBLIC_ACCESS_TOKEN_STORAGE_KEY, String(data.token));
            return;
          }
        }
      } catch {
        // fall through
      }
      window.location.href = "/public";
    })();
    return;
  }
  window.localStorage.setItem("lia_session_expired", "1");
  window.localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
  window.location.href = "/login";
}

export async function getJson<T>(url: string): Promise<T> {
  const response = await fetch(url, {
    headers: buildHeaders(),
  });
  const payload = await readJson<T>(response);
  if (!response.ok) {
    handleUnauthorized(response.status);
    const message =
      payload && typeof payload === "object" && "error" in payload ? String((payload as { error?: string }).error || response.statusText) : response.statusText;
    throw new ApiError(message, response.status, payload);
  }
  return payload as T;
}

export async function postJson<TResponse, TBody = unknown>(url: string, body: TBody): Promise<{ response: Response; data: TResponse | null }> {
  const response = await fetch(url, {
    method: "POST",
    headers: buildHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(body),
  });
  if (!response.ok) handleUnauthorized(response.status);
  const data = await readJson<TResponse>(response);
  return { response, data };
}
