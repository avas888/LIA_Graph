import type { MobileSheet } from "./mobileSheet";
import {
  renderMobileExpertCards,
  type ExpertCardViewModel,
} from "@/shared/ui/organisms/expertCards";

export interface MobileInterpPanel {
  setCards(cards: ExpertCardViewModel[]): void;
  setResponseReceived(received: boolean): void;
  clear(): void;
}

export function mountMobileInterpPanel(
  root: HTMLElement,
  sheet: MobileSheet,
  options: {
    onOpenCard?: (cardId: string) => void;
  } = {},
): MobileInterpPanel {
  const listEl = root.querySelector<HTMLElement>("#mobile-interp-list")!;
  const emptyEl = root.querySelector<HTMLElement>("#mobile-interp-empty")!;
  let currentCards: ExpertCardViewModel[] = [];
  let responseReceived = false;

  function setResponseReceived(received: boolean): void {
    responseReceived = received;
    // Update empty state text if currently showing empty
    if (currentCards.length === 0 && !emptyEl.hidden) {
      updateEmptyStateText();
    }
  }

  function updateEmptyStateText(): void {
    const textEl = emptyEl.querySelector<HTMLElement>(".mobile-empty-state-text");
    if (textEl) {
      textEl.textContent = responseReceived
        ? "No se encontraron interpretaciones de expertos para esta consulta."
        : "Las interpretaciones de expertos aparecerán aquí cuando LIA responda tu consulta";
    }
  }

  function setCards(cards: ExpertCardViewModel[]): void {
    currentCards = cards.filter((card) => !card.hidden);
    if (currentCards.length === 0) {
      listEl.replaceChildren();
      emptyEl.hidden = false;
      updateEmptyStateText();
      return;
    }
    emptyEl.hidden = true;
    renderMobileExpertCards(listEl, currentCards);
  }

  function clear(): void {
    currentCards = [];
    responseReceived = false;
    listEl.replaceChildren();
    emptyEl.hidden = false;
    updateEmptyStateText();
  }

  listEl.addEventListener("click", (event: Event) => {
    const cardEl = (event.target as HTMLElement).closest<HTMLElement>(".mobile-interp-card");
    if (!cardEl) return;

    const cardId = cardEl.dataset.cardId ?? "";
    const card = currentCards.find((candidate) => candidate.id === cardId);
    if (!card) return;

    options.onOpenCard?.(card.id);
    requestAnimationFrame(() => {
      setTimeout(() => openInterpSheet(card), 150);
    });
  });

  function openInterpSheet(card: ExpertCardViewModel): void {
    const modal = root.querySelector<HTMLElement>("#modal-expert-detail");
    const detailContent = modal?.querySelector<HTMLElement>("#expert-detail-content");
    const detailHtml = detailContent?.innerHTML ?? "";

    const signalBadge = card.signalLabel
      ? `<span class="mobile-interp-card-signal mobile-interp-card-signal--sheet" data-signal="${card.signal}">${escapeHtml(card.signalLabel)}</span>`
      : "";

    sheet.open({
      title: card.articleLabel || "Interpretación",
      subtitle: card.classificationLabel,
      html: `
        ${signalBadge}
        <div>${detailHtml || `<p>${escapeHtml(card.nutshell || card.heading)}</p>`}</div>
      `,
    });

    if (modal) {
      const layer = modal.closest<HTMLElement>("#modal-layer");
      if (layer) layer.hidden = true;
      modal.classList.remove("is-open");
      modal.setAttribute("aria-hidden", "true");
    }
  }

  return { setCards, setResponseReceived, clear };
}

function escapeHtml(text: string): string {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}
