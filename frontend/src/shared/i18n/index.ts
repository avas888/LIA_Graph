import { getLocalStorage } from "@/shared/browser/storage";
import { DEFAULT_LOCALE, LOCALE_STORAGE_KEY, catalogs } from "./catalogs";

export type LocaleCode = keyof typeof catalogs;

export interface I18nRuntime {
  locale: LocaleCode;
  t: (key: string, vars?: Record<string, string | number>) => string;
  formatNumber: (value: number, options?: Intl.NumberFormatOptions) => string;
  formatDateTime: (value: string | number | Date, options?: Intl.DateTimeFormatOptions) => string;
}

function pickLocale(candidate: string): LocaleCode {
  const normalized = String(candidate || "").trim();
  if (normalized in catalogs) return normalized as LocaleCode;
  const byLanguage = Object.keys(catalogs).find((locale) => locale.toLowerCase().startsWith(normalized.toLowerCase().split("-")[0]));
  return (byLanguage as LocaleCode | undefined) || DEFAULT_LOCALE;
}

function resolveLocale(localeOverride = ""): LocaleCode {
  const explicit = String(localeOverride || "").trim();
  if (explicit) return pickLocale(explicit);

  const storage = getLocalStorage();
  try {
    const stored = storage.getItem(LOCALE_STORAGE_KEY);
    if (stored) return pickLocale(stored);
  } catch (_error) {
    // Ignore storage failures.
  }

  // Product default is es-CO — only use browser language if user explicitly stored a preference.
  return DEFAULT_LOCALE;
}

export function createI18n(localeOverride = ""): I18nRuntime {
  const locale = resolveLocale(localeOverride);
  const current = catalogs[locale];
  const fallback = catalogs[DEFAULT_LOCALE];

  document.documentElement.lang = locale;

  return {
    locale,
    t(key, vars = {}) {
      const template = current[key] || fallback[key] || key;
      return template.replace(/\{(\w+)\}/g, (_match, name) => String(vars[name] ?? `{${name}}`));
    },
    formatNumber(value, options) {
      return new Intl.NumberFormat(locale, options).format(value);
    },
    formatDateTime(value, options) {
      const date = value instanceof Date ? value : new Date(value);
      if (Number.isNaN(date.getTime())) return String(value ?? "");
      return new Intl.DateTimeFormat(locale, options).format(date);
    },
  };
}
