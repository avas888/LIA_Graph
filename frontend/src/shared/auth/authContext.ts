/**
 * Client-side auth context — decoded from the platform access token (JWT).
 *
 * The token is stored in localStorage by the embed exchange flow.
 * For the main chat app (non-embed), the context may be absent — in that
 * case `getAuthContext()` returns a default anonymous context.
 */

import { getApiAccessToken } from "@/shared/api/client";

export interface AuthContext {
  tenantId: string;
  userId: string;
  role: string; // "tenant_user" | "tenant_admin" | "platform_admin"
  activeCompanyId: string;
  integrationId: string;
}

const ANONYMOUS_CONTEXT: AuthContext = {
  tenantId: "",
  userId: "",
  role: "",
  activeCompanyId: "",
  integrationId: "",
};

let _cached: AuthContext | null = null;

/**
 * Decode the base64url-encoded payload section of a JWT.
 * Returns null if the token is malformed.
 */
function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;

    // Base64url → base64 → decode
    let payload = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    // Pad to multiple of 4
    while (payload.length % 4 !== 0) payload += "=";

    const decoded = atob(payload);
    return JSON.parse(decoded) as Record<string, unknown>;
  } catch {
    return null;
  }
}

/**
 * Read the current auth context from the stored access token.
 * Returns anonymous context if no token is present, decoding fails,
 * or the token has expired.
 * Result is cached until `clearAuthContext()` is called.
 */
export function getAuthContext(): AuthContext {
  if (_cached) return _cached;

  const token = getApiAccessToken();
  if (!token) return ANONYMOUS_CONTEXT;

  const claims = decodeJwtPayload(token);
  if (!claims) return ANONYMOUS_CONTEXT;

  // Check token expiration — treat expired tokens as unauthenticated
  const exp = typeof claims.exp === "number" ? claims.exp : 0;
  if (exp > 0 && exp < Math.floor(Date.now() / 1000)) {
    return ANONYMOUS_CONTEXT;
  }

  _cached = {
    tenantId: String(claims.tenant_id ?? ""),
    userId: String(claims.user_id ?? ""),
    role: String(claims.role ?? ""),
    activeCompanyId: String(claims.active_company_id ?? ""),
    integrationId: String(claims.integration_id ?? ""),
  };
  return _cached;
}

/**
 * Clear the cached context — call when the token changes (login/logout).
 */
export function clearAuthContext(): void {
  _cached = null;
  try { localStorage.removeItem("lia_display_name"); } catch { /* noop */ }
}

/**
 * Return the user's display name stored at login, falling back to userId.
 */
export function getDisplayName(): string {
  try {
    const stored = localStorage.getItem("lia_display_name");
    if (stored) return stored;
  } catch { /* noop */ }
  return getAuthContext().userId;
}

/**
 * Whether the current user has admin-level access (can see admin tabs).
 * Requires an explicit admin role — anonymous/unauthenticated users are NOT admins.
 */
export function isAdmin(): boolean {
  const ctx = getAuthContext();
  return ctx.role === "tenant_admin" || ctx.role === "platform_admin";
}

/**
 * Whether a stored token exists but has expired (exp claim in the past).
 * Used by the auth gate to distinguish "no token" from "expired token".
 */
export function isTokenExpired(): boolean {
  const token = getApiAccessToken();
  if (!token) return false;
  const claims = decodeJwtPayload(token);
  if (!claims) return false;
  const exp = typeof claims.exp === "number" ? claims.exp : 0;
  return exp > 0 && exp < Math.floor(Date.now() / 1000);
}

/**
 * Whether auth context is available (user authenticated via embed exchange).
 */
export function isAuthenticated(): boolean {
  const ctx = getAuthContext();
  return ctx.tenantId !== "";
}
