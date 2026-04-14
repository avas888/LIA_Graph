/**
 * Public visitor shell + API client mode flag + atomic molecule contracts.
 *
 * Verifies the user-visible invariants of the no-login `/public` surface:
 *   - Shell delegates the banner + captcha overlay to molecules in
 *     `shared/ui/molecules/`; the shell HTML only carries empty `data-mount`
 *     slots and the underlying chat shell.
 *   - `createPublicBanner` produces the canonical banner with a login link
 *     built via the `createLinkAction` atom (`data-lia-component`).
 *   - `createPublicCaptchaOverlay` produces the canonical hidden overlay
 *     with a `widgetTarget` ready for `turnstile.render(target, ...)`.
 *   - `setApiClientMode("public")` causes `buildHeaders` to read from
 *     `sessionStorage["lia_public_access_token"]` instead of localStorage.
 *   - `setPublicAccessToken` stores the token under the public key.
 */

import { beforeEach, describe, expect, it } from "vitest";

import { renderPublicShell } from "@/app/public/shell";
import { renderMobileShell } from "@/app/mobile/shell-mobile";
import { createBrandMark } from "@/shared/ui/atoms/brandMark";
import { createPublicBanner } from "@/shared/ui/molecules/publicBanner";
import { createPublicCaptchaOverlay } from "@/shared/ui/molecules/publicCaptchaOverlay";
import {
  setApiClientMode,
  getApiClientMode,
  getApiAccessToken,
} from "@/shared/api/client";
import {
  clearPublicAccessToken,
  getPublicAccessToken,
  setPublicAccessToken,
} from "@/shared/auth/publicSession";

const fakeI18n = {
  t: (key: string) => key,
} as unknown as Parameters<typeof renderPublicShell>[0];

beforeEach(() => {
  // Reset all storage between tests
  if (typeof window !== "undefined") {
    window.sessionStorage.clear();
    window.localStorage.clear();
  }
  setApiClientMode("platform");
});

describe("renderPublicShell", () => {
  it("wraps content in .public-mode for CSS scoping", () => {
    const html = renderPublicShell(fakeI18n);
    expect(html).toContain('class="public-mode public-shell"');
    expect(html).toContain('data-lia-component="public-shell"');
  });

  it("reserves data-mount slots for the banner and captcha overlay molecules", () => {
    const html = renderPublicShell(fakeI18n);
    expect(html).toContain('data-mount="public-banner"');
    expect(html).toContain('data-mount="public-captcha-overlay"');
  });

  it("does NOT inline the banner or captcha overlay markup (delegated to molecules)", () => {
    const html = renderPublicShell(fakeI18n);
    expect(html).not.toContain("lia-public-captcha-card");
    expect(html).not.toContain("lia-public-captcha-title");
    expect(html).not.toContain("lia-public-banner__text");
  });

  it("still renders the underlying chat shell DOM (so chatApp can mount)", () => {
    const html = renderPublicShell(fakeI18n);
    expect(html).toContain('id="chat-form"');
    expect(html).toContain('id="message"');
    expect(html).toContain('id="send-btn"');
    expect(html).toContain('id="chat-log"');
  });
});

describe("renderPublicShell DOM layout", () => {
  it("places the banner slot BEFORE the chat shell so it can shrink-wrap above it", () => {
    const container = document.createElement("div");
    container.innerHTML = renderPublicShell(fakeI18n);
    const publicMode = container.querySelector(".public-mode")!;
    const children = Array.from(publicMode.children);

    const bannerSlot = children.findIndex(
      (n) => n instanceof HTMLElement && n.dataset.mount === "public-banner",
    );
    const chatShell = children.findIndex(
      (n) => n instanceof HTMLElement && n.classList.contains("app-shell"),
    );

    expect(bannerSlot).toBeGreaterThanOrEqual(0);
    expect(chatShell).toBeGreaterThan(bannerSlot);
  });

  it("exposes the composer label, textarea, and send button as queryable nodes", () => {
    const container = document.createElement("div");
    container.innerHTML = renderPublicShell(fakeI18n);

    const label = container.querySelector<HTMLLabelElement>('label.composer-label[for="message"]');
    const textarea = container.querySelector<HTMLTextAreaElement>("textarea#message");
    const sendBtn = container.querySelector<HTMLButtonElement>("button#send-btn");

    expect(label).not.toBeNull();
    expect(textarea).not.toBeNull();
    expect(textarea?.required).toBe(true);
    expect(sendBtn).not.toBeNull();
    expect(sendBtn?.type).toBe("submit");
  });

  it("keeps the .composer-input-shell wrapper that hosts the textarea + idle cursor", () => {
    // The empty-state hint is now rendered by the textarea's native
    // `placeholder` attribute (wired through the `chat.composer.placeholder`
    // i18n key), and the pulsating cursor is still a sibling element
    // controlled by `compose-cursor.css` via the `[data-turn-state="ready-empty"]
    // .composer-input-shell textarea:focus ~ .composer-idle-cursor` selector.
    // The public shell must keep the wrapper + textarea + cursor nodes for
    // both mechanisms to render.
    const container = document.createElement("div");
    container.innerHTML = renderPublicShell(fakeI18n);

    const inputShell = container.querySelector(".composer-input-shell");
    expect(inputShell).not.toBeNull();
    const textarea = inputShell?.querySelector<HTMLTextAreaElement>("textarea#message");
    expect(textarea).not.toBeNull();
    // fakeI18n.t() returns the key verbatim, so the placeholder must
    // resolve to the `chat.composer.placeholder` key.
    expect(textarea?.getAttribute("placeholder")).toBe("chat.composer.placeholder");
    expect(inputShell?.querySelector(".composer-idle-cursor")).not.toBeNull();
  });
});

