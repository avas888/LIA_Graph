import type { PipelineEdge, PipelineGraph, PipelineLane, PipelineNode } from "./types";

export const PIPELINE_VERSION = "2026-04-15";

const lanes: PipelineLane[] = [
  { id: "plataforma", label: "Entry + Routing", color: "var(--orch-lane-plataforma)", order: 0 },
  { id: "retrieval", label: "Served Chat (Pipeline D)", color: "var(--orch-lane-retrieval)", order: 1 },
  { id: "surfaces", label: "Published Experience", color: "var(--orch-lane-surfaces)", order: 2 },
  { id: "almacenamiento", label: "Runtime Stores", color: "var(--orch-lane-almacenamiento)", order: 3 },
  { id: "ingesta", label: "Corpus Source", color: "var(--orch-lane-ingesta)", order: 4 },
  { id: "parsing", label: "Graph Build", color: "var(--orch-lane-parsing)", order: 5 },
  { id: "mobile", label: "Dev / Staging Modes", color: "var(--orch-lane-mobile)", order: 6 },
];

const nodes: PipelineNode[] = [
  {
    id: "plataforma.entry",
    lane: "plataforma",
    kind: "stage",
    title: "/public + /api/chat",
    summary: "Public GUI, authenticated GUI, and direct chat API all enter through the same backend surface.",
    actors: ["python"],
    metrics: ["GUI + API", "8787 local"],
    order: 0,
    detailHtml: `
      <p><strong>Live entry points:</strong></p>
      <ul>
        <li><code>/public</code> — public browser shell for local and demo testing</li>
        <li><code>/api/chat</code> — buffered response contract</li>
        <li><code>/api/chat/stream</code> — SSE streaming contract</li>
      </ul>
      <p>The product path is shared: the GUI and the API hit the same runtime instead of maintaining two different chat stacks.</p>
    `,
  },
  {
    id: "plataforma.server",
    lane: "plataforma",
    kind: "stage",
    title: "ui_server.py",
    summary: "Serves HTML, handles auth or public sessions, parses the chat payload, and starts the runtime.",
    actors: ["python"],
    metrics: ["public profile", "SSE"],
    order: 1,
    detailHtml: `
      <p><strong>Responsibilities:</strong></p>
      <ul>
        <li>Serve <code>/public</code>, <code>/orchestration</code>, and other HTML shells</li>
        <li>Issue public visitor sessions in local/dev flows</li>
        <li>Validate authenticated access where needed</li>
        <li>Normalize request payloads before routing chat</li>
      </ul>
      <p>This is the orchestration choke point for the app.</p>
    `,
  },
  {
    id: "plataforma.router",
    lane: "plataforma",
    kind: "config",
    title: "pipeline_router.py",
    summary: "The served chat route is pipeline_d. Routing seams can exist around it, but the product path is this graph-native runtime.",
    actors: ["python"],
    metrics: ["default = pipeline_d"],
    order: 2,
    detailHtml: `
      <p><strong>Current truth:</strong></p>
      <ul>
        <li><code>pipeline_d</code> — live served path</li>
        <li>Any alternate route exists only as a controlled runtime seam</li>
      </ul>
      <p>The orchestration story starts here: request enters, route resolves, graph-native runtime executes.</p>
    `,
  },

  {
    id: "retrieval.topic_router",
    lane: "retrieval",
    kind: "stage",
    title: "topic_router()",
    summary: "Maps practical accountant language into topic hints and guardrails. The user does not need to cite the law.",
    actors: ["python"],
    metrics: ["natural language"],
    order: 0,
    detailHtml: `
      <p><strong>What this stage does:</strong></p>
      <ul>
        <li>Detect the dominant accountant workflow in the question</li>
        <li>Prevent side mentions from hijacking the route</li>
        <li>Keep practical queries practical, even when the prompt never names an article</li>
      </ul>
      <p>Example: a devolución / saldo a favor question should stay on procedimiento tributario even if it also mentions facturación electrónica.</p>
    `,
  },
  {
    id: "retrieval.planner",
    lane: "retrieval",
    kind: "stage",
    title: "build_graph_retrieval_plan()",
    summary: "Builds query_mode, graph anchors, lexical article searches, traversal budgets, topic hints, and temporal_context.",
    actors: ["python"],
    metrics: ["query_mode", "temporal_context"],
    order: 1,
    detailHtml: `
      <p><strong>The planner decides:</strong></p>
      <ul>
        <li><code>query_mode</code> — for example <code>obligation_chain</code> or <code>historical_reform_chain</code></li>
        <li>Anchor articles or reform laws when the question gives enough evidence</li>
        <li>Lexical graph searches when the user asks in practical language instead of citing the law</li>
        <li><code>temporal_context</code> for historical or vigencia-sensitive questions</li>
      </ul>
      <p>This stage turns a practical accountant question into a concrete graph retrieval plan.</p>
    `,
  },
  {
    id: "retrieval.resolve",
    lane: "retrieval",
    kind: "stage",
    title: "resolve_entry_points()",
    summary: "Turns lexical searches into concrete article or reform nodes while preserving the natural-language retrieval intent.",
    actors: ["python"],
    metrics: ["article_search → article"],
    order: 2,
    detailHtml: `
      <p><strong>Why this exists:</strong></p>
      <ul>
        <li>Accountants often ask operational questions without naming the statute first</li>
        <li>The runtime still needs hard article anchors to traverse the graph well</li>
        <li>The original lexical search terms remain useful for selecting the right support documents</li>
      </ul>
      <p>This bridge is what lets natural-language prompts land on the right legal nodes.</p>
    `,
  },
  {
    id: "retrieval.evidence",
    lane: "retrieval",
    kind: "stage",
    title: "retrieve_graph_evidence()",
    summary: "Reads local graph artifacts, collects primary articles and reforms, then attaches practical or interpretive support after the graph is grounded.",
    actors: ["python"],
    metrics: ["artifacts on disk", "graph_first"],
    order: 3,
    detailHtml: `
      <p><strong>Live answer inputs:</strong></p>
      <ul>
        <li><code>artifacts/canonical_corpus_manifest.json</code></li>
        <li><code>artifacts/parsed_articles.jsonl</code></li>
        <li><code>artifacts/typed_edges.jsonl</code></li>
      </ul>
      <p><strong>Evidence bundle shape:</strong></p>
      <ul>
        <li>Primary articles</li>
        <li>Connected articles</li>
        <li>Related reforms</li>
        <li>Support documents from practica / interpretacion when they materially help the accountant do the work</li>
      </ul>
      <p>Graph grounding comes first. Support documents enrich the answer after the legal anchor is stable.</p>
    `,
  },
  {
    id: "retrieval.answer",
    lane: "retrieval",
    kind: "stage",
    title: "compose_graph_native_answer()",
    summary: "Publishes practice-first content: what to do, procedure, legal anchors, changes, precautions, and opportunities.",
    actors: ["python"],
    metrics: ["no meta", "practical first"],
    order: 4,
    detailHtml: `
      <p><strong>Published reply rule:</strong></p>
      <ul>
        <li>Lead with accountant value, not system introspection</li>
        <li>Explain the procedure in usable steps</li>
        <li>Pepper in the law where it helps the accountant act correctly</li>
        <li>Reserve deep legal study for the normativa / evidence surfaces</li>
      </ul>
      <p><strong>Visible structure today:</strong></p>
      <ul>
        <li><code>Qué Haría Primero</code></li>
        <li><code>Procedimiento Sugerido</code></li>
        <li><code>Soportes y Papeles de Trabajo</code></li>
        <li><code>Anclaje Legal</code></li>
        <li><code>Cambios y Contexto Legal</code></li>
        <li><code>Precauciones</code></li>
        <li><code>Oportunidades</code></li>
      </ul>
      <p>Planner labels, route names, and retrieval self-commentary stay out of the published answer.</p>
    `,
  },
  {
    id: "retrieval.contract",
    lane: "retrieval",
    kind: "stage",
    title: "PipelineCResponse",
    summary: "Returns the final contract: answer text, citations, diagnostics, confidence, and graph_native vs graph_native_partial.",
    actors: ["python"],
    metrics: ["citations", "diagnostics"],
    order: 5,
    detailHtml: `
      <p><strong>Two separate audiences exist here:</strong></p>
      <ul>
        <li><strong>User-facing:</strong> practical answer content only</li>
        <li><strong>Internal/runtime-facing:</strong> planner metadata, evidence bundle metadata, diagnostics, and confidence fields</li>
      </ul>
      <p>The response still carries diagnostics for debugging, but that metadata is not supposed to leak into the published accountant reply.</p>
    `,
  },

  {
    id: "surfaces.public",
    lane: "surfaces",
    kind: "stage",
    title: "Public GUI",
    summary: "Local no-login browser path on /public. This is the fastest way to test the real corpus-backed chat experience.",
    actors: ["python"],
    metrics: ["public profile"],
    order: 0,
    detailHtml: `
      <p>Local development enables the public visitor flow so the team can test real chat without full login friction.</p>
      <p>This surface now hits the same <code>pipeline_d</code> route as the API.</p>
    `,
  },
  {
    id: "surfaces.auth",
    lane: "surfaces",
    kind: "stage",
    title: "Authenticated GUI",
    summary: "Same chat runtime, but with account-scoped shells and the future managed-chat experience layered around it.",
    actors: ["python"],
    metrics: ["same runtime"],
    order: 1,
    detailHtml: `
      <p>The important orchestration truth is shared runtime, not separate chat logic.</p>
      <p>Public and authenticated shells should differ in access and product chrome, not in the legal answer engine.</p>
    `,
  },
  {
    id: "surfaces.normativa",
    lane: "surfaces",
    kind: "stage",
    title: "Normativa / Evidence Panels",
    summary: "This is where deeper legal reading belongs: source text, citations, and evidence inspection beyond the main answer body.",
    actors: ["python"],
    metrics: ["deep dive"],
    order: 2,
    detailHtml: `
      <p>The main answer should help the accountant act.</p>
      <p>The normativa surfaces are where the accountant can rest, verify legal context, and dig deeper into the exact texts if desired.</p>
    `,
  },
  {
    id: "surfaces.partial",
    lane: "surfaces",
    kind: "config",
    title: "Still Partial",
    summary: "Chat works end to end, but rich evidence drill-down, saved history, and some managed/admin surfaces still need more restoration.",
    actors: ["python"],
    metrics: ["chat ready", "managed layer partial"],
    order: 3,
    detailHtml: `
      <p><strong>Healthy now:</strong> open GUI, ask a question, get a corpus-backed answer.</p>
      <p><strong>Still recovering:</strong> richer evidence utilities, saved conversation management, and some operational surfaces.</p>
    `,
  },

  {
    id: "almacenamiento.artifacts",
    lane: "almacenamiento",
    kind: "store",
    title: "Local Artifacts on Disk",
    summary: "The live answer path reads local graph artifacts. This is the actual retrieval source for served chat today.",
    actors: ["python"],
    metrics: ["manifest + articles + edges"],
    order: 0,
    detailHtml: `
      <p><strong>This is the live retrieval source today:</strong></p>
      <ul>
        <li><code>canonical_corpus_manifest.json</code></li>
        <li><code>parsed_articles.jsonl</code></li>
        <li><code>typed_edges.jsonl</code></li>
      </ul>
      <p>If these artifacts are missing or stale, the served graph-native chat path degrades.</p>
    `,
  },
  {
    id: "almacenamiento.supabase",
    lane: "almacenamiento",
    kind: "store",
    title: "Supabase Runtime Persistence",
    summary: "Supabase is for conversations, metrics, feedback, auth nonces, usage, and staging-mode persistence. It is not the live retrieval engine.",
    actors: ["sql"],
    metrics: ["runtime persistence"],
    order: 1,
    detailHtml: `
      <p><strong>Used for:</strong></p>
      <ul>
        <li>Conversation state</li>
        <li>Chat runs and metrics</li>
        <li>Feedback</li>
        <li>Terms state, usage ledger, auth nonces, active-generation state</li>
      </ul>
      <p>This store surrounds the chat experience operationally, but the live answer engine still reads the local graph artifacts.</p>
    `,
  },
  {
    id: "almacenamiento.falkor",
    lane: "almacenamiento",
    kind: "store",
    title: "Falkor Graph Parity",
    summary: "Falkor exists for local Docker parity and staging-mode graph operations, not for per-request live traversal in the current served chat path.",
    actors: ["python"],
    metrics: ["local docker", "cloud staging"],
    order: 2,
    detailHtml: `
      <p><strong>Environment split:</strong></p>
      <ul>
        <li><code>npm run dev</code> — local Docker Falkor</li>
        <li><code>npm run dev:staging</code> — cloud Falkor from env</li>
      </ul>
      <p>Important nuance: the answer path still uses generated artifacts, not a live Falkor traversal on every question.</p>
    `,
  },

  {
    id: "ingesta.knowledge",
    lane: "ingesta",
    kind: "store",
    title: "knowledge_base/",
    summary: "Source material across normativa, interpretacion, and practica.",
    actors: ["curator"],
    metrics: ["source of truth"],
    order: 0,
    detailHtml: `
      <p>The graph-native answer path depends on a curated corpus, not on ad hoc live web retrieval.</p>
      <p>The important families remain:</p>
      <ul>
        <li><code>normativa_base</code></li>
        <li><code>interpretative_guidance</code></li>
        <li><code>practica_erp</code></li>
      </ul>
    `,
  },
  {
    id: "ingesta.manifest",
    lane: "ingesta",
    kind: "config",
    title: "Canonical Manifest",
    summary: "Tracks which documents are ready, what family they belong to, and how they should be interpreted downstream.",
    actors: ["curator", "python"],
    metrics: ["ready docs only"],
    order: 1,
    detailHtml: `
      <p>The manifest is the editorial contract between corpus curation and runtime behavior.</p>
      <p>It tells the system which support documents are canonical enough to ride alongside graph evidence.</p>
    `,
  },
  {
    id: "ingesta.publish",
    lane: "ingesta",
    kind: "stage",
    title: "Published Corpus",
    summary: "Only canonically ready material should flow into the graph artifacts that power chat.",
    actors: ["python"],
    metrics: ["published set"],
    order: 2,
    detailHtml: `
      <p>This step matters because the served chat path should not improvise from stale, draft, or off-policy material.</p>
    `,
  },

  {
    id: "parsing.articles",
    lane: "parsing",
    kind: "stage",
    title: "parsed_articles.jsonl",
    summary: "Article nodes with title, excerpt, source path, and the keys needed for graph-native retrieval.",
    actors: ["python"],
    metrics: ["article nodes"],
    order: 0,
    detailHtml: `
      <p>This artifact gives Lia Graph the legal anchors it can actually traverse and cite.</p>
    `,
  },
  {
    id: "parsing.edges",
    lane: "parsing",
    kind: "stage",
    title: "typed_edges.jsonl",
    summary: "Typed relations such as REQUIRES, REFERENCES, MODIFIES, and SUPERSEDES connect the legal graph.",
    actors: ["python"],
    metrics: ["typed relations"],
    order: 1,
    detailHtml: `
      <p>The planner chooses the traversal style; this artifact supplies the legal paths that make that traversal meaningful.</p>
    `,
  },
  {
    id: "parsing.temporal",
    lane: "parsing",
    kind: "stage",
    title: "temporal_intent.py",
    summary: "Historical and vigencia helpers let the planner choose the right cutoff and the right reform context.",
    actors: ["python"],
    metrics: ["historical slice"],
    order: 2,
    detailHtml: `
      <p>This is why questions like “antes de la Ley 2277 de 2022” can be handled as temporal graph problems instead of just string matching.</p>
    `,
  },

  {
    id: "mobile.dev",
    lane: "mobile",
    kind: "stage",
    title: "npm run dev",
    summary: "Builds the public UI, runs health checks, uses filesystem storage plus local Docker Falkor, and serves the local app.",
    actors: ["python"],
    metrics: ["local health check"],
    order: 0,
    detailHtml: `
      <p><strong>Local dev truth:</strong></p>
      <ul>
        <li>Public GUI is enabled</li>
        <li>Artifacts on disk power the answer path</li>
        <li>Local Falkor is checked for parity, not used as the live chat retriever</li>
      </ul>
    `,
  },
  {
    id: "mobile.staging",
    lane: "mobile",
    kind: "stage",
    title: "npm run dev:staging",
    summary: "Runs the same app shell against cloud Falkor and Supabase persistence while keeping the served answer path artifact-backed.",
    actors: ["python", "sql"],
    metrics: ["cloud env"],
    order: 1,
    detailHtml: `
      <p>Staging-mode should be described as environment parity around the same product runtime, not as a totally different retrieval engine.</p>
    `,
  },
  {
    id: "mobile.truth",
    lane: "mobile",
    kind: "config",
    title: "Production-Like Truth",
    summary: "Same HTML shell, same ui_server, same pipeline_d, same practical-first answer contract. The main remaining gaps are richer managed surfaces and sharper retrieval precision.",
    actors: ["python"],
    metrics: ["same served path"],
    order: 2,
    detailHtml: `
      <p><strong>Healthy:</strong> the real GUI chat path is live.</p>
      <p><strong>Still improving:</strong> temporal precision, duplicate version disambiguation, and the richer managed-chat surfaces around the core answer engine.</p>
    `,
  },
];

