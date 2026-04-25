import fs from "node:fs";
import net from "node:net";
import path from "node:path";
import { spawn, spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, "..");
const FRONTEND_DIR = path.join(ROOT, "frontend");
const ARTIFACTS_DIR = path.join(ROOT, "artifacts");

const LOCAL_FALKOR_URL = "redis://127.0.0.1:6389";
const LOCAL_FALKOR_HOST = "127.0.0.1";
const LOCAL_FALKOR_PORT = 6389;
const LOCAL_FALKOR_IMAGE = "falkordb/falkordb:latest";
const LOCAL_FALKOR_CONTAINER = "lia-graph-falkor-dev";
const DEFAULT_HOST = "127.0.0.1";
const DEFAULT_PORT = "8787";
const DEFAULT_GRAPH = "LIA_REGULATORY_GRAPH";

const REQUIRED_ARTIFACTS = [
  "canonical_corpus_manifest.json",
  "parsed_articles.jsonl",
  "typed_edges.jsonl",
];

function log(line = "") {
  process.stdout.write(`${line}\n`);
}

function fail(message) {
  throw new Error(message);
}

function parseEnvLine(line) {
  const raw = String(line || "").trim();
  if (!raw || raw.startsWith("#") || !raw.includes("=")) return null;
  const [rawKey, ...rest] = raw.split("=");
  const key = rawKey.trim();
  if (!key) return null;
  let value = rest.join("=").trim();
  if (
    value.length >= 2 &&
    ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'")))
  ) {
    value = value.slice(1, -1);
  }
  return [key, value];
}

function loadEnvForMode(mode) {
  const env = { ...process.env };
  const protectedKeys = new Set(Object.keys(process.env));
  const files = [".env", ".env.local"];
  if (mode === "local") files.push(".env.dev.local");
  if (mode === "staging") files.push(".env.staging");

  for (const file of files) {
    const filePath = path.join(ROOT, file);
    if (!fs.existsSync(filePath) || !fs.statSync(filePath).isFile()) continue;
    const text = fs.readFileSync(filePath, "utf8");
    for (const line of text.split(/\r?\n/)) {
      const parsed = parseEnvLine(line);
      if (!parsed) continue;
      const [key, value] = parsed;
      if (protectedKeys.has(key)) continue;
      env[key] = value;
    }
  }
  return env;
}

function runCommand(command, args, options = {}) {
  const result = spawnSync(command, args, {
    cwd: ROOT,
    encoding: "utf8",
    stdio: options.stdio || "pipe",
    env: options.env || process.env,
  });
  if (result.error) {
    throw result.error;
  }
  return result;
}

function ensureCommandAvailable(command, probeArgs = ["--version"]) {
  try {
    const result = runCommand(command, probeArgs);
    if (result.status !== 0) {
      fail(`Command \`${command}\` is installed but did not run cleanly.`);
    }
  } catch (error) {
    fail(`Required command \`${command}\` is not available: ${error.message}`);
  }
}

function ensureArtifactsExist() {
  const missing = REQUIRED_ARTIFACTS.filter((name) => !fs.existsSync(path.join(ARTIFACTS_DIR, name)));
  if (missing.length) {
    fail(
      `Missing required graph artifacts: ${missing.join(", ")}. Run \`make phase2-graph-artifacts PHASE2_CORPUS_DIR=knowledge_base\` first.`
    );
  }
}

function ensureFrontendDependencies() {
  const nodeModulesPath = path.join(FRONTEND_DIR, "node_modules");
  if (fs.existsSync(nodeModulesPath)) return;
  log("Installing frontend dependencies with `npm --prefix frontend ci`...");
  const result = runCommand("npm", ["--prefix", "frontend", "ci"], { stdio: "inherit" });
  if (result.status !== 0) {
    fail("Failed to install frontend dependencies.");
  }
}

function buildFrontend() {
  log("Building public UI bundle...");
  const result = runCommand("npm", ["--prefix", "frontend", "run", "build:public"], {
    stdio: "inherit",
  });
  if (result.status !== 0) {
    fail("Frontend build failed.");
  }
}

function dockerContainerExists(name) {
  const result = runCommand("docker", ["ps", "-a", "--format", "{{.Names}}"]);
  if (result.status !== 0) return false;
  return String(result.stdout || "")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .includes(name);
}

