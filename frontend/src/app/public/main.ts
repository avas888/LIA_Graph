import "@/styles/main.css";
import "@/styles/public.css";
import { mountChatApp } from "@/features/chat/chatApp";
import { createPageContext } from "@/shared/app/bootstrap";
import { setApiClientMode } from "@/shared/api/client";
import {
  clearPublicAccessToken,
  getPublicAccessToken,
  refreshPublicSession,
  setPublicAccessToken,
} from "@/shared/auth/publicSession";
import { renderPublicShell } from "@/app/public/shell";
import { createPublicBanner } from "@/shared/ui/molecules/publicBanner";
import {
  createPublicCaptchaOverlay,
  type PublicCaptchaOverlayHandle,
} from "@/shared/ui/molecules/publicCaptchaOverlay";
import { isMobile } from "@/app/mobile/detectMobile";
import { queryRequired } from "@/shared/dom/template";

declare global {
  interface Window {
    turnstile?: {
      render: (
        container: HTMLElement | string,
        options: {
          sitekey: string;
          callback: (token: string) => void;
          "error-callback"?: () => void;
          theme?: "light" | "dark" | "auto";
        },
      ) => string;
      reset: (widgetId?: string) => void;
    };
  }
}

interface PublicBootHints {
  token: string;
  expiresAt: number;
  captchaRequired: boolean;
  turnstileSiteKey: string;
}

function readMetaContent(name: string): string {
  const node = document.head.querySelector(`meta[name="${name}"]`);
  return node?.getAttribute("content")?.trim() ?? "";
}

function readBootHints(): PublicBootHints {
  return {
    token: readMetaContent("lia-public-token"),
    expiresAt: Number(readMetaContent("lia-public-expires-at") || 0) || 0,
    captchaRequired: readMetaContent("lia-public-captcha-required") === "true",
    turnstileSiteKey: readMetaContent("lia-public-turnstile-site-key"),
  };
}

async function postSession(turnstileToken?: string): Promise<{ token: string; expires_at: number } | null> {
  try {
    const response = await fetch("/api/public/session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(turnstileToken ? { turnstile_token: turnstileToken } : {}),
    });
    if (!response.ok) return null;
    const data = (await response.json()) as { token?: string; expires_at?: number } | null;
    if (!data || !data.token) return null;
    return { token: String(data.token), expires_at: Number(data.expires_at || 0) };
  } catch {
    return null;
  }
}

async function waitForTurnstileScript(timeoutMs: number): Promise<boolean> {
  if (typeof window === "undefined") return false;
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    if (window.turnstile) return true;
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  return false;
}

async function renderTurnstileWidget(
  siteKey: string,
  target: HTMLElement,
): Promise<string | null> {
  const ready = await waitForTurnstileScript(10_000);
  if (!ready || !window.turnstile) {
    // eslint-disable-next-line no-console
    console.error("[lia-public] Cloudflare Turnstile script never loaded");
    return null;
  }
  return new Promise((resolve) => {
    try {
      window.turnstile!.render(target, {
        sitekey: siteKey,
        theme: "light",
        callback: (token: string) => resolve(token),
        "error-callback": () => {
          // eslint-disable-next-line no-console
          console.error("[lia-public] Turnstile error callback fired");
          resolve(null);
        },
      });
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error("[lia-public] turnstile.render threw", error);
      resolve(null);
    }
  });
}

function scheduleSilentRefresh(expiresAtEpoch: number): void {
  if (!expiresAtEpoch) return;
  const nowMs = Date.now();
  const expiresMs = expiresAtEpoch * 1000;
  const refreshAt = expiresMs - 10 * 60 * 1000;
  const delayMs = Math.max(refreshAt - nowMs, 30 * 1000);
  if (!Number.isFinite(delayMs)) return;
  window.setTimeout(async () => {
    const ok = await refreshPublicSession();
    if (!ok) {
      clearPublicAccessToken();
      window.location.reload();
      return;
    }
    const next = Number(window.sessionStorage.getItem("lia_public_expires_at") || 0);
    scheduleSilentRefresh(next);
  }, delayMs);
}

interface MountedPublicShell {
  page: ReturnType<typeof createPageContext>;
  captcha: PublicCaptchaOverlayHandle;
  /** Called once the user has a valid JWT — wires up chatApp + any mobile controllers. */
  wireChat: () => Promise<void>;
}

/**
 * Mount the captcha overlay and add it to the document. Shared by both the
 * desktop and mobile public shells so the overlay markup lives in exactly
 * one place. Returns the molecule handle the caller stores on the shell
 * state for `showOverlay` / `setError`.
 */