const edges: PipelineEdge[] = [
  { from: "plataforma.entry", to: "plataforma.server" },
  { from: "plataforma.server", to: "plataforma.router" },

  { from: "plataforma.router", to: "retrieval.topic_router", crossLane: true, label: "default route" },
  { from: "retrieval.topic_router", to: "retrieval.planner" },
  { from: "retrieval.planner", to: "retrieval.resolve" },
  { from: "retrieval.resolve", to: "retrieval.evidence" },
  { from: "retrieval.evidence", to: "retrieval.answer" },
  { from: "retrieval.answer", to: "retrieval.contract" },

  { from: "retrieval.contract", to: "surfaces.public", crossLane: true, label: "published answer" },
  { from: "retrieval.contract", to: "surfaces.auth", crossLane: true, label: "published answer" },
  { from: "retrieval.contract", to: "surfaces.normativa", crossLane: true, label: "citations + evidence" },
  { from: "surfaces.auth", to: "surfaces.partial", label: "managed layer" },

  { from: "ingesta.knowledge", to: "ingesta.manifest" },
  { from: "ingesta.manifest", to: "ingesta.publish" },
  { from: "ingesta.publish", to: "parsing.articles", crossLane: true, label: "build" },
  { from: "ingesta.publish", to: "parsing.edges", crossLane: true, label: "build" },
  { from: "parsing.articles", to: "almacenamiento.artifacts", crossLane: true, label: "article nodes" },
  { from: "parsing.edges", to: "almacenamiento.artifacts", crossLane: true, label: "typed graph" },
  { from: "parsing.temporal", to: "retrieval.planner", crossLane: true, label: "historical intent" },
  { from: "almacenamiento.artifacts", to: "retrieval.evidence", crossLane: true, label: "live answer source" },

  { from: "almacenamiento.supabase", to: "plataforma.server", crossLane: true, label: "sessions + metrics" },
  { from: "almacenamiento.falkor", to: "mobile.dev", crossLane: true, label: "local parity" },
  { from: "almacenamiento.falkor", to: "mobile.staging", crossLane: true, label: "cloud parity" },

  { from: "mobile.dev", to: "plataforma.server", crossLane: true, label: "local launch" },
  { from: "mobile.staging", to: "plataforma.server", crossLane: true, label: "staging-mode launch" },
  { from: "mobile.truth", to: "plataforma.router", crossLane: true, label: "served reality" },
];

export const pipelineGraph: PipelineGraph = { nodes, edges, lanes };
