import { expect, test } from "@playwright/test";

test.use({
  viewport: { width: 390, height: 844 },
  userAgent:
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
  deviceScaleFactor: 3,
  isMobile: true,
  hasTouch: true,
});

test("public mobile shell renders chat handoff and hides auth-only drawer actions", async ({ page }) => {
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
          trace_id: "trace_public_mobile",
          session_id: "chat_public_mobile",
          response_route: "decision",
        })}\n\n`,
        `event: status\ndata: ${JSON.stringify({ message: "Buscando en el corpus..." })}\n\n`,
        `event: final\ndata: ${JSON.stringify({
          trace_id: "trace_public_mobile",
          session_id: "chat_public_mobile",
          answer_markdown: "Respuesta móvil pública de prueba.",
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
        trace_id: "trace_public_mobile_fallback",
        session_id: "chat_public_mobile_fallback",
        answer_markdown: "Respuesta fallback móvil pública.",
        answer_mode: "graph_native",
        confidence_mode: "graph_artifact_planner_v1",
        citations: [],
        diagnostics: {},
      }),
    });
  });

  await page.goto(
    "/public?message=Necesito+orientación+rápida+sobre+saldo+a+favor",
    { waitUntil: "domcontentloaded" },
  );

  await expect(page.locator('.mobile-shell[data-mobile-mode="public"]')).toBeVisible();
  await page.waitForSelector(".bubble-user", { state: "visible" });
  await page.waitForSelector(".bubble-assistant", { state: "visible" });
  await expect(page.locator(".bubble-user")).toContainText("Necesito orientación rápida");
  await expect(page.locator(".bubble-assistant")).toContainText("Respuesta móvil pública de prueba.");

  await page.locator('.mobile-tab[data-tab="normativa"]').click();
  await expect(page.locator('#mobile-panel-normativa.is-active')).toBeVisible();

  await page.locator('.mobile-tab[data-tab="interpretacion"]').click();
  await expect(page.locator('#mobile-panel-interpretacion.is-active')).toBeVisible();

  await page.locator(".mobile-hamburger-btn").click();
  await expect(page.locator(".mobile-drawer.is-open")).toBeVisible();
  await expect(page.locator(".mobile-drawer-user")).toHaveCount(0);
  await expect(page.locator('[data-drawer-action="historial"]')).toHaveCount(0);
  await expect(page.locator('[data-drawer-action="logout"]')).toHaveCount(0);
  await expect(page.locator('[data-drawer-action="new-conversation"]')).toBeVisible();
});
