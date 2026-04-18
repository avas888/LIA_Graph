import type { I18nRuntime } from "@/shared/i18n";

type ContractCard = {
  title: string;
  producer: string;
  contract: string;
  consumer: string;
  scope: string;
  bullets: string[];
};

type LaneCard = {
  id: string;
  number: string;
  title: string;
  summary: string;
  bullets: string[];
};

type ModuleCard = {
  title: string;
  path: string;
  role: string;
  consumes: string;
  produces: string;
  scope: "shared" | "main-chat" | "normativa" | "interpretacion" | "reader-windows";
  stability: "stable-facade" | "implementation-detail" | "surface-seam";
  bullets: string[];
};

const contractCards: ContractCard[] = [
  {
    title: "Request Envelope",
    producer: "ui_server.py + pipeline_c/contracts.py",
    contract: "normalized chat request",
    consumer: "topic_router.py / orchestrator.py",
    scope: "Compartido",
    bullets: [
      "Mensaje, historial, knobs y contexto de sesión.",
      "Define la forma de entrada común para GUI y API.",
    ],
  },
  {
    title: "Topic & Guardrails",
    producer: "topic_router.py",
    contract: "topic hints + dominant workflow pressure",
    consumer: "planner.py",
    scope: "Compartido",
    bullets: [
      "Resiste side mentions que intentan secuestrar la ruta.",
      "Le da al planner una lectura más útil que un topic flat.",
    ],
  },
  {
    title: "Retrieval Plan",
    producer: "planner.py",
    contract: "query_mode + entry_points + temporal_context",
    consumer: "retriever.py / orchestrator.py",
    scope: "Compartido",
    bullets: [
      "Convierte lenguaje contable en anclas, budgets y contexto temporal.",
      "En follow-ups enfocados puede heredar normas o período ya activos para no reabrir el caso desde cero.",
      "Es donde viven strategy_chain, reform_chain y los workflows operativos.",
    ],
  },
  {
    title: "Evidence Bundle",
    producer: "retriever.py",
    contract: "GraphEvidenceBundle",
    consumer: "answer_synthesis.py",
    scope: "Compartido",
    bullets: [
      "Primary articles, connected articles, reforms y support docs.",
      "El orden correcto es graph grounding primero, support después.",
    ],
  },
  {
    title: "Enrichment Signals",
    producer: "answer_support.py",
    contract: "article_insights + support_insights",
    consumer: "answer_synthesis.py",
    scope: "Compartido hot path",
    bullets: [
      "Extrae procedure, precaution, strategy, jurisprudence y checklist.",
      "Es la capa que evita que la respuesta dependa solo de copy hardcodeado.",
    ],
  },
  {
    title: "Structured Answer Parts",
    producer: "answer_synthesis.py",
    contract: "GraphNativeAnswerParts",
    consumer: "answer_assembly.py / orchestrator.py",
    scope: "Main chat",
    bullets: [
      "Recommendations, procedure, paperwork, legal anchors, context y precautions.",
      "Todavía no es markdown visible; es el handoff entre síntesis y assembly.",
    ],
  },
  {
    title: "Visible Markdown",
    producer: "answer_assembly.py",
    contract: "first-turn route + follow-up route + shared rendering helpers",
    consumer: "orchestrator.py",
    scope: "Main chat",
    bullets: [
      "Decide cómo se publica el primer turno y cómo se publica un second+ follow-up.",
      "Es un contrato de superficie, no de retrieval.",
    ],
  },
  {
    title: "Deterministic Citation Profile",
    producer: "ui_citation_profile_builders.py",
    contract: "citation modal/page chrome",
    consumer: "ui_citation_controllers.py / frontend normativa",
    scope: "Normativa",
    bullets: [
      "Resuelve doc_id/reference_key, familia normativa, binding force, facts, caution, original text y acciones.",
      "Sostiene phase=instant para que el modal abra rápido sin depender del grafo.",
    ],
  },
  {
    title: "Normativa Surface Parts",
    producer: "src/lia_graph/normativa/synthesis.py",
    contract: "NormativaSynthesis",
    consumer: "src/lia_graph/normativa/assembly.py / normative_analysis.py",
    scope: "Normativa",
    bullets: [
      "La fachada estable delega a policy, synthesis helpers y section builders dentro del paquete.",
      "Convierte shared graph evidence en lead, vigencia y narrativa útil para el contador sin reutilizar answer_first_bubble.py como contrato de modal.",
    ],
  },
  {
    title: "Normativa Published Payload",
    producer: "src/lia_graph/normativa/assembly.py + normative_analysis.py",
    contract: "phase=llm enrichment + deep analysis payload",
    consumer: "ui_citation_controllers.py / frontend normativa",
    scope: "Normativa",
    bullets: [
      "Mantiene el contrato viejo del modal y de la página profunda sin cambiar la UX visible.",
      "Los campos determinísticos siguen siendo la autoridad y el enrichment llena solo lo que le corresponde.",
    ],
  },
  {
    title: "Document Reader Payload",
    producer: "ui_source_view_processors.py",
    contract: "source-view / article-reader payload",
    consumer: "/source-view y lectores documentales",
    scope: "Ventanas lectoras",
    bullets: [
      "Renderiza documento original, navegación, excerpts y anexos sin pasar por answer_*.",
      "Es una superficie de lectura determinística, no una superficie de respuesta conversacional.",
    ],
  },
  {
    title: "Runtime Response",
    producer: "orchestrator.py",
    contract: "PipelineCResponse",
    consumer: "ui_server.py",
    scope: "Compartido runtime",
    bullets: [
      "Empaqueta answer text, citations, confidence y diagnostics.",
      "La UI ve respuesta y citas; los internals ven además el metadata de runtime.",
    ],
  },
];

