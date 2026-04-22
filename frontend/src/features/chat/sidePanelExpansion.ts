import { getLocalStorage } from "@/shared/browser/storage";

export type SidePanelState = "idle" | "normativa" | "expertos";

const STORAGE_KEY = "lia_side_panel_expansion_v1";
const VALID_STATES: readonly SidePanelState[] = ["idle", "normativa", "expertos"];

function isValidState(value: string | null): value is SidePanelState {
  return value !== null && (VALID_STATES as readonly string[]).includes(value);
}

export function initSidePanelExpansion(sidePanelEl: HTMLElement): () => void {
  const storage = getLocalStorage();

  function readPersisted(): SidePanelState {
    try {
      const raw = storage.getItem(STORAGE_KEY);
      return isValidState(raw) ? raw : "idle";
    } catch {
      return "idle";
    }
  }

  function persist(state: SidePanelState): void {
    try {
      if (state === "idle") storage.removeItem(STORAGE_KEY);
      else storage.setItem(STORAGE_KEY, state);
    } catch {}
  }

  function applyState(state: SidePanelState): void {
    sidePanelEl.dataset.sidePanelExpansion = state;

    const expandButtons = sidePanelEl.querySelectorAll<HTMLButtonElement>(
      "[data-side-panel-target]",
    );
    expandButtons.forEach((btn) => {
      const target = btn.dataset.sidePanelTarget as SidePanelState | undefined;
      const isActive = target === state;
      btn.setAttribute("aria-pressed", String(isActive));
    });

    const restoreHints = sidePanelEl.querySelectorAll<HTMLButtonElement>(
      "[data-side-panel-restore]",
    );
    restoreHints.forEach((hint) => {
      const which = hint.dataset.sidePanelRestore as SidePanelState | undefined;
      const isCollapsed = state !== "idle" && which !== undefined && which !== state;
      hint.hidden = !isCollapsed;
      hint.tabIndex = isCollapsed ? 0 : -1;
    });
  }

  function setState(next: SidePanelState): void {
    applyState(next);
    persist(next);
  }

  function onExpandClick(event: Event): void {
    const button = (event.target as HTMLElement)?.closest<HTMLButtonElement>(
      "[data-side-panel-target]",
    );
    if (!button || !sidePanelEl.contains(button)) return;
    const target = button.dataset.sidePanelTarget as SidePanelState | undefined;
    if (!target || target === "idle") return;
    const current = (sidePanelEl.dataset.sidePanelExpansion ?? "idle") as SidePanelState;
    setState(current === target ? "idle" : target);
  }

  function onRestoreClick(event: Event): void {
    const hint = (event.target as HTMLElement)?.closest<HTMLButtonElement>(
      "[data-side-panel-restore]",
    );
    if (!hint || !sidePanelEl.contains(hint) || hint.hidden) return;
    setState("idle");
  }

  sidePanelEl.addEventListener("click", onExpandClick);
  sidePanelEl.addEventListener("click", onRestoreClick);

  applyState(readPersisted());

  return function dispose(): void {
    sidePanelEl.removeEventListener("click", onExpandClick);
    sidePanelEl.removeEventListener("click", onRestoreClick);
  };
}
