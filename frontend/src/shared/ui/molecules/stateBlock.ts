export type LiaStateTone = "loading" | "empty" | "error" | "deferred" | "success";

export interface StateBlockOptions {
  className?: string;
  compact?: boolean;
  message: string;
  title?: string;
  tone: LiaStateTone;
}

export function createStateBlock({
  className = "",
  compact = false,
  message,
  title = "",
  tone,
}: StateBlockOptions): HTMLDivElement {
  const block = document.createElement("div");
  block.className = [
    "lia-state-block",
    `lia-state-block--${tone}`,
    compact ? "lia-state-block--compact" : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");
  block.setAttribute("data-lia-component", "state-block");
  block.setAttribute("role", tone === "error" ? "alert" : "status");
  block.setAttribute("aria-live", tone === "error" ? "assertive" : "polite");

  if (tone === "loading") {
    const spinner = document.createElement("span");
    spinner.className = "lia-state-block__spinner";
    spinner.setAttribute("aria-hidden", "true");
    block.appendChild(spinner);
  }

  const copy = document.createElement("div");
  copy.className = "lia-state-block__copy";

  if (title) {
    const heading = document.createElement("strong");
    heading.className = "lia-state-block__title";
    heading.textContent = title;
    copy.appendChild(heading);
  }

  const body = document.createElement("p");
  body.className = "lia-state-block__message";
  body.textContent = message;
  copy.appendChild(body);

  block.appendChild(copy);
  return block;
}
