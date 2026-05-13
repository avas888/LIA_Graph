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

function listPortListeners(port) {
  const lsof = spawnSync("lsof", ["-ti", `TCP:${port}`, "-sTCP:LISTEN"], { encoding: "utf8" });
  if (lsof.status === 0 && lsof.stdout) {
    return lsof.stdout.split("\n").map((s) => s.trim()).filter(Boolean);
  }
  const fuser = spawnSync("fuser", [`${port}/tcp`], { encoding: "utf8" });
  if (fuser.status === 0 && fuser.stdout) {
    return fuser.stdout.split(/\s+/).map((s) => s.trim()).filter(Boolean);
  }
  return [];
}

function describePid(pid) {
  const ps = spawnSync("ps", ["-p", String(pid), "-o", "command="], { encoding: "utf8" });
  if (ps.status === 0 && ps.stdout) {
    return ps.stdout.trim();
  }
  return "<unknown>";
}

async function freePortIfHeld(port) {
  let pids = listPortListeners(port);
  if (pids.length === 0) return true;
  for (const pid of pids) {
    log(`Freeing port ${port}: terminating PID ${pid} (${describePid(pid)}).`);
    try { process.kill(Number(pid), "SIGTERM"); } catch (err) {
      log(`  SIGTERM to ${pid} failed: ${err.message}`);
    }
  }
  for (let i = 0; i < 10; i += 1) {
    await new Promise((r) => setTimeout(r, 200));
    if (listPortListeners(port).length === 0) return true;
  }
  pids = listPortListeners(port);
  for (const pid of pids) {
    log(`  Port ${port} still held; sending SIGKILL to PID ${pid}.`);
    try { process.kill(Number(pid), "SIGKILL"); } catch (err) {
      log(`  SIGKILL to ${pid} failed: ${err.message}`);
    }
  }
  await new Promise((r) => setTimeout(r, 400));
  return listPortListeners(port).length === 0;
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

  // fix_v7 §3b — real query-side Gemini embeddings replace the legacy
  // 768-dim zero vector. Default `1` (on) across all three modes per the
  // "every non-contradicting improvement flag on" stance for internal beta.
  // Shell override still wins. Rollback path: set `LIA_QUERY_EMBEDDINGS_ENABLED=0`
  // (zero-vector falls back into hybrid_search; FTS half of RRF dominates).
  // Required for the orchestration.md §4.1 invariant "vector half of RRF
  // is live, not silently zeroed".
  if (!String(env.LIA_QUERY_EMBEDDINGS_ENABLED || "").trim()) {
    env.LIA_QUERY_EMBEDDINGS_ENABLED = "1";
  }

  // fix_v7 §3c — synthesis-time cross-topic content gate. Drops template
  // bullets that cite norms whose `art:<N>` prefix is not in
  // `config/topic_norm_allowlist.json[primary_topic]["allowed_prefixes"]`
  // (with `cross_topic_allowed` carve-outs for known sibling topics).
  // Default `enforce` 2026-05-11 — the gate is a no-op for any topic that
  // isn't in the allowlist, so the worst-case is "no change in behavior",
  // never a regression. Shell override wins; `LIA_TOPIC_GATE_MODE=off`
  // disables without removing the config file.
  if (!String(env.LIA_TOPIC_GATE_MODE || "").trim()) {
    env.LIA_TOPIC_GATE_MODE = "enforce";
  }

  // fix_v11_may Phase 11B — InterpretationNode + INTERPRETS + COVERS_TOPIC
  // loader runs as part of `materialize_graph_artifacts`. Default `enforce`
  // 2026-05-11 — loader is idempotent (MERGE on doc_id + endpoints) and
  // adds ~30-60s to ingest wall-clock for ~105 interpretation docs.
  // Set `LIA_INGEST_INTERPRETATION_NODES=off` to skip during diagnostic
  // re-ingests.
  if (!String(env.LIA_INGEST_INTERPRETATION_NODES || "").trim()) {
    env.LIA_INGEST_INTERPRETATION_NODES = "enforce";
  }

  // fix_v11_may Phase 11B — Expert-panel dispatcher anchors interpretation
  // doc_ids on Falkor `INTERPRETS` edges (ordered by trust_tier) instead
  // of the Python-side `interpretacion/article_index.py` lookup, when the
  // panel payload carries article_refs.
  //
  // 2026-05-11 — DEFAULT `off` per gate-6 DISCARD decision (fix_v11_may
  // §17). Phase 11B + 3 attempted refinements (R1 judge fix, R2 Option A
  // soft veto, R3 hybrid count threshold) all came in at or below the
  // v10/v11A baseline of 12/21 on the mini-panel. The Falkor anchor
  // surfaces correct candidates, but the downstream assembly filter is
  // the bottleneck and resists tuning along the off_topic-pattern axis.
  // Path to ≥ 70 % needs a different relevance signal at the assembly
  // layer (semantic similarity at the filter, not pattern matching).
  //
  // Set `LIA_PLANNER_INTERPRETATION_ANCHOR=on` to re-enable the Falkor
  // anchor for diagnostic A/B work. The cloud InterpretationNode
  // subgraph (105 nodes + 586 INTERPRETS + 105 COVERS_TOPIC) stays in
  // place — harmless, ready for future re-attempts. The Python
  // `article_index` fallback path serves while this flag is `off`.
  if (!String(env.LIA_PLANNER_INTERPRETATION_ANCHOR || "").trim()) {
    env.LIA_PLANNER_INTERPRETATION_ANCHOR = "off";
  }

  // fix_v12_may §2.C — practical-substance boost in hybrid_search.
  // Multiplies the RRF score of `practica_erp` chunks (the 1,463
  // operational-guidance chunks tagged by fix_v10_may Phase 10A) so
  // the `**Recomendaciones Prácticas**` lead section introduced in
  // Phase 12A is fed by real práctica content rather than
  // article-derived bullets in normative voice. Default 1.5 mirrors
  // LIA_TOPIC_BOOST_FACTOR / LIA_SUBTOPIC_BOOST_FACTOR. Floors at 1.0
  // (Invariant I5, never penalize). Set to `1.0` (or `0`) to disable;
  // shell override still wins. Requires migration
  // `supabase/migrations/20260513000001_knowledge_class_boost.sql`
  // applied to the target Supabase; the retriever degrades to
  // unboosted ranking via the strip-and-retry recovery if the
  // RPC rejects the new params.
  // fix_v13_may §5 — default flipped 1.5 → 1.0. The dedicated práctica
  // retrieval lane (`practica/retriever_supabase.py`) feeds the
  // Recomendaciones Prácticas section with real `practica_erp` chunks
  // through a reserved-slot budget, so the v12 soft-boost mechanism is
  // no longer needed by default. Kept wired (the SQL parameter +
  // Python plumbing stay in retriever_supabase.py) as emergency
  // rollback: setting LIA_PRACTICA_BOOST_FACTOR=1.5 in shell env
  // restores the v12 mechanism while LIA_PRACTICA_SOURCE=disabled
  // turns off the new lane.
  if (!String(env.LIA_PRACTICA_BOOST_FACTOR || "").trim()) {
    env.LIA_PRACTICA_BOOST_FACTOR = "1.0";
  }

  // fix_v13_may §5 — reserved slot budget for the dedicated práctica
  // lane. 3 matches `build_recommendations`'s natural `tuple(lines[:3])`
  // cap. Raise via shell env only after SME validation flags follow-up
  // bubbles as still normative-voiced (fix_v13_may §7 deferred item).
  if (!String(env.LIA_PRACTICA_RESERVED_SLOTS || "").trim()) {
    env.LIA_PRACTICA_RESERVED_SLOTS = "3";
  }

  // fix_v14_may §3 (A1) — legal-anchor topic-allowlist gate.
  // Promoted to `enforce` 2026-05-13 after sprint v14.1 panel-judge
  // confirmed INCLUDE under the operator-amended decision rule (net
  // improvement + zero new hallucinations; replaces the original
  // "zero PASS→REJECT" hard veto). v14.1 measurement: combined 42-Q
  // judge-pass-rate 26 % → 31 % strict (+5 pp); 3 turns degraded
  // BORDERLINE→REJECT but inspection confirmed zero new invented
  // facts (degradations are corpus-leak fragments, not hallucinations).
  // Rollback: set `LIA_LEGAL_ANCHOR_GATE_MODE=shadow` (gate runs but
  // does not alter output) or `=off`.
  if (!String(env.LIA_LEGAL_ANCHOR_GATE_MODE || "").trim()) {
    env.LIA_LEGAL_ANCHOR_GATE_MODE = "enforce";
  }

  // fix_v14_may §4 (A2) — unified chunk-quality heuristics. Promoted
  // to `enforce` 2026-05-13 alongside A1 (same v14.1 sprint;
  // operator-amended rule). v14.1 fired only 8 demotions across 42
  // turns (mostly `cross_topic_operational_leak`); refinement of
  // pattern catalog deferred to v14.2 §4. Rollback: set
  // `LIA_CHUNK_QUALITY_HEURISTIC_MODE=shadow` or `=off`.
  if (!String(env.LIA_CHUNK_QUALITY_HEURISTIC_MODE || "").trim()) {
    env.LIA_CHUNK_QUALITY_HEURISTIC_MODE = "enforce";
  }

  if (mode === "local") {
    env.LIA_STORAGE_BACKEND = "supabase";
    env.FALKORDB_URL = LOCAL_FALKOR_URL;
    // Local dev keeps both read paths on the filesystem artifacts + local Falkor.
    if (!String(env.LIA_CORPUS_SOURCE || "").trim()) env.LIA_CORPUS_SOURCE = "artifacts";
    if (!String(env.LIA_GRAPH_MODE || "").trim()) env.LIA_GRAPH_MODE = "artifacts";
    // fix_v10_may Phase 10B — Interpretación de Expertos panel reads.
    // Local dev stays on the filesystem catalog (cheap + offline; matches
    // the LIA_CORPUS_SOURCE=artifacts pattern); shell override still wins
    // for the local-but-cloud-experts dev case.
    if (!String(env.LIA_INTERPRETATION_SOURCE || "").trim()) {
      env.LIA_INTERPRETATION_SOURCE = "filesystem";
    }
    // fix_v13_may §5 — dedicated práctica lane reads through
    // hybrid_search against Supabase; there is no filesystem fallback
    // yet (§7 deferred). Local dev defaults to `disabled` so chats
    // work fully offline; matches the LIA_CORPUS_SOURCE=artifacts
    // pattern. Shell override wins; flip to `supabase` against a
    // cloud Supabase to exercise the new lane from local dev.
    if (!String(env.LIA_PRACTICA_SOURCE || "").trim()) {
      env.LIA_PRACTICA_SOURCE = "disabled";
    }
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
    // fix_v10_may Phase 10B — Interpretación de Expertos panel via the
    // hybrid_search RPC against cloud Supabase. Shell override still wins
    // (set LIA_INTERPRETATION_SOURCE=filesystem to revert to the catalog
    // fallback for diagnostic purposes).
    if (!String(env.LIA_INTERPRETATION_SOURCE || "").trim()) {
      env.LIA_INTERPRETATION_SOURCE = "supabase";
    }
    // fix_v13_may §5 — staging defaults the dedicated práctica lane
    // ON. Reads the 1,463-row cloud `practica_erp` chunk population
    // through the hybrid_search RPC and reserves slots for the
    // Recomendaciones Prácticas section. Shell override wins; set
    // `LIA_PRACTICA_SOURCE=disabled` to bypass the new lane (the
    // section then falls through to v12 behavior).
    if (!String(env.LIA_PRACTICA_SOURCE || "").trim()) {
      env.LIA_PRACTICA_SOURCE = "supabase";
    }
  } else if (mode === "production") {
    env.LIA_STORAGE_BACKEND = "supabase";
    // fix_v10_may Phase 10B → flipped to supabase on 2026-05-12 per
    // operator beta-risk-forward stance. CLAUDE.md already documents
    // production as supabase; aligning code with docs. The filesystem
    // catalog (token-overlap scan of canonical_corpus_manifest.json)
    // returns wrong docs on any topic with strong on-corpus interp
    // briefs (TP, GMF, cambiario), and the /enhance LLM-judge then
    // marks them irrelevant → empty panel. Supabase retriever (with
    // topic boost + trust tier + embeddings) clears that case.
    if (!String(env.LIA_INTERPRETATION_SOURCE || "").trim()) {
      env.LIA_INTERPRETATION_SOURCE = "supabase";
    }
    // fix_v13_may §5 — production mirrors staging. Dedicated lane ON
    // by default; rollback via shell env (`LIA_PRACTICA_SOURCE=disabled`
    // + optional `LIA_PRACTICA_BOOST_FACTOR=1.5` to reinstate the v12
    // soft-boost mechanism, one-flag-flip, no redeploy).
    if (!String(env.LIA_PRACTICA_SOURCE || "").trim()) {
      env.LIA_PRACTICA_SOURCE = "supabase";
    }
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
  if (Number.isFinite(portNumber)) {
    const portBusy = await waitForPort(host, portNumber, 1000);
    if (portBusy) {
      log(`Port ${port} on ${host} is held; attempting to free it before starting the server.`);
      const freed = await freePortIfHeld(portNumber);
      if (!freed) {
        fail(
          `Port ${port} on ${host} is already in use and could not be freed. Stop the existing server or rerun with LIA_UI_PORT=<other-port>.`
        );
      }
      const stillBusy = await waitForPort(host, portNumber, 500);
      if (stillBusy) {
        fail(
          `Port ${port} on ${host} is still in use after reclaim attempt. Stop the existing server or rerun with LIA_UI_PORT=<other-port>.`
        );
      }
    }
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
