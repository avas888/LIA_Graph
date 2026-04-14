import { describe, expect, it } from "vitest";
import { readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";

const FRONTEND_ROOT = process.cwd().endsWith(`${path.sep}frontend`)
  ? process.cwd()
  : path.join(process.cwd(), "frontend");
const SHARED_UI_ROOT = path.join(FRONTEND_ROOT, "src", "shared", "ui");

function collectFiles(root: string, extensions: string[]): string[] {
  const files: string[] = [];
  for (const entry of readdirSync(root)) {
    const fullPath = path.join(root, entry);
    const stats = statSync(fullPath);
    if (stats.isDirectory()) {
      files.push(...collectFiles(fullPath, extensions));
      continue;
    }
    if (extensions.includes(path.extname(fullPath))) {
      files.push(fullPath);
    }
  }
  return files;
}

function rel(filePath: string): string {
  return path.relative(FRONTEND_ROOT, filePath).replaceAll(path.sep, "/");
}

function read(filePath: string): string {
  return readFileSync(filePath, "utf8");
}

describe("atomic design guardrails", () => {
  it("keeps raw hex colors out of the shared UI layer and migrated renderers", () => {
    const files = [
      ...collectFiles(path.join(SHARED_UI_ROOT, "atoms"), [".ts"]),
      ...collectFiles(path.join(SHARED_UI_ROOT, "molecules"), [".ts"]),
      ...collectFiles(path.join(SHARED_UI_ROOT, "organisms"), [".ts"]),
      ...collectFiles(path.join(SHARED_UI_ROOT, "patterns"), [".ts"]),
      path.join(FRONTEND_ROOT, "src", "styles", "ui", "primitives.css"),
      path.join(FRONTEND_ROOT, "src", "styles", "public.css"),
      path.join(FRONTEND_ROOT, "src", "features", "chat", "chatCitationRenderer.ts"),
      path.join(FRONTEND_ROOT, "src", "features", "chat", "expertPanelController.ts"),
      path.join(FRONTEND_ROOT, "src", "features", "record", "recordView.ts"),
      path.join(FRONTEND_ROOT, "src", "features", "admin", "adminUsersController.ts"),
      path.join(FRONTEND_ROOT, "src", "app", "mobile", "mobileChatAdapter.ts"),
      path.join(FRONTEND_ROOT, "src", "app", "mobile", "mobileNormativaPanel.ts"),
      path.join(FRONTEND_ROOT, "src", "app", "mobile", "mobileInterpPanel.ts"),
      path.join(FRONTEND_ROOT, "src", "app", "mobile", "mobileHistorial.ts"),
      ...collectFiles(path.join(FRONTEND_ROOT, "src", "app", "public"), [".ts"]),
    ];
    const rawHexPattern = /(?<!&)#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b/g;

    const violations = files.flatMap((filePath) => {
      const matches = read(filePath).match(rawHexPattern) ?? [];
      return matches.map((match) => `${rel(filePath)} -> ${match}`);
    });

    expect(violations).toEqual([]);
  });

  it("keeps inline svg literals centralized in shared/ui/icons.ts", () => {
    const files = [
      ...collectFiles(path.join(SHARED_UI_ROOT, "atoms"), [".ts"]),
      ...collectFiles(path.join(SHARED_UI_ROOT, "molecules"), [".ts"]),
      ...collectFiles(path.join(SHARED_UI_ROOT, "organisms"), [".ts"]),
      ...collectFiles(path.join(SHARED_UI_ROOT, "patterns"), [".ts"]),
      path.join(FRONTEND_ROOT, "src", "features", "chat", "chatCitationRenderer.ts"),
      path.join(FRONTEND_ROOT, "src", "features", "record", "recordView.ts"),
      path.join(FRONTEND_ROOT, "src", "features", "admin", "adminUsersController.ts"),
      ...collectFiles(path.join(FRONTEND_ROOT, "src", "app", "public"), [".ts"]),
    ];
    const violations = files
      .filter((filePath) => /<svg[\s>]/.test(read(filePath)))
      .map(rel);

    expect(violations).toEqual([]);
  });

  it("keeps migrated reusable markup delegated to shared UI renderers", () => {
    const fileRules: Array<{ file: string; bannedTokens: string[] }> = [
      {
        file: "src/features/chat/chatCitationRenderer.ts",
        bannedTokens: ["citation-trigger", "citation-group-divider", "mobile-citation-card"],
      },
      {
        file: "src/features/record/recordView.ts",
        bannedTokens: ["record-card", "record-date-group", "record-filter-pill", "record-topic-pill"],
      },
      {
        file: "src/features/admin/adminUsersController.ts",
        bannedTokens: ["admin-user-status-pill"],
      },
      {
        file: "src/app/mobile/mobileHistorial.ts",
        bannedTokens: ["mobile-historial-card", "mobile-history-card"],
      },
      {
        // The public visitor shell must delegate the banner and captcha
        // overlay markup to shared/ui/molecules/publicBanner.ts and
        // shared/ui/molecules/publicCaptchaOverlay.ts. Inlining the markup
        // here would re-introduce the duplication the molecules exist to
        // remove.
        file: "src/app/public/shell.ts",
        bannedTokens: [
          "lia-public-captcha-card",
          "lia-public-captcha-title",
          "lia-public-captcha-widget",
          "lia-public-banner__text",
          "lia-public-banner__badge",
          "public-shell-banner-link",
        ],
      },
      {
        // The public visitor banner must NOT carry a login CTA. Public
        // visitors have no platform credentials, so any /login bait would
        // either trap them in a 401-redirect loop or surface a path the
        // chokepoint already 403s.
        //
        // Inline <img> is also banned: the logo MUST come from the
        // createBrandMark atom so the authenticated chrome and the public
        // banner stay byte-identical on the brand contract.
        //
        // Tab markup is banned because the public surface has a single
        // panel — tabs are an authenticated-only affordance.
        file: "src/shared/ui/molecules/publicBanner.ts",
        bannedTokens: [
          "/login",
          "loginLabel",
          "loginHref",
          "createLinkAction",
          "<img",
          'role="tab"',
          'role="tablist"',
          "browser-tab ",
        ],
      },
      {
        // Public main must NOT mount the historial controller (there is
        // no history for anonymous visitors) or pass any auth-only login
        // affordances. The mobile public path uses renderMobileShell with
        // mode="public" which already strips those entries from the DOM.
        file: "src/app/public/main.ts",
        bannedTokens: [
          "loginLabel",
          "loginHref",
          "mountMobileHistorial",
          "mobileHistorial",
        ],
      },
    ];

    const violations = fileRules.flatMap(({ file, bannedTokens }) => {
      const fullPath = path.join(FRONTEND_ROOT, file);
      const content = read(fullPath);
      return bannedTokens
        .filter((token) => content.includes(token))
        .map((token) => `${file} -> ${token}`);
    });

    expect(violations).toEqual([]);
  });
});
