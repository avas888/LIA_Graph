import { mountTemplate } from "@/shared/dom/template";
import { createI18n, type I18nRuntime } from "@/shared/i18n";
import { requireAuth } from "@/shared/auth/authGate";

export interface PageContext {
  i18n: I18nRuntime;
  root: HTMLElement;
  mountShell: (html: string) => void;
  setTitle: (title: string) => void;
}

interface CreatePageContextOptions {
  missingRootMessage: string;
  rootId?: string;
}

export function createPageContext({
  missingRootMessage,
  rootId = "app",
}: CreatePageContextOptions): PageContext {
  const root = document.getElementById(rootId);
  if (!root) {
    throw new Error(missingRootMessage);
  }

  const i18n = createI18n();

  return {
    i18n,
    root,
    mountShell(html: string) {
      mountTemplate(root, html);
    },
    setTitle(title: string) {
      document.title = title;
    },
  };
}

interface BootstrapShellPageOptions {
  missingRootMessage: string;
  mountApp: (root: HTMLElement, context: { i18n: I18nRuntime }) => void;
  renderShell: (i18n: I18nRuntime) => string;
  rootId?: string;
  title: (i18n: I18nRuntime) => string;
}

export function bootstrapShellPage({
  missingRootMessage,
  mountApp,
  renderShell,
  rootId,
  title,
}: BootstrapShellPageOptions): void {
  // Auth gate: redirect to /login if not authenticated
  if (!requireAuth()) return;

  const page = createPageContext({ missingRootMessage, rootId });
  page.setTitle(title(page.i18n));
  page.mountShell(renderShell(page.i18n));
  mountApp(page.root, { i18n: page.i18n });
}
