/**
 * Public visitor captcha overlay molecule.
 *
 * Built from atoms (`createStateBlock` for the messaging card) and a single
 * data-lia-component contract so app/public/main.ts and any future no-login
 * surface can reuse it without duplicating markup.
 *
 * The overlay starts hidden (`hidden` attribute). The owning controller calls
 * `showOverlay()` after wiring the Turnstile widget into the returned
 * `widgetTarget` element. On error, the controller calls `setError(message)`
 * which mutates the state-block message in place.
 *
 * Per docs/ui/atomic_design_ui_architecture.md §3 — no raw hex, no inline svg.
 * All colors come from CSS tokens via `lia-public-captcha-overlay` styles in
 * `frontend/src/styles/public.css`.
 */

import { createStateBlock } from "@/shared/ui/molecules/stateBlock";

export interface PublicCaptchaOverlayHandle {
  /** Root overlay element to insert into the DOM. Starts `hidden`. */
  root: HTMLElement;
  /** Empty `<div>` where the Turnstile (or any) widget mounts. */
  widgetTarget: HTMLElement;
  /** Reveal the overlay (clears `hidden`). */
  showOverlay: () => void;
  /** Hide the overlay (sets `hidden`). */
  hideOverlay: () => void;
  /** Replace the helper copy with an error message. */
  setError: (message: string) => void;
  /** Restore the default helper copy. */
  clearError: () => void;
}

export interface PublicCaptchaOverlayOptions {
  title: string;
  helpText: string;
}

export function createPublicCaptchaOverlay({
  title,
  helpText,
}: PublicCaptchaOverlayOptions): PublicCaptchaOverlayHandle {
  const root = document.createElement("div");
  root.id = "public-captcha-overlay";
  root.className = "lia-public-captcha-overlay";
  root.setAttribute("data-lia-component", "public-captcha-overlay");
  root.setAttribute("role", "dialog");
  root.setAttribute("aria-modal", "true");
  root.setAttribute("aria-labelledby", "public-captcha-title");
  root.hidden = true;

  const card = document.createElement("div");
  card.className = "lia-public-captcha-card";
  card.setAttribute("data-lia-component", "public-captcha-card");

  const heading = document.createElement("h2");
  heading.id = "public-captcha-title";
  heading.className = "lia-public-captcha-title";
  heading.textContent = title;
  card.appendChild(heading);

  // The state block carries the helper copy AND becomes the error surface
  // when `setError` is called. We start with an empty/loading tone so the
  // visual is "we are waiting for your input".
  const state = createStateBlock({
    className: "lia-public-captcha-state",
    compact: true,
    message: helpText,
    tone: "loading",
  });
  card.appendChild(state);

  const widgetTarget = document.createElement("div");
  widgetTarget.id = "public-captcha-widget";
  widgetTarget.className = "lia-public-captcha-widget";
  widgetTarget.setAttribute("data-lia-component", "public-captcha-widget");
  card.appendChild(widgetTarget);

  root.appendChild(card);

  function getMessageNode(): HTMLElement | null {
    return state.querySelector<HTMLElement>(".lia-state-block__message");
  }

  return {
    root,
    widgetTarget,
    showOverlay: () => {
      root.hidden = false;
    },
    hideOverlay: () => {
      root.hidden = true;
    },
    setError: (message: string) => {
      state.classList.remove("lia-state-block--loading");
      state.classList.add("lia-state-block--error");
      state.setAttribute("role", "alert");
      state.setAttribute("aria-live", "assertive");
      const spinner = state.querySelector(".lia-state-block__spinner");
      if (spinner) spinner.remove();
      const messageNode = getMessageNode();
      if (messageNode) messageNode.textContent = message;
    },
    clearError: () => {
      state.classList.remove("lia-state-block--error");
      state.classList.add("lia-state-block--loading");
      state.setAttribute("role", "status");
      state.setAttribute("aria-live", "polite");
      const messageNode = getMessageNode();
      if (messageNode) messageNode.textContent = helpText;
    },
  };
}
