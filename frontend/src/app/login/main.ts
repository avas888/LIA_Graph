// @ts-nocheck

/**
 * Login page entry point.
 *
 * This page does NOT call requireAuth() — it must render for
 * unauthenticated users (it IS the auth gate destination).
 */

import "@/styles/main.css";
import { createI18n } from "@/shared/i18n";
import { mountLoginApp } from "@/features/auth/loginApp";

const i18n = createI18n();
const root = document.getElementById("app");
if (root) {
  mountLoginApp(root, { i18n });
}
