# 04 — Phase 3: Graph Planner and Retrieval

## Status

- `phase_id`: 3
- `status`: IN_PROGRESS
- `owner`: Codex + repo maintainer
- `last_updated`: 2026-04-15T22:07:07-04:00
- `depends_on`: phases 1 and 2 complete
- `exit_criteria`:
  - planner outputs query mode, entry points and budgets
  - retriever returns graph-aware evidence bundle
  - time-scope and vigencia filters influence retrieval decisions
  - fallback semantic path defined for weak anchors

## Intent

- objetivo de la fase: convertir preguntas reales de contador en entry points, traversal plans y evidence bundles
- valor de negocio: evita retrieval plano y recupera cadenas normativas utiles para responder
- superficies afectadas:
  - intake/planning
  - graph retrieval
  - topic bridge
  - evidence assembly
- lane coordination across normativa, interpretacion y practica
- consumo del corpus auditado y rotulado sin volver topic/subtopic la capa load-bearing
- consumo de la capa canonica, no de source assets crudos
- consumo del manifiesto canonico bendecido por la reconnaissance gate, o de un review queue explicitamente aceptado, nunca de admision cruda sin revisar

## Implementation Scope

### Entra

- planner de modos de consulta
- seleccion de entry points
- traversal budgets
- graph retrieval y subgraph assembly
- semantic fallback controlado

### No Entra

- composer final
- runtime history and access controls
- compiled cache

## Files To Create

- `src/lia_graph/pipeline_d/planner.py` - creado
- `src/lia_graph/pipeline_d/retriever.py` - creado
- `src/lia_graph/pipeline_d/contracts.py` - creado
- `src/lia_graph/pipeline_c/temporal_intent.py` - creado
- `src/lia_graph/pipeline_d/answer_support.py` - creado
- `src/lia_graph/pipeline_d/retrieval_support.py` - creado
- `src/lia_graph/pipeline_d/evidence_bundle.py` - opcional, todavia no necesario

## Files To Modify

- `src/lia_graph/topic_router.py` - pendiente si hace falta mas señal para modos/historico
- `src/lia_graph/pipeline_c/intake.py` - actualizado para reutilizar helper historico compartido
- `src/lia_graph/pipeline_c/norm_topic_index.py` - pendiente de reevaluacion
- `src/lia_graph/pipeline_d/orchestrator.py` - actualizado con la primera ruta graph-native real
- `docs/orchestration/orchestration.md` - actualizado para reflejar solo el runtime actual
- `frontend/src/features/orchestration/graph/pipelineGraph.ts` - actualizado para reflejar solo el runtime actual
- `frontend/tests/orchestrationApp.test.ts` - actualizado para evitar que vuelva texto stale sobre la ruta anterior
- `tests/test_phase3_graph_planner_retrieval.py` - nuevo

## Tests For This Surface

### Unitarias

- resolucion de entry points desde articulo, concepto, workflow y company cues
- query mode selection
- traversal budgets y edge filters
- vigencia/time-scope correctness
- semantic fallback cuando faltan anchors

### Integracion

- planner + retriever sobre subgrafo real
- handoff correcto desde intake compartido
- bundle consistente para preguntas multi-hop
- mezcla controlada de backbone normativo con support evidence interpretativo/practico cuando aplique
- preservacion de labels canonicos como hints, sin reemplazar entry points y traversal graph-based
- respeto por `graph_parse_ready` y `parse_strategy` al decidir que evidencia entra por grafo y cual entra por retrieval support
- respeto por `canonical_blessing_status` al decidir que evidencia entra como soporte durable versus evidencia que sigue en cola de revision

### Smoke/Eval

- retrieval quality en preguntas multi-hop de normativa, con ET como slice importante pero no unico
- comparacion baseline vs graph bundle en casos seleccionados
- smokes actuales verdes:
  - RUB: `631-5 -> 631-6 -> 658-3`
  - factura electronica / soportes: `771-2 -> 616-1 -> 617`
  - historico ET: `115 -> Ley 2277 de 2022` con corte inferido `2021-12-31`
  - prompt practico de contador sobre devolucion / saldo a favor: respuesta graph-native anclada en `850`, `589` y `815`
- el runtime servido ahora cae en `pipeline_d` por defecto, de modo que el GUI/no-login public path ya puede probar Phase 3 sin header override manual
- el browser path tambien esta verde otra vez: `/public` y `/public?message=...` ya envian la pregunta y reciben respuesta graph-native en local dev

## Execution Steps

1. Definir el planner output contract. Completo.
2. Mapear señales desde `topic_router` e intake compartido sin volver `topic/subtopic` la unica puerta de entrada. Parcial avanzada: el planner ya reutiliza detección histórica compartida sin abrir un segundo path de retrieval.
3. Resolver entry points normativos y contextuales. Completo en v1 para anchors explicitos, lexical graph fallback y la primera lane de prompts practicos de contador sin cita legal.
4. Ejecutar traversal con vigencia y budget. Parcial avanzada: `historical_reform_chain` ya cambia budget, prioridad de reformas y snippets; el ranking de vecinos/support docs ya filtra ruido obvio para el GUI; falta mayor precisión con `effective_date` real y mejor desambiguación de versiones.
5. Empaquetar el evidence bundle con provenance suficiente para composer, respetando la frontera entre canonical corpus y source assets. Completo para la primera ruta.
6. No consumir como evidencia durable un documento que siga `blocked` en reconnaissance, y tratar `review_required` solo bajo regla explicita y visible. Completo para la primera ruta.