function waitForPort(host, port, timeoutMs) {
  return new Promise((resolve) => {
    const startedAt = Date.now();
    const attempt = () => {
      const socket = net.createConnection({ host, port });
      socket.setTimeout(1000);
      socket.on("connect", () => {
        socket.destroy();
        resolve(true);
      });
      const onFailure = () => {
        socket.destroy();
        if (Date.now() - startedAt >= timeoutMs) {
          resolve(false);
          return;
        }
        setTimeout(attempt, 400);
      };
      socket.on("error", onFailure);
      socket.on("timeout", onFailure);
    };
    attempt();
  });
}

async function ensureLocalFalkorDocker(env) {
  const portReady = await waitForPort(LOCAL_FALKOR_HOST, LOCAL_FALKOR_PORT, 1000);
  if (portReady) {
    log(`Detected FalkorDB listener on ${LOCAL_FALKOR_URL}.`);
    return;
  }

  ensureCommandAvailable("docker");
  if (dockerContainerExists(LOCAL_FALKOR_CONTAINER)) {
    log(`Starting existing Docker container \`${LOCAL_FALKOR_CONTAINER}\`...`);
    const startResult = runCommand("docker", ["start", LOCAL_FALKOR_CONTAINER], { stdio: "inherit" });
    if (startResult.status !== 0) {
      fail(`Failed to start Docker container \`${LOCAL_FALKOR_CONTAINER}\`.`);
    }
  } else {
    log(`Launching local FalkorDB Docker container \`${LOCAL_FALKOR_CONTAINER}\` on ${LOCAL_FALKOR_URL}...`);
    const runResult = runCommand(
      "docker",
      ["run", "-d", "--name", LOCAL_FALKOR_CONTAINER, "-p", `${LOCAL_FALKOR_PORT}:6379`, LOCAL_FALKOR_IMAGE],
      { stdio: "inherit" }
    );
    if (runResult.status !== 0) {
      fail(
        `Failed to launch local FalkorDB Docker container. Check whether port ${LOCAL_FALKOR_PORT} is already in use.`
      );
    }
  }

  const ready = await waitForPort(LOCAL_FALKOR_HOST, LOCAL_FALKOR_PORT, 15000);
  if (!ready) {
    fail(`Local FalkorDB Docker did not become reachable on ${LOCAL_FALKOR_URL}.`);
  }
}

async function ensureLocalSupabaseStack(env) {
  // Local Supabase API port (Kong gateway). Standard supabase CLI default.
  const host = "127.0.0.1";
  const port = 54321;
  const ready = await waitForPort(host, port, 1000);
  if (ready) {
    log(`Detected Supabase local API on http://${host}:${port}.`);
    return;
  }
  fail(
    `Local Supabase stack is not running on http://${host}:${port}. ` +
      "Start it with `supabase start` before running `npm run dev`."
  );
}

function summarizeDependencyResults(results) {
  for (const result of results) {
    const marker = result.ok ? "OK" : "!!";
    log(`- [${marker}] ${result.name}: ${result.summary}`);
  }
}

function runDependencySmoke(checks, env) {
  const args = ["run", "python", "-m", "lia_graph.dependency_smoke", "--json"];
  for (const check of checks) {
    args.push("--only", check);
  }
  const result = runCommand("uv", args, { env });
  let parsed = [];
  try {
    parsed = JSON.parse(result.stdout || "[]");
  } catch {
    parsed = [];
  }
  summarizeDependencyResults(parsed);
  if (result.status !== 0) {
    const detail = result.stderr?.trim() || result.stdout?.trim() || "dependency_smoke failed";
    fail(detail);
  }
  return parsed;
}

