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

  if (mode === "local") {
    env.LIA_STORAGE_BACKEND = "filesystem";
    env.FALKORDB_URL = LOCAL_FALKOR_URL;
  } else if (mode === "staging") {
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
  if (mode === "staging") {
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
    log("Storage backend: filesystem");
    log("Supabase cloud is skipped in local mode.");
    runDependencySmoke(["falkordb", "gemini"], env);
  } else {
    log("Storage backend: supabase");
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
  log("Note: current graph chat answers are artifact-backed; FalkorDB is still preflighted for environment parity and graph ops.");
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
