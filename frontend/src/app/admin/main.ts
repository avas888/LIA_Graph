import "@/styles/main.css";
import "@/styles/admin/users.css";
import { requireAuth } from "@/shared/auth/authGate";
import { ApiError, getJson } from "@/shared/api/client";
import { mountAdminUsers, handleInvite } from "@/features/admin/adminUsersController";

// ── Auth gate ──
if (!requireAuth()) {
  // Browser will redirect to /login.
} else {
  initAdminApp();
}

type MeResponse = {
  me?: {
    tenant_id?: string;
    user_id?: string;
    role?: string;
    active_company_id?: string;
    integration_id?: string;
  };
};

type UsageSummaryBucket = {
  group_value?: string;
  events?: number;
  total_tokens?: number;
  input_tokens?: number;
  output_tokens?: number;
  billable_events?: number;
};

type UsageSummaryResponse = {
  summary?: {
    totals?: {
      events?: number;
      total_tokens?: number;
      input_tokens?: number;
      output_tokens?: number;
      billable_events?: number;
    };
    groups?: UsageSummaryBucket[];
  };
};

type ReviewRecord = {
  trace_id?: string;
  vote?: string;
  comment?: string;
  user_id?: string;
  company_id?: string;
  timestamp?: string;
};

type ReviewsResponse = {
  reviews?: ReviewRecord[];
};

function initAdminApp(): void {
  const root = document.querySelector<HTMLElement>("#app");

  if (!root) {
    throw new Error("Missing #app root.");
  }

  root.innerHTML = `
    <main class="ops-shell">
      <header class="app-header app-hero">
        <div class="hero-copy">
          <p class="eyebrow">Admin Plane</p>
          <h1>LIA Administracion</h1>
          <p class="hero-lede">Consumo, reviews y alcance actual del tenant sin acoplar el runtime a un proveedor LLM especifico.</p>
        </div>
      </header>
      <section class="ops-backstage">
        <article class="ops-card ops-window">
          <div class="ops-window-head">
            <h2>Contexto</h2>
          </div>
          <div class="ops-window-body">
            <pre id="admin-me" class="diagnostics">Cargando identidad...</pre>
          </div>
        </article>
        <article class="ops-card ops-window">
          <div class="ops-window-head">
            <h2>Uso</h2>
          </div>
          <div class="ops-window-body">
            <pre id="admin-usage" class="diagnostics">Cargando consumo...</pre>
          </div>
        </article>
        <article class="ops-card ops-window">
          <div class="ops-window-head">
            <h2>Reviews</h2>
          </div>
          <div class="ops-window-body">
            <pre id="admin-reviews" class="diagnostics">Cargando feedback...</pre>
          </div>
        </article>
        <article class="ops-card ops-window" style="grid-column: 1 / -1">
          <div class="ops-window-head" style="display:flex;justify-content:space-between;align-items:center">
            <h2>Usuarios</h2>
            <button id="btn-invite-user" class="lia-btn lia-btn--primary" data-lia-component="invite-user-btn">+ Invitar</button>
          </div>
          <div class="ops-window-body">
            <div id="admin-users">Cargando usuarios...</div>
          </div>
        </article>
      </section>
    </main>
  `;

  const meNode = root.querySelector<HTMLElement>("#admin-me");
  const usageNode = root.querySelector<HTMLElement>("#admin-usage");
  const reviewsNode = root.querySelector<HTMLElement>("#admin-reviews");
  const usersNode = root.querySelector<HTMLElement>("#admin-users");

  function writeJson(node: HTMLElement | null, payload: unknown): void {
    if (!node) return;
    node.textContent = JSON.stringify(payload, null, 2);
  }

  async function loadAdminSurface(): Promise<void> {
    try {
      const [mePayload, usagePayload, reviewsPayload] = await Promise.all([
        getJson<MeResponse>("/api/me"),
        getJson<UsageSummaryResponse>("/api/admin/usage?group_by=user_id&limit=500"),
        getJson<ReviewsResponse>("/api/admin/reviews?limit=50"),
      ]);
      const me = mePayload.me || {};
      writeJson(meNode, me);

      // Mount users card with tenant context
      const tenantId = me.tenant_id || "";
      if (usersNode && tenantId) {
        mountAdminUsers(usersNode, tenantId);
      }

      // Wire invite button
      const inviteBtn = root!.querySelector<HTMLButtonElement>("#btn-invite-user");
      if (inviteBtn && tenantId) {
        inviteBtn.addEventListener("click", () => handleInvite(tenantId));
      }

      writeJson(usageNode, {
        totals: usagePayload.summary?.totals || {},
        groups: usagePayload.summary?.groups || [],
      });
      writeJson(
        reviewsNode,
        (reviewsPayload.reviews || []).map((review) => ({
          trace_id: review.trace_id,
          vote: review.vote,
          user_id: review.user_id,
          company_id: review.company_id,
          timestamp: review.timestamp,
          comment: review.comment,
        }))
      );
    } catch (error) {
      const message = error instanceof ApiError ? `${error.status} ${error.message}` : error instanceof Error ? error.message : "unknown_error";
      writeJson(meNode, { error: message });
      writeJson(usageNode, { error: message });
      writeJson(reviewsNode, { error: message });
    }
  }

  void loadAdminSurface();
}
