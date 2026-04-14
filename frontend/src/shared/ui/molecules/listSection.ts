export interface ListSectionHeadingOptions {
  className?: string;
  countText?: string;
  dataComponent?: string;
  label: string;
  tagName?: keyof HTMLElementTagNameMap;
}

export function createListSectionHeading({
  className = "",
  countText = "",
  dataComponent = "list-section-heading",
  label,
  tagName = "div",
}: ListSectionHeadingOptions): HTMLElement {
  const heading = document.createElement(tagName);
  heading.className = ["lia-list-section-heading", className].filter(Boolean).join(" ");
  heading.setAttribute("data-lia-component", dataComponent);

  const labelNode = document.createElement("span");
  labelNode.className = "lia-list-section-heading__label";
  labelNode.textContent = label;
  heading.appendChild(labelNode);

  if (countText) {
    const countNode = document.createElement("span");
    countNode.className = "lia-list-section-heading__count";
    countNode.textContent = countText;
    heading.appendChild(countNode);
  }

  return heading;
}
