/**
 * LIA brand mark atom — logo + tagline.
 *
 * The single source of truth for the LIA brand presentation. Both the
 * authenticated `browserTabs.ts` chrome and the no-login `publicBanner.ts`
 * molecule consume this atom so the logo + tagline contract lives in one
 * place.
 *
 * Per `docs/ui/atomic_design_ui_architecture.md`:
 *   - Atoms only depend on tokens / icons / small DOM helpers.
 *   - Carries `data-lia-component="brand-mark"` for tests + adapters.
 *   - No raw colors — visual styling lives in
 *     `frontend/src/styles/browser-tabs.css` (`.browser-tab-brand-*`).
 */

export interface BrandMarkOptions {
  /** URL of the logo image. */
  logoSrc: string;
  /** Accessible alt text for the logo. */
  logoAlt: string;
  /** Tagline text shown next to the logo. */
  tagline: string;
  /** Optional extra class for surface-specific tweaks. */
  className?: string;
  /** Override the data-lia-component identifier (rare). */
  dataComponent?: string;
}

export function createBrandMark({
  logoSrc,
  logoAlt,
  tagline,
  className = "",
  dataComponent = "brand-mark",
}: BrandMarkOptions): HTMLElement {
  const root = document.createElement("div");
  root.className = ["browser-tab-brand", className].filter(Boolean).join(" ");
  root.setAttribute("data-lia-component", dataComponent);
  root.setAttribute("aria-hidden", "true");

  const logo = document.createElement("img");
  logo.src = logoSrc;
  logo.alt = logoAlt;
  logo.className = "browser-tab-brand-logo";
  root.appendChild(logo);

  const taglineNode = document.createElement("span");
  taglineNode.className = "browser-tab-brand-tagline";
  taglineNode.textContent = tagline;
  root.appendChild(taglineNode);

  return root;
}

/**
 * String form of the brand mark — for surfaces that compose HTML strings
 * (like `renderBrowserChrome`) instead of mounting DOM nodes. The output
 * is byte-identical to the DOM atom so the two paths render the same
 * `data-lia-component="brand-mark"` contract.
 */
export function renderBrandMarkHtml(options: BrandMarkOptions): string {
  const node = createBrandMark(options);
  return node.outerHTML;
}
