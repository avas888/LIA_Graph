/**
 * @vitest-environment jsdom
 *
 * Atomic-design unit test for the corpus-health-metric molecule.
 * The organism (`corpusHealthCard`) composes 4 of these; if the molecule
 * regresses, all four cards render wrong simultaneously.
 */
import { describe, expect, it } from "vitest";

import { createCorpusHealthMetric } from "@/shared/ui/molecules/corpusHealthMetric";

describe("corpusHealthMetric", () => {
  it("renders title + primary + tone, omits secondary when not provided", () => {
    const el = createCorpusHealthMetric({
      title: "Generación activa",
      primary: "gen_active_rolling",
      tone: "ok",
    });
    expect(el.dataset.tone).toBe("ok");
    expect(el.classList.contains("lia-corpus-health-metric--ok")).toBe(true);
    expect(
      el.querySelector(".lia-corpus-health-metric__title")?.textContent,
    ).toBe("Generación activa");
    expect(
      el.querySelector(".lia-corpus-health-metric__primary")?.textContent,
    ).toBe("gen_active_rolling");
    expect(el.querySelector(".lia-corpus-health-metric__secondary")).toBeNull();
  });

  it("renders secondary when provided", () => {
    const el = createCorpusHealthMetric({
      title: "Embeddings",
      primary: "12 chunks pendientes",
      secondary: "99.96% al día — corre `make phase2-embed-backfill`",
      tone: "warning",
    });
    expect(
      el.querySelector(".lia-corpus-health-metric__secondary")?.textContent,
    ).toContain("phase2-embed-backfill");
    expect(el.dataset.tone).toBe("warning");
  });

  it("ignores empty/whitespace-only secondary", () => {
    const el = createCorpusHealthMetric({
      title: "Parity",
      primary: "Alineada ✓",
      secondary: "   ",
      tone: "ok",
    });
    expect(el.querySelector(".lia-corpus-health-metric__secondary")).toBeNull();
  });

  it("supports all four tones", () => {
    for (const tone of ["ok", "warning", "danger", "neutral"] as const) {
      const el = createCorpusHealthMetric({
        title: "x",
        primary: "y",
        tone,
      });
      expect(el.dataset.tone).toBe(tone);
      expect(el.classList.contains(`lia-corpus-health-metric--${tone}`)).toBe(
        true,
      );
    }
  });
});
