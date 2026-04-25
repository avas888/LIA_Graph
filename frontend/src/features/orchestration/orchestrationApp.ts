import type { I18nRuntime } from "@/shared/i18n";
import {
  type ContractCard,
  type LaneCard,
  type ModuleCard,
  contractCards,
  laneCards,
  moduleCards,
  tuningRows,
} from "@/features/orchestration/orchestrationCards";

export function mountOrchestrationApp(
  root: HTMLElement,
  _ctx: { i18n: I18nRuntime },
): void {
  const content = root.querySelector<HTMLElement>("#orch-content");
  const scrollRoot = root.querySelector<HTMLElement>("#orch-scroll");
  if (!content || !scrollRoot) return;

  content.innerHTML = renderPage();

  const navButtons = Array.from(root.querySelectorAll<HTMLElement>(".orch-nav-btn"));
  navButtons.forEach((button) => {
    button.addEventListener("click", (event) => {
      const targetId = button.dataset.target;
      if (!targetId) return;
      const target = root.querySelector<HTMLElement>(`#${targetId}`);
      if (!target) return;
      event.preventDefault();
      const toolbar = root.querySelector<HTMLElement>(".orch-toolbar");
      const toolbarOffset = (toolbar?.getBoundingClientRect().height || 0) + 18;
      const top = Math.max(0, target.getBoundingClientRect().top + window.scrollY - toolbarOffset);
      try {
        window.scrollTo({ top, behavior: "smooth" });
      } catch (_error) {
        target.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    });
  });

  const filterButtons = Array.from(root.querySelectorAll<HTMLButtonElement>(".orch-filter-btn"));
  const moduleCards = Array.from(root.querySelectorAll<HTMLElement>(".orch-module-card"));

  const applyScopeFilter = (scope: string) => {
    filterButtons.forEach((button) => {
      button.setAttribute("aria-pressed", String(button.dataset.scopeFilter === scope));
    });
    moduleCards.forEach((card) => {
      const cardScope = card.dataset.scope;
      card.hidden = !(scope === "all" || cardScope === scope);
    });
  };

  filterButtons.forEach((button) => {
    button.addEventListener("click", () => {
      applyScopeFilter(button.dataset.scopeFilter || "all");
    });
  });

  applyScopeFilter("all");
}

function renderPage(): string {
  return `
    <section id="orch-overview" class="orch-section orch-hero-section">
      <div class="orch-section-header">
        <p class="orch-section-kicker">Vista general</p>
        <h2 class="orch-section-title">La arquitectura nueva está organizada por contratos y facades</h2>
        <p class="orch-section-copy">
          La idea central ya no es “un orchestrator enorme que hace todo”, sino una cadena de handoffs explícitos:
          request normalizado, retrieval plan, evidence bundle, enrichment insights, answer parts, assembly visible y response contract.
        </p>
      </div>

      <div class="orch-overview-grid">
        <article class="orch-highlight-card">
          <span class="orch-highlight-label">Request path</span>
          <h3>ui_server → pipeline_router → topic_router → orchestrator</h3>
          <p>La ruta pública es corta y clara. El detalle vive detrás de Pipeline D, no disperso por la UI.</p>
        </article>
        <article class="orch-highlight-card">
          <span class="orch-highlight-label">Execution path</span>
          <h3>planner → retriever → synthesis facade → assembly facade</h3>
          <p>La ejecución interna ya distingue evidencia, síntesis y publicación visible, incluyendo first turn vs second+ follow-up del chat.</p>
        </article>
        <article class="orch-highlight-card">
          <span class="orch-highlight-label">Surface rule</span>
          <h3>Cada ventana tiene su propia assembly: chat, Normativa, Interpretación y lectores</h3>
          <p>Se comparte graph logic cuando tiene sentido. La UX contract se separa por superficie.</p>
        </article>
        <article class="orch-highlight-card">
          <span class="orch-highlight-label">Post-answer tracks</span>
          <h3>Bubble primero; Normativa e Interpretación arrancan después con el mismo kernel mínimo</h3>
          <p>Las ventanas laterales son sibling tracks. No bloquean el bubble ni se bloquean entre sí más allá de la semilla del turno.</p>
        </article>
        <article class="orch-highlight-card">
          <span class="orch-highlight-label">Env matrix v2026-04-25-temafirst-readdressed</span>
          <h3>dev lee artifacts; dev:staging lee Supabase + FalkorDB live</h3>
          <p>LIA_CORPUS_SOURCE y LIA_GRAPH_MODE, seteados por scripts/dev-launcher.mjs, eligen el adapter por request. Tabla versionada y change log viven en docs/guide/orchestration.md.</p>
        </article>
      </div>
    </section>

    <section id="orch-contracts" class="orch-section">
      <div class="orch-section-header">
        <p class="orch-section-kicker">Information architecture</p>
        <h2 class="orch-section-title">Mapa de contratos</h2>
        <p class="orch-section-copy">
          Esta es la secuencia más importante para entender el runtime: cada capa produce un contrato claro que la siguiente consume.
        </p>
      </div>
      <div class="orch-contract-flow">
        ${contractCards.map(renderContractCard).join("")}
      </div>
    </section>

    <section id="orch-lanes" class="orch-section">
      <div class="orch-section-header">
        <p class="orch-section-kicker">Runtime lanes</p>
        <h2 class="orch-section-title">Del corpus al answer visible</h2>
        <p class="orch-section-copy">
          Los lanes ordenan la historia completa: build-time, runtime path, synthesis, assembly y packaging.
        </p>
      </div>
      <div class="orch-lane-grid">
        ${laneCards.map(renderLaneCard).join("")}
      </div>
    </section>

    <section id="orch-modules" class="orch-section">
      <div class="orch-section-header">
        <p class="orch-section-kicker">Module map</p>
        <h2 class="orch-section-title">Quién hace qué</h2>
        <p class="orch-section-copy">
          Los filtros de arriba recortan este mapa por alcance. Las facades estables son las puertas correctas; los demás módulos son implementación más específica.
        </p>
      </div>
      <div class="orch-module-grid">
        ${moduleCards.map(renderModuleCard).join("")}
      </div>
    </section>

    <section id="orch-surfaces" class="orch-section">
      <div class="orch-section-header">
        <p class="orch-section-kicker">Surface boundaries</p>
        <h2 class="orch-section-title">Qué se comparte y qué no</h2>
        <p class="orch-section-copy">
          El principal cambio de arquitectura es este límite: la lógica de evidencia puede compartirse; la assembly visible no.
        </p>
      </div>
      <div class="orch-boundary-grid">
        <article class="orch-boundary-card" data-tone="shared">
          <h3>Graph runtime compartido</h3>
          <ul>
            <li>Request normalization</li>
            <li>Topic routing y guardrails</li>
            <li>Planner</li>
            <li>Retriever y evidence bundle</li>
            <li>Enrichment extraction si realmente aplica a varias superficies</li>
          </ul>
        </article>
        <article class="orch-boundary-card" data-tone="main-chat">
          <h3>Main chat</h3>
          <ul>
            <li>answer_synthesis facade</li>
            <li>answer_assembly facade</li>
            <li>first bubble shapes</li>
            <li>follow-up publication path</li>
            <li>inline legal anchors del chat</li>
            <li>historical recap del chat</li>
          </ul>
        </article>
        <article class="orch-boundary-card" data-tone="future">
          <h3>Normativa</h3>
          <ul>
            <li>capa determinística de citation/profile</li>
            <li>paquete propio src/lia_graph/normativa/* para enrichment</li>
            <li>reutiliza planner/retriever compartidos cuando aplica</li>
            <li>no consume el first bubble del chat como UI contract</li>
          </ul>
        </article>
        <article class="orch-boundary-card" data-tone="future">
          <h3>Interpretación</h3>
          <ul>
            <li>controller seam + paquete propio src/lia_graph/interpretacion/*</li>
            <li>ranking, grouping, summary y explore propios</li>
            <li>puede compartir evidence utilities</li>
            <li>arranca después del bubble sin esperar el retrieval completo de Normativa</li>
            <li>no debe piggybackear sobre Normativa ni sobre main chat</li>
          </ul>
        </article>
        <article class="orch-boundary-card" data-tone="shared">
          <h3>Lectores documentales</h3>
          <ul>
            <li>source view, article reader y form/document windows</li>
            <li>assembly determinística basada en texto y metadata</li>
            <li>pueden consumir procesadores normativos</li>
            <li>no pasan por answer_* del chat</li>
          </ul>
        </article>
      </div>

      <div class="orch-warning-card">
        <strong>Regla de diseño:</strong>
        comparte retrieval y evidence cuando convenga; separa siempre la assembly visible por superficie.
      </div>
    </section>

    <section id="orch-tuning" class="orch-section">
      <div class="orch-section-header">
        <p class="orch-section-kicker">Tuning guide</p>
        <h2 class="orch-section-title">Si algo sale mal, toca la capa correcta</h2>
        <p class="orch-section-copy">
          Esta tabla existe para evitar regressions por tocar el módulo equivocado.
        </p>
      </div>
      <div class="orch-tuning-table">
        ${tuningRows.map(renderTuningRow).join("")}
      </div>
    </section>
  `;
}

function renderContractCard(card: ContractCard): string {
  return `
    <article class="orch-contract-card">
      <span class="orch-contract-producer">${card.producer}</span>
      <h3>${card.title}</h3>
      <p class="orch-contract-chain">${card.contract} <span>→</span> ${card.consumer}</p>
      <span class="orch-scope-pill">${card.scope}</span>
      <ul>
        ${card.bullets.map((bullet) => `<li>${bullet}</li>`).join("")}
      </ul>
    </article>
  `;
}

function renderLaneCard(card: LaneCard): string {
  return `
    <article class="orch-lane-card" id="${card.id}">
      <div class="orch-lane-index">${card.number}</div>
      <div class="orch-lane-copy">
        <h3>${card.title}</h3>
        <p>${card.summary}</p>
        <ul>
          ${card.bullets.map((bullet) => `<li>${bullet}</li>`).join("")}
        </ul>
      </div>
    </article>
  `;
}

function renderModuleCard(card: ModuleCard): string {
  return `
    <article class="orch-module-card" data-scope="${card.scope}">
      <div class="orch-module-topline">
        <span class="orch-module-scope" data-scope-tone="${card.scope}">${formatScope(card.scope)}</span>
        <span class="orch-module-stability" data-stability="${card.stability}">${formatStability(card.stability)}</span>
      </div>
      <h3>${card.title}</h3>
      <p class="orch-module-path">${card.path}</p>
      <p class="orch-module-role">${card.role}</p>
      <dl class="orch-module-contract">
        <div>
          <dt>Consume</dt>
          <dd>${card.consumes}</dd>
        </div>
        <div>
          <dt>Produce</dt>
          <dd>${card.produces}</dd>
        </div>
      </dl>
      <ul class="orch-module-list">
        ${card.bullets.map((bullet) => `<li>${bullet}</li>`).join("")}
      </ul>
    </article>
  `;
}

function renderTuningRow(row: { symptom: string; edit: string; why: string }): string {
  return `
    <article class="orch-tuning-row">
      <div>
        <span class="orch-tuning-label">Síntoma</span>
        <p>${row.symptom}</p>
      </div>
      <div>
        <span class="orch-tuning-label">Edita</span>
        <p><code>${row.edit}</code></p>
      </div>
      <div>
        <span class="orch-tuning-label">Por qué</span>
        <p>${row.why}</p>
      </div>
    </article>
  `;
}

function formatScope(scope: ModuleCard["scope"]): string {
  if (scope === "shared") return "Compartido";
  if (scope === "main-chat") return "Main chat";
  if (scope === "normativa") return "Normativa";
  if (scope === "interpretacion") return "Interpretación";
  return "Ventanas lectoras";
}

function formatStability(stability: ModuleCard["stability"]): string {
  if (stability === "stable-facade") return "Facade estable";
  if (stability === "surface-seam") return "Surface seam";
  return "Implementación";
}