const laneCards: LaneCard[] = [
  {
    id: "lane-0",
    number: "0",
    title: "Ingesta y artifacts",
    summary: "Del corpus crudo al bundle que el runtime sí puede leer.",
    bullets: [
      "Sync desde Dropbox a knowledge_base.",
      "Audit gate, manifest canónico y graphization normativa.",
      "Produce canonical_corpus_manifest, parsed_articles y typed_edges.",
    ],
  },
  {
    id: "lane-1",
    number: "1",
    title: "Entry y routing",
    summary: "La app recibe la pregunta y decide por qué runtime pasar.",
    bullets: [
      "ui_server.py normaliza entrada GUI/API.",
      "pipeline_router.py resuelve pipeline_d.",
      "No decide todavía el contenido de la respuesta.",
    ],
  },
  {
    id: "lane-2",
    number: "2",
    title: "Topic y guardrails",
    summary: "Convierte lenguaje de contador en hints útiles sin exigir cita legal.",
    bullets: [
      "Detecta workflow dominante.",
      "Evita que side mentions cambien de carril la consulta.",
      "Entrega pressure útil al planner.",
    ],
  },
  {
    id: "lane-3",
    number: "3",
    title: "Planner",
    summary: "Construye el retrieval plan, query_mode y temporal_context.",
    bullets: [
      "Strategy, reform, historical y operational chains viven aquí.",
      "Define anchors, budgets y lexical searches.",
      "Es donde se decide el porqué de la recuperación.",
    ],
  },
  {
    id: "lane-4",
    number: "4",
    title: "Retrieval (env-gated)",
    summary: "Resuelve anclas, camina el grafo y arma el evidence bundle. El orchestrator elige adapter por request según LIA_CORPUS_SOURCE + LIA_GRAPH_MODE (ver matriz v2026-04-18 en docs/guide/orchestration.md).",
    bullets: [
      "dev: retriever.py sobre artifacts locales + local Falkor docker (parity).",
      "dev:staging: retriever_supabase.py (hybrid_search RPC) + retriever_falkor.py (Cypher BFS sobre LIA_REGULATORY_GRAPH).",
      "Los tres adapters devuelven el mismo GraphEvidenceBundle; synthesis/assembly no saben cuál corrió.",
      "Falkor adapter propaga errores — nunca hace fallback silencioso a artifacts en staging.",
      "Historical mode sigue siendo más estricto con connected noise en cualquiera de los tres caminos.",
    ],
  },
  {
    id: "lane-5",
    number: "5",
    title: "Surface synthesis",
    summary: "Convierte evidencia en partes estructuradas específicas por superficie.",
    bullets: [
      "Main chat usa la facade estable answer_synthesis.py.",
      "Normativa usa src/lia_graph/normativa/synthesis.py como seam estable sobre shared graph evidence.",
      "Todavía no es payload visible final; sigue siendo handoff de síntesis.",
    ],
  },
  {
    id: "lane-6",
    number: "6",
    title: "Surface assembly",
    summary: "Publica first turn, second+ follow-ups o payloads de modal/page para Normativa.",
    bullets: [
      "Main chat publica con answer_assembly.py: first bubble en turno 1 y follow-up path en turno 2+.",
      "Normativa publica con src/lia_graph/normativa/assembly.py sobre el contrato viejo del modal.",
      "Las ventanas lectoras siguen siendo determinísticas y no pasan por answer_assembly.py.",
    ],
  },
  {
    id: "lane-7",
    number: "7",
    title: "Response packaging",
    summary: "Empaqueta chat, expone endpoints de ventana y deja diagnostics fuera de la respuesta visible.",
    bullets: [
      "orchestrator.py empaqueta PipelineCResponse para main chat.",
      "ui_citation_controllers.py expone /api/citation-profile y /api/normative-analysis.",
      "Supabase persiste runtime state y — en dev:staging — también sirve los chunks del retrieval vía hybrid_search.",
      "FalkorDB es el traversal engine live en dev:staging (LIA_GRAPH_MODE=falkor_live); en dev sigue siendo soporte de graph ops.",
      "response.diagnostics.retrieval_backend + graph_backend dejan claro qué adapter atendió cada turno.",
    ],
  },
];

