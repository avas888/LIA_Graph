import { ApiError, getJson } from "@/shared/api/client";
import { createBadge } from "@/shared/ui/atoms/badge";
import { createFactCard } from "@/shared/ui/molecules/factCard";

// ── Types ──

type ServiceAccountEntry = {
  service_account_id?: string;
  display_name?: string;
  secret_hint?: string;
  status?: string;
  created_at?: string;
  last_used_at?: string | null;
};

type ServiceAccountsResponse = {
  ok?: boolean;
  service_accounts?: ServiceAccountEntry[];
};

type EvalStats = {
  total_requests?: number;
  total_errors?: number;
  error_rate?: number;
  total_input_tokens?: number;
  total_output_tokens?: number;
  total_tokens?: number;
  latency_p50_ms?: number;
  latency_p95_ms?: number;
  by_endpoint?: { endpoint?: string; requests?: number; errors?: number }[];
};

type EvalStatsResponse = {
  ok?: boolean;
  stats?: EvalStats;
};

type EvalLogEntry = {
  log_id?: string;
  endpoint?: string;
  method?: string;
  status_code?: number;
  latency_ms?: number | null;
  input_tokens?: number;
  output_tokens?: number;
  created_at?: string;
  eval_run_id?: string;
  eval_turn_id?: string;
  request_body?: unknown;
  response_summary?: unknown;
  error?: string | null;
};

type EvalLogsResponse = {
  ok?: boolean;
  logs?: EvalLogEntry[];
  total?: number;
  limit?: number;
  offset?: number;
};

// ── State ──

let _currentOffset = 0;
const PAGE_SIZE = 20;

// ── Public entry point ──

export function mountAdminApiTab(container: HTMLElement, _tenantId: string): void {
  container.innerHTML = renderApiTabShell();

  const keySection = container.querySelector<HTMLElement>("#admin-api-key-section");
  const statsSection = container.querySelector<HTMLElement>("#admin-api-stats");
  const logsSection = container.querySelector<HTMLElement>("#admin-api-logs");
  const logsPage = container.querySelector<HTMLElement>("#admin-api-logs-pagination");
  const refreshBtn = container.querySelector<HTMLButtonElement>("#admin-api-logs-refresh");

  if (keySection) loadServiceAccounts(keySection);
  if (statsSection) loadEvalStats(statsSection);
  if (logsSection && logsPage) loadEvalLogs(logsSection, logsPage, 0);

  refreshBtn?.addEventListener("click", () => {
    if (logsSection && logsPage) loadEvalLogs(logsSection, logsPage, _currentOffset);
  });
}

// ── Shell HTML ──

function renderApiTabShell(): string {
  return `
    <div class="admin-api-shell">
      <article class="ops-card ops-window">
        <div class="ops-window-head">
          <h2>Credenciales del servicio</h2>
        </div>
        <div class="ops-window-body">
          <div id="admin-api-key-section">
            <p class="admin-api-empty">Cargando credenciales...</p>
          </div>
        </div>
      </article>

      <article class="ops-card ops-window" style="grid-column: 1 / -1">
        <div class="ops-window-head">
          <h2>Estadisticas de uso</h2>
        </div>
        <div class="ops-window-body">
          <div id="admin-api-stats" class="admin-api-stats-grid">
            <p class="admin-api-empty">Cargando estadisticas...</p>
          </div>
        </div>
      </article>

      <article class="ops-card ops-window" style="grid-column: 1 / -1">
        <div class="ops-window-head" style="display:flex;justify-content:space-between;align-items:center">
          <h2>Logs recientes</h2>
          <button id="admin-api-logs-refresh" class="admin-api-copy-btn">Actualizar</button>
        </div>
        <div class="ops-window-body">
          <div id="admin-api-logs">
            <p class="admin-api-empty">Cargando logs...</p>
          </div>
          <div id="admin-api-logs-pagination" class="admin-api-pagination"></div>
        </div>
      </article>
    </div>
  `;
}

// ── Service accounts ──