function buildRuntimeEnv(mode) {
  const env = loadEnvForMode(mode);
  env.PYTHONPATH = "src:.";
  env.LIA_DISABLE_DOTENV = "1";
  env.FALKORDB_GRAPH = String(env.FALKORDB_GRAPH || DEFAULT_GRAPH).trim() || DEFAULT_GRAPH;
  env.LIA_UI_HOST = String(env.LIA_UI_HOST || DEFAULT_HOST).trim() || DEFAULT_HOST;
  env.LIA_UI_PORT = String(env.LIA_UI_PORT || DEFAULT_PORT).trim() || DEFAULT_PORT;

  // LLM polish is on by default across all modes — the chat is useless
  // as template boilerplate. Explicit `LIA_LLM_POLISH_ENABLED=0` from the
  // shell still wins so operators can disable on the fly.
  if (!String(env.LIA_LLM_POLISH_ENABLED || "").trim()) {
    env.LIA_LLM_POLISH_ENABLED = "1";
  }

  // Cross-encoder reranker (structural backlog #2). Default flipped
  // to `live` on 2026-04-22 per the "all improvements on" directive
  // for the internal-beta period. With no sidecar deployed yet, the
  // adapter falls back to hybrid order and logs
  // `reranker_fallback=true` — functionally identical to shadow for
  // served answers, but methodology-labeled as live so the regression
  // gates stay aligned once the sidecar actually lands. Shell override
  // still wins.
  if (!String(env.LIA_RERANKER_MODE || "").trim()) {
    env.LIA_RERANKER_MODE = "live";
  }

  // V2-2 query decomposition. Default flipped to `on` on 2026-04-22
  // (same directive). Multi-`¿…?` queries fan out per sub-question
  // before retrieval; results merge at synthesis. Applies to all three
  // run modes — local, staging, production — since this is internal
  // beta and no flag here contradicts another. Shell override wins.
  if (!String(env.LIA_QUERY_DECOMPOSE || "").trim()) {
    env.LIA_QUERY_DECOMPOSE = "on";
  }

  // v5 Phase 3 — TEMA-first retrieval. When on, the Falkor retriever
  // augments its candidate article-key set with TopicNode<-[:TEMA]-
  // articles for the routed topic hint. **Default `on`** across all
  // three modes per the 2026-04-25 re-flip (env-matrix tag
  // `v2026-04-25-temafirst-readdressed`). The 2026-04-24 revert was
  // unblocked by: taxonomy v2 + K2 path-veto landing (next_v3 §13.7),
  // SME 30Q at 30/30 post Alejandro spot-review (§13.11 + §13.11.1),
  // and operator's qualitative-pass on §8.4 gate 9
  // (gate_9_threshold_decision.md §7). Shell / Railway override still wins.
  if (!String(env.LIA_TEMA_FIRST_RETRIEVAL || "").trim()) {
    env.LIA_TEMA_FIRST_RETRIEVAL = "on";
  }

  // v6 phase 3 — defensive coherence gate. Default `enforce` 2026-04-25 per
  // operator's "no off/shadow flags" directive. Step-04 verification at
  // would-refuse=1/30 (below [4,12] safe band) is low-risk; watch production
  // refusal-rate, revert to `shadow` if regressions surface.
  if (!String(env.LIA_EVIDENCE_COHERENCE_GATE || "").trim()) {
    env.LIA_EVIDENCE_COHERENCE_GATE = "enforce";
  }

  // v6 phase 4 — per-topic citation allow-list. Default `enforce` 2026-04-25
  // per "no off flags" directive. Higher-risk flip (not yet end-to-end
  // verified): if accountants report missing valid cites, revert to `off`.
  if (!String(env.LIA_POLICY_CITATION_ALLOWLIST || "").trim()) {
    env.LIA_POLICY_CITATION_ALLOWLIST = "enforce";
  }

  // Taxonomy-aware classifier prompt + K2 path-veto (next_v3 §7 / §13.7).
  // Default `enforce` 2026-04-25 — validated through 5 rebuilds (Cypher 6/6).
  // Affects ingest only; runtime ignores it. Listed here so a launcher-driven
  // ingest invocation inherits the right default.
  if (!String(env.LIA_INGEST_CLASSIFIER_TAXONOMY_AWARE || "").trim()) {
    env.LIA_INGEST_CLASSIFIER_TAXONOMY_AWARE = "enforce";
  }

  if (mode === "local") {
    env.LIA_STORAGE_BACKEND = "supabase";
    env.FALKORDB_URL = LOCAL_FALKOR_URL;
    // Local dev keeps both read paths on the filesystem artifacts + local Falkor.
    if (!String(env.LIA_CORPUS_SOURCE || "").trim()) env.LIA_CORPUS_SOURCE = "artifacts";
    if (!String(env.LIA_GRAPH_MODE || "").trim()) env.LIA_GRAPH_MODE = "artifacts";
    // Fallbacks if .env.dev.local is missing — safe demo keys shipped with every local Supabase CLI install.
    if (!String(env.SUPABASE_URL || "").trim()) {
      env.SUPABASE_URL = "http://127.0.0.1:54321";
    }
    if (!String(env.SUPABASE_ANON_KEY || "").trim()) {
      env.SUPABASE_ANON_KEY =
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0";
    }
    if (!String(env.SUPABASE_SERVICE_ROLE_KEY || "").trim()) {
      env.SUPABASE_SERVICE_ROLE_KEY =
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImV4cCI6MTk4MzgxMjk5Nn0.EGIM96RAZx35lJzdJsyH-qQwv8Hdp7fsn3W0YpN81IU";
    }
  } else if (mode === "staging") {
    env.LIA_STORAGE_BACKEND = "supabase";
    // Staging reads the corpus from cloud Supabase and walks the graph against
    // cloud FalkorDB. Must already be hydrated — see `make phase2-graph-artifacts-supabase`.
    env.LIA_CORPUS_SOURCE = "supabase";
    env.LIA_GRAPH_MODE = "falkor_live";
  } else if (mode === "production") {
    env.LIA_STORAGE_BACKEND = "supabase";
  } else {
    fail(`Unsupported mode: ${mode}`);
  }
  return env;
}

