export interface NormativeSectionViewModel {
  id: string;
  title: string;
  body: string;
}

export function createNormativeSection(
  { id, title, body }: NormativeSectionViewModel,
  onRenderBody?: (container: HTMLElement, markdown: string) => Promise<void>,
): HTMLElement {
  const article = document.createElement("article");
  article.className = "lia-normative-section";
  article.setAttribute("data-lia-component", "normative-section");
  article.dataset.sectionId = id;

  const titleEl = document.createElement("h2");
  titleEl.className = "lia-normative-section__title";
  titleEl.textContent = title;

  const bodyEl = document.createElement("div");
  bodyEl.className = "lia-normative-section__body";

  article.append(titleEl, bodyEl);

  if (onRenderBody) {
    void onRenderBody(bodyEl, body);
  } else {
    bodyEl.textContent = body;
  }

  return article;
}
