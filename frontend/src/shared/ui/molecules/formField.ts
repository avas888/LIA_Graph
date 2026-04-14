import { createInput, type InputOptions } from "@/shared/ui/atoms/input";
import { createIconButton, type ButtonOptions } from "@/shared/ui/atoms/button";

export interface FormFieldOptions {
  className?: string;
  input: InputOptions;
  label: string;
  labelFor?: string;
  /** Optional trailing action button (e.g. password toggle). */
  trailingAction?: ButtonOptions;
}

export function createFormField({
  className = "",
  input: inputOpts,
  label,
  labelFor,
  trailingAction,
}: FormFieldOptions): HTMLDivElement {
  const wrapper = document.createElement("div");
  wrapper.className = ["lia-form-field", className].filter(Boolean).join(" ");
  wrapper.setAttribute("data-lia-component", "form-field");

  const labelEl = document.createElement("label");
  labelEl.className = "lia-form-field__label";
  labelEl.textContent = label;
  if (labelFor || inputOpts.id) {
    labelEl.htmlFor = labelFor || inputOpts.id || "";
  }
  wrapper.appendChild(labelEl);

  if (trailingAction) {
    const inputRow = document.createElement("div");
    inputRow.className = "lia-form-field__input-row";

    const input = createInput(inputOpts);
    inputRow.appendChild(input);

    const action = createIconButton({
      ...trailingAction,
      className: ["lia-form-field__trailing-action", trailingAction.className || ""].filter(Boolean).join(" "),
    });
    inputRow.appendChild(action);

    wrapper.appendChild(inputRow);
  } else {
    wrapper.appendChild(createInput(inputOpts));
  }

  return wrapper;
}
