import type { I18nRuntime } from "@/shared/i18n";

export function renderOrchestrationShell(i18n: I18nRuntime): string {
  return `
    <main class="orch-shell">
      <header class="orch-header">
        <div class="orch-brand">
          <a href="/" class="nav-link orch-back-link">${i18n.t("common.backToChat")}</a>
          <div class="orch-brand-copy">
            <p class="orch-eyebrow">Mapa vivo del runtime</p>
            <h1 class="orch-title">Arquitectura de Información y Orquestación</h1>
            <p class="orch-subtitle">
              Cómo viaja la información desde la pregunta del contador hasta la respuesta visible, qué contrato entrega cada capa y dónde terminan los límites entre lógica compartida, los seams estables de cada superficie y los tres tracks post-answer: bubble principal, Normativa e Interpretación.
            </p>
          </div>
        </div>

        <div class="orch-status-stack">
          <div class="orch-status-card">
            <span class="orch-status-label">Pipeline servido</span>
            <strong>pipeline_d</strong>
          </div>
          <div class="orch-status-card">
            <span class="orch-status-label">Última granularización</span>
            <strong>2026-04-20 · ui13</strong>
          </div>
          <div class="orch-status-card">
            <span class="orch-status-label">Env matrix</span>
            <strong>v2026-04-22-betaflipsall</strong>
          </div>
          <div class="orch-status-card">
            <span class="orch-status-label">Retrieval (dev / staging)</span>
            <strong>artifacts + local Falkor / Supabase + FalkorDB live</strong>
          </div>
        </div>
      </header>

      <section class="orch-toolbar">
        <nav class="orch-nav" aria-label="Navegación de arquitectura">
          <a class="orch-nav-btn" href="#orch-overview" data-target="orch-overview">Vista general</a>
          <a class="orch-nav-btn" href="#orch-contracts" data-target="orch-contracts">Contratos</a>
          <a class="orch-nav-btn" href="#orch-lanes" data-target="orch-lanes">Lanes</a>
          <a class="orch-nav-btn" href="#orch-modules" data-target="orch-modules">Módulos</a>
          <a class="orch-nav-btn" href="#orch-surfaces" data-target="orch-surfaces">Superficies</a>
          <a class="orch-nav-btn" href="#orch-tuning" data-target="orch-tuning">Tuning</a>
        </nav>

        <div class="orch-filter-group" role="toolbar" aria-label="Filtrar módulos por alcance">
          <button class="orch-filter-btn" data-scope-filter="all" aria-pressed="true">Todos</button>
          <button class="orch-filter-btn" data-scope-filter="shared" aria-pressed="false">Compartido</button>
          <button class="orch-filter-btn" data-scope-filter="main-chat" aria-pressed="false">Main chat</button>
          <button class="orch-filter-btn" data-scope-filter="normativa" aria-pressed="false">Normativa</button>
          <button class="orch-filter-btn" data-scope-filter="interpretacion" aria-pressed="false">Interpretación</button>
          <button class="orch-filter-btn" data-scope-filter="reader-windows" aria-pressed="false">Ventanas lectoras</button>
        </div>
      </section>

      <section id="orch-scroll" class="orch-scroll">
        <div id="orch-content" class="orch-content"></div>
      </section>
    </main>
  `;
}