async function loadServiceAccounts(section: HTMLElement): Promise<void> {
  try {
    const data = await getJson<ServiceAccountsResponse>("/api/admin/eval/service-accounts");
    const accounts = data.service_accounts || [];
    if (accounts.length === 0) {
      section.innerHTML = `<p class="admin-api-empty">No hay cuentas de servicio configuradas.</p>`;
      return;
    }
    section.innerHTML = "";
    for (const account of accounts) {
      section.appendChild(renderKeyCard(account));
    }
  } catch (err) {
    const msg = err instanceof ApiError ? `${err.status}: ${err.message}` : "Error al cargar credenciales";
    section.innerHTML = `<p class="admin-api-empty" style="color:var(--status-error)">${msg}</p>`;
  }
}

function renderKeyCard(account: ServiceAccountEntry): HTMLElement {
  const wrapper = document.createElement("div");

  // Key row
  const row = document.createElement("div");
  row.className = "admin-api-key-row";

  const hint = document.createElement("code");
  hint.className = "admin-api-key-hint";
  hint.textContent = account.secret_hint || account.service_account_id || "—";

  const copyBtn = document.createElement("button");
  copyBtn.className = "admin-api-copy-btn";
  copyBtn.textContent = "Copiar";
  wireCopyButton(copyBtn, () => hint.textContent || "");

  const badge = createBadge({
    label: account.status || "unknown",
    tone: account.status === "active" ? "success" : "error",
  });

  row.append(hint, copyBtn, badge);

  // Meta row
  const meta = document.createElement("div");
  meta.className = "admin-api-key-meta";
  const created = account.created_at ? new Date(account.created_at).toLocaleDateString() : "—";
  const lastUsed = account.last_used_at ? new Date(account.last_used_at).toLocaleString() : "nunca";
  meta.innerHTML = `<small>${account.display_name || ""} &mdash; Creada: ${created} &mdash; Ultimo uso: ${lastUsed}</small>`;

  wrapper.append(row, meta);
  return wrapper;
}

// ── Stats ──

async function loadEvalStats(section: HTMLElement): Promise<void> {
  try {
    const data = await getJson<EvalStatsResponse>("/api/admin/eval/stats");
    const s = data.stats || {};
    section.innerHTML = "";

    const cards: { label: string; value: string }[] = [
      { label: "Total Requests", value: String(s.total_requests ?? 0) },
      { label: "Errores", value: String(s.total_errors ?? 0) },
      { label: "Error Rate", value: `${((s.error_rate ?? 0) * 100).toFixed(1)}%` },
      { label: "Latencia p50", value: `${s.latency_p50_ms ?? 0}ms` },
      { label: "Latencia p95", value: `${s.latency_p95_ms ?? 0}ms` },
      { label: "Input Tokens", value: formatNumber(s.total_input_tokens ?? 0) },
      { label: "Output Tokens", value: formatNumber(s.total_output_tokens ?? 0) },
    ];

    for (const card of cards) {
      section.appendChild(createFactCard(card));
    }
  } catch (err) {
    const msg = err instanceof ApiError ? `${err.status}: ${err.message}` : "Error al cargar estadisticas";
    section.innerHTML = `<p class="admin-api-empty" style="color:var(--status-error)">${msg}</p>`;
  }
}

// ── Logs ──

async function loadEvalLogs(section: HTMLElement, pageSection: HTMLElement, offset: number): Promise<void> {
  _currentOffset = offset;
  try {
    const data = await getJson<EvalLogsResponse>(`/api/admin/eval/logs?limit=${PAGE_SIZE}&offset=${offset}`);
    const logs = data.logs || [];
    const total = data.total ?? 0;

    if (logs.length === 0) {
      section.innerHTML = `<p class="admin-api-empty">No hay logs de evaluacion.</p>`;
      pageSection.innerHTML = "";
      return;
    }

    section.innerHTML = "";
    for (const entry of logs) {
      section.appendChild(renderLogEntry(entry));
    }

    renderPagination(pageSection, total, offset, PAGE_SIZE);
  } catch (err) {
    const msg = err instanceof ApiError ? `${err.status}: ${err.message}` : "Error al cargar logs";
    section.innerHTML = `<p class="admin-api-empty" style="color:var(--status-error)">${msg}</p>`;
    pageSection.innerHTML = "";
  }
}

