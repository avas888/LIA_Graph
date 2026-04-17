import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/shared/auth/authContext", () => ({
  getAuthContext: vi.fn(() => ({
    tenantId: "",
    userId: "",
    role: "",
    activeCompanyId: "",
    integrationId: "",
  })),
}));

import { getAuthContext } from "@/shared/auth/authContext";
import { getVisibleTabs } from "@/shared/auth/tabAccess";

const mockGetAuthContext = vi.mocked(getAuthContext);

const ALL_TABS = [
  { id: "chat", label: "Chat", category: "user" as const },
  { id: "normativa", label: "Normativa", category: "user" as const },
  { id: "interpretacion", label: "Interpretacion", category: "user" as const },
  { id: "backstage", label: "Backstage", category: "admin" as const },
  { id: "activity", label: "Actividad", category: "admin" as const },
  { id: "ingestion", label: "Ingesta", category: "admin" as const },
  { id: "orchestration", label: "Orchestration", category: "admin" as const },
  { id: "ratings", label: "Ratings", category: "admin" as const },
  { id: "api", label: "API", category: "admin" as const },
];

describe("getVisibleTabs", () => {
  beforeEach(() => {
    mockGetAuthContext.mockReturnValue({
      tenantId: "",
      userId: "",
      role: "",
      activeCompanyId: "",
      integrationId: "",
    });
  });

  it("hides admin tabs from tenant_user", () => {
    mockGetAuthContext.mockReturnValue({
      tenantId: "tenant-alpha",
      userId: "usr_usuario1",
      role: "tenant_user",
      activeCompanyId: "",
      integrationId: "",
    });

    const visible = getVisibleTabs(ALL_TABS);

    expect(visible.map((tab) => tab.id)).toEqual(["chat", "normativa", "interpretacion"]);
  });

  it("keeps the critical admin tabs visible for platform_admin", () => {
    mockGetAuthContext.mockReturnValue({
      tenantId: "tenant-dev",
      userId: "usr_admin_001",
      role: "platform_admin",
      activeCompanyId: "",
      integrationId: "",
    });

    const visible = getVisibleTabs(ALL_TABS);
    const tabIds = visible.map((tab) => tab.id);

    expect(tabIds).toContain("backstage");
    expect(tabIds).toContain("activity");
    expect(tabIds).toContain("ingestion");
    expect(tabIds).toContain("orchestration");
    expect(tabIds).toContain("ratings");
    expect(tabIds).toContain("api");
  });
});
