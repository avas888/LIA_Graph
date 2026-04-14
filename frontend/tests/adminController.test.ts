import { beforeEach, describe, expect, it, vi } from "vitest";

// ── Mock dependencies before importing the module under test ───────

vi.mock("@/shared/api/client", () => ({
  getJson: vi.fn(),
  postJson: vi.fn(),
}));

vi.mock("@/shared/ui/colors", () => ({
  semantic: {
    status: { error: "#ff0000", success: "#00ff00" },
    border: { default: "#cccccc" },
    text: { tertiary: "#999999" },
  },
}));

vi.mock("@/shared/ui/organisms/adminUserRows", () => ({
  createAdminUserRow: vi.fn(
    (rowModel: { userId: string; displayName: string; email: string; roleLabel: string; statusLabel: string }) => {
      const tr = document.createElement("tr");
      tr.dataset.uid = rowModel.userId;
      tr.setAttribute("data-lia-component", "admin-user-row");
      tr.innerHTML = `<td>${rowModel.displayName}</td><td>${rowModel.email}</td><td>${rowModel.roleLabel}</td><td>${rowModel.statusLabel}</td><td></td>`;
      return tr;
    },
  ),
  createAdminUsersFeedbackRow: vi.fn((message: string, tone: string) => {
    const tr = document.createElement("tr");
    tr.dataset.tone = tone;
    tr.innerHTML = `<td colspan="5">${message}</td>`;
    return tr;
  }),
}));

import { getJson, postJson } from "@/shared/api/client";
import { mountAdminUsers, handleInvite } from "@/features/admin/adminUsersController";

const mockGetJson = vi.mocked(getJson);
const mockPostJson = vi.mocked(postJson);

