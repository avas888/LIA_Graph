import { expect, test } from "@playwright/test";

function fakeJwt(payload: Record<string, unknown>): string {
  const encode = (value: Record<string, unknown>) =>
    Buffer.from(JSON.stringify(value))
      .toString("base64")
      .replace(/\+/g, "-")
      .replace(/\//g, "_")
      .replace(/=+$/g, "");
  return `${encode({ alg: "none", typ: "JWT" })}.${encode(payload)}.sig`;
}

test("public chat handoff renders loading state and first answer", async ({ page }) => {
  await page.route("**/api/build-info", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ ok: true, build_info: {} }),
    });
  });

  await page.route("**/api/llm/status", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        llm_runtime: {
          model: "gemini-2.5-flash",
          selected_type: "gemini",
          selected_provider: "gemini_primary",
        },
      }),
    });
  });

  await page.route("**/api/chat/stream", async (route) => {
    await page.waitForTimeout(350);
    await route.fulfill({
      status: 200,
      contentType: "text/event-stream; charset=utf-8",
      body: [
        `event: meta\ndata: ${JSON.stringify({
          trace_id: "trace_public_smoke",
          session_id: "chat_public_smoke",
          response_route: "decision",
        })}\n\n`,
        `event: status\ndata: ${JSON.stringify({ message: "Buscando en el corpus..." })}\n\n`,
        `event: final\ndata: ${JSON.stringify({
          trace_id: "trace_public_smoke",
          session_id: "chat_public_smoke",
          answer_markdown:
            "Respuesta automática de prueba sobre saldo a favor, devolución DIAN y plazos.",
          answer_mode: "graph_native",
          confidence_mode: "graph_artifact_planner_v1",
          citations: [],
          diagnostics: {},
        })}\n\n`,
      ].join(""),
    });
  });

  await page.route("**/api/chat", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        trace_id: "trace_public_fallback",
        session_id: "chat_public_fallback",
        answer_markdown: "Respuesta fallback de prueba.",
        answer_mode: "graph_native",
        confidence_mode: "graph_artifact_planner_v1",
        citations: [],
        diagnostics: {},
      }),
    });
  });

  await page.goto(
    "/public?message=Mi+cliente+tiene+saldo+a+favor+en+renta+del+AG+2025",
    { waitUntil: "domcontentloaded" },
  );

  await page.waitForSelector(".bubble-user", { state: "visible" });
  await page.waitForSelector(".bubble-assistant", { state: "visible" });
  await expect(page.locator("textarea#message")).toHaveValue("");
  await expect(page.locator(".bubble-user")).toContainText("Mi cliente tiene saldo a favor");
  await expect(page.locator(".bubble-assistant")).toContainText(
    "Respuesta automática de prueba sobre saldo a favor, devolución DIAN y plazos.",
  );
  const overlay = page.locator("#lia-thinking-overlay");
  if (await overlay.count()) {
    await expect(overlay).toBeHidden();
  }
  await expect(page).toHaveURL(/\/public$/);
});

test("protected surfaces boot across major routes", async ({ page }) => {
  const token = fakeJwt({
    tenant_id: "tenant_demo",
    user_id: "ava",
    role: "platform_admin",
    active_company_id: "company_demo",
    integration_id: "int_demo",
    exp: Math.floor(Date.now() / 1000) + 60 * 60,
  });

  await page.addInitScript((jwt: string) => {
    window.localStorage.setItem("lia_platform_access_token", jwt);
  }, token);

  await page.route("**/api/**", async (route) => {
    const url = route.request().url();
    const respond = async (body: unknown) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(body),
      });

    if (url.includes("/api/me")) {
      await respond({
        me: {
          tenant_id: "tenant_demo",
          user_id: "ava",
          role: "platform_admin",
          active_company_id: "company_demo",
          integration_id: "int_demo",
        },
      });
      return;
    }
    if (url.includes("/api/admin/usage")) {
      await respond({ summary: { totals: { events: 1 }, groups: [] } });
      return;
    }
    if (url.includes("/api/admin/reviews")) {
      await respond({ reviews: [] });
      return;
    }
    if (url.includes("/api/admin/users")) {
      await respond({
        users: [
          {
            user_id: "ava",
            email: "ava@example.com",
            display_name: "Ava",
            role: "platform_admin",
            status: "active",
          },
        ],
      });
      return;
    }
    if (url.includes("/api/admin/activity")) {
      await respond({
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
    if (url.includes("/api/corpora")) {
      await respond({
        corpora: [{ key: "declaracion_renta", label: "Declaración de Renta", active: true }],
        default: "declaracion_renta",
      });
      return;
    }
    if (url.includes("/api/ops/runs")) {
      await respond({ runs: [] });
      return;
    }
    if (url.includes("/api/ingestion/sessions")) {
      await respond({ sessions: [] });
      return;
    }
    if (url.includes("/api/ops/corpus-status")) {
      await respond({ ok: true, summary_cards: [], notes: [], available_actions: [] });
      return;
    }
    if (url.includes("/api/ops/embedding-status")) {
      await respond({ ok: true, runs: [], summary_cards: [] });
      return;
    }
    if (url.includes("/api/ops/reindex-status")) {
      await respond({ ok: true, runs: [], summary_cards: [] });
      return;
    }
    if (url.includes("/api/normative-analysis")) {
      await respond({
        ok: true,
        title: "Artículo de prueba",
        document_family: "ley",
        lead: "Resumen del documento.",
        preview_facts: [{ label: "Jerarquía", value: "Alta" }],
        sections: [{ id: "sec-1", title: "Sección", body: "Contenido normativo." }],
        timeline_events: [],
        related_documents: [],
        allowed_secondary_overlays: [],
        recommended_actions: [],
      });
      return;
    }
    if (url.includes("/api/form-guides/catalog")) {
      await respond({
        ok: true,
        guides: [
          {
            reference_key: "f220",
            title: "Formulario 220",
            profile_label: "General",
            supported_views: ["guide"],
          },
        ],
      });
      return;
    }
    if (url.includes("/api/form-guides/content")) {
      await respond({
        ok: true,
        manifest: {
          reference_key: "f220",
          title: "Formulario 220",
          profile_id: "general",
          profile_label: "General",
          supported_views: ["guide"],
        },
        structured_sections: [],
        interactive_map: [],
        official_form_pdf_url: "",
      });
      return;
    }
    await respond({});
  });

  await page.goto("/orchestration");
  await expect(page.locator(".orch-title")).toBeVisible();
  expect(await page.locator(".orch-module-card").count()).toBeGreaterThan(0);

  await page.goto("/normative-analysis?doc_id=doc_demo");
  await expect(page.locator("#normative-analysis-title")).toContainText("Artículo de prueba");

  await page.goto("/form-guide?reference_key=f220");
  await expect(page.locator("body")).toContainText("Guía visual");
  await expect(page.locator("body")).toContainText("Chatea sobre este formulario");

  await page.goto("/ops");
  await expect(page.getByRole("heading", { name: "Pipeline C Ops Console" })).toBeVisible();
  await expect(page.getByRole("tab", { name: /Ingesta/ })).toBeVisible();

  await page.goto("/admin");
  await expect(page.locator("body")).toContainText("LIA Administracion");

  await page.goto("/login");
  await expect(page.locator("body")).toContainText("Inteligencia Especializada para Contadores");

  await page.goto("/invite?token=test_invite");
  await expect(page.locator("body")).toContainText("Bienvenido a LIA");

  await page.goto("/embed");
  await expect(page.locator("body")).toContainText("LIA embebido");
});
