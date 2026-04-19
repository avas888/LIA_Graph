const OVERLAY_ID = "mobile-form-guide-modal";
const EMBED_PARAM = "embed=1";

function appendEmbedParam(url: string): string {
  if (!url) return url;
  if (/(^|[?&])embed=1(&|$)/.test(url)) return url;
  return url + (url.includes("?") ? "&" : "?") + EMBED_PARAM;
}

function currentOverlay(): HTMLElement | null {
  return document.getElementById(OVERLAY_ID);
}

function closeMobileFormGuideModal(): void {
  const overlay = currentOverlay();
  if (!overlay) return;
  overlay.classList.remove("is-open");
  const onEnd = () => {
    overlay.removeEventListener("transitionend", onEnd);
    overlay.remove();
    if (!document.querySelector(".mobile-sheet-overlay.is-open")) {
      document.body.style.overflow = "";
    }
  };
  overlay.addEventListener("transitionend", onEnd, { once: true });
  setTimeout(() => {
    if (!overlay.classList.contains("is-open")) {
      overlay.remove();
      if (!document.querySelector(".mobile-sheet-overlay.is-open")) {
        document.body.style.overflow = "";
      }
    }
  }, 400);
}

export function openMobileFormGuideModal(url: string, title: string): void {
  if (!url) return;
  closeMobileFormGuideModal();

  const overlay = document.createElement("div");
  overlay.id = OVERLAY_ID;
  overlay.className = "mobile-form-guide-modal-overlay";
  overlay.innerHTML = `
    <div class="mfgm-scrim"></div>
    <div class="mfgm-dialog" role="dialog" aria-modal="true" aria-label="${escapeAttr(title)}">
      <header class="mfgm-chrome">
        <span class="mfgm-title">${escapeHtml(title)}</span>
        <button type="button" class="mfgm-close" aria-label="Cerrar guía">&times;</button>
      </header>
      <iframe class="mfgm-iframe" src="${escapeAttr(appendEmbedParam(url))}" title="${escapeAttr(title)}"></iframe>
    </div>
  `;

  document.body.appendChild(overlay);
  document.body.style.overflow = "hidden";

  void overlay.offsetHeight;
  overlay.classList.add("is-open");

  overlay.querySelector(".mfgm-close")?.addEventListener("click", closeMobileFormGuideModal);
  overlay.querySelector(".mfgm-scrim")?.addEventListener("click", closeMobileFormGuideModal);
}

let delegationInstalled = false;

export function installMobileFormGuideModalDelegation(): void {
  if (delegationInstalled) return;
  delegationInstalled = true;

  document.addEventListener("click", (event) => {
    const target = event.target as HTMLElement | null;
    const trigger = target?.closest<HTMLElement>("[data-mobile-form-guide-url]");
    if (!trigger) return;
    event.preventDefault();
    const url = trigger.getAttribute("data-mobile-form-guide-url") || "";
    const title = trigger.getAttribute("data-mobile-form-guide-title") || "Guía";
    openMobileFormGuideModal(url, title);
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && currentOverlay()) {
      closeMobileFormGuideModal();
    }
  });
}

function escapeHtml(text: string): string {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function escapeAttr(text: string): string {
  return escapeHtml(text).replace(/"/g, "&quot;");
}