function makeUser(overrides: Record<string, unknown> = {}) {
  return {
    user_id: "u1",
    email: "ana@example.com",
    display_name: "Ana",
    role: "tenant_user",
    status: "active",
    created_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

async function flushUi(): Promise<void> {
  await Promise.resolve();
  await new Promise((r) => setTimeout(r, 0));
  await Promise.resolve();
}

// ── mountAdminUsers ──────────────────────────────────────────────────

describe("mountAdminUsers", () => {
  let container: HTMLElement;

  beforeEach(() => {
    vi.restoreAllMocks();
    container = document.createElement("div");
    document.body.replaceChildren(container);

    // Re-apply mocks after restoreAllMocks
    vi.mocked(getJson).mockReset();
    vi.mocked(postJson).mockReset();
  });

  it("renders the users table shell with thead and tbody", () => {
    mockGetJson.mockResolvedValue({ ok: true, users: [] });
    mountAdminUsers(container, "tenant-1");

    expect(container.querySelector("table.admin-users-table")).not.toBeNull();
    expect(container.querySelector("thead")).not.toBeNull();
    expect(container.querySelector("#users-tbody")).not.toBeNull();
  });

  it("loads and renders user rows from API", async () => {
    mockGetJson.mockResolvedValue({
      ok: true,
      users: [
        makeUser({ user_id: "u1", display_name: "Ana", email: "ana@co.com", status: "active", role: "tenant_user" }),
        makeUser({ user_id: "u2", display_name: "Luis", email: "luis@co.com", status: "suspended", role: "tenant_admin" }),
      ],
    });

    mountAdminUsers(container, "tenant-1");
    await flushUi();

    expect(mockGetJson).toHaveBeenCalledWith("/api/admin/users?tenant_id=tenant-1");
    const rows = container.querySelectorAll("tr[data-lia-component='admin-user-row']");
    expect(rows.length).toBe(2);
  });

  it("renders empty feedback when no users are returned", async () => {
    mockGetJson.mockResolvedValue({ ok: true, users: [] });
    mountAdminUsers(container, "tenant-1");
    await flushUi();

    const feedback = container.querySelector("tr[data-tone='empty']");
    expect(feedback).not.toBeNull();
    expect(feedback!.textContent).toContain("Sin usuarios");
  });

  it("renders error feedback when API call fails", async () => {
    mockGetJson.mockRejectedValue(new Error("Network error"));
    mountAdminUsers(container, "tenant-1");
    await flushUi();

    const feedback = container.querySelector("tr[data-tone='error']");
    expect(feedback).not.toBeNull();
    expect(feedback!.textContent).toContain("Network error");
  });

  it("renders generic error message when error is not an Error instance", async () => {
    mockGetJson.mockRejectedValue("string error");
    mountAdminUsers(container, "tenant-1");
    await flushUi();

    const feedback = container.querySelector("tr[data-tone='error']");
    expect(feedback).not.toBeNull();
    expect(feedback!.textContent).toContain("Error al cargar usuarios");
  });

  it("does not fetch if container or tenantId is missing", async () => {
    // mountAdminUsers sets the internal _container and _tenantId,
    // so calling with an empty tenant should still attempt to load
    // but with empty tenant_id param
    mockGetJson.mockResolvedValue({ ok: true, users: [] });
    mountAdminUsers(container, "");
    await flushUi();

    // loadUsers checks !_tenantId and returns early
    // The initial "Cargando..." row should remain since loadUsers exits early
    expect(container.querySelector("#users-tbody")!.textContent).toContain("Cargando...");
  });
});

// ── handleInvite ──────────────────────────────────────────────────────

describe("handleInvite", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.mocked(getJson).mockReset();
    vi.mocked(postJson).mockReset();
    document.body.replaceChildren();

    // Stub HTMLDialogElement.showModal since jsdom doesn't implement it
    if (!HTMLDialogElement.prototype.showModal) {
      HTMLDialogElement.prototype.showModal = vi.fn();
    } else {
      vi.spyOn(HTMLDialogElement.prototype, "showModal").mockImplementation(() => {});
    }
    if (!HTMLDialogElement.prototype.close) {
      HTMLDialogElement.prototype.close = vi.fn();
    }
  });

  it("appends a dialog element to the body with invite form", async () => {
    // Don't await — just fire and let the dialog appear
    void handleInvite("tenant-1");
    await flushUi();

    const dialog = document.querySelector<HTMLDialogElement>("dialog.invite-dialog");
    expect(dialog).not.toBeNull();
    expect(dialog!.querySelector("#invite-email")).not.toBeNull();
    expect(dialog!.querySelector("#invite-role")).not.toBeNull();
    expect(dialog!.querySelector(".btn-cancel")).not.toBeNull();
    expect(dialog!.querySelector(".btn-submit")).not.toBeNull();
  });

  it("cancel button closes and removes the dialog", async () => {
    void handleInvite("tenant-1");
    await flushUi();

    const dialog = document.querySelector<HTMLDialogElement>("dialog.invite-dialog")!;
    const cancelBtn = dialog.querySelector<HTMLButtonElement>(".btn-cancel")!;
    cancelBtn.click();

    // Trigger close event manually since jsdom doesn't fire it
    dialog.dispatchEvent(new Event("close"));
    await flushUi();

    expect(document.querySelector("dialog.invite-dialog")).toBeNull();
  });

  it("submitting the form calls postJson with email, role, tenant_id", async () => {
    mockPostJson.mockResolvedValue({
      response: new Response(),
      data: { ok: true, invite: { token_id: "t1", invite_url: "https://app.lia.co/invite?token=abc", email: "new@co.com", role: "tenant_user", expires_at: "2026-02-01" } },
    });

    void handleInvite("tenant-1");
    await flushUi();

    const dialog = document.querySelector<HTMLDialogElement>("dialog.invite-dialog")!;
    const emailInput = dialog.querySelector<HTMLInputElement>("#invite-email")!;
    const roleSelect = dialog.querySelector<HTMLSelectElement>("#invite-role")!;
    const form = dialog.querySelector<HTMLFormElement>("form")!;

    emailInput.value = "new@co.com";
    roleSelect.value = "tenant_admin";

    form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    await flushUi();

    expect(mockPostJson).toHaveBeenCalledWith("/api/admin/users/invite", {
      email: "new@co.com",
      role: "tenant_admin",
      tenant_id: "tenant-1",
    });
  });

  it("shows invite URL on successful invite creation", async () => {
    mockPostJson.mockResolvedValue({
      response: new Response(),
      data: {
        ok: true,
        invite: {
          token_id: "t1",
          invite_url: "https://app.lia.co/invite?token=abc",
          email: "new@co.com",
          role: "tenant_user",
          expires_at: "2026-02-01",
        },
      },
    });

    void handleInvite("tenant-1");
    await flushUi();

    const dialog = document.querySelector<HTMLDialogElement>("dialog.invite-dialog")!;
    const emailInput = dialog.querySelector<HTMLInputElement>("#invite-email")!;
    emailInput.value = "new@co.com";

    const form = dialog.querySelector<HTMLFormElement>("form")!;
    form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    await flushUi();

    const resultDiv = dialog.querySelector<HTMLElement>(".invite-result")!;
    expect(resultDiv.style.display).toBe("block");
    expect(resultDiv.textContent).toContain("Invitaci\u00f3n creada");

    const urlInput = resultDiv.querySelector<HTMLInputElement>("input[type='text']");
    expect(urlInput).not.toBeNull();
    expect(urlInput!.value).toBe("https://app.lia.co/invite?token=abc");
  });

  it("shows error message when invite API returns ok=false", async () => {
    mockPostJson.mockResolvedValue({
      response: new Response(),
      data: { ok: false, error: "Email ya registrado" },
    });

    void handleInvite("tenant-1");
    await flushUi();

    const dialog = document.querySelector<HTMLDialogElement>("dialog.invite-dialog")!;
    const emailInput = dialog.querySelector<HTMLInputElement>("#invite-email")!;
    emailInput.value = "dup@co.com";

    const form = dialog.querySelector<HTMLFormElement>("form")!;
    form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    await flushUi();

    const resultDiv = dialog.querySelector<HTMLElement>(".invite-result")!;
    expect(resultDiv.style.display).toBe("block");
    expect(resultDiv.textContent).toContain("Email ya registrado");
  });

  it("shows connection error when postJson rejects", async () => {
    mockPostJson.mockRejectedValue(new Error("fetch failed"));

    void handleInvite("tenant-1");
    await flushUi();

    const dialog = document.querySelector<HTMLDialogElement>("dialog.invite-dialog")!;
    const emailInput = dialog.querySelector<HTMLInputElement>("#invite-email")!;
    emailInput.value = "fail@co.com";

    const form = dialog.querySelector<HTMLFormElement>("form")!;
    form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    await flushUi();

    const resultDiv = dialog.querySelector<HTMLElement>(".invite-result")!;
    expect(resultDiv.style.display).toBe("block");
    expect(resultDiv.textContent).toContain("Error de conexi\u00f3n");
  });

  it("disables submit button while sending", async () => {
    let resolvePost!: (v: unknown) => void;
    mockPostJson.mockReturnValue(new Promise((r) => { resolvePost = r; }));

    void handleInvite("tenant-1");
    await flushUi();

    const dialog = document.querySelector<HTMLDialogElement>("dialog.invite-dialog")!;
    const emailInput = dialog.querySelector<HTMLInputElement>("#invite-email")!;
    emailInput.value = "wait@co.com";

    const submitBtn = dialog.querySelector<HTMLButtonElement>(".btn-submit")!;
    const form = dialog.querySelector<HTMLFormElement>("form")!;
    form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    await flushUi();

    // While waiting, button should be disabled with "Enviando..."
    expect(submitBtn.disabled).toBe(true);
    expect(submitBtn.textContent).toBe("Enviando...");

    // Resolve with failure to re-enable
    resolvePost({
      response: new Response(),
      data: { ok: false, error: "err" },
    });
    await flushUi();

    expect(submitBtn.disabled).toBe(false);
    expect(submitBtn.textContent).toBe("Enviar invitaci\u00f3n");
  });
});
