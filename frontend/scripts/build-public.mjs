import path from "node:path";
import { fileURLToPath } from "node:url";

import { build } from "vite";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const frontendRoot = path.resolve(__dirname, "..");
const uiRoot = path.resolve(frontendRoot, "..", "ui");

await build({
  root: frontendRoot,
  publicDir: path.resolve(frontendRoot, "public"),
  resolve: {
    alias: {
      "@": path.resolve(frontendRoot, "src"),
    },
  },
  build: {
    outDir: uiRoot,
    emptyOutDir: true,
    rollupOptions: {
      input: {
        admin: path.resolve(frontendRoot, "admin.html"),
        embed: path.resolve(frontendRoot, "embed.html"),
        "form-guide": path.resolve(frontendRoot, "form-guide.html"),
        index: path.resolve(frontendRoot, "index.html"),
        invite: path.resolve(frontendRoot, "invite.html"),
        login: path.resolve(frontendRoot, "login.html"),
        "normative-analysis": path.resolve(frontendRoot, "normative-analysis.html"),
        ops: path.resolve(frontendRoot, "ops.html"),
        orchestration: path.resolve(frontendRoot, "orchestration.html"),
        public: path.resolve(frontendRoot, "public.html"),
      },
    },
  },
});
