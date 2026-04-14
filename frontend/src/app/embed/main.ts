import "@/styles/main.css";
import { ApiError, clearApiAccessToken, postJson, setApiAccessToken } from "@/shared/api/client";

type EmbedExchangeResponse = {
  ok?: boolean;
  access_token?: string;
  expires_at?: number;
  me?: {
    tenant_id?: string;
    user_id?: string;
    active_company_id?: string;
    integration_id?: string;
  };
};

type EmbedInitMessage = {
  type?: string;
  grant?: string;
  host_grant?: string;
};

const root = document.querySelector<HTMLElement>("#app");

if (!root) {
  throw new Error("Missing #app root.");
}

root.innerHTML = `
  <main class="ops-shell">
    <section class="ops-card ops-window" style="max-width: 780px; margin: 8vh auto;">
      <div class="ops-window-head">
        <div>
          <p class="eyebrow">Embed Gateway</p>
          <h1 style="margin: 0.25rem 0 0;">LIA embebido</h1>
        </div>
      </div>
      <div class="ops-window-body">
        <p id="embed-status" class="ops-copy">Esperando grant firmado de la app host.</p>
        <pre id="embed-detail" class="diagnostics" style="white-space: pre-wrap;">Handshake pendiente.</pre>
      </div>
    </section>
  </main>
`;

const statusNode = root.querySelector<HTMLElement>("#embed-status");
const detailNode = root.querySelector<HTMLElement>("#embed-detail");

function renderStatus(message: string, detail: string): void {
  if (statusNode) statusNode.textContent = message;
  if (detailNode) detailNode.textContent = detail;
}

async function exchangeGrant(grant: string): Promise<void> {
  renderStatus("Intercambiando sesion con LIA...", "Validando grant, origin y alcance de tenant.");
  try {
    const { response, data } = await postJson<EmbedExchangeResponse, { grant: string }>("/api/embed/exchange", { grant });
    if (!response.ok || !data?.access_token) {
      const payloadMessage =
        data && typeof data === "object" && "error" in data ? JSON.stringify((data as { error?: unknown }).error) : response.statusText;
      throw new ApiError(payloadMessage || "exchange_failed", response.status, data);
    }
    setApiAccessToken(data.access_token);
    renderStatus(
      "Sesion embebida lista.",
      `tenant=${data.me?.tenant_id || "-"} user=${data.me?.user_id || "-"} company=${data.me?.active_company_id || "-"} integration=${data.me?.integration_id || "-"}`
    );
    window.setTimeout(() => {
      window.location.replace("/");
    }, 250);
  } catch (error) {
    clearApiAccessToken();
    const message = error instanceof Error ? error.message : "exchange_failed";
    renderStatus("No fue posible inicializar el embed.", message);
  }
}

window.addEventListener("message", (event: MessageEvent<EmbedInitMessage>) => {
  const payload = event.data;
  if (!payload || payload.type !== "lia:init") {
    return;
  }
  const grant = String(payload.grant || payload.host_grant || "").trim();
  if (!grant) {
    renderStatus("Grant faltante.", "La app host envio `lia:init` sin grant firmado.");
    return;
  }
  void exchangeGrant(grant);
});

clearApiAccessToken();
window.parent?.postMessage({ type: "lia:ready" }, "*");