function renderLogEntry(entry: EvalLogEntry): HTMLElement {
  const accordion = document.createElement("div");
  accordion.className = "ops-log-accordion admin-api-log-entry";

  const summary = document.createElement("div");
  summary.className = "ops-log-accordion-summary admin-api-log-summary";
  summary.setAttribute("role", "button");
  summary.setAttribute("tabindex", "0");

  const marker = document.createElement("span");
  marker.className = "ops-log-accordion-marker";
  marker.textContent = "\u25B6";

  const method = document.createElement("span");
  method.className = "admin-api-log-method";
  method.textContent = entry.method || "POST";

  const endpoint = document.createElement("span");
  endpoint.className = "admin-api-log-endpoint";
  endpoint.textContent = entry.endpoint || "/api/eval/ask";

  const statusCode = entry.status_code ?? 0;
  const badge = createBadge({
    label: String(statusCode),
    tone: statusCode >= 200 && statusCode < 400 ? "success" : "error",
  });

  const latency = document.createElement("span");
  latency.className = "admin-api-log-latency";
  latency.textContent = entry.latency_ms != null ? `${Math.round(entry.latency_ms)}ms` : "—";

  const timeEl = document.createElement("span");
  timeEl.className = "admin-api-log-time";
  timeEl.textContent = entry.created_at ? new Date(entry.created_at).toLocaleTimeString() : "";

  const copyBtn = document.createElement("button");
  copyBtn.className = "ops-log-copy-btn";
  copyBtn.textContent = "Copiar";

  summary.append(marker, method, endpoint, badge, latency, timeEl, copyBtn);

  const body = document.createElement("pre");
  body.className = "ops-log-body";
  body.hidden = true;
  body.textContent = JSON.stringify(
    { request: entry.request_body, response_summary: entry.response_summary, error: entry.error },
    null,
    2,
  );

  wireAccordionToggle(summary, body, marker);
  wireCopyButton(copyBtn, () => body.textContent || "");

  accordion.append(summary, body);
  return accordion;
}

function renderPagination(container: HTMLElement, total: number, offset: number, limit: number): void {
  container.innerHTML = "";
  const logsSection = container.previousElementSibling as HTMLElement | null;

  const info = document.createElement("span");
  info.className = "admin-api-pagination-info";
  const start = offset + 1;
  const end = Math.min(offset + limit, total);
  info.textContent = `${start}-${end} de ${total}`;

  const btnGroup = document.createElement("div");
  btnGroup.style.display = "flex";
  btnGroup.style.gap = "0.5rem";

  const prevBtn = document.createElement("button");
  prevBtn.className = "admin-api-copy-btn";
  prevBtn.textContent = "\u2190 Anterior";
  prevBtn.disabled = offset <= 0;
  prevBtn.addEventListener("click", () => {
    if (logsSection) loadEvalLogs(logsSection, container, Math.max(0, offset - limit));
  });

  const nextBtn = document.createElement("button");
  nextBtn.className = "admin-api-copy-btn";
  nextBtn.textContent = "Siguiente \u2192";
  nextBtn.disabled = offset + limit >= total;
  nextBtn.addEventListener("click", () => {
    if (logsSection) loadEvalLogs(logsSection, container, offset + limit);
  });

  btnGroup.append(prevBtn, nextBtn);
  container.append(info, btnGroup);
}

// ── Utilities ──

function wireAccordionToggle(summary: HTMLElement, body: HTMLElement, marker: HTMLElement): void {
  const toggle = () => {
    body.hidden = !body.hidden;
    marker.textContent = body.hidden ? "\u25B6" : "\u25BC";
  };
  summary.addEventListener("click", (e) => {
    if ((e.target as HTMLElement).closest(".ops-log-copy-btn")) return;
    toggle();
  });
  summary.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      toggle();
    }
  });
}

function wireCopyButton(button: HTMLElement, getText: () => string): void {
  button.addEventListener("click", async (e) => {
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(getText());
      const original = button.textContent;
      button.textContent = "Copiado!";
      setTimeout(() => {
        button.textContent = original;
      }, 2000);
    } catch {
      // Fallback: select text
    }
  });
}

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}
