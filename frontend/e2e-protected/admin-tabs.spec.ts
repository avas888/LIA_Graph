import { expect, test } from "@playwright/test";

const API_ROUTE = /^https?:\/\/[^/]+\/api\/.*$/;

function fakeJwt(payload: Record<string, unknown>): string {
  const encode = (value: Record<string, unknown>) =>
    Buffer.from(JSON.stringify(value))
      .toString("base64")
      .replace(/\+/g, "-")
      .replace(/\//g, "_")
      .replace(/=+$/g, "");
  return `${encode({ alg: "none", typ: "JWT" })}.${encode(payload)}.sig`;
}

async function mockAdminApis(page: Parameters<typeof test>[0]["page"]): Promise<void> {
  await page.route(API_ROUTE, async (route) => {
    const url = route.request().url();
    const fulfillJson = async (body: unknown) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(body),
      });

    if (url.includes("/api/build-info")) {
      await fulfillJson({ ok: true, build_info: {} });
      return;
    }
    if (url.includes("/api/llm/status")) {
      await fulfillJson({
        llm_runtime: {
          model: "gemini-2.5-flash",
          selected_type: "gemini",
          selected_provider: "gemini_primary",
        },
      });
      return;
    }
    if (url.includes("/api/ops/runs")) {
      await fulfillJson({ runs: [] });
      return;
    }
    if (url.includes("/api/conversations/topics")) {
      await fulfillJson({ ok: true, topics: ["renta", "iva"] });
      return;
    }
    if (url.includes("/api/conversations?")) {
      await fulfillJson({
        ok: true,
        sessions: [
          {
            session_id: "sess_admin_1",
            first_question: "Saldo a favor en renta",
            topic: "renta",
            tenant_id: "tenant-dev",
            user_id: "usr_admin_001",
            user_display_name: "Admin LIA",
            turn_count: 3,
            created_at: "2026-04-17T10:00:00Z",
            updated_at: "2026-04-17T10:05:00Z",
            status: "active",
          },
        ],
      });
      return;
    }
    if (url.includes("/api/admin/tenants")) {
      await fulfillJson({
        ok: true,
        tenants: [
          {
            tenant_id: "tenant-dev",
            display_name: "LIA Dev",
            members: [
              {
                user_id: "usr_admin_001",
                email: "admin@lia.dev",
                display_name: "Admin LIA",
              },
            ],
          },
        ],
      });
      return;
    }
    if (url.includes("/api/admin/users")) {
      await fulfillJson({
        ok: true,
        users: [
          {
            user_id: "usr_admin_001",
            email: "admin@lia.dev",
            display_name: "Admin LIA",
            role: "platform_admin",
            status: "active",
            created_at: "2026-04-01T00:00:00Z",
          },
        ],
      });
      return;
    }
    if (url.includes("/api/admin/activity")) {
      await fulfillJson({
        ok: true,
        activity: {
          recent_logins: [],
          user_stats: [],
          summary: {
            logins_today: 1,
            active_users_7d: 1,
            total_interactions_7d: 3,
          },
        },
      });
      return;
    }
    if (url.includes("/api/admin/ratings")) {
      await fulfillJson({
        ok: true,
        ratings: [
          {
            trace_id: "trace_admin_rating",
            session_id: "sess_admin_1",
            user_id: "usr_admin_001",
            rating: 5,
            comment: "Muy útil",
            question_text: "¿Cómo trato un saldo a favor?",
            answer_text: "Respuesta de prueba.",
            timestamp: "2026-04-17T10:10:00Z",
            tenant_id: "tenant-dev",
          },
        ],
      });
      return;
    }
    if (url.includes("/api/admin/eval/service-accounts")) {
      await fulfillJson({
        ok: true,
        service_accounts: [
          {
            service_account_id: "svc_eval_1",
            display_name: "Eval Robot",
            secret_hint: "lia_eval_...1234",
            status: "active",
            created_at: "2026-04-10T00:00:00Z",
            last_used_at: "2026-04-17T09:00:00Z",
          },
        ],
      });
      return;
    }
    if (url.includes("/api/admin/eval/stats")) {
      await fulfillJson({
        ok: true,
        stats: {
          total_requests: 12,
          total_errors: 0,
          error_rate: 0,
          total_input_tokens: 1200,
          total_output_tokens: 2400,
          latency_p50_ms: 450,
          latency_p95_ms: 980,
        },
      });
      return;
    }
    if (url.includes("/api/admin/eval/logs")) {
      await fulfillJson({
        ok: true,
        logs: [
          {
            log_id: "log_1",
            endpoint: "/api/eval/ask",
            method: "POST",
            status_code: 200,
            latency_ms: 420,
            input_tokens: 100,
            output_tokens: 250,
            created_at: "2026-04-17T09:15:00Z",
          },
        ],
        total: 1,
        limit: 20,
        offset: 0,
      });
      return;
    }
    if (url.includes("/api/corpora")) {
      await fulfillJson({
        ok: true,
        corpora: [{ key: "declaracion_renta", label: "Declaración de Renta", active: true }],
        default: "declaracion_renta",
      });
      return;
    }
    if (url.includes("/api/ingestion/sessions")) {
      await fulfillJson({ ok: true, sessions: [] });
      return;
    }
    if (url.includes("/api/ops/corpus-status")) {
      await fulfillJson({
        production: {
          available: true,
          generation_id: "prod_01",
          documents: 10,
          chunks: 20,
          embeddings_complete: true,
          knowledge_class_counts: {
            normative_base: 6,
            interpretative_guidance: 2,
            practica_erp: 2,
          },
          activated_at: "2026-04-17T09:00:00Z",
        },
        wip: {
          available: true,
          generation_id: "wip_01",
          documents: 12,
          chunks: 26,
          embeddings_complete: true,
          knowledge_class_counts: {
            normative_base: 7,
            interpretative_guidance: 3,
            practica_erp: 2,
          },
          activated_at: "2026-04-17T09:30:00Z",
        },
        delta: { documents: "+2", chunks: "+6", promotable: true },
        preflight_ready: true,
        preflight_reasons: [],
        rollback_available: false,
        rollback_reason: "Rollback is not available yet.",
        rollback_generation_id: null,
        current_operation: null,
        last_operation: null,
      });
      return;
    }
    if (url.includes("/api/ops/embedding-status")) {
      await fulfillJson({
        api_health: { ok: true, detail: "healthy" },
        total_chunks: 26,
        embedded_chunks: 26,
        null_embedding_chunks: 0,
        coverage_pct: 100,
        current_operation: null,
        last_operation: null,
      });
      return;
    }
    if (url.includes("/api/ops/reindex-status")) {
      await fulfillJson({
        current_operation: null,
        last_operation: null,
      });
      return;
    }
    await fulfillJson({ ok: true });
  });
}