const moduleCards: ModuleCard[] = [
  {
    title: "ui_server.py",
    path: "src/lia_graph/ui_server.py",
    role: "Entry shell del producto",
    consumes: "HTTP request, auth/public context",
    produces: "normalized request + served HTML/API surface",
    scope: "shared",
    stability: "implementation-detail",
    bullets: [
      "Sirve /public, /api/chat, /api/chat/stream y /orchestration.",
      "Dispara el runtime pero no decide el shaping visible del answer.",
    ],
  },
  {
    title: "planner.py",
    path: "src/lia_graph/pipeline_d/planner.py",
    role: "Planificador de retrieval",
    consumes: "message + topic hints + guardrails",
    produces: "retrieval plan",
    scope: "shared",
    stability: "implementation-detail",
    bullets: [
      "Define query_mode, entry_points, budgets y temporal_context.",
      "Puede heredar anchors y período del caso activo cuando el usuario hace double click en un punto previo.",
      "Es shared logic; Normativa puede reutilizarlo si su problema es realmente el mismo.",
    ],
  },
  {
    title: "retriever.py",
    path: "src/lia_graph/pipeline_d/retriever.py",
    role: "Graph evidence selector (dev / artifacts)",
    consumes: "retrieval plan + artifacts",
    produces: "GraphEvidenceBundle",
    scope: "shared",
    stability: "implementation-detail",
    bullets: [
      "Arma primary_articles, connected_articles, related_reforms y support_documents desde artifacts.",
      "Sigue siendo el path por defecto para dev (LIA_CORPUS_SOURCE=artifacts).",
    ],
  },
  {
    title: "retriever_supabase.py",
    path: "src/lia_graph/pipeline_d/retriever_supabase.py",
    role: "Supabase hybrid_search adapter (staging)",
    consumes: "retrieval plan + cloud Supabase (documents, hybrid_search RPC)",
    produces: "GraphEvidenceBundle (chunks + citations)",
    scope: "shared",
    stability: "implementation-detail",
    bullets: [
      "Activo cuando LIA_CORPUS_SOURCE=supabase (dev:staging default).",
      "Produce primary/connected articles desde chunk rows y citations/support docs desde documents.",
    ],
  },
  {
    title: "retriever_falkor.py",
    path: "src/lia_graph/pipeline_d/retriever_falkor.py",
    role: "FalkorDB bounded Cypher BFS (staging)",
    consumes: "retrieval plan + cloud FalkorDB (LIA_REGULATORY_GRAPH)",
    produces: "GraphEvidenceBundle (graph half)",
    scope: "shared",
    stability: "implementation-detail",
    bullets: [
      "Activo cuando LIA_GRAPH_MODE=falkor_live (dev:staging default).",
      "Cualquier error de Falkor se propaga — nada de fallback silencioso a artifacts.",
    ],
  },
  {
    title: "supabase_sink.py",
    path: "src/lia_graph/ingestion/supabase_sink.py",
    role: "Corpus sink (build-time, cloud)",
    consumes: "parsed articles + classified edges + canonical manifest",
    produces: "upserts a documents / document_chunks / corpus_generations / normative_edges",
    scope: "shared",
    stability: "implementation-detail",
    bullets: [
      "Se ejecuta vía make phase2-graph-artifacts-supabase, strictamente aditivo.",
      "Idempotente por (source_key,target_key,relation,generation_id) y chunk_id; no toca embeddings.",
    ],
  },
  {
    title: "answer_support.py",
    path: "src/lia_graph/pipeline_d/answer_support.py",
    role: "Extractor de enrichment",
    consumes: "primary/connected articles + support docs",
    produces: "article_insights + support_insights",
    scope: "shared",
    stability: "implementation-detail",
    bullets: [
      "Captura procedure, precaution, strategy, jurisprudence y checklist.",
      "Es la bisagra entre retrieval y síntesis.",
    ],
  },
  {
    title: "answer_synthesis.py",
    path: "src/lia_graph/pipeline_d/answer_synthesis.py",
    role: "Fachada estable de síntesis",
    consumes: "GraphEvidenceBundle + insights + temporal_context",
    produces: "GraphNativeAnswerParts",
    scope: "main-chat",
    stability: "stable-facade",
    bullets: [
      "Es el entrypoint que deberían consumir otros módulos del runtime.",
      "Oculta la descomposición interna de synthesis para main chat.",
    ],
  },
  {
    title: "answer_synthesis_sections.py",
    path: "src/lia_graph/pipeline_d/answer_synthesis_sections.py",
    role: "Builders por sección",
    consumes: "evidence + insights + temporal context",
    produces: "candidate lines por sección",
    scope: "main-chat",
    stability: "implementation-detail",
    bullets: [
      "Recommendations, procedure, paperwork, legal anchors, context, precautions, opportunities.",
      "Aquí vive la priorización de qué candidato pertenece a qué sección.",
    ],
  },
  {
    title: "answer_synthesis_helpers.py",
    path: "src/lia_graph/pipeline_d/answer_synthesis_helpers.py",
    role: "Heurísticas compartidas de síntesis",
    consumes: "candidate lines + articles + support text",
    produces: "fallbacks y helpers reutilizables",
    scope: "main-chat",
    stability: "implementation-detail",
    bullets: [
      "Support-line extension, fallbacks, anchor-tail injection y heurísticas tributarias.",
      "No debería absorber visible UX ni títulos de secciones.",
    ],
  },
  {
    title: "answer_assembly.py",
    path: "src/lia_graph/pipeline_d/answer_assembly.py",
    role: "Fachada estable de assembly",
    consumes: "GraphNativeAnswerParts",
    produces: "first-turn route + follow-up route + shared exports",
    scope: "main-chat",
    stability: "stable-facade",
    bullets: [
      "Es la puerta correcta para consumir assembly del main chat.",
      "No obliga a conocer el layout interno del first turn ni del follow-up path.",
    ],
  },
  {
    title: "answer_followup.py",
    path: "src/lia_graph/pipeline_d/answer_followup.py",
    role: "Compositor del second+ turno",
    consumes: "answer parts + request continuity context",
    produces: "focused drill-down answers o follow-up sections más directas",
    scope: "main-chat",
    stability: "implementation-detail",
    bullets: [
      "Decide si el usuario está haciendo double click en un punto previo o abriendo un follow-up más amplio.",
      "Publica second+ answers sin replay automático del mapa amplio del primer turno.",
    ],
  },
  {
    title: "answer_first_bubble.py",
    path: "src/lia_graph/pipeline_d/answer_first_bubble.py",
    role: "Compositor del primer turno",
    consumes: "answer parts + temporal context + support signal",
    produces: "first-turn visible sections",
    scope: "main-chat",
    stability: "implementation-detail",
    bullets: [
      "Decide shape general vs tax-planning advisory.",
      "No elige anchors ni recap por sí solo; delega esos subproblemas.",
    ],
  },
  {
    title: "answer_inline_anchors.py",
    path: "src/lia_graph/pipeline_d/answer_inline_anchors.py",
    role: "Line-level legal anchoring",
    consumes: "candidate lines + primary/connected articles",
    produces: "PreparedAnswerLine con bases inline",
    scope: "main-chat",
    stability: "implementation-detail",
    bullets: [
      "Limpia tails viejos, puntúa anchors y renderiza la base legal al final de la línea.",
      "Es donde la recomendación se amarra al porqué normativo de manera legible.",
    ],
  },
  {
    title: "answer_historical_recap.py",
    path: "src/lia_graph/pipeline_d/answer_historical_recap.py",
    role: "Recap histórico",
    consumes: "primary articles + reforms + temporal context",
    produces: "líneas de recap nuevo -> viejo",
    scope: "main-chat",
    stability: "implementation-detail",
    bullets: [
      "Decide si el recap aparece.",
      "Ordena y redacta reform chains sin mezclar eso con el resto del assembly.",
    ],
  },
  {
    title: "answer_shared.py",
    path: "src/lia_graph/pipeline_d/answer_shared.py",
    role: "Utilidades comunes de publicación",
    consumes: "candidate lines y request metadata",
    produces: "normalización, filtros y render helpers",
    scope: "main-chat",
    stability: "implementation-detail",
    bullets: [
      "normalize_text, filtering, dedup, first-response gating y markdown helpers.",
      "Es shared dentro de main chat, no shared entre superficies.",
    ],
  },
  {
    title: "orchestrator.py",
    path: "src/lia_graph/pipeline_d/orchestrator.py",
    role: "Runtime flow de Pipeline D",
    consumes: "normalized request",
    produces: "PipelineCResponse",
    scope: "shared",
    stability: "implementation-detail",
    bullets: [
      "Entry point del runtime servido.",
      "Planifica, recupera, sintetiza, ensambla y empaqueta sin absorber toda la lógica interna.",
    ],
  },
  {
    title: "ui_citation_controllers.py",
    path: "src/lia_graph/ui_citation_controllers.py",
    role: "Controlador HTTP de Normativa",
    consumes: "/api/citation-profile y /api/normative-analysis",
    produces: "phase=instant/phase=llm payloads + deep analysis payload",
    scope: "normativa",
    stability: "implementation-detail",
    bullets: [
      "Mantiene el contrato viejo de frontend mientras deriva el enrichment al paquete src/lia_graph/normativa/.",
      "Es la bisagra entre la capa determinística de perfil y la capa graph-backed de Normativa.",
    ],
  },
  {
    title: "ui_citation_profile_builders.py",
    path: "src/lia_graph/ui_citation_profile_builders.py",
    role: "Builder determinístico de chrome normativa",
    consumes: "resolved citation/doc context + taxonomy helpers",
    produces: "facts, caution, original_text, vigencia, actions, needs_llm",
    scope: "normativa",
    stability: "implementation-detail",
    bullets: [
      "Restauró el read path heredado de Lia Contadores para el modal de Normativa.",
      "Define el primer paint rápido y autoritativo antes de cualquier enrichment graph-backed.",
    ],
  },
  {
    title: "src/lia_graph/normativa/orchestrator.py",
    path: "src/lia_graph/normativa/orchestrator.py",
    role: "Runtime flow propio de Normativa",
    consumes: "deterministic citation context + shared planner/retriever",
    produces: "surface-specific synthesis inputs + diagnostics",
    scope: "normativa",
    stability: "stable-facade",
    bullets: [
      "Reutiliza graph retrieval compartido sin importar answer_* del main chat.",
      "Es el seam correcto para adaptar Normativa a futuras evoluciones de Pipeline D.",
    ],
  },
  {
    title: "src/lia_graph/normativa/synthesis.py",
    path: "src/lia_graph/normativa/synthesis.py",
    role: "Fachada estable de síntesis de Normativa",
    consumes: "GraphEvidenceBundle + normative context",
    produces: "NormativaSynthesis",
    scope: "normativa",
    stability: "stable-facade",
    bullets: [
      "Es la puerta correcta para consumir síntesis de la superficie Normativa.",
      "Mantiene separado el seam estable de las heurísticas y builders internos.",
    ],
  },
  {
    title: "src/lia_graph/normativa/policy.py",
    path: "src/lia_graph/normativa/policy.py",
    role: "Política declarativa de Normativa",
    consumes: "section ids, titles y límites de surface",
    produces: "blueprints y constantes de síntesis/assembly",
    scope: "normativa",
    stability: "implementation-detail",
    bullets: [
      "Centraliza títulos, ids y límites útiles de la superficie.",
      "Evita strings repartidos entre orchestrator, synthesis y sections.",
    ],
  },
  {
    title: "src/lia_graph/normativa/synthesis_helpers.py",
    path: "src/lia_graph/normativa/synthesis_helpers.py",
    role: "Helpers de evidence-to-parts",
    consumes: "GraphEvidenceBundle + context",
    produces: "anchor lines, relation lines, support lines y diagnostics",
    scope: "normativa",
    stability: "implementation-detail",
    bullets: [
      "Separa la recolección de señales del armado visible de secciones.",
      "Hace que editar Normativa se parezca más a agregar un recognizer o collector que a tocar una sola función grande.",
    ],
  },
  {
    title: "src/lia_graph/normativa/sections.py",
    path: "src/lia_graph/normativa/sections.py",
    role: "Builders por sección de Normativa",
    consumes: "surface parts + section policy",
    produces: "summaries, next steps y sections publicables",
    scope: "normativa",
    stability: "implementation-detail",
    bullets: [
      "Construye hierarchy/applicability/professional impact/relations sin acoplarse al modal heredado.",
      "Es el equivalente surface-specific al layer de section builders del main chat.",
    ],
  },
  {
    title: "src/lia_graph/normativa/assembly.py",
    path: "src/lia_graph/normativa/assembly.py",
    role: "Assembly del modal y deep analysis de Normativa",
    consumes: "normativa surface parts + deterministic payload",
    produces: "payloads compatibles con el frontend heredado",
    scope: "normativa",
    stability: "stable-facade",
    bullets: [
      "Mapea enrichment graph-backed al contrato ya usado por profileRenderer.ts y normativeAnalysisApp.ts.",
      "Mantiene separados los campos autoritativos determinísticos de la narrativa adicional.",
    ],
  },
  {
    title: "normative_analysis.py",
    path: "src/lia_graph/normative_analysis.py",
    role: "Payload builder de análisis profundo",
    consumes: "citation context + deterministic processors + normativa assembly",
    produces: "deep-analysis sections y chrome estructural",
    scope: "normativa",
    stability: "implementation-detail",
    bullets: [
      "Conserva facts, caution, relations y actions en la página de análisis.",
      "Delega la narrativa generada al paquete de Normativa en lugar de la UI de chat.",
    ],
  },
  {
    title: "ui_analysis_controllers.py",
    path: "src/lia_graph/ui_analysis_controllers.py",
    role: "Seam HTTP de Interpretación",
    consumes: "requests de análisis/interpretación",
    produces: "dispatch al paquete src/lia_graph/interpretacion/*",
    scope: "interpretacion",
    stability: "surface-seam",
    bullets: [
      "Recibe los endpoints de Expertos y los deriva al runtime propio de la superficie.",
      "Mantiene separado el controlador HTTP de la síntesis visible y del ranking interno.",
    ],
  },
  {
    title: "src/lia_graph/interpretacion/orchestrator.py",
    path: "src/lia_graph/interpretacion/orchestrator.py",
    role: "Runtime flow propio de Interpretación",
    consumes: "turn kernel + shared retrieval utilities",
    produces: "surface-specific synthesis inputs + endpoint payloads",
    scope: "interpretacion",
    stability: "stable-facade",
    bullets: [
      "Lanza el retrieval de Expertos con el kernel mínimo del turno, sin colgarse de la completion de Normativa.",
      "Orquesta expert panel, citation interpretations y interpretation summary sin tocar answer_* del chat.",
    ],
  },
  {
    title: "src/lia_graph/interpretacion/synthesis.py",
    path: "src/lia_graph/interpretacion/synthesis.py",
    role: "Fachada estable de síntesis de Interpretación",
    consumes: "candidate docs + decision frame",
    produces: "ExpertPanelSurface y CitationInterpretationsSurface",
    scope: "interpretacion",
    stability: "stable-facade",
    bullets: [
      "Agrupa, ordena y publica tarjetas interpretativas como contrato propio de la superficie.",
      "Mantiene separado el seam estable de los heurísticos y builders internos.",
    ],
  },
  {
    title: "src/lia_graph/interpretacion/policy.py",
    path: "src/lia_graph/interpretacion/policy.py",
    role: "Política declarativa de Interpretación",
    consumes: "límites, modos y prompts de surface",
    produces: "constantes y blueprints de summary/enhance/explore",
    scope: "interpretacion",
    stability: "implementation-detail",
    bullets: [
      "Centraliza límites operativos del panel de Expertos y de sus prompts auxiliares.",
      "Evita strings y topes repartidos entre orchestrator, synthesis y assembly.",
    ],
  },
  {
    title: "src/lia_graph/interpretacion/synthesis_helpers.py",
    path: "src/lia_graph/interpretacion/synthesis_helpers.py",
    role: "Helpers de ranking, grouping y fallback",
    consumes: "candidate docs + decision frame + requested refs",
    produces: "selection, group classification y fallbacks determinísticos",
    scope: "interpretacion",
    stability: "implementation-detail",
    bullets: [
      "Separa la recolección y scoring de señales del armado visible del panel.",
      "Permite que editar Interpretación se parezca a agregar recognizers o precedence rules, no a tocar una sola función grande.",
    ],
  },
  {
    title: "src/lia_graph/interpretacion/assembly.py",
    path: "src/lia_graph/interpretacion/assembly.py",
    role: "Assembly de payloads de Interpretación",
    consumes: "surface parts + llm/deterministic runtime state",
    produces: "payloads para expert panel, summary y explore",
    scope: "interpretacion",
    stability: "stable-facade",
    bullets: [
      "Mapea la síntesis interpretativa al contrato ya esperado por expertPanelController.ts y interpretationModal.ts.",
      "Mantiene separado el runtime interno del shape público de cada endpoint.",
    ],
  },
  {
    title: "interpretation_relevance.py",
    path: "src/lia_graph/interpretation_relevance.py",
    role: "Fachada de compatibilidad para ranking interpretativo",
    consumes: "imports heredados desde ui_server y módulos shared",
    produces: "re-export del contrato del paquete interpretacion",
    scope: "interpretacion",
    stability: "implementation-detail",
    bullets: [
      "Mantiene estable la costura vieja mientras la autoridad real vive en src/lia_graph/interpretacion/.",
      "Evita que callers antiguos tengan que conocer el refactor completo del surface package.",
    ],
  },
  {
    title: "ui_source_view_processors.py",
    path: "src/lia_graph/ui_source_view_processors.py",
    role: "Builder de lectores documentales",
    consumes: "source text + metadata + reader params",
    produces: "source-view/article-reader payload",
    scope: "reader-windows",
    stability: "implementation-detail",
    bullets: [
      "Renderiza el documento original, la navegación interna y los extractos legibles.",
      "No depende de answer_synthesis.py ni answer_assembly.py.",
    ],
  },
  {
    title: "ui_normative_processors.py",
    path: "src/lia_graph/ui_normative_processors.py",
    role: "Procesadores normativos determinísticos",
    consumes: "markdown/texto original + resolved document rows",
    produces: "ET locators, vigencia detail y additional depth sections",
    scope: "reader-windows",
    stability: "implementation-detail",
    bullets: [
      "Alimenta Normativa y los lectores con estructura documental confiable y rápida.",
      "La vigencia resumida ya no depende de un camino LLM aparte para abrir la ventana.",
    ],
  },
];

