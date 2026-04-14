import type { PipelineGraph, PipelineNode, PipelineEdge, PipelineLane } from "./types";

export const PIPELINE_VERSION = "2026-04-08";

const lanes: PipelineLane[] = [
  { id: "ingesta", label: "Ingesta", color: "var(--orch-lane-ingesta)", order: 0 },
  { id: "parsing", label: "Parsing y Etiquetado", color: "var(--orch-lane-parsing)", order: 1 },
  { id: "almacenamiento", label: "Almacenamiento", color: "var(--orch-lane-almacenamiento)", order: 2 },
  { id: "retrieval", label: "Retrieval (Pipeline C)", color: "var(--orch-lane-retrieval)", order: 3 },
  { id: "surfaces", label: "Superficies Secundarias", color: "var(--orch-lane-surfaces)", order: 4 },
  { id: "plataforma", label: "Plataforma (Auth + Admin)", color: "var(--orch-lane-plataforma)", order: 5 },
  { id: "mobile", label: "Mobile Shell", color: "var(--orch-lane-mobile)", order: 6 },
];

const nodes: PipelineNode[] = [
  // ── Lane 1: Ingesta ──────────────────────────────────────
  {
    id: "ingesta.knowledge_base",
    lane: "ingesta",
    kind: "store",
    title: "knowledge_base/",
    summary: "Repositorio de archivos fuente: normativa, doctrina, guias practicas.",
    actors: ["curator"],
    metrics: ["~2494 docs (WIP)", "md/json/pdf"],
    order: 0,
    detailHtml: `
      <p><strong>Estructura de directorios:</strong></p>
      <ul>
        <li><code>normativa/renta/corpus_legal/</code> — Estatuto Tributario, leyes, decretos</li>
        <li><code>normativa/renta/corpus_critico_p0/</code> — corpus critico prioritario</li>
        <li><code>doctrina/</code> — conceptos DIAN, oficios</li>
        <li><code>industry_guidance/</code> — interpretaciones profesionales</li>
        <li><code>practica/</code> — guias ERP, tutoriales, formularios</li>
      </ul>
      <p><strong>Formatos aceptados:</strong> Markdown (.md), JSON (.json), PDF, DOCX</p>
    `,
  },
  {
    id: "ingesta.manifest",
    lane: "ingesta",
    kind: "config",
    title: "manifest CSV",
    summary: "Registro editorial: vigencia, tema, tipo de documento, curation_status.",
    actors: ["curator"],
    metrics: ["4816 filas"],
    order: 1,
    detailHtml: `
      <p><strong>Campos clave del manifest:</strong></p>
      <ul>
        <li><code>relative_path</code> — ruta al archivo fuente</li>
        <li><code>vigencia</code> — vigente | derogada | proyecto | desconocida</li>
        <li><code>tema</code> / <code>subtema</code> — taxonomia tematica</li>
        <li><code>tipo_de_documento</code> — ley, decreto, concepto, guia, etc.</li>
        <li><code>curation_status</code> — raw | normalized_active | promoted_curated</li>
        <li><code>knowledge_class</code> — normative_base | interpretative_guidance | practica_erp</li>
      </ul>
      <p><code>_manifest_vigencia</code> registra el valor crudo del CSV; <code>vigencia</code> puede ser inferida.</p>
      <p><strong>Regla 2026-03-17:</strong> <code>practica_erp</code> ya no recibe anchors, <code>subtema</code> o <code>concept_tags</code> desde section maps o filenames; esa metadata sale del cuerpo normalizado y el gate vigente se lee como <code>ok=true</code> + <code>totals.blocking_issues=0</code>.</p>
    `,
  },
  {
    id: "ingesta.scan",
    lane: "ingesta",
    kind: "stage",
    title: "scan_documents()",
    summary: "Escanea knowledge_base/, enriquece con manifest, genera DocumentRecord.",
    actors: ["python"],
    metrics: ["~2617 docs"],
    order: 2,
    detailHtml: `
      <p><strong>Proceso:</strong></p>
      <ol>
        <li>Recorre <code>knowledge_base/</code> recursivamente</li>
        <li>Cruza con manifest CSV por <code>relative_path</code></li>
        <li>Excluye docs con <code>_manifest_vigencia</code> in {derogada, proyecto}</li>
        <li>Genera <code>DocumentRecord</code> con metadata completa</li>
        <li>Aplica <code>_infer_vigencia()</code> si no hay vigencia explicita</li>
      </ol>
      <p><strong>Archivo:</strong> <code>src/lia_contador/ingest.py</code></p>
    `,
  },
  {
    id: "ingesta.chunk",
    lane: "ingesta",
    kind: "stage",
    title: "chunk_document()",
    summary: "Divide cada documento en chunks semanticos con overlap.",
    actors: ["python"],
    metrics: ["~39439 chunks"],
    order: 3,
    detailHtml: `
      <p><strong>Estrategia de chunking:</strong></p>
      <ul>
        <li>Separacion por headers markdown (## / ###)</li>
        <li>Limite maximo por chunk (~2000 tokens)</li>
        <li>Overlap semantico entre chunks contiguos</li>
        <li>Preserva metadata del documento padre</li>
        <li>Genera <code>chunk_id</code> unico por chunk</li>
      </ul>
    `,
  },
  {
    id: "ingesta.jsonl",
    lane: "ingesta",
    kind: "store",
    title: "artifacts/*.jsonl",
    summary: "Indices JSONL locales: document_index.jsonl + document_chunk_index.jsonl.",
    actors: ["python"],
    metrics: ["2 archivos"],
    order: 4,
    detailHtml: `
      <p><strong>Archivos generados:</strong></p>
      <ul>
        <li><code>artifacts/document_index.jsonl</code> — un registro por documento</li>
        <li><code>artifacts/document_chunk_index.jsonl</code> — un registro por chunk</li>
      </ul>
      <p>Estos archivos son validos sin Supabase. Usados por <code>JSONLTestRetriever</code> en tests.</p>
    `,
  },
  {
    id: "ingesta.gui_session",
    lane: "ingesta",
    kind: "stage",
    title: "GUI: ingestion_runtime",
    summary: "Sesion de ingesta via UI: upload → extract → etl → write → batch gates → done.",
    actors: ["python"],
    metrics: ["heartbeat", "4 sub-stages"],
    order: 5,
    detailHtml: `
      <p><strong>Ciclo de vida por documento:</strong></p>
      <ol>
        <li><strong>extracting</strong> (15-45%) — extraccion de texto (.md, .pdf, .docx, .json)</li>
        <li><strong>etl</strong> (55%) — normalizacion, split en partes de 16K chars</li>
        <li><strong>writing</strong> (72-85%) — escribe raw + normalized, upsert manifest</li>
        <li><strong>done_pending_batch_gate</strong> (85%) — espera a que todo el lote termine</li>
      </ol>
      <p><strong>Batch gates</strong> (92%):</p>
      <ol>
        <li><code>validating</code> — validate_strict_fn() contra el corpus</li>
        <li><code>manifest</code> — _flip_manifest_rows_active()</li>
        <li><code>indexing</code> — build_index_fn() reconstruye indice global</li>
        <li><code>syncing</code> — _sync_incremental() sincroniza a WIP (best-effort)</li>
      </ol>
      <p><strong>WIP sync tracking:</strong> <code>wip_sync_status</code> registra el resultado: <code>success</code> o <code>skipped</code> (si WIP no disponible). Banner amarillo en Kanban cuando <code>skipped</code>.</p>
      <p><strong>Heartbeat:</strong> <code>heartbeat_at</code> + <code>gate_sub_stage</code> actualizados entre cada sub-stage. El frontend detecta stall si &gt;120s sin heartbeat.</p>
      <p><strong>Rollback:</strong> Si gates falla, revierte manifest y marca <code>needs_retry_batch_gate</code>.</p>
      <p><strong>Recuperacion WIP:</strong> Operaciones → "Sincronizar JSONL a WIP" (<code>POST /api/ops/corpus/sync-to-wip</code>) sincroniza el JSONL local sin reindex.</p>
    `,
  },
  {
    id: "ingesta.sync_supabase",
    lane: "ingesta",
    kind: "stage",
    title: "sync_to_supabase()",
    summary: "Upsert documentos + chunks + embeddings; activa la generacion solo tras verificacion correcta en Supabase.",
    actors: ["python", "sql"],
    metrics: ["verified gate"],
    order: 6,
    detailHtml: `
      <p><strong>Pipeline de sync:</strong></p>
      <ol>
        <li>Upsert documentos a tabla <code>documents</code></li>
        <li>Upsert chunks a tabla <code>document_chunks</code> (batch 100)</li>
        <li>FK constraint: chunks con doc_id huerfano son omitidos</li>
        <li>Auto-embed chunks nuevos (embedding null) si <code>GEMINI_API_KEY</code> esta configurado</li>
        <li>Null bytes (<code>\\x00</code>) eliminados antes de insert</li>
        <li>Solo despues de verificar counts/embeddings/FTS se marca la generacion activa en <code>corpus_generations</code></li>
        <li>El gate de reindex exige <code>practical_doc_anchor_audit.json</code> con <code>ok=true</code> y <code>totals.blocking_issues=0</code></li>
        <li>Si el target es <code>both</code>, la corrida tambien verifica paridad production/wip por <code>generation_digest</code></li>
      </ol>
      <p><strong>Archivo:</strong> <code>src/lia_contador/ingest.py :: sync_to_supabase()</code></p>
    `,
  },

  {
    id: "ingesta.promote",
    lane: "ingesta",
    kind: "stage",
    title: "cli promote",
    summary: "Promocion incremental WIP → Production: 8 fases con checkpoint, propaga knowledge_class_counts.",
    actors: ["python", "sql"],
    metrics: ["8 fases", "resumable"],
    order: 7,
    detailHtml: `
      <p><strong>Pipeline de promocion:</strong></p>
      <ol>
        <li><code>build_promotion_plan()</code> — compara WIP vs production, genera worklists</li>
        <li><strong>docs_stage_new</strong> — upsert docs nuevos (batch 100)</li>
        <li><strong>chunks_upsert</strong> — upsert chunks nuevos/cambiados</li>
        <li><strong>chunks_retag</strong> — retag generation_id en chunks sin cambios</li>
        <li><strong>chunks_delete</strong> — eliminar chunks huerfanos</li>
        <li><strong>docs_finalize</strong> — retag generation_id en docs restantes</li>
        <li><strong>docs_delete</strong> — eliminar docs huerfanos</li>
        <li><strong>embed_pending</strong> — embed chunks nuevos sin vector</li>
        <li><strong>activate_generation</strong> — activa generacion con <code>knowledge_class_counts</code></li>
      </ol>
      <p><strong>Resumabilidad:</strong> Cada fase emite checkpoint. Si se interrumpe, resume desde el ultimo completado.</p>
      <p><strong>CLI:</strong> <code>uv run python -m lia_contador.cli promote</code></p>
      <p><strong>Fix 2026-03-20:</strong> <code>knowledge_class_counts</code> ahora se lee de la generacion WIP y se propaga a production.</p>
    `,
  },

  {
    id: "ingesta.kanban_classify",
    lane: "ingesta",
    kind: "stage",
    title: "classify()",
    summary: "Clasificador de 3 niveles: keywords → LLM → manual. Threshold 0.95.",
    actors: ["python", "llm"],
    metrics: ["3 niveles", "0.95 threshold"],
    order: 8,
    detailHtml: `
      <p><strong>Cascada de clasificacion:</strong></p>
      <ol>
        <li><strong>N1 — Keywords + Filename</strong> (sin LLM):
          <ul>
            <li><code>detect_topic_from_text()</code> — reusa topic_router.py (16 dominios)</li>
            <li><code>_FILENAME_TYPE_PATTERNS</code> — regex sobre nombre de archivo</li>
            <li><code>combined_confidence = topic_confidence × type_confidence</code></li>
          </ul>
        </li>
        <li><strong>N2 — LLM fallback</strong> (si N1 &lt; 0.95):
          <ul>
            <li><code>generate_llm_strict()</code> para topic + type</li>
            <li>Fusion ponderada N1 + N2 (acuerdo amplifica confianza)</li>
          </ul>
        </li>
        <li><strong>N3 — Manual</strong>: si combined &lt; 0.95, <code>is_raw=true</code> → bloqueado hasta asignacion manual</li>
      </ol>
      <p><strong>Aliases:</strong> "normativa" → normative_base, "interpretacion" → interpretative_guidance, "practica" → practica_erp</p>
      <p><strong>Archivo:</strong> <code>src/lia_contador/ingestion_classifier.py</code></p>
    `,
  },
  {
    id: "ingesta.kanban_dedup",
    lane: "ingesta",
    kind: "stage",
    title: "dedup()",
    summary: "4 niveles: bounce exacto (sin disco), revision listener, delta aditivo H2, fallback manual.",
    actors: ["python", "sql"],
    metrics: ["4 niveles", "Jaccard 0.80"],
    order: 9,
    detailHtml: `
      <p><strong>Dedup inteligente de 4 niveles:</strong></p>
      <ol>
        <li><strong>Bounce exacto</strong>: SHA256 en <code>add_file()</code> &mdash; rebote sin escritura a disco. Pill: &ldquo;&#8617; Ya existe en el corpus&rdquo;.</li>
        <li><strong>Revision listener</strong>: filename versionado (<code>_v1&rarr;_v2</code>) o fechado (ISO, compacto, mes-nombre EN+ES). Detecta si es revisi&oacute;n m&aacute;s reciente.</li>
        <li><strong>Delta aditivo</strong>: diff por secciones H2 (Jaccard &ge; 0.80). Ingesta solo secciones nuevas/modificadas. Lineage: <code>derived_from_doc_id</code>.</li>
        <li><strong>Fallback manual</strong>: si Supabase no disponible o diff falla &rarr; panel Reemplazar / Agregar nuevo / Descartar.</li>
      </ol>
      <p><strong>Best-effort:</strong> Si Supabase no disponible, retorna no-duplicado.</p>
      <p><strong>Archivos:</strong> <code>ingestion_dedup.py</code>, <code>ingestion_diff.py</code></p>
    `,
  },
  {
    id: "ingesta.kanban_diff",
    lane: "ingesta",
    kind: "stage",
    title: "diff_sections()",
    summary: "Diff H2-level entre documento nuevo y existente. Produce delta aditivo o bounce.",
    actors: ["python"],
    metrics: ["Jaccard 0.80", "lineage"],
    order: 9.5,
    detailHtml: `
      <p><strong>Modulo:</strong> <code>src/lia_contador/ingestion_diff.py</code></p>
      <p><strong>Funciones:</strong></p>
      <ul>
        <li><code>extract_sections(text)</code> &rarr; lista de Section(heading, body, signature)</li>
        <li><code>diff_sections(new, existing, threshold=0.80)</code> &rarr; DiffResult</li>
        <li><code>build_delta_document(diff, ...)</code> &rarr; markdown parcial o None</li>
      </ul>
      <p><strong>Logica:</strong></p>
      <ul>
        <li>Jaccard &gt; 0.80 sobre tokens = seccion sin cambios &rarr; skip</li>
        <li>Mismo heading, Jaccard &lt; 0.80 = seccion modificada &rarr; incluir</li>
        <li>Sin heading match = seccion nueva &rarr; incluir</li>
        <li>Si todo coincide &rarr; bounce (no additive content)</li>
      </ul>
    `,
  },
  {
    id: "ingesta.kanban_worker",
    lane: "ingesta",
    kind: "stage",
    title: "worker_pipeline()",
    summary: "Pipeline de 8 etapas: dedup → classify → analysis → chunking → sync → embed → verify → complete.",
    actors: ["python", "sql", "embedding"],
    metrics: ["8 etapas", "max 5 concurrentes"],
    order: 10,
    detailHtml: `
      <p><strong>Etapas con progreso:</strong></p>
      <table class="orch-detail-table">
        <tr><td>dedup</td><td>3%</td><td>Verificar duplicados contra corpus</td></tr>
        <tr><td>classify</td><td>8%</td><td>Clasificar topic + type (cascada N1→N2→N3)</td></tr>
        <tr><td>analysis</td><td>18%</td><td>Extraer metadata, idioma, estructura</td></tr>
        <tr><td>chunking</td><td>38%</td><td>Split 200-2000 chars, asignar chunk_id</td></tr>
        <tr><td>sync</td><td>62%</td><td>Upsert doc + chunks a Supabase</td></tr>
        <tr><td>embed</td><td>88%</td><td>Embeddings gemini-embedding-001 (768d)</td></tr>
        <tr><td>verify</td><td>96%</td><td>Validar integridad en Supabase</td></tr>
        <tr><td>complete</td><td>100%</td><td>Documento listo para retrieval</td></tr>
      </table>
      <p><strong>Cola:</strong> FIFO, max 5 workers concurrentes, docs <code>is_raw=true</code> bloqueados.</p>
      <p><strong>Archivos:</strong> <code>src/lia_contador/ingestion_worker.py</code>, <code>src/lia_contador/ingestion_queue.py</code></p>
    `,
  },

  // ── Lane 2: Parsing y Etiquetado ─────────────────────────
  {
    id: "parsing.extract",
    lane: "parsing",
    kind: "stage",
    title: "extract_text()",
    summary: "Extrae texto crudo del archivo fuente (md, json, pdf, docx).",
    actors: ["python"],
    order: 0,
    detailHtml: `
      <p>Detecta formato por extension y aplica extractor correspondiente. Markdown se procesa directamente; PDF y DOCX usan librerias especializadas.</p>
    `,
  },
  {
    id: "parsing.metadata",
    lane: "parsing",
    kind: "stage",
    title: "metadata_enrichment()",
    summary: "Genera tags taxonomicos: knowledge_class, trust_tier, concept_tags, normative_refs.",
    actors: ["python"],
    order: 1,
    detailHtml: `
      <p><strong>Tags generados:</strong></p>
      <table class="orch-detail-table">
        <tr><td><code>knowledge_class</code></td><td>normative_base | interpretative_guidance | practica_erp</td></tr>
        <tr><td><code>trust_tier</code></td><td>high | medium | low</td></tr>
        <tr><td><code>source_origin</code></td><td>official_registry | curated_public | user_upload | internal_template</td></tr>
        <tr><td><code>curation_status</code></td><td>raw | normalized_active | promoted_curated</td></tr>
        <tr><td><code>vigencia</code></td><td>vigente | derogada | proyecto | desconocida</td></tr>
        <tr><td><code>concept_tags</code></td><td>["ingreso", "fuente_nacional", ...]</td></tr>
        <tr><td><code>normative_refs</code></td><td>["et_art_26", "decreto:2229:2023"]</td></tr>
        <tr><td><code>mentioned_reference_keys</code></td><td>["formulario:110", "ley:2277:2022"]</td></tr>
      </table>
      <p>Tambien: <code>tema</code>, <code>subtema</code>, <code>tipo_de_documento</code>, <code>tipo_de_consulta</code>, <code>tipo_de_accion</code>, <code>tipo_de_riesgo</code>, <code>nivel_practicidad</code></p>
      <p><strong>Practicos:</strong> <code>reference_identity_keys</code> queda vacio salvo que el artefacto sea canonico/companion real.</p>
      <p><strong>Etiquetas de citacion:</strong> modelo de proveniencia por <code>knowledge_class</code> configurado en <code>config/display_labels.json</code> (white-label safe): normativa → autoridad real, interpretacion → proveedor, practica → prefijo configurable sin marca (default "Perspectiva para tu consideración").</p>
    `,
  },
  {
    id: "parsing.quality",
    lane: "parsing",
    kind: "stage",
    title: "quality_gate()",
    summary: "Valida minimos: summary >= 50 chars, curation_status != raw (con fallback).",
    actors: ["python"],
    order: 2,
    detailHtml: `
      <p><strong>Criterios de calidad:</strong></p>
      <ul>
        <li>Summary minimo: 50 caracteres</li>
        <li><code>curation_status == "raw"</code> excluido con fallback</li>
        <li><code>pending_validation</code> ya NO forza <code>trust_tier=low</code></li>
        <li>Solo <code>curation_status=="raw"</code> forza trust_tier=low</li>
      </ul>
    `,
  },
  {
    id: "parsing.taxonomy",
    lane: "parsing",
    kind: "stage",
    title: "taxonomy_tags()",
    summary: "Asigna tema, subtema, tipo_de_documento desde manifest y heuristicas.",
    actors: ["python"],
    order: 3,
  },
  {
    id: "parsing.embed",
    lane: "parsing",
    kind: "stage",
    title: "embed_chunks()",
    summary: "Genera embeddings con gemini-embedding-001 (768 dims) via API nativa Gemini.",
    actors: ["python", "embedding"],
    metrics: ["768 dims", "~39439 chunks"],
    order: 4,
    detailHtml: `
      <p><strong>Modelo:</strong> <code>gemini-embedding-001</code> via API nativa Gemini (<code>embedContent</code>/<code>batchEmbedContents</code>)</p>
      <p><strong>NO</strong> usa endpoint OpenAI-compat (no soporta embeddings).</p>
      <ul>
        <li>Dimensiones: 768 (con <code>outputDimensionality</code>)</li>
        <li>Config: <code>config/embedding.json</code></li>
        <li>Script: <code>scripts/embed_chunks.py</code> — idempotente, ~677s para 24920 chunks</li>
        <li>Modulo: <code>src/lia_contador/embeddings.py</code> — urllib.request (sin SDK), LRU-cached</li>
      </ul>
    `,
  },

  // ── Lane 3: Almacenamiento ───────────────────────────────
  {
    id: "almacenamiento.editorial",
    lane: "almacenamiento",
    kind: "stage",
    title: "editorial_review()",
    summary: "Curador revisa y promueve documentos: raw → normalized → promoted.",
    actors: ["curator"],
    order: 0,
    detailHtml: `
      <p><strong>Flujo editorial:</strong></p>
      <ol>
        <li><code>raw</code> — recien ingestado, sin revision</li>
        <li><code>normalized_active</code> — normalizado, activo para retrieval</li>
        <li><code>promoted_curated</code> — curado, maxima confianza</li>
      </ol>
      <p>La promocion se registra en el manifest CSV y se propaga en la siguiente ingesta.</p>
    `,
  },
  {
    id: "almacenamiento.supabase",
    lane: "almacenamiento",
    kind: "store",
    title: "Supabase (PostgreSQL)",
    summary: "Base de datos principal y runtime state: corpus, sesiones, metrics, telemetry y settings de Pipeline C.",
    actors: ["sql"],
    metrics: ["~37150 chunks (WIP)", "~2494 docs (WIP)"],
    order: 1,
    detailHtml: `
      <p><strong>Tablas principales:</strong></p>
      <ul>
        <li><code>documents</code> — registro por documento con metadata completa</li>
        <li><code>document_chunks</code> — chunks con <code>chunk_text</code>, <code>embedding vector(768)</code>, metadata</li>
        <li><code>corpus_generations</code> — generacion activa, files publicados y conteos por knowledge_class</li>
        <li><code>retrieval_events</code> — telemetria de cada retrieval</li>
        <li><code>conversations</code>, <code>feedback</code>, <code>clarification_sessions</code> — persistencia conversacional</li>
        <li><code>orchestration_settings</code>, <code>terms_acceptance_state</code> — runtime config y compliance state</li>
        <li><code>chat_session_metrics</code>, <code>citation_gap_registry</code>, <code>pipeline_c_runs</code> — observabilidad operativa</li>
      </ul>
      <p><strong>Indices:</strong> HNSW en vector(768), tsvector trigger (spanish), unique en doc_id</p>
      <p><strong>PostgREST timeout:</strong> 15s (migracion 000014) — default 3s era insuficiente para 34K+ chunks</p>
      <p><strong>Estado auditado:</strong> generacion WIP <code>20260320T160626…1288284b</code>, production <code>20260320T142153…40fd05ab</code>, <code>32</code> migraciones presentes y paridad production/wip exigida por <code>generation_digest</code> cuando el target de sync es <code>both</code>.</p>
    `,
  },
  {
    id: "almacenamiento.generations",
    lane: "almacenamiento",
    kind: "store",
    title: "corpus_generations",
    summary: "Registro activo del corpus: generation_id, files, counts y activation gate usados por Pipeline C.",
    actors: ["sql"],
    metrics: ["1 activa"],
    order: 2,
    detailHtml: `
      <p><strong>Rol:</strong> source of truth de la generacion activa cuando <code>LIA_STORAGE_BACKEND=supabase</code>.</p>
      <ul>
        <li><code>generation_id</code> — id activo del corpus</li>
        <li><code>documents</code> / <code>chunks</code> — conteos esperados para el gate de readiness</li>
        <li><code>files</code> — catalogo publicado de nombres de indice por capa/pais</li>
        <li><code>knowledge_class_counts</code> — conteos para surfaces admin/reindex</li>
        <li><code>is_active</code> — una sola generacion activa visible para Pipeline C</li>
      </ul>
      <p>Reemplaza el uso productivo de <code>artifacts/runtime/active_index_generation.json</code> como autoridad del runtime y evita split-brain entre artifact local y Supabase.</p>
      <p><strong>Snapshot vigente (WIP):</strong> <code>20260320T160626…1288284b</code> con <code>~2494</code> docs, <code>~37150</code> chunks, <code>~2230/~63/200</code> por capa (post-purge interpretativa 2026-03-20).</p>
    `,
  },
  {
    id: "almacenamiento.fts_rpc",
    lane: "almacenamiento",
    kind: "stage",
    title: "fts_scored_prefilter()",
    summary: "RPC: FTS pre-filter con OR-based scoring + hard SQL filters. ~200ms.",
    actors: ["sql"],
    metrics: ["~200ms", "~2190 candidatos"],
    order: 3,
    detailHtml: `
      <p><strong>Migracion:</strong> 000008</p>
      <p><strong>Logica:</strong></p>
      <ul>
        <li>OR-based FTS (full-text search con config <code>spanish</code>)</li>
        <li>Hard SQL filters: topic, pais, vigencia, visibility</li>
        <li>Tokens numericos de 1-2 digitos filtrados para evitar full-table scans</li>
        <li>Retorna ~2190 candidatos preordenados por relevancia FTS</li>
      </ul>
      <p><strong>Rendimiento:</strong> 214ms vs 9.4s del enfoque anterior (44x mejora)</p>
    `,
  },
  {
    id: "almacenamiento.hybrid_rpc",
    lane: "almacenamiento",
    kind: "stage",
    title: "hybrid_search()",
    summary: "RPC: busqueda hibrida FTS + vector via RRF fusion. 10 columnas metadata.",
    actors: ["sql", "embedding"],
    metrics: ["RRF k=60"],
    order: 4,
    detailHtml: `
      <p><strong>Migracion:</strong> 000007 (creacion), 000009 (metadata columns)</p>
      <p><strong>Fusion RRF:</strong> Reciprocal Rank Fusion con k=60 (configurable en <code>config/retrieval.yaml</code>)</p>
      <p><strong>Inputs:</strong> FTS scores + cosine similarity de embeddings</p>
      <p><strong>Metadata devuelta:</strong> relative_path, tema, subtema, tipo_de_documento, tipo_de_consulta, tipo_de_accion, tipo_de_riesgo, trust_tier, source_origin, nivel_practicidad</p>
    `,
  },

  // ── Lane 4: Retrieval (Pipeline C) ───────────────────────
  {
    id: "retrieval.supabase_gate",
    lane: "retrieval",
    kind: "stage",
    title: "supabase_gate()",
    summary: "Valida que Supabase este activo y corpus_generations tenga generacion activa.",
    actors: ["python", "sql"],
    order: -1,
    detailHtml: `
      <p>Pre-requisito obligatorio. Si Supabase no esta listo o no hay generacion activa, el pipeline aborta con <code>PC_SUPABASE_NOT_READY</code>.</p>
      <p><strong>Archivo:</strong> <code>src/lia_contador/pipeline_c/orchestrator.py</code></p>
      <p>Cuando el corpus se sincroniza a <code>both</code>, el gate no abre si production y wip no coinciden en digest.</p>
    `,
  },
  {
    id: "retrieval.api",
    lane: "retrieval",
    kind: "stage",
    title: "POST /api/chat",
    summary: "Entrypoint HTTP: batch (/api/chat) o streaming SSE (/api/chat/stream), con knobs publicos bubble-first.",
    actors: ["python"],
    metrics: ["timeout 25s", "3 knobs opt-in"],
    order: 0,
    detailHtml: `
      <p><strong>Entrypoints:</strong></p>
      <ul>
        <li><code>POST /api/chat</code> — respuesta batch completa</li>
        <li><code>POST /api/chat/stream</code> — SSE con <code>StructuredMarkdownStreamAssembler</code></li>
        <li><code>CLI: ask-pc</code> — interfaz de linea de comandos</li>
      </ul>
      <p><strong>Request:</strong> <code>PipelineCRequest</code> (contracts.py)</p>
      <p><strong>Knobs publicos opcionales:</strong> <code>retrieval_profile</code> (<code>baseline_keyword | hybrid_rerank | hybrid_semantic | advanced_corrective</code>), <code>response_depth</code> (<code>auto | concise | deep</code>) y <code>first_response_mode</code> (<code>fast_action | balanced_action</code>).</p>
      <p><strong>Routing tematico observable:</strong> <code>ui_chat_controller.py</code> + <code>topic_router.py</code> resuelven <code>requested_topic</code>, <code>effective_topic</code>, <code>secondary_topics</code>, <code>topic_adjusted</code> y <code>topic_notice</code>.</p>
      <p>El keyword matching usa word-boundary regex (<code>\\b</code>) para evitar falsos positivos donde keywords cortos aparecen dentro de palabras no relacionadas (e.g. <code>"arl"</code> en <code>"sumarle"</code>).</p>
      <p>Si el cliente omite <code>topic</code>, el contrato publico puede conservar <code>requested_topic=null</code> aunque internamente exista fallback a <code>declaracion_renta</code>.</p>
      <p><strong>Dedupe del turno:</strong> <code>build_chat_run_fingerprint()</code> ya incluye <code>session_id</code>, <code>client_turn_id</code>, <code>message</code>, <code>topic</code>, <code>pais</code>, <code>primary_scope_mode</code>, <code>response_route</code>, <code>retrieval_profile</code>, <code>response_depth</code>, <code>first_response_mode</code> y <code>engine_version</code>.</p>
      <p><strong>Metadata runtime observable:</strong> la respuesta publica preserva <code>llm_runtime.selected_transport</code>, <code>adapter_class</code>, <code>runtime_config_path</code> y <code>attempts</code>, permitiendo distinguir <code>Gemini Native</code> vs <code>OpenAI Wrapper</code> sin inspeccionar logs.</p>
      <p>Siempre incluye <code>trace_id</code>, <code>run_id</code>, telemetria y token usage en respuesta.</p>
    `,
  },
  {
    id: "retrieval.intake",
    lane: "retrieval",
    kind: "stage",
    title: "intake()",
    summary: "Clasifica risk_level, legal_depth, verifier_mode, cross-domain bridging (Layer 1+2).",
    actors: ["python"],
    order: 1,
    detailHtml: `
      <p><strong>Clasificaciones:</strong></p>
      <ul>
        <li><code>risk_level</code> — bajo, medio, alto, critico</li>
        <li><code>legal_depth</code> — superficial, intermedio, profundo</li>
        <li><code>verifier_mode</code> — determina si verify stage bloquea o advierte</li>
        <li><code>detected_secondary_topics</code> — topics secundarios (3 fuentes, merge):
          <ul>
            <li><strong>Layer 1</strong> — Keywords → <code>_CROSS_DOMAIN_RELATIONS</code> (15 relaciones viables: renta↔fe, renta→laboral, renta→niif, retencion→rst/laboral/fe, fe↔sancionatorio, iva→fe, exogena→fe/laboral, gmf→renta)</li>
            <li><strong>Layer 2</strong> — Norms → <code>legal_query_planner._QUERY_RULES</code> (19 reglas) → <code>resolve_secondary_topics_from_norms()</code> (resuelve complements via corpus index, filtro vigencia)</li>
            <li><strong>Layer 3</strong> — Thin-bundle broadening (reactivo, en retriever)</li>
          </ul>
        </li>
        <li><code>cross_domain_reason</code> — keyword y/o norm que disparo la deteccion</li>
      </ul>
      <p><strong>Etapa 1</strong> del pipeline estricto de 6 etapas.</p>
      <p><strong>Cross-domain bridging v1:</strong> Conecta ~27 silos tematicos del corpus colombiano. Layer 1 detecta conceptos modernos por keyword (DSNOF, nomina electronica, RST). Layer 2 detecta articulos antiguos del ET y resuelve puentes via complements normativos (ej: Art. 107 → factura electronica via Art. 617). 7 reglas latentes se activan cuando la ingesta agregue norm keys faltantes.</p>
    `,
  },
  {
    id: "retrieval.planner",
    lane: "retrieval",
    kind: "stage",
    title: "planner()",
    summary: "Decide top_k, cascade_mode y budgets adaptativos usando el turno actual, continuidad conversacional y retrieval_profile.",
    actors: ["python"],
    order: 2,
    detailHtml: `
      <p><strong>Decisiones:</strong></p>
      <ul>
        <li><code>retrieval_profile</code> — perfila el plan entre baseline keyword, hybrid y corrective</li>
        <li><code>top_k</code> — cuantos chunks recuperar</li>
        <li><code>cascade_mode</code> — practica_first_deferred_normative | all_layers | normativa_only</li>
        <li>Secuencia de tiers: practica → normativa_base → interpretativa</li>
        <li><code>secondary_top_k</code> — budget para topics secundarios (<code>max(5, top_k // 2)</code>)</li>
        <li><code>secondary_topics</code> — topics secundarios propagados desde intake</li>
        <li><code>conversation_state</code> — goal, normas ancladas, subpreguntas abiertas y carry-forward facts</li>
      </ul>
      <p>En follow-ups con continuidad fuerte, RAG8 puede subir budgets y mover el plan a <code>all_layers</code> para no perder cobertura en T2/T3.</p>
    `,
  },
  {
    id: "retrieval.cache",
    lane: "retrieval",
    kind: "stage",
    title: "semantic_cache()",
    summary: "Busca evidencia cacheada para query + plan similar; el fingerprint ahora incorpora continuidad cuando aplica.",
    actors: ["python"],
    order: 2.5,
    detailHtml: `
      <p><strong>Logica:</strong></p>
      <ul>
        <li>Busca en cache compartido por hash de query + plan</li>
        <li>RAG8 suma huella de continuidad cuando hay <code>conversation_state</code> o anchors previos</li>
        <li><strong>Cache hit:</strong> reutiliza EvidencePack previo, retrieval_duration=0</li>
        <li><strong>Cache miss:</strong> continua a retrieval, guarda resultado en cache</li>
      </ul>
      <p><strong>Archivo:</strong> <code>src/lia_contador/pipeline_c/orchestrator.py</code></p>
    `,
  },
  {
    id: "retrieval.retrieve",
    lane: "retrieval",
    kind: "stage",
    title: "retrieve()",
    summary: "Scoring hibrido 8-señales via Supabase, continuity lane por sesión y cobertura por subpregunta.",
    actors: ["python", "sql"],
    metrics: ["8 señales", "3 lanes"],
    order: 3,
    detailHtml: `
      <p><strong>Formula 8-señales</strong> (cuando <code>enable_embeddings="on"</code>):</p>
      <pre class="orch-detail-code">text_combined = trigram×0.35 + lexical×0.35 + embedding_sim×0.30</pre>
      <p><strong>Governance scoring:</strong></p>
      <pre class="orch-detail-code">base_credibility×0.55 + freshness×0.25 + utility_boost×0.10</pre>
      <p><strong>Trust tier multipliers:</strong></p>
      <ul>
        <li>high: ×1.00</li>
        <li>medium: ×0.82</li>
        <li>low: ×0.52</li>
      </ul>
      <p><strong>Calendar boost:</strong> +0.15 si query_nature="plazo" (0.08 tipo_doc + 0.04 subtema + 0.03 tags)</p>
      <p><strong>3 lanes:</strong> procedimiento, riesgo, alternativas (top-N=40 each)</p>
      <p><strong>Diversity cap:</strong> max 3 chunks por doc_id</p>
      <p><strong>Semantic equivalence:</strong> calendario/vencimiento/plazo expandidos</p>
      <p><strong>Time budget:</strong> 45s normal / 12s fast</p>
      <p><strong>Modulos canonicos:</strong></p>
      <ul>
        <li><code>pipeline_c/retriever.py</code> — orchestration (4A-4C, 4B½)</li>
        <li><code>pipeline_c/supabase_fetch.py</code> — SupabaseRetriever, FTS/hybrid RPCs</li>
        <li><code>pipeline_c/reranker.py</code> — python_rerank() (3-lane, 8-signal)</li>
        <li><code>pipeline_c/retrieval_scoring.py</code> — ~54 scoring functions</li>
        <li><code>pipeline_c/retrieval_diagnostics.py</code> — diagnostics + layer counts</li>
        <li><code>pipeline_c/norm_topic_index.py</code> — norm→topic cross-domain index</li>
      </ul>
      <p><strong>Telemetry:</strong> el stage persiste <code>selector_diagnostics</code> con <code>layer_mix</code>, per-index counts, fanout, quotas y score stats.</p>
      <p><strong>Topic diagnostics:</strong> <code>retrieval_diagnostics</code> conserva <code>primary_topic</code>, <code>requested_topic</code> y <code>topic_adjusted</code> para que el reroute quede observable.</p>
      <p><strong>Fases del retrieval:</strong></p>
      <ol>
        <li><strong>4A — Zero-results reformulation:</strong> Si vacio, expande query via <code>_SEMANTIC_EQUIVALENCE</code> y reintenta</li>
        <li><strong>4B — Query decomposition:</strong> Si multi-hop, split en sub-queries (max 4) con <code>context_anchor</code> derivado de <code>accountant_need</code> para preservar intento primario. Sub-retrieval usa <code>refined_query</code> original del planner. RAG8 también siembra decomposition desde <code>open_subquestions</code> cuando el follow-up es corto.</li>
        <li><strong>Continuity lane:</strong> reutiliza anchors previos y refs abiertas por <code>session_id</code> antes del broadening.</li>
        <li><strong>4B&frac12; — Thin-bundle broadening</strong> (reactivo): Si doc_count &lt; 5 y secondary_topics vacio, extrae normative_refs del bundle → <code>resolve_secondary_topics_from_norms()</code> → cap 1 topic. Previene explosion de retrieval. Solo dispara cuando intake norm+keyword fallaron.</li>
        <li><strong>4B→4C dedup:</strong> Si decomposition ejecutó, filtra secondary_topics que ya cubren sub-queries; capea <code>secondary_top_k</code> a 3 para evitar inundación de docs tangenciales.</li>
        <li><strong>4C — Cross-domain:</strong> Si <code>secondary_topics</code> tras dedup, fetch paralelo con ThreadPoolExecutor (max 3 workers). <code>topic_attribution</code> se usa downstream en compose para anotar docs secundarios con <code>[tema: X]</code>.</li>
      </ol>
      <p><strong>Diagnósticos RAG8:</strong> <code>continuity_hits</code> + <code>coverage_by_subquestion</code> via <code>selector_diagnostics</code>.</p>
      <p><strong>Cross-domain:</strong></p>
      <ul>
        <li>Budget secundario: <code>max(5, primary_top_k // 2)</code></li>
        <li>Merge: docs primarios conservan posicion; secundarios deduplicados por <code>chunk_id</code></li>
        <li><code>topic_attribution</code>: dict[str, list[str]] en EvidencePack</li>
      </ul>
    `,
  },
  {
    id: "retrieval.calibrate",
    lane: "retrieval",
    kind: "stage",
    title: "calibrate_confidence()",
    summary: "Gate pre-compose: evalua calidad de evidencia. Puede abortar sin llamar LLM.",
    actors: ["python"],
    order: 3.5,
    detailHtml: `
      <p><strong>Logica:</strong></p>
      <ul>
        <li>Evalua calidad y cobertura de la evidencia recuperada</li>
        <li><strong>should_abstain=true:</strong> Levanta <code>EvidenceInsufficientError</code> — no gasta tokens LLM</li>
        <li><strong>should_abstain=false:</strong> Continua a compose</li>
      </ul>
      <p><strong>Beneficio:</strong> Evita llamadas LLM costosas cuando la evidencia es claramente insuficiente.</p>
    `,
  },
  {
    id: "retrieval.compose",
    lane: "retrieval",
    kind: "model",
    title: "compose_answer()",
    summary: "Construye prompt y llama a Gemini 2.5-Flash (T=0.1, reasoning_effort=medium) via transporte resuelto por runtime config.",
    actors: ["python", "llm"],
    metrics: ["T=0.1", "single call"],
    order: 4,
    detailHtml: `
      <p><strong>Actor:</strong> Gemini 2.5-Flash (T=0.1, <code>reasoning_effort=medium</code>) — UNICO nodo con LLM en todo el pipeline.</p>
      <p><strong>Resolucion de runtime:</strong> <code>resolve_llm_adapter()</code> decide el adapter en tiempo de ejecucion. El stock actual del repo usa <code>GeminiChatAdapter</code> sobre la surface OpenAI-compatible, pero el mismo nodo soporta <code>GeminiNativeChatAdapter</code> si el runtime se configura con <code>transport=native</code> o si <code>LIA_LLM_RUNTIME_CONFIG_PATH</code> apunta a la variante native.</p>
      <p><strong>Controles visibles:</strong> <code>response_depth</code> ajusta la profundidad (<code>auto</code>, <code>concise</code>, <code>deep</code>) y <code>first_response_mode</code> sesga la apertura hacia accion rapida o balanceada sin cambiar el contrato base.</p>
      <p><strong>Secciones del prompt:</strong></p>
      <ol>
        <li><code>format_spec</code> — formato de salida esperado</li>
        <li><code>objective</code> — objetivo de la respuesta</li>
        <li><code>structure_hint</code> — estructura sugerida</li>
        <li><code>route_hint</code> — pista de ruta tematica</li>
        <li><code>grounding_rules</code> — reglas de anclaje en evidencia</li>
        <li><code>normative_accuracy</code> — reglas de precision normativa</li>
        <li><code>citations</code> — formato de citaciones (etiquetas por proveniencia via <code>config/display_labels.json</code>)</li>
        <li><code>evidence_snippets</code> — chunks agrupados por knowledge_class con headers neutros ("Evidencia normativa:", "Análisis interpretativo:", "Guías prácticas:"); docs de secondary topics anotados con <code>[tema: X]</code> para distinguir evidencia primaria de complementaria</li>
        <li><code>primary_intent_hint</code> — surfacea <code>accountant_need</code> como intento primario del contador</li>
        <li><code>normative_anchoring_hint</code> — ancla "Normativa relevante" al tema principal cuando hay secondary_topics</li>
        <li><code>coverage_obligations</code> — subpreguntas/obligaciones explícitas derivadas del turno actual</li>
      </ol>
      <p><strong>Retry:</strong> hasta 2 intentos, pero el segundo queda reservado a repair de cobertura o truncación real.</p>
      <p><strong>Quality scoring:</strong> continuidad + completitud + cobertura, ya no solo longitud/dígitos.</p>
      <p><strong>Reroute tematico:</strong> si <code>topic_adjusted=true</code>, el scoring interno favorece documentos cuyo <code>doc.topic</code> coincide con <code>primary_topic</code> y penaliza los no alineados.</p>
      <p><strong>Metadata emitida:</strong> el payload final devuelve <code>llm_runtime.selected_transport</code>, <code>llm_runtime.adapter_class</code>, <code>llm_runtime.runtime_config_path</code> y <code>llm_runtime.attempts</code>; la misma huella alimenta benchmarks bubble-first y long cognition.</p>
      <p><strong>Bubble-first pass 2026-04-04:</strong> el prompt activo endurece apertura accionable, normalizacion de headings y repair de cobertura antes de aceptar la respuesta final.</p>
      <p><strong>Adapter:</strong> <code>generate(prompt) → str</code> via <code>src/lia_contador/adapters/llm.py</code></p>
    `,
  },
  {
    id: "retrieval.verify",
    lane: "retrieval",
    kind: "stage",
    title: "verify()",
    summary: "Chequea respuesta contra evidencia. evidence_echo y entity_grounding endurecen el grounding.",
    actors: ["python"],
    order: 5,
    detailHtml: `
      <p><strong>Verificaciones:</strong></p>
      <ul>
        <li>Contraste respuesta vs chunks recuperados</li>
        <li>Puede bloquear respuestas si verificacion falla en strict mode</li>
        <li><code>evidence_echo</code> — deteccion deterministica de contradicciones numericas</li>
        <li><code>entity_grounding</code> — valida que las referencias normativas citadas aparezcan en la evidencia</li>
        <li><code>legal_coverage</code> — norma principal + complementarias (penalty only, no bloquea)</li>
      </ul>
      <p><strong>Blockers (strict):</strong> no_evidence, article_without_citation, strict_requires_normative, evidence_echo_contradiction, ungrounded_entities (ratio&lt;0.5), missing_vigencia, period_violation</p>
      <p><strong>Solo penalty:</strong> <code>missing_principal_norm</code>, <code>missing_required_complements</code> (0.08/complemento, max 0.20) — string-match demasiado fragil para bloquear</p>
      <p><strong>Archivo:</strong> <code>src/lia_contador/pipeline_c/verifier.py</code></p>
    `,
  },
  {
    id: "retrieval.safety",
    lane: "retrieval",
    kind: "stage",
    title: "safety()",
    summary: "Limpieza final, formateo pais-especifico (es-CO).",
    actors: ["python"],
    order: 6,
    detailHtml: `
      <p><strong>Acciones:</strong></p>
      <ul>
        <li>Limpieza de annotations internas (<code>strip_inline_evidence_annotations</code>)</li>
        <li>Formateo especifico Colombia (moneda, fechas, abreviaciones)</li>
        <li>Validacion final de estructura de respuesta</li>
      </ul>
    `,
  },
  {
    id: "retrieval.stream",
    lane: "retrieval",
    kind: "stage",
    title: "stream_sse()",
    summary: "SSE streaming con StructuredMarkdownStreamAssembler para output en tiempo real.",
    actors: ["python"],
    order: 7,
    detailHtml: `
      <p><strong>Clase:</strong> <code>StructuredMarkdownStreamAssembler</code></p>
      <p>Parsea bloques markdown en tiempo real durante el streaming SSE. Envia eventos parciales al frontend conforme llegan tokens del LLM.</p>
      <p><strong>Archivo:</strong> <code>src/lia_contador/pipeline_c/streaming.py</code></p>
    `,
  },

  // ── Lane 5: Superficies Secundarias ─────────────────────
  {
    id: "surfaces.expert_panel",
    lane: "surfaces",
    kind: "stage",
    title: "POST /api/expert-panel",
    summary: "Retrieval interpretativo + split por provider. La clasificacion es deterministica; el nutshell puede usar rescate LLM.",
    actors: ["python", "sql"],
    metrics: ["deterministico", "quality gate"],
    order: 0,
    detailHtml: `
      <p><strong>Modulos:</strong> <code>src/lia_contador/expert_summaries.py</code>, <code>src/lia_contador/expert_classification.py</code></p>
      <p><strong>Pipeline:</strong></p>
      <ol>
        <li>Recibe <code>message</code>, <code>normative_article_refs</code>, <code>assistant_answer</code></li>
        <li>Retrieval via <code>SupabaseRetriever</code> (capa <code>interpretative_guidance</code>)</li>
        <li>Split de chunks multi-provider en evidencias por seccion</li>
        <li>Crux extraction: valor agregado → como aplicar → enfoque distintivo</li>
        <li>Quality gate del nutshell y rescue LLM solo si el copy deterministico es pobre</li>
        <li>Persistencia de overrides por provider + source_hash</li>
      </ol>
      <p><strong>Respuesta:</strong> <code>groups[]</code> (ExpertGroup), <code>ungrouped[]</code> (ExpertSnippet), diagnostics</p>
      <p><strong>URLs de fuente (2026-03-20):</strong> Cada <code>ExpertSnippet</code> incluye <code>source_view_url</code>, <code>official_url</code> y <code>open_url</code>. El frontend renderiza "Ver en corpus" como fallback anchor.</p>
    `,
  },
  {
    id: "surfaces.expert_crux",
    lane: "surfaces",
    kind: "model",
    title: "split_expert_sections()",
    summary: "Genera evidencias por provider con crux-first summary, quality gate y overrides persistidos.",
    actors: ["python", "llm"],
    metrics: ["conditional LLM"],
    order: 1,
    detailHtml: `
      <p><strong>Funcion:</strong> <code>split_expert_sections()</code></p>
      <ul>
        <li>Divide un chunk en secciones por provider</li>
        <li>Extrae <code>card_summary</code> tipo nutshell sin titulo/autor/speaker</li>
        <li>Si el resumen es pobre, llama <code>generate_llm_strict()</code> como rescate</li>
        <li>Guarda overrides reutilizables en <code>expert_summary_overrides</code></li>
      </ul>
    `,
  },
  {
    id: "surfaces.expert_classify",
    lane: "surfaces",
    kind: "stage",
    title: "classify_expert_groups()",
    summary: "Clasificador deterministico: regex de posicion, pares opuestos, agrupacion por articulo y group summary crux-first.",
    actors: ["python"],
    order: 2,
    detailHtml: `
      <p><strong>Funcion:</strong> <code>classify_expert_groups()</code></p>
      <p><strong>Deteccion de posicion:</strong></p>
      <ul>
        <li>Prioridad: restringe &gt; condiciona &gt; permite &gt; neutral</li>
        <li>Deteccion via regex sobre texto del snippet</li>
        <li>Pares opuestos (permite vs restringe) generan señal de divergencia</li>
      </ul>
      <p><strong>Dataclasses:</strong> <code>ExpertSnippet</code>, <code>ExpertGroup</code></p>
      <p><strong>Agrupacion:</strong> por articulo normativo (e.g. "ET:art26")</p>
      <p><strong>Nota:</strong> El LLM no decide la clasificacion; solo puede rescatar el nutshell del grupo si el copy ensamblado es pobre.</p>
    `,
  },
  {
    id: "surfaces.citation_profile",
    lane: "surfaces",
    kind: "stage",
    title: "GET /api/citation-profile",
    summary: "Perfil normativo de una citacion. Renderizado en dos fases: instant + LLM. Tres paths por document_family: ET, Ley, Formulario.",
    actors: ["python", "sql", "llm"],
    metrics: ["2-phase render", "3 families"],
    order: 3,
    detailHtml: `
      <p><strong>Patron de renderizado multi-fase:</strong></p>
      <ol>
        <li><strong>Fase 1 — Instant</strong> (<code>?phase=instant</code>, ~200ms):
          <ul>
            <li>Titulo, binding_force, document_family — clasificacion deterministica</li>
            <li>Texto vigente del articulo — chunk del corpus en Supabase</li>
            <li>Vigencia, hechos editoriales — metadata del manifest/indice</li>
            <li>Comentario experto — grounded desde chunks</li>
            <li>Lead — fallback deterministico para ET articles</li>
            <li>Respuesta incluye <code>needs_llm: true|false</code></li>
          </ul>
        </li>
        <li><strong>Fase 2 — LLM</strong> (<code>?phase=llm</code>, ~2-5s):
          <ul>
            <li>Lead enriquecido — contextual a la pregunta del usuario</li>
            <li>Hechos editoriales enriquecidos — purpose_text, mandatory_when</li>
            <li>Seccion "Impacto para la profesion contable" — professional_impact</li>
          </ul>
        </li>
      </ol>
      <p><strong>Renderizado por familia (document_family):</strong></p>
      <table class="orch-detail-table">
        <tr><th>Aspecto</th><th>ET Article (<code>et_dur</code>)</th><th>Ley (<code>ley</code>)</th><th>Formulario</th></tr>
        <tr><td>doc_id pattern</td><td><code>renta_corpus_a_et_art_*</code></td><td><code>co_ley_NUMBER_YEAR</code></td><td><code>formulario:*</code></td></tr>
        <tr><td>Original text</td><td>Blockquote central</td><td>No</td><td>No</td></tr>
        <tr><td>Lead</td><td>Integrado en seccion</td><td>Separado (topbar)</td><td>N/A</td></tr>
        <tr><td>Analisis profundo</td><td>Oculto</td><td>Visible</td><td>Oculto</td></tr>
        <tr><td>Checkmark</td><td>No</td><td>Si</td><td>No</td></tr>
        <tr><td>Fase LLM</td><td>Si</td><td>Si</td><td>No (deterministico)</td></tr>
        <tr><td>Article picker</td><td>Si (rangos)</td><td>No</td><td>No</td></tr>
      </table>
      <p><strong>Cross-type guard (frontend):</strong> <code>buildCitationProfileParams()</code> detecta si un doc_id ET tiene un source_label de Ley ("Frankenstein citation") y envia <code>reference_key=ley:NUMBER:YEAR</code> en vez del doc_id incorrecto. Tres capas de deteccion: reference_key regex, doc_id regex, label regex.</p>
      <p><strong>Cross-type guard (backend):</strong> <code>_is_cross_type_mention_mismatch()</code> previene que menciones <code>ley:</code> se resuelvan contra docs ET, y viceversa. Opera en loops de enriquecimiento y resolucion.</p>
      <p><strong>Title parsing:</strong> Ley check ANTES de ET parse en <code>formatNormativeCitationTitle()</code> — previene que "Ley 2277 de 2022" sea consumido como articulo ET "2277".</p>
      <p><strong>Reference resolution (backend):</strong></p>
      <ul>
        <li><code>reference_key="ley:2277:2022"</code> → <code>doc_id = "co_ley_2277_2022"</code></li>
        <li><code>reference_key="et" + locator_start="720"</code> → <code>doc_id = "renta_corpus_a_et_art_720"</code></li>
      </ul>
      <p><strong>Concordancias collapse (2026-04-01):</strong> Secciones de concordancias colapsadas por defecto; secciones de profundidad (depth) renderizadas separadamente para mejorar legibilidad.</p>
      <p><strong>Normograma URLs (2026-04-01):</strong> Resoluciones DIAN usan zero-padding de 4 digitos (ej: <code>0042</code>). Links externos resueltos para menciones bare de resolucion/concepto.</p>
    `,
  },
  {
    id: "surfaces.citation_interp",
    lane: "surfaces",
    kind: "stage",
    title: "POST /api/citation-interpretations",
    summary: "Recupera documentos de interpretacion profesional relevantes a una citacion normativa.",
    actors: ["python", "sql"],
    order: 4,
    detailHtml: `
      <p><strong>Pipeline:</strong></p>
      <ol>
        <li>Recibe <code>citation.doc_id</code> + <code>message_context</code></li>
        <li>Construye query seed desde contexto de citacion</li>
        <li>Retrieval via <code>SupabaseRetriever</code> (filtro <code>interpretative_guidance</code>)</li>
        <li>Deduplicacion de documentos (<code>_dedupe_interpretation_docs()</code>)</li>
        <li>Enriquecimiento: providers, enlaces, card summaries, snippets</li>
      </ol>
      <p><strong>Respuesta:</strong> <code>cards[]</code> con relevance_score, provider_links, snippet, card_summary</p>
    `,
  },
  {
    id: "surfaces.interp_summary",
    lane: "surfaces",
    kind: "model",
    title: "POST /api/interpretation-summary",
    summary: "Resume una interpretacion seleccionada en contexto de la citacion original. Usa LLM.",
    actors: ["python", "llm"],
    metrics: ["LLM call"],
    order: 5,
    detailHtml: `
      <p><strong>Pipeline:</strong></p>
      <ol>
        <li>Carga texto del corpus de la interpretacion seleccionada</li>
        <li>Construye prompt con contexto de citacion normativa</li>
        <li>Llamada LLM via <code>generate_llm_strict()</code></li>
        <li>Respuesta JSON estructurada: summary, metadata, citations</li>
      </ol>
      <p><strong>Nota:</strong> Segundo nodo LLM del sistema (ademas de <code>compose_answer()</code> en Pipeline C).</p>
    `,
  },
  {
    id: "surfaces.normative_support",
    lane: "surfaces",
    kind: "stage",
    title: "POST /api/normative-support",
    summary: "Endpoint de citas rapido sin LLM. Devuelve solo citaciones normativas relevantes.",
    actors: ["python", "sql"],
    order: 6,
    detailHtml: `
      <p><strong>Caracteristica:</strong> Sin llamada LLM — solo retrieval y citas.</p>
      <p>Util para obtener base legal sin coste de generacion.</p>
    `,
  },
  {
    id: "surfaces.form_guide_chat",
    lane: "surfaces",
    kind: "model",
    title: "POST /api/form-guides/chat",
    summary: "Chat contextual por campo de formulario. Usa LLM con contexto del hotspot especifico.",
    actors: ["python", "llm"],
    metrics: ["LLM call"],
    order: 7,
    detailHtml: `
      <p><strong>Input:</strong> <code>guide_key</code> + <code>field_key</code> + <code>message</code></p>
      <p>Carga contexto del formulario y hotspot, construye prompt especializado, llama LLM.</p>
    `,
  },
  {
    id: "surfaces.ingestion_ctrl",
    lane: "surfaces",
    kind: "stage",
    title: "Ingestion Controls",
    summary: "Endpoints de control de sesiones de ingesta: stop, clear, retry, delete-failed, delete session.",
    actors: ["python"],
    order: 8,
    detailHtml: `
      <p><strong>Endpoints:</strong></p>
      <ul>
        <li><code>POST /api/ingestion/sessions/{id}/stop</code> — detiene batch activo</li>
        <li><code>POST /api/ingestion/sessions/{id}/clear</code> — limpia items fallidos</li>
        <li><code>POST /api/ingestion/sessions/{id}/delete-failed</code> — elimina todos los fallidos</li>
        <li><code>DELETE /api/ingestion/sessions/{id}</code> — elimina sesion completa</li>
        <li><code>POST /api/ingestion/classify</code> — clasifica documento con cascada N1+N2</li>
        <li><code>POST /api/ingestion/resolve-duplicate</code> — acepta/rechaza near-duplicate</li>
        <li><code>POST /api/ingestion/auto-process</code> — arranca procesamiento automatico</li>
        <li><code>POST /api/ingestion/manual-classify</code> — asigna topic+type manualmente</li>
      </ul>
      <p><strong>Runtime:</strong> <code>INGESTION_RUNTIME</code> en <code>src/lia_contador/ingestion_runtime.py</code></p>
    `,
  },

  // ── Lane 6: Plataforma (Auth + Admin) ──────────────────────
  {
    id: "plataforma.auth",
    lane: "plataforma",
    kind: "stage",
    title: "platform_auth.py",
    summary: "JWT signing canonico: issue_access_token() como unico punto de emision (login, invite, embed).",
    actors: ["python"],
    metrics: ["HS256", "canonical"],
    order: 0,
    detailHtml: `
      <p><strong>Responsabilidades:</strong></p>
      <ul>
        <li><code>issue_access_token()</code> — unico punto de emision de JWTs</li>
        <li>Validacion de grants firmados del host (embed exchange)</li>
        <li>Claims: tenant_id, user_id, role, company_ids</li>
        <li>Firma con <code>LIA_PLATFORM_SIGNING_SECRET</code> (HS256)</li>
      </ul>
      <p><strong>Unificacion (2026-03-25):</strong> Login, invite-accept y embed exchange ahora usan <code>issue_access_token()</code> como unico punto de firma. Elimina duplicacion que causaba fragilidad cross-environment.</p>
    `,
  },
  {
    id: "plataforma.security",
    lane: "plataforma",
    kind: "stage",
    title: "Security Layer",
    summary: "Headers, rate limiting, body limits, CORS, suspended user enforcement.",
    actors: ["python"],
    metrics: ["token-bucket", "1MB limit"],
    order: 1,
    detailHtml: `
      <p><strong>Capas de seguridad (orden de ejecucion):</strong></p>
      <ol>
        <li><strong>Security headers</strong>: nosniff, X-Frame-Options DENY, HSTS (prod/staging)</li>
        <li><strong>JWT validation</strong>: bearer token → AuthContext</li>
        <li><strong>Suspended check</strong>: cache 60s TTL → 403</li>
        <li><strong>Rate limiting</strong>: token-bucket (auth 10/min, chat 30/min, invite 10/min) → 429</li>
        <li><strong>Body size limit</strong>: 1MB → 413</li>
      </ol>
      <p><strong>CORS</strong>: whitelist-only en produccion (localhost solo en dev)</p>
      <p><strong>Archivo:</strong> <code>src/lia_contador/rate_limiter.py</code>, <code>ui_server.py</code></p>
    `,
  },
  {
    id: "plataforma.user_mgmt",
    lane: "plataforma",
    kind: "stage",
    title: "User Management",
    summary: "Invite-link login, tenant CRUD, suspend/reactivate/delete.",
    actors: ["python", "sql"],
    metrics: ["10 endpoints"],
    order: 2,
    detailHtml: `
      <p><strong>Flujo de invitacion:</strong></p>
      <ol>
        <li>Admin: <code>POST /api/admin/users/invite</code> → genera token + URL</li>
        <li>Usuario: <code>GET /invite?token=...</code> → pagina HTML</li>
        <li>Acepta: <code>POST /api/invite/accept</code> → crea usuario + JWT</li>
      </ol>
      <p><strong>Gestion:</strong></p>
      <ul>
        <li><code>GET /api/admin/users</code>, <code>GET /api/admin/tenants</code></li>
        <li><code>POST /api/admin/users/{id}/suspend|reactivate|delete</code></li>
        <li><code>POST /api/admin/tenants</code></li>
      </ul>
      <p><strong>Store:</strong> <code>src/lia_contador/user_management.py</code></p>
      <p><strong>Controllers:</strong> <code>src/lia_contador/ui_user_management_controllers.py</code></p>
      <p><strong>Migracion:</strong> <code>20260324000001_admin_invite_tokens.sql</code></p>
    `,
  },
  {
    id: "plataforma.auth_frontend",
    lane: "plataforma",
    kind: "stage",
    title: "Auth Frontend",
    summary: "JWT en localStorage, authGate, tab filtering por rol.",
    actors: ["typescript"],
    metrics: ["localStorage"],
    order: 3,
    detailHtml: `
      <p><strong>Modulos:</strong></p>
      <ul>
        <li><code>authContext.ts</code> — decodifica JWT de localStorage → {tenantId, userId, role, companyId}. Migracion automatica desde sessionStorage on-load</li>
        <li><code>authGate.ts</code> — wrapper de ruta protegida, redirige a login si no hay token</li>
        <li><code>tabAccess.ts</code> — filtra tabs visibles por rol (tenant_user solo ve user tabs)</li>
      </ul>
      <p><strong>Token key:</strong> <code>lia_platform_access_token</code> en localStorage</p>
      <p><strong>Migracion (2026-03-25):</strong> Token movido de sessionStorage a localStorage para persistencia cross-tab.</p>
    `,
  },
  {
    id: "plataforma.rls",
    lane: "plataforma",
    kind: "config",
    title: "RLS Policies",
    summary: "Row-Level Security en 9 tablas tenant-scoped. Service role bypasses RLS.",
    actors: ["sql"],
    metrics: ["9 tablas"],
    order: 4,
    detailHtml: `
      <p><strong>Tablas protegidas:</strong></p>
      <ul>
        <li>conversations, conversation_turns</li>
        <li>feedback, usage_events, usage_rollups_daily, usage_rollups_monthly</li>
        <li>chat_runs, jobs, contributions</li>
      </ul>
      <p><strong>Helper:</strong> <code>requesting_tenant_id()</code> extrae tenant_id del JWT</p>
      <p><strong>Bypass:</strong> service_role salta RLS (backend admin)</p>
      <p><strong>Migracion:</strong> <code>20260322000001_rls_tenant_isolation.sql</code></p>
    `,
  },

  // ── Lane 7: Mobile Shell ─────────────────────────────────
  {
    id: "mobile.detect",
    lane: "mobile",
    kind: "stage",
    title: "detectMobile()",
    summary: "Deteccion por UA pattern + viewport <768px al bootstrap.",
    actors: ["python"],
    metrics: ["UA + viewport"],
    order: 0,
    detailHtml: `
      <p><strong>Heuristicas:</strong></p>
      <ul>
        <li>UA pattern: <code>Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini</code></li>
        <li>Viewport: <code>window.innerWidth &lt; 768</code></li>
        <li>Retorna <code>true</code> si <strong>cualquiera</strong> matchea</li>
      </ul>
      <p><strong>Archivo:</strong> <code>frontend/src/app/mobile/detectMobile.ts</code></p>
    `,
  },
  {
    id: "mobile.shell",
    lane: "mobile",
    kind: "stage",
    title: "shell-mobile.ts",
    summary: "Template HTML del shell movil: topbar, viewport, tabs, drawer, sheet.",
    actors: ["python"],
    metrics: ["4 paneles", "3 tabs"],
    order: 1,
    detailHtml: `
      <p><strong>Estructura:</strong></p>
      <ul>
        <li><strong>Topbar</strong> (48px): logo + tagline i18n (#E8611A) + hamburguesa</li>
        <li><strong>Viewport</strong>: 4 paneles absolutos (chat, normativa, interp, historial)</li>
        <li><strong>Tab bar</strong> (56px): Chat | Normativa | Interpretación (con badges)</li>
        <li><strong>Drawer</strong>: slide-from-right, user info, nav, logout</li>
        <li><strong>Sheet</strong>: bottom sheet overlay (85dvh, swipe-to-dismiss)</li>
      </ul>
      <p>Embebe el shell desktop completo en <code>#mobile-panel-chat</code>; CSS oculta chrome desktop.</p>
    `,
  },
  {
    id: "mobile.adapter",
    lane: "mobile",
    kind: "stage",
    title: "mobileChatAdapter",
    summary: "Bridge por eventos UI tipados: view models desktop compartidos → mobile + badges.",
    actors: ["python"],
    metrics: ["2 eventos UI"],
    order: 2,
    detailHtml: `
      <p><strong>Eventos escuchados:</strong></p>
      <ul>
        <li><strong>Citations</strong>: escucha <code>lia:citations-updated</code> → aplana grupos compartidos → renderiza tarjetas en normativa + actualiza badge</li>
        <li><strong>Expert</strong>: escucha <code>lia:experts-updated</code> → recibe cards compartidas → renderiza interp panel + actualiza badge</li>
      </ul>
      <p><strong>Reset:</strong> al enviar nuevo query, limpia paneles y resetea badges.</p>
      <p><strong>Archivo:</strong> <code>frontend/src/app/mobile/mobileChatAdapter.ts</code></p>
    `,
  },
  {
    id: "mobile.normativa",
    lane: "mobile",
    kind: "stage",
    title: "mobileNormativaPanel",
    summary: "Tarjetas de citas normativas con bottom sheet de detalle.",
    actors: ["python"],
    order: 3,
    detailHtml: `
      <p>Click en tarjeta → trigger modal desktop → lectura → contenido al bottom sheet.</p>
      <p>Incluye: fuerza de vinculacion, extracto, datos clave, secciones, CTAs.</p>
    `,
  },
  {
    id: "mobile.interp",
    lane: "mobile",
    kind: "stage",
    title: "mobileInterpPanel",
    summary: "Interpretaciones agrupadas por clasificacion con bottom sheet de detalle.",
    actors: ["python"],
    order: 4,
    detailHtml: `
      <p><strong>Agrupacion:</strong> concordancia → complementario → divergencia → individual</p>
      <p><strong>Señales:</strong> permite (✅), restringe (⛔), condiciona (⚠️)</p>
    `,
  },
  {
    id: "mobile.historial",
    lane: "mobile",
    kind: "stage",
    title: "mobileHistorial",
    summary: "Historial full-screen con busqueda, filtros por tema, caching inteligente.",
    actors: ["python"],
    metrics: ["PAGE_SIZE=50"],
    order: 5,
    detailHtml: `
      <p><strong>Features:</strong></p>
      <ul>
        <li>Topic pills: Todos, Renta, IVA, Laboral, ICA, NIIF, Facturación, Exógena, Calendario</li>
        <li>Busqueda debounced (250ms) sobre <code>first_question</code></li>
        <li>Agrupacion por fecha: Hoy, Ayer, Esta semana, Mes+Año</li>
        <li>Paginacion con "Cargar más"</li>
      </ul>
      <p><strong>Caching:</strong> primer acceso → loader googly-eyes + fetch; re-opens renderizan cache instantaneamente + refresh background.</p>
    `,
  },
];

