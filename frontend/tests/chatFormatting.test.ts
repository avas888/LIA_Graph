import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  applyKernelHierarchyFormattingMarkdown,
  splitAnswerFromFollowupSection,
  stripInlineEvidenceAnnotations,
} from "@/features/chat/formatting";
import { renderMarkdown } from "@/content/markdown";

describe("applyKernelHierarchyFormattingMarkdown", () => {
  beforeEach(() => {
    vi.stubGlobal("matchMedia", vi.fn().mockReturnValue({ matches: false }));
  });

  it("renders top-level numbered headings as ordered sections with nested bullets", () => {
    const formatted = applyKernelHierarchyFormattingMarkdown(
      [
        "1. Recopilacion y depuracion",
        "* Ingresos",
        "* Costos",
        "2. Conciliacion fiscal",
        "* Papeles de trabajo",
      ].join("\n")
    );

    expect(formatted).toContain("1. **<u>Recopilacion y depuracion:</u>**\n   * Ingresos");
    expect(formatted).toContain("2. **<u>Conciliacion fiscal:</u>**\n   * Papeles de trabajo");
  });

  it("keeps long numbered recommendation sentences as normal list items instead of underlined pseudo-headings", () => {
    const formatted = applyKernelHierarchyFormattingMarkdown(
      [
        "1. El régimen base del art. 147 ET es que la sociedad compensa la pérdida fiscal contra la renta líquida ordinaria de años siguientes; no es un trámite de devolución o compensación de saldo a favor ante la DIAN:",
        "2. Para pérdidas sujetas al régimen vigente, la regla operativa es 12 períodos gravables y sin tope porcentual anual; revisa el art. 290 ET solo si el saldo viene de años anteriores bajo régimen de transición:",
      ].join("\n")
    );

    expect(formatted).toContain("1. El régimen base del art. 147 ET es que la sociedad compensa la pérdida fiscal");
    expect(formatted).toContain("2. Para pérdidas sujetas al régimen vigente, la regla operativa es 12 períodos gravables");
    expect(formatted).not.toContain("**<u>El régimen base");
    expect(formatted).not.toContain("**<u>Para pérdidas sujetas");
  });

  it("dedents markdown-style nested bullets under numbered sections instead of flattening them", () => {
    const formatted = applyKernelHierarchyFormattingMarkdown(
      [
        "1. Preparacion y recopilacion",
        "    *   **Patrimonio Fiscal:** Revise activos y pasivos.",
        "    *   **Costos y Deducciones:** Organice soportes.",
      ].join("\n")
    );

    // 4-space indent is treated as markdown syntax for the first nested list level under `1.`
    expect(formatted).toContain("1. **<u>Preparacion y recopilacion:</u>**\n   * **Patrimonio Fiscal:** Revise activos y pasivos.");
    expect(formatted).toContain("   * **Costos y Deducciones:** Organice soportes.");
  });

  it("preserves 2-space indented bullets as nested sub-bullets", () => {
    const formatted = applyKernelHierarchyFormattingMarkdown(
      [
        "* **Ingresos:**",
        "  * Identificar la totalidad de ingresos ordinarios.",
        "  * Clasificar ingresos gravados y no gravados.",
      ].join("\n")
    );

    expect(formatted).toContain("* **Ingresos:**\n   * Identificar");
    expect(formatted).toContain("   * Clasificar");
  });

  it("preserves 4-level bullet hierarchy with distinct indentation", () => {
    const formatted = applyKernelHierarchyFormattingMarkdown(
      [
        "1. Preparacion documental",
        "* **Patrimonio Fiscal:**",
        "  * Revise activos y pasivos.",
        "    * Verificar avalúos catastrales.",
        "      * Comprobante de la secretaría.",
      ].join("\n")
    );

    expect(formatted).toContain("1. **<u>Preparacion documental:</u>**");
    expect(formatted).toContain("* **Patrimonio Fiscal:**");
    expect(formatted).toContain("   * Revise activos y pasivos.");
    expect(formatted).toContain("      * Verificar avalúos catastrales.");
    expect(formatted).toContain("         * Comprobante de la secretaría.");
  });

  it("flattens indentation deeper than level 4 to level 4", () => {
    const formatted = applyKernelHierarchyFormattingMarkdown(
      [
        "* Top bullet",
        "  * Level 3",
        "    * Level 4",
        "        * Too deep — should flatten to level 4",
      ].join("\n")
    );

    expect(formatted).toContain("* Top bullet");
    expect(formatted).toContain("   * Level 3");
    expect(formatted).toContain("      * Level 4");
    expect(formatted).toContain("         * Too deep — should flatten to level 4");
    expect(formatted).not.toContain("            *");
  });

  it("removes inline evidence annotations with nested brackets from visible answer text", () => {
    const cleaned = stripInlineEvidenceAnnotations(
      "* **Patrimonio Fiscal:** Revise activos y pasivos. [evidencia: [practica_erp] DIAN | templates/ingestion_rag_ready/2026_03/seccion_10_patrimonio_fiscal_0ec4c896_part_01.md]"
    );

    expect(cleaned).toBe("* **Patrimonio Fiscal:** Revise activos y pasivos.");
    expect(cleaned).not.toContain("practica_erp");
    expect(cleaned).not.toContain("templates/ingestion_rag_ready");
  });

  it("formats numbered sections even when the answer also contains fenced code blocks", () => {
    const formatted = applyKernelHierarchyFormattingMarkdown(
      [
        "1. Preparacion y recopilacion",
        "* Revise soportes",
        "",
        "```json",
        '{"nit":"900123456"}',
        "```",
        "",
        "2. Presentacion",
        "* Presente en Muisca",
      ].join("\n")
    );

    expect(formatted).toContain("1. **<u>Preparacion y recopilacion:</u>**\n   * Revise soportes");
    expect(formatted).toContain("```json\n{\"nit\":\"900123456\"}\n```");
    expect(formatted).toContain("2. **<u>Presentacion:</u>**\n   * Presente en Muisca");
  });

  it("converts numbered subsection trees into nested bullets that match the standard chat layout", () => {
    const formatted = applyKernelHierarchyFormattingMarkdown(
      [
        "1. Titulo de seccion",
        "1.1 Sub-seccion",
        "1.1.1 Sub-sub-seccion 1: Aca texto.",
        "1.1.2 Sub-sub-seccion 2",
        "1.1.2.1 Sub-sub-sub seccion A: Va aca.",
        "1.1.2.2 Sub-sub-sub seccion B: Va aca tambien.",
      ].join("\n")
    );

    expect(formatted).toContain("1. **<u>Titulo de seccion:</u>**");
    expect(formatted).toContain("   * **Sub-seccion:**");
    expect(formatted).toContain("      * **Sub-sub-seccion 1:** Aca texto.");
    expect(formatted).toContain("      * **Sub-sub-seccion 2:**");
    expect(formatted).toContain("         * **Sub-sub-sub seccion A:** Va aca.");
    expect(formatted).toContain("         * **Sub-sub-sub seccion B:** Va aca tambien.");
  });

  it("renders the normalized hierarchy as one ordered list with nested bullet lists", async () => {
    const container = document.createElement("div");
    const scrollContainer = document.createElement("div");
    scrollContainer.appendChild(container);

    await renderMarkdown(
      container,
      applyKernelHierarchyFormattingMarkdown(
        [
          "1. Titulo de seccion",
          "1.1 Sub-seccion",
          "1.1.1 Sub-sub-seccion 1: Aca texto.",
          "1.1.2 Sub-sub-seccion 2",
          "1.1.2.1 Sub-sub-sub seccion A: Va aca.",
        ].join("\n")
      ),
      { scrollContainer }
    );

    expect(container.querySelectorAll("ol")).toHaveLength(1);
    expect(container.querySelectorAll("ol > li")).toHaveLength(1);
    expect(container.querySelectorAll("ol > li > ul")).toHaveLength(1);
    expect(container.querySelectorAll("ol > li > ul > li")).toHaveLength(1);
    expect(container.querySelectorAll("ol > li > ul > li > ul > li")).toHaveLength(2);
    expect(container.querySelector("ol > li > strong > u")?.textContent).toBe("Titulo de seccion:");
    expect(container.textContent).toContain("Sub-sub-sub seccion A:");
  });
});

describe("splitAnswerFromFollowupSection", () => {
  it("strips only an explicit followup section at the end of the answer", () => {
    const result = splitAnswerFromFollowupSection(
      [
        "1. Preparacion",
        "* Revise soportes",
        "",
        "Sugerencias de consultas adicionales",
        "6.1 ¿Quieres que lo bajemos a cronograma exacto por tipo de contribuyente y NIT?",
        "6.2 ¿Quieres que te prepare checklist de soportes y controles para evitar errores de presentación?",
      ].join("\n")
    );

    expect(result.answer).toBe("1. Preparacion\n* Revise soportes");
    expect(result.followupQueries).toHaveLength(2);
  });

  it("keeps legitimate section numbering when there is no explicit followup section", () => {
    const result = splitAnswerFromFollowupSection(
      [
        "6.1 Regimen SIMPLE",
        "Compare base gravable, tarifa y retenciones antes de decidir.",
      ].join("\n")
    );

    expect(result.answer).toContain("6.1 Regimen SIMPLE");
    expect(result.followupQueries).toHaveLength(0);
  });
});
