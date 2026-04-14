/**
 * Auth gate — redirects unauthenticated users to /login.
 *
 * Call at the top of every protected entry point. Returns `true` if the
 * user is authenticated and the page should render; `false` if the
 * redirect was triggered and execution should stop.
 */

import { isAuthenticated, isTokenExpired } from "./authContext";
import { clearApiAccessToken } from "@/shared/api/client";

const SESSION_EXPIRED_KEY = "lia_session_expired";

export function requireAuth(): boolean {
  if (isAuthenticated()) return true;

  // Distinguish "token expired" from "never logged in"
  if (isTokenExpired()) {
    clearApiAccessToken();
    try { localStorage.setItem(SESSION_EXPIRED_KEY, "1"); } catch { /* noop */ }
  }

  window.location.href = "/login";
  return false;
}