const edges: PipelineEdge[] = [
  // Ingesta flow (CLI/build_index path)
  { from: "ingesta.knowledge_base", to: "ingesta.manifest", label: "editorial" },
  { from: "ingesta.knowledge_base", to: "ingesta.scan" },
  { from: "ingesta.manifest", to: "ingesta.scan", label: "metadata" },
  { from: "ingesta.scan", to: "ingesta.chunk" },
  { from: "ingesta.chunk", to: "ingesta.jsonl" },
  { from: "ingesta.jsonl", to: "ingesta.sync_supabase" },

  { from: "ingesta.sync_supabase", to: "ingesta.promote", label: "WIP validated" },

  // Ingesta flow (GUI session path)
  { from: "ingesta.gui_session", to: "ingesta.knowledge_base", label: "raw + normalized" },
  { from: "ingesta.gui_session", to: "ingesta.manifest", label: "upsert rows" },
  { from: "ingesta.gui_session", to: "ingesta.jsonl", label: "batch gates → reindex" },

  // Ingesta flow (Kanban worker path)
  { from: "ingesta.kanban_dedup", to: "ingesta.kanban_classify", label: "no duplicate" },
  { from: "ingesta.kanban_dedup", to: "ingesta.kanban_diff", label: "near-dup / revision" },
  { from: "ingesta.kanban_diff", to: "ingesta.kanban_classify", label: "delta doc" },
  { from: "ingesta.kanban_classify", to: "ingesta.kanban_worker", label: "conf ≥ 0.95" },
  { from: "ingesta.kanban_worker", to: "almacenamiento.supabase", crossLane: true, label: "sync + embed" },
  { from: "ingesta.gui_session", to: "ingesta.kanban_dedup", label: "auto-process" },

  // Parsing flow
  { from: "parsing.extract", to: "parsing.metadata" },
  { from: "parsing.metadata", to: "parsing.quality" },
  { from: "parsing.quality", to: "parsing.taxonomy" },
  { from: "parsing.taxonomy", to: "parsing.embed" },

  // Almacenamiento flow
  { from: "almacenamiento.editorial", to: "almacenamiento.supabase" },
  { from: "almacenamiento.supabase", to: "almacenamiento.generations" },
  { from: "almacenamiento.supabase", to: "almacenamiento.fts_rpc" },
  { from: "almacenamiento.supabase", to: "almacenamiento.hybrid_rpc" },

  // Retrieval (Pipeline C) flow
  { from: "retrieval.api", to: "retrieval.supabase_gate" },
  { from: "retrieval.supabase_gate", to: "retrieval.intake" },
  { from: "retrieval.intake", to: "retrieval.planner" },
  { from: "retrieval.planner", to: "retrieval.cache" },
  { from: "retrieval.cache", to: "retrieval.retrieve", label: "cache miss" },
  { from: "retrieval.cache", to: "retrieval.calibrate", label: "cache hit" },
  { from: "retrieval.retrieve", to: "retrieval.calibrate" },
  { from: "retrieval.calibrate", to: "retrieval.compose" },
  { from: "retrieval.compose", to: "retrieval.verify" },
  { from: "retrieval.verify", to: "retrieval.safety" },
  { from: "retrieval.safety", to: "retrieval.stream" },

  // Cross-lane edges
  { from: "ingesta.scan", to: "parsing.extract", crossLane: true },
  { from: "parsing.metadata", to: "ingesta.manifest", crossLane: true, label: "tags" },
  { from: "ingesta.sync_supabase", to: "almacenamiento.supabase", crossLane: true },
  { from: "ingesta.sync_supabase", to: "almacenamiento.generations", crossLane: true, label: "activate WIP" },
  { from: "ingesta.promote", to: "almacenamiento.generations", crossLane: true, label: "activate production" },
  { from: "parsing.embed", to: "almacenamiento.supabase", crossLane: true, label: "vectors" },
  { from: "almacenamiento.generations", to: "retrieval.supabase_gate", crossLane: true, label: "active gen" },
  { from: "almacenamiento.fts_rpc", to: "retrieval.retrieve", crossLane: true, label: "FTS" },
  { from: "almacenamiento.hybrid_rpc", to: "retrieval.retrieve", crossLane: true, label: "hybrid" },

  // Surfaces flow
  { from: "surfaces.expert_panel", to: "surfaces.expert_crux" },
  { from: "surfaces.expert_crux", to: "surfaces.expert_classify" },
  { from: "surfaces.citation_profile", to: "surfaces.citation_interp", label: "doc context" },
  { from: "surfaces.citation_interp", to: "surfaces.interp_summary" },

  // Cross-lane: surfaces ← retrieval/almacenamiento
  { from: "almacenamiento.hybrid_rpc", to: "surfaces.expert_panel", crossLane: true, label: "interpretive" },
  { from: "almacenamiento.supabase", to: "surfaces.citation_profile", crossLane: true, label: "instant (chunks)" },
  { from: "almacenamiento.hybrid_rpc", to: "surfaces.citation_interp", crossLane: true, label: "interpretive" },
  { from: "almacenamiento.hybrid_rpc", to: "surfaces.normative_support", crossLane: true, label: "citations" },
  { from: "almacenamiento.supabase", to: "surfaces.form_guide_chat", crossLane: true, label: "guide context" },
  { from: "ingesta.gui_session", to: "surfaces.ingestion_ctrl", crossLane: true, label: "sessions" },
  { from: "ingesta.kanban_worker", to: "surfaces.ingestion_ctrl", crossLane: true, label: "worker status" },

  // Platform lane flow
  { from: "plataforma.auth", to: "plataforma.security" },
  { from: "plataforma.security", to: "plataforma.user_mgmt" },
  { from: "plataforma.auth", to: "plataforma.auth_frontend", crossLane: true, label: "JWT" },
  { from: "plataforma.rls", to: "almacenamiento.supabase", crossLane: true, label: "tenant isolation" },

  // Platform ↔ Retrieval
  { from: "plataforma.auth", to: "retrieval.api", crossLane: true, label: "auth context" },

  // Mobile shell flow
  { from: "mobile.detect", to: "mobile.shell", label: "isMobile()" },
  { from: "mobile.shell", to: "mobile.adapter" },
  { from: "mobile.adapter", to: "mobile.normativa", label: "citations" },
  { from: "mobile.adapter", to: "mobile.interp", label: "expert" },

  // Cross-lane: mobile ← surfaces (shared view models + UI events)
  { from: "surfaces.citation_profile", to: "mobile.normativa", crossLane: true, label: "shared citations + event" },
  { from: "surfaces.expert_panel", to: "mobile.interp", crossLane: true, label: "shared cards + event" },
  { from: "plataforma.auth", to: "mobile.shell", crossLane: true, label: "drawer auth" },
];

export const pipelineGraph: PipelineGraph = { nodes, edges, lanes };
