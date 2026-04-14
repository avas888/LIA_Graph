import { beforeEach, describe, expect, it } from "vitest";
import { createI18n } from "@/shared/i18n";
import { LOCALE_STORAGE_KEY } from "@/shared/i18n/catalogs";

describe("createI18n", () => {
  beforeEach(() => {
    const storage = new Map();
    Object.defineProperty(window, "localStorage", {
      configurable: true,
      value: {
        getItem(key: string) {
          return storage.has(key) ? storage.get(key) : null;
        },
        setItem(key: string, value: string) {
          storage.set(key, value);
        },
        removeItem(key: string) {
          storage.delete(key);
        },
        clear() {
          storage.clear();
        },
      },
    });
    window.localStorage.clear();
  });

  it("uses the explicit locale override when provided", () => {
    const i18n = createI18n("en-US");
    expect(i18n.locale).toBe("en-US");
    expect(i18n.t("chat.composer.send")).toBe("Send inquiry");
  });

  it("falls back to a stored locale override", () => {
    window.localStorage.setItem(LOCALE_STORAGE_KEY, "en-US");
    const i18n = createI18n();
    expect(i18n.locale).toBe("en-US");
    expect(document.documentElement.lang).toBe("en-US");
  });

  it("exposes the curated normative modal labels in both locales", () => {
    const es = createI18n("es-CO");
    const en = createI18n("en-US");

    expect(es.t("chat.modal.norma.original")).toBe("Ir a documento original");
    expect(es.t("chat.modal.norma.guideUnavailable")).toBe("Esta guía aún no está disponible");
    expect(es.t("chat.modal.norma.originalFallback")).toContain("PDF normalizado");

    expect(en.t("chat.modal.norma.original")).toBe("Go to original document");
    expect(en.t("chat.modal.norma.guideUnavailable")).toBe("This guide is not available yet");
    expect(en.t("chat.modal.norma.originalFallback")).toContain("normalized PDF");
  });
});
