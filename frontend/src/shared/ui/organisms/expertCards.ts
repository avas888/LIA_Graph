import { createListSectionHeading } from "@/shared/ui/molecules/listSection";

export type ExpertCardClassification =
  | "concordancia"
  | "divergencia"
  | "complementario"
  | "individual";

export type ExpertSignal = "permite" | "restringe" | "condiciona" | "neutral";

export interface ExpertCardViewModel {
  articleLabel: string;
  classification: ExpertCardClassification;
  classificationLabel: string;
  heading: string;
  hidden?: boolean;
  id: string;
  nutshell?: string | null;
  providerLabels: string[];
  providerOverflowLabel?: string | null;
  relevancia?: string | null;
  signal: ExpertSignal;
  signalLabel: string;
  sourceCountLabel: string;
}

const MOBILE_GROUP_ORDER: ExpertCardClassification[] = [
  "concordancia",
  "complementario",
  "divergencia",
  "individual",
];

function createProviderChip(label: string): HTMLSpanElement {
  const chip = document.createElement("span");
  chip.className = "expert-card-chip expert-card-chip--provider lia-chip lia-chip--neutral lia-chip--soft";
  chip.setAttribute("data-lia-component", "expert-provider-chip");
  chip.textContent = label;
  return chip;
}

function createDesktopExpertCard(
  card: ExpertCardViewModel,
  onCardClick?: ((card: ExpertCardViewModel) => void) | null,
): HTMLButtonElement {
  const button = document.createElement("button");
  button.type = "button";
  button.className = `expert-card expert-card--${card.classification}`;
  button.setAttribute("aria-label", card.heading);
  button.setAttribute("data-lia-component", "expert-card");
  button.dataset.cardId = card.id;
  button.hidden = Boolean(card.hidden);

  const header = document.createElement("div");
  header.className = "expert-card-header";

  if (card.classification !== "individual" || card.providerLabels.length === 0) {
    const classificationChip = document.createElement("span");
    classificationChip.className = `expert-card-chip expert-card-chip--${card.classification}`;
    classificationChip.textContent = card.classificationLabel;
    header.appendChild(classificationChip);
  }

  if (card.articleLabel) {
    const articleChip = document.createElement("span");
    articleChip.className = "expert-card-chip expert-card-chip--article";
    articleChip.textContent = card.articleLabel;
    header.appendChild(articleChip);
  }

  for (const provider of card.providerLabels) {
    header.appendChild(createProviderChip(provider));
  }

  if (card.providerOverflowLabel) {
    const overflow = createProviderChip(card.providerOverflowLabel);
    overflow.classList.add("expert-card-chip--provider-overflow");
    header.appendChild(overflow);
  }

  if (card.signal !== "neutral" && card.signalLabel) {
    const signalChip = document.createElement("span");
    signalChip.className = `expert-card-chip expert-card-chip--signal expert-card-chip--signal-${card.signal}`;
    signalChip.textContent = card.signalLabel;
    header.appendChild(signalChip);
  }

  const relevancia = document.createElement("p");
  relevancia.className = "expert-card-relevancia";
  relevancia.hidden = !card.relevancia;
  if (card.relevancia) {
    relevancia.textContent = card.relevancia;
    relevancia.classList.add("expert-card-relevancia--visible");
  }

  const title = document.createElement("h3");
  title.className = "expert-card-title";
  title.textContent = card.heading;
  title.hidden = Boolean(card.nutshell);

  const nutshell = document.createElement("p");
  nutshell.className = "expert-card-nutshell";
  nutshell.hidden = !card.nutshell;
  if (card.nutshell) {
    nutshell.textContent = card.nutshell;
    nutshell.classList.add("expert-card-nutshell--visible");
  }

  const footer = document.createElement("div");
  footer.className = "expert-card-footer";
  const meta = document.createElement("span");
  meta.className = "expert-card-footer-meta";
  meta.textContent = card.sourceCountLabel;
  const open = document.createElement("span");
  open.className = "expert-card-open";
  open.textContent = "Ver m\u00e1s \u203A";
  footer.append(meta, open);

  button.append(header, relevancia, title, nutshell, footer);
  if (onCardClick) {
    button.addEventListener("click", () => onCardClick(card));
  }
  return button;
}

