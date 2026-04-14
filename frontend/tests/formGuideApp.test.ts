import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderFormGuideShell } from "@/app/form-guide/shell";
import { mountFormGuideApp } from "@/features/form-guide/formGuideApp";
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

function normalizedText(node: Element | null): string {
  return String(node?.textContent || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

describe("form guide app", () => {
  beforeEach(() => {
    document.body.innerHTML = `<div id="app">${renderFormGuideShell(createI18n("es-CO"))}</div>`;
    vi.restoreAllMocks();
    window.history.pushState({}, "", "/form-guide?reference_key=formulario%3A110");
    vi.stubGlobal("open", vi.fn());
  });

  it("loads the guide with textual and graphic panels, opens a rich field modal and downloads the official PDF", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url.startsWith("/api/form-guides/catalog")) {
          return Promise.resolve(
            mockJsonResponse({
              ok: true,
              guides: [
                {
                  reference_key: "formulario:110",
                  title: "Formulario 110",
                  form_version: "Resolucion DIAN 000188 de 2024 (AG 2025)",
                  available_profiles: [
                    {
                      profile_id: "pj_ordinario",
                      profile_label: "Persona Juridica - Regimen Ordinario",
                    },
                  ],
                  supported_views: ["structured", "interactive"],
                  last_verified_date: "2026-03-07",
                  download_available: true,
                  disclaimer: "Guia pedagogica.",
                },
              ],
            })
          );
        }
        if (url.startsWith("/api/form-guides/content")) {
          return Promise.resolve(
            mockJsonResponse({
              ok: true,
              manifest: {
                reference_key: "formulario:110",
                title: "Formulario 110",
                form_version: "Resolucion DIAN 000188 de 2024 (AG 2025)",
                profile_id: "pj_ordinario",
                profile_label: "Persona Juridica - Regimen Ordinario",
                supported_views: ["structured", "interactive"],
                last_verified_date: "2026-03-07",
                disclaimer: "Guia pedagogica.",
              },
              structured_sections: [
                {
                  section_id: "datos_generales",
                  title: "Seccion 1 - Datos Generales",
                  purpose: "Validar identificacion y RUT.",
                  what_to_review: "Confirma RUT y actividad economica.",
                  profile_differences: "",
                  common_errors: "Usar un NIT desactualizado.",
                  warnings: "Revisa la informacion registral.",
                },
              ],
              interactive_map: [
                {
                  field_id: "f110_nit",
                  label: "NIT del declarante",
                  page: 1,
                  bbox: [5, 12, 25, 3],
                  section: "datos_generales",
                  casilla: 5,
                  año_gravable: "2025",
                  profiles: ["pj_ordinario"],
                  instruction_md: "Revisa el RUT antes de diligenciar.",
                  official_dian_instruction: "Digite el NIT sin digito de verificacion.",
                  what_to_review_before_filling: "Valida identificacion.",
                  common_errors: "Usar el digito de verificacion.",
                  warnings: "La declaracion puede ser rechazada.",
                  source_ids: ["src_dian_f110"],
                  last_verified_date: "2026-03-07",
                },
              ],
              page_assets: [
                {
                  name: "page_01.png",
                  page: 1,
                  url: "/api/form-guides/asset?reference_key=formulario%3A110&profile=pj_ordinario&name=page_01.png",
                },
              ],
              official_pdf_url: "https://www.dian.gov.co/atencionciudadano/formulariosinstructivos/Formularios/2025/Formulario_110_2025.pdf",
              official_pdf_authority: "DIAN",
              pages: ["page_01.png"],
              sources: [
                {
                  source_id: "src_dian_f110",
                  title: "Formulario 110 AG 2025 - PDF oficial DIAN",
                  url: "https://www.dian.gov.co/atencionciudadano/formulariosinstructivos/Formularios/2025/Formulario_110_2025.pdf",
                  source_type: "formulario_oficial_pdf",
                  authority: "DIAN",
                  is_primary: true,
                  last_checked_date: "2026-03-07",
                  notes: "Formulario oficial publicado por la DIAN.",
                },
              ],
              disclaimer: "Guia pedagogica.",
            })
          );
        }
        if (url === "/api/form-guides/chat" && init?.method === "POST") {
          return Promise.resolve(
            mockJsonResponse({
              ok: true,
              answer_markdown: "1. Revisa datos generales.\n2. Valida patrimonio e ingresos.",
              answer_mode: "pedagogical",
              grounding: {},
              suggested_followups: [],
            })
          );
        }
        throw new Error(`Unexpected fetch: ${url}`);
      })
    );

    const root = document.getElementById("app");
    if (!root) {
      throw new Error("Missing root.");
    }

    mountFormGuideApp(root, { i18n: createI18n("es-CO") });
    await flushUi();
    await flushUi();

    expect(document.getElementById("form-guide-title")?.textContent).toContain("Formulario 110");
    expect(document.querySelectorAll("#structured-sections .guide-section").length).toBe(1);
    expect((document.getElementById("form-guide-interactive-view") as HTMLElement | null)?.hidden).toBe(false);
    expect((document.getElementById("form-guide-structured-view") as HTMLElement | null)?.hidden).toBe(false);
    expect(document.getElementById("form-guide-structured-view")?.textContent).toContain("Guía texto del formulario");
    expect(document.getElementById("form-guide-interactive-view")?.textContent).toContain("Guía gráfica del formulario");
    expect(document.getElementById("view-interactive-btn")?.getAttribute("aria-selected")).toBe("true");
    expect(document.getElementById("view-structured-btn")?.getAttribute("aria-selected")).toBe("false");

    expect(document.querySelector(".guide-document-image")).not.toBeNull();

    const pdfBtn = document.getElementById("form-guide-pdf-btn") as HTMLButtonElement | null;
    pdfBtn?.click();
    expect(window.open).toHaveBeenCalledWith(
      "https://www.dian.gov.co/atencionciudadano/formulariosinstructivos/Formularios/2025/Formulario_110_2025.pdf",
      "_blank",
      "noopener,noreferrer"
    );

    const hotspot = document.querySelector(".guide-hotspot") as HTMLElement | null;
    hotspot?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    const fieldDialog = document.getElementById("form-guide-field-dialog") as HTMLDialogElement | null;
    expect(fieldDialog?.open || fieldDialog?.hasAttribute("open")).toBe(true);
    expect(document.getElementById("field-dialog-title")?.textContent).toContain("Casilla 5");
    expect(document.getElementById("field-dialog-title")?.textContent).toContain("NIT del declarante");
    expect(normalizedText(document.getElementById("field-dialog-summary"))).toContain("Valida identificacion");
    expect(normalizedText(document.getElementById("field-dialog-body"))).toContain("Como diligenciar: NIT del declarante");
    expect(normalizedText(document.getElementById("field-dialog-body"))).toContain("Instruccion DIAN para NIT del declarante");
    expect(normalizedText(document.getElementById("field-dialog-body"))).toContain("Digite el NIT sin digito de verificacion");
    expect(normalizedText(document.getElementById("field-dialog-body"))).toContain("Contexto de la seccion");
    expect(normalizedText(document.getElementById("field-dialog-body"))).toContain("Que revisar en NIT del declarante");
    expect(document.querySelector(".guide-hotspot")?.getAttribute("data-casilla")).toBe("5");
    expect(normalizedText(document.getElementById("form-guide-chat-context"))).toContain("Casilla 5");
    expect(normalizedText(document.getElementById("form-guide-chat-context"))).toContain("Seccion 1 - Datos Generales");

    const input = document.getElementById("form-guide-chat-input") as HTMLTextAreaElement | null;
    const form = document.getElementById("form-guide-chat-form") as HTMLFormElement | null;
    if (!input || !form) {
      throw new Error("Missing chat elements.");
    }
    input.value = "cuales son los principales pasos para presentar la declaracion de renta de una pyme en 2026?";
    form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    await flushUi();
    await flushUi();

    const assistantMessages = Array.from(document.querySelectorAll(".form-guide-chat-assistant .chat-bubble-body"));
    expect(assistantMessages.at(-1)?.textContent).toContain("Revisa datos generales");
  });

  it("prompts for a profile when the guide has variants and renders the sources dialog after selection", async () => {
    const requestedProfiles: string[] = [];

    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        if (url.startsWith("/api/form-guides/catalog")) {
          return Promise.resolve(
            mockJsonResponse({
              ok: true,
              guides: [
                {
                  reference_key: "formulario:110",
                  title: "Formulario 110",
                  form_version: "Resolucion DIAN 000188 de 2024 (AG 2025)",
                  available_profiles: [
                    { profile_id: "pn_residente", profile_label: "Persona Natural Residente" },
                    { profile_id: "pj_ordinario", profile_label: "Persona Juridica - Regimen Ordinario" },
                  ],
                  supported_views: ["structured"],
                  last_verified_date: "2026-03-07",
                  download_available: true,
                  disclaimer: "Guia pedagogica.",
                },
              ],
            })
          );
        }
        if (url.startsWith("/api/form-guides/content")) {
          const profile = new URL(url, "https://lia.local").searchParams.get("profile") || "";
          requestedProfiles.push(profile);
          return Promise.resolve(
            mockJsonResponse({
              ok: true,
              manifest: {
                reference_key: "formulario:110",
                title: "Formulario 110",
                form_version: "Resolucion DIAN 000188 de 2024 (AG 2025)",
                profile_id: profile,
                profile_label: profile === "pj_ordinario" ? "Persona Juridica - Regimen Ordinario" : "Persona Natural Residente",
                supported_views: ["structured"],
                last_verified_date: "2026-03-07",
                disclaimer: "Guia pedagogica.",
              },
              structured_sections: [
                {
                  section_id: "datos_generales",
                  title: "Seccion 1 - Datos Generales",
                  purpose: "Validar identificacion y RUT.",
                  what_to_review: "Confirmar datos basicos.",
                  profile_differences: "",
                  common_errors: "",
                  warnings: "",
                },
              ],
              interactive_map: [],
              page_assets: [],
              pages: [],
              official_pdf_url: "",
              official_pdf_authority: "",
              sources: [
                {
                  source_id: "src_dian_f110",
                  title: "Formulario 110 AG 2025 - PDF oficial DIAN",
                  url: "https://www.dian.gov.co/formulario_110_2025.pdf",
                  source_type: "formulario_oficial_pdf",
                  authority: "DIAN",
                  is_primary: true,
                  last_checked_date: "2026-03-07",
                  notes: "Formulario oficial publicado por la DIAN.",
                },
              ],
              disclaimer: "Guia pedagogica.",
            })
          );
        }
        throw new Error(`Unexpected fetch: ${url}`);
      })
    );

    const root = document.getElementById("app");
    if (!root) {
      throw new Error("Missing root.");
    }

    mountFormGuideApp(root, { i18n: createI18n("es-CO") });
    await flushUi();
    await flushUi();

    expect((document.getElementById("form-guide-profile-selector") as HTMLElement | null)?.hidden).toBe(false);
    expect(normalizedText(document.getElementById("profile-options"))).toContain("Persona Natural Residente");
    expect(normalizedText(document.getElementById("profile-options"))).toContain("Persona Juridica - Regimen Ordinario");
    expect(requestedProfiles).toEqual([]);

    const selectedProfileBtn = document.querySelector('[data-profile="pj_ordinario"]') as HTMLButtonElement | null;
    selectedProfileBtn?.click();
    await flushUi();
    await flushUi();

    expect(requestedProfiles).toEqual(["pj_ordinario"]);
    expect((document.getElementById("form-guide-profile-selector") as HTMLElement | null)?.hidden).toBe(true);
    expect(document.getElementById("form-guide-profile")?.textContent).toContain("Persona Jurídica - Régimen Ordinario");

    const sourcesBtn = document.getElementById("form-guide-sources-btn") as HTMLButtonElement | null;
    const sourcesDialog = document.getElementById("form-guide-sources-dialog") as HTMLDialogElement | null;
    sourcesBtn?.click();

    expect(sourcesDialog?.open || sourcesDialog?.hasAttribute("open")).toBe(true);
    expect(normalizedText(document.getElementById("sources-list"))).toContain("Formulario 110 AG 2025 - PDF oficial DIAN");
    expect(normalizedText(document.getElementById("sources-list"))).toContain("Formulario oficial publicado por la DIAN");
  });

  it("falls back to a pending message instead of presenting section boilerplate as field-specific guidance", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        if (url.startsWith("/api/form-guides/catalog")) {
          return Promise.resolve(
            mockJsonResponse({
              ok: true,
              guides: [
                {
                  reference_key: "formulario:110",
                  title: "Formulario 110",
                  form_version: "Resolucion DIAN 000188 de 2024 (AG 2025)",
                  available_profiles: [{ profile_id: "pj_ordinario", profile_label: "Persona Juridica - Regimen Ordinario" }],
                  supported_views: ["structured", "interactive"],
                  last_verified_date: "2026-03-07",
                  download_available: true,
                  disclaimer: "Guia pedagogica.",
                },
              ],
            })
          );
        }
        if (url.startsWith("/api/form-guides/content")) {
          return Promise.resolve(
            mockJsonResponse({
              ok: true,
              manifest: {
                reference_key: "formulario:110",
                title: "Formulario 110",
                form_version: "Resolucion DIAN 000188 de 2024 (AG 2025)",
                profile_id: "pj_ordinario",
                profile_label: "Persona Juridica - Regimen Ordinario",
                supported_views: ["structured", "interactive"],
                last_verified_date: "2026-03-07",
                disclaimer: "Guia pedagogica.",
              },
              structured_sections: [
                {
                  section_id: "patrimonio",
                  title: "Seccion 2 - Patrimonio",
                  purpose: "Reportar patrimonio bruto y deudas.",
                  what_to_review: "Conciliar patrimonio bruto contra balance general.",
                  profile_differences: "",
                  common_errors: "Omitir activos en el exterior.",
                  warnings: "Revisar exclusiones patrimoniales.",
                },
              ],
              interactive_map: [
                {
                  field_id: "f110_c123",
                  label: "Casilla sin curacion puntual",
                  page: 1,
                  bbox: [5, 12, 25, 3],
                  section: "patrimonio",
                  casilla: 123,
                  año_gravable: "2025",
                  profiles: ["pj_ordinario"],
                  instruction_md:
                    "Revise la casilla **123** (Casilla sin curacion puntual) dentro de la seccion **Seccion 2 - Patrimonio** y concilie su valor con los soportes fiscales antes de presentar el formulario.",
                  official_dian_instruction: "",
                  what_to_review_before_filling: "",
                  common_errors: "",
                  warnings: "",
                  source_ids: ["src_dian_f110"],
                  last_verified_date: "2026-03-07",
                },
              ],
              page_assets: [
                {
                  name: "page_01.png",
                  page: 1,
                  url: "/api/form-guides/asset?reference_key=formulario%3A110&profile=pj_ordinario&name=page_01.png",
                },
              ],
              official_pdf_url: "",
              official_pdf_authority: "",
              pages: ["page_01.png"],
              sources: [],
              disclaimer: "Guia pedagogica.",
            })
          );
        }
        throw new Error(`Unexpected fetch: ${url}`);
      })
    );

    const root = document.getElementById("app");
    if (!root) {
      throw new Error("Missing root.");
    }

    mountFormGuideApp(root, { i18n: createI18n("es-CO") });
    await flushUi();
    await flushUi();

    const hotspot = document.querySelector(".guide-hotspot") as HTMLElement | null;
    hotspot?.dispatchEvent(new MouseEvent("click", { bubbles: true }));

    expect(normalizedText(document.getElementById("field-dialog-body"))).toContain("Detalle especifico pendiente");
    expect(normalizedText(document.getElementById("field-dialog-body"))).toContain("Contexto de la seccion");
    expect(normalizedText(document.getElementById("field-dialog-body"))).not.toContain("Que revisar en Casilla sin curacion puntual");
    expect(normalizedText(document.getElementById("field-dialog-body"))).not.toContain("Errores frecuentes en Casilla sin curacion puntual");
  });

  it("renders a clear handoff to the general chat for out-of-scope questions", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url.startsWith("/api/form-guides/catalog")) {
          return Promise.resolve(
            mockJsonResponse({
              ok: true,
              guides: [
                {
                  reference_key: "formulario:110",
                  title: "Formulario 110",
                  form_version: "Resolucion DIAN 000188 de 2024 (AG 2025)",
                  available_profiles: [{ profile_id: "pj_ordinario", profile_label: "Persona Juridica - Regimen Ordinario" }],
                  supported_views: ["structured", "interactive"],
                  last_verified_date: "2026-03-07",
                  download_available: true,
                  disclaimer: "Guia pedagogica.",
                },
              ],
            })
          );
        }
        if (url.startsWith("/api/form-guides/content")) {
          return Promise.resolve(
            mockJsonResponse({
              ok: true,
              manifest: {
                reference_key: "formulario:110",
                title: "Formulario 110",
                form_version: "Resolucion DIAN 000188 de 2024 (AG 2025)",
                profile_id: "pj_ordinario",
                profile_label: "Persona Juridica - Regimen Ordinario",
                supported_views: ["structured"],
                last_verified_date: "2026-03-07",
                disclaimer: "Guia pedagogica.",
              },
              structured_sections: [],
              interactive_map: [],
              page_assets: [],
              pages: [],
              sources: [],
              disclaimer: "Guia pedagogica.",
            })
          );
        }
        if (url === "/api/form-guides/chat" && init?.method === "POST") {
          return Promise.resolve(
            mockJsonResponse({
              ok: true,
              answer_markdown: "Esta ventana solo responde preguntas sobre este formulario y su diligenciamiento.",
              answer_mode: "out_of_scope_refusal",
              grounding: {
                handoff_url: "/?prefill=%C2%BFEste%20formulario%20es%20obligatorio%3F",
                handoff_target: "chat_general",
              },
              suggested_followups: [],
            })
          );
        }
        throw new Error(`Unexpected fetch: ${url}`);
      })
    );

    const root = document.getElementById("app");
    if (!root) {
      throw new Error("Missing root.");
    }

    mountFormGuideApp(root, { i18n: createI18n("es-CO") });
    await flushUi();
    await flushUi();

    const input = document.getElementById("form-guide-chat-input") as HTMLTextAreaElement | null;
    const form = document.getElementById("form-guide-chat-form") as HTMLFormElement | null;
    if (!input || !form) {
      throw new Error("Missing chat elements.");
    }

    input.value = "¿Este formulario es obligatorio?";
    form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    await flushUi();
    await flushUi();

    const handoffLink = document.querySelector<HTMLAnchorElement>(".form-guide-chat-handoff a");
    expect(document.querySelector(".form-guide-chat-handoff-helper")?.textContent).toContain("quedará como borrador");
    expect(handoffLink?.textContent).toContain("Continuar en el chat general");
    expect(handoffLink?.getAttribute("href")).toBe("/?prefill=%C2%BFEste%20formulario%20es%20obligatorio%3F");
    expect(handoffLink?.getAttribute("target")).toBe("_blank");
  });
});