describe("createBrandMark atom", () => {
  it("renders the canonical data-lia-component contract", () => {
    const mark = createBrandMark({
      logoSrc: "/assets/lia-logo.png",
      logoAlt: "LIA",
      tagline: "Asesoria contable instantanea",
    });
    expect(mark.getAttribute("data-lia-component")).toBe("brand-mark");
    expect(mark.classList.contains("browser-tab-brand")).toBe(true);
    expect(mark.getAttribute("aria-hidden")).toBe("true");
  });

  it("composes a logo img and a tagline span using canonical class names", () => {
    const mark = createBrandMark({
      logoSrc: "/assets/lia-logo.png",
      logoAlt: "LIA",
      tagline: "Asesoria contable instantanea",
    });
    const logo = mark.querySelector<HTMLImageElement>("img.browser-tab-brand-logo");
    expect(logo).not.toBeNull();
    expect(logo!.getAttribute("src")).toBe("/assets/lia-logo.png");
    expect(logo!.alt).toBe("LIA");
    const tagline = mark.querySelector<HTMLElement>("span.browser-tab-brand-tagline");
    expect(tagline?.textContent).toBe("Asesoria contable instantanea");
  });
});

describe("createPublicBanner molecule", () => {
  function buildBanner() {
    return createPublicBanner({
      badgeLabel: "Acceso público",
      description: "sin historial.",
      logoSrc: "/assets/lia-logo.png",
      logoAlt: "LIA",
      tagline: "Asesoria contable instantanea",
    });
  }

  it("renders the data-lia-component contract on a header element", () => {
    const banner = buildBanner();
    expect(banner.getAttribute("data-lia-component")).toBe("public-banner");
    expect(banner.tagName.toLowerCase()).toBe("header");
    expect(banner.getAttribute("role")).toBe("banner");
  });

  it("renders the disclosure pill as plain text — no anchors", () => {
    const banner = buildBanner();
    const disclosure = banner.querySelector<HTMLElement>('[data-lia-component="public-banner-disclosure"]');
    expect(disclosure).not.toBeNull();
    expect(disclosure!.textContent).toContain("Acceso público");
    expect(disclosure!.textContent).toContain("sin historial.");
    const badge = banner.querySelector<HTMLElement>(".lia-public-banner__badge");
    expect(badge?.textContent).toBe("Acceso público");
  });

  it("composes the brand mark via the createBrandMark atom (single source of truth)", () => {
    const banner = buildBanner();
    const brandMark = banner.querySelector<HTMLElement>('[data-lia-component="brand-mark"]');
    expect(brandMark).not.toBeNull();
    // The atom must be the ONLY logo path in the banner — no inline <img>
    // outside the atom.
    const allImgs = banner.querySelectorAll("img");
    expect(allImgs.length).toBe(1);
    expect(brandMark!.contains(allImgs[0])).toBe(true);
    expect(allImgs[0].getAttribute("src")).toBe("/assets/lia-logo.png");
    // Tagline is inside the brand mark (not duplicated outside).
    expect(brandMark!.querySelector(".browser-tab-brand-tagline")?.textContent).toBe(
      "Asesoria contable instantanea",
    );
  });

  it("contains NO login CTA — public surface is a deliberate dead end", () => {
    const banner = buildBanner();
    const anchors = banner.querySelectorAll("a");
    expect(anchors.length).toBe(0);
    expect(banner.outerHTML).not.toContain("/login");
    expect(banner.outerHTML.toLowerCase()).not.toContain("inicia sesión");
    expect(banner.outerHTML.toLowerCase()).not.toContain("inicia sesion");
  });

  it("contains NO tabs — tabs are an authenticated-only affordance", () => {
    const banner = buildBanner();
    expect(banner.querySelectorAll(".browser-tab").length).toBe(0);
    expect(banner.querySelectorAll('[role="tab"]').length).toBe(0);
    expect(banner.querySelectorAll('[role="tablist"]').length).toBe(0);
  });
});

