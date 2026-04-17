import path from "node:path";
import { fileURLToPath } from "node:url";

import { defineConfig } from "@playwright/test";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export default defineConfig({
  testDir: path.resolve(__dirname, "e2e-protected"),
  fullyParallel: true,
  reporter: "list",
  timeout: 45_000,
  use: {
    baseURL: "http://127.0.0.1:4173",
    headless: true,
  },
  webServer: {
    command: "npm exec vite -- --host 127.0.0.1 --port 4173",
    cwd: __dirname,
    port: 4173,
    reuseExistingServer: true,
    timeout: 180_000,
  },
});
