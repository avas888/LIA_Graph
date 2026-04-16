import path from "node:path";
import { fileURLToPath } from "node:url";

import { defineConfig } from "@playwright/test";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, "..");

export default defineConfig({
  testDir: path.resolve(__dirname, "e2e"),
  fullyParallel: true,
  reporter: "list",
  timeout: 45_000,
  use: {
    baseURL: "http://127.0.0.1:8787",
    headless: true,
  },
  webServer: {
    command: "npm run dev",
    cwd: repoRoot,
    port: 8787,
    reuseExistingServer: true,
    timeout: 180_000,
  },
});
