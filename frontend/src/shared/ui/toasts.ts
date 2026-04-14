import type { I18nRuntime } from "@/shared/i18n";
import { icons } from "@/shared/ui/icons";

type ToastTone = "info" | "success" | "error" | "caution";

interface ShowToastOptions {
  title?: string;
  message: string;
  tone?: ToastTone;
  durationMs?: number;
}

interface ConfirmToastOptions {
  title?: string;
  message: string;
  tone?: Extract<ToastTone, "caution" | "error">;
  confirmLabel?: string;
  cancelLabel?: string;
}

interface ToastController {
  show: (options: ShowToastOptions) => void;
  confirm: (options: ConfirmToastOptions) => Promise<boolean>;
}

const TOAST_HOST_ID = "lia-toast-host";

const TONE_ICONS: Record<ToastTone, string> = {
  info:    icons.info,
  success: icons.checkCircle,
  error:   icons.error,
  caution: icons.warning,
};

function toneIcon(tone: ToastTone): string {
  return TONE_ICONS[tone] || TONE_ICONS.info;
}

let sharedController: ToastController | null = null;

function ensureToastHost(i18n: I18nRuntime): HTMLElement {
  const existing = document.getElementById(TOAST_HOST_ID);
  if (existing instanceof HTMLElement) {
    existing.setAttribute("aria-label", i18n.t("toast.host.label"));
    return existing;
  }

  const host = document.createElement("section");
  host.id = TOAST_HOST_ID;
  host.className = "lia-toast-host";
  host.setAttribute("aria-label", i18n.t("toast.host.label"));
  document.body.appendChild(host);
  return host;
}

function createToastNode({
  i18n,
  title = "",
  message,
  tone = "info",
}: {
  i18n: I18nRuntime;
  title?: string;
  message: string;
  tone?: ToastTone;
}): HTMLDivElement {
  const toast = document.createElement("div");
  toast.className = "lia-toast";
  toast.dataset.tone = tone;

  const iconWrap = document.createElement("span");
  iconWrap.className = "lia-toast-icon";
  iconWrap.innerHTML = toneIcon(tone);

  const body = document.createElement("div");
  body.className = "lia-toast-body";

  if (String(title || "").trim()) {
    const titleNode = document.createElement("p");
    titleNode.className = "lia-toast-title";
    titleNode.textContent = String(title).trim();
    body.appendChild(titleNode);
  }

  const messageNode = document.createElement("p");
  messageNode.className = "lia-toast-message";
  messageNode.textContent = String(message || "").trim();
  body.appendChild(messageNode);

  const dismissBtn = document.createElement("button");
  dismissBtn.type = "button";
  dismissBtn.className = "lia-toast-dismiss";
  dismissBtn.setAttribute("aria-label", i18n.t("toast.dismiss"));
  dismissBtn.innerHTML = icons.close;

  toast.appendChild(iconWrap);
  toast.appendChild(body);
  toast.appendChild(dismissBtn);
  return toast;
}

export function getToastController(i18n: I18nRuntime): ToastController {
  if (sharedController) {
    ensureToastHost(i18n);
    return sharedController;
  }

  let activeConfirmCleanup: (() => void) | null = null;

  function show({ title = "", message, tone = "info", durationMs = 4200 }: ShowToastOptions): void {
    const cleanMessage = String(message || "").trim();
    if (!cleanMessage) return;

    const host = ensureToastHost(i18n);
    const toast = createToastNode({ i18n, title, message: cleanMessage, tone });
    toast.setAttribute("role", tone === "error" || tone === "caution" ? "alert" : "status");
    toast.setAttribute("aria-live", tone === "error" || tone === "caution" ? "assertive" : "polite");

    const dismissBtn = toast.querySelector<HTMLButtonElement>(".lia-toast-dismiss");
    const teardown = () => {
      window.clearTimeout(timeoutId);
      toast.remove();
    };
    const timeoutId = window.setTimeout(teardown, Math.max(1200, Number(durationMs) || 4200));
    dismissBtn?.addEventListener("click", teardown, { once: true });

    host.prepend(toast);
  }

  async function confirm({
    title = "",
    message,
    tone = "caution",
    confirmLabel,
    cancelLabel,
  }: ConfirmToastOptions): Promise<boolean> {
    const cleanMessage = String(message || "").trim();
    if (!cleanMessage) return false;

    if (activeConfirmCleanup) {
      activeConfirmCleanup();
      activeConfirmCleanup = null;
    }

    const host = ensureToastHost(i18n);
    const toast = createToastNode({ i18n, title, message: cleanMessage, tone });
    toast.classList.add("is-sticky");
    toast.setAttribute("role", "alertdialog");
    toast.setAttribute("aria-live", "assertive");

    const actions = document.createElement("div");
    actions.className = "lia-toast-actions";

    const cancelBtn = document.createElement("button");
    cancelBtn.type = "button";
    cancelBtn.className = "lia-toast-action lia-toast-action-secondary";
    cancelBtn.textContent = String(cancelLabel || i18n.t("toast.action.cancel")).trim();

    const confirmBtn = document.createElement("button");
    confirmBtn.type = "button";
    confirmBtn.className = "lia-toast-action lia-toast-action-primary";
    confirmBtn.textContent = String(confirmLabel || i18n.t("toast.action.confirm")).trim();

    actions.appendChild(cancelBtn);
    actions.appendChild(confirmBtn);
    toast.appendChild(actions);
    host.prepend(toast);

    const dismissBtn = toast.querySelector<HTMLButtonElement>(".lia-toast-dismiss");

    return await new Promise<boolean>((resolve) => {
      let settled = false;
      const finish = (value: boolean) => {
        if (settled) return;
        settled = true;
        cleanup();
        resolve(value);
      };

      const cleanup = () => {
        cancelBtn.removeEventListener("click", handleCancel);
        confirmBtn.removeEventListener("click", handleConfirm);
        dismissBtn?.removeEventListener("click", handleCancel);
        toast.remove();
        if (activeConfirmCleanup === cleanup) {
          activeConfirmCleanup = null;
        }
      };

      const handleCancel = () => finish(false);
      const handleConfirm = () => finish(true);

      activeConfirmCleanup = () => finish(false);

      cancelBtn.addEventListener("click", handleCancel);
      confirmBtn.addEventListener("click", handleConfirm);
      dismissBtn?.addEventListener("click", handleCancel);

      window.setTimeout(() => {
        confirmBtn.focus({ preventScroll: true });
      }, 0);
    });
  }

  sharedController = {
    show,
    confirm,
  };

  ensureToastHost(i18n);
  return sharedController;
}
