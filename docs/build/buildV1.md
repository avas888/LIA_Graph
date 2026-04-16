# Build V1 — Nuevo RAG con Graph para LIA

## Resumen Ejecutivo

LIA no necesita un chatbot de moda con grafo; necesita un motor de decision contable-tributaria que responda con contexto de empresa, vigencia normativa, trazabilidad y siguiente accion util para un contador. Build V1 organiza esa construccion como un paquete documental ejecutable, de forma que el equipo pueda pasar de arquitectura a implementacion sin perder continuidad.

La decision central de esta build es clara: el corazon sera un grafo regulatorio compartido construido sobre un corpus unico para todos los tenants. La shell actual se conserva; cambia el motor de recuperacion, planificacion y composicion. El tenant queda en la capa de runtime, historial, permisos y contexto de interaccion, no como particion de conocimiento.

Ese corpus compartido no es solo ET. Para Build V1 debemos pensar al menos en tres familias de evidencia:

- normativa / doctrina oficial
- interpretacion / expertos
- practica / Loggro

Esto no describe una jerarquia de valor. Las tres familias son valiosas por derecho propio para un contador. Lo que cambia en Phase 2 no es su importancia, sino la forma de representarlas: la familia normativa se graphiza primero porque vigencia, reformas, excepciones y dependencias encajan de manera natural en relaciones tipadas; interpretacion y practica deben quedar inventariadas, medibles y recuperables desde el mismo pass de corpus, no escondidas detras de lenguaje futuro.

Ese reset tambien corrige una debilidad central del stack anterior: los `rotulos`, `topics` y `subtopics` no pueden volver a ser la capa load-bearing del retrieval. En Build V1, la semantica normativa fuerte debe vivir en estructura de grafo; el rotulado queda como apoyo de nombres, compatibilidad, enrutamiento inicial y gobernanza de vocabulario.

Tambien obliga a distinguir tres capas que antes se confundian con facilidad:

- capa de source assets: todos los archivos auditados
- capa de corpus canonico: documentos accountant-facing admitidos y revisions pendientes adjuntas a sus base docs
- capa de reasoning: inputs realmente parseables y graphizables para el motor

La parse surface es mas angosta que la audit surface. La graph surface es mas angosta que la parse surface.

Y ahora hay una compuerta mas: que un documento haya sido admitido a la capa canonica no significa automaticamente que ya sea confiable como input durable. Antes de bendecir el manifiesto canonico, Build V1 exige una reconnaissance quality gate que haga visible autoridad, ambiguedad, shape documental y linkage de revisiones.

## Que Problema De Negocio Resuelve El Nuevo RAG

El problema no es solo "recuperar documentos". El problema real es ayudar a un contador a responder preguntas como:

- que norma aplica aqui
- a que empresa, regimen y periodo aplica
- que excepciones o reformas cambian la conclusion
- que evidencia respalda la respuesta
- que accion operativa debe seguir

El RAG actual y los componentes heredados sirven como shell y baseline, pero no modelan de forma nativa las relaciones normativas, la vigencia y las cadenas de reforma del corpus compartido. El nuevo RAG con Graph busca cerrar exactamente esa brecha, manteniendo el aislamiento de historial y trazabilidad por tenant en la capa de aplicacion.

## Por Que GraphRAG Si, Pero Subordinado Al Proposito De LIA

GraphRAG aporta valor cuando:

- la respuesta depende de varias normas conectadas
- la vigencia y la reforma importan
- hay que distinguir norma, doctrina, guia operativa y decision previa
- la salida debe conservar provenance fuerte

GraphRAG no se adopta por novedad. Se adopta porque el dominio tributario colombiano ya se comporta como un grafo: articulos, reformas, excepciones, dependencias de calculo, conceptos, parametros y relaciones cross-domain. En LIA, el grafo no reemplaza todo; coordina la evidencia de mayor valor y deja a las otras capas resolver lo que el grafo no debe absorber.

## Decision Arquitectonica Principal

Build V1 cierra estas decisiones:

- LIA no sera un "graph chatbot" generico.
- LIA sera un motor multi-tenant de decision contable-tributaria, con trazabilidad normativa y contexto de empresa.
- El corpus sera unico y compartido para todos los tenants.
- El corpus compartido tendra al menos tres familias de evidencia:
  - normativa / doctrina oficial
  - interpretacion / expertos
  - practica / Loggro
