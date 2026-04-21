/**
 * Section heading atom.
 *
 * Replaces the legacy pattern of hand-rolled <h4> elements with tiny
 * ALL-CAPS eyebrow styling. A section heading can lead a panel or a
 * modal with real hierarchy: a readable label, an optional kicker
 * eyebrow, and a subtle accent rule that ties it into the surrounding
 * surface without shouting.
 *
 * Variants:
 *   - level  : semantic tag (h2 | h3 | h4) — defaults to h3
 *   - size   : sm | md | lg — controls the label type scale
 *   - tone   : primary | accent | muted
 *   - accent : render a left accent rule (editorial bar)
 *   - eyebrow: optional kicker text above the heading (not uppercased here;
 *              the CSS decides letter-spacing to keep things themeable)
 */

export type LiaSectionHeadingLevel = "h2" | "h3" | "h4";
export type LiaSectionHeadingTone = "primary" | "accent" | "muted";
export type LiaSectionHeadingSize = "sm" | "md" | "lg";

export interface SectionHeadingOptions {
  accent?: boolean;
  className?: string;
  dataComponent?: string;
  eyebrow?: string | null;
  label: string;
  level?: LiaSectionHeadingLevel;
  size?: LiaSectionHeadingSize;
  tone?: LiaSectionHeadingTone;
}

export function createSectionHeading(options: SectionHeadingOptions): HTMLElement {
  const {
    accent = false,
    className = "",
    dataComponent = "section-heading",
    eyebrow = null,
    label,
    level = "h3",
    size = "md",
    tone = "primary",
  } = options;

  const wrapper = document.createElement("div");
  wrapper.className = [
    "lia-section-heading",
    `lia-section-heading--${tone}`,
    `lia-section-heading--${size}`,
    accent ? "lia-section-heading--accent" : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");
  wrapper.setAttribute("data-lia-component", dataComponent);

  if (eyebrow && eyebrow.trim()) {
    const eyebrowNode = document.createElement("span");
    eyebrowNode.className = "lia-section-heading__eyebrow";
    eyebrowNode.textContent = eyebrow.trim();
    wrapper.appendChild(eyebrowNode);
  }

  const heading = document.createElement(level);
  heading.className = "lia-section-heading__label";
  heading.textContent = label;
  wrapper.appendChild(heading);

  return wrapper;
}
