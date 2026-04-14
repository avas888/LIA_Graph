/**
 * Reusable googly-eyes loader — a lightweight inline spinner
 * distinct from the full-screen LIA thinking overlay.
 *
 * Usage:
 *   import { createGooglyLoader } from "@/shared/ui/googlyLoader";
 *   const loader = createGooglyLoader("Cargando historial...");
 *   container.appendChild(loader.el);
 *   // later:
 *   loader.hide();   // hides with hidden attribute
 *   loader.show();   // shows again
 *   loader.setText("Reanudando..."); // update label
 *   loader.remove(); // remove from DOM
 */

import "@/styles/googly-loader.css";

export interface GooglyLoader {
  el: HTMLElement;
  show(): void;
  hide(): void;
  setText(text: string): void;
  remove(): void;
}

export function createGooglyLoader(label?: string): GooglyLoader {
  const wrapper = document.createElement("div");
  wrapper.className = "googly-loader";
  wrapper.setAttribute("role", "status");
  wrapper.setAttribute("aria-live", "polite");

  wrapper.innerHTML = `
    <div class="googly-loader-orb" aria-hidden="true">
      <span class="googly-loader-core">
        <span class="lia-thinking-eye-pair">
          <span class="lia-thinking-eye">
            <span class="lia-thinking-eye-pupil"></span>
          </span>
          <span class="lia-thinking-eye">
            <span class="lia-thinking-eye-pupil"></span>
          </span>
        </span>
      </span>
    </div>
    ${label ? `<span class="googly-loader-label">${label}</span>` : ""}
  `;

  const labelEl = wrapper.querySelector<HTMLElement>(".googly-loader-label");

  return {
    el: wrapper,
    show() {
      wrapper.hidden = false;
    },
    hide() {
      wrapper.hidden = true;
    },
    setText(text: string) {
      if (labelEl) {
        labelEl.textContent = text;
      } else if (text) {
        const span = document.createElement("span");
        span.className = "googly-loader-label";
        span.textContent = text;
        wrapper.appendChild(span);
      }
    },
    remove() {
      wrapper.remove();
    },
  };
}