describe("createPublicCaptchaOverlay molecule", () => {
  it("starts hidden and exposes the data-lia-component contract", () => {
    const overlay = createPublicCaptchaOverlay({
      title: "Demuestra que eres humano",
      helpText: "Resuelve el captcha para empezar.",
    });
    expect(overlay.root.getAttribute("data-lia-component")).toBe("public-captcha-overlay");
    expect(overlay.root.hidden).toBe(true);
    expect(overlay.root.getAttribute("role")).toBe("dialog");
    expect(overlay.root.getAttribute("aria-modal")).toBe("true");
  });

  it("provides a widgetTarget element for the Turnstile mount", () => {
    const overlay = createPublicCaptchaOverlay({ title: "t", helpText: "h" });
    expect(overlay.widgetTarget.id).toBe("public-captcha-widget");
    expect(overlay.widgetTarget.getAttribute("data-lia-component")).toBe("public-captcha-widget");
    // The widget target lives inside the overlay root
    expect(overlay.root.contains(overlay.widgetTarget)).toBe(true);
  });

  it("uses the createStateBlock molecule for the helper copy", () => {
    const overlay = createPublicCaptchaOverlay({
      title: "Demuestra que eres humano",
      helpText: "Resuelve el captcha para empezar.",
    });
    const stateBlock = overlay.root.querySelector('[data-lia-component="state-block"]');
    expect(stateBlock).not.toBeNull();
    expect(stateBlock!.textContent).toContain("Resuelve el captcha");
  });

  it("setError swaps the state-block tone to error and updates the message", () => {
    const overlay = createPublicCaptchaOverlay({ title: "t", helpText: "default copy" });
    overlay.setError("captcha rechazado");
    const stateBlock = overlay.root.querySelector('[data-lia-component="state-block"]');
    expect(stateBlock!.classList.contains("lia-state-block--error")).toBe(true);
    expect(stateBlock!.classList.contains("lia-state-block--loading")).toBe(false);
    expect(stateBlock!.getAttribute("role")).toBe("alert");
    expect(stateBlock!.textContent).toContain("captcha rechazado");
  });

  it("clearError restores the loading tone and the original copy", () => {
    const overlay = createPublicCaptchaOverlay({ title: "t", helpText: "default copy" });
    overlay.setError("oops");
    overlay.clearError();
    const stateBlock = overlay.root.querySelector('[data-lia-component="state-block"]');
    expect(stateBlock!.classList.contains("lia-state-block--loading")).toBe(true);
    expect(stateBlock!.classList.contains("lia-state-block--error")).toBe(false);
    expect(stateBlock!.textContent).toContain("default copy");
  });

  it("showOverlay/hideOverlay toggle the hidden attribute", () => {
    const overlay = createPublicCaptchaOverlay({ title: "t", helpText: "h" });
    expect(overlay.root.hidden).toBe(true);
    overlay.showOverlay();
    expect(overlay.root.hidden).toBe(false);
    overlay.hideOverlay();
    expect(overlay.root.hidden).toBe(true);
  });
});

describe("publicSession storage", () => {
  it("setPublicAccessToken writes to sessionStorage", () => {
    setPublicAccessToken({ token: "abc.def.ghi", expires_at: 1700000000 });
    expect(window.sessionStorage.getItem("lia_public_access_token")).toBe("abc.def.ghi");
    expect(getPublicAccessToken()).toBe("abc.def.ghi");
  });

  it("clearPublicAccessToken removes both keys", () => {
    setPublicAccessToken({ token: "abc.def.ghi", expires_at: 1700000000 });
    clearPublicAccessToken();
    expect(getPublicAccessToken()).toBeNull();
    expect(window.sessionStorage.getItem("lia_public_expires_at")).toBeNull();
  });
});

describe("setApiClientMode", () => {
  it("defaults to platform mode", () => {
    expect(getApiClientMode()).toBe("platform");
  });

  it("switches to public mode and reads from sessionStorage", () => {
    window.sessionStorage.setItem("lia_public_access_token", "public-jwt-token");
    window.localStorage.setItem("lia_platform_access_token", "platform-jwt-token");

    setApiClientMode("public");
    expect(getApiAccessToken()).toBe("public-jwt-token");
  });

  it("switches back to platform mode and reads from localStorage", () => {
    window.sessionStorage.setItem("lia_public_access_token", "public-jwt-token");
    window.localStorage.setItem("lia_platform_access_token", "platform-jwt-token");

    setApiClientMode("public");
    expect(getApiAccessToken()).toBe("public-jwt-token");

    setApiClientMode("platform");
    expect(getApiAccessToken()).toBe("platform-jwt-token");
  });

  it("returns null when public mode has no token", () => {
    setApiClientMode("public");
    expect(getApiAccessToken()).toBeNull();
  });
});