- El shared regulatory graph sera el nucleo del razonamiento.
- Phase 2 materializa el corpus compartido completo en un solo pass y graphiza primero la familia normativa/oficial porque es la que mejor encaja en estructura de grafo; interpretacion y practica no desaparecen ni esperan a una fase lejana para existir en el sistema.
- Antes de inventariar o graphizar, Phase 2 debe ejecutar una compuerta de auditoria de corpus para separar documentos accountant-facing de working files, patches y notas internas.
- Esa compuerta audit-first recorre la superficie total de archivos y luego materializa una capa canonica antes de cualquier parse normativo.
- La capa canonica no se trata como verdad durable solo por admision: una reconnaissance quality gate puede dejar documentos en `review_required` o `blocked` antes de bendecir el manifiesto.
- Los `revision_candidate` no son corpus standalone; viven adjuntos a su base doc dentro del manifiesto canonico hasta que exista merge confiable.
- Un activo no-markdown o no-parse-ready puede seguir siendo valioso en la capa canonica o de inventory sin ser enviado al parser ni al grafo.
- El vocabulario ratificado es autoridad de nombres para topic y subtopic, pero no la unica puerta de admision del corpus ni el sustituto de relaciones legales.
- El tenant no introduce un corpus propio; introduce aislamiento de sesiones, historial, permisos, metricas y contexto conversacional.
- Habra dos capas principales de evidencia y una capa de runtime:
  - graph regulatorio compartido
  - capa complementaria compartida de retrieval e inventory sobre el mismo corpus, cuando haga falta soporte vectorial o lexical adicional o evidencia no graphizada
  - capa runtime multi-tenant para historial, company context, permisos y trazabilidad
- La shell actual se mantiene compatible via:
  - `PipelineCRequest`
  - `PipelineCResponse`
  - `src/lia_graph/ui_chat_controller.py`
  - `src/lia_graph/ui_server.py` con `_chat_controller_deps()`
  - `StructuredMarkdownStreamAssembler`
- El rollout sera por fases, con shadow mode antes de cualquier cambio de default.

## Alcance Build V1

Build V1 no implementa codigo del nuevo motor. Build V1 deja la construccion lista para ejecutar, con:

- arquitectura objetivo
- fases ordenadas
- archivos a crear o modificar por fase
- pruebas por superficie tocada
- checkpoints de estado
- recovery instructions
- decision log

`docs/build/` es solo para documentacion. Los archivos de implementacion que aqui se listan son objetivos de trabajo en el arbol real del proyecto, por ejemplo:

- `src/lia_graph/`
- `supabase/migrations/`
- `evals/`
- `scripts/`
- `frontend/`

La organizacion final del codigo debe seguir mejor practica tecnica y no estar condicionada por la estructura de `docs/build/`.

No entra en esta build:

- implementacion de FalkorDB
- migraciones nuevas ejecutadas
- reemplazo del runtime activo
- cambios en frontend mas alla de lo que deba quedar planificado

## Como Se Divide La Implementacion Por Fases

- Fase 1: runtime seams y contratos
- Fase 2: shared regulatory graph
- Fase 3: graph planner y retrieval
- Fase 4: tenant runtime context, history and access
- Fase 5: composer, verifier y cache
- Fase 6: routing, evals y shadow mode
- Fase 7: rollout, ops y gobernanza

Cada fase vive como documento operativo independiente dentro de `docs/build/buildv1/` y puede retomarse leyendo solo `STATE.md` y el archivo de la fase activa.

Los documentos por fase describen archivos de codigo a crear o modificar, pero esos archivos viven en sus ubicaciones tecnicas naturales dentro del repo, no dentro de `docs/build/`.

## Como Usar El Estado Para Continuar El Trabajo

El paquete Build V1 es state aware. El flujo operativo esperado es:

1. Leer `docs/build/buildv1/NEXT.md`
2. Leer `docs/build/buildv1/STATE.md`
3. Identificar la fase activa y su `next_action`
4. Abrir el documento de esa fase
5. Retomar desde `Checkpoint Log.current_step`
6. Verificar `blocked_by`, `artifacts_created` y `Failure Recovery`
7. Actualizar `NEXT.md` con la mejor siguiente accion al cerrar cada sesion
8. Actualizar `Decision Log` y `Checkpoint Log` al cerrar cada sesion

Regla de oro: el estado debe registrar progreso operativo real, no solo intencion.

## Indice De Documentos Detallados

- `docs/build/buildv1/README.md`
- `docs/build/buildv1/NEXT.md`
- `docs/build/buildv1/STATE.md`
- `docs/build/buildv1/00-business-purpose-and-success-metrics.md`
- `docs/build/buildv1/01-target-architecture.md`
- `docs/build/buildv1/02-phase-1-runtime-seams-and-contracts.md`
- `docs/build/buildv1/03-phase-2-shared-regulatory-graph.md`
- `docs/build/buildv1/04-phase-3-graph-planner-and-retrieval.md`
- `docs/build/buildv1/05-phase-4-tenant-runtime-context-history-and-access.md`
- `docs/build/buildv1/06-phase-5-composer-verifier-and-cache.md`
- `docs/build/buildv1/07-phase-6-routing-evals-and-shadow-mode.md`
- `docs/build/buildv1/08-phase-7-rollout-ops-and-governance.md`
- `docs/build/buildv1/appendix-a-file-map.md`
- `docs/build/buildv1/appendix-b-test-map.md`
- `docs/build/buildv1/appendix-c-state-template.md`
- `docs/build/buildv1/appendix-d-corpus-audit-and-labeling-policy.md`
