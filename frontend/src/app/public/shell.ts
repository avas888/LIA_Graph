import type { I18nRuntime } from "@/shared/i18n";
import { renderChatShell } from "@/app/chat/shell";

/**
 * Public visitor shell.
 *
 * Returns the HTML markup for the no-login `/public` surface as a single
 * string, the same convention `renderChatShell` follows. Reusable molecules
 * (banner + captcha overlay) are NOT inlined here — they live in
 * `frontend/src/shared/ui/molecules/` per `docs/ui/atomic_design_ui_architecture.md`.
 *
 * Two `data-mount` slots are reserved for the molecules:
 *
 *   * `data-mount="public-banner"`         → `createPublicBanner(...)`
 *   * `data-mount="public-captcha-overlay"`→ `createPublicCaptchaOverlay(...)`
 *
 * `frontend/src/app/public/main.ts` builds those molecules and inserts them
 * into the slots after `mountTemplate`.
 *
 * The `.public-mode` scope class is preserved so `frontend/src/styles/public.css`
 * can hide the session drawer, admin tabs, and runtime chrome that the
 * authenticated chat shell renders. The `chat-session-drawer` element is
 * intentionally still present (its DOM ids are required by `chatDom.ts`); the
 * Proxy-wrapped session controller in `chatApp.ts` keeps it inert when
 * `mode === "public"`.
 */
export function renderPublicShell(i18n: I18nRuntime): string {
  return `
    <div class="public-mode public-shell" data-lia-component="public-shell">
      <div data-mount="public-banner"></div>
      <div data-mount="public-captcha-overlay"></div>
      ${renderChatShell(i18n)}
    </div>
  `;
}
