import type { I18nRuntime } from "@/shared/i18n";

export function renderNormativeAnalysisShell(i18n: I18nRuntime): string {
  return `
    <main class="normative-analysis-shell">
      <header class="normative-analysis-header">
        <div class="normative-analysis-header-info">
          <p id="normative-analysis-family" class="form-guide-eyebrow"></p>
          <h1 id="normative-analysis-title">${i18n.t("normativeAnalysis.loadingTitle")}</h1>
          <p id="normative-analysis-binding" class="normative-analysis-binding" hidden></p>
        </div>
        <div class="normative-analysis-header-actions">
          <a href="/" class="nav-link form-guide-back-link">${i18n.t("common.backToChat")}</a>
        </div>
      </header>

      <div id="normative-analysis-loading" class="form-guide-loading">
        <p>${i18n.t("normativeAnalysis.loading")}</p>
      </div>

      <div id="normative-analysis-error" class="form-guide-error" hidden>
        <p id="normative-analysis-error-message">${i18n.t("normativeAnalysis.error")}</p>
        <a href="/" class="primary-btn">${i18n.t("common.backToChat")}</a>
      </div>

      <div id="normative-analysis-content" class="normative-analysis-layout" hidden>
        <section class="normative-analysis-main">
          <div id="normative-analysis-caution" class="normative-analysis-caution" hidden>
            <strong id="normative-analysis-caution-title"></strong>
            <p id="normative-analysis-caution-body"></p>
          </div>

          <p id="normative-analysis-lead" class="normative-analysis-lead"></p>
          <div id="normative-analysis-facts" class="normative-analysis-facts"></div>
          <div id="normative-analysis-sections" class="normative-analysis-sections"></div>
        </section>

        <aside class="normative-analysis-sidebar">
          <section class="guide-page-card">
            <div class="guide-page-header">
              <h2>${i18n.t("normativeAnalysis.timelineTitle")}</h2>
              <p>${i18n.t("normativeAnalysis.timelineSubtitle")}</p>
            </div>
            <div id="normative-analysis-timeline" class="normative-analysis-timeline"></div>
          </section>

          <section class="guide-page-card">
            <div class="guide-page-header">
              <h2>${i18n.t("normativeAnalysis.relationsTitle")}</h2>
              <p>${i18n.t("normativeAnalysis.relationsSubtitle")}</p>
            </div>
            <div id="normative-analysis-relations" class="normative-analysis-relations"></div>
          </section>

          <section class="guide-page-card">
            <div class="guide-page-header">
              <h2>${i18n.t("normativeAnalysis.overlaysTitle")}</h2>
              <p>${i18n.t("normativeAnalysis.overlaysSubtitle")}</p>
            </div>
            <div id="normative-analysis-overlays" class="normative-analysis-overlays"></div>
          </section>

          <section class="guide-page-card">
            <div class="guide-page-header">
              <h2>${i18n.t("normativeAnalysis.actionsTitle")}</h2>
              <p>${i18n.t("normativeAnalysis.actionsSubtitle")}</p>
            </div>
            <div id="normative-analysis-actions" class="normative-analysis-actions"></div>
          </section>
        </aside>
      </div>
    </main>
  `;
}