const tuningRows = [
  {
    symptom: "Se activó el workflow equivocado",
    edit: "planner.py",
    why: "El problema está en query_mode, entry points o temporal intent.",
  },
  {
    symptom: "La evidencia está mal anclada",
    edit: "retriever.py / retrieval_support.py",
    why: "El bundle llegó mal antes de que existiera el answer.",
  },
  {
    symptom: "La evidencia es buena pero las secciones salen flojas",
    edit: "answer_synthesis_sections.py / answer_synthesis_helpers.py",
    why: "El fallo está en candidate generation, no en rendering.",
  },
  {
    symptom: "La primera burbuja está bien orientada pero los anclajes inline son pobres",
    edit: "answer_inline_anchors.py",
    why: "Es un problema line-level de anchor selection y phrasing.",
  },
  {
    symptom: "El recap histórico aparece mal o se siente ruidoso",
    edit: "answer_historical_recap.py",
    why: "Ahí vive la lógica de visibilidad y wording del recap.",
  },
  {
    symptom: "La voz o el shape visible están mal",
    edit: "answer_policy.py / answer_first_bubble.py / answer_followup.py / answer_shared.py",
    why: "Es un problema de policy o assembly, no de retrieval.",
  },
  {
    symptom: "Normativa abre con facts, caution o vigencia determinística incorrectos",
    edit: "ui_citation_profile_builders.py / ui_reference_resolvers.py / ui_normative_processors.py",
    why: "El problema está en el read path autoritativo del modal, no en el graph enrichment.",
  },
  {
    symptom: "Normativa trae buena evidencia pero se siente floja o poco útil",
    edit: "src/lia_graph/normativa/policy.py / src/lia_graph/normativa/synthesis_helpers.py / src/lia_graph/normativa/sections.py",
    why: "Ahí vive la traducción de evidencia a narrativa específica de la superficie y sus blueprints declarativos.",
  },
  {
    symptom: "El contrato del modal o de /normative-analysis sale mal armado",
    edit: "src/lia_graph/normativa/assembly.py / ui_citation_controllers.py / normative_analysis.py",
    why: "Es un problema de payload mapping y endpoint assembly, no del first bubble del chat.",
  },
  {
    symptom: "La ventana de Interpretación necesita cambios visibles",
    edit: "src/lia_graph/interpretacion/orchestrator.py / synthesis.py / policy.py / synthesis_helpers.py / assembly.py",
    why: "Debe evolucionar como superficie independiente, con runtime y assembly propios.",
  },
  {
    symptom: "El lector de documento/artículo muestra mal el original o la navegación",
    edit: "ui_source_view_processors.py / ui_normative_processors.py",
    why: "Es una superficie de lectura determinística con reglas propias.",
  },
];

