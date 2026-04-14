import { beforeEach, describe, expect, it, vi } from "vitest";
import { createTooltipManager } from "@/features/chat/chatTooltipManager";

function createDeps() {
  const expertTooltipNode = document.createElement("div");
  expertTooltipNode.hidden = true;
  const expertTooltipShellNode = document.createElement("div");
  const expertTooltipTriggerNode = document.createElement("button");
  expertTooltipShellNode.appendChild(expertTooltipTriggerNode);
  document.body.appendChild(expertTooltipShellNode);
  return { expertTooltipNode, expertTooltipShellNode, expertTooltipTriggerNode };
}

describe("createTooltipManager", () => {
  let deps: ReturnType<typeof createDeps>;
  let mgr: ReturnType<typeof createTooltipManager>;

  beforeEach(() => {
    document.body.innerHTML = "";
    deps = createDeps();
    mgr = createTooltipManager(deps);
  });

  describe("setExpertTooltipOpen", () => {
    it("opens the tooltip and sets aria-expanded", () => {
      mgr.setExpertTooltipOpen(true);
      expect(deps.expertTooltipNode.hidden).toBe(false);
      expect(deps.expertTooltipTriggerNode.getAttribute("aria-expanded")).toBe("true");
    });

    it("closes the tooltip and clears aria-expanded", () => {
      mgr.setExpertTooltipOpen(true);
      mgr.setExpertTooltipOpen(false);
      expect(deps.expertTooltipNode.hidden).toBe(true);
      expect(deps.expertTooltipTriggerNode.getAttribute("aria-expanded")).toBe("false");
    });
  });

  describe("updateExpertTooltipPosition", () => {
    it("does nothing when tooltip is hidden", () => {
      deps.expertTooltipNode.hidden = true;
      mgr.updateExpertTooltipPosition();
      expect(deps.expertTooltipNode.style.top).toBe("");
    });

    it("sets top and left when tooltip is visible", () => {
      mgr.setExpertTooltipOpen(true);
      // jsdom getBoundingClientRect returns zeros, so position should be set to margin values
      mgr.updateExpertTooltipPosition();
      expect(deps.expertTooltipNode.style.top).toBeTruthy();
      expect(deps.expertTooltipNode.style.left).toBeTruthy();
    });
  });

  describe("bindExpertTooltip", () => {
    it("moves tooltip to document.body and adds floating class", () => {
      mgr.bindExpertTooltip();
      expect(deps.expertTooltipNode.parentElement).toBe(document.body);
      expect(deps.expertTooltipNode.classList.contains("section-tooltip-popover--floating")).toBe(true);
    });

    it("opens on mouseenter and closes on mouseleave (trigger)", () => {
      mgr.bindExpertTooltip();
      deps.expertTooltipTriggerNode.dispatchEvent(new MouseEvent("mouseenter"));
      expect(deps.expertTooltipNode.hidden).toBe(false);
      deps.expertTooltipTriggerNode.dispatchEvent(new MouseEvent("mouseleave"));
      expect(deps.expertTooltipNode.hidden).toBe(true);
    });

    it("opens on mouseenter and closes on mouseleave (tooltip node)", () => {
      mgr.bindExpertTooltip();
      deps.expertTooltipNode.dispatchEvent(new MouseEvent("mouseenter"));
      expect(deps.expertTooltipNode.hidden).toBe(false);
      deps.expertTooltipNode.dispatchEvent(new MouseEvent("mouseleave"));
      expect(deps.expertTooltipNode.hidden).toBe(true);
    });

    it("opens on focus", () => {
      mgr.bindExpertTooltip();
      deps.expertTooltipTriggerNode.dispatchEvent(new FocusEvent("focus"));
      expect(deps.expertTooltipNode.hidden).toBe(false);
    });

    it("click toggles pinned state — hover no longer closes", () => {
      mgr.bindExpertTooltip();
      // Click to pin open
      deps.expertTooltipTriggerNode.dispatchEvent(new MouseEvent("click", { bubbles: true }));
      expect(deps.expertTooltipNode.hidden).toBe(false);
      // Mouseleave should NOT close because it's pinned
      deps.expertTooltipTriggerNode.dispatchEvent(new MouseEvent("mouseleave"));
      expect(deps.expertTooltipNode.hidden).toBe(false);
    });

    it("second click unpins and closes", () => {
      mgr.bindExpertTooltip();
      deps.expertTooltipTriggerNode.dispatchEvent(new MouseEvent("click", { bubbles: true }));
      deps.expertTooltipTriggerNode.dispatchEvent(new MouseEvent("click", { bubbles: true }));
      expect(deps.expertTooltipNode.hidden).toBe(true);
    });

    it("Escape unpins tooltip and returns focus to trigger", () => {
      mgr.bindExpertTooltip();
      deps.expertTooltipTriggerNode.dispatchEvent(new MouseEvent("click", { bubbles: true }));
      expect(deps.expertTooltipNode.hidden).toBe(false);
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
      // Tooltip stays visible because focus() on trigger fires the focus handler
      // which re-opens in hover mode (unpinned). Mouseleave will now close it.
      expect(deps.expertTooltipNode.hidden).toBe(false);
      deps.expertTooltipTriggerNode.dispatchEvent(new MouseEvent("mouseleave"));
      expect(deps.expertTooltipNode.hidden).toBe(true);
    });

    it("Escape on hidden tooltip does nothing", () => {
      mgr.bindExpertTooltip();
      // Tooltip already hidden — Escape should be a no-op
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
      expect(deps.expertTooltipNode.hidden).toBe(true);
    });

    it("pointerdown outside closes pinned tooltip", () => {
      mgr.bindExpertTooltip();
      deps.expertTooltipTriggerNode.dispatchEvent(new MouseEvent("click", { bubbles: true }));
      expect(deps.expertTooltipNode.hidden).toBe(false);
      // Click somewhere outside
      const outside = document.createElement("div");
      document.body.appendChild(outside);
      document.dispatchEvent(new PointerEvent("pointerdown", { bubbles: true }));
      expect(deps.expertTooltipNode.hidden).toBe(true);
    });

    it("pointerdown inside shell does NOT close", () => {
      mgr.bindExpertTooltip();
      deps.expertTooltipTriggerNode.dispatchEvent(new MouseEvent("click", { bubbles: true }));
      // pointerdown on trigger (inside shell)
      deps.expertTooltipTriggerNode.dispatchEvent(new PointerEvent("pointerdown", { bubbles: true }));
      expect(deps.expertTooltipNode.hidden).toBe(false);
    });

    it("does not re-append tooltip if already a child of body", () => {
      document.body.appendChild(deps.expertTooltipNode);
      mgr.bindExpertTooltip();
      // Should still be in body with no duplication
      const count = Array.from(document.body.children).filter(
        (c) => c === deps.expertTooltipNode
      ).length;
      expect(count).toBe(1);
    });
  });
});
