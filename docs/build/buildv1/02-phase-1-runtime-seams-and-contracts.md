# 02 — Phase 1: Runtime Seams and Contracts

## Status

- `phase_id`: 1
- `status`: COMPLETE
- `owner`: Codex + repo maintainer
- `last_updated`: 2026-04-14T10:51:27-04:00
- `depends_on`: Build V1 docs approved
- `exit_criteria`:
  - pipeline routing seam defined behind current shell contract
  - request/response compatibility preserved
  - telemetry fields for pipeline variant defined
  - no change required to public chat surface

## Intent

- objetivo de la fase: definir el punto de insercion del nuevo motor sin romper la shell existente
- valor de negocio: permite evolucionar el motor de razonamiento con bajo riesgo para la experiencia actual
- superficies afectadas:
  - chat runtime
  - request/response contracts
  - streaming path
  - chat run coordination
  - telemetry base

## Implementation Scope

### Entra

- resolver de pipeline detras de la dependencia actual
- contrato interno para ejecutar Pipeline D sin cambiar el payload publico
- tagging de telemetria por variante de pipeline
- definicion del comportamiento de dual-run futuro

### No Entra

- logica real de graph retrieval
- cambios en frontend
- nuevas migraciones de datos

## Files To Create

- `src/lia_graph/pipeline_router.py` - nuevo
- `src/lia_graph/pipeline_d/orchestrator.py` - nuevo si no existe en implementacion real
- `tests/test_phase1_runtime_seams.py` - nuevo

## Files To Modify

- `src/lia_graph/ui_server.py` - existente
- `src/lia_graph/ui_chat_controller.py` - existente
- `src/lia_graph/ui_chat_payload.py` - existente
- `src/lia_graph/ui_chat_persistence.py` - existente
- `src/lia_graph/ui_chat_context.py` - existente
- `src/lia_graph/clarification_session_store.py` - existente
- `src/lia_graph/ui_citation_controllers.py` - existente
- `src/lia_graph/ui_reference_resolvers.py` - existente
- `src/lia_graph/pipeline_d/__init__.py` - existente
- `src/lia_graph/pipeline_c/contracts.py` - existente
- `src/lia_graph/pipeline_c/orchestrator.py` - existente
- `src/lia_graph/chat_run_runtime.py` - existente
- `src/lia_graph/chat_runs_store.py` - existente

## Tests For This Surface

### Unitarias

- `pipeline_router` elige variante correcta para request normal, explicit route y future dual-run
- contratos siguen serializando `PipelineCResponse.to_dict()` sin cambios de forma
- tagging de telemetria agrega `pipeline_variant` sin romper consumidores actuales

### Integracion

- `/api/chat` mantiene respuesta valida con runner resuelto por seam
- `/api/chat/stream` mantiene draft/final sin romper `StructuredMarkdownStreamAssembler`
- `chat_run_id` no duplica corridas por cambio de seam

### Smoke/Eval

- smoke local del flujo chat con pipeline baseline
- smoke del runner alterno en modo compat stub

## Execution Steps

1. Definir una interfaz de runner comun para baseline y Pipeline D.
2. Crear `pipeline_router.py` para resolver el runner segun config y request context.
3. Sustituir la referencia directa actual en `_chat_controller_deps()` por el resolver.
4. Propagar metadatos minimos de variante de pipeline a payloads y run telemetry.
5. Validar que rutas `/api/chat` y `/api/chat/stream` siguen compatibles.

## Checkpoint Log

- `current_step`: 5
- `completed_steps`: [1, 2, 3, 4, 5]
- `blocked_by`: []
- `artifacts_created`: [
  "src/lia_graph/pipeline_router.py",
  "src/lia_graph/pipeline_d/orchestrator.py",
  "tests/test_phase1_runtime_seams.py"
]
- `notes`: "El seam ya enruta baseline, graph y dual-run futuro detras de `_chat_controller_deps()`. `PipelineCResponse.to_dict()` se mantuvo estable; la metadata de variante se agrega en payloads API, chat-run telemetry y SSE meta. El override explicito de fase 1 entra por metadata/backend headers (`X-LIA-Pipeline-Route` o `X-LIA-Pipeline-Variant`). El smoke local paso en `/api/chat` y `/api/chat/stream` para baseline y `pipeline_d` usando `LIA_STORAGE_BACKEND=filesystem`. Durante ese smoke se corrigieron compat shims que estaban rompiendo dispatch y payload assembly. Persiste una advertencia no bloqueante: `run_job_async` aun degrada la programacion de persistencia asincrona en este scaffold."

## Failure Recovery

- como retomar:
  - leer `STATE.md`
  - confirmar si el seam ya fue creado o solo documentado
  - revisar si existe `src/lia_graph/pipeline_router.py`
  - revisar si `ui_server.py` sigue inyectando `run_pipeline_c` directo
- que verificar antes de continuar:
  - integridad del contract de `PipelineCResponse`
  - comportamiento actual de `chat_run_coordinator`
  - draft/final parity en stream

## Open Questions

- si el selector de pipeline debe vivir solo en config o tambien en request metadata desde la primera iteracion
- si el dual-run debe emitir telemetria separada o una estructura consolidada por chat run

## Decision Log

- se mantiene el contrato publico actual
- la shell no debe conocer detalles de graph retrieval
- la variante de pipeline se resuelve en el backend, no en el frontend, durante v1 inicial
- el override explicito de variante se acepta por metadata del request, no por un cambio del payload publico
- `dual_run` en fase 1 sirve solo el runner primario y expone `shadow_pipeline_variant` como metadata preparatoria
- el smoke de fase 1 se valida localmente en modo `filesystem` cuando Supabase no esta disponible en el runtime de shell
