import { getLocalStorage } from "@/shared/browser/storage";

const STORAGE_KEY = "lia_chat_splitter_v4";
const MIN_CHAT_PX = 360;
const MIN_SIDE_PX = 280;

export function initSplitter(layoutEl: HTMLElement, splitterEl: HTMLElement): void {
  const storage = getLocalStorage();
  let dragging = false;
  let startX = 0;
  let startChatWidth = 0;
  const gap = parseFloat(getComputedStyle(layoutEl).columnGap) || 16;

  function applySplit(chatWidth: number): void {
    const available = layoutEl.clientWidth - splitterEl.offsetWidth - gap * 2;
    const clamped = Math.max(MIN_CHAT_PX, Math.min(chatWidth, available - MIN_SIDE_PX));
    layoutEl.style.gridTemplateColumns = `${clamped}px 6px minmax(0, 1fr)`;
    try {
      storage.setItem(STORAGE_KEY, String(clamped));
    } catch {}
  }

  function resetSplit(): void {
    layoutEl.style.gridTemplateColumns = "";
    try {
      storage.removeItem(STORAGE_KEY);
    } catch {}
  }

  function restoreSplit(): void {
    const saved = storage.getItem(STORAGE_KEY);
    if (saved) {
      const parsed = Number(saved);
      if (Number.isFinite(parsed) && parsed > 0) {
        applySplit(parsed);
        return;
      }
    }
    // No saved preference — let CSS 1fr/1fr (50/50) default apply.
  }

  function onPointerDown(e: PointerEvent): void {
    if (e.button !== 0) return;
    e.preventDefault();
    dragging = true;
    startX = e.clientX;
    const chatPanel = layoutEl.querySelector<HTMLElement>(".chat-panel");
    startChatWidth = chatPanel ? chatPanel.offsetWidth : layoutEl.clientWidth * 0.5;
    splitterEl.setPointerCapture(e.pointerId);
    splitterEl.classList.add("is-dragging");
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  }

  function onPointerMove(e: PointerEvent): void {
    if (!dragging) return;
    const delta = e.clientX - startX;
    applySplit(startChatWidth + delta);
  }

  function onPointerUp(e: PointerEvent): void {
    if (!dragging) return;
    dragging = false;
    splitterEl.releasePointerCapture(e.pointerId);
    splitterEl.classList.remove("is-dragging");
    document.body.style.cursor = "";
    document.body.style.userSelect = "";
  }

  function onKeyDown(e: KeyboardEvent): void {
    const step = e.shiftKey ? 60 : 20;
    const chatPanel = layoutEl.querySelector<HTMLElement>(".chat-panel");
    const current = chatPanel ? chatPanel.offsetWidth : layoutEl.clientWidth * 0.5;
    if (e.key === "ArrowLeft") {
      e.preventDefault();
      applySplit(current - step);
    } else if (e.key === "ArrowRight") {
      e.preventDefault();
      applySplit(current + step);
    } else if (e.key === "Home") {
      e.preventDefault();
      resetSplit();
    }
  }

  splitterEl.addEventListener("pointerdown", onPointerDown);
  splitterEl.addEventListener("pointermove", onPointerMove);
  splitterEl.addEventListener("pointerup", onPointerUp);
  splitterEl.addEventListener("pointercancel", onPointerUp);
  splitterEl.addEventListener("dblclick", resetSplit);
  splitterEl.addEventListener("keydown", onKeyDown);

  restoreSplit();
}
