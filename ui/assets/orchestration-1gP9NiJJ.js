import"./main-DbZp9w8b.js";import{i as _}from"./icons-Cle6XWst.js";import{p as S}from"./colors-7KT68QD8.js";import{b as D}from"./bootstrap-CDL0BdR1.js";import"./index-DE07Z79R.js";import"./authGate-Bb2S6efH.js";import"./client-OE0sHIIg.js";function N(e){return`
    <main class="orch-shell">
      <header class="orch-header">
        <div class="orch-header-left">
          <a href="/" class="nav-link orch-back-link">${e.t("common.backToChat")}</a>
          <div class="orch-header-title-group">
            <p class="orch-eyebrow">${e.t("orch.eyebrow")}</p>
            <h1 class="orch-title">${e.t("orch.title")}</h1>
          </div>
        </div>
        <div class="orch-header-center">
          <nav class="orch-lane-nav" aria-label="${e.t("orch.laneNav")}">
            <button class="orch-lane-btn" data-lane="ingesta">${e.t("orch.lane.ingesta")}</button>
            <button class="orch-lane-btn" data-lane="parsing">${e.t("orch.lane.parsing")}</button>
            <button class="orch-lane-btn" data-lane="almacenamiento">${e.t("orch.lane.almacenamiento")}</button>
            <button class="orch-lane-btn" data-lane="retrieval">${e.t("orch.lane.retrieval")}</button>
            <button class="orch-lane-btn" data-lane="surfaces">${e.t("orch.lane.surfaces")}</button>
          </nav>
        </div>
        <div class="orch-header-right">
          <div class="orch-legend" aria-label="${e.t("orch.legend")}">
            <span class="orch-legend-item" data-actor="curator">
              <span class="orch-actor-dot" data-actor="curator"></span>
              ${e.t("orch.actor.curator")}
            </span>
            <span class="orch-legend-item" data-actor="python">
              <span class="orch-actor-dot" data-actor="python"></span>
              ${e.t("orch.actor.python")}
            </span>
            <span class="orch-legend-item" data-actor="sql">
              <span class="orch-actor-dot" data-actor="sql"></span>
              ${e.t("orch.actor.sql")}
            </span>
            <span class="orch-legend-item" data-actor="llm">
              <span class="orch-actor-dot" data-actor="llm"></span>
              ${e.t("orch.actor.llm")}
            </span>
            <span class="orch-legend-item" data-actor="embedding">
              <span class="orch-actor-dot" data-actor="embedding"></span>
              ${e.t("orch.actor.embedding")}
            </span>
          </div>
        </div>
      </header>

      <div id="orch-viewport" class="orch-viewport">
        <div id="orch-canvas" class="orch-canvas">
          <svg id="orch-svg" class="orch-svg-overlay"></svg>
        </div>
      </div>

      <div id="orch-minimap" class="orch-minimap">
        <canvas id="orch-minimap-canvas" width="220" height="154"></canvas>
        <div id="orch-minimap-lens" class="orch-minimap-lens"></div>
      </div>
    </main>
  `}const G=[{id:"plataforma",label:"Entry + Routing",color:"var(--orch-lane-plataforma)",order:0},{id:"retrieval",label:"Served Chat (Pipeline D)",color:"var(--orch-lane-retrieval)",order:1},{id:"surfaces",label:"Published Experience",color:"var(--orch-lane-surfaces)",order:2},{id:"almacenamiento",label:"Runtime Stores",color:"var(--orch-lane-almacenamiento)",order:3},{id:"ingesta",label:"Corpus Source",color:"var(--orch-lane-ingesta)",order:4},{id:"parsing",label:"Graph Build",color:"var(--orch-lane-parsing)",order:5},{id:"mobile",label:"Dev / Staging Modes",color:"var(--orch-lane-mobile)",order:6}],B=[{id:"plataforma.entry",lane:"plataforma",kind:"stage",title:"/public + /api/chat",summary:"Public GUI, authenticated GUI, and direct chat API all enter through the same backend surface.",actors:["python"],metrics:["GUI + API","8787 local"],order:0,detailHtml:`
      <p><strong>Live entry points:</strong></p>
      <ul>
        <li><code>/public</code> — public browser shell for local and demo testing</li>
        <li><code>/api/chat</code> — buffered response contract</li>
        <li><code>/api/chat/stream</code> — SSE streaming contract</li>
      </ul>
      <p>The product path is shared: the GUI and the API hit the same runtime instead of maintaining two different chat stacks.</p>
    `},{id:"plataforma.server",lane:"plataforma",kind:"stage",title:"ui_server.py",summary:"Serves HTML, handles auth or public sessions, parses the chat payload, and starts the runtime.",actors:["python"],metrics:["public profile","SSE"],order:1,detailHtml:`
      <p><strong>Responsibilities:</strong></p>
      <ul>
        <li>Serve <code>/public</code>, <code>/orchestration</code>, and other HTML shells</li>
        <li>Issue public visitor sessions in local/dev flows</li>
        <li>Validate authenticated access where needed</li>
        <li>Normalize request payloads before routing chat</li>
      </ul>
      <p>This is the orchestration choke point for the app.</p>
    `},{id:"plataforma.router",lane:"plataforma",kind:"config",title:"pipeline_router.py",summary:"The served chat route is pipeline_d. Routing seams can exist around it, but the product path is this graph-native runtime.",actors:["python"],metrics:["default = pipeline_d"],order:2,detailHtml:`
      <p><strong>Current truth:</strong></p>
      <ul>
        <li><code>pipeline_d</code> — live served path</li>
        <li>Any alternate route exists only as a controlled runtime seam</li>
      </ul>
      <p>The orchestration story starts here: request enters, route resolves, graph-native runtime executes.</p>
    `},{id:"retrieval.topic_router",lane:"retrieval",kind:"stage",title:"topic_router()",summary:"Maps practical accountant language into topic hints and guardrails. The user does not need to cite the law.",actors:["python"],metrics:["natural language"],order:0,detailHtml:`
      <p><strong>What this stage does:</strong></p>
      <ul>
        <li>Detect the dominant accountant workflow in the question</li>
        <li>Prevent side mentions from hijacking the route</li>
        <li>Keep practical queries practical, even when the prompt never names an article</li>
      </ul>
      <p>Example: a devolución / saldo a favor question should stay on procedimiento tributario even if it also mentions facturación electrónica.</p>
    `},{id:"retrieval.planner",lane:"retrieval",kind:"stage",title:"build_graph_retrieval_plan()",summary:"Builds query_mode, graph anchors, lexical article searches, traversal budgets, topic hints, and temporal_context.",actors:["python"],metrics:["query_mode","temporal_context"],order:1,detailHtml:`
      <p><strong>The planner decides:</strong></p>
      <ul>
        <li><code>query_mode</code> — for example <code>obligation_chain</code> or <code>historical_reform_chain</code></li>
        <li>Anchor articles or reform laws when the question gives enough evidence</li>
        <li>Lexical graph searches when the user asks in practical language instead of citing the law</li>
        <li><code>temporal_context</code> for historical or vigencia-sensitive questions</li>
      </ul>
      <p>This stage turns a practical accountant question into a concrete graph retrieval plan.</p>
    `},{id:"retrieval.resolve",lane:"retrieval",kind:"stage",title:"resolve_entry_points()",summary:"Turns lexical searches into concrete article or reform nodes while preserving the natural-language retrieval intent.",actors:["python"],metrics:["article_search → article"],order:2,detailHtml:`
      <p><strong>Why this exists:</strong></p>
      <ul>
        <li>Accountants often ask operational questions without naming the statute first</li>
        <li>The runtime still needs hard article anchors to traverse the graph well</li>
        <li>The original lexical search terms remain useful for selecting the right support documents</li>
      </ul>
      <p>This bridge is what lets natural-language prompts land on the right legal nodes.</p>
    `},{id:"retrieval.evidence",lane:"retrieval",kind:"stage",title:"retrieve_graph_evidence()",summary:"Reads local graph artifacts, collects primary articles and reforms, then attaches practical or interpretive support after the graph is grounded.",actors:["python"],metrics:["artifacts on disk","graph_first"],order:3,detailHtml:`
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
    `},{id:"retrieval.answer",lane:"retrieval",kind:"stage",title:"compose_graph_native_answer()",summary:"Publishes practice-first content: what to do, procedure, legal anchors, changes, precautions, and opportunities.",actors:["python"],metrics:["no meta","practical first"],order:4,detailHtml:`
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
    `},{id:"retrieval.contract",lane:"retrieval",kind:"stage",title:"PipelineCResponse",summary:"Returns the final contract: answer text, citations, diagnostics, confidence, and graph_native vs graph_native_partial.",actors:["python"],metrics:["citations","diagnostics"],order:5,detailHtml:`
      <p><strong>Two separate audiences exist here:</strong></p>
      <ul>
        <li><strong>User-facing:</strong> practical answer content only</li>
        <li><strong>Internal/runtime-facing:</strong> planner metadata, evidence bundle metadata, diagnostics, and confidence fields</li>
      </ul>
      <p>The response still carries diagnostics for debugging, but that metadata is not supposed to leak into the published accountant reply.</p>
    `},{id:"surfaces.public",lane:"surfaces",kind:"stage",title:"Public GUI",summary:"Local no-login browser path on /public. This is the fastest way to test the real corpus-backed chat experience.",actors:["python"],metrics:["public profile"],order:0,detailHtml:`
      <p>Local development enables the public visitor flow so the team can test real chat without full login friction.</p>
      <p>This surface now hits the same <code>pipeline_d</code> route as the API.</p>
    `},{id:"surfaces.auth",lane:"surfaces",kind:"stage",title:"Authenticated GUI",summary:"Same chat runtime, but with account-scoped shells and the future managed-chat experience layered around it.",actors:["python"],metrics:["same runtime"],order:1,detailHtml:`
      <p>The important orchestration truth is shared runtime, not separate chat logic.</p>
      <p>Public and authenticated shells should differ in access and product chrome, not in the legal answer engine.</p>
    `},{id:"surfaces.normativa",lane:"surfaces",kind:"stage",title:"Normativa / Evidence Panels",summary:"This is where deeper legal reading belongs: source text, citations, and evidence inspection beyond the main answer body.",actors:["python"],metrics:["deep dive"],order:2,detailHtml:`
      <p>The main answer should help the accountant act.</p>
      <p>The normativa surfaces are where the accountant can rest, verify legal context, and dig deeper into the exact texts if desired.</p>
    `},{id:"surfaces.partial",lane:"surfaces",kind:"config",title:"Still Partial",summary:"Chat works end to end, but rich evidence drill-down, saved history, and some managed/admin surfaces still need more restoration.",actors:["python"],metrics:["chat ready","managed layer partial"],order:3,detailHtml:`
      <p><strong>Healthy now:</strong> open GUI, ask a question, get a corpus-backed answer.</p>
      <p><strong>Still recovering:</strong> richer evidence utilities, saved conversation management, and some operational surfaces.</p>
    `},{id:"almacenamiento.artifacts",lane:"almacenamiento",kind:"store",title:"Local Artifacts on Disk",summary:"The live answer path reads local graph artifacts. This is the actual retrieval source for served chat today.",actors:["python"],metrics:["manifest + articles + edges"],order:0,detailHtml:`
      <p><strong>This is the live retrieval source today:</strong></p>
      <ul>
        <li><code>canonical_corpus_manifest.json</code></li>
        <li><code>parsed_articles.jsonl</code></li>
        <li><code>typed_edges.jsonl</code></li>
      </ul>
      <p>If these artifacts are missing or stale, the served graph-native chat path degrades.</p>
    `},{id:"almacenamiento.supabase",lane:"almacenamiento",kind:"store",title:"Supabase Runtime Persistence",summary:"Supabase is for conversations, metrics, feedback, auth nonces, usage, and staging-mode persistence. It is not the live retrieval engine.",actors:["sql"],metrics:["runtime persistence"],order:1,detailHtml:`
      <p><strong>Used for:</strong></p>
      <ul>
        <li>Conversation state</li>
        <li>Chat runs and metrics</li>
        <li>Feedback</li>
        <li>Terms state, usage ledger, auth nonces, active-generation state</li>
      </ul>
      <p>This store surrounds the chat experience operationally, but the live answer engine still reads the local graph artifacts.</p>
    `},{id:"almacenamiento.falkor",lane:"almacenamiento",kind:"store",title:"Falkor Graph Parity",summary:"Falkor exists for local Docker parity and staging-mode graph operations, not for per-request live traversal in the current served chat path.",actors:["python"],metrics:["local docker","cloud staging"],order:2,detailHtml:`
      <p><strong>Environment split:</strong></p>
      <ul>
        <li><code>npm run dev</code> — local Docker Falkor</li>
        <li><code>npm run dev:staging</code> — cloud Falkor from env</li>
      </ul>
      <p>Important nuance: the answer path still uses generated artifacts, not a live Falkor traversal on every question.</p>
    `},{id:"ingesta.knowledge",lane:"ingesta",kind:"store",title:"knowledge_base/",summary:"Source material across normativa, interpretacion, and practica.",actors:["curator"],metrics:["source of truth"],order:0,detailHtml:`
      <p>The graph-native answer path depends on a curated corpus, not on ad hoc live web retrieval.</p>
      <p>The important families remain:</p>
      <ul>
        <li><code>normativa_base</code></li>
        <li><code>interpretative_guidance</code></li>
        <li><code>practica_erp</code></li>
      </ul>
    `},{id:"ingesta.manifest",lane:"ingesta",kind:"config",title:"Canonical Manifest",summary:"Tracks which documents are ready, what family they belong to, and how they should be interpreted downstream.",actors:["curator","python"],metrics:["ready docs only"],order:1,detailHtml:`
      <p>The manifest is the editorial contract between corpus curation and runtime behavior.</p>
      <p>It tells the system which support documents are canonical enough to ride alongside graph evidence.</p>
    `},{id:"ingesta.publish",lane:"ingesta",kind:"stage",title:"Published Corpus",summary:"Only canonically ready material should flow into the graph artifacts that power chat.",actors:["python"],metrics:["published set"],order:2,detailHtml:`
      <p>This step matters because the served chat path should not improvise from stale, draft, or off-policy material.</p>
    `},{id:"parsing.articles",lane:"parsing",kind:"stage",title:"parsed_articles.jsonl",summary:"Article nodes with title, excerpt, source path, and the keys needed for graph-native retrieval.",actors:["python"],metrics:["article nodes"],order:0,detailHtml:`
      <p>This artifact gives Lia Graph the legal anchors it can actually traverse and cite.</p>
    `},{id:"parsing.edges",lane:"parsing",kind:"stage",title:"typed_edges.jsonl",summary:"Typed relations such as REQUIRES, REFERENCES, MODIFIES, and SUPERSEDES connect the legal graph.",actors:["python"],metrics:["typed relations"],order:1,detailHtml:`
      <p>The planner chooses the traversal style; this artifact supplies the legal paths that make that traversal meaningful.</p>
    `},{id:"parsing.temporal",lane:"parsing",kind:"stage",title:"temporal_intent.py",summary:"Historical and vigencia helpers let the planner choose the right cutoff and the right reform context.",actors:["python"],metrics:["historical slice"],order:2,detailHtml:`
      <p>This is why questions like “antes de la Ley 2277 de 2022” can be handled as temporal graph problems instead of just string matching.</p>
    `},{id:"mobile.dev",lane:"mobile",kind:"stage",title:"npm run dev",summary:"Builds the public UI, runs health checks, uses filesystem storage plus local Docker Falkor, and serves the local app.",actors:["python"],metrics:["local health check"],order:0,detailHtml:`
      <p><strong>Local dev truth:</strong></p>
      <ul>
        <li>Public GUI is enabled</li>
        <li>Artifacts on disk power the answer path</li>
        <li>Local Falkor is checked for parity, not used as the live chat retriever</li>
      </ul>
    `},{id:"mobile.staging",lane:"mobile",kind:"stage",title:"npm run dev:staging",summary:"Runs the same app shell against cloud Falkor and Supabase persistence while keeping the served answer path artifact-backed.",actors:["python","sql"],metrics:["cloud env"],order:1,detailHtml:`
      <p>Staging-mode should be described as environment parity around the same product runtime, not as a totally different retrieval engine.</p>
    `},{id:"mobile.truth",lane:"mobile",kind:"config",title:"Production-Like Truth",summary:"Same HTML shell, same ui_server, same pipeline_d, same practical-first answer contract. The main remaining gaps are richer managed surfaces and sharper retrieval precision.",actors:["python"],metrics:["same served path"],order:2,detailHtml:`
      <p><strong>Healthy:</strong> the real GUI chat path is live.</p>
      <p><strong>Still improving:</strong> temporal precision, duplicate version disambiguation, and the richer managed-chat surfaces around the core answer engine.</p>
    `}],O=[{from:"plataforma.entry",to:"plataforma.server"},{from:"plataforma.server",to:"plataforma.router"},{from:"plataforma.router",to:"retrieval.topic_router",crossLane:!0,label:"default route"},{from:"retrieval.topic_router",to:"retrieval.planner"},{from:"retrieval.planner",to:"retrieval.resolve"},{from:"retrieval.resolve",to:"retrieval.evidence"},{from:"retrieval.evidence",to:"retrieval.answer"},{from:"retrieval.answer",to:"retrieval.contract"},{from:"retrieval.contract",to:"surfaces.public",crossLane:!0,label:"published answer"},{from:"retrieval.contract",to:"surfaces.auth",crossLane:!0,label:"published answer"},{from:"retrieval.contract",to:"surfaces.normativa",crossLane:!0,label:"citations + evidence"},{from:"surfaces.auth",to:"surfaces.partial",label:"managed layer"},{from:"ingesta.knowledge",to:"ingesta.manifest"},{from:"ingesta.manifest",to:"ingesta.publish"},{from:"ingesta.publish",to:"parsing.articles",crossLane:!0,label:"build"},{from:"ingesta.publish",to:"parsing.edges",crossLane:!0,label:"build"},{from:"parsing.articles",to:"almacenamiento.artifacts",crossLane:!0,label:"article nodes"},{from:"parsing.edges",to:"almacenamiento.artifacts",crossLane:!0,label:"typed graph"},{from:"parsing.temporal",to:"retrieval.planner",crossLane:!0,label:"historical intent"},{from:"almacenamiento.artifacts",to:"retrieval.evidence",crossLane:!0,label:"live answer source"},{from:"almacenamiento.supabase",to:"plataforma.server",crossLane:!0,label:"sessions + metrics"},{from:"almacenamiento.falkor",to:"mobile.dev",crossLane:!0,label:"local parity"},{from:"almacenamiento.falkor",to:"mobile.staging",crossLane:!0,label:"cloud parity"},{from:"mobile.dev",to:"plataforma.server",crossLane:!0,label:"local launch"},{from:"mobile.staging",to:"plataforma.server",crossLane:!0,label:"staging-mode launch"},{from:"mobile.truth",to:"plataforma.router",crossLane:!0,label:"served reality"}],L={nodes:B,edges:O,lanes:G},x=260,$=120,H=80,I=40,E=60,T=50,P=44,W=60,f=80;function U(e){const l=new Map,r=new Map,o=[...e.lanes].sort((d,h)=>d.order-h.order);let a=f,t=0;for(const d of o){const h=e.nodes.filter(y=>y.lane===d.id).sort((y,b)=>y.order-b.order),m=h.length*x+(h.length-1)*H+E*2,v=$+T*2+P+I,p={x:f,y:a,w:m,h:v};r.set(d.id,p);let g=f+E;const i=a+P+T;for(const y of h)l.set(y.id,{x:g,y:i,w:x,h:$}),g+=x+H;const u=f+m;u>t&&(t=u),a+=v+W}const n=t+f;for(const[,d]of r)d.w=n-f*2;const s=a+f;return{nodePositions:l,laneRects:r,canvasWidth:n,canvasHeight:s}}function j(e,l){const r=new Map,o=new Map,a=[...e.lanes].sort((h,c)=>h.order-c.order);let t=f,n=0;for(const h of a){const c=e.nodes.filter(w=>w.lane===h.id).sort((w,k)=>w.order-k.order);let m=$;for(const w of c){const k=l.get(w.id)??0,A=$+k;A>m&&(m=A)}const p=c.length*x+(c.length-1)*H+E*2,g=m+T*2+P+I,i={x:f,y:t,w:p,h:g};o.set(h.id,i);let u=f+E;const y=t+P+T;for(const w of c){const k=l.get(w.id)??0;r.set(w.id,{x:u,y,w:x,h:$+k}),u+=x+H}const b=f+p;b>n&&(n=b),t+=g+W}const s=n+f;for(const[,h]of o)h.w=s-f*2;const d=t+f;return{nodePositions:r,laneRects:o,canvasWidth:s,canvasHeight:d}}const Y={curator:_.actorCurator,python:_.actorPython,sql:_.actorSql,llm:_.actorLlm,embedding:_.actorEmbedding};function F(e){return`<span class="orch-actor" data-actor="${e}" title="${e}">${Y[e]}</span>`}function X(e){return e.map(F).join("")}function K(e,l,r){var o;for(const a of l.lanes){const t=r.laneRects.get(a.id);if(!t)continue;const n=document.createElement("div");n.className="orch-lane",n.dataset.lane=a.id,n.style.cssText=`left:${t.x}px;top:${t.y}px;width:${t.w}px;height:${t.h}px;`;const s=document.createElement("div");s.className="orch-lane-label",s.textContent=a.label,n.appendChild(s),e.appendChild(n)}for(const a of l.nodes){const t=r.nodePositions.get(a.id);if(!t)continue;const n=document.createElement("article");n.className="orch-node",n.dataset.nodeId=a.id,n.dataset.kind=a.kind,n.dataset.pipeline=a.lane,n.style.cssText=`left:${t.x}px;top:${t.y}px;width:${t.w}px;`;const s=(o=a.metrics)!=null&&o.length?`<div class="orch-node-metrics">${a.metrics.map(m=>`<span class="orch-metric">${m}</span>`).join("")}</div>`:"",d=a.detailHtml?`<div class="orch-node-detail" hidden>${a.detailHtml}</div>`:"",c=!!a.detailHtml?'<button class="orch-node-toggle" aria-expanded="false" aria-label="Expandir detalles">▸</button>':"";n.innerHTML=`
      <div class="orch-node-head">
        <div class="orch-node-badges">${X(a.actors)}</div>
        <h3 class="orch-node-title">${a.title}</h3>
        ${c}
      </div>
      <p class="orch-node-summary">${a.summary}</p>
      ${s}
      ${d}
    `,e.appendChild(n)}}function Q(e,l,r){for(const o of l.lanes){const a=r.laneRects.get(o.id);if(!a)continue;const t=e.querySelector(`.orch-lane[data-lane="${o.id}"]`);t&&(t.style.cssText=`left:${a.x}px;top:${a.y}px;width:${a.w}px;height:${a.h}px;`)}for(const o of l.nodes){const a=r.nodePositions.get(o.id);if(!a)continue;const t=e.querySelector(`.orch-node[data-node-id="${o.id}"]`);t&&(t.style.left=`${a.x}px`,t.style.top=`${a.y}px`,t.style.width=`${a.w}px`)}e.style.width=`${r.canvasWidth}px`,e.style.height=`${r.canvasHeight}px`}const R="orch-arrowhead",C="orch-arrowhead-cross";function M(e,l,r){e.innerHTML="",e.setAttribute("width",String(r.canvasWidth)),e.setAttribute("height",String(r.canvasHeight)),e.setAttribute("viewBox",`0 0 ${r.canvasWidth} ${r.canvasHeight}`);const o=document.createElementNS("http://www.w3.org/2000/svg","defs");o.innerHTML=`
    <marker id="${R}" viewBox="0 0 10 7" refX="10" refY="3.5"
            markerWidth="8" markerHeight="6" orient="auto-start-reverse">
      <polygon points="0 0, 10 3.5, 0 7" fill="var(--orch-edge-color)" />
    </marker>
    <marker id="${C}" viewBox="0 0 10 7" refX="10" refY="3.5"
            markerWidth="8" markerHeight="6" orient="auto-start-reverse">
      <polygon points="0 0, 10 3.5, 0 7" fill="var(--orch-edge-cross-color)" />
    </marker>
  `,e.appendChild(o);const a=new Map(l.nodes.map(t=>[t.id,t]));for(const t of l.edges){const n=r.nodePositions.get(t.from),s=r.nodePositions.get(t.to);if(!n||!s)continue;const d=a.get(t.from),h=a.get(t.to),c=t.crossLane??(d==null?void 0:d.lane)!==(h==null?void 0:h.lane),m=document.createElementNS("http://www.w3.org/2000/svg","path"),v=c?z(n,s):V(n,s);if(m.setAttribute("d",v),m.setAttribute("class",c?"orch-edge orch-edge--cross":"orch-edge"),m.setAttribute("marker-end",`url(#${c?C:R})`),e.appendChild(m),t.label){const p=(n.x+n.w+s.x)/2,g=(n.y+n.h/2+s.y+s.h/2)/2,i=document.createElementNS("http://www.w3.org/2000/svg","text");i.setAttribute("x",String(p)),i.setAttribute("y",String(g-6)),i.setAttribute("class","orch-edge-label"),i.textContent=t.label,e.appendChild(i)}}}function V(e,l){const r=e.x+x,o=e.y+$/2,a=l.x,t=l.y+$/2,n=(r+a)/2;return`M ${r},${o} C ${n},${o} ${n},${t} ${a},${t}`}function z(e,l){const r=e.x+x/2,o=e.y+e.h,a=l.x+x/2,t=l.y,n=(o+t)/2,s=12;if(Math.abs(r-a)<2)return`M ${r},${o} L ${a},${t}`;const d=a>r?1:-1;return`M ${r},${o} L ${r},${n-s} Q ${r},${n} ${r+s*d},${n} L ${a-s*d},${n} Q ${a},${n} ${a},${n+s} L ${a},${t}`}function q(e,l){const{viewport:r,minimapCanvas:o,lens:a}=e,t=o.getContext("2d");if(!t)return()=>{};const n=o.width,s=o.height,d=n/l.canvasWidth,h=s/l.canvasHeight,c=Math.min(d,h);function m(){if(t){t.clearRect(0,0,n,s),t.fillStyle=S.neutral[50],t.fillRect(0,0,n,s);for(const[,i]of l.laneRects)t.fillStyle=`${S.green[100]}80`,t.fillRect(i.x*c,i.y*c,i.w*c,i.h*c),t.strokeStyle=S.neutral[300],t.lineWidth=.5,t.strokeRect(i.x*c,i.y*c,i.w*c,i.h*c);for(const[,i]of l.nodePositions)t.fillStyle=S.white,t.fillRect(i.x*c,i.y*c,i.w*c,i.h*c),t.strokeStyle=S.neutral[400],t.lineWidth=.5,t.strokeRect(i.x*c,i.y*c,i.w*c,i.h*c)}}function v(){const i=r.clientWidth/l.canvasWidth*n,u=r.clientHeight/l.canvasHeight*s,y=r.scrollLeft/l.canvasWidth*n,b=r.scrollTop/l.canvasHeight*s;a.style.width=`${Math.min(i,n)}px`,a.style.height=`${Math.min(u,s)}px`,a.style.left=`${y}px`,a.style.top=`${b}px`}m(),v();const p=()=>v();r.addEventListener("scroll",p,{passive:!0});const g=i=>{const u=o.getBoundingClientRect(),y=i.clientX-u.left,b=i.clientY-u.top,w=y/n*l.canvasWidth-r.clientWidth/2,k=b/s*l.canvasHeight-r.clientHeight/2;r.scrollTo({left:Math.max(0,w),top:Math.max(0,k),behavior:"smooth"})};return o.addEventListener("click",g),()=>{r.removeEventListener("scroll",p),o.removeEventListener("click",g)}}function J(e,l,r){const o=l.laneRects.get(r);o&&e.scrollTo({left:Math.max(0,o.x-40),top:Math.max(0,o.y-20),behavior:"smooth"})}function Z(e){const r=o=>{switch(o.key){case"ArrowLeft":e.scrollBy({left:-120,behavior:"smooth"}),o.preventDefault();break;case"ArrowRight":e.scrollBy({left:120,behavior:"smooth"}),o.preventDefault();break;case"ArrowUp":e.scrollBy({top:-120,behavior:"smooth"}),o.preventDefault();break;case"ArrowDown":e.scrollBy({top:120,behavior:"smooth"}),o.preventDefault();break}};return document.addEventListener("keydown",r),()=>document.removeEventListener("keydown",r)}function ee(e,l){const r=e.querySelector("#orch-viewport"),o=e.querySelector("#orch-canvas"),a=e.querySelector("#orch-svg"),t=e.querySelector("#orch-minimap-canvas"),n=e.querySelector("#orch-minimap-lens");if(!r||!o||!a||!t||!n)return;let s=U(L);const d=new Map;o.style.width=`${s.canvasWidth}px`,o.style.height=`${s.canvasHeight}px`,K(o,L,s),M(a,L,s);let h=q({viewport:r,minimapCanvas:t,lens:n},s);const c=Z(r);e.querySelectorAll(".orch-lane-btn").forEach(v=>{v.addEventListener("click",()=>{const p=v.dataset.lane;J(r,s,p)})}),o.addEventListener("click",v=>{const p=v.target.closest(".orch-node-toggle");if(!p)return;const g=p.closest(".orch-node");if(!g)return;const i=g.dataset.nodeId;if(!i)return;const u=g.querySelector(".orch-node-detail");if(!u)return;if(p.getAttribute("aria-expanded")==="true")u.hidden=!0,p.setAttribute("aria-expanded","false"),p.textContent="▸",d.set(i,0);else{u.hidden=!1,p.setAttribute("aria-expanded","true"),p.textContent="▾";const b=u.scrollHeight;d.set(i,b+16)}s=j(L,d),o.style.width=`${s.canvasWidth}px`,o.style.height=`${s.canvasHeight}px`,Q(o,L,s),M(a,L,s),h(),h=q({viewport:r,minimapCanvas:t,lens:n},s)}),window.addEventListener("beforeunload",()=>{h(),c()})}D({missingRootMessage:"Missing #app root for orchestration page.",mountApp:ee,renderShell:N,title:e=>e.t("app.title.orchestration")||"LIA - Orquestacion de Pipelines"});
