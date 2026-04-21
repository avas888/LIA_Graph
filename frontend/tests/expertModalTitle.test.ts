import { beforeEach, describe, expect, it } from "vitest";
import { applySplitTitle } from "@/features/chat/expertModalTitle";

describe("applySplitTitle", () => {
  let host: HTMLElement;

  beforeEach(() => {
    host = document.createElement("h3");
  });

  it("renders main title + topic subtitle when 'Tema principal' is present", () => {
    applySplitTitle(
      host,
      "FIR-E01 — Firmeza de las Declaraciones: Interpretaciones sobre Plazos Tema principal: plazos generales",
    );
    const main = host.querySelector(".expert-detail-title-main");
    const topic = host.querySelector(".expert-detail-title-topic");
    expect(main?.textContent).toContain("Firmeza de las Declaraciones");
    expect(main?.textContent).not.toContain("FIR-E01");
    expect(topic?.textContent).toBe("Tema principal: plazos generales");
  });

  it("renders only the main title when 'Tema principal' is absent", () => {
    applySplitTitle(host, "FIR-E01 — Firmeza de las Declaraciones");
    const main = host.querySelector(".expert-detail-title-main");
    const topic = host.querySelector(".expert-detail-title-topic");
    expect(main?.textContent).toBe("Firmeza de las Declaraciones");
    expect(topic).toBeNull();
  });

  it("strips leading internal doc codes", () => {
    applySplitTitle(host, "PER-E01 — Pérdidas fiscales");
    const main = host.querySelector(".expert-detail-title-main");
    expect(main?.textContent).toBe("Pérdidas fiscales");
  });

  it("wipes prior content when re-applied", () => {
    applySplitTitle(host, "Título A Tema principal: tema A");
    applySplitTitle(host, "Título B");
    expect(host.querySelectorAll(".expert-detail-title-main").length).toBe(1);
    expect(host.querySelectorAll(".expert-detail-title-topic").length).toBe(0);
    expect(host.querySelector(".expert-detail-title-main")?.textContent).toBe("Título B");
  });

  it("collapses a paragraph-shaped heading into a short proper title", () => {
    applySplitTitle(
      host,
      "Posicion Normativa — Referencia Rapida Los INCRNGO son ingresos que, reuniendo las condiciones para ser gravables, han sido excluidos de la base gravable por norma expresa del ET.",
    );
    const main = host.querySelector(".expert-detail-title-main");
    expect(main?.textContent).toBe("Posicion Normativa — Referencia Rapida");
    expect(main?.textContent?.length).toBeLessThan(60);
  });
});