function ensureRequiredEnv(mode, env) {
  const missing = [];
  const requireKey = (key) => {
    if (!String(env[key] || "").trim()) missing.push(key);
  };

  requireKey("GEMINI_API_KEY");
  requireKey("FALKORDB_URL");
  if (mode === "local" || mode === "staging") {
    requireKey("SUPABASE_URL");
    if (!String(env.SUPABASE_SERVICE_ROLE_KEY || "").trim() && !String(env.SUPABASE_ANON_KEY || "").trim()) {
      missing.push("SUPABASE_SERVICE_ROLE_KEY|SUPABASE_ANON_KEY");
    }
  }
  if (missing.length) {
    fail(`Missing required env for ${mode} mode: ${missing.join(", ")}`);
  }
}

async function preflight(mode) {
  log(`Running ${mode} preflight...`);
  ensureCommandAvailable("uv");
  ensureCommandAvailable("npm");

  const env = buildRuntimeEnv(mode);
  ensureRequiredEnv(mode, env);
  ensureArtifactsExist();
  ensureFrontendDependencies();
  buildFrontend();

  if (mode === "local") {
    await ensureLocalFalkorDocker(env);
    await ensureLocalSupabaseStack(env);
    log("Storage backend: supabase (local docker)");
    log("Runtime read path: artifacts (filesystem) + local FalkorDB docker");
    runDependencySmoke(["falkordb", "supabase", "gemini"], env);
  } else {
    log("Storage backend: supabase (cloud)");
    log(
      `Runtime read path: ${env.LIA_CORPUS_SOURCE || "artifacts"} (chunks) + ${
        env.LIA_GRAPH_MODE || "artifacts"
      } (graph)`
    );
    runDependencySmoke(["falkordb", "supabase", "gemini"], env);
  }

  return env;
}

async function startServer(env) {
  const host = String(env.LIA_UI_HOST || DEFAULT_HOST).trim() || DEFAULT_HOST;
  const port = String(env.LIA_UI_PORT || DEFAULT_PORT).trim() || DEFAULT_PORT;
  const portNumber = Number(port);
  const portBusy = Number.isFinite(portNumber)
    ? await waitForPort(host, portNumber, 1000)
    : false;
  if (portBusy) {
    fail(
      `Port ${port} on ${host} is already in use. Stop the existing server or rerun with LIA_UI_PORT=<other-port>.`
    );
  }

  log(`Starting UI server on http://${host}:${port} ...`);
  const corpusSource = String(env.LIA_CORPUS_SOURCE || "artifacts").trim() || "artifacts";
  const graphMode = String(env.LIA_GRAPH_MODE || "artifacts").trim() || "artifacts";
  if (corpusSource === "supabase" && graphMode === "falkor_live") {
    log("Note: served chat answers read chunks from cloud Supabase and walk the graph in cloud FalkorDB.");
  } else {
    log("Note: served chat answers are artifact-backed; FalkorDB is still preflighted for environment parity and graph ops.");
  }
  const child = spawn(
    "uv",
    ["run", "python", "-m", "lia_graph.ui_server", "--host", host, "--port", port],
    {
      cwd: ROOT,
      env,
      stdio: "inherit",
    }
  );

  const forwardSignal = (signal) => {
    if (!child.killed) child.kill(signal);
  };
  process.on("SIGINT", forwardSignal);
  process.on("SIGTERM", forwardSignal);
  child.on("exit", (code, signal) => {
    if (signal) {
      process.kill(process.pid, signal);
      return;
    }
    process.exit(code ?? 0);
  });
}

async function main() {
  const mode = process.argv[2] || "local";
  const checkOnly = process.argv.includes("--check");
  if (mode === "production") {
    log("Production runs on Railway. Use `railway up` or push-to-deploy.");
    log("This mode is intentionally disabled locally.");
    process.exit(2);
  }
  try {
    const env = await preflight(mode);
    if (checkOnly) {
      log(`Preflight passed for ${mode} mode.`);
      return;
    }
    await startServer(env);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    log(`Preflight failed: ${message}`);
    process.exit(1);
  }
}

await main();