test("platform admin can navigate every visible top-level tab", async ({ page }) => {
  const token = fakeJwt({
    tenant_id: "tenant-dev",
    user_id: "usr_admin_001",
    role: "platform_admin",
    active_company_id: "company_demo",
    integration_id: "int_demo",
    exp: Math.floor(Date.now() / 1000) + 60 * 60,
  });

  const runtimeErrors: string[] = [];
  page.on("pageerror", (error) => runtimeErrors.push(`pageerror: ${error.message}`));
  page.on("console", (msg) => {
    if (msg.type() !== "error") return;
    const text = msg.text();
    if (text.includes("[LIA] Failed") || text.includes("Tab switch error")) {
      runtimeErrors.push(`console: ${text}`);
    }
  });

  await page.addInitScript((jwt: string) => {
    window.localStorage.setItem("lia_platform_access_token", jwt);
    window.localStorage.setItem("lia_display_name", "Admin LIA");
  }, token);

  await mockAdminApis(page);

  await page.goto("/index.html", { waitUntil: "domcontentloaded" });

  await expect(page.locator('[data-browser-tab="chat"]')).toBeVisible();
  await expect(page.locator('[data-browser-tab="record"]')).toBeVisible();
  await expect(page.locator('[data-browser-tab="backstage"]')).toBeVisible();
  await expect(page.locator('[data-browser-tab="activity"]')).toBeVisible();
  await expect(page.locator('[data-browser-tab="ingestion"]')).toBeVisible();
  await expect(page.locator('[data-browser-tab="orchestration"]')).toBeVisible();
  await expect(page.locator('[data-browser-tab="ratings"]')).toBeVisible();
  await expect(page.locator('[data-browser-tab="api"]')).toBeVisible();

  await expect(page.locator("#tab-panel-chat.is-active")).toBeVisible();
  await expect(page.locator("textarea#message")).toBeVisible();

  await page.locator('[data-browser-tab="record"]').click();
  await expect(page.locator("#tab-panel-record.is-active")).toBeVisible();
  await expect(page.locator(".record-shell")).toBeVisible();

  await page.locator('[data-browser-tab="backstage"]').click();
  await expect(page.locator("#tab-panel-backstage.is-active")).toBeVisible();
  await expect(page.locator("#tab-panel-backstage")).toContainText("Pipeline C Ops Console");
  await expect(page.locator("#debug-summary")).toBeVisible();

  await page.locator('[data-browser-tab="activity"]').click();
  await expect(page.locator("#tab-panel-activity.is-active")).toBeVisible();
  await expect(page.locator("#tab-panel-activity")).toContainText("Actividad de Usuarios");

  await page.locator('[data-browser-tab="ingestion"]').click();
  await expect(page.locator("#tab-panel-ingestion.is-active")).toBeVisible();
  await expect(page.locator("#tab-panel-ingestion")).toContainText("Sesiones");
  await expect(page.locator("#tab-panel-ingestion")).toContainText("Promoción");

  await page.locator('[data-browser-tab="ratings"]').click();
  await expect(page.locator("#tab-panel-ratings.is-active")).toBeVisible();
  await expect(page.locator(".ratings-title")).toContainText("Calificaciones de usuarios");

  await page.locator('[data-browser-tab="api"]').click();
  await expect(page.locator("#tab-panel-api.is-active")).toBeVisible();
  await expect(page.locator("#tab-panel-api")).toContainText("Credenciales del servicio");

  await page.locator('[data-browser-tab="orchestration"]').click();
  await expect(page).toHaveURL(/\/orchestration(?:\.html)?$/);
  await expect(page.locator(".orch-title")).toBeVisible();

  expect(runtimeErrors).toEqual([]);
});
