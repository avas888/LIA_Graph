import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderNormativeAnalysisShell } from "@/app/normative-analysis/shell";
import { mountNormativeAnalysisApp } from "@/features/normative-analysis/normativeAnalysisApp";
import { createI18n } from "@/shared/i18n";

function mockJsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

async function flushUi(): Promise<void> {
  await Promise.resolve();
  await new Promise((resolve) => window.setTimeout(resolve, 0));
  await Promise.resolve();
}

describe("normative analysis app", () => {
  beforeEach(() => {
    document.body.innerHTML = `<div id="app">${renderNormativeAnalysisShell(createI18n("es-CO"))}</div>`;
    vi.restoreAllMocks();
    window.history.pushState({}, "", "/normative-analysis?doc_id=doc_ley_001");
  });

  it("loads and renders the deep analysis surface", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        if (url === "/api/normative-analysis?doc_id=doc_ley_001") {
          return Promise.resolve(
            mockJsonResponse({
              ok: true,
              title: "Ley 2277 de 2022",
              document_family: "ley",
              family_subtype: "ley_ordinaria",
              binding_force: "Ley o estatuto",
              lead: "Reforma tributaria que ajusta reglas relevantes para la declaración de renta.",
              caution_banner: {
                title: "Revisa vigencia material",
                body: "Contrasta si el artículo consultado fue modificado por norma posterior.",
                tone: "warning",
              },
              preview_facts: [
                { label: "Qué regula", value: "Ajusta reglas sustantivas del impuesto sobre la renta." },
                { label: "Impacto", value: "Exige revisar cambios antes de cerrar papeles de trabajo." },
              ],
              sections: [
                {
                  id: "impacto",
                  title: "Impacto para contadores",
                  body: "Prioriza la **vigencia** y la trazabilidad de artículos modificados.",
                },
              ],
              timeline_events: [
                {
                  id: "issued",
                  label: "Expedición",
                  date: "2022-12-13",
                  detail: "Publicada en el Diario Oficial.",
                },
              ],
              related_documents: [
                {
                  title: "Decreto 1625 de 2016",
                  relation_type: "regulated_by",
                  relation_label: "Desarrollo reglamentario",
                  helper_text: "Aterriza reglas operativas.",
                  url: "/normative-analysis?doc_id=doc_dur_1625",
                },
              ],
              allowed_secondary_overlays: ["jurisprudencia_constitucional", "concepto_dian"],
              recommended_actions: [
                {
                  id: "source",
                  kind: "source",
                  label: "Ir a documento original",
                  url: "/source-view?doc_id=doc_ley_001",
                  helper_text: "Abre el soporte primario.",
                },
              ],
            })
          );
        }
        throw new Error(`Unexpected fetch: ${url}`);
      })
    );

    const root = document.getElementById("app");
    if (!root) {
      throw new Error("Missing app root.");
    }

    mountNormativeAnalysisApp(root, { i18n: createI18n("es-CO") });
    await flushUi();
    await flushUi();

    expect(document.title).toContain("Ley 2277 de 2022");
    expect(document.getElementById("normative-analysis-title")?.textContent).toContain("Ley 2277 de 2022");
    expect(document.getElementById("normative-analysis-binding")?.textContent).toContain("Ley o estatuto");
    expect(document.getElementById("normative-analysis-caution")?.hidden).toBe(false);
    expect(document.getElementById("normative-analysis-facts")?.textContent).toContain("Qué regula");
    expect(document.getElementById("normative-analysis-sections")?.textContent).toContain("Impacto para contadores");
    expect(document.getElementById("normative-analysis-timeline")?.textContent).toContain("Expedición");
    expect(document.getElementById("normative-analysis-relations")?.textContent).toContain("Decreto 1625 de 2016");
    expect(document.getElementById("normative-analysis-overlays")?.textContent).toContain("jurisprudencia constitucional");
    expect(document.getElementById("normative-analysis-actions")?.textContent).toContain("Ir a documento original");
  });

  it("keeps the deep-analysis caution banner hidden when the payload only contains invisible text", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        if (url === "/api/normative-analysis?doc_id=doc_ley_001") {
          return Promise.resolve(
            mockJsonResponse({
              ok: true,
              title: "Ley 2277 de 2022",
              document_family: "ley",
              lead: "Reforma tributaria con cambios en renta.",
              caution_banner: {
                title: "\u200B",
                body: "\u2060\uFEFF",
                tone: "warning",
              },
              preview_facts: [],
              sections: [],
              timeline_events: [],
              related_documents: [],
              allowed_secondary_overlays: [],
              recommended_actions: [],
            })
          );
        }
        throw new Error(`Unexpected fetch: ${url}`);
      })
    );

    const root = document.getElementById("app");
    if (!root) {
      throw new Error("Missing app root.");
    }

    mountNormativeAnalysisApp(root, { i18n: createI18n("es-CO") });
    await flushUi();
    await flushUi();

    expect(document.getElementById("normative-analysis-caution")?.hidden).toBe(true);
    expect(document.getElementById("normative-analysis-caution-title")?.textContent).toBe("");
    expect(document.getElementById("normative-analysis-caution-body")?.textContent).toBe("");
  });
});