## Checkpoint Log

- `current_step`: 4
- `completed_steps`: [1, 2, 3, 5, 6]
- `blocked_by`: []
- `artifacts_created`: [
  "docs/build/buildv1/04-phase-3-graph-planner-and-retrieval.md",
  "src/lia_graph/pipeline_c/temporal_intent.py",
  "src/lia_graph/pipeline_d/answer_support.py",
  "src/lia_graph/pipeline_d/contracts.py",
  "src/lia_graph/pipeline_d/planner.py",
  "src/lia_graph/pipeline_d/retriever.py",
  "src/lia_graph/pipeline_d/retrieval_support.py",
  "src/lia_graph/pipeline_d/orchestrator.py",
  "tests/test_phase3_graph_planner_retrieval.py"
]
- `notes`: "Phase 3 ya es la ruta servida del producto. En esta iteración la prioridad explícita pasó a ser la calidad del primer answer visible para el contador. Para sostener eso sin seguir creciendo archivos grandes, la lógica de formatting y scoring se granularizó en `answer_support.py` y `retrieval_support.py`, dejando `orchestrator.py` y `retriever.py` por debajo de 1000 LOC. En comportamiento, `pipeline_d` ahora evita que frases procedimentales como `antes de pedir...` activen por error el modo histórico o el modo reforma; agrega búsquedas léxicas específicas para prompts de corrección / firmeza / beneficio de auditoría; endurece el filtro histórico para no meter connected articles ni support docs prácticos ruidosos; y extrae más hechos operativos desde los propios artículos ancla cuando ya están presentes en el artifact text. El formatter visible sigue siendo práctico primero, pero ahora limpia mejor URLs/bibliografía, conserva mejor plazos y reglas operativas en la primera respuesta, y evita contaminar respuestas históricas con soporte práctico ajeno. `docs/orchestration/orchestration.md` también quedó reescrita para documentar paso a paso los algoritmos, prioridades y cálculos reales de planner, retrieval y assembly. Los smokes verdes actuales cubren RUB, factura electrónica, histórico ET (`115` + `Ley 2277 de 2022`, corte `2021-12-31`), devolución (`850`, `589`, `815`) y un prompt mixto de corrección / firmeza / devolución (`588`, `589`, `714`). Lo que sigue es seguir mejorando vigencia exacta, desambiguación de versiones, selección de soporte práctico y síntesis visible por tema."

## Failure Recovery

- como retomar:
  - verificar el ultimo planner contract aprobado
  - revisar si ya existe `evidence_bundle.py`
  - inspeccionar si fallback semantic se disparaba por ausencia de anchors o por bug de planner
- que verificar antes de continuar:
  - existencia del graph schema
  - existencia de audit outputs, reconnaissance outputs e inventario del corpus compartido
  - normalizacion de topics sin depender solo de ellos para narrowing
  - estado de `canonical_blessing_status` del manifiesto que se quiere consumir
  - filtros temporales disponibles
  - si el ruido en connected articles viene de ranking o de colisión de `article_key`

## Open Questions

- si `global_pattern` vive en esta fase o se deja solo documentado para implementacion posterior
- si el bridge con `norm_topic_index.py` debe quedarse o retirarse cuando FalkorDB asuma el rol principal
- hasta dónde conviene resolver temporalidad exacta en artifacts versus inferirla en retrieval mientras `effective_date` siga vacio en el manifiesto

## Decision Log

- retrieval sera mode-aware
- semantic fallback existe, pero no domina el path cuando el grafo tiene buenos anchors
- labels y vocabulario ayudan con entry hints y compatibilidad, pero el razonamiento normativo debe descansar en graph anchors, traversal y provenance
- Phase 3 consume corpus canonico bendecido; admision de archivos por si sola no basta para convertirlos en evidencia durable
- el fallback debil aprobado para esta fase es lexical matching sobre articulos del grafo, no retrieval label-first sobre documentos
- el primer evidence bundle se arma desde graph evidence primario y luego adjunta documentos canonicos listos como soporte normativa/interpretacion/practica
- la primera capa temporal de Phase 3 vive dentro del planner contract y la recuperación graph-first; si falta precisión debe mejorarse ahí, no creando un path histórico paralelo
- los prompts prácticos de contador deben poder generar anchors de planner aunque no citen la ley; la primera lane aprobada para eso es devolución / saldo a favor
- la respuesta publicada al usuario final no debe incluir meta-thinking del sistema; el planner/retrieval vive en `diagnostics`, no en el texto visible del answer
- la documentación y el HTML de `/orchestration` deben representar solo el runtime actual y actualizarse al mismo tiempo que cambie la ruta servida