function attachCaptchaOverlay(): PublicCaptchaOverlayHandle {
  const captcha = createPublicCaptchaOverlay({
    title: "Demuestra que eres humano",
    helpText: "Resuelve el captcha para empezar a usar LIA en modo público.",
  });
  // Try to insert into the dedicated mount slot first; fall back to body.
  const overlaySlot = document.querySelector<HTMLElement>('[data-mount="public-captcha-overlay"]');
  if (overlaySlot) {
    overlaySlot.replaceWith(captcha.root);
  } else {
    document.body.appendChild(captcha.root);
  }
  return captcha;
}

/**
 * Desktop public shell: navy banner + chat shell + side panels.
 * The chat controllers are NOT wired up here — `wireChat` does that once
 * the user has a valid JWT, so the captcha overlay can sit over the
 * un-wired chat shell while the user solves the challenge.
 */
function mountDesktopPublicShell(): MountedPublicShell {
  setApiClientMode("public");

  const page = createPageContext({ missingRootMessage: "Missing #app root." });
  page.setTitle("LIA — Acceso público");
  page.mountShell(renderPublicShell(page.i18n));

  // Insert the banner molecule into its mount slot. The brand mark
  // (logo + tagline) goes through the same atom the authenticated chrome
  // consumes, so the public banner inherits the canonical brand language.
  const bannerSlot = page.root.querySelector<HTMLElement>('[data-mount="public-banner"]');
  if (bannerSlot) {
    const banner = createPublicBanner({
      badgeLabel: "Acceso público",
      description: "sin historial.",
      logoSrc: "/assets/lia-logo.png",
      logoAlt: "LIA",
      tagline: page.i18n.t("chat.hero.tagline"),
    });
    bannerSlot.replaceWith(banner);
  }

  const captcha = attachCaptchaOverlay();

  const chatPanel = page.root.querySelector<HTMLElement>(".chat-panel");
  if (!chatPanel) {
    throw new Error("Missing .chat-panel inside public shell.");
  }

  let chatMounted = false;
  async function wireChat(): Promise<void> {
    if (chatMounted) return;
    mountChatApp(chatPanel, { i18n: page.i18n, mode: "public" });
    chatMounted = true;
  }

  return { page, captcha, wireChat };
}

/**
 * Mobile public shell: identical to what `user1@lia.dev` sees on mobile
 * (same `renderMobileShell`, same chat/normativa/interpretación bottom
 * tabs, same sheet), minus the auth-only drawer items (user info,
 * historial, logout) and the historial panel. Implemented by passing
 * `mode="public"` through `renderMobileShell`.
 *
 * The chat runs through `mountChatApp` on `#mobile-panel-chat` exactly
 * like the authenticated mobile path — same controller, same multi-turn
 * behavior — just with the `mode: "public"` flag so the chatApp hides
 * per-bubble feedback affordances.
 */
