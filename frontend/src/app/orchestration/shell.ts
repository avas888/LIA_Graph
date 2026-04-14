import type { I18nRuntime } from "@/shared/i18n";

export function renderOrchestrationShell(i18n: I18nRuntime): string {
  return `
    <main class="orch-shell">
      <header class="orch-header">
        <div class="orch-header-left">
          <a href="/" class="nav-link orch-back-link">${i18n.t("common.backToChat")}</a>
          <div class="orch-header-title-group">
            <p class="orch-eyebrow">${i18n.t("orch.eyebrow")}</p>
            <h1 class="orch-title">${i18n.t("orch.title")}</h1>
          </div>
        </div>
        <div class="orch-header-center">
          <nav class="orch-lane-nav" aria-label="${i18n.t("orch.laneNav")}">
            <button class="orch-lane-btn" data-lane="ingesta">${i18n.t("orch.lane.ingesta")}</button>
            <button class="orch-lane-btn" data-lane="parsing">${i18n.t("orch.lane.parsing")}</button>
            <button class="orch-lane-btn" data-lane="almacenamiento">${i18n.t("orch.lane.almacenamiento")}</button>
            <button class="orch-lane-btn" data-lane="retrieval">${i18n.t("orch.lane.retrieval")}</button>
            <button class="orch-lane-btn" data-lane="surfaces">${i18n.t("orch.lane.surfaces")}</button>
          </nav>
        </div>
        <div class="orch-header-right">
          <div class="orch-legend" aria-label="${i18n.t("orch.legend")}">
            <span class="orch-legend-item" data-actor="curator">
              <span class="orch-actor-dot" data-actor="curator"></span>
              ${i18n.t("orch.actor.curator")}
            </span>
            <span class="orch-legend-item" data-actor="python">
              <span class="orch-actor-dot" data-actor="python"></span>
              ${i18n.t("orch.actor.python")}
            </span>
            <span class="orch-legend-item" data-actor="sql">
              <span class="orch-actor-dot" data-actor="sql"></span>
              ${i18n.t("orch.actor.sql")}
            </span>
            <span class="orch-legend-item" data-actor="llm">
              <span class="orch-actor-dot" data-actor="llm"></span>
              ${i18n.t("orch.actor.llm")}
            </span>
            <span class="orch-legend-item" data-actor="embedding">
              <span class="orch-actor-dot" data-actor="embedding"></span>
              ${i18n.t("orch.actor.embedding")}
            </span>
          </div>
        </div>
      </header>

      <div id="orch-viewport" class="orch-viewport">
        <div id="orch-canvas" class="orch-canvas">
          <svg id="orch-svg" class="orch-svg-overlay"></svg>
        </div>
      </div>

      <div id="orch-minimap" class="orch-minimap">
        <canvas id="orch-minimap-canvas" width="220" height="154"></canvas>
        <div id="orch-minimap-lens" class="orch-minimap-lens"></div>
      </div>
    </main>
  `;
}
