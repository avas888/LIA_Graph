import { LiaThinkingAnimation } from "@/shared/async/liaThinkingAnimation";

export interface ThinkingOverlayController {
  start: () => void;
  stop: () => void;
  reset: () => void;
  prime: () => void;
  withTask: <T>(task: () => Promise<T>) => Promise<T>;
}

let singleton: ThinkingOverlayController | null = null;

export function getThinkingOverlay(): ThinkingOverlayController {
  if (singleton) return singleton;

  let activeRequests = 0;
  let showDelayTimer: number | null = null;
  let failsafeTimer: number | null = null;
  let isVisible = false;

  let overlayNode: HTMLDivElement | null = null;
  let liaAnimation: LiaThinkingAnimation | null = null;

  function ensureOverlay(): void {
    if (overlayNode) return;

    overlayNode = document.getElementById("lia-thinking-overlay") as HTMLDivElement | null;
    if (!overlayNode) {
      overlayNode = document.createElement("div");
      overlayNode.id = "lia-thinking-overlay";
      overlayNode.className = "lia-thinking-overlay";
      overlayNode.hidden = true;
      overlayNode.innerHTML = `
        <div class="lia-thinking-card" role="status" aria-live="polite" aria-atomic="true">
          <div id="lia-thinking-poses" aria-hidden="true"></div>
        </div>
      `;
      // Scope to .chat-panel so tabs/side-panel remain interactive
      const chatPanel = document.querySelector(".chat-panel");
      (chatPanel || document.body).appendChild(overlayNode);
    }

    if (!liaAnimation) {
      const posesEl = document.getElementById("lia-thinking-poses");
      if (posesEl) {
        liaAnimation = new LiaThinkingAnimation("lia-thinking-poses", 2500);
        liaAnimation.init();
      }
    }
  }

  function clearTimers(): void {
    if (failsafeTimer !== null) {
      window.clearTimeout(failsafeTimer);
      failsafeTimer = null;
    }
  }

  function showNow(): void {
    ensureOverlay();
    if (!overlayNode || isVisible) return;
    isVisible = true;
    overlayNode.hidden = false;
    overlayNode.classList.add("is-visible");
    liaAnimation?.start();

    failsafeTimer = window.setTimeout(() => {
      activeRequests = 0;
      hideNow();
      console.warn("Thinking overlay reset by failsafe timeout.");
    }, 45000);
  }

  function hideNow(): void {
    if (!overlayNode || !isVisible) return;
    isVisible = false;
    overlayNode.classList.remove("is-visible");
    overlayNode.hidden = true;
    liaAnimation?.stop();
    clearTimers();
  }

  function start(): void {
    activeRequests += 1;
    if (activeRequests !== 1) return;
    if (showDelayTimer !== null) {
      window.clearTimeout(showDelayTimer);
    }
    showDelayTimer = window.setTimeout(() => {
      showDelayTimer = null;
      if (activeRequests > 0) {
        showNow();
      }
    }, 140);
  }

  function stop(): void {
    activeRequests = Math.max(0, activeRequests - 1);
    if (activeRequests > 0) return;
    if (showDelayTimer !== null) {
      window.clearTimeout(showDelayTimer);
      showDelayTimer = null;
    }
    hideNow();
  }

  async function withTask<T>(task: () => Promise<T>): Promise<T> {
    start();
    try {
      return await task();
    } finally {
      stop();
    }
  }

  singleton = {
    start,
    stop,
    prime() {
      ensureOverlay();
    },
    withTask,
    reset() {
      activeRequests = 0;
      if (showDelayTimer !== null) {
        window.clearTimeout(showDelayTimer);
        showDelayTimer = null;
      }
      hideNow();
    },
  };

  // Build the hidden overlay immediately so the mascot assets begin loading
  // before the user's first request finishes.
  ensureOverlay();

  return singleton;
}