function mountMobilePublicShell(): MountedPublicShell {
  setApiClientMode("public");

  // iOS Safari: set shell height to window.innerHeight (accounts for toolbar)
  function syncShellHeight(): void {
    document.documentElement.style.setProperty("--app-height", `${window.innerHeight}px`);
  }
  syncShellHeight();
  window.addEventListener("resize", syncShellHeight);

  const page = createPageContext({ missingRootMessage: "Missing #app root." });
  page.setTitle("LIA — Acceso público");

  // The mobile shell template is the same one the authenticated chat
  // mounts. Dynamic-imported so the desktop path never loads the mobile
  // bundle.
  let chatMounted = false;

  async function wireChat(): Promise<void> {
    if (chatMounted) return;

    const [{ renderMobileShell }] = await Promise.all([
      import("@/app/mobile/shell-mobile"),
      import("@/styles/mobile/index.css"),
    ]);

    page.mountShell(renderMobileShell(page.i18n, "public"));
    // Re-attach the captcha overlay element (it was detached when mountShell
    // rewrote the #app innerHTML). `attachCaptchaOverlay` adds it to body
    // since the mobile shell has no mount slot.
    document.body.appendChild(captcha.root);

    const chatPanel = queryRequired<HTMLElement>(page.root, "#mobile-panel-chat");
    const chatApp = mountChatApp(chatPanel, { i18n: page.i18n, mode: "public" });

    // Mount the same mobile controllers the authenticated chat uses.
    // Historial is intentionally omitted — its DOM is not rendered in
    // `public` mode and the drawer controller tolerates the missing item.
    const [
      { mountMobileNav },
      { mountMobileSheet },
      { mountMobileNormativaPanel },
      { mountMobileInterpPanel },
      { mountMobileChatAdapter },
      { mountMobileDrawer },
      { getToastController },
    ] = await Promise.all([
      import("@/app/mobile/mobileNav"),
      import("@/app/mobile/mobileSheet"),
      import("@/app/mobile/mobileNormativaPanel"),
      import("@/app/mobile/mobileInterpPanel"),
      import("@/app/mobile/mobileChatAdapter"),
      import("@/app/mobile/mobileDrawer"),
      import("@/shared/ui/toasts"),
    ]);

    const toastController = getToastController(page.i18n);
    const chatLog = queryRequired<HTMLElement>(page.root, "#chat-log");
    const newThreadBtn = page.root.querySelector<HTMLButtonElement>("#new-thread-btn");

    const nav = mountMobileNav(page.root, {
      onChatTabReclick: async () => {
        const hasBubbles = chatLog.querySelector(".bubble") !== null;
        if (!hasBubbles) return;
        const confirmed = await toastController.confirm({
          message: page.i18n.t("chat.newChat.caution"),
          tone: "caution",
          confirmLabel: page.i18n.t("chat.newChat.confirmAction"),
          cancelLabel: page.i18n.t("chat.newChat.cancelAction"),
        });
        if (confirmed) newThreadBtn?.click();
      },
    });

    const mobileSheet = mountMobileSheet(page.root);
    const { setMobileSheet } = await import("@/features/chat/normative/articleReader");
    setMobileSheet(mobileSheet);

    const normativaPanel = mountMobileNormativaPanel(page.root, mobileSheet, {
      onOpenCitation: (citationId: string) => {
        if (chatApp && typeof chatApp.openCitationById === "function") {
          chatApp.openCitationById(citationId);
        }
      },
    });
    const interpPanel = mountMobileInterpPanel(page.root, mobileSheet, {
      onOpenCard: (cardId: string) => {
        if (chatApp && typeof chatApp.openExpertCardById === "function") {
          chatApp.openExpertCardById(cardId);
        }
      },
    });

    mountMobileChatAdapter({ root: page.root, nav, normativaPanel, interpPanel });

    mountMobileDrawer(page.root, {
      onNewConversation: () => {
        nav.switchTab("chat");
        page.root.querySelector<HTMLButtonElement>("#new-thread-btn")?.click();
      },
      // No `onHistorial` in public mode — the drawer item is absent from
      // the DOM, so the handler would never fire anyway. mobileDrawer
      // tolerates the missing callback.
    });

    chatMounted = true;
  }

  // The captcha overlay must exist BEFORE the mobile shell is mounted
  // (since the mobile path may have to show the overlay immediately on
  // first visit). We attach it to body now; `wireChat` re-appends it
  // AFTER mountShell wipes #app.
  const captcha = attachCaptchaOverlay();

  return { page, captcha, wireChat };
}

async function bootPublic(): Promise<void> {
  // Always mount the shell first so the captcha overlay (and the chat DOM
  // behind it) actually exists in the document. The overlay starts hidden
  // and only reveals itself in the captcha-required branch.
  const shell = isMobile() ? mountMobilePublicShell() : mountDesktopPublicShell();

  const hints = readBootHints();
  const existingToken = getPublicAccessToken();

  // Path 1 — token already in sessionStorage from a previous tab session.
  if (existingToken) {
    scheduleSilentRefresh(Number(window.sessionStorage.getItem("lia_public_expires_at") || 0));
    await shell.wireChat();
    return;
  }

  // Path 2 — server injected a token in the meta tag (returning IP, already
  // in `public_captcha_passes`).
  if (!hints.captchaRequired && hints.token) {
    setPublicAccessToken({ token: hints.token, expires_at: hints.expiresAt });
    scheduleSilentRefresh(hints.expiresAt);
    await shell.wireChat();
    return;
  }

  // Path 3 — first visit from this IP. Show the captcha overlay over the
  // (un-wired) chat shell, render the Turnstile widget, then on success POST
  // /api/public/session and wire the chat.
  shell.captcha.showOverlay();

  if (!hints.turnstileSiteKey) {
    shell.captcha.setError("Configuración de captcha no disponible. Recarga la página.");
    return;
  }

  const turnstileToken = await renderTurnstileWidget(
    hints.turnstileSiteKey,
    shell.captcha.widgetTarget,
  );
  if (!turnstileToken) {
    shell.captcha.setError(
      "No se pudo cargar el widget de captcha. Verifica que tu navegador permita scripts de challenges.cloudflare.com y recarga.",
    );
    return;
  }

  const session = await postSession(turnstileToken);
  if (!session) {
    shell.captcha.setError("Captcha rechazado por el servidor. Recarga e inténtalo de nuevo.");
    return;
  }

  setPublicAccessToken(session);
  shell.captcha.hideOverlay();
  scheduleSilentRefresh(session.expires_at);
  await shell.wireChat();
}

// We deliberately do NOT call requireAuth() — public visitors have no platform
// auth context and must never be redirected to /login.
void bootPublic();
