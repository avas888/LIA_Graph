export type LiaInputType = "text" | "email" | "password" | "number" | "tel" | "url";

export interface InputOptions {
  attrs?: Record<string, string>;
  autocomplete?: string;
  className?: string;
  dataComponent?: string;
  disabled?: boolean;
  id?: string;
  maxlength?: number;
  minlength?: number;
  name?: string;
  placeholder?: string;
  required?: boolean;
  type?: LiaInputType;
  value?: string;
}

export function createInput({
  attrs = {},
  autocomplete,
  className = "",
  dataComponent = "input",
  disabled = false,
  id,
  maxlength,
  minlength,
  name,
  placeholder = "",
  required = false,
  type = "text",
  value = "",
}: InputOptions): HTMLInputElement {
  const input = document.createElement("input");
  input.type = type;
  input.className = ["lia-input", className].filter(Boolean).join(" ");
  input.setAttribute("data-lia-component", dataComponent);
  if (id) input.id = id;
  if (name) input.name = name;
  if (placeholder) input.placeholder = placeholder;
  if (value) input.value = value;
  if (required) input.required = true;
  if (disabled) input.disabled = true;
  if (autocomplete) input.autocomplete = autocomplete;
  if (minlength != null) input.minLength = minlength;
  if (maxlength != null) input.maxLength = maxlength;
  for (const [k, v] of Object.entries(attrs)) {
    input.setAttribute(k, v);
  }
  return input;
}

export interface TextareaOptions {
  attrs?: Record<string, string>;
  className?: string;
  dataComponent?: string;
  disabled?: boolean;
  id?: string;
  maxlength?: number;
  name?: string;
  placeholder?: string;
  required?: boolean;
  rows?: number;
  value?: string;
}

export function createTextarea({
  attrs = {},
  className = "",
  dataComponent = "textarea",
  disabled = false,
  id,
  maxlength,
  name,
  placeholder = "",
  required = false,
  rows = 3,
  value = "",
}: TextareaOptions): HTMLTextAreaElement {
  const textarea = document.createElement("textarea");
  textarea.className = ["lia-input lia-textarea", className].filter(Boolean).join(" ");
  textarea.setAttribute("data-lia-component", dataComponent);
  if (id) textarea.id = id;
  if (name) textarea.name = name;
  if (placeholder) textarea.placeholder = placeholder;
  if (value) textarea.value = value;
  if (required) textarea.required = true;
  if (disabled) textarea.disabled = true;
  if (rows) textarea.rows = rows;
  if (maxlength != null) textarea.maxLength = maxlength;
  for (const [k, v] of Object.entries(attrs)) {
    textarea.setAttribute(k, v);
  }
  return textarea;
}
