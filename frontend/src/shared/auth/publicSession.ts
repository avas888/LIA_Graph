/**
 * Public visitor session storage.
 *
 * Stores the short-lived `public_visitor` JWT in `sessionStorage` so it stays
 * isolated from the long-lived authenticated token in `localStorage`. We
 * deliberately use `sessionStorage` (tab-scoped) so closing the tab clears the
 * token; refreshing keeps it. The persistent identity lives at the IP-hash
 * level on the backend (`public_captcha_passes`), not in browser storage.
 */

const PUBLIC_TOKEN_STORAGE_KEY = "lia_public_access_token";
const PUBLIC_EXPIRES_STORAGE_KEY = "lia_public_expires_at";

export interface PublicSessionPayload {
  token: string;
  expires_at: number;
}

export function setPublicAccessToken(payload: PublicSessionPayload): void {
  if (typeof window === "undefined") return;
  const token = payload.token.trim();
  if (!token) {
    clearPublicAccessToken();
    return;
  }
  window.sessionStorage.setItem(PUBLIC_TOKEN_STORAGE_KEY, token);
  window.sessionStorage.setItem(
    PUBLIC_EXPIRES_STORAGE_KEY,
    String(Math.max(0, Math.floor(payload.expires_at || 0))),
  );
}

export function getPublicAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  const token = window.sessionStorage.getItem(PUBLIC_TOKEN_STORAGE_KEY);
  return token && token.trim() ? token.trim() : null;
}

export function getPublicExpiresAt(): number {
  if (typeof window === "undefined") return 0;
  const raw = window.sessionStorage.getItem(PUBLIC_EXPIRES_STORAGE_KEY);
  const value = Number(raw || 0);
  return Number.isFinite(value) ? value : 0;
}

export function clearPublicAccessToken(): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.removeItem(PUBLIC_TOKEN_STORAGE_KEY);
  window.sessionStorage.removeItem(PUBLIC_EXPIRES_STORAGE_KEY);
}

/**
 * Refresh the public visitor session by hitting `/api/public/session`.
 * Returns true on success, false otherwise. The captcha is skipped because
 * the IP is already in `public_captcha_passes` after the first solve.
 */
export async function refreshPublicSession(): Promise<boolean> {
  try {
    const response = await fetch("/api/public/session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    if (!response.ok) return false;
    const data = (await response.json()) as Partial<PublicSessionPayload> | null;
    if (!data || !data.token) return false;
    setPublicAccessToken({
      token: String(data.token),
      expires_at: Number(data.expires_at || 0),
    });
    return true;
  } catch {
    return false;
  }
}
