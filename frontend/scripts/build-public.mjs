import { mkdir, writeFile } from "node:fs/promises";
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

await mkdir(uiRoot, { recursive: true });
await writeFile(
  path.join(uiRoot, "index.html"),
  `<!doctype html>
<html lang="es-CO">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
    <meta http-equiv="refresh" content="0; url=/public" />
    <title>LIA</title>
    <style>
      :root {
        color-scheme: light;
        font-family: "IBM Plex Sans", system-ui, sans-serif;
      }
      body {
        margin: 0;
        min-height: 100vh;
        display: grid;
        place-items: center;
        background:
          radial-gradient(circle at top, rgba(56, 189, 248, 0.18), transparent 42%),
          linear-gradient(180deg, #081120 0%, #0d1b2a 55%, #10233f 100%);
        color: #f8fafc;
      }
      main {
        width: min(30rem, calc(100vw - 2rem));
        padding: 2rem;
        border-radius: 1.25rem;
        background: rgba(8, 17, 32, 0.78);
        box-shadow: 0 20px 60px rgba(8, 15, 32, 0.35);
        text-align: center;
      }
      a {
        color: inherit;
      }
    </style>
  </head>
  <body>
    <main>
      <h1>Redirigiendo a LIA</h1>
      <p>Si no cambia automáticamente, entra a <a href="/public">/public</a>.</p>
    </main>
  </body>
</html>
`,
  "utf8",
);
