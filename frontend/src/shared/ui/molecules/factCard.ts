export interface FactCardViewModel {
  label: string;
  value: string;
}

export function createFactCard({ label, value }: FactCardViewModel): HTMLElement {
  const article = document.createElement("article");
  article.className = "lia-fact-card";
  article.setAttribute("data-lia-component", "fact-card");

  const labelEl = document.createElement("p");
  labelEl.className = "lia-fact-card__label";
  labelEl.textContent = label;

  const valueEl = document.createElement("p");
  valueEl.className = "lia-fact-card__value";
  valueEl.textContent = value;

  article.append(labelEl, valueEl);
  return article;
}
