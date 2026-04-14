export interface MobileSheet {
  open(opts: { title: string; subtitle?: string; html: string }): void;
  replaceContent(html: string): void;
  close(): void;
  isOpen(): boolean;
}

/**
 * Generic bottom sheet component.
 * Supports open/close, swipe-down gesture, and overlay dismiss.
 */
export function mountMobileSheet(root: HTMLElement): MobileSheet {
  const overlay = root.querySelector<HTMLElement>(".mobile-sheet-overlay")!;
  const sheet = overlay.querySelector<HTMLElement>(".mobile-sheet")!;
  const scrim = overlay.querySelector<HTMLElement>(".mobile-sheet-scrim")!;
  const titleEl = overlay.querySelector<HTMLElement>(".mobile-sheet-title")!;
  const subtitleEl = overlay.querySelector<HTMLElement>(".mobile-sheet-subtitle")!;
  const closeBtn = overlay.querySelector<HTMLButtonElement>(".mobile-sheet-close")!;
  const contentEl = overlay.querySelector<HTMLElement>(".mobile-sheet-content")!;
  const handle = overlay.querySelector<HTMLElement>(".mobile-sheet-handle")!;

  let _isOpen = false;
  let dragStartY = 0;
  let dragging = false;

  function open(opts: { title: string; subtitle?: string; html: string }): void {
    titleEl.textContent = opts.title;
    subtitleEl.textContent = opts.subtitle ?? "";
    subtitleEl.hidden = !opts.subtitle;
    contentEl.innerHTML = opts.html;

    overlay.hidden = false;
    // Force reflow so CSS transition triggers
    void overlay.offsetHeight;
    overlay.classList.add("is-open");
    _isOpen = true;
    document.body.style.overflow = "hidden";
  }

  function replaceContent(html: string): void {
    contentEl.innerHTML = html;
    contentEl.scrollTop = 0;
  }

  function close(): void {
    overlay.classList.remove("is-open");
    _isOpen = false;
    document.body.style.overflow = "";
    sheet.style.transform = "";
    const onEnd = () => {
      overlay.hidden = true;
      contentEl.innerHTML = "";
      overlay.removeEventListener("transitionend", onEnd);
    };
    overlay.addEventListener("transitionend", onEnd, { once: true });
    // Fallback if no transition fires
    setTimeout(() => {
      if (!_isOpen) {
        overlay.hidden = true;
      }
    }, 400);
  }

  function isOpen(): boolean {
    return _isOpen;
  }

  // ── Close triggers ──────────────────────────────────────

  closeBtn.addEventListener("click", close);
  scrim.addEventListener("click", close);

  // ── Swipe-down gesture on handle ────────────────────────

  handle.addEventListener(
    "touchstart",
    (e: TouchEvent) => {
      dragStartY = e.touches[0].clientY;
      dragging = true;
      sheet.style.transition = "none";
    },
    { passive: true },
  );

  document.addEventListener(
    "touchmove",
    (e: TouchEvent) => {
      if (!dragging || !_isOpen) return;
      const dy = e.touches[0].clientY - dragStartY;
      if (dy > 0) {
        sheet.style.transform = `translateY(${dy}px)`;
      }
    },
    { passive: true },
  );

  document.addEventListener("touchend", () => {
    if (!dragging) return;
    dragging = false;
    sheet.style.transition = "";
    const currentTransform = sheet.style.transform;
    const match = currentTransform.match(/translateY\((\d+)px\)/);
    const dy = match ? parseInt(match[1], 10) : 0;
    if (dy > 100) {
      close();
    } else {
      sheet.style.transform = "";
    }
  });

  // Escape key
  document.addEventListener("keydown", (e: KeyboardEvent) => {
    if (e.key === "Escape" && _isOpen) close();
  });

  return { open, replaceContent, close, isOpen };
}
