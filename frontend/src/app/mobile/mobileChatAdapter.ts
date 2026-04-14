import type { MobileNav } from "./mobileNav";
import type { MobileNormativaPanel } from "./mobileNormativaPanel";
import type { MobileInterpPanel } from "./mobileInterpPanel";
import { icons } from "@/shared/ui/icons";
import {
  UI_EVENT_CITATIONS_UPDATED,
  UI_EVENT_EXPERTS_UPDATED,
  type CitationsUpdatedDetail,
  type ExpertsUpdatedDetail,
} from "@/shared/ui/patterns/uiEvents";
import { flattenCitationGroups } from "@/shared/ui/organisms/citationList";

export interface MobileChatAdapterDeps {
  root: HTMLElement;
  nav: MobileNav;
  normativaPanel: MobileNormativaPanel;
  interpPanel: MobileInterpPanel;
}

/**
 * Bridges chat state updates into the mobile shell without scraping desktop DOM.
 */
export function mountMobileChatAdapter(deps: MobileChatAdapterDeps): void {
  const {
    root,
    nav,
    normativaPanel,
    interpPanel,
  } = deps;

  const chatForm = root.querySelector<HTMLFormElement>("#chat-form")!;
  const messageInput = root.querySelector<HTMLTextAreaElement>("#message")!;

  root.addEventListener(UI_EVENT_CITATIONS_UPDATED, (event: Event) => {
    const detail = (event as CustomEvent<CitationsUpdatedDetail>).detail;
    const items = flattenCitationGroups(detail?.groups || []);
    normativaPanel.setCitations(items);
    nav.updateBadge("normativa", items.length);
    if (detail?.isFinal) {
      interpPanel.setResponseReceived(true);
    }
  });

  root.addEventListener(UI_EVENT_EXPERTS_UPDATED, (event: Event) => {
    const detail = (event as CustomEvent<ExpertsUpdatedDetail>).detail;
    const cards = detail?.cards || [];
    interpPanel.setCards(cards);
    nav.updateBadge("interpretacion", cards.length);
  });

  chatForm.addEventListener("submit", () => {
    nav.resetBadges();
    normativaPanel.clear();
    interpPanel.clear();
    interpPanel.setResponseReceived(false);
  });

  const newThreadBtn = root.querySelector<HTMLButtonElement>("#new-thread-btn");
  if (newThreadBtn) {
    newThreadBtn.addEventListener("click", () => {
      nav.resetBadges();
      normativaPanel.clear();
      interpPanel.clear();
      interpPanel.setResponseReceived(false);
      nav.switchTab("chat");
    });
  }

  const sendBtn = root.querySelector<HTMLButtonElement>("#send-btn");
  if (sendBtn) {
    const label = sendBtn.textContent?.trim() || "Enviar";
    sendBtn.innerHTML = icons.send;
    sendBtn.setAttribute("aria-label", label);
  }

  messageInput.addEventListener("input", () => {
    messageInput.style.height = "auto";
    messageInput.style.height = `${Math.min(messageInput.scrollHeight, 120)}px`;
  });
}
