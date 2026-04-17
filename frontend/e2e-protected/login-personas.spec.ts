import { expect, test } from "@playwright/test";

const API_ROUTE = /^https?:\/\/[^/]+\/api\/.*$/;

type Persona = {
  email: string;
  userId: string;
  displayName: string;
  role: "tenant_user" | "platform_admin";
};

const SHARED_PASSWORD = "AlphaTemp#2026";

const PERSONAS: Persona[] = [
  {
    email: "admin@lia.dev",
    userId: "usr_admin_001",
    displayName: "Admin LIA",
    role: "platform_admin",
  },
  ...Array.from({ length: 10 }, (_, index) => ({
    email: `usuario${index + 1}@lia.dev`,
    userId: `usr_usuario${index + 1}`,
    displayName: `Usuario ${index + 1}`,
    role: "tenant_user" as const,
  })),
];

function fakeJwt(payload: Record<string, unknown>): string {
  const encode = (value: Record<string, unknown>) =>
    Buffer.from(JSON.stringify(value))
      .toString("base64")
      .replace(/\+/g, "-")
      .replace(/\//g, "_")
      .replace(/=+$/g, "");
  return `${encode({ alg: "none", typ: "JWT" })}.${encode(payload)}.sig`;
}

async function mockPersonaApis(page: Parameters<typeof test>[0]["page"], persona: Persona): Promise<void> {
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
          display_name: persona.displayName,
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
    await fulfillJson({ ok: true, sessions: [], topics: [], tenants: [] });
  });
}

for (const persona of PERSONAS) {
  test(`${persona.email} can log in and land on the correct shell`, async ({ page }) => {
    const runtimeErrors: string[] = [];
    page.on("pageerror", (error) => runtimeErrors.push(`pageerror: ${error.message}`));
    page.on("console", (msg) => {
      if (msg.type() !== "error") return;
      const text = msg.text();
      if (text.includes("[LIA] Failed") || text.includes("Tab switch error")) {
        runtimeErrors.push(`console: ${text}`);
      }
    });

    await mockPersonaApis(page, persona);

    await page.goto("/login.html", { waitUntil: "domcontentloaded" });
    await page.locator("#email").fill(persona.email);
    await page.locator("#password").fill(SHARED_PASSWORD);
    await page.getByRole("button", { name: "Entrar" }).click();

    await expect(page).toHaveURL(/\/$/);
    await expect(page.locator('[data-browser-tab="chat"]')).toBeVisible();
    await expect(page.locator('[data-browser-tab="record"]')).toBeVisible();

    if (persona.role === "platform_admin") {
      await expect(page.locator('[data-browser-tab="backstage"]')).toBeVisible();
      await expect(page.locator('[data-browser-tab="activity"]')).toBeVisible();
      await expect(page.locator('[data-browser-tab="ingestion"]')).toBeVisible();
      await expect(page.locator('[data-browser-tab="orchestration"]')).toBeVisible();
      await expect(page.locator('[data-browser-tab="ratings"]')).toBeVisible();
      await expect(page.locator('[data-browser-tab="api"]')).toBeVisible();
      await expect(page.locator(".browser-tab")).toHaveCount(8);
    } else {
      await expect(page.locator('[data-browser-tab="backstage"]')).toHaveCount(0);
      await expect(page.locator('[data-browser-tab="activity"]')).toHaveCount(0);
      await expect(page.locator('[data-browser-tab="ingestion"]')).toHaveCount(0);
      await expect(page.locator('[data-browser-tab="orchestration"]')).toHaveCount(0);
      await expect(page.locator('[data-browser-tab="ratings"]')).toHaveCount(0);
      await expect(page.locator('[data-browser-tab="api"]')).toHaveCount(0);
      await expect(page.locator(".browser-tab")).toHaveCount(2);
    }

    await expect(page.locator(".user-menu-email")).toContainText(persona.displayName);
    expect(runtimeErrors).toEqual([]);
  });
}