export function renderExpertCardList(
  container: HTMLElement,
  cards: ExpertCardViewModel[],
  options: {
    onCardClick?: ((card: ExpertCardViewModel) => void) | null;
  } = {},
): void {
  container.replaceChildren();
  const fragment = document.createDocumentFragment();
  for (const card of cards) {
    fragment.appendChild(createDesktopExpertCard(card, options.onCardClick || null));
  }
  container.appendChild(fragment);
}

function createMobileExpertCard(card: ExpertCardViewModel): HTMLDivElement {
  const mobileCard = document.createElement("div");
  mobileCard.className = "mobile-interp-card";
  mobileCard.setAttribute("data-lia-component", "mobile-expert-card");
  mobileCard.dataset.cardId = card.id;
  mobileCard.dataset.classification = card.classification;
  mobileCard.setAttribute("role", "button");
  mobileCard.tabIndex = 0;

  const header = document.createElement("div");
  header.className = "mobile-interp-card-header";

  const ref = document.createElement("span");
  ref.className = "mobile-interp-card-ref";
  ref.textContent = card.articleLabel;
  header.appendChild(ref);

  if (card.signalLabel) {
    const signal = document.createElement("span");
    signal.className = "mobile-interp-card-signal";
    signal.dataset.signal = card.signal;
    signal.textContent = card.signalLabel;
    header.appendChild(signal);
  }

  // Layer 1: Why this interpretation is relevant
  if (card.relevancia) {
    const relevancia = document.createElement("p");
    relevancia.className = "mobile-interp-card-desc";
    const label = document.createElement("strong");
    label.textContent = "Posible relevancia: ";
    const summary = document.createElement("em");
    summary.style.fontWeight = "600";
    summary.textContent = card.relevancia;
    relevancia.append(label, summary);
    mobileCard.append(header, relevancia);
  } else {
    mobileCard.appendChild(header);
  }

  // Layer 2: Nutshell — summary of the interpretation and its conclusion
  if (card.nutshell) {
    const summary = document.createElement("p");
    summary.className = "mobile-interp-card-summary";
    summary.textContent = card.nutshell;
    mobileCard.appendChild(summary);
  }

  // Layer 3: Extended heading (card_summary) when we already showed relevancia above
  if (card.relevancia && card.heading && card.heading !== card.relevancia) {
    const extended = document.createElement("p");
    extended.className = "mobile-interp-card-extended";
    extended.textContent = card.heading;
    mobileCard.appendChild(extended);
  } else if (!card.relevancia) {
    // No relevancia — show heading as the main description
    const desc = document.createElement("p");
    desc.className = "mobile-interp-card-desc";
    desc.textContent = card.heading;
    mobileCard.appendChild(desc);
  }

  const footer = document.createElement("div");
  footer.className = "mobile-interp-card-footer";
  const sources = document.createElement("span");
  sources.className = "mobile-interp-card-sources";
  sources.textContent =
    card.providerLabels.length > 0
      ? `Fuentes: ${card.providerLabels.join(", ")}`
      : card.sourceCountLabel;
  const arrow = document.createElement("span");
  arrow.className = "mobile-interp-card-arrow";
  arrow.setAttribute("aria-hidden", "true");
  arrow.textContent = "\u25B6";
  footer.append(sources, arrow);
  mobileCard.appendChild(footer);
  return mobileCard;
}

export function renderMobileExpertCards(
  container: HTMLElement,
  cards: ExpertCardViewModel[],
): void {
  container.replaceChildren();
  const grouped = new Map<ExpertCardClassification, ExpertCardViewModel[]>();
  for (const classification of MOBILE_GROUP_ORDER) {
    grouped.set(classification, []);
  }
  for (const card of cards) {
    if (card.hidden) continue;
    grouped.get(card.classification)?.push(card);
  }

  const fragment = document.createDocumentFragment();
  for (const classification of MOBILE_GROUP_ORDER) {
    const group = grouped.get(classification) || [];
    if (group.length === 0) continue;
    if (classification !== "individual") {
      fragment.appendChild(
        createListSectionHeading({
          className: "mobile-interp-group-label",
          dataComponent: "mobile-expert-group-label",
          label: group[0].classificationLabel.toUpperCase(),
          tagName: "p",
        }),
      );
    }
    group.forEach((card) => fragment.appendChild(createMobileExpertCard(card)));
  }

  container.appendChild(fragment);
}
