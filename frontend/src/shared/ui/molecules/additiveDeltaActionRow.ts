/**
 * Additive-corpus-v1 action row (Phase 8).
 *
 * Preview + Apply + Cancel buttons with a confirmation modal on Apply that
 * names the delta_id + bucket counts explicitly. Double-click guarded:
 * Apply disables + swaps to a spinner after the first click until the
 * caller calls ``releaseApply()`` or the state transitions to Running.
 */

import { createButton } from "@/shared/ui/atoms/button";

export type AdditiveDeltaUiState =
  | "idle"
  | "previewed"
  | "previewed-empty"
  | "running"
  | "terminal"
  | "pending"; // intermediate after Apply POST, before job_id returns

export interface AdditiveDeltaActionRowCallbacks {
  onPreview: () => void;
  /** Opt-in deep scan. Re-classifies every doc (20-25 min, ~US$6-16 in
   * Gemini). Used after prompt/taxonomy changes when drift detection on
   * byte-identical docs matters. See plan Decision D.
   */
  onDeepPreview: () => void;
  onApply: () => void;
  onCancel: () => void;
  onReset: () => void;
}

export interface AdditiveDeltaActionRowViewModel {
  state: AdditiveDeltaUiState;
  deltaId?: string;
  counts?: { added: number; modified: number; removed: number };
}

export interface AdditiveDeltaActionRowHandle {
  element: HTMLElement;
  update: (vm: AdditiveDeltaActionRowViewModel) => void;
}

function renderConfirmModal(
  vm: AdditiveDeltaActionRowViewModel,
  onConfirm: () => void,
): HTMLElement {
  const backdrop = document.createElement("div");
  backdrop.className = "lia-adelta-modal__backdrop";
  backdrop.setAttribute("role", "dialog");
  backdrop.setAttribute("aria-modal", "true");
  backdrop.setAttribute("aria-label", "Confirmar aplicación del delta");

  const modal = document.createElement("div");
  modal.className = "lia-adelta-modal";

  const title = document.createElement("h3");
  title.className = "lia-adelta-modal__title";
  title.textContent = "Confirmar aplicación";

  const body = document.createElement("p");
  body.className = "lia-adelta-modal__body";
  const c = vm.counts ?? { added: 0, modified: 0, removed: 0 };
  body.textContent =
    `Aplicar delta ${vm.deltaId ?? "(pendiente)"} con +${c.added} / ` +
    `~${c.modified} / -${c.removed} cambios. Esto afecta producción.`;

  const actions = document.createElement("div");
  actions.className = "lia-adelta-modal__actions";

  const cancelBtn = createButton({
    label: "Cancelar",
    tone: "ghost",
    onClick: () => backdrop.remove(),
  });
  const confirmBtn = createButton({
    label: "Aplicar delta",
    tone: "primary",
    onClick: () => {
      backdrop.remove();
      onConfirm();
    },
  });

  actions.append(cancelBtn, confirmBtn);
  modal.append(title, body, actions);
  backdrop.appendChild(modal);
  return backdrop;
}

export function createAdditiveDeltaActionRow(
  initial: AdditiveDeltaActionRowViewModel,
  callbacks: AdditiveDeltaActionRowCallbacks,
): AdditiveDeltaActionRowHandle {
  const root = document.createElement("div");
  root.className = "lia-adelta-actions";
  root.setAttribute("data-lia-component", "additive-delta-actions");

  const previewBtn = createButton({
    label: "Previsualizar",
    tone: "secondary",
    onClick: () => callbacks.onPreview(),
  });
  const deepPreviewBtn = createButton({
    label: "Análisis profundo",
    tone: "ghost",
    className: "lia-adelta-action-row__deep",
    attrs: {
      title:
        "Re-clasifica los ~1.3k documentos con el LLM completo. " +
        "Úsalo cuando cambie el prompt del clasificador o la taxonomía. " +
        "Tarda 20-25 min y cuesta ~US$ 6-16 en Gemini.",
    },
    onClick: () => callbacks.onDeepPreview(),
  });
  const applyBtn = createButton({
    label: "Aplicar",
    tone: "primary",
    disabled: true,
  });
  const cancelBtn = createButton({
    label: "Cancelar",
    tone: "destructive",
    onClick: () => callbacks.onCancel(),
  });
  const resetBtn = createButton({
    label: "Nuevo delta",
    tone: "ghost",
    onClick: () => callbacks.onReset(),
  });

  applyBtn.addEventListener("click", () => {
    const vm = currentVm;
    if (vm.state !== "previewed") return;
    document.body.appendChild(renderConfirmModal(vm, () => {
      applyBtn.disabled = true;
      applyBtn.classList.add("is-pending");
      callbacks.onApply();
    }));
  });

  root.append(previewBtn, deepPreviewBtn, applyBtn, cancelBtn, resetBtn);

  let currentVm: AdditiveDeltaActionRowViewModel = initial;

  function update(vm: AdditiveDeltaActionRowViewModel): void {
    currentVm = vm;
    const { state } = vm;
    previewBtn.disabled = state === "running" || state === "pending";
    // Deep preview shares disable gating with the normal preview and
    // also hides once we're past idle/previewed — no point offering it
    // while a job is running.
    deepPreviewBtn.disabled = state === "running" || state === "pending";
    deepPreviewBtn.hidden = state === "running" || state === "terminal";
    applyBtn.disabled = state !== "previewed";
    applyBtn.classList.toggle("is-pending", state === "pending");
    cancelBtn.hidden = state !== "running" && state !== "pending";
    resetBtn.hidden = state !== "terminal";
  }

  update(initial);

  return { element: root, update };
}