describe("renderMobileShell public mode parity", () => {
  function buildContainer(mode: "default" | "public"): HTMLElement {
    const container = document.createElement("div");
    container.innerHTML = renderMobileShell(fakeI18n, mode);
    return container;
  }

  it("tags the shell with data-mobile-mode + mobile-shell--public class", () => {
    const container = buildContainer("public");
    const shell = container.querySelector<HTMLElement>(".mobile-shell")!;
    expect(shell.dataset.liaComponent).toBe("mobile-shell");
    expect(shell.dataset.mobileMode).toBe("public");
    expect(shell.classList.contains("mobile-shell--public")).toBe(true);
  });

  it("defaults to authenticated mode when no flag is passed", () => {
    const container = buildContainer("default");
    const shell = container.querySelector<HTMLElement>(".mobile-shell")!;
    expect(shell.dataset.mobileMode).toBe("default");
    expect(shell.classList.contains("mobile-shell--public")).toBe(false);
  });

  it("keeps the three content tabs (chat / normativa / interpretación) in public mode", () => {
    const container = buildContainer("public");
    const tabs = container.querySelectorAll<HTMLElement>(".mobile-tab[data-tab]");
    const tabIds = Array.from(tabs).map((t) => t.dataset.tab);
    expect(tabIds).toEqual(["chat", "normativa", "interpretacion"]);
  });

  it("keeps the chat/normativa/interpretación panels mounted for public", () => {
    const container = buildContainer("public");
    expect(container.querySelector("#mobile-panel-chat")).not.toBeNull();
    expect(container.querySelector("#mobile-panel-normativa")).not.toBeNull();
    expect(container.querySelector("#mobile-panel-interpretacion")).not.toBeNull();
  });

  it("embeds the full chat shell inside #mobile-panel-chat so chatApp can mount", () => {
    const container = buildContainer("public");
    const chatPanel = container.querySelector<HTMLElement>("#mobile-panel-chat")!;
    // Same DOM ids chatDom.ts collects
    expect(chatPanel.querySelector("#chat-form")).not.toBeNull();
    expect(chatPanel.querySelector("#message")).not.toBeNull();
    expect(chatPanel.querySelector("#send-btn")).not.toBeNull();
    expect(chatPanel.querySelector("#chat-log")).not.toBeNull();
    expect(chatPanel.querySelector("#chat-session-drawer")).not.toBeNull();
  });

  it("strips the historial panel in public mode", () => {
    const container = buildContainer("public");
    expect(container.querySelector("#mobile-panel-historial")).toBeNull();
  });

  it("keeps the historial panel in default mode (parity guard)", () => {
    const container = buildContainer("default");
    expect(container.querySelector("#mobile-panel-historial")).not.toBeNull();
  });

  it("strips the user-info block + role labels in public mode", () => {
    const container = buildContainer("public");
    expect(container.querySelector(".mobile-drawer-user")).toBeNull();
    expect(container.querySelector("#mobile-drawer-user-name")).toBeNull();
    expect(container.querySelector("#mobile-drawer-user-role")).toBeNull();
  });

  it("strips the historial drawer item and the logout footer in public mode", () => {
    const container = buildContainer("public");
    expect(container.querySelector('[data-drawer-action="historial"]')).toBeNull();
    expect(container.querySelector('[data-drawer-action="logout"]')).toBeNull();
    expect(container.querySelector(".mobile-drawer-footer")).toBeNull();
  });

  it("keeps the 'Nueva conversación' drawer action in public mode", () => {
    const container = buildContainer("public");
    const newConv = container.querySelector('[data-drawer-action="new-conversation"]');
    expect(newConv).not.toBeNull();
  });

  it("default mode still renders historial + user info + logout (parity guard)", () => {
    const container = buildContainer("default");
    expect(container.querySelector(".mobile-drawer-user")).not.toBeNull();
    expect(container.querySelector('[data-drawer-action="historial"]')).not.toBeNull();
    expect(container.querySelector('[data-drawer-action="logout"]')).not.toBeNull();
    expect(container.querySelector(".mobile-drawer-footer")).not.toBeNull();
  });

  it("preserves the bottom sheet and hamburger in public mode", () => {
    const container = buildContainer("public");
    expect(container.querySelector(".mobile-sheet-overlay")).not.toBeNull();
    expect(container.querySelector(".mobile-hamburger-btn")).not.toBeNull();
  });
});
