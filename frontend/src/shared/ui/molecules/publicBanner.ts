/**
 * Public visitor disclosure banner molecule.
 *
 * Mirrors the dark navy chrome strip used by the authenticated browser
 * chrome (`browserTabs.ts` → `.browser-tab-bar`) so the no-login `/public`
 * surface inherits the same brand language: navy background + LIA logo +
 * orange tagline. The two surfaces never duplicate the brand markup —
 * both compose the `createBrandMark` atom from
 * `frontend/src/shared/ui/atoms/brandMark.ts`.
 *
 * Differences from the authenticated chrome:
 *   - No tabs (public visitors have a single surface)
 *   - No user menu / login affordance (public is a deliberate dead end)
 *   - A short disclosure pill ("Acceso público — sin historial") sits on
 *     the left where the tabs would normally live.
 */

import { createBrandMark } from "@/shared/ui/atoms/brandMark";

export interface PublicBannerOptions {
  /** Short label rendered in bold at the start of the disclosure. */
  badgeLabel: string;
  /** Sentence shown after the badge (no inline HTML, plain text). */
  description: string;
  /** Logo URL (mirrors the authenticated chrome `BrowserChromeBrand`). */
  logoSrc: string;
  /** Accessible alt text for the logo. */
  logoAlt: string;
  /** Tagline shown next to the logo. */
  tagline: string;
}

export function createPublicBanner({
  badgeLabel,
  description,
  logoSrc,
  logoAlt,
  tagline,
}: PublicBannerOptions): HTMLElement {
  const banner = document.createElement("header");
  banner.className = "lia-public-banner";
  banner.setAttribute("data-lia-component", "public-banner");
  banner.setAttribute("role", "banner");

  // Disclosure pill on the left — sits where the tabs would be on the
  // authenticated chrome. Plain text only, no anchors.
  const disclosure = document.createElement("p");
  disclosure.className = "lia-public-banner__disclosure";
  disclosure.setAttribute("data-lia-component", "public-banner-disclosure");

  const badge = document.createElement("strong");
  badge.className = "lia-public-banner__badge";
  badge.textContent = badgeLabel;
  disclosure.appendChild(badge);
  disclosure.appendChild(document.createTextNode(` — ${description}`));

  banner.appendChild(disclosure);

  // Brand mark atom — single source of truth for logo + tagline. Same
  // atom the authenticated browser chrome consumes, so visual parity
  // and the `data-lia-component="brand-mark"` test contract are guaranteed.
  banner.appendChild(
    createBrandMark({
      logoSrc,
      logoAlt,
      tagline,
      className: "lia-public-banner__brand",
    }),
  );

  return banner;
}
