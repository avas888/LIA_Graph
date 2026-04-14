import { describe, expect, it, beforeEach, vi } from "vitest";
import { mountMobileSheet } from "@/app/mobile/mobileSheet";

function createDom(): HTMLElement {
  const root = document.createElement("div");
  root.innerHTML = `
    <div class="mobile-sheet-overlay" hidden>
      <div class="mobile-sheet-scrim"></div>
      <div class="mobile-sheet">
        <div class="mobile-sheet-handle"></div>
        <div class="mobile-sheet-header">
          <div>
            <h3 class="mobile-sheet-title"></h3>
            <p class="mobile-sheet-subtitle"></p>
          </div>
          <button class="mobile-sheet-close" type="button">&times;</button>
        </div>
        <div class="mobile-sheet-content"></div>
      </div>
    </div>
  `;
  return root;
}

describe("mobileSheet", () => {
  let root: HTMLElement;

  beforeEach(() => {
    document.body.innerHTML = "";
    document.body.style.overflow = "";
    root = createDom();
    document.body.appendChild(root);
  });

  it("starts closed", () => {
    const sheet = mountMobileSheet(root);
    expect(sheet.isOpen()).toBe(false);
  });

  it("open shows overlay and sets content", () => {
    const sheet = mountMobileSheet(root);
    sheet.open({
      title: "Estatuto Tributario",
      subtitle: "Art. 240",
      html: "<p>Content here</p>",
    });

    expect(sheet.isOpen()).toBe(true);
    const overlay = root.querySelector<HTMLElement>(".mobile-sheet-overlay")!;
    expect(overlay.hidden).toBe(false);
    expect(overlay.classList.contains("is-open")).toBe(true);

    expect(root.querySelector(".mobile-sheet-title")!.textContent).toBe("Estatuto Tributario");
    expect(root.querySelector(".mobile-sheet-subtitle")!.textContent).toBe("Art. 240");
    expect(root.querySelector(".mobile-sheet-content")!.innerHTML).toContain("Content here");
  });

  it("close button closes the sheet", () => {
    const sheet = mountMobileSheet(root);
    sheet.open({ title: "Test", html: "<p>hi</p>" });

    const closeBtn = root.querySelector<HTMLButtonElement>(".mobile-sheet-close")!;
    closeBtn.click();

    expect(sheet.isOpen()).toBe(false);
    const overlay = root.querySelector<HTMLElement>(".mobile-sheet-overlay")!;
    expect(overlay.classList.contains("is-open")).toBe(false);
  });

  it("scrim click closes the sheet", () => {
    const sheet = mountMobileSheet(root);
    sheet.open({ title: "Test", html: "<p>hi</p>" });

    const scrim = root.querySelector<HTMLElement>(".mobile-sheet-scrim")!;
    scrim.click();

    expect(sheet.isOpen()).toBe(false);
  });

  it("escape key closes the sheet", () => {
    const sheet = mountMobileSheet(root);
    sheet.open({ title: "Test", html: "<p>hi</p>" });

    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));

    expect(sheet.isOpen()).toBe(false);
  });

  it("subtitle is hidden when not provided", () => {
    const sheet = mountMobileSheet(root);
    sheet.open({ title: "Test", html: "<p>hi</p>" });

    const subtitle = root.querySelector<HTMLElement>(".mobile-sheet-subtitle")!;
    expect(subtitle.hidden).toBe(true);
  });
});
