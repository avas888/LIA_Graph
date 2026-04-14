import { beforeEach, describe, expect, it, vi } from "vitest";

// Mock the API client module before importing authContext
vi.mock("@/shared/api/client", () => ({
  getApiAccessToken: vi.fn(() => null),
  setApiAccessToken: vi.fn(),
  clearApiAccessToken: vi.fn(),
}));

import {
  clearAuthContext,
  getAuthContext,
  getDisplayName,
  isAdmin,
  isAuthenticated,
} from "@/shared/auth/authContext";
import { getApiAccessToken } from "@/shared/api/client";

const mockGetToken = vi.mocked(getApiAccessToken);

/** Build a minimal JWT with the given payload claims (no signature verification). */
function fakeJwt(payload: Record<string, unknown>): string {
  const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const body = btoa(JSON.stringify(payload));
  return `${header}.${body}.fake-signature`;
}

describe("authContext", () => {
  beforeEach(() => {
    clearAuthContext();
    mockGetToken.mockReturnValue(null);

    // Provide a minimal localStorage mock
    const storage = new Map<string, string>();
    Object.defineProperty(window, "localStorage", {
      configurable: true,
      value: {
        getItem: (k: string) => storage.get(k) ?? null,
        setItem: (k: string, v: string) => storage.set(k, v),
        removeItem: (k: string) => storage.delete(k),
        clear: () => storage.clear(),
      },
    });
  });

  describe("getAuthContext", () => {
    it("returns anonymous context when no token", () => {
      const ctx = getAuthContext();
      expect(ctx.tenantId).toBe("");
      expect(ctx.userId).toBe("");
      expect(ctx.role).toBe("");
    });

    it("decodes a valid JWT", () => {
      const token = fakeJwt({
        tenant_id: "t1",
        user_id: "u1",
        role: "tenant_admin",
        active_company_id: "c1",
        integration_id: "i1",
        exp: Math.floor(Date.now() / 1000) + 3600,
      });
      mockGetToken.mockReturnValue(token);

      const ctx = getAuthContext();
      expect(ctx.tenantId).toBe("t1");
      expect(ctx.userId).toBe("u1");
      expect(ctx.role).toBe("tenant_admin");
      expect(ctx.activeCompanyId).toBe("c1");
      expect(ctx.integrationId).toBe("i1");
    });

    it("returns anonymous for expired JWT", () => {
      const token = fakeJwt({
        tenant_id: "t1",
        user_id: "u1",
        role: "tenant_user",
        exp: Math.floor(Date.now() / 1000) - 100, // expired
      });
      mockGetToken.mockReturnValue(token);

      const ctx = getAuthContext();
      expect(ctx.tenantId).toBe("");
    });

    it("returns anonymous for malformed token", () => {
      mockGetToken.mockReturnValue("not.a.jwt.at.all");
      expect(getAuthContext().tenantId).toBe("");
    });

    it("returns anonymous for token with wrong segment count", () => {
      mockGetToken.mockReturnValue("onlyone");
      expect(getAuthContext().tenantId).toBe("");
    });

    it("caches the decoded context", () => {
      const token = fakeJwt({
        tenant_id: "t1",
        user_id: "u1",
        role: "tenant_user",
        exp: Math.floor(Date.now() / 1000) + 3600,
      });
      mockGetToken.mockReturnValue(token);

      const first = getAuthContext();
      const second = getAuthContext();
      expect(first).toBe(second); // same reference
    });

    it("clearAuthContext resets the cache", () => {
      const token = fakeJwt({
        tenant_id: "t1",
        user_id: "u1",
        role: "tenant_user",
        exp: Math.floor(Date.now() / 1000) + 3600,
      });
      mockGetToken.mockReturnValue(token);

      const first = getAuthContext();
      clearAuthContext();
      mockGetToken.mockReturnValue(null);
      const second = getAuthContext();
      expect(second.tenantId).toBe("");
      expect(first).not.toBe(second);
    });
  });

  describe("isAdmin", () => {
    it("returns true for tenant_admin", () => {
      mockGetToken.mockReturnValue(
        fakeJwt({ tenant_id: "t1", role: "tenant_admin", exp: Math.floor(Date.now() / 1000) + 3600 }),
      );
      expect(isAdmin()).toBe(true);
    });

    it("returns true for platform_admin", () => {
      mockGetToken.mockReturnValue(
        fakeJwt({ tenant_id: "t1", role: "platform_admin", exp: Math.floor(Date.now() / 1000) + 3600 }),
      );
      expect(isAdmin()).toBe(true);
    });

    it("returns false for tenant_user", () => {
      mockGetToken.mockReturnValue(
        fakeJwt({ tenant_id: "t1", role: "tenant_user", exp: Math.floor(Date.now() / 1000) + 3600 }),
      );
      expect(isAdmin()).toBe(false);
    });

    it("returns false for anonymous", () => {
      expect(isAdmin()).toBe(false);
    });
  });

  describe("isAuthenticated", () => {
    it("returns true when tenantId is present", () => {
      mockGetToken.mockReturnValue(
        fakeJwt({ tenant_id: "t1", role: "tenant_user", exp: Math.floor(Date.now() / 1000) + 3600 }),
      );
      expect(isAuthenticated()).toBe(true);
    });

    it("returns false for anonymous", () => {
      expect(isAuthenticated()).toBe(false);
    });
  });

  describe("getDisplayName", () => {
    it("returns stored display name when present", () => {
      window.localStorage.setItem("lia_display_name", "Ana García");
      expect(getDisplayName()).toBe("Ana García");
    });

    it("falls back to userId when no display name stored", () => {
      mockGetToken.mockReturnValue(
        fakeJwt({ tenant_id: "t1", user_id: "user-42", role: "tenant_user", exp: Math.floor(Date.now() / 1000) + 3600 }),
      );
      expect(getDisplayName()).toBe("user-42");
    });

    it("falls back to empty string for anonymous with no stored name", () => {
      expect(getDisplayName()).toBe("");
    });
  });
});
