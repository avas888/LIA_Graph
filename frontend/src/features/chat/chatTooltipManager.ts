// @ts-nocheck

/**
 * Expert tooltip positioning and interaction manager.
 * Extracted from chatApp.ts during decouple-v1 Phase 2.
 */

export interface TooltipManagerDeps {
  expertTooltipNode: HTMLElement;
  expertTooltipShellNode: HTMLElement;
  expertTooltipTriggerNode: HTMLElement;
}

export function createTooltipManager(deps: TooltipManagerDeps) {
  const { expertTooltipNode, expertTooltipShellNode, expertTooltipTriggerNode } = deps;

  let expertTooltipPinned = false;

  function setExpertTooltipOpen(open) {
    expertTooltipNode.hidden = !open;
    expertTooltipTriggerNode.setAttribute("aria-expanded", String(open));
    if (open) {
      updateExpertTooltipPosition();
    }
  }

  function updateExpertTooltipPosition() {
    if (expertTooltipNode.hidden) return;
    const triggerRect = expertTooltipTriggerNode.getBoundingClientRect();
    const tooltipRect = expertTooltipNode.getBoundingClientRect();
    const gap = 10;
    const margin = 16;
    let top = triggerRect.top - tooltipRect.height - gap;
    if (top < margin) {
      top = Math.min(window.innerHeight - tooltipRect.height - margin, triggerRect.bottom + gap);
    }
    let left = triggerRect.left;
    if (left + tooltipRect.width > window.innerWidth - margin) {
      left = window.innerWidth - tooltipRect.width - margin;
    }
    left = Math.max(margin, left);
    expertTooltipNode.style.top = `${Math.max(margin, top)}px`;
    expertTooltipNode.style.left = `${left}px`;
  }

  function bindExpertTooltip() {
    expertTooltipNode.classList.add("section-tooltip-popover--floating");
    if (expertTooltipNode.parentElement !== document.body) {
      document.body.appendChild(expertTooltipNode);
    }
    const openHover = () => {
      if (expertTooltipPinned) return;
      setExpertTooltipOpen(true);
    };
    const closeHover = () => {
      if (expertTooltipPinned) return;
      setExpertTooltipOpen(false);
    };
    const closePinned = () => {
      expertTooltipPinned = false;
      setExpertTooltipOpen(false);
    };

    expertTooltipTriggerNode.addEventListener("mouseenter", openHover);
    expertTooltipTriggerNode.addEventListener("mouseleave", closeHover);
    expertTooltipNode.addEventListener("mouseenter", openHover);
    expertTooltipNode.addEventListener("mouseleave", closeHover);
    expertTooltipTriggerNode.addEventListener("focus", () => setExpertTooltipOpen(true));
    expertTooltipTriggerNode.addEventListener("click", (event) => {
      event.preventDefault();
      expertTooltipPinned = !expertTooltipPinned;
      setExpertTooltipOpen(expertTooltipPinned || document.activeElement === expertTooltipTriggerNode);
    });
    expertTooltipTriggerNode.addEventListener("blur", () => {
      window.setTimeout(() => {
        if (document.activeElement === expertTooltipTriggerNode) return;
        closeHover();
      }, 0);
    });
    document.addEventListener("pointerdown", (event) => {
      const target = event.target;
      if (!(target instanceof Node)) return;
      if (expertTooltipShellNode.contains(target) || expertTooltipNode.contains(target)) return;
      closePinned();
    });
    window.addEventListener("keydown", (event) => {
      if (event.key !== "Escape") return;
      if (expertTooltipNode.hidden) return;
      closePinned();
      if (document.activeElement !== expertTooltipTriggerNode) {
        expertTooltipTriggerNode.focus();
      }
    });
    window.addEventListener("resize", updateExpertTooltipPosition);
    window.addEventListener("scroll", updateExpertTooltipPosition, true);
  }

  return { setExpertTooltipOpen, updateExpertTooltipPosition, bindExpertTooltip };
}
