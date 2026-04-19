// @ts-nocheck

import { renderMarkdown } from "@/content/markdown";
import type { FormGuideState } from "@/features/form-guide/formGuideState";
import { icons } from "@/shared/ui/icons";
import {
  closeDialogSafely,
  escapeHtml,
  fieldDisplayName,
  isDialogOpen,
  openDialogSafely,
  renderHotspotBadge,
  resolveHotspotAnchor,
  setGuideView,
  uiText,
  type FieldHotspot,
  type GuideCatalogEntry,
  type GuideContentResponse,
  type GuidePageAsset,
  type StructuredSection,
} from "@/features/form-guide/formGuideTypes";

interface CreateFormGuideSurfaceControllerOptions {
  state: FormGuideState;
}

export function createFormGuideSurfaceController({ state }: CreateFormGuideSurfaceControllerOptions) {
  function markdownToPlainText(markdown: string): string {
    const container = document.createElement("div");
    renderMarkdown(container, markdown);
    return uiText(container.textContent || "");
  }

  function normalizeGuideText(value: string): string {
    return markdownToPlainText(value)
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/[^a-z0-9]+/gi, " ")
      .trim()
      .toLowerCase();
  }

  function isBoilerplateFieldInstruction(field: FieldHotspot, section: StructuredSection | undefined): boolean {
    const instruction = normalizeGuideText(field.instruction_md || "");
    if (!instruction) return true;

    const sectionTitle = normalizeGuideText(section?.title || "");
    const mentionsCoordinates =
      Boolean(field.casilla && instruction.includes(`casilla ${field.casilla}`)) &&
      Boolean(sectionTitle && instruction.includes(sectionTitle));
    const hasTemplatePrompt =
      instruction.includes("revise la casilla") ||
      instruction.includes("verifique la casilla") ||
      instruction.includes("dentro de la seccion") ||
      instruction.includes("antes de presentar");
    const lacksSupportingDetail =
      !uiText(field.what_to_review_before_filling || "") &&
      !uiText(field.common_errors || "") &&
      !uiText(field.warnings || "");

    return hasTemplatePrompt && mentionsCoordinates && lacksSupportingDetail;
  }

  function isRedundantWithOfficialInstruction(officialInstruction: string, fallbackInstruction: string): boolean {
    const official = normalizeGuideText(officialInstruction);
    const fallback = normalizeGuideText(fallbackInstruction);
    if (!official || !fallback) return false;
    return official.includes(fallback) || fallback.includes(official);
  }

  function focusGuideChatInput(): void {
    const input = document.getElementById("form-guide-chat-input") as HTMLTextAreaElement | null;
    if (!input) return;
    input.focus();
    input.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }

  function syncGuideSelection(): void {
    document.querySelectorAll(".guide-hotspot-active").forEach((node) => node.classList.remove("guide-hotspot-active"));
    document.querySelectorAll(".guide-section-active").forEach((node) => node.classList.remove("guide-section-active"));

    if (state.selectedFieldId) {
      const activeHotspot = document.querySelector(`.guide-hotspot[data-field-id="${state.selectedFieldId}"]`);
      activeHotspot?.classList.add("guide-hotspot-active");
    }
    if (state.selectedSection) {
      const activeSection = document.querySelector(`.guide-section[data-section-id="${state.selectedSection}"]`);
      activeSection?.classList.add("guide-section-active");
    }
  }

  function updateChatContext(): void {
    const contextEl = document.getElementById("form-guide-chat-context");
    if (!contextEl) return;

    if (state.selectedFieldId) {
      const field = state.guideHotspotsById.get(state.selectedFieldId);
      const section = state.selectedSection ? state.guideSectionsById.get(state.selectedSection) : undefined;
      const fieldContext = field?.casilla
        ? `Casilla ${field.casilla} — ${uiText(field.label)}`
        : uiText(field?.label || state.selectedFieldId);
      contextEl.textContent = section ? `Contexto: ${fieldContext} · ${uiText(section.title)}` : `Contexto: ${fieldContext}`;
      return;
    }

    if (state.selectedSection) {
      const section = state.guideSectionsById.get(state.selectedSection);
      contextEl.textContent = `Contexto: ${uiText(section?.title || state.selectedSection)}`;
      return;
    }

    contextEl.textContent = "";
  }

  function openFieldDialog(field: FieldHotspot): void {
    const dialog = document.getElementById("form-guide-field-dialog") as HTMLDialogElement | null;
    const titleEl = document.getElementById("field-dialog-title");
    const eyebrowEl = document.getElementById("field-dialog-eyebrow");
    const metaEl = document.getElementById("field-dialog-meta");
    const summaryEl = document.getElementById("field-dialog-summary");
    const bodyEl = document.getElementById("field-dialog-body");
    if (!dialog || !titleEl || !eyebrowEl || !metaEl || !summaryEl || !bodyEl) return;

    const section = state.guideSectionsById.get(field.section);
    const fieldName = uiText(fieldDisplayName(field));
    const officialInstruction = uiText(field.official_dian_instruction || "");
    const rawFallbackInstruction = String(field.instruction_md || "").trim();
    const fallbackInstruction = uiText(rawFallbackInstruction);
    const hasSpecificFallback =
      Boolean(rawFallbackInstruction) && !isBoilerplateFieldInstruction(field, section);
    const showFallbackCard =
      hasSpecificFallback && (!officialInstruction || !isRedundantWithOfficialInstruction(officialInstruction, rawFallbackInstruction));
    const summaryText = uiText(field.what_to_review_before_filling || "");

    dialog.dataset.fieldId = field.field_id;
    dialog.dataset.sectionId = field.section;
    titleEl.textContent = field.casilla ? `Casilla ${field.casilla} — ${uiText(field.label)}` : uiText(field.label);
    eyebrowEl.textContent = uiText(section?.title || "Campo guiado");
    metaEl.innerHTML = [
      field.casilla ? `<span class="field-dialog-chip">Casilla ${field.casilla}</span>` : "",
      field.año_gravable ? `<span class="field-dialog-chip">AG ${escapeHtml(field.año_gravable)}</span>` : "",
      `<span class="field-dialog-chip">Página ${field.page}</span>`,
      section?.title ? `<span class="field-dialog-chip field-dialog-chip-soft">${escapeHtml(uiText(section.title))}</span>` : "",
    ]
      .filter(Boolean)
      .join("");

    summaryEl.textContent = summaryText;
    summaryEl.hidden = !summaryText;

    const cards: string[] = [];
    if (showFallbackCard) {
      const sourceAuthorities = (field.source_ids || [])
        .map((sid) => state.guideSources.find((s) => s.source_id === sid))
        .filter(Boolean)
        .map((s) => s!.authority)
        .filter((a, i, arr) => a && arr.indexOf(a) === i);
      const sourceBadge = sourceAuthorities.length > 0
        ? `<span class="field-dialog-source-badge">Fuente: ${escapeHtml(sourceAuthorities.join(", "))}</span>`
        : "";
      cards.push(`
        <article class="field-dialog-card field-dialog-card-primary">
          <p class="guide-section-label">${officialInstruction ? "Cómo diligenciar" : "Indicación principal"}: ${escapeHtml(fieldName)}</p>
          <div data-field-dialog-markdown="fallback" class="field-dialog-markdown"></div>
          ${sourceBadge}
        </article>
      `);
    }
    if (officialInstruction) {
      cards.push(`
        <article class="field-dialog-card field-dialog-card-dian">
          <p class="guide-section-label dian-official-label">Instrucción DIAN para ${escapeHtml(fieldName)}</p>
          <p>${escapeHtml(officialInstruction)}</p>
          <span class="dian-official-badge">Recomendación Oficial DIAN</span>
        </article>
      `);
    }

    if (field.what_to_review_before_filling) {
      cards.push(`
        <article class="field-dialog-card">
          <p class="guide-section-label">Qué revisar en ${escapeHtml(fieldName)}</p>
          <p>${escapeHtml(uiText(field.what_to_review_before_filling))}</p>
        </article>
      `);
    }

    if (field.common_errors) {
      cards.push(`
        <article class="field-dialog-card field-dialog-card-errors">
          <p class="guide-section-label">Errores frecuentes en ${escapeHtml(fieldName)}</p>
          <p>${escapeHtml(uiText(field.common_errors))}</p>
        </article>
      `);
    }

    if (field.warnings) {
      cards.push(`
        <article class="field-dialog-card field-dialog-card-warnings">
          <p class="guide-section-label">Advertencias para ${escapeHtml(fieldName)}</p>
          <p>${escapeHtml(uiText(field.warnings))}</p>
        </article>
      `);
    }

    if (!showFallbackCard && !officialInstruction && !field.what_to_review_before_filling && !field.common_errors && !field.warnings) {
      cards.push(`
        <article class="field-dialog-card">
          <p class="guide-section-label">Detalle específico pendiente</p>
          <p>Esta casilla ya está ubicada y titulada, pero su comentario puntual aún no está curado con suficiente detalle.</p>
        </article>
      `);
    }
    if (section?.title || section?.purpose || section?.profile_differences) {
      const contextParts = [
        section?.title ? `<p><strong>Sección:</strong> ${escapeHtml(uiText(section.title))}</p>` : "",
        section?.purpose ? `<p><strong>Para qué sirve:</strong> ${escapeHtml(uiText(section.purpose))}</p>` : "",
        section?.profile_differences
          ? `<p><strong>Diferencias por perfil:</strong> ${escapeHtml(uiText(section.profile_differences))}</p>`
          : "",
      ].filter(Boolean);
      cards.push(`
        <article class="field-dialog-card">
          <p class="guide-section-label">Contexto de la sección</p>
          ${contextParts.join("")}
        </article>
      `);
    }

    bodyEl.innerHTML = cards.join("");
    const fallbackInstructionEl = bodyEl.querySelector('[data-field-dialog-markdown="fallback"]') as HTMLElement | null;
    if (fallbackInstructionEl && rawFallbackInstruction) {
      renderMarkdown(fallbackInstructionEl, rawFallbackInstruction);
    }

    openDialogSafely(dialog);
  }

  function buildCamposHtml(hotspots: FieldHotspot[], sectionId: string): string {
    const sectionFields = hotspots
      .filter((h) => h.section === sectionId)
      .sort((a, b) => (a.casilla || 0) - (b.casilla || 0));
    if (sectionFields.length === 0) return "";

    const items = sectionFields
      .map((field) => {
        const casillaBadge = field.casilla ? `<span class="campo-casilla">Cas. ${field.casilla}</span>` : "";
        const label = escapeHtml(uiText(field.label));
        const instruction = field.instruction_md
          ? escapeHtml(markdownToPlainText(field.instruction_md).slice(0, 160))
          : "";
        const truncated = instruction.length >= 160 ? instruction + "…" : instruction;
        return `
          <li class="campo-item" data-campo-field-id="${field.field_id}" role="button" tabindex="0">
            <div class="campo-header">${casillaBadge}<span class="campo-label">${label}</span></div>
            ${truncated ? `<p class="campo-instruction">${truncated}</p>` : ""}
            <span class="campo-open-icon" aria-hidden="true" title="Ver ficha completa">${icons.externalLink}</span>
          </li>
        `;
      })
      .join("");

    return `
      <div class="guide-section-block guide-section-campos">
        <p class="guide-section-label">Campos de esta sección (${sectionFields.length})</p>
        <ul class="campo-list">${items}</ul>
      </div>
    `;
  }

  function renderStructuredView(sections: StructuredSection[], hotspots: FieldHotspot[]): void {
    const container = document.getElementById("structured-sections");
    if (!container) return;

    container.innerHTML = sections
      .map(
        (section) => `
        <article class="guide-section" data-section-id="${section.section_id}">
          <h3 class="guide-section-title">${escapeHtml(uiText(section.title))}</h3>
          ${section.purpose ? `<div class="guide-section-block"><p class="guide-section-label">Para qué sirve</p><p>${escapeHtml(uiText(section.purpose))}</p></div>` : ""}
          ${section.what_to_review ? `<div class="guide-section-block"><p class="guide-section-label">Qué revisar antes de diligenciar</p><p>${escapeHtml(uiText(section.what_to_review))}</p></div>` : ""}
          ${section.profile_differences ? `<div class="guide-section-block"><p class="guide-section-label">Diferencias por perfil</p><p>${escapeHtml(uiText(section.profile_differences))}</p></div>` : ""}
          ${buildCamposHtml(hotspots, section.section_id)}
          ${section.common_errors ? `<div class="guide-section-block guide-section-errors"><p class="guide-section-label">Errores frecuentes</p><p>${escapeHtml(uiText(section.common_errors))}</p></div>` : ""}
          ${section.warnings ? `<div class="guide-section-block guide-section-warnings"><p class="guide-section-label">Advertencias</p><p>${escapeHtml(uiText(section.warnings))}</p></div>` : ""}
        </article>
      `
      )
      .join("");

    container.onclick = (event) => {
      const campoItem = (event.target as HTMLElement).closest("[data-campo-field-id]") as HTMLElement | null;
      if (campoItem) {
        const fieldId = campoItem.dataset.campoFieldId || "";
        const field = state.guideHotspotsById.get(fieldId);
        if (field) {
          state.selectedFieldId = fieldId;
          state.selectedSection = field.section;
          syncGuideSelection();
          updateChatContext();
          openFieldDialog(field);
        }
        return;
      }

      const section = (event.target as HTMLElement).closest("[data-section-id]") as HTMLElement | null;
      if (!section) return;
      state.selectedSection = section.dataset.sectionId || null;
      state.selectedFieldId = null;
      syncGuideSelection();
      updateChatContext();
    };
  }

  function renderInteractiveFallback(message: string): void {
    const container = document.getElementById("interactive-pages");
    if (!container) return;
    container.innerHTML = `
      <section class="guide-page-card guide-page-card-empty">
        <div class="guide-page-header">
          <div>
            <h3 class="interactive-page-title">Guía gráfica no disponible</h3>
            <p>Este formulario aún no tiene mapa de campos publicado.</p>
          </div>
        </div>
        <div class="guide-document-fallback">${escapeHtml(message)}</div>
      </section>
    `;
  }

  function renderInteractiveMap(hotspots: FieldHotspot[], pageAssets: GuidePageAsset[]): void {
    const byPage = new Map<number, FieldHotspot[]>();
    hotspots.forEach((hotspot) => {
      const list = byPage.get(hotspot.page) || [];
      list.push(hotspot);
      byPage.set(hotspot.page, list);
    });

    const container = document.getElementById("interactive-pages");
    if (!container) return;

    const assetByPage = new Map<number, GuidePageAsset>();
    pageAssets.forEach((asset) => {
      assetByPage.set(asset.page, asset);
    });

    const pages = (byPage.size > 0 ? Array.from(byPage.keys()) : Array.from(assetByPage.keys())).sort((a, b) => a - b);
    container.innerHTML = pages
      .map((pageNum) => {
        const asset = assetByPage.get(pageNum);
        const fields = byPage.get(pageNum) || [];
        return `
          <section class="guide-page-card" data-guide-page="${pageNum}">
            <div class="guide-page-header">
              <div>
                <h3 class="interactive-page-title">Página ${pageNum}</h3>
                <p>${fields.length} campo(s) guiado(s)</p>
              </div>
              <div class="guide-page-helper">Haz clic en un campo para abrir o cerrar la ficha.</div>
            </div>
            <div class="guide-document-frame">
              ${asset ? `<img class="guide-document-image" src="${escapeHtml(asset.url)}" alt="Vista exacta página ${pageNum} del formulario" />` : `<div class="guide-document-fallback">No hay asset publicado para esta página.</div>`}
              <div class="guide-hotspot-layer">
                ${fields
                  .map((field) => {
                    const anchor = resolveHotspotAnchor(field);
                    return `
                      <button
                        class="guide-hotspot"
                        type="button"
                        data-field-id="${field.field_id}"
                        data-casilla="${field.casilla || ""}"
                        data-section="${field.section}"
                        data-page="${field.page}"
                        data-marker-x="${anchor.markerCenterX ?? ""}"
                        data-marker-y="${anchor.markerCenterY ?? ""}"
                        data-marker-centered="${anchor.centered ? "true" : "false"}"
                        aria-label="Abrir o cerrar detalle de ${escapeHtml(uiText(field.label))}"
                        style="left:${anchor.left}%;top:${anchor.top}%;--guide-hotspot-translate-x:${anchor.centered ? "-50%" : "0"};--guide-hotspot-translate-y:${anchor.centered ? "-50%" : "0"};"
                      >
                        <span class="guide-hotspot-pill">${escapeHtml(renderHotspotBadge(field))}</span>
                      </button>
                    `;
                  })
                  .join("")}
              </div>
            </div>
          </section>
        `;
      })
      .join("");

    const allFields = Array.from(byPage.values()).flat();

    container.onclick = (event) => {
      const btn = (event.target as HTMLElement).closest("[data-field-id]") as HTMLElement | null;
      if (!btn) return;

      const fieldId = btn.dataset.fieldId || "";
      const field = allFields.find((item) => item.field_id === fieldId);
      if (!field) return;
      const dialog = document.getElementById("form-guide-field-dialog") as HTMLDialogElement | null;
      const sameFieldOpen = Boolean(dialog && dialog.dataset.fieldId === fieldId && isDialogOpen(dialog));

      state.selectedFieldId = fieldId;
      state.selectedSection = field.section;
      syncGuideSelection();
      updateChatContext();
      if (sameFieldOpen && dialog) {
        closeDialogSafely(dialog);
        return;
      }
      openFieldDialog(field);
    };
  }

  function wireViewToggle(): void {
    const structuredBtn = document.getElementById("view-structured-btn");
    const interactiveBtn = document.getElementById("view-interactive-btn");
    const structuredView = document.getElementById("form-guide-structured-view");
    const interactiveView = document.getElementById("form-guide-interactive-view");
    const mainContainer = document.querySelector(".form-guide-main") as HTMLElement | null;

    if (!structuredBtn || !interactiveBtn || !structuredView || !interactiveView) return;

    structuredBtn.onclick = () => {
      setGuideView("structured");
      structuredView.scrollIntoView({ block: "start", behavior: "smooth" });
    };

    interactiveBtn.onclick = () => {
      if (interactiveBtn.hasAttribute("disabled")) return;
      setGuideView("interactive");
      interactiveView.scrollIntoView({ block: "start", behavior: "smooth" });
    };

    state.guideViewObserver?.disconnect();
    if (typeof IntersectionObserver !== "function") return;

    state.guideViewObserver = new IntersectionObserver(
      (entries) => {
        const visibleEntries = entries
          .filter((entry) => entry.isIntersecting)
          .sort((left, right) => right.intersectionRatio - left.intersectionRatio);
        const topEntry = visibleEntries[0];
        if (!topEntry) return;
        if (topEntry.target === interactiveView && !interactiveBtn.hasAttribute("disabled")) {
          setGuideView("interactive");
          return;
        }
        if (topEntry.target === structuredView) {
          setGuideView("structured");
        }
      },
      {
        root: mainContainer,
        threshold: [0.35, 0.6, 0.85],
        rootMargin: "-12% 0px -45% 0px",
      }
    );

    state.guideViewObserver.observe(interactiveView);
    state.guideViewObserver.observe(structuredView);
  }

  function wireFieldDialog(): void {
    const dialog = document.getElementById("form-guide-field-dialog") as HTMLDialogElement | null;
    const closeBtn = document.getElementById("close-field-dialog");

    if (!dialog) return;

    if (closeBtn) {
      closeBtn.onclick = () => closeDialogSafely(dialog);
    }

    dialog.onclick = (event) => {
      if (event.defaultPrevented) return;
      closeDialogSafely(dialog);
    };
  }

  function wireSourcesDialog(): void {
    const btn = document.getElementById("form-guide-sources-btn");
    const dialog = document.getElementById("form-guide-sources-dialog") as HTMLDialogElement | null;
    const closeBtn = document.getElementById("close-sources-dialog");
    const sourcesList = document.getElementById("sources-list");

    if (!btn || !dialog || !sourcesList) return;

    btn.onclick = () => {
      sourcesList.innerHTML = state.guideSources
        .map(
          (source) => `
          <div class="source-card ${source.is_primary ? "source-primary" : "source-secondary"}">
            <p class="source-title">${escapeHtml(uiText(source.title))}</p>
            <p class="source-authority">${escapeHtml(uiText(source.authority))} · ${source.is_primary ? "Fuente primaria" : "Fuente secundaria"}</p>
            ${source.url ? `<a href="${escapeHtml(source.url)}" target="_blank" rel="noopener noreferrer" class="source-link">Ver fuente</a>` : ""}
            ${source.notes ? `<p class="source-notes">${escapeHtml(uiText(source.notes))}</p>` : ""}
            <p class="source-checked">Verificada: ${escapeHtml(source.last_checked_date)}</p>
          </div>
        `
        )
        .join("");
      openDialogSafely(dialog);
    };

    if (closeBtn) {
      closeBtn.onclick = () => closeDialogSafely(dialog);
    }
    dialog.onclick = (event) => {
      if (event.target === dialog) closeDialogSafely(dialog);
    };
  }

  function wirePdfDownload(): void {
    const btn = document.getElementById("form-guide-pdf-btn") as HTMLButtonElement | null;
    if (!btn) return;

    btn.disabled = !state.guideOfficialPdfUrl;
    btn.title = state.guideOfficialPdfUrl
      ? state.guideOfficialPdfAuthority
        ? `Abre el PDF oficial publicado por ${state.guideOfficialPdfAuthority}`
        : "Abre el PDF oficial del formulario."
      : "Este formulario aún no tiene un PDF oficial publicado en la guía.";
    btn.onclick = () => {
      if (!state.guideOfficialPdfUrl) return;
      window.open(state.guideOfficialPdfUrl, "_blank", "noopener,noreferrer");
    };
  }

  function wireMobileMenu(): void {
    const hamburger = document.querySelector<HTMLButtonElement>(".form-guide-hamburger");
    const menu = document.querySelector<HTMLElement>(".form-guide-mobile-menu");
    if (!hamburger || !menu) return;

    hamburger.addEventListener("click", () => {
      menu.hidden = !menu.hidden;
    });

    // Close menu when clicking outside
    document.addEventListener("click", (e) => {
      if (!menu.hidden && !menu.contains(e.target as Node) && e.target !== hamburger && !hamburger.contains(e.target as Node)) {
        menu.hidden = true;
      }
    });

    // Wire mobile sources button to desktop handler
    const srcMobile = document.getElementById("form-guide-sources-btn-mobile");
    const srcDesktop = document.getElementById("form-guide-sources-btn");
    if (srcMobile && srcDesktop) {
      srcMobile.addEventListener("click", () => { menu.hidden = true; srcDesktop.click(); });
    }

    // Wire mobile PDF button to desktop handler
    const pdfMobile = document.getElementById("form-guide-pdf-btn-mobile");
    const pdfDesktop = document.getElementById("form-guide-pdf-btn");
    if (pdfMobile && pdfDesktop) {
      pdfMobile.addEventListener("click", () => { menu.hidden = true; pdfDesktop.click(); });
    }
  }

  function showLoading(): void {
    const loadingEl = document.getElementById("form-guide-loading");
    const selectorEl = document.getElementById("form-guide-profile-selector");
    const errorEl = document.getElementById("form-guide-error");
    const contentEl = document.getElementById("form-guide-content");
    if (loadingEl) loadingEl.hidden = false;
    if (selectorEl) selectorEl.hidden = true;
    if (errorEl) errorEl.hidden = true;
    if (contentEl) contentEl.hidden = true;
  }

  function showProfileSelector(catalog: GuideCatalogEntry, onSelect: (profileId: string) => void): void {
    const loadingEl = document.getElementById("form-guide-loading");
    const selectorEl = document.getElementById("form-guide-profile-selector");
    const optionsEl = document.getElementById("profile-options");
    if (loadingEl) loadingEl.hidden = true;
    if (!selectorEl || !optionsEl) return;

    selectorEl.hidden = false;
    optionsEl.innerHTML = catalog.available_profiles
      .map(
        (profile) => `
          <button class="profile-option-btn" type="button" data-profile="${profile.profile_id}">
            <strong>${uiText(profile.profile_label)}</strong>
          </button>
        `
      )
      .join("");

    optionsEl.onclick = (event) => {
      const btn = (event.target as HTMLElement).closest("[data-profile]") as HTMLElement | null;
      if (!btn) return;
      selectorEl.hidden = true;
      onSelect(btn.dataset.profile || "");
    };
  }

  function showError(message: string): void {
    const loadingEl = document.getElementById("form-guide-loading");
    const errorEl = document.getElementById("form-guide-error");
    const errorMsg = document.getElementById("form-guide-error-message");
    if (loadingEl) loadingEl.hidden = true;
    if (errorEl) errorEl.hidden = false;
    if (errorMsg) errorMsg.textContent = uiText(message);
  }

  function renderGuide(data: GuideContentResponse): void {
    const loadingEl = document.getElementById("form-guide-loading");
    const contentEl = document.getElementById("form-guide-content");
    const disclaimerEl = document.getElementById("form-guide-disclaimer");
    state.guideSectionsById = new Map(data.structured_sections.map((section) => [section.section_id, section]));
    state.guideHotspotsById = new Map(data.interactive_map.map((field) => [field.field_id, field]));

    if (loadingEl) loadingEl.hidden = true;
    if (contentEl) contentEl.hidden = false;

    const titleEl = document.getElementById("form-guide-title");
    const profileEl = document.getElementById("form-guide-profile");
    const versionEl = document.getElementById("form-guide-version");
    const verifiedEl = document.getElementById("form-guide-verified");

    if (titleEl) titleEl.textContent = uiText(data.manifest.title);
    if (profileEl) profileEl.textContent = uiText(data.manifest.profile_label);
    if (versionEl) versionEl.textContent = uiText(data.manifest.form_version);
    if (verifiedEl) verifiedEl.textContent = `Última verificación: ${data.manifest.last_verified_date}`;

    if (disclaimerEl && data.disclaimer) {
      disclaimerEl.textContent = uiText(data.disclaimer);
      disclaimerEl.hidden = false;
    }

    renderStructuredView(data.structured_sections, data.interactive_map);

    const interactiveBtn = document.getElementById("view-interactive-btn");
    const hasInteractiveViewer = data.interactive_map.length > 0 && state.guidePageAssets.length > 0;
    if (!hasInteractiveViewer && interactiveBtn) {
      interactiveBtn.setAttribute("disabled", "true");
      interactiveBtn.title = "Guía gráfica no disponible para esta guía";
      renderInteractiveFallback("La guía textual sigue disponible mientras se publica el mapa gráfico certificado.");
    } else if (interactiveBtn) {
      interactiveBtn.removeAttribute("disabled");
      interactiveBtn.title = "";
      renderInteractiveMap(data.interactive_map, state.guidePageAssets);
    } else if (hasInteractiveViewer) {
      renderInteractiveMap(data.interactive_map, state.guidePageAssets);
    }

    wireViewToggle();
    wireFieldDialog();
    wireSourcesDialog();
    wirePdfDownload();
    wireMobileMenu();
    const preferText = window.matchMedia("(max-width: 640px)").matches;
    setGuideView(preferText ? "structured" : (hasInteractiveViewer ? "interactive" : "structured"));
    syncGuideSelection();
    updateChatContext();
  }

  return {
    renderGuide,
    showError,
    showLoading,
    showProfileSelector,
  };
}
// @ts-nocheck
