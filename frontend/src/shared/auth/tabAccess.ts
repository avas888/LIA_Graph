/**
 * Tab visibility based on user role.
 *
 * User-facing tabs (category "user") are always visible.
 * Admin tabs (category "admin") require tenant_admin or platform_admin role.
 * Unauthenticated users and tenant_user see only user tabs.
 */

import type { BrowserTabConfig } from "@/shared/dom/browserTabs";
import { getAuthContext } from "./authContext";

/**
 * Filter tabs to those visible for the current user's role.
 */
export function getVisibleTabs(allTabs: BrowserTabConfig[]): BrowserTabConfig[] {
  const ctx = getAuthContext();
  if (ctx.role === "platform_admin" || ctx.role === "tenant_admin") {
    return allTabs;
  }
  return allTabs.filter((t) => t.category === "user");
}
