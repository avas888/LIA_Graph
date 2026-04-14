export type LiaButtonTone = "primary" | "secondary" | "destructive" | "ghost";

interface BaseButtonOptions {
  attrs?: Record<string, string>;
  className?: string;
  dataComponent?: string;
  disabled?: boolean;
  iconHtml?: string;
  label?: string;
  tone?: LiaButtonTone;
}

export interface ButtonOptions extends BaseButtonOptions {
  onClick?: ((event: MouseEvent) => void) | null;
  type?: "button" | "submit" | "reset";
}

export interface LinkActionOptions extends BaseButtonOptions {
  href: string;
  rel?: string;
  target?: "_blank" | "_self" | "_parent" | "_top";
}

function applyCommonAttributes(
  element: HTMLElement,
  {
    attrs = {},
    className = "",
    dataComponent = "button",
    disabled = false,
    iconHtml = "",
    label = "",
    tone = "secondary",
  }: BaseButtonOptions,
): void {
  element.className = ["lia-btn", `lia-btn--${tone}`, className].filter(Boolean).join(" ");
  element.setAttribute("data-lia-component", dataComponent);
  for (const [name, value] of Object.entries(attrs)) {
    element.setAttribute(name, value);
  }
  if ("disabled" in element) {
    (element as HTMLButtonElement).disabled = disabled;
  }
  if (iconHtml) {
    const icon = document.createElement("span");
    icon.className = "lia-btn__icon";
    icon.setAttribute("aria-hidden", "true");
    icon.innerHTML = iconHtml;
    element.appendChild(icon);
  }
  if (label) {
    const text = document.createElement("span");
    text.className = "lia-btn__label";
    text.textContent = label;
    element.appendChild(text);
  }
}

export function createButton({
  onClick = null,
  type = "button",
  ...options
}: ButtonOptions): HTMLButtonElement {
  const button = document.createElement("button");
  button.type = type;
  applyCommonAttributes(button, options);
  if (onClick) {
    button.addEventListener("click", onClick);
  }
  return button;
}

export function createIconButton(options: ButtonOptions): HTMLButtonElement {
  return createButton({
    ...options,
    className: ["lia-btn--icon", options.className || ""].filter(Boolean).join(" "),
    dataComponent: options.dataComponent || "icon-button",
  });
}

export function createLinkAction({
  href,
  rel = "noopener noreferrer",
  target = "_blank",
  ...options
}: LinkActionOptions): HTMLAnchorElement {
  const anchor = document.createElement("a");
  anchor.href = href;
  anchor.rel = rel;
  anchor.target = target;
  applyCommonAttributes(anchor, {
    ...options,
    dataComponent: options.dataComponent || "link-action",
  });
  return anchor;
}
