import { describe, expect, it, beforeEach, vi } from "vitest";
import { mountMobileDrawer } from "@/app/mobile/mobileDrawer";

// Mock auth context
vi.mock("@/shared/auth/authContext", () => ({
  getAuthContext: () => ({
    tenantId: "t-1",
    userId: "user-1",
    role: "tenant_user",
    activeCompanyId: "c-1",
    integrationId: "",
  }),
  clearAuthContext: vi.fn(),
}));

function createDom(): HTMLElement {
  const root = document.createElement("div");
  root.innerHTML = `
    <button class="mobile-hamburger-btn" type="button">&#9776;</button>
    <div class="mobile-drawer" hidden>
      <div class="mobile-drawer-scrim"></div>
      <div class="mobile-drawer-panel">
        <div class="mobile-drawer-header">
          <div class="mobile-drawer-brand">
            <span class="mobile-drawer-brand-name">LIA</span>
          </div>
          <button class="mobile-drawer-close" type="button">&times;</button>
        </div>
        <div class="mobile-drawer-user">
          <p id="mobile-drawer-user-name" class="mobile-drawer-user-name"></p>
          <p id="mobile-drawer-user-role" class="mobile-drawer-user-role"></p>
        </div>
        <nav class="mobile-drawer-nav">
          <button class="mobile-drawer-item" type="button" data-drawer-action="new-conversation">Nueva conversación</button>
          <button class="mobile-drawer-item" type="button" data-drawer-action="historial">Historial</button>
        </nav>
        <div class="mobile-drawer-footer">
          <button class="mobile-drawer-item" type="button" data-drawer-action="logout">Cerrar sesión</button>
        </div>
      </div>
    </div>
  `;
  return root;
}

describe("mobileDrawer", () => {
  let root: HTMLElement;

  beforeEach(() => {
    document.body.innerHTML = "";
    root = createDom();
    document.body.appendChild(root);
  });

  it("opens when hamburger button is clicked", () => {
    mountMobileDrawer(root, {
      onNewConversation: vi.fn(),
      onHistorial: vi.fn(),
    });

    const hamburger = root.querySelector<HTMLButtonElement>(".mobile-hamburger-btn")!;
    hamburger.click();

    const drawer = root.querySelector<HTMLElement>(".mobile-drawer")!;
    expect(drawer.hidden).toBe(false);
    expect(drawer.classList.contains("is-open")).toBe(true);
  });

  it("closes when close button is clicked", () => {
    const { close } = mountMobileDrawer(root, {
      onNewConversation: vi.fn(),
      onHistorial: vi.fn(),
    });

    const hamburger = root.querySelector<HTMLButtonElement>(".mobile-hamburger-btn")!;
    hamburger.click();

    const closeBtn = root.querySelector<HTMLButtonElement>(".mobile-drawer-close")!;
    closeBtn.click();

    const drawer = root.querySelector<HTMLElement>(".mobile-drawer")!;
    expect(drawer.classList.contains("is-open")).toBe(false);
  });

  it("closes when scrim is clicked", () => {
    mountMobileDrawer(root, {
      onNewConversation: vi.fn(),
      onHistorial: vi.fn(),
    });

    const hamburger = root.querySelector<HTMLButtonElement>(".mobile-hamburger-btn")!;
    hamburger.click();

    const scrim = root.querySelector<HTMLElement>(".mobile-drawer-scrim")!;
    scrim.click();

    const drawer = root.querySelector<HTMLElement>(".mobile-drawer")!;
    expect(drawer.classList.contains("is-open")).toBe(false);
  });

  it("calls onNewConversation callback", () => {
    const onNew = vi.fn();
    mountMobileDrawer(root, {
      onNewConversation: onNew,
      onHistorial: vi.fn(),
    });

    const btn = root.querySelector<HTMLButtonElement>('[data-drawer-action="new-conversation"]')!;
    btn.click();

    expect(onNew).toHaveBeenCalledOnce();
  });

  it("calls onHistorial callback", () => {
    const onHist = vi.fn();
    mountMobileDrawer(root, {
      onNewConversation: vi.fn(),
      onHistorial: onHist,
    });

    const btn = root.querySelector<HTMLButtonElement>('[data-drawer-action="historial"]')!;
    btn.click();

    expect(onHist).toHaveBeenCalledOnce();
  });

  it("populates user info from auth context", () => {
    mountMobileDrawer(root, {
      onNewConversation: vi.fn(),
      onHistorial: vi.fn(),
    });

    expect(root.querySelector("#mobile-drawer-user-name")!.textContent).toBe("user-1");
    expect(root.querySelector("#mobile-drawer-user-role")!.textContent).toBe("Contador");
  });
});
