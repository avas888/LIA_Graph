// @ts-nocheck

/**
 * Invite page entry point.
 *
 * Like login, this page does NOT call requireAuth() — it must render
 * for unauthenticated users accepting an invite link.
 */

import "@/styles/main.css";
import { createI18n } from "@/shared/i18n";
import { mountInviteApp } from "@/features/auth/inviteApp";

const i18n = createI18n();
const root = document.getElementById("app");
if (root) {
  mountInviteApp(root, { i18n });
}
