/**
 * WCAG 2.1 AA contrast validation for the color token system.
 *
 * Pure-math implementation of relative luminance + contrast ratio.
 * Token hex values must be kept in sync with frontend/src/styles/tokens.css.
 * jsdom does not parse CSS, so static pairs are tested directly.
 */
import { describe, it, expect } from "vitest";

/* ── WCAG 2.1 relative luminance ──────────────────────────── */

function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace("#", "");
  return [
    parseInt(h.slice(0, 2), 16),
    parseInt(h.slice(2, 4), 16),
    parseInt(h.slice(4, 6), 16),
  ];
}

function relativeLuminance(hex: string): number {
  const [r, g, b] = hexToRgb(hex).map((c) => {
    const s = c / 255;
    return s <= 0.04045 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrastRatio(fg: string, bg: string): number {
  const l1 = relativeLuminance(fg);
  const l2 = relativeLuminance(bg);
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

/* ── Token values (from tokens.css) ───────────────────────── */

const tokens = {
  "p-neutral-50": "#f8faf9",
  "p-neutral-100": "#f0f4f2",
  "p-neutral-800": "#222e2a",
  "p-neutral-600": "#4a5b53",
  "p-neutral-500": "#5f7169",
  "p-green-50": "#eef8f3",
  "p-green-600": "#0f5a47",
  "p-green-700": "#083a2f",
  "p-amber-400": "#c07a38",
  "p-red-600": "#8d2f1d",
  "p-red-50": "#fff6f4",
  "p-red-700": "#7a2a1e",
  "p-blue-500": "#1d60b8",
  "p-blue-600": "#155d9a",
  "p-blue-800": "#1a5276",
  white: "#ffffff",
} as const;

/* ── Contrast pair tests ──────────────────────────────────── */

describe("WCAG AA contrast validation", () => {
  const pairs: {
    label: string;
    fg: string;
    bg: string;
    minRatio: number;
  }[] = [
    {
      label: "Body text on base surface",
      fg: tokens["p-neutral-800"],
      bg: tokens["p-neutral-100"],
      minRatio: 4.5,
    },
    {
      label: "Secondary text (neutral-600) on raised surface",
      fg: tokens["p-neutral-600"],
      bg: tokens["p-neutral-50"],
      minRatio: 4.5,
    },
    {
      label: "Tertiary text (neutral-500) on raised surface",
      fg: tokens["p-neutral-500"],
      bg: tokens["p-neutral-50"],
      minRatio: 4.5,
    },
    {
      label: "Secondary text (neutral-600) on base surface",
      fg: tokens["p-neutral-600"],
      bg: tokens["p-neutral-100"],
      minRatio: 4.5,
    },
    {
      label: "Tertiary text (neutral-500) on base surface",
      fg: tokens["p-neutral-500"],
      bg: tokens["p-neutral-100"],
      minRatio: 4.5,
    },
    {
      label: "Status ok (green-600) on raised surface",
      fg: tokens["p-green-600"],
      bg: tokens["p-neutral-50"],
      minRatio: 4.5,
    },
    {
      label: "Status warn (amber-400) on raised surface",
      fg: tokens["p-amber-400"],
      bg: tokens["p-neutral-50"],
      minRatio: 3,
    },
    {
      label: "Status error (red-600) on raised surface",
      fg: tokens["p-red-600"],
      bg: tokens["p-neutral-50"],
      minRatio: 4.5,
    },
    {
      label: "Primary btn text (white) on green-600",
      fg: tokens.white,
      bg: tokens["p-green-600"],
      minRatio: 4.5,
    },
    {
      label: "Secondary btn text (green-700) on green-50",
      fg: tokens["p-green-700"],
      bg: tokens["p-green-50"],
      minRatio: 4.5,
    },
    {
      label: "Flash success text (green-700) on green-50",
      fg: tokens["p-green-700"],
      bg: tokens["p-green-50"],
      minRatio: 4.5,
    },
    {
      label: "Flash error text (red-600) on red-50",
      fg: tokens["p-red-600"],
      bg: tokens["p-red-50"],
      minRatio: 4.5,
    },
    {
      label: "Chat link (blue-500) on raised surface",
      fg: tokens["p-blue-500"],
      bg: tokens["p-neutral-50"],
      minRatio: 4.5,
    },
    {
      label: "Chat user link (blue-600) on green-50",
      fg: tokens["p-blue-600"],
      bg: tokens["p-green-50"],
      minRatio: 4.5,
    },
    {
      label: "Reset btn text (red-700) on red-50",
      fg: tokens["p-red-700"],
      bg: tokens["p-red-50"],
      minRatio: 4.5,
    },
    {
      label: "DIAN accent (blue-800) on raised surface",
      fg: tokens["p-blue-800"],
      bg: tokens["p-neutral-50"],
      minRatio: 4.5,
    },
  ];

  for (const { label, fg, bg, minRatio } of pairs) {
    it(`${label}: ≥${minRatio}:1`, () => {
      const ratio = contrastRatio(fg, bg);
      expect(ratio).toBeGreaterThanOrEqual(minRatio);
    });
  }
});
