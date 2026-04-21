/**
 * Expert-detail modal title renderer.
 *
 * Single concern: given a raw group/card heading, populate the modal's
 * `<h3>` title node with two stacked lines — main title (larger) and an
 * optional "Tema principal: X" subtitle (smaller). Kept out of the
 * controller so title styling and the parsing contract evolve together.
 */

import {
  cleanModalTitle,
  sanitizeExpertText,
  splitTitleAndTopic,
} from "@/features/chat/expertSummaryText";

const TITLE_MAX_CHARS = 140;

export function applySplitTitle(titleNode: HTMLElement, rawHeading: string): void {
  titleNode.innerHTML = "";
  const { title, topic } = splitTitleAndTopic(rawHeading);
  const candidate = title || sanitizeExpertText(rawHeading) || String(rawHeading || "");
  const mainText = cleanModalTitle(candidate, TITLE_MAX_CHARS) || candidate;

  const main = document.createElement("span");
  main.className = "expert-detail-title-main";
  main.textContent = mainText;
  titleNode.appendChild(main);

  if (topic) {
    const subtitle = document.createElement("span");
    subtitle.className = "expert-detail-title-topic";
    subtitle.textContent = `Tema principal: ${topic}`;
    titleNode.appendChild(subtitle);
  }
}