export function mountOrchestrationApp(
  root: HTMLElement,
  _ctx: { i18n: I18nRuntime },
): void {
  const content = root.querySelector<HTMLElement>("#orch-content");
  const scrollRoot = root.querySelector<HTMLElement>("#orch-scroll");
  if (!content || !scrollRoot) return;

  content.innerHTML = renderPage();

  const navButtons = Array.from(root.querySelectorAll<HTMLElement>(".orch-nav-btn"));
  navButtons.forEach((button) => {
    button.addEventListener("click", (event) => {
      const targetId = button.dataset.target;
      if (!targetId) return;
      const target = root.querySelector<HTMLElement>(`#${targetId}`);
      if (!target) return;
      event.preventDefault();
      const toolbar = root.querySelector<HTMLElement>(".orch-toolbar");
      const toolbarOffset = (toolbar?.getBoundingClientRect().height || 0) + 18;
      const top = Math.max(0, target.getBoundingClientRect().top + window.scrollY - toolbarOffset);
      try {
        window.scrollTo({ top, behavior: "smooth" });
      } catch (_error) {
        target.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    });
  });

  const filterButtons = Array.from(root.querySelectorAll<HTMLButtonElement>(".orch-filter-btn"));
  const moduleCards = Array.from(root.querySelectorAll<HTMLElement>(".orch-module-card"));

  const applyScopeFilter = (scope: string) => {
    filterButtons.forEach((button) => {
      button.setAttribute("aria-pressed", String(button.dataset.scopeFilter === scope));
    });
    moduleCards.forEach((card) => {
      const cardScope = card.dataset.scope;
      card.hidden = !(scope === "all" || cardScope === scope);
    });
  };

  filterButtons.forEach((button) => {
    button.addEventListener("click", () => {
      applyScopeFilter(button.dataset.scopeFilter || "all");
    });
  });

  applyScopeFilter("all");
}

function renderPage(): string {
  return `
    <section id="orch-overview" class="orch-section orch-hero-section">
      <div class="orch-section-header">
        <p class="orch-section-kicker">Vista general</p>
        <h2 class="orch-section-title">La arquitectura nueva está organizada por contratos y facades</h2>
        <p class="orch-section-copy">
          La idea central ya no es “un orchestrator enorme que hace todo”, sino una cadena de handoffs explícitos:
          request normalizado, retrieval plan, evidence bundle, enrichment insights, answer parts, assembly visible y response contract.
        </p>
      </div>

      <div class="orch-overview-grid">
        <article class="orch-highlight-card">
          <span class="orch-highlight-label">Request path</span>
          <h3>ui_server → pipeline_router → topic_router → orchestrator</h3>
          <p>La ruta pública es corta y clara. El detalle vive detrás de Pipeline D, no disperso por la UI.</p>
        </article>
        <article class="orch-highlight-card">
          <span class="orch-highlight-label">Execution path</span>
          <h3>planner → retriever → synthesis facade → assembly facade</h3>
          <p>La ejecución interna ya distingue evidencia, síntesis y publicación visible, incluyendo first turn vs second+ follow-up del chat.</p>
        </article>
        <article class="orch-highlight-card">
          <span class="orch-highlight-label">Surface rule</span>
          <h3>Cada ventana tiene su propia assembly: chat, Normativa, Interpretación y lectores</h3>
          <p>Se comparte graph logic cuando tiene sentido. La UX contract se separa por superficie.</p>
        </article>
        <article class="orch-highlight-card">
          <span class="orch-highlight-label">Post-answer tracks</span>
          <h3>Bubble primero; Normativa e Interpretación arrancan después con el mismo kernel mínimo</h3>
          <p>Las ventanas laterales son sibling tracks. No bloquean el bubble ni se bloquean entre sí más allá de la semilla del turno.</p>
        </article>
        <article class="orch-highlight-card">
          <span class="orch-highlight-label">Env matrix v2026-04-18</span>
          <h3>dev lee artifacts; dev:staging lee Supabase + FalkorDB live</h3>
          <p>LIA_CORPUS_SOURCE y LIA_GRAPH_MODE, seteados por scripts/dev-launcher.mjs, eligen el adapter por request. Tabla versionada y change log viven en docs/guide/orchestration.md.</p>
        </article>
      </div>
    </section>

    <section id="orch-contracts" class="orch-section">
      <div class="orch-section-header">
        <p class="orch-section-kicker">Information architecture</p>
        <h2 class="orch-section-title">Mapa de contratos</h2>
        <p class="orch-section-copy">
          Esta es la secuencia más importante para entender el runtime: cada capa produce un contrato claro que la siguiente consume.
        </p>
      </div>
      <div class="orch-contract-flow">
        ${contractCards.map(renderContractCard).join("")}
      </div>
    </section>

    <section id="orch-lanes" class="orch-section">
      <div class="orch-section-header">
        <p class="orch-section-kicker">Runtime lanes</p>
        <h2 class="orch-section-title">Del corpus al answer visible</h2>
        <p class="orch-section-copy">
          Los lanes ordenan la historia completa: build-time, runtime path, synthesis, assembly y packaging.
        </p>
      </div>
      <div class="orch-lane-grid">
        ${laneCards.map(renderLaneCard).join("")}
      </div>
    </section>

    <section id="orch-modules" class="orch-section">
      <div class="orch-section-header">
        <p class="orch-section-kicker">Module map</p>
        <h2 class="orch-section-title">Quién hace qué</h2>
        <p class="orch-section-copy">
          Los filtros de arriba recortan este mapa por alcance. Las facades estables son las puertas correctas; los demás módulos son implementación más específica.
        </p>
      </div>
      <div class="orch-module-grid">
        ${moduleCards.map(renderModuleCard).join("")}
      </div>
    </section>

    <section id="orch-surfaces" class="orch-section">
      <div class="orch-section-header">
        <p class="orch-section-kicker">Surface boundaries</p>
        <h2 class="orch-section-title">Qué se comparte y qué no</h2>
        <p class="orch-section-copy">
          El principal cambio de arquitectura es este límite: la lógica de evidencia puede compartirse; la assembly visible no.
        </p>
      </div>
      <div class="orch-boundary-grid">
        <article class="orch-boundary-card" data-tone="shared">
          <h3>Graph runtime compartido</h3>
          <ul>
            <li>Request normalization</li>
            <li>Topic routing y guardrails</li>
            <li>Planner</li>
            <li>Retriever y evidence bundle</li>
            <li>Enrichment extraction si realmente aplica a varias superficies</li>
          </ul>
        </article>
        <article class="orch-boundary-card" data-tone="main-chat">
          <h3>Main chat</h3>
          <ul>
            <li>answer_synthesis facade</li>
            <li>answer_assembly facade</li>
            <li>first bubble shapes</li>
            <li>follow-up publication path</li>
            <li>inline legal anchors del chat</li>
            <li>historical recap del chat</li>
          </ul>
        </article>
        <article class="orch-boundary-card" data-tone="future">
          <h3>Normativa</h3>
          <ul>
            <li>capa determinística de citation/profile</li>
            <li>paquete propio src/lia_graph/normativa/* para enrichment</li>
            <li>reutiliza planner/retriever compartidos cuando aplica</li>
            <li>no consume el first bubble del chat como UI contract</li>
          </ul>
        </article>
        <article class="orch-boundary-card" data-tone="future">
          <h3>Interpretación</h3>
          <ul>
            <li>controller seam + paquete propio src/lia_graph/interpretacion/*</li>
            <li>ranking, grouping, summary y explore propios</li>
            <li>puede compartir evidence utilities</li>
            <li>arranca después del bubble sin esperar el retrieval completo de Normativa</li>
            <li>no debe piggybackear sobre Normativa ni sobre main chat</li>
          </ul>
        </article>
        <article class="orch-boundary-card" data-tone="shared">
          <h3>Lectores documentales</h3>
          <ul>
            <li>source view, article reader y form/document windows</li>
            <li>assembly determinística basada en texto y metadata</li>
            <li>pueden consumir procesadores normativos</li>
            <li>no pasan por answer_* del chat</li>
          </ul>
        </article>
      </div>

      <div class="orch-warning-card">
        <strong>Regla de diseño:</strong>
        comparte retrieval y evidence cuando convenga; separa siempre la assembly visible por superficie.
      </div>
    </section>

    <section id="orch-tuning" class="orch-section">
      <div class="orch-section-header">
        <p class="orch-section-kicker">Tuning guide</p>
        <h2 class="orch-section-title">Si algo sale mal, toca la capa correcta</h2>
        <p class="orch-section-copy">
          Esta tabla existe para evitar regressions por tocar el módulo equivocado.
        </p>
      </div>
      <div class="orch-tuning-table">
        ${tuningRows.map(renderTuningRow).join("")}
      </div>
    </section>
  `;
}

function renderContractCard(card: ContractCard): string {
  return `
    <article class="orch-contract-card">
      <span class="orch-contract-producer">${card.producer}</span>
      <h3>${card.title}</h3>
      <p class="orch-contract-chain">${card.contract} <span>→</span> ${card.consumer}</p>
      <span class="orch-scope-pill">${card.scope}</span>
      <ul>
        ${card.bullets.map((bullet) => `<li>${bullet}</li>`).join("")}
      </ul>
    </article>
  `;
}

function renderLaneCard(card: LaneCard): string {
  return `
    <article class="orch-lane-card" id="${card.id}">
      <div class="orch-lane-index">${card.number}</div>
      <div class="orch-lane-copy">
        <h3>${card.title}</h3>
        <p>${card.summary}</p>
        <ul>
          ${card.bullets.map((bullet) => `<li>${bullet}</li>`).join("")}
        </ul>
      </div>
    </article>
  `;
}

function renderModuleCard(card: ModuleCard): string {
  return `
    <article class="orch-module-card" data-scope="${card.scope}">
      <div class="orch-module-topline">
        <span class="orch-module-scope" data-scope-tone="${card.scope}">${formatScope(card.scope)}</span>
        <span class="orch-module-stability" data-stability="${card.stability}">${formatStability(card.stability)}</span>
      </div>
      <h3>${card.title}</h3>
      <p class="orch-module-path">${card.path}</p>
      <p class="orch-module-role">${card.role}</p>
      <dl class="orch-module-contract">
        <div>
          <dt>Consume</dt>
          <dd>${card.consumes}</dd>
        </div>
        <div>
          <dt>Produce</dt>
          <dd>${card.produces}</dd>
        </div>
      </dl>
      <ul class="orch-module-list">
        ${card.bullets.map((bullet) => `<li>${bullet}</li>`).join("")}
      </ul>
    </article>
  `;
}

function renderTuningRow(row: { symptom: string; edit: string; why: string }): string {
  return `
    <article class="orch-tuning-row">
      <div>
        <span class="orch-tuning-label">Síntoma</span>
        <p>${row.symptom}</p>
      </div>
      <div>
        <span class="orch-tuning-label">Edita</span>
        <p><code>${row.edit}</code></p>
      </div>
      <div>
        <span class="orch-tuning-label">Por qué</span>
        <p>${row.why}</p>
      </div>
    </article>
  `;
}

function formatScope(scope: ModuleCard["scope"]): string {
  if (scope === "shared") return "Compartido";
  if (scope === "main-chat") return "Main chat";
  if (scope === "normativa") return "Normativa";
  if (scope === "interpretacion") return "Interpretación";
  return "Ventanas lectoras";
}

function formatStability(stability: ModuleCard["stability"]): string {
  if (stability === "stable-facade") return "Facade estable";
  if (stability === "surface-seam") return "Surface seam";
  return "Implementación";
}
