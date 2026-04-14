export interface TimelineItemViewModel {
  id: string;
  label: string;
  date?: string;
  detail?: string;
}

export function createTimelineItem(
  { id, label, date, detail }: TimelineItemViewModel,
  unconfirmedDateLabel = "",
): HTMLElement {
  const article = document.createElement("article");
  article.className = "lia-timeline-item";
  article.setAttribute("data-lia-component", "timeline-item");
  article.dataset.eventId = id;

  const labelEl = document.createElement("h3");
  labelEl.className = "lia-timeline-item__label";
  labelEl.textContent = label;

  const dateEl = document.createElement("p");
  dateEl.className = "lia-timeline-item__meta";
  dateEl.textContent = date?.trim() || unconfirmedDateLabel;

  article.append(labelEl, dateEl);

  if (detail?.trim()) {
    const detailEl = document.createElement("p");
    detailEl.className = "lia-timeline-item__detail";
    detailEl.textContent = detail;
    article.appendChild(detailEl);
  }

  return article;
}
