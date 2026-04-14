export interface RelationLinkViewModel {
  docId?: string;
  title: string;
  relationLabel?: string;
  helperText?: string;
  url?: string;
}

export function createRelationLink({
  docId,
  title,
  relationLabel,
  helperText,
  url,
}: RelationLinkViewModel): HTMLElement {
  const article = document.createElement("article");
  article.className = "lia-relation-link";
  article.setAttribute("data-lia-component", "relation-link");
  if (docId) article.dataset.docId = docId;

  if (relationLabel?.trim()) {
    const label = document.createElement("p");
    label.className = "lia-relation-link__meta";
    label.textContent = relationLabel;
    article.appendChild(label);
  }

  const link = document.createElement("a");
  link.className = "lia-relation-link__title";
  link.href = url?.trim() || "#";
  link.textContent = title;
  article.appendChild(link);

  if (helperText?.trim()) {
    const helper = document.createElement("p");
    helper.className = "lia-relation-link__helper";
    helper.textContent = helperText;
    article.appendChild(helper);
  }

  return article;
}
