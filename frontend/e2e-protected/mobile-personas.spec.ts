import { expect, test } from "@playwright/test";

const API_ROUTE = /^https?:\/\/[^/]+\/api\/.*$/;
const SHARED_PASSWORD = "AlphaTemp#2026";

type Persona = {
  email: string;
  userId: string;
  role: "tenant_user" | "platform_admin";
};

const PERSONAS: Persona[] = [
  {
    email: "admin@lia.dev",
    userId: "usr_admin_001",
    role: "platform_admin",
  },
  ...Array.from({ length: 10 }, (_, index) => ({
    email: `usuario${index + 1}@lia.dev`,
    userId: `usr_usuario${index + 1}`,
    role: "tenant_user" as const,
  })),
];

test.use({
  viewport: { width: 390, height: 844 },
  userAgent:
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
  deviceScaleFactor: 3,
  isMobile: true,
  hasTouch: true,
});

function fakeJwt(payload: Record<string, unknown>): string {
  const encode = (value: Record<string, unknown>) =>
    Buffer.from(JSON.stringify(value))
      .toString("base64")
      .replace(/\+/g, "-")
      .replace(/\//g, "_")
      .replace(/=+$/g, "");
  return `${encode({ alg: "none", typ: "JWT" })}.${encode(payload)}.sig`;
}

async function mockMobileApis(page: Parameters<typeof test>[0]["page"], persona: Persona): Promise<void> {
  await page.route(API_ROUTE, async (route) => {
    const url = route.request().url();
    const method = route.request().method();
    const fulfillJson = async (body: unknown) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(body),
      });

    if (url.includes("/api/auth/login") && method === "POST") {
      await fulfillJson({
        ok: true,
        access_token: fakeJwt({
          tenant_id: "tenant-dev",
          user_id: persona.userId,
          role: persona.role,
          active_company_id: "company_demo",
          integration_id: "int_demo",
          exp: Math.floor(Date.now() / 1000) + 60 * 60,
        }),
        me: {
          tenant_id: "tenant-dev",
          user_id: persona.userId,
          role: persona.role,
          display_name: persona.userId,
          email: persona.email,
        },
      });
      return;
    }

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
      await fulfillJson({ ok: true, topics: [] });
      return;
    }
    if (url.includes("/api/conversations?")) {
      await fulfillJson({ ok: true, sessions: [] });
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
    await fulfillJson({ ok: true, sessions: [], topics: [], tenants: [] });
  });
}

for (const persona of PERSONAS) {
  test(`${persona.email} can use the mobile authenticated shell`, async ({ page }) => {
    const runtimeErrors: string[] = [];
    page.on("pageerror", (error) => runtimeErrors.push(`pageerror: ${error.message}`));
    page.on("console", (msg) => {
      if (msg.type() !== "error") return;
      const text = msg.text();
      if (text.includes("[LIA] Failed") || text.includes("Tab switch error")) {
        runtimeErrors.push(`console: ${text}`);
      }
    });

    await mockMobileApis(page, persona);

    await page.goto("/login.html", { waitUntil: "domcontentloaded" });
    await page.locator("#email").fill(persona.email);
    await page.locator("#password").fill(SHARED_PASSWORD);
    await page.getByRole("button", { name: "Entrar" }).click();

    await expect(page).toHaveURL(/\/$/);
    await expect(page.locator('.mobile-shell[data-mobile-mode="default"]')).toBeVisible();
    await expect(page.locator(".mobile-topbar")).toBeVisible();
    await expect(page.locator(".mobile-tab-bar")).toBeVisible();
    await expect(page.locator('#mobile-panel-chat.is-active')).toBeVisible();
    await expect(page.locator("#mobile-drawer-user-name")).toContainText(persona.userId);

    await page.locator('.mobile-tab[data-tab="normativa"]').click();
    await expect(page.locator('#mobile-panel-normativa.is-active')).toBeVisible();

    await page.locator('.mobile-tab[data-tab="interpretacion"]').click();
    await expect(page.locator('#mobile-panel-interpretacion.is-active')).toBeVisible();

    await page.locator('.mobile-tab[data-tab="chat"]').click();
    await expect(page.locator('#mobile-panel-chat.is-active')).toBeVisible();

    await page.locator(".mobile-hamburger-btn").click();
    await expect(page.locator(".mobile-drawer.is-open")).toBeVisible();
    await expect(page.locator("#mobile-drawer-user-role")).toContainText(
      persona.role === "platform_admin" ? "Administrador de Plataforma" : "Contador",
    );
    await expect(page.locator('[data-drawer-action="logout"]')).toBeVisible();

    expect(runtimeErrors).toEqual([]);
  });
}
