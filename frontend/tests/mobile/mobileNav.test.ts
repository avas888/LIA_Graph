import { describe, expect, it, beforeEach, afterEach } from "vitest";
import { mountMobileNav } from "@/app/mobile/mobileNav";

function createDom(): HTMLElement {
  const root = document.createElement("div");
  root.innerHTML = `
    <div class="mobile-viewport">
      <div id="mobile-panel-chat" class="mobile-panel is-active"></div>
      <div id="mobile-panel-normativa" class="mobile-panel"></div>
      <div id="mobile-panel-interpretacion" class="mobile-panel"></div>
      <div id="mobile-panel-historial" class="mobile-panel"></div>
    </div>
    <nav class="mobile-tab-bar">
      <button class="mobile-tab is-active" data-tab="chat" type="button">
        <span class="mobile-tab-icon">Chat</span>
        <span class="mobile-tab-label">Chat</span>
      </button>
      <button class="mobile-tab" data-tab="normativa" type="button">
        <span class="mobile-tab-icon">Norm</span>
        <span class="mobile-tab-label">Normativa</span>
        <span class="mobile-tab-badge" hidden></span>
      </button>
      <button class="mobile-tab" data-tab="interpretacion" type="button">
        <span class="mobile-tab-icon">Interp</span>
        <span class="mobile-tab-label">Interp.</span>
        <span class="mobile-tab-badge" hidden></span>
      </button>
    </nav>
  `;
  return root;
}

describe("mobileNav", () => {
  let root: HTMLElement;

  beforeEach(() => {
    document.body.innerHTML = "";
    root = createDom();
    document.body.appendChild(root);
  });

  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("starts with chat tab active", () => {
    const nav = mountMobileNav(root);
    expect(nav.activeTab()).toBe("chat");
    expect(root.querySelector("#mobile-panel-chat")!.classList.contains("is-active")).toBe(true);
  });

  it("switchTab shows correct panel and hides others", () => {
    const nav = mountMobileNav(root);
    nav.switchTab("normativa");

    expect(nav.activeTab()).toBe("normativa");
    expect(root.querySelector("#mobile-panel-chat")!.classList.contains("is-active")).toBe(false);
    expect(root.querySelector("#mobile-panel-normativa")!.classList.contains("is-active")).toBe(true);
    expect(root.querySelector("#mobile-panel-interpretacion")!.classList.contains("is-active")).toBe(false);
  });

  it("click on tab switches panel", () => {
    mountMobileNav(root);
    const interpBtn = root.querySelector<HTMLButtonElement>('.mobile-tab[data-tab="interpretacion"]')!;
    interpBtn.click();

    expect(root.querySelector("#mobile-panel-interpretacion")!.classList.contains("is-active")).toBe(true);
    expect(root.querySelector("#mobile-panel-chat")!.classList.contains("is-active")).toBe(false);
  });

  it("updateBadge shows badge with count", () => {
    const nav = mountMobileNav(root);
    nav.updateBadge("normativa", 3);

    const badge = root.querySelector('.mobile-tab[data-tab="normativa"] .mobile-tab-badge')!;
    expect(badge.textContent).toBe("3");
    expect((badge as HTMLElement).hidden).toBe(false);
  });

  it("updateBadge hides badge when count is 0", () => {
    const nav = mountMobileNav(root);
    nav.updateBadge("normativa", 3);
    nav.updateBadge("normativa", 0);

    const badge = root.querySelector('.mobile-tab[data-tab="normativa"] .mobile-tab-badge') as HTMLElement;
    expect(badge.hidden).toBe(true);
  });

  it("resetBadges hides all badges", () => {
    const nav = mountMobileNav(root);
    nav.updateBadge("normativa", 5);
    nav.updateBadge("interpretacion", 2);
    nav.resetBadges();

    const badges = root.querySelectorAll<HTMLElement>(".mobile-tab-badge");
    badges.forEach((b) => expect(b.hidden).toBe(true));
  });

  it("tab button gets is-active class when switched", () => {
    mountMobileNav(root);
    const normBtn = root.querySelector<HTMLButtonElement>('.mobile-tab[data-tab="normativa"]')!;
    normBtn.click();

    expect(normBtn.classList.contains("is-active")).toBe(true);
    const chatBtn = root.querySelector<HTMLButtonElement>('.mobile-tab[data-tab="chat"]')!;
    expect(chatBtn.classList.contains("is-active")).toBe(false);
  });
});
